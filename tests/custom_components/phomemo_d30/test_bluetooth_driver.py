"""Test Bluetooth printer driver."""
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from PIL import Image

# Mock homeassistant.components.bluetooth before importing bluetooth_driver
sys.modules['homeassistant.components.bluetooth'] = MagicMock()

from custom_components.phomemo_d30.models import PrintJob
from custom_components.phomemo_d30.phomemo.bluetooth_driver import BluetoothPhomemoDriver
from custom_components.phomemo_d30.phomemo.exceptions import FatalError, RecoverableError


def create_test_image():
    """Create a simple test image."""
    return Image.new("RGB", (50, 30), color="white")


@pytest.mark.asyncio
async def test_bluetooth_driver_connect():
    """Test Bluetooth connection."""
    hass = MagicMock()
    address = "AA:BB:CC:DD:EE:FF"

    with patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.bluetooth") as mock_bt, \
         patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.BleakClient") as mock_client_class:

        mock_ble_device = MagicMock()
        mock_bt.async_ble_device_from_address.return_value = mock_ble_device

        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client_class.return_value = mock_client

        driver = BluetoothPhomemoDriver(hass, address)
        await driver.connect()

        assert driver.is_connected()
        mock_client.connect.assert_called_once()


@pytest.mark.asyncio
async def test_bluetooth_driver_print():
    """Test printing via Bluetooth."""
    hass = MagicMock()
    address = "AA:BB:CC:DD:EE:FF"

    with patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.bluetooth") as mock_bt, \
         patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.BleakClient") as mock_client_class, \
         patch("custom_components.phomemo_d30.phomemo.bluetooth_driver.protocol") as mock_protocol:

        mock_ble_device = MagicMock()
        mock_bt.async_ble_device_from_address.return_value = mock_ble_device

        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client_class.return_value = mock_client

        # Mock protocol functions
        mock_processed_image = Image.new("1", (96, 30), color=1)
        mock_protocol.preprocess_image.return_value = mock_processed_image

        # Mock initialization packets (returns list of 7 packets)
        mock_protocol.get_initialization_packets.return_value = [
            b'\x1f\x11\x38',
            b'\x1f\x11\x12\x1f\x11\x13',
            b'\x1f\x11\x09',
            b'\x1f\x11\x11',
            b'\x1f\x11\x19',
            b'\x1f\x11\x07',
            b'\x1f\x11\x0a\x1f\x11\x02\x02'
        ]

        # Mock encode_print_command (returns list of command bytes)
        mock_protocol.encode_print_command.return_value = [
            b'\x1f\x11\x24' + b'\x00' * 100
        ]

        driver = BluetoothPhomemoDriver(hass, address)
        await driver.connect()

        img = create_test_image()
        job = PrintJob(image=img, width=50, height=30)

        await driver.print(job)

        # Should have written data to characteristic (init packets + print commands)
        assert mock_client.write_gatt_char.called
        # At least 8 calls: 7 init packets + 1 print command
        assert mock_client.write_gatt_char.call_count >= 8
