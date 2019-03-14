



.. highlight:: none

.. _storm-ref-data-mod:

Storm Reference - Data Modification
===================================

Storm can be used to directly modify the Synapse hypergraph by:

- adding or deleting nodes;
- setting, modifying, or deleting properties on nodes; and 
- adding or deleting tags from nodes.

While :ref:`syn-storm` and the Synapse command line (cmdr - see :ref:`syn-ref-cmd`) are not optimal for adding or modifying large amounts of data, users gain a powerful degree of flexibility and efficiency through the ability to create or modify data on the fly.

For adding or modifying larger amounts of data, it is preferable to use the Synapse feed utility (:ref:`syn-tools-feed`), the Synapse CSV tool (:ref:`syn-tools-csvtool`), or programmatic ingest of data to help automate the process.

.. WARNING::
  The ability to add and modify data directly from Storm is powerful and convenient, but also means users can inadvertently modify (or even delete) data inappropriately through mistyped syntax or premature striking of the "enter" key. While some built-in protections exist within Synapse itself it is important to remember that **there is no "are you sure?" prompt before a Storm query executes.**
  
  The following recommended best practices will help prevent inadvertent changes to the hypergraph:
  
    - Use the Synapse permissions system to enforce least privilege. Limit users to permissions appropriate for tasks they have been trained for / are responsible for.
    - Limit potentially destructive permissions even for trained / trusted users. Require the use of the Storm :ref:`storm-sudo` command for significant / critical changes (such as the deletion of nodes).
    - Use extreme caution when constructing complex Storm queries that may modify (or delete) large numbers of nodes. It is **strongly recommended** that you validate the output of a query by first running the query on its own to ensure it returns the expected results (set of nodes) before permanently modifying (or deleting) those nodes.

See :ref:`storm-ref-syntax` for an explanation of the syntax format used below.

See :ref:`storm-ref-type-specific` for details on special syntax or handling for specific data types.

Edit Mode
---------

To modify data in a Cortex using Storm, you must enter "edit mode". The use of square brackets ( ``[ ]`` ) within a Storm query can be thought of as entering edit mode, with the data in the brackets specifying the changes to be made. This is true for changes involving nodes, properties, and tags. **The only exception is the deletion of nodes, which is done using the Storm :ref:`storm-delnode` command.**

The square brackets used for the Storm data modification syntax indicate "perform the enclosed changes" in a generic way. The brackets are shorthand to request any of the following:

- `Add Nodes`_
- `Add or Modify Properties`_
- `Delete Properties`_
- `Add Tags`_
- `Remove Tags`_

This means that all of the above directives can be specified within a single set of brackets, in any combination and in any order. The only caveat is that a node must exist before it can be modified, so you must add a node before you add a secondary property or a tag. See `Combining Data Modification Operations`_ below for examples.

.. WARNING::
  It is critical to remember that **the brackets are NOT a boundary that segregates nodes;** the brackets simply indicate the start and end of data modification operations. They do **NOT** separate "nodes the modifications should apply to" from "nodes they should not apply to". Storm :ref:`storm-op-chain` with left-to-right processing order still applies. **Any modification request that operates on previous Storm output will operate on EVERYTHING to the left of the modify operation, regardless of whether those nodes are within or outside the brackets.**

Consider the following examples:

- ``inet:fqdn#aka.feye.thr.apt1 [ inet:fqdn=somedomain.com +#aka.eset.thr.sednit ]``
  
  The above Storm query will:
  
    - **Lift** all of the domains tagged ``#aka.feye.thr.apt1``.
    - **Create** the node for domain ``somedomain.com`` (if it does not exist), or lift it if it does.
    - **Apply the tag** ``aka.eset.thr.sednit`` to the domain ``somedomain.com`` **and** all of the domains tagged ``aka.feye.thr.apt1``


- ``[inet:ipv4=1.2.3.4 :asn=1111 inet:ipv4=5.6.7.8 :asn=2222]``
  
  The above Storm query will:
    
    - **Create** (or lift) the node for IP ``1.2.3.4``.
    - **Set** the node's ``:asn`` property to ``1111``.
    - **Create** (or lift) the node for IP ``5.6.7.8``.
    - **Set** the ``:asn`` property for **both** IPs to ``2222``.

Add Nodes
---------

Operation to add the specified node(s) to a Cortex.

**Syntax:**

[ <form> = <valu> ... ]

**Examples:**

*Create a simple node:*


.. parsed-literal::

    [ inet:fqdn=woot.com ]


*Create a composite (comp) node:*


.. parsed-literal::

    [ inet:dns:a=(woot.com, 12.34.56.78) ]


*Create a GUID node:*


.. parsed-literal::

    [ ou:org=2f92bc913918f6598bcf310972ebf32e]



.. parsed-literal::

    [ ou:org="*" ]


*Create a digraph (edge) node:*


.. parsed-literal::

    [ refs=((media:news, 00a1f0d928e25729b9e86e2d08c127ce), (inet:fqdn, woot.com)) ]


*Create multiple nodes:*


.. parsed-literal::

    [ inet:fqdn=woot.com inet:ipv4=12.34.56.78 hash:md5=d41d8cd98f00b204e9800998ecf8427e ]


**Usage Notes:**

- Storm can create as many nodes as are specified within the brackets. It is not necessary to create only one node at a time.
- For nodes specified within the brackets that do not already exist, Storm will create and return the node. For nodes that already exist, Storm will simply return that node.
- When creating a *<form>* whose *<valu>* consists of multiple components, the components must be passed as a comma-separated list enclosed in parentheses.
- Once a node is created, its primary property (*<form>* = *<valu>*) **cannot be modified.** The only way to "change" a node’s primary property is to create a new node (and optionally delete the old node). "Modifying" nodes therefore consists of adding, modifying, or deleting secondary properties (including universal properties) or adding or removing tags.

Add or Modify Properties
------------------------

Operation to add (set) or change one or more properties on the specified node(s).

The same syntax is used to apply a new property or modify an existing property.

**Syntax:**

*<query>* **[ :** *<prop>* **=** *<pval>* ... **]**

**Examples:**

*Add (or modify) secondary property:*


.. parsed-literal::

    <inet:ipv4> [ :loc=us.oh.wilmington ]


*Add (or modify) universal property:*


.. parsed-literal::

    <inet:dns:a> [ .seen=("2017/08/01 01:23", "2017/08/01 04:56") ]


*Add (or modify) a string property to a null value:*


.. parsed-literal::

    <media:news> [ :summary="" ]


**Usage Notes:**

- Additions or modifications to properties are performed on the output of a previous Storm query. 
- Storm will set or change the specified properties for all nodes in the current working set (i.e., all nodes resulting from Storm syntax to the left of the *<prop> = <pval>* statement(s)) for which that property is valid, **whether those nodes are within or outside of the brackets.**
- Specifying a property will set the *<prop> = <pval>* if it does not exist, or modify (overwrite) the *<prop> = <pval>* if it already exists. **There is no prompt to confirm overwriting of an existing property.**
- Storm will return an error if the inbound set of nodes contains any forms for which *<prop>* is not a valid property. For example, attempting to set a ``:loc`` property when the inbound nodes contain both domains and IP addresses will return an error as ``:loc`` is not a valid secondary property for a domain (``inet:fqdn``).
- Secondary properties **must** be specified by their relative property name. For example, for the form ``foo:bar`` with the property ``baz`` (i.e., ``foo:bar:baz``) the relative property name is specified as ``:baz``.
- Storm can set or modify any secondary property (including universal properties) except those explicitly defined as read-only (``'ro' : 1``) in the data model. Attempts to modify read only properties will return an error.

Delete Properties
-----------------

Operation to delete (fully remove) one or more properties from the specified node(s).

.. WARNING::
  Storm syntax to delete properties has the potential to be destructive if executed following an incorrect, badly formed, or mistyped query. Users are **strongly encouraged** to validate their query by first executing it on its own (without the delete property operation) to confirm it returns the expected nodes before adding the delete syntax. While the property deletion syntax cannot fully remove a node from the hypergraph, it is possible for a bad property deletion operation to irreversibly damage hypergraph pivoting and traversal.

**Syntax:**

*<query>* **[ -:** *<prop>* ... **]**

**Examples:**

*Delete a property:*


.. parsed-literal::

    <inet:ipv4> [ -:loc ]


*Delete multiple properties:*


.. parsed-literal::

    <media:news> [ -:author -:summary ]


*Delete property using elevated privileges:*


.. parsed-literal::

    sudo | <ou:org> [ -:phone ]


**Usage Notes:**

- Property deletions are performed on the output of a previous Storm query.
- Storm will delete the specified property / properties for all nodes in the current working set (i.e., all nodes resulting from Storm syntax to the left of the *-:<prop>* statement), **whether those nodes are within or outside of the brackets.**
- Deleting a property fully removes the property from the node; it does not set the property to a null value.
- Properties which are read-only ( ``'ro' : 1`` ) as specified in the data model cannot be deleted.
- Storm edit operations may need to be executed using the Storm :ref:`storm-sudo` command to succeed. (As a best practice, we **strongly recommend** requiring administrator permissions activated using :ref:`storm-sudo` to carry out delete operations.)

Delete Nodes
------------

Nodes can be deleted from a Cortex using the Storm :ref:`storm-delnode` command.

Add Tags
--------

Operation to add one or more tags to the specified node(s).

**Syntax:**

*<query>* **[ +#** *<tag>* [ **=(** *<min_time>* **,** *<max_time>* **)** ] ... **]**

**Examples:**

*Add tags:*



.. parsed-literal::

    <inet:fqdn> [ +#aka.feye.thr.apt1 +#cno.infra.sink.hole ]


*Add tag with timestamps:*


.. parsed-literal::

    <inet:fqdn> [ +#cno.infra.sink.hole=(2014/11/06, 2016/11/06) ]


**Usage Notes:**

- Tag additions are performed on the output of a previous Storm query.
- Storm will add the specified tag(s) to all nodes in the current working set (i.e., all nodes resulting from Storm syntax to the left of the *+#<tag>* statement) **whether those nodes are within or outside of the brackets.**
- Timestamps can be added to a tag to show a point in time or an interval during which the tag was known to be valid or applicable to the node in question. In the second example above, the timestamps on the tag ``cno.infra.sink.hole`` are meant to indicate that the domain was sinkholed between 11/6/2014 and 11/6/2016.)
- Timestamps are applied only to the tags to which they are explicitly added. For example, adding a timestamp to the tag ``#foo.bar.baz`` does **not** add the timestamp to tags ``#foo.bar`` and ``#foo``.
- See the sections on time *<time>* and interval *<ival>* types in :ref:`storm-ref-type-specific` for additional details on times.

Modify Tags
-----------

Tags are "binary" in that they are either applied to a node or they are not. The only modification that can be made to an existing tag is to add or update any associated timestamp, which can be done using the same syntax as `Add Tags`_.

To "change" the tag applied to a node, you must add the new tag and delete the old one.

The Storm :ref:`storm-movetag` command can be used to modify tags in bulk - that is, rename an entire set of tags, or move a tag to a different tag tree.

Remove Tags
-----------

Operation to delete one or more tags from the specified node(s).

Removing a tag from a node differs from deleting the node representing a tag (a ``syn:tag`` node), which can be done using the Storm :ref:`storm-delnode` command.

.. WARNING::
  Storm syntax to remove tags has the potential to be destructive if executed on an incorrect, badly formed, or mistyped query. Users are **strongly encouraged** to validate their query by first executing it on its own to confirm it returns the expected nodes before adding the tag deletion syntax.
  
  In addition, it is **essential** to understand how removing a tag at a given position in a tag tree affects other tags within that tree. Otherwise, tags may be improperly left in place ("orphaned") or inadvertently removed.

**Syntax:**

*<query>* **[ -#** *<tag>* ... **]**

**Examples:**

*Remove a tag:*


.. parsed-literal::

    <inet:ipv4> [ -#cno.infra.anon.tor ]


*Remove a tag using elevated privileges:*


.. parsed-literal::

    sudo | <inet:ipv4> [ -#cno.infra.anon.tor ]


**Usage Notes:**

- Tag deletions are performed on the output of a previous Storm query.
- Storm will delete the specified tag(s) from all nodes in the current working set (i.e., all nodes resulting from Storm syntax to the left of the -#<tag> statement), **whether those nodes are within or outside of the brackets.**
- Deleting a leaf tag deletes **only** the leaf tag from the node. For example, ``[ -#foo.bar.baz ]`` will delete the tag ``#foo.bar.baz`` but leave the tags ``#foo.bar`` and ``#foo`` on the node.
- Deleting a non-leaf tag deletes that tag and **all tags below it in the tag hierarchy** from the node. For example, ``[ -#foo ]`` used on a node with tags ``#foo.bar.baz`` and ``#foo.hurr.derp`` will remove **all** of the following tags:

  - ``#foo.bar.baz``
  - ``#foo.hurr.derp``
  - ``#foo.bar``
  - ``#foo.hurr``
  - ``#foo``

- Storm edit operations may need to be executed using the Storm :ref:`storm-sudo` command to succeed. (As a best practice, we **strongly recommend** requiring administrator permissions activated using :ref:`storm-sudo` to carry out delete operations.)

Combining Data Modification Operations
--------------------------------------

The square brackets representing edit mode are used for a wide range of operations, meaning it is possible to combine operations within a single set of brackets.

**Examples:**

*Create a node and add secondary properties:*



.. parsed-literal::

    [ inet:ipv4=94.75.194.194 :loc=nl :asn=60781 ]


*Create a node and add a tag:*


.. parsed-literal::

    [ inet:fqdn=blackcake.net +#aka.feye.thr.apt1 ]

