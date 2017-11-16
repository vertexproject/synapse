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

**Operator Syntax:**
::
  **stat(** *<handler>* **,** *<prop>* [ **,valu =** *<valu>* ] **)**

**Macro Syntax:**
N/A

**Examples:**

**count** - returns the number of nodes with the specified *<prop>* or *<prop> / <valu>*

*Determine the number of domains in the Cortex:*
::
  ask --props stat(count,inet:fqdn)
  stat:count - inet:fqdn
      :valu = 239887
  (1 results)

*Determine the number of .net domains in the Cortex:*
::
  ask --props stat(count,inet:fqdn:domain,valu=net)
  stat:count - inet:fqdn:domain
      :valu = 11438
  (1 results)

*Determine the total number of nodes (forms) in the Cortex:*
::
  ask --props stat(count,tufo:form)
  stat:count = tufo:form
      :valu = 100461644
  (1 results)

**min** - returns the minimum value for the specified *<prop>*

*Determine the minimum (earliest) date of birth for any person in the Cortex:*
::
  ask --props stat(min,ps:person:dob)
  stat:min - ps:person:dob
      :valu = 345772800000
  (1 results)

*Determine the minimum (earliest) observed date for any DNS A record in the Cortex:*
::
  ask --props stat(min,inet:dns:a:seen:min)
  stat:min = inet:dns:a:seen:min
      :valu = 1251770027000
  (1 results)

**Note:** date values are returned in Unix epoch format.

**max** - returns the maximum value for the specified *<prop>*

*Determine the maximum (largest) IPv6 address stored in the Cortex:*
::
  ask --props stat(max,inet:ipv6)
  stat:max = inet:ipv6
      :valu = 2a06:1700:0:14::207
  (1 results)

**sum** - returns the sum of the values of the specified *<prop>*

*Determine the total size of all files in the Cortex:*
::
  ask --props stat(sum,file:bytes:size)
  stat:sum = file:bytes:size
      :valu = 1088807999
  (1 results)


**mean** - returns the mean (average) of the values of the specified *<prop>*

*Determine the average size of a file in the Cortex:*
::
  ask --props stat(mean,file:bytes:size)
  stat:mean - file:bytes:size
      :valu = 1382.3535373669456
  (1 results)


**histo** - returns a histogram (count of instances by value) for the specified *<prop>*

**Note:** the ``ask --raw`` parameter returns results in JSON format, which may be more "readable" at the CLI for large histograms.

*Determine the distribution by country for organizations in the Cortex:*
::
  ask --props stat(histo,ou:org:cc)
  stat:histo - ou:org:cc
      :valu = {'fi': 1, 'ua': 2, 'ca': 1, 'ie': 2, 'ch': 2, 'pl': 1, 'ro': 1, 'cz': 1, 'kr': 1, 'de': 4, 'lu': 2, 'ae': 1, 'jp': 7, 'gb': 4, 'dk': 1, 'nl': 2, 'ru': 2, 'sk': 1, 'vn': 1, 'hk': 1, 'us': 57, 'bz': 1, 'il': 6, 'au': 1, 'cn': 8}
  (1 results)

*Determine the distribution of registration dates for domains in the Cortex:*

.. _common.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/common.py

.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_
