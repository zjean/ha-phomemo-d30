# Enable Debug Logging for Phomemo D30

To see detailed logs for debugging issues with the Phomemo D30 integration, you need to enable debug logging in Home Assistant.

## Method 1: Configuration.yaml (Persistent)

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    # Phomemo D30 integration
    custom_components.phomemo_d30: debug
    custom_components.phomemo_d30.phomemo.bluetooth_driver: debug
    custom_components.phomemo_d30.queue: debug

    # Home Assistant Bluetooth (if having connection issues)
    homeassistant.components.bluetooth: info
    habluetooth: info
```

**Then restart Home Assistant.**

## Method 2: Developer Tools (Temporary - until next restart)

1. Go to **Developer Tools** → **Services**
2. Choose service: `Logger: Set level`
3. Use this YAML:

```yaml
custom_components.phomemo_d30: debug
custom_components.phomemo_d30.phomemo.bluetooth_driver: debug
custom_components.phomemo_d30.queue: debug
```

**This is reset on Home Assistant restart.**

## View Logs

### Option 1: Home Assistant UI
- **Settings** → **System** → **Logs**
- Search for "phomemo"
- Logs update in real-time

### Option 2: Command Line
```bash
# Follow logs in real-time
tail -f /config/home-assistant.log | grep -i phomemo

# View recent phomemo logs
grep -i phomemo /config/home-assistant.log | tail -50
```

## What to Look For

With debug logging enabled, you should see:

### When Integration Starts
```
Connected to Bluetooth device XX:XX:XX:XX:XX:XX
Print queue started
Subscribed to MQTT topic: homeassistant/phomemo/print
```

### When MQTT Message Received
```
Received MQTT message on topic homeassistant/phomemo/print (payload size: XXXX bytes)
Detected raw image data (PNG or JPEG)  OR  Attempting to parse payload as JSON
Created print job xxxxx from raw image/JSON
Adding job xxxxx to print queue
Successfully added print job xxxxx to queue
```

### When Print Job Processes
```
Processing job xxxxx
Bluetooth driver: printing job xxxxx (width=50, height=30)
Sending XXXX bytes to printer XX:XX:XX:XX:XX:XX
Bluetooth driver: job xxxxx completed
Job xxxxx completed
```

## Common Issues

### No logs at all when sending MQTT
- Check MQTT topic matches configuration
- Verify MQTT message is actually being sent
- Check MQTT integration is working: `Developer Tools` → `MQTT` → `Subscribe to topic`

### "Processing job" but nothing happens
- Printer may be off or out of range
- Check Bluetooth connection logs
- Look for "RecoverableError" messages

### Job fails immediately
- Look for "FatalError" messages
- Check image format and size
- Verify printer is compatible

## Test MQTT Manually

In **Developer Tools** → **MQTT** → **Publish**, send a test message:

**Topic:** `homeassistant/phomemo/print` (or your configured topic)

**Payload (JSON):**
```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "width": 50,
  "height": 30,
  "darkness": 5,
  "rotate": 0
}
```

Or send a raw PNG/JPG file (binary payload).

You should see logs appear immediately in the Home Assistant logs.
