#!/usr/bin/env python
from argparse import ArgumentParser, Namespace
from logging import getLevelName

from serial_jobs import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_JSON_CONFIG_PATH,
    LOGGING_LEVELS,
    configure_logging,
    convert_configuration,
    load_configuration,
)


def parse_arguments() -> Namespace:
    parser = ArgumentParser(
        description="Validate YAML configuration and convert it to JSON format."
    )
    parser.add_argument(
        "--yaml-config-path",
        default=DEFAULT_CONFIG_PATH,
        help="path to the input YAML configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "--json-config-path",
        default=DEFAULT_JSON_CONFIG_PATH,
        help="path to the output JSON configuration file (default: %(default)s)",
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

    configuration = load_configuration(namespace.yaml_config_path)
    convert_configuration(configuration, namespace.json_config_path)


if __name__ == "__main__":
    validate_and_convert()
