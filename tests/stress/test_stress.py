"""
Comprehensive stress tests for LingualDub core engine, registry, pipeline, and utilities.

Tests include:
- High concurrency and thread safety (Registry, ResourceManager)
- Large payload scale (10,000+ segments, deep provenance)
- Deep multi-stage pipeline execution
- Chaotic failure cascades and fault tolerance
- Deserialization fuzzing and edge cases
"""

import concurrent.futures
import hashlib
import json
import random
import threading
from typing import List, Union
from unittest.mock import patch

import pytest

import lingualdub as ld
from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.pipeline.executor import PipelineExecutionError, PipelineExecutor
from lingualdub.registry.manifest import ManifestScanner
from lingualdub.registry.registry import ConflictPolicy, Registry, RegistryError
from lingualdub.utils.resource_manager import ChecksumError, ResourceManager


# ─── 1. CONCURRENCY & THREAD SAFETY ───

def test_concurrent_registry_writes_and_reads():
    """Test 50 threads concurrently registering and resolving entries."""
    registry = Registry(conflict_policy=ConflictPolicy.NAMESPACED)
    num_threads = 50
    entries_per_thread = 20

    def worker(thread_id: int):
        for i in range(entries_per_thread):
            key = f"key_{thread_id}_{i}"
            val = f"value_{thread_id}_{i}"
            registry.register("component", key, val, version="1.0.0")
            resolved = registry.resolve("component", key)
            assert resolved == val

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, t) for t in range(num_threads)]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    registered_items = registry.list("component")
    assert len(registered_items) == num_threads * entries_per_thread


def test_concurrent_resource_manager_downloads(tmp_path):
    """Test multiple threads requesting the same resource simultaneously."""
    content = b"heavy-neural-model-weights-binary-data"
    checksum = hashlib.sha256(content).hexdigest()
    manager = ResourceManager(cache_dir=tmp_path)

    download_count = 0
    lock = threading.Lock()

    def fake_urlopen(req, timeout=30):
        nonlocal download_count
        with lock:
            download_count += 1
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.read = MagicMock(side_effect=[content, b""])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None
        return mock_resp

    def worker():
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            path = manager.get("model-shared", "1.0.0", "http://example.com/weights.bin", checksum)
            assert path.exists()
            assert path.read_bytes() == content

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker) for _ in range(20)]
        for f in concurrent.futures.as_completed(futures):
            f.result()


# ─── 2. LARGE PAYLOAD & SCALE STRESS ───

def test_large_segment_payload_round_trip():
    """Test serialization and timing calculation for 10,000 segments."""
    num_segments = 10_000
    segments = []
    current_time = 0.0

    luganda_phrases = [
        "Oli otya nno?",
        "Tusanyuse nnyo okulaba.",
        "Emikono waggulu!",
        "LingualDub ekola bulungi nnyo.",
        "Abaana basoma ebitabo.",
    ]

    for i in range(num_segments):
        duration = random.uniform(0.5, 3.0)
        end_time = current_time + duration
        seg = Segment(
            start=round(current_time, 3),
            end=round(end_time, 3),
            text=random.choice(luganda_phrases),
            language="lug",
            speaker=f"SPK_{i % 50:03d}",
            confidence=round(random.uniform(0.80, 0.99), 2),
            source_language="lug",
            metadata={"index": i, "pitch": 120.5},
        )
        segments.append(seg)
        current_time = end_time

    result = Result(
        segments=segments,
        source_language="lug",
        target_language="eng",
        provenance={"total_segments": num_segments, "run_id": "stress-test-uuid"},
    )

    # Serialize
    serialized = result.to_dict()
    assert len(serialized["segments"]) == num_segments

    # Deserialize
    restored = Result.from_dict(serialized)
    assert len(restored.segments) == num_segments
    assert restored.segments[0].text == segments[0].text
    assert restored.segments[-1].end == segments[-1].end
    assert restored.is_usable is True


# ─── 3. DEEP PIPELINE CHAINS & CAPABILITY VALIDATION ───

class PassThroughStage(Component):
    """Component that passes input through and records its execution in provenance."""
    def __init__(self, stage_idx: int, req: List[str], prov: List[str]):
        self.name = f"stage_{stage_idx:03d}"
        self.version = "1.0.0"
        self.task = ComponentTask.ASR
        self.requires = req
        self.provides = prov
        self.on_failure = FailureMode.ABORT
        self.stage_idx = stage_idx

    def run(self, input: Union[Resource, Result]) -> Result:
        res = input if isinstance(input, Result) else Result(source_language="lug")
        res.provenance[f"executed_stage_{self.stage_idx}"] = True
        return res


def test_deep_pipeline_chain_100_stages():
    """Test assembly and execution of a 100-stage pipeline with chained capabilities."""
    stages = []
    for i in range(100):
        req = [f"cap_{i}"] if i > 0 else []
        prov = [f"cap_{i+1}"]
        stages.append(PassThroughStage(i, req, prov))

    pipeline = Pipeline(stages=stages, source_language="lug")
    assert len(pipeline.stage_names) == 100

    executor = PipelineExecutor(pipeline)
    final_result = executor.run(Result(source_language="lug"))

    assert final_result.status == ResultStatus.COMPLETE
    assert "executed_stage_0" in final_result.provenance
    assert "executed_stage_99" in final_result.provenance
    assert "pipeline" in final_result.provenance


# ─── 4. CHAOTIC FAILURE CASCADES ───

class FlakyStage(Component):
    def __init__(self, name: str, mode: FailureMode, fail: bool, has_degrade: bool = True):
        self.name = name
        self.version = "1.0.0"
        self.task = ComponentTask.ASR
        self.requires = []
        self.provides = []
        self.on_failure = mode
        self.fail = fail
        self.has_degrade = has_degrade

    def run(self, input: Union[Resource, Result]) -> Result:
        if self.fail:
            raise RuntimeError(f"Simulated fault in {self.name}")
        return input if isinstance(input, Result) else Result()

    def degrade(self, input: Union[Resource, Result]) -> Result:
        if not self.has_degrade:
            raise NotImplementedError()
        res = input if isinstance(input, Result) else Result()
        res.mark_degraded(f"Fallback path active for {self.name}")
        return res


def test_mixed_failure_cascade_pipeline():
    """Test complex pipeline with a mixture of succeeding, skipping, and degrading stages."""
    stages = [
        FlakyStage("s1_ok", FailureMode.ABORT, fail=False),
        FlakyStage("s2_skip", FailureMode.SKIP, fail=True),
        FlakyStage("s3_degrade", FailureMode.DEGRADE, fail=True, has_degrade=True),
        FlakyStage("s4_degrade_nodef", FailureMode.DEGRADE, fail=True, has_degrade=False),
        FlakyStage("s5_ok_final", FailureMode.ABORT, fail=False),
    ]

    pipeline = Pipeline(stages=stages, source_language="lug", on_stage_failure=FailureMode.SKIP)
    executor = PipelineExecutor(pipeline)

    result = executor.run(Result(source_language="lug"))

    # Pipeline should complete in a degraded/partial state with all warnings accumulated
    assert result.status in (ResultStatus.DEGRADED, ResultStatus.PARTIAL)
    assert result.is_usable is True
    assert len(result.warnings) >= 3


# ─── 5. DESERIALIZATION FUZZING & CORRUPTED INPUTS ───

def test_deserialization_fuzzing_resilience():
    """Test from_dict resilience against missing, malformed, or extra fields."""
    # Language with extra unknown keys
    lang = ld.Language.from_dict({
        "code": "lug",
        "name": "Luganda",
        "family": "Bantu",
        "resource_profile": "speech-moderate",
        "unknown_future_field": "test",
    })
    assert lang.code == "lug"

    # Segment with missing optional fields
    seg = ld.Segment.from_dict({
        "start": 0.0,
        "end": 1.5,
        "text": "Hello",
        "language": "eng",
    })
    assert seg.speaker is None
    assert seg.confidence is None

    # Resource with unknown fields
    res = ld.Resource.from_dict({
        "id": "res_001",
        "kind": "speech",
        "language": "lug",
        "version": "1.0",
        "extra_info": [1, 2, 3],
    })
    assert res.kind == ResourceKind.SPEECH
    assert res.has_consent is False


# ─── 6. MANIFEST SCANNER STRESS & ISOLATION ───

def test_manifest_scanner_heavy_directory_tree(tmp_path):
    """Test scanner traversal across a large nested directory tree with mixed manifests."""
    # Create 50 nested directories
    for i in range(50):
        sub = tmp_path / f"pkg_{i}" / "sub"
        sub.mkdir(parents=True, exist_ok=True)
        # Create a valid manifest in every 5th directory
        if i % 5 == 0:
            manifest_file = sub / "lingualdub.manifest.json"
            manifest_file.write_text(json.dumps({
                "name": f"ext_{i}",
                "version": "1.0.0",
                "entries": [
                    {
                        "kind": "component",
                        "key": f"comp_{i}",
                        "module": "pathlib",
                        "attr": "Path",
                        "version": "1.0.0"
                    }
                ]
            }))
        # Create a corrupted manifest in every 7th directory
        elif i % 7 == 0:
            corrupt = sub / "lingualdub.manifest.json"
            corrupt.write_text("{ corrupt json ...")

    registry = Registry()
    scanner = ManifestScanner(registry)
    count = scanner.scan(search_paths=[tmp_path])

    # Exactly 10 valid manifests loaded without crashing on the corrupt ones
    assert count == 10
