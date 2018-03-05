.. highlight:: none

Storm Reference - Filter Operator, Comparators, and Helpers
===========================================================

The filter operator operates on the output of **a previous Storm query.**

The filter operator, along with various comparison operators (comparators) and helper functions can be used to filter (refine, downselect) the set of nodes returned by the Storm query, based on specified criteria.

The filter operator, comparators, and helper functions are all defined in storm.py_.

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Filter operations differ in that, while there is a ``filt()`` operator within Synapse, the operator syntax is not available via Storm. In other words, all filter operations within Storm are performed using **macro syntax.**

filt()
------
Filters the set of nodes output by a Storm query by either including ( + ) or excluding ( - ) a set of nodes based on specified criteria.

**Operator Syntax**

N/A

**Macro Syntax**

.. parsed-literal::
  
  **+** | **-** *<prop>* | *<prop> <comparator> <valu>* | **#** *<tag>* | *<helper>* **(** *<params>* **)**

**Examples:**

These basic examples all use the "equals" comparator. See below for additional examples using other comparators_.

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
  
* The **comparator** (comparison operator) specifies how *<prop>* is evaulated with respect to *<valu>*. The most common comparator is equals ( = ), although other standard comparators are available.
* A **helper function** is a Storm-specific feature that optimizes certain types of filter operations. Helpers are discussed separately_.

Filter Comparators
------------------

Filter operations can be performed using any of the standard mathematical / logical comparison operators (comparators):

* = : equals
* < : less than
* > : greater than
* <= : less than or equal to
* >= : greater than or equal to
* ~= : regular expression

**Examples:**

*Less than:*

* Downselect to include only domains created before January 1, 2017:
  ::

    +inet:fqdn:created < "20170101"

*Greater than:*

* Downselect to exclude files larger than 4096 bytes:
  ::

    -file:bytes:size > 4096
    
*Less than or equal to:*

* Downselect to include only DNS A records whose most recent observed time was on or before March 15, 2014 at 12:00 UTC:
  ::

    +inet:dns:a:seen:max <= "201403151200"
    
*Greater than or equal to:*

* Downselect to include only people born on or after January 1, 1980:
  ::

    +ps:person:dob >= "19800101"
    
*Regular expression:*

* Downselect to include only domains that start with the string "serve":
  ::

    +inet:fqdn ~= "serve*"
    
**Usage Notes:**

* Storm does not include a "not equal to" ( != ) comparator. Since filtering is either an inclusive ( + ) or exclusive ( - ) operation, equivalent logic can be performed using "equals" ( = ):

  * "**exclude** things **not equal** to *<foo>*" is equivalent to "**include** things **equal** to *<foo>*"
  * "**include** things **not equal** to *<foo>*" is equivanelt to "**exclude** things **equal** to *<foo>*"

* The Storm query planner will optimize lifts which which meet the following criteria:

  #. Do not specify a ``valu`` to lift by.
  #. Are immediately followed by a positive tag filter.

  This is done to prevent potentially dangerous queries which may cause all nodes of a given form or property to be
  lifted, which may require significant resources and generate results that are subsequentially discarded by a
  filter operation. For example, the following queries are all executed in the same fashion by the Storm runtime:

  ::

    inet:fqdn +#hehe.haha

    lift( inet:fqdn ) +#hehe.haha

    inet:fqdn*tag=hehe.haha


Filter Helper Functions
-----------------------

Storm includes a number of filter helper functions. These helpers are designed to optimize queries that would otherwise require multiple filter operations (such as querying for multiple values, or a range of values, for a specified property).

Storm also includes a set of `by handlers`__ that are used in conjunction with ``lift()`` operations (as in "lift by..."). While filter helpers optimize certain filter operations, they are carried out **after** an initial ``lift()`` operation. By handlers are similar to filter helpers but optimize certain ``lift()`` operations by effectively lifting and filtering nodes in a single operation.

With respect to the use of by handlers vs. filter helper functions, neither is "more correct" than the other. Because they perform similar functions (lift **and** filter vs. lift **then** filter) the set of by handlers and the set of filter functions largely parallel each other. In other words, you can "lift by X or Y" using a by handler or you can "filter by X or Y" using a filter helper.

By handlers are typically "more efficient" because they filter **during** the lift operation as opposed to after; however, the performance impact will typically be insignificant except in the case of very large ``lift()`` operations.

Individual filter helper functions are documented below.

**re()**

Todo

**and()**

Todo

**or()**

Todo

**in()**

Todo

**has()**

Todo

**seen()**

Todo

**range()**

Todo

**tag()**

Todo

**ival()**

Todo

**ivalival()**

Todo


.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_

.. _comparators: ../userguides/ug014_storm_ref_filter.html#filter-comparators

.. _separately: ../userguides/ug014_storm_ref_filter.html#filter-helper-functions

.. _handlers: ../userguides/ug016_storm_ref_byhandlers.html
__ handlers_
