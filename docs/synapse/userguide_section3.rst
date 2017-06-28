2. Graphs and Hypergraphs
=========================

To understand the power of Synapse, it helps to have some additional background. Without delving into mathematical definitions, this section introduces key concepts related to a **hypergraph,** and contrasts them with those of a **graph** or a **directed graph.** Most people should be familiar with the concept of a graph – even if not in the strict mathematical sense – or with data that can be visually represented in graph form.

**Graphs**

A **graph** is a mathematical structure used to model pairwise relations between objects. Graphs consist of **vertices** (or **nodes**) that represent objects, and **edges** that connect two vertices in some type of relationship. Note that edges are specifically pairwise or **two-dimensional:** an edge connects exactly two nodes. Both nodes and edges may have **properties** that describe their relevant features. In this sense both nodes and edges can be thought of as representational objects within the graph, with nodes typically representing things (“nouns”) and edges representing relationships (“verbs”).

A simple example of data that can be represented by a graph are cities connected by roads. If abstracted into graph format, each city would be a vertex or node, and a road connecting two cities would be an edge. Since you can travel from City A to City B or from City B to City A on the same road, the graph is “directionless” (or “undirected”).

Another example would be social networks based on “connections”, such as Facebook or LinkedIn. In this case, each person would be a node, and the connection between two people would be an edge. Because basic connections in these networks are mutual (you can’t “friend” someone on Facebook without them agreeing to “friend” you in return), it can be considered a directionless graph. (This is a bit of a simplification, but serves our purpose as an example.)

**Directed Graphs**

A **directed graph** is a graph where the edges have a direction associated with them. In other words, the relationship represented by the edge is “one-way”. Where an edge in an undirected graph is often represented by a straight line, an edge in a directed graph is represented by an arrow.

In our cities-and-roads example, the graph would be a directed graph if the roads were all one-way streets; in such a case you can use a particular road to go from City A to City B, but not from City B to City A.

In our social networks example, networks that support a “follows” relationship (such as Twitter) can be represented as directed graphs. Each person is still a node, but the “follows” relationship is one way – I can “follow” you, but you don’t have to follow me. If you choose to follow me, that would be a second, independent one-way edge in the opposite direction. (Again, this is a bit of a simplification but works for a basic illustration.)

Many other types of data can be represented with nodes and directed edges.  In information security, for example, you can represent data and relationships such as:

``<malware_file> -- <performed DNS lookup for> --> <domain>``

or

``<domain> -- <has DNS A record for> --> <IP_address>``

In those cases, files, domains and IP addresses are nodes and “performed DNS lookup” or “has DNS A record” (e.g., “resolved to”) are edges (relationships). The edges are directed because a malware binary can contain programming to resolve a domain name, but a domain can’t “perform a lookup” for a malware binary; the relationship (edge) is one-way or directional.

In addition to nodes and edges, some directed graph implementations may allow labeling or tagging of nodes and / or edges with additional information. These tags can act as metadata for various purposes, such as to create analytically relevant groupings.

Many tools exist to visually represent various types of data in a directed graph format; Maltego (which bills itself as a “visual link analysis tool” that can represent information in a directed graph) is a well-known example.

**Analysis with Graphs**

Directed graphs have become increasingly popular for representing and conducting analysis across large data sets. Analysis using a directed graph can be highly generalized into four methods for interacting with the data:

- **Lifting** or retrieving data. This simply asks about and returns specific nodes or edges from the graph. For example, you can ask about the node representing your Twitter account, or about the node representing IP address 1.2.3.4. You can also ask about sets of nodes that share some common feature – for example, all of the Twitter users who signed up for the service in January 2014, or all the PE executables whose compile date is 6/19/1992.

- **Filtering** the results. Once you’ve asked about (lifted) an initial data set (a node or set of nodes), filtering allows you to further refine your results by either including or excluding data based on some criteria. For example, once you have your list of Twitter users who signed up in January 2014, you may decide to exclude users who list their location as the United States. Similarly, once you have your list of files compiled on 6/19/1992, you can filter those results to only include files whose size is greater than 26576 bytes.

- **Traversing** the graph structure. Once you’ve asked about an initial data set, you can ask about relationships between your data set and other nodes by pathing (traversing) along the edges (relationships) that connect those nodes. For example, if you retrieve the node for your Twitter account, you can identify all of the accounts you are following on Twitter by traversing all of the “follows” edges from your node to the nodes of accounts that you follow. Similarly, if you retrieve the node for IP address 1.2.3.4, you can retrieve all of the domains that resolve to that IP by pathing backwards (remember, edges are directional) along the all of the “resolves to” edges that point to that IP.

- **Pivoting** across like properties. Once you’ve asked about an initial data set, pivoting allows you to retrieve additional nodes or edges that share some property in common with your original data. For example, you can retrieve the node representing a PE executable, and then pivot to any other PE executables that share the same PE import hash or the same PE compile time.

Despite their utility and increased use, directed graphs have certain limitations, most notably the “two-dimensionality” inherent in the concept of an edge. The fact that an edge can only connect exactly two nodes leads to a variety of consequences, including:

- **Performance.** Even though a directed graph edge can only join two nodes, in theory there is no limit to the total number of edges to or from a given node – you can have 100,000 followers on Twitter, connected to you by 100,000 edges. However, these “edge dense” or “heavy” nodes represent a potential performance limitation when attempting to conduct analysis across a large or complex directed graph. The computational resources required to traverse all of those edges, hold the resulting set of nodes in memory, and then perform additional operations on the results (filtering, pivoting, additional traversals, etc.) can become prohibitive.

- **Data Representation.** Some relationships involve more than two objects, which may require some creativity (or at the very least, additional overhead) to force them into a two-dimensional directed graph model. One side effect may be a multiplication of edges, as noted above; another may be the need to continually create specialized node types to represent arbitrary “clusters” of data or objects (basically combining what would normally be two or more nodes into a single node, simply so the cluster can be associated with another node via a single edge).

**Hypergraphs**

A **hypergraph** is a generalization of a graph in which an edge can join any number of nodes. Because an edge is no longer limited to joining exactly two nodes, edges in a hypergraph are often called **hyperedges**. If a directed graph where edges join exactly two nodes is “two-dimensional”, then a hypergraph where a hyperedge can join any number (n-number) of nodes can be considered **“n-dimensional”**.

Looked at another way, they key features of a hypergraph are:

- **Everything is a node.** “Things” (“nouns”) are still nodes in a hypergraph, similar to a regular graph. However, relationships (“verbs”) are now also represented as nodes. Looked at another way, where an edge in a graph consists of three objects (two nodes and the edge connecting them), in a hypergraph the same data is represented as a single multi-dimensional node.

- **Hyperedges connect arbitrary sets of nodes.** An edge in a regular graph connects two nodes, and can be easily visualized in two dimensions as a line or arrow connecting two points. A hyperedge can connect an arbitrary number of nodes; one way to attempt to visualize this is as a “shape” (though this doesn’t entirely escape the “nodes and edges” concept, and becomes increasingly difficult to visualize beyond three dimensions). The standard “visualization” for a hyperedge is as a set of disconnected nodes encircled by a boundary; the boundary represents the hyperedge “joining” the nodes into a related group. Just as there is no limit to the number of edges to or from a node in a directed graph, a node in a hypergraph can be joined by any number of hyperedges (e.g., be part of any number of “groups”).

In Synapse, hyperedges are represented by **tags,** which can be thought of as labels applied to nodes.

**Analysis with a Synapse Hypergraph**

Synapse is a specific implementation of a hypergraph model. Within Synapse, an individual hypergraph is called a **Cortex.** A Cortex is a scalable hypergraph implementation which also includes key/value-based node properties and a data model which facilitates normalization.

Analysis of data using a Cortex leverages some of the same methods as a directed graph: **lifting** nodes and **filtering** results are still part of the process. However, as noted above, in the absence of pairwise edges there is no **traversal.** Instead, all navigation is based on a **pivot.** (Technically, selecting a set of nodes from Synapse based on a tag could be considered “navigating” along a hyperedge. But mostly everything is a pivot.)

Synapse optimizes this ability to pivot across properties through two key design features: **type safety** and **property normalization.**

- **Type safety** ensures that node property types are explicitly declared and enforced across the data model. Where a property value is an IP address, for example, that IP address is declared and stored as an integer for consistency (as opposed to being stored as an integer in some instances and a dotted-decimal string in others).

- **Property normalization** ensures that properties are represented in a consistent manner for both storage and display purposes, regardless of the format in which they are received. Synapse takes a “do what I mean” approach to input where possible, attempting to recognize common formats and normalize them on the user’s behalf. This allows users to work with data in a way that should feel “natural”. For example, a user can enter an IP address as an integer, a hex string, or a dotted decimal notation; Synapse will automatically store the IP as an integer and represent it back to the user as a dotted-decimal string. Similarly, a user can enter a directory path using either Windows (``C:\foo\bar\baz.exe``) or Linux (``/home/user/foo/bar``) format and using any combination of upper and lowercase letters; Synapse will automatically enforce normalization such as the use of forward slashes for directory separators and the use of all lower-case letters for drive, path, and file names.

These features make pivoting highly effective because they ensure that data of the same type and / or with the same value is represented consistently throughout the Synapse hypergraph. In contrast, lack of consistency can cause analysts to miss relevant correlations - either because the same data is represented in multiple forms, or because the burden is placed on the analyst to “correctly” normalize their input when querying the system.

Synapse’s optimized use of pivots, combined with the ability to represent relationships (including complex “multi-dimensional” relationships) as nodes, provides some significant advantages over a directed graph. These include:

*Performance*

“Asking questions” of a hypergraph may be less computationally intensive than in a directed graph. As a simple example, let’s say you want to know all of the domains that have resolved to a particular IP address. “Resolves to” (“has a DNS A record for”) is a relationship (edge) in a directed graph, so to answer this question you first need to **lift** the node for the IP address and then **traverse** an arbitrary number of edges to return the set of nodes represented by the endpoints of all those edges. For a handful of edges (domains), this traversal is not very difficult; but if thousands of domains have resolved to that IP, traversing all of those edges becomes more computationally intensive.

Viewed another way - and depending on the specific implementation of the directed graph - a traversal may represent two pivots “under the hood”. Assume a generic representation of an edge as a tuple comprised of two nodes and the specific edge relationship ({n1,edge,n2}). “Traversing” from one set of nodes, along a specified edge, to a second set of nodes can be viewed as an initial pivot from a set of nodes to that set of edges where those nodes represent n1 of the edge; and then a second pivot from the set of n2s of those edges to the nodes that correspond to those n2s.

In a Cortex, a single node represents the “resolves to” relationship, with the domain and IP address involved in the relationship both stored as properties on that node. So you simply need to **lift** the set of “resolves to” nodes where the value of the IP address property is the IP you are interested in. Once you have the relevant set of “resolves to” nodes, you simply **pivot** from the set of “domain” properties to the set of nodes representing those domains.

*No Loss of Granularity*

As noted above, the pairwise nature of edges in a directed graph may result in a loss of granularity for complex relationships that realistically involve three or more elements as opposed to the two elements supported by a directed edge. In order to “fit” those relationships into a directed graph model, one solution is to arbitrarily combine some of those elements into a single node in order to force the relationship to be pairwise. This results in some loss of detail as elements that should rightly be treated as independent components are artificially conflated.

*Discovery*

“Asking questions of” or “exploring” a directed graph has some inherent limitations. First, since relationships are represented by edges, an analyst is limited to asking about (traversing) “known relationships” (that is, edges that are already defined in the model). This may limit the discovery of new or unexpected patterns or correlations.

Similarly, while directed graphs may support some navigation via pivots, analysts are often limited to pivoting via the same property / value on the same node type – for example, I can ask about all PE file nodes that have the same PE import hash value as a given PE file node because I am asking about the same value for the same property across the same node type. As noted above, Synapse’s type enforcement and property normalization remove this restriction.

In a directed graph it is harder to ask about a value that may be present in different properties on different node types. For example, let’s say you have a malicious domain and you determine the set of IP addresses that the domain has resolved to. You want to know if any of those IP addresses have also been used to send spear phishing email messages. Speaking generically, there is no readily apparent relationship between an IP address as the resolution of a domain, and an IP address as the source of an email message, other than the fact that they are both IP addresses. This lack of an apparent relationship (edge) implies that you can’t get your answer using a few simple traversals.

How you answer this question will vary depending on the specific implementation of the directed graph. However, if you assume an implementation with the following defined edges:

``<domain> -- <has DNS A record> --> <IP address>``

and 

``<IP address> -- <was source IP for> --> <RFC822 file>``

Then you may be able to obtain an answer through a multi-part query similar to the following:

1. Traverse the set of “has DNS A record” edges from the domain to obtain the set of IP addresses.
2. Traverse the set of “was source IP” edges from the resulting set of IP addresses to the set of RFC822 messages to get the messages (if any) associated with the IPs.
3. Traverse **back** along the “was source IP” edges from the RFC822 messages to get the IP addresses that were used to send email messages.

If the above sounds messy and a bit redundant, it’s because to an extent, it is. There may be slightly more “elegant” solutions given alternate directed graph implementations (for example, if the source IP of an email message was stored as a property on the email message node as opposed to being associated with the message via an edge). But it still requires some creative navigation amongst nodes, edges, and properties to find the answer.

In a Synapse hypergraph Cortex, the IP addresses appear as properties on both the set of “domain has DNS A record” nodes (as the “resolved to” property, for example) and the set of “spear phishing email nodes” (as the “source IP” property, for example). You can simply pivot between the two node types based on the value of those properties to find your answer. Not only is the navigation itself significantly easier, but you are able to readily ask questions across disparate or arbitrary data types (DNS records and email messages), as long as they share some value in common – even if that value represents a different property in each case.

**Conclusions**

Though hypergraphs may be less familiar conceptually than traditional graphs, they offer distinct performance and analytical advantages over directed graph models, addressing historical shortcomings in representation, navigation, and analytical capability. Synapse, as a specific implementation of a hypergraph model, incorporates additional design features (type safety, property normalization, and a robust query language, in addition to storage and indexing optimization for performance) that further enhance its power and flexibility as an analysis tool.







