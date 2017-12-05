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

* Pivot from a set of domains (``inet:fqdn`` nodes) to the DNS A records for those domains:
  ::
    pivot( inet:fqdn, inet:dns:a:fqdn )
    
    pivot( inet:dns:a:fqdn )
    
    inet:fqdn  ->  inet:dns:a:fqdn
    
    -> inet:dns:a:fqdn

* Pivot from a set of domains (``inet:fqdn`` nodes) to the DNS A records for those domains, but limit the results to 10 nodes:
  ::
    pivot( inet:fqdn, inet:dns:a:fqdn, limit=10 )
    
    pivot( inet:dns:a:fqdn, limit=10 )
    
    inet:fqdn^10  ->  inet:dns:a:fqdn

* Pivot from a set of domains (``inet:fqdn`` nodes) to the DNS A records for those domains, and from the IP addresses in the DNS A records to the set of IPv4 nodes (e.g., pivot from a set of domains to the set of IP addresses the domains resolved to).
  ::
    pivot(inet:fqdn,inet:dns:a:fqdn) pivot(inet:dns:a:ipv4,inet:ipv4)
      
    pivot(inet:dns:a:fqdn) pivot(:ipv4,inet:ipv4)
    
    inet:fqdn -> inet:dns:a:fqdn inet:dns:a:ipv4 
      -> inet:ipv4
    
    -> inet:dns:a:fqdn :ipv4 -> inet:ipv4

* Pivot from a set of domains to the set of subdomains for those domains:
  ::
    pivot(inet:fqdn,inet:fqdn:domain)
    
    pivot(inet:fqdn:domain)
    
    inet:fqdn -> inet:fqdn:domain
    
    -> inet:fqdn:domain

* Pivot from a set of email addresses to the set of domains registered to those email addresses.
  ::
    pivot(inet:email,inet:whois:regmail:email)
      pivot(inet:whois:regmail:fqdn,inet:fqdn)
    
    pivot(inet:whois:regmail:email) pivot(:fqdn,inet:fqdn)
    
    inet:email -> inet:whois:regmail:email 
      inet:whois:regmail:fqdn -> inet:fqdn
    
    -> inet:whois:regmail:email :fqdn -> inet:fqdn

* Pivot from a set of email addresses to the set of whois records associated with those email addresses.
  ::
    pivot(inet:email,inet:whois:contatct:email)
      pivot(inet:whois:contact:rec,inet:whois:rec)
    
    pivot(inet:whois:contact:email) pivot(:rec,inet:whois:rec)
    
    inet:email -> inet:whois:contact:email inet:whois:contact:rec
      -> inet:whois:rec
    
    -> inet:whois:contact:email inet:whois:contact:rec -> inet:whois:rec

**Usage notes:**

* If the source property for the pivot is the primary property of the working set of nodes, the *<srcprop>* can be omitted from Operator syntax. The *<srcprop>* can also be omitted from Macro syntax, unless a limit parameter ( ``^`` ) is specified.
* Relative properties can be used to specify *<srcprop>* as the source form(s) are, by definition, the form(s) of the working set of nodes.
* The ``limit=`` parameter can be provided as input to the ``pivot()`` operator itself; alternately the ``limit()`` operator_ can be used to specify a limit.

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

.. _operator: ../userguides/ug018_storm_ref_misc.html#limit
