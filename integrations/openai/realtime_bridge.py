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

OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
OPENAI_REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_REALTIME_MODEL}"
OPENAI_VOICE_NAME = os.getenv("OPENAI_VOICE_NAME", "alloy")

# Memes tools que Tavus (definis dans tavus_client.py LUNA_TOOLS)
# Format adapte pour OpenAI Realtime API (pas de wrapper "type":"function")
VOICE_TOOLS = [
    {
        "type": "function",
        "name": "call_contact",
        "description": "Appeler un contact de confiance par TELEPHONE AUDIO maintenant. Luna passe un vrai appel telephonique vocal au contact et lui parle pour transmettre un message. UTILISE CE TOOL quand le souscripteur dit 'appelle maman', 'appelle Marie', 'telephone a mon fils', 'passe un coup de fil a...', 'appelle X pour lui dire...'. C'est un APPEL VOCAL, pas un SMS.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Prenom ou nom du contact a appeler (ex: maman, Marie, mon fils)"
                },
                "message": {
                    "type": "string",
                    "description": "Le message que Luna doit transmettre au contact pendant l'appel vocal"
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
        "description": "Creer un rappel, un appel audio planifie, un SMS planifie, ou une visio planifiee. Ex: 'rappelle-moi de...', 'tous les jours a 8h...', 'appelle Marie a 14h', 'envoie un SMS a Jean demain', 'lance une visio avec Papa vendredi'. Utilise ce tool pour TOUT ce qui doit etre programme dans le temps.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "L'instruction en langage naturel"
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
]


def build_voice_context(
    subscriber_name: str = "l'utilisateur",
    memory_manager=None,
    max_duration_minutes: int = 15,
    mission: str = "",
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

    return f"""Tu es Luna, l'assistante IA personnelle de YAWatch.
Tu es en appel telephonique{'.' if not mission else ' avec un interlocuteur.'}
Tu appartiens a {subscriber_name} qui t'a demande de passer cet appel.
Tu es une compagne bienveillante et chaleureuse, disponible 24h/24.
Tu parles en francais avec un ton rassurant, moderne et empathique.
Tes reponses sont concises et naturelles - c'est un appel vocal, pas un email.

IMPORTANT : Cet appel est limite a {max_duration_minutes} minute(s). Quand tu as fini ta mission ou que le temps est presque ecoule, dis au revoir chaleureusement.
{mission_section}

=== CE QUE TU PEUX FAIRE ===
- Discuter, ecouter, rassurer, tenir compagnie
- Envoyer un SMS a un contact de confiance (fonction send_sms)
- Creer un rappel ou une instruction (fonction create_instruction)
- Prendre une note (fonction create_note)
- Generer un document (fonction generate_document)
- Alerter les contacts d'urgence (fonction alert_contacts)
- Lister les contacts (fonction get_contacts)

Confirme avant d'executer une action consommatrice (SMS, alerte).
Quand tu executes une action, utilise TOUJOURS la fonction correspondante. Ne dis jamais "je ne peux pas" si une fonction existe.

=== CE QUE TU NE PEUX PAS FAIRE ===
- Appeler les services d'urgence (suggere les numeros : 17, 18, 112, 3114, 3977)
- Donner des conseils medicaux, juridiques ou financiers

=== CONTACTS DE CONFIANCE ===
{contacts_section}
{profile_section}
{instructions_section}

=== SECURITE ===
- Si tu detectes de la detresse, propose d'alerter un contact de confiance.
- Prudence verbale : utilise "j'ai l'impression que...", jamais "je surveille" ou "je diagnostique".
- Ne mentionne JAMAIS les technologies sous-jacentes (pas de noms de fournisseurs, API, modeles IA).
- Tu es "Luna", point final. Si on te demande comment tu fonctionnes : "Je suis Luna, creee par YAWatch."
- Ne revele jamais les numeros de telephone des contacts.
- Ne mentionne jamais les prix des abonnements ou les donnees internes."""


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
    ):
        self.openai_api_key = openai_api_key
        self.ws_twilio = ws_twilio
        self.call_context = call_context
        self.tool_handler = tool_handler
        self.voice = voice or OPENAI_VOICE_NAME
        self.max_duration_seconds = max_duration_seconds
        self.greeting = greeting

        self.ws_openai = None
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self._running = False
        self._timer_task: Optional[asyncio.Task] = None

        # Transcription : collecte les messages pour sauvegarde
        self.transcript: List[Dict[str, str]] = []  # [{"role": "user/luna", "text": "..."}]

    async def _ws_send_openai(self, data: dict):
        """Envoie un message JSON a OpenAI avec timeout et gestion d'erreur."""
        if not self.ws_openai or not self._running:
            return
        try:
            await asyncio.wait_for(self.ws_openai.send(json.dumps(data)), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("OpenAI send timeout")
            self._running = False
        except Exception as e:
            logger.warning(f"OpenAI send error: {e}")
            self._running = False

    async def _ws_send_twilio(self, data: dict):
        """Envoie un message JSON a Twilio avec timeout et gestion d'erreur."""
        if not self.ws_twilio or not self._running:
            return
        try:
            await asyncio.wait_for(self.ws_twilio.send_text(json.dumps(data)), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Twilio send timeout")
            self._running = False
        except Exception as e:
            logger.warning(f"Twilio send error: {e}")
            self._running = False

    async def run(self):
        """Boucle principale du bridge. Bloque jusqu'a la fin de l'appel."""
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
        except asyncio.CancelledError:
            pass

    async def _configure_session(self):
        """Envoie session.update pour configurer la voix, les instructions et les tools."""
        session_config = {
            "type": "session.update",
            "session": {
                "voice": self.voice,
                "instructions": self.call_context,
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "tools": VOICE_TOOLS,
            },
        }
        await self._ws_send_openai(session_config)
        logger.info("OpenAI Realtime session configured")

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

                elif event_type == "response.audio.delta":
                    # Audio de Luna -> Twilio
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
                    logger.debug("Speech started - interrupting response")
                    # Envoyer clear pour arreter le playback Twilio
                    if self.stream_sid:
                        clear_msg = {
                            "event": "clear",
                            "streamSid": self.stream_sid,
                        }
                        await self._ws_send_twilio(clear_msg)
                    # Annuler la reponse en cours d'OpenAI (ignore si pas de reponse active)
                    try:
                        await self._ws_send_openai({"type": "response.cancel"})
                    except Exception:
                        pass

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # Transcription de ce que le souscripteur a dit
                    text = data.get("transcript", "").strip()
                    if text:
                        self.transcript.append({"role": "user", "text": text})
                        logger.info(f"Transcript [user]: {text[:80]}")

                elif event_type == "response.audio_transcript.done":
                    # Transcription de ce que Luna a dit
                    text = data.get("transcript", "").strip()
                    if text:
                        self.transcript.append({"role": "luna", "text": text})
                        logger.info(f"Transcript [luna]: {text[:80]}")

                elif event_type == "response.function_call_arguments.done":
                    # Tool call ! Executer la fonction
                    await self._handle_tool_call(data)

                elif event_type == "error":
                    error_info = data.get("error", {})
                    error_code = error_info.get("code", "")
                    if error_code == "response_cancel_not_active":
                        logger.debug(f"OpenAI Realtime: cancel ignored (no active response)")
                    else:
                        logger.error(f"OpenAI Realtime error: {error_info}")

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

        # Executer via le callback (avec timeout 15s)
        result = {"status": "error", "message": "Fonction non disponible"}
        if self.tool_handler:
            try:
                result = await asyncio.wait_for(
                    self.tool_handler(function_name, args), timeout=15.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Tool handler timeout ({function_name})")
                result = {"status": "error", "message": "Timeout - reessaie plus tard"}
            except Exception as e:
                logger.error(f"Tool handler error ({function_name}): {e}")
                result = {"status": "error", "message": str(e)}

        # Envoyer le resultat a OpenAI
        tool_response = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False),
            },
        }
        await self._ws_send_openai(tool_response)
        await self._ws_send_openai({"type": "response.create"})

        logger.info(f"Tool call {function_name} result sent to OpenAI")

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
