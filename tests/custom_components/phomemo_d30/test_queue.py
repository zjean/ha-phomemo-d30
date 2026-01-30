"""Test the print queue manager."""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from PIL import Image

from custom_components.phomemo_d30.models import PrintJob, JobStatus
from custom_components.phomemo_d30.phomemo.exceptions import RecoverableError, FatalError
from custom_components.phomemo_d30.queue import PrintQueue


def create_test_image():
    """Create a simple test image."""
    return Image.new("RGB", (100, 100), color="white")


@pytest.mark.asyncio
async def test_queue_add_job():
    """Test adding a job to the queue."""
    driver = AsyncMock()
    queue = PrintQueue(driver, max_size=10, retry_attempts=3, retry_delay=1)

    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30)

    await queue.add_job(job)

    assert queue.size() == 1


@pytest.mark.asyncio
async def test_queue_process_job_success():
    """Test successful job processing."""
    driver = AsyncMock()
    driver.print = AsyncMock()

    queue = PrintQueue(driver, max_size=10, retry_attempts=3, retry_delay=0.1)

    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30)

    await queue.add_job(job)
    await queue.start()

    # Wait for processing
    await asyncio.sleep(0.2)
    await queue.stop()

    assert queue.size() == 0
    driver.print.assert_called_once_with(job)
    assert job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_queue_process_job_with_retry():
    """Test job retry on recoverable error."""
    driver = AsyncMock()

    # Fail twice, then succeed
    call_count = 0
    async def mock_print(job):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RecoverableError("Connection timeout")

    driver.print = mock_print

    queue = PrintQueue(driver, max_size=10, retry_attempts=3, retry_delay=0.1)

    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30, max_attempts=3)

    await queue.add_job(job)
    await queue.start()

    # Wait for retries
    await asyncio.sleep(1.0)
    await queue.stop()

    assert call_count == 3
    assert job.attempts == 2  # Only failed attempts are counted
    assert job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_queue_process_job_fatal_error():
    """Test job fails on fatal error."""
    driver = AsyncMock()
    driver.print = AsyncMock(side_effect=FatalError("Invalid image"))

    queue = PrintQueue(driver, max_size=10, retry_attempts=3, retry_delay=0.1)

    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30)

    await queue.add_job(job)
    await queue.start()

    # Wait for processing
    await asyncio.sleep(0.2)
    await queue.stop()

    assert job.status == JobStatus.FAILED
    assert job.error == "Invalid image"
    driver.print.assert_called_once()


@pytest.mark.asyncio
async def test_queue_max_retries_exceeded():
    """Test job fails after max retries."""
    driver = AsyncMock()
    driver.print = AsyncMock(side_effect=RecoverableError("Connection timeout"))

    queue = PrintQueue(driver, max_size=10, retry_attempts=3, retry_delay=0.1)

    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30, max_attempts=3)

    await queue.add_job(job)
    await queue.start()

    # Wait for all retries
    await asyncio.sleep(1.0)
    await queue.stop()

    assert job.status == JobStatus.FAILED
    assert job.attempts == 3
    assert "Connection timeout" in job.error


@pytest.mark.asyncio
async def test_queue_clear():
    """Test clearing the queue."""
    driver = AsyncMock()
    queue = PrintQueue(driver, max_size=10, retry_attempts=3, retry_delay=1)

    img = create_test_image()

    for i in range(3):
        job = PrintJob(image=img, width=50, height=30)
        await queue.add_job(job)

    assert queue.size() == 3

    await queue.clear()

    assert queue.size() == 0


@pytest.mark.asyncio
async def test_queue_stop():
    """Test stopping the queue."""
    driver = AsyncMock()
    driver.print = AsyncMock()

    queue = PrintQueue(driver, max_size=10, retry_attempts=3, retry_delay=1)

    await queue.start()
    assert queue.is_running()

    await queue.stop()
    assert not queue.is_running()
