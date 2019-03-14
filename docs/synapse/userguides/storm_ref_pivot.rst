



.. highlight:: none

.. _storm-ref-pivot:

Storm Reference - Pivoting
==========================

Pivot operations are performed on the output of a Storm query. Pivot operators are used to navigate from one set of nodes to another based a specified relationship. The pivot operations available within Storm are:

- `Pivot Out Operator`_
- `Pivot In Operator`_
- `Pivot With Join`_
- `Pivot to Digraph (Edge) Nodes`_
- `Pivot Across Digraph (Edge) Nodes`_
- `Pivot to Tags`_
- `Pivot from Tags`_
- `Implicit Pivot Syntax`_

.. NOTE::
  When pivoting from a secondary property (*<prop> = <pval>*), the secondary property **must** be specified using the relative property name only (``:baz`` vs. ``foo:bar:baz``). Specifying the full property name before the pivot would be interpreted as an additional lift (i.e., ``<inet:dns:a> inet:dns:a:fqdn -> inet:fqdn`` would be interpreted as "take a set of inet:dns:a records from an initial query, lift all inet:dns:a records with an :fqdn property (i.e., every inet:dns:a node in the Cortex), and then pivot to the associated inet:fqdn nodes").

See :ref:`storm-ref-syntax` for an explanation of the syntax format used below.

See :ref:`storm-ref-type-specific` for details on special syntax or handling for specific data types.

Pivot Out Operator
------------------

The pivot out operator ( ``->`` ) is the primary Storm pivot operator. The pivot out operator pivots from a primary or secondary property value of the current set of nodes to a primary or secondary property value of another set of nodes. This operator is also referred to as the "reference out" operator as it is used to pivot to nodes that are **referenced by** the current node set.

The pivot out operator is used to:

- pivot from the primary property of the inbound set of nodes to the equivalent secondary property of another set of nodes,
- pivot from a secondary property of the inbound set of nodes to the equivalent primary property of another set of nodes,
- pivot from any / all secondary properties of the inbound set of nodes to the equivalent primary property of any / all nodes (“wildcard” pivot out), and
- pivot from a secondary property of the inbound set of nodes to the equivalent secondary property of another set of nodes.

`Pivot to Digraph (Edge) Nodes`_ and `Pivot Across Digraph (Edge) Nodes`_ are covered separately below.

**Syntax:**

*<query>* **->** *<form>* **:** *<prop>*

*<query>* **:** *<prop>* **->** *<form>*

*<query>* **-> ***
 
*<query>* **:** *<prop>* **->** *<form>* **:** *<prop>*

**Examples:**

*Pivot from primary property (<form> = <valu>) to secondary property (<prop> = <pval>):*

- Pivot from a set of domains to all of their subdomains regardless of depth:



.. parsed-literal::

    <inet:fqdn> -> inet:fqdn:zone


- Pivot from a set of domains to their DNS A records:


.. parsed-literal::

    <inet:fqdn> -> inet:dns:a:fqdn


*Pivot from secondary property (<prop> = <pval>) to primary property (<form> = <valu>):*

- Pivot from a set of DNS A records to the resolution IP addresses contained in those records:


.. parsed-literal::

    <inet:dns:a> :ipv4 -> inet:ipv4


*Pivot from all secondary properties to all forms (<prop> = <pval> to <form> = <valu>):*

- Pivot from a set of WHOIS records to all nodes whose primary property equals *any* of the secondary properties of the WHOIS record (the asterisk ``*`` is a wildcard that indicates pivot to **any** applicable node):


.. parsed-literal::

    <inet:whois:rec> -> *


*Pivot from secondary property (<prop> = <pval>) to secondary property (<prop> = <pval>):*

- Pivot from the WHOIS records for a set of domains to the DNS A records for the same domains:


.. parsed-literal::

    <inet:whois:rec> :fqdn -> inet:dns:a:fqdn


**Usage Notes:**

- Pivoting out using the asterisk wildcard ( ``*`` ) is sometimes called a **refs out** pivot because it pivots from **all** secondary properties to **all nodes referenced by** those properties.
- Pivoting using the wildcard is based on strong data typing within the Synapse data model, so will only pivot out to properties that match both *<type>* and *<valu>* / *<pval>*. This means that the following nodes will **not** be returned by a wildcard pivot out:

  - Nodes with matching *<valu>* / *<pval>* but of different *<type>*. For example, if a node’s secondary property is a string (type *<str>*) that happens to contain a valid domain (type *<inet:fqdn>*), a wildcard pivot out from the node with the string value will **not** return the ``inet:fqdn`` node.
  - Digraph (edge) nodes, whose properties are of type *<ndef>* (node definition, or *<form>,<valu>* tuples). See `Pivot to Digraph (Edge) Nodes`_ and `Pivot Across Digraph (Edge) Nodes`_ for details on pivoting to / through those forms.

- It is possible to perform an explicit pivot between properties of different types. For example: ``<inet:dns:query> :name -> inet:fqdn``


Pivot In Operator
-----------------

The pivot in ( ``<-``) operator is similar to but separate from the pivot out ( ``->``) operator. Instead of pivoting to the set of nodes the current set references, the pivot in operator pivots to the set of nodes that references the current set of nodes.

Logically, any pivot in operation can be expressed as an equivalent pivot out operation. For example, the following two pivots would be functionally equivalent:

- Pivot out from a set of domains to the DNS A records referenced by the domains:

  `<inet:fqdn> -> inet:dns:a:fqdn`

- Pivot in to a set of domains from the DNS A records that reference the domains:

  `<inet:fqdn> <- inet:dns:a:fqdn`

Because of this equivalence, and because "left to right" logic is generally more intuitive, **only pivot out has been fully implemented in Storm.** (The second example, above, will actually return an error.) The pivot in operator exists, but is only used to simplify certain special case pivot operations:

- pivot from any / all primary properties of the inbound set of nodes to the equivalent secondary property of any / all nodes ("wildcard" pivot in), and
- reverse `Pivot to Digraph (Edge) Nodes`_ and reverse `Pivot Across Digraph (Edge) Nodes`_ (covered separately below).

**Syntax:**

*<query>* **<- ***
 
**Example:**

*Pivot from all primary properties to all nodes with an equivalent secondary property (<form> = <valu> to <prop> = <pval>):*

- Pivot from a set of domains to all nodes with a secondary property that references the domains:



.. parsed-literal::

    <inet:fqdn> <- *


**Usage Notes:**

- Pivoting in using the asterisk wildcard ( ``*`` ) is sometimes called a **refs in** pivot because it pivots from **all** nodes to **all nodes that reference** those nodes.
- Pivoting in using the wildcard will return an instance of a node for **each** matching secondary property. For example, where a node may have the same *<pval>* for two different secondary properties (such as ``:domain`` and ``:zone`` on an ``inet:fqdn`` node), the pivot in will return two copies of the node. Results can be de-duplicated using the Storm :ref:`storm-uniq` command.
- Pivoting using the wildcard is based on strong data typing within the Synapse data model, so will only pivot in from properties that match both *<type>* and *<valu>* / *<pval>*. This means that the following nodes will **not** be returned by a wildcard pivot in:

  - Nodes with matching *<valu>* / *<pval>* but of different *<type>*. For example, if a node’s primary property (such as a domain, type *<inet:fqdn>*) - happens to be referenced as as a different type (such as a string, type *<str>*) as a secondary property of another node, a wildcard pivot in to the ``inet:fqdn`` node will **not** return the node with the string value.
  - Digraph (edge) nodes, whose properties are of type *<ndef>* (node definition, or *<form>,<valu>* tuples). See `Pivot to Digraph (Edge) Nodes`_ and `Pivot Across Digraph (Edge) Nodes`_ for details on pivoting to / through those forms.

- Other than digraph (edge) node navigation / traversal, pivot in can only be used with the wildcard ( ``*`` ). That is, pivot in does not support specifying a particular target form:

  ``inet:fqdn=woot.com <- inet:dns:a:fqdn``

  The above query will return an error. A filter operation (see :ref:`storm-ref-filter`) can be used to downselect the results of a wildcard pivot in operation to a specific set of forms:
  
  ``inet:fqdn=woot.com <- * +inet:dns:a``
  
  Note that when attempting to specify a target form using `Implicit Pivot Syntax`_, Storm currently (**and incorrectly**) returns 0 nodes (even if nodes exist) instead of generating an error:
  
  ``inet:fqdn=woot.com <- inet:dns:a``


Pivot With Join
---------------

The pivot and join operator ( ``-+>`` ) performs the specified pivot operation but joins the results with the inbound set of nodes. That is, the inbound nodes are retained and combined with the results of the pivot.

Another way to look at the difference between a pivot and a join is that a pivot operation **consumes** nodes (the inbound set is discarded and only nodes resulting from the pivot operation are returned) but a pivot and join does **not** consume the inbound nodes.

The pivot and join operator is used to:

- retain the inbound nodes and pivot from the primary property of the inbound set of nodes to the equivalent secondary property of another set of nodes,
- retain the inbound nodes and pivot from a secondary property of the inbound set of nodes to the equivalent primary property of another set of nodes,
- retain the inbound nodes and pivot from any / all secondary properties of the inbound set of nodes to the equivalent primary property of any / all nodes (“wildcard” pivot out), and
- retain the inbound nodes and pivot from a secondary property of the inbound set of nodes to the equivalent secondary property of another set of nodes.

**Syntax:**

*<query>* **-+>** *<form>* **:** *<prop>*

*<query>* **:** *<prop>* **-+>** *<form>*

*<query>* **-+> ***
 
*<query>* **:** *<prop>* **-+>** *<form>* **:** *<prop>*

**Examples:**

*Pivot and join from primary property (<form> = <valu>) to secondary property (<prop> = <pval>):*

- Return a set of domains and all of their immediate subdomains:



.. parsed-literal::

    <inet:fqdn> -+> inet:fqdn:domain


*Pivot and join from secondary property (<prop> = <pval>) to primary property (<form> = <valu>):*

- Return a set of DNS A records and their associated IP addresses:


.. parsed-literal::

    <inet:dns:a> :ipv4 -+> inet:ipv4


*Pivot and join from all secondary properties to all forms (<prop> = <pval> to <form> = <valu>):*

- Return a set of WHOIS records and all nodes whose primary property equals any of the secondary properties of the WHOIS record (the asterisk ( ``*`` ) is a wildcard that indicates pivot to any applicable node):


.. parsed-literal::

    <inet:whois:rec> -+> *


*Pivot and join from secondary property (<prop> = <pval>) to secondary property (<prop> = <pval>):*

- Return the WHOIS records for a set of domains and the DNS A records for the same domains:


.. parsed-literal::

    <inet:whois:rec> :fqdn -+> inet:dns:a:fqdn


**Usage Notes:**

- A pivot and join using the wildcard ( ``*`` ) will pivot to all nodes whose primary property (*<form> = <valu>*) matches a secondary property (*<prop> = <pval>*) of the inbound nodes. This **excludes** digraph nodes (such as ``refs`` or ``has`` nodes) because their primary property is a pair of ``ndefs`` (node definitions, or *<form>, <valu>* tuples).

Pivot to Digraph (Edge) Nodes
-----------------------------

Digraph (edge) nodes <link to background docs> are of type ``edge`` or ``timeedge``. These nodes (forms) are unique in that their primary property value is a pair of **node definitions** (type ``ndef``) - that is, *<form>, <valu>* tuples. (``timeedge`` forms are comprised of two *<form>, <valu>* tuples and an additional *<time>* value). Each  *<form>, <valu>* tuple from the primary property is broken out as secondary property ``:n1`` or ``:n2``. This means that pivoting to and from digraph nodes is a bit different than pivoting to and from nodes whose properties are a simple *<valu>* or *<pval>*.

**Syntax:**

*<query>* **->** *<edge>* | *<timeedge>* [**:n2**]

*<query>* **-+>** *<edge>* | *<timeedge>* [**:n2**]

*<query>* **<-** *<edge>* | *<timeedge>*

**Examples:**

*Pivot out from a set of nodes whose ndefs (<form>, <valu>) are the first element (:n1) in a set of a digraph nodes:*

- Pivot out from a person node to the set of digraph nodes representing things that person “has”:



.. parsed-literal::

    <ps:person> -> has


- Return an article and the set of digraph nodes representing things “referenced” by the article:


.. parsed-literal::

    <media:news> -+> refs


- Pivot out from a person node to the set of ``timeedge`` digraph nodes representing places that person has been to (and when):


.. parsed-literal::

    <ps:person> -> wentto


- Pivot out from a set of domains to the set of digraph nodes representing things that **reference** the domains:


.. parsed-literal::

    <inet:fqdn> -> refs:n2


*Pivot in from a set of nodes whose ndefs (<form>, <valu>) are the second element (:n2) in a set of a digraph nodes:*

- Pivot in from an article to the set of digraph nodes representing things that “have” the article (e.g., people or organizations who authored the article):


.. parsed-literal::

    <media:news> <- has


**Usage Notes:**
- The pivot out and pivot in operators have been optimized for digraph nodes. Because digraphs use ``ndef`` properties, Storm makes the following assumptions:

  - When pivoting to or from a set of nodes to a set of digraph nodes, pivot using the ``ndef`` (*<form>,<valu>*) of the inbound nodes and not their primary property (*<valu>*) alone.
  - When pivoting **out** to a digraph node, the inbound nodes’ *<form>,<valu>* ``ndef`` will be the **first** element (``:n1``) of the digraph. You must explicitly specify ``:n2`` to pivot to the second element.
  - When pivoting **in** to a digraph node, the inbound nodes’ *<form>,<valu>* ``ndef`` will be the **second** element (``:n2``) of the digraph. It is not possible to pivot in to ``:n1``.

- Pivoting to / from digraph nodes is one of the specialized use cases for the pivot in ( ``<-``) operator, however the primary use case of pivot in with digraph nodes is reverse edge traversal (see `Pivot Across Digraph (Edge) Nodes`_). See `Pivot In Operator`_ for general limitations of the pivot in operator.

Pivot Across Digraph (Edge) Nodes
---------------------------------

Because digraph nodes represent generic edge relationships, analytically we are often more interested in the nodes on "either side" of the edge than in the digraph node itself. For this reason, the pivot operators have been optimized to allow a syntax for easily navigating "across" these digraphs (edges).

**Syntax:**

*<query>* **->** *<edge>* | *<timeedge>* **->** ***** | *<form>*

*<query>* **<-** *<edge>* | *<timeedge>* **<-** ***** | *<form>*

**Examples:**

- Traverse a set of ``has`` nodes to pivot from a person to all the things the person "has":


.. parsed-literal::

    <ps:person> -> has -> *


- Traverse a set of ``refs`` nodes to pivot from a set of domains to the articles that "reference" the domain:


.. parsed-literal::

    <inet:fqdn> <- refs <- media:news


- Traverse a set of ``wentto`` nodes to pivot from a person to the locations the person has visited:


.. parsed-literal::

    <ps:person> -> wentto -> *


**Usage Notes:**

- Storm makes the following assumptions to optimize the two pivots:

  - For pivots out, the first pivot is to the digraph nodes’ ``:n1`` property and the second pivot is from the digraph nodes’ ``:n2`` property.
  - For pivots in, the first pivot is to the digraph nodes’ ``:n2`` property and the second pivot is from the digraph nodes’ ``:n1`` property.

- Pivoting "across" the digraph nodes still performs two pivot operations (i.e., to the digraph nodes and then from them). As such it is still possible to apply an optional filter to the digraph nodes themselves before the second pivot.

Pivot to Tags
-------------

Pivot to tags syntax allows you to pivot from a set of nodes to the set of ``syn:tag`` nodes for the tags applied to those nodes. This includes:

- pivot to all leaf tag nodes,
- pivot to all tag nodes,
- pivot to all tag nodes matching a specified prefix, and
- pivot to tag nodes matching an exact tag.

See the Synapse background documents <link> for additional discussion of tags and ``syn:tag`` nodes.

**Syntax:**

*<query>* **-> #** [ ***** | **#** *<tag>* **.*** | **#** *<tag>* ]

**Examples:**

*Pivot to all leaf tag nodes:*

- Pivot from a set of domains to the ``syn:tag`` nodes for all leaf tags applied to those domains:


.. parsed-literal::

    <inet:fqdn> -> #


*Pivot to ALL tag nodes:*

- Pivot from a set of files to the ``syn:tag`` nodes for **all** tags applied to those files:


.. parsed-literal::

    <file:bytes> -> #*


*Pivot to all tag nodes matching the specified prefix:*

- Pivot from a set of IP addresses to the ``syn:tag`` nodes for all tags applied to those IPs that are part of the anonymized infrastructure tag tree:


.. parsed-literal::

    <inet:ipv4> -> #cno.infra.anon.*


*Pivot to tag nodes exactly matching the specified tag:*

- Pivot from a set of nodes to the ``syn:tag`` node for ``#foo.bar`` (if present on the inbound set of nodes):


.. parsed-literal::

    <query> -> #foo.bar


**Usage Notes:**

- Pivot to all tags ( ``#*`` ) and pivot by prefix matching ( ``#<tag>.*`` ) will match **all** tags in the relevant tag trees from the inbound nodes, not just the leaf tags. For example, for an inbound node with tag ``#foo.bar.baz``, ``#*`` will return the ``syn:tag`` nodes for ``foo``, ``foo.bar``, and ``foo.bar.baz``.

Pivot from Tags
---------------

Pivot from tags syntax allows you to pivot from a set of ``syn:tag`` nodes to the set of nodes that have those tags.

**Syntax:**

*<syn:tag>* **->** ***** | *<form>*

**Examples:**

- Pivot to all domains tagged with tags from any of the inbound ``syn:tag`` nodes:



.. parsed-literal::

    <syn:tag> -> inet:fqdn


- Pivot to **all** nodes tagged with tags from any of the inbound ``syn:tag`` nodes:


.. parsed-literal::

    <syn:tag> -> *


**Usage Notes:**

- In many cases, pivot from tags is functionally equivalent to :ref:`lift-tag`. That is, the following queries will both return all nodes tagged with ``#aka.feye.thr.apt1``:

  ``syn:tag=aka.feye.thr.apt1 -> *``
  
  ``#aka.feye.thr.apt1``
  
  Pivoting from tags is most useful when used in conjunction with `Pivot to Tags`_ - that is, taking a set of inbound nodes, pivoting to the ``syn:tag`` nodes for any associated tags (pivot to tags), and then pivoting out again to other nodes tagged with some or all of those tags (pivot from tags).

Implicit Pivot Syntax
---------------------

If the target or source property of a pivot is readily apparent - that is, given the inbound and target forms, only one set of properties makes sense for that pivot - the properties do not have to be explicitly specified. This **implicit pivot syntax** allows users to enter more concise pivot queries in some cases.

Implicit pivot syntax can be used to pivot from a primary property to a secondary property, as well as from a secondary property to a primary property.

**Examples:**

*Pivot from primary property (<form> = <valu>) to implicit secondary property (<prop> = <pval>):*

- Pivot from a set of domains to their associated DNS A records:

**Regular (full) syntax:**


.. parsed-literal::

    <inet:fqdn> -> inet:dns:a:fqdn


**Implicit syntax:**


.. parsed-literal::

    <inet:fqdn> -> inet:dns:a


With implicit syntax, the target property ``:fqdn`` can be omitted because it is the only logical target given a set of ``inet:fqdn`` nodes as the source.

*Pivot from implicit secondary property (<prop> = <pval>) to primary property (<form> = <valu>):*

- Pivot from a set of DNS A records to their associated IP addresses:

**Regular (full) syntax:**


.. parsed-literal::

    <inet:dns:a> :ipv4 -> inet:ipv4


**Implicit syntax:**


.. parsed-literal::

    <inet:dns:a> -> inet:ipv4


With implicit syntax, the source property ``:ipv4`` can be omitted because it is the only logical source given a set of ``inet:ipv4`` nodes as the target.

*Use of multiple implicit pivots:*

- Pivot from a set of domains to their DNS A records and then to the associated IP addresses:

**Regular (full) syntax:**


.. parsed-literal::

    <inet:fqdn> -> inet:dns:a:fqdn :ipv4 -> inet:ipv4


**Implicit syntax:**


.. parsed-literal::

    <inet:fqdn> -> inet:dns:a -> inet:ipv4

