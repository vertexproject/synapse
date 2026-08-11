<a id="storm-ref-data-mod"></a>

# Storm Reference - Data Modification

Storm can be used to modify data in Synapse by:

- adding or deleting nodes;
- setting, modifying, or deleting properties on nodes;
- adding or deleting light edges; and
- adding or deleting tags from nodes (including tag timestamps or tag properties).

The ability to create or modify data on the fly gives users a powerful degree of flexibility and efficiency.

> [!WARNING]
> The ability to add and modify data directly from Storm is powerful and convenient, but users can inadvertently modify (or even delete) data inappropriately through mistyped syntax, incorrect Storm logic, or premature striking of the "enter" key. While some built-in protections exist within Synapse itself, it is important to remember that **there is no "are you sure?" prompt before a Storm query executes.**
>
> The following best practices will help prevent inadvertent changes to a Cortex:
>
> - **Always** [Fork a View](views_layers.md#ug_fork_view) and perform your changes in the fork. Once you have validated the changes, they can be merged into the parent view; if anything goes wrong, the fork can simply be deleted.
> - Use caution when constructing complex Storm queries that may modify (or delete) large numbers of nodes. It is **strongly recommended** that you validate the output of a query by first running the query on its own (without the edit or delete operations) to ensure it returns the expected results (set of nodes) before permanently modifying or deleting those nodes.
> - Use the Synapse permissions system to enforce least privilege. Limit users to permissions appropriate for tasks they have been trained for / are responsible for.

> [!TIP]
> For adding data at scale, we recommend use of the Synapse [cortex.csv](syn_tools_cortex_csv.md#syn-tools-cortex-csv), the Synapse [cortex.feed](syn_tools_cortex_feed.md#syn-tools-cortex-feed) utility, the Optic [Ingest Tool](../glossary.md#gloss-ingest-tool), or the programmatic ingest of data (e.g., using a [Power-Up](../glossary.md#gloss-power-up)).)

See [Storm Reference - Document Syntax Conventions](storm_ref_syntax.md#storm-ref-syntax) for an explanation of the syntax format used below.

See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details on special syntax or handling for specific data types ([Type](data_model.md#data-type)).

<a id="edit-mode"></a>

## Edit Mode

To perform an edit operation in Storm, you must enter edit mode. Edit mode makes use of several conventions to specify what changes should be made and to what data:

- [Edit Brackets](storm_ref_data_mod.md#edit-brackets)
- [Edit Parentheses](storm_ref_data_mod.md#edit-parens)
- ["Try" Operator](storm_ref_lift.md#lift-try)
- [Conditional Edit Operators](storm_ref_data_mod.md#conditional-edit-operators)
- [Autoadds and Depadds](storm_ref_data_mod.md#autoadds-depadds)

<a id="edit-brackets"></a>

### Edit Brackets

The use of square brackets ( `[ ]` ) within a Storm query can be thought of as entering edit mode. The data in the brackets specifies the changes to be made involving nodes, properties, light edges, and tags. The only exception is deleting nodes, which is done using the Storm [delnode](storm_ref_cmd.md#storm-delnode) command.

The square brackets used for the Storm data modification (edit) syntax indicate "perform the enclosed changes" in a generic way. Edit brackets are used to perform any of the following:

- [Add Nodes](storm_ref_data_mod.md#node-add)
- [Add or Modify Properties](storm_ref_data_mod.md#prop-add-mod)
- [Add or Modify Properties Using Subqueries](storm_ref_data_mod.md#prop-add-mod-subquery)
- [Delete Properties](storm_ref_data_mod.md#prop-del)
- [Add Light Edges](storm_ref_data_mod.md#light-edge-add)
- [Delete Light Edges](storm_ref_data_mod.md#light-edge-del)
- [Add Tags](storm_ref_data_mod.md#tag-add)
- [Modify Tags](storm_ref_data_mod.md#tag-mod)
- [Remove Tags](storm_ref_data_mod.md#tag-del)

All of the above directives can be specified within a single set of brackets (subject to Storm logic and Storm's pipeline behavior).

> [!NOTE]
> It is critical to remember that **the brackets are NOT a boundary that segregates nodes;** the brackets simply indicate the start and end of an edit operation. Editing is simply another Storm operation, so the specified edits will be performed on **ALL nodes inbound to the edit operation** as part of the Storm pipeline, regardless of whether those nodes are within or outside the brackets.
>
> The exception is modifications that are placed within [Edit Parentheses](storm_ref_data_mod.md#edit-parens), which can be used to segregate specific edit operations.
>
> For simplicity, syntax examples below demonstrating how to add nodes, modify properties, etc. only use edit brackets. See [Combining Data Modification Operations](storm_ref_data_mod.md#data-mod-combo) below for examples showing the use of edit brackets with and without edit parentheses.

<a id="edit-parens"></a>

### Edit Parentheses

Storm supports the use of edit parentheses ( `( )` ) inside of [Edit Brackets](storm_ref_data_mod.md#edit-brackets). Edit parentheses (parens) explicitly limit a set of modifications to a specific node or nodes by enclosing the node(s) and their associated modification(s) within the parentheses. This overrides the default behavior for edit brackets, which is that every change specified within the brackets applies to **all nodes inbound to the edit operation.** Edit parens thus allow you to make limited changes inline with a more complex Storm query instead of having to use a smaller, separate query to make those changes.

Note that multiple sets of edit parens can be used within a single set of edit brackets; each set of edit parens delimits a separate set of edits.

See [Combining Data Modification Operations](storm_ref_data_mod.md#data-mod-combo) below for examples showing the use of edit brackets with and without edit parentheses.

<a id="edit-try"></a>

### "Try" Operator

The Storm "try" operator can be used in edit operations when setting properties ( `?=` ) or adding tags ( `+?#` ).

Properties in Synapse are subject to [Type Enforcement](../glossary.md#gloss-type-enforce). Type enforcement makes a reasonable attempt to ensure that a value makes sense for the property in question - that the value you specify for an `inet:ip` node looks reasonably like an IP address (and not an FQDN or URL). If you try to set a property value that does not pass Synapse's type enforcement validation, Synapse will generate a `BadTypeValu` error. The error will cause the currently executing Storm query to halt and stop processing.

When using the try operator, Synapse will attempt (try) to set the property value. With the try operator, instead of halting in the event of a `BadTypeValu` error, Synapse will ignore the error (silently fail on that specific edit operation) but continue processing the rest of the Storm query.

The try operator is especially useful for Storm-based automated ingest of data where the data source may contain bad (improperly typed or poorly formatted) data, where a single badly-formatted entry could cause an ingest query to fail in the middle.

For example, the following query will silently fail to create an `inet:ip` node with the improper value `woot.com`, but will continue to create the IP `22.22.22.22`:

```stormdoc
storm> [ inet:ip?=woot.com inet:ip?=22.22.22.22 ]
inet:ip=22.22.22.22
        :type = unicast
        :version = 4
```

In contrast, the following query will throw a `BadTypeValu` error and exit when it encounters the invalid IP value. The rest of the query fails to run, and the IP `22.22.22.22` is never created:

```stormdoc
storm> [ inet:ip=woot.com inet:ip=22.22.22.22 ]
ERROR: Invalid IP address: woot.com
```

> [!TIP]
> See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for specialized "try" syntax when working with arrays.

#### Tags and the "Try" Operator

Tags are also nodes (`syn:tag` nodes), and tag values are also subject to type enforcement. As such, the "try" operator can also be used when applying tags:

`inet:ip=58.158.177.102 [ +?#cno.infra.dns.sink.hole ]`

While Synapse automatically normalizes tag elements (e.g., by replacing dash characters ( `-` ) or spaces with underscores ( `_` )), some characters (such as ASCII symbols other than the underscore) are not allowed. The "try" operator may be useful when ingesting third-party data or constructing a tag using a [Variable](../glossary.md#gloss-variable) where the variable may contain unexpected values. For example:

`inet:ip=8.8.8.8 [ +?#foo.$tag ]`

... where `$tag` is a variable representing a tag element derived from the source data.

See the [syn:tag](storm_ref_type_specific.md#type-syn-tag) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for additional detail on tags / `syn:tag` forms.

### Conditional Edit Operators

The conditional edit operators ( `*unset=` and `*$<varname>=` ) can be used to only set properties when certain conditions are met.

The `*unset=` operator will only set a property when it does not already have a value to prevent overwriting existing data. For example:

`inet:ip=1.2.3.4 [ :asn *unset=12345 ]`

will only set the `:asn` property on the `inet:ip` node if it is not already set. The conditional edit operators can also be combined with the "try" operator ( `*unset?=` ) to prevent failures due to bad data:

`inet:ip=1.2.3.4 [ :asn *unset?=invalid ]`

Variable values may also be used to control the conditional edit behavior, and allow two more values in addition to `unset`; `always` and `never`. For example:

`$asn=always $loc=never inet:ip=1.2.4.5 [ :place:loc *$loc=us :asn *$asn?=12345 ]`

will never set the `:place:loc` property and will always attempt to set the `:asn` property. This behavior is useful when creating Storm ingest functions where fine tuned control over specific property edit behavior is needed. Rather than creating variations of the same ingest function with different combinations of property set behavior, one function can use a dictionary of configuration options to control the edit behavior used during each execution.

<a id="autoadds-depadds"></a>

### Autoadds and Depadds

Synapse makes use of two optimization features when adding nodes or setting secondary properties: automatic additions ([Autoadd](../glossary.md#gloss-autoadd)) and dependent additions ([Depadd](../glossary.md#gloss-depadd)).

**Autoadd** is the process where, on node creation, Synapse will automatically set any secondary properties that can be computed from a node's primary property. Because a node's primary property cannot be changed once set, computed secondary properties are read-only.

For example, when creating the email address `inet:email=visi@vertex.link`, Synapse will automatically set the `inet:email` node's secondary properties (the username `:username=visi` and domain `:fqdn=vertex.link`).

**Depadd** is the process where, on setting a node's secondary property value, if that property is of a type that is also a form, Synapse will automatically create the node with the corresponding primary property value. (You can view this as the secondary property "depending on" the existence of a node with the corresponding primary property.)

To use the same example, when creating the email `inet:email=visi@vertex.link` and setting the secondary properties above, Synapse will also create the associated nodes `entity:name=visi` and `inet:fqdn=vertex.link` if they do not exist.

Autoadd and depadd work together (and recursively) to simplify adding data to Synapse.

<a id="node-add"></a>

## Add Nodes

Operation to add the specified node(s) to a Cortex.

**Syntax:**

**\[** *\<form\>* **=** \| **?=** *\<valu\>* ... **\]**

> [!TIP]
> You can optionally use the ["Try" Operator](storm_ref_data_mod.md#edit-try) ( `?=` ) when adding nodes.

**Examples:**

Create a simple node (FQDN):

``` text
[ inet:fqdn=woot.com ]
```

Create a composite (comp) node (DNS A record):

``` text
[ inet:dns:a=( woot.com, 12.34.56.78 ) ]
```

Create a GUID node by generating an arbitrary guid using the asterisk character:

``` text
[ risk:threat=* ]
```

Create a GUID node by specifying a list of string values used to generate a predictable guid:

``` text
[ risk:threat=( apt1, mandiant ) ]
```

Create a GUID node using dictionary syntax to create a predictable guid **and** deconflict the node against any existing nodes in the Cortex with the same property values:

``` text
[ risk:threat=( { "name": "apt1", "reporter:name": "mandiant" } ) ]
```

> [!TIP]
> For information on the differences and use cases for arbitrary guids, predictable guids, and dictionary syntax, see the [guid](storm_ref_type_specific.md#type-guid) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific).
>
> Storm also includes various [gen](storm_ref_cmd.md#storm-gen) (generate) commands to simplify the creation of some common guid forms.

Create multiple nodes in a single edit operation:

``` text
[ inet:fqdn=woot.com inet:ip=12.34.56.78 crypto:hash:md5=d41d8cd98f00b204e9800998ecf8427e ]
```

**Usage Notes:**

- If a node specified within the edit brackets does not exist, Synapse creates and returns the node. If the node already exists, Synapse simply returns (lifts) the node.
- When creating a *\<form\>* whose *\<valu\>* consists of multiple components, the components must be passed as a comma-separated list enclosed in parentheses.
- Once a node is created, its primary property (*\<form\>*=\*\<valu\>*)cannot be modified.*\* The only way to "change" a node's primary property is to create a new node (and optionally delete the old node).

<a id="prop-add-mod"></a>

## Add or Modify Properties

Operation to add (set) or change one or more properties on the specified node(s).

The same syntax is used to apply a new property or modify an existing property.

**Syntax:**

*\<query\>* **\[ :** *\<prop\>* **=** \| **?=** *\<pval\>* ... **\]**

*\<query\>* **\[ :** *\<prop\>* **\*unset=** \| **\*unset?** *\<pval\>* ... **\]**

*\<query\>* **\[ :** *\<prop\>* **\*\$\<varname\>=** \| **\*\$\<varname\>?=** *\<pval\>* ... **\]**

> [!TIP]
> You can optionally use the ["Try" Operator](storm_ref_data_mod.md#edit-try) ( `?=` ) when setting or modifying properties.

> [!NOTE]
> Synapse supports secondary properties that are **arrays** (lists or sets of typed forms), such as `ou:org:names`. See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for the syntax used to add or modify array properties.

**Examples:**

Add (or modify) a secondary property:

``` text
<inet:ip> [ :place:loc=us.oh.wilmington ]
```

**Usage Notes:**

- Specifying a property will set the *\<prop\>=\<pval\>* if it does not exist, or modify (overwrite) the *\<prop\>=\<pval\>* if it already exists. **There is no prompt to confirm overwriting of an existing property.**
- Storm will return an error if the inbound set of nodes contains any forms for which *\<prop\>* is not a valid property. For example, attempting to set a `:place:loc` property when the inbound nodes contain both FQDNs and IP addresses will return an error as `:place:loc` is not a valid secondary property for an FQDN (`inet:fqdn`).
- Properties to be set or modified **must** be specified by their relative property name. For example, for the form `foo:bar` with the property `baz` (i.e., `foo:bar:baz`) the relative property name is specified as `:baz`.

<a id="prop-add-mod-subquery"></a>

## Add or Modify Properties Using Subqueries

Secondary property values can be set using a **subquery** to assign the value. The subquery executes a Storm query to lift the node(s) that should be assigned as the value of the secondary property.

This is a specialized use case that is most useful when working with property values that are guid nodes (see [Guid](../glossary.md#gloss-guid)). Using a subquery allows you to reference the node using a more human-friendly method (as opposed to needing to copy / paste the guid value).

(See [Storm Reference - Subqueries](storm_ref_subquery.md#storm-ref-subquery) for additional detail on subqueries.)

> [!TIP]
> You can optionally use the ["Try" Operator](storm_ref_data_mod.md#edit-try) ( `?=` ) when setting or modifying properties using a subquery.

**Syntax:**

*\<query\>* **\[ :** *\<prop\>* **=** \| **?=** **{** *\<query\>* **}** ... **\]**

**Examples:**

Use a subquery to assign an organization (`ou:org`) as the secondary property of an `entity:contact` node:

```stormdoc
storm> entity:contact:name='Ozzie the Pony' [ :org={ ou:org:name='The Vertex Project' } ]
entity:contact=b03173bee96299ce60be9bdff1f68e04
        :name = Ozzie the Pony
        :org = 65d8a6380f7a777008e5fbd03a22453a
        :org:name = The Vertex Project
        :type = employee.vertex
```

In the example above, the subquery `ou:org:name='The Vertex Project'` is used to lift the organization node with that `:name` property value and assign the node to the `:org` property of the `entity:contact` node.

Use a subquery to assign one or more industries (`ind:industry`) to an organization:

```stormdoc
storm> ou:org:name=apple [ :industries+={ ind:industry:name~=manufacturing ind:industry:name~=telecommunications } ]
ou:org=a4c02b3a2e26188ef27fb571faf14ca1
        :industries = ['2e1de12c9509d165195b3975e1171bc9', '9c3957ec70bd75335f01d80125c03b39']
        :name = apple
        :names = ['apple, inc.']
```

In the example above, the subquery is used to lift the specified industry nodes (`ind:industry`) and assign both nodes to the `ou:org:industries` property for Apple's organization node.

> [!NOTE]
> The `ou:org:industries` property is an **array** (a list or set of typed forms), so the query above uses array-specific syntax. See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for detail on the syntax used to add or modify array properties.

**Usage Notes:**

- When using a subquery to assign a property value, Storm will throw an error if the subquery fails to lift any nodes.
- When using a subquery to assign a value to a property that takes only a single value, Storm will throw an error if the subquery returns more than one node.
- When using a subquery to assign a property value, the subquery cannot iterate more than 128 times or Storm will throw an error. For example, attempting to assign all industries to a single organization ( `ou:org=<guid> [ :industries+={ ind:industry } ]` ) will error if there are more than 128 `ind:industry` nodes.

<a id="prop-del"></a>

## Delete Properties

Operation to delete (fully remove) one or more properties from the specified node(s).

**Syntax:**

*\<query\>* **\[ -:** *\<prop\>* ... **\]**

**Examples:**

Delete the `:place:loc` property from an `inet:ip` node:

``` text
<inet:ip> [ -:place:loc ]
```

Delete multiple properties from a `doc:report` node:

``` text
<doc:report> [ -:creator -:desc ]
```

**Usage Notes:**

- Deleting a property fully removes the property from the node; it does not set the property to a null value.

<a id="node-del"></a>

## Delete Nodes

Nodes can be deleted from a Cortex using the Storm [delnode](storm_ref_cmd.md#storm-delnode) command.

<a id="light-edge-add"></a>

## Add Light Edges

Operation that links the specified node(s) to another node or set of nodes (as specified by a Storm expression or variable) using a lightweight edge (light edge).

See [Lightweight Edge](data_model.md#data-light-edge) for details on light edges.

**Syntax:**

*\<query\>* **\[ +(** *\<verb\>* **)\> {** *\<storm\>* **}** \| *\<valu\>* **\]**

*\<query\>* **\[ \<(** *\<verb\>* **)+ {** *\<storm\>* **}** \| *\<valu\>* **\]**

> [!NOTE]
> The query syntax used to create light edges will yield the nodes that are **inbound to the edit brackets** (that is, the nodes represented by *\<query\>*).
>
> The nodes specified by the Storm expression ( `{ <storm> }` ) must already exist in the Cortex or must be created as part of the Storm expression (i.e., using edit brackets) in order for the light edges to be created.

**Examples:**

Link the specified FQDN and IP to the `doc:report` node referenced by the Storm expression using a `-(refs)>` light edge:

``` text
inet:fqdn=woot.com inet:ip=1.2.3.4 [ <(refs)+ { doc:report:title="report about bad stuff" } ]
```

Link the specified `doc:report` node to the set of indicators Mandiant associates with APT1 (`#rep.mandiant.apt1`) using a `-(refs)>` light edge:

``` text
doc:report:title="apt1 report" [ +(refs)> { #rep.mandiant.apt1 } ]
```

Link the specified threat cluster (`risk:threat`) to the technique used by the cluster with a `-(used)>` light edge:

``` text
risk:threat:name='forest blizzard' [ +(used)> { meta:technique:name=phishing } ]
```

Link the specified threat cluster to a technique used by the cluster with a `-(used)>` light edge, creating the technique if it does not exist:

``` text
risk:threat:name='forest blizzard' [ +(used)> { [ meta:technique=( { "name": "phishing", "reporter:name": "mitre" } ) ] }
```

> [!TIP]
> A `meta:technique` is a guid node; the example above uses [Dictionary Syntax](storm_ref_type_specific.md#guid-dictionary) to create / deconflict the `meta:technique` node based on the technique `:name` and `:reporter:name`.

Link the specified `doc:report` node to a node contained in a variable using a `-(refs)>` light edge:

``` text
$fqdn={ inet:fqdn=woot.com } doc:report:title="\"It's all WINNTI\", says researcher" [ +(refs)> $fqdn ]
```

> [!TIP]
> In the example above, the document title includes double quotes (`"`), so the backslash (`\`) is needed in order to escape those characters. See [Entering Literals](storm_ref_intro.md#storm-literals) for details on the use of single quotes, double quotes, and escape characters in Storm.

**Usage Notes:**

- The plus sign ( `+` ) used with the light edge expression within the edit brackets is used to create the light edge(s).
- Light edges can be created in either direction (e.g., with the directional arrow pointing either right ( `+(<verb>)>` ) or left ( `<(<verb>)+` ) - whichever syntax is easier.
- The Storm [edges](storm_ref_cmd.md#storm-edges) and [lift](storm_ref_cmd.md#storm-lift) commands can be used to work with light edges in Synapse.

<a id="light-edge-del"></a>

## Delete Light Edges

Operation that deletes the light edge linking the specified node(s) to the set of nodes specified by a given Storm expression or variable.

See [Lightweight Edge](data_model.md#data-light-edge) for details on light edges.

**Syntax:**

*\<query\>* **\[ -(** *\<verb\>* **)\> {** *\<storm\>* **}** \| *\<valu\>* **\]**

*\<query\>* **\[ \<(** *\<verb\>* **)- {** *\<storm\>* **}** \| *\<valu\>* **\]**

> [!NOTE]
> The minus sign ( `-` ) used with a light edge **outside** any edit brackets simply instructs Storm to traverse (walk) the specified light edge (see [Traversal Operations](storm_ref_pivot.md#storm-traverse)). The minus sign used with a light edge **inside** edit brackets instructs Storm to **delete** the specified edges.

**Examples:**

Delete the `-(refs)>` light edge linking the MD5 hash of the empty file to the specified `doc:report` node:

``` text
crypto:hash:md5=d41d8cd98f00b204e9800998ecf8427e [ <(refs)- { doc:report:title="report about bad stuff" } ]
```

Delete the `-(used)>` light edge linking the threat cluster Forest Blizzard to the technique "phishing":

``` text
risk:threat:name='forest blizzard' [ -(used)> { meta:technique:name=phishing } ]
```

Delete the `-(refs)>` light edge linking the specified `doc:report` and a node contained in a variable:

``` text
$fqdn={ inet:fqdn=woot.com } doc:report:title="\"It's all WINNTI\", says researcher" [ -(refs)> $fqdn ]
```

> [!TIP]
> In the example above, the document title includes double quotes (`"`), so the backslash (`\`) is needed in order to escape those characters. See [Entering Literals](storm_ref_intro.md#storm-literals) for details on the use of single quotes, double quotes, and escape characters in Storm.

**Usage Notes:**

- The minus sign ( `-` ) used with the light edge expression within the edit brackets is used to delete the light edge(s).
- Light edges can be deleted in either direction (e.g., with the directional arrow pointing either right ( `-(<verb>)>` ) or left ( `<(<verb>)-` ) - whichever syntax is easier.

<a id="tag-add"></a>

## Add Tags

Operation to add one or more tags to the specified node(s).

> [!TIP]
> You can optionally use the ["Try" Operator](storm_ref_data_mod.md#edit-try) ( `+?#` ) when adding tags.

**Syntax:**

*\<query\>* **\[** **+#** \| **+?#** *\<tag\>* ... **\]**

**Examples:**

Add a single tag:

``` text
<inet:ip> [ +#cno.infra.anon.tor.exit ]
```

Add multiple tags:

``` text
<inet:fqdn> [ +#rep.mandiant.apt1 +#cno.infra.dns.sink.holed ]
```

<a id="tag-prop-add"></a>

### Add Tag Timestamps or Tag Properties

Synapse supports the use of [Tag Timestamps](analytical_model.md#tag-timestamps) and [Tag Properties](analytical_model.md#tag-properties) to provide additional context to tags where appropriate.

> [!TIP]
> You can optionally use the ["Try" Operator](storm_ref_data_mod.md#edit-try) when setting or modifying tag timestamps or tag properties.
>
> - When using the try operator with tag timestamps, the operator is used with the tag name ( `+?#<tag>=<time>` or `+?#<tag>=(<min_time>,<max_time>)` ).
> - When using the try operator with a tag property, the operator is used with the tag property value ( `+#<tag>:<tagprop>?=<pval>` ).
>
> Note that the tag and tag timestamp(s) or the tag and tag property are evaluated as a whole; if any part of the tag expression is invalid, the full edit operation will fail. For example, when attempting to add a tag with timestamps where the tag is valid but the timestamp values are not, neither the tag nor the timestamps will be applied.

**Syntax:**

Add tag timestamps:

*\<query\>* **\[ +#** \| **+?#** *\<tag\>* **=** *\<time\>* \| **(** *\<min_time\>* **,** *\<max_time\>* **)** ... **\]**

Add tag property:

*\<query\>* **\[ +#** *\<tag\>* **:** *\<tagprop\>* **=** \| **?=** *\<pval\>* ... **\]**

**Examples:**

Add tag with single timestamp:

``` text
<inet:fqdn> [ +#cno.infra.dns.sink.holed=2018/11/27 ]
```

Add tag with a time interval (min / max):

``` text
<inet:fqdn> [ +#cno.infra.dns.sink.holed=(2014/11/06, 2016/11/06) ]
```

> [!TIP]
> Tag timestamps are interval (`ival`) types. See the [ival](storm_ref_type_specific.md#type-ival) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details on interval behavior and working with intervals.

Add tag with custom tag property and value:

``` text
<inet:fqdn> [ +#rep.symantec:_risk=87 ]
```

> [!TIP]
> Tag properties must be defined and added to the data model before they can be used. See [Tag Properties](analytical_model.md#tag-properties) for additional information.

**Usage Notes:**

- [Tag Timestamps](analytical_model.md#tag-timestamps) and [Tag Properties](analytical_model.md#tag-properties) are applied only to the tags to which they are explicitly added. For example, adding a timestamp to the tag `#foo.bar.baz` does **not** add the timestamp to tags `#foo.bar` and `#foo`.

<a id="tag-mod"></a>

## Modify Tags

Tags are "binary" in that they are either applied to a node or they are not. Tag names cannot be changed once set. To "change" the tag applied to a node, you must add the new tag and delete the old one.

> [!TIP]
> The Storm [movetag](storm_ref_cmd.md#storm-movetag) command can be used to modify tags in bulk - that is, migrate an entire set of tags (i.e., effectively "rename" the tags by creating and applying new tags and removing the old ones) or move a tag to a different tag tree.

<a id="tag-prop-mod"></a>

### Modify Tag Timestamps or Tag Properties

Tag timestamps or tag properties can be modified using the same syntax used to add the timestamp or property.

> [!TIP]
> Tag timestamps are interval (`ival`) types. See the [ival](storm_ref_type_specific.md#type-ival) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details on interval behavior when modifying interval values.

<a id="tag-del"></a>

## Remove Tags

Operation to delete one or more tags from the specified node(s).

Removing a tag from a node differs from deleting the node representing a tag (a `syn:tag` node), which can be done using the Storm [delnode](storm_ref_cmd.md#storm-delnode) command.

**Syntax:**

*\<query\>* **\[ -#** *\<tag\>* ... **\]**

**Examples:**

Remove a leaf tag (i.e., the final or rightmost element of the tag):

``` text
<inet:ip> [ -#cno.infra.anon.tor.exit ]
```

Remove a full tag (i.e., the entire tag):

``` text
<inet:ip> [ -#cno ]
```

**Usage Notes:**

- Deleting a leaf tag deletes **only** the leaf tag from the node. For example, `[ -#foo.bar.baz ]` will delete the tag `#foo.bar.baz` but leave the tags `#foo.bar` and `#foo` on the node.
- Deleting a non-leaf tag deletes that tag and **all tags below it in the tag hierarchy** from the node. For example, `[ -#foo ]` used on a node with tags `#foo.bar.baz` and `#foo.hurr.derp` will remove **all** of the following tags:
  - `#foo.bar.baz`
  - `#foo.hurr.derp`
  - `#foo.bar`
  - `#foo.hurr`
  - `#foo`

> [!TIP]
> The Storm [tag.prune](storm_ref_cmd.md#storm-tag-prune) command can be used to recursively remove tags (i.e., from a leaf tag up through parent tags that do not have other children).

<a id="tag-time-del"></a>

### Remove Tag Timestamps

To remove a tag timestamp from a tag, you must remove the tag element that contains the timestamp. The tag element can be re-added without the timestamp if needed.

<a id="tag-prop-del"></a>

### Remove Tag Properties

Removing a tag property deletes the property and any property value. The tag element to which the property was appended will remain.

**Syntax:**

Remove a tag property:

*\<query\>* **\[ -#** *\<tag\>* **:** *\<tagprop\>* ... **\]**

**Example:**

Remove the custom tag property `:_risk` from a tag:

``` text
<inet:fqdn> [ -#rep.symantec:_risk ]
```

<a id="data-mod-combo"></a>

## Combining Data Modification Operations

Storm allows you to perform multiple edits within a single edit operation (set of edit brackets).

### Simple Examples

Create a node and add secondary properties:

``` text
[ inet:ip=94.75.194.194 :place:loc=nl :asn=60781 ]
```

Create a node and add a tag:

``` text
[ inet:fqdn=blackcake.net +#rep.mandiant.apt1 ]
```

### Edit Brackets and Edit Parentheses Examples

Edit parentheses can be used within edit brackets to isolate edit operations (e.g., so a particular edit does not apply to all inbound nodes).

The following examples illustrate the differences in Storm behavior when using [Edit Brackets](storm_ref_data_mod.md#edit-brackets) alone vs. with [Edit Parentheses](storm_ref_data_mod.md#edit-parens).

When performing simple edit operations (i.e., Storm queries that add / modify a single node, or apply a tag to the nodes retrieved by a Storm lift operation) users can generally use edit brackets alone without delimiting edit operations within additional edit parentheses (edit parens).

Edit parens may be necessary when creating and modifying multiple nodes in a single query, or performing edits within a longer or more complex Storm query. In these cases, understanding the difference between edit brackets' "operate on everything inbound" vs. edit parens' "limit modifications to the specified nodes" is critical to avoid unintended data modifications.

**Example 1:**

Consider the following Storm query that uses only edit brackets:

``` text
inet:fqdn#rep.mandiant.apt1 [ inet:fqdn=somedomain.com +#rep.eset.sednit ]
```

The query will:

- Lift all domains that Mandiant associates with APT1 (`#rep.mandiant.apt1`).
- Create the new domain `somedomain.com` (if it does not already exist) or lift it (if it does).
- Apply the tag `#rep.eset.sednit` to the domain `somedomain.com` **and** to all of the domains tagged `#rep.mandiant.apt1` (because those FQDNs are inbound to the edit operation / edit brackets).

We can see the effects in the output of our example query. All of the FQDNs tagged `#rep.mandiant.apt1` are also tagged `#rep.eset.sednit`:

```stormdoc
storm> inet:fqdn#rep.mandiant.apt1 [ inet:fqdn=somedomain.com +#rep.eset.sednit ]
inet:fqdn=newsonet.net
        :domain = net
        :host = newsonet
        :issuffix = false
        :iszone = true
        :zone = newsonet.net
        #rep.eset.sednit
        #rep.mandiant.apt1
inet:fqdn=staycools.net
        :domain = net
        :host = staycools
        :issuffix = false
        :iszone = true
        :zone = staycools.net
        #rep.eset.sednit
        #rep.mandiant.apt1
inet:fqdn=hugesoft.org
        :domain = org
        :host = hugesoft
        :issuffix = false
        :iszone = true
        :zone = hugesoft.org
        #rep.eset.sednit
        #rep.mandiant.apt1
inet:fqdn=purpledaily.com
        :domain = com
        :host = purpledaily
        :issuffix = false
        :iszone = true
        :zone = purpledaily.com
        #rep.eset.sednit
        #rep.mandiant.apt1
inet:fqdn=blackcake.net
        :domain = net
        :host = blackcake
        :issuffix = false
        :iszone = true
        :zone = blackcake.net
        #cno.infra.dns.sink.holed
        #rep.eset.sednit
        #rep.mandiant.apt1
inet:fqdn=somedomain.com
        :domain = com
        :host = somedomain
        :issuffix = false
        :iszone = true
        :zone = somedomain.com
        #rep.eset.sednit
```

Consider the same query using edit parens inside the brackets:

``` text
inet:fqdn#rep.mandiant.apt1 [ ( inet:fqdn=somedomain.com +#rep.eset.sednit ) ]
```

Because we used the edit parens, the query will:

- Lift all domains that Mandiant associates with APT1.
- Create the new domain `somedomain.com` (if it does not already exist) or lift it (if it does).
- Apply the tag `rep.eset.sednit` **only** to the domain `somedomain.com`.

We can see the difference in the output of the example query. Only the FQDN `somedomain.com` was tagged `#rep.eset.sednit`:

```stormdoc
storm> inet:fqdn#rep.mandiant.apt1 [ ( inet:fqdn=somedomain.com +#rep.eset.sednit ) ]
inet:fqdn=newsonet.net
        :domain = net
        :host = newsonet
        :issuffix = false
        :iszone = true
        :zone = newsonet.net
        #rep.mandiant.apt1
inet:fqdn=staycools.net
        :domain = net
        :host = staycools
        :issuffix = false
        :iszone = true
        :zone = staycools.net
        #rep.mandiant.apt1
inet:fqdn=hugesoft.org
        :domain = org
        :host = hugesoft
        :issuffix = false
        :iszone = true
        :zone = hugesoft.org
        #rep.mandiant.apt1
inet:fqdn=purpledaily.com
        :domain = com
        :host = purpledaily
        :issuffix = false
        :iszone = true
        :zone = purpledaily.com
        #rep.mandiant.apt1
inet:fqdn=blackcake.net
        :domain = net
        :host = blackcake
        :issuffix = false
        :iszone = true
        :zone = blackcake.net
        #cno.infra.dns.sink.holed
        #rep.mandiant.apt1
inet:fqdn=somedomain.com
        :domain = com
        :host = somedomain
        :issuffix = false
        :iszone = true
        :zone = somedomain.com
        #rep.eset.sednit
```

**Example 2:**

Consider the following Storm query that uses only edit brackets:

``` text
[ inet:ip=1.2.3.4 :asn=1111 inet:ip=5.6.7.8 :asn=2222 ]
```

The query will:

- Create (or lift) the IP address `1.2.3.4`.
- Set the IP's `:asn` property to `1111`.
- Create (or lift) the IP address `5.6.7.8`.
- Set the `:asn` property for **both** IP addresses to `2222`.

We can see the effects in the output of our example query. Both IPs have the ASN `2222`:

```stormdoc
storm> [ inet:ip=1.2.3.4 :asn=1111 inet:ip=5.6.7.8 :asn=2222 ]
inet:ip=1.2.3.4
        :asn = 2222
        :type = unicast
        :version = 4
inet:ip=5.6.7.8
        :asn = 2222
        :type = unicast
        :version = 4
```

Consider the same query using edit parens inside the brackets:

``` text
[ ( inet:ip=1.2.3.4 :asn=1111 ) ( inet:ip=5.6.7.8 :asn=2222 ) ]
```

Because the edit parens separate the two sets of modifications, IP `1.2.3.4` has its `:asn` property set to `1111` while IP `5.6.7.8` has its `:asn` property set to `2222`:

```stormdoc
storm> [ ( inet:ip=1.2.3.4 :asn=1111 ) ( inet:ip=5.6.7.8 :asn=2222 ) ]
inet:ip=1.2.3.4
        :asn = 1111
        :type = unicast
        :version = 4
inet:ip=5.6.7.8
        :asn = 2222
        :type = unicast
        :version = 4
```
