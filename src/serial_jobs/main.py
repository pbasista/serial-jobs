"""Functionality related to the main entry point."""
from asyncio import gather
from logging import INFO, Logger, basicConfig, getLogger

from .config import DEFAULT_CONFIG_PATH, load_configuration
from .device import Device
from .job import Job
from .mqtt import MQTTBroker
from .task import Task

# copied over from logging._nameToLevel
# because the mentioned variable is marked as private
LOGGING_LEVELS = {
    "CRITICAL": 50,
    "FATAL": 50,
    "ERROR": 40,
    "WARN": 30,
    "WARNING": 30,
    "INFO": 20,
    "DEBUG": 10,
    "NOTSET": 0,
}


def configure_logging(level=INFO) -> Logger:
    color_reset = "\x1b[0m"
    cyan = "\x1b[36;20m"
    gray = "\x1b[37;20m"
    logger_format = (
        f"{gray}%(asctime)s{color_reset} "
        f"{cyan}%(levelname)7s{color_reset} "
        f"{gray}%(name)s{color_reset} %(message)s"
    )
    basicConfig(format=logger_format, level=level, force=True)
    return getLogger(__name__)


async def work(
    configuration_path: str = DEFAULT_CONFIG_PATH,
    logging_level: int = INFO,
    keep_going: bool = False,
    send_initial_messages: bool = True,
    send_task_messages: bool = True,
) -> None:
    """Dispatch configured jobs at configured intervals."""
    logger = configure_logging(logging_level)
    config = load_configuration(configuration_path)

    logger.debug("loading specifications")
    MQTTBroker.load_specifications(config["mqtt_brokers"])
    Device.load_specifications(config["devices"])
    Task.load_specifications(config["tasks"])
    Job.load_specifications(config["jobs"])
    logger.debug("specifications loaded")

    awaitable_jobs = [
        job.carry_out(keep_going, send_initial_messages, send_task_messages)
        for job in Job.from_all_specs()
    ]
    logger.info("carrying out %d jobs", len(awaitable_jobs))
    await gather(*awaitable_jobs)
