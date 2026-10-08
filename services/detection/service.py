from core.models.candidate import CandidateMoment


class SignalDetector:
    """Collect independent signals that can indicate an interesting moment."""

    def detect(self, media_path: str) -> list[CandidateMoment]:
        raise NotImplementedError
