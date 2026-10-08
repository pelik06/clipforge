from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    CREATED = "created"
    INGESTING = "ingesting"
    TRANSCRIBING = "transcribing"
    DETECTING = "detecting"
    SCORING = "scoring"
    CLIPPING = "clipping"
    QC = "qc"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    source: str
    status: JobStatus = JobStatus.CREATED
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
