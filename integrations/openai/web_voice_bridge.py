"""
Web Voice Bridge — Pont audio direct entre navigateur et OpenAI Realtime API

Le navigateur capture l'audio du micro via AudioWorklet, l'envoie en PCM16 base64
via WebSocket au serveur, qui relaie vers OpenAI Realtime API.
La reponse audio revient par le meme chemin.

Pas de Twilio, pas de Tavus — conversation directe voix, toujours disponible.

Usage:
    bridge = WebVoiceBridge(
        openai_api_key="sk-...",
        ws_client=fastapi_websocket,
        context="Tu es Luna...",
        tool_handler=async_func,
    )
    await bridge.run()
"""
import json
import uuid
import asyncio
import logging
import time as _time
import pathlib
from typing import Optional, Dict, Any, Callable, Awaitable, List

import websockets
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

import os

# ── Enregistreur de session — pour diagnostic autonome Claude ────────────────
_SESSION_LOG_DIR = pathlib.Path("/tmp/iris_sessions")
_SESSION_LOG_DIR.mkdir(exist_ok=True)

def _session_log(session_file: pathlib.Path, event_type: str, data: dict):
    """Écrit un événement JSON dans le fichier de session (une ligne par événement)."""
    try:
        entry = {"t": round(_time.time(), 3), "type": event_type, **data}
        with session_file.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
OPENAI_REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_REALTIME_MODEL}"
OPENAI_VOICE_NAME = os.getenv("OPENAI_VOICE_NAME", "coral")

# Import des tools depuis le bridge Twilio (meme jeu de tools)
from integrations.openai.realtime_bridge import VOICE_TOOLS, _realtime_semaphore, _active_bridges

# Modes de mission Iris — Objectif 024
from integrations.iris.modes import (
    IRIS_MODES, DEFAULT_MODE, build_mode_context, get_mode_tools, detect_mode_from_text
)
from integrations.iris.workspace_orchestrator import WorkspacePlan, orchestrate_workspace_request

# Nombre d'erreurs client consecutives avant arret
_MAX_CLIENT_ERRORS = 3
# Nombre d'erreurs OpenAI consecutives (hors audio) avant arret
_MAX_OPENAI_ERRORS = 15

# Mots de promesse Iris qui signalent un rendu imminent mais non declenche
_PROMISE_PATTERNS = [
    "je vais préparer", "je vais créer", "je vais générer", "je vais faire",
    "je m'en occupe", "je vais afficher", "je vais rédiger", "je vais montrer",
    "je vais construire", "je vais organiser", "je vais dresser", "je vais établir",
    "je te prépare", "je te crée", "je te génère", "je te fais",
    "c'est parti", "je lance", "je démarre",
]

# Mapping intent -> render_type pour fallback deterministe
_INTENT_RENDER_MAP = [
    # Ordre de priorité : actions sensibles d'abord, fallback en dernier
    (["envoyer sms", "envoie sms", "envoyer un message", "envoie un email", "envoyer un email", "envoie un mail",
      "appelle ", "appeler ", "contacte ", "payer ", "virement ", "réserver ", "commander "], "action_board"),
    (["il me manque", "il manque", "information manquante", "pour ça il faut"], "missing_info"),
    (["formulaire", "remplis ", "complète ", "besoin de tes infos"], "form_board"),
    (["quelle option", "lequel choisir", "laquelle choisir", "pour ou contre",
      "avantages inconvénients", "inconvénients avantages"], "decision_board"),
    (["kanban", "sprint", "backlog", "a faire/en cours/termine", "colonnes taches",
      "avancement des taches", "etat des taches", "en cours.*termine", "a faire.*en cours"], "kanban_board"),
    (["reunion", "compte-rendu", "ordre du jour", "pv de", "note de reunion",
      "demarre la reunion", "ouvre la reunion", "demarre.*reunion", "ouvre.*reunion"], "meeting_board"),
    (["fiche contact", "qui est ", "coordonnées de"], "contact_board"),
    (["budget", "solde", "mes dépenses", "mes finances", "combien j'ai"], "budget_board"),
    (["adresse", "itinéraire", "trajet", "localisation", "comment aller", "où est"], "map_board"),
    (["fichiers", "pièces jointes", "photos ", "images "], "media_board"),
    (["graphique", "courbe", "histogramme", "camembert", "évolution", "tendance", "diagramme"], "chart"),
    (["roadmap", "feuille de route", "plan par étapes", "jalons"], "roadmap"),
    (["planning", "chronologie", "échéances", "calendrier", "timeline",
      "lancement le ", "livraison le ", "mise en production"], "timeline"),
    (["indicateurs", "metriques", "chiffres cles", "kpi", "statistiques", "stats",
      "temps de reponse", "disponibilite", "quota voix", "chiffres cles",
      "indicateurs de performance", "tableau de bord"], "kpi_cards"),
    (["actions a faire", "liste les actions", "avant le lancement", "checklist",
      "a faire avant", "todo", "taches a realiser", "taches a accomplir",
      "liste.*taches", "avant la mise en production", "avant la livraison",
      "a faire aujourd", "preparer pour la demo", "preparer pour le lancement"], "action_board"),
    (["tableau", "colonnes", "lignes", "données en tableau", "liste de"], "data_board"),
    (["etat des services", "statut des services", "mes quotas", "diagnostic",
      "sante du systeme", "operationnel", "tout fonctionne", "services fonctionnent",
      "etat de mes services", "l etat de mes services", "mes services",
      "etat du systeme", "verifie les services", "systeme fonctionne"], "status_rail"),
    (["compare ", "versus ", "avantages", "inconvénients", " vs "], "comparison"),
    (["rédige", "courrier", "lettre", "brouillon", "note officielle"], "document_draft"),
    (["pdf", "contrat", "devis", "facture", "analyse de fichier"], "document_insight"),
]


class _IrisActionRouter:
    """Routeur d'action deterministe cote serveur.

    Detecte les promesses Iris ('je vais preparer...') et, si aucun tool_call
    n'arrive dans un delai court, force un render fallback base sur la derniere
    demande utilisateur. Ne declenche JAMAIS d'actions sensibles.
    """

    _FALLBACK_DELAY_SECONDS = 4.0
    _FALLBACK_DELAY_DOC_SECONDS = 2.0  # plus court quand un document est en session

    def __init__(self, bridge):
        self._bridge = bridge
        self._last_user_text = ""
        self._promise_detected = False
        self._tool_call_received = False
        self._fallback_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def on_user_transcript(self, text: str):
        """Memorise la derniere demande utilisateur."""
        self._last_user_text = text
        logger.info(f"ActionRouter: user demande memorisee ({len(text)} chars)")

    def on_iris_transcript(self, text: str):
        """Detecte une promesse Iris et demarre le timer de fallback."""
        lower = text.lower()
        is_promise = any(p.lower() in lower for p in _PROMISE_PATTERNS)
        if is_promise:
            logger.info(f"ActionRouter: PROMESSE detectee -> '{text[:80]}...'")
            self._promise_detected = True
            self._tool_call_received = False
            self._start_fallback_timer()
        else:
            # Si Iris repond sans promesse, annuler tout timer en cours
            self._cancel_fallback_timer()

    def on_tool_call(self, name: str):
        """Un tool_call a ete recu : annuler le fallback."""
        logger.info(f"ActionRouter: tool_call recu ({name}) -> fallback annule")
        self._tool_call_received = True
        self._cancel_fallback_timer()

    def _start_fallback_timer(self):
        self._cancel_fallback_timer()
        has_docs = bool(getattr(self._bridge, "_session_documents", []))
        delay = self._FALLBACK_DELAY_DOC_SECONDS if has_docs else self._FALLBACK_DELAY_SECONDS
        self._fallback_task = asyncio.create_task(self._fallback_worker(delay))

    def _cancel_fallback_timer(self):
        if self._fallback_task and not self._fallback_task.done():
            self._fallback_task.cancel()
        self._fallback_task = None

    async def _fallback_worker(self, delay: float = 4.0):
        try:
            await asyncio.sleep(delay)
            await self._execute_fallback()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"ActionRouter fallback error: {e}")

    async def _execute_fallback(self):
        async with self._lock:
            if self._tool_call_received:
                return
            if not self._last_user_text:
                return

            # Si un document est en session → fallback document_insight avec le vrai contenu
            session_docs = getattr(self._bridge, "_session_documents", [])
            if session_docs:
                last_doc = session_docs[-1]
                render_type = "document_insight"
                render_msg = {
                    "type": "render",
                    "render_type": "document_insight",
                    "title": last_doc.get("filename", "Document"),
                    "boxes": [
                        {"title": "Analyse", "body": last_doc.get("analysis", "—")},
                        {"title": "Demande", "body": self._last_user_text[:200]},
                    ],
                    "tags": [{"label": "Fallback visuel", "type": "warn"}],
                    "actions": [
                        {"label": "Synthèse"},
                        {"label": "Points clés"},
                        {"label": "Améliorer ce CV"},
                        {"label": "Tableau"},
                    ],
                    "source": "action_router_fallback",
                }
            else:
                render_type = self._infer_render_type(self._last_user_text)
                render_msg = {
                    "type": "render",
                    "render_type": render_type,
                    "payload": self._build_payload(render_type, self._last_user_text),
                    "source": "action_router_fallback",
                }

            logger.info(f"ActionRouter: FALLBACK FORCE -> {render_type}")
            await self._bridge._ws_send_client(render_msg)

            # Enrichissement async du skeleton (voix path) — remplace le skeleton par des vraies données
            if render_type != "context_panel" and not session_docs:
                _send_fn = (
                    (lambda m: self._bridge._session_manager.broadcast(self._bridge._session_id, m))
                    if (self._bridge._session_id and self._bridge._session_manager)
                    else self._bridge._ws_send_client
                )
                asyncio.create_task(
                    self._enrich_payload_async(render_type, self._last_user_text, _send_fn)
                )

            # Informer le client que c'est un fallback
            await self._bridge._ws_send_client({
                "type": "action_router",
                "action": "force_render",
                "render_type": render_type,
                "reason": "promesse_iris_non_honoree",
                "last_link": "action_router_fallback",
            })

    def _infer_render_type(self, text: str) -> str:
        import unicodedata as _ud, re as _re
        lower = text.lower()
        nfd = _ud.normalize("NFD", lower)
        stripped = "".join(c for c in nfd if _ud.category(c) != "Mn")
        for mots_cles, rt in _INTENT_RENDER_MAP:
            for m in mots_cles:
                if ".*" in m or m.startswith("^") or m.endswith("$"):
                    # Pattern regex — chercher dans lower et stripped
                    try:
                        if _re.search(m, lower) or _re.search(m, stripped):
                            return rt
                    except Exception:
                        pass
                else:
                    if m in lower or m in stripped:
                        return rt
        return "context_panel"

    async def _enrich_payload_async(self, render_type: str, user_text: str, send_fn) -> None:
        """Appelle GPT-4o-mini pour enrichir le payload, puis l'envoie au client."""
        _SCHEMAS = {
            "status_rail": (
                '{"services":[{"name":"OpenAI","status":"ok","detail":"API connectée"},{"name":"Twilio","status":"ok","detail":"SMS/Voix actif"},{"name":"Stripe","status":"ok","detail":"Paiements actifs"},{"name":"Redis","status":"ok","detail":"Cache opérationnel"}],"summary":"État général du système."}'
            ),
            "kpi_cards": (
                '{"kpis":[{"label":"Utilisateurs actifs","value":"1 200","unit":"","trend":"up"},{"label":"Satisfaction","value":"94","unit":"%","trend":"stable"},{"label":"Temps de réponse","value":"1.8","unit":"s","trend":"down"},{"label":"Disponibilité","value":"99.7","unit":"%","trend":"stable"}],"summary":"Indicateurs clés du projet."}'
            ),
            "action_board": (
                '{"sections":[{"title":"Urgent","items":[{"text":"Action 1","done":false,"priority":"high"},{"text":"Action 2","done":false,"priority":"high"}]},{"title":"Cette semaine","items":[{"text":"Action 3","done":false,"priority":"medium"}]}],"summary":"Liste des actions prioritaires."}'
            ),
            "timeline": (
                '{"events":[{"date":"01/06/2026","title":"Phase 1","description":"Démarrage","status":"done"},{"date":"15/06/2026","title":"Phase 2","description":"Développement","status":"en_cours"},{"date":"30/06/2026","title":"Lancement","description":"Mise en production","status":"upcoming"}],"summary":"Chronologie du projet."}'
            ),
            "chart": (
                '{"type":"bar","labels":["Jan","Fév","Mar","Avr","Mai","Jun"],"datasets":[{"label":"Revenus (€)","data":[2000,3200,4100,5500,7200,9000]}],"summary":"Évolution des revenus sur 6 mois."}'
            ),
            "budget_board": (
                '{"lines":[{"label":"Infrastructure","amount":450,"category":"technique"},{"label":"APIs","amount":280,"category":"technique"},{"label":"Marketing","amount":500,"category":"commercial"},{"label":"Support","amount":150,"category":"opérations"}],"total":1380,"currency":"EUR","summary":"Budget mensuel consolidé."}'
            ),
            "decision_board": (
                '{"options":[{"name":"Option A","pros":["Rapide","Moins cher"],"cons":["Risque","Moins stable"],"recommended":false},{"name":"Option B","pros":["Stable","Documenté"],"cons":["Plus long","Plus cher"],"recommended":true}],"recommendation":"Option B recommandée.","summary":"Analyse pour décision."}'
            ),
            "meeting_board": (
                '{"title":"Réunion","date":"aujourd\'hui","time":"maintenant","participants":[{"name":"Alice","initials":"AL","role":"Chef de projet"},{"name":"Bob","initials":"BO","role":"Tech lead"},{"name":"Vous","initials":"V","role":"Fondateur"}],"agenda":[{"item":"Point avancement","done":false},{"item":"Décisions budget","done":false},{"item":"Planning Q3","done":false}],"decisions":[],"summary":"Réunion en cours."}'
            ),
            "document_draft": (
                '{"title":"Email de confirmation","subject":"Confirmation de votre demande","body":"Bonjour [Prénom],\n\nSuite à notre échange du [date], nous confirmons [action principale].\n\nCordialement,\n[Votre nom]","placeholders":["[Prénom]","[date]","[action principale]","[Votre nom]"],"summary":"Brouillon prêt à compléter."}'
            ),
            "roadmap": (
                '{"phases":[{"title":"Phase 1 — Fondation","description":"Architecture, auth, DB","status":"done","duration":"4 sem"},{"title":"Phase 2 — Core","description":"Fonctionnalités principales","status":"en_cours","duration":"6 sem"},{"title":"Phase 3 — Lancement","description":"Beta, marketing, onboarding","status":"upcoming","duration":"4 sem"}],"summary":"Roadmap produit."}'
            ),
            "comparison": (
                '{"options":[{"name":"Option A","pros":["Avantage 1","Avantage 2"],"cons":["Inconvénient 1"],"score":7},{"name":"Option B","pros":["Avantage 3","Avantage 4"],"cons":["Inconvénient 2","Inconvénient 3"],"score":8}],"recommendation":"Option B légèrement préférée.","summary":"Comparaison des options."}'
            ),
            "data_board": (
                '{"title":"Données","columns":["Item","Valeur","Statut"],"rows":[["Ligne 1","Donnée A","ok"],["Ligne 2","Donnée B","attente"],["Ligne 3","Donnée C","ok"]],"summary":"Tableau de données."}'
            ),
        }
        if render_type not in _SCHEMAS:
            return

        _today = _time.strftime("%d/%m/%Y")
        _prompt = (
            f"Panneau : {render_type}. Demande : \"{user_text}\". Date : {_today}.\n"
            f"Génère un JSON réaliste adapté à la demande. Exacte structure :\n{_SCHEMAS[render_type]}\n"
            f"Règles : 3-5 items min | status_rail→services Luna (OpenAI,Twilio,Stripe,Redis,Tavus) | "
            f"timeline→dates réelles autour {_today} | montants en euros | français | JSON pur sans commentaires."
        )
        try:
            import anthropic as _anthropic, re as _re_json
            _ant_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_KEY_CHAT")
            _client = _anthropic.AsyncAnthropic(api_key=_ant_key)
            _resp = await _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=900,
                temperature=0.3,
                system=(
                    "Tu génères uniquement du JSON valide pour des panneaux visuels. "
                    "Aucun texte avant ou après le JSON. Aucun markdown. JSON pur."
                ),
                messages=[{"role": "user", "content": _prompt}],
            )
            _raw = _resp.content[0].text.strip()
            _m = _re_json.search(r'\{.*\}', _raw, _re_json.DOTALL)
            _rich = json.loads(_m.group(0) if _m else _raw)
            await send_fn({
                "type": "render",
                "render_type": render_type,
                "payload": _rich,
                "enriched": True,
            })
            logger.info(f"WebVoice: payload enrichi (haiku) envoyé ({render_type})")
        except Exception as _e:
            logger.warning(f"WebVoice: enrich_payload failed ({render_type}): {_e}")

    def _build_payload(self, render_type: str, user_text: str) -> Dict[str, Any]:
        """Construit un payload minimal (squelette) — sera enrichi async par _enrich_payload_async."""
        now_str = _time.strftime("%d/%m/%Y %H:%M")
        if render_type == "data_board":
            return {
                "title": "Données demandées",
                "columns": ["Item", "Valeur"],
                "rows": [["Demande", user_text[:60]]],
                "summary": "Rendu forcé par Action Router — données à compléter.",
            }
        if render_type == "chart":
            return {
                "title": "Graphique demandé",
                "type": "bar",
                "labels": ["A", "B", "C"],
                "datasets": [{"label": "Valeurs", "data": [0, 0, 0]}],
                "summary": "Rendu forcé par Action Router — données chiffrées à extraire.",
            }
        if render_type == "kpi_cards":
            return {
                "kpis": [
                    {"label": "Demande", "value": "?"},
                    {"label": "Statut", "value": "En attente de données"},
                ],
                "summary": "Rendu forcé par Action Router — KPIs à compléter.",
            }
        if render_type == "action_board":
            return {
                "sections": [
                    {"title": "À faire", "items": [{"text": user_text[:80], "done": False}]}
                ],
                "summary": "Rendu forcé par Action Router — actions à préciser.",
            }
        if render_type == "kanban_board":
            return {
                "columns": [
                    {"id": "todo", "label": "À faire", "color": "todo", "cards": [{"title": user_text[:60], "tag": None}]},
                    {"id": "doing", "label": "En cours", "color": "doing", "cards": []},
                    {"id": "blocked", "label": "Bloqué", "color": "blocked", "cards": []},
                    {"id": "done", "label": "Terminé", "color": "done", "cards": []},
                ],
                "summary": "Rendu forcé par Action Router — kanban à compléter.",
            }
        if render_type == "meeting_board":
            return {
                "title": "Réunion",
                "date": now_str.split()[0],
                "time": now_str.split()[1] if len(now_str.split()) > 1 else "--:--",
                "participants": [{"name": "Vous", "initials": "V"}],
                "agenda": [{"item": user_text[:100], "done": False}],
                "decisions": [],
                "summary": "Rendu forcé par Action Router — réunion à définir.",
            }
        if render_type == "document_draft":
            return {
                "title": "Brouillon",
                "body": user_text,
                "placeholders": ["[compléter]"],
                "summary": "Rendu forcé par Action Router — brouillon à rédiger.",
            }
        if render_type == "timeline":
            return {
                "events": [{"date": now_str, "title": user_text[:60]}],
                "summary": "Rendu forcé par Action Router — chronologie à établir.",
            }
        if render_type == "roadmap":
            return {
                "phases": [{"title": "Phase 1", "description": user_text[:80], "status": "en_cours"}],
                "summary": "Rendu forcé par Action Router — roadmap à construire.",
            }
        if render_type == "comparison":
            return {
                "options": [
                    {"name": "Option A", "pros": ["à définir"], "cons": ["à définir"]},
                    {"name": "Option B", "pros": ["à définir"], "cons": ["à définir"]},
                ],
                "summary": "Rendu forcé par Action Router — comparaison à établir.",
            }
        if render_type == "map_board":
            return {
                "locations": [{"name": user_text[:60], "lat": 0.0, "lng": 0.0}],
                "summary": "Rendu forcé par Action Router — localisation à préciser.",
            }
        # context_panel (default)
        return {
            "sections": [
                {"heading": "Demande", "body": user_text},
                {"heading": "Statut", "body": "Rendu forcé par Action Router — en attente de données complètes."},
            ],
            "summary": "Rendu forcé par Action Router.",
        }


class WebVoiceBridge:
    """Pont audio WebSocket navigateur <-> OpenAI Realtime API."""

    def __init__(
        self,
        openai_api_key: str,
        ws_client,  # FastAPI WebSocket
        context: str = "",
        tool_handler: Optional[Callable[[str, Dict], Awaitable[Dict]]] = None,
        voice: str = OPENAI_VOICE_NAME,
        max_duration_seconds: int = 300,
        greeting: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        vad_eagerness: str = "low",
        # Session collaborative
        session_id: Optional[str] = None,
        participant_id: Optional[str] = None,
        participant_role: str = "owner",
        participant_name: str = "",
        session_manager=None,  # IrisSessionManager | None
        initial_mode: str = DEFAULT_MODE,  # Mode initial transmis via ?mode= (Objectif 026)
    ):
        self.openai_api_key = openai_api_key
        self.ws_client = ws_client
        self.context = context
        self.tool_handler = tool_handler
        self.voice = voice
        self.max_duration_seconds = max_duration_seconds
        self.greeting = greeting
        self.conversation_history = conversation_history or []
        self.vad_eagerness = vad_eagerness
        self.ws_openai = None
        self._running = False
        self._timer_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._elapsed_task: Optional[asyncio.Task] = None
        self.transcript: List[Dict[str, str]] = []
        self._tool_calls_log: List[str] = []
        self._client_errors = 0
        self._openai_errors = 0
        self._last_client_activity = 0.0
        self._start_time = 0.0
        # Session
        self._session_id = session_id
        self._participant_id = participant_id
        self._participant_role = participant_role
        self._participant_name = participant_name
        self._session_manager = session_manager
        # Iris Action Router — fallback deterministe si le LLM n'appelle pas d'outil
        self._action_router = _IrisActionRouter(self)
        # Mode de mission Iris — initialisé depuis le query param ?mode= (Objectif 026)
        self._active_mode = initial_mode if initial_mode in IRIS_MODES else DEFAULT_MODE
        self._base_context = context  # Contexte système de base (sans mode)
        # Fichier de session pour diagnostic autonome — /tmp/iris_sessions/<id>.jsonl
        _sid = session_id or str(uuid.uuid4())[:8]
        self._session_file = _SESSION_LOG_DIR / f"{_sid}_{int(_time.time())}.jsonl"
        _session_log(self._session_file, "session_start", {
            "mode": self._active_mode, "model": "",
        })

    def _client_connected(self) -> bool:
        """Verifie si le WebSocket client est toujours connecte."""
        try:
            return (
                self.ws_client is not None
                and hasattr(self.ws_client, "client_state")
                and self.ws_client.client_state == WebSocketState.CONNECTED
            )
        except Exception:
            return False

    async def _ws_send_openai(self, data: dict, retries: int = 2, critical: bool = True) -> bool:
        """Envoie vers OpenAI. critical=False pour les audio chunks (ne tue pas la session)."""
        if not self.ws_openai or not self._running:
            return False
        payload = json.dumps(data)
        for attempt in range(retries + 1):
            try:
                await asyncio.wait_for(self.ws_openai.send(payload), timeout=15.0)
                self._openai_errors = 0
                return True
            except asyncio.TimeoutError:
                if attempt < retries:
                    await asyncio.sleep(0.3)
                else:
                    self._openai_errors += 1
                    if critical or self._openai_errors >= _MAX_OPENAI_ERRORS:
                        logger.error(f"WebVoice: OpenAI send timeout (critical={critical}, errors={self._openai_errors})")
                        self._running = False
                    return False
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebVoice: OpenAI WS closed during send")
                self._running = False
                return False
            except Exception as e:
                logger.error(f"WebVoice OpenAI send error: {e}")
                self._openai_errors += 1
                if critical or self._openai_errors >= _MAX_OPENAI_ERRORS:
                    self._running = False
                return False
        return False

    async def _ws_send_client(self, data: dict) -> bool:
        """Envoie vers le navigateur. Tolere quelques echecs avant d'arreter."""
        if not self._client_connected():
            self._client_errors += 1
            if self._client_errors >= _MAX_CLIENT_ERRORS:
                logger.info(f"WebVoice: client disconnected ({self._client_errors} errors)")
                self._running = False
            return False
        try:
            await asyncio.wait_for(
                self.ws_client.send_text(json.dumps(data)), timeout=10.0
            )
            self._client_errors = 0
            return True
        except asyncio.TimeoutError:
            self._client_errors += 1
            logger.warning(f"WebVoice: client send timeout ({self._client_errors}/{_MAX_CLIENT_ERRORS})")
            if self._client_errors >= _MAX_CLIENT_ERRORS:
                self._running = False
            return False
        except Exception as e:
            self._client_errors += 1
            logger.warning(f"WebVoice client send error ({self._client_errors}/{_MAX_CLIENT_ERRORS}): {e}")
            if self._client_errors >= _MAX_CLIENT_ERRORS:
                self._running = False
            return False

    async def run(self):
        global _active_bridges

        # Verifier que la cle API est disponible
        if not self.openai_api_key:
            await self._ws_send_client({"type": "error", "message": "Service vocal non configure"})
            return

        async with _realtime_semaphore:
            _active_bridges += 1
            logger.info(f"WebVoiceBridge started (active: {_active_bridges})")
            self._running = True
            try:
                _ws_version = int(websockets.__version__.split(".")[0])
                _headers_kwarg = "additional_headers" if _ws_version >= 13 else "extra_headers"
                _ws_kwargs = {
                    _headers_kwarg: {
                        "Authorization": f"Bearer {self.openai_api_key}",
                    },
                    "close_timeout": 5,
                    "ping_interval": 30,
                    "ping_timeout": 60,  # WebView Android peut bloquer le thread JS > 20s
                }
                self.ws_openai = await asyncio.wait_for(
                    websockets.connect(OPENAI_REALTIME_URL, **_ws_kwargs),
                    timeout=10.0,
                )
                logger.info("WebVoice: OpenAI Realtime connected")

                ok = await self._configure_session()
                if not ok or not self._running:
                    return

                self._start_time = _time.time()
                self._timer_task = asyncio.create_task(self._duration_timer())
                self._keepalive_task = asyncio.create_task(self._client_keepalive())
                self._elapsed_task = asyncio.create_task(self._elapsed_broadcaster())
                self._last_client_activity = _time.time()

                # Injecter l'historique de conversation precedent (reconnexion)
                if self.conversation_history:
                    await self._inject_conversation_history()

                # BOOT VERT — session active, Iris prête
                await self._ws_send_client({"type": "boot_state", "state": "vert"})
                logger.info("[BOOT] VERT — IRIS READY")

                # Notifie le client que la connexion est prete
                await self._ws_send_client({
                    "type": "ready",
                    "max_duration": self.max_duration_seconds,
                })

                # Greeting: Luna parle en premier
                if self.greeting:
                    await self._send_greeting()

                # Les deux taches tournent en parallele — si l'une s'arrete, on arrete l'autre
                done, pending = await asyncio.wait(
                    [
                        asyncio.create_task(self._relay_client_to_openai()),
                        asyncio.create_task(self._relay_openai_to_client()),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                self._running = False
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

            except asyncio.TimeoutError:
                logger.error("WebVoice: OpenAI connection timeout")
                await self._ws_send_client({"type": "error", "message": "Connexion au service vocal impossible. Reessaie."})
            except websockets.exceptions.InvalidStatusCode as e:
                logger.error(f"WebVoice: OpenAI rejected connection: {e}")
                msg = "Service vocal temporairement indisponible"
                if hasattr(e, "status_code") and e.status_code == 401:
                    msg = "Cle API invalide"
                elif hasattr(e, "status_code") and e.status_code == 429:
                    msg = "Trop de sessions vocales en cours. Patiente quelques instants."
                await self._ws_send_client({"type": "error", "message": msg})
            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"WebVoice: OpenAI WS closed: {e}")
            except Exception as e:
                logger.error(f"WebVoiceBridge error: {e}")
                await self._ws_send_client({"type": "error", "message": "Erreur inattendue. Reessaie."})
            finally:
                self._running = False
                _active_bridges = max(0, _active_bridges - 1)
                logger.info(f"WebVoiceBridge ended (active: {_active_bridges})")
                for task in (self._timer_task, self._keepalive_task, self._elapsed_task):
                    if task:
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass
                await self._cleanup()

    async def _client_keepalive(self):
        """Ping le client toutes les 45s — WebView Android peut être lent à répondre."""
        try:
            while self._running:
                await asyncio.sleep(45)
                if not self._running:
                    break
                # Verifie l'inactivite client — 5 min en mode conversationnel
                idle = _time.time() - self._last_client_activity
                if idle > 300:
                    logger.info(f"WebVoice: client idle {idle:.0f}s — stopping")
                    self._running = False
                    await self._ws_send_client({
                        "type": "ended",
                        "reason": "Inactivite detectee — la session se ferme",
                    })
                    break
                # Envoie un ping applicatif
                await self._ws_send_client({"type": "ping"})
        except asyncio.CancelledError:
            pass

    async def _duration_timer(self):
        try:
            # Avertissement 1 minute avant la fin
            warn_at = max(0, self.max_duration_seconds - 60)
            if warn_at > 0:
                await asyncio.sleep(warn_at)
                if self._running:
                    await self._ws_send_client({
                        "type": "warning",
                        "message": "La session se termine dans 1 minute",
                    })
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(self.max_duration_seconds)

            if self._running:
                logger.info(f"WebVoice: max duration reached ({self.max_duration_seconds}s)")
                await self._ws_send_client({
                    "type": "ended",
                    "reason": "Duree maximum atteinte",
                })
                self._running = False
        except asyncio.CancelledError:
            pass

    async def _elapsed_broadcaster(self):
        """Envoie le temps ecoule au client toutes les 10s pour affichage du timer."""
        try:
            while self._running:
                await asyncio.sleep(10)
                if not self._running:
                    break
                elapsed = int(_time.time() - self._start_time)
                remaining = max(0, self.max_duration_seconds - elapsed)
                await self._ws_send_client({
                    "type": "elapsed",
                    "elapsed": elapsed,
                    "remaining": remaining,
                    "max_duration": self.max_duration_seconds,
                })
        except asyncio.CancelledError:
            pass

    async def _inject_conversation_history(self):
        """Injecte l'historique de conversation precedent pour continuite apres reconnexion."""
        if not self.conversation_history:
            return
        # Limiter a 20 derniers echanges pour ne pas surcharger le contexte
        history = self.conversation_history[-20:]
        summary = "=== HISTORIQUE DE CONVERSATION PRECEDENT ===\n"
        summary += "Voici ce qui a ete dit juste avant dans cette conversation :\n"
        for entry in history:
            role = "Utilisateur" if entry.get("role") == "user" else "Luna"
            summary += f"{role}: {entry.get('text', '')}\n"
        summary += "=== FIN HISTORIQUE — Continue la conversation naturellement ===\n"

        # Injecter comme message systeme dans la conversation OpenAI
        await self._ws_send_openai({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": summary}],
            },
        })
        logger.info(f"WebVoice: injected {len(history)} history entries for continuity")

    async def _emit_workspace_plan(self, plan: WorkspacePlan) -> None:
        """Server-first Command Screen render for a work request."""
        if not plan.should_render:
            return
        if plan.mode and plan.mode != self._active_mode and plan.mode in IRIS_MODES:
            await self.set_mode(plan.mode)

        render_msg = {
            "type": "render",
            "render_type": plan.render_type,
            "payload": plan.payload,
            "source": plan.source,
        }
        if self._session_id and self._session_manager:
            await self._session_manager.broadcast(self._session_id, render_msg)
        else:
            await self._ws_send_client(render_msg)
        logger.info(
            f"WebVoice: workspace_orchestrator render_type={plan.render_type} "
            f"mode={self._active_mode} render_done=true"
        )
        _session_log(self._session_file, "workspace_orchestrator", {
            "mode": self._active_mode,
            "render_type": plan.render_type,
            "source": plan.source,
        })

    async def _configure_session(self) -> bool:
        # Lire l'événement initial d'OpenAI (session.created ou error) avant d'envoyer session.update.
        # Si le modèle est invalide ou le quota épuisé, OpenAI envoie un error ici puis ferme le WS.
        try:
            raw = await asyncio.wait_for(self.ws_openai.recv(), timeout=5.0)
            first = json.loads(raw)
            first_type = first.get("type", "?")
            if first_type == "error":
                err = first.get("error", {})
                logger.error(
                    f"WebVoice: OpenAI error avant session.update — code={err.get('code','?')} msg={err.get('message','')[:200]}"
                )
                self._running = False
                await self._ws_send_client({
                    "type": "error",
                    "message": "Service vocal temporairement indisponible.",
                })
                return False
            logger.info(f"WebVoice: OpenAI initial event: {first_type}")
        except asyncio.TimeoutError:
            logger.warning("WebVoice: pas d'événement initial OpenAI (timeout 5s) — on continue")
        except Exception as e:
            logger.warning(f"WebVoice: lecture event initial OpenAI: {e}")

    def _build_filtered_tools(self, mode_id: str) -> List[Dict]:
        """Filtre VOICE_TOOLS selon le mode actif.
        chat n'est inclus qu'en mode discussion — en modes productifs,
        iris_render et les outils métier sont disponibles (tool_choice=auto).
        """
        allowed = set(get_mode_tools(mode_id))
        filtered = [t for t in VOICE_TOOLS if t.get("name", "") in allowed]
        # Dernier recours : fournir iris_render si la liste est vide
        if not filtered:
            fallback = next((t for t in VOICE_TOOLS if t.get("name") == "iris_render"), None)
            if fallback:
                filtered = [fallback]
        return filtered

    async def _configure_session(self):
        """Configure la session OpenAI (voice, VAD, tools)."""
        # BOOT ROUGE — identité et règles en cours de chargement
        await self._ws_send_client({"type": "boot_state", "state": "rouge"})
        logger.info("[BOOT] ROUGE — chargement identité système")

        try:
            raw = await asyncio.wait_for(self.ws_openai.recv(), timeout=5.0)
            first = json.loads(raw)
            first_type = first.get("type", "?")
            if first_type == "error":
                err = first.get("error", {})
                logger.error(
                    f"WebVoice: OpenAI error avant session.update — code={err.get('code','?')} msg={err.get('message','')[:200]}"
                )
                self._running = False
                await self._ws_send_client({
                    "type": "error",
                    "message": "Service vocal temporairement indisponible.",
                })
                return False
            logger.info(f"WebVoice: OpenAI initial event: {first_type}")
        except asyncio.TimeoutError:
            logger.warning("WebVoice: pas d'evenement initial OpenAI (timeout 5s) — on continue")
        except Exception as e:
            logger.warning(f"WebVoice: lecture event initial OpenAI: {e}")

        mode_ctx = build_mode_context(self._active_mode)
        filtered_tools = self._build_filtered_tools(self._active_mode)
        tool_names = [t.get("name", "?") for t in filtered_tools]
        state_block = (
            f"\n\n[IRIS_STATE]\n"
            f"mode_actif={self._active_mode}\n"
            f"command_screen=true\n"
            f"boutons=Modifier,Copier,Télécharger,Fermer\n"
            f"tools_autorisés={','.join(tool_names)}\n"
            f"iris_render_disponible={'iris_render' in tool_names}\n"
            f"document_chargé={'oui' if getattr(self, '_session_documents', []) else 'non'}\n"
            f"[/IRIS_STATE]"
        )
        full_context = self._base_context
        if mode_ctx:
            full_context += f"\n\n{mode_ctx}"
        full_context += state_block

        session_config = {
            "type": "session.update",
            "session": {
                "instructions": full_context,
                "voice": self.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1",
                    "language": "fr",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 400,
                    "silence_duration_ms": 700,
                    # Iris must not answer before the server has the transcript.
                    # We first infer the active mode from the user's words, update
                    # the tool set, then explicitly trigger response.create.
                    "create_response": False,
                },
                "tools": filtered_tools,
                # required fonctionne pour les réponses VAD (voix).
                # Pour les messages texte, iris_render est déclenché côté serveur.
                "tool_choice": "required",
            },
        }
        ok = await self._ws_send_openai(session_config)
        if ok:
            tool_names = [t.get("name", "?") for t in filtered_tools]
            chat_present = "chat" in tool_names
            logger.info(
                f"WebVoice: prompt_marker=IRIS_COMMAND_SCREEN_V1 "
                f"session_model={OPENAI_REALTIME_MODEL} session_voice={self.voice} "
                f"session_mode={self._active_mode} session_tools_count={len(filtered_tools)} "
                f"session_tools={tool_names} chat_present={chat_present} session_updated=true"
            )

            # Ancrage identité via Q&A planté dans l'historique de conversation.
            # Plus fiable que role="system" (non garanti sur gpt-realtime-mini).
            # Le modèle voit sa propre "réponse passée" et reste cohérent.
            await self._ws_send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Iris, qui es-tu et as-tu un panneau visuel ?"}],
                },
            })
            await self._ws_send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    # Realtime API : le type de contenu assistant est "output_text" (pas "text")
                    "content": [{
                        "type": "output_text",
                        "text": (
                            "Je suis Iris, l'opératrice IA du centre de commande YAWatch Luna. "
                            "Oui, j'ai l'Iris Command Screen — mon panneau visuel actif à l'écran en ce moment. "
                            "Je l'alimente via iris_render à chaque réponse."
                        ),
                    }],
                },
            })
            logger.info("[BOOT] Q&A d'ancrage injecté dans l'historique — Iris contextualisée")

            # BOOT ORANGE — vérifications terminées
            await self._ws_send_client({"type": "boot_state", "state": "orange"})
            logger.info("[BOOT] ORANGE — vérifications OK")

        return ok

    async def set_mode(self, mode_id: str) -> bool:
        """Change le mode de mission Iris et met a jour la session OpenAI."""
        mode = IRIS_MODES.get(mode_id)
        if not mode:
            logger.warning(f"WebVoice: mode inconnu '{mode_id}'")
            return False

        self._active_mode = mode_id
        logger.info(f"WebVoice: mode change -> {mode_id} ({mode['label']})")

        mode_ctx = build_mode_context(mode_id)
        filtered_tools = self._build_filtered_tools(mode_id)
        tool_names_set = [t.get("name", "?") for t in filtered_tools]
        state_block = (
            f"\n\n[IRIS_STATE]\n"
            f"mode_actif={mode_id}\n"
            f"command_screen=true\n"
            f"boutons=Modifier,Copier,Télécharger,Fermer\n"
            f"tools_autorisés={','.join(tool_names_set)}\n"
            f"iris_render_disponible={'iris_render' in tool_names_set}\n"
            f"document_chargé={'oui' if getattr(self, '_session_documents', []) else 'non'}\n"
            f"[/IRIS_STATE]"
        )
        full_context = self._base_context
        if mode_ctx:
            full_context += f"\n\n{mode_ctx}"
        full_context += state_block

        session_update = {
            "type": "session.update",
            "session": {
                "instructions": full_context,
                "tools": filtered_tools,
                "tool_choice": "required",
            },
        }
        ok = await self._ws_send_openai(session_update)
        if ok:
            tool_names = [t.get("name", "?") for t in filtered_tools]
            logger.info(
                f"WebVoice: prompt_marker=IRIS_COMMAND_SCREEN_V1 "
                f"session_mode={mode_id} session_tools_count={len(filtered_tools)} "
                f"session_tools={tool_names} chat_present={'chat' in tool_names} session_updated=true"
            )

        await self._ws_send_client({
            "type": "mode_changed",
            "mode": mode_id,
            "label": mode["label"],
            "allowed_tools": mode.get("allowed_tools", []),
            "auto_render": mode.get("auto_render", False),
        })

        if self._session_id and self._session_manager:
            await self._session_manager.broadcast(self._session_id, {
                "type": "mode_changed",
                "mode": mode_id,
                "label": mode["label"],
            })

        return ok

    async def _send_greeting(self):
        """Déclenche la salutation initiale via response.create/instructions (pas de user message)."""
        # On n'envoie PAS de user message — cela forçait OpenAI à reformuler.
        # On utilise response.create avec instructions pour respecter la phrase exacte du system prompt.
        # Greeting : iris_render côté serveur (panneau de bienvenue) + parole sans outils.
        # tool_choice dans response.create cause session.type error sur gpt-realtime-mini.
        await self._ws_send_client({
            "type": "render",
            "render_type": "context_panel",
            "payload": {
                "title": "Iris — Système actif",
                "sections": [{"heading": "Prête", "body": "Tous les systèmes sont opérationnels. Parlez-moi naturellement."}],
                "context": "Session démarrée",
            },
        })
        ok = await self._ws_send_openai({
            "type": "response.create",
            "response": {
                "instructions": self.greeting,
                "tools": [],
            },
        })
        if ok:
            logger.info("WebVoice: greeting triggered via response.create/instructions")
        else:
            logger.warning("WebVoice: greeting trigger failed")

    async def _precompute_doc_renders(self, fname: str, analysis: str):
        """Pre-calcule 8 render types pour un document via GPT-4o-mini."""
        _prompt = (
            f"Tu analyses ce document et génères des données structurées pour des rendus visuels.\n\n"
            f"Document: {fname}\nContenu:\n{analysis[:4000]}\n\n"
            f"Génère un JSON avec ces clés (null si non applicable) :\n"
            f'{{"context_panel":{{"title":"Synthèse — titre court","sections":['
            f'{{"heading":"Résumé","body":"2-3 phrases"}},{{"heading":"Points clés","body":"• point1\\n• point2\\n• point3"}},'
            f'{{"heading":"Conclusion","body":"1 phrase"}}]}},'
            f'"action_board":{{"sections":[{{"title":"Actions","items":[{{"text":"Action réelle du doc","done":false,"tag":"urgent"}}]}}]}},'
            f'"timeline":{{"events":[{{"date":"JJ/MM/AAAA","title":"Jalon réel","description":"détail"}}]}},'
            f'"data_board":{{"title":"Tableau","columns":["Col1","Col2","Col3"],"rows":[["val","val","val"]]}},'
            f'"kanban_board":{{"columns":['
            f'{{"id":"todo","label":"À faire","color":"todo","cards":[{{"title":"Tâche réelle"}}]}},'
            f'{{"id":"doing","label":"En cours","color":"doing","cards":[]}},'
            f'{{"id":"done","label":"Terminé","color":"done","cards":[]}}]}},'
            f'"kpi_cards":{{"kpis":[{{"label":"Indicateur","value":"Valeur chiffrée","trend":"flat"}}]}},'
            f'"budget_board":{{"kpis":[{{"label":"Total","value":"X €","trend":"flat"}}],'
            f'"categories":[{{"name":"Poste","amount":0,"percent":0}}],"summary":""}},'
            f'"document_draft":{{"title":"Réponse à {fname}","recipient":"","body":"Réponse professionnelle rédigée à partir du document"}}}}\n\n'
            f"Règles : extrais uniquement les vraies données du document. "
            f"Max 8 items par liste. Dates réelles si présentes. JSON valide uniquement sans markdown."
        )
        try:
            import openai as _oa
            _client = _oa.AsyncOpenAI(api_key=self.openai_api_key)
            _resp = await _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": _prompt}],
                response_format={"type": "json_object"},
                max_tokens=3000,
                temperature=0.1,
            )
            _renders = json.loads(_resp.choices[0].message.content)
            if not hasattr(self, "_session_doc_renders"):
                self._session_doc_renders = {}
            self._session_doc_renders[fname] = _renders
            self._session_doc_renders["_latest"] = fname
            _available = [k for k, v in _renders.items() if v is not None]
            logger.info(f"WebVoice: precomputed {len(_available)} renders for {fname[:40]}: {_available}")
            await self._ws_send_client({
                "type": "doc_renders_ready",
                "filename": fname,
                "available": _available,
            })
        except Exception as _e:
            logger.error(f"WebVoice: _precompute_doc_renders error: {_e}")

    async def _auto_correct_denial(self):
        """Corrige automatiquement quand Iris nie avoir un panneau ICS."""
        try:
            _doc_ctx = ""
            if hasattr(self, "_session_documents") and self._session_documents:
                _last = max(self._session_documents, key=lambda d: d.get("ts", 0))
                _doc_ctx = f" Document actif : {_last['filename']}."
            await self._ws_send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": (
                        f"[CORRECTION SYSTÈME]{_doc_ctx} "
                        f"Tu AS un panneau Iris Command Screen actif et visible à l'écran maintenant. "
                        f"Appelle iris_render avec le bon render_type et le payload rempli. "
                        f"Ne lis JAMAIS le contenu à l'oral — affiche-le dans le panneau."
                    )}],
                },
            })
            await self._ws_send_openai({
                "type": "response.create",
                "response": {
                    "instructions": (
                        "Appelle iris_render MAINTENANT avec le bon render_type et payload rempli. "
                        "Ne lis pas le contenu à l'oral. 1 phrase courte puis appel iris_render."
                    ),
                    "tools": self._build_filtered_tools(self._active_mode),
                },
            })
            logger.info("WebVoice: auto_correct_denial triggered successfully")
        except Exception as _e:
            logger.error(f"WebVoice: auto_correct_denial error: {_e}")
        finally:
            await asyncio.sleep(15)
            self._denial_correcting = False

    async def _relay_client_to_openai(self):
        """Recoit l'audio PCM16 du navigateur et l'envoie a OpenAI."""
        try:
            async for message in self.ws_client.iter_text():
                if not self._running:
                    break
                self._last_client_activity = _time.time()

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type", "")

                if msg_type == "audio":
                    audio_b64 = data.get("audio", "")
                    if audio_b64 and self.ws_openai:
                        # Audio chunks = non-critical (retries=0, ne tue pas la session)
                        await self._ws_send_openai({
                            "type": "input_audio_buffer.append",
                            "audio": audio_b64,
                        }, retries=0, critical=False)

                elif msg_type == "text":
                    text = str(data.get("text", "")).strip()
                    if text and self.ws_openai:
                        self.transcript.append({"role": "user", "text": text})
                        logger.info(f"WebVoice TEXT USER: {text[:120]}")
                        await self._ws_send_openai({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": text}],
                            },
                        })
                        plan = orchestrate_workspace_request(
                            text,
                            active_mode=self._active_mode,
                            session_documents=getattr(self, "_session_documents", []),
                        )
                        await self._emit_workspace_plan(plan)
                        if plan.should_render:
                            await self._ws_send_openai({
                                "type": "response.create",
                                "response": {
                                    "instructions": (
                                        plan.speech_instruction
                                        + " Ne dis jamais que tu ne peux pas afficher : "
                                          "le serveur vient d'afficher le panneau."
                                    ),
                                    "tools": [],
                                },
                            })
                        else:
                            await self._ws_send_openai({"type": "response.create"})

                elif msg_type == "ui_event":
                    event_name = data.get("name", "")
                    if event_name == "document_uploaded" and self.ws_openai:
                        fname = str(data.get("filename", "fichier"))[:120]
                        analysis = str(data.get("analysis", ""))[:2000]
                        logger.info(f"WebVoice: ui_event document_uploaded fname={fname[:60]}")

                        # Bascule automatique en mode analyse si on est en discussion
                        if self._active_mode == DEFAULT_MODE:
                            logger.info(f"WebVoice: auto_switch_mode discussion -> analyse (document uploaded)")
                            await self.set_mode("analyse")

                        # Stocker le document en memoire de session
                        doc_entry = {"filename": fname, "analysis": analysis, "ts": _time.time()}
                        if not hasattr(self, "_session_documents"):
                            self._session_documents = []
                        self._session_documents.append(doc_entry)

                        # Pré-calculer les rendus en arrière-plan (GPT-4o-mini)
                        asyncio.create_task(self._precompute_doc_renders(fname, analysis))

                        # Injecter un message court — Iris confirme la réception, ne lit pas le contenu
                        inject_text = (
                            f'[DOCUMENT REÇU : {fname}]\n'
                            f'Résumé court : {analysis[:300]}...\n\n'
                            f'Confirme la réception en 1 phrase. '
                            f'Dis que le panneau est mis à jour et que les transformations sont disponibles. '
                            f'Ne lis PAS le contenu à l\'oral.'
                        )
                        await self._ws_send_openai({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": inject_text}],
                            },
                        })
                        await self._ws_send_openai({
                            "type": "response.create",
                            "response": {
                                "instructions": (
                                    "Confirme la réception du document en 1 phrase. "
                                    "Ex: 'Reçu — le panneau est à jour, clique sur les boutons pour transformer.' "
                                    "Ne lis PAS le contenu. Ne liste pas les fonctionnalités."
                                ),
                                "tools": self._build_filtered_tools(self._active_mode),
                            },
                        })

                        # Rendu immédiat document_insight dans le Command Screen
                        # Privé : _ws_send_client envoie uniquement à ce WS (pas de broadcast session)
                        await self._ws_send_client({
                            "type": "render",
                            "render_type": "document_insight",
                            "title": fname,
                            "boxes": [
                                {"title": "Analyse", "body": analysis if analysis else "—"},
                            ],
                            "tags": [
                                {"label": "Reçu", "type": "ok"},
                            ],
                            "actions": [
                                {"label": "Synthèse"},
                                {"label": "Points clés"},
                                {"label": "Tableau"},
                                {"label": "Kanban"},
                                {"label": "Timeline"},
                                {"label": "Contacts"},
                                {"label": "Budget"},
                                {"label": "Rédiger une réponse"},
                            ],
                            "private": True,
                        })
                        logger.info(f"WebVoice: render_type=document_insight fn=upload render_done=true")

                        await self._ws_send_client({
                            "type": "ui_state_ack",
                            "event": "document_uploaded",
                            "filename": fname,
                        })
                        logger.info(f"WebVoice: ui_state_ack document_uploaded fname={fname[:60]}")
                    elif event_name == "doc_action" and self.ws_openai:
                        _da_action = str(data.get("action", "")).strip()
                        _da_fname  = str(data.get("filename", ""))
                        if not _da_fname and hasattr(self, "_session_documents") and self._session_documents:
                            _da_fname = self._session_documents[-1].get("filename", "le document")
                        logger.info(f"WebVoice: ui_event doc_action action={_da_action[:40]} fname={_da_fname[:40]}")

                        _DOC_ACTION_PROMPTS = {
                            "synthese":            ("context_panel",   "Fais une synthese complete du document. Appelle iris_render(render_type='context_panel', payload={title:..., sections:[{heading:'Resume', body:...},{heading:'Points cles', body:...},{heading:'Conclusion', body:...}]}) avec le vrai contenu."),
                            "synthèse":            ("context_panel",   "Fais une synthese complete du document. Appelle iris_render(render_type='context_panel', payload={title:..., sections:[{heading:'Resume', body:...},{heading:'Points cles', body:...},{heading:'Conclusion', body:...}]}) avec le vrai contenu."),
                            "points cles":         ("action_board",    "Liste les points cles et actions a retenir. Appelle iris_render(render_type='action_board', payload={sections:[{title:'Actions', items:[{text:'...',done:false},...]}]}) avec les vrais items du document."),
                            "points clés":         ("action_board",    "Liste les points cles et actions a retenir. Appelle iris_render(render_type='action_board', payload={sections:[{title:'Actions', items:[{text:'...',done:false},...]}]}) avec les vrais items du document."),
                            "tableau":             ("data_board",      "Transforme le contenu en tableau structure. Appelle iris_render(render_type='data_board', payload={title:'...', columns:[...], rows:[[...]]}) avec les vraies donnees du document."),
                            "kanban":              ("kanban_board",    "Organise les taches en Kanban. Appelle iris_render(render_type='kanban_board', payload={columns:[{id:'todo',label:'A faire',color:'todo',cards:[{title:'...'}]},{id:'doing',label:'En cours',color:'doing',cards:[]},{id:'done',label:'Termine',color:'done',cards:[]}]}) avec les taches reelles du document."),
                            "timeline":            ("timeline",        "Extrais toutes les dates et jalons. Appelle iris_render(render_type='timeline', payload={events:[{date:'JJ/MM/AAAA',title:'...',description:'...'}]}) avec les vraies dates du document."),
                            "rediger une reponse": ("document_draft",  "Redige une reponse professionnelle. Appelle iris_render(render_type='document_draft', payload={title:'Reponse a ...', recipient:'...', body:'...'}) avec le contenu adapte au document."),
                            "rédiger une réponse": ("document_draft",  "Redige une reponse professionnelle. Appelle iris_render(render_type='document_draft', payload={title:'Reponse a ...', recipient:'...', body:'...'}) avec le contenu adapte au document."),
                            "contacts":            ("contact_board",   "Extrais tous les noms et coordonnees mentionnes. Appelle iris_render(render_type='data_board', payload={title:'Contacts', columns:['Nom','Role','Contact'], rows:[...]}) avec les vraies personnes du document."),
                            "budget":              ("budget_board",    "Extrais les donnees financieres et montants. Appelle iris_render(render_type='budget_board', payload={kpis:[{label:'...', value:'...€', trend:'flat'}], categories:[{name:'...', amount:0, percent:0}], summary:'...'}) avec les vrais chiffres."),
                            "sauvegarder":         ("",                "Sauvegarde ce document dans le vault Luna de l'utilisateur et confirme."),
                        }
                        _key = _da_action.lower().strip()
                        _ACTION_TO_RTYPE = {
                            "synthese": "context_panel", "synthèse": "context_panel",
                            "points cles": "action_board", "points clés": "action_board",
                            "tableau": "data_board",
                            "kanban": "kanban_board",
                            "timeline": "timeline",
                            "contacts": "contact_board",
                            "budget": "budget_board",
                            "rediger une reponse": "document_draft",
                            "rédiger une réponse": "document_draft",
                        }
                        _rtype = _ACTION_TO_RTYPE.get(_key, "context_panel")

                        # Chercher le rendu pré-calculé
                        _precomputed = None
                        if hasattr(self, "_session_doc_renders"):
                            _dr = self._session_doc_renders.get(_da_fname)
                            if not _dr:
                                _latest_name = self._session_doc_renders.get("_latest", "")
                                _dr = self._session_doc_renders.get(_latest_name, {}) if _latest_name else {}
                            if isinstance(_dr, dict):
                                _precomputed = _dr.get(_rtype)

                        if _precomputed:
                            # Rendu pré-calculé : envoi direct au client, SANS passer par le modèle
                            _render_msg = {"type": "render", "render_type": _rtype}
                            _render_msg.update(_precomputed)
                            await self._ws_send_client(_render_msg)
                            logger.info(f"WebVoice: doc_action precomputed render sent rtype={_rtype}")

                            # Iris confirme en 1 phrase — elle ne génère PAS les données
                            await self._ws_send_openai({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": (
                                        f"[SYSTÈME : Le panneau '{_rtype}' a été affiché automatiquement "
                                        f"pour '{_da_fname}'. Dis 1 phrase de confirmation courte. "
                                        f"Ex: 'Voilà le kanban — les tâches sont organisées.' "
                                        f"Ne décris pas chaque item. Ne lis pas le contenu."
                                    )}],
                                },
                            })
                            await self._ws_send_openai({
                                "type": "response.create",
                                "response": {
                                    "instructions": "1 phrase de confirmation du panneau affiché. Rien de plus.",
                                    "tools": [],
                                },
                            })
                        else:
                            # Fallback si pré-calcul pas encore prêt
                            _rtype_fb, _instruction_fb = _DOC_ACTION_PROMPTS.get(_key, (
                                "context_panel",
                                f"Effectue '{_da_action}' sur ce document et appelle iris_render."
                            ))
                            _doc_text = ""
                            if hasattr(self, "_session_documents") and self._session_documents:
                                _last = max(self._session_documents, key=lambda d: d.get("ts", 0))
                                _doc_text = _last.get("analysis", "")
                            await self._ws_send_openai({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": (
                                        f"[ACTION : {_da_action} — {_da_fname}]\n"
                                        f"Contenu : {_doc_text[:2000]}\n\n{_instruction_fb}\n"
                                        f"OBLIGATOIRE : appelle iris_render. Ne lis PAS le contenu à l'oral."
                                    )}],
                                },
                            })
                            await self._ws_send_openai({
                                "type": "response.create",
                                "response": {
                                    "instructions": (
                                        f"Appelle iris_render(render_type='{_rtype_fb}') avec les vraies données. "
                                        f"1 phrase courte. Ne lis PAS le contenu à l'oral."
                                    ),
                                    "tools": self._build_filtered_tools(self._active_mode),
                                },
                            })
                            logger.info(f"WebVoice: doc_action fallback (no precomputed) rtype={_rtype_fb}")

                    else:
                        logger.info(f"WebVoice: ui_event unhandled name={event_name}")

                elif msg_type == "mode_select":
                    mode_id = data.get("mode", "")
                    if mode_id:
                        await self.set_mode(mode_id)
                    else:
                        logger.warning("WebVoice: mode_select sans mode_id")

                elif msg_type == "stop":
                    logger.info("WebVoice: client requested stop")
                    self._running = False
                    break

                elif msg_type == "pong":
                    pass  # Reponse au ping keepalive

        except websockets.exceptions.ConnectionClosed:
            if self._running:
                logger.info("WebVoice: client WS closed")
        except Exception as e:
            if self._running:
                logger.error(f"WebVoice client relay error: {e}")
        self._running = False

    async def _relay_openai_to_client(self):
        """Recoit l'audio d'OpenAI et l'envoie au navigateur."""
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
                    logger.info("WebVoice: OpenAI session created")

                elif event_type == "session.updated":
                    logger.info("WebVoice: session_updated=true")

                elif event_type in ("response.audio.delta", "response.output_audio.delta"):
                    audio_delta = data.get("delta", "")
                    if audio_delta:
                        await self._ws_send_client({
                            "type": "audio",
                            "audio": audio_delta,
                        })

                elif event_type in ("response.audio.done", "response.output_audio.done"):
                    await self._ws_send_client({"type": "audio_done"})

                elif event_type == "input_audio_buffer.speech_started":
                    logger.debug("WebVoice: user speaking — interrupt")
                    await self._ws_send_openai({"type": "response.cancel"}, retries=1, critical=False)
                    await self._ws_send_client({"type": "interrupt"})

                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.debug("WebVoice: user stopped speaking")

                elif event_type == "input_audio_buffer.committed":
                    logger.debug("WebVoice: audio buffer committed")

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = data.get("transcript", "").strip()
                    if text:
                        self.transcript.append({"role": "user", "text": text})
                        logger.info(f"WebVoice USER: {text[:120]}")
                        self._action_router.on_user_transcript(text)
                        # Fallback mode auto — si le client a envoyé mode=discussion (défaut)
                        # et que le texte suggère un mode productif, basculer automatiquement
                        if self._active_mode == DEFAULT_MODE:
                            detected = detect_mode_from_text(text)
                            if detected != DEFAULT_MODE:
                                logger.info(f"WebVoice: mode_auto_detected={detected} from user text")
                                await self.set_mode(detected)
                                await self._ws_send_client({
                                    "type": "mode_changed",
                                    "mode": detected,
                                    "label": IRIS_MODES[detected]["label"],
                                })
                        await self._ws_send_client({
                            "type": "transcript",
                            "role": "user",
                            "text": text,
                        })
                        plan = orchestrate_workspace_request(
                            text,
                            active_mode=self._active_mode,
                            session_documents=getattr(self, "_session_documents", []),
                        )
                        await self._emit_workspace_plan(plan)
                        if plan.should_render:
                            await self._ws_send_openai({
                                "type": "response.create",
                                "response": {
                                    "instructions": (
                                        plan.speech_instruction
                                        + " Reponds en une phrase courte, sans relire le contenu du panneau."
                                    ),
                                    "tools": [],
                                },
                            })
                            logger.info(
                                f"WebVoice: response_created_after_orchestrator "
                                f"mode={self._active_mode} render_type={plan.render_type}"
                            )
                        else:
                            await self._ws_send_openai({"type": "response.create"})
                            logger.info(
                                f"WebVoice: response_created_after_mode mode={self._active_mode}"
                            )

                elif event_type in ("response.audio_transcript.done", "response.output_audio_transcript.done"):
                    text = data.get("transcript", "").strip()
                    if text:
                        self.transcript.append({"role": "luna", "text": text})
                        logger.info(f"WebVoice LUNA: {text[:120]}")
                        _session_log(self._session_file, "iris_transcript", {"text": text[:300]})
                        self._action_router.on_iris_transcript(text)
                        await self._ws_send_client({
                            "type": "transcript",
                            "role": "luna",
                            "text": text,
                        })
                        # Garde-fou : détecter le déni du panneau ICS et corriger en temps réel
                        _DENIAL_PHRASES = [
                            "ne peux pas afficher", "n'ai pas de panneau", "pas de panneau visuel",
                            "je ne dispose pas d'un panneau", "pas d'écran", "aucun panneau",
                            "cannot display", "don't have a visual panel",
                        ]
                        _tlow = text.lower()
                        if (not getattr(self, "_denial_correcting", False)
                                and any(p in _tlow for p in _DENIAL_PHRASES)
                                and (
                                    (hasattr(self, "_session_documents") and self._session_documents)
                                    or self._active_mode != DEFAULT_MODE
                                )):
                            logger.warning(f"WebVoice: iris_panel_denial detected — auto-correcting")
                            self._denial_correcting = True
                            asyncio.create_task(self._auto_correct_denial())

                elif event_type == "response.function_call_arguments.done":
                    # Notifier le router AVANT le traitement pour annuler tout fallback
                    call_id = data.get("call_id", "")
                    function_name = data.get("name", "")
                    if function_name:
                        self._action_router.on_tool_call(function_name)
                    await self._handle_tool_call(data)

                elif event_type == "response.done":
                    self._delta_buf = ""
                    self._delta_cancelled = False

                elif event_type == "rate_limits.updated":
                    pass  # Info OpenAI, ignorer

                elif event_type == "input_audio_buffer.cleared":
                    pass

                elif event_type == "response.created":
                    pass

                elif event_type == "response.output_item.added":
                    pass

                elif event_type == "response.content_part.added":
                    pass

                elif event_type == "response.content_part.done":
                    pass

                elif event_type == "response.output_item.done":
                    pass

                elif event_type == "conversation.item.created":
                    pass

                elif event_type in ("response.audio_transcript.delta", "response.output_audio_transcript.delta"):
                    # Accumulation du delta pour détection précoce du déni
                    _delta = data.get("delta", "").lower()
                    if _delta:
                        if not hasattr(self, "_delta_buf"):
                            self._delta_buf = ""
                        self._delta_buf += _delta
                        # Phrases qui ne doivent jamais sortir d'Iris
                        _EARLY_DENIAL = [
                            "ne peux pas afficher", "n'ai pas de panneau",
                            "pas de panneau visuel", "je ne dispose pas d'un panneau",
                        ]
                        _has_doc = hasattr(self, "_session_documents") and bool(self._session_documents)
                        _in_work_mode = self._active_mode != DEFAULT_MODE
                        if ((_has_doc or _in_work_mode)
                                and not getattr(self, "_delta_cancelled", False)
                                and not getattr(self, "_denial_correcting", False)
                                and any(p in self._delta_buf for p in _EARLY_DENIAL)):
                            self._delta_cancelled = True
                            self._delta_buf = ""
                            self._denial_correcting = True
                            logger.warning("WebVoice: denial intercepted in delta — cancelling response")
                            await self._ws_send_openai({"type": "response.cancel"})
                            await self._ws_send_client({"type": "audio_cancel"})
                            asyncio.create_task(self._auto_correct_denial())

                elif event_type in ("conversation.item.done", "conversation.item.added"):
                    pass

                elif event_type == "conversation.item.input_audio_transcription.failed":
                    logger.warning(f"WebVoice: transcription failed: {data.get('error', {})}")
                    # Non fatal — l'audio a ete traite, juste pas de transcript

                elif event_type == "error":
                    error_info = data.get("error", {})
                    error_code = error_info.get("code", "")
                    error_msg = error_info.get("message", "")

                    if error_code == "response_cancel_not_active":
                        pass  # Benin — on a cancel une reponse qui n'existait plus
                    elif error_code in ("invalid_request_error",):
                        # Souvent un audio mal forme — non fatal sauf si repetitif
                        self._openai_errors += 1
                        logger.warning(f"WebVoice OpenAI non-fatal error ({self._openai_errors}): {error_msg[:200]}")
                        if self._openai_errors >= _MAX_OPENAI_ERRORS:
                            logger.error("WebVoice: too many OpenAI errors — stopping")
                            self._running = False
                            await self._ws_send_client({
                                "type": "error",
                                "message": "Trop d'erreurs de communication. Reessaie.",
                            })
                            break
                    elif error_code in ("authentication_failed", "rate_limit_exceeded", "server_error"):
                        logger.error(f"WebVoice OpenAI FATAL error: {error_info}")
                        self._running = False
                        _user_msg = {
                            "rate_limit_exceeded": "Trop de demandes simultanees. Reessaie dans un instant.",
                            "authentication_failed": "Probleme d'authentification avec le service vocal.",
                            "server_error": "Le service vocal rencontre un probleme. Reessaie.",
                        }.get(error_code, "Erreur du service vocal.")
                        await self._ws_send_client({
                            "type": "error",
                            "message": _user_msg,
                        })
                        break
                    else:
                        # Erreur inconnue — log mais ne tue pas
                        logger.warning(f"WebVoice OpenAI unknown error: {error_info}")
                        self._openai_errors += 1
                        if self._openai_errors >= _MAX_OPENAI_ERRORS:
                            self._running = False
                            break

                else:
                    # Evenement inconnu — ignorer silencieusement
                    logger.debug(f"WebVoice: unhandled event: {event_type}")

        except websockets.exceptions.ConnectionClosed as e:
            if self._running:
                logger.info(f"WebVoice: OpenAI WS closed: {e}")
                await self._ws_send_client({"type": "error", "message": "Connexion au service vocal perdue. Reessaie."})
            self._running = False
        except Exception as e:
            if self._running:
                logger.error(f"WebVoice OpenAI relay error: {e}")
                await self._ws_send_client({"type": "error", "message": "Erreur de communication. Reessaie."})
            self._running = False

    async def _handle_tool_call(self, data: Dict):
        call_id = data.get("call_id", "")
        function_name = data.get("name", "")
        arguments_str = data.get("arguments", "{}")

        if not call_id:
            logger.warning(f"WebVoice: tool call without call_id: {function_name}")
            return

        try:
            args = json.loads(arguments_str)
        except json.JSONDecodeError:
            args = {}

        logger.info(f"WebVoice tool_call: {function_name}({args})")
        _session_log(self._session_file, "tool_call", {"name": function_name, "args_keys": list(args.keys()) if isinstance(args, dict) else []})

        def _normalize_iris_render_args(raw_args: Dict) -> tuple[str, Dict, str]:
            """Accept both strict {render_type, payload} and direct render fields.

            OpenAI usually follows the tool schema, but under pressure it can send
            {render_type, title, rows, boxes...}. The client only sees what the
            server forwards, so never let a valid direct render become payload={}.
            """
            if not isinstance(raw_args, dict):
                return "missing_info", {
                    "title": "Rendu impossible",
                    "fields": ["Arguments iris_render illisibles"],
                    "context": "Iris a appelé l'outil, mais les données reçues ne sont pas un objet JSON.",
                }, "invalid_args"

            render_type = str(raw_args.get("render_type") or "context_panel")
            payload = raw_args.get("payload")
            if isinstance(payload, dict) and payload:
                return render_type, payload, "payload"

            direct_payload = {
                k: v for k, v in raw_args.items()
                if k not in {"render_type", "payload"} and v not in (None, "", [], {})
            }
            if direct_payload:
                return render_type, direct_payload, "args_unwrapped"

            last_user_text = getattr(self._action_router, "_last_user_text", "") if self._action_router else ""
            return "missing_info", {
                "title": "Informations manquantes",
                "fields": ["Le contenu à afficher", "Les données du tableau ou du document"],
                "context": last_user_text[:240] or "Iris a appelé le panneau sans fournir de contenu exploitable.",
                "summary": "Le Command Screen est prêt, mais l'appel iris_render était vide.",
            }, "empty_payload_fallback"

        # chat : reponse conversationnelle simple
        if function_name == "chat":
            msg = args.get("message", "")
            logger.info(f"WebVoice chat: {msg[:120]}")
            await self._ws_send_client({
                "type": "tool_call",
                "name": "chat",
                "status": "ok",
                "message": msg[:200],
            })
            await self._ws_send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"status": "ok", "message": msg}, ensure_ascii=False),
                },
            })
            await self._ws_send_openai({"type": "response.create"})
            return

        # iris_render : affichage Iris Workspace — broadcast session ou envoi direct
        if function_name == "iris_render":
            render_type, payload, payload_source = _normalize_iris_render_args(args)
            render_msg = {"type": "render", "render_type": render_type, "payload": payload}
            if self._session_id and self._session_manager:
                await self._session_manager.broadcast(self._session_id, render_msg)
            else:
                await self._ws_send_client(render_msg)
            logger.info(
                f"WebVoice: render_type={render_type} fn=iris_render "
                f"payload_source={payload_source} keys={list(payload.keys())[:12]} render_done=true"
            )
            _session_log(self._session_file, "iris_render", {"render_type": render_type, "source": payload_source})

            # Enrichissement async quand le modèle a appelé iris_render avec payload vide
            if payload_source == "empty_payload_fallback" and self._action_router:
                _usr = getattr(self._action_router, "_last_user_text", "")
                _real_type = self._action_router._infer_render_type(_usr) if _usr else "context_panel"
                if _real_type != "context_panel" and _usr:
                    _send_fn_v = (
                        (lambda m: self._session_manager.broadcast(self._session_id, m))
                        if (self._session_id and self._session_manager)
                        else self._ws_send_client
                    )
                    asyncio.create_task(
                        self._action_router._enrich_payload_async(_real_type, _usr, _send_fn_v)
                    )

            await self._ws_send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({
                        "status": "ok",
                        "displayed": True,
                        "render_type": render_type,
                        "payload_source": payload_source,
                    }, ensure_ascii=False),
                },
            })
            # tools:[] dans response.create overrides la session pour cette réponse uniquement.
            # Sans outil disponible, le modèle est forcé de parler — boucle iris_render brisée.
            # Note: tool_choice:"none" cause une erreur session.type sur gpt-realtime-mini.
            await self._ws_send_openai({
                "type": "response.create",
                "response": {"tools": []},
            })
            self._tool_calls_log.append(f"iris_render:{render_type}")
            return

        # invite_to_session : crée un invité et retourne un lien
        if function_name == "invite_to_session":
            if not self._session_id or not self._session_manager:
                _tool_result = {"status": "error",
                                "message": "Aucune session active. Démarre une session via le bouton dans l'interface."}
            else:
                name = args.get("name", "Invité")
                role = args.get("role", "guest")
                project_filter = args.get("project_filter", [])
                pid = str(uuid.uuid4())[:8]
                participant = {
                    "participant_id": pid,
                    "session_id": self._session_id,
                    "name": name,
                    "role": role,
                    "projects_allowed": project_filter,
                    "can_trigger_actions": False,
                }
                self._session_manager.add_participant(self._session_id, participant)
                invite_token = self._session_manager.create_invite(self._session_id, pid)
                base_url = os.getenv("VOICE_CALLBACK_URL", "")
                invite_link = f"{base_url}/join/{invite_token}"
                # Notifier les autres participants via session_panel render
                participants = self._session_manager.get_participants(self._session_id)
                session = self._session_manager.get_session(self._session_id)
                await self._session_manager.broadcast(self._session_id, {
                    "type": "render",
                    "render_type": "session_panel",
                    "payload": {
                        "session_name": session.get("name", "Session Iris") if session else "Session Iris",
                        "participants": [
                            {"name": p["name"], "role": p["role"], "status": "active" if p.get("online") else "invited"}
                            for p in participants
                        ],
                        "pending_actions": [],
                    },
                })
                _tool_result = {
                    "status": "ok",
                    "message": f"Invitation créée pour {name}.",
                    "invite_link": invite_link,
                    "role": role,
                    "participant_id": pid,
                }
                logger.info(f"Iris invite created: {name} ({role}) → {invite_link}")
            await self._ws_send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(_tool_result, ensure_ascii=False),
                },
            })
            await self._ws_send_openai({"type": "response.create"})
            return

        # Gating actions sensibles pour les invités (non-owner)
        _SENSITIVE_TOOLS = {"send_sms", "send_email", "call_contact", "alert_contacts",
                            "invite_visio", "generate_document", "request_payment",
                            "book_restaurant", "search_flights", "search_hotels",
                            "add_expense", "add_reminder", "create_instruction", "create_note"}
        if self._participant_role != "owner" and function_name in _SENSITIVE_TOOLS:
            if self._session_id and self._session_manager:
                aid = self._session_manager.create_pending_action(self._session_id, {
                    "action_type": function_name,
                    "payload": args,
                    "requested_by_name": self._participant_name,
                    "requested_by_id": self._participant_id,
                })
                await self._session_manager.notify_owner(self._session_id, {
                    "type": "action_pending",
                    "action_id": aid,
                    "action_type": function_name,
                    "requested_by": self._participant_name,
                    "payload": args,
                })
                _gate_result = {
                    "status": "pending_owner_approval",
                    "action_id": aid,
                    "message": f"Action '{function_name}' soumise au souscripteur pour validation.",
                }
            else:
                _gate_result = {
                    "status": "validation_required",
                    "message": "Action sensible bloquée — validation du souscripteur requise.",
                }
            await self._ws_send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(_gate_result, ensure_ascii=False),
                },
            })
            await self._ws_send_openai({"type": "response.create"})
            return

        # hang_up : arrêter le bridge proprement
        if function_name == "hang_up":
            reason = args.get("reason", "fin de conversation")
            logger.info(f"WebVoice hang_up: {reason}")
            tool_response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"status": "ok", "message": "Appel terminé."}, ensure_ascii=False),
                },
            }
            await self._ws_send_openai(tool_response)
            await self._ws_send_client({"type": "tool_call", "name": "hang_up", "status": "ok", "message": "Appel terminé."})
            await asyncio.sleep(2)
            self._running = False
            return

        # Notifie le client qu'un tool est en cours
        logger.info(f"WebVoice tool_call notify client: {function_name} -> running")
        await self._ws_send_client({
            "type": "tool_call",
            "name": function_name,
            "status": "running",
        })

        _tool_start = _time.time()
        result = {"status": "error", "message": "Fonction non disponible"}
        if self.tool_handler:
            try:
                result = await asyncio.wait_for(
                    self.tool_handler(function_name, args), timeout=45.0
                )
                if not isinstance(result, dict):
                    result = {"status": "error", "message": "Reponse invalide de la fonction"}
            except asyncio.TimeoutError:
                result = {"status": "error", "message": "Operation trop longue, reessaie"}
            except Exception as e:
                logger.error(f"WebVoice tool {function_name} exception: {e}")
                result = {"status": "error", "message": f"Erreur lors de l'execution: {type(e).__name__}"}
        _tool_elapsed = _time.time() - _tool_start
        logger.info(f"WebVoice tool {function_name}: {_tool_elapsed:.1f}s -> {result.get('status', '?')}")

        # Anti-hallucination : si une action echoue, forcer Luna a le dire
        _ACTION_TOOLS = {"call_contact", "send_sms", "send_email", "alert_contacts",
                         "invite_visio", "generate_document", "send_dm_voice"}
        if result.get("status") == "error" and function_name in _ACTION_TOOLS:
            result["IMPORTANT"] = (
                f"L'action {function_name} a ECHOUE. Informe le souscripteur. "
                f"N'invente RIEN."
            )

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

        # Notifie le client du resultat
        await self._ws_send_client({
            "type": "tool_call",
            "name": function_name,
            "status": result.get("status", "unknown"),
            "message": result.get("message", "")[:100],
        })

        self._tool_calls_log.append(f"{function_name}: {result.get('status', '?')}")

    async def _cleanup(self):
        self._running = False
        if self.ws_openai:
            try:
                await self.ws_openai.close()
            except Exception:
                pass
            self.ws_openai = None
        logger.info(f"WebVoiceBridge cleanup ({len(self.transcript)} entries)")
