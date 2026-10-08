from dataclasses import dataclass
from pathlib import Path

from services.ingest.service import validate_source


@dataclass
class PipelineResult:
    source: str
    status: str
    outputs: list[str]


def run_mvp(source: str) -> PipelineResult:
    """Phase-1 orchestration placeholder.

    The first implementation should connect:
    ingest -> transcription -> detection -> scoring -> clipping -> QC.
    """
    path = validate_source(source)

    # TODO:
    # 1. Transcribe with timestamps.
    # 2. Detect independent signals.
    # 3. Build context-complete candidate windows.
    # 4. Score/rank candidates.
    # 5. Render top clips with FFmpeg.
    # 6. Run QC.
    # 7. Write a manifest.

    return PipelineResult(
        source=str(path),
        status="scaffold_ready",
        outputs=[],
    )
