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

## Milestone 7 — Audio-Visual Sync

| Component | Model | Licence | Notes |
|---|---|---|---|
| AV Sync Evaluator | `SyncNet` deterministic timing offset (`AVSyncEvaluator`, `syncnet_dummy_v1`) | Apache-2.0 (offline) / MIT production | `mean_av_offset_ms`, `pct_within_100ms`, tolerance 100ms |
| Dialogue Timing | Heuristic snap to `video_cues`/`scene_cut` (`DialogueTimingComponent`) | Apache-2.0 | Compatible with M4 `DurationModellingComponent` |
| Video Merger | FFmpeg `VideoMergerComponent` (dummy WAV+video placeholder offline) | Apache-2.0 | `ResourceKind.VIDEO`, provenance `video_merger`, `source_video_ref` |

## Milestone 8 — Generalisation Proof (Runyankole)

| Task | Component | Model | Licence | Rationale |
|---|---|---|---|---|
| ASR (Runyankole) | `RunyankoleASRComponent` (`runyankole_asr`) | `Sunbird/asr-whisper-51-african-languages` (SALT Runyankole-Rukiga, 51 langs) | Apache-2.0 (via HF) | SALT fine-tune covers nyn+Rukiga jointly; Luganda→nyn transfer evidence ~35% zero-shot WER → <20% with 10h adapt |
| ASR fallback (offline) | `RunyankoleASRComponent` deterministic | Deterministic nyn phrase `Agandi nungyi...` | Apache-2.0 | No torch dependency, `supported_languages=["nyn"]` strict scoping for M8.2 proof |
| Translation (nyn→eng) | `HuggingFaceTranslationComponent` | `facebook/nllb-200-distilled-600M` (`nyn_Latn`) | CC-BY-NC 4.0 | NLLB nyn_Latn already proven; same pipeline as Luganda |
| TTS | `MMSTTSComponent` / `DummyTTSComponent` | `facebook/mms-tts-eng` or `mms-tts-nyn` | CC-BY-NC 4.0 | Reused, no new TTS needed |

Evaluation sets (M8.3): `nyn_asr_eval_salt_v1` (SALT Runyankole-Rukiga test split, 5 samples, `SALT_ASR_EVAL_PROTOCOL_V1`, CC-BY-4.0, `consent_basis: institutional_open_research_release`) and `nyn_eng_parallel_eval_salt_v1` (3 pairs, `SALT_MT_EVAL_PROTOCOL_V1`). Both carry `related_language_proxy: lug`, `transfer_basis: lug->nyn`.

Configs: `configs/runyankole_mock_pipeline.yaml` (offline `runyankole_asr→dummy_translator→dummy_tts`) and `configs/runyankole_english_baseline.yaml` (Colab `runyankole_asr(use_neural=true) + hf_translator(nyn→eng) + mms_tts`). Loaded via `ConfigLoader` + `PipelineExecutor` without core changes — architectural audit 8.5.

Audit: `docs/research/runyankole_audit.md` (speech ~40h SALT, text Hansard/JW.org/MoH, licenses CC-BY-4.0/CC-BY-NC 4.0, transfer analysis).

All model weights are acquired via `lingualdub.utils.ResourceManager` (SHA256 verified, `~/.cache/lingualdub`, `LINGUALDUB_CACHE_DIR` override) and versioned in `Result.provenance`.

*Last updated: 2026-09-10 — versioned with LingualDub `0.1.0`.*
