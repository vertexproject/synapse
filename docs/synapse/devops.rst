.. toctree::
    :titlesonly:

.. _devopsguide:

Synapse DevOps Guide
####################

Deployment Walk-Through
=======================

For this walk-through, you will need a staging system or docker container where you have the open-source
synapse package installed.  You may also use the `_synapse-quickstart` container. We will assume you are
planning to use ``docker-compose`` for this deployment, but the setup instructions are mostly the same
regardless of your chosen orchestration method.

Chose your Aha network name
---------------------------

Your Aha network name is a namespace where the services for this deployment will live.  While it's not
required to be a valid FQDN, it definitely makes things a bit easier in the long run. For this example,
we will be using ``loop.vertex.link`` which The Vertex Project maintains as a wild-card DNS entry which
resolves to ``127.0.0.1``.

For your production deployment, you likely want to chose something like ``syn.yourcompany.com``.

Generate deployment files
-------------------------

The ``geninfra`` tool can be used to easily generate FIXME::
    python -m synapse.tools.geninfra loop.vertex.link
    <FIXME> paste in output here

Create a DNS A or AAAA record
-----------------------------

You will only need a DNS A or AAAA record to resolve your **Aha** host.  All of the other Storm Services,
including commercial Advanced Power-Ups, will use the **Aha** service to locate one another. For this example,
the **Aha** service was generated using the name ``aha.loop.vertex.link`` which resolves to ``127.0.0.1`` and
should work for a loopback only deployment example.

Copy your service directories
-----------------------------

For a real deployment, you are likely running some of the containers on different hosts. You can use ``scp`` or
any other file transfer mechanism to move a service directory to the host you would like to run it on. The following
notional example may be skipped if you are using ``loop.vertex.link``::
    scp loop.vertex.link/aha root@host00.vertex.link:/srv/aha.loop.vertex.link
    scp loop.vertex.link/axon root@host01.vertex.link:/srv/axon.loop.vertex.link
    scp loop.vertex.link/cortex root@host02.vertex.link:/srv/cortex.loop.vertex.link

Start your containers
---------------------

If you are using ``loop.vertex.link`` as an example, you can start your containers locally::
    docker-compose -f aha/docker-compose.yaml up -d
    docker-compose -f axon/docker-compose.yaml up -d
    docker-compose -f cortex/docker-compose.yaml up -d

If you moved the service directories to other hosts, you will need to execute the ``docker-compose`` commands from
a shell on those hosts.  For example::
    invisigoth@visi01:~/example/$ ssh root@host00.vertex.link
    root@host00:~/# cd /srv/aha.loop.vertex.link
    root@host00:~/srv/aha.loop.vertex.link# docker-compose up -d

Updating your containers
------------------------

The Vertex Project regularly releases updated containers.  You can see a real-time announcement of each service
release in the ``#synapse-releases`` channel in our `_Synapse slack`. To update a container you need to pull
the updated definition and restart the container::
    invisigoth@visi01:~/example/$ ssh root@host00.vertex.link
    root@host00:~/# cd /srv/aha.loop.vertex.link
    root@host00:~/srv/aha.loop.vertex.link# docker-compose pull
    root@host00:~/srv/aha.loop.vertex.link# docker-compose down
    root@host00:~/srv/aha.loop.vertex.link# docker-compose up -d

Devops Best Practices
=====================

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

Tips for Better Performance
---------------------------

The Cortex process acts as the database for all configuration and graph data.  Inasmuch, it interacts with the
operating system in similar ways as other database systems like PostgreSQL or MySQL, and recommendations for good
performance for other database systems may also apply to running Synapse services.

Keep your RAM/data ratio high
*****************************

Database systems run best when the amount of RAM available exceeds the size of the data being stored. While it's
not always practical or affordable to have more RAM than data, keeping that ratio as high as possible has a dramatic
effect on performance.

Use low-latency storage
***********************

As the database accesses persistent storage, minimizing storage latency is important for a high performance.
Locating a Synapse service on a filesystem backed to a mechanical hard drive is strongly discouraged.  For the same
reason, running the Service on an NFS filesystem (including NFS-based systems like AWS EFS) is *strongly* discouraged.

Kernel Tuning
*************

Default kernel parameters on most Linux distributions are not optimized for database performance. We recommend
adding the folling lines to ``/etc/sysctl.conf`` on all systems being used to host Synapse services::
    vm.swappiness=10
    vm.dirty_expire_centisecs=20
    vm.dirty_writeback_centisecs=20

The following describes the effects of relevant tuning parameters.

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

Logging
-------

SYN_LOG_LEVEL
*************

Logging verbosity can be controlled by using the ``SYN_LOG_LEVEL`` environment variable.  The ``SYN_LOG_LEVEL``
variable can be specified as one of the following values.

``CRITICAL``

``ERRROR``

``WARNING``

``INFO``

``DEBUG``

SYN_LOG_STRUCT
**************

Structured logging may be enabled by using the ``SYN_LOG_STRUCT`` environment variable. The ``SYN_LOG_STRUCT`` variable
will enable structured logging if it is not set to a false value such as ``0`` or ``false``.

When structured logging is enabled logs will be emitted in JSON lines format. An example of that output is shown below,
showing the startup of a Cortex with structured logging enabled::

    $ SYN_LOG_LEVEL=INFO SYN_LOG_STRUCT=true python -m synapse.servers.cortex cells/core00/
    {"message": "log level set to INFO", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "common.py", "func": "setlogging"}, "level": "INFO", "time": "2021-06-28 15:47:54,825"}
    {"message": "dmon listening: tls://0.0.0.0:27492/?ca=test", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "cell.py", "func": "initServiceNetwork"}, "level": "INFO", "time": "2021-06-28 15:47:55,101"}
    {"message": "...cortex API (telepath): tls://0.0.0.0:27492/?ca=test", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "cell.py", "func": "initFromArgv"}, "level": "INFO", "time": "2021-06-28 15:47:55,102"}
    {"message": "...cortex API (https): 4443", "logger": {"name": "synapse.lib.cell", "process": "MainProcess", "filename": "cell.py", "func": "initFromArgv"}, "level": "INFO", "time": "2021-06-28 15:47:55,103"}

These structured logs are designed to be easy to ingest into third party log collection platforms. They contain the log
message, level, time, and metadata about where the log message came from. The following is a pretty printed example::

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

When exceptions are logged with structured logging, we capture additional information about the exception. In the following
example, we also have the query text, username and user iden available in the log message pretty-printed log message::

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

.. _devops-general-migrations:

Data Migrations
---------------

In the event that a Synapse release contains a data migration for a part of the Synapse ecosystem, the Changelog will
indicate what component is being migrated and why. This will be made under the ``Automated Migrations`` header, at the
top of the changelog.

It is *strongly* recommended that you have a recently tested backup generated before applying an update with a data
migration.

Automatic data migrations may cause additional startup times on the first boot of the version. For production deployments
it may be worth testing how long the conversion takes by running it on a recent backup in a development environment.

Service Specifics
=================

.. toctree::
    :titlesonly:

    devops/aha
    devops/axon
    devops/cortex
    devops/cryotank

Orchestration
=============
.. toctree::
    :titlesonly:

    devops/orch/kubernetes

.. _index:              ../index.html
.. _synapse-quickstart: https://github.com/vertexproject/synapse-quickstart
.. _Synapse slack: https://v.vtx.lk/join-slack
.. _Python logging: https://docs.python.org/3.8/library/logging.html#logging-levels
