"""ASR backend using Voxtral Mini — local model or Mistral API."""

import json
import time
import urllib.request
from io import BytesIO
from uuid import uuid4

from .config import Config

_API_URL = "https://api.mistral.ai/v1/audio/transcriptions"
_REPO_ID = "mistralai/Voxtral-Mini-4B-Realtime-2602"


class VoxtralASREngine:
    """Speech recognition engine using Voxtral (local or API)."""

    def __init__(self, config: Config):
        self.config = config
        self._use_api = bool(config.mistral_api_key)
        self._model = None
        self._processor = None

    def load(self):
        """Load the local model, or no-op for API mode."""
        if self._use_api:
            print("Voxtral backend ready (API mode)")
            return

        if self._model is not None:
            return

        import torch
        from transformers import (
            AutoProcessor,
            VoxtralRealtimeForConditionalGeneration,
        )

        print(f"Loading model: {_REPO_ID}")
        t0 = time.time()
        self._processor = AutoProcessor.from_pretrained(_REPO_ID)
        self._model = VoxtralRealtimeForConditionalGeneration.from_pretrained(
            _REPO_ID,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        elapsed = time.time() - t0
        print(f"Model loaded in {elapsed:.1f}s")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file."""
        if self._use_api:
            return self._transcribe_api(audio_path)
        return self._transcribe_local(audio_path)

    def _transcribe_local(self, audio_path: str) -> str:
        """Transcribe using the local model."""
        from mistral_common.tokens.tokenizers.audio import Audio

        if self._model is None:
            self.load()

        t0 = time.time()
        audio = Audio.from_file(audio_path, strict=False)
        audio.resample(self._processor.feature_extractor.sampling_rate)

        inputs = self._processor(audio.audio_array, return_tensors="pt")
        inputs = inputs.to(self._model.device, dtype=self._model.dtype)

        outputs = self._model.generate(**inputs)
        decoded = self._processor.batch_decode(outputs, skip_special_tokens=True)
        text = decoded[0].strip() if decoded else ""

        elapsed = time.time() - t0
        print(f"Transcription ({elapsed:.1f}s): {text}")
        return text

    def _transcribe_api(self, audio_path: str) -> str:
        """Transcribe via the Mistral API."""
        t0 = time.time()

        body, content_type = _build_multipart(
            audio_path,
            model="voxtral-mini-latest",
            language=self.config.language,
        )

        req = urllib.request.Request(
            _API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.mistral_api_key}",
                "Content-Type": content_type,
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        text = data.get("text", "").strip()
        elapsed = time.time() - t0
        print(f"Transcription ({elapsed:.1f}s): {text}")
        return text


def _build_multipart(
    audio_path: str,
    model: str,
    language: str,
) -> tuple[bytes, str]:
    """Build a multipart/form-data request body."""
    boundary = uuid4().hex

    parts = BytesIO()

    # model field
    parts.write(f"--{boundary}\r\n".encode())
    parts.write(b'Content-Disposition: form-data; name="model"\r\n\r\n')
    parts.write(f"{model}\r\n".encode())

    # language field
    parts.write(f"--{boundary}\r\n".encode())
    parts.write(b'Content-Disposition: form-data; name="language"\r\n\r\n')
    parts.write(f"{language}\r\n".encode())

    # file field
    parts.write(f"--{boundary}\r\n".encode())
    parts.write(
        b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
    )
    parts.write(b"Content-Type: audio/wav\r\n\r\n")
    with open(audio_path, "rb") as f:
        parts.write(f.read())
    parts.write(b"\r\n")

    # closing boundary
    parts.write(f"--{boundary}--\r\n".encode())

    content_type = f"multipart/form-data; boundary={boundary}"
    return parts.getvalue(), content_type
