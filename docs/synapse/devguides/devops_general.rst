General Devops
==============

.. _devops-general-backups:

Backups
-------

It is strongly recommended that users schedule regular backups of all services deployed within their **Synapse**
ecosystem. Each service can be backed up using the **Synapse** backup tool: ``synapse.tools.backup``.

The **Synapse** service architecture is designed to contain everything a service needs within the directory you
specify during service startup.  Take, for example, a **Cortex** started with::

    python -m synapse.servers.cortex /data/cortex00

The **Cortex** will be completely contained within the service working directory ``/data/cortex00``. The synapse tool
``synapse.tools.backup`` may be used to create a backup copy of this working directory which may then be restored.

It is important that you use ``synapse.tools.backup`` rather than simply copying the directory. It is important to avoid
standard file copy operations on running LMDB files due to potentially causing sparse file expansion or producing a
corrupt copy. LMDB makes use of sparse files which allocate file block storage only when the blocks are written to.
This means a file copy tool which is not sparse-file aware can inadvertently cause massive file expansion during copy.

It is also worth noting that the newly created backup is a defragmented / optimized copy of all database data
structures.  As such, we recommend occasionally scheduling a maintenance window to create a "cold backup" with the
service offline and deploy the backup copy when bringing the service back online.  Regularly performing this
"restore from cold backup" procedure can dramatically improve performance and resource utilization.

Running A Backup
****************

Continuing our previous example, running a backup is as simple as::

    python -m synapse.tools.backup /data/cortex00 /backups/cortex00_`date +%Y%m%d`

Assuming that your backup was run on ``May 19, 2020``, this would create a backup in the directory
``/backups/cortex00_20200519``.

The backup command can be run on a live service. Depending on your configuration, creating a live backup
of your service can temporarily degrade performance of the running service. As such, it may be best to schedule
backups during low utilization time windows.

Restoring From Backup
*********************

In the event that restoring from backup is necessary, simply move the service working directory and
copy a previous backup directory to the service working directory location.  From our previous example,
this would involve running the following shell commands::

    mv /data/cortex00 /data/cortex00_old
    cp -R /backups/cortex00_20200519 /data/cortex00
    python -m synapse.servers.cortex /path/to/cortex


.. _devops-general-https:

Cell HTTPS Server
-----------------

Each Synapse cell will generate and use self-signed certificates by default for its webserver. These allow a user to
quickly get started with testing HTTP interfaces on Cells, but is not recommended for a production deployment.
Each cell loads the certificate and key material from ``./sslcert.pem`` and ``./sslkey.pem``. In our Docker containers,
these would be ``/vertex/storage/sslcert.pem`` and ``/vertex/storage/sslkey.pem``.

These files can be replaced on disk with your own certificate and private key. The certifcate should be a full
certificate chain. The following Docker-Compose example shows how to map in your own TLS key material that the Cortex
webserver will use:

::

    version: '3'
    services:
      cortex:
        image: vertexproject/synapse-cortex:v2.x.x
        ports:
          # Expose 4443 to point to the Cortex HTTP server
          - "4443:4443"
        volumes:
          # Map in local Cortex dir
          - ./cortex:/vertex/storage
          # Map in ssl certs from ../certs
          - ../certs/fullchain.pem:/vertex/storage/sslcert.pem
          - ../certs/privkey.pem:/vertex/storage/sslkey.pem
        environment:
          - SYN_LOG_LEVEL=DEBUG
          - SYN_CORTEX_AUTH_PASSWD=root

.. _devops-general-telepath-tls:

Telepath TLS/SSL Deployments
----------------------------

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

Self-Signed Certificates using easycert
***************************************

For self-signed certificates, we need to generate a CA certificate and key as well as a server certificate and key.

The synapse ``easycert`` can be used to easily generate a CA and server certificates. For example, if we wanted
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

Any external CA may be used to sign ``telepath`` server certificates. The ``easycert`` can be used to easily
generate a certificate signing request (CSR) to be signed by an external CA or you can simply copy or link
pre-existing PEM encoded certificate files to the expected filesystem locations.

To generate a CSR using ``easycert``::

    python -m synapse.tools.easycert --csr --server cortex.vertex.link
    key saved: /home/visi/.syn/certs/hosts/cortex.vertex.link.key
    csr saved: /home/visi/.syn/certs/hosts/cortex.vertex.link.csr

You may then submit your CSR file (in this case ``~/.syn/certs/hosts/cortex.vertex.link.csr``) to your CA of choice for signing.
Once your CA returns a signed certificate in PEM format, place it in the expected location (``~/.syn/certs/hosts/cortex.vertex.link.crt`` in this example)
and it will be loaded when you start your service.

Client-Side Certificates for Authentication
*******************************************

To use client-side certificates for authentication, the CA certificate to use for validating client certificates
must be specified in the ``--telepath`` listen url. For example, to use the "vertex" CA certificate previously generated,
the listen url would be: ``ssl://0.0.0.0/?hostname=cortex.vertex.link&ca=vertex``.

To generate a client certificate for the user ``user@cortex.vertex.link``, ``easycert`` can be used as follows::

    python -m synapse.tools.easycert user@cortex.vertex.link --signas vertex
    cert saved: /home/cisphyx/.syn/certs/users/user@cortex.vertex.link.crt
    key saved: /home/cisphyx/.syn/certs/users/user@cortex.vertex.link.key

The user will need to add both of the generated files to their users certificate directory, located by default at ``~/.syn/certs/users``.
Once in place, the user will be able to connect to the Cortex using certificate authentication instead of a password::

    python -m synapse.tools.cmdr ssl://user@cortex.vertex.link/

.. _devops-general-performance:

Tips for Better Performance
---------------------------

The Cortex process acts as the database for all configuration and graph data.  Inasmuch, it interacts with the
operating system in similar ways as other database systems like PostgreSQL or MySQL, and recommendations for good
performance for other database systems may also apply to running a Synapse Cortex.

Database systems run best when the amount of RAM available exceeds the size of the data being stored.  Barring having
more RAM than data, the closer you can get, the better.

As the database constantly accesses persistent storage, minimizing storage latency is important for a high performance
Cortex.  Locating the Cortex on a filesystem backed to a mechanical hard drive is strongly discouraged.  For the same
reason, running the Cortex from an NFS filesystem (including NFS-based systems like AWS EFS) is discouraged.

The default settings of most Linux-based operating systems are not set for ideal performance.

Consider setting the following Linux system variables.  These can be set via /etc/sysctl.conf, the sysctl utility, or
writing to the /proc/sys filesystem.

``vm.swappiness=10``
    Reduce preference for kernel to swap out memory-mapped files.

``vm.dirty_expire_centisecs=20``
    Define "old" data to be anything changed more than 200 ms ago.

``vm.dirty_writeback_centisecs=20``
    Accelerate writing "old" data back to disk.

``vm.dirty_background_ratio=2``
    This is expressed as a percentage of total RAM in the system.  After the total amount of dirty memory exceeds this
    threshold, the kernel will begin writing it to disk in the background.  We want this low to maximize storage I/O
    throughput utilization.

    This value is appropriate for systems with 128 GiB RAM.  For systems with less RAM, this number should be larger,
    for systems with more, this number may be smaller.

``vm.dirty_ratio=4``
    This is expressed as a percentage of total RAM in the system.  After the total amount of dirty memory exceeds this
    threshold, all writes will become synchronous, which means the Cortex will "pause" waiting for the write to
    complete.  To avoid large sawtooth-like behavior, this value should be low.

    This value is appropriate for systems with 128 GiB RAM.   For systems with less RAM, this number should be larger,
    for systems with more, this number may be smaller.

    This setting is particularly important for systems with lots of writing (e.g. making new nodes), lots of RAM, and
    relatively slow storage.


.. _devops-general-migrations:

Data Migrations
---------------

In the event that a Synapse release contains a data migration for a part of the Synapse ecosystem, the Changelog will
indicate what component is being migrated and why. This will be made under the ``Automated Migrations`` header, at the
top of the changelog.

Automatic data migrations may cause additional startup times on the first boot of the version. Deployments with startup
or liveliness probes should have those disabled while this upgrade is performed to prevent accidental termination of
the relevant processes. Please ensure you have a tested backup available before applying these updates.
