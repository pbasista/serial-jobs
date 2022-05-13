"""Functionality related to getting the values from devices."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Generic, TypeVar, Union

from .data import Data, RegisterDataT
from .device import Device, RegisterSpec

ValueTypeT = TypeVar("ValueTypeT", bound=Union[str, date, datetime, time])


@dataclass(frozen=True)
class Value(Generic[ValueTypeT]):
    value_type: type[ValueTypeT]
    mapping: dict
    data: list[Data]
    register_specs: list[RegisterSpec]

    @classmethod
    def from_spec(cls, spec: dict) -> Value:
        value_type_name = spec.get("type", "")
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
