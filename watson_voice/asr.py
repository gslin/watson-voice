"""ASR engine interface and faster-whisper backend."""

import time
from typing import Protocol

from faster_whisper import WhisperModel

from .config import Config


class ASRBackend(Protocol):
    """Protocol for ASR backends."""

    def load(self) -> None: ...

    def transcribe(self, audio_path: str) -> str: ...


class WhisperASREngine:
    """Speech recognition engine using faster-whisper."""

    def __init__(self, config: Config):
        self.config = config
        self._model = None

    def load(self):
        """Load the ASR model. Call this once at startup."""
        if self._model is not None:
            return
        print(f"Loading model: {self.config.model_name}")
        print(f"Device: {self.config.device}, Compute type: {self.config.compute_type}")
        t0 = time.time()
        self._model = WhisperModel(
            self.config.model_name,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )
        elapsed = time.time() - t0
        print(f"Model loaded in {elapsed:.1f}s")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file and return the recognized text."""
        if self._model is None:
            self.load()

        t0 = time.time()
        segments, info = self._model.transcribe(
            audio_path,
            language=self.config.language,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )
        texts = [segment.text.strip() for segment in segments]
        text = " ".join(t for t in texts if t)
        elapsed = time.time() - t0
        print(f"Transcription ({elapsed:.1f}s): {text}")
        return text
