# Phomemo D30 Home Assistant Integration - Design Document

**Date:** 2026-01-29
**Status:** Approved
**Author:** Design Session with User

## Overview

A Home Assistant custom integration that receives label images from Homebox via MQTT and prints them to a Phomemo D30 label printer connected via Bluetooth. The integration includes mock mode for testing without hardware.

## Requirements

- Receive base64-encoded PNG images via MQTT from Homebox
- Print to Phomemo D30 via Bluetooth
- Full Home Assistant integration with sensor entities
- Fixed printer settings in configuration
- Custom dimensions per print job via MQTT
- Automatic retry on failure (configurable)
- Sequential print queue
- HACS installation support
- Mock mode for testing without hardware

## Architecture

### Overall Architecture & Components

The integration is a Home Assistant custom component called `phomemo_d30` installable via HACS.

**Core Components:**
1. **MQTT Listener** - Subscribes to configurable MQTT topic(s), receives base64-encoded PNG images with metadata
2. **Print Queue Manager** - Async queue that handles sequential job processing, prevents concurrent prints
3. **Phomemo Driver** - Wrapper around vivier/phomemo-tools that handles Bluetooth communication and actual printing
4. **State Manager** - Tracks printer status, exposes HA sensor entities

**Technology Stack:**
- Python 3.11+ (HA requirement)
- vivier/phomemo-tools (vendored or as dependency)
- HA's built-in MQTT integration (via `homeassistant.components.mqtt`)
- HA's Bluetooth integration for device discovery
- Pillow (PIL) for image processing if needed

**File Structure:**
```
custom_components/phomemo_d30/
├── __init__.py          # Integration setup
├── manifest.json        # HACS metadata
├── config_flow.py       # UI configuration
├── const.py            # Constants
├── coordinator.py      # Data update coordinator
├── sensor.py           # Sensor entities
├── services.yaml       # Service definitions
└── phomemo/
    ├── driver.py       # Phomemo printer driver
    ├── queue.py        # Print queue manager
    └── vendor/         # Vendored vivier/phomemo-tools code
```

## Data Flow & MQTT Integration

**MQTT Message Format:**
```json
{
  "image": "base64_encoded_png_data",
  "width": 50,
  "height": 30,
  "darkness": 5,
  "rotate": 0
}
```

**Data Flow:**
1. Homebox publishes to `homeassistant/phomemo/print` (configurable)
2. MQTT Listener receives and validates message
3. Decodes base64 → PIL Image object
4. Creates PrintJob object with metadata
5. Adds to queue (updates sensor: "queued")
6. Queue processes sequentially
7. Driver prints via Bluetooth or Mock
8. Updates sensor entities on completion

**Mock Driver for Testing:**
The driver supports two modes via config:
```yaml
phomemo_d30:
  bluetooth_mac: "AA:BB:CC:DD:EE:FF"
  mqtt_topic: "homeassistant/phomemo/print"
  mode: "mock"  # or "bluetooth"
  mock_print_delay: 2  # seconds to simulate printing
  mock_save_path: "/config/phomemo_test_prints/"  # save images for inspection
```

When `mode: mock`, it will:
- Simulate Bluetooth connection
- Wait `mock_print_delay` seconds
- Save received images to `mock_save_path` with timestamp
- Return success without actual hardware

## Print Queue & Job Management

**Queue Implementation:**
The `PrintQueue` class uses Python's `asyncio.Queue` for thread-safe async operation.

**Job States:**
- `queued` - Waiting in queue
- `printing` - Currently printing
- `completed` - Successfully printed
- `failed` - Failed after all retries
- `retrying` - Temporary failure, will retry

**Job Structure:**
```python
class PrintJob:
    id: str  # UUID
    image: PIL.Image
    width: int
    height: int
    darkness: int
    rotate: int
    timestamp: datetime
    attempts: int = 0
    max_attempts: int = 3
    status: JobStatus
    error: Optional[str] = None
```

**Processing Logic:**
1. Single async worker pulls from queue
2. Updates job status to `printing`
3. Calls driver to print
4. On failure:
   - If `attempts < max_attempts`: status → `retrying`, wait `retry_delay` (5s default), re-queue
   - Else: status → `failed`, log error
5. On success: status → `completed`
6. All state changes update HA sensors immediately

**Queue Controls:**
The integration exposes HA services:
- `phomemo_d30.print` - Manual print (bypass MQTT)
- `phomemo_d30.clear_queue` - Clear pending jobs
- `phomemo_d30.retry_failed` - Retry last failed job

## Home Assistant Entities & Services

**Sensor Entities:**

1. **`sensor.phomemo_d30_status`**
   - States: `idle`, `printing`, `error`, `disconnected`
   - Attributes: current_job_id, bluetooth_connected, queue_length

2. **`sensor.phomemo_d30_queue`**
   - State: Number of jobs in queue (0-N)
   - Attributes: job_ids[], oldest_job_timestamp

3. **`sensor.phomemo_d30_last_print`**
   - State: Timestamp of last successful print
   - Attributes: job_id, width, height, duration_seconds

4. **`sensor.phomemo_d30_statistics`**
   - State: Total prints today
   - Attributes: total_prints, failed_prints, success_rate, uptime

**Services:**

```yaml
# services.yaml
print:
  description: "Print an image to Phomemo D30"
  fields:
    image_path:
      description: "Path to image file or base64 data"
      example: "/config/www/label.png"
    width:
      description: "Label width in mm"
      example: 50
    height:
      description: "Label height in mm (optional, auto if not set)"
      example: 30

clear_queue:
  description: "Clear all pending print jobs"

retry_failed:
  description: "Retry the last failed print job"
```

## Configuration & Settings

**Config Flow (UI-based setup):**

**Step 1 - Bluetooth Discovery:**
- Auto-discover Phomemo D30 devices via HA Bluetooth
- Allow manual MAC address entry as fallback
- Option to select "Mock Mode" for testing

**Step 2 - MQTT Configuration:**
- MQTT topic to subscribe to (default: `homeassistant/phomemo/print`)
- Requires MQTT integration already configured

**Step 3 - Printer Settings:**
```yaml
# Fixed settings (stored in config entry)
darkness: 5           # 1-7, default 5
speed: normal         # slow/normal/fast
retry_attempts: 3     # Number of retry attempts
retry_delay: 5        # Seconds between retries
queue_max_size: 50    # Prevent infinite queue
```

**Configuration.yaml (Legacy Support):**
Also support YAML config for advanced users:
```yaml
phomemo_d30:
  bluetooth_mac: "AA:BB:CC:DD:EE:FF"
  mqtt_topic: "homeassistant/phomemo/print"
  mode: "bluetooth"  # or "mock"
  darkness: 5
  retry_attempts: 3
  retry_delay: 5
  mock_print_delay: 2
  mock_save_path: "/config/phomemo_test_prints/"
```

**Options Flow:**
Allow reconfiguring settings after setup without deleting/re-adding the integration.

## Error Handling & Retry Logic

**Error Categories:**

**1. Recoverable Errors (will retry):**
- Bluetooth connection timeout
- Temporary device busy
- Transient communication errors
- Action: Retry with exponential backoff (5s, 10s, 20s)

**2. Fatal Errors (fail immediately):**
- Invalid image format
- Image dimensions out of bounds
- Malformed MQTT payload
- Mock mode: simulated random failures (10% rate for testing)
- Action: Move to failed state, log error, update sensors

**3. Connection Errors:**
- Bluetooth device not found
- Device disconnected during print
- Action: Set status to `disconnected`, pause queue, attempt reconnection every 30s

**Error Handling Flow:**
```python
try:
    await driver.print(job)
except RecoverableError as e:
    if job.attempts < max_attempts:
        job.status = "retrying"
        await asyncio.sleep(retry_delay * (2 ** job.attempts))
        await queue.put(job)  # Re-queue
    else:
        job.status = "failed"
        job.error = str(e)
except FatalError as e:
    job.status = "failed"
    job.error = str(e)
    # Don't retry
```

**Logging:**
- Debug: All MQTT messages received
- Info: Print started/completed
- Warning: Retrying after failure
- Error: Fatal errors, max retries exceeded

**Notifications:**
Optional HA notification on persistent failures (configurable).

## Installation & Deployment

**HACS Installation:**

**manifest.json:**
```json
{
  "domain": "phomemo_d30",
  "name": "Phomemo D30 Label Printer",
  "codeowners": ["@yourusername"],
  "config_flow": true,
  "dependencies": ["mqtt", "bluetooth"],
  "documentation": "https://github.com/yourusername/ha-phomemo-d30",
  "iot_class": "local_push",
  "requirements": ["Pillow==10.1.0"],
  "version": "1.0.0"
}
```

**Installation Steps:**
1. Add custom repository to HACS
2. Install "Phomemo D30 Label Printer"
3. Restart Home Assistant
4. Configuration → Integrations → Add Integration → Phomemo D30
5. Follow config flow

**Dependencies:**
- vivier/phomemo-tools: Bundle Python code directly in `custom_components/phomemo_d30/phomemo/vendor/` (avoid external binary deps)
- Pillow: For image processing (already common in HA)
- HA built-in: MQTT, Bluetooth integrations

**Testing Workflow:**
1. Install in mock mode
2. Configure MQTT topic
3. Send test message via MQTT
4. Check `/config/phomemo_test_prints/` for saved images
5. Monitor sensor entities for status updates
6. Once working, switch to bluetooth mode with real device

**Documentation:**
- README with setup instructions
- Example MQTT payloads
- Homebox integration guide
- Troubleshooting common issues

## Development Environment Setup

**VS Code Dev Container (Selected Approach):**

**Setup:**
```yaml
# .devcontainer/devcontainer.json
{
  "name": "Home Assistant",
  "image": "ghcr.io/home-assistant/devcontainer:latest",
  "appPort": ["9123:8123"],
  "postCreateCommand": "container install",
  "extensions": [
    "ms-python.python",
    "ms-python.vscode-pylance"
  ]
}
```

**Development Workflow:**
1. Run HA in dev mode: `hass -c ./config`
2. Enable debug logging for integration in `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.phomemo_d30: debug
```
3. Use mock mode for testing without hardware
4. Test MQTT with `mosquitto_pub` or HA Developer Tools
5. Hot reload: Configuration → YAML → Reload custom integrations

**Testing:**
- Unit tests with pytest
- Mock Bluetooth adapter
- MQTT test harness
- CI/CD with GitHub Actions

## References

- Homebox MQTT example: https://blog.fuzzymistborn.com/homebox-labels-over-mqtt/
- vivier/phomemo-tools: https://github.com/vivier/phomemo-tools
- crabdancing/phomemo-d30: https://github.com/crabdancing/phomemo-d30
- polskafan/phomemo_d30: https://github.com/polskafan/phomemo_d30
