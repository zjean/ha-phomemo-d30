# Phomemo-Tools Bluetooth Driver Integration Design

**Date:** 2026-01-30
**Status:** Approved
**License Change:** MIT → GPL-3.0

## Overview

Integrate the phomemo-tools library's D30 protocol implementation to create a real Bluetooth driver alongside the existing mock driver. Users will be able to select between mock and Bluetooth drivers via configuration, with Bluetooth device discovery through Home Assistant's Bluetooth integration.

## License Change

**Required:** Change project license from MIT to GPL-3.0

- phomemo-tools is GPL-3.0 licensed
- Vendoring GPL-3.0 code requires the entire project to be GPL-3.0
- GPL-3.0 is compatible with Home Assistant
- Update LICENSE file and README.md
- Add attribution to vivier/phomemo-tools in all vendored code headers

**Attribution format:**
```python
# Adapted from phomemo-tools by Laurent Vivier
# Original: https://github.com/vivier/phomemo-tools
# License: GPL-3.0
```

## Architecture

### Directory Structure

```
custom_components/phomemo_d30/phomemo/
├── driver.py           # PhomemoDriver ABC, MockPhomemoDriver (existing)
├── bluetooth_driver.py # NEW: BluetoothPhomemoDriver
├── protocol.py         # NEW: D30 protocol (vendored from phomemo-tools)
└── exceptions.py       # Existing exceptions
```

### Driver Selection

**Configuration field:**
```python
driver_type: "mock" | "bluetooth"
```

**Instantiation in `__init__.py`:**
```python
if config["driver_type"] == "mock":
    driver = MockPhomemoDriver(
        save_path=config["save_path"],
        print_delay=config.get("print_delay", 2.0),
        failure_rate=config.get("failure_rate", 0.0)
    )
else:  # bluetooth
    driver = BluetoothPhomemoDriver(
        hass=hass,
        bluetooth_address=config["bluetooth_address"]
    )
```

Both drivers implement the `PhomemoDriver` interface, so queue and MQTT handling remain unchanged.

## Protocol Implementation

### Vendoring phomemo-tools

Extract and adapt relevant Python code from phomemo-tools into `protocol.py`:

**Key components:**
1. **Image preprocessing** - Convert PIL Image to D30 format (1-bit monochrome, dithered)
2. **Protocol encoding** - Generate D30 Bluetooth protocol byte sequences
3. **Print commands** - Header, image data chunks, footer/print trigger

**Adaptations needed:**
- phomemo-tools writes to stdout/file descriptors (CUPS)
- We need functions that return byte sequences
- Convert synchronous operations to async-compatible (use `asyncio.to_thread()` for PIL)

**API structure:**
```python
# protocol.py

def preprocess_image(
    image: Image,
    width: int,
    height: int,
    darkness: int
) -> Image:
    """Convert image to D30 format (monochrome, dithered).

    Adapted from phomemo-tools by Laurent Vivier.
    """
    # Vendor phomemo-tools image processing logic
    pass

def encode_print_data(
    image: Image,
    darkness: int,
    rotate: int
) -> bytes:
    """Encode image as D30 protocol bytes.

    Adapted from phomemo-tools by Laurent Vivier.
    Returns complete byte sequence to send over Bluetooth.
    """
    # Vendor phomemo-tools protocol encoding
    pass
```

## BluetoothPhomemoDriver Implementation

### Class Structure

```python
# bluetooth_driver.py

from homeassistant.components import bluetooth
from bleak import BleakClient
from typing import Optional

class BluetoothPhomemoDriver(PhomemoDriver):
    """Bluetooth driver using Home Assistant's Bluetooth integration."""

    def __init__(self, hass, bluetooth_address: str):
        """Initialize Bluetooth driver.

        Args:
            hass: Home Assistant instance
            bluetooth_address: MAC address from discovered device
        """
        self._hass = hass
        self._address = bluetooth_address
        self._client: Optional[BleakClient] = None
        self._connected = False
        self._write_characteristic = None
```

### Connection Flow

```python
async def connect(self) -> None:
    """Connect to D30 via Home Assistant Bluetooth."""
    # 1. Get BLE device from HA's Bluetooth integration
    ble_device = bluetooth.async_ble_device_from_address(
        self._hass,
        self._address
    )

    # 2. Create BleakClient and connect
    self._client = BleakClient(ble_device)
    await self._client.connect()

    # 3. Discover printer's write characteristic
    # (likely serial port profile or custom characteristic)
    services = await self._client.get_services()
    self._write_characteristic = # ... find write characteristic

    self._connected = True
```

### Printing Flow

```python
async def print(self, job: PrintJob) -> None:
    """Print a job via Bluetooth.

    Raises:
        FatalError: Invalid image format, not connected
        RecoverableError: Connection timeout, BLE disconnection
    """
    if not self._connected:
        raise FatalError("Bluetooth driver not connected")

    # 1. Preprocess image (run in thread pool to avoid blocking)
    processed_image = await asyncio.to_thread(
        protocol.preprocess_image,
        job.image, job.width, job.height, job.darkness
    )

    # 2. Encode to D30 protocol bytes
    print_data = await asyncio.to_thread(
        protocol.encode_print_data,
        processed_image, job.darkness, job.rotate
    )

    # 3. Split into chunks (BLE MTU limits, typically 512 bytes)
    chunk_size = 512
    for i in range(0, len(print_data), chunk_size):
        chunk = print_data[i:i+chunk_size]
        await self._client.write_gatt_char(
            self._write_characteristic,
            chunk
        )
        # Add small delay between chunks if needed
        await asyncio.sleep(0.01)
```

### Error Handling

- **Connection timeouts** → `RecoverableError` (queue retries)
- **Invalid image format** → `FatalError` (don't retry)
- **BLE disconnection during print** → `RecoverableError`
- **Bluetooth adapter not available** → `FatalError` with helpful message

## Configuration Flow

### Step 1: Driver Type Selection

```python
# config_flow.py

async def async_step_user(self, user_input=None):
    """Handle initial driver type selection."""
    if user_input is not None:
        if user_input["driver_type"] == "mock":
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
```

### Step 2a: Mock Driver Configuration

```python
async def async_step_mock(self, user_input=None):
    """Configure mock driver."""
    schema = vol.Schema({
        vol.Required("save_path", default="/config/phomemo_prints"): str,
        vol.Optional("print_delay", default=2.0): vol.Coerce(float),
        vol.Optional("failure_rate", default=0.0): vol.All(
            vol.Coerce(float),
            vol.Range(min=0.0, max=1.0)
        )
    })

    if user_input is not None:
        return self.async_create_entry(
            title="Phomemo D30 (Mock)",
            data={**user_input, "driver_type": "mock"}
        )

    return self.async_show_form(step_id="mock", data_schema=schema)
```

### Step 2b: Bluetooth Device Selection

```python
async def async_step_bluetooth(self, user_input=None):
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

## Testing Strategy

### Unit Tests

**`tests/custom_components/phomemo_d30/test_protocol.py`:**
- Test image preprocessing with various input formats
- Test protocol encoding produces expected byte sequences
- Test with known good images/outputs from phomemo-tools

**`tests/custom_components/phomemo_d30/test_bluetooth_driver.py`:**
- Mock BleakClient
- Test connection/disconnection flows
- Test error handling (timeouts, disconnections)
- Test print data chunking

**Existing tests:**
- Keep `test_mock_driver.py` (no changes)
- Keep `test_queue.py` (works with both driver types)
- Keep `test_models.py` (no changes)

### Integration Tests

- Test config flow with mocked Bluetooth discovery
- Test driver instantiation for both types
- Test queue processes jobs with both driver types

### Manual Testing

1. **Mock driver** - Verify existing functionality still works
2. **Bluetooth discovery** - Check D30 appears in device list
3. **Real printing** - Test with actual D30 hardware
4. **Error scenarios** - Test connection failures, disconnections during print

## Implementation Steps

### 1. License & Attribution
- [ ] Update LICENSE file to GPL-3.0
- [ ] Update README.md license section
- [ ] Add GPL-3.0 headers to all new files

### 2. Vendor Protocol Code
- [ ] Clone phomemo-tools repository
- [ ] Extract D30 protocol Python code
- [ ] Create `custom_components/phomemo_d30/phomemo/protocol.py`
- [ ] Adapt for async (use `asyncio.to_thread()` where needed)
- [ ] Add GPL-3.0 header with attribution

### 3. Implement BluetoothPhomemoDriver
- [ ] Create `custom_components/phomemo_d30/phomemo/bluetooth_driver.py`
- [ ] Implement `connect()`, `disconnect()`, `is_connected()`, `print()`
- [ ] Use Home Assistant's Bluetooth APIs
- [ ] Handle BLE characteristics discovery
- [ ] Implement chunked data transmission

### 4. Update Config Flow
- [ ] Add driver type selection step
- [ ] Add mock driver config step
- [ ] Add Bluetooth device selection step
- [ ] Handle "no devices found" case

### 5. Update Dependencies
- [ ] Add `bleak` to `manifest.json` requirements
- [ ] Update `requirements_dev.txt` with `bleak` for testing

### 6. Add Tests
- [ ] Create `test_protocol.py`
- [ ] Create `test_bluetooth_driver.py`
- [ ] Update `test_init.py` for driver instantiation

### 7. Update Documentation
- [ ] Update README.md with Bluetooth setup instructions
- [ ] Add troubleshooting section for Bluetooth issues
- [ ] Document driver selection in config

## Dependencies

**New requirement:**
```json
"requirements": ["bleak>=0.21.0"]
```

`bleak` is a cross-platform Bluetooth Low Energy library that works with Home Assistant's Bluetooth integration.

## Error Messages

**User-facing error messages:**

- **No Bluetooth devices found:** "No Phomemo printers discovered. Make sure your D30 is powered on and Bluetooth is enabled."
- **Connection timeout:** "Could not connect to printer. Check Bluetooth range and try again."
- **Bluetooth not available:** "Home Assistant's Bluetooth integration is not enabled. Please enable it in Settings → Devices & Services."

## Success Criteria

- [ ] Users can select between mock and Bluetooth drivers in config
- [ ] Bluetooth devices are discovered via HA's Bluetooth integration
- [ ] Bluetooth driver successfully prints to real D30 hardware
- [ ] Mock driver continues to work as before
- [ ] All tests pass
- [ ] License properly changed to GPL-3.0 with attribution

## References

- [vivier/phomemo-tools](https://github.com/vivier/phomemo-tools) - D30 support added in v2.1 (Dec 2025)
- [Home Assistant Bluetooth Integration](https://www.home-assistant.io/integrations/bluetooth/)
- [Bleak Documentation](https://bleak.readthedocs.io/)
- GPL-3.0 License: https://www.gnu.org/licenses/gpl-3.0.html
