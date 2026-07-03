import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.openai.web_voice_bridge import WebVoiceBridge


def test_emergency_summary_keeps_raw_phrase():
    enriched = WebVoiceBridge._enrich_emergency_summary(
        "malaise",
        "au secours, j'ai du mal à respirer",
    )

    assert enriched == "malaise. Phrase entendue : au secours, j'ai du mal à respirer"


def test_emergency_summary_does_not_duplicate_raw_phrase():
    enriched = WebVoiceBridge._enrich_emergency_summary(
        "malaise. Phrase entendue : au secours, j'ai du mal à respirer",
        "au secours, j'ai du mal à respirer",
    )

    assert enriched == "malaise. Phrase entendue : au secours, j'ai du mal à respirer"
