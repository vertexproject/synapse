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


.. _storm.py: ../../../synapse/lib/storm.py
__ storm.py_

.. _conventions: ../userguides/ug011_storm_basics.rst#syntax-conventions
__ conventions_

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
