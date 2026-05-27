#!/usr/bin/env python3
"""
Monte la vidéo de présentation Luna v2.
Améliorations : transitions fade, sous-titres, musique ambiante, meilleur pacing.
"""
import subprocess
import math
from pathlib import Path

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "audio"
SCREENS_DIR = BASE / "screens"
OUTPUT_DIR = BASE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

W, H = 1080, 1920
BG = "0a0a1a"
ACCENT = "a78bfa"
FPS = 25
FADE_DUR = 0.6  # secondes de fondu


# ══════════════════════════════════════════════════════════════════
# SÉQUENCES — structure narrative
# ══════════════════════════════════════════════════════════════════
SEQUENCES = [
    # --- ACCROCHE ---
    {"audio": "01_accroche", "screens": ["chat_greeting"],
     "subtitle": "Imagine quelqu'un\nqui te connaît vraiment..."},
    {"audio": "01b_reveal", "screens": ["login"],
     "subtitle": "Elle s'appelle Luna.", "title": "LUNA"},

    # --- PRÉSENTATION ---
    {"audio": "02_cest_quoi", "screens": ["chat_conversation"],
     "subtitle": None},

    # --- CHAT ---
    {"audio": "03_chat", "screens": ["chat_instruction", "chat_confirm"],
     "subtitle": None, "title": "CHAT"},

    # --- VOIX ---
    {"audio": "04_voix", "screens": ["voice_call"],
     "subtitle": None, "title": "APPEL VOCAL"},

    # --- VISIO ---
    {"audio": "05_visio", "screens": ["cinema_night", "cinema_zoom", "tavus_fullscreen"],
     "subtitle": None, "title": "VISIO"},

    # --- PERCEPTION ---
    {"audio": "06_perception", "screens": ["perception_camera", "contacts_list"],
     "subtitle": None, "title": "PERCEPTION"},

    # --- MONDE ---
    {"audio": "07_monde", "screens": ["world_scene", "world_badges", "world_shop"],
     "subtitle": None, "title": "LE MONDE DE LUNA"},

    # --- AMIS ---
    {"audio": "08_amis", "screens": ["friends_list", "friends_dm"],
     "subtitle": None, "title": "AMIS"},

    # --- FAMILLE ---
    {"audio": "09_famille", "screens": ["family_group", "family_sos"],
     "subtitle": None, "title": "FAMILLE"},

    # --- CLOSING ---
    {"audio": "10_closing", "screens": ["chat_goodnight"],
     "subtitle": "Quelqu'un qui reste.\nQui s'adapte.\nQui ne t'oublie jamais."},
    {"audio": "10b_tagline", "screens": ["logo"],
     "subtitle": "Luna.\nTa compagnon bienveillante."},
]


def dur(path):
    """Durée audio en secondes."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def ff(args, label=""):
    """Wrapper ffmpeg silencieux."""
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True)
    if r.returncode != 0 and label:
        print(f"\n  ERREUR ffmpeg [{label}]: {r.stderr[-300:]}")
    return r.returncode == 0


def build_seq(idx, seq):
    """Construit un segment : images + Ken Burns + fade + titre + sous-titres + audio."""
    audio_path = AUDIO_DIR / f"{seq['audio']}.mp3"
    if not audio_path.exists():
        return None

    total_dur = dur(audio_path)
    screens = seq.get("screens", ["login"])
    title = seq.get("title")
    subtitle = seq.get("subtitle")

    # ── Construire la piste visuelle ──
    parts = []
    per_screen = total_dur / len(screens)

    for i, sname in enumerate(screens):
        img = SCREENS_DIR / f"{sname}.png"
        clip = OUTPUT_DIR / f"_s{idx}_c{i}.mp4"

        if not img.exists():
            # Fond uni placeholder
            ff(["-f", "lavfi", "-i", f"color=c=0x{BG}:s={W}x{H}:d={per_screen}:r={FPS}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], f"placeholder {sname}")
        else:
            # Ken Burns : zoom 100→106% + léger pan
            n_frames = int(per_screen * FPS)
            ff([
                "-loop", "1", "-i", str(img), "-t", str(per_screen),
                "-vf", (
                    f"scale={W + 200}:{H + 350}:force_original_aspect_ratio=decrease,"
                    f"pad={W + 200}:{H + 350}:(ow-iw)/2:(oh-ih)/2:color=0x{BG},"
                    f"zoompan=z='1.0+0.001*on':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
                    f"d={n_frames}:s={W}x{H}:fps={FPS},"
                    # Fade in au début de chaque image
                    f"fade=t=in:st=0:d={FADE_DUR}:color=0x{BG},"
                    # Fade out à la fin
                    f"fade=t=out:st={per_screen - FADE_DUR}:d={FADE_DUR}:color=0x{BG}"
                ),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
                str(clip)
            ], f"ken_burns {sname}")

        parts.append(clip)

    # ── Concat les clips visuels ──
    visual = OUTPUT_DIR / f"_s{idx}_visual.mp4"
    lst = OUTPUT_DIR / f"_s{idx}_list.txt"
    lst.write_text("\n".join(f"file '{p}'" for p in parts if p.exists()))

    if len(parts) > 1:
        ff(["-f", "concat", "-safe", "0", "-i", str(lst),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(visual)], "concat")
    elif parts and parts[0].exists():
        parts[0].rename(visual)

    if not visual.exists():
        return None

    # ── Ajouter titre et sous-titres ──
    overlays = []

    if title:
        # Titre en haut, apparaît pendant 2s avec fade
        escaped = title.replace("'", "'\\''")
        overlays.append(
            f"drawtext=text='{escaped}':"
            f"fontcolor=0x{ACCENT}:fontsize=52:font=DejaVu Sans Bold:"
            f"x=(w-text_w)/2:y=120:"
            f"enable='between(t,0.3,2.5)':"
            f"alpha='if(lt(t,0.6),min(1,(t-0.3)/0.3),if(gt(t,2.0),max(0,(2.5-t)/0.5),1))'"
        )

    if subtitle:
        lines = subtitle.split("\n")
        for li, line in enumerate(lines):
            escaped = line.replace("'", "'\\''").replace(":", "\\:")
            y_pos = H - 300 + li * 50
            overlays.append(
                f"drawtext=text='{escaped}':"
                f"fontcolor=white:fontsize=36:font=DejaVu Sans:"
                f"x=(w-text_w)/2:y={y_pos}:"
                f"shadowcolor=black:shadowx=2:shadowy=2"
            )

    # Barre fine violette en bas (signature)
    overlays.append(
        f"drawbox=x=0:y={H - 4}:w={W}:h=4:color=0x{ACCENT}@0.8:t=fill"
    )

    if overlays:
        titled = OUTPUT_DIR / f"_s{idx}_titled.mp4"
        vf = ",".join(overlays)
        ff(["-i", str(visual), "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
            str(titled)], "overlays")
        if titled.exists():
            visual.unlink(missing_ok=True)
            visual = titled

    # ── Combiner vidéo + audio ──
    final = OUTPUT_DIR / f"seq_{idx:02d}_{seq['audio']}.mp4"
    ff(["-i", str(visual), "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(final)], "mux")

    return final


def generate_ambient_music(duration, output_path):
    """Génère une piste audio ambiante douce avec ffmpeg (sinus harmoniques)."""
    print("  Génération musique ambiante...", end=" ", flush=True)
    # Accord doux : A3(220Hz) + C#4(277Hz) + E4(330Hz) à très bas volume
    ff([
        "-f", "lavfi",
        "-i", (
            f"sine=f=220:d={duration}[a];"
            f"sine=f=277:d={duration}[b];"
            f"sine=f=330:d={duration}[c];"
            f"sine=f=440:d={duration}[d];"
            f"[a][b]amix=inputs=2[ab];"
            f"[c][d]amix=inputs=2[cd];"
            f"[ab][cd]amix=inputs=2,"
            f"volume=0.04,"
            f"afade=t=in:d=3,"
            f"afade=t=out:st={duration - 4}:d=4,"
            f"lowpass=f=800,"
            f"aecho=0.8:0.88:60:0.3"
        ),
        "-t", str(duration),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ], "ambient music")
    print("OK")


def main():
    print("=== Montage Vidéo Luna v2 ===\n")

    # Build sequences
    seq_files = []
    for i, seq in enumerate(SEQUENCES):
        label = seq["audio"]
        print(f"  [{i + 1}/{len(SEQUENCES)}] {label}...", end=" ", flush=True)
        result = build_seq(i, seq)
        if result and result.exists():
            d = dur(result)
            seq_files.append(result)
            print(f"OK ({d:.1f}s)")
        else:
            print("SKIP")

    if not seq_files:
        print("\n  ERREUR: Aucune séquence. Lance d'abord generate_voiceover.py")
        return

    # Concat toutes les séquences
    print(f"\n  Assemblage ({len(seq_files)} segments)...", end=" ", flush=True)
    concat_list = OUTPUT_DIR / "_concat.txt"
    concat_list.write_text("\n".join(f"file '{f}'" for f in seq_files))
    raw_video = OUTPUT_DIR / "_raw.mp4"
    ff(["-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(raw_video)], "concat final")
    print("OK")

    total_dur = dur(raw_video)

    # Musique ambiante
    music_path = AUDIO_DIR / "music.mp3"
    if not music_path.exists():
        generate_ambient_music(total_dur + 2, music_path)

    # Mix voix + musique
    print("  Mix audio final...", end=" ", flush=True)
    final = OUTPUT_DIR / "luna_presentation.mp4"
    ff([
        "-i", str(raw_video),
        "-i", str(music_path),
        "-filter_complex", (
            # Voix = piste 0, musique = piste 1
            # Musique à 15% du volume, voix à 100%
            "[0:a]volume=1.0[voice];"
            "[1:a]volume=0.15[music];"
            "[voice][music]amix=inputs=2:duration=shortest[out]"
        ),
        "-map", "0:v", "-map", "[out]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(final)
    ], "mix final")
    print("OK")

    # Nettoyage des fichiers temporaires
    for f in OUTPUT_DIR.glob("_*"):
        f.unlink(missing_ok=True)
    for f in OUTPUT_DIR.glob("seq_*"):
        f.unlink(missing_ok=True)

    if final.exists():
        size_mb = final.stat().st_size / (1024 * 1024)
        d = dur(final)
        mins = int(d // 60)
        secs = int(d % 60)
        print(f"\n  ╔══════════════════════════════════╗")
        print(f"  ║  VIDÉO FINALE PRÊTE              ║")
        print(f"  ╠══════════════════════════════════╣")
        print(f"  ║  Fichier : luna_presentation.mp4 ║")
        print(f"  ║  Durée   : {mins}min{secs:02d}s               ║")
        print(f"  ║  Taille  : {size_mb:.1f} MB               ║")
        print(f"  ║  Format  : {W}×{H} (9:16)        ║")
        print(f"  ╚══════════════════════════════════╝")
        print(f"\n  {final}")
    else:
        print("\n  ERREUR: Fichier final non généré")


if __name__ == "__main__":
    main()
