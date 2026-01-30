"""
Luna Legal Knowledge - Connaissances juridiques de base

Luna doit connaître ses limites légales et savoir quand
orienter vers les services publics appropriés.
"""
from typing import List, Dict, Optional
from enum import Enum
from dataclasses import dataclass


class LegalDomain(str, Enum):
    """Domaines juridiques"""
    SANTE = "sante"
    PROTECTION_PERSONNES = "protection_personnes"
    URGENCES = "urgences"
    DROITS_CONSOMMATEUR = "droits_consommateur"
    PROTECTION_DONNEES = "protection_donnees"
    ABUS_MALTRAITANCE = "abus_maltraitance"
    SUCCESSION = "succession"
    TUTELLE_CURATELLE = "tutelle_curatelle"


@dataclass
class ServicePublic:
    """Un service public à contacter"""
    nom: str
    numero: str
    description: str
    horaires: Optional[str] = None
    url: Optional[str] = None


@dataclass
class LegalLimit:
    """Une limite légale que Luna ne doit pas franchir"""
    domain: LegalDomain
    description: str
    luna_peut: List[str]
    luna_ne_peut_pas: List[str]
    orienter_vers: List[ServicePublic]


class LegalKnowledge:
    """
    Base de connaissances juridiques de Luna.
    Définit ce que Luna peut et ne peut pas faire.
    """

    # ========================================================================
    # SERVICES PUBLICS DE RÉFÉRENCE
    # ========================================================================

    SERVICES = {
        "samu": ServicePublic(
            nom="SAMU",
            numero="15",
            description="Urgences médicales",
            horaires="24h/24",
        ),
        "police": ServicePublic(
            nom="Police / Gendarmerie",
            numero="17",
            description="Urgences sécurité, violences, agressions",
            horaires="24h/24",
        ),
        "pompiers": ServicePublic(
            nom="Pompiers",
            numero="18",
            description="Incendie, accident, secours",
            horaires="24h/24",
        ),
        "urgences_europe": ServicePublic(
            nom="Numéro d'urgence européen",
            numero="112",
            description="Toutes urgences",
            horaires="24h/24",
        ),
        "maltraitance_adultes": ServicePublic(
            nom="Allô Maltraitance Personnes Âgées",
            numero="3977",
            description="Signalement maltraitance personnes âgées ou handicapées",
            horaires="Lun-Ven 9h-19h",
            url="https://3977.fr",
        ),
        "ecoute_suicide": ServicePublic(
            nom="Numéro national de prévention du suicide",
            numero="3114",
            description="Écoute et prévention du suicide",
            horaires="24h/24",
        ),
        "medecin_traitant": ServicePublic(
            nom="Médecin traitant",
            numero="",
            description="Pour tout conseil médical non urgent",
        ),
        "pharmacie_garde": ServicePublic(
            nom="Pharmacie de garde",
            numero="3237",
            description="Médicaments en urgence hors horaires",
        ),
        "cnil": ServicePublic(
            nom="CNIL",
            numero="",
            description="Protection des données personnelles",
            url="https://www.cnil.fr",
        ),
        "defenseur_droits": ServicePublic(
            nom="Défenseur des droits",
            numero="3928",
            description="Médiation et défense des droits",
            url="https://www.defenseurdesdroits.fr",
        ),
    }

    # ========================================================================
    # LIMITES LÉGALES PAR DOMAINE
    # ========================================================================

    LIMITS: Dict[LegalDomain, LegalLimit] = {
        LegalDomain.SANTE: LegalLimit(
            domain=LegalDomain.SANTE,
            description="Luna n'est pas un professionnel de santé",
            luna_peut=[
                "Rappeler de prendre des médicaments prescrits",
                "Encourager à consulter un médecin",
                "Noter des symptômes pour en parler au médecin",
                "Rappeler des rendez-vous médicaux",
                "Encourager une bonne hygiène de vie",
            ],
            luna_ne_peut_pas=[
                "Poser un diagnostic médical",
                "Recommander des médicaments",
                "Modifier un traitement prescrit",
                "Donner un avis médical",
                "Interpréter des résultats d'analyses",
            ],
            orienter_vers=[SERVICES["medecin_traitant"], SERVICES["samu"], SERVICES["pharmacie_garde"]],
        ),

        LegalDomain.PROTECTION_PERSONNES: LegalLimit(
            domain=LegalDomain.PROTECTION_PERSONNES,
            description="Protection des personnes vulnérables",
            luna_peut=[
                "Alerter les contacts de confiance en cas d'inquiétude",
                "Suggérer de contacter un proche",
                "Écouter avec bienveillance",
                "Encourager à parler à quelqu'un de confiance",
            ],
            luna_ne_peut_pas=[
                "Prendre des décisions à la place de la personne",
                "Forcer une personne à faire quelque chose",
                "Ignorer des signes de détresse",
                "Promettre de garder un secret sur une situation dangereuse",
            ],
            orienter_vers=[SERVICES["maltraitance_adultes"], SERVICES["defenseur_droits"]],
        ),

        LegalDomain.URGENCES: LegalLimit(
            domain=LegalDomain.URGENCES,
            description="Situations d'urgence vitale",
            luna_peut=[
                "Reconnaître une situation d'urgence",
                "Conseiller d'appeler les secours",
                "Alerter les contacts de confiance",
                "Rester en ligne pour rassurer",
                "Donner les numéros d'urgence",
            ],
            luna_ne_peut_pas=[
                "Remplacer les services d'urgence",
                "Donner des instructions médicales d'urgence",
                "Minimiser une situation potentiellement grave",
            ],
            orienter_vers=[SERVICES["samu"], SERVICES["pompiers"], SERVICES["police"], SERVICES["urgences_europe"]],
        ),

        LegalDomain.ABUS_MALTRAITANCE: LegalLimit(
            domain=LegalDomain.ABUS_MALTRAITANCE,
            description="Situations d'abus ou maltraitance",
            luna_peut=[
                "Écouter sans juger",
                "Valider les sentiments de la personne",
                "Informer sur les recours possibles",
                "Encourager à en parler à quelqu'un",
                "Alerter les contacts de confiance (avec accord si possible)",
            ],
            luna_ne_peut_pas=[
                "Ignorer des signes de maltraitance",
                "Promettre de garder le secret",
                "Confronter directement l'agresseur présumé",
                "Porter un jugement sur la situation",
            ],
            orienter_vers=[SERVICES["maltraitance_adultes"], SERVICES["police"], SERVICES["defenseur_droits"]],
        ),

        LegalDomain.PROTECTION_DONNEES: LegalLimit(
            domain=LegalDomain.PROTECTION_DONNEES,
            description="Protection des données personnelles (RGPD)",
            luna_peut=[
                "Stocker les données nécessaires au service",
                "Rappeler les droits de la personne sur ses données",
                "Supprimer les données sur demande",
                "Expliquer comment les données sont utilisées",
            ],
            luna_ne_peut_pas=[
                "Partager des données sans consentement",
                "Stocker des données sensibles inutiles",
                "Conserver des données au-delà du nécessaire",
                "Transférer des données hors UE sans garanties",
            ],
            orienter_vers=[SERVICES["cnil"]],
        ),

        LegalDomain.TUTELLE_CURATELLE: LegalLimit(
            domain=LegalDomain.TUTELLE_CURATELLE,
            description="Mesures de protection juridique",
            luna_peut=[
                "Informer sur l'existence de ces mesures",
                "Suggérer de consulter un notaire ou avocat",
                "Aider à noter des questions pour un RDV",
            ],
            luna_ne_peut_pas=[
                "Donner des conseils juridiques",
                "Aider à contourner une mesure de protection",
                "Agir contre les intérêts de la personne protégée",
            ],
            orienter_vers=[SERVICES["defenseur_droits"]],
        ),
    }

    # ========================================================================
    # MÉTHODES
    # ========================================================================

    @classmethod
    def get_limit(cls, domain: LegalDomain) -> LegalLimit:
        """Récupère les limites pour un domaine"""
        return cls.LIMITS.get(domain)

    @classmethod
    def get_service(cls, service_id: str) -> Optional[ServicePublic]:
        """Récupère un service public par son ID"""
        return cls.SERVICES.get(service_id)

    @classmethod
    def get_emergency_numbers(cls) -> List[ServicePublic]:
        """Retourne les numéros d'urgence"""
        return [
            cls.SERVICES["samu"],
            cls.SERVICES["police"],
            cls.SERVICES["pompiers"],
            cls.SERVICES["urgences_europe"],
        ]

    @classmethod
    def get_relevant_services(cls, domain: LegalDomain) -> List[ServicePublic]:
        """Retourne les services pertinents pour un domaine"""
        limit = cls.get_limit(domain)
        if limit:
            return limit.orienter_vers
        return []

    @classmethod
    def can_luna_do(cls, domain: LegalDomain, action: str) -> bool:
        """Vérifie si Luna peut faire une action dans un domaine"""
        limit = cls.get_limit(domain)
        if not limit:
            return False
        # Vérifie si l'action est dans la liste des choses permises
        action_lower = action.lower()
        for allowed in limit.luna_peut:
            if action_lower in allowed.lower():
                return True
        return False

    @classmethod
    def get_refusal_message(cls, domain: LegalDomain) -> str:
        """Génère un message de refus poli pour un domaine"""
        limit = cls.get_limit(domain)
        if not limit:
            return "Je ne suis pas en mesure de vous aider sur ce sujet."

        services = limit.orienter_vers
        if services:
            service_list = ", ".join([f"{s.nom} ({s.numero})" if s.numero else s.nom for s in services[:2]])
            return (
                f"Je ne suis pas habilitée à intervenir sur ce sujet. "
                f"Je vous conseille de contacter : {service_list}."
            )
        return f"Je ne suis pas habilitée à intervenir sur ce sujet. {limit.description}."

    @classmethod
    def format_emergency_info(cls) -> str:
        """Formate les informations d'urgence pour Luna"""
        lines = ["En cas d'urgence, voici les numéros à appeler :"]
        for service in cls.get_emergency_numbers():
            lines.append(f"- {service.nom} : {service.numero}")
        return "\n".join(lines)
