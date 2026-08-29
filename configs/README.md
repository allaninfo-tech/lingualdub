# Pipeline Configuration Templates

This directory contains YAML pipeline configuration templates. Configuration-driven
execution allows experiments to be shared as reproducible pipeline definitions
without requiring Python code.

A pipeline configuration specifies:
- Source and target language
- Component selection per stage (type and optionally version)
- Per-segment language routing (for code-switching-aware pipelines)
- Stage failure behaviour

Concrete configuration files will be added as components are implemented.
