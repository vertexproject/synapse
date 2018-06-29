.. highlight:: none

Background - Data Model and Terminology
=======================================

This section covers the basic “building blocks” of the Synapse hypergraph data model. It is intended to provide an overview of the fundamentals to get you started.

**Note:** This documentation presents the data model from a User or Analyst perspective; for detailed information, see the `Data Model`_ section or the Synapse source code.

* `Background`_
* `Data Model Terminology`_
* `Nodes`_
* `Forms`_
* `Types`_
* `Tags`_

Background
----------

Recall that **Synapse is a distributed key-value hypergraph analysis framework.** That is, Synapse is a particular implementation of a hypergraph model, where an instance of a hypergraph is called a Cortex. In our brief discussion_ of graphs and hypergraphs, we pointed out some fundamental concepts related to the Synapse hypergraph implementation:

* **Everything is a node.** There are no pairwise (“two-dimensional”) edges in a hypergraph the way there are in a directed graph.

* **Tags act as hyperedges.** In a directed graph, an edge connects exactly two nodes. In Synapse, tags are labels that can be applied to an arbitrary number of nodes. These tags effectively act as an n-dimensional edge that can connect any number of nodes – a hyperedge.

* **(Almost) every navigation of the graph is a pivot.** Since there are no pairwise edges in a hypergraph, you can’t query or explore the graph by traversing its edges. Instead, navigation primarily consists of pivoting from the properties of one set of nodes to the properties of another set of nodes. (Since tags are hyperedges, there are ways to lift by or “pivot through” tags that act as “hyperedge traversal”; but most navigation is via pivots.)

To start building on those concepts, you need to understand the basic elements of the Synapse data model.

Data Model Terminology
----------------------

The fundamental concepts you should be familiar with are:

* `Nodes`_
* `Forms`_
* `Types`_
* `Tags`_

Synapse uses a query language called **Storm** to interact with data in the hypergraph. Storm allows a user to ask about, filter, and pivot around data based on node properties, values, and tags. **Understanding these structures will significantly improve your ability to use Storm and interact with Synapse data.**

Nodes
-----

A node is a unique object within the Synapse hypergraph. In Synapse nodes represent standard objects (“nouns”) such as IP addresses, files, people, bank accounts, or chemical formulas. However, in Synapse nodes also represent relationships (“verbs” - remember, what would have been an edge in a directed graph is now also a node in Synapse). It may be better to think of a node generically as a “thing” - any “thing” you want to model within Synapse (object, relationship, event) is represented as a node.

Every node consists of the following components:

* A **primary property** that consists of the form of the node (see below) plus its specific value. All primary properties (``<form> = <valu>``) must be unique for a given node type (form). For example, the primary property of the node representing the domain “woot.com” would be ``inet:fqdn = woot.com``. The uniqueness of the ``<form> = <valu>`` pair ensures there can be only one node that represents the domain “woot.com”. Because this unique pair “defines” the node, the form / value combination is also known as the node’s **ndef** (short for “node definition”).

* Various **universal properties.** As the name implies, universal properties are applicable to all nodes. Their property name is preceded by a dot ( ``.`` ) to distinguish them from form-specific properties. Examples of universal properties include:

  * ``.created``: every node is automatically assigned a ``.created`` property on formation whose value is its creation timestamp.
  * ``.seen``: can be used to assign “first observed” and “last observed” timestamps to a given node, if applicable. “When” a particular node existed or was observed is important for many types of analysis. When was a Twitter account (``inet:web:acct``) created and when was it deleted or shut down? During what time period did the domain woot.com resolve to IP 1.2.3.4 (``inet:dns:a``)?

* Various **secondary properties** (``<prop> = <valu>``) that are specific to that node type and provide additional detail about that particular node. A node representing an Internet domain will have different secondary properties than a node representing a person, which will have different secondary properties than a node representing a bank account.

**Example**

The Storm query below lifts and displays the node for the domain "woot.com".

::

  cli> storm inet:fqdn=woot.com
  
  inet:fqdn = woot.com
      .created = 2018/05/17 16:40:46.047
      :domain = com
      :host = woot
      :issuffix = False
      :iszone = True
      :zone = woot.com
  complete. 1 nodes in 1 ms (1000/sec).

In the output above:

* ``inet:fqdn = woot.com`` is the primary property (``<form> = <valu>``).
* ``.created`` is a universal property showing when the node was added to the Cortex.
* ``:domain``, ``:host``, etc. are form-specific secondary properties with their associated values (``:<prop> = <valu>``). For readability, secondary properties are displayed as **relative properties** within the namespace of the form’s primary property (e.g., ``:iszone`` as opposed to ``inet:fqdn:iszone``). The preceding colon ( ``:`` ) indicates the property is a relative property.

Forms
-----

A form is the definition of an object in the Synapse data model. If a node is an object in a Synapse hypergraph, a form is the “template” that tells you how that node should be created. In other words, if you want to create a domain (``inet:fqdn`` node) in Synapse, the ``inet:fqdn`` form tells you the proper structure for the node and the properties it can contain. ``inet:fqdn`` is a form; ``inet:fqdn = woot.com`` (``<form> = <valu>``) is a node.

The terms ‘form’ and ‘node’ are sometimes used interchangeably, but it is useful to maintain the distinction between template (form) and instance (node).

Forms are defined within the Synapse source code and their structure can be found within the appropriate Python module. For example, the ``inet:fqdn`` form is defined within the inet.py_ module. Form definitions (auto-generated from the Synapse source code) can also be found within the Synapse `Data Model`_ documents.

**Example**

Below are examples of how a form (``inet:fqdn``) is represented in both the Synapse source code (in this case, ``inet.py`) and in the auto-generated documentation.


*Synapse source code:*

::

  ('inet:fqdn', {}, (
      ('created', ('time', {'ismin': True}), {
          'doc': 'The earliest known registration (creation) date for
            The fqdn.'
      }),
      ('domain', ('inet:fqdn', {}), {
          'ro': True,
          'doc': 'The parent domain for the FQDN.',
      }),
      ('expires', ('time', {'ismax': True}), {
          'doc': 'The current expiration date for the fqdn.'
      }),
      ('host', ('str', {'lower': True}), {
          'ro': True,
          'doc': 'The host part of the FQDN.',
      }),
      ('issuffix', ('bool', {}), {
          'doc': 'True if the FQDN is considered a suffix.',
          'defval': 0,
      }),
      ('iszone', ('bool', {}), {
          'doc': 'True if the FQDN is considered a zone.',
          'defval': 0,
      }),
      ('updated', ('time', {'ismax': True}), {
          'doc': 'The last known updated date for the fqdn.'
      }),
      ('zone', ('inet:fqdn', {}), {
          'doc': 'The zone level parent for this FQDN.',
      }),
  ))

*Auto-generated user documentation:*

::

  **inet:fqdn = <inet:fqdn>**
  A Fully Qualified Domain Name (FQDN)
  
  Properties:
    inet:fqdn:created = <time>
    * The earliest known registration (creation) date for the fqdn.
    inet:fqdn:domain = <inet:fqdn>
    * The parent domain for the FQDN
    inet:fqdn:expires = <time>
    * The current expiration date for the fqdn.
    inet:fqdn:host = <str>
    * The host part of the FQDN.
    inet:fqdn:issuffix = <bool> (default: 0)
    * True if the FQDN is considered a suffix.
    inet:fqdn:iszone = <bool> (default: 0)
    * True if the FQDN is considered a zone.
    inet:fqdn:updated = <time>
    * The last known updated time for the fqdn.
    inet:fqdn:zone = <inet:fqdn>
    * The zone level parent for this FQDN.

Form definitions include:

* The **primary property** whose value must be unique across all instances of that form.
* A set of (possibly optional) **secondary properties,** structured as ``<prop> = <valu>``, listed with their defined type (``<time>``, ``<bool>``) as well as any special handling or normalization of the type for that property (e.g., ``'str'``, ``{'lower': True}``).
* Whether a property is **read only** (``‘ro’``) once set. (Note that ``‘ro’`` is visible in the source code but the designation is not carried over into the auto-generated documentation). “Read only” typically applies to secondary properties that are derived from the primary property. Since a node’s primary property value cannot be changed once set, any secondary properties derived from the primary property value should also be immutable. Secondary properties that can be derived from the primary property will be set automatically by Synapse when the node is created.
* Whether a property has a **default value** (``‘defval’``) if an explicit value for the property is not specified.
* Inline **documentation** (``‘doc’``) that clarifies the purpose or intended definition of the property.

Types
-----

A type is the definition of a data element within the Synapse data model. A type describes what the element is and enforces how it should look, including how it should be normalized (if necessary) for both storage and representation (display).

Synapse supports standard types (such as integers and strings) as well as extensions of those types that may be knowledge domain-specific. For example, in Synapse an IP address is a custom type that is an extension of an integer type. An IP is stored as an integer, but based on the IP address type Synapse performs additional checks when you try to create data of that type to ensure the data represents a “properly formed” IP address.

Users typically will not interact directly with types; they primarily underlie and support the Synapse data model. However, types are important because they define the primary and secondary properties of forms, which in turn define nodes. Specifically, **all forms are types** (though not all types are forms). This strong **type enforcement** is one of Synapse’s most powerful features, because it allows users to pivot across arbitrary data within the hypergraph simply because they share the same typed property, allowing for the discovery of potential relationships among seemingly disparate data.

Tags
----

Tags are annotations applied to nodes. Simplistically, they can be thought of as labels that provide context to the data represented by the node.

Broadly speaking, within Synapse:

* Nodes represent **things:** objects, relationships, or events. In other words, nodes typically represent facts or observables that are objectively true and unchanging.
* Tags represent **assessments:** judgements that could change if the data or the analysis of the data changes.

For example, an internet domain is an “objectively real thing” - a domain exists, was registered, etc. and can be created as a node such as ``inet:fqdn = woot.com``. Whether that domain is sinkholed is an assessment - a researcher may need to evaluate data related to that domain (such as domain registration records or current and past IP resolutions) to decide whether the domain appears to be sinkholed (or when it was sinkholed). This assessment can be represented by applying a tag such as ``#cno.sink.hole`` to the ``inet:fqdn = woot.com`` node.

Tags are designed to be “hierarchical”, moving from left to right with increasing specificity. The dot ( ``.`` ) character is used as a separator between tag elements.

Tags are nodes based on a form (``syn:tag``) defined within the Synapse data model. That is, the tag ``#cno.sink.hole`` can be applied to another node; but the tag itself also exists as the node ``syn:tag = cno.sink.hole``.

**Example**

The **node** ``syn:tag = aka.feye.thr.apt1``:

::

  cli> storm syn:tag = aka.feye.thr.apt1

  syn:tag = aka.feye.thr.apt1
          .created = 2018/05/17 17:11:36.967
          :base = apt1
          :depth = 3
          :doc = Indicator or activity FireEye calls (or associates with) the APT1 threat group.
          :title = APT1 (FireEye)
          :up = aka.feye.thr
  complete. 1 nodes in 1 ms (1000/sec).

The **tag** ``#aka.feye.thr.apt1`` applied to the **node** ``inet:fqdn = hugesoft.org``:

::

  cli> storm inet:fqdn = hugesoft.org
  
  inet:fqdn = hugesoft.org
          .created = 2018/05/17 21:00:59.274
          :domain = org
          :host = hugesoft
          :issuffix = False
          :iszone = True
          :zone = hugesoft.org
          #aka = (None, None)
          #aka.feye = (None, None)
          #aka.feye.thr = (None, None)
          #aka.feye.thr.apt1 = (None, None)
  complete. 1 nodes in 2 ms (500/sec).

By default, Storm displays each individual tag in the tag hierarchy represented by ``#aka.feye.thr.apt1``. The ``(None, None)`` is a placeholder for optional ``.seen``-type properties for the tag itself (e.g., earliest / most recent time that tag was assessed to be relevant or “true” with respect to the node to which it is applied).

Synapse does not include any pre-populated tags (syn:form = <tag>), just as it does not include any pre-populated domains (inet:fqdn = <domain>). Because tags can be highly specific to both a given knowledge domain and to the type of analysis being done within that domain, organizations have the flexibility to create a tag structure that is most useful to them.

Tags are discussed in greater detail elsewhere in this documentation.


.. _`Data Model`: ../../datamodel.rst
.. _discussion: ../userguides/ug003_bkd_graphs_hypergraphs.rst
.. _inet.py: https://github.com/vertexproject/synapse/blob/010/synapse/models/inet.py

