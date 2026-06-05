"""
Luna Global Settings - Configuration centralisee pour les modes de fonctionnement.

Variables d'environnement:
    FOUNDATION_TEST_MODE: bool = False
        True = aucun appel externe reel (SMS, email, appels, reservations, paiements)
    ALLOW_TEST_EXTERNAL: bool = False
        Surcharge dangereuse pour forcer les appels externes meme en test.
        NE JAMAIS METTRE True EN PRODUCTION.
"""
import os
import logging

logger = logging.getLogger(__name__)


class LunaSettings:
    """Configuration globale Luna, lue depuis les variables d'environnement."""

    def __init__(self):
        self.foundation_test_mode = os.getenv("FOUNDATION_TEST_MODE", "false").lower() == "true"
        self.allow_test_external = os.getenv("ALLOW_TEST_EXTERNAL", "false").lower() == "true"

        if self.foundation_test_mode:
            logger.warning(
                "🧪 FOUNDATION_TEST_MODE=True — Aucun appel externe reel ne sera effectue"
            )
        if self.allow_test_external:
            logger.critical(
                "⚠️ ALLOW_TEST_EXTERNAL=True — Les appels externes sont FORCES en mode test. "
                "NE JAMAIS UTILISER EN PRODUCTION."
            )

    @property
    def is_production_safe(self) -> bool:
        """True si le systeme peut faire des appels externes reels."""
        return not self.foundation_test_mode or self.allow_test_external


# Singleton global
_settings_instance = None


def get_settings() -> LunaSettings:
    """Retourne l'instance singleton des settings Luna."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = LunaSettings()
    return _settings_instance


def reset_settings() -> LunaSettings:
    """Force le rechargement des settings (utile pour les tests)."""
    global _settings_instance
    _settings_instance = LunaSettings()
    return _settings_instance
