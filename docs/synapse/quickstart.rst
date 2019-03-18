.. _quickstart:

Getting Started
###############

This quick start will help you get a **Cortex** up and running, introduce a few devops basics, and get you access to the **Storm** hypergraph query engine.

.. toctree::
    :titlesonly:

Installing Synapse
==================

**Synapse** is a python 3.7 package with several dependencies such as msgpack and lmdb which are compiled python modules.  Synapse makes extensive use of the newest asynchronous design patterns in python and is not compatibile with python versions prior to 3.7.  To use Synapse in a production deployment or a multi-version python environment it may easiest to deploy the pre-built docker containers.

Docker Containers
-----------------

The Synapse release process creates several docker containers for use in production deployments.

*vertexproject/synapse-cortex*
    A Synapse Cortex server image which uses the volume /vertex/storage for storage.

*vertexproject/synapse*
    The Synapse base image with installed dependencies.  This image is mostly useful as a base image for custom entrypoints.

Each Synapse release will build and upload tagged images to Docker Hub.  It is strongly recommended that docker based deployments specify specific version tags.

From Python Package
-------------------

Python packages are built for Synapse releases and uploaded to the Python Package Index (pypi) at https://pypi.org/project/synapse/.  The "pip" command may be used to install directly from pypi::

    pip install synapse

It is recommended that build scripts and automated installations specify an exact version or version range to prevent unintended updates.

From Github
-----------

For development and tracking pre-release Synapse versions, use the Github repo (https://github.com/vertexproject/synapse) to checkout the Synapse source code.  Using a git checkout in production deployments is strongly discouraged.

Starting a Cortex
=================

Each deployed Cortex requires a storage directory.  For performance, it is recommended that the filesystem is running on solid-state/flash drives.

Using the Command Line
----------------------

A Synapse Cortex server may be started from the command line using the synapse.servers.cortex python module.  The only required argument is a directory which is used for storage.::

    python -m synapse.servers.cortex /path/to/cortex

This will start a Cortex server which uses ``/path/to/cortex`` for storage.  The Cortex may be reached via **telepath** (for future commands) via the url ``cell:///path/to/cortex``.

Relative paths may also be used by removing a forward-slash from the URL.  For example, if executing from the ``/path/to/`` directory, the URL ``cell://cortex`` could be used.  For the remaining examples in this document, the cell://cortex URL will be used.

Using Docker
------------

The following docker-compose.yml file can be used to deploy a Cortex server using the synapse-cortex docker image::

    version: '3'

    services:

        core00:

            image: vertexproject/synapse-cortex:v0.1.x

            volumes:
                - /path/to/storage:/vertex/storage

            ports:
                - "4443:4443"
                - "27492:27492"

The server may then be started using typical docker-compose commands or more advanced orchestration.

Adding Initial Users/Roles/Rules
================================

To prepare for sharing a Cortex via telepath or HTTP, roles and users should be created with permissions to allow no more access than necessary.  The following commands create the user "visi" who can add nodes, set properties, and add tags::

    python -m synapse.tools.cellauth cell://cortex modify visi --adduser --passwd secretsauce
    python -m synapse.tools.cellauth cell://cortex modify visi --addrule node:add
    python -m synapse.tools.cellauth cell://cortex modify visi --addrule node:set
    python -m synapse.tools.cellauth cell://cortex modify visi --addrule node:set

Additionally, users may be granted the ``storm.cmd.sudo`` permission to allow them to use the Storm ``sudo`` command to execute queries as a super-user.  Keep in mind that any user with access to the ``sudo`` command can bypass all Storm permissions.::

    python -m synapse.tools.cellauth cell://cortex modify visi --addrule storm.cmd.sudo

To allow remote access for the default root user account, a password can be set using the following command::

    python -m synapse.tools.cellauth cell://cortex modify root --passwd secretsauce

Granular permissions based on types of nodes and tags may be used to create roles based on domain-specific workflows.  The following permissions exist for controlling access to nodes and tags.

*node:add*
     Add any form of node.

*node:add.<form>*
     Add a specific form of node.  (ex. ``node:add.inet:ipv4``)

*node:set*
     Set any property.

*node:set.<prop>*
     Set a specific property.  (ex. ``node:set.inet:ipv4:loc``)

*node:del*
     Delete any form of node.

*node:del.<form>*
     Delete a <form> node. (ex. ``node:del.inet:ipv4``)

*tag:add*
      Add any tag to a node.

*tag:add.<tag>*
     Add a specific tag or subtag to a node. (ex. ``tag:add.foo.bar``)

*tag:del*
      Remove any tag from a node.

*tag:del.<tag>*
     Remove a specific tag or subtag to a node. (ex. ``tag:add.foo.bar``)

Remote Access
=============

Once the user accounts have been created, the Cortex will allow connections from remote systems and users using either the Synapse RPC protocol named telepath or the HTTPS API.  Assuming our server is named "cortex.vertex.link", the user "visi" configured earlier would be able to access the Cortex remotely using the Synapse Commander (see :ref:`syn-tools-cmdr`) via the following command::

    python -m synapse.tools.cmdr tcp://visi:secretsauce@cortex.vertex.link:27492/

To manage multiple services and protect sensitive information in the telepath URL, you may create an entry in your telepath "aliases" file located at ``~/.syn/aliases.yaml``::

    core00: tcp://visi:secretsauce@cortex.vertex.link:27492/

Once an alias is created, the name may be specified in place of the telepath connection URL::

    python -m synapse.tools.cmdr core00

From here, the remote user is free to use the "storm" command to execute queries from the CLI.  See :ref:`storm-ref-intro` for details.  Additionally, the HTTPS API is now available on the default port 4443.  See :ref:`http-api` for details.

Cortex Backups
==============

It is strongly recommended that you regularly backup production Cortex instances.  The Synapse backup tool (synapse.tools.backup) may be used to create a snapshot of a running Cortex without the need to bring the service down or interrupt availability.  It is important to avoid standard file copy operations on running LMDB files due to potentially causing sparse file expansion or producing a corrupt copy.  LMDB makes use of sparse files which allocate file block storage only when the blocks are written to.  This means a file copy tool which is not sparse-file aware can inadvertantly cause massive file expansion during copy.  Once a backup is created ( and has not been loaded by a Cortex ) it is safe to zip/copy the backup files normally.::

    python -m synapse.tools.backup /path/to/cortex /path/to/backup

.. _Index:              ../index.html
