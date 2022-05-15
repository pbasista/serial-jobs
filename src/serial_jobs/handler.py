"""Functionality related to handlers."""
from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from typing import ClassVar

from .device import Device
from .specification import SpecMixin
from .value import Value

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class Handler(SpecMixin):
    specs_by_id: ClassVar[dict[str, dict]] = {}

    mqtt_topic: str
    device: Device
    value: Value

    @classmethod
    def from_spec(cls, spec: dict) -> Handler:
        handler_id = spec["id"]
        name = spec.get("name")
        mqtt_topic = spec["mqtt_topic"]
        device_id = spec.get("device", Device.default_id())
        device = Device.from_id(device_id)
        value_spec = spec["value"]
        value = Value.from_spec(value_spec)
        return cls(
            spec_id=handler_id,
            name=name,
            mqtt_topic=mqtt_topic,
            device=device,
            value=value,
        )

    def clear_data(self) -> int:
        """Clear the data for this handler on the configured device.

        Return the number of registers cleared.
        """
        return self.device.clear_registers(self.value.register_specs)

    async def fetch_data(self) -> int:
        """Fetch the data for this handler from the configured device.

        Return the number of bytes read.
        """
        return await self.device.read_registers(
            self.value.register_specs, include_writable_block=True
        )

    def change_data(self, input_value: str) -> int:
        """Change the cached data for this handler on the configured device.

        Return the number of bytes processed.
        """
        return self.value.change_register_bytes(input_value, self.device)

    async def dump_data(self) -> int:
        """Dump the data of this handler to the configured device.

        Return the number of bytes written.
        """
        return await self.device.write_registers(self.value.register_specs)

    async def handle(self, input_value: str, write_to_device: bool = True) -> None:
        """Handle the provided input value according to the configuration."""
        LOGGER.info("handler %s: handling input value %s", self.spec_id, input_value)
        self.clear_data()
        await self.fetch_data()
        self.change_data(input_value)
        if write_to_device:
            await self.dump_data()
        else:
            LOGGER.warning("handler %s: NOT writing to device", self.spec_id)
