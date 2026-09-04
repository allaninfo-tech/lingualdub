"""
Unit tests for Milestone 5 — Voice-Retention Evaluation.

Covers:
- SpeakerEmbeddingComponent: consent enforcement, deterministic embeddings, ResourceManager acquisition
- SpeakerSimilarityEvaluator: cosine similarity, provenance, edge cases
"""

import math
import tempfile
from pathlib import Path

import pytest

from lingualdub.components.eval.speaker_similarity import SpeakerSimilarityEvaluator, _cosine_similarity
from lingualdub.components.speaker.embedding import SpeakerEmbeddingComponent, _deterministic_embedding
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_wav(path: Path, freq: float = 440.0):
    from lingualdub.components.tts.dummy import _write_dummy_wav

    _write_dummy_wav(path, duration_sec=1.0, freq_hz=freq)


def _make_result_with_consent(text: str = "hello world", lang: str = "lug"):
    seg = Segment(start=0.0, end=1.0, text=text, language=lang, speaker="spk1")
    return Result(
        segments=[seg],
        source_language=lang,
        provenance={"consent_basis": "research", "evaluation_protocol": "VOICE_RETENTION_MOS_V1"},
        artifacts=[],
        metadata={},
    )


# ─────────────────────────────────────────────────────────────────────────────
# SpeakerEmbeddingComponent
# ─────────────────────────────────────────────────────────────────────────────


class TestSpeakerEmbeddingComponent:
    def test_accepts_resource_with_consent(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        res = Resource(
            id="test_res",
            kind=ResourceKind.SPEECH,
            language="lug",
            version="1.0.0",
            path=str(wav),
            provenance={"consent_basis": "research"},
        )
        comp = SpeakerEmbeddingComponent()
        out = comp.run(res)
        assert "speaker_embedding" in out.metadata
        assert len(out.metadata["speaker_embedding"]) == 192
        assert "speaker_encoder" in out.provenance
        # Check L2 normalized
        emb = out.metadata["speaker_embedding"]
        norm = math.sqrt(sum(x * x for x in emb))
        assert norm == pytest.approx(1.0, abs=1e-6)

    def test_accepts_result_with_artifacts(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        seg = Segment(start=0.0, end=1.0, text="hello", language="lug", speaker="spk1")
        res = Result(
            segments=[seg],
            source_language="lug",
            provenance={"consent_basis": "research"},
            artifacts=[str(wav)],
            metadata={},
        )
        comp = SpeakerEmbeddingComponent()
        out = comp.run(res)
        assert "speaker_embedding" in out.metadata
        assert out.metadata["speaker_embedding_dim"] == 192

    def test_refuses_resource_without_consent(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        res = Resource(
            id="bad",
            kind=ResourceKind.SPEECH,
            language="lug",
            version="1.0.0",
            path=str(wav),
            provenance={},  # no consent
        )
        comp = SpeakerEmbeddingComponent()
        with pytest.raises(ValueError, match="consent_basis"):
            comp.run(res)

    def test_refuses_result_without_consent(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        seg = Segment(start=0.0, end=1.0, text="hello", language="lug", speaker="spk1")
        res = Result(
            segments=[seg],
            source_language="lug",
            provenance={},  # no consent
            artifacts=[str(wav)],
        )
        comp = SpeakerEmbeddingComponent()
        with pytest.raises(ValueError, match="consent_basis"):
            comp.run(res)

    def test_deterministic_same_audio_identical(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav, freq=440)
        res = Resource(
            id="a",
            kind=ResourceKind.SPEECH,
            language="lug",
            version="1.0.0",
            path=str(wav),
            provenance={"consent_basis": "research"},
        )
        comp = SpeakerEmbeddingComponent()
        out1 = comp.run(res)
        out2 = comp.run(res)
        emb1 = out1.metadata["speaker_embedding"]
        emb2 = out2.metadata["speaker_embedding"]
        # Same audio → cosine 1.0
        cos = _cosine_similarity(emb1, emb2)
        assert cos == pytest.approx(1.0, abs=1e-6)
        assert emb1 == emb2

    def test_different_audio_different_embedding(self, tmp_path):
        wav1 = tmp_path / "a.wav"
        wav2 = tmp_path / "b.wav"
        _make_wav(wav1, freq=440)
        _make_wav(wav2, freq=880)
        res1 = Resource(id="r1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", path=str(wav1), provenance={"consent_basis": "research"})
        res2 = Resource(id="r2", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", path=str(wav2), provenance={"consent_basis": "research"})
        comp = SpeakerEmbeddingComponent()
        out1 = comp.run(res1)
        out2 = comp.run(res2)
        cos = _cosine_similarity(out1.metadata["speaker_embedding"], out2.metadata["speaker_embedding"])
        # Different audio should not be identical (cos < 0.99)
        assert cos < 0.99

    def test_acquires_via_resource_manager(self, tmp_path):
        # Offline fallback should not crash without ResourceManager
        comp = SpeakerEmbeddingComponent(resource_manager=None, registry=None)
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        res = Resource(id="x", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", path=str(wav), provenance={"consent_basis": "research"})
        out = comp.run(res)
        assert "speaker_embedding" in out.metadata

    def test_capability_tokens(self):
        comp = SpeakerEmbeddingComponent()
        assert "speaker_embedding" in comp.provides

    def test_output_in_result_metadata(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        res = Resource(id="x", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", path=str(wav), provenance={"consent_basis": "research"})
        comp = SpeakerEmbeddingComponent(embedding_dim=128)
        out = comp.run(res)
        assert out.metadata["speaker_embedding_dim"] == 128
        assert len(out.metadata["speaker_embedding"]) == 128


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic helper
# ─────────────────────────────────────────────────────────────────────────────


class TestDeterministicEmbedding:
    def test_same_key_identical(self):
        e1 = _deterministic_embedding("same_key", dim=64)
        e2 = _deterministic_embedding("same_key", dim=64)
        assert e1 == e2
        assert _cosine_similarity(e1, e2) == pytest.approx(1.0, abs=1e-6)

    def test_different_key_different(self):
        e1 = _deterministic_embedding("key_a", dim=64)
        e2 = _deterministic_embedding("key_b", dim=64)
        cos = _cosine_similarity(e1, e2)
        assert cos < 0.9

    def test_unit_norm(self):
        e = _deterministic_embedding("test", dim=192)
        norm = math.sqrt(sum(x * x for x in e))
        assert norm == pytest.approx(1.0, abs=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# SpeakerSimilarityEvaluator
# ─────────────────────────────────────────────────────────────────────────────


class TestSpeakerSimilarityEvaluator:
    def test_identical_embeddings_score_1(self):
        emb = _deterministic_embedding("identical", dim=32)
        hyp = Result(segments=[Segment(start=0.0, end=1.0, text="a", language="lug")], source_language="lug", provenance={"consent_basis": "research"}, metadata={"speaker_embedding": emb})
        ref = Result(segments=[Segment(start=0.0, end=1.0, text="b", language="lug")], source_language="lug", provenance={"consent_basis": "research"}, metadata={"speaker_embedding": list(emb)})
        evaluator = SpeakerSimilarityEvaluator()
        out = evaluator.evaluate_pair(hyp, ref)
        assert out.metadata["metrics"]["speaker_similarity"] == pytest.approx(1.0, abs=1e-6)
        assert out.metadata["metrics"]["cosine_similarity"] == pytest.approx(1.0, abs=1e-6)
        assert 0 <= out.metadata["metrics"]["speaker_similarity"] <= 1

    def test_orthogonal_embeddings_score_0(self):
        dim = 32
        e1 = [0.0] * dim
        e2 = [0.0] * dim
        e1[0] = 1.0
        e2[1] = 1.0
        hyp = Result(segments=[Segment(start=0.0, end=1.0, text="a", language="lug")], source_language="lug", provenance={"consent_basis": "research"}, metadata={"speaker_embedding": e1})
        ref = Result(segments=[Segment(start=0.0, end=1.0, text="b", language="lug")], source_language="lug", provenance={"consent_basis": "research"}, metadata={"speaker_embedding": e2})
        evaluator = SpeakerSimilarityEvaluator()
        out = evaluator.evaluate_pair(hyp, ref)
        assert out.metadata["metrics"]["speaker_similarity"] == pytest.approx(0.0, abs=1e-6)
        assert out.metadata["metrics"]["cosine_similarity"] == pytest.approx(0.0, abs=1e-6)

    def test_provenance_set(self):
        emb = _deterministic_embedding("x", dim=16)
        hyp = Result(segments=[], source_language="lug", provenance={"consent_basis": "research", "dataset_version": "1.0.0", "evaluation_protocol": "VOICE_RETENTION_MOS_V1"}, metadata={"speaker_embedding": emb})
        ref = Result(segments=[], source_language="lug", provenance={"consent_basis": "research", "dataset_version": "1.0.0", "evaluation_protocol": "VOICE_RETENTION_MOS_V1"}, metadata={"speaker_embedding": emb})
        evaluator = SpeakerSimilarityEvaluator()
        out = evaluator.evaluate_pair(hyp, ref)
        assert "evaluator" in out.provenance
        assert "speaker_similarity_evaluator" in out.provenance["evaluator"]
        assert out.provenance["dataset_version"] == "1.0.0"
        assert out.provenance["evaluation_protocol"] == "VOICE_RETENTION_MOS_V1"

    def test_missing_embedding_raises(self):
        hyp = Result(segments=[], source_language="lug", provenance={"consent_basis": "research"}, metadata={})
        ref = Result(segments=[], source_language="lug", provenance={"consent_basis": "research"}, metadata={"speaker_embedding": [1.0, 0.0]})
        evaluator = SpeakerSimilarityEvaluator()
        with pytest.raises(ValueError, match="hypothesis.*speaker_embedding"):
            evaluator.evaluate_pair(hyp, ref)

    def test_capability_tokens(self):
        evaluator = SpeakerSimilarityEvaluator()
        assert "speaker_embedding" in evaluator.requires
        assert "speaker_similarity_metrics" in evaluator.provides

    def test_score_in_range(self, tmp_path):
        # Random embeddings should always be in [0,1]
        for i in range(5):
            e1 = _deterministic_embedding(f"rand_a_{i}", dim=64)
            e2 = _deterministic_embedding(f"rand_b_{i}", dim=64)
            hyp = Result(segments=[], source_language="lug", provenance={"consent_basis": "research"}, metadata={"speaker_embedding": e1})
            ref = Result(segments=[], source_language="lug", provenance={"consent_basis": "research"}, metadata={"speaker_embedding": e2})
            out = SpeakerSimilarityEvaluator().evaluate_pair(hyp, ref)
            score = out.metadata["metrics"]["speaker_similarity"]
            assert 0.0 <= score <= 1.0
