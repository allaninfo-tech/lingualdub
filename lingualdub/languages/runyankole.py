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
    resource_profile="speech-moderate / text-moderate (via transfer & Sunbird SALT)",
    supported_tasks=["asr", "translation", "tts"],
    related_languages=["lug", "swa"],
    metadata={
        "region": "Western Uganda (Ankole sub-region)",
        "speakers_estimate": "~3.5 million",
        "corpora": {
            "speech": "Sunbird AI / Makerere SALT Runyankole-Rukiga corpus (~40h audio, 16kHz)",
            "text": "Uganda Parliament Hansard, JW.org bilingual corpus, Ugandan MoH health advisories",
            "pretrained_models": [
                "facebook/nllb-200-distilled-600M (nyn_Latn)",
                "facebook/mms-tts-nyn",
                "Sunbird/asr-whisper-51-african-languages",
            ],
        },
        "transfer_analysis": {
            "source_proxy": "lug",
            "lexical_similarity": "~70-80% cognate overlap with Luganda",
            "morphology": "Agglutinative Bantu noun class system identical in structure to Luganda",
            "recommendation": "Use Luganda acoustic representations as warm-start for Runyankole ASR adaptation.",
        },
        "audit_completed": True,
    },
)

