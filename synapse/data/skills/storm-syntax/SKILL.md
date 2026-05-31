---
name: storm-syntax
description: >-
  Reference for the Storm query language used by the Synapse Cortex: nodes and the
  data model, lifting, filtering, pivoting and traversal, editing nodes, tags,
  variables and types, control flow, and libraries. Use when composing or explaining
  Storm queries.
---

# Storm Syntax

Storm is the query language of the Synapse Cortex. A Storm query is a pipeline: nodes are
lifted from storage and flow left-to-right through operations that filter, pivot, edit, or
emit them. Most operations act on the nodes currently in the pipeline.

## Nodes and the data model

A node has a **form** (its type), a **primary value**, secondary **properties**, and
**tags**. Names use colon-delimited namespaces:

- Form: `inet:fqdn`, `inet:ipv4`, `media:news`
- Secondary property: `inet:dns:a:fqdn`, `:asn` (the `:` prefix refers to a property on the
  node in the pipeline)
- Universal property: `.created`, `.seen`
- Tag: `#cno.mal.redtree`, tag property: `#rep.vt:score`

Use the `syn://model` MCP resource (or `get_model` tool) to discover available forms,
properties, and types.

## Lifting (selecting nodes)

```storm
inet:fqdn                      // all FQDN nodes
inet:fqdn=vertex.link          // one node by primary value
inet:dns:a:fqdn=vertex.link    // by secondary property value
inet:ipv4=1.2.3.4/24           // by CIDR (type-aware)
inet:fqdn^=vertex              // prefix lift
inet:ipv4*range=(1.2.3.4, 1.2.3.20)
#cno.mal.redtree               // all nodes with a tag
inet:fqdn#cno.mal.redtree      // a form with a tag
```

## Filtering

Filters keep (`+`) or drop (`-`) nodes already in the pipeline:

```storm
inet:dns:a +:fqdn=vertex.link        // keep where :fqdn equals
inet:dns:a -:fqdn=vertex.link        // drop where :fqdn equals
inet:ipv4 +#cno.mal                  // keep tagged nodes
inet:fqdn +:issuffix=(true)
inet:ipv4 +($node.value() > 16909060)
```

Comparators include `=`, `!=`, `~=` (regex), `>`, `>=`, `<`, `<=`, `^=` (prefix), and
range. Combine with `and`, `or`, `not`, and parentheses.

## Pivoting and traversal

Move from the current nodes to related nodes:

```storm
inet:dns:a -> inet:fqdn        // pivot out to the form/prop referenced
inet:fqdn -> inet:dns:a        // pivot in (nodes that reference these)
inet:dns:a :fqdn -> inet:fqdn  // pivot from a specific property
inet:fqdn -> *                 // pivot to all referenced nodes
inet:fqdn <- *                 // pivot from all referencing nodes
```

Light edge traversal uses verbs in parentheses:

```storm
media:news -(refs)> *          // walk 'refs' edges out
* <(refs)- media:news          // walk 'refs' edges in
```

## Editing nodes

Edits live inside square brackets and create/modify nodes:

```storm
[ inet:fqdn=vertex.link ]                       // create (or make current)
[ inet:dns:a=(vertex.link, 1.2.3.4) :asof=now ] // create with a property
inet:fqdn=vertex.link [ :iszone=(true) ]        // set a property
[ inet:ipv4=1.2.3.4 +#cno.mal.redtree ]         // add a tag
inet:ipv4=1.2.3.4 [ -#cno.mal.redtree ]         // remove a tag
[ media:news=* :title="hello" ]                 // * generates a guid
[ inet:fqdn=vertex.link +(refs)> { inet:ipv4=1.2.3.4 } ]  // add an edge
```

`?=` and `:prop?=` set values only if they are valid/non-null (no error on bad input).
Deletion uses the `delnode` command: `inet:fqdn=vertex.link | delnode`.

## Tags

```storm
#cno.mal                       // lift by tag
inet:ipv4 [ +#cno.mal.redtree ]              // apply a tag
inet:ipv4 [ +#cno.mal.redtree=(2020, 2021) ] // tag with a time interval
inet:ipv4 +#cno.mal@=2020                    // filter by tag time
inet:ipv4 [ +#rep.vt:score=42 ]              // set a tag property
```

## Variables and types

```storm
$fqdn = vertex.link
$tags = ([])
$tags.append(cno.mal)
$d = ({"key": "valu"})
$now = $lib.time.now()
[ inet:fqdn=$fqdn ]
inet:dns:a $fqdn=:fqdn -> inet:fqdn +$fqdn    // per-node variable from a property
```

Literals: `(true)`/`(false)`/`(null)`, numbers `(42)`, lists `([1, 2])`, dicts
`({"k": "v"})`. Strings interpolate with backticks: `` `text {$var}` ``. Access node data
with `$node.value()`, `$node.form()`, `$node.repr()`, `$node.tags()`.

## Control flow

```storm
for $item in $list { ... }
for ($key, $valu) in $dict { ... }
while ($x < 10) { ... }
if ($score > 90) { ... } elif ($score > 50) { ... } else { ... }
switch $form { "inet:fqdn": { ... } *: { ... } }
try { ... } catch * as err { ... }
```

`break`, `continue`, and `stop` control loops/pipeline. `yield` emits nodes from a
subquery. Subqueries in `{ }` run a nested pipeline.

## Commands and libraries

Pipe nodes into commands with `|`:

```storm
inet:fqdn | limit 10
inet:fqdn | uniq
inet:ipv4 | count
media:news | tee { -> * } { -(refs)> * }
```

The `$lib.*` libraries provide functions, e.g. `$lib.print(mesg)`, `$lib.warn(mesg)`,
`$lib.time.now()`, `$lib.inet.http.get(url)`, `$lib.csv.emit(...)`. Define functions with
`function name(arg) { ... return($valu) }`. Use the `syn://stormdocs` MCP resource to
discover libraries, types, and commands.

## Comments

```storm
// line comment
/* block comment */
```
