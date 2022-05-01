from .base import Device
from .bms import BMSDevice
from .modbus import ModbusDevice


def get_device(device_config: dict) -> Device:
    """Return an instance Device initialized from provided configuration."""
    device_type = device_config["type"]
    device_class = globals()[device_type]
    return device_class.from_config(device_config)
