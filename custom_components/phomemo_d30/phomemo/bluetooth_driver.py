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
WRITE_CHAR_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"  # ff02 is WRITE, ff01 is READ


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
        _LOGGER.info("=== BLUETOOTH CONNECTION START ===")
        _LOGGER.debug("Target address: %s", self._address)
        _LOGGER.debug("Write characteristic UUID: %s", self._write_characteristic)

        try:
            # Get BLE device from HA's Bluetooth integration
            _LOGGER.debug("Looking up BLE device from HA Bluetooth integration")
            ble_device = bluetooth.async_ble_device_from_address(
                self._hass,
                self._address,
                connectable=True
            )

            if ble_device is None:
                _LOGGER.error("❌ BLE device %s not found in HA Bluetooth", self._address)
                _LOGGER.error("Make sure the printer is powered on and in range")
                _LOGGER.error("Check HA Settings -> Devices & Services -> Bluetooth")
                raise FatalError(
                    f"Bluetooth device {self._address} not found. "
                    "Make sure the printer is powered on and in range."
                )

            _LOGGER.info("✓ Found BLE device: %s", ble_device)
            _LOGGER.debug("BLE device name: %s", ble_device.name if hasattr(ble_device, 'name') else 'Unknown')
            _LOGGER.debug("BLE device address: %s", ble_device.address if hasattr(ble_device, 'address') else 'Unknown')

            # Use bleak-retry-connector for reliable connection
            _LOGGER.debug("Establishing connection with max_attempts=3...")
            self._client = await establish_connection(
                BleakClient,
                ble_device,
                self._address,
                max_attempts=3,
            )

            _LOGGER.debug("BleakClient created: %s", self._client)
            _LOGGER.debug("Client is_connected: %s", self._client.is_connected)

            # Log available services and characteristics
            if self._client.is_connected:
                try:
                    services = self._client.services
                    _LOGGER.debug("Available BLE services:")
                    for service in services:
                        _LOGGER.debug("  Service: %s", service.uuid)
                        for char in service.characteristics:
                            _LOGGER.debug("    Characteristic: %s (properties: %s)",
                                         char.uuid, char.properties)
                except Exception as e:
                    _LOGGER.debug("Could not enumerate services: %s", e)

            self._connected = True

            # Verify write characteristic exists
            try:
                char = self._client.services.get_characteristic(self._write_characteristic)
                if char:
                    _LOGGER.info("✓ Found write characteristic: %s", self._write_characteristic)
                    _LOGGER.debug("  Properties: %s", char.properties)
                else:
                    _LOGGER.warning("⚠️  Write characteristic %s not found", self._write_characteristic)
            except Exception as e:
                _LOGGER.debug("Could not verify characteristic: %s", e)

            _LOGGER.info("✓ Successfully connected to Bluetooth device %s", self._address)
            _LOGGER.info("=== BLUETOOTH CONNECTION COMPLETE ===")

        except asyncio.TimeoutError as e:
            _LOGGER.error("❌ Connection timeout: %s", e)
            _LOGGER.error("Check printer is in range and not connected to another device")
            raise RecoverableError(
                f"Bluetooth connection timeout: {e}. Check printer range."
            ) from e
        except Exception as e:
            _LOGGER.error("❌ Connection failed: %s", e, exc_info=True)
            raise RecoverableError(
                f"Bluetooth connection failed: {e}"
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from the printer."""
        _LOGGER.info("=== BLUETOOTH DISCONNECT START ===")
        _LOGGER.debug("Current connection state: %s", self._connected)
        _LOGGER.debug("Client exists: %s", self._client is not None)

        if self._client and self._connected:
            _LOGGER.debug("Disconnecting from Bluetooth device %s", self._address)
            try:
                await self._client.disconnect()
                self._connected = False
                _LOGGER.info("✓ Disconnected from Bluetooth device %s", self._address)
            except Exception as e:
                _LOGGER.warning("Error during disconnect: %s", e)
                self._connected = False
        else:
            _LOGGER.debug("No active connection to disconnect")

        _LOGGER.info("=== BLUETOOTH DISCONNECT COMPLETE ===")

    def is_connected(self) -> bool:
        """Check if connected to printer."""
        is_conn = self._connected and self._client is not None and self._client.is_connected
        _LOGGER.debug("Connection check: _connected=%s, _client exists=%s, client.is_connected=%s → result=%s",
                     self._connected, self._client is not None,
                     self._client.is_connected if self._client else False,
                     is_conn)
        return is_conn


    async def _send_data(self, data: bytes, chunk_size: int = 128) -> None:
        """Send data to printer in BLE-sized chunks.

        Args:
            data: Bytes to send
            chunk_size: Maximum bytes per BLE write (default: 128, matches Web Bluetooth reference)
        """
        if not self._client:
            _LOGGER.error("❌ Cannot send data: BleakClient is None")
            raise FatalError("BleakClient not initialized")

        if not self._client.is_connected:
            _LOGGER.error("❌ Cannot send data: BLE client not connected")
            raise RecoverableError("BLE client disconnected")

        total_chunks = (len(data) + chunk_size - 1) // chunk_size
        _LOGGER.debug("Preparing to send %d bytes in %d chunks (chunk_size=%d)",
                     len(data), total_chunks, chunk_size)

        # Log first bytes of data as hex preview
        preview_len = min(32, len(data))
        _LOGGER.debug("Data preview (first %d bytes): %s%s",
                     preview_len,
                     data[:preview_len].hex(),
                     "..." if len(data) > preview_len else "")

        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            chunk_num = i // chunk_size + 1

            _LOGGER.debug("→ Sending BLE chunk %d/%d (%d bytes)",
                         chunk_num, total_chunks, len(chunk))
            _LOGGER.debug("  Chunk hex (first 16 bytes): %s%s",
                         chunk[:16].hex(),
                         "..." if len(chunk) > 16 else "")

            try:
                await self._client.write_gatt_char(
                    self._write_characteristic,
                    chunk,
                    response=True,  # Write with response (matches Web Bluetooth reference implementation)
                )
                _LOGGER.debug("  ✓ Chunk %d sent successfully", chunk_num)
            except Exception as e:
                _LOGGER.error("❌ Failed to send chunk %d: %s", chunk_num, e, exc_info=True)
                raise RecoverableError(f"BLE write failed on chunk {chunk_num}: {e}") from e

            # Small delay to avoid overwhelming the printer
            await asyncio.sleep(0.01)

        _LOGGER.debug("✓ All %d chunks sent successfully", total_chunks)

    async def _ensure_connected(self) -> None:
        """Ensure we're connected to the printer, connecting if needed.

        Raises:
            RecoverableError: If connection fails (allows retry)
        """
        if self.is_connected():
            _LOGGER.debug("Already connected to printer")
            return

        _LOGGER.info("Not connected, attempting to connect to printer")
        try:
            await self.connect()
            # Give the Bluetooth stack time to stabilize after connection
            _LOGGER.debug("Waiting 1 second for connection to stabilize")
            await asyncio.sleep(1.0)
        except FatalError as e:
            # Convert FatalError to RecoverableError to allow retries
            # (printer might be turning on, coming into range, etc.)
            _LOGGER.warning("Connection failed, will retry: %s", e)
            raise RecoverableError(f"Connection failed: {e}") from e

    async def print(self, job: PrintJob) -> None:
        """Print a job via Bluetooth.

        Args:
            job: Print job to execute

        Raises:
            FatalError: Invalid image format, not connected
            RecoverableError: Connection timeout, BLE disconnection
        """
        _LOGGER.info("=" * 60)
        _LOGGER.info("=== BLUETOOTH PRINT START ===")
        _LOGGER.info("Job ID: %s", job.id)
        _LOGGER.info("Image size: %s", job.image.size)
        _LOGGER.info("Image mode: %s", job.image.mode)
        _LOGGER.info("Paper size: %dx%d mm", job.width, job.height)
        _LOGGER.info("Darkness: %d", job.darkness)
        _LOGGER.info("Rotation: %d°", job.rotate)
        _LOGGER.info("=" * 60)

        # Ensure we're connected before printing
        await self._ensure_connected()
        _LOGGER.debug("✓ Connection status verified")

        try:
            # Preprocess image (run in thread pool to avoid blocking)
            _LOGGER.info("Step 1/4: Preprocessing image...")
            _LOGGER.debug("  Original size: %s", job.image.size)
            _LOGGER.debug("  Original mode: %s", job.image.mode)
            _LOGGER.debug("  Target width: 96 dots (D30 printer width)")

            processed_image = await asyncio.to_thread(
                protocol.preprocess_image,
                job.image,
            )

            _LOGGER.info("  ✓ Image preprocessed")
            _LOGGER.debug("  Processed size: %s", processed_image.size)
            _LOGGER.debug("  Processed mode: %s", processed_image.mode)
            _LOGGER.debug("  Aspect ratio preserved: original=%s, processed=%s",
                         job.image.size[0] / job.image.size[1] if job.image.size[1] > 0 else 'N/A',
                         processed_image.size[0] / processed_image.size[1] if processed_image.size[1] > 0 else 'N/A')

            # Send initialization packets (required before each print)
            _LOGGER.info("Step 2/4: Sending initialization packets...")
            init_packets = protocol.get_initialization_packets()
            _LOGGER.debug("  Total init packets: %d", len(init_packets))

            for i, packet in enumerate(init_packets):
                _LOGGER.debug("  Init packet %d/%d: %d bytes, hex=%s",
                             i + 1, len(init_packets), len(packet), packet.hex())
                await self._send_data(packet)

            _LOGGER.info("  ✓ All initialization packets sent")

            # Encode to D30 protocol bytes (returns list of commands, one per chunk)
            _LOGGER.info("Step 3/4: Encoding print commands...")
            _LOGGER.debug("  Encoding image to D30 protocol format...")

            print_commands = await asyncio.to_thread(
                protocol.encode_print_command,
                processed_image,
            )

            _LOGGER.info("  ✓ Print commands encoded")
            _LOGGER.debug("  Generated %d print command(s)", len(print_commands))
            for i, cmd in enumerate(print_commands):
                _LOGGER.debug("  Command %d: %d bytes", i + 1, len(cmd))

            # Send each print command
            _LOGGER.info("Step 4/4: Sending print commands to printer...")
            total_bytes = 0
            for i, command in enumerate(print_commands):
                _LOGGER.debug("  Sending print command %d/%d (%d bytes)",
                             i + 1, len(print_commands), len(command))
                await self._send_data(command)
                total_bytes += len(command)
                _LOGGER.debug("  ✓ Print command %d sent", i + 1)

            _LOGGER.info("  ✓ All print commands sent")
            _LOGGER.info("=" * 60)
            _LOGGER.info("=== BLUETOOTH PRINT COMPLETE ===")
            _LOGGER.info("Job %s completed successfully", job.id)
            _LOGGER.info("Total data sent: %d bytes", total_bytes)
            _LOGGER.info("Init packets: %d bytes", sum(len(p) for p in init_packets))
            _LOGGER.info("Print commands: %d bytes", total_bytes)
            _LOGGER.info("=" * 60)

        except ValueError as e:
            _LOGGER.error("❌ Invalid image format: %s", e, exc_info=True)
            raise FatalError(f"Invalid image format: {e}") from e
        except asyncio.TimeoutError as e:
            _LOGGER.error("❌ Bluetooth write timeout: %s", e)
            _LOGGER.error("Printer may be busy, out of range, or turned off")
            raise RecoverableError(
                f"Bluetooth write timeout: {e}. Printer may be busy."
            ) from e
        except Exception as e:
            # BLE disconnection or other errors
            _LOGGER.error("❌ Bluetooth print failed: %s", e, exc_info=True)
            self._connected = False
            _LOGGER.error("Marked connection as disconnected, will retry")
            raise RecoverableError(
                f"Bluetooth print failed: {e}. Will retry."
            ) from e
