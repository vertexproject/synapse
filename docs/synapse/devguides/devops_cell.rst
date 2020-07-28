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

Cell Permissions
----------------

The following permissions exist for controlling access to Cell operations.

*admin.cmds*
    Set or remove Storm command definitions from a Cortex.

*auth.role.add*
    Add a Storm Role.

*auth.role.del*
    Delete a Storm Role.

*auth.role.set.rules*
    Set rules for a Storm Role.

*auth.user.add*
    Add a User.

*auth.user.del*
    Delete a User.

*auth.user.grant*
    Grant a Storm Role to a user.

*auth.user.revoke*
    Revoke a Storm Role from a user.

*auth.user.set.admin*
    Set whether a User is an Admin.

*auth.user.set.email*
    Set the email of a User.

*auth.user.set.locked*
    Set the locked status of a User.

*auth.user.set.passwd*
    Set a User's password.

*auth.user.set.rules*
    Set rules for a User.

*axon.get*
    Retrieve a binary object from the Axon.

*axon.has*
    Check if the Axon has bytes represented by a SHA-256 or return SHA-256 and object sizes from an offset.

*axon.upload*
    Upload and save a binary object to the Axon.

*cron.add*
    Add a cron job.

*cron.del*
    Delete a cron job.

*cron.get*
    Get a cron job.

*cron.set*
    Update the Storm Query for a cron job.

*cron.set.doc*
    Set the docstring for a cron job.

*cron.set.name*
    Set the name for a cron job.

*dmon.add*
    Add a Storm Dmon.

*dmon.del*
    Delete any Storm Dmon.

*dmon.del.<iden>*
    Delete a specific Storm Dmon.

*dmon.log*
    Get messages from Storm Dmons.

*feed:data*
    Ingest feed data of any type.

*feed:data.<name>*
    Ingest feed data of a specific ingest type.

*globals.get*
    Get global variables.

*globals.get.<name>*
    Get a specific global variable.

*globals.pop*
    Pop a global variables.

*globals.pop.<name>*
    Pop a specific global variable.

*globals.set*
    Set global variables.

*globals.set.<name>*
    Set a specific global variable.

*health*
    Get a HealthCheck object from the Cell.

*impersonate*
    Impersonate another User.

*layer.add*
    Add a Layer.

*layer.del*
    Delete a Layer.

*layer.edits.read*
    Read edits made to a layer.

*layer.lift*
    Lift data from any layer.

*layer.lift.<iden>*
    Lift data from a specific layer.

*layer.set.<name>*
    Set the Layer definition for a Layer.

*layer.write.<iden>*
    Write to any layer.

*layer.write.<iden>*
    Write to a specific layer.

*lib.telepath.open*
    Open a Telepath Proxy to a URL.

*lib.telepath.open.<scheme>*
    Open a Telepath Proxy to a URL with a specific scheme.

*model.prop.add.<form>*
    Add an extended property to a form.

*model.prop.del.<form>*
    Remove an extended property from a form.

*model.tagprop.add*
    Add a tag property.

*model.tagprop.del*
    Remove a tag property.

*model.univ.add*
    Add an extended universal property.

*model.univ.del*
    Remove an extended universal property.

*node.add*
    Add any form of node.

*node.add.<form>*
    Add a specific form of node.  (ex. ``node.add.inet:ipv4``)

*node.data.get*
    Get the value of any node data property on a node.

*node.data.get.<name>*
    Get the value of a specific node data property on a node.

*node.data.list*
    List all of the node data properties on a node.

*node.data.pop*
    Remove and return the value of any node data property on a node.

*node.data.pop.<name>*
    Remove and return the value of a specific node data property on a node.

*node.data.set*
    Set any node data property on a node.

*node.data.set.<name>*
    Set a specific node data property on a node.

*node.del*
    Delete any form of node.

*node.del.<form>*
    Delete a <form> node. (ex. ``node.del.inet:ipv4``)

*node.edge.add*
    Add lightweight edges.

*node.edge.add.<verb>*
    Add lightweight edges with a specific verb.

*node.edge.del*
    Remove lightweight edges.

*node.edge.del.<verb>*
    Remove lightweight edges with a specific verb.

*node.prop.del*
    Delete any property.

*node.prop.del.<prop>*
    Delete a specific property.  (ex. ``node.prop.del.inet:ipv4:loc``)

*node.prop.set*
    Set any property.

*node.prop.set.<prop>*
    Set a specific property.  (ex. ``node.prop.set.inet:ipv4:loc``)

*node.tag.add*
    Add any tag to a node.

*node.tag.add.<tag>*
    Add a specific tag or subtag to a node. (ex. ``node.tag.add.foo.bar``)

*node.tag.del*
    Remove any tag from a node.

*node.tag.del.<tag>*
    Remove a specific tag or subtag to a node. (ex. ``node.tag.del.foo.bar``)

*pkg.add*
    Add a Storm package.

*pkg.del*
    Remove a Storm package.

*queue.add*
    Add a Queue.

*queue.del*
    Delete a Queue.

*queue.get*
    Get a Queue object.

*queue.put*
    Put an object in a Queue.

*service.add*
    Add a Storm Service.

*service.del*
    Remove a Storm Service.

*service.get*
    Get any Storm Service definition.

*service.get.<name>*
    Get a specific Storm Service definition.

*service.list*
    List the Storm Service definitions.

*status*
    Get status information for a Cortex.

*sync*
    Get nodeedit sets for a layer.

*task.del*
    Kill a running task.

*task.get*
    Get information about a running task.

*trigger.add*
    Add a Trigger.

*trigger.del*
    Delete a Trigger.

*trigger.get*
    Get a Trigger.

*trigger.set*
    Set the Storm Query for an existing Trigger.

*trigger.set.doc*
    Set the docstring for a Trigger.

*trigger.set.name*
    Set the name for a trigger.

*view.add*
    Add a View.

*view.del*
    Delete a View.

*view.read*
    Read from a View.

*view.set.<name>*
    Set the View definition for a View.

*watch*
    Hook Cortex/View/Layer watch points based on a watch definition.

*watch.view.<iden>*
    Hook Cortex/View/Layer watch points based on a watch definition for a specific iden.
