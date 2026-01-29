"""Test the mock printer driver."""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from PIL import Image

from custom_components.phomemo_d30.models import PrintJob
from custom_components.phomemo_d30.phomemo.driver import MockPhomemoDriver
from custom_components.phomemo_d30.phomemo.exceptions import FatalError, RecoverableError


def create_test_image():
    """Create a simple test image."""
    img = Image.new("RGB", (100, 100), color="white")
    return img


@pytest.mark.asyncio
async def test_mock_driver_connect():
    """Test mock driver connection."""
    with TemporaryDirectory() as tmpdir:
        driver = MockPhomemoDriver(
            save_path=tmpdir,
            print_delay=0.1,
        )

        await driver.connect()
        assert driver.is_connected()

        await driver.disconnect()
        assert not driver.is_connected()


@pytest.mark.asyncio
async def test_mock_driver_print_success():
    """Test successful print with mock driver."""
    with TemporaryDirectory() as tmpdir:
        driver = MockPhomemoDriver(
            save_path=tmpdir,
            print_delay=0.1,
        )

        await driver.connect()

        img = create_test_image()
        job = PrintJob(image=img, width=50, height=30)

        await driver.print(job)

        # Check that image was saved
        saved_files = list(Path(tmpdir).glob("*.png"))
        assert len(saved_files) == 1

        # Verify saved image can be loaded
        saved_img = Image.open(saved_files[0])
        assert saved_img.size == img.size


@pytest.mark.asyncio
async def test_mock_driver_print_delay():
    """Test mock driver respects print delay."""
    with TemporaryDirectory() as tmpdir:
        driver = MockPhomemoDriver(
            save_path=tmpdir,
            print_delay=0.5,
        )

        await driver.connect()

        img = create_test_image()
        job = PrintJob(image=img, width=50, height=30)

        start = asyncio.get_event_loop().time()
        await driver.print(job)
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed >= 0.5


@pytest.mark.asyncio
async def test_mock_driver_print_without_connection():
    """Test printing without connection raises error."""
    with TemporaryDirectory() as tmpdir:
        driver = MockPhomemoDriver(
            save_path=tmpdir,
            print_delay=0.1,
        )

        img = create_test_image()
        job = PrintJob(image=img, width=50, height=30)

        with pytest.raises(FatalError, match="not connected"):
            await driver.print(job)


@pytest.mark.asyncio
async def test_mock_driver_multiple_prints():
    """Test multiple prints save separate files."""
    with TemporaryDirectory() as tmpdir:
        driver = MockPhomemoDriver(
            save_path=tmpdir,
            print_delay=0.1,
        )

        await driver.connect()

        img = create_test_image()

        for i in range(3):
            job = PrintJob(image=img, width=50, height=30)
            await driver.print(job)

        saved_files = list(Path(tmpdir).glob("*.png"))
        assert len(saved_files) == 3


@pytest.mark.asyncio
async def test_mock_driver_failure_rate():
    """Test mock driver failure rate simulation."""
    with TemporaryDirectory() as tmpdir:
        # Test with 100% failure rate
        driver = MockPhomemoDriver(
            save_path=tmpdir,
            print_delay=0.1,
            failure_rate=1.0,
        )

        await driver.connect()

        img = create_test_image()
        job = PrintJob(image=img, width=50, height=30)

        # Should always fail with 100% failure rate
        with pytest.raises(RecoverableError, match="Simulated print failure"):
            await driver.print(job)

        # No files should be saved when print fails
        saved_files = list(Path(tmpdir).glob("*.png"))
        assert len(saved_files) == 0
