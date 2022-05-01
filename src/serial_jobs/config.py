"""Functions related to configuration."""
from strictyaml import YAML, load

from .schema import schema


def load_configuration(path: str = "./configuration.yaml") -> YAML:
    """Return the parsed configuration from file at the provided path."""
    with open(path, encoding="utf-8") as input_file:
        content = input_file.read()

    return load(content, schema)
