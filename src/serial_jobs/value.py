"""Functionality related to getting the values from devices."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from functools import cached_property
from typing import Generic, TypeVar, Union

from .data import Data, RegisterDataT
from .device import Device, RegisterSpec

ValueTypeT = TypeVar("ValueTypeT", bound=Union[float, int, str, date, datetime, time])


@dataclass(frozen=True)
class Value(Generic[ValueTypeT]):
    value_type: type[ValueTypeT]
    mapping: dict
    data: list[Data]
    register_specs: list[RegisterSpec]

    @classmethod
    def from_spec(cls, spec: dict) -> Value:
        value_type_name = spec.get("type", "")
        value_type: type[ValueTypeT]
        if value_type_name == "float":
            value_type = float  # type: ignore
        elif value_type_name == "int":
            value_type = int  # type: ignore
        else:
            value_type = globals().get(value_type_name, str)
        mapping = spec.get("mapping", {})
        data = [Data.from_spec(data_spec) for data_spec in spec["data"]]
        register_specs = [data_part.register_spec for data_part in data]

        return cls(
            value_type=value_type,
            mapping=mapping,
            data=data,
            register_specs=register_specs,
        )

    @cached_property
    def reverse_mapping(self) -> dict:
        if len(self.mapping.values()) != len(set(self.mapping.values())):
            raise RuntimeError("non-injective mapping cannot be reversed")
        return {v: k for k, v in self.mapping.items()}

    def get_calculated_data(self, device: Device) -> list[RegisterDataT]:
        return [data_part.calculate(device) for data_part in self.data]

    def calculate(self, device: Device) -> ValueTypeT:
        """Calculate and return the represented value.

        Use the cached data from the provided device's registers as input.
        """
        calculated_data: list[RegisterDataT] = self.get_calculated_data(device)
        mapped_data = calculated_data
        if self.mapping:
            mapped_data = [
                self.mapping.get(str(calculated_data_part), str(calculated_data_part))
                for calculated_data_part in calculated_data
            ]

        if self.value_type == datetime:
            int_data = [int(mapped_data_part) for mapped_data_part in mapped_data]
            tzinfo = datetime.now().astimezone().tzinfo
            timestamp = datetime(*int_data)  # type: ignore
            return timestamp.replace(tzinfo=tzinfo)  # type: ignore

        return self.value_type(*mapped_data)  # type: ignore

    def get_register_data(self, input_value: str) -> list[RegisterDataT]:
        """Parse the represented value from provided string.

        Return a list of the corresponding register data.
        """
        mapped_value = self.reverse_mapping.get(input_value, input_value)
        data: list[RegisterDataT]

        if self.value_type == date:
            date_value = date.fromisoformat(mapped_value)
            data = [date_value.year, date_value.month, date_value.day]
        elif self.value_type == datetime:
            datetime_value = datetime.fromisoformat(mapped_value)
            data = [
                datetime_value.year,
                datetime_value.month,
                datetime_value.day,
                datetime_value.hour,
                datetime_value.minute,
                datetime_value.second,
            ]
        elif self.value_type == time:
            time_value = time.fromisoformat(mapped_value)
            data = [time_value.hour, time_value.minute, time_value.second]
        elif self.value_type == float:
            data = [float(mapped_value)]
        elif self.value_type == int:
            data = [int(mapped_value)]
        elif self.value_type == str:
            data = [str(mapped_value)]

        return data

    def change_register_bytes(self, input_value: str, device: Device) -> int:
        """Change register bytes to match the provided input value.

        Use cached data from the provided device as input.

        Return the number of bytes processed.
        """
        register_data = self.get_register_data(input_value)

        bytes_processed = 0
        for data_part, register_data_part in zip(self.data, register_data):
            bytes_processed += data_part.change(register_data_part, device)

        return bytes_processed
