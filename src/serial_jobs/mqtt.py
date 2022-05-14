"""Functionality related to MQTT clients."""
from __future__ import annotations

from asyncio import Lock
from dataclasses import dataclass, field
from functools import partial
from logging import getLogger
from typing import ClassVar, Optional

from gmqtt import Client
from gmqtt.mqtt.constants import MQTTv311

from .specification import SpecMixin

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class MQTTMessage:
    topic: str
    payload: dict

    @classmethod
    def from_spec(cls, spec: dict) -> MQTTMessage:
        topic, payload = next(iter(spec.items()))
        return cls(topic, payload)


@dataclass(frozen=True)
class MQTTClient:
    cache: ClassVar[dict[str, MQTTClient]] = {}

    client_id: str
    host: str
    port: int
    username: str
    password: str
    lock: Lock = field(default_factory=Lock, init=False)
    client: Client = field(default_factory=partial(Client, None), init=False)

    @classmethod
    def get_by_id(cls, client_id: str) -> Optional[MQTTClient]:
        return cls.cache.get(client_id)

    def __post_init__(self) -> None:
        self.cache[self.client_id] = self
        self.client.set_auth_credentials(self.username, self.password)

    async def connect(self) -> None:
        async with self.lock:
            if self.client.is_connected:
                LOGGER.warning("mqtt_client %s: already connected", self.client_id)
                return
            LOGGER.debug("mqtt_client %s: connecting", self.client_id)
            await self.client.connect(self.host, self.port, version=MQTTv311)
            LOGGER.debug("mqtt_client %s: connected", self.client_id)

    async def publish(self, topic: str, value: str, retain: bool = False) -> None:
        async with self.lock:
            self.client.publish(topic, value, retain=retain)


@dataclass(frozen=True)
class MQTTBroker(SpecMixin):
    specs_by_id: ClassVar[dict[str, dict]] = {}
    lock: ClassVar[Lock] = Lock()

    host: str
    port: int
    mqtt_client: MQTTClient

    @classmethod
    def from_spec(cls, spec: dict) -> MQTTBroker:
        broker_id = spec["id"]
        name = spec.get("name")
        host = spec["host"]
        port = spec["port"]
        mqtt_client = MQTTClient.get_by_id(broker_id)
        if mqtt_client is None:
            mqtt_client = MQTTClient(
                broker_id, host, port, spec["username"], spec["password"]
            )

        return cls(
            spec_id=broker_id, name=name, host=host, port=port, mqtt_client=mqtt_client
        )

    async def connect(self) -> None:
        await self.mqtt_client.connect()

    async def publish(self, topic: str, value: str, retain: bool = False) -> None:
        await self.mqtt_client.publish(topic, value, retain=retain)
