"""Functions related to YAML schema used for validating the configuration."""
from re import compile as re_compile

from strictyaml import (
    Enum,
    Float,
    HexInt,
    Int,
    Map,
    MapPattern,
    Optional,
    ScalarValidator,
    Seq,
    Str,
    UniqueSeq,
)


class YAMLSerializationError(ValueError):
    ...


def is_binary(value: str) -> bool:
    """Return true if the provided value is a string of a binary integer."""
    return re_compile(r"^0[bB]+[01]+$").match(value) is not None


class BinInt(ScalarValidator):
    def validate_scalar(self, chunk):
        val = chunk.contents
        if not is_binary(val):
            chunk.expecting_but_found("when expecting a binary integer")
        return int(val, 2)

    @staticmethod
    def to_yaml(data):
        if is_binary(data):
            if isinstance(data, int):
                return bin(data)
            return data
        raise YAMLSerializationError(f"'{data}' is not a binary integer.")


mqtt_broker_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        "host": Str(),
        "port": Int(),
        "username": Str(),
        "password": Str(),
    }
)

mqtt_brokers_schema = Seq(mqtt_broker_schema)

serial_schema = Map(
    {
        "port": Str(),
        "baud_rate": Int(),
        "data_bits": Int(),
        "stop_bits": Float(),
        "parity": Enum(("N", "E", "O", "M", "S")),
        "timeout": Float(),
    }
)

protocol_schema = Map(
    {
        Optional("modbus_address"): HexInt(),
    }
)

device_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        Optional("type", default="ModbusDevice"): Str(),
        "serial": serial_schema,
        Optional("protocol"): protocol_schema,
    }
)

devices_schema = Seq(device_schema)

coil_schema = Map(
    {
        "address": HexInt(),
    }
)

register_byte_schema = Map(
    {
        "address": HexInt(),
        Optional("byte_index"): Int(),
        Optional("bitmask"): BinInt(),
        Optional("bitrightshift"): Int(),
    }
)

register_schema = Map(
    {
        "address": HexInt(),
        Optional("bitmask"): BinInt(),
        Optional("bitrightshift"): Int(),
    }
)

data_part_schema = Map(
    {
        Optional("discrete_input"): coil_schema,
        Optional("coil"): coil_schema,
        Optional("register_byte"): register_byte_schema,
        Optional("input_register_byte"): register_byte_schema,
        Optional("register"): register_schema,
        Optional("input_register"): register_schema,
    }
)

data_schema = Seq(data_part_schema)

value_schema = Map(
    {
        Optional("type"): Str(),
        Optional("mapping"): MapPattern(Int(), Str()),
        Optional("scale_factor"): Int(),
        "data": data_schema,
    }
)

task_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        Optional("device"): Str(),
        "mqtt_topic": Str(),
        Optional("mqtt_broker"): Str(),
        "value": value_schema,
    }
)

tasks_schema = Seq(task_schema)

job_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        "sleep": Int(),
        "tasks": UniqueSeq(Str()),
    }
)

jobs_schema = Seq(job_schema)

schema = Map(
    {
        "mqtt_brokers": mqtt_brokers_schema,
        "devices": devices_schema,
        "tasks": tasks_schema,
        "jobs": jobs_schema,
    }
)
