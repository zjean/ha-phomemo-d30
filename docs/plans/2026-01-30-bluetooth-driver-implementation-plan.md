# Phomemo-Tools Bluetooth Driver Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate phomemo-tools library to add real Bluetooth printing capability alongside the existing mock driver, with user-selectable driver type in config flow.

**Architecture:** Vendor D30 protocol code from phomemo-tools, create BluetoothPhomemoDriver using Home Assistant's Bluetooth integration and bleak library, update config flow for driver selection with Bluetooth device discovery, maintain existing MockPhomemoDriver and queue unchanged.

**Tech Stack:** Python 3.11, Home Assistant Bluetooth integration, bleak BLE library, PIL for image processing, phomemo-tools protocol (GPL-3.0)

---

## Task 1: Update License to GPL-3.0

**Files:**
- Modify: `LICENSE`
- Modify: `README.md:288-291`

**Step 1: Update LICENSE file**

Replace MIT license with GPL-3.0:

```
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

[Full GPL-3.0 text from https://www.gnu.org/licenses/gpl-3.0.txt]

---

This project includes code adapted from phomemo-tools by Laurent Vivier
Original: https://github.com/vivier/phomemo-tools
License: GPL-3.0
```

**Step 2: Update README.md license section**

Change line 288-291 from:

```markdown
## License

MIT License
```

To:

```markdown
## License

GPL-3.0 License

This project includes code adapted from [phomemo-tools](https://github.com/vivier/phomemo-tools) by Laurent Vivier, which is licensed under GPL-3.0.
```

**Step 3: Commit**

```bash
git add LICENSE README.md
git commit -m "chore: change license from MIT to GPL-3.0

Required for vendoring phomemo-tools D30 protocol code.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Add bleak Dependency

**Files:**
- Modify: `custom_components/phomemo_d30/manifest.json:9`
- Modify: `requirements_dev.txt`

**Step 1: Add bleak to manifest.json**

Change line 9 from:

```json
  "requirements": ["Pillow==10.1.0"],
```

To:

```json
  "requirements": ["Pillow==10.1.0", "bleak>=0.21.0"],
```

**Step 2: Add bleak to requirements_dev.txt**

Append to file:

```
bleak>=0.21.0
```

**Step 3: Commit**

```bash
git add custom_components/phomemo_d30/manifest.json requirements_dev.txt
git commit -m "feat: add bleak dependency for Bluetooth support

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Vendor D30 Protocol Code

**Files:**
- Create: `custom_components/phomemo_d30/phomemo/protocol.py`
- Create: `tests/custom_components/phomemo_d30/test_protocol.py`

**Step 1: Clone phomemo-tools to examine code**

Run: `git clone --depth 1 https://github.com/vivier/phomemo-tools.git /tmp/phomemo-tools`

**Step 2: Write failing test for protocol functions**

Create `tests/custom_components/phomemo_d30/test_protocol.py`:

```python
"""Test D30 protocol encoding."""
import pytest
from PIL import Image

from custom_components.phomemo_d30.phomemo.protocol import (
    preprocess_image,
    encode_print_data,
)


def create_test_image(width=100, height=100, color="white"):
    """Create a simple test image."""
    return Image.new("RGB", (width, height), color=color)


def test_preprocess_image_converts_to_monochrome():
    """Test image preprocessing converts to 1-bit monochrome."""
    img = create_test_image(50, 30)

    processed = preprocess_image(img, width=50, height=30, darkness=5)

    assert processed.mode == "1"  # 1-bit monochrome
    assert processed.size == (50, 30)


def test_encode_print_data_returns_bytes():
    """Test protocol encoding returns byte sequence."""
    img = Image.new("1", (50, 30), color=1)  # 1-bit white image

    data = encode_print_data(img, darkness=5, rotate=0)

    assert isinstance(data, bytes)
    assert len(data) > 0
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_protocol.py -v`

Expected: FAIL with "No module named 'custom_components.phomemo_d30.phomemo.protocol'"

**Step 4: Create protocol.py with vendored code**

Create `custom_components/phomemo_d30/phomemo/protocol.py`:

```python
"""D30 printer protocol implementation.

Adapted from phomemo-tools by Laurent Vivier
Original: https://github.com/vivier/phomemo-tools
License: GPL-3.0
"""
import struct
from PIL import Image, ImageOps


def preprocess_image(
    image: Image.Image,
    width: int,
    height: int,
    darkness: int = 5,
) -> Image.Image:
    """Convert image to D30 format (1-bit monochrome, dithered).

    Args:
        image: Input PIL Image
        width: Target width in mm
        height: Target height in mm
        darkness: Print darkness (1-5), higher = darker

    Returns:
        1-bit monochrome PIL Image ready for encoding
    """
    # Convert to grayscale first
    if image.mode != "L":
        image = image.convert("L")

    # Adjust darkness by modifying brightness/contrast
    # Darkness 5 = normal, 1 = lightest, higher = darker
    if darkness != 5:
        factor = 1.0 + (darkness - 5) * 0.2  # Scale brightness
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(factor)

    # Resize to target dimensions (D30 is 203 DPI)
    # For now, use the image as-is and let caller handle sizing

    # Convert to 1-bit with dithering
    image = image.convert("1", dither=Image.FLOYDSTEINBERG)

    return image


def encode_print_data(
    image: Image.Image,
    darkness: int = 5,
    rotate: int = 0,
) -> bytes:
    """Encode image as D30 protocol bytes.

    Args:
        image: 1-bit monochrome PIL Image
        darkness: Print darkness (1-5)
        rotate: Rotation angle (0, 90, 180, 270)

    Returns:
        Complete byte sequence to send to printer over Bluetooth
    """
    if image.mode != "1":
        raise ValueError(f"Image must be 1-bit monochrome, got {image.mode}")

    # Rotate image if requested
    if rotate == 90:
        image = image.rotate(90, expand=True)
    elif rotate == 180:
        image = image.rotate(180, expand=True)
    elif rotate == 270:
        image = image.rotate(270, expand=True)

    width, height = image.size

    # Convert image to bitmap bytes (1 bit per pixel, row by row)
    # Pixels are packed into bytes, MSB first
    bitmap_data = bytearray()

    for y in range(height):
        row_bytes = bytearray()
        for x in range(0, width, 8):
            byte = 0
            for bit in range(8):
                if x + bit < width:
                    pixel = image.getpixel((x + bit, y))
                    # Invert: 1 = white, 0 = black for thermal printer
                    if pixel == 0:  # PIL: 0 = black
                        byte |= (1 << (7 - bit))
            row_bytes.append(byte)
        bitmap_data.extend(row_bytes)

    # Build D30 protocol packet
    # Based on phomemo-tools D30 implementation
    packet = bytearray()

    # Header
    packet.extend(b'\x1f\x11')  # D30 print command

    # Image dimensions
    packet.extend(struct.pack('>H', width))   # Width (big-endian)
    packet.extend(struct.pack('>H', height))  # Height (big-endian)

    # Darkness setting (1-5)
    packet.append(min(5, max(1, darkness)))

    # Bitmap data
    packet.extend(bitmap_data)

    # Footer
    packet.extend(b'\x1f\x1e')  # End of print

    return bytes(packet)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_protocol.py -v`

Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add custom_components/phomemo_d30/phomemo/protocol.py tests/custom_components/phomemo_d30/test_protocol.py
git commit -m "feat: vendor D30 protocol from phomemo-tools

Add image preprocessing and protocol encoding functions.
Adapted from phomemo-tools by Laurent Vivier (GPL-3.0).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Implement BluetoothPhomemoDriver

**Files:**
- Create: `custom_components/phomemo_d30/phomemo/bluetooth_driver.py`
- Create: `tests/custom_components/phomemo_d30/test_bluetooth_driver.py`

**Step 1: Write failing test for Bluetooth driver**

Create `tests/custom_components/phomemo_d30/test_bluetooth_driver.py`:

```python
"""Test Bluetooth printer driver."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from PIL import Image

from custom_components.phomemo_d30.models import PrintJob
from custom_components.phomemo_d30.phomemo.bluetooth_driver import BluetoothPhomemoDriver
from custom_components.phomemo_d30.phomemo.exceptions import FatalError, RecoverableError


def create_test_image():
    """Create a simple test image."""
    return Image.new("RGB", (50, 30), color="white")


@pytest.mark.asyncio
async def test_bluetooth_driver_connect():
    """Test Bluetooth connection."""
    hass = MagicMock()
    address = "AA:BB:CC:DD:EE:FF"

    with patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.bluetooth") as mock_bt, \
         patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.BleakClient") as mock_client_class:

        mock_ble_device = MagicMock()
        mock_bt.async_ble_device_from_address.return_value = mock_ble_device

        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client_class.return_value = mock_client

        driver = BluetoothPhomemoDriver(hass, address)
        await driver.connect()

        assert driver.is_connected()
        mock_client.connect.assert_called_once()


@pytest.mark.asyncio
async def test_bluetooth_driver_print():
    """Test printing via Bluetooth."""
    hass = MagicMock()
    address = "AA:BB:CC:DD:EE:FF"

    with patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.bluetooth") as mock_bt, \
         patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.BleakClient") as mock_client_class:

        mock_ble_device = MagicMock()
        mock_bt.async_ble_device_from_address.return_value = mock_ble_device

        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client_class.return_value = mock_client

        driver = BluetoothPhomemoDriver(hass, address)
        await driver.connect()

        img = create_test_image()
        job = PrintJob(image=img, width=50, height=30)

        await driver.print(job)

        # Should have written data to characteristic
        assert mock_client.write_gatt_char.called
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_bluetooth_driver.py -v`

Expected: FAIL with "No module named 'custom_components.phomemo_d30.phomemo.bluetooth_driver'"

**Step 3: Create BluetoothPhomemoDriver**

Create `custom_components/phomemo_d30/phomemo/bluetooth_driver.py`:

```python
"""Bluetooth printer driver for Phomemo D30.

Adapted from phomemo-tools by Laurent Vivier
Original: https://github.com/vivier/phomemo-tools
License: GPL-3.0
"""
import asyncio
import logging
from typing import Optional

from bleak import BleakClient
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from ..models import PrintJob
from .driver import PhomemoDriver
from .exceptions import FatalError, RecoverableError
from . import protocol

_LOGGER = logging.getLogger(__name__)

# D30 Bluetooth characteristics
# Serial port service UUID (common for thermal printers)
SERIAL_SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"


class BluetoothPhomemoDriver(PhomemoDriver):
    """Bluetooth driver for Phomemo D30 using Home Assistant Bluetooth."""

    def __init__(self, hass: HomeAssistant, bluetooth_address: str):
        """Initialize Bluetooth driver.

        Args:
            hass: Home Assistant instance
            bluetooth_address: MAC address from discovered device
        """
        self._hass = hass
        self._address = bluetooth_address
        self._client: Optional[BleakClient] = None
        self._connected = False
        self._write_characteristic = WRITE_CHAR_UUID

    async def connect(self) -> None:
        """Connect to D30 via Home Assistant Bluetooth.

        Raises:
            FatalError: If Bluetooth device not found
            RecoverableError: If connection times out
        """
        try:
            # Get BLE device from HA's Bluetooth integration
            ble_device = bluetooth.async_ble_device_from_address(
                self._hass,
                self._address,
                connectable=True
            )

            if ble_device is None:
                raise FatalError(
                    f"Bluetooth device {self._address} not found. "
                    "Make sure the printer is powered on and in range."
                )

            # Create BleakClient and connect
            self._client = BleakClient(ble_device)

            _LOGGER.debug("Connecting to Bluetooth device %s", self._address)
            await asyncio.wait_for(self._client.connect(), timeout=10.0)

            self._connected = True
            _LOGGER.info("Connected to Bluetooth device %s", self._address)

        except asyncio.TimeoutError as e:
            raise RecoverableError(
                f"Bluetooth connection timeout: {e}. Check printer range."
            ) from e
        except Exception as e:
            raise RecoverableError(
                f"Bluetooth connection failed: {e}"
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from the printer."""
        if self._client and self._connected:
            _LOGGER.debug("Disconnecting from Bluetooth device %s", self._address)
            await self._client.disconnect()
            self._connected = False
            _LOGGER.info("Disconnected from Bluetooth device %s", self._address)

    def is_connected(self) -> bool:
        """Check if connected to printer."""
        return self._connected and self._client is not None and self._client.is_connected

    async def print(self, job: PrintJob) -> None:
        """Print a job via Bluetooth.

        Args:
            job: Print job to execute

        Raises:
            FatalError: Invalid image format, not connected
            RecoverableError: Connection timeout, BLE disconnection
        """
        if not self.is_connected():
            raise FatalError("Bluetooth driver not connected")

        _LOGGER.info(
            "Bluetooth driver: printing job %s (width=%d, height=%d)",
            job.id,
            job.width,
            job.height,
        )

        try:
            # Preprocess image (run in thread pool to avoid blocking)
            processed_image = await asyncio.to_thread(
                protocol.preprocess_image,
                job.image,
                job.width,
                job.height,
                job.darkness,
            )

            # Encode to D30 protocol bytes
            print_data = await asyncio.to_thread(
                protocol.encode_print_data,
                processed_image,
                job.darkness,
                job.rotate,
            )

            _LOGGER.debug(
                "Sending %d bytes to printer %s",
                len(print_data),
                self._address,
            )

            # Split into chunks (BLE MTU limits, typically 512 bytes)
            chunk_size = 512
            for i in range(0, len(print_data), chunk_size):
                chunk = print_data[i : i + chunk_size]
                await self._client.write_gatt_char(
                    self._write_characteristic,
                    chunk,
                    response=False,  # Write without response for speed
                )
                # Small delay to avoid overwhelming the printer
                await asyncio.sleep(0.01)

            _LOGGER.info("Bluetooth driver: job %s completed", job.id)

        except ValueError as e:
            raise FatalError(f"Invalid image format: {e}") from e
        except asyncio.TimeoutError as e:
            raise RecoverableError(
                f"Bluetooth write timeout: {e}. Printer may be busy."
            ) from e
        except Exception as e:
            # BLE disconnection or other errors
            self._connected = False
            raise RecoverableError(
                f"Bluetooth print failed: {e}. Will retry."
            ) from e
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_bluetooth_driver.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add custom_components/phomemo_d30/phomemo/bluetooth_driver.py tests/custom_components/phomemo_d30/test_bluetooth_driver.py
git commit -m "feat: add Bluetooth driver for D30 printer

Implements PhomemoDriver interface using bleak and HA Bluetooth integration.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update Config Flow for Driver Selection

**Files:**
- Create: `custom_components/phomemo_d30/config_flow.py`
- Create: `tests/custom_components/phomemo_d30/test_config_flow.py`

**Step 1: Write failing test for config flow**

Create `tests/custom_components/phomemo_d30/test_config_flow.py`:

```python
"""Test config flow."""
from unittest.mock import patch, MagicMock
import pytest

from homeassistant import config_entries
from custom_components.phomemo_d30.const import DOMAIN


@pytest.mark.asyncio
async def test_config_flow_driver_type_selection(hass):
    """Test driver type selection step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "driver_type" in result["data_schema"].schema


@pytest.mark.asyncio
async def test_config_flow_mock_driver(hass):
    """Test mock driver configuration."""
    # Start flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Select mock driver
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"driver_type": "mock"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "mock"

    # Configure mock settings
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "save_path": "/config/test_prints",
            "print_delay": 1.0,
            "failure_rate": 0.0
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Phomemo D30 (Mock)"
    assert result["data"]["driver_type"] == "mock"


@pytest.mark.asyncio
async def test_config_flow_bluetooth_driver(hass):
    """Test Bluetooth driver configuration."""
    # Mock Bluetooth discovery
    mock_device = MagicMock()
    mock_device.address = "AA:BB:CC:DD:EE:FF"
    mock_device.name = "Phomemo-D30"

    with patch("custom_components.phomemo_d30.config_flow.bluetooth.async_discovered_service_info") as mock_discover:
        mock_discover.return_value = [mock_device]

        # Start flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Select Bluetooth driver
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"driver_type": "bluetooth"}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "bluetooth"

        # Select device
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"device": "AA:BB:CC:DD:EE:FF"}
        )

        assert result["type"] == "create_entry"
        assert result["title"] == "Phomemo D30 (AA:BB:CC:DD:EE:FF)"
        assert result["data"]["driver_type"] == "bluetooth"
        assert result["data"]["bluetooth_address"] == "AA:BB:CC:DD:EE:FF"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_config_flow.py -v`

Expected: FAIL with "No module named 'custom_components.phomemo_d30.config_flow'"

**Step 3: Create config_flow.py**

Create `custom_components/phomemo_d30/config_flow.py`:

```python
"""Config flow for Phomemo D30 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PhomemoD30ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Phomemo D30."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._driver_type: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial driver type selection."""
        if user_input is not None:
            self._driver_type = user_input["driver_type"]
            if self._driver_type == "mock":
                return await self.async_step_mock()
            else:
                return await self.async_step_bluetooth()

        schema = vol.Schema({
            vol.Required("driver_type"): vol.In({
                "mock": "Mock Printer (Testing)",
                "bluetooth": "Bluetooth Printer (Real D30)"
            })
        })

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_mock(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure mock driver."""
        if user_input is not None:
            return self.async_create_entry(
                title="Phomemo D30 (Mock)",
                data={
                    "driver_type": "mock",
                    "save_path": user_input["save_path"],
                    "print_delay": user_input.get("print_delay", 2.0),
                    "failure_rate": user_input.get("failure_rate", 0.0),
                }
            )

        schema = vol.Schema({
            vol.Required("save_path", default="/config/phomemo_prints"): str,
            vol.Optional("print_delay", default=2.0): vol.Coerce(float),
            vol.Optional("failure_rate", default=0.0): vol.All(
                vol.Coerce(float),
                vol.Range(min=0.0, max=1.0)
            )
        })

        return self.async_show_form(step_id="mock", data_schema=schema)

    async def async_step_bluetooth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show discovered Phomemo devices."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Phomemo D30 ({user_input['device']})",
                data={
                    "driver_type": "bluetooth",
                    "bluetooth_address": user_input["device"]
                }
            )

        # Get discovered Bluetooth devices from HA
        discovered = bluetooth.async_discovered_service_info(self.hass)

        # Filter for Phomemo devices
        phomemo_devices = [
            device for device in discovered
            if "phomemo" in device.name.lower() or "d30" in device.name.lower()
        ]

        if not phomemo_devices:
            return self.async_abort(reason="no_devices_found")

        schema = vol.Schema({
            vol.Required("device"): vol.In({
                dev.address: f"{dev.name} ({dev.address})"
                for dev in phomemo_devices
            })
        })

        return self.async_show_form(step_id="bluetooth", data_schema=schema)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_config_flow.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add custom_components/phomemo_d30/config_flow.py tests/custom_components/phomemo_d30/test_config_flow.py
git commit -m "feat: add config flow for driver selection

Support mock and Bluetooth driver configuration with device discovery.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Update Integration Init for Driver Instantiation

**Files:**
- Modify: `custom_components/phomemo_d30/__init__.py:25-32`
- Modify: `tests/custom_components/phomemo_d30/test_init.py`

**Step 1: Write failing test for driver instantiation**

Add to `tests/custom_components/phomemo_d30/test_init.py`:

```python
@pytest.mark.asyncio
async def test_setup_entry_mock_driver(hass):
    """Test setup with mock driver."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "driver_type": "mock",
            "save_path": "/tmp/test",
            "print_delay": 1.0,
            "failure_rate": 0.0,
        }
    )
    entry.add_to_hass(hass)

    assert await async_setup_entry(hass, entry)
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_setup_entry_bluetooth_driver(hass):
    """Test setup with Bluetooth driver."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "driver_type": "bluetooth",
            "bluetooth_address": "AA:BB:CC:DD:EE:FF",
        }
    )
    entry.add_to_hass(hass)

    assert await async_setup_entry(hass, entry)
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/custom_components/phomemo_d30/test_init.py::test_setup_entry_mock_driver tests/custom_components/phomemo_d30/test_init.py::test_setup_entry_bluetooth_driver -v`

Expected: May pass or fail depending on current implementation

**Step 3: Update __init__.py to instantiate drivers**

Modify `custom_components/phomemo_d30/__init__.py` lines 25-32:

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Phomemo D30 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Instantiate appropriate driver based on config
    driver_type = entry.data.get("driver_type", "mock")

    if driver_type == "mock":
        from .phomemo.driver import MockPhomemoDriver
        driver = MockPhomemoDriver(
            save_path=entry.data["save_path"],
            print_delay=entry.data.get("print_delay", 2.0),
            failure_rate=entry.data.get("failure_rate", 0.0),
        )
    else:  # bluetooth
        from .phomemo.bluetooth_driver import BluetoothPhomemoDriver
        driver = BluetoothPhomemoDriver(
            hass=hass,
            bluetooth_address=entry.data["bluetooth_address"],
        )

    # Store driver instance
    hass.data[DOMAIN][entry.entry_id] = {
        "driver": driver,
        "config": entry.data,
    }

    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/custom_components/phomemo_d30/test_init.py -v`

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add custom_components/phomemo_d30/__init__.py tests/custom_components/phomemo_d30/test_init.py
git commit -m "feat: instantiate driver based on config entry

Support both mock and Bluetooth driver instantiation.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Add Translation Strings

**Files:**
- Create: `custom_components/phomemo_d30/translations/en.json`

**Step 1: Create translations file**

Create `custom_components/phomemo_d30/translations/en.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Phomemo D30 Setup",
        "description": "Select printer driver type",
        "data": {
          "driver_type": "Driver Type"
        }
      },
      "mock": {
        "title": "Mock Printer Configuration",
        "description": "Configure test printer (saves images to disk)",
        "data": {
          "save_path": "Save Path",
          "print_delay": "Print Delay (seconds)",
          "failure_rate": "Simulated Failure Rate (0.0-1.0)"
        }
      },
      "bluetooth": {
        "title": "Bluetooth Printer Selection",
        "description": "Select your Phomemo D30 printer",
        "data": {
          "device": "Printer"
        }
      }
    },
    "error": {
      "no_devices_found": "No Phomemo printers found. Make sure your D30 is powered on and Bluetooth is enabled."
    },
    "abort": {
      "no_devices_found": "No Phomemo printers discovered"
    }
  }
}
```

**Step 2: Commit**

```bash
git add custom_components/phomemo_d30/translations/en.json
git commit -m "feat: add English translation strings for config flow

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Update README with Bluetooth Instructions

**Files:**
- Modify: `README.md:269-281`

**Step 1: Add Bluetooth setup section**

Insert after line 269 (before "## Troubleshooting"):

```markdown
## Bluetooth Printer Setup

### Prerequisites

1. **Enable Home Assistant's Bluetooth integration:**
   - Go to: Settings → Devices & Services
   - Click: Add Integration
   - Search: Bluetooth
   - Follow setup wizard

2. **Power on your Phomemo D30 and enable Bluetooth pairing mode**

### Configuration

1. **Add the Phomemo D30 integration:**
   - Go to: Settings → Devices & Services
   - Click: Add Integration
   - Search: Phomemo D30
   - Select: "Bluetooth Printer (Real D30)"
   - Choose your printer from the discovered devices list

2. **If your printer doesn't appear:**
   - Make sure it's powered on and in Bluetooth range
   - Check that HA's Bluetooth integration is working: Settings → Devices & Services → Bluetooth
   - Try restarting the D30 printer

### Driver Selection

You can configure multiple instances of the integration:
- **Mock Driver** - For testing without hardware (saves images to disk)
- **Bluetooth Driver** - For real D30 printer via Bluetooth

```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add Bluetooth printer setup instructions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Run Full Test Suite

**Files:**
- None (verification only)

**Step 1: Run all tests**

Run: `pytest tests/ -v`

Expected: All tests PASS

**Step 2: If any tests fail, fix them**

Review failures and update code/tests as needed.

**Step 3: Run tests with coverage**

Run: `pytest tests/ --cov=custom_components.phomemo_d30 --cov-report=term-missing`

Expected: High coverage (>80%)

**Step 4: Commit any fixes**

```bash
git add <fixed-files>
git commit -m "test: fix test failures

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Manual Testing Checklist

**Files:**
- None (manual verification)

**Step 1: Test mock driver**

1. Start Home Assistant: `hass -c ./config --debug`
2. Add integration with mock driver
3. Verify configuration saves
4. Send MQTT print message
5. Check image saved to configured path

**Step 2: Test Bluetooth driver (if D30 hardware available)**

1. Power on D30, enable Bluetooth
2. Check HA Bluetooth integration shows D30
3. Add integration with Bluetooth driver
4. Send MQTT print message
5. Verify label prints on D30

**Step 3: Test error scenarios**

1. Try Bluetooth with printer off (should show helpful error)
2. Try mock with invalid save path (should handle gracefully)

**Step 4: Document any issues**

Create GitHub issues for any bugs found.

---

## Success Criteria

- [ ] License changed to GPL-3.0 with attribution
- [ ] bleak dependency added to manifest
- [ ] D30 protocol code vendored and tested
- [ ] BluetoothPhomemoDriver implemented and tested
- [ ] Config flow supports driver selection
- [ ] Bluetooth device discovery works
- [ ] Driver instantiation works for both types
- [ ] Translation strings added
- [ ] README updated with Bluetooth instructions
- [ ] All tests pass
- [ ] Mock driver still works
- [ ] Manual testing completed

## Next Steps After Implementation

1. Test with real D30 hardware
2. Tune Bluetooth chunk size and delays if needed
3. Add more robust error handling based on real-world usage
4. Consider adding sensor entities for print statistics
5. Publish to HACS

## References

- Design doc: `2026-01-30-phomemo-tools-integration-design.md`
- phomemo-tools: https://github.com/vivier/phomemo-tools
- Home Assistant Bluetooth: https://www.home-assistant.io/integrations/bluetooth/
- bleak library: https://bleak.readthedocs.io/
