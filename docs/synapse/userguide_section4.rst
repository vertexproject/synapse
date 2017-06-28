3. Synapse Data Model - Basics
==============================

This section covers the basic “building blocks” of the Synapse hypergraph data model. It is intended to provide an overview of the fundamentals to get you started. Model elements are discussed in greater detail in the next section.

(**Note:** This documentation presents the data model from a User or Analyst perspective; for detailed information, see the `Data Model`_ section of readthedocs or the Synapse source code.)

**Background**

Recall that **Synapse is a distributed key-value hypergraph analysis framework.** That is, Synapse is a particular implementation of a hypergraph model, where an instance of a hypergraph is called a Cortex. In our brief discussion of graphs and hypergraphs, we pointed out some fundamental concepts related to the Synapse hypergraph implementation:

- **Everything is a node.** There are no pairwise (“two-dimensional”) edges in a hypergraph the way there are in a directed graph.

- **Tags act as “hyperedges”.** In a directed graph, an edge connects exactly two nodes. In Synapse, tags are labels that can be applied to an arbitrary number of nodes. These tags effectively act as an n-dimensional edge that can connect any number of nodes – a hyperedge.

- **Every navigation of the graph is a pivot.** Since there are no pairwise edges in a hypergraph, you can’t query or explore the graph by navigating (traversing) its edges. Instead, every navigation is a pivot from the properties of one node or set of nodes to the properties of another set of nodes. (Technically, selecting a set of nodes based on tag could be considered “navigating” along a hyperedge. But mostly everything is a pivot.)

To start building on those concepts, you need to understand the basic elements of the Synapse data model.

**Data Model Terminology**

The fundamental concepts you should be familiar with are:

- Node
- Form
- Type
- Tag

Synapse uses a query language called **Storm** to interact with data in the hypergraph. Storm allows a user to ask about, filter, and pivot around data based in large part on node properties, values, and tags. **Understanding these structures will significantly improve your ability to use Storm and interact with Synapse data.**

**Node**

A node can be thought of as an “object” within the hypergraph; although that is a bit of a misnomer, as nodes in Synapse can represent both “objects” (IP addresses, files, people, bank accounts, chemical formulas) and “relationships” (remember, what would have been an edge in a directed graph is now also a node in Synapse). It may be better to think of a node generically as a “thing”: any “thing” you want to model within Synapse (object, relationship, event) is represented as a node.

Nodes are represented by data structures called “tufos” (short for “tuple form”; a **form** is described below). While “tufo” is used in the Synapse technical documentation and source code, “node” is more familiar and intuitive to most people, so this User Guide uses that term. However, the terms “tufo” and “node” are roughly interchangeable. (A high-level overview of tufos_ is provided in readthedocs.)

From a user perspective, you need to know that every node consists of the following components:

- A **globally unique identifier** (GUID, identifier, or ID) that is **unique across all nodes in a given hypergraph** (e.g., a given Cortex). The way that node GUIDs are generated makes them “Cortex specific”: this means that the same node (e.g., ``inet:fqdn=woot.com``) in two different Cortexes could have a different GUID in each.

- One more more **universal properties** created automatically by Synapse whenever a new node is generated. The most important universal property for our purpose is the property ``tufo:form=<form>`` that lists the **primary property type** for that node. For example, a node representing an Internet domain (``inet:fqdn``) would have the universal property ``tufo:form=inet:fqdn``.

- A single **primary property** that consists of the **form** of the node plus its specific value.
  
  All primary properties (``<form>=<value>``) **must be unique for a given form** (node type). For example, the primary property of the node representing the domain “woot.com” would be ``inet:fqdn=woot.com``. The uniqueness of the ``<form>=<value>`` pair ensures there can be only one node that represents the domain “woot.com”.
  
  Where the object represented by the node does not have a characteristic that is sufficiently unique to act as a primary property value – that is, any object where the possibility of a collision exists – the primary property is a machine-generated GUID. For example, in Synapse objects such as people, companies / organizations, or files (e.g., specific sets of bytes) are represented by GUIDs. Note that the GUID used as the **primary property** for some nodes is different from the GUID assigned to each node as its **identifier.**

- Various **secondary properties** that are specific to that form. A node representing an Internet domain will have different secondary properties than a node representing a person, which will have different secondary properties than a node representing a bank account.

  Some secondary properties (and their values) are generated and set automatically when a node is created. Other secondary properties may be added or modified at a later time, unless they are defined as “read only” in the form definition.

  Secondary properties form a **relative namespace** beneath the namespace of the node’s form. That is, if the node’s form type is ``tufo:form=foo:bar`` (e.g., this is a ``foo:bar`` node), then all secondary properties will be named in the format ``foo:bar:<secondary_prop>``. In some circumstances (e.g., where the namespace context is clear) secondary properties can be referenced as **relative properties** – that is, as ``:<secondary_prop>`` as opposed to the fully qualified ``foo:bar:<secondary_prop>``. So a secondary property ``foo:bar:baz`` can be referenced by its relative name ``:baz`` in some circumstances.

- Optional **ephemeral properties** that may exist temporarily for some special purpose, and do not represent data stored permanently about that node. Ephemeral property names are preceded by a dot ( ``.`` ) to indicate they are ephemeral. The most common ephemeral property is ``.new``, which indicates that a node is newly created.

*Example*

An example will help to illustrate the concepts above. The command below adds a node for the domain “woowoo.com” to a Cortex and displays the detailed properties of the newly-created node::

  cli> ask --raw addnode(inet:fqdn,woowoo.com)
  [
    [
      "159eb804de045a47220dbde76984f2f4",
      {
        ".new": true,
        "inet:fqdn": "woowoo.com",
        "inet:fqdn:domain": "com",
        "inet:fqdn:host": "woowoo",
        "inet:fqdn:sfx": 0,
        "inet:fqdn:zone": 1,
        "tufo:form": "inet:fqdn"
      }
    ]
  ]
  (1 results)

In the output above:

- ``159eb804de045a47220dbde76984f2f4`` is the GUID (identifier) for the node.
- ``".new": True`` is the ephemeral property showing this is a newly created node.
- ``"tufo:form": "inet:fqdn"`` lists the type of node (the form for the node).
- ``"inet:fqdn": "woowoo.com"`` is the primary property of the node (``<form>=<value>``).

The remaining entries are various node-specific secondary properties and their values (``inet:fqdn:zone``, ``inet:fqdn:domain``, etc.)

**Forms**

A form is the definition of a Synapse hypergraph node. A form consists of the declaration of the primary property and its **type**, along with the form’s secondary properties (and their types). A form can be thought of as a template: if you want to create an ``inet:fqdn`` node in Synapse, the ``inet:fqdn`` form tells you the proper structure for the node and the properties it can contain.

Forms are defined within the Synapse data model, and are declared within the model as tufos – that is, form definitions are themselves nodes in the hypergraph. Form definitions can be found within the `Data Model`_ section of readthedocs; those definitions are auto-generated from the Synapse source code. Forms are also documented within the source code of the appropriate Python module itself. (For example, the ``inet:fqdn`` form is defined within the ``inet.py`` module).

The data model can be extended to include new forms or to modify existing forms (e.g., to add or change the secondary properties of a form) by:

- creating new form nodes directly within the hypergraph to describe the updated data model; or
- updating or extending the relevant Synapse source code.

Because forms are nodes within the Synapse hypergraph, they can be created or modified directly within the Cortex, without the need to modify the Synapse source code. However, because the Synapse source code supports features such as model versioning and migration paths, it is preferable to maintain long-term or official model changes within the Synapse source.

Below are examples of how a form (``inet:fqdn``) is represented and documented in both readthedocs_ and the `Synapse source code`_ (in this case, ``inet.py``).

*inet:fqdn - readthedocs (auto-generated from source code)*
::
    **inet:fqdn = <inet:fqdn>**
    A Fully Qualified Domain Name (FQDN)

    Properties:
        inet:fqdn:created = <time:min>
        * Minimum time in millis since epoch
        inet:fqdn:domain = <inet:fqdn>
        * The parent FQDN of the FQDN
        inet:fqdn:expires = <time:max>
        * Maximum time in millis since epoch
        inet:fqdn:host = <str>
        * The hostname of the FQDN
        inet:fqdn:sfx = <bool> (default: 0)
        * Set to 1 if this FQDN is considered a “suffix”
        inet:fqdn:updated = <time:max>
        * Maximum time in millis since epoch
        inet:fqdn:zone = <bool> (default: 0)
        * Set to 1 if this FQDN is a logical zone (under a suffix)

*Synapse source code (inet.py)*
::
  ('inet:fqdn',{'ptype':'inet:fqdn'},[
    ('sfx',{'ptype':'bool','defval':0,'doc':'Set to 1 if this FQDN is considered a "suffix"'}),
    ('zone',{'ptype':'bool','defval':0,'doc':'Set to 1 if this FQDN is a logical zone (under a suffix)'}),
    ('domain',{'ptype':'inet:fqdn','doc':'The parent FQDN of the FQDN'}),
    ('host',{'ptype':'str','doc':'The hostname of the FQDN'}),
    ('created',{'ptype':'time:min'}),
    ('updated',{'ptype':'time:max'}),
    ('expires',{'ptype':'time:max'}),
  ]),


**Note** that there are some minor differences between the the auto-generated documentation in readthedocs and the Synapse source code. Since either (or both together) can be helpful for analysts working with Synapse data, it helps to be aware of these differences.

- **Default values.** Some nodes have properties that are automatically set to a specific value unless otherwise specified. If a property has a default value, it will be noted in both readthedocs and the source code.

- **Read-only properties.** Primary properties are unique and cannot be changed. Some secondary properties (typically those derived from the primary property) should also not be modified and are therefore implicitly read-only. In some cases, secondary properties are explicitly defined as read-only in the Synapse source code via the definition ``'ro':1``. However, these designations are not carried over to readthedocs. (An example is the ``:port`` property of an ``inet:url`` node. A port number is generally not included in a URL that uses standard ports for a given protocol (e.g., ``https://www.foo.com/bar/baz.html``). Based on the presence of an “https” prefix in a URL, Synapse will set ``:port=443`` as a read-only property, as specified in the source.)

- **Readability.** While readthedocs is a bit more readable for the general user, the auto-generation process sorts and displays types, forms, and form secondary properties in alphabetical order. However, alphabetical order may not be the most intuitive order for grouping either forms or form-specific properties, based on how an analyst would typically view or work with the data.

  In contrast, the Synapse source code lists forms and form properties in an order that may be more “sensical” for the given node type. The source code also tends to list secondary properties that can be automatically set by Synapse first in the source code (e.g., secondary properties that can be derived from the primary property’s value). For example, when creating the node ``inet:fqdn=woowoo.com``, Synapse can parse that ``<property>=<value>`` and automatically set the secondary properties ``inet:fqdn:domain=com`` and ``inet:fqdn:host=woowoo``. Secondary properties that require that an additional value be provided (e.g., ``inet:fqdn:created``) are listed later in the source code.

**Types**

A **type** is the definition of an element within the data model, describing what the element is and how it should be normalized (if necessary) and structured to conform to the model. Synapse supports standard types (such as integers and strings) as well as extensions of these types. From a user standpoint, types are important primarily as they define the primary and secondary properties of forms.

The data model can be extended to define new types by updating or extending the relevant Synapse source code.

**Tags**

Tags are annotations applied to nodes. Broadly speaking, nodes represent “things” (objects, relationships, events – generally things that are “facts” or “observables”) while tags represent analytical observations – annotations that **could** change if the data or the assessment of the data changes.

Tags can be applied to any number of relevant nodes, so in this sense tags act as **hyperedges** within the Synapse hypergraph, joining an arbitrary number of nodes in an “n-dimensional” relationship.

A tag – like every other object in the Synapse data model – is also a form (``syn:tag``) that is declared in the Synapse data model (in `datamodel.py`_) and represented within the hypergraph as a node. However, since the form (“template”) of a tag already exists within the data model, creating new tags does not require any changes to the Synapse source code. Analysts can create new tags “on the fly” to record their analytical observations. Creating a new tag simply creates a new node of form ``syn:tag`` just as creating a new Internet domain creates a new node of form ``inet:fqdn``.

Tags can represent any observation that is analytically relevant to the knowledge domain modeled within the Synapse hypergraph. For example, in the knowledge domain of cyber threat data, analysts may wish to annotate observations such as:

- “This malware binary is part of the threat cluster we track as Foobar Group.” (``syn:tag=tc.foobar``)
- “This IP address is a TOR exit node.” (``syn:tag=net.tor.exit``)
- “This domain has been sinkholed.” (``syn:tag=cno.sink.hole``)
- “FooCorp Security says this indicator is part of activity they call Vicious Wombat.” (``syn:tag=aka.foocorp.viciouswombat``)
- “This malware persists as a Windows service.” (``syn:tag=persist.winreg.service``)

Note that tags can use a dotted “hierarchical” notation that allows analytical observations to be grouped by increasing levels of specificity. For example:

- ``syn:tag=persist`` (malware persistence methods)
- ``syn:tag=persist.winreg`` (malware persistence methods using the Windows registry)
- ``syn:tag=persist.winreg.service`` (malware persistence methods using the Service keys of the Windows registry)

Nodes, properties, and tags are discussed in greater detail in the next section.


.. _Data Model: https://vertexprojectsynapse.readthedocs.io/en/latest/synapse/datamodel.html
.. _tufos: https://vertexprojectsynapse.readthedocs.io/en/latest/synapse/cortex.html#introducing-the-tufo
.. _readthedocs: https://vertexprojectsynapse.readthedocs.io/en/latest/synapse/datamodel.html#inet-fqdn-inet-fqdn
.. _Synapse source code: https://github.com/vertexproject/synapse/blob/master/synapse/models/inet.py
.. _datamodel.py: https://github.com/vertexproject/synapse/blob/master/synapse/datamodel.py
