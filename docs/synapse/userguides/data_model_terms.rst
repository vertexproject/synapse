



.. highlight:: none

.. _data-model-terms:

Data Model - Terminology
========================

**Note:** This documentation presents the data model from a User or Analyst perspective. See the online documentation on Types_ and Forms_ or the Synapse source code_ for more detailed information.

Recall that **Synapse is a distributed key-value hypergraph analysis framework.** That is, Synapse is a particular implementation of a hypergraph model, where an instance of a hypergraph is called a Cortex. In our brief discussion of graphs and hypergraphs, we pointed out some fundamental concepts related to the Synapse hypergraph implementation:

- **Everything is a node.** There are no pairwise ("two-dimensional") edges in a hypergraph the way there are in a directed graph. While Synapse includes some edge-like nodes (digraph nodes or "relationship" nodes) in its data model, they are still nodes.

- **Tags act as hyperedges.** In a directed graph, an edge connects exactly two nodes. In Synapse, tags are labels that can be applied to an arbitrary number of nodes. These tags effectively act as an n-dimensional edge that can connect any number of nodes – a hyperedge.

- **(Almost) every navigation of the graph is a pivot.** Since there are no pairwise edges in a hypergraph, you can’t query or explore the graph by traversing its edges. Instead, navigation primarily consists of pivoting from the properties of one set of nodes to the properties of another set of nodes. (Since tags are hyperedges, there are ways to lift by or "pivot through" tags to effectively perform "hyperedge traversal"; but most navigation is via pivots.)

To start building on those concepts, you need to understand the basic elements of the Synapse data model. The fundamental terms and concepts you should be familiar with are:

- Type_
- Form_
- Node_
- Property_
- Tag_

Synapse uses a query language called **Storm** (see :ref:`storm-ref-intro`) to interact with data in the hypergraph. Storm allows a user to lift, filter, and pivot across data based on node properties, values, and tags. **Understanding these model structures will significantly improve your ability to use Storm and interact with Synapse data.**

.. _data-types:

Type
----

A **type** is the definition of a data element within the Synapse data model. A type describes what the element is and enforces how it should look, including how it should be normalized, if necessary, for both storage (including indexing) and representation (display).

The Synapse data model supports the following:

- **Base types,** which are foundational to Synapse and meant to be "universal" across any data model for any knowledge domain. Base types include standard types such as integers and strings, as well as common types defined within or specific to Synapse such as globally unique identifiers (``guid``), date/time values (``time``), time intervals (``ival``), and tags (``syn:tag``).

- **Model-specific types** (or just "types"), which are specific to a given Synapse data model for a given knowledge domain. An object (:ref:`data-forms`) represented in the data model may itself be defined as a specific type with its own definition, normalization rules, and other constraints. In some cases, model-specific types may be extensions of base types (e.g., a U.S. Social Security Number (``gov:us:ssn``) is an extension of the integer (``int``) type with additional constraints to describe allowable format, range, etc.). In other cases, a model-specific type may be created specifically to define a given model element. For example, a fully qualified domain name (``inet:fqdn``) is its own type that is used to describe and define a domain in Synapse.

Users typically will not interact with types directly; they are primarily used "behind the scenes" to define and support the Synapse data model. From a user perspective, it is important to keep the following points in mind for types:

- **Every element in the Synapse data model must be defined as a type.** Synapse uses **forms** to define the objects that can be represented (modeled) within a Synapse hypergraph. Forms have **properties** (primary and secondary) and every property must be explicitly defined as a particular type.

- **Type enforcement is essential to Synapse’s functionality.** Type enforcement means every property is defined as a type, and Synapse enforces rules for how elements of that type can (or can’t) be created. This means (for example) that IPv4 addresses are always stored as integers (although displayed in dotted-decimal format) as opposed to integers in some cases but hex values or dotted strings in others. In addition, Synapse only allows the creation of "sensible" IP addresses - you can’t create an IP such as 273.42.97.426. This means that elements of the same type are always created, stored, and represented in the same way which ensures consistency and helps prevent "bad data" from getting into a Cortex.

- **Type awareness facilitates interaction with a Synapse hypergraph.** Synapse and the Storm query language are "model aware" and know which types are used for each property in the model. At a practical level this allows users to use a more concise syntax when using the Storm query language because in many cases the query parser "understands" which navigation options make sense, given the types of the properties used in the query. It also allows users to use wildcards to pivot (see :ref:`storm-ref-pivot`) without knowing the "destination" forms or nodes - Synapse "knows" which forms can be reached from the current set of data based on types.

- **It is still possible to navigate (pivot) between elements of different types that have the same value.** Type enforcement simplifies pivoting, but does not restrict you to only pivoting between properties of the same type. For example, the value of a Windows registry may be a string (type ``str``), but that string may represent a file path (type ``file:path``). While the Storm query parser would not automatically "recognize" that as a valid pivot (because the property types differ), it is possible to explicitly tell Storm to pivot from a specific ``file:path`` node to any registry value nodes whose string property value (``it:dev:regval:str``) matches that path.

Type-Specific Behavior
++++++++++++++++++++++

Synapse implements various type-specific optimizations to improve performance and functionality. Some of these are "back end" optimizations (i.e., for indexing and storage) while some are more "front end" in terms of how users interact with data of certain types via Storm. See :ref:`storm-ref-type-specific` for additional detail.

Viewing or Working with Types
+++++++++++++++++++++++++++++

Types (both base and model-specific) are defined within the Synapse source code. An auto-generated dictionary (from current source code) of Types_ can be found in the online documentation.

Types can also be viewed within a Cortex. A full list of current types can be displayed with the following Storm command:

``cli> storm syn:type``

See :ref:`storm-ref-model-introspect` for additional detail on working with model elements within Storm.

Type Example
++++++++++++

The data associated with a type’s definition is displayed slightly differently between the Synapse source code, the auto-generated online documents, and from the Storm command line. Users wishing to review type structure or other elements of the Synapse data model are encouraged to use the source(s) that are most useful to them.

The example below shows the type for a fully qualified domain name (``inet:fqdn``) as it is represented in the Synapse source code, the online documents, and from Storm.

Source Code
***********

.. parsed-literal::
  
  ('inet:fqdn', 'synapse.models.inet.Fqdn', {}, {
    'doc': 'A Fully Qualified Domain Name (FQDN).',
    'ex': 'vertex.link'}),

Auto-Generated Online Documents
*******************************

**inet:fqdn**
A Fully Qualified Domain Name (FQDN). It is implemented by the following class: ``synapse.models.inet.Fqdn``.

A example of ``inet:fqdn``:

- ``vertex.link``

Storm
*****


.. parsed-literal::

    cli> storm syn:type=inet:fqdn
    
    syn:type=inet:fqdn
            .created = 2019/03/13 23:55:24.423
            :ctor = synapse.models.inet.Fqdn
            :doc = A Fully Qualified Domain Name (FQDN).
    complete. 1 nodes in 54 ms (18/sec).


.. _data-forms:

Form
----

A **form** is the definition of an object in the Synapse data model. A form acts as a "template" that tells you how to create an object (Node_). While the concepts of form and node are closely related, it is useful to maintain the distinction between the template for creating an object (form) and an instance of a particular object (node). ``inet:fqdn`` is a form; ``inet:fqdn = woot.com`` (``<form> = <valu>``) is a node.

A form consists of the following:

- A **primary property.** The primary property of a form must be selected / defined such that the value of that property is unique across all possible instances of that form. A form’s primary property must be defined as a specific **type.** In many cases, a form will have its own type definition - for example, the form ``inet:fqdn`` is of type ``inet:fqdn``. All forms are types (that is, must be defined as a Type_) although not all types are forms.
- Optional **secondary properties.** If present, secondary properties must also have a defined type, as well as any additional constraints on the property, such as:
  
  - Whether a property is read-only once set.
  - Whether a default value should be set for the property if no value is specified.
  - Any normalization (outside of type-specific normalization) that should occur for the property (such as converting a string to all lowercase).

Form secondary properties should also include brief documentation explaining the nature or purpose of the property.

Secondary properties are form-specific and are explicitly defined for each form. However, Synapse also supports a set of universal secondary properties (**universal properties**) that are valid for all forms.

Property_ discusses these concepts in greater detail.

While types underlie the data model and are generally not used directly by analysts, forms comprise the essential "structure" of the data analysts work with. Understanding (and having a good reference) for form structure and options is essential for working with Synapse data.

Viewing or Working with Forms
+++++++++++++++++++++++++++++

Like types, forms are defined within the Synapse source code and include a base set of forms intended to be generic across any data model, as well as a number of model-specific (knowledge domain-specific) forms. An auto-generated dictionary (from current source code) of Forms_ can be found in the online documentation.

Forms can also be viewed within a Cortex. A full list of current forms can be displayed with the following Storm command:

``cli> storm syn:form``

See :ref:`storm-ref-model-introspect` for additional detail on working with model elements within Storm.

Form Example
++++++++++++

The data associated with a form’s definition is displayed slightly differently between the Synapse source code, the auto-generated online documents, and from the Storm command line. Users wishing to review form structure or other elements of the Synapse data model are encouraged to use the source(s) that are most useful.

The example below shows the form for a fully qualified domain name (``inet:fqdn``) as it is represented in the Synapse source code, the online documents, and from Storm. Note that the output displayed via Storm includes universal properties (``.seen``, ``.created``), where the static source code (and the documents generated from it) do not. Universal properties are defined separately within the Synapse source and have their own section_ in the auto-generated online documents.

Source Code
***********

.. parsed-literal::
  
  ('inet:fqdn', {}, (
     ('domain', ('inet:fqdn', {}), {
        'ro': True,
        'doc': 'The parent domain for the FQDN.',
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
     ('zone', ('inet:fqdn', {}), {
        'doc': 'The zone level parent for this FQDN.',
     }),
  ))


Auto-Generated Online Documents
*******************************

**inet:fqdn**
A Fully Qualified Domain Name (FQDN).

Properties:
  
  :domain / inet:fqdn:domain
    The parent domain for the FQDN. It has the following property options set:
    
    - Read Only: ``True``
    
    The property type is inet:fqdn.

  :host / inet:fqdn:host
    The host part of the FQDN. It has the following property options set:
    
    - Read Only: ``True``
    
    The property type is str. Its type has the following options set:
    lower: ``True``

  :issuffix / inet:fqdn:issuffix
    True if the FQDN is considered a suffix. It has the following property options set:
    
    - Default Value: ``0``
    
    The property type is bool.

  :iszone / inet:fqdn:iszone
    True if the FQDN is considered a zone. It has the following property options set:
    
    - Default Value: ``0``
    
    The property type is bool.

  :zone / inet:fqdn:zone
    The zone level parent for this FQDN.
    
    The property type is inet:fqdn.

Storm
*****

Form (``inet:fqdn``) alone:


.. parsed-literal::

    cli> storm syn:form=inet:fqdn
    
    syn:form=inet:fqdn
            .created = 2019/03/13 23:55:24.423
            :doc = A Fully Qualified Domain Name (FQDN).
            :runt = False
            :type = inet:fqdn
    complete. 1 nodes in 2 ms (500/sec).


Form with secondary properties:


.. parsed-literal::

    cli> storm syn:prop:form=inet:fqdn
    
    syn:prop=inet:fqdn
            .created = 2019/03/13 23:55:24.423
            :doc = A Fully Qualified Domain Name (FQDN).
            :form = inet:fqdn
            :type = inet:fqdn
            :univ = False
    syn:prop=inet:fqdn.seen
            .created = 2019/03/13 23:55:24.423
            :base = .seen
            :doc = The time interval for first/last observation of the node.
            :form = inet:fqdn
            :relname = .seen
            :ro = False
            :type = ival
            :univ = False
    syn:prop=inet:fqdn.created
            .created = 2019/03/13 23:55:24.423
            :base = .created
            :doc = The time the node was created in the cortex.
            :form = inet:fqdn
            :relname = .created
            :ro = True
            :type = time
            :univ = False
    syn:prop=inet:fqdn:created
            .created = 2019/03/13 23:55:24.423
            :base = created
            :doc = The earliest known registration (creation) date for the fqdn.
            :form = inet:fqdn
            :relname = created
            :ro = False
            :type = time
            :univ = False
    syn:prop=inet:fqdn:domain
            .created = 2019/03/13 23:55:24.423
            :base = domain
            :doc = The parent domain for the FQDN.
            :form = inet:fqdn
            :relname = domain
            :ro = True
            :type = inet:fqdn
            :univ = False
    syn:prop=inet:fqdn:expires
            .created = 2019/03/13 23:55:24.423
            :base = expires
            :doc = The current expiration date for the fqdn.
            :form = inet:fqdn
            :relname = expires
            :ro = False
            :type = time
            :univ = False
    syn:prop=inet:fqdn:host
            .created = 2019/03/13 23:55:24.423
            :base = host
            :doc = The host part of the FQDN.
            :form = inet:fqdn
            :relname = host
            :ro = True
            :type = str
            :univ = False
    syn:prop=inet:fqdn:issuffix
            .created = 2019/03/13 23:55:24.423
            :base = issuffix
            :defval = 0
            :doc = True if the FQDN is considered a suffix.
            :form = inet:fqdn
            :relname = issuffix
            :ro = False
            :type = bool
            :univ = False
    syn:prop=inet:fqdn:iszone
            .created = 2019/03/13 23:55:24.423
            :base = iszone
            :defval = 0
            :doc = True if the FQDN is considered a zone.
            :form = inet:fqdn
            :relname = iszone
            :ro = False
            :type = bool
            :univ = False
    syn:prop=inet:fqdn:updated
            .created = 2019/03/13 23:55:24.423
            :base = updated
            :doc = The last known updated date for the fqdn.
            :form = inet:fqdn
            :relname = updated
            :ro = False
            :type = time
            :univ = False
    syn:prop=inet:fqdn:zone
            .created = 2019/03/13 23:55:24.423
            :base = zone
            :doc = The zone level parent for this FQDN.
            :form = inet:fqdn
            :relname = zone
            :ro = False
            :type = inet:fqdn
            :univ = False
    complete. 11 nodes in 2 ms (5500/sec).


.. _data-nodes:

Node
----

A **node** is a unique object within the Synapse hypergraph. In Synapse nodes represent standard objects ("nouns") such as IP addresses, files, people, bank accounts, or chemical formulas. However, in Synapse nodes also represent relationships ("verbs") because what would have been an edge in a directed graph is now also a node in a Synapse hypergraph. It may be better to think of a node generically as a "thing" - any "thing" you want to model within Synapse (entity, relationship, event) is represented as a node.

Every node consists of the following components:

- A **primary property** that consists of the Form_ of the node plus its specific value. All primary properties (``<form> = <valu>``) must be unique for a given form. For example, the primary property of the node representing the domain ``woot.com`` would be ``inet:fqdn = woot.com``. The uniqueness of the ``<form> = <valu>`` pair ensures there can be only one node that represents the domain ``woot.com``. Because this unique pair "defines" the node, the comma-separated form / value combination (``<form>,<valu>``)is also known as the node’s **ndef** (short for "node definition").

- One or more **universal properties.** As the name implies, universal properties are applicable to all nodes.

- Optional **secondary properties.** Similar to primary properties, secondary properties consist of a property name defined as a specific type, and the property’s associated value for the node (``<prop> = <pval>``). Secondary properties are specific to a given node type (form) and provide additional detail about that particular node.

- Optional **tags**. A Tag_ acts as a label with a particular meaning that can be applied to a node to provide context. Tags are discussed in greater detail below.

Viewing or Working with Nodes
+++++++++++++++++++++++++++++

To view or work with nodes, you must have a Cortex that contains nodes (data). Users typically interact with Cortex data via the Synapse cmdr command line interface (:ref:`syn-tools-cmdr`) using the Storm query language (:ref:`storm-ref-intro`).

Node Example
++++++++++++

The Storm query below lifts and displays the node for the domain ``google.com``:


.. parsed-literal::

    cli> storm inet:fqdn=google.com
    
    inet:fqdn=google.com
            .created = 2019/03/13 23:55:24.534
            :domain = com
            :host = google
            :issuffix = False
            :iszone = True
            :zone = google.com
            #rep.majestic.1m
    complete. 1 nodes in 3 ms (333/sec).


In the output above:

- ``inet:fqdn = google.com`` is the **primary property** (``<form> = <valu>``).
- While not explicitly displayed, the node’s **ndef** would be ``inet:fqdn,google.com``.
- ``.created`` is a **universal property** showing when the node was added to the Cortex.
- ``:domain``, ``:host``, etc. are form-specific **secondary properties** with their associated values (``<prop> = <pval>``). For readability, secondary properties are displayed as **relative properties** within the namespace of the form’s primary property (e.g., ``:iszone`` as opposed to ``inet:fqdn:iszone``).
- ``#rep.majestic.1m`` is a **tag** indicating that ``google.com`` has been reported by web analytics company Majestic_ in their top million most-linked domains.

.. _data-props:

Property
--------

**Properties** are the individual elements that define a Form_ or (along with their specific values) that comprise a Node_.

Primary Property
++++++++++++++++

Every Form_ consists of (at minimum) a **primary property** that is defined as a specific Type_. Every Node_ consists of (at minimum) a primary property (its form) plus the node-specific value of the primary property (``<form> = <valu>``). In defining a form for a particular object (node), the primary property must be defined such that its value is unique across all possible instances of that form.

The concept of a unique primary property is straightforward for forms that represent simple objects; for example, the "thing" that makes an IP address unique is the IP address itself: ``inet:ipv4 = 1.2.3.4``. Defining an appropriate primary property for more complex multidimensional nodes (such as those representing a :ref:`form-relationship` or an :ref:`form-event`) can be more challenging.

Because a primary property uniquely defines a node, it cannot be modified once the node is created. To "change" a node's primary property you must delete and re-create the node.

Secondary Property
++++++++++++++++++

A Form_ can include optional **secondary properties** that provide additional detail about the form. As with primary properties, each secondary property must be defined as an explicit Type_. Similarly, a Node_ includes optional secondary properties (as defined by the node's form) along with their specific values (``<prop> = <pval>``).

Secondary properties are characteristics that do not uniquely define a form, but may further describe or distinguish a given form and its associated nodes. For example, the Autonomous System (AS) that an IP address belongs to does not "define" the IP (and in fact an IP's associated AS can change), but it provides further detail about the IP address.

Many secondary properties are derived from a node's primary property and are automatically set when the node is created. For example, creating the node ``file:path="c:\\windows\\system32\\cmd.exe"`` will automatically set the properties ``:base = cmd.exe``, ``:base:ext = exe``, and ``:dir = c:/windows/system32``. Because a node's primary property cannot be changed once set, any secondary properties derived from the primary property also cannot be changed (i.e., are read-only). Non-derived secondary properties can be set, modified, or even deleted.

Universal Property
++++++++++++++++++

Most secondary properties are form-specific, providing specific detail about individual objects within the data model. However, Synapse defines a subset of secondary properties as **universal properties** that are potentially applicable to all forms within the Synapse data model. Universal properties include:

- ``.created``, which is set for all nodes and whose value is the date / time that the node was created within a Cortex.
- ``.seen``, which is optional and whose value is a time interval (minimum or "first seen" and maximum or "last seen") during which the node was observed, existed, or was valid.

Property Namespace
++++++++++++++++++

Properties (both primary and secondary) comprise a colon-separated ( ``:`` ) namespace within the Synapse data model. All primary properties (i.e., forms, form names) include at least two colon-separated elements, such as ``inet:fqdn``.  The first element can be thought of as a rough "category" for the form (i.e., ``inet`` for Internet-related objects) with the second and / or subsequent elements defining the specific "subcategory" and / or "thing" within that category (``inet:fqdn``, ``inet:dns:query``, ``inet:dns:answer``, etc.)

Secondary properties extend and exist within the namespace of their primary property (form). Secondary properties are preceded by a colon ( ``:`` ) **except for** universal properties, which are preceded by a period ( ``.`` ) to distinguish them from form-specific secodnary properties. The secondary (both universal and form-specific) properties of ``inet:fqdn`` for example would include:

- ``inet:fqdn.created`` (universal property)
- ``inet:fqdn:zone`` (secondary property)

Secondary properties also comprise a relative namespace / set of **relative properties** with respect to their primary property (form). In many cases the Storm query language allows you to reference a secondary property using its relative property name where the context of the relative namespace is clear (i.e., ``:zone`` vs. ``inet:fqdn:zone``).

Relative properties are also used for display purposes within Synapse for visual clarity (see the `Node Example`_ above).

In some cases secondary properties may have their own "namespace". Viewed another way, while both primary and secondary properties use colons (or periods for universal properties) to separate elements of the property name, not all separators represent property "boundaries"; some act more as name "sub-namespace" separators. For example ``file:bytes`` is a primary property / form. A ``file:bytes`` form may include secondary properties such as ``:mime:pe:imphash`` and ``:mime:pe:complied``.  In this case ``:mime`` and ``:mime:pe`` are not themselves secondary properties, but sub-namespaces for individual MIME data types and the "PE executable" data type specifically.

Viewing or Working with Properties
++++++++++++++++++++++++++++++++++

As Properties are used to define Forms, they are defined within the Synapse source code with their respective Forms_. Universal properties are not defined "per-form" but have their own section_ in the online documentation.

Properties can also be viewed within a Cortex. A full list of current properties can be displayed with the following Storm command:

``cli> storm syn:prop``

See :ref:`storm-ref-model-introspect` for additional detail on working with model elements within Storm.

Property Example
++++++++++++++++

The data associated with a property’s definition is displayed slightly differently between the Synapse source code, the auto-generated online documents, and from the Storm command line. Users wishing to review property structure or other elements of the Synapse data model are encouraged to use the source(s) that are most useful to them.

As primary properties are forms and secondary properties (with the exception of universal properties) are form-specific, properties can be viewed within the Synapse source code and online documentation by viewing the associated Form_.

Within Storm, it is possible to view individual primary or secondary properties as follows:

Storm
*****

Primary property:



.. parsed-literal::

    cli> storm syn:prop=inet:fqdn
    
    syn:prop=inet:fqdn
            .created = 2019/03/13 23:55:24.423
            :doc = A Fully Qualified Domain Name (FQDN).
            :form = inet:fqdn
            :type = inet:fqdn
            :univ = False
    complete. 1 nodes in 2 ms (500/sec).


Secondary property:


.. parsed-literal::

    cli> storm syn:prop=inet:fqdn:domain
    
    syn:prop=inet:fqdn:domain
            .created = 2019/03/13 23:55:24.423
            :base = domain
            :doc = The parent domain for the FQDN.
            :form = inet:fqdn
            :relname = domain
            :ro = True
            :type = inet:fqdn
            :univ = False
    complete. 1 nodes in 3 ms (333/sec).


.. _data-tags:

Tag
---

**Tags** are annotations applied to nodes. Simplistically, they can be thought of as labels that provide context to the data represented by the node.

Broadly speaking, within Synapse:

- Nodes represent **things:** objects, relationships, or events. In other words, nodes typically represent facts or observables that are objectively true and unchanging.
- Tags typically represent **assessments:** judgements that could change if the data or the analysis of the data changes.

For example, an Internet domain is an "objectively real thing" - a domain exists, was registered, etc. and can be created as a node such as ``inet:fqdn = woot.com``. Whether a domain has been sinkholed (i.e., where a supposedly malicious domain is taken over or re-registered by a researcher to identify potential victims attempting to resolve the domain) is an assessment. A researcher may need to evaluate data related to that domain (such as domain registration records or current and past IP resolutions) to decide whether the domain appears to be sinkholed. This assessment can be represented by applying a tag such as ``#cno.infra.sink.hole`` to the ``inet:fqdn = woot.com`` node. 

Tags are unique within the Synapse model because tags are both **nodes** and **labels applied to nodes.** Tags are nodes based on a form (``syn:tag``, of type ``syn:tag``) defined within the Synapse data model. That is, the tag ``#cno.infra.sink.hole`` can be applied to another node; but the tag itself also exists as the node ``syn:tag = cno.infra.sink.hole``. This difference is illustrated in the example below.

Tags are introduced here but are discussed in greater detail in :ref:`analytical-model-tags`.

Viewing or Working with Tags
++++++++++++++++++++++++++++

As tags are nodes (data) within the Synapse data model, they can be viewed and operated upon just like other data in a Cortex. Users typically interact with Cortex data via the Synapse cmdr command line interface (:ref:`syn-tools-cmdr`) using the Storm query language (:ref:`storm-ref-intro`).

See :ref:`storm-ref-model-introspect` for additional detail on working with model elements within Storm.

Tag Example
+++++++++++

The Storm query below displays the **node** for the tag ``cno.infra.sink.hole``:


.. parsed-literal::

    cli> storm syn:tag=cno.infra.sink.hole
    
    syn:tag=cno.infra.sink.hole
            .created = 2019/03/13 23:55:24.610
            :base = hole
            :depth = 3
            :doc = A sinkholed domain or the IP address the sinkholed domain resolves to.
            :title = Sinkholed domain or associated IP
            :up = cno.infra.sink
    complete. 1 nodes in 3 ms (333/sec).


The Storm query below displays the **tag** ``#cno.infra.sink.hole`` applied to the **node** ``inet:fqdn = hugesoft.org``:


.. parsed-literal::

    cli> storm inet:fqdn=hugesoft.org
    
    inet:fqdn=hugesoft.org
            .created = 2019/03/13 23:55:24.620
            :domain = org
            :host = hugesoft
            :issuffix = False
            :iszone = True
            :zone = hugesoft.org
            #aka.feye.thr.apt1
            #cno.infra.sink.hole = (2014/01/11 00:00:00.000, 2018/03/30 00:00:00.000)
    complete. 1 nodes in 3 ms (333/sec).


Note that a tag **applied to a node** uses the "tag" symbol ( ``#`` ). This is a visual cue to distinguish tags on a node from the node's secondary properties. The symbol is also used within the Storm syntax to reference a tag as opposed to a ``syn:tag`` node.


.. _Types: https://vertexprojectsynapse.readthedocs.io/en/latest/autodocs/datamodel_types.html
.. _Forms: https://vertexprojectsynapse.readthedocs.io/en/latest/autodocs/datamodel_forms.html
.. _code: https://github.com/vertexproject/synapse
.. _section: https://vertexprojectsynapse.readthedocs.io/en/latest/autodocs/datamodel_forms.html#universal-properties
.. _Majestic: https://majestic.com/reports/majestic-million
