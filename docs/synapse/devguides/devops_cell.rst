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
