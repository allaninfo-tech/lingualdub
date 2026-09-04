"""
Speaker similarity evaluator for voice-retention (Milestone 5).

Computes cosine similarity between two speaker embeddings and returns
a score in [0, 1] with full provenance. Registered via manifest.
"""

from __future__ import annotations

import math
from typing import List, Union

from lingualdub.components.eval.base import EvaluatorComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors (range [-1, 1])."""
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Embedding dimension mismatch: {len(vec_a)} vs {len(vec_b)}")
    if not vec_a:
        raise ValueError("Empty embedding vector")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _to_01_score(cosine: float) -> float:
    """
    Map cosine [-1, 1] to [0, 1] for reporting.

    Uses clipping: max(0, cosine) → identical 1.0, orthogonal 0.0, opposite 0.0.
    This matches M5 spec: identical →1.0, orthogonal →0.0.
    Raw cosine is also preserved in metadata for analysis.
    """
    # Clip to [0,1] — negative cosine treated as 0 (no similarity)
    return max(0.0, min(1.0, cosine))


class SpeakerSimilarityEvaluator(EvaluatorComponent):
    """
    Evaluates speaker similarity via cosine between two embeddings.

    Accepts two Results each carrying metadata["speaker_embedding"].
    Returns a Result with metadata["metrics"]["speaker_similarity"] in [0,1].
    """

    name: str = "speaker_similarity_evaluator"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.EVAL
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["speaker_embedding"]
    provides: List[str] = ["speaker_similarity_metrics"]
    on_failure: FailureMode = FailureMode.SKIP

    def __init__(self, version: str = "1.0.0") -> None:
        self.version = version

    def run(self, input: Union[Result, Resource]) -> Result:
        # Default run: if input is a Result with embedding, return it with metrics placeholder
        if isinstance(input, Result):
            if "speaker_embedding" in input.metadata:
                # Single-result evaluation not meaningful; return as-is
                return input
            return input
        return Result()

    def evaluate_pair(self, hypothesis: Result, reference: Union[Result, Resource]) -> Result:
        """
        Compute cosine similarity between hypothesis and reference embeddings.

        Args:
            hypothesis: Dubbed audio Result with speaker_embedding
            reference: Source audio Result (or Resource) with speaker_embedding.
                      If Resource, expects metadata["speaker_embedding"] or will
                      attempt to extract.

        Returns:
            Result with metadata["metrics"]["speaker_similarity"] in [0,1]
            and provenance["evaluator"].

        Raises:
            ValueError: if either embedding missing or dimension mismatch
        """
        # Extract hypothesis embedding
        hyp_emb = hypothesis.metadata.get("speaker_embedding")
        if hyp_emb is None:
            raise ValueError(
                "SpeakerSimilarityEvaluator: hypothesis Result missing metadata['speaker_embedding']. "
                "Run SpeakerEmbeddingComponent on both source and dubbed audio first."
            )

        # Extract reference embedding
        if isinstance(reference, Result):
            ref_emb = reference.metadata.get("speaker_embedding")
            if ref_emb is None:
                raise ValueError(
                    "SpeakerSimilarityEvaluator: reference Result missing metadata['speaker_embedding']. "
                    "Run SpeakerEmbeddingComponent on the reference audio first."
                )
            ref_provenance = reference.provenance
            ref_version = reference.provenance.get("speaker_encoder", "unknown")
        elif isinstance(reference, Resource):
            # Resource may carry embedding in metadata (pre-computed) or we error
            ref_emb = reference.metadata.get("speaker_embedding")
            if ref_emb is None:
                raise ValueError(
                    f"SpeakerSimilarityEvaluator: reference Resource {reference.id!r} missing speaker_embedding. "
                    "Provide a Result with embedding or a Resource with metadata['speaker_embedding']."
                )
            ref_provenance = reference.provenance
            ref_version = reference.provenance.get("speaker_encoder", "unknown")
        else:
            raise ValueError(f"Unsupported reference type: {type(reference).__name__}")

        # Validate types
        if not isinstance(hyp_emb, list) or not isinstance(ref_emb, list):
            raise ValueError("Embeddings must be lists of floats")

        cosine = _cosine_similarity(ref_emb, hyp_emb)
        score_01 = _to_01_score(cosine)

        # Round for reporting
        cosine_r = round(float(cosine), 4)
        score_r = round(float(score_01), 4)

        metrics = {
            "speaker_similarity": score_r,
            "cosine_similarity": cosine_r,
            "cosine_raw": cosine_r,
            "score_01": score_r,
            "embedding_dim": len(hyp_emb),
            "reference_embedding_dim": len(ref_emb),
        }

        # Provenance: merge hypothesis provenance, add evaluator, preserve dataset_version/protocol
        prov = dict(hypothesis.provenance)
        prov["evaluator"] = f"{self.name}@{self.version}"
        prov["speaker_similarity_model"] = f"{self.name}@{self.version}"
        # Preserve evaluation protocol/dataset version from reference if present
        if isinstance(reference, (Result, Resource)):
            if "dataset_version" in ref_provenance:
                prov["dataset_version"] = ref_provenance["dataset_version"]
            if "evaluation_protocol" in ref_provenance:
                prov["evaluation_protocol"] = ref_provenance["evaluation_protocol"]
            # Preserve speaker encoder versions
            if "speaker_encoder" in ref_provenance:
                prov["reference_speaker_encoder"] = ref_provenance["speaker_encoder"]
            if "speaker_encoder" in hypothesis.provenance:
                prov["hypothesis_speaker_encoder"] = hypothesis.provenance["speaker_encoder"]

        # Also store raw embeddings' provenance for reproducibility
        prov["hypothesis_embedding_source"] = hypothesis.metadata.get("speaker_model", "unknown")
        if isinstance(reference, Result):
            prov["reference_embedding_source"] = reference.metadata.get("speaker_model", "unknown")

        result = Result(
            segments=list(hypothesis.segments),
            source_language=hypothesis.source_language,
            target_language=hypothesis.target_language,
            warnings=list(hypothesis.warnings),
            provenance=prov,
            artifacts=list(hypothesis.artifacts),
            metadata={**hypothesis.metadata, "metrics": metrics, "speaker_similarity": metrics},
        )
        return result
