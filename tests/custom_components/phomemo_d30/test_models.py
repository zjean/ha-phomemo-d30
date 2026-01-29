"""Test the Phomemo D30 data models."""
from datetime import datetime
from io import BytesIO

import pytest
from PIL import Image

from custom_components.phomemo_d30.const import JOB_QUEUED, JOB_PRINTING, JOB_COMPLETED
from custom_components.phomemo_d30.models import PrintJob, JobStatus


def create_test_image():
    """Create a simple test image."""
    img = Image.new("RGB", (100, 100), color="white")
    return img


def test_print_job_creation():
    """Test creating a print job."""
    img = create_test_image()
    job = PrintJob(
        image=img,
        width=50,
        height=30,
    )

    assert job.id is not None
    assert len(job.id) == 36  # UUID length
    assert job.image == img
    assert job.width == 50
    assert job.height == 30
    assert job.darkness == 5  # default
    assert job.rotate == 0  # default
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.error is None
    assert isinstance(job.timestamp, datetime)


def test_print_job_with_custom_settings():
    """Test creating a job with custom settings."""
    img = create_test_image()
    job = PrintJob(
        image=img,
        width=60,
        height=40,
        darkness=7,
        rotate=90,
        max_attempts=5,
    )

    assert job.width == 60
    assert job.height == 40
    assert job.darkness == 7
    assert job.rotate == 90
    assert job.max_attempts == 5


def test_print_job_status_transitions():
    """Test job status state transitions."""
    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30)

    assert job.status == JobStatus.QUEUED

    job.status = JobStatus.PRINTING
    assert job.status == JobStatus.PRINTING

    job.status = JobStatus.COMPLETED
    assert job.status == JobStatus.COMPLETED


def test_print_job_increment_attempts():
    """Test incrementing job attempts."""
    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30, max_attempts=3)

    assert job.attempts == 0
    assert job.can_retry()

    job.attempts += 1
    assert job.attempts == 1
    assert job.can_retry()

    job.attempts += 1
    job.attempts += 1
    assert job.attempts == 3
    assert not job.can_retry()


def test_print_job_error_tracking():
    """Test job error tracking."""
    img = create_test_image()
    job = PrintJob(image=img, width=50, height=30)

    assert job.error is None

    job.error = "Connection timeout"
    assert job.error == "Connection timeout"
