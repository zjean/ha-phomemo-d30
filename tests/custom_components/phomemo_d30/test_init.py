"""Test the Phomemo D30 integration setup."""
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.phomemo_d30.const import DOMAIN
from tests.conftest import MockConfigEntry


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "mode": "mock",
            "mqtt_topic": "homeassistant/phomemo/print",
            "darkness": 5,
            "retry_attempts": 3,
            "retry_delay": 5,
            "mock_print_delay": 2,
            "mock_save_path": "/tmp/phomemo_test",
        },
        title="Phomemo D30",
    )


async def test_setup_entry(hass: HomeAssistant, mock_config_entry):
    """Test integration setup from config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data


async def test_unload_entry(hass: HomeAssistant, mock_config_entry):
    """Test integration unload."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
    assert DOMAIN not in hass.data


async def test_setup_entry_mock_driver(hass: HomeAssistant):
    """Test setup entry instantiates mock driver."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "mode": "mock",
            "mqtt_topic": "homeassistant/phomemo/print",
            "darkness": 5,
            "retry_attempts": 3,
            "retry_delay": 5,
            "mock_print_delay": 2.0,
            "mock_save_path": "/tmp/phomemo_test",
        },
        title="Phomemo D30 (Mock)",
    )
    config_entry.add_to_hass(hass)

    # Verify setup succeeds
    result = await hass.config_entries.async_setup(config_entry.entry_id)
    assert result
    await hass.async_block_till_done()

    # Check driver is stored in hass.data
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    assert "driver" in entry_data

    # Verify it's a MockPhomemoDriver
    from custom_components.phomemo_d30.phomemo.driver import MockPhomemoDriver
    driver = entry_data["driver"]
    assert isinstance(driver, MockPhomemoDriver)


async def test_setup_entry_bluetooth_driver(hass: HomeAssistant):
    """Test setup entry instantiates Bluetooth driver."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "mode": "bluetooth",
            "bluetooth_mac": "AA:BB:CC:DD:EE:FF",
            "mqtt_topic": "homeassistant/phomemo/print",
            "darkness": 5,
            "retry_attempts": 3,
            "retry_delay": 5,
        },
        title="Phomemo D30 (Bluetooth)",
    )
    config_entry.add_to_hass(hass)

    # Mock the BluetoothPhomemoDriver since we can't test real Bluetooth
    with patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.BluetoothPhomemoDriver") as mock_bt_driver:
        mock_driver_instance = mock_bt_driver.return_value

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify BluetoothPhomemoDriver was instantiated with correct params
        mock_bt_driver.assert_called_once_with(
            hass=hass,
            mac_address="AA:BB:CC:DD:EE:FF"
        )

        # Check driver is stored in hass.data
        assert DOMAIN in hass.data
        assert config_entry.entry_id in hass.data[DOMAIN]
        entry_data = hass.data[DOMAIN][config_entry.entry_id]
        assert "driver" in entry_data
        assert entry_data["driver"] == mock_driver_instance
