.. _vtx_300_devops-telepath-async-only:

Synchronous Telepath Removed
============================

Telepath proxies are now strictly asynchronous. The transparent synchronous
wrappers that let 2.x code call remote APIs without ``await`` have been removed.

What changed
    In 2.x, a Telepath ``Proxy`` could be driven from synchronous code: methods
    were wrapped so they could be called without ``await``, generator methods
    supported plain iteration, and the proxy supported a synchronous context
    manager. This was backed by a global background event-loop thread and
    ``synapse.glob.sync()`` / ``synapse.glob.synchelp()``.

    In 3.x those shims are gone. ``synapse.glob`` no longer defines ``sync`` or
    ``synchelp``. In ``synapse/telepath.py``, ``Method.__call__`` is now an
    ``async def`` coroutine, generator-method calls return an async-only
    ``GenrIter`` (iterate with ``async for`` or collect with ``await .list()``),
    and ``openurl()`` is itself an ``async def`` coroutine that must be awaited.
    The ``Proxy`` is a ``Base`` subclass, so it is used as an async context
    manager via ``__aenter__`` / ``__aexit__``.

Why
    Removing the dual sync/async machinery -- the global background event-loop
    thread and the ``run_coroutine_threadsafe`` shims -- simplifies the client,
    removes a class of cross-thread bugs, and matches the async-first nature of
    the rest of the codebase. The contract is now explicit: every remote call is
    a coroutine.

What you need to do
    Audit any integration or automation script that talked to a Synapse service
    over Telepath from synchronous code. Wrap your logic in an async function and
    drive it with ``asyncio.run()``; ``await`` the ``openurl()`` call and every
    proxy method call; iterate generator methods such as ``storm()`` with
    ``async for`` (or ``await <call>.list()``). Remove any reliance on
    ``synapse.glob.sync()`` / ``synapse.glob.synchelp()`` in your own code --
    those helpers no longer exist.

    .. code-block:: python

        # 2.x: synchronous usage worked transparently
        import synapse.telepath as s_telepath

        with s_telepath.openurl(url) as proxy:
            for mesg in proxy.storm('inet:fqdn'):
                dostuff(mesg)

    .. code-block:: python

        # 3.x: async-only
        import asyncio
        import synapse.telepath as s_telepath

        async def main():
            async with await s_telepath.openurl(url) as proxy:
                async for mesg in proxy.storm('inet:fqdn'):
                    dostuff(mesg)

        asyncio.run(main())
