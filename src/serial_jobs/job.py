"""Functions related to carrying out jobs."""
from __future__ import annotations

from asyncio import sleep
from dataclasses import dataclass, field
from logging import getLogger

from .base import CachedInstance
from .task import Task

LOGGER = getLogger(__name__)


@dataclass(frozen=True)
class Job(CachedInstance):
    name: str | None
    sleep_timeout: float
    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_config(cls, job_config: dict) -> Job:
        job_id = job_config["id"]
        name = job_config.get("name")
        sleep_timeout = job_config["sleep"]
        task_ids = job_config["tasks"]
        tasks = []
        for task_id in task_ids:
            tasks.append(Task.get_by_id(task_id))
        return cls(
            instance_id=job_id, name=name, sleep_timeout=sleep_timeout, tasks=tasks
        )

    async def carry_out(self) -> None:
        LOGGER.info("carrying out job %s", self.instance_id)
        while True:
            for task in self.tasks:
                await task.perform()
            LOGGER.debug(
                "job %s: sleeping for %d seconds", self.instance_id, self.sleep_timeout
            )
            await sleep(self.sleep_timeout)
