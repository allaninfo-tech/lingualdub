# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-10

### Added
- **M0 — Core Foundation**: `Language`, `Resource`, `Component`, `Pipeline`, `Result`, and `Segment` domain abstractions with JSON serialization, `ResourceManager` caching with SHA256 integrity, `Registry` with conflict policies, and `ManifestScanner` extension discovery.
- **M1 — First Real Pipeline**: Luganda $\to$ English baseline with Sunbird ASR/MT, OpenAI Whisper, and Meta MMS-TTS adapters, plus offline dummy adapters.
- **M2 — Evaluation Infrastructure**: `WEREvaluator`, `TranslationEvaluator` (BLEU & chrF), dataset resources, and reproducible `compare_runs` utility.
- **M3 — Code-Switching**: Heuristic LID, word-level timestamp segmentation, and automatic per-segment language routing in `PipelineExecutor`.
- **M4 — Temporal Alignment**: Forced alignment (`DummyForcedAlignmentComponent`), duration modelling, and speech-rate control (`FittingStrategy`).
- **M5 — Voice Retention Evaluation**: `SpeakerEmbeddingComponent`, `SpeakerSimilarityEvaluator` (cosine similarity), and mandatory consent verification (`ensure_consent`).
- **M6 — Cross-Lingual Voice Transfer**: `VoiceConditionedTTSComponent` conditioned on speaker reference with consent enforcement.
- **M7 — Audio-Visual Synchronisation**: `AVSyncEvaluator`, `DialogueTimingComponent`, and `VideoMergerComponent` with `.mp4` artifact creation.
- **M8 — Generalisation Proof**: Complete Runyankole (`nyn`) speech-to-speech transfer proof with zero framework core modifications.
- **M9 — Stable v0.1.0 Release**: Standardized Apache 2.0 licensing, PyPI publishing pipeline, updated documentation site, and complete contributor guide.

## [0.1.0-dev] - 2026-08-31
- Initial public repository structure and framework skeleton.

