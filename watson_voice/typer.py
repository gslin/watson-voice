"""Text input handler - types recognized text into the active application."""

import subprocess

from .config import Config


class TextTyper:
    """Commits recognized text to the focused application."""

    def __init__(self, config: Config):
        self.method = config.input_method
        self.display = config.display_server

    def type_text(self, text: str):
        """Type the given text into the currently focused application."""
        if not text:
            return

        if self.method == "clipboard":
            self._type_via_clipboard(text)
        elif self.method == "xdotool":
            self._type_via_xdotool(text)

    def _type_via_clipboard(self, text: str):
        """Copy text to clipboard and simulate paste."""
        if self.display == "wayland":
            # Wayland: wl-copy + wtype
            subprocess.run(
                ["wl-copy", "--", text],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["wtype", "-M", "ctrl", "-P", "v", "-p", "v", "-m", "ctrl"],
                check=True,
                capture_output=True,
            )
        else:
            # X11: xclip + xdotool
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                check=True,
                capture_output=True,
            )

    def _type_via_xdotool(self, text: str):
        """Type text directly via xdotool (X11 only)."""
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "10", "--", text],
            check=True,
            capture_output=True,
        )
