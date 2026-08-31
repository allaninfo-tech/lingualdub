"""
Meta MMS-TTS / VITS component adapter for high-quality speech synthesis.
"""

from __future__ import annotations
import logging
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Union

from lingualdub.components.tts.base import TTSComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result

logger = logging.getLogger(__name__)

# ISO 639-3 to MMS-TTS model checkpoint mapping
MMS_TTS_MODELS = {
    "eng": "facebook/mms-tts-eng",
    "lug": "facebook/mms-tts-lug",
    "nyn": "facebook/mms-tts-nyn",
    "swa": "facebook/mms-tts-swh",
}


class MMSTTSComponent(TTSComponent):
    """
    TTS component wrapping Hugging Face VitsModel (Meta MMS-TTS).
    """

    name: str = "mms_tts"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TTS
    supported_languages: List[str] = ["eng", "lug", "nyn", "swa"]
    requires: List[str] = ["translation"]
    provides: List[str] = ["synthesised_audio"]
    on_failure: FailureMode = FailureMode.DEGRADE

    def __init__(
        self,
        model_name_or_path: Optional[str] = None,
        language: str = "eng",
        output_dir: Optional[str] = None,
        device: Optional[str] = None,
        version: str = "1.0.0",
    ) -> None:
        self.language = language
        self.model_name_or_path = model_name_or_path or MMS_TTS_MODELS.get(language, "facebook/mms-tts-eng")
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "lingualdub_mms_tts"
        self.device = device
        self.version = version
        self._model = None
        self._tokenizer = None

    def _load_model(self) -> None:
        """Lazy load VitsModel & AutoTokenizer."""
        if self._model is None:
            try:
                import torch
                from transformers import AutoTokenizer, VitsModel
            except ImportError as exc:
                raise RuntimeError(
                    "MMSTTSComponent requires 'transformers', 'torch', and 'scipy'. "
                    "Install with: pip install torch transformers scipy soundfile"
                ) from exc

            device = self.device
            if device is None:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"

            logger.info("Loading MMS-TTS model %r on %s", self.model_name_or_path, device)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path)
            self._model = VitsModel.from_pretrained(self.model_name_or_path).to(device)

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(f"MMSTTSComponent expects a Result input, got {type(input).__name__}")

        if not input.segments:
            return Result(
                segments=[],
                source_language=input.source_language,
                target_language=input.target_language,
            )

        self._load_model()
        import scipy.io.wavfile
        import torch

        self.output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = list(input.artifacts)

        for idx, seg in enumerate(input.segments):
            if not seg.text or not seg.text.strip():
                continue

            inputs = self._tokenizer(seg.text, return_tensors="pt")
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

            with torch.no_grad():
                output = self._model(**inputs).waveform

            waveform = output.squeeze().cpu().numpy()
            sample_rate = self._model.config.sampling_rate
            out_file = self.output_dir / f"mms_{self.language}_seg_{idx}_{self.version}.wav"
            scipy.io.wavfile.write(str(out_file), rate=sample_rate, data=waveform)
            artifacts.append(str(out_file))

        return Result(
            segments=list(input.segments),
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=list(input.warnings),
            provenance=dict(input.provenance),
            artifacts=artifacts,
            metadata={
                **input.metadata,
                "tts_model": self.model_name_or_path,
            },
        )

    def degrade(self, input: Union[Result, Resource]) -> Result:
        """Degraded fallback if neural synthesis fails."""
        from lingualdub.components.tts.dummy import DummyTTSComponent
        dummy = DummyTTSComponent(output_dir=str(self.output_dir))
        res = dummy.degrade(input)
        res.mark_degraded(f"MMSTTSComponent ({self.model_name_or_path}) failed; fell back to dummy audio")
        return res
