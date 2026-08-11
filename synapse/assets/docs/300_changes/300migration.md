<a id="vtx_300_migration"></a>


# Synapse 3.0.0 Migration Guide

This guide helps you prepare your existing Synapse 2.x integrations for Synapse 3.0.0 -- your Storm queries, packages, triggers, crons, macros, configuration, and the client or automation code that talks to a Synapse service. In-place migration of an existing 2.x Cortex's data is not part of this release (see the [Cortex storage and data model changes](300migration.md#cortex-storage-and-data-model-changes) section below): you stand up a new 3.x deployment and point your ported integrations at it, rather than upgrading a running 2.x deployment in place. Work through the sections in order: prepare, review the Cortex storage and data model changes, update configuration, port Storm, port integrations, and validate. The larger model reshapes should be reviewed by an analyst.

For the exhaustive list of incompatibilities see [Synapse 3.0.0 Breaking Changes](300breakingchanges.md#vtx_300_breakingchanges), and for operator-level detail see [Synapse 3.0.0 DevOps Guide](300devops.md#vtx_300_devops). This guide cross-references both rather than duplicating them.

## Before you begin

1.  Provision Python 3.14. Synapse 3.x requires the 3.14.x line (`>=3.14,<3.15`); importing under an earlier interpreter raises. Update venvs, CI runners, and any host that imports the `synapse` package. See [Minimum Python Version 3.14](devops-python-version.md#vtx_300_devops-python-version).
2.  Pull the 3.x Docker image tags. The base `vertexproject/synapse` image is now built on the official Python 3.14 image, and the published set is the base plus the `-aha`, `-axon`, `-cortex`, and `-jsonstor` variants. The 2.x `cryotank` and `stemcell` images are gone; rebase any custom image off `vertexproject/synapse:v3.0.0b1`.
3.  Keep your existing 2.x deployment running and unchanged. You will stand up a separate 3.x deployment to port your integrations against rather than upgrading 2.x in place, so the 2.x services and their data remain available throughout (and as a fallback). Back up services as usual.
4.  Read [Synapse 3.0.0 Breaking Changes](300breakingchanges.md#vtx_300_breakingchanges) end to end and inventory what your deployment uses: custom config keys, Storm packages, triggers, crons, macros, and any code that talks to a service over Telepath or HTTP.

## Cortex storage and data model changes

3.x changes the on-disk Cortex storage layout. When 3.x opens a 2.x Cortex directory it detects the 2.x `cortex:version` and raises `BadStorageVersion` rather than migrating in place. See [NID Layer Storage Format](devops-layer-storage-nid.md#vtx_300_devops-layer-storage-nid).

> [!NOTE]
> Automated migration of an existing 2.x Cortex is **not part of this release**. Evaluate Synapse 3.0.0 against a new 3.x Cortex; a supported path for migrating existing Cortex data is expected in a later release. The rest of this guide -- porting Storm, configuration, and integrations -- applies regardless of how your data is eventually moved.

The following 3.x model and storage changes determine how data is stored and queried (and are what a future migration will need to apply); review them so your Storm and tooling target the 3.x shapes:

- **NID storage.** Layers are keyed by Cortex-wide 64-bit integer NIDs rather than 32-byte BUIDs, and the index fan-out collapses into a single `indx` db. See [NID Layer Storage Format](devops-layer-storage-nid.md#vtx_300_devops-layer-storage-nid).
- **Form and property renames.** Many forms and props are renamed; update your Storm to the new names. Existing data is reconciled when a Cortex is migrated to 3.x. See [Form and Property Renames](datamodel-form-renames.md#vtx_300_datamodel-form-renames) and [Typed Name/Id Forms](datamodel-typed-names-ids.md#vtx_300_datamodel-typed-names-ids).
- **IP unification.** `inet:ipv4` and `inet:ipv6` become the single `inet:ip` form (system value is now a `(version, int)` tuple), and the CIDR/range forms `inet:cidr4` / `inet:cidr6` (and `inet:net4` / `inet:net6`) become `inet:net`. See [Merged inet:ipv4 / inet:ipv6 into inet:ip](datamodel-ip-unification.md#vtx_300_datamodel-ip-unification).
- **Microsecond timestamps.** Time values use epoch microseconds (not milliseconds) and the repr is ISO 8601. See [Microsecond Timestamps and ISO-8601 Repr](datamodel-timestamps.md#vtx_300_datamodel-timestamps).
- **Typed property values.** `node.get()` returns a property value as a `(type, value)` pair. See [Typed Property Values](datamodel-typed-values.md#vtx_300_datamodel-typed-values).
- **Observed time and intervals.** The universal `.seen` property becomes the `:seen` interval on forms that implement `meta:observable`, and time-plus-duration data collapses into `:period`. See [Intervals and Timestamps](datamodel-intervals.md#vtx_300_datamodel-intervals).

The larger model reshapes are not simple one-to-one renames and will need analyst review when planning a migration: most impactful is the removal of the flat `inet:web:*` model in favor of the platform-oriented `inet:service:*` family (see [inet:service:* Model Updates](datamodel-inet-service.md#vtx_300_datamodel-inet-service)); the contact and campaign/goal remodels (`ps:contact` -\> `entity:contact`, `ou:campaign`/`ou:goal` -\> `entity:campaign`/`entity:goal`) likewise warrant review (see [Form and Property Renames](datamodel-form-renames.md#vtx_300_datamodel-form-renames)).

## Update configuration

3.x rejects an unknown configuration key at boot, so every removed key must be deleted from your `cell.yaml` (and any `SYN_*` environment variables) before starting a service. See [Removed and Changed Configuration Options](devops-storage-config-changes.md#vtx_300_devops-storage-config-changes).

1.  Remove the Cortex `modules` key. Cortexes no longer load in-process Python Core modules. Reimplement any custom Core-module behavior as a Storm package, an extended model registered via `$lib.model.ext.*`, or a separate service. See [Cortex Core Modules Removed](admin-core-modules-removed.md#vtx_300_admin-core-modules-removed).

2.  Remove the per-layer tuning keys `layers:lockmemory` and `layers:logedits` (there is no replacement; tune the per-layer NID cache with `layers:cache:size`), plus the fully-removed `cron:enable`, `trigger:enable`, `layer:lmdb:map_async`, `layer:lmdb:max_replay_log`, `provenance:en`, and `storm:interface:search` keys. Remove the hidden Cell keys `auth:ctor`, `auth:conf`, `nexslog:async`, and `cell:ctor`. Remove the Cell `inaugural` key; users and roles it seeded on a previous boot are unaffected, and new ones are provisioned with `aha:admin` plus the `auth.user.add` / `auth.role.add` Storm commands. Remove the hidden Cell `aha:svcinfo` key and unset any `SYN_<CELL>_AHA_SVCINFO` environment variables -- a leftover key fails the boot but a leftover environment variable is silently ignored; a service now always registers the `urlinfo` of its real listener, so there is no replacement override. See [Removed and Changed Configuration Options](devops-storage-config-changes.md#vtx_300_devops-storage-config-changes).

    ``` yaml
    # 2.x cortex cell.yaml
    modules:
      - myorg.synmods.MyCoreModule
    layers:lockmemory: true
    layers:logedits: true
    cron:enable: true

    # 3.x cortex cell.yaml -- removed keys deleted
    layers:cache:size: 10000
    max:nodes: 0
    ```

3.  Convert per-layer `mirror` / `upstream` sync. The per-layer follower options are gone. For full-service replication, run the whole Cortex as a mirror by deploying an additional instance under the same AHA provisioning secret (the Cell `mirror` config has been removed; mirrors follow the AHA determined leader dynamically); for layer-to-layer sync, use layer push/pull (`layer.push.add` / `layer.pull.add`). Note that, unlike Cortex/Cell config keys, a stale `mirror` or `upstream` key left on a *layer definition* is silently ignored rather than rejected at boot -- but you should still remove `mirror`, `upstream`, `lockmemory`, and `logedits` from layer definitions. See [Layer upstream/mirror Removed (use push/pull)](devops-layer-sync-pushpull.md#vtx_300_devops-layer-sync-pushpull).

    ``` text
    // 3.x: configure a layer pull via Storm
    layer.pull.add $dstlayriden `tcp://root:secret@cortex.example.org/*/layer/{$srclayriden}`
    ```

4.  Review container logging. Synapse containers now emit JSON structured logs by default. If you previously set `SYN_LOG_STRUCT=true` you can remove it, since it is now the default. To keep unstructured text output, set `SYN_LOG_STRUCT=false` on the container. See [Logging](devops-logging.md#vtx_300_devops-logging).

## Port your Storm

Audit every Storm query, macro, trigger, cron, and package for the changes below.

1.  **Removed and relocated \$lib surfaces.** `$lib.user` -\> `$lib.auth.users.get()`; `$lib.str` and `$lib.text()` -\> `.join` and backtick strings; `$lib.vars`, `$lib.bytes` (reduced to `fromints()`), `$lib.ps` -\> `$lib.task`, `$lib.inet.whois.guid`, `$lib.notifications`, and `$lib.projects` removed or reshaped; `$lib.gen` public helpers removed and the `gen.*` commands flattened (`gen.ou.org` -\> `gen.org`). See [Removed and Relocated Storm Libraries](storm-lib-removed.md#vtx_300_storm-lib-removed).

2.  **No boolean/null library accessors** (`$lib.true` / `$lib.false` / `$lib.null`). Use the first-class literals `(true)` / `(false)` / `(null)` (and bare `true` / `false` / `null` in expressions). See [Removed and Relocated Storm Libraries](storm-lib-removed.md#vtx_300_storm-lib-removed).

3.  **Object access conventions.** Zero-argument accessors are now properties: `$node.form`, `$node.ndef`, `$node.value` (no parens); `$node.iden()` is replaced by the integer `$node.nid`. Dict-like objects (`$lib.globals`, `$lib.env`) use deref/setitem, and `.pack()` is gone from View/Layer/User/Role. See [Storm Object Access Conventions](storm-object-conventions.md#vtx_300_storm-object-conventions).

    ``` text
    // 2.x
    $valu = $node.value()
    $v = $lib.globals.get(mykey)

    // 3.x
    $valu = $node.value
    $v = $lib.globals.mykey
    ```

4.  **Virtual, meta, and universal properties.** `.seen` is now the relative interface property `:seen`; `.created` (and `.updated`) stay as leading-dot node meta properties. Address structural sub-values with the no-whitespace `.virt` dot (for example `inet:server.ip` or `:period.min`). See [Virtual Properties in Storm](storm-virtual-properties-syntax.md#vtx_300_storm-virtual-properties-syntax).

5.  **Cron and trigger commands/APIs.** `cron.add` takes `<period> <query>` with the new period syntax; `cron.move` / `cron.enable` / `cron.disable` (and the trigger equivalents) fold into `cron.mod` / `trigger.mod` with `--enabled`. `trigger.add` takes `condition` and `storm` positionally (no `--query`). The cdef query key is renamed `query` -\> `storm`. See [Cron and Trigger API Changes](storm-cron-and-trigger-api.md#vtx_300_storm-cron-and-trigger-api).

    ``` text
    // 2.x
    cron.add --hourly 30 { inet:ipv4#stale | delnode }
    trigger.add node:add --form inet:ipv4 --query { $lib.print(hi) }

    // 3.x
    cron.add hourly@:30 { inet:ip#stale | delnode }
    trigger.add node:add --form inet:ip { $lib.print(hi) }
    ```

6.  **Macros.** The macro definition lost its `user` field; read provenance from `creator` and grant access with `macro.grant` / `$lib.macro.grant()`. See [Storm Macro Definition Changes](storm-macros.md#vtx_300_storm-macros).

7.  **Tag glob matching.** Wildcards now allow zero-length matches, so `#foo*` and `#foo**` match a node tagged only `#foo`. Audit globs that relied on a wildcard forcing at least one character. See [Tag Glob Zero-Length Matching](storm-tag-glob-matching.md#vtx_300_storm-tag-glob-matching).

8.  **Syntax and operators.** Inbound pivots/joins accept only `*`; dotted property suffixes are no longer allowed inside property tokens; a dot in a deref or tag segment must hug its operand (no leading whitespace). New additive features include `in` / `not in`, the `as` cast, and pivot target lists. See [Storm Syntax and Operator Changes](storm-syntax-operators.md#vtx_300_storm-syntax-operators).

9.  **HTTP SSL options.** Replace `ssl_verify` and `ssl_opts` on `$lib.inet.http.*` with a single `ssl` dictionary (the boolean becomes the `verify` key). See [HTTP/Axon SSL Option Changes](storm-http-ssl-options.md#vtx_300_storm-http-ssl-options).

    ``` text
    // 2.x
    $resp = $lib.inet.http.get($url, ssl_verify=$verify)

    // 3.x
    $resp = $lib.inet.http.get($url, ssl=({"verify": $verify}))
    ```

10. **Package description fields.** Rename `descr` to `desc` on command definitions, `optic.actions` entries, and `optic.spotlight.extractors` entries in your package YAML -- a pkgdef still using `descr` in one of these spots fails schema validation. See [Package description fields renamed to ``desc``](storm-package-command-desc.md#vtx_300_storm-package-command-desc).

## Port integrations

Update any code that drives a Synapse service over Telepath or HTTP.

1.  **Async-only Telepath.** The synchronous Telepath shims are removed: `synapse.glob.sync` / `synchelp` no longer exist, `openurl()` is a coroutine, proxy methods must be awaited, and generator methods are iterated with `async for`. Wrap client logic in an async function driven by `asyncio.run()`. See [Synchronous Telepath Removed](devops-telepath-async-only.md#vtx_300_devops-telepath-async-only).

    ``` python
    # 3.x: async-only
    import asyncio
    import synapse.telepath as s_telepath

    async def main():
        async with await s_telepath.openurl(url) as proxy:
            async for mesg in proxy.storm('inet:fqdn'):
                dostuff(mesg)

    asyncio.run(main())
    ```

2.  **CoreApi and CellApi changes.** Legacy `CoreApi` methods are removed (`addNode` / `addNodes` -\> `callStorm`; `getModelDefs()` -\> `getModelDef()`; the `sync*` RPCs -\> Cortex mirroring / layer push-pull). Hive and name-based auth helpers are removed from `CellApi`; use the iden-based `getUserDefByName` / `addUserRule` / `setUserAdmin` path. All versioned HTTP API endpoints also moved from the `/api/v1/` to the `/api/v3/` prefix (the `/api/v1/storm/nodes` endpoint is removed entirely -- use `/api/v3/storm`). See [Breaking API Changes for Integrators](misc-breaking-api.md#vtx_300_misc-breaking-api) and [HTTP API Endpoints Moved from /api/v1 to /api/v3](misc-http-api-v3.md#vtx_300_misc-http-api-v3).

3.  **Single feed format.** `addFeedData` drops its leading format-name argument and always takes the packed-node format; pass just the items (and `viewiden`), with `reqmeta=False` when the items have no export-meta header. Drop `--format` from `synapse.tools.cortex.feed`. See [Single Feed Data Format](devops-feed-single-format.md#vtx_300_devops-feed-single-format).

    ``` python
    # 2.x
    await prox.addFeedData('syn.nodes', items, viewiden=viewiden)

    # 3.x
    await prox.addFeedData(items, viewiden=viewiden, reqmeta=False)
    ```

## Validate

After the new 3.x services are running, confirm the deployment before cutting over production traffic.

1.  **Smoke queries.** Run a few representative lifts against the 3.x Cortex (using the Storm CLI `python -m synapse.tools.storm <url>`, since `cmdr` is removed -- see [CLI Tool Changes (cmdr, cellauth, reorg)](devops-cli-tools.md#vtx_300_devops-cli-tools)). Spot-check the forms your queries and packages depend on under their new names (for example `inet:ip`, `crypto:hash:sha256`, `entity:contact`).
2.  **Confirm crons and triggers.** List jobs and triggers with the 3.x command set (`cron.list` / `cron.stat` and `trigger.list`) and verify each re-created job has the expected `storm` query, `enabled` state, and `creator` / `user`. See [Cron and Trigger API Changes](storm-cron-and-trigger-api.md#vtx_300_storm-cron-and-trigger-api).
3.  **Watch the logs.** Tail the service logs for warnings or errors while you exercise ported Storm, packages, and integrations against the new Cortex. The logs are now ISO-8601 UTC microsecond formatted (see [Synapse 3.0.0 DevOps Guide](300devops.md#vtx_300_devops)).
