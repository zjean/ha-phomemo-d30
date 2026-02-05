"""Config flow for Phomemo D30."""
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

if TYPE_CHECKING:
    from homeassistant.components import bluetooth

from .const import (
    CONF_BLUETOOTH_MAC,
    CONF_DARKNESS,
    CONF_MODE,
    CONF_MOCK_PRINT_DELAY,
    CONF_MOCK_SAVE_PATH,
    CONF_MQTT_TOPIC,
    CONF_RETRY_ATTEMPTS,
    CONF_RETRY_DELAY,
    DEFAULT_DARKNESS,
    DEFAULT_MOCK_PRINT_DELAY,
    DEFAULT_MOCK_SAVE_PATH,
    DEFAULT_MQTT_TOPIC,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DOMAIN,
    MODE_BLUETOOTH,
    MODE_MOCK,
)

_LOGGER = logging.getLogger(__name__)


class PhomemoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Phomemo D30."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._mode: Optional[str] = None
        self._bluetooth_devices: Dict[str, str] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step - driver selection."""
        if user_input is not None:
            self._mode = user_input[CONF_MODE]

            if self._mode == MODE_MOCK:
                return await self.async_step_mock()
            elif self._mode == MODE_BLUETOOTH:
                return await self.async_step_bluetooth_discovery()

        # Show driver selection form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=MODE_MOCK): vol.In(
                    {MODE_MOCK: "Mock (Testing)", MODE_BLUETOOTH: "Bluetooth"}
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    async def async_step_mock(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle mock driver configuration."""
        errors = {}

        if user_input is not None:
            # Validate MQTT topic
            if not user_input.get(CONF_MQTT_TOPIC):
                errors["base"] = "mqtt_topic_required"
            else:
                # Set unique_id and check for existing entry
                await self.async_set_unique_id(f"{DOMAIN}_mock")
                self._abort_if_unique_id_configured()

                # Create entry
                return self.async_create_entry(
                    title="Phomemo D30 (Mock)",
                    data={
                        CONF_MODE: MODE_MOCK,
                        CONF_MQTT_TOPIC: user_input[CONF_MQTT_TOPIC],
                        CONF_MOCK_SAVE_PATH: user_input.get(
                            CONF_MOCK_SAVE_PATH, DEFAULT_MOCK_SAVE_PATH
                        ),
                        CONF_MOCK_PRINT_DELAY: user_input.get(
                            CONF_MOCK_PRINT_DELAY, DEFAULT_MOCK_PRINT_DELAY
                        ),
                        CONF_DARKNESS: DEFAULT_DARKNESS,
                        CONF_RETRY_ATTEMPTS: DEFAULT_RETRY_ATTEMPTS,
                        CONF_RETRY_DELAY: DEFAULT_RETRY_DELAY,
                    },
                )

        # Show mock configuration form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
                vol.Optional(
                    CONF_MOCK_SAVE_PATH, default=DEFAULT_MOCK_SAVE_PATH
                ): str,
                vol.Optional(
                    CONF_MOCK_PRINT_DELAY, default=DEFAULT_MOCK_PRINT_DELAY
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
            }
        )

        return self.async_show_form(
            step_id="mock",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_bluetooth_discovery(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Discover Bluetooth devices."""
        # Import here to avoid import errors during tests
        try:
            from homeassistant.components import bluetooth
        except ImportError:
            return self.async_abort(reason="bluetooth_not_available")

        # Discover all Bluetooth devices
        discovered_devices = bluetooth.async_discovered_service_info(self.hass)

        # Add all devices with names
        all_devices = {}
        for device in discovered_devices:
            if device.name:
                all_devices[device.address] = f"{device.name} ({device.address})"

        if not all_devices:
            return self.async_abort(reason="no_devices_found")

        self._bluetooth_devices = all_devices
        return await self.async_step_bluetooth()

    async def async_step_bluetooth(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle Bluetooth device selection."""
        errors = {}

        if user_input is not None:
            # Validate MQTT topic and device
            if not user_input.get(CONF_MQTT_TOPIC):
                errors["base"] = "mqtt_topic_required"
            elif not user_input.get(CONF_BLUETOOTH_MAC):
                errors["base"] = "bluetooth_mac_required"
            else:
                # Set unique_id based on MAC address and check for existing entry
                mac_address = user_input[CONF_BLUETOOTH_MAC]
                await self.async_set_unique_id(f"{DOMAIN}_{mac_address}")
                self._abort_if_unique_id_configured()

                # Create entry
                return self.async_create_entry(
                    title="Phomemo D30 (Bluetooth)",
                    data={
                        CONF_MODE: MODE_BLUETOOTH,
                        CONF_BLUETOOTH_MAC: mac_address,
                        CONF_MQTT_TOPIC: user_input[CONF_MQTT_TOPIC],
                        CONF_DARKNESS: DEFAULT_DARKNESS,
                        CONF_RETRY_ATTEMPTS: DEFAULT_RETRY_ATTEMPTS,
                        CONF_RETRY_DELAY: DEFAULT_RETRY_DELAY,
                    },
                )

        # Show Bluetooth configuration form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_BLUETOOTH_MAC): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=mac, label=name)
                            for mac, name in self._bluetooth_devices.items()
                        ]
                    )
                ),
                vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
            }
        )

        return self.async_show_form(
            step_id="bluetooth",
            data_schema=data_schema,
            errors=errors,
        )
