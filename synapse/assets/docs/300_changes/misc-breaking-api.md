<a id="vtx_300_misc-breaking-api"></a>


# Breaking API Changes for Integrators

Synapse 3.0.0 removes a number of long-deprecated Telepath and HTTP API methods. Integrators driving Synapse services over Telepath or the HTTP API should review the changes below and update their clients. Entries are ordered roughly by how commonly the affected methods appear in integration code.

## Legacy CoreApi node, model, and sync methods removed

What changed

:   Several long-deprecated or now-unsupported `CoreApi` Telepath methods are removed: `addNode`, `addNodes`, `addUnivProp`, `delUnivProp`, `getCoreMods`, `getFeedFuncs`, `getFormsByPrefix`, `iterUnivRows`, `syncIndexEvents`, `syncLayerNodeEdits`, and `syncLayersEvents`. The `getModelDefs` rename is covered as a separate entry below.

Why

:   `addNode` and `addNodes` were superseded by Storm long ago. `getCoreMods` is gone because Cortexes no longer support pluggable Core modules. The universal-prop add/delete helpers and the named feed function listing were retired, and the `sync*` layer-event RPCs were superseded by the supported Cortex mirroring and layer push/pull mechanisms.

What you need to do

:   Use Storm to add nodes instead of `addNode` / `addNodes`, and add extended form and tag properties via the `$lib.model.ext` Storm APIs (e.g. `$lib.model.ext.addFormProp`). Note that universal extended properties (what `addUnivProp` created) are no longer supported in 3.x and have no direct replacement -- `$lib.model.ext` no longer exposes an `addUnivProp` method. Stop depending on `getCoreMods`. For replication between layers, use the supported Cortex mirroring / layer push-pull configuration rather than the `sync*` methods.

    ``` python
    # 2.x
    await prox.addNode('inet:fqdn', 'foo.com')

    # 3.x
    await prox.callStorm('[ inet:fqdn=foo.com ]')
    ```

## Deprecated Hive and auth convenience methods removed from CellApi

What changed

:   The Hive accessor methods (`getHiveKey`, `getHiveKeys`, `listHiveKey`, `setHiveKey`, `popHiveKey`, `saveHiveTree`) and the deprecated name-based auth convenience methods (`getAuthInfo`, `addAuthRule`, `delAuthRule`, `setAuthAdmin`) are removed from `CellApi`.

Why

:   The Hive subsystem is removed in 3.0.0 (`synapse.lib.hive` no longer exists). The legacy name-based auth helpers were superseded by the iden-based user and role APIs (`addUserRule`, `delUserRule`, `setUserAdmin`, `getUserDef`, `getUserDefByName`, and the role equivalents), which remain available.

What you need to do

:   Stop calling these methods over Telepath. For auth, use the iden-based APIs: look up the user with `getUserDefByName` / `getUserDef`, then call `addUserRule` / `delUserRule` / `setUserAdmin` with the user iden. There is no Hive replacement.

    ``` python
    # 2.x
    await prox.setHiveKey(('foo', 'bar'), 'baz')
    await prox.addAuthRule('visi', (True, ('node', 'add')))

    # 3.x
    user = await prox.getUserDefByName('visi')
    await prox.addUserRule(user['iden'], (True, ('node', 'add')))
    # (no Hive replacement)
    ```

## CoreApi getModelDefs() replaced by getModelDef()

What changed

:   The Cortex Telepath method `getModelDefs()` (plural), which returned a list of model definition tuples, is removed and replaced by `getModelDef()` (singular), which returns a single model definition dictionary.

Why

:   The 3.x model is represented as one consolidated definition rather than a list of stacked module definitions, reflecting the removal of pluggable Core modules.

What you need to do

:   Change integration code that called `getModelDefs()` to call `getModelDef()` and consume a single model definition object instead of iterating a list.

    ``` python
    # 2.x
    modeldefs = await prox.getModelDefs()
    for name, modl in modeldefs:
        ...

    # 3.x
    modeldef = await prox.getModelDef()
    ```

## Deprecated /api/v1/storm/nodes HTTP endpoint removed

What changed

:   The Cortex HTTP API endpoint `POST /api/v1/storm/nodes` (handler `StormNodesV1`) is removed. In 2.x it streamed packed nodes and emitted a deprecation warning.

Why

:   The endpoint was deprecated in favor of the message-based storm endpoint, which returns the full Storm message stream (including non-node messages), so the node-only variant was dropped.

What you need to do

:   Switch HTTP integrations from the removed `/api/v1/storm/nodes` to `/api/v3/storm` and filter the message stream for `('node', ...)` messages client-side, or use `/api/v3/storm/call` when you need a single return value. (The HTTP API version prefix also moved from `v1` to `v3` -- see [HTTP API Endpoints Moved from /api/v1 to /api/v3](misc-http-api-v3.md#vtx_300_misc-http-api-v3).)

    ``` bash
    # 2.x
    POST /api/v1/storm/nodes
    {"query": "inet:ipv4"}

    # 3.x
    POST /api/v3/storm
    {"query": "inet:ip"}
    # consume the message stream; keep messages whose [0] == 'node'
    ```

## BadOperArg removed; input validation now raises BadArg

What changed

:   The `synapse.exc.BadOperArg` exception class is removed. In addition, many Storm operations that reject bad input now raise `synapse.exc.BadArg` where 2.x raised `synapse.exc.StormRuntimeError` (for example `movetag`, `tee`, `batch --size`, `diff` with `--tag` / `--prop`, `task.kill`, trigger and cron iden matching, `$lib.min` / `$lib.max`, `$lib.lift.byPropAlts` / `byPropRefs`, `$lib.time.format`, and set-mutability checks).

Why

:   Synapse now uses a single convention: `BadArg` rejects input known to be bad, while `StormRuntimeError` is reserved for failures that occur after the arguments are accepted. The `BadOperArg` class was redundant with `BadArg`.

What you need to do

:   Stop catching `BadOperArg` -- it no longer exists. Update Python integrations and Storm `catch` clauses that relied on `StormRuntimeError` for these validation errors to catch `BadArg` instead (catching the common base `SynErr` also works).

    ``` python
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
    ```

## Version reporting uses PEP 440 strings

What changed

:   Synapse version reporting moved to PEP 440 version strings. `synapse.version` (and `synapse.lib.version.version`) is now a string such as `3.0.0` rather than a `(major, minor, patch)` integer tuple, and `synapse.lib.version.verstring` is removed. `getCellInfo()` no longer includes the `verstring` keys. In Storm, `$lib.version.synapse` returns a version string, and `$lib.version.matches()` accepts either a version string or a list of version integers.

Why

:   A single PEP 440 string is the canonical, pip-compatible representation and can express prerelease suffixes (for example `1.2.3rc1`), which an integer tuple cannot.

What you need to do

:   Update code that treated `synapse.version` as a tuple (for example indexing `synapse.version[0]` or comparing tuples). `synapse.lib.version.parse()` returns a comparable version object and `release()` returns the `(major, minor, patch)` triple. Replace `synapse.lib.version.verstring` with `synapse.version`, and stop reading `verstring` from `getCellInfo()` output.

    ``` python
    # 2.x
    major = synapse.version[0]
    verstr = synapse.lib.version.verstring

    # 3.x
    major = synapse.lib.version.release()[0]
    verstr = synapse.version
    ```

## HTTP API error codes align with synapse.exc class names

What changed

:   Every error code returned by a synapse HTTP API in the `code` field of an error envelope now names a real `synapse.exc` class. Five codes were renamed to match exceptions that already existed:

    | Was | Now | Where |
    |---|---|---|
    | `DupUser` | `DupUserName` | `/api/v3/auth/adduser` |
    | `DupRole` | `DupRoleName` | `/api/v3/auth/addrole` |
    | `NotAuthenticated` | `AuthDeny` | any API, when the session is not logged in |
    | `MissingField` | `SchemaViolation` | any API, when a required body field is absent |
    | `BadHttpParam` | `BadArg` | any API, when a query parameter value is invalid |

Why

:   Clients reconstruct an exception from the envelope by resolving `code` against `synapse.exc` (`synapse.exc.getSynErrCtor()`, used by `synapse.lib.httpapi.result()`). A code with no matching class silently collapsed to a base `SynErr`, so a caller could not tell one failure from another. Rather than adding classes that exist only to make wire codes resolve, the codes now reuse the exceptions synapse already raises for these conditions over Telepath and Storm, so one condition has one name on every transport.

    Two of the renames merge a distinction that previously existed on the wire. This is deliberate, and the HTTP status code continues to carry it:

    - `AuthDeny` is now returned both when there is no session at all (`401`) and when the caller is authenticated but not permitted (`403`). A single handler can return it for either reason, so check the status code, not just `code`.
    - `SchemaViolation` is now returned both when a request body does not parse and when it parses but omits a required field. Both are `400`, so use `mesg` to tell them apart.

What you need to do

:   Update any client matching on the literal strings `DupUser`, `DupRole`, `NotAuthenticated`, `MissingField`, or `BadHttpParam`. Clients that resolve the code against `synapse.exc` keep working, but note that `synapse.exc.NotAuthenticated`, `synapse.exc.BadHttpParam`, and `synapse.exc.MissingField` no longer exist, so code that imports or catches them by name must be updated.

    ``` python
    # 2.x
    if item.get('code') == 'NotAuthenticated':
        reauth()

    # 3.x -- AuthDeny also covers the authenticated-but-forbidden case
    if item.get('code') == 'AuthDeny' and resp.status == 401:
        reauth()
    ```

## Storm HTTP API always streams JSON lines

What changed

:   The `/api/v3/storm` endpoint always streams newline delimited JSON, and the response declares the content type `application/jsonl`. The 2.x `stream` key in the request body is removed; a `stream` value sent by a client is ignored.

    In 2.x the default framing wrote each Storm message with no delimiter and relied on the HTTP chunked encoding to separate them, and `"stream": "jsonlines"` opted in to a trailing newline per message.

Why

:   The chunk-delimited framing is not reliable in practice: a reverse proxy may coalesce or split chunks, so a reader that parsed one chunk as one message could fail on a deployment that worked in testing. Newline delimited JSON gives readers a delimiter that survives the transport, which made the opt-in mode the only one worth keeping.

What you need to do

:   Read the response one line at a time instead of parsing each HTTP chunk as a message. Clients that already sent `"stream": "jsonlines"` need no change beyond dropping the now-unused key.

    ``` python
    # 2.x
    data = {'query': query, 'stream': 'jsonlines'}
    async with sess.get(url, json=data) as resp:
        async for byts, x in resp.content.iter_chunks():
            mesg = json.loads(byts)

    # 3.x
    data = {'query': query}
    async with sess.get(url, json=data) as resp:
        async for line in resp.content:
            mesg = json.loads(line)
    ```

:   The `synapse.tools.storm` CLI and the `synapse.tools.storm._http.HttpCortex` client do this for you.

## Unused 2.x modules removed

What changed

:   Seven modules that no longer had a caller inside Synapse are removed:

    | Module | What it was |
    |---|---|
    | `synapse.lib.encoding` | The 2.x pluggable ingest format registry: the `encoders` / `decoders` maps, `encode()` / `decode()` with the `'utf8,base64,-utf8'` layering syntax, the `csv` / `xml` / `lines` / `json` / `jsonl` / `mpk` format yielders, `addFormat()`, and `iterdata()`. |
    | `synapse.lib.ingest` | The 2.x ingest subsystem, already emptied to a placeholder. |
    | `synapse.mindmeld` | Already emptied to a placeholder. |
    | `synapse.lib.interval` | The `fold()` / `overlap()` / `parsetime()` helpers for 2.x `(min, max)` interval tuples. |
    | `synapse.lib.ratelimit` | The `RateLimit` class. |
    | `synapse.lib.slaboffs` | The `SlabOffs` offset helper. |
    | `synapse.lookup.iso3166` | An ISO-3166 country code table. |

Why

:   Each was a leftover of a 2.x subsystem that 3.0.0 replaced, and nothing in Synapse imported any of them. `synapse.lib.encoding`'s format functions still took a 2.x ingest definition dict (`format:csv:quote`, `format:lines:skipre`, and so on) describing directives that no longer exist. `synapse.lib.interval` is additionally the wrong shape for 3.x, where an interval norms to a `(min, max, duration)` triple rather than a `(min, max)` pair.

What you need to do

:   Stop importing these modules. `RateLimit` and `SlabOffs` are the two most likely to have been borrowed by an external Storm package or service; copy the implementation into your own codebase if you still need it. To read a `.jsonl` file, iterate the file and decode each line -- which is all `iterdata(fd, format='jsonl')` did.

    ``` python
    # 2.x
    import synapse.lib.encoding as s_encoding
    items = list(s_encoding.iterdata(fd, False, format='jsonl'))

    # 3.x
    import synapse.lib.json as s_json
    items = [s_json.loads(line) for line in fd]
    ```

## Unraised exception classes removed from synapse.exc

What changed

:   Ten exception classes that Synapse never raised are removed from `synapse.exc`: `BadCtorType`, `DupIndx`, `ModAlreadyLoaded`, `NoSuchAct`, `NoSuchDecoder`, `NoSuchEncoder`, `NoSuchLift`, `NoSuchOpt`, `PathExists`, and `StepTimeout`.

Why

:   Their names trace to subsystems 3.0.0 removed -- `ModAlreadyLoaded` to pluggable `CoreModule` loading, `NoSuchAct` to the old action and feed registry, `NoSuchLift` and `DupIndx` to the pre-3.x layer index API, `StepTimeout` to the old test step helper, and `NoSuchDecoder` / `NoSuchEncoder` to the removed `synapse.lib.encoding`. Keeping an exception that nothing raises is a promise Synapse cannot break but also never keeps.

    Note that the similarly named `NoSuchIndx` and `NoSuchDir` are still raised and remain available.

What you need to do

:   Nothing at runtime -- because Synapse never raised these, no `except` clause that names one has ever fired. The only thing that breaks is code that references the name directly, such as an import or a retry tuple; remove those references.

    ``` python
    # 2.x
    from synapse.exc import NoSuchOpt, StepTimeout
    RETRY_ON = (s_exc.NotReady, s_exc.StepTimeout)

    # 3.x
    RETRY_ON = (s_exc.NotReady,)
    ```

## Cell.initFromArgv() and Cell.execmain() no longer accept outp

What changed

:   The `outp` keyword argument is removed from `synapse.lib.cell.Cell.initFromArgv()` and `synapse.lib.cell.Cell.execmain()`. Both now take `argv` only.

Why

:   The argument had already stopped doing anything -- `execmain()` defaulted it to `synapse.lib.output.stdout` and threaded it into `initFromArgv()`, which never read it. Service startup reports through logging instead, which is what a container or an init system collects.

What you need to do

:   Drop `outp=` from any call. This matters at startup: a service entry point that still passes it raises `TypeError` before the Cell is created. Nothing replaces it -- configure logging (`SYN_LOG_LEVEL`, `SYN_LOG_STRUCT`) to control what a starting service emits.

    ``` python
    # 2.x
    await MyCell.execmain(sys.argv[1:], outp=outp)

    # 3.x
    await MyCell.execmain(sys.argv[1:])
    ```
