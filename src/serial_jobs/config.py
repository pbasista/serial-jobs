"""Functions related to configuration."""
from json import dumps, loads
from logging import getLogger
from os.path import isfile

from strictyaml import load

from .schema import schema

DEFAULT_CONFIG_PATH = "./configuration.yaml"
DEFAULT_JSON_CONFIG_PATH = DEFAULT_CONFIG_PATH.rsplit(".", maxsplit=1)[0] + ".json"
LOGGER = getLogger(__name__)


def load_configuration(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Return the parsed configuration from file at the provided path."""
    LOGGER.info("loading configuration file %s", path)

    with open(path, encoding="utf-8") as input_file:
        content = input_file.read()

    if path.lower().endswith(".json"):
        configuration = loads(content)
    elif path.lower().endswith(".yaml"):
        yaml_configuration = load(content, schema)
        configuration = yaml_configuration.data
    else:
        raise ValueError("unsupported configuration file type")

    LOGGER.info("configuration file loaded")

    return configuration


def convert_configuration(
    configuration: dict, path: str = DEFAULT_JSON_CONFIG_PATH
) -> None:
    if isfile(path):
        answer = input(f"Overwrite configuration file {path}? (y/n)")
        if answer.lower() != "y":
            LOGGER.warning("NOT overwriting configuration file %s", path)
            return

    LOGGER.info("writing configuration to file %s", path)
    with open(path, mode="w", encoding="utf-8") as output_file:
        output_file.write(dumps(configuration))
