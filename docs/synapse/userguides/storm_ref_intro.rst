.. highlight:: none

.. _storm-ref-intro:

Storm Reference - Introduction
==============================

**Storm** is the query language used to interact with data in Synapse. Storm allows you to ask about, retrieve, annotate, add, modify, and delete data from a Synapse Cortex. Most Synapse users will access Synapse via the Storm command-line interface (**Storm CLI**) (see :ref:`syn-tools-storm`):

``storm> <query>``

.. note::

  If you're just getting started with Synapse, you can use the Synapse Quickstart_ to quickly set up and connect to a local Cortex using the Storm CLI.

This section covers several important high-level Storm concepts:

- `Storm Background`_
- `Basic Storm Operations`_

  - `Lift, Filter, and Pivot Criteria`_

- `Whitespace and Literals in Storm`_
- `Storm Operating Concepts`_

  - `Operation Chaining`_
  - `Storm as a Pipeline`_
  - `Node Consumption`_
  
- `Advanced Storm Operations`_

.. _storm-bkgd:

Storm Background
----------------

In designing Storm, we needed it to be flexible and powerful enough to allow interaction with large amounts of data and a wide range of disparate data types. However, we also needed Storm to be intuitive and efficient so it would be accessible to a wide range of users. We wrote Storm specifically to be used by analysts and other users from a variety of knowledge domains who are not necessarily programmers and who would not want to use what felt like a "programming language".

Wherever possible, we masked Storm’s underlying programmatic complexity. The intent is for Storm to act more like a "data language", allowing users to:

- **Reference data and query operations in an intuitive form.** By using features such as property normalization, type enforcement / type awareness, and syntax and query optimization, Storm takes a "do what I mean" approach that makes it simple to use and understand. Once you get the gist of it, Storm "just works"!

- **Use a simple yet powerful syntax to run Storm queries.** To avoid feeling like a programming language (or even a traditional database query language), Storm avoids the use of operator-like functions and parameters. Instead, Storm uses:
  
  - Intuitive keyboard symbols (such as an "arrow" ( ``->`` ) for pivot operations) for efficient querying.
  - A natural language-like syntax so that using Storm feels more like "asking a question" than "constructing a data query".

Analysts still need to learn the Storm "language" - forms (:ref:`data-form`) and tags (:ref:`data-tag`) are Storm's "words", and Storm operators allows you to construct "sentences". That said, the intent is for Storm to function more like "how do I ask this question about the data?" and not "how do I write a program to get the data I need?"

Finally – and most importantly – **giving analysts direct access to Storm allows them to create arbitrary queries and provides them with an extraordinarily powerful analytical tool.** Analysts are not constrained to a set of "canned" queries provided through a GUI or an API. Instead, they can follow their analysis wherever it takes them, creating queries as needed and working with the data in whatever manner is most appropriate to their research.

.. _storm-ops-basic:

Basic Storm Operations
----------------------

Storm allows users to perform all of the common operations used to interact with the data in a Synapse Cortex:

- **Lift:** – retrieve data based on specified criteria. (:ref:`storm-ref-lift`)
- **Filter:** – refine your results by including or excluding a subset of nodes based on specified criteria. (:ref:`storm-ref-filter`)
- **Pivot:** – take a set of nodes and identify other nodes that share one or more property values with the lifted set. (:ref:`storm-ref-pivot`)
- **Data modification:** – add, modify, annotate, and delete nodes from a Synapse Cortex. (:ref:`storm-ref-data-mod`)

Additional operations include:

- **Traverse** light edges. (:ref:`light-edge`, :ref:`walk-light-edge`)
- **Pipe** (send) nodes to Storm commands (:ref:`storm-ref-cmd`). Storm supports an extensible set of commands such as :ref:`storm-limit`, :ref:`storm-max`, or :ref:`storm-uniq`. These commands provide specific functionality to further extend the analytical power of Storm. Additional Storm commands allow management of permissions for users and roles, Synapse views and layers, and Synapse's automation features (:ref:`storm-ref-automation`). Available commands can be displayed by running ``help`` from the Storm CLI.

Storm also incorporates a number of :ref:`storm-ops-adv` that provide even greater power and flexibility.

.. note::

  While Storm queries can range from the very simple to the highly complex, all Storm queries are constructed from this relatively small set of "building blocks". Most users, especially when they first start, only need the handful of blocks listed above!


Lift, Filter, and Pivot Criteria
++++++++++++++++++++++++++++++++

The main operations carried out with Storm are lifting, filtering, and pivoting (we include traversing light edges as part of "pivoting"). When conducting these operations, you need to be able to clearly specify the data you are interested in – your selection criteria. In most cases, the criteria you specify will be based on one or more of the following:

- A **property** (primary or secondary) on a node.
- A specific **value** for a property (*<form> = <valu>* or *<prop> = <pval>*) on a node.
- A **tag** on a node.
- The existence of a **light edge** linking nodes.
- The name ("verb") of a specific **light edge** linking nodes. 

All of the above elements – nodes, properties, values, and tags – are the fundamental building blocks of the Synapse data model (see :ref:`data-model-terms`). **As such, an understanding of the Synapse data model is essential to effective use of Storm.**

.. _storm-whitespace-literals:

Whitespace and Literals in Storm
--------------------------------

Storm allows (and in some cases requires) whitespace within Storm to delimit syntax elements such as commands and command arguments. Quotation marks are used to **preserve** whitespace characters and other special characters in literals used within Storm.

.. _storm-whitespace:

Using Whitespace Characters
+++++++++++++++++++++++++++

Whitespace characters (i.e., spaces) are used within the Storm CLI to delimit command line arguments. Specifically, whitespace characters are used to separate commands, command arguments, command operators, variables and literals.

When entering a query/command on the Storm CLI, one or more whitespace characters are **required** between the following command line arguments:

- A command (such as ``max``) and command line parameters (in this case, the property ``:asof``):
  
  ``storm> inet:whois:rec:fqdn=vertex.link | max :asof``
  
- An unquoted literal and any subsequent CLI argument or operator:
  
  ``storm> inet:email=support@vertex.link | count``
  
  ``storm> inet:email=support@vertex.link -> *``

Whitespace characters can **optionally** be used when performing the following CLI operations:

- Assigning values using the equals sign assignment operator:
  
  ``storm> [inet:ipv4=192.168.0.1]``
  
  ``storm> [inet:ipv4 = 192.168.0.1]``

- Comparison operations:
  
  ``storm> file:bytes:size>65536``
  
  ``storm> file:bytes:size > 65536``

- Pivot operations:
  
  ``storm> inet:ipv4->*``
  
  ``storm> inet:ipv4 -> *``
  
- Specifying the content of edit brackets or edit parentheses:

  ``storm> [inet:fqdn=vertex.link]``
  
  ``storm> [ inet:fqdn=vertex.link ]``
  
  ``storm> [ inet:fqdn=vertx.link (inet:ipv4=1.2.3.4 :asn=5678) ]``
  
  ``storm> [ inet:fqdn=vertex.link ( inet:ipv4=1.2.3.4 :asn=5678 ) ]``

Whitespace characters **cannot** be used between reserved characters when performing the following CLI operations:

- Add and remove tag operations. The plus ( ``+`` ) and minus  ( ``-`` ) sign characters are used to add and remove tags to and from nodes in Synapse respectively. When performing tag operations using these characters, a whitespace character cannot be used between the actual character and the tag name (e.g., ``+#<tag>``).
  
  ``storm> inet:ipv4 = 192.168.0.1 [ -#oldtag +#newtag ]``

.. _storm-literals:

Entering Literals
+++++++++++++++++

Storm uses quotation marks (single and double) to preserve whitespace and other special characters that represent literals. If values with these characters are not quoted, Synapse may misinterpret them and throw a syntax error.

Single ( ``' '`` ) or double ( ``" "`` ) quotation marks can be used when entering a literal on the CLI during an assignment or comparison operation. Enclosing a literal in quotation marks is **required** when the literal:

 - begins with a non-alphanumeric character,
 - contains a space ( ``\s`` ), tab ( ``\t`` ) or newline( ``\n`` ) character, or
 - contains a reserved Synapse character (for example, ``\ ) , = ] } |``).

Enclosing a literal in **single** quotation marks will preserve the literal meaning of **each character.** That is, each character in the literal is interpreted exactly as entered.

 - Note that if a literal (such as a string) **includes** a single quotation mark / tick mark, it must be enclosed in double quotes.
 
  - Wrong: ``'Storm's intuitive syntax makes it easy to learn and use.'``
  - Right: ``"Storm's intuitive syntax makes it easy to learn and use."``

Enclosing a literal in **double** quotation marks will preserve the literal meaning of all characters **except for** the backslash ( ``\`` ) character, which is interpreted as an 'escape' character. The backslash can be used to include special characters such as tab (``\t``) or newline (``\n``) within a literal.

 - If you need to include a literal backslash within a double-quoted literal, you must enter it as a "double backslash" (the first backslash "escapes" the following backslash character):
 
   - Wrong: ``"C:\Program Files\Mozilla Firefox\firefox.exe"``
   - Right: ``"C:\\Program Files\\Mozilla Firefox\\firefox.exe"``
   
 Note that because the above example does not include a single quote / tick mark as part of the literal, you can simply enclose the file path in  single quote:
 
   - Also right: ``'C:\Program Files\Mozilla Firefox\firefox.exe'``

The Storm queries below demonstrate assignment and comparison operations that **do not require** quotation marks:

- Lifting the domain ``vtx.lk``:
  
  ``storm> inet:fqdn = vtx.lk``

- Lifting the file name ``windowsupdate.exe``:
  
  ``storm> file:base = windowsupdate.exe``

The commands below demonstrate assignment and comparison operations that **require** the use of quotation marks. Failing to enclose the literals below in quotation marks will result in a syntax error.

- Lift the file name ``windows update.exe`` which contains a whitespace character:
  
  ``storm> file:base = 'windows update.exe'``

- Lift the file name ``windows,update.exe`` which contains the comma special character:
  
  ``storm> file:base = "windows,update.exe"``

.. _storm-op-concepts:

Storm Operating Concepts
------------------------

Storm has several notable features in the way it interacts with and operates on data. Understanding these features is important to using Storm in general, and essential to using more advanced Storm operations effectively.

.. _storm-op-chain:

Operation Chaining
++++++++++++++++++

As noted above, users commonly interact with data (nodes) in Synapse using operations such as lift, filter, and pivot. Storm allows multiple operations to be chained together to form increasingly complex queries. When Storm operations are concatenated in this manner, they are processed **in order from left to right** with each operation (lift, filter, or pivot) acting on the output of the previous operation.

..  NOTE::

  The initial set of nodes in any Storm query (i.e., the set of nodes selected by your first lift operation) is known as your **initial working set**.
  
Note that most operations (other than those used solely to lift or add data) require an existing data set on which to operate. This data set is typically the output of a previous Storm operation - the previous operation in the chain - whose results are the nodes you want to modify or otherwise work with.

.. NOTE::

  The output of any Storm operation (other than your initial lift) is known as your **current working set**. Depending on the operation(s) performed, your current working set may not be the same as your initial working set (see :ref:`storm-node-consume` below). Your working set emerges from one Storm operation and is considered **inbound** to the next operation in the chain.

From an analysis standpoint, this means that Storm syntax can parallel an analyst's natural thought process, as you perform one Storm operation and then consider the "next step" you want to take in your analysis: "show me X data...that’s interesting, take a subset of X data and show me the Y data that relates to X...hm, now take the results from Y and show me any relationship to Z data..." and so on. Each "now show me..." thought commonly corresponds to a new Storm operation that can be added to your existing Storm query to navigate through the data.

From a practical standpoint, it means that **order matters** when constructing a Storm query. A lengthy Storm query is not evaluated as a whole. Instead, Synapse parses each component of the query in order, evaluating each component individually and potentially returning a new **working set** after each operation before executing the next operation.

(Technically, any query you construct is first evaluated as a whole **to ensure it is a syntactically valid query** - Synapse will complain if your Storm syntax is incorrect. But once Synapse has checked your Storm syntax, nodes are processed by each Storm operation in order.)

.. _storm-pipeline:

Storm as a Pipeline
+++++++++++++++++++

Most objects in a Synapse Cortex are nodes (:ref:`data-node`), so most Storm operations act on nodes. Not only are chained Storm operations carried out from left to right, but **nodes pass individually through the chain.** The series of Storm operations (i.e., the overall Storm query) can be thought of as a "pipeline". Regardless of how simple or complex the Storm query is, and regardless of whether your initial working set consists of one node or 100,000 nodes, each node is "fired" through the query pipeline one at a time.

A key advantage of this behavior is that it provides significant latency and memory use reduction to Storm. Because nodes are operated on one at a time, Storm can start returning results immediately even if the initial data set is quite large.

Outside of this latency reduction, Storm’s "pipeline" behavior is generally transparent to a user — from the user’s standpoint, they write a query to operate on data, and data comes back as a result of that query. However, this pipeline behavior can be important to understand when working with (or troubleshooting) Storm queries that leverage features such as subqueries, variables, or control flow operations.

.. _storm-node-consume:

Node Consumption
++++++++++++++++

Most Storm operations **consume** nodes when the operation occurs. That is, the set of nodes (the working set) that is **inbound** to a particular Storm operation is typically transformed by that operation in some way. In fact, with few exceptions (such as the join operator (see :ref:`storm-ref-pivot`) and the Storm :ref:`storm-count` command), the nodes inbound to an operation are typically **not** retained - they are "consumed" during execution. Storm outputs only those nodes that result from carrying out the specified operation. If you lift a set of nodes and then filter the results, only those nodes captured by the filter are retained - the other nodes are consumed (discarded).

In this way the operations performed in sequence may add or remove nodes from Storm's **working set,** or clear the set entirely. The set is continually changing based on the last-performed operation or last-issued command. Particularly when first learning Storm, users are encouraged to break down lengthy queries into their component parts, and to validate the output (results) after the addition of each operation to the overall query.

.. _storm-ops-adv:

Advanced Storm Operations
-------------------------

In our experience, the more analysts use Storm, the more they want even greater power and flexibility from the language to support their analytical workflow! To meet these demands, Storm evolved a number of advanced features, including:

- Subqueries (:ref:`storm-ref-subquery`)
- Variables (:ref:`storm-adv-vars`)
- Methods (:ref:`storm-adv-methods`)
- Libraries (:ref:`storm-adv-libs`)
- Control Flow (:ref:`storm-adv-control`)

**Analysts do not need to use or understand these more advanced concepts in order to use Storm or Synapse.** Basic Storm functions are sufficient for a wide range of analytical needs and workflows. However, these additional features are available to both "power users" and developers as needed:

- For analysts, once they are comfortable with Storm basics, many of them want to expand their Storm skills **specifically because it facilitates their analysis.**
- For developers, writing extensions to Synapse in Storm has the advantage that the extension **can be deployed or updated on the fly.** Contrast this with extensions written in Python, for example, which would require restarting the system during a maintenance window in order to deploy or update the code.

.. note::

  Synapse's **Power-Ups**, which provide extended services and connections to third-party data sources, are all written in Storm and exposed to Synapse users as Storm commands!


.. _Quickstart: https://github.com/vertexproject/synapse-quickstart
