.. highlight:: none

.. _storm-ref-intro:

Storm Reference - Introduction
==============================

**Storm** is the query language used to interact with data in Synapse. Storm allows you to ask about,
retrieve, annotate, add, modify, and delete data within a Synapse Cortex. If you are using the `open source`_
or `Quickstart`_ versions of Synapse, you will access Synapse via the Storm command-line interface (**Storm CLI**)
(see :ref:`syn-tools-storm`):

::
  
  storm> <query>

If you are a Synapse Enterprise customer or have requested a Synapse Enterprise `demo instance`_ you will
access Synapse via the Synapse UI (also known as `Optic`_) and use Storm from the Storm query bar.
  
.. TIP::
  
  If you're not sure which version of Synapse to start with, check out our `Getting Started guide`_.
  

.. _storm-bkgd:

Storm Background
----------------

In designing Storm, we needed it to be flexible and powerful enough to allow interaction with large amounts
of data and a wide range of disparate data types. However, we also needed Storm to be intuitive and efficient
so it would be accessible to a wide range of users. We wrote Storm specifically to be used by analysts and
other users from a variety of knowledge domains who are not necessarily programmers and who would not want to
use what felt like a "programming language".

Wherever possible, we masked Storm’s underlying programmatic complexity. The intent is for Storm to act more
like a "data language", allowing users to:

- **Reference data and query operations in an intuitive form.** We took a "do what I mean" approach for how
  users interact with and use Storm so that users can focus on the **data** and the relationships among the
  data, not the query language. Once you get the gist of it, Storm "just works"! This is because Storm and
  Synapse make use of a number of features "under the hood" such as property normalization, type enforcement / 
  type awareness, and syntax and query optimization, to make Storm easier for you to use. Synapse and Storm
  do the work in the background so you can focus on analysis.

- **Use a simple yet powerful syntax to run Storm queries.** Storm uses intuitive keyboard symbols (such as
  an "arrow" ( ``->`` ) for pivot operations) for efficient querying, as well as a natural language-like syntax.
  This makes using Storm feel more like "asking a question" than "constructing a data query". In fact, one
  method we use to teach Storm to new users is to practice "translating" questions into queries (you'll be
  surprised how straightforward it is!).

Analysts still need to learn the Storm "language" - forms (:ref:`data-form`) and tags (:ref:`data-tag`) are
Storm's "words", and Storm operators allows you to construct "sentences". That said, the intent is for Storm
to function more like "how do I ask this question about the data?" and not "how do I write a program to get
the data I need?"

Finally – and most importantly – 
**giving analysts direct access to Storm allows them to create arbitrary queries and provides them with an extraordinarily powerful analytical tool.**
Analysts are not constrained to a set of "canned" queries provided through a GUI or an API. Instead, they can
follow their analysis wherever it takes them, creating queries as needed and working with the data in whatever
manner is most appropriate to their research.

.. _storm-ops-basic:

Basic Storm Operations
----------------------

Storm allows users to perform all of the common operations used to interact with data in Synapse:

- `Lift`_: retrieve data based on specified criteria.
- `Filter`_: refine your results by including or excluding a subset of nodes based on specified criteria.
- `Pivot`_: take a set of nodes and identify other nodes that share one or more property values with the
  lifted set.
- `Traverse`_ light edges.
- `Modify data`_: create, modify, annotate (tag), and delete nodes from Synapse.
- `Run commands`_: Storm supports an extensible set of commands. Many commands provide specific
  functionality to extend the analytical power of Storm. Other Storm commands allow management of permissions
  for users and roles, Synapse views and layers, and Synapse's `automation`_ features. You can display available
  commands by running ``help`` from the Storm CLI.

Many Storm queries - even "complex" ones - can be constructed from this simple set of "building blocks". For
users who want to expand their Storm capabilities, there are additional :ref:`storm-ops-adv` that provide even
greater power and flexibility.


Lift, Filter, and Pivot Criteria
++++++++++++++++++++++++++++++++

The main operations carried out with Storm are lifting, filtering, and pivoting (we include traversing light
edges as part of "pivoting"). When conducting these operations, you need to be able to clearly specify the data
you are interested in – your selection criteria. In most cases, the criteria you specify will be based on one
or more of the following:

- A **property** (primary or secondary) on a node.
- A specific **value** for a property (*<form> = <valu>* or *<prop> = <pval>*) on a node.
- A **tag** on a node.
- The existence of a **light edge** linking nodes.
- The name ("verb") of a specific **light edge** linking nodes. 

All of the above elements – nodes, properties, values, and tags – are the fundamental building blocks of the
Synapse data model (see :ref:`data-model-terms`). **As such, an understanding of the Synapse data model is essential to effective use of Storm.**

.. _storm-whitespace-literals:

Whitespace and Literals in Storm
--------------------------------

The Storm query language allows (and in some cases requires) whitespace in order to separate syntax elements
such as commands and command arguments.

When using **literals** in Storm, quotation marks are used to **preserve** whitespace characters and other
special characters within the literal.

.. _storm-whitespace:

Using Whitespace Characters
+++++++++++++++++++++++++++

Whitespace characters (i.e., spaces) are used within Storm to separate command line arguments. Specifically,
whitespace characters are used to separate commands, command arguments, command operators, variables and literals.

When entering a query/command in Storm, one or more whitespace characters are **required** between the following
command line arguments:

- A command (such as ``max``) and command line parameters (in this case, the property ``:asof``):

::
  
  storm> inet:whois:rec:fqdn=vertex.link | max :asof
  
- An unquoted literal and any subsequent argument or operator:

::
  
  storm> inet:email=support@vertex.link | count
  
  storm> inet:email=support@vertex.link -> *

Whitespace characters can **optionally** be used when performing the following operations:

- Assigning values using the equals sign assignment operator:

::
  
  storm> [inet:ip=192.168.0.1]
  
  storm> [inet:ip = 192.168.0.1]

- Comparison operations:

::
  
  storm> file:bytes:size>65536
  
  storm> file:bytes:size > 65536

- Pivot operations:

::
  
  storm> inet:ip->*
  
  storm> inet:ip -> *
  
- Specifying the content of edit brackets or edit parentheses:

::

  storm> [inet:fqdn=vertex.link]
  
  storm> [ inet:fqdn=vertex.link ]
  
  storm> [ inet:fqdn=vertx.link (inet:ip=1.2.3.4 :asn=5678) ]
  
  storm> [ inet:fqdn=vertex.link ( inet:ip=1.2.3.4 :asn=5678 ) ]

Whitespace characters **cannot** be used between reserved characters when performing the following CLI operations:

- Add and remove tag operations. The plus ( ``+`` ) and minus  ( ``-`` ) sign characters are used to add and
  remove tags to and from nodes in Synapse respectively. When performing tag operations using these characters,
  a whitespace character cannot be used between the actual character and the tag name (e.g., ``+#<tag>``).

::

  storm> inet:ip = 192.168.0.1 [ -#oldtag +#newtag ]

.. _storm-literals:

Entering Literals
+++++++++++++++++

Storm uses quotation marks (single and double) to preserve whitespace and other special characters that represent
literals. If values with these characters are not quoted, Synapse may misinterpret them and throw a syntax error.

Single ( ``' '`` ) or double ( ``" "`` ) quotation marks can be used when specifying a literal in Storm during an
assignment or comparison operation. Enclosing a literal in quotation marks is **required** when the literal:

 - begins with a non-alphanumeric character,
 - contains a space ( ``\s`` ), tab ( ``\t`` ) or newline( ``\n`` ) character, or
 - contains a reserved Synapse character (for example, ``\ ) , = ] } |``).

Enclosing a literal in **single** quotation marks will preserve the literal meaning of **each character.** That
is, each character in the literal is interpreted exactly as entered.

 - Note that if a literal (such as a string) **includes** a single quotation mark / tick mark, it must be enclosed
   in double quotes.
 
  - Wrong: ``'Storm's intuitive syntax makes it easy to learn and use.'``
  - Right: ``"Storm's intuitive syntax makes it easy to learn and use."``

Enclosing a literal in **double** quotation marks will preserve the literal meaning of all characters **except for**
the backslash ( ``\`` ) character, which is interpreted as an 'escape' character. The backslash can be used to include
special characters such as tab (``\t``) or newline (``\n``) within a literal.

 - If you need to include a literal backslash within a double-quoted literal, you must enter it as a "double 
   backslash" (the first backslash "escapes" the following backslash character):

   - Wrong: ``"C:\Program Files\Mozilla Firefox\firefox.exe"``
   - Right: ``"C:\\Program Files\\Mozilla Firefox\\firefox.exe"``
   
 Note that because the above example does not include a single quote / tick mark as part of the literal, you can
 simply enclose the file path in single quotes:
 
   - Also right: ``'C:\Program Files\Mozilla Firefox\firefox.exe'``

The Storm queries below demonstrate assignment and comparison operations that **do not require** quotation marks:

- Lifting the domain ``vtx.lk``:

::
  
  storm> inet:fqdn = vtx.lk

- Lifting the file name ``windowsupdate.exe``:

::
  
  storm> file:base = windowsupdate.exe

The commands below demonstrate assignment and comparison operations that **require** the use of quotation marks.
Failing to enclose the literals below in quotation marks will result in a syntax error.

- Lift the file name ``windows update.exe`` which contains a whitespace character:

::
  
  storm> file:base = 'windows update.exe'

- Lift the organization name ``The Vertex Project, LLC`` which contains both whitespace and the comma special character:

::
  
  storm> ou:name = 'The Vertex Project, LLC'

.. _storm-backtick-format-strings:

Backtick Format Strings
+++++++++++++++++++++++

Backticks ( ``` ``` ) can be used to specify a format string in Storm, with curly braces used to specify
expressions which will be substituted into the string at runtime. Any valid Storm expression may be used in
a format string, such as variables, node properties, tags, or function calls.

- Use a variable in a string:

::

  storm> $ip = "1.2.3.4" $str = `The IP is {$ip}`

- Use node properties in a string:

::

  storm> inet:ip=1.2.3.4 $lib.print(`IP {$node.repr()}: asn={:asn} .seen={.seen} foo={#foo}`)

- Lift a node using a format string:

::

  storm> $ip=1.2.3.4 $port=22 inet:client=`{$ip}:{$port}`

Backtick format strings may also span multiple lines, which will include the newlines when displayed:

::

    storm> inet:ip=1.2.3.4 $lib.print(`
    IP {$node.repr()}:
    asn={:asn}
    .seen={.seen}
    foo={#foo}`)

Like double quotes, backticks will preserve the literal meaning of all characters
**except for** the backslash ( ``\`` ) character, which is interpreted as an 'escape'
character. The backslash can be used to include special characters such as tab (``\t``)
or newline (``\n``), or to include a backtick (`````) or curly brace (``{``) in the string.

.. _storm-op-concepts:

Storm Operating Concepts
------------------------

Storm has several notable features in the way it interacts with and operates on data. These concepts are
important but also pretty intuitive; it's good to be familiar with them, but most users don't need to worry
about them too much for standard Storm queries and operations (day-to-day interaction with Synapse data).

These concepts are much more important if you're using more `advanced Storm`_ constructs such as variables,
control flow, or functions. If you're writing advanced Storm queries, automation, or custom Power-Ups, you should be
comfortable with these terms and behaviors.

.. _storm-op-work-set:

Working Set
+++++++++++

Most objects in Synapse are **nodes**. Most Storm operations start by **lifting** (selecting) a node or set of
nodes from Synapse's data store.

 - The set of nodes that you start with is called your **initial working set**.
 - The set of nodes at any given point in your Storm query is called your **current working set**.

.. _storm-op-chain:

Operation Chaining
++++++++++++++++++

Users commonly interact with data (nodes) in Synapse using operations such as lift, filter, and pivot. Storm allows
multiple operations to be **chained** together to form increasingly complex queries:

::
  
  storm> inet:fqdn=vertex.link
  
  storm> inet:fqdn=vertex.link -> inet:dns:a
  
  storm> inet:fqdn=vertex.link -> inet:dns:a -> inet:ip
  
  storm> inet:fqdn=vertex.link -> inet:dns:a -> inet:ip +:type=unicast

The above example demonstrates chaining a lift (``inet:fqdn=vetex.link``) with two pivots
(``-> inet:dns:a``, ``-> inet:ip``) and a filter (``+:type=unicast``).

When Storm operations are concatenated in this manner, they are processed **in order from left to right** with each
operation (lift, filter, or pivot) acting on the output of the previous operation. A Storm query is not evaluated
as a single whole; Storm evaluates your working set of nodes against each operation in order before moving to the
next operation.

.. NOTE::
  
  Technically, any query you construct is first evaluated as a whole **to ensure it is a syntactically valid query** -
  Synapse will complain if your Storm syntax is incorrect. But once Synapse has checked your Storm syntax, nodes are
  processed by each Storm operation in order.

You do not have to write (or execute) Storm queries "one operation at a time" - this example is meant to illustrate
how you can chain individual Storm operations together to form longer queries. If you know that the question
you want Storm to answer is "show me the unicast IP addresses that the FQDN vertex.link has resolved to", you can
simply run the final query in its entirety. But you can also "build" queries one operation at a time if you're
exploring the data or aren't sure yet where your analysis will take you.

The ability to build queries operation by operation means that a Storm query can parallel an analyst's natural
thought process: you perform one Storm operation and then consider the "next step" you want to take in your analysis!

.. _storm-node-consume:

Node Consumption
++++++++++++++++

Storm operations typically **transform** your working set in some way. That is, the nodes that "go into" (are inbound)
to a given Storm operation are not necessarily the nodes that "come out" of that operation.

Take our operation chaining example above:

 - Our **initial working set** consists of the single node ``inet:fqdn=vertex.link``, which we selected with a lift
   operation.
 - When we pivot to the DNS A records for that FQDN, we navigate away from (drop) our initial ``inet:fqdn`` node, and
   navigate to (add) the DNS A nodes. Our **current working set** now consists of the DNS A records (``inet:dns:a`` nodes)
   for vertex.link.
 - Similarly, when we pivot to the IP addresses, we navigate away from (drop) the DNS A nodes and navigate to (add)
   the IP nodes. Our current working set is made up of the ``inet:ip`` nodes.
 - Finally, when we perform our filter operation, we may discard (drop) any IP nodes representing non-unicast IPs
   (such as ``inet:ip=127.0.0.1``) if present.
 
We refer to this transformation (in particular, dropping) of some or all nodes by a given Storm operation as **consuming**
nodes. Most Storm operations consume nodes (that is, change your working set in some way - what comes out of the operation
is not the same set of nodes that goes in).
 
For standard Storm queries this process should be fairly intuitive ("now that you point that out...of course that
is what's happening"). However, the idea of **node consumption** and the transformation of your current working set
is important to keep in mind for more advanced Storm.

.. TIP::
  
  Storm commands (built-in commands, or commands added by Power-Ups) that operate on nodes generally do **not**
  consume nodes - the nodes that "go into" the command are the same nodes that "come out" by default. This allows
  you to chain multiple commands together that all operate on the same inbound nodes. Commands may include a
  ``--yield`` option to modify this behavior and drop (consume) the inbound nodes and return the node(s) (or
  primary node(s)) produced by the command.


.. _storm-pipeline:

Storm as a Pipeline
+++++++++++++++++++

Just as each Storm **operation** in the chain is processed individually from left to right, **each node** in your
working set is evaluated **individually** against a given Storm operation in a query. You can think of your Storm
query as a **pipeline** of operations, with each node "fired" one at a time through the pipeline. Whether you start
with one node or 10,000 nodes, they are evaluated against your Storm query one by one.

Processing nodes one by one significantly reduces Synapse's latency and memory use: this is a big part of what
makes Synapse so fast and responsive. Synapse can immediately provide you with results for the initial nodes while
it continues processing the remaining nodes. In other words, you don't have to wait for your **entire** query to
complete before starting to see results.

For everyday Storm, this behavior is transparent - you run a Storm query, you get a response. However, understanding
this pipeline behavior is critical when working with (or troubleshooting) Storm queries that leverage features such
as subqueries, variables, control flow operations, or functions.

.. _storm-ops-adv:

Advanced Storm Operations
-------------------------

In our experience, the more analysts use Storm, the more they want even greater power and flexibility from the
language to support their analytical workflow! To meet these demands, Storm evolved a number of advanced features,
including:

- `Variables`_
- `Methods`_
- `Control Flow`_
- `Functions`_
- :ref:`stormtypes-libs-header`
- :ref:`stormtypes-prim-header`

**Analysts do not need to use or understand these more advanced concepts in order to use Storm or Synapse.**
Basic Storm functions are sufficient for a wide range of analytical needs and workflows. However, these additional
features are available to both "power users" and developers as needed:

- For analysts, once they are comfortable with Storm basics, many of them want to expand their Storm skills
  **specifically because it facilitates their analysis.**
- For developers, writing extensions to Synapse in Storm has the advantage that the extension
  **can be deployed or updated on the fly.** Contrast this with extensions written in Python, for example, which
  would require restarting the system during a maintenance window in order to deploy or update the code.

.. NOTE::

  Synapse's `Rapid Power-Ups`_ are written entirely in Storm and exposed to Synapse users as Storm commands!


.. _open source: https://github.com/vertexproject/synapse
.. _Quickstart: https://github.com/vertexproject/synapse-quickstart
.. _demo instance: https://vertex.link/request-a-demo
.. _Optic: https://synapse.docs.vertex.link/projects/optic/en/latest/index.html
.. _Getting Started guide: https://synapse.docs.vertex.link/en/latest/synapse/quickstart.html

.. _Lift: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_lift.html
.. _Filter: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_filter.html
.. _Pivot: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_pivot.html
.. _Traverse: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_pivot.html#traverse-walk-light-edges
.. _`Modify data`: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_data_mod.html
.. _`Run commands`: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_cmd.html
.. _automation: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_automation.html

.. _advanced Storm: https://synapse.docs.vertex.link/en/latest/synapse/userguides/index_storm_adv.html

.. _Variables: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_adv_vars.html
.. _Methods: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_adv_methods.html
.. _Control Flow: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_adv_control.html
.. _Functions: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_adv_functions.html

.. _`Rapid Power-Ups`: https://synapse.docs.vertex.link/en/latest/synapse/power_ups.html#rapid-power-ups
