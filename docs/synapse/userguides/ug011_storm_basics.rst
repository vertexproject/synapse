.. highlight:: none

Storm Query Language - Basics
=============================

Background
----------

**Storm** is the query language used to interact with data in a Synapse hypergraph. Storm allows you to ask about, retrieve, annotate, add, modify, and delete data from a Cortex.

Most Synapse users (e.g., those conducting analysis on the data) will access Storm via the command-line interface (CLI), using the ``ask`` command to invoke a Storm query. The Synapse CLI can invoke Storm operators directly – that is, calling the operator and passing appropriate parameters:

``cli> ask <operator>(<param_1>,<param_2>...<param_n>)``

``cli> ask lift(inet:fqdn,woot.com)``

That said, Storm is meant to be usable by analysts from a variety of knowledge domains who are not necessarily programmers and who may not be comfortable using operators in what feels like a “programming language”. For this reason, Storm has been designed to mask some of the underlying programmatic complexity. The intent is for Storm to act more like a “data language”, allowing knowledge domain users to:

* **Reference data and data types in an intuitive form.** Through features such as type safety and property normalization, Storm tries to take a “do what I mean” approach, removing the burden of translating or standardizing data from the user where possible.
* **Use a simplified syntax to run Storm queries.** In addition to the standard operator-based Storm syntax, most common operators support the use of a short-form **macro syntax** to make queries both more intuitive and more efficient (by allowing common queries to be executed with fewer keystrokes).

As an example of this simplification, analysts can ask Synapse about a node simply by specifying the node’s form and primary property value (``<form>=<value>``):

``cli> ask inet:ipv4=1.2.3.4``

Note that Storm accepts the IP address in its “intuitive” form (dotted decimal notation), even though Synapse stores IP addresses as integers (IP ``1.2.3.4`` is stored as integer ``16909060``). The analyst does not need to convert the IP to integer form to run the query, nor do they need to escape the IP with quotes (``“1.2.3.4”``) to indicate it is a string representation of the data. (Generally speaking, double quotes only need to be used when input contains characters that would otherwise be interpreted as "end of data" (space, comma) or other specialized input (e.g, escape characters) by the Synapse parser.)

In addition, the Storm syntax should feel intuitive to the user, like asking a question: “Tell me about (ask about) the IP address 1.2.3.4”. In reality, Storm translates that simplified syntax into the correct syntax for the underlying ``lift()`` operator, which actually retrieves the data:

``cli> ask inet:ipv4=1.2.3.4``

is equivalent to:

``cli> ask lift(inet:ipv4,1.2.3.4)``

Analysts still need to learn the Storm “language” and master enough command-line syntax to perform tasks and find help when necessary. However, the intent is for Storm to function more like “how do I ask this question of the data?” and not “how do I write a program to get the data I need?”

Finally – and most importantly – giving analysts direct access to Storm to allow them to create arbitrary queries provides them with an extraordinarily powerful analytical tool. Analysts are not constrained by working with a set of predefined queries provided to them through a GUI or an API. Instead, they can follow their analysis wherever it takes them, creating queries as needed and working with the data in whatever manner is most appropriate to their research.

Storm Operators
---------------

Storm is based on an underlying set of **operators** that allow interaction with a Synapse Cortex and its data. All Storm operators can be accessed from the Synapse command line interface via the ``ask`` command, using either operator syntax or the shortened macro syntax where available. Most operators (other than ``lift()`` and a few others used to select or retrieve data) require an existing data set on which to operate. This data set is typically the output of a previous Storm query whose results are the nodes you want to modify or otherwise work with. Operators may also require one or more parameters to further specify what you want to do with the result set.

Storm queries can be as simple as asking to lift a single node:

``cli> ask inet:fqdn=woot.com``

Alternately, they can be highly complex, chaining a series of operators to lift a set of nodes and perform a series of additional filter and pivot operations that follow a line of analysis across the data::

    cli> ask inet:fqdn*tag=tc.t12 -> inet:dns:a:fqdn inet:dns:a:ipv4 -> inet:ipv4
        -#anon.tor -#anon.vpn -> inet:dns:a:ipv4 inet:dns:a:fqdn -> inet:fqdn

The second query above represents a common analytical workflow to research potentially malicious infrastructure. It takes a set of “known bad” domains, moves to the IP addresses those domains have resolved to, excludes some potentially irrelevant IPs, and then moves to other domains that have resolved to those IPs. Domains that resolved to the same IP address(es) as our “known bad” domains during the same time period may also be associated with our threat group. The query is broken down below; note how each new component builds on the previous query to follow a line of analysis and refine results:

* Lift all domains tagged as part of Threat Group 12 (``inet:fqdn*tag=tc.t12``)
* Pivot from those domains to DNS A record nodes that have those domains (``-> inet:dns:a:fqdn``)
* Pivot from those DNS A record nodes to the IP addresses those domains have resolved to (``inet:dns:a:ipv4 -> inet:ipv4``)
* Remove any IP addresses tagged as TOR exit nodes (``-#anon.tor``)
* Remove any IP addresses tagged as anonymous VPN infrastructure (``-#anon.vpn``)
* Pivot from those remaining IP addresses to any DNS A records where those IPs were present (``-> inet:dns:a:ipv4``)
* Pivot from those DNS A records to the domains associated with those records (``inet:dns:a:fqdn -> inet:fqdn``)

Operator Categories
-------------------

Storm operators can be divided into broad categories based on their typical use:

* **Data modification** – add, modify, annotate, and delete nodes from a Cortex.
* **Lift (query) operators** – retrieve data based on specified criteria.
* **Filter operators** – take a set of lifted nodes and refine your results by including or excluding a subset of nodes based on specified criteria.
* **Pivot operators** -  take a set of lifted nodes and identify other nodes that share one or more properties or property values with the lifted set.
* **Lift and filter (“by” handlers)** – optimize certain queries by lifting and filtering nodes concurrently.
* **Statistical operators** – specialized operators to calculate statistics over a set of nodes.
* **Miscellaneous operators** – various special purpose operators that do not fit into one of the above categories.

Storm and the Synapse CLI
-------------------------

Recall that when accessing Storm from the Synapse command line, the ``ask`` command indicates that subsequent input represents a Storm query. Storm queries executed from the Synapse CLI must all be preceded by the ``ask`` command:

``cli> ask <query>``

Lift, Filter, and Pivot Criteria
--------------------------------

Working with Synapse data commonly involves three broad types of operations:

* **Lifting** data (selecting a set of nodes).
* **Filtering** data (down-selecting a subset of nodes from an existing set of nodes).
* **Pivoting** across data ("navigating" the hypergraph by moving from an existing set of nodes to another set of nodes that share some property and / or value with the original set).

Whether lifting, filtering, or pivoting across data in a Cortex, you need to be able to clearly specify the data you’re interested in – your selection criteria. In most cases, the criteria you specify will be based on one or more of the following:

* A **property** (primary or secondary) on a node.
* A **specific value** for a property (``<form>=<value>`` or ``<prop>=<value>``) on a node.
* A **tag** on a node.

All of the above elements – nodes, properties, values, and tags – are the fundamental `building blocks`__ of the Synapse data model. **As such, an understanding of the Synapse data model is essential to effective use of Storm.**

"Good" and "Bad" Queries
------------------------

Storm is meant to be flexible as well as performant across large and diverse data sets. There is no single "right" way to use Storm to ask a question of the hypergraph data. However, there are definitely "better" (more efficient or more performant) ways to ask a question. Given that there is typically more than one "path" to an answer (more than one way to ask the question), analysts should consider which path may be more optimal (or at least consider which path is **not** optimal) when formulating a Storm query.

Crafting an optimal query can mean the difference between quickly receiving a meaningful response and waiting for Synapse to return a response because it is processing an excessive amount of data. Synapse currently has no built-in timeouts or other limits (such as total number of nodes lifted) on Storm queries, though these "safety nets" are planned for a future release. Asking a "bad" (non-performant) question will not harm Synapse, but it may frustrate analysts waiting for their CLI to return a response.

As a simple example of a "bad" vs "good" query, let's say you want to lift all of the IP addresses that are part of the threat cluster (the set of associated indicators) for Threat Group 12. There are two key components to the data you want to ask about: IP addresses (``inet:ipv4``), represented by a set of nodes; and the Threat Group 12 threat cluster, represented by a tag (``tc.t12``) applied to the relevant nodes.

Two ways to ask that question using Storm are:

* Lift all of the IP addresses in Synapse, then filter down to only those tagged as part of the Threat Group 12 threat cluster:

``cli> ask inet:ipv4 +#tc.t12``

* Lift all of the nodes tagged as part of the Threat Group 12 threat cluster, then filter down to only IP address nodes:

``cli> ask #tc.t12 +inet:ipv4``

The first query is problematic because it first asks Storm to return **all** ``inet:ipv4`` nodes within the hypergraph – potentially hundreds of thousands, or even millions of nodes, depending on how densely populated the hypergraph is (mathematically speaking, there are over four billion possible IPv4 addresses). Synapse has to lift **all** of those ``inet:ipv4`` nodes into memory and then select only those nodes with the ``tc.t12`` tag. The query is likely to take an extremely long time to return or to time out entirely (at least until query limits are incorporated into Synapse), and therefore represents a "bad" query.

The second query first asks Storm to return **all** nodes tagged with ``tc.t12``. This may still be a large number depending on how much analysis and annotation has been performed related to Threat Group 12. However, the number of nodes tagged ``tc.t12`` will still be much smaller than the number of ``inet:ipv4`` nodes within a hypergraph. As such, the second query is more efficient or performant, and represents a "good" (or at least "better" query).

(**Note:** The previous example is used for simple illustrative purposes. Technically, the "best" way to ask this particular question would be to use what is called a Storm "by" handler (represented by the asterisk ( ``*`` ) to "lift by tag":

``cli> ask inet:ipv4*tag=tc.t12``

"By" handlers are specifically designed to further optimize certain queries by lifting and filtering nodes concurrently, as opposed to lifting nodes and then filtering the results.)

.. _blocks: ../userguides/ug003_dm_basics.html
__ blocks_
