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
import asyncio
import logging
import time as _time
from typing import Optional, Dict, Any, Callable, Awaitable, List

import websockets
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

import os

OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
OPENAI_REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_REALTIME_MODEL}"
OPENAI_VOICE_NAME = os.getenv("OPENAI_VOICE_NAME", "alloy")

# Import des tools depuis le bridge Twilio (meme jeu de tools)
from integrations.openai.realtime_bridge import VOICE_TOOLS, _realtime_semaphore, _active_bridges

# Nombre d'erreurs client consecutives avant arret
_MAX_CLIENT_ERRORS = 3
# Nombre d'erreurs OpenAI consecutives (hors audio) avant arret
_MAX_OPENAI_ERRORS = 5


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
                    "ping_interval": 20,
                    "ping_timeout": 20,
                }
                self.ws_openai = await asyncio.wait_for(
                    websockets.connect(OPENAI_REALTIME_URL, **_ws_kwargs),
                    timeout=10.0,
                )
                logger.info("WebVoice: OpenAI Realtime connected")

                await self._configure_session()

                self._start_time = _time.time()
                self._timer_task = asyncio.create_task(self._duration_timer())
                self._keepalive_task = asyncio.create_task(self._client_keepalive())
                self._elapsed_task = asyncio.create_task(self._elapsed_broadcaster())
                self._last_client_activity = _time.time()

                # Injecter l'historique de conversation precedent (reconnexion)
                if self.conversation_history:
                    await self._inject_conversation_history()

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
        """Ping le client toutes les 25s pour detecter les deconnexions tot."""
        try:
            while self._running:
                await asyncio.sleep(25)
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

    async def _configure_session(self):
        # Format API Realtime GA (post-beta) — audio imbriqué sous audio.input/output
        session_config = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "instructions": self.context,
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "transcription": {"model": "whisper-1"},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 500,
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "voice": self.voice,
                    },
                },
                "tools": VOICE_TOOLS,
                "tool_choice": "auto",
            },
        }
        await self._ws_send_openai(session_config)
        logger.info("WebVoice: session configured (audio/pcm 24kHz, server_vad)")

    async def _send_greeting(self):
        """Envoie un message initial pour que Luna salue le souscripteur."""
        greeting_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": self.greeting}],
            },
        }
        await self._ws_send_openai(greeting_event)
        await self._ws_send_openai({"type": "response.create"})
        logger.info("WebVoice: greeting sent")

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
                    logger.debug("WebVoice: OpenAI session updated")

                elif event_type == "response.audio.delta":
                    audio_delta = data.get("delta", "")
                    if audio_delta:
                        await self._ws_send_client({
                            "type": "audio",
                            "audio": audio_delta,
                        })

                elif event_type == "response.audio.done":
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
                        await self._ws_send_client({
                            "type": "transcript",
                            "role": "user",
                            "text": text,
                        })

                elif event_type == "response.audio_transcript.done":
                    text = data.get("transcript", "").strip()
                    if text:
                        self.transcript.append({"role": "luna", "text": text})
                        logger.info(f"WebVoice LUNA: {text[:120]}")
                        await self._ws_send_client({
                            "type": "transcript",
                            "role": "luna",
                            "text": text,
                        })

                elif event_type == "response.function_call_arguments.done":
                    await self._handle_tool_call(data)

                elif event_type == "response.done":
                    pass  # Fin de reponse, rien a faire

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

                elif event_type == "response.audio_transcript.delta":
                    pass  # Partial transcript, handled at .done

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
