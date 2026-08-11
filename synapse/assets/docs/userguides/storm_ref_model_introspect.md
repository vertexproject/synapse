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

```stormdoc
storm> syn:type | limit 3
syn:type=auth:passwd
        :ctor = synapse.models.auth.Passwd
        :doc = A password string.
        :extmodel = false
        :opts = {'enums': None, 'regex': None, 'lower': False, 'strip': False, 'upper': False, 'replace': (), 'mapping': None, 'onespace': False, 'globsuffix': False}
syn:type=int
        :ctor = synapse.lib.types.Int
        :doc = The base 64 bit signed integer type.
        :extmodel = false
        :opts = {'size': 8, 'signed': True, 'enums': None, 'enums:strict': True, 'fmt': '%d', 'min': None, 'max': None, 'ismin': False, 'ismax': False}
syn:type=float
        :ctor = synapse.lib.types.Float
        :doc = The base floating point type.
        :extmodel = false
        :opts = {'fmt': '%f', 'min': None, 'minisvalid': True, 'max': None, 'maxisvalid': True}
```

Display a specific type:

```stormdoc
storm> syn:type=inet:fqdn
syn:type=inet:fqdn
        :ctor = synapse.models.inet.Fqdn
        :doc = A Fully Qualified Domain Name (FQDN).
        :extmodel = false
```

Display all types that are sub-types of `str` (string):

```stormdoc
storm> syn:type:parent=str | limit 3
syn:type=base:id
        :ctor = synapse.lib.types.Str
        :doc = A base type for ID strings.
        :extmodel = false
        :opts = {'enums': None, 'regex': None, 'lower': False, 'strip': True, 'upper': False, 'replace': (), 'mapping': None, 'onespace': False, 'globsuffix': False}
        :parent = str
syn:type=str:lower
        :ctor = synapse.lib.types.Str
        :doc = A case insensitive string.
        :extmodel = false
        :opts = {'enums': None, 'regex': None, 'lower': True, 'strip': True, 'upper': False, 'replace': (), 'mapping': None, 'onespace': False, 'globsuffix': False}
        :parent = str
syn:type=str:upper
        :ctor = synapse.lib.types.Str
        :doc = A case insensitive string normalized to upper case.
        :extmodel = false
        :opts = {'enums': None, 'regex': None, 'lower': False, 'strip': True, 'upper': True, 'replace': (), 'mapping': None, 'onespace': False, 'globsuffix': False}
        :parent = str
```

> [!TIP]
> Sub-types (`syn:type:parent`) are derived from a base type, but may have:
>
> - a specific purpose (e.g., it is helpful to distinguish strings that are HTTP header names from other arbitrary strings); and / or
> - additional (or alternate) constraints (`:opts`) on how the string can look and how it is normalized. For example, a Society for Worldwide Interbank Financial Telecommunication (SWIFT) Bank Identifier Code (BIC) used for routing financial transactions is a string, but one that has a specific format. An `econ:bank:swift:bic` in Synapse extends (is a `subof`) the `str` type that uses a regular expression (regex) to ensure that only properly formatted BIC values are created.

#### Forms

Display all forms:

```stormdoc
storm> syn:form | limit 3
syn:form=auth:passwd
        :doc = A password string.
        :extmodel = false
        :interfaces = ['auth:credential', 'crypto:hashable', 'meta:observable']
        :runt = false
        :type = auth:passwd
syn:form=syn:tag
        :doc = The base type for a synapse tag.
        :extmodel = false
        :runt = false
        :type = syn:tag
syn:form=meta:topic
        :doc = A topic string.
        :extmodel = false
        :interfaces = ['risk:targetable']
        :runt = false
        :type = meta:topic
```

Display a specific form:

```stormdoc
storm> syn:form=inet:ip
syn:form=inet:ip
        :doc = An IPv4 or IPv6 address.
        :extmodel = false
        :interfaces = ['meta:usable', 'meta:observable', 'geo:locatable']
        :runt = false
        :type = inet:ip
```

Display all of the properties of a specific form:

```stormdoc
storm> syn:prop:form=inet:ip | limit 3
syn:prop=inet:ip
        :array = false
        :doc = An IPv4 or IPv6 address.
        :extmodel = false
        :form = inet:ip
        :type = ['inet:ip']
syn:prop=inet:ip:asn
        :array = false
        :base = asn
        :computed = false
        :doc = The ASN to which the IP address is currently assigned.
        :extmodel = false
        :form = inet:ip
        :relname = asn
        :type = ['inet:asn']
syn:prop=inet:ip:type
        :array = false
        :base = type
        :computed = false
        :doc = The type of IP address (e.g., private, multicast, etc.).
        :extmodel = false
        :form = inet:ip
        :relname = type
        :type = ['str:lower']
```

> [!TIP]
> A form's properties include its primary and secondary properties. Because meta properties (`.created` and `.updated`) exist on every form, Synapse does not include them for purposes of generating runt nodes.

Display a specific property of a specific form:

```stormdoc
storm> syn:prop=inet:ip:place:loc
syn:prop=inet:ip:place:loc
        :array = false
        :base = loc
        :computed = false
        :doc = The geopolitical location where the IP address was located.
        :extmodel = false
        :form = inet:ip
        :relname = place:loc
        :type = ['loc']
```

Display all of the forms that are tagged `#cno.threat.sparkling_unicorn`:

```stormdoc
storm> #cno.threat.sparkling_unicorn $form=$node.form -> { syn:form=$form } | uniq
syn:form=inet:fqdn
        :doc = A Fully Qualified Domain Name (FQDN).
        :extmodel = false
        :interfaces = ['meta:usable', 'meta:observable']
        :runt = false
        :type = inet:fqdn
syn:form=inet:ip
        :doc = An IPv4 or IPv6 address.
        :extmodel = false
        :interfaces = ['meta:usable', 'meta:observable', 'geo:locatable']
        :runt = false
        :type = inet:ip
syn:form=crypto:hash:sha256
        :doc = A hex encoded SHA256 hash.
        :extmodel = false
        :interfaces = ['crypto:hash', 'meta:observable']
        :runt = false
        :type = crypto:hash:sha256
```

The query above assigns the variable `$form` to each node's form, uses [Raw Pivot Syntax](storm_ref_pivot.md#raw-pivot-syntax) to pivot to the associated `syn:form` runt nodes, and deduplicates the results.

#### Properties

Display all properties:

```stormdoc
storm> syn:prop | limit 3
syn:prop=auth:passwd
        :array = false
        :doc = A password string.
        :extmodel = false
        :form = auth:passwd
        :type = ['auth:passwd']
syn:prop=auth:passwd:md5
        :array = false
        :base = md5
        :computed = true
        :doc = The MD5 hash of the password.
        :extmodel = false
        :form = auth:passwd
        :relname = md5
        :type = ['crypto:hash:md5']
syn:prop=auth:passwd:sha1
        :array = false
        :base = sha1
        :computed = true
        :doc = The SHA1 hash of the password.
        :extmodel = false
        :form = auth:passwd
        :relname = sha1
        :type = ['crypto:hash:sha1']
```

Display all properties that are **computed** by Synapse:

```stormdoc
storm> syn:prop:computed=true | limit 3
syn:prop=auth:passwd:md5
        :array = false
        :base = md5
        :computed = true
        :doc = The MD5 hash of the password.
        :extmodel = false
        :form = auth:passwd
        :relname = md5
        :type = ['crypto:hash:md5']
syn:prop=auth:passwd:sha1
        :array = false
        :base = sha1
        :computed = true
        :doc = The SHA1 hash of the password.
        :extmodel = false
        :form = auth:passwd
        :relname = sha1
        :type = ['crypto:hash:sha1']
syn:prop=auth:passwd:sha256
        :array = false
        :base = sha256
        :computed = true
        :doc = The SHA256 hash of the password.
        :extmodel = false
        :form = auth:passwd
        :relname = sha256
        :type = ['crypto:hash:sha256']
```

> [!TIP]
> **Computed** properties are secondary properties that are derived or extracted from a node's primary property. Synapse computes and sets these properties automatically. Because they are based on the node's primary property, computed properties are read-only and cannot be edited.

Display all properties that are arrays:

```stormdoc
storm> syn:prop:array=true | limit 3
syn:prop=meta:story:ids
        :array = true
        :base = ids
        :computed = false
        :doc = An array of alternate IDs for the story.
        :extmodel = false
        :form = meta:story
        :relname = ids
        :type = ['base:id']
syn:prop=meta:story:supersedes
        :array = true
        :base = supersedes
        :computed = false
        :doc = An array of story versions which are superseded by this story.
        :extmodel = false
        :form = meta:story
        :relname = supersedes
        :type = ['meta:story']
syn:prop=meta:story:topics
        :array = true
        :base = topics
        :computed = false
        :doc = The topics discussed in the story.
        :extmodel = false
        :form = meta:story
        :relname = topics
        :type = ['meta:topic']
```

Display all properties that can be of a specific type (e.g., an IP address / `inet:ip`):

```stormdoc
storm> syn:prop:type*[=inet:ip] | limit 3
syn:prop=crypto:x509:cert:identities:ips
        :array = true
        :base = ips
        :computed = false
        :doc = The fused list of IP addresses identified by the cert CN and SANs.
        :extmodel = false
        :form = crypto:x509:cert
        :relname = identities:ips
        :type = ['inet:ip']
syn:prop=inet:dns:a:ip
        :array = false
        :base = ip
        :computed = true
        :doc = The IPv4 address returned in the A record.
        :extmodel = false
        :form = inet:dns:a
        :relname = ip
        :type = ['inet:ip']
syn:prop=inet:dns:aaaa:ip
        :array = false
        :base = ip
        :computed = true
        :doc = The IPv6 address returned in the AAAA record.
        :extmodel = false
        :form = inet:dns:aaaa
        :relname = ip
        :type = ['inet:ip']
```

> [!TIP]
> All properties in Synapse must have a type, and any property can optionally be declared with more than one type. This means that property types are arrays, and you need to use [array syntax](storm_ref_lift.md#lift-by-arrays) to query them.

#### Interfaces

Display all interfaces:

```stormdoc
storm> syn:interface | limit 3
syn:interface=auth:credential
        :doc = An interface implemented by authentication credential forms.
syn:interface=meta:observable
        :doc = Properties common to forms which can be observed.
syn:interface=meta:havable
        :doc = An interface used to describe items that can be possessed by an entity.
```

Display a specific interface:

```stormdoc
storm> syn:interface=meta:taxonomy
syn:interface=meta:taxonomy
        :doc = Properties common to taxonomies.
```

Display all **forms** that implement a specific interface (e.g., `inet:proto:request`):

```stormdoc
storm> syn:form:interfaces*[=inet:proto:request] | limit 3
syn:form=inet:dns:request
        :doc = A DNS protocol request.
        :extmodel = false
        :interfaces = ['inet:proto:request', 'base:event', 'meta:causal', 'inet:proto:link']
        :runt = false
        :type = inet:dns:request
syn:form=inet:http:request
        :doc = A single HTTP request.
        :extmodel = false
        :interfaces = ['inet:proto:request', 'base:event', 'meta:causal', 'inet:proto:link']
        :runt = false
        :type = inet:http:request
syn:form=inet:wifi:login
        :doc = An authentication event for a Wi-Fi network.
        :extmodel = false
        :interfaces = ['inet:proto:login', 'inet:proto:request', 'base:event', 'meta:causal', 'inet:proto:link']
        :runt = false
        :type = inet:wifi:login
```

Display all **interfaces** that implement a specific interface (e.g., `base:activity`):

```stormdoc
storm> syn:interface:interfaces*[=base:activity] | limit 3
syn:interface=meta:schedulable
        :doc = An interface implemented by activities which may be scheduled.
        :interfaces = ['base:activity']
syn:interface=entity:activity
        :doc = Properties common to activity carried out by an actor.
        :interfaces = ['base:activity', 'entity:action']
syn:interface=entity:participable
        :doc = An interface implemented by activities which an actor may participate in.
        :interfaces = ['base:activity']
```

> [!TIP]
> The queries above will return results (`syn:form` or `syn:interface` runt nodes) that implement the interface either directly or recursively (i.e., as the result of implementing another interface that implements the interface you are querying).

Display all forms **referenced by** a specific form (i.e., which properties of this form are **also** forms):

```stormdoc
storm> syn:prop:form=file:bytes :type -> syn:type -> syn:form | limit 3
syn:form=file:bytes
        :doc = A file.
        :extmodel = false
        :interfaces = ['meta:usable', 'meta:observable']
        :runt = false
        :type = file:bytes
syn:form=crypto:hash:md5
        :doc = A hex encoded MD5 hash.
        :extmodel = false
        :interfaces = ['crypto:hash', 'meta:observable']
        :runt = false
        :type = crypto:hash:md5
syn:form=crypto:hash:sha1
        :doc = A hex encoded SHA1 hash.
        :extmodel = false
        :interfaces = ['crypto:hash', 'meta:observable']
        :runt = false
        :type = crypto:hash:sha1
```

Display all forms that **reference** a specific form (i.e., which forms **have** this form as a secondary property):

```stormdoc
storm> syn:form=file:bytes :type -> syn:type -> syn:prop:type | limit 3
syn:prop=meta:story:file
        :array = false
        :base = file
        :computed = false
        :doc = The file containing the story contents.
        :extmodel = false
        :form = meta:story
        :relname = file
        :type = ['file:bytes']
syn:prop=biz:rfp:file
        :array = false
        :base = file
        :computed = false
        :doc = The file containing the RFP contents.
        :extmodel = false
        :form = biz:rfp
        :relname = file
        :type = ['file:bytes']
syn:prop=crypto:currency:transaction:contract:input
        :array = false
        :base = input
        :computed = false
        :doc = Input value to a smart contract call.
        :extmodel = false
        :form = crypto:currency:transaction
        :relname = contract:input
        :type = ['file:bytes']
```

#### Extended Model

Types, forms, properties, and tag properties which have been added to a Cortex as custom (extended) model elements all carry an `:extmodel` property which is set to `true`.

Display all extended forms:

```stormdoc
storm> syn:form:extmodel=true
syn:form=_visi:place
        :doc = A place Visi has been.
        :extmodel = true
        :runt = false
        :type = _visi:place
```

Display all extended types:

```stormdoc
storm> syn:type:extmodel=true
syn:type=_visi:place
        :ctor = synapse.lib.types.Str
        :doc = A place Visi has been.
        :extmodel = true
        :opts = {'enums': None, 'regex': None, 'lower': False, 'strip': True, 'upper': False, 'replace': (), 'mapping': None, 'onespace': False, 'globsuffix': False}
        :parent = str
syn:type=_visi:score
        :ctor = synapse.lib.types.Int
        :doc = A score assigned by Visi.
        :extmodel = true
        :opts = {'size': 8, 'signed': True, 'enums': None, 'enums:strict': True, 'fmt': '%d', 'min': None, 'max': None, 'ismin': False, 'ismax': False}
        :parent = int
```

Display all extended properties:

```stormdoc
storm> syn:prop:extmodel=true
syn:prop=_visi:place
        :array = false
        :doc = A place Visi has been.
        :extmodel = true
        :form = _visi:place
        :type = ['_visi:place']
syn:prop=inet:fqdn:_visi:seen
        :array = false
        :base = seen
        :computed = false
        :doc = Set to true if Visi has seen the FQDN.
        :extmodel = true
        :form = inet:fqdn
        :relname = _visi:seen
        :type = ['bool']
```

Display all extended tag properties:

```stormdoc
storm> syn:tagprop:extmodel=true
syn:tagprop=_visi:score
        :doc = A score assigned by Visi.
        :extmodel = true
        :type = int
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

```stormdoc
storm> syn:tag=cno.infra.anon.tor
syn:tag=cno.infra.anon.tor
        :base = tor
        :depth = 3
        :doc = Infrastructure associated with the TOR network.
        :title = TOR infrastructure
        :up = cno.infra.anon
```

Lift all root tags:

```stormdoc
storm> syn:tag:depth=0
syn:tag=cno
        :base = cno
        :depth = 0
```

Lift all tags one level "down" from the specified tag:

```stormdoc
storm> syn:tag:up=cno.infra.anon
syn:tag=cno.infra.anon.tor
        :base = tor
        :depth = 3
        :doc = Infrastructure associated with the TOR network.
        :title = TOR infrastructure
        :up = cno.infra.anon
syn:tag=cno.infra.anon.vpn
        :base = vpn
        :depth = 3
        :doc = A server representing an anonymous VPN service, or the associated IP address. Alternately, an FQDN explicitly denoting an anonymous VPN that resolves to the associated IP.
        :title = Anonymous VPN
        :up = cno.infra.anon
```

Lift all tags that start with a given prefix, regardless of depth:

```stormdoc
storm> syn:tag^=cno.infra
syn:tag=cno.infra
        :base = infra
        :depth = 1
        :doc = Top-level tag for infrastructure.
        :title = Infrastructure
        :up = cno
syn:tag=cno.infra.anon
        :base = anon
        :depth = 2
        :doc = Top-level tag for anonymization services.
        :title = Anonymization services
        :up = cno.infra
syn:tag=cno.infra.anon.tor
        :base = tor
        :depth = 3
        :doc = Infrastructure associated with the TOR network.
        :title = TOR infrastructure
        :up = cno.infra.anon
syn:tag=cno.infra.anon.vpn
        :base = vpn
        :depth = 3
        :doc = A server representing an anonymous VPN service, or the associated IP address. Alternately, an FQDN explicitly denoting an anonymous VPN that resolves to the associated IP.
        :title = Anonymous VPN
        :up = cno.infra.anon
```

Lift all tags that share the same base (rightmost) element:

```stormdoc
storm> syn:tag:base=salt_typhoon
syn:tag=rep.uscisa.salt_typhoon
        :base = salt_typhoon
        :depth = 2
        :doc = Indicator or activity US-CISA calls (or associates with) Salt Typhoon.
        :title = Salt Typhoon (US-CISA)
        :up = rep.uscisa
syn:tag=rep.microsoft.salt_typhoon
        :base = salt_typhoon
        :depth = 2
        :doc = Indicator or activity Microsoft calls (or associates with) Salt Typhoon.
        :title = Salt Typhoon (Microsoft)
        :up = rep.microsoft
```
