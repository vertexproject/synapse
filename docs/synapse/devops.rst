.. toctree::
    :titlesonly:

.. _devopsguide:

Synapse DevOps Guide
####################

General
=======

TLS/SSL Deployments
-------------------

For production deployments, it is recommended that all services use the built-in ``telepath`` SSL/TLS
protocol. You may deploy a service using TLS encryption by specifying a ``--telepath`` listen URL option, such
as ``ssl://cortex.vertex.link/``.

Under some circumstances, such as inbound DNAT networks or multi-homed hosts, it may be necessary to specify a
socket bind address that is different than the hostname. If your environment requires you to bind an address that
is different than the hostname's DNS entry, an explicit hostname query parameter may be
specified:``ssl://0.0.0.0/?hostname=cortex.vertex.link``.

The client will also need to specify an SSL/TLS ``telepath`` URL such as: ``ssl://visi:passwd@cortex.vertex.link``.

Once the ``ssl`` protocol is specified, the ``hostname``, either from a query parameter or from the URL's
network location, is used to lookup a matching ``crt`` and ``key`` file pair from your server certificate directory
located at ``~/.syn/certs/hosts``. See the following sections for how to setup server certificates.

Self-Signed Certificates using certtool
***************************************

For self-signed certificates, we need to generate a CA certificate and key as well as a server certificate and key.

The synapse ``certtool`` can be used to easily generate a CA and server certificates. For example, if we wanted
to generate a CA certificate for "vertex"::
    python -m synapse.tools.easycert --ca vertex
    key saved: /home/visi/.syn/certs/cas/vertex.key
    cert saved: /home/visi/.syn/certs/cas/vertex.crt

We can then generate a server certificate and keyfile pair and sign it with our new CA::
    python -m synapse.tools.easycert --server cortex.vertex.link --signas vertex
    key saved: /home/visi/.syn/certs/hosts/cortex.vertex.link.key
    cert saved: /home/visi/.syn/certs/hosts/cortex.vertex.link.crt

To verify the server certificate, clients will need to have the ``~/.syn/certs/cas/vertex.crt`` file in their
certificate directory.

NOTE: do not distribute the ``~/.syn/certs/cas/vertex.key`` file as that would allow regular users the ability
to sign arbitrary certificates).

CA-Signed Certificates
**********************

Any external CA may be used to sign ``telepath`` server certificates. The ``certtool`` can be used to easily
generate a certificate signing request (CSR) to be signed by an external CA or you can simply copy or link
pre-existing PEM encoded certificate files to the expected filesystem locations.

To generate a CSR using ``certtool``::
    python -m synapse.tools.easycert --csr --server cortex.vertex.link
    key saved: /home/visi/.syn/certs/hosts/cortex.vertex.link.key
    csr saved: /home/visi/.syn/certs/hosts/cortex.vertex.link.csr

You may then submit your CSR file (in this case ``~/.syn/certs/hosts/cortex.vertex.link.csr``) to your CA of choice for signing.
Once your CA returns a signed certificate in PEM format, place it in the expected location (``~/.syn/certs/hosts/cortex.vertex.link.crt`` in this example)
and it will be loaded when you start your service.

Client-Side Certificates for Authentication
*******************************************

TODO

Cortex
======

Docker Deployment
-----------------

Configuring A Mirror
--------------------

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

Axon
====

Cryotank
========

.. _index:              ../index.html
