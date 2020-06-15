.. _dev_stormservices:

Storm Service Development
#########################

Anatomy of a Storm Service
==========================

A Storm :ref:`gloss-service` is a standalone application that extends the capabilities of the Cortex.
One common use case for creating a service is to add a Storm command that will query third-party data,
translate the results into the Synapse datamodel, and then ingest them into the hypergraph.

A Storm service generally implements the following components:

- A :ref:`gloss-package` that contains the new :ref:`stormservice-cmd` and optional new :ref:`stormservice-mod`.

- A subclass of ``synapse.lib.CellApi`` which uses the ``synapse.lib.StormSvc`` mixin and contains the following information:

    - The service name, version, packages, and events as defined in ``synapse.lib.StormSvc``.
    - Custom methods which will be accessible as Telepath API endpoints, and therefore available for use within defined Storm commands.

- A subclass of ``synapse.lib.Cell`` which includes additional configuration defintions (``confdefs``) that the Storm service requires. Typically the methods required to implement the service functionality are contained here, and are called within the Cell API.

Service startup
---------------

Since Storm services are Cell implementations, there are helpers available to simplify startup configuration.
For example, if ``MySvc`` is the new custom subclass of ``synapse.lib.Cell``, ``MySvc.execmain(sys.argv[1:])`` can be used
to run it as a main module.  The service specific configuration definitions will be available as command line options (``--<mysvcconf1>``)
and environment variables (``MYSVC_<mysvcconf1>``).

A simple startup command, which includes configurations inherited from the Cell, might look as follows
(assuming that the service components live in a ``service.py`` file)::

    python -m synmods.mysvc.service --telepath tcp://0.0.0.0:27495 --https 2443 --<mysvcconf1> foo <service_cell_dirn>

Connecting a service
--------------------

Before connecting a service to a Cortex it is best practice to add a new user to the service Cell (:ref:`initial-roles`).

A Storm command can then be run on the Cortex to add the new service::

    service.add mysvc tcp://<username>:<passwd>@<service_ip>:27495

Permissions to access the service can be added by adding the ``service.get.<svc_iden>`` rule to the appropriate users / roles.

The new Storm commands will now be available for use, and are included in Storm ``help``.

.. _stormservice-cmd:

Storm Service Commands
======================

Implementation
--------------

Multiple Storm commands can be added to a Storm service package, with each defining the following attributes:

    - ``name``: Name of Storm command to surface in the Cortex.
    - ``descr``: Description of the command which will be available in ``help`` displays.
    - ``cmdargs``: An optional list of arguments for the command.
    - ``cmdconf``: An optional dictionary of additional configuration variables to provide to the command Storm execution.
    - ``forms``: List of input and output forms for the command.
    - ``storm``: The Storm code, as a string, that will be executed when the command is called.

Typically, the Storm code will start by getting a reference to the service via ``$svc = $lib.service.get($cmdconf.svciden)``
and reading in any defined ``cmdargs`` that are available in ``$cmdopts``.  The methods defined in the service's Cell API
can then be called by, for example, ``$retn = $svc.mysvcmethod($cmdopts.query)``.

Input/Output Conventions
------------------------

Most commands that enrich or add additional context to nodes should simply yield the nodes they were given as inputs.
If they don’t know how to enrich or add additional context to a given form, nodes of that form should be yielded rather than producing an error.
This allows a series of enrichment commands to be pipelined regardless of the different inputs that a given command knows how to operate on.

Argument Conventions
--------------------

``--verbose``
~~~~~~~~~~~~~

In general, Storm commands should operate silently over their input nodes and should especially avoid printing anything "per node".
However, when an error occurs, the command may use ``$lib.warn()`` to print a warning message per-node.
Commands should implement a ``--verbose`` command line option to enable printing "per node" informational output.

``--debug``
~~~~~~~~~~~

For commands where additional messaging would assist in debugging a ``--debug`` command line option should be implemented.
For example, a Storm command that is querying a third-party data source could use ``$lib.print()`` to print the raw query string
and raw response when the ``--debug`` option is specified.

``--yield``
~~~~~~~~~~~

For commands that create additional nodes, it may be beneficial to add a ``--yield`` option to allow a query to operate on the newly created nodes.
Some guidelines for ``--yield`` options:

- The command should *not* yield the input node(s) when a ``--yield`` is specified
- The ``--yield`` option should *not* be implemented when pivoting from the input node to reach the newly created node is a “refs out” or 1-to-1 direct pivot. For example, there is no need to have a ``--yield`` option on the ``maxmind`` command even though it may create an ``inet:asn`` node for an input ``inet:ipv4`` node due to the 1-to-1 pivot ``-> inet:asn`` being possible.
- The ``--yield`` option should ideally determine a “primary” node form to yield even when the command may create many forms in order to tag them or update .seen times.

.. _stormservice-mod:

Storm Service Modules
=====================

Modules can be added to a Storm service package to surface reusable Storm functions.
Each module defines a ``name``, which is used for importing elsewhere via ``$lib.import()``,
and a ``storm`` string.  The Storm code in this case contains callable functions with the format::

    function myfunc(var1, var2) {
        // function Storm code
    }
