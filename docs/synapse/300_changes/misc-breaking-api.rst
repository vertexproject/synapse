.. _vtx_300_misc-breaking-api:

Breaking API Changes for Integrators
====================================

Synapse 3.0.0 removes a number of long-deprecated Telepath and HTTP API methods. Integrators driving
Synapse services over Telepath or the HTTP API should review the changes below and update their clients.
Entries are ordered roughly by how commonly the affected methods appear in integration code.

Legacy CoreApi node, model, and sync methods removed
----------------------------------------------------

What changed
    Several long-deprecated or now-unsupported ``CoreApi`` Telepath methods are removed: ``addNode``,
    ``addNodes``, ``addUnivProp``, ``delUnivProp``, ``getCoreMods``, ``getFeedFuncs``,
    ``getFormsByPrefix``, ``iterUnivRows``, ``syncIndexEvents``, ``syncLayerNodeEdits``, and
    ``syncLayersEvents``. The ``getModelDefs`` rename is covered as a separate entry below.

Why
    ``addNode`` and ``addNodes`` were superseded by Storm long ago. ``getCoreMods`` is gone because
    Cortexes no longer support pluggable Core modules. The universal-prop add/delete helpers and the
    named feed function listing were retired, and the ``sync*`` layer-event RPCs were superseded by the
    supported Cortex mirroring and layer push/pull mechanisms.

What you need to do
    Use Storm to add nodes instead of ``addNode`` / ``addNodes``, and add extended form and tag
    properties via the ``$lib.model.ext`` Storm APIs (e.g. ``$lib.model.ext.addFormProp``). Note that
    universal extended properties (what ``addUnivProp`` created) are no longer supported in 3.x and have
    no direct replacement -- ``$lib.model.ext`` no longer exposes an ``addUnivProp`` method. Stop
    depending on ``getCoreMods``. For replication between layers, use the supported Cortex mirroring /
    layer push-pull configuration rather than the ``sync*`` methods.

    .. code-block:: python

        # 2.x
        await prox.addNode('inet:fqdn', 'foo.com')

        # 3.x
        await prox.callStorm('[ inet:fqdn=foo.com ]')

Deprecated Hive and auth convenience methods removed from CellApi
-----------------------------------------------------------------

What changed
    The Hive accessor methods (``getHiveKey``, ``getHiveKeys``, ``listHiveKey``, ``setHiveKey``,
    ``popHiveKey``, ``saveHiveTree``) and the deprecated name-based auth convenience methods
    (``getAuthInfo``, ``addAuthRule``, ``delAuthRule``, ``setAuthAdmin``) are removed from ``CellApi``.

Why
    The Hive subsystem is removed in 3.0.0 (``synapse.lib.hive`` no longer exists). The legacy name-based
    auth helpers were superseded by the iden-based user and role APIs (``addUserRule``, ``delUserRule``,
    ``setUserAdmin``, ``getUserDef``, ``getUserDefByName``, and the role equivalents), which remain
    available.

What you need to do
    Stop calling these methods over Telepath. For auth, use the iden-based APIs: look up the user with
    ``getUserDefByName`` / ``getUserDef``, then call ``addUserRule`` / ``delUserRule`` / ``setUserAdmin``
    with the user iden. There is no Hive replacement.

    .. code-block:: python

        # 2.x
        await prox.setHiveKey(('foo', 'bar'), 'baz')
        await prox.addAuthRule('visi', (True, ('node', 'add')))

        # 3.x
        user = await prox.getUserDefByName('visi')
        await prox.addUserRule(user['iden'], (True, ('node', 'add')))
        # (no Hive replacement)

CoreApi getModelDefs() replaced by getModelDef()
------------------------------------------------

What changed
    The Cortex Telepath method ``getModelDefs()`` (plural), which returned a list of model definition
    tuples, is removed and replaced by ``getModelDef()`` (singular), which returns a single model
    definition dictionary.

Why
    The 3.x model is represented as one consolidated definition rather than a list of stacked module
    definitions, reflecting the removal of pluggable Core modules.

What you need to do
    Change integration code that called ``getModelDefs()`` to call ``getModelDef()`` and consume a single
    model definition object instead of iterating a list.

    .. code-block:: python

        # 2.x
        modeldefs = await prox.getModelDefs()
        for name, modl in modeldefs:
            ...

        # 3.x
        modeldef = await prox.getModelDef()


Deprecated /api/v1/storm/nodes HTTP endpoint removed
----------------------------------------------------

What changed
    The Cortex HTTP API endpoint ``POST /api/v1/storm/nodes`` (handler ``StormNodesV1``) is removed. In 2.x
    it streamed packed nodes and emitted a deprecation warning.

Why
    The endpoint was deprecated in favor of the message-based storm endpoint, which returns the full Storm
    message stream (including non-node messages), so the node-only variant was dropped.

What you need to do
    Switch HTTP integrations from the removed ``/api/v1/storm/nodes`` to ``/api/v3/storm`` and filter the
    message stream for ``('node', ...)`` messages client-side, or use ``/api/v3/storm/call`` when you need a
    single return value. (The HTTP API version prefix also moved from ``v1`` to ``v3`` -- see
    :ref:`vtx_300_misc-http-api-v3`.)

    .. code-block:: bash

        # 2.x
        POST /api/v1/storm/nodes
        {"query": "inet:ipv4"}

        # 3.x
        POST /api/v3/storm
        {"query": "inet:ip"}
        # consume the message stream; keep messages whose [0] == 'node'

BadOperArg removed; input validation now raises BadArg
------------------------------------------------------

What changed
    The ``synapse.exc.BadOperArg`` exception class is removed. In addition, many Storm operations that
    reject bad input now raise ``synapse.exc.BadArg`` where 2.x raised ``synapse.exc.StormRuntimeError``
    (for example ``movetag``, ``tee``, ``batch --size``, ``diff`` with ``--tag`` / ``--prop``,
    ``task.kill``, trigger and cron iden matching, ``$lib.min`` / ``$lib.max``,
    ``$lib.lift.byPropAlts`` / ``byPropRefs``, ``$lib.time.format``, and set-mutability checks).

Why
    Synapse now uses a single convention: ``BadArg`` rejects input known to be bad, while
    ``StormRuntimeError`` is reserved for failures that occur after the arguments are accepted. The
    ``BadOperArg`` class was redundant with ``BadArg``.

What you need to do
    Stop catching ``BadOperArg`` -- it no longer exists. Update Python integrations and Storm ``catch``
    clauses that relied on ``StormRuntimeError`` for these validation errors to catch ``BadArg`` instead
    (catching the common base ``SynErr`` also works).

    .. code-block:: python

        # 2.x
        try:
            await prox.callStorm(text, opts=opts)
        except s_exc.BadOperArg:
            ...

        # 3.x
        try:
            await prox.callStorm(text, opts=opts)
        except s_exc.BadArg:
            ...

Version reporting uses PEP 440 strings
--------------------------------------

What changed
    Synapse version reporting moved to PEP 440 version strings. ``synapse.version`` (and
    ``synapse.lib.version.version``) is now a string such as ``3.0.0`` rather than a
    ``(major, minor, patch)`` integer tuple, and ``synapse.lib.version.verstring`` is removed.
    ``getCellInfo()`` no longer includes the ``verstring`` keys. In Storm, ``$lib.version.synapse``
    returns a version string, and ``$lib.version.matches()`` accepts either a version string or a list
    of version integers.

Why
    A single PEP 440 string is the canonical, pip-compatible representation and can express prerelease
    suffixes (for example ``1.2.3rc1``), which an integer tuple cannot.

What you need to do
    Update code that treated ``synapse.version`` as a tuple (for example indexing ``synapse.version[0]``
    or comparing tuples). ``synapse.lib.version.parse()`` returns a comparable version object and
    ``release()`` returns the ``(major, minor, patch)`` triple. Replace ``synapse.lib.version.verstring``
    with ``synapse.version``, and stop reading ``verstring`` from ``getCellInfo()`` output.

    .. code-block:: python

        # 2.x
        major = synapse.version[0]
        verstr = synapse.lib.version.verstring

        # 3.x
        major = synapse.lib.version.release()[0]
        verstr = synapse.version
