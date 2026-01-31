# Development Guide

This guide covers the development setup for the Phomemo D30 Home Assistant integration.

## Prerequisites

- Docker Desktop installed and running
- Visual Studio Code with Dev Containers extension
- Git

## Getting Started

### 1. Open in Dev Container

The project uses VS Code Dev Containers for a consistent development environment.

1. Open this folder in VS Code
2. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
3. Select: **"Dev Containers: Reopen in Container"**
4. Wait for container to build (first time takes a few minutes)

The devcontainer will automatically:
- Set up Python 3.11
- Install all dependencies from `requirements_dev.txt`
- Install Home Assistant
- Forward port 8123 for HA web interface

### 2. Verify Setup

Once inside the container:

```bash
# Check Python version
python --version  # Should show Python 3.11.x

# Check dependencies
pip list | grep pytest
pip list | grep homeassistant
```

## Running Home Assistant

### Option 1: VS Code Debugger (Recommended)

1. Press **F5** or go to Run and Debug panel (`Cmd+Shift+D`)
2. Select **"Home Assistant"** from the dropdown
3. Click the green play button
4. Wait for Home Assistant to start
5. Open browser to: **http://localhost:8123**

The integration is symlinked from `config/custom_components/phomemo_d30` so changes are reflected immediately.

### Option 2: Terminal

```bash
# Start Home Assistant manually
hass -c ./config --debug
```

### Configure the Integration

1. Go to: **Settings** → **Devices & Services**
2. Click: **Add Integration**
3. Search: **Phomemo D30**
4. Follow setup wizard

## Development Workflow

### Test-Driven Development (Recommended)

```bash
# 1. Write failing test
# 2. Run test to verify it fails
pytest tests/custom_components/phomemo_d30/test_models.py -v

# 3. Write implementation
# 4. Run test to verify it passes
pytest tests/custom_components/phomemo_d30/test_models.py -v

# 5. Commit
git add . && git commit -m "feat: add feature"
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/custom_components/phomemo_d30/test_init.py -v

# Run with coverage
pytest tests/ -v --cov=custom_components.phomemo_d30 --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
black custom_components/ tests/

# Lint code
ruff check custom_components/ tests/

# Or use VS Code tasks:
# Cmd+Shift+P → "Tasks: Run Task" → Select task
```

## Project Structure

```
.
├── custom_components/
│   └── phomemo_d30/          # Integration code
│       ├── __init__.py       # Integration setup
│       ├── manifest.json     # Integration metadata
│       ├── const.py          # Constants
│       ├── models.py         # Data models
│       ├── queue.py          # Print queue manager
│       ├── config_flow.py    # Config flow UI
│       └── phomemo/          # Printer drivers
│           ├── driver.py     # Mock & Bluetooth drivers
│           └── exceptions.py # Custom exceptions
├── tests/                    # Pytest tests
│   └── custom_components/
│       └── phomemo_d30/
├── config/                   # HA test configuration
│   ├── configuration.yaml    # HA config
│   └── custom_components/    # Symlink to integration
├── .devcontainer/
│   └── devcontainer.json     # Dev container config
├── .vscode/
│   ├── launch.json          # Debug configurations
│   └── tasks.json           # VS Code tasks
└── docs/
    └── plans/               # Implementation plans
```

## MQTT Testing

### Using Home Assistant Developer Tools

1. Go to: **Developer Tools** → **Services**
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

### Using mosquitto_pub (in container)

```bash
# Install mosquitto client if needed
apt-get update && apt-get install -y mosquitto-clients

# Publish test message
mosquitto_pub -h localhost -t "homeassistant/phomemo/print" -m '{
  "image": "iVBORw0KGgo...(base64)...",
  "width": 50,
  "height": 30,
  "darkness": 5,
  "rotate": 0
}'
```

## Mock Mode Testing

The integration includes a mock printer driver for testing without hardware:

1. Configure integration in **mock mode**
2. Set `mock_save_path` to `/config/phomemo_test_prints`
3. Send MQTT messages
4. Check saved images:
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
# In container
tail -f config/home-assistant.log

# Or in HA UI
# Settings → System → Logs
```

### VS Code Debugging

1. Set breakpoints in your code
2. Press **F5** to start HA in debug mode
3. Breakpoints will be hit when code executes
4. Use debug console to inspect variables

## Useful VS Code Commands

- **F5** - Start Home Assistant (debug mode)
- **Cmd+Shift+P** - Command Palette
- **Cmd+Shift+B** - Run Build Task

### Available Tasks

- Run Tests
- Run Tests with Coverage
- Format Code
- Lint Code

## Troubleshooting

### Dev Container Won't Start

```bash
# Check Docker is running
docker ps

# Rebuild container
# Cmd+Shift+P → "Dev Containers: Rebuild Container"
```

### Home Assistant Won't Start

```bash
# Check logs for errors
tail -f config/home-assistant.log

# Try starting manually to see errors
hass -c ./config --debug
```

### Tests Failing

```bash
# Reinstall dependencies
pip install -r requirements_dev.txt

# Clear pytest cache
rm -rf .pytest_cache/
pytest tests/ -v
```

### Integration Not Loading

```bash
# Verify symlink exists
ls -la config/custom_components/phomemo_d30

# Check manifest.json is valid
cat custom_components/phomemo_d30/manifest.json | python -m json.tool

# Restart Home Assistant after code changes
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Follow TDD workflow (write tests first)
4. Run tests: `pytest tests/ -v`
5. Format code: `black custom_components/ tests/`
6. Lint code: `ruff check custom_components/ tests/`
7. Commit with conventional commits: `feat:`, `fix:`, `docs:`, etc.
8. Push and create a Pull Request

## References

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Homebox MQTT Integration](https://blog.fuzzymistborn.com/homebox-labels-over-mqtt/)
- [vivier/phomemo-tools](https://github.com/vivier/phomemo-tools)
- Implementation Plan: `docs/plans/2026-01-29-phomemo-d30-implementation-plan.md`
