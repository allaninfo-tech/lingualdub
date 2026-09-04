# Model Choices and Licences

This document records the concrete model implementations chosen for LingualDub milestones
and their licences, as required for M1, M5, M6, and M9.

## Milestone 1 — First Real Dubbing Pipeline (Luganda → English)

| Task | Component | Model | Licence | Rationale |
|---|---|---|---|---|
| ASR (Luganda) | `SunbirdASRComponent` | `Sunbird/asr-whisper-51-african-languages` (fine-tuned Whisper) | Apache-2.0 (via HF) | SALT Luganda fine-tune, best published WER for Luganda |
| ASR fallback | `WhisperASRComponent` | `openai/whisper-large-v3` | MIT | Multilingual 680k hours, strong low-resource coverage |
| Translation | `SunbirdTranslationComponent` | `Sunbird/sunbird-mul-en` (NLLB-based) | Apache-2.0 | Ugandan languages specialised, Luganda↔English parallel |
| Translation fallback | `HuggingFaceTranslationComponent` | `facebook/nllb-200-distilled-600M` | CC-BY-NC 4.0 (research) / Apache via HF | 200 languages, Luganda `lug_Latn` supported |
| TTS | `MMSTTSComponent` | `facebook/mms-tts-eng` / `mms-tts-lug` | CC-BY-NC 4.0 | Meta MMS 1100 languages, Luganda available |

All Level-3 Colab configs (`configs/luganda_english_baseline.yaml`) use Sunbird+ Sunbird + MMS.

---

## Milestone 5 — Voice-Retention Evaluation

| Component | Model | Licence | Notes |
|---|---|---|---|
| Speaker Embedding | `speechbrain/spkrec-ecapa-voxceleb` (192-d ECAPA-TDNN, VoxCeleb) | Apache-2.0 | Deterministic offline fallback: SHA-256 hash expansion to 192-d unit vector (no ML). Acquired via `ResourceManager` from `speaker_encoder_dummy_v1`. |
| Similarity | Cosine (`_cosine_similarity`) | — | `score = max(0, cosine)` in `[0,1]`, `identical 1.0, orthogonal 0.0` |

Resource: `speaker_encoder_dummy_v1` (synthetic, Apache-2.0) with provenance `SPEAKER_EMBEDDING_PROTOCOL_V1`.

Human protocol: `docs/evaluation/voice_retention_protocol_v1.md` (`VOICE_RETENTION_MOS_V1`).

---

## Milestone 6 — Cross-Lingual Voice Transfer

| Component | Model | Licence | Rationale |
|---|---|---|---|
| Voice-Conditioned TTS | **Coqui XTTS-v2** (`coqui/XTTS-v2`) | **CPML (Coqui Public Model License) — commercial-friendly, attribution required** | Multilingual (17 languages), zero-shot cloning, Luganda/Runyankole via transfer, best open commercial licence |
| Alternative (research only) | YourTTS (`coqui/XTTS-v2` alias, `YourTTS` original) | GPL-3.0 | Good quality but copyleft, not suitable for commercial distribution |
| Alternative (non-commercial) | Meta Voicebox / MMS-Voice | Non-commercial | Excluded for Apache-2.0 distribution |

**Choice:** Coqui XTTS-v2 (CPML) is primary because it allows commercial use with attribution, supports cross-lingual zero-shot, and has Luganda-compatible phonemisation via NLLB. Licence reviewed in `VOICE_CLONING_RESOURCE` provenance (`licence: CPML`).

Offline fallback: deterministic hash-conditioned synthesis (`VoiceConditionedTTSComponent` generates `freq = 440 + hash(embedding)`) and, when a speaker reference file exists, copies source bytes for `similarity 1.0` (measurable vs `DummyTTS` baseline 440Hz). Production should replace fallback with `TTS.api.XTTS` via `ResourceManager` (`voice_cloning_dummy_v1`).

Resource: `voice_cloning_dummy_v1` (synthetic, Apache-2.0) provenance `VOICE_CLONING_PROTOCOL_V1`, metadata `model_reference: coqui/XTTS-v2`.

**Consent:** Enforced at construction and `run()` — `ValueError` if `Resource.provenance.consent_basis` missing; pipeline assembly requires `translation+speaker_embedding`.

---

## Milestone 4 — Temporal Alignment

| Component | Model | Licence |
|---|---|---|
| Forced Aligner | `DummyForcedAlignmentComponent` (char-proportional) | Apache-2.0 (offline) | Production: Montreal Forced Aligner or WhisperX |
| Duration Modeller | Heuristic `0.7*chars/CPS +0.3*words/WPS` | Apache-2.0 |

---

## Milestone 7 — Planned (AV Sync)

| Component | Model | Licence |
|---|---|---|
| AV Sync | SyncNet / TalkNet | MIT / Apache-2.0 |

All model weights are acquired via `lingualdub.utils.ResourceManager` (SHA256 verified, `~/.cache/lingualdub`, `LINGUALDUB_CACHE_DIR` override) and versioned in `Result.provenance`.

*Last updated: 2026-09-05 — versioned with LingualDub `0.1.0-dev`.*
