"""Base functionality related to communication with individual devices."""
from __future__ import annotations

from asyncio import Lock
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import islice
from logging import getLogger
from typing import ClassVar, Iterable, Iterator, Optional, Sequence, Tuple, TypeVar

from ..specification import SpecMixin

DeviceT = TypeVar("DeviceT", bound="Device")
ChunkT = TypeVar("ChunkT")

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class AddressRange:
    start_address: int
    stop_address: int

    def __post_init__(self):
        if self.stop_address <= self.start_address:
            raise ValueError("stop address is lower than or equal to start address")

    @property
    def addresses(self) -> range:
        return range(self.start_address, self.stop_address)


def chunks(iterable: Iterable[ChunkT], chunk_size: int) -> Iterator[Tuple[ChunkT, ...]]:
    """Return a chunks iterator over the provided iterable.

    The returned iterator returns chunks (tuples)
    of the provided size from the provided iterable.
    """
    iterator = iter(iterable)
    return iter(lambda: tuple(islice(iterator, chunk_size)), ())


def get_ranges(numbers: Iterable[int]) -> list[range]:
    """Return a list of ranges representing the provided sequence."""
    ranges = []
    sorted_numbers = sorted(numbers)
    range_start = sorted_numbers[0]
    previous_number = range_start
    for number in sorted_numbers[1:]:
        if number - 1 != previous_number:
            ranges.append(range(range_start, previous_number + 1))
            range_start = number
        previous_number = number
    ranges.append(range(range_start, previous_number + 1))

    return ranges


class RegisterType(Enum):
    DEFAULT = auto()  # device-specific default register type
    COIL = auto()  # 1 bit right justified within 1 byte
    DISCRETE = auto()  # 1 bit right justified within 1 byte
    HOLDING = auto()  # 2 bytes
    INPUT = auto()  # 2 bytes


@dataclass(frozen=True)
class RegisterSpec:
    register_type: RegisterType
    readable_block: AddressRange
    writable_block: AddressRange

    @property
    def readable_addresses(self) -> range:
        return self.readable_block.addresses

    @property
    def writable_addresses(self) -> range:
        return self.writable_block.addresses


@dataclass(frozen=True)
class Device(SpecMixin):
    locks: ClassVar[dict[str, Lock]] = {}
    default_register_type: ClassVar[RegisterType] = RegisterType.DEFAULT

    specs_by_id: ClassVar[dict[str, dict]] = {}

    registers: dict[RegisterType, dict[int, bytes]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    lock: Optional[Lock] = None

    @classmethod
    def get_register_size(cls, register_type: RegisterType) -> int:
        raise NotImplementedError

    @classmethod
    def get_lock(cls: type[DeviceT], lock_id: str) -> Lock:
        lock = cls.locks.get(lock_id)
        if lock is None:
            LOGGER.info("creating device lock %s", lock_id)
            lock = Lock()
            cls.locks[lock_id] = lock

        return lock

    @classmethod
    def from_spec(cls: type[DeviceT], spec: dict) -> DeviceT:
        subclasses_by_name = {
            subcls.__name__: subcls for subcls in cls.__subclasses__()
        }
        device_type = spec["type"]
        subclass = subclasses_by_name[device_type]
        return subclass.from_spec(spec)

    def _read_register(self, address: int, register_type: RegisterType) -> int:
        """Perform a single read operation on the device.

        Get the value of the register
        of the provided type at the provided address
        and store it into cache.

        Return the number of bytes read.
        """
        raise NotImplementedError

    def _read_register_range(
        self, start_address: int, stop_address: int, register_type: RegisterType
    ) -> int:
        """Perform a sequential read operation on the device.

        Get the values of the provided continuous range of registers
        of the provided type and store them into cache.

        Return the number of bytes read.
        """
        if register_type == RegisterType.DEFAULT:
            register_type = self.default_register_type

        LOGGER.debug(
            "device %s: reading from %s register addresses %d-%d",
            self.spec_id,
            register_type.name,
            start_address,
            stop_address,
        )

        bytes_read = 0
        for address in range(start_address, stop_address):
            bytes_read += self._read_register(address, register_type)

        return bytes_read

    def _write_register(self, address: int, register_type: RegisterType) -> int:
        """Perform a single write operation on the device.

        Get the cached value of the register
        of the provided type at the provided address
        and write it to the device.

        Return the number of bytes written.
        """
        raise NotImplementedError

    def _write_register_range(
        self, start_address: int, stop_address: int, register_type: RegisterType
    ) -> int:
        """Perform a sequential write operation on the device.

        Get the cached values of the provided continuous range of registers
        of the provided type and write them to the device.

        Return the number of bytes written.
        """
        if register_type == RegisterType.DEFAULT:
            register_type = self.default_register_type

        LOGGER.debug(
            "device %s: writing to %s register addresses %d-%d",
            self.spec_id,
            register_type.name,
            start_address,
            stop_address,
        )

        bytes_written = 0
        for address in range(start_address, stop_address):
            bytes_written += self._write_register(address, register_type)

        return bytes_written

    async def read_registers(
        self,
        register_specs: Sequence[RegisterSpec],
        include_writable_block: bool = False,
    ) -> int:
        """Read data from the specified registers.

        Return the number of bytes read.
        """
        register_specs_by_type: dict[RegisterType, set[int]] = defaultdict(set)
        for register_spec in register_specs:
            register_specs_by_type[register_spec.register_type] |= set(
                register_spec.readable_addresses
            )
            if include_writable_block:
                register_specs_by_type[register_spec.register_type] |= set(
                    register_spec.writable_addresses
                )

        if self.lock is None:
            raise RuntimeError("lock is unavailable")

        bytes_read = 0
        async with self.lock:
            for register_type, register_addresses in register_specs_by_type.items():
                address_ranges = get_ranges(register_addresses)
                for address_range in address_ranges:
                    if len(address_range) == 1:
                        bytes_read += self._read_register(
                            address_range.start, register_type
                        )
                    else:
                        bytes_read += self._read_register_range(
                            address_range.start, address_range.stop, register_type
                        )

        return bytes_read

    async def write_registers(self, register_specs: Sequence[RegisterSpec]) -> int:
        """Write data from cache to the specified registers.

        Return the number of bytes written.
        """
        register_specs_by_type: dict[RegisterType, set[int]] = defaultdict(set)
        for register_spec in register_specs:
            register_specs_by_type[register_spec.register_type] |= set(
                register_spec.writable_addresses
            )

        if self.lock is None:
            raise RuntimeError("lock is unavailable")

        bytes_written = 0
        async with self.lock:
            for register_type, register_addresses in register_specs_by_type.items():
                address_ranges = get_ranges(register_addresses)
                for address_range in address_ranges:
                    if len(address_range) == 1:
                        bytes_written += self._write_register(
                            address_range.start, register_type
                        )
                    else:
                        bytes_written += self._write_register_range(
                            address_range.start, address_range.stop, register_type
                        )

        return bytes_written

    def get_bytes(self, register_spec: RegisterSpec) -> bytes:
        """Return the cached bytes from the specified register."""
        if register_spec.register_type == RegisterType.DEFAULT:
            register_type = self.default_register_type
        else:
            register_type = register_spec.register_type

        return b"".join(
            (
                self.registers[register_type][address]
                for address in register_spec.readable_addresses
            )
        )

    def put_bytes(self, register_spec: RegisterSpec, register_bytes: bytes) -> int:
        """Put the provided register bytes to cache.

        Only change the readable register addresses.

        The registers in the writable block
        that are not also part of the readable block
        will be kept unchanged so that their original values
        could be written to the device.

        Return the number of bytes processed.
        """
        if register_spec.register_type == RegisterType.DEFAULT:
            register_type = self.default_register_type
        else:
            register_type = register_spec.register_type

        register_size = self.get_register_size(register_type)

        for address, ints_chunk in zip(
            register_spec.readable_addresses, chunks(register_bytes, register_size)
        ):
            self.registers[register_type][address] = bytes(ints_chunk)

        return len(register_bytes)

    def clear_registers(self, register_specs: Sequence[RegisterSpec]) -> int:
        """Clear the data from the specified registers.

        Return the number of registers cleared.
        """
        register_specs_by_type: dict[RegisterType, set[int]] = defaultdict(set)
        for register_spec in register_specs:
            register_specs_by_type[register_spec.register_type].union(
                set(register_spec.readable_addresses),
                set(register_spec.writable_addresses),
            )

        registers_cleared = 0
        for register_type, register_addresses in register_specs_by_type.items():
            for register_address in register_addresses:
                self.registers[register_type].pop(register_address, None)
            registers_cleared += len(register_addresses)

        LOGGER.debug(
            "device %s: cleared data from %s registers",
            self.spec_id,
            registers_cleared,
        )

        return registers_cleared
