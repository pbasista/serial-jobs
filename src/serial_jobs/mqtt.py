"""Functionality related to MQTT clients."""
from __future__ import annotations

from asyncio import Lock
from dataclasses import dataclass
from logging import getLogger
from typing import ClassVar

from gmqtt import Client
from gmqtt.mqtt.constants import MQTTv311

from .specification import SpecMixin

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class MQTTBroker(SpecMixin):
    specs_by_id: ClassVar[dict[str, dict]] = {}
    clients_by_id: ClassVar[dict[str, Client]] = {}
    lock: ClassVar[Lock] = Lock()

    host: str
    port: int
    client: Client

    @classmethod
    def from_spec(cls, spec: dict) -> MQTTBroker:
        broker_id = spec["id"]
        name = spec.get("name")
        host = spec["host"]
        port = spec["port"]
        if broker_id in cls.clients_by_id:
            client = cls.clients_by_id[broker_id]
        else:
            client = Client(broker_id)
            cls.clients_by_id[broker_id] = client
        client.set_auth_credentials(spec["username"], spec["password"])

        return cls(spec_id=broker_id, name=name, host=host, port=port, client=client)

    async def connect(self) -> None:
        async with self.lock:
            if self.client.is_connected:
                LOGGER.debug("mqtt_broker %s: already connected", self.spec_id)
            else:
                LOGGER.info("mqtt_broker %s: connecting", self.spec_id)
                await self.client.connect(self.host, self.port, version=MQTTv311)
                LOGGER.info("mqtt_broker %s: connected", self.spec_id)

    def publish(self, topic: str, value: str, retain: bool = False) -> None:
        self.client.publish(topic, value, retain=retain)
