.. toctree::
    :titlesonly:

.. _deploymentguide:

Synapse Deployment Guide
########################

Introduction
============

This step-by-step guide will walk you through a production-ready Synapse deployment. Services will be
configured to register with ``AHA`` for service discovery and to prepare for future devops tasks such
as promoting a mirror to leader and registering install Synapse Advanced Power-Ups.

This guide will also walk you through deploying all Synapse services using TLS to authenticate both
servers and clients using client-certificates to minimize the need for secrets management by eliminating
passwords from all telepath URLs.

For the purposes of this guide, we will use ``docker-compose`` as a light-weight orchestration mechanism.
The steps, configurations, and volume mapping guidance given in this guide apply equally to other container
orchestration mechanisms such as Kubernetes but for simplicity's sake, this guide will only cover
docker-compose_ based deployments.


Preparation
===========

Preparing Hosts
---------------

Ensure that you have an updated install of docker_ and docker-compose_.

In order to run the Synapse service containers as a non-root user, you will need to add a user
to the host system.  For this guide, we will use the linux user name ``synuser``. This user name can be replaced
by whatever user name or numeric ID is appropriate for your deployment. We recommend that you do *not* use the
linux user ``nobody`` for this purpose.

Default kernel parameters on most Linux distributions are not optimized for database performance. We recommend
adding the following lines to ``/etc/sysctl.conf`` on all systems being used to host Synapse services::

    vm.swappiness=10
    vm.dirty_expire_centisecs=20
    vm.dirty_writeback_centisecs=20

We will use the directory ``/srv/syn/`` on the host systems as the base directory used to deploy
the Synapse services. Each service will be deployed in separate ``/srv/syn/<svcname>`` directories. This
directory can be changed to whatever you would like, and the services may be deployed to any host provided
that the hosts can directly connect to each other.  It is critical to performance that these storage volumes
be low-latency. More latent storage mechanisms such as spinning dicks, NFS, or EFS should be avoided!

We highly recommend that hosts used to run Synapse services deploy a log aggregation agent to make it easier
to view the logs from the various containers in a single place.

Decide on a Name
================

Throughout the examples, we will be using ``loop.vertex.link`` as the AHA network name which is also
used by default as the common-name (CN) for the CA certificate. This should be changed to an appropriate
network name used by your synapse deployment such as ``syn.acmecorp.com``.

Deploy AHA Service
==================

The AHA service is used for service discovery and can be used as a CA to issue host/user certificates
used to link Synapse services. Other Synapse services will need to be able to resolve the IP address
of the AHA service by name, so it is likely that you need to create a DNS A/AAAA record in your existing
resolver.

For this example deployment, we will name our AHA server ``aha.loop.vertex.link`` and assume DNS records
have been created to resolve the FQDN to an IPv4 / IPv6 address of the host running the container.

Create the container directory::

    mkdir -p /srv/syn/aha/storage

Create the ``/srv/syn/aha/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      user: synuser
      aha:
        image: vertexproject/synapse-aha:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage

Create the ``/srv/syn/aha/storage/cell.yaml`` file with contents::

    aha:name: aha
    aha:network: loop.vertex.link
    aha:urls: ssl://aha.loop.vertex.link:27492
    dmon:listen: ssl://0.0.0.0:27492?hostname=aha.loop.vertex.link&ca=loop.vertex.link
    provision:listen: tcp://0.0.0.0:27272/

NOTE: Don't forget to replace ``loop.vertex.link`` with your chosen network name!

Change ownership of the storage directory to the user you will use to run the container::

    chown -R synuser /srv/syn/aha/storage

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
blobs and exposes APIs for streaming files in and out regardless of their size.  Given sufficient filesystem
size, an Axon can be used to efficiently store and retrieve very large files as well as a high number
(easily billions) of files.

Inside the AHA container
------------------------

Generate a one-time use provisioning API key::

    python -m synapse.tools.aha.provision 00.axon

You should see output that looks similar to this::

    one-time use provisioning key: b751e6c3e6fc2dad7a28d67e315e1874

On the Host
-----------

Create the container directory::

    mkdir -p /srv/syn/axon/storage
    chown -R synuser /srv/syn/axon/storage

Create the ``/srv/syn/00.axon/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      00.axon:
        user: synuser
        image: vertexproject/synapse-axon:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        environment:
            - SYN_AXON_AHA_PROVISION=tcp://aha.loop.vertex.link:27272/b751e6c3e6fc2dad7a28d67e315e1874

Don't forget to replace ``b751e6c3e6fc2dad7a28d67e315e1874`` with your one-time use provisioning key!

Start the container::

    docker-compose --file /srv/syn/axon/docker-compose.yaml pull
    docker-compose --file /srv/syn/axon/docker-compose.yaml up -d

Deploy JSONStor Service
=======================

Inside the AHA container
------------------------

Generate a one-time use provisioning API key::

    python -m synapse.tools.aha.provision 00.jsonstor

You should see output that looks similar to this::

    one-time use provisioning key: 8c5eeeafdc569b5a0642ee451205efae

On the Host
-----------

Create the container directory::

    mkdir -p /srv/syn/00.jsonstor/storage
    chown -R synuser /srv/syn/00.jsonstor/storage

Create the ``/srv/syn/00.jsonstor/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      00.jsonstor:
        user: synuser
        image: vertexproject/synapse-jsonstor:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        environment:
            - SYN_JSONSTOR_AHA_PROVISION=tcp://aha.loop.vertex.link:27272/8c5eeeafdc569b5a0642ee451205efae

Don't forget to replace ``8c5eeeafdc569b5a0642ee451205efae`` with your one-time use provisioning key!

Start the container::

    docker-compose --file /srv/syn/00.jsonstor/docker-compose.yaml pull
    docker-compose --file /srv/syn/00.jsonstor/docker-compose.yaml up -d

Deploy Cortex Service
=====================

Inside the AHA container
------------------------

Edit or copy the following contents to the file ``/tmp/cortex.yaml`` inside the container::

    axon: aha://axon...
    jsonstor: aha://jsonstor...

Generate a one-time use provisioning key::

    python -m synapse.tools.aha.provision 00.cortex --user root --cellyaml /tmp/cortex.yaml

You should see output that looks similar to this::

    one-time use provisioning key: 8c5eeeafdc569b5a0642ee451205efae

On the Host
-----------

Create the container directory::

    mkdir -p /srv/syn/00.cortex/storage
    chown -R synuser /srv/syn/00.cortex/storage

Create the ``/srv/syn/00.cortex/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      00.cortex:
        user: synuser
        image: vertexproject/synapse-cortex:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        environment:
            - SYN_CORTEX_AHA_PROVISION=tcp://aha.loop.vertex.link:27272/8c5eeeafdc569b5a0642ee451205efae

Start the container::

    docker-compose --file /srv/syn/00.cortex/docker-compose.yaml pull
    docker-compose --file /srv/syn/00.cortex/docker-compose.yaml up -d

NOTE: Remember, you can view the container logs in real-time using::

    docker-compose --file /srv/syn/00.cortex/docker-compose.yaml logs -f

Deploy Cortex Mirror (optional)
===============================

To deploy a Cortex mirror, we must start with a backup snapshot of an existing Cortex that has already
been initialized. For instructions on generating a backup, see the docs _here.

Inside the AHA container
------------------------

Generate a one-time use API key for provisioning from *inside the AHA container*::

    python -m synapse.tools.aha.provision 01.cortex --mirror 00.cortex

You should see output that looks similar to this::

    one-time use provisioning key: 4f655032bc87b012955922724c4f7ae5

On the Host
-----------

Create the container storage directory::

    mkdir -p /srv/syn/01.cortex/storage
    chown -R synuser /srv/syn/01.cortex/storage

Create the ``/srv/syn/01.cortex/docker-compose.yaml`` file with contents::

    version: "3.3"
    services:
      01.cortex:
        user: synuser
        image: vertexproject/synapse-cortex:v2.x.x
        environment:
            - SYN_CORTEX_AHA_PROVISION=tcp://aha.loop.vertex.link:27272/4f655032bc87b012955922724c4f7ae5
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage

Start the container::

    docker-compose --file /srv/syn/01.cortex/docker-compose.yaml pull
    docker-compose --file /srv/syn/01.cortex/docker-compose.yaml up -d

NOTE: If you are deploying a mirror from an existing large Cortex, this startup may take a while
to complete initialization.

What's next?
============

See the devops_ documentation for instructions on performing various maintenance tasks on your deployment!

.. _docker: https://docs.docker.com/engine/install/
.. _docker-compose: https://docs.docker.com/compose/install/
