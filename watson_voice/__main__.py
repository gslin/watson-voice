"""Entry point for watson-voice daemon."""

from .app import VoiceInputDaemon
from .config import parse_args


def main():
    config = parse_args()
    daemon = VoiceInputDaemon(config)
    try:
        daemon.run()
    finally:
        daemon.cleanup()


if __name__ == "__main__":
    main()
