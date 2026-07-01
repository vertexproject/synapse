.. _vtx_300_devops-layer-storage-nid:

NID Layer Storage Format
========================

Synapse 3.0.0 replaces the per-layer, BUID-keyed on-disk storage model with a
Cortex-wide integer Node ID (NID) model. This is a DevOps-facing on-disk format
change; it is transparent to analysts and requires no Storm changes.

NID-keyed layer storage
-----------------------

What changed
    In 2.x, every layer maintained a fan-out of separate LMDB sub-databases
    keyed by a node's 32-byte BUID (``bybuidv3`` for storage nodes plus
    ``byprop``, ``byarray``, ``bytag``, ``bytagprop``, ``byform``, ``byndef``,
    ``byverb``, ``edgesn1``/``edgesn2``/``edgesn1n2``, and counters), and a node
    edit was a ``(<buid>, <form>, [edits])`` tuple.

    In 3.x, the Cortex assigns each node ndef a monotonically increasing 64-bit
    integer NID and maintains the ndef-to-NID mapping once, at the Cortex level,
    in a ``v3stor`` slab at ``slabs/layersv3.lmdb`` (with ``nid2ndef`` and
    ``ndef2nid`` dbs and a ``nextnid`` counter). Each layer now uses just two
    dbs for nodes: a single ``bynid`` db holding storage nodes, and a single
    unified ``indx`` db (dupsort, dupfixed) into which every index type is
    written using an abbreviation prefix. The on-disk node-edit / sode tuple
    changed from ``(<buid>, <form>, [edits])`` to ``(<nid>, <form>, [edits])``.

Why
    A NID is 8 bytes versus 32 for a BUID, so every index row that previously
    carried a BUID value now carries a far smaller NID. Because the mapping
    lives once at the Cortex and the same NID is reused across all index types
    and across layers, index sizes shrink and a single indirection point gives
    flexibility for future migrations. Collapsing the per-layer index fan-out
    into one ``indx`` db (with per-index abbreviation prefixes) also reduces
    per-layer db overhead.

What you need to do
    This is a non-trivial on-disk format change. It is NOT an automatic in-place
    upgrade: when 3.x opens a 2.x Cortex directory it detects the stored
    ``cortex:version`` is from the 2.x line and raises ``BadStorageVersion``
    ("The Cortex storage directory is from Synapse 2.x and must be migrated.")
    rather than migrating in place. Note that the per-layer storage version is
    not what signals the change -- both 2.x and 3.x report layer version 11; the
    gate is the Cortex-level version check.

    Automated migration of an existing 2.x Cortex is not part of this release;
    evaluate Synapse 3.0.0 with a new 3.x Cortex and keep your 2.x deployment
    intact. A supported path for migrating existing Cortex data is expected in a
    later release, at which point the new layer directories plus a Cortex-level
    ``slabs/layersv3.lmdb`` mapping db will differ in size and shape from 2.x.

Cortex-wide, Nexus-replicated NID assignment
--------------------------------------------

What changed
    NIDs are allocated once per node ndef at the Cortex level and shared by all
    layers. ``genNdefNid(ndef)`` returns an existing NID if present, otherwise
    issues the Nexus-replicated push ``nid:gen``, whose ``onPush`` handler
    ``_genNdefNid`` increments ``nextnid`` and writes both ``nid2ndef`` and
    ``ndef2nid`` so every mirror agrees on the same NID. Edge edits resolve
    their N2 destination ndef to a NID the same way.

    The ``remoteToLocalEdits`` / ``localToRemoteEdits`` paths translate between
    the wire (ndef-based) edit form and the local NID form for replication and
    the compatibility node-edit API. One nuance: when a node-add edit arrives
    locally with ``nid=None``, the NID is generated via the non-Nexus
    ``_genNdefNid`` directly (mirrors populate the mapping from the replicated
    node-add edit), whereas edits referencing an already-existing or remote ndef
    use the Nexus-replicated ``genNdefNid``.

Why
    A single Cortex-wide NID namespace (rather than per-layer BUID keys) is what
    lets the smaller integer keys be used consistently across every layer and
    the shared Nexus log, while keeping mirrors deterministically in sync about
    which integer maps to which node.

What you need to do
    No action for analysts or operators. Integrators using the Telepath
    node-edit APIs should note that edits are exchanged in a remote
    (ndef-based) form and translated to the local NID form via the compat flag.
    Pass ``compat=True`` when feeding edits sourced from a different Cortex so
    NIDs are resolved or generated locally rather than assumed to match.

    .. code-block:: python

        # 3.x: feeding edits sourced from a different Cortex
        async for item in layrapi.syncNodeEdits(offs, compat=True):
            ...

        await layrapi.saveNodeEdits(edits, meta, compat=True)
