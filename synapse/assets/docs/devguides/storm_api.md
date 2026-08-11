<a id="dev_storm_api"></a>


# Storm API Guide

<a id="dev_storm_apis"></a>


## Storm APIs

Storm is available over Telepath and HTTP API interfaces. Both interfaces require a Storm query string, and may take additional `opts` arguments.

### Telepath

There are three Storm APIs exposed via Telepath.

`storm(text, *, opts=None)`

:   The Storm API returns a message stream.

`callStorm(text, *, opts=None)`

:   The callStorm API returns a message given by the Storm `return( )` syntax.

`count(text, *, opts=None)`

:   The count API returns a count of the number of nodes which would have been emitted by running a given query. It can be found here [Cortex](../httpapi.md#http-api-cortex).

> [!NOTE]
> As of Synapse 3.0.0 the `opts` argument to these Telepath APIs (and to `reqValidStorm` / `isValidStorm`) is keyword-only: it must be passed as `opts=...` and can no longer be supplied positionally.

### HTTP API

The HTTP API versions of the Storm APIs can be found here [Cortex HTTP API](../httpapi.md#cortex).

`/v1/api/storm`

:   This API returns a message stream.

`/v1/api/storm/call`

:   This API returns a message given by the Storm `return( )` syntax.

`/v1/api/storm/export`

:   This API returns a stream of msgpack encoded data, which can be used as a <span class="title-ref">.nodes</span> file for later import.

<a id="dev_storm_message"></a>


## Message Types

The Telepath `storm()` and HTTP `api/v3/storm` APIs yield messages from the Storm runtime to the caller. These are the messages that may be seen when consuming the message stream.

Each message has the following basic structure:

``` text
[ "type", { ..type specific info... } ]
```

### init

First message sent by a Storm query runtime.

It includes the following keys:

task

:   The task identifier (which can be used for task cancellation).

tick

:   The epoch time the query execution started (in microseconds). This value is computed from the host time and may be affected by any changes in the host clock.

abstick

:   The relative time that the query execution started (in microseconds). This value is computed from a monotonic clock and can be used as a reference time.

text

:   The Storm query text.

hash

:   The md5sum of the Storm query text.

meta

:   The `meta` opt, echoed back verbatim. Present only when the `meta` opt was supplied.

Example:

``` text
('init',
 {'task': '8c90c67e37a30101a2f6a7dfb2fa0805',
  'text': '.created | limit 3',
  'hash': '2d16e12e80be53e0e79e7c7af9bda12b',
  'tick': 1539221678859})
```

### node

This represents a packed node. Each serialized node will have the following structure:

``` text
[
    [<form>, <valu>],       # The [ typename, typevalue ] definition of the node.
    {
        "nid": <int>,       # The node's integer Node ID (NID) within this Cortex.
        "meta": {},         # Node metadata (e.g. created/updated time).
        "tags": {},         # The tags on the node, as value envelopes.
        "props": {},        # The node's secondary properties, as value envelopes.
        "tagprops": {},     # The node's tag properties, as value envelopes.
        "path": {},         # Path-related information accumulated by the query.

        # always included
        "n1verbs": {}       # Counts of outbound light-edge verbs.
        "n2verbs": {}       # Counts of inbound light-edge verbs.

        # optional
        "nodedata": {}      # Node data carried along the path, when present.
        "repr": ...         # (node:opts repr) Presentation value for the node's own value.
        "virts": {}         # (node:opts virts) Virtual property values of the node's own value.
        "links": [...]      # (node:opts links) Pivot/edge link trail used to reach the node.
        "storage": [...]    # (node:opts storage) Per-layer storage breakdown.
        "embeds": {}        # (node:opts embeds) Embedded props from related nodes.
    }
]
```

#### Value envelopes

Each value within `props`, `tags` and `tagprops` is a two element **envelope**:

``` text
[<valu>, <info>]
```

The two element envelope is invariant; the keys of the info dict are not. Index
`[0]` and `[1]` unconditionally, and never inspect lengths or element types to
decide what you are holding.

The reserved info keys are:

`t`

:   The concrete type name of the value.

`r`

:   A human readable rendering of the value, produced by `node:opts` `repr`.

`v`

:   Virtual property values, as `{name: [<valu>, <info>]}`, produced by `node:opts` `virts`.

Model derived names never appear at the top level of an info dict; they appear
only as keys within `v`. New keys are registered in the `Node.pack()` docstring.

`t` is packed only where the concrete type is carried by the data rather than
derivable from the model. It is present on a scalar property and on each array
member, whose types vary per value, and absent on an array container, a tag and
a tag property.

The value of an array property is a list of member envelopes, so envelope
nesting is bounded at one level: a member is always a scalar envelope, never
another array.

An array container's `r` is never suppressed, even when it matches the member
values. It is the only thing which lets a consumer without the data model render
an array without inspecting the shape of the value. A scalar `r` and a member `r`
are still omitted when they match the value.

An embed is packed exactly like a property on the node it was walked to, so one
reader serves both.

> [!NOTE]
> In Synapse 3.0.0 the packed node is keyed by an integer `nid` (Node ID) rather than the 2.x hex `iden`, gains a `meta` dictionary, and always includes `n1verbs` / `n2verbs` light-edge verb counts. Property, tag and tag property values are envelopes rather than bare values; the `reprs` and `tagpropreprs` dictionaries and the flattened `<name>.type`, `<name>.<virt>` and `<name>.size` keys they replace are gone. The `repr`, `links`, `virts`, and `storage` keys are produced by the `node:opts` option (see [Storm Opts](storm_api.md#dev_storm_opts)).
>
> Runtime-only nodes (`syn:form`, `syn:prop`, and the other `syn:` runt forms) are packed from a fixed property dictionary and carry none of the `nid`, `meta`, `n1verbs` or `n2verbs` keys, but their property values are envelopes like any other node's.

Example:

This example is simple - it does not include repr, virts, or link information:

``` text
('node',
 (('inet:fqdn', 'icon.torrentart.com'),
  {'nid': 1099511627992,
   'meta': {'created': 1526590932444000},
   'props': {'domain': ('torrentart.com', {'t': 'inet:fqdn'}),
             'host': ('icon', {'t': 'str:lower'}),
             'issuffix': (0, {'t': 'bool'}),
             'iszone': (0, {'t': 'bool'}),
             'zone': ('torrentart.com', {'t': 'inet:fqdn'})},
   'tags': {'aka': ((None, None, None), {}),
            'aka.beep': ((None, None, None), {})},
   'path': {},
   'n1verbs': {},
   'n2verbs': {}}))
```

For repr information, see the examples in the opts documentation [Storm Opts](storm_api.md#dev_storm_opts).

### ping

A keepalive message. This is sent periodically when the `keepalive` options is set. See [Storm Opts](storm_api.md#dev_storm_opts) for more information.

### print

The print event contains a message intended to be displayed to the caller.

It includes the following key:

mesg

:   The message to be displayed to the user.

Example:

``` text
(print, {'mesg': 'I am a message!'})
```

This can be produced by users with the `$lib.print()` Storm API.

### warn

The warn event contains data about issues encountered when performing an action.

It includes the following keys:

mesg

:   The message to be displayed to the user.

The warn event may contain additional, arbitrary keys in it.

Example:

``` text
('warn',
 {'mesg': 'Unable to foo the bar.com domain',
  'domain': 'bar.com'})
```

This can be produced by users with the `$lib.warn()` Storm API.

### err

The err event is sent if there is a fatal error encountered when executing a Storm query. There will be no further processing; only a `fini` message sent afterwards.

The err event does contain a marshalled exception in it. This contains the exception type as the identifier; and several attributes from the exception.

The following keys are usually present in the marshalled information:

esrc

:   Source line that raised the exception.

efile

:   File that the exception was raised from.

eline

:   Line number from the raising file.

ename

:   Name of the function where the exception was from.

mesg

:   The `mesg` argument to a SynErr exception, if present; or the `str()` exception.

Additional keys may also be present, depending on the exception that was raised.

Example:

``` text
('err',
 ('BadTypeValu',
  {'efile': 'inet.py',
   'eline': 294,
   'form': 'inet:fqdn',
   'mesg': 'FQDN failed to match fqdnre [^[\\w._-]+$]',
   'name': 'inet:fqdn',
   'valu': '1234@#'}))
```

### fini

The last message sent by a Storm query runtime. This can be used as a key to stop processing messages or finalize any sort of rollup of messages.

It includes the following keys:

tock

:   The epoch time the query execution finished (in microseconds). This value is computed from adding the `took` value to the `tick` value from the `init` message.

took

:   The amount of time it took for the query to execute (in microseconds). This value is computed from the `abstick` and `abstock` values.

abstock

:   The relative time that the query execution finished at (in microseconds). This value is computed from a monotonic clock and should always be equal to or greater than the `abstick` value from the `init` message.

count

:   The number of nodes yielded by the runtime.

nexsoffs

:   The Cortex nexus offset once the query finished. Pass this as the `nexsoffs` opt of a subsequent query to keep a read behind a write, which is what makes read-your-writes work against a mirror or a read pool worker.

Example:

``` text
('fini', {'count': 1, 'tock': 1539221715240000, 'took': 36381000, 'nexsoffs': 7759195})
```

> [!NOTE]
> If the Storm runtime is cancelled for some reason, there will be no `err` or `fini` messages sent. This is because the task cancellation may tear down the channel and we would have an async task blocking on attempting to send data to a closed channel.

### edits

The `edits` message represents changes that are occurring to the underlying graph, as a result of running a Storm query.

It includes the following keys:

edits

:   A list of changes made to a set of nodes.

time

:   The epoch time the edits were committed (in microseconds), or `None` when the caller did not supply one.

Example:

``` text
# Nodeedits produced by the following query: [(inet:ip=1.2.3.4 :asn=1)]

('edits',
 {'edits': (('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
             'inet:ip',
             ((0, ((4, 16909060), 26), ()),
              (2, ('.created', 1662578208195, None, 21), ()),
              (2, ('type', 'unicast', None, 1), ()))),)})
('edits',
 {'edits': (('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
             'inet:ip',
             ((2, ('asn', 1, None, 9), ()),)),
            ('371bfbcd479fec0582d55e8cf1011c91c97f306cf66ceea994ac9c37e475a537',
             'inet:asn',
             ((0, (1, 9), ()),
              (2, ('.created', 1662578208196, None, 21), ()))))})
```

### storm:fire

The `storm:fire` message is a arbitrary user created message produced by the `$lib.fire()` Storm API. It includes the following keys:

type

:   The type of the event.

data

:   User provided data.

Example:

``` text
# The following query produces an event
$l = ((1), (2), (3)) $lib.fire('demo', key=valu, somelist=$l)

# The event produced.
('storm:fire', {'data': {'key': 'valu', 'somelist': (1, 2, 3)}, 'type': 'demo'})
```

### look:miss

The `look:miss` message is sent when the Storm runtime is set to `lookup` mode and the node that was identified by the scrape logic is not present in the current View.

It includes the following key:

ndef

:   A tuple of the form and normalized value.

Example:

``` text
('look:miss', {'ndef': ('inet:fqdn', 'hehe.com')})

# The ip value is presented in system mode.
('look:miss', {'ndef': ('inet:ip', (4, 16909060))})
```

### csv:row

The `csv:row` message is sent by the Storm runtime by the `$lib.csv.emit()` Storm API.

It includes the following keys:

row

:   A list of elements that make up the row.

table

:   A optional table name. This may be `None`.

Example:

``` text
# This query produces the following event: $lib.csv.emit(foo, bar, $lib.time.now())
('csv:row', {'row': ('foo', 'bar', 1662578057658), 'table': None})

# This query produces the following event: $lib.csv.emit(foo, bar, $lib.time.now(), table=foo)
('csv:row', {'row': ('foo', 'bar', 1662578059282), 'table': 'foo'})
```

<a id="dev_storm_call"></a>


## Storm Call APIs

The Telepath `callStorm()` and HTTP API `storm/call` interfaces are designed to return a single message to the caller, as opposed to a stream of messages. This is done using the Storm `return( )` syntax. Common uses for the call interfaces include getting and setting values where the full message stream would not be useful.

Example:

> The following example shows retrieving a user definition.
>
> ``` python3
> # Prox is assumed to be a Telepath proxy to a Cortex.
> >>> text = '$user = $lib.auth.users.byname($name) return ( $user )'
> >>> opts = {'vars': {'name': 'root'}}
> >>> ret = prox.callStorm(text, opts=opts)
> >>> pprint(ret)
> {'admin': True,
>  'archived': False,
>  'authgates': {'0b942d5f4309d70e5fa64423714e25aa': {'admin': True},
>                'cdf6f1727da73dbac95e295e5d258847': {'admin': True}},
>  'email': None,
>  'iden': '933a320b7ce8134ba5abd93aa487e1b5',
>  'locked': False,
>  'name': 'root',
>  'roles': (),
>  'rules': (),
>  'type': 'user'}
> ```
>
> The following shows setting an API key for a Power-Up. There is no `return` statement, so the return value defaults to None.
>
> ``` python3
> # Prox is assumed to be a Telepath proxy to a Cortex.
> >>> text = 'foobar.setup.apikey $apikey'
> >>> opts = {'vars': {'apikey': 'secretKey'}}
> >>> ret = prox.callStorm(text, opts=opts)
> >>> print(ret)
> None
> ```

<a id="dev_storm_opts"></a>


## Storm Opts

All Storm API endpoints take an `opts` argument. This is a dictionary that contains metadata that is used by the Storm runtime for various purposes. Examples are given using Python syntax.

The `opts` dictionary is validated against a JSON schema (`synapse.lib.schemas.stormOptsSchema`) on every Storm call. Only the keys documented below are accepted; an undeclared key raises a `SchemaViolation` rather than being silently ignored, so a misspelled opt fails loudly at the call rather than quietly doing nothing.

### debug

If this is set to True, the Storm runtime will be created with `$lib.debug` set to True.

Example:

> ``` python3
> opts = {'debug': True}
> ```

### graph

Apply a subgraph projection to the query results. The value may be `True` (use the default projection rules), the name of a stored graph projection, or a rules dictionary. When set, the runtime also emits the nodes reachable via the projection rules rather than only the lifted nodes.

Example:

> ``` python3
> opts = {'graph': True}
> ```

### nids

This is a list of integer Node IDs (NIDs) to use as initial input to the Storm runtime. Each value must be an integer NID (a `BadTypeValu` is raised otherwise); the corresponding nodes are used as input after any `ndefs` are lifted, but prior to regular lift operations which may start a Storm query.

> [!NOTE]
> This replaces the 2.x `idens` option, which took hex `iden` (BUID) hashes. The 3.x storage format keys nodes by integer NID, so initial input is now seeded with `nids`; the `idens` option is no longer supported.

Example:

> ``` python3
> nids = (1099511627992, 1099511628010)
> opts = {'nids': nids}
> ```

### keepalive

This is the period ( in seconds ) in which to send a `ping` message from a Storm query which is streaming results, such as the Telepath `.storm()` API or the HTTP `/v1/api/storm` API endpoint. This may be used with long-running Storm queries when behind a network proxy or load balancer which may terminate idle connections.

The keepalive value must be greater than zero.

Example:

> ``` python3
> keepalive = 2  # Send a keepalive message every 2 seconds
> opts = {'keepalive': keepalive}
> ```

### limit

Limit the total number of nodes that the Storm runtime produces. When this number is reached, the runtime will be stopped.

Example:

> ``` python3
> opts = {'limit': 100}
> ```

### meta

An arbitrary dictionary of caller defined metadata. The Cortex does not interpret it. It is echoed back verbatim as the `meta` key of the `init` message, which lets a caller correlate a message stream with its own per-query state without inventing Storm opts for it, and it is recorded on the Storm query log entry when the `storm:log` configuration is enabled.

The key is omitted from the `init` message entirely when the opt is not set.

> [!NOTE]
> Because `meta` is written to the query log, it is not a place for secrets. Use `vars` for those; `vars` values are never logged.

It is recorded as a nested `meta` key of the log record's `params` rather than merged into it, so a caller cannot supply a field which would read as the Cortex's own.

Example:

> ``` python3
> opts = {'meta': {'jobid': '5a5b1f0d1e4f4c0a', 'source': 'nightly-ingest'}}
> ```

### mode

This is the mode that a Storm query is parsed in. Specifying `lookup` mode enables unified text input that combines scraping, lifting, and datamodel hint-based lookups.

Example:

> ``` python3
> # Using lookup mode, the query text (before an optional | pipe to return to storm mode) is scraped
> # for typed values such as FQDNs, IP Addresses, and Hashes and an attempt is made to lift
> # any matching nodes. A look:miss message is fired for any scraped value that is not found
> # in the current View. Any text that remains after scraping is matched against forms and
> # properties that define lookup mode hints in the data model (via the modes.lookup info key),
> # using the comparator specified by each hint (e.g. ^= for prefix matching).
> opts = {'mode': 'lookup'}
> ```

### ndefs

This is a list of form and value tuples to use as initial input to the Storm runtime. These are expected to be the already normalized, system mode, values for the nodes. These nodes are lifted before any other lift operators are run.

Example:

> ``` python3
> ndefs = (
>     ('inet:fqdn', 'com'),
>     ('inet:ip', (4, 134744072)),
> )
>
> opts = {'ndefs': ndefs}
> ```

### nexus

Hold the query until the Cortex reaches a Nexus offset. This is how a caller keeps a read behind its own write when a mirror or a read pool worker might serve it. The recognized sub-keys are:

`offset` (int)

:   The Nexus offset to wait for. Take it from the `nexsoffs` key of a previous query's `fini` message.

`timeout` (number)

:   How long to wait, in seconds. A `TimeOut` is raised if the offset is not reached in time. Waits indefinitely when not set.

Example:

> ``` python3
> # ...having taken offs from the fini message of the write which preceded this read
> opts = {'nexus': {'offset': offs, 'timeout': 30}}
> ```

### readpool

Synapse Enterprise only. If a read pool is configured, setting this to `false` pins the query to the leader rather than allowing it to be handed off to a read pool worker. The open source Cortex accepts the option and ignores it.

Example:

> ``` python3
> opts = {'readpool': False}
> ```

### readonly

Run the Storm query in a readonly mode. This prevents editing the graph data, and only allows a small subset of whitelisted Storm library functions to be used.

Examples:

> ``` python3
> opts = {'readonly': True}
> ```

### node:opts

A nested dictionary that controls how each node is packed in the output message stream. In Synapse 3.0.0 this replaces the 2.x top-level `repr`, `links`, and `show:storage` node-output options; those top-level keys are rejected by the 3.x runtime. The recognized sub-keys are:

`repr` (bool, default `False`)

:   Populate human-friendly representations of system mode values. When set, the node gains a `repr` key for its own value, and each property, tag and tag property envelope gains an `r` key. A scalar `r` is omitted when it matches the value; an array container's `r` is always populated. There is no longer a `reprs` or `tagpropreprs` dictionary.

`links` (bool, default `False`)

:   Include a `links` key on each packed node: an ordered list of `(nid, info)` tuples describing the pivot or edge-walk steps used to reach the node. Note the first element of each entry is now an integer NID (it was a hex iden in 2.x).

`embeds` (dict, default `None`)

:   A mapping of `{form: {nodepath: (relprop, ...)}}` requesting embedded property values from related nodes, added under an `embeds` key on the packed node. Each `nodepath` is a `::` delimited chain of form-typed properties to walk from the yielded node, and each `relprop` is a property to read off the node that chain arrives at.

    ``` python3
    # embed the ASN number and registrant name of an inet:ip node's :asn
    opts = {'node:opts': {'embeds': {'inet:ip': {'asn': ('registrant:name',)}}}}
    ```

`virts` (bool, default `False`)

:   Include virtual property values. The node gains a `virts` key for its own value, and each property envelope which has virts gains a `v` key mapping the virt name to its own envelope. Virtual properties are no longer flattened into `props` as `<name>.<virt>` sibling keys, and the `<name>.type` and `<name>.size` keys they came with are gone -- the type is on the envelope as `t`, and an array's size is `v.size`.

`storage` (bool, default `False`)

:   Include a `storage` key containing a raw breakdown of the storage nodes for each yielded node, which can be used to determine which parts of the node are stored in which layer within the view.

Example:

``` python3
# Request reprs and virtual properties.
opts = {'node:opts': {'repr': True, 'virts': True}}

# A Storm node message with reprs and virts added to it (note the integer nid).
# ':version' carries an 'r' because its repr differs from the stored value,
# while ':type' does not, since 'unicast' reprs to itself.
('node',
 (('inet:ip', (4, 134744072)),
  {'nid': 1099511627992,
   'meta': {'created': 1662491423034000},
   'props': {'version': (4, {'t': 'inet:ipversion', 'r': '4'}),
             'type': ('unicast', {'t': 'str:lower'})},
   'tags': {},
   'tagprops': {},
   'path': {},
   'n1verbs': {},
   'n2verbs': {},
   'repr': '8.8.8.8',
   'virts': {}}))
```

### show

A list of message types to include in the output message stream. Every message type is filtered by this option, including `init`, `fini`, and `err`.

If the option is not set the full message stream is sent. If it is set, only the types it names are sent, so an empty list sends nothing at all. A named type installs a handler for just that type, so anything unlisted is never queued rather than being filtered after the fact.

> [!NOTE]
> `err` is filtered like any other message type, so a `show` list which omits it silently discards query errors. Include `err` unless dropping them is what you intend.

Example:

> ``` python3
> # Only node and warn messages.
> opts = {'show': ['node', 'warn']}
>
> # Nodes without the edits which produced them, still reporting errors.
> opts = {'show': ['node', 'err']}
>
> # Consume no messages at all.
> opts = {'show': []}
> ```

### hide

A list of message types to remove from the output message stream. This is the inverse of `show`: every type is sent except the ones it names.

If the option is not set, or is set to an empty list, nothing is hidden. Unlike `show`, a hidden type is filtered as it is relayed rather than never queued.

`show` and `hide` are mutually exclusive -- setting both raises a `BadArg`. Use `show` when you know the full set of types you want, and `hide` when you want everything except a few.

> [!NOTE]
> `err` is hidden like any other message type, so a `hide` list which names it silently discards query errors.

Example:

> ``` python3
> # Everything except the edits which produced the nodes.
> opts = {'hide': ['edits']}
>
> # Drop the bookkeeping messages, keeping nodes, output, and errors.
> opts = {'hide': ['init', 'fini']}
> ```

### sudo

A boolean option which attempts to invoke the Storm runtime as a global admin. This option requires the user or one of their roles to allow the `storm.sudo` permission.

Example:

> ``` python3
> opts = {'sudo': True}
> ```

### task

A user provided guid that is used as the task identifier for the Storm runtime. This allows a user to have a predictable identifier that they can use for task cancellation.

A caller is given the iden it asked for or an error, never a different one. The Storm runtime will raise a `BadArg` if the `task` iden is already associated with a currently running task, or if the runtime is already promoted under a different iden (which is the case for a nested runtime, such as one started by `$lib.storm.run()`).

Example:

> ``` python3
> # Generate a guid on the client side and provide it to the Cortex
> import synapse.common as s_commmon
> task_iden = s_common.guid()
> opts = {'task': task_iden}
> ```

### user

The User iden to run the Storm query as. This allows a global admin to run a Storm query as another user.

Example:

> ``` python3
> opts = {'user': 6e9c8de2f1aa39fee11c19d0974e0917}
> ```

### vars

A dictionary of key - value pairs that are mapped into the Storm runtime as variables. Some uses of this include providing data to the runtime that is used with an ingest script, or to provide secrets to the Storm runtime so that they will not be logged.

Example:

> ``` python3
> # A secret key - A good example of this is configuring a Rapid Power-Up.
> vars = {'secretkey': 'c8de2fe11c19d0974e091aa39fe176e9'}
> opts = {'vars': vars}
>
> # Some example data that could be used in a Storm ingest script.
> records = (
>     ('foobar.com', '8.8.8.8', '20210810'),
>     ('bazplace.net', '1.2.3.4', '20210810'),
> )
> vars = {'records': records}
> opts = {'vars': vars}
> ```

> [!NOTE]
> Variable names must be strings, and the names `lib`, `node`, and `path` are reserved and may not be used as `vars` keys (a `BadArg` is raised otherwise).

### view

The View iden in which to run the Storm query in. If not specified, the query will run in the user's default view.

Example:

> ``` python3
> opts = {'view': 31ded629eea3c7221be0a61695862952}
> ```
