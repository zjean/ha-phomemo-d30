#!/bin/bash

set -e

echo "🔧 Setting up Home Assistant testing environment for Phomemo D30..."

# Create necessary directories
mkdir -p ha_config
mkdir -p test_prints
mkdir -p mosquitto/{config,data,log}

# Set permissions
chmod -R 777 mosquitto/data mosquitto/log
chmod -R 755 test_prints

# Create initial HA configuration if it doesn't exist
if [ ! -f "ha_config/configuration.yaml" ]; then
    echo "📝 Creating initial Home Assistant configuration..."
    cat > ha_config/configuration.yaml << 'YAML'
# Home Assistant Configuration for Phomemo D30 Testing

default_config:

# Enable logger for debugging
logger:
  default: info
  logs:
    custom_components.phomemo_d30: debug

# MQTT Configuration
mqtt:
  broker: mosquitto
  port: 1883
  discovery: true
  discovery_prefix: homeassistant

# Enable Bluetooth (if available)
bluetooth:

# HTTP Configuration
http:
  server_host: 0.0.0.0
  server_port: 8123
YAML
fi

# Create .gitignore for Docker artifacts
if [ ! -f ".dockerignore" ]; then
    cat > .dockerignore << 'IGNORE'
ha_config/
test_prints/
mosquitto/data/
mosquitto/log/
.pytest_cache/
__pycache__/
*.pyc
.coverage
IGNORE
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Start containers:      docker compose up -d"
echo "  2. View logs:             docker compose logs -f homeassistant"
echo "  3. Access Home Assistant: http://localhost:8123"
echo "  4. Stop containers:       docker compose down"
echo ""
echo "🔍 Testing the integration:"
echo "  1. Go to Settings → Devices & Services"
echo "  2. Click '+ Add Integration'"
echo "  3. Search for 'Phomemo D30'"
echo "  4. Select 'Mock' driver for testing without hardware"
echo ""
echo "📨 Send test print via MQTT:"
echo "  docker exec mosquitto-phomemo mosquitto_pub \\"
echo "    -t 'homeassistant/phomemo/print' \\"
echo "    -m '{\"image\":\"iVBORw0KGgoAAAANSUhEUg...\",\"width\":50,\"height\":30}'"
echo ""
