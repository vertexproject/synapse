



.. highlight:: none

.. _data-model-form-categories:

Data Model - Form Categories
============================

Synapse forms can be broadly grouped into conceptual categories based on the object a form is meant to represent - an :ref:`form-entity`, a :ref:`form-relationship`, or an :ref:`form-event`.

Synapse forms can also be broadly grouped based on how their primary properties (``<form> = <valu>``) are structured or formed.

Recall that ``<form> = <valu>`` must be unique for all forms of a given type. In other words, the ``<valu>`` must be defined so that it uniquely identifies any given node of that form; it represents that form’s "essence" or "thinghood" in a way that allows the unambiguous deconfliction of all possible nodes of that form.

Conceptually speaking, the general categories of forms in Synapse are:

- `Simple Form`_
- `Composite (Comp) Form`_
- `GUID Form`_
- `Digraph (Edge) Form`_
- `Generic Form`_

This list represents a conceptual framework to understand the Synapse data model.

.. _form-simple:

Simple Form
-----------

A simple form refers to a form whose primary property is a single typed ``<valu>``. They are commonly used to represent an :ref:`form-entity`, and so tend to be the most readily understood from a modeling perspective.

**Examples**

- **IP addresses.** An IP address (IPv4 or IPv6) must be unique within its address space and can be defined by the address itself: ``inet:ipv4 = 1.2.3.4``. Secondary properties include the associated Autonomous System number and whether the IP belongs to a specialized or reserved group (e.g., private, multicast, etc.).

- **Email addresses.** An email address must be unique in order to route email to the correct account / individual and can be defined by the address itself: ``inet:email = joe.smith@company.com``. Secondary properties include the domain where the account receives mail and the username for the account.

.. _form-comp:

Composite (Comp) Form
---------------------

A composite (comp) form is one where the primary property is a comma-separated list of two or more typed ``<valu>`` elements. While no single element makes the form unique, a combination of elements can uniquely define a given node of that form. Comp forms are often (though not universally) used to represent a :ref:`form-relationship`.

**Examples**

- **Fused DNS A records.** A DNS A record can be uniquely defined by the combination of the domain (``inet:fqdn``) and the IP address (``inet:ipv4``) in the A record. Synapse’s ``inet:dns:a`` form represents the knowledge that a given domain has ever resolved to a specific IP (fused knowledge): ``inet:dns:a = (woot.com, 1.2.3.4)``.

- **Web-based accounts.** An account at an online service (such as Github or Gmail) can be uniquely defined by the combination of the domain where the service is hosted (``inet:fqdn``) and the unique user ID (``inet:user``) used to identify the account: ``inet:web:acct = (twitter.com, joeuser)``.

- **Social networks.** Many online services allow users to establish relationships with other users of that service. These relationships may be one-way (you can follow someone on Twitter) or two-way (you can mutually connect with someone on LinkedIn). A given one-way social network relationship can be uniquely defined by the two users (``inet:web:acct``) involved in the relationship: ``inet:web:follows = ((twitter.com,alice), (twitter.com,bob))``. (A two-way relationship can be defined by two one-way relationships.)
  
  Note that each of the elements in the ``inet:web:follows`` comp form is itself a comp form (``inet:web:acct``).
  
- **Subsidiaries.** An organization / sub-organization relationship (e.g., corporation / subsidiary, company / division, government / ministry, etc.) can be uniquely defined by the specific parent / child entities (``ou:org``) involved: ``ou:suborg = (084e295272e839afcf3f1fe10c6c97b9, 237e88a35439fdb566d909e291339154)``.
  
  Note that each of the organizations (``ou:org``) in the relationship is represented by a 128-bit Globally Unique Identifier (GUID), each an example of a `GUID Form`_.

.. _form-guid:

GUID Form
---------

A GUID (Globally Unique Identifier) form is uniquely defined by a machine-generated 128-bit number. GUIDs account for cases where it is impossible to uniquely define a thing based on a specific set of properties no matter how many individual elements are factored into a comp form. A GUID form can be considered a special case of a :ref:`form-simple` where the typed ``<valu>`` is of type ``<guid>``.

While certain types of data **could** be represented by a comp form based on a sufficient number of properties of the data, there are advantages to using a GUID instead:

- in a comp form, the elements used to create the primary property are **required** in order to create a node of that form. It is not uncommon for real world data to be incomplete. Using a GUID allows all of those elements to be defined as optional secondary properties, so the node can be created with as much (or as little) data as is available.
- Some data sources are such that individual records can be considered unique a priori. This often applies to event-type forms for large quantities of events. In this case it sufficient to distinguish the nodes from each other using a GUID as opposed to being uniqued over a subset of properties.
- There is a potential performance benefit to representing forms using GUIDs because they are guaranteed to be unique for a given Cortex. In particular, when ingesting data presumed to be unique, creating GUID-based forms vs comp forms eliminates the need to parse and deconflict nodes before they are created. This benefit can be significant over large data sets.

**Examples**

- **People.** Synapse uses a GUID as the primary property for a person (``ps:person``) node. There is no single property or set of properties that uniquely and unambiguously define a person. A person’s full name, date of birth, or place of birth (or the combination of all three) are not guaranteed to be fully unique across an entire population. Identification numbers (such as Social Security or National ID numbers) are country-specific, and not all countries require each citizen to have an ID number. Even a person’s genome is not guaranteed to be unique (such as in the case of identical twins).

  Secondary properties include the person’s name (including given, middle, or family names) and date of birth.

- **Host execution / sandbox data.** The ability to model detailed behavior of a process executing on a host (or in a sandbox) is important for a range of disciplines, including incident response and malware analysis. Modeling this data is challenging because of the number of effects that execution may have on a system (files read, written, or deleted; network activity initiated). Even if we focus on a specific effect ("a process wrote a new file to disk"), there are still a number of details that may define a "unique instance" of "process writes file": the specific host (``it:host``) where the process ran, the program (``file:bytes``) that wrote the file to disk, the process (``file:bytes``) that launched the program, the time the execution occurred, the file that was written (``file:bytes``), the file’s path (``file:path``), and so on. While all of these elements could be used to create a comp form, in the "real world" not all of this data may be available in all cases, making a GUID a better option for forms such as ``it:exec:file.write``.

- **Unique DNS responses.** Similar to host execution data, an individual DNS response to a request could potentially be uniqued based on a comp form containing multiple elements (time, DNS query, server that replied, response code, specific response, etc.) However, the same issues described above apply and it is preferable to use a GUID for forms such as ``inet:dns:request`` or ``inet:dns:answer``.

.. _form-edge:

Digraph (Edge) Form
-------------------

A digraph form ("edge" form) is a specialized :ref:`form-comp` whose primary property value consists of two ``<form>,<valu>`` pairs  (``ndefs``). It is a specialized relationship form that can be used to link two arbitrary forms in a generic relationship.

Recall that a :ref:`form-relationship` can be the hypergraph equivalent of an edge connecting two nodes in a directed graph. A standard relationship form (such as ``inet:dns:a``) represents a specific relationship ("has DNS A record for") between two explicitly typed nodes (``inet:fqdn`` and ``inet:ipv4``). Synapse's strong typing and type safety ensure that all primary and secondary properties are explicitly typed, which facilitates both normalization of data and the ability to readily pivot across disparate properties that share the same data type. However, this means that types for all primary and secondary properties must be defined in the data model ahead of time.

Some relationships are generic enough to apply to a wide variety of forms. One example is "has": <thing a> "has" <thing b>. While it is possible to explicitly define typed forms for every possible variation of that relationship ("person has telephone number", "company has social media account"), this would mean the data model must be updated every time a new variation of what is essentially the same "has" relationship is identified.

Synapse addresses this issue by defining a node’s **ndef** ("node definition, or ``<form>,<valu>`` pair) as a data :ref:`data-types`. Properties of type ``ndef`` can thus effectively specify both a type (``<form>``) and a ``<valu>`` at the time of node creation. This allows for generic relationship forms that can link two "arbitrary" node types.

With the addition of a timestamp, a digraph ("edge") form becomes a "timeedge" form that can represent "when" a specific digraph relationship occurred or existed.

**Examples**

**"Has".** There are a number of use cases where it is helpful to note that a thing owns or possesses ("has") another thing. Examples include:

- A company (``ou:org``) owns a corporate office (``geo:place``, ``mat:item``), a range of IP addresses (``inet:cidr4``), or a delivery van (``mat:item``).
- A person (``ps:person``) has an email address (``inet:email``) or telephone number (``tel:phone``).
  
In some cases the relationship of a person or organization owning or possessing ("having") a resource (a social media account, or an email address) may be indirectly apparent via existing pivots in the hypergraph. For example, an organization (``ou:org``) may have a name that is shared by a social media account (``ou:org:name -> inet:web:acct:realname``) where the social media account also references the organization’s web page (``inet:web:acct:webpage -> ou:org:url``). However, it may be desirable to more tightly link an "owning" entity to things that it "has". In addition, there may be things that an organization or person "has" that are not as easily identified via primary and secondary property pivots. In these cases the "has" form can represent this relationship between the "owning" entity and the arbitrary thing owned.
  
An example of an organization (``ou:org``) "having" an office location (``geo:place``) is shown in the sample ``edge:has`` node below. Note that both ``ou:org`` nodes and ``geo:place`` nodes are GUID forms: ``edge:has=((ou:org, b604a5a269e5dab3e8d6d57b0e7509d0), (geo:place, 594e74be7ce9b719cadf788cc631ddfb))``.

**"References".** There are a number of use cases where it is helpful to note that a thing “references” another thing. Examples include:

- A binary executable (``file:bytes``) that contains interesting strings (``it:dev:str``).
- A report (``media:news``) that contains threat indicators, such as hashes (``hash:sha256``), domains (``inet:fqdn``), email addresses (``inet:email``), etc.
- A photograph (``file:bytes``) that depicts a person (``ps:person``), a location (``geo:place``), a landmark (``mat:item``), etc.
- A news article (``media:news``) that describes an event such as a conference (``ou:conference``).

An example of an article (such as a whitepaper) referencing a malicious domain is shown in the sample ``edge:refs`` node below. A ``media:news`` node is a GUID form: ``edge:refs=((media:news, 1f0c86b779a8e5acae21fec6c67a51c7), (inet:fqdn, stratforglobal.net))``

**"Went to".** "Went to" (``edge:wentto``) is an example of a timeedge form that can represent that a thing (often a person, potentially an object such as a bus) traveled to a place (a city, an office building, a set of geolocation coordinates) or that a person attended an event (a conference, a party) at a particular time.

.. _form-generic:

Generic Form
------------

The Synapse data model includes a number of "generic" forms that can be used to represent metadata and / or arbitrary data. 

Arbitrary Data
++++++++++++++

In an ideal world, all data represented in a Synapse hypergraph would be accurately modeled using an appropriate form to property capture the data’s unique (primary property) and contextual (secondary property) characteristics. However, designing an appropriate data model may require extended discussion, subject matter expertise, and testing against "real world" data - not to mention development time to implement model changes. In addition, there are use cases where data that needs to be added to a Cortex for reference or analysis purposes, but simply does not have sufficient detail to be represented accurately, even if appropriate data forms exist.

While the use of generic forms is not ideal (the representation of data is lossy, which may impact effective analysis), these forms allow for the addition of arbitrary data to a hypergraph, either because that is the only way the data can be represented; or because an appropriate model does not yet exist but the data is needed now.

Generic forms such as ``graph:node``, ``graph:edge``, ``graph:timeedge`` and ``graph:event`` can be used for this purpose. Similarly, the generic ``graph:cluster`` node can be used to link (via ``edge:refs`` forms) a set of nodes of arbitrary size ("someone says these things are all related") in the absence of greater detail.

Metadata
++++++++

The Synapse data model includes forms such as ``meta:source`` and ``meta:seen`` that can be used to track data sources (such as a sensor or a third-party service) and the knowledge that a particular piece of data (node, ``ndef``) was observed by or from a particular source (``meta:source``).
