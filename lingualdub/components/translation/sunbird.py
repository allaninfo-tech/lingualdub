"""
Sunbird AI Translation adapter for Ugandan and East African languages.

Specialized in Luganda (lug), Runyankole (nyn), Acholi (ach), Ateso (teo),
Lugbara (lgg), and English (eng).
"""

from __future__ import annotations
import json
import logging
import os
import urllib.request
from typing import Any, List, Optional, Union

from lingualdub.components.translation.base import TranslationComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment

logger = logging.getLogger(__name__)

# Sunbird language code aliases
SUNBIRD_LANG_CODES = {
    "lug": "Luganda",
    "nyn": "Runyankole",
    "ach": "Acholi",
    "teo": "Ateso",
    "lgg": "Lugbara",
    "eng": "English",
}


class SunbirdTranslationComponent(TranslationComponent):
    """
    Translation component using Sunbird AI specialized Ugandan multilingual models or API.
    """

    name: str = "sunbird_translator"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TRANSLATION
    supported_languages: List[str] = ["lug", "nyn", "ach", "teo", "lgg", "eng"]
    requires: List[str] = ["transcription"]
    provides: List[str] = ["translation"]
    on_failure: FailureMode = FailureMode.ABORT

    def __init__(
        self,
        model_name_or_path: str = "Sunbird/sunbird-mul-en",
        source_language: str = "lug",
        target_language: str = "eng",
        api_key: Optional[str] = None,
        use_api: bool = False,
        device: Optional[str] = None,
        version: str = "1.0.0",
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.source_language = source_language
        self.target_language = target_language
        self.api_key = api_key or os.environ.get("SUNBIRD_API_KEY")
        self.use_api = use_api
        self.device = device
        self.version = version
        self._model = None
        self._tokenizer = None

    def _load_model(self) -> None:
        """Lazy load Hugging Face model and tokenizer."""
        if self._model is None:
            try:
                import torch
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "SunbirdTranslationComponent requires 'transformers' and 'torch'. "
                    "Install with: pip install torch transformers"
                ) from exc

            device = self.device
            if device is None:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"

            logger.info("Loading translation model %r on device %s", self.model_name_or_path, device)
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path)
                self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name_or_path).to(device)
            except Exception as exc:
                fallback_model = "facebook/nllb-200-distilled-600M"
                logger.warning(
                    "Failed to load %r (%s). Falling back to public model %r.",
                    self.model_name_or_path, exc, fallback_model,
                )
                self.model_name_or_path = fallback_model
                self._tokenizer = AutoTokenizer.from_pretrained(fallback_model)
                self._model = AutoModelForSeq2SeqLM.from_pretrained(fallback_model).to(device)

    def _translate_api(self, texts: List[str]) -> List[str]:
        """Translate via Sunbird AI cloud API."""
        if not self.api_key:
            raise ValueError("Sunbird API translation requires an API key in SUNBIRD_API_KEY.")

        api_url = "https://api.sunbird.ai/tasks/nmt"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        src_name = SUNBIRD_LANG_CODES.get(self.source_language, "Luganda")
        tgt_name = SUNBIRD_LANG_CODES.get(self.target_language, "English")

        payload = {
            "source_language": src_name,
            "target_language": tgt_name,
            "text": "\n".join(texts),
        }

        req = urllib.request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        out_text = data.get("text", "")
        return [t.strip() for t in out_text.split("\n")] if out_text else texts

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(f"SunbirdTranslationComponent expects a Result input, got {type(input).__name__}")

        if not input.segments:
            return Result(
                segments=[],
                source_language=input.source_language or self.source_language,
                target_language=self.target_language,
            )

        texts = [s.text for s in input.segments]

        if self.use_api and self.api_key:
            decoded = self._translate_api(texts)
        else:
            self._load_model()
            # Target language mapping for NLLB / multilingual Seq2Seq
            nllb_map = {
                "lug": "lug_Latn",
                "nyn": "nyn_Latn",
                "eng": "eng_Latn",
                "swa": "swh_Latn",
                "ach": "ach_Latn",
            }
            src_code = nllb_map.get(self.source_language, self.source_language)
            tgt_code = nllb_map.get(self.target_language, self.target_language)

            if hasattr(self._tokenizer, "src_lang"):
                self._tokenizer.src_lang = src_code

            inputs = self._tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

            forced_bos = None
            if hasattr(self._tokenizer, "lang_code_to_id") and tgt_code in self._tokenizer.lang_code_to_id:
                forced_bos = self._tokenizer.lang_code_to_id[tgt_code]
            elif hasattr(self._tokenizer, "convert_tokens_to_ids"):
                tid = self._tokenizer.convert_tokens_to_ids(tgt_code)
                if tid and tid != self._tokenizer.unk_token_id:
                    forced_bos = tid

            try:
                import torch
            except ImportError:
                torch = None

            if torch is not None:
                with torch.no_grad():
                    if forced_bos is not None:
                        generated = self._model.generate(**inputs, forced_bos_token_id=forced_bos, max_length=512)
                    else:
                        generated = self._model.generate(**inputs, max_length=512)
            else:
                if forced_bos is not None:
                    generated = self._model.generate(**inputs, forced_bos_token_id=forced_bos, max_length=512)
                else:
                    generated = self._model.generate(**inputs, max_length=512)

            decoded = self._tokenizer.batch_decode(generated, skip_special_tokens=True)

        translated_segments: List[Segment] = []
        for s, trans in zip(input.segments, decoded):
            translated_segments.append(
                Segment(
                    start=s.start,
                    end=s.end,
                    text=trans.strip(),
                    language=self.target_language,
                    source_language=s.language or self.source_language,
                    speaker=s.speaker,
                    confidence=s.confidence,
                    metadata=dict(s.metadata),
                )
            )

        return Result(
            segments=translated_segments,
            source_language=input.source_language or self.source_language,
            target_language=self.target_language,
            warnings=list(input.warnings),
            provenance=dict(input.provenance),
            artifacts=list(input.artifacts),
            metadata={
                **input.metadata,
                "translation_model": self.model_name_or_path,
                "translation_provider": "sunbird_api" if (self.use_api and self.api_key) else "sunbird_hf",
            },
        )
