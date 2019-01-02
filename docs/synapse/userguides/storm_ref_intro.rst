



.. _storm-ref-intro:

Storm Reference - Introduction
==============================

Storm (:ref:`bkd-storm`) is the query language used to interact with data in a Cortex. Storm allows you to ask about, retrieve, annotate, add, modify, and delete data from a Cortex. Most Synapse users (e.g., those conducting analysis on the data) will access Storm via the command-line interface (CLI), using the Synapse ``storm`` command to invoke a Storm query:

``cli> storm <query>``

This section covers the following important Storm background concepts:

- `Storm Operations`_
- `Lift, Filter, and Pivot Criteria`_
- `Operation Chaining`_
- `Node Consumption`_

Storm Operations
----------------

Storm allows users to perform all of the standard operations used to interact with a Cortex:

- **Lift:** – retrieve data based on specified criteria. (:ref:`storm-ref-lift`)
- **Filter:** – take a set of lifted nodes and refine your results by including or excluding a subset of nodes based on specified criteria. (:ref:`storm-ref-filter`)
- **Pivot:** – take a set of lifted nodes and identify other nodes that share one or more properties or property values with the lifted set. (:ref:`storm-ref-pivot`)
- **Data modification:** – add, modify, annotate, and delete nodes from a Cortex. (:ref:`storm-ref-data-mod`)

Most operations (other than those used solely to lift or add data) require an existing data set on which to operate. This data set is typically the output of a previous Storm operation whose results are the nodes you want to modify or otherwise work with.

In addition to these operations, the Storm query language supports an extensible set of Storm commands (:ref:`storm-ref-cmd`). Commands such as ``limit``, ``noderefs``, or ``uniq`` support specific functionality to further extend the power of Storm. Available commands can be displayed with ``storm help``.

Storm also supports powerful features such as the use of **variables** (:ref:`storm-ref-vars`) in queries and the ability to issue **subqueries** (:ref:`storm-ref-subquery`) within Storm itself.

Lift, Filter, and Pivot Criteria
--------------------------------

The main operations carried out with Storm are lifting, filtering, and pivoting. When conducting these operations, you need to be able to clearly specify the data you are interested in – your selection criteria. In most cases, the criteria you specify will be based on one or more of the following:

- A **property** (primary or secondary) on a node.
- A specific **value** for a property (*<form> = <valu>* or *<prop> = <pval>*) on a node.
- A **tag** on a node.

All of the above elements – nodes, properties, values, and tags – are the fundamental building blocks of the Synapse data model (:ref:`bkd_data_model`). **As such, an understanding of the Synapse data model is essential to effective use of Storm.**

Operation Chaining
------------------

Storm allows multiple operations to be chained together to form increasingly complex queries. Storm operations are processed **in order from left to right** with each operation (lift, filter, or pivot) acting on the current result set (e.g., the output of the previous operation).

From an analysis standpoint, this feature means that Storm syntax can parallel an analyst’s natural thought process: "show me X data…that’s interesting, take a subset of X data and show me the Y data that relates to X...hm, now take the results from Y and show me any relationship to Z data..." and so on.

From a practical standpoint, it means that **order matters** when constructing a Storm query. A lengthy Storm query is not evaluated as a whole. Instead, Synapse parses each component of the query in order, evaluating each component individually.

Node Consumption
----------------

Most Storm operations **consume** nodes when the operation occurs. That is, the set of nodes input into a particular Storm operation is typically transformed by that operation in some way. With few exceptions (such as the join operator <link> and the Storm count command <link>), the nodes input to the operation are **not** retained - they are "consumed" during processing. Storm outputs only those nodes that result from carrying out the specified operation. If you lift a set of nodes and then filter the results, only those nodes captured by the filter are retained - the other nodes are discarded.

In this way the operations performed in sequence may add or remove nodes from Storm’s working set, or clear the set entirely. The set is continually changing based on the last-performed operation or last-issued command. Particularly when first learning Storm, users are encouraged to break down lengthy queries into their component parts, and to validate the output (results) after the addition of each operation to the overall query.
