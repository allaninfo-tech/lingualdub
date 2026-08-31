# LingualDub Experiment Logs & Results

This directory contains versioned, reproducible experiment records executed across local environments, Google Colab, or remote GPU clusters.

## The Rule of Separation

- **Code & Configs (`GitHub`)**: Stored here under version control.
- **Model Checkpoints & Heavy Audio**: Stored on Hugging Face Hub or cloud caches; **never** committed to Git.
- **Results & Evaluation Envelopes (`results.json`, `README.md`)**: Committed back to GitHub so runs can be tracked, inspected, and compared locally using `lingualdub compare`.

## Experiment Directory Structure

```text
experiments/
└── <task_or_language>/
    └── <run_name>/
        ├── config.yaml      # Exact pipeline configuration used
        ├── results.json     # Structured Result envelope (segments, metrics, provenance)
        └── README.md        # Human-readable run summary with WER / chrF scores
```

## Comparing Two Runs

To compute metric deltas between two runs:

```bash
python -m lingualdub.cli compare \
  --baseline experiments/luganda_dubbing/baseline_v1/results.json \
  --candidate experiments/luganda_dubbing/run_v2/results.json
```
