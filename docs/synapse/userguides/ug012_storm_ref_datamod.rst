Storm Reference - Data Modification Operators
=============================================

The operators below can be used to modify the Synapse hypergraph by:

* adding or deleting nodes
* adding cross-reference (xref) nodes
* setting or modifying properties on nodes
* adding or deleting tags from nodes

(**Note:** currently there is no operator for deleting properties from nodes (e.g., ``delprop()``). This is planned for a future release.)

All of these operators are defined in `storm.py`__.

**IMPORTANT:** Synapse does not have an "are you sure?" prompt. Caution should be used with operators that can modify Synapse data, especially when used on the output of complex queries that may modify (or delete) large numbers of nodes. It is **strongly recommended** that you validate the output of a query (does the query return the expected results?) by first running the query on its own before applying any operator that will modify that data.

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Where specific query examples are given, they are commonly provided in pairs using operator syntax followed by the equivalent macro syntax (if available).

addnode()
---------
Adds the specified node(s) to a Cortex.

**Operator Syntax:**

.. parsed-literal::
  
  **addnode(** *<form>* **,** *<valu>* **,** [ **:** *<prop>* **=** *<pval>* **,** ...] **)**
  
  **addnode(** *<form>* **, (** *<valu_1>* **,** *<valu_2>* **,** ... **) ,** [ **:** *<prop>* **=** *<pval>* **,** ...] **)**

**Macro Syntax:**

.. parsed-literal::
  
  **[** *<form>* **=** *<valu>* ... [ **:** *<prop>* **=** *<pval>* ...] **]**
  
  **[** *<form>* **= (** *<valu_1>* **,** *<valu_2>* **,** ... **)** [ **:** *<prop>* **=** *<pval>* ...] **]**

**Examples:**

*Simple Node:*

``addnode( inet:fqdn , woot.com )``

``[ inet:fqdn = woot.com ]``

*Separator (sepr) Node:*

``addnode( inet:dns:a , ( woot.com , 1.2.3.4 ) )``

``[ inet:dns:a = ( woot.com , 1.2.3.4 ) ]``

*Composite (comp) Node:*

``addnode( inet:follows , (twitter.com/ernie , twitter.com/bert ) )``

``[ inet:follows = ( twitter.com/ernie , twitter.com/bert ) ]``

*Comp Node with Optional Values:*

Todo

*Cross-reference (xref) Node:*

``addnode( file:txtref , ( d41d8cd98f00b204e9800998ecf8427e , inet:fqdn , woot.com ) )``

``[ file:txtref = ( d41d8cd98f00b204e9800998ecf8427e , inet:fqdn , woot.com ) ]``

*Node with Properties:*

``addnode( inet:dns:a , ( woot.com , 1.2.3.4 ) , :seen:min = "2017-08-01 01:23" , :seen:max = "2017-08-10 04:56" )``

``[ inet:dns:a = ( woot.com , 1.2.3.4 ) :seen:min = "2017-08-01 01:23" :seen:max = "2017-08-10 04:56" ]``

**Usage Notes:**

* ``addnode()`` used at the Synapse CLI is most suitable for adding a relatively small number of nodes. For larger amounts of data, it is preferable to use the Synapse `ingest`__ subsystem to automate the process.
* When creating a <form> whose <valu> consists of multiple components, the components must be passed as a comma-separated list enclosed in parentheses.
* ``addnode()`` will create non-deconflictable node types.
* ``addnode()`` will check whether a deconflictable node type already exists and either create it or return information on the existing node.
* Secondary properties must be specified by their relative property name (``:baz`` instead of ``foo:bar:baz``).
* Specifying one or more secondary properties will set the ``<prop>=<pval>`` if it does not exist, or modify (overwrite) the ``<prop>=<pval>`` if it already exists.

**Operator Syntax Notes:**

* The operator syntax can only create only one node at a time.

**Macro Syntax Notes:**

* The macro syntax can create as many nodes as are specified within the brackets.
* All nodes specified within the brackets that do not already exist will be created. For nodes that already exist, Synapse will return data for that node.


.. _storm.py: ../../../synapse/lib/storm.py
__ storm.py_

.. _conventions: ../userguides/ug011_storm_basics.rst#syntax-conventions
__ conventions_

.. _ingest: ../userguides/ug050_ing_intro.rst
__ ingest_
