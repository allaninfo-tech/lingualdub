# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Declarative pipeline configuration loader.

Loads and resolves Pipeline instances from YAML or JSON configuration files
via the Registry.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from lingualdub.core.component import FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.protocols import ComponentProtocol
from lingualdub.registry.registry import Registry

logger = logging.getLogger(__name__)


def _parse_yaml(text: str, filepath: Path) -> dict[str, Any]:
    """Parse YAML content, requiring PyYAML for non-JSON files."""
    from lingualdub.exceptions import ConfigurationValidationError

    if not text.strip():
        raise ConfigurationValidationError(
            f"Configuration file {filepath} is empty.", field="config"
        )
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        if data is None:
            raise ConfigurationValidationError(
                f"Configuration file {filepath} contains empty YAML.", field="config"
            )
        if not isinstance(data, dict):
            raise ConfigurationValidationError(
                f"Configuration file {filepath} must contain a top-level mapping, got {type(data).__name__}.",
                field="config",
            )
        return data
    except ImportError as exc:
        raise ImportError(
            f"PyYAML is required to load YAML config {filepath}. Install with `pip install pyyaml` "
            f"or `pip install lingualdub[dev]`. (Original error: {exc})"
        ) from exc
    except ConfigurationValidationError:
        raise
    except Exception as exc:
        # yaml.YAMLError
        raise ConfigurationValidationError(
            f"Failed to parse YAML configuration {filepath}: {exc}", field="config"
        ) from exc


class ConfigLoader:
    """
    Loads declarative pipeline configurations and instantiates Pipeline objects.
    """

    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def load_dict(self, config: dict[str, Any]) -> Pipeline:
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
        from lingualdub.exceptions import ConfigurationValidationError

        if not isinstance(config, dict):
            raise ConfigurationValidationError(
                f"Pipeline configuration must be a mapping, got {type(config).__name__}.",
                field="config",
            )
        source_lang = config.get("source_language", "lug")
        if not isinstance(source_lang, str) or not source_lang:
            raise ConfigurationValidationError(
                "Pipeline configuration 'source_language' must be a non-empty string.",
                field="source_language",
            )
        target_lang = config.get("target_language")
        if target_lang is not None and not isinstance(target_lang, str):
            raise ConfigurationValidationError(
                "Pipeline configuration 'target_language' must be a string or null.",
                field="target_language",
            )
        if "per_segment_language" in config and not isinstance(
            config["per_segment_language"], bool
        ):
            raise ConfigurationValidationError(
                f"Field 'per_segment_language' must be a bool, got {type(config['per_segment_language']).__name__}: {config['per_segment_language']!r}.",
                field="per_segment_language",
            )
        per_segment = bool(config.get("per_segment_language", False))
        if (
            "on_stage_failure" in config
            and config["on_stage_failure"] is not None
            and not isinstance(config["on_stage_failure"], str)
        ):
            raise ConfigurationValidationError(
                f"Field 'on_stage_failure' must be a string, got {type(config['on_stage_failure']).__name__}: {config['on_stage_failure']!r}.",
                field="on_stage_failure",
            )
        failure_mode_str = str(config.get("on_stage_failure", "abort")).lower()
        try:
            failure_mode = FailureMode(failure_mode_str)
        except ValueError as exc:
            raise ConfigurationValidationError(
                f"Invalid on_stage_failure {failure_mode_str!r}: must be one of {[e.value for e in FailureMode]}.",
                field="on_stage_failure",
            ) from exc
        name = config.get("name")
        if name is not None and not isinstance(name, str):
            raise ConfigurationValidationError(
                "Pipeline configuration 'name' must be a string or null.", field="name"
            )
        description = config.get("description")
        if description is not None and not isinstance(description, str):
            raise ConfigurationValidationError(
                "Pipeline configuration 'description' must be a string or null.",
                field="description",
            )
        metadata = config.get("metadata", {})
        if metadata is not None and not isinstance(metadata, dict):
            raise ConfigurationValidationError(
                f"Field 'metadata' must be a dict, got {type(metadata).__name__}: {metadata!r}.",
                field="metadata",
            )
        metadata = metadata or {}

        stages_config = config.get("stages", [])
        if not isinstance(stages_config, list):
            raise ConfigurationValidationError(
                f"Field 'stages' must be a list, got {type(stages_config).__name__}: {stages_config!r}.",
                field="stages",
            )
        if not stages_config:
            raise ConfigurationValidationError(
                "Pipeline configuration must define at least one stage in 'stages'.",
                field="stages",
            )

        resolved_stages: list[ComponentProtocol] = []
        for i, stage_def in enumerate(stages_config):
            key: str
            if isinstance(stage_def, str):
                # Simple component key
                kind = "component"
                key = stage_def
                version = None
                params: dict[str, Any] = {}
            elif isinstance(stage_def, dict):
                raw_kind = stage_def.get("kind", "component")
                if not isinstance(raw_kind, str) or not raw_kind.strip():
                    raise ConfigurationValidationError(
                        f"Stage #{i} 'kind' must be a non-empty string, got {raw_kind!r}.",
                        field=f"stages[{i}].kind",
                    )
                kind = raw_kind.strip()
                raw_key = stage_def.get("key") or stage_def.get("name")
                if not raw_key or not isinstance(raw_key, str):
                    from lingualdub.exceptions import ConfigurationValidationError

                    raise ConfigurationValidationError(
                        f"Stage #{i} in config must specify 'key' or 'name' as a string.",
                        field=f"stages[{i}].key",
                    )
                key = raw_key
                version = stage_def.get("version")
                if version is not None and not isinstance(version, str):
                    raise ConfigurationValidationError(
                        f"Stage #{i} 'version' must be a string or None, got {type(version).__name__}: {version!r}.",
                        field=f"stages[{i}].version",
                    )
                params = stage_def.get("params", {})
                if not isinstance(params, dict):
                    raise ConfigurationValidationError(
                        f"Stage #{i} 'params' must be a dict, got {type(params).__name__}: {params!r}.",
                        field=f"stages[{i}].params",
                    )
            else:
                from lingualdub.exceptions import ConfigurationValidationError

                raise ConfigurationValidationError(
                    f"Invalid stage definition #{i}: {stage_def!r}",
                    field=f"stages[{i}]",
                )

            try:
                impl = self.registry.resolve(kind, key, version=version)
            except Exception as exc:
                from lingualdub.exceptions import ConfigurationValidationError, RegistryError

                if isinstance(exc, RegistryError):
                    raise ConfigurationValidationError(
                        f"Stage #{i} resolve failed for ({kind!r}, {key!r}, version={version!r}): {exc}",
                        field=f"stages[{i}]",
                    ) from exc
                raise
            if isinstance(impl, type):
                # Instantiable class
                try:
                    instance = impl(**params) if params else impl()
                except TypeError as exc:
                    from lingualdub.exceptions import ComponentContractError

                    raise ComponentContractError(
                        f"Failed to instantiate component ({kind!r}, {key!r}) with params {params!r}: {exc}",
                        component=key,
                    ) from exc
            elif isinstance(impl, ComponentProtocol):
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
                        from lingualdub.exceptions import ComponentContractError

                        raise ComponentContractError(
                            f"Resolved object for ({kind!r}, {key!r}) with params {params!r} failed: {exc}",
                            component=key,
                        ) from exc
                else:
                    instance = impl

            if not isinstance(instance, ComponentProtocol):
                from lingualdub.exceptions import ComponentContractError

                raise ComponentContractError(
                    f"Resolved object for ({kind!r}, {key!r}) is {type(instance).__name__}, "
                    f"must be a Component instance.",
                    component=key,
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

    def load_file(self, path: str | Path) -> Pipeline:
        """
        Load and instantiate a Pipeline from a YAML or JSON file.

        Args:
            path: Path to the configuration file.

        Returns:
            Assembled Pipeline object.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(  # justified: built-in file error
                f"Configuration file not found: {filepath}"
            )  # justified: standard library file not found — caller expects built-in

        content = filepath.read_text(encoding="utf-8")
        if filepath.suffixes and filepath.suffixes[-1].lower() == ".json":
            try:
                config = json.loads(content)
            except json.JSONDecodeError as exc:
                from lingualdub.exceptions import ConfigurationValidationError

                raise ConfigurationValidationError(
                    f"Failed to parse JSON configuration {filepath}: {exc}", field="config"
                ) from exc
        elif filepath.suffixes and filepath.suffixes[-1].lower() in (".yaml", ".yml"):
            config = _parse_yaml(content, filepath)
        elif not filepath.suffix:
            # Extension-less: try YAML, fallback to JSON
            try:
                config = _parse_yaml(content, filepath)
            except Exception as yaml_exc:
                # Don't mask ImportError (missing yaml dependency)
                if isinstance(yaml_exc, ImportError):
                    raise
                try:
                    config = json.loads(content)
                except json.JSONDecodeError as exc:
                    from lingualdub.exceptions import ConfigurationValidationError

                    raise ConfigurationValidationError(
                        f"Configuration file {filepath} is not valid YAML or JSON: {exc}",
                        field="config",
                    ) from exc
        else:
            raise ConfigurationValidationError(
                f"Unsupported config extension {filepath.suffix!r} for {filepath}. Use .yaml/.yml/.json",
                field="config",
            )

        return self.load_dict(config)
