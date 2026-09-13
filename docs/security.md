# Security — Trust Boundaries and Hardening (PRO-004)

This document defines trust boundaries, input validation, and secure handling for LingualDub (PRO-004, PRO-005, PRO-006).

## Trust Boundaries

| Boundary | Trusted | Untrusted | Handling |
|---|---|---|---|
| **CLI / API input** | Framework code, validated `FrameworkConfig` | User-supplied YAML/JSON config, audio/text paths, `Resource.path`, `Segment.text`, `metadata` dicts | Validate at entry points via `lingualdub.utils.validation` — reject traversal, size limits, depth limits |
| **ResourceManager cache** | `~/.cache/lingualdub` and `LINGUALDUB_CACHE_DIR` (config-controlled) | Remote URLs, downloaded files, checksums | SSRF block (localhost, private nets, metadata endpoints), 2GB cap, SHA256 verification, atomic writes |
| **Manifest discovery** | Installed `lingualdub.manifest.json` files on `sys.path` depth ≤3 | Manifest `module`/`attr` entrypoints, `task` enums | Strict JSON schema validation (`registry/manifest_schema.json`), `ManifestError` on violation |
| **Logging / Metrics labels** | Structured fields `run_id`, `pipeline_name` etc. | User-provided `api_key`, `email`, `speaker_reference`, file paths | `RedactionFilter` replaces `[REDACTED]` (PRO-005), `log_redaction_enabled` toggle, `sensitive_fields` extensible |
| **Config loading** | Defaults, `FrameworkConfig` dataclass | Env vars `LINGUALDUB_*`, YAML/JSON file content | `yaml.safe_load` only (never `yaml.load`), env var precedence documented, frozen after `validate()` |

## Input Validation

All public constructors delegate to `lingualdub.utils.validation`:

- `require_non_empty_string`, `validate_language_code`, `validate_version_string` — core invariants.
- `validate_resource_path(path)` — rejects `..`, null bytes, URL-encoded `%2e/%2f/%5c`, `~` expansion, and paths exceeding `DEFAULT_MAX_RESOURCE_PATH_LENGTH` (4096). Raises `ResourceError("Path traversal detected")`.
- `validate_segment_text_length(text, max_length=5000)` — enforces `FrameworkConfig.max_segment_length`.
- `validate_metadata_depth(dict, max_depth=10)` — enforces `FrameworkConfig.max_metadata_depth`.
- `validate_metadata_depth` checks nesting; oversized or too-deep inputs raise `ConfigurationValidationError`.

### Example

```python
from lingualdub.utils.validation import validate_resource_path

validate_resource_path("../../../etc/passwd")
# -> ResourceError: Path traversal detected for 'path': '../../../etc/passwd' contains '..'.

from lingualdub.core.segment import Segment

Segment(start=0, end=1, text="x" * 6000, language="lug")
# -> ConfigurationValidationError: Field 'text' exceeds max segment length 5000
```

### Size Limits

| Input | Limit | Config Key | Default |
|---|---|---|---|
| `Segment.text` | `max_segment_length` | `FrameworkConfig.max_segment_length` | `5000` chars |
| `Resource.path` | `DEFAULT_MAX_RESOURCE_PATH_LENGTH` | — | `4096` chars |
| `metadata`/`provenance` depth | `max_metadata_depth` | `FrameworkConfig.max_metadata_depth` | `10` |
| Downloaded file | `2GB` | `ResourceManager` internal | `2GiB` cap |

Limits are enforced at construction time, not at pipeline runtime, so errors are early.

## Safe YAML Loading

All config loading uses `yaml.safe_load` only:

- `lingualdub/pipeline/config_loader.py:37` — `yaml.safe_load(text)` for YAML; JSON via `json.loads`.
- Never `yaml.load` without `Loader=yaml.SafeLoader`. A grep for `yaml.load` without safe loader is part of CI.

A YAML containing Python tags (`!!python/object`) raises `ConfigurationValidationError` via `yaml.YAMLError` wrapper.

## SecurityConfig

`FrameworkConfig` exposes:

```python
from lingualdub.config import FrameworkConfig, SecurityConfig

cfg = load_config({"max_segment_length": 2000})
assert cfg.max_segment_length == 2000
assert cfg.security_config.max_segment_length == 2000  # view

sc = SecurityConfig(
    max_segment_length=5000, max_metadata_depth=10, path_traversal_check_enabled=True
)
sc.validate()
```

`SecurityConfig` is also importable from `lingualdub.config` and `lingualdub` top-level.

## Path Traversal Prevention

`ResourceManager._sanitize_part` and `validate_resource_path` both enforce:

- No `/` or `\` in `resource_id`/`version`/`filename` parts
- No `..` or leading `.`
- No `%2e/%2f/%5c` URL-encoded
- No null byte or `:`
- Resolved path must stay within `cache_dir` (`Path.resolve().relative_to(cache_dir.resolve())`)

## Secret Protection (PRO-005)

`lingualdub.observability.redaction.RedactionFilter` scans every log record for sensitive field names:

Default list (`FrameworkConfig.sensitive_fields`): `api_key`, `access_token`, `speaker_reference`, `voice_path`, `consent_record`, `email`. User can extend:

```python
cfg = load_config({"sensitive_fields": ["api_key", "custom_token"]})
from lingualdub.observability.logging import configure_logging

configure_logging(cfg)
```

Filter replaces values with `[REDACTED]` in `record.__dict__`, `record.args`, and message string. Applied automatically to all handlers when `log_redaction_enabled=True` (default).

Verification: log capture in tests confirms zero occurrences of raw secret values.

## Dependency Scanning (PRO-006)

- `pip-audit` added to `[dev]` extra in `pyproject.toml`.
- Workflow `.github/workflows/security.yml` runs `pip-audit --strict` on every push/PR, fails on critical/high CVE.
- Vulnerability response: see workflow `security.yml` comments — critical CVE blocks merge; high CVE requires justification; policy documented here.

### Security Workflow

```yaml
# .github/workflows/security.yml
name: Security Audit
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -e ".[dev]" && pip install pip-audit
      - run: pip-audit --strict
```

## Reporting

Report security issues via `SECURITY.md` (private disclosure). Do not file public issues for vulnerabilities.

## Changelog

- `PRO-004`: Added `validate_resource_path`, `SecurityConfig`, safe YAML, limits, traversal checks.
- `PRO-005`: Added `RedactionFilter`, `sensitive_fields` config.
- `PRO-006`: Added `pip-audit` and `security.yml`.
