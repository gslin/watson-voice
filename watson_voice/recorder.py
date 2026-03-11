"""Audio recorder for voice input."""

import tempfile
import threading
import wave

import numpy as np
import sounddevice as sd

from .config import Config


class AudioRecorder:
    """Records audio from microphone. Stops when stop() is called."""

    def __init__(self, config: Config):
        self.sample_rate = config.sample_rate
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        """Start recording audio from the default microphone."""
        with self._lock:
            if self._recording:
                return
            self._recording = True
            self._frames = []

        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> str | None:
        """Stop recording and return path to the WAV file, or None if empty."""
        with self._lock:
            if not self._recording:
                return None
            self._recording = False

        if self._thread:
            self._thread.join(timeout=5)
        return self._save_wav()

    def _record_loop(self):
        frame_duration_ms = 30
        frame_size = int(self.sample_rate * frame_duration_ms / 1000)

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=frame_size,
            ) as stream:
                while self._recording:
                    data, _ = stream.read(frame_size)
                    self._frames.append(data.flatten().copy())
        except Exception as e:
            print(f"Recording error: {e}")
            self._recording = False

    def _save_wav(self) -> str | None:
        """Save recorded frames to a temporary WAV file."""
        if not self._frames:
            return None

        audio_data = np.concatenate(self._frames)
        # Skip if too short (less than 0.1s of audio)
        if len(audio_data) < self.sample_rate * 0.1:
            return None

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        return tmp.name
