"""Functionality related to calculating data from bytes provided by devices."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from struct import calcsize, pack, unpack
from typing import ClassVar, Optional, Union

from .device import AddressRange, Device, RegisterSpec, RegisterType

RegisterDataT = Union[float, int, str]


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

    struct_sizes = {
        unpack_type: calcsize(format_string)
        for unpack_type, format_string in format_strings.items()
    }

    unpack_type: str
    data_type: type[RegisterDataT]
    register_spec: RegisterSpec
    byte_order: Optional[list[int]]
    byte_offset: int
    byte_count: Optional[int]
    bitmask: Optional[int]
    bitshift: Optional[int]
    increase_by: Optional[int]
    scale_factor: Optional[int]

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
        readable_block = AddressRange(address, address + register_count)
        writable_block_spec = data_part_spec.get("writable_block")
        if writable_block_spec is None:
            writable_block = deepcopy(readable_block)
        else:
            writable_block = AddressRange(
                writable_block_spec["start_address"],
                writable_block_spec["stop_address"],
            )
        register_spec = RegisterSpec(register_type, readable_block, writable_block)
        byte_order = data_part_spec.get("byte_order")
        byte_index = data_part_spec.get("byte_index")
        byte_offset = data_part_spec.get("byte_offset", 0)
        byte_count = data_part_spec.get("byte_count")
        if byte_index is not None:
            byte_offset = byte_index
            byte_count = 1
        bitmask = data_part_spec.get("bitmask")
        bitshift = data_part_spec.get("bitshift")
        increase_by = data_part_spec.get("increase_by")
        scale_factor = data_part_spec.get("scale_factor")

        return cls(
            unpack_type=unpack_type,
            data_type=data_type,
            register_spec=register_spec,
            byte_order=byte_order,
            byte_offset=byte_offset,
            byte_count=byte_count,
            bitmask=bitmask,
            bitshift=bitshift,
            increase_by=increase_by,
            scale_factor=scale_factor,
        )

    def unpack(self, register_bytes: bytes) -> RegisterDataT:
        if self.unpack_type == "string":
            return register_bytes.decode("utf-8")
        return unpack(self.format_strings[self.unpack_type], register_bytes)[0]

    def pack(self, data: RegisterDataT) -> bytes:
        if self.unpack_type == "string":
            if not isinstance(data, str):
                raise RuntimeError("register data is not instance of str")
            return data.encode("utf-8")
        return pack(self.format_strings[self.unpack_type], data)

    def _reorder_register_bytes(self, register_bytes: bytes) -> bytes:
        if self.byte_order is not None:
            register_bytes = bytes(register_bytes[index] for index in self.byte_order)

        return register_bytes

    def _slice_register_bytes(self, register_bytes: bytes) -> bytes:
        register_bytes = register_bytes[self.byte_offset :]
        if self.byte_count:
            register_bytes = register_bytes[: self.byte_count]

        return register_bytes

    def calculate(self, device: Device) -> RegisterDataT:
        """Return the data calculated using bytes from the provided device."""
        register_bytes = device.get_bytes(self.register_spec)
        register_bytes = self._reorder_register_bytes(register_bytes)
        register_bytes = self._slice_register_bytes(register_bytes)

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

    # pylint: disable-next=abstract-method
    def change(self, register_data: RegisterDataT, device: Device) -> int:
        """Change register bytes to match the provided register data.

        1. Obtain the current register bytes from the device.
        2. Undo the configured calculations on the provided register data.
        3. Apply the changes to the corresponding register bytes.

        Return the number of bytes processed.
        """
        expected_size = self.struct_sizes[self.unpack_type]
        current_register_bytes = device.get_bytes(self.register_spec)
        current_register_bytes = self._reorder_register_bytes(current_register_bytes)

        register_bytes = bytearray(current_register_bytes)

        current_register_bytes = self._slice_register_bytes(current_register_bytes)

        current_data = self.data_type(self.unpack(current_register_bytes))

        if isinstance(register_data, (int, float)):
            if self.scale_factor:
                register_data *= self.scale_factor
            if self.increase_by:
                register_data -= self.increase_by

        if self.data_type == int:
            if not isinstance(current_data, int):
                raise RuntimeError("current data is not instance of int")

            register_data = int(register_data)
            if self.bitshift:
                if self.bitshift > 0:
                    register_data <<= self.bitshift
                elif self.bitshift < 0:
                    register_data >>= self.bitshift
            if self.bitmask:
                inverse_bitmask = (1 << 8 * expected_size) - 1
                register_data |= current_data ^ inverse_bitmask

        changed_bytes = self.pack(register_data)

        if self.byte_count:
            register_bytes[self.byte_offset : self.byte_count] = changed_bytes
        else:
            register_bytes[self.byte_offset :] = changed_bytes

        if self.byte_order is not None:
            register_bytes = bytearray(
                register_bytes[self.byte_order.index(i)] for i in range(expected_size)
            )

        return device.put_bytes(self.register_spec, register_bytes)
