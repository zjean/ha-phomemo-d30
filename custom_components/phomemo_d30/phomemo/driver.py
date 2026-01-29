"""Phomemo printer drivers."""
import asyncio
import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import PrintJob
from .exceptions import FatalError, RecoverableError

_LOGGER = logging.getLogger(__name__)


class PhomemoDriver(ABC):
    """Abstract base class for Phomemo printer drivers."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the printer."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the printer."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to printer."""

    @abstractmethod
    async def print(self, job: PrintJob) -> None:
        """Print a job."""


class MockPhomemoDriver(PhomemoDriver):
    """Mock printer driver for testing."""

    def __init__(
        self,
        save_path: str,
        print_delay: float = 2.0,
        failure_rate: float = 0.0,
    ):
        """Initialize mock driver.

        Args:
            save_path: Directory to save printed images
            print_delay: Simulated print delay in seconds
            failure_rate: Probability of random failure (0.0-1.0)
        """
        self._save_path = Path(save_path)
        self._print_delay = print_delay
        self._failure_rate = failure_rate
        self._connected = False

        # Create save directory if it doesn't exist
        self._save_path.mkdir(parents=True, exist_ok=True)

    async def connect(self) -> None:
        """Connect to the mock printer."""
        _LOGGER.debug("Mock driver: connecting")
        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected = True
        _LOGGER.info("Mock driver: connected")

    async def disconnect(self) -> None:
        """Disconnect from the mock printer."""
        _LOGGER.debug("Mock driver: disconnecting")
        self._connected = False
        _LOGGER.info("Mock driver: disconnected")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    async def print(self, job: PrintJob) -> None:
        """Print a job (save image to disk).

        Args:
            job: Print job to execute

        Raises:
            FatalError: If not connected or print fails
            RecoverableError: If simulated failure occurs
        """
        if not self._connected:
            raise FatalError("Mock driver not connected")

        _LOGGER.info(
            "Mock driver: printing job %s (width=%d, height=%d)",
            job.id,
            job.width,
            job.height,
        )

        # Simulate printing delay
        await asyncio.sleep(self._print_delay)

        # Simulate random failures if failure_rate is set
        if self._failure_rate > 0:
            if random.random() < self._failure_rate:
                raise RecoverableError(f"Simulated print failure (failure_rate={self._failure_rate})")

        # Save image with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"print_{timestamp}_{job.id[:8]}.png"
        filepath = self._save_path / filename

        job.image.save(filepath)

        _LOGGER.info("Mock driver: saved print to %s", filepath)
