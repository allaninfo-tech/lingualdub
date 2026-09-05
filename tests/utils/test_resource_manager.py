"""Tests for lingualdub.utils.resource_manager."""

import hashlib
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from lingualdub.utils.resource_manager import (
    ResourceManager,
    ChecksumError,
    ResourceNotFoundError,
)


def _sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_cache_hit_skips_download(tmp_path):
    content = b"fake model weights"
    checksum = _sha256_of(content)
    manager = ResourceManager(cache_dir=tmp_path)

    # Pre-create the cached file
    cached = tmp_path / "my_model" / "1.0.0" / "model.bin"
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(content)

    with patch("urllib.request.urlretrieve") as mock_dl:
        result = manager.get("my_model", "1.0.0", "http://example.com/model.bin", checksum)
        mock_dl.assert_not_called()

    assert result == cached


def test_downloads_on_miss(tmp_path):
    content = b"downloaded weights"
    checksum = _sha256_of(content)
    manager = ResourceManager(cache_dir=tmp_path)

    def fake_urlopen(req, timeout=30):
        # req may be Request or str
        mock_resp = MagicMock()
        mock_resp.read = MagicMock(side_effect=[content, b""])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = manager.get("my_model", "1.0.0", "http://example.com/model.bin", checksum)

    assert result.exists()
    assert result.read_bytes() == content


def test_checksum_mismatch_raises(tmp_path):
    content = b"correct content"
    wrong_checksum = _sha256_of(b"wrong content")
    manager = ResourceManager(cache_dir=tmp_path)

    cached = tmp_path / "my_model" / "1.0.0" / "model.bin"
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(content)

    with pytest.raises(ChecksumError, match="Checksum mismatch"):
        manager.get("my_model", "1.0.0", "http://example.com/model.bin", wrong_checksum)


def test_env_var_overrides_cache_dir(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom_cache"
    monkeypatch.setenv("LINGUALDUB_CACHE_DIR", str(custom_dir))
    manager = ResourceManager()
    assert manager.cache_dir == custom_dir


def test_cache_path_helper(tmp_path):
    manager = ResourceManager(cache_dir=tmp_path)
    path = manager.cache_path("my_model", "1.0.0", "model.bin")
    assert path == tmp_path / "my_model" / "1.0.0" / "model.bin"


def test_download_failure_raises_resource_not_found(tmp_path):
    manager = ResourceManager(cache_dir=tmp_path)

    with patch("urllib.request.urlopen", side_effect=OSError("network error")):
        with pytest.raises(ResourceNotFoundError, match="Could not download"):
            manager.get("my_model", "1.0.0", "http://example.com/model.bin", "abc123")
