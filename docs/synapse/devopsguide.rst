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
    handoff. It is **critical that you not bring the previous leader back online** once this has been done. To regain
    redundancy, deploy a new mirror using the AHA provisioning process described in the :ref:`deploymentguide`.

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

    version: "3.3"
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

    version: "3.3"
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

    version: "3.3"
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

That directory will be mounted at ``/vertex/boothooks``. The following docker-compose file shows mounting that
directory into the container and setting environment variables for the script to use::

  version: "3.3"
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

    version: "3.3"
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
~~~~~~~~~~~~~~~~~~

The following examples walks through deploying an example Synapse deployment ( based on :ref:`deploymentguide` ), but
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
+++

The following ``aha.yaml`` can be used to deploy an Aha service.

.. literalinclude:: ./kubernetes/aha.yaml
    :language: yaml

This can be deployed via ``kubectl apply``. That will create the PVC, deployment, and service.

::

    $ kubectl apply -f aha.yaml
    persistentvolumeclaim/example-aha created
    deployment.apps/aha created
    service/aha created

You can see the startup logs as well:

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
++++


The following ``axon.yaml`` can be used as the basis to deploy an Axon service.

.. literalinclude:: ./kubernetes/axon.yaml
    :language: yaml

Before we deploy that, we need to create the Aha provisioning URL. We can do that via ``kubectl exec``. That should look
like the following:

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.axon
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/39a33f6e3fa2b512552c2c7770e28d30?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_AXON_AHA_PROVISION`` environment variable, so that block looks like the
following:

::

    - name: SYN_AXON_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/39a33f6e3fa2b512552c2c7770e28d30?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"

This can then be deployed via ``kubectl apply``:

::

    $ kubectl apply -f axon.yaml
    persistentvolumeclaim/example-axon00 unchanged
    deployment.apps/axon00 created

You can see the Axon logs as well. These show provisioning and listening for traffic:

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
++++++++

The following ``jsonstor.yaml`` can be used as the basis to deploy a JSONStor service.

.. literalinclude:: ./kubernetes/jsonstor.yaml
    :language: yaml

Before we deploy that, we need to create the Aha provisioning URL. We can do that via ``kubectl exec``. That should look
like the following:

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.jsonstor
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/cbe50bb470ba55a5df9287391f843580?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_JSONSTOR_AHA_PROVISION`` environment variable, so that block lookslike the
following:

::

    - name: SYN_JSONSTOR_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/cbe50bb470ba55a5df9287391f843580?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"


This can then be deployed via ``kubectl apply``:

::

    $ kubectl apply -f jsonstor.yaml
    persistentvolumeclaim/example-jsonstor00 created
    deployment.apps/jsonstor00 created

You can see the JSONStor logs as well. These show provisioning and listening for traffic:

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
++++++

The following ``cortex.yaml`` can be used as the basis to deploy the Cortex.

.. literalinclude:: ./kubernetes/cortex.yaml
    :language: yaml

Before we deploy that, we need to create the Aha provisioning URL. This uses a fixed listening port for the Cortex, so
that we can later use port-forwarding to access the Cortex service. We do this via ``kubectl exec``. That should look
like the following:

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.cortex --dmon-port 27492
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/c06cd588e469a3b7f8a56d98414acf8a?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_CORTEX_AHA_PROVISION`` environment variable, so that block lookslike the
following:

::

    - name: SYN_CORTEX_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/c06cd588e469a3b7f8a56d98414acf8a?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"


This can then be deployed via ``kubectl apply``:

::

    $ kubectl apply -f cortex.yaml
    persistentvolumeclaim/example-cortex00 created
    deployment.apps/cortex00 created
    service/cortex created


You can see the Cortex logs as well. These show provisioning and listening for traffic, as well as the connection being
made to the Axon and JSONStor services:

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
+++++++++++++++++++

Synapse services and tooling assumes that IP and Port combinations registered with the AHA service are reachable.
This example shows a way to connect to the Cortex from **outside** of the Kubernetes cluster without resolving service
information via Aha. Communication between services inside of the cluster does not need to go through these steps.
This does assume that your local environment has the Python synapse package available.

First add a user to the Cortex:

::

    $ kubectl exec -it deployment/cortex00 -- python -m synapse.tools.moduser --add --admin true visi
    Adding user: visi
    ...setting admin: true

Then we need to generate a user provisioning URL:

::

    $ kubectl exec -it deployment/aha -- python -m synapse.tools.aha.provision.user visi
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/5d67f84c279afa240062d2f3b32fdb99?certhash=e32d0e1da01b5eb0cefd4c107ddc8c8221a9a39bce25dea04f469c6474d84a23

Port-forward the AHA provisioning service to your local environment:

::

    kubectl port-forward service/aha 27272:provisioning

Run the enroll tool to create a user certificate pair and have it signed by the Aha service. We replace the service DNS
name of ``aha.default.svc.cluster.local`` with ``localhost`` in this example.

::

    $ python -m synapse.tools.aha.enroll ssl://localhost:27272/5d67f84c279afa240062d2f3b32fdb99?certhash=e32d0e1da01b5eb0cefd4c107ddc8c8221a9a39bce25dea04f469c6474d84a23
    Saved CA certificate: /home/visi/.syn/certs/cas/default.svc.cluster.local.crt
    Saved user certificate: /home/visi/.syn/certs/users/visi@default.svc.cluster.local.crt
    Updating known AHA servers

The Aha service port-forward can be disabled, and replaced with a port-forward for the Cortex service:

::

    kubectl port-forward service/cortex 27492:telepath

Then connect to the Cortex via the Storm CLI, using the URL
``ssl://visi@localhost:27492/?hostname=00.cortex.default.svc.cluster.local``.

::

    $ python -m synapse.tools.storm "ssl://visi@localhost:27492/?hostname=00.cortex.default.svc.cluster.local"

    Welcome to the Storm interpreter!

    Local interpreter (non-storm) commands may be executed with a ! prefix:
        Use !quit to exit.
        Use !help to see local interpreter commands.

    storm>

The Storm CLI tool can then be used to run Storm commands.

Commercial Components
+++++++++++++++++++++

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

::

    $ kubectl exec deployment/aha -- python -m synapse.tools.aha.provision.service 00.optic
    one-time use URL: ssl://aha.default.svc.cluster.local:27272/3f692cda9dfb152f74a8a0251165bcc4?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f

We want to copy that URL into the ``SYN_OPTIC_AHA_PROVISION`` environment variable, so that block lookslike the
following:

::

    - name: SYN_OPTIC_AHA_PROVISION
      value: "ssl://aha.default.svc.cluster.local:27272/3f692cda9dfb152f74a8a0251165bcc4?certhash=09c8329ed29b89b77e0a2fdc23e64aea407ad4d7e71d67d3fea92ddd9466592f"


This can then be deployed via ``kubectl apply``:

::

    $ kubectl apply -f optic.yaml
    persistentvolumeclaim/example-optic00 created
    deployment.apps/optic00 created
    service/optic created

You can see the Optic logs as well. These show provisioning and listening for traffic, as well as the connection being
made to the Axon, Cortex, and JSONStor services:

::

    $ kubectl logs --tail 30 -l app.kubernetes.io/instance=optic00
    2023-03-08 17:32:40,149 [INFO] log level set to DEBUG [common.py:setlogging:MainThread:MainProcess]
    2023-03-08 17:32:40,150 [DEBUG] Set config valu from envar: [SYN_OPTIC_CORTEX] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,150 [DEBUG] Set config valu from envar: [SYN_OPTIC_AXON] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,151 [DEBUG] Set config valu from envar: [SYN_OPTIC_JSONSTOR] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,151 [DEBUG] Set config valu from envar: [SYN_OPTIC_HTTPS_PORT] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,152 [DEBUG] Set config valu from envar: [SYN_OPTIC_AHA_PROVISION] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,153 [INFO] Provisioning optic from AHA service. [cell.py:_bootCellProv:MainThread:MainProcess]
    2023-03-08 17:32:40,264 [DEBUG] Set config valu from envar: [SYN_OPTIC_CORTEX] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,265 [DEBUG] Set config valu from envar: [SYN_OPTIC_AXON] [config.py:setConfFromEnvs:MainThread:MainProcess]
    2023-03-08 17:32:40,265 [DEBUG] Set config valu from envar: [SYN_OPTIC_JSONSTOR] [config.py:setConfFromEnvs:MainThread:MainProcess]
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

::

    $ kubectl exec -it deployment/cortex00 -- python -m synapse.tools.moduser --passwd secretPassword visi
    Modifying user: visi
    ...setting passwd: secretPassword

Enable a port-forward to connect to the Optic service:

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
    applications.

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

Considerations for transitioning to commercial components
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Cortex is often not exposed, or only exposed via the HTTP service.
The Optic user interface component is commonly exposed as an http service. This is frequently done behind an
application load balancer in practice.

.. _orch-kubernetes-sysctl:

Performance Tuning in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is common for Kubernetes to be executed in a managed environment, where an operator may not have direct access to
the underlying hosts. In that scenario, applying the system configurations detailed in :ref:`devops-task-performance`
may be difficult. The following example shows a DaemonSet which runs a privileged pod, that ensures that the desired
``sysctl`` values are set on the host. You may need to modify this to meet any requirements which are specific to
your deployment.

The following ``sysctl.yaml`` can be used as the basis to deploy these modifications.

.. literalinclude:: ./kubernetes/sysctl.yaml
    :language: yaml


This can be deployed via ``kubectl apply``. That will create the DaemonSet for you..

::

    $ kubectl apply -f sysctl_dset.yaml
    daemonset.apps/setsysctl created

You can see the sysctl pods by running the following command:

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
