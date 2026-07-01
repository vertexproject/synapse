.. _vtx_300_devops-layer-sync-pushpull:

Layer upstream/mirror Removed (use push/pull)
=============================================

What changed
    The per-layer ``mirror`` and ``upstream`` configuration options have been removed.

    In 2.x a layer definition could carry a ``mirror`` (or ``upstream``) URL, which made
    that layer act as a follower of a remote layer. In 3.x the follower and mirror code
    has been removed.

    The supported replacements remain available: Cortex-level service mirroring (the Cell
    ``mirror`` configuration) for full-service replication, and Layer push/pull
    (``layer.push.add`` / ``layer.pull.add`` and the corresponding ``Cortex`` APIs
    ``addLayrPush`` / ``addLayrPull`` / ``delLayrPush`` / ``delLayrPull``) for
    layer-to-layer synchronization.

Why
    The per-layer ``mirror``/``upstream`` mechanisms were legacy synchronization paths
    superseded by the more efficient Cortex mirroring and Layer push/pull. Removing them
    reduces complexity and steers deployments to the supported, Nexus-based replication.

What you need to do
    Before upgrading, identify any layers configured with ``mirror`` or ``upstream`` and
    re-architect them. For full-service replication, run the whole Cortex as a mirror via
    the Cell ``mirror`` configuration. For layer-to-layer synchronization, configure Layer
    push/pull. Remove ``mirror``, ``upstream``, ``lockmemory``, and ``logedits`` keys from
    layer definitions and cell configuration.

    .. code-block:: python

        # 2.x: a layer definition with a mirror follower
        ldef = {'mirror': 'aha://cortex.example.org/...', 'logedits': True}
        await core.addLayer(ldef)

    In 3.x, set up a layer pull instead (from the source layer into the destination layer):

    ::

        // 3.x: configure a layer pull via Storm
        // (the URL is a backtick format string so $srclayriden is interpolated)
        layer.pull.add $dstlayriden `tcp://root:secret@cortex.example.org/*/layer/{$srclayriden}`

    Or run the entire Cortex as a mirror by setting the Cell ``mirror`` configuration:

    .. code-block:: yaml

        # 3.x: cell.yaml on the follower Cortex
        mirror: aha://cortex.example.org/...
