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

    backup:dir: /vertex/backups

    dmon:listen: ssl://0.0.0.0:27492?hostname=aha.loop.vertex.link&ca=loop.vertex.link
    provision:listen: tcp://0.0.0.0:27272

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

If you plan to install the commercial ``Synapse-S3`` Axon, you should replace this step with the
deployment guidance provided _here.

Generate a one-time use API key for provisioning the axon by executing the following command from *inside
the AHA container*::
    python -m synapse.tools.aha.provision axon

You should see output that looks similar to this::
    one-time use provisioning key: b751e6c3e6fc2dad7a28d67e315e1874

Create the container directory::
    mkdir -p /srv/synapse/axon/backups
    mkdir -p /srv/synapse/axon/storage
    chown -R synuser /srv/synapse/axon/backups
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
        - ./backups:/vertex/backups

``storage/cell.yaml``::
    backup:dir: /vertex/backups
    aha:provision: tcp://aha.loop.vertex.link:27272/b751e6c3e6fc2dad7a28d67e315e1874

note: Don't forget to replace ``aha.loop.vertex.link`` with your AHA server DNS name.
note: Don't forget to replace ``b751e6c3e6fc2dad7a28d67e315e1874`` with your one-time use provisioning key.

Deploy JSONStor Service (optional)
##################################

Deploy Cortex Service
#####################

Deploy Cortex Mirror (optional)
###############################

What's next?
############

See the _devops documentation for instructions on performing various maintenance tasks on your deployment!

Running a Backup
================

Switching to Structured Logging
===============================

Updating Services
=================

Check the service documentation changelogs 
