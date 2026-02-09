"""The Phomemo D30 Label Printer integration."""
from __future__ import annotations

import base64
import json
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt

from .const import DOMAIN, PLATFORMS, CONF_MQTT_TOPIC, SERVICE_TEST_PRINT
from .queue import PrintQueue
from .models import PrintJob

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Phomemo D30 integration from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Phomemo D30 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Instantiate appropriate driver based on config
    mode = entry.data.get("mode", "mock")

    if mode == "bluetooth":
        # Import here to avoid dependency issues when not using Bluetooth
        from .phomemo.bluetooth_driver import BluetoothPhomemoDriver
        driver = BluetoothPhomemoDriver(
            hass=hass,
            bluetooth_address=entry.data["bluetooth_mac"],
        )
    else:  # mock (default)
        from .phomemo.driver import MockPhomemoDriver
        driver = MockPhomemoDriver(
            save_path=entry.data.get("mock_save_path", "/tmp/phomemo"),
            print_delay=entry.data.get("mock_print_delay", 2.0),
        )

    # Note: We don't connect immediately to allow setup even if printer is off
    # Connection will happen automatically on first print attempt
    _LOGGER.info("Driver initialized (connection deferred until first print)")

    # Create print queue
    queue = PrintQueue(
        driver=driver,
        max_size=entry.data.get("queue_max_size", 50),
        retry_attempts=entry.data.get("retry_attempts", 5),
        retry_delay=entry.data.get("retry_delay", 5),
    )

    # Start queue worker
    await queue.start()

    # Store driver and queue instances
    hass.data[DOMAIN][entry.entry_id] = {
        "driver": driver,
        "queue": queue,
        "config": entry.data,
    }

    # Subscribe to MQTT topic
    mqtt_topic = entry.data.get(CONF_MQTT_TOPIC, "homeassistant/phomemo/print")

    async def handle_mqtt_message(msg):
        """Handle incoming MQTT message."""
        _LOGGER.info(
            "Received MQTT message on topic %s (payload size: %d bytes)",
            msg.topic,
            len(msg.payload) if msg.payload else 0
        )
        _LOGGER.debug("Message QoS: %s, Retain: %s", msg.qos, msg.retain)
        try:
            # Check if payload is binary (raw image) or JSON
            payload_bytes = msg.payload if isinstance(msg.payload, bytes) else msg.payload.encode()
            _LOGGER.debug("Payload type: %s, first 20 bytes: %s", type(msg.payload), payload_bytes[:20])

            from PIL import Image
            from io import BytesIO

            # Check if it's a raw image file (PNG, JPG, etc.)
            if payload_bytes.startswith(b'\x89PNG') or payload_bytes.startswith(b'\xff\xd8\xff'):
                # Raw image data - open directly
                _LOGGER.info("Detected raw image data (PNG or JPEG)")
                try:
                    image = Image.open(BytesIO(payload_bytes))
                    _LOGGER.info("Opened raw image file: format=%s, size=%s", image.format, image.size)
                except Exception as e:
                    _LOGGER.error("Failed to open raw image data: %s", e)
                    return

                # Use defaults for missing metadata
                job = PrintJob(
                    image=image,
                    width=50,
                    height=30,
                    darkness=entry.data.get("darkness", 5),
                    rotate=0,
                )
                _LOGGER.info("Created print job %s from raw image", job.id)
            else:
                # JSON payload with base64-encoded image
                _LOGGER.info("Attempting to parse payload as JSON")
                try:
                    payload = json.loads(payload_bytes)
                    _LOGGER.info("Successfully parsed JSON payload")
                except json.JSONDecodeError as e:
                    _LOGGER.error(
                        "Invalid MQTT payload: not a valid image file or JSON. "
                        "Send raw PNG/JPG file or JSON: {\"image\": \"base64...\", \"width\": 50, \"height\": 30}. "
                        "Error: %s",
                        e
                    )
                    return

                # Validate required fields
                if "image" not in payload:
                    _LOGGER.error("MQTT JSON payload missing required 'image' field")
                    return

                # Decode base64 image
                try:
                    _LOGGER.debug("Decoding base64 image (length: %d chars)", len(payload["image"]))
                    image_data = base64.b64decode(payload["image"])
                    _LOGGER.debug("Decoded image data: %d bytes", len(image_data))
                    image = Image.open(BytesIO(image_data))
                    _LOGGER.debug("Opened image: format=%s, size=%s, mode=%s", image.format, image.size, image.mode)
                except Exception as e:
                    _LOGGER.error("Failed to decode image from base64: %s", e)
                    return

                # Create print job with metadata from JSON
                job = PrintJob(
                    image=image,
                    width=payload.get("width", 50),
                    height=payload.get("height", 30),
                    darkness=payload.get("darkness", entry.data.get("darkness", 5)),
                    rotate=payload.get("rotate", 0),
                )
                _LOGGER.info(
                    "Created print job %s from JSON (size=%s, darkness=%d)",
                    job.id, image.size, job.darkness
                )

            # Add to queue
            _LOGGER.info("Adding job %s to print queue (current size: %d)", job.id, queue.size())
            await queue.add_job(job)
            _LOGGER.info("Successfully added print job %s to queue", job.id)

        except Exception as e:
            _LOGGER.error("Unexpected error processing MQTT message: %s", e, exc_info=True)

    await mqtt.async_subscribe(hass, mqtt_topic, handle_mqtt_message, qos=1, encoding=None)
    _LOGGER.info("Subscribed to MQTT topic: %s", mqtt_topic)

    # Register test print service
    async def handle_test_print(call):
        """Handle test print service call."""
        from datetime import datetime
        from PIL import Image, ImageDraw, ImageFont

        _LOGGER.info("Test print service called")

        # Get parameters from service call
        text = call.data.get("text", "TEST LABEL")
        width_mm = call.data.get("width", 50)
        height_mm = call.data.get("height", 30)
        darkness = call.data.get("darkness", entry.data.get("darkness", 5))
        rotate = call.data.get("rotate", 0)

        # Calculate pixel dimensions (assuming ~200 DPI)
        # 50mm ≈ 384 pixels, 30mm ≈ 240 pixels
        width_px = int(width_mm * 7.68)  # ~200 DPI conversion
        height_px = int(height_mm * 8.0)

        _LOGGER.debug(
            "Creating test label: text='%s', size=%dx%d px (%dx%d mm), darkness=%d, rotate=%d",
            text, width_px, height_px, width_mm, height_mm, darkness, rotate
        )

        # Create test label image
        image = Image.new('RGB', (width_px, height_px), 'white')
        draw = ImageDraw.Draw(image)

        # Draw border
        draw.rectangle([(5, 5), (width_px-5, height_px-5)], outline='black', width=3)

        # Add main text
        try:
            font_size = min(width_px, height_px) // 8
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            try:
                # Try macOS font
                font_size = min(width_px, height_px) // 8
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                # Fall back to default
                font = ImageFont.load_default()

        # Center text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (width_px - text_width) // 2
        text_y = (height_px - text_height) // 2 - 20
        draw.text((text_x, text_y), text, fill='black', font=font)

        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            small_font_size = font_size // 2
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", small_font_size)
        except:
            try:
                small_font_size = font_size // 2
                small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", small_font_size)
            except:
                small_font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), timestamp, font=small_font)
        ts_width = bbox[2] - bbox[0]
        ts_x = (width_px - ts_width) // 2
        draw.text((ts_x, height_px - 40), timestamp, fill='black', font=small_font)

        # Create print job
        job = PrintJob(
            image=image,
            width=width_mm,
            height=height_mm,
            darkness=darkness,
            rotate=rotate,
        )

        _LOGGER.info("Adding test print job %s to queue", job.id)
        await queue.add_job(job)
        _LOGGER.info("Test print job %s added successfully", job.id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_PRINT,
        handle_test_print,
    )
    _LOGGER.info("Registered %s.%s service", DOMAIN, SERVICE_TEST_PRINT)

    # Forward the setup to platforms (if any)
    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms (if any)
    unload_ok = True
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Stop queue and disconnect driver
        entry_data = hass.data[DOMAIN].get(entry.entry_id, {})

        if "queue" in entry_data:
            await entry_data["queue"].stop()
            _LOGGER.info("Stopped print queue")

        if "driver" in entry_data:
            await entry_data["driver"].disconnect()
            _LOGGER.info("Disconnected driver")

        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)

        # Remove domain and unregister services if no entries remain
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            hass.services.async_remove(DOMAIN, SERVICE_TEST_PRINT)
            _LOGGER.info("Unregistered services")

    return unload_ok
