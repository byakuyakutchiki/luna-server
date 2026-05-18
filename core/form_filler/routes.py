"""Routes API Form Filler Luna.

/api/form-filler/*  (auth JWT via middleware request.state.tenant_id)
"""

import base64
import html
import json
import logging
import os
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from .redis_ops import FormFillerRedisOps
from .engine import analyze_form, fill_pdf, image_to_pdf, pdf_to_preview_images

# Modèles vision par provider (OCR pièce d'identité)
_VISION_MODELS = {
    "openai":   "gpt-4o",
    "deepseek": "deepseek-chat",
    "kimi":     "moonshot-v1-8k",
}

_ID_FIELDS = [
    "nom", "prenom", "nom_naissance", "date_naissance", "lieu_naissance",
    "departement_naissance", "nationalite", "adresse", "code_postal",
    "ville", "numero_ci",
]

_OCR_PROMPT = """Tu es un systeme d'OCR expert specialise dans l'extraction de donnees depuis des pieces d'identite francaises (CNI, passeport, titre de sejour).

Analyse cette image et extrais les informations suivantes. Reponds UNIQUEMENT en JSON valide avec ces cles exactes :

{
    "nom": "string ou null",
    "prenom": "string ou null",
    "nom_naissance": "string ou null",
    "date_naissance": "YYYY-MM-DD ou null",
    "lieu_naissance": "string ou null",
    "departement_naissance": "string ou null (numero ou nom)",
    "nationalite": "string ou null",
    "adresse": "string ou null (numero + rue uniquement)",
    "code_postal": "string ou null",
    "ville": "string ou null",
    "numero_ci": "string ou null"
}

REGLES :
- Si un champ n'est pas visible ou illisible, mets null
- Pour la date de naissance, convertis TOUJOURS au format YYYY-MM-DD
- Pour l'adresse, ne garde que numero + rue (sans code postal ni ville)
- Ne rajoute AUCUN texte en dehors du JSON
- Ne fais AUCUNE supposition — null si tu n'es pas sur a plus de 90%"""

logger = logging.getLogger(__name__)

form_filler_router = APIRouter()

MAX_UPLOAD_B64 = 25_000_000  # ~18 MB image


def _get_fops(request: Request) -> FormFillerRedisOps | None:
    rc = getattr(request.app.state, "_redis_client", None)
    if rc is None:
        try:
            from luna_web import _redis_client
            rc = _redis_client
        except (ImportError, AttributeError):
            return None
    if rc is None:
        return None
    tid = getattr(request.state, "tenant_id", None)
    if tid is None:
        return None
    return FormFillerRedisOps(rc, int(tid))


def _get_openai():
    try:
        from luna_web import openai_client
        return openai_client
    except (ImportError, AttributeError):
        return None


def _error(msg, status=400):
    return JSONResponse(status_code=status, content={"error": msg})


def _unavailable():
    return _error("Service non disponible", 503)


# ═══════════════════════════════════════════════════════════════════
# ANALYSE DU FORMULAIRE
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.post("/api/form-filler/analyze")
async def api_analyze(request: Request):
    """Upload et analyse d'un formulaire (image ou PDF en base64)."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()

    openai = _get_openai()
    if not openai:
        return _error("OpenAI non configuré", 503)

    try:
        body = await request.json()
        file_b64 = body.get("file", "")
        filename = html.escape(body.get("filename", "formulaire.pdf"))
        media_type = body.get("media_type", "image/jpeg")
    except Exception:
        return _error("Corps invalide")

    if not file_b64:
        return _error("Fichier manquant (champ 'file' en base64)")
    if len(file_b64) > MAX_UPLOAD_B64:
        return _error("Fichier trop volumineux (max 18 MB)")

    # Si image, créer aussi une version PDF pour le remplissage
    try:
        raw_bytes = base64.b64decode(file_b64)
    except Exception:
        return _error("Base64 invalide")

    if media_type.startswith("image/"):
        pdf_bytes = image_to_pdf(raw_bytes)
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
    elif media_type == "application/pdf":
        pdf_b64 = file_b64
    else:
        return _error(f"Type non supporté: {media_type}")

    # Analyse Vision IA
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        analysis = await analyze_form(openai, file_b64, media_type, model)
    except Exception as e:
        logger.error(f"Form filler analysis failed: {e}")
        return _error(f"Erreur d'analyse IA: {str(e)}", 500)

    # Ajouter un warning si c'est une photo (pas un vrai PDF)
    is_photo = media_type.startswith("image/")
    if is_photo:
        analysis.warnings.insert(0,
            "Document uploadé en photo. Pour un résultat optimal, "
            "téléchargez le formulaire PDF vierge depuis le site officiel "
            "(service-public.fr, impots.gouv.fr, etc.) et uploadez-le ici."
        )

    # Sauvegarder la session
    analysis_dict = analysis.model_dump()
    analysis_dict["is_photo"] = is_photo
    sid = fops.create_session(analysis_dict, pdf_b64, filename)

    logger.info(f"FORM_FILLER: analyzed {filename}, {len(analysis.fields)} fields, session={sid}")

    return {
        "session_id": sid,
        **analysis_dict,
    }


# ═══════════════════════════════════════════════════════════════════
# APERÇU PDF
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.get("/api/form-filler/preview/{session_id}")
async def api_preview(request: Request, session_id: str, page: int = 0):
    """Aperçu image d'une page du PDF original."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()

    session = fops.get_session(session_id)
    if not session:
        return _error("Session expirée", 404)

    pdf_bytes = base64.b64decode(session["pdf_b64"])
    images = pdf_to_preview_images(pdf_bytes)

    if page >= len(images):
        return _error("Page inexistante", 404)

    return {"page": page, "total_pages": len(images), "image": images[page]}


# ═══════════════════════════════════════════════════════════════════
# REMPLISSAGE PDF
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.post("/api/form-filler/fill")
async def api_fill(request: Request):
    """Remplit le PDF avec les valeurs fournies."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()

    try:
        body = await request.json()
        sid = body.get("session_id", "")
        fields = body.get("fields", [])
        signature = body.get("signature_data")
    except Exception:
        return _error("Corps invalide")

    if not sid:
        return _error("session_id manquant")

    session = fops.get_session(sid)
    if not session:
        return _error("Session expirée. Réuploadez le document.", 404)

    pdf_bytes = base64.b64decode(session["pdf_b64"])

    try:
        filled_bytes = fill_pdf(pdf_bytes, fields, signature)
    except Exception as e:
        logger.error(f"Form filler fill failed: {e}")
        return _error(f"Erreur de remplissage: {str(e)}", 500)

    # Sauvegarder le PDF rempli
    filled_b64 = base64.b64encode(filled_bytes).decode()
    fops.save_filled_pdf(sid, filled_b64)

    # Aperçu du résultat
    previews = pdf_to_preview_images(filled_bytes)

    # Historique
    fops.add_to_history({
        "filename": session.get("filename", "formulaire"),
        "form_title": session.get("analysis", {}).get("form_title", ""),
        "fields_count": len(fields),
        "filled_count": sum(1 for f in fields if f.get("value")),
    })

    logger.info(f"FORM_FILLER: filled {session.get('filename')}, session={sid}")

    return {
        "success": True,
        "preview_pages": previews,
        "page_count": len(previews),
    }


# ═══════════════════════════════════════════════════════════════════
# TÉLÉCHARGEMENT
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.get("/api/form-filler/download/{session_id}")
async def api_download(request: Request, session_id: str):
    """Télécharge le PDF rempli."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()

    filled_b64 = fops.get_filled_pdf(session_id)
    if not filled_b64:
        return _error("PDF non trouvé. Session expirée ou non rempli.", 404)

    session = fops.get_session(session_id)
    filename = "formulaire_rempli.pdf"
    if session:
        name = session.get("filename", "formulaire").rsplit(".", 1)[0]
        filename = f"{name}_rempli.pdf"

    pdf_bytes = base64.b64decode(filled_b64)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════
# AUTO-FILL DEPUIS PROFIL
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.post("/api/form-filler/autofill/{session_id}")
async def api_autofill(request: Request, session_id: str):
    """Pré-remplit les champs depuis le profil utilisateur."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()

    session = fops.get_session(session_id)
    if not session:
        return _error("Session expirée", 404)

    profile = fops.get_profile()
    if not profile:
        return {"fields": [], "filled_count": 0, "total_count": 0}

    analysis = session.get("analysis", {})
    fields = analysis.get("fields", [])

    filled_count = 0
    for field in fields:
        pk = field.get("profile_key")
        if pk and pk in profile and profile[pk]:
            field["value"] = str(profile[pk])
            filled_count += 1

    return {
        "fields": fields,
        "filled_count": filled_count,
        "total_count": len(fields),
    }


# ═══════════════════════════════════════════════════════════════════
# PROFIL UTILISATEUR
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.get("/api/form-filler/profile")
async def api_get_profile(request: Request):
    """Récupère le profil utilisateur."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()
    return fops.get_profile()


@form_filler_router.post("/api/form-filler/profile")
async def api_save_profile(request: Request):
    """Sauvegarde le profil utilisateur."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()
    try:
        profile = await request.json()
    except Exception:
        return _error("Corps invalide")

    # Sanitize
    clean = {}
    for k, v in profile.items():
        if isinstance(v, str):
            clean[html.escape(k)] = html.escape(v.strip())
    fops.save_profile(clean)
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# SCAN PIÈCE D'IDENTITÉ (OCR Vision IA)
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.post("/api/form-filler/profile/scan-document")
async def api_scan_identity_document(request: Request):
    """Extrait les champs d'identité depuis une photo de CNI/passeport via Vision IA."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Corps JSON invalide"})

    image_b64 = body.get("image", "")
    media_type = body.get("media_type", "image/jpeg")

    if not image_b64:
        return JSONResponse(status_code=400, content={"error": "Image manquante"})
    if len(image_b64) > 15_000_000:
        return JSONResponse(status_code=413, content={"error": "Image trop volumineuse (max ~10MB)"})

    # Fabrique le client LLM vision selon le provider configuré
    try:
        from integrations.llm.provider import build_llm_client, LLM_PROVIDERS
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        vision_model = _VISION_MODELS.get(provider, "gpt-4o")
        llm = build_llm_client()
    except Exception as e:
        logger.error(f"Scan ID — client LLM indisponible: {e}")
        return JSONResponse(status_code=503, content={"error": "Service IA non disponible"})

    data_uri = f"data:{media_type};base64,{image_b64}"

    try:
        # response_format json_object force gpt-4o à ne jamais wrapper en markdown
        fmt_kwargs = {}
        if provider == "openai":
            fmt_kwargs["response_format"] = {"type": "json_object"}

        resp = llm.chat.completions.create(
            model=vision_model,
            messages=[
                {"role": "system", "content": (
                    "Tu es un extracteur OCR de pièces d'identité françaises. "
                    "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, "
                    "sans bloc markdown, sans commentaire."
                )},
                {"role": "user", "content": [
                    {"type": "text", "text": _OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
                ]},
            ],
            max_tokens=800,
            temperature=0.0,
            **fmt_kwargs,
        )
        raw = resp.choices[0].message.content or ""

        # Parse JSON — priorité json_object, fallback extraction manuelle
        extracted: dict = {}
        try:
            extracted = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            try:
                m = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
                json_str = m.group(1) if m else raw[raw.find("{"):raw.rfind("}") + 1]
                if json_str.strip():
                    extracted = json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Scan ID — réponse non-JSON du LLM: {raw[:120]}")

        # Normalise : garantit toutes les clés attendues
        for k in _ID_FIELDS:
            if k not in extracted:
                extracted[k] = None

        missing = [k for k in _ID_FIELDS if not extracted.get(k)]
        filled_count = len(_ID_FIELDS) - len(missing)
        confidence = "high" if len(missing) <= 2 else "medium" if len(missing) <= 5 else "low"

        if filled_count == 0:
            logger.info(f"Scan ID — aucun champ extrait (document illisible?) | provider={provider}")
            return {"success": True, "extracted": extracted, "missing": missing, "confidence": "none",
                    "warning": "Document illisible ou aucune pièce d'identité détectée."}

        logger.info(f"Scan ID — tenant {getattr(request.state, 'tenant_id', '?')}: {filled_count}/{len(_ID_FIELDS)} champs | provider={provider} | model={vision_model}")
        return {"success": True, "extracted": extracted, "missing": missing, "confidence": confidence}
    except Exception as e:
        logger.exception(f"Scan ID — erreur API: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur lors de l'analyse: {e}"})


# ═══════════════════════════════════════════════════════════════════
# HISTORIQUE
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.get("/api/form-filler/history")
async def api_history(request: Request):
    """Historique des formulaires remplis."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()
    return {"history": fops.get_history()}
