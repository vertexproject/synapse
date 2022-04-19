.. toctree::
    :titlesonly:

.. _deploymentguide:

Deployment Guide
################

Introduction
============

This step-by-step guide will walk you through a production-ready Synapse deployment. Services will be
configured register with ``AHA`` for service discovery and to prepare for future devops tasks such
as promoting a mirror to leader and registering ``Synapse Advanced Power-Ups``.

This guide will also walk you through deploying all Synapse services using TLS to authenticate both
servers and clients using client-certificates to minimize the need for secrets management by eliminating
passwords from all deployment configurations.

Deployment FAQ
--------------

Conventions
===========

* Docker-Compose

For the purposes of this guide, we will use ``docker-compose`` as a light-weight orchestration mechanism.
The steps, configurations, and volume mapping guidance given in this guide apply equally to other container
orchestration mechanisms such as ``Kubernetes`` but for simplicity's sake, this guide will only cover
``docker-compose`` based deployments.

* Container Users

In order to run the ``Synapse`` service containers as a non-root user, you will need to add a user
to the host system.  For this guide, we will use the linux user name ``synuser``. This user name can be replaced
by whatever user name or numeric ID is appropriate for your deployment. We recommend that you do *not* use the
linux user ``nobody`` for this purpose.

* Host Filesystem

We will use the directory ``/srv/synapse/`` on the *host* systems as the base directory used to deploy
the ``Synapse`` services.  This directory can be changed to whatever you would like, and the services
may be deployed to any host provided that the hosts can directly connect to eachother.

* AHA Network Name / CA Name

Throughout the examples, we will be using ``loop.vertex.link`` as the ``AHA`` network name which is also
used by default as the common-name (CN) for the CA certificate. This should be changed to an appropriate
network name used by your synapse deployment such as ``syn.acmecorp.com``.

Preparation
===========

Sizing Hosts
------------

Paving Hosts
------------

TODO
* Ensure an updated / functional docker install
* Add the user used to run the containers
* Tune kernel parameters for database performance
* Add log aggregation agent

Deploy AHA Service
##################

The AHA service is used for service discovery and can be used as a CA to issue host/user certificates
used to link Synapse services. Other Synapse services will need to be able to resolve the IP address
of the AHA service by name.

For this exmple deployment, we will name our AHA server ``aha.loop.vertex.link`` and assume DNS records
have been created to resolve the FQDN to an IPv4 / IPv6 address of the host running the container.

Create and change ownership of the container directory::
    mkdir -p /srv/synapse/aha/storage
    mkdir -p /srv/synapse/aha/backups
    chown -R synuser /srv/synapse/aha/backups
    chown -R synuser /srv/synapse/aha/storage

Create the following files in ``/srv/synapse/aha/``. Don't forget to replace ``loop.vertex.link`` with
your chosen network name!

``docker-compose.yaml``::
    version: "3.3"
    services:
      user: synuser
      aha:
        image: vertexproject/synapse-aha:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        - ./backups:/vertex/backups

``storage/cell.yaml``::
    aha:name: aha.loop.vertex.link
    aha:network: loop.vertex.link
    aha:admin: root@loop.vertex.link
    aha:urls: ssl://aha.loop.vertex.link:27492

    dmon:listen: ssl://0.0.0.0:27492?hostname=aha.loop.vertex.link&ca=loop.vertex.link

Start the container using ``docker-compose`` on the *host* from the ``/srv/synapse/aha`` directory::
    docker-compose pull
    docker-compose up -d

NOTE: For details on learning to use docker-compose see FIXME LINK

To view the container logs at any time you may run the following command on the *host* from the
``/srv/synapse/aha`` directory::
    docker-compose logs -f

You may also execute a shell inside the container using ``docker-compose`` from the ``/srv/synapse/aha``
directory on the *host*. This will be necessary for some of the additional provisioning steps::
    docker-compose exec aha /bin/bash

Deploy Axon Service
###################

In the Synapse service archtecture, an Axon provides a place to store arbitrary bytes/files as binary
blobs and exposes APIs for streaming files in and out regardless of their size.  Given sufficient filesystem
size, an Axon can be used to efficiently store and retrieve very large files as well as a high number
(easily billions) of files.

Generate a one-time use API key for provisioning the axon by executing the following command from *inside
the AHA container*::
    python -m synapse.tools.aha.provision axon

You should see output that looks similar to this::
    one-time use provisioning key: b751e6c3e6fc2dad7a28d67e315e1874

Create the container directory::
    mkdir -p /srv/synapse/axon/storage
    chown -R synuser /srv/synapse/axon/storage

Create the following files in ``/srv/synapse/axon/``.

``docker-compose.yaml``::
    version: "3.3"
    services:
      user: synuser
      aha:
        image: vertexproject/synapse-axon:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage

``storage/cell.yaml``::
    aha:provision: tcp://aha.loop.vertex.link:27272/b751e6c3e6fc2dad7a28d67e315e1874
    inaugural:
        users:
            - name: cortex@loop.vertex.link
              admin: true

note: Don't forget to replace ``aha.loop.vertex.link`` with your AHA server DNS name.
note: Don't forget to replace ``b751e6c3e6fc2dad7a28d67e315e1874`` with your one-time use provisioning key.

Start the container using ``docker-compose`` on the *host* from the ``/srv/synapse/axon`` directory::
    docker-compose pull
    docker-compose up -d

Deploy JSONStor Service (optional)
##################################

Deploy Cortex Service
#####################

In order to prepare to have a peer-mirror deployment where we can easily promote any mirror to being
the leader, we will provision this Cortex using the name ``00.cortex``.  If the service name being provisioned
includes a ``.`` character, the provisioning logic assumes that the last part (``cortex`` in this case) is the
name of the leader.

Generate a one-time use API key for provisioning the axon by executing the following command from *inside
the AHA container*::
    python -m synapse.tools.aha.provision 00.cortex

You should see output that looks similar to this::
    one-time use provisioning key: 8c5eeeafdc569b5a0642ee451205efae

Create the container directory::
    mkdir -p /srv/synapse/00.cortex/backups
    mkdir -p /srv/synapse/00.cortex/storage
    chown -R synuser /srv/synapse/00.cortex/backups
    chown -R synuser /srv/synapse/00.cortex/storage

Create the following files in ``/srv/synapse/00.cortex/``.

``docker-compose.yaml``::
    version: "3.3"
    services:
      00.cortex:
        user: synuser
        image: vertexproject/synapse-cortex:v2.x.x
        network_mode: host
        restart: unless-stopped
        volumes:
        - ./storage:/vertex/storage
        - ./backups:/vertex/backups

``storage/cell.yaml``::
    nexslog:en: true
    backup:dir: /vertex/backups
    axon: aha://cortex@axon.loop.vertex.link/
    jsonstor: aha://cortex@jsonstor.loop.vertex.link/
    aha:provision: tcp://aha.loop.vertex.link:27272/8c5eeeafdc569b5a0642ee451205efae

The ``nexslog:en: true`` option configures the Cortex to enable change logging that is necessary
for mirror configurations.  Additionally, the ``axon: aha://cortex@axon.loop.vertex.link`` configures
the Cortex to use the provisioned Axon to store raw bytes such as files.  Finally, the
``jsonstor: aha://cortex@jsonstor.loop.vertex.link`` configures the Cortex to use the provisioned
JSONStor service to store user specified or Power-Up cached data.

Start the container using ``docker-compose`` on the *host* from the ``/srv/synapse/axon`` directory::
    docker-compose pull
    docker-compose up -d

Deploy Cortex Mirror (optional)
###############################

To deploy a Cortex mirror, we must start with a backup snapshot of an existing Cortex that has already
been initialized. For instructions on generating a backup, see the docs _here.

Create the container backup directory::
    mkdir -p /srv/synapse/01.cortex/backups
    chown -R synuser /srv/synapse/01.cortex/backups

Move the backup to the ``/srv/synapse/01.cortex`` directory on the *host* then extract and rename the folder::
    mv cortex-202204180202.tgz /srv/synapse/01.cortex
    cd /srv/synapse/01.cortex
    tar -vzxf cortex-202204180202.tgz
    mv cortex-202204180202 storage
    chown -R synuser 

Change permissions 

Then edit the ``storage/cell.yaml`` file to set the following options ( leaving all other options as-is )::
    aha:name: 01.cortex.loop.vertex.link
    mirror: aha://cortex@cortex.loop.vertex.link

Take a backup of your 

What's next?
############

See the _devops documentation for instructions on performing various maintenance tasks on your deployment!

Running a Backup
================

Switching to Structured Logging
===============================

Updating Services
=================

* Check the service documentation changelogs 
