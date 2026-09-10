"""
Runyankole (nyn) language profile.

Runyankole is the second validation language for LingualDub, chosen to test
cross-language framework generality rather than treating Luganda as a proxy
for all Bantu languages. Its resource profile is sparser than Luganda's,
making it a direct test of the framework's language-family transfer capability.

Resource profile (M8.1 Final — audit completed 2026-09-10):
  speech-sparse / text-sparse (native) → speech-moderate via family transfer
See docs/research/runyankole_audit.md for full audit and licenses.
"""

from lingualdub.core.language import Language

RUNYANKOLE = Language(
    code="nyn",
    name="Runyankole",
    family="Bantu (Great Lakes)",
    resource_profile="speech-sparse / text-sparse → speech-moderate via Luganda family transfer (SALT 40h Runyankole-Rukiga, audit 2026-09-10)",
    supported_tasks=["asr", "translation", "tts", "code_switch"],
    related_languages=["lug", "swa", "lgg"],
    resources=[
        "nyn_asr_eval_salt_v1",
        "nyn_eng_parallel_eval_salt_v1",
        "dummy_timing_resource",
        "speaker_encoder_dummy_v1",
    ],
    compatible_components=[
        "runyankole_asr",
        "dummy_asr",
        "sunbird_asr",
        "whisper_asr",
        "dummy_translator",
        "hf_translator",
        "dummy_tts",
        "mms_tts",
    ],
    metadata={
        "region": "Western Uganda (Ankole sub-region)",
        "speakers_estimate": "~3.5 million",
        "resource_profile_final": "speech-sparse / text-sparse (native) → speech-moderate via family transfer",
        "audit_date": "2026-09-10",
        "audit_documentation": "docs/research/runyankole_audit.md",
        "corpora": {
            "speech": "Sunbird AI / Makerere SALT Runyankole-Rukiga corpus (~40h audio, 16kHz, Ankole sub-region, CC-BY-4.0)",
            "speech_hours": "~40h SALT Runyankole-Rukiga (Makerere/Sunbird), 16kHz, single-mic, verified transcripts",
            "text": "Uganda Parliament Hansard (2020-2024), JW.org bilingual Runyankole-English, Ugandan MoH health advisories (parallel, CC-BY-4.0 where released)",
            "text_sources_detailed": [
                "SALT Runyankole-Rukiga speech corpus (Makerere AI / Sunbird AI) — CC-BY-4.0 — https://huggingface.co/datasets/Sunbird/salt",
                "Uganda Parliament Hansard transcripts (English-Runyankole) — public domain/government release",
                "JW.org Watchtower parallel corpus (Runyankole) — research use, non-commercial segments excluded from release",
                "MoH health advisories (Runyankole) — CC-BY-4.0 via Sunbird",
            ],
            "pretrained_models": [
                "facebook/nllb-200-distilled-600M (nyn_Latn) — CC-BY-NC 4.0 / research",
                "facebook/mms-tts-nyn — CC-BY-NC 4.0",
                "Sunbird/asr-whisper-51-african-languages — Apache-2.0 (covers lug, nyn, lgg, ach, teo, swa)",
                "openai/whisper-large-v3 — MIT (multilingual fallback)",
            ],
            "licenses": {
                "SALT": "CC-BY-4.0",
                "Sunbird checkpoints": "Apache-2.0",
                "mms-tts-nyn": "CC-BY-NC 4.0",
                "nllb-200": "CC-BY-NC 4.0",
            },
        },
        "transfer_analysis": {
            "source_proxy": "lug",
            "lexical_similarity": "~70-80% cognate overlap with Luganda (Bantu Great Lakes, Runyankore-Rukiga close to Luganda)",
            "morphology": "Agglutinative Bantu noun class system identical in structure to Luganda (classes 1-10 correspond 1:1)",
            "phonology": "Shared 5-vowel system, identical consonant inventory except Runyankole retained /r/ vs Luganda /l/ contrast",
            "recommendation": "Use Luganda acoustic representations as warm-start for Runyankole ASR adaptation; fine-tune Sunbird SALT Luganda checkpoint on 40h Runyankole-Rukiga. NLLB nyn_Latn already supports direct MT.",
            "evidence": "Luganda SALT model zero-shot WER ~35% on Runyankole held-out (reported in Sunbird SALT paper); after 10h fine-tune projected <20% WER.",
        },
        "evaluation_resources": [
            "nyn_asr_eval_salt_v1 (5 samples, SALT_ASR_EVAL_PROTOCOL_V1, CC-BY-4.0)",
            "nyn_eng_parallel_eval_salt_v1 (3 pairs, SALT_MT_EVAL_PROTOCOL_V1, CC-BY-4.0)",
        ],
        "audit_completed": True,
        "notes": "M8.1 final audit completed 2026-09-10 — speech-sparse native augmented to moderate via family transfer. No core framework change required.",
    },
)

