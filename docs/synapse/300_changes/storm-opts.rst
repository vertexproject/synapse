.. _vtx_300_storm-opts:

Storm opts API Changes
======================

The ``opts`` dictionary accepted by the Storm APIs (``storm`` / ``callStorm`` / ``count`` over
Telepath and HTTP) changed in several user-facing ways in Synapse 3.0.0. For the full per-key
reference see :ref:`dev_storm_opts`.

``opts`` is now keyword-only
----------------------------

What changed
    The Telepath ``storm``, ``callStorm``, and ``count`` methods (and ``reqValidStorm`` /
    ``isValidStorm``) now take ``opts`` as a keyword-only argument -- the signature is
    ``storm(text, *, opts=None)``. Passing ``opts`` positionally is no longer accepted.

Why
    Making ``opts`` keyword-only prevents accidental positional misuse and matches the
    async-only Telepath calling convention.

What you need to do
    Pass ``opts`` by keyword.

    .. code-block:: python

        # 2.x (positional opts accepted)
        await prox.callStorm(text, opts)

        # 3.x (keyword-only)
        await prox.callStorm(text, opts=opts)

``idens`` replaced by ``nids``
------------------------------

What changed
    The ``idens`` opt (a list of hex ``iden`` / BUID hashes used as initial input nodes) is
    removed. Initial input is now seeded with ``nids`` -- a list of integer Node IDs (NIDs).
    Each value must be an integer NID or a ``BadTypeValu`` is raised.

Why
    The 3.x layer storage format keys nodes by an integer NID rather than a 32-byte BUID, so
    node references in the API surface use the NID.

What you need to do
    Migrate callers from ``idens`` (hex hashes) to ``nids`` (integers).

    .. code-block:: python

        # 2.x
        opts = {'idens': ('ee6b92c9fd848a2cb00f3a3618148c512b58456b8b51fbed79251811597eeea3',)}

        # 3.x
        opts = {'nids': (1099511627992,)}

Node-output opts consolidated under ``node:opts``
-------------------------------------------------

What changed
    The top-level ``repr``, ``links``, and ``show:storage`` opts are no longer read at the top
    level of the ``opts`` dict. They are now sub-keys of a single ``node:opts`` dictionary,
    which also adds ``embeds``, ``virts``, and ``verbs`` controls. Setting the old top-level
    keys has no effect (they are silently ignored).

Why
    Grouping the node-packing controls into one ``node:opts`` dict gives a single, extensible
    place to configure how nodes are serialized.

What you need to do
    Move ``repr`` / ``links`` / ``show:storage`` into ``node:opts``.

    .. code-block:: python

        # 2.x
        opts = {'repr': True, 'links': True, 'show:storage': True}

        # 3.x
        opts = {'node:opts': {'repr': True, 'links': True, 'show:storage': True}}

        # New 3.x controls
        opts = {'node:opts': {'virts': True, 'verbs': False, 'embeds': {'inet:ipv4': ('asn',)}}}

Packed node shape: ``nid``, ``meta``, and edge-verb counts
----------------------------------------------------------

What changed
    The packed node (pode) info dict is now keyed by an integer ``nid`` (Node ID) instead of the
    2.x hex ``iden``, gains a ``meta`` dictionary (e.g. created/updated time), and -- by default
    -- includes ``n1verbs`` and ``n2verbs`` light-edge verb count dictionaries. The ``links``
    trail entries are now ``(nid, info)`` tuples whose first element is an integer NID. Virtual
    property values appear under a ``virts`` key when ``node:opts`` ``virts`` is set.

Why
    The packed node reflects the 3.x NID-based storage and the new edge-count and virtual-property
    model features.

What you need to do
    Update any code that reads ``pode[1]['iden']`` to use ``pode[1]['nid']`` (an integer), parse
    link trails as integer-NID-keyed tuples, and -- if you do not want the edge-verb counts --
    set ``node:opts`` ``verbs`` to ``False``.

    .. code-block:: python

        # 3.x packed node info dict
        {'nid': 1099511627992,
         'meta': {'created': 1662491423034000},
         'props': {'type': 'unicast'},
         'tags': {},
         'tagprops': {},
         'path': {},
         'n1verbs': {},
         'n2verbs': {}}

``vars`` name validation
------------------------

What changed
    ``vars`` keys must be strings, and the names ``lib``, ``node``, and ``path`` are reserved and
    rejected. Supplying a non-string key or one of the reserved names raises ``BadArg``.

Why
    The reserved names collide with the built-in ``$lib``, ``$node``, and ``$path`` Storm
    variables, so they can no longer be overridden via ``vars``.

What you need to do
    Rename any ``vars`` keys that use ``lib``, ``node``, or ``path``, and ensure all keys are
    strings.
