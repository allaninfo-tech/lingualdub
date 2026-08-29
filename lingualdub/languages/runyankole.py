"""
Runyankole (nyn) language profile.

Runyankole is the second validation language for LingualDub, chosen to test
cross-language framework generality rather than treating Luganda as a proxy
for all Bantu languages. Its resource profile is sparser than Luganda's,
making it a direct test of the framework's language-family transfer capability.

Resource profile: speech-sparse / text-sparse (audit in progress)
"""

from lingualdub.core.language import Language

RUNYANKOLE = Language(
    code="nyn",
    name="Runyankole",
    family="Bantu (Great Lakes)",
    resource_profile="speech-sparse / text-sparse",
    supported_tasks=["asr"],
    related_languages=["lug", "swa"],
    metadata={
        "region": "Uganda (Western)",
        "speakers_estimate": "~2-3 million",
        "notes": (
            "Second LingualDub validation language. Resource audit in progress. "
            "Shares Bantu morphology and geographic contact history with Luganda, "
            "making it a direct test of language-family transfer (§11). "
            "Minimal standalone pretrained model coverage confirmed so far."
        ),
    },
)
