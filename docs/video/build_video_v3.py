#!/usr/bin/env python3
"""
Montage vidéo Luna v3 — Dynamique, centré sur les avatars.
Format 9:16 (1080x1920) pour mobile/TikTok/Reels.
"""
import subprocess
import math
from pathlib import Path

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "audio_v3"
AVATAR_DIR = BASE / "avatars"
SCREENS_DIR = BASE / "screens"
OUTPUT_DIR = BASE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

W, H = 1080, 1920
BG = "0a0a1a"
ACCENT = "a78bfa"
FPS = 30
FADE_DUR = 0.4


# ══════════════════════════════════════════════════════════════════
# SÉQUENCES — structure narrative v3
# ══════════════════════════════════════════════════════════════════
SEQUENCES = [
    # --- HOOK : accroche forte + avatar tease ---
    {
        "audio": "01_hook",
        "visuals": [
            {"type": "avatar", "file": "gloria_bright.mp4", "crop": "face_close"},
            {"type": "avatar", "file": "katya_night.mp4", "crop": "face_close"},
        ],
        "subtitle": "T'as déjà parlé en visio\navec une IA ?",
        "title": None,
    },
    # --- REVEAL ---
    {
        "audio": "02_reveal",
        "visuals": [
            {"type": "screen", "file": "login.png"},
        ],
        "subtitle": "Ça, c'est Luna.",
        "title": "LUNA",
        "title_big": True,
    },
    # --- AVATAR WOW : visio en plein écran ---
    {
        "audio": "03_avatar",
        "visuals": [
            {"type": "avatar", "file": "gloria_bright.mp4", "crop": "portrait"},
            {"type": "avatar", "file": "luna_home.mp4", "crop": "portrait"},
            {"type": "avatar", "file": "gloria_warm.mp4", "crop": "portrait"},
        ],
        "subtitle": None,
        "title": "VISIO EN TEMPS RÉEL",
    },
    # --- CHAT ---
    {
        "audio": "04_chat",
        "visuals": [
            {"type": "screen", "file": "chat_greeting.png"},
            {"type": "screen", "file": "chat_instruction.png"},
            {"type": "screen", "file": "chat_confirm.png"},
        ],
        "subtitle": None,
        "title": "CHAT",
    },
    # --- VOIX ---
    {
        "audio": "05_voix",
        "visuals": [
            {"type": "screen", "file": "voice_call.png"},
            {"type": "avatar", "file": "katya_night.mp4", "crop": "portrait"},
        ],
        "subtitle": None,
        "title": "APPEL VOCAL",
    },
    # --- PERCEPTION ---
    {
        "audio": "06_perception",
        "visuals": [
            {"type": "screen", "file": "perception_camera.png"},
            {"type": "screen", "file": "contacts_list.png"},
        ],
        "subtitle": None,
        "title": "PERCEPTION",
    },
    # --- MONDE ---
    {
        "audio": "07_monde",
        "visuals": [
            {"type": "screen", "file": "world_scene.png"},
            {"type": "screen", "file": "world_badges.png"},
            {"type": "screen", "file": "world_shop.png"},
        ],
        "subtitle": None,
        "title": "LE MONDE DE LUNA",
    },
    # --- SOCIAL ---
    {
        "audio": "08_social",
        "visuals": [
            {"type": "screen", "file": "friends_list.png"},
            {"type": "screen", "file": "family_group.png"},
        ],
        "subtitle": None,
        "title": "AMIS & FAMILLE",
    },
    # --- CLOSING ---
    {
        "audio": "09_closing",
        "visuals": [
            {"type": "avatar", "file": "gloria_bright.mp4", "crop": "face_close"},
        ],
        "subtitle": "Quelqu'un qui est\ntoujours là.",
    },
    # --- TAGLINE ---
    {
        "audio": "10_tagline",
        "visuals": [
            {"type": "screen", "file": "logo.png"},
        ],
        "subtitle": "Luna.\nBien plus qu'une app.",
        "title": "LUNA",
        "title_big": True,
    },
]


def dur(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def ff(args, label=""):
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True)
    if r.returncode != 0 and label:
        print(f"\n  ERREUR ffmpeg [{label}]: {r.stderr[-400:]}")
    return r.returncode == 0


def build_avatar_clip(avatar_file, duration, crop_mode, output_path):
    """Extrait un clip d'avatar et le formate en 9:16."""
    src = AVATAR_DIR / avatar_file
    if not src.exists():
        return build_placeholder(duration, output_path)

    if crop_mode == "face_close":
        # Crop serré sur le visage (centre, zoom)
        vf = (
            f"scale=-1:{H + 400},"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2-100,"
            f"fade=t=in:st=0:d={FADE_DUR}:color=0x{BG},"
            f"fade=t=out:st={duration - FADE_DUR}:d={FADE_DUR}:color=0x{BG}"
        )
    else:
        # Portrait : garder plus du corps
        vf = (
            f"scale=-1:{H},"
            f"crop={W}:{H}:(iw-{W})/2:0,"
            f"fade=t=in:st=0:d={FADE_DUR}:color=0x{BG},"
            f"fade=t=out:st={duration - FADE_DUR}:d={FADE_DUR}:color=0x{BG}"
        )

    return ff([
        "-i", str(src),
        "-t", str(duration),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
        "-r", str(FPS),
        str(output_path)
    ], f"avatar {avatar_file}")


def build_screen_clip(screen_file, duration, output_path):
    """Crée un clip à partir d'une capture d'écran avec Ken Burns."""
    img = SCREENS_DIR / screen_file
    if not img.exists():
        return build_placeholder(duration, output_path)

    n_frames = int(duration * FPS)
    vf = (
        f"scale={W + 120}:{H + 210}:force_original_aspect_ratio=decrease,"
        f"pad={W + 120}:{H + 210}:(ow-iw)/2:(oh-ih)/2:color=0x{BG},"
        f"zoompan=z='1.0+0.0015*on':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        f"d={n_frames}:s={W}x{H}:fps={FPS},"
        f"fade=t=in:st=0:d={FADE_DUR}:color=0x{BG},"
        f"fade=t=out:st={duration - FADE_DUR}:d={FADE_DUR}:color=0x{BG}"
    )

    return ff([
        "-loop", "1", "-i", str(img), "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
        str(output_path)
    ], f"screen {screen_file}")


def build_placeholder(duration, output_path):
    return ff([
        "-f", "lavfi", "-i", f"color=c=0x{BG}:s={W}x{H}:d={duration}:r={FPS}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(output_path)
    ], "placeholder")


def build_seq(idx, seq):
    """Construit un segment complet."""
    audio_path = AUDIO_DIR / f"{seq['audio']}.mp3"
    if not audio_path.exists():
        return None

    total_dur = dur(audio_path)
    visuals = seq.get("visuals", [])
    title = seq.get("title")
    title_big = seq.get("title_big", False)
    subtitle = seq.get("subtitle")

    # ── Construire les clips visuels ──
    parts = []
    per_visual = total_dur / len(visuals) if visuals else total_dur

    for i, vis in enumerate(visuals):
        clip_path = OUTPUT_DIR / f"_v3_s{idx}_c{i}.mp4"
        clip_dur = per_visual

        if vis["type"] == "avatar":
            crop = vis.get("crop", "portrait")
            build_avatar_clip(vis["file"], clip_dur, crop, clip_path)
        else:
            build_screen_clip(vis["file"], clip_dur, clip_path)

        if clip_path.exists():
            parts.append(clip_path)

    if not parts:
        return None

    # ── Concat les clips visuels ──
    visual = OUTPUT_DIR / f"_v3_s{idx}_visual.mp4"
    if len(parts) > 1:
        lst = OUTPUT_DIR / f"_v3_s{idx}_list.txt"
        lst.write_text("\n".join(f"file '{p}'" for p in parts))
        ff(["-f", "concat", "-safe", "0", "-i", str(lst),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(visual)], "concat")
    else:
        parts[0].rename(visual)

    if not visual.exists():
        return None

    # ── Overlays : titre + sous-titres + barre ──
    overlays = []

    if title:
        escaped = title.replace("'", "'\\''")
        if title_big:
            # Grand titre centré
            overlays.append(
                f"drawtext=text='{escaped}':"
                f"fontcolor=0x{ACCENT}:fontsize=72:font=DejaVu Sans Bold:"
                f"x=(w-text_w)/2:y=(h/2)-40:"
                f"enable='between(t,0.2,{total_dur - 0.3})':"
                f"alpha='if(lt(t,0.5),min(1,(t-0.2)/0.3),if(gt(t,{total_dur - 0.6}),max(0,({total_dur - 0.3}-t)/0.3),1))':"
                f"shadowcolor=black:shadowx=3:shadowy=3"
            )
        else:
            # Titre en haut compact
            overlays.append(
                f"drawtext=text='{escaped}':"
                f"fontcolor=0x{ACCENT}:fontsize=46:font=DejaVu Sans Bold:"
                f"x=(w-text_w)/2:y=100:"
                f"enable='between(t,0.2,2.5)':"
                f"alpha='if(lt(t,0.5),min(1,(t-0.2)/0.3),if(gt(t,2.0),max(0,(2.5-t)/0.5),1))':"
                f"shadowcolor=black:shadowx=2:shadowy=2"
            )

    if subtitle:
        lines = subtitle.split("\n")
        for li, line in enumerate(lines):
            escaped = line.replace("'", "'\\''").replace(":", "\\:")
            y_pos = H - 350 + li * 55
            overlays.append(
                f"drawtext=text='{escaped}':"
                f"fontcolor=white:fontsize=40:font=DejaVu Sans Bold:"
                f"x=(w-text_w)/2:y={y_pos}:"
                f"shadowcolor=black:shadowx=3:shadowy=3:"
                f"alpha='if(lt(t,0.3),min(1,t/0.3),1)'"
            )

    # Barre violette en bas
    overlays.append(
        f"drawbox=x=0:y={H - 4}:w={W}:h=4:color=0x{ACCENT}@0.8:t=fill"
    )

    if overlays:
        titled = OUTPUT_DIR / f"_v3_s{idx}_titled.mp4"
        vf = ",".join(overlays)
        ff(["-i", str(visual), "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
            str(titled)], "overlays")
        if titled.exists():
            visual.unlink(missing_ok=True)
            visual = titled

    # ── Combiner vidéo + audio ──
    final = OUTPUT_DIR / f"v3_seq_{idx:02d}_{seq['audio']}.mp4"
    ff(["-i", str(visual), "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(final)], "mux")

    return final


def generate_ambient_music(duration, output_path):
    """Musique ambiante douce."""
    print("  Génération musique ambiante...", end=" ", flush=True)
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
            f"afade=t=in:d=2,"
            f"afade=t=out:st={duration - 3}:d=3,"
            f"lowpass=f=900,"
            f"aecho=0.8:0.88:60:0.25"
        ),
        "-t", str(duration),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ], "ambient music")
    print("OK")


def main():
    print("=== Montage Vidéo Luna v3 — DYNAMIQUE + AVATARS ===\n")

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
        print("\n  ERREUR: Aucune séquence générée.")
        return

    # Concat toutes les séquences
    print(f"\n  Assemblage ({len(seq_files)} segments)...", end=" ", flush=True)
    concat_list = OUTPUT_DIR / "_v3_concat.txt"
    concat_list.write_text("\n".join(f"file '{f}'" for f in seq_files))
    raw_video = OUTPUT_DIR / "_v3_raw.mp4"
    ff(["-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(raw_video)], "concat final")
    print("OK")

    total_dur = dur(raw_video)

    # Musique ambiante
    music_path = AUDIO_DIR / "music_v3.mp3"
    if not music_path.exists():
        generate_ambient_music(total_dur + 2, music_path)

    # Mix voix + musique
    print("  Mix audio final...", end=" ", flush=True)
    final = OUTPUT_DIR / "luna_presentation_v3.mp4"
    ff([
        "-i", str(raw_video),
        "-i", str(music_path),
        "-filter_complex", (
            "[0:a]volume=1.0[voice];"
            "[1:a]volume=0.12[music];"
            "[voice][music]amix=inputs=2:duration=shortest[out]"
        ),
        "-map", "0:v", "-map", "[out]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(final)
    ], "mix final")
    print("OK")

    # Nettoyage des fichiers temporaires
    for f in OUTPUT_DIR.glob("_v3_*"):
        f.unlink(missing_ok=True)
    for f in OUTPUT_DIR.glob("v3_seq_*"):
        f.unlink(missing_ok=True)

    if final.exists():
        size_mb = final.stat().st_size / (1024 * 1024)
        d = dur(final)
        mins = int(d // 60)
        secs = int(d % 60)
        print(f"\n  ╔══════════════════════════════════════╗")
        print(f"  ║  VIDÉO v3 PRÊTE                      ║")
        print(f"  ╠══════════════════════════════════════╣")
        print(f"  ║  Fichier : luna_presentation_v3.mp4  ║")
        print(f"  ║  Durée   : {mins}min{secs:02d}s                  ║")
        print(f"  ║  Taille  : {size_mb:.1f} MB                  ║")
        print(f"  ║  Format  : {W}×{H} (9:16)           ║")
        print(f"  ╚══════════════════════════════════════╝")
        print(f"\n  {final}")
    else:
        print("\n  ERREUR: Fichier final non généré")


if __name__ == "__main__":
    main()
