Ingest - Sending Data to a Remote Cortex
========================================

It is easy to send data processed by an Ingest to a remote Cortex.  This is done using the ``--sync`` option when
invoking the ingest tool.  An example can be seen below::

    python -m synapse.lib.ingest --sync tcp://some.place.com/core /path/too/ingestdef.json

The above invocation doesn't specify a Cortex with the ``--core`` option - instead it runs the ingest into a ``ram://``
backed Cortex by default. This can be useful so that the local ram Cortex can quickly deduplicate data from the ingest,
and the resulting events will be sent up to the remote Cortex as splice events.  The remote Cortex will then apply any
changes it needs in order to add anything new (nodes, props, tags, etc) from the ingest processing.
