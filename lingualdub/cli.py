"""
Command Line Interface (CLI) for LingualDub.

Supports running experiments, listing registered components, evaluating results,
and comparing experiment runs.
"""

from __future__ import annotations
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import lingualdub as ld
from lingualdub.components.eval.metrics import WEREvaluator, TranslationEvaluator, TemporalAlignmentEvaluator
from lingualdub.pipeline.config_loader import ConfigLoader
from lingualdub.registry.manifest import ManifestScanner
from lingualdub.utils.comparison import compare_runs

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("lingualdub.cli")


def get_default_registry() -> ld.Registry:
    """Build and populate the default framework Registry."""
    registry = ld.Registry(conflict_policy=ld.ConflictPolicy.HIGHEST_VERSION)

    # Register built-in languages
    from lingualdub.languages.luganda import LUGANDA
    from lingualdub.languages.runyankole import RUNYANKOLE
    registry.register("language", "lug", LUGANDA, version="1.0.0")
    registry.register("language", "nyn", RUNYANKOLE, version="1.0.0")

    # Register built-in dummy/mock components
    from lingualdub.components.asr.dummy import DummyASRComponent
    from lingualdub.components.translation.dummy import DummyTranslationComponent
    from lingualdub.components.tts.dummy import DummyTTSComponent

    registry.register("component", "dummy_asr", DummyASRComponent, version="1.0.0")
    registry.register("component", "dummy_translator", DummyTranslationComponent, version="1.0.0")
    registry.register("component", "dummy_tts", DummyTTSComponent, version="1.0.0")

    # Register real adapters if available
    try:
        from lingualdub.components.asr.sunbird import SunbirdASRComponent
        registry.register("component", "sunbird_asr", SunbirdASRComponent, version="1.0.0")
    except Exception:
        pass

    try:
        from lingualdub.components.asr.whisper import WhisperASRComponent
        registry.register("component", "whisper_asr", WhisperASRComponent, version="1.0.0")
    except Exception:
        pass

    try:
        from lingualdub.components.translation.sunbird import SunbirdTranslationComponent
        registry.register("component", "sunbird_translator", SunbirdTranslationComponent, version="1.0.0")
    except Exception:
        pass

    try:
        from lingualdub.components.translation.hf_translator import HuggingFaceTranslationComponent
        registry.register("component", "hf_translator", HuggingFaceTranslationComponent, version="1.0.0")
    except Exception:
        pass

    try:
        from lingualdub.components.tts.mms_tts import MMSTTSComponent
        registry.register("component", "mms_tts", MMSTTSComponent, version="1.0.0")
    except Exception:
        pass

    # Register evaluators
    registry.register("component", "wer_evaluator", WEREvaluator, version="1.0.0")
    registry.register("component", "translation_evaluator", TranslationEvaluator, version="1.0.0")
    registry.register("component", "temporal_alignment_evaluator", TemporalAlignmentEvaluator, version="1.0.0")

    # Scan installed extension manifests
    scanner = ManifestScanner(registry)
    try:
        scanner.scan()
    except Exception as exc:
        logger.debug("Manifest scanning: %s", exc)

    return registry


def cmd_experiment_run(args: argparse.Namespace) -> int:
    """Run a pipeline experiment from a configuration file."""
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Configuration file not found: %s", config_path)
        return 1

    registry = get_default_registry()
    loader = ConfigLoader(registry)

    try:
        pipeline = loader.load_file(config_path)
    except Exception as exc:
        logger.error("Failed to load pipeline from %s: %s", config_path, exc)
        return 1

    logger.info("Loaded pipeline: %r (stages: %s)", pipeline.name or "unnamed", pipeline.stage_names)

    # Prepare input resource or text
    if args.input_audio:
        input_obj = ld.Resource(
            id="cli_audio_input",
            kind=ld.ResourceKind.SPEECH,
            language=pipeline.source_language,
            version="1.0.0",
            path=str(args.input_audio),
            provenance={"consent_basis": "user_provided"},
        )
    elif args.sample_text:
        input_obj = ld.Result(
            segments=[
                ld.Segment(
                    start=0.0,
                    end=3.0,
                    text=args.sample_text,
                    language=pipeline.source_language,
                )
            ],
            source_language=pipeline.source_language,
        )
    else:
        # Default placeholder
        input_obj = ld.Resource(
            id="default_sample",
            kind=ld.ResourceKind.SPEECH,
            language=pipeline.source_language,
            version="1.0.0",
            provenance={"source": "cli_default"},
        )

    executor = ld.PipelineExecutor(pipeline)
    try:
        result = executor.run(input_obj)
    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc)
        return 1

    logger.info("Pipeline completed with status: %s", result.status.value.upper())
    for s in result.segments:
        logger.info("  [%0.2fs -> %0.2fs] (%s): %s", s.start, s.end, s.language or "-", s.text)

    # Save output if output directory is provided
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        results_file = out_dir / "results.json"
        results_file.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        logger.info("Saved result JSON to: %s", results_file)

        # Write experiment summary README
        summary_file = out_dir / "README.md"
        summary_md = f"""# Experiment Run: {pipeline.name or 'Unnamed'}

- **Status**: `{result.status.value.upper()}`
- **Source Language**: `{pipeline.source_language}`
- **Target Language**: `{pipeline.target_language or 'N/A'}`
- **Stages**: `{' -> '.join(pipeline.stage_names)}`
- **Segments Count**: {len(result.segments)}
- **Artifacts**: {len(result.artifacts)}

## Segment Outputs
"""
        for s in result.segments:
            summary_md += f"- **[{s.start:.2f}s - {s.end:.2f}s]** ({s.language}): {s.text}\n"

        summary_file.write_text(summary_md, encoding="utf-8")
        logger.info("Saved experiment summary to: %s", summary_file)

    return 0


def cmd_registry_list(args: argparse.Namespace) -> int:
    """List registered framework items."""
    registry = get_default_registry()
    kinds = [args.kind] if args.kind else ["language", "component", "resource"]
    for kind in kinds:
        items = registry.list(kind)
        print(f"\n[{kind.upper()}S] ({len(items)} registered):")
        for key, ver in items:
            print(f"  - {key:<30} (v{ver})")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two experiment results."""
    try:
        res = compare_runs(args.baseline, args.candidate)
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        logger.error("Comparison failed: %s", exc)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lingualdub",
        description="LingualDub — Speech-AI Framework for Low-Resource Languages",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # lingualdub experiment run ...
    exp_parser = subparsers.add_parser("experiment", help="Experiment commands")
    exp_sub = exp_parser.add_subparsers(dest="exp_subcommand")
    run_parser = exp_sub.add_parser("run", help="Run a pipeline experiment from config")
    run_parser.add_argument("config", help="Path to pipeline configuration YAML/JSON")
    run_parser.add_argument("--input-audio", "-i", help="Path to input audio file")
    run_parser.add_argument("--sample-text", "-t", help="Sample text for direct text pipeline tests")
    run_parser.add_argument("--output-dir", "-o", help="Output directory to save results and artifacts")

    # lingualdub registry ...
    reg_parser = subparsers.add_parser("registry", help="Registry inspection")
    reg_sub = reg_parser.add_subparsers(dest="reg_subcommand")
    list_parser = reg_sub.add_parser("list", help="List registered components and languages")
    list_parser.add_argument("--kind", "-k", choices=["language", "component", "resource"], help="Filter by kind")

    # lingualdub compare ...
    cmp_parser = subparsers.add_parser("compare", help="Compare two experiment results")
    cmp_parser.add_argument("--baseline", "-b", required=True, help="Path to baseline results.json")
    cmp_parser.add_argument("--candidate", "-c", required=True, help="Path to candidate results.json")

    args = parser.parse_args(argv)
    if args.subcommand == "experiment" and args.exp_subcommand == "run":
        return cmd_experiment_run(args)
    elif args.subcommand == "registry" and args.reg_subcommand == "list":
        return cmd_registry_list(args)
    elif args.subcommand == "compare":
        return cmd_compare(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
