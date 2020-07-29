Cell Permissions
################

The following section contains permissions used to control access in Synapse Cell implementations which are baked into the core
Synapse package. These can be added to or removed from users with the cellauth tool::

    python -m synapse.tools.cellauth cell://cortex modify myuser --addrule node.add
    python -m synapse.tools.cellauth cell://cortex modify myuser --delrule node.tag.add

or managed through Storm (see :ref:`stormlibs-lib-auth`).

Axon Permissions
================

The following permissions exist for controlling access to Axon operations.

*axon.get*
    Retrieve a binary object from the Axon.

*axon.has*
    Check if the Axon has bytes represented by a SHA-256 or return SHA-256 and object sizes from an offset.

*axon.upload*
    Upload and save a binary object to the Axon.

Cell Permissions
================

The following permissions exist for controlling access to Cell operations.

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

*health*
    Get a HealthCheck object from the Cell.

*impersonate*
    Impersonate another User.

*task.del*
    Kill a running task.

*task.get*
    Get information about a running task.

Cortex Permissions
==================

The following permissions exist for controlling access to Cortex operations.

*admin.cmds*
    Set or remove Storm command definitions from a Cortex.

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

    **Note:** This is currently a deprecated permission.

*sync*
    Get nodeedit sets for a layer.

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
