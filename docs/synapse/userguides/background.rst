.. highlight:: none

.. _userguide_bkd:

Background
##########

.. _bkd-why-synapse:

Why Synapse?
============

**Synapse is a central intelligence system created to support analyst teams in every stage of the intelligence life cycle.**
We designed Synapse to answer complex questions that require the fusion of large data sets from a broad range of 
sources that span multiple disciplines. Analysis in Synapse is based on representing all relevant data in a structured model
that allows analysts or algorithms to query, annotate, navigate, and reason over the collected data.

.. TIP::
  
  See Synapse's :ref:`intro-features` for an overview of Synapse's advantages!

Synapse is based on a proven methodology informed by real-world experience. Synapse traces its roots to the proprietary,
directed graph-based analysis platform (Nucleus) used within Mandiant to produce the APT1_ Report. Synapse was originally
created to improve upon our years of experience with directed graphs. Over the past decade, Synapse has been battle-tested
by our internal team, our customers, and our community. Based on their feedback, we have continued to evolve Synapse's
capabilities to meet the changing needs of an increasingly complex and interconnected analysis environment. 

From the beginning, we designed Synapse to support the following critical elements:

- The use of a **shared analytical workspace** to give analysts access to the same data and assessments
  in real time. Shared visibility helps to pool collected knowledge and significantly reduces the duplication of
  effort that can occur in siloed or isolated systems.

- The ability to capture and consistently represent **all analytically relevant data** within a single platform.
  Synapse's :ref:`userguide_datamodel` is both extensive and readily extensible to adapt to new data sets and changing
  analysis needs.

- The principle that **relationships among and conclusions about data should be self-evident.** To the extent
  possible, data and analytical findings must be represented within Synapse so that the analysis "speaks for itself".
  By representing data and assessments in a consistent and structured manner, Synapse significantly reduces ambiguity
  around and misinterpretation of both ground-truth data and analytical conclusions. 

These features give Synapse the following advantages:

- Synapse allows (and requires!) analysts to **show our work** in a reasonably concise manner. Analysts should not
  have to refer to long-form reporting (or rely on an unquestioned subject matter expert) to understand a line of
  analytical reasoning.

- Synapse allows analysts to better **review and validate our findings**. Conflicting analysis is readily identified
  through the structure of the data itself. Analysts can readily question, review, debate, deconflict, and
  ultimately improve their analytical findings.

- By representing data and relationships in Synapse's knowledge graph, **analysis becomes decomposable**. That is,
  analytical assessments can be traced through the graph to the "ground truth" observations that informed our
  conclusions.

- Because Synapse's knowledge graph is continually expanded, updated, and revised, it always represents the
  **current, combined understanding** of an organization's data and analysis. Unlike prose reports or tickets, Synapse
  is never stale or outdated.
  
Synapse's hypergraph-based design addresses many of the shortcomings we identified with earlier directed graph and
prototype hypergraph systems. And because our experience taught us the power of a flexible analysis platform over large
and disparate data sets, Synapse is designed to be flexible, modular, and adaptable to **any** knowledge domain
- not just threat intelligence data.

Many of the real-world examples in this User Guide reference data from the fields of information technology or threat
intelligence, given Synapse’s history. But Synapse's structures, processes, and queries can be applied to other knowledge
domains and data sets. **The intent of Synapse is that any data that can be represented in a spreadsheet, database, or graph database can be represented in Synapse using an appropriate data model.**

.. _bkd-graphs-hypergraphs:

Graphs and Hypergraphs
======================

To understand the power of Synapse, it helps to have some additional background. Without getting into
mathematical definitions, this section introduces key concepts related to a **hypergraph,** and contrasts them
with those of a **graph** or a **directed graph.** Most analysts should be familiar with the concept of a graph
– even if not in the strict mathematical sense – or with data that can be visually represented in graph form.

.. _bkd-graphs:

Graphs
------

A **graph** is a mathematical structure used to model pairwise relations between objects. Graphs consist of:

- **vertices** (or **nodes**) that represent objects, and
- **edges** that connect two vertices in some type of relationship.

|graph|

Edges connect exactly two nodes; they are "pairwise" or "two-dimensional". Nodes and edges may have properties that
describe their relevant features. Both nodes and edges are representational objects within the graph: nodes typically
represent things ("nouns") and edges typically represent relationships ("verbs").

**Examples**

**Cities and Roads.** A simple example of data that can be represented by a graph are cities connected by
roads. If abstracted into graph format, each city would be a vertex or node and a road connecting two cities
would be an edge. Since you can travel from City A to City B or from City B to City A on the same road, the
graph is **directionless** or **undirected.**

**Social Networks.** Another example is social networks based on mutual "connections", such as LinkedIn. In this
case, each person would be a node and the connection between two people would be an edge. In most cases, LinkedIn
requires you to request a connection that the other party must accept. Once accepted, both parties are connected
to each other. In this sense it can be considered a directionless graph. (This is a simplification, but serves our
purpose as an example.)

.. _bkd-directed-graphs:

Directed Graphs
---------------

A **directed graph** is a graph where the edges have a direction associated with them. In other words, the
relationship represented by the edge is one-way. An edge in a regular (undirected) graph is typically represented
by a straight line, but an edge in a directed graph is typically represented by an arrow.

|directedgraph|

**Examples**

**Cities and Roads.** In our cities-and-roads example, the graph would be a directed graph if the roads were
all one-way streets: in this case you can use a particular road to go from City A to City B, but not from City
B to City A.

**Social Networks.** Social networks that support a "follows" relationship (such as X or Bluesky) can be represented
as directed graphs. Each person is still a node, but the "follows" relationship is one way – I can follow you,
but you don’t have to follow me. If you choose to follow me, that would be a second, independent one-way edge
in the opposite direction. (This is also a simplification but works for a basic illustration.)

**Other Examples.** Many other types of data can be represented with nodes and directed edges.  For example, in
information security you can represent data and relationships such as:

::

  malware_file --performed DNS lookup for--> domain

or

::

  domain --resolves to--> ip_address

In these examples, files, domains, and IP addresses are nodes and "performed DNS lookup for" (queried) and
"resolves to" are edges (relationships). The edges are directed because a malware binary can contain programming
to query a domain name, but a domain can’t "perform a lookup" for a malware binary; the relationship (edge) is one-way.

Some directed graph implementations allow users to label or tag nodes and edges with additional information. These
tags can act as metadata for various purposes, such as to provide context or to group related objects.

.. _bkd-graph-analysis:

Analysis with Graphs
--------------------

When working with graphs and directed graphs, analysts typically select objects (nodes) and navigate the graph by
traversing the edges (relationships) that connect those nodes. Because edges are used to explicitly link nodes, a key
limitation to this approach is that all relationships (edges) between objects must be explicitly defined within the
graph model; you must know all of the relationships that you want to represent in advance. This makes it extremely
difficult to discover novel relationships (e.g, that you failed to consider or did not realize existed) among the data.

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
  hyperedge can connect an arbitrary number of nodes; this can make hypergraphs more challenging to visualize in
  a "flat" form. As in the image above, hyperedges are commonly represented as a set of disconnected nodes
  encircled by a boundary; the boundary represents the hyperedge "joining" the nodes into a related group.
  Just as there is no limit to the number of edges to or from a node in a directed graph, a node in a hypergraph
  can be joined by any number of hyperedges (i.e., can be part of any number of "groups").

.. _bkd-synapse-hypergraph:

Analysis with a Synapse Hypergraph
----------------------------------

**Synapse** is a particular implementation of a hypergraph model. In Synapse, all objects and most relationships are nodes
(though Synapse uses what we call lightweight or light edges, similar to directed edges, in some cases). This means that
most relationships in Synapse are based on nodes sharing a common **property value** as opposed to being explicitly
linked by an edge.

In Synapse, the "resolves to" relationship between an FQDN and an IPv4 is not represented by an edge. Instead, the two
objects (nodes) are related via a third node (a DNS A node) representing the relationship. Both the FQDN and IPv4 are
**properties** of the DNS A node. To understand the relationship between an FQDN and the IPv4 it resolves to, you navigate
(pivot) from the FQDN to the DNS A node to the IPv4 node using the nodes' property values - no edges are used or traversed
in this case.

This means that in Synapse, you are not limited to navigating or exploring the data using predefined edges. Instead, you
primarily navigate (**pivot**) among nodes with **shared property values**. Synapse can readily identify these shared
values, and show you the existing relationships; you don't need to know them in advance. This simplifies navigation and
helps users discover novel relationships they might otherwise miss.

Synapse uses mechanisms such as :ref:`gloss-type-enforce` to ensure that properties conform to their expected values
(e.g., Synapse does its best to prevent you from entering an email address where you need a URL, and that any
URL you enter looks reasonably like a URL) and :ref:`gloss-type-norm` to ensure property values are represented
consistently (e.g., in many cases Synapse converts string-based values to all lowercase for consistency). These
methods make the data as consistent and "clean" as possible to facilitate navigation and discovery.

.. _APT1: https://v.vtx.lk/apt1-report

.. |graph| image:: https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Undirected_graph_no_background.svg/330px-Undirected_graph_no_background.svg.png 
.. |directedgraph| image:: https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Directed_acyclic_graph_3.svg/330px-Directed_acyclic_graph_3.svg.png
.. |hypergraph| image:: https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Hypergraph-wikipedia.svg/330px-Hypergraph-wikipedia.svg.png
