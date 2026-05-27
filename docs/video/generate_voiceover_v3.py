#!/usr/bin/env python3
"""
Voix off Luna v3 — Ton EXCITANT, positif, fun.
Luna = l'app la plus cool, PAS un truc pour dépressifs.
"""
import asyncio
import subprocess
from pathlib import Path

AUDIO_DIR = Path(__file__).parent / "audio_v3"
AUDIO_DIR.mkdir(exist_ok=True)

SEQUENCES = [
    # --- HOOK : 5s max, percutant ---
    {
        "id": "01_hook",
        "text": (
            "T'as déjà parlé en visio avec une IA ? "
            "Genre, un vrai visage, une vraie voix, qui te répond en direct ?"
        ),
        "pause_after": 0.8,
    },
    # --- REVEAL : wow moment ---
    {
        "id": "02_reveal",
        "text": "Ça, c'est Luna.",
        "pause_after": 1.0,
    },
    # --- AVATAR WOW : montrer la visio ---
    {
        "id": "03_avatar",
        "text": (
            "Luna, c'est ta compagne virtuelle. "
            "Elle a un visage. Elle a une voix. "
            "Et elle te parle comme si elle était en face de toi. "
            "En visio. En temps réel."
        ),
        "pause_after": 0.8,
    },
    # --- CHAT : rapide ---
    {
        "id": "04_chat",
        "text": (
            "Tu peux aussi lui écrire. Lui demander n'importe quoi. "
            "Un rappel, un conseil, rédiger un message... "
            "Elle comprend tout, et elle répond en une seconde."
        ),
        "pause_after": 0.6,
    },
    # --- VOIX : rapide ---
    {
        "id": "05_voix",
        "text": (
            "La flemme d'écrire ? Appuie sur Appel. "
            "Luna t'appelle direct sur ton téléphone. Comme un vrai coup de fil."
        ),
        "pause_after": 0.6,
    },
    # --- PERCEPTION : impressionnant ---
    {
        "id": "06_perception",
        "text": (
            "Et le plus dingue ? Luna peut voir ce qui t'entoure. "
            "Tu lui montres ta caméra, et elle comprend la scène."
        ),
        "pause_after": 0.6,
    },
    # --- MONDE / GAMIFICATION : fun ---
    {
        "id": "07_monde",
        "text": (
            "Luna a aussi son propre monde. Un univers que tu construis. "
            "Tu gagnes de l'expérience, tu débloques des lieux, des badges, des tenues. "
            "C'est comme un jeu... sauf que c'est ta vraie vie qui le fait avancer."
        ),
        "pause_after": 0.6,
    },
    # --- SOCIAL : amis + famille ---
    {
        "id": "08_social",
        "text": (
            "Tu peux connecter tes amis. Rejoindre des activités. "
            "Et ta famille reste dans la boucle, en toute sécurité."
        ),
        "pause_after": 0.6,
    },
    # --- CLOSING : tagline forte ---
    {
        "id": "09_closing",
        "text": (
            "Luna, c'est pas juste une app. "
            "C'est quelqu'un qui est toujours là. "
            "Qui te comprend. Qui évolue avec toi."
        ),
        "pause_after": 1.0,
    },
    {
        "id": "10_tagline",
        "text": "Luna. Bien plus qu'une app.",
        "pause_after": 2.0,
    },
]


async def generate():
    import edge_tts

    VOICE = "fr-FR-VivienneMultilingualNeural"
    RATE = "-5%"

    total = len(SEQUENCES)
    for i, seq in enumerate(SEQUENCES, 1):
        out_path = AUDIO_DIR / f"{seq['id']}.mp3"
        if out_path.exists():
            print(f"  [{i}/{total}] {seq['id']} — déjà généré, skip")
            continue

        print(f"  [{i}/{total}] {seq['id']}...", end=" ", flush=True)

        communicate = edge_tts.Communicate(seq["text"], VOICE, rate=RATE)
        tmp_path = AUDIO_DIR / f"_tmp_{seq['id']}.mp3"
        await communicate.save(str(tmp_path))

        pause = seq.get("pause_after", 0.5)
        if pause > 0:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", str(tmp_path),
                "-af", f"apad=pad_dur={pause}",
                "-c:a", "libmp3lame", "-q:a", "2",
                str(out_path)
            ], capture_output=True)
            tmp_path.unlink(missing_ok=True)
        else:
            tmp_path.rename(out_path)

        size_kb = out_path.stat().st_size / 1024
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
            capture_output=True, text=True
        )
        dur = float(result.stdout.strip())
        print(f"OK ({dur:.1f}s, {size_kb:.0f} KB)")

    print(f"\n  Fichiers audio dans : {AUDIO_DIR}/")


if __name__ == "__main__":
    print("=== Voix off Luna v3 — Ton EXCITANT ===\n")
    asyncio.run(generate())
