Cell Operations
===============

As detailed in :ref:`dev_architecture`, the ``Cell`` implements a number of core management functionalities,
and is therefore used as the base class for Synapse applications.  It is also recommended to implement ``Cell`` for
custom Storm Services and other Synapse related components.

.. _devops-cell-config:

Configuring a Cell
------------------

A Cell has a set of base configuration data that will also be inherited by any implementations:

- ``dirn``: The storage directory for the Cell which is a required argument for Cell startup.
- ``telepath``: Optional override for the Telepath URL to listen on.
- ``https``: Optional override for the port to bind for the HTTPS/REST API.
- ``name``: Optional additional name to share the cell as.

The Cell class also specifies configuration variables in ``confdefs``:

- ``auth:passwd``: Optional bootstrapping for the root user password.
- ``nexslog:en``: Optional enablement of Nexus logging (most custom Cell implementations will not set this).

Cell implementations can extend the configuration variables available by specifying them in
``confdefs`` in the Cell subclass.  The variable names can be namespaced using colons, for example ``mysvc:apikey``.

Depending on deployment requirements, a combination of methods can be used for loading the configurations into the Cell.

.. note::
    The Cell directory (refered to as ``dirn``) should be considered a persistent directory for a given Synapse
    cell. Inside of this directory there are several files stored which are necessary in order for a given instance
    of a cell deployment to work properly.

    Docker images made by Vertex to support Synapse cells will have default volumes for ``/vertex/storage``.
    We use this as the default cell directory for default entry points in documentation. This location can either
    have a persistent docker volume present for it created, or a external location on disk can be mapped into this
    location. Any orchestration tooling should consider the requirements for cell directory data to be persistent,
    unless stated otherwise.


Config File
***********

A Cell has one optional configuration file, ``cell.yaml``, that may be located in the root Cell directory.
The format of this file is YAML, and variable names are specified without alteration, for example::

    ---
    auth:passwd: secret
    mysvc:apikey: 720a50f9-cfa1-43a9-9eca-dda379ecd8c5
    ...

Environment Variables
*********************

Environment variable names are automatically generated for a Cell configuration options using the following naming
convention: ``SYN_<cell_subclass_name>_<variable_name>``.  Variable names with colons are replaced with underscores,
and the raw environment variable value is deserialized as yaml, prior to performing type validation.

Command Line
************

Variables which can only be easily passed as command line arguments are available on the command line.
Variable names with colons are replaced with a single dash.

.. note::

    When used to launch a Cell as the entry point of a program, the configuration precedence order is:

    #. Command line arguments
    #. Environment variables
    #. cell.yaml values

    These may all be mixed and matched for a given deployment.
    If a backup of a Cell is made and the deployment uses configuration data from command line arguments and
    environment variables, those will need to be considered when moving/restoring the backup.

Starting a Cell
---------------

The examples provided below are intended for Cell implementations outside of the Synapse level components,
which have their own servers in the ``synapse.servers`` module.

As Main Module
**************

Cell implementations may define the following as the main application entrypoint (where MyCell is the Cell subclass)::

    if __name__ == '__main__':
        asyncio.run(MyCell.execmain(sys.argv[1:]))

The cell can then be started with::

    python -m path.to.main /path/to/dirn

As Cell Server
**************

The generic Cell server can also be used for starting the Cell by specifying the constructor as an argument::

    python -m synapse.servers.cell path.to.MyCell /path/to/dirn

.. _devops-cell-logging:

Cell Logging
------------

Synapse Cells have logging configured with the command line or with environment variables. The following command line
arguments can be used to enable logging at specific levels, as well as enabling structured logging::

  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Specify the Python logging log level.
  --structured-logging  Use structured logging.

These can also be configured from the environmental variables ``SYN_LOG_LEVEL`` and ``SYN_LOG_STRUCT``, respectively.
The ``SYN_LOG_LEVEL`` variable can be specified as a string (``DEBUG``, ``INFO``, etc) or as a corresponding
`Python logging`_ log level as an integer. The ``SYN_LOG_STRUCT`` varialbe, if present, will enabled structured logging
if it is not set to a false value such as ``0`` or ``false``.

When structured logging is enabled logs will be emitted in JSON lines format. An example of that output is shown below,
showing the startup of a Cortex with structured logging enabled::

    $ SYN_LOG_LEVEL=INFO SYN_LOG_STRUCT=true python -m synapse.servers.cortex cells/core00/
    {"message": "log level set to INFO", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "common.py", "func": "setlogging"}, "level": "INFO", "time": "2021-06-28 15:47:54,825"}
    {"message": "dmon listening: tls://0.0.0.0:27492/?ca=test", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "cell.py", "func": "initServiceNetwork"}, "level": "INFO", "time": "2021-06-28 15:47:55,101"}
    {"message": "...cortex API (telepath): tls://0.0.0.0:27492/?ca=test", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "cell.py", "func": "initFromArgv"}, "level": "INFO", "time": "2021-06-28 15:47:55,102"}
    {"message": "...cortex API (https): 4443", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "cell.py", "func": "initFromArgv"}, "level": "INFO", "time": "2021-06-28 15:47:55,103"}

These structured logs are designed to be easy to ingest into third party log collection platforms. They contain the log
message, level, time, and metadata about where the log message came from. The following is a pretty printed example::

    {
      "message": "log level set to INFO",
      "logger": {
        "name": "synapse.lib.cell",
        "process": "MainProcess",
        "filename": "common.py",
        "func": "setlogging"
      },
      "level": "INFO",
      "time": "2021-06-28 15:47:54,825"
    }

When exceptions are logged with structured logging, we capture additional information about the exception, including the
entire traceback. In the event that the error is a Synapse Err class, we also capture additional metadata which was
attached to the error. In the following example, we also have the query text, username and user iden available in the
log message pretty-printed log message::

    {
      "message": "Error during storm execution for { || }",
      "logger": {
        "name": "synapse.lib.view",
        "process": "MainProcess",
        "filename": "view.py",
        "func": "runStorm"
      },
      "level": "ERROR",
      "time": "2021-06-28 15:49:34,401",
      "err": {
        "efile": "coro.py",
        "eline": 233,
        "esrc": "return await asyncio.get_running_loop().run_in_executor(forkpool, _runtodo, todo)",
        "ename": "forked",
        "at": 1,
        "text": "||",
        "mesg": "No terminal defined for '|' at line 1 col 2.  Expecting one of: #, $, (, *, + or -, -(, -+>, -->, ->, :, <(, <+-, <-, <--, [, break, command name, continue, fini, for, function, if, init, property name, return, switch, while, whitespace or comment, yield, {",
        "etb": ".... long traceback ...",
        "errname": "BadSyntax"
      },
      "text": "||",
      "username": "root",
      "user": "3189065f95d3ab0a6904e604260c0be2"
    }

.. _Python logging: https://docs.python.org/3.8/library/logging.html#logging-levels