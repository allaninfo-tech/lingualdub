"""
ResourceManager — download, cache, and verify resources.

Provides a standard mechanism for components to acquire model weights
and data files. All downloads are cached locally and verified with
SHA256 checksums. A cache hit (file exists and checksum matches) skips
the download entirely.
"""

from __future__ import annotations
import hashlib
import os
import urllib.request
from pathlib import Path
from typing import Optional


DEFAULT_CACHE_DIR = Path.home() / ".cache" / "lingualdub"
ENV_CACHE_DIR = "LINGUALDUB_CACHE_DIR"


class ChecksumError(Exception):
    """Raised when a downloaded or cached file does not match its expected SHA256 checksum."""


class ResourceNotFoundError(Exception):
    """Raised when a required resource is not available locally and cannot be downloaded."""


class ResourceManager:
    """
    Downloads, caches, and verifies resource files for LingualDub components.

    The cache directory defaults to ~/.cache/lingualdub/ and can be overridden
    by setting the LINGUALDUB_CACHE_DIR environment variable.

    Usage:
        manager = ResourceManager()
        path = manager.get(
            resource_id="whisper-small",
            version="1.0.0",
            url="https://example.com/model.bin",
            checksum="abc123...",
        )
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        env_dir = os.environ.get(ENV_CACHE_DIR)
        self.cache_dir: Path = Path(env_dir) if env_dir else (cache_dir or DEFAULT_CACHE_DIR)

    def get(
        self,
        resource_id: str,
        version: str,
        url: str,
        checksum: str,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Return the local path to a cached resource, downloading if needed.

        Args:
            resource_id: Unique identifier for this resource.
            version: Version string used for cache namespacing.
            url: URL to download from if not already cached.
            checksum: Expected SHA256 hex digest of the file.
            filename: Local filename to save as. Defaults to the last URL path segment.

        Returns:
            Path to the verified local file.

        Raises:
            ChecksumError: If the file fails checksum verification.
            ResourceNotFoundError: If the file cannot be downloaded.
        """
        filename = filename or url.split("/")[-1]
        local_path = self.cache_dir / resource_id / version / filename

        if local_path.exists():
            self._verify(local_path, checksum)
            return local_path

        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, local_path)
        except Exception as exc:
            raise ResourceNotFoundError(
                f"Could not download resource {resource_id!r} from {url!r}: {exc}"
            ) from exc

        self._verify(local_path, checksum)
        return local_path

    def _verify(self, path: Path, expected: str) -> None:
        """Verify the SHA256 checksum of a local file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        actual = sha256.hexdigest()
        if actual != expected:
            raise ChecksumError(
                f"Checksum mismatch for {path.name!r}: "
                f"expected {expected!r}, got {actual!r}."
            )

    def cache_path(self, resource_id: str, version: str, filename: str) -> Path:
        """Return the expected local cache path without downloading."""
        return self.cache_dir / resource_id / version / filename
