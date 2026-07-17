.. _vtx_300_devops-telepath-clientv2:

Telepath Client Replaced by ClientV2
====================================

The legacy ``synapse.telepath.Client`` has been removed. Every persistent
Telepath client -- inside Synapse services and in the tools shipped with Synapse
-- now uses ``synapse.telepath.ClientV2``.

What changed
    ``synapse.telepath.Client`` no longer exists. Code that created a
    reconnecting client with ``s_telepath.Client.anit(url, ...)`` must now use
    ``s_telepath.ClientV2.anit(url, onlink=...)`` and obtain a live proxy for
    each use with ``await client.proxy(timeout=...)``.

    ``ClientV2`` is not new. It has existed alongside the old ``Client`` for some
    time; this change removes the legacy class and standardizes every client on
    ``ClientV2``.

Why
    The old ``Client`` had architectural problems and, in practice, was
    frequently used incorrectly. It exposed a proxy that could be reached before
    a link was actually established -- and that was re-established silently
    across reconnects -- so callers routinely raced the connection: reaching for
    a proxy that was not yet live, or holding one that had gone away on a
    reconnect. These patterns produced intermittent, hard-to-reproduce race
    conditions.

    ``ClientV2`` makes the contract explicit. ``await client.proxy()`` returns a
    proxy only once a link is live, and waits (up to an optional timeout) when
    one is not yet available. Because readiness is now expressed simply by
    awaiting ``proxy()``, the conversion also let us delete a large number of
    ad-hoc "``<thing>ready``" events -- for example the Cortex's ``axready`` and
    similar per-client ready flags and onlink callbacks -- that existed only to
    paper over the old client's timing gaps.

What you need to do
    Audit any integration or tooling code that constructed a
    ``synapse.telepath.Client``. Switch it to ``ClientV2`` and resolve a live
    proxy at the point of use rather than caching one or gating on your own
    "ready" signal:

    .. code-block:: python

        # old: legacy reconnecting Client
        import synapse.telepath as s_telepath

        client = await s_telepath.Client.anit(url)
        # ... reach for the client / a cached proxy and hope it is connected ...

    .. code-block:: python

        # new: ClientV2, resolve a live proxy per use
        import synapse.telepath as s_telepath

        client = await s_telepath.ClientV2.anit(url, onlink=onlink)
        proxy = await client.proxy(timeout=30)
        await proxy.someMethod()

    If you register an ``onlink`` callback, note that ``ClientV2`` invokes it as
    ``onlink(proxy, urlinfo)``.
