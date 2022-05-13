"""Functionality related to carrying out jobs."""
from __future__ import annotations

from asyncio import sleep
from dataclasses import dataclass, field
from json import dumps
from logging import getLogger
from typing import ClassVar

from .mqtt import MQTTBroker
from .specification import SpecMixin
from .task import Task

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
class Job(SpecMixin):
    specs_by_id: ClassVar[dict[str, dict]] = {}

    mqtt_broker: MQTTBroker
    mqtt_messages: list[MQTTMessage]
    sleep_timeout: float
    is_enabled: bool
    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_spec(cls, spec: dict) -> Job:
        job_id = spec["id"]
        name = spec.get("name")
        mqtt_broker_id = spec.get("mqtt_broker", MQTTBroker.default_id())
        mqtt_broker = MQTTBroker.from_id(mqtt_broker_id)
        mqtt_messages_spec = spec.get("mqtt_messages", [])
        mqtt_messages = [
            MQTTMessage.from_spec(mqtt_message_spec)
            for mqtt_message_spec in mqtt_messages_spec
        ]
        sleep_timeout = spec["sleep"]
        is_enabled = spec.get("enabled", True)
        task_ids = spec["tasks"]
        tasks = []
        for task_id in task_ids:
            tasks.append(Task.from_id(task_id))
        return cls(
            spec_id=job_id,
            name=name,
            mqtt_broker=mqtt_broker,
            mqtt_messages=mqtt_messages,
            sleep_timeout=sleep_timeout,
            is_enabled=is_enabled,
            tasks=tasks,
        )

    async def clear_data(self) -> int:
        """Clear the data for all the configured tasks.

        Return the number of registers cleared.
        """
        registers_cleared = 0
        for task in self.tasks:
            registers_cleared += task.clear_data()

        LOGGER.debug(
            "job %s: cleared %d cached device registers",
            self.spec_id,
            registers_cleared,
        )
        return registers_cleared

    async def fetch_data(self) -> int:
        """Fetch the data for all the configured tasks.

        Return the number of bytes read.
        """
        bytes_read = 0
        for task in self.tasks:
            bytes_read += task.fetch_data()

        LOGGER.debug(
            "job %s: fetched %d bytes of data from the devices",
            self.spec_id,
            bytes_read,
        )
        return bytes_read

    async def connect_to_mqtt(self) -> None:
        """Connecto to the MQTT brokers used by the configured tasks."""
        mqtt_brokers = [task.mqtt_broker for task in self.tasks]
        LOGGER.info(
            "job %s: connecting to the configured MQTT brokers",
            self.spec_id,
        )
        for mqtt_broker in mqtt_brokers:
            await mqtt_broker.connect()

    async def send_messages(self) -> None:
        """Send the configured MQTT messages to the configured MQTT broker."""
        if not self.mqtt_messages:
            LOGGER.warning(
                "job %s: no initial MQTT message configured",
                self.spec_id,
            )
            return

        LOGGER.info(
            "job %s: sending %d initial messages to MQTT broker %s",
            self.spec_id,
            len(self.mqtt_messages),
            self.mqtt_broker.spec_id,
        )

        for mqtt_message in self.mqtt_messages:
            payload = dumps(mqtt_message.payload)
            LOGGER.debug(
                "job %s: publishing to MQTT topic %s payload:\n%s",
                self.spec_id,
                mqtt_message.topic,
                payload,
            )
            self.mqtt_broker.publish(mqtt_message.topic, payload, retain=True)

    async def perform_tasks(self, send_task_messages: bool = True) -> None:
        """Perform all the configured tasks."""
        await self.clear_data()
        await self.fetch_data()
        for task in self.tasks:
            await task.perform(send_task_messages)

    async def carry_out(
        self,
        keep_going: bool = False,
        send_initial_messages: bool = True,
        send_task_messages: bool = True,
    ) -> None:
        """Carry out all the tasks of this job in a loop indefinitely."""
        if not self.is_enabled:
            LOGGER.warning("job %s: skipped because it is disabled", self.spec_id)
            return

        LOGGER.info("job %s: started", self.spec_id)

        if send_initial_messages or send_task_messages:
            await self.connect_to_mqtt()

        if send_initial_messages:
            await self.send_messages()
        else:
            LOGGER.warning(
                "job %s: NOT sending initial MQTT messages",
                self.spec_id,
            )

        while True:
            try:
                await self.perform_tasks(send_task_messages)
            # pylint: disable-next=broad-except
            except Exception as exc:
                LOGGER.debug(
                    "job %s: exception",
                    self.spec_id,
                    exc_info=True,
                    stack_info=True,
                )
                if keep_going:
                    LOGGER.warning(
                        "job %s: encountered exception: %s",
                        self.spec_id,
                        exc,
                    )
                else:
                    LOGGER.error(
                        "job %s: stopped due to exception: %s",
                        self.spec_id,
                        exc,
                    )
                    break

            LOGGER.info(
                "job %s: sleeping for %d seconds", self.spec_id, self.sleep_timeout
            )
            await sleep(self.sleep_timeout)
