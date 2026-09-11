# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Hugging Face Whisper / Sunbird ASR component adapter.

Supports running small models locally (e.g. openai/whisper-tiny) and large
multilingual / fine-tuned models on GPU/Colab (e.g. openai/whisper-large-v3,
Sunbird/salt-asr-luganda).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

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
    supported_languages: list[str] = ["lug", "nyn", "eng", "swa", "fra"]
    requires: list[str] = []
    provides: list[str] = ["transcription", "word_timestamps", "language_detection"]
    on_failure: FailureMode = FailureMode.ABORT

    def __init__(
        self,
        model_name_or_path: str = "openai/whisper-tiny",
        device: str | None = None,
        language: str | None = "lug",
        task: str = "transcribe",
        return_timestamps: bool | str = "word",
        version: str = "1.0.0",
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.device = device
        self.language = language
        self.asr_task = task
        self.return_timestamps = return_timestamps
        self.version = version
        self._pipeline: Any = None

    def _get_pipeline(self) -> Any:
        """Lazy load transformers pipeline only when run() is called."""
        if self._pipeline is None:
            try:
                import torch
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(  # justified: missing optional heavy dependency (torch/transformers) — not a framework error
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

            # FIX: Some fine-tuned whisper models have eos_token_id as a list
            # which breaks WhisperTimeStampLogitsProcessor (TypeError: slice indices must be integers)
            gen_config = getattr(self._pipeline.model, "generation_config", None)
            if (
                gen_config is not None
                and isinstance(gen_config.eos_token_id, list)
                and len(gen_config.eos_token_id) > 0
            ):
                gen_config.eos_token_id = gen_config.eos_token_id[0]

        return self._pipeline

    def run(self, input: Result | Resource) -> Result:
        # Determine audio path
        audio_path: str | None = None
        source_lang: str = self.language or "und"

        if isinstance(input, Resource):
            source_lang = input.language or self.language or "und"
            audio_path = str(input.path) if input.path else None
            if not audio_path and input.provenance.get("path"):
                audio_path = str(input.provenance["path"])
        elif isinstance(input, Result):
            source_lang = input.source_language or self.language or "und"
            if input.artifacts:
                audio_path = input.artifacts[0]

        if not audio_path or not Path(audio_path).exists():
            raise FileNotFoundError(  # justified: standard library file not found — caller expects built-in
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
        segments: list[Segment] = []
        full_text = out.get("text", "").strip()
        chunks = out.get("chunks", [])

        if chunks:
            for chunk in chunks:
                timestamp = chunk.get("timestamp", (0.0, 0.0))
                start = float(timestamp[0]) if timestamp[0] is not None else 0.0
                end = (
                    float(timestamp[1])
                    if (len(timestamp) > 1 and timestamp[1] is not None)
                    else start + 1.0
                )
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
