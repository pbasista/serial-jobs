#!/usr/bin/env python
from argparse import ArgumentParser, Namespace
from logging import getLevelName

from strictyaml import YAML

from serial_jobs import (
    DEFAULT_CONFIG_PATH,
    LOGGING_LEVELS,
    configuration_schema,
    configure_logging,
    load_stub_configuration,
    merge_configurations,
    save_yaml_configuration,
)


def parse_arguments() -> Namespace:
    parser = ArgumentParser(
        description="Merge the provided YAML configuration files into one."
    )
    # pylint: disable-next=duplicate-code
    parser.add_argument(
        "--logging-level",
        default="DEBUG",
        choices=LOGGING_LEVELS.keys(),
        help="logging level (default: %(default)s)",
    )
    parser.add_argument(
        "--output-config-path",
        default=DEFAULT_CONFIG_PATH,
        help="path to the output YAML configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "input_config_path",
        nargs="+",
        help="path to input YAML configuration file",
    )

    return parser.parse_args()


def merge_configs() -> None:
    namespace = parse_arguments()
    logging_level = getLevelName(namespace.logging_level)
    configure_logging(logging_level)

    input_config_path_iterator = iter(namespace.input_config_path)
    first_input_config_path = next(input_config_path_iterator)

    yaml_configuration = load_stub_configuration(first_input_config_path).as_marked_up()

    for input_config_path in input_config_path_iterator:
        stub_configuration = load_stub_configuration(input_config_path).as_marked_up()
        yaml_configuration = merge_configurations(
            stub_configuration, yaml_configuration
        )

    yaml_configuration = YAML(yaml_configuration)
    yaml_configuration.revalidate(configuration_schema)

    save_yaml_configuration(yaml_configuration, namespace.output_config_path)


if __name__ == "__main__":
    merge_configs()
