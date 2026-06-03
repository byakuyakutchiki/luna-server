"""
OpenAI Realtime Bridge - Pont audio entre Twilio Media Streams et OpenAI Realtime API

Relaie l'audio bidirectionnellement :
  Telephone <-> Twilio Media Stream (WebSocket) <-> Ce bridge <-> OpenAI Realtime API (WebSocket)

Format audio : G.711 mu-law (8kHz) natif des deux cotes -> zero transcodage.

Usage:
    bridge = RealtimeBridge(
        openai_api_key="sk-...",
        ws_twilio=websocket,  # FastAPI WebSocket connecte par Twilio
        call_context="Tu es Luna...",
        tool_handler=async_func,  # Callback pour executer les tool calls
    )
    await bridge.run()
"""
import json
import base64
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, Awaitable, List

import websockets

logger = logging.getLogger(__name__)

import os

OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
OPENAI_REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_REALTIME_MODEL}"
OPENAI_VOICE_NAME = os.getenv("OPENAI_VOICE_NAME", "alloy")

# Semaphore globale: limite les connexions OpenAI Realtime simultanées
# OpenAI rate limit ~100-200 concurrent connections/account
_realtime_semaphore = asyncio.Semaphore(int(os.getenv("OPENAI_REALTIME_MAX_CONCURRENT", "50")))
_active_bridges = 0  # compteur pour monitoring

# Memes tools que Tavus (definis dans tavus_client.py LUNA_TOOLS)
# Format adapte pour OpenAI Realtime API (pas de wrapper "type":"function")
VOICE_TOOLS = [
    {
        "type": "function",
        "name": "chat",
        "description": "Repondre a l'utilisateur par conversation normale. Utilise UNIQUEMENT quand l'utilisateur fait une simple conversation, une question d'information, ou une discussion sans demande de rendu visuel. Si l'utilisateur demande un tableau, un graphique, un document, une reunion, un kanban, ou tout rendu visuel — NE PAS utiliser chat, utiliser iris_render ou un autre outil approprie.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "La reponse textuelle courte a l'utilisateur"
                }
            },
            "required": ["message"]
        }
    },
    {
        "type": "function",
        "name": "call_contact",
        "description": "Appeler quelqu'un par TELEPHONE AUDIO maintenant. Luna passe un vrai appel telephonique vocal et parle pour transmettre un message. Deux usages : (A) Appeler un contact de confiance par son nom : 'appelle maman', 'appelle Marie'. (B) Appeler une administration/service avec un numero donne par le souscripteur : 'appelle la mairie au 01 44 56 78 90'. Pour (B), renseigner phone_number avec le numero fourni. C'est un APPEL VOCAL, pas un SMS.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Prenom ou nom du contact, ou nom du service/administration a appeler"
                },
                "message": {
                    "type": "string",
                    "description": "Le message que Luna doit transmettre pendant l'appel vocal"
                },
                "phone_number": {
                    "type": "string",
                    "description": "Numero de telephone a appeler directement (uniquement pour les administrations/services, quand le souscripteur donne le numero). Ne PAS renseigner pour les contacts de confiance."
                }
            },
            "required": ["contact_name", "message"]
        }
    },
    {
        "type": "function",
        "name": "send_sms",
        "description": "Envoyer un SMS ECRIT (texto) a un contact de confiance. UNIQUEMENT quand le souscripteur demande explicitement un SMS ou un texto. Ex: 'envoie un SMS a maman', 'envoie un texto a Marie'. NE PAS utiliser si le souscripteur dit 'appelle' ou 'telephone' — dans ce cas utiliser call_contact.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Prenom ou nom du contact de confiance"
                },
                "message": {
                    "type": "string",
                    "description": "Le contenu du SMS a envoyer"
                }
            },
            "required": ["contact_name", "message"]
        }
    },
    {
        "type": "function",
        "name": "create_instruction",
        "description": "Creer un rappel, un appel audio planifie, un SMS planifie, ou une visio planifiee. Ex: 'rappelle-moi de...', 'tous les jours a 8h...', 'appelle Marie a 14h pendant 5 min', 'envoie un SMS a Jean demain'. Pour les appels planifies, precise la duree max en minutes (1-10).",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "L'instruction en langage naturel"
                },
                "max_duration_minutes": {
                    "type": "integer",
                    "description": "Duree max de l'appel en minutes (1-10, defaut 3). Uniquement pour les appels planifies."
                }
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "create_note",
        "description": "Prendre une note. Quand le souscripteur dit 'note que...', 'retiens que...'",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Le contenu de la note"
                }
            },
            "required": ["content"]
        }
    },
    {
        "type": "function",
        "name": "get_contacts",
        "description": "Lister les contacts de confiance du souscripteur.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "generate_document",
        "description": "Generer un document (courrier, lettre, resume).",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["courrier_admin", "courrier_resiliation", "resume_hebdo", "fiche_sante", "compte_rendu", "export_notes"],
                    "description": "Le type de document"
                },
                "subject": {
                    "type": "string",
                    "description": "L'objet du document"
                },
                "details": {
                    "type": "string",
                    "description": "Les details a inclure"
                }
            },
            "required": ["doc_type", "subject"]
        }
    },
    {
        "type": "function",
        "name": "alert_contacts",
        "description": "Alerter tous les contacts de confiance en cas d'urgence.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "La raison de l'alerte"
                }
            },
            "required": ["reason"]
        }
    },
    {
        "type": "function",
        "name": "send_email",
        "description": "Envoyer un email a un contact de confiance. Quand le souscripteur dit 'envoie un email a...', 'ecris un mail a...', 'envoie un message a... par email'.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Prenom ou nom du contact destinataire (ex: maman, Marie, mon fils)"
                },
                "subject": {
                    "type": "string",
                    "description": "L'objet de l'email"
                },
                "body": {
                    "type": "string",
                    "description": "Le contenu de l'email"
                }
            },
            "required": ["contact_name", "subject", "body"]
        }
    },
    {
        "type": "function",
        "name": "invite_visio",
        "description": "Inviter un contact de confiance en visioconference. Envoie un SMS avec un lien pour rejoindre la visio. Quand le souscripteur dit 'invite X en visio', 'fais une visio avec X', 'appelle X en video', 'envoie un lien visio a X'.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Prenom ou nom du contact a inviter (ex: maman, Ludovic, ma soeur)"
                }
            },
            "required": ["contact_name"]
        }
    },
    {
        "type": "function",
        "name": "search_web",
        "description": "Rechercher des informations sur Internet. Utilise cette fonction quand le souscripteur demande de chercher un restaurant, un hotel, des horaires de train, un vol, un service, un numero de telephone, une adresse, ou toute information pratique. Ex: 'cherche un restaurant italien pres de chez moi', 'trouve-moi un train pour Paris demain', 'quel est le numero de la mairie de Lyon'. Renvoie les resultats les plus pertinents.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "La recherche a effectuer (en francais ou anglais)"
                },
                "location": {
                    "type": "string",
                    "description": "Ville ou adresse pour contextualiser la recherche (optionnel, utilise la localisation du souscripteur si disponible)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "search_places",
        "description": "Rechercher des lieux, commerces et services a proximite : restaurants, hotels, pharmacies, taxis, coiffeurs, garages, etc. Plus precis que search_web pour les recherches locales. Retourne noms, adresses, telephones, notes, horaires. Utilise quand le souscripteur demande 'trouve-moi un restaurant', 'une pharmacie de garde', 'un hotel pres de la gare', 'un taxi', 'un coiffeur'.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Ce que le souscripteur cherche (ex: 'restaurant italien', 'pharmacie de garde', 'hotel 3 etoiles')"
                },
                "location": {
                    "type": "string",
                    "description": "Ville ou quartier (optionnel, utilise la localisation du souscripteur si non precise)"
                },
                "category": {
                    "type": "string",
                    "description": "Categorie du lieu (restaurant, hotel, pharmacie, taxi, coiffeur, garage, etc.)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "get_page_info",
        "description": "Consulter une page web pour extraire des informations detaillees : menu d'un restaurant, tarifs d'un hotel, horaires d'un service, disponibilites. Utilise apres search_web ou search_places pour obtenir plus de details sur un resultat. Ex: consulter le site d'un restaurant pour voir le menu et les prix.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL de la page a consulter"
                },
                "focus": {
                    "type": "string",
                    "description": "Ce que Luna cherche sur la page (ex: 'menu et prix', 'horaires', 'tarifs chambre', 'disponibilites')"
                }
            },
            "required": ["url"]
        }
    },
    {
        "type": "function",
        "name": "get_player_stats",
        "description": "Obtenir les statistiques du Monde IA Watch du souscripteur : niveau, XP, etoiles, serie de connexion, stabilite. Utilise quand le souscripteur demande 'quel est mon niveau ?', 'combien j'ai d'XP ?', 'c'est quoi ma serie ?'.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "get_active_missions",
        "description": "Obtenir les missions actives du souscripteur dans le Monde IA Watch, avec progression et recompense. Utilise quand il demande 'quelles sont mes missions ?', 'qu'est-ce que je dois faire ?', 'mes objectifs'.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "get_badges",
        "description": "Obtenir la liste des badges gagnes par le souscripteur dans le Monde IA Watch. Utilise quand il demande 'quels badges j'ai ?', 'mes trophees', 'mes recompenses'.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "get_weather",
        "description": "Obtenir la meteo actuelle et les previsions. Utilise quand le souscripteur demande 'quel temps fait-il ?', 'meteo', 'il va pleuvoir ?', 'temperature', 'quel temps demain ?', 'est-ce qu'il fait beau ?'. Peut specifier une ville ou utiliser la localisation du souscripteur.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Ville pour la meteo (ex: 'Paris', 'Lyon', 'Marseille'). Si non precise, utilise la localisation du souscripteur."
                }
            }
        }
    },
    {
        "type": "function",
        "name": "get_news",
        "description": "Obtenir les dernieres actualites du jour. Utilise quand le souscripteur demande 'quelles sont les nouvelles ?', 'actualites', 'infos du jour', 'qu'est-ce qui se passe ?', 'les news', 'donne-moi les infos'. Peut filtrer par categorie.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["general", "france", "monde", "economie", "sport", "tech", "sante"],
                    "description": "Categorie d'actualites souhaitee. Par defaut: general (un mix de tout)."
                },
                "count": {
                    "type": "integer",
                    "description": "Nombre d'articles a retourner (3-10). Par defaut: 5."
                }
            }
        }
    },
    {
        "type": "function",
        "name": "search_flights",
        "description": "Rechercher des vols avec prix, horaires, compagnies. Utilise quand le souscripteur demande 'trouve-moi un vol pour...', 'billet d'avion pour...', 'vol Paris-Nice'. Retourne des resultats reels avec liens de reservation. Le souscripteur reserve et paie LUI-MEME sur le site — tu ne geres PAS le paiement. Donne-lui toutes les infos pour qu'il n'ait plus qu'a cliquer.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Ville ou aeroport de depart (ex: 'Paris', 'Lyon', 'CDG')"
                },
                "destination": {
                    "type": "string",
                    "description": "Ville ou aeroport d'arrivee"
                },
                "departure_date": {
                    "type": "string",
                    "description": "Date de depart YYYY-MM-DD"
                },
                "return_date": {
                    "type": "string",
                    "description": "Date de retour YYYY-MM-DD (optionnel, aller simple si absent)"
                },
                "passengers": {
                    "type": "integer",
                    "description": "Nombre de passagers (default: 1)"
                },
                "travel_class": {
                    "type": "string",
                    "enum": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
                    "description": "Classe de voyage (default: ECONOMY)"
                },
                "direct_only": {
                    "type": "boolean",
                    "description": "Vols directs uniquement (default: false)"
                }
            },
            "required": ["origin", "destination", "departure_date"]
        }
    },
    {
        "type": "function",
        "name": "search_hotels",
        "description": "Rechercher des hotels avec prix, etoiles, disponibilites. Utilise quand le souscripteur demande 'trouve-moi un hotel a...', 'ou dormir a...', 'hebergement a...'. Retourne des resultats reels avec liens de reservation. Le souscripteur reserve et paie LUI-MEME — tu ne geres PAS le paiement. Donne toutes les infos utiles (prix, adresse, note, lien).",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Ville (ex: 'Paris', 'Lyon', 'Barcelone')"
                },
                "check_in": {
                    "type": "string",
                    "description": "Date d'arrivee YYYY-MM-DD"
                },
                "check_out": {
                    "type": "string",
                    "description": "Date de depart YYYY-MM-DD"
                },
                "guests": {
                    "type": "integer",
                    "description": "Nombre de personnes (default: 1)"
                },
                "stars": {
                    "type": "integer",
                    "description": "Nombre minimum d'etoiles (1-5, optionnel)"
                },
                "price_range": {
                    "type": "string",
                    "description": "Budget par nuit en EUR (ex: '50-150', optionnel)"
                }
            },
            "required": ["city", "check_in", "check_out"]
        }
    },
    {
        "type": "function",
        "name": "book_restaurant",
        "description": "Rechercher un restaurant avec adresse, telephone, note, horaires. Utilise quand le souscripteur demande 'trouve-moi un restaurant', 'un resto italien ce soir', 'ou manger a Lyon'. Retourne des resultats reels. Pour reserver, tu peux proposer d'appeler le restaurant avec call_contact, ou donner le numero pour que le souscripteur appelle lui-meme.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Ville (ex: 'Paris', 'Lyon')"
                },
                "date": {
                    "type": "string",
                    "description": "Date YYYY-MM-DD"
                },
                "time": {
                    "type": "string",
                    "description": "Heure souhaitee HH:MM (default: 20:00)"
                },
                "party_size": {
                    "type": "integer",
                    "description": "Nombre de convives (default: 2)"
                },
                "cuisine": {
                    "type": "string",
                    "description": "Type de cuisine souhaitee (italien, japonais, francais, etc. — optionnel)"
                }
            },
            "required": ["city", "date"]
        }
    },
    # === SOCIAL TOOLS ===
    {
        "type": "function",
        "name": "get_friends_online",
        "description": "Voir les amis du souscripteur dans le Monde Luna et lesquels sont en ligne. Utilise quand il demande 'qui est connecte ?', 'mes amis sont la ?', 'qui est en ligne ?', 'combien j'ai d'amis ?'.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "send_dm_voice",
        "description": "Envoyer un message prive (DM) a un ami dans le Monde Luna. PAS un SMS — c'est un message dans l'application Luna. Utilise quand le souscripteur dit 'envoie un message a [ami Luna]', 'dis a [ami Luna] que...', en parlant d'un ami du Monde Luna (pas un contact de confiance). Pour les contacts de confiance, utilise send_sms ou send_email.",
        "parameters": {
            "type": "object",
            "properties": {
                "friend_name": {
                    "type": "string",
                    "description": "Pseudo ou prenom de l'ami dans le Monde Luna"
                },
                "message": {
                    "type": "string",
                    "description": "Le message a envoyer"
                }
            },
            "required": ["friend_name", "message"]
        }
    },
    {
        "type": "function",
        "name": "get_my_friend_code",
        "description": "Obtenir le code ami du souscripteur pour qu'il puisse le partager. Utilise quand il demande 'c'est quoi mon code ami ?', 'mon code pour ajouter des amis', 'comment on m'ajoute ?'.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    # === PERCEPTION TOOL ===
    {
        "type": "function",
        "name": "look_around",
        "description": "Regarder ce que la camera du souscripteur voit en ce moment. Utilise quand le souscripteur dit 'qu'est-ce que tu vois ?', 'regarde autour', 'tu me vois ?', 'decris ce que tu vois', 'qu'est-ce qu'il y a devant moi ?'. Necessite que la camera soit activee.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    # --- SECRETARY TOOLS ---
    {
        "type": "function",
        "name": "get_documents_summary",
        "description": "Voir le resume des documents du souscripteur : combien de factures en attente, combien payees, total a payer, dossiers. Utilise quand il demande 'ou j'en suis avec mes papiers', 'mes factures', 'mon courrier'.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "get_budget_analysis",
        "description": "Analyse le budget du souscripteur : revenus, depenses, reste a vivre, prevision fin de mois, suggestions d'economies. Utilise quand il demande 'mon budget', 'est-ce que je peux me permettre X', 'combien il me reste', 'je suis dans le rouge?'.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "check_affordability",
        "description": "Verifie si le souscripteur peut se permettre une depense. Utilise quand il dit 'est-ce que je peux acheter X a Y euros', 'j'ai envie de X, c'est possible?'.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Montant de la depense en euros"},
                "label": {"type": "string", "description": "Description de la depense"}
            },
            "required": ["amount"]
        }
    },
    {
        "type": "function",
        "name": "add_expense",
        "description": "Enregistre une depense ou un revenu. Utilise quand le souscripteur dit 'j'ai depense X pour Y', 'j'ai recu mon salaire', 'j'ai paye le loyer'.",
        "parameters": {
            "type": "object",
            "properties": {
                "montant": {"type": "number", "description": "Montant en euros"},
                "label": {"type": "string", "description": "Description (ex: courses, loyer, essence)"},
                "categorie": {"type": "string", "description": "Categorie: logement, courses, transport, loisirs, sante, abonnements, impots, autre"},
                "direction": {"type": "string", "enum": ["depense", "revenu"], "description": "depense ou revenu"}
            },
            "required": ["montant", "label"]
        }
    },
    {
        "type": "function",
        "name": "get_reminders",
        "description": "Liste les rappels et echeances a venir + ceux en retard. Utilise quand le souscripteur demande 'qu'est-ce que je dois faire', 'mes echeances', 'j'ai oublie quelque chose?'.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "add_reminder",
        "description": "Cree un rappel pour le souscripteur. Utilise quand il dit 'rappelle-moi de...', 'il faut que je pense a...', 'n'oublie pas de...'. Toujours extraire l'heure si mentionnee.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titre du rappel"},
                "due_date": {"type": "string", "description": "Date d'echeance au format YYYY-MM-DD"},
                "due_time": {"type": "string", "description": "Heure du rappel au format HH:MM (ex: 20:00, 08:30). Obligatoire si l'heure est mentionnee."},
                "description": {"type": "string", "description": "Details supplementaires"}
            },
            "required": ["title"]
        }
    },
    {
        "type": "function",
        "name": "search_documents",
        "description": "Cherche dans les documents du souscripteur par mot-cle (emetteur, reference, objet). Utilise quand il demande 'retrouve ma facture EDF', 'ou est le courrier de la CAF'.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Mot-cle de recherche (emetteur, reference, type)"}
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "list_folders",
        "description": "Affiche l'arborescence des dossiers de documents du souscripteur. Utilise quand il demande 'mes dossiers', 'montre mes classeurs', 'comment c'est range'.",
        "parameters": {"type": "object", "properties": {}}
    },
    # === CONFERENCE ===
    {
        "type": "function",
        "name": "join_conference",
        "description": (
            "Rejoindre une conference telephonique en composant un numero et en entrant un code PIN. "
            "Luna ecoute et prend des notes de reunion. "
            "Utilise quand le souscripteur dit 'rejoins ma reunion', 'appelle le bridge de conf', "
            "'prends des notes a la reunion', 'rejoins le call'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Numero de telephone du bridge de conference (format E.164 ou national)"
                },
                "pin": {
                    "type": "string",
                    "description": "Code PIN ou identifiant de reunion (chiffres uniquement, sans espaces)"
                },
                "context": {
                    "type": "string",
                    "description": "Nom ou sujet de la reunion pour les notes (ex: 'Reunion equipe projet X')"
                },
                "max_duration_minutes": {
                    "type": "integer",
                    "description": "Duree max de la conference en minutes (defaut 60)"
                }
            },
            "required": ["phone_number"]
        }
    },
    # === SESSION COLLABORATION ===
    {
        "type": "function",
        "name": "invite_to_session",
        "description": (
            "Inviter quelqu'un a rejoindre la session Iris collaborative. "
            "Utilise quand le souscripteur dit 'invite Marie', 'ajoute Pierre a la session', "
            "'partage la session avec M. Dupont'. "
            "Genere un lien d'invitation unique. "
            "role='trusted' pour l'equipe interne, role='guest' pour un client ou collaborateur externe. "
            "project_filter limite ce que l'invite peut voir (laisser vide = acces projet en cours seulement)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Prenom ou nom de la personne a inviter (ex: 'Marie', 'M. Dupont')"
                },
                "role": {
                    "type": "string",
                    "enum": ["trusted", "guest"],
                    "description": "trusted = equipe de confiance, guest = collaborateur externe"
                },
                "project_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Projets que l'invite peut voir. Vide = projet en cours seulement."
                },
                "send_sms": {
                    "type": "boolean",
                    "description": "Envoyer le lien par SMS (necessite numero)"
                },
                "phone_number": {
                    "type": "string",
                    "description": "Numero de telephone pour envoyer le lien d'invitation"
                }
            },
            "required": ["name"]
        }
    },
    # === CALL CONTROL ===
    {
        "type": "function",
        "name": "iris_render",
        "description": (
            "Afficher du contenu visuel dans l'Iris Command Screen. "
            "Tu as la main sur cet ecran : tu peux projeter un tableau, un graphique, "
            "des KPI, une timeline, une roadmap, une comparaison, un document, une carte, "
            "un budget, une reunion, une decision, une fiche contact ou un formulaire. "
            "Appelle cette fonction AVANT de parler chaque fois que tu prepares un rendu visuel. "
            "Si l'utilisateur demande de transformer un tableau ou des chiffres en graphique, "
            "utilise render_type=chart. Ne dis jamais que tu ne peux pas utiliser ton tableau. "
            "Le souscripteur voit le rendu visuel en temps reel pendant que tu parles. "
            "N'envoie pas le contenu en texte oral : mets-le dans le payload et parle brievement."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "render_type": {
                    "type": "string",
                    "enum": [
                        "data_board", "document_draft", "action_board", "context_panel",
                        "missing_info", "status_rail", "kpi_cards", "chart", "timeline",
                        "roadmap", "comparison", "document_insight", "kanban_board",
                        "contact_board", "map_board", "decision_board", "budget_board",
                        "meeting_board", "media_board", "form_board"
                    ],
                    "description": (
                        "data_board=tableau, chart=graphique/courbe/barres/donut, "
                        "kpi_cards=indicateurs, timeline=chronologie, roadmap=plan par phases, "
                        "comparison=comparaison, document_draft=courrier/lettre, "
                        "document_insight=analyse document, action_board=checklist/action, "
                        "kanban_board=taches par colonnes, contact_board=fiche contact, "
                        "map_board=carte/adresse, decision_board=aide a la decision, "
                        "budget_board=budget, meeting_board=reunion, media_board=fichiers, "
                        "form_board=formulaire, context_panel=contexte, missing_info=infos manquantes, "
                        "status_rail=etat services"
                    )
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Donnees du rendu selon render_type. "
                        "data_board: {title, columns:[str], rows:[[str]], summary?}. "
                        "document_draft: {title, recipient?, body, placeholders?:[str]}. "
                        "action_board: {sections:[{title,items:[{text,done?,tag?}]}], requires_confirmation?, action_type?, summary?}. "
                        "context_panel: {sections:[{heading,body}]}. "
                        "missing_info: {fields:[str], suggestions?:[str]}. "
                        "status_rail: {services:[{name,status,info?}]}. "
                        "chart: {title, type:'line'|'bar'|'donut', labels:[str], datasets:[{label,data:[number]}], summary?}. "
                        "kpi_cards: {kpis:[{label,value,trend?}], summary?}. "
                        "timeline: {events:[{date,title,description?}], summary?}. "
                        "roadmap: {phases:[{title,description,status?}], summary?}. "
                        "decision_board: {options:[{name,pros:[str],cons:[str]}], recommendation?}. "
                        "meeting_board: {title, date?, time?, participants:[{name,initials?}], agenda:[{item,done?}], decisions:[str], summary?}. "
                        "kanban_board: {title, columns:[{id,label,color?,cards:[{title,tag?}]}], summary?}."
                    ),
                    "additionalProperties": True
                }
            },
            "required": ["render_type", "payload"]
        }
    },
    {
        "type": "function",
        "name": "start_meeting",
        "description": "Demarrer la prise de notes d'une reunion. Utilise quand l'utilisateur dit 'prenons les notes', 'reunion', 'compte-rendu', 'qui doit faire quoi'. Iris affiche un meeting_board avec participants, ordre du jour, decisions et actions. Tu peux mettre a jour le meeting_board plusieurs fois pendant la reunion avec iris_render.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titre de la reunion"},
                "participants": {"type": "array", "items": {"type": "string"}, "description": "Noms des participants"}
            },
            "required": ["title"]
        }
    },
    {
        "type": "function",
        "name": "organize_kanban",
        "description": "Organiser des taches en tableau Kanban. Utilise quand l'utilisateur dit 'organise mes taches', 'kanban', 'a faire', 'priorites', 'plan d'action'. Iris affiche un kanban_board avec colonnes (A faire, En cours, Bloque, Termine) et les taches demandees.",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste des taches a organiser"
                }
            },
            "required": ["tasks"]
        }
    },
    {
        "type": "function",
        "name": "hang_up",
        "description": "Raccrocher et terminer l'appel telephonique. OBLIGATOIRE : utilise cette fonction CHAQUE FOIS que tu dis au revoir, que tu raccroches, ou que la conversation est terminee. Ne dis JAMAIS 'je raccroche' sans appeler cette fonction immediatement apres.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Raison de la fin d'appel (ex: 'mission accomplie', 'au revoir', 'fin de conversation')"
                }
            }
        }
    },
]


def _build_gamification_voice_section(redis_client, tenant_id: int) -> str:
    """Build gamification context for voice calls."""
    if not redis_client or not tenant_id:
        return ""
    try:
        from core.gamification.redis_ops import GamificationRedisOps
        from core.gamification.engine import get_level_for_xp
        gops = GamificationRedisOps(redis_client)
        player = gops.get_player(tenant_id)
        if not player:
            return ""
        xp = int(player.get("xp", 0))
        lvl = get_level_for_xp(xp)
        streak = int(player.get("streak_days", 0))
        stars = int(player.get("stars", 0))
        section = f"\n=== MONDE IA WATCH ===\n"
        section += f"Niveau {lvl['level']} ({lvl['title']}), {lvl['progress_percent']}% vers le suivant\n"
        section += f"XP: {xp}, Etoiles: {stars}, Serie: {streak} jour(s)\n"
        section += "Tu peux repondre aux questions sur le niveau, les badges et les missions si on te demande.\n"
        return section
    except Exception:
        return ""


def _build_language_voice_section(language: str) -> str:
    """Build language instruction for voice calls."""
    if language == "en":
        return "=== LANGUAGE ===\nThe subscriber prefers English. Respond EXCLUSIVELY in English. Keep the same warm tone.\n"
    elif language == "es":
        return "=== IDIOMA ===\nEl suscriptor prefiere espanol. Responde EXCLUSIVAMENTE en espanol. Tono calido.\n"
    return ""


def _build_budget_voice_section(redis_client, tenant_id: int) -> str:
    """Build budget context for voice calls."""
    if not redis_client or not tenant_id:
        return ""
    try:
        profile = redis_client.get_profile(tenant_id)
        if not profile:
            return ""
        max_budget = int(float(getattr(profile, "max_budget", 0) or 0))
        if max_budget <= 0:
            return ""
        import datetime as _dt
        month_key = _dt.datetime.now().strftime("%Y-%m")
        spending_key = f"{redis_client.prefix}:{tenant_id}:concierge:spending:{month_key}"
        spent_cents = int(redis_client.client.get(spending_key) or 0)
        spent_eur = spent_cents / 100
        remaining = max(0, max_budget - spent_eur)
        return (
            f"\n=== BUDGET CONCIERGERIE ===\n"
            f"Plafond: {max_budget} EUR/mois. Depense ce mois: {spent_eur:.2f} EUR. Reste: {remaining:.2f} EUR.\n"
            f"Ne propose RIEN qui depasse le reste. Si request_payment refuse, explique le plafond.\n"
        )
    except Exception:
        return ""


def _build_perception_voice_section(memory_manager) -> str:
    """Build perception context if camera is active."""
    if not memory_manager:
        return ""
    try:
        if not memory_manager.is_perception_enabled():
            return ""
        scene = memory_manager.get_perception_state()
        if not scene:
            return "\n=== PERCEPTION VISUELLE ===\nLa camera est activee mais aucune scene n'a encore ete analysee.\nTu peux utiliser la fonction look_around pour regarder.\n"
        desc = scene.scene_description if hasattr(scene, "scene_description") else str(scene)
        section = "\n=== PERCEPTION VISUELLE (camera active) ===\n"
        section += f"Derniere observation : {desc}\n"
        section += "Tu peux utiliser la fonction look_around pour actualiser ta vision.\n"
        if hasattr(scene, "abnormalities") and scene.abnormalities:
            for abn in scene.abnormalities:
                if abn.get("severity") in ("attention", "concern"):
                    section += f"[{abn['severity'].upper()}] {abn.get('description', '')}\n"
        return section
    except Exception:
        return ""


def build_conference_context(
    conference_name: str,
    max_duration_minutes: int = 60,
) -> str:
    """Prompt pour le mode conférence — Luna écoute et prend des notes, ne parle pas."""
    return f"""Tu es Luna, l'IA YAWatch. Tu es en mode OBSERVATION lors d'une reunion.

Reunion : {conference_name}
Duree maximale : {max_duration_minutes} minute(s).

=== TON ROLE ===
Tu ecoutes la reunion en silence et tu prends des notes en temps reel via create_note().
Tu uses create_note() pour chaque point cle : decision prise, action a faire, chiffre important.

=== REGLES ABSOLUES ===
- NE PARLE PAS dans la conference. Reste silencieuse.
- NE REPONDS PAS aux questions de la reunion (tu n'es pas participante).
- Appelle UNIQUEMENT create_note() — jamais send_sms, call_contact ou invite_visio.
- Une note toutes les 3-5 minutes maximum. Ne surcharge pas.

=== FORMAT DES NOTES ===
- Titre court : contexte ou decision
- Contenu : fait factuel, concis, sans interpretation

Quand la reunion se termine ou que tu atteins la duree max, appelle hang_up()."""


def build_voice_context(
    subscriber_name: str = "l'utilisateur",
    memory_manager=None,
    max_duration_minutes: int = 15,
    mission: str = "",
    contact_name: str = "",
    redis_client=None,
    tenant_id: int = 0,
    language: str = "fr",
) -> str:
    """
    Construit le contexte Luna pour les appels vocaux.
    Charge le profil, les contacts et les instructions actives depuis Redis.
    """
    contacts_section = "Aucun contact de confiance enregistre."
    instructions_section = ""
    profile_section = ""

    if memory_manager:
        # Contacts
        try:
            contacts = memory_manager.list_trusted_contacts()
            if contacts:
                lines = []
                for c in contacts:
                    first_name = c.name.split()[0] if c.name else "Contact"
                    relation = c.relation or "proche"
                    lines.append(f"- {first_name} ({relation})")
                contacts_section = "\n".join(lines)
        except Exception:
            pass

        # Instructions actives de l'editeur
        try:
            instructions = memory_manager.list_active_instructions()
            if instructions:
                instr_lines = []
                for instr in instructions[:10]:  # max 10 pour ne pas surcharger
                    desc = getattr(instr, "description", str(instr))
                    instr_lines.append(f"- {desc}")
                instructions_section = "\n=== INSTRUCTIONS DE L'EDITEUR (a suivre) ===\n" + "\n".join(instr_lines)
        except Exception:
            pass

        # Profil souscripteur
        try:
            profile = memory_manager.get_subscriber_profile()
            if profile:
                parts = []
                fn = getattr(profile, "first_name", "")
                ln = getattr(profile, "last_name", "")
                if fn or ln:
                    parts.append(f"Nom: {fn} {ln}".strip())
                age = getattr(profile, "age", "") or getattr(profile, "birth_date", "")
                if age:
                    parts.append(f"Age/Naissance: {age}")
                autonomy = getattr(profile, "autonomy", "")
                if autonomy:
                    parts.append(f"Autonomie: {autonomy}")
                family = getattr(profile, "family_status", "")
                if family:
                    parts.append(f"Situation: {family}")
                rules = getattr(profile, "permanent_rules", "")
                if rules:
                    parts.append(f"Regles permanentes: {rules}")
                if parts:
                    profile_section = "\n=== PROFIL DU SOUSCRIPTEUR ===\n" + "\n".join(parts)
        except Exception:
            pass

    mission_section = ""
    if mission:
        mission_section = f"""
=== MISSION DE CET APPEL ===
{mission}
Tu dois accomplir cette mission puis raccrocher poliment. Reste focalisee sur cette mission."""

    # Determiner qui est au telephone
    if contact_name:
        interlocutor_section = (
            f"Tu es en appel telephonique avec {contact_name}.\n"
            f"C'est {subscriber_name} qui t'a demande de passer cet appel a {contact_name}.\n"
            f"IMPORTANT : La personne au telephone est {contact_name}, PAS {subscriber_name}. "
            f"Adresse-toi a {contact_name} par son prenom."
        )
    elif mission:
        interlocutor_section = (
            f"Tu es en appel telephonique avec un interlocuteur.\n"
            f"C'est {subscriber_name} qui t'a demande de passer cet appel."
        )
    else:
        interlocutor_section = (
            f"Tu es en appel telephonique avec {subscriber_name}.\n"
            f"Adresse-toi a {subscriber_name} par son prenom."
        )

    return f"""Tu es Luna, l'assistante IA personnelle de YAWatch.
{interlocutor_section}
Tu es une compagne bienveillante et chaleureuse, disponible 24h/24.
Tu parles en francais avec un ton rassurant, moderne et empathique.
Tes reponses sont concises et naturelles - c'est un appel vocal, pas un email.

IMPORTANT : Cet appel est limite a {max_duration_minutes} minute(s). Quand tu as fini ta mission ou que le temps est presque ecoule, dis au revoir chaleureusement puis appelle la fonction hang_up pour raccrocher REELLEMENT.

=== REGLE ABSOLUE : ACTIONS REELLES ===
Quand tu dis que tu fais quelque chose, tu DOIS le faire pour de vrai en appelant la fonction correspondante.
- "je raccroche" → tu DOIS appeler hang_up() immediatement
- "je t'envoie un SMS" → tu DOIS appeler send_sms()
- "je vais noter ca" → tu DOIS appeler create_note()
- "je vais l'appeler" → tu DOIS appeler call_contact()
Ne dis JAMAIS que tu fais une action sans appeler la fonction. Tes paroles DOIVENT correspondre a tes actes.
{mission_section}

=== CE QUE TU PEUX FAIRE ===
- Discuter, ecouter, rassurer, tenir compagnie
- Envoyer un SMS a un contact de confiance (fonction send_sms)
- Envoyer un email (fonction send_email)
- Appeler un contact par telephone (fonction call_contact)
- Inviter en visioconference (fonction invite_visio)
- Creer un rappel ou une instruction (fonction create_instruction)
- Prendre une note (fonction create_note)
- Generer un document (fonction generate_document)
- Alerter les contacts d'urgence (fonction alert_contacts)
- Lister les contacts (fonction get_contacts)
- Chercher sur Internet : restaurants, vols, hotels, services, infos (fonction search_web, search_places)
- Donner la meteo en temps reel (fonction get_weather)
- Donner les actualites du jour (fonction get_news)
- Consulter une page web pour extraire des infos precises (fonction get_page_info)
- Chercher des vols avec prix et horaires (fonction search_flights)
- Chercher des hotels avec prix et disponibilites (fonction search_hotels)
- Trouver un restaurant avec adresse et telephone (fonction book_restaurant)
- Voir qui est en ligne parmi les amis Luna (fonction get_friends_online)
- Envoyer un message prive a un ami Luna (fonction send_dm_voice)
- Donner le code ami du souscripteur (fonction get_my_friend_code)
- Regarder ce que la camera voit (fonction look_around — si camera activee)

=== CONCIERGERIE — REGLE D'OR ===
Tu fais TOUT le travail de recherche. Tu presentes les meilleures options avec les details (prix, lien, adresse, telephone, horaires).
Le souscripteur n'a plus qu'a choisir et agir (cliquer sur le lien, appeler, se deplacer).
Tu ne geres JAMAIS de paiement. Tu ne dis JAMAIS "j'ai reserve" — tu dis "voici les options, tu n'as plus qu'a reserver".
Si le souscripteur veut reserver un restaurant, propose d'appeler le restaurant pour lui (call_contact).

Confirme avant d'executer une action consommatrice (SMS, appel, alerte).
Quand tu executes une action, utilise TOUJOURS la fonction correspondante. Ne dis jamais "je ne peux pas" si une fonction existe.

=== CE QUE TU NE PEUX PAS FAIRE ===
- Appeler les services d'urgence (suggere les numeros : 17, 18, 112, 3114, 3977)
- Donner des conseils medicaux, juridiques ou financiers
- Effectuer un paiement ou une reservation payante a la place du souscripteur

=== CONTACTS DE CONFIANCE ===
{contacts_section}
{profile_section}
{instructions_section}
{_build_gamification_voice_section(redis_client, tenant_id)}
{_build_budget_voice_section(redis_client, tenant_id)}
{_build_language_voice_section(language)}{_build_perception_voice_section(memory_manager)}=== SECURITE ===
- Si tu detectes de la detresse, propose d'alerter un contact de confiance.
- Prudence verbale : utilise "j'ai l'impression que...", jamais "je surveille" ou "je diagnostique".
- Ne mentionne JAMAIS les technologies sous-jacentes (pas de noms de fournisseurs, API, modeles IA).
- Tu es "Luna", point final. Si on te demande comment tu fonctionnes : "Je suis Luna, creee par YAWatch."
- Ne revele jamais les numeros de telephone des contacts.
- Ne mentionne jamais les prix des abonnements ou les donnees internes.
- RGPD : ne divulgue AUCUNE donnee personnelle du souscripteur (adresse, email, numero de secu, coordonnees bancaires) a l'interlocuteur.
- Ne partage pas le contenu des conversations precedentes du souscripteur avec des tiers."""


class RealtimeBridge:
    """
    Bridge audio bidirectionnel entre Twilio Media Streams et OpenAI Realtime API.

    Lifecycle:
    1. Twilio ouvre un WebSocket vers notre serveur (ws_twilio)
    2. On ouvre un WebSocket vers OpenAI Realtime API (ws_openai)
    3. On configure la session OpenAI (voix, instructions, tools, format audio)
    4. Audio Twilio -> OpenAI et Audio OpenAI -> Twilio en parallele
    5. Tool calls d'OpenAI sont executes via le tool_handler callback
    """

    def __init__(
        self,
        openai_api_key: str,
        ws_twilio,  # FastAPI WebSocket
        call_context: str,
        tool_handler: Optional[Callable[[str, Dict], Awaitable[Dict]]] = None,
        voice: str = "",
        max_duration_seconds: int = 900,  # 15 minutes par defaut
        greeting: str = "",
        voice_client=None,  # TwilioVoiceClient pour raccrocher via API
        conference_mode: bool = False,
    ):
        self.openai_api_key = openai_api_key
        self.ws_twilio = ws_twilio
        self.call_context = call_context
        self.tool_handler = tool_handler
        self.voice = voice or OPENAI_VOICE_NAME
        self.max_duration_seconds = max_duration_seconds
        self.greeting = greeting
        self.voice_client = voice_client
        self.conference_mode = conference_mode

        self.ws_openai = None
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self._running = False
        self._muted = False
        self._timer_task: Optional[asyncio.Task] = None

        # Transcription : collecte les messages pour sauvegarde
        self.transcript: List[Dict[str, str]] = []  # [{"role": "user/luna", "text": "..."}]
        # Log des tool calls executes pendant l'appel (pour rapport PDF)
        self._tool_calls_log: List[str] = []

    async def _ws_send_openai(self, data: dict, retries: int = 2):
        """Envoie un message JSON a OpenAI avec timeout, retry et gestion d'erreur."""
        if not self.ws_openai or not self._running:
            return False
        payload = json.dumps(data)
        for attempt in range(retries + 1):
            try:
                await asyncio.wait_for(self.ws_openai.send(payload), timeout=15.0)
                return True
            except asyncio.TimeoutError:
                if attempt < retries:
                    logger.warning(f"OpenAI send timeout (attempt {attempt+1}/{retries+1}), retrying...")
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"OpenAI send timeout after {retries+1} attempts")
                    self._running = False
                    return False
            except Exception as e:
                logger.error(f"OpenAI send error: {e}")
                self._running = False
                return False
        return False

    async def _ws_send_twilio(self, data: dict, retries: int = 1):
        """Envoie un message JSON a Twilio avec timeout, retry et gestion d'erreur."""
        if not self.ws_twilio or not self._running:
            return False
        payload = json.dumps(data)
        for attempt in range(retries + 1):
            try:
                await asyncio.wait_for(self.ws_twilio.send_text(payload), timeout=15.0)
                return True
            except asyncio.TimeoutError:
                if attempt < retries:
                    logger.warning(f"Twilio send timeout (attempt {attempt+1}/{retries+1}), retrying...")
                    await asyncio.sleep(0.3)
                else:
                    logger.error(f"Twilio send timeout after {retries+1} attempts")
                    self._running = False
                    return False
            except Exception as e:
                logger.error(f"Twilio send error: {e}")
                self._running = False
                return False
        return False

    async def run(self):
        """Boucle principale du bridge. Bloque jusqu'a la fin de l'appel.
        Protege par semaphore pour limiter les connexions OpenAI simultanees."""
        global _active_bridges
        async with _realtime_semaphore:
            _active_bridges += 1
            logger.info(f"RealtimeBridge started (active: {_active_bridges})")
            self._running = True
            try:
                # Ouvre la connexion vers OpenAI Realtime (timeout 10s)
                # websockets 13+ : extra_headers -> additional_headers
                _ws_version = int(websockets.__version__.split(".")[0])
                _headers_kwarg = "additional_headers" if _ws_version >= 13 else "extra_headers"
                _ws_kwargs = {
                    _headers_kwarg: {
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "OpenAI-Beta": "realtime=v1",
                    },
                    "close_timeout": 5,
                    "ping_interval": 20,
                    "ping_timeout": 10,
                }
                self.ws_openai = await asyncio.wait_for(
                    websockets.connect(OPENAI_REALTIME_URL, **_ws_kwargs),
                    timeout=10.0,
                )
                logger.info("OpenAI Realtime WebSocket connected")

                # Configure la session
                await self._configure_session()

                # Lance le timer de duree max
                self._timer_task = asyncio.create_task(self._duration_timer())

                # Lance les deux relais en parallele
                await asyncio.gather(
                    self._relay_twilio_to_openai(),
                    self._relay_openai_to_twilio(),
                )

            except asyncio.TimeoutError:
                logger.error("OpenAI Realtime connection timeout (10s)")
            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"OpenAI WebSocket closed: {e}")
            except OSError as e:
                logger.error(f"Network error connecting to OpenAI: {e}")
            except Exception as e:
                logger.error(f"RealtimeBridge error: {e}")
            finally:
                self._running = False
                _active_bridges -= 1
                logger.info(f"RealtimeBridge ended (active: {_active_bridges})")
                if self._timer_task:
                    self._timer_task.cancel()
                    try:
                        await self._timer_task
                    except asyncio.CancelledError:
                        pass
                await self._cleanup()

    async def _duration_timer(self):
        """Coupe l'appel apres max_duration_seconds."""
        try:
            await asyncio.sleep(self.max_duration_seconds)
            logger.info(f"Voice call max duration reached ({self.max_duration_seconds}s)")
            self._running = False
            # Raccrocher reellement via l'API Twilio
            if self.voice_client and self.call_sid:
                try:
                    await self.voice_client.terminate_call_async(self.call_sid)
                except Exception as e:
                    logger.warning(f"Could not terminate call via Twilio API: {e}")
        except asyncio.CancelledError:
            pass

    async def _configure_session(self):
        """Envoie session.update pour configurer la voix, les instructions et les tools."""
        if self.conference_mode:
            # Fix 1+3: texte uniquement (zéro audio sortant), VAD haute sensibilité
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "instructions": self.call_context,
                    "input_audio_format": "g711_ulaw",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.9,
                        "silence_duration_ms": 2000,
                    },
                    "tools": VOICE_TOOLS,
                },
            }
            logger.info("OpenAI Realtime session configured (conference/text-only mode)")
        else:
            session_config = {
                "type": "session.update",
                "session": {
                    "voice": self.voice,
                    "instructions": self.call_context,
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "semantic_vad",
                        "eagerness": "medium",
                    },
                    "tools": VOICE_TOOLS,
                },
            }
            logger.info("OpenAI Realtime session configured")
        await self._ws_send_openai(session_config)

    async def force_mute(self):
        """Coupe immédiatement la parole de Luna et bloque toute future sortie audio."""
        self._muted = True
        if self._running and self.ws_openai:
            await self._ws_send_openai({"type": "response.cancel"})
            if self.stream_sid:
                await self._ws_send_twilio({"event": "clear", "streamSid": self.stream_sid})
        logger.info(f"[{self.call_sid}] Bridge force-muted")

    async def _send_greeting(self):
        """Envoie un message initial pour que Luna salue le souscripteur."""
        # Injecte un message "utilisateur" fictif pour declencher la reponse de Luna
        greeting_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": self.greeting,
                    }
                ],
            },
        }
        await self._ws_send_openai(greeting_event)
        # Declenche la reponse vocale
        await self._ws_send_openai({"type": "response.create"})
        logger.info("Greeting sent to OpenAI Realtime")

    async def _relay_twilio_to_openai(self):
        """Recoit l'audio de Twilio et l'envoie a OpenAI."""
        try:
            async for message in self.ws_twilio.iter_text():
                if not self._running:
                    break

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                event = data.get("event", "")

                if event == "connected":
                    logger.info("Twilio Media Stream connected")

                elif event == "start":
                    self.stream_sid = data.get("streamSid", "")
                    start_info = data.get("start", {})
                    self.call_sid = start_info.get("callSid", "")
                    logger.info(f"Twilio stream started: streamSid={self.stream_sid}, callSid={self.call_sid}")
                    # Envoie le greeting initial pour que Luna parle en premier
                    if self.greeting and self.ws_openai:
                        await self._send_greeting()

                elif event == "media":
                    # Audio entrant du telephone -> OpenAI
                    payload = data.get("media", {}).get("payload", "")
                    if payload and self.ws_openai:
                        audio_event = {
                            "type": "input_audio_buffer.append",
                            "audio": payload,  # deja en base64 g711_ulaw
                        }
                        await self._ws_send_openai(audio_event)

                elif event == "stop":
                    logger.info("Twilio stream stopped")
                    self._running = False
                    break

        except Exception as e:
            if self._running:
                logger.error(f"Twilio relay error: {e}")
            self._running = False

    async def _relay_openai_to_twilio(self):
        """Recoit l'audio d'OpenAI et l'envoie a Twilio."""
        try:
            async for message in self.ws_openai:
                if not self._running:
                    break

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                event_type = data.get("type", "")

                if event_type == "session.created":
                    logger.info("OpenAI Realtime session created")

                elif event_type == "session.updated":
                    logger.info("OpenAI Realtime session updated")

                elif event_type == "response.created":
                    # Fix 4: annuler immédiatement toute réponse si muted
                    if self._muted:
                        await self._ws_send_openai({"type": "response.cancel"})

                elif event_type == "response.audio.delta":
                    # Audio de Luna -> Twilio
                    if self._muted:
                        # Fix 4: audio bloqué — vider le buffer Twilio et annuler
                        if self.stream_sid:
                            await self._ws_send_twilio({"event": "clear", "streamSid": self.stream_sid})
                        await self._ws_send_openai({"type": "response.cancel"})
                        continue
                    audio_delta = data.get("delta", "")
                    if audio_delta and self.stream_sid:
                        twilio_msg = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {
                                "payload": audio_delta,  # base64 g711_ulaw
                            },
                        }
                        await self._ws_send_twilio(twilio_msg)

                elif event_type == "input_audio_buffer.speech_started":
                    # L'utilisateur a commence a parler -> interrompre Luna
                    logger.info(f"[{self.call_sid}] User speech started — interrupting Luna")
                    # Envoyer clear pour arreter le playback Twilio
                    if self.stream_sid:
                        clear_msg = {
                            "event": "clear",
                            "streamSid": self.stream_sid,
                        }
                        clear_ok = await self._ws_send_twilio(clear_msg)
                        if not clear_ok:
                            logger.warning(f"[{self.call_sid}] Failed to clear Twilio audio")
                    # Annuler la reponse en cours d'OpenAI
                    cancel_ok = await self._ws_send_openai({"type": "response.cancel"})
                    if not cancel_ok and self._running:
                        logger.warning(f"[{self.call_sid}] Failed to cancel OpenAI response")

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # Transcription de ce que le souscripteur a dit
                    text = data.get("transcript", "").strip()
                    if text:
                        self.transcript.append({"role": "user", "text": text})
                        logger.info(f"[{self.call_sid}] USER: {text[:120]}")

                elif event_type == "response.audio_transcript.done":
                    # Transcription de ce que Luna a dit
                    text = data.get("transcript", "").strip()
                    if text:
                        self.transcript.append({"role": "luna", "text": text})
                        logger.info(f"[{self.call_sid}] LUNA: {text[:120]}")

                elif event_type == "response.function_call_arguments.done":
                    # Tool call ! Executer la fonction
                    await self._handle_tool_call(data)

                elif event_type == "error":
                    error_info = data.get("error", {})
                    error_code = error_info.get("code", "")
                    if error_code == "response_cancel_not_active":
                        logger.debug("OpenAI Realtime: cancel ignored (no active response)")
                    else:
                        logger.error(f"OpenAI Realtime error: {error_info}")
                        # Erreurs fatales = fermer le bridge proprement
                        _fatal_codes = {
                            "invalid_request_error", "authentication_failed",
                            "rate_limit_exceeded", "server_error",
                        }
                        if error_code in _fatal_codes:
                            logger.error(f"Fatal OpenAI error ({error_code}), closing bridge")
                            self._running = False
                            break

        except websockets.exceptions.ConnectionClosed as e:
            if self._running:
                logger.info(f"OpenAI WebSocket closed: {e}")
            self._running = False
        except Exception as e:
            if self._running:
                logger.error(f"OpenAI relay error: {e}")
            self._running = False

    async def _handle_tool_call(self, data: Dict):
        """Execute un tool call et renvoie le resultat a OpenAI."""
        call_id = data.get("call_id", "")
        function_name = data.get("name", "")
        arguments_str = data.get("arguments", "{}")

        try:
            args = json.loads(arguments_str)
        except json.JSONDecodeError:
            args = {}

        logger.info(f"Voice tool_call: {function_name}({args})")

        # --- hang_up: handled directly by the bridge ---
        if function_name == "hang_up":
            reason = args.get("reason", "fin de conversation")
            logger.info(f"[{self.call_sid}] HANG_UP called: {reason}")
            self._tool_calls_log.append(f"hang_up: ok — {reason}")
            # Send success back to OpenAI so it doesn't generate more speech
            tool_response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"status": "ok", "message": "Appel termine."}, ensure_ascii=False),
                },
            }
            await self._ws_send_openai(tool_response)
            # Brief delay so farewell audio finishes playing
            await asyncio.sleep(3)
            self._running = False
            # Raccrocher reellement via l'API Twilio
            if self.voice_client and self.call_sid:
                try:
                    await self.voice_client.terminate_call_async(self.call_sid)
                except Exception as e:
                    logger.warning(f"hang_up: could not terminate via Twilio API: {e}")
            return

        # Executer via le callback (avec timeout 45s pour les tools lents)
        import time as _time
        _tool_start = _time.time()
        result = {"status": "error", "message": "Fonction non disponible"}
        if self.tool_handler:
            try:
                result = await asyncio.wait_for(
                    self.tool_handler(function_name, args), timeout=45.0
                )
            except asyncio.TimeoutError:
                _elapsed = _time.time() - _tool_start
                logger.error(f"Tool handler timeout ({function_name}) after {_elapsed:.1f}s")
                result = {"status": "error", "message": "L'operation a pris trop de temps. Reessaie."}
            except Exception as e:
                _elapsed = _time.time() - _tool_start
                logger.error(f"Tool handler error ({function_name}) after {_elapsed:.1f}s: {e}")
                result = {"status": "error", "message": str(e)}
        _tool_elapsed = _time.time() - _tool_start
        logger.info(f"Tool {function_name} completed in {_tool_elapsed:.1f}s → {result.get('status', '?')}")

        # Anti-hallucination: if action tool failed, make the error output
        # very explicit so the LLM cannot pretend it succeeded
        _ACTION_TOOLS = {"call_contact", "send_sms", "send_email", "alert_contacts",
                         "request_payment", "invite_visio", "generate_document"}
        if result.get("status") == "error" and function_name in _ACTION_TOOLS:
            result["IMPORTANT"] = (
                f"L'action {function_name} a ECHOUE. Tu DOIS informer le souscripteur "
                f"de l'echec. N'invente RIEN. Ne pretends PAS que l'action a reussi."
            )

        # Envoyer le resultat a OpenAI (avec verification du succes)
        tool_response = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False),
            },
        }
        sent_ok = await self._ws_send_openai(tool_response)
        if sent_ok:
            await self._ws_send_openai({"type": "response.create"})
            logger.info(f"Tool {function_name} result delivered to OpenAI")
        else:
            logger.error(f"Tool {function_name} result FAILED to send to OpenAI (bridge may be dead)")

        # Log pour le rapport PDF
        status = result.get("status", "unknown")
        msg = result.get("message", "")[:100]
        self._tool_calls_log.append(f"{function_name}: {status} — {msg}")

    def get_transcript_text(self) -> str:
        """Retourne la transcription formatee."""
        lines = []
        for entry in self.transcript:
            role = "Souscripteur" if entry["role"] == "user" else "Luna"
            lines.append(f"{role}: {entry['text']}")
        return "\n".join(lines)

    async def _cleanup(self):
        """Ferme proprement les connexions."""
        self._running = False
        if self.ws_openai:
            try:
                await self.ws_openai.close()
            except Exception:
                pass
        logger.info(f"RealtimeBridge cleanup done ({len(self.transcript)} transcript entries)")
