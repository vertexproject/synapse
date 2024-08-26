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
at ``sslcert.pem`` and ``sslkey.pem`` in the service storage directory. At any time, you can replace these self-signed
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
    docker compose exec 00.cortex /bin/bash

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

.. note::

    When taking a backup of a service, the backup is written by the service locally to disk. This may take
    up storage space equal to the current size of the service. If the service does not have the ``backup:dir`` option
    configured for a dedicated backup directory (or volume), this backup is made to ``/vertex/storage/backups`` by
    default. If the volume backing ``/vertex/storage`` reaches a maximum capacity, the backup process will fail.

    To avoid this from being an issue, when using the default configuration, make sure services do not exceed 50% of
    their storage utilization. For example, a Cortex that has a size of 32GB of utilized space may take up 32GB
    during a backup. The volume backing ``/vertex/storage`` should be at least 64GB in size to avoid issues taking
    backups.

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
    docker compose down
    mv storage storage.broken
    cp -R /nfs/backups/00.cortex/20220422094622 storage
    docker compose up -d

Then you can tail the logs to ensure the service is fully restored::

    cd /srv/syn/00.cortex
    docker compose logs -f

.. _devops-task-promote:

Promoting a Mirror
------------------

.. note::
    To gracefully promote a mirror to being the leader, your deployment must include AHA based service discovery
    as well as use TLS client-certificates for service authentication.

To gracefully promote a mirror which was deployed in a similar fashion to the one described in :ref:`deploymentguide`
you can use the built-in promote tool ``synapse.tools.promote``. Begin by executing a shell within the mirror container::

    cd /srv/syn/01.cortex
    docker compose exec 01.cortex /bin/bash

And from the shell executed within the container::

    python -m synapse.tools.promote

Once completed, the previous leader will now be configured as a follower of the newly promoted leader.

.. note::

    If you are promoting the follower due to a catastrophic failure of the previous leader, you may use the
    command ``synapse.tools.promote --failure`` to force promotion despite not being able to carry out a graceful
    handoff. It is **critical that you not bring the previous leader back online** once this has been done. To regain
    redundancy, deploy a new mirror using the AHA provisioning process described in the :ref:`deploymentguide`.

.. _devops-task-update:

Updating Services
-----------------

Updating a Synapse service requires pulling the newest docker image and restarting the container. For Synapse
services which have mirrors deployed, you must ensure that the mirrors are updated first so that any newly introduced
change messages can be consumed. If you are using a mirrors-of-mirrors tree topology, the update should be deployed in
a "leafs first" order.

.. note::

    A service mirror will enter into read-only mode if they detect that their leader is a higher version than they are.

Continuing with our previous example from the :ref:`deploymentguide` we would update the mirror ``01.cortex`` first::

    cd /srv/syn/01.cortex
    docker compose pull
    docker compose down
    docker compose up -d

After ensuring that the mirror has come back online and is fully operational, we will update the leader which may
include a :ref:`datamigration` while it comes back online::

    cd /srv/syn/00.cortex
    docker compose pull
    docker compose down
    docker compose up -d

.. note::

    Once a Synapse service update has been deployed, you may **NOT** revert to a previous version! Reverting services
    to prior versions is not supported.

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

Synapse Services may have additional data migrations applied during updates as well. These will always be noted in the
Changelog for an individual service.

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

.. _devops-task-low-downtime-updates:

Low Downtime Updates
~~~~~~~~~~~~~~~~~~~~

For services that are deployed in a mirror configuration, service upgrades can be performed with minimal downtime.

#. Update the service mirrors.
#. Use the Synapse ``synapse.tools.promote`` tool to promote a service as a mirror. This will start any data migrations
   which need to happen. Cortex data model migrations will be checked and executed as well.
#. Update the old service leader.

Continuing with our previous example from the :ref:`deploymentguide` we would update the mirror ``01.cortex`` first::

    cd /srv/syn/01.cortex
    docker compose pull
    docker compose down
    docker compose up -d

Then we would promote the mirror to being a leader. This promotion will also start any data migrations that need to
be performed::

    cd /srv/syn/01.cortex
    docker compose exec 01.cortex python -m synapse.tools.promote

After the promotion is completed, the previous leader can be updated. Since it is now mirroring ``01.cortex``, it will
start to replicate any changes from the leader once it comes online, including any data migrations that are being
performed::

    cd /srv/syn/00.cortex
    docker compose pull
    docker compose down
    docker compose up -d

Restarting the old leader ensures that any services previously talking to ``aha://cortex...`` will automatically
reconnect to the new leader.

Update Sequencing
~~~~~~~~~~~~~~~~~

.. note::

    Some of the services mentioned here are part of our commercial offering.

When deploying updates, we suggest deploying updates to the entire ecosystem in the following order:

#. AHA, Axon, and the JSONStor services:

    This order ensures that the AHA service, Axon, and JSONStor services are all updated first.

#. Cortex:

    Next, the Cortex should be updated. It may use new or updated APIs from the previous services.

#. Search and Metrics services:

    The Search and Metrics updates, in turn, may use new or updated APIs from the Cortex.

#. Optic:

    The Optic service may use new or updated APIs from the previous services. Optic has its own version
    requirements for communicating with the Cortex and will not work if that version requirement is unmet.

#. Any remaining Advanced Power-Ups:

    Remaining Advanced Power-Ups would provide new or updated functionality to other services.

#. Any Rapid Power-Ups:

    Some Rapid Power-Ups may integrate with Advanced Power-Ups to provide additional functionality. Having the Advanced
    Power-Ups updated ensures that any optional dependencies that the Rapid Power-Ups may have would be met.

Updating Rapid Power-Ups
~~~~~~~~~~~~~~~~~~~~~~~~

When updating Rapid Power-Ups, the ``vertex.pkg.upgrade`` command can be used to upgrade all installed packages, or to
upgrade individual packages.

If you are using the Optic UI for managing Rapid Power-Ups, you can use it to review available upgrades and review
their changelogs prior to upgrading. It can also be used to update all available Rapid Power-Ups for you at once.

Release Cadence
~~~~~~~~~~~~~~~

Vertex does not follow a strict release cadence for Synapse, Advanced Power-Ups, or Rapid Power-Ups. As we develop new
functionality and address issues, we will release new versions of Synapse and Power-Ups on an as-needed basis.
We recommend that users and organizations adopt an upgrade cycle that works for their operational needs.

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

Custom date formatting strings can also be provided by setting the ``SYN_LOG_DATEFORMAT`` string. This is expected to be a
strftime_ format string. The following shows an example of setting this value::

    SYN_LOG_DATEFORMAT="%d%m%Y %H:%M:%S"

produces the following output::

    28062021 15:48:01 [INFO] log level set to DEBUG [common.py:setlogging:MainThread:MainProcess]

This will also be used to format the ``time`` key used for structured logging.

.. warning::
    Milliseconds are not available when using the date formatting option. This will result in a loss of precision for
    the timestamps that appear in log output.

.. _devops-task-diskfree:

Configure Free Space Requirement
--------------------------------

To avoid the risk of data corruption due to lack of disk space, Synapse services periodically
check the amount of free space available and will switch to read-only mode if they are below
a minimum threshold. This threshold can be controlled via the ``limit:disk:free`` configuration
option, and is set to 5% free space by default.

If the available free space goes below the minimum threshold, the service will continue
the free space checks and re-enable writes if the available space returns above the
threshold.

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

.. _devops-task-onboot-optimize:

Optimize Databases
------------------

As noted in :ref:`devops-task-backup`, restoring a service from a backup will result in
the service having a defragmented / optimized copy of its databases. An alternative method
for optimizing the databases in place is by using the ``onboot:optimize`` configuration
option. Setting ``onboot:optimize`` to ``true`` will delay startup to optimize LMDB 
databases during boot to recover free space and increase performance. Depending on
the amount of activity since the last time the databases were optimized, this process
may take a significant amount of time. To reduce downtime during this process,
deployments with mirrors are encouraged to use a strategy like that described in
:ref:`devops-task-low-downtime-updates` to first optimize a mirror, then promote that mirror
to being the leader and optimizing the old service leader.

After the optimization process is completed, the ``onboot:optimize`` option can be set
back to ``false``. It is not necessary to optimize the databases on every boot of a
service, but regularly scheduling an optimization pass based on the write activity of
the service will help ensure optimal performance.

.. note::

    During the optimization process, the service will make an optimized copy of each
    LMDB database used by the service which will then be atomically swapped into place
    of the existing database. As a result, an amount of free space equal to the size of
    the largest database will be required during the optimization.

.. note::

    Though not encouraged, it is safe to shutdown a service during the optimization
    process. Progress on the LMDB database being optimized at the time of shutdown will be lost.

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
:ref:`syn-tools-storm` CLI tool, will also need to provision a user TLS certificate for them. This can be done using
the ``synapse.tools.aha.provision.user`` command from **within the AHA container**::

    python -m synapse.tools.aha.provision.user visi

Which will produce output similar to::
    
    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

.. note::
    The enrollment URL may only be used once. It should be given to the user using a secure messaging system
    to prevent an attacker from using it before the user.

Once the one-time enrollment URL has been passed along to the user, the **user must run an enrollment command** to configure
their environment to use the AHA server and generate a user certificate from the host they will be using to run the Storm CLI::

    python -m synapse.tools.aha.enroll ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

Once they are enrolled, the user can connect using the Telepath URL ``aha://cortex.<yournetwork>``::

    python -m synapse.tools.storm aha://cortex.<yournetwork>

.. _ devops-task-users-password:

Managing Password Policies
~~~~~~~~~~~~~~~~~~~~~~~~~~

Services can be configured with password policies. These can be used to define the complexity of a password, the number
of allowed login attempts, and the number of previous passwords to check against. This is configured by setting the
``auth:passwd:policy`` configuration value for the service, with the desired policy settings. The policy object
accepts the following keys:

``attempts``
    Maximum number of incorrect attempts before locking user account. This is an integer value.

``previous``
    Number of previous passwords to disallow. This is an integer value.

``complexity``
    The complexity key must be set to an object. It can have the following keys:

    ``length``
        Minimum password character length. This is an integer value with a minimum value of 1.

    ``sequences``
        Maximum sequence length in a password. Sequences can be letters or numbers, forward or reverse. This is an
        integer value with a minimum value of 2.

    ``upper:count``
        The minimum number of uppercase characters required in password. This is an integer value.

    ``upper:valid``
        All valid uppercase characters. This defaults to a string of uppercase ASCII characters. This can be set to
        a null value to disable any checking of the uppercase characters rules.

    ``lower:count``
        The minimum number of lowercase characters required in password. This is an integer value.

    ``lower:valid``
        All valid lowercase characters. This defaults to a string of lowercase ASCII characters. This can be set to
        a null value to disable any checking of the lowercase character rules.

    ``special:count``
        The minimum number of special characters required in password. This is an integer value.

    ``special:valid``
        All valid special characters. This defaults to a string of ASCII punctuation characters. This can be set to
        a null value to disable any checking of the special characters rules.

    ``number:count``
        The minimum number of digit characters required in password. This is an integer value.

    ``number:valid``
        All valid digit characters. This defaults to a string of ASCII number characters. This can be set to
        a null value to disable any checking of the number character rules.

The following example shows setting a password policy on the Cortex with the following policy:

* Maximum of three failed password login attempts before locking.

* Keep the previous two passwords to prevent password reuse.

* Complexity rules:

    * Require at least 12 total characters.

    * Disallow sequences of more than 3 characters in a row.

    * Require at least two uppercase characters.

    * Require at least two lowercase characters.

    * Specify a custom set of lowercase characters to check against (ASCII & some unicode characters).

    * Require at least two special characters.

    * Require at least two numbers.

The following Compose file shows using the policy:

::

    services:
      00.cortex:
        user: "999"
        image: vertexproject/synapse-cortex:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
            - ./storage:/vertex/storage
        environment:
            SYN_CORTEX_AXON: aha://axon...
            SYN_CORTEX_JSONSTOR: aha://jsonstor...
            SYN_CORTEX_AUTH_PASSWD_POLICY: '{"complexity": {"length": 12, "sequences": 3, "upper:count": 2, "lower:count": 2, "lower:valid": "abcdefghijklmnopqrstuvwxyzαβγ", "special:count": 2, "number:count": 2}, "attempts": 3, "previous": 2}'

Attempting to set a user password which fails to meet the complexity requirements would produce an error::

    storm> auth.user.mod lowuser --passwd hehe
    ERROR: Cannot change password due to the following policy violations:
      - Password must be at least 12 characters.
      - Password must contain at least 2 uppercase characters, 0 found.
      - Password must contain at least 2 special characters, 0 found.
      - Password must contain at least 2 digit characters, 0 found.
    complete. 0 nodes in 146 ms (0/sec).


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

.. note::
    When specifying a connection string using AHA, you can append a ``mirror=true`` parameter to the connection string
    (e.g. ``aha://cortex...?mirror=true``) to cause AHA to prefer connecting to a service mirror rather than the leader
    (if mirrors are available).

Deployment Options
------------------

The following are some additional deployment options not covered in the :ref:`deploymentguide`.

.. note::
  These examples assume the reader has reviewed and understood the Synapse Deployment Guide.


Telepath Listening Port
~~~~~~~~~~~~~~~~~~~~~~~

If you need to deploy a service to have Telepath listen on a specific port, you can use the provision tool to specify
the port to bind. This example will show deploying the Axon to a specific Telepath listening port.

**Inside the AHA container**

Generate a one-time use provisioning URL, with the ``--dmon-port`` option::

    python -m synapse.tools.aha.provision.service --dmon-port 30001 01.axon

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/01.axon/storage
    chown -R 999 /srv/syn/01.axon/storage

Create the ``/srv/syn/01.axon/docker-compose.yaml`` file with contents::

    services:
      01.axon:
        user: "999"
        image: vertexproject/synapse-axon:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
            - ./storage:/vertex/storage
        environment:
            # disable HTTPS API for now to prevent port collisions
            - SYN_AXON_HTTPS_PORT=null
            - SYN_AXON_AHA_PROVISION=ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

After starting the service, the Axon will now be configured to bind its Telepath listening port to 30001. This can be
seen in the services ``cell.yaml`` file.

  ::

    ---
    aha:name: 01.axon
    aha:network: <yournetwork>
    aha:provision: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>
    aha:registry:
    - ssl://root@aha.<yournetwork>
    aha:user: root
    dmon:listen: ssl://0.0.0.0:30001?hostname=01.axon.<yournetwork>&ca=<yournetwork>
    ...

HTTPS Listening Port
~~~~~~~~~~~~~~~~~~~~

If you need to deploy a service to have HTTPs listen on a specific port, you can use the provision tool to specify
the port to bind. This example will show deploying the Cortex to a specific HTTPS listening port.

**Inside the AHA container**

Generate a one-time use provisioning URL, with the ``--https-port`` option::

    python -m synapse.tools.aha.provision.service --https-port 8443 02.cortex

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/02.cortex/storage
    chown -R 999 /srv/syn/02.cortex/storage

Create the ``/srv/syn/01.axon/docker-compose.yaml`` file with contents::

    services:
      02.cortex:
        user: "999"
        image: vertexproject/synapse-axon:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
            - ./storage:/vertex/storage
        environment:
            - SYN_CORTEX_AHA_PROVISION=ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

After starting the service, the Cortex will now be configured to bind its HTTPS listening port to 8443. This can be
seen in the services ``cell.yaml`` file.

  ::

    ---
    aha:name: 02.cortex
    aha:network: <yournetwork>
    aha:provision: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>
    aha:registry:
    - ssl://root@aha.<yournetwork>
    aha:user: root
    dmon:listen: ssl://0.0.0.0:0?hostname=02.cortex.<yournetwork>&ca=<yournetwork>
    https:port: 8443
    ...


.. _devops-task-nexustrim:

Trimming the Nexus Log
----------------------

The Nexus log can be trimmed to reduce the storage size of any Synapse Service that has Nexus logging enabled.
This is commonly done before taking backups to reduce to their size.

For a Cortex **without** any mirrors, this is best accomplished in Storm via the following query::

    $lib.cell.trimNexsLog()

The Storm API call will rotate the Nexus log and then delete the older entries.

If the Cortex is mirrored, a list of Telepath URLs of all mirrors must be provided.
This ensures that all mirrors have rotated their Nexus logs before the cull operation is executed.

.. warning::
    If this list is ommitted, or incorrect, the mirrors may become de-synchronized
    which will require a re-deployment from a backup of the upstream.

The Telepath URLs can be provided to the Storm API as follows::

    $mirrors = ("aha://01.cortex...", "aha://02.cortex...")
    $lib.cell.trimNexsLog(consumers=$mirrors)

.. _devops-deprecation-warnings:

Viewing Deprecation Warnings
----------------------------

When functionality in Synapse is deprecated, it is marked with the standard Python warnings_ mechanism to note
that it is deprecated. Deprecated functionality is also noted in service changelogs as well. To view these warnings
in your environment, you can set the ``PYTHONWARNINGS`` environment variable to display them.
The following shows this being enabled for a Cortex deployment::

    services:
      00.cortex:
        user: "999"
        image: vertexproject/synapse-cortex:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
            - ./storage:/vertex/storage
        environment:
            - SYN_CORTEX_AXON=aha://axon...
            - SYN_CORTEX_JSONSTOR=aha://jsonstor...
            - PYTHONWARNINGS=default::DeprecationWarning:synapse.common

With this set, our deprecation warnings are emitted the first time the deprecated functionality is used. For example,
if a remote caller uses the ``eval()`` API on a Cortex, it would log the following message::

    /usr/local/lib/python3.8/dist-packages/synapse/common.py:913: DeprecationWarning: "CoreApi.eval" is deprecated in 2.x and will be removed in 3.0.0
      warnings.warn(mesg, DeprecationWarning)

This would indicate the use of a deprecated API.

Entrypoint Hooking
------------------

Synapse service containers provide two ways that users can modify the container startup process, in order to execute
their own scripts or commands.

The first way to modify the startup process is using a script that executes before services start. This can be
configured by mapping in a file at ``/vertex/boothooks/preboot.sh`` and making sure it is marked as an executable.
If this file is present, the script will be executed prior to booting the service. If this does not return ``0``, the
container will fail to start up.

One example for using this hook is to use ``certbot`` to create HTTPS certificates for a Synapse service. This example
assumes the Cortex is running as root, so that certbot can bind port 80 to perform the ``http-01`` challenge. Non-root
deployments may require additional port mapping for a given deployment.

Create a boothooks directory::

  mkdir -p /srv/syn/00.cortex/bookhooks

Copy the following script to ``/srv/syn/cortex/bookhooks/preboot.sh`` and use ``chmod`` to mark it as an executable
file:

.. literalinclude:: devguides/certbot.sh
    :language: bash

That directory will be mounted at ``/vertex/boothooks``. The following Compose file shows mounting that
directory into the container and setting environment variables for the script to use::

  services:
    00.cortex:
      image: vertexproject/synapse-cortex:v2.x.x
      network_mode: host
      restart: unless-stopped
      volumes:
          - ./storage:/vertex/storage
          - ./boothooks:/vertex/boothooks
      environment:
          SYN_LOG_LEVEL: "DEBUG"
          SYN_CORTEX_STORM_LOG: "true"
          SYN_CORTEX_AHA_PROVISION: "ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>"
          CERTBOT_HOSTNAME: "cortex.acme.corp"
          CERTBOT_EMAIL: "user@acme.corp"

When started, the container will attempt to run the script before starting the Cortex service.

The second way to modify a container startup process is running a script concurrently to the service. This can be set
by mapping in a file at ``/vertex/boothooks/concurrent.sh``, also as an executable file. If this file is present, the
script is executed as a backgrounded task prior to starting up the Synapse service. This script would be stopped
when the container is stopped.

.. note::

    If a volume is mapped into ``/vertex/boothooks/`` it will not be included in any backups made by a Synapse service
    using the backup APIs. Making backups of any data persisted in these locations is the responsibility of the
    operator configuring the container.

Containers with Custom Users
----------------------------

By default, Synapse service containers will work running as ``root`` ( uid 0 ) and ``synuser`` ( uid 999 ) without any
modification. In order to run a Synapse service container as a different user that is not built into the container by
default, the user, group and home directory need to be added to the image. This can be done with a custom Dockerfile to
modify a container. For example, the following Dockerfile would add the user ``altuser`` to the Container with a user
id value of 8888::

    FROM vertexproject/synapse-cortex:v2.x.x
    RUN set -ex \
    && groupadd -g 8888 altuser \
    && useradd -r --home-dir=/home/altuser -u 8888 -g altuser --shell /bin/bash altuser \
    && mkdir -p /home/altuser \
    && chown 8888:8888 /home/altuser

Running this with a ``docker build`` command can be used to create the image ``customcortex:v2.x.x``::

    $ docker build -f Dockerfile --tag  customcortex:v2.x.x .
    Sending build context to Docker daemon  4.608kB
    Step 1/2 : FROM vertexproject/synapse-cortex:v2.113.0
    ---> 8a2dd3465700
    Step 2/2 : RUN set -ex && groupadd -g 8888 altuser && useradd -r --home-dir=/home/altuser -u 8888 -g altuser --shell /bin/bash altuser && mkdir -p /home/altuser && chown 8888:8888 /home/altuser
    ---> Running in 9c7b30365c2d
    + groupadd -g 8888 altuser
    + useradd -r --home-dir=/home/altuser -u 8888 -g altuser --shell /bin/bash altuser
    + mkdir -p /home/altuser
    + chown 8888:8888 /home/altuser
    Removing intermediate container 9c7b30365c2d
     ---> fd7173d42923
    Successfully built fd7173d42923
    Successfully tagged customcortex:v2.x.x

That custom user can then be used to run the Cortex::

    services:
      00.cortex:
        user: "8888"
        image: customcortex:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        environment:
        - SYN_CORTEX_AXON=aha://axon...
        - SYN_CORTEX_JSONSTOR=aha://jsonstor...
        - SYN_CORTEX_AHA_PROVISION=ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

The following bash script can be used to help automate this process, by adding the user to an image and appending
the custom username to the image tag:

.. literalinclude:: devguides/adduserimage.sh
    :language: bash

Saving this to ``adduserimage.sh``, it can then be used to quickly modify an image. The following example shows running
this to add a user named ``foouser`` with the uid 1234::

    $ ./adduserimage.sh vertexproject/synapse-aha:v2.113.0 foouser 1234
    Add user/group foouser with 1234 into vertexproject/synapse-aha:v2.113.0, creating: vertexproject/synapse-aha:v2.113.0-foouser
    Sending build context to Docker daemon  4.608kB
    Step 1/2 : FROM vertexproject/synapse-aha:v2.113.0
     ---> 53251b832df0
    Step 2/2 : RUN set -ex && groupadd -g 1234 foouser && useradd -r --home-dir=/home/foouser -u 1234 -g foouser --shell /bin/bash foouser && mkdir -p /home/foouser && chown 1234:1234 /home/foouser
     ---> Running in 1c9e793d6761
    + groupadd -g 1234 foouser
    + useradd -r --home-dir=/home/foouser -u 1234 -g foouser --shell /bin/bash foouser
    + mkdir -p /home/foouser
    + chown 1234:1234 /home/foouser
    Removing intermediate container 1c9e793d6761
     ---> 21a12f395462
    Successfully built 21a12f395462
    Successfully tagged vertexproject/synapse-aha:v2.113.0-foouser


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

    import sys
    import asyncio

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
data that is not part of the :ref:`userguide_datamodel`. For an example of deploying a JSONStor, see the :ref:`deploymentguide`.

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

.. _devops-svc-cortex-ext-http:

Extended HTTP API
~~~~~~~~~~~~~~~~~

.. highlight:: none

The Cortex can be configured ( via Storm ) to service custom HTTP API endpoints. These user defined endpoints execute
Storm code in order to generate responses. This allows creating custom HTTP API responses or URL paths which may meet
custom needs.

These endpoints have a base URL of ``/api/ext/``. Additional path components in a request are used to resolve which API
definition is used to handle the response.

The Storm queries which implement these endpoints will have a ``$request`` object ( see
:ref:`stormprims-http-api-request-f527` ) added to them. This object is used to send custom data back to the caller.
This object contains helpers to access the request data, as well as functions to send data back to the caller.

.. note::

    Several examples show curl_ and jq_ being used to access endpoints or process data. These tools are not required
    in order to interact with the Extended HTTP API.

A Simple Example
++++++++++++++++

The following simple example shows adding an API endpoint and setting the ``GET`` method on it that just returns a
simple message embedded in a dictionary::

    $api = $lib.cortex.httpapi.add('demo/path00')
    $api.methods.get = ${
        $mesg=`Hello! I am a request made to {$request.path}`
        $headers = ({"Some": "Value"})
        $body = ({"mesg": $mesg})
        $request.reply(200, headers=$headers, body=$body)
     }

When accessing that HTTP API endpoint on the Cortex, the response data has the status code, custom headers, and custom
body in the reponse::

    $ curl -D - -sku "root:root" "https://127.0.0.1:4443/api/ext/demo/path00"
    HTTP/1.1 200 OK
    Content-Type: application/json; charset=utf8"
    Date: Tue, 17 Oct 2023 16:21:32 GMT
    Some: value
    Content-Length: 53

    {"mesg": "Hello! I am a request made to demo/path00"}

The ``$request.reply()`` method automatically will convert primitive objects into a JSON response, enabling rapid
development of JSON based API endpoints.

Accessing Request Data
++++++++++++++++++++++

The ``$request`` object has information available about the request itself. The following API example shows access to
all of that request data, and echoes it back to the caller::

    $api = $lib.cortex.httpapi.add('demo/([a-z0-9]*)')
    $api.methods.post = ${
        $body = ({
            "method": $request.method,        // The HTTP method
            "headers": $request.headers,      // Any request headers
            "params": $request.params,        // Any requets parameters
            "uri": $request.uri,              // The full URI requested
            "path": $request.path,            // The path component after /api/ext/
            "args": $request.args,            // Any capture groups matched from the path.
            "client": $request.client,        // Requester client IP
            "iden": $request.api.iden,        // The iden of the HTTP API handling the request
            "nbyts": $lib.len($request.body), // The raw body is available as bytes
        })
        try {
            $body.json = $request.json        // Synapse will lazily load the request body as json upon access
        } catch StormRuntimeError as err {    // But it may not be json!
            $body.json = 'err'
        }
        $headers = ({'Echo': 'hehe!'})
        $request.reply(200, headers=$headers, body=$body)
    }

Accessing that endpoint shows that request information is echoed back to the caller::

    $ curl -sku "root:secret" -XPOST -d '{"some":["json", "items"]}' "https://127.0.0.1:4443/api/ext/demo/ohmy?hehe=haha" | jq
    {
      "method": "POST",
      "headers": {
        "host": "127.0.0.1:4443",
        "authorization": "Basic cm9vdDpzZWNyZXQ=",
        "user-agent": "curl/7.81.0",
        "accept": "*/*",
        "content-length": "26",
        "content-type": "application/x-www-form-urlencoded"
      },
      "params": {
        "hehe": "haha"
      },
      "uri": "/api/ext/demo/ohmy?hehe=haha",
      "path": "demo/ohmy",
      "args": [
        "ohmy"
      ],
      "client": "127.0.0.1",
      "iden": "50cf80d0e332a31608331490cd453103",
      "nbyts": 26,
      "json": {
        "some": [
          "json",
          "items"
        ]
      }
    }


The ``$request.headers`` are accessed in a case-insensitive manner.  ``$request.parameters`` are case sensitive. The
following example shows that::

    $api = $lib.cortex.httpapi.get(50cf80d0e332a31608331490cd453103)
    $api.methods.get = ${
        $body=({
            "ua":   $request.headers."UseR-AGent",  // case insensitive match on the User-Agent string
            "hehe": $request.params.hehe,
            "HEHE": $request.params.HEHE,
        })
        $request.reply(200, body=$body)
    }

The output of that endpoint::

    $ curl -s -k -u "root:secret" "https://127.0.0.1:4443/api/ext/demo/casemath?hehe=haha&HEHE=uppercase"  | jq
    {
      "ua": "curl/7.81.0",
      "hehe": "haha",
      "HEHE": "uppercase"
    }

.. note::

    Request headers and parameters are flattened into a single key / value mapping. Duplicate request headers or
    parameters are not exposed in the ``$request`` object.

Managing HTTP APIs
++++++++++++++++++

When creating an Extended HTTP API, the request path must be provided. This path component is matched against any
path components after ``/api/etx/*`` when determing which API endpoint will service the request. The API endpoints are
matched in order, comparing their ``path`` against the requested path using a case sensitive fullmatch_ regular
expression comparison. Newly created API endpoints are added to the end of the list for matching. It is best for
these endpoints to be ordered from most specific to least specific.

To list the registered APIs, their order, and path information, use the ``cortex.httpapi.list`` command::

    storm> cortex.httpapi.list
     order | iden                             | owner                | auth  | runas  | path
    =======|==================================|======================|=======|========|======
    0      | 50cf80d0e332a31608331490cd453103 | root                 | true  | owner  | demo/([a-z0-9]*)
    1      | 586311d3a7a26d6138bdc07169e4cde5 | root                 | true  | owner  | demo/path00
    2      | 1896bda5dbd97615ee553059079620ba | root                 | true  | owner  | demo/path01
    3      | daaf33e23b16540acdc872fee2de1b61 | root                 | true  | owner  | something/Else

In this example, there are four items listed. The ``path`` of the first item will match the paths for the second and
third items. The index for the first item needs to be moved using the ``cortex.httpapi.index`` commmand. That command
allows users to change the order in which the API endpoints are matched::

    storm> cortex.httpapi.index 50cf80d0e332a31608331490cd453103 3
    Set HTTP API 50cf80d0e332a31608331490cd453103 to index 3

    storm> cortex.httpapi.list
     order | iden                             | owner                | auth  | runas  | path
    =======|==================================|======================|=======|========|======
    0      | 586311d3a7a26d6138bdc07169e4cde5 | root                 | true  | owner  | demo/path00
    1      | 1896bda5dbd97615ee553059079620ba | root                 | true  | owner  | demo/path01
    2      | daaf33e23b16540acdc872fee2de1b61 | root                 | true  | owner  | something/Else
    3      | 50cf80d0e332a31608331490cd453103 | root                 | true  | owner  | demo/([a-z0-9]*)


The endpoints in the example are now checked in a "more specific" to "least specific" order.

The path of an endpoint can also be changed. This can be done by assigning a new value to the ``path`` attribute on
the ``http:api`` object in Storm::

    storm> $api=$lib.cortex.httpapi.get(1896bda5dbd97615ee553059079620ba) $api.path="demo/mynew/path"
    complete. 0 nodes in 8 ms (0/sec).

    storm> cortex.httpapi.list
     order | iden                             | owner                | auth  | runas  | path
    =======|==================================|======================|=======|========|======
    0      | 586311d3a7a26d6138bdc07169e4cde5 | root                 | true  | owner  | demo/path00
    1      | 1896bda5dbd97615ee553059079620ba | root                 | true  | owner  | demo/mynew/path
    2      | daaf33e23b16540acdc872fee2de1b61 | root                 | true  | owner  | something/Else
    3      | 50cf80d0e332a31608331490cd453103 | root                 | true  | owner  | demo/([a-z0-9]*)

The path components which match each regular expression capture group in the ``path`` will be set in the
``$request.args`` data. An endpoint can capture multiple args this way::

    // Set the echo API handler defined earlier to have a path which has multiple capture groups
    $api = $lib.cortex.httpapi.get(50cf80d0e332a31608331490cd453103)
    $api.path="demo/([a-z0-9]+)/(.*)"

The capture groups are then available::

    $ curl -sku "root:secret" -XPOST "https://127.0.0.1:4443/api/ext/demo/foobar1/AnotherArgument/inTheGroup"  | jq '.args'
    [
      "foobar1",
      "AnotherArgument/inTheGroup"
    ]


.. note::

    The Cortex does not make any attempt to do any inspection of path values which may conflict between the endpoints.
    This is because the paths for a given endpoint may be changed, they can contain regular expressions, and they may
    have their resolution order changed. Cortex users are responsible for configuring their endpoints with correct
    paths and order to meet their use cases.

The Extended HTTP APIs can also be given a name and a description. The following shows setting the ``name`` and
``desc`` fields, and then showing the details of the API using ``cortex.httpapi.stat``. This command shows detailed
information about the Extended HTTP API endpoint::

    $api = $lib.cortex.httpapi.get(50cf80d0e332a31608331490cd453103)
    $api.name="demo wildcard"
    $api.desc='''This API endpoint is a wildcard example. It has a GET method and a POST method available.'''

    // Stat output
    storm> cortex.httpapi.stat 50cf80d0e332a31608331490cd453103
    Iden: 50cf80d0e332a31608331490cd453103
    Creator: root (b13c21813628ac4464b78b5d7c55cd64)
    Created: 2023/10/18 14:02:52.070
    Updated: 2023/10/18 14:07:29.448
    Path: demo/([a-z0-9]+)/(.*)
    Owner: root (b13c21813628ac4464b78b5d7c55cd64)
    Runas: owner
    View: default (a1877dd028915d90862e35e24b491bfc)
    Readonly: false
    Authenticated: true
    Name: demo wildcard
    Description: This API endpoint is a wildcard example. It has a GET method and a POST method available.

    No user permissions are required to run this HTTP API endpoint.
    The handler defines the following HTTP methods:
    Method: POST
    $body = ({
                "method": $request.method,        // The HTTP method
                "headers": $request.headers,      // Any request headers
                "params": $request.params,        // Any requets parameters
                "uri": $request.uri,              // The full URI requested
                "path": $request.path,            // The path component after /api/ext/
                "args": $request.args,            // Any capture groups matched from the path.
                "client": $request.client,        // Requester client IP
                "iden": $request.api.iden,        // The iden of the HTTP API handling the request
                "nbyts": $lib.len($request.body), // The raw body is available as bytes
            })
            try {
                $body.json = $request.json        // Synapse will lazily load the request body as json upon access
            } catch StormRuntimeError as err {    // But it may not be json!
                $body.json = 'err'
            }
            $headers = ({'Echo': 'hehe!'})
            $request.reply(200, headers=$headers, body=$body)

    Method: GET
    $body=({
                "ua":   $request.headers."UseR-AGent",  // case insensitive match on the User-Agent string
                "hehe": $request.params.hehe,
                "HEHE": $request.params.HEHE,
            })
            $request.reply(200, body=$body)

    No vars are set for the handler.

Supported Methods
+++++++++++++++++

The endpoints support the following HTTP Methods:

- ``GET``
- ``PUT``
- ``HEAD``
- ``POST``
- ``PATCH``
- ``DELETE``
- ``OPTIONS``

The logic which implements these methods is set via Storm. The following example shows setting two simple methods for a
given endpoint::

    $api = $lib.cortex.httpapi.get(586311d3a7a26d6138bdc07169e4cde5)
    $api.methods.get = ${ $request.reply(200, headers=({"X-Method": "GET"}))
    $api.methods.put = ${ $request.reply(200, headers=({"X-Method": "PUT"}))

These methods can be removed as well by assigning ``$lib.undef`` to the value::

    // Remove the GET method
    $api = $lib.cortex.httpapi.get(586311d3a7a26d6138bdc07169e4cde5)
    $api.methods.put = $lib.undef

Users are not required to implement their methods in any particular styles or conventions. The only method specific
restriction on the endpoint logic is for the ``HEAD`` method. Any body content that is sent in response to the ``HEAD``
method will not be transmitted to the requester. This body content will be omitted from being transmitted without
warning or error.

A request which is made with for method that a matching handler does not implement will return an HTTP 405 error.

Authentication, Permissions, and Users
++++++++++++++++++++++++++++++++++++++

Since the endpoints are executed by running Storm queries to generate responses, Synapse must resolve the associated
:ref:`gloss-user` and a :ref:`gloss-view` which will be used to run the query. There are a few important properties of
the endpoints that users configuring them must be aware of.

**owner**

    By default, the user that creates an endpoint is marked as the ``owner`` for that endpoint. This is the default
    user that will execute the Storm queries which implement the HTTP Methods. This value can be changed by setting
    the ``.owner`` property on the endpoint object to a different User.

    A user marked as the ``owner`` of an endpoint does not have any permissions granted that allows them to edit the
    endpoint.

**view**

    The View that an Extended HTTP API endpoint is created in is recorded as the View that the Storm endpoints are
    executed in. This View can be changed by assigning the ``.view`` property on the endpoint object to a different
    View.

**authenticated**

    By default, the endpoints require the requester to have an authenticated session. Information about API
    authentication can be found at :ref:`http-api-authentication`. This authentication requirement can be disabled by
    setting the ``.authenticated`` property on the endpoint object to ``$lib.false``. That will allow the endpoint to
    be resolved without presenting any sort of authentication information.

**runas**

    By default, the Storm logic is run by the user that is marked as the ``owner``. Endpoints can instead be configured
    to run as the authenticated user by setting the ``.runas`` property on the HTTP API object to ``user``.  In order
    to change the behavior to executing the queries as the owner, the value should be set to ``owner``.

    When an endpoint is configured with ``runas`` set to ``user`` and ``authenticated`` to ``$lib.false`` any
    calls to that API will be executed as the ``owner``.

This allows creating endpoints that run in one of three modes:

- Authenticated & runs as the Owner
- Authenticated & runs as the User
- Unauthenticated & runs as the Owner

These three modes can be demonstrated by configuring endpoints that will echo back the current user::

    // Create a query object that we will use for each handler
    $echo=${ $request.reply(200, body=$lib.user.name()) }

    // Create the first endpoint with a default configuration.
    $api0 = $lib.cortex.httpapi.add('demo/owner')
    $api0.methods.get=$echo

    // Create the second endpoint which runs its logic as the requester.
    $api1 = $lib.cortex.httpapi.add('demo/user')
    $api1.runas=user
    $api1.methods.get=$echo

    // Create the third endpoint which does not require authentication.
    $api2 = $lib.cortex.httpapi.add('demo/noauth')
    $api2.authenticated=$lib.false  // Disable authentication
    $api2.methods.get=$echo

Accessing those endpoints with different users gives various results::

    # The demo/owner endpoint runs as the owner
    $ curl -sku "root:secret" "https://127.0.0.1:4443/api/ext/demo/owner"  | jq
    "root"

    $ curl -sku "lowuser:demo" "https://127.0.0.1:4443/api/ext/demo/owner"  | jq
    "root"

    # The demo/user endpoint runs as the requester
    $ curl -sku "root:secret" "https://127.0.0.1:4443/api/ext/demo/user"  | jq
    "root"

    $ curl -sku "lowuser:demo" "https://127.0.0.1:4443/api/ext/demo/user"  | jq
    "lowuser"

    # The demo/noauth endpoint runas the owner
    $ curl -sk "https://127.0.0.1:4443/api/ext/demo/noauth"  | jq
    "root"

If the owner or an authenticated user does not have permission to execute a Storm query in the configured View, or if
the endpoints' View is deleted from the Cortex, this will raise a fatal error and return an HTTP 500 error. Once a
query has started executing, regular Storm permissions apply.

Endpoints can also have permissions defined for them. This allows locking down an endpoint such that while a user may
still have access to the underlying view, they may lack the specific permissions required to execute the endpoint.
These permissions are checked against the authenticated user, and not the endpoint owner. The following example shows
setting a single permission on one of our earlier endpoints::

    $api=$lib.cortex.httpapi.get(bd4679ab8e8a1fbc030b46e275ddba96)
    $api.perms=(your.custom.permission,)

Accessing it as a user without the specified permission generates an ``AuthDeny`` error::

    $ curl -sku "lowuser:demo" "https://127.0.0.1:4443/api/ext/demo/owner"  | jq
    {
      "status": "err",
      "code": "AuthDeny",
      "mesg": "User (lowuser) must have permission your.custom.permission"
    }

The user can have that permission granted via Storm::

    storm> auth.user.addrule lowuser your.custom.permission
    Added rule your.custom.permission to user lowuser.

Then the endpoint can be accessed::

    $ curl -sku "lowuser:demo" "https://127.0.0.1:4443/api/ext/demo/owner"  | jq
    "root"

For additional information about managing user permissions, see :ref:`admin_create_users_roles`.

.. note::

    When the Optic UI is used to proxy the ``/api/ext`` endpoint, authentication must be done using Optic's login
    endpoint. Basic auth is not available.

Readonly Mode
+++++++++++++

The Storm queries for a given handler may be executed in a ``readonly`` runtime. This is disabled by default. This can
be changed by setting the ``readonly`` attribute on the ``http:api`` object::

    // Enable the Storm queries to be readonly
    $api = $lib.cortex.httpapi.get($yourIden)
    $api.readonly = $lib.true

Endpoint Variables
++++++++++++++++++

User defined variables may be set for the queries as well. These variables are mapped into the runtime for each method.
This can be used to provide constants or other information which may change, without needing to alter the underlying
Storm code which defines a method. These can be read ( or removed ) by altering the ``$api.vars`` dictionary. This is
an example of using a variable in a query::

    // Set a variable that a method uses:

    $api = $lib.cortex.httpapi.get($yourIden)
    $api.methods.get = ${
        $mesg = `There are {$number} things available!`
        $request.reply(200, body=({"mesg": $mesg})
    }
    $api.vars.number = (5)

When executing this method, the JSON response would be the following::

    {"mesg": "There are 5 things available!"}

If ``$api.vars.number = "several"`` was executed, the JSON response would now be the following::

    {"mesg": "There are several things available!"}

Variables can be removed by assigning ``$lib.undef`` to them::

    $api = $lib.cortex.httpapi.get($yourIden)
    $api.vars.number = $lib.undef

Sending Custom Responses
++++++++++++++++++++++++

Responses can be made which are not JSON formatted. The ``$request.reply()`` method can be used to send raw bytes. The
user must provide any appropriate headers alongside their request.

**HTML Example**

The following example shows an endpoint which generates a small amount of HTML. It uses an HTML template stored in in
the method ``vars``. This template has a small string formatted in it, converted to bytes, and then the headers are
set. The end result can be then rendered in a web browser::

    $api = $lib.cortex.httpapi.add('demo/html')
    $api.vars.template = '''<!DOCTYPE html>
    <html>
    <body>
    <h1>A Header</h1>
    <p>{mesg}</p>
    </body>
    </html>'''
    $api.methods.get = ${
        $duration = $lib.model.type(duration).repr($lib.cell.uptime().uptime)
        $mesg = `The Cortex has been up for {$duration}`
        $html = $lib.str.format($template, mesg=$mesg)
        $buf = $html.encode()
        $headers = ({
            "Content-Type": "text/html",
            "Content-Length": `{$lib.len($buf)}`
        })
        $request.reply(200, headers=$headers, body=$buf)
    }

Accessing this endpoint with ``curl`` shows the following::

    $ curl -D - -sku "root:secret" "https://127.0.0.1:4443/api/ext/demo/html"
    HTTP/1.1 200 OK
    Content-Type: text/html
    Date: Wed, 18 Oct 2023 14:07:47 GMT
    Content-Length: 137

    <!DOCTYPE html>
    <html>
    <body>
    <h1>A Header</h1>
    <p>The Cortex has been up for 1D 00:59:12.704</p>
    </body>
    </html>f

**Streaming Examples**

The ``http:request`` object has methods that allow a user to send the response code, headers and body separately.
One use for this is to create a streaming response. This can be used when the total response size may not be known
or to avoid incurring memory pressure on the Cortex when computing results.

The following examples generates some JSONLines data::

    $api = $lib.cortex.httpapi.add('demo/jsonlines')
    $api.methods.get = ${
        $request.sendcode(200)
        // This allows a browser to view the response
        $request.sendheaders(({"Content-Type": "text/plain; charset=utf8"}))
        $values = ((1), (2), (3))
        for $i in $values {
            $data = ({'i': $i})
            $body=`{$lib.json.save($data)}\n`
            $request.sendbody($body.encode())
        }
    }

Accessing this endpoint shows the JSONLines rows sent back::

    $ curl -D - -sku "root:secret" "https://127.0.0.1:4443/api/ext/demo/jsonlines"
    HTTP/1.1 200 OK
    Content-Type: text/plain; charset=utf8
    Date: Wed, 18 Oct 2023 14:31:29 GMT
     nosniff
    Transfer-Encoding: chunked

    {"i": 1}
    {"i": 2}
    {"i": 3}

In a similar fashion, a CSV can be generated. This example shows an integer and its square being computed::

    $api = $lib.cortex.httpapi.add('demo/csv')
    $api.methods.get = ${
        $request.sendcode(200)
        $request.sendheaders(({"Content-Type": "text/csv"}))

        // Header row
        $header="i, square\n"
        $request.sendbody($header.encode())

        $n = 10  // Number of rows to compute
        for $i in $lib.range($n) {
            $square = ($i * $i)
            $body = `{$i}, {$square}\n`
            $request.sendbody($body.encode())
        }
    }

Accessing this shows the CSV content being sent back::

    $ curl -D - -sku "root:secret" "https://127.0.0.1:4443/api/ext/demo/csv"
    HTTP/1.1 200 OK
    Content-Type: text/csv
    Date: Wed, 18 Oct 2023 14:43:37 GMT
    Transfer-Encoding: chunked

    i, square
    0, 0
    1, 1
    2, 4
    3, 9
    4, 16
    5, 25
    6, 36
    7, 49
    8, 64
    9, 81


When using the ``sendcode()``, ``sendheaders()``, and ``sendbody()`` APIs the order in which they are called does
matter. The status code and headers can be set at any point before sending body data. They can even be set multiple
times if the response logic needs to change a value it previously set.

Once the body data has been sent, the status code and headers will be sent to the HTTP client and cannot be changed.
Attempting to change the status code or send additional headers will have no effect. This will generate a warning
message on the Cortex.

The **minimum** data that the Extended HTTP API requires for a response to be considered valid is setting the status
code. If the status code is not set by an endpoint, or if body content is sent prior to setting the endpoint, then
an HTTP 500 status code will be sent to the caller.

Messages and Error Handling
+++++++++++++++++++++++++++

Messages sent out of the Storm runtime using functions such as ``$lib.print()``, ``$lib.warn()``, or ``$lib.fire()``
are not available to HTTP API callers. The ``$lib.log`` Storm library can be used for doing out of band logging of
messages that need to be generated while handling a response.

A Storm query which generates an error which tears down the Storm runtime with an ``err`` message will result in an
HTTP 500 response being sent. The error will be encoded in the Synapse HTTP API error convention documented at
:ref:`http-api-conventions`.

For example, if the previous example where the handler sent a ``mesg``  about the ``$number`` of things available was
run after the variable  ``$number`` was removed, the code would generate the following response body:

.. highlight:: none

::

    {"status": "err", "code": "NoSuchVar", "mesg": "Missing variable: number"}

Custom error handling of issues that arise inside of the Storm query execution can be handled with the
:ref:`flow-try-catch`. This allows a user to have finer control over their error codes, headers and error body content.

.. note::

    The HTTP 500 response will not be sent if there has already been body data send by the endpoint.

Devops Details
==============

Orchestration
-------------

.. _orch-kubernetes:

Kubernetes
~~~~~~~~~~

A popular option for Orchestration is Kubernetes. Kubernetes is an open-source system for automating the deployment,
scaling and management of containerized applications. Synapse does work in Kubernetes environments.

.. note::

    If you are using these examples to get started with Synapse on Kubernetes, you may need to adapt them to meet
    operational needs for your environment.

.. _orch-kubernetes-deployment:

Example Deployment
++++++++++++++++++

The following examples walk through deploying an example Synapse deployment ( based on :ref:`deploymentguide` ), but
inside of a managed Kubernetes cluster managed by Digital Ocean. This deployment makes a few assumptions:

  Synapse Deployment Guide
    This guide assumes a familiarity with the Synapse deployment guide. Concepts covered there are not repeated here.

  namespace
    These examples use the Kubernetes ``default`` namespace.

  PersistentVolumeClaim
    These examples use PersistentVolumeClaim (PVC) to create a persistent storage location. All Synapse services assume
    they have some persistent storage to read and write to.  This example uses the ``storageClass`` of
    ``do-block-storage``. You may need to alter these examples to provide a ``storageClass`` that is appropriate
    for your environment.

  Aha naming
    In Kubernetes, we rely on the default naming behavior for services to find the Aha service via DNS, so our Aha name
    and Aha network should match the internal naming for services in the cluster. The ``aha:network`` value is
    ``<namespace>.<cluster dns root>``. This DNS root value is normally ``svc.cluster.local``, so the resulting DNS
    label for the Aha service is ``aha.default.svc.cluster.local``. Similarly, the Aha service is configured to listen
    on ``0.0.0.0``, since we cannot bind the DNS label provided by Kubernetes prior to the Pod running Aha being
    available.

Aha
^^^

The following ``aha.yaml`` can be used to deploy an Aha service.

.. literalinclude:: ./kubernetes/aha.yaml
    :language: yaml

This can be deployed via ``kubectl apply``. That will create the PVC, deployment, and service.

.. highlight:: bash

::

    $ kubectl apply -f aha.yaml
    persistentvolumeclaim/example-aha created
    deployment.apps/aha created
    service/aha created

You can see the startup logs as well:

.. highlight:: bash

::

    $ kubectl logs -l app.kubernetes.io/instance=aha
    2023-03-08 04:22:02,568 [DEBUG] Set config valu from envar: [SYN_AHA_DMON_LISTEN] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 04:22:02,568 [DEBUG] Set config valu from envar: [SYN_AHA_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 04:22:02,568 [DEBUG] Set config valu from envar: [SYN_AHA_AHA_NAME] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 04:22:02,569 [DEBUG] Set config valu from envar: [SYN_AHA_AHA_NETWORK] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 04:22:02,651 [INFO] Adding CA certificate for default.svc.cluster.local [aha.py:initServiceRuntime:MainThread:MainProcess]
    2023-03-08 04:22:02,651 [INFO] Generating CA certificate for default.svc.cluster.local [aha.py:genCaCert:MainThread:MainProcess]
    2023-03-08 04:22:06,401 [INFO] Adding server certificate for aha.default.svc.cluster.local [aha.py:initServiceRuntime:MainThread:MainProcess]
    2023-03-08 04:22:08,879 [INFO] dmon listening: ssl://0.0.0.0?hostname=aha.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initServiceNetwork:MainThread:MainProcess]
    2023-03-08 04:22:08,882 [INFO] ...ahacell API (telepath): ssl://0.0.0.0?hostname=aha.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initFromArgv:MainThread:MainProcess]
    2023-03-08 04:22:08,882 [INFO] ...ahacell API (https): disabled [cell.py:initFromArgv:MainThread:MainProcess]


Axon
^^^^

The following ``axon.yaml`` can be used as the basis to deploy an Axon service.

.. literalinclude:: ./kubernetes/axon.yaml
    :language: yaml

Before we deploy that, we need to create the Aha provisioning URL. We can do that via ``kubectl exec``. That should look
like the following:

.. highlight:: bash

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.axon
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/39a33f6e3fa2b512552c2c7770e28d30?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_AXON_AHA_PROVISION`` environment variable, so that block looks like the
following:

.. highlight:: yaml

::

    - name: SYN_AXON_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/39a33f6e3fa2b512552c2c7770e28d30?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"

This can then be deployed via ``kubectl apply``:

.. highlight:: bash

::

    $ kubectl apply -f axon.yaml
    persistentvolumeclaim/example-axon00 unchanged
    deployment.apps/axon00 created

You can see the Axon logs as well. These show provisioning and listening for traffic:

.. highlight:: bash

::

    $ kubectl logs -l app.kubernetes.io/instance=axon00
    2023-03-08 17:27:44,721 [INFO] log level set to DEBUG [common.py:setlogging:MainThread:MainProcess]
    2023-03-08 17:27:44,722 [DEBUG] Set config valu from envar: [SYN_AXON_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:27:44,722 [DEBUG] Set config valu from envar: [SYN_AXON_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:27:44,723 [INFO] Provisioning axon from AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:27:44,833 [DEBUG] Set config valu from envar: [SYN_AXON_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:27:44,833 [DEBUG] Set config valu from envar: [SYN_AXON_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:27:51,649 [INFO] Done provisioning axon AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:27:51,898 [INFO] dmon listening: ssl://0.0.0.0:0?hostname=00.axon.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initServiceNetwork:MainThread:MainProcess]
    2023-03-08 17:27:51,899 [INFO] ...axon API (telepath): ssl://0.0.0.0:0?hostname=00.axon.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initFromArgv:MainThread:MainProcess]
    2023-03-08 17:27:51,899 [INFO] ...axon API (https): disabled [cell.py:initFromArgv:MainThread:MainProcess]

The hostname ``00.axon.default.svc.cluster.local`` seen in the logs is **not** a DNS label in Kubernetes. That is an
internal label used by the service to resolve SSL certificates that it provisioned with the Aha service, and as the
name that it uses to register with the Aha service.


JSONStor
^^^^^^^^

The following ``jsonstor.yaml`` can be used as the basis to deploy a JSONStor service.

.. literalinclude:: ./kubernetes/jsonstor.yaml
    :language: yaml

Before we deploy that, we need to create the Aha provisioning URL. We can do that via ``kubectl exec``. That should look
like the following:

.. highlight:: bash

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.jsonstor
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/cbe50bb470ba55a5df9287391f843580?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_JSONSTOR_AHA_PROVISION`` environment variable, so that block looks like the
following:

.. highlight:: yaml

::

    - name: SYN_JSONSTOR_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/cbe50bb470ba55a5df9287391f843580?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"


This can then be deployed via ``kubectl apply``:

.. highlight:: bash

::

    $ kubectl apply -f jsonstor.yaml
    persistentvolumeclaim/example-jsonstor00 created
    deployment.apps/jsonstor00 created

You can see the JSONStor logs as well. These show provisioning and listening for traffic:

.. highlight:: bash

::

    $ kubectl logs -l app.kubernetes.io/instance=jsonstor00
    2023-03-08 17:29:15,137 [INFO] log level set to DEBUG [common.py:setlogging:MainThread:MainProcess]
    2023-03-08 17:29:15,137 [DEBUG] Set config valu from envar: [SYN_JSONSTOR_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:15,138 [DEBUG] Set config valu from envar: [SYN_JSONSTOR_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:15,140 [INFO] Provisioning jsonstorcell from AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:29:15,261 [DEBUG] Set config valu from envar: [SYN_JSONSTOR_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:15,261 [DEBUG] Set config valu from envar: [SYN_JSONSTOR_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:19,325 [INFO] Done provisioning jsonstorcell AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:29:19,966 [INFO] dmon listening: ssl://0.0.0.0:0?hostname=00.jsonstor.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initServiceNetwork:MainThread:MainProcess]
    2023-03-08 17:29:19,966 [INFO] ...jsonstorcell API (telepath): ssl://0.0.0.0:0?hostname=00.jsonstor.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initFromArgv:MainThread:MainProcess]
    2023-03-08 17:29:19,966 [INFO] ...jsonstorcell API (https): disabled [cell.py:initFromArgv:MainThread:MainProcess]

Cortex
^^^^^^

The following ``cortex.yaml`` can be used as the basis to deploy the Cortex.

.. literalinclude:: ./kubernetes/cortex.yaml
    :language: yaml

Before we deploy that, we need to create the Aha provisioning URL. This uses a fixed listening port for the Cortex, so
that we can later use port-forwarding to access the Cortex service. We do this via ``kubectl exec``. That should look
like the following:

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.cortex --dmon-port 27492
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/c06cd588e469a3b7f8a56d98414acf8a?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_CORTEX_AHA_PROVISION`` environment variable, so that block looks like the
following:

.. highlight:: bash

::

    - name: SYN_CORTEX_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/c06cd588e469a3b7f8a56d98414acf8a?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"


This can then be deployed via ``kubectl apply``:

.. highlight:: bash

::

    $ kubectl apply -f cortex.yaml
    persistentvolumeclaim/example-cortex00 created
    deployment.apps/cortex00 created
    service/cortex created


You can see the Cortex logs as well. These show provisioning and listening for traffic, as well as the connection being
made to the Axon and JSONStor services:

.. highlight:: bash

::

    $ kubectl logs -l app.kubernetes.io/instance=cortex00
    2023-03-08 17:29:16,892 [INFO] log level set to DEBUG [common.py:setlogging:MainThread:MainProcess]
    2023-03-08 17:29:16,893 [DEBUG] Set config valu from envar: [SYN_CORTEX_AXON] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:16,893 [DEBUG] Set config valu from envar: [SYN_CORTEX_JSONSTOR] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:16,894 [DEBUG] Set config valu from envar: [SYN_CORTEX_STORM_LOG] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:16,894 [DEBUG] Set config valu from envar: [SYN_CORTEX_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:16,894 [DEBUG] Set config valu from envar: [SYN_CORTEX_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:16,896 [INFO] Provisioning cortex from AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:29:17,008 [DEBUG] Set config valu from envar: [SYN_CORTEX_AXON] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:17,009 [DEBUG] Set config valu from envar: [SYN_CORTEX_JSONSTOR] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:17,009 [DEBUG] Set config valu from envar: [SYN_CORTEX_STORM_LOG] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:17,010 [DEBUG] Set config valu from envar: [SYN_CORTEX_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:17,010 [DEBUG] Set config valu from envar: [SYN_CORTEX_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:29:20,356 [INFO] Done provisioning cortex AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:29:21,077 [INFO] dmon listening: ssl://0.0.0.0:27492?hostname=00.cortex.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initServiceNetwork:MainThread:MainProcess]
    2023-03-08 17:29:21,078 [INFO] ...cortex API (telepath): ssl://0.0.0.0:27492?hostname=00.cortex.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initFromArgv:MainThread:MainProcess]
    2023-03-08 17:29:21,078 [INFO] ...cortex API (https): disabled [cell.py:initFromArgv:MainThread:MainProcess]
    2023-03-08 17:29:21,082 [DEBUG] Connected to remote axon aha://axon... [cortex.py:onlink:MainThread:MainProcess]
    2023-03-08 17:29:21,174 [DEBUG] Connected to remote jsonstor aha://jsonstor... [cortex.py:onlink:MainThread:MainProcess]


CLI Tooling Example
^^^^^^^^^^^^^^^^^^^

Synapse services and tooling assumes that IP and Port combinations registered with the AHA service are reachable.
This example shows a way to connect to the Cortex from **outside** of the Kubernetes cluster without resolving service
information via Aha. Communication between services inside of the cluster does not need to go through these steps.
This does assume that your local environment has the Python synapse package available.

First add a user to the Cortex:

.. highlight:: bash

::

    $ kubectl exec -it deployment/cortex00 -- python -m synapse.tools.moduser --add --admin true visi
    Adding user: visi
    ...setting admin: true

Then we need to generate a user provisioning URL:

.. highlight:: bash

::

    $ kubectl exec -it deployment/aha -- python -m synapse.tools.aha.provision.user visi
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/5d67f84c279afa240062d2f3b32fdb99?certhash=e32d0e1da01b5eb0cefd4c107ddc8c8221a9a39bce25dea04f469c6474d84a23

Port-forward the AHA provisioning service to your local environment:

.. highlight:: bash

::

    $ kubectl port-forward service/aha 27272:provisioning

Run the enroll tool to create a user certificate pair and have it signed by the Aha service. We replace the service DNS
name of ``aha.default.svc.cluster.local`` with ``localhost`` in this example.

.. highlight:: bash

::

    $ python -m synapse.tools.aha.enroll ssl://localhost:27272/5d67f84c279afa240062d2f3b32fdb99?certhash=e32d0e1da01b5eb0cefd4c107ddc8c8221a9a39bce25dea04f469c6474d84a23
    Saved CA certificate: /home/visi/.syn/certs/cas/default.svc.cluster.local.crt
    Saved user certificate: /home/visi/.syn/certs/users/visi@default.svc.cluster.local.crt
    Updating known AHA servers

The Aha service port-forward can be disabled, and replaced with a port-forward for the Cortex service:

.. highlight:: bash

::

    kubectl port-forward service/cortex 27492:telepath

Then connect to the Cortex via the Storm CLI, using the URL
``ssl://visi@localhost:27492/?hostname=00.cortex.default.svc.cluster.local``.

.. highlight:: bash

::

    $ python -m synapse.tools.storm "ssl://visi@localhost:27492/?hostname=00.cortex.default.svc.cluster.local"

    Welcome to the Storm interpreter!

    Local interpreter (non-storm) commands may be executed with a ! prefix:
        Use !quit to exit.
        Use !help to see local interpreter commands.

    storm>

The Storm CLI tool can then be used to run Storm commands.

Commercial Components
^^^^^^^^^^^^^^^^^^^^^

For Synapse-Enterprise users, deploying commercial components can follow a similar pattern. The following is an example
of deploying Optic, the Synapse User Interface, as it is a common part of a Synapse deployment. This enables users to
interact with Synapse via a web browser, instead of using the CLI tools. This example shows accessing the service via
a port-forward. This example does not contain the full configuration settings you will need for a production deployment
of Optic, please see :ref:`synapse-ui` for more information.

.. note::

    Optic is available as a part of the **Synapse Enterprise** commercial offering. This example assumes that the
    Kubernetes cluster has a valid ``imagePullSecret`` named ``regcred`` which can access commercial images.

The following ``optic.yaml`` can be used as the basis to deploy Optic.

.. literalinclude:: ./kubernetes/optic.yaml
    :language: yaml

Before we deploy that, we need to create the Aha provisioning URL. We do this via ``kubectl exec``. That should look
like the following:

.. highlight:: bash

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.optic
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/3f692cda9dfb152f74a8a0251165bcc4?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_OPTIC_AHA_PROVISION`` environment variable, so that block looks like the
following:

.. highlight:: yaml

::

    - name: SYN_OPTIC_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/3f692cda9dfb152f74a8a0251165bcc4?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"


This can then be deployed via ``kubectl apply``:

.. highlight:: bash

::

    $ kubectl apply -f optic.yaml
    persistentvolumeclaim/example-optic00 created
    deployment.apps/optic00 created
    service/optic created

You can see the Optic logs as well. These show provisioning and listening for traffic, as well as the connection being
made to the Axon, Cortex, and JSONStor services:

.. highlight:: bash

::

    $ kubectl logs --tail 30 -l app.kubernetes.io/instance=optic00
    2023-03-08 17:32:40,149 [INFO] log level set to DEBUG [common.py:setlogging:MainThread:MainProcess]
    2023-03-08 17:32:40,150 [DEBUG] Set config valu from envar: [SYN_OPTIC_CORTEX] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,150 [DEBUG] Set config valu from envar: [SYN_OPTIC_AXON] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,151 [DEBUG] Set config valu from envar: [SYN_OPTIC_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,152 [DEBUG] Set config valu from envar: [SYN_OPTIC_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,153 [INFO] Provisioning optic from AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:32:40,264 [DEBUG] Set config valu from envar: [SYN_OPTIC_CORTEX] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,265 [DEBUG] Set config valu from envar: [SYN_OPTIC_AXON] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,265 [DEBUG] Set config valu from envar: [SYN_OPTIC_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,266 [DEBUG] Set config valu from envar: [SYN_OPTIC_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:45,181 [INFO] Done provisioning optic AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:32:45,247 [INFO] optic wwwroot: /usr/local/lib/python3.10/dist-packages/optic/site [app.py:initServiceStorage:MainThread:MainProcess]
    2023-03-08 17:32:45,248 [WARNING] Waiting for remote jsonstor... [app.py:initJsonStor:MainThread:MainProcess]
    2023-03-08 17:32:45,502 [INFO] Connected to JsonStor at [aha://jsonstor...] [app.py:initJsonStor:MainThread:MainProcess]
    2023-03-08 17:32:45,504 [INFO] Waiting for connection to Cortex [app.py:_initOpticCortex:MainThread:MainProcess]
    2023-03-08 17:32:45,599 [INFO] Connected to Cortex at [aha://cortex...] [app.py:_initOpticCortex:MainThread:MainProcess]
    2023-03-08 17:32:45,930 [INFO] Connected to Axon at [aha://axon...] [app.py:onaxonlink:MainThread:MainProcess]
    2023-03-08 17:32:45,937 [DEBUG] Email settings/server not configured or invalid. [app.py:initEmailApis:asyncio_0:MainProcess]
    2023-03-08 17:32:45,975 [INFO] dmon listening: ssl://0.0.0.0:0?hostname=00.optic.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initServiceNetwork:MainThread:MainProcess]
    2023-03-08 17:32:45,976 [WARNING] NO CERTIFICATE FOUND! generating self-signed certificate. [cell.py:addHttpsPort:MainThread:MainProcess]
    2023-03-08 17:32:47,773 [INFO] https listening: 4443 [cell.py:initServiceNetwork:MainThread:MainProcess]
    2023-03-08 17:32:47,773 [INFO] ...optic API (telepath): ssl://0.0.0.0:0?hostname=00.optic.default.svc.cluster.local&ca=default.svc.cluster.local [cell.py:initFromArgv:MainThread:MainProcess]
    2023-03-08 17:32:47,773 [INFO] ...optic API (https): 4443 [cell.py:initFromArgv:MainThread:MainProcess]

Once Optic is connected, we will need to set a password for the user we previously created in order to log in. This can
be done via ``kubectl exec``, setting the password for the user on the Cortex:

.. highlight:: bash

::

    $ kubectl exec -it deployment/cortex00 -- python -m synapse.tools.moduser --passwd secretPassword visi
    Modifying user: visi
    ...setting passwd: secretPassword

Enable a port-forward to connect to the Optic service:

.. highlight:: bash

::

    $ kubectl port-forward service/optic 4443:https

You can then use a Chrome browser to navigate to ``https://localhost:4443`` and you should be prompted with an Optic
login screen. You can enter your username and password ( ``visi`` and ``secretPassword`` ) in order to login to Optic.

Practical Considerations
++++++++++++++++++++++++

The following items should be considered for Kubernetes deployments intended for production use cases:

  Healthchecks
    These examples use large ``startupProbe`` failure values. Vertex recommends these large values, since service
    updates may have automatic data migrations which they perform at startup. These will be performed before a service
    has enabled any listeners which would respond to healthcheck probes. The large value prevents a service from being
    terminated prior to a long running data migration completing.

  Ingress and Load Balancing
    The use of ``kubectl port-forward`` may not be sustainable in a production environment. It is common to use a form
    of ingress controller or load balancer for external services to reach services such as the Cortex or Optic
    applications. It is common for the Optic UI or the Cortex HTTP API to be exposed to end users since that often has
    a simpler networking configuration than exposing Telepath services on Aha and the Cortex.

  Log aggregation
    Many Kubernetes clusters may perform some sort of log aggregation for the containers running in them. If your log
    aggregation solution can parse JSON formatted container logs, you can set the ``SYN_LOG_STRUCT`` environment
    variable to ``"true"`` to enable structured log output. See :ref:`devops-task-logging` for more information about that
    option.

  Node Selectors
    These examples do not use any node selectors to bind pods to specific nodes or node types. Node selectors on the
    podspec can be used to constrain different services to different types of nodes. For example, they can be used to
    ensure the Cortex is deployed to a node which has been provisioned as a high memory node for that purpose.

  PVC
    The previous examples used relatively small volume claim sizes for demonstration purposes. A ``storageClass``
    which can be dynamically resized will be helpful in the event of needing to grow the storage used by a deployment.
    This is a common feature for managed Kubernetes instances.

.. _orch-kubernetes-sysctl:

Performance Tuning in Kubernetes
++++++++++++++++++++++++++++++++

It is common for Kubernetes to be executed in a managed environment, where an operator may not have direct access to
the underlying hosts. In that scenario, applying the system configurations detailed in :ref:`devops-task-performance`
may be difficult. The following example shows a DaemonSet which runs a privileged pod, that ensures that the desired
``sysctl`` values are set on the host. You may need to modify this to meet any requirements which are specific to
your deployment.

The following ``sysctl.yaml`` can be used as the basis to deploy these modifications.

.. literalinclude:: ./kubernetes/sysctl.yaml
    :language: yaml


This can be deployed via ``kubectl apply``. That will create the DaemonSet for you..

.. highlight:: bash

::

    $ kubectl apply -f sysctl_dset.yaml
    daemonset.apps/setsysctl created

You can see the sysctl pods by running the following command:

.. highlight:: bash

::

    $ kubectl get pods -l app.kubernetes.io/component=sysctl -o wide


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
.. _Synapse-Backup: ../../../projects/backup/en/latest/
.. _Synapse-S3: ../../../projects/s3/en/latest/
.. _hypergraph: https://en.wikipedia.org/wiki/Hypergraph
.. _warnings: https://docs.python.org/3/library/warnings.html
.. _strftime: https://docs.python.org/3/library/time.html#time.strftime
.. _fullmatch: https://docs.python.org/3/library/re.html#re.fullmatch
.. _curl: https://curl.se/
.. _jq: https://github.com/jqlang/jq
