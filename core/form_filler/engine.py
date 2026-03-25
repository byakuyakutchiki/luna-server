"""Moteur FormFiller : analyse Vision + remplissage PDF.

Utilise le client OpenAI de Luna (gpt-4o-mini vision) et PyMuPDF.
"""

import base64
import json
import re
import io
import logging

import fitz  # PyMuPDF
from PIL import Image

from .models import AnalysisResult, DetectedField, FieldPosition

logger = logging.getLogger(__name__)

# ── Prompt d'analyse ──────────────────────────────────────────────

ANALYSIS_PROMPT = """Tu es un expert en analyse de formulaires administratifs français (CERFA, impôts, sécu, mutuelle, banque, etc.).

Analyse cette image de formulaire et identifie CHAQUE champ à remplir.

Pour chaque champ, donne :
- **id** : identifiant unique snake_case (ex: "nom_famille", "date_naissance")
- **label** : le texte du label tel qu'il apparaît sur le formulaire
- **field_type** : un parmi [text, date, checkbox, number, phone, email, signature, radio, select, address, textarea]
- **position** : coordonnées en pourcentage de la page {x, y, w, h} (x=gauche, y=haut, w=largeur, h=hauteur). Sois PRÉCIS.
- **description** : aide pour l'utilisateur (ce qu'il doit mettre)
- **required** : true/false
- **group** : parmi [identite, adresse, contact, professionnel, bancaire, famille, fiscal, medical, autre]
- **options** : pour checkbox/radio/select, liste des options
- **placeholder** : exemple de valeur (ex: "JJ/MM/AAAA")
- **profile_key** : si champ standard, clé parmi : nom, prenom, nom_naissance, sexe, date_naissance, lieu_naissance, departement_naissance, nationalite, numero_secu, email, telephone, adresse, complement_adresse, code_postal, ville, pays, profession, employeur, iban, bic, situation_familiale, nombre_enfants, numero_fiscal. Sinon null.

Réponds UNIQUEMENT avec un JSON valide :
{
  "form_title": "Titre",
  "form_type": "CERFA 12345*02",
  "description": "Description courte",
  "fields": [ ... ],
  "page_count": 1,
  "warnings": ["remarques"]
}

IMPORTANT : Détecte TOUS les champs. Positions PRÉCISES en %. N'invente PAS de champs inexistants."""


def _parse_json(text: str) -> dict:
    """Extrait le JSON de la réponse, même avec des code blocks markdown."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pattern in [r'```json\s*\n?(.*?)\n?\s*```', r'```\s*\n?(.*?)\n?\s*```', r'\{[\s\S]*\}']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                candidate = match.group(1) if '```' in pattern else match.group(0)
                return json.loads(candidate)
            except (json.JSONDecodeError, IndexError):
                continue
    raise ValueError(f"JSON invalide dans la réponse: {text[:300]}")


# ── Analyse Vision ────────────────────────────────────────────────

async def analyze_form(openai_client, image_b64: str, media_type: str = "image/jpeg", model: str = "gpt-4o-mini") -> AnalysisResult:
    """Analyse un formulaire via OpenAI Vision.

    Args:
        openai_client: Client OpenAI de Luna
        image_b64: Image en base64
        media_type: Type MIME (image/jpeg, image/png, application/pdf)
        model: Modèle OpenAI à utiliser

    Returns:
        AnalysisResult avec champs détectés
    """
    # Si PDF, convertir la première page en image
    if media_type == "application/pdf":
        pdf_bytes = base64.b64decode(image_b64)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        image_bytes = pix.tobytes("png")
        doc.close()
        image_b64 = base64.b64encode(image_bytes).decode()
        media_type = "image/png"

    data_uri = f"data:{media_type};base64,{image_b64}"

    response = openai_client.chat.completions.create(
        model=model,
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
                {"type": "text", "text": ANALYSIS_PROMPT},
            ],
        }],
    )

    data = _parse_json(response.choices[0].message.content)

    fields = []
    for i, f in enumerate(data.get("fields", [])):
        pos = f.get("position", {})
        field = DetectedField(
            id=f.get("id", f"field_{i}"),
            label=f.get("label", f"Champ {i+1}"),
            field_type=f.get("field_type", "text"),
            position=FieldPosition(
                x=float(pos.get("x", 0)), y=float(pos.get("y", 0)),
                w=float(pos.get("w", 30)), h=float(pos.get("h", 3)),
                page=int(pos.get("page", 0)),
            ),
            description=f.get("description", ""),
            required=f.get("required", False),
            group=f.get("group", "autre"),
            options=f.get("options", []),
            placeholder=f.get("placeholder", ""),
            profile_key=f.get("profile_key"),
        )
        fields.append(field)

    return AnalysisResult(
        form_title=data.get("form_title", "Formulaire"),
        form_type=data.get("form_type", ""),
        description=data.get("description", ""),
        fields=fields,
        page_count=data.get("page_count", 1),
        warnings=data.get("warnings", []),
    )


# ── Conversion image → PDF ────────────────────────────────────────

def image_to_pdf(image_bytes: bytes) -> bytes:
    """Convertit une image en PDF."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    # EXIF auto-rotate
    try:
        from PIL import ExifTags
        exif = img._getexif()
        if exif:
            for tag, val in exif.items():
                if ExifTags.TAGS.get(tag) == "Orientation":
                    if val == 3: img = img.rotate(180, expand=True)
                    elif val == 6: img = img.rotate(270, expand=True)
                    elif val == 8: img = img.rotate(90, expand=True)
    except (AttributeError, KeyError):
        pass
    buf = io.BytesIO()
    img.save(buf, "PDF", resolution=150)
    return buf.getvalue()


# ── PDF → images preview ──────────────────────────────────────────

def pdf_to_preview_images(pdf_bytes: bytes, dpi: int = 150) -> list[str]:
    """Convertit un PDF en images base64 pour aperçu."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        images.append(base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    return images


# ── Remplissage PDF ───────────────────────────────────────────────

def _font_size(h: float) -> float:
    if h < 12: return 8
    if h < 16: return 9
    if h < 20: return 10
    if h < 28: return 11
    return 12


def fill_pdf(pdf_bytes: bytes, fields: list[dict], signature_b64: str = None) -> bytes:
    """Remplit un PDF avec les valeurs des champs détectés.

    Args:
        pdf_bytes: PDF original
        fields: Liste de dicts avec id, value, position, field_type
        signature_b64: Signature en base64 PNG (optionnel)

    Returns:
        PDF rempli en bytes
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for f in fields:
        value = f.get("value")
        ftype = f.get("field_type", "text")
        pos = f.get("position", {})

        if not value and ftype != "signature":
            continue

        page_num = int(pos.get("page", 0))
        if page_num >= len(doc):
            continue

        page = doc[page_num]
        pw, ph = page.rect.width, page.rect.height

        x = (float(pos.get("x", 0)) / 100) * pw
        y = (float(pos.get("y", 0)) / 100) * ph
        w = (float(pos.get("w", 30)) / 100) * pw
        h = (float(pos.get("h", 3)) / 100) * ph
        rect = fitz.Rect(x, y, x + w, y + h)

        if ftype == "checkbox":
            if value and value.lower() in ("true", "oui", "yes", "x", "1"):
                fs = min(h * 0.8, 14)
                page.insert_text(
                    fitz.Point(x + w/2 - fs/4, y + h/2 + fs/3),
                    "X", fontsize=fs, fontname="helv", color=(0, 0, 0.6),
                )
        elif ftype == "signature":
            if signature_b64:
                try:
                    sig = signature_b64.split(",")[1] if "," in signature_b64 else signature_b64
                    sig_bytes = base64.b64decode(sig)
                    page.insert_image(fitz.Rect(x+2, y+2, x+w-2, y+h-2), stream=sig_bytes)
                except Exception:
                    page.insert_textbox(rect, "Signé électroniquement",
                                        fontsize=8, fontname="helv", color=(0, 0, 0.5),
                                        align=fitz.TEXT_ALIGN_CENTER)
        else:
            fs = _font_size(h)
            text_rect = fitz.Rect(x+2, y+1, x+w-2, y+h-1)
            page.insert_textbox(text_rect, value or "", fontsize=fs,
                                fontname="helv", color=(0, 0, 0.15))

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()
