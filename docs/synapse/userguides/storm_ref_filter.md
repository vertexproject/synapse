```mdstorm-setup
```

```mdstorm --hide
$propinfo = ({"doc": "The VirusTotal reputation score."}) $lib.model.ext.addFormProp(file:bytes, _virustotal:reputation, (int, ({})), $propinfo)
```

```mdstorm --hide
$propinfo = ({"doc": "Boolean which records whether the organization is a threat group."}) $lib.model.ext.addFormProp(ou:org, _vertex:threatintel:isthreat, (bool, ({})), $propinfo)
```

```mdstorm --hide
$tagpropinfo = ({"doc": "A risk tagprop."}) $lib.model.ext.addTagProp(_risk, (int, ({})), $tagpropinfo)
```

<a id="storm-ref-filter"></a>


# Storm Reference - Filtering

Filter operations are performed on the output of a previous Storm operation such as a lift or pivot. A filter operation downselects from the working set of nodes by either including or excluding a subset of nodes based on specified criteria.

- `+` specifies an **inclusion** filter. The filter downselects the working set to **only** those nodes that match the specified criteria.
- `-` specifies an **exclusion** filter. The filter downselects the working set to all nodes **except** those that match the specified criteria.

Similar to lift operations ([Storm Reference - Lifting](storm_ref_lift.md#storm-ref-lift)), filter operations can be broken down into "types" of filters based on the criteria, comparison operator, or special handler used:

- [Filter by Form](storm_ref_filter.md#filter-form)
- [Filter by Property](storm_ref_filter.md#filter-prop)
- [Filter by Property Value - Standard Comparison Operators](storm_ref_filter.md#filter-by-property-value---standard-comparison-operators)
- [Filter by Property Value - Extended Comparison Operators](storm_ref_filter.md#filter-prop-extended)
- [Tag Filters](storm_ref_filter.md#tag-filter)

> [!TIP]
> In general, you can filter using the same criteria and comparison operators used for lift operations. This includes using a wildcard ( `*` ) to partially match form names and using [Interface](../glossary.md#gloss-interface) names to filter by all forms that implement an interface.
>
> Because filter operations act on a pre-selected **subset** of nodes, some additional methods are available for filtering that would be less efficient for initial lift operations. For example, you can filter FQDNs (`inet:fqdn` nodes) by prefix ( `^=` ), although you cannot lift FQDNs using that operator. Similarly, you can [Filter by Tag Globs](storm_ref_filter.md#filter-tag-globs) but you cannot lift using that syntax.

Storm also supports specialized filters and filter operations:

- [Compound Filters](storm_ref_filter.md#filter-compound)
- [Subquery Filters](storm_ref_filter.md#filter-subquery)
- [Expression Filters](storm_ref_filter.md#filter-expression)
- [Embedded Property Syntax](storm_ref_filter.md#embed_prop_syntax)

See [Storm Reference - Document Syntax Conventions](storm_ref_syntax.md#storm-ref-syntax) for an explanation of the syntax format used below.

See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details on special syntax or handling for specific data types.

<a id="filter-form"></a>


## Filter by Form

A "filter by form" operation modifies your working set to include (or exclude) all nodes of the specified form. The wildcard (asterisk) character ( `*` ) can be used to filter based on forms that match a partial form name / namespace.

If a form (or forms) in the working set implements an [Interface](../glossary.md#gloss-interface), you can specify the interface name to filter based on all forms that implement the interface.

<a id="filter-form-name"></a>


### Filter by Form Name

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>*

**Examples:**

Filter the current working set to only include fully qualified domain names (FQDNs / `inet:fqdn` nodes):

```mdstorm --hide
[ inet:fqdn=woot.com inet:fqdn=vertex.link  inet:fqdn=google.com inet:ip=127.0.0.1 ] +inet:fqdn
```

``` text
<query> +inet:fqdn
```

Filter the current working set to exclude URLs (`inet:url` nodes):

```mdstorm --hide
[ inet:fqdn=vertex.link inet:url=https://vertex.link ] -inet:url
```

``` text
<query> -inet:url
```

<a id="filter-form-wildcard"></a>


### Filter by Form Name - Wildcard

You can use the wildcard (asterisk) character ( `*` ) to specify all forms that match a partial form name. Use of the wildcard is not limited to form namespace boundaries.

> [!NOTE]
> The wildcard can only be used at the end of the partial form name match. It cannot be used at the beginning or in the middle of the form name. For example, both of the following are **invalid**:
>
> `+*:header`
>
> `-it:exec:*:del`
>
> In addition, use of the wildcard does not extend to partial matching of **property** names. For example, `entity:contact` is a form that has multiple `:place` secondary properties (e.g., `:place:name`, `:place:loc`). The following is **invalid** because it tries to match a partial property name:
>
> `+entity:contact:place:*`

**Syntax:**

*\<query\>* **+** \| **-** *\<partial_form_name\>* \*\*\*\*\*

**Examples:**

Filter the current working set to exclude DNS nodes (e.g., `inet:dns:a`, `inet:dns:mx`, `inet:dns:request`):

```mdstorm --hide
[ inet:dns:a=(example.com, 1.2.3.4) inet:fqdn=woot.com inet:dns:request=( { "time": "2023/05/03 21:09:04.000", "query:name": "vertex.link" } ) ] -inet:dns:*
```

``` text
<query> -inet:dns:*
```

Filter the current working set to only include antivirus / scan-related nodes (e.g., `it:av:scan:result`, `it:av:signame`):

```mdstorm --hide
[ it:av:scan:result=0002a57045f969b18245349054662d73 it:av:signame=backdoor.maggie inet:fqdn=woot.com ] +it:av:s*
```

``` text
<query> +it:av:s*
```

### Filter Form by Interface

You can use the name of an interface to filter all forms that implement that interface.

> [!NOTE]
> When filtering by interface, you cannot use the wildcard ( `*` ) character to match multiple interface names. Synapse will interpret use of the wildcard as an attempt to match multiple form names.

**Syntax:**

*\<query\>* **+** \| **-** *\<interface\>*

**Examples:**

Filter the current working set to only include host event nodes (all nodes of all forms that implement the `it:host:event` interface):

```mdstorm --hide
[ inet:fqdn=woot.com file:bytes=( { "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" } ) it:exec:file:add=30007dc3cdd02b6cde7b8a140d3759f5 it:exec:windows:registry:set=70007c24662e98b17b3d4aaab669aebb ] +it:host:event
```

``` text
<query> +it:host:event
```

Filter the current working set to exclude taxonomy nodes (all nodes of all forms that implement the `meta:taxonomy` interface):

```mdstorm --hide
[ risk:threat=( { "name": "oilrig", "reporter:name": "palo alto" } ) risk:compromise=( { "name": "very bad compromise", "reporter:name": "recorded future" } ) risk:attack:type:taxonomy=very.bad risk:threat:type:taxonomy=pranksters ] -meta:taxonomy
```

``` text
<query> -meta:taxonomy
```

<a id="filter-prop"></a>


## Filter by Property

A "filter by property" operation modifies your working set to include (or exclude) all forms that **have** the specified property (secondary or extended), regardless of the property value.

> [!TIP]
> When filtering by property, you can specify the property using either the **full** property name (i.e., the combined form and property, such as `inet:dns:a:ip`) or the **relative** property name (i.e., the property name alone, including its separator character, such as `:ip`).
>
> Using the relative property name allows for simplified syntax and more efficient data entry ("less typing"). Full property names can be used for clarity (i.e., specifying **exactly** what you want to filter on).
>
> Full property names are **required** when filtering on a property using an interface. They may also be required in cases where multiple nodes in the inbound working set have the same relative property name (e.g., `inet:dns:a:ip` and `inet:asnip:ip`) and you only wish to filter based on the property of one of the forms.
>
> Each example below is shown using both the full property name (*\<form\>:\<prop\>*) and the relative property name (*:\<prop\>*) where applicable.

<a id="filter-prop-second"></a>


### Filter by Secondary Property

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** *\<prop\>*

**Examples:**

Filter the current working set to only include threats (`risk:threat` nodes) that have an assessed country of origin (`:place:country:code` property):

```mdstorm --hide
[ ( risk:threat=( { "reporter:name": "google", "name": "unc1234" } ) ) ( risk:threat=( { "reporter:name": "microsoft", "name": "peach sandstorm" } ) :place:country:code=ir ) ( risk:threat=( { "reporter:name": "sophos", "name": "bronze butler" } ) :place:country:code=cn ) ] +risk:threat:place:country:code
```

``` text
<query> +risk:threat:place:country:code
```

```mdstorm --hide
risk:threat +:place:country:code
```

``` text
<query> +:place:country:code
```

Filter the current working set to exclude articles (`doc:report` nodes) that have a publisher name (`:publisher:name` property):

```mdstorm --hide
[ doc:report=( { "publisher:name": "microsoft", "published": "2026/03/10" } ) doc:report=( { "publisher:name": "eset", "published": "2026/04/28" } ) doc:report=50004ea4025f1b60b7fe5670e41c8cd2 ] -doc:report:publisher:name
```

``` text
<query> -doc:report:publisher:name
```

```mdstorm --hide
doc:report -:publisher:name
```

``` text
<query> -:publisher:name
```

<a id="filter-prop-interface"></a>


### Filter by Interface Property

If a form implements an [Interface](../glossary.md#gloss-interface) that defines a set or properties, you can filter all nodes of all forms that have that property by specifying the full name of the interface and its property.

> [!TIP]
> When filtering using an interface property, you must use full property syntax (i.e., the combined interface and property name).

**Syntax:**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>*

**Example:**

Filter the current working set to only include those host event nodes (all nodes of all forms that implement the `it:host:event` interface) that have a `:time` property:

```mdstorm --hide
[ it:exec:file:add=21001f4244940b70fe40c83fe3d43f15 ( it:exec:file:add=830044cffe0d11151cd1946a4651ec63 :time=now ) ] +it:host:event:time
```

``` text
<query> +it:host:event:time
```

<a id="filter-prop-extend"></a>


### Filter by Extended Property

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:\_** *\<prop\>*

**Example:**

Filter the current working set to exclude those organizations (`ou:org` nodes) that are considered threats (`:_vertex:threatintel:isthreat`):

```mdstorm --hide
[ ( ou:org=( { "name": "vertex" } ) :_vertex:threatintel:isthreat=0 ) ( ou:org=( { "name": "fsb" } ) :_vertex:threatintel:isthreat=1 ) ] -ou:org:_vertex:threatintel:isthreat
```

``` text
<query> -ou:org:_vertex:threatintel:isthreat
```

```mdstorm --hide
ou:org -:_vertex:threatintel:isthreat
```

``` text
<query> -:_vertex:threatintel:isthreat
```

> [!TIP]
> The `:_vertex:threatintel:isthreat` extended property is a Boolean property added by the [Vertex-Threat-Intel](/docs/vertex-threat-intel/latest/index.md) Power-Up. It can be used to indicate whether an organization is tracked as a threat group.

## Filter by Property Value - Standard Comparison Operators

A "filter by property value" operation modifies the current working set to include (or exclude) the node(s) whose property matches the specified value. This type of filter requires:

- the filter operator ( `+` or `-` );
- the property name (full or relative) to use for the filter;
- a [Comparison Operator](../glossary.md#gloss-comp-operator) to specify how the property value should be evaluated; and
- the property value.

A "filter by property value" can be performed using primary, secondary, or extended properties.

In Synapse, we define **standard comparison operators** as the following set of operators:

- equal to ( `=` )
- less than ( `<` )
- greater than ( `>` )
- less than or equal to ( `<=` )
- greater than or equal to ( `>=` )

For filter operations, the not equal ( `!=` ) operator is also supported.

When filtering by secondary or extended property value, you can specify the property using either the **full** property name (i.e., the combined form and property, such as `inet:dns:a:ip`) or the **relative** property name (i.e., the property name alone, including its separator character, such as `:ip`).

Using the relative property name allows for simplified syntax and more efficient data entry ("less typing"). Full property names can be used for clarity (i.e., specifying **exactly** what you want to filter on).

Full property names are **required**:

- when filtering based on an interface property value.
- in cases where multiple nodes in the inbound working set have the same relative property name (e.g., `inet:dns:a:ip` and `inet:asnip:ip`, or a meta property such as `.created`) and you only wish to filter based on the property of one of the forms.

Each example below is shown using both the full property name (*\<form\>:\<prop\>*) and the relative property name (*:\<prop\>*) where applicable.

> [!TIP]
> When filtering nodes by a property value where the value is a time (date / time), you do not need to use full `YYYY/MM/DD hh:mm:ss.mmm` syntax. Synapse allows you to use either lower resolution values (e.g., `YYYY/MM/DD`) or wildcard values (e.g., `YYYY/MM*`). In particular, wildcard syntax can be used to specify any values that match the wildcard expression. See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) types for a detailed discussion of these behaviors.

<a id="filter-prop-std-primary"></a>


### Filter by Primary Property Value

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* *\<operator\>* *\<valu\>*

Filter the current working set to exclude the loopback IP address (`127.0.0.1`):

```mdstorm --hide
[ inet:ip=127.0.0.1 inet:ip=8.8.8.8 ] -inet:ip = 127.0.0.1
```

``` text
<query> -inet:ip = 127.0.0.1
```

```mdstorm --hide
inet:ip=127.0.0.1 inet:ip=8.8.8.8 +inet:ip != 127.0.0.1
```

``` text
<query> +inet:ip != 127.0.0.1
```

<a id="filter-prop-std-secondary"></a>


### Filter by Secondary Property Value

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** *\<prop\>* *\<operator\>* *\<pval\>*

Filter the current working set to include only those FQDNs (`inet:fqdn` nodes) that are also logical zones:

```mdstorm --hide
[ inet:fqdn=woot.com inet:fqdn=vertex.link inet:fqdn=google.com ] +inet:fqdn:iszone = 1
```

``` text
<query> +inet:fqdn:iszone = 1
```

```mdstorm --hide
inet:fqdn=woot.com inet:fqdn=vertex.link inet:fqdn=google.com +:iszone = 1
```

``` text
<query> +:iszone  = 1
```

Filter the current working set to exclude any PE (portable executable) metadata files (`file:mime:pe` nodes) with a compiled time of `1992-06-19 22:22:17`:

```mdstorm --hide
$file1={ [ file:bytes=( { "sha256": "d7c12acb306b5100a5497586942b68a8f6d5deb353083da594caba2523c3171f" } ) ] } $file2={ [ file:bytes=( { "sha256": "54ebdea80d30660f1d7be0b71bc3eb04189ef2036cdbba24d60f474547d3516a" } ) ] } [ file:mime:pe=( { "file": $file1, "compiled": "1992-06-19T22:22:17Z" } ) file:mime:pe=( { "file": $file2, "compiled": "2025-10-28T19:04:16Z" } ) ] -file:mime:pe:compiled = '1992/06/19 22:22:17'
```

``` text
<query> -file:mime:pe:compiled = '1992/06/19 22:22:17'
```

```mdstorm --hide
file:mime:pe:compiled -:compiled = '1992/06/19 22:22:17'
```

``` text
<query> -:compiled = '1992/06/19 22:22:17'
```

Filter the current working set to include only those PE (portable executable) metadata files (`file:mime:pe` nodes) with a compiled time in 2025:

```mdstorm --hide
$file1={ [ file:bytes=( { "sha256": "4f0ff2089666fbc6e71f9e6cd64f854785bb4a74b307e9df39b811f186eaf7d0" } ) ] } $file2={ [ file:bytes=( { "sha256": "3c7fb61f0601f9facd3c2a1b319039a3fad6535b33359493b8a8a3f24dea00e3" } ) ] } [ file:mime:pe=( { "file": $file1, "compiled": "2025/11/05 00:07:13" } ) file:mime:pe=( { "file": $file2, "compiled": "2022/07/22 23:12:15" } ) ] +file:mime:pe:compiled = 2025*
```

``` text
<query> +file:mime:pe:compiled = 2025*
```

```mdstorm --hide
file:mime:pe:compiled +:compiled = 2025*
```

``` text
<query> +:compiled = 2025*
```

Filter the current working set to exclude those files (`file:bytes` nodes) whose size is greater than or equal to 1MB:

```mdstorm --hide
[ ( file:bytes=( { "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" } ) :size=16384 ) ( file:bytes=( { "sha256": "ec04b04e079ff54e73faf7ef72e69b8919fb24eecba521b65788c47eac0baf41" } ) :size=1000054 ) ] -file:bytes:size >= 1000000
```

``` text
<query> -file:bytes:size >= 1000000
```

```mdstorm --hide
file:bytes -:size >= 1000000
```

``` text
<query> -:size >= 1000000
```

<a id="filter-prop-std-interface"></a>


### Filter by Interface Property Value

If a form implements an [Interface](../glossary.md#gloss-interface) that defines a set of properties, you can filter all nodes of all forms with a specific value for that property by using the name of the interface.

> [!TIP]
> When filtering using an interface property value, you must use full property syntax (i.e., the combined interface and property name).

**Syntax:**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples:**

Filter the current working set to only include those Microsoft Office metadata nodes (all nodes of all forms that implement the `file:mime:msoffice` interface) whose `:author:name` value is `admin`:

```mdstorm --hide
[ file:mime:msdoc=( { "application:name": "Microsoft Word", "author:name": "ozzie" } ) file:mime:msxls=( { "application:name": "Microsoft Excel", "author:name": "admin" } ) ] +file:mime:msoffice:author:name = admin
```

``` text
<query> +file:mime:msoffice:author:name = admin
```

Filter the current working set to exclude any host event nodes (all nodes of all forms that implement the `it:host:event` interface) observed earlier than January 1, 2024:

```mdstorm --hide
[ (it:exec:file:add=97001f17db58c29f039147b67528f891 :time=now) (it:exec:file:write=ab004740d68588f0dd7f9f9cf8fa27ee :time=2022/02/20) ] -it:host:event:time < 2024/01/01
```

``` text
<query> -it:host:event:time < 2024/01/01
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

**+** \| **-** \[ *\<form\>* \] **.** *\<prop\>* *\<operator\>* *\<pval\>*

Filter the current working set to include only those nodes created on January 1, 2024 or later:

```mdstorm --hide
.created +.created >= 2024/01/01
```

``` text
<query> +.created >= 2024/01/01
```

Filter the current working set to include only those FQDNs (`inet:fqdn` nodes) created on January 1, 2024 or later:

```mdstorm --hide
.created +inet:fqdn.created >= 2024/01/01
```

``` text
<query> +inet:fqdn.created >= 2024/01/01
```

### Filter by Extended Property Value

When filtering by extended property value, you can use any standard comparison operator supported by the property's type. For example, if the extended property is a string, only the equal to ( `=` ) standard operator is supported. If the extended property is an integer, any of the standard operators can be used.

**Syntax:**

**+** \| **-** \[ *\<form\>* \] **:\_** *\<prop\>* *\<operator\>* *\<pval\>*

Filter the current working set to include only those organizations (`ou:org` nodes) which are categorized as threats (`:_vertex:threatintel:isthreat`):

```mdstorm --hide
[ ( ou:org=( { "name": "vertex" } ) :_vertex:threatintel:isthreat=0 ) ( ou:org=( { "name": "fsb" } ) :_vertex:threatintel:isthreat=1 ) ] +ou:org:_vertex:threatintel:isthreat = true
```

``` text
<query> +ou:org:_vertex:threatintel:isthreat = true
```

```mdstorm --hide
ou:org +:_vertex:threatintel:isthreat = true
```

``` text
<query> +:_vertex:threatintel:isthreat = true
```

> [!TIP]
> Boolean values can be specified using either `true` / `false` or `1` / `0`.

Filter the current working set to include only those files (`file:bytes` nodes) whose VirusTotal reputation score (`:_virustotal:reputation`) is less than -100:

```mdstorm --hide
[ file:bytes=( { "sha256": "87b7e57140e790b6602c461472ddc07abf66d07a3f534cdf293d4b73922406fe" } ) :size=188928 :mime='application/vnd.microsoft.portable-executable' :_virustotal:reputation=-427 ] +file:bytes:_virustotal:reputation < -100
```

``` text
<query> +file:bytes:_virustotal:reputation < -100
```

```mdstorm --hide
file:bytes +:_virustotal:reputation < -100
```

``` text
<query> +:_virustotal:reputation < -100
```

<a id="filter-prop-extended"></a>


## Filter by Property Value - Extended Comparison Operators

Storm supports a set of extended comparison operators (comparators) for specialized filter operations. In most cases, the same extended comparators are available for both lifting and filtering:

- [Filter by Regular Expression (~=)](storm_ref_filter.md#filter-regex)
- [Filter by Prefix (^=)](storm_ref_filter.md#filter-prefix)
- @@XNAMED@@Filter by Time or Interval (@=)@@
- [Filter by Range (\*range=)](storm_ref_filter.md#filter-range)
- [Filter by Set Membership (\*in=)](storm_ref_filter.md#filter-set)
- [Filter by Proximity (\*near=)](storm_ref_filter.md#filter-proximity)
- [Filter by (Arrays) (\*\[ \])](storm_ref_filter.md#filter-by-arrays)

Each extended comparison operator can be used with any kind of property (primary, secondary, or extended) whose [Type](../glossary.md#gloss-type) is appropriate for the comparison used. When filtering by secondary property value, you can optionally specify an [Interface](../glossary.md#gloss-interface) name and property to filter based on all forms that implement that interface.

<a id="filter-regex"></a>


### Filter by Regular Expression (~=)

The extended comparator `~=` is used to filter nodes based on PCRE-compatible regular expressions.

> [!TIP]
> [Filter by Prefix (^=)](storm_ref_filter.md#filter-prefix) can be used to filter based on the beginning of string-based properties, and is more efficient for beginning-of-string filter operations. It should be used instead of a regular expression filter where possible.

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* **~=** *\<regex\>*

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **~=** *\<regex\>*

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **~=** *\<regex\>*

**Examples:**

Filter the current working set to only include reports (`doc:report` nodes) whose title includes the string `sandstorm`:

```mdstorm --hide
[ (doc:report=( { "publisher:name": "microsoft", "title": "peach sandstorm password spray campaigns enable intelligence collection at high-value targets", "published": "2023/09/14 00:00:00" } ) ) (doc:report=( { "publisher:name": "microsoft", "title": "cadet blizzard emerges as a novel and distinct russian threat actor", "published": "2023/06/14 00:00:00" } ) ) ] +doc:report:title ~= sandstorm
```

``` text
<query> +doc:report:title ~= sandstorm
```

```mdstorm --hide
doc:report +:title ~= sandstorm
```

``` text
<query> +:title ~= sandstorm
```

Filter the current working set to exclude organizations (`ou:org` nodes) whose name contains a string that starts with `v`, followed by 0 or more characters, followed by `x`:

```mdstorm --hide
[ ( ou:org=4b0c2c5671874922ce001d69215d032f :name="the vertex project" :names=(vertex,) ) ( ou:org=ad8de4b5da0fccb2caadb0d425e35847 :name=vxunderground ) ] -ou:org:name ~= '^v.*x'
```

``` text
<query> -ou:org:name ~= '^v.*x'
```

```mdstorm --hide
ou:org -:name ~= '^v.*x'
```

``` text
<query> -:name ~= '^v.*x'
```

Filter the current working set to only include taxonomy nodes (all nodes of all forms that implement the `meta:taxonomy` interface) whose description (`:desc` property) includes the string `credential`:

```mdstorm --hide
[ risk:attack=e10028b8a56d01ccc1df5fcd9c5b8b65 ( risk:attack:type:taxonomy=foo.bar :desc='credential phishing' ) ( entity:goal:type:taxonomy=baz.faz :desc='obtain admin credentials' ) ( belief:system:type:taxonomy=hurr.derp :desc='hand out uncs like candy' ) ] +meta:taxonomy:desc ~= credential
```

``` text
<query> +meta:taxonxomy:desc ~= credential
```

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

```mdstorm --hide
[ inet:email=abuse@1and1.com inet:email=abuse.tor-exit@posteo.org ] -inet:email ^= abuse
```

``` text
<query> -inet:email ^= abuse
```

Filter the current working set to only include organizations (`ou:org` nodes) whose name starts with `ministry`:

```mdstorm --hide
[ ( ou:org=a7f31ce9809e103ddedf36c1e1e91249 :name='ministry for foreign affairs of finland' ) ( ou:org=1560dc4129405e18fd32f30b6f01fa1f :name='ministry of finance of ukraine' ) ] +ou:org:name ^= ministry
```

``` text
<query> +ou:org:name ^= ministry
```

```mdstorm --hide
ou:org +:name ^= ministry
```

``` text
<query> +:name ^= ministry
```

Filter the current working set to only include Microsoft Office metadata nodes (all nodes of all forms that implement the `file:mime:msoffice` interface) whose `:author:name` value starts with `Admin`:

```mdstorm --hide
[ file:mime:msdoc=( { "application:name": "Microsoft Word", "author:name": "ozzie" } ) file:mime:msdoc=( { "application:name": "Microsoft Word", "author:name": "Administrator" } ) file:mime:msppt=( { "application:name": "Microsoft PowerPoint", "author:name": "admin" } ) ] +file:mime:msoffice:author:name ^= Admin
```

``` text
<query> +file:mime:msoffice:author:name ^= Admin
```

<a id="filter-interval"></a>


### Filter by Time or Interval (@=)

The time extended comparator (`@=`) is used to filter nodes based on comparisons among various combinations of times and intervals.

> [!TIP]
> See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for additional detail on the use and behavior of [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) data types.

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **@=(** *\<ival_min\>* **,** *\<ival_max\>* **)**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **@=** *\<time\>*

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **@=(** *\<ival_min\>* **,** *\<ival_max\>* **)**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **@=** *\<time\>*

**Examples:**

Filter the current working set to include only those DNS A records (`inet:dns:a` nodes) whose `:seen` values fall between July 1, 2022 and and August 1, 2022:

```mdstorm --hide
[ inet:dns:a=(easymathpath.com, 135.125.78.187) :seen=(2021/09/12 00:00:00, 2023/08/08 01:50:54.001) ] +inet:dns:a:seen @= ( 2022/07/01, 2022/08/01 )
```

``` text
<query> +inet:dns:a:seen @= ( 2022/07/01, 2022/08/01 )
```

```mdstorm --hide
inet:dns:a +:seen @= ( 2022/07/01, 2022/08/01 )
```

``` text
<query> +:seen @= ( 2022/07/01, 2022/08/01 )
```

Filter the current working set to only include DNS requests (`inet:dns:request` nodes) that occurred on May 3, 2023 (between `05/03/2023 00:00:00` and `05/03/2023 23:59:59`):

```mdstorm --hide
[ inet:dns:request=( { "time": "2023/05/03 21:09:04.000", "query:name": "vertex.link" } ) ] +inet:dns:request:time @= ( '2023/05/03 00:00:00', '2023/05/04 00:00:00' )
```

``` text
<query> +inet:dns:request:time @= ( '2023/05/03 00:00:00', '2023/05/04 00:00:00' )
```

```mdstorm --hide
inet:dns:request +:time @= ( '2023/05/03 00:00:00', '2023/05/04 00:00:00' )
```

``` text
<query> +:time @= ( '2023/05/03 00:00:00', '2023/05/04 00:00:00' )
```

> [!TIP]
> Because the `inet:dns:request:time` property is a single date / time value, the following filters will also work:
>
> - `+inet:dns:request:time = 2023/05/03*`
> - `+:time = 2023/05/03*`

Filter the current working set to only include DNS A records (`inet:dns:a` nodes) whose `:seen` time window includes the date December 1, 2023:

```mdstorm --hide
inet:dns:a +inet:dns:a:seen @= 2023/12/01
```

``` text
<query> +inet:dns:a:seen @= 2023/12/01
```

```mdstorm --hide
inet:dns:a +:seen @= 2023/12/01
```

``` text
<query> +:seen @= 2023/12/01
```

Filter the current working set to include only those domain WHOIS records (`inet:whois:record` nodes) where the domain was registered (created) exactly on March 19, 2019 at 5:00 UTC:

```mdstorm --hide
[ inet:whois:record=( { "fqdn": "woot.com", "created": "2019/03/19 05:00:00" } ) inet:whois:record=( { "fqdn": "vertex.link", "created": "2025/06/27 09:22:57" } ) ] +inet:whois:record:created @= '2019/03/19 05:00:00'
```

``` text
<query> +inet:whois:record:created @= '2019/03/19 05:00:00'
```

```mdstorm --hide
inet:whois:record +:created @= '2019/03/19 05:00:00'
```

``` text
<query> +:created @= '2019/03/19 05:00:00'
```

> [!NOTE]
> When comparing a single time value to a time property, the `@=` comparator behaves just like the equal to ( `=` ) operator.

Filter the current working set to only include the reports (`doc:report` nodes) that were published within the past day:

```mdstorm --hide
[ doc:report=0f0040e43b61eee735820d5d65cdcdac :published=now ] +doc:report:published @= ( now, '-1 day' )
```

``` text
<query> +doc:report:published @= ( now, '-1 day' )
```

```mdstorm --hide
doc:report +:published @= ( now, '-1 day' )
```

``` text
<query> +:published @= ( now, '-1 day' )
```

Filter the current working set to only include the host event nodes (all nodes of all forms that implement the `it:host:event` interface) whose `:time` value is within the past three hours:

```mdstorm --hide
[ ( it:exec:mutex:add=6b00d6e6b1bdb5fbc12331059a90353b :time=2024/01/13 ) ( it:exec:file:write=2d007c5bd0b84ca9c9b4c6b4c17bd997 :time=2024/01/31 ) ( it:exec:file:add=79001ff435d6652d09bce9048acbe3b0 :time=now ) ] +it:host:event:time @= (now, '-3 hours')
```

``` text
<query> +it:host:event:time @= (now, '-3 hours')
```

**Usage Notes:**

- When specifying an interval with the `@=` operator, the minimum value is included in the interval for comparison purposes but the maximum value is **not**. This is equivalent to "greater than or equal to *\<min\>* and less than *\<max\>*". This behavior differs from that of the `*range=` operator, which includes **both** the minimum and maximum.

- **Comparing intervals to intervals:** when using an interval with the `@=` operator to filter nodes based on an interval property, Synapse returns nodes whose interval value has **any** overlap with the specified interval. For example:

  - A lift interval of September 1, 2018 to October 1, 2018 ( 2018/09/01, 2018/10/01 ) will match nodes with any of the following intervals:
    - August 12, 2018 to September 6, 2018 ( 2018/08/12, 2018/09/06 ).
    - September 13, 2018 to September 17, 2018 ( 2018/09/13, 2018/09/17 ).
    - September 30, 2018 to November 5, 2018 ( 2018/09/30, 2018/11/05 ).

- **Comparing intervals to times:** When using an interval with the `@=` operator to lift nodes based on a time property, Synapse returns nodes whose time value falls within the specified interval.

- **Comparing times to times:** When using a time with the `@=` operator to filter nodes based on a time property, Synapse returns nodes whose timestamp is an **exact match** of the specified time. In other words, in this case the interval comparator ( `@=` ) behaves like the equal to comparator ( `=` ).

- When specifying date / time and interval values, Synapse allows the use of both lower resolution values (e.g., `YYYY/MM/DD`), and wildcard values (e.g., `YYYY/MM*`). Wildcard time syntax may provide a simpler and more intuitive means to specify some intervals. For example `inet:whois:rec:asof=2018*` is equivalent to `inet:whois:rec:asof@=('2018/01/01', '2019/01/01')`.

- Time-based keywords (such as `now`) and relative time syntax (expressions such as `+-1 hour` or `-7 days`) can be used for interval values.

  See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) types for a detailed discussion of these behaviors.

<a id="filter-range"></a>


### Filter by Range (\*range=)

The range extended comparator (`*range=`) supports filtering nodes whose *\<form\> = \<valu\>* or *\<prop\> = \<pval\>* fall within a specified range of values. The comparator can be used with types such as integers and times.

> [!NOTE]
> The `*range=` operator can be used to filter `inet:ip` values. However, ranges of [inet:ip](storm_ref_type_specific.md#type-inet-ip) nodes can also be filtered directly by specifying the lower and upper addresses in the range using `<min>-<max>` format. For example:
>
> - `+inet:ip = 192.168.0.0-192.168.0.10`
> - `+:ip = 192.168.0.0-192.168.0.10`
>
> For IPv6 values, the range must be enclosed in quotes:
>
> - `+inet:ip = "::0-ff::ff"`
> - `+:ip = "::0-ff::ff"`
>
> The `*range=` operator cannot be used to compare a time range with a property value that is an interval (`ival` type). The interval ( `@=` ) operator should be used instead.

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

**Examples:**

Filter the current working set to exclude files (`file:bytes` nodes) whose size is between 1000 and 100000 bytes:

```mdstorm --hide
[ file:bytes=( { "sha256": "00ecd10902d3a3c52035dfa0da027d4942494c75f59b6d6d6670564d85376c94" } ) :size=2000 ] -file:bytes:size *range= ( 1000, 100000 )
```

``` text
<query> -file:bytes:size *range= ( 1000, 100000 )
```

```mdstorm --hide
file:bytes -:size *range= ( 1000, 100000 )
```

``` text
<query> -:size *range= ( 1000, 100000 )
```

Filter the current working set to only include files (`file:bytes` nodes) whose VirusTotal reputation score (`:_virustotal:reputation`) is between -20 and 20:

```mdstorm --hide
[ ( file:bytes=( { "sha256": "d231f3b6d6e4c56cb7f149cbc0178f7b80448c24f14dced5a864015512b0ba1f" } ) :_virustotal:reputation=-16 ) ( file:bytes=( { "sha256": "d0e526a19497117a854f1ac9a9347f7621709afc3548c2e6a46b19e833578eac" } ) :_virustotal:reputation=8 ) ] +file:bytes:_virustotal:reputation *range= ( -20, 20 )
```

``` text
<query> +file:bytes:_virustotal:reputation *range= ( -20, 20 )
```

```mdstorm --hide
file:bytes +:_virustotal:reputation *range= ( -20, 20 )
```

``` text
<query> +:_virustotal:reputation *range= ( -20, 20 )
```

Filter the current working set to exclude DNS requests (`inet:dns:request` nodes) that were made between November 29, 2025 and January 14, 2026:

```mdstorm --hide
[ inet:dns:request=( { "query:name": "vertex.link", "time": "2025/12/09 13:47:11" } ) inet:dns:request=( { "query:name": "example.com", "time": "2026/05/03 20:07:01" } ) ] -inet:dns:request:time *range= ( 2025/11/29, 2026/01/14 )
```

``` text
<query> -inet:dns:request:time *range= ( 2025/11/29, 2026/01/14 )
```

```mdstorm --hide
inet:dns:request -:time *range= ( 2025/11/29, 2026/01/14 )
```

``` text
<query> -:time *range= ( 2025/11/29, 2026/01/14 )
```

Filter the current working set to only include DNS requests (`inet:dns:request` nodes) made within one day of December 1, 2021:

```mdstorm --hide
[ inet:dns:request=c40037adf2d5bf23295fa8c55eaad5f6 :time="2021/11/30 21:09:04.000"] +inet:dns:request:time *range= ( 2021/12/01, '+-1 day' )
```

``` text
<query> +inet:dns:request:time *range= ( 2021/12/01, '+-1 day' )
```

```mdstorm --hide
inet:dns:request +:time *range= ( 2021/12/01, '+-1 day' )
```

``` text
<query> +:time *range= ( 2021/12/01, '+-1 day' )
```

Filter the current working set to only include taxonomy nodes (all nodes of all forms that implement the `meta:taxonomy` interface) whose `:depth` is between 1 and 3 (i.e., between 2 and 4 taxonomy elements):

```mdstorm --hide
[ risk:attack:type:taxonomy=bad risk:attack:type:taxonomy=bad.sorta risk:attack:type:taxonomy=bad.very risk:attack:type:taxonomy=bad.pretty.darn.bad ] +meta:taxonomy:depth *range= (1, 3)
```

``` text
<query> +meta:taxonomy:depth *range= (1, 3)
```

**Usage Notes:**

- When specifying a range (`*range=`), both the minimum and maximum values are **included** in the range (the equivalent of "greater than or equal to *\<min\>* and less than or equal to *\<max\>*"). This behavior is slightly different than that for time interval (`@=`), which includes the minimum but not the maximum.
- When specifying a range of time values, Synapse allows you to use either lower resolution values (e.g., `YYYY/MM/DD`) or wildcard values (e.g., `YYYY/MM*`) for the minimum and/or maximum range values. In some cases, plain wildcard time syntax may provide a simpler and more intuitive means to specify some time ranges. For example `+inet:whois:rec:asof=2018*` (or `+:asof=2018*`) is equivalent to `+inet:whois:rec:asof*range=('2018/01/01', '2018/12/31 23:59:59.999')` (or `+:asof*range=('2018/01/01', '2018/12/31 23:59:59.999')`). See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) types for a detailed discussion of these behaviors.
- When using keywords (such as `now`) or relative values (such as `-1 hour`) to specify a range of times, the first value in the range is calculated relative to the current time and the second value is calculated relative to the first value.
- If you specify a range value that is nonsensical or exclusionary (such as `( 47, 16 )`), Synapse will **not** generate an error and will simply fail to return results. (The expression is syntactically correct, but no value is both greater than 47 and less than 16).

<a id="filter-set"></a>


### Filter by Set Membership (\*in=)

The set membership extended comparator (`*in=`) supports filtering nodes whose *\<form\> = \<valu\>* or *\<prop\> = \<pval\>* matches any of a set of specified values. The comparator can be used with any type.

**Syntax:**

*\<query\>* **+** \| **-** *\<form\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

*\<query\>* **+** \| **-** *\<interface\>* **:** *\<prop\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

**Examples:**

Filter the current working set to exclude entity names (`entity:name` nodes) matching any of the specified values:

```mdstorm --hide
[ entity:name=fsb entity:name=gru entity:name='yevgeniy prigozhin' entity:name='vladimir putin' ] -entity:name *in= ( fsb, 'vladimir putin' )
```

``` text
<query> -entity:name *in= ( fsb, 'vladimir putin' )
```

Filter the current working set to only include IP addresses (`inet:ip` nodes) associated with any of the specified Autonomous System (AS) numbers:

```mdstorm --hide
[ (inet:asn=44477 :registrant:name='stark industries solutions ltd') (inet:asn=20473 :registrant:name=as-choopa) (inet:asn=9009 :registrant:name='m247 europe srl') ]
```

```mdstorm --hide
[ ( inet:ip=45.67.34.75 :asn=44477 ) ( inet:ip=149.248.1.50 :asn=20473 ) ( inet:ip=89.249.66.255 :asn=9009 ) ] +inet:ip:asn *in= ( 9009, 20473, 44477 )
```

``` text
<query> +inet:ip:asn *in= ( 9009, 20473, 44477 )
```

```mdstorm --hide
inet:ip +:asn *in= ( 9009, 20473, 44477 )
```

``` text
<query> +:asn *in= ( 9009, 20473, 44477 )
```

Filter the current working set to only include tags (`syn:tag` nodes) whose final tag element matches any of the specified string values:

```mdstorm --hide
[ syn:tag=rep.talos.plugx syn:tag=rep.eset.korplug syn:tag=rep.mandiant.sogu syn:tag=rep.alienvault.kaba ] +syn:tag:base *in= ( plugx, korplug, sogu, kaba )
```

``` text
<query> +syn:tag:base *in= ( plugx, korplug, sogu, kaba )
```

```mdstorm --hide
syn:tag +:base *in= ( plugx, korplug, sogu, kaba )
```

``` text
<query> +:base *in= ( plugx, korplug, sogu, kaba )
```

<a id="filter-proximity"></a>


### Filter by Proximity (\*near=)

The proximity extended comparator (`*near=`) supports filtering nodes by "nearness" to another node. Currently, `*near=` supports proximity based on geospatial location (i.e., nodes within a given radius of a specified latitude / longitude).

**Syntax:**

*\<query\>* **+** \| **-** \[ *\<form\>* \] **:** \| **.** \| **:\_** *\<prop\>* **\*near = ((** *\<lat\>* **,** *\<long\>* **),** *\<radius\>* **)**

**Examples:**

Filter the current working set to only include locations (`geo:place` nodes) within 500 meters of the Russian Cryptographic Museum (where the coordinates `55.83069, 37.59781` represent the Museum's location):

```mdstorm --hide
[ geo:place=( { "latlong": "55.83088, 37.59962", "name": "Russian Cryptographic Museum" } ) ] +geo:place:latlong *near= ( (55.83069, 37.59781), 500m )
```

``` text
<query> +geo:place:latlong *near= ( (55.83069, 37.59781), 500m )
```

```mdstorm --hide
geo:place +:latlong *near= ( (55.83069, 37.59781), 500m )
```

``` text
<query> +:latlong *near= ( (55.83069, 37.59781), 500m )
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
- The `*near=` comparator works for geospatial data by lifting nodes within a square bounding box centered at *\<lat\>,\<long\>*, then filters the nodes returned by ensuring that they are within the great-circle distance given by the *\<radius\>* argument.

<a id="filter-by-arrays"></a>


### Filter by (Arrays) (\*\[ \])

Storm uses a special syntax to filter (or lift) by comparison with one or more elements of an [array](storm_ref_type_specific.md#type-array) type. The syntax consists of an asterisk ( `*` ) preceding a set of square brackets ( `[ ]` ), where the square brackets contain a comparison operator and a value that can match one or more elements in the array. This allows users to match any value in the array list without needing to know the exact order or values of the array itself.

> [!NOTE]
> When filtering based on a value in an array property, you must use the relative name of the property. The full property name (i.e., the combined form and property) is not supported for this type of filter.

**Syntax:**

*\<query\>* **+** \| **-** **:** \| **.** \| **:\_** *\<prop\>* **\*\[** *\<operator\>* *\<pval\>* **\]**

**Examples:**

Filter the current working set to only include x509 certificates (`crypto:x509:cert` nodes) that reference FQDNs ending with `.xyz`:

```mdstorm --hide
[ crypto:x509:cert=8500881809f0d7738dd351a804e2f2ef :identities:fqdns=(woot.biz, woot.xyz) ] +:identities:fqdns *[= '*.xyz' ]
```

``` text
<query> +:identities:fqdns *[= '*.xyz' ]
```

Filter the current working set to only include threat clusters (`risk:threat` nodes) whose secondary (alternate) names include the string `dragon`:

```mdstorm --hide
[ ( risk:threat=( { "reporter:name": "lookout", "name": "apt41" } ) :names+='double dragon' )  ( risk:threat=( { "reporter:name": "sophos", "name": "iron liberty" } ) :names+=dragonfly ) ( risk:threat=( { "reporter:name": "google", "name": "apt28" } ) :names+='forest blizzard' ) ] +:names *[~= dragon ]
```

``` text
<query> +:names *[~= dragon ]
```

**Usage Notes:**

- The comparison operator used must be valid for filter operations for the type used in the array.
- The standard equals ( `=` ) operator can be used to filter nodes based on array properties, but the value specified must **exactly match** the **full** property value in question:
  - For example: `ou:org +:names=("the vertex project","the vertex project llc",vertex)` will filter to any `ou:org` nodes whose `:names` property consists of **exactly** those names in **exactly** that order.
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

A "filter by tag" operation downselects the current working set to include (or exclude) all nodes with the specified tag.

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>*

Filter the current working set to exclude all nodes that ESET associates with Sednit (`#rep.eset.sednit`):

```mdstorm --hide
[ inet:fqdn=kg-news.org inet:ip=92.114.92.125 +#rep.eset.sednit ] -#rep.eset.sednit
```

``` text
<query> -#rep.eset.sednit
```

Filter the current working set to only include nodes associated with anonymized infrastructure (`#cno.infra.anon`):

```mdstorm --hide
[ (inet:fqdn=ca2.vpn.airdns.org +#cno.infra.anon.vpn) (inet:ip=104.244.73.193 +#cno.infra.anon.tor.exit) ] +#cno.infra.anon
```

``` text
<query> +#cno.infra.anon
```

> [!TIP]
> Tags are hierarchical, and each tag element is its own tag; the tag `#cno.infra.anon` consists of the tags `#cno`, `#cno.infra`, and `#cno.infra.anon`. Filtering nodes using a tag "higher up" in the tag hierarchy will include (or exclude) nodes with the specified tag or any tag "lower down" in the hierarchy. In other words, filtering by `#cno.infra.anon` will filter all "anonymized" infrastructure, whether the infrastructure is a VPN (`#cno.infra.anon.vpn`), a TOR node (`#cno.infra.anon.tor`), or an anonymous proxy (`#cno.infra.anon.proxy`).

<a id="filter-tag-globs"></a>


### Filter by Tag Globs

Synapse supports filtering based on the set of tags that match a specified glob expression using single ( `*` ) or double ( `**` ) asterisks, or a combination of the two.

The single asterisk and double asterisk behave differently:

- The asterisk ( `*` ) represents an arbitrary string of zero or more characters that matches **within** a single tag element (i.e., one element as bounded by the tag's "dot" ( `.` ) separators).
- The double asterisk ( `**` ) represents an arbitrary string match of zero or more characters anywhere in the tag, including **across** tag elements.

Another way to look at this is that the single asterisk is constrained by the tag's "dot" boundaries, but the double asterisk is not.

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<string\>* \| \*\***\* \|**\***\* \[**.\*\* *\<string\>* \| \*\***\* \|**\*\*\*\* ... \]

**Examples:**

Filter the current working set to exclude any nodes tagged as `seduploader` by any third-party reporting organization:

```mdstorm --hide
[ inet:fqdn=woot.com +#rep.eset.seduploader +#rep.paloalto.seduploader +#rep.kaspersky.sednit ] -#rep.*.seduploader
```

``` text
<query> -#rep.*.seduploader
```

To record assessments made by third parties, The Vertex Project uses `rep` ("reported by") as the root tag element, followed by a tag element for the reporting organization (e.g., `rep.eset`), followed by the name of the "thing" reported (in this case, the `seduploader` malware family).

The tag glob filter above uses the single asterisk to match any tag element in the second position, and will match tags such as:

- `rep.eset.seduploader`
- `rep.paloalto.seduploader`

...etc.

Filter the current working set to include any nodes tagged as `cobaltstrike` by any third-party reporting organization whose name begins with `m`:

```mdstorm --hide
[ ( inet:fqdn=woot.com +#rep.mandiant.cobaltstrike ) ( inet:fqdn=evil.com +#rep.microsoft.cobaltstrike ) ( inet:ip=1.1.1.1 +#rep.malwarebazaar.cobaltstrike ) ] +#rep.m*.cobaltstrike
```

``` text
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

Filter the current working set to exclude any nodes tagged as `seduploader` either internally or by any third-party reporting organization:

```mdstorm --hide
[ inet:fqdn=woot.com +#rep.eset.seduploader +#rep.paloalto.seduploader +#rep.kaspersky.sednit ] -#*.*.seduploader
```

``` text
<query> -#*.*.seduploader
```

The Vertex Project uses the `cno` root tag to represent our own internal assessments (and distinguish them from third party-assessments), and the `mal` element to represent assessments related to malware. The tag glob filter above uses two single asterisks to match any element in both the first and second positions, and will match all of the following:

- `rep.eset.seduploader`
- `rep.paloalto.seduploader`
- `cno.mal.seduploader`

...etc.

Filter the current working set to include any nodes reported by Microsoft whose tags end in `blizzard`:

```mdstorm --hide
[ ( inet:fqdn=lotorgas.ru +#rep.microsoft.aqua_blizzard ) ( inet:fqdn=justiceua.org +#rep.microsoft.cadet_blizzard ) ( inet:fqdn=actblues.com +#rep.microsoft.forest_blizzard ) ( inet:fqdn=scandefinform.com +#rep.microsoft.star_blizzard ) ] +#rep.microsoft.**blizzard
```

``` text
<query> +#rep.microsoft.**blizzard
```

The tag glob filter above uses a double asterisk to match any Microsoft tag (tag that begins `rep.microsoft`) that ends in `blizzard`, regardless of tag depth (i.e., the double asterisk matches **across** tag elements). The filter will match all of the following:

- `rep.microsoft.aqua_blizzard`
- `rep.microsoft.cadet_blizzard`
- `rep.microsoft.very.long.tag.that.ends.with.blizzard`

...etc.

Filter the current working set to exclude any nodes tagged with any tag that starts with `cno` and is followed by any string:

```mdstorm --hide
[ ( inet:ip=93.90.223.185 +#cno.infra.dns.sink.hole ) ( inet:fqdn=vertex.link +#cno ) ] -#cno**
```

``` text
<query> -#cno**
```

The tag glob filter above uses a double asterisk to match any string (whose length is zero or more characters) following `cno`. The double asterisk matches **across** tag elements, so the filter will match all of the following:

- `cno`
- `cno.mal`
- `cno.threat.t42`
- `cnoooo.you_get_a_cno.and_you_get_a_cno`

...etc.

Filter the current working set to include any nodes tagged by any third-party reporting organization where the tag contains the string `2017`:

```mdstorm --hide
[ ( file:bytes=( { "sha256": "f0aa64e048ba6e054e31b86ae0dfdaee0dcdab73e324e7bb926c9dccdee63a14" } ) +#rep.vt.cve_2017_11882 ) ( crypto:hash:md5=806fad8aac92164f971c04bb4877c00f +#rep.alienvault.cve20178291 ) ( file:bytes=( { "sha256": "de6389e89062e049423ef018612df0734b94dfd9d9a4f3880ca6b8ff0bbbc4cc" } ) +#rep.malwarebazaar.3p.reversinglabs.document_ole_exploit_cve_2017_11182 ) ] +#rep.*.**2017**
```

``` text
<query> +#rep.*.**2017**
```

The tag glob filter above uses both a single and double asterisk. The single asterisk matches any tag element in the second position; the double asterisk matches any string that includes `2017`, including across dot (`.`) boundaries. The filter will match all of the following:

- `rep.alienvault.cve20178291`
- `rep.malwarebazaar.3p.reversinglabs.document_ole_exploit_cve_2017_11882`
- `rep.vt.cve_2017_0199`
- `rep.acme.2017`

<a id="filter-tag-timestamp"></a>


### Filter Using Tag Timestamp Values

A tag timestamp can be thought of as a specialized "property" of a tag that happens to be a date / time range (interval). You can filter nodes based on tag timestamp values using any comparison operator supported by interval ([ival](storm_ref_type_specific.md#type-ival) types). The time / interval extended operator ( `@=` ) is used most often, but equal to ( `=` ) can also be used to **exactly** match the values in the interval.

See [Filter by Time or Interval (@=)](storm_ref_filter.md#filter-interval) for additional detail on the use of the `@=` operator.

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>* **@=** *\<time\>* \| **(** *\<min_time\>* **,** *\<max_time\>* **)**

Filter the current result set to only include nodes that were associated with anonymous VPN infrastructure (`#cno.infra.anon.vpn`) between December 1, 2023 and January 1, 2024:

```mdstorm --hide
[ ( inet:fqdn=wazn.airservers.org +#cno.infra.anon.vpn=(2023/05/24 23:16:51.423, 2023/12/05 23:12:40.626) ) ( inet:ip=2607:9000:0:85:68a3:75b4:13ab:770a +#cno.infra.anon.vpn=(2023/08/15 00:12:15,2023/12/05 23:12:54) ) ] +#cno.infra.anon.vpn @= ( 2023/12/01, 2024/01/01 )
```

``` text
<query> +#cno.infra.anon.vpn @= ( 2023/12/01, 2024/01/01 )
```

Filter the current working set to only include nodes that were owned / controlled by Threat Cluster 15 (`#cno.threat.t15.own`) as of October 30, 2021:

```mdstorm --hide
[ inet:fqdn=ronthecat.com +#cno.threat.t15.own=(2020/09/12, 2022/09/12) ] +#cno.threat.t15.own @= 2021/10/30
```

``` text
<query> +#cno.threat.t15.own @= 2021/10/30
```

<a id="filter-tag-prop"></a>


### Filter Using Tag Properties

[Tag Properties](analytical_model.md#tag-properties) can be used to provide additional context to tags. Storm supports filtering nodes whose tags have a specific tag property (regardless of the value of the property).

> [!NOTE]
> In many cases, information previously recorded using a tag property is better suited to the use of an [Extended Property](../glossary.md#gloss-extended-prop).

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>* \| \*\***\***:\*\* *\<tagprop\>*

Filter the current working set to only include nodes with a `:_risk` tag property reported by Symantec (`#rep.symantec`):

```mdstorm --hide
[ ( inet:fqdn=woot.com +#rep.symantec:_risk=87 ) ( inet:ip=8.8.8.8 +#rep.domaintools:_risk=42 ) ] +#rep.symantec:_risk
```

``` text
<query> +#rep.symantec:_risk
```

Filter the current working set to include nodes with a `:_risk` tag property associated with any tag:

```mdstorm --hide
[ ( inet:fqdn=woot.com +#rep.symantec:_risk=87 ) ( inet:ip=8.8.8.8 +#rep.domaintools:_risk=42 ) ] +#**:_risk
```

``` text
<query> +#**:_risk
```

> [!TIP]
> When filtering based on the **existence** of a tag property, you can use tag glob syntax (see [Filter by Tag Globs](storm_ref_filter.md#filter-tag-globs)) to specify the associated tags. Filters such as `+#rep.*.*:_risk` or (per the above example) `+#**:_risk` are supported.
>
> When filtering for a specific tag property that appears on **any** tag, either a double asterisk (tag glob, as above) or single asterisk can be used, e.g.: `+#*:_risk`. The single asterisk in this instance is not a tag glob, but a special syntax helper for this specific use case. (That is, because entering `+#*:_risk` instead of `+#**:_risk` is a common user error, Synapse automatically handles this case to "do what you mean".)

<a id="filter-tag-prop-value"></a>


### Filter Using Tag Property Values

Storm supports filtering nodes based on the value of a tag property (similar to filtering by the value of a node property).

You can filter nodes based on tag property values using any comparison operator supported by the property's [Type](../glossary.md#gloss-type). For example, if the tag property is defined as an integer (`int`) type, you can use any comparison operator supported by integers.

> [!NOTE]
> Tag glob syntax (see [Filter by Tag Globs](storm_ref_filter.md#filter-tag-globs)) is **not** supported when filtering based on a tag property value. For example, a filter such as `+#rep.**:_risk>20` will generate a syntax error.

**Syntax:**

*\<query\>* **+** \| **-** **\#** *\<tag\>* **:** *\<tagprop\>* *\<operator\>* *\<pval\>*

Filter the current working set to include nodes with a `:_risk` tag property value of 100 as reported by ESET (`#rep.eset`):

```mdstorm --hide
[ ( inet:fqdn=woot.com +#rep.symantec:_risk=87 ) ( inet:ip=8.8.8.8 +#rep.domaintools:_risk=42 ) ( inet:fqdn=vertex.link +#rep.eset:_risk=100 ) ] +#rep.eset:_risk = 100
```

``` text
<query> +#rep.eset:_risk = 100
```

Filter the current working set to exclude nodes with a `:_risk` property value less than 90 as reported by DomainTools (`#rep.domaintools`):

```mdstorm --hide
[ ( inet:fqdn=woot.com +#rep.symantec:_risk=87 ) (inet:ip=8.8.8.8 +#rep.domaintools:_risk=42 ) ( inet:fqdn=vertex.link +#rep.vertex:_risk=100 ) ] -#rep.domaintools:_risk < 90
```

``` text
<query> -#rep.domaintools:_risk < 90
```

Filter the current working set to include nodes with a `:_risk` property with a value between 45 and 70 as reported by Symantec (`#rep.symantec`):

```mdstorm --hide
[ ( inet:fqdn=woot.com +#rep.symantec:_risk=87 ) ( inet:ip=8.8.8.8 +#rep.domaintools:_risk=42 ) ] +#rep.symantec:_risk *range= ( 45, 70 )
```

``` text
<query> +#rep.symantec:_risk *range= ( 45, 70 )
```

<a id="filter-compound"></a>


## Compound Filters

Storm supports the use of the logical operators **and**, **or**, and **not** (including **and not**) to construct compound filters. You can use parentheses to group portions of the filter statement to indicate order of precedence and clarify logical operations when evaluating the filter.

> [!NOTE]
> - Logical operators must be specified in lower case.
> - Synapse evaluates compound filters **in order from left to right**. Depending on the filter, left-to-right order may differ from the standard Boolean order of operations (**not** then **and** then **or**).
> - Parentheses should be used to logically group portions of the filter statement if necessary to clarify order of operations.

**Syntax:**

*\<query\>* **+** \| **-** **(** *\<filter\>* **and** \| **or** \| **not** \| **and not** ... **)**

**Examples:**

Filter the current working set to only include SHA1 hashes (`crypto:hash:sha1` nodes) or FQDNs (`inet:fqdn` nodes) that ESET associates with Sednit (`#rep.eset.sednit`):

```mdstorm --hide
.created +( ( crypto:hash:sha1 or inet:fqdn ) and #rep.eset.sednit )
```

``` text
<query> +( ( crypto:hash:sha1 or inet:fqdn ) and #rep.eset.sednit )
```

Filter the current working set to include only SHA1 hashes or FQDNs that ESET associates with Sednit and that are **not** sinkholed (`#cno.infra.dns.sink.holed`):

```mdstorm --hide
.created +( ( crypto:hash:sha1 or inet:fqdn ) and ( #rep.eset.sednit and not #cno.infra.dns.sink.holed ) )
```

``` text
<query> +( ( crypto:hash:sha1 or inet:fqdn ) and ( #rep.eset.sednit and not #cno.infra.dns.sink.holed ) )
```

Filter the current working set to only include IP addresses (`inet:ip` nodes) that are on AS2119, AS210558, or AS53667 and are located in Luxembourg:

```mdstorm --hide
[ ( inet:ip=2.58.56.12 :asn=210558 :place:loc=nl ) ( inet:ip=46.195.78.212 :asn=2119 :place:loc=se ) ( inet:ip=104.244.72.4 :asn=53667 :place:loc=lu ) ( inet:ip=37.235.48.29 :asn=9009 :place:loc=pl ) ] +( ( :asn=2119 or :asn=210558 or :asn=53667 ) and :place:loc^=lu )
```

``` text
<query> +( ( inet:ip:asn=2119 or inet:ip:asn=210558 or inet:ip:asn=53667 ) and inet:ip:place:loc^=lu )
```

```mdstorm --hide
inet:ip +( ( :asn=2119 or :asn=210558 or :asn=53667 ) and :place:loc^=lu )
```

``` text
<query> +( ( :asn=2119 or :asn=210558 or :asn=53667 ) and :place:loc^=lu )
```

<a id="filter-subquery"></a>


## Subquery Filters

You can use Storm's subquery syntax ([Storm Reference - Subqueries](storm_ref_subquery.md#storm-ref-subquery)) to create filters. A subquery (enclosed in curly braces ( `{ }` ) ) can be placed within a larger Storm query.

Most filter operations in Storm will modify (reduce) your current set of nodes based on some criteria of the **nodes themselves** (e.g., a node's form, property, or tag).

Subquery filters allow you to filter your **current** set of nodes based on some criteria of **nearby** nodes. You use the subquery filter to effectively "look ahead" at nodes one or more pivots away from your current nodes, and filter your current nodes based on the properties of those "nearby" nodes.

When nodes are passed to a subquery filter, they are evaluated against the filter's criteria:

- Nodes are **excluded** ("consumed", discarded) if they evaluate **false.**
- Nodes are **included** (not "consumed", retained) if they evaluate **true.**

The subquery pivot operation (used to "look ahead" at other nodes) is effectively performed in the background (without navigating away from your current working set), which provides a more powerful and efficent way to filter your data. (The alternative would be to **actually** navigate to the nearby nodes, filter those nodes, and then navigate **back** to the data you are interested in.)

You can optionally use a standard (mathematical) comparison operator with a subquery filter, in order to filter your current set of nodes based on the **number of results** returned by executing the subfilter's Storm query.

Refer to the [Storm Reference - Subqueries](storm_ref_subquery.md#storm-ref-subquery) guide for additional information on subqueries and subquery filters.

**Syntax:**

*\<query\>* **+** \| **-** **{** *\<query\>* **}** \[ *\<standard operator\>* *\<value\>* \]

**Examples:**

Filter the current working set of FQDNs (`inet:fqdn` nodes) to only FQDNs that have resolved to an IP address that Trend Micro associates with Pawn Storm (i.e., an IP address tagged `#rep.trend.pawnstorm`):

```mdstorm --hide
inet:fqdn +{ -> inet:dns:a -> inet:ip +#rep.trend.pawnstorm }
```

``` text
<inet:fqdn> +{ -> inet:dns:a -> inet:ip +#rep.trend.pawnstorm }
```

The subquery filter above takes the inbound `inet:fqdn` nodes and (within the subquery):

- pivots to the associated DNS A records (`inet:dns:a` nodes);
- pivots to the asssociated IP addresses (`inet:ip` nodes);
- checks the IP for the presence of a `#rep.trend.pawnstorm` tag.

The subquery filter returns only those `inet:fqdn` nodes where, if you performed the operations within the subquery, **would** (based on the inclusive filter) result in an `inet:ip` node with a `#rep.trend.pawnstorm` tag.

Filter the current working set of IP addresses (`inet:ip` nodes) to exclude any IP associated with an Autonomous System (AS) whose name starts with `makonix`:

```mdstorm --hide
inet:ip -{ :asn -> inet:asn +:registrant:name ^= makonix }
```

``` text
<inet:ip> -{ :asn -> inet:asn +:registrant:name ^= makonix }
```

The subquery filter above takes the inbound `inet:ip` nodes and (within the subquery):

- pivots to the associated `inet:asn` nodes; and
- checks the `inet:asn` nodes for a `:registrant:name` value that starts with "makonix".

The subquery filter returns only those `inet:ip` nodes where, if you performed the operations within the subquery, **would not** (based on the exclusive filter) result in an `inet:asn` node with a `:name` value starting with "makonix".

> [!TIP]
> See [Embedded Property Syntax](storm_ref_filter.md#embed_prop_syntax) for an alternative way to perform this query.

Filter the current working set of files (`file:bytes` nodes) to include only files that are detected as malicious in ten (10) or more scans (i.e., files that are associated with ten or more `it:av:scan:result` nodes whose `:verdict` property value is `malicious`):

```mdstorm --hide
file:bytes +{ -> it:av:scan:result +:verdict=malicious }>=10
```

``` text
<file:bytes> +{ -> it:av:scan:result +:verdict=malicious }>=10
```

The subquery filter above takes the inbound `file:bytes` nodes and (within the subquery):

- pivots to the associated `it:av:scan:result` nodes; and
- filters the results to include only those nodes whose `it:av:scan:result:verdict` property value is `malicious`; and
- counts the number of resulting `it:av:scan:result` nodes for each file.

The subquery filter returns only those `file:bytes` nodes with 10 or more associated `it:av:scan:result` nodes with a `malicious` verdict.

> [!TIP]
> This is a simplified example. `it:av:scan:result` nodes represent a scan performed at a given point in time; the filter above does not provide any time constraints so will count any / all "malicious" results, regardless of "when" the scan was performed. Results could include files detected as malicious by ten different vendors during a single scan as well as files detected as malicious by only one vendor during ten different scans.

Filter the current working set of x509 certificates (`crypto:x509:cert` nodes) to only include certificates linked to more than one FQDN identity:

```mdstorm --hide
[ ( crypto:x509:cert=3e0016d728b979b7f8fd77a2738047eb :identities:fqdns=(woot.com,) ) ( crypto:x509:cert=0d002397195463d88d188ae67b83de8e :identities:fqdns=(hurr.net, derp.org) ) ] +{ :identities:fqdns -> inet:fqdn }>1
```

``` text
<crypto:x509:cert> +{ :identities:fqdns -> inet:fqdn }>1
```

The subquery filter above takes the inbound `crypto:x509:cert` nodes and (within the subquery):

- uses the `:identities:fqdns` array property to pivot to any associated FQDNs (`inet:fqdn` nodes); and
- counts the number of `inet:fqdn` nodes associated with each certificate.

The subquery filter returns only those `crypto:x509:cert` nodes associated with more than one FQDN.

> [!TIP]
> See [Expression Filters](storm_ref_filter.md#filter-expression) below for an alternative way to perform this query.

<a id="filter-expression"></a>


## Expression Filters

An expression filter is used to downselect your current working set based on the evaluation of a particular expression. Expression filters are useful when:

- you need to compute a value that you want to use for the filter, or
- when you want to filter based on a value that may change (e.g., when using Storm queries that assign variables; see [Storm Reference - Advanced - Variables](storm_adv_vars.md#storm-adv-vars)).

**Syntax:**

*\<query\>* **+** \| **-** **\$(** *\<expression\>* **)**

**Examples:**

Filter the current working set of x509 certificates (`crypto:x509:cert` nodes) to only include certificates linked to more than one FQDN identity:

```mdstorm --hide
[ ( crypto:x509:cert=3e0016d728b979b7f8fd77a2738047eb :identities:fqdns=(woot.com,) ) ( crypto:x509:cert=0d002397195463d88d188ae67b83de8e :identities:fqdns=(hurr.net, derp.org) ) ] $fqdns=:identities:fqdns +$( $fqdns.size() > 1 )
```

``` text
<crypto:x509:cert> $fqdns=:identities:fqdns +$( $fqdns.size() > 1 )
```

This example assigns the list of domains in the `crypto:x509:cert:identities:fqdns` property to the user-defined variable `$fqdns`, computes the number of domains in the list using [stormprims-list-size](../stormtypes_prims.md#stormprims-list-size), and checks to see if the result is greater than 1.

(See the [Storm Library Documentation](../stormtypes.md#stormtypes_index) for additional detail on Storm types and Storm libraries.)

> [!TIP]
> This certificate example is identical to the final example under [Subquery Filters](storm_ref_filter.md#filter-subquery) above, and shows an alternative way to return the same data.
>
> This expression filter is more efficient than the subquery filter because the expression filter simply evaluates the expression ("what is the size of the `:identities:fqdns` array property?"), where the subquery filter needs to pivot to the adjacent nodes in order to evaluate the results. This difference in performance is negligible for small data sets but more pronounced when working with large numbers of nodes.

Filter the current working set of network flows (`inet:flow` nodes) to only include flows where the total number of bytes transferred in the flow between the source (`:client:txbytes`) and destination (`:server:txbytes`) is greater than 100MB (~100,000,000 bytes):

```mdstorm --hide
[ inet:flow=( { "client:txbytes": "60000000", "server:txbytes": "60000000" } ) inet:flow=( { "client:txbytes": "1024", "server:txbytes": "4096" } ) ] +$( :client:txbytes + :server:txbytes >=100000000 )
```

``` text
<inet:flow> +$( :client:txbytes + :server:txbytes >=100000000 )
```

Filter the current set of nodes associated with any threat group or threat cluster (e.g., tagged `#cno.threat.<threat_name>`), to include only those nodes that are attributed to more than one threat (e.g., that have more than one `#cno.threat.<threat_name>` tag):

```mdstorm --hide
[ ( inet:ip=4.4.4.4 +#cno.threat.foo ) ( inet:ip=7.7.7.7 +#cno.threat.hurr +#cno.threat.derp ) ] +$( $node.globtags(cno.threat.*).size() > 1 )
```

``` text
#cno.threat +$( $node.globtags(cno.threat.*).size() > 1 )
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

*\<query\>* \[ **+ \| -** \] **:** *\<prop\>* **::** *\<prop\>* \[ **::** *\<prop\>* ... \]

*\<query\>* \[ **+ \| -** \] **:** *\<prop\>* \[ **::** *\<prop\>* ... \] **::** *\<prop\>* *\<operator\>* *\<pval\>*

> [!NOTE]
> When using embedded property syntax in Storm, the leading colon (before the name of the initial secondary property) is **required** - e.g., `:asn::name`.
>
> When using this syntax in Optic (the Synapse UI) to create an [embed column](/docs/synapse-enterprise-optic/latest/user_interface/userguides/custom_environ.md#display-a-property-from-a-nearby-node-in-a-column-embed-column) in Tabular display mode, the initial colon should be **omitted** - e.g, `asn::name`. Optic effectively prepends the initial colon for you.

**Filter Example:**

The example below illustrates the use of embedded property syntax in a filter expression.

Filter the current working set of IP addresses (`inet:ip` nodes) to exclude any IP associated with an Autonomous System (AS) whose registrant name starts with `makonix`:

```mdstorm --hide
[ inet:ip=185.86.150.67 :asn={[ inet:asn=52173 :registrant:name="makonix, lv" ]} ] -:asn::registrant:name ^= makonix
```

``` text
<inet:ip> -:asn::registrant:name ^= makonix
```

> [!TIP]
> This example is an alternative way to return the same data as the second example under [Subquery Filters](storm_ref_filter.md#filter-subquery) above:
>
> ``` text
> <inet:ip> -{ :asn -> inet:asn +:registrant:name ^= makonix }
> ```

**Variable Assignment Example:**

Embedded property syntax can also be used when assigning variables (see [Storm Reference - Advanced - Variables](storm_adv_vars.md#storm-adv-vars)).

Set the variable `$name` to the registrant name of the Autonomous System (AS) associated with a given IP address:

```mdstorm --hide
inet:ip $name=:asn::registrant:name
```

``` text
<inet:ip> $name=:asn::registrant:name
```

This example uses embedded property syntax to pivot from the inbound `inet:ip` node, to the ASN (`inet:asn` node) associated with the IP's `:asn` property, and assigns the value of the ASN's `:registrant:name` property to the variable `$name`.
