# Storm Query Language Syntax Skill

TRIGGER: When writing, editing, reviewing, or discussing Storm (.storm) files, Storm queries, Storm packages, or Synapse query language code.

## Language Overview

Storm is an async pipeline-based graph query language for Synapse. Queries are chains of operations separated by `|` that transform streams of `(node, path)` tuples lazily. Storm files use `/* */` and `//` comments. Inline commands must end with `|` to return to storm operator syntax.

## Syntax Quick Reference

### Lifting (Select Nodes)

```storm
inet:fqdn                          // all nodes of a form
inet:fqdn=example.com              // by primary value
inet:fqdn:zone=1                   // by property value
inet:fqdn:zone                     // where property is set
#tag.name                          // by tag
#tag.*                             // by tag glob
:prop*[range=(200,400)]            // by array contents
reverse(inet:fqdn)                 // reverse lift order
```

Comparison operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `~=` (regex), `^=` (prefix)

### Filtering

```storm
+#tag.name                         // keep nodes with tag
-:prop=value                       // remove matching nodes
+{ -> inet:ipv4 +:asn=1234 }      // subquery filter (keep)
-{ -> inet:ipv4 }                  // subquery filter (remove)
+(:asn=1234 or :asn=5678)         // compound: and, or, not
```

### Pivoting (Graph Traversal)

```storm
-> *                               // pivot to all referenced nodes
-> inet:ipv4                       // pivot to specific form
-> (inet:ipv4, inet:ipv6)         // pivot to multiple forms
<- *                               // reverse pivot (incoming refs)
-+> *                              // join pivot (keep source + targets)
-> { subquery }                    // raw pivot via subquery
:dns:a -> inet:ipv4               // property-based pivot

// Light edge traversal
-(refs)> *                         // walk N1 edges (outbound)
<(refs)- *                         // walk N2 edges (inbound)
--> *                              // N-walk (multi-hop)
<-- *                              // reverse N-walk
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
[ *unset= value ]                             // set only if unset (conditional)

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
$result = ($x + $y) * 2

// Comparison: =, !=, <, >, <=, >=, ~=, ^=, in, not in
$check = ($a > 5 and $b < 10)

// Logical: and, or, not
$match = ($str ~= "pattern")
```

**Operator precedence** (low→high): `or` → `and` → `not` → comparisons → `+/-` → `*/%` → unary `-` → `**`

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
stop                                          // halt current node processing
emit $value                                   // emit data to caller
```

### Functions

```storm
function myFunc(arg1, arg2=$lib.null) {
    // own pipeline scope
    return($result)
}

// Invocation
$result = $myFunc(val1, arg2=val2)

// Functions can yield nodes
function getNodes(form) {
    yield $lib.lift.byProp($form)
}
```

### Subqueries

```storm
// Pass-through (nodes unchanged, side effects persist)
inet:fqdn { [ +#reviewed ] }

// Yield (replace pipeline with subquery results)
yield { inet:fqdn=example.com -> * }

// As node reference in edits
[ :account = { [ syn:user=$lib.user.iden ] } ]

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
$lib.user.iden                               // current user iden
$lib.user.vars.$key                          // per-user variable
$lib.user.allowed($perm)                     // check permission
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

// JSON Schema
$lib.json.schema($schema).validate($data)    // returns ($ok, $result)

// Version
$lib.version.synapse                         // synapse version tuple
```

### Node Object Methods

```storm
$node.form()                                 // form name string
$node.ndef()                                 // (form, value) tuple
$node.value()                                // primary value
$node.repr()                                 // human representation
$node.props                                  // property dict access
$node.props.propname                         // specific property
$node.isform("inet:fqdn")                   // check form type
$node.has(:prop)                             // check property exists
$node.get(:prop)                             // get property value
$node.tags()                                 // get tags dict
$node.globtags(pattern)                      // match tags by glob
$node.data.set("key", $value)               // set node data
$node.data.get("key")                        // get node data
```

## Storm Package Conventions

### Standard Module Pattern

Every package follows this 4-module structure:

**Main module** (`pkgname.storm`):
```storm
/* Package-Name API */
$setup = $lib.import(pkgname.setup)
$ingest = $lib.import(pkgname.ingest)
$privsep = $lib.import(pkgname.privsep)

function enrich(n, opts=(null)) {
    $opts = $setup.resolveOpts($opts)
    $ingest.initMetaSource()

    if (not $n.isform(target:form)) {
        if $lib.debug {
            $lib.print(`pkgname enrich() skipping form: {$n.form()}={$n.repr()}`)
        }
        stop
    }

    $result = $privsep.getApiData($n, opts=$opts)
    if $result {
        for $item in $result.data {
            yield $ingest.addResult($item, opts=$opts)
        }
    }
}
```

**Setup module** (`pkgname.setup.storm`):
```storm
/* all APIs in this module are unstable/internal */
$vaultType = "package-name"

function resolveOpts(opts) {
    if ($opts = null) { $opts = ({}) }
    switch $lib.utils.type($opts.vault) {
        "str": { $opts.vault = $reqVault(name=$opts.vault) }
        "null": { $opts.vault = $reqVault() }
        "vault": { }
        *: { $lib.raise(BadArg, `Unexpected type for vault: {$lib.utils.type($opts.vault)}`) }
    }
    return($opts)
}

function reqVault(name=(null)) {
    $vault = $getVault(name=$name)
    if $vault { return($vault) }
    $lib.exit(`No configs found. Use pkgname.config.add to create one.`)
}
```

**Ingest module** (`pkgname.ingest.storm`):
```storm
/* all APIs in this module are unstable/internal */
$setup = $lib.import(pkgname.setup)

$srcnode = (null)
function initMetaSource() {
    if $srcnode { return($srcnode) }
    [ meta:source=$setup.modconf.source
        :name="Package Name"
        :type="package.type"
    ]
    $srcnode = $node
    return($node)
}

function addResult(item, opts=(null)) {
    [ target:form?=($item.key, $item.value)
        :prop?=$item.prop
        +?#$_prefixTags($opts.vault.configs.tag_prefix, $item.tags)
        <(seen)+ $srcnode
    ]
    return($node)
}
```

**Privsep module** (`pkgname.privsep.storm`) — runs as root for API calls:
```storm
/* all APIs in this module are unstable/internal */
$__setup = $lib.import(pkgname.setup)

$baseurl = $modconf.baseurl
$__endpoints = $modconf.endpoints

function __getJson(opts, endpoint, params=(null)) {
    $apikey = $opts.vault.secrets.apikey
    $proxy = $opts.vault.configs.proxy
    $ssl_verify = $opts.vault.configs.ssl_verify

    $headers = ({
        "Authorization": $apikey,
        "Accept": "application/json",
    })

    $url = `{$baseurl}{$endpoint}`
    $resp = $lib.inet.http.request("GET", $url, headers=$headers,
        params=$params, ssl=({"verify": $ssl_verify}), proxy=$proxy)

    if ($resp.code = 200) {
        return($resp.json())
    }
    $lib.warn(`API returned code {$resp.code}: {$resp.reason}`)
    return()
}
```

**Command module** (`pkgname.enrich.storm`):
```storm
init {
    if $cmdopts.debug { $lib.debug = (true) }
    $mod = $lib.import(pkgname)
}

$opts = ({
    "vault": $cmdopts.config,
})

divert $cmdopts.yield --size $cmdopts.size $mod.enrich($node, opts=$opts)
```

### Common Patterns

**Tag prefixing**:
```storm
function _prefixTags(prefix, tags) {
    if ($prefix = null or not $tags) { return(([]) ) }
    return($lib.tags.prefix($tags, $prefix))
}
```

**Meta source tracking** — every ingest module creates a `meta:source` node and links ingested data via `<(seen)+ $srcnode` edges.

**Try-add with `?=`** — use `?=` for properties/nodes that may fail type validation: `[ inet:dns:a?=($fqdn, $ip) ]`

**Conditional tags from variables**: `[ +?#$tags ]` — adds tags from a list variable, skipping if null.

**Subquery for inline node creation**: `[ :account = { [ syn:user=$lib.user.iden ] } ]`

**Edit parens for inline node refs**: `[( risk:vuln=($ndef, $vuln) :node=$ndef )]`

**Spin to discard pipeline nodes**: `[ inet:fqdn?=$hostname ] spin` — create node but don't yield it.

**Fini for cleanup**: `fini { return() }` or `fini { $ingest.setFeedOffset($qnode, $time) }`

**Debug logging pattern**:
```storm
if $lib.debug {
    $lib.print(`pkgname function(): {$n.form()}={$n.repr()}`)
}
```

**Retry loop with rate limiting**:
```storm
while ($tries < $maxTries) {
    $resp = $lib.inet.http.request("GET", $url, ...)
    if ($resp.code = 200) { return($resp.json()) }
    if ($resp.code = 429) {
        $retryin = $resp.headers."Retry-After"
        if (not $retryin) { $retryin = ($tries * 3) }
    }
    if ($retryin and $tries < $maxTries) {
        $lib.warn(`API returned {$resp.code}. Retrying in {$retryin}s.`)
        $lib.time.sleep($retryin)
        $tries = ($tries + 1)
        continue
    }
    $lib.warn(`API returned code {$resp.code}: {$resp.reason}`)
    return()
}
```

**Paginated API iteration**:
```storm
function __iterPagedJson(opts, endpoint, params=(null)) {
    if ($params = null) { $params = ({}) }
    while (1) {
        $data = $__getJson($opts, $endpoint, params=$params)
        if (not $data) { break }
        for $item in $data.results { emit $item }
        $next = $data.next
        if (not $next) { break }
        $params.next = $next
    }
}
```

**Vault-based config (modern pattern)**: Use `$lib.vault.*` for storing API keys and configuration. Use `$lib.json.schema()` for validation. Scope can be `"global"` or `"user"`.

**Legacy config pattern**: Use `$lib.globals.$key` for global settings and `$lib.user.vars.$key` for per-user settings.

## Style Rules

- Use `/* */` block comments for module headers, `//` for inline comments
- Private/internal functions use `_` prefix: `function _helperFunc()`
- Double-underscore `__` prefix for privsep-internal functions: `function __getJson()`
- Module variables at top level: `$setup = $lib.import(...)`, `$srcnode = (null)`
- Format strings with backticks for interpolation: `` `text {$var}` ``
- Parenthesize boolean expressions: `if ($a = null)`, `$x = (true)`, `$list = ([])`
- Use `$lib.raise(ErrName, "message")` for errors, `$lib.exit("message")` for fatal exits
- Use `stop` to skip the current node (not `return()` which exits the function)
- Use `return()` with empty parens for void returns
- Comparison uses single `=` (not `==`): `if ($code = 200)`
- Prefer structured relationships such as property pivots or verb specific pivots over wild cards.
- Use the most specific syntax which makes sense. (`-(refs)> inet:fqdn` is better than `--> *`)
