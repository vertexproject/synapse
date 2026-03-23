# Storm Query Language Skill

TRIGGER: When writing, editing, reviewing, validating, debugging, or running Storm (.storm) files, Storm queries, Storm packages, or Synapse query language code. Also triggered when fixing BadSyntax exceptions, troubleshooting Storm parse errors, or running Storm queries against a local Cortex.

## Validating Storm Syntax

**IMPORTANT: Claude MUST validate ALL Storm query logic it generates using the validation tool below. Every Storm query written to a file, embedded in a test, or included in a Storm package MUST be validated before being considered complete. No exceptions.**

### Using the CLI Validation Tool (Required)

The `synapse.tools.storm.validate` tool validates Storm syntax without requiring a running Cortex. Always use this tool to validate Storm queries.

```bash
# Validate a .storm file
python -m synapse.tools.storm.validate path/to/query.storm

# Validate from stdin (use - as the file argument)
echo 'inet:fqdn=example.com' | python -m synapse.tools.storm.validate -

# Validate with a specific parse mode
python -m synapse.tools.storm.validate --mode lookup path/to/lookup.storm
python -m synapse.tools.storm.validate --mode search path/to/search.storm
```

Exit codes: `0` = valid syntax (prints `ok`), `1` = invalid syntax (prints error with line/column info).

**Workflow for validating generated Storm:**
1. Write the Storm query to a temporary file.
2. Run `python -m synapse.tools.storm.validate <file>` to check syntax.
3. If validation fails, fix the query and re-validate before proceeding.

### Running Storm Queries Locally

The `synapse.tools.storm.tester` tool runs Storm queries against a local Cortex without requiring an external service. It spins up a temporary Cortex, executes the query, and prints formatted results.

```bash
# Run a query from a .storm file
python -m synapse.tools.storm.tester path/to/query.storm

# Run from stdin
echo '[ inet:fqdn=example.com ]' | python -m synapse.tools.storm.tester -

# Raw JSON output (one Storm message per line)
python -m synapse.tools.storm.tester --raw path/to/query.storm

# Persistent directory (data survives between runs)
python -m synapse.tools.storm.tester --dir /tmp/mycore path/to/create.storm
python -m synapse.tools.storm.tester --dir /tmp/mycore path/to/query.storm

# Run in a specific view
python -m synapse.tools.storm.tester --dir /tmp/mycore --view <iden> path/to/query.storm

# Run in a disposable forked view (data isolation)
python -m synapse.tools.storm.tester --dir /tmp/mycore --forked path/to/query.storm

# Fork from a specific view (inherits parent layers, writes are discarded)
python -m synapse.tools.storm.tester --dir /tmp/mycore --view <iden> --forked path/to/query.storm
```

Without `--dir`, a temporary directory is created and cleaned up after the run. With `--dir`, the directory persists so nodes created in one run can be queried in the next.

The `--view` option runs the query in a specific view by iden instead of the default view. The `--forked` option forks the target view before running, then deletes the fork after execution -- any nodes or changes made during the run are discarded, leaving the underlying data untouched. Combined with `--dir`, this allows safe testing against persistent data.

**Use cases:**
- Quickly test Storm queries without standing up a full Cortex service
- Verify that a query produces the expected nodes and output
- Iteratively build up graph data across multiple runs using `--dir`
- Get raw JSON message output for scripting or debugging with `--raw`
- Validate that Storm logic works end-to-end (not just syntax) before deploying to a package
- Run queries in a specific view with `--view` for multi-view testing
- Use `--forked` to run queries without modifying the underlying data
- Combine `--dir` + `--forked` for safe, repeatable testing against persistent data

## Reading BadSyntax Errors

A `BadSyntax` exception contains:
- **`mesg`**: Human-readable error (e.g., `"Unexpected token 'and' at line 3, column 5, expecting one of: ..."`)
- **`line`** / **`column`**: Location in the query text
- **`token`**: The unexpected token value
- **`at`**: Character offset in query text
- **`highlight`**: Dict with `hash`, `lines`, `columns`, `offsets` for precise source mapping

The parser converts Lark errors to friendly messages using `terminalEnglishMap` in `synapse/lib/parser.py`.

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
$node.isform("inet:fqdn")                    // check form type
$node.tags()                                 // get tags dict
$node.difftags($tags)                        // diff tags vs current
$node.globtags(pattern)                      // match tags by glob
$node.edges()                                // iterate light edges
$node.addEdge($verb, $n2iden)                // add a light edge
$node.delEdge($verb, $n2iden)                // delete a light edge
$node.protocol()                             // get protocol name
$node.protocols()                            // get all protocols
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
inet:fqdn | limit 10 | +#tag
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
    *: { ... }
}
```

### 9. Wrong Comparison in Filter Context vs Expression Context
```storm
// Filter context uses direct comparison operators
+:asn=1234

// Expression context needs parenthesized comparison
if ($node.value() = "test") { ... }
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
    if ($fatal) {return($lib.null) }   // exit function
    return(woot)                       // exit function returning "woot"
}

function check01(n) {
    for $x in $n {
        emit $x             // emit $x to the invoker
        if ($x = woot) {
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
- Double-underscore `__` prefix for privsep-internal functions: `function __getJson()`
- Module variables at top level: `$setup = $lib.import(...)`, `$srcnode = (null)`
- Format strings with backticks for interpolation: `` `text {$var}` ``
- Parenthesize boolean expressions: `if ($a = null)`, `$x = (true)`, `$list = ([])`
- Use `$lib.raise(ErrName, "message")` for errors, `$lib.exit("message")` for fatal exits
- Use `return()` with empty parens to return `(null)`
- Comparison uses single `=` (not `==`): `if ($code = 200)`
- Use `(true)`, `(false)`, `(null)` -- not `$lib.true`, `$lib.false`, `$lib.null`
- Prefer structured relationships such as property pivots or verb specific pivots over wild cards.
- Use the most specific syntax which makes sense. (`-(refs)> inet:fqdn` is better than `--> *`)

## Debugging Workflow

1. **Isolate the failing query** -- extract the minimal Storm snippet that reproduces the error.

2. **Check the error location** -- `BadSyntax` provides `line` and `column`. Look at that exact position in the query.

3. **Validate incrementally** -- for complex queries, test each pipeline stage separately:
   ```storm
   // Test lift alone
   inet:fqdn=example.com

   // Then add filter
   inet:fqdn=example.com +:zone=1

   // Then add pivot
   inet:fqdn=example.com +:zone=1 -> inet:dns:a
   ```

4. **Check the grammar** -- the Lark grammar is at `synapse/data/lark/storm.lark`. The `terminalEnglishMap` in `synapse/lib/parser.py` maps token names to readable descriptions.

5. **Unit test pattern for syntax validation**:
   ```python
   async def test_storm_syntax(self):
       async with self.getTestCore() as core:
           # Valid query should not raise
           await core.nodes('inet:fqdn=example.com')

           # Invalid query should raise BadSyntax
           with self.raises(s_exc.BadSyntax):
               await core.nodes('inet:fqdn=example.com [')
   ```

6. **Runtime errors vs parse errors** -- if the query parses but fails at runtime, the error is likely a `NoSuchForm`, `NoSuchProp`, `BadTypeValu`, or `AuthDeny`, not `BadSyntax`. Check the data model for valid form/property names.

## Key Files

| File | Purpose |
|------|---------|
| `synapse/tools/storm/validate.py` | CLI tool for validating Storm syntax without a Cortex |
| `synapse/tools/storm/tester.py` | CLI tool for running Storm queries against a local Cortex |
| `synapse/lib/parser.py` | Storm parser, AST converter, error handling |
| `synapse/data/lark/storm.lark` | Lark grammar definition |
| `synapse/lib/ast.py` | AST node classes |
| `synapse/lib/storm.py` | Storm runtime execution |
| `synapse/exc.py` | `BadSyntax` and other exception classes |
| `synapse/lib/stormtypes.py` | Storm type system and `$lib` implementations |
