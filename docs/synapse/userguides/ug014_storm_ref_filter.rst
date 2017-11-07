.. highlight:: none

Storm Reference - Filter Operator, Comparators, and Helpers
===========================================================

The filter operator operates on the output of **a previous Storm query.**

The filter operator, along with various comparison operators (comparators) and helper functions can be used to filter (refine, downselect) the set of nodes returned by the Storm query, based on specified criteria.

All of these operators are defined in storm.py_.

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Filter operations differ in that, while there is a ``filt()`` operator within Synapse that handles filter operations, the operator syntax is not available via Storm. In other words, all filter operations within Storm are performed using **macro syntax.**

filt()
------
Filters the set of nodes output by a Storm query by either including ( + ) or excluding ( - ) a set of nodes based on specified criteria.

**Macro Syntax**

.. parsed-literal::
  
  **+** | **-** *<prop>* | *<prop> <comparator> <valu>* | **#** *<tag>* | *<helper>* **(** *<params>* **)**

**Examples:**

These basic examples all use the "equals" comparator. See below for additional examples using other comparators.

*Filter by primary property (form):*

* Downselect to include only domains:
  ::
    +inet:fqdn

*Filter by primary <prop> / <valu>:*

* Downselect to exclude the domain google.com:
  ::
    -inet:fqdn = google.com
    
*Filter by secondary property:*

* Downselect to exclude domains with an "expires" property:
  ::
    -inet:fqdn:expires
    
*Filter by secondary <prop> / <valu>:*

* Downselect to include only those domains that are also logical zones:
  ::
    +inet:fqdn:zone = 1
 
*Filter by tag:*

* Downselect to exclude nodes tagged as associated with Tor:
  ::
    -#anon.tor
    
**Usage Notes:**

* A filter operation downselects from the working set of nodes by either **including** or **excluding** a subset of nodes based on a set of criteria.

  * **+** specifies an **inclusion filter.** The filter downselects the working set to **only** those nodes that match the specified criteria.
  * **-** specifies an **exclusion filter.** The filter downselects the working set to all nodes **except** those that match the specified criteria.
  
* The **comparator** (comparison operator) specifies how *<prop>* is evaulated with respect to *<valu>*. The most common comparator is equals ( = ), although other standard comparators are available (see below).
* A **helper function** is a Storm-specific feature that optimizes certain types of filter operations. Helpers are discussed separately below.

Filter Comparators
------------------


Filter Helper Functions
-----------------------
Todo

.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_
