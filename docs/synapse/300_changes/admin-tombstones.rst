.. _vtx_300_admin-tombstones:

Tombstones and Forked-View Deletes
==================================

Synapse 3.0.0 introduces tombstones: a layer-storage mechanism that lets a forked
(child) view record the deletion of data that lives only in a parent/read-only
layer, without mutating the parent. This changes how deletes behave in forks, how
``diff`` and ``merge`` work, and adds new Storm APIs and a new ``syn:deleted`` runt
form. The entries below are ordered most-impactful first.

Deleting in a forked view now records tombstones
------------------------------------------------

What changed
    Synapse 3.0.0 adds a full set of tombstone node edits to the layer storage
    format (``EDIT_NODE_TOMB`` through ``EDIT_EDGE_TOMB_DEL``, covering whole nodes,
    props, tags, tagprops, nodedata keys, and edges, plus matching ``*_TOMB_DEL``
    edits), along with ``INDX_TOMB`` and ``FLAG_TOMB`` storage bytes. In a forked
    view you can now delete a node -- or just a property, tag, tagprop, nodedata
    key, or edge -- that exists only in a parent layer. The write layer records a
    tombstone (a whole-node tombstone sets the storage node's ``antivalu``;
    part-of-node tombstones use ``antiprops`` / ``antitags`` / ``antitagprops``)
    rather than mutating the parent. While viewing the fork, the tombstoned
    node/value is no longer visible, and a fully tombstoned node is not lifted.

    In 2.x this was impossible: deleting an inherited node in a fork had no effect
    on the parent copy.

Why
    Forked views are used as scratch/working views layered over shared read-only
    data. Previously a fork could add and override data but could not represent a
    deletion of inherited data, so cleanup or correction of upstream nodes could not
    be staged and reviewed in a fork before being applied. Tombstones let a fork
    express "this should be gone" without touching the parent until merge.

What you need to do
    You can now run normal delete operations (``delnode``, ``[ -:prop ]``,
    ``[ -#tag ]``, edge and nodedata deletes) inside a forked view against data that
    lives in a parent layer; the fork hides it via a tombstone instead of doing
    nothing. Within the fork the data disappears from lifts and pivots -- if a query
    that used to return parent nodes now returns nothing in a fork, check for
    tombstones.

    ::

        // Synapse 2.x: in a forked view you could not delete a node that only
        // existed in the parent layer -- the parent copy remained visible.
        inet:fqdn=evil.com delnode   // no effect on the inherited node

        // Synapse 3.x: in a forked view this records a tombstone; the node is
        // hidden in the fork (not lifted) but the parent layer is untouched
        // until merge.
        inet:fqdn=evil.com delnode

        // part-of-node deletes also tombstone inherited values:
        inet:ip=1.2.3.4 [ -:asn ]
        inet:ip=1.2.3.4 [ -#my.tag ]

Inspecting staged deletions with diff and syn:deleted
-----------------------------------------------------

What changed
    A new runt form ``syn:deleted`` (type ``data``, ``runt=True``) is added in 3.x,
    with the computed props ``:nid``, ``:form``, ``:value``, and ``:sodes`` (the
    per-layer storage nodes). Because tombstoned nodes are intentionally not lifted,
    the ``diff`` command surfaces them: its lift path iterates the write layer's
    storage nodes and, when a storage node has ``antivalu`` set (a whole-node
    tombstone), yields ``view.getDeletedRuntNode(nid)`` -- a ``syn:deleted`` runt
    node whose primary value is the ndef of the deleted node -- instead of trying to
    lift the now-hidden node. The prop-scoped (``--prop``) diff path also walks the
    layer's prop tombstones so deleted props are surfaced alongside changed props.
    Added and changed nodes still diff as their normal forms; only fully-deleted
    nodes appear as ``syn:deleted``.

Why
    Tombstoned nodes are not visible to ordinary lifts or pivots in a fork, so
    without a dedicated surface there would be no way to see or act on staged
    deletions. ``syn:deleted`` gives analysts and admins a first-class, filterable
    handle on pending deletions before a merge.

What you need to do
    To audit what a fork will delete on merge, run ``diff`` and filter for
    ``syn:deleted``. You can filter by the original form with
    ``+syn:deleted:form=<form>`` and read the deleted ndef from the node value. Do
    not expect ``diff`` to return the original form for deleted nodes -- it returns
    ``syn:deleted`` runt nodes for those, and a fully tombstoned node will not appear
    in an ordinary lift within the fork.

    ::

        // Synapse 2.x: diff only surfaced added/changed nodes in the top layer;
        // there was no representation of deletions.
        diff

        // Synapse 3.x: see everything the fork changed, including deletions
        diff

        // just the deleted inet:ip nodes
        diff | +syn:deleted:form=inet:ip

        // inspect a pending deletion (prints the deleted ndef)
        diff | +syn:deleted $lib.print($node.value)

Merging a fork now applies staged deletions to the parent
---------------------------------------------------------

What changed
    View merge logic in 3.x understands tombstones. During merge, a lone
    ``EDIT_NODE_TOMB`` edit deletes the parent node; part-of-node tombstones
    (``EDIT_PROP_TOMB`` / ``EDIT_TAG_TOMB`` / ``EDIT_TAGPROP_TOMB`` /
    ``EDIT_NODEDATA_TOMB`` / ``EDIT_EDGE_TOMB``) are translated into pop / delTag /
    delTagProp / popData / delEdge operations against the parent. After the merge,
    tombstones for nodes/values that are not present in any further parent view are
    removed; a tombstone whose value still exists in a deeper parent continues to
    exist (so the deletion keeps masking the still-present ancestor value). The
    ``diff | merge --apply`` flow turns staged deletions into actual parent
    deletions.

Why
    This makes deletion a first-class, mergeable operation: you can stage deletes in
    a fork, review them, and promote them to the parent exactly like adds and edits,
    with multi-parent layer stacks handled correctly (a tombstone is only dropped
    once nothing below still needs masking).

What you need to do
    Treat deletions staged in a fork as part of the merge, just like adds. Review
    pending deletions with ``diff`` before merging, then merge. After
    ``merge --apply``, the nodes/values you deleted in the fork will be gone from the
    parent; verify with a lift in the parent view. In multi-parent stacks, be aware a
    tombstone may persist in an intermediate parent if a deeper layer still holds the
    value.

    ::

        // Synapse 2.x: merging a fork could only push adds/edits to the parent;
        // there was no way to delete inherited parent data via merge.
        diff | merge --apply   // deletions in the fork were never applied

        // Synapse 3.x: stage deletions in a fork, review, then merge them down
        inet:ip=1.2.3.4 delnode   // in the fork: records a tombstone
        diff | +syn:deleted       // review pending deletions
        diff | merge --apply      // applies the deletion to the parent

New Storm APIs to inspect and remove tombstones
-----------------------------------------------

What changed
    The Storm Layer object gains tombstone-management methods. ``getTombstones()``
    yields ``(nid, tombtype, info)`` tuples for the tombstones in the layer;
    ``getEdgeTombstones(verb=None)`` yields ``(n1nid, verb, n2nid)`` edge tombstones;
    and ``delTombstone(nid, tombtype, tombinfo)`` removes a tombstone, returning
    ``True`` if removed and ``False`` if not. ``getNodeData(nid)`` now yields
    ``(name, valu, istombstone)`` tuples so node-data tombstones are visible, and it
    takes a nid (e.g. ``$node.nid``) rather than the 2.x node iden.

Why
    Because tombstones are a new persistent storage concept, admins and integrators
    need a way to enumerate and reverse them -- for example to undo a staged deletion
    in a fork without re-creating the node, or to audit what a layer is masking.

What you need to do
    Use ``$lib.layer.get().getTombstones()`` (or ``getEdgeTombstones``) to enumerate
    staged deletions in a write layer, and ``$layer.delTombstone($nid, $tombtype,
    $tombinfo)`` to cancel a staged deletion before merge. When iterating node data
    with ``getNodeData()`` in 3.x, expect a third ``istombstone`` element in each
    tuple, and pass a nid instead of the node iden.

    ::

        // Synapse 2.x: no tombstone APIs existed; getNodeData yielded 2-tuples
        // keyed by node iden.
        for ($name, $valu) in $layer.getNodeData($node.iden()) { $lib.print($name) }

        // Synapse 3.x: list tombstones in the current write layer
        $layer = $lib.layer.get()
        for ($nid, $type, $info) in $layer.getTombstones() {
            $lib.print(`tomb {$type} {$info}`)
        }

        // cancel a staged deletion
        $layer.delTombstone($nid, $type, $info)

        // node data now yields (name, valu, istombstone)
        for ($name, $valu, $tomb) in $layer.getNodeData($node.nid) {
            $lib.print(`{$name} tomb={$tomb}`)
        }

movenodes gains --preserve-tombstones
-------------------------------------

What changed
    The ``movenodes`` Storm command, which moves storage nodes between layers within
    a view, is tombstone-aware in 3.x. By default, when the merged result of a moved
    storage node is a tombstone, any current value in the destination layer is
    deleted and the tombstone itself is removed (the deletion is realized rather than
    carried). The new ``--preserve-tombstones`` flag instead adds the tombstone to
    the destination layer in addition to deleting the current value, so the
    destination keeps masking lower layers. This applies to whole nodes, props,
    tags, tagprops, nodedata, and edges.

Why
    With tombstones now part of layer storage, moving storage nodes between layers
    has to decide what to do with a deletion marker. The default realizes the delete;
    ``--preserve-tombstones`` is needed when the destination still sits above other
    layers that contain the value being masked.

What you need to do
    When using ``movenodes`` in 3.x, decide whether a moved deletion should simply
    remove the value (default) or continue masking deeper layers in the destination
    (use ``--preserve-tombstones``). This option did not exist in 2.x because there
    were no tombstones.

    ::

        // Synapse 2.x: movenodes had no tombstone awareness or --preserve flag
        ou:org | movenodes --apply

        // Synapse 3.x: move storage nodes, keeping deletion masks
        ou:org | movenodes --apply --preserve-tombstones
