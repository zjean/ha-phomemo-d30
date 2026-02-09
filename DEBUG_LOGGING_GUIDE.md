# Debug Logging Guide

## What Was Added

I've added extensive debug logging throughout the Bluetooth and printing code:

### Bluetooth Driver (`bluetooth_driver.py`)
- **Connection details**: BLE device discovery, available services/characteristics
- **Connection status**: Step-by-step connection process with visual indicators (✓/❌)
- **Data transmission**: Every BLE chunk with byte counts and hex previews
- **Print job flow**: 4-step printing process with detailed progress
- **Error handling**: Detailed error messages with context

### Protocol Encoder (`protocol.py`)
- **Image preprocessing**: Size conversions, aspect ratio, color inversion
- **Pixel sampling**: Sample pixel values at each stage
- **Command encoding**: Byte-by-byte encoding with hex previews
- **Image chunking**: How images are split into 255-line chunks
- **Initialization packets**: All 7 init packets with descriptions

### Print Queue (`queue.py`)
- Already has good logging for job flow and retry logic

## Enable Debug Logging in Home Assistant

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    # Enable debug logging for Phomemo integration
    custom_components.phomemo_d30: debug

    # Optional: Also enable debug for Home Assistant's Bluetooth
    homeassistant.components.bluetooth: debug
```

Then restart Home Assistant.

## View Logs

### Option 1: Home Assistant UI (Recommended)
1. Go to **Settings** → **System** → **Logs**
2. Logs auto-update in real-time
3. Use browser search (Ctrl+F / Cmd+F) to find:
   - `BLUETOOTH CONNECTION START` - Connection process
   - `BLUETOOTH PRINT START` - Print job start
   - `IMAGE PREPROCESSING` - Image conversion
   - `ENCODE PRINT COMMAND` - Protocol encoding
   - `❌` - Errors
   - `✓` - Successes

### Option 2: Command Line (More Detailed)
```bash
# Tail live logs
docker exec -it homeassistant tail -f /config/home-assistant.log

# Or if running in Docker compose:
docker compose logs -f homeassistant

# Filter for Phomemo only
docker exec -it homeassistant tail -f /config/home-assistant.log | grep phomemo_d30
```

### Option 3: SSH into Home Assistant OS
```bash
# SSH into HA OS
ssh root@homeassistant.local

# View logs
ha core logs -f
```

## What You'll See

When you call the test print service, you'll see output like this:

```
INFO === BLUETOOTH CONNECTION START ===
DEBUG Target address: AA:BB:CC:DD:EE:FF
DEBUG Write characteristic UUID: 0000ff01-0000-1000-8000-00805f9b34fb
DEBUG Looking up BLE device from HA Bluetooth integration
INFO ✓ Found BLE device: <BleakDevice>
DEBUG BLE device name: D30
DEBUG Establishing connection with max_attempts=3...
INFO ✓ Successfully connected to Bluetooth device AA:BB:CC:DD:EE:FF
INFO === BLUETOOTH CONNECTION COMPLETE ===

INFO ============================================================
INFO === BLUETOOTH PRINT START ===
INFO Job ID: abc123-def456
INFO Image size: (384, 240)
INFO Image mode: RGB
INFO Paper size: 50x30 mm
INFO Darkness: 5
INFO Rotation: 0°
INFO ============================================================

INFO Step 1/4: Preprocessing image...
DEBUG === IMAGE PREPROCESSING START ===
DEBUG Input image size: (384, 240)
DEBUG Input image mode: RGB
DEBUG Target width: 96 dots
DEBUG Calculated new size: (96, 60) (aspect ratio: 1.600)
DEBUG Sample pixels before inversion (first 5): [(255, 255, 255), ...]
DEBUG Final image size: (96, 60)
DEBUG Final image mode: 1
DEBUG === IMAGE PREPROCESSING COMPLETE ===
INFO   ✓ Image preprocessed

INFO Step 2/4: Sending initialization packets...
DEBUG Getting D30 initialization packets
DEBUG   Init packet 1: 1f1138 (3 bytes)
DEBUG   Init packet 2: 1f11121f1113 (6 bytes)
[... more init packets ...]
DEBUG → Sending BLE chunk 1/1 (3 bytes)
DEBUG   Chunk hex (first 16 bytes): 1f1138
DEBUG   ✓ Chunk 1 sent successfully
INFO   ✓ All initialization packets sent

INFO Step 3/4: Encoding print commands...
DEBUG === ENCODE PRINT COMMAND START ===
DEBUG Image size: (96, 60)
DEBUG Image mode: 1
DEBUG Splitting 96x60 image into 1 chunk(s) (max_height=255)
DEBUG Processing chunk 1: size=(96, 60)
DEBUG   Header bytes: 1f1124001b401d7630000c004001 (15 bytes)
DEBUG   Encoding 60 lines, 12 bytes per line...
DEBUG Generated 1 command(s) total
DEBUG Total encoded data: 735 bytes
DEBUG === ENCODE PRINT COMMAND COMPLETE ===
INFO   ✓ Print commands encoded

INFO Step 4/4: Sending print commands to printer...
DEBUG Preparing to send 735 bytes in 2 chunks (chunk_size=512)
DEBUG Data preview (first 32 bytes): 1f1124001b401d7630000c004001000000000000...
DEBUG → Sending BLE chunk 1/2 (512 bytes)
DEBUG   ✓ Chunk 1 sent successfully
DEBUG → Sending BLE chunk 2/2 (223 bytes)
DEBUG   ✓ Chunk 2 sent successfully
INFO   ✓ All print commands sent

INFO ============================================================
INFO === BLUETOOTH PRINT COMPLETE ===
INFO Job abc123-def456 completed successfully
INFO Total data sent: 735 bytes
INFO ============================================================
```

## Troubleshooting with Logs

### If printer not found:
Look for:
```
ERROR ❌ BLE device AA:BB:CC:DD:EE:FF not found in HA Bluetooth
ERROR Make sure the printer is powered on and in range
```
**Fix**: Turn on printer, check Bluetooth integration in HA

### If connection fails:
Look for:
```
ERROR ❌ Connection timeout: ...
ERROR Check printer is in range and not connected to another device
```
**Fix**: Move printer closer, disconnect from other devices

### If print fails:
Look for:
```
ERROR ❌ Failed to send chunk X: ...
```
**Fix**: Check logs for BLE disconnection, try restarting printer

### If image encoding fails:
Look for:
```
ERROR ❌ Invalid image mode: expected '1', got 'RGB'
```
**Fix**: This indicates a bug in preprocessing - check logs above

## Tips

1. **Call the test print service** to generate logs:
   ```yaml
   service: phomemo_d30.test_print
   data:
     text: "Debug Test"
   ```

2. **Search for visual markers** in logs:
   - `===` - Major section starts
   - `✓` - Successful operations
   - `❌` - Errors
   - `⚠️` - Warnings

3. **Check step-by-step progress**: The print process is divided into 4 clear steps

4. **Hex dumps**: Every BLE packet shows hex preview for protocol debugging

5. **Performance**: Check "Total bytes sent" and timing between log entries

## Reporting Issues

When reporting issues, include:
1. Full log output from "BLUETOOTH CONNECTION START" to "COMPLETE"
2. Your printer model (D30)
3. Home Assistant version
4. Bluetooth adapter info
5. Distance between HA and printer
