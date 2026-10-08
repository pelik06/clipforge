from core.models.transcript import TranscriptSegment


class Transcriber:
    """Interface for a timestamped speech-to-text implementation."""

    def transcribe(self, media_path: str) -> list[TranscriptSegment]:
        raise NotImplementedError
