Cell Operations
===============

As detailed in :ref:`dev_architecture`, the ``Cell`` implements a number of core management functionalities,
and is therefore used as the base class for Synapse applications.  It is also recommended to implement ``Cell`` for custom services.

.. _devops-cell-config:

Configuring a Cell Service
--------------------------

Parameters
**********

A Cell has a set of base configuration parameters that will also be inherited by any implementations:

- ``dirn``: The storage directory for the service which is a required argument for service startup.
- ``telepath``: Optional override for the Telepath URL to listen on.
- ``https``: Optional override for the port to bind for the HTTPS/REST API.
- ``name``: Optional additional name to share the service as.
- ``auth:passwd``: Optional bootstrapping for the root user password.
- ``nexslog:en``: Optional enablement of Nexus logging (most custom Cell implementations will not set this).

Additionally, a Cell implementation may provide additional configuration parameters specific to the service
by setting definitions in ``confdefs`` in the Cell subclass.
Within ``confdefs``, parameters can be namespaced using colons, for example ``mysvc:apikey``.

Loading
*******

Depending on deployment requirements, a combination of methods can be used for loading the configurations into the Cell.

**YAML File**

If a ``cell.yaml`` file is present in the root Cell directory, configuration parameters will be read in
with the same naming convention as in ``confdefs``.  For example::

    auth:passwd: secret
    mysvc:apikey: 720a50f9-cfa1-43a9-9eca-dda379ecd8c5

**Environment Variables**

Environment variable names are automatically generated for a Cell service using the following naming convention:
``SYN_<cell_subclass_name>_<parameter>``.  Parameter names with colons are replaced with underscores.

**Command Line**

Configuration parameters can also be passed in as command line arguments when starting the service.
The naming convention is the same as ``confdefs`` with the exception that colons are replaced with a single dash.

Starting a Cell Service
-----------------------

The examples provided below are intended for Cell implementations outside of the Synapse level components
which have their own servers in the ``synapse.servers`` module.

As Main Module
**************

Cell implementations should define the following as the main application entrypoint (where MySvc is the Cell subclass)::

    if __name__ == '__main__':
        asyncio.run(MySvc.execmain(sys.argv[1:]))

The service can then be started with::

    python -m path.to.main /path/to/dirn

As Cell Server
**************

The generic Cell server can also be used for starting the service by specifying the constructor as an argument::

    python -m synapse.servers.cell path.to.MySvc /path/to/dirn

