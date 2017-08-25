Storm Reference - Data Modification Operators
=============================================

The operators below can be used to modify the Synapse hypergraph by:

* adding or deleting nodes
* adding cross-reference (xref) nodes
* setting or modifying properties on nodes
* adding or deleting tags from nodes

(**Note:** currently there is no operator for deleting properties from nodes (e.g., ``delprop()``). This is planned for a future release.)

All of these operators are defined in storm.py_.

.. WARNING::
  Synapse does not have an "are you sure?" prompt. Caution should be used with operators that can modify Synapse data, especially when used on the output of complex queries that may modify (or delete) large numbers of nodes. It is **strongly recommended** that you validate the output of a query by first running the query on its own to ensure it returns the expected results before applying any operator that will modify that data.

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
* When creating a ``<form>`` whose ``<valu>`` consists of multiple components, the components must be passed as a comma-separated list enclosed in parentheses.
* ``addnode()`` will create non-deconflictable node types.
* ``addnode()`` will check whether a deconflictable node type already exists and either create it or return information on the existing node.
* Secondary properties must be specified by their relative property name. For the form ``foo:bar`` and the property ``baz`` (e.g., ``foo:bar:baz``) the relative property name is specified as ``:baz``.
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
* Synapse will set the secondary propert(ies) for all nodes returned by ``<query>`` for which that secondary property is a valid property. Nodes for which that property is not a valid secondary property will be ignored.
* ``setprop()`` will create and set the property if it does not exist, or overwrite the existing ``<prop>=<pval>`` if it does exist.
* ``setprop()`` can set or modify any property not explicitly defined as read only (``'ro' : 1``) in the data model. Attempts to modify read only properties will fail silently (e.g., the property value will not be overwritten, but the user will not be notified that the request failed).
* ``setprop()`` cannot be used to remove (delete) a property entirely.

**Operator Syntax Notes:**

* N/A

**Macro Syntax Notes:**

* Synapse will attempt to set the specified propert(ies) for all previously referenced nodes (e.g., to the left of the ``<prop>=<pval>`` statement) for which that property is valid, **whether those nodes are within or outside of the macro syntax brackets.** See `Special Note on Macro Syntax`_.

addtag()
--------

Adds one or more tags to the specified node(s).

**Operator Syntax:**

.. parsed-literal::
  *<query>* **addtag(** *<tag>* [ **@** *<yyyymmddhhmmss>-<yyyymmddhhmmss>* **,** ... ] **)**

**Macro Syntax:**

.. parsed-literal::
  *<query>* **[ #** *<tag>* **@** *<yyyymmddhhmmss>-<yyyymmddhhmmss>* ... **]**

**Examples:**

*Add Tags*

``inet:fqdn = woot.com addtag( foo.bar , baz.faz )``

``inet:fqdn = woot.com [ #foo.bar #baz.faz ]``

*Add Tag with Single Timestamp*

``inet:fqdn = woot.com addtag( baz.faz@201708151330 )``

``inet:fqdn = woot.com [ #baz.faz@201708151330 ]``

*Add Tag with Time Boundaries*

``inet:fqdn = woot.com addtag( baz.faz@20160101-20160131 )``

``inet:fqdn = woot.com [ #baz.faz@20160101-20160131 ]``


**Usage Notes:**

* ``addtag()`` operates on the output of a previous Storm query.
* Synapse will apply the specified tag(s) to all nodes returned by ``<query>``.
* Timestamps_ (in the format YYYYMMDDHHMMSS) can be added to a tag to show a point in time or a range during which the tag was known to be valid (equivalent to ``:seen:min`` and ``:seen:max`` for the tag).
* Timestamps must have a minimum resolution of YYYY.
* If one timestamp is provided and no timestamps currently exist on the tag, Synapse will set both the minimum and maximum timestamps as specified.
* If a two timestamps are provided and no timestamps currently exist on the tag, Synapse will set the minimum and maximum timestamps as specified.
* If timestamps already exist on the tag, Synapse will check the timestamp argument(s) provided against the existing timestamps:

  * If a timestamp argument is **earlier** than the current minimum timestamp, Synapse will update the minimum time with the new value.
  * If a timestamp argument is **later** than the current maximum timestamp, Synapse will update the maximum time with the new value.
  * If timestamp arguments fall **between** the existing minimum and maximum, no updates will be made.

* In short, the timestamp window on a given tag can be updated by being "pushed out" from the current values, but there is currently no way to "decrease" the window (other than deleting the tag from the node and recreating it).

**Operator Syntax Notes:**

* N/A

**Macro Syntax Notes:**

* Synapse will set the specified tag(s) for all previously referenced nodes (e.g., to the left of the ``<tag>`` statement) **whether those nodes are within or outside of the macro syntax brackets.** See `Special Note on Macro Syntax`_.

delnode()
---------

Deletes the specified node(s) from a Cortex.

**Operator Syntax:**

.. parsed-literal::
  *<query>* **delnode(** [ **force=1** ] **)**

**Macro Syntax:**

None.

**Examples:**

``inet:fqdn = woot.com delnode()``

``inet:fqdn = woot.com delnode(force=1)``

**Usage Notes:**

* ``delnode()`` operates on the output of a previous Storm query.
* ``delnode()`` can be executed with no parameters, although this effectively does nothing (i.e., the operator will consume input, but not actually delete the nodes).
* Use of the ``force=1`` parameter will delete the nodes input to the operator. The need to enter ``force=1`` is meant to require the user to think about what they're doing before executing the ``delnode()`` command (there is no "are you sure?" prompt). Future releases of Synapse will support a permissions structure that will limit the users who are able to execute this operator.

.. WARNING::
  ``delnode()`` has the potential to be destructive if executed on an incorrect, badly formed, or mistyped query. Users are strongly encouraged to validate their query by first executing it on its own to confirm it returns the expected nodes before executing ``delnode()``. Consider the difference between running ``inet:fqdn=woot.com delnode(force=1)`` (which deletes the single node for the domain ``woot.com`` and accidentally running ``inet:fqdn delnode(force=1)`` (which deletes **ALL** ``inet:fqdn`` nodes).

delprop()
---------

Todo

deltag()
--------

Deletes one or more tags from the specified node(s).

**Operator Syntax:**

.. parsed-literal::
  *<query>* **deltag(** *<tag>* [ **,** ... ] **)**

**Macro Syntax:**

.. parsed-literal::
  *<query>* **[ -#** *<tag>* ... **]**

**Examples:**

``inet:fqdn = woot.com deltag( baz.faz )``

``inet:fqdn = woot.com [ -#baz.faz ]``

**Usage Notes:**

* ``deltag()`` operates on the output of a previous query.
* Deleting a leaf tag deletes **only** the leaf tag.
* Deleting a non-leaf tag deletes that tag and all tags below it in the tag hierarchy.

**Operator Syntax Notes:**

* N/A

**Macro Syntax Notes:**

* Synapse will delete the specified tag(s) from all previously referenced nodes (e.g., to the left of the ``<tag>`` statement), **whether those nodes are within or outside of the macro syntax brackets.** See `Special Note on Macro Syntax`_.

Special Note on Macro Syntax
----------------------------

The square brackets ( ``[ ]`` ) used for the Storm macro syntax indicate “perform the enclosed data modifications” in a generic way. As such, the brackets are shorthand to request any of the following:

* Add nodes (``addnode()``).
* Add or modify properties (``setprop()``).
* Delete properties (once ``delprop()`` is implemented).
* Add tags (``addtag()``).
* Delete tags (``deltag()``).

This means that all of the above directives can be specified within a single set of macro syntax brackets, in any combination and in any order.

However, it is important to keep in mind that **the brackets are NOT a boundary that segregates nodes.** The brackets simply indicate the start and end of data modification shorthand. They do **NOT** separate "nodes these modifications should apply to" from "nodes they should not apply to". The Storm `operator chaining`__ with left-to-right processing order still applies. Any modification request that operates on previous Storm output will operate on the output of everything “leftwards” of the modifier, regardless of whether that content is within or outside of the macro syntax brackets. For example:

``inet:ipv4 = 12.34.56.78 inet:fqdn = woot.com [ inet:ipv4 = 1.2.3.4 :created = "2016-12-18 00:35" inet:fqdn = woowoo.com #my.tag ]``

The above statement will:

* Lift the nodes for IP ``12.34.56.78`` and domain ``woot.com`` (if they exist);
* Create the node for IP ``1.2.3.4`` (if it does not exist), or retrieve it if it does;
* Set the ``:created`` property for domain ``woot.com``;
* Create the node for domain ``woowoo.com`` (if it does not exist), or retrieve it if it does;
* Apply the tag ``my.tag`` to IP ``12.34.56.78`` and domain ``woot.com`` (if they exist) and to IP ``1.2.3.4`` and domain ``woowoo.com``.




.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_

.. _ingest: ../userguides/ug050_ing_intro.html
__ ingest_

.. _xref: ../userguides/ug007_dm_nodetypes.html#cross-reference-xref-nodes
__ xref_

.. _timestamps: ../userguides/ug008_dm_tagconcepts.html#tag-timestamps

.. _chaining: ../userguides/ug011_storm_basics.html#operator-chaining
__ chaining_
