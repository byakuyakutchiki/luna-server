"""
Tavus Client - Integration video avatar Luna
Crée et gère les conversations vidéo via Tavus CVI.
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any, Tuple
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
) -> str:
    """
    Construit le contexte conversationnel SANITISE pour Tavus.
    Ce contexte est envoye a Tavus lors de la creation de conversation.
    Il NE CONTIENT PAS d'informations confidentielles.
    """
    # Section contacts
    if memory_manager:
        contacts_section = _build_contacts_section(memory_manager)
    else:
        contacts_section = "Des contacts de confiance sont enregistres. Tu peux proposer de les alerter."

    try:
        return f"""=== QUI TU ES ===
Tu es Luna, l'assistante IA personnelle de YAWatch.
Tu es une compagne bienveillante et chaleureuse, disponible 24h/24, 7j/7.
Tu parles en francais avec un ton rassurant, moderne et empathique.
Tu tutoies le souscripteur sauf s'il te demande de le vouvoyer.

=== TON SOUSCRIPTEUR ===
Tu parles avec {subscriber_name}.
Il est en appel video avec toi en ce moment.

=== CE QUE TU PEUX FAIRE EN VISIO ===
- Discuter, ecouter, rassurer, tenir compagnie
- Suggerer d'appeler les services d'urgence (tu donnes les numeros)
- Proposer d'alerter les contacts de confiance par SMS
- Un contact de confiance peut rejoindre cet appel video (le souscripteur peut l'inviter)

=== CE QUE TU NE PEUX PAS FAIRE ===
- Tu ne peux PAS appeler les services d'urgence toi-meme (c'est interdit pour une IA)
- Tu ne peux PAS envoyer de SMS toi-meme depuis la visio (le souscripteur le fait via l'interface)
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

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_conversation(
        self,
        tenant_id: int,
        custom_greeting: Optional[str] = None,
        context: Optional[str] = None,
        max_duration: int = 1800,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Crée une nouvelle conversation vidéo Tavus.

        Returns:
            (success, data) avec data contenant conversation_url et conversation_id
        """
        if not self.is_configured:
            return False, {"error": "Tavus non configure (cle API ou persona manquante)"}

        payload = {
            "persona_id": self.persona_id,
            "properties": {"max_call_duration": max_duration},
        }
        if custom_greeting:
            payload["custom_greeting"] = custom_greeting
        if context:
            payload["conversational_context"] = context

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

    def end_conversation(self, conversation_id: str) -> bool:
        """Marque une conversation comme terminée"""
        conv = self._active_conversations.get(conversation_id)
        if conv:
            conv.status = "ended"
            logger.info(f"Tavus conversation ended: {conversation_id}")
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
