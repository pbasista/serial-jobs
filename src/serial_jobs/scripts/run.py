#!/usr/bin/env python
from argparse import ArgumentParser, Namespace
from asyncio import run
from logging import getLevelName

from serial_jobs import DEFAULT_CONFIG_PATH, LOGGING_LEVELS, work


def parse_arguments() -> Namespace:
    parser = ArgumentParser(description="Run Serial Jobs")
    parser.add_argument(
        "--config-path",
        default=DEFAULT_CONFIG_PATH,
        help="path to the YAML or JSON configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "--logging-level",
        default="INFO",
        choices=LOGGING_LEVELS.keys(),
        help="logging level (default: %(default)s)",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="keep carrying out a job or providing a service after exception",
    )
    parser.add_argument(
        "--no-handler-writes",
        action="store_false",
        dest="write_to_device",
        help="do not write to any device registers from within handlers",
    )
    parser.add_argument(
        "--no-initial-messages",
        action="store_false",
        dest="send_initial_messages",
        help="do not send initial messages to MQTT broker",
    )
    parser.add_argument(
        "--no-task-messages",
        action="store_false",
        dest="send_task_messages",
        help="do not send messages to MQTT broker from individual tasks",
    )

    return parser.parse_args()


def do_work():
    namespace = parse_arguments()
    run(
        work(
            namespace.config_path,
            getLevelName(namespace.logging_level),
            namespace.keep_going,
            namespace.write_to_device,
            namespace.send_initial_messages,
            namespace.send_task_messages,
        )
    )


if __name__ == "__main__":
    do_work()
