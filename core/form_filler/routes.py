"""Routes API Form Filler Luna.

/api/form-filler/*  (auth JWT via middleware request.state.tenant_id)
"""

import base64
import html
import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from .redis_ops import FormFillerRedisOps
from .engine import analyze_form, fill_pdf, image_to_pdf, pdf_to_preview_images

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

    # Sauvegarder la session
    analysis_dict = analysis.model_dump()
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
# HISTORIQUE
# ═══════════════════════════════════════════════════════════════════

@form_filler_router.get("/api/form-filler/history")
async def api_history(request: Request):
    """Historique des formulaires remplis."""
    fops = _get_fops(request)
    if not fops:
        return _unavailable()
    return {"history": fops.get_history()}
