"""Routes API Coffre-fort documentaire — YAWatch Luna.

Chaque client gère ses propres documents.
RGPD : consentement explicite requis, delete complet disponible, images non stockées.
"""
import html
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .classifier import classify_document, DOC_TYPES
from .redis_ops import VaultRedisOps

logger = logging.getLogger("luna.vault")

vault_router = APIRouter()

_VISION_MODEL = "gpt-4o"
_MAX_IMAGE_B64 = 15_000_000


def _get_vops(request: Request) -> VaultRedisOps | None:
    tid = getattr(request.state, "tenant_id", None)
    if not tid:
        return None
    try:
        from luna_web import _redis_client
        if not _redis_client:
            return None
        return VaultRedisOps(_redis_client, int(tid))
    except (ImportError, AttributeError):
        return None


def _get_llm():
    try:
        from luna_web import openai_client
        return openai_client
    except (ImportError, AttributeError):
        return None


def _err(msg: str, status: int = 400):
    return JSONResponse(status_code=status, content={"error": msg})


# ═══════════════════════════════════════════════════════════════════════
# CONSENTEMENT RGPD
# ═══════════════════════════════════════════════════════════════════════

@vault_router.get("/api/vault/consent")
async def get_consent(request: Request):
    """Vérifie si le consentement RGPD a été donné."""
    vops = _get_vops(request)
    if not vops:
        return _err("Non disponible", 503)
    return {"consent": vops.has_consent()}


@vault_router.post("/api/vault/consent")
async def record_consent(request: Request):
    """Enregistre le consentement RGPD du client."""
    vops = _get_vops(request)
    if not vops:
        return _err("Non disponible", 503)
    vops.record_consent()
    logger.info(f"Vault consent recorded for tenant {vops.tid}")
    return {"success": True, "message": "Consentement enregistré"}


@vault_router.delete("/api/vault/consent")
async def revoke_consent(request: Request):
    """Révocation RGPD — supprime tous les documents et le consentement."""
    vops = _get_vops(request)
    if not vops:
        return _err("Non disponible", 503)
    count = vops.revoke_consent() or 0
    logger.info(f"Vault consent revoked for tenant {vops.tid} — {count} docs deleted")
    return {"success": True, "deleted_count": count, "message": "Consentement révoqué et données supprimées"}


# ═══════════════════════════════════════════════════════════════════════
# SCAN ET CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════

@vault_router.post("/api/vault/scan")
async def scan_document(request: Request):
    """Scanne, classifie, extrait les métadonnées et stocke un document.

    Corps: {image: base64, media_type: string, titre_hint?: string}
    Ne stocke PAS l'image — uniquement les métadonnées extraites (RGPD minimisation).
    """
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)

    if not vops.has_consent():
        return JSONResponse(status_code=403, content={
            "error": "Consentement RGPD requis",
            "consent_required": True,
            "message": "Veuillez accepter les conditions d'utilisation du coffre-fort avant de scanner.",
        })

    llm = _get_llm()
    if not llm:
        return _err("Service IA non disponible", 503)

    try:
        body = await request.json()
    except Exception:
        return _err("Corps JSON invalide")

    image_b64 = body.get("image", "")
    media_type = body.get("media_type", "image/jpeg")
    titre_hint = html.escape(body.get("titre_hint", ""))

    if not image_b64:
        return _err("Image manquante")
    if len(image_b64) > _MAX_IMAGE_B64:
        return _err("Image trop volumineuse (max ~10MB)")

    metadata = await classify_document(image_b64, media_type, llm, _VISION_MODEL)

    if titre_hint and not metadata.get("titre"):
        metadata["titre"] = titre_hint

    if not metadata.get("titre"):
        metadata["titre"] = metadata.get("doc_label", "Document")

    doc_id = vops.save_doc(metadata)
    logger.info(
        f"Vault scan: tenant={vops.tid} doc_id={doc_id} "
        f"type={metadata['doc_type']} expiry={metadata.get('date_expiration')} "
        f"reminders={len(metadata.get('reminders', []))}"
    )

    return {
        "success": True,
        "doc_id": doc_id,
        "doc_type": metadata["doc_type"],
        "doc_label": metadata["doc_label"],
        "doc_emoji": metadata["doc_emoji"],
        "titre": metadata["titre"],
        "emetteur": metadata.get("emetteur"),
        "date_document": metadata.get("date_document"),
        "date_expiration": metadata.get("date_expiration"),
        "montant": metadata.get("montant"),
        "reference": metadata.get("reference"),
        "notes": metadata.get("notes"),
        "expiry_status": metadata.get("expiry_status", "none"),
        "expires_in_days": metadata.get("expires_in_days"),
        "reminders_count": len(metadata.get("reminders", [])),
        "is_sensitive": metadata.get("is_sensitive", False),
        "reminders": metadata.get("reminders", []),
        # Nouveaux champs v2
        "confidence": metadata.get("confidence", 0.0),
        "extracted_fields": metadata.get("extracted_fields", {}),
        "profile_update_available": metadata.get("profile_update_available", False),
        "profile_fields": metadata.get("profile_fields", {}),
    }


# ═══════════════════════════════════════════════════════════════════════
# LISTE ET DÉTAIL
# ═══════════════════════════════════════════════════════════════════════

@vault_router.get("/api/vault/docs")
async def list_docs(request: Request):
    """Liste tous les documents du coffre-fort."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)

    if not vops.has_consent():
        return {"docs": [], "consent_required": True}

    docs = vops.resolve_folders(vops.list_docs(limit=200))
    reminders = vops.get_upcoming_reminders(days=30)

    # Compte par statut d'expiration
    summary = {"expired": 0, "urgent": 0, "warning": 0, "ok": 0, "none": 0}
    for d in docs:
        s = d.get("expiry_status", "none")
        summary[s] = summary.get(s, 0) + 1

    return {
        "docs": docs,
        "total": len(docs),
        "summary": summary,
        "upcoming_reminders": reminders[:10],
    }


@vault_router.get("/api/vault/doc/{doc_id}")
async def get_doc(request: Request, doc_id: str):
    """Détail d'un document."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)

    doc = vops.get_doc(doc_id)
    if not doc:
        return _err("Document non trouvé", 404)

    return doc


# ═══════════════════════════════════════════════════════════════════════
# SUPPRESSION (RGPD)
# ═══════════════════════════════════════════════════════════════════════

@vault_router.delete("/api/vault/doc/{doc_id}")
async def delete_doc(request: Request, doc_id: str):
    """Supprime un document (droit à l'effacement RGPD)."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)

    ok = vops.delete_doc(doc_id)
    if not ok:
        return _err("Document non trouvé", 404)

    logger.info(f"Vault delete: tenant={vops.tid} doc_id={doc_id}")
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════
# ARBORESCENCE / CLASSEMENT (issue #22, Lot A)
# ═══════════════════════════════════════════════════════════════════════

@vault_router.get("/api/vault/tree")
async def get_tree(request: Request):
    """Arborescence des documents : dossiers, sous-dossiers, compteurs, urgences."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)
    if not vops.has_consent():
        return {"tree": [], "total": 0, "consent_required": True}
    return vops.build_tree()


@vault_router.post("/api/vault/doc/{doc_id}/move")
async def move_doc(request: Request, doc_id: str):
    """Déplace un document dans un dossier. Corps: {folder_path: "Logement/Énergie"}."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)
    try:
        body = await request.json()
    except Exception:
        return _err("Corps JSON invalide")
    res = vops.move_doc(doc_id, body.get("folder_path", ""))
    if not res.get("ok"):
        return _err(res.get("error", "Échec"), 400)
    logger.info(f"Vault move: tenant={vops.tid} doc={doc_id} → {res['folder_path']}")
    return {"success": True, **res}


@vault_router.post("/api/vault/doc/{doc_id}/rename")
async def rename_doc(request: Request, doc_id: str):
    """Renomme un document. Corps: {titre: "Facture EDF – Juin 2026"}."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)
    try:
        body = await request.json()
    except Exception:
        return _err("Corps JSON invalide")
    res = vops.rename_doc(doc_id, body.get("titre", ""))
    if not res.get("ok"):
        return _err(res.get("error", "Échec"), 400)
    return {"success": True, **res}


@vault_router.post("/api/vault/folder")
async def manage_folder(request: Request):
    """CRUD dossier. Corps: {action: create|rename|merge|delete, path?, new?, src?, dst?}."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)
    try:
        body = await request.json()
    except Exception:
        return _err("Corps JSON invalide")
    action = (body.get("action") or "").strip()
    if action == "create":
        fp = vops.add_folder(body.get("path", ""))
        if not fp:
            return _err("Chemin invalide")
        return {"success": True, "path": fp}
    if action == "rename":
        res = vops.rename_folder(body.get("path", ""), body.get("new", ""))
    elif action == "merge":
        res = vops.merge_folders(body.get("src", ""), body.get("dst", ""))
    elif action == "delete":
        res = vops.delete_folder(body.get("path", ""))
    else:
        return _err(f"Action inconnue: {action}")
    if not res.get("ok"):
        return _err(res.get("error", "Échec"), 400)
    logger.info(f"Vault folder {action}: tenant={vops.tid} {body}")
    return {"success": True, **res}


# ═══════════════════════════════════════════════════════════════════════
# RAPPELS À VENIR
# ═══════════════════════════════════════════════════════════════════════

@vault_router.get("/api/vault/reminders")
async def get_reminders(request: Request):
    """Rappels à venir dans les 30 prochains jours."""
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)

    if not vops.has_consent():
        return {"reminders": []}

    return {"reminders": vops.get_upcoming_reminders(days=30)}


# ═══════════════════════════════════════════════════════════════════════
# CATALOGUE DES TYPES DE DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════

@vault_router.get("/api/vault/types")
async def get_doc_types(request: Request):
    """Liste les types de documents supportés."""
    return {
        "types": [
            {
                "id": k, "label": v["label"], "emoji": v.get("emoji", "📎"),
                "sensitive": v.get("sensitive", False),
                "fields_count": len(v.get("fields", [])),
            }
            for k, v in DOC_TYPES.items()
        ]
    }


# ═══════════════════════════════════════════════════════════════════════
# PROFIL UNIFIÉ (pont vault → formulaires)
# ═══════════════════════════════════════════════════════════════════════

@vault_router.get("/api/vault/profile-data")
async def get_profile_data(request: Request):
    """Consolide toutes les données extraites du vault en un profil structuré.

    Pont critique vault → formulaires : identité, adresse, sécu, fiscal,
    assurance, bancaire — chacun tracé vers le document source.
    """
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)

    if not vops.has_consent():
        return {"identity": {}, "address": {}, "secu": {}, "fiscal": {},
                "assurance": {}, "banking": {}, "sources": {},
                "completeness": {}, "consent_required": True}

    return vops.get_profile_data()


@vault_router.post("/api/vault/apply-to-profile")
async def apply_to_profile(request: Request):
    """Applique les champs identité d'un doc scanné au profil form-filler.

    Corps: {"doc_id": "xxx"}
    Seuls les types identité (cni, passeport, titre_sejour, permis_conduire) sont éligibles.
    """
    vops = _get_vops(request)
    if not vops:
        return _err("Authentification requise", 401)

    try:
        body = await request.json()
    except Exception:
        return _err("Corps JSON invalide")

    doc_id = body.get("doc_id", "").strip()
    if not doc_id:
        return _err("doc_id requis")

    doc = vops.get_doc(doc_id)
    if not doc:
        return _err("Document non trouvé", 404)

    doc_type = doc.get("doc_type", "")
    _IDENTITY_TYPES = {"cni", "passeport", "titre_sejour", "permis_conduire"}
    if doc_type not in _IDENTITY_TYPES:
        return _err(f"Type '{doc_type}' non éligible — seuls CNI/passeport/titre séjour/permis", 400)

    # Extraire les champs d'identité
    raw_fields = doc.get("extracted_fields", {})
    if isinstance(raw_fields, str):
        try:
            raw_fields = json.loads(raw_fields)
        except Exception:
            raw_fields = {}

    _IDENTITY_KEYS = {
        "nom", "prenom", "nom_naissance", "date_naissance", "lieu_naissance",
        "departement_naissance", "nationalite", "adresse", "code_postal",
        "ville", "numero_ci", "numero_passeport", "numero_permis",
    }
    updates = {k: v for k, v in raw_fields.items() if k in _IDENTITY_KEYS and v is not None}

    if not updates:
        return {"success": False, "updated_fields": [],
                "message": "Aucun champ identité extractible dans ce document"}

    # Écriture dans le profil form-filler (même format que FormFillerRedisOps.save_profile)
    try:
        from luna_web import _redis_client
        if not _redis_client:
            return _err("Redis non disponible", 503)
        tid = vops.tid
        profile_key = f"luna:t:{tid}:formfiller:profile"
        existing_raw = _redis_client.client.get(profile_key)
        existing = {}
        if existing_raw:
            try:
                existing = json.loads(existing_raw)
            except Exception:
                pass
        existing.update(updates)
        existing["_source_doc_id"] = doc_id
        existing["_source_doc_type"] = doc_type
        _redis_client.client.set(
            profile_key,
            json.dumps(existing, ensure_ascii=False),
            ex=86400 * 365,
        )
        logger.info(f"Vault apply-to-profile: tenant={tid} doc={doc_id} fields={list(updates.keys())}")
        return {
            "success": True,
            "updated_fields": list(updates.keys()),
            "message": f"Profil mis à jour avec {len(updates)} champs depuis {doc.get('doc_label', doc_type)}",
        }
    except Exception as e:
        logger.error(f"Vault apply-to-profile error: {e}")
        return _err(f"Erreur mise à jour profil: {e}", 500)
