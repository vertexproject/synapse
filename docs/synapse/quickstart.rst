.. toctree::
    :titlesonly:

.. _quickstart:

Getting Started
###############

This quick start will help you get a **Cortex** up and running, introduce a few devops basics, and get you access to
the **Storm** hypergraph query engine.

Installing Synapse
==================

**Synapse** is a python 3.7 package with several dependencies such as msgpack and lmdb which are compiled python
modules.  Synapse makes extensive use of the newest asynchronous design patterns in python and is not compatible with
python versions prior to 3.7.  To use Synapse in a production deployment or a multi-version python environment it may
easiest to deploy the pre-built docker containers.

Docker Containers
-----------------

The Synapse release process creates several docker containers for use in production deployments.

*vertexproject/synapse-cortex*
    A Synapse Cortex server image which uses the volume /vertex/storage for storage.

*vertexproject/synapse*
    The Synapse base image with installed dependencies.  This image is mostly useful as a base image for custom entry
    points.

Each Synapse release will build and upload tagged images to Docker Hub.  It is strongly recommended that docker based
deployments specify specific version tags. A full list of Docker containers can be found here
:ref:`synapse-docker-images`.

From Python Package
-------------------

Python packages are built for Synapse releases and uploaded to the Python Package Index (pypi) at
https://pypi.org/project/synapse/.  The "pip" command may be used to install directly from pypi::

    pip install synapse

It is recommended that build scripts and automated installations specify an exact version or version range to prevent
unintended updates.

From Github
-----------

For development and tracking pre-release Synapse versions, use the Github repo
(https://github.com/vertexproject/synapse) to checkout the Synapse source code.  Using a git checkout of the master
branch in production deployments is strongly discouraged.

.. _quick_start_cortex:

Starting a Cortex
=================

Each deployed Cortex requires a storage directory.  For performance, it is recommended that the filesystem is running
on solid-state/flash drives.

Using the Command Line
----------------------

A Synapse Cortex server may be started from the command line using the ``synapse.servers.cortex`` python module. The
only required argument is a directory which is used for storage::

    python -m synapse.servers.cortex /path/to/cortex

This will start a Cortex server which uses ``/path/to/cortex`` for storage. The Cortex may be reached via
**telepath** (for future commands) via the url ``cell:///path/to/cortex``.

Relative paths may also be used by removing a forward-slash from the URL.  For example, if executing from the
``/path/to/`` directory, the URL ``cell://cortex`` could be used.  For the remaining examples in this document, the
cell://cortex URL will be used.

Using Docker
------------

The following docker-compose.yml file can be used to deploy a Cortex server using the synapse-cortex docker image::

    version: '3'

    services:

        core00:

            image: vertexproject/synapse-cortex:v2.x.x

            volumes:
                # Map in a persistent storage directory
                - /path/to/storage:/vertex/storage

            environment:
                # Set a default password for the root user
                - SYN_CORTEX_AUTH_PASSWD=secretsauce

            ports:
                # Default https port
                - "4443:4443"
                # Default telepath port
                - "27492:27492"

The server may then be started using typical docker-compose commands or more advanced orchestration.

.. _initial-roles:

Adding Initial Users/Roles/Rules
================================

To prepare for sharing a Cortex via telepath or HTTP, roles and users should be created with permissions to allow no
more access than necessary.  The following commands create the user "visi" who can add nodes, set properties, and add
tags::

    python -m synapse.tools.cellauth cell://cortex modify visi --adduser
    python -m synapse.tools.cellauth cell://cortex modify visi --passwd secretsauce
    python -m synapse.tools.cellauth cell://cortex modify visi --addrule node.add
    python -m synapse.tools.cellauth cell://cortex modify visi --addrule node.prop.set
    python -m synapse.tools.cellauth cell://cortex modify visi --addrule node.tag.add

To allow remote access for the default root user account, a password can be set using the following command::

    python -m synapse.tools.cellauth cell://cortex modify root --passwd secretsauce

Granular permissions based on types of nodes and tags may be used to create roles based on domain-specific workflows.
The following permissions exist for controlling access to nodes and tags.

*node.add*
     Add any form of node.

*node.add.<form>*
     Add a specific form of node.  (ex. ``node.add.inet:ipv4``)

*node.del*
     Delete any form of node.

*node.del.<form>*
     Delete a <form> node. (ex. ``node.del.inet:ipv4``)

*node.prop.set*
     Set any property.

*node.prop.set.<prop>*
     Set a specific property.  (ex. ``node.prop.set.inet:ipv4:loc``)

*node.prop.del*
     Delete any property.

*node.prop.del.<prop>*
     Delete a specific property.  (ex. ``node.prop.del.inet:ipv4:loc``)

*node.tag.add*
     Add any tag to a node.

*node.tag.add.<tag>*
     Add a specific tag or subtag to a node. (ex. ``node.tag.add.foo.bar``)

*node.tag.del*
     Remove any tag from a node.

*node.tag.del.<tag>*
     Remove a specific tag or subtag to a node. (ex. ``node.tag.del.foo.bar``)

For a complete list of permissions which may be used, see :ref:`devops-cell-permissions`.

Remote Access
=============

Once the user accounts have been created, the Cortex will allow connections from remote systems and users using either
the Synapse RPC protocol named telepath or the HTTPS API.  Assuming our server is named "cortex.vertex.link", the user
"visi" configured earlier would be able to access the Cortex remotely using the Synapse Commander
(see :ref:`syn-tools-cmdr`) via the following command::

    python -m synapse.tools.cmdr tcp://visi:secretsauce@cortex.vertex.link:27492/

To manage multiple services and protect sensitive information in the telepath URL, you may create an entry in your
telepath "aliases" file located at ``~/.syn/aliases.yaml``::

    core00: tcp://visi:secretsauce@cortex.vertex.link:27492/

Once an alias is created, the name may be specified in place of the telepath connection URL::

    python -m synapse.tools.cmdr core00

From here, the remote user is free to use the "storm" command to execute queries from the CLI.
See :ref:`storm-ref-intro` for details. Additionally, the HTTPS API is now available on the default port 4443.
See :ref:`http-api` for details.

.. _Index:              ../index.html
