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


addxref()
---------

Create one or more cross-reference (`xref`__) nodes that reference a specified ``<form>=<valu>``.

**Operator Syntax:**

.. parsed-literal::
  *<query>* **addxref(** *<type>* **,** *<form>* **,** *<valu>* **)**

**Macro Syntax:**

None.

**Examples:**

``file:bytes = d41d8cd98f00b204e9800998ecf8427e addxref( file:txtref , inet:fqdn , woot.com )``

**Usage Notes:**

* ``addxref()`` operates on the output of a previous Storm query.
* There are currently two valid ``<type>`` values, ``file:txtref`` and ``file:imgof``. For both of those types, the Storm query should return one or more ``file:bytes`` nodes.
* Xref nodes can also be created with ``addnode()`` using the syntax for creating a comp node type (e.g., ``addnode( file:txtref , ( <file_guid> , <form> , <valu> ) )``). Note that ``addnode()`` can only create one xref node at a time (e.g., from a single ``file:bytes`` node to a single ``<form>=<valu>``).
* ``addxref()`` may be useful if you want to create multiple xref nodes from multiple ``file:bytes`` nodes to the same ``<form>=<valu>`` at once (e.g., if you have eight photographs of the same object).


setprop()
---------

Sets one or more property values on the specified node(s).

**Operator Syntax:**

.. parsed-literal::
  *<query>* **setprop( :** *<prop>* **=** *<pval>* **,** ... **)**

**Macro Syntax:**

.. parsed-literal::
  *<query>* **[ :** *<prop>* **=** *<pval>* ... **]**

**Examples:**

``inet:dns:a = woot.com/1.2.3.4 setprop( :seen:min = "2017-08-01 01:23" , :seen:max = "2017-08-10 04:56" )``

``inet:dns:a = woot.com/1.2.3.4 [ :seen:min = "2017-08-01 01:23" :seen:max = "2017-08-10 04:56" ]``

**Usage Notes:**

* ``setprop()`` operates on the output of a previous Storm query.
* Secondary properties must be specified by their relative property name. For the form ``foo:bar`` and the property ``baz`` (e.g., ``foo:bar:baz``) the relative property name is specified as ``:baz``.
* Synapse will set the secondary propert(ies) for all nodes returned by `<query>` for which that secondary property is a valid property. Nodes for which that property is not a valid secondary property will be ignored.
* ``setprop()`` will create and set the property if it does not exist, or overwrite the existing ``<prop>=<pval>`` if it does exist.
* ``setprop()`` can set or modify any property not explicitly defined as read only (``'ro' : 1``) in the data model. Attempts to modify read only properties will fail silently (e.g., the property value will not be overwritten, but the user will not be notified that the request failed).
* ``setprop()`` cannot be used to remove (delete) a property entirely.

**Operator Syntax Notes:**

* N/A

**Macro Syntax Notes:**

* Synapse will attempt to set the specified propert(ies) for all previously referenced nodes (e.g., to the left of the ``<prop>=<pval>`` statement) for which that property is valid, **whether those nodes are within or outside of the macro syntax brackets.**

addtag()
--------

Adds one or more tags to the specified node(s).

**Operator Syntax:**

.. parsed-literal::
  *<query>* **addtag(** *<tag>* [ **,** ... ] **)**

**Macro Syntax:**

.. parsed-literal::
  *<query>* **[** **#** *<tag>* ... **]**

**Examples:**

``inet:fqdn = woot.com addtag( foo.bar , baz.faz )``

``inet:fqdn = woot.com [ #foo.bar #baz.faz ]``

**Usage Notes:**

* ``addtag()`` operates on the output of a previous Storm query.
* Synapse will apply the specified tag(s) to all nodes returned by ``<query>``.

**Operator Syntax Notes:**

* N/A

**Macro Syntax Notes:**

* Synapse will set the specified tag(s) for all previously referenced nodes (e.g., to the left of the ``<tag>`` statement) **whether those nodes are within or outside of the macro syntax brackets.**














.. _storm.py: ../../../synapse/lib/storm.py
__ storm.py_

.. _conventions: ../userguides/ug011_storm_basics.rst#syntax-conventions
__ conventions_

.. _ingest: ../userguides/ug050_ing_intro.rst
__ ingest_


.. _xref: ../userguides/ug007_dm_nodetypes.rst#cross-reference-xref-nodes
__ xref_
