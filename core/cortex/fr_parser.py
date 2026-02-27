"""
PARSER FRANCAIS — Comprend ce que tu veux dire en francais.

Au lieu de taper /status ou LUNA BAN 185.x.x.x,
tu ecris comme tu parles:

  "comment va le serveur ?"        → STATUS
  "ya des attaques ?"              → THREATS
  "bloque l'ip 185.220.101.34"    → BAN 185.220.101.34
  "vire le client 5"              → KILL 5
  "ferme tout"                     → LOCK
  "c'est quoi les dernières erreurs" → ERRORS
  "fais un backup"                → BACKUP
  "montre les clients"            → CLIENTS
  "combien il reste au client 3"  → QUOTA 3
  "fiche du client 3"            → CLIENT 3
  "inscris marie@mail.fr premium Marie" → REGISTER
  "passe le 3 en premium"        → PLAN_SET 3 premium
  "dis a tous maintenance ce soir" → BROADCAST

2 couches:
  1. Pattern matching (instantane, gratuit, 90% des cas)
  2. Fallback GPT-4o-mini (si pattern pas trouve, ~0.001€/requete)
"""

import os
import re
import logging
from typing import Optional, Tuple

import httpx

logger = logging.getLogger("cortex.fr_parser")


# ──────────────────────────────────────────
# ALIASES FRANCAIS POUR COMMANDES
# ──────────────────────────────────────────

# Commandes en francais → commande systeme
FR_COMMAND_ALIASES = {
    # STATUS
    "etat": "STATUS", "état": "STATUS", "status": "STATUS",
    "statut": "STATUS", "situation": "STATUS",
    # HEALTH
    "sante": "HEALTH", "santé": "HEALTH", "health": "HEALTH",
    "systeme": "HEALTH", "système": "HEALTH",
    # THREATS
    "menaces": "THREATS", "attaques": "THREATS", "securite": "THREATS",
    "sécurité": "THREATS", "threats": "THREATS", "piratage": "THREATS",
    # CLIENTS
    "clients": "CLIENTS", "abonnes": "CLIENTS", "abonnés": "CLIENTS",
    "utilisateurs": "CLIENTS",
    # QUOTA
    "quota": "QUOTA", "consommation": "QUOTA", "conso": "QUOTA",
    # BAN
    "ban": "BAN", "bannir": "BAN", "bloquer": "BAN", "bloque": "BAN",
    "virer": "BAN", "blacklist": "BAN",
    # UNBAN
    "unban": "UNBAN", "debannir": "UNBAN", "débannir": "UNBAN",
    "debloquer": "UNBAN", "débloquer": "UNBAN",
    # BANNED
    "bannis": "BANNED", "banned": "BANNED", "blackliste": "BANNED",
    "bloquees": "BANNED", "bloquées": "BANNED",
    # LOCK
    "lock": "LOCK", "verrouiller": "LOCK", "fermer": "LOCK",
    "lockdown": "LOCK", "urgence": "LOCK",
    # UNLOCK
    "unlock": "UNLOCK", "deverrouiller": "UNLOCK", "déverrouiller": "UNLOCK",
    "ouvrir": "UNLOCK", "rouvrir": "UNLOCK",
    # SHIELD
    "bouclier": "SHIELD", "shield": "SHIELD",
    # KILL
    "kill": "KILL", "suspendre": "KILL", "couper": "KILL",
    "desactiver": "KILL", "désactiver": "KILL",
    # REVIVE
    "revive": "REVIVE", "reactiver": "REVIVE", "réactiver": "REVIVE",
    "remettre": "REVIVE",
    # BACKUP
    "backup": "BACKUP", "sauvegarde": "BACKUP", "sauvegarder": "BACKUP",
    # LOGS
    "logs": "LOGS", "evenements": "LOGS", "événements": "LOGS",
    "journal": "LOGS",
    # ERRORS
    "erreurs": "ERRORS", "errors": "ERRORS", "bugs": "ERRORS",
    "problemes": "ERRORS", "problèmes": "ERRORS",
    # DIGEST
    "digest": "DIGEST", "rapport": "DIGEST", "resume": "DIGEST",
    "résumé": "DIGEST", "bilan": "DIGEST",
    # CORTEX
    "cortex": "CORTEX", "cerveau": "CORTEX", "ia": "CORTEX",
    # HELP
    "aide": "HELP", "help": "HELP", "commandes": "HELP",
    # AUTH/TOTP
    "auth": "AUTH", "connexion": "AUTH", "login": "AUTH",
    "totp": "TOTP", "code": "TOTP",
    # RESTART
    "restart": "RESTART", "redemarrer": "RESTART", "redémarrer": "RESTART",
    "relancer": "RESTART",
    # PING
    "ping": "PING", "test": "PING", "allo": "PING",
    # UPTIME
    "uptime": "UPTIME",
    # REDIS
    "redis": "REDIS",
    # CONFIG
    "configuration": "CONFIG",
    # WHITELIST
    "whitelist": "WHITELIST",
    # SESSIONS
    "sessions": "SESSIONS", "connectes": "SESSIONS", "connectés": "SESSIONS",
    # PROCESSES
    "processus": "PROCESSES", "process": "PROCESSES", "top": "PROCESSES",
    # NETWORK
    "reseau": "NETWORK", "réseau": "NETWORK", "network": "NETWORK",
    "connexions": "NETWORK",
    # DISK
    "disque": "DISK", "disk": "DISK", "stockage": "DISK",
    # VERSION
    "version": "VERSION",
    # MAINTENANCE
    "maintenance": "MAINTENANCE",
    # ANNOUNCE
    "annonce": "ANNOUNCE", "annoncer": "ANNOUNCE", "diffuser": "ANNOUNCE",
    "communiquer": "ANNOUNCE",
    # MSG
    "message": "MSG", "ecrire": "MSG", "écrire": "MSG",
    # PURGE
    "purge": "PURGE", "purger": "PURGE", "nettoyer": "PURGE",
    "vider": "PURGE",
    # RATELIMIT
    "ratelimit": "RATELIMIT", "limite": "RATELIMIT",
    # STOP
    "stop": "STOP", "eteindre": "STOP", "éteindre": "STOP",
    "arreter": "STOP", "arrêter": "STOP",
    # REKEY
    "rekey": "REKEY",
    # WIPE
    "wipe": "WIPE", "effacer": "WIPE", "supprimer": "WIPE",
    # QUOTA_SET
    "quota_set": "QUOTA_SET",
    # QUOTA_RESET
    "quota_reset": "QUOTA_RESET",
    # WHITELIST_ADD
    "whitelist_add": "WHITELIST_ADD",
    # WHITELIST_DEL
    "whitelist_del": "WHITELIST_DEL",
    # AUDIT
    "audit": "AUDIT", "historique": "AUDIT", "piste": "AUDIT",
    "trace": "AUDIT", "actions": "AUDIT",
    # COUTS
    "couts": "COUTS", "coûts": "COUTS", "depenses": "COUTS",
    "dépenses": "COUTS", "costs": "COUTS", "facture": "COUTS",
    # EXPORT
    "export": "EXPORT", "exporter": "EXPORT", "pdf": "EXPORT",
    "telecharger": "EXPORT", "télécharger": "EXPORT",
    # CLIENT (fiche detaillee)
    "fiche": "CLIENT", "detail": "CLIENT", "détail": "CLIENT",
    "infos": "CLIENT", "profil": "CLIENT",
    # REGISTER (inscrire un client)
    "inscrire": "REGISTER", "inscrits": "REGISTER", "creer": "REGISTER",
    "créer": "REGISTER", "enregistrer": "REGISTER", "nouveau": "REGISTER",
    # PLAN_SET (changer plan)
    "plan": "PLAN_SET",
    # BROADCAST (message a tous)
    "broadcast": "BROADCAST",
}

# ──────────────────────────────────────────
# PATTERNS FRANCAIS (phrases completes)
# ──────────────────────────────────────────

# Chaque pattern: (regex, commande, groupe pour extraire l'argument)
# ORDRE IMPORTANT: les patterns specifiques AVANT les patterns generiques
FR_PATTERNS = [
    # ── PATTERNS SPECIFIQUES EN PREMIER ──

    # AUDIT (avant LOGS qui matchait "historique")
    (r"(journal|piste|trace)\s+(d.?)?(audit|actions?)", "AUDIT", None),
    (r"qui\s+a\s+fait\s+quoi", "AUDIT", None),
    (r"(dernieres?|dernières?)\s+(actions?|commandes?)", "AUDIT", None),
    (r"(historique|audit)\s+(des\s+)?(actions?|commandes?)", "AUDIT", None),
    (r"^audit\s*(\d*)$", "AUDIT", 1),

    # COUTS (avant DIGEST)
    (r"combien\s+(ca|ça)\s+(coute|coûte)", "COUTS", None),
    (r"(couts?|coûts?|depenses?|dépenses?)\s+(du\s+)?(mois|jour|semaine)?", "COUTS", None),
    (r"(combien|quel)\s+(on\s+)?(a\s+)?(depense|dépensé|paye|payé)", "COUTS", None),
    (r"factur(e|ation)", "COUTS", None),

    # EXPORT (avant DIGEST pour "genere un pdf")
    (r"(genere|génère|export|envoie|telecharge|télécharge)\s+(le\s+)?(pdf|document|fichier)", "EXPORT", None),
    (r"(export|pdf)\s+(audit|couts|coûts|complet|historique|depenses|dépenses)", "EXPORT", None),

    # PING (restrictif)
    (r"^(allo|ping|pong)$", "PING", None),
    (r"^t.?es?\s+la\s*\??$", "PING", None),
    (r"^tu\s+(repond|es\s+la|vis)", "PING", None),

    # UPTIME (avant STATUS qui matche "tourne")
    (r"(depuis\s+quand|combien\s+de\s+temps).*(tourne|marche|en\s+ligne|demarre|démarré)", "UPTIME", None),
    (r"^uptime$", "UPTIME", None),
    (r"(temps|duree|durée)\s+de\s+(fonctionnement|marche)", "UPTIME", None),

    # CORTEX (avant STATUS pour "comment va le cortex")
    (r"(etat|état)\s+(du\s+)?(cortex|cerveau|ia)\b", "CORTEX", None),
    (r"comment\s+va\s+(le\s+)?(cortex|cerveau|ia)\b", "CORTEX", None),
    (r"(le\s+)?cerveau\s+(va|tourne|marche)", "CORTEX", None),

    # REDIS (avant HEALTH pour "comment va redis")
    (r"(etat|état|info|details?)\s+(de\s+)?redis", "REDIS", None),
    (r"redis\s+(va|marche|status|info)", "REDIS", None),
    (r"comment\s+va\s+redis", "REDIS", None),
    (r"base\s+de\s+donn[ée]es", "REDIS", None),

    # CONFIG (avant HELP qui matche trop large)
    (r"\b(config|configuration)\b", "CONFIG", None),
    (r"(parametres?|paramètres?|reglages?|réglages?)\s+(du\s+)?(serveur|cortex|luna)?", "CONFIG", None),
    (r"(montre|affiche).*(config|reglages|réglages|parametres|paramètres)", "CONFIG", None),

    # DISK (avant HEALTH qui matchait "disque/place")
    (r"(espace|place)\s+(sur\s+le\s+)?(disque|stockage|disk)", "DISK", None),
    (r"(disque|stockage|disk)\s+(plein|libre|utilise)", "DISK", None),
    (r"combien\s+de\s+place\b", "DISK", None),
    (r"espace\s+disque", "DISK", None),

    # PROCESSES (avant HEALTH qui matchait "cpu")
    (r"(processus|process|top)\s+(en\s+cours|actifs?)?", "PROCESSES", None),
    (r"(qu.?est.?ce\s+qui|quoi\s+qui)\s+(tourne|utilise\s+(le\s+)?cpu)", "PROCESSES", None),
    (r"(charge|utilisation)\s+(du\s+)?(cpu|processeur)", "PROCESSES", None),

    # SESSIONS (avant STATUS)
    (r"qui\s+est\s+connect[ée]", "SESSIONS", None),
    (r"sessions?\s+(actives?|en\s+cours)", "SESSIONS", None),
    (r"qui\s+utilise\s+le\s+serveur", "SESSIONS", None),
    (r"combien\s+de\s+(gens|personnes)\s+connect", "SESSIONS", None),

    # NETWORK
    (r"(reseau|réseau)\s*(actif|en\s+cours)?", "NETWORK", None),
    (r"\b(trafic|traffic|bande\s+passante)\b", "NETWORK", None),
    (r"\bports?\s+(ouverts?|ecoute)", "NETWORK", None),
    (r"connexions?\s+(reseau|réseau|actives?|en\s+cours)", "NETWORK", None),

    # VERSION
    (r"(quelle|quel)\s+version", "VERSION", None),
    (r"^version$", "VERSION", None),
    (r"version\s+(de\s+)?(luna|serveur|python)", "VERSION", None),

    # MAINTENANCE (avant LOCK)
    (r"(mets?|passe|met)\s+(en\s+)?maintenance\s*(.*)", "MAINTENANCE", 3),
    (r"mode\s+maintenance\s*(.*)", "MAINTENANCE", 1),

    # ANNOUNCE (avant DIGEST — mais BROADCAST prend "a tous/tout le monde")
    (r"annonce\s*:?\s+(.+)", "ANNOUNCE", 1),
    (r"(annonce|communique)\s+(aux?\s+clients?)\s*:?\s*(.*)", "ANNOUNCE", 3),

    # STOP (avant LOCK "arrete tout")
    (r"(eteins?|éteins?)\s+(le\s+)?serveur", "STOP", None),
    (r"arret\s+(complet|total|du\s+serveur)", "STOP", None),

    # WIPE (avant KILL)
    (r"(efface|supprime|wipe)\s+.*(client|tenant)\s*#?(\d+)", "WIPE", 3),
    (r"(supprime|efface)\s+toutes?\s+.*(donnees|données)\s+.*(client|#)\s*(\d+)", "WIPE", 4),

    # REKEY
    (r"(regenere|régénère|change|nouvelle)\s+.*(cle|clé)\s*(api)?", "REKEY", None),

    # QUOTA_SET — avant QUOTA (special: multi-args)
    (r"(change|modifie|mets?)\s+.*quota\s+.*(client|#)\s*(\d+)\s+.*?(sms|voice|visio)\s+(\d+)", "_QUOTA_SET", None),

    # CLIENT — fiche detaillee d'un client (avant CLIENTS/QUOTA)
    (r"(fiche|detail|détail|profil|infos?)\s+(du\s+|de\s+)?(client\s+)?#?(\d+)", "CLIENT", 4),
    (r"(montre|affiche|donne)\s+(moi\s+)?(la\s+)?fiche\s+(du\s+)?#?(\d+)", "CLIENT", 5),
    (r"c.?est\s+qui\s+(le\s+)?(client\s+)?#?(\d+)", "CLIENT", 3),

    # REGISTER — inscrire un nouveau client (special: multi-args)
    (r"(inscris?|cree|crée|enregistre|nouveau)\s+(le\s+)?(client\s+)?(\S+@\S+)\s+(essentiel|confort|premium)\s+(\S+)\s*(.*)", "_REGISTER", None),
    (r"(inscris?|cree|crée|enregistre)\s+(\S+@\S+)\s+(essentiel|confort|premium)\s+(\S+)\s*(.*)", "_REGISTER", None),

    # PLAN_SET — changer le plan d'un client (special: multi-args)
    (r"(change|passe|mets?|met)\s+(le\s+)?(plan|abonnement)\s+(du\s+)?(client\s+)?#?(\d+)\s+(en\s+|a\s+|à\s+)?(essentiel|confort|premium)", "_PLAN_SET", None),
    (r"(passe|mets?|met)\s+(le\s+)?#?(\d+)\s+(en\s+)?(essentiel|confort|premium)", "_PLAN_SET", None),
    (r"(change|modifie)\s+(le\s+)?plan\s+(du\s+)?#?(\d+)\s+(en\s+|a\s+|à\s+)?(essentiel|confort|premium)", "_PLAN_SET", None),

    # BROADCAST — message a tous les clients (avant ANNOUNCE)
    (r"(ecris?|dis|envoie|message|previens?)\s+(a\s+tous|à\s+tous)\s*:?\s*(.*)", "BROADCAST", 3),
    (r"broadcast\s*:?\s*(.*)", "BROADCAST", 1),
    (r"(dis|previens?)\s+(tout\s+le\s+monde)\s*:?\s*(.*)", "BROADCAST", 3),

    # ── PATTERNS CLASSIQUES ──

    # STATUS
    (r"comment\s+(va|est)\s+(le\s+)?serveur", "STATUS", None),
    (r"(ca|ça)\s+va\s+le\s+serveur", "STATUS", None),
    (r"(etat|état)\s+(du\s+)?serveur", "STATUS", None),
    (r"tout\s+va\s+bien", "STATUS", None),
    (r"(ca|ça)\s+tourne\s*(bien)?$", "STATUS", None),
    (r"il\s+(va|est)\s+(comment|bien)", "STATUS", None),
    (r"quoi\s+de\s+neuf", "STATUS", None),

    # HEALTH
    (r"(sante|santé)\s+(du\s+)?(serveur|systeme|système)", "HEALTH", None),
    (r"\b(ram|cpu|memoire|mémoire)\b", "HEALTH", None),
    (r"(ca|ça)\s+(rame|lag)", "HEALTH", None),
    (r"combien\s+de\s+(ram|memoire|mémoire)", "HEALTH", None),
    (r"(ssl|certificat)\s*(expire|valide)?", "HEALTH", None),

    # THREATS
    (r"(ya|y\s*a|il\s+y\s+a)\s+(des\s+)?(attaques?|menaces?|pirat)", "THREATS", None),
    (r"(on\s+se\s+fait|quelqu.?un)\s+(attaque|pirate|hack)", "THREATS", None),
    (r"securite|sécurité", "THREATS", None),
    (r"(quelqu.?un|on)\s+(essaie|tente)\s+de", "THREATS", None),
    (r"rapport\s+(de\s+)?(securite|sécurité|menace)", "THREATS", None),

    # CLIENTS
    (r"(montre|liste|affiche|combien)\s+(moi\s+)?(les\s+|de\s+)?clients?", "CLIENTS", None),
    (r"(qui\s+sont|combien)\s+(mes\s+)?clients", "CLIENTS", None),
    (r"(liste|voir)\s+(des\s+)?abonne", "CLIENTS", None),
    (r"mes\s+clients", "CLIENTS", None),

    # QUOTA — avec extraction du tenant_id
    (r"quota\s+(du\s+)?client\s*#?(\d+)", "QUOTA", 2),
    (r"(combien|reste)\s+.*(client|abonne)\s*#?(\d+)", "QUOTA", 3),
    (r"(conso|consommation)\s+(du\s+)?#?(\d+)", "QUOTA", 3),
    (r"(il\s+)?(lui\s+)?reste\s+quoi\s+au?\s*#?(\d+)", "QUOTA", 3),

    # BAN — avec extraction de l'IP
    (r"(ban|banni[rs]?|bloqu|vir[ée]?|blacklist|bloque)\s+.?(?:l.?ip\s+)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "BAN", 2),
    (r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+.*(ban|bloqu|vir)", "BAN", 1),
    (r"degage\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "BAN", 1),

    # UNBAN — avec extraction de l'IP
    (r"(unban|deban|déban|debloqu|débloqu)\s+.?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "UNBAN", 2),
    (r"(enleve|enlève|retire)\s+.*(ban|blocage).+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "UNBAN", 3),

    # BANNED
    (r"(liste|quelles?|montre).*(ip|adresses?)\s+(banni|bloqu)", "BANNED", None),
    (r"(qui\s+est|combien)\s+(banni|bloqu)", "BANNED", None),
    (r"ip.*(banni|bloqu)", "BANNED", None),

    # LOCK
    (r"(ferme|verrouille|lock)\s+(tout|le\s+serveur)", "LOCK", None),
    (r"(lockdown|mode\s+urgence)", "LOCK", None),
    (r"(coupe|arrete|arrête)\s+tout", "LOCK", None),
    (r"plus\s+personne\s+(accede|rentre|entre|accède)", "LOCK", None),

    # UNLOCK
    (r"(ouvre|rouvre|deverrouille|déverrouille|unlock)", "UNLOCK", None),
    (r"(remet|remets)\s+en\s+(marche|route|service)", "UNLOCK", None),
    (r"c.?est\s+(bon|ok|fini|réglé|regle)", "UNLOCK", None),

    # SHIELD
    (r"(bouclier|shield)\s+(on|active|actif)", "SHIELD ON", None),
    (r"(bouclier|shield)\s+(off|desactive|désactive)", "SHIELD OFF", None),
    (r"mode\s+(bunker|defense|défense)", "SHIELD ON", None),

    # KILL — avec extraction tenant_id
    (r"(coupe|suspend|desactive|désactive|kill|vire)\s+.*(client|abonne)\s*#?(\d+)", "KILL", 3),
    (r"(coupe|suspend)\s+le?\s*#?(\d+)", "KILL", 2),

    # REVIVE — avec extraction tenant_id
    (r"(reactive|réactive|remet|revive)\s+.*(client|abonne)\s*#?(\d+)", "REVIVE", 3),
    (r"(reactive|réactive|remet)\s+le?\s*#?(\d+)", "REVIVE", 2),

    # BACKUP
    (r"(fais|lance|fait)\s+(un\s+)?backup", "BACKUP", None),
    (r"sauvegard[ée]?\s+(redis|tout|les\s+donnees|les\s+données)", "BACKUP", None),
    (r"backup\s+(maintenant|redis|now)", "BACKUP", None),

    # LOGS
    (r"(montre|affiche|dernier).*(log|evenement|événement|journal)", "LOGS", None),
    (r"(quoi|qu.?est-ce).*(pass[ée]|arriv[ée])", "LOGS", None),
    (r"(il\s+s.?est\s+pass[ée]\s+quoi)", "LOGS", None),

    # ERRORS
    (r"(montre|affiche|dernier).*(erreur|bug|probleme|problème)", "ERRORS", None),
    (r"(quoi|qu.?est-ce).*(plante|crash|bug)", "ERRORS", None),
    (r"(ya|y\s*a)\s+(des\s+)?erreurs?", "ERRORS", None),
    (r"(ca|ça)\s+(plante|bug|crash)", "ERRORS", None),

    # DIGEST
    (r"(envoie|fais|donne)\s+(moi\s+)?(un\s+)?(rapport|resume|résumé|digest|bilan)", "DIGEST", None),
    (r"(rapport|bilan)\s+(maintenant|complet|global)", "DIGEST", None),

    # RESTART
    (r"(redemarre|redémarre|restart|relance)\s+(le\s+)?(serveur)?", "RESTART", None),
    (r"reboot", "RESTART", None),

    # HELP (en dernier car "aide/commandes" est tres large)
    (r"^(aide|help)$", "HELP", None),
    (r"^commandes?$", "HELP", None),
    (r"(tu\s+)?(sais|peux)\s+faire\s+quoi", "HELP", None),
    (r"comment\s+(ca|ça)\s+marche", "HELP", None),

    # MSG — avec extraction id et message (special: multi-args)
    (r"(ecris?|dis|envoie|message)\s+au?\s+client\s*#?(\d+)\s*:?\s*(.*)", "_MSG", None),

    # PURGE
    (r"(purge|nettoie|vide|supprime)\s+(les\s+)?(logs?|erreurs?|bans?|sessions?|annonces?)", "PURGE", 3),

    # RATELIMIT — avec extraction de la valeur
    (r"(limite|ratelimit)\s+(a|à)?\s*(\d+)\s*(req|requetes?|par\s+min)?", "RATELIMIT", 3),
    (r"(\d+)\s+(requetes?|req)\s+(par\s+)?min", "RATELIMIT", 1),

    # WHITELIST_ADD — avec IP
    (r"(ajoute|autorise)\s+.*(whitelist|blanche)\s*:?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "WHITELIST_ADD", 3),
    (r"(whitelist|liste\s+blanche)\s+(add|ajoute)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "WHITELIST_ADD", 3),

    # WHITELIST_DEL — avec IP
    (r"(retire|enleve|enlève|supprime)\s+.*(whitelist|blanche)\s*:?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "WHITELIST_DEL", 3),

    # QUOTA_RESET
    (r"(raz|reset|remise?\s+a\s+zero)\s+.*quota\s+.*(client|#)\s*(\d+)", "QUOTA_RESET", 3),
]


def parse_french(text: str) -> Tuple[Optional[str], str]:
    """
    Parse une phrase francaise et retourne (COMMANDE, arguments).
    Retourne (None, "") si pas compris.

    Exemples:
        "comment va le serveur" → ("STATUS", "")
        "bloque l'ip 185.220.101.34" → ("BAN", "185.220.101.34")
        "quota du client 3" → ("QUOTA", "3")
        "ferme tout ya un problème" → ("LOCK", "ya un problème")
    """
    text_original = text.strip()
    text_clean = text_original.lower()
    # Enlever la ponctuation de fin
    text_clean = re.sub(r'[?!.;:]+$', '', text_clean).strip()
    # Normaliser les apostrophes
    text_clean = text_clean.replace("'", "'").replace("'", "'")

    # Commandes qui attendent un ID numerique en premier arg
    _ID_COMMANDS = {"CLIENT", "QUOTA", "KILL", "REVIVE", "WIPE"}
    # Commandes qui attendent une IP en premier arg
    _IP_COMMANDS = {"BAN", "UNBAN"}

    # ── ETAPE 1: Commande directe (si ca commence par un alias) ──
    words = text_clean.split()
    first_word = words[0] if words else ""
    if first_word in FR_COMMAND_ALIASES:
        # Eviter les faux positifs: "etat du cerveau" != STATUS
        # Si le 2e/3e mot pointe vers une autre commande, laisser les patterns decider
        rest = text_clean[len(first_word):].strip()
        rest_words = rest.split()
        skip_alias = False
        for rw in rest_words[:3]:
            rw_clean = rw.strip("'")
            if rw_clean in FR_COMMAND_ALIASES:
                candidate = FR_COMMAND_ALIASES[rw_clean]
                if candidate != FR_COMMAND_ALIASES[first_word]:
                    skip_alias = True
                    break
        if not skip_alias:
            cmd = FR_COMMAND_ALIASES[first_word]
            # Extraire juste le nombre pour les commandes ID
            if cmd in _ID_COMMANDS:
                num = re.search(r'(\d+)', rest)
                if num:
                    return cmd, num.group(1)
            # Extraire juste l'IP pour les commandes IP
            if cmd in _IP_COMMANDS:
                ip = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', rest)
                if ip:
                    return cmd, ip.group(1)
            return cmd, rest

    # ── ETAPE 2: Pattern matching sur la phrase complete ──
    for pattern, command, arg_group in FR_PATTERNS:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            # Commandes speciales: reconstruire les args depuis les groupes
            if command == "_REGISTER":
                # Re-match sur le texte original pour preserver la casse des noms
                match_orig = re.search(pattern, text_original.lower(), re.IGNORECASE)
                # Utiliser le texte original pour extraire les valeurs
                orig_lower = text_original.lower()
                # Trouver email et plan dans le texte original
                email_m = re.search(r'(\S+@\S+)', text_original)
                plan_m = re.search(r'\b(essentiel|confort|premium)\b', orig_lower)
                if email_m and plan_m:
                    email = email_m.group(1).lower()
                    plan = plan_m.group(1)
                    # Tout ce qui vient apres le plan = prenom [nom]
                    after_plan = text_original[plan_m.end():].strip()
                    parts = after_plan.split(maxsplit=1)
                    prenom = parts[0] if parts else ""
                    nom = parts[1].strip() if len(parts) > 1 else ""
                    if prenom:
                        return "REGISTER", f"{email} {plan} {prenom} {nom}".strip()
                continue

            if command == "_PLAN_SET":
                groups = match.groups()
                # Trouver tenant_id (nombre) et plan dans les groupes
                tid = plan = ""
                for g in groups:
                    if not g:
                        continue
                    g = g.strip()
                    if g.isdigit():
                        tid = g
                    elif g.lower() in ("essentiel", "confort", "premium"):
                        plan = g.lower()
                if tid and plan:
                    return "PLAN_SET", f"{tid} {plan}"
                continue

            if command == "_MSG":
                # Extraire id et message: "ecris au client 3: salut"
                tid = match.group(2) if match.lastindex >= 2 else ""
                msg = match.group(3).strip() if match.lastindex >= 3 else ""
                if tid:
                    return "MSG", f"{tid} {msg}".strip()
                continue

            if command == "_QUOTA_SET":
                # Pattern groups: (verb, "client"|"#", tid, resource, value)
                # Index:           1      2              3    4          5
                try:
                    tid = match.group(3)
                    resource = match.group(4).lower()
                    value = match.group(5)
                    if tid and resource and value:
                        return "QUOTA_SET", f"{tid} {resource} {value}"
                except (IndexError, AttributeError):
                    pass
                continue

            if arg_group is not None:
                try:
                    arg = match.group(arg_group)
                    return command, arg
                except (IndexError, AttributeError):
                    pass
            # Pour LOCK, extraire la raison apres le match
            if command == "LOCK":
                after = text_clean[match.end():].strip()
                return command, after if after else ""
            # Pour les commandes avec ON/OFF dans le pattern
            if " " in command:
                parts = command.split(" ", 1)
                return parts[0], parts[1]
            return command, ""

    # ── ETAPE 3: "client 3" → CLIENT (fiche), "quota 3" → QUOTA ──
    num_match = re.search(r'\b(\d+)\b', text_clean)
    if num_match:
        # "client 3" ou "#3" sans contexte quota → fiche client
        if re.search(r'(client|#)\s*' + num_match.group(1), text_clean):
            if not any(w in text_clean for w in
                       ["quota", "conso", "combien", "reste"]):
                return "CLIENT", num_match.group(1)
        # Contexte quota explicite
        if any(w in text_clean for w in
               ["quota", "conso", "consommation", "combien", "reste"]):
            return "QUOTA", num_match.group(1)

    # ── ETAPE 4: Chercher une IP isolée (possible BAN) ──
    ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', text_clean)
    if ip_match and any(w in text_clean for w in
                         ["ban", "bloqu", "vir", "degage", "dégage",
                          "stop", "arrêt", "arret"]):
        return "BAN", ip_match.group(1)

    # Pas compris par les patterns
    return None, ""


async def parse_french_ai(text: str) -> Tuple[Optional[str], str]:
    """
    Fallback IA: utilise GPT-4o-mini pour comprendre l'intention.
    Cout: ~0.001€ par requete.
    Appele SEULEMENT si parse_french() ne comprend pas.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None, ""

    prompt = f"""Tu es le parser de commandes de Luna Cortex, un système de gestion de serveur.
L'utilisateur envoie un message en français depuis son téléphone.
Tu dois extraire LA COMMANDE et LES ARGUMENTS.

Commandes disponibles:
STATUS (état du serveur), HEALTH (santé système), THREATS (sécurité),
CLIENTS (liste clients), CLIENT <id> (fiche détaillée d'un client),
QUOTA <id> (quota d'un client),
BAN <ip> (bannir IP), UNBAN <ip> (débannir), BANNED (IPs bannies),
LOCK <raison> (lockdown), UNLOCK (déverrouiller),
SHIELD ON/OFF (mode bouclier),
KILL <id> (suspendre client), REVIVE <id> (réactiver),
BACKUP (sauvegarde), LOGS (événements), ERRORS (erreurs),
DIGEST (rapport), CORTEX (état IA), RESTART (redémarrer),
HELP (aide), AUTH <code> (connexion), TOTP <code> (vérifier TOTP),
PING (test serveur vivant), UPTIME (durée fonctionnement),
REDIS (infos base de données), CONFIG (configuration),
WHITELIST (IPs autorisées), SESSIONS (qui est connecté),
PROCESSES (processus système), NETWORK (réseau/connexions),
DISK (espace disque), VERSION (versions logicielles),
MAINTENANCE <message> (mode maintenance), ANNOUNCE <message> (annonce à tous),
MSG <id> <message> (message à un client),
BROADCAST <message> (message à TOUS les clients),
REGISTER <email> <plan> <prenom> [nom] (inscrire un client, plans: essentiel/confort/premium),
PLAN_SET <id> <plan> (changer le plan d'un client: essentiel/confort/premium),
WHITELIST_ADD <ip> (ajouter IP whitelist), WHITELIST_DEL <ip> (retirer),
QUOTA_SET <id> <ressource> <valeur> (modifier quota),
QUOTA_RESET <id> (RAZ quota), PURGE <cible> (nettoyer logs/bans/etc),
RATELIMIT <valeur> (limite requêtes/min),
STOP (arrêt serveur), REKEY (nouvelle clé API), WIPE <id> (supprimer client),
AUDIT [jours] (journal d'audit/historique actions), COUTS (coûts du mois),
EXPORT <audit|couts|complet> [param] (générer PDF)

Message: "{text}"

Réponds UNIQUEMENT au format: COMMANDE|arguments
Si pas d'arguments: COMMANDE|
Si tu ne comprends pas: UNKNOWN|
Exemples:
"comment va le serveur" → STATUS|
"bloque 185.1.2.3" → BAN|185.1.2.3
"quota du client 7" → QUOTA|7
"ferme tout maintenance nuit" → LOCK|maintenance nuit
"fiche du client 3" → CLIENT|3
"c'est qui le 5" → CLIENT|5
"inscris marie@mail.fr premium Marie Dupont" → REGISTER|marie@mail.fr premium Marie Dupont
"passe le 3 en premium" → PLAN_SET|3 premium
"dis a tous maintenance ce soir" → BROADCAST|maintenance ce soir"""

    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 60,
                    "temperature": 0,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                answer = data["choices"][0]["message"]["content"].strip()
                if "|" in answer:
                    parts = answer.split("|", 1)
                    cmd = parts[0].strip().upper()
                    args = parts[1].strip() if len(parts) > 1 else ""
                    if cmd != "UNKNOWN":
                        logger.info(f"FR AI parse: '{text}' → {cmd} {args}")
                        return cmd, args
    except Exception as e:
        logger.debug(f"FR AI parse erreur: {e}")

    return None, ""


async def understand_french(text: str) -> Tuple[Optional[str], str]:
    """
    Point d'entrée principal.
    1. Essaie les patterns (gratuit, instantané)
    2. Si pas compris → fallback IA (0.001€)
    3. Si toujours pas → retourne None

    Retourne (COMMANDE, arguments) ou (None, "").
    """
    # Patterns d'abord
    cmd, args = parse_french(text)
    if cmd:
        return cmd, args

    # Fallback IA
    cmd, args = await parse_french_ai(text)
    if cmd:
        return cmd, args

    return None, ""
