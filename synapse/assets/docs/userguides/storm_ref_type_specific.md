<a id="storm-ref-type-specific"></a>

# Storm Reference - Type-Specific Storm Behavior

Some data [types](../glossary.md#gloss-type) within Synapse have additional optimizations. These include optimizations for:

- indexing (how the type is stored for retrieval);
- parsing (how the type can be specified for input);
- insertion (how the type can be used to create or modify nodes);
- operations (how the type can be lifted, filtered, or otherwise compared).

Key types that have been optimized in various ways are documented below along with specialized operations that may be available for those types.

> [!TIP]
> The Synapse data model is continually expanding and evolving. This section describes some of the most useful / relevant optimizations, but is **not** a complete reference of all type-specific optimizations, or of all available types, type behaviors, or type enforcement constraints.
>
> For details on all available types see the online [documentation](../datamodel_types.md) or the Synapse source [code](https://github.com/vertexproject/synapse).

- [array](storm_ref_type_specific.md#type-array) (array)
- [duration](storm_ref_type_specific.md#type-duration) (duration)
- [file:bytes](storm_ref_type_specific.md#type-file) (file)
- [guid](storm_ref_type_specific.md#type-guid) (globally unique identifier)
- [inet:fqdn](storm_ref_type_specific.md#type-inet-fqdn) (FQDN)
- [inet:ip](storm_ref_type_specific.md#type-inet-ip) (IP)
- [int](storm_ref_type_specific.md#type-int) (integer)
- [ival](storm_ref_type_specific.md#type-ival) (time interval)
- [loc](storm_ref_type_specific.md#type-loc) (location)
- [str](storm_ref_type_specific.md#type-str) (string)
- [syn:tag](storm_ref_type_specific.md#type-syn-tag) (tag)
- [taxonomy](storm_ref_type_specific.md#type-taxoxnomy) (taxonomy)
- [time](storm_ref_type_specific.md#type-time) (date/time)

<a id="type-array"></a>

## array

An `array` is a specialized type that consists of either a list or a set of typed values. That is, an array is a type that consists of one or more values that are themselves all of a single, defined type.

> [!TIP]
> An array that is a **list** can have duplicate entries in the list. An array that is a **set** consists of a unique group of entries.

`Array` types can be used for secondary properties where that property may have multiple values. Examples of array secondary properties include `doc:report:topics`, `inet:email:message:headers`, and `ps:person:names`. You can view all secondary properties that are `array` types using the following Storm query:

``` text
syn:prop:array=true
```

> [!TIP]
> Some forms include both a singular and an array property for the same type. This allows you to record a primary value along with optional variations (e.g., `ou:org:name` and `ou:org:names`).

**Virtual Properties**

All `array` properties have a `.size` virtual property (e.g., `ou:org:names.size`). The value of `.size` is set by Synapse to the number of array values and cannot be edited by a user.

### Indexing

N/A

### Parsing

Because an `array` is a list or set of typed values, `array` elements can be input in any format supported by the type of the elements themselves. For example, if an `array` consists of `inet:ip` values, the values can be input in any supported `inet:ip` format (e.g., dotted-decimal string, tuple, etc.).

### Insertion

Because an array may contain multiple values, an `array` property must be set using comma-separated values enclosed in parentheses (this is true even if the array contains only a single element; you must still use parentheses, and the single element must still be followed by a trailing comma). Single or double quotes are required in accordance with the standard rules for using [Whitespace and Literals in Storm](storm_ref_intro.md#storm-whitespace-literals).

**Examples:**

Set the `:names` property of an organization (`ou:org`) node to a single value:

```stormdoc
storm> ou:org:name=vertex [ :names=('The Vertex Project',) ]
ou:org=7918de6a997e984dbf966f8002df95ad
        :name = vertex
        :names = ['The Vertex Project']
        :websites = ['https://vertex.link/']
```

Set the `:names` property of an organization (`ou:org`) node to contain multiple variations of the organization name:

```stormdoc
storm> ou:org:name=vertex [ :names=('The Vertex Project', 'The Vertex Project, LLC') ]
ou:org=7918de6a997e984dbf966f8002df95ad
        :name = vertex
        :names = ['The Vertex Project', 'The Vertex Project, LLC']
        :websites = ['https://vertex.link/']
```

> [!WARNING]
> Using the equals ( `=` ) operator to set an array property value will set or update (overwrite) the **entire** property value. To add or remove individual elements from an array, use the `+=`, `-=`, `++=`, or `--=` operators.

Add a name to the array of names associated with an organization:

```stormdoc
storm> ou:org:name='Monty Python' [ :names+='The Spanish Inquisition' ]
ou:org=96df93d36ef3399ca05a49a3e8a3e3ad
        :name = Monty Python
        :names = ["Monty Python's Flying Circus", 'The Spanish Inquisition']
```

Remove a name from the array of names associated with an organization:

```stormdoc
storm> ou:org:name='Monty Python' [ :names-='The Spanish Inquisition' ]
ou:org=96df93d36ef3399ca05a49a3e8a3e3ad
        :name = Monty Python
        :names = ["Monty Python's Flying Circus"]
```

Add multiple values to the array of names associated with an organization:

```stormdoc
storm> ou:org:name='Monty Python' [ :names ++= ('The Spanish Inquisition', 'Spamalot') ]
ou:org=96df93d36ef3399ca05a49a3e8a3e3ad
        :name = Monty Python
        :names = ["Monty Python's Flying Circus", 'Spamalot', 'The Spanish Inquisition']
```

Remove multiple values from the array of names associated with an organization:

```stormdoc
storm> ou:org:name='Monty Python' [ :names --= ('The Spanish Inquisition', 'Spamalot') ]
ou:org=96df93d36ef3399ca05a49a3e8a3e3ad
        :name = Monty Python
        :names = ["Monty Python's Flying Circus"]
```

> [!TIP]
> The standard "edit try" operator ( `?=` ) (see ["Try" Operator](storm_ref_data_mod.md#edit-try) in the [Storm Reference - Data Modification](storm_ref_data_mod.md#storm-ref-data-mod)) can be used to attempt to set a **full** array property value where you are unsure whether the value will succeed. The specialized `?+=` or `?-=` operators can be used to attempt to add or remove a **single** array value in a similar manner. The `?++=` and `?--=` operators can be used to attempt to add or remove multiple values from an array value, ignoring any items which fail to normalize.

Use the edit try operator to attempt to add a single value to the `:emails` array property of a set of contact information (an `entity:contact` node). (An invalid email address is used below to show the "fail silently" behavior for the edit try operator.)

```stormdoc
storm> entity:contact:name='ron the cat' [ :emails?+='ron[at]protonmail.com' ]
entity:contact=eb141bade0f7833c7998d9871f7dd871
        :emails = ['ron@vertex.link']
        :name = ron the cat
        :type = vertex.employee
```

**Usage Notes:**

- When using the standard edit try operator ( `?=` ) to attempt to set the **full** value of an array property (vs. adding or removing an element from an array), the **entire** attempt will fail if **any** value in the list of values fails. For example, if you try to set `[ :identities:emails?=(alice@vertex.link, bob) ]` on an X509 certificate (`crypto:x509:cert`), Synapse will fail to set the property altogether because `bob` is not a valid email address (even though `alice@vertex.link` is).
- The edit try operators for **removing** elements from an array ( `?-=` or `?--=` ) are unique to arrays as arrays are the only type that allows removal of individual elements from a property. (Properties with a single value are either set, modified (updated), or the property is deleted altogether.) As with other uses of edit try, use of the operator allows the operation to silently fail (vs. error and halt) if the operation attempts to remove a value from an array that does not match the array's defined type. For example, attempting to remove an IP from an array of email addresses will halt with a `BadTypeValu` error if the standard remove operator ( `-=`) is used, but silently fail (do nothing and continue) if the edit try version ( `?-=`) is used.

### Operations

#### Lifting and Filtering

Lifting or filtering array properties using the equals ( `=` ) operator requires an **exact match** of the full array property value. This is often infeasible for arrays because lifting by the full array value requires you to know the exact values of each of the array elements as well as their exact order:

```stormdoc
storm> ou:org:names=('The Vertex Project', 'The Vertex Project, LLC')
ou:org=7918de6a997e984dbf966f8002df95ad
        :name = vertex
        :names = ['The Vertex Project', 'The Vertex Project, LLC']
        :websites = ['https://vertex.link/']
```

For this reason, Storm offers a special syntax for lifting and filtering with `array` types. The syntax consists of an asterisk ( `*` ) followed by a set of square brackets ( `[ ]` ), where the square brackets contain a comparison operator and a value that can match one or more elements in the array. This allows users to match elements in the array similarly to how they would match individual property values.

> [!NOTE]
> The square brackets used to lift or filter based on values in an array should not be confused with square brackets used to add or modify nodes or properties in [Edit Mode](storm_ref_data_mod.md#edit-mode).

**Examples:**

Lift the `ou:org` node(s) whose `:names` property contains a name that exactly matches `the vertex project`:

```stormdoc
storm> ou:org:names*[='the vertex project']
ou:org=7918de6a997e984dbf966f8002df95ad
        :name = vertex
        :names = ['The Vertex Project', 'The Vertex Project, LLC']
        :websites = ['https://vertex.link/']
```

Lift the `ou:org` node(s) whose `:names` property contains a name that includes the string `vertex`:

```stormdoc
storm> ou:org:names*[~=vertex]
ou:org=7918de6a997e984dbf966f8002df95ad
        :name = vertex
        :names = ['The Vertex Project', 'The Vertex Project, LLC']
        :websites = ['https://vertex.link/']
ou:org=7918de6a997e984dbf966f8002df95ad
        :name = vertex
        :names = ['The Vertex Project', 'The Vertex Project, LLC']
        :websites = ['https://vertex.link/']
```

> [!TIP]
> The above query returns two instances of the same `ou:org` node because both values in the `:names` array match the queried string - there are two matches, so the node is returned twice.

Lift the x509 certificate nodes that reference the domain `microsoft.com`:

```stormdoc
storm> crypto:x509:cert:identities:fqdns*[=microsoft.com]
crypto:x509:cert=1239ca963e0bf5801029ee309279af85
        :identities:fqdns = ['microsoft.com', 'office365.com']
        :issuer = CN=Microsoft Certificate Authority
        :sha256 = 6b60c1c833979494caff32bf02391793ac85f533516367f12a1cea857bbacba7
```

Filter a set of articles (`doc:report` nodes) by Proofpoint to include only those with a topic that starts with "cyber":

```stormdoc
storm> doc:report:publisher:name=proofpoint +:topics*[^=cyber]
doc:report=35f46fad2d9c564cd9f6164b15a65ae3
        :publisher:name = proofpoint
        :title = more things happened today
        :topics = ['cybersecurity', 'zero trust']
doc:report=8856a1e346dbac855fc30a8e1478bf8a
        :publisher:name = proofpoint
        :title = report about stuff
        :topics = ['cybercrime', 'ransomware']
```

See [Lift by (Arrays) (*[ ])](storm_ref_lift.md#lift-by-arrays) and [Filter by (Arrays) (*[ ])](storm_ref_filter.md#filter-by-arrays) for additional details.

#### Pivoting

Synapse and Storm are type-aware and will facilitate pivoting between properties of the same type. This includes pivoting between individual typed properties and array properties consisting of those same types. Type awareness for arrays includes both standard form and property pivots as well as wildcard pivots.

**Examples:**

Pivot from a set of x509 certificate nodes to the set of domains referenced by the certificates (such as in the `:identities:fqdns` array property):

```stormdoc
storm> crypto:x509:cert -> inet:fqdn
inet:fqdn=microsoft.com
        :domain = com
        :host = microsoft
        :issuffix = false
        :iszone = true
        :zone = microsoft.com
inet:fqdn=office365.com
        :domain = com
        :host = office365
        :issuffix = false
        :iszone = true
        :zone = office365.com
```

Pivot from a set of `entity:name` nodes to any nodes that reference those names (e.g., `ou:org` nodes where the `entity:name` is present in the `:name` property or `:names` array):

```stormdoc
storm> entity:name^=ministry <- *
ou:org=e365491864a971d208683af6d0c5258a
        :name = valisministeerium
        :names = ['ministry of foreign affairs of estonia']
ou:org=d9a396b7dbd4be115c04961f650a239c
        :name = ministry of public security
        :names = ['mps']
```

<a id="type-duration"></a>

## duration

`duration` is a type that represents a period (length) of time.

You can view all secondary properties that include `duration` types using the following Storm query:

``` text
syn:prop:type*[=duration]
```

In addition, all properties that are interval ([ival](storm_ref_type_specific.md#type-ival)) types have a `.duration` virtual property.

### Indexing

A `duration` is stored as an integer value representing the number of microseconds.

### Parsing

A `duration` is commonly specified using a string value (days / hours / minutes / seconds / microseconds as appropriate) with the following notation:

`##D hh:mm:ss.mmmmmm`

The literal uppercase letter `D` is used to represent the number of days. When entering a duration value as a string, single or double quotes are required in accordance with the standard rules for using [Whitespace and Literals in Storm](storm_ref_intro.md#storm-whitespace-literals).

A `duration` can also be specified as the number of microseconds expressed as an integer value enclosed in parentheses:

`(218262777)`

> [!TIP]
> Similar to [time](storm_ref_type_specific.md#type-time) types, Synapse expects users to enter duration values using human-friendly strings, and will attempt to parse the input as such. Using parentheses tells Synapse to interpret the value as a raw integer.
>
> Note that this parentheses syntax only applies when setting or updating a `duration` property using Storm. When setting or updating a property in the [Optic UI](/docs/synapse-enterprise-optic/latest/index.md) by editing a field, you must enter a duration string value.

### Insertion

When setting a `duration` value, enter the value using either format above.

**Examples:**

Set the initial connection delay (`:connect:delay`) for the command and control (C2) configuration (`it:sec:c2:config`) for a malicious software sample to 17 minutes:

```stormdoc
storm> it:sec:c2:config:family=redtree [ :connect:delay=00:17:00 ]
it:sec:c2:config=d55ce84c26e688c9739c96398f289788
        :connect:delay = 00:17:00
        :family = redtree
        :file = f46d3ee70e8824a45370cbeed445289f
```

Set the duration of a compromise (`risk:compromise` node) to six days, six hours, 46 minutes, and 23 seconds:

```stormdoc
storm> risk:compromise:name='example compromise' [ :period.duration='6D 06:46:23' ]
risk:compromise=7e85e3476e8c18bdbf6aec4289361a68
        :name = example compromise
        :period = ? - ?
        :reporter:name = vertex
```

Or:

```stormdoc
storm> risk:compromise:name='example compromise' [ :period.duration=(542783000000) ]
risk:compromise=7e85e3476e8c18bdbf6aec4289361a68
        :name = example compromise
        :period = ? - ?
        :reporter:name = vertex
```

**Usage Notes:**

- Duration values can be set at any level of granularity; e.g., `[ :duration=19D ]` is acceptable, as are values to microsecond resolution.
- In the example above, `.duration` is a virtual property of `risk:compromise:period`, which is an interval (`ival`) type. See the [ival](storm_ref_type_specific.md#type-ival) section below for a detailed discussion of `ival` types, including their virtual properties (`.min`, `.max`, `.duration`, `.precision`) and related behaviors.

### Operations

As `duration` types are stored as integers, they support any operations suitable for integer values. This includes:

- comparison using mathematical operators (such as greater than ( `>`));
- finding low or high values using the [min](storm_ref_cmd.md#storm-min) or [max](storm_ref_cmd.md#storm-max) commands;
- use of the range ( `*range=` ) comparison operator;

...etc.

In addition, arithmetic on typed values preserves the `duration` type:

- adding or subtracting two `duration` values yields a `duration`;
- multiplying a `duration` by an integer yields a `duration`;
- adding a `duration` to a `time` yields a new `time` (see [time](storm_ref_type_specific.md#type-time)).

<a id="type-file"></a>

## file:bytes

Files (`file:bytes`) nodes are [guid](storm_ref_type_specific.md#type-guid) forms and are subject to the same type-specific behaviors as other `guid` nodes.

### Indexing

N/A

### Parsing

N/A

### Insertion

We recommend using [Dictionary Syntax](storm_ref_type_specific.md#guid-dictionary) and the file's SHA256 hash for [deconfliction](storm_ref_type_specific.md#guid-best-practices) purposes. (Generating MD5 hash collisions is trivial and SHA1 collisions are feasible, so these hashes are insufficiently unique for reliable deconfliction.)

Synapse will automatically create a `file:bytes` node when any file is loaded into the Cortex. (Synapse's Axon storage must be configured and enabled in order to upload files). Synapse will deconflict or add the file based on the SHA256 hash, and calculate and set the file's size and other hash properties.

> [!TIP]
> Files ingested directly into a storage Axon will not automatically create corresponding `file:bytes` nodes in the Cortex.

Files can be ingested programmatically (such as via a Synapse [Power-Up](../glossary.md#gloss-power-up)). Other options include:

- the built-in Synapse [wget](storm_ref_cmd.md#storm-wget) command;
- the **Upload File** menu option available from the [Optic UI](/docs/synapse-enterprise-optic/latest/index.md), which allows you to either upload a file from local disk, or download a file from a specified URL; or
- the <span class="title-ref">[axon.put](syn_tools_axon_put.md#syn-tools-axon-put) tool, available from the CLI in the community version of Synapse, which loads a file into the Axon and optionally creates the corresponding </span><span class="title-ref">file:bytes</span>\` node.

Similarly, Storm's HTTP library ([stormlibs-lib-inet-http](../stormtypes_libs.md#stormlibs-lib-inet-http)) could be leveraged to retrieve a web-based file and use the returned bytes as input (potentially using Storm variables - see [Storm Reference - Advanced - Variables](storm_adv_vars.md#storm-adv-vars)) to the `guid` generator. A detailed discussion of this method is beyond the scope of this section; see the [stormtypes-libs-header](../stormtypes_libs.md#stormtypes-libs-header) technical documentation for additional detail.

### Operations

N/A

<a id="type-guid"></a>

## guid

Within Synapse, the Globally Unique Identifier (`guid`) [Type](data_model.md#data-type) refers to a 128-bit value used as a form's primary property. The value is represented in hex (e.g., `4b0c2c5671874922ce001d69215d032f`).

The term should not be confused with the definition of GUID used by [Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/guiddef/ns-guiddef-guid), or with other types of [identifiers](../glossary.md#gloss-iden) used within Synapse.

The `guid` type is used as the primary property for forms that cannot be uniquely defined by a set of property values. See the background documents on the Synapse data model for additional details on the [Guid Form](data_model.md#form-guid).

### Indexing

N/A

### Parsing

It is impractical to manually type a guid value when lifting or otherwise specifying a guid form. While a guid can be specified by a sufficiently unique prefix (e.g., `ou:org^=4b0c2`), it is more common to reference a guid node using a more human-friendly secondary property. For example:

```stormdoc
storm> ou:org:name=vertex
ou:org=7918de6a997e984dbf966f8002df95ad
        :name = vertex
        :names = ['The Vertex Project', 'The Vertex Project, LLC']
        :websites = ['https://vertex.link/']
```

Alternatively, the guid value can be copied and pasted.

<a id="guid-type-insertion"></a>

### Insertion

There are multiple ways to create guid nodes in Synapse. The critical consideration when deciding which method is best for your use case is how (or whether) you can **deconflict** guid nodes.

<a id="guid-best-practices"></a>

#### Deconfliction

Synapse uses **deconfliction** when nodes are created to ensure that all nodes of a given form are unique within a Cortex - that is, you do not have multiple nodes in Synapse that represent the same thing.

Deconfliction is based on a node's primary property value. When you attempt to create a node such as an email address, Synapse checks to see whether an `inet:email` node with the specified value already exists. If so, Synapse simply returns the existing node; otherwise, Synapse creates a new node:

```stormdoc
storm> [ inet:email=training@vertex.link ]
inet:email=training@vertex.link
        :fqdn = vertex.link
        :username = training
```

Guid forms are notable in that their primary property - a 128-bit value represented in hex - has no obvious relationship to whatever the form represents. For example, the primary property of an organization node (e.g., `ou:org=0efcf9b86fa373fab26112f2b29b94ca`) does not tell you anything about the organization itself, such as its name, location, or URL. This means that guids are useful for guaranteeing that nodes are **unique** (you cannot create two different `ou:org` nodes in Synapse with the same guid), but less useful for **deconfliction**.

Most importantly, it is still possible for users or processes to inadvertently create multiple guid nodes that represent the same thing:

```stormdoc
storm> ou:org:name='the vertex project'
ou:org=41297aa13d003417d229d76a80cfcbdf
        :name = the vertex project
        :websites = ['https://vertex.link/']
ou:org=fe45477715b3e95d8276cf4a78759a4e
        :name = the vertex project
        :websites = ['https://vertex.link/']
```

The nodes above have different guid values - they are unique and have been deconflicted based on their primary property. But looking at the secondary properties, it is clear (to a human) that both `ou:org` nodes are meant to represent The Vertex Project - this is a problem, because we do not want two different nodes for one organization.

With guid nodes, it is their **secondary properties** that provide meaningful information about the node. In order to avoid creating two guid nodes that represent the same thing, you may need to check the secondary properties of existing nodes before creating new ones. This process is called **secondary property deconfliction**.

> [!NOTE]
> When creating guid nodes, [Dictionary Syntax](storm_ref_type_specific.md#guid-dictionary) is preferred where possible. [Predictable Guids](storm_ref_type_specific.md#guid-predictable) and [Arbitrary Guids](storm_ref_type_specific.md#guid-arbitrary) can also be used, but you should consider their pros / cons and appropriate use cases.

<a id="guid-dictionary"></a>

#### Dictionary Syntax

Dictionary guid constructor syntax ("dictionary syntax" for short) is the preferred method for creating guid nodes. This method will:

- perform secondary property deconfliction using specified values;
- generate a predictable guid; and
- automatically set some secondary property values when creating a new node.

> [!TIP]
> Dictionary guid constructor syntax is referred to as **dictionary syntax** for simplicity. You may also encounter the term **guid constructor** or its shortened form, **gutor**. Although there are multiple ways to construct a guid (as described below), the terms guid constructor and gutor refer specifically to dictionary guid constructor syntax.

Dictionary syntax uses a JSON dictionary with a set of `key:value` pairs to deconflict and create guid nodes. The `key:value` pairs are secondary property names and values to deconflict on.

Synapse will perform secondary property deconfliction using the property names and values in the dictionary, and will return the node if found. Otherwise, Synapse creates a new node (using the dictionary to generate a predictable guid) and sets the property values specified in the dictionary.

> [!NOTE]
> A **predictable** guid is one that can be generated consistently - that is, the same data will result in the same guid each time. They may also be referred to as stable, repeatable, or re-encounterable guids. (Contrast this with [Arbitrary Guids](storm_ref_type_specific.md#guid-arbitrary), below.)

**Example:**

You want to create an organization node for The Vertex Project, deconflicting on the company name and email.

```stormdoc
storm> [ ou:org=( { "name": "the vertex project", "email": "info@vertex.link" } ) ]
ou:org=4d6e7a274a2cb69edf7d01922b85fdc7
        :email = info@vertex.link
        :name = the vertex project
```

In the query above:

- the square brackets ( `[ ]` ) are the Storm edit brackets.
- the parentheses ( `( )` ) denote Storm [Expression Syntax](../glossary.md#gloss-expression-syntax) - that the contents are an expression that should be evaluated in some way. In this case, it causes the content to be parsed as a JSON dictionary.
- the curly braces ( `{ }` ) and their contents are the JSON dictionary.

Note that dictionary syntax is "model aware" - because the `key:value` pairs are property names and values, Synapse can use this information to set the listed properties, including normalizing the values if necessary.

> [!TIP]
> Synapse implements several Storm commands known as generator ("gen") commands. These commands use dictionary syntax "under the hood" to deconflict and create some common guid nodes. (See the [gen](storm_ref_cmd.md#storm-gen) section in the [Storm Reference - Storm Commands](storm_ref_cmd.md#storm-ref-cmd) for available generator commands (or run `help` from your Synapse CLI).)

**Notes:**

- Dictionary syntax will automatically deconflict on "primary" and "alternate" secondary properties, where appropriate. For example in the query above, Synapse will check both the `:name` and `:names` properties of existing `ou:org` nodes for the value `'the vertex project'`, even though only `"name"` is included in the dictionary.
- When choosing secondary properties to deconflict on (particularly for automated or bulk ingest), you should:
  - Select properties that are unique enough to allow deconfliction. For example, an organization's name is reasonably unique; its location (`:loc`) is probably not.
  - Select properties that will always be present in your source data. If a property is not present, you can't use it to deconflict or create a node.
  - If you ingest data about the same objects (for example, organizations or TLS certificates) from multiple data sources and need to deconflict across all of them, select properties that will be present in all of the sources.
- Deconfliction is performed using the full set of properties provided in the JSON dictionary; Synapse will look for an existing node that has **all** of the listed values. When choosing `key:value` pairs for the dictionary, we recommend using the minimum number of entries needed to uniquely identify / deconflict a node. If you use too many values, you may fail to identify an existing node if it has only some of those values set.
- You can use literals or variables within the JSON dictionary:

```stormdoc
storm> [ ou:org=( { "name": "the vertex project", "email": "info@vertex.link" } ) ]
ou:org=4d6e7a274a2cb69edf7d01922b85fdc7
        :email = info@vertex.link
        :name = the vertex project
```

```stormdoc
storm> $name='the vertex project' $email=info@vertex.link [ ou:org=( { "name": $name, "email": $email } ) ]
ou:org=4d6e7a274a2cb69edf7d01922b85fdc7
        :email = info@vertex.link
        :name = the vertex project
```

- When creating a new node using dictionary syntax, Synapse uses an algorithm (the guid generator or "guid grinder") to generate a predictable guid using the dictionary content as input. The dictionary is converted to a sorted (alphabetical) list of `(<key>, <normalized value>)` tuples that are fed to the algorithm (the same algorithm is implemented by the `$lib.guid()` library (see [stormlibs-lib-guid](../stormtypes_libs.md#stormlibs-lib-guid)).

  Given the following query in dictionary syntax:

  ``` text
  [ ou:org=( { "name": "The Vertex Project", "email": "info@vertex.link" } ) ]
  ```

  ...the dictionary is converted to the following list of tuples for purposes of creating a predictable guid:

  ``` text
  [ ou:org=( (email, info@vertex.link), (name, 'the vertex project') ) ]
  ```

  The tuples within the outermost parentheses are fed to the algorithm to create the guid. The dictionary values are **normalized** based on their type ("The Vertex Project" is normalized to lowercase in the tuple) and the tuples are sorted alphabetically by key. The algorithm simply interprets the tuples as a set of ordered strings for purposes of generating the guid value.

- You can use the values of `array` type properties for deconfliction, but the dictionary value to deconflict on must include **all** values present in the array. In other words, if your dictionary includes one array value in the `key:value` pair but the existing node has three values for that property, deconfliction will fail.

Let's say you want to deconflict an `ou:org` node using the organization's FQDN (from the `:dns:mx` array property). Consider the following existing node:

```stormdoc
storm> ou:org:name='the vertex project'
ou:org=4d6e7a274a2cb69edf7d01922b85fdc7
        :dns:mx = ['vertex.link', 'vtx.lk']
        :email = info@vertex.link
        :name = the vertex project
```

The following dictionary syntax identifies and lifts the existing node (note the guid value), because **both** MX FQDNs in the JSON dictionary are present on the existing node:

```stormdoc
storm> [ ou:org=( { "name": "the vertex project", "dns:mx": [ "vtx.lk", "vertex.link" ] } ) ]
ou:org=4d6e7a274a2cb69edf7d01922b85fdc7
        :dns:mx = ['vertex.link', 'vtx.lk']
        :email = info@vertex.link
        :name = the vertex project
```

In contrast, the following dictionary syntax only contains one of the `:dns:mx` values, so fails to deconflict and creates a new node with a different guid:

```stormdoc
storm> [ ou:org=( { "name": "vertex", "dns:mx": [ "vertex.link" ] } )  ]
ou:org=8621515203b49ce5a95800989f9a783b
        :dns:mx = ['vertex.link']
        :name = vertex
```

<a id="guid-dictionary-special-keys"></a>

### Special Keys

Dictionary syntax recognizes the following special `$`-prefixed keys in addition to the property names used for deconfliction. These keys are reserved and may not be used as property names in the deconfliction dictionary.

**\$as**

`$as` accepts a form name string that names the form the dictionary should construct. By default the form is determined by context: at the top level it is the form being created, and when setting a property it is the form the property's type resolves to. When a property may reference more than one form (for example a property typed by an interface), there is no single form to construct and `$as` is required to name it.

```stormdoc
storm> meta:note:text="example note" [ :creator=( { "$as": "ps:person", "name": "alice liddell" } ) ]
meta:note=ff21a3dc1182a8bd1ad0bc79800513a4
        :creator = 4d2217d714db5e75719c988bf1798895
        :creator:name = alice liddell
        :text = example note
```

The named form must be allowed by the target. If it is not (or it is not a guid form), normalization raises an error, which the `?=` operator and `$try` (see below) suppress. When `$as` is provided where the form is already fixed by context, it must match that form.

**\$props**

`$props` accepts a nested dictionary of property names and values to set on the resolved or created node. Properties listed in `$props` are *not* used for deconfliction, they are only applied after the node is found or created. This is useful for setting properties that should not influence which node is matched.

`$props` also accepts a nested `$try` key (see below) that overrides the top-level `$try` for the `$props` sub-dictionary.

```stormdoc
storm> [ ou:org=( { "name": "vertex project", "$props": { "desc": "a great org", "phone": "15551234567" } } ) ]
ou:org=53dc5b6083904309a43641eb7b74e444
        :desc = a great org
        :name = vertex project
        :phone = +1 (555) 123-4567
```

**Virtual property keys**

Dictionary syntax supports dotted keys of the form `base.virtname` to set **virtual properties** on secondary properties that expose them. Virtual properties are derived pseudo-properties on a type that are not stored independently but affect the underlying value (e.g., `:seen.min`, `:price.currency`).

A dotted key is recognized as a virtual property reference when:

- The portion before the last dot names a real secondary property on the form; *and*
- The portion after the last dot names a known virtual property on that property's type.

Any dotted key that does not match this pattern is treated as an ordinary property name (and will raise `NoSuchProp` if no such property exists).

*Deconfliction-dict virtual keys* -- Virtual keys in the top-level dictionary contribute to the property values used for deconfliction. Whether they affect the **guid** depends on whether the virtual property changes the underlying normalized value of its base property:

- For [ival](storm_ref_type_specific.md#type-ival)-typed properties (e.g., `:seen`), the virtual properties `min`, `max`, `duration`, and `precision` change the ival tuple itself, so two dictionaries with different `.min` values produce **different** guids and therefore different nodes.
- For `econ:price`-typed properties (e.g., `:price`), `currency` and `adjusted` are stored as virt metadata alongside the numeric value. Two dictionaries with the same numeric price but different currencies resolve to the **same** node (the currency is applied to the node on first creation; on re-deconfliction the currency in the deconf dict is not re-applied).

*\`\`\$props\`\` virtual keys* -- Virtual keys in `$props` are applied to the node as if they appeared in the explicit edit syntax (`:price.currency=USD`). The base property's value is seeded from the deconfliction dictionary when necessary (e.g., `$props: {"price.currency": "USD"}` with `price` in the deconfliction dict).

> [!NOTE]
> Virtual property keys are **not** accepted in `$unsets`.

*Example -- econ:price virtual key in the deconfliction dict*:

```stormdoc
storm> [ biz:listing=( { "name": "widget", "price": "10", "price.currency": "usd" } ) ]
biz:listing=d9efd209ec0c275beaae1ae42aa2ac26
        :name = widget
        :price = 10USD
```

*Example -- econ:price virtual key in \`\`\$props\`\`*:

```stormdoc
storm> [ biz:listing=( { "name": "widget2", "price": "5", "$props": { "price.currency": "usd" } } ) ]
biz:listing=e3fd0b6a1d41ad7196f2855d54b65290
        :name = widget2
        :price = 5USD
```

**\$try**

`$try` accepts a boolean (`true` / `false`, default `false`). When `true`, any property in `$props` whose value fails type normalization is silently skipped rather than raising an error. It has no effect on properties in the deconfliction dictionary or on `$unsets` constraint validation.

```stormdoc
storm> [ ou:org=( { "name": "vertex project", "$try": true, "$props": { "phone": "not-a-phone-number", "desc": "fine value" } } ) ]
ou:org=53dc5b6083904309a43641eb7b74e444
        :desc = fine value
        :name = vertex project
```

**\$salt**

`$salt` accepts a string value that is mixed into the guid generation algorithm as extra entropy. Two dictionaries that produce the same guid without a salt will produce different guids when different salts are provided. This is useful when you need to model multiple distinct entities that would otherwise collide (e.g., entries from different data sources that share the same deconfliction keys but are not the same entity).

The `$salt` value itself is not stored on the node.

```stormdoc
storm> [ ou:org=( { "name": "salty org", "$salt": "source-a" } ) ]
ou:org=31dcb02de25cf801c504649249da2b51
        :name = salty org
```

**\$unsets**

`$unsets` accepts a list of property names that must not be set on the node for the gutor to match an existing node. If no existing node satisfies the constraint, a new node is created instead. For new nodes, the named properties are absent by default.

This is analogous to the `*unset=` conditional edit operator, where "unset" describes the required state of the property rather than a destructive action.

Each name in `$unsets` must be a valid property on the form. Specifying a property that also appears in the deconfliction dictionary or in `$props` is an error.

```stormdoc
storm> [ ou:org=( { "name": "example org" } ) ]
ou:org=5b35796aed18ace44190dbabb6067ffc
        :name = example org
```

```stormdoc
storm> [ ou:org=( { "name": "example org", "$unsets": ["desc"] } ) ]
ou:org=5b35796aed18ace44190dbabb6067ffc
        :name = example org
```

<a id="guid-predictable"></a>

#### Predictable Guids

You can use the guid generation algorithm described above to create a predictable guid **without** performing secondary property deconfliction.

To create a predictable guid, provide a list of ordered inputs (enclosed in parentheses) that will be used to generate the guid:

```stormdoc
storm> [ ou:org=('the vertex project', 'https://vertex.link/') ]
ou:org=d7f0d5bd78b358a74147995fc9b2e1b2
```

Note that this is a "blank" node with no secondary properties set. Unlike dictionary syntax where the JSON dictionary lists properties and values as `key:value` pairs, the syntax for predictable guids simply provides a list of strings to the algorithm. You can set the properties once the node has been created, or set them as part of your original query:

```stormdoc
storm> [ ou:org=('the vertex project', 'https://vertex.link/') :name='the vertex project' :websites+=https://vertex.link/ ]
ou:org=d7f0d5bd78b358a74147995fc9b2e1b2
        :name = the vertex project
        :websites = ['https://vertex.link/']
```

Secondary property deconfliction (provided by dictionary syntax and described above) is the preferred deconfliction method to avoid duplicate nodes. However, predictable guids may be useful when:

- dictionary syntax is not an option. There may be cases where an object's secondary properties are not unique enough to be used for deconfliction, or data sources are sparse and you cannot identify a set of properties that are guaranteed to be present across all data sources.
- you have a unique data source. In this case, you can use predictable guids to ensure that individual nodes are created in a repeatable way (in case you need to reingest the same data) without worrying about deconfliction (because there is no alternate source for the same data to deconflict with). Examples of this type of unique data include internal log or alert data or reporter-specific data (e.g., nodes with `:reporter` or `:reporter:name` properties) where by definition the reporter is the unique source for that information).

**Notes:**

- The set of inputs must be sufficient to create a unique node. Be sure to choose inputs that will always be present in the data source.
- If the nodes being created are event-based (e.g., include a unique timestamp), then the timestamp should be used as one of the inputs.
- When using this method to deconflict data from a unique (single) data source, we recommend that you include the source (e.g., the name of the data source) as one of the inputs.
- You can specify input values as literals or variables. The guid is generated using the algorithm implemented by the `$lib.guid()` library (see [stormlibs-lib-guid](../stormtypes_libs.md#stormlibs-lib-guid)). All of the following are valid:

```stormdoc
storm> [ ou:org=('the vertex project', https://vertex.link/) ]
ou:org=d7f0d5bd78b358a74147995fc9b2e1b2
```

```stormdoc
storm> $name='the vertex project' $url=https://vertex.link/ [ ou:org=($name, $url) ]
ou:org=d7f0d5bd78b358a74147995fc9b2e1b2
```

```stormdoc
storm> $guid=$lib.guid('the vertex project', https://vertex.link/) [ ou:org=$guid ]
ou:org=d7f0d5bd78b358a74147995fc9b2e1b2
```

```stormdoc
storm> $name='the vertex project' $url=https://vertex.link/ $guid=$lib.guid($name, $url) [ ou:org=$guid ]
ou:org=d7f0d5bd78b358a74147995fc9b2e1b2
```

```stormdoc
storm> $name='the vertex project' $url=https://vertex.link/ [ ou:org=$lib.guid($name, $url) ]
ou:org=d7f0d5bd78b358a74147995fc9b2e1b2
```

- The input to the algorithm is interpreted as a structured list of **string values** (i.e., `(str_0, str_1, str_2...str_n)`). To consistently generate the same guid, each string must be **identical** (note that strings are case sensitive) and in the **same order** each time.

<a id="guid-arbitrary"></a>

#### Arbitrary Guids

You can specify the asterisk ( `*` ) as the primary property value when creating a guid node. This tells Synapse to generate an **arbitrary** guid for the node. For example:

```stormdoc
storm> [ ou:org=* ]
ou:org=9ce42424393cc8143f90dfce9decd3a3
```

Note that this is a "blank" node with no secondary properties set. You can set the properties once the node has been created, or set them as part of your original query:

```stormdoc
storm> [ ou:org=* :name='the vertex project' ]
ou:org=fc937c7bec941ccdf9cc251f8457b0c9
        :name = the vertex project
```

> [!WARNING]
> The guid values created with the asterisk (`*`) are truly arbitrary and no other deconfliction is performed. If you run the query above a second time, Synapse will create a second `ou:org` node with the same `:name` but a **new** arbitrary guid.

Arbitrary guids are the simplest to create (so are often favored for one-off, manual node creation). However, they are the most risky from a deconfliction standpoint. No secondary property deconfliction is used, and the guids that are generated are not predictable.

Using arbitrary guids may be acceptable when:

- you will **never** need to deconflict the data, so the guid value doesn't matter. (It is rare that you never need to deconflict or reingest data, but this may be the case for some highly unique data sets.)
- a user needs to manually create a guid node, and the asterisk ( `*` ) is the simplest means to do so (e.g., if a command or other automation does not exist to help create the kind of node in question).

In particular users (who are most likely to make use of this method due to its simplicity) should understand the risks and trade-offs with respect to deconfliction. Alternatively, users may be able to:

- Make use of Storm generator ("gen") commands, where available. (See the [gen](storm_ref_cmd.md#storm-gen) section in the [Storm Reference - Storm Commands](storm_ref_cmd.md#storm-ref-cmd) for available generator commands (or run `help` from your Synapse CLI).)
- Create other types of automation (macros, node actions, etc.) as appropriate to assist with node creation without needing to know the correct Storm for dictionary syntax or predictable guid syntax.
- If these options are not available, train users to manually check for duplicate nodes before creating a new, arbitrary guid form. (This is "best effort" - even if users remember to check, they will not be able to discover duplicate nodes that may exist in forks or other views that are not visible to the user.)
- Decide to live with the risk. The number of user-created nodes is likely to be small compared to the volume of data ingested through Power-Ups or other automation. Nodes initially created with arbitrary guids may later be "recognized" (and deconflicted appropriately) by automation that uses other guid node creation strategies.

### Operations

Because guid values are unwieldy to use on the command line (outside of copy and paste operations), it is often easier to lift guid nodes by a unique secondary property.

**Examples:**

Lift an org node by its name:

```stormdoc
storm> ou:org:name='foo corporation'
ou:org=911df639e39ea5756ada95e7285c31d2
        :name = foo corporation
```

Lift a DNS request node by the name used in the DNS query:

```stormdoc
storm> inet:dns:request:query:name=pop.seznam.cz
inet:dns:request=e24e2348a8e3ccc2ce7002aaecdb7376
        :query:name = pop.seznam.cz
        :time = 2020-04-30T09:30:33Z
```

It is also possible to lift and filter guid nodes using a "sufficiently unique" prefix match of the guid value.

**Example:**

Lift an `entity:contact` node by a partial prefix match:

```stormdoc
storm> entity:contact^=92a43a
entity:contact=92a43adc904c5e62c4cc80817004c7f5
        :name = ozzie the pony
        :org:name = vertex
        :type = vertex.employee
```

The length of the value that is "sufficiently unique" will vary depending on the data in your instance of Synapse. If your selection criteria matches more than one node, Synapse will return all matches.

When **setting** or **updating** a secondary property that is a guid value, you may use a human-friendly Storm query (specifically a subquery) to reference the node whose primary property (guid value) you wish to set for the secondary property.

**Example:**

Set the `:org` property for an `entity:contact` node to the guid value of the associated `ou:org` node using a Storm query:

```stormdoc
storm> entity:contact:name='ron the cat' [ :org={ ou:org:name='the vertex project' } ]
entity:contact=eb141bade0f7833c7998d9871f7dd871
        :emails = ['ron@vertex.link']
        :name = ron the cat
        :org = fc937c7bec941ccdf9cc251f8457b0c9
        :title = cattribution analyst
        :type = vertex.employee
```

> [!NOTE]
> The Storm query used to specify the guid node must return exactly one node. If the query returns more than one node, or does not return any nodes, Synapse will generate an error.

See [Add or Modify Properties Using Subqueries](storm_ref_data_mod.md#prop-add-mod-subquery) for additional details.

<a id="type-inet-fqdn"></a>

## inet:fqdn

**Fully qualified domain names** (FQDNs) are structured as a set of string elements separated by the dot ( `.` ) character. The Domain Name System acts as a "reverse hierarchy" (operating from right to left instead of from left to right) separated along the dot boundaries - i.e., `com` is the hierarchical root for domains such as `google.com` or `microsoft.com`.

Because of this logical structure, Synapse includes certain optimizations for working with `inet:fqdn` types:

- Reverse string indexing on `inet:fqdn` types.
- Default values for the secondary properties `:issuffix` and `:iszone` of a given `inet:fqdn` node based on the values of those properties for the node's parent domain.

### Indexing

Synapse performs **reverse string indexing** on `inet:fqdn` types. Domains are indexed in full reverse order -that is, the domain `this.is.my.domain.com` is indexed as `moc.niamod.ym.si.siht` to account for the reverse hierarchy implicit in the DNS structure.

### Parsing

N/A

### Insertion

When `inet:fqdn` nodes are created (or modifications to certain properties are made), Synapse uses some built-in logic to set certain secondary properties related to zones of control (specifically, `:issuffix`, `:iszone`, and `:zone`).

The reverse hierarchy implicit in dotted FQDNs represents elements such as `<host>.<domain>.<suffix>`, but can also represent implicit or explicit **zones of control**. The term "zone of control" is loosely defined, and is not meant to represent control or authority by any specific organization or entity. Instead, "zone of control" can be thought of as a boundary within an individual FQDN hierarchy where control of a portion of the domain namespace shifts from one entity or owner to another.

A simple example is the `com` top-level domain (managed by Verisign) vs. the domain `microsoft.com` (controlled by Microsoft Corporation). `Com` represents one zone of control where `microsoft.com` represents another.

The `inet:fqdn` form in the Synapse data model uses several secondary properties that relate to zones of control:

- `:issuffix` = primary zone of control
- `:iszone` = secondary zone of control
- `:zone` = authoritative zone for a given domain or subdomain

**Note**: contrast `:zone` with `:domain` which simply represents the next level "up" in the hierarchy from the current domain.

Synapse uses the following logic for suffixes and zones when an `inet:fqdn` is created:

1.  All domains consisting of a single element (such as `com`, `museum`, `us`, `br`, etc.) are considered **suffixes** and receive the following default values:
    - `:issuffix=1`
    - `:iszone=0`
    - `:zone=<none / property not set>`
    - `:domain=<none / property not set>`
2.  Any domain whose **parent domain is a suffix** is considered a **zone** and receives the following default values:
    - `:issuffix=0`
    - `:iszone=1`
    - `:zone=<set to self>`
    - `:domain=<set to parent domain>`
3.  Any domain whose **parent domain is a zone** is considered a normal subdomain and receives the following default values:
    - `:issuffix=0`
    - `:iszone=0`
    - `:zone=<set to parent domain>`
    - `:domain=<set to parent domain>`
4.  Any domain whose parent domain is a normal subdomain receives the following default values:
    - `:issuffix=0`
    - `:iszone=0`
    - `:zone=<set to first domain "up" the domain hierarchy with :iszone=1>`
    - `:domain=<set to parent domain>`

> [!NOTE]
> The above logic is **recursive** over all nodes in a Cortex. Changing an `:issuffix` or `:iszone` property on an existing `inet:fqdn` node will not only modify that node, but also propagate any changes associated with those properties to any existing subdomains.

#### Potential Limitations

Synapse's default logic works well for single-element top-level domains (TLDs) (such as `com` vs `microsoft.com`). However, it does not address cases that may be relevant for certain types of analysis, such as:

- **Top-level country code domains and their subdomains.** Under Synapse's default logic `uk` is a suffix and `co.uk` is a zone. However, `co.uk` could **also** be considered a suffix in its own right, because subdomains such as `somecompany.co.uk` are under the control of the organization that registers them. In this case, `uk` would be a suffix, `co.uk` could be considered both a suffix **and** a zone, and `somecompany.co.uk` could be considered a zone.
- **Special-case zones of control.** Some domains (such as those used to host web-based services) can be considered specialized zones of control. In these cases, the service provider typically owns the main domain (such as `wordpress.com`) but individual customers can register personal subdomains for their hosted services (such as `joesblog.wordpress.com`). The division between `wordpress.com` and individual customer subdomains could represent different zones of control. In this case, `com` would be a suffix, `wordpress.com` could be considered both a suffix **and** a zone, and `joesblog.wordpress.com` could be considered a zone.

Examples such as these are **not accounted for** by Synapse's default suffix / zone logic. You may need to modify `:issuffix` and / or `:iszone` values on additional FQDNs, depending on your analysis needs. (Once the relevant properties are set, the changes are propagated recursively as noted above).

> [!TIP]
> The [Synapse-PSL](/docs/synapse-psl/latest/index.md) Power-Up can be used to ingest the current Public Suffix list from <https://publicsuffix.org/>.

### Operations

Because of Synapse's reverse string indexing for `inet:fqdn` types, domains can be lifted or filtered based on matching any partial domain suffix string. The asterisk ( `*` ) is the extended operator used to perform this operation. The asterisk does **not** have to be used along dot boundaries but can match anywhere in any FQDN element.

**Examples**

Lift all domains that end with `yahooapis.com`:

```stormdoc
storm> inet:fqdn='*yahooapis.com'
inet:fqdn=ayuisyahooapis.com
        :domain = com
        :host = ayuisyahooapis
        :issuffix = false
        :iszone = true
        :zone = ayuisyahooapis.com
inet:fqdn=micyuisyahooapis.com
        :domain = com
        :host = micyuisyahooapis
        :issuffix = false
        :iszone = true
        :zone = micyuisyahooapis.com
inet:fqdn=usyahooapis.com
        :domain = com
        :host = usyahooapis
        :issuffix = false
        :iszone = true
        :zone = usyahooapis.com
```

Lift all domains ending with `s.wordpress.com`:

```stormdoc
storm> inet:fqdn='*s.wordpress.com'
inet:fqdn=dogs.wordpress.com
        :domain = wordpress.com
        :host = dogs
        :issuffix = false
        :iszone = false
        :zone = wordpress.com
inet:fqdn=sss.wordpress.com
        :domain = wordpress.com
        :host = sss
        :issuffix = false
        :iszone = false
        :zone = wordpress.com
inet:fqdn=www.sss.wordpress.com
        :domain = sss.wordpress.com
        :host = www
        :issuffix = false
        :iszone = false
        :zone = wordpress.com
inet:fqdn=cats.wordpress.com
        :domain = wordpress.com
        :host = cats
        :issuffix = false
        :iszone = false
        :zone = wordpress.com
```

Filter a set of DNS A records to those with domains ending with `.museum`:

```stormdoc
storm> inet:dns:a +:fqdn='*.museum'
inet:dns:a=('woot.museum', '5.6.7.8')
        :fqdn = woot.museum
        :ip = 5.6.7.8
```

**Usage Notes**

- Because the asterisk is a non-alphanumeric character, the string to be matched must be enclosed in single or double quotes (see [Whitespace and Literals in Storm](storm_ref_intro.md#storm-whitespace-literals)).
- Because domains are reverse-indexed instead of prefix indexed, for **lift** operations, partial string matching can only occur based on the end (suffix) of a domain. It is not possible to **lift** FQDNs by prefix. For example, `inet:fqdn^=yahoo` is invalid.
- Domains can be **filtered** by prefix (`^=`). For example, `inet:fqdn='*.biz' +inet:fqdn^=smtp` is valid.
- Domains cannot be **filtered** based on suffix matching (note that a "lift by suffix" is effectively a combined "lift and filter" operation).
- Domains can be lifted or filtered using the regular expression (regex) extended operator (`~=`). For example `inet:fqdn~=google` is valid (see [Lift by Regular Expression (~=)](storm_ref_lift.md#lift-regex) and [Filter by Regular Expression (~=)](storm_ref_filter.md#filter-regex)). Note that lifting by regular expression is a brute-force operation and may be resource-intensive over large data sets; lifting a subset of data by some other method and then filtering by regular expression is preferable where possible.

<a id="type-inet-ip"></a>

## inet:ip

Synapse uses the same form (`inet:ip`) for both IPv4 and IPv6 addresses. IP addresses are stored as tuples of integers where the first integer is the Internet Protocol version (4 or 6) and the second integer is the decimal value of the IP address. IP addresses are represented (displayed) to users as dotted-decimal strings (for IPv4) or colon-separated strings (for IPv6).

### Indexing

IP addresses are indexed as tuples of integers. This optimizes various comparison operations, including greater than / less than, range, etc.

### Parsing

While IP addresses are stored and indexed as tuples of integers, they can be input into Storm (and used within Storm operations) as any of the following.

String: :

``` text
inet:ip=192.168.0.1
```

``` text
inet:ip=2606:4700:3035::ac43:cb25
```

Range: :

``` text
inet:ip=192.168.0.1-192.168.0.10
```

``` text
inet:ip=2606:4700:3035::ac43:cb25-2606:4700:3035::ac43:cb48
```

CIDR notation: :

``` text
inet:ip=192.168.0.0/24
```

``` text
inet:ip=2606:4700:3035:0000:0000:0000:ac43:cb00/120
```

Tuple of version/value integers: :

``` text
inet:ip=([4, 3232235521])
```

``` text
inet:ip=([6, 50543257686979224944580090171408763685])
```

### Insertion

Individual `inet:ip` nodes can be created using any of the input formats described above.

> [!TIP]
> When creating an `inet:ip` node, Synapse automatically sets the `:version` and `:type` properties (for IPv4 and IPv6 addresses) and the `:scope` property (for IPv6 addresses).

In addition, you can specify IP values using range or CIDR format to create multiple `inet:ip` nodes without the need to specify each address individually.

**Examples**

**Note:** results (output) not shown below due to length.

Create ten `inet:ip` nodes:

``` text
[ inet:ip=2606:4700:20::681a:3780-2606:4700:20::681a:3789 ]
```

Create the 256 addresses in the range 192.168.0.0/24:

``` text
[ inet:ip=192.168.0.0/24 ]
```

### Operations

Similar to node insertion, lifting or filtering IP addresses by range or by CIDR notation will operate on every `inet:ip` node that exists within the Cortex and falls within the specified range or CIDR block. This allows operating on multiple contiguous IP addresses without the need to specify them individually.

**Examples**

Lift all `inet:ip` nodes within the specified range that exist within the Cortex:

```stormdoc
storm> inet:ip=2606:4700:3031::6815:1c70-2606:4700:3031::6815:1c79
inet:ip=2606:4700:3031::6815:1c72
        :scope = global
        :type = unicast
        :version = 6
inet:ip=2606:4700:3031::6815:1c76
        :scope = global
        :type = unicast
        :version = 6
inet:ip=2606:4700:3031::6815:1c77
        :scope = global
        :type = unicast
        :version = 6
```

Filter a set of DNS A records to only include those whose IP value is within the 172.16.\* RFC1918 range:

```stormdoc
storm> inet:dns:a:fqdn=woot.com +:ip=172.16.0.0/12
inet:dns:a=('woot.com', '172.16.47.12')
        :fqdn = woot.com
        :ip = 172.16.47.12
```

<a id="type-int"></a>

## int

An `int` is an integer value. Synapse stores, indexes, and displays integer values as decimal integers, but will also accept as hex or octal values as input.

### Indexing

N/A

### Parsing

When adding or modifying integer values, Synapse will accept integer, hex (preceded by `0x`), and octal (preceded by `0o`) values and represent them as decimal integer values.

**Examples**

Set the number of items available for sale (`:count:total`) of a `biz:listing` to 42:

```stormdoc
storm> biz:listing:name='widgets for sale' [ :count:total=42 ]
biz:listing=09b216f462057dd2018e92695231a1a6
        :count:total = 42
        :name = widgets for sale
        :price = 10USD
```

Use a hex value to set the `:ip:proto` property for an `inet:flow` node to 6:

```stormdoc
storm> inet:flow:server.ip=142.118.95.50 [ :ip:proto=0x06 ]
inet:flow=4e43f635884ea6c381992ae0c78a964e
        :ip:proto = 6
        :period = 2026-04-27T09:37:42Z - 2026-04-27T09:37:42.000001Z
        :server = tcp://142.118.95.50:8888
```

Use the octal value 755 to set the POSIX permissions for a RAR archive entry:

```stormdoc
storm> file:mime:rar:entry [ :extra:posix:perms=0o755 ]
file:mime:rar:entry=20271c769d69a6db5c691dbe391214e9
        :added = 2023-08-11T11:33:00Z
        :extra:posix:perms = 493
        :file = a1ad3c4eb92948a788eb3b60246984c2
        :parent = 2030fb2331688d4b6d55afb26828dd8e
```

Posix permissions are commonly represented in octal (e.g., 755), which is decimal 493.

### Insertion

Same as for parsing.

### Operations

Use integer, hex, or octal values to lift and filter integer types using standard comparison operators.

**Examples**

Lift all `risk:alert` nodes where the `:priority` is greater than 5:

```stormdoc
storm> risk:alert:priority>5
risk:alert=c0266bc76a31e37bab40b8a4dd78736b
        :created = 2023-08-01T09:00:00Z
        :name = outbound traffic to SOC-reported IP
        :priority = 9
```

Lift all `inet:flow` nodes tagged with `#my.tag` and filter to include only those where the `:ip:proto` property is set to the hex equivalent of 6:

```stormdoc
storm> inet:flow#mytag +:ip:proto=0x06
```

Use an octal value to lift all the RAR entry nodes where the `:extra:posix:perms` are 755 (decimal 493):

```stormdoc
storm> file:mime:rar:entry:extra:posix:perms=0o755
file:mime:rar:entry=20271c769d69a6db5c691dbe391214e9
        :added = 2023-08-11T11:33:00Z
        :extra:posix:perms = 493
        :file = a1ad3c4eb92948a788eb3b60246984c2
        :parent = 2030fb2331688d4b6d55afb26828dd8e
```

<a id="type-ival"></a>

## ival

`ival` (interval) is a specialized type consisting of two `time` types in a paired `(<min>, <max>)` relationship. As such, the individual values in an `ival` are subject to the same specialized handling as individual [time](storm_ref_type_specific.md#type-time) values.

`ival` types have their own optimizations in addition to those related to `time` types.

### Indexing

N/A

### Parsing

An `ival` type is typically specified as two comma-separated time values enclosed in parentheses. Alternately, an `ival` can be specified as a single time value with no parentheses (see **Insertion** below for `ival` behavior when specifying a single time value).

Single or double quotes are required in accordance with the standard rules for using [Whitespace and Literals in Storm](storm_ref_intro.md#storm-whitespace-literals). For example:

- `:seen=('2017/03/24 12:13:27', '2017/08/05 17:23:46')`
- `+#sometag=(2018/09/15, "+24 hours")`
- `:seen=2019/03/24`

As `ival` types are a pair of values (i.e., an explicit minimum and maximum), the values must be placed in parentheses and separated by a comma: `(<min>, <max>)`. The parser expects two values with this format.

An `ival` can also be specified as a single time value, in which case the value must be specified **without** parentheses: `<time>`. See **Insertion** below for `ival` behavior when adding vs. modifying using a single time value vs. a `(<min>, <max>)` pair.

When entering an `ival` type, each time value can be input using most of the acceptable formats for [time](storm_ref_type_specific.md#type-time) types, including explicit times (including lower resolution times and wildcard times), relative times, and the special values `now` and `?`.

`ival` types also support relative times using `+-` format to represent both a positive and negative offset from a given point (i.e., `'+-1 hour'`).

When entering relative times in an `ival` type:

- A relative time in the **first** (`<min>`) position is calculated relative to the **current time** (`now`).
- A relative time in the **second** (`<max>`) position is calculated relative to the **first** (`<min>`) time.

For example:

- `:seen='+1 hour'` means from the current time (now) to one hour after the current time.
- `:seen=(2018/12/01, '+1 day')` means from 12:00 AM December 1, 2018 to 12:00 AM December 2, 2018.
- `:seen=(2018/12/01, '-1 day')` means from 12:00 AM November 30, 2018 to 12:00 AM December 1, 2018.
- `:seen=(now, '+-5 minutes')` means from 5 minutes ago to 5 minutes from now.
- `:seen=('-30 minutes', '+1 hour')` means from 30 minutes ago to 30 minutes from now.

When specifying minimum and maximum times for an `ival` type (or when specifying minimum and maximum `time` values to the `*range=` comparator), the following restrictions should be kept in mind:

- Minimums and maximums that use explicit times and / or special terms (`now`, `?`) should be specified in `<min>, <max>` order.
  - Specifying a `<max>, <min>` order will **not** result in an error message, but because it results in an exclusionary time window, it will not return any nodes (i.e., no time / interval can be both greater than a max value and less than a min value).
  - Similarly, combinations of relative times that result in an effective `<max>, <min>` after relative offsets are calculated are allowed will not generate an error, but will result in an exclusionary time window that does not return any nodes.
- Values that result in a nonsensical `<min>, <max>` are not allowed and will generate an error. For example:
  - The special value `?` cannot be used as a minimum value in a `(<min>, <max>)` pair.
  - A `+-` relative time cannot be used as a minimum value in a `(<min>, <max>)` pair.
  - When specifying a `+-` relative time as the maximum value in a `(<min>, <max>)` pair, an explicit `<min>` value is also required (i.e., either an explicit time or `now`).

### Insertion

- When **adding** an `ival` as a `(<min>, <max>)` pair, the `ival` can be specified as described above.

  - If the values for `<min>` and `<max>` are identical, then `<min>` will be set to the specified value and `<max>` will be set to `<min>` plus 1 ms.

- When **adding** an `ival` as a single time value, it must be specified **without** parentheses.

  - When a single time value is used, the `<min>` value will be set to the specified time and the `<max>` will be set to the `<min>` time plus 1 ms.

- When **modifying** an existing `ival` property (including tag timestamps) with either a `(<min>, <max>)` pair or a single time value, the existing `ival` is **not** simply overwritten (as is the norm for modifying properties - see [Storm Reference - Data Modification](storm_ref_data_mod.md#storm-ref-data-mod)). Instead, the `<min>` and / or `<max>` are **only** updated if the new value(s) are:

  - Less than the current `<min>`, and / or
  - Greater than the current `<max>`.

  This means that once set, `<min>` and `<max>` can only be "pushed out" to a lower minimum and / or a higher maximum. Specifying a time or times that fall **within** the current minimum and maximum will have no effect (i.e., the current values will be retained).

  This means that it is not possible to "shrink" an `ival` directly; to specify a higher minimum or a lower maximum (or to remove the timestamps altogether), you must delete the `ival` property (or remove the timestamped tag) and re-add it with the updated values.

### Operations

`ival` types can be lifted and filtered (see [Storm Reference - Lifting](storm_ref_lift.md#storm-ref-lift) and [Storm Reference - Filtering](storm_ref_filter.md#storm-ref-filter)) with the standard equivalent ( `=` ) operator, which will match the **exact** `<min>` and `<max>` values specified.

**Example:**

Lift the DNS A nodes whose observation window is **exactly** from 2018/12/13 01:05 to 2018/12/16 12:57:

```stormdoc
storm> inet:dns:a:seen=('2018/12/13 01:05', '2018/12/16 12:57')
inet:dns:a=('yoyodyne.com', '16.16.16.16')
        :fqdn = yoyodyne.com
        :ip = 16.16.16.16
        :seen = 2018-12-13T01:05:00Z - 2018-12-16T12:57:00Z
```

`ival` types cannot be used with comparison operators such as "less than" or "greater than or equal to".

`ival` types are most often lifted or filtered using the custom interval comparator (`@=`) (see [Lift by Time or Interval (@=)](storm_ref_lift.md#lift-interval) and [Filter by Time or Interval (@=)](storm_ref_filter.md#filter-interval)). `@=` is intended for time-based comparisons (including comparing `ival` types with `time` types).

**Example:**

Lift all the DNS A nodes whose observation window overlaps with the interval of March 1, 2019 through April 1, 2019:

```stormdoc
storm> inet:dns:a:seen@=(2019/03/01, 2019/04/01)
inet:dns:a=('hurr.com', '4.4.4.4')
        :fqdn = hurr.com
        :ip = 4.4.4.4
        :seen = 2019-01-05T09:38:00Z - 2019-03-12T18:17:00Z
inet:dns:a=('derp.net', '8.8.8.8')
        :fqdn = derp.net
        :ip = 8.8.8.8
        :seen = 2019-03-08T07:26:00Z - 2019-03-22T10:14:00Z
inet:dns:a=('blergh.org', '2.2.2.2')
        :fqdn = blergh.org
        :ip = 2.2.2.2
        :seen = 2019-03-28T22:22:00Z - 2019-04-27T00:03:00Z
```

`ival` types cannot be used with the `*range=` custom comparator. `*range=` can only be used to specify a range of individual values (such as `time` or `int`).

> [!TIP]
> By definition, an `ival` is a **pair** of date/time values treated as a single combined value. This means that when using [variables](storm_adv_vars.md#storm-adv-vars) to work with `ival` types, the full value of the property is assigned to the variable by default. For example, given a node (such as an `inet:dns:a` node) with a `:seen` value of `(2023/07/08 11:19:02, 2023/12/14 21:18:47)`, the variable assignment `$time=:seen` will assign the **pair** of date/times to `$time`.
>
> You can access each date/time of an `ival` independently by assigning the value to a **pair** of variables as follows:
>
> `( $min, $max )=:seen`
>
> `$min` will represent the value `2023/07/08 11:19:02` and `$max` will represent the value `2023/12/14 21:18:47`.

<a id="type-loc"></a>

## loc

`Loc` is a specialized type used to represent geopolitical locations (i.e., locations within geopolitical boundaries) as a series of user-defined dot-separated hierarchical strings - for example, *\<country\>.\<region\>.\<city\>*. This allows specifying locations such as `us.fl.miami`, `gb.london`, and `ca.on.toronto`.

`Loc` is an extension of the [str](storm_ref_type_specific.md#type-str) type. However, because `loc` types use strings that comprise a dot-separated hierarchy, they exhibit slightly modified behavior from standard string types for certain operations.

### Indexing

The `loc` type is an extension of the [str](storm_ref_type_specific.md#type-str) type and is **prefix-indexed** like other strings. However, the use of dot-separated boundaries impacts operations using `loc` values.

`loc` values are normalized to lowercase.

### Parsing

`loc` values can be input using any case (uppercase, lowercase, mixed case) but will normalized to lowercase.

Components of a `loc` value must be separated by the dot ( `.` ) character. A `loc` value that consists of a single element does not require a trailing dot.

The dot is a reserved character for the `loc` type and is used to separate string elements along hierarchical boundaries. The use of the dot as a reserved boundary marker impacts some operations using the `loc` type. Note that this means the dot cannot be used as part of a location string. For example, the following location value would be interpreted as a hierarchical location with four elements (`us`, `fl`, `st`, and `petersburg`):

- `:loc=us.fl.st.petersburg`

To appropriately represent the "city" element of the above location, an alternate syntax must be used. For example:

- `:loc=us.fl.stpetersburg`
- `:loc='us.fl.st petersburg'`
- `:loc=us.fl.st_petersburg`
- ...etc.

As an extension of the `str` type, `loc` types are subject to Synapse's restrictions regarding using [Whitespace and Literals in Storm](storm_ref_intro.md#storm-whitespace-literals).

### Insertion

Same as for parsing.

As `loc` values are simply dot-separated strings, the use or enforcement of any specific convention for geolocation values and hierarchies is an implementation decision.

### Operations

The use of the dot character ( `.` ) as a reserved boundary marker impacts prefix ( `^=` ) and equivalent ( `=` ) operations using the `loc` type.

#### Prefix Operator

When **lifting** or **filtering** on `loc` property values using the prefix comparison operator ( `^=` ), the specified value must fall on a dot boundary.

String and string-derived types are **prefix-indexed** to optimize lifting or filtering strings that start with a given substring. For standard strings, the prefix operator can be used with strings of arbitrary length. However, for `loc` types, the prefix operator works along dot boundaries. This is because it is generally more analytically meaningful to lift all locations within the US (`^= us`) or within Florida (`^= us.fl`) than it is to lift all locations in the US within states that start with `M` (`^= us.m`).

Prefix comparison for `loc` types is useful because it easily allows lifting or filtering at any appropriate level of resolution within the dotted hierarchy:

**Examples:**

Lift all organizations located in Turkey (`tr`):

```stormdoc
storm> ou:org:place:loc^=tr
ou:org=729523c7015f7601feb284e1fdbaf64c
        :name = republic of turkey ministry of foreign affairs
        :place:loc = tr.ankara
ou:org=152b0923ee4d4fab577cd887433ba66f
        :name = adeo it consulting services
        :place:loc = tr.istanbul
```

Lift all IP addresses geolocated in the province of Ontario, Canada (`ca.on`):

```stormdoc
storm> inet:ip:place:loc^=ca.on
inet:ip=149.248.52.240
        :place:loc = ca.on
        :type = unicast
        :version = 4
inet:ip=49.51.12.195
        :place:loc = ca.on.barrie
        :type = unicast
        :version = 4
inet:ip=199.201.123.200
        :place:loc = ca.on.keswick
        :type = unicast
        :version = 4
```

> [!NOTE]
> Specifying a more granular prefix value will not match values that are less granular. That is, `inet:ip:place:loc^=ca.on` will fail to match `inet:ip:place:loc=ca`.

#### Equals Operator

When **lifting** or **filtering** on `loc` property values using the equals operator ( `=` ), Synapse will return **exact** matches for the specified value. The query below will only lift `geo:place` nodes with `:loc=us.wa.seattle`; it will not lift nodes with `:loc=us.wa` or `:loc=us.washington.seattle`:

Lift all places in the city of Seattle, Washington:

```stormdoc
storm> geo:place:loc=us.wa.seattle
geo:place=965638e363dcca0e7148136ad68551aa
        :latlong = 47.6205099,-122.3514714
        :loc = us.wa.seattle
        :name = space needle
geo:place=c50de88c5787c9eaae2697544cc679f2
        :latlong = 47.4502535,-122.3110105
        :loc = us.wa.seattle
        :name = seattle-tacoma international airport
```

When **lifting** on `:loc` property values using the equals operator ( `=` ), a single asterisk ( `*` ) can be used as a wildcard to represent any trailing string following a dot boundary (including no trailing string - `:loc=us.*` will match `:loc=us` as well as `:loc=us.tx.austin`). The asterisk must immediately follow a dot boundary and must be the final character in the expression (e.g., expressions such as `:loc=us.*.rochester` and `:loc=us.m*` are invalid; the expressions will not generate an error but will fail to return any nodes).

Lift all organizations located in Turkey:

```stormdoc
storm> ou:org:place:loc=tr.*
ou:org=729523c7015f7601feb284e1fdbaf64c
        :name = republic of turkey ministry of foreign affairs
        :place:loc = tr.ankara
ou:org=152b0923ee4d4fab577cd887433ba66f
        :name = adeo it consulting services
        :place:loc = tr.istanbul
```

Lift all IP addresses geolocated in the province of Ontario, Canada:

```stormdoc
storm> inet:ip:place:loc=ca.on.*
inet:ip=149.248.52.240
        :place:loc = ca.on
        :type = unicast
        :version = 4
inet:ip=49.51.12.195
        :place:loc = ca.on.barrie
        :type = unicast
        :version = 4
inet:ip=199.201.123.200
        :place:loc = ca.on.keswick
        :type = unicast
        :version = 4
```

> [!NOTE]
> Lifting by `loc` property value using the wildcard is equivalent to a prefix lift. The following queries will return the same results:
>
> Wildcard: `ou:org:place:loc=de.*`
>
> Prefix match: `ou:org:place:loc^=de`

<a id="type-str"></a>

## str

### Indexing

String (and string-derived) types are indexed by **prefix** (character-by-character from the beginning of the string). This allows matching on any initial substring.

### Parsing

Some string types and string-derived types are normalized to all lowercase to facilitate pivoting across like values without case-sensitivity. For types that are normalized in this fashion, the string can be entered in mixed-case and will be automatically converted to lowercase.

Strings are subject to Synapse's restrictions regarding using [Whitespace and Literals in Storm](storm_ref_intro.md#storm-whitespace-literals).

### Insertion

Same as for parsing.

### Operations

Because of Synapse's use of **prefix indexing,** string and string-derived types can be lifted or filtered based on matching an initial substring of any string using the prefix extended comparator (`^=`) (see [Lift by Prefix (^=)](storm_ref_lift.md#lift-prefix) and [Filter by Prefix (^=)](storm_ref_filter.md#filter-prefix)).

Prefix matching is case-sensitive based on the specific type being matched. If the target property's type is case-sensitive, the string to match must be entered in case-sensitive form. If the target property is case-insensitive (i.e., normalized to lowercase) the string to match can be entered in any case (upper, lower, or mixed) and will be automatically normalized by Synapse.

**Examples**

Lift all organizations whose name starts with the word "Acme":

```stormdoc
storm> ou:org:name^=acme
ou:org=70a48c4618332a7d6e9251a9b02699c3
        :name = acme construction
ou:org=fa605964cccb6209733f50ca547f41f2
        :name = acme practical joke products
```

Strings and string-derived types can also be lifted or filtered using the regular expression extended comparator ( `~=`) (see [Lift by Regular Expression (~=)](storm_ref_lift.md#lift-regex) and [Filter by Regular Expression (~=)](storm_ref_filter.md#filter-regex)).

<a id="type-syn-tag"></a>

## syn:tag

`syn:tag` is a specialized type used for [Tag](data_model.md#data-tag) nodes and properties within Synapse. Tags are used to group related nodes; provide context to nodes; and often represent domain-specific, analytically relevant observations or assessments. Tags support a hierarchical namespace based on user-defined dot-separated strings. This hierarchy allows recording classes or categories of observations that can be defined with increasing specificity. (See [Analytical Model](analytical_model.md#analytical-model) for more information.)

### Indexing

The `syn:tag` type is an extension of the [str](storm_ref_type_specific.md#type-str) type and is **prefix-indexed** like other strings.

`syn:tag` values are normalized to lowercase.

### Parsing

Components of a `syn:tag` value must be separated by the dot ( `.` ) character. The dot is a reserved character for the `syn:tag` type and is used to separate string elements along hierarchical boundaries. A `syn:tag` value that consists of a single element does not require a trailing dot.

`syn:tag` values can contain ASCII lowercase characters, numerals, and underscores, as well as Unicode words (including most characters that can be part of a word in any language). Spaces and ASCII symbols (other than the underscore) are not allowed.

The following are all acceptable `syn:tag` values:

- `syn:tag=cno`
- `syn:tag=rep.vt.exploit`
- `syn:tag=rep.microsoft.forest_blizzard`
- `syn:tag=cno.mil.pla.3pla` (Unicode words are also supported as tag elements -- for example, tag
  components written in Chinese, Cyrillic, or other non-Latin scripts -- for international taxonomy use cases)

When creating a `syn:tag` node or setting a property whose type is `syn:tag` (such as `risk:threat:tag`), Synapse will automatically normalize the value by:

- converting uppercase letters to lowercase;
- converting dashes ( `-` ) or spaces to underscores ( `_` ).
- ignoring any disallowed characters.

**Examples:**

```stormdoc
storm> [ syn:tag='rep.us-cisa.LAPSUS$' ]
syn:tag=rep.us_cisa.lapsus
        :base = lapsus
        :depth = 2
        :up = rep.us_cisa
```

In the above example:

- the dash in `us-cisa` is converted to an underscore;
- `LAPSUS` is lowercased to `lapsus`; and
- the dollar sign ( `$` ) is ignored.

> [!NOTE]
> If you attempt to **apply** a tag that contains invalid characters to a node, Synapse will throw a Storm syntax error. The only normalization Synapse performs in this situation is to gracefully convert any uppercase letters to lowercase. The following Storm query will throw an error:
>
> `[ inet:fqdn=woot.com +#rep.us-cisa.LAPSUS$ ]`

### Insertion

The `syn:tag` type is unique in that it is a type that can also be applied as a label to other nodes.

A `syn:tag` (as a node) does not have to be created before the equivalent tag (label) can be applied to another node. That is, applying a tag to a node will result in the automatic creation of the corresponding `syn:tag` node or nodes (assuming the appropriate user permissions). For example:

```stormdoc
storm> [ inet:fqdn=woot.com +#some.new.tag ]
inet:fqdn=woot.com
        :domain = com
        :host = woot
        :issuffix = false
        :iszone = true
        :zone = woot.com
        #some.new.tag
```

The Storm syntax above will apply the tag `#some.new.tag` to the node `inet:fqdn=woot.com` and automatically create the node `syn:tag=some.new.tag` if it does not already exist (as well as `syn:tag=some` and `syn:tag=some.new`).

### Operations

Like strings and other string-derived types, `syn:tag` types are **prefix-indexed**. This means that `syn:tag` values can be lifted and filtered using the prefix comparison operator ( `^=` ).

When lifting and filtering `syn:tag` types by prefix, the expression to match is **not** constrained by the dot ( `.` ) boundary that separates tag elements.

Prefix comparison for `syn:tag` types is useful because it allows you to easily identify a subset of tags or to lift / filter tags at any appropriate level of resolution within a tag hierarchy.

**Examples:**

Lift all tags in the computer network operations (`cno`) tree:

```stormdoc
storm> syn:tag^=cno
syn:tag=cno
        :base = cno
        :depth = 0
syn:tag=cno.mal
        :base = mal
        :depth = 1
        :up = cno
syn:tag=cno.mal.redtree
        :base = redtree
        :depth = 2
        :up = cno.mal
syn:tag=cno.threat
        :base = threat
        :depth = 1
        :up = cno
syn:tag=cno.threat.t27
        :base = t27
        :depth = 2
        :up = cno.threat
```

Lift all tags associated with data reported by Sophos where the final tag element starts with `co`:

```stormdoc
storm> syn:tag^=rep.sophos.co
syn:tag=rep.sophos.cobalt_shadow
        :base = cobalt_shadow
        :depth = 2
        :title = COBALT SHADOW (Sophos)
        :up = rep.sophos
syn:tag=rep.sophos.copper_fieldstone
        :base = copper_fieldstone
        :depth = 2
        :title = COPPER FIELDSTONE (Sophos)
        :up = rep.sophos
```

**Usage notes:**

- Specifying a more granular prefix value will **not** match values that are less granular. That is, `syn:tag^=cno.infra` will fail to match `syn:tag=cno`.
- Use of the equals comparator ( `=` ) with `syn:tag` types will match the **exact value only.** So `syn:tag=rep` will **only** match that tag and will not match `syn:tag=rep.symantec` or `syn:tag=rep.trend.pawnstorm`.
- When lifting or filtering `syn:tag` types, use of the wildcard ( `*` ) is not allowed. For example, the following Storm expression is invalid and will throw a syntax error: `syn:tag=rep.*.cobalt_strike`

> [!NOTE]
> Working with (lifting, filtering, etc.) `syn:tag` **types** (`syn:tag` forms or property values) is different from working with **tags** applied to nodes. In particular, when filtering based on the tag(s) applied to a set of nodes, you can filter using single or double asterisks ( `*` or `**`). See [Filter by Tag Globs](storm_ref_filter.md#filter-tag-globs) or the general [Tag Filters](storm_ref_filter.md#tag-filter) or [Tag Lifts](storm_ref_lift.md#tag-lifts) sections for details on working with tags applied to nodes.

<a id="type-taxoxnomy"></a>

## taxonomy

A `taxonomy` in Synapse is used to represent a set of hierarchical types or categories that can be used to classify objects (forms). Many forms in Synapse include `:type` properties (such as `it:software:type`, `geo:place:type`, or `doc:report:type`).

> [!TIP]
> `taxonomy` is a base [Type](../glossary.md#gloss-type) that is commonly extended to define form-specific taxonomies. That is, a software product (`it:software`) has a `:type` property that can represent a set of tool/malware types or categories. The `it:software:type` property has a form-specific type of `it:software:type:taxonomy`.
>
> While this section describes the behavior of taxonomies generally, keep in mind that each form can have its own taxonomy / set of categories independent of other taxonomies. This allows you to define one taxonomy to categorize tools/malware and a separate taxonomy to categorize articles or publications, for example.

Most taxonomy types are also forms (i.e., `it:software:type:taxonomy`), so you can lift, view, and work with them just like other nodes in Synapse. To ensure consistency across the numerous taxonomy forms, most taxonomies inherit the `meta:taxonomy` [Interface](../glossary.md#gloss-interface).

Given their hierarchical structure, taxonomies share some similarities with [tags](storm_ref_type_specific.md#type-syn-tag):

- Taxonomies can be hierarchical, using a dotted (dot-separated) namespace to represent various levels in the hierarchy.
- Taxonomy forms include properties such as `:base`, `:depth`, and `:parent` that allow you to lift, pivot, and navigate among taxonomy nodes similar to the way you navigate [Tags as Nodes](analytical_model.md#analytical-tags-nodes).

There are no pre-defined taxonomies in Synapse. You can make use of taxonomies (or not), and can define taxonomies that are tailored to your specifc analysis needs. For example, you can construct a multi-level taxonomy to help subdivide and organize industries using their `:type` property:

- `ind:industry:type=education`
- `ind:industry:type=education.colleges`
- `ind:industry:type=education.colleges.universities`
- `ind:industry:type=education.colleges.junior`
- `ind:industry:type=finance`
- `ind:industry:type=finance.banking`
- `ind:industry:type=finance.defi`

...etc.

Taxonomies do not have to be multi-level / hierarchcial. If you only need a simple set of categories, you can define a flat taxonomy with only one level. The following uses a flat taxonomy to populate `it:software:type` properties:

- `it:software:type=backdoor`
- `it:software:type=downloader`
- `it:software:type=dropper`
- `it:software:type=utility`

... etc.

### Indexing

The `taxonomy` type is an extension of the [str](storm_ref_type_specific.md#type-str) type and is **prefix-indexed** like other strings.

`taxonomy` values are normalized to lowercase. A `taxonomy` value always includes a trailing dot ( `.` ), regardless of the number of elements (taxons) in the value.

The trailing dot is masked / omitted when displaying the taxonomy value. This difference can be seen when displaying the value's representation (display value, using the method `$node.repr()`) as opposed to its actual value (using the attribute `$node.value`):

```stormdoc
storm> entity:goal:type:taxonomy=financial_gain $lib.print($node.repr()) $lib.print($node.value)
financial_gain
financial_gain.
entity:goal:type:taxonomy=financial_gain
        :base = financial_gain
        :depth = 0
```

### Parsing

Components of a `taxonomy` value must be separated by the dot ( `.` ) character. The dot is a reserved character for the `taxonomy` type and is used to separate elements (taxons) along hierarchical boundaries. All `taxonomy` values end in a trailing dot.

`taxonomy` values can contain ASCII lowercase characters, numerals, and underscores, as well as Unicode words (including most characters that can be part of a word in any language). Spaces and ASCII symbols (other than the underscore) are not allowed.

When creating a `taxonomy` node or setting a `taxonomy` property, Synapse will automatically normalize the value by:

- converting uppercase letters to lowercase;
- converting dashes ( `-` ) or spaces to underscores ( `_` );
- ignoring any disallowed characters; and
- adding the trailing dot ( `.` ) to the stored value if not specified.

### Insertion

N/A - no special behavior when working with `taxonomy` nodes or properties other than as specified above.

### Operations

Like strings and other string-derived types, `taxonomy` types are **prefix-indexed**. This means that `taxonomy` values can be lifted and filtered using the prefix comparison operator ( `^=` ).

When lifting and filtering `taxonomy` types by prefix, the expression to match is **not** constrained by the dot ( `.` ) boundary that separates taxonomy elements.

Prefix comparison for `taxonomy` types is useful because it allows you to easily identify a subset of forms based on lifting or filtering those forms using any appropriate level of resolution within the form's taxonomy.

**Examples:**

Lift all industries (`ind:industry` nodes) within the "media" category / taxonomy:

```stormdoc
storm> ind:industry:type^=media
ind:industry=7ae4b38ab2f6ff357ccc3af9f2fe08eb
        :name = media
        :type = media
ind:industry=6942ca4b2a116555a05a8a61df2f95ae
        :name = entertainment
        :type = media.entertainment
ind:industry=3012dd13ad13769abb640315e0268b50
        :name = journalism and news media
        :type = media.journalism
ind:industry=856018e7b0b5666acc29c93f96031e0c
        :name = journalists and reporters
        :type = media.journalism.reporters
ind:industry=54c66062e7d30a118d7e5d0e61948cfd
        :name = publishing
        :type = media.publishing
ind:industry=5a5686c1c34b3dea70b97631a4abd710
        :name = print media
        :type = media.publishing.print
```

Lift all industries (`ind:industry` nodes) within the "media" category / taxonomy whose subcategory starts with "j":

```stormdoc
storm> ind:industry:type^=media.j
ind:industry=3012dd13ad13769abb640315e0268b50
        :name = journalism and news media
        :type = media.journalism
ind:industry=856018e7b0b5666acc29c93f96031e0c
        :name = journalists and reporters
        :type = media.journalism.reporters
```

**Usage notes:**

- Specifying a more granular prefix value will not match values that are less granular. That is, `it:software:availability^=public.commercial` will fail to match `it:software:availability=public`
- Use of the equals comparator ( `=` ) with `taxonomy` types will match the exact value only. So `ind:industry:type=energy` will only match that taxonomy and will not match `ind:industry:type=energy.electricity` or `ind:industry:type=energy.electricity.distribution`.
- When lifting or filtering `taxonomy` types, use of the wildcard ( `*` ) is not allowed. For example, the following Storm expression is invalid and will throw a syntax error: `risk:attack:type:taxonomy=phishing.*`.

<a id="type-time"></a>

## time

Synapse stores `time` types in Epoch microseconds (micros) - that is, the number of microseconds since January 1, 1970. The `time` type is technically a date/time because it encompasses both a date and a time. A time value alone, such as 12:37 PM (12:37:00.000000), is invalid.

See also the section on [ival](storm_ref_type_specific.md#type-ival) (interval) types for details on how `time` types are used as minimum / maximum pairs.

### Indexing

N/A

### Parsing

`time` values can be input into Storm as any of the following:

- **Explicit** times:

  - Human-readable (YYYY/MM/DD hh:mm:ss.mmmmmm):

    `'2018/12/16 09:37:52.324'`

  - Human-readable "Zulu" (YYYY/MM/DDThh:mm:ss.mmmmmmZ):

    `2018/12/16T09:37:52.324Z`

  - Human-readable with time zone (YYYY-MM-DD hh:mm:ss.mmmmmm+/-hh:mm). No spaces are allowed between the time value and the time zone offset:

    `2018-12-16 09:37:52.324-04:00`

    > [!NOTE]
    > Synapse does not support the **storage** of an explicit time zone with a time value (i.e., +0800). Synapse stores time values in UTC for consistency. If a time zone is specified using an acceptable time zone offset format on input, Synapse will automatically convert the value to UTC for storage. If no time zone is specified, Synapse will assume the value is in UTC.

  - No formatting (YYYYMMDDhhmmssmmmmmm):

    `20181216093752324000`

  - Epoch micros:

    `(1544953072324000)`

    > [!TIP]
    > Synapse expects that users will generally enter time values using human-friendly strings, and will attempt to parse the input as such. Using parentheses tells Synapse to interpret the value as a raw integer.
    >
    > Note that this parentheses syntax only applies when setting or updating a `time` property using Storm. When setting or updating a property in the [Optic UI](/docs/synapse-enterprise-optic/latest/index.md) by editing a field, you must enter a time string value.

- **Relative** (offset) time values in the format:

  **+** \| **-** \| **+-** *\<count\>* *\<unit\>*

  where *\<count\>* is a numeric value and *\<unit\>* is one of the following:

  > - `minute(s)`
  > - `hour(s)`
  > - `day(s)`

  **Examples:**

  > - `'+7 days'`
  > - `'-15 minutes'`
  > - `'+-1 hour'`

- **Special** time values:

  - the keyword `now` is used to represent the current date/time.

  - a question mark ( `?` ) is used to effectively represent an unspecified / indefinite time in the future (technically equivalent to 9223372036854775807 micros, i.e., "some really high value in the future". Note that technically the largest valid micros value is 253402300799999999, which represents 9999/12/31 23:59:59.999999).

    The question mark can be used as the maximum value of an interval ([ival](storm_ref_type_specific.md#type-ival)) type to specify that the data or assessment associated with the `ival` should be considered valid indefinitely. (Contrast that with a maximum interval value set to the equivalent of `now` that would need to be continually updated over time in order to remain current.)

Standard rules regarding using [Whitespace and Literals in Storm](storm_ref_intro.md#storm-whitespace-literals) apply. For example, `'2018/12/16 09:37:52.324'` needs to be entered in single or double quotes, but `2018/12/16` does not. Similarly, relative times starting with `+` or `-` and the special time value `?` need to be placed in single or double quotes.

#### Lower Resolution Time Values and Wildcard Time Values

`time` values (including tag timestamps) must be entered at a minimum resolution of year (`YYYY`) and can be entered up to a maximum resolution of microseconds (`YYYY/MM/DD hh:mm:ss.mmmmmm`).

Where lower resolution values are entered, Synapse will make logical assumptions about the intended date / time value and zero-fill the remainder of the equivalent epoch mills date / time. For example:

- A value of `2016` will be interpreted as 12:00 AM on January 1, 2016 (`2016/01/01 00:00:00.000000`).
- A value of `2018/10/27` will be interpreted as 12:00 AM on that date (`2018/10/27 00:00:00.000000`).
- A value of `'2020/03/16 05'` will be interpreted as 05:00 AM on that date (`2020/03/16 05:00:00.000000`).
- A value of `'2018/10/27 14:00-04:00'` will be interpreted as 14:00 (2:00 PM) on that date with a 4 hour offset from UTC (`2018/10/27 14:00:00.000-04:00`, stored in UTC as `2018/10/27 18:00:00.000000`).

Synapse also supports the use of the wildcard ( `*` ) character to specify a partial time value match:

- A value of `2016*` will be interpreted as "any date / time within the year 2016".
- A value of `2018/10/27*` will be interpreted as "any time on October 27, 2018".
- A value of `'2020/03/16 05*'` will be interpreted as "any time within the hour of 05:00 on March 16, 2020".

> [!NOTE]
> When using wildcard syntax, the wildcard must be used on a sensible time value boundary, such as `YYYYMM*`. You cannot us a wildcard to "split" values (i.e., `YYMMD*` is invaild syntax).

**Examples:**

Set the time of a DNS request to the current time:

```stormdoc
storm> inet:dns:request:query:name=woot.com [ :time=now ]
inet:dns:request=a8569961179b0f059054dd9531019b9a
        :query:name = woot.com
        :time = 2026-08-11T19:32:43.468444Z
```

Set the observed time window (technically an `ival` type) for when an IP address was a known sinkhole (via the `#cno.infra.dns.sink.hole` tag) from its known start date to an indefinite future time (i.e., the sinkhole is presumed to remain a sinkhole indefinitely / until the values are manually updated with an explicit end date):

```stormdoc
storm> [ inet:ip=1.2.3.4 +#cno.infra.dns.sink.hole=(2017/06/13, '?') ]
inet:ip=1.2.3.4
        :type = unicast
        :version = 4
        #cno.infra.dns.sink.hole = 2017-06-13T00:00:00Z - ?
```

- Set the observed time window using a time zone offset:

```stormdoc
storm> [ inet:ip=5.6.7.8 +#cno.infra.dns.sink.hole=(2017/06/13 09:46+04:00, '?') ]
inet:ip=5.6.7.8
        :type = unicast
        :version = 4
        #cno.infra.dns.sink.hole = 2017-06-13T05:46:00Z - ?
```

### Insertion

When adding or modifying `time` types, any of the above formats (explicit / relative / special terms) can be specified.

In addition, when adding or modifying `time` types, a lower resolution time and a wildcard time behave identically. In other words, the following are equivalent Storm queries (both will set the `:time` value of the newly created DNS request node to `2021/01/23 00:00:00.000000`):

```stormdoc
storm> inet:dns:request:query:name=example.com [ :time=2021/01/23 ]
inet:dns:request=4e584c97fa99b1cc81ee966b489ccd43
        :query:name = example.com
        :time = 2021-01-23T00:00:00Z
```

```stormdoc
storm> inet:dns:request:query:name=example.com [ :time=2021/01/23* ]
inet:dns:request=4e584c97fa99b1cc81ee966b489ccd43
        :query:name = example.com
        :time = 2021-01-23T00:00:00Z
```

When specifying a relative time for a `time` value, **the offset will be calculated from the current time** (`now`):

```stormdoc
storm> inet:dns:request:query:name=woot.com [ :time='-5 minutes' ]
inet:dns:request=a8569961179b0f059054dd9531019b9a
        :query:name = woot.com
        :time = 2026-08-11T19:27:43.494354Z
```

Plus / minus ( `+-` ) relative times cannot be specified for `time` types, as the type requires a single value. See the section on [ival](storm_ref_type_specific.md#type-ival) (interval) types for details on using `+-` times with `ival` types.

### Operations

`time` types can be lifted and filtered using:

- Standard logical and mathematical comparison operators (comparators).
- The extended range ( `*range=` ) custom comparator.
- The extended interval ( `@=` ) custom comparator.

Arithmetic on typed values preserves the `time` type:

- subtracting two `time` values yields a `duration` (see [duration](storm_ref_type_specific.md#type-duration));
- adding or subtracting a `duration` to or from a `time` yields a new `time`.

#### Standard Operators

`time` types can be lifted and filtered with the standard logical and mathematical comparators (see [Storm Reference - Lifting](storm_ref_lift.md#storm-ref-lift) and [Storm Reference - Filtering](storm_ref_filter.md#storm-ref-filter)). This includes the use of lower resolution time values and wildcard time values.

**Example:**

Filter a set of DNS request nodes to those that occurred prior to June 1, 2019:

```stormdoc
storm> inet:dns:request +:time<2019/06/01
inet:dns:request=947d62a0a3af257f8c19ffbbb631a0ff
        :query:name = derp.net
        :time = 2015-12-14T19:22:00Z
inet:dns:request=b7937c1d4e3159f6bbe83b15f9c84d23
        :query:name = hurr.com
        :time = 2018-06-28T17:43:00Z
```

> [!NOTE]
> It is important to understand the differences in behavior when lifting and filtering `time` types using lower resolution time values (which Synpase zero-fills) or wildcard time values (which Synpase wildcard-matches). These behaviors vary based on the specific operator used.

- When lifting or filtering using the equivalent ( `=` ) operator, behavior is **different:**

  - `:time=2021/05/13` means equal to **the exact date/time value** `2021/05/13 00:00:00.000`.
  - `:time=2021/05/13*` means equal to **any** time on that date (`2021/05/13 00:00:00.000` through `2021/05/13 23:59:59.999`).

- When lifting or filtering using the greater than ( `>`) / greater than or equal to ( `>=`) operators, behavior is **equivalent:**

  - `:time>2021/05/13` and `:time>2021/05/13*` **both** mean any date / time greater than `2021/05/13 00:00:00.000`.
  - `:time>=2021/05/13` and `:time>=2021/05/13*` **both** mean any date / time greater than or equal to `2021/05/13 00:00:00.000`.

  Both are equivalent because in this case Synapse interprets the wildcard syntax as "greater than or equal to the **lowest** possible wildcard match", which in this case is `2021/05/13 00:00:00.000`.

- When lifting or filtering using the less than ( `<` ) / less than or equal to ( `<=` ) operators, behavior is **different:**

  - `:time<2021/05/13` / `:time<=2021/05/13` mean any date / time less than (or less than or equal to) `2021/05/13 00:00:00.000`.
  - `:time<2021/05/13*` / `:time<=2021/05/13*` both mean any date / time less than (or less than or equal to) `2021/05/13 23:59:59.999`.

  The behavior differs because in this case Synapse interprets the wildcard syntax as "less than or equal to the **highest** possible wildcard match", which in this case is `2021/05/13 23:59:59.999`.

> [!TIP]
> The wildcard syntax is useful because it can provide a simplified, more intuitive means to specify certain time ranges / time intervals without needing to use the range ( `*range=` ) or interval ( `@=` ) operators. For example, the following three Storm queries are equivalent and will return all files compiled at any time within the year 2019:
>
> ``` text
> file:bytes:mime:pe:compiled=2019*
>
> file:bytes:mime:pe:compiled*range=('2019/01/01 00:00:00.000', '2019/12/31 23:59:59.999')
>
> file:bytes:mime:pe:compiled@=('2019/01/01', '2020/01/01')
> ```
>
> (A **range** maximum value represents "less than or equal to" that value, while an **interval** maximum value represents "less than" that value.)

#### Range Custom Operator

`time` types can lifted and filtered using the `*range=` custom comparator (see [Lift by Range (*range=)](storm_ref_lift.md#lift-range) and [Filter by Range (*range=)](storm_ref_filter.md#filter-range)).

**Example:**

Lift a set of `file:bytes` nodes whose PE compiled time is between January 1, 2019 and today:

```stormdoc
storm> file:mime:pe:compiled*range=(2021/01/01, now)
file:mime:pe=7f9899adcfd3c62d98cf70fe06daaf40
        :compiled = 2021-04-13T00:23:14Z
        :file = e96796b9016d801ac201d720e3544e13
file:mime:pe=d35f5ed5b10b8d1c3333d621a1ece572
        :compiled = 2023-10-30T05:34:22Z
        :file = 25ec0d9ba759244aa39ecfb182cb8c47
```

> [!NOTE]
> Both lower resolution times (`2025`) and wildcard times (`2025*`) can be used for values specified within the `*range=` operator. Because the range operator is a shorthand syntax for "greater than or equal to `<range_min>` and less than or equal to `<range_max>`", users should be aware of differences in behavior between each kind of time value with greater than / less than operators.

See the Storm documents referenced above for additional examples using the range (`*range=`) comparator.

#### Interval Custom Operator

`time` types can be lifted and filtered using the interval ( `@=` ) custom comparator (see [Lift by Time or Interval (@=)](storm_ref_lift.md#lift-interval) and [Filter by Time or Interval (@=)](storm_ref_filter.md#filter-interval)). The comparator is specifically designed to compare `time` types and `ival` types, which can be useful (for example) for filtering to a set of nodes whose `time` properties fall within a specified interval.

**Example:**

Lift a set of DNS A records whose window of observation includes March 16, 2019 at 13:00 UTC:

```stormdoc
storm> inet:dns:a:seen@='2019/03/16 13:00'
inet:dns:a=('aaaa.org', '1.2.3.4')
        :fqdn = aaaa.org
        :ip = 1.2.3.4
        :seen = 2018-12-29T12:36:27Z - 2019-06-03T18:14:33Z
inet:dns:a=('derp.net', '8.8.8.8')
        :fqdn = derp.net
        :ip = 8.8.8.8
        :seen = 2019-03-08T07:26:00Z - 2019-03-22T10:14:00Z
inet:dns:a=('bbbb.edu', '5.6.7.8')
        :fqdn = bbbb.edu
        :ip = 5.6.7.8
        :seen = 2019-03-16T12:59:59Z - 2019-03-16T13:01:01Z
```

> [!NOTE]
> Both lower resolution times (`2025`) and wildcard time (`2025*`) can be used for values specified within the `@=` operator. Because the interval operator is a shorthand syntax for "greater than or equal to `<ival_min>` and less than `<ival_max>`", users should be aware of differences in behavior between each kind of time value with greater than / less than operators.

See the Storm documents referenced above for additional examples using the interval (`@=`) comparator.
