"""Functionality related to communication with BMS devices."""
from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from struct import pack
from time import sleep

from serial import Serial

from .base import Device, RegisterType

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
# pylint: disable-next=abstract-method
class BMSDevice(Device):
    serial: Serial = None

    @classmethod
    def from_spec(cls, spec: dict) -> BMSDevice:
        device_id = spec["id"]
        name = spec.get("name")
        serial_config = spec["serial"]
        port = serial_config["port"]
        lock = cls.get_lock(port)
        serial = Serial(
            port=port,
            baudrate=serial_config["baud_rate"],
            bytesize=serial_config["data_bits"],
            stopbits=serial_config["stop_bits"],
            parity=serial_config["parity"],
            timeout=serial_config["timeout"],
        )

        serial.close()

        return cls(spec_id=device_id, name=name, lock=lock, serial=serial)

    def query(self, request: bytes) -> bytes:
        """Send the provided request to the device and return its response."""
        # TODO: Add validation, handling of errors and timeouts
        LOGGER.debug("device %s: sending data %s", self.spec_id, request.hex(" "))

        if not self.serial.is_open:
            self.serial.open()

        # Request structure:
        # * 0xDD
        # * 1 byte of operation type (0xA5: read, 0x5A: write)
        # * 1 byte of register address
        # * 1 byte of data length
        # * "data length" bytes of content
        # * 2 bytes of checksum
        # * 0x77
        self.serial.write(request)

        # Response structure:
        # * 0xDD
        # * 1 byte of register address
        # * 1 byte of response status (0x00: OK, 0x80: error)
        # * 1 byte of data length
        # * "data length" bytes of content
        # * 2 bytes of checksum
        # * 0x77
        response = bytearray()

        attempts = 0
        response.extend(self.serial.read(4))

        while len(response) < 4 and attempts < 3:
            sleep(0.5)
            response.extend(self.serial.read(4))
            attempts += 1

        if len(response) < 4:
            raise RuntimeError(f"only {len(response)} bytes received from the device")

        length = response[3]
        response.extend(self.serial.read(length + 3))

        checksum_value = 0x10000 - sum(response[2:-3])
        expected_checksum = pack(">H", checksum_value)
        received_checksum = response[-3:-1]
        if received_checksum != expected_checksum:
            LOGGER.error("device %s: response checksum error", self.spec_id)

        self.serial.close()

        LOGGER.debug("device %s: received data %s", self.spec_id, response.hex(" "))

        return response

    def _read_register(self, address: int, register_type: RegisterType) -> int:
        LOGGER.debug(
            "device %s: reading from %s BMS register address %d",
            self.spec_id,
            register_type.name,
            address,
        )

        if register_type == RegisterType.DEFAULT:
            input_values = [0xDD, 0xA5, address, 0]
            checksum = 0x10000 - sum(input_values[2:])
            request = bytes(input_values) + pack(">H", checksum) + bytes([0x77])
            bytes_value = self.query(request)[4:-3]

        self.registers[register_type][address] = bytes_value
        return len(bytes_value)
