"""
WebSocket handler pour Simli — Pipeline conversationnel temps reel.
=================================================================
Flux : navigateur (micro PCM16) -> WS -> STT (Whisper) -> LLM (GPT-4o-mini)
     -> TTS (gpt-4o-mini-tts) -> MP3 -> ffmpeg -> PCM16 16kHz -> chunks paces
     -> WS -> frontend -> SimliClient.sendAudioData() -> video lip-sync

Protocole WebSocket :
    Client -> Serveur : {"type": "audio", "data": "<base64_pcm16>"}
    Client -> Serveur : {"type": "text", "text": "..."}
    Client -> Serveur : {"type": "request_greeting"}
    Serveur -> Client : {"type": "simli_audio", "pcm16_b64": "..."}
    Serveur -> Client : {"type": "llm_text", "text": "..."}
    Serveur -> Client : {"type": "audio_fallback", "data": "...", "codec": "mp3"}
    Serveur -> Client : {"type": "status", "session": "active"}
    Serveur -> Client : {"type": "pipeline_done"}
"""
import asyncio
import base64
import json
import logging
import os
import struct
import time
from typing import Optional

import httpx

from .tts_engine import tts_to_pcm16, tts_to_mp3
from .luna_schedule import get_current_scene, get_enriched_system_prompt, get_current_emotion_id

logger = logging.getLogger("luna.simli.ws")

# Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

# Audio settings
MIN_AUDIO_BYTES = 6400       # 200ms a 16kHz
SILENCE_TIMEOUT_S = 1.5
SESSION_TIMEOUT_S = 1800     # 30 min
AI_ENGINE_CHUNK_SIZE = 6000  # 3000 samples = 187.5ms
CHUNK_PACING_MS = 0.175      # leger sous-debit

# Etat par session
_audio_buffers: dict[str, bytearray] = {}
_conversations: dict[str, list] = {}
_silence_timers: dict[str, float] = {}


# =====================================================================
# STT — OpenAI Whisper API
# =====================================================================
async def _stt_transcribe(pcm16_bytes: bytes, sample_rate: int = 16000) -> Optional[str]:
    """Transcrit un buffer audio PCM16 en texte via Whisper."""
    if not OPENAI_API_KEY:
        return None
    wav_bytes = _pcm16_to_wav(pcm16_bytes, sample_rate)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                data={"model": "whisper-1", "language": "fr"},
            )
        if r.status_code == 200:
            text = r.json().get("text", "").strip()
            return text if text and len(text) > 1 else None
        logger.error(f"Whisper erreur {r.status_code}: {r.text[:300]}")
    except Exception as e:
        logger.error(f"STT erreur: {e}")
    return None


def _pcm16_to_wav(pcm16: bytes, sr: int = 16000, ch: int = 1) -> bytes:
    dl = len(pcm16)
    hdr = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + dl, b"WAVE", b"fmt ", 16,
        1, ch, sr, sr * ch * 2, ch * 2, 16,
        b"data", dl,
    )
    return hdr + pcm16


# =====================================================================
# LLM — OpenAI Chat Completions
# =====================================================================
async def _llm_answer(user_text: str, session_id: str = "") -> str:
    """Genere une reponse LLM avec contexte temporel."""
    history = _conversations.setdefault(session_id, [])
    history.append({"role": "user", "content": user_text})
    system_prompt = get_enriched_system_prompt()
    messages = [{"role": "system", "content": system_prompt}] + history[-20:]

    if not OPENAI_API_KEY:
        answer = "Bonjour, je suis Luna. Comment puis-je t'aider ?"
        history.append({"role": "assistant", "content": answer})
        return answer

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": LLM_MODEL, "messages": messages, "max_tokens": 200},
            )
        if r.status_code == 200:
            answer = r.json()["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": answer})
            return answer
        logger.error(f"LLM erreur {r.status_code}: {r.text[:300]}")
    except Exception as e:
        logger.error(f"LLM erreur: {e}")

    fallback = "Je suis la, comment puis-je t'aider ?"
    history.append({"role": "assistant", "content": fallback})
    return fallback


# =====================================================================
# Audio pacing
# =====================================================================
async def _send_paced_audio(ws, pcm16_data: bytes) -> None:
    """Envoie les chunks PCM16 au rythme de lecture pour lip-sync."""
    total_chunks = 0
    t0 = asyncio.get_event_loop().time()
    for i in range(0, len(pcm16_data), AI_ENGINE_CHUNK_SIZE):
        chunk = pcm16_data[i:i + AI_ENGINE_CHUNK_SIZE]
        chunk_b64 = base64.b64encode(chunk).decode()
        await _ws_send(ws, {"type": "simli_audio", "pcm16_b64": chunk_b64})
        total_chunks += 1
        target_time = t0 + total_chunks * CHUNK_PACING_MS
        now = asyncio.get_event_loop().time()
        delay = target_time - now
        if delay > 0:
            await asyncio.sleep(delay)
    logger.info(f"Audio pace: {total_chunks} chunks, {len(pcm16_data)} bytes")


# =====================================================================
# Pipeline Simli
# =====================================================================
async def _run_simli_pipeline(ws, session_id: str, user_text: str) -> None:
    """Pipeline : LLM → TTS → PCM16 paces → SimliClient."""
    await _ws_send(ws, {"type": "stt_final", "text": user_text})

    answer = await _llm_answer(user_text, session_id)
    logger.info(f"[{session_id}] Simli LLM: {answer[:80]}...")
    await _ws_send(ws, {"type": "llm_text", "text": answer})

    pcm16_data = await tts_to_pcm16(answer)
    if pcm16_data:
        await _send_paced_audio(ws, pcm16_data)

    mp3_data = await tts_to_mp3(answer)
    if mp3_data:
        await _ws_send(ws, {
            "type": "audio_fallback",
            "data": base64.b64encode(mp3_data).decode(),
            "codec": "mp3",
        })

    await _ws_send(ws, {"type": "pipeline_done"})


async def _send_greeting(ws, session_id: str) -> None:
    """Envoie le greeting contextuel de Luna."""
    scene = get_current_scene()
    greeting = scene["greeting"]
    logger.info(f"[{session_id}] Greeting: {greeting[:60]}...")

    history = _conversations.setdefault(session_id, [])
    history.append({"role": "assistant", "content": greeting})

    await _ws_send(ws, {"type": "llm_text", "text": greeting})

    pcm16_data = await tts_to_pcm16(greeting)
    if pcm16_data:
        await _send_paced_audio(ws, pcm16_data)

    mp3_data = await tts_to_mp3(greeting)
    if mp3_data:
        await _ws_send(ws, {
            "type": "tts_audio",
            "audio_b64": base64.b64encode(mp3_data).decode(),
        })

    await _ws_send(ws, {"type": "pipeline_done"})


# =====================================================================
# WebSocket utility
# =====================================================================
async def _ws_send(ws, data: dict) -> bool:
    try:
        await ws.send_text(json.dumps(data))
        return True
    except Exception as e:
        logger.warning(f"WS send error: {e}")
        return False


# =====================================================================
# Handler principal
# =====================================================================
async def handle_simli_session(ws, session_id: str):
    """Gestionnaire WebSocket Simli."""
    from fastapi import WebSocketDisconnect

    await ws.accept()
    logger.info(f"Simli WS connecte: {session_id}")

    _audio_buffers[session_id] = bytearray()
    _silence_timers[session_id] = 0
    session_start = time.time()

    emotion_id = get_current_emotion_id()
    await _ws_send(ws, {
        "type": "status",
        "gpu": "offline",
        "session": "active",
        "emotion_id": emotion_id,
    })

    pipeline_lock = asyncio.Lock()

    async def _check_silence():
        while True:
            await asyncio.sleep(0.2)
            last_audio = _silence_timers.get(session_id, 0)
            buf = _audio_buffers.get(session_id, bytearray())
            if last_audio > 0 and len(buf) >= MIN_AUDIO_BYTES:
                elapsed = time.time() - last_audio
                if elapsed >= SILENCE_TIMEOUT_S:
                    async with pipeline_lock:
                        audio_data = bytes(buf)
                        _audio_buffers[session_id] = bytearray()
                        _silence_timers[session_id] = 0
                        if len(audio_data) < MIN_AUDIO_BYTES:
                            continue
                        logger.info(f"[{session_id}] Silence, STT sur {len(audio_data)} bytes")
                        text = await _stt_transcribe(audio_data)
                        if not text:
                            continue
                        logger.info(f"[{session_id}] STT: '{text}'")
                        await _run_simli_pipeline(ws, session_id, text)

    silence_task = asyncio.create_task(_check_silence())

    try:
        while True:
            if time.time() - session_start > SESSION_TIMEOUT_S:
                await _ws_send(ws, {"type": "error", "message": "Session expiree (30 min)"})
                break

            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                await _ws_send(ws, {"type": "status", "session": "active"})
                continue

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            t = data.get("type")

            if t == "audio":
                audio_b64 = data.get("data", "")
                if not audio_b64:
                    continue
                try:
                    pcm = base64.b64decode(audio_b64)
                except Exception:
                    continue
                _audio_buffers[session_id].extend(pcm)
                _silence_timers[session_id] = time.time()

            elif t == "text":
                text = data.get("text", "").strip()
                if text:
                    async with pipeline_lock:
                        await _run_simli_pipeline(ws, session_id, text)

            elif t == "request_greeting":
                async with pipeline_lock:
                    await _send_greeting(ws, session_id)

            elif t == "ping":
                await _ws_send(ws, {"type": "pong"})

            elif t == "stop":
                logger.info(f"[{session_id}] Arret demande")
                break

    except Exception as e:
        logger.info(f"Simli WS deconnecte: {session_id} ({type(e).__name__})")
    finally:
        if silence_task and not silence_task.done():
            silence_task.cancel()
            try:
                await silence_task
            except asyncio.CancelledError:
                pass

        _audio_buffers.pop(session_id, None)
        _conversations.pop(session_id, None)
        _silence_timers.pop(session_id, None)

        try:
            await _ws_send(ws, {"type": "status", "session": "ended"})
        except Exception:
            pass

        logger.info(f"[{session_id}] Simli session terminee")
