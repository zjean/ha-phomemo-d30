# Phomemo D30 Label Printer for Home Assistant

A Home Assistant custom integration for the Phomemo D30 label printer. Print labels via MQTT (e.g., from Homebox) using Bluetooth.

## Features

- Print labels via MQTT messages
- Bluetooth connectivity to Phomemo D30 printer
- Mock mode for testing without hardware
- Print queue with retry logic
- Sensor entities for monitoring printer status

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add repository: `https://github.com/janwiebe/ha-phomemo-d30`
4. Category: **Integration**
5. Click **Add**
6. Search for "Phomemo D30" in HACS
7. Click **Download**
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/phomemo_d30` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Prerequisites

1. **MQTT Integration** must be configured in Home Assistant
2. **Bluetooth Integration** must be enabled (for real printer)
3. **Phomemo D30 printer** powered on and in range

### Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Phomemo D30**
4. Select driver type:
   - **Bluetooth** - For real D30 printer
   - **Mock** - For testing (saves images to disk)
5. Configure MQTT topic (default: `homeassistant/phomemo/print`)
6. For Bluetooth: Select your D30 printer from discovered devices

## Usage

### Printing via MQTT

Send a JSON message to your configured MQTT topic with the following format:

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUg...",
  "width": 50,
  "height": 30,
  "darkness": 5,
  "rotate": 0
}
```

**Fields:**
- `image` (required): Base64-encoded PNG image
- `width` (optional): Paper width in mm (default: 50)
- `height` (optional): Paper height in mm (default: 30)
- `darkness` (optional): Print darkness 0-5 (default: 3)
- `rotate` (optional): Rotation in degrees: 0, 90, 180, 270 (default: 0)

### Example: Using Home Assistant Developer Tools

1. Go to **Developer Tools** → **Services**
2. Service: `mqtt.publish`
3. Service Data:
```yaml
topic: homeassistant/phomemo/print
payload: |
  {
    "image": "iVBORw0KGgoAAAANSUhEUg...",
    "width": 50,
    "height": 30
  }
```

### Example: Using mosquitto_pub

```bash
mosquitto_pub -h localhost -t "homeassistant/phomemo/print" -m '{
  "image": "iVBORw0KGgoAAAANSUhEUg...",
  "width": 50,
  "height": 30
}'
```

### Integration with Homebox

This integration works perfectly with [Homebox](https://github.com/hay-kot/homebox) label printing. Configure Homebox to publish MQTT messages to your configured topic.

See: [Homebox MQTT Integration Guide](https://blog.fuzzymistborn.com/homebox-labels-over-mqtt/)

## Entities

The integration creates the following sensor entities:

- **Print Queue Size** - Number of pending print jobs
- **Print Queue Status** - Current status: idle, printing, error

## Troubleshooting

### Printer not discovered

- Ensure Bluetooth integration is enabled and working
- Power cycle the Phomemo D30 printer
- Make sure the printer is in range
- Verify no other device is connected to the printer

### Print job fails

- Check Home Assistant logs: **Settings** → **System** → **Logs**
- Enable debug logging (see below)
- Verify MQTT message format is correct
- Check printer has paper and is powered on

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.phomemo_d30: debug
```

Then restart Home Assistant.

## Mock Mode

For testing without hardware, use **Mock** driver mode:

1. Configure integration with Mock driver
2. Set save path (e.g., `/config/phomemo_test_prints`)
3. Print jobs will be saved as PNG files to the specified directory

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and contributing guidelines.

## Credits

This integration includes code adapted from [phomemo-tools](https://github.com/vivier/phomemo-tools) by Laurent Vivier.

## License

GPL-3.0-or-later

This project includes code adapted from phomemo-tools, which is licensed under GPL-3.0.

## Support

- [Report Issues](https://github.com/janwiebe/ha-phomemo-d30/issues)
- [Home Assistant Community](https://community.home-assistant.io/)
