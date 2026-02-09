# Test Print Button for Home Assistant

## Quick Start - Using Developer Tools

After restarting Home Assistant with the updated integration:

1. Go to **Developer Tools** → **Services**
2. Select service: `Phomemo D30 Label Printer: Test Print`
3. Fill in optional parameters (or leave defaults):
   - **Text**: "TEST LABEL" (default)
   - **Width**: 50 mm (default)
   - **Height**: 30 mm (default)
   - **Darkness**: 5 (default)
   - **Rotation**: 0° (default)
4. Click **Call Service**

Your printer should print a test label with the text and current timestamp!

## Adding a Button to Your Dashboard

### Method 1: Button Card (Simplest)

Add this to your dashboard in YAML mode or via the UI:

```yaml
type: button
name: Test Print Label
icon: mdi:printer
tap_action:
  action: call-service
  service: phomemo_d30.test_print
  service_data:
    text: "TEST LABEL"
    width: 50
    height: 30
    darkness: 5
    rotate: 0
```

### Method 2: Entity Button (Alternative)

First, create a script in your `configuration.yaml` or `scripts.yaml`:

```yaml
test_print_label:
  alias: "Test Print Label"
  icon: mdi:printer
  sequence:
    - service: phomemo_d30.test_print
      data:
        text: "TEST LABEL"
        width: 50
        height: 30
        darkness: 5
```

Then add a button card to your dashboard:

```yaml
type: button
entity: script.test_print_label
name: Test Print
icon: mdi:printer
tap_action:
  action: call-service
  service: script.test_print_label
```

### Method 3: Custom Text Input

For dynamic text, create an input text helper and a script:

**configuration.yaml:**
```yaml
input_text:
  label_text:
    name: "Label Text"
    initial: "TEST LABEL"
    max: 50

script:
  print_custom_label:
    alias: "Print Custom Label"
    icon: mdi:printer-pos
    sequence:
      - service: phomemo_d30.test_print
        data:
          text: "{{ states('input_text.label_text') }}"
          width: 50
          height: 30
          darkness: 5
```

**Dashboard card:**
```yaml
type: vertical-stack
cards:
  - type: entities
    entities:
      - entity: input_text.label_text
  - type: button
    name: Print Label
    icon: mdi:printer
    tap_action:
      action: call-service
      service: script.print_custom_label
```

## Example Automation

Print a test label every day at 9 AM:

```yaml
automation:
  - alias: "Daily Printer Test"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: phomemo_d30.test_print
        data:
          text: "Daily Test"
          darkness: 5
```

## Service Parameters

All parameters are **optional**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | string | "TEST LABEL" | Text to print on label |
| `width` | int | 50 | Paper width in mm |
| `height` | int | 30 | Paper height in mm |
| `darkness` | int (0-5) | 5 | Print darkness level |
| `rotate` | int (0/90/180/270) | 0 | Rotation in degrees |

## Troubleshooting

If the test print doesn't work:

1. Check that the integration is loaded: **Settings** → **Devices & Services** → Look for "Phomemo D30"
2. Check logs: **Settings** → **System** → **Logs**
3. Verify MQTT is working: **Developer Tools** → **MQTT** → Test publish
4. For Bluetooth mode: Ensure printer is on and in range
5. For Mock mode: Check the configured save path for generated images

## Using with Automations

Example: Print a label when a door opens:

```yaml
automation:
  - alias: "Print Door Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: phomemo_d30.test_print
        data:
          text: "DOOR OPENED"
          darkness: 5
```
