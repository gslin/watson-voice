"""Text input handler - sends recognized text back to fcitx5 addon."""

import os


class TextTyper:
    """Sends recognized text to fcitx5 addon via result FIFO."""

    def __init__(self, result_fifo_path: str):
        self.result_fifo_path = result_fifo_path

    def type_text(self, text: str):
        """Send text to fcitx5 addon for commitString()."""
        if not text:
            return

        print(f"Sending text to fcitx5: {text!r}")

        fd = os.open(self.result_fifo_path, os.O_WRONLY | os.O_NONBLOCK)
        try:
            msg = text + "\n"
            os.write(fd, msg.encode("utf-8"))
        finally:
            os.close(fd)

        print("Text sent successfully.")
