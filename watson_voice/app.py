"""Main daemon - listens on FIFO for commands from fcitx5 addon."""

import os
import signal
import subprocess
import threading

from .asr import ASREngine
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
        self.asr = ASREngine(config)
        self.recorder = AudioRecorder(config)
        self.typer = TextTyper(config)
        self._processing = False
        self._lock = threading.Lock()
        self._running = True

    def run(self):
        """Start the daemon."""
        print("Watson Voice Daemon")
        print(f"Model: {self.config.model_name}")
        print(f"Device: {self.config.device} ({self.config.compute_type})")
        print(f"Display: {self.config.display_server}")
        print(f"FIFO: {self.config.fifo_path}")
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
                # Open FIFO for reading; blocks until a writer opens it.
                # Re-opens automatically when the writer closes.
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
            self._start_recording()
        elif cmd == "stop":
            self._stop_and_transcribe()
        elif cmd == "cancel":
            self._cancel_recording()
        else:
            print(f"Unknown command: {cmd}")

    def _start_recording(self):
        """Start audio recording."""
        with self._lock:
            if self._processing:
                return
            # If already recording (e.g. rapid switch), stop first
            if self.recorder.is_recording:
                self.recorder.stop()

        print("Recording started...")
        self.recorder.start()

    def _stop_and_transcribe(self):
        """Stop recording and transcribe."""
        with self._lock:
            if self._processing:
                return
            if not self.recorder.is_recording:
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
            _notify("No speech", "No audio was captured.")
            with self._lock:
                self._processing = False

    def _cancel_recording(self):
        """Cancel recording without transcribing."""
        if self.recorder.is_recording:
            self.recorder.stop()
            print("Recording cancelled.")

    def _transcribe_and_type(self, audio_path: str):
        """Transcribe audio and type the result."""
        try:
            _notify("Recognizing...", "Processing speech...")
            text = self.asr.transcribe(audio_path)

            if text:
                self.typer.type_text(text)
                _notify("Done", text[:100])
            else:
                print("No speech detected in audio.")
                _notify("No speech detected")
        except Exception as e:
            print(f"Transcription error: {e}")
            _notify("Error", str(e)[:100])
        finally:
            with self._lock:
                self._processing = False
            try:
                os.unlink(audio_path)
            except OSError:
                pass

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self._running = False
        if self.recorder.is_recording:
            self.recorder.stop()
        # Clean up FIFO
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


def _is_fifo(path: str) -> bool:
    """Check if a path is a FIFO."""
    import stat

    try:
        return stat.S_ISFIFO(os.stat(path).st_mode)
    except OSError:
        return False
