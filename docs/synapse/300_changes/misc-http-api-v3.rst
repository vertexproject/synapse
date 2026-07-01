.. _vtx_300_misc-http-api-v3:

HTTP API Endpoints Moved from /api/v1 to /api/v3
================================================

What changed
    All versioned Cortex and Cell HTTP API endpoints moved from the ``/api/v1/`` path prefix to
    ``/api/v3/`` in Synapse 3.0.0. For example, ``/api/v1/storm`` is now ``/api/v3/storm``,
    ``/api/v1/storm/call`` is now ``/api/v3/storm/call``, and auth endpoints such as
    ``/api/v1/auth/adduser`` are now ``/api/v3/auth/adduser``. The 2.x ``/api/v1/`` paths are
    removed -- there are no ``/api/v1/`` or ``/api/v2/`` compatibility aliases. The unversioned
    ``/api/v0/`` endpoints (such as the health/active checks) are unchanged.

.. note::

    Several Cortex HTTP endpoints now accept **API key authentication only** (the
    ``X-API-KEY`` header); HTTP Basic auth and session cookies are rejected with ``401``. This
    applies to ``/api/v3/storm``, ``/api/v3/storm/call``, ``/api/v3/storm/export``,
    ``/api/v3/model``, ``/api/v3/model/norm``, the user-defined ``/api/ext/*`` endpoints, and
    the Cortex file endpoints ``/api/v3/axon/files/*``. Use an API key for any integration that
    drives these endpoints over HTTP.

Why
    The HTTP API surface has backward-incompatible changes in 3.0.0 -- for example the Storm
    message stream, the ``opts`` dictionary, and the packed-node shape -- so the version prefix
    was advanced to ``v3`` to signal the new contract.

What you need to do
    Update every HTTP client, integration, reverse-proxy rule, and saved request to use the
    ``/api/v3/`` prefix in place of ``/api/v1/``. A request to a ``/api/v1/`` path will no longer
    resolve.

    .. code-block:: bash

        # 2.x paths
        /api/v1/storm
        /api/v1/storm/call
        /api/v1/storm/export
        /api/v1/auth/adduser

        # 3.x paths
        /api/v3/storm
        /api/v3/storm/call
        /api/v3/storm/export
        /api/v3/auth/adduser

    Some endpoints changed beyond the version prefix: see :ref:`vtx_300_misc-breaking-api` (for
    example the removed ``/api/v1/storm/nodes`` endpoint) and :ref:`vtx_300_storm-opts` (for the
    ``opts`` dictionary changes).
