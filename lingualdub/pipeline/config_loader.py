"""
Declarative pipeline configuration loader.

Loads and resolves Pipeline instances from YAML or JSON configuration files
via the Registry.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from lingualdub.core.component import Component, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.registry.registry import Registry

logger = logging.getLogger(__name__)


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Fallback simple YAML-like parser if PyYAML is not installed."""
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        # Fallback: try json
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Basic YAML parser for simple key-value structures
    result: Dict[str, Any] = {}
    current_list: Optional[str] = None
    current_item: Optional[Dict[str, Any]] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("- "):
            # List item
            if current_list:
                item_content = line[2:].strip()
                if ":" in item_content:
                    k, v = item_content.split(":", 1)
                    current_item = {k.strip(): _parse_val(v.strip())}
                    result.setdefault(current_list, []).append(current_item)
                else:
                    result.setdefault(current_list, []).append(_parse_val(item_content))
            continue

        if raw_line.startswith("    ") and current_item is not None:
            # Sub-property of current list item
            sub = line.strip()
            if ":" in sub:
                k, v = sub.split(":", 1)
                current_item[k.strip()] = _parse_val(v.strip())
            continue

        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if not v:
                current_list = k
                result[k] = []
                current_item = None
            else:
                current_list = None
                current_item = None
                result[k] = _parse_val(v)

    return result


def _parse_val(val: str) -> Any:
    val = val.strip().strip("'\"")
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() == "null" or val.lower() == "none":
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


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
        """
        source_lang = config.get("source_language", "lug")
        target_lang = config.get("target_language")
        per_segment = bool(config.get("per_segment_language", False))
        failure_mode_str = config.get("on_stage_failure", "abort").lower()
        failure_mode = FailureMode(failure_mode_str)
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
                instance = impl(**params) if params else impl()
            elif isinstance(impl, Component):
                instance = impl
            else:
                # Custom callable or object
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
            config = json.loads(content)
        else:
            config = _parse_simple_yaml(content)

        return self.load_dict(config)
