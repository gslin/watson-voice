"""Configuration for watson-voice."""

import argparse
import os
from dataclasses import dataclass


@dataclass
class Config:
    # ASR backend: "whisper", "voxtral", or "cohere"
    backend: str = "whisper"

    # ASR model settings (for whisper backend)
    model_name: str = "SoybeanMilk/faster-whisper-Breeze-ASR-25"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "zh"

    # Mistral API key (for voxtral backend, or MISTRAL_API_KEY env var)
    mistral_api_key: str = ""

    # Audio recording settings
    sample_rate: int = 16000

    # FIFO path for fcitx5 addon communication
    fifo_path: str = ""

    # FIFO path for sending results back to fcitx5 addon
    result_fifo_path: str = ""

    def __post_init__(self):
        if not self.fifo_path:
            self.fifo_path = _default_fifo_path()
        if not self.result_fifo_path:
            self.result_fifo_path = _default_result_fifo_path()


def _default_fifo_path() -> str:
    """Return the default FIFO path."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return os.path.join(runtime, "watson-voice.fifo")
    return f"/tmp/watson-voice-{os.getuid()}.fifo"


def _default_result_fifo_path() -> str:
    """Return the default result FIFO path."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return os.path.join(runtime, "watson-voice-result.fifo")
    return f"/tmp/watson-voice-result-{os.getuid()}.fifo"


def parse_args() -> Config:
    """Parse command-line arguments into Config."""
    parser = argparse.ArgumentParser(
        description="Watson Voice - Voice input daemon for fcitx5"
    )
    parser.add_argument(
        "--backend",
        default=Config.backend,
        choices=["whisper", "voxtral", "cohere"],
        help="ASR backend (default: %(default)s)",
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
        "--mistral-api-key",
        default="",
        help="Mistral API key for voxtral backend (or set MISTRAL_API_KEY env var)",
    )
    parser.add_argument(
        "--fifo-path",
        default="",
        help="FIFO path for fcitx5 addon communication (auto-determined)",
    )
    parser.add_argument(
        "--result-fifo-path",
        default="",
        help="Result FIFO path for sending text back to fcitx5 (auto-determined)",
    )
    args = parser.parse_args()

    mistral_key = args.mistral_api_key or os.environ.get("MISTRAL_API_KEY", "")

    return Config(
        backend=args.backend,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        mistral_api_key=mistral_key,
        fifo_path=args.fifo_path,
        result_fifo_path=args.result_fifo_path,
    )
