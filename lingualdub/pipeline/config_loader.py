"""
Declarative pipeline configuration loader.

Loads and resolves Pipeline instances from YAML or JSON configuration files
via the Registry.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from lingualdub.core.component import Component, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.registry.registry import Registry

logger = logging.getLogger(__name__)


def _parse_yaml(text: str, filepath: Path) -> Dict[str, Any]:
    """Parse YAML content, requiring PyYAML for non-JSON files."""
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Configuration file {filepath} must contain a top-level mapping, got {type(data).__name__}."
            )
        return data
    except ImportError as exc:
        raise ImportError(
            f"PyYAML is required to load YAML config {filepath}. Install with `pip install pyyaml` "
            f"or `pip install lingualdub[dev]`. (Original error: {exc})"
        ) from exc
    except Exception as exc:
        # yaml.YAMLError or ValueError from above
        raise ValueError(f"Failed to parse YAML configuration {filepath}: {exc}") from exc


class ConfigLoader:
    """
    Loads declarative pipeline configurations and instantiates Pipeline objects.
    """

    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def load_dict(self, config: Dict[str, Any]) -> Pipeline:
        """
        Instantiate a Pipeline from a configuration dictionary.

        Args:
            config: Pipeline configuration dictionary.

        Returns:
            Assembled and compatibility-checked Pipeline object.

        Raises:
            ValueError: If config is malformed or stage definitions are invalid.
            TypeError: If resolved objects are not Components.
        """
        if not isinstance(config, dict):
            raise ValueError(f"Pipeline configuration must be a mapping, got {type(config).__name__}.")
        source_lang = config.get("source_language", "lug")
        if not isinstance(source_lang, str) or not source_lang:
            raise ValueError("Pipeline configuration 'source_language' must be a non-empty string.")
        target_lang = config.get("target_language")
        per_segment = bool(config.get("per_segment_language", False))
        failure_mode_str = str(config.get("on_stage_failure", "abort")).lower()
        try:
            failure_mode = FailureMode(failure_mode_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid on_stage_failure {failure_mode_str!r}: must be one of {[e.value for e in FailureMode]}."
            ) from exc
        name = config.get("name")
        description = config.get("description")
        metadata = config.get("metadata", {})

        stages_config = config.get("stages", [])
        if not stages_config:
            raise ValueError("Pipeline configuration must define at least one stage in 'stages'.")

        resolved_stages: List[Component] = []
        for i, stage_def in enumerate(stages_config):
            if isinstance(stage_def, str):
                # Simple component key
                kind = "component"
                key = stage_def
                version = None
                params: Dict[str, Any] = {}
            elif isinstance(stage_def, dict):
                kind = stage_def.get("kind", "component")
                key = stage_def.get("key") or stage_def.get("name")
                if not key:
                    raise ValueError(f"Stage #{i} in config must specify 'key' or 'name'.")
                version = stage_def.get("version")
                params = stage_def.get("params", {})
            else:
                raise ValueError(f"Invalid stage definition #{i}: {stage_def!r}")

            impl = self.registry.resolve(kind, key, version=version)
            if isinstance(impl, type):
                # Instantiable class
                try:
                    instance = impl(**params) if params else impl()
                except TypeError as exc:
                    raise TypeError(
                        f"Failed to instantiate component ({kind!r}, {key!r}) with params {params!r}: {exc}"
                    ) from exc
            elif isinstance(impl, Component):
                if params:
                    logger.warning(
                        "Stage #%d (%s/%s) resolved to an instance but params %r were supplied and will be ignored.",
                        i,
                        kind,
                        key,
                        params,
                    )
                instance = impl
            else:
                # Custom callable or object — try calling if params supplied
                if params and callable(impl):
                    try:
                        instance = impl(**params)  # type: ignore[operator]
                    except Exception as exc:
                        raise TypeError(
                            f"Resolved object for ({kind!r}, {key!r}) with params {params!r} failed: {exc}"
                        ) from exc
                else:
                    instance = impl

            if not isinstance(instance, Component):
                raise TypeError(
                    f"Resolved object for ({kind!r}, {key!r}) is {type(instance).__name__}, "
                    f"must be a Component instance."
                )

            resolved_stages.append(instance)

        pipeline = Pipeline(
            stages=resolved_stages,
            source_language=source_lang,
            target_language=target_lang,
            per_segment_language=per_segment,
            on_stage_failure=failure_mode,
            name=name,
            description=description,
            metadata=metadata,
        )
        return pipeline

    def load_file(self, path: Union[str, Path]) -> Pipeline:
        """
        Load and instantiate a Pipeline from a YAML or JSON file.

        Args:
            path: Path to the configuration file.

        Returns:
            Assembled Pipeline object.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        content = filepath.read_text(encoding="utf-8")
        if filepath.suffix.lower() == ".json":
            try:
                config = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Failed to parse JSON configuration {filepath}: {exc}") from exc
        elif filepath.suffix.lower() in (".yaml", ".yml"):
            config = _parse_yaml(content, filepath)
        else:
            # Try YAML first, fallback to JSON for extension-less files
            try:
                config = _parse_yaml(content, filepath)
            except Exception:
                try:
                    config = json.loads(content)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Configuration file {filepath} is not valid YAML or JSON: {exc}"
                    ) from exc

        return self.load_dict(config)
