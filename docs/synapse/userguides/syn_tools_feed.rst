.. highlight:: none

.. _syn-tools-feed:

feed
====

The Synapse ``feed`` tool is a way to ingest data exported from one Cortex into another Cortex. Users should be familiar with both the Synapse data model (:ref:`data-model-terms` et al.) as well as Synapse concepts such as packed nodes in order to use and understand the ``feed`` tool effectively.


Syntax
------
The ``feed`` tool is executed from an operating system command shell. The command usage is as follows (line is wrapped for readability):

::

  usage: synapse.tools.feed [-h] (--cortex CORTEX | --test) [--debug] [--format FORMAT] [--modules MODULES]   
    [--chunksize CHUNKSIZE] [--offset OFFSET] [files ...]

Where:
- ``-h`` displays detailed help and these command line options
- ``CORTEX``  specifies the telapth URL to the Cortex where the data should be ingested.

- ``--test`` means to perform the ingest against a temporary, local Cortex instead of a live cortex, for testing or validation
  
  - When using a temporary Cortex, you do not need to provide a path.
  
- ``--debug`` specifies to drop into an interactive prompt to inspect the state of the Cortex post-ingest.
  
- ``FORMAT`` specifies the format of the input files. 

  - Currently, only the value "syn.nodes" is supported. This is also the default value.

- ``MODULES`` specifies a path to a Synapse CoreModule class that will be loaded into the temporary Cortex.

  - This option has no effect if the ``--test`` option is not specified

- ``CHUNKSIZE`` specifies how many lines or chunks of data to read at a time from the given files.

  - Defaults to 1000 if not specified

- ``OFFSET`` specifies how many chunks of data to skip over (starting at the beginning)

- ``files`` is a series of file paths containing data to load into the Cortex (or temporary Cortex)

  - Every file must be either json-serialized data, msgpack-serialized data, yaml-serialized data, or a 
    json lines file. The files do not have to all be of the same type.
  
Ingest Examples - Overview
--------------------------

The ``feed`` tool 

Ingest Example 1
++++++++++++++++

This example demonstrates loading a set of nodes via the ``feed`` tool with the "syn.nodes" format option. The nodes
are of a variety of types, and are encoded in a json lines (jsonl) format.

**JSONL File:**

The jsonl file (``testnodes.jsonl``) contains a list of nodes in their packed form. Each line in the file corresponds
to a single node, with all of the properties, tags, and nodedata on the node encoded in a json friendly format.

::

  [["it:reveng:function", "9710579930d831abd88acff1f2ecd04f"], {"iden": "508204ebc73709faa161ba8c111aec323f63a78a84495694f317feb067f41802", "tags": {"my": [null, null], "my.cool": [null, null], "my.cool.tag": [null, null]}, "props": {".created": 1625069466909, "description": "An example function"},   "tagprops": {}, "nodedata": {}, "path": {}}]
  [["inet:ipv4", 386412289], {"iden": "d6270ca2dc592cd0e8edf8c73000f80b63df4bcd601c9a631d8c68666fdda5ae", "tags": {"my": [null, null], "my.cool": [null, null], "my.cool.tag": [null, null]}, "props": {".created": 1625069584577, "type": "unicast"}, "tagprops": {}, "nodedata": {}, "path": {}}]
  [["inet:url", "https://synapse.docs.vertex.link/en/latest/synapse/userguide.html#userguide"], {"iden": "dba0a280fc1f8cf317dffa137df0e1761b6f94cacbf56523809d4f17d8263840", "tags": {"my": [null, null], "my.cool": [null, null], "my.cool.tag": [null, null]}, "props": {".created": 1625069758843, "proto": "https", "path": "/en/latest/synapse/userguide.html#userguide", "params": "", "fqdn": "synapse.docs.vertex.link", "port": 443, "base": "https://synapse.docs.vertex.link/en/latest/synapse/userguide.html#userguide"}, "tagprops": {}, "nodedata": {}, "path": {}}]
  [["file:bytes", "sha256:ffd19426d3f020996c482255b92a547a2f63afcfc11b45a98fb3fb5be69dd75c"], {"iden": "137fd16d2caab221e7580be63c149f83a11dd11f10f078d9f582fedef9b57ad5", "tags": {"my": [null, null], "my.cool": [null, null], "my.cool.tag": [null, null]}, "props": {".created": 1625070470041, "sha256": "ffd19426d3f020996c482255b92a547a2f63afcfc11b45a98fb3fb5be69dd75c", "md5": "be1bb5ab2057d69fb6d0a9d0684168fe", "sha1": "57d13f1fa2322058dc80e5d6d768546b47238fcd", "size": 16}, "tagprops": {}, "nodedata": {}, "path": {}}]


**Verifying the Data:**

Typically, users will want to double check the data they have before loading it into a production Cortex. The ``feed``
tool allows us to perform an ingest our of nodes file against an empty, ephemeral Cortex, so that we can check what
nodes get created before adding them to a production Cortex. To load ``testnodes.jsonl`` into an ephemeral Cortex and
drop into a prompt to explore the ingested nodes, run:

:: 

  python -m synapse.tools.feed --test --debug testnodes.jsonl

Assuming the command completed with no errors, we should now have a ``cmdr`` prompt connected to our test Cortex:

::

  cli>
 
From which we can issue Storm commands to interact with and validate the nodes that were just ingested. For example:

::

  cli> storm #my.cool.tag
  
  it:reveng:function=9710579930d831abd88acff1f2ecd04f
           .created = 2021/06/30 19:46:31.810
           :description = An example function
           #my.cool.tag
  inet:ipv4=23.8.47.1
           .created = 2021/06/30 19:46:31.810
           :type = unicast
           #my.cool.tag
  inet:url=https://synapse.docs.vertex.link/en/latest/synapse/userguide.html#userguide
           .created = 2021/06/30 19:46:31.810
           :base = https://synapse.docs.vertex.link/en/latest/synapse/userguide.html#userguide
           :fqdn = synapse.docs.vertex.link
           :params =
           :path = /en/latest/synapse/userguide.html#userguide
           :port = 443
           :proto = https
           #my.cool.tag
  file:bytes=sha256:ffd19426d3f020996c482255b92a547a2f63afcfc11b45a98fb3fb5be69dd75c
           .created = 2021/06/30 19:46:31.810
           :md5 = be1bb5ab2057d69fb6d0a9d0684168fe
           :sha1 = 57d13f1fa2322058dc80e5d6d768546b47238fcd
           :sha256 = ffd19426d3f020996c482255b92a547a2f63afcfc11b45a98fb3fb5be69dd75c
           :size = 16
           #my.cool.tag
  complete. 4 nodes in 16 ms (250/sec).


**Loading the Data:**

Once we've inspected and verified the data is acceptable for loading, we can point the ``feed`` tool to the Cortex we
want to load the nodes into, and the same nodes should be added.

::

  python -m synapse.tools.feed --cortex "aha://cortex..." testnodes.jsonl
    
However, once we've inspected the data, let's say that the it:reveng:function and inet:ipv4 nodes are not allowed in
the production Cortex, but the inet:url and file:bytes are. We can skip these two nodes by using a combination of
the ``chunksize`` and ``offset`` parameters:

::

  python -m synapse.tools.feed --cortex "aha://cortex..." testnodes.jsonl --chunksize 1 --offset 1
    
With the ``chunksize`` parameter signifying that the ``feed`` tool should read two lines at a time from the file and
process those before reading the next line, and the ``offset`` parameter meaning the ``feed`` tool should skip all
lines before and including line 1 (so lines 1 and 0) when attempting to add nodes, and only add nodes once it's read
in lines 2 and beyond.
