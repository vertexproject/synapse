.. _vtx_300_datamodel-extended-model:

Extended Model Changes (Edges, Universal Props)
===============================================

Synapse 3.0.0 reworks how light-edge verbs and extended properties are defined. Edge verbs are
now part of the data model and validated on write, the ad-hoc ``$lib.model.edge`` key-value
store is gone, and extended universal properties have been removed entirely. The entries below
are ordered by how often a 2.x deployment is likely to hit them.

Edge verbs must be modeled (underscore-prefixed) and are validated on write
---------------------------------------------------------------------------

What changed
    Light-edge verbs are now part of the data model and validated when an edge is written.
    Writing an edge whose ``(n1form, verb, n2form)`` triple is not declared raises
    ``NoSuchEdge``. Built-in verbs are declared in the model (interface-based n1/n2 forms are
    allowed). Custom (extended) verbs must be registered ahead of time with
    ``$lib.model.ext.addEdge`` and the verb must begin with an underscore; registering a verb
    that does not is rejected. You may pass ``*`` for ``n1form`` or ``n2form`` to mean any
    form, and a declaration can be specific, fully-wildcard, or partially-specified.

Why
    Defining edge verbs in the model prevents typos and incorrect verb usage, and documents
    which edges exist in a Cortex. This matches the existing extended form and property
    registration model.

What you need to do
    Before using a custom edge verb in 3.x, register it once with ``$lib.model.ext.addEdge``
    and prefix it with an underscore. Replace ad-hoc 2.x verbs with either a built-in modeled
    verb or a registered ``_verb``. Use ``*`` for ``n1form`` / ``n2form`` when the edge should
    apply to any form.

    ::

        // 2.x: any verb usable without declaration
        [ inet:fqdn=vertex.link ] +(seenby)> { ou:org=* }

        // 3.x: declare the extended verb once (underscore-prefixed), then use it
        $lib.model.ext.addEdge('inet:fqdn', '_seenby', 'ou:org', ({"doc": "..."}))
        inet:fqdn=vertex.link [ +(_seenby)> { ou:org=* } ]

``$lib.model.edge`` key-value store removed
-------------------------------------------

What changed
    The 2.x ``$lib.model.edge`` library -- the free-form edge-verb key-value store with ``get``
    / ``set`` / ``del`` / ``list`` (deprecated for v3.0.0) -- is removed. The rest of
    ``$lib.model`` remains; note that ``$lib.model`` now also has a read-only
    ``edge(n1form, verb, n2form)`` method that returns a ``model:edge`` object from the data
    model, so the ``$lib.model.edge`` name still resolves -- as a lookup method, not as the old
    mutable key-value library.

Why
    Edge verbs are now defined in the data model rather than tracked in an ad-hoc hive
    key-value store. This provides validation, visibility, and documentation of edge verbs.

What you need to do
    Stop calling ``$lib.model.edge.get`` / ``set`` / ``del`` / ``list``. Define extended edge
    verbs with ``$lib.model.ext.addEdge(n1form, verb, n2form, edgeinfo)`` -- the verb is the
    second argument and the verb must be prefixed with an underscore (e.g. ``_myedge``)
    -- and rely on the model for edge-verb metadata.

    ::

        // 2.x: ad-hoc edge metadata in a key-value store
        $lib.model.edge.set(refs, doc, 'documentation string')
        $verbs = $lib.model.edge.list()

        // 3.x: define the edge verb in the model
        $lib.model.ext.addEdge('doc:report', '_discusses', 'entity:name', ({"doc": "documentation string"}))

``$lib.model.ext.addUnivProp`` / ``delUnivProp`` removed
--------------------------------------------------------

What changed
    The extended-model Storm APIs ``$lib.model.ext.addUnivProp()`` and
    ``$lib.model.ext.delUnivProp()`` are removed.

Why
    Universal properties are removed in 3.x, so there is no longer a mechanism to define an
    extended universal property.

What you need to do
    Stop using ``$lib.model.ext.addUnivProp`` / ``delUnivProp``. Add an extended property to
    the specific form(s) with ``$lib.model.ext.addFormProp()`` instead, or model the data on an
    appropriate interface-supplied property.

    ::

        // 2.x: define an extended universal property
        $lib.model.ext.addUnivProp("_score", ("int", ({})), ({"doc": "..."}))

        // 3.x: define an extended property on a specific form
        $lib.model.ext.addFormProp("inet:ip", "_score", ("int", ({})), ({"doc": "..."}))
