"""
Luganda (lug) language profile.

Luganda is the first validation language for LingualDub. This module defines
its Language object and known resource profile, and registers it with the
framework Registry. The profile reflects a resource audit, not assumed parity
with high-resource languages.

Resource profile: speech-moderate / text-moderate
"""

from lingualdub.core.language import Language

LUGANDA = Language(
    code="lug",
    name="Luganda",
    family="Bantu (Great Lakes)",
    resource_profile="speech-moderate / text-moderate",
    supported_tasks=["asr", "translation", "tts", "code_switch"],
    related_languages=["nyn", "swa"],
    metadata={
        "region": "Uganda",
        "speakers_estimate": "~4-6 million",
        "notes": (
            "First LingualDub validation language. Some existing recordings and "
            "Uganda-focused ASR research corpora available. Parallel text to English "
            "is limited. Pretrained multilingual ASR coverage exists."
        ),
    },
)
