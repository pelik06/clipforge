from dataclasses import dataclass


@dataclass
class QCResult:
    passed: bool
    checks: dict[str, bool]
    errors: list[str]


class QualityController:
    def check(self, video_path: str) -> QCResult:
        raise NotImplementedError
