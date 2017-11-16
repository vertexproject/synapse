Storm Reference - Statistical Operator
======================================

The statistical operator is used to generate data about data in Synapse.

``stat()`` is defined in common.py_ as opposed to storm.py_.

``stat()`` operates differently from other Storm operators:

* ``stat()`` operates directly on the Synapse storage layer using the row-level APIs (as opposed to the node (form) APIs used by other Storm operators). This is an optimization that allows ``stat()`` to answer questions across large data sets ("all of the IP addresses in Synapse") that would otherwise be too "heavy" (non-performant) to lift.

* Depending on the specific ``stat()`` handler used and the optimizations available in a particular Syanpse storage backing, the amount of time for a given ``stat()`` query to return may vary. For example, "count" operations will generally return much faster than "min" or "max" operations, even with the use of row-level APIs.

* ``stat()`` is designed as a stand-alone operator; because it uses a different set of APIs, it cannot operate on the output of a previous Storm query and so cannot be "chained" as part of a larger query.

* Because Storm expects to return node data as the result of a query, ``stat()`` generates an "ephemeral node" containing the results of the operation. That is, output is structured as a "node" with properties reflecting the query parameters and results. However, this ephemeral node does not have a node identifier (ID), and the node is not permanently stored in the Cortex.

* Because ``stat()`` results are **properties** on the resulting ephemeral node, the ``--props`` or ``--raw`` parameter should be used with the Synapse ``ask`` command to display relevant ``stat()`` output.

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

Note that in the raw output the node ID is ``null``, reflecting that this is an ephemeral node.

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
  stat:count = inet:fqdn
      :valu = 239887
  (1 results)

*Determine the number of .net domains in the Cortex:*
::
  ask --props stat(count,inet:fqdn:domain,valu=net)
  stat:count = inet:fqdn:domain
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
      :valu = {'fi': 1, 'ua': 2, 'ca': 1, 'ie': 2, 'ch': 2, 'pl': 1, 'ro': 1, 'cz': 1, 
      'kr': 1, 'de': 4, 'lu': 2, 'ae': 1, 'jp': 7, 'gb': 4, 'dk': 1, 'nl': 2, 'ru': 2,
      'sk': 1, 'vn': 1, 'hk': 1, 'us': 57, 'bz': 1, 'il': 6, 'au': 1, 'cn': 8}
  (1 results)

*Determine the distribution of registration dates for domains in the Cortex:*
::
  ask --props stat(histo,inet:whois:rec:created)
  stat:histo = inet:whois:rec:created
      :valu = {0: 2, 756604800000: 1, 1504310400000: 1, 1481932800000: 2, 
      1210605909000: 1, 1504224000000: 2, 1499212800000: 3, 1474588800000: 2, 
      1504051200000: 1, 1499126400000: 1, 1479427200000: 6, 1454889600000: 1, 
      1503964800000: 2, 1484265600000: 1, 1262183445000: 6, 
      ... <truncated for space>
      1494806400000: 3, 1496534400000: 2, 1480636800000: 3, 1455408000000: 1,
      1475020800000: 3, 1477872000000: 2, 1474934400000: 1, 1504396800000: 3,
      1494547200000: 1, 1484697600000: 1}
  (1 results)

**any** - Boolean; returns true if **any** of the specified *<prop>* evaluate to "true" in the Cortex

*Determine whether the inet:web:acct:avatar property is present (exists and is non-zero) on any nodes in the Cortex:*
::
  ask --props stat(any,inet:web:acct:avatar)
  stat:any = inet:web:acct:avatar
      :valu = True
  (1 results)

**all** - Boolean; returns true if **all** of the specified *<prop>* evaluate to "true" in the Cortex

*Determine whether all syn:tag:title properties in the Cortex have non-zero values:*
::
  ask --props stat(all,syn:tag:title)
  stat:all = syn:tag:title
      :valu = False
  (1 results)


.. _common.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/common.py

.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_
