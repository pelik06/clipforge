from core.models.candidate import CandidateMoment


class MomentScorer:
    """Rank candidate moments using streamer-specific signals."""

    def score(self, candidates: list[CandidateMoment]) -> list[CandidateMoment]:
        raise NotImplementedError
