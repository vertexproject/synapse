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


Filter Comparators
------------------


Filter Helper Funcitions
------------------------
Todo

.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_
