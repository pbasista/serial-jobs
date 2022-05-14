"""Functionality related to communication with Modbus devices."""
from __future__ import annotations

from dataclasses import dataclass
from logging import DEBUG, getLogger
from struct import pack
from typing import ClassVar, Optional, Union

from minimalmodbus import Instrument, _serialports

from .base import Device, RegisterType

LOGGER = getLogger(__name__)


def pack_byte(value: Union[bool, int]) -> bytes:
    return pack(">B", value)


def pack_short(value: int) -> bytes:
    return pack(">H", value)


@dataclass(frozen=True)
class ModbusDevice(Device):
    default_register_type: ClassVar[RegisterType] = RegisterType.INPUT

    function_codes: ClassVar[dict[RegisterType, int]] = {
        RegisterType.COIL: 1,
        RegisterType.DISCRETE: 2,
        RegisterType.HOLDING: 3,
        RegisterType.INPUT: 4,
    }

    instrument: Optional[Instrument] = None

    @classmethod
    def from_spec(cls, spec: dict) -> ModbusDevice:
        device_id = spec["id"]
        name = spec.get("name")
        serial_config = spec["serial"]
        protocol_config = spec["protocol"]
        port = serial_config["port"]
        lock = cls.get_lock(port)
        instrument = get_instrument(
            port=port,
            baud_rate=serial_config["baud_rate"],
            data_bits=serial_config["data_bits"],
            stop_bits=serial_config["stop_bits"],
            parity=serial_config["parity"],
            timeout=serial_config["timeout"],
            modbus_address=protocol_config["modbus_address"],
        )
        return cls(spec_id=device_id, name=name, lock=lock, instrument=instrument)

    def _read_register(self, address: int, register_type: RegisterType) -> int:
        if self.instrument is None:
            raise RuntimeError("instrument is unavailable")

        if register_type == register_type.DEFAULT:
            register_type = self.default_register_type

        LOGGER.debug(
            "device %s: reading from %s Modbus register address %d",
            self.spec_id,
            register_type.name,
            address,
        )

        if register_type in (RegisterType.COIL, RegisterType.DISCRETE):
            int_value = self.instrument.read_bit(
                address, functioncode=self.function_codes[register_type]
            )
            bytes_value = pack_byte(int_value)
        elif register_type in (
            RegisterType.HOLDING,
            RegisterType.INPUT,
        ):
            int_value = self.instrument.read_register(
                address, functioncode=self.function_codes[register_type]
            )
            bytes_value = pack_short(int_value)

        self.registers[register_type][address] = bytes_value
        return len(bytes_value)

    def _read_register_range(
        self, start_address: int, stop_address: int, register_type: RegisterType
    ) -> int:
        if self.instrument is None:
            raise RuntimeError("instrument is unavailable")

        if register_type == register_type.DEFAULT:
            register_type = self.default_register_type

        LOGGER.debug(
            "device %s: reading from %s Modbus register block of addresses %d-%d",
            self.spec_id,
            register_type.name,
            start_address,
            stop_address,
        )

        number_of_registers = stop_address - start_address
        if register_type in (RegisterType.COIL, RegisterType.DISCRETE):
            int_values = self.instrument.read_bits(
                start_address,
                number_of_bits=number_of_registers,
                functioncode=self.function_codes[register_type],
            )
            bytes_values = [pack_byte(int_value) for int_value in int_values]
        elif register_type in (
            RegisterType.HOLDING,
            RegisterType.INPUT,
        ):
            int_values = self.instrument.read_registers(
                start_address,
                number_of_registers=number_of_registers,
                functioncode=self.function_codes[register_type],
            )
            bytes_values = [pack_short(int_value) for int_value in int_values]

        for address, bytes_value in zip(
            range(start_address, stop_address), bytes_values
        ):
            self.registers[register_type][address] = bytes_value

        return len(bytes_values[0]) * len(bytes_values)


# pylint: disable-next=too-many-arguments
def get_instrument(
    port: str,
    baud_rate: int,
    data_bits: int,
    stop_bits: float,
    parity: str,
    timeout: float,
    modbus_address: int,
) -> Instrument:
    """Return the Modbus instrument with the specified parameters."""
    # Remove any previously used Serial instances from cache.
    # This allows using the same serial port with different settings.
    _serialports.clear()

    instrument = Instrument(
        port=port,
        slaveaddress=modbus_address,
        close_port_after_each_call=True,
        debug=LOGGER.getEffectiveLevel() < DEBUG,
    )
    instrument.serial.baudrate = baud_rate
    instrument.serial.data_bits = data_bits
    instrument.serial.stop_bits = stop_bits
    instrument.serial.parity = parity
    instrument.serial.timeout = timeout
    return instrument
