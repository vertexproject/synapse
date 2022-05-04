.. toctree::
    :titlesonly:

.. _devopsguide:

Synapse Devops Guide
####################

Overview
========

Docker Images
-------------

Each Synapse service is distributed as a ``docker`` image which contains all the dependencies required to run the
service. For the open-source Synapse images, the tag ``:v2.x.x`` will always be present on the most recent supported
release. Image names are specified in each service specific section below.

Synapse services **require persistent storage**. Each ``docker`` container expects persistent storage to be available
within the directory ``/vertex/storage`` which should be a persistent mapped volume. Only one container may run from a
given volume at a time.

cell.yaml
---------

Each Synapse service has one configuration file, ``cell.yaml``, which is located in the service storage directory,
typically ``/vertex/storage/cell.yaml`` in the ``docker`` images. Configuration options are specified in YAML format
using the same syntax as their documentation, for example::

    aha:name: cortex
    aha:network: loop.vertex.local

Environment Variables
---------------------

Synapse services may also be configured using environment variables specified in their documentation. The value will
be parsed as a YAML value to allow structured data to be specified via environment variables and then subject to
normal configuration schema validation.

HTTPS Certificates
------------------

Synapse services that expose HTTPS APIs will automatically generate a self-signed certificate and key if they are not found
at ``sslcert.crt`` and ``sslkey.pem`` in the service storage directory. At any time, you can replace these self-signed
files with a certificate and key generated using :ref:`syn-tools-easycert` or generated and signed by an external CA.

Common Devops Tasks
===================

.. _devops-task-backup:

Generating a Backup
-------------------

.. note::
    If you are a Synapse Enterprise customer you should deploy the Synapse-Backup_ Advanced Power-Up.

It is strongly recommended that users schedule regular backups of all services deployed within their Synapse
ecosystem. Each service must be backed up using either the **live** backup tool ``synapse.tools.livebackup`` or
the offline backup tool ``synapse.tools.backup``.

For a production deployment similar to the one described in the :ref:`deploymentguide` you can easily run
the backup tool by executing a shell **inside** the docker container.  For example, if we were generating
a backup of the Cortex we would::

    cd /srv/syn/00.cortex
    docker-compose exec 00.cortex /bin/bash

And from the shell executed within the container::

    python -m synapse.tools.livebackup

This will generate a backup in a time stamp directory similar to::

    /vertex/storage/backups/20220422094622

Once the backup directory is generated you may exit the docker shell and the backup will be accessible from
the **host** file system as::

    /srv/syn/00.cortex/storage/backups/20220422094622

At this point it is safe to use standard tools like ``mv``, ``tar``, and ``scp`` on the backup folder::

    mv /srv/syn/00.cortex/storage/backups/20220422094622 /nfs/backups/00.cortex/

.. note::

    It is important that you use ``synapse.tools.livebackup`` to ensure a transactionally consistant backup.

It is also worth noting that the newly created backup is a defragmented / optimized copy of the databases.
We recommend occasionally scheduling a maintenance window to create a "cold backup" using the offline
``synapse.tools.backup`` command with the service offline and deploy the backup copy when bringing the service
back online.  Regularly performing this "restore from cold backup" procedure can dramatically improve performance
and resource utilization.

.. _devops-task-restore:

Restoring a Backup
------------------

In the hopefully unlikely event that you need to restore a **Synapse** service from a backup the process is fairly
simple. For a production deployment similar to the one described in :ref:`deploymentguide` and assuming we moved
the backup file as described in :ref:`devops-task-backup`::

    cd /srv/syn/00.cortex
    docker-compose down
    mv storage storage.broken
    cp -R /nfs/backups/00.cortex/20220422094622 storage
    docker-compose up -d

Then you can tail the logs to ensure the service is fully restored::

    cd /srv/syn/00.cortex
    docker-compose logs -f

.. _devops-task-promote:

Promoting a Mirror
------------------

.. note::
    To gracefully promote a mirror to being the leader, your deployment must include AHA based service discovery
    as well as use TLS client-certificates for service authentication.

To gracefully promote a mirror which was deployed in a similar fashion to the one described in :ref:`deploymentguide`
you can use the built-in promote tool ``synapse.tools.promote``. Begin by executing a shell within the mirror container::

    cd /srv/syn/01.cortex
    docker-compose exec 01.cortex /bin/bash

And from the shell executed within the container::

    python -m synapse.tools.promote

Once completed, the previous leader will now be configured as a follower of the newly promoted leader.

.. note::

    If you are promoting the follower due to a catastrophic failure of the previous leader, you may use the
    command ``synapse.tools.promote --failure`` to force promotion despite not being able to carry out a graceful
    handoff. It is **critcal that you not bring the previous leader back online** once this has been done. To regain
    redundancy, deploy a new mirror from backup using the AHA provisioning process described in the :ref:`deploymentguide`.

.. _devops-task-update:

Updating Services
-----------------

Updating a Synapse service requires pulling the newest docker image and restarting the container. For Synapse
services which have mirrors deployed, you must ensure that the mirrors are updated first so that any newly introduced
change messages can be consumed. If you are using a mirrors-of-mirrors tree topology, the update should be deployed in
a "leafs first" order.

Continuing with our previous example from the :ref:`deploymentguide` we would update the mirror ``01.cortex`` first::

    cd /srv/syn/01.cortex
    docker-compose pull
    docker-compose down
    docker-compose up -d

After ensuring that the mirror has come back online and is fully operational, we will update the leader which may
include a :ref:`datamigration` while it comes back online::

    cd /srv/syn/00.cortex
    docker-compose pull
    docker-compose down
    docker-compose up -d

.. note::

    Once a Synapse service update has been deployed, you may **NOT** revert to a previous version!

.. _datamigration:

Data Migration
~~~~~~~~~~~~~~

When a Synapse release contains a data migration for a part of the Synapse data model, the Changelog will indicate
what component is being migrated and why. This will be made under the ``Automated Migrations`` header, at the
top of the changelog.

Automatic data migrations may cause additional startup times on the first boot of the version. When beginning a data
migration, a WARNING level log message will be printed for each stage of the migration::

     beginning model migration -> (0, 2, 8)

Once complete, a WARNING level log message will be issued::

    ...model migrations complete!

.. note::

    Please ensure you have a tested backup available before applying these updates.

.. _modelflagday:

Model Flag Day
~~~~~~~~~~~~~~

Periodically, a Synapse release will include small, but technically backward incompatible, changes to the data model.
All such migrations will include a ``Model Flag Day`` heading in the Changelog with a detailed description
of each change to the data model. Additionally, the release will execute an in-place migration to modify data to confirm
with model updates. If necessary, any data that can not be migrated automatically will be saved to a location documented
within the detailed description.

When we release a Synapse version containing a ``Model Flag Day`` update, we will simultaneously release updates to any
effected Power-Ups.

Examples of potential ``Model Flag Day`` changes:

    * Removing a previously deprecated property
    * Specifying a more specific type for a property to allow pivoting
    * Tightening type normalization constraints of a property

It is **highly** recommended that production deployments have a process for testing custom storm code in a staging
environment to help identify any tweaks that may be necessary due to the updated data model.

.. note::

    Please ensure you have a tested backup available before applying these updates.

.. _devops-task-logging:

Configure Logging
-----------------

Synapse services support controlling log verbosity via the ``SYN_LOG_LEVEL`` environment variable. The following values
may be used: ``CRITCAL``, ``ERROR``, ``WARNING``, ``INFO``, and ``DEBUG``. For example::

    SYN_LOG_LEVEL=INFO

To enable JSON structured logging output suitable for ingest and indexing, specify the following environment variable
to the ``docker`` container::

    SYN_LOG_STRUCT=true

These structured logs are designed to be easy to ingest into third party log collection platforms. They contain the log
message, level, time, and metadata about where the log message came from::

    {
      "message": "log level set to INFO",
      "logger": {
        "name": "synapse.lib.cell",
        "process": "MainProcess",
        "filename": "common.py",
        "func": "setlogging"
      },
      "level": "INFO",
      "time": "2021-06-28 15:47:54,825"
    }

When exceptions are logged with structured logging, we capture additional information about the exception, including the
entire traceback. In the event that the error is a Synapse Err class, we also capture additional metadata which was
attached to the error. In the following example, we also have the query text, username and user iden available in the
log message pretty-printed log message::

    {
      "message": "Error during storm execution for { || }",
      "logger": {
        "name": "synapse.lib.view",
        "process": "MainProcess",
        "filename": "view.py",
        "func": "runStorm"
      },
      "level": "ERROR",
      "time": "2021-06-28 15:49:34,401",
      "err": {
        "efile": "coro.py",
        "eline": 233,
        "esrc": "return await asyncio.get_running_loop().run_in_executor(forkpool, _runtodo, todo)",
        "ename": "forked",
        "at": 1,
        "text": "||",
        "mesg": "No terminal defined for '|' at line 1 col 2.  Expecting one of: #, $, (, *, + or -, -(, -+>, -->, ->, :, <(, <+-, <-, <--, [, break, command name, continue, fini, for, function, if, init, property name, return, switch, while, whitespace or comment, yield, {",
        "etb": ".... long traceback ...",
        "errname": "BadSyntax"
      },
      "text": "||",
      "username": "root",
      "user": "3189065f95d3ab0a6904e604260c0be2"
    }

.. _devops-task-performance:

Performance Tuning
------------------

Performance tuning Synapse services is very similar to performance tuning other database systems like PostgreSQL or MySQL.
Recommendations for good performance for other database systems may also apply to Synapse services. Database systems
run best when given as much RAM as possible. Under **ideal** circumstances, the amount of RAM exceeds the total database
storage size.

Minimizing storage latency is important for a high performance Synapse service. Locating the storage volume backed by a
mechanical hard drive is **strongly** discouraged.  For the same reason, running Synapse services from an NFS file system
(including NFS-based systems like AWS EFS) is **strongly** discouraged.

The default settings of most Linux-based operating systems are not set for ideal performance.

Consider setting the following Linux system variables.  These can be set via /etc/sysctl.conf, the sysctl utility, or
writing to the /proc/sys file system.

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

.. _devops-task-users:

Managing Users and Roles
------------------------

Adding Users
~~~~~~~~~~~~

Managing users and service accounts in the Synapse ecosystem is most easily accomplished using the ``moduser`` tool
executed from **within** the service ``docker`` container. In this example we add the user ``visi``
as an admin user to the Cortex by running the following command from **within the Cortex container**::

    python -m synapse.tools.moduser --add --admin visi

If the deployment is using AHA and TLS client certificates and the user will be connecting via the Telepath API using the
:ref:`syn-tools-storm` CLI tool, will will also need to provision a user TLS certificate for them. This can be done using
the ``synapse.tools.aha.provision.user`` command from **within the AHA container**::

    python -m synapse.tools.aha.provision.user visi

Which will produce output similar to::
    
    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

.. note::
    The enrollment URL may only be used once. It should be given to the user using a secure messaging system
    to prevent an attacker from using it before the user.

Once the one-time enrollment URL has been passed along to the user, the **user must run an enrollment command** to configure
their environment to use the AHA server and generate a user certificate from the host they will be using to run the Storm CLI::

    python -m synapse.tools.enroll ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

Once they are enrolled, the user can connect using the Telepath URL ``aha://cortex.<yournetwork>``::

    python -m synapse.tools.storm aha://cortex.<yournetwork>

.. _devops-task-aha:

Updating to AHA and Telepath TLS
--------------------------------

If you have an existing deployment which didn't initially include AHA and Telepath TLS, it can easily be deployed and
configured after the fact.  However, as services move to TLS it will **break existing telepath URLs** that may be in
use, so you should test the deployment before updating your production instance.

To move to AHA, first deploy an AHA service as discussed in the :ref:`deploymentguide`. For each service, you may then
run the ``provision`` tool as described and add the ``aha:provision`` configuration option to the ``cell.yaml`` or use
the service specific environment variable to prompt the service to provision itself.

.. note::
    It is recommended that you name your services with leading numbers to prepare for an eventual mirror deployment.

For example, to add an existing Axon to your new AHA server, you would execute the following from **inside the AHA container**::

    python -m synapse.tools.aha.provision 00.axon

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

Then add the following entry to the Axon's ``cell.conf``::

    aha:provision: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

Or add the following environment variable to your orchestration::

    SYN_AXON_AHA_PROVISION=ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

Then restart the Axon container. As it restarts, the service will generate user and host certificates and update it's
``cell.yaml`` file to include the necessary AHA configuration options. The ``dmon:listen`` option will be updated
to reflect the use of SSL/TLS and the requirement to use client certificates for authentication. As additional services
are provisioned, you may update the URLs they use to connect to the Axon to ``aha://axon...``.

Synapse Services
================

.. _devops-svc-ahacell:

AHA
---

The AHA service provides service discovery, provisioning, graceful mirror promotion, and certificate authority
services to the other Synapse services. For a step-by-step guide to deploying an AHA instance, see the
:ref:`deploymentguide`. We will use ``<yournetwork>`` to specify locations where the value should be replaced with
your chosen AHA network name.

Docker Image: ``vertexproject/synapse-aha:v2.x.x``

**Configuration**

A typical AHA deployment requires some initial configuration options. At a minimum, you must specify the following::

    aha:name: aha
    aha:network: <yournetwork>
    dmon:listen: ssl://aha.<yournetwork>&ca=<yournetwork>

To enable provisioning using AHA you must specify an alternate listener such as::

    provision:listen: tcp://aha.<yournetwork>:27272

.. note::
    The network connection from a Synapse service to the AHA service must NOT be passing through a Network Adress
    Translation (NAT) device.

For the full list supported options, see the :ref:`autodoc-conf-aha`.

**Using Aha with Custom Client Code**

.. highlight:: python3

Loading the known AHA resolvers for use with custom python clients can be easily
accomplished using the ``withTeleEnv()`` context manager::

    import synapse.telepath as s_telepath

    async def main(argv):

        # This context manager loads telepath.yaml
        async with s_telepath.withTeleEnv():

            async with await s_telepath.openurl(argv[0]) as proxy:

                # call service provided telepath APIs

                info = await proxy.getCellInfo()
                print(repr(info))
                
        return 0

    sys.exit(asyncio.run(main(sys.argv[1:]))))

.. _devops-svc-axon:

Axon
----

.. note::
    If you are a Synapse Enterprise customer you should consider deploying the Synapse-S3_ Axon.

The Axon service provides binary / blob storage inside of the Synapse ecosystem. Binary objects are indexed based
on the SHA-256 hash so that storage of the same set of bytes is not duplicated. The Axon exposes a set of Telepath / HTTP
APIs that can be used to upload, download, and check for the existence of a binary blob.  For a step-by-step guide to
deploying an Axon, see the :ref:`deploymentguide`.

Docker Image: ``vertexproject/synapse-axon:v2.x.x``

.. note::

    For ease of use in simple deployments, the Cortex contains an embedded Axon instance.  For production deployments
    it is **highly** recommended that you install it as a separated service to help distribute load and allow direct
    access by other Advanced Power-Ups.

**Configuration**

A typical Axon deployment does not require any additional configuration. For the full list supported options, see the
:ref:`autodoc-conf-axon`.

**Permissions**

*axon*
    Controls access to all ``axon.*`` permissions.

*axon.get*
    Controls access to retrieve a binary blob from the Axon based on the SHA256 hash.

*axon.has*
    Controls access to check if bytes are present and return sizes based on the SHA256 hash.

*axon.upload*
    Controls access to upload a binary blob to the Axon.

For example, to allow the user ``visi`` to upload, download, and confirm files you would execute the following command
from **inside the Axon container**::

    python -m synapse.tools.moduser --add visi --allow axon

.. _devops-svc-jsonstorcell:

JSONStor
--------

The JSONStor is a utility service that provides a mechanism for storing and retrieving arbitrary JSON objects using
a hierarchical naming system. It is commonly used to store user preferences, cache API query responses, and hold
data that is not part of the :ref:`_userguide_datamodel`. For an example of deploying a JSONStor, see the :ref:`deploymentguide`.

Docker Image: ``vertexproject/synapse-jsonstor:v2.x.x``

.. note::

    For ease of use in simple deployments, the Cortex contains an embedded JSONStor instance.  For production deployments
    it is **highly** recommended that you install it as a separated service to help distribute load and allow direct
    access by other Advanced Power-Ups.

**Configuration**

A typical JSONStor deployment does not require any additional configuration. For the full list supported options, see the
:ref:`autodoc-conf-jsonstor`.

.. _devops-svc-cortex:

Cortex
------

A Cortex is the hypergraph_ database and main component of the Synapse service architecture. The Cortex is also where the
Storm query language runtimes and execute where all automation and enrichment occurs. For a step-by-step guide to deploying
a Cortex, see the :ref:`deploymentguide`.

Docker Image: ``vertexproject/synapse-cortex:v2.x.x``

**Configuration**

Many of the configurations and permissions managed within the Cortex are the responsibility of the global admin rather than
the devops team. See the :ref:`adminguide` for details on global admin tasks and details.

The Cortex can be configured to log Storm queries executed by users. This is done by setting the ``storm:log`` and
``storm:log:level`` configuration options. The ``storm:log:level`` option may be one of ``DEBUG``, ``INFO`` , ``WARNING``,
``ERROR``, ``CRITICAL`` This allows an organization to set what log level their Storm queries are logged at.

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

This logging does interplay with the underlying log configuration ( :ref:`devops-task-logging` ). The
``storm:log:level`` value must be greater than or equal to the ``SYN_LOG_LEVEL``, otherwise the Storm log will
not be emitted.

For the full list supported options, see the :ref:`autodoc-conf-cortex`.

Devops Details
==============

Orchestration
-------------

.. include:: devguides/orch_hashistack.rst
.. include:: devguides/orch_kubernetes.rst

.. _autodoc-conf-aha:

AHA Configuration Options
-------------------------
.. include:: autodocs/conf_ahacell.rst

.. _autodoc-conf-axon:

Axon Configuration Options
--------------------------
.. include:: autodocs/conf_axon.rst

.. _autodoc-conf-jsonstor:

JSONStor Configuration Options
------------------------------
.. include:: autodocs/conf_jsonstorcell.rst

.. _autodoc-conf-cortex:

Cortex Configuration Options
----------------------------
.. include:: autodocs/conf_cortex.rst

.. _index:              ../index.html
.. _Synapse-Backup: ../projects/backup/en/latest/
.. _Synapse-S3: ../projects/s3/en/latest/
.. _hypergraph: https://en.wikipedia.org/wiki/Hypergraph
