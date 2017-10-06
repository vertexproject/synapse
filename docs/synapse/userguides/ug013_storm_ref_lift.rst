.. highlight:: none

Storm Reference - Lift Operators
================================

The operators below can be used to retrieve a set of nodes from a Synapse hypergraph based on a set of specified criteria.

All of these operators are defined in storm.py_.

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Where specific query examples are given, they are commonly provided in pairs using operator syntax followed by the equivalent macro syntax (if available).

lift()
------

Lifts (retrieves) a set of nodes from a Cortex based on specified criteria.

Optional parameters:

* **"by" handler:** a "by" handler is a modifier that limits the lift criteria in various ways. Use of a "by" handler can be thought of as similar to performing a filter_ operation concurrent with lifting instead of after lifting.

  * ``by=`` (operator syntax)
  * ``*`` (macro syntax)
  
  "By" handlers have specific use cases and are documented separately_.

* **Return limit:** specify the maximum number of nodes to be returned by the lift query.

  * ``limit=`` (operator syntax)
  * ``^`` (macro syntax)
  
Lift operations are highly flexible. Only basic examples of ``lift()`` usage are provided here. See the section on `by handlers`__ for specialized lift operations using the "by" parameter.

**Operator Syntax:**

.. parsed-literal::
  
  **lift(** *<prop>* [ **,** *<valu>* **, limit=** *<limit>* **, by=** *<by>* ] **)**
  
**Macro Syntax:**

.. parsed-literal::
  
  *<prop>* [ **^** *<limit>* ***** *<by>* **=** *<valu>* ]
  
**Examples:**

*Lift by primary property (form):*

* Lift all domain nodes:
  ::
    lift( inet:fqdn )
    
    inet:fqdn
  
*Lift by secondary property:*

* Lift all ``inet:fqdn`` nodes that have an ``:updated`` secondary property:
  ::
    lift( inet:fqdn:updated )
    
    inet:fqdn:updated
  
*Lift by primary prop=valu:*

* Lift the node for domain ``woot.com``:
  ::
    lift( inet:fqdn , woot.com )
    
    inet:fqdn = woot.com
  
*Lift by secondary prop=valu:*

* Lift all DNS A record nodes where the domain is ``woot.com``:
  ::
    lift( inet:dns:a:fqdn , woot.com )
    
    inet:dns:a:fqdn = woot.com
  
*Lift with limit:*

* Lift 10 domain nodes:
  ::
    lift( inet:fqdn , limit=10 )
    
    inet:fqdn^10
  
* Lift 25 DNS A record nodes where the IP is ``127.0.0.1``:
  ::
    lift( inet:dns:a:ipv4 , 127.0.0.1 , limit=25)
    
    inet:dns:a:ipv4^25=127.0.0.1
  
*Lift with "by" handlers – lift by tag*

A single example using a "by" handler is provided for illustrative purposes. Individual "by" handlers may use their own custom syntax. See the `Storm By Handler`__ reference for additional details and usage.

* Lift by tag: lift all ``inet:fqdn`` nodes that have the tag ``my.tag``:
  ::
    lift( inet:fqdn , by=tag , my.tag)
    
    inet:fqdn*tag=my.tag
  
* Lift 10 ``inet:fqdn`` nodes with the tag ``my.tag``:
  ::
    lift(inet:fqdn,limit=10,by=tag,my.tag)
    
    inet:fqdn^10*tag=my.tag
  
**Usage Notes:**

* Nodes are typically lifted by:
  
  * **Primary property (form):** Lifting by form is possible but often impractical. Specifying a form alone attempts to lift all nodes of that form.
  * **Primary prop=valu:** Lifts a node by its primary property value. This is the most common method for lifting a single node.
  * **Secondary property:** Similar to lifting by form, lifting by a secondary property alone will lift all nodes with that property, regardless of the property's specific value. It is often impractical but may be feasible in limited cases (e.g., where only a relatively small number of nodes have an given secondary property).
  * **Secondary prop=valu:** Lifts all nodes that have the secondary property with the specified value.

* When lifting by prop + valu, additional comparison operators can be used besides just equals ( ``=`` ); these include 'not equals', 'greater than or equal to', etc. Use of these comparison operators is covered under Storm By Handlers.
* For ``lift()`` operations at the CLI, it is generally simpler to use macro syntax.
* The ``limit=`` option (``^`` in macro syntax) restricts **the number of nodes returned,** regardless of the total number of nodes that would otherwise be returned by the query. The specific nodes returned are non-deterministic. Limiting the results of a query is generally not useful for analysis (it artificially restricts results) but may be useful for troubleshooting queries or returning "exemplar" nodes (e.g., to examine their structure, properties, etc.)
* The number of nodes returned by any query can also be restricted by using the ``limit()`` operator_. However, this method executes the entire query, **then filters the results** to the specified number of nodes. So:

  ``lift ( inet:fqdn , limit=10 )``
  
  and
  
  ``lift ( inet:fqdn ) limit( 10 )``
  
  Are two different queries. The first lifts 10 ``inet:fqdn`` nodes. The second lifts **all** ``inet:fqdn`` nodes and limits the displayed results to 10.

guid()
------

Lifts one or more nodes based on each node's Globally Unique Identifier (GUID).

**Operator Syntax:**

.. parsed-literal::
  
  **guid(** *<guid>* [ **,** ... ] **)**
  
**Macro Syntax:**

N/A

**Examples:**
::
  guid( a4d82cf025323796617ff57e884a4738 )
  
  guid( 6472c5f038b0a4e5b1853c49e688fc74 , 5413b2ae7632a0909d63d31a33ec0807 )
  
**Usage Notes:**

* The GUID is a unique identifier assigned to every node. (This identifier is **not** the GUID value used as a primary property by some forms.)
* The GUID for a node or set of nodes can be displayed at the Synapse CLI by using the ``ask --raw`` option preceding a Storm query. For example, in the query output below, ``b19fe2a26bbe4a6c74b051142d0e5316`` is the GUID for the requested node:
  ::
    ask --raw inet:ipv4=1.2.3.4
    [
      [
        "b19fe2a26bbe4a6c74b051142d0e5316",
        {
          "inet:ipv4": 16909060,
          "inet:ipv4:asn": 0,
          "inet:ipv4:cc": "??",
          "inet:ipv4:type": "??",
          "tufo:form": "inet:ipv4"
        }
      ]
    ]
    (1 results)
  
alltag()
--------

Lifts a set of nodes based on one or more tags.

**Operator Syntax:**

.. parsed-literal::
  
  **alltag(** *<tag>* [ **,** ...] **)**
  
**Macro Syntax:**

.. parsed-literal::
  
  **#** *<tag>* ...
  
**Examples:**
*Lifts all nodes that have the tag foo.bar or the tag baz.faz.*
::
  alltag( foo.bar , baz.faz )
  
  #foo.bar #baz.faz

**Usage Notes:**

* ``alltag()`` retrieves all nodes that have **any** of the specified tags.


.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_

.. _filter: ../userguides/ug014_storm_ref_filter.rst

.. _separately: ../userguides/ug016_storm_ref_byhandlers.rst

.. _handlers: ../userguides/ug016_storm_ref_byhandlers.rst
__ handlers_

.. _handler: ../userguides/ug016_storm_ref_byhandlers.rst
__ handler_

.. _operator: ../userguides/ug018_storm_ref_misc.rst#limit
