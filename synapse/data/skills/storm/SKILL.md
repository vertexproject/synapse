---
name: storm
description: >-
  Reference for the Storm query language used by the Synapse Cortex: lifting,
  filtering, pivoting and traversal, editing nodes, tags, variables and types,
  control flow, functions, commands, and libraries. Use when composing, validating,
  debugging, or explaining Storm queries.
---

# Storm Query Language Skill

TRIGGER: When writing, editing, reviewing, validating, debugging, or running Storm (.storm) files, Storm queries, Storm packages, or Synapse query language code. Also triggered when fixing BadSyntax exceptions, troubleshooting Storm parse errors, or running Storm queries against a Cortex.

## Language Overview

Storm is an async pipeline-based graph query language for Synapse. Queries are chains of operations and commands that transform streams of `(node, path)` tuples lazily. Storm files use `/* */` and `//` comments. Inline commands must end with `|` to return to storm operator syntax.

## Validating and Running Storm

**IMPORTANT: Claude MUST validate ALL Storm query logic it generates using the MCP tools below. Every Storm query written to a file, embedded in a test, or included in a Storm package MUST be validated before being considered complete. No exceptions.**

### Validating Storm Syntax (Required)

The `storm_validate` MCP tool validates Storm syntax without executing the query. Always use it to check a query before running it.

- Argument: `query` (the Storm query text).
- Returns `{"valid": true}` when the syntax is valid, or `{"valid": false, "err": <ErrName>, "mesg": <details>}` when the query fails to parse.

**Workflow for validating generated Storm:**
1. Call `storm_validate` with the query text.
2. If `valid` is `false`, read `err` / `mesg` (which include line/column info), fix the query, and re-validate before proceeding.

### Running Storm Queries

The `storm` MCP tool runs a Storm query against the Cortex and returns a **page** of result messages: `{"messages": [(<type>, <info>), ...], "cursor": <str-or-null>}`. Each message is a `(<type>, <info>)` tuple as yielded by the Storm runtime (e.g. `node`, `print`, `warn`, `err`, `fini`).

**Each query must be fully drained or cancelled.** If `cursor` is non-null, the query produced more messages than one page and is still running on the server -- you MUST either call `storm_continue(cursor)` repeatedly until it returns a null cursor (fully drained), or call `storm_cancel(cursor)` to discard the rest. Never abandon a query with a non-null cursor: it holds a Storm runtime open on the server until it times out. A null cursor means the query is complete and nothing further is required.

The `call_storm` MCP tool runs a query and returns only the value from its `return()` statement (no pagination). Use it when the query is written as a single function-style query that returns one value.

`storm` and `call_storm` accept:
- `query` (required): the Storm query text.
- `opts` (optional): Storm query opts, e.g. `{"vars": {...}}`, `{"view": <iden>}`, or `{"limit": <n>}`. Setting `"view"` is important -- see [Selecting a View](#selecting-a-view).

`storm_continue` and `storm_cancel` take a single `cursor` argument. Queries run as the calling user and respect that user's permissions; the view is whatever `opts["view"]` specifies, else the user's default view.

**Use cases:**
- Verify that a query produces the expected nodes and output (`storm`).
- Retrieve a computed value from a function-style query (`call_storm`).
- Iteratively build up and query graph data across calls.
- Validate that Storm logic works end-to-end (not just syntax) before deploying it to a package.

### Selecting a View

A query always runs in exactly one view. There is no "active session view" -- the view is
chosen **per call** by setting `"view"` in the `opts` of `storm` / `call_storm`
(e.g. `opts={"view": "<iden>"}`). If `"view"` is omitted, the query runs in the calling
user's default view.

**Running a query in the wrong view can be VERY BAD** -- it can create, modify, or destroy
data in the wrong place. When you are not certain which view the user intends, do NOT guess:
call `view_list`, show the choices, and ask the user to confirm which view to use. Once
chosen, reuse that view iden in the `opts` of every subsequent `storm` / `call_storm` call.

View MCP tools:
- `view_list` -- list the views the user can read, as `{iden, name, parent}`. Take the
  `iden` of the intended view and pass it as `opts={"view": "<iden>"}` on later calls.
- `view_get` -- return the iden of the user's default view (the one used when `opts` omits a
  view).
- `view_fork` -- fork a view (defaults to the user's default view), creating a child view
  with its own writable top layer; returns the new fork's iden.
- `view_del` -- delete a view (its layers are not deleted).
- `view_merge` -- merge a forked view's changes down into its parent (the fork is not
  deleted; the view must be a fork without parent quorum voting).

**Developing ingest logic (do this for ANY node-editing work):** a `view_fork` followed by a
`view_del` is the safe way to test logic that edits nodes. `view_fork` a view to get a fork
iden, run the ingest by passing that iden as `opts={"view": "<fork-iden>"}` to the `storm`
tool, inspect the results, then `view_del` the fork to discard every change -- the underlying
data is never touched. Strongly prefer this workflow whenever developing or iterating on
ingest or other node-editing Storm. Use `view_merge` instead of `view_del` only once the logic
is verified and you want to keep the changes.

### Discovering the Data Model

Do not guess form or property names. Use:
- the `model_find` MCP tool to search the data model by regex (matched against the names and docs of forms, properties, types, and interfaces), or the `syn://model` MCP resource for the full Synapse data model (forms, properties, types, univs, tagprops, edges, interfaces);
- the `syn://model/form/{name}` MCP resource for a single form definition;
- the `syn://stormdocs` MCP resource for Storm library, type, and command documentation.

## Reading BadSyntax Errors

A `BadSyntax` exception (surfaced via `storm_validate` or an `err` message) contains:
- **`mesg`**: Human-readable error (e.g. `"Unexpected token 'and' at line 3, column 5, expecting one of: ..."`)
- **`line`** / **`column`**: Location in the query text
- **`token`**: The unexpected token value
- **`at`**: Character offset in query text
- **`highlight`**: Dict with `hash`, `lines`, `columns`, `offsets` for precise source mapping

The parser converts raw Lark token names into friendly English descriptions in its error messages.

## Syntax Quick Reference

### Lifting (Select Nodes)

```storm
inet:fqdn                          // all nodes of a form
inet:fqdn=example.com              // by primary value
inet:fqdn:zone=1                   // by property value
inet:fqdn:zone                     // where property is set
#tag.name                          // by tag
inet:fqdn#tag.name                 // by form with tag
entity:contact:names*[=example]    // by array contents
reverse(inet:fqdn)                 // reverse lift order
```

Comparison operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `~=` (regex), `^=` (prefix), `@=` (time/interval)

### Filtering

```storm
+#tag.name                        // keep nodes with tag
-:prop=value                      // remove matching nodes
+{ -> inet:ipv4 +:asn=1234 }      // subquery filter (keep)
-{ -> inet:ipv4 }                 // subquery filter (remove)
+{ -> inet:dns:a } < 2            // subquery filter with count compare
+(:asn=1234 or :asn=5678)         // compound: and, or, not
+$(:client:txbytes >= 100)        // expression filter (keep)
-$($fqdns.size() > 1)             // expression filter (remove)
+:asn::name=woot                  // embed filter syntax using ::
```

### Pivoting (Graph Traversal)

```storm
-> *                               // pivot to all referenced nodes
-> inet:ipv4                       // pivot to specific form
-> (inet:ipv4, inet:ipv6)          // pivot to multiple forms
<- *                               // reverse pivot (incoming refs)
-+> *                              // join pivot (keep source + targets)
-> { subquery }                    // raw pivot via subquery
:ipv4 -> inet:ipv4                 // property-based pivot

// Light edge traversal
-(refs)> *                         // walk N1 edges (outbound)
<(refs)- *                         // walk N2 edges (inbound)
--> *                              // N-walk (multi-hop)
<-- *                              // reverse N-walk

// Edge join pivots (keep source + targets)
-(refs)+> *                        // N1 edge join pivot
<+(refs)- *                        // N2 edge join pivot
--+> *                             // N-walk join
<+-- *                             // reverse N-walk join
```

### Edit Blocks `[ ]`

```storm
// Node creation
[ inet:fqdn=example.com ]                    // create node
[ inet:fqdn?=example.com ]                   // try-create (ignore errors)

// Property modification
[ :asn=1234 ]                                // set property
[ :tags += newval ]                           // add to array (+=)
[ :tags -= oldval ]                           // remove from array (-=)
[ :tags ++= $list ]                           // add multiple (++=)
[ :tags --= $list ]                           // remove multiple (--=)
[ -:asn ]                                     // delete property
[ :prop ?= value ]                            // try-set (ignore type errors)
[ :prop*unset= value ]                        // set only if unset (conditional)
[ :prop={ foo:bar } ]                         // assign from a subquery (yields a node; its value is assigned)
[ :prop={[ foo:bar=baz ]} ]                   // the subquery may create the node to assign

// Tag operations
[ +#tag.name ]                                // add tag
[ +?#tag.name ]                               // try-add tag (ignore errors)
[ -#tag.name ]                                // remove tag
[ +#tag=(2023-01-01, 2024-01-01) ]           // tag with time interval
[ +#tag:confidence=80 ]                       // set tag property
[ -#tag:confidence ]                          // delete tag property
[ +?#$tags ]                                  // add tags from variable

// Light edge operations
[ +(refs)> { inet:ipv4=1.2.3.4 } ]          // add edge via subquery
[ -(refs)> { inet:ipv4=1.2.3.4 } ]          // remove edge via subquery
[ <(seen)+ $srcnode ]                         // add N2 edge to variable
// a subquery that returns no nodes (or a $srcnode of (null)) is valid and makes no changes

// Parenthesized edit context only edits nodes created in the same parens context
// All other nodes in the pipeline are not affected
[( risk:vuln=($vendor, $id)
    :name=Woot          // Only edits name on the risk:vuln
    <(seen)+ $srcnode   // Only adds the edge to the risk:vuln
)]
```

### Variables & Expressions

```storm
$x = 42                                      // assignment
$name = :prop                                // from node property
($a, $b) = $tuple                            // tuple unpacking
$obj.key = "value"                           // item assignment

// Arithmetic: +, -, *, /, %, **
$result = (($x + $y) * 2)

// Comparison: =, !=, <, >, <=, >=, ~=, ^=
$check = ($a > 5 and $b < 10)

// Logical: and, or, not
$match = ($str ~= "pattern")
```

**Operator precedence** (low->high): `or` -> `and` -> `not` -> comparisons -> `+/-` -> `*/%` -> unary `-` -> `**`

### Type Specific Behavior

#### Strings

```storm
inet:fqdn=example.com                        // unquoted (no spaces)
'literal string \n not escaped'              // single-quoted (raw)
"escaped string \n \t \\"                    // double-quoted (escapes)
'''raw multiline
string'''                                    // triple-quoted

`format string {$var} and {:prop}`           // backtick format string
`result: {$x + 1} name: {$node.repr()}`     // expressions in {}
```

#### Dicts

Dereference directly by key, assign by key, and iterate as `($name, $valu)` tuples. A key may
be given literally or via a variable:

```storm
$dict = ({"foo": "bar"})
$lib.print($dict.foo)                        // dereference a literal key -> bar
$dict.foo = baz                              // assign a literal key (creates or overwrites)

$key = foo
$lib.print($dict.$key)                       // dereference via a variable key -> baz
$dict.$key = heya                            // assign via a variable key

for ($name, $valu) in $dict {                // iterate key/value pairs
    $lib.print(`{$name}={$valu}`)
}
```

In a chained dereference, a `$`-prefixed element uses that variable's value as the key while a
bare element is a literal key. So `$foo.$bar.baz` reads `$foo` at the key held by `$bar`, then
reads the literal key `baz` from that result (i.e. `($foo[$bar])["baz"]`).

#### Lists / Arrays

Index directly (indexes are zero-based), and iterate:

```storm
$list = (["foo", "bar", "baz"])
$lib.print($list.2)                          // index directly, 0-based -> baz

for $item in $list {                         // iterate the items
    $lib.print($item)
}
```

#### Null

Dereferencing something that does not exist yields `(null)` (rather than raising):

```storm
$dict = ({"foo": "bar"})
$lib.print($dict.nope)                       // missing key -> (null)
```

Iterating over `(null)` safely produces zero iterations, so a guard is unnecessary -- a
`for` loop over a missing/`(null)` value simply does not run:

```storm
// no need to guard with `if $foo.bar { ... }` first
for $item in $foo.bar {                      // if $foo.bar is (null), this runs 0 times
    ...
}
```

#### Guids

A `guid` form has an opaque, randomly-distributed primary value. To create or deconflict one
from meaningful data, pass a dict (a guid constructor, aka a "gutor") whose keys are
secondary properties. Those properties both generate a stable guid -- repeating the same
dict resolves to the same node -- and are set on the node. This is especially valuable when
you need to **deconflict on multiple secondary properties** at once:

```storm
// deconflict a risk:threat on both :name and :reporter:name
[ risk:threat=({"name": "apt1", "reporter:name": "mandiant"}) ]
```

The deconfliction set is order-independent: the same keys/values always resolve to the same
node regardless of dict ordering.

Two reserved keys control the rest of the construction:

- `$props` -- a dict of additional properties to set that do NOT participate in
  deconfliction (they do not affect the generated guid):

```storm
[ risk:threat=({"name": "apt1", "reporter:name": "mandiant",
                "$props": {"desc": "A state-sponsored cyber espionage group."}}) ]
```

- `$try` -- when `(true)`, values in `$props` that fail type validation are skipped instead
  of raising; the node is still created with its valid properties:

```storm
[ risk:threat=({"name": "apt1", "reporter:name": "mandiant",
                "$try": (true), "$props": {"reporter:published": "not a date"}}) ]
// the node is created; the invalid reporter:published is simply not set
```

Properties declared with alternates (`alts`) are also consulted during the deconfliction
pass, so a deconf value will match an existing node even when that value is stored on one of
the property's alternate properties.

A guid form can also be generated from an **array of seed values**, producing a stable,
re-encounterable guid -- the same values always resolve to the same node. Unlike a gutor
dict, the seed values are NOT stored as properties; they only determine the guid:

```storm
// the same (vendor, id) tuple always resolves to the same node
[ foo:bar=(acme, $foo.id) ]
```

Use an array seed when a node is uniquely identified by a fixed set of positional inputs;
use a gutor dict when you want to deconflict on (and record) named secondary properties.

#### Times

A `time` property holds a single date/time. Time values accept flexible input: lower-resolution
dates, wildcards, the `now` keyword, and relative offsets.

```storm
:time=2023/05/03                             // lower-resolution date
:time="2023/05/03 21:09:04.000"              // full precision (quote when it has spaces)
:time=2023/05*                               // wildcard
:time=now                                    // the "now" keyword
:time="-3 days"                              // relative to now
```

The `@=` comparator compares a time property against a single time or an interval `(min, max)`.
An interval is min-inclusive and max-exclusive (`>= min and < max`):

```storm
inet:dns:request:time@=2023/05/03            // a single time is an exact match (same as =)
inet:dns:request:time@=(2023/05/03, 2023/05/04)  // time falls within [min, max)
.created@=(now, "-7 days")                   // created within the past 7 days
```

#### Intervals (ival)

An `ival` property holds a `(min, max)` time window -- e.g. the universal `.seen` property or a
tag's timestamps. Set it with a two-element `(min, max)` tuple:

```storm
[ inet:dns:a=(woot.com, 1.2.3.4) .seen=(2021/09/12, 2023/08/08) ]
[ inet:fqdn=woot.com +#cno.threat.t20=(2020/01/01, 2020/06/01) ]   // a tag time window
```

The `@=` comparator compares an interval property against a single time (matches when the time
falls within the property's window) or another interval (matches on ANY overlap):

```storm
inet:dns:a.seen@=2022/07/15                  // a time within the .seen window
inet:dns:a.seen@=(2022/07/01, 2022/08/01)    // any overlap with the .seen window
#cno.threat.t20@=(2020, 2021)                // lift by overlapping tag timestamps
inet:fqdn#cno.threat.t20@=2020/03/01         // filter/lift by a time within tag timestamps
```

Time keywords (`now`) and relative offsets (`"-1 day"`, `"+30 days"`) may be used as interval
bounds, e.g. `(now, "-1 day")`.

### Control Flow

```storm
// If/elif/else
if $condition { ... }
elif $other { ... }
else { ... }

// For loop (with optional tuple unpacking)
for $item in $list { ... }
for ($key, $val) in $dict { ... }

// While loop
while $condition { ... }

// Switch/case
switch $var {
    "val1": { ... }
    "val2": { ... }
    ("val3", "val4"): { ... }                // multi-value case
    *: { ... }                                // default
}

// Try/catch (catches SynErr exceptions)
try {
    ...
} catch BadArg as $err {
    ...
} catch (AuthDeny, NoSuchName) as $err {     // multi-exception catch
    ...
} catch * as $err {                           // catch all
    ...
}

// Flow control
break                                         // exit loop
continue                                      // next iteration
return($value)                                // return from function
stop                                          // terminate an emitter function
emit $value                                   // emit data to caller
```

**Prefer the pipeline over control flow.** Control flow logic (`if`/`elif`/`else`,
`switch`, `for`, `while`) should ONLY be used when the work cannot be expressed with inline
Storm pipeline operations or subquery filters. Storm authors should strongly prefer inline
pipe operations -- filters, subqueries, and conditional edits -- over control flow, because
they run per-node, read more clearly, and stay lazy. Reach for `if`/`switch`/`for` only when
no pipeline/subquery filter can do the job.

```storm
// AVOID -- control flow operating on node properties
if $node.props.foo { $node.props.baz=faz }

// PREFER -- a subquery filter plus a conditional edit in the pipeline
{ +:foo [ :baz=faz ] }
```

The subquery `{ +:foo [ :baz=faz ] }` keeps only nodes that have `:foo` set and edits
`:baz` on them, without removing the other nodes from the outer pipeline.

**Wrap loops that run with nodes in the pipeline.** A `for`/`while` loop runs its body once
per loop iteration for each inbound node, so the loop re-emits each inbound node and the
output count becomes `node_count * iteration_count` (e.g. 2 nodes x a 3-item loop yields 6).
To run a loop without polluting the outer pipeline with these duplicates, wrap it in a
subquery -- `{ for $foo in $bar { ... } }` -- which executes the loop (including any edits or
side effects) but isolates the outer pipeline, leaving the inbound nodes unchanged.

```storm
// AVOID -- multiplies the pipeline: 2 inbound nodes x 3 iterations = 6 nodes out
inet:ipv4 for $i in (1, 2, 3) { $lib.print($i) }

// PREFER -- the loop still runs, but the outer pipeline still has just the 2 inbound nodes
inet:ipv4 { for $i in (1, 2, 3) { $lib.print($i) } }
```

### Functions

```storm
// Callable functions must have a return() statement
function myFunc(arg1, arg2=(null)) {
    // own pipeline scope
    return($result)
}

// Invocation
$result = $myFunc(val1, arg2=val2)

// Emitter functions use the emit / stop keywords to act like a generator
function getData() {
    for $item in $getStuff() {
        emit $item
        if ($item.foo = "bar") { stop }
    }
}

// Invocation must iterate over the results
for $item in $getData() {
    $lib.print($item)
}

// Functions without a return() or emit yield nodes from their pipeline
function getNodes(valu) {
    form:prop=$valu +#tag.name
}

// Invocation yielding the results into the current pipeline
yield $getNodes(valu)

// Invocation may iterate over the results
for $n in $getNodes() {
    $lib.print($n)
}

```

### Subqueries

```storm
// As node reference in edits
[ :account = { [ syn:user=$lib.auth.users.get().iden ] } ]

// Embedded query expression
$file = { [ file:bytes=$sha256 ] }

// Perform operations after pivots or filters without effecting the outer pipeline
inet:fqdn { -> inet:dns:a [ +#reviewed ] } // still has inet:fqdn nodes in the pipeline
```

### Lifecycle Blocks

```storm
init { ... }                                  // runs once before any nodes are allowed through the pipeline
empty { ... }                                 // runs if pipeline is empty
fini { ... }                                  // runs once after all nodes have passed through the pipeline
```

### Built-in Commands

```storm
limit 10                                      // limit output count
count                                         // count nodes
uniq                                          // deduplicate
spin                                          // consume without output
max :prop                                     // keep max by property
min :prop                                     // keep min by property
tee { query1 } { query2 }                   // branch pipeline
once                                          // deduplicate per-query
delnode                                       // delete nodes
movetag old.tag new.tag                      // rename tags
help [command]                                // show help
iden $iden                                    // lift node by iden
background { query }                         // run query in background
batch --size 100 { query }                   // batch pipeline processing
copyto $layer                                // copy nodes to layer
diff                                          // yield added/changed nodes
edges.del                                     // delete light edges
merge --apply                                // merge layer changes
movenodes --srclayer $src --destlayer $dst   // move nodes between layers
parallel { query }                           // parallel execution
runas --user $user { query }                 // run as another user
scrape --refs $text                          // scrape indicators
sleep $seconds                               // pause execution
tag.prune #tag                               // prune tag tree
tree { query }                               // recursive traversal
view.exec $view { query }                   // execute in view
```

Any Storm command can be safely run with `--help` to print its usage/help output without
executing it (e.g. `scrape --help`), which is the reliable way to discover a command's
arguments and options.

### Key $lib Functions

```storm
// Core
$lib.import(module.name)                     // import Storm module
$lib.print(`message {$var}`)                 // output message
$lib.warn("warning text")                    // output warning
$lib.raise(ErrName, "message")               // raise exception
$lib.exit("fatal message")                   // exit with error
$lib.debug = (true)                          // enable debug mode
$lib.pprint($data)                           // pretty-print data

// Type operations
$lib.trycast(typename, $value)               // returns ($ok, $valu)
$lib.cast(typename, $value)                  // cast or raise
$lib.vars.type($value)                       // get type name string
$lib.len($collection)                        // length
$lib.sorted($list)                           // sort

// Time
$lib.time.now()                              // current timestamp
$lib.time.format($time, "%Y-%m-%d")          // format timestamp
$lib.time.sleep($seconds)                    // sleep

// Data structures
$lib.dict.keys($dict)                        // dict keys
$lib.dict.has($dict, $key)                   // check key exists
$lib.guid(parts...)                          // generate GUID
$lib.tags.prefix($tags, $prefix)             // prefix tag list

// HTTP
$lib.inet.http.request($meth, $url,
    headers=$headers, params=$params, json=$json,
    ssl_verify=$ssl_verify, ssl_opts=$ssl_opts, proxy=$proxy)   // HTTP request
$resp.code                                    // response code
$resp.json()                                  // parse JSON body
$resp.headers                                 // response headers
$resp.reason                                  // status reason

// Axon (blob storage)
($size, $sha256) = $lib.axon.put($bytes)     // store bytes
$hashes = $lib.axon.hashset($sha256)         // get hash set

// Auth
$lib.auth.users.get().iden                   // current user iden
$lib.auth.users.get().vars.$key              // per-user variable
$lib.auth.users.get().allowed($perm)         // check permission
$lib.globals.get($key)                       // get a global variable
$lib.globals.set($key, $valu)                // set a global variable
$lib.auth.users.get($iden)                   // get user by iden
$lib.auth.users.byname($name)               // get user by name
$lib.auth.roles.byname($name)               // get role by name
$lib.auth.easyperm.confirm($obj, $lvl)       // check easyperm

// Model
$lib.model.form($formname)                   // get form object

// Vault
$lib.vault.add($name, $type, $scope, $owner, $secrets, $configs)
$lib.vault.bytype($type, scope=$scope)       // find vault by type
$lib.vault.byname($name)                     // find vault by name
$lib.vault.list()                            // list all vaults

// Package
$lib.pkg.get(package-name)                   // get package def
$lib.pkg.get(name).version                   // package version
$lib.pkg.get(name).vaults.$type.schemas      // vault schemas

// JSON
$lib.json.schema($schema).validate($data)    // returns ($ok, $result)
$lib.json.load($string)                      // parse JSON string
$lib.json.save($data)                        // serialize to JSON string

// Lift
$lib.lift.byNodeData($name)                  // lift nodes with a given nodedata key

// Version
$lib.version.synapse()                       // synapse version tuple
```

### Node Object Attributes / Methods

```storm
$node.form()                                 // form name string
$node.ndef()                                 // (form, value) tuple
$node.iden()                                 // node identity hash
$node.value()                                // primary value
$node.repr()                                 // human representation
$node.pack()                                 // pack node to dict
$node.props                                  // property dict access
$node.props.propname                         // specific property
$node.isform(inet:fqdn)                      // check form type
$node.tags()                                 // get tags dict
$node.difftags($tags)                        // diff tags vs current
$node.globtags(pattern)                      // match tags by glob
$node.edges()                                // iterate light edges
$node.addEdge($verb, $n2iden)                // add a light edge
$node.delEdge($verb, $n2iden)                // delete a light edge
$node.getByLayer()                           // get node per layer
$node.getStorNodes()                         // get storage nodes
$node.data.set("key", $value)                // set node data
$node.data.get("key")                        // get node data
$node.data.has("key")                        // check node data exists
```

## Common Syntax Errors & Fixes

### 1. Using `==` Instead of `=` for Comparison
```storm
// WRONG - Storm uses single = for comparison
if ($x == 5) { ... }

// CORRECT
if ($x = 5) { ... }
```

### 2. Missing Parentheses Around JSON expressions
```storm
// WRONG
$x = true
$y = 999    // WRONG because $y ends up being "999" not 999
$dict = {}
$list = []

// CORRECT
$x = (true)
$y = (999)
$dict = ({})
$list = ([])
```

### 3. Forgetting `|` After Inline Commands
```storm
// WRONG - command output stays in command syntax mode
inet:fqdn limit 10 +#tag

// CORRECT - pipe returns to Storm operator syntax
inet:fqdn limit 10 | +#tag
```

### 4. Unbalanced Brackets/Braces
```storm
// WRONG
[ inet:fqdn=example.com
  :zone=1

// CORRECT
[ inet:fqdn=example.com
  :zone=1
]
```

### 5. Wrong String Quoting
```storm
// WRONG - single quotes do NOT process escapes
$x = 'line\nnewline'    // literal \n

// CORRECT - use double quotes for escapes
$x = "line\nnewline"
```

### 6. Missing `$` on Variable References
```storm
// WRONG
for item in $list { ... }

// CORRECT
for $item in $list { ... }
```

### 7. Using `return` Without Parentheses
```storm
// WRONG
return $value

// CORRECT
return($value)
return()          // void return
```

### 8. Incorrect Switch/Case Syntax
```storm
// WRONG - missing colon after case value
switch $x {
    "val1" { ... }
}

// CORRECT
switch $x {
    "val1": { ... }
}
```

### 9. Wrong Comparison in Filter Context vs Expression Context
```storm
// Filter context uses direct comparison operators
+:asn=1234

// Expression context needs parenthesized comparison
if ($node.value = "test") { ... }
```

### 10. Incorrect `try`/`catch` Exception Names
```storm
// WRONG - using full exception class path
try { ... } catch s_exc.BadArg as $err { ... }

// CORRECT - use just the exception name (SynErr subclass name)
try { ... } catch BadArg as $err { ... }
try { ... } catch (AuthDeny, NoSuchName) as $err { ... }
try { ... } catch * as $err { ... }
```

### 11. Using `stop` vs `return()` Incorrectly
```storm
// stop - exits an emitter function
// return() - exits a callable function

function check00(n) {
    if ($fatal) { return() }   // exit function
    return(woot)                       // exit function returning "woot"
}

function check01(n) {
    for $x in $n {
        emit $x             // emit $x to the invoker
        if ($x = 'woot') {
            stop            // exit the emitter function
        }
    }
}
```

### 12. Format String Escaping
```storm
// WRONG - unescaped backtick or brace in format string
$msg = `literal brace: { causes error`

// CORRECT - escape literal backticks with \` and literal braces with \{
$msg = `literal brace: \{ not interpolated`
```

### 13. Edit Block Inside Filter
```storm
// WRONG - can't nest edit blocks in filters
+[ :prop=value ]

// CORRECT - separate filter and edit
+:prop=value
// or
[ :prop=value ]
```

### 14. Duplicate Keyword Arguments
```storm
// WRONG - parser catches duplicate kwargs
$func(arg1=1, arg1=2)

// CORRECT
$func(arg1=1, arg2=2)
```

### 15. Positional After Keyword Arguments
```storm
// WRONG
$func(key=1, "positional")

// CORRECT
$func("positional", key=1)
```

## Style Rules

- Use `/* */` block comments for module headers, `//` for inline comments
- Private/internal functions use `_` prefix: `function _helperFunc()`
- Double-underscore `__` prefix for module-internal variables and functions: they cannot be accessed from outside the module that defines them (e.g. `function __getJson()`)
- Module variables at top level: `$setup = $lib.import(...)`, `$srcnode = (null)`
- Format strings with backticks for interpolation: `` `text {$var}` ``
- Parenthesize values and conditions so Storm evaluates them as typed expressions rather than bare strings or edit syntax: `(true)` / `(false)` / `(null)` (not `$lib.true` / `$lib.false` / `$lib.null`), numbers `(42)`, collections `([])` / `({})`, and comparisons like `if ($a = null)`
- Use `$lib.raise(ErrName, "message")` for errors, `$lib.exit("message")` for fatal exits
- Use `return()` with empty parens to return `(null)`
- Comparison uses single `=` (not `==`): `if ($code = 200)`
- Prefer structured relationships such as property pivots or verb specific pivots over wild cards.
- Use the most specific syntax which makes sense. (`-(refs)> inet:fqdn` is better than `--> *`)

## Debugging Workflow

1. **Isolate the failing query** -- extract the minimal Storm snippet that reproduces the error.

2. **Check the error location** -- the `storm_validate` result (and `BadSyntax`) provides `line` and `column`. Look at that exact position in the query.

3. **Build up incrementally and check the output at each step** -- for complex queries, construct the query one pipeline stage at a time, running each stage with the `storm` tool and confirming it yields the expected nodes/output before adding the next operation. This pins down which stage changes the results. The focus here is verifying the expected output at each step; you can also `storm_validate` each stage for syntax, or do both:
   ```storm
   // Run the lift alone and confirm the expected nodes come back
   inet:fqdn=example.com

   // Add the filter and confirm the result set narrows as expected
   inet:fqdn=example.com +:zone=1

   // Add the pivot and confirm it lands on the expected nodes
   inet:fqdn=example.com +:zone=1 -> inet:dns:a
   ```

4. **Check the grammar** -- read the raw Lark grammar from the `syn://storm/grammar` MCP resource. Storm's error messages already map raw token names to readable descriptions.

5. **Verify end-to-end** -- once the syntax is valid, run the query with the `storm` tool and inspect the returned `node` / `print` / `warn` / `err` messages to confirm it produces the expected results.

6. **Runtime errors vs parse errors** -- if the query parses but fails at runtime, the error is likely a `NoSuchForm`, `NoSuchProp`, `BadTypeValu`, or `AuthDeny`, not `BadSyntax`. Use the `model_find` MCP tool (or `syn://model` MCP resource) for valid form/property names.

## Key Tools & Files

| Tool / File | Purpose |
|-------------|---------|
| `storm_validate` MCP tool | Validate Storm syntax without executing a query |
| `storm` / `call_storm` MCP tools | Run Storm queries against the Cortex (page of result messages / return a value) |
| `view_list` / `view_get` MCP tools | List views (for the `view` storm opt) and read the user's default view |
| `view_fork` / `view_del` / `view_merge` MCP tools | Fork, delete, and merge views (use fork+del to safely test ingest) |
| `model_find` MCP tool, `syn://model` MCP resource | Search / discover forms, properties, and types |
| `syn://model/form/{name}` MCP resource | A single data model form definition |
| `syn://stormdocs` MCP resource | Storm library, type, and command documentation |
| `syn://storm/grammar` MCP resource | The raw Lark grammar for the Storm query language |
