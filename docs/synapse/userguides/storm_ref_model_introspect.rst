.. highlight:: none


.. _storm-ref-model-introspect:

Storm Reference - Model Introspection
=====================================

This section provides a brief overview / tutorial of some basic Storm queries to allow introspection / navigation of Synapse's:

- `Data Model`_
- `Analytical Model`_

The sample queries below are meant to help users new to Synapse and Storm get started examining forms and tags within a Cortex. The queries all use standard Storm syntax and operations (such as pivots). For more detail on using Storm, see :ref:`storm-ref-intro` and related Storm topics.

Data Model
----------

Analysts working with the data in the Synapse hypergraph will quickly become familiar with the forms they work with most often. However, as the model expands - or when first learning Synapse - it is helpful to be able to easily reference forms that may be less familiar, as well as how different forms relate to each other.

While the data model can be referenced within the Synapse source code_ or via the auto-generated :ref:`dm-index` documentation, it can be inconvenient to stop in the middle of an analytical workflow to search for the correct documentation. It is even more challenging to stop and browse through extensive documentation when you’re not sure what you’re looking for (or whether an appropriate form exists for your needs).

For these reasons Synapse supports **data model introspection** within the Synapse hypergraph itself - that is, the Synapse data model is itself data stored within the Cortex. Introspection allows users to obtain the model definition for a given Cortex at run-time. The model definition contains a list of all native and custom types, forms, and properties supported by the current Cortex.

These model elements are generated as nodes in the Cortex from the current Synapse data model when a Cortex is initialized or when a new module is loaded. As nodes, they can be lifted, filtered, and pivoted across just like other nodes. However, the model-specific nodes do not persist permanently in storage and they cannot be modified (edited) or tagged. Because they are generated at run-time they are known as run-time nodes or **runt nodes.**

The following runt node forms are used to represent the Synapse data model for types, forms, and properties, respectively.

- ``syn:type``
- ``syn:form``
- ``syn:prop``

As nodes within the Cortex, these forms can be lifted, filtered, and pivoted across using the Storm query language, just like any other nodes (with the exception of editing or tagging). Refer to the various Storm documents for details on Storm syntax. A few simple example queries are provided below to illustrate some common operations for model introspection.

Example Queries
+++++++++++++++

- Display all current types / forms / properties:


::

    storm> syn:type | limit 2
    syn:type=int
            :ctor = synapse.lib.types.Int
            :doc = The base 64 bit signed integer type.
            :opts = {'size': 8, 'signed': True, 'fmt': '%d', 'min': None, 'max': None, 'ismin': False, 'ismax': False}
            .created = 2023/10/05 21:47:42.639
    syn:type=float
            :ctor = synapse.lib.types.Float
            :doc = The base floating point type.
            :opts = {'fmt': '%f', 'min': None, 'minisvalid': True, 'max': None, 'maxisvalid': True}
            .created = 2023/10/05 21:47:42.639




::

    storm> syn:form | limit 2
    syn:form=inet:dns:a
            :doc = The result of a DNS A record lookup.
            :runt = false
            :type = inet:dns:a
            .created = 2023/10/05 21:47:42.653
    syn:form=inet:dns:aaaa
            :doc = The result of a DNS AAAA record lookup.
            :runt = false
            :type = inet:dns:aaaa
            .created = 2023/10/05 21:47:42.653




::

    storm> syn:prop | limit 2
    syn:prop=.seen
            :base = .seen
            :doc = The time interval for first/last observation of the node.
            :extmodel = false
            :relname = .seen
            :ro = false
            :type = ival
            :univ = true
            .created = 2023/10/05 21:47:42.666
    syn:prop=.created
            :base = .created
            :doc = The time the node was created in the cortex.
            :extmodel = false
            :relname = .created
            :ro = true
            :type = time
            :univ = true
            .created = 2023/10/05 21:47:42.666



- Display all types that are sub-types of 'string':


::

    storm> syn:type:subof = str | limit 2
    syn:type=ou:sic
            :ctor = synapse.lib.types.Str
            :doc = The four digit Standard Industrial Classification Code.
            :opts = {'enums': None, 'regex': '^[0-9]{4}$', 'lower': False, 'strip': False, 'replace': (), 'onespace': False, 'globsuffix': False}
            :subof = str
            .created = 2023/10/05 21:47:42.686
    syn:type=ou:naics
            :ctor = synapse.lib.types.Str
            :doc = North American Industry Classification System codes and prefixes.
            :opts = {'enums': None, 'regex': '^[1-9][0-9]{1,5}?$', 'lower': False, 'strip': True, 'replace': (), 'onespace': False, 'globsuffix': False}
            :subof = str
            .created = 2023/10/05 21:47:42.686



- Display a specific type:


::

    storm> syn:type = inet:fqdn
    syn:type=inet:fqdn
            :ctor = synapse.models.inet.Fqdn
            :doc = A Fully Qualified Domain Name (FQDN).
            .created = 2023/10/05 21:47:42.699



- Display a specific form:


::

    storm> syn:form = inet:fqdn
    syn:form=inet:fqdn
            :doc = A Fully Qualified Domain Name (FQDN).
            :runt = false
            :type = inet:fqdn
            .created = 2023/10/05 21:47:42.711



- Display a specific property of a specific form:


::

    storm> syn:prop = inet:ipv4:loc
    syn:prop=inet:ipv4:loc
            :base = loc
            :doc = The geo-political location string for the IPv4.
            :extmodel = false
            :form = inet:ipv4
            :relname = loc
            :ro = false
            :type = loc
            :univ = false
            .created = 2023/10/05 21:47:42.723



- Display a specific form and all its secondary properties (including universal properties):


::

    storm> syn:prop:form = inet:fqdn | limit 2
    syn:prop=inet:fqdn
            :doc = A Fully Qualified Domain Name (FQDN).
            :extmodel = false
            :form = inet:fqdn
            :type = inet:fqdn
            .created = 2023/10/05 21:47:42.736
    syn:prop=inet:fqdn.seen
            :base = .seen
            :doc = The time interval for first/last observation of the node.
            :extmodel = false
            :form = inet:fqdn
            :relname = .seen
            :ro = false
            :type = ival
            :univ = false
            .created = 2023/10/05 21:47:42.736



- Display all properties whose type is ``inet:fqdn``:


::

    storm> syn:prop:type = inet:fqdn | limit 2
    syn:prop=inet:dns:a:fqdn
            :base = fqdn
            :doc = The domain queried for its DNS A record.
            :extmodel = false
            :form = inet:dns:a
            :relname = fqdn
            :ro = true
            :type = inet:fqdn
            :univ = false
            .created = 2023/10/05 21:47:42.763
    syn:prop=inet:dns:aaaa:fqdn
            :base = fqdn
            :doc = The domain queried for its DNS AAAA record.
            :extmodel = false
            :form = inet:dns:aaaa
            :relname = fqdn
            :ro = true
            :type = inet:fqdn
            :univ = false
            .created = 2023/10/05 21:47:42.763



- Display all forms **referenced by** a specific form (i.e., the specified form contains secondary properties that are themselves forms):


::

    storm> syn:prop:form = inet:whois:rec :type -> syn:form
    syn:form=inet:whois:rec
            :doc = A domain whois record.
            :runt = false
            :type = inet:whois:rec
            .created = 2023/10/05 21:47:42.796
    syn:form=inet:fqdn
            :doc = A Fully Qualified Domain Name (FQDN).
            :runt = false
            :type = inet:fqdn
            .created = 2023/10/05 21:47:42.796
    syn:form=inet:whois:rar
            :doc = A domain registrar.
            :runt = false
            :type = inet:whois:rar
            .created = 2023/10/05 21:47:42.796
    syn:form=inet:whois:reg
            :doc = A domain registrant.
            :runt = false
            :type = inet:whois:reg
            .created = 2023/10/05 21:47:42.796



- Display all forms that **reference** a specific form (i.e., the specified form is a secondary property of another form):


::

    storm> syn:form = inet:whois:rec -> syn:prop:type :form -> syn:form
    syn:form=inet:whois:contact
            :doc = An individual contact from a domain whois record.
            :runt = false
            :type = inet:whois:contact
            .created = 2023/10/05 21:47:42.830
    syn:form=inet:whois:rec
            :doc = A domain whois record.
            :runt = false
            :type = inet:whois:rec
            .created = 2023/10/05 21:47:42.830
    syn:form=inet:whois:recns
            :doc = A nameserver associated with a domain whois record.
            :runt = false
            :type = inet:whois:recns
            .created = 2023/10/05 21:47:42.830



Analytical Model
----------------

As the number of tags used in the hypergraph increases, analysts must be able to readily identify tags, tag hierarchies, and the precise meaning of individual tags so they can be applied and interpreted correctly.

Unlike the runt nodes used for the Synapse data model, the ``syn:tag`` nodes that represent tags are regular objects in the Cortex that can be lifted, filtered, and pivoted across (as well as edited, tagged, and deleted) just like any other nodes. In a sense it is possible to perform **"analytical model introspection"** by examining the nodes representing a Cortex's analytical model (i.e., tags).

Lifting, filtering, and pivoting across ``syn:tag`` nodes is performed using the standard Storm query syntax; refer to the various Storm documents for details on using Storm. See also the ``syn:tag`` section of :ref:`storm-ref-type-specific` for additional details on working with ``syn:tag`` nodes.

A few simple example queries are provided below to illustrate some common operations for working with tags. As Synapse does not include any pre-populated ``syn:tag`` nodes, these examples assume you have a Cortex where some number of tags have been created.

Example Queries
+++++++++++++++

- Lift a single tag:

::

    storm> syn:tag = cno.infra.anon.tor
    syn:tag=cno.infra.anon.tor
            :base = tor
            :depth = 3
            :doc = Various types of Tor infrastructure, including: a server representing a Tor service or the associated IP address; a host known to be a Tor node / hosting a Tor service; contact information associated with an entity responsible for a given Tor node.
            :title = Tor Infrastructure
            :up = cno.infra.anon
            .created = 2023/10/05 21:47:42.866



- Lift all root tags:


::

    storm> syn:tag:depth = 0
    syn:tag=cno
            :base = cno
            :depth = 0
            .created = 2023/10/05 21:47:42.858



- Lift all tags one level "down" from the specified tag:


::

    storm> syn:tag:up = cno.infra.anon
    syn:tag=cno.infra.anon.tor
            :base = tor
            :depth = 3
            :doc = Various types of Tor infrastructure, including: a server representing a Tor service or the associated IP address; a host known to be a Tor node / hosting a Tor service; contact information associated with an entity responsible for a given Tor node.
            :title = Tor Infrastructure
            :up = cno.infra.anon
            .created = 2023/10/05 21:47:42.866
    syn:tag=cno.infra.anon.vpn
            :base = vpn
            :depth = 3
            :doc = A server representing an anonymous VPN service, or the associated IP address. Alternately, an FQDN explicilty denoting an anonymous VPN that resolves to the associated IP.
            :title = Anonymous VPN
            :up = cno.infra.anon
            .created = 2023/10/05 21:47:42.869



- Lift all tags that start with a given prefix, regardless of depth:


::

    storm> syn:tag ^= cno.infra
    syn:tag=cno.infra
            :base = infra
            :depth = 1
            :doc = Top-level tag for infrastructre.
            :title = Infrastructure
            :up = cno
            .created = 2023/10/05 21:47:42.858
    syn:tag=cno.infra.anon
            :base = anon
            :depth = 2
            :doc = Top-level tag for anonymization services.
            :title = Anonymization services
            :up = cno.infra
            .created = 2023/10/05 21:47:42.862
    syn:tag=cno.infra.anon.tor
            :base = tor
            :depth = 3
            :doc = Various types of Tor infrastructure, including: a server representing a Tor service or the associated IP address; a host known to be a Tor node / hosting a Tor service; contact information associated with an entity responsible for a given Tor node.
            :title = Tor Infrastructure
            :up = cno.infra.anon
            .created = 2023/10/05 21:47:42.866
    syn:tag=cno.infra.anon.vpn
            :base = vpn
            :depth = 3
            :doc = A server representing an anonymous VPN service, or the associated IP address. Alternately, an FQDN explicilty denoting an anonymous VPN that resolves to the associated IP.
            :title = Anonymous VPN
            :up = cno.infra.anon
            .created = 2023/10/05 21:47:42.869



- Lift all tags that share the same base (rightmost) element:

::

    storm> syn:tag:base = sofacy
    syn:tag=rep.uscert.sofacy
            :base = sofacy
            :depth = 2
            :doc = Indicator or activity uscert calls (or associates with) sofacy.
            :title = sofacy(uscert)
            :up = rep.uscert
            .created = 2023/10/05 21:47:42.930
    syn:tag=rep.talos.sofacy
            :base = sofacy
            :depth = 2
            :doc = Indicator or activity talos calls (or associates with) sofacy.
            :title = sofacy(talos)
            :up = rep.talos
            .created = 2023/10/05 21:47:42.933




.. _code: https://github.com/vertexproject/synapse
