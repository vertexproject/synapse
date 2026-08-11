<a id="vtx_300_storm-opts"></a>


# Storm opts API Changes

The `opts` dictionary accepted by the Storm APIs (`storm` / `callStorm` / `count` over Telepath and HTTP) changed in several user-facing ways in Synapse 3.0.0. For the full per-key reference see [Storm Opts](../devguides/storm_api.md#dev_storm_opts).

## `opts` is now keyword-only

What changed

:   The Telepath `storm`, `callStorm`, and `count` methods (and `reqValidStorm` / `isValidStorm`) now take `opts` as a keyword-only argument -- the signature is `storm(text, *, opts=None)`. Passing `opts` positionally is no longer accepted.

Why

:   Making `opts` keyword-only prevents accidental positional misuse and matches the async-only Telepath calling convention.

What you need to do

:   Pass `opts` by keyword.

    ``` python
    # 2.x (positional opts accepted)
    await prox.callStorm(text, opts)

    # 3.x (keyword-only)
    await prox.callStorm(text, opts=opts)
    ```

## `idens` replaced by `nids`

What changed

:   The `idens` opt (a list of hex `iden` / BUID hashes used as initial input nodes) is removed. Initial input is now seeded with `nids` -- a list of integer Node IDs (NIDs). Each value must be an integer NID or a `BadTypeValu` is raised.

Why

:   The 3.x layer storage format keys nodes by an integer NID rather than a 32-byte BUID, so node references in the API surface use the NID.

What you need to do

:   Migrate callers from `idens` (hex hashes) to `nids` (integers).

    ``` python
    # 2.x
    opts = {'idens': ('ee6b92c9fd848a2cb00f3a3618148c512b58456b8b51fbed79251811597eeea3',)}

    # 3.x
    opts = {'nids': (1099511627992,)}
    ```

## Node-output opts consolidated under `node:opts`

What changed

:   The top-level `repr`, `links`, and `show:storage` opts are no longer read at the top level of the `opts` dict. They are now sub-keys of a single `node:opts` dictionary, spelled `repr`, `links` and `storage`, which also adds `embeds` and `virts` controls. Setting the old top-level keys raises a `SchemaViolation`.

Why

:   Grouping the node-packing controls into one `node:opts` dict gives a single, extensible place to configure how nodes are serialized.

What you need to do

:   Move `repr` / `links` / `show:storage` into `node:opts`, noting that `show:storage` is spelled `storage` there.

    ``` python
    # 2.x
    opts = {'repr': True, 'links': True, 'show:storage': True}

    # 3.x
    opts = {'node:opts': {'repr': True, 'links': True, 'storage': True}}

    # New 3.x controls
    opts = {'node:opts': {'virts': True, 'embeds': {'inet:ipv4': {'asn': ('registrant:name',)}}}}
    ```

## `editformat` removed

What changed

:   The `editformat` opt is removed, along with the `node:edits:count` message type it produced. Edit messages are always streamed, under the name `edits` (renamed from `node:edits`, see [`node:edits` renamed to `edits`](#nodeedits-renamed-to-edits) below). Passing `editformat` raises a `SchemaViolation`, since the `opts` schema is closed (see [`opts` is validated against a schema](#opts-is-validated-against-a-schema) below).

Why

:   The `show` opt is already a general message-type allowlist, which covers the `none` case without a second edits-only knob, and the `count` summary is derivable from the `edits` list carried by every `edits` message.

What you need to do

:   Use `show` to omit `edits` from the stream, and sum the edits client-side if you need the count. Note that `show` must be non-empty -- an empty list disables filtering rather than minimizing it.

    ``` python
    # 2.x
    opts = {'editformat': 'none'}
    opts = {'editformat': 'count'}

    # 3.x -- list the message types you want; edits is simply not among them
    opts = {'show': ('node', 'print', 'warn')}

    # 3.x -- derive the 2.x count from an edits message
    count = sum(len(edit[2]) for edit in mesg[1].get('edits', ()))
    ```

## `node:edits` renamed to `edits`

What changed

:   The `node:edits` Storm message type is renamed to `edits`. The message payload is unchanged -- it still carries the `edits` and `time` keys.

Why

:   Every message in the stream already describes something the runtime did to the graph, so the `node:` prefix distinguished nothing. The shorter name also matches the `edits` key the message has always carried.

What you need to do

:   Match on `edits` wherever you matched on `node:edits`, including in `show` allowlists.

    ``` python
    # 2.x
    async for mesg in prox.storm(text, opts={'show': ('node', 'node:edits')}):
        if mesg[0] == 'node:edits':
            ...

    # 3.x
    async for mesg in prox.storm(text, opts={'show': ('node', 'edits')}):
        if mesg[0] == 'edits':
            ...
    ```

## `opts` is validated against a schema

What changed

:   The Storm `opts` dictionary is now validated against a JSON schema (`synapse.lib.schemas.stormOptsSchema`) on every Storm call. The schema is closed: an opt which is not declared raises a `SchemaViolation` rather than being silently ignored, and a declared opt with the wrong type is rejected too. The same schema validates the `stormopts` of a Storm dmon definition, which previously named three opts the dmon does not read while accepting any other key.

Why

:   The opt surface had no single description, so a misspelled or removed opt was accepted and quietly did nothing -- a `2.x` caller still passing `idens` or a top level `repr` got no indication that the opt stopped working. One schema now describes the surface, and the failure is loud.

What you need to do

:   Remove opts which no longer exist, and correct any whose value was the wrong type. A client with its own per-query state carries it in the `meta` opt rather than as top level opts; the one product specific key still declared is `readpool`, which Synapse Enterprise reads.

    ``` python
    # 2.x -- silently ignored in early 3.x, now a SchemaViolation
    opts = {'idens': ('ee6b92c9...',)}
    opts = {'repr': True}

    # 3.x
    opts = {'nids': (1099511627992,)}
    opts = {'node:opts': {'repr': True}}
    ```

## `meta` opt added

What changed

:   A new `meta` opt takes an arbitrary dictionary which the Cortex does not interpret. It is echoed back verbatim as the `meta` key of the `init` message (and omitted from `init` when the opt is not set), and is recorded on the Storm query log entry when `storm:log` is enabled. It is not a place for secrets; use `vars` for those, which are never logged.

Why

:   Clients carried their own per-query state as top level Storm opts, which meant the Cortex had to declare key names it never read in order to keep the opts schema closed. One open, explicitly caller-owned key replaces all of them.

What you need to do

:   Move any client specific keys out of the top level of `opts` and into `meta`, and read them back off the `init` message.

    ``` python
    # 2.x -- client keys alongside real Storm opts
    opts = {'view': viewiden, 'myapp:jobid': jobid}

    # 3.x
    opts = {'view': viewiden, 'meta': {'jobid': jobid}}

    # ...and on the way back out
    for (mtyp, mnfo) in msgs:
        if mtyp == 'init':
            jobid = mnfo.get('meta', {}).get('jobid')
    ```

## `task` is honored or rejected, never dropped

What changed

:   The `task` opt is no longer silently ignored when the runtime is already promoted under another iden. A caller is given the iden it asked for or a `BadArg`. Asking for an iden already in use by a running task raises, as does asking for one from a runtime already promoted under a different iden -- which is the case for a nested runtime such as one started by `$lib.storm.run()`.

Why

:   The `init` message reports the task iden, and a caller which supplied its own could silently be handed a different one, so the iden could not be relied on to cancel or correlate the query. This is the behavior the API reference already documented.

What you need to do

:   Do not pass `task` from inside a Storm runtime. Elsewhere, no change: a caller which supplied a unique iden already got it.

## `show` filters every message type

What changed

:   The `show` opt now controls the whole message stream. `init`, `fini`, and `err` were previously sent regardless of what `show` named, and are now filtered like any other type. An empty list also changed meaning: it used to disable filtering and send everything, and now sends nothing at all.

Why

:   Two message types behaving differently from the rest made the opt hard to reason about, and the empty list did the opposite of what it read like -- `{'show': []}` looked like "nothing" and delivered the full stream.

What you need to do

:   Add `init`, `fini`, or `err` to any `show` list which needs them; in particular a list which omits `err` now silently discards query errors. Replace `{'show': []}` with the opt left unset if the intent was the full stream.

    ``` python
    # 2.x -- init/fini/err arrived regardless
    opts = {'show': ['node']}

    # 3.x -- name everything the caller consumes
    opts = {'show': ['init', 'node', 'err', 'fini']}

    # 2.x -- an empty list sent the whole stream
    opts = {'show': []}

    # 3.x -- omit the opt for the whole stream; [] now sends nothing
    opts = {}
    ```

## `nexsoffs` and `nexstimeout` moved under `nexus`

What changed

:   The two nexus opts are now sub-keys of a single `nexus` dictionary: `nexsoffs` became `nexus.offset` and `nexstimeout` became `nexus.timeout`. The `nexsoffs` key of the `fini` message is unchanged.

Why

:   The two opts are only meaningful together -- a timeout with no offset does nothing -- so they group like the other paired opts rather than sitting at the top level with a shared prefix.

What you need to do

:   Move both keys under `nexus`.

    ``` python
    # 2.x
    opts = {'nexsoffs': 7759195, 'nexstimeout': 30}

    # 3.x
    opts = {'nexus': {'offset': 7759195, 'timeout': 30}}
    ```

## `node:opts` loses `verbs` and renames `show:storage`

What changed

:   The `verbs` sub-key of `node:opts` is removed and the behavior is unconditional: a packed node always carries the `n1verbs` and `n2verbs` light-edge verb counts. The `show:storage` sub-key is renamed to `storage`, matching the packed node key it populates. Both old spellings now raise a `SchemaViolation`.

Why

:   `verbs` was the only `node:opts` sub-key which defaulted to enabled, so it was the only one where omitting it and setting it differed. The counts are a dict merge over data already in memory, so there was little to gain by suppressing them. `show:storage` was the only sub-key whose name did not match the key it produced.

What you need to do

:   Drop `verbs` from any `node:opts`, and rename `show:storage` to `storage`.

    ``` python
    # 2.x / early 3.x
    opts = {'node:opts': {'verbs': False, 'show:storage': True}}

    # 3.x
    opts = {'node:opts': {'storage': True}}
    ```

## Packed node shape: `nid`, `meta`, and edge-verb counts

What changed

:   The packed node (pode) info dict is now keyed by an integer `nid` (Node ID) instead of the 2.x hex `iden`, gains a `meta` dictionary (e.g. created/updated time), and always includes `n1verbs` and `n2verbs` light-edge verb count dictionaries. The `links` trail entries are now `(nid, info)` tuples whose first element is an integer NID. Virtual property values appear under a `virts` key when `node:opts` `virts` is set.

Why

:   The packed node reflects the 3.x NID-based storage and the new edge-count and virtual-property model features.

What you need to do

:   Update any code that reads `pode[1]['iden']` to use `pode[1]['nid']` (an integer), and parse link trails as integer-NID-keyed tuples.

## Packed node values are envelopes

What changed

:   Each value within a packed node's `props`, `tags` and `tagprops` is now a two element envelope, `[<valu>, <info>]`, rather than a bare value or a `(typename, valu)` pair. The info dict carries a `t` type name, an `r` repr and a `v` dict of virtual property envelopes.

    This replaces four things at once. The top level `reprs` and `tagpropreprs`
    dictionaries are gone, and so are the flattened `<name>.type`,
    `<name>.<virt>` and `<name>.size` keys which used to sit alongside a
    property in `props`.

    The value of an array property is a list of member envelopes, since array
    members carry independent types.

    `Node.pack()` is also the interchange format for `.nodes` export and the
    `syn.nodes` feed, so a `.nodes` file exported by an earlier 3.0.0 build
    carries the old shape and must be re-exported.

Why

:   Everything else about a property was hung off keys which replicate the property name, or off a parallel dictionary keyed by it again. Adding any new per property fact meant inventing another sidecar. The envelope gives per value information one place to live, and lets a consumer index `[0]` and `[1]` unconditionally rather than inspecting the shape of a value to work out what it is holding.

What you need to do

:   Read a property value as `pode[1]['props'][name][0]` and its type as `[1].get('t')`. Read a repr from the envelope's `r` rather than from `reprs`, and a virtual property from the base property's `v` dict rather than from a `<name>.<virt>` sibling key. `synapse.lib.node.prop()` now returns the whole envelope. The packed format is stable across 3.x, so index it directly rather than reaching for an accessor.

    Re-export any `.nodes` files produced by an earlier 3.0.0 build.

    ``` python
    # 3.x packed node info dict
    {'nid': 1099511627992,
     'meta': {'created': 1662491423034000},
     'props': {'type': 'unicast'},
     'tags': {},
     'tagprops': {},
     'path': {},
     'n1verbs': {},
     'n2verbs': {}}
    ```

## `vars` name validation

What changed

:   `vars` keys must be strings, and the names `lib`, `node`, and `path` are reserved and rejected. Supplying a non-string key or one of the reserved names raises `BadArg`.

Why

:   The reserved names collide with the built-in `$lib`, `$node`, and `$path` Storm variables, so they can no longer be overridden via `vars`.

What you need to do

:   Rename any `vars` keys that use `lib`, `node`, or `path`, and ensure all keys are strings.
