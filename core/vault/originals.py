"""Stockage chiffré des documents originaux — Coffre-fort Luna (issue #22, phase 2 / option B).

Option B validée par Ludo : on conserve l'original (image/PDF) **chiffré au repos**,
de façon **opt-in** (consentement séparé), avec **droit à l'effacement** en cascade.

Défense en profondeur :
  - chiffrement applicatif Fernet (AES-128-CBC + HMAC) AVANT upload — la clé n'est
    jamais stockée ni connue de GCS ;
  - chiffrement GCS natif au repos (Google-managed) par-dessus ;
  - clé dérivée par (tenant, doc) via HKDF-SHA256 d'un secret serveur — compromettre
    un objet ne révèle pas les autres, et aucune clé ne transite/persiste.

Dégrade proprement si GCS ou la clé sont indisponibles (la feature se désactive,
le reste du vault continue de fonctionner).
"""
import base64
import logging
import os

logger = logging.getLogger("luna.vault.originals")

_BUCKET_NAME = os.getenv("VAULT_ORIGINALS_BUCKET", "luna-vault-originals-674304336025")
_gcs_client = None
_gcs_err = None


def _bucket():
    """Bucket GCS des originaux (lazy init). None si indisponible."""
    global _gcs_client, _gcs_err
    if _gcs_client is None:
        try:
            from google.cloud import storage as _gcs_storage
            _gcs_client = _gcs_storage.Client()
        except Exception as e:  # noqa: BLE001
            _gcs_err = str(e)
            logger.warning(f"GCS indisponible pour les originaux: {e}")
            return None
    try:
        return _gcs_client.bucket(_BUCKET_NAME)
    except Exception as e:  # noqa: BLE001
        _gcs_err = str(e)
        return None


def available() -> bool:
    """Vrai si le stockage chiffré des originaux est opérationnel (clé + GCS)."""
    return _master_secret() is not None and _bucket() is not None


def _master_secret() -> bytes | None:
    secret = os.getenv("VAULT_ORIGINALS_KEY") or os.getenv("JWT_SECRET_KEY")
    return secret.encode("utf-8") if secret else None


def _fernet(tenant_id: int, doc_id: str):
    """Dérive une clé Fernet propre à (tenant, doc) via HKDF-SHA256. None si pas de secret."""
    master = _master_secret()
    if not master:
        return None
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=f"vault-orig:{tenant_id}:{doc_id}".encode("utf-8"),
        info=b"luna-vault-original-v1",
    )
    key = base64.urlsafe_b64encode(hkdf.derive(master))
    return Fernet(key)


def _blob_path(tenant_id: int, doc_id: str) -> str:
    return f"originals/{tenant_id}/{doc_id}.enc"


def store(tenant_id: int, doc_id: str, data: bytes, content_type: str) -> bool:
    """Chiffre puis stocke l'original. Retourne True si stocké."""
    f = _fernet(tenant_id, doc_id)
    bkt = _bucket()
    if not f or not bkt:
        return False
    try:
        token = f.encrypt(data)
        blob = bkt.blob(_blob_path(tenant_id, doc_id))
        # content_type réel mémorisé en métadonnée ; l'objet stocké est opaque (chiffré)
        blob.metadata = {"ct": content_type or "application/octet-stream"}
        blob.upload_from_string(token, content_type="application/octet-stream")
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"store original échec tid={tenant_id} doc={doc_id}: {e}")
        return False


def fetch(tenant_id: int, doc_id: str):
    """Récupère et déchiffre l'original. Retourne (bytes, content_type) ou None."""
    f = _fernet(tenant_id, doc_id)
    bkt = _bucket()
    if not f or not bkt:
        return None
    try:
        blob = bkt.blob(_blob_path(tenant_id, doc_id))
        if not blob.exists():
            return None
        blob.reload()
        ct = (blob.metadata or {}).get("ct", "application/octet-stream")
        token = blob.download_as_bytes()
        data = f.decrypt(token)
        return data, ct
    except Exception as e:  # noqa: BLE001
        logger.error(f"fetch original échec tid={tenant_id} doc={doc_id}: {e}")
        return None


def has(tenant_id: int, doc_id: str) -> bool:
    bkt = _bucket()
    if not bkt:
        return False
    try:
        return bkt.blob(_blob_path(tenant_id, doc_id)).exists()
    except Exception:  # noqa: BLE001
        return False


def delete(tenant_id: int, doc_id: str) -> bool:
    """Supprime l'original (droit à l'effacement)."""
    bkt = _bucket()
    if not bkt:
        return False
    try:
        blob = bkt.blob(_blob_path(tenant_id, doc_id))
        if blob.exists():
            blob.delete()
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"delete original échec tid={tenant_id} doc={doc_id}: {e}")
        return False


def delete_all(tenant_id: int) -> int:
    """Supprime tous les originaux d'un tenant (révocation RGPD)."""
    bkt = _bucket()
    if not bkt:
        return 0
    n = 0
    try:
        for blob in bkt.list_blobs(prefix=f"originals/{tenant_id}/"):
            blob.delete()
            n += 1
    except Exception as e:  # noqa: BLE001
        logger.error(f"delete_all originals échec tid={tenant_id}: {e}")
    return n
