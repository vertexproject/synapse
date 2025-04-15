.. _300_changes:

Synapse 3.0.0 Changes
=====================

Features and Enhancements
-------------------------

- Tombstones

In forked views, it is now possible to delete nodes and parts of nodes which are present in parent views due to the
addition of "Tombstone" edits. When looking at a view with tombstone edits, deleted parts of nodes will no longer be
visible and deleted nodes will no longer be lifted. Merging the forked view will delete the nodes and values in the
parent view, and tombstones for nodes or values which are not present in any further parent views will be removed;
if there are further parent views which do contain the tombstoned value, the tombstone will continue to exist in the
parent view. When using the Storm ``diff`` command, fully deleted nodes are represented by a new ``syn:deleted`` runt
node type which has a value containing the ``ndef`` of the deleted node.

- Merged IPv4 and IPv6 Model Elements

Model elements which were previously seperated into IPv4 and IPv6 versions have been merged into a single element
which will auto-detect the type of the value, for example ``inet:ipv4`` and ``inet:ipv6`` are now just ``inet:ip``.
This change simplifies cases where both IPv4 and IPv6 values may be present and reduces complexity when pivoting.
The system mode value for IP addresses is now a tuple of the version number and integer value of the IP. For cases
where only a specific IP version is allowed, the ``inet:ip`` type accepts a ``version`` option which restricts
values to that specific version.

- Virtual Properties

Data model types can now define "virtual properties" which are sub-properties of a value. Virtual properties are
specified in Storm by using the ``*`` operator after a property or form name, such as ``inet:server*ip`` or
``.seen*max>2025``. Virtual properties can be used to retrieve/lift/filter/pivot similar to regular properties.
A full list of virtual properties provided by each type is available in the `Types section of the Synapse Data Model documentation`_

- Updated Layer Storage Format

Layer storage has been updated to index nodes by "Node ID" (NID). NIDs are arbitrary integers which are mapped
to the BUID of each node in a Cortex. This change results in reduced index sizes and additional flexibility for
migrations.

- Deconflicted Node Edits in Nexus Log

Node edits are now deconflicted before being saved to the Nexus log and distributed to mirrors. In Synapse 2.x.x, 
the node edit log for each layer contained the deconflicted copy of the node edits for that layer; that node edit log
now contains the indexes in the Nexus log where the edits are present. These changes result in a significant reduction
in storage utilization and allow services which consume node edits to use the Nexus log directly rather than
aggregating the edits from all layers individually.

Backward Compatibility Breaks
-----------------------------

Microsecond Timestamps
~~~~~~~~~~~~~~~~~~~~~~

What changed
    Timestamps are now in microseconds since epoch instead of milliseconds.

Why make the change
    Currently when ingesting data from sources which provide microsecond accurate timestamps
    for things such as network flow data, Synapse loses accuracy.

What you need to do
    Ensure anywhere you are directly working with epoch timestamps is updated to
    handle/provide microseconds instead of milliseconds.

Extended Model Edge Verbs
~~~~~~~~~~~~~~~~~~~~~~~~~

What changed
    Edge verbs are now required to be defined in the data model.

Why make the change
    Defining edge verbs in the data model prevents incorrect usage of verbs
    an provides additional visibility and documentation of what is in the Cortex.

What you need to do
    Use ``$lib.model.ext.addEdge()`` to add extended model edges to the data model
    in your Cortex and make sure they are prefixed with an underscore (``_``).

Removed Core Modules
~~~~~~~~~~~~~~~~~~~~

What changed
    Cortexes no longer support Core modules.

Why make the change
    Core modules can significantly change Cortex behavior and cause performance/stability issues.
    In general, any functionality added by a Core module can now be accomplished with the use of
    a Storm package or other Synapse features, making support for them an unnecessary risk.

What you need to do
    Ensure your Cortex configuration does not specify the ``modules`` option.

Removed Upstream/Mirror Layers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What changed
    Cortexes no longer support Core modules.

Why make the change
    Core modules can significantly change Cortex behavior and cause performance/stability issues.
    In general, any functionality added by a Core module can now be accomplished with the use of
    a Storm package or other Synapse features, making support for them an unnecessary risk.

What you need to do
    Ensure your Cortex configuration does not specify the ``modules`` option.

Additional Changes
------------------

- Added ``in`` and ``not in`` operators to Storm.
- ``proj:project`` nodes no longer create authgates to manage their permissions.
- ``syn:cron`` and ``syn:trigger`` runt nodes have been removed.
- Synchronous usage of Telepath APIs is no longer supported.
- ``synapse.tools.cmdr`` and ``synapse.tools.cellauth`` have been removed.
- ``NoSuchForm`` and ``NoSuchProp`` exceptions now attempt to provide suggestions if the provided name
  was a form or property which was migrated.
- ``$lib.globals`` and other dictionary like Storm objects now use the deref/setitem convention instead
  of ``.get()``, ``.set()``, and ``.list()`` methods.
- The ``repr()`` for times has been updated to ``ISO 8601`` format.
- Wildcards in tag glob expressions will now allow zero length matches rather than requiring at least one character.

.. _Types section of the Synapse Data Model documentation: autodocs/datamodel_types.html
