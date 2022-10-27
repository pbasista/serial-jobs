# Serial Jobs

A tool for bidirectional communication between serial devices and MQTT brokers.

## Overview

* Configured serial devices are periodically polled for data.
* The obtained values are then sent to the configured MQTT brokers.
* Subscribtions to the configured MQTT topics are created.
* The configured handlers are run when a matching MQTT message is received.

## Features

This section summarizes the main features of this application.

* Reading and writing data via [Modbus](https://modbus.org/specs.php) protocol.
* Possibility to define and use custom protocols.
* Sending custom initialization MQTT messages on startup. [^1]
* Configuration files in YAML or JSON format.

[^1]: The initialization MQTT messages can be used
to automatically configure the consumers of the value-carrying MQTT messages
like [Home Assistant](https://www.home-assistant.io/)
to handle them appropriately.

## Terminology

This section explains the terminology used within the configuration files and source code.

### Common

1. An _mqtt_broker_ configuration object specifies how to communicate with an MQTT broker.
1. A _device_ configuration object specifies how to communicate with a serial device.
1. A _data_ configuration object specifies how to map raw bytes from _device_ to simple data parts.
1. A _value_ configuration object specifies how to map simple _data_ parts obtained from _device_ to a serializable value that can be used when communicating with an MQTT broker.

### Reading from devices

1. A _task_ specifies how to retrieve a particular _value_ from a particular _device_ and also where and how to send it within an MQTT message.
1. A _job_ specifies how often to perform particular _tasks_.

### Writing to devices

1. A _handler_ specifies how to extract a particular _value_ from an incoming MQTT message with a particular MQTT topic and how to write it to a particular _device_.
1. A _service_ specifies which handlers to run upon receiving messages from a particular MQTT broker.

## Configuration

The application is configured via a configuration file.

### Configuration file

The configuration file can use either YAML or JSON format.
It consists of configuration objects described below.

### Configuration objects

Unless stated otherwise:

* fields within the defined configuration objects are mandatory
* fields which represent addresses of any kind must be specified as hexadecimal numbers

#### `mqtt_brokers`

A _sequence_ of MQTT broker specifications.
Each specification might contain fields defined below.

- `id`: Unique ID of the defined MQTT broker.

    It is used for referring to a particular MQTT broker within this configuration.

- `name`: _Optional_ human-readable name of the defined MQTT broker.

    It might be used to make the configuration file less ambiguous.

- `host`: Hostname of the defined MQTT broker.
- `port`: Port of the defined MQTT broker.
- `username`: Username for connecting to the defined MQTT broker.
- `password`: Password for the defined username.

#### `devices`

A _sequence_ of serial device specifications.
Each specification might contain fields defined below.

- `id`: Unique ID of the defined serial device.

    It is used for referring to a particular serial device within this configuration.

- `name`: _Optional_ human-readable name of the defined serial device.

    It might be used to make the configuration file less ambiguous.

- `type`: _Optional_ type of the defined serial device. Defaults to `ModbusDevice`. 

    Available values are:

    1. `ModbusDevice` for devices which communicate over the [Modbus](https://modbus.org/specs.php) protocol.
    1. `BMSDevice` for devices which communicate over a protocol that is used by the battery management systems from manufacturers such as [JBD](https://gitlab.com/bms-tools/bms-tools/-/blob/master/JBD_REGISTER_MAP.md/).

    It is possible to define custom device types by creating a subclass of `serial_jobs.device.Device` and importing it in the `src/serial_jobs/device/__init__.py` file.

- `protocol`: _Optional_ device-type-specific protocol details needed for communicating with the device.

    It might contain fields defined below.

    - `modbus_address`: _Optional_ Modbus device ID (or Modbus device _address_) used for communicating with the defined Modbus device.

        In case of `ModbusDevice` device type, this field is _mandatory_.

- `serial`: Specification of the parameters for serial communication with the defined device.

    The specified values must be accepted by the [`serial.Serial`](https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial) class from the [`pyserial`](https://github.com/pyserial/pyserial) module.

    It might contain fields defined below.

    - `port`: Name of the hardware device (or port) used for serial communication with the defined device.
    - `baud_rate`: Baud rate used for serial communication with the defined device.
    - `data_bits`: Number of data bits used for serial communication with the defined device.
    - `stop_bits`: Number of stop bits used for serial communication with the defined device.
    - `parity`: Parity used for serial communication with the defined device.
    - `timeout`: Timeout in seconds used for serial communication with the defined device.

#### `tasks`

A _sequence_ of task specifications.

Each specification might contain fields defined below.

- `id`: Unique ID of the defined task.

    It is used for referring to a particular task within this configuration.

- `name`: _Optional_ human-readable name of the defined task.

    It might be used to make the configuration file less ambiguous.

- `device`: _Optional_ ID of the configured serial device which is used by this task.

    If there is only one configured device, then this field might be omitted
    and the only configured device will be used.

- `mqtt_broker`: _Optional_ ID of the configured MQTT broker which is used by this task.

    If there is only one configured MQTT broker, then this field might be omitted
    and the only configured MQTT broker will be used.

- `mqtt_topic`: MQTT topic to which the MQTT messages with the obtained values will be sent.
- `value`: Specification of how to obtain the value for sending to the configured MQTT broker from the configured serial device.

    It might contain fields defined below.

    - `type`: _Optional_ Python data type to which to convert the obtained data before serializing it to string for sending to the configured MQTT broker.

        Available values are: `float`, `int`, `str`, `date`, `datetime`, `time`

    - `mapping`: _Optional_ string-to-string mapping applied to the obtained data before converting it to the final value type.

        Example:

            mapping:
              0: normal
              1: high temperature warning
              2: low temperature warning

    - `data`: A _sequence_ of data part specifications.

        A data part specification defines how to obtain individual parts of data from the device.
        It consists of a single field whose name determines the data type of the data part
        and whose value determines the device register from which to obtain the bytes for the data part.

        Available data types are:

        - `string`: string of byte characters
        - `byte`: one-byte unsigned integer
        - `signed_byte`: one-byte signed integer
        - `short`: two-byte unsigned integer
        - `signed_short`: two-byte signed integer
        - `long`: four-byte unsigned integer
        - `signed_long`: four-byte signed integer
        - `float`: four-byte floating point number
        - `double`: eight-byte floating point number

        All multi-byte numeric data types are by default expected to use big-endian byte order (i.e. the most significant byte has the smallest memory address).

        The values representing the device register from which to obtain the bytes for the data part might contain the following fields:

        - `register_type`: _Optional_ type of the register to read from. Defaults to `default`.

            Available values are:

            - `default`: The device-specific default register type.

                Some device types like `ModbusDevice` do not have the default register type.
                For those it is necessary to explicitly specify a register type other than `default`.

            - `coil`: A readable and writable register type which holds one bit of data.

                Available only for devices of type `ModbusDevice`.

            - `discrete`: A readable register type which holds one bit of data.

                Available only for devices of type `ModbusDevice`.

            - `holding`: A readable and writable register type which holds two bytes of data.

                Available only for devices of type `ModbusDevice`.

            - `input`: A readable register type which holds one bit of data.

                Available only for devices of type `ModbusDevice`.

        - `writable_block`: _Optional_ specification of the block of registers which need to be written to the device at the same time when writing the data to this particular register block.

            It might contain fields defined below.

            - `start_address`: Start address (inclusive) of the register block to write.
            - `stop_address`: Stop address (exclusive) of the register block to write.

        - `register_count`: _Optional_ number of registers to use. Defaults to 1.
        - `address`: Start address (inclusive) of the register block to use.
        - `byte_order`: _Optional_ sequence of byte indices determining how to order the bytes from this register block into the resulting data part.
        - `byte_offset`: _Optional_ number of bytes from this register block to skip before creating the resulting data part.
        - `byte_count`: _Optional_ number of bytes from this register block starting at `byte_offset` to use for creating the resulting data part.
        - `byte_index`: _Optional_ index of a single byte within this register block to use for creating the resulting data part.

            If defined, overrides `byte_offset` and `byte_count`.

        - `bitmask`: _Optional_ binary integer determining the bitmask applied to the sequence of bytes extracted from this register block.

            Example: `0b10001100`

        - `bitshift`: _Optional_ number of bits to shift the sequence of bytes extracted from this register block.

            If positive, shift to the right (i.e. divide by a power of two). If negative, shift to the left (i.e. multiply by a power two).

        - `scale_factor`: _Optional_ Number by which to divide the bit-shifted data value.
        - `increase_by`: _Optional_ Number which is added to the scaled data value.

Configuration files for some real devices and real use cases
are available in the [`config_stubs`](./config_stubs) directory.
