# Contributing to LingualDub

The primary extension mechanism is the component and registry system.
New languages, models, methods, datasets, and evaluators can all be contributed
as registered extensions without requiring changes to framework internals.

## Extension Types

| Type | Where | How |
|---|---|---|
| New language | `lingualdub/languages/` or extension package | Define a `Language` object and register it |
| New component | Any package with a manifest | Subclass the relevant base class and register it |
| New dataset | Any package with a manifest | Define a `Resource` object and register it |
| New evaluator | Any package with a manifest | Subclass `EvaluatorComponent` and register it |
| New pipeline | `configs/` or application code | Compose existing components |

## Code Standards

- Python 3.10+
- Type annotations on all public functions and class attributes
- Docstrings on all public classes and methods
- Tests for all new components and abstractions

## Research Contributions

Research challenge modules live under `research/`. Each module has its own
README describing the current baseline, open questions, and done-when criteria.
Research contributions do not need to touch the core framework package.

Detailed contribution guidelines will be published alongside the first stable release.
