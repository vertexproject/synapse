Storm Reference - Miscellaneous Operators
=========================================

Todo

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Where specific query examples are given, they are commonly provided in pairs using operator syntax followed by the equivalent macro syntax (if available).

show:cols()
-----------
Todo

limit()
-------
Provides a hard limit on the number of nodes which are emitted by the ``limit()`` operator.
This also back-propagates a ``limit=`` argument to the previous query operator.


Optional parameters:

* **Return limit:** specify the maximum number of nodes returned by the ``pivot()`` query.

  * ``limit=`` (operator syntax)

**Operator syntax:**

.. parsed-literal::

  **limit( *<limit>* )**

**Macro syntax:**

N/A

**Examples:**

* Limit the total number of nodes of a lift to 10 nodes:
  ::
    inet:ipv4*tag=hehe.haha limit(10)

* Limit the number of nodes which were emitted by a ``refs()`` command to 10 nodes:
  ::
    inet:ipv4=8.8.8.8 refs() limit(10)

* Limit the numbers of nodes which were emitted by a pivot macro operator to 10 nodes:
  ::
     inet:ipv4=8.8.8.8 inet:ipv4->inet:dns:a:ipv4 limit(10)

* Perform a pivot, limiting the output with ``limit()``, then find all the tags which are on the output nodes:
  ::
     inet:ipv4=8.8.8.8 inet:ipv4->inet:dns:a:ipv4 limit(10) totags()

* ``limit()`` will push its own limit into the preceeding query operator, so the following example would behave as if the ``pivot()`` had ``limit=10``:
  ::
     inet:ipv4=8.8.8.8 pivot(inet:dns:a:ipv4, limit=1) limit(10)

**Usage notes:**

* ``limit()`` does consume nodes by design.  It will readd the consume nodes back into the working set of nodes until the limit value is met.
* Since the ``limit()`` operator acts as a hard limit for the number of nodes it emits, care must be taken when using ``limit()`` in conjunction with multiple storm operations which do not consume nodes. It is possible that the use of ``limit()`` may discard all nodes from subsequent lifts or join type of operations.  In that case, it is typically better to just specify a ``limit=<value>`` argument to those operators directly, rather than using the ``limit()`` operator.
* The ``limit()`` operator causes the Storm query planner to insert the limit value into the previous storm operator as a ``limit=<value>`` argument. This will override any value already provided to an operator.
* The ``limit()`` oeprator may produce an artificial limit on the number of nodes produced by a query. It may be a good tool for sampling data but its use may impair the user from being able to perform effective analysis on the system.

opts()
------
Todo

save()
------
Todo

load()
------
Todo

clear()
-------
Todo

nexttag()
---------
Todo

dset()
------
Todo

get:tasks()
-----------
Todo

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_
