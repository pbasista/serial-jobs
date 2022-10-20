"""Functions related to YAML schema used for validating the configuration."""
from re import compile as re_compile

from strictyaml import (
    Any,
    Bool,
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

from .data import Data


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

writable_block_schema = Map(
    {
        "start_address": HexInt(),
        "stop_address": HexInt(),
    }
)

register_schema = Map(
    {
        Optional("register_type", default="default"): Enum(
            ("default", "coil", "discrete", "holding", "input")
        ),
        Optional("writable_block"): writable_block_schema,
        Optional("register_count", default=1): Int(),
        "address": HexInt(),
        Optional("byte_order"): Seq(Int()),
        Optional("byte_offset"): Int(),
        Optional("byte_count"): Int(),
        Optional("byte_index"): Int(),  # if defined, overrides offset and count
        Optional("bitmask"): BinInt(),
        Optional("bitshift"): Int(),  # if positive, shift to the right
        Optional("increase_by"): Int(),
        Optional("scale_factor"): Int(),
    }
)

data_part_schema = MapPattern(
    Enum(list(Data.format_strings.keys()) + ["string"]),
    register_schema,
    minimum_keys=1,
    maximum_keys=1,
)

data_schema = Seq(data_part_schema)

value_schema = Map(
    {
        Optional("type"): Enum(("float", "int", "str", "date", "datetime", "time")),
        Optional("mapping"): MapPattern(Str(), Str()),
        "data": data_schema,
    }
)

task_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        Optional("device"): Str(),
        Optional("mqtt_broker"): Str(),
        "mqtt_topic": Str(),
        "value": value_schema,
    }
)

tasks_schema = Seq(task_schema)

job_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        Optional("enabled"): Bool(),
        Optional("mqtt_broker"): Str(),
        Optional("mqtt_messages"): Seq(MapPattern(Str(), MapPattern(Str(), Any()))),
        "sleep": Int(),
        "tasks": UniqueSeq(Str()),
    }
)

jobs_schema = Seq(job_schema)

input_value_schema = Map(
    {
        Optional("mapping"): MapPattern(Str(), Str()),
        Optional("type"): Enum(("float", "int", "str")),
        "data": data_schema,
    }
)

handler_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        Optional("device"): Str(),
        "mqtt_topic": Str(),
        "value": input_value_schema,
    }
)

handlers_schema = Seq(handler_schema)

service_schema = Map(
    {
        "id": Str(),
        Optional("name"): Str(),
        Optional("enabled"): Bool(),
        Optional("mqtt_broker"): Str(),
        Optional("mqtt_messages"): Seq(MapPattern(Str(), MapPattern(Str(), Any()))),
        "handlers": UniqueSeq(Str()),
    }
)

services_schema = Seq(service_schema)

configuration_stub_schema = Map(
    {
        Optional("mqtt_brokers"): mqtt_brokers_schema,
        Optional("devices"): devices_schema,
        Optional("tasks"): tasks_schema,
        Optional("jobs"): jobs_schema,
        Optional("handlers"): handlers_schema,
        Optional("services"): services_schema,
    }
)

configuration_schema = Map(
    {
        "mqtt_brokers": mqtt_brokers_schema,
        "devices": devices_schema,
        "tasks": tasks_schema,
        "jobs": jobs_schema,
        "handlers": handlers_schema,
        "services": services_schema,
    }
)
