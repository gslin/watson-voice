"""ASR backend using Cohere Transcribe — local model."""

import time

from .config import Config

_REPO_ID = "CohereLabs/cohere-transcribe-03-2026"


class CohereASREngine:
    """Speech recognition engine using Cohere Transcribe (local)."""

    def __init__(self, config: Config):
        self.config = config
        self._model = None
        self._processor = None

    def load(self):
        """Load the local model."""
        if self._model is not None:
            return

        import torch
        from transformers import AutoProcessor, CohereAsrForConditionalGeneration

        print(f"Loading model: {_REPO_ID}")
        t0 = time.time()
        self._processor = AutoProcessor.from_pretrained(_REPO_ID)
        self._model = CohereAsrForConditionalGeneration.from_pretrained(
            _REPO_ID,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        elapsed = time.time() - t0
        print(f"Model loaded in {elapsed:.1f}s")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file."""
        from transformers.audio_utils import load_audio

        if self._model is None:
            self.load()

        t0 = time.time()
        audio = load_audio(audio_path, sampling_rate=16000)
        inputs = self._processor(
            audio,
            sampling_rate=16000,
            return_tensors="pt",
            language=self.config.language,
        )
        inputs.to(self._model.device, dtype=self._model.dtype)

        outputs = self._model.generate(**inputs, max_new_tokens=256)
        text = self._processor.decode(outputs, skip_special_tokens=True)
        if isinstance(text, list):
            text = text[0]
        text = text.strip()

        elapsed = time.time() - t0
        print(f"Transcription ({elapsed:.1f}s): {text}")
        return text
