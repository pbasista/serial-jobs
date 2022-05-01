"""Functions related to communication with BMS devices."""
from __future__ import annotations

from dataclasses import dataclass

from .base import Device


@dataclass(frozen=True)
class BMSDevice(Device):
    @classmethod
    def from_config(cls, device_config: dict) -> BMSDevice:
        device_id = device_config["id"]
        name = device_config.get("name")
        return cls(instance_id=device_id, name=name)

    def read_register(
        self, address: int, register_type: BMSDevice.RegisterType = None
    ) -> bytes:
        return bytes()
