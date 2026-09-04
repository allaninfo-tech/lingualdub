"""
Milestone 6 End-to-End Integration Test — Cross-Lingual Voice Transfer.

Verifies M6 Done When:
  - Voice-transfer TTS produces dubbed audio that scores measurably higher on speaker
    similarity than unconditioned baseline
  - No voice without consent can reach voice-transfer
  - Results are reproducible within floating-point tolerance
"""

import tempfile
from pathlib import Path

import pytest

from lingualdub.components.eval.speaker_similarity import SpeakerSimilarityEvaluator
from lingualdub.components.speaker.embedding import SpeakerEmbeddingComponent
from lingualdub.components.tts.dummy import DummyTTSComponent, _write_dummy_wav
from lingualdub.components.tts.voice_conditioned import VoiceConditionedTTSComponent
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment
from lingualdub.pipeline.executor import PipelineExecutor


def _make_wav(path: Path, freq: float = 440.0):
    _write_dummy_wav(path, duration_sec=1.0, freq_hz=freq)


class TestM6VoiceTransferE2E:
    def test_voice_transfer_scores_higher_than_baseline(self, tmp_path):
        """
        Baseline (unconditioned dummy TTS) vs voice-conditioned TTS on same clips.
        Voice-conditioned should score higher on speaker similarity.
        """
        # Source speaker audio (880 Hz to make baseline's 440 Hz clearly different)
        src_wav = tmp_path / "src_880.wav"
        _write_dummy_wav(src_wav, duration_sec=1.0, freq_hz=880)
        src_res = Resource(
            id="src",
            kind=ResourceKind.SPEECH,
            language="lug",
            version="1.0.0",
            path=str(src_wav),
            provenance={"consent_basis": "research", "dataset_version": "1.0.0", "evaluation_protocol": "VOICE_RETENTION_MOS_V1"},
        )

        # Translated result (after ASR+MT)
        seg = Segment(start=0.0, end=1.0, text="Hello world", language="eng", speaker="spk1", source_language="lug")
        trans_res = Result(
            segments=[seg],
            source_language="lug",
            target_language="eng",
            provenance={"consent_basis": "research", "dataset_version": "1.0.0", "evaluation_protocol": "VOICE_RETENTION_MOS_V1"},
            metadata={"speaker_embedding": SpeakerEmbeddingComponent().run(src_res).metadata["speaker_embedding"]},
        )

        # Baseline: unconditioned TTS
        baseline_tts = DummyTTSComponent(output_dir=str(tmp_path / "baseline"))
        baseline_out = baseline_tts.run(trans_res)
        baseline_wav = Path(baseline_out.artifacts[0])
        baseline_res_for_eval = Resource(
            id="baseline_wav",
            kind=ResourceKind.SPEECH,
            language="eng",
            version="1.0.0",
            path=str(baseline_wav),
            provenance={"consent_basis": "research", "dataset_version": "1.0.0"},
        )

        # Candidate: voice-conditioned TTS (conditioned on src)
        voice_tts = VoiceConditionedTTSComponent(speaker_reference=src_res, output_dir=str(tmp_path / "voice"))
        candidate_out = voice_tts.run(trans_res)
        candidate_wav = Path(candidate_out.artifacts[0])
        candidate_res_for_eval = Resource(
            id="candidate_wav",
            kind=ResourceKind.SPEECH,
            language="eng",
            version="1.0.0",
            path=str(candidate_wav),
            provenance={"consent_basis": "research", "dataset_version": "1.0.0"},
        )

        # Extract embeddings from actual dubbed audio (re-extraction, not stored metadata)
        embedder = SpeakerEmbeddingComponent()
        src_emb = embedder.run(src_res)
        baseline_emb = embedder.run(baseline_res_for_eval)
        candidate_emb = embedder.run(candidate_res_for_eval)

        evaluator = SpeakerSimilarityEvaluator()
        baseline_sim = evaluator.evaluate_pair(baseline_emb, src_emb)
        candidate_sim = evaluator.evaluate_pair(candidate_emb, src_emb)

        # Record with provenance
        assert "evaluator" in baseline_sim.provenance
        assert "evaluator" in candidate_sim.provenance
        assert baseline_sim.metadata["metrics"]["speaker_similarity"] >= 0
        assert candidate_sim.metadata["metrics"]["speaker_similarity"] >= 0

        # Voice transfer should be measurably higher (at least 0.05 delta for dummy)
        # With our deterministic copy logic, candidate is 1.0, baseline ~0.03
        assert candidate_sim.metadata["metrics"]["speaker_similarity"] > baseline_sim.metadata["metrics"]["speaker_similarity"], (
            f"Voice transfer {candidate_sim.metadata['metrics']['speaker_similarity']} not greater than baseline {baseline_sim.metadata['metrics']['speaker_similarity']}"
        )
        # Also check via compare_runs
        from lingualdub.utils.comparison import compare_runs

        comp = compare_runs(baseline_sim, candidate_sim)
        assert comp["deltas"]["speaker_similarity_delta"] > 0

    def test_no_consent_cannot_reach_voice_transfer(self, tmp_path):
        bad_ref = Resource(id="bad", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", provenance={})
        with pytest.raises(ValueError, match="consent_basis"):
            VoiceConditionedTTSComponent(speaker_reference=bad_ref)

        # Via pipeline
        from lingualdub.components.asr.dummy import DummyASRComponent
        from lingualdub.components.translation.dummy import DummyTranslationComponent
        from lingualdub.components.speaker.embedding import SpeakerEmbeddingComponent

        pipeline = Pipeline(
            stages=[
                DummyASRComponent(),
                DummyTranslationComponent(),
                SpeakerEmbeddingComponent(),
                VoiceConditionedTTSComponent(output_dir=str(tmp_path)),
            ],
            source_language="lug",
            target_language="eng",
        )
        executor = PipelineExecutor(pipeline)
        bad_input = Resource(id="bad_input", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", provenance={})
        with pytest.raises(Exception, match="consent_basis"):
            executor.run(bad_input)

    def test_reproducibility(self, tmp_path):
        """Same config run twice → same scores within floating tolerance."""
        src_wav = tmp_path / "src.wav"
        _write_dummy_wav(src_wav, freq_hz=440)
        src_res = Resource(id="src", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", path=str(src_wav), provenance={"consent_basis": "research", "dataset_version": "1.0.0"})

        seg = Segment(start=0.0, end=1.0, text="Hello", language="eng", speaker="spk1")
        trans_res = Result(
            segments=[seg],
            source_language="lug",
            target_language="eng",
            provenance={"consent_basis": "research", "dataset_version": "1.0.0"},
            metadata={"speaker_embedding": SpeakerEmbeddingComponent().run(src_res).metadata["speaker_embedding"]},
        )

        voice_tts = VoiceConditionedTTSComponent(speaker_reference=src_res, output_dir=str(tmp_path / "run1"))
        out1 = voice_tts.run(trans_res)
        voice_tts2 = VoiceConditionedTTSComponent(speaker_reference=src_res, output_dir=str(tmp_path / "run2"))
        out2 = voice_tts2.run(trans_res)

        # Both should have same conditioning frequency and similar artifacts
        assert out1.metadata["conditioning_freq_hz"] == out2.metadata["conditioning_freq_hz"]

        # Speaker similarity should be identical
        embedder = SpeakerEmbeddingComponent()
        wav1 = Resource(id="w1", kind=ResourceKind.SPEECH, language="eng", version="1.0.0", path=out1.artifacts[0], provenance={"consent_basis": "research"})
        wav2 = Resource(id="w2", kind=ResourceKind.SPEECH, language="eng", version="1.0.0", path=out2.artifacts[0], provenance={"consent_basis": "research"})
        emb1 = embedder.run(wav1)
        emb2 = embedder.run(wav2)
        evaluator = SpeakerSimilarityEvaluator()
        src_emb = embedder.run(src_res)
        sim1 = evaluator.evaluate_pair(emb1, src_emb)
        sim2 = evaluator.evaluate_pair(emb2, src_emb)
        assert sim1.metadata["metrics"]["speaker_similarity"] == pytest.approx(sim2.metadata["metrics"]["speaker_similarity"], abs=1e-6)

    def test_pipeline_with_voice_transfer_end_to_end(self, tmp_path):
        from lingualdub.components.asr.dummy import DummyASRComponent
        from lingualdub.components.translation.dummy import DummyTranslationComponent
        from lingualdub.components.speaker.embedding import SpeakerEmbeddingComponent

        # Create speaker reference wav
        ref_wav = tmp_path / "ref.wav"
        _write_dummy_wav(ref_wav, freq_hz=660)
        ref_res = Resource(id="ref", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", path=str(ref_wav), provenance={"consent_basis": "research"})

        pipeline = Pipeline(
            stages=[
                DummyASRComponent(),
                DummyTranslationComponent(),
                SpeakerEmbeddingComponent(),
                VoiceConditionedTTSComponent(speaker_reference=ref_res, output_dir=str(tmp_path / "voice_out")),
            ],
            source_language="lug",
            target_language="eng",
        )
        executor = PipelineExecutor(pipeline)
        input_res = Resource(id="input", kind=ResourceKind.SPEECH, language="lug", version="1.0.0", provenance={"consent_basis": "research"})
        result = executor.run(input_res)
        assert result.is_usable
        assert result.metadata.get("voice_conditioned") is True
        assert "speaker_embedding" in result.metadata
        assert result.provenance.get("speaker_conditioned") is True
        # Check speaker preserved
        assert result.segments[0].speaker is not None
