from core.models.candidate import CandidateMoment


def test_candidate_duration():
    candidate = CandidateMoment(start=10.0, end=25.0)
    assert candidate.duration == 15.0
