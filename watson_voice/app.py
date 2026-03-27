"""Main daemon - listens on FIFO for commands from fcitx5 addon."""

import os
import signal
import subprocess
import threading

import opencc

from .config import Config
from .recorder import AudioRecorder
from .typer import TextTyper


def _notify(title: str, body: str = ""):
    """Send a desktop notification."""
    try:
        subprocess.run(
            ["notify-send", "-a", "Watson Voice", "-t", "2000", title, body],
            capture_output=True,
        )
    except FileNotFoundError:
        pass


class VoiceInputDaemon:
    """Daemon that listens on FIFO for start/stop commands from fcitx5 addon."""

    def __init__(self, config: Config):
        self.config = config
        self.asr = _create_asr_engine(config)
        self.recorder = AudioRecorder(config)
        self._s2t = opencc.OpenCC("s2t")
        self.typer = TextTyper(config.result_fifo_path)
        self._active = False  # Whether voice input mode is active
        self._processing = False
        self._lock = threading.Lock()
        self._running = True

    def run(self):
        """Start the daemon."""
        print("Watson Voice Daemon")
        print(f"Model: {self.config.model_name}")
        print(f"Device: {self.config.device} ({self.config.compute_type})")
        print(f"FIFO: {self.config.fifo_path}")
        print(f"Result FIFO: {self.config.result_fifo_path}")
        print()

        # Pre-load the model
        self.asr.load()

        # Set up FIFO
        self._setup_fifo()

        # Handle shutdown signals
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        print()
        print("Ready! Listening for commands from fcitx5 addon.")
        _notify("Watson Voice Ready", "Switch to '語音輸入' to start recording")

        # Main loop: read commands from FIFO
        self._listen_loop()

    def _setup_fifo(self):
        """Create the FIFO if it doesn't exist."""
        path = self.config.fifo_path
        if os.path.exists(path):
            if not _is_fifo(path):
                os.unlink(path)
                os.mkfifo(path)
        else:
            os.mkfifo(path)

    def _listen_loop(self):
        """Read commands from FIFO in a loop."""
        while self._running:
            try:
                with open(self.config.fifo_path, "r") as f:
                    for line in f:
                        cmd = line.strip()
                        if cmd:
                            self._handle_command(cmd)
                        if not self._running:
                            break
            except OSError as e:
                if self._running:
                    print(f"FIFO read error: {e}")

    def _handle_command(self, cmd: str):
        """Handle a command from the fcitx5 addon."""
        print(f"Command: {cmd}")

        if cmd == "start":
            self._activate()
        elif cmd == "stop":
            self._deactivate()
        elif cmd == "cancel":
            self._cancel()
        else:
            print(f"Unknown command: {cmd}")

    def _activate(self):
        """Activate voice input mode - start recording with auto-detection."""
        self._active = True
        self._start_recording()

    def _deactivate(self):
        """Deactivate voice input mode - stop and transcribe remaining audio."""
        self._active = False
        self._stop_and_transcribe()

    def _cancel(self):
        """Cancel everything."""
        self._active = False
        if self.recorder.is_recording:
            self.recorder.stop()
            print("Recording cancelled.")

    def _start_recording(self):
        """Start recording with silence detection."""
        with self._lock:
            if self._processing:
                return
            if self.recorder.is_recording:
                self.recorder.stop()

        print("Recording started...")
        self.recorder.start(on_silence=self._on_silence_detected)

    def _on_silence_detected(self):
        """Called by recorder when silence is detected after speech."""
        print("Auto-stop triggered by silence detection.")
        # Must not call stop()/join() from the recorder thread itself,
        # so handle transcription in a new thread.
        threading.Thread(target=self._do_transcribe, daemon=True).start()

    def _stop_and_transcribe(self):
        """Stop recording and transcribe (manual stop)."""
        with self._lock:
            if self._processing:
                return
            if not self.recorder.is_recording:
                return
        self._do_transcribe()

    def _do_transcribe(self):
        """Stop recorder and transcribe in a background thread."""
        with self._lock:
            if self._processing:
                return
            self._processing = True

        audio_path = self.recorder.stop()
        if audio_path:
            threading.Thread(
                target=self._transcribe_and_type,
                args=(audio_path,),
                daemon=True,
            ).start()
        else:
            print("No audio recorded.")
            with self._lock:
                self._processing = False
            # If still active, restart recording
            if self._active:
                self._start_recording()

    def _transcribe_and_type(self, audio_path: str):
        """Transcribe audio and type the result, then restart if still active."""
        try:
            text = self.asr.transcribe(audio_path)
            text = self._s2t.convert(text)

            if text:
                self.typer.type_text(text)
                print(f"Committed: {text}")
            else:
                print("No speech detected in audio.")
        except Exception as e:
            print(f"Transcription error: {e}")
        finally:
            with self._lock:
                self._processing = False
            try:
                os.unlink(audio_path)
            except OSError:
                pass

            # If still in voice input mode, restart recording for next utterance
            if self._active:
                print("Restarting recording...")
                self._start_recording()

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self._running = False
        self._active = False
        if self.recorder.is_recording:
            self.recorder.stop()
        try:
            os.unlink(self.config.fifo_path)
        except OSError:
            pass

    def cleanup(self):
        """Clean up resources."""
        try:
            os.unlink(self.config.fifo_path)
        except OSError:
            pass


def _create_asr_engine(config: Config):
    """Create the appropriate ASR engine based on config."""
    if config.backend == "voxtral":
        from .asr_voxtral import VoxtralASREngine

        return VoxtralASREngine(config)

    from .asr import WhisperASREngine

    return WhisperASREngine(config)


def _is_fifo(path: str) -> bool:
    """Check if a path is a FIFO."""
    import stat

    try:
        return stat.S_ISFIFO(os.stat(path).st_mode)
    except OSError:
        return False
