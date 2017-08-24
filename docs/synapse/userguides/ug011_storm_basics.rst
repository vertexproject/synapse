.. highlight:: none

Storm Query Language - Basics
=============================

Background
----------

**Storm** is the query language used to interact with data in a Synapse hypergraph. Storm allows you to ask about, retrieve, annotate, add, modify, and delete data from a Cortex.

Most Synapse users (e.g., those conducting analysis on the data) will access Storm via the command-line interface (CLI), using the Synapse ``ask`` command to invoke a Storm query:

.. parsed-literal::
  cli> **ask** *<query>*

Storm is based on an underlying set of **operators** that allow interaction with a Synapse Cortex and its data. The Synapse CLI can invoke Storm operators directly – that is, calling the operator and passing appropriate parameters:

.. parsed-literal::
  cli> **ask** *<operator>* **(** *<param_1>* **,** *<param_2>* ... *<param_n>* **)**
  
For example:

``cli> ask lift(inet:fqdn,woot.com)``

That said, Storm is meant to be usable by analysts from a variety of knowledge domains who are not necessarily programmers and who may not be comfortable using operators in what feels like a “programming language”. For this reason, Storm has been designed to mask some of the underlying programmatic complexity. The intent is for Storm to act more like a “data language”, allowing knowledge domain users to:

* **Reference data and data types in an intuitive form.** Through features such as type safety and property normalization, Storm tries to take a “do what I mean” approach, removing the burden of translating or standardizing data from the user where possible.
* **Use a simplified syntax to run Storm queries.** In addition to the standard operator-based Storm syntax (**operator syntax**), most common operators support the use of a short-form **macro syntax** to make queries both more intuitive and more efficient (by allowing common queries to be executed with fewer keystrokes).

As an example of this simplification, analysts can ask Synapse about a node simply by specifying the node’s form and primary property value (``<form>=<valu>``):

``cli> ask inet:ipv4=1.2.3.4``

Note that Storm accepts the IP address in its “intuitive” form (dotted decimal notation), even though Synapse stores IP addresses as integers (IP ``1.2.3.4`` is stored as integer ``16909060``). The analyst does not need to convert the IP to integer form to run the query, nor do they need to escape the IP with quotes (``"1.2.3.4"``) to indicate it is a string representation of the data. (Generally speaking, double quotes only need to be used when input contains characters that would otherwise be interpreted as "end of data" (space, comma) or other specialized input (e.g, escape characters) by the Synapse parser.)

In addition, the Storm syntax should feel intuitive to the user, like asking a question: “Tell me about (ask about) the IP address 1.2.3.4”. Analysts still need to learn the Storm “language” and master enough command-line syntax to perform tasks and find help when necessary. However, the intent is for Storm to function more like “how do I ask this question of the data?” and not “how do I write a program to get the data I need?”

Finally – and most importantly – giving analysts direct access to Storm to allow them to create arbitrary queries provides them with an extraordinarily powerful analytical tool. Analysts are not constrained by working with a set of predefined queries provided to them through a GUI or an API. Instead, they can follow their analysis wherever it takes them, creating queries as needed and working with the data in whatever manner is most appropriate to their research.

Storm Operators
---------------

Operators implement various Storm functions such as retrieving nodes, applying tags, or pivoting across data. Operators can be divided into broad categories based on their typical use:

* **Data modification** – add, modify, annotate, and delete nodes from a Cortex.
* **Lift (query) operators** – retrieve data based on specified criteria.
* **Filter operators** – take a set of lifted nodes and refine your results by including or excluding a subset of nodes based on specified criteria.
* **Pivot operators** -  take a set of lifted nodes and identify other nodes that share one or more properties or property values with the lifted set.
* **Lift and filter (“by” handlers)** – optimize certain queries by lifting and filtering nodes concurrently.
* **Statistical operators** – specialized operators to calculate statistics over a set of nodes.
* **Miscellaneous operators** – various special purpose operators that do not fit into one of the above categories.

Most operators (other than those used solely to lift data) require an existing data set on which to operate. This data set is typically the output of a previous Storm operator whose results are the nodes you want to modify or otherwise work with.

Lift, Filter, and Pivot Criteria
--------------------------------

Working with Synapse data commonly involves three broad types of operations:

* **Lifting** data (selecting a set of nodes).
* **Filtering** data (down-selecting a subset of nodes from an existing set of nodes).
* **Pivoting** across data ("navigating" the hypergraph by moving from an existing set of nodes to another set of nodes that share some property and / or value with the original set).

Whether lifting, filtering, or pivoting across data in a Cortex, you need to be able to clearly specify the data you’re interested in – your selection criteria. In most cases, the criteria you specify will be based on one or more of the following:

* A **property** (primary or secondary) on a node.
* A **specific value** for a property (``<form>=<valu>`` or ``<prop>=<pval>``) on a node.
* A **tag** on a node.

All of the above elements – nodes, properties, values, and tags – are the fundamental `building blocks`__ of the Synapse data model. **As such, an understanding of the Synapse data model is essential to effective use of Storm.**

Operator Chaining
-----------------

Storm allows multiple operators to be chained together to form increasingly complex queries. Storm operators are processed **in order from left to right** with each operator acting on the current result set (e.g., the output of the previous operator).

From an analysis standpoint, this feature means that Storm can parallel an analyst's natural thought process: "show me X data...that's interesting, show me the Y data that relates to X...hm, take only this subset of results from Y and show me any relationship to Z data…" and so on.

From a practical standpoint, it means that **order matters** when constructing a Storm query. A lengthy Storm query is not evaluated as a whole. Instead, Synapse parses each component of the query in order, evaluating each component individually as it goes. The Storm runtime(s) executing the query keep a list of lifted nodes in memory while performing the requested lifts, pivots, data modification, and so on. The operators used may add or remove nodes from this "working set", or clear the set entirely; as such the in-memory set is continually changing based on the last-used operator. Particularly when first learning Storm, users are encouraged to break down complex queries into their component parts, and to validate the output (results) after the addition of each operator to the overall query.

Syntax Conventions
------------------

The Synapse documentation provides numerous examples of both abstract Storm syntax (usage statements) and specific Storm queries. The following conventions are used for Storm usage statements:

* Items that must be entered literally on the command line are in **bold.** These items include the command name and literal characters.
* Items representing variables that must be replaced by a name are in *italics*.
* **Bold** brackets are literal characters. Parameters enclosed in non-bolded brackets are optional.
* Parameters **not** enclosed in brackets are required.
* A vertical bar signifies that you choose only one parameter. For example, ``[ a | b ]`` indicates that you can choose a, b, or nothing.
* Ellipses ( ``...`` ) signify the parameter can be repeated on the command line.

Whitespace may be used in the examples for formatting and readability. Synapse will parse Storm input with or without whitespace (e.g., the Synapse parser will strip / ignore whitespace in Storm queries; the exception is that whitespace within double-quoted strings is preserved, such as the timestamp in the example below). 

For example, the following Storm queries are equivalent to the Synapse parser:

``addnode( inet:fqdn , woot.com , : created = "2017-08-15 01:23" )``

``addnode(inet:fqdn,woot.com,:created="2017-08-15 01:23")``

Examples of **specific** queries represent fully literal input, but are not shown in bold for readability. For example:

*Usage statement:*

.. parsed-literal::
  **addnode(** *<form>* **,** *<valu>* **,** [ **:** *<prop>* **=** *<pval>* **,** ...] **)**

*Specific query:*

``addnode(inet:fqdn,woot.com)``

Operator Syntax vs. Macro Syntax
--------------------------------

Storm operators function similar to a programming language, where the operator acts as a function and the operator's parameters act as input to that function. With very few exceptions, all Storm operators can be used at the Synapse command line by invoking the Synapse ``ask`` command, calling the appropriate Storm operator, and passing appropriate parameters to the operator; this is known as **operator syntax** and provides the most complete access to Storm's functionality.

While Storm's operator syntax is both detailed and complete, it has a few drawbacks:

* It can feel very "code-like", particularly to analysts or other Synapse users who are not programmers.
* It has few optimizations, meaning that every operator and its associated parameters must be typed in full. This can become tedious for users who interact heavily with Synapse using Storm.

To address these issues, Storm also supports what is known as **macro syntax.** Macro syntax acts as a sort of "shorthand" through techniques such as:

* Replacing operators with equivalent intuitive symbols.
* Allowing the omission of explicit operator names or parameters where there is an obvious default value.

The macro syntax is meant to be both more efficient (requiring fewer keystrokes) and more intuitive, a "data language" for asking questions of the data as opposed to a programming language for retrieving data from a data store.

While not every operator has a macro syntax equivalent, the most commonly used operators have been implemented both ways. When Storm macro syntax is used at the CLI, Synapse automatically "translates" the macro syntax to the equivalent operator syntax in order to execute the requested query.

Two examples – one simple, one more complex – illustrate the differences between the two.

*Example 1*

The most basic Storm query simply lifts (retrieves) a single node (such as the domain ``woot.com``) using the ``lift()`` operator:

``cli> ask lift(inet:fqdn,woot.com)``

The same query can be executed as follows using macro syntax:

``cli> ask inet:fqdn=woot.com``

Note that in macro syntax, the ``lift()`` operator – the most fundamental Storm operator – is eliminated entirely; macro syntax assumes you want to retrieve (lift) nodes unless you specify otherwise. Similarly, instead of entering comma-separated parameters as input to the operator, macro syntax supports the use of the simple ``<prop>=<valu>`` pattern to ask about the node in question.

*Example 2*

The usefulness of macro syntax is even more apparent with longer, more complex queries. Storm allows users to chain operators together to lift a set of nodes and perform a series of additional filter and pivot operations that follow a line of analysis across the data.

In the knowledge domain of cyber threat data, there is a common analytical workflow used to research potentially malicious infrastructure. This line of analysis takes a set of “known bad” domains (for example, those associated with a known threat cluster), identifies the IP addresses those domains have resolved to, excludes some potentially irrelevant IPs, and then identifies other domains that have resolved to those IPs. Domains that resolved to the same IP address(es) as the “known bad” domains during the same time period may be associated with the same threat.

The full query for this line of analytical reasoning using operator syntax would be::

  cli> ask lift(inet:fqdn,by=tag,tc.t12) pivot(inet:fqdn,inet:dns:a:fqdn) 
    pivot(inet:dns:a:ipv4,inet:ipv4) -#anon.tor -#anon.vpn 
    pivot(inet:ipv4,inet:dns:a:ipv4) pivot(inet:dns:a:fqdn,inet:fqdn)

The same query using macro syntax would be::

  cli> ask inet:fqdn*tag=tc.t12 -> inet:dns:a:fqdn :ipv4 -> inet:ipv4 -#anon.tor -#anon.vpn
    -> inet:dns:a:ipv4 :fqdn -> inet:fqdn
  
The components of the query are broken down below; note how each new component builds on the previous query to follow the line of analysis and refine results:

+-------------------------+----------------------------------------+--------------------------------------------------+
| Request                 | Operator & Macro Syntax                | Macro Syntax Notes                               |
+=========================+========================================+==================================================+
| List all nodes tagged as| Operator                               | - Omit "lift(...)" operator                      |
| part of Threat Cluster  |   ``lift(inet:fqdn,by=tag,tc.t12)``    | - Asterisk (``*``) substitus for "by" paramerter |
| 12                      | Macro                                  |                                                  |
|                         |   ``inet:fqdn*tag=tc.12``              |                                                  |
+-------------------------+----------------------------------------+--------------------------------------------------+
| Pivot from these domains| Operator                               | - Omit the "form" parameter in pivot             |
| to DNS A record nodes   |   ``pivot(inet:fqdn,inet:dns:a:fqdn)`` |   (``inet:fqdn``) as it is the primary property  |
| that haves those domains| Macro                                  |   of our working result set (ie. default input   |
|                         |   ``-> inet:dns:a:fqdn``               |   value).                                        |
|                         |                                        | - Arrow (``->``) substitutes for "pivot" operator|
+-------------------------+----------------------------------------+--------------------------------------------------+
| Pivot from those DNA A  | Operator                               | - Arrow ( ``->`` ) substitutes for "pivot"       |
| record nodes to the IP  |   ``pivot(inet:dns:a:ipv4,inet:ipv4)`` |   operator                                       |
| addresses those domains | Macro                                  |                                                  |
| have resolved too       |   ``:ipv4 -> inet:ipv4``               |                                                  |
+-------------------------+----------------------------------------+--------------------------------------------------+
| Remove any IP addresses | Operator                               | - Filter operation; this minus (``-``) represents|
| tagged as TOR exit nodes|   No Operator syntax available         |   an exclusion filter.                           |
|                         | Macro                                  | - Hash (``#``) substitutes for "tag"             |
|                         |   ``-#anon.tor``                       |                                                  |
+-------------------------+----------------------------------------+--------------------------------------------------+
| Remove any IP addresses | Operator                               | - Filter operation; this minus (``-``) represents|
| tagged as anonymous VPN |   No Operator syntax available         |   an exclusion filter.                           |
| infrastructure.         | Macro                                  | - Hash (``#``) substitutes for "tag"             |
|                         |   ``-#anon.vpn``                       |                                                  |
+-------------------------+----------------------------------------+--------------------------------------------------+
| Pivot from those        | Operator                               | - Omit "from" parameter in pivot (``inet:ipv4``) |
| remaining IP addresses  |   ``pivot(inet:ipv4,inet:dns:a:ipv4)`` |   as it is the primary property of our working   |
| to any DNS A records    | Macro                                  |   result set.                                    |
| where those IPs were    |   ``-> inet:dns:a:ipv4``               | - Arrow ( ``->`` ) substitutes for "pivot"       |
| present                 |                                        |   operator                                       |
+-------------------------+----------------------------------------+--------------------------------------------------+
| Pivot from those DNS A  | Operator                               | - Arrow ( ``->`` ) substitutes for "pivot"       |
| records to the domains  |   ``pivot(inet:dns:a:fqdn,inet:fqdn)`` |   operator                                       |
| associated with those   | Macro                                  |                                                  |
| records                 |   ``:fqdn -> inet:fqdn``               |                                                  |
+-------------------------+----------------------------------------+--------------------------------------------------+

**Note:** Filter operations at the command line (CLI) are performed using macro syntax; there is no equivalent operator syntax.

See the Storm reference guides or a detailed discussion of individual operators and their operator and / or macro syntax.

Query Optimization - "Good" and "Bad" Queries
---------------------------------------------

Storm is meant to be flexible as well as performant across large and diverse data sets. There is no single "right" way to use Storm to ask a question of the hypergraph data. However, there are definitely "better" (more efficient or more performant) ways to ask a question. Given that there is typically more than one "path" to an answer (more than one way to ask the question), analysts should consider which path may be more optimal (or at least consider which path is **not** optimal) when formulating a Storm query.

Crafting an optimal query can mean the difference between quickly receiving a meaningful response and waiting for Synapse to return a response because it is processing an excessive amount of data. Synapse currently has no built-in timeouts or other limits (such as total number of nodes lifted) on Storm queries, though these "safety nets" are planned for a future release. Asking a "bad" (non-performant) question will not harm Synapse, but it may frustrate analysts waiting for their CLI to return a response.

As a simple example of a "bad" vs "good" query, let's say you want to lift all of the IP addresses that are associated with Threat Cluster 12. There are two key components to the data you want to ask about: IP addresses (``inet:ipv4``), represented by a set of nodes; and the activity (set of related indicators) known as Threat Cluster 12, represented by a tag (``tc.t12``) applied to the relevant nodes.

Two ways to ask that question using Storm are:

* Lift all of the IP addresses in Synapse, then filter down to only those tagged as part of Threat Cluster 12:

``cli> ask inet:ipv4 +#tc.t12``

* Lift all of the nodes tagged as part of Threat Cluster 12, then filter down to only IP address nodes:

``cli> ask #tc.t12 +inet:ipv4``

The first query is problematic because it first asks Storm to return **all** ``inet:ipv4`` nodes within the hypergraph – potentially hundreds of thousands, or even millions of nodes, depending on how densely populated the hypergraph is (mathematically speaking, there are over four billion possible IPv4 addresses). Synapse has to lift **all** of those ``inet:ipv4`` nodes into memory and then select only those nodes with the ``tc.t12`` tag. The query is likely to take an extremely long time to return (at least until query limits are incorporated into Synapse), and therefore represents a "bad" query.

The second query first asks Storm to return **all** nodes tagged with ``tc.t12``. This may still be a large number depending on how much analysis and annotation has been performed related to Threat Cluster 12. However, the number of nodes tagged ``tc.t12`` will still be much smaller than the number of ``inet:ipv4`` nodes within a hypergraph. As such, the second query is more efficient or performant, and represents a "good" (or at least "better" query).

(**Note:** The previous example is used for simple illustrative purposes. Technically, the "best" way to ask this particular question would be to use what is called a Storm "by" handler (represented by the asterisk ( ``*`` )) to "lift by tag":

``cli> ask inet:ipv4*tag=tc.t12``

"By" handlers are specifically designed to further optimize certain queries by lifting and filtering nodes concurrently, as opposed to lifting nodes and then filtering the results.)

.. _blocks: ../userguides/ug003_dm_basics.html
__ blocks_
