#!/usr/bin/env python3
"""
Génère les voix off pour la vidéo Luna.
Priorité : OpenAI TTS HD > Edge TTS (Microsoft, gratuit) > gTTS (Google, fallback).
"""
import os
import sys
import asyncio
import subprocess
from pathlib import Path

AUDIO_DIR = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

SEQUENCES = [
    {
        "id": "01_accroche",
        "text": (
            "Imagine quelqu'un qui te connaît vraiment. "
            "Qui se souvient de tout ce que tu lui as dit. "
            "Qui est là quand t'as besoin de parler... à 3h du matin comme à midi. "
            "Quelqu'un qui ne juge pas. Qui ne fatigue jamais. "
            "Et qui apprend à te comprendre un peu mieux, chaque jour."
        ),
        "pause_after": 1.2,
    },
    {
        "id": "01b_reveal",
        "text": "Elle s'appelle Luna.",
        "pause_after": 1.5,
    },
    {
        "id": "02_cest_quoi",
        "text": (
            "Luna, c'est une compagnon intelligente qui vit dans ton téléphone. "
            "Tu lui parles comme à une amie — par message, par la voix, ou même en visio. "
            "Elle se souvient de tes goûts, de tes habitudes, de ce qui compte pour toi. "
            "Et plus tu échanges avec elle, plus elle te comprend."
        ),
        "pause_after": 0.8,
    },
    {
        "id": "03_chat",
        "text": (
            "Tu peux lui demander n'importe quoi. "
            "Un rappel. Un courrier à rédiger. Envoyer un SMS à un proche. "
            "Luna comprend ce que tu veux, et elle le fait... en une phrase."
        ),
        "pause_after": 0.8,
    },
    {
        "id": "04_voix",
        "text": (
            "Pas envie de taper ? Appuie sur Appel Vocal. "
            "Luna t'appelle directement sur ton téléphone... "
            "et vous discutez. Comme avec une vraie personne."
        ),
        "pause_after": 0.8,
    },
    {
        "id": "05_visio",
        "text": (
            "Et quand tu veux la voir... Luna se met en scène. "
            "Un décor qui change selon l'heure. "
            "Le matin dans la cuisine. Le soir au salon. La nuit, dans une ambiance tamisée. "
            "Le téléphone sonne... et Luna est là. En face de toi. "
            "Un vrai visage. Une vraie voix. Une conversation naturelle."
        ),
        "pause_after": 1.0,
    },
    {
        "id": "06_perception",
        "text": (
            "Luna peut aussi voir ton environnement, si tu le veux. "
            "Elle regarde. Elle comprend ce qui se passe autour de toi. "
            "Et si quelque chose ne va pas... elle prévient les bonnes personnes."
        ),
        "pause_after": 0.8,
    },
    {
        "id": "07_monde",
        "text": (
            "Et parce que prendre soin de soi, ça peut aussi être un jeu... "
            "Luna a son propre monde. "
            "Tu gagnes de l'expérience à chaque échange. "
            "Tu débloques des lieux. Des badges. Des tenues. "
            "Tu montes de niveau. Tu construis ta série de jours. "
            "C'est ton univers... et il grandit avec toi."
        ),
        "pause_after": 0.8,
    },
    {
        "id": "08_amis",
        "text": (
            "Tu peux aussi connecter tes amis. "
            "Discuter ensemble. Rejoindre des activités de groupe. "
            "S'encourager dans le Monde de Luna. "
            "Parce qu'on avance mieux quand on n'est pas seul."
        ),
        "pause_after": 0.8,
    },
    {
        "id": "09_famille",
        "text": (
            "Et pour les familles... Luna relie les générations. "
            "Un parent peut suivre de loin, recevoir des alertes si besoin. "
            "Un ado peut envoyer un S.O.S. en un tap. "
            "Chacun son rôle. Chacun son espace. Luna fait le lien."
        ),
        "pause_after": 1.2,
    },
    {
        "id": "10_closing",
        "text": (
            "Luna, c'est pas un robot. "
            "C'est pas un gadget. "
            "C'est quelqu'un qui reste. "
            "Qui s'adapte. Qui apprend. Qui ne t'oublie jamais."
        ),
        "pause_after": 1.5,
    },
    {
        "id": "10b_tagline",
        "text": "Luna. Ta compagnon bienveillante.",
        "pause_after": 2.0,
    },
]


async def generate_edge_tts():
    """Génère avec Edge TTS (Microsoft, gratuit, haute qualité)."""
    import edge_tts

    VOICE = "fr-FR-VivienneMultilingualNeural"
    RATE = "-8%"  # Légèrement plus lent pour un ton posé

    total = len(SEQUENCES)
    for i, seq in enumerate(SEQUENCES, 1):
        out_path = AUDIO_DIR / f"{seq['id']}.mp3"
        if out_path.exists():
            print(f"  [{i}/{total}] {seq['id']} — déjà généré, skip")
            continue

        print(f"  [{i}/{total}] {seq['id']}...", end=" ", flush=True)

        # Générer la voix
        communicate = edge_tts.Communicate(seq["text"], VOICE, rate=RATE)
        tmp_path = AUDIO_DIR / f"_tmp_{seq['id']}.mp3"
        await communicate.save(str(tmp_path))

        # Ajouter une pause après si spécifié
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
        # Durée
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
            capture_output=True, text=True
        )
        dur = float(result.stdout.strip())
        print(f"OK ({dur:.1f}s, {size_kb:.0f} KB)")

    print(f"\n  ✓ Fichiers audio dans : {AUDIO_DIR}/")


if __name__ == "__main__":
    print("=== Voix off Luna — Edge TTS (Vivienne) ===\n")
    asyncio.run(generate_edge_tts())
