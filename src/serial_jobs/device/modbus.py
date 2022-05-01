"""Functions related to communication with Modbus devices."""
from __future__ import annotations

from dataclasses import dataclass
from enum import auto
from importlib import import_module

from minimalmodbus import Instrument, _serialports

from .base import Device, RegisterTypeT


@dataclass(frozen=True)
class ModbusDevice(Device):
    class RegisterType(Device.RegisterType):
        DISCRETE_INPUT = auto()  # 1 bit
        COIL = auto()  # 1 bit
        INPUT_REGISTER = auto()  # 2 bytes
        HOLDING_REGISTER = auto()  # 2 bytes

    instrument: Instrument

    @classmethod
    def from_config(cls, device_config: dict) -> ModbusDevice:
        device_id = device_config["id"]
        name = device_config.get("name")
        serial_config = device_config["serial"]
        protocol_config = device_config["protocol"]
        if "modbus_address" in protocol_config:
            instrument = get_instrument(
                serial_config["port"],
                serial_config["baud_rate"],
                serial_config["data_bits"],
                serial_config["stop_bits"],
                serial_config["parity"],
                serial_config["timeout"],
                protocol_config["modbus_address"],
            )
        else:
            instrument_module = import_module(protocol_config["module"])
            instrument_class = getattr(instrument_module, protocol_config["class"])
            instrument = instrument_class(
                serial_config["port"],
                serial_config["baud_rate"],
                serial_config["data_bits"],
                serial_config["stop_bits"],
                serial_config["parity"],
                serial_config["timeout"],
            )
        return cls(instance_id=device_id, name=name, instrument=instrument)

    def read_register(self, address: int, register_type: RegisterTypeT = None) -> bytes:
        return self.instrument.read_register(address)


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

    instrument = Instrument(port=port, slaveaddress=modbus_address)
    instrument.serial.baudrate = baud_rate
    instrument.serial.data_bits = data_bits
    instrument.serial.stop_bits = stop_bits
    instrument.serial.parity = parity
    instrument.serial.timeout = timeout
    return instrument
