<a id="vtx_300_devops-cli-tools"></a>


# CLI Tool Changes (cmdr, cellauth, reorg)

Synapse 3.0.0 reorganizes the command line tools under `synapse.tools` into service-oriented subpackages, removes the legacy `cmdr` and `cellauth` tools along with several retired subsystems, and teaches the Storm CLI to connect over the HTTP API. The entries below are ordered by how likely they are to affect an existing 2.x deployment.

## Tools relocated into namespaced subpackages

What changed

:   The top-level tool modules under `synapse.tools.<name>` -- which in 2.x were deprecation shims (warning since `v2.225.0`) re-exporting from a subpackage -- are deleted in 3.0.0. Only the dotted subpackage paths work now. The 3.x layout is: `synapse.tools.service.*` holds `apikey`, `backup`, `demote`, `healthcheck`, `modrole`, `moduser`, `promote`, `reload`, `shutdown`, and `snapshot`; `synapse.tools.cortex.*` holds `csv` (the renamed `csvtool`), `docmodel`, `feed`, and a `layer` subpackage; `synapse.tools.axon.*` holds `copy`, `dump`, `get`, `load`, and `put`; `synapse.tools.utils.*` holds `doc`, `easycert`, `guid`, and `json2mpk`; and `synapse.tools.aha.*` holds `clone`, `del`, `easycert`, `enroll`, `list`, `mirror`, and a `provision` subpackage. (`synapse.tools.utils.autodoc` is removed outright rather than relocated -- see [rstorm and Sphinx removed](#rstorm-and-sphinx-removed----docs-are-built-with-mdstormmddocs) below.)

Why

:   Grouping tools by the service they operate on clarifies usage and ownership, and 3.0.0 completes a migration that began with the `v2.225.0` deprecation warnings.

What you need to do

:   Update scripts, cron jobs, systemd units, container entrypoints, and Dockerfiles that call the old top-level module paths. The CLI arguments are otherwise unchanged. Common mappings: `csvtool` -\> `cortex.csv`, `feed` -\> `cortex.feed`, `genpkg` -\> `storm.pkg.gen`, `easycert` -\> `utils.easycert`, `guid` -\> `utils.guid`, `json2mpk` -\> `utils.json2mpk`, `apikey` -\> `service.apikey`, `backup` -\> `service.backup`, `snapshot` -\> `service.snapshot`, `reload` -\> `service.reload`, `shutdown` -\> `service.shutdown`, `demote` -\> `service.demote`, `promote` -\> `service.promote`, `healthcheck` -\> `service.healthcheck`, `moduser` -\> `service.moduser`, `modrole` -\> `service.modrole`, `pushfile` -\> `axon.put`, `pullfile` -\> `axon.get`, and `axon2axon` -\> `axon.copy`. `autodoc` has no mapping -- it is removed, not relocated.

    ``` bash
    # 2.x
    python -m synapse.tools.pushfile cell://axon ./report.pdf
    python -m synapse.tools.csvtool ./load.storm ./data.csv --cortex cell://core
    python -m synapse.tools.backup /srv/core /backups/core

    # 3.x
    python -m synapse.tools.axon.put cell://axon ./report.pdf
    python -m synapse.tools.cortex.csv ./load.storm ./data.csv --cortex cell://core
    python -m synapse.tools.service.backup /srv/core /backups/core
    ```

## cmdr removed -- use the Storm CLI

What changed

:   The interactive command shell `synapse.tools.cmdr` is removed. The replacement is the Storm CLI, `synapse.tools.storm`.

Why

:   `cmdr` layered a bespoke command interpreter on top of Storm. The Storm CLI is the single, supported way to run interactive queries against a Cortex and exposes interpreter commands via the `!` convention.

What you need to do

:   Replace any invocation of `python -m synapse.tools.cmdr <url>` with `python -m synapse.tools.storm <url>`. In the Storm CLI, lines beginning with `!` are routed to the local interpreter (e.g. `!help`); everything else is executed as Storm. Remove any code that imports `synapse.lib.cmdr`; it no longer exists.

    ``` bash
    # 2.x
    python -m synapse.tools.cmdr cell://vertex/storage

    # 3.x
    python -m synapse.tools.storm cell://vertex/storage
    ```

## cellauth removed -- manage auth with moduser/modrole

What changed

:   The auth-management CLI `synapse.tools.cellauth` is removed. Its capabilities are now covered by `synapse.tools.service.moduser` and `synapse.tools.service.modrole` (plus the Storm `$lib.auth.*` APIs for in-Storm management).

Why

:   Auth management is consolidated into the per-object service tools and Storm auth APIs, removing the parallel `cellauth` tool with its own rule-string handling.

What you need to do

:   Replace `cellauth` invocations with `moduser`/`modrole`. `moduser` takes the username as a positional argument and supports `--url`, `--add`/`--del`, `--list`, `--admin {true,false}`, `--passwd`, `--email`, `--locked {true,false}`, `--grant`/`--revoke` (roles), `--allow`/`--deny` (permission rules, repeatable), and `--gate` (target an auth gate iden). `modrole` offers the equivalent for roles. See [Permission Changes](admin-permissions.md#vtx_300_admin-permissions) for the renamed and removed permission strings to use with `--allow`/`--deny`.

    ``` bash
    # 2.x
    python -m synapse.tools.cellauth cell://core modify visi --addrule node.add
    python -m synapse.tools.cellauth cell://core modify visi --admin true

    # 3.x
    python -m synapse.tools.service.moduser --url cell://core --allow node.add visi
    python -m synapse.tools.service.moduser --url cell://core --admin true visi
    ```

## Cryotank and Hive tooling removed

What changed

:   The Cryotank service and its CLI tools (`synapse.tools.cryo.cat`, `synapse.tools.cryo.list`) are removed, along with `synapse.cryotank` and `synapse.servers.cryotank`. The Hive tools (`synapse.tools.hive.load`, `synapse.tools.hive.save`) and the `synapse.lib.hive` library are removed.

Why

:   Cryotank and Hive are legacy subsystems retired in 3.0.0; cell configuration and state no longer live in a Hive tree, and Cryotank is no longer a shipped service.

What you need to do

:   Stop using `cryo.cat`/`cryo.list` and `hive.load`/`hive.save`. If you ran a Cryotank service, plan a migration off it before upgrading. Any code importing `synapse.lib.hive`, `synapse.cryotank`, or `synapse.servers.cryotank` must be removed -- they no longer exist.

    ``` bash
    # 2.x
    python -m synapse.tools.cryo.list cell://cryo

    # 3.x -- cryotank service removed; no replacement
    ```

## Storm CLI connects over the HTTP API

What changed

:   The Storm CLI accepts an `https://` URL in addition to the Telepath URL schemes, and drives the Cortex through the HTTP API rather than Telepath. New options apply only to those URLs: `--https-ca-dir`, `--https-noverify`, and `--https-proxy` (an aiohttp-socks compatible proxy URL). Passing any of them alongside a Telepath URL is an error.

Why

:   Telepath is frequently not reachable from an analyst workstation, while the Cortex HTTP API commonly is -- it is the interface already exposed through a reverse proxy or load balancer. This removes the need for a Telepath tunnel to use the Storm CLI against such a deployment.

What you need to do

:   Nothing; existing Telepath invocations are unchanged. To use the HTTP API, supply a user API key as the user portion of the URL. A key is required, because the Storm HTTP endpoints accept API key authentication only (see [HTTP API Endpoints Moved from /api/v1 to /api/v3](misc-http-api-v3.md#vtx_300_misc-http-api-v3)). See [API Key Support](../httpapi.md#http-api-apikey) for creating one and [storm](../userguides/syn_tools_storm.md#syn-tools-storm) for the full option list.

    ``` bash
    # telepath, unchanged
    python -m synapse.tools.storm cell://vertex/storage

    # 3.x -- over the HTTP API
    python -m synapse.tools.storm https://<apikey>@synapse.woot.com:4443/
    ```

> [!NOTE]
> When streaming a Storm query over the HTTP API, the Storm CLI sets the `keepalive` option to 6 seconds so that a long running query which produces no output does not have its connection terminated by an intermediate proxy. Override it by setting `keepalive` in an `--optsfile`. The `!export` command does not support keepalive messages; its request is bounded at one hour instead.

## rstorm and Sphinx removed -- docs are built with mdstorm/mddocs

What changed

:   `synapse.tools.utils.rstorm` (the RST documentation pre-processor) and `synapse.lib.rstorm` are removed, along with the Sphinx build (`docs/conf.py`, the RST HTML theme, and the `sphinx`/`sphinx-rtd-theme`/`sphinx-notfound-page` dependencies). `synapse.tools.utils.autodoc` is also removed: autodoc'd content (confdefs, API docs, a Storm package's command/module reference, the data model, the Storm types reference) is now requested inline with an `` ```mdautodoc `` fence at the point of use, resolved by `mdstorm` alongside every other directive.

Why

:   All Synapse documentation moved from reStructuredText to Markdown; `synapse.lib.mdstorm` and `synapse.lib.mddocs` execute Storm directives and build doc bundles directly from Markdown, with no Sphinx step. Folding autodoc generation into an `mdstorm` directive removes the separate "generate a file into a savedir, then splice it in" pre-pass and its per-bundle `mddocs.yaml` config.

What you need to do

:   If you maintained your own `.rst`/`.rstorm` documentation using `rstorm`, port it to Markdown with fenced `mdstorm`/`mdstorm-setup`/`mdshell`/`mdautodoc` directives (see `synsrc/docs/README.md` for the directive mapping) and build it with `synapse.tools.utils.mdstorm` for a single file, or with `synapse.tools.storm.pkg.doc` if it is a Storm package's `docs/` tree.

    ``` bash
    # 2.x
    python -m synapse.tools.utils.rstorm mydoc.rst --save mydoc.out.rst

    # 3.x
    python -m synapse.tools.utils.mdstorm mydoc.md --save mydoc.out.md
    ```

