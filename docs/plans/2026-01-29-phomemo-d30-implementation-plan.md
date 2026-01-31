# Phomemo D30 Home Assistant Integration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Home Assistant custom integration that receives label images via MQTT and prints to Phomemo D30 via Bluetooth with mock mode support.

**Architecture:** HA custom component with MQTT listener, async print queue, Bluetooth/mock driver, and sensor entities. Config flow for UI setup, supports both YAML and UI configuration.

**Tech Stack:** Python 3.11+, Home Assistant, MQTT, Bluetooth, Pillow, vivier/phomemo-tools (vendored)

---

## Task 1: Development Environment Setup

**Files:**
- Create: `.devcontainer/devcontainer.json`
- Create: `requirements_dev.txt`
- Create: `pytest.ini`

**Step 1: Create dev container configuration**

Create `.devcontainer/devcontainer.json`:
```json
{
  "name": "Home Assistant Development",
  "image": "ghcr.io/home-assistant/devcontainer:latest",
  "appPort": ["9123:8123"],
  "postCreateCommand": "container install",
  "extensions": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter"
  ],
  "mounts": [
    "source=${localWorkspaceFolder},target=/workspaces/label-printer,type=bind"
  ],
  "workspaceFolder": "/workspaces/label-printer"
}
```

**Step 2: Create development requirements**

Create `requirements_dev.txt`:
```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-homeassistant-custom-component==0.13.87
black==23.12.1
ruff==0.1.9
Pillow==10.1.0
```

**Step 3: Create pytest configuration**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

**Step 4: Create test directory structure**

Run:
```bash
mkdir -p tests/custom_components/phomemo_d30
touch tests/__init__.py
touch tests/custom_components/__init__.py
touch tests/custom_components/phomemo_d30/__init__.py
```

**Step 5: Commit**

```bash
git add .devcontainer/ requirements_dev.txt pytest.ini tests/
git commit -m "feat: setup development environment

- Add VS Code dev container for HA development
- Configure pytest for async testing
- Create test directory structure"
```

---

## Task 2: Core Integration Structure

**Files:**
- Create: `custom_components/phomemo_d30/__init__.py`
- Create: `custom_components/phomemo_d30/manifest.json`
- Create: `custom_components/phomemo_d30/const.py`
- Test: `tests/custom_components/phomemo_d30/test_init.py`

**Step 1: Write test for integration setup**

Create `tests/custom_components/phomemo_d30/test_init.py`:
```python
"""Test the Phomemo D30 integration setup."""
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.phomemo_d30.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "mode": "mock",
            "mqtt_topic": "homeassistant/phomemo/print",
            "darkness": 5,
            "retry_attempts": 3,
            "retry_delay": 5,
            "mock_print_delay": 2,
            "mock_save_path": "/tmp/phomemo_test",
        },
        title="Phomemo D30",
    )


async def test_setup_entry(hass: HomeAssistant, mock_config_entry):
    """Test integration setup from config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data


async def test_unload_entry(hass: HomeAssistant, mock_config_entry):
    """Test integration unload."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
    assert DOMAIN not in hass.data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_init.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'custom_components.phomemo_d30'"

**Step 3: Create constants file**

Create `custom_components/phomemo_d30/const.py`:
```python
"""Constants for the Phomemo D30 integration."""

DOMAIN = "phomemo_d30"

# Config keys
CONF_MODE = "mode"
CONF_BLUETOOTH_MAC = "bluetooth_mac"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_DARKNESS = "darkness"
CONF_SPEED = "speed"
CONF_RETRY_ATTEMPTS = "retry_attempts"
CONF_RETRY_DELAY = "retry_delay"
CONF_QUEUE_MAX_SIZE = "queue_max_size"
CONF_MOCK_PRINT_DELAY = "mock_print_delay"
CONF_MOCK_SAVE_PATH = "mock_save_path"

# Defaults
DEFAULT_MQTT_TOPIC = "homeassistant/phomemo/print"
DEFAULT_DARKNESS = 5
DEFAULT_SPEED = "normal"
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 5
DEFAULT_QUEUE_MAX_SIZE = 50
DEFAULT_MOCK_PRINT_DELAY = 2
DEFAULT_MOCK_SAVE_PATH = "/config/phomemo_test_prints"

# Modes
MODE_BLUETOOTH = "bluetooth"
MODE_MOCK = "mock"

# Printer states
STATE_IDLE = "idle"
STATE_PRINTING = "printing"
STATE_ERROR = "error"
STATE_DISCONNECTED = "disconnected"

# Job states
JOB_QUEUED = "queued"
JOB_PRINTING = "printing"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"
JOB_RETRYING = "retrying"

# Platforms
PLATFORMS = ["sensor"]
```

**Step 4: Create manifest file**

Create `custom_components/phomemo_d30/manifest.json`:
```json
{
  "domain": "phomemo_d30",
  "name": "Phomemo D30 Label Printer",
  "codeowners": ["@janwiebe"],
  "config_flow": true,
  "dependencies": ["mqtt", "bluetooth"],
  "documentation": "https://github.com/janwiebe/ha-phomemo-d30",
  "iot_class": "local_push",
  "requirements": ["Pillow==10.1.0"],
  "version": "0.1.0"
}
```

**Step 5: Create integration __init__.py with setup/unload**

Create `custom_components/phomemo_d30/__init__.py`:
```python
"""The Phomemo D30 Label Printer integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Phomemo D30 from a config entry."""
    _LOGGER.debug("Setting up Phomemo D30 integration")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Phomemo D30 integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_init.py -v`
Expected: PASS (both test_setup_entry and test_unload_entry)

**Step 7: Commit**

```bash
git add custom_components/phomemo_d30/ tests/
git commit -m "feat: add core integration structure

- Define domain constants and configuration keys
- Implement async setup and unload
- Add manifest for HACS compatibility
- Test setup and unload flows"
```

---

## Task 3: Print Job Data Model

**Files:**
- Create: `custom_components/phomemo_d30/models.py`
- Test: `tests/custom_components/phomemo_d30/test_models.py`

**Step 1: Write test for PrintJob model**

Create `tests/custom_components/phomemo_d30/test_models.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'custom_components.phomemo_d30.models'"

**Step 3: Create models module**

Create `custom_components/phomemo_d30/models.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_models.py -v`
Expected: PASS (all tests pass)

**Step 5: Commit**

```bash
git add custom_components/phomemo_d30/models.py tests/
git commit -m "feat: add print job data model

- Define PrintJob dataclass with image and metadata
- Add JobStatus enum for state tracking
- Support retry logic with attempt counting
- Include error tracking"
```

---

## Task 4: Mock Printer Driver

**Files:**
- Create: `custom_components/phomemo_d30/phomemo/__init__.py`
- Create: `custom_components/phomemo_d30/phomemo/driver.py`
- Create: `custom_components/phomemo_d30/phomemo/exceptions.py`
- Test: `tests/custom_components/phomemo_d30/test_mock_driver.py`

**Step 1: Write test for mock driver**

Create `tests/custom_components/phomemo_d30/test_mock_driver.py`:
```python
"""Test the mock printer driver."""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from PIL import Image

from custom_components.phomemo_d30.models import PrintJob
from custom_components.phomemo_d30.phomemo.driver import MockPhomemoDriver
from custom_components.phomemo_d30.phomemo.exceptions import FatalError


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_mock_driver.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create exceptions module**

Create `custom_components/phomemo_d30/phomemo/__init__.py`:
```python
"""Phomemo printer driver package."""
```

Create `custom_components/phomemo_d30/phomemo/exceptions.py`:
```python
"""Exceptions for Phomemo printer driver."""


class PhomemoError(Exception):
    """Base exception for Phomemo driver."""


class RecoverableError(PhomemoError):
    """Recoverable error that can be retried."""


class FatalError(PhomemoError):
    """Fatal error that cannot be retried."""


class ConnectionError(RecoverableError):
    """Connection-related error."""
```

**Step 4: Create mock driver**

Create `custom_components/phomemo_d30/phomemo/driver.py`:
```python
"""Phomemo printer drivers."""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import PrintJob
from .exceptions import FatalError

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

        # Save image with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"print_{timestamp}_{job.id[:8]}.png"
        filepath = self._save_path / filename

        job.image.save(filepath)

        _LOGGER.info("Mock driver: saved print to %s", filepath)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_mock_driver.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add custom_components/phomemo_d30/phomemo/ tests/
git commit -m "feat: add mock printer driver

- Define abstract PhomemoDriver interface
- Implement MockPhomemoDriver for testing
- Support simulated print delays
- Save printed images to disk for inspection
- Add custom exception hierarchy"
```

---

## Task 5: Print Queue Manager

**Files:**
- Create: `custom_components/phomemo_d30/queue.py`
- Test: `tests/custom_components/phomemo_d30/test_queue.py`

**Step 1: Write test for print queue**

Create `tests/custom_components/phomemo_d30/test_queue.py`:
```python
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

    assert call_count == 3
    assert job.attempts == 3
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_queue.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create queue manager**

Create `custom_components/phomemo_d30/queue.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_queue.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/phomemo_d30/queue.py tests/
git commit -m "feat: add print queue manager

- Implement async queue with worker task
- Support retry logic with exponential backoff
- Handle recoverable and fatal errors
- Add queue control methods (start/stop/clear)
- Track job status transitions"
```

---

## Task 6: MQTT Message Parser

**Files:**
- Create: `custom_components/phomemo_d30/mqtt_handler.py`
- Test: `tests/custom_components/phomemo_d30/test_mqtt_handler.py`

**Step 1: Write test for MQTT message parser**

Create `tests/custom_components/phomemo_d30/test_mqtt_handler.py`:
```python
"""Test MQTT message handling."""
import base64
from io import BytesIO

import pytest
from PIL import Image

from custom_components.phomemo_d30.mqtt_handler import parse_mqtt_message, MQTTParseError


def create_test_image_base64():
    """Create a base64-encoded test image."""
    img = Image.new("RGB", (100, 100), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_parse_valid_message():
    """Test parsing valid MQTT message."""
    image_b64 = create_test_image_base64()
    message = {
        "image": image_b64,
        "width": 50,
        "height": 30,
    }

    job = parse_mqtt_message(message, max_attempts=3)

    assert job.width == 50
    assert job.height == 30
    assert job.darkness == 5  # default
    assert job.rotate == 0  # default
    assert job.image.size == (100, 100)


def test_parse_message_with_optional_fields():
    """Test parsing message with optional fields."""
    image_b64 = create_test_image_base64()
    message = {
        "image": image_b64,
        "width": 60,
        "height": 40,
        "darkness": 7,
        "rotate": 90,
    }

    job = parse_mqtt_message(message, max_attempts=3)

    assert job.width == 60
    assert job.height == 40
    assert job.darkness == 7
    assert job.rotate == 90


def test_parse_message_missing_image():
    """Test parsing message without image field."""
    message = {
        "width": 50,
        "height": 30,
    }

    with pytest.raises(MQTTParseError, match="Missing required field: image"):
        parse_mqtt_message(message)


def test_parse_message_missing_width():
    """Test parsing message without width field."""
    image_b64 = create_test_image_base64()
    message = {
        "image": image_b64,
        "height": 30,
    }

    with pytest.raises(MQTTParseError, match="Missing required field: width"):
        parse_mqtt_message(message)


def test_parse_message_missing_height():
    """Test parsing message without height field."""
    image_b64 = create_test_image_base64()
    message = {
        "image": image_b64,
        "width": 50,
    }

    with pytest.raises(MQTTParseError, match="Missing required field: height"):
        parse_mqtt_message(message)


def test_parse_message_invalid_base64():
    """Test parsing message with invalid base64."""
    message = {
        "image": "not-valid-base64!!!",
        "width": 50,
        "height": 30,
    }

    with pytest.raises(MQTTParseError, match="Invalid base64 image data"):
        parse_mqtt_message(message)


def test_parse_message_invalid_image_data():
    """Test parsing message with invalid image data."""
    invalid_data = base64.b64encode(b"not an image").decode()
    message = {
        "image": invalid_data,
        "width": 50,
        "height": 30,
    }

    with pytest.raises(MQTTParseError, match="Cannot decode image"):
        parse_mqtt_message(message)


def test_parse_message_invalid_darkness():
    """Test parsing message with out-of-range darkness."""
    image_b64 = create_test_image_base64()
    message = {
        "image": image_b64,
        "width": 50,
        "height": 30,
        "darkness": 10,  # Out of range
    }

    with pytest.raises(MQTTParseError, match="Darkness must be between 1 and 7"):
        parse_mqtt_message(message)


def test_parse_message_invalid_rotate():
    """Test parsing message with invalid rotation."""
    image_b64 = create_test_image_base64()
    message = {
        "image": image_b64,
        "width": 50,
        "height": 30,
        "rotate": 45,  # Not a valid rotation
    }

    with pytest.raises(MQTTParseError, match="Rotate must be 0, 90, 180, or 270"):
        parse_mqtt_message(message)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_mqtt_handler.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create MQTT handler module**

Create `custom_components/phomemo_d30/mqtt_handler.py`:
```python
"""MQTT message handling for Phomemo D30."""
import base64
import logging
from io import BytesIO
from typing import Any, Dict

from PIL import Image

from .const import DEFAULT_DARKNESS
from .models import PrintJob

_LOGGER = logging.getLogger(__name__)


class MQTTParseError(Exception):
    """Error parsing MQTT message."""


def parse_mqtt_message(
    message: Dict[str, Any],
    max_attempts: int = 3,
) -> PrintJob:
    """Parse MQTT message into a PrintJob.

    Args:
        message: MQTT message payload as dict
        max_attempts: Maximum retry attempts for the job

    Returns:
        PrintJob instance

    Raises:
        MQTTParseError: If message is invalid
    """
    # Validate required fields
    if "image" not in message:
        raise MQTTParseError("Missing required field: image")
    if "width" not in message:
        raise MQTTParseError("Missing required field: width")
    if "height" not in message:
        raise MQTTParseError("Missing required field: height")

    # Decode base64 image
    try:
        image_data = base64.b64decode(message["image"])
    except Exception as e:
        raise MQTTParseError(f"Invalid base64 image data: {e}")

    # Load image
    try:
        image = Image.open(BytesIO(image_data))
    except Exception as e:
        raise MQTTParseError(f"Cannot decode image: {e}")

    # Parse dimensions
    try:
        width = int(message["width"])
        height = int(message["height"])
    except (ValueError, TypeError) as e:
        raise MQTTParseError(f"Invalid dimensions: {e}")

    # Parse optional fields
    darkness = message.get("darkness", DEFAULT_DARKNESS)
    rotate = message.get("rotate", 0)

    # Validate darkness
    if not isinstance(darkness, int) or not 1 <= darkness <= 7:
        raise MQTTParseError("Darkness must be between 1 and 7")

    # Validate rotation
    if rotate not in [0, 90, 180, 270]:
        raise MQTTParseError("Rotate must be 0, 90, 180, or 270")

    _LOGGER.debug(
        "Parsed MQTT message: width=%d, height=%d, darkness=%d, rotate=%d",
        width,
        height,
        darkness,
        rotate,
    )

    return PrintJob(
        image=image,
        width=width,
        height=height,
        darkness=darkness,
        rotate=rotate,
        max_attempts=max_attempts,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_mqtt_handler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/phomemo_d30/mqtt_handler.py tests/
git commit -m "feat: add MQTT message parser

- Parse base64-encoded images from MQTT
- Validate required and optional fields
- Support darkness and rotation settings
- Provide clear error messages for invalid data"
```

---

## Task 7: Coordinator with MQTT and Queue Integration

**Files:**
- Modify: `custom_components/phomemo_d30/__init__.py`
- Create: `custom_components/phomemo_d30/coordinator.py`
- Test: `tests/custom_components/phomemo_d30/test_coordinator.py`

**Step 1: Write test for coordinator**

Create `tests/custom_components/phomemo_d30/test_coordinator.py`:
```python
"""Test the coordinator."""
import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from PIL import Image

from custom_components.phomemo_d30.coordinator import PhomemoCoordinator
from custom_components.phomemo_d30.const import MODE_MOCK


def create_test_image_base64():
    """Create a base64-encoded test image."""
    img = Image.new("RGB", (100, 100), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.mark.asyncio
async def test_coordinator_setup(hass: HomeAssistant):
    """Test coordinator setup."""
    config = {
        "mode": MODE_MOCK,
        "mqtt_topic": "test/topic",
        "mock_save_path": "/tmp/test",
        "mock_print_delay": 0.1,
        "retry_attempts": 3,
        "retry_delay": 1,
        "queue_max_size": 10,
    }

    coordinator = PhomemoCoordinator(hass, config)

    await coordinator.async_setup()

    assert coordinator.is_connected()
    assert coordinator.queue.is_running()


@pytest.mark.asyncio
async def test_coordinator_shutdown(hass: HomeAssistant):
    """Test coordinator shutdown."""
    config = {
        "mode": MODE_MOCK,
        "mqtt_topic": "test/topic",
        "mock_save_path": "/tmp/test",
        "mock_print_delay": 0.1,
        "retry_attempts": 3,
        "retry_delay": 1,
        "queue_max_size": 10,
    }

    coordinator = PhomemoCoordinator(hass, config)

    await coordinator.async_setup()
    await coordinator.async_shutdown()

    assert not coordinator.is_connected()
    assert not coordinator.queue.is_running()


@pytest.mark.asyncio
async def test_coordinator_mqtt_message(hass: HomeAssistant):
    """Test handling MQTT message."""
    config = {
        "mode": MODE_MOCK,
        "mqtt_topic": "test/topic",
        "mock_save_path": "/tmp/test",
        "mock_print_delay": 0.1,
        "retry_attempts": 3,
        "retry_delay": 1,
        "queue_max_size": 10,
    }

    coordinator = PhomemoCoordinator(hass, config)
    await coordinator.async_setup()

    # Create mock MQTT message
    image_b64 = create_test_image_base64()

    mock_msg = MagicMock()
    mock_msg.payload = f'{{"image": "{image_b64}", "width": 50, "height": 30}}'

    await coordinator._handle_mqtt_message(mock_msg)

    # Check job was added to queue
    assert coordinator.queue.size() == 1


@pytest.mark.asyncio
async def test_coordinator_get_status(hass: HomeAssistant):
    """Test getting coordinator status."""
    config = {
        "mode": MODE_MOCK,
        "mqtt_topic": "test/topic",
        "mock_save_path": "/tmp/test",
        "mock_print_delay": 0.1,
        "retry_attempts": 3,
        "retry_delay": 1,
        "queue_max_size": 10,
    }

    coordinator = PhomemoCoordinator(hass, config)
    await coordinator.async_setup()

    status = coordinator.get_status()

    assert status["connected"] is True
    assert status["queue_size"] == 0
    assert status["printer_state"] == "idle"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_coordinator.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create coordinator module**

Create `custom_components/phomemo_d30/coordinator.py`:
```python
"""Coordinator for Phomemo D30 integration."""
import json
import logging
from typing import Any, Callable, Dict

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_MODE,
    CONF_MQTT_TOPIC,
    CONF_MOCK_SAVE_PATH,
    CONF_MOCK_PRINT_DELAY,
    CONF_RETRY_ATTEMPTS,
    CONF_RETRY_DELAY,
    CONF_QUEUE_MAX_SIZE,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DEFAULT_QUEUE_MAX_SIZE,
    DEFAULT_MOCK_PRINT_DELAY,
    MODE_MOCK,
    STATE_IDLE,
    STATE_PRINTING,
    STATE_DISCONNECTED,
)
from .mqtt_handler import parse_mqtt_message, MQTTParseError
from .phomemo.driver import MockPhomemoDriver
from .queue import PrintQueue

_LOGGER = logging.getLogger(__name__)


class PhomemoCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Phomemo printer and queue."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Phomemo D30",
        )

        self.config = config
        self.driver = None
        self.queue = None
        self._mqtt_unsubscribe: Callable | None = None
        self._printer_state = STATE_DISCONNECTED

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Create driver based on mode
        mode = self.config.get(CONF_MODE, MODE_MOCK)

        if mode == MODE_MOCK:
            self.driver = MockPhomemoDriver(
                save_path=self.config.get(CONF_MOCK_SAVE_PATH, "/tmp/phomemo"),
                print_delay=self.config.get(CONF_MOCK_PRINT_DELAY, DEFAULT_MOCK_PRINT_DELAY),
            )
        else:
            # TODO: Implement Bluetooth driver
            raise NotImplementedError("Bluetooth driver not yet implemented")

        # Connect to printer
        await self.driver.connect()
        self._printer_state = STATE_IDLE

        # Create and start queue
        self.queue = PrintQueue(
            driver=self.driver,
            max_size=self.config.get(CONF_QUEUE_MAX_SIZE, DEFAULT_QUEUE_MAX_SIZE),
            retry_attempts=self.config.get(CONF_RETRY_ATTEMPTS, DEFAULT_RETRY_ATTEMPTS),
            retry_delay=self.config.get(CONF_RETRY_DELAY, DEFAULT_RETRY_DELAY),
        )
        await self.queue.start()

        # Subscribe to MQTT topic
        topic = self.config.get(CONF_MQTT_TOPIC)
        if topic:
            self._mqtt_unsubscribe = await mqtt.async_subscribe(
                self.hass,
                topic,
                self._handle_mqtt_message,
                qos=1,
            )
            _LOGGER.info("Subscribed to MQTT topic: %s", topic)

    async def async_shutdown(self) -> None:
        """Shut down the coordinator."""
        # Unsubscribe from MQTT
        if self._mqtt_unsubscribe:
            self._mqtt_unsubscribe()

        # Stop queue
        if self.queue:
            await self.queue.stop()

        # Disconnect driver
        if self.driver:
            await self.driver.disconnect()
            self._printer_state = STATE_DISCONNECTED

    @callback
    async def _handle_mqtt_message(self, msg) -> None:
        """Handle incoming MQTT message."""
        _LOGGER.debug("Received MQTT message: %s", msg.payload)

        try:
            # Parse JSON payload
            payload = json.loads(msg.payload)

            # Parse into PrintJob
            job = parse_mqtt_message(
                payload,
                max_attempts=self.config.get(CONF_RETRY_ATTEMPTS, DEFAULT_RETRY_ATTEMPTS),
            )

            # Add to queue
            await self.queue.add_job(job)
            _LOGGER.info("Added print job %s to queue", job.id)

            # Update state
            self.async_set_updated_data({})

        except json.JSONDecodeError as e:
            _LOGGER.error("Invalid JSON in MQTT message: %s", e)
        except MQTTParseError as e:
            _LOGGER.error("Failed to parse MQTT message: %s", e)
        except Exception as e:
            _LOGGER.exception("Unexpected error handling MQTT message: %s", e)

    def is_connected(self) -> bool:
        """Check if printer is connected."""
        return self.driver and self.driver.is_connected()

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "connected": self.is_connected(),
            "queue_size": self.queue.size() if self.queue else 0,
            "printer_state": self._printer_state,
        }
```

**Step 4: Update __init__.py to use coordinator**

Read the current __init__.py:

Run: `pytest tests/custom_components/phomemo_d30/test_coordinator.py -v`
Expected: PASS

**Step 5: Modify __init__.py to integrate coordinator**

Create `custom_components/phomemo_d30/__init__.py` (update):
```python
"""The Phomemo D30 Label Printer integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import PhomemoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Phomemo D30 from a config entry."""
    _LOGGER.debug("Setting up Phomemo D30 integration")

    # Create coordinator
    coordinator = PhomemoCoordinator(hass, entry.data)
    await coordinator.async_setup()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Phomemo D30 integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Shutdown coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()

        # Remove from data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
```

**Step 6: Run integration test**

Run: `pytest tests/custom_components/phomemo_d30/test_init.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add custom_components/phomemo_d30/ tests/
git commit -m "feat: add coordinator with MQTT integration

- Create PhomemoCoordinator managing driver and queue
- Subscribe to MQTT topic and handle messages
- Integrate coordinator into integration setup/unload
- Support mock and bluetooth driver modes"
```

---

## Task 8: Sensor Entities

**Files:**
- Create: `custom_components/phomemo_d30/sensor.py`
- Test: `tests/custom_components/phomemo_d30/test_sensor.py`

**Step 1: Write test for sensor entities**

Create `tests/custom_components/phomemo_d30/test_sensor.py`:
```python
"""Test the sensor platform."""
from unittest.mock import Mock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.phomemo_d30.const import DOMAIN, STATE_IDLE


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock()
    coordinator.is_connected.return_value = True
    coordinator.get_status.return_value = {
        "connected": True,
        "queue_size": 0,
        "printer_state": STATE_IDLE,
    }
    coordinator.queue = Mock()
    coordinator.queue.size.return_value = 0
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "mode": "mock",
            "mqtt_topic": "test/topic",
        },
        title="Phomemo D30",
    )


async def test_sensor_status_entity(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test status sensor entity."""
    from custom_components.phomemo_d30.sensor import PhomemoStatusSensor

    sensor = PhomemoStatusSensor(mock_coordinator, mock_config_entry)

    assert sensor.name == "Phomemo D30 Status"
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_status"
    assert sensor.state == STATE_IDLE
    assert sensor.extra_state_attributes["bluetooth_connected"] is True
    assert sensor.extra_state_attributes["queue_length"] == 0


async def test_sensor_queue_entity(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test queue sensor entity."""
    from custom_components.phomemo_d30.sensor import PhomemoQueueSensor

    mock_coordinator.queue.size.return_value = 5

    sensor = PhomemoQueueSensor(mock_coordinator, mock_config_entry)

    assert sensor.name == "Phomemo D30 Queue"
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_queue"
    assert sensor.state == 5
    assert sensor.native_unit_of_measurement == "jobs"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_sensor.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create sensor platform**

Create `custom_components/phomemo_d30/sensor.py`:
```python
"""Sensor platform for Phomemo D30."""
import logging
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PhomemoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Phomemo D30 sensors."""
    coordinator: PhomemoCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        PhomemoStatusSensor(coordinator, entry),
        PhomemoQueueSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


class PhomemoStatusSensor(SensorEntity):
    """Sensor for printer status."""

    def __init__(self, coordinator: PhomemoCoordinator, entry: ConfigEntry):
        """Initialize status sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = "Phomemo D30 Status"
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        status = self._coordinator.get_status()
        return status.get("printer_state", "unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        status = self._coordinator.get_status()
        return {
            "bluetooth_connected": status.get("connected", False),
            "queue_length": status.get("queue_size", 0),
        }


class PhomemoQueueSensor(SensorEntity):
    """Sensor for queue size."""

    def __init__(self, coordinator: PhomemoCoordinator, entry: ConfigEntry):
        """Initialize queue sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = "Phomemo D30 Queue"
        self._attr_unique_id = f"{entry.entry_id}_queue"
        self._attr_native_unit_of_measurement = "jobs"

    @property
    def state(self) -> int:
        """Return the state of the sensor."""
        return self._coordinator.queue.size() if self._coordinator.queue else 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_sensor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/phomemo_d30/sensor.py tests/
git commit -m "feat: add sensor entities

- Implement status sensor (idle/printing/error/disconnected)
- Implement queue sensor (job count)
- Add entity attributes for connection and queue state"
```

---

## Task 9: Config Flow (Basic Mock Mode)

**Files:**
- Create: `custom_components/phomemo_d30/config_flow.py`
- Create: `custom_components/phomemo_d30/strings.json`
- Create: `custom_components/phomemo_d30/translations/en.json`
- Test: `tests/custom_components/phomemo_d30/test_config_flow.py`

**Step 1: Write test for config flow**

Create `tests/custom_components/phomemo_d30/test_config_flow.py`:
```python
"""Test the config flow."""
import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.phomemo_d30.const import DOMAIN


async def test_form_mock_mode(hass: HomeAssistant):
    """Test config flow for mock mode."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # Submit mock mode configuration
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "mode": "mock",
            "mqtt_topic": "homeassistant/phomemo/print",
            "mock_save_path": "/config/phomemo_test",
        },
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Phomemo D30 (Mock)"
    assert result["data"]["mode"] == "mock"
    assert result["data"]["mqtt_topic"] == "homeassistant/phomemo/print"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_config_flow.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create config flow**

Create `custom_components/phomemo_d30/config_flow.py`:
```python
"""Config flow for Phomemo D30."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_MODE,
    CONF_MQTT_TOPIC,
    CONF_MOCK_SAVE_PATH,
    CONF_DARKNESS,
    CONF_RETRY_ATTEMPTS,
    CONF_RETRY_DELAY,
    DEFAULT_MQTT_TOPIC,
    DEFAULT_MOCK_SAVE_PATH,
    DEFAULT_DARKNESS,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DOMAIN,
    MODE_MOCK,
)

_LOGGER = logging.getLogger(__name__)


class PhomemoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Phomemo D30."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate MQTT topic
            if not user_input.get(CONF_MQTT_TOPIC):
                errors["base"] = "mqtt_topic_required"
            else:
                # Create entry
                title = f"Phomemo D30 ({user_input[CONF_MODE].title()})"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_MODE: user_input[CONF_MODE],
                        CONF_MQTT_TOPIC: user_input[CONF_MQTT_TOPIC],
                        CONF_MOCK_SAVE_PATH: user_input.get(
                            CONF_MOCK_SAVE_PATH, DEFAULT_MOCK_SAVE_PATH
                        ),
                        CONF_DARKNESS: DEFAULT_DARKNESS,
                        CONF_RETRY_ATTEMPTS: DEFAULT_RETRY_ATTEMPTS,
                        CONF_RETRY_DELAY: DEFAULT_RETRY_DELAY,
                    },
                )

        # Show form
        data_schema = vol.Schema({
            vol.Required(CONF_MODE, default=MODE_MOCK): vol.In([MODE_MOCK]),
            vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
            vol.Optional(CONF_MOCK_SAVE_PATH, default=DEFAULT_MOCK_SAVE_PATH): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
```

**Step 4: Create strings.json**

Create `custom_components/phomemo_d30/strings.json`:
```json
{
  "config": {
    "step": {
      "user": {
        "title": "Configure Phomemo D30",
        "description": "Set up your Phomemo D30 label printer",
        "data": {
          "mode": "Printer Mode",
          "mqtt_topic": "MQTT Topic",
          "mock_save_path": "Mock Save Path"
        }
      }
    },
    "error": {
      "mqtt_topic_required": "MQTT topic is required"
    }
  }
}
```

**Step 5: Create translations**

Create `custom_components/phomemo_d30/translations/en.json`:
```json
{
  "config": {
    "step": {
      "user": {
        "title": "Configure Phomemo D30",
        "description": "Set up your Phomemo D30 label printer",
        "data": {
          "mode": "Printer Mode",
          "mqtt_topic": "MQTT Topic",
          "mock_save_path": "Mock Save Path"
        }
      }
    },
    "error": {
      "mqtt_topic_required": "MQTT topic is required"
    }
  }
}
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_config_flow.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add custom_components/phomemo_d30/ tests/
git commit -m "feat: add config flow for mock mode

- Implement basic UI configuration flow
- Support mock mode setup
- Add MQTT topic configuration
- Include translations and strings"
```

---

## Task 10: Services Definition

**Files:**
- Create: `custom_components/phomemo_d30/services.yaml`
- Modify: `custom_components/phomemo_d30/__init__.py`
- Test: `tests/custom_components/phomemo_d30/test_services.py`

**Step 1: Write test for services**

Create `tests/custom_components/phomemo_d30/test_services.py`:
```python
"""Test services."""
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.phomemo_d30.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "mode": "mock",
            "mqtt_topic": "test/topic",
            "mock_save_path": "/tmp/test",
        },
        title="Phomemo D30",
    )


async def test_clear_queue_service(hass: HomeAssistant, mock_config_entry):
    """Test clear_queue service."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Call service
    await hass.services.async_call(
        DOMAIN,
        "clear_queue",
        {},
        blocking=True,
    )

    # Service should complete without error
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_services.py -v`
Expected: FAIL (service not registered)

**Step 3: Create services.yaml**

Create `custom_components/phomemo_d30/services.yaml`:
```yaml
clear_queue:
  name: Clear print queue
  description: Clear all pending print jobs from the queue
  fields: {}

print:
  name: Print label
  description: Print a label image to Phomemo D30
  fields:
    image_path:
      name: Image path
      description: Path to image file or base64-encoded image data
      required: true
      example: "/config/www/label.png"
      selector:
        text:
    width:
      name: Width
      description: Label width in millimeters
      required: true
      example: 50
      selector:
        number:
          min: 10
          max: 100
          unit_of_measurement: "mm"
    height:
      name: Height
      description: Label height in millimeters
      required: true
      example: 30
      selector:
        number:
          min: 10
          max: 100
          unit_of_measurement: "mm"
```

**Step 4: Update __init__.py to register services**

Update `custom_components/phomemo_d30/__init__.py`:
```python
"""The Phomemo D30 Label Printer integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS
from .coordinator import PhomemoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Phomemo D30 from a config entry."""
    _LOGGER.debug("Setting up Phomemo D30 integration")

    # Create coordinator
    coordinator = PhomemoCoordinator(hass, entry.data)
    await coordinator.async_setup()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_clear_queue(call: ServiceCall) -> None:
        """Handle clear_queue service."""
        for coord in hass.data[DOMAIN].values():
            if isinstance(coord, PhomemoCoordinator):
                await coord.queue.clear()
                _LOGGER.info("Cleared print queue")

    hass.services.async_register(
        DOMAIN,
        "clear_queue",
        handle_clear_queue,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Phomemo D30 integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Shutdown coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()

        # Remove from data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_services.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add custom_components/phomemo_d30/ tests/
git commit -m "feat: add services for queue control

- Define clear_queue service
- Define print service schema
- Register services on integration setup"
```

---

## Task 11: README and Documentation

**Files:**
- Create: `README.md`
- Create: `HACS_README.md`

**Step 1: Create README**

Create `README.md`:
```markdown
# Phomemo D30 Label Printer for Home Assistant

A Home Assistant custom integration for the Phomemo D30 label printer. Receive label images via MQTT (e.g., from Homebox) and print them via Bluetooth.

## Features

- 🖨️ Print labels via Bluetooth or mock mode
- 📨 Receive print jobs via MQTT
- 📊 Monitor printer status and queue with sensor entities
- 🔄 Automatic retry on connection failures
- 🧪 Mock mode for testing without hardware
- 🎛️ UI configuration via Home Assistant

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the 3 dots in the top right
4. Select "Custom repositories"
5. Add this repository URL
6. Click "Download"
7. Restart Home Assistant

### Manual

1. Copy `custom_components/phomemo_d30` to your `config/custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Configuration** → **Integrations**
2. Click **Add Integration**
3. Search for "Phomemo D30"
4. Select printer mode:
   - **Mock**: Testing without hardware (saves images to disk)
   - **Bluetooth**: Real printer (coming soon)
5. Configure MQTT topic (default: `homeassistant/phomemo/print`)
6. Complete setup

## MQTT Message Format

Send print jobs to the configured MQTT topic with this JSON format:

```json
{
  "image": "<base64-encoded PNG>",
  "width": 50,
  "height": 30,
  "darkness": 5,
  "rotate": 0
}
```

**Required fields:**
- `image`: Base64-encoded PNG image data
- `width`: Label width in millimeters
- `height`: Label height in millimeters

**Optional fields:**
- `darkness`: Print darkness (1-7, default: 5)
- `rotate`: Rotation angle (0, 90, 180, 270, default: 0)

## Entities

### Sensors

- **sensor.phomemo_d30_status**: Printer status (`idle`, `printing`, `error`, `disconnected`)
- **sensor.phomemo_d30_queue**: Number of jobs in print queue

## Services

### `phomemo_d30.clear_queue`

Clear all pending print jobs.

### `phomemo_d30.print`

Manually print a label (bypass MQTT).

**Parameters:**
- `image_path`: Path to image file or base64 data
- `width`: Label width in mm
- `height`: Label height in mm

## Development

See [Development Guide](docs/development.md) for details on:
- Setting up the dev environment
- Running tests
- Contributing

## Testing with Mock Mode

1. Configure integration in mock mode
2. Set `mock_save_path` to `/config/phomemo_test_prints`
3. Send MQTT messages
4. Check saved images in the configured path

## Integration with Homebox

This integration is designed to work with [Homebox](https://github.com/hay-kot/homebox) label printing. Configure Homebox to send labels to your MQTT topic.

See the [Homebox MQTT guide](https://blog.fuzzymistborn.com/homebox-labels-over-mqtt/) for setup instructions.

## Credits

Based on [vivier/phomemo-tools](https://github.com/vivier/phomemo-tools) for Phomemo printer communication.

## License

MIT License
```

**Step 2: Create HACS README**

Create `HACS_README.md`:
```markdown
# Phomemo D30 Label Printer

Print labels to your Phomemo D30 printer from Home Assistant via MQTT.

Perfect for integration with Homebox for automatic label printing.

## Quick Start

1. Install via HACS
2. Add integration in Home Assistant
3. Configure MQTT topic
4. Start printing!

See [full documentation](https://github.com/yourusername/ha-phomemo-d30) for details.
```

**Step 3: Commit**

```bash
git add README.md HACS_README.md
git commit -m "docs: add README and installation guide

- Document installation via HACS and manual
- Explain MQTT message format
- List entities and services
- Add testing and development info"
```

---

## Task 12: Final Testing and Verification

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Check code formatting**

Run:
```bash
black custom_components/phomemo_d30/ tests/
ruff check custom_components/phomemo_d30/ tests/
```
Expected: No errors

**Step 3: Manual testing checklist**

Create `docs/testing-checklist.md`:
```markdown
# Testing Checklist

## Mock Mode Testing

- [ ] Install integration in Home Assistant dev container
- [ ] Configure in mock mode
- [ ] Subscribe to MQTT topic
- [ ] Send test MQTT message with base64 image
- [ ] Verify image saved to mock_save_path
- [ ] Check sensor.phomemo_d30_status shows "idle"
- [ ] Check sensor.phomemo_d30_queue shows correct count
- [ ] Send multiple messages and verify queue processing
- [ ] Call clear_queue service
- [ ] Verify queue cleared

## Error Handling

- [ ] Send invalid MQTT message (missing fields)
- [ ] Send invalid base64 data
- [ ] Send invalid image data
- [ ] Verify errors logged correctly
- [ ] Verify sensor status updates

## Integration Lifecycle

- [ ] Install integration
- [ ] Reload integration
- [ ] Restart Home Assistant
- [ ] Uninstall integration
- [ ] Verify clean shutdown
```

**Step 4: Commit checklist**

```bash
git add docs/testing-checklist.md
git commit -m "test: add manual testing checklist

- Define mock mode test scenarios
- Add error handling tests
- Include integration lifecycle tests"
```

**Step 5: Create final verification script**

Create `.github/workflows/test.yml`:
```yaml
name: Test

on:
  push:
    branches: [main, feature/*]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements_dev.txt

      - name: Run tests
        run: pytest tests/ -v

      - name: Check formatting
        run: |
          black --check custom_components/ tests/
          ruff check custom_components/ tests/
```

**Step 6: Commit CI configuration**

```bash
git add .github/workflows/test.yml
git commit -m "ci: add GitHub Actions test workflow

- Run pytest on push and PR
- Check code formatting with black and ruff
- Test on Python 3.11"
```

---

## Summary

This implementation plan creates a complete Home Assistant integration for the Phomemo D30 label printer with:

1. ✅ Development environment with VS Code dev container
2. ✅ Core integration structure with proper HA patterns
3. ✅ Print job data model with status tracking
4. ✅ Mock printer driver for hardware-free testing
5. ✅ Async print queue with retry logic
6. ✅ MQTT message parser with validation
7. ✅ Coordinator managing driver, queue, and MQTT
8. ✅ Sensor entities for status monitoring
9. ✅ Config flow for UI setup
10. ✅ Services for queue control
11. ✅ Documentation and README
12. ✅ Testing and CI/CD

## Next Steps

After completing this plan:
1. Test in Home Assistant dev container
2. Implement Bluetooth driver (following mock driver pattern)
3. Test with real Phomemo D30 hardware
4. Publish to HACS
5. Integrate with Homebox

## References

- @superpowers:test-driven-development - TDD workflow used throughout
- @superpowers:systematic-debugging - For troubleshooting failures
- @superpowers:verification-before-completion - Run tests before claiming completion
