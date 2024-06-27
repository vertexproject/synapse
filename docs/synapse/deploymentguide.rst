.. _deploymentguide:

Synapse Deployment Guide
########################

Introduction
============

This step-by-step guide will walk you through a production-ready Synapse deployment. Services will be
configured to register with ``AHA`` for service discovery and to prepare for future devops tasks such
as promoting a mirror to leader and provisioning future Synapse Advanced Power-Ups.

This guide will also walk you through deploying all Synapse services using TLS to authenticate both
servers and clients using client-certificates to minimize the need for secrets management by eliminating
passwords from all telepath URLs.

For the purposes of this guide, we will use ``docker compose`` as a light-weight orchestration mechanism.
The steps, configurations, and volume mapping guidance given in this guide apply equally to other container
orchestration mechanisms such as Kubernetes but for simplicity's sake, this guide will only cover
``docker compose`` based deployments.

.. note::
    Due to `known networking limitations of docker on Mac`_ we do **not** support or recommend the use
    of Docker for Mac for testing or deploying production Synapse instances. Containers run within
    separate ``docker compose`` commands will not be able to reliably communicate with each other.

Synapse services **require persistent storage**. Each ``docker`` container expects persistent storage to be available
within the directory ``/vertex/storage`` which should be a persistent mapped volume. Only one container may run from a
given volume at a time.

.. note::
    To allow hosts to be provisioned on one system, this guide instructs you to disable HTTP API listening
    ports on all services other than the main Cortex. You may remove those configuration options if you are
    running on separate hosts or select alternate ports which do not conflict.

Prepare your Hosts
==================

Ensure that you have an updated install of docker_ and docker-compose_.

In order to help you run the Synapse service containers as a non-root user, Synapse service docker containers
have been preconfigured with a user named ``synuser`` with UID ``999``. You may replace ``999`` in the configs
below, but keep in mind that doing so will result in the container not having a name for the user. We recommend
that you do **not** use the Linux user ``nobody`` for this purpose.

Default kernel parameters on most Linux distributions are not optimized for database performance. We recommend
adding the following lines to ``/etc/sysctl.conf`` on all systems being used to host Synapse services::

    vm.swappiness=10
    vm.dirty_expire_centisecs=20
    vm.dirty_writeback_centisecs=20

See :ref:`devops-task-performance` for a list of additional tuning options.

We will use the directory ``/srv/syn/`` on the host systems as the base directory used to deploy
the Synapse services. Each service will be deployed in separate ``/srv/syn/<svcname>`` directories. This
directory can be changed to whatever you would like, and the services may be deployed to any host provided
that the hosts can directly connect to each other.  It is critical to performance that these storage volumes
be low-latency. More latent storage mechanisms such as spinning disks, NFS, or EFS should be avoided!

We highly recommend that hosts used to run Synapse services deploy a log aggregation agent to make it easier
to view the logs from the various containers in a single place.

When using AHA, you may run any of the **other** services on additional hosts as long as they can connect
directly to the AHA service.  You may also shutdown a service, move it's volume to a different host, and
start it backup without changing anything.

Decide on a Name
================

Throughout the examples, we will be using ``<yournetwork>`` as the AHA network name which is also used as the
common-name (CN) for the CA certificate. This should be changed to an appropriate network name used by your
synapse deployment such as ``syn.acmecorp.com``. We will use ``<yournetwork>`` in the following configs to
specify locations which should be replaced with your selected AHA network name. For a **test** deployment which
runs **all** docker containers on one host, you may use ``loop.vertex.link``.

.. note::
    It is important that you choose a name and stick with it for a given deployment. Once we begin generating
    host and service account certificates, changing this name will be difficult.

Deploy AHA Service
==================

The AHA service is used for service discovery and acts as a CA to issue host/user certificates used to link
Synapse services. Other Synapse services will need to be able to resolve the IP address of the AHA service
by name, so it is likely that you need to create a DNS A/AAAA record in your existing resolver. When you are
using AHA, the only host that needs DNS or other external name resolution is the AHA service.

.. note::
    It is important to ensure that ``aha.<yournetwork>`` is resolvable via DNS or docker container service
    name resolution from within the container environment! There are configuration options you may use if
    this is impossible, but the configuration is far simpler if we can make this assumption.

Create the container directory::

    mkdir -p /srv/syn/aha/storage

Create the ``/srv/syn/aha/docker-compose.yaml`` file with contents::

    services:
      aha:
        user: "999"
        image: vertexproject/synapse-aha:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
            - ./storage:/vertex/storage
        environment:
            - SYN_AHA_HTTPS_PORT=null
            - SYN_AHA_AHA_NAME=aha
            - SYN_AHA_DNS_NAME=aha.<yuournetwork>

.. note::

    Don't forget to replace ``<yournetwork>`` with your chosen network name!

Change ownership of the storage directory to the user you will use to run the container::

    chown -R 999 /srv/syn/aha/storage

Start the container using ``docker compose``::

    docker compose --file /srv/syn/aha/docker-compose.yaml pull
    docker compose --file /srv/syn/aha/docker-compose.yaml up -d

To view the container logs at any time you may run the following command on the *host* from the
``/srv/syn/aha`` directory::

    docker compose logs -f

You may also execute a shell inside the container using ``docker compose`` from the ``/srv/syn/aha``
directory on the *host*. This will be necessary for some of the additional provisioning steps::

    docker compose exec aha /bin/bash


.. _deploy_axon:

Deploy Axon Service
===================

In the Synapse service architecture, an Axon provides a place to store arbitrary bytes/files as binary
blobs and exposes APIs for streaming files in and out regardless of their size.  Given sufficient file system
size, an Axon can be used to efficiently store and retrieve very large files as well as a high number
(easily billions) of files.

**Inside the AHA container**

Generate a one-time use provisioning URL::

    python -m synapse.tools.aha.provision.service 00.axon

These one-time use URLs are used to connect to the Aha service, retrieve configuration data, and provision SSL
certificates for the service. When this is done, the service records that the URL has been used in its persistent
storage, and will not attempt to perform the provisioning process again unless the URL changes. If the provisioning URL
is reused, services will encounter **NoSuchName** errors and fail to start up - this indicates a service has attempted
to re-use the one-time use URL!

.. note::

    We strongly encourage you to use a numbered hierarchical naming convention for services where the
    first part of the name is a 0 padded number and the second part is the service type. The above example
    ``00.axon`` will allow you to deploy mirror instances in the future, such as ``01.axon``, where the AHA
    name ``axon.<yournetwork>`` will automatically resolve to which ever one is the current leader.

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/00.axon/storage
    chown -R 999 /srv/syn/00.axon/storage

Create the ``/srv/syn/00.axon/docker-compose.yaml`` file with contents::

    services:
      00.axon:
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

.. note::

    Don't forget to replace your one-time use provisioning URL!

Start the container::

    docker compose --file /srv/syn/00.axon/docker-compose.yaml pull
    docker compose --file /srv/syn/00.axon/docker-compose.yaml up -d

Deploy JSONStor Service
=======================

**Inside the AHA container**

Generate a one-time use provisioning URL::

    python -m synapse.tools.aha.provision.service 00.jsonstor

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/00.jsonstor/storage
    chown -R 999 /srv/syn/00.jsonstor/storage

Create the ``/srv/syn/00.jsonstor/docker-compose.yaml`` file with contents::

    services:
      00.jsonstor:
        user: "999"
        image: vertexproject/synapse-jsonstor:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
            - ./storage:/vertex/storage
        environment:
            # disable HTTPS API for now to prevent port collisions
            - SYN_JSONSTOR_HTTPS_PORT=null
            - SYN_JSONSTOR_AHA_PROVISION=ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

.. note::

    Don't forget to replace your one-time use provisioning URL!

Start the container::

    docker compose --file /srv/syn/00.jsonstor/docker-compose.yaml pull
    docker compose --file /srv/syn/00.jsonstor/docker-compose.yaml up -d

Deploy Cortex Service
=====================

**Inside the AHA container**

Generate a one-time use provisioning URL::

    python -m synapse.tools.aha.provision.service 00.cortex

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/00.cortex/storage
    chown -R 999 /srv/syn/00.cortex/storage

Create the ``/srv/syn/00.cortex/docker-compose.yaml`` file with contents::

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
            - SYN_CORTEX_AHA_PROVISION=ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

.. note::

    Don't forget to replace your one-time use provisioning URL!

.. note::

    The values ``aha://axon...`` and ``aha://jsonstor...`` can be used as-is without changing
    them because the AHA network (provided by the provisioning server) is automatically subtituted
    in any ``aha://`` scheme URL ending with ``...``

Start the container::

    docker compose --file /srv/syn/00.cortex/docker-compose.yaml pull
    docker compose --file /srv/syn/00.cortex/docker-compose.yaml up -d

Remember, you can view the container logs in real-time using::

    docker compose --file /srv/syn/00.cortex/docker-compose.yaml logs -f

.. _deployment-guide-mirror:

Deploy Cortex Mirror (optional)
===============================

**Inside the AHA container**

Generate a one-time use URL for provisioning from *inside the AHA container*::

    python -m synapse.tools.aha.provision.service 01.cortex --mirror cortex

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container storage directory::

    mkdir -p /srv/syn/01.cortex/storage
    chown -R 999 /srv/syn/01.cortex/storage

Create the ``/srv/syn/01.cortex/docker-compose.yaml`` file with contents::

    services:
      01.cortex:
        user: "999"
        image: vertexproject/synapse-cortex:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
            - ./storage:/vertex/storage
        environment:
            - SYN_CORTEX_AXON=aha://axon...
            - SYN_CORTEX_JSONSTOR=aha://jsonstor...
            # disable HTTPS API for now to prevent port collisions
            - SYN_CORTEX_HTTPS_PORT=null
            - SYN_CORTEX_AHA_PROVISION=ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

.. note::

    Don't forget to replace your one-time use provisioning URL!

Start the container::

    docker compose --file /srv/syn/01.cortex/docker-compose.yaml pull
    docker compose --file /srv/syn/01.cortex/docker-compose.yaml up -d

.. note::

    If you are deploying a mirror from an existing large Cortex, this startup may take a while to complete
    initialization.

.. _enroll_cli_users:

Enroll CLI Users
================

A Synapse user is generally synonymous with a user account on the Cortex. To bootstrap CLI users who will
have Cortex access using the Telepath API, we will need to add them to the Cortex and generate user
certificates for them. To add a new admin user to the Cortex, run the following command from **inside the
Cortex container**::

    python -m synapse.tools.moduser --add --admin true visi

.. note::
    If you are a Synapse Enterprise customer, using the Synapse UI with SSO, the admin may now login to the
    Synapse UI. You may skip the following steps if the admin will not be using CLI tools to access the Cortex.

Then we will need to generate a one-time use URL they may use to generate a user certificate. Run the
following command from **inside the AHA container** to generate a one-time use URL for the user::

    python -m synapse.tools.aha.provision.user visi

You should see output that looks similar to this::

    one-time use URL: ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

Then the **user** may run::

    python -m synapse.tools.aha.enroll ssl://aha.<yournetwork>:27272/<guid>?certhash=<sha256>

Once they are enrolled, they will have a user certificate located in ``~/.syn/certs/users`` and their telepath
configuration located in ``~/.syn/telepath.yaml`` will be updated to reflect the use of the AHA server. From there
the user should be able to use standard Synapse CLI tools using the ``aha://`` URL such as::

    python -m synapse.tools.storm aha://visi@cortex.<yournetwork>

.. _deployment-guide-storm-pool:

Configure a Storm Query Pool (optional)
=======================================

A Cortex may be configured to use a pool of mirrors in order to offload Storm query execution and distribute
query load among a configurable group of mirrors. We will assume you have configured two additional mirrors named
``01.cortex...`` and ``02.cortex...`` using the process described in the previous :ref:`deployment-guide-mirror`
step. In our example, we will also assume that the mirrors will be used for both query parallelism and for graceful
promotions to minimize downtime during upgrades and optimization.

The following commands are run using the Storm CLI tool discussed in the :ref:`enroll_cli_users` section. First, use
the Storm CLI to run the ``aha.pool.add`` command to create a new AHA pool::

    aha.pool.add pool00.cortex...

Then add the Cortex leader as well as the two mirrors to the pool::

    aha.pool.svc.add pool00.cortex... 00.cortex...
    aha.pool.svc.add pool00.cortex... 01.cortex...
    aha.pool.svc.add pool00.cortex... 02.cortex...

Then configure the Cortex to use the newly created AHA service pool::

    cortex.storm.pool.set aha://pool00.cortex...

Now your Cortex will distribute Storm queries across the available mirrors. You may add or remove mirrors
from the pool at any time using the ``aha.pool.svc.add`` and ``aha.pool.svc.del`` commands and the pool topology
updates will be automatically sent. You may want to review some of the command options to adjust timeouts for your
environment.

If you wish to remove the pool configuration from the Cortex you may use the ``cortex.storm.pool.del`` command.

What's next?
============

See the :ref:`adminguide` for instructions on performing application administrator tasks.  See the :ref:`devopsguide`
for instructions on performing various maintenance tasks on your deployment!

.. _docker: https://docs.docker.com/engine/install/
.. _docker-compose: https://docs.docker.com/compose/install/
.. _known networking limitations of docker on Mac: https://docs.docker.com/desktop/mac/networking/#known-limitations-use-cases-and-workarounds
