"""Functions related to getting the values from devices."""
from __future__ import annotations

from dataclasses import dataclass

from .device import Device


@dataclass(frozen=True)
class DataPart:
    data_part_type: str
    address: int
    bitmask: int
    bitrightshift: int
    byte_index: int
    # discrete_input
    # coil
    # input_register_byte
    # register_byte
    # input_register
    # register

    @classmethod
    def from_config(cls, data_part_config: dict) -> DataPart:
        data_part_type, raw_data_config = next(iter(data_part_config.items()))
        address = raw_data_config["address"]
        byte_index = raw_data_config.get("byte_index")
        bitmask = raw_data_config.get("bitmask")
        bitrightshift = raw_data_config.get("bitrightshift")

        return cls(
            data_part_type=data_part_type,
            address=address,
            byte_index=byte_index,
            bitmask=bitmask,
            bitrightshift=bitrightshift,
        )

    def get_bytes(self, device: Device) -> bytes:
        # TODO Handle timeouts and recover from them gracefully
        return device.read_register(self.address)


@dataclass(frozen=True)
class Value:
    value_type: str
    scale_factor: int
    mapping: dict
    data: list[DataPart]

    @classmethod
    def from_config(cls, value_config: dict) -> Value:
        value_type = value_config.get("type", "unsigned_short")
        if value_type not in {
            "unsigned_short",
            "short",
            "unsigned_long",
            "long",
            "float",
            "datetime",
        }:
            raise ValueError(f"unsupported value type: {value_type}")

        scale_factor = value_config.get("scale_factor", 1)
        mapping = value_config.get("mapping", {})
        data = []
        for data_part_config in value_config["data"]:
            data.append(DataPart.from_config(data_part_config))

        return cls(
            value_type=value_type,
            scale_factor=scale_factor,
            mapping=mapping,
            data=data,
        )

    def get_data(self, device: Device) -> bytes:
        bytes_data = []
        for data_part in self.data:
            bytes_data.append(data_part.get_bytes(device))

        return b"".join(bytes_data)

    def get(self, device: Device) -> str:
        """Obtain and return the represented value."""
        data = self.get_data(device)
        value = int(data)
        scaled_value = value / self.scale_factor
        mapped_value = self.mapping.get(scaled_value, scaled_value)
        return str(mapped_value)
