# Docker Testing Guide for Phomemo D30 Integration

This guide will help you test the Phomemo D30 Home Assistant integration using Docker.

## Prerequisites

- Docker and Docker Compose installed
- At least 2GB free disk space
- Ports 8123 (HA) and 1883 (MQTT) available

## Quick Start

### 1. Setup Environment

```bash
./docker-setup.sh
```

This creates all necessary directories and configuration files.

### 2. Start Containers

```bash
docker compose up -d
```

Wait about 30 seconds for Home Assistant to fully start.

### 3. Access Home Assistant

Open your browser to: **http://localhost:8123**

On first run:
1. Create your user account
2. Set up your home details
3. Skip device discovery

### 4. Add the Phomemo D30 Integration

1. Go to: **Settings → Devices & Services**
2. Click: **+ Add Integration** (bottom right)
3. Search: **Phomemo D30**
4. Select driver type:
   - **Mock** - For testing without hardware (recommended)
   - **Bluetooth** - For real D30 printer (requires Bluetooth adapter)

#### Mock Driver Configuration

- **MQTT Topic**: `homeassistant/phomemo/print` (default)
- **Save Path**: `/config/phomemo_prints` (images saved here)
- **Print Delay**: `2.0` seconds (simulate print time)

#### Bluetooth Driver Configuration (Optional)

- Requires USB Bluetooth adapter
- Requires D30 printer powered on
- Select discovered device from list

## Testing the Integration

### Method 1: Using MQTT Command Line

#### Send a simple test print:

```bash
docker exec mosquitto-phomemo mosquitto_pub \
  -t 'homeassistant/phomemo/print' \
  -m '{
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FAAhKDveksOjuAAAAAElFTkSuQmCC",
    "width": 50,
    "height": 30
  }'
```

This sends a tiny 10x10 black square test image.

#### Check the result (Mock Driver):

```bash
ls -lh test_prints/
```

You should see a PNG file with the printed image.

### Method 2: Using Home Assistant Developer Tools

1. Go to: **Developer Tools → Services**
2. Service: `mqtt.publish`
3. Service Data:

```yaml
topic: homeassistant/phomemo/print
payload: |
  {
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FAAhKDveksOjuAAAAAElFTkSuQmCC",
    "width": 50,
    "height": 30
  }
```

### Method 3: Create an Automation

Create an automation that triggers on events:

```yaml
alias: Test Phomemo Print
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: "on"
action:
  - service: mqtt.publish
    data:
      topic: homeassistant/phomemo/print
      payload: |
        {
          "image": "your_base64_image_here",
          "width": 50,
          "height": 30
        }
```

## Viewing Logs

### Home Assistant Logs

```bash
# Follow logs in real-time
docker compose logs -f homeassistant

# View Phomemo-specific logs
docker compose logs homeassistant | grep phomemo_d30

# View last 100 lines
docker compose logs --tail=100 homeassistant
```

### MQTT Logs

```bash
# Follow MQTT messages
docker exec mosquitto-phomemo mosquitto_sub -v -t '#'

# Follow only Phomemo messages
docker exec mosquitto-phomemo mosquitto_sub -v -t 'homeassistant/phomemo/#'
```

## Troubleshooting

### Integration Not Showing Up

1. Check custom component is mounted:
```bash
docker exec homeassistant-phomemo ls -la /config/custom_components/phomemo_d30
```

2. Restart Home Assistant:
```bash
docker compose restart homeassistant
```

3. Check logs for errors:
```bash
docker compose logs homeassistant | grep -i error
```

### MQTT Not Working

1. Check MQTT broker is running:
```bash
docker compose ps mosquitto
```

2. Test MQTT connection:
```bash
docker exec mosquitto-phomemo mosquitto_pub -t 'test' -m 'hello'
docker exec mosquitto-phomemo mosquitto_sub -t 'test' -C 1
```

3. Verify MQTT configuration in HA:
   - Go to: Settings → Devices & Services → MQTT
   - Should show "Connected"

### Bluetooth Not Working (Optional)

Bluetooth requires:
1. USB Bluetooth adapter passed through to container
2. D30 printer in pairing mode
3. Sufficient permissions (privileged mode)

Check Bluetooth availability:
```bash
docker exec homeassistant-phomemo hcitool dev
```

### Print Jobs Not Processing

1. Check integration is loaded:
```bash
docker compose logs homeassistant | grep "Phomemo D30"
```

2. Check MQTT messages are received:
```bash
docker exec mosquitto-phomemo mosquitto_sub -v -t 'homeassistant/phomemo/print'
# Then send a test message in another terminal
```

3. Enable debug logging in `ha_config/configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.phomemo_d30: debug
```

Then restart: `docker compose restart homeassistant`

## Advanced Testing

### Test with Real Images

Convert an image to base64:

```bash
# Linux/Mac
base64 -i myimage.png | tr -d '\n' > image_b64.txt

# Then use in MQTT payload
cat image_b64.txt
```

### Monitor Queue Status

The integration maintains a print queue. Check status via HA logs:

```bash
docker compose logs -f homeassistant | grep -i queue
```

### Test Retry Logic

Configure mock driver with failure rate to test retry:
1. In config flow, set failure rate to `0.5` (50% failure)
2. Send multiple print jobs
3. Watch logs to see retry mechanism

```bash
docker compose logs -f homeassistant | grep -E "(retry|failed|success)"
```

## File Locations

| Path | Purpose |
|------|---------|
| `ha_config/` | Home Assistant configuration |
| `test_prints/` | Mock driver saves images here |
| `mosquitto/config/` | MQTT broker configuration |
| `mosquitto/log/` | MQTT broker logs |
| `custom_components/phomemo_d30/` | Integration source code |

## Useful Commands

```bash
# Start in background
docker compose up -d

# Start with logs
docker compose up

# Stop containers
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild containers
docker compose up -d --build

# Shell into Home Assistant container
docker exec -it homeassistant-phomemo bash

# Shell into Mosquitto container
docker exec -it mosquitto-phomemo sh

# View container resource usage
docker stats

# Clean up everything
docker compose down -v
rm -rf ha_config test_prints mosquitto/data mosquitto/log
```

## Creating Test Images

### Python Script to Create Test Labels

```python
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO

# Create a simple label
img = Image.new('RGB', (400, 300), color='white')
draw = ImageDraw.Draw(img)

# Draw some text
draw.text((10, 10), "Test Label", fill='black')
draw.rectangle([10, 50, 390, 290], outline='black', width=2)

# Convert to base64
buffer = BytesIO()
img.save(buffer, format='PNG')
img_base64 = base64.b64encode(buffer.getvalue()).decode()

print(f"Base64 image (first 100 chars): {img_base64[:100]}...")
print(f"Full length: {len(img_base64)} characters")

# Save for reference
with open('test_image_b64.txt', 'w') as f:
    f.write(img_base64)
```

## Performance Testing

### Stress Test Queue

```bash
# Send 10 print jobs rapidly
for i in {1..10}; do
  docker exec mosquitto-phomemo mosquitto_pub \
    -t 'homeassistant/phomemo/print' \
    -m '{"image":"iVBORw0KGg...","width":50,"height":30}'
  echo "Sent job $i"
done

# Watch queue processing
docker compose logs -f homeassistant | grep -E "(queue|print|job)"
```

## Cleanup

### Remove Everything

```bash
# Stop and remove containers
docker compose down -v

# Remove created directories
rm -rf ha_config test_prints mosquitto/data mosquitto/log

# Remove configuration
rm -f ha_config/configuration.yaml

# Optionally remove Docker images
docker rmi homeassistant/home-assistant:2026.1 eclipse-mosquitto:2.0
```

### Keep Configuration, Remove Data

```bash
# Stop containers
docker compose down

# Clean only data directories
rm -rf test_prints/* mosquitto/data/* mosquitto/log/*

# Restart fresh
docker compose up -d
```

## Next Steps

1. **Test Mock Driver** - Verify images are saved correctly
2. **Test MQTT Integration** - Ensure messages trigger prints
3. **Test Error Handling** - Try invalid payloads
4. **Test Bluetooth** (if available) - Connect to real D30
5. **Create Automations** - Build real-world use cases
6. **Monitor Performance** - Check queue processing speed

## Support

- Check logs: `docker compose logs -f`
- Review integration code: `custom_components/phomemo_d30/`
- Test suite: `pytest tests/`
- Documentation: `README.md`
