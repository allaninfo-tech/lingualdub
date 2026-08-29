# Getting Started

> **Note:** LingualDub is in pre-alpha development. This guide reflects the
> intended developer experience. Detailed setup instructions will be published
> with the first release.

## Installation

```bash
pip install lingualdub
```

Or to install from source:

```bash
git clone https://github.com/allaninfo-tech/lingualdub.git
cd lingualdub
pip install -e .
```

## Core Concepts

Before using the framework, it helps to understand the five core objects:

1. **Language** — describes a language and its resource profile
2. **Resource** — a data asset with provenance and versioning
3. **Component** — a replaceable processing unit with explicit input/output contracts
4. **Pipeline** — a composed sequence of components
5. **Result** — a structured output carrying status, segments, and provenance

## Development Lifecycle

The recommended workflow when working with a new language:

1. **Profile** the language — run a resource audit, create a `Language` object
2. **Register** available resources and compatible components
3. **Compose** a pipeline from the available components
4. **Run** a baseline to establish a measurable floor
5. **Adapt** — fine-tune or transfer from related languages where needed
6. **Evaluate** — use registered evaluator components
7. **Save** artifacts and register them for the next iteration

## Extending the Framework

See [contributing.md](contributing.md) for how to add new languages,
components, datasets, and evaluators.
