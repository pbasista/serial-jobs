"""Functions related to performing tasks."""
from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger

from .base import CachedInstance
from .device import Device
from .mqtt import MQTTBroker
from .value import Value

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class Task(CachedInstance):
    name: str | None
    mqtt_topic: str
    mqtt_broker: MQTTBroker
    device: Device
    value: Value

    @classmethod
    def from_config(cls, task_config: dict) -> Task:
        task_id = task_config["id"]
        name = task_config.get("name")
        mqtt_topic = task_config["mqtt_topic"]
        mqtt_broker_id = task_config.get("mqtt_broker")
        mqtt_broker = MQTTBroker.get_by_id(mqtt_broker_id)
        device_id = task_config.get("device")
        device = Device.get_by_id(device_id)
        value_config = task_config["value"]
        value = Value.from_config(value_config)
        device = Device.get_by_id(device_id)
        return cls(
            instance_id=task_id,
            name=name,
            mqtt_topic=mqtt_topic,
            mqtt_broker=mqtt_broker,
            device=device,
            value=value,
        )

    async def perform(self) -> None:
        LOGGER.info("performing task %s", self.instance_id)
        value = self.value.get(self.device)
        LOGGER.debug(
            "task %s: publishing to MQTT topic %s payload %s",
            self.instance_id,
            self.mqtt_topic,
            value,
        )
        self.mqtt_broker.client.publish(self.mqtt_topic, value)
