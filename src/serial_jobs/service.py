"""Functionality related to providing services."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from json import dumps
from logging import getLogger
from typing import ClassVar

from .handler import Handler
from .mqtt import Client, MQTTBroker, MQTTMessage
from .specification import SpecMixin

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class Service(SpecMixin):
    specs_by_id: ClassVar[dict[str, dict]] = {}

    mqtt_broker: MQTTBroker
    mqtt_messages: list[MQTTMessage]
    is_enabled: bool
    handlers: dict[str, list[Handler]]

    @classmethod
    def from_spec(cls, spec: dict) -> Service:
        service_id = spec["id"]
        name = spec.get("name")
        mqtt_broker_id = spec.get("mqtt_broker", MQTTBroker.default_id())
        mqtt_broker = MQTTBroker.from_id(mqtt_broker_id)
        mqtt_messages_spec = spec.get("mqtt_messages", [])
        mqtt_messages = [
            MQTTMessage.from_spec(mqtt_message_spec)
            for mqtt_message_spec in mqtt_messages_spec
        ]
        is_enabled = spec.get("enabled", True)
        handler_ids = spec["handlers"]
        handlers = defaultdict(list)
        for handler_id in handler_ids:
            handler = Handler.from_id(handler_id)
            handlers[handler.mqtt_topic].append(handler)
        return cls(
            spec_id=service_id,
            name=name,
            mqtt_broker=mqtt_broker,
            mqtt_messages=mqtt_messages,
            is_enabled=is_enabled,
            handlers=handlers,
        )

    async def connect_to_mqtt(self) -> None:
        """Connecto to the configured MQTT broker."""
        LOGGER.info("service %s: connecting to configured MQTT broker", self.spec_id)
        await self.mqtt_broker.connect()

    async def send_messages(self) -> None:
        """Send the configured MQTT messages to the configured MQTT broker."""
        if not self.mqtt_messages:
            LOGGER.warning(
                "service %s: no initial MQTT message configured",
                self.spec_id,
            )
            return

        LOGGER.info(
            "service %s: sending %d initial messages to MQTT broker %s",
            self.spec_id,
            len(self.mqtt_messages),
            self.mqtt_broker.spec_id,
        )

        for mqtt_message in self.mqtt_messages:
            payload = dumps(mqtt_message.payload)
            LOGGER.debug(
                "service %s: publishing to MQTT topic %s payload:\n%s",
                self.spec_id,
                mqtt_message.topic,
                payload,
            )
            await self.mqtt_broker.publish(mqtt_message.topic, payload, retain=True)

    async def subscribe_to_mqtt(
        self, keep_going: bool = False, write_to_device: bool = True
    ):
        handler = partial(self.dispatch_handlers, keep_going, write_to_device)
        await self.mqtt_broker.subscribe(list(self.handlers.keys()), handler)

    async def dispatch_handlers(
        self,
        keep_going: bool,
        write_to_device: bool,
        _client: Client,
        topic: str,
        payload: bytes,
        _qos: int,
        _properties: dict,
    ):
        if topic in self.handlers:
            LOGGER.info(
                "service %s: dispatching %d handlers for topic %s",
                self.spec_id,
                len(self.handlers[topic]),
                topic,
            )
            for handler in self.handlers[topic]:
                try:
                    await handler.handle(payload.decode("utf-8"), write_to_device)
                # pylint: disable-next=broad-except
                except Exception as exc:
                    LOGGER.debug(
                        "handler %s: exception",
                        handler.spec_id,
                        exc_info=True,
                        stack_info=True,
                    )
                    if keep_going:
                        LOGGER.warning(
                            "handler %s: encountered exception: %s",
                            handler.spec_id,
                            exc,
                        )
                    else:
                        LOGGER.error(
                            "handler %s: stopped due to exception: %s",
                            handler.spec_id,
                            exc,
                        )
                        raise
        else:
            raise RuntimeError(f"no handler for topic {topic}")

    async def provide(
        self,
        keep_going: bool = False,
        write_to_device: bool = True,
        send_initial_messages: bool = True,
    ) -> None:
        """Subscribe to configured MQTT topics and handle the messages."""
        if not self.is_enabled:
            LOGGER.warning("service %s: skipped because it is disabled", self.spec_id)
            return

        LOGGER.info("service %s: started", self.spec_id)

        await self.connect_to_mqtt()

        if send_initial_messages:
            await self.send_messages()
        else:
            LOGGER.warning(
                "service %s: NOT sending initial MQTT messages", self.spec_id
            )

        await self.subscribe_to_mqtt(keep_going, write_to_device)
