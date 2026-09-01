"""
Hugging Face Whisper / Sunbird ASR component adapter.

Supports running small models locally (e.g. openai/whisper-tiny) and large
multilingual / fine-tuned models on GPU/Colab (e.g. openai/whisper-large-v3,
Sunbird/salt-asr-luganda).
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, List, Optional, Union

from lingualdub.components.asr.base import ASRComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment

logger = logging.getLogger(__name__)


class WhisperASRComponent(ASRComponent):
    """
    ASR adapter using Hugging Face Transformers Whisper pipeline.
    """

    name: str = "whisper_asr"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa", "fra"]
    requires: List[str] = []
    provides: List[str] = ["transcription", "word_timestamps", "language_detection"]
    on_failure: FailureMode = FailureMode.ABORT

    def __init__(
        self,
        model_name_or_path: str = "openai/whisper-tiny",
        device: Optional[str] = None,
        language: Optional[str] = "lug",
        task: str = "transcribe",
        return_timestamps: Union[bool, str] = "word",
        version: str = "1.0.0",
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.device = device
        self.language = language
        self.asr_task = task
        self.return_timestamps = return_timestamps
        self.version = version
        self._pipeline = None

    def _get_pipeline(self) -> Any:
        """Lazy load transformers pipeline only when run() is called."""
        if self._pipeline is None:
            try:
                import torch
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "WhisperASRComponent requires 'transformers' and 'torch'. "
                    "Install with: pip install torch transformers"
                ) from exc

            device = self.device
            if device is None:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"

            logger.info("Loading ASR model %r on device %r", self.model_name_or_path, device)
            self._pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_name_or_path,
                device=device,
                # NOTE: return_timestamps="word" causes TypeError with newer transformers/Python 3.13.
                # Using True (chunk-level) which is stable across all versions.
                return_timestamps=True,
            )
        return self._pipeline

    def run(self, input: Union[Result, Resource]) -> Result:
        # Determine audio path
        audio_path: Optional[str] = None
        source_lang = self.language

        if isinstance(input, Resource):
            source_lang = input.language or self.language
            audio_path = str(input.path) if input.path else None
            if not audio_path and input.provenance.get("path"):
                audio_path = str(input.provenance["path"])
        elif isinstance(input, Result):
            source_lang = input.source_language or self.language
            if input.artifacts:
                audio_path = input.artifacts[0]

        if not audio_path or not Path(audio_path).exists():
            raise FileNotFoundError(
                f"ASR audio path {audio_path!r} does not exist or was not specified."
            )

        pipe = self._get_pipeline()
        generate_kwargs = {}
        if self.language:
            generate_kwargs["language"] = self.language
        if self.asr_task:
            generate_kwargs["task"] = self.asr_task

        out = pipe(audio_path, generate_kwargs=generate_kwargs)

        # Parse output into Segment objects
        segments: List[Segment] = []
        full_text = out.get("text", "").strip()
        chunks = out.get("chunks", [])

        if chunks:
            for chunk in chunks:
                timestamp = chunk.get("timestamp", (0.0, 0.0))
                start = float(timestamp[0]) if timestamp[0] is not None else 0.0
                end = float(timestamp[1]) if (len(timestamp) > 1 and timestamp[1] is not None) else start + 1.0
                text = chunk.get("text", "").strip()
                if text:
                    segments.append(
                        Segment(
                            start=start,
                            end=end,
                            text=text,
                            language=source_lang,
                            confidence=0.9,
                        )
                    )
        else:
            segments.append(
                Segment(
                    start=0.0,
                    end=5.0,
                    text=full_text,
                    language=source_lang,
                    confidence=0.9,
                )
            )

        return Result(
            segments=segments,
            source_language=source_lang,
            metadata={
                "model": self.model_name_or_path,
                "audio_path": audio_path,
            },
        )
