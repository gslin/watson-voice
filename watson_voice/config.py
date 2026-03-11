"""Configuration for watson-voice."""

import argparse
import os
from dataclasses import dataclass


@dataclass
class Config:
    # ASR model settings
    model_name: str = "SoybeanMilk/faster-whisper-Breeze-ASR-25"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "zh"

    # Audio recording settings
    sample_rate: int = 16000

    # FIFO path for fcitx5 addon communication
    fifo_path: str = ""

    # Text input method: "clipboard" (recommended) or "xdotool"
    input_method: str = "clipboard"

    # Display environment: "x11" or "wayland" (auto-detected)
    display_server: str = ""

    def __post_init__(self):
        if not self.display_server:
            self.display_server = _detect_display_server()
        if not self.fifo_path:
            self.fifo_path = _default_fifo_path()


def _detect_display_server() -> str:
    """Detect whether running on X11 or Wayland."""
    xdg_session = os.environ.get("XDG_SESSION_TYPE", "")
    if "wayland" in xdg_session.lower():
        return "wayland"
    if os.environ.get("WAYLAND_DISPLAY", ""):
        return "wayland"
    return "x11"


def _default_fifo_path() -> str:
    """Return the default FIFO path."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return os.path.join(runtime, "watson-voice.fifo")
    return f"/tmp/watson-voice-{os.getuid()}.fifo"


def parse_args() -> Config:
    """Parse command-line arguments into Config."""
    parser = argparse.ArgumentParser(
        description="Watson Voice - Voice input daemon for fcitx5"
    )
    parser.add_argument(
        "--model",
        default=Config.model_name,
        help="ASR model name or path (default: %(default)s)",
    )
    parser.add_argument(
        "--device",
        default=Config.device,
        choices=["cuda", "cpu"],
        help="Compute device (default: %(default)s)",
    )
    parser.add_argument(
        "--compute-type",
        default=Config.compute_type,
        choices=["float16", "int8_float16", "int8", "float32"],
        help="Compute type for inference (default: %(default)s)",
    )
    parser.add_argument(
        "--language",
        default=Config.language,
        help="Language code for ASR (default: %(default)s)",
    )
    parser.add_argument(
        "--input-method",
        default=Config.input_method,
        choices=["clipboard", "xdotool"],
        help="Text input method (default: %(default)s)",
    )
    parser.add_argument(
        "--display-server",
        default="",
        choices=["x11", "wayland", ""],
        help="Display server (auto-detected if empty)",
    )
    parser.add_argument(
        "--fifo-path",
        default="",
        help="FIFO path for fcitx5 addon communication (auto-determined)",
    )
    args = parser.parse_args()

    return Config(
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        input_method=args.input_method,
        display_server=args.display_server,
        fifo_path=args.fifo_path,
    )
