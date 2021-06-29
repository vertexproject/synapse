Cortex Operations
=================

Docker Deployment
-----------------

A Cortex may be quickly deployed using pre-built docker containers which are built with each Synapse release.
The Cortex docker container is configured to allocate all local storage within the directory ``/vertex/storage`` which
may be mapped in as a volume.

.. note::
    It is strongly recommended that production deployments specify a specific container version such as ``vertexproject/synapse-cortex:v2.4.0``
    to make version updates an opt-in behavior.

The following example docker-compose.yml file will execute a cortex with an external storage volume mapped and ports mapped to expose the Cortex::

    services:
      core_000:
        environment:
        - SYN_LOG_LEVEL=DEBUG
        - SYN_CORTEX_AUTH_PASSWD=secret
        image: vertexproject/synapse-cortex:master
        ports:
        - 443:4443
        - 27492:27492
        volumes:
        - ./core_000:/vertex/storage
    version: '3'

.. note::

    The ``SYN_CORTEX_AUTH_PASSWD`` environment variable or ``auth:passwd`` key in ``cell.yaml`` will initialize the password
    for the ``root`` user.  Additional custom Cortex configuration may be done via additional environment variables or
    options within the ``cell.yaml``.

You can now connect to the Cortex using the ``cmdr`` tool::

    python -m synapse.tools.cmdr tcp://root:secret@localhost:27492


Storm Query Logging
-------------------

The Cortex can be configured to log Storm queries executed by users. This is done by setting the ``storm:log`` and
``storm:log:level`` configuration options ( :ref:`autodoc-cortex-conf` ). The ``storm:log:level`` option may be one of
``DEBUG``, ``INFO`` , ``WARNING``, ``ERROR``, ``CRITICAL``; or as a corresponding `Python logging`_ log level as an
integer value. This allows an organization to set what log level their Storm queries are logged at.

When enabled, the log message contains the query text and username::

    2021-06-28 16:17:55,775 [INFO] Executing storm query {inet:ipv4=1.2.3.4} as [root] [cortex.py:_logStormQuery:MainThread:MainProcess]

When structured logging is also enabled for a Cortex, the query text, username, and user iden are included as individual
fields in the logged message as well::

    {
      "message": "Executing storm query {inet:ipv4=1.2.3.4} as [root]",
      "logger": {
        "name": "synapse.storm",
        "process": "MainProcess",
        "filename": "cortex.py",
        "func": "_logStormQuery"
      },
      "level": "INFO",
      "time": "2021-06-28 16:18:47,232",
      "text": "inet:ipv4=1.2.3.4",
      "username": "root",
      "user": "3189065f95d3ab0a6904e604260c0be2"
    }

This logging does interplay with the underlying Cell log configuration ( :ref:`devops-cell-logging` ). The
``storm:log:level`` value must be greater than or equal to the base log level of the Cell, otherwise the Storm log will
not be emitted.


Configuring A Mirror
--------------------

A Cortex mirror replicates an entire Cortex to another host allowing it to act as a parallel query execution
engine or hot-spare.  Mirrors may be created in "tree" configurations where one mirror is used to synchronize several
downstream mirrors to offload replication load from the main Cortex.  Additionally, Cortex mirrors support
write-back, allowing the mirror to appear to be read-write by passing edits to the upstream Cortex and awaiting
synchronization to apply the change locally.

To deploy a Cortex mirror, you must first ensure that the ``nexuslog:en`` setting on your Cortex is enabled in ``cell.yaml``.
This is enabled by default, but may be disabled in some high-performance custom configurations.  The initial state of a
mirror is created by creating a backup of the Cortex using the standard synapse service backup tool::

    python -m synapse.tools.backup /path/to/cortex /path/to/mirror/cortex

A single backup may be copied multiple times to deploy several mirrors.  Once the backup is created, edit the ``cell.yaml``
of the new mirror to include a telepath URL to the upstream Cortex::

    mirror: "tcp://user:passwd@cortexhost/"

.. note::

    The telepath URL must contain a valid user/password with global admin priviledges on the upstream Cortex.

Once the ``mirror`` option is configured, the new mirror Cortex may be deployed normally and will stay synchronized
in near real-time provided it can maintain the network link.

Configuring A Remote Axon
-------------------------

By default a Cortex will initialize a local :ref:`gloss-axon` for general object / blob storage. This allows certain
Cortex functionality to work without additional configuration. The local Axon is not exposed in a remote fashion.

An Axon can instead be deployed as a remote server (see :ref:`devops-axon`) and the Cortex can be configured to be aware
of it, by specifying the Axon's Telepath URL in the ``axon`` configuration parameter (see :ref:`autodoc-cortex-conf`).

For example, if the remote Axon is listening on port ``27592``, and has a service user ``core00``, then the
Cortex ``cell.yaml`` file could have the following configuration::

    ---
    axon: tcp://core00:secret@<axon_host_ip>:27592
    ...

For interacting with byte storage inside of Storm, see :ref:`stormlibs-lib-bytes` for APIs related to interacting with
the Axon.

.. _200_migration:

0.1.x to 2.x.x Migration
------------------------

.. warning::
    The ``0.1.x`` to ``2.x.x`` migration tools have been removed in Synapse ``v2.9.0``.

For information about migrating older Cortexes to v2.8.0, please refer to the ``v2.8.0`` documentation
`here <https://synapse.docs.vertex.link/en/v2.8.0/synapse/devguides/devops_cortex.html#x-to-2-x-x-migration>`_.

.. _Python logging: https://docs.python.org/3.8/library/logging.html#logging-levels