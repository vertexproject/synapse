# Storm Query Language Syntax Skill

TRIGGER: When writing, editing, reviewing, or discussing Storm (.storm) files, Storm queries, Storm packages, or Synapse query language code.

## Language Overview

Storm is an async pipeline-based graph query language for Synapse. Queries are chains of operations and commands that transform streams of `(node, path)` tuples lazily. Storm files use `/* */` and `//` comments. Inline commands must end with `|` to return to storm operator syntax.

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

Comparison operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `~=` (regex), `^=` (prefix), `in`, `not in`

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

// Parenthesized edit context (inline node creation)
[( risk:vuln=($ndef, $vuln)
    :node=$ndef
    :vuln=$vuln
    <(seen)+ $srcnode
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

// Comparison: =, !=, <, >, <=, >=, ~=, ^=, in, not in
$check = ($a > 5 and $b < 10)

// Logical: and, or, not
$match = ($str ~= "pattern")
```

**Operator precedence** (low->high): `or` -> `and` -> `not` -> comparisons -> `+/-` -> `*/%` -> unary `-` -> `**`

### Strings

```storm
inet:fqdn=example.com                        // unquoted (no spaces)
'literal string \n not escaped'              // single-quoted (raw)
"escaped string \n \t \\"                    // double-quoted (escapes)
'''raw multiline
string'''                                    // triple-quoted

`format string {$var} and {:prop}`           // backtick format string
`result: {$x + 1} name: {$node.repr()}`     // expressions in {}
```

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
// Pass-through (nodes unchanged, side effects persist)
inet:fqdn { [ +#reviewed ] }

// As node reference in edits
[ :account = { [ syn:user=$lib.auth.users.get().iden ] } ]

// Embedded query expression
$file = ${ [ file:bytes=$sha256 ] }
```

### Lifecycle Blocks

```storm
init { ... }                                  // runs once before any nodes
empty { ... }                                 // runs if pipeline is empty
fini { ... }                                  // runs once after all nodes
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
divert $cmdopts.yield --size $cmdopts.size $mod.enrich($node)  // divert pipeline
delnode                                       // delete nodes
movetag old.tag new.tag                      // rename tags
graph                                         // generate subgraph
help [command]                                // show help
iden $iden                                    // lift node by iden
background { query }                         // run query in background
batch --size 100 { query }                   // batch pipeline processing
copyto $layer                                // copy nodes to layer
diff                                          // yield added/changed nodes
edges.del                                     // delete light edges
intersect { query }                          // intersect pipelines
lift.byverb $verb                            // lift by edge verb
merge --apply                                // merge layer changes
movenodes --srclayer $src --destlayer $dst   // move nodes between layers
parallel { query }                           // parallel execution
reindex                                       // reindex nodes
runas --user $user { query }                 // run as another user
scrape --refs $text                          // scrape indicators
sleep $seconds                               // pause execution
tag.prune #tag                               // prune tag tree
tree { query }                               // recursive traversal
view.exec $view { query }                   // execute in view
```

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
$lib.utils.type($value)                      // get type name string
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
    headers=$headers, params=$params,
    json=$json, ssl=$ssl, proxy=$proxy)      // HTTP request
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
$lib.globals.$key                            // global variable
$lib.auth.users.get($iden)                   // get user by iden
$lib.auth.users.byname($name)               // get user by name
$lib.auth.roles.byname($name)               // get role by name
$lib.auth.easyperm.confirm($obj, $lvl)       // check easyperm

// Model
$lib.model.form($formname)                   // get form object
$lib.gen._riskVulnByCve($cve, ...)           // generate risk:vuln

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
$lib.lift.byPropAlts($name, $valu, cmpr="=") // lift by prop value including alternates
$lib.lift.byPropRefs($props, valu=$propvalu, cmpr="=") // lift nodes referenced by props
$lib.lift.byPropsDict($form, $propsdict, errok=(false)) // lift by multiple prop values
$lib.lift.byNodeData($name)                  // lift nodes with a given nodedata key

// Version
$lib.version.synapse                         // synapse version tuple
```

### Node Object Methods

```storm
$node.form()                                 // form name string
$node.ndef()                                 // (form, value) tuple
$node.iden()                                 // node identity hash
$node.nid                                    // node ID in the layer
$node.value()                                // primary value
$node.repr()                                 // human representation
$node.pack()                                 // pack node to dict
$node.props                                  // property dict access
$node.props.propname                         // specific property
$node.isform("inet:fqdn")                   // check form type
$node.tags()                                 // get tags dict
$node.difftags($tags)                        // diff tags vs current
$node.globtags(pattern)                      // match tags by glob
$node.edges()                                // iterate light edges
$node.addEdge($verb, $n2iden)               // add a light edge
$node.delEdge($verb, $n2iden)               // delete a light edge
$node.protocol()                             // get protocol name
$node.protocols()                            // get all protocols
$node.getByLayer()                           // get node per layer
$node.getStorNodes()                         // get storage nodes
$node.data.set("key", $value)               // set node data
$node.data.get("key")                        // get node data
$node.data.has("key")                        // check node data exists
```

## Style Rules

- Use `/* */` block comments for module headers, `//` for inline comments
- Private/internal functions use `_` prefix: `function _helperFunc()`
- Double-underscore `__` prefix for privsep-internal functions: `function __getJson()`
- Module variables at top level: `$setup = $lib.import(...)`, `$srcnode = (null)`
- Format strings with backticks for interpolation: `` `text {$var}` ``
- Parenthesize boolean expressions: `if ($a = null)`, `$x = (true)`, `$list = ([])`
- Use `$lib.raise(ErrName, "message")` for errors, `$lib.exit("message")` for fatal exits
- Use `return()` with empty parens to return `(null)`
- Comparison uses single `=` (not `==`): `if ($code = 200)`
- Use `(true)`, `(false)`, `(null)` — not `$lib.true`, `$lib.false`, `$lib.null`
- Prefer structured relationships such as property pivots or verb specific pivots over wild cards.
- Use the most specific syntax which makes sense. (`-(refs)> inet:fqdn` is better than `--> *`)
