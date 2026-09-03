"""
Hugging Face translation adapter for NLLB, M2M100, or Sunbird models.
"""

from __future__ import annotations
import logging
from typing import Any, List, Optional, Union

from lingualdub.components.translation.base import TranslationComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment

logger = logging.getLogger(__name__)

# ISO 639-3 to NLLB language code mapping
NLLB_CODE_MAP = {
    "lug": "lug_Latn",
    "nyn": "nyn_Latn",
    "eng": "eng_Latn",
    "swa": "swh_Latn",
    "fra": "fra_Latn",
}


class HuggingFaceTranslationComponent(TranslationComponent):
    """
    Translation component wrapping Hugging Face Seq2Seq / NLLB models.
    """

    name: str = "hf_translator"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TRANSLATION
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa", "fra"]
    requires: List[str] = ["transcription"]
    provides: List[str] = ["translation"]
    on_failure: FailureMode = FailureMode.ABORT

    def __init__(
        self,
        model_name_or_path: str = "facebook/nllb-200-distilled-600M",
        source_language: str = "lug",
        target_language: str = "eng",
        device: Optional[str] = None,
        max_length: int = 512,
        version: str = "1.0.0",
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.source_language = source_language
        self.target_language = target_language
        self.device = device
        self.max_length = max_length
        self.version = version
        self._model = None
        self._tokenizer = None

    def _load_model(self) -> None:
        """Lazy load model and tokenizer."""
        if self._model is None:
            try:
                import torch
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "HuggingFaceTranslationComponent requires 'transformers' and 'torch'. "
                    "Install with: pip install torch transformers"
                ) from exc

            device = self.device
            if device is None:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"

            logger.info("Loading translation model %r on device %s", self.model_name_or_path, device)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name_or_path).to(device)

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(
                f"HuggingFaceTranslationComponent expects a Result input, got {type(input).__name__}"
            )

        if not input.segments:
            return Result(
                segments=[],
                source_language=input.source_language or self.source_language,
                target_language=self.target_language,
            )

        self._load_model()
        try:
            import torch
        except ImportError:
            torch = None

        src_lang_code = NLLB_CODE_MAP.get(self.source_language, self.source_language)
        tgt_lang_code = NLLB_CODE_MAP.get(self.target_language, self.target_language)

        translated_segments: List[Segment] = []
        texts = [s.text for s in input.segments]

        # Tokenize batch
        if hasattr(self._tokenizer, "src_lang"):
            self._tokenizer.src_lang = src_lang_code

        inputs = self._tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

        forced_bos_token_id = None
        if hasattr(self._tokenizer, "lang_code_to_id") and tgt_lang_code in self._tokenizer.lang_code_to_id:
            forced_bos_token_id = self._tokenizer.lang_code_to_id[tgt_lang_code]

        if torch is not None:
            with torch.no_grad():
                if forced_bos_token_id is not None:
                    generated = self._model.generate(
                        **inputs,
                        forced_bos_token_id=forced_bos_token_id,
                        max_length=self.max_length,
                    )
                else:
                    generated = self._model.generate(**inputs, max_length=self.max_length)
        else:
            if forced_bos_token_id is not None:
                generated = self._model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=self.max_length,
                )
            else:
                generated = self._model.generate(**inputs, max_length=self.max_length)

        decoded = self._tokenizer.batch_decode(generated, skip_special_tokens=True)

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
            },
        )
