"""Functions related to the main entry point."""
from asyncio import gather
from logging import DEBUG, basicConfig, getLogger

from .config import load_configuration
from .device import get_device
from .job import Job
from .mqtt import MQTTBroker
from .task import Task

COLOR_RESET = "\x1b[0m"
CYAN = "\x1b[36;20m"
GRAY = "\x1b[37;20m"
LOGGER_FORMAT = (
    f"{GRAY}%(asctime)s{COLOR_RESET} "
    f"{CYAN}%(levelname)7s{COLOR_RESET} "
    f"{GRAY}%(name)s{COLOR_RESET} %(message)s"
)
basicConfig(format=LOGGER_FORMAT, level=DEBUG)
LOGGER = getLogger(__name__)


async def work() -> None:
    """Dispatch configured jobs at configured intervals."""
    config = load_configuration()

    mqtt_brokers = {}
    for mqtt_config in config["mqtt_brokers"]:
        mqtt_broker = await MQTTBroker.from_config(mqtt_config.data)
        mqtt_brokers[mqtt_broker.instance_id] = mqtt_broker

    devices = {}
    for device_config in config["devices"]:
        device = get_device(device_config.data)
        devices[device.instance_id] = device

    tasks = {}
    for task_config in config["tasks"]:
        task = Task.from_config(task_config.data)
        tasks[task.instance_id] = task

    jobs = {}
    for job_config in config["jobs"]:
        job = Job.from_config(job_config.data)
        jobs[job.instance_id] = job

    awaitable_jobs = [job.carry_out() for job in jobs.values()]
    LOGGER.info("carrying out %d jobs", len(awaitable_jobs))
    await gather(*awaitable_jobs)
