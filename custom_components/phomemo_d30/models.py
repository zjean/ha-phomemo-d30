"""Data models for Phomemo D30 integration."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from PIL import Image

from .const import DEFAULT_DARKNESS


class JobStatus(str, Enum):
    """Print job status enum."""

    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class PrintJob:
    """Represents a print job."""

    image: Image.Image
    width: int
    height: int
    darkness: int = DEFAULT_DARKNESS
    rotate: int = 0
    max_attempts: int = 3

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    status: JobStatus = field(default=JobStatus.QUEUED)
    attempts: int = 0
    error: Optional[str] = None

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.attempts < self.max_attempts
