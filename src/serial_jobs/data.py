"""Functionality related to calculating data from bytes provided by devices."""
from __future__ import annotations

from dataclasses import dataclass
from struct import unpack
from typing import ClassVar, Optional, Union

from .device import Device, RegisterSpec, RegisterType

RegisterDataT = Union[int, float, str]


@dataclass(frozen=True)
# pylint: disable-next=too-many-instance-attributes
class Data:
    format_strings: ClassVar[dict[str, str]] = {
        "byte": ">B",
        "signed_byte": ">b",
        "short": ">H",
        "signed_short": ">h",
        "long": ">L",
        "signed_long": ">l",
        "float": ">f",
        "double": ">d",
    }

    unpack_type: str
    data_type: type[RegisterDataT]
    register_spec: RegisterSpec
    byte_order: Optional[list[int]]
    byte_offset: int
    byte_count: Optional[int]
    bitmask: Optional[int]
    bitshift: Optional[int]
    scale_factor: Optional[int]
    increase_by: Optional[int]

    @classmethod
    # pylint: disable-next=too-many-locals
    def from_spec(cls, spec: dict) -> Data:
        unpack_type, data_part_spec = next(iter(spec.items()))
        data_type: type[RegisterDataT] = str
        if unpack_type in (
            "byte",
            "signed_byte",
            "short",
            "signed_short",
            "long",
            "signed_long",
        ):
            data_type = int
        elif unpack_type in ("float", "double"):
            data_type = float
        register_type = RegisterType[data_part_spec["register_type"].upper()]
        register_count = data_part_spec["register_count"]
        address = data_part_spec["address"]
        register_spec = RegisterSpec(register_type, address, address + register_count)
        byte_order = data_part_spec.get("byte_order")
        byte_index = data_part_spec.get("byte_index")
        byte_offset = data_part_spec.get("byte_offset", 0)
        byte_count = data_part_spec.get("byte_count")
        if byte_index is not None:
            byte_offset = byte_index
            byte_count = 1
        bitmask = data_part_spec.get("bitmask")
        bitshift = data_part_spec.get("bitshift")
        scale_factor = data_part_spec.get("scale_factor")
        increase_by = data_part_spec.get("increase_by")

        return cls(
            unpack_type=unpack_type,
            data_type=data_type,
            register_spec=register_spec,
            byte_order=byte_order,
            byte_offset=byte_offset,
            byte_count=byte_count,
            bitmask=bitmask,
            bitshift=bitshift,
            scale_factor=scale_factor,
            increase_by=increase_by,
        )

    def unpack(self, register_bytes: bytes) -> RegisterDataT:
        if self.unpack_type == "string":
            return register_bytes.decode("utf-8")
        return unpack(self.format_strings[self.unpack_type], register_bytes)[0]

    def calculate(self, device: Device) -> RegisterDataT:
        """Return the data calculated using bytes from the provided device."""
        register_bytes = device.get_bytes(self.register_spec)
        if self.byte_order is not None:
            register_bytes = bytes(register_bytes[index] for index in self.byte_order)
        register_bytes = register_bytes[self.byte_offset :]
        if self.byte_count:
            register_bytes = register_bytes[: self.byte_count]

        data = self.data_type(self.unpack(register_bytes))

        if isinstance(data, int):
            if self.bitmask:
                data &= self.bitmask
            if self.bitshift:
                if self.bitshift > 0:
                    data >>= self.bitshift
                elif self.bitshift < 0:
                    data <<= self.bitshift

        if isinstance(data, (int, float)):
            if self.increase_by:
                data += self.increase_by
            if self.scale_factor:
                data /= self.scale_factor

        return data  # type: ignore
