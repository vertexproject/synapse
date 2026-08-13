```mdstorm-setup
```

```mdstorm --hide
$propinfo = ({"doc": "The VirusTotal reputation score."}) $lib.model.ext.addFormProp(file:bytes, _virustotal:reputation, (int, ({})), $propinfo)
```

<a id="storm-ref-lift"></a>

# Storm Reference - Lifting

Lift operations retrieve a set of nodes from Synapse's knowledge graph based on the criteria you specify. All lift operations are retrieval operations, but they can be broken down into kinds of lifts based on the particular criteria, comparison operator, or special handler used to perform the lift:

- [Lift by Form](storm_ref_lift.md#lift-form)
- [Lift by Property](storm_ref_lift.md#lift-prop)
- [Lift by Property Value - Standard Comparison Operators](storm_ref_lift.md#lift-prop-standard)
- [Lift by Property Value - Extended Comparison Operators](storm_ref_lift.md#lift-prop-extended)
- [Tag Lifts](storm_ref_lift.md#tag-lifts)

In addition, the ``reverse`` keyword and the "try" operator can each be used with lift operations to modify their behavior:

- ["reverse" Keyword](storm_ref_lift.md#lift-reverse)
- ["Try" Operator](storm_ref_lift.md#lift-try)

In the examples below, we only show the Storm query by default (not the resulting nodes) in order to focus on how to write a particular kind of query. Where displaying the results helps to illustrate some aspect of a query's behavior, we include a second example to do so.

> [!TIP]
> Most user interactions with Synapse start when you **lift** the initial data (nodes) you want to work with. There is no "show me all the data" command where you can then drill down to find the data you want. So knowing how to specify the data you want by creating a lift query in Storm is essential.
>
> (Technically, you can lift **all** nodes in Synapse with the Storm query ``.created``, because every node in Synapse has a ``.created`` property. But starting by displaying **all** nodes is impractical for all but the smallest Cortexes.)  
>
> If you are new to Storm, you can use the [Optic UI](/docs/synapse-enterprise-optic/latest/index.md) with the [Storm Query Bar](/docs/synapse-enterprise-optic/latest/user_interface/userguides/quick_tour.md#storm-query-bar-query-mode-selector) in **Lookup mode** (vs. Storm mode). Lookup mode allows you to lift nodes by entering search keywords or common indicators (such as hashes or IPs) without using Storm.

See [Storm Reference - Document Syntax Conventions](storm_ref_syntax.md#storm-ref-syntax) for an explanation of the syntax format used below.

See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details on special syntax or handling for specific data types.

<a id="lift-form"></a>

## Lift by Form

**Lift by form** operations return all nodes of that form in Synapse - for example, all IP addresses (`inet:ip`) or all threat clusters (`risk:threat`). Lift by form includes several variations:

- The wildcard (asterisk) character ( `*` ) can be used to lift all nodes of all forms that match a partial form name / namespace.
- If a form implements an [interface](../glossary.md#gloss-interface), you can use the interface name to lift all nodes of all forms that implement the interface.
- If a form makes use of [form inheritance](../glossary.md#gloss-form-inheritance), you can use the name of a parent form to lift all nodes of the parent form and any form that extends the parent.

> [!TIP]
> In a production instance of Synapse, lifting **all** nodes of a commonly used form, interface, or parent form may return thousands or tens of thousands of nodes. Lifting by form (including its variations) can be used with the Storm [limit](storm_ref_cmd.md#storm-limit) command to return only a specified number of nodes. For example:
>
> `inet:ip | limit 10`
>
> This type of query is useful for viewing a subset of sample data for a particular form.

<a id="lift-form-name"></a>

### Lift by Form Name

A **lift by form name** operation returns all nodes for the specified [form](data_model.md#data-form). This type of lift requires the name of the form whose nodes you want to lift.

**Syntax**

*\<form\>*

**Examples**

Lift all FQDNs (`inet:fqdn` nodes):

```mdstorm --hide
[ inet:fqdn=woot.com inet:fqdn=vertex.link inet:fqdn=google.com ]
```

```mdstorm --hide
inet:fqdn
```

``` text
inet:fqdn
```

Lift all nodes representing articles (`doc:report` nodes):

```mdstorm --hide
[ doc:report=( { "publisher:name": "eset", "published": "2016/10/20", "title": "dissection of sednit espionage group" } ) doc:report=( { "publisher:name": "trend micro", "published": "2023/09/18", "title": "earth lusca employs new linux backdoor, uses cobalt strike for lateral movement" } ) ]
```

```mdstorm --hide
doc:report
```

``` text
doc:report
```

<a id="lift-form-wildcard"></a>

### Lift by Form Name - Wildcard

You can use the wildcard (asterisk) character ( `*` ) to specify all forms that match a partial form name. Use of the wildcard is **not** limited to form namespace boundaries.

**Syntax**

*\<partial_form_name\>* **\***

**Examples**

Lift all DNS A (`inet:dns:a`) and DNS AAAA (`inet:dns:aaaa`) nodes:

```mdstorm --hide
[ inet:dns:a=( woot.com, 1.1.1.1 ) inet:dns:aaaa=( woot.com, 2600:1419:9c00:283::356e )  ]
```

``` text
inet:dns:a*
```

```mdstorm
inet:dns:a*
```

Lift all hash nodes (e.g., `crypto:hash:md5`, `crypto:hash:sha256`, etc.):

```mdstorm --hide
[ crypto:hash:md5=cf30b7550f04a9372c3257c9b5cff3e9 crypto:hash:sha1=04301b59c6eb71db2f701086b617a98c6e026872 crypto:hash:ssdeep=384:XgUIheHmcKKkBIGBGHEBZrK8gFJNFpmX:Q8mIkAw+lFJnsX ]
```

``` text
crypto:hash:*
```

```mdstorm
crypto:hash:*
```

**Note**: cryptographic hashes in Synapse implement the `crypto:hash` interface, and can alternatively be lifted using the [interface name](../glossary.md#gloss-interface).

**Usage Notes**

- The wildcard character ( `*` ) can only be used to match literal form names. It cannot be used to match interface names or when lifting by [parent form](../glossary.md#gloss-form-inheritance) with the intent to also lift extended forms (the wildcard will match form names only; it has no awareness of form inheritance).
- The wildcard can only be used at the end of the partial form name match. It cannot be used at the beginning or in the middle of the form name. For example, the following are both **invalid**:
  
``` text
*:header
```
  
``` text
it:exec:*:add
```
  
- The wildcard cannot be used to match property names. For example, `entity:contact` is a form that has multiple   `:place` secondary properties (e.g., `:place:name`, `:place:loc`). The following is **invalid** because it   tries to match a partial property name:
  
``` text
entity:contact:place:*
```

<a id="lift-form-interface"></a>

### Lift Form by Interface

You can use the name of any [interface](../glossary.md#gloss-interface) to lift all nodes of all forms that implement that interface.

**Syntax**

*\<interface\>*

**Examples**

Lift all hash nodes (all nodes of all forms that implement the `crypto:hash` interface):

``` text
crypto:hash
```

```mdstorm
crypto:hash
```

Lift all host event nodes (all nodes of all forms that implement the `it:host:event` interface):

```mdstorm --hide
[ it:exec:file:add=( { "time": "2026/04/23 05:44:27", "path": "c:\windows\system32\myfile.exe" } ) it:exec:fetch=( { "time": "2026/06/09 14:16:03", "url": "https://vertex.link/" } ) ]
```

``` text
it:host:event
```
```mdstorm
it:host:event
```

<a id="lift-form-parent"></a>

### Lift by Parent Form

Forms can make use of [form inheritance](../glossary.md#gloss-form-inheritance). Similar to class inheritance in object-oriented programming, Synapse allows you to define a **parent form** and create more specific forms that **inherit** the properties of the parent (and optionally extend the parent with additional properties).

You can use the name of a parent form to lift all nodes of the parent form, and all nodes of all forms that extend the parent.

**Syntax**

*\<parent_form\>*

> [!TIP]
> Where *\<form\>* is used in a query syntax example, it refers to **any** form (including parent forms, or forms that extend a parent form). We use *\<parent_form\>* here to emphasize this particular use case.

**Examples**

Lift all of the `it:host:account` nodes and all nodes of all forms that extend `it:host:account`:

```mdstorm --hide
$host1={ [ it:host=( { "name": "ozzie's iphone", "os:name": "iOS 26.5.2"} ) ] } $host2={ [ it:host=( { "name": "ozzie-laptop", "os:name": "Ubuntu 24.04" } ) ] } $host3={ [ it:host=( { "name": "DESKTOP-8F2NL0R", "os:name": "Microsoft Windows 11 Home" } ) ] } [ it:host:account=( { "username": "ozzie", "host": $host1 } ) it:host:posix:account=( { "username": "ozzie", "host": $host2, "home": "/home/ozzie", "shell": "/bin/bash" } ) it:host:windows:account=( { "username": "ron the cat", "host": $host3, "id": "S-1-5-21-4772941793-982498634-1278416829-1074", "home": "c:\\users\\ron the cat" } ) ]
```

``` text
it:host:account
```

```mdstorm
it:host:account
```

<a id="lift-prop"></a>

## Lift by Property

A **lift by property** operation returns all nodes that **have** the specified [property](data_model.md#data-prop) set, regardless of the property value. Property lifts work the same way regardless of the kind of property (e.g., secondary property, virtual property, meta property, extended property, etc.)

In most cases, lifting by property requires the full name (i.e., the combined form and property name) of the property you want to use to lift the nodes. Meta properties are the exception, where the form name is optional (see below).

You can also leverage [interfaces](../glossary.md#gloss-interface) and [form inheritance](../glossary.md#gloss-form-inheritance) to lift by property across multiple related forms.

<a id="lift-prop-second"></a>

### Lift by Secondary Property

These examples assume a secondary property delimited with a colon ( **:** ). Examples for meta properties, virtual properties, and extended properties are described below.

**Syntax**

*\<form\>* **:** *\<prop\>*

**Examples**

Lift the IP address nodes that have an Autonomous System number (`:asn`) property:

```mdstorm --hide
[ ( inet:ip=41.164.23.42 :asn=36937 ) ( inet:ip=155.254.9.3 :asn=19754 ) ]
```

```mdstorm --hide
inet:ip:asn
```

``` text
inet:ip:asn
```

Lift the threat clusters (`risk:threat` nodes) that have an associated place name:

```mdstorm --hide
[ risk:threat=( { "name": "Storm-1125", "reporter:name": "Microsoft", "$props": { "place:name": "Belarus" } } ) risk:threat=( { "name": "COSMIC WOLF", "reporter:name": "Crowdstrike", "$props": { "place:name": "Türkiye" } } ) risk:threat=( { "name": "PLATINUM COLONY", "reporter:name": "Sophos", "$props": { "place:name": "United States" } } ) ]
```

``` text
risk:threat:place:name
```

```mdstorm
risk:threat:place:name
```

<a id="lift-prop-virt"></a>

### Lift by Virtual Property

[Virtual properties](data_model.md#virtual-property) are declared as part of a [type](data_model.md#type) and may be present on both primary (forms) and secondary properties.

**Syntax**

*\<form\>* \[ **:** *\<prop\>* \] **.** *\<prop\>*

**Examples**

Lift the file paths that include a file extension (`.ext`):

```mdstorm --hide
[ file:path=c:\windows\system32 file:path=/home/ozzie/Documents/myfile.txt file:path='c:\users\ron the cat\snack_budget.xlsx' ]
```

``` text
file:path.ext
```

```mdstorm
file:path.ext
```

Lift the network flows (`inet:flow`) where the client has an associated port (`.port`):

```mdstorm --hide
$client1={ [ inet:client=tcp://1.2.3.4 ] } $client2={ [ inet:client=tcp://5.6.7.8:27342 ] } $server1={ [ inet:server=tcp://23.76.57.252:443 ] } [ inet:flow=( { "client": $client1, "server": $server1 } ) inet:flow=( { "client": $client2, "server": $server1 } ) ]
```

``` text
inet:flow:client.port
```

```mdstorm
inet:flow:client.port
```

<a id="lift-prop-meta"></a>

### Lift by Meta Property

[Meta properties](data_model.md#meta-property) apply to all forms and are automatically populated. Synapse uses two meta properties:

- `.created`: a time which represents the date and time a node was created in Synapse.
- `.updated`: a time which represents the date and time a node was last modified in Synapse.

**Syntax**

\[ *\<form\>* \] **.** *\<prop\>*

**Examples**

Lift all nodes in Synapse:

```mdstorm --hide
.created
```

``` text
.created
```

> [!TIP]
> Both the `.created` (and `.updated`) properties are automatically set for every node when it is first added to Synapse. Because these properties are present on all nodes, lifting by either property effectively lifts every node in Synapse (technically, every node in the current [view](../glossary.md#gloss-view)).

Lift all FQDN nodes in Synapse:

```mdstorm --hide
inet:fqdn.created
```

``` text
inet:fqdn.created
```

> [!TIP]
> Because all `inet:fqdn` nodes have a `.created` property, you can get the same results by simply lifting all FQDNs by form (e.g., `inet:fqdn`).
> 
> Lifting by `.created` (or `.updated`) can be used with the `reverse` keyword (and optionally the [limit](storm_ref_cmd.md#limit) command) to lift the most recently created (or updated) nodes (of any kind), or nodes of a specific form. See the ["reverse" keyword](storm_ref_lift.md#lift-reverse) section for details.

<a id="lift-prop-extend"></a>

### Lift by Extended Property

Synapse's data model can be extended with custom forms, properties, or edges. To avoid potential namespace collisions with properties in the base data model, extended property names must begin with an underscore. See the section on [extending the data model](data_model.md#extending-the-data-model) for details.

**Syntax**

*\<form\>* **:\_** *\<prop\>*

**Examples**

Lift the files (`file:bytes` nodes) that have a VirusTotal reputation extended property (`:_virustotal:reputation`):

```mdstorm --hide
[ file:bytes=( { "sha256": "87b7e57140e790b6602c461472ddc07abf66d07a3f534cdf293d4b73922406fe" } ) :size=188928 :mime='application/vnd.microsoft.portable-executable' :_virustotal:reputation=-427 ]
```

```mdstorm --hide
file:bytes:_virustotal:reputation
```

``` text
file:bytes:_virustotal:reputation
```

> [!NOTE]
> The `:_virustotal:reputation` extended property is added to the Synapse data model by the [Synapse-VirusTotal](/docs/synapse-virustotal/latest/index.md) Power-Up.


<a id="lift-prop-interface"></a>

### Lift by Interface Property

If a form implements an [interface](../glossary.md#gloss-interface) that defines a set or properties, you can lift all nodes of all forms that implement the interface and have that property by specifying the full name of the interface and its property.

**Syntax**

*\<interface\>* **:** | **.** | **:_** *\<prop\>*

**Examples**

Lift the host event nodes (all nodes of all forms that implement the `it:host:event` interface) that have a `:time` property:

```mdstorm --hide
[ it:exec:file:add=( { "time": "2026/04/23 05:44:27", "path": "c:\windows\system32\myfile.exe" } ) it:exec:fetch=( { "time": "2026/06/09 14:16:03", "url": "https://vertex.link/" } ) ]
```

``` text
it:host:event:time
```

```mdstorm
it:host:event:time
```

Lift all "authorable" nodes (all nodes of all forms that implement the `doc:authorable` interface) that have a `:creator:name` property:

```mdstorm --hide
[ doc:report=( { "creator:name": "ozzie", "title": "Finally Some Good News", "published": "2026/02/07", "publisher:name": "vertex" } ) doc:resume=( { "creator:name": "ron the cat", "created": "2027/04/12", "summary": "Very food-motivated, will work hard for snacks." } ) it:app:yara:rule=( { "creator:name": "ozzie", "created": "2025/12/22", "text": "Here is some detection logic." } ) ]
```

``` text
doc:authorable:creator:name
```

```mdstorm
doc:authorable:creator:name
```

<a id="lift-prop-parent"></a>

### Lift By Parent Form Property

Where forms make use of [inheritance](../glossary.md#gloss-form-inheritance), lifting by a parent form property will lift all nodes of the parent form and all nodes of all forms that extend the parent that have that property.

**Syntax**

*\<parent_form\>* **:** | **.** | **:_** *\<prop\>*

**Examples**

Lift the `it:host:account` nodes and all nodes of all forms that extend `it:host:account` that have a `:home`
property:

```mdstorm --hide
$host1={ [ it:host=( { "name": "ozzie's iphone", "os:name": "iOS 26.5.2"} ) ] } $host2={ [ it:host=( { "name": "ozzie-laptop", "os:name": "Ubuntu 24.04" } ) ] } $host3={ [ it:host=( { "name": "DESKTOP-8F2NL0R", "os:name": "Microsoft Windows 11 Home" } ) ] } [ it:host:account=( { "username": "ozzie", "host": $host1 } ) it:host:posix:account=( { "username": "ozzie", "host": $host2, "home": "/home/ozzie", "shell": "/bin/bash" } ) it:host:windows:account=( { "username": "ron the cat", "host": $host3, "id": "S-1-5-21-4772941793-982498634-1278416829-1074", "home": "c:\\users\\ron the cat" } ) ]
```

``` text
it:host:account:home
```

```mdstorm
it:host:account:home
```

<a id="lift-prop-standard"></a>

## Lift by Property Value - Standard Comparison Operators

A **lift by property value** operation returns the node(s) whose property matches the specified value. This type of lift requires:

- the form name or full property name (i.e., the combined form and property name) that you will use to lift the node(s);
- a [comparison operator](../glossary.md#gloss-comp-operator) to specify how the property value should be evaluated; and
- the property value.

A lift by property value can be performed using any kind of property (primary, secondary, virtual, meta, extended, etc.). You can also leverage [interfaces](../glossary.md#gloss-interface) and [form inheritance](../glossary.md#gloss-form-inheritance) to lift by property value across multiple related forms.

In Synapse, we define **standard comparison operators** as the following set of operators:

- equal to ( `=` )
- less than ( `<` )
- greater than ( `>` )
- less than or equal to ( `<=` )
- greater than or equal to ( `>=` )

The ["try" operator](storm_ref_lift.md#lift-try) ( `?=` ) can optionally be used in place of the standard equal to operator ( `=` ). Use of the try operator is generally not required for interactive Storm queries, but may be useful for more complex Storm queries (such as automation or Storm-based ingest queries).

The most commonly used standard comparison operator is the equal to ( `=` ) operator. Comparison operators that expect a **quantity** (i.e., the inequality symbols `<`, `>`, `<=`, and `>=`) can only be used with properties whose type supports the comparison (e.g., integers, dates/times, etc.)

> [!TIP]
> IP addresses (`inet:ip` nodes) are stored as their decimal integer equivalents (even though they are displayed in human friendly format), and can be used with the various inequality operators:
>
> ``` text
> inet:ip<192.168.0.0
> ```
>
> Or:
>
> ``` text
> inet:ip >=2000::1
> ```
>

<a id="lift-prop-std-primary"></a>

### Lift by Primary Property Value

**Syntax**

*\<form\>* *\<operator\>* *\<valu\>*

**Examples**

Lift the FQDN `vertex.link`:

```mdstorm --hide
[ inet:fqdn=vertex.link ]
```

```mdstorm --hide
inet:fqdn=vertex.link
```

``` text
inet:fqdn=vertex.link
```

Lift the DNS A record showing that domain `woot.com` resolved to IP `1.2.3.4`:

```mdstorm --hide
[ inet:dns:a=(woot.com, 1.2.3.4 ) ]
```

```mdstorm --hide
inet:dns:a=(woot.com, 1.2.3.4)
```

``` text
inet:dns:a=(woot.com, 1.2.3.4)
```

Lift the organization whose primary property matches the specified `guid` value:

```mdstorm --hide
[ ou:org=4b0c2c5671874922ce001d69215d032f ]
```

```mdstorm --hide
ou:org=4b0c2c5671874922ce001d69215d032f
```

``` text
ou:org=4b0c2c5671874922ce001d69215d032f
```

<a id="lift-prop-std-secondary"></a>

### Lift by Secondary Property Value

**Syntax**

*\<form\>* **:** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples**

Lift the organization (`ou:org` node) with the name `the vertex project`:

```mdstorm --hide
[ ou:org=( { "name": "The Vertex Project" } ) ]
```

```mdstorm --hide
ou:org:name='the vertex project'
```

``` text
ou:org:name='the vertex project'
```

Lift the DNS A records for the FQDN `hugesoft.org`:

```mdstorm --hide
[ inet:dns:a=(hugesoft.org, 69.195.129.72) inet:dns:a=(hugesoft.org, 103.224.212.219) ]
```

```mdstorm --hide
inet:dns:a:fqdn=hugesoft.org
```

``` text
inet:dns:a:fqdn=hugesoft.org
```

Lift the PE (portable executable) file metadata nodes (`file:mime:pe`) with a compiled time of `1992-06-19 22:22:17`:

```mdstorm --hide
$file1={ [ file:bytes=( { "sha256": "d7c12acb306b5100a5497586942b68a8f6d5deb353083da594caba2523c3171f" } ) ] } $file2={ [ file:bytes=( { "sha256": "54ebdea80d30660f1d7be0b71bc3eb04189ef2036cdbba24d60f474547d3516a" } ) ] }  [ file:mime:pe=( { "file": $file1, "compiled": "1992-06-19T22:22:17Z" } ) file:mime:pe=( { "file": $file2, "compiled": "1992-06-19T22:22:17Z" } ) ]
```

```mdstorm --hide
file:mime:pe:compiled='1992/06/19 22:22:17'
```

``` text
file:mime:pe:compiled='1992/06/19 22:22:17'
```

Lift the file with the specified MD5 hash:

```mdstorm --hide
[ file:bytes=( { "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "$props": { "md5": "d41d8cd98f00b204e9800998ecf8427e" } } ) ]
```

```mdstorm --hide
file:bytes:md5=d41d8cd98f00b204e9800998ecf8427e
```

``` text
file:bytes:md5=d41d8cd98f00b204e9800998ecf8427e
```

Lift all reports that were published during June 2026:

```mdstorm --hide
[ doc:report=( { "publisher:name": "Microsoft", "title": "A Report by Microsoft", "published": "2026/06/27" } ) doc:report=( { "publisher:name": "SentinelOne", "title": "A Different Report by SentinelOne", "published": "2026/07/15" } ) ]
```

```mdstorm --hide
doc:report:published>=202606
```

``` text
doc:report:published=202606*
```

Lift the reports that were published on or after June 1, 2026:

```mdstorm --hide
doc:report:published>=2026/06/01
```

``` text
doc:report:published>=2026/06/01
```

Lift the nodes representing political races (`pol:race`) where voter turnout was greater than 10,000:

```mdstorm --hide
$election={ [ pol:election=( { "name": "Derpistan 2026 Regional Election", "period": "(2025/11/04, 2025/11/05)" } ) ] } $office1={ [ pol:office=( { "title": "Bureaucrat-in-Chief" } ) ] } $office2={ [ pol:office=( { "title": "Head Supervisory Supervisor" } ) ] } [ pol:race=( { "election": $election, "office": $office1, "$props": { "turnout": "11279" } } ) pol:race=( { "election": $election, "office": $office2, "$props": { "turnout": "9734" } } ) ]
```

```mdstorm --hide
pol:race:turnout>10000
```

``` text
pol:race:turnout>10000
```

**Usage Notes:**

- When lifting nodes by secondary property value where the value is a `time` (date / time):
  - You can use time values of any acceptable resolution (e.g., from `2026` to `2026/07/27 18:23:46.935216`). Lower-resolution times are **zero-filled** by default, so `2026` is interpreted as `2026/01/01 00:00:00.000000`.
  - You can use a wildcard ( `*` ) to specify any time that matches the wildcard expression. For example, `2026/05*` (or `202605*`) is interpreted as "any date/time during May 2026". 

See the type-specific documentation for [time](storm_ref_type_specific.md#type-time) types for a detailed discussion of these behaviors.

<a id="lift-prop-std-virt"></a>

### Lift by Virtual Property Value

**Syntax**

*\<form\>* \[ **:** *\<prop\>* \] **.** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples**

Lift all the servers listening on port 22:

```mdstorm --hide
[ inet:server=tcp://152.228.204.80:22 ]
```

```mdstorm --hide
inet:server.port=22
```

``` text
inet:server.port=22
```

Lift all the compromises (``risk:compromise`` nodes) where the associated ``:actor`` is an organization:

```mdstorm --hide
$actor1={ [ ou:org=( { "name": "Military Unit 26165 (GRU)" } ) ] } $actor2={ [ risk:threat=( { "name": "FANCY BEAR", "reporter:name": "CrowdStrike" } ) ] } [ risk:compromise=( { "name": "very bad compromise", "reporter:name": "vertex", "$props": { "actor": $actor1 } } ) risk:compromise=( { "name": "slightly less bad compromise", "reporter:name": "CrowdStrike", "$props": { "actor": $actor2 } } ) ]
```

``` text
risk:compromise:actor.type=ou:org
```

```mdstorm
risk:compromise:actor.type=ou:org
```

Lift all of the email messages (``inet:email:message`` nodes) with three or more attachments:

```mdstorm --hide
$file1={ [ file:bytes=( { "sha256": "026e9e1cb1a9c2bc0631726cacdb208e704235666042543e766fbd4555bd6950" } ) ] } $file2={ [ file:bytes=( { "sha256": "f78ee3005ca9f0e78a9dd136fc69afe7c06d69d1fc6218bc9e7eb3adec045977" } ) ] } $file3={ [ file:bytes=( { "sha256": "7dc1a836449baa108bdbf9a269e6aeef78d84915a5967eeffe19fda9c4208d13" } ) ] } $attach1={ [file:attachment=( { "file": $file1, "path": "fake_invoice.pdf" } ) ] } $attach2={ [file:attachment=( { "file": $file1, "path": "my_resume.docx" } ) ] } $attach3={ [file:attachment=( { "file": $file1, "path": "not_malware.exe" } ) ] } [ inet:email:message=( { "date": "2026/04/01", "from": "ron_the_cat@proton.me", "to": "ozzie@gmail.com", "subject": "Plz open all the attachments kthx" } ) :attachments=( $attach1, $attach2, $attach3 ) ]
```

```mdstorm --hide
inet:email:message:attachments.size>=3
```

``` text
inet:email:message:attachments.size>=3
```
  
<a id="lift-prop-std-meta"></a>

### Lift by Meta Property Value

Synapse has two built-in meta properties:

- `.created` a time which represents the date and time a node was created in Synapse.
- `.updated` a time which represents the date and time a node was last modified in Synapse.

Both values are set when a node is created. The `.updated` value is modified whenever any change is made to the node.

Times (date / time values) are stored as integers (epoch microseconds) in Synapse and can be lifted using any standard comparison operator.

The [Lift by Time or Interval (@=)](storm_ref_lift.md#lift-interval) and [Lift by Range (*range=)](storm_ref_lift.md#lift-range) extended comparison operators provide additional flexibility when lifting by times and intervals.

See also the [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) sections of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for additional details on working with times and intervals in Synapse.

**Syntax**

\[ *\<form\>* \] **.** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples**

Lift all nodes created after June 1, 2026:

```mdstorm --hide
.created>=2026/06/01
```

``` text
.created>=2026/06/01
```

Lift all organizations updated during the hour of 1500 (e.g., between 1500 and 1600) on February 20, 2026:

```mdstorm --hide
ou:org.updated=2026022015*
```

``` text
ou:org.updated=2026022015*
```

<a id="lift-prop-std-extended"></a>

### Lift by Extended Property Value

When lifting by extended property value, you can use any standard comparison operator supported by the property's type. For example, if the extended property is a string, only the equal to ( `=` ) standard operator is supported. If the extended property is an integer, any of the standard operators can be used.

**Syntax**

*\<form\>* **:\_** *\<prop\>* *\<operator\>* *\<pval\>*

**Example**

Lift the files (`file:bytes` nodes) with a VirusTotal reputation score (`:_virustotal:reputation` extended property) less than -50:

```mdstorm --hide
[ file:bytes=( { "sha256": "87b7e57140e790b6602c461472ddc07abf66d07a3f534cdf293d4b73922406fe" } ) :size=188928 :mime='application/vnd.microsoft.portable-executable' :_virustotal:reputation=-427 ]
```

```mdstorm --hide
file:bytes:_virustotal:reputation<-50
```

``` text
file:bytes:_virustotal:reputation<-50
```

<a id="lift-prop-std-interface"></a>

### Lift by Interface Property Value

If a form implements an [interface](../glossary.md#gloss-interface) that defines a set of properties, you can lift all nodes of all forms with a specific value for that property by using the name of the interface.

> [!TIP]
> Synapse returns results in lexical order (sorted, ascending to descending) based on the way the queried property is indexed. When using an interface to lift by secondary property, Synapse performs the lifts for each form in parallel, and yields the results in order. See the ["reverse" Keyword](storm_ref_lift.md#lift-reverse) section for additional discussion of this concept.

**Syntax**

*\<interface\>* **:** | **.** | **:_** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples**

Lift all "authorable" nodes (all nodes of all forms that implement the `doc:authorable` interface) where the `:creator:name` is `ozzie`:

```mdstorm --hide
[ doc:report=( { "creator:name": "ozzie", "title": "Finally Some Good News", "published": "2026/02/07", "publisher:name": "vertex" } ) doc:resume=( { "creator:name": "ron the cat", "created": "2027/04/12", "summary": "Very food-motivated, will work hard for snacks." } ) it:app:yara:rule=( { "creator:name": "ozzie", "created": "2025/12/22", "text": "Here is some detection logic." } ) ]
```

``` text
doc:authorable:creator:name=ozzie
```

```mdstorm
doc:authorable:creator:name=ozzie
```

Lift the host event nodes (all nodes of all forms that implement the `it:host:event` interface) associated with the host name `ron-pc`:

```mdstorm --hide
$host4 = { [ it:host=( { "name": "ron-pc", "os:name": "Microsoft Windows 11 Home" } ) ] } [ it:exec:file:add=( { "host": $host4, "time": "2026/03/17 02:44:17", "path": "c:\\users\\ron the cat\\myfile.txt" } ) it:exec:fetch=( { "host": $host4, "time": "2026/05/27 23:11:42", "url": "https://www.allthesnacks.com/" } ) ]
```

``` text
it:host:event:host={ it:host:name=ron-pc }
```

```mdstorm
it:host:event:host={ it:host:name=ron-pc }
```

> [!TIP]
> The `:host` property is a guid value (the guid of the associated `it:host` node). The example above uses a [subquery](../glossary.md#gloss-subquery) to refer to the host using a Storm query to lift the node (i.e., the `it:host` node whose `:name` is `ron-pc`) instead of specifying the guid value directly. Subqueries are a useful way to work with guid forms by referencing nodes using more human-friendly secondary property values. See [Using Subqueries to Reference Nodes](storm_ref_subquery.md#subquery-ref-nodes) for a more detailed discussion.
>
> Alternatively, you can use [embedded property syntax](storm_ref_filter.md#embed_prop_syntax) to refer to the name of the host:
>
> ```text
> it:host:event:host::name=ron-pc
> ```
> 

<a id="lift-prop-std-parent"></a>

### Lift by Parent Form Property Value

Where forms make use of [inheritance](../glossary.md#gloss-form-inheritance), lifting by a parent form property value will lift all nodes of the parent form and all nodes of all forms that extend the parent that have that property value.

**Syntax**

*\<parent_form\>* **:** | **.** | **:_** *\<prop\>* *\<operator\>* *\<pval\>*

**Examples**

Lift every technique or mitigation reported by MITRE (the `meta:technique` form is extended by the `risk:mitigation` form):

```mdstorm --hide 
[ meta:technique=( { "id": "T1003.001", "reporter:name": "mitre", "$props": { "name": "LSASS memory (enterprise)", "desc": "Adversaries may attempt to access credential material stored in the process memory of the Local Security Authority Subsystem Service (LSASS)." } } ) risk:mitigation=( { "id": "M1043", "reporter:name": "mitre", "$props": { "name": "credential access protection (enterprise)", "desc": "Credential Access Protection focuses on implementing measures to prevent adversaries from obtaining credentials, such as passwords, hashes, tokens, or keys, that could be used for unauthorized access." } } ) ]
```

``` text
meta:technique:reporter:name=mitre
```

```mdstorm
meta:technique:reporter:name=mitre
```

Lift every stored file entry node with the specified file path:

```mdstorm --hide
$host4 = { [ it:host=( { "name": "ron-pc", "os:name": "Microsoft Windows 11 Home" } ) ] } [ file:system:entry=( { "host": $host4, "path": "c:\windows\system32\\\\fonts\cmd.exe", "created": "2026/06/22 09:25:14" } ) file:mime:rar:entry=( { "path": "c:\windows\system32\\\\fonts\cmd.exe", "created": "2026/06/20 13:07:46" } ) ]
```

``` text
file:stored:entry:path=c:\windows\system32\fonts\cmd.exe
```

```mdstorm
file:stored:entry:path=c:\windows\system32\fonts\cmd.exe
```

The stored file entry (`file:stored:entry`) parent form represents a file (`file:bytes`) stored in a specific location, with optional associated timestamps (e.g., `:created`, `:accessed`, etc.). It is extended by forms including `file:system:entry` (a file on a host file system) and archive files such as `file:archive:entry` or `file:mime:rar:entry`.

<a id="lift-prop-extended"></a>

## Lift by Property Value - Extended Comparison Operators

Storm supports a set of extended comparison operators (comparators) for specialized lift operations.

- [Lift by Regular Expression (~=)](storm_ref_lift.md#lift-regex)
- [Lift by Prefix (^=)](storm_ref_lift.md#lift-prefix)
- [Lift by Time or Interval (@=)](storm_ref_lift.md#lift-interval)
- [Lift by Range (\*range=)](storm_ref_lift.md#lift-range)
- [Lift by Set Membership (\*in=)](storm_ref_lift.md#lift-set)
- [Lift by Proximity (\*near=)](storm_ref_lift.md#lift-proximity)
- [Lift by (Arrays) (\*\[ \])](storm_ref_lift.md#lift-by-arrays)

Just as with standard comparison operators, lifting by property value with extended comparison operators requires:

- the form name or full property name (i.e., the combined form and property name) that you will use to lift the node(s);
- a [comparison operator](../glossary.md#gloss-comp-operator) to specify how the property value should be evaluated; and
- the property value.

A lift by property value using extended comparison operators can be performed using any kind of property (primary, secondary, virtual, meta, extended, etc.), as long as the property's [type](../glossary.md#gloss-type) is appropriate for the comparison used.

You can also leverage [interfaces](../glossary.md#gloss-interface) and [form inheritance](../glossary.md#gloss-form-inheritance) to lift by property value across multiple related forms. See the sections on [lift by interface property value](storm_ref_lift.md#lift-prop-std-interface) and [lift by parent form property value](storm_ref_lift.md#lift-prop-std-parent) above for examples. 

<a id="lift-regex"></a>

### Lift by Regular Expression (~=)

The extended comparator `~=` is used to lift nodes based on Perl Compatible Regular Expressions (PCRE).

> [!NOTE]
> **Lifting** nodes based on regular expression is a **brute force** operation and therefore inefficient. For performance purposes, we strongly recommend that you lift your initial working set using some other criteria, and then **filter** by regular expression (which is more performant) if needed.
>
> [Lift by Prefix (^=)](storm_ref_lift.md#lift-prefix) can be used to match the **beginning** of string-based properties as another more efficient alternative to lifting by regular expression.

**Syntax**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **~=** *\<regex\>*

*\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **~=** *\<regex\>*

**Examples**

Lift the reports (`doc:report` nodes) whose title includes the string `sandstorm`:

```mdstorm --hide
[ doc:report=( { "publisher:name": "microsoft", "title": "peach sandstorm password spray campaigns enable intelligence collection at high-value targets", "published": "2023/09/14" } ) doc:report=( { "publisher:name": "microsoft", "title": "new ttps observed in mint sandstorm campaign targeting high-profile individuals at universities and research orgs", "published": "2024/01/17" } ) ]
```

```mdstorm --hide
doc:report:title~=sandstorm
```

``` text
doc:report:title~=sandstorm
```

Lift the organizations (`ou:org` nodes) whose name contains a string that starts with `v`, followed by 0 or more characters, followed by `x`:

```mdstorm --hide
[ ou:org=( { "name": "Vertex" } ) ou:org=( { "name": "Vx Underground" } ) ]
```

``` text
ou:org:name~='^v.*x'
```

```mdstorm
ou:org:name~='^v.*x'
```

<a id="lift-prefix"></a>

### Lift by Prefix (^=)

Synapse performs prefix indexing on string and string-derived types, which optimizes lifting nodes whose `<valu>` or `<pval>` starts with a given prefix (substring). The extended comparator `^=` is used to lift nodes by prefix.

> [!NOTE]
> Extended string types that support dotted notation (such as the [loc](storm_ref_type_specific.md#type-loc) or [syn:tag](storm_ref_type_specific.md#type-syn-tag) types) have custom behaviors with respect to lifting and filtering by prefix.
>
> In addition, [inet:fqdn](storm_ref_type_specific.md#type-inet-fqdn) nodes are indexed in reverse string order so cannot be lifted using the prefix extended operator. However, reverse indexing allows wildcard ( `*` ) matching of the beginning of any FQDN string.
>
> See the relevant sections in the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) guide for details.

**Syntax**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **^=** *\<prefix\>*

*\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **^=** *\<prefix\>*

**Examples**

Lift the email addresses (`inet:email` nodes) that start with `abuse`:

```mdstorm --hide
[ inet:email=abuse@1and1.com inet:email=abuse.tor-exit@posteo.org ]
```

```mdstorm --hide
inet:email^=abuse
```

``` text
inet:email^=abuse
```

Lift the organizations (`ou:org` nodes) whose name starts with `ministry`:

```mdstorm --hide
[ ou:org=( { "name": "Ministry for Foreign Affairs of Finland" } ) ou:org=( { "name": "Ministry of Finance of Ukraine" } ) ]
```

```mdstorm --hide
ou:org:name^=ministry
```

``` text
ou:org:name^=ministry
```

Lift the Microsoft Office metadata nodes (all nodes of all forms that implement the `file:mime:msoffice` interface) whose `:author:name` starts with `DESKTOP`:

```mdstorm --hide
[ file:mime:msdoc=( { "application:name": "Microsoft Word", "author:name": "DESKTOP-BCXJXDX", "title": "Perfectly Safe Document" } ) file:mime:msppt=( { "application:name": "Microsoft PowerPoint", "author:name": "Ozzie", "title": "Why Bananas are the Best Fruit" } ) file:mime:msxls=( { "application:name": "Microsoft Excel", "author:name": "DESKTOP-KOCEDSI", "title": "Fine to Enable Macros" } ) ]
```

``` text
file:mime:msoffice:author:name^=DESKTOP
```

```mdstorm
file:mime:msoffice:author:name^=DESKTOP
```

Lift the tags (`syn:tag` nodes) in the `rep.alienvault` tree where the third tag element starts with the numeral `0`:

```mdstorm --hide
[ syn:tag=rep.alienvault.0_day syn:tag=rep.alienvault.0ktapus ]
```

``` text
syn:tag^=rep.alienvault.0
```

```mdstorm
syn:tag^=rep.alienvault.0
```

> [!TIP]
> When lifting `syn:tag` nodes by prefix, the prefix string is not constrained to dot boundaries. In other words, a prefix lift used with tags can match a partial tag element. The query above will match all of the following tags:
>
> - `syn:tag=rep.alienvault.0_day`
> - `syn:tag=rep.alienvault.0_days`
> - `syn:tag=rep.alienvault.0day`
> - `syn:tag=rep.alienvault.0days`
> - `syn:tag=rep.alienvault.0ktapus`

<a id="lift-interval"></a>

### Lift by Time or Interval (@=)

Many forms include properties that are date / time values (`<ptype>=<time>`) or time windows / intervals (`<ptype>=<ival>`). The time/interval extended comparator `@=` is used to lift nodes based on comparisons among various combinations of times and intervals.

**Syntax**

*\<form\>* | *\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **@=(** *\<ival_min\>* **,** *\<ival_max\>* **)**

*\<form\>* | *\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **@=** *\<time\>*

**Examples**

Lift the DNS A records whose `:seen` values overlap with the period from July 1, 2025 to August 1, 2025:

```mdstorm --hide
[ ( inet:dns:a=(easymathpath.com, 135.125.78.187) :seen=('2025/06/28 12:14:07', '2025/07/22 01:50:54') ) ( inet:dns:a=(hardmathpath.com, 42.27.18.56) :seen=('2025/07/14 22:03:00', '2025/09/06 05:26:19') ) ( inet:dns:a=(mathpath.com, 206.57.19.28) :seen=('2025/07/07 14:47:04', '2025/07/28 23:29:15') ) ( inet:dns:a=(geometrypath.com, 197.43.22.108) :seen=('2025/03/19 18:08:43', '2025/10/06 17:57:55') ) ] 
```

``` text
inet:dns:a:seen@=(2025/07/01, 2025/08/01)
```

```mdstorm
inet:dns:a:seen@=(2025/07/01, 2025/08/01)
```

Lift the DNS requests that occurred on May 3, 2023 between 2100 and 2200:

```mdstorm --hide
[ inet:dns:request=( { "time": "2023/05/03 21:09:04", "query:name": "vertex.link" } ) ]
```

``` text
inet:dns:request:time@=('2023/05/03 21:00', '2023/05/03 22:00')
```

```mdstorm
inet:dns:request:time@=('2023/05/03 21:00', '2023/05/03 22:00')
```

Lift the reports that were published within the past day:

```mdstorm --hide
[ doc:report=( { "publisher:name": "The Vertex Project", "title": "Swanson Still Stealing Things" } ) :published=now ]
```

```mdstorm --hide
doc:report:published@=(now, '-1 day')
```

``` text
doc:report:published@=(now, '-1 day')
```

Lift the host event nodes (all nodes of all forms that implement the `it:host:event` interface) that occurred within the past three hours:

```mdstorm --hide
[ ( it:exec:file:write=( { "path": "c:/windows/system32/evil.exe" } ) :time=now ) it:exec:mutex:add=( { "time": "2024/01/15", "name": "abcdefg" } ) ]
```

```mdstorm --hide
it:host:event:time@=(now, '-3 hours')
```

``` text
it:host:event:time@=(now, '-3 hours')
```

**Usage Notes:**

- When specifying an interval with the `@=` operator, the minimum value is **included** in the interval for comparison purposes but the maximum value is **not**. This is equivalent to "greater than or equal to `<min>` and less than `<max>`". This behavior differs from that of the `*range=` operator, which includes **both** the minimum and maximum.

- **Comparing intervals to intervals:** When using `@=` to compare an interval (e.g., `@=(2025/07/01, 2025/08/01)`) with an interval property (e.g., `:seen`), Synapse returns all nodes whose interval property values **overlap** in any way with the specified interval. This includes results that fall entirely within the interval, as well as results that start and / or end outside of the interval boundaries.  
  To find results that fall **within** an interval, use the `.min` and `.max` virtual properties with the `>=` and `<` operators. For example:  
  ``` text
    inet:dns:a:seen.min>=2025/07/01 +:seen.max<2025/08/01
  ```
  
- **Comparing intervals to times:** When using `@=` to compare an interval (e.g., (`@=('2023/05/03 21:00', '2023/05/03 22:00')`) with a time property (e.g. `:time`) Synapse will return all nodes whose time property value falls **within** the specified interval.

- **Comparing times to times:** When using `@=` to compare a time (e.g., `@=2026/02/19 08:15:37`) with a time property, Synapse returns nodes whose timestamp is an **exact match** of the specified time. (In this case the interval comparator ( `@=` ) behaves like the equal to comparator ( `=` ).)

- Time-based keywords (such as `now`) and relative time values (expressions such as `+-1 hour` or `-7 days`) can be used for interval values.

- When using relative time values (such as `-1 hour`) in an interval, a relative value in `<min>` is calculated relative to the current time (`now`). A relative value in `<max>` is calculated relative to `<min>`.

- Time values (including interval `<min>` / `<max>` values) can be specified at any resolution (e.g., `2026` to `2026/06/23 09:33:47.2348971`). All lower-resolution values are **zero-filled** by default; so Synapse interprets `2026` as `2026/01/01 00:00:00.000000`.

- A time value specified using wildcard syntax is equivalent to a time interval, and may provide a simpler and more intuitive way to represent some interval values. For example, say you want to lift domain whois records where the FQDN was registered (`:created`) during May 2024. The query `inet:whois:record:created=202405*` is equivalent to `inet:whois:record:created@=(2024/05/01, 2024/06/01)`.

> [!NOTE]
> Times and intervals can make use of specialized syntax elements and behaviors, the details of which are beyond the scope of this document.
> See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for a more detailed discussion of [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) data types.

<a id="lift-range"></a>

### Lift by Range (\*range=)

The range extended comparator (`*range=`) supports lifting nodes whose `<form>=<valu>` or `<prop>=<pval>` fall within a specified range of values. The comparator can be used with types such as integers and times.

> [!NOTE]
> The `*range=` operator cannot be used to compare a time range with a property value that is an interval (`ival` type). The interval ( `@=` ) operator should be used instead.
>
> The `*range=` operator can be used to lift `inet:ip` values (which are stored as integers). However, ranges of `inet:ip` nodes can also be lifted directly by specifying the lower and upper addresses in the range using `<min>-<max>` format, or by using CIDR notation. See the [inet:ip](storm_ref_type_specific.md#type-inet-ip) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) document for details. 

**Syntax**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

*\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **\*range = (** *\<range_min\>* **,** *\<range_max\>* **)**

**Examples**

Lift the files whose size is between 1000 and 100000 bytes:

```mdstorm --hide
[ file:bytes=( { "sha256": "00ecd10902d3a3c52035dfa0da027d4942494c75f59b6d6d6670564d85376c94" } ) :size=2000 ]
```

```mdstorm --hide
file:bytes:size*range=(1000, 100000)
```

``` text
file:bytes:size*range=(1000, 100000)
```

Lift the files whose VirusTotal reputation score (`:_virustotal:reputation` extended property) is between -20 and 20:

```mdstorm --hide
[ file:bytes=( { "sha256": "d231f3b6d6e4c56cb7f149cbc0178f7b80448c24f14dced5a864015512b0ba1f", "$props": { "_virustotal:reputation": "-16" } } ) file:bytes=( { "sha256": "d0e526a19497117a854f1ac9a9347f7621709afc3548c2e6a46b19e833578eac", "$props": { "_virustotal:reputation": "8" } } ) ]
```

```mdstorm --hide
file:bytes:_virustotal:reputation*range=(-20, 20)
```

``` text
file:bytes:_virustotal:reputation*range=(-20, 20)
```

Lift the DNS requests that were made between November 29, 2025 and January 14, 2026:

```mdstorm --hide
[ inet:dns:request=( { "query:name": "vertex.link", "time": "2025/12/09 13:47:11" } ) inet:dns:request=( { "query:name": "example.com", "time": "2026/01/03 20:07:01" } ) ]
```

```mdstorm --hide
inet:dns:request:time*range=(2025/11/29, 2026/01/14)
```

``` text
inet:dns:request:time*range=(2025/11/29, 2026/01/14)
```

Lift the HTTP requests (`inet:http:request` nodes) made within one day of December 1, 2024:

```mdstorm --hide
[ inet:http:request=( { "time": "2024/11/30 21:09:04", "method": "GET", "url": "https://vertex.link/" } ) ]
```

```mdstorm --hide
inet:http:request:time*range=(2024/12/01, '+-1 day')
```

``` text
inet:http:request:time*range=(2024/12/01, '+-1 day')
```

**Usage Notes:**

- When specifying a range, **both** the minimum and maximum values are **included** in the range. This is the equivalent of "greater than or equal to `<min>` and less than or equal to `<max>`". This behavior is in contrast to the `@=` operator

- If you specify range `<min>, <max>` values that are nonsensical or exclusionary (such as `*range=(47, 16)`), Synapse will **not** generate an error and will simply fail to return results. (The expression is syntactically correct, but no value is both greater than 47 and less than 16).

- Time-based keywords (such as `now`) and relative time values (expressions such as `+-1 hour` or `-7 days`) can be used for range values.

- When using relative time values (such as `-1 hour`) in a range, a relative value in `<min>` is calculated relative to the current time (`now`). A relative value in `<max>` is calculated relative to `<min>`.

- Time values (including range `<min>` / `<max>` values) can be specified at any resolution (e.g., `2026` to `2026/06/23 09:33:47.2348971`). All lower-resolution values are **zero-filled** by default; so Synapse interprets `2026` as `2026/01/01 00:00:00.000000`.

- A time value specified using wildcard syntax is equivalent to a range of times, and may provide a simpler and more intuitive way to represent some range values. For example, say you want to lift domain whois records where the FQDN was registered (`:created`) during May 2024. The query `inet:whois:record:created=202405*` is equivalent to `inet:whois:record:created*range=(2024/05/01, '2024/05/31 23:59:59.999999')`.

> [!NOTE]
> Times and intervals can make use of specialized syntax elements and behaviors, the details of which are beyond the scope of this document.
> See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for a more detailed discussion of [time](storm_ref_type_specific.md#type-time) and [ival](storm_ref_type_specific.md#type-ival) data types.

<a id="lift-set"></a>

### Lift by Set Membership (\*in=)

The set membership extended comparator (`*in=`) supports lifting nodes whose `<form>=<valu>` or `<prop>=<pval>` matches any of a set of specified values. The comparator can be used with any type.

**Syntax**

*\<form\>* \[ **:** \| **.** \| **:\_** *\<prop\>* \] **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

*\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **\*in = (** *\<set_1\>* **,** *\<set_2\>* **,** ... **)**

**Examples**

Lift entity names matching any of the specified values:

```mdstorm --hide
[ entity:name=fsb entity:name='yevgeniy prigozhin' entity:name='vladimir putin' ]
```

```mdstorm --hide
entity:name*in=(fsb, 'yevgeniy prigozhin', 'vladimir putin')
```

``` text
entity:name*in=(fsb, 'yevgeniy prigozhin', 'vladimir putin')
```

Lift the IP addresses associated with any of the specified Autonomous System (AS) numbers:

```mdstorm --hide
[ ( inet:asn=44477 :registrant:name='stark industries solutions ltd' ) ( inet:asn=20473 :registrant:name=as-choopa ) ( inet:asn=9009 :registrant:name='m247 europe srl' ) ]
```

```mdstorm --hide
inet:ip:asn*in=(9009, 20473, 44477)
```

``` text
inet:ip:asn*in=(9009, 20473, 44477)
```

Lift the tags (`syn:tag` nodes) whose final tag element (`:base`) matches any of the specified string values:

```mdstorm --hide
[ syn:tag=rep.talos.plugx syn:tag=rep.eset.korplug syn:tag=rep.mandiant.sogu syn:tag=rep.alienvault.kaba ]
```

``` text
syn:tag:base*in=(plugx, korplug, sogu, kaba)
```

```mdstorm
syn:tag:base*in=(plugx, korplug, sogu, kaba)
```

<a id="lift-proximity"></a>

### Lift by Proximity (\*near=)

The proximity extended comparator (`*near=`) supports lifting nodes by "nearness" to another node. Currently, `*near=` supports proximity based on geospatial location (i.e., nodes within a given radius of a specified latitude / longitude).

**Syntax**

*\<form\>* | *\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **\*near = ((** *\<lat\>* **,** *\<long\>* **),** *\<radius\>* **)**

**Examples**

Lift the locations (`geo:place` nodes) within 500 meters of the Russian Cryptographic Museum (where the coordinates `55.83069, 37.59781` represent the Museum's location):

```mdstorm --hide
[ geo:place=( { "latlong": "55.83088, 37.59962", "name": "Russian Cryptographic Museum" } ) ]
```

```mdstorm --hide
geo:place:latlong*near=((55.83069, 37.59781), 500m)
```

``` text
geo:place:latlong*near=((55.83069, 37.59781), 500m)
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
- Radius values of less than 1 must be specified with a leading zero (e.g., `0.5km`).
- The `*near=` comparator works for geospatial data by lifting nodes within a square bounding box centered at `<lat>, <long>`, then filters the nodes returned by ensuring that they are within the great-circle distance given by the `<radius>` argument.

<a id="lift-by-arrays"></a>

### Lift by (Arrays) (\*\[ \])

Storm uses a special syntax to lift (or filter) by comparison with one or more elements of an [array](storm_ref_type_specific.md#type-array) type. The syntax consists of an asterisk ( `*` ) preceding a set of square brackets ( `[ ]` ), where the square brackets contain a comparison operator and a value that can match one or more elements in the array. This allows users to match values in the array list without needing to know the exact order or values of the array itself.

**Syntax**

*\<form\>* | *\<interface\>* **:** \| **.** \| **:\_** *\<prop\>* **\*\[** *\<operator\>* *\<pval\>* **\]**

**Examples**

Lift the x509 certificates (`crypto:x509:cert` nodes) that reference FQDNs ending with `.xyz`:

```mdstorm --hide
[ crypto:x509:cert=8000873a9b409001877da726967a367f :identities:fqdns=(woot.biz, woot.xyz) ]
```

```mdstorm --hide
crypto:x509:cert:identities:fqdns*[='*.xyz']
```

``` text
crypto:x509:cert:identities:fqdns*[='*.xyz']
```

Lift the threat clusters (`risk:threat` nodes) whose secondary (alternate) names include the string `dragon`:

```mdstorm --hide
[ ( risk:threat=( { "reporter:name": "lookout", "name": "apt41" } ) :names+='double dragon' )  ( risk:threat=( { "reporter:name": "sophos", "name": "iron liberty" } ) :names+=dragonfly ) ]
```

``` text
risk:threat:names*[~=dragon]
```

```mdstorm
risk:threat:names*[~=dragon]
```

**Usage Notes:**

- The comparison operator used must be valid for lift operations for the type used in the array. For example, [inet:fqdn](storm_ref_type_specific.md#type-inet-fqdn) suffix matching (i.e., `crypto:x509:cert:identities:fqdns*[='*.com']`), can be used when lifting arrays consisting of domains, but the prefix operator ( `^=` ), which is only valid when **filtering** `inet:fqdns`, cannot.

- The standard equals ( `=` ) operator can be used to lift nodes based on array properties, but the value specified must **exactly match** the **full** property value in question. For example:

  `ou:org:names=('the vertex project', 'the vertex project llc', vertex )`

- See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) document for a more detailed discussion of working with arrays.

<a id="tag-lifts"></a>

## Tag Lifts

Tags in Synapse can represent observations or assessments. They are used to provide context to nodes (in the form of "labels" applied to nodes) and to group related nodes.

Storm supports lifting nodes based on the tag(s) applied to the node, as well lifting based on tag timestamps, tag properties, or tag property values.

The hashtag symbol ( `#` ) is used to specify a tag name when lifting by tag.

When performing a tag lift, you can use the name of an [interface](../glossary.md#gloss-interface), to represent all nodes of all forms that implement the interface. Similarly, if a form makes use of [form inheritance](../glossary.md#gloss-form-inheritance), you can use the name of a parent form represent all nodes of the parent form and any form that extends the parent.

> [!NOTE]
> Synapse does not include any pre-defined tags (although some Power-Ups may create tags as defined within the Power-Up itself). The examples below are based on tags and tag conventions used by The Vertex Project.

<a id="lift-by-tag"></a>

### Lift by Tag

A **lift by tag** operation lifts **all** nodes that have the specified tag.

**Syntax**

**\#** *\<tag\>*

**Examples**

Lift all nodes that ESET associates with Sednit (`#rep.eset.sednit`):

```mdstorm --hide
[ inet:fqdn=kg-news.org inet:ip=92.114.92.125 +#rep.eset.sednit ]
```

``` text
#rep.eset.sednit
```

```mdstorm
#rep.eset.sednit
```

Lift all nodes associated with anonymized infrastructure (`#cno.infra.anon`):

```mdstorm --hide
[ ( inet:fqdn=ca2.vpn.airdns.org +#cno.infra.anon.vpn ) ( inet:ip=104.244.73.193 +#cno.infra.anon.tor.exit ) ]
```

``` text
#cno.infra.anon
```

```mdstorm
#cno.infra.anon
```

> [!TIP]
> Tags are hierarchical, and each tag element is its own tag; the tag `#cno.infra.anon` consists of the tags `#cno`, `#cno.infra`, and `#cno.infra.anon`. Lifting nodes using a tag higher up in the tag hierarchy will lift all nodes with specified tag or any tag lower down in the hierarchy. In other words, lifting by `#cno.infra.anon` will lift all anonymized infrastructure, whether the infrastructure is a VPN (`#cno.infra.anon.vpn`), a TOR node (`#cno.infra.anon.tor`), or an anonymous proxy (`#cno.infra.anon.proxy`).

<a id="lift-form-by-tag"></a>

### Lift Form by Tag

A **lift form by tag** operation lifts only those nodes of the specified form that have a particular tag.

**Syntax**

*\<form\>* | *\<interface\>* **\#** *\<tag\>*

**Examples**

Lift the FQDNs that ESET associates with Sednit (`#rep.eset.sednit`):

```mdstorm --hide
[ inet:fqdn=kg-news.org inet:ip=92.114.92.125 +#rep.eset.sednit ]
```

```mdstorm --hide
inet:fqdn#rep.eset.sednit
```

``` text
inet:fqdn#rep.eset.sednit
```

Lift the IP addresses associated with DNS sinkhole infrastructure (`#cno.infra.dns.sink.hole`):

```mdstorm --hide
[ inet:ip=134.209.227.14 +#cno.infra.dns.sink.hole ]
```

```mdstorm --hide
inet:ip#cno.infra.dns.sink.hole
```

``` text
inet:ip#cno.infra.dns.sink.hole
```

List all entity activity nodes (all nodes of all forms that implement the `entity:activity` interface) that Vertex attributes to the Wobbly Emu threat group (`#cno.threat.wobbly_emu`):

```mdstorm --hide
[ risk:attack=( { "name": "CVE-2026-1603 Exploit Attempt", "period": "2026/02/17", "reporter:name": "Vertex", "actor:name": "Wobbly Emu" } ) entity:campaign=( { "name": "Credential Phishing Campaign", "period": "(2026/05/13, 2026/05/18)", "reporter:name": "Vertex", "actor:name": "Wobbly Emu" } ) risk:extortion=( { "name": "Extortion / Threat to Release Internal Data", "period": "2026/06/01", "reporter:name": "Vertex", "actor:name": "Wobbly Emu" } ) +#cno.threat.wobbly_emu ]
```

``` text
entity:activity#cno.threat.wobbly_emu
```

```mdstorm
entity:activity#cno.threat.wobbly_emu
```

> [!TIP]
> The equivalent of a lift form by tag operation is a lift operation that lifts all nodes of the specified form, (e.g., all `inet:ip` nodes), followed by a filter operation that keeps only those nodes with the specified tag. This set of operations performed in sequence (lift, then filter) can be resource-intensive and inefficient, since it requires you to first lift **all** nodes of a form only to potentially discard most of them.
> 
> Instead, Synapse specifically optimizes the lift form by tag operation to **only** lift nodes that have the tag.
> 
> If you specify a Storm query such as `inet:fqdn +#rep.mandiant.apt1`, Synapse will automatically execute the query **as if** you had entered `inet:fqdn#rep.mandiant.apt1`. In other words, in some cases Synapse knows to "do what you mean" in order to process your queries more efficiently.

<a id="lift-tag-timestamp"></a>

### Lift Using Tag Timestamps

A tag timestamp can be thought of as a specialized "property" of a tag that happens to be a date / time range (interval). You can lift nodes based on tag timestamp values using:
- the full interval associated with the timestamp. You can use any comparison operator supported by interval ([ival](storm_ref_type_specific.md#type-ival) types). The time / interval extended operator ( `@=` ) is used most often, but equal to ( `=` ) can also be used to **exactly** match the values in the interval.
- the individual `<min>` or `<max>` values of the interval. Because the tag dot separator ( `.` ) is the same character used to delimit virtual properties, you must enclose the tag string in parentheses when referencing the `.min` or `.max` value of a tag timestamp. 

See [Lift by Time or Interval (@=)](storm_ref_lift.md#lift-interval) for additional detail on the use of the `@=` operator.

**Syntax**

\[ *\<form\>* | *\<interface\>* \] **\#** *\<tag\>* **@=** *\<time\>* \| **(** *\<min_time\>* **,** *\<max_time\>* **)**

\[ *\<form\>* | *\<interface\>* \] **\#(** *\<tag\>* **).min** | **).max** *\<operator\>* *\<pval\>* 

Lift any nodes that were associated with anonymous VPN infrastructure (`#cno.infra.anon.vpn`) between December 1, 2023 and January 1, 2024:

```mdstorm --hide
[ ( inet:fqdn=wazn.airservers.org +#cno.infra.anon.vpn=('2023/05/24 23:16:51.423', '2023/12/05 23:12:40.626') ) ( inet:ip=2607:9000:0:85:68a3:75b4:13ab:770a +#cno.infra.anon.vpn=('2023/08/15 00:12:15', '2023/12/05 23:12:54') ) ]
```

```mdstorm --hide
#cno.infra.anon.vpn@=(2023/12/01, 2024/01/01)
```

``` text
#cno.infra.anon.vpn@=(2023/12/01, 2024/01/01)
```

Lift the FQDNs that were owned / controlled by Threat Cluster 15 (`#cno.threat.t15.own`) as of October 30, 2025:

```mdstorm --hide
[ inet:fqdn=ronthecat.com +#cno.threat.t15.own=(2023/09/12, 2025/09/12) ]
```

```mdstorm --hide
inet:fqdn#cno.threat.t15.own@=2025/10/30
```

``` text
inet:fqdn#cno.threat.t15.own@=2025/10/30
```

Lift the IP addresses that were identified as TOR exit nodes (`#cno.infra.anon.tor.exit`) on or after June 1, 2026:

```mdstorm --hide
[ ( inet:ip=185.29.8.215 +#cno.infra.anon.tor.exit=(2025/05/08 14:30:51, 2026/01/04 22:05:03) ) ( inet:ip=91.208.162.197 +#cno.infra.anon.tor.exit=(2026/07/14 15:00:25, 2026/08/01 15:35:57) ) ]
```

```mdstorm --hide
inet:ip#(cno.infra.anon.tor.exit).min>=2026/06/01
```

``` text
  inet:ip#(cno.infra.anon.tor.exit).min>=2026/06/01
```

<a id="lift-tag-prop"></a>

### Lift Using Tag Properties

[Tag Properties](analytical_model.md#tag-properties) can be used to provide additional context to tags. Storm supports lifting nodes whose tags have a specific tag property (regardless of the value of the property).

> [!TIP]
> Synapse v3 includes two tag properties in its base data model: `:confidence` (of type and `meta:score`) and `:tlp` (of type `it:sec:tlp`). Tag properties can be added by [extending the data model](data_model.md#extending-the-data-model).

**Syntax**

\[ *\<form\>* | *\<interface\>* \] **\#** *\<tag\>* **:** | **:_** *\<tagprop\>*

Lift any nodes that Vertex associates with the threat group Vicious Wombat (`#cno.threat.vicious_wombat`) where the tag has a `:tlp` tag property:

```mdstorm --hide
[ (inet:ip=5.6.7.8 +#cno.threat.vicious_wombat:tlp=amber-strict) (inet:fqdn=marsupialsrule.com +#cno.threat.vicious_wombat:tlp=amber) ]
```

```text
#cno.threat.vicious_wombat:tlp
```

```mdstorm
#cno.threat.vicious_wombat:tlp
```

Lift the IP addresses tagged as sinkhole infrastructure (`#cno.infra.dns.sink.hole`) that have an associated `:confidence` tag property:

```mdstorm --hide
[ (inet:ip=69.195.129.72 +#cno.infra.dns.sink.hole:confidence=high ) (inet:ip=45.56.77.175 +#cno.infra.dns.sink.hole:confidence=low ) inet:ip=8.8.8.8 ]
```

```text
inet:ip#cno.infra.dns.sink.hole:confidence
```

```mdstorm
inet:ip#cno.infra.dns.sink.hole:confidence
```

> [!NOTE]
> You must specify a tag associated with the tag property. It is not possible to lift nodes based on a particular tag property being present on **any** tag (e.g., a Storm query such as `#:tlp` will generate a `BadSyntax` error).

<a id="lift-tag-prop-value"></a>

### Lift Using Tag Property Values

Storm supports lifting nodes based on the value of a tag property (similar to lifting by the value of a node property).

You can lift nodes based on tag property values using any comparison operator supported by the property's [type](../glossary.md#gloss-type). For example, if the tag property is defined as an integer (`int`) type, you can use any comparison operator supported by integers.

The ["Try" Operator](storm_ref_lift.md#lift-try) ( `?=` ) can optionally be used in place of the standard equal to operator ( `=` ) for tag property values. Use of the try operator is generally not required for interactive Storm queries, but may be useful for more complex Storm queries (such as automation or Storm-based ingest queries).

**Syntax**

\[ *\<form\>* | *\<interface\>* \] **\#** *\<tag\>* **:** | **:_** *\<tagprop\>* *\<operator\>* *\<pval\>*

**Examples**

Lift all of the nodes that Vertex associates with the threat group Vicious Wombat (`#cno.threat.vicious_wombat`) that are marked as **lower** than TLP: Amber (e.g., TLP: Green or TLP: Clear): 

```mdstorm --hide
[ (inet:ip=5.6.7.8 +#cno.threat.vicious.wombat:tlp=amber-strict) (inet:fqdn=marsupialsrule.com +#cno.threat.vicious.wombat:tlp=amber) (inet:fqdn=combatwombat.net +#cno.threat.vicious_wombat:tlp=green) (inet:email=fuzzywuzzy@cutebutdeadly.org +#cno.threat.vicious_wombat:tlp=clear) ]
```

```text
#cno.threat.vicious_wombat:tlp<amber
```

```mdstorm
#cno.threat.vicious_wombat:tlp<amber
```

> [!TIP]
> The `:tlp` tag property's type is `it:sec:tlp`. This type is an enum of defined integer values (10, 20, 30, etc.) corresponding to TLP levels (clear, green, amber, etc.) The property can be queried (and compared) based on the integer value. The value itself can be specified using either the integer (`30`) or the corresponding term (`amber`).

Lift the IP addresses tagged as sinkholes (`#cno.infra.dns.sink.hole`) where the associated `:confidence` is high:

```mdstorm --hide
[ (inet:ip=69.195.129.72 +#cno.infra.dns.sink.hole:confidence=high ) (inet:ip=45.56.77.175 +#cno.infra.dns.sink.hole:confidence=low ) inet:ip=8.8.8.8 ]
```

```text
inet:ip#cno.infra.dns.sink.hole:confidence=high
```

```mdstorm
inet:ip#cno.infra.dns.sink.hole:confidence=high
```

> [!TIP]
> The `:confidence` tag property's type is `meta:score`. The type is an enum that defines a standard set of integer values (0, 10, 20, etc.) with corresponding confidence terms (none, lowest, low, medium, etc). Users are not limited to these specific values, but can specify any integer. Values can be specified (and compared) using either the integer value or (where present) the corresponding term.

<a id="lift-tag-recursive"></a>

### Recursive Tag Lift (##)

You can apply tags to `syn:tag` nodes to provide additional context to the `syn:tag` node itself, or to group related `syn:tag` nodes.

A **recursive tag lift** retrieves all nodes with the specified tag. If the results include any `syn:tag` nodes, the recursive lift will also lift any nodes with those tags. The process continues until no more `syn:tag` nodes are returned.

The final result set returned by a recursive tag lift includes all of the nodes that were lifted recursively, but will **not** include any lifted `syn:tag` nodes themselves.

The double hashtag symbol ( `##` ) is used to specify a recursive tag lift.

> [!NOTE]
> "Tag the tags" can provide context to things that tags represent and may be suitable for some use cases.
>
> However, many forms in data model have a `:tag` property that links a `syn:tag` to the object or concept the tag represents. For example a tag used to associate nodes with a threat cluster (such as `#rep.microsoft.forest_blizzard`) can be linked to a `risk:threat` **node** representing Microsoft's Forest Blizzard. Linking a tag (`syn:tag`) to a node (`risk:threat`) can provide significantly more context (via the node's properties) about Forest Blizzard than simply tagging a tag. For example, the `risk:threat` node can record information such as when the group was active, any alternate names used in reporting, and so on. In short, using a form that is linked to a tag and has secondary properties to provide context gives you greater flexibility to record that context (vs. "tag the tags") and simplifies lifting, filtering, and pivoting across similar nodes.
>
> See [Tags Associated with Nodes](analytical_model.md#analytical-tags-asnodes) for a brief discussion of this concept, or the [User Guide](/docs/synapse-enterprise-optic/latest/user_interface/userguide.md) for the [Vertex-Threat-Intel](/docs/vertex-threat-intel/latest/index.md) Power-Up (in particular, the [Threat Intel Model](/docs/vertex-threat-intel/latest/ugmodel.md) section) for additional examples.

**Syntax**

**\##** *\<tag\>*

**Example**

You are using "availability" tags to show the general availability of software reported by Mandiant. You add the appropriate "availability" tag to the `syn:tag` node that represents the associated software. For example, you apply the tag `#rep.mandiant.avail.public` to the node `syn:tag=rep.mandiant.gh0st` because Mandiant reported that the source code for the Gh0st backdoor is publicly available.

You want to lift the nodes (e.g., indicators of compromise) associated with any software that Mandiant reports is publicly available:

```mdstorm --hide
[ ( syn:tag=rep.mandiant.beacon syn:tag=rep.mandiant.gh0st +#rep.mandiant.avail.public ) ( crypto:hash:md5=1844370fa7dac0e99779000f8f0b2f4e inet:fqdn=zomerax.top +#rep.mandiant.beacon ) ( inet:fqdn=iphone.vizvaz.com +#rep.mandiant.gh0st ) ]
```

``` text
##rep.mandiant.avail.public
```

```mdstorm --hide
##rep.mandiant.avail.public
```

The query above:

- Lifts the nodes tagged `#rep.mandiant.avail.public`, such as `syn:tag` nodes for software that Mandiant assesses is publicly available (e.g., `syn:tag=rep.mandiant.gh0st` or `syn:tag=rep.mandiant.beacon`).
- Lifts any nodes tagged with those tags (e.g., `#rep.mandiant.gh0st` or `#rep.mandiant.beacon`). This would typically include IOCs such as hashes, FQDNs, IPs, URLs, etc.
- If any nodes tagged with the additional tags (`#rep.mandiant.gh0st`, etc.) are `syn:tag` nodes, repeat the process, continuing until no more `syn:tag` nodes are lifted.
- Returns the recursively lifted set of nodes (excluding any `syn:tag` nodes).

**Note:** the example above is somewhat contrived. `it:software` has an `:availability` property that can be used to record this data.

<a id="lift-reverse"></a>

## "reverse" Keyword

Synapse indexes property values so that data (nodes) can be lifted (retrieved) and returned quickly. By default, lift results are returned in lexical order (i.e., sorted in ascending order), based on the property specified in the lift (primary, secondary, meta, extended, or virtual) and the way the property is indexed.

The `reverse` keyword can be used to return the specified nodes in reverse lexical order (i.e., sorted in descending order). To perform a reverse lift, specify the `reverse` keyword and enclose the lift operation in parentheses.

A reverse lift can be followed by additional Storm operations (pivots, filters, commands) just like a "normal" lift.

> [!TIP]
> When using the `reverse` keyword to lift by secondary property value using an [interface](../glossary.md#gloss-interface) name, Synapse performs the lifts for each form in parallel, and yields the results in descending order. For example, the following query will return all nodes of all forms that implement the `it:host:event` interface that have a `:time` value greater than or equal to 2024/02/01, sorted in descending order (most recent first):
>
> ``` text
> reverse (it:host:event:time>=2024/02/01)
> ```
> 

**Syntax**

**reverse (** *\<lift\>* **)**

**Examples**

Lift IP addresses (`inet:ip` nodes) with a `:place:loc` property (sorted descending based on the `:place:loc` property value):

```mdstorm --hide
[ ( inet:ip=197.155.229.194 :place:loc=zw.ha.harare ) ( inet:ip=41.221.147.14 :place:loc=zw ) ( inet:ip=41.164.23.42 :place:loc=za.wc.worcester ) ( inet:ip=155.254.9.3 :place:loc='us.mt.three forks' ) ( inet:ip=102.64.66.222 :place:loc='tz.02.dar es salaam' ) ]
```

``` text
reverse ( inet:ip:place:loc )
```

```mdstorm
reverse ( inet:ip:place:loc )
```

Lift five IP addresses (`inet:ip` nodes) (sorted descending based on the integer value of the `inet:ip` primary property):

```mdstorm --hide
[ inet:ip=255.255.255.255 inet:ip=223.159.33.195 inet:ip=198.42.76.23 inet:ip=52.16.48.7 inet:ip=40.250.10.120 inet:ip=12.163.57.22 ]
```

``` text
reverse ( inet:ip ) | limit 5
```

```mdstorm
reverse ( inet:ip ) | limit 5
```

Lift the five most recently-created email addresses (`inet:email` nodes) (sorted descending by the `.created` property value):

```mdstorm --hide
[ inet:email=praveen.s@hsrfunke.com inet:email=alhossani@adnoc.ae inet:email=20231128124623.11d85d83ed11a341@adnoc.ae inet:email=support@hammer-software.com inet:email=alex.gronholm@nextday.fi inet:email=dholth@fastmail.fm inet:email=illia.volochii@gmail.com ]
```

``` text
reverse ( inet:email.created ) | limit 5
```

```mdstorm
reverse ( inet:email.created ) | limit 5
```

> [!NOTE]
> In some cases, Synapse uses specialized indexing to optimize specific Storm operations (such as the ability to lift forms by tag) or to make it easier to work with certain types of data (type-specific behavior). For example, FQDN strings (`inet:fqdn` types) are reversed before being indexed.
>
> Where specialized indexing is used, both "normal" and reverse lifts still return nodes in lexical or reverse lexical order, respectively. However, the "sort order" of the results may not be apparent, based on the custom criteria used to index the nodes.
>
> See the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) section for details on some type-specific behaviors, including any custom indexing for the listed types.

<a id="lift-try"></a>

## "Try" Operator

The Storm "try" operator ( `?=` ) can be used in any lift operation as an alternative to the equal to ( `=` ) comparison operator.

Properties in Synapse are subject to [type enforcement](../glossary.md#gloss-type-enforce). Type enforcement makes a reasonable attempt to ensure that a value makes sense for the property in question - that the value you specify for an `inet:ip` node looks reasonably like an IP address (and not an FQDN or URL). If you try to lift a set of nodes using a property value that does not pass Synapse's type enforcement validation, Synapse will generate an error. The error will cause the currently executing Storm query to halt and stop processing. For example, the following query halts based on the bad value (`evil.com`) provided for an `inet:ip` node:

```mdstorm --hide
[ inet:ip=8.8.8.8 ]
```

```mdstorm --fail
inet:ip=evil.com inet:ip=8.8.8.8
```

When using the try operator ( `?=` ), Synapse will to attempt (try) to lift the node(s) using the specified property value. However, instead of halting in the event of an error, Synapse will ignore the error (silently fail on that specific lift operation) but continue processing the rest of the Storm query. Using the try operator below, Synapse ignores the bad value for the first IP address but returns the second one:

```mdstorm
inet:ip?=evil.com inet:ip?=8.8.8.8
```

The try operator is generally not necessary for interactive Storm queries. However, it can be very useful for more complex Storm queries or Storm-based automation (see [Storm Reference - Automation](storm_ref_automation.md#storm-ref-automation)), where a single badly-formatted lift operation (potentially relying on input or data from a third-party data source) could cause the query to fail during execution.

**Syntax**

*\<form\>* **?=** *\<valu\>*

*\<form\>* | *\<interface\>* **:** | **.** | **:_** *\<prop\>* **?=** *\<pval\>*

> [!TIP]
> See the [array](storm_ref_type_specific.md#type-array) section of the [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for specialized "try" syntax when working with array properties.

**Examples**

Try to lift the MD5 `174cc541c8d9e1accef73025293923a6`:

```mdstorm --hide
[ crypto:hash:md5=174cc541c8d9e1accef73025293923a6 ]
```

```mdstorm --hide
crypto:hash:md5?=174cc541c8d9e1accef73025293923a6
```

``` text
crypto:hash:md5?=174cc541c8d9e1accef73025293923a6
```

Try to lift the DNS A records whose `:ip` property is `192.168.0.100`:

```mdstorm --hide
[ inet:dns:a=(woot.com, 192.168.0.100) ]
```

```mdstorm --hide
inet:dns:a:ip?=192.168.0.100
```

``` text
inet:dns:a:ip?=192.168.0.100
```

Try to lift the email addresses for `ron@vertex.link` and `ozzie@vertex.link`:

In the example below, note that despite the first email address being entered incorrectly (using `[at]`), the error message is suppressed, and the query executes to completion.

```mdstorm --hide
[ inet:email=ron@vertex.link inet:email=ozzie@vertex.link ]
```

```mdstorm
inet:email?='ron[at]vertex.link' inet:email?='ozzie@vertex.link'
```
