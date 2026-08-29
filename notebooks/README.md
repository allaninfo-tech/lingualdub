# Notebooks

This is the primary development and testing workspace for LingualDub. All model
testing, component experimentation, pipeline runs, and data exploration happen here
before anything gets promoted to the framework package.

## Structure

| Folder | Purpose |
|---|---|
| `00_getting_started/` | Framework orientation — core objects, registry, basic wiring |
| `01_language_profiling/` | Auditing language resources before building pipelines |
| `02_pipelines/` | Building and running end-to-end pipelines |
| `03_components/` | Testing and evaluating individual components in isolation |
| `04_adaptation/` | Fine-tuning, transfer learning, and data augmentation workflows |
| `05_evaluation/` | Running evaluators, comparing runs, inspecting results |
| `06_experiments/` | Active scratch space for ongoing experiments |

## Workflow

Notebooks are the lab. The loop is:

1. **Explore** data and model behaviour here
2. **Prototype** component logic in a notebook
3. **Promote** stable, tested logic into `lingualdub/components/`
4. **Register** the component and write a test in `tests/`
5. **Repeat**

## Conventions

- Number notebooks within each folder: `01_`, `02_`, etc.
- Keep one clear topic per notebook
- Add a markdown cell at the top describing what the notebook does and what you expect to learn
- Record results and observations in markdown cells — not just code
