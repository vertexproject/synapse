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

Two tools have been created to execute migration of an ``0.1.x`` Cortex to ``2.x.x``:

* ``migrate_200`` migrates all data from the source to a new destination ``2.x.x`` Cortex.
* ``sync_200`` allows for a backup to be migrated and then synchronized with a running Cortex to facilitate minimal downtime.

Migration Quickstart
********************

.. note::

    The duration of migration is proportional to the amount of data stored, and is highly dependent on
    the available system resources (especially disk I/O). For larger Cortexes it is recommended to
    run migration on hardware without other highly active processes.

#. Update the source to the latest Synapse ``0.1.x`` release.
#. Create a backup of the ``0.1.x`` Cortex.
#. In a new location install Synapse ``2.x.x`` and copy any custom modules / configurations present in the ``0.1.x`` environment.
#. Start migration using the backup as the source::

    python -m synapse.tools.migrate_200 --src <backup_cortex_dirn> --dest <new_2xx_dirn>

#. Inspect the migration output for any errors that may require action (see :ref:`migration-errors` for details).
#. Startup the ``2.x.x`` Cortex.

Migration Options
*****************

* ``--from-last`` restarts node migration from the last checkpoint (automatically saved at periodic intervals).
* ``--safety-off`` disables form value normalization checks as a pre-condition to migrate nodes (may allow migration to run faster).
* ``--src-dedicated`` opens the source layer slabs with locked memory (must have sufficient memory available).

Additional options that, if specified, will *not* run a migration process:

* ``--form-counts`` is a helper utility that scans all nodes and produces counts by form for source and destination.
* ``--dump-errors`` saves migration errors to a file in the migration directory in msgpack format.

.. _migration-errors:

Migration Errors
****************

During node migration the following errors may occur, all of which indicate that the node was not migrated:

``Unable to determine stortype`` or ``Buid/norming exception: NoSuchForm``

* A custom form/property may not have been properly loaded into the ``2.x.x`` environment.
* The node may not have been properly updated in a prior ``0.1.x`` datamodel migration and therefore no longer exists.

``Normed form val does not match inbound`` or ``Calculated buid does not match inbound``

* Is likely due to a node that was not properly re-normalized after a prior Synapse update.

Post-migration Synchronization
******************************

After migration, the ``sync_200`` service can be used to push post-backup changes to the migrated ``2.x.x`` Cortex,
and keep it updated until cut-over. ``sync_200`` uses splices to translate the changes, and therefore they must
be enabled on the source Cortex. In order to control and monitor synchronization, ``sync_200`` can be added as a Storm service.

When synchronization is started the service will enable "migration mode" on the destination ``2.x.x`` Cortex, which
prevents cron jobs and triggers from running. Migration mode will then be disabled when the synchronization is
stopped or when the Cortex is restarted.

#. Complete migration, including starting up the ``2.x.x`` Cortex.
#. Locate the saved splice offset file from migration at ``<new_2xx_dirn>/migration/lyroffs.yaml``.
#. Start the ``sync_200`` service (shown with the optional ``--auth-passwd`` to bootstrap the root user)::

    python -m synapse.tools.sync_200 <sync_dirn> \
        --auth-passwd secret --offsfile <path_to_lyroffs.yaml> \
        --src <01x_telepath_url> --dest <20x_telepath_url>

#. Add the Storm service to the Cortex and use the available commands to start synchronization.
#. When ready to cut-over, and the read status is up-to-date, stop the synchronization using the ``stopsync`` command.

Cleanup
*******

After migration is fully complete, delete the now-unused directory "migration" inside the cortex directory.

Configuration Options
---------------------

For a list of boot time configuration options for the Cortex, see the listing at :ref:`autodoc-cortex-conf`.
