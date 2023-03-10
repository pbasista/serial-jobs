###########
Serial Jobs
###########

A tool for bidirectional communication between serial devices and MQTT brokers.

.. sectnum::
.. contents::
   :local:

********
Features
********

* Data flow is fully defined in a configuration file.
* Built-in support for the `Modbus`_ protocol.
* Adding support for custom serial protocols possible by extending code.
* Ability to send user-specific initialization MQTT messages on startup.

.. note::

   The initialization MQTT messages can be used
   to automatically configure the consumers of the value-carrying MQTT messages,
   like `Home Assistant`_, to handle them appropriately.

.. _Modbus: https://modbus.org/specs.php
.. _Home Assistant: https://www.home-assistant.io/

One of the design goals is to enable regular users
to get desired data from any Modbus device
merely by editing a configuration file.

************
How it works
************

Reading from serial devices
===========================

#. Configured serial devices are periodically polled for data.
#. These data are then converted to usable values according to the configured rules.
#. The obtained values are then sent to the configured MQTT brokers.

Writing to serial devices
=========================

#. Subscribtions to the configured MQTT topics are created.
#. The configured handlers are run when a matching MQTT message is received.
#. Handlers extract values from the incoming MQTT messages
   and convert them to protocol-specific data according to the configured rules.
#. The obtained data are then written to the configured serial devices.

************
Installation
************

.. code-block:: console

  $ pip install serial-jobs

*****
Usage
*****

#. Edit the provided YAML configuration file stubs in the `config_stubs`_ directory
   or create new ones as desired.

.. _config_stubs: https://github.com/pbasista/serial-jobs/tree/main/config_stubs

#. Merge the relevant YAML configuration file stubs into a single file.

   .. code-block:: console

      $ merge_config config_stubs/*
      INFO serial_jobs.config loading stub configuration file config_stubs/epever-charge-controller.yaml
      INFO serial_jobs.config loading stub configuration file config_stubs/jbd-battery-management-system.yaml
      INFO serial_jobs.config loading stub configuration file config_stubs/mqtt-brokers.yaml
      INFO serial_jobs.config loading stub configuration file config_stubs/orno-energy-meter.yaml
      Overwrite configuration file ./configuration.yaml? (y/n) y
      INFO serial_jobs.config saving configuration to file ./configuration.yaml
      INFO serial_jobs.config configuration file saved

#. Convert the configuration file from YAML format to JSON format
   for faster parsing at runtime.

   .. code-block:: console

      $ convert_config
      INFO serial_jobs.config loading configuration file ./configuration.yaml
      INFO serial_jobs.config configuration file loaded
      Overwrite configuration file ./configuration.json? (y/n) y
      INFO serial_jobs.config saving configuration to file ./configuration.json
      INFO serial_jobs.config configuration file saved

#. Run the application.

   .. code-block:: console

      $ serial_jobs
      INFO serial_jobs.config loading configuration file ./configuration.json
      INFO serial_jobs.config configuration file loaded
      INFO serial_jobs.device.base creating device lock /dev/ttyUSB0
      ...


*************
Configuration
*************

The application is configured via a configuration file in either YAML or JSON format.

Below is an example of a simple configuration file which uses the YAML format.

.. code-block:: yaml

    mqtt_brokers:
      - id: local
        host: 127.0.0.1
        port: 1883
        username:
        password:

    devices:
      - id: orno-or-we-514
        name: ORNO OR-WE-514 single phase energy meter
        serial:
          port: /dev/ttyUSB0
          baud_rate: 9600
          data_bits: 8
          stop_bits: 1
          parity: E
          timeout: 0.1
        protocol:
          modbus_address: 0x13

    tasks:
      - id: o-active-power
        name: active power in W
        device: orno-or-we-514
        mqtt_topic: orno-or-we-514/active-power
        value:
          data:
            - signed_long:
                register_type: holding
                register_count: 2
                address: 0x140

    jobs:
      - id: power-meter
        mqtt_messages:
          - homeassistant/sensor/default/power-meter-active-power/config:
              device:
                name: ORNO energy meter
                manufacturer: ORNO
                model: OR-WE-514
                identifiers: orno-or-we-514
              device_class: power
              name: Active Power
              state_class: measurement
              state_topic: orno-or-we-514/active-power
              object_id: orno-or-we-514-active-power
              unique_id: orno-or-we-514-active-power
              unit_of_measurement: W
        sleep: 10
        tasks:
          - o-active-power

It instructs ``serial-jobs`` to poll an energy meter
for the current active power value every 10 seconds
and publish it to an MQTT broker.

Configuration files for some real devices and real use cases
are available in the `config_stubs`_ directory.

The data structures used within the configuration file are described below.

Configuration data structures
=============================

Valid configuration data structures are: a string, a number, a boolean, a sequence or an object.

.. note::

   All numeric formats recognized by Python are supported.
   For instance, values which represent hardware addresses of any kind
   might be specified as hexadecimal numbers, i.e. numbers prefixed with ``0x``.

A *sequence* is a list-like data structure.
It must contain items of the same type.

An *object* is a dictionary-like data structure.
It consists of *fields*.

A *field* is represented by a *key* and a *value*.
A *key* is a string.
A *value* can be any valid configuration data structure,
i.e. a string, a number, a boolean, a sequence or an object.

There can be at most one field with a particular key within a specific object.

Terminology
-----------

This section explains the terminology used within this documentation,
the configuration files and the source code.

data part
    Partially meaningful piece of information
    that can be converted to protocol-specific sequence of bytes
    suitable for a particular serial device.

value
    A meaningful piece of information represented by *data parts* on a serial device.

task
    A routine which retrieves a particular *value* from a particular serial device
    and sends it within an MQTT message.

job
    A group of *tasks* performed periodically.

handler
    A routine which extracts a particular *value* from an incoming MQTT message
    with a particular MQTT topic and writes it to a particular serial device.

service
    A group of *handlers* to run upon receiving messages from a particular MQTT broker.

Top-level configuration structures
----------------------------------

This section describes configuration data structures
that might be present at the top-level of the configuration file.

Common
^^^^^^

.. _mqtt-broker:

``mqtt_brokers``
    A part of configuration which specifies how to communicate with MQTT brokers.

    It consists of a *sequence* of MQTT broker specifications.
    Each specification might contain the fields defined below.

    :id: Unique ID of the defined MQTT broker.
        It is used for referring to a particular MQTT broker within this configuration.
    :name: *(optional)* Human-readable name of the defined MQTT broker.
        It might be used to make the configuration file less ambiguous.
    :host: Hostname of the defined MQTT broker.
    :port: Port of the defined MQTT broker.
    :username: Username for connecting to the defined MQTT broker.
    :password: Password for the defined username.

    **Example:**

    .. code-block:: yaml

        mqtt_brokers:
          - id: local
            host: 127.0.0.1
            port: 1883
            username:
            password:

.. _devices:

``devices``
    A part of configuration which specifies how to communicate with serial devices.

    It consists of a *sequence* of serial device specifications.
    Each specification might contain fields defined below.

    :id: Unique ID of the defined serial device.
        It is used for referring to a particular serial device within this configuration.
    :name: *(optional)* Human-readable name of the defined serial device.
        It might be used to make the configuration file less ambiguous.
    :type: *(optional)* Type of the defined serial device.
        Defaults to ``ModbusDevice``.

        Available device types:

        * ``ModbusDevice`` for devices which communicate
          over the `Modbus`_ protocol.
        * ``BMSDevice`` for devices which communicate
          over a protocol that is used by the battery management systems
          from manufacturers such as `JBD`_.

          .. _JBD: https://gitlab.com/bms-tools/bms-tools/-/blob/master/JBD_REGISTER_MAP.md/

        .. note::

           It is possible to define a custom device type
           by creating a subclass of ``serial_jobs.device.Device``
           and importing it in the ``src/serial_jobs/device/__init__.py`` file.

    :serial: `Specification <serial_>`_ of the parameters for serial communication with the defined device.
    :protocol: *(optional)* Device-type-specific protocol details needed for communicating with the device.

        It might contain fields defined below.

        :modbus_address: *(optional)* Modbus device ID (or Modbus device *address*)
            used for communicating with the defined Modbus device.

            In case of ``ModbusDevice`` device type, this field is *mandatory*.

    **Example:**

    .. code-block:: yaml

        devices:
          - id: orno-or-we-514
            name: ORNO OR-WE-514 single phase energy meter
            serial:
              port: /dev/ttyUSB0
              baud_rate: 9600
              data_bits: 8
              stop_bits: 1
              parity: E
              timeout: 0.1
            protocol:
              modbus_address: 0x13

Related to reading from devices
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _tasks:

``tasks``
    A part of configuration which specifies
    how to retrieve `values <value_>`_ from `devices`_
    and also where and how to send them within MQTT messages.

    It consists of a *sequence* of task specifications.
    Each specification might contain fields defined below.

    :id: Unique ID of the defined task.
        It is used for referring to a particular task within this configuration.

    :name: *(optional)* Human-readable name of the defined task.
        It might be used to make the configuration file less ambiguous.

    :device: *(optional)* ID of the configured serial device which is used by this task.
        If there is only one configured device,
        then this field might be omitted
        and the only configured device will be used.

    :mqtt_broker: *(optional)* ID of the configured MQTT broker which is used by this task.
        If there is only one configured MQTT broker,
        then this field might be omitted
        and the only configured MQTT broker will be used.

    :mqtt_topic: MQTT topic to which the MQTT messages with the obtained values will be sent.

    :value: `Specification <value_>`_ of how to obtain the value
        for sending to the configured MQTT broker from the configured serial device.

    **Example:**

    .. code-block:: yaml

        tasks:
          - id: o-active-power
            name: active power in W
            device: orno-or-we-514
            mqtt_topic: orno-or-we-514/active-power
            value:
              data:
                - signed_long:
                    register_type: holding
                    register_count: 2
                    address: 0x140

.. _jobs:

``jobs``
    A part of configuration which specifies how often to perform particular `tasks`_.

    It consists of a *sequence* of job specifications.
    Each specification might contain fields defined below.

    :id: Unique ID of the defined job.
        It is used for referring to a particular job within this configuration.

    :name: *(optional)* Human-readable name of the defined job.
        It might be used to make the configuration file less ambiguous.

    :enabled: *(optional)* Boolean flag indicating whether to run this job or not.
        Defaults to *true*.

    :mqtt_broker: *(optional)* ID of the configured MQTT broker
        which is used to send initialization MQTT messages by this job.
        If there is only one configured MQTT broker,
        then this field might be omitted
        and the only configured MQTT broker will be used.

    :mqtt_messages: *(optional)* A *sequence* of specifications
        of initialization MQTT messages
        to be sent before running this job for the first time.

        Each specification consists of an *object* with a single field.
        Its key denotes the MQTT *topic* to which the message will be sent.
        Its value denotes the message content.

        .. note::

            The initialization MQTT messages are sent with the `RETAIN`_ flag.

        .. _RETAIN: http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349265

    :sleep: Number of seconds to wait between consecutive runs of this job.

    :tasks: A sequence of IDs of `tasks`_ which should be performed by this job.

    **Example:**

    .. code-block:: yaml

        jobs:
          - id: power-meter
            mqtt_messages:
              - homeassistant/sensor/default/power-meter-active-power/config:
                  device:
                    name: ORNO energy meter
                    manufacturer: ORNO
                    model: OR-WE-514
                    identifiers: orno-or-we-514
                  device_class: power
                  name: Active Power
                  state_class: measurement
                  state_topic: orno-or-we-514/active-power
                  object_id: orno-or-we-514-active-power
                  unique_id: orno-or-we-514-active-power
                  unit_of_measurement: W
            sleep: 10
            tasks:
              - o-active-power

Related to writing to devices
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _handlers:

``handlers``
    A part of configuration which specifies
    how to extract particular `values <input_value_>`_
    from incoming MQTT messages with particular MQTT topics
    and how to write them to particular `devices`_.

    It consists of a *sequence* of handler specifications.
    Each specification might contain fields defined below.

    :id: Unique ID of the defined handler.
        It is used for referring to a particular handler within this configuration.

    :name: *(optional)* Human-readable name of the defined handler.
        It might be used to make the configuration file less ambiguous.

    :device: *(optional)* ID of the configured serial device which is used by this handler.
        If there is only one configured device,
        then this field might be omitted
        and the only configured device will be used.

    :mqtt_topic: MQTT topic of MQTT messages
        from whose content this handler will extract the values.

    :value: `Specification <input_value_>`_ of how to extract the value
        from the incoming MQTT messages
        and how to write it to the configured serial device.

    **Example:**

    .. code-block:: yaml

        handlers:
          - id: e-battery-float-voltage-set
            device: epever-xtra-4415n
            mqtt_topic: epever-xtra-4415n/battery-float-voltage/set
            value:
              type: float
              data:
                - short:
                    register_type: holding
                    writable_block:
                      start_address: 0x9003
                      stop_address: 0x900F
                    address: 0x9008
                    scale_factor: 100

.. _services:

``services``
    A part of configuration which specifies which `handlers`_ to run
    upon receiving messages from particular MQTT brokers.

    It consists of a *sequence* of service specifications.
    Each specification might contain fields defined below.

    :id: Unique ID of the defined service.
        It is used for referring to a particular service within this configuration.

    :name: *(optional)* Human-readable name of the defined service.
        It might be used to make the configuration file less ambiguous.

    :enabled: *(optional)* Boolean flag indicating
        whether this service should be provided or not.
        Defaults to *true*.

    :mqtt_broker: *(optional)* ID of the configured MQTT broker which is used by this service.
        If there is only one configured MQTT broker,
        then this field might be omitted
        and the only configured MQTT broker will be used.

    :mqtt_messages: *(optional)* A *sequence* of specifications
        of initialization MQTT messages
        to be sent before starting to provide this service.

        Each specification consists of an *object* with a single field.
        Its key denotes the MQTT *topic* to which the message will be sent.
        Its value denotes the message content.

        .. note::

            The initialization MQTT messages are sent with the `RETAIN`_ flag.

        .. _RETAIN: http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349265

    :handlers: A sequence of IDs of `handlers`_ which should be dispatched by this service.

    **Example:**

    .. code-block:: yaml

        services:
          - id: charge-controller-float-voltage
            mqtt_messages:
              - homeassistant/number/default/charge-controller-battery-float-voltage/config:
                  device:
                    name: EPEVER solar charge controller
                    manufacturer: EPEVER
                    model: XTRA 4415N
                    identifiers: epever-xtra-4415n
                  entity_category: config
                  name: Battery Float Voltage
                  min: 12
                  max: 14.6
                  step: 0.01
                  device_class: voltage
                  state_class: measurement
                  command_topic: epever-xtra-4415n/battery-float-voltage/set
                  state_topic: epever-xtra-4415n/battery-float-voltage
                  object_id: epever-xtra-4415n-battery-float-voltage
                  unique_id: epever-xtra-4415n-battery-float-voltage
                  unit_of_measurement: V
            handlers:
              - e-battery-float-voltage-set

Lower-level configuration structures
------------------------------------

This section describes configuration data structures
that might only be present within certain other configuration data structures.

.. _serial:

``serial``
    Specification of the parameters for serial communication with the defined device.

    The specified values must be accepted by the `serial.Serial`_ class
    from the `pyserial`_  module.
    It might contain fields defined below.

    .. _serial.Serial: https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial
    .. _pyserial: https://github.com/pyserial/pyserial

    :port: Name of the hardware device (or port)
        used for serial communication with the defined device.
    :baud_rate: Baud rate used for serial communication with the defined device.
    :data_bits: Number of data bits used for serial communication
        with the defined device.
    :stop_bits: Number of stop bits used for serial communication
        with the defined device.
    :parity: Parity used for serial communication with the defined device.
    :timeout: Timeout in seconds used for serial communication
        with the defined device.

    **Example:**

    .. code-block:: yaml

        serial:
          port: /dev/ttyUSB0
          baud_rate: 9600
          data_bits: 8
          stop_bits: 1
          parity: E
          timeout: 0.1

.. _value:

``value`` (when used within `tasks`_ as MQTT output value)
    A part of configuration which specifies
    how to map simple `data`_ parts obtained from serial `devices`_
    to a serializable value that can be used
    when communicating with an MQTT broker.

    It consists of an object which specifies how to obtain the value
    for sending to the configured MQTT broker from the configured serial device.

    It might contain fields defined below.

    :type: *(optional)* Python data type to which to convert the obtained data
        before serializing it to string for sending to the configured MQTT broker.

        Available values are:
        `float`_, `int`_,
        `str`_,
        `date`_, `datetime`_ and `time`_.

    .. _float: https://docs.python.org/3/library/stdtypes.html#additional-methods-on-float
    .. _int: https://docs.python.org/3/library/stdtypes.html#additional-methods-on-integer-types
    .. _str: https://docs.python.org/3/library/stdtypes.html#textseq
    .. _date: https://docs.python.org/3/library/datetime.html#datetime.date
    .. _datetime: https://docs.python.org/3/library/datetime.html#datetime.datetime
    .. _time: https://docs.python.org/3/library/datetime.html#datetime.time

    :mapping: *(optional)* An object containing string-to-string mapping
        applied to the obtained data *before* converting it to the final value type.

        **Example:**

        .. code-block:: yaml

            mapping:
              0: normal
              1: high temperature warning
              2: low temperature warning

    :data: A *sequence* of data part `specifications <data_>`_.
        They specify how to convert the obtained data parts
        to Python values which could be serialized as an MQTT message.

    **Example:**

    .. code-block:: yaml

        value:
          mapping:
            0: normal
            1: overvoltage
            2: undervoltage
            3: low voltage disconnect
            4: fault
          data:
            - short:
                address: 0x3200
                bitmask: 0b1111

.. _input_value:

``value`` (when used within `handlers`_ as MQTT input value)
    A part of configuration which specifies
    how to extract value from an incoming MQTT message
    and how to write it to a particular serial `device <devices_>`_.

    It consists of an object which specifies how to obtain the value
    for sending to the configured MQTT broker from the configured serial device.

    It might contain fields defined below.

    :mapping: *(optional)* An object containing string-to-string mapping
        applied to the obtained MQTT message content
        *before* converting it to the final value type.

        **Example:**

        .. code-block:: yaml

            mapping:
              false: 0
              true: 1

    :type: *(optional)* Python data type to which to convert
        the string content of the obtained MQTT message
        before transforming it into data parts
        which will then be written to the configured serial device.

        Available values are:
        `float`_, `int`_,
        `str`_,
        `date`_, `datetime`_ and `time`_.

    :data: A *sequence* of data part `specifications <data_>`_.
        They specify how to convert the obtained Python value to data parts
        which could be written to the configured serial device.

    **Example:**

    .. code-block:: yaml

        value:
          type: float
          data:
            - short:
                register_type: holding
                writable_block:
                  start_address: 0x9003
                  stop_address: 0x900F
                address: 0x9008
                scale_factor: 100

.. _data:

``data``
    A part of configuration which specifies
    the mapping between raw bytes from `devices`_ and simple *data parts*.

    It consists of a *sequence* of data part specifications.

    A data part specification is an object
    which defines how to map an individual data part to raw device bytes.
    It consists of a single *field* whose name determines the *data type* of the data part
    and whose value determines the device *registers* which contain the bytes for the data part.

    Available data types are:

    * ``string``: string of byte-sized characters
    * ``byte``: one-byte unsigned integer
    * ``signed_byte``: one-byte signed integer
    * ``short``: two-byte unsigned integer
    * ``signed_short``: two-byte signed integer
    * ``long``: four-byte unsigned integer
    * ``signed_long``: four-byte signed integer
    * ``float``: four-byte floating point number
    * ``double``: eight-byte floating point number

    All multi-byte numeric data types are by default expected to use
    big-endian byte order (i.e. the most significant byte has the smallest memory address).

    The value of this field, representing the device registers,
    might contain the following fields:

    :register_type: *(optional)* Type of the register to read from.
        Defaults to ``default``.

        Available values are:

        * ``default``: The device-specific default register type.
          Some device types like ``ModbusDevice`` do not have the default register type.
          For those it is necessary to explicitly specify a register type other than ``default``.

        * ``coil``: A readable and writable register type which holds one bit of data.
          Available only for devices of type ``ModbusDevice``.

        * ``discrete``: A read-only register type which holds one bit of data.
          Available only for devices of type ``ModbusDevice``.

        * ``holding``: A readable and writable register type which holds two bytes of data.
          Available only for devices of type ``ModbusDevice``.

        * ``input``: A read-only register type which holds two bytes of data.
          Available only for devices of type ``ModbusDevice``.

    :writable_block: *(optional)* Specification of the block of registers
        which need to be written to the device at the same time
        when writing the data to this particular register block.

        It might contain fields defined below.

        * ``start_address``: Start address (inclusive) of the register block to write.
        * ``stop_address``: Stop address (exclusive) of the register block to write.

        .. note::

            Registers in the defined writable block
            which are unaffected by the operations on this data part
            are at first read from the serial device
            and then written back unchanged.

    :register_count: *(optional)* Number of consecutive registers to use. Defaults to 1.
    :address: Start address (inclusive) of the register block to use.
    :byte_order: *(optional)* Sequence of zero-based byte indices
        determining how to order the bytes from this register block
        into the resulting data part.

        .. note::

            This field can be used to change the byte order.
            For example, converting 4 bytes long little-endian value from a serial device
            to 4 bytes long big-endian data part can be done like this:

            .. code-block:: yaml

                byte_order: [3, 2, 1, 0]

    :byte_offset: *(optional)* Number of bytes from this register block to skip
        before creating the resulting data part.
    :byte_count: *(optional)* number of bytes from this register block
        starting at ``byte_offset`` to use for creating the resulting data part.
    :byte_index: *(optional)* Index of a single byte within this register block
        to use for creating the resulting data part.
        If defined, it overrides ``byte_offset`` and ``byte_count``.

    :bitmask: *(optional)* Binary integer (i.e. a number prefixed with ``0b``)
        determining the bitmask applied to the sequence of bytes
        extracted from this register block.

        **Example:** ``0b10001100``

    :bitshift: *(optional)* Number of bits to shift the sequence of bytes
        extracted from this register block.
        If positive, shift to the right (i.e. divide by a power of two).
        If negative, shift to the left (i.e. multiply by a power of two).

    :scale_factor: *(optional)* Number by which to divide the bit-shifted data value.
    :increase_by: *(optional)* Number which is added to the scaled data value.


    .. note::

        The order and meaning of the data operations mentioned above applies
        when converting raw device bytes to data parts within `tasks`_.

        This order is **reversed**
        when converting data parts to raw device bytes within `handlers`_.

        For instance, the operation which is performed *last* within `tasks`_,
        i.e. increasing of a value by a constant, is performed *first* within `handlers`_.

        In addition, instead of performing the operation in its original form,
        its *reverse* is performed,
        i.e. the value of the data part is decreased by the same constant.

    **Example:**

    .. code-block:: yaml

        data:
          - long:
              register_count: 2
              address: 0x3102
              byte_order: [2, 3, 0, 1]
              scale_factor: 100

    In this example, the data flow when reading from a serial device
    starts at the device registers ``0x3102`` and ``0x3103``.
    Reading those registers results in four obtained bytes.
    Those four bytes are then reordered using the defined permutation.
    Then they are converted to unsigned long integer.
    And then this value is divided by 100.
    The outcome is then processed further as a data part.

    The data flow when writing to a serial device is reversed.
    At first the unsigned long integer is multiplied by 100.
    Then its bytes are reordered using the inverse of the defined permutation.
    And then the resulting bytes are written
    to device registers ``0x3102`` and ``0x3103``.
