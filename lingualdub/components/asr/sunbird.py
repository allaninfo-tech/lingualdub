"""
Sunbird AI ASR component adapter for Ugandan and East African languages.

Supports:
1. Local/Colab execution via Sunbird Hugging Face checkpoints (e.g. Sunbird/salt-asr-luganda,
   Sunbird/sunbird-asr-lug).
2. Direct Sunbird AI Cloud API execution if an API token (SUNBIRD_API_KEY) is configured.
"""

from __future__ import annotations
import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any, List, Optional, Union

from lingualdub.components.asr.base import ASRComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment

logger = logging.getLogger(__name__)

# Sunbird supported languages
SUNBIRD_SUPPORTED_LANGUAGES = ["lug", "nyn", "ach", "teo", "lgg", "eng"]


class SunbirdASRComponent(ASRComponent):
    """
    ASR component specifically tuned for Luganda and Ugandan languages using Sunbird AI.
    """

    name: str = "sunbird_asr"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    supported_languages: List[str] = SUNBIRD_SUPPORTED_LANGUAGES
    requires: List[str] = []
    provides: List[str] = ["transcription", "word_timestamps", "language_detection"]
    on_failure: FailureMode = FailureMode.ABORT

    def __init__(
        self,
        model_name_or_path: str = "Sunbird/salt-asr-luganda",
        api_key: Optional[str] = None,
        language: str = "lug",
        use_api: bool = False,
        device: Optional[str] = None,
        version: str = "1.0.0",
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.api_key = api_key or os.environ.get("SUNBIRD_API_KEY")
        self.language = language
        self.use_api = use_api
        self.device = device
        self.version = version
        self._pipeline = None

    def _get_hf_pipeline(self) -> Any:
        """Lazy load Sunbird model checkpoint via Hugging Face pipeline."""
        if self._pipeline is None:
            try:
                import torch
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "SunbirdASRComponent local execution requires 'transformers' and 'torch'. "
                    "Install with: pip install torch transformers"
                ) from exc

            device = self.device
            if device is None:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"

            logger.info("Loading Sunbird ASR model %r on device %s", self.model_name_or_path, device)
            self._pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_name_or_path,
                device=device,
                return_timestamps="word",
            )
        return self._pipeline

    def _run_api(self, audio_path: str) -> Result:
        """Execute transcription via Sunbird AI cloud API."""
        if not self.api_key:
            raise ValueError(
                "Sunbird API transcription requires an API key. Set SUNBIRD_API_KEY environment variable."
            )

        api_url = "https://api.sunbird.ai/tasks/stt"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        # Sunbird STT API call
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        req = urllib.request.Request(api_url, data=audio_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        text = data.get("text", "").strip()
        segments = [
            Segment(
                start=0.0,
                end=5.0,
                text=text,
                language=self.language,
                confidence=data.get("confidence", 0.92),
            )
        ]
        return Result(
            segments=segments,
            source_language=self.language,
            metadata={"provider": "sunbird_api", "model": self.model_name_or_path},
        )

    def run(self, input: Union[Result, Resource]) -> Result:
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
                f"Sunbird ASR audio path {audio_path!r} does not exist or was not specified."
            )

        if self.use_api and self.api_key:
            return self._run_api(audio_path)

        pipe = self._get_hf_pipeline()
        out = pipe(audio_path)

        segments: List[Segment] = []
        chunks = out.get("chunks", [])
        full_text = out.get("text", "").strip()

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
                            confidence=0.92,
                        )
                    )
        else:
            segments.append(
                Segment(
                    start=0.0,
                    end=5.0,
                    text=full_text,
                    language=source_lang,
                    confidence=0.92,
                )
            )

        return Result(
            segments=segments,
            source_language=source_lang,
            metadata={
                "provider": "sunbird_hf",
                "model": self.model_name_or_path,
                "audio_path": audio_path,
            },
        )
