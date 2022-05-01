"""Functions related to MQTT clients."""
from __future__ import annotations

from dataclasses import dataclass

from gmqtt import Client
from gmqtt.mqtt.constants import MQTTv311

from .base import CachedInstance


@dataclass(frozen=True)
class MQTTBroker(CachedInstance):
    name: str | None
    client: Client

    @classmethod
    async def from_config(cls, mqtt_config: dict) -> MQTTBroker:
        broker_id = mqtt_config["id"]
        name = mqtt_config.get("name")
        client = await get_client(
            broker_id,
            mqtt_config["host"],
            mqtt_config["port"],
            mqtt_config["username"],
            mqtt_config["password"],
        )
        return cls(instance_id=broker_id, name=name, client=client)


async def get_client(
    client_id: str, host: str, port: int, username: str, password: str
) -> Client:
    """Return MQTT client connected to the specified broker."""
    client = Client(client_id)
    client.set_auth_credentials(username, password)
    await client.connect(host, port, version=MQTTv311)
    return client
