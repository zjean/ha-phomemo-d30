# Home Assistant Core Dev Container Setup Guide

This guide explains how to set up the official Home Assistant core development environment for developing the Phomemo D30 custom integration.

## Why Use the Official HA Core Dev Container?

The official dev container provides:
- ✅ All dependencies pre-configured and compatible
- ✅ No josepy/acme version conflicts
- ✅ Full Home Assistant instance for testing
- ✅ Official VS Code tasks and launch configurations
- ✅ Proper testing environment
- ✅ Matches production HA environment exactly

## Setup Steps

### Step 1: Clone Home Assistant Core Repository

```bash
# Navigate to your projects directory
cd ~/prive/

# Clone the official Home Assistant core repository
git clone https://github.com/home-assistant/core.git ha-core

# Navigate into the repository
cd ha-core
```

This downloads the entire Home Assistant codebase (~500MB).

### Step 2: Open in VS Code Dev Container

1. **Open the `ha-core` folder in VS Code:**
   ```bash
   code ~/prive/ha-core
   ```

2. **VS Code will detect `.devcontainer/devcontainer.json`** and show a notification:
   - Click: **"Reopen in Container"**
   - Or use: `Cmd+Shift+P` → "Dev Containers: Reopen in Container"

3. **Wait for container to build** (10-20 minutes first time):
   - Downloads official HA dev container image
   - Installs all Python dependencies
   - Sets up development environment
   - Configures VS Code extensions

4. **Verify setup** once container is ready:
   ```bash
   # Check Python version (should be 3.12+)
   python --version

   # Check Home Assistant is available
   hass --version

   # Check you're in the container (look for "vscode@..." in terminal)
   whoami
   ```

### Step 3: Link Your Custom Integration

You have two options for using your custom integration with HA core:

#### Option A: Symlink (Recommended for Development)

This keeps your integration code in the separate repository but makes it available to HA:

```bash
# Create symlink from your integration to HA components directory
ln -s /workspaces/label-printer/.worktrees/phomemo-integration/custom_components/phomemo_d30 \
      /workspaces/core/homeassistant/components/phomemo_d30

# Verify symlink was created
ls -la /workspaces/core/homeassistant/components/ | grep phomemo
```

**Pros:**
- Changes in your repo automatically appear in HA
- Can commit/push from your separate repo
- Easier to manage as a standalone integration

**Cons:**
- Need to ensure both paths are available in container

#### Option B: Copy Integration Files

Copy your integration into the HA core components directory:

```bash
# Copy integration to HA components
cp -r /workspaces/label-printer/.worktrees/phomemo-integration/custom_components/phomemo_d30 \
     /workspaces/core/homeassistant/components/

# Verify it was copied
ls /workspaces/core/homeassistant/components/phomemo_d30/
```

**Pros:**
- Simpler, no symlink dependencies
- Easier to test in isolation

**Cons:**
- Need to copy files after each change
- Have to manage two copies of the code

### Step 4: Configure Home Assistant

Create a test configuration:

```bash
# The config directory should already exist
cd /workspaces/core/config

# Edit configuration.yaml to add your integration
cat >> configuration.yaml << 'EOF'

# Enable logging for development
logger:
  default: info
  logs:
    homeassistant.components.phomemo_d30: debug

# Enable MQTT (required for your integration)
mqtt:
  broker: localhost
  port: 1883
EOF
```

### Step 5: Run Home Assistant

#### Method 1: Using VS Code Task (Recommended)

1. Press `Cmd+Shift+P`
2. Select: **"Tasks: Run Task"**
3. Choose: **"Run Home Assistant Core"** (or similar task name)
4. Wait for HA to start
5. Open browser to: **http://localhost:8123**

#### Method 2: Using Terminal

```bash
# Start Home Assistant in development mode
hass -c config --debug

# Or use the script shortcut
script/run
```

#### Method 3: Using VS Code Debugger

1. Go to Run and Debug panel (`Cmd+Shift+D`)
2. Select: **"Home Assistant"** from dropdown
3. Press **F5** to start with debugger attached
4. Set breakpoints in your integration code
5. Debug when your code is executed

### Step 6: Add Your Integration to HA

Once Home Assistant is running:

1. **Navigate to**: http://localhost:8123
2. **Complete initial setup** (create user account)
3. **Go to**: Settings → Devices & Services
4. **Click**: Add Integration
5. **Search**: "Phomemo D30"
6. **Configure** your integration

## Development Workflow

### Making Changes to Your Integration

If using **symlink (Option A)**:
```bash
# Edit files in your original repo
cd /workspaces/label-printer/.worktrees/phomemo-integration
# Make changes to custom_components/phomemo_d30/...

# Restart HA to load changes
# Stop HA (Ctrl+C in terminal)
# Start again: hass -c config
```

If using **copy (Option B)**:
```bash
# Edit files in HA core
cd /workspaces/core/homeassistant/components/phomemo_d30
# Make changes...

# Copy changes back to your repo
cp -r /workspaces/core/homeassistant/components/phomemo_d30/* \
     /workspaces/label-printer/.worktrees/phomemo-integration/custom_components/phomemo_d30/
```

### Running Tests

```bash
# Run your integration tests
pytest tests/components/phomemo_d30/ -v

# Or copy your tests to HA core first
cp -r /workspaces/label-printer/.worktrees/phomemo-integration/tests/custom_components/phomemo_d30 \
     /workspaces/core/tests/components/

# Then run
pytest tests/components/phomemo_d30/ -v
```

### Hot Reload

For some changes, you can reload without restarting:

1. **Go to**: Developer Tools → YAML
2. **Click**: Reload Custom Components
3. Or use service: `homeassistant.reload_config_entry`

## Troubleshooting

### Container Won't Build

```bash
# Check Docker is running
docker ps

# Try rebuilding from scratch
# In VS Code: Cmd+Shift+P → "Dev Containers: Rebuild Container Without Cache"
```

### Integration Not Loading

```bash
# Check integration files exist
ls -la /workspaces/core/homeassistant/components/phomemo_d30/

# Check manifest.json is valid
cat /workspaces/core/homeassistant/components/phomemo_d30/manifest.json

# Check HA logs
tail -f config/home-assistant.log | grep phomemo
```

### Symlink Not Working

```bash
# Verify both paths exist and are accessible
ls -la /workspaces/label-printer/.worktrees/phomemo-integration/custom_components/phomemo_d30/
ls -la /workspaces/core/homeassistant/components/

# If symlink broken, recreate it
rm /workspaces/core/homeassistant/components/phomemo_d30
ln -s /workspaces/label-printer/.worktrees/phomemo-integration/custom_components/phomemo_d30 \
      /workspaces/core/homeassistant/components/phomemo_d30
```

### Changes Not Appearing

```bash
# Restart Home Assistant completely
# Stop HA (Ctrl+C)
# Clear cache
rm -rf config/.storage/
# Start again
hass -c config --debug
```

## Useful Commands

```bash
# Check HA version
hass --version

# Validate configuration
hass --script check_config -c config

# Run specific component tests
pytest tests/components/phomemo_d30/ -v -k "test_name"

# Format code (in HA core style)
python -m black homeassistant/components/phomemo_d30/

# Lint code
python -m pylint homeassistant/components/phomemo_d30/

# Type check
python -m mypy homeassistant/components/phomemo_d30/
```

## Keeping Both Environments

You can keep both setups:

1. **HA Core Dev Container** (`~/prive/ha-core/`)
   - For running full HA instance
   - For integration testing
   - For debugging

2. **Standalone Integration** (`~/prive/label-printer/`)
   - For TDD development with pytest
   - For version control and commits
   - For HACS distribution

**Workflow:**
1. Develop and test with pytest in standalone repo
2. Copy/symlink to HA core for manual testing
3. Commit changes in standalone repo
4. Publish from standalone repo to HACS

## Next Steps

After setup:

1. ✅ Verify HA starts and runs
2. ✅ Add your integration through the UI
3. ✅ Test MQTT message handling
4. ✅ Test mock printer functionality
5. ✅ Debug any issues using VS Code debugger
6. ✅ Continue implementing remaining tasks

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Setting up Dev Environment](https://developers.home-assistant.io/docs/development_environment/)
- [Creating Custom Integration](https://developers.home-assistant.io/docs/creating_component_index/)
- [Integration Testing](https://developers.home-assistant.io/docs/development_testing/)

---

**Current Status:** Guide created, ready to execute setup steps.
