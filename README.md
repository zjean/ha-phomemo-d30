# Phomemo D30 Home Assistant Integration - Development

A Home Assistant custom integration for the Phomemo D30 label printer. Print labels via MQTT (e.g., from Homebox) using Bluetooth or mock mode.

## Development Setup

### Prerequisites

- Docker Desktop installed and running
- Visual Studio Code with Dev Containers extension
- Git

### Getting Started

1. **Open in Dev Container:**
   ```bash
   # In VS Code:
   # - Open this folder
   # - Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)
   # - Select: "Dev Containers: Reopen in Container"
   # - Wait for container to build (first time takes a few minutes)
   ```

2. **Verify Setup:**
   ```bash
   # Once inside the container, check Python version:
   python --version  # Should show Python 3.11.x

   # Check dependencies are installed:
   pip list | grep pytest
   ```

## Running Home Assistant

### Option 1: Using VS Code Debugger (Recommended)

1. **Press F5** or go to Run and Debug panel (Cmd+Shift+D)
2. Select **"Home Assistant"** from the dropdown
3. Click the green play button
4. Wait for Home Assistant to start (first time downloads dependencies)
5. Open browser to: **http://localhost:8123**

### Option 2: Using Terminal

```bash
# Start Home Assistant manually:
hass -c ./config --debug

# The integration will be loaded from:
# config/custom_components/phomemo_d30 (symlinked)
```

### Option 3: Run Tests (TDD Approach)

```bash
# Run all tests:
pytest tests/ -v

# Run specific test file:
pytest tests/custom_components/phomemo_d30/test_init.py -v

# Run with coverage:
pytest tests/ -v --cov=custom_components.phomemo_d30 --cov-report=html
```

## Development Workflow

### 1. Test-Driven Development (Recommended)

```bash
# 1. Write failing test
# 2. Run test to verify it fails:
pytest tests/custom_components/phomemo_d30/test_models.py -v

# 3. Write implementation
# 4. Run test to verify it passes:
pytest tests/custom_components/phomemo_d30/test_models.py -v

# 5. Commit
git add . && git commit -m "feat: add feature"
```

### 2. Manual Testing in Home Assistant

1. **Start HA** (F5 or `hass -c ./config`)
2. **Configure the integration:**
   - Go to: Settings → Devices & Services
   - Click: Add Integration
   - Search: Phomemo D30
   - Follow setup wizard
3. **Test the integration** manually

### 3. Code Quality

```bash
# Format code:
black custom_components/ tests/

# Lint code:
ruff check custom_components/ tests/

# Or use VS Code tasks:
# Cmd+Shift+P → "Tasks: Run Task" → Select task
```

## Project Structure

```
.
├── custom_components/
│   └── phomemo_d30/          # The integration code
│       ├── __init__.py       # Integration setup
│       ├── manifest.json     # Integration metadata
│       ├── const.py          # Constants
│       ├── models.py         # Data models
│       ├── queue.py          # Print queue manager
│       ├── coordinator.py    # MQTT & state coordinator
│       ├── sensor.py         # Sensor entities
│       └── phomemo/          # Printer drivers
│           ├── driver.py     # Mock & Bluetooth drivers
│           └── exceptions.py # Custom exceptions
├── tests/                    # Pytest tests
│   └── custom_components/
│       └── phomemo_d30/
├── config/                   # HA test configuration
│   ├── configuration.yaml    # HA config
│   └── custom_components/    # Symlink to integration
├── .vscode/
│   ├── launch.json          # Debug configurations
│   └── tasks.json           # VS Code tasks
└── docs/
    └── plans/               # Implementation plans
```

## MQTT Testing

### Using mosquitto (in container):

```bash
# Install mosquitto client (if needed):
apt-get update && apt-get install -y mosquitto-clients

# Publish test message:
mosquitto_pub -h localhost -t "homeassistant/phomemo/print" -m '{
  "image": "iVBORw0KGgo...(base64)...",
  "width": 50,
  "height": 30,
  "darkness": 5,
  "rotate": 0
}'
```

### Using Home Assistant Developer Tools:

1. Go to: Developer Tools → Services
2. Service: `mqtt.publish`
3. Service Data:
```yaml
topic: homeassistant/phomemo/print
payload: |
  {
    "image": "iVBORw0KGgo...",
    "width": 50,
    "height": 30
  }
```

## Mock Mode Testing

The integration includes a mock printer driver for testing without hardware:

1. Configure integration in **mock mode**
2. Set `mock_save_path` to `/config/phomemo_test_prints`
3. Send MQTT messages
4. Check saved images in the configured path:
```bash
ls -la config/phomemo_test_prints/
```

## Debugging

### Enable Debug Logging

Edit `config/configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.phomemo_d30: debug
```

### View Logs

```bash
# In container:
tail -f config/home-assistant.log

# Or in HA UI:
# Settings → System → Logs
```

### Debugging with VS Code

1. Set breakpoints in your code
2. Press F5 to start HA in debug mode
3. Breakpoints will be hit when code executes
4. Use debug console to inspect variables

## Useful VS Code Commands

- **F5** - Start Home Assistant (debug mode)
- **Cmd+Shift+P** - Command Palette
- **Cmd+Shift+B** - Run Build Task
- Tasks available:
  - Run Tests
  - Run Tests with Coverage
  - Format Code
  - Lint Code

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
   - Select driver type: **Bluetooth** (for real D30 printer)
   - Choose your printer from the discovered devices list
   - Configure MQTT topic (default: `homeassistant/phomemo/print`)

2. **If your printer doesn't appear:**
   - Make sure it's powered on and in Bluetooth range
   - Check that HA's Bluetooth integration is working: Settings → Devices & Services → Bluetooth
   - Try restarting the D30 printer
   - Ensure no other device is connected to the printer

### Driver Selection

You can configure multiple instances of the integration:

- **Mock Driver** - For testing without hardware (saves images to disk)
- **Bluetooth Driver** - For real D30 printer via Bluetooth

Each instance can be configured with its own MQTT topic, allowing you to run both mock and real printers simultaneously for testing.

### Bluetooth Printing

Once configured, send print jobs via MQTT to your configured topic:

```bash
mosquitto_pub -h localhost -t "homeassistant/phomemo/print" -m '{
  "image": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
  "width": 50,
  "height": 30
}'
```

The integration will:
1. Connect to the D30 via Bluetooth
2. Process and convert the image to D30 format
3. Send the data to the printer
4. Handle reconnection if the connection is lost

## Troubleshooting

### Dev Container Won't Start

```bash
# Check Docker is running:
docker ps

# Rebuild container:
# Cmd+Shift+P → "Dev Containers: Rebuild Container"
```

### Home Assistant Won't Start

```bash
# Check logs for errors:
tail -f config/home-assistant.log

# Try starting manually to see errors:
hass -c ./config --debug
```

### Tests Failing

```bash
# Install dependencies again:
pip install -r requirements_dev.txt

# Clear pytest cache:
rm -rf .pytest_cache/
pytest tests/ -v
```

### Integration Not Loading

```bash
# Verify symlink exists:
ls -la config/custom_components/phomemo_d30

# Check manifest.json is valid:
cat custom_components/phomemo_d30/manifest.json | python -m json.tool

# Restart Home Assistant after code changes
```

## Contributing

1. Follow TDD workflow (write tests first)
2. Run tests before committing: `pytest tests/ -v`
3. Format code: `black custom_components/ tests/`
4. Lint code: `ruff check custom_components/ tests/`
5. Commit with conventional commits: `feat:`, `fix:`, `docs:`, etc.

## Next Steps

- [ ] Implement Bluetooth driver (currently using mock mode)
- [ ] Test with real Phomemo D30 hardware
- [ ] Add more sensor entities (statistics, last print, etc.)
- [ ] Publish to HACS
- [ ] Create documentation for end users

## References

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Homebox MQTT Integration](https://blog.fuzzymistborn.com/homebox-labels-over-mqtt/)
- [vivier/phomemo-tools](https://github.com/vivier/phomemo-tools)
- Implementation Plan: `docs/plans/2026-01-29-phomemo-d30-implementation-plan.md`

## License

GPL-3.0 License

This project includes code adapted from [phomemo-tools](https://github.com/vivier/phomemo-tools) by Laurent Vivier, which is licensed under GPL-3.0.
