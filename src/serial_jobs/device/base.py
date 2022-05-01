"""Functions related to communication with individual devices."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from ..base import CachedInstance

DeviceT = TypeVar("DeviceT", bound="Device")
RegisterTypeT = TypeVar("RegisterTypeT", bound="Device.RegisterType")


@dataclass(frozen=True)
class Device(CachedInstance):
    class RegisterType(Enum):
        ...

    name: str | None

    @classmethod
    def from_config(cls: type[DeviceT], device_config: dict) -> DeviceT:
        raise NotImplementedError

    def read_register(self, address: int, register_type: RegisterTypeT = None) -> bytes:
        raise NotImplementedError
