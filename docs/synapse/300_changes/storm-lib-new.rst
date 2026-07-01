.. _vtx_300_storm-lib-new:

New and Changed Storm Libraries
===============================

Synapse 3.0.0 adds several new Storm libraries and reshapes a few existing ones. The
changes below are ordered most-impactful first. Most are additive, but ``$lib.utils``
has one removal that may require a port.

New ``$lib.file`` library
-------------------------

What changed
    A new ``$lib.file`` library is added with ``$lib.file.frombytes(valu)`` and
    ``$lib.file.fromhex(valu)``. ``frombytes()`` uploads the supplied bytes to the
    configured Axon and returns the deconflicted ``file:bytes`` node for that content.
    ``fromhex()`` decodes a hex string and then delegates to ``frombytes()``.

Why
    Provides a single Storm call that both stores file content in the Axon and
    materializes the deconflicted ``file:bytes`` node, replacing the older multi-step
    pattern of uploading bytes and then hand-building the node.

What you need to do
    Call ``$lib.file.frombytes()`` (or ``$lib.file.fromhex()``) instead of uploading
    bytes and separately creating the ``file:bytes`` node. The caller must have the
    ``axon.upload`` permission as well as node ``add`` and ``prop set`` permissions for
    ``file:bytes`` on the write layer.

    ::

        // 2.x: upload then build the node by hand
        ($size, $sha256) = $lib.bytes.put($byts)
        [ file:bytes=$sha256 ]

        // 3.x: one call returns the file:bytes node
        $node = $lib.file.frombytes($byts)

``$lib.utils.buid()`` removed; ``$lib.utils.type()`` added
----------------------------------------------------------

What changed
    In 2.x ``$lib.utils`` exposed ``buid()`` and ``todo()``. In 3.x ``$lib.utils``
    exposes ``type()`` and ``todo()``. The ``buid()`` helper was dropped, and ``type()``
    (the generic value-type inspector formerly at ``$lib.vars.type``) was added.

Why
    Removes the rarely-used buid helper and gives the generic value-type inspector a
    stable home under ``$lib.utils``.

What you need to do
    Replace ``$lib.vars.type($x)`` with ``$lib.utils.type($x)``. If you relied on
    ``$lib.utils.buid()`` there is no direct replacement; reconsider whether a buid is
    actually required.

    ::

        // 2.x
        $t = $lib.vars.type($x)
        $b = $lib.utils.buid($x)

        // 3.x
        $t = $lib.utils.type($x)

New ``$lib.lift`` helpers for the alts and interface model
----------------------------------------------------------

What changed
    The ``$lib.lift`` library gained several helpers in 3.x, in addition to the existing
    ``byNodeData`` and ``tagsByPref``:

    - ``byPropAlts(name, valu, cmpr='=')`` -- lift by a property value, including its
      alternate values.
    - ``byPropRefs(props, valu=(null), cmpr='=')`` -- lift nodes that are referenced
      by named props of other nodes.
    - ``byTypeValue(name, valu, cmpr='=')`` -- lift nodes that have a property of a given
      type and value.
    - ``byPropsDict(form, props, errok=(false))`` -- lift all nodes of a form matching
      a dict of property values, with an ``errok`` flag to suppress norm failures.

Why
    The 3.x model adds alts behavior (a singular property such as ``:name``
    auto-populating a plural ``:names``), typed property values, and interfaces. These
    helpers make it practical to lift across alternate values, by type, or by a property
    dict without hand-writing the lifts.

What you need to do
    These are additive, so no migration is required. Where you previously hand-wrote
    separate lifts to cover a singular property and its plural alternate, use
    ``byPropAlts`` instead; use ``byTypeValue`` to find any node with a property of a
    given type and value, and ``byPropsDict`` for multi-property lifts.

    ::

        // 3.x: deconflict against both :name and its alternate :names
        yield $lib.lift.byPropAlts("ou:org:name", $reporter)

New ``$lib.cortex`` library with Node ID (NID) helpers
------------------------------------------------------

What changed
    A new top-level ``$lib.cortex`` library is added with ``getNodeByNid(nid)``,
    ``getNdefByNid(nid)``, and ``getNidByNdef(ndef)``. The existing ``$lib.cortex.httpapi``
    sublibrary is unchanged.

Why
    3.x changed the layer storage format to index nodes by an integer Node ID (NID).
    These helpers expose the mapping between NIDs and nodes/ndefs to Storm.

What you need to do
    This is purely additive -- no migration needed. If you need to resolve nodes by their
    Cortex-local NID, use the new helpers.

    ::

        // 3.x
        $node = $lib.cortex.getNodeByNid($nid)
        $nid = $lib.cortex.getNidByNdef((inet:fqdn, vertex.link))

New ``$lib.pkg.state()`` for read-only package state
----------------------------------------------------

What changed
    ``$lib.pkg.state(<pkgname>)`` is added and returns a read-only ``pkg:state`` object
    that exposes ``deref()`` and ``iter()`` access to package state values. This
    complements the existing ``$lib.pkg.vars()`` (read/write package vars, admin-gated)
    and ``$lib.pkg.queues()``.

Why
    Gives packages a read-only surface to publish state to consumers, distinct from the
    admin-gated mutable package vars -- useful as power-ups move per-install config and
    cursor state into package-scoped storage.

What you need to do
    This is additive. Read published package state via ``$lib.pkg.state(name)``, and use
    ``$lib.pkg.vars(name)`` for read/write (admin-gated) package config or
    ``$lib.pkg.queues(name)`` for persistent queues.

    ::

        // 3.x
        $state = $lib.pkg.state("synapse-foo")
        $cursor = $state.deref("cursor")
