"""
TTS Engine pour Simli — OpenAI gpt-4o-mini-tts + Edge-TTS fallback.
Conversion MP3 → PCM16 16kHz mono via ffmpeg.
"""
import asyncio
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("luna.simli.tts")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TTS_VOICE = os.getenv("TTS_VOICE", "coral")
TTS_ENGINE = os.getenv("TTS_ENGINE", "openai")

LUNA_VOICE_INSTRUCTIONS = (
    "Parle comme une amie proche, chaleureuse et bienveillante. "
    "Voix douce et naturelle avec de vraies emotions : joie, tendresse, empathie. "
    "Rythme naturel avec des micro-pauses, des sourires dans la voix. "
    "Tu es francaise, ton ton est intime et rassurant, jamais robotique."
)


async def openai_tts(text: str, voice: str = "") -> Optional[bytes]:
    """Synthetise via OpenAI gpt-4o-mini-tts. Retourne du MP3."""
    voice = voice or TTS_VOICE
    if not OPENAI_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini-tts",
                    "input": text,
                    "voice": voice,
                    "instructions": LUNA_VOICE_INSTRUCTIONS,
                    "response_format": "mp3",
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    logger.info(f"OpenAI TTS: {len(data)} bytes, voix={voice}")
                    return data
                else:
                    err = await resp.text()
                    logger.error(f"OpenAI TTS erreur {resp.status}: {err[:200]}")
                    return None
    except Exception as e:
        logger.error(f"OpenAI TTS exception: {e}")
        return None


async def edge_tts(text: str, voice: str = "fr-FR-DeniseNeural") -> Optional[bytes]:
    """Synthetise via Edge-TTS (gratuit, fallback). Retourne du MP3."""
    try:
        import edge_tts
    except ImportError:
        return None
    try:
        communicate = edge_tts.Communicate(text, voice)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks) if chunks else None
    except Exception as e:
        logger.error(f"Edge-TTS erreur: {e}")
        return None


async def mp3_to_pcm16(mp3_data: bytes, sample_rate: int = 16000) -> Optional[bytes]:
    """Convertit du MP3 en PCM16 via ffmpeg."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", "pipe:0",
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", str(sample_rate), "-ac", "1", "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(input=mp3_data),
            timeout=30.0,
        )
        return stdout if stdout else None
    except asyncio.TimeoutError:
        logger.error("ffmpeg timeout (30s)")
        return None
    except Exception as e:
        logger.error(f"ffmpeg erreur: {e}")
        return None


async def tts_to_pcm16(text: str, voice: str = "") -> Optional[bytes]:
    """TTS → PCM16. OpenAI en priorite, fallback Edge-TTS."""
    mp3_data = None
    if TTS_ENGINE == "openai":
        mp3_data = await openai_tts(text, voice)
    if not mp3_data:
        mp3_data = await edge_tts(text)
    if not mp3_data:
        return None
    return await mp3_to_pcm16(mp3_data)


async def tts_to_mp3(text: str, voice: str = "") -> Optional[bytes]:
    """TTS → MP3. OpenAI en priorite, fallback Edge-TTS."""
    if TTS_ENGINE == "openai":
        mp3_data = await openai_tts(text, voice)
        if mp3_data:
            return mp3_data
    return await edge_tts(text)
