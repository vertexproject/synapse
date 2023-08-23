.. highlight:: none

.. _userguide_bkd:

Background
##########

.. _bkd-why-synapse:

Why Synapse?
============

**Synapse is a versatile central intelligence and analysis system created to support analyst teams in every stage of the intelligence life cycle.**
We designed Synapse to answer complex questions which require the fusion of large data sets from a broad range of 
sources that span multiple disciplines. Analysis is based on representing all data in a structured model that allows
analysts or algorithms to query, annotate, navigate, and reason over the collected data.

.. TIP::
  
  See Synapse's :ref:`intro-features` for an overview of Synapse's advantages!

Synapse is based on a proven methodology informed by real-world experience. Synapse grew out of the need to
track a complex, diverse, and very large data set: namely, cyber threat data. Synapse is the successor to the
proprietary, directed graph-based analysis platform (Nucleus) used within Mandiant to produce the APT1_ Report.

Synapse and its predecessors were designed from the beginning to support the following critical elements:

- The use of a **shared analytical workspace** to give analysts access to the same data and assessments
  in real time.

- The principle that **relationships among and conclusions about data should be self-evident.** That is,
  to the extent possible, data and analytical findings must be represented so that analysis captured within
  the system should "speak for itself". 

These features give Synapse the following advantages:

- Synapse allows (and requires) analysts to "show their work" in a reasonably concise manner. Analysts should not
  have to refer to long-form reporting (or rely on the unquestioned word of a subject matter expert) to trace a
  line of analytical reasoning.

- Synapse allows analysts to better review and validate their findings. Conflicting analysis is highlighted through
  the structure of the data itself. Analysis can readily be questioned, reviewed, deconflicted, and ultimately improved.

- Because Synapse's knowledge store is continually expanded, updated, and revised, it always represents the
  current, combined understanding of its data and analysis. Unlike prose reports or tickets, Synapse is never stale
  or outdated.
  
Synapse's hypergraph design addresses many of the shortcomings we identified with earlier directed graph and prototype
hypergraph systems. In addition, because our experience taught us the power of a flexible analysis platform over
any large and disparate data set, Synapse has been designed to be flexible, modular, and adaptable to **any**
knowledge domain - not just cyber threat data.

Many of the real-world examples in this User Guide reference data from the fields of information technology or
cyber threat intelligence, given Synapse’s history. But Synapse's structures, processes, and queries can be applied
to other knowledge domains and data sets. **The intent of Synapse is that any data that could be represented in a spreadsheet, database, or graph database can be represented in Synapse using an appropriate data model.**

.. _bkd-graphs-hypergraphs:

Graphs and Hypergraphs
======================

To understand the power of Synapse, it helps to have some additional background. Without delving into
mathematical definitions, this section introduces key concepts related to a **hypergraph,** and contrasts them
with those of a **graph** or a **directed graph.** Most people should be familiar with the concept of a graph
– even if not in the strict mathematical sense – or with data that can be visually represented in graph form.

.. _bkd-graphs:

Graphs
------

A **graph** is a mathematical structure used to model pairwise relations between objects. Graphs consist of:

- **vertices** (or **nodes**) that represent objects, and
- **edges** that connect two vertices in some type of relationship.

|graph|

Edges connect exactly two nodes; they are "pairwise" or "two-dimensional". Both nodes and edges may have properties
that describe their relevant features. In this sense both nodes and edges can be thought of as representational
objects within the graph: nodes typically represent things ("nouns") and edges typically represent relationships
("verbs").

**Examples**

**Cities and Roads.** A simple example of data that can be represented by a graph are cities connected by
roads. If abstracted into graph format, each city would be a vertex or node and a road connecting two cities
would be an edge. Since you can travel from City A to City B or from City B to City A on the same road, the
graph is **directionless** or **undirected.**

**Social Networks.** Another example is social networks based on "connections", such as LinkedIn. In this case,
each person would be a node and the connection between two people would be an edge. In most cases, LinkedIn
requires a mutual connection (you must request a connection and the other party must accept); in this sense it can
be considered a directionless graph. (This is a simplification, but serves our purpose as an example.)

.. _bkd-directed-graphs:

Directed Graphs
---------------

A **directed graph** is a graph where the edges have a direction associated with them. In other words, the
relationship represented by the edge is one-way. Where an edge in an undirected graph is often represented by
a straight line, an edge in a directed graph is represented by an arrow.

|directedgraph|

**Examples**

**Cities and Roads.** In our cities-and-roads example, the graph would be a directed graph if the roads were
all one-way streets: in this case you can use a particular road to go from City A to City B, but not from City
B to City A.

**Social Networks.** Social networks that support a "follows" relationship (such as Twitter) can be represented
as directed graphs. Each person is still a node, but the "follows" relationship is one way – I can "follow" you,
but you don’t have to follow me. If you choose to follow me, that would be a second, independent one-way edge
in the opposite direction. (This is also a simplification but works for a basic illustration.)

**Other Examples.** Many other types of data can be represented with nodes and directed edges.  For example, in
information security you can represent data and relationships such as:

``malware_file --(performed DNS lookup for)--> domain``

or

``domain --(resolves to)--> ip_address``

In these examples, files, domains, and IP addresses are nodes and "performed DNS lookup for" and "resolves to"
are edges (relationships). The edges are directed because a malware binary can contain programming to resolve
a domain name, but a domain can’t "perform a lookup" for a malware binary; the relationship (edge) is one-way.

In addition to nodes and edges, some directed graph implementations may allow labeling or tagging of nodes and
edges with additional information. These tags can act as metadata for various purposes, such as to create
analytically relevant groups of objects.

Many tools exist to visually represent various types of data in a directed graph format.

.. _bkd-graph-analysis:

Analysis with Graphs
--------------------

When working with graphs and directed graphs, analysts typically select (or lift) objects (nodes) and
navigate the graph by traversing the edges (relationships) that connect those nodes. A key limitation to
this approach is that all relationships (edges) between objects must be explicitly defined. You must know
all of the relationships that you want to represent in advance, which makes the discovery of novel relationships
among the data extremely difficult.

.. _bkd-hypergraphs:

Hypergraphs
-----------

A **hypergraph** is a generalization of a graph in which an edge can join any number of nodes. Because an edge
is no longer limited to joining exactly two nodes, edges in a hypergraph are often called **hyperedges.**

|hypergraph|

Looked at another way, the key features of a hypergraph are:

- **Everything is a node.** In a hypergraph, objects ("nouns") are still nodes, similar to a directed graph.
  However, relationships ("verbs", commonly represented as edges in a directed graph) may also be represented
  as nodes. An edge in a directed graph consists of three objects (two nodes and the edge connecting them), but
  in a hypergraph the same data may be represented as a single multi-dimensional node.

- **Hyperedges connect arbitrary sets of nodes.** An edge in a directed graph connects exactly two nodes. A
  hyperedge can connect an arbitrary number of nodes; this makes hypergraphs more challenging to visualize in
  a "flat" form. As in the image above, hyperedges are commonly represented as a set of disconnected nodes
  encircled by a boundary; the boundary represents the hyperedge "joining" the nodes into a related group.
  Just as there is no limit to the number of edges to or from a node in a directed graph, a node in a hypergraph
  can be joined by any number of hyperedges (i.e., be part of any number of "groups").

.. _bkd-synapse-hypergraph:

Analysis with a Synapse Hypergraph
----------------------------------

Synapse is a specific implementation of a hypergraph model. Synapse's data store is called a **Cortex.** A Cortex
is a scalable hypergraph implementation which includes key/value-based node properties and a data model that
facilitates normalization.

In Synapse, all objects and most relationships are nodes (though Synapse uses what we call "lightweight" or "light"
edges, similar to directed edges, in some cases). This means that most relationships in Synapse are based on nodes
sharing a common property value. Instead of an FQDN being related to an IPv4 using a "resolves to" edge:

- the FQDN node is related to a DNS A record because the FQDN is a **property** of the DNS A node;
- the DNS A node is related to an IPv4 because the IPv4 is a **property** of the DNS A node.

So, in Synapse to understand the relationship between an FQDN and the IPv4 it resolves to, you navigate
(pivot) from the FQDN to the DNS A node to the IPv4 node using those nodes' shared property values.

This means that in Synapse, you are not limited to navigating the data using explicitly defined edges; you primarily
navigate (**pivot**) among nodes with shared property values. Synapse can readily identify these shared values, which both
simplifies navigation (Synapse can "show you" the relationships; you don't need to know them in advance) and
help users discover novel relationships that you may not know existed.

Synapse uses mechanisms such as **type enforcement** to ensure that properties conform to their expected values
(e.g., Synapse does its best to prevent you from entering an email address where you need a URL, and that any
URL you enter looks reasonably like a URL) and **property normalization** to ensure property values are represented
consistently (e.g., in many cases Synapse converts string-based values to all lowercase for consistency). These
methods make the data as consistent and "clean" as possible to facilitate navigation and discovery.

.. _APT1: https://www.mandiant.com/media/9941/download

.. |graph| image:: https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Undirected_graph_no_background.svg/320px-Undirected_graph_no_background.svg.png 
.. |directedgraph| image:: https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Directed_acyclic_graph_3.svg/320px-Directed_acyclic_graph_3.svg.png
.. |hypergraph| image:: https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Hypergraph-wikipedia.svg/320px-Hypergraph-wikipedia.svg.png
