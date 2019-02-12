Getting Started
###############

This quick start will help you get a cortex up and running, introduce a few devops basics, and get you access to the STORM hypergraph query engine.

.. toctree::
    :titlesonly:

Installing Synapse
==================

Synapse is a python 3.7 package with several dependencies such as msgpack and lmdb which are compiled python modules.  Synapse makes extensive use of the newest asynchronous design patterns in python and is not compatibile with python versions prior to 3.7.  To use Synapse in a production deployment or a multi-version python environment it may easiest to deploy the pre-built docker containers.

From Python Package
-------------------

```
pip3.7 install synapse:0.1.x
```

From Git Repo
-------------

```
git clone https://github.com/vertexproject/synapse
cd synapse
python setup.py install
```

Starting a Cortex
=================

Each deployed Cortex requires a directory to use for persistence.  For performance, it is important that the filesystem is running on solid-state/flash drives.

Using Docker
------------

TODO running docker command manually

TODO using a docker-compose file

TODO NOTE all python -m commands in the rest of the quick start must be executed from within the container via execing in

Using the Command Line
----------------------

A Synapse cortex server may be started from the command line using the synapse.servers.cortex python module.  The only required argument for a local cortex server is a directory which is used for storage.::

    python -m synapse.servers.cortex /path/to/cortex

This will start a cortex server which uses /path/to/cortex for storage.  The cortex may be reached via telepath (for future commands) via the url::

    cell:///path/to/cortex

Adding Initial Users/Roles/Rules
================================

To prepare for sharing a Cortex via telepath or HTTP, roles and users should be created with permissions to allow no more access than necessary.  To allow remote access for the default root user account, a password must be set using the following command::

    python -m synapse.tools.cmdr cell:///path/to/cortex auth passwd root secret

However, it is recommended that user/service accounts are created with the minimum access needed.  The following commands create the user "visi" who can add nodes, set properties, and add tags::
    python -m synapse.tools.cmdr cell:///path/to/cortex auth user add visi
    python -m synapse.tools.cmdr cell:///path/to/cortex auth user passwd secretsauce
    python -m synapse.tools.cmdr cell:///path/to/cortex auth user allow node:add node:set tag:add

For a detailed discussion on permissions within the Cortex see (FIXME devops perms section)

Sharing a Cortex
================

A Cortex may be shared for remote callers using the Synapse RPC protocol named telepath or an HTTP/HTTPS API.  Once the Cortex is shared via telepath, it may be reached remotely using the commander (synapse.tools.cmdr) or the STORM command line interface::

    python -m synapse.tools.cmdr tcp://visi:secretsauce@cortex.example.com/cortex


Using the Command Line
----------------------

--host 0.0.0.0

NOTE mention the default port and default telepath connection
--http-host = cortex.example.com --https-host=cortex.example.com

NOTE: certdir and certificates

/path/to/cortex/certs/cortex.example.com/sslkey.pem
/path/to/cortex/certs/cortex.example.com/sslcert.pem

Using Docker
------------

SYN_CORTEX_HOST=0.0.0.0 docker 
SYN_CORTEX_HTTP_HOST=cortex.example.com
SYN_CORTEX_HTTPS_HOST=cortex.example.com

Using Docker Compose
--------------------

Cortex Backups
==============

It is strongly recommended that you regularly backup production Cortex instances.  The Synapse backup tool (synapse.tools.backup) may be used to create a snapshot of a running Cortex without the need to bring the service down or interrupt availability.  It is important to avoid standard file copy operations on running LMDB files due to potentially causing sparse file expansion or producing a corrupt copy.  LMDB makes extensive use of sparse files which allocate file block storage only when the blocks are written to.  This means a file copy tool which is not sparse-file aware can inadvertantly cause massive file expansion during copy.  Once a backup is created ( and has not been loaded by a cortex ) it is safe to zip/copy the backup files normally.

```
python -m synapse.tools.backup /path/to/cortex /path/to/backup
```

.. _Index:              ../index.html
