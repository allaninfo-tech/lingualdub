from transformers import pipeline, GenerationConfig
import os

pipe = pipeline("automatic-speech-recognition", model="openai/whisper-small", return_timestamps=True, device="cpu")
# Overwrite model config with list eos_token_id to simulate the bug
pipe.model.generation_config.eos_token_id = [50257]
try:
    pipe("data/samples/sample_lug.wav", generate_kwargs={"task": "transcribe"})
    print("Success without eos_token_id kwarg")
except Exception as e:
    print("Failed without eos_token_id kwarg:", repr(e))

try:
    pipe("data/samples/sample_lug.wav", generate_kwargs={"task": "transcribe", "eos_token_id": 50257})
    print("Success WITH eos_token_id kwarg=50257")
except Exception as e:
    print("Failed WITH eos_token_id kwarg=50257:", repr(e))

