.. _devops-axon:

Axon Operations
===============

The Axon is an interface for providing binary / blob storage inside of the Synapse ecosystem.
Binary objects are indexed based on the SHA-256 hash so that storage of the same set of bytes is not duplicated.

The Axon is one of the Synapse core application components, and can be either deployed as a client within
another Synapse application or as a standalone server.  The Axon server exposes a set of Telepath APIs for uploading,
downloading, and checking existance of a binary object.

A dedicated module is available in ``synapse.servers.axon`` to start an Axon server::

    python -m synapse.servers.axon /data/axon00

The following permissions exist for controlling access to Axon operations.

*axon.get*
    Retrieve a binary object from the Axon.

*axon.has*
    Check if the Axon has bytes represented by a SHA-256 or return SHA-256 and object sizes from an offset.

*axon.upload*
    Upload and save a binary object to the Axon.

Configuration Options
---------------------

The Axon application implements the Synapse Cell class and as such can be configured much like other Cell
implementations. For details on the general configuration options see :ref:`devops-cell-config`.
For a list of boot time configuration options for the Axon, see the listing at :ref:`autodoc-axon-conf`.

The Axon application utilizes local storage,
and has similar system requirements as other object storage systems (without data replication).

When deployed as a remote server it is a best practice to add a new service user,
which can be accomplished with ``synapse.tools.cellauth``. ::

    python -m synapse.tools.cellauth tcp://root:<root_passwd>@<svc_ip>:<svc_port> modify svcuser1 --adduser
    python -m synapse.tools.cellauth tcp://root:<root_passwd>@<svc_ip>:<svc_port> modify svcuser1 --passwd secret

Backups
-------

It is strongly recommended that users schedule regular backups of the Axon.

When the Axon is deployed as a client within another application
(e.g. if no remote Axon Telepath URL is specified in a Cortex)
it will be backed up as part of the parent application backup process on the top-level directory.

If the Axon is deployed as a standalone application, the Synapse backup tool can be used on the directory
specified during service startup.

For details on the backup tool and process see :ref:`devops-general-backups`.

Docker Deployment
-----------------

The Synapse release process creates an Axon Docker container for use in production deployments.

*vertexproject/synapse-axon*
    A Synapse Axon server image which uses the volume /vertex/storage for storage.

Each Synapse release will build and upload tagged images to Docker Hub.
It is strongly recommended that Docker based deployments specify specific version tags.
