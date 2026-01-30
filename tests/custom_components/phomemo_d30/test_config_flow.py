"""Test the config flow."""
from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.phomemo_d30.const import DOMAIN, MODE_MOCK, MODE_BLUETOOTH


async def test_form_user_step(hass: HomeAssistant):
    """Test user step shows driver selection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_form_mock_mode(hass: HomeAssistant):
    """Test config flow for mock mode."""
    # Start flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select mock mode
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"mode": MODE_MOCK},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "mock"

    # Configure mock settings
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "mqtt_topic": "homeassistant/phomemo/print",
            "mock_save_path": "/config/phomemo_test",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Phomemo D30 (Mock)"
    assert result["data"]["mode"] == MODE_MOCK
    assert result["data"]["mqtt_topic"] == "homeassistant/phomemo/print"


async def test_form_bluetooth_mode_no_devices(hass: HomeAssistant):
    """Test config flow aborts when no Bluetooth devices found."""
    # Start flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Mock empty bluetooth discovery
    mock_bluetooth = MagicMock()
    mock_bluetooth.async_discovered_service_info.return_value = []

    # Select bluetooth mode - should abort with no devices
    with patch.dict(
        "sys.modules",
        {"homeassistant.components.bluetooth": mock_bluetooth},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"mode": MODE_BLUETOOTH},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_form_bluetooth_mode_with_devices(hass: HomeAssistant):
    """Test config flow for bluetooth mode with discovered devices."""
    # Mock bluetooth service info
    mock_device_1 = MagicMock()
    mock_device_1.name = "Phomemo-D30-1234"
    mock_device_1.address = "AA:BB:CC:DD:EE:FF"

    mock_device_2 = MagicMock()
    mock_device_2.name = "Phomemo-D30-5678"
    mock_device_2.address = "11:22:33:44:55:66"

    # Start flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Mock the bluetooth module for discovery
    mock_bluetooth = MagicMock()
    mock_bluetooth.async_discovered_service_info.return_value = [
        mock_device_1,
        mock_device_2,
    ]

    # Select bluetooth mode and discover devices
    with patch.dict(
        "sys.modules",
        {"homeassistant.components.bluetooth": mock_bluetooth},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"mode": MODE_BLUETOOTH},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bluetooth"

    # Select a device
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "bluetooth_mac": "AA:BB:CC:DD:EE:FF",
            "mqtt_topic": "homeassistant/phomemo/print",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Phomemo D30 (Bluetooth)"
    assert result["data"]["mode"] == MODE_BLUETOOTH
    assert result["data"]["bluetooth_mac"] == "AA:BB:CC:DD:EE:FF"


async def test_form_duplicate_mock_entry(hass: HomeAssistant):
    """Test that we abort if mock entry already exists."""
    # Mock existing config entry
    mock_entry = MagicMock()
    mock_entry.domain = DOMAIN
    mock_entry.data = {
        "mode": MODE_MOCK,
        "mqtt_topic": "homeassistant/phomemo/print",
    }
    mock_entry.unique_id = "phomemo_d30_mock"

    # Add to hass entries using _mock_entries
    hass.config_entries._mock_entries = [mock_entry]

    # Try to create another mock entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select mock mode
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"mode": MODE_MOCK},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "mock"

    # Try to configure mock - should abort due to existing entry
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "mqtt_topic": "homeassistant/phomemo/print",
            "mock_save_path": "/config/phomemo_test",
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_form_duplicate_bluetooth_entry(hass: HomeAssistant):
    """Test that we abort if Bluetooth device already configured."""
    # Mock existing config entry for device
    mock_entry = MagicMock()
    mock_entry.domain = DOMAIN
    mock_entry.data = {
        "mode": MODE_BLUETOOTH,
        "bluetooth_mac": "AA:BB:CC:DD:EE:FF",
        "mqtt_topic": "homeassistant/phomemo/print",
    }
    mock_entry.unique_id = "phomemo_d30_AA:BB:CC:DD:EE:FF"

    # Add to hass entries using _mock_entries
    hass.config_entries._mock_entries = [mock_entry]

    # Mock bluetooth service info
    mock_device_1 = MagicMock()
    mock_device_1.name = "Phomemo-D30-1234"
    mock_device_1.address = "AA:BB:CC:DD:EE:FF"

    # Start flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Mock the bluetooth module for discovery
    mock_bluetooth = MagicMock()
    mock_bluetooth.async_discovered_service_info.return_value = [mock_device_1]

    # Select bluetooth mode and discover devices
    with patch.dict(
        "sys.modules",
        {"homeassistant.components.bluetooth": mock_bluetooth},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"mode": MODE_BLUETOOTH},
        )

    # Try to configure the same device
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "bluetooth_mac": "AA:BB:CC:DD:EE:FF",
            "mqtt_topic": "homeassistant/phomemo/print",
        },
    )

    # Should abort due to existing entry
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
