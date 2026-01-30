"""Print queue manager for Phomemo D30."""
import asyncio
import logging
from typing import Optional

from .models import PrintJob, JobStatus
from .phomemo.driver import PhomemoDriver
from .phomemo.exceptions import RecoverableError, FatalError

_LOGGER = logging.getLogger(__name__)


class PrintQueue:
    """Manages print job queue with retry logic."""

    def __init__(
        self,
        driver: PhomemoDriver,
        max_size: int = 50,
        retry_attempts: int = 3,
        retry_delay: float = 5.0,
    ):
        """Initialize print queue.

        Args:
            driver: Printer driver instance
            max_size: Maximum queue size
            retry_attempts: Number of retry attempts for recoverable errors
            retry_delay: Base delay between retries in seconds
        """
        self._driver = driver
        self._max_size = max_size
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay

        self._queue: asyncio.Queue[PrintJob] = asyncio.Queue(maxsize=max_size)
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def add_job(self, job: PrintJob) -> None:
        """Add a job to the queue.

        Args:
            job: Print job to add

        Raises:
            asyncio.QueueFull: If queue is full
        """
        job.status = JobStatus.QUEUED
        await self._queue.put(job)
        _LOGGER.debug("Added job %s to queue (size=%d)", job.id, self.size())

    async def start(self) -> None:
        """Start the queue worker."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        _LOGGER.info("Print queue started")

    async def stop(self) -> None:
        """Stop the queue worker."""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        _LOGGER.info("Print queue stopped")

    async def clear(self) -> None:
        """Clear all pending jobs from the queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        _LOGGER.info("Print queue cleared")

    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def is_running(self) -> bool:
        """Check if queue is running."""
        return self._running

    async def _process_queue(self) -> None:
        """Process jobs from the queue."""
        while self._running:
            try:
                job = await self._queue.get()
                await self._process_job(job)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.exception("Unexpected error in queue worker: %s", e)

    async def _process_job(self, job: PrintJob) -> None:
        """Process a single print job.

        Args:
            job: Job to process
        """
        _LOGGER.info("Processing job %s", job.id)
        job.status = JobStatus.PRINTING

        while True:
            try:
                await self._driver.print(job)
                job.status = JobStatus.COMPLETED
                _LOGGER.info("Job %s completed", job.id)
                break

            except RecoverableError as e:
                job.attempts += 1
                _LOGGER.warning(
                    "Job %s failed (attempt %d/%d): %s",
                    job.id,
                    job.attempts,
                    job.max_attempts,
                    e,
                )

                if not job.can_retry():
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    _LOGGER.error("Job %s failed after max retries", job.id)
                    break

                job.status = JobStatus.RETRYING
                delay = self._retry_delay * (2 ** (job.attempts - 1))
                await asyncio.sleep(delay)
                job.status = JobStatus.PRINTING

            except FatalError as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                _LOGGER.error("Job %s failed with fatal error: %s", job.id, e)
                break
