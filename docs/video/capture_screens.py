#!/usr/bin/env python3
"""
Capture les écrans de l'app Luna via Chromium headless.
Génère des PNG 1080x1920 (portrait mobile) pour le montage vidéo.
"""
import os
import subprocess
import time
import json
from pathlib import Path

BASE = Path(__file__).parent
SCREENS_DIR = BASE / "screens"
SCREENS_DIR.mkdir(exist_ok=True)

LUNA_URL = "https://luna-beta-674304336025.europe-west1.run.app"

# Identifiants de test (à adapter)
TEST_EMAIL = os.environ.get("LUNA_TEST_EMAIL", "")
TEST_PASSWORD = os.environ.get("LUNA_TEST_PASSWORD", "")

# Résolution mobile portrait
W, H = 412, 915


def chrome_screenshot(url, output_path, delay=3, extra_js=None):
    """Capture une page avec Chromium headless."""
    js_code = ""
    if extra_js:
        js_code = f"--run-all-compositor-stages-before-draw --virtual-time-budget=5000"

    cmd = [
        "chromium", "--headless", "--disable-gpu", "--no-sandbox",
        f"--window-size={W},{H}",
        "--hide-scrollbars",
        f"--screenshot={output_path}",
    ]
    if extra_js:
        cmd.append(f"--run-all-compositor-stages-before-draw")

    cmd.append(url)

    subprocess.run(cmd, capture_output=True, timeout=30)


def capture_static_screens():
    """Capture les écrans statiques (pas besoin de login)."""
    print("  Captures statiques...")

    # Page login
    print("    login...", end=" ", flush=True)
    chrome_screenshot(LUNA_URL, str(SCREENS_DIR / "login.png"))
    print("OK")

    # Cinématique (décors SVG)
    backgrounds = {
        "cinema_night": "bg_night.svg",
        "cinema_bedroom": "bg_bedroom.svg",
        "cinema_kitchen": "bg_kitchen_morning.svg",
        "cinema_livingroom": "bg_livingroom_evening.svg",
        "cinema_park": "bg_park.svg",
    }

    for name, svg in backgrounds.items():
        print(f"    {name}...", end=" ", flush=True)
        # Créer une page HTML temp avec le SVG en fond
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:100%; height:100%; background:#000; overflow:hidden; }}
.bg {{ position:absolute; inset:0; background-image:url('{LUNA_URL}/static/assets/backgrounds/{svg}');
       background-size:200% auto; background-position:center 40%; background-repeat:no-repeat; }}
.letterbox-t {{ position:absolute; top:0; left:0; right:0; height:11%; background:#000; z-index:5; }}
.letterbox-b {{ position:absolute; bottom:0; left:0; right:0; height:11%; background:#000; z-index:5; }}
.grain {{ position:absolute; inset:0; z-index:4; opacity:0.06;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E"); }}
.vignette {{ position:absolute; inset:0; z-index:3;
  background:radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.7) 100%); }}
.phone {{ position:absolute; z-index:6; left:50%; margin-left:-30px; bottom:35%;
  width:60px; height:106px; }}
.phone-body {{ width:100%; height:100%; background:linear-gradient(145deg,#2a2a3e,#1a1a2e);
  border-radius:16px; border:1.5px solid #444; box-shadow:0 12px 40px rgba(0,0,0,0.7);
  overflow:hidden; display:flex; flex-direction:column; }}
.phone-notch {{ width:28%; height:4px; margin:5px auto 0; background:#333; border-radius:3px; }}
.phone-screen {{ flex:1; margin:4px 5px 6px; background:linear-gradient(135deg,#1a1a3e,#2a2a5e);
  border-radius:10px; display:flex; align-items:center; justify-content:center; }}
.caller {{ text-align:center; }}
.caller-icon {{ width:32px; height:32px; margin:0 auto 5px; background:linear-gradient(135deg,#7c8cf8,#a78bfa);
  border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:15px; color:#fff; font-weight:700; }}
.caller-name {{ font-size:8px; color:#fff; font-weight:700; }}
.caller-label {{ font-size:6.5px; color:#bbb; margin-top:1px; }}
.scene-text {{ position:absolute; bottom:0; left:0; right:0; z-index:8;
  padding:32px 24px 28px; background:linear-gradient(transparent,rgba(0,0,0,0.8));
  font-family:Georgia,serif; font-size:17px; color:rgba(255,255,255,0.92);
  font-style:italic; letter-spacing:1.2px; }}
</style></head>
<body>
<div class="bg"></div>
<div class="grain"></div>
<div class="vignette"></div>
<div class="letterbox-t"></div>
<div class="letterbox-b"></div>
<div class="phone"><div class="phone-body"><div class="phone-notch"></div>
<div class="phone-screen"><div class="caller"><div class="caller-icon">L</div>
<div class="caller-name">Luna</div><div class="caller-label">Appel entrant...</div>
</div></div></div></div>
<div class="scene-text">Luna se met en scène pour toi...</div>
</body></html>"""
        tmp = Path(f"/tmp/capture_{name}.html")
        tmp.write_text(html)
        chrome_screenshot(f"file://{tmp}", str(SCREENS_DIR / f"{name}.png"))
        print("OK")

    # Monde de Luna
    print("    world_scene...", end=" ", flush=True)
    chrome_screenshot(f"{LUNA_URL}/world?embed=1", str(SCREENS_DIR / "world_scene.png"), delay=5)
    print("OK")


def create_mockup_screens():
    """Crée des mockups pour les écrans qui nécessitent un login."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  WARN: Pillow manquant, mockups non générés")
        return

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_msg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        font = font_small = font_big = font_msg = ImageFont.load_default()

    bg_color = (10, 10, 26)
    purple = (167, 139, 250)
    dark_purple = (76, 29, 149)
    card_bg = (30, 30, 63)
    text_color = (224, 224, 224)
    dim_text = (136, 136, 136)

    def new_img():
        return Image.new("RGB", (W * 2, H * 2), bg_color)  # 2x pour la qualité

    def draw_header(draw, img_w):
        # Header
        draw.rectangle([0, 0, img_w, 100], fill=(26, 26, 62))
        draw.text((20, 30), "● Luna", fill=purple, font=font_big)
        draw.text((20, 68), "Ton compagnon bienveillant", fill=dim_text, font=font_small)
        draw.line([0, 100, img_w, 100], fill=(51, 51, 51))

    def draw_tabs(draw, img_w, active="Chat"):
        tabs = ["Chat", "Profil", "Contacts", "Amis", "Instructions", "Documents", "Perception", "Quotas", "Monde"]
        x = 10
        y_top = 104
        for t in tabs:
            color = purple if t == active else dim_text
            draw.text((x, y_top + 10), t, fill=color, font=font_small)
            if t == active:
                bbox = draw.textbbox((x, y_top + 10), t, font=font_small)
                draw.line([x, y_top + 35, bbox[2], y_top + 35], fill=(124, 58, 237), width=3)
            x += 90
        draw.line([0, y_top + 40, img_w, y_top + 40], fill=(51, 51, 51))

    def draw_message(draw, text, is_luna, y, img_w):
        """Dessine une bulle de message."""
        max_w = int(img_w * 0.7)
        bg = card_bg if is_luna else dark_purple
        padding = 20

        # Mesurer le texte
        bbox = draw.textbbox((0, 0), text, font=font_msg)
        tw = min(bbox[2] - bbox[0], max_w - 2 * padding)
        th = bbox[3] - bbox[1]

        # Wrapping simple
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test, font=font_msg)
            if bbox[2] - bbox[0] > max_w - 2 * padding:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        line_h = 26
        total_h = len(lines) * line_h + 2 * padding
        if is_luna:
            total_h += 22  # Espace pour "Luna"

        x = 20 if is_luna else img_w - max_w - 20
        # Rectangle arrondi (simulé)
        draw.rounded_rectangle([x, y, x + max_w, y + total_h], radius=20, fill=bg)

        ty = y + padding
        if is_luna:
            draw.text((x + padding, ty), "Luna", fill=purple, font=font_small)
            ty += 22

        for line in lines:
            draw.text((x + padding, ty), line, fill=text_color, font=font_msg)
            ty += line_h

        return y + total_h + 12

    # --- CHAT GREETING ---
    print("    chat_greeting (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Chat")
    y = 180
    y = draw_message(draw, "Salut ! Comment tu vas aujourd'hui ? Je suis contente de te retrouver.", True, y, W * 2)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "chat_greeting.png"))
    print("OK")

    # --- CHAT CONVERSATION ---
    print("    chat_conversation (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Chat")
    y = 180
    y = draw_message(draw, "Salut Luna ! Ça va bien et toi ?", False, y, W * 2)
    y = draw_message(draw, "Super ! Je suis toujours en forme. Tu as passé une bonne journée ?", True, y, W * 2)
    y = draw_message(draw, "Oui tranquille, j'ai bossé sur le projet", False, y, W * 2)
    y = draw_message(draw, "Génial ! Tu veux qu'on en parle ou tu préfères décompresser un peu ?", True, y, W * 2)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "chat_conversation.png"))
    print("OK")

    # --- CHAT INSTRUCTION ---
    print("    chat_instruction (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Chat")
    y = 180
    y = draw_message(draw, "Rappelle-moi de prendre mes cachets tous les jours à 8h", False, y, W * 2)
    y = draw_message(draw, "C'est noté ! Je te rappellerai chaque matin à 8h pour tes cachets. Tu veux que je prévienne quelqu'un si tu oublies ?", True, y, W * 2)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "chat_instruction.png"))
    print("OK")

    # --- CHAT CONFIRM ---
    print("    chat_confirm (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Chat")
    y = 180
    y = draw_message(draw, "Envoie un SMS à Marie pour lui dire que je vais bien", False, y, W * 2)
    y = draw_message(draw, "SMS envoyé à Marie : « Coucou Marie, je vais bien, bisous ! » ✓", True, y, W * 2)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "chat_confirm.png"))
    print("OK")

    # --- VOICE CALL ---
    print("    voice_call (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W * 2, H * 2], fill=(10, 10, 30))
    # Cercle central
    cx, cy = W, H
    r = 120
    draw.ellipse([cx - r, cy - r - 100, cx + r, cy + r - 100], fill=(124, 58, 237))
    draw.text((cx - 25, cy - 60 - 100), "L", fill="white", font=font_big)
    draw.text((cx - 50, cy + r - 70), "Luna t'appelle...", fill=text_color, font=font)
    draw.text((cx - 80, cy + r - 35), "Décroche pour discuter", fill=dim_text, font=font_small)
    # Boutons
    draw.ellipse([cx - 40, cy + r + 40, cx + 40, cy + r + 120], fill=(34, 197, 94))
    draw.text((cx - 8, cy + r + 65), "📞", fill="white", font=font)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "voice_call.png"))
    print("OK")

    # --- TAVUS FULLSCREEN ---
    print("    tavus_fullscreen (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W * 2, H * 2], fill=(15, 10, 25))
    # Silhouette visage
    cx, cy = W, H - 200
    draw.ellipse([cx - 180, cy - 240, cx + 180, cy + 180], fill=(40, 30, 60))
    draw.text((cx - 120, H * 2 - 160), "En conversation avec Luna...", fill=purple, font=font)
    # Bouton raccrocher
    draw.ellipse([cx - 35, H * 2 - 100, cx + 35, H * 2 - 30], fill=(239, 68, 68))
    draw.text((cx - 8, H * 2 - 80), "✕", fill="white", font=font)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "tavus_fullscreen.png"))
    print("OK")

    # --- PERCEPTION ---
    print("    perception_camera (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Perception")
    # Camera feed placeholder
    cam_y = 160
    draw.rounded_rectangle([40, cam_y, W * 2 - 40, cam_y + 500], radius=16, fill=(20, 20, 40))
    draw.text((60, cam_y + 10), "● En direct", fill=(74, 222, 128), font=font_small)
    draw.text((W - 40, cam_y + 220), "📷", fill=dim_text, font=font_big)
    # Analyse card
    ay = cam_y + 530
    draw.rounded_rectangle([40, ay, W * 2 - 40, ay + 180], radius=16, fill=card_bg)
    draw.text((60, ay + 15), "Ce que Luna voit :", fill=purple, font=font)
    draw.text((60, ay + 50), "1 personne assise au salon.", fill=text_color, font=font_msg)
    draw.text((60, ay + 80), "Posture : détendue. Lumière : tamisée.", fill=text_color, font=font_msg)
    draw.text((60, ay + 120), "Aucune anomalie détectée ✓", fill=(74, 222, 128), font=font_small)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "perception_camera.png"))
    print("OK")

    # --- CONTACTS ---
    print("    contacts_list (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Contacts")
    y = 170
    draw.text((40, y), "Contacts de confiance", fill=text_color, font=font_big)
    y += 50
    contacts = [
        ("Marie", "fille", "+33 6 12 34 56 78", "SMS"),
        ("Jean", "voisin", "+33 6 98 76 54 32", "Appel"),
        ("Dr Dupont", "médecin", "+33 1 23 45 67 89", "Urgence"),
    ]
    for name, rel, phone, channel in contacts:
        draw.rounded_rectangle([40, y, W * 2 - 40, y + 100], radius=12, fill=card_bg)
        draw.text((60, y + 12), name, fill=text_color, font=font)
        draw.rounded_rectangle([60 + len(name) * 14, y + 12, 60 + len(name) * 14 + len(rel) * 11 + 16, y + 36], radius=8, fill=dark_purple)
        draw.text((60 + len(name) * 14 + 8, y + 14), rel, fill=purple, font=font_small)
        draw.text((60, y + 45), phone, fill=dim_text, font=font_small)
        draw.text((60, y + 70), f"Canal : {channel}", fill=dim_text, font=font_small)
        y += 115
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "contacts_list.png"))
    print("OK")

    # --- FRIENDS ---
    print("    friends_list (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Amis")
    y = 170
    draw.text((40, y), "Mon code ami : ", fill=text_color, font=font)
    draw.rounded_rectangle([280, y - 4, 440, y + 32], radius=8, fill=dark_purple)
    draw.text((295, y), "AB3K7X", fill=purple, font=font)
    y += 60
    draw.text((40, y), "Mes amis (3)", fill=text_color, font=font_big)
    y += 50
    friends = [("Sophie", "● en ligne", "Niv. 4"), ("Lucas", "hors ligne", "Niv. 7"), ("Emma", "● en ligne", "Niv. 2")]
    for name, status, level in friends:
        draw.rounded_rectangle([40, y, W * 2 - 40, y + 80], radius=12, fill=card_bg)
        draw.text((70, y + 15), "👤", fill=text_color, font=font)
        draw.text((110, y + 15), name, fill=text_color, font=font)
        color = (74, 222, 128) if "en ligne" in status else dim_text
        draw.text((110, y + 45), status, fill=color, font=font_small)
        draw.text((W * 2 - 200, y + 20), level, fill=purple, font=font_small)
        draw.rounded_rectangle([W * 2 - 170, y + 45, W * 2 - 60, y + 70], radius=8, fill=dark_purple)
        draw.text((W * 2 - 155, y + 47), "Message", fill=purple, font=font_small)
        y += 95
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "friends_list.png"))
    print("OK")

    # --- FRIENDS DM ---
    print("    friends_dm (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W * 2, H * 2], fill=bg_color)
    # Modal overlay
    draw.rounded_rectangle([20, 200, W * 2 - 20, H * 2 - 200], radius=20, fill=(20, 20, 40))
    draw.text((60, 220), "✕", fill=dim_text, font=font)
    draw.text((120, 225), "Sophie", fill=text_color, font=font_big)
    y = 300
    y = draw_message(draw, "Coucou ! Tu as vu le nouveau badge ?", False, y, W * 2 - 80)
    y = draw_message(draw, "Oui trop bien ! J'ai débloqué le Phare aussi 🎉", False, y, W * 2 - 80)
    # On triche un peu pour simuler un DM
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "friends_dm.png"))
    print("OK")

    # --- FAMILY ---
    print("    family_group (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    y = 120
    draw.text((40, y), "Groupe familial", fill=text_color, font=font_big)
    y += 50
    draw.rounded_rectangle([40, y, W * 2 - 40, y + 140], radius=16, fill=card_bg)
    draw.text((60, y + 15), "Famille Martin", fill=purple, font=font)
    draw.text((60, y + 50), "👨 Papa (gardien)  ✓ vérifié", fill=text_color, font=font_msg)
    draw.text((60, y + 80), "👩 Maman (gardien)  ✓ vérifié", fill=text_color, font=font_msg)
    draw.text((60, y + 110), "👧 Emma, 14 ans (ado)  ✓ vérifié", fill=text_color, font=font_msg)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "family_group.png"))
    print("OK")

    # --- FAMILY SOS ---
    print("    family_sos (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W * 2, H * 2], fill=bg_color)
    cx, cy = W, H - 100
    r = 100
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(239, 68, 68))
    draw.text((cx - 35, cy - 20), "SOS", fill="white", font=font_big)
    draw.text((cx - 120, cy + r + 30), "Appuie pour alerter", fill=text_color, font=font)
    draw.text((cx - 100, cy + r + 60), "tes proches en 1 tap", fill=dim_text, font=font)
    draw.text((cx - 140, cy - r - 80), "👧 Emma a besoin d'aide", fill=(239, 68, 68), font=font_big)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "family_sos.png"))
    print("OK")

    # --- CHAT GOODNIGHT ---
    print("    chat_goodnight (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw_header(draw, W * 2)
    draw_tabs(draw, W * 2, "Chat")
    y = 180
    y = draw_message(draw, "Bonne nuit Luna !", False, y, W * 2)
    y = draw_message(draw, "Bonne nuit ! Repose-toi bien. Je serai là demain, comme toujours.", True, y, W * 2)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "chat_goodnight.png"))
    print("OK")

    # --- WORLD BADGES ---
    print("    world_badges (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W * 2, H * 2], fill=bg_color)
    draw.text((40, 30), "Ciel Étoilé — Badges", fill=purple, font=font_big)
    draw.text((40, 70), "8 / 20 badges débloqués", fill=dim_text, font=font)
    y = 120
    badges = [
        ("🌟", "Premier Pas", "Envoie ton 1er message", True),
        ("🔥", "Série de 7j", "7 jours consécutifs", True),
        ("💬", "Bavard", "100 messages envoyés", True),
        ("📞", "Premier Appel", "Appelle Luna en vocal", True),
        ("🎥", "Face à Face", "1ère visio avec Luna", True),
        ("👥", "Sociable", "Ajoute 3 amis", True),
        ("🏆", "Maître", "Atteins le niveau 10", False),
        ("❓", "???", "Badge secret", False),
    ]
    col = 0
    for icon, name, desc, earned in badges:
        bx = 40 + col * (W - 10)
        opacity_fill = card_bg if earned else (20, 20, 30)
        draw.rounded_rectangle([bx, y, bx + W - 30, y + 120], radius=12, fill=opacity_fill)
        draw.text((bx + 20, y + 10), icon if earned else "❓", fill=text_color if earned else dim_text, font=font_big)
        draw.text((bx + 70, y + 15), name, fill=text_color if earned else dim_text, font=font)
        draw.text((bx + 70, y + 45), desc, fill=dim_text, font=font_small)
        if earned:
            draw.text((bx + 70, y + 75), "✓ Débloqué", fill=(74, 222, 128), font=font_small)
        else:
            draw.text((bx + 70, y + 75), "🔒 Verrouillé", fill=dim_text, font=font_small)
        col += 1
        if col >= 2:
            col = 0
            y += 135
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "world_badges.png"))
    print("OK")

    # --- WORLD SHOP ---
    print("    world_shop (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W * 2, H * 2], fill=bg_color)
    draw.text((40, 30), "Boutique", fill=purple, font=font_big)
    draw.text((W * 2 - 200, 35), "142 ⭐", fill=(251, 191, 36), font=font)
    y = 90
    items = [
        ("👗", "Robe Étoilée", "Tenue exclusive", "25 ⭐"),
        ("🖼️", "Cadre Doré", "Pour ton profil", "15 ⭐"),
        ("🌙", "Aura Lunaire", "Effet de lumière", "40 ⭐"),
        ("🎀", "Noeud Rose", "Accessoire mignon", "10 ⭐"),
    ]
    col = 0
    for icon, name, desc, price in items:
        bx = 40 + col * (W - 10)
        draw.rounded_rectangle([bx, y, bx + W - 30, y + 160], radius=12, fill=card_bg)
        draw.text((bx + (W - 30) // 2 - 20, y + 10), icon, fill=text_color, font=font_big)
        draw.text((bx + 20, y + 60), name, fill=text_color, font=font)
        draw.text((bx + 20, y + 90), desc, fill=dim_text, font=font_small)
        draw.rounded_rectangle([bx + 20, y + 120, bx + W - 50, y + 148], radius=8, fill=dark_purple)
        draw.text((bx + (W - 30) // 2 - 20, y + 122), price, fill=(251, 191, 36), font=font_small)
        col += 1
        if col >= 2:
            col = 0
            y += 175
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "world_shop.png"))
    print("OK")

    # --- CINEMA ZOOM ---
    print("    cinema_zoom (mockup)...", end=" ", flush=True)
    img = new_img()
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W * 2, H * 2], fill=(5, 5, 15))
    # Zoom sur l'écran du téléphone
    cx, cy = W, H
    # Écran éclairé
    draw.rounded_rectangle([cx - 250, cy - 350, cx + 250, cy + 350], radius=40, fill=(30, 30, 60))
    # Visage Luna (cercle simplifié)
    draw.ellipse([cx - 120, cy - 200, cx + 120, cy + 60], fill=(60, 40, 80))
    draw.text((cx - 80, cy + 100), "Luna répond...", fill=purple, font=font)
    # Bandes noires
    draw.rectangle([0, 0, W * 2, 200], fill="black")
    draw.rectangle([0, H * 2 - 200, W * 2, H * 2], fill="black")
    img = img.resize((W, H), Image.LANCZOS)
    img.save(str(SCREENS_DIR / "cinema_zoom.png"))
    print("OK")


def main():
    print("=== Capture écrans Luna ===\n")
    print("  Captures statiques (Chromium)...")
    capture_static_screens()
    print("\n  Mockups (Pillow)...")
    create_mockup_screens()
    print(f"\n  Tous les écrans sont dans : {SCREENS_DIR}/")
    print(f"  Total : {len(list(SCREENS_DIR.glob('*.png')))} images")


if __name__ == "__main__":
    main()
