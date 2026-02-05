"""Bluetooth printer driver for Phomemo D30.

Adapted from phomemo-tools by Laurent Vivier
Original: https://github.com/vivier/phomemo-tools
License: GPL-3.0
"""
import asyncio
import logging
from typing import Optional

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from ..models import PrintJob
from .driver import PhomemoDriver
from .exceptions import FatalError, RecoverableError
from . import protocol

_LOGGER = logging.getLogger(__name__)

# D30 Bluetooth characteristics
# Serial port service UUID (common for thermal printers)
SERIAL_SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"


class BluetoothPhomemoDriver(PhomemoDriver):
    """Bluetooth driver for Phomemo D30 using Home Assistant Bluetooth."""

    def __init__(self, hass: HomeAssistant, bluetooth_address: str):
        """Initialize Bluetooth driver.

        Args:
            hass: Home Assistant instance
            bluetooth_address: MAC address from discovered device
        """
        self._hass = hass
        self._address = bluetooth_address
        self._client: Optional[BleakClient] = None
        self._connected = False
        self._write_characteristic = WRITE_CHAR_UUID

    async def connect(self) -> None:
        """Connect to D30 via Home Assistant Bluetooth.

        Raises:
            FatalError: If Bluetooth device not found
            RecoverableError: If connection times out
        """
        _LOGGER.debug("Attempting to connect to Bluetooth device %s", self._address)
        try:
            # Get BLE device from HA's Bluetooth integration
            _LOGGER.debug("Looking up BLE device from HA Bluetooth")
            ble_device = bluetooth.async_ble_device_from_address(
                self._hass,
                self._address,
                connectable=True
            )

            if ble_device is None:
                _LOGGER.error("BLE device %s not found in HA Bluetooth", self._address)
                raise FatalError(
                    f"Bluetooth device {self._address} not found. "
                    "Make sure the printer is powered on and in range."
                )

            # Use bleak-retry-connector for reliable connection
            _LOGGER.debug("Connecting to Bluetooth device %s", self._address)
            self._client = await establish_connection(
                BleakClient,
                ble_device,
                self._address,
                max_attempts=3,
            )

            self._connected = True
            _LOGGER.info("Connected to Bluetooth device %s", self._address)

        except asyncio.TimeoutError as e:
            raise RecoverableError(
                f"Bluetooth connection timeout: {e}. Check printer range."
            ) from e
        except Exception as e:
            raise RecoverableError(
                f"Bluetooth connection failed: {e}"
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from the printer."""
        if self._client and self._connected:
            _LOGGER.debug("Disconnecting from Bluetooth device %s", self._address)
            await self._client.disconnect()
            self._connected = False
            _LOGGER.info("Disconnected from Bluetooth device %s", self._address)

    def is_connected(self) -> bool:
        """Check if connected to printer."""
        return self._connected and self._client is not None and self._client.is_connected

    async def print(self, job: PrintJob) -> None:
        """Print a job via Bluetooth.

        Args:
            job: Print job to execute

        Raises:
            FatalError: Invalid image format, not connected
            RecoverableError: Connection timeout, BLE disconnection
        """
        if not self.is_connected():
            raise FatalError("Bluetooth driver not connected")

        _LOGGER.info(
            "Bluetooth driver: printing job %s (width=%d, height=%d)",
            job.id,
            job.width,
            job.height,
        )

        try:
            # Preprocess image (run in thread pool to avoid blocking)
            _LOGGER.debug("Preprocessing image: size=%s, mode=%s", job.image.size, job.image.mode)
            processed_image = await asyncio.to_thread(
                protocol.preprocess_image,
                job.image,
            )
            _LOGGER.debug("Preprocessed image: size=%s, mode=%s", processed_image.size, processed_image.mode)

            # Encode to D30 protocol bytes
            _LOGGER.debug("Encoding print command with darkness=%d", job.darkness)
            print_data = await asyncio.to_thread(
                protocol.encode_print_command,
                processed_image,
            )

            _LOGGER.debug(
                "Sending %d bytes to printer %s in %d-byte chunks",
                len(print_data),
                self._address,
                512,
            )

            # Split into chunks (BLE MTU limits, typically 512 bytes)
            chunk_size = 512
            total_chunks = (len(print_data) + chunk_size - 1) // chunk_size
            _LOGGER.debug("Sending data in %d chunks", total_chunks)

            for i in range(0, len(print_data), chunk_size):
                chunk = print_data[i : i + chunk_size]
                chunk_num = i // chunk_size + 1
                _LOGGER.debug("Sending chunk %d/%d (%d bytes)", chunk_num, total_chunks, len(chunk))
                await self._client.write_gatt_char(
                    self._write_characteristic,
                    chunk,
                    response=False,  # Write without response for speed
                )
                # Small delay to avoid overwhelming the printer
                await asyncio.sleep(0.01)

            _LOGGER.info("Bluetooth driver: job %s completed successfully", job.id)
            _LOGGER.debug("Total bytes sent: %d", len(print_data))

        except ValueError as e:
            raise FatalError(f"Invalid image format: {e}") from e
        except asyncio.TimeoutError as e:
            raise RecoverableError(
                f"Bluetooth write timeout: {e}. Printer may be busy."
            ) from e
        except Exception as e:
            # BLE disconnection or other errors
            self._connected = False
            raise RecoverableError(
                f"Bluetooth print failed: {e}. Will retry."
            ) from e
