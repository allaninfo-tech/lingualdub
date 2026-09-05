# Research Module: AV Sync (M7)

## Status
Implemented — M7 closed. See `docs/milestones.md` for acceptance criteria.

## Baseline
Naive audio-mux without re-timing: dubbed audio concatenated and muxed with
source video at original segment boundaries (no dialogue snapping). This
baseline typically yields mean AV offset >200ms and <60% within 100ms when
translation length differs from source.

## Method (M7.1-M7.3)
- **M7.1 AVSyncEvaluator**: Deterministic `|dubbed_end - source_end|*1000` ms
  with SyncNet neural path via ResourceManager (SyncNet/Chung et al. or
  AV-HuBERT). Groups by `source_segment_index` for SPLIT handling.
  Metrics: `mean_av_offset_ms`, `pct_within_100ms` (tolerance 100ms).
- **M7.2 DialogueTimingComponent**: Snaps `Segment.start/end` to nearest video
  cue (scene-cut hist diff via OpenCV, ffprobe fallback, provenance
  `video_cues`, subtitle cues) within 150ms. Preserves M4
  `duration_target` and `speaker`.
- **M7.3 VideoMergerComponent**: Merges dubbed WAVs + source video via
  ffmpeg (python/subprocess) with dummy MP4 fallback for offline CI. Output
  artifact carries provenance `video_merger`, `dubbed_video`, `source_video_ref`,
  `run_id`.

## Done When (M7)
- Luganda video → English dubbed video where mean AV offset ≤100ms
- Video artifact registered with full provenance
- `AVSyncEvaluator` tests pass (unit + E2E `tests/integration/test_m7_av_sync_e2e.py`)

## Evaluation
Run `pytest tests/integration/test_m7_av_sync_e2e.py -v` and
`lingualdub experiment run configs/av_sync_mock_pipeline.yaml --input-video data/samples/sample_lug.mp4 --output-dir experiments/av_sync_test`

## Notes
Depends on M4 temporal alignment. See `research/README.md` and
`docs/milestones.md#milestone-7` for dependency graph.
