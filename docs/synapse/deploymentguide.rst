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

For the purposes of this guide, we will use ``docker-compose`` as a light-weight orchestration mechanism.
The steps, configurations, and volume mapping guidance given in this guide apply equally to other container
orchestration mechanisms such as Kubernetes but for simplicity's sake, this guide will only cover
``docker-compose`` based deployments.

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

Throughout the examples, we will be using ``loop.vertex.link`` as the AHA network name which is also
used by default as the common-name (CN) for the CA certificate. This should be changed to an appropriate
network name used by your synapse deployment such as ``syn.acmecorp.com``.

.. note::
    It is important that you choose a name and stick with it for a given deployment. Once we begin generating
    host and service account certificates, changing this name will be difficult.

Deploy AHA Service
==================

The AHA service is used for service discovery and acts as a CA to issue host/user certificates used to link
Synapse services. Other Synapse services will need to be able to resolve the IP address of the AHA service
by name, so it is likely that you need to create a DNS A/AAAA record in your existing resolver. When you are
using AHA, the only host that needs DNS or other external name resolution is the AHA service.

For this example deployment, we will name our AHA server ``aha.loop.vertex.link`` and assume DNS records
have been created to resolve the FQDN to an IPv4 / IPv6 address of the host running the container.

Create the container directory::

    mkdir -p /srv/syn/aha/storage

Create the ``/srv/syn/aha/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      aha:
        user: "999"
        image: vertexproject/synapse-aha:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage

Create the ``/srv/syn/aha/storage/cell.yaml`` file with contents::

    aha:name: aha
    aha:network: loop.vertex.link
    aha:urls: ssl://aha.loop.vertex.link
    dmon:listen: ssl://aha.loop.vertex.link?ca=loop.vertex.link
    provision:listen: ssl://aha.loop.vertex.link:27272/

.. note::

    Don't forget to replace ``loop.vertex.link`` with your chosen network name!

Change ownership of the storage directory to the user you will use to run the container::

    chown -R 999 /srv/syn/aha/storage

Start the container using ``docker-compose``::

    docker-compose -f /srv/syn/aha/docker-compose.yaml pull
    docker-compose -f /srv/syn/aha/docker-compose.yaml up -d

To view the container logs at any time you may run the following command on the *host* from the
``/srv/syn/aha`` directory::

    docker-compose logs -f

You may also execute a shell inside the container using ``docker-compose`` from the ``/srv/syn/aha``
directory on the *host*. This will be necessary for some of the additional provisioning steps::

    docker-compose exec aha /bin/bash

Deploy Axon Service
===================

In the Synapse service architecture, an Axon provides a place to store arbitrary bytes/files as binary
blobs and exposes APIs for streaming files in and out regardless of their size.  Given sufficient file system
size, an Axon can be used to efficiently store and retrieve very large files as well as a high number
(easily billions) of files.

**Inside the AHA container**

Generate a one-time use provisioning URL::

    python -m synapse.tools.aha.provision.service 00.axon

You should see output that looks similar to this::

    one-time use URL: ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/00.axon/storage
    chown -R 999 /srv/syn/00.axon/storage

Create the ``/srv/syn/00.axon/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      00.axon:
        user: "999"
        image: vertexproject/synapse-axon:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        environment:
            - SYN_AXON_AHA_PROVISION=ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

.. note::

    Don't forget to replace your one-time use provisioning URL!

Start the container::

    docker-compose --file /srv/syn/00.axon/docker-compose.yaml pull
    docker-compose --file /srv/syn/00.axon/docker-compose.yaml up -d

Deploy JSONStor Service
=======================

**Inside the AHA container**

Generate a one-time use provisioning URL::

    python -m synapse.tools.aha.provision.service 00.jsonstor

You should see output that looks similar to this::

    one-time use URL: ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/00.jsonstor/storage
    chown -R 999 /srv/syn/00.jsonstor/storage

Create the ``/srv/syn/00.jsonstor/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      00.jsonstor:
        user: "999"
        image: vertexproject/synapse-jsonstor:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        environment:
            - SYN_JSONSTOR_AHA_PROVISION=ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

.. note::

    Don't forget to replace your one-time use provisioning URL!

Start the container::

    docker-compose --file /srv/syn/00.jsonstor/docker-compose.yaml pull
    docker-compose --file /srv/syn/00.jsonstor/docker-compose.yaml up -d

Deploy Cortex Service
=====================

**Inside the AHA container**

Edit or copy the following contents to the file ``/tmp/cortex.yaml`` inside the container::

    axon: aha://axon...
    jsonstor: aha://jsonstor...

For example, you could use this command to create the contents from inside the container::

    cat > /tmp/cortex.yaml << EOF
    axon: aha://axon...
    jsonstor: aha://jsonstor...
    EOF

Generate a one-time use provisioning URL::

    python -m synapse.tools.aha.provision.service 00.cortex --user root --cellyaml /tmp/cortex.yaml

You should see output that looks similar to this::

    one-time use URL: ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container directory::

    mkdir -p /srv/syn/00.cortex/storage
    chown -R 999 /srv/syn/00.cortex/storage

Create the ``/srv/syn/00.cortex/docker-compose.yaml`` file with contents::

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
            - SYN_CORTEX_AHA_PROVISION=ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

.. note::

    Don't forget to replace your one-time use provisioning URL!

Start the container::

    docker-compose --file /srv/syn/00.cortex/docker-compose.yaml pull
    docker-compose --file /srv/syn/00.cortex/docker-compose.yaml up -d

Remember, you can view the container logs in real-time using::

    docker-compose --file /srv/syn/00.cortex/docker-compose.yaml logs -f

Deploy Cortex Mirror (optional)
===============================

**Inside the AHA container**

Generate a one-time use URL for provisioning from *inside the AHA container*::

    python -m synapse.tools.aha.provision.service 01.cortex --user root --mirror cortex

You should see output that looks similar to this::

    one-time use URL: ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

**On the Host**

Create the container storage directory::

    mkdir -p /srv/syn/01.cortex/storage
    chown -R 999 /srv/syn/01.cortex/storage

Create the ``/srv/syn/01.cortex/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      01.cortex:
        user: "999"
        image: vertexproject/synapse-cortex:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        environment:
            - SYN_CORTEX_AHA_PROVISION=ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

.. note::

    Don't forget to replace your one-time use provisioning URL!

Start the container::

    docker-compose --file /srv/syn/01.cortex/docker-compose.yaml pull
    docker-compose --file /srv/syn/01.cortex/docker-compose.yaml up -d

.. note::

    If you are deploying a mirror from an existing large Cortex, this startup may take a while to complete
    initialization.

Enroll CLI Users
================

A Synapse user is generally synonymous with a user account on the Cortex. To bootstrap CLI users who will
have Cortex access using the Telepath API, we will need to add them to the Cortex and generate user
certificates for them. To add a new admin user to the Cortex, run the following command from **inside the
Cortex container**::

    python -m synapse.tools.moduser --add --admin true visi@loop.vertex.link

.. note::
    Don't forget to change ``loop.vertex.link`` to your chosen network name!

.. note::
    If you are a Synapse Enterprise customer, using the Synapse UI with SSO, the admin may now login to the
    Synapse UI. You may skip the following steps if the admin will not be using CLI tools to access the Cortex.

Then we will need to generate a one-time use URL they may use to generate a user certificate. Run the
following command from **inside the AHA container** to genreate a one-time use URL for the user::

    python -m synapse.tools.aha.provision.user visi

You should see output that looks similar to this::

    one-time use URL: ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

Then the **user** may run::

    python -m synapse.tools.aha.enroll ssl://aha.loop.vertex.link:27272/<guid>?certhash=<sha256>

Once they are enrolled, they will have a user certificate located in ``~/.syn/certs/users`` and their telepath
configuration located in ``~/.syn/telepath.yaml`` will be updated to reflect the use of the AHA server. From there
the user should be able to use standard Synapse cli tools using the ``aha://`` URL such as::

    python -m synapse.tools.storm aha://visi@cortex.loop.vertex.link

What's next?
============

See the :ref:`adminguide` for instructions on performing application administrator tasks.  See the :ref:`devopsguide`
for instructions on performing various maintenance tasks on your deployment!

.. _docker: https://docs.docker.com/engine/install/
.. _docker-compose: https://docs.docker.com/compose/install/
