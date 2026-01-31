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

from .const import DOMAIN, PLATFORMS, CONF_MQTT_TOPIC
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
            mac_address=entry.data["bluetooth_mac"],
        )
    else:  # mock (default)
        from .phomemo.driver import MockPhomemoDriver
        driver = MockPhomemoDriver(
            save_path=entry.data.get("mock_save_path", "/tmp/phomemo"),
            print_delay=entry.data.get("mock_print_delay", 2.0),
        )

    # Connect the driver
    await driver.connect()

    # Create print queue
    queue = PrintQueue(
        driver=driver,
        max_size=entry.data.get("queue_max_size", 50),
        retry_attempts=entry.data.get("retry_attempts", 3),
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
        try:
            payload = json.loads(msg.payload)

            # Decode base64 image
            from PIL import Image
            from io import BytesIO
            image_data = base64.b64decode(payload["image"])
            image = Image.open(BytesIO(image_data))

            # Create print job
            job = PrintJob(
                image=image,
                width=payload.get("width", 50),
                height=payload.get("height", 30),
                darkness=payload.get("darkness", entry.data.get("darkness", 5)),
                rotate=payload.get("rotate", 0),
            )

            # Add to queue
            await queue.add_job(job)
            _LOGGER.info("Added print job %s to queue from MQTT", job.id)

        except Exception as e:
            _LOGGER.error("Error processing MQTT message: %s", e, exc_info=True)

    await mqtt.async_subscribe(hass, mqtt_topic, handle_mqtt_message, qos=1)
    _LOGGER.info("Subscribed to MQTT topic: %s", mqtt_topic)

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

        # Remove domain if no entries remain
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
