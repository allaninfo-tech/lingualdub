"""
Milestone 5 End-to-End Integration Test — Voice-Retention Evaluation.

Verifies M5 Done When:
  - Given source and dubbed audio, pipeline extracts speaker embeddings and returns cosine similarity with full provenance
  - Human evaluation protocol document is versioned
  - No voice without consent can reach speaker encoder
"""

import tempfile
from pathlib import Path

import pytest

from lingualdub.components.eval.speaker_similarity import SpeakerSimilarityEvaluator
from lingualdub.components.speaker.embedding import SpeakerEmbeddingComponent
from lingualdub.components.tts.dummy import _write_dummy_wav
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment
from lingualdub.pipeline.executor import PipelineExecutor


def _make_wav(path: Path, freq: float = 440.0):
    _write_dummy_wav(path, duration_sec=1.0, freq_hz=freq)


class TestM5VoiceRetentionE2E:
    def test_source_and_dubbed_similarity_with_provenance(self, tmp_path):
        """M5 Done When: source + dubbed → embeddings → similarity with provenance."""
        src_wav = tmp_path / "src.wav"
        dub_wav = tmp_path / "dub.wav"
        _make_wav(src_wav, freq=440)
        _make_wav(dub_wav, freq=440)  # same speaker → high similarity

        src_res = Resource(
            id="src_audio",
            kind=ResourceKind.SPEECH,
            language="lug",
            version="1.0.0",
            path=str(src_wav),
            provenance={"consent_basis": "research", "dataset_version": "1.0.0", "evaluation_protocol": "VOICE_RETENTION_MOS_V1"},
        )
        dub_res = Resource(
            id="dub_audio",
            kind=ResourceKind.SPEECH,
            language="eng",
            version="1.0.0",
            path=str(dub_wav),
            provenance={"consent_basis": "research", "dataset_version": "1.0.0", "evaluation_protocol": "VOICE_RETENTION_MOS_V1"},
        )

        embedder = SpeakerEmbeddingComponent()
        src_emb = embedder.run(src_res)
        dub_emb = embedder.run(dub_res)

        assert "speaker_embedding" in src_emb.metadata
        assert "speaker_embedding" in dub_emb.metadata
        assert src_emb.provenance["speaker_encoder"] == "speaker_embedding@1.0.0"

        evaluator = SpeakerSimilarityEvaluator()
        sim_result = evaluator.evaluate_pair(dub_emb, src_emb)

        assert "speaker_similarity" in sim_result.metadata["metrics"]
        assert 0 <= sim_result.metadata["metrics"]["speaker_similarity"] <= 1
        # Same audio → similarity 1.0
        assert sim_result.metadata["metrics"]["speaker_similarity"] == pytest.approx(1.0, abs=1e-6)
        assert "evaluator" in sim_result.provenance
        assert "speaker_similarity_evaluator" in sim_result.provenance["evaluator"]
        assert sim_result.provenance["dataset_version"] == "1.0.0"
        assert sim_result.provenance["evaluation_protocol"] == "VOICE_RETENTION_MOS_V1"

    def test_human_protocol_document_exists(self):
        """Human evaluation protocol must be versioned and complete."""
        proto_path = Path("docs/evaluation/voice_retention_protocol_v1.md")
        assert proto_path.exists(), "Protocol document missing"
        content = proto_path.read_text(encoding="utf-8")
        assert "VOICE_RETENTION_MOS_V1" in content
        assert "1.0.0" in content
        assert "How similar does the dubbed voice sound" in content
        assert "1–5" in content or "1-5" in content or "MOS" in content
        assert "Krippendorff" in content or "Alpha" in content
        assert "mean" in content.lower()
        assert "std" in content.lower()

    def test_no_consent_cannot_reach_encoder_via_resource(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        bad_res = Resource(
            id="bad",
            kind=ResourceKind.SPEECH,
            language="lug",
            version="1.0.0",
            path=str(wav),
            provenance={},  # no consent
        )
        comp = SpeakerEmbeddingComponent()
        with pytest.raises(ValueError, match="consent_basis"):
            comp.run(bad_res)

    def test_no_consent_cannot_reach_encoder_via_pipeline(self, tmp_path):
        """Pipeline execution must also enforce consent."""
        from lingualdub.components.asr.dummy import DummyASRComponent
        from lingualdub.components.translation.dummy import DummyTranslationComponent
        from lingualdub.components.tts.dummy import DummyTTSComponent

        tts_out = tmp_path / "tts"
        pipeline = Pipeline(
            stages=[
                DummyASRComponent(),
                DummyTranslationComponent(),
                DummyTTSComponent(output_dir=str(tts_out)),
                SpeakerEmbeddingComponent(),
            ],
            source_language="lug",
            target_language="eng",
        )
        executor = PipelineExecutor(pipeline)
        bad_res = Resource(id="bad", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", provenance={})
        with pytest.raises(Exception, match="consent_basis"):
            executor.run(bad_res)

    def test_no_consent_cannot_reach_encoder_via_result(self, tmp_path):
        wav = tmp_path / "audio.wav"
        _make_wav(wav)
        seg = Segment(start=0.0, end=1.0, text="hi", language="lug", speaker="spk1")
        bad_result = Result(
            segments=[seg],
            source_language="lug",
            provenance={},  # no consent
            artifacts=[str(wav)],
        )
        comp = SpeakerEmbeddingComponent()
        with pytest.raises(ValueError, match="consent_basis"):
            comp.run(bad_result)

    def test_pipeline_with_consent_succeeds(self, tmp_path):
        from lingualdub.components.asr.dummy import DummyASRComponent
        from lingualdub.components.translation.dummy import DummyTranslationComponent
        from lingualdub.components.tts.dummy import DummyTTSComponent

        tts_out = tmp_path / "tts"
        pipeline = Pipeline(
            stages=[
                DummyASRComponent(),
                DummyTranslationComponent(),
                DummyTTSComponent(output_dir=str(tts_out)),
                SpeakerEmbeddingComponent(),
            ],
            source_language="lug",
            target_language="eng",
        )
        executor = PipelineExecutor(pipeline)
        good_res = Resource(id="good", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", provenance={"consent_basis": "research"})
        result = executor.run(good_res)
        assert result.is_usable
        assert "speaker_embedding" in result.metadata
        assert result.provenance.get("consent_basis") == "research"

    def test_similarity_evaluator_registered(self):
        from lingualdub.cli import get_default_registry

        registry = get_default_registry()
        assert ("speaker_embedding", "1.0.0") in registry.list("component")
        assert ("speaker_similarity_evaluator", "1.0.0") in registry.list("component")
        assert ("speaker_encoder_dummy_v1", "1.0.0") in registry.list("resource")
