.. _vtx_300_devops:

Synapse 3.0.0 DevOps Guide
==========================

This guide is for operators deploying and running Synapse 3.x services. It is the
DevOps subset of the 3.0.0 changes, going deeper than the upgrade runbook. For the
ordered upgrade steps see :ref:`vtx_300_migration`, and for the complete list of
incompatibilities see :ref:`vtx_300_breakingchanges`. The topic pages referenced
below are the authoritative source for each change.

Runtime requirements
--------------------

Synapse 3.x requires Python 3.14, pinned to the 3.14 minor release
(``requires-python`` is ``>=3.14,<3.15``); importing ``synapse`` on an earlier
interpreter raises. Provision the 3.14.x line on every host that runs Synapse or
imports the ``synapse`` package -- venvs, CI runners, and automation hosts. See
:ref:`vtx_300_devops-python-version`.

Storage format and migration
----------------------------

Synapse 3.x replaces the per-layer, BUID-keyed on-disk storage model with a
Cortex-wide 64-bit integer Node ID (NID) model (:ref:`vtx_300_devops-layer-storage-nid`).
Each node ndef is assigned a NID once at the Cortex level; the ndef-to-NID mapping
lives in a ``v3stor`` slab at ``slabs/layersv3.lmdb``, and each layer stores nodes
in a single ``bynid`` db plus one unified ``indx`` db. Because an 8-byte NID
replaces the 32-byte BUID in every index row and the mapping is shared across all
index types and layers, index sizes shrink and lifts are faster. This is transparent
to analysts -- no Storm or query changes are required.

This is NOT an automatic in-place upgrade. When 3.x opens a 2.x Cortex directory it
detects the 2.x ``cortex:version`` and raises ``BadStorageVersion`` rather than
migrating in place. Note that the per-layer storage version is not the gate (both
2.x and 3.x report layer version 11) -- the Cortex-level version is.

Automated migration of an existing 2.x Cortex is not part of this release. Stand
up a new 3.x Cortex and keep your 2.x deployment intact; a
supported path for migrating existing Cortex data is expected in a later release. When
that lands, expect a new on-disk layout -- the layer directories plus a new Cortex-level
``slabs/layersv3.lmdb`` mapping db -- that differs in size and shape from 2.x, which will
affect backup sizing.

Integrators who parsed raw layer LMDB files directly, or who relied on the
BUID-keyed index layout, must update to the NID model.

Nexus and replication
---------------------

Node edits are now deconflicted before they are written to the Nexus log
(:ref:`vtx_300_devops-nexus-deconfliction`). In 2.x raw edits went to the Nexus and the
deconflicted copy was written to a separate per-layer ``nodeeditlog`` slab gated by
``logedits``. In 3.x ``saveNodeEdits`` computes the deconflicted edits first and
sends only those to the Nexus; the per-layer ``nodeeditlog`` slab is gone and the
local edit form is keyed by NID rather than BUID.

Operational impact:

- Smaller storage and less per-layer write amplification, since deconflicted edits
  are stored once in the Nexus log rather than in the Nexus plus a deduplicated
  per-layer copy.
- Downstream consumers should read the Cortex Nexus log directly (filtered to the
  layer iden and the ``'edits'`` entries) instead of aggregating per-layer edit logs.
  The Nexus log contains already-deconflicted edits keyed by NID.
- The ``logedits`` option no longer exists -- remove it from layer configuration.

Layer synchronization
---------------------

The per-layer ``mirror`` and ``upstream`` configuration options have been removed,
along with the follower code that consumed them (:ref:`vtx_300_devops-layer-sync-pushpull`).
The supported replacements are:

- Cortex-level service mirroring, for full service replication. The Cell ``mirror``
  configuration option has also been removed: mirrors now follow the current AHA determined
  leader dynamically, so deploying an additional instance under the same AHA provisioning
  secret is all that is required (see :ref:`deployment-guide-mirror`). The new ``parent``
  option is *not* a rename of ``mirror`` -- it is an explicit override that pins a service
  to a fixed upstream telepath URL and is rarely needed.
- Layer push/pull (``layer.push.add`` / ``layer.pull.add`` and the corresponding
  Cortex APIs) for layer-to-layer synchronization.

Before upgrading, identify any layers configured with ``mirror`` or ``upstream`` and
re-architect them. Note that the layer definition validator uses
``additionalProperties: True``, so a stray ``mirror``/``upstream`` key will not fail
validation -- it is silently ignored with no follower behavior. ``setLayerInfo`` now
only accepts ``name``, ``desc``, ``cache:size``, and ``readonly``.

In 3.x, running the whole Cortex as a mirror requires no follower ``cell.yaml`` config:
deploy the additional instance under the same AHA provisioning secret and it follows the
AHA determined leader automatically (see :ref:`deployment-guide-mirror`).

::

    // 3.x: configure a layer pull from a source layer into a destination layer
    layer.pull.add $dstlayriden `tcp://root:secret@cortex.example.org/*/layer/{$srclayriden}`

Configuration
-------------

An unknown configuration key is rejected at boot, so every removed key must be
deleted from ``cell.yaml`` (and ``SYN_*`` environment variables) before upgrading
(:ref:`vtx_300_devops-storage-config-changes`).

Removed Cortex keys:

- ``modules`` -- Cortexes no longer support in-process Python Core modules; the
  ``getCoreMod()``/``getCoreMods()``/``loadCoreModule()`` APIs and the backing
  ``synapse.lib.module``/``synapse.lib.modules`` are gone. Reimplement custom
  behavior as a Storm package or via ``$lib.model.ext.*`` (:ref:`vtx_300_admin-core-modules-removed`).
- ``layers:lockmemory`` and ``layers:logedits`` -- no longer seeded onto new layers
  and no longer carried in layer definitions. There is no replacement for these.
- Previously-deprecated keys ``cron:enable``, ``trigger:enable``,
  ``layer:lmdb:map_async``, ``layer:lmdb:max_replay_log``, and ``provenance:en`` are
  fully removed.

The remaining layer-related Cortex options are ``layers:cache:size`` and ``max:nodes``.

Changed semantics -- ``layers:cache:size`` still exists, but now sizes the per-layer
in-memory cache of NID-keyed storage nodes (relabeled from "buid cache" to "nid
cache"). The effective size resolves with priority: per-layer ``cache:size`` >
Cortex ``layers:cache:size`` > the default of 10000. No action is required to keep
using it; existing values continue to work as a cache-entry count.

Removed hidden Cell keys: ``auth:ctor``, ``auth:conf``, ``nexslog:async``, and
``cell:ctor`` (used by the removed stemcell). Remove these from any service
``cell.yaml``. If you used a custom auth constructor via ``auth:ctor``, that hook is
gone -- manage auth through the standard subsystem (for example ``moduser`` /
``modrole``).

.. code-block:: yaml

    # 2.x cortex cell.yaml
    modules:
      - myproj.mymodule.MyModule
    layers:lockmemory: true
    layers:logedits: true
    cron:enable: true

.. code-block:: yaml

    # 3.x cortex cell.yaml -- removed keys deleted
    layers:cache:size: 10000
    max:nodes: 0

Logging
-------

Synapse containers now emit JSON structured logs by default; the
``synapse`` Dockerfile sets ``SYN_LOG_STRUCT="true"``, whereas 2.x containers defaulted
to unstructured text and structured output was opt-in. Set the ``SYN_LOG_STRUCT=false``
environment variable on the container to restore unstructured text output
(:ref:`vtx_300_devops-logging`).

Log timestamps are now rendered in UTC as ISO-8601 with microsecond precision and a
trailing ``Z`` (for example ``2026-06-25T13:42:07.123456Z``), affecting both the
structured JSON ``time`` field and the unstructured text logs
(:ref:`vtx_300_devops-logging`). In 2.x the default was local-time with
comma-separated milliseconds.

Update any log-ingestion or parsing pipelines (SIEM, fluentd/vector grok patterns,
dashboards) that assumed the old format. ``SYN_LOG_DATEFORMAT`` still maps to the
formatter ``datefmt``, but it is now applied via ``strftime`` against a UTC
datetime; if you set a custom format and want sub-second precision you must include
``%f``.

.. code-block:: bash

    # 3.x default (UTC, microseconds, ISO-8601 'Z')
    # 2026-06-25T13:42:07.123456Z [INFO] cortex started ...

    # custom UTC format (include %f for microseconds):
    export SYN_LOG_DATEFORMAT='%Y-%m-%dT%H:%M:%S.%fZ'

Feeds
-----

Cortex feed ingest is standardized on a single packed-node format; the pluggable
feed-format registry is removed and the leading format-name argument is dropped from
``addFeedData`` (:ref:`vtx_300_devops-feed-single-format`). The telepath signature is now
``addFeedData(items, *, viewiden=None, reqmeta=True)``. When ``reqmeta`` is ``True``
the first item must be an export-meta header dict (``vers`` of ``1`` and a
``synapse_ver`` satisfying ``>=3.0.0b1,<4.0.0``). The HTTP ``/api/v3/feed`` endpoint
always requires the export-meta header.

The CLI ``synapse.tools.cortex.feed`` dropped its ``--format`` / ``-f`` option and
infers the format from the file extension: ``.mpk`` and ``.nodes`` are packed-node
files (meta header read from the file), while ``.json``, ``.jsonl``, and ``.yaml``
are fed without a meta header.

.. code-block:: bash

    # 2.x CLI -- explicit --format
    python -m synapse.tools.cortex.feed -c cell://./core --format syn.nodes data.nodes

    # 3.x CLI -- format inferred from the .nodes/.mpk extension
    python -m synapse.tools.cortex.feed -c cell://./core data.nodes

Automatic Storm service discovery
---------------------------------

An active Cortex now discovers Storm services through AHA and adds them
automatically. A service that exposes a Storm service API advertises the
``stormservice`` feature when it registers with AHA. The Cortex watches the AHA
service topology -- using the initial service listing and live ``svc:add``
updates -- and, for each such service, adds it using an ``aha://<type>...`` URL
that resolves to the current leader of that service type.

This replaces the manual ``service.add <name> aha://<name>...`` step from Storm
service deployment. Deploy the service under the same AHA provisioning secret as
the Cortex and it is added with no operator action. Services are keyed by type,
so re-registration, reconnects, and Cortex reboots do not create duplicates, and
a service already added under a name matching its type is left untouched.

Service tooling
---------------

The top-level tool modules under ``synapse.tools.<name>`` are removed; only the
service-oriented subpackage paths work now (:ref:`vtx_300_devops-cli-tools`). Update
scripts, cron jobs, systemd units, container entrypoints, and Dockerfiles. CLI
arguments are otherwise unchanged. The layout is:

- ``synapse.tools.service.*`` -- ``apikey``, ``backup``, ``demote``, ``healthcheck``,
  ``livebackup``, ``modrole``, ``moduser``, ``promote``, ``reload``, ``shutdown``,
  ``snapshot``.
- ``synapse.tools.cortex.*`` -- ``csv`` (renamed from ``csvtool``), ``docmodel``,
  ``feed``, and the ``layer`` subpackage.
- ``synapse.tools.axon.*`` -- ``copy``, ``dump``, ``get``, ``load``, ``put``.
- ``synapse.tools.utils.*`` -- ``autodoc``, ``easycert``, ``guid``, ``json2mpk``,
  ``rstorm``.
- ``synapse.tools.aha.*`` -- ``clone``, ``easycert``, ``enroll``, ``list``,
  ``mirror``, and a ``provision`` subpackage.
- ``synapse.tools.storm`` -- the Storm CLI (replacing ``cmdr``), plus the ``storm.pkg``
  subpackage (``storm.pkg.gen``, ``storm.pkg.doc``) for generating and documenting Storm
  packages.

Removed tools:

- ``cmdr`` and ``synapse.lib.cmdr`` are removed -- use the Storm CLI
  ``synapse.tools.storm`` (lines beginning with ``!`` route to the local interpreter).
- ``cellauth`` is removed -- manage auth with ``synapse.tools.service.moduser`` /
  ``modrole`` (plus the Storm ``$lib.auth.*`` APIs). ``moduser`` takes the username
  as a positional argument and supports ``--url``, ``--add``/``--del``, ``--list``,
  ``--admin``, ``--passwd``, ``--email``, ``--locked``, ``--grant``/``--revoke``,
  ``--allow``/``--deny``, and ``--gate``. See :ref:`vtx_300_admin-permissions` for the
  renamed and removed permission strings.
- The Cryotank service and its tools, the Hive tools and ``synapse.lib.hive``, and
  ``synapse.tools.pkgs.gendocs`` are removed. Build Storm package docs with
  ``synapse.tools.storm.pkg.doc`` (requires ``pandoc``).

.. code-block:: bash

    # 2.x -> 3.x tool path examples
    python -m synapse.tools.backup /srv/core /backups/core        # 2.x
    python -m synapse.tools.service.backup /srv/core /backups/core # 3.x

    python -m synapse.tools.cmdr cell://vertex/storage            # 2.x
    python -m synapse.tools.storm cell://vertex/storage           # 3.x

    python -m synapse.tools.cellauth cell://core modify visi --addrule node.add  # 2.x
    python -m synapse.tools.service.moduser --url cell://core --allow node.add visi  # 3.x

Telepath for operational scripts
--------------------------------

Telepath proxies are now strictly asynchronous; the transparent synchronous wrappers
that let 2.x code call remote APIs without ``await`` are removed, and
``synapse.glob.sync()`` / ``synapse.glob.synchelp()`` no longer exist
(:ref:`vtx_300_devops-telepath-async-only`). Audit any ops automation that talked to a
Synapse service over Telepath from synchronous code. Wrap your logic in an async
function driven by ``asyncio.run()``, ``await`` the ``openurl()`` call and every
proxy method call, and iterate generator methods such as ``storm()`` with
``async for`` (or ``await <call>.list()``).

.. code-block:: python

    # 3.x: async-only
    import asyncio
    import synapse.telepath as s_telepath

    async def main():
        async with await s_telepath.openurl(url) as proxy:
            async for mesg in proxy.storm('inet:fqdn'):
                dostuff(mesg)

    asyncio.run(main())
