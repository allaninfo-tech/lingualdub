"""
Unit tests for neural adapters with mocked pipeline/model outputs.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from lingualdub.components.asr.sunbird import SunbirdASRComponent
from lingualdub.components.asr.whisper import WhisperASRComponent
from lingualdub.components.translation.sunbird import SunbirdTranslationComponent
from lingualdub.components.translation.hf_translator import HuggingFaceTranslationComponent
from lingualdub.components.tts.mms_tts import MMSTTSComponent
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


def test_sunbird_asr_mock_inference(tmp_path):
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"RIFFdummywav")

    asr = SunbirdASRComponent()
    mock_pipe = MagicMock()
    mock_pipe.return_value = {
        "text": "Oli otya nnyabo",
        "chunks": [
            {"timestamp": (0.0, 1.5), "text": "Oli otya"},
            {"timestamp": (1.5, 3.0), "text": "nnyabo"},
        ],
    }
    asr._pipeline = mock_pipe

    res = Resource(id="test_audio", kind=ResourceKind.SPEECH, language="lug", version="1.0", path=str(audio_file))
    out = asr.run(res)

    assert len(out.segments) == 2
    assert out.segments[0].text == "Oli otya"
    assert out.segments[1].text == "nnyabo"
    assert out.source_language == "lug"


def test_whisper_asr_mock_inference(tmp_path):
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"RIFFdummywav")

    asr = WhisperASRComponent(language="lug")
    mock_tensor = MagicMock()
    mock_tensor.to.return_value = mock_tensor
    mock_pipe = MagicMock()
    mock_pipe.return_value = {
        "text": "hello world",
        "chunks": [{"timestamp": (0.0, 2.0), "text": "hello world"}],
    }
    asr._pipeline = mock_pipe

    res = Resource(id="test_audio", kind=ResourceKind.SPEECH, language="lug", version="1.0", path=str(audio_file))
    out = asr.run(res)

    assert len(out.segments) == 1
    assert out.segments[0].text == "hello world"


def test_sunbird_translator_mock_inference():
    trans = SunbirdTranslationComponent(source_language="lug", target_language="eng")
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()

    mock_tensor = MagicMock()
    mock_tensor.to.return_value = mock_tensor
    mock_tokenizer.return_value = {"input_ids": mock_tensor}
    mock_tokenizer.batch_decode.return_value = ["how are you madam"]
    mock_model.generate.return_value = MagicMock()
    mock_model.device = "cpu"

    trans._model = mock_model
    trans._tokenizer = mock_tokenizer

    inp = Result(
        segments=[Segment(start=0.0, end=2.0, text="Oli otya nnyabo", language="lug")],
        source_language="lug",
    )
    out = trans.run(inp)

    assert len(out.segments) == 1
    assert out.segments[0].text == "how are you madam"
    assert out.segments[0].language == "eng"


def test_hf_translator_mock_inference():
    trans = HuggingFaceTranslationComponent(source_language="lug", target_language="eng")
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()

    mock_tensor = MagicMock()
    mock_tensor.to.return_value = mock_tensor
    mock_tokenizer.return_value = {"input_ids": mock_tensor}
    mock_tokenizer.batch_decode.return_value = ["good morning"]
    mock_model.generate.return_value = MagicMock()
    mock_model.device = "cpu"

    trans._model = mock_model
    trans._tokenizer = mock_tokenizer

    inp = Result(
        segments=[Segment(start=0.0, end=2.0, text="wasuze otya", language="lug")],
        source_language="lug",
    )
    out = trans.run(inp)

    assert len(out.segments) == 1
    assert out.segments[0].text == "good morning"
    assert out.segments[0].language == "eng"


def test_mms_tts_mock_inference(tmp_path):
    import numpy as np
    tts = MMSTTSComponent(output_dir=str(tmp_path))
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()

    mock_tensor = MagicMock()
    mock_tensor.to.return_value = mock_tensor
    mock_tensor.shape = [1, 5]
    mock_tokenizer.return_value = {"input_ids": mock_tensor}

    mock_output = MagicMock()
    mock_waveform = MagicMock()
    mock_waveform.squeeze.return_value.cpu.return_value.numpy.return_value = np.zeros(16000, dtype=np.float32)
    mock_output.waveform = mock_waveform
    mock_model.return_value = mock_output
    mock_model.config.sampling_rate = 16000
    mock_model.device = "cpu"

    tts._model = mock_model
    tts._tokenizer = mock_tokenizer

    inp = Result(
        segments=[Segment(start=0.0, end=1.0, text="hello", language="lug")],
        source_language="lug",
        target_language="lug",
    )
    out = tts.run(inp)
    assert len(out.artifacts) == 1
    assert Path(out.artifacts[0]).exists()
