"""Tests for lingualdub.registry.manifest."""

import json
import pytest
from pathlib import Path

from lingualdub.registry.registry import Registry
from lingualdub.registry.manifest import ManifestScanner, ManifestError, MANIFEST_FILENAME


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / MANIFEST_FILENAME
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


VALID_MANIFEST = {
    "name": "test-extension",
    "version": "1.0.0",
    "entries": [
        {
            "kind": "component",
            "key": "pathlib_path",
            "module": "pathlib",
            "attr": "Path",
            "version": "1.0.0",
            "metadata": {"task": "asr"},
        }
    ],
}


def test_load_valid_manifest(tmp_path):
    manifest_path = _write_manifest(tmp_path, VALID_MANIFEST)
    registry = Registry()
    scanner = ManifestScanner(registry)
    count = scanner.load(manifest_path)
    assert count == 1
    resolved = registry.resolve("component", "pathlib_path")
    assert resolved is Path


def test_load_registers_all_entries(tmp_path):
    data = {
        "name": "multi",
        "version": "1.0.0",
        "entries": [
            {"kind": "component", "key": "a", "module": "pathlib", "attr": "Path", "version": "1.0.0"},
            {"kind": "language", "key": "b", "module": "pathlib", "attr": "PurePath", "version": "2.0.0"},
        ],
    }
    manifest_path = _write_manifest(tmp_path, data)
    registry = Registry()
    scanner = ManifestScanner(registry)
    count = scanner.load(manifest_path)
    assert count == 2
    assert registry.resolve("component", "a") is Path
    assert registry.resolve("language", "b") is not None


def test_load_invalid_json_raises(tmp_path):
    p = tmp_path / MANIFEST_FILENAME
    p.write_text("{ not valid json }", encoding="utf-8")
    scanner = ManifestScanner(Registry())
    with pytest.raises(ManifestError, match="not valid JSON"):
        scanner.load(p)


def test_load_missing_entries_key_raises(tmp_path):
    p = _write_manifest(tmp_path, {"name": "bad", "version": "1.0.0"})
    scanner = ManifestScanner(Registry())
    with pytest.raises(ManifestError, match="missing required top-level key 'entries'"):
        scanner.load(p)


def test_load_entry_missing_field_raises(tmp_path):
    data = {
        "name": "bad",
        "version": "1.0.0",
        "entries": [{"kind": "component", "key": "x"}],  # missing module, attr, version
    }
    p = _write_manifest(tmp_path, data)
    scanner = ManifestScanner(Registry())
    with pytest.raises(ManifestError, match="missing required fields"):
        scanner.load(p)


def test_load_bad_module_raises(tmp_path):
    data = {
        "name": "bad",
        "version": "1.0.0",
        "entries": [
            {"kind": "component", "key": "x", "module": "nonexistent_module_xyz",
             "attr": "Foo", "version": "1.0.0"}
        ],
    }
    p = _write_manifest(tmp_path, data)
    scanner = ManifestScanner(Registry())
    with pytest.raises(ManifestError, match="cannot import"):
        scanner.load(p)


def test_load_bad_attr_raises(tmp_path):
    data = {
        "name": "bad",
        "version": "1.0.0",
        "entries": [
            {"kind": "component", "key": "x", "module": "pathlib",
             "attr": "NonExistentClass", "version": "1.0.0"}
        ],
    }
    p = _write_manifest(tmp_path, data)
    scanner = ManifestScanner(Registry())
    with pytest.raises(ManifestError, match="no attribute"):
        scanner.load(p)


def test_scan_discovers_manifest(tmp_path):
    _write_manifest(tmp_path, VALID_MANIFEST)
    registry = Registry()
    scanner = ManifestScanner(registry)
    count = scanner.scan(search_paths=[tmp_path])
    assert count == 1
    assert registry.resolve("component", "pathlib_path") is Path


def test_scan_skips_malformed_manifest(tmp_path):
    p = tmp_path / MANIFEST_FILENAME
    p.write_text("not json", encoding="utf-8")
    registry = Registry()
    scanner = ManifestScanner(registry)
    # Should not raise — malformed manifests are logged and skipped
    count = scanner.scan(search_paths=[tmp_path])
    assert count == 0


def test_scan_empty_directory(tmp_path):
    registry = Registry()
    scanner = ManifestScanner(registry)
    count = scanner.scan(search_paths=[tmp_path])
    assert count == 0


def test_scan_discovers_with_empty_string_in_sys_path(monkeypatch, tmp_path):
    """Ensure scanner finds manifests in current directory when sys.path has ''."""
    _write_manifest(tmp_path, VALID_MANIFEST)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.path", ["", "/nonexistent/dir"])
    registry = Registry()
    scanner = ManifestScanner(registry)
    count = scanner.scan()
    assert count == 1
    assert registry.resolve("component", "pathlib_path") is Path

