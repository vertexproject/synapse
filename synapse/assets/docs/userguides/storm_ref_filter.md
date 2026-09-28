<a id="storm-ref-filter"></a>

# Storm Reference - Filtering

Filter operations are performed on the output of a previous Storm operation such as a lift or pivot. A filter operation downselects from the working set of nodes by either including or excluding a subset of nodes based on specified criteria.

- `+` specifies an **inclusion** filter. The filter downselects the working set to **only** those nodes that match the specified criteria.
- `-` specifies an **exclusion** filter. The filter downselects the working set to all nodes **except** those that match the specified criteria.

Similar to lift operations ([Storm Reference - Lifting](storm_ref_lift.md#storm-ref-lift)), filter operations can be broken down into kinds of filters based on the criteria, comparison operator, or special handler used:

- [Filter by Form](storm_ref_filter.md#filter-form)
- [Filter by Property](storm_ref_filter.md#filter-prop)
- [Filter by Property Value - Standard Comparison Operators](storm_ref_filter.md#filter-by-property-value---standard-comparison-operators)
- [Filter by Property Value - Extended Comparison Operators](storm_ref_filter.md#filter-prop-extended)
- [Tag Filters](storm_ref_filter.md#tag-filter)

> [!TIP]
> In general, you can filter using the same criteria and comparison operators used for lift operations. This includes using a wildcard ( `*` ) to partially match form names, using [interface](../glossary.md#gloss-interface) names to filter by all forms that implement an interface, or using the name of a [base form](../glossary.md#gloss-form-base) or [parent form](../glossary.md#gloss-form-parent) to filter by all forms that [inherit](../glossary.md#gloss-form-inheritance) from that form.
>
> Because filter operations act on a pre-selected **subset** of nodes, you can filter using some methods that are less efficient when used for initial lift operations. For example, you can filter FQDNs (`inet:fqdn` nodes) by prefix ( `^=` ), although you cannot lift FQDNs using that operator. Similarly, you can [Filter by Tag Globs](storm_ref_filter.md#filter-tag-globs) but you cannot lift using that syntax.

Storm also supports specialized filters and filter operations:

- [Compound Filters](storm_ref_filter.md#filter-compound)
- [Subquery Filters](storm_ref_filter.md#filter-subquery)
- [Expression Filters](storm_ref_filter.md#filter-expression)
- [Embedded Property Syntax](storm_ref_filter.md#embed_prop_syntax)

See [Storm Reference - Document Syntax Conventions](storm_ref_syntax.md#storm-ref-syntax) for an explanation of the syntax format used below.

See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details on special syntax or handling for specific data types.

<a id="filter-form"></a>

## Filter by Form

A **filter by form** operation modifies your working set to include (or exclude) all nodes of the specified form.

You can filter using an individual form name, an interface name, a base or parent form name, or using the wildcard (asterisk) character ( `*` ) to filter based on forms that match a partial form name / namespace.

<a id="filter-form-name"></a>

### Filter by Form Name

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>*

**Examples:**

Filter the current working set to only include fully qualified domain names (FQDNs):

```text
<query> +inet:fqdn
```

Filter the current working set to exclude URLs:

```text
<query> -inet:url
```

<a id="filter-form-wildcard"></a>

### Filter by Form Name - Wildcard

You can use the wildcard (asterisk) character ( `*` ) to specify all forms that match a partial form name. Use of the wildcard is **not** limited to form namespace boundaries.

> [!NOTE]
> If the wildcard expression matches the name of a [parent form](../glossary.md#gloss-form-parent), the query will **also** filter forms extended by the parent as part of [form inheritance](../glossary.md#gloss-form-inheritance), even if the extended form name does not match the wildcard expression. This is the same behavior as [Filter by Parent Form](storm_ref_filter.md#filter-form-parent) using an explicit form name.

**Syntax:**

*\<query\>* **+** \| **-** *\<partial_form_name\>* **\***

**Examples:**

Filter the current working set to exclude DNS nodes (e.g., `inet:dns:a`, `inet:dns:mx`, `inet:dns:request`):

```text
<query> -inet:dns:*
```

Filter the current working set to only include antivirus / scan-related nodes (e.g., `it:av:scan:result`, `it:av:signame`):

```text
<query> +it:av:s*
```

**Usage Notes**

- The wildcard character ( `*` ) can only be used to match form names. It cannot be used to match [interface](../glossary.md#gloss-interface) names.
- The wildcard can only be used at the end of the partial form name match. It cannot be used at the beginning or in the middle of the form name. For example, the following are both **invalid**:
  
```text
+*:header
```
  
```text
-it:exec:*:add
```
  
- The wildcard cannot be used to match property names. For example, `entity:contact` is a form that has multiple `:place` secondary properties (e.g., `:place:name`, `:place:loc`). The following is **invalid** because it tries to match a partial property name:
  
```storm
+entity:contact:place:*
```

<a id="filter-form-interface"></a>

### Filter Form by Interface

You can use the name of an [interface](../glossary.md#gloss-interface) to filter all nodes of all forms that implement that interface.

> [!NOTE]
> When filtering by interface, you cannot use the wildcard ( `*` ) character to match multiple interface names. Synapse will interpret use of the wildcard as an attempt to match multiple form names.

**Syntax:**

*\<query\>* **+** \| **-** *\<interface\>*

**Examples:**

Filter the current working set to exclude all hash nodes (all nodes of all forms that implement the `crypto:hash` interface):

```text
<query> -crypto:hash
```

Filter the current working set to only include host event nodes (all nodes of all forms that implement the `it:host:event` interface):

```text
<query> +it:host:event
```

<a id="filter-form-parent"></a>

### Filter Form by Parent Form

Forms can make use of [form inheritance](../glossary.md#gloss-form-inheritance). Similar to class inheritance in object-oriented programming, Synapse allows you to define a **parent form** and create more specific forms that **inherit** the properties of the parent (and optionally extend the parent with additional properties).

You can use the name of a parent form to filter all nodes of the parent form, and all nodes of all forms that extend the parent.

**Syntax:**

*\<query\>* **+** \| **-** *\<parent_form\>*

> [!TIP]
> Where *\<form\>* is used in a query syntax example, it refers to **any** form (including parent forms, or forms that extend a parent form). We use *\<parent_form\>* here to emphasize this particular use case.

**Examples:**

Filter the current working set to only include all of the `it:host:account` nodes and all nodes of all forms that extend `it:host:account`:

```text
<query> +it:host:account
```

<a id="filter-prop"></a>

## Filter by Property

A **filter by property** operation modifies your working set to include (or exclude) all forms that **have** the specified [property](data_model.md#data-prop) set, regardless of the property value. Property filters work the same way regardless of the kind of property (e.g., secondary property, virtual property, extended property, etc.)

You can also leverage [interfaces](../glossary.md#gloss-interface) and [form inheritance](../glossary.md#gloss-form-inheritance) to filter by property across multiple related forms.

When filtering by property, you can specify the property using either the **full** property name (the combined form and property, such as `inet:dns:a:ip`) or the **relative** property name (the property name alone, including its separator character, such as `:ip`). Using the relative property name is a simpler (and more efficient) syntax. Full property names can be used for clarity (i.e., specifying **exactly** what you want to filter on).

Full property names are **required** in some cases:

- When filtering on an interface property.
- When filtering on a parent form property, and you want the filter to also apply to forms that extend the parent.
- When multiple nodes in the inbound working set have the same relative property name (e.g., `inet:dns:a:ip` and `inet:asnip:ip`) and you only wish to filter based on the property of one of the forms.

> [!NOTE]
> When filtering by property using the **relative** property name, Synapse will silently drop any inbound nodes that:
> - do not have the property defined on their form, or
> - that have the property defined, but have no value present.
> 
> For example:
> 
> ```storm
> inet:fqdn=vertex.link inet:ip=8.8.8.8 +:asn
> ```
> 
> The query above will silently drop the `inet:fqdn` (which does not have an `:asn` property defined), and will return only the `inet:ip` if the `:asn` property is set.
> 
> Contrast this behavior with filtering by property **value**, where Synapse will return a `NoSuchProp` error if you specify a relative property that is not defined on any inbound forms.

Examples below are shown using both the full property name (*\<form\>:\<prop\>*) and the relative property name (*:\<prop\>*) where applicable.

<a id="filter-prop-second"></a>

### Filter by Secondary Property

These examples assume a secondary property delimited with a colon ( **:** ). Examples for meta properties, virtual properties, and extended properties are described below.

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** *\<prop\>*

**Examples:**

Filter the current working set to only include threats (`risk:threat` nodes) that have an assessed country of origin (`:place:country:code` property):

```text
<query> +risk:threat:place:country:code
```

```text
<query> +:place:country:code
```

Filter the current working set to exclude articles (`doc:report` nodes) that have a publisher name (`:publisher:name` property):

```text
<query> -doc:report:publisher:name
```

```text
<query> -:publisher:name
```

<a id="filter-prop-virt"></a>

### Filter by Virtual Property

[Virtual properties](data_model.md#virtual-property) are declared as part of a [type](data_model.md#type) and may be present on both primary (forms) and secondary properties.

**Syntax**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **.** *\<prop\>* 

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** *\<prop\>* **.** *\<prop\>* 

**Examples**

Filter the current working set to only include file paths with a file extension (`.ext`):

```text
<query> +file:path.ext
```

```text
<query> +.ext
```

Filter the current working set to exclude network flows (`inet:flow`) where the client has an associated port (`.port`):

```text
<query> -inet:flow:client.port
```

```text
<query> -:client.port
```

<a id="filter-prop-meta"></a>

### Filter by Meta Property

[Meta properties](data_model.md#meta-property) apply to all forms and are automatically populated. Synapse uses two meta properties:

- `.created`: a time which represents the date and time a node was created in Synapse.
- `.updated`: a time which represents the date and time a node was last modified in Synapse.

**Syntax**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **.** *\<prop\>*

> [!NOTE]
> Storm supports filtering by meta property. However, because meta properties are always present on every node, filtering on a meta property will always include (or exclude) every node in the current working set when filtering by property alone (e.g., `+.created`, `-.updated`), or every node of the specified form when a form name is included (e.g., `+inet:fqdn.created`, `-inet:ip.updated`).

<a id="filter-prop-extend"></a>

### Filter by Extended Property

Synapse's data model can be extended with custom forms, properties, or edges. To avoid potential namespace collisions with properties in the base data model, extended property names must begin with an underscore. See the section on [extending the data model](data_model.md#extending-the-data-model) for details.

**Syntax**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:\_** *\<prop\>*

**Examples**

Filter the current working set to only include nodes that have a VirusTotal reputation extended property (`:_virustotal:reputation`):

```text
<query> +:_virustotal:reputation
```

> [!TIP]
> The `:_virustotal:reputation` extended property is added to the Synapse data model by the [Synapse-VirusTotal](/docs/synapse-virustotal/latest/index.md) Power-Up. The property is added to multiple forms, including `file:bytes`, `inet:fqdn`, `inet:ip`, and `inet:url`. The filter above (which uses the relative property name `:_virustotal:reputation`) will return nodes of **any** form that have the extended property.
>  
> To only return nodes of a **specific** form (such as files), use the full form + property name:
>  
> `<query> +file:bytes:_virustotal:reputation`

<a id="filter-prop-interface"></a>

### Filter by Interface Property

If a form implements an [interface](../glossary.md#gloss-interface) that defines a set or properties, you can filter all nodes of all forms that have that property by specifying the full name of the interface and its property.

> [!TIP]
> When filtering using an interface property, you must use full property syntax (i.e., the combined interface and property name).

**Syntax:**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>*

**Example:**

Filter the current working set to only include those host event nodes (all nodes of all forms that implement the `it:host:event` interface) that have a `:time` property:

```text
<query> +it:host:event:time
```

<a id="filter-prop-parent"></a>

### Filter By Parent Form Property

Where forms make use of [inheritance](../glossary.md#gloss-form-inheritance), filtering by a parent form property will filter all nodes of the parent form and all nodes of all forms that extend the parent that have that property.

> [!TIP]
> You must use full property syntax (the parent form + property name) in order for the filter to apply to the parent form and all extended forms. If you use relative property syntax, Synapse will filter the inbound nodes based on the presence or absence of the property on any inbound nodes, independent of any form inheritance.

**Syntax**

*\<query\>* **+** \| **-** *\<parent_form\>* **:** | **.** | **:_** *\<prop\>*

**Examples**

Filter the current working set to only include `it:host:account` nodes and all nodes of all forms that extend `it:host:account` that have a `:home` property:

```text
<query> +it:host:account:home
```

> [!TIP]
> The `it:host:account` form is extended by `it:host:posix:account` and `it:host:windows:account`, so the filter will return any of those forms present in the original `<query>` that have the `:home` property set.

<a id="filter-prop-standard"></a>

## Filter by Property Value - Standard Comparison Operators

A **filter by property value** operation modifies the current working set to include (or exclude) the node(s) whose property matches the specified value. This type of filter requires:

- the filter operator ( `+` or `-` );
- the property name (full or relative) to use for the filter;
- a [comparison operator](../glossary.md#gloss-comp-operator) to specify how the property value should be evaluated; and
- the property value.

A filter by property value can be performed using any kind of property (primary, secondary, virtual, meta, extended, etc.). You can also leverage [interfaces](../glossary.md#gloss-interface) and [form inheritance](../glossary.md#gloss-form-inheritance) to filter by property value across multiple related forms.

In Synapse, we define **standard comparison operators** as the following set of operators:

- equal to ( `=` )
- less than ( `<` )
- greater than ( `>` )
- less than or equal to ( `<=` )
- greater than or equal to ( `>=` )

For filter operations, the not equal ( `!=` ) operator is also supported.

The most commonly used standard comparison operator is the equal to ( `=` ) operator. Comparison operators that expect a **quantity** (i.e., the inequality symbols `<`, `>`, `<=`, and `>=`) can only be used with properties whose type supports the comparison (e.g., integers, dates/times, IP addresses, etc.)

When filtering by property value, you can specify the property using either the **full** property name (the combined form and property, such as `inet:dns:a:ip`) or the **relative** property name (the property name alone, including its separator character, such as `:ip`). Using the relative property name is a simpler (and more efficient) syntax. Full property names can be used for clarity (i.e., specifying **exactly** what you want to filter on).

Full property names are **required** in some cases:

- When filtering on an interface property value.
- When filtering on a parent form property value, and you want the filter to also apply to forms that extend the parent.
- When multiple nodes in the inbound working set have the same relative property name (e.g., `inet:dns:a:ip` and `inet:asnip:ip`) and you only wish to filter based on the property value of one of the forms.
- When only some forms in the inbound working set have the specified property.

> [!NOTE]
> When filtering by property value using the **relative** property name, Synapse will generate a `NoSuchProp` error if any inbound nodes do not have the property defined for that form. For example:
> 
> ```storm
> inet:fqdn=vertex.link inet:ip=8.8.8.8 +:asn=15169
> ```
> 
> The query above will generate a `NoSuchProp: No property named :asn.` error because an `inet:fqdn` does not have an `:asn` property.
> 
> Contrast this behavior with filtering by the presence of a property (e.g., `+:asn`), where Synapse will silently drop any inbound nodes that do not have that property.

Examples below are shown using both the full property name (*\<form\>:\<prop\>*) and the relative property name (*:\<prop\>*) where applicable.

> [!TIP]
> When filtering nodes by a property value where the value is a `time` (date / time), you can use time values of any acceptable resolution (e.g., from `2026` to `2026/07/27 18:23:46.935216`). Lower-resolution times are **zero-filled** by default, so `2026` is interpreted as `2026/01/01 00:00:00.000000`.
> You can also use a wildcard ( `*` ) to specify any time that matches the wildcard expression. For example, `2026/05*` (or `202605*`) is interpreted as "any date/time during May 2026".
> See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) types for a detailed discussion of these behaviors.

<a id="filter-prop-std-primary"></a>

### Filter by Primary Property Value

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* *\<operator\>* *\<valu\>*

Filter the current working set to exclude the loopback IP address (`127.0.0.1`):

```text
<query> -inet:ip=127.0.0.1
```

```text
<query> +inet:ip!=127.0.0.1
```

<a id="filter-prop-std-secondary"></a>

### Filter by Secondary Property Value

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** *\<prop\>* *\<operator\>* *\<pval\>*

Filter the current working set to include only those FQDNs that are also logical zones:

```text
<query> +inet:fqdn:iszone=1
```

```text
<query> +:iszone=1
```

Filter the current working set to exclude any PE (portable executable) metadata files (`file:mime:pe` nodes) with a compiled time of `1992-06-19 22:22:17`:

```text
<query> -file:mime:pe:compiled='1992/06/19 22:22:17'
```

```text
<query> -:compiled='1992/06/19 22:22:17'
```

Filter the current working set to only include reports that were published during June 2026:

```text
<query> +doc:report:published=202606*
```

```text
<query> +:published=202606*
```

Filter the current working set to exclude those files (`file:bytes` nodes) whose size is greater than or equal to 1MB:

```text
<query> -file:bytes:size>=1000000
```

```text
<query> -:size>=1000000
```

<a id="filter-prop-std-virt"></a>

### Filter by Virtual Property Value

**Syntax**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **.** *\<prop\>* *\<operator\>* *\<pval\>*

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** *\<prop\>* **.** *\<prop\>* *\<operator\>* *\<pval\>*

> [!TIP]
> See [Filter Using Tag Timestamps](storm_ref_filter.md#filter-tag-timestamp) for special syntax when accessing virtual properties (e.g., `.min`, `.max`, `.duration`) associated with tag timestamps.

**Examples**

Filter the current working set to only include servers listening on port 22:

```text
<query> +inet:server.port=22
```

```text
<query> +.port=22
```

Filter the current working set to only include email messages (`inet:email:message` nodes) with three or more attachments:

```text
<query> +inet:email:message:attachments.size>=3
```

```text
<query> +:attachments.size>=3
```

<a id="filter-prop-std-meta"></a>

### Filter by Meta Property Value

Synapse has two built-in meta properties:

- `.created` a time which represents the date and time a node was created in Synapse.
- `.updated` a time which represents the date and time a node was last modified in Synapse.

Times (date / time values) are stored as integers (epoch microseconds) in Synapse and can be filtered using any standard comparison operator.

The [Filter by Time or Interval (@=)](storm_ref_filter.md#filter-interval) and [Filter by Range (*range=)](storm_ref_filter.md#filter-range) extended comparison operators provide additional flexibility when filtering by times and intervals.

See the [time](storm_ref_type_specific.md#type-time) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for additional details on working with times in Synapse.

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **.** *\<prop\>* *\<operator\>* *\<pval\>*

Filter the current working set to include only those nodes created on January 1, 2026 or later:

```text
<query> +.created>=2026/01/01
```

Filter the current working set to include only those FQDNs created on January 1, 2026 or later:

```text
<query> +inet:fqdn.created>=2026/01/01
```

<a id="filter-prop-std-extended"></a>

### Filter by Extended Property Value

When filtering by extended property value, you can use any standard comparison operator supported by the property's type. For example, if the extended property is a string, only the equal to ( `=` ) standard operator is supported. If the extended property is an integer, any of the standard operators can be used.

**Syntax**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:\_** *\<prop\>* *\<operator\>* *\<pval\>*

**Example**

Filter the current working set to only include files (`file:bytes` nodes) with a VirusTotal reputation score (`:_virustotal:reputation` extended property) less than -50:

```text
<query> +file:bytes:_virustotal:reputation<-50
```

```text
<query> +:_virustotal:reputation<-50
```

> [!TIP]
> The `:_virustotal:reputation` extended property is added to the Synapse data model by the [Synapse-VirusTotal](/docs/synapse-virustotal/latest/index.md) Power-Up. The property is added to multiple forms, including `file:bytes`, `inet:fqdn`, `inet:ip`, and `inet:url`. The filtering by the relative property name (`:_virustotal:reputation`) will return nodes of **any** form in the inbound working set that have the extended property with the specified value.

<a id="filter-prop-std-interface"></a>

### Filter by Interface Property Value

If a form implements an [interface](../glossary.md#gloss-interface) that defines a set of properties, you can filter all nodes of all forms with a specific value for that property by using the name of the interface.

> [!TIP]
> When filtering using an interface property value, you must use full property syntax (i.e., the combined interface and property name).

**Syntax:**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples:**

Filter the current working set to only include those Microsoft Office metadata nodes (all nodes of all forms that implement the `file:mime:msoffice` interface) whose `:author:name` value is `admin`:

```text
<query> +file:mime:msoffice:author:name=admin
```

Filter the current working set to exclude any host event nodes (all nodes of all forms that implement the `it:host:event` interface) observed earlier than January 1, 2024:

```text
<query> -it:host:event:time<2024/01/01
```

<a id="filter-prop-std-parent"></a>

### Filter by Parent Form Property Value

Where forms make use of [inheritance](../glossary.md#gloss-form-inheritance), filtering by a parent form property value will filter all nodes of the parent form and all nodes of all forms that extend the parent that have that property value.

> [!TIP]
> You must use full property syntax (the parent form + property name) in order for the filter to apply to the parent form and all extended forms. If you use relative property syntax, Synapse will filter the inbound nodes based on the presence or absence of the property and its value on any inbound nodes, independent of any form inheritance.

**Syntax**

*\<query\>* **+** \| **-** *\<parent_form\>* **:** | **.** | **:_** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples**

Filter the current working set to exclude techniques or mitigations reported by MITRE (the `meta:technique` form is extended by the `risk:mitigation` form):

```text
<query> -meta:technique:reporter:name=mitre
```

Filter the current working set to only include stored file entry nodes with the specified file path:

```text
<query> +file:stored:entry:path=c:\windows\system32\fonts\cmd.exe
```

The stored file entry (`file:stored:entry`) parent form represents a file (`file:bytes`) stored in a specific location, with optional associated timestamps (e.g., `:created`, `:accessed`, etc.). It is extended by forms including `file:system:entry` (a file on a host file system) and archive files such as `file:archive:entry` or `file:mime:rar:entry`.

<a id="filter-prop-extended"></a>

## Filter by Property Value - Extended Comparison Operators

Storm supports a set of extended comparison operators (comparators) for specialized filter operations. In most cases, the same extended comparators are available for both lifting and filtering:

- [Filter by Regular Expression (~=)](storm_ref_filter.md#filter-regex)
- [Filter by Prefix (^=)](storm_ref_filter.md#filter-prefix)
- [Filter by Time or Interval (@=)](storm_ref_filter.md#filter-interval)
- [Filter by Range (\*range=)](storm_ref_filter.md#filter-range)
- [Filter by Set Membership (\*in=)](storm_ref_filter.md#filter-set)
- [Filter by Proximity (\*near=)](storm_ref_filter.md#filter-proximity)
- [Filter by (Arrays) (\*\[ \])](storm_ref_filter.md#filter-by-arrays)

Just as with standard comparison operators, filtering with extended comparison operators requires:

- the filter operator ( `+` or `-` );
- the property name (full or relative) to use for the filter;
- the appropriate [comparison operator](../glossary.md#gloss-comp-operator) to specify how the property value should be evaluated; and
- the property value.

Each extended comparison operator can be used with any kind of property (primary, secondary, virtual, extended, etc.) whose [type](../glossary.md#gloss-type) is appropriate for the comparison used. You can also leverage [interfaces](../glossary.md#gloss-interface) and [form inheritance](../glossary.md#gloss-form-inheritance) to filter by property value across multiple related forms.

As with other kinds of filters, you can use either full property syntax (the full form name and property name) or relative property syntax (the property name alone, including its separator character) in most cases.

Full property names are **required** in some cases:

- When filtering on an interface property value.
- When filtering on a parent form property value, and you want the filter to also apply to forms that extend the parent.
- When multiple nodes in the inbound working set have the same relative property name (e.g., `inet:dns:a:ip` and `inet:asnip:ip`) and you only wish to filter based on the property value of one of the forms.
- When only some forms in the inbound working set have the specified property defined. When filtering by property value using the **relative** property name, Synapse will generate a `NoSuchProp` error if any inbound nodes do not have the property as part of their form.

<a id="filter-regex"></a>

### Filter by Regular Expression (~=)

The extended comparator `~=` is used to filter nodes based on regular expression.

> [!TIP]
> In Synapse, `~=` matches are **case-insensitive** by default. To force a case-sensitive match, start the pattern with the inline flag `(?-i)`.
>   
> [Filter by Prefix (^=)](storm_ref_filter.md#filter-prefix) can be used to filter based on the beginning of string-based properties, and is more efficient for beginning-of-string filter operations. It should be used instead of a regular expression filter where possible.

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* **~=** *\<regex\>*

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **~=** *\<regex\>*

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **~=** *\<regex\>*

**Examples:**

Filter the current working set to only include reports (`doc:report` nodes) whose title includes the string `sandstorm`:

```text
<query> +doc:report:title~=sandstorm
```

```text
<query> +:title~=sandstorm
```

Filter the current working set to exclude organizations (`ou:org` nodes) whose name contains a string that starts with `v`, followed by 0 or more characters, followed by `x`:

```text
<query> -ou:org:name~='^v.*x'
```

```text
<query> -:name~='^v.*x'
```

Filter the current working set to only include taxonomy nodes (all nodes of all forms that implement the `meta:taxonomy` interface) whose description (`:desc` property) includes the string `credential`:

```text
<query> +meta:taxonomy:desc~=credential
```

`Meta:taxonomy` is an interface, so you must use full property syntax in the example above.

<a id="filter-prefix"></a>

### Filter by Prefix (^=)

Synapse performs prefix indexing on strings and string-derived types, which optimizes filtering nodes whose *\<valu\>* or *\<pval\>* starts with a given prefix (substring). The extended comparator `^=` is used to filter nodes by prefix.

> [!NOTE]
> Extended string types that support dotted notation (such as the [loc](storm_ref_type_specific.md#type-loc) or [syn:tag](storm_ref_type_specific.md#type-syn-tag) types) have custom behaviors with respect to lifting and filtering by prefix.
>
> [inet:fqdn](storm_ref_type_specific.md#type-inet-fqdn) nodes are indexed in reverse string order so cannot be **lifted** using the prefix extended operator. However, they can be **filtered** by prefix.
>
> See the relevant sections in the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for details.

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* **^=** *\<prefix\>*

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **^=** *\<prefix\>*

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **^=** *\<prefix\>*

**Examples:**

Filter the current working set to exclude email addresses (`inet:email` nodes) that start with `abuse`:

```text
<query> -inet:email^=abuse
```

Filter the current working set to only include organizations (`ou:org` nodes) whose name starts with `ministry`:

```text
<query> +ou:org:name^=ministry
```

```text
<query> +:name^=ministry
```

Filter the current working set to only include Microsoft Office metadata nodes (all nodes of all forms that implement the `file:mime:msoffice` interface) whose `:author:name` value starts with `Admin`:

```text
<query> +file:mime:msoffice:author:name^=Admin
```

<a id="filter-interval"></a>

### Filter by Time or Interval (@=)

The time extended comparator (`@=`) is used to filter nodes based on comparisons among various combinations of times and intervals.

See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for additional detail on the use and behavior of [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) data types.

> [!TIP]
> You can use the virtual properties associated with time and interval types to [Filter by Virtual Property](storm_ref_filter.md#filter-prop-virt) or [Filter by Virtual Property Value](storm_ref_filter.md#filter-prop-std-virt).

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **@=(** *\<ival_min\>* **,** *\<ival_max\>* **)**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **@=** *\<time\>*

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **@=(** *\<ival_min\>* **,** *\<ival_max\>* **)**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **@=** *\<time\>*

**Examples:**

Filter the current working set to include only those DNS A records (`inet:dns:a` nodes) whose `:seen` values fall between July 1, 2022 and and August 1, 2022:

```text
<query> +inet:dns:a:seen@=(2022/07/01, 2022/08/01)
```

```text
<query> +:seen@=(2022/07/01, 2022/08/01)
```

Filter the current working set to only include DNS requests (`inet:dns:request` nodes) that occurred on May 3, 2023 (between `05/03/2023 00:00:00` and `05/03/2023 23:59:59`):

```text
<query> +inet:dns:request:time@=('2023/05/03 00:00:00', '2023/05/04 00:00:00')
```

```text
<query> +:time@=('2023/05/03 00:00:00', '2023/05/04 00:00:00')
```

> [!TIP]
> Because the `inet:dns:request:time` property is a single date / time value, the following filters will also work:
>
> - `+inet:dns:request:time=2023/05/03*`
> - `+:time=2023/05/03*`

Filter the current working set to only include DNS A records (`inet:dns:a` nodes) whose `:seen` time window includes the date September 1, 2023:

```text
<query> +inet:dns:a:seen@=2023/09/01
```

```text
<query> +:seen@=2023/09/01
```

Filter the current working set to include only those domain WHOIS records (`inet:whois:record` nodes) where the domain was registered (created) exactly on March 19, 2019 at 5:00 UTC:

```text
<query> +inet:whois:record:created@='2019/03/19 05:00:00'
```

```text
<query> +:created@='2019/03/19 05:00:00'
```

> [!NOTE]
> When comparing a single time value to a time property, the `@=` comparator behaves just like the equal to ( `=` ) operator.

Filter the current working set to only include the reports (`doc:report` nodes) that were published within the past day:

```text
<query> +doc:report:published@=(now, '-1 day')
```

```text
<query> +:published@=(now, '-1 day')
```

Filter the current working set to only include the host event nodes (all nodes of all forms that implement the `it:host:event` interface) whose `:time` value is within the past three hours:

```text
<query> +it:host:event:time@=(now, '-3 hours')
```

**Usage Notes:**

- When specifying an interval with the `@=` operator, the minimum value is **included** in the interval for comparison purposes but the maximum value is **not**. This is equivalent to "greater than or equal to *\<min\>* and less than *\<max\>*". This behavior differs from that of the `*range=` operator, which includes **both** the minimum and maximum.

- **Comparing intervals to intervals:** when using an interval with the `@=` operator to filter nodes based on an interval property, Synapse returns nodes whose interval value has **any** overlap with the specified interval. For example:

  - A filter interval of September 1, 2018 to October 1, 2018 (2018/09/01, 2018/10/01) will match nodes with any of the following intervals:
    - August 12, 2018 to September 6, 2018 (2018/08/12, 2018/09/06 - `.max` value is within the interval).
    - September 13, 2018 to September 17, 2018 (2018/09/13, 2018/09/17 - both `.min` and `.max` values are within the interval).
    - September 30, 2018 to November 5, 2018 (2018/09/30, 2018/11/05 - `.min` value is within the interval).
    - August 12, 2018 to November 5, 2018 (2018/08/12, 2018/11/05 - the interval is within the `.min` and `.max` values).

- **Comparing intervals to times:** When using an interval with the `@=` operator to filter nodes based on a time property, Synapse returns nodes whose time value falls within the specified interval.

- **Comparing times to times:** When using a time with the `@=` operator to filter nodes based on a time property, Synapse returns nodes whose timestamp is an **exact match** of the specified time. In other words, in this case the interval comparator ( `@=` ) behaves like the equal to comparator ( `=` ).

- When specifying date / time and interval values, Synapse allows the use of both lower resolution values (e.g., `YYYY/MM/DD`), and wildcard values (e.g., `YYYY/MM*`). Wildcard time syntax may provide a simpler and more intuitive means to specify some intervals. For example `inet:whois:record:created=2018*` is equivalent to `inet:whois:record:created@=('2018/01/01', '2019/01/01')`.

- Time-based keywords (such as `now`) and relative time syntax (expressions such as `+-1 hour` or `-7 days`) can be used for interval values.

  See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) types for a detailed discussion of these behaviors.

<a id="filter-range"></a>

### Filter by Range (\*range=)

The range extended comparator (`*range=`) supports filtering nodes whose *\<form\> = \<valu\>* or *\<prop\> = \<pval\>* fall within a specified range of values. The comparator can be used with types such as integers and times.

> [!NOTE]
> The `*range=` operator can be used to filter `inet:ip` values. However, ranges of [inet:ip](storm_ref_type_specific.md#type-inet-ip) nodes can also be filtered directly by specifying the lower and upper addresses in the range using `<min>-<max>` format. For example:
>
> - `+inet:ip=192.168.0.0-192.168.0.10`
> - `+:ip=192.168.0.0-192.168.0.10`
>  
> - `+inet:ip=2a10::0-2a11::ff`
> - `+:ip=2a10::0-2a11::ff`
>
> The `*range=` operator cannot be used to compare a time range with a property value that is an interval (`ival` type). The interval ( `@=` ) operator should be used instead.

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

**Examples:**

Filter the current working set to exclude files (`file:bytes` nodes) whose size is between 1000 and 100000 bytes:

```text
<query> -file:bytes:size*range=(1000, 100000)
```

```text
<query> -:size*range=(1000, 100000)
```

Filter the current working set to only include files (`file:bytes` nodes) whose VirusTotal reputation score (`:_virustotal:reputation`) is between -20 and 20:

```text
<query> +file:bytes:_virustotal:reputation*range=(-20, 20)
```

```text
<query> +:_virustotal:reputation*range=(-20, 20)
```

Filter the current working set to exclude DNS requests (`inet:dns:request` nodes) that were made between November 29, 2025 and January 14, 2026:

```text
<query> -inet:dns:request:time*range=(2025/11/29, 2026/01/14)
```

```text
<query> -:time*range=(2025/11/29, 2026/01/14)
```

Filter the current working set to only include DNS requests (`inet:dns:request` nodes) made within one day of December 1, 2025:

```text
<query> +inet:dns:request:time*range=(2025/12/01, '+-1 day')
```

```text
<query> +:time*range=(2025/12/01, '+-1 day')
```

Filter the current working set to only include taxonomy nodes (all nodes of all forms that implement the `meta:taxonomy` interface) whose `:depth` is between 1 and 3 (i.e., between 2 and 4 taxonomy elements):

```text
<query> +meta:taxonomy:depth*range=(1, 3)
```

**Usage Notes:**

- When specifying a range (`*range=`), both the minimum and maximum values are **included** in the range (the equivalent of "greater than or equal to *\<min\>* and less than or equal to *\<max\>*"). This behavior is slightly different than that for time interval (`@=`), which includes the minimum but not the maximum.
- When specifying a range of time values, Synapse allows you to use either lower resolution values (e.g., `YYYY/MM/DD`) or wildcard values (e.g., `YYYY/MM*`) for the minimum and/or maximum range values. In some cases, plain wildcard time syntax may provide a simpler and more intuitive means to specify some time ranges. For example `+inet:whois:record:created=2018*` is equivalent to `+inet:whois:record:created*range=('2018/01/01', '2018/12/31 23:59:59.999999')`. See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) types for a detailed discussion of these behaviors.
- When using keywords (such as `now`) or relative values (such as `-1 hour`) to specify a range of times, the first value in the range is calculated relative to the current time and the second value is calculated relative to the first value.
- If you specify a range value that is nonsensical or exclusionary (such as `(47, 16)`), Synapse will **not** generate an error and will simply fail to return results. (The expression is syntactically correct, but no value is both greater than 47 and less than 16).

<a id="filter-set"></a>

### Filter by Set Membership (\*in=)

The set membership extended comparator (`*in=`) supports filtering nodes whose *\<form\> = \<valu\>* or *\<prop\> = \<pval\>* matches any of a set of specified values. The comparator can be used with any type.

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

**Examples:**

Filter the current working set to exclude entity names matching any of the specified values:

```text
<query> -entity:name*in=(fsb, 'vladimir putin')
```

Filter the current working set to only include IP addresses associated with any of the specified Autonomous System (AS) numbers:

```text
<query> +inet:ip:asn*in=(9009, 20473, 44477)
```

```text
<query> +:asn*in=(9009, 20473, 44477)
```

Filter the current working set to only include tags (`syn:tag` nodes) whose final tag element matches any of the specified string values:

```text
<query> +syn:tag:base*in=(plugx, korplug, sogu, kaba)
```

```text
<query> +:base*in=(plugx, korplug, sogu, kaba)
```

<a id="filter-proximity"></a>

### Filter by Proximity (\*near=)

The proximity extended comparator (`*near=`) supports filtering nodes by "nearness" to another node. Currently, `*near=` supports proximity based on geospatial location (i.e., nodes within a given radius of a specified latitude / longitude).

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **\*near = ((** *\<lat\>* **,** *\<long\>* **),** *\<radius\>* **)**

**Examples:**

Filter the current working set to only include locations (`geo:place` nodes) within 500 meters of the Russian Cryptographic Museum (where the coordinates `55.83069, 37.59781` represent the Museum's location):

```text
<query> +geo:place:latlong*near=((55.83069, 37.59781), 500m)
```

```text
<query> +:latlong*near=((55.83069, 37.59781), 500m)
```

**Usage Notes:**

- In the example above, the latitude and longitude of the desired location are explicitly specified as parameters to `*near=`.
- Radius can be specified in the following units. The values in parentheses are the acceptable terms for specifying a given unit:
  - Kilometers (`km` / `kilometer` / `kilometers`)
  - Meters (`m` / `meter` / `meters`)
  - Centimeters (`cm` / `centimeter` / `centimeters`)
  - Millimeters (`mm` / `millimeter` / `millimeters`)
  - Miles (`mile` / `miles`)
  - Yards (`yard` / `yards`)
  - Feet (`foot` / `feet`)
- Radius values of less than 1 must be specified with a leading zero (e.g., 0.5 km).
- The `*near=` comparator works for geospatial data by filtering the nodes to ensure that they are within the great-circle distance given by the *\<radius\>* argument.

<a id="filter-by-arrays"></a>

### Filter by (Arrays) (\*\[ \])

Storm uses a special syntax to filter (or lift) by comparison with one or more elements of an [array](storm_ref_type_specific.md#type-array) type. The syntax consists of an asterisk ( `*` ) preceding a set of square brackets ( `[ ]` ), where the square brackets contain a comparison operator and a value that can match one or more elements in the array. This allows users to match any value in the array list without needing to know the exact order or values of the array itself.

When filtering based on a value in an array property, you must use the **relative** name of the property. The full property name (i.e., the combined form and property) is not supported for this type of filter.

> [!TIP]
> You can use the `.size` virtual property associated with array types to [Filter by Virtual Property Value](storm_ref_filter.md#filter-prop-std-virt).

**Syntax:**

*\<query\>* **+** \| **-** **:** \| **.** \| **:\_** *\<prop\>* **\*\[** *\<operator\>* *\<pval\>* **\]**

**Examples:**

Filter the current working set to only include x509 certificates (`crypto:x509:cert` nodes) that reference FQDNs ending with `.xyz`:

```text
<query> +:identities:fqdns*[='*.xyz']
```

Filter the current working set to only include threat clusters (`risk:threat` nodes) whose secondary (alternate) names include the string `dragon`:

```text
<query> +:names*[~=dragon]
```

**Usage Notes:**

- The comparison operator used must be valid for filter operations for the type used in the array.
- The standard equals ( `=` ) operator can be used to filter nodes based on array properties, but the value(s) specified must **exactly match** all of the values in the array:
  - For example: `ou:org +:names=("the vertex project", "the vertex project llc", vertex)` will filter to any `ou:org` nodes whose `:names` property consists of all those names exactly as specified. (For sorted / de-duplicated arrays - such as `ou:org:names` - the **order** does not matter because Synapse normalizes the values first.) 
- See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) document for additional details on working with arrays.

<a id="tag-filter"></a>

## Tag Filters

Tags in Synapse can represent observations or assessments. They are used to provide context to nodes (in the form of "labels" applied to nodes) and to group related nodes.

Storm supports filtering nodes based on the tags applied to nodes (including the use of tag globs), as well as filtering based on tag timestamps, tag properties, or tag property values.

The "hashtag" symbol ( `#` ) is used to specify a tag name when filtering by tag.

> [!NOTE]
> Synapse does not include any pre-defined tags (although some Power-Ups may create tags defined within the Power-Up itself). The examples below are based on tags and tag conventions used by The Vertex Project.

<a id="filter-tag"></a>

### Filter by Tag (#)

A **filter by tag** operation downselects the current working set to include (or exclude) all nodes with the specified tag.

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>*

Filter the current working set to exclude all nodes that ESET associates with Sednit (`#rep.eset.sednit`):

```text
<query> -#rep.eset.sednit
```

Filter the current working set to only include nodes associated with anonymized infrastructure (`#cno.infra.anon`):

```text
<query> +#cno.infra.anon
```

> [!TIP]
> Tags are hierarchical, and each tag element is its own tag; the tag `#cno.infra.anon` consists of the tags `#cno`, `#cno.infra`, and `#cno.infra.anon`. Filtering nodes using a tag "higher up" in the tag hierarchy will include (or exclude) nodes with the specified tag or any tag "lower down" in the hierarchy. In other words, filtering by `#cno.infra.anon` will filter all "anonymized" infrastructure, whether the infrastructure is a VPN (`#cno.infra.anon.vpn`), a TOR node (`#cno.infra.anon.tor`), or an anonymous proxy (`#cno.infra.anon.proxy`).

<a id="filter-tag-globs"></a>

### Filter by Tag Globs

Synapse supports filtering based on the set of tags that match a specified glob expression using single ( `*` ) or double ( `**` ) asterisks, or a combination of the two.

The single asterisk and double asterisk behave differently:

- The asterisk ( `*` ) represents an arbitrary string of zero or more characters that matches **within** a single tag element (i.e., one element as bounded by the tag's dot ( `.` ) separators).
- The double asterisk ( `**` ) represents an arbitrary string match of zero or more characters anywhere in the tag, including **across** tag elements.

Another way to look at this is that the single asterisk is constrained by the tag's dot boundaries, but the double asterisk is not.

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<string\>* \| **\*** \| **\*\*** \[ *\<string\>* \| **.** \| **\*** \| **\*\*** ... \]

**Examples:**

Filter the current working set to exclude any nodes tagged as `seduploader` by any third-party reporting organization:

```text
<query> -#rep.*.seduploader
```

To record assessments made by third parties, The Vertex Project uses `rep` ("reported by") as the root tag element, followed by a tag element for the reporting organization (e.g., `rep.eset`), followed by the name of the "thing" reported (in this case, the `seduploader` malware family).

The tag glob filter above uses the single asterisk to match any tag element in the second position, and will match tags such as:

- `rep.eset.seduploader`
- `rep.paloalto.seduploader`

...etc.

Filter the current working set to include any nodes tagged as `cobaltstrike` by any third-party reporting organization whose name begins with `m`:

```text
<query> +#rep.m*.cobaltstrike
```

The tag glob filter above uses the single asterisk to match any partial tag element in the second position that starts with `m` and is followed by any string of zero or more characters. The single asterisk matches **within** tag element boundaries, and will match tags such as:

- `rep.m.cobaltstrike`
- `rep.malwarebazaar.cobaltstrike`
- `rep.microsoft.cobaltstrike`

> [!TIP]
> The filter above would **not** match on a tag such as `rep.malwarebazaar.3p.anyrun.cobaltstrike`, because the string `cobaltstrike` is not the third tag element. A double asterisk, which matches **across** a tag's "dot" boundaries, would match this tag as well as the example tags above:
>
> `rep.m**cobaltstrike`

Filter the current working set to include any nodes tagged as `seduploader` either internally or by any third-party reporting organization:

```text
<query> +#*.*.seduploader
```

The Vertex Project uses the `cno` root tag to represent our own internal assessments (and distinguish them from third party-assessments), and the `mal` element to represent assessments related to malware. The tag glob filter above uses two single asterisks to match any element in both the first and second positions, and will match all of the following:

- `rep.eset.seduploader`
- `rep.paloalto.seduploader`
- `cno.mal.seduploader`

...etc.

Filter the current working set to include any nodes reported by Microsoft whose tags end in `blizzard`:

```text
<query> +#rep.microsoft.**blizzard
```

The tag glob filter above uses a double asterisk to match any Microsoft tag (tag that begins `rep.microsoft`) that ends in `blizzard`, regardless of tag depth (i.e., the double asterisk matches **across** tag elements). The filter will match all of the following:

- `rep.microsoft.aqua_blizzard`
- `rep.microsoft.cadet_blizzard`
- `rep.microsoft.very.long.tag.that.ends.with.blizzard`

...etc.

Filter the current working set to exclude any nodes tagged with any tag that starts with `cno` and is followed by any string:

```text
<query> -#cno**
```

The tag glob filter above uses a double asterisk to match any string (whose length is zero or more characters) following `cno`. The double asterisk matches **across** tag elements, so the filter will match all of the following:

- `cno`
- `cno.mal`
- `cno.threat.t42`
- `cnoooo.you_get_a_cno.and_you_get_a_cno`

...etc.

Filter the current working set to include any nodes tagged by any third-party reporting organization where the tag contains the string `2017`:

```text
<query> +#rep.*.**2017**
```

The tag glob filter above uses both a single and double asterisk. The single asterisk matches any tag element in the second position; the double asterisk matches any string that includes `2017`, including across dot (`.`) boundaries. The filter will match all of the following:

- `rep.alienvault.cve20178291`
- `rep.malwarebazaar.3p.reversinglabs.document_ole_exploit_cve_2017_11882`
- `rep.vt.cve_2017_0199`
- `rep.acme.2017`

<a id="filter-tag-timestamp"></a>

### Filter Using Tag Timestamp Values

A tag timestamp can be thought of as a specialized "property" of a tag that happens to be a date / time range (interval). You can filter nodes based on tag timestamp values using any comparison operator supported by [interval](storm_ref_type_specific.md#type-ival) types. The time / interval extended operator ( `@=` ) is used most often, but equal to ( `=` ) can also be used to **exactly** match the values in the interval.

See [Filter by Time or Interval (@=)](storm_ref_filter.md#filter-interval) for additional detail on the use of the `@=` operator.

> [!TIP]
> Tag timestamps have virtual properties (`.min`, `.max`, and `.duration`) similar to other interval types. You can use these virtual properties to [Filter by Virtual Property Value](storm_ref_filter.md#filter-prop-std-virt). To access a tag timestamp's virtual properties, you must enclose the tag in parentheses. For example, given the following tag:
>  
> `#cno.threat.sparkling_unicorn.own=(2024/03/20, 2026/03/20)`
>  
> You can access the timestamp's `.min` value as follows:
>  
> `#(cno.threat.sparkling_unicorn.own).min`

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>* **@=** *\<time\>* \| **(** *\<min_time\>* **,** *\<max_time\>* **)**

*\<query\>* **+** \| **-** **\#(** *\<tag\>* **).** *\<virtprop\>* *\<operator\>* *\<valu\>*

Filter the current result set to only include nodes that were associated with anonymous VPN infrastructure (`#cno.infra.anon.vpn`) between December 1, 2023 and January 1, 2024:

```text
<query> +#cno.infra.anon.vpn@=(2023/12/01, 2024/01/01)
```

Filter the current working set to only include nodes that were owned / controlled by Threat Cluster 15 (`#cno.threat.t15.own`) **as of** October 30, 2024:

```text
<query> +#cno.threat.t15.own@=2024/10/30
```

The query above returns all nodes whose tag timestamp range **includes** the date 2024/10/30.

Filter the current working set to only include nodes that were owned / controlled by Threat Cluster 15 (`#cno.threat.t15.own`) **on or after** October 30, 2024:

```text
<query> +#(cno.threat.t15.own).min>=2024/10/30
```

The query above returns all nodes whose tag timestamp minimum (`.min`) is greater than or equal to 2024/10/30.

<a id="filter-tag-prop"></a>

### Filter Using Tag Properties

[Tag Properties](analytical_model.md#tag-properties) can be used to provide additional context to tags. Storm supports filtering nodes whose tags have a specific tag property (regardless of the value of the property).

> [!TIP]
> Synapse v3 includes two tag properties in its base data model: `:confidence` (of type `meta:score`) and `:tlp` (of type `it:sec:tlp`). Tag properties can be added by [extending the data model](data_model.md#extending-the-data-model).

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>* \| *\<tag_glob\>* **:** *\<tagprop\>*

*\<query\>* **+** \| **-** **\#** **\*** **:** *\<tagprop\>*

*\<query\>* **+** \| **-** **\#** **\*\*** **:** *\<tagprop\>*

When filtering based on the **existence** of a tag property, you can use tag glob syntax (see [Filter by Tag Globs](storm_ref_filter.md#filter-tag-globs)) to specify the associated tags. Filters such as `+#rep.*.*:_risk` or `+#cno.**:_risk` are supported.

When filtering for a specific tag property that appears on **any** tag, use the double asterisk ( `**` ) tag glob to specify any tag (`+#**:tlp`). You can also use a single asterisk (`+#*:tlp`); in this instance the single asterisk is not a tag glob, but a special syntax helper for this particular use case. (Because entering `+#*:tlp` instead of `+#**:tlp` is a common user error, Synapse automatically handles this case to "do what you mean".)

Filter the current working set to include nodes reported by Symantec (`#rep.symantec.*`) that have an associated `:tlp` tag property:

```text
<query> +#rep.symantec.*:tlp
```

Filter the current working set to include nodes with a `:confidence` tag property associated with any tag:

```text
<query> +#**:confidence
```

<a id="filter-tag-prop-value"></a>

### Filter Using Tag Property Values

Storm supports filtering nodes based on the value of a tag property (similar to filtering by the value of a node property).

You can filter nodes based on tag property values using any comparison operator supported by the property's [Type](../glossary.md#gloss-type). For example, if the tag property is defined as an integer (`int`) type, you can use any comparison operator supported by integers.

> [!TIP] 
> When filtering using tag property values, you must use the specific tag whose property values you want to evaluate. Tag glob syntax (see [Filter by Tag Globs](storm_ref_filter.md#filter-tag-globs)) is **not** supported when filtering based on a tag property value. For example, a filter such as `+#rep.**:tlp>green` will generate a syntax error.

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>* **:** *\<tagprop\>* *\<operator\>* *\<pval\>*

Filter the current working set to include nodes that ESET associates with Sednit (`#rep.eset.sednit`) with a `:tlp` tag property value of `amber` or higher:

```text
<query> +#rep.eset.sednit:tlp>=amber
```

Filter the current working set to exclude nodes that DomainTools reports are malicious (`#rep.domaintools.mal`) with a `:confidence` value of `lowest`:

```text
<query> -#rep.domaintools.mal:confidence=lowest
```

<a id="filter-compound"></a>

## Compound Filters

Storm supports the use of the logical operators **and**, **or**, and **not** (including **and not**) to construct compound filters. You can use parentheses to group portions of the filter statement to indicate order of precedence and clarify logical operations when evaluating the filter.

> [!NOTE]
> - Logical operators must be specified in lower case.
> - Synapse evaluates compound filters **in order from left to right**. Depending on the filter, left-to-right order may differ from the standard Boolean order of operations (**not** then **and** then **or**).
> - Parentheses should be used to logically group portions of the filter statement if necessary to clarify order of operations.

**Syntax:**

*\<query\>* **+** \| **-** **(** \[ **not** \] *\<filter\>* **and** \| **or** \[ **not** \] *\<filter\>* ... **)**

**Examples:**

Filter the current working set to only include SHA1 hashes (`crypto:hash:sha1` nodes) or FQDNs (`inet:fqdn` nodes) that ESET associates with Sednit (`#rep.eset.sednit`):

```text
<query> +( (crypto:hash:sha1 or inet:fqdn) and #rep.eset.sednit )
```

Filter the current working set to include only SHA1 hashes or FQDNs that ESET associates with Sednit and that are **not** sinkholed (`#cno.infra.dns.sink.holed`):

```text
<query> +( (crypto:hash:sha1 or inet:fqdn) and (#rep.eset.sednit and not #cno.infra.dns.sink.holed) )
```

Filter the current working set to only include IP addresses (`inet:ip` nodes) that are on AS2119, AS210558, or AS53667 and are located in Luxembourg:

```text
<query> +( (inet:ip:asn=2119 or inet:ip:asn=210558 or inet:ip:asn=53667) and inet:ip:place:loc^=lu )
```

```text
<query> +( (:asn=2119 or :asn=210558 or :asn=53667) and :place:loc^=lu )
```

<a id="filter-subquery"></a>

## Subquery Filters

You can use Storm's [subquery syntax](storm_ref_subquery.md#storm-ref-subquery) to create filters. A subquery (enclosed in curly braces ( `{ }` ) ) can be placed within a larger Storm query.

Most filter operations in Storm will modify (reduce) your current working set of nodes based on some criteria of the **nodes themselves** (e.g., a node's form, property, or tag).

Subquery filters allow you to filter your **current** set of nodes based on some criteria of **nearby** nodes. You use the subquery filter to examine nodes one or more pivots away from your current nodes, and filter your current nodes based on the properties of those "nearby" nodes.

When nodes are passed to a subquery filter, they are evaluated against the filter's criteria:

- Nodes are **excluded** ("consumed", discarded) if they evaluate **false.**
- Nodes are **included** (not "consumed", retained) if they evaluate **true.**

The subquery pivot operation (used to examine nearby nodes) is effectively performed in the background (without navigating away from your current working set), which provides a more powerful and efficient way to filter your data. (The alternative would be to **actually** navigate to the nearby nodes, filter those nodes, and then navigate **back** to the data you are interested in.)

You can optionally use a standard (mathematical) comparison operator with a subquery filter, in order to filter your current set of nodes based on the **number of results** returned by executing the subfilter's Storm query.

Refer to the [Storm Reference - Subqueries](storm_ref_subquery.md#storm-ref-subquery) guide for additional information on subqueries and subquery filters.

**Syntax:**

*\<query\>* **+** \| **-** **{** *\<query\>* **}** \[ *\<standard operator\>* *\<value\>* \]

**Examples:**

Filter the current working set of FQDNs (`inet:fqdn` nodes) to only FQDNs that have resolved to an IP address that Palo Alto Networks associates with Playful Taurus (i.e., an IP address tagged `#rep.paloalto.playful_taurus`):

```text
<inet:fqdn> +{ -> inet:dns:a -> inet:ip +#rep.paloalto.playful_taurus }
```

The subquery filter above takes the inbound `inet:fqdn` nodes and (within the subquery):

- pivots to the associated DNS A records (`inet:dns:a` nodes);
- pivots to the associated IP addresses (`inet:ip` nodes);
- checks the IP for the presence of a `#rep.paloalto.playful_taurus` tag.

The subquery filter returns only those `inet:fqdn` nodes where the operations performed within the subquery **would** (based on the inclusive filter) result in an `inet:ip` node with a `#rep.paloalto.playful_taurus` tag.

Filter the current working set of IP addresses (`inet:ip` nodes) to exclude any IP associated with an Autonomous System (AS) whose name starts with `amazon`:

```text
<inet:ip> -{ :asn -> inet:asn +:registrant:name^=amazon }
```

The subquery filter above takes the inbound `inet:ip` nodes and (within the subquery):

- pivots to the associated `inet:asn` nodes; and
- checks the `inet:asn` nodes for a `:registrant:name` value that starts with "amazon".

The subquery filter returns only those `inet:ip` nodes where the operations performed within the subquery **would not** (based on the exclusive filter) result in an `inet:asn` node with a `:registrant:name` value starting with "amazon".

> [!TIP]
> See [Embedded Property Syntax](storm_ref_filter.md#embed_prop_syntax) for an alternative way to perform this query.

Filter the current working set of files (`file:bytes` nodes) to include only files that are detected as malicious in ten (10) or more scans (i.e., files that are associated with ten or more `it:av:scan:result` nodes whose `:verdict` property value is `malicious`):

```text
<file:bytes> +{ -> it:av:scan:result +:verdict=malicious }>=10
```

The subquery filter above takes the inbound `file:bytes` nodes and (within the subquery):

- pivots to the associated `it:av:scan:result` nodes; and
- filters the results to include only those nodes whose `it:av:scan:result:verdict` property value is `malicious`; and
- counts the number of resulting `it:av:scan:result` nodes for each file.

The subquery filter returns only those `file:bytes` nodes where the operations performed within the subquery **would** (based on the inclusive filter) result in 10 or more associated `it:av:scan:result` nodes with a `malicious` verdict.

> [!TIP]
> This is a simplified example. `it:av:scan:result` nodes represent a scan performed at a given point in time; the filter above does not provide any time constraints so will count any / all "malicious" results, regardless of "when" the scan was performed. Results could include files detected as malicious by ten different vendors during a single scan as well as files detected as malicious by only one vendor during ten different scans.

Filter the current working set of files to include only those that perform DNS queries for two or more FQDNs that have been reported by a third-party (tagged `#rep`):

```text
<query> +{ -> inet:dns:request -> inet:fqdn +#rep }>=2
```

The subquery filter above takes the inbound `file:bytes` nodes and (within the subquery):

- pivots to the associated `inet:dns:request` nodes;
- pivots to the queried `inet:fqdn` nodes; and
- filters the results to include only those FQDNs with a `#rep` tag; and
- counts the number of resulting tagged `inet:fqdn` nodes for each file.

The subquery filter returns only those `file:bytes` nodes where the operations performed within the subquery **would** (based on the inclusive filter) result in two or more queried `inet:fqdn` nodes with a `#rep` tag.

<a id="filter-expression"></a>

## Expression Filters

An expression filter is used to downselect your current working set based on the evaluation of a particular expression. Expression filters are useful when:

- you need to compute a value that you want to use for the filter, or
- when you want to filter based on a value that may change (e.g., when using Storm queries that assign variables; see [Storm Reference - Advanced - Variables](storm_adv_vars.md#storm-adv-vars)).

**Syntax:**

*\<query\>* **+** \| **-** **\$(** *\<expression\>* **)**

**Examples:**

Filter the current working set of network flows (`inet:flow` nodes) to only include flows where the total number of bytes transferred in the flow between the source (`:client:txbytes`) and destination (`:server:txbytes`) is greater than 100MB (~100,000,000 bytes):

```text
<inet:flow> +$( :client:txbytes + :server:txbytes>=100000000 )
```

Filter the current set of nodes associated with any threat group or threat cluster (e.g., tagged `#cno.threat.<threat_name>`), to include only those nodes that are attributed to more than one threat (e.g., that have more than one `#cno.threat.<threat_name>` tag):

```storm
#cno.threat +$( $node.globtags(cno.threat.*).size()>1 )
```

This query may identify nodes that are incorrectly attributed to more than one group, or instances where two or more threat clusters overlap (which may indicate that the clusters actually represent a single set of activity).

This example uses the [$node.globtags()](storm_adv_methods.md#meth-node-globtags) method to select the set of tags on each node that match the specified expression (`cno.threat.*`) and [stormprims-list-size](../stormtypes_prims.md#stormprims-list-size) to count the number of matches.

<a id="embed_prop_syntax"></a>

## Embedded Property Syntax

Storm includes a shortened syntax consisting of two colons (`::`) that can be used to reference a secondary property of an **adjacent** node. Because the syntax can be used to "pull in" a property or property value from a nearby node, it is known as "embedded property syntax".

Embedded property syntax expresses something that is similar (in concept, though not in practice) to a secondary-to-secondary property pivot (see [Storm Reference - Pivoting](storm_ref_pivot.md#storm-ref-pivot)). The syntax expresses navigation:

- From a **secondary property** of a form (such as `inet:ip:asn`), to
- The **form** for that secondary property (i.e., `inet:asn`), to
- A **secondary property** (or property value) of that **target form** (such as `inet:asn:registrant:name`).

Note that while the "net effect" is of a secondary-to-secondary property pivot, the "navigation" that occurs is from secondary property to form (primary property) to secondary property.

> [!TIP]
> This process can be repeated to reference properties of forms more than one pivot away.

Despite its similarity to a pivot operation, embedded property syntax is commonly used for:

- **Filter operations** (specifically, as a more concise alternative to certain [Subquery Filters](storm_ref_filter.md#filter-subquery))
- **Variable assignment** (see [Storm Reference - Advanced - Variables](storm_adv_vars.md#storm-adv-vars))
- Defining an [Embed Column](../glossary.md#gloss-embed-col) in the Synapse UI (Optic)

**Syntax:**

*\<query\>* **+** \| **-** **:** *\<prop\>* **::** *\<prop\>* \[ **::** *\<prop\>* ... \]

*\<query\>* **+** \| **-** **:** *\<prop\>* \[ **::** *\<prop\>* ... \] **::** *\<prop\>* *\<operator\>* *\<pval\>*

*\<query\>* **$** *\<varname\>* **=:** *\<prop\>* **::** *\<prop\>* \[ **::** *\<prop\>* ... \]

> [!NOTE]
> When using embedded property syntax in Storm, the leading colon (before the name of the initial secondary property) is **required** - e.g., `:asn::name`.
>
> When using this syntax in Optic (the Synapse UI) to create an [embed column](/docs/synapse-enterprise-optic/latest/user_interface/userguides/custom_environ.md#display-a-property-from-a-nearby-node-in-a-column-embed-column) in Tabular display mode, the initial colon should be **omitted** - e.g, `asn::name`. Optic effectively prepends the initial colon for you.

**Filter Example:**

The example below illustrates the use of embedded property syntax in a filter expression.

Filter the current working set of IP addresses (`inet:ip` nodes) to exclude any IP associated with an Autonomous System (AS) whose name starts with `amazon`:

```text
<inet:ip> -:asn::registrant:name^=amazon
```

> [!TIP]
> This example is an alternative way to return the same data as the second example under [Subquery Filters](storm_ref_filter.md#filter-subquery) above:
>
> ```text
> <inet:ip> -{ :asn -> inet:asn +:registrant:name^=amazon }
> ```

**Variable Assignment Example:**

Embedded property syntax can also be used when assigning variables (see [Storm Reference - Advanced - Variables](storm_adv_vars.md#storm-adv-vars)).

Set the variable `$name` to the registrant name of the Autonomous System (AS) associated with a given IP address:

```text
<inet:ip> $name=:asn::registrant:name
```

This example uses embedded property syntax to pivot from the inbound `inet:ip` node, to the ASN (`inet:asn` node) associated with the IP's `:asn` property, and assigns the value of the ASN's `:registrant:name` property to the variable `$name`.
