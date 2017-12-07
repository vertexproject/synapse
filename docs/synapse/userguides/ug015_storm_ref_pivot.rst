.. highlight:: none

Storm Reference - Pivot Operators
=================================

Pivot operators operate on the output of a **previous Storm query.**

The operators below can be used to pivot from one set of nodes to another set of nodes within a Synapse hypergraph based on a set of specified criteria.

All of these operators are defined in storm.py_.

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Where specific query examples are given, they are commonly provided in pairs using operator syntax followed by the equivalent macro syntax (if available).

pivot()
-------
Returns a set of nodes that share a specified property of the same type / valu as the original set of nodes.

Optional parameters:

* **Return limit:** specify the maximum number of nodes returned by the ``pivot()`` query.

  * ``limit=`` (operator syntax)

**Operator syntax:**

.. parsed-literal::

  **pivot(** [ *<srcprop>* **,** ] *<dstprop>* [ **, limit=** *<limit>* ] **)**

**Macro syntax:**

.. parsed-literal::

  [ *<srcprop>* ] **->** *<dstprop>*

**Examples:**

* Pivot from a set of domains (``inet:fqdn`` nodes) in the working set to the DNS A records for those domains:
  ::
    pivot( inet:fqdn, inet:dns:a:fqdn )
    
    pivot( inet:dns:a:fqdn )
    
    inet:fqdn  ->  inet:dns:a:fqdn
    
    -> inet:dns:a:fqdn

* Pivot from a set of domains in the working set to the DNS A records for those domains, but limit the results to 10 nodes:
  ::
    pivot( inet:fqdn, inet:dns:a:fqdn, limit=10 )
    
    pivot( inet:dns:a:fqdn, limit=10 )

* Pivot from a set of domains in the working set to the DNS A records for those domains, and from the IP addresses in the DNS A records to the associated set of IPv4 nodes (e.g., pivot from a set of domains to the set of IP addresses the domains resolved to).
  ::
    pivot( inet:fqdn, inet:dns:a:fqdn ) pivot( inet:dns:a:ipv4, inet:ipv4 )
      
    pivot( inet:dns:a:fqdn ) pivot( :ipv4, inet:ipv4 )
    
    inet:fqdn -> inet:dns:a:fqdn inet:dns:a:ipv4 
      -> inet:ipv4
    
    -> inet:dns:a:fqdn :ipv4 -> inet:ipv4

* Pivot from a set of domains in the working set to the set of subdomains for those domains:
  ::
    pivot( inet:fqdn, inet:fqdn:domain )
    
    pivot( inet:fqdn:domain )
    
    inet:fqdn -> inet:fqdn:domain
    
    -> inet:fqdn:domain

* Pivot from a set of email addresses in the working set to the set of domains registered to those email addresses.
  ::
    pivot( inet:email, inet:whois:regmail:email )
      pivot( inet:whois:regmail:fqdn, inet:fqdn )
    
    pivot( inet:whois:regmail:email ) pivot( :fqdn, inet:fqdn )
    
    inet:email -> inet:whois:regmail:email 
      inet:whois:regmail:fqdn -> inet:fqdn
    
    -> inet:whois:regmail:email :fqdn -> inet:fqdn

* Pivot from a set of email addresses in the working set to the set of whois records associated with those email addresses.
  ::
    pivot( inet:email, inet:whois:contact:email )
      pivot( inet:whois:contact:rec, inet:whois:rec )
    
    pivot( inet:whois:contact:email ) pivot( :rec, inet:whois:rec )
    
    inet:email -> inet:whois:contact:email inet:whois:contact:rec
      -> inet:whois:rec
    
    -> inet:whois:contact:email inet:whois:contact:rec -> inet:whois:rec

**Usage notes:**

* If the source property for the pivot is the primary property of the working set of nodes, the *<srcprop>* can be omitted from both Operator and Macro syntax.
* If the source property for the pivot is a secondary property of the working set of nodes, relative property syntax can be used to specify *<srcprop>* as the source properties are, by definition, properties from the working set of nodes.
* The ``limit=`` parameter can be provided as input to the ``pivot()`` operator itself when using Operator syntax. Alternately the ``limit()`` operator_ can be used after the ``pivot()`` operator (in either Operator or Macro syntax) to specify a limit on the number of nodes returned.

join()
------
Todo

refs()
------
Returns the set of nodes that "reference" or are "referenced by" the working set of nodes.

Optional parameters:

* **in:** return all nodes that have a secondary property *<type> (<ptype>) = <valu>* that is the same as (**references**) any primary *<prop> = <valu>* in the working set of nodes.
* **out:** return all the nodes whose primary *<prop> = <valu>* is the same as (is **referenced by**) any secondary property *<type> (<ptype>) = <valu>* in the working set of nodes.
* If no parameters are specified, ``refs()`` will return the combined results of both ``refs(in)`` and ``refs(out)`` (e.g., execute all pivots to / from the working set of nodes).
* **Return limit:** specify the maximum number of nodes returned by the ``pivot()`` query.
  
  * ``limit=`` (operator syntax)

**Operator syntax:**

.. parsed-literal::
  **refs(** [ **in** | **out , limit=** *<num>* ] **)**

**Macro syntax:**

N/A

**Examples:**

* Return all of the nodes that **reference** a set of nodes:
  ::
    refs( in )

  Assume a set of ``inet:fqdn`` nodes in the working set. ``refs(in)`` will return any node with a secondary property type *<ptype> = <valu>* that matches the *<type> = <valu>* of those ``inet:fqdn`` nodes. For example, this may include ``inet:dns:a`` nodes (``inet:dns:a:fqdn``), ``inet:whois:rec`` nodes (``inet:whois:rec:fqdn``), additional ``inet:fqdn`` nodes (``inet:fqdn:domain``), etc.

* Return all the nodes **referenced by** a set of nodes:
  ::
    refs( out )

  Assume a set of ``inet:dns:a`` nodes in the working set. ``refs(out)`` will return any node with a primary *<type> = <valu>* that matches any secondary property type *<ptype> = <valu>* in the working set. As an ``inet:dns:a`` record includes secondary properties of type ``inet:fqdn`` (``inet:dns:a:fqdn``) and ``inet:ipv4`` (``inet:dns:a:ipv4``), the query may return those node types.

* Return all of the nodes that **reference** or are **referenced by** a set of nodes:
  ::
    refs()

  Assume a set of ``inet:email`` nodes in the working set. An ``inet:email`` *<type> = <valu>* may be referenced by *<ptype> = <valu>* from a variety of forms, including ``inet:whois:contact`` (``inet:whois:contact:email``), ``inet:dns:soa`` (``inet:dns:soa:email``) or ``inet:web:acct`` (``inet:web:acct:email``). Based on its secondary properties, a *<ptype> = <valu>* from an ``inet:email`` node may reference *<type> = <valu>* forms such as ``inet:fqdn`` (``inet:email:fqdn``) or ``inet:user`` (``inet:email:user``).

**Usage notes:**

* ``refs()`` / ``refs(in)`` / ``refs(out)`` can be useful in an "exploratory" manner to identify what other nodes / forms are "reachable from" (can be pivoted to or from) the working set of nodes. However, because ``refs()`` essentially carries out all possible pivots, the set of nodes returned may be quite large. In such cases a more focused ``pivot()`` or ``join()`` operation may be more useful.
* ``refs()`` does not consume nodes, so the results of a ``refs()`` operation will include both the original working set as well as the resulting set of nodes.
* The ``limit=`` parameter can be provided as input to the ``pivot()`` operator itself when using Operator syntax. Alternately the ``limit()`` operator_ can be used after the ``pivot()`` operator (in either Operator or Macro syntax) to specify a limit on the number of nodes returned.
* Because ``refs()`` does not consume nodes, this impacts the results returned by the ``limit=`` parameter or the ``limit()`` operator. The ``limit=`` parameter will return **all** of the original nodes, **plus** the specified number of results. The ``limit()`` operator will return a **total** number of nodes equal to the specified limit, first including the original working nodes and then including resulting nodes (if possible).

fromtags()
----------
Given a working set that contains one or more ``syn:tag`` nodes, returns the specified set of nodes to which those tags have been applied.

``fromtags()`` can be thought of as pivoting **from** a set of **tags**, to a set of nodes that have those tags.

Optional parameters:

*  **<form>:** return only nodes of the specified form(s).
* If no forms are specified, ``fromtags()`` returns all nodes for all forms to which the tags are applied.

**Operator syntax:**

.. parsed-literal::
  
  **fromtags(** [ *<form_1>* **,** *<form_2>* **,** *...<form_n>* ] **)**

**Macro syntax:**

N/A

**Examples:**

* Return the set of all nodes to which a given set of tags have been applied:
  ::
    fromtags()

* Return the set of ``inet:fqdn`` and ``inet:email`` nodes to which a given set of tags have been applied:
  ::
    fromtags( inet:fqdn, inet:email )

**Usage notes:**

* ``fromtags()`` pivots from leaf tags only. For example, if the working set contains ``syn:tag=foo.bar.baz``, ``fromtags()`` will return nodes with ``#foo.bar.baz`` but **not** nodes with ``#foo.bar`` or ``#foo`` alone.
* In some cases, pivoting with ``fromtags()`` is equivalent to lifting by tag; for example, ``ask #foo.mytag`` is equivalent to ``ask syn:tag=foo.mytag fromtags()``. However, ``fromtags()`` can also take more complex queries as input.
* For example, say you are tagging nodes with analytical observations made by third parties: ``syn:tag=alias.acme.redtree`` ("things Acme Corporation states are associated with "Redtree" malware") or ``syn:tag=alias.foo.redtree`` ("things Foo Organization states are associated with "Redtree" malware"). To return all nodes **any** organization associates with "Redtree" you could do:
  
  ``ask syn:tag:base=redtree fromtags()``

* ``totags()`` and ``fromtags()`` are often used together to:

  * pivot from a set of nodes, to the tags applied to those nodes, to other nodes that have the same tags; or
  * from a set of tags, to nodes those tags are applied to, to other tags applied to those same nodes.

totags()
--------
Returns the set of all tags (``syn:tag`` nodes) applied to the working set of nodes.

``totags()`` can be thought of as pivoting from a set of nodes, **to** the set of **tags** applied to those nodes.

Optional parameters:

* **leaf:** specify whether ``totags()`` should return **only** leaf tags (``leaf = 1``) or **all** tags in the tag hierarchy (``leaf = 0``).

* If no parameter is specified, ``totags()`` assumes ``leaf = 1``.

**Operator syntax:**

.. parsed-literal::
  
  **totags(** [ **leaf = 1** | **0** ] **)**

**Macro syntax:**

N/A

**Examples:**

* Return the set of leaf tags applied to a given set of nodes:
  ::
    totags( leaf = 1 )
    
    totags()

* Return all tags applied to a given set of nodes:
  ::
    totags( leaf = 0 )

**Usage notes:**

* ``totags()`` and ``totags(leaf=1)`` return the set of leaf tags only. For example, if nodes in the working set have the tag ``#foo.bar.baz``, ``totags()`` will return ``syn:tag=foo.bar.baz``, but not ``syn:tag=foo.bar`` or ``syn:tag=foo``.

* As tags represent analytical observations or assessments, ``totags()`` can be useful for "summarizing" the set of assessments associated with a given set of nodes. For example, with respect to cyber threat data, assume you are using tags to track malicious activity associated with a particular threat cluster (threat group), such as "Threat Cluster 5". After retrieving all nodes tagged as part of that threat cluster, you can use ``totags()`` to list all other tags (analytical observations) that are associated with the nodes in that threat cluster. Depending on the analytical model (tag structure) you are using, those tags could represent the names of malware families, sets of tactics, techniques, and procedures (TTPs) used by the threat cluster, and so on:
  ::
    ask #cno.threat.t5.tc totags()

* ``totags()`` and ``fromtags()`` are often used together to:
  
  * pivot from a set of nodes, to the tags applied to those nodes, to other nodes that have the same tags; or
  * from a set of tags, to nodes those tags are applied to, to other tags applied to those same nodes.

jointags()
----------
Returns all specified nodes that have **any** of the tags applied to **any** of the working set of nodes.

``jointags()`` can be thought of as executing a ``totags()`` operation followed by a ``fromtags()`` operation.

Optional parameters:

* **<form>:** return only nodes of the specified form(s).
* If no forms are specified, ``jointags()`` returns all nodes for all forms to which the tags are applied.

**Operator syntax:**

.. parsed-literal::
  
  **jointags(** [ *<form_1>* **,** *<form_2>* **,** *...<form_n>* ] **)**

**Macro syntax:**

N/A

**Examples:**

* Return the set of nodes that share any of the tags applied to the working set of nodes:
  ::
    jointags()

* Return the set of ``inet:fqdn`` and ``inet:email`` nodes that share any of the tags applied to the working set of nodes:
  ::
    jointags( inet:fqdn, inet:email )

**Usage notes:**

* ``jointags()`` pivots using the set of leaf tags only. For example if nodes in the working set have the tag ``#foo.bar.baz``, ``jointags()`` will return other nodes with ``#foo.bar.baz``, but not nodes with ``#foo.bar`` or ``#foo`` alone.

* ``jointags()``, like ``refs()``, can be useful to "explore" other nodes that share some analytical assessment (tag) with the working set of nodes, but may return a large number of nodes. It may be more efficient to narrow the scope of the query using ``totags()`` in combination with a filter operator (e.g., to potentially limit the specific tags selected) followed by ``fromtags()``.

tree()
------

Recursively return the set of nodes that have a property type (*<type> = <valu>* or *<ptype> = <valu>*) that matches the specified property type (*<type> = <valu>* or *<ptype> = <valu>*) from the working set of nodes.

``tree()`` can be thought of as a recursive pivot that can be used to "traverse" a set of nodes which reference their own types or multiple duplicate ptypes (such as domains / subdomains, or tags in a tag hierarchy). This allows a user to build a set of nodes which have self-referencing forms. The recursive pivot takes the place of multiple single pivots.

Optional parameters:

* **recurnlim:** recursion limit; specify the maximum number of recursive queries to execute.
* In the absence of a ``recurnlim`` parameter, ``tree()`` assumes a default limit of 20 (``recurnlim=20``).
* To disable limits on recursion (e.g., continue executing pivots until no more results are returned), ``recurnlim`` should be set to 0 (``recurnlim=0``).

**Operator Syntax:**

.. parsed-literal::

  **tree(** [ *<srcprop>* **,** ] *<dstprop>* [ **, recurnlim=** *<n>* ] **)**
  
**Macro Syntax:**

N/A

**Examples:**

*Traverse "down" a set of nodes:*

* Given a set of domains (``inet:fqdn``) in the working set, return the domain(s) and all of their child domains (subdomains):
  ::
    tree( inet:fqdn, inet:fqdn:domain )
    
    tree( inet:fqdn:domain )

* Given a base tag (``syn:tag``) in the working set, return all tags in that tag's hierarchy / tag tree:
  ::
    tree( syn:tag, syn:tag:up )
    
    tree( syn:tag:up )

* Given a parent organization (``ou:org``), pivot to the organization / sub-organization nodes (``ou:suborg``) where that org is a parent, and return all of the sub-organizations under that parent (full Storm query provided for clarity):
  ::
     ask --props ou:org=<org_guid> -> ou:suborg:org tree( ou:suborg:sub,
       ou:suborg:org ) :sub -> ou:org

*Traverse "up" a set of nodes:*

* Given a set of domains (``inet:fqdn``) in the working set, return the domain(s) and all of their parent domains:
  ::
    tree( inet:fqdn:domain, inet:fqdn )
    
    tree( :domain, inet:fqdn)

* Given a child organization (``ou:org``), pivot to the organization / sub-organization nodes (``ou:suborg``) where that org is a child, and return all of the parent organizations above that child (full Storm query provided for clarity):
  ::
    ask --props ou:org=<org_guid> -> ou:suborg:sub tree( ou:suborg:org,
      ou:suborg:sub ) :org -> ou:org

**Usage Notes:**

* If the source property for the ``tree()`` operation is the primary property of the working set of nodes, *<srcprop>* can be omitted.
* If the source property for the ``tree()`` operation is a secondary property of the working set of nodes, relative property syntax can be used to specify *<srcprop>* as the source properties are, by definition, properties from of the working set of nodes.


.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_

.. _operator: ../userguides/ug018_storm_ref_misc.html#limit
