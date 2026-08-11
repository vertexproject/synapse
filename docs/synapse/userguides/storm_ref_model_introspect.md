```mdstorm-setup
```

<a id="storm-ref-model-introspect"></a>


# Storm Reference - Model Introspection

This section describes how you can examine (perform introspection on) Synapse's **Data Model** (types, forms, etc.) and **Analytical Model** (tags) from within Synapse itself using Storm. (For details on using Storm, see [Storm Reference - Introduction](storm_ref_intro.md#storm-ref-intro) and related Storm topics.)

<a id="introspect-data-model"></a>


## Data Model

Synapse's data model is the essential framework that supports the consistent, structural representation of analytically relevant data and relationships. The effective use of the data model is the key that unlocks Synapse's powerful analysis and intelligence capabilities.

There are many ways to examine Synapse's data model, including through the Synapse source [code](https://github.com/vertexproject/synapse) or via the auto-generated [Synapse Data Model](../datamodel.md#dm-index) documentation. You can also explore the data model and its elements from within Synapse itself, using the Storm query language.

> [!TIP]
> [Synapse Enterprise](https://vertex.link/synapse) customers or users with a Synapse [demo stack](https://vertex.link/request-a-demo) can also use the [Optic](/docs/synapse-enterprise-optic/latest/index.md) UI (specifically Optic's [Data Model Explorer](/docs/synapse-enterprise-optic/latest/user_interface/userguides/get_help.md#using-data-model-explorer), located in the Help Tool) to examine the data model.

Synapse is able to read the current data model definition (all native and custom (extended) model elements) on demand and project the model as nodes within the Cortex itself. Because these nodes are generated on demand (at run-time) they are known as run-time nodes or **runt nodes**.

The following runt node forms are used to represent the Synapse data model for types, forms, properties, and interfaces, respectively:

- `syn:type`
- `syn:form`
- `syn:prop`
- `syn:interface`

> [!NOTE]
> Additional runt node forms exist besides the ones listed above. To view all of the runt forms in Synapse, use the following command:
>
> ``` text
> syn:form:runt=true
> ```

Because runt nodes are generated from the data model when requested, they cannot be modified (edited) or tagged. However, you can lift, filter, and pivot across them using Storm, just like any other nodes.

Refer to the various Storm documents for details on Storm syntax. A few simple example queries are provided below to illustrate some common operations for model introspection. (The [limit](storm_ref_cmd.md#storm-limit) command is used in some examples to display a sampling of results for illustrative purposes.)

### Example Queries

#### Types

Display all types:

```mdstorm
syn:type | limit 3
```

Display a specific type:

```mdstorm
syn:type=inet:fqdn
```

Display all types that are sub-types of `str` (string):

```mdstorm
syn:type:parent=str | limit 3
```

> [!TIP]
> Sub-types (`syn:type:parent`) are derived from a base type, but may have:
>
> - a specific purpose (e.g., it is helpful to distinguish strings that are HTTP header names from other arbitrary strings); and / or
> - additional (or alternate) constraints (`:opts`) on how the string can look and how it is normalized. For example, a Society for Worldwide Interbank Financial Telecommunication (SWIFT) Bank Identifier Code (BIC) used for routing financial transactions is a string, but one that has a specific format. An `econ:bank:swift:bic` in Synapse extends (is a `subof`) the `str` type that uses a regular expression (regex) to ensure that only properly formatted BIC values are created.

#### Forms

Display all forms:

```mdstorm
syn:form | limit 3
```

Display a specific form:

```mdstorm
syn:form=inet:ip
```

Display all of the properties of a specific form:

```mdstorm
syn:prop:form=inet:ip | limit 3
```

> [!TIP]
> A form's properties include its primary and secondary properties. Because meta properties (`.created` and `.updated`) exist on every form, Synapse does not include them for purposes of generating runt nodes.

Display a specific property of a specific form:

```mdstorm
syn:prop=inet:ip:place:loc
```

Display all of the forms that are tagged `#cno.threat.sparkling_unicorn`:

```mdstorm --hide
[ inet:fqdn=woot.com inet:ip=123.120.96.42 crypto:hash:sha256=5f6b2a0d1d966fc4f1ed292b46240767f4acb06c13512b0061b434ae2a692fa1 +#cno.threat.sparkling_unicorn ]
```

```mdstorm
#cno.threat.sparkling_unicorn $form=$node.form -> { syn:form=$form } | uniq
```

The query above assigns the variable `$form` to each node's form, uses [Raw Pivot Syntax](storm_ref_pivot.md#raw-pivot-syntax) to pivot to the associated `syn:form` runt nodes, and deduplicates the results.

#### Properties

Display all properties:

```mdstorm
syn:prop | limit 3
```

Display all properties that are **computed** by Synapse:

```mdstorm
syn:prop:computed=true | limit 3
```

> [!TIP]
> **Computed** properties are secondary properties that are derived or extracted from a node's primary property. Synapse computes and sets these properties automatically. Because they are based on the node's primary property, computed properties are read-only and cannot be edited.

Display all properties that are arrays:

```mdstorm
syn:prop:array=true | limit 3
```

Display all properties that can be of a specific type (e.g., an IP address / `inet:ip`):

```mdstorm
syn:prop:type*[=inet:ip] | limit 3
```

> [!TIP]
> All properties in Synapse must have a type, and any property can optionally be declared with more than one type. This means that property types are arrays, and you need to use [array syntax](storm_ref_lift.md#lift-by-arrays) to query them.

#### Interfaces

Display all interfaces:

```mdstorm
syn:interface | limit 3
```

Display a specific interface:

```mdstorm
syn:interface=meta:taxonomy
```

Display all **forms** that implement a specific interface (e.g., `inet:proto:request`):

```mdstorm
syn:form:interfaces*[=inet:proto:request] | limit 3
```

Display all **interfaces** that implement a specific interface (e.g., `base:activity`):

```mdstorm
syn:interface:interfaces*[=base:activity] | limit 3
```

> [!TIP]
> The queries above will return results (`syn:form` or `syn:interface` runt nodes) that implement the interface either directly or recursively (i.e., as the result of implementing another interface that implements the interface you are querying).

Display all forms **referenced by** a specific form (i.e., which properties of this form are **also** forms):

```mdstorm
syn:prop:form=file:bytes :type -> syn:type -> syn:form | limit 3
```

Display all forms that **reference** a specific form (i.e., which forms **have** this form as a secondary property):

```mdstorm
syn:form=file:bytes :type -> syn:type -> syn:prop:type | limit 3
```

#### Extended Model

Types, forms, properties, and tag properties which have been added to a Cortex as custom (extended) model elements all carry an `:extmodel` property which is set to `true`.

Display all extended forms:

```mdstorm --hide
$lib.model.ext.addForm(_visi:place, str, ({}), ({"doc": "A place Visi has been."}))
```

```mdstorm
syn:form:extmodel=true
```

Display all extended types:

```mdstorm --hide
$lib.model.ext.addType(_visi:score, int, ({}), ({"doc": "A score assigned by Visi."}))
```

```mdstorm
syn:type:extmodel=true
```

Display all extended properties:

```mdstorm --hide
$lib.model.ext.addFormProp(inet:fqdn, _visi:seen, (bool, ({})), ({"doc": "Set to true if Visi has seen the FQDN."}))
```

```mdstorm
syn:prop:extmodel=true
```

Display all extended tag properties:

```mdstorm --hide
$lib.model.ext.addTagProp(_visi:score, (int, ({})), ({"doc": "A score assigned by Visi."}))
```

```mdstorm
syn:tagprop:extmodel=true
```

> [!NOTE]
> An extended form also adds an extended type with the same name, so it is included in the results of a `syn:type:extmodel=true` query.

<a id="introspect-analytical-model"></a>


## Analytical Model

Tags in Synapse are a set of user-defined hierarchical labels that are used to group related nodes and provide context to individual nodes. Tags often represent internal (or third-party) assessments, so they are effectively an **analytical model** of context and conclusions that are relevant for your organization's analysis needs. Synapse users need to be able to readily identify tags, tag hierarchies, and the precise meaning of individual tags so they can be applied and interpreted correctly and consistently.

You can query and navigate Synapse's analytical model using tags (`syn:tag` nodes) similar to the way you navigate the data model using runt nodes. Note that `syn:tag` nodes are regular objects in the Cortex (**not** run-time nodes) that can be lifted, filtered, and pivoted across (as well as edited, tagged, and deleted) just like any other nodes.

> [!TIP]
> [Synapse Enterprise](https://vertex.link/synapse) customers or users with a Synapse [demo stack](https://vertex.link/request-a-demo) can also use the [Optic](/docs/synapse-enterprise-optic/latest/index.md) UI (specifically Optic's [Tag Explorer](/docs/synapse-enterprise-optic/latest/user_interface/userguides/get_help.md#using-tag-explorer), located in the Help Tool) to examine the analytical model.

You can lift, filter, and pivot across `syn:tag` nodes using the standard Storm query syntax; refer to the various Storm documents for details on using Storm. See also the `syn:tag` section of [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for additional details on working with `syn:tag` nodes.

A few simple example queries are provided below to illustrate some common operations for working with tags. As Synapse does not include any pre-populated `syn:tag` nodes, these examples assume you have a Cortex where tags have been created.

### Example Queries

Lift a single tag:

```mdstorm --hide
[ ( syn:tag=cno.infra :doc="Top-level tag for infrastructure." :title="Infrastructure" ) ( syn:tag=cno.infra.anon :doc="Top-level tag for anonymization services." :title="Anonymization services" ) ( syn:tag=cno.infra.anon.tor :doc="Infrastructure associated with the TOR network." :title="TOR infrastructure" ) ( syn:tag=cno.infra.anon.vpn :doc="A server representing an anonymous VPN service, or the associated IP address. Alternately, an FQDN explicitly denoting an anonymous VPN that resolves to the associated IP." :title = "Anonymous VPN" ) ]
```

```mdstorm
syn:tag=cno.infra.anon.tor
```

Lift all root tags:

```mdstorm
syn:tag:depth=0
```

Lift all tags one level "down" from the specified tag:

```mdstorm
syn:tag:up=cno.infra.anon
```

Lift all tags that start with a given prefix, regardless of depth:

```mdstorm
syn:tag^=cno.infra
```

Lift all tags that share the same base (rightmost) element:

```mdstorm --hide
[ ( syn:tag=rep.uscisa.salt_typhoon :doc="Indicator or activity US-CISA calls (or associates with) Salt Typhoon." :title="Salt Typhoon (US-CISA)" ) ( syn:tag=rep.microsoft.salt_typhoon :doc="Indicator or activity Microsoft calls (or associates with) Salt Typhoon." :title="Salt Typhoon (Microsoft)" ) ]
```

```mdstorm
syn:tag:base=salt_typhoon
```
