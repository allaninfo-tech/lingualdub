# Voice-Retention Human Evaluation Protocol — Version 1.0.0

**Protocol ID:** `VOICE_RETENTION_MOS_V1`
**Version:** `1.0.0`
**Date:** 2026-09-05
**Status:** Active — All M5/M6 voice-retention evaluations must cite this version in provenance.

---

## 1. Purpose

Quantify how similar the dubbed voice sounds to the original speaker (speaker identity retention) via controlled human judgement. This complements automatic cosine similarity from speaker embeddings and is **mandatory** for any claim about voice preservation or cross-lingual voice transfer.

---

## 2. Evaluation Question (Exact Wording)

> **“How similar does the dubbed voice sound to the original speaker’s voice, ignoring language, content, and audio quality?”**

Raters must be instructed that:
- Language difference is expected (e.g. Luganda → English) and must not lower the score.
- They should focus only on vocal timbre, pitch, and speaking style as identity cues.

The question is presented verbatim in the rater interface, translated to the rater’s native language if needed, with back-translation verified.

---

## 3. Rating Scale (1–5 MOS)

| Score | Label | Description |
|---|---|---|
| 1 | Very Dissimilar | Clearly a different person |
| 2 | Somewhat Dissimilar | Noticeably different, but some shared traits |
| 3 | Moderately Similar | Could be the same person with some doubt |
| 4 | Very Similar | Strongly resembles the original speaker |
| 5 | Identical / Indistinguishable | Cannot distinguish from original speaker |

- Scale is discrete, integer only.
- Mid-point 3 = “moderately similar” — explicit anchor.
- Raters may not give half-points.
- Raters must confirm they heard both clips fully before scoring.

---

## 4. Minimum Rater Requirements

- **Minimum number of raters per clip:** 3 independent raters.
- **Minimum total raters per evaluation set:** 5 unique raters (to avoid single-rater bias).
- **Rater qualification:** Native or fluent listeners of both source and target languages preferred; otherwise, listeners must be screened for normal hearing and no prior exposure to the specific speakers in training.
- **Exclusion:** Raters who participated in training the voice-transfer model for that evaluation are excluded (blind).

---

## 5. Audio Presentation Format

- **Randomised:** Each rater receives clips in a uniquely shuffled order (seeded, logged).
- **Blind:** Raters are not told which system produced the dubbed audio (baseline vs candidate) nor the speaker identity labels. System identifiers are hidden.
- **Paired presentation:** Each trial presents the *reference* (original source audio, 2–5s) followed by 0.5s silence then the *test* (dubbed English audio, same utterance). Both clips are loudness-normalized to -23 LUFS.
- **Interface:** Web-based, headphones required, volume calibration tone at start.
- **Repetition:** Raters may replay the pair once (max 2 plays) before scoring.
- **Attention checks:** 2 gold trials per 20 clips where reference == test (expected score 5) and where reference vs clearly different speaker (expected score 1). Failure on both flags the rater’s batch for review.

---

## 6. Scoring Aggregation Method

For each system/version evaluated:

- **Mean Opinion Score (MOS):** arithmetic mean of all valid ratings for that system.
- **Standard deviation (SD):** sample SD across ratings.
- **Sample size (N):** total number of ratings (raters × clips).
- **95% Confidence Interval:** `mean ± 1.96 * SD / sqrt(N)`.
- **System-level MOS:** average of clip-level means (equal weight per clip).

Reported to two decimal places.

---

## 7. Inter-Rater Agreement Measure

- **Krippendorff’s Alpha (interval)** — computed across all raters and clips for the evaluation run.
- **Threshold:** α ≥ 0.40 required for publication; α < 0.40 triggers rater retraining or additional raters.
- Alternative (if <3 raters per clip): **Intraclass Correlation Coefficient ICC(2,k)** reported.

Both α/ICC and the contingency table must be archived with the run.

---

## 8. Reporting Format (Required Fields)

Every voice-retention evaluation run must emit a JSON record with:

```json
{
  "protocol": "VOICE_RETENTION_MOS_V1",
  "protocol_version": "1.0.0",
  "mean": 3.85,
  "std": 0.62,
  "n": 90,
  "ci95_low": 3.72,
  "ci95_high": 3.98,
  "alpha": 0.53,
  "dataset_version": "1.0.0",
  "system_version": "speaker_embedding@1.0.0 + mms_tts@1.0.0",
  "clips_evaluated": 30,
  "raters_count": 6,
  "timestamp": "2026-09-05T00:00:00Z",
  "run_id": "uuid"
}
```

Additionally, a CSV with columns `clip_id, rater_id, score, system, timestamp` must be stored as artifact.

---

## 9. Provenance Citation

All Results that include voice-retention scores must carry in `provenance`:

```json
{
  "evaluation_protocol": "VOICE_RETENTION_MOS_V1",
  "protocol_version": "1.0.0",
  "evaluator": "speaker_similarity_evaluator@1.0.0 / human_mos@1.0.0"
}
```

The automatic cosine similarity and the human MOS are complementary; both should be reported, not one in place of the other.

---

## 10. Versioning

- Any change to wording, scale, rater count, aggregation, or presentation requires a new protocol version (e.g. `VOICE_RETENTION_MOS_V2`) and a migration note.
- Previous results remain comparable only within the same protocol version; cross-version comparison must raise `ProvenanceMismatchError` in `compare_runs`.

---

*This document is versioned and cited in Result.provenance for every voice-retention evaluation.*
