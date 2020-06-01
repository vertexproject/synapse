.. toctree::
    :titlesonly:

.. _devopsguide:

Synapse DevOps Guide
####################

TBD - See :ref:`quickstart` for current docs.

Cortex
======

Docker Deployment
-----------------

Configuring A Mirror
--------------------

.. _200_migration:

0.1.x to 2.0.0 Migration
------------------------

Two tools have been created to execute migration of an ``0.1.x`` Cortex to ``2.0.0``:

* ``migrate_200`` migrates all data from the source to a new destination ``0.2.x`` Cortex.
* ``sync_200`` allows for a backup to be migrated and then synchronized with a running Cortex to facilitate minimal downtime.

Migration Quickstart
********************

.. note::

    The duration of migration is proportional to the amount of data stored, and is highly dependant on
    the available system resources (especially disk I/O). For larger Cortexes it is recommended to
    run migration on hardware without other highly active processes.

#. Update the source to the latest Synapse ``0.1.x`` release.
#. Create a backup of the ``0.1.x`` Cortex.
#. In a new location install Synapse ``2.0.x`` and copy any custom modules / configurations present in the ``0.1.x`` environment.
#. Start migration using the backup as the source::

    python -m synapse.tools.migrate_200 --src <backup_cortex_dirn> --dest <new_20x_dirn>

#. Inspect the migration output for any errors that may require action (see :ref:`migration-errors` for details).
#. Startup the ``2.0.x`` Cortex.

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

* A custom form/property may not have been properly loaded into the ``0.2.x`` environment.
* The node may not have been properly updated in a prior ``0.1.x`` datamodel migration and therefore no longer exists.

``Normed form val does not match inbound`` or ``Calculated buid does not match inbound``

* Is likely due to a node that was not properly re-normalized after a prior Synapse update.

Post-migration Synchronization
******************************

After migration, the ``sync_200`` service can be used to push post-backup changes to the migrated ``0.2.x`` Cortex,
and keep it updated until cut-over. ``sync_200`` uses splices to translate the changes, and therefore they must
be enabled on the source Cortex. In order to control and monitor synchronization, ``sync_200`` can be added as a Storm service.

When synchronization is started the service will enable "migration mode" on the destination ``0.2.x`` Cortex, which
prevents cron jobs and triggers from running.  Migration mode will then be disabled when the synchronization is
stopped or when the Cortex is restarted.

#. Complete migration, including starting up the ``2.0.x`` Cortex.
#. Locate the saved splice offset file from migration at ``<new_20x_dirn>/migration/lyroffs.yaml``.
#. Start the ``sync_200`` service (shown with the optional ``--auth-passwd`` to bootstrap the root user)::

    python -m synapse.tools.sync_200 <sync_dirn> \
        --auth-passwd secret --offsfile <path_to_lyroffs.yaml> \
        --src <01x_telepath_url> --dest <02x_telepath_url>

#. Add the Storm service to the Cortex and use the available commands to start synchronization.
#. When ready to cut-over, and the read status is up-to-date, stop the synchronization using the ``stopsync`` command.

Axon
====

Cryotank
========

.. _index:              ../index.html
