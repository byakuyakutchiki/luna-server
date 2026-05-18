"""Routes API Secretaire personnelle Luna.

/api/secretary/*  (auth JWT via middleware request.state.tenant_id)
"""

import html
import logging
import asyncio
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .redis_ops import SecretaryRedisOps
from .scanner import scan_document, generate_budget_suggestions

logger = logging.getLogger(__name__)

secretary_router = APIRouter()

MAX_IMAGE_SIZE = 1_500_000  # ~1.1 MB base64 = ~800KB image


def _get_sops(request: Request) -> SecretaryRedisOps:
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
    return SecretaryRedisOps(rc, int(tid))


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


# =====================================================================
# SCAN DOCUMENT
# =====================================================================

@secretary_router.post("/api/secretary/scan")
async def scan_doc(request: Request):
    """Scanne un document (photo) et l'analyse via IA."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()

    try:
        body = await request.json()
        image_b64 = body.get("image", "")
        source = body.get("source", "photo")  # photo, email, upload
    except Exception:
        return _error("Corps invalide")

    if not image_b64:
        return _error("Image manquante")
    if len(image_b64) > MAX_IMAGE_SIZE:
        return _error("Image trop grande (max ~800KB)")

    openai = _get_openai()
    if not openai:
        return _error("IA non configuree", 503)

    # Analyse async
    loop = asyncio.get_event_loop()
    success, data = await scan_document(openai, image_b64)

    if not success:
        return _error(data.get("error", "Erreur d'analyse"))

    # Sanitize text fields
    for field in ("emetteur", "destinataire", "objet", "reference", "notes", "action_requise"):
        if data.get(field):
            data[field] = html.escape(str(data[field]), quote=True)

    data["source"] = source
    doc_id, is_duplicate = sops.add_document(data)

    if is_duplicate:
        existing = sops.get_document(doc_id)
        return {
            "success": True,
            "duplicate": True,
            "doc_id": doc_id,
            "message": f"Ce document existe deja (ref: {existing.get('reference', doc_id[:8])})",
            "document": existing,
        }

    doc = sops.get_document(doc_id)
    return {
        "success": True,
        "duplicate": False,
        "doc_id": doc_id,
        "document": doc,
        "message": f"Document classe dans {doc.get('folder', 'Divers')}",
    }


# =====================================================================
# DOCUMENTS - Liste & Detail
# =====================================================================

@secretary_router.get("/api/secretary/documents")
async def list_documents(request: Request, type: str = None, status: str = None, limit: int = 50):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    docs = sops.get_documents(limit=min(limit, 100), doc_type=type, status=status)
    return {"documents": docs, "count": len(docs)}


@secretary_router.get("/api/secretary/documents/{doc_id}")
async def get_document(request: Request, doc_id: str):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    doc = sops.get_document(doc_id)
    if not doc:
        return _error("Document non trouve", 404)
    return {"document": doc}


@secretary_router.post("/api/secretary/documents/{doc_id}/status")
async def update_doc_status(request: Request, doc_id: str):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    try:
        body = await request.json()
        status = body.get("status", "")
    except Exception:
        return _error("Corps invalide")
    if status not in ("pending", "paid", "overdue", "archived"):
        return _error("Statut invalide (pending, paid, overdue, archived)")
    if sops.mark_document_status(doc_id, status):
        return {"success": True}
    return _error("Document non trouve", 404)


@secretary_router.get("/api/secretary/documents/search/{query}")
async def search_docs(request: Request, query: str):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    docs = sops.search_documents(query)
    return {"documents": docs, "count": len(docs)}


@secretary_router.get("/api/secretary/summary")
async def documents_summary(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    return sops.get_documents_summary()


# =====================================================================
# DOSSIERS (Folders)
# =====================================================================

@secretary_router.get("/api/secretary/folders")
async def list_folders(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    folders = sops.get_folders()
    return {"folders": folders}


@secretary_router.get("/api/secretary/folders/{folder_path:path}")
async def folder_contents(request: Request, folder_path: str):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    docs = sops.get_folder_documents(folder_path)
    return {"folder": folder_path, "documents": docs, "count": len(docs)}


# =====================================================================
# BUDGET
# =====================================================================

@secretary_router.get("/api/secretary/budget")
async def get_budget(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    analysis = sops.get_budget_analysis()
    suggestions = generate_budget_suggestions(analysis)
    return {
        "analysis": analysis,
        "suggestions": suggestions,
        "profile": sops.get_budget_profile(),
    }


@secretary_router.post("/api/secretary/budget/profile")
async def set_budget_profile(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    try:
        body = await request.json()
    except Exception:
        return _error("Corps invalide")

    profile = {}
    for field in ("revenus_mensuels", "charges_fixes", "loyer", "credits", "epargne_cible"):
        val = body.get(field)
        if val is not None:
            try:
                profile[field] = str(float(val))
            except (ValueError, TypeError):
                return _error(f"Valeur invalide pour {field}")

    if not profile:
        return _error("Aucune donnee fournie")

    sops.set_budget_profile(profile)
    return {"success": True, "profile": sops.get_budget_profile()}


@secretary_router.post("/api/secretary/budget/entry")
async def add_budget_entry(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    try:
        body = await request.json()
    except Exception:
        return _error("Corps invalide")

    montant = body.get("montant")
    if montant is None:
        return _error("Montant requis")
    try:
        montant = float(montant)
    except (ValueError, TypeError):
        return _error("Montant invalide")

    entry = {
        "montant": montant,
        "direction": body.get("direction", "depense"),
        "categorie": html.escape(body.get("categorie", "autre")),
        "label": html.escape(body.get("label", "")[:100]),
        "date": body.get("date", ""),
    }

    entry_id = sops.add_budget_entry(entry)
    return {"success": True, "entry_id": entry_id}


@secretary_router.get("/api/secretary/budget/entries")
async def get_entries(request: Request, month: str = None):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    entries = sops.get_budget_entries(month=month)
    totals = sops.get_monthly_totals(month=month)
    return {"entries": entries, "totals": totals}


# =====================================================================
# RAPPELS
# =====================================================================

@secretary_router.get("/api/secretary/reminders")
async def list_reminders(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    upcoming = sops.get_upcoming_reminders()
    overdue = sops.get_overdue_reminders()
    return {
        "upcoming": upcoming,
        "overdue": overdue,
        "total_upcoming": len(upcoming),
        "total_overdue": len(overdue),
    }


@secretary_router.post("/api/secretary/reminders")
async def add_reminder(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    try:
        body = await request.json()
    except Exception:
        return _error("Corps invalide")

    title = html.escape(body.get("title", "").strip()[:100])
    if not title:
        return _error("Titre requis")

    reminder = {
        "title": title,
        "description": html.escape(body.get("description", "")[:300]),
        "due_date": body.get("due_date", ""),
        "due_time": body.get("due_time", ""),
        "type": body.get("type", "manuel"),
    }

    rem_id = sops.add_reminder(reminder)
    return {"success": True, "reminder_id": rem_id}


@secretary_router.post("/api/secretary/reminders/{rem_id}/done")
async def mark_done(request: Request, rem_id: str):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    if sops.mark_reminder_done(rem_id):
        return {"success": True}
    return _error("Rappel non trouve", 404)


@secretary_router.delete("/api/secretary/reminders/{rem_id}")
async def delete_reminder(request: Request, rem_id: str):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    if sops.delete_reminder(rem_id):
        return {"success": True}
    return _error("Rappel non trouve", 404)


# =====================================================================
# CHECK AFFORDABILITY ("Est-ce que je peux me le permettre ?")
# =====================================================================

@secretary_router.post("/api/secretary/can-i-afford")
async def can_i_afford(request: Request):
    """Verifie si une depense est viable par rapport au budget."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    try:
        body = await request.json()
        amount = float(body.get("amount", 0))
        label = body.get("label", "cette depense")
    except Exception:
        return _error("Corps invalide")

    if amount <= 0:
        return _error("Montant invalide")

    analysis = sops.get_budget_analysis()
    reste = analysis.get("reste_a_vivre", 0)
    prevu_fin = analysis.get("solde_prevu_fin_mois", 0)

    can_afford = (reste - amount) > 0
    safe = (prevu_fin - amount) > 50  # marge de securite 50€

    if can_afford and safe:
        verdict = "oui"
        message = f"Oui, tu peux te permettre {label} ({amount:.0f}€). Il te restera environ {prevu_fin - amount:.0f}€ en fin de mois."
    elif can_afford and not safe:
        verdict = "risque"
        message = f"C'est possible mais risque. Apres {label} ({amount:.0f}€), ta fin de mois sera tres serree ({prevu_fin - amount:.0f}€)."
    else:
        verdict = "non"
        deficit = amount - reste
        message = f"Ce n'est pas raisonnable. {label} ({amount:.0f}€) depasse ton budget disponible de {deficit:.0f}€."

    return {
        "verdict": verdict,
        "message": message,
        "amount": amount,
        "reste_avant": round(reste, 2),
        "reste_apres": round(reste - amount, 2),
        "prevu_fin_mois": round(prevu_fin - amount, 2),
    }
