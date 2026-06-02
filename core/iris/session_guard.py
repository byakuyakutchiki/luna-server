"""
core/iris/session_guard.py
Middleware de sécurité : filtrage des données par scope et validation owner.
"""
from typing import Any, Dict, Optional
from core.iris.participants import (
    IrisParticipant,
    IrisRole,
    requires_owner_validation,
    check_permission,
)


class IrisSessionGuard:
    """
    Garde-fou de session Iris.
    Filtre les payloads de rendu et bloque les actions non autorisées.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._participants: Dict[str, IrisParticipant] = {}
        self._owner_id: Optional[str] = None

    def register_participant(self, participant: IrisParticipant) -> None:
        """Ajoute un participant à la session."""
        self._participants[participant.id] = participant
        if participant.user_type == IrisRole.OWNER and self._owner_id is None:
            self._owner_id = participant.id

    def remove_participant(self, participant_id: str) -> None:
        """Retire un participant."""
        self._participants.pop(participant_id, None)

    def get_participant(self, participant_id: str) -> Optional[IrisParticipant]:
        return self._participants.get(participant_id)

    def get_owner(self) -> Optional[IrisParticipant]:
        if self._owner_id:
            return self._participants.get(self._owner_id)
        return None

    def list_participants(self) -> list:
        return list(self._participants.values())

    # ───────────────────────────────────────────────────────────
    # FILTRAGE DES DONNÉES
    # ───────────────────────────────────────────────────────────

    def filter_render_payload(
        self, payload: dict, participant_id: str
    ) -> dict:
        """
        Filtre un payload de rendu selon le scope du participant.
        Retourne un payload sécurisé ou un message de refus.
        """
        participant = self._participants.get(participant_id)
        if not participant:
            return {"render_type": "context_panel", "payload": {"title": "Session", "sections": [{"heading": "Erreur", "body": "Participant non reconnu."}]}}

        if participant.user_type == IrisRole.OWNER:
            return payload

        # Trusted sans scope = voit tout sauf données sensibles owner
        if participant.user_type == IrisRole.TRUSTED and not participant.scope_project:
            return self._strip_owner_sensitive(payload)

        # Guest / Trusted avec scope = filtrer par projet
        if participant.scope_project:
            return self._apply_project_filter(payload, participant.scope_project)

        # Guest sans scope = données génériques uniquement
        if participant.user_type == IrisRole.GUEST:
            return self._apply_guest_filter(payload)

        return payload

    def _strip_owner_sensitive(self, payload: dict) -> dict:
        """Retire les champs marqués comme sensibles pour le owner."""
        # TODO: implémenter le stripping réel selon le modèle de données
        safe = dict(payload)
        if "payload" in safe and isinstance(safe["payload"], dict):
            p = safe["payload"]
            p.pop("owner_notes", None)
            p.pop("financial_raw", None)
        return safe

    def _apply_project_filter(self, payload: dict, scope_project: str) -> dict:
        """Ne conserve que les données liées au projet autorisé."""
        # TODO: implémenter le filtrage par projet (tag, catégorie, etc.)
        safe = dict(payload)
        project_match = False
        if "payload" in safe and isinstance(safe["payload"], dict):
            p = safe["payload"]
            # Heuristique : si le payload mentionne le projet → OK
            payload_str = str(p).lower()
            if scope_project.lower() in payload_str:
                project_match = True
        if not project_match:
            return {
                "render_type": "context_panel",
                "payload": {
                    "title": "Confidentiel",
                    "sections": [
                        {
                            "heading": "Accès restreint",
                            "body": "Ces informations ne concernent pas votre projet."
                        }
                    ]
                }
            }
        return safe

    def _apply_guest_filter(self, payload: dict) -> dict:
        """Filtre strict pour les invités sans scope défini."""
        safe = dict(payload)
        # Par défaut, un guest sans scope ne voit que des messages génériques
        # ou des données explicitement tagguées 'public'
        if "payload" in safe and isinstance(safe["payload"], dict):
            p = safe["payload"]
            is_public = p.get("visibility") == "public"
            if not is_public:
                return {
                    "render_type": "context_panel",
                    "payload": {
                        "title": "Confidentiel",
                        "sections": [
                            {
                                "heading": "Accès restreint",
                                "body": "Ces informations sont confidentielles."
                            }
                        ]
                    }
                }
        return safe

    # ───────────────────────────────────────────────────────────
    # VALIDATION DES ACTIONS ENGAGEANTES
    # ───────────────────────────────────────────────────────────

    def validate_action(
        self,
        action_type: str,
        participant_id: str,
        owner_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Valide une action. Retourne :
        - {"ok": True} si autorisée
        - {"ok": False, "reason": "..."} si interdite
        - {"ok": False, "requires_confirmation": True, "owner_id": "..."} si validation owner requise
        """
        participant = self._participants.get(participant_id)
        if not participant:
            return {"ok": False, "reason": "Participant non reconnu."}

        if not check_permission(action_type, participant):
            return {"ok": False, "reason": "Action non autorisée pour votre rôle."}

        if requires_owner_validation(action_type, participant):
            if owner_confirmed:
                return {"ok": True}
            owner = self.get_owner()
            return {
                "ok": False,
                "requires_confirmation": True,
                "owner_id": owner.id if owner else None,
                "reason": "Cette action nécessite la validation du propriétaire."
            }

        return {"ok": True}

    def owner_confirm_action(self, action_type: str, requester_id: str) -> bool:
        """Simule la confirmation explicite du owner (à appeler via WS ou API)."""
        # TODO: loguer l'audit de confirmation
        return True

    # ───────────────────────────────────────────────────────────
    # UTILITAIRES WS
    # ───────────────────────────────────────────────────────────

    def compute_visible_to(self, payload: dict) -> Optional[list]:
        """
        Détermine la liste des participant_id autorisés à voir ce payload.
        Retourne None si visible par tous.
        """
        # Par défaut, tout le monde voit
        # TODO: affiner selon le contenu du payload (projet, confidentialité)
        return None

    def presence_event(self, participant_id: str, status: str) -> dict:
        """Génère un événement de présence WS."""
        return {
            "type": "presence",
            "participant_id": participant_id,
            "status": status,  # joined | left | typing
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
