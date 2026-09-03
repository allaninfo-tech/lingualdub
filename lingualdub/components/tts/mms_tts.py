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

# ISO 639-3 to MMS-TTS model checkpoint mapping.
# Note: not all languages have dedicated MMS-TTS checkpoints.
# facebook/mms-tts-eng is used as a safe fallback.
MMS_TTS_MODELS = {
    "eng": "facebook/mms-tts-eng",
    "lug": "facebook/mms-tts-lug",
    "swa": "facebook/mms-tts-swh",
    # nyn (Runyankole) does not have a dedicated MMS-TTS checkpoint yet.
    # Components using nyn as TTS target should use "eng" or another model.
}

MMS_TTS_FALLBACK = "facebook/mms-tts-eng"


class MMSTTSComponent(TTSComponent):
    """
    TTS component wrapping Hugging Face VitsModel (Meta MMS-TTS).
    """

    name: str = "mms_tts"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TTS
    supported_languages: List[str] = ["eng", "lug", "swa"]
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
        # Resolve checkpoint: use explicit path, then language map, then fallback.
        if model_name_or_path:
            self.model_name_or_path = model_name_or_path
        elif language in MMS_TTS_MODELS:
            self.model_name_or_path = MMS_TTS_MODELS[language]
        else:
            logger.warning(
                "MMS-TTS: no checkpoint for language %r; falling back to %r.",
                language, MMS_TTS_FALLBACK,
            )
            self.model_name_or_path = MMS_TTS_FALLBACK
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
        try:
            import torch
        except ImportError:
            torch = None

        def _write_wav(dest: Path, rate: int, data: Any) -> None:
            try:
                import scipy.io.wavfile
                scipy.io.wavfile.write(str(dest), rate=rate, data=data)
            except ImportError:
                import struct
                import wave
                with wave.open(str(dest), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(rate)
                    int16_data = [int(max(-1.0, min(1.0, float(x))) * 32767.0) for x in data]
                    wf.writeframes(struct.pack(f"<{len(int16_data)}h", *int16_data))

        self.output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = list(input.artifacts)
        warnings = list(input.warnings)

        for idx, seg in enumerate(input.segments):
            text = (seg.text or "").strip()
            if not text:
                continue

            try:
                inputs = self._tokenizer(text, return_tensors="pt")
                if inputs["input_ids"].shape[-1] == 0:
                    continue

                inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

                if torch is not None:
                    with torch.no_grad():
                        output = self._model(**inputs).waveform
                else:
                    output = self._model(**inputs).waveform

                waveform = output.squeeze().cpu().numpy()
                sample_rate = self._model.config.sampling_rate
                out_file = self.output_dir / f"mms_{self.language}_seg_{idx}_{self.version}.wav"
                _write_wav(out_file, sample_rate, waveform)
                artifacts.append(str(out_file))
            except Exception as exc:
                logger.warning("MMS-TTS synthesis failed on segment #%d (%r): %s", idx, text, exc)
                warnings.append(f"MMS-TTS synthesis failed on segment #{idx}: {exc}")

        return Result(
            segments=list(input.segments),
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=warnings,
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
