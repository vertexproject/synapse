.. highlight:: none

.. _storm-ref-intro:

Storm Reference - Introduction
==============================

**Storm** is the query language used to interact with data in a Cortex. Storm allows you to ask about, retrieve, annotate, add, modify, and delete data from a Cortex. Most Synapse users (e.g., those conducting analysis on the data) will access Storm via the Synapse  **cmdr** command-line interface (CLI) (see :ref:`syn-tools-cmdr`), using the :ref:`syn-storm` command to invoke a Storm query:

``cli> storm <query>``

This section covers the following important high-level Storm concepts:

- `Storm Background`_
- `Basic Storm Operations`_

  - `Lift, Filter, and Pivot Criteria`_
  
- `Advanced Storm Operations`_
- `Storm Operating Concepts`_

  - `Operation Chaining`_
  - `Storm as a Pipeline`_
  - `Node Consumption`_

.. _storm-bkgd:

Storm Background
----------------

In designing Storm, we needed it to be flexible and powerful enough to allow interaction with large amounts of data and a wide range of disparate data types. However, we also needed Storm to be intuitive and efficient so it would be accessible to a wide range of users. We wrote Storm specifically to be used by analysts and other users from a variety of knowledge domains who are not necessarily programmers and who would not want to use what felt like a "programming language".

Wherever possible, we masked Storm’s underlying programmatic complexity. The intent is for Storm to act more like a "data language", allowing users to:

- **Reference data and query parameters in an intuitive form.** Through features such as type safety, property normalization, and syntax and query optimization, Storm takes a "do what I mean" approach. To the extent possible, Storm removes the burden of translating or standardizing data from the user.

- **Use a simple yet powerful syntax to run Storm queries.** To avoid feeling like a programming language (or even a traditional database query language), Storm avoids the use of operator-like functions and parameters. Instead, Storm:
  
  - Leverages intuitive keyboard symbols for efficient querying.
  - Uses a natural language-like syntax so using Storm feels more like "asking a question" than "constructing a data query".

Analysts still need to learn the Storm "language" - forms (:ref:`data-form`) and tags (:ref:`data-tag`) are Storm's "words", and the Storm syntax allows you to construct "sentences". That said, the intent is for Storm to function more like "how do I ask this question of the data?" and not "how do I write a program to get the data I need?"

Finally – and most importantly – **giving analysts direct access to Storm to allow them to create arbitrary queries provides them with an extraordinarily powerful analytical tool.** Analysts are not constrained by working with a set of predefined queries provided to them through a GUI or an API. Instead, they can follow their analysis wherever it takes them, creating queries as needed and working with the data in whatever manner is most appropriate to their research.

.. _storm-ops-basic:

Basic Storm Operations
----------------------

Storm allows users to perform all of the common operations used to interact with the data in a Cortex:

- **Lift:** – retrieve data based on specified criteria. (:ref:`storm-ref-lift`)
- **Filter:** – take a set of lifted nodes and refine your results by including or excluding a subset of nodes based on specified criteria. (:ref:`storm-ref-filter`)
- **Pivot:** – take a set of lifted nodes and identify other nodes that share one or more properties or property values with the lifted set. (:ref:`storm-ref-pivot`)
- **Data modification:** – add, modify, annotate, and delete nodes from a Cortex. (:ref:`storm-ref-data-mod`)

Additional operations include:

- **Traverse** light edges. (:ref:`light-edge` :ref:`walk-light-edge`)
- **Pipe** (send) nodes to Storm commands (:ref:`storm-ref-cmd`). Storm supports an extensible set of commands such as :ref:`storm-limit`, :ref:`storm-max`, or :ref:`storm-uniq` support specific functionality to further extend the power of Storm. Available commands can be displayed with ``storm help``. Additional functionality (such as connectors to third-party data sources) can be implemented in Storm and exposed as commands.

Storm also supports powerful features such as the use of **variables** (:ref:`storm-adv-vars`) in queries, the availability of **libraries** (:ref:`stormtypes-libs-header`) to extend Storm's functionality, and the ability to issue **subqueries** (:ref:`storm-ref-subquery`) within Storm itself.

.. NOTE::

  While Storm queries can range from the very simple to the highly complex, all Storm queries are constructed from this relatively small set of "building blocks" - and unless you're working with more advanced Storm, you'll only need a handful of blocks: typically lift, filter, pivot, traverse light edges, and pipe to Storm commands.


Lift, Filter, and Pivot Criteria
++++++++++++++++++++++++++++++++

The main operations carried out with Storm are lifting, filtering, and pivoting (we include traversing light edges as part of "pivoting"). When conducting these operations, you need to be able to clearly specify the data you are interested in – your selection criteria. In most cases, the criteria you specify will be based on one or more of the following:

- A **property** (primary or secondary) on a node.
- A specific **value** for a property (*<form> = <valu>* or *<prop> = <pval>*) on a node.
- A **tag** on a node.
- The existence of a **light edge** linking nodes.
- The name ("verb") of a specific **light edge** linking nodes. 

All of the above elements – nodes, properties, values, and tags – are the fundamental building blocks of the Synapse data model (see :ref:`data-model-terms`). **As such, an understanding of the Synapse data model is essential to effective use of Storm.**

.. _storm-ops-adv:

Advanced Storm Operations
-------------------------

In our experience, the more analysts use Storm, the more they want even greater power and flexibility from the language to support their analytical workflow. To meet these demands, Storm evolved a number of advanced features, including:

- Subqueries (:ref:`storm-ref-subquery`)
- Variables (:ref:`storm-adv-vars`)
- Methods (:ref:`storm-adv-methods`)
- Libraries (:ref:`storm-adv-libs`)
- Control Flow (:ref:`storm-adv-control`)

**Analysts do not need to use or understand these more advanced concepts in order to use Storm or Synapse.** Basic Storm functions are sufficient for a wide range of analytical needs and workflows. However, these additional features are available to both “power users” and developers as needed:

- For analysts, once they are comfortable with Storm basics, many of them want to expand their Storm skills **specifically because it facilitates their analysis.**
- For developers, writing extensions to Synapse in Storm has the advantage that the extension **can be deployed or updated on the fly.** Contrast this with extensions written in Python, for example, which would require restarting the system during a maintenance window in order to deploy or update the code.

.. _storm-op-concepts:

Storm Operating Concepts
------------------------

Storm has several notable features in the way it interacts with and operates on data. Understanding these features is important to using Storm in general, and essential to using more advanced Storm operations effectively.

.. _storm-op-chain:

Operation Chaining
++++++++++++++++++

As noted above, users commonly interact with data (nodes) in a Cortex using operations such as lift, filter, and pivot. Storm allows multiple operations to be chained together to form increasingly complex queries. When Storm operations are concatenated in this manner, they are processed **in order from left to right** with each operation (lift, filter, or pivot) acting on the output of the previous operation.

..  NOTE::

  The initial set of nodes in any Storm query (i.e., the set of nodes selected by your first lift operation) is known as your **initial working set**.
  
Note that most operations (other than those used solely to lift or add data) require an existing data set on which to operate. This data set is typically the output of a previous Storm operation - the previous operation in the chain - whose results are the nodes you want to modify or otherwise work with.

.. NOTE::

  The output of any Storm operations (other than your initial lift) is known as your **current working set**. Depending on the operation(s) performed, your current working set may not be the same as your initial working set (see :ref:`storm-node-consume` below). Your working set emerges from one Storm operation and is considered **inbound** to the next operation in the chain.

From an analysis standpoint, this means that Storm syntax can parallel an analyst’s natural thought process, as you perform one Storm operation, and then consider the "next step" you want to take in your analysis: "show me X data...that’s interesting, take a subset of X data and show me the Y data that relates to X...hm, now take the results from Y and show me any relationship to Z data..." and so on.

From a practical standpoint, it means that **order matters** when constructing a Storm query. A lengthy Storm query is not evaluated as a whole. Instead, Synapse parses each component of the query in order, evaluating each component individually.

(Technically, any query you construct is first evaluated as a whole **to ensure it is a valid query** - that is, the query uses valid Storm syntax; Synapse will complain about invalid Storm. Once Synapse has checked your Storm syntax, nodes are processed by each Storm operation in order.)

.. _storm-pipeline:

Storm as a Pipeline
+++++++++++++++++++

Most objects in a Cortex are nodes (:ref:`data-node`), so most Storm operations act on nodes. Not only are chained Storm operations carried out from left to right, but **nodes pass individually through the chain.** The series of Storm operations (i.e., the overall Storm query) can be thought of as a "pipeline". Regardless of how simple or complex the Storm query is, and regardless of whether your initial working set consists of one node or 100,000 nodes, each node is "fired" through the query pipeline one at a time.

A key advantage of this behavior is that it provides significant latency and memory use reduction to Storm. Because nodes are operated on one at a time, Storm can start returning results immediately even if the initial data set is quite large.

Outside of this latency reduction, Storm’s "pipeline" behavior is generally transparent to a user — from the user’s standpoint, they write a query to operate on data, and data comes back as a result of that query. However, this pipeline behavior can be important to understand when working with (or troubleshooting) Storm queries that leverage features such as subqueries, variables, or control flow operations.

.. _storm-node-consume:

Node Consumption
++++++++++++++++

Most Storm operations **consume** nodes when the operation occurs. That is, the set of nodes (the working set) that is **inbound** to a particular Storm operation is typically transformed by that operation in some way. In fact, with few exceptions (such as the join operator (see :ref:`storm-ref-pivot`) and the Storm :ref:`storm-count` command), the nodes inbound to an operation are typically **not** retained - they are "consumed" during execution. Storm outputs only those nodes that result from carrying out the specified operation. If you lift a set of nodes and then filter the results, only those nodes captured by the filter are retained - the other nodes are consumed (discarded).

In this way the operations performed in sequence may add or remove nodes from Storm’s working set, or clear the set entirely. The set is continually changing based on the last-performed operation or last-issued command. Particularly when first learning Storm, users are encouraged to break down lengthy queries into their component parts, and to validate the output (results) after the addition of each operation to the overall query.
