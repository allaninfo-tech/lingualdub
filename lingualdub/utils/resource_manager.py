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


import threading
import uuid


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

    Thread-safe: uses atomic file operations and internal locking to prevent
    race conditions during concurrent downloads.
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        env_dir = os.environ.get(ENV_CACHE_DIR)
        # Explicit cache_dir takes precedence over env var; env var used only as fallback.
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir)
        elif env_dir:
            self.cache_dir = Path(env_dir)
        else:
            self.cache_dir = DEFAULT_CACHE_DIR
        self._lock = threading.Lock()

    @staticmethod
    def _sanitize_part(value: str, label: str) -> str:
        """Validate a path part does not contain traversal or separators."""
        if not value or not value.strip():
            raise ValueError(f"{label} must be a non-empty string.")
        if "/" in value or "\\" in value or ".." in value:
            raise ValueError(f"{label} {value!r} must not contain path separators or '..'.")
        if Path(value).is_absolute():
            raise ValueError(f"{label} {value!r} must not be absolute.")
        return value

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
        filename = filename or url.split("/")[-1].split("?")[0].split("#")[0]
        if not filename:
            filename = f"{resource_id}_{version}"
        # Validate parts to prevent path traversal
        self._sanitize_part(resource_id, "resource_id")
        self._sanitize_part(version, "version")
        self._sanitize_part(filename, "filename")
        # Validate URL scheme to prevent SSRF (only http/https allowed)
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ResourceNotFoundError(f"Unsupported URL scheme for {url!r}: only http/https allowed.")
        local_path = self.cache_dir / resource_id / version / filename
        # Ensure resolved path stays within cache_dir
        try:
            local_path.resolve().relative_to(self.cache_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"Resolved path {local_path!r} escapes cache directory {self.cache_dir!r}.") from exc

        # Fast path: already cached and verified
        if local_path.exists():
            self._verify(local_path, checksum)
            return local_path

        with self._lock:
            # Double-check inside lock
            if local_path.exists():
                self._verify(local_path, checksum)
                return local_path

            local_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = local_path.parent / f".tmp_{uuid.uuid4().hex}_{filename}"

            try:
                # Use urlopen with timeout instead of deprecated urlretrieve; stream to file
                import urllib.request as _urlrequest

                req = _urlrequest.Request(url, headers={"User-Agent": "LingualDub/0.1"})
                with _urlrequest.urlopen(req, timeout=30) as resp, open(temp_path, "wb") as out:
                    for chunk in iter(lambda: resp.read(8192), b""):
                        out.write(chunk)
                self._verify(temp_path, checksum)
                os.replace(temp_path, local_path)
            except ChecksumError:
                if temp_path.exists():
                    temp_path.unlink()
                raise
            except Exception as exc:
                if temp_path.exists():
                    temp_path.unlink()
                raise ResourceNotFoundError(
                    f"Could not download resource {resource_id!r} from {url!r}: {exc}"
                ) from exc

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
        self._sanitize_part(resource_id, "resource_id")
        self._sanitize_part(version, "version")
        self._sanitize_part(filename, "filename")
        p = self.cache_dir / resource_id / version / filename
        try:
            p.resolve().relative_to(self.cache_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"Resolved path {p!r} escapes cache directory {self.cache_dir!r}.") from exc
        return p
