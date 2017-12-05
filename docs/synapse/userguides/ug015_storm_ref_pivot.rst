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

  * ``limit=`` (operational syntax)
  * ``^`` (macro syntax)

**Operator syntax:**

.. parsed-literal::

  **pivot(** [ *<srcprop>* **,** ] *<dstprop>* [ **, limit=** *<limit>* ] **)**

**Macro syntax:**

.. parsed-literal::

  [ *<srcprop>* **^** *<num>* ] **->** *<dstprop>*

**Examples:**



join()
------
Todo

refs()
------
Todo

fromtags()
----------
Todo

totags()
--------
Todo

jointags()
----------
Todo

tree()
------

The `tree()` operator acts as a recursive pivot for forms which reference their own types or multiple duplicate ptypes.

**Operator Syntax:**

.. parsed-literal::

  *<query>* **tree(** *<srcprop> , <dstprop>,* [ *recurnlim=<n>* ] **)**

  *<query>* **tree(** *<relative srcprop>, <dstprop>,* [ *recurnlim=<n>* ] **)**

  *<query>* **tree(** *<dstprop>,* [ *recurnlim=<n>* ] **)**

**Macro Syntax:**

There is no macro syntax for the tree() operator.

**Examples:**
::

  # Full form - traversing to all of the woot.com children nodes
  inet:fqdn = woot.com tree( inet:fqdn, inet:fqdn:domain )

  # Relative source only form - traversing ou:suborg relationships
  ou:org:alias = someorg -> ou:suborg:org tree( :sub, ou:suborg:org ) :sub -> ou:org

  # Destination only form - traversing all of the woot.com children nodes.
  inet:fqdn = woot.com tree( inet:fqdn:domain )

  # Select the entire syn:tage=foo tree.
  syn:tag=foo tree(syn:tag, syn:tag:up)

  # tree() up - select all parent fqdns of mx.somebox.woot.com
  inet:fqdn = mx.somebox.woot.com tree( inet:fqdn:domain, inet:fqdn )

**Usage Notes:**

* The ``tree()`` operator acts as a recursive pivot. This allows a user to build a set of nodes which have
  self-referencing forms. For example, in the ``syn:tag`` form, the ``syn:tag:up`` ptype is a ``syn:tag``, so we can
  recursively pivot on it.
* The ``recurlim`` option may be set to limit the depth of the number of lookups performed by the tree() operator. This
  can be used to only grab a portion of a node tree.  This value defaults to 20; and can be set to zero (``recurlim=0``)
  in order to disable this limit.
* The ``tree()`` operator does consume all of the nodes present in the source `query` it uses to start pivoting from,
  and only returns the nodes from the resulting pivots.

**Operator Syntax Notes:**

* N/A

**Macro Syntax Notes:**

* ``tree()`` has no Macro syntax implementation.

.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_
