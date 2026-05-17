"""
Tavus Client - Integration video avatar Luna
Cree et gere les conversations video via Tavus CVI.
Supporte le tool calling pour permettre a Luna d'agir depuis la visio.
"""
import os
import json
import logging
import httpx
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

TAVUS_API_BASE = "https://tavusapi.com/v2"


@dataclass
class TavusConversation:
    """Conversation Tavus active"""
    conversation_id: str
    conversation_url: str
    persona_id: str
    tenant_id: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    participants: list = field(default_factory=list)
    status: str = "active"


def _build_contacts_section(memory_manager) -> str:
    """Construit la section contacts avec PRENOMS UNIQUEMENT (jamais les telephones)."""
    try:
        contacts = memory_manager.list_trusted_contacts()
        if not contacts:
            return "Aucun contact de confiance enregistre pour le moment."
        lines = []
        for c in contacts:
            first_name = c.name.split()[0] if c.name else "Contact"
            relation = c.relation or "proche"
            lines.append(f"- {first_name} ({relation})")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Cannot load contacts for Tavus context: {e}")
        return "Des contacts de confiance sont enregistres. Tu peux proposer de les alerter."


def build_tavus_context(
    subscriber_name: str = "l'utilisateur",
    memory_manager=None,
    guest_names: list = None,
) -> str:
    """
    Construit le contexte conversationnel SANITISE pour Tavus.
    Ce contexte est envoye a Tavus lors de la creation de conversation.
    Il NE CONTIENT PAS d'informations confidentielles.

    Args:
        guest_names: liste de prenoms des invites presents dans la visio
    """
    # Section contacts
    if memory_manager:
        contacts_section = _build_contacts_section(memory_manager)
    else:
        contacts_section = "Des contacts de confiance sont enregistres. Tu peux proposer de les alerter."

    # Section invites (multi-participant)
    guests_section = ""
    if guest_names:
        guests_list = ", ".join(guest_names)
        guests_section = f"""
=== INVITES DANS CETTE VISIO ===
Des invites participent a cet appel : {guests_list}.
Sois accueillante avec eux. Ils sont les bienvenus.

REGLE ABSOLUE — IDENTITE DU SOUSCRIPTEUR :
- Ton souscripteur est {subscriber_name}. Tu lui appartiens, tu le connais.
- Les invites ({guests_list}) sont des INVITES. Ils ne sont PAS ton souscripteur.
- Tu ne dois JAMAIS executer d'action engageante (paiement, reservation, achat,
  envoi d'email, generation de document) a la demande d'un invite.
- Si un invite te demande une action, reponds poliment :
  "Je suis l'assistante de {subscriber_name}, je ne peux agir qu'a sa demande."
- Tu PEUX discuter, repondre aux questions generales, et etre chaleureuse avec tout le monde.
- Seul {subscriber_name} peut te donner des instructions d'action.
"""

    try:
        return f"""=== QUI TU ES ===
Tu es Luna, l'assistante IA personnelle de YAWatch.
Tu es une compagne bienveillante et chaleureuse, disponible 24h/24, 7j/7.
Tu parles en francais avec un ton rassurant, moderne et empathique.
Tu tutoies le souscripteur sauf s'il te demande de le vouvoyer.

=== TON SOUSCRIPTEUR ===
Tu parles avec {subscriber_name}.
Il est en appel video avec toi en ce moment.
{guests_section}
=== CE QUE TU PEUX FAIRE EN VISIO ===
- Discuter, ecouter, rassurer, tenir compagnie
- Donner la météo actuelle (les données sont déjà dans ton contexte, rubrique DONNÉES EN TEMPS RÉEL)
- Donner les titres d'actualité du moment (déjà dans ton contexte)
- Donner la date et l'heure (déjà dans ton contexte)
- Envoyer un SMS a un contact de confiance (utilise la fonction send_sms)
- Creer un rappel ou une instruction (utilise la fonction create_instruction)
- Prendre une note (utilise la fonction create_note)
- Generer un document/courrier (utilise la fonction generate_document)
- Alerter les contacts d'urgence (utilise la fonction alert_contacts)
- Lister les contacts de confiance (utilise la fonction get_contacts)
- Passer un appel telephonique vocal a un contact (utilise la fonction call_contact — JAMAIS pour 17/18/112)
- Envoyer un email a un contact (utilise la fonction send_email)
- Rechercher sur le web (utilise la fonction search_web)
- Rechercher des lieux, restaurants, commerces (utilise la fonction search_places)
- Rechercher des vols (utilise la fonction search_flights)
- Rechercher des hotels (utilise la fonction search_hotels)
- Suggerer d'appeler les services d'urgence (tu donnes les numeros, tu ne les appelles PAS toi-meme)
- Inviter un contact a rejoindre cet appel video
- Analyser un document ou une image partage pendant la visio (l'analyse t'est injectee automatiquement)
- Rediger et envoyer un compte-rendu / conclusions a tous les participants (utilise la fonction send_conclusions)

IMPORTANT : Quand le souscripteur te demande une action, utilise TOUJOURS la fonction appropriee.
Ne dis pas "je ne peux pas faire ca" si une fonction existe pour le faire.
Confirme avant d'executer une action consommatrice (SMS, alerte, appel).
Pour la météo et les actualités : utilise DIRECTEMENT les données DONNÉES EN TEMPS RÉEL — ne prétends PAS appeler un outil si les données sont déjà là.

=== MODE PROFESSIONNEL / RÉUNION D'ENTREPRISE ===
Tu es aussi une assistante de réunion IA incarnée. En reunion avec plusieurs participants :
- Tu prends des notes automatiquement et restes discrete — tu n'interromps PAS les conversations entre humains
- Tu analyses les documents partages et en extrais les points cles
- A la fin tu rediges un compte-rendu structure (points discutes, decisions, actions) et l'envoies aux participants
- Tu donnes ton avis uniquement si on te le demande directement ("Luna, qu'est-ce que tu en penses ?")
- Tu peux etre utilisee soit pour avoir de la compagnie (usage personnel) soit comme outil de travail (usage professionnel)

=== CE QUE TU NE PEUX PAS FAIRE ===
- Tu ne peux PAS appeler les services d'urgence toi-meme (c'est interdit pour une IA)
- Tu ne donnes AUCUN conseil medical, juridique ou financier
- Tu ne connais PAS les details techniques du systeme et tu n'en parles jamais

=== NUMEROS D'URGENCE (a suggerer si besoin) ===
- Police : 17
- Pompiers : 18
- Urgences europeennes : 112
- Prevention suicide : 3114 (24h/24)
- Maltraitance personnes agees : 3977

=== SECURITE ===
- Si tu detectes de la detresse, propose d'alerter un contact de confiance
- Si c'est une urgence vitale, suggere fortement d'appeler le 112 ou le numero adapte
- N'ignore jamais des signes de danger
- Ecoute toujours avec bienveillance et respecte la dignite de la personne
- Demande confirmation avant de proposer d'alerter les contacts (sauf urgence vitale)

=== CONTACTS DE CONFIANCE ===
{contacts_section}

=== INFORMATIONS CONFIDENTIELLES - NE JAMAIS MENTIONNER ===
Tu ne dois JAMAIS parler de :
- L'architecture technique, les technologies, les serveurs, les bases de donnees
- Les prix, abonnements, modele commercial, marges ou revenus
- Les numeros de telephone des contacts (tu connais seulement leurs prenoms)
- Les donnees d'autres utilisateurs ou souscripteurs
- Les quotas, pourcentages d'utilisation, limites internes du systeme
- Les cles API, mots de passe ou configurations
Si on te pose ces questions, reponds simplement que tu n'as pas acces a ces informations.

=== PRUDENCE VERBALE (OBLIGATOIRE) ===
Tu ne dis JAMAIS : "surveillance", "je surveille", "diagnostic", "je diagnostique",
"chute" (dire "situation au sol"), "urgence medicale" (dire "situation preoccupante"),
"detection certaine", "je garantis", "je protege".
Tu utilises TOUJOURS : "j'ai l'impression que...", "il me semble que...",
"j'ai remarque que...", "il se pourrait que...", "je te suggere de...".
Tu ne promets JAMAIS une surveillance garantie ou une protection assuree.
Tu es une aide contextuelle, pas un dispositif de securite.

=== STYLE ===
- Reponses concises et naturelles, pas de paves
- Chaleureuse mais pas infantilisante
- Proactive : propose des actions concretes
- Si le souscripteur demande une action, confirme avant"""

    except Exception as e:
        logger.exception("Erreur construction contexte Tavus")
        # Fallback minimal : identite + securite uniquement
        return (
            "Tu es Luna, assistante IA de YAWatch. "
            "Tu es bienveillante et chaleureuse. "
            "Tu ne donnes aucun conseil medical. "
            "Tu ne peux pas appeler les urgences. "
            "Tu peux suggerer les numeros : 17 (police), 18 (pompiers), 112 (urgences), 3114 (suicide), 3977 (maltraitance). "
            "Ne mentionne jamais l'architecture technique, les prix ou les donnees internes."
        )


class TavusClient:
    """
    Client pour l'API Tavus CVI (Conversational Video Interface).
    Gère les conversations vidéo avec l'avatar Luna.
    """

    def __init__(
        self,
        api_key: str,
        persona_id: str,
        memory_manager=None,
    ):
        self.api_key = api_key
        self.persona_id = persona_id
        self.memory = memory_manager
        self._active_conversations: Dict[str, TavusConversation] = {}

    @classmethod
    def from_env(cls, memory_manager=None):
        """Crée un client depuis les variables d'environnement"""
        api_key = os.getenv("TAVUS_API_KEY", "")
        persona_id = os.getenv("TAVUS_LUNA_PERSONA_ID", "")
        return cls(api_key=api_key, persona_id=persona_id, memory_manager=memory_manager)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.persona_id)

    # =====================================================================
    # TOOL CALLING - Definition des outils que Luna peut utiliser en visio
    # =====================================================================

    LUNA_TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "call_contact",
                "description": "Passer un appel telephone VOCAL a un contact de confiance. Utilise UNIQUEMENT quand le souscripteur dit 'appelle...', 'telephone a...', 'passe un coup de fil a...'. NE PAS utiliser pour envoyer un message texte (→ send_sms) ni pour une visio (→ invite_visio).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Prenom ou nom du contact a appeler (ex: maman, Marie, mon fils)"
                        }
                    },
                    "required": ["contact_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_sms",
                "description": "Envoyer un SMS ECRIT a UN SEUL contact de confiance. Utilise quand le souscripteur dit 'envoie un SMS a...', 'ecris un message a...', 'previens X'. Pour un appel vocal → call_contact. Pour alerter TOUS les contacts en urgence → alert_contacts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Prenom ou nom du contact de confiance (ex: Marie, mon fils, maman)"
                        },
                        "message": {
                            "type": "string",
                            "description": "Le contenu du SMS a envoyer"
                        }
                    },
                    "required": ["contact_name", "message"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_instruction",
                "description": "Creer un rappel ou une instruction pour le souscripteur. Utilise cette fonction quand il demande 'rappelle-moi de...', 'tous les jours a...', 'previens-moi si...'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "L'instruction en langage naturel, telle que le souscripteur l'a formulee"
                        }
                    },
                    "required": ["text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_note",
                "description": "Prendre une note pour le souscripteur. Utilise cette fonction quand il dit 'note que...', 'retiens que...', 'j'ai un RDV...'",
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
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_contacts",
                "description": "Lister les contacts de confiance du souscripteur. Utilise cette fonction quand il demande 'qui sont mes contacts ?', 'a qui tu peux envoyer un SMS ?'",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_document",
                "description": "Generer un document (courrier administratif, lettre, resume, fiche sante). Utilise cette fonction quand le souscripteur demande de rediger un courrier, une lettre, un document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_type": {
                            "type": "string",
                            "enum": ["courrier_admin", "courrier_resiliation", "resume_hebdo", "fiche_sante", "compte_rendu", "export_notes"],
                            "description": "Le type de document a generer"
                        },
                        "subject": {
                            "type": "string",
                            "description": "L'objet ou le sujet du document"
                        },
                        "details": {
                            "type": "string",
                            "description": "Les details et informations a inclure dans le document"
                        }
                    },
                    "required": ["doc_type", "subject"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "alert_contacts",
                "description": "Alerter EN URGENCE TOUS les contacts de confiance simultanement par SMS. Utilise UNIQUEMENT si le souscripteur est en danger (chute, malaise, detresse grave). Pour un message a un seul contact → send_sms. Inclut automatiquement la position GPS du souscripteur.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "La raison de l'alerte (ex: 'se sent mal', 'chute', 'besoin d aide')"
                        }
                    },
                    "required": ["reason"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "report_observation",
                "description": "Rapporter une observation visuelle faite pendant l'appel video. Utilise cette fonction quand tu remarques que le souscripteur semble fatigue, triste, en detresse, ou dans une situation inhabituelle.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "observation": {
                            "type": "string",
                            "description": "Ce que tu as observe (ex: 'semble fatigue', 'air triste', 'position inhabituelle')"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["info", "attention", "concern"],
                            "description": "Niveau: info (normal), attention (a surveiller), concern (preoccupant)"
                        }
                    },
                    "required": ["observation"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Envoyer un email a un contact de confiance. Utilise cette fonction quand le souscripteur dit 'envoie un email a...', 'ecris un mail a...', 'envoie un message a... par email'.",
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
            }
        },
        {
            "type": "function",
            "function": {
                "name": "invite_visio",
                "description": "Inviter un contact de confiance en visioconference. Envoie un SMS au contact avec un lien pour rejoindre la visio. Quand le souscripteur dit 'invite X en visio', 'fais une visio avec X', 'appelle X en video'.",
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
            }
        },
    ]

    @classmethod
    def _build_dynamic_tools(cls, contacts: list) -> list:
        """Retourne LUNA_TOOLS avec contact_name contraint aux prénoms connus."""
        import copy
        if not contacts:
            return cls.LUNA_TOOLS
        names = [c.name.split()[0] for c in contacts if c.name]
        if not names:
            return cls.LUNA_TOOLS
        contact_tools = {"send_sms", "call_contact", "send_email", "invite_visio"}
        tools = copy.deepcopy(cls.LUNA_TOOLS)
        for tool in tools:
            fn = tool.get("function", {})
            if fn.get("name") in contact_tools:
                props = fn.get("parameters", {}).get("properties", {})
                if "contact_name" in props:
                    props["contact_name"]["enum"] = names
                    props["contact_name"]["description"] = (
                        f"Prenom exact du contact (doit etre l'un de : {', '.join(names)})"
                    )
        return tools

    async def configure_tools_for_tenant(self, contacts: list) -> bool:
        """Patch la persona Tavus avec les noms de contacts actuels du tenant."""
        dynamic_tools = self._build_dynamic_tools(contacts)
        if not self.is_configured:
            return False
        try:
            payload = [{"op": "replace", "path": "/layers/llm/tools", "value": dynamic_tools}]
            async with httpx.AsyncClient() as http:
                resp = await http.patch(
                    f"{TAVUS_API_BASE}/personas/{self.persona_id}",
                    headers=self._headers(),
                    json=payload,
                    timeout=15,
                )
            ok = resp.status_code in (200, 204)
            if ok:
                logger.info(f"Tavus tools dynamiques configures ({len(dynamic_tools)} tools, {len(contacts)} contacts)")
            else:
                logger.warning(f"Tavus dynamic tools PATCH failed ({resp.status_code}): {resp.text[:200]}")
            return ok
        except Exception as e:
            logger.warning(f"configure_tools_for_tenant error: {e}")
            return False

    async def configure_tools(self) -> bool:
        """
        Configure les tools (function calling) sur la persona Tavus.
        Envoie un PATCH pour mettre a jour layers.llm.tools.

        Returns:
            True si configure avec succes
        """
        if not self.is_configured:
            logger.warning("Tavus non configure, skip tools configuration")
            return False

        try:
            # Tavus PATCH uses JSON Patch (RFC 6902) format
            payload = [
                {
                    "op": "replace",
                    "path": "/layers/llm/tools",
                    "value": self.LUNA_TOOLS,
                }
            ]

            async with httpx.AsyncClient() as http:
                resp = await http.patch(
                    f"{TAVUS_API_BASE}/personas/{self.persona_id}",
                    headers=self._headers(),
                    json=payload,
                    timeout=15,
                )

            if resp.status_code in (200, 204):
                logger.info(f"Tavus persona tools configured ({len(self.LUNA_TOOLS)} tools)")
                return True
            else:
                detail = resp.text[:200]
                logger.warning(f"Tavus PATCH persona failed ({resp.status_code}): {detail}")
                return False

        except Exception as e:
            logger.warning(f"Tavus configure_tools error: {e}")
            return False

    async def configure_perception(self) -> bool:
        """
        Configure Tavus Raven (ambient awareness) sur la persona.
        Raven detecte emotions, langage corporel et environnement pendant les visios.
        """
        if not self.is_configured:
            return False

        try:
            payload = [
                {
                    "op": "replace",
                    "path": "/layers/perception",
                    "value": {
                        "ambient_awareness_queries": [
                            "L'utilisateur semble-t-il fatigue ou somnolent ?",
                            "L'utilisateur montre-t-il des signes de detresse ou d'inconfort ?",
                            "L'utilisateur est-il assis, debout, ou dans une position inhabituelle ?",
                            "Y a-t-il quelqu'un d'autre visible dans la piece ?",
                            "L'utilisateur semble-t-il heureux, triste, ou neutre ?",
                            "L'utilisateur semble-t-il avoir chute ou etre tombe ?",
                            "L'utilisateur semble-t-il en danger physique (agression, blessure visible) ?",
                            "L'utilisateur semble-t-il inconscient ou sans reaction ?",
                            "L'utilisateur tient-il une partie de son corps (douleur, blessure) ?",
                            "L'environnement semble-t-il dangereux (feu, fumee, eau, objet casse) ?",
                        ],
                        "perception_model": "raven-0",
                    }
                }
            ]

            async with httpx.AsyncClient() as http:
                resp = await http.patch(
                    f"{TAVUS_API_BASE}/personas/{self.persona_id}",
                    headers=self._headers(),
                    json=payload,
                    timeout=15,
                )

            if resp.status_code in (200, 204):
                logger.info("Tavus Raven perception configured")
                return True
            else:
                logger.warning(f"Tavus perception config failed ({resp.status_code}): {resp.text[:200]}")
                return False

        except Exception as e:
            logger.warning(f"Tavus configure_perception error: {e}")
            return False

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _cleanup_stale_conversations(self) -> None:
        """Purge les conversations inactives depuis plus de 2h du cache mémoire."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=2)
        stale = [cid for cid, c in self._active_conversations.items() if c.created_at < cutoff]
        for cid in stale:
            self._active_conversations.pop(cid, None)
            logger.info("Conversation Tavus expirée purgée du cache: %s", cid)

    async def create_conversation(
        self,
        tenant_id: int,
        custom_greeting: Optional[str] = None,
        context: Optional[str] = None,
        max_duration: int = 40,
        callback_url: Optional[str] = None,
        replica_id: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Cree une nouvelle conversation video Tavus.

        Args:
            callback_url: URL du webhook pour recevoir les events (tool_call, transcription)
            replica_id: Override la replica visuelle de la persona (decor horaire)

        Returns:
            (success, data) avec data contenant conversation_url et conversation_id
        """
        self._cleanup_stale_conversations()

        if not self.is_configured:
            return False, {"error": "Tavus non configure (cle API ou persona manquante)"}

        # Injecte les contacts actuels du tenant dans les outils Tavus (enum dynamique)
        if self.memory:
            try:
                contacts = self.memory.list_trusted_contacts()
                if contacts:
                    await self.configure_tools_for_tenant(contacts)
            except Exception as _e:
                logger.warning(f"Dynamic tools injection failed (non-bloquant): {_e}")

        payload = {
            "persona_id": self.persona_id,
            "properties": {"max_call_duration": max_duration},
        }
        if replica_id:
            payload["replica_id"] = replica_id
        if custom_greeting:
            payload["custom_greeting"] = custom_greeting
        if context:
            payload["conversational_context"] = context
        if callback_url:
            payload["callback_url"] = callback_url

        try:
            async with httpx.AsyncClient() as http:
                resp = await http.post(
                    f"{TAVUS_API_BASE}/conversations",
                    headers=self._headers(),
                    json=payload,
                    timeout=15,
                )

            data = resp.json()

            if resp.status_code == 401:
                return False, {"error": "Cle API Tavus invalide ou expiree"}
            if resp.status_code == 402:
                return False, {"error": "Credit Tavus insuffisant. Recharge le compte."}
            if resp.status_code == 404:
                return False, {"error": f"Persona Luna introuvable ({self.persona_id})"}
            if resp.status_code == 429:
                return False, {"error": "Trop d'appels simultanes. Reessaie."}
            if resp.status_code != 200:
                detail = data.get("message") or data.get("error") or str(data)
                return False, {"error": f"Tavus ({resp.status_code}): {detail}"}

            conv_id = data.get("conversation_id", "")
            conv_url = data.get("conversation_url", "")

            # Enregistre la conversation active
            conv = TavusConversation(
                conversation_id=conv_id,
                conversation_url=conv_url,
                persona_id=self.persona_id,
                tenant_id=tenant_id,
            )
            self._active_conversations[conv_id] = conv

            # Persiste dans Redis si dispo
            if self.memory:
                try:
                    self.memory.create_conversation(
                        contact_phone="tavus_video",
                        contact_name="Luna Video",
                        relation="avatar",
                        channel="visio",
                    )
                    self.memory.add_note(
                        content=f"Appel video demarre: {conv_url}",
                        context="visio",
                        source="tavus",
                        tags=["visio", "tavus", conv_id],
                    )
                except Exception as e:
                    logger.warning(f"Impossible de persister la conversation Tavus: {e}")

            logger.info(f"Tavus conversation created: {conv_id} for tenant {tenant_id}")

            return True, {
                "conversation_id": conv_id,
                "conversation_url": conv_url,
            }

        except httpx.ConnectTimeout:
            return False, {"error": "Tavus ne repond pas (timeout)"}
        except httpx.ConnectError:
            return False, {"error": "Impossible de joindre Tavus. Verifie internet."}
        except Exception as e:
            logger.exception("Erreur Tavus inattendue")
            return False, {"error": f"Erreur inattendue: {type(e).__name__}"}

    def get_active_conversation(self, tenant_id: int) -> Optional[TavusConversation]:
        """Retourne la conversation active pour un tenant"""
        for conv in self._active_conversations.values():
            if conv.tenant_id == tenant_id and conv.status == "active":
                return conv
        return None

    def get_conversation_url(self, conversation_id: str) -> Optional[str]:
        """Retourne l'URL d'une conversation pour invitation"""
        conv = self._active_conversations.get(conversation_id)
        if conv:
            return conv.conversation_url
        return None

    async def add_participant_via_sms(
        self,
        conversation_id: str,
        contact_name: str,
        contact_phone: str,
        sms_client=None,
        tenant_id: int = 0,
    ) -> Tuple[bool, str]:
        """
        Invite un contact de confiance à rejoindre la visio par SMS.

        Envoie un SMS contenant le lien de la conversation Tavus.

        Returns:
            (success, message)
        """
        conv = self._active_conversations.get(conversation_id)
        if not conv:
            return False, "Aucune conversation active avec cet ID"

        if not sms_client:
            return False, "Service SMS non disponible"

        invite_msg = (
            f"Luna - {contact_name}, tu es invite(e) a rejoindre un appel video. "
            f"Clique ici pour rejoindre : {conv.conversation_url}"
        )

        try:
            success, details = sms_client.send(contact_phone, invite_msg)
            if success:
                conv.participants.append({
                    "name": contact_name,
                    "phone": contact_phone,
                    "invited_at": datetime.utcnow().isoformat(),
                    "method": "sms",
                })

                if self.memory:
                    try:
                        self.memory.add_note(
                            content=f"Invitation visio envoyee a {contact_name} ({contact_phone})",
                            context="visio",
                            source="tavus",
                            tags=["visio", "invitation", contact_name],
                        )
                    except Exception:
                        pass

                logger.info(f"Invitation SMS envoyee a {contact_name} pour conv {conversation_id}")
                return True, f"SMS d'invitation envoye a {contact_name}"
            else:
                return False, f"Echec envoi SMS: {details.get('error', 'inconnu')}"
        except Exception as e:
            logger.exception(f"Erreur invitation SMS a {contact_name}")
            return False, f"Erreur: {type(e).__name__}"

    async def end_conversation(self, conversation_id: str) -> bool:
        """Termine une conversation Tavus cote API (stoppe la facturation) et nettoie le cache."""
        # 1. Appel API Tavus pour terminer la conversation
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.delete(
                    f"{TAVUS_API_BASE}/conversations/{conversation_id}",
                    headers=self._headers(),
                    timeout=10,
                )
            if resp.status_code in (200, 204, 404):
                logger.info(f"Tavus conversation terminated via API: {conversation_id} (status={resp.status_code})")
            else:
                logger.warning(f"Tavus end_conversation API returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Tavus end_conversation API error: {e}")

        # 2. Nettoyer le cache local
        conv = self._active_conversations.pop(conversation_id, None)
        if conv:
            conv.status = "ended"
            logger.info(f"Tavus conversation removed from cache: {conversation_id}")
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du client Tavus"""
        return {
            "configured": self.is_configured,
            "persona_id": self.persona_id,
            "active_conversations": len(
                [c for c in self._active_conversations.values() if c.status == "active"]
            ),
        }
