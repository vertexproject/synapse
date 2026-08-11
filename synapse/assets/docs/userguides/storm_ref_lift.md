<a id="storm-ref-lift"></a>

# Storm Reference - Lifting

Lift operations retrieve a set of nodes based on the specified criteria. While all lift operations are retrieval operations, they can be broken down into "types" of lifts based on the criteria, comparison operator, or special handler used:

- [Lift by Form](storm_ref_lift.md#lift-form)
- [Lift by Property](storm_ref_lift.md#lift-prop)
- [Lift by Property Value - Standard Comparison Operators](storm_ref_lift.md#lift-prop-standard)
- [Lift by Property Value - Extended Comparison Operators](storm_ref_lift.md#lift-prop-extended)
- [Tag Lifts](storm_ref_lift.md#tag-lifts)

In addition, the specialized "reverse" keyword and the "try" operator can each be used with lift operations to modify their behavior:

- ["reverse" Keyword](storm_ref_lift.md#lift-reverse)
- ["Try" Operator](storm_ref_lift.md#lift-try)

> [!TIP]
> When performing lift operations, you can specify the name of an [Interface](../glossary.md#gloss-interface) to represent all forms that implement that interface. See the sections below for details and examples.

See [Storm Reference - Document Syntax Conventions](storm_ref_syntax.md#storm-ref-syntax) for an explanation of the syntax format used below.

See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details on special syntax or handling for specific data types.

<a id="lift-form"></a>

## Lift by Form

"Lift by form" operations return **all** nodes of that form in Synapse. The wildcard (asterisk) character ( `*` ) can be used to lift all nodes of all forms that match a partial form name / namespace.

If a form implements an [Interface](../glossary.md#gloss-interface), you can specify the interface name to lift all nodes of all forms that implement the interface.

> [!TIP]
> In a production instance of Synapse, lifting **all** nodes of a commonly used form (e.g., `inet:fqdn` or `inet:ip`) or lifting by an interface that is implemented by numerous forms (e.g. `it:host:event`) may return thousands or tens of thousands of nodes. Lifting by form or interface can be used with the Storm [limit](storm_ref_cmd.md#storm-limit) command to return only a specified number of nodes (for example, to view a sample of available data).

<a id="lift-form-name"></a>

### Lift by Form Name

A "lift by form name" operation returns all nodes for the specified [Form](data_model.md#data-form). This type of lift requires the name of the form whose nodes you want to lift.

**Syntax:**

*\<form\>*

**Examples:**

Lift all FQDNs (`inet:fqdn` nodes):

``` text
inet:fqdn
```

Lift all nodes representing articles (`doc:report` nodes):

``` text
doc:report
```

<a id="lift-form-wildcard"></a>

### Lift by Form Name - Wildcard

You can use the wildcard (asterisk) character ( `*` ) to specify all forms that match a partial form name. Use of the wildcard is not limited to form namespace boundaries.

> [!NOTE]
> The wildcard can only be used at the end of the partial form name match. It cannot be used at the beginning or in the middle of the form name. For example, both of the following are **invalid**:
>
> `*:header`
>
> `it:exec:*:del`
>
> In addition, use of the wildcard does not extend to partial matching of **property** names. For example, `entity:contact` is a form that has multiple `:place` secondary properties (e.g., `:place:name`, `:place:loc`). The following is **invalid** because it tries to match a partial property name:
>
> `entity:contact:place:*`

**Syntax:**

*\<partial_form_name\>* \*\*\*\*\*

**Examples:**

Lift all DNS A (`inet:dns:a`) and DNS AAAA (`inet:dns:aaaa`) nodes:

``` text
inet:dns:a*
```

<a id="lift-form-interface"></a>

### Lift Form by Interface

You can use the name of an [Interface](../glossary.md#gloss-interface) to lift all forms that implement that interface.

> [!NOTE]
> When lifting by interface, you cannot use the wildcard ( `*` ) character to match multiple interface names. Synapse will interpret use of the wildcard as an attempt to match multiple form names.

**Syntax:**

*\<interface\>*

**Examples:**

Lift all host event nodes (all nodes of all forms that implement the `it:host:event` interface):

``` text
it:host:event
```

Lift all taxonomy nodes (all nodes of all forms that implement the `meta:taxonomy` interface):

``` text
meta:taxonomy
```

<a id="lift-prop"></a>

## Lift by Property

A "lift by property" operation returns all nodes that **have** the specified [Property](data_model.md#data-prop) set, regardless of the property value. In most cases, this type of lift requires the full name (i.e., the combined form and property name) of the property you want to use to lift the nodes. When lifting by a meta property, the form name is only needed if you want to lift nodes of a specific form.

<a id="lift-prop-second"></a>

### Lift by Secondary Property

**Syntax:**

*\<form\>* **:** *\<prop\>*

**Examples:**

Lift the IP (`inet:ip`) nodes that have a location (`:place:loc`) property:

``` text
inet:ip:place:loc
```

Lift the PE (portable executable) metadata nodes (`file:mime:pe`) that have a PDB path (`:pdbpath` property):

``` text
file:mime:pe:pdbpath
```

<a id="lift-prop-interface"></a>

### Lift by Interface Property

If a form implements an [Interface](../glossary.md#gloss-interface) that defines a set or properties, you can lift all nodes of all forms that have that property by specifying the full name of the interface and its property.

**Syntax:**

*\<interface\>* **:** *\<prop\>*

**Examples:**

Lift the host event nodes (all nodes of all forms that implement the `it:host:event` interface) that have a `:time` property:

``` text
it:host:event:time
```

Lift the protocol request nodes (all nodes of all forms that implement the `inet:proto:request` interface) that have an associated network flow (i.e., that have a `:flow` property):

``` text
inet:proto:request:flow
```

<a id="lift-prop-meta"></a>

### Lift by Meta Property

**Syntax:**

\[ *\<form\>* \] **.** *\<prop\>*

A [Meta Property](../glossary.md#gloss-meta-prop) applies to any node and is automatically populated. Synapse uses two meta properties:

- `.created` a time which represents the date and time a node was created in Synapse.
- `.updated` a time which represents the date and time a node was last modified in Synapse.

**Examples:**

Lift all nodes in Synapse:

``` text
.created
```

> [!TIP]
> Because the `.created` property is automatically set for every node when it is first added to Synapse, lifting by the `.created` property effectively lifts every node in Synapse (technically, every node in the current [View](../glossary.md#gloss-view)).

<a id="lift-prop-extend"></a>

### Lift by Extended Property

**Syntax:**

*\<form\>* **:\_** *\<prop\>*

An [Extended Property](../glossary.md#gloss-extended-prop) is a custom property that has been added to the Synapse data model to capture specialized data for a given form. To avoid potential namespace collisions with standard properties, extended property names must begin with an underscore. In addition, we recommend using the name of the source or vendor of the property data as the first property namespace element.

**Examples:**

Lift the files (`file:bytes` nodes) that have a VirusTotal reputation extended property (`:_virustotal:reputation`):

``` text
file:bytes:_virustotal:reputation
```

> [!NOTE]
> The `:_virustotal:reputation` extended property is added to the Synapse data model by the [Synapse-VirusTotal](/docs/synapse-virustotal/latest/index.md) Power-Up.

<a id="lift-prop-standard"></a>

## Lift by Property Value - Standard Comparison Operators

A "lift by property value" operation returns the node(s) whose property matches the specified value. This type of lift requires:

- the form name or full property name (i.e., the combined form and property name) that you will use to lift the node(s);
- a [Comparison Operator](../glossary.md#gloss-comp-operator) to specify how the property value should be evaluated; and
- the property value.

A "lift by property value" can be performed using primary, secondary, or extended properties.

> [!TIP]
> When lifting by a secondary property value, you can specify either a form name or an [Interface](../glossary.md#gloss-interface) name.

In Synapse, we define **standard comparison operators** as the following set of operators:

- equal to ( `=` )
- less than ( `<` )
- greater than ( `>` )
- less than or equal to ( `<=` )
- greater than or equal to ( `>=` )

The ["Try" Operator](storm_ref_lift.md#lift-try) ( `?=` ) can optionally be used in place of the standard equal to operator ( `=` ). Use of the try operator is generally not required for interactive Storm queries, but may be useful for more complex Storm queries (such as automation or Storm-based ingest queries).

The most commonly used standard comparison operator is the equal to ( `=` ) operator. Comparison operators that expect a **quantity** (i.e., the inequality symbols `<`, `>`, `<=`, and `>=`) can only be used with properties whose type supports the comparison (e.g., integers, dates/times, etc.)

> [!TIP]
> IP addresses (`inet:ip` nodes) are stored as their decimal integer equivalents (even though they are displayed in human friendly format), and can be used with the various inequality operators:
>
> ``` text
> inet:ip < 192.168.0.0
> ```
>
> IPv6 addresses can also be used with the various inequality operators if enclosed in single or double quotes:
>
> ``` text
> inet:ip >= '::0'
> ```

<a id="lift-prop-std-primary"></a>

### Lift by Primary Property Value

**Syntax:**

*\<form\>* *\<operator\>* *\<valu\>*

**Examples:**

Lift the FQDN `vertex.link`:

``` text
inet:fqdn = vertex.link
```

Lift the DNS A record (`inet:dns:a` node) showing that domain `woot.com` resolved to IP `1.2.3.4`:

``` text
inet:dns:a = (woot.com, 1.2.3.4)
```

Lift the organization (`ou:org` node) whose primary property is the specified guid (globally unique identifier):

``` text
ou:org = 4b0c2c5671874922ce001d69215d032f
```

Lift the Autonomous System (`inet:asn`) nodes whose AS number is less than 50:

``` text
inet:asn < 50
```

<a id="lift-prop-std-secondary"></a>

### Lift by Secondary Property Value

**Syntax:**

*\<form\>* **:** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples:**

Lift the organization (`ou:org` node) with the name `the vertex project`:

``` text
ou:org:name = "the vertex project"
```

Lift the DNS A records (`inet:dns:a` nodes) for the FQDN `hugesoft.org`:

``` text
inet:dns:a:fqdn = hugesoft.org
```

Lift the PE (portable executable) file metadata nodes (`file:mime:pe`) with a compiled time of `1992-06-19 22:22:17`:

``` text
file:mime:pe:compiled = '1992/06/19 22:22:17'
```

Lift the PE (portable executable) file metadata nodes (`file:mime:pe`) with a compiled time that falls within the year 2025:

``` text
file:mime:pe:compiled = 2025*
```

Lift the files (`file:bytes` nodes) whose size is less than 1MB:

``` text
file:bytes:size < 1000000
```

Lift the domain WHOIS records (`inet:whois:record` nodes) for FQDNs registered (created) after January 1, 2023:

``` text
inet:whois:record:created > 2023/01/01
```

Lift the reports (`doc:report` nodes) that were published during the year 2012 or earlier:

``` text
doc:report:published <= 2012*
```

Lift email messages (`inet:email:message` nodes) that were sent on April 22, 2026 or later:

``` text
inet:email:message:date >= 2026/04/22
```

**Usage Notes:**

- When lifting nodes by secondary property value where the value is a time (date / time), you do not need to use full `YYYY/MM/DD hh:mm:ss.mmm` syntax. Synapse allows the use of both lower resolution values (e.g., `YYYY/MM/DD`) and wildcard values (e.g., `YYYY/MM*`). In particular, wildcard syntax can be used to specify any values that match the wildcard expression. See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) types for a detailed discussion of these behaviors.

<a id="lift-prop-std-interface"></a>

### Lift by Interface Property Value

If a form implements an [Interface](../glossary.md#gloss-interface) that defines a set of properties, you can lift all nodes of all forms with a specific value for that property by using the name of the interface.

> [!TIP]
> Synapse returns results in lexical order (sorted, ascending to descending) based on the way the queried property is indexed. When using an interface to lift by secondary property, Synapse performs the lifts for each form in parallel, and yields the results in order. See the ["reverse" Keyword](storm_ref_lift.md#lift-reverse) section for additional discussion of this concept.

**Syntax:**

*\<interface\>* **:** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples:**

Lift the host event nodes (all nodes of all forms that implement the `it:host:event` interface) associated with the host name `ron-pc`:

``` text
it:host:event:host = { it:host:name=ron-pc }
```

> [!TIP]
> The `:host` property is a guid value (the guid of an `it:host` node). The example above uses a [Subquery](../glossary.md#gloss-subquery) to specify the host guid value using another Storm query (i.e., "The guid of the `it:host` node whose `:name` is `ron-pc`") instead of specifying the guid value directly. Subqueries are a useful way to work with guid forms by referencing nodes using more human-friendly secondary property values. See [Using Subqueries to Reference Nodes](storm_ref_subquery.md#subquery-ref-nodes) for a more detailed discussion.

Lift the host event nodes (all nodes of all forms that implement the `it:host:event` interface) that were observed on or after February 1, 2024:

``` text
it:host:event:time >= 2024/02/01
```

<a id="lift-prop-std-meta"></a>

### Lift by Meta Property Value

Synapse has two built-in meta properties:

- `.created` a time which represents the date and time a node was created in Synapse.
- `.updated` a time which represents the date and time a node was last modified in Synapse.

Times (date / time values) are stored as integers (epoch microseconds) in Synapse and can be lifted using any standard comparison operator.

The [Lift by Time or Interval (@=)](storm_ref_lift.md#lift-interval) and [Lift by Range (*range=)](storm_ref_lift.md#lift-range) extended comparison operators provide additional flexibility when lifting by times and intervals.

See also the [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) sections of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for additional details on working with times and intervals in Synapse.

**Syntax:**

\[ *\<form\>* \] **.** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples:**

Lift all nodes created after January 1, 2026:

``` text
.created >= 2024/01/01
```

<a id="lift-prop-std-extended"></a>

### Lift by Extended Property Value

When lifting by extended property value, you can use any standard comparison operator supported by the property's type. For example, if the extended property is a string, only the equal to ( `=` ) standard operator is supported. If the extended property is an integer, any of the standard operators can be used.

**Syntax:**

*\<form\>* **:\_** *\<prop\>* *\<operator\>* *\<pval\>*

**Example:**

Lift the files (`file:bytes` nodes) with a VirusTotal reputation score (`:_virustotal:reputation` extended property) less than -50:

``` text
file:bytes:_virustotal:reputation < -50
```

<a id="lift-prop-extended"></a>

## Lift by Property Value - Extended Comparison Operators

Storm supports a set of extended comparison operators (comparators) for specialized lift operations.

- [Lift by Regular Expression (~=)](storm_ref_lift.md#lift-regex)
- [Lift by Prefix (^=)](storm_ref_lift.md#lift-prefix)
- @@XNAMED@@Lift by Time or Interval (@=)@@
- [Lift by Range (\*range=)](storm_ref_lift.md#lift-range)
- [Lift by Set Membership (\*in=)](storm_ref_lift.md#lift-set)
- [Lift by Proximity (\*near=)](storm_ref_lift.md#lift-proximity)
- [Lift by (Arrays) (\*\[ \])](storm_ref_lift.md#lift-by-arrays)

Just as with standard comparison operators, lifting by property value with extended comparison operators requires:

- the form name or full property name (i.e., the combined form and property name) that you will use to lift the node(s);
- a [Comparison Operator](../glossary.md#gloss-comp-operator) to specify how the property value should be evaluated; and
- the property value.

Each extended comparison operator can be used with any kind of property (primary, secondary, meta, extended, or virtual) whose [Type](../glossary.md#gloss-type) is appropriate for the comparison used.

> [!TIP]
> When lifting by a secondary property value, you can specify either a form name or an [Interface](../glossary.md#gloss-interface) name.
>
> Synapse returns results in lexical order (sorted, ascending to descending) based on the way the queried property is indexed. When using an interface to lift by secondary property, Synapse performs the lifts for each form in parallel, and yields the results in order. See the ["reverse" Keyword](storm_ref_lift.md#lift-reverse) section for additional discussion of this concept.

<a id="lift-regex"></a>

### Lift by Regular Expression (~=)

The extended comparator `~=` is used to lift nodes based on PCRE-compatible regular expressions.

> [!TIP]
> **Lifting** nodes based on regular expression is a brute force operation and therefore inefficient. For performance purposes, we recommend lifting your initial working set using some other criteria, and then **filtering** by regular expression where possible.
>
> Alternatively, [Lift by Prefix (^=)](storm_ref_lift.md#lift-prefix) can be used to match the **beginning** of string-based properties as a more efficient alternative to lifting by regular expression.

**Syntax:**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **~=** *\<regex\>*

*\<interface\>* **:** *\<prop\>* **~=** *\<regex\>*

**Examples:**

Lift the reports (`doc:report` nodes) whose title includes the string `sandstorm`:

``` text
doc:report:title ~= sandstorm
```

Lift the organizations (`ou:org` nodes) whose name contains a string that starts with `v`, followed by 0 or more characters, followed by `x`:

``` text
ou:org:name ~= '^v.*x'
```

<a id="lift-prefix"></a>

### Lift by Prefix (^=)

Synapse performs prefix indexing on string and string-derived types, which optimizes lifting nodes whose *\<valu\>* or *\<pval\>* starts with a given prefix (substring). The extended comparator `^=` is used to lift nodes by prefix.

> [!NOTE]
> Extended string types that support dotted notation (such as the [loc](storm_ref_type_specific.md#type-loc) or [syn:tag](storm_ref_type_specific.md#type-syn-tag) types) have custom behaviors with respect to lifting and filtering by prefix.
>
> [inet:fqdn](storm_ref_type_specific.md#type-inet-fqdn) nodes are indexed in reverse string order so cannot be lifted using the prefix extended operator. However, reverse indexing allows wildcard ( `*` ) matching of the beginning of any FQDN string.
>
> See the relevant sections in the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for details.

**Syntax:**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **^=** *\<prefix\>*

*\<interface\>* **:** *\<prop\>* **^=** *\<prefix\>*

**Examples:**

Lift the email addresses (`inet:email` nodes) that start with `abuse`:

``` text
inet:email ^= abuse
```

Lift the organizations (`ou:org` nodes) whose name starts with `ministry`:

``` text
ou:org:name ^= ministry
```

Lift the Microsoft Office metadata nodes (all nodes of all forms that implement the `file:mime:msoffice` interface) whose `:author:name` starts with `DESKTOP`:

``` text
file:mime:msoffice:author:name ^= DESKTOP
```

Lift the tags (`syn:tag` nodes) in the `rep.alienvault` tree where the third tag element starts with the numeral `0`:

``` text
syn:tag ^= rep.alienvault.0
```

> [!TIP]
> Even though tag elements are dot-separated, when lifting `syn:tag` nodes by prefix the prefix string is not constrained to dot boundaries. In other words, a prefix lift used with tags can match a partial tag element. The query above will match all of the following tags:
>
> - `syn:tag=rep.alienvault.0_day`
> - `syn:tag=rep.alienvault.0_days`
> - `syn:tag=rep.alienvault.0day`
> - `syn:tag=rep.alienvault.0days`
> - `syn:tag=rep.alienvault.0ktapus`

<a id="lift-interval"></a>

### Lift by Time or Interval (@=)

Many forms include properties that are date / time values (*\<ptype\>* = *\<time\>*) or time windows / intervals (*\<ptype\>* = *\<ival\>*). The time/interval extended comparator `@=` is used to lift nodes based on comparisons among various combinations of times and intervals.

> [!TIP]
> See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for additional detail on the use and behavior of [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) data types.

**Syntax:**

*\<form\>* **:** \| **.** \| **:\_** *\<prop\>* **@=(** *\<ival_min\>* **,** *\<ival_max\>* **)**

*\<form\>* **:** \| **.** \| **:\_** *\<prop\>* **@=** *\<time\>*

*\<interface\>* **:** *\<prop\>* **@=(** *\<ival_min\>* **,** *\<ival_max\>* **)**

*\<interface\>* **:** *\<prop\>* **@=** *\<time\>*

**Examples:**

Lift the DNS A records (`inet:dns:a` nodes) whose `:seen` values fall between July 1, 2022 and August 1, 2022:

``` text
inet:dns:a:seen @= ( 2022/07/01, 2022/08/01 )
```

Lift the DNS requests (`inet:dns:request` nodes) that occurred on May 3, 2023 (between `05/03/2023 00:00:00` and `05/03/2023 23:59:59`):

``` text
inet:dns:request:time @= ( '2023/05/03 00:00:00', '2023/05/04 00:00:00' )
```

Lift the reports (`doc:report` nodes) that were published within the past day:

``` text
doc:report:published @= ( now, '-1 day' )
```

Lift the host event nodes (all nodes of all forms that implement the `it:host:event` interface) that occurred within the past three hours:

``` text
it:host:event:time @= (now, '-3 hours')
```

**Usage Notes:**

- When specifying an interval with the `@=` operator, the minimum value is included in the interval for comparison purposes but the maximum value is **not**. This is equivalent to "greater than or equal to *\<min\>* and less than *\<max\>*". This behavior differs from that of the `*range=` operator, which includes **both** the minimum and maximum.

- **Comparing intervals to intervals:** when using an interval with the `@=` operator to lift nodes based on an interval property, Synapse returns nodes whose interval value has **any** overlap with the specified interval. For example:

  - A lift interval of September 1, 2018 to October 1, 2018 ( 2018/09/01, 2018/10/01 ) will match nodes with any of the following intervals:
    - August 12, 2018 to September 6, 2018 ( 2018/08/12, 2018/09/06 ).
    - September 13, 2018 to September 17, 2018 ( 2018/09/13, 2018/09/17 ).
    - September 30, 2018 to November 5, 2018 ( 2018/09/30, 2018/11/05 ).

- **Comparing intervals to times:** When using an interval with the `@=` operator to lift nodes based on a time property, Synapse returns nodes whose time value falls within the specified interval.

- **Comparing times to times:** When using a time with the `@=` operator to lift nodes based on a time property, Synapse returns nodes whose timestamp is an **exact match** of the specified time. In other words, in this case the interval comparator ( `@=` ) behaves like the equal to comparator ( `=` ).

- When specifying date / time and interval values, Synapse allows the use of both lower resolution values (e.g., `YYYY/MM/DD`), and wildcard values (e.g., `YYYY/MM*`). Wildcard time syntax may provide a simpler and more intuitive means to specify some intervals. For example `inet:whois:rec:asof=2018*` is equivalent to `inet:whois:rec:asof@=('2018/01/01', '2019/01/01')`.

- Time-based keywords (such as `now`) and relative time syntax (expressions such as `+-1 hour` or `-7 days`) can be used for interval values.

  See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) types for a detailed discussion of these behaviors.

<a id="lift-range"></a>

### Lift by Range (\*range=)

The range extended comparator (`*range=`) supports lifting nodes whose *\<form\>* = *\<valu\>* or *\<prop\>* = *\<pval\>* fall within a specified range of values. The comparator can be used with types such as integers and times.

> [!NOTE]
> The `*range=` operator cannot be used to compare a time range with a property value that is an interval (`ival` type). The interval ( `@=` ) operator should be used instead.
>
> The `*range=` operator can be used to lift `inet:ip` values. However, ranges of [inet:ip](storm_ref_type_specific.md#type-inet-ip) nodes can also be lifted directly by specifying the lower and upper addresses in the range using `<min>-<max>` format. For example:
>
> `inet:ip = 192.168.0.0-192.168.0.10`
>
> For IPv6 values, the range must be enclosed in quotes:
>
> `inet:ip = "::0-ff::ff"`

**Syntax:**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

*\<interface\>* **:** *\<prop\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

**Examples:**

Lift the files (`file:bytes` nodes) whose size is between 1000 and 100000 bytes:

``` text
file:bytes:size *range= ( 1000, 100000 )
```

Lift the files (`file:bytes` nodes) whose VirusTotal reputation score (`:_virustotal:reputation` extended property) is between -20 and 20:

``` text
file:bytes:_virustotal:reputation *range= ( -20, 20 )
```

Lift the DNS requests (`inet:dns:request` nodes) that were made between November 29, 2025 and January 14, 2026:

``` text
inet:dns:request:time *range= ( 2025/11/29, 2026/01/14 )
```

Lift the HTTP requests (`inet:http:request` nodes) made within one day of December 1, 2024:

``` text
inet:http:request:time *range= ( 2024/12/01, '+-1 day' )
```

**Usage Notes:**

- When specifying a range, **both** the minimum and maximum values are **included** in the range. This is the equivalent of "greater than or equal to *\<min\>* and less than or equal to *\<max\>*").
- When specifying a range of time values, Synapse allows the use of both lower resolution values (e.g., `YYYY/MM/DD`) and wildcard values (e.g., `YYYY/MM*`) for the minimum and/or maximum range values. In some cases, wildcard time syntax may provide a simpler and more intuitive means to specify some time ranges. For example `inet:whois:rec:asof=2018*` is equivalent to `inet:whois:rec:asof*range=('2018/01/01', '2018/12/31 23:59:59.999')`. See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) types for a detailed discussion of these behaviors.
- When using keywords (such as `now`) or relative values (such as `-1 hour`) to specify a range of times, the first value in the range is calculated relative to the current time and the second value is calculated relative to the first value.
- If you specify a range value that is nonsensical or exclusionary (such as `( 47, 16 )`), Synapse will **not** generate an error and will simply fail to return results. (The expression is syntactically correct, but no value is both greater than 47 and less than 16).

<a id="lift-set"></a>

### Lift by Set Membership (\*in=)

The set membership extended comparator (`*in=`) supports lifting nodes whose *\<form\> = \<valu\>* or *\<prop\> = \<pval\>* matches any of a set of specified values. The comparator can be used with any type.

**Syntax:**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

*\<interface\>* **:** *\<prop\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

**Examples:**

Lift entity names (`entity:name` nodes) matching any of the specified values:

``` text
entity:name *in= ( fsb, gru, 'yevgeniy prigozhin', 'vladimir putin' )
```

Lift the IP addresses (`inet:ip` nodes) associated with any of the specified Autonomous System (AS) numbers:

``` text
inet:ip:asn *in= ( 9009, 20473, 44477 )
```

Lift the tags (`syn:tag` nodes) whose final tag element matches any of the specified string values:

``` text
syn:tag:base *in= ( plugx, korplug, sogu, kaba )
```

<a id="lift-proximity"></a>

### Lift by Proximity (\*near=)

The proximity extended comparator (`*near=`) supports lifting nodes by "nearness" to another node. Currently, `*near=` supports proximity based on geospatial location (i.e., nodes within a given radius of a specified latitude / longitude).

**Syntax:**

*\<form\>* **:** \| **.** \| **:\_** *\<prop\>* **\*near = ((** *\<lat\>* **,** *\<long\>* **),** *\<radius\>* **)**

**Examples:**

Lift the locations (`geo:place` nodes) within 500 meters of the Russian Cryptographic Museum (where the coordinates 55.83069,37.59781 represent the Museum's location):

``` text
geo:place:latlong *near= ( (55.83069, 37.59781), 500m )
```

**Usage Notes:**

- Radius can be specified in the following units. The terms recognized by Storm are listed in parentheses. For example, radius can be specified as 2km or '2 km' or '0.5 meters' or '6 feet' (distance expressions that contain spaces need to be enclosed in single or double quotes):
  - Kilometers ( `km` / `kilometer` / `kilometers` )
  - Meters ( `m` / `meter` / `meters` )
  - Centimeters ( `cm` / `centimeter` / `centimeters` )
  - Millimeters ( `mm` / `millimeter` / `millimeters` )
  - Miles ( `mile` / `miles` )
  - Yards ( `yard` / `yards` )
  - Feet ( `foot` / `feet` )
- Radius values of less than 1 must be specified with a leading zero (e.g., 0.5km).
- The `*near=` comparator works for geospatial data by lifting nodes within a square bounding box centered at *\<lat\>,\<long\>*, then filters the nodes returned by ensuring that they are within the great-circle distance given by the *\<radius\>* argument.

<a id="lift-by-arrays"></a>

### Lift by (Arrays) (\*\[ \])

Storm uses a special syntax to lift (or filter) by comparison with one or more elements of an [array](storm_ref_type_specific.md#type-array) type. The syntax consists of an asterisk ( `*` ) preceding a set of square brackets ( `[ ]` ), where the square brackets contain a comparison operator and a value that can match one or more elements in the array. This allows users to match values in the array list without needing to know the exact order or values of the array itself.

**Syntax:**

*\<form\>* **:** \| **.** \| **:\_** *\<prop\>* **\[** *\<operator\>* *\<pval\>* **\]**

**Examples:**

Lift the x509 certificates (`crypto:x509:cert` nodes) that reference FQDNs ending with `.xyz`:

``` text
crypto:x509:cert:identities:fqdns *[ = '*.xyz' ]
```

Lift the threat clusters (`risk:threat` nodes) whose secondary (alternate) names include the string `dragon`:

``` text
risk:threat:names *[ ~= dragon ]
```

**Usage Notes:**

- The comparison operator used must be valid for lift operations for the type used in the array. For example, [inet:fqdn](storm_ref_type_specific.md#type-inet-fqdn) suffix matching (i.e., `crypto:x509:cert:identities:fqdns *[ = '*.com' ]`), can be used when lifting arrays consisting of domains, but the prefix operator ( `^=` ), which is only valid when **filtering** `inet:fqdns`, cannot.

- The standard equals ( `=` ) operator can be used to filter nodes based on array properties, but the value specified must **exactly match** the **full** property value in question. For example:

  `ou:org:names=( "the vertex project", "the vertex project llc", vertex )`

- See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) document for additional details.

<a id="tag-lifts"></a>

## Tag Lifts

Tags in Synapse can represent observations or assessments. They are used to provide context to nodes (in the form of "labels" applied to nodes) and to group related nodes.

Storm supports lifting nodes based on the tag(s) applied to the node, as well lifting based on tag timestamps, tag properties, or tag property values.

The "hashtag" symbol ( `#` ) is used to specify a tag name when lifting by tag.

> [!NOTE]
> Synapse does not include any pre-defined tags (although some Power-Ups may create tags defined within the Power-Up itself). The examples below are based on tags and tag conventions used by The Vertex Project.

<a id="lift-by-tag"></a>

### Lift by Tag

A "lift by tag" operation lifts **all** nodes that have the specified tag.

**Syntax:**

**\#** *\<tag\>*

**Examples:**

Lift all nodes that ESET associates with Sednit (`#rep.eset.sednit`):

``` text
#rep.eset.sednit
```

Lift all nodes associated with anonymized infrastructure (`#cno.infra.anon`):

``` text
#cno.infra.anon
```

> [!TIP]
> Tags are hierarchical, and each tag element is its own tag; the tag `#cno.infra.anon` consists of the tags `#cno`, `#cno.infra`, and `#cno.infra.anon`. Lifting nodes using a tag "higher up" in the tag hierarchy will lift all nodes with specified tag or any tag "lower down" in the hierarchy. In other words, lifting by `#cno.infra.anon` will lift "anonymized" infrastructure, whether the infrastructure is a VPN (`#cno.infra.anon.vpn`), a TOR node (`#cno.infra.anon.tor`), or an anonymous proxy (`#cno.infra.anon.proxy`).

<a id="lift-form-by-tag"></a>

### Lift Form by Tag

Lift form by tag lifts only those nodes of the specified form that have a particular tag.

**Syntax:**

*\<form\>* **\#** *\<tag\>*

**Examples:**

Lift the FQDNs (`inet:fqdn` nodes) that ESET associates with Sednit (`#rep.eset.sednit`):

``` text
inet:fqdn#rep.eset.sednit
```

Lift the IP addresses (`inet:ip` nodes) associated with DNS sinkhole infrastructure (`#cno.infra.dns.sink.hole`):

``` text
inet:ip#cno.infra.dns.sink.hole
```

> [!TIP]
> A "lift form by tag" operation is equivalent to a "lift and filter" operation that first lifts **all** nodes of the specified form, and then filters the results to **only** those nodes with the specified tag. This set of operations is potentially resource-intensive and inefficient (why lift **all** nodes only to discard most of them?). Instead, Synapse specifically optimizes "lift form by tag" operations to **only** lift nodes that have the tag.
>
> In fact, if you specify a Storm query such as `inet:fqdn +#rep.mandiant.apt1`, Synapse will execute the query as if you had specified the "lift form by tag" query `inet:fqdn#rep.mandiant.apt1`. In other words, in some cases Synapse knows to "do what you mean" in order to process your queries more efficiently.

<a id="lift-tag-timestamp"></a>

### Lift Using Tag Timestamps

A tag timestamp can be thought of as a specialized "property" of a tag that happens to be a date / time range (interval). You can lift nodes based on tag timestamp values using any comparison operator supported by interval ([ival](storm_ref_type_specific.md#type-ival) types). The time / interval extended operator ( `@=` ) is used most often, but equal to ( `=` ) can also be used to **exact** match the values in the interval.

See [Lift by Time or Interval (@=)](storm_ref_lift.md#lift-interval) for additional detail on the use of the `@=` operator.

**Syntax:**

\[ *\<form\>* \] **\#** *\<tag\>* **@=** *\<time\>* \| **(** *\<min_time\>* **,** *\<max_time\>* **)**

Lift the nodes that were associated with anonymous VPN infrastructure (`#cno.infra.anon.vpn`) between December 1, 2023 and January 1, 2024:

``` text
#cno.infra.anon.vpn @= ( 2023/12/01, 2024/01/01 )
```

Lift the FQDNs (`inet:fqdn` nodes) that were owned / controlled by Threat Cluster 15 (`#cno.threat.t15.own`) as of October 30, 2021:

``` text
inet:fqdn#cno.threat.t15.own @= 2021/10/30
```

Lift the IP addresses (`inet:ip` nodes) that were TOR exit nodes (`#cno.infra.anon.tor.exit`) between April 1, 2023 and July 1, 2023:

``` text
inet:ip#cno.infra.anon.tor.exit @= ( 2023/04/01, 2023/07/01 )
```

<a id="lift-tag-prop"></a>

### Lift Using Tag Properties

[Tag Properties](analytical_model.md#tag-properties) can be used to provide additional context to tags. Storm supports lifting nodes whose tags have a specific tag property (regardless of the value of the property).

> [!NOTE]
> In many cases, information previously recorded using a tag property is better suited to the use of an [Extended Property](../glossary.md#gloss-extended-prop).

**Syntax:**

\[ *\<form\>* \] **\#** *\<tag\>* **:** *\<tagprop\>*

Lift the nodes with a `:_risk` tag property reported by Symantec (`#rep.symantec:_risk`):

``` text
#rep.symantec:_risk
```

Lift the FQDNs (`inet:fqdn` nodes) with a `:_risk` tag property reported by Symantec (`#rep.symantec:_risk`):\*

``` text
inet:fqdn#rep.symantec:_risk
```

> [!NOTE]
> You must specify a tag associated with the tag property. It is not possible to lift nodes based on a particular tag property being present on **any** tag (e.g., Storm queries such as `#:_risk` or `inet:fqdn#:_risk` will generate `BadSyntax` errors).

<a id="lift-tag-prop-value"></a>

### Lift Using Tag Property Values

Storm supports lifting nodes based on the value of a tag property (similar to lifting by the value of a node property).

You can lift nodes based on tag property values using any comparison operator supported by the property's [Type](../glossary.md#gloss-type). For example, if the tag property is defined as an integer (`int`) type, you can use any comparison operator supported by integers.

The ["Try" Operator](storm_ref_lift.md#lift-try) ( `?=` ) can optionally be used in place of the standard equal to operator ( `=` ) for tag property values. Use of the try operator is generally not required for interactive Storm queries, but may be useful for more complex Storm queries (such as automation or Storm-based ingest queries).

**Syntax:**

\[ *\<form\>* \] **\#** *\<tag\>* **:** *\<tagprop\>* *\<operator\>* *\<pval\>*

Lift the nodes with a `:_risk` tag property value of 100 as reported by ESET (`#rep.eset:_risk`):

``` text
#rep.eset:_risk = 100
```

Lift the FQDNs (`inet:fqdn` nodes) with a `:_risk` tag property value greater than 90 as reported by DomainTools (`#rep.domaintools:_risk`):

``` text
inet:fqdn#rep.domaintools:_risk > 90
```

Lift the FQDNs (`inet:fqdn` nodes) with a `:_risk` tag property with a value between 45 and 70 as reported by Symantec (`#rep.symantec:_risk`):

``` text
inet:fqdn#rep.symantec:_risk *range= ( 45, 70 )
```

<a id="lift-tag-recursive"></a>

### Recursive Tag Lift (##)

Tags can be applied to `syn:tag` nodes to record additional information about the the observation represented by the `syn:tag` node itself. In other words, tags (labels) can be used to provide additional context about tags (`syn:tag` nodes).

The ability to "tag the tags" can be used to represent certain types of analytical relationships. For example:

- `syn:tag` nodes representing threat groups can be tagged to indicate their assessed country of origin.
- `syn:tag` nodes representing malware or tools can be tagged with their assessed availability (e.g., public, private, private but shared, etc.)

A recursive tag lift retrieves all nodes with the specified tag. If the results include any `syn:tag` nodes, the recursive lift will also lift any nodes with those tags. The process continues until no more `syn:tag` nodes are returned.

The final result set returned by a recursive tag lift includes all of the nodes that were lifted recursively, but will **not** include any lifted `syn:tag` nodes themselves.

The "double hashtag" symbol ( `##` ) is used to specify a recursive tag lift.

> [!NOTE]
> "Tag the tags" is one approach to provide context to things that tags represent and may be suitable for some use cases. However, the Synapse data model now includes **forms** to represent objects or concepts that are commonly associated with tags, and that can be linked to their associated tag via a `:tag` secondary property. For example, a `risk:threat` node can represent Microsoft's reporting on Forest Blizzard, with a `:tag` property that could be set to `rep.microsoft.forest_blizzard`. The node can be used to record additional context about Microsoft's Forest Blizzard, including things like when the group was active, alternate names used in reporting, and so on. In short, using a form that is linked to a tag and has secondary properties to provide context gives you greater flexibility to record that context (vs. "tag the tags") and simplifies lifting, filtering, and pivoting across similar nodes.
>
> See [Tags Associated with Nodes](analytical_model.md#analytical-tags-asnodes) for a brief discussion of this concept, or the [User Guide](/docs/synapse-enterprise-optic/latest/user_interface/userguide.md) for the [Vertex-Threat-Intel](/docs/vertex-threat-intel/latest/index.md) Power-Up (in particular, the [Threat Intel Model](/docs/vertex-threat-intel/latest/ugmodel.md) section) for additional examples.

**Syntax:**

**\##** *\<tag\>*

**Example:**

You are using "availability" tags to show the general availability of malware or tools reported by Mandiant. You add the appropriate "availability" tag to the `syn:tag` node that represents the associated malware. For example, you apply the tag `#rep.mandiant.avail.public` to the node `syn:tag=rep.mandiant.gh0st` because Mandiant reported that the source code for the Gh0st backdoor is publicly available.

Lift the nodes (e.g., indicators of compromise) associated with any malware family or tool that Mandiant reports is publicly available:

``` text
##rep.mandiant.avail.public
```

The query above will:

- Lift the nodes tagged `#rep.mandiant.avail.public`, such as `syn:tag` nodes for tools or malware families that Mandiant assesses are publicly available (e.g., `syn:tag=rep.mandiant.gh0st` or `syn:tag=rep.mandiant.beacon`).
- Lift any nodes tagged with those tags (e.g., `#rep.mandiant.gh0st` or `#rep.mandiant.beacon`). This would typically include IOCs such as hashes, FQDNs, IPs, URLs, etc.
- If any nodes tagged with the additional tags (`#rep.mandiant.gh0st`, etc.) are `syn:tag` nodes, repeat the process, continuing until no more `syn:tag` nodes are lifted.
- Return the recursively lifted set of nodes (excluding any `syn:tag` nodes).

<a id="lift-reverse"></a>

## "reverse" Keyword

Synapse indexes property values so that data (nodes) can be lifted (retrieved) and returned quickly. By default, lift results are returned in lexical order (i.e., sorted in ascending order), based on the property specified in the lift (primary, secondary, meta, extended, or virtual) and the way the property is indexed.

The `reverse` keyword can be used to return the specified nodes in reverse lexical order (i.e., sorted in descending order). To perform a "reverse" lift, specify the `reverse` keyword and enclose the lift operation in parentheses.

A "reverse" lift can be followed by additional Storm operations (pivots, filters, commands) just like a "normal" lift.

> [!TIP]
> When using the `reverse` keyword to lift by secondary property value using an [Interface](../glossary.md#gloss-interface) name, Synapse performs the lifts for each form in parallel, and yields the results in descending order. For example, the following query will return all nodes of all forms that implement the `it:host:event` interface that have a `:time` value greater than or equal to 2024/02/01, sorted in descending order (most recent first):
>
> ``` text
> reverse (it:host:event:time >= 2024/02/01)
> ```

**Syntax:**

**reverse (** *\<lift\>* **)**

**Examples:**

Lift IP addresses (`inet:ip` nodes) with a `:place:loc` property (sorted descending based on the `:place:loc` property value):

```stormdoc
storm> reverse ( inet:ip:place:loc )
inet:ip=197.155.229.194
        :place:loc = zw.ha.harare
        :type = unicast
        :version = 4
inet:ip=41.221.147.14
        :place:loc = zw
        :type = unicast
        :version = 4
inet:ip=41.164.23.42
        :place:loc = za.wc.worcester
        :type = unicast
        :version = 4
inet:ip=155.254.9.3
        :place:loc = us.mt.three forks
        :type = unicast
        :version = 4
inet:ip=102.64.66.222
        :place:loc = tz.02.dar es salaam
        :type = unicast
        :version = 4
```

Lift five IP addresses (`inet:ip` nodes) (sorted descending based on the integer value of the `inet:ip` primary property):

```stormdoc
storm> reverse ( inet:ip ) | limit 5
inet:ip=2607:9000:0:85:68a3:75b4:13ab:770a
        :scope = global
        :type = unicast
        :version = 6
        #cno.infra.anon.vpn = 2023-08-15T00:12:15Z - 2023-12-05T23:12:54Z
inet:ip=2600:1419:9c00:283::356e
        :scope = global
        :type = unicast
        :version = 6
inet:ip=255.255.255.255
        :type = private
        :version = 4
inet:ip=223.159.33.195
        :type = unicast
        :version = 4
inet:ip=198.42.76.23
        :type = unicast
        :version = 4
```

Lift the five most recently-created email addresses (`inet:email` nodes) (sorted descending by the `.created` property value):

```stormdoc
storm> reverse ( inet:email.created ) | limit 5
inet:email=illia.volochii@gmail.com
        :fqdn = gmail.com
        :username = illia.volochii
inet:email=dholth@fastmail.fm
        :fqdn = fastmail.fm
        :username = dholth
inet:email=alex.gronholm@nextday.fi
        :fqdn = nextday.fi
        :username = alex.gronholm
inet:email=support@hammer-software.com
        :fqdn = hammer-software.com
        :username = support
inet:email=20231128124623.11d85d83ed11a341@adnoc.ae
        :fqdn = adnoc.ae
        :username = 20231128124623.11d85d83ed11a341
```

> [!NOTE]
> In some cases, Synapse uses specialized indexing to optimize specific Storm operations (such as the ability to lift forms by tag) or to make it easier to work with certain types of data (type-specific behavior). For example, FQDN strings (`inet:fqdn` types) are reversed before being indexed.
>
> Where specialized indexing is used, both "normal" and "reverse" lifts still return nodes in lexical or reverse lexical order, respectively. However, the "sort order" of the results may not be apparent, based on the custom criteria used to index the nodes.
>
> See the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) section for details on some type-specific behaviors, including any custom indexing for the listed types.

<a id="lift-try"></a>

## "Try" Operator

The Storm "try" operator ( `?=` ) can be used in lift operations as an alternative to the equal to ( `=` ) comparison operator.

Properties in Synapse are subject to [Type Enforcement](../glossary.md#gloss-type-enforce). Type enforcement makes a reasonable attempt to ensure that a value "makes sense" for the property in question - that the value you specify for an `inet:ip` node looks reasonably like an IP address (and not an FQDN or URL). If you try to lift a set of nodes using a property value that does not pass Synapse's type enforcement validation, Synapse will generate an error. The error will cause the currently executing Storm query to halt and stop processing. For example, the following query halts based on the bad value (`evil.com`) provided for an `inet:ip` node:

```stormdoc
storm> inet:ip = evil.com inet:ip = 8.8.8.8
ERROR: Invalid IP address: evil.com
```

When using the try operator ( `?=` ), Synapse will to attempt (try) to lift the node(s) using the specified property value. However, instead of halting in the event of an error, Synapse will ignore the error (silently fail on that specific lift operation) but continue processing the rest of the Storm query. Using the try operator below, Synapse ignores the bad value for the first IP address but returns the second one:

```stormdoc
storm> inet:ip ?= evil.com inet:ip ?= 8.8.8.8
inet:ip=8.8.8.8
        :type = unicast
        :version = 4
        #rep.domaintools:_risk = 42
```

The try operator is generally not necessary for interactive Storm queries. However, it can be very useful for more complex Storm queries or Storm-based automation (see [Storm Reference - Automation](storm_ref_automation.md#storm-ref-automation)), where a single badly-formatted lift operation (potentially relying on input or data from a third-party data source) could cause the query to fail during execution.

> [!TIP]
> The try operator can also be used when lifting using an [Interface](../glossary.md#gloss-interface).

**Syntax:**

*\<form\>* **?=** *\<valu\>*

*\<form\>* **:** *\<prop\>* **?=** *\<pval\>*

*\<interface\>* **:** *\<prop\>* **?=** *\<pval\>*

> [!TIP]
> See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for specialized "try" syntax when working with array properties.

**Examples:**

Try to lift the MD5 (`crypto:hash:md5` node) `174cc541c8d9e1accef73025293923a6`:

```stormdoc
storm> crypto:hash:md5 ?= 174cc541c8d9e1accef73025293923a6
crypto:hash:md5=174cc541c8d9e1accef73025293923a6
```

Try to lift the DNS A records (`inet:dns:a` nodes) whose `:ip` property is `192.168.0.100`:

```stormdoc
storm> inet:dns:a:ip ?= 192.168.0.100
inet:dns:a=('woot.com', '192.168.0.100')
        :fqdn = woot.com
        :ip = 192.168.0.100
```

Try to lift the email addresses (`inet:email` nodes) for `ron@vertex.link` and `ozzie@vertex.link`:

In the example below, note that despite the first email address being entered incorrectly (using `[at]`), the error message is suppressed, and the query executes to completion.

```stormdoc
storm> inet:email ?= 'ron[at]vertex.link' inet:email ?= 'ozzie@vertex.link'
inet:email=ozzie@vertex.link
        :fqdn = vertex.link
        :username = ozzie
```

Try to lift the Microsoft Office document metadata nodes (all nodes of all forms that implement the `file:mime:msoffice` interface) whose `:author:name` property is `Rafael Moon`:

``` text
file:mime:msoffice:author:name ?= 'Rafael Moon'
```
