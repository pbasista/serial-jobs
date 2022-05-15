#!/usr/bin/env python
from argparse import ArgumentParser, Namespace
from logging import getLevelName

from serial_jobs import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_JSON_CONFIG_PATH,
    LOGGING_LEVELS,
    configure_logging,
    load_configuration,
    save_configuration,
)


def parse_arguments() -> Namespace:
    parser = ArgumentParser(
        description=(
            "Load configuration from file and save it to different file. "
            "Optionally convert between YAML and JSON formats."
        )
    )
    parser.add_argument(
        "--input-config-path",
        default=DEFAULT_CONFIG_PATH,
        help="path to the input configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "--output-config-path",
        default=DEFAULT_JSON_CONFIG_PATH,
        help="path to the output configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "--logging-level",
        default="DEBUG",
        choices=LOGGING_LEVELS.keys(),
        help="logging level (default: %(default)s)",
    )

    return parser.parse_args()


def validate_and_convert() -> None:
    namespace = parse_arguments()
    logging_level = getLevelName(namespace.logging_level)
    configure_logging(logging_level)

    configuration = load_configuration(namespace.input_config_path)
    save_configuration(configuration, namespace.output_config_path)


if __name__ == "__main__":
    validate_and_convert()
