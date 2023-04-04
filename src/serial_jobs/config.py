"""Functions related to configuration."""
from json import dumps, loads
from logging import getLogger
from os.path import isfile

from strictyaml import YAML, as_document, load
from strictyaml.ruamel.comments import CommentedMap

from .schema import configuration_schema, configuration_stub_schema

DEFAULT_CONFIG_PATH = "./configuration.json"
DEFAULT_JSON_CONFIG_PATH = DEFAULT_CONFIG_PATH.rsplit(".", maxsplit=1)[0] + ".json"
LOGGER = getLogger(__name__)


def merge_configurations(
    input_one: CommentedMap, input_two: CommentedMap
) -> CommentedMap:
    """Merge top-level mappings of two provided YAML objects.

    Return the combined result.
    """
    for toplevel_key, toplevel_value in input_one.items():
        if toplevel_key in input_two:
            input_two[toplevel_key].extend(toplevel_value)
        else:
            input_two[toplevel_key] = toplevel_value

    return input_two


def load_stub_configuration(path) -> YAML:
    LOGGER.info("loading stub configuration file %s", path)

    with open(path, encoding="utf-8") as input_file:
        content = input_file.read()

    return load(content, configuration_stub_schema)


def load_configuration(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Return the parsed configuration from file at the provided path.

    If the provided path represents a YAML file,
    also validate its content against the defined schema.
    """
    LOGGER.info("loading configuration file %s", path)

    with open(path, encoding="utf-8") as input_file:
        content = input_file.read()

    if path.lower().endswith(".json"):
        configuration = loads(content)
    elif path.lower().endswith(".yaml"):
        yaml_configuration = load(content, configuration_schema)
        configuration = yaml_configuration.data
    else:
        raise ValueError("unsupported configuration file type")

    LOGGER.info("configuration file loaded")

    return configuration


def save_configuration(
    configuration: dict, path: str = DEFAULT_JSON_CONFIG_PATH
) -> None:
    """Save provided configuration to file at the provided path."""
    if isfile(path):
        answer = input(f"Overwrite configuration file {path}? (y/n) ")
        if answer.lower() != "y":
            LOGGER.warning("NOT overwriting configuration file %s", path)
            return

    if path.lower().endswith(".json"):
        serialized_configuration = dumps(configuration)
    elif path.lower().endswith(".yaml"):
        serialized_configuration = as_document(
            configuration, configuration_schema
        ).as_yaml()
    else:
        raise ValueError("unsupported configuration file type")

    LOGGER.info("saving configuration to file %s", path)

    with open(path, mode="w", encoding="utf-8") as output_file:
        output_file.write(serialized_configuration)

    LOGGER.info("configuration file saved")


def save_yaml_configuration(
    configuration: YAML, path: str = DEFAULT_JSON_CONFIG_PATH
) -> None:
    """Save provided YAML configuration to file at the provided path."""
    if isfile(path):
        answer = input(f"Overwrite configuration file {path}? (y/n) ")
        if answer.lower() != "y":
            LOGGER.warning("NOT overwriting configuration file %s", path)
            return

    LOGGER.info("saving configuration to file %s", path)

    with open(path, mode="w", encoding="utf-8") as output_file:
        output_file.write(configuration.as_yaml())

    LOGGER.info("configuration file saved")
