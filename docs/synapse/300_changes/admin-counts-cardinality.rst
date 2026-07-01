.. _vtx_300_admin-counts-cardinality:

Form/Property Counts and Cardinality Tracking
=============================================

In 3.x, the per-layer ``counters`` database used in 2.x is replaced by a single unified
``indxcounts`` store keyed by index abbreviation. Every property, tag, array, tagprop, and
edge index write increments -- and every delete decrements -- the count for its abbreviation,
so the layer can answer cardinality questions cheaply and exactly.

What changed
    Each layer now maintains an ``indxcounts`` store (a slab-backed ``LruHotCount`` keyed by
    index abbreviation, obtained via ``layrslab.getLruHotCount('indxcounts')``) instead of the
    2.x per-layer ``counters`` database. Index writes increment and deletes decrement the
    relevant abbreviation, so the layer always knows how many nodes carry a given form,
    property, tag, tagprop, array member, or edge verb.

    The Storm-exposed ``getPropCount`` method on ``$lib.layer`` and ``$lib.view`` drops the
    2.x ``maxsize`` argument. Its signature is now ``getPropCount(propname, valu)``. There is
    no longer a row cap to pass. Layer counts are maintained incrementally and are exact; the
    ``$lib.view`` variant remains a fast approximate count summed across the view's layers (a
    value overwritten in a higher layer is still counted in each layer that holds it).

Why
    Cheap, accurate counts of how many nodes have a given form, property, value, tag, tagprop,
    or edge verb (including by endpoint form) are groundwork for query planning and
    optimization: the engine can estimate cardinality and choose a cheaper lift or pivot path.
    They also give admins fast visibility into Cortex composition without full scans.

What you need to do
    These counts are maintained automatically; no operational action is required. If you call
    the Storm ``getPropCount`` method and pass a ``maxsize`` argument, remove it -- the
    parameter no longer exists. Counts read directly from a layer are exact; the ``$lib.view``
    variant is a fast approximate sum across the view's layers.

    ::

        // 2.x -- second positional arg was maxsize
        $count = $lib.layer.get().getPropCount(inet:ipv4, (1000))

        // 3.x -- maxsize removed; the count is exact
        $count = $lib.layer.get().getPropCount(inet:ip)

