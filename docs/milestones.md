# LingualDub — Project Milestones

> **Vision:**
> A composable, registry-based framework that makes the repeated engineering and research work
> around low-resource speech **reusable, composable, and replaceable** — without modifying the
> framework core when a new language, model, method, or evaluator is introduced.
>
> **Validation languages:**
> Luganda (`lug`) → Runyankole (`nyn`) → expandable to any low-resource language.

This document is the source of truth for project growth. A milestone is closed only when every
item in its checklist is met and its **Done When** condition is verifiably satisfied.

---

## Dependency Order

```
M0 — Foundation
 └─► M1 — First Real Pipeline
       └─► M2 — Evaluation Infrastructure
             ├─► M3 — Code-Switching
             ├─► M4 — Temporal Alignment ──────────► M7 — Audio-Visual Sync
             ├─► M5 — Voice-Retention Evaluation ──► M6 — Cross-Lingual Voice Transfer
             └─► M8 — Generalisation (Runyankole)

M0 through M8 ─────────────────────────────────────► M9 — Stable v0.1.0 Release
```

---

## Risk Register

| Risk | What it blocks | Mitigation |
|---|---|---|
| No real model implementations | M1 cannot start | Commit to one ASR, one MT, one TTS model before M1 begins |
| Extension manifest system not designed | External contributions structurally impossible | Build in M0 before any community outreach |
| Executor provenance-merge bug | Evaluation comparisons silently wrong | Fix in M0 with an explicit test proving provenance survives stage transitions |
| Voice data used without consent | Legal and ethical exposure | Enforce `consent_basis` at both resource registration and pipeline assembly |
| Runyankole resource audit not started | M8 cannot begin | Run audit alongside M2 work, not after |
| License unresolved | Nobody can legally use or contribute | Resolve before M9; Apache 2.0 is the standard for research frameworks |
| No CI | Regressions go undetected | Set up automated test runs in M0 |

---

---

# Milestone 0 — Solid Foundation

**Goal:** Make the existing skeleton trustworthy before building on it. Every abstraction that
has been designed must be tested. Every system that has been described must exist in code.

---

### 0.1 — Test suite for core abstractions

- [x] Tests for the Language object: required field validation, edge cases
- [x] Tests for the Resource object: field validation, consent enforcement logic, all resource kind values
- [x] Tests for the Segment object: timing guards (start ≥ 0, end ≥ start), duration calculation
- [x] Tests for the Result object: all status transitions (mark_partial, mark_degraded, mark_failed), is_usable, warning accumulation
- [x] Tests for the Component base: capability compatibility checking, language support checking, default degrade raises NotImplementedError
- [x] Tests for the Pipeline: empty stage guard, empty source language guard, assembly-time capability mismatch detection, stage names property
- [x] Mock components (return hardcoded Results, no ML) created as shared test fixtures
- [x] All tests pass

---

### 0.2 — Test suite for the registry

- [x] Register and resolve a single entry round-trip
- [x] Resolve by exact version
- [x] Resolve with no match raises a clear registry error
- [x] NAMESPACED conflict policy: both registrations are kept
- [x] HIGHEST_VERSION conflict policy: the higher version wins
- [x] EXPLICIT conflict policy: raises an error on collision
- [x] List returns sorted results
- [x] All tests pass

---

### 0.3 — Test suite for the pipeline executor

- [x] ABORT failure mode: executor raises a pipeline execution error and marks result FAILED
- [x] SKIP failure mode: result is marked PARTIAL and execution continues with remaining stages
- [x] DEGRADE failure mode (component has a degrade path): result is marked DEGRADED
- [x] DEGRADE failure mode (no degrade path defined): falls back to PARTIAL behaviour
- [x] Multi-stage pipeline where only one stage fails: other stages still run
- [x] Provenance set by the executor is not lost when a stage returns its own Result — provenance merging is explicitly tested
- [x] All tests pass

---

### 0.4 — Fix the executor provenance-merge bug

- [x] The current behaviour is identified: the executor creates an initial Result with provenance, but the first stage that returns its own Result silently replaces it, discarding the executor's provenance
- [x] A provenance-merging strategy is chosen and documented
- [x] The fix is implemented
- [x] A test proves provenance set before the stage loop is still present in the final Result

---

### 0.5 — Extension manifest system

- [x] A manifest format is designed and documented (JSON file, Python entry points, or equivalent)
- [x] A manifest scanner is implemented: discovers installed extensions, parses manifests, calls register() for each declared entry
- [x] A malformed or invalid manifest raises a clear error identifying the problem
- [x] Built-in languages and components are registered through the manifest path rather than by hardcoded imports
- [x] Manifest format is documented so external contributors know how to ship extensions
- [x] Scanner tests pass: valid manifest registers correctly; invalid manifest raises a clear error

---

### 0.6 — Serialization for all core objects

- [x] A serialization strategy is chosen (Pydantic, dataclasses with to_dict/from_dict, or equivalent)
- [x] Every core object (Language, Resource, Segment, Result, Pipeline) can serialize to a JSON-compatible representation
- [x] Every core object can deserialize from that same representation back to an equal object
- [x] Round-trip tests pass for every core type: object → serialize → deserialize → assert equal
- [x] A pipeline configuration can be saved to disk and reloaded into a live Pipeline object

---

### 0.7 — Resource manager

- [x] A ResourceManager utility is implemented
- [x] Given a resource identifier and URL, it downloads the resource to a local cache
- [x] Default cache location is predictable and follows platform conventions
- [x] The cache location can be overridden via an environment variable
- [x] On a cache hit (file already exists and checksum matches), no download is performed
- [x] SHA256 checksum is verified after every download; a mismatch raises a clear checksum error
- [x] If a required resource is missing, a clear error is raised naming the resource and its expected location
- [x] Tests pass without real network calls (use mocking in CI)

---

### 0.8 — Continuous integration

- [x] A CI workflow runs on every push and every pull request to the main branch
- [x] The workflow installs dependencies from a clean environment and runs the full test suite
- [x] The workflow reports test coverage
- [x] Coverage on the core package is ≥ 80 %
- [x] A failing test causes the CI run to fail and blocks merging

---

### M0 — Done When

- [x] All sub-tasks 0.1 through 0.8 are complete
- [x] `pytest` passes with ≥ 80 % coverage on the core package
- [x] CI passes on every push
- [x] All core objects round-trip through serialization without data loss
- [x] Extension manifests are discovered and loaded without hardcoded imports

---

---

# Milestone 1 — First Real Dubbing Pipeline

**Goal:** A complete end-to-end run: a Luganda audio file goes in, an English audio file comes
out, and the Result carries full provenance. No voice preservation yet — this milestone proves
that the pipeline contract works with real models.

---

### 1.1 — Component I/O contracts

- [x] Each component base class documents exactly what Segment fields it expects to receive as input
- [x] Each component base class documents exactly what Segment fields it guarantees to populate in its output
- [x] These contracts are enforced at pipeline assembly time wherever possible, not just at runtime
- [x] The capability token vocabulary (the strings used in `requires` and `provides`) is documented and agreed upon

---

### 1.2 — ASR component (Luganda)

- [x] A concrete ASR component implementation wraps an existing multilingual model (`SunbirdASRComponent` and `WhisperASRComponent`)
- [x] The model choice is documented with rationale (Sunbird SALT Luganda fine-tune & OpenAI Whisper Large v3)
- [x] The component accepts an audio resource as input
- [x] The component outputs a Result with Segment objects carrying: start time, end time, transcribed text, language code, and confidence score
- [x] Word-level timestamps are emitted as a capability token
- [x] Language detection is emitted as a capability token
- [x] The component is registered via manifest
- [x] An integration test confirms: given a short Luganda audio clip, the output has at least one segment with non-empty text and valid timing

---

### 1.3 — Translation component (Luganda → English)

- [x] A concrete translation component implementation wraps an existing multilingual MT model (`SunbirdTranslationComponent` & `HuggingFaceTranslationComponent`)
- [x] The model choice is documented with rationale (Sunbird `sunbird-mul-en` & Meta NLLB-200)
- [x] The component accepts a Result with source-language Segment objects
- [x] The component outputs a Result with translated Segment objects
- [x] The original source language is preserved on each Segment (source_language field)
- [x] The output Segment language field is updated to the target language
- [x] The component declares which capability tokens it requires and provides
- [x] The component is registered via manifest
- [x] An integration test confirms: given a Result with Luganda segments, the output contains English text and the source language field is preserved

---

### 1.4 — TTS component (English)

- [x] A concrete TTS component implementation wraps an existing speech synthesis model (`MMSTTSComponent` & `DummyTTSComponent`)
- [x] The model choice is documented with rationale (Meta MMS-TTS English)
- [x] The component accepts a Result with translated text Segments
- [x] The component synthesises audio for each segment and adds the output audio paths to Result.artifacts
- [x] The component is configured to degrade gracefully (silent or placeholder audio) rather than abort on failure
- [x] A degrade() path is implemented
- [x] The component declares which capability tokens it requires and provides
- [x] The component is registered via manifest
- [x] An integration test confirms: given a Result with English segments, the output artifacts list contains at least one valid audio file

---

### 1.5 — Pipeline configuration and config loader

- [x] A pipeline configuration format is defined (YAML or JSON)
- [x] A configuration loader resolves component names from the registry and constructs a live Pipeline object
- [x] A reference pipeline config for the Luganda → English dubbing pipeline is committed (`configs/luganda_english_baseline.yaml`)
- [x] The config loader is tested: loading the reference config produces the correct Pipeline with stages in the right order

---

### 1.6 — End-to-end integration test and notebook

- [x] An end-to-end integration test runs the full ASR → Translation → TTS pipeline on a short Luganda audio clip
- [x] The test asserts: result status is COMPLETE
- [x] The test asserts: result provenance contains pipeline name, run ID, component versions, and dataset version
- [x] The test asserts: result artifacts contains at least one synthesised English audio file
- [x] A notebook demonstrates the full pipeline from audio input to dubbed audio output with result inspection (`notebooks/colab_luganda_m1_experiment.ipynb`)
- [x] The notebook runs without errors

---

### M1 — Done When

- [x] A Luganda audio file is passed to the pipeline and an English audio file is produced
- [x] Result status is COMPLETE
- [x] Result provenance is fully populated
- [x] The integration test passes in CI
- [x] The notebook runs end-to-end without errors

---

---

# Milestone 2 — Evaluation Infrastructure

**Goal:** Every result is measurable and two runs with the same evaluation set but different
component versions are directly comparable with a single function call.

---

### 2.1 — Evaluator base class

- [x] The evaluator component base class is fully specified
- [x] It accepts a pipeline Result and a reference evaluation Resource as inputs
- [x] It returns a Result whose metadata carries structured metric values
- [x] Standard metric key names are defined and documented: WER, CER for ASR; BLEU, chrF for translation; timing envelope for alignment
- [x] All evaluators are required to populate provenance with evaluation set version and protocol name

---

### 2.2 — ASR evaluator (WER and CER)

- [x] A WER and CER evaluator component is implemented (`WEREvaluator`)
- [x] It computes word error rate and character error rate against a reference transcription resource
- [x] It requires a transcription capability token
- [x] It returns structured metric values in result metadata
- [x] It populates provenance correctly
- [x] It is registered via manifest
- [x] Unit tests confirm correct computation against known inputs

---

### 2.3 — Translation evaluator (BLEU and chrF)

- [x] A BLEU and chrF evaluator component is implemented (`TranslationEvaluator`)
- [x] It computes scores against a reference translation resource
- [x] It requires a translation capability token
- [x] It returns structured metric values in result metadata
- [x] It populates provenance correctly
- [x] It is registered via manifest
- [x] Unit tests confirm correct computation against known inputs

---

### 2.4 — Evaluation sets registered as resources

- [x] A Luganda ASR evaluation set is identified and registered as a Resource with version, source, and license recorded in provenance
- [x] A Luganda → English parallel evaluation set is identified and registered as a Resource with version, source, and license
- [x] Data sources and licenses are documented

---

### 2.5 — Run comparison utility

- [x] A utility function accepts two Result objects and returns a dict of metric deltas (`compare_runs`)
- [x] It validates that both results share the same dataset version and evaluation protocol before comparing; raises a clear error if they are not comparable
- [x] Tests confirm: two results with different metric values produce the correct deltas; mismatched metadata raises an error

---

### 2.6 — Runyankole resource audit (begin now, do not wait for M8)

- [x] Available Runyankole speech corpora are surveyed and catalogued
- [x] Available Runyankole text data is surveyed and catalogued
- [x] The Runyankole language profile is updated to reflect confirmed resources
- [x] Confirmed resources are registered with version, source, and license

---

### M2 — Done When

- [x] Running the M1 pipeline on the Luganda ASR evaluation set produces a Result with WER and CER in its metadata
- [x] Running it twice with different component versions and calling compare_runs() returns a metric delta dict
- [x] Both evaluation sets are registered with full provenance
- [x] All evaluator tests pass

---

---

# Milestone 3 — Code-Switching

**Goal:** Mixed-language speech is handled structurally. Segment.language is authoritative per
segment, not inherited from the file or utterance level. Routing is automatic.

---

### 3.1 — Language identification at the segment level

- [x] A component is implemented that takes ASR output with word-level timestamps and assigns a language code to each Segment (`DummyCodeSwitchComponent` & `HeuristicLIDComponent`)
- [x] A language identification model or signal (from ASR output, fastText LID, or equivalent) is used
- [x] The component requires word timestamp capability
- [x] The component provides language label capability
- [x] The component is registered via manifest
- [x] Unit tests confirm: given input with spans in two languages, each output Segment has the correct language code

---

### 3.2 — Per-segment language routing in the executor

- [x] The executor implements the per_segment_language pipeline flag
- [x] When the flag is enabled, each stage is invoked only for segments whose language it declares support for
- [x] When a segment's language is not supported by any component in a stage, the failure mode is applied: SKIP marks the segment, ABORT raises a clear error naming the unsupported language
- [x] All routing paths are covered by tests

---

### 3.3 — Code-switch evaluation set

- [x] A collection of utterances containing both Luganda and English spans is assembled (`LUGANDA_ENG_CODESWITCH_EVAL_SET`)
- [x] Ground-truth per-segment language labels are recorded
- [x] Consent basis is recorded for all voice recordings
- [x] The collection is registered as a Resource with version and provenance

---

### 3.4 — End-to-end code-switch integration test

- [x] The full pipeline runs on mixed-language audio: ASR → code-switch detection → per-segment routing → translation → TTS
- [x] Luganda segments are translated; English segments are passed through without re-translation
- [x] Segment.language matches ground truth on ≥ 80 % of segments
- [x] The test passes in CI

---

### M3 — Done When

- [x] A mixed-language audio file produces a Result where every Segment has a language code set correctly
- [x] Per-segment routing is tested end-to-end
- [x] The integration test passes
- [x] No file in the core package was changed to make this work

---

---

# Milestone 4 — Temporal Alignment

**Goal:** Dubbed audio fits within the timing envelope of the source so it is usable in
audiovisual content without constant timing drift.

---

### 4.1 — Forced alignment

- [x] A forced alignment component is implemented using an established aligner
- [x] It produces word-level timestamps within each Segment
- [x] It requires a transcription capability and emits an aligned timestamps capability
- [x] It acquires pronunciation dictionaries and acoustic models via the ResourceManager
- [x] It is registered via manifest
- [x] Unit tests confirm: word-level timestamps fall within the parent Segment boundaries

---

### 4.2 — Duration modelling

- [x] A duration modelling component computes the target duration for each synthesised segment based on source timing and translated character count
- [x] Target duration is stored in Segment metadata
- [x] It requires translation and aligned timestamp capabilities and provides duration target capability
- [x] Unit tests confirm: duration ratios are computed correctly for known inputs

---

### 4.3 — TTS speech-rate control

- [x] The TTS component is extended to accept target duration metadata per Segment
- [x] Three fitting strategies are implemented: COMPRESS (faster speech rate), SPLIT (break at sentence boundaries), SKIP (mark segment as unfit)
- [x] The strategy chosen for each segment is recorded in Segment metadata
- [x] The TTS component's required capability tokens are updated to include duration targets

---

### 4.4 — Temporal alignment evaluator

- [x] An evaluator component computes the percentage of segments whose dubbed end time is within 200ms of the source end time
- [x] The score is returned as a float in result metadata
- [x] The evaluator is registered via manifest
- [x] Tests confirm correct scoring against known inputs

---

### M4 — Done When

- [x] A Luganda → English pipeline produces dubbed audio where ≥ 80 % of segments are within 200ms of the source timing envelope
- [x] The timing score is measured by the evaluator and recorded with full provenance
- [x] All component and integration tests pass


---

---

# Milestone 5 — Voice-Retention Evaluation

**Goal:** A repeatable, versioned, provenance-tracked score measuring how similar the dubbed
voice sounds to the original speaker. This is a prerequisite for voice transfer.

> **Consent is mandatory.** Every voice Resource used in M5 or M6 must carry a recorded consent
> basis. This must be enforced at both resource registration time and pipeline assembly time.
> A component that processes voice data must refuse to run if the input resource has no consent basis.

---

### 5.1 — Speaker embedding component

- [ ] A speaker embedding component is implemented using an established speaker encoder model
- [ ] It accepts an audio resource or a Result with audio artifacts as input
- [ ] It outputs a speaker embedding vector in Result metadata
- [ ] It refuses to process any resource that lacks a consent basis and raises a clear error
- [ ] It acquires model weights via the ResourceManager
- [ ] It is registered via manifest
- [ ] Unit tests confirm: two calls with the same audio produce near-identical embeddings

---

### 5.2 — Speaker similarity evaluator

- [ ] A speaker similarity evaluator accepts two Results, each with a speaker embedding in metadata
- [ ] It computes cosine similarity between the two embeddings and returns a score in [0, 1]
- [ ] The score is returned in result metadata with full provenance
- [ ] It is registered via manifest
- [ ] Unit tests confirm: identical embeddings → 1.0; orthogonal embeddings → 0.0

---

### 5.3 — Human evaluation protocol

- [ ] A formal human evaluation protocol is written and versioned
- [ ] The protocol specifies: exact question wording, rating scale (1–5 MOS), minimum number of raters, audio presentation format (randomised, blind), scoring aggregation method, and inter-rater agreement measure
- [ ] The protocol specifies the exact reporting format: mean, standard deviation, sample size, dataset version, system version
- [ ] All voice-retention evaluations must cite the protocol version

---

### M5 — Done When

- [ ] Given a source audio file and a dubbed audio file, the pipeline extracts speaker embeddings from both and returns a cosine similarity score with full provenance
- [ ] The human evaluation protocol document is written and versioned
- [ ] All component and evaluator tests pass
- [ ] No voice resource without consent can reach the speaker encoder under any execution path

---

---

# Milestone 6 — Cross-Lingual Voice Transfer

**Depends on M5. Voice-retention evaluation must be operational before this milestone begins.**

**Goal:** The dubbed speech preserves the original speaker's voice characteristics across the
language boundary — the same person's voice, speaking a different language.

---

### 6.1 — Voice-conditioned TTS component

- [ ] A voice-conditioned TTS component wraps a zero-shot or few-shot cross-lingual voice cloning model
- [ ] The model choice and its licence are documented
- [ ] The component accepts translated text Segments and a speaker reference Resource
- [ ] It enforces consent on the speaker reference Resource and raises a clear error if absent
- [ ] It synthesises audio conditioned on the speaker embedding from the reference
- [ ] It requires translation and speaker embedding capability tokens
- [ ] It provides synthesised audio and voice conditioned capability tokens
- [ ] It acquires model weights via the ResourceManager
- [ ] It is registered via manifest

---

### 6.2 — Speaker identity propagation through the pipeline

- [ ] The Segment speaker field is set by the ASR component and is not cleared by any downstream component
- [ ] The translation component explicitly preserves the speaker field on output Segments
- [ ] The voice-conditioned TTS component reads the speaker field to select the correct reference
- [ ] Speaker embedding availability is validated at pipeline assembly time, not only at runtime

---

### 6.3 — Baseline comparison and results

- [ ] A baseline is established: the unconditioned TTS from M1 is run on a fixed set of test clips and speaker similarity scores are recorded
- [ ] The voice-transfer TTS is run on the same test clips and scores are recorded
- [ ] The voice-transfer scores are compared against the baseline
- [ ] Results are recorded with component versions, dataset version, and run IDs so they are reproducible

---

### M6 — Done When

- [ ] The voice-transfer TTS produces dubbed audio that scores measurably higher on speaker similarity than the unconditioned baseline
- [ ] No voice resource without consent can reach the voice-transfer component under any execution path
- [ ] Results are reproducible: the same config run twice produces the same scores within floating-point tolerance

---

---

# Milestone 7 — Audio-Visual Synchronisation

**Depends on M4. Temporal alignment must be working before this milestone begins.**

**Goal:** Dubbed audio can be inserted into a video with plausible lip-sync alignment.

---

### 7.1 — AV sync evaluator

- [ ] An evaluator component measures the lip-sync offset between dubbed audio and source video using an established AV synchrony model
- [ ] The metric is mean absolute AV offset in milliseconds across segments
- [ ] The score is returned in result metadata
- [ ] The evaluator is registered via manifest
- [ ] Tests confirm correct behaviour on known inputs

---

### 7.2 — Dialogue timing adapter

- [ ] A dialogue timing component adjusts Segment boundaries to align with on-screen dialogue cues
- [ ] It detects cue boundaries from the source video (scene cuts, mouth-open periods, or subtitle cues)
- [ ] It produces updated Segment start and end times that snap to these boundaries
- [ ] It builds on and is compatible with the temporal alignment stage from M4

---

### 7.3 — Video output artifact

- [ ] A pipeline stage merges dubbed audio with a source video file
- [ ] The merged video is registered as a Resource artifact with full provenance: component versions, run ID, source video reference
- [ ] The ResourceKind enumeration is extended if necessary to include a video type

---

### M7 — Done When

- [ ] Given a source video with Luganda audio, the pipeline produces a dubbed video with English audio where mean AV sync offset is ≤ 100ms across segments
- [ ] The video artifact is registered with full provenance
- [ ] The AV sync evaluator test passes

---

---

# Milestone 8 — Generalisation Proof (Runyankole)

**Goal:** Prove the framework's core claim: a new language can be added and a full pipeline can
run end-to-end without modifying the framework core.

---

### 8.1 — Runyankole resource audit completion

- [ ] The audit begun in M2 is completed
- [ ] The Runyankole language profile is updated to its final resource profile label
- [ ] All confirmed resources are registered with version, source, and license
- [ ] Data sources and licenses are documented

---

### 8.2 — Runyankole ASR via language-family transfer

- [ ] A Runyankole ASR component is implemented using cross-lingual transfer from the Luganda ASR work
- [ ] The component declares supported_languages = ["nyn"]
- [ ] The component is registered via manifest
- [ ] No file in the core, registry, or pipeline packages is modified to make this work

---

### 8.3 — Runyankole evaluation

- [ ] A Runyankole ASR evaluation set is registered as a Resource
- [ ] The WER evaluator from M2 is run on Runyankole output
- [ ] Results are recorded alongside Luganda baseline results for comparison

---

### 8.4 — Runyankole pipeline

- [ ] A pipeline configuration for Runyankole is created by composing existing registered components
- [ ] The pipeline is loaded from config and runs end-to-end
- [ ] No file in the core, registry, or pipeline packages is modified to make this work

---

### 8.5 — Architectural audit

The following changes must all have been made **without modifying any file in the core, registry,
or pipeline packages**. If any item below required such a change, the architecture has not met its
design goal.

- [ ] New language registered → only language profile and manifest modified
- [ ] New ASR component added → only component implementation and manifest created
- [ ] New evaluation set registered → only Resource definition added
- [ ] New pipeline composed → only configuration file created
- [ ] Zero lines changed in core, registry, or pipeline packages across this entire milestone

---

### M8 — Done When

- [ ] A Runyankole ASR pipeline runs end-to-end with evaluation and results are recorded
- [ ] The architectural audit (8.5) is all green
- [ ] No framework core file was changed

---

---

# Milestone 9 — Stable First Release (v0.1.0)

**Goal:** The framework is usable and extendable by contributors who were not involved in
building it.

---

### 9.1 — Licence

- [ ] A licence is chosen and applied (Apache 2.0 recommended for research frameworks)
- [ ] The licence file is updated from its current placeholder
- [ ] The project metadata reflects the chosen licence
- [ ] All source files carry the correct licence identifier

---

### 9.2 — PyPI publication

- [ ] All project metadata is complete: name, version, description, classifiers, keywords, authors, URLs
- [ ] The package builds cleanly
- [ ] It is published to TestPyPI and installs correctly from there
- [ ] It is published to PyPI
- [ ] Installation via `pip install lingualdub` works on a clean machine
- [ ] A release CI workflow publishes automatically on a version tag push

---

### 9.3 — Contribution guide

- [ ] How to set up a development environment from scratch
- [ ] How to run the test suite and check coverage
- [ ] How to implement a new component from scratch with a working minimal example
- [ ] How to write and publish a manifest file
- [ ] How to register a new language
- [ ] How to register a dataset as a Resource
- [ ] Code style requirements: type annotations on all public APIs, docstrings on all public classes and methods, line length, formatting tool
- [ ] Pull request and review process
- [ ] A contributor outside the core team has followed the guide from scratch and confirmed it works

---

### 9.4 — Documentation site

- [ ] Home page: project purpose, quickstart, links to PyPI and GitHub
- [ ] Getting Started: real working example based on the M1 pipeline (install → configure → run → inspect Result)
- [ ] Architecture overview
- [ ] Component authoring guide: how to subclass a component base, declare capability tokens, implement run() and degrade()
- [ ] Registry and manifest guide: how to write a manifest, how the scanner works, how versioning works
- [ ] Research modules status page: current status of M3 through M7 with their done-when conditions
- [ ] Evaluation guide: how to register an evaluation set, run an evaluator, and compare runs
- [ ] API reference generated from docstrings
- [ ] All pages are accurate and reflect the current released version

---

### 9.5 — Test coverage

- [ ] Test coverage on the core package is ≥ 85 %
- [ ] End-to-end integration tests for the M1, M2, and M3 pipelines pass in CI
- [ ] Every test skip in CI has a documented reason in the test file
- [ ] `pytest` passes with the coverage threshold enforced as a hard failure

---

### M9 — Done When

- [ ] `pip install lingualdub` works from PyPI
- [ ] A contributor outside the core team can follow the contribution guide and publish a working component
- [ ] All documentation pages are live and accurate for the released version
- [ ] CI passes with ≥ 85 % coverage on every push to main
- [ ] The licence is applied and the repository is legally usable

---

---

*This document is the source of truth for project growth tracking. Update checklist items as
work is completed. Do not mark a milestone closed until its Done When condition is fully and
verifiably met. File names, module paths, and implementation details may evolve — the
deliverables described here do not.*
