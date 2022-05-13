"""Functionality related to performing tasks."""
from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from typing import ClassVar

from .device import Device
from .mqtt import MQTTBroker
from .specification import SpecMixin
from .value import Value

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class Task(SpecMixin):
    specs_by_id: ClassVar[dict[str, dict]] = {}

    mqtt_topic: str
    mqtt_broker: MQTTBroker
    device: Device
    value: Value

    @classmethod
    def from_spec(cls, spec: dict) -> Task:
        task_id = spec["id"]
        name = spec.get("name")
        mqtt_topic = spec["mqtt_topic"]
        mqtt_broker_id = spec.get("mqtt_broker", MQTTBroker.default_id())
        mqtt_broker = MQTTBroker.from_id(mqtt_broker_id)
        device_id = spec.get("device", Device.default_id())
        device = Device.from_id(device_id)
        value_spec = spec["value"]
        value = Value.from_spec(value_spec)
        return cls(
            spec_id=task_id,
            name=name,
            mqtt_topic=mqtt_topic,
            mqtt_broker=mqtt_broker,
            device=device,
            value=value,
        )

    def clear_data(self) -> int:
        """Clear the data for this task on the configured device.

        Return the number of registers cleared.
        """
        return self.device.clear_registers(self.value.register_specs)

    def fetch_data(self) -> int:
        """Fetch the data for this task from the configured device.

        Return the number of bytes read.
        """
        return self.device.read_registers(self.value.register_specs)

    async def perform(self, send_task_messages: bool = True) -> None:
        """Calculate specified value using data previously read from device."""
        LOGGER.info("performing task %s", self.spec_id)
        # TODO Handle timeouts and recover from them gracefully
        calculated_value = str(self.value.calculate(self.device))
        LOGGER.debug(
            "task %s: publishing to MQTT topic %s payload: %s",
            self.spec_id,
            self.mqtt_topic,
            calculated_value,
        )
        if send_task_messages:
            self.mqtt_broker.publish(self.mqtt_topic, calculated_value)
        else:
            LOGGER.warning(
                "task %s: NOT publishing message to MQTT broker",
                self.spec_id,
            )
