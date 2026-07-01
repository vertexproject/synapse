.. _vtx_300_devops-storage-config-changes:

Removed and Changed Configuration Options
=========================================

Synapse 3.0.0 removes several Cortex and base-Cell configuration options and changes the
meaning of one layer cache option. An unknown configuration key is rejected at boot, so any
removed key must be deleted from your ``cell.yaml`` (and ``SYN_*`` environment variables)
before upgrading.

Removed Cortex configuration keys
---------------------------------

What changed
    The Cortex ``modules`` option is removed -- Cortexes no longer support Core modules. The
    per-layer tuning options ``layers:lockmemory`` and ``layers:logedits`` are removed; the
    Cortex no longer seeds ``lockmemory`` or ``logedits`` onto new layer definitions, and a
    layer definition no longer carries those keys. Several previously-deprecated options are
    also fully removed from the confdefs: ``cron:enable``, ``trigger:enable``,
    ``layer:lmdb:map_async``, ``layer:lmdb:max_replay_log``, and ``provenance:en``. The
    remaining layer-related Cortex options are ``layers:cache:size`` and ``max:nodes``.

Why
    Core modules could arbitrarily change Cortex behavior and are replaceable by Storm
    packages. ``logedits`` is obsolete now that there is no separate per-layer node-edit log
    (edits are tracked deconflicted in the Nexus log), and ``lockmemory`` is no longer applied
    to layer definitions. The other options had already been documented as deprecated/ignored
    in 2.x and are now gone entirely.

What you need to do
    Remove these keys from any Cortex configuration before upgrading. If you tuned layer
    memory cache via ``layers:lockmemory`` / ``layers:logedits``, there is no replacement for
    those; to tune the per-layer node cache use ``layers:cache:size`` (see the next section).

    .. code-block:: yaml

        # 2.x cortex cell.yaml
        modules:
          - myproj.mymodule.MyModule
        layers:lockmemory: true
        layers:logedits: true
        cron:enable: true
        trigger:enable: true
        provenance:en: false

    .. code-block:: yaml

        # 3.x cortex cell.yaml -- removed keys deleted
        layers:cache:size: 10000
        max:nodes: 0

Changed semantics: ``layers:cache:size``
-----------------------------------------

What changed
    The ``layers:cache:size`` Cortex option (and the per-layer ``cache:size`` option) still
    exists, but its description changed from "Default buid cache size for new layers" to
    "Default nid cache size for new layers". It now sizes the per-layer in-memory cache of
    NID-keyed storage nodes. The effective size is resolved with priority: per-layer
    ``cache:size`` > Cortex ``layers:cache:size`` > the default of 10000.

Why
    Storage nodes are now keyed by NID rather than BUID, so the in-memory cache is keyed by
    NID and the option was relabeled to match.

What you need to do
    No action is required to keep using ``layers:cache:size``; existing values continue to
    work as a cache-entry count. Just be aware it now sizes the NID cache rather than the BUID
    cache.

    .. code-block:: yaml

        # 3.x cortex cell.yaml
        layers:cache:size: 10000

Removed hidden Cell configuration keys
--------------------------------------

What changed
    Three hidden base-Cell options are removed: ``auth:ctor`` (a Python path used to hook
    construction of the cell auth object), ``auth:conf`` (extended config for an alternate
    auth constructor), and ``nexslog:async`` (already deprecated and ignored). The
    ``cell:ctor`` option, used by the now-removed stemcell, is also gone.

Why
    ``auth:ctor`` and ``auth:conf`` supported pluggable alternate auth backends that are no
    longer a supported extension point, and ``nexslog:async`` had already been marked
    deprecated and ignored.

What you need to do
    Remove ``auth:ctor``, ``auth:conf``, and ``nexslog:async`` from any service ``cell.yaml``.
    If you used a custom auth constructor via ``auth:ctor``, that hook is gone -- manage auth
    through the standard auth subsystem (for example ``moduser`` / ``modrole``).

    .. code-block:: yaml

        # 2.x cell.yaml
        auth:ctor: my.module.AuthCtor
        auth:conf: {}
        nexslog:async: true

    .. code-block:: yaml

        # 3.x cell.yaml -- auth:ctor / auth:conf / nexslog:async removed
