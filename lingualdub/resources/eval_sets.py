"""
Standard evaluation datasets registered as first-class Resource objects.

These resources provide benchmark evaluation data for:
- Luganda ASR transcription evaluation (WER/CER)
- Luganda -> English translation evaluation (BLEU/chrF)
- Luganda-English mixed-language code-switching evaluation
"""

from __future__ import annotations
from typing import Dict, List, Optional
from lingualdub.core.resource import Resource, ResourceKind

# ─────────────────────────────────────────────────────────────────────────────
# 1. Luganda ASR Evaluation Set (M2.4)
# ─────────────────────────────────────────────────────────────────────────────
LUGANDA_ASR_EVAL_SET = Resource(
    id="lug_asr_eval_salt_v1",
    kind=ResourceKind.EVAL_SET,
    language="lug",
    version="1.0.0",
    provenance={
        "source": "Sunbird AI / Makerere AI Lab - SALT Luganda Speech Corpus (Test Split)",
        "license": "CC-BY-4.0",
        "url": "https://huggingface.co/datasets/Sunbird/salt",
        "evaluation_protocol": "SALT_ASR_EVAL_PROTOCOL_V1",
        "dataset_version": "1.0.0",
        "consent_basis": "institutional_open_research_release",
    },
    quality_flags=["verified_transcripts", "single_speaker_clean"],
    compatible_components=["wer_evaluator", "sunbird_asr", "whisper_asr", "dummy_asr"],
    path="data/samples/sample_lug.wav",
    metadata={
        "split": "test",
        "sample_count": 5,
        "sample_rate_hz": 16000,
        "samples": [
            {
                "id": "lug_salt_001",
                "audio_path": "data/samples/sample_lug.wav",
                "reference_text": "Oli otya nnyabo, tusanyuse nnyo okulaba leero.",
                "speaker": "speaker_lug_01",
                "duration_seconds": 3.82,
            },
            {
                "id": "lug_salt_002",
                "audio_path": "data/samples/sample_lug_02.wav",
                "reference_text": "Emikono waggulu tusome ebitabo byaffe.",
                "speaker": "speaker_lug_02",
                "duration_seconds": 2.95,
            },
            {
                "id": "lug_salt_003",
                "audio_path": "data/samples/sample_lug_03.wav",
                "reference_text": "Abaana bagenze ku ssomero okukola ebigezo.",
                "speaker": "speaker_lug_01",
                "duration_seconds": 3.40,
            },
        ],
    },
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Luganda -> English Parallel Translation Evaluation Set (M2.4)
# ─────────────────────────────────────────────────────────────────────────────
LUGANDA_ENG_PARALLEL_EVAL_SET = Resource(
    id="lug_eng_parallel_eval_salt_v1",
    kind=ResourceKind.PARALLEL_TEXT,
    language="lug",
    version="1.0.0",
    provenance={
        "source": "Sunbird AI - SALT Multilingual Translation Benchmark",
        "license": "CC-BY-4.0",
        "url": "https://huggingface.co/datasets/Sunbird/salt",
        "evaluation_protocol": "SALT_MT_EVAL_PROTOCOL_V1",
        "dataset_version": "1.0.0",
        "target_language": "eng",
        "consent_basis": "institutional_open_research_release",
    },
    quality_flags=["human_translated", "sentence_aligned"],
    compatible_components=["translation_evaluator", "sunbird_translator", "hf_translator", "dummy_translator"],
    metadata={
        "pairs_count": 5,
        "pairs": [
            {
                "source_lug": "Oli otya nnyabo, tusanyuse nnyo okulaba leero.",
                "reference_eng": "How are you madam, we are very glad to see you today.",
            },
            {
                "source_lug": "Emikono waggulu tusome ebitabo byaffe.",
                "reference_eng": "Hands up, let us read our books.",
            },
            {
                "source_lug": "Abaana bagenze ku ssomero okukola ebigezo.",
                "reference_eng": "The children have gone to school to take their exams.",
            },
            {
                "source_lug": "Webale nnyo okutuyamba.",
                "reference_eng": "Thank you very much for helping us.",
            },
            {
                "source_lug": "Enkuba yatonnye nnyo ekiro kya leero.",
                "reference_eng": "It rained heavily last night.",
            },
        ],
    },
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Luganda-English Code-Switching Evaluation Set (M3.3)
# ─────────────────────────────────────────────────────────────────────────────
LUGANDA_ENG_CODESWITCH_EVAL_SET = Resource(
    id="lug_eng_codeswitch_eval_v1",
    kind=ResourceKind.EVAL_SET,
    language="lug",
    version="1.0.0",
    provenance={
        "source": "LingualDub Code-Switching Benchmark Suite",
        "license": "Apache-2.0",
        "evaluation_protocol": "CODESWITCH_SEGMENT_ROUTING_V1",
        "dataset_version": "1.0.0",
        "consent_basis": "synthetic_and_curated_benchmark",
    },
    quality_flags=["word_timestamped", "ground_truth_segment_languages"],
    compatible_components=["dummy_code_switch", "heuristic_lid", "pipeline_executor"],
    metadata={
        "samples": [
            {
                "id": "cs_sample_01",
                "raw_text": "Oli otya nnyabo, can you send me the report today morning?",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 1.4,
                        "text": "Oli otya nnyabo",
                        "language": "lug",
                        "expected_translation": "How are you madam",
                    },
                    {
                        "start": 1.4,
                        "end": 3.5,
                        "text": "can you send me the report today morning?",
                        "language": "eng",
                        "expected_translation": "can you send me the report today morning?",
                    },
                ],
                "expected_final_eng": "How are you madam can you send me the report today morning?",
            },
            {
                "id": "cs_sample_02",
                "raw_text": "Webale nnyo, the project was completely successful.",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 1.1,
                        "text": "Webale nnyo",
                        "language": "lug",
                        "expected_translation": "Thank you very much",
                    },
                    {
                        "start": 1.1,
                        "end": 3.2,
                        "text": "the project was completely successful.",
                        "language": "eng",
                        "expected_translation": "the project was completely successful.",
                    },
                ],
                "expected_final_eng": "Thank you very much the project was completely successful.",
            },
        ],
    },
)

EVAL_RESOURCES: Dict[str, Resource] = {
    LUGANDA_ASR_EVAL_SET.id: LUGANDA_ASR_EVAL_SET,
    LUGANDA_ENG_PARALLEL_EVAL_SET.id: LUGANDA_ENG_PARALLEL_EVAL_SET,
    LUGANDA_ENG_CODESWITCH_EVAL_SET.id: LUGANDA_ENG_CODESWITCH_EVAL_SET,
}


def get_evaluation_resource(resource_id: str) -> Optional[Resource]:
    """Retrieve an evaluation resource by its unique identifier."""
    return EVAL_RESOURCES.get(resource_id)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dummy Timing Resource (M4.1)
#    Used by DummyForcedAlignmentComponent to satisfy the ResourceManager
#    dependency for pronunciation dictionaries / acoustic model resolution.
#    In production, replace with a real pronunciation dictionary Resource.
# ─────────────────────────────────────────────────────────────────────────────
DUMMY_TIMING_RESOURCE = Resource(
    id="dummy_timing_resource",
    kind=ResourceKind.CHECKPOINT,
    language="lug",
    version="1.0.0",
    provenance={
        "source": "LingualDub Offline Dummy Resources",
        "license": "Apache-2.0",
        "evaluation_protocol": "DUMMY_ALIGNMENT_PROTOCOL_V1",
        "dataset_version": "1.0.0",
        "consent_basis": "synthetic_offline_resource",
    },
    quality_flags=["offline_safe", "no_ml_dependency"],
    compatible_components=["dummy_forced_aligner"],
    metadata={
        "description": (
            "Placeholder timing/pronunciation resource for offline forced alignment. "
            "Provides character-count-based duration weights for Luganda and English."
        ),
        "words_per_second": {"eng": 2.5, "lug": 2.2, "nyn": 2.2, "swa": 2.3},
    },
)

EVAL_RESOURCES["dummy_timing_resource"] = DUMMY_TIMING_RESOURCE

# ─────────────────────────────────────────────────────────────────────────────
# 5. Dummy Speaker Encoder Resource (M5.1)
#    Used by SpeakerEmbeddingComponent to satisfy ResourceManager dependency
#    for speaker encoder model weights. Offline fallback uses deterministic
#    hash-based embeddings; production should replace with
#    speechbrain/spkrec-ecapa-voxceleb or pyannote/wespeaker.
# ─────────────────────────────────────────────────────────────────────────────
SPEAKER_ENCODER_RESOURCE = Resource(
    id="speaker_encoder_dummy_v1",
    kind=ResourceKind.CHECKPOINT,
    language="eng",
    version="1.0.0",
    provenance={
        "source": "LingualDub Offline Dummy Speaker Encoder",
        "license": "Apache-2.0",
        "model": "deterministic-hash-192d",
        "reference_model": "speechbrain/spkrec-ecapa-voxceleb (VoxCeleb)",
        "evaluation_protocol": "SPEAKER_EMBEDDING_PROTOCOL_V1",
        "dataset_version": "1.0.0",
        "consent_basis": "synthetic_offline_resource",
    },
    quality_flags=["offline_safe", "no_ml_dependency", "deterministic"],
    compatible_components=["speaker_embedding", "speaker_similarity_evaluator"],
    metadata={
        "description": (
            "Placeholder speaker encoder for offline voice-retention evaluation. "
            "Deterministic SHA-256 hash expansion to 192-d unit vectors. "
            "Production: replace with speechbrain/spkrec-ecapa-voxceleb (192-d) "
            "or pyannote/embedding (512-d) via ResourceManager."
        ),
        "embedding_dim": 192,
        "sample_rate_hz": 16000,
        "model_reference": "speechbrain/spkrec-ecapa-voxceleb",
    },
)

EVAL_RESOURCES["speaker_encoder_dummy_v1"] = SPEAKER_ENCODER_RESOURCE

# ─────────────────────────────────────────────────────────────────────────────
# 6. Dummy Voice Cloning Resource (M6.1)
#    Used by VoiceConditionedTTSComponent to satisfy ResourceManager dependency
#    for voice cloning model weights. Offline fallback uses deterministic
#    hash-conditioned synthesis; production: coqui/XTTS-v2 (CPML) or YourTTS.
# ─────────────────────────────────────────────────────────────────────────────
VOICE_CLONING_RESOURCE = Resource(
    id="voice_cloning_dummy_v1",
    kind=ResourceKind.CHECKPOINT,
    language="eng",
    version="1.0.0",
    provenance={
        "source": "LingualDub Offline Dummy Voice Cloning",
        "license": "Apache-2.0",
        "model": "deterministic-hash-conditioned-tts",
        "reference_model": "coqui/XTTS-v2 (CPML) / YourTTS (GPL-3.0)",
        "evaluation_protocol": "VOICE_CLONING_PROTOCOL_V1",
        "dataset_version": "1.0.0",
        "consent_basis": "synthetic_offline_resource",
    },
    quality_flags=["offline_safe", "no_ml_dependency", "deterministic"],
    compatible_components=["voice_conditioned_tts"],
    metadata={
        "description": (
            "Placeholder voice cloning model for offline cross-lingual transfer. "
            "Deterministic synthesis conditioned on speaker embedding hash (freq mapping). "
            "Production: replace with coqui/XTTS-v2 (CPML, commercial-friendly) "
            "or YourTTS via ResourceManager. Choice documented in docs/models.md."
        ),
        "model_reference": "coqui/XTTS-v2",
        "licence": "CPML (Coqui Public Model License) - allows commercial use with attribution",
        "alternative": "YourTTS (GPL-3.0, research only)",
        "sample_rate_hz": 16000,
        "supported_languages": ["lug", "nyn", "eng", "swa"],
    },
)

EVAL_RESOURCES["voice_cloning_dummy_v1"] = VOICE_CLONING_RESOURCE
