"""
Luna LLM Provider — fabrique le client OpenAI-compatible selon LLM_PROVIDER.

Variables d'environnement:
  LLM_PROVIDER   : openai | deepseek | kimi   (défaut: openai)
  LLM_API_KEY    : clé API du provider choisi  (prioritaire)
  OPENAI_API_KEY : rétrocompatibilité si LLM_PROVIDER=openai et LLM_API_KEY absent
  LLM_MODEL      : modèle à utiliser (optionnel, défaut par provider)
  OPENAI_MODEL   : rétrocompatibilité si LLM_MODEL absent
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# Configs par provider : (base_url, modèle_par_défaut, nom_lisible)
LLM_PROVIDERS: dict[str, tuple[str | None, str, str]] = {
    "openai":   (None,                           "gpt-4o-mini",          "OpenAI ChatGPT"),
    "deepseek": ("https://api.deepseek.com",      "deepseek-chat",        "DeepSeek"),
    "kimi":     ("https://api.moonshot.cn/v1",    "moonshot-v1-8k",       "Kimi (Moonshot)"),
}


def build_llm_client(api_key: str | None = None) -> OpenAI:
    """
    Construit et retourne un client OpenAI-compatible pour le provider configuré.
    Lève ValueError si la clé API est absente hors mode SETUP.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()

    if provider not in LLM_PROVIDERS:
        logger.warning(f"LLM_PROVIDER inconnu '{provider}' — fallback openai")
        provider = "openai"

    base_url, _default_model, label = LLM_PROVIDERS[provider]

    # Résolution de la clé API (priorité: argument > LLM_API_KEY > OPENAI_API_KEY pour openai)
    key = api_key or os.getenv("LLM_API_KEY") or (
        os.getenv("OPENAI_API_KEY") if provider == "openai" else None
    )

    if not key:
        raise ValueError(
            f"Clé API manquante pour {label}. "
            f"Définissez LLM_API_KEY (ou OPENAI_API_KEY si provider=openai) dans .env"
        )

    logger.info(f"LLM provider: {label} | model: {get_llm_model()}")

    kwargs: dict = {"api_key": key}
    if base_url:
        kwargs["base_url"] = base_url

    return OpenAI(**kwargs)


def get_llm_model() -> str:
    """Retourne le modèle LLM à utiliser selon la config."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    _, default_model, _ = LLM_PROVIDERS.get(provider, LLM_PROVIDERS["openai"])
    # LLM_MODEL en priorité, sinon OPENAI_MODEL (rétrocompat), sinon défaut provider
    return os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or default_model


def get_provider_label() -> str:
    """Retourne le nom lisible du provider actif."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    _, _, label = LLM_PROVIDERS.get(provider, LLM_PROVIDERS["openai"])
    return label
