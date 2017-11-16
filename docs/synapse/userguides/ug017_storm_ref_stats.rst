Storm Reference - Statistical Operator
======================================

The statistical operator is used to generate data about data in Synapse.

``Stat()`` is defined in common.py_ as opposed to storm.py_.

``Stat()`` operates differently from other Storm operators:

* It operates directly on the Synapse storage layer using the row-level APIs (as opposed to the node (form) APIs used by other Storm operators). This is an optimization that allows ``stat()`` to answer questions across large data sets ("all of the IP addresses in Synapse") that would otherwise be too "heavy" (non-performant) to lift.

* Depending on the specific ``stat()`` handler used and the optimizations available in a particular Syanpse storage backing, the amount of time for a given ``stat()`` query to return may vary. For example, "count" operations will generally return much faster than "min" or "max" operations, even with the use of row-level APIs.

* It is designed as a stand-alone operator; because it uses a different set of APIs, it cannot operate on the output of a previous query and so cannot be "chained" as part of a larger Storm query.

* Because Storm expects to return node data as the result of a query, ``stat()`` generates an "ephemeral node" containing the results of the operation. That is, output is structured as a "node" with properties reflecting the query parameters and results. However, this ephemeral node does not have a node identifier (ID), and the node is not permanently stored in the Cortex.

* Because ``stat()`` results are properties on the resulting ephemeral node, the ``--props`` or ``--raw`` parameter should be used with the Synapse ``ask`` command to display relevant ``stat()`` output.

The following examples show how the output of ``stat()`` varies based on the ``ask`` parameter used:

*No parameters:*
::
  ask stat(count,inet:fqdn)
  stat:count = inet:fqdn
  (1 results)

*"props" parameter:*
::
  ask --props stat(count,inet:fqdn)
  stat:count = inet:fqdn
      :valu = 239886
  (1 results)

*"raw" parameter:*
::
  ask --raw stat(count,inet:fqdn)
  [
    [
      null,
      {
        "stat:count": "inet:fqdn",
        "stat:count:valu": 239886,
        "tufo:form": "stat:count"
      }
    ]
  ]
  (1 results)

Note that in the raw output the node ID is ``null``.

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Where specific query examples are given, they are commonly provided in pairs using operator syntax followed by the equivalent macro syntax (if available).

stat()
------

Generates statistics about data in Synapse.



.. _common.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/common.py

.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_
