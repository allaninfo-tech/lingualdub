# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Core Abstractions**: `Language`, `Resource`, `Component`, `Pipeline`, `Result`, `Segment`.
- **Registry & Manifest System**: `Registry` with conflict resolution policies (`NAMESPACED`, `HIGHEST_VERSION`, `EXPLICIT`) and `ManifestScanner` for dynamic extension discovery.
- **Pipeline Execution**: `PipelineExecutor` supporting `ABORT`, `SKIP`, and `DEGRADE` failure modes with automatic provenance merging.
- **Resource Management**: `ResourceManager` with caching, SHA256 integrity verification, and environment variable overrides.
- **Data Serialization**: JSON-compatible `to_dict()` and `from_dict()` methods on all core data structures.
- **Test Infrastructure**: Comprehensive test suite with >90% coverage on core modules and GitHub Actions CI.
- **Community Standards**: Full Apache 2.0 license, `CITATION.cff`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and issue/PR templates.

## [0.1.0-dev] - 2026-08-31
- Initial public repository structure and framework skeleton.
