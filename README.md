# Serial Jobs

A tool for bidirectional communication between serial devices and MQTT brokers.

Configured serial devices are periodically polled for data
which are then sent to the configured MQTT brokers.

Subscribtions to the configured MQTT topics are created
and the configured handlers are run when an MQTT message is received.

## Features

* reading data via [Modbus](https://modbus.org/specs.php) protocol
* possibility to add support for custom protocols
* sending custom initialization messages to MQTT broker
* configuration in YAML or JSON format

Custom initialization MQTT messages can be used
to automatically configure the consumers
of the MQTT messages with the actual values,
like [Home Assistant](https://www.home-assistant.io/),
to handle them appropriately.

### Terminology

This section explains the terminology used within the configuration file.

### Common

1. An _mqtt_broker_ specifies how to communicate with an MQTT broker.
1. A _device_ specifies how to communicate with a serial device.
1. A _data_ specifies how map raw bytes from device to a simple data part usable for obtaining a _value_.
1. A _value_ specifies how to map simple _data_ parts provided by device to a value usable in practice.

### Reading from devices

1. A _task_ specifies how to retrieve a particular _value_ from a particular _device_ and how to send it within an MQTT message.
1. A _job_ specifies how often to run particular _tasks_.

### Writing to devices

1. A _handler_ specifies how to extract _value_ from the incoming MQTT message and write it to a particular _device_.
1. A _service_ specifies which handlers to run upon receiving messages from a particular _mqtt_broker_.

## Configuration

Configuration files for some real devices and real use cases
are available in the [`config_stubs`](./config_stubs) directory.
