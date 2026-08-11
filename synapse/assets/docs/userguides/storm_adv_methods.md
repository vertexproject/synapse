<a id="storm-adv-methods"></a>

# Storm Reference - Advanced - Methods

Some of Storm's [Built-In Variables](storm_adv_vars.md#vars-builtin) support **methods** used to perform various actions on the object represented by the variable.

A **subset** of the built-in variables / objects that support methods, along with a few commonly used methods and examples, are listed below. For full detail, refer to the [stormtypes-prim-header](../stormtypes_prims.md#stormtypes-prim-header) technical reference.

<a id="meth-lib"></a>

## \$lib

The built-in [$lib](storm_adv_vars.md#vars-global-lib) variable is used to access Storm libraries. See the [stormtypes-libs-header](../stormtypes_libs.md#stormtypes-libs-header) technical reference for additional detail on available libraries.

[Optic](/docs/synapse-enterprise-optic/latest/index.md) users can use the **Library Explorer** (located in the Help Tool) to examine available libraries. Libraries are listed without their `$lib` prefix (e.g., `$lib.print()` is listed under `print(mesg)`).

> [!NOTE]
> In the examples below, the `$lib.print()` library function is used to display the value returned when a specific built-in variable or method is called. This is done for illustrative purposes only; `$lib.print()` is not required in order to use variables or methods.
>
> In some examples the Storm [spin](storm_ref_cmd.md#storm-spin) command is used to suppress display of the node itself. We do this for cases where displaying the node detracts from illustrating the value of the variable.

In some instances we have included use-case examples, where the variable or method is used in a sample Storm query to illustrate a possible practical use. While we have attempted to use relatively simple examples for clarity, some examples may leverage additional Storm features such as [subqueries](storm_ref_subquery.md), [subquery filters](storm_ref_filter.md#filter-subquery), or [control flow](storm_adv_control.md) elements such as `for` loops or `switch` statements.

<a id="meth-node"></a>

## \$node

[$node](storm_adv_vars.md#vars-node-node) is a built-in Storm variable that references **the current node in the Storm query pipeline**. `$node` can be used as a variable on its own or with the example methods listed below. See the [stormprims-node-f527](../stormtypes_prims.md#stormprims-node-f527) section of the [stormtypes-prim-header](../stormtypes_prims.md#stormtypes-prim-header) technical documentation for a full list.

> [!NOTE]
> As the `$node` variable and related methods reference the current node in the Storm pipeline, any Storm logic referencing `$node` will fail to execute if the pipeline does not contain a node (i.e., based on previously executing Storm logic).
>
> Also, because `$node` always refers to the **current** node, use of the variable carries some risks in more complex Storm queries and / or where the nodes in the pipeline are changing. (Use of `$node` is less risky in smaller / more tightly scoped queries.) Ensure you know **exactly** which node `$node` is operating on, or consider using alternatives such as a [User-Defined Variables](storm_adv_vars.md#vars-user) or a self-contained [function](storm_adv_functions.md).

**Examples**

Print the value of `$node` for an `inet:dns:a` node:

```stormdoc
storm> inet:dns:a=(woot.com, 54.173.9.236) $lib.print($node) | spin
Node{(('inet:dns:a', (('inet:fqdn', 'woot.com'), ('inet:ipv4', (4, 917309932)))), {'nid': 0, 'meta': {'created': 1786244006752088, 'updated': 1786244006755052}, 'tags': {}, 'props': {'fqdn': ('inet:fqdn', 'woot.com'), 'ip': ('inet:ip', (4, 917309932)), 'seen': ('ival', (1482957991000000, 1482957991001000, 1000))}, 'tagprops': {}, 'n1verbs': {}, 'n2verbs': {}})}
```

Print the value of `$node` for an `inet:fqdn` node with tags present:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node) | spin
Node{(('inet:fqdn', 'aunewsonline.com'), {'nid': 4, 'meta': {'created': 1786244006769939, 'updated': 1786244006774394}, 'tags': {'rep': (None, None, None), 'rep.mandiant': (None, None, None), 'rep.mandiant.apt1': (None, None, None), 'cno': (None, None, None), 'cno.infra': (None, None, None), 'cno.infra.dns': (None, None, None), 'cno.infra.dns.sink': (None, None, None), 'cno.infra.dns.sink.hole': (None, None, None), 'cno.infra.dns.sink.hole.kleissner': (1385424000000000, 1480118400000000, 94694400000000)}, 'props': {'host': ('str:lower', 'aunewsonline'), 'domain': ('inet:fqdn', 'com'), 'issuffix': ('bool', 0), 'iszone': ('bool', 1), 'zone': ('inet:fqdn', 'aunewsonline.com')}, 'tagprops': {}, 'n1verbs': {}, 'n2verbs': {}})}
```

> [!NOTE]
> The value of `$node` is the entire node object and associated properties and tags, as opposed to a specific aspect of the node, such as its iden or primary property value.
>
> As demonstrated below, some node constructors can intelligently leverage the relevant aspects of the full node object (the value of the `$node` variable) when creating new nodes.

Assign `$node` to the variable `$ns` and use it to set the `:nameservers` property of related WHOIS records:

```stormdoc
storm> inet:fqdn=ns1.example.com $ns=$node :zone -> inet:whois:record:fqdn [ :nameservers+=$ns ]
inet:whois:record=cba505c601a201eec02bebde19c031d5
        :created = 2024-03-27T03:00:00Z
        :fqdn = example.com
        :nameservers = ('ns1.example.com',)
        :updated = 2026-03-22T11:37:00Z
inet:whois:record=c7b669878864e9f66b2034e7c3cd3165
        :created = 2024-03-27T03:00:00Z
        :fqdn = example.com
        :nameservers = ('ns1.example.com',)
        :updated = 2024-09-18T22:46:00Z
```

In the example above, the [$node.value](storm_adv_methods.md#meth-node-value) method could have been used instead of `$node` to set the `:nameservers` property of the `inet:whois:record` nodes. In this case, the node constructor knows to use the primary property value from the `inet:fqdn` node to set the value.

Assign `$node` to the variable `$actor` and use it to set the `:actor` property of a `risk:compromise` node:

```stormdoc
storm> risk:threat:name='sparkling unicorn' $actor=$node [ ( risk:compromise=( { "name": "very bad compromise", "reporter:name": "vertex" } ) :actor=$actor ) ]
risk:threat=814fdc1e8fe2635386e776a372bb7ae2
        :name = sparkling unicorn
        :reporter:name = vertex
risk:compromise=0ba9429212d4740a132fb542aa210092
        :actor = 814fdc1e8fe2635386e776a372bb7ae2
        :name = very bad compromise
        :reporter:name = vertex
```

In the example above, `:actor` is a property that accepts multiple types (e.g., any form that implements the `entity:actor` interface). To ensure the property is set to correctly, Synapse needs to know both the value **and** type (form), for the property. Both are obtained from the full `$node` object.

<a id="meth-node-form"></a>

### \$node.form

The `$node.form` attribute returns the **form** of the current node in the Storm pipeline.

**Examples**

Print the form of an `inet:dns:a` node:

```stormdoc
storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.form) | spin
inet:dns:a
```

<a id="meth-node-globtags"></a>

### \$node.globtags()

The `$node.globtags()` method returns a **list of string matches from the set of tags applied to the current node** in the Storm pipeline.

The method takes a single argument consisting of a wildcard expression for the substring to match.

- The argument requires at least one wildcard ( `*` ) representing the substring(s) to match.
- The method performs an **exclusive match** and returns **only** the matched substring(s), not the entire tag containing the substring match.
- The wildcard ( `*` ) character can be used to match full or partial tag elements.
- Single wildcards are constrained by tag element boundaries (i.e., the dot ( `.` ) character). Single wildcards can match an entire tag element or a partial string within an element.
- The double wildcard ( `**` ) can be used to match across any number of tag elements; that is, the double wildcard is not constrained by the dot boundary.
- If the string expression starts with a wildcard, it must be enclosed in quotes in accordance with the use of [Entering Literals](storm_ref_intro.md#storm-literals).

See [$node.tags()](storm_adv_methods.md#meth-node-tags) to access full tags (vs. tag substrings).

**Examples**

Print the set of top-level (root) tags from any tags applied to the current node:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags('*')) | spin
['cno', 'rep']
```

Print the list of numbers associated with any threat group tags (e.g., such as `cno.threat.t42.own` or `cno.threat.t127.use`) applied to the current node:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags(cno.threat.t*)) | spin
['83']
```

In the example above, `$node.globtags()` returns the matching substring only (`83`), which is the portion matching the wildcard; it does not return the `t` character.

Print the list of organizations and associated names (e.g., threat group or malware family names) from any third-party (`rep`) tags applied to the current node:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags(rep.*.*)) | spin
[('crowdstrike', 'commentpanda'), ('mandiant', 'apt1'), ('mcafee', 'commentcrew'), ('symantec', 'commentcrew')]
```

Print all sub-tags for any tags starting with `foo` applied to the current node:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags(foo.**)) | spin
['bar', 'bar.baz', 'derp']
```

<a id="meth-node-is"></a>

### \$node.is()

The `$node.is()` method returns a Boolean value (true / false) for whether the current node in the Storm pipeline is of a specified form or implements a specified interface.

The method takes either a single form or interface, or a list of forms and/or interfaces, and returns `true` if the node matches any of the parameters. `$node.is()` respects form inheritance, so will return `true` if the node's form extends a base form specified as a parameter.

**Examples**

Print the Boolean value for whether a node is an `inet:fqdn` form:

```stormdoc
storm> inet:ip=54.173.9.236 $lib.print($node.is(inet:fqdn)) | spin
false
```

Print the Boolean value for whether a node is either an `inet:fqdn` or an `inet:ip` form:

```stormdoc
storm> inet:ip=54.173.9.236 $lib.print($node.is((inet:fqdn, inet:ip))) | spin
true
```

Print the Boolean value for whether a node implements the `entity:actor` interface:

```stormdoc
storm> risk:threat:name='sparkling unicorn' $lib.print($node.is(entity:actor)) | spin
true
```

Print the Boolean value for whether a node is an `it:host:account` form, or any form that extends that form:

```stormdoc
storm> it:host:windows:account:username='ron the cat' $lib.print($node.is(it:host:account)) | spin
true
```

Because `it:host:windows:account` extends `it:host:account`, the above query returns `true`.

<a id="meth-node-ndef"></a>

### \$node.ndef

The `$node.ndef` attribute returns the [Ndef](../glossary.md#gloss-ndef) (node definition) of the current node in the Storm pipeline.

**Examples**

Print the ndef of an `inet:dns:a` node:

```stormdoc
storm> inet:dns:a=(woot.com, 54.173.9.236) $lib.print($node.ndef) | spin
('inet:dns:a', (('inet:fqdn', 'woot.com'), ('inet:ipv4', (4, 917309932))))
```

<a id="meth-node-repr"></a>

### \$node.repr()

The `$node.repr()` method returns the human-friendly [Repr](../glossary.md#gloss-repr) (representation) of the specified property of the current node in the Storm pipeline (as opposed to the raw value stored by Synapse).

The method can optionally take one argument.

- If no arguments are provided, the method returns the repr of the node's primary property value.
- If an argument is provided, it should be the string of the secondary property name (i.e., without the leading colon ( `:` ) from relative property syntax). Virtual properties of secondary properties should omit the leading colon but include the dot ( `.` )preceding the virtual property name (e.g., `$node.repr(server.ip)`).
- If a meta property string or a virtual property of a primary property is provided, it must be preceded by the dot ( `.` ) and enclosed in quotes in accordance with the use of [Entering Literals](storm_ref_intro.md#storm-literals).

See [$node.value](storm_adv_methods.md#meth-node-value) to return the raw value of a property.

**Examples**

Print the repr of the primary property value of an `inet:dns:a` node:

```stormdoc
storm> inet:dns:a=(woot.com, 54.173.9.236) $lib.print($node.repr())  | spin
('woot.com', '54.173.9.236')
```

Print the repr of the `:ip` secondary property value of an `inet:dns:a` node:

```stormdoc
storm> inet:dns:a=(woot.com, 54.173.9.236) $lib.print($node.repr(ip)) | spin
54.173.9.236
```

Print the repr of the `.ip` virtual property of an `inet:server` node:

```stormdoc
storm> inet:server=tcp://67.227.226.240:22 $lib.print($node.repr('.ip')) | spin
67.227.226.240
```

Print the repr of the `:server.ip` virtual property of an `inet:flow` node:

```stormdoc
storm> inet:flow:server=tcp://67.227.226.240:22 $lib.print($node.repr(server.ip)) | spin
67.227.226.240
```

Print the repr of the `.created` meta property of an `inet:dns:a` node:

```stormdoc
storm> inet:dns:a=(woot.com, 54.173.9.236) $lib.print($node.repr('.created')) | spin
2026-08-09T02:53:26.752088Z
```

<a id="meth-node-tags"></a>

### \$node.tags()

The `$node.tags()` method returns a **list of the tags applied to the current node** in the Storm pipeline.

The method can optionally take one argument.

- If no arguments are provided, the method returns the full list of all tags applied to the node.
- An optional argument consisting of a wildcard string expression can be used to match a subset of tags.
  - If a string is used with no wildcards, the string must be an exact match for the tag element.
  - The wildcard ( `*` ) character can be used to match full or partial tag elements.
  - The method performs an **inclusive match** and returns the full tag for all tags that match the provided expression.
  - Single wildcards are constrained by tag element boundaries (i.e., the dot ( `.` ) character). Single wildcards can match an entire tag element or a partial string within an element.
  - The double wildcard ( `**` ) can be used to match across any number of tag elements; that is, the double wildcard is not constrained by the dot boundary.
  - If the string expression starts with a wildcard, it must be enclosed in quotes in accordance with the use of [Entering Literals](storm_ref_intro.md#storm-literals).

See [$node.globtags()](storm_adv_methods.md#meth-node-globtags) to access tag substrings (vs. full tags).

**Examples**

Print the list of all tags associated with an `inet:fqdn` node:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.tags()) | spin
['cno', 'cno.infra', 'cno.infra.dns', 'cno.infra.dns.sink', 'cno.infra.dns.sink.hole', 'cno.infra.dns.sink.hole.kleissner', 'cno.threat', 'cno.threat.t83', 'cno.threat.t83.own', 'faz', 'faz.baz', 'foo', 'foo.bar', 'foo.bar.baz', 'foo.derp', 'rep', 'rep.crowdstrike', 'rep.crowdstrike.commentpanda', 'rep.mandiant', 'rep.mandiant.apt1', 'rep.mcafee', 'rep.mcafee.commentcrew', 'rep.symantec', 'rep.symantec.commentcrew']
```

Print the tag that exactly matches the string `cno` if present on an `inet:fqdn` node:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(cno)) | spin
['cno']
```

Print the list of all tags two elements in length that start with `foo`:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(foo.*)) | spin
['foo.bar', 'foo.derp']
```

Print the list of all tags of any length that start with `f`:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(f**)) | spin
['faz', 'faz.baz', 'foo', 'foo.bar', 'foo.bar.baz', 'foo.derp']
```

Print the list of all tags of any length whose first element is `rep` and whose third element starts with `comment`:

```stormdoc
storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(rep.*.comment*)) | spin
['rep.crowdstrike.commentpanda', 'rep.mcafee.commentcrew', 'rep.symantec.commentcrew']
```

<a id="meth-node-value"></a>

### \$node.value

The `$node.value` attribute returns the raw value of the primary property of the current node in the Storm pipeline.

See [$node.repr()](storm_adv_methods.md#meth-node-repr) to return the human-friendly value of a property.

> [!NOTE]
> The `$node.value` attribute is only used to return the primary property value of a node. Secondary property values can be accessed via a user-defined variable (i.e., `$myvar = :<prop>`).

**Examples**

Print the raw value of the primary property value of an `inet:dns:a` node:

```stormdoc
storm> inet:dns:a=(woot.com, 54.173.9.236) $lib.print($node.value) | spin
(('inet:fqdn', 'woot.com'), ('inet:ipv4', (4, 917309932)))
```

<a id="meth-path"></a>

## \$path

[$path](storm_adv_vars.md#vars-node-path) is a built-in Storm variable that **references the path of a node as it travels through the pipeline of a Storm query.**

The `$path` variable is generally not used on its own, but in conjunction with its methods. See the [stormprims-node-path-f527](../stormtypes_prims.md#stormprims-node-path-f527) section of the [stormtypes-prim-header](../stormtypes_prims.md#stormtypes-prim-header) technical documentation for a full list.

<a id="meth-path-links"></a>

### \$path.links()

The `$path.links()` method returns a list of (node id, link info) tuples of each link in a node's path through a Storm query.

The method takes no arguments.

**Examples**

Print the list of links for the path of a single node through two pivots to a single end node:

```stormdoc
storm> inet:fqdn=aunewsonline.com -> inet:dns:a +:ip=67.215.66.149 -> inet:ip $lib.print($path.links())
[(4, {'type': 'prop', 'prop': 'fqdn', 'reverse': True}), (48, {'type': 'prop', 'prop': 'ip'})]
inet:ip=67.215.66.149
        :type = unicast
        :version = 4
```

The example above returns the node ids of the original `inet:fqdn` node and the `inet:dns:a` node with the specified IP, along with information about the pivot performed that linked the nodes.

Print the list of links for the path of a single node through two pivots to three different end nodes (i.e., three paths):

```stormdoc
storm> inet:fqdn=aunewsonline.com -> inet:dns:a -> inet:ip $lib.print($path.links())
[(4, {'type': 'prop', 'prop': 'fqdn', 'reverse': True}), (48, {'type': 'prop', 'prop': 'ip'})]
inet:ip=67.215.66.149
        :type = unicast
        :version = 4
[(4, {'type': 'prop', 'prop': 'fqdn', 'reverse': True}), (50, {'type': 'prop', 'prop': 'ip'})]
inet:ip=184.168.221.92
        :type = unicast
        :version = 4
[(4, {'type': 'prop', 'prop': 'fqdn', 'reverse': True}), (52, {'type': 'prop', 'prop': 'ip'})]
inet:ip=104.239.213.7
        :type = unicast
        :version = 4
```

In the example above, the FQDN has three DNS A records, thus there are three different paths that the original node takes through the query.

> [!NOTE]
> A lift operation contains no pivots (i.e., no "path"), so the method does not return any links.
