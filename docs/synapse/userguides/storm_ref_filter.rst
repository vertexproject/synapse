



.. highlight:: none

.. _storm-ref-filter:

Storm Reference - Filtering
===========================

Filter operations are performed on the output of a previous Storm query. A filter operation downselects from the working set of nodes by either including or excluding a subset of nodes based on a set of criteria.

- ``+`` specifies an **inclusion** filter. The filter downselects the working set to **only** those nodes that match the specified criteria.
- ``-`` specifies an **exclusion** filter. The filter downselects the working set to all nodes **except** those that match the specified criteria.

The types of filter operations within Storm are highly flexible and consist of the following:

- `Simple Filters`_
- `Filters Using Standard Comparison Operators`_
- `Filters Using Extended Comparison Operators`_
- `Compound Filters`_
- `Subquery Filters`_

In most cases, the criteria and available comparators for lift operations (:ref:`storm-ref-lift`) are also available for filter operations.

.. NOTE::
   When filtering based on a secondary property (*<prop>*) or secondary property value (*<prop> = <pval>*), the property can be specified using the relative property name only (``:baz`` vs. ``foo:bar:baz``) unless the full property name is required for disambiguation. In the examples below, both syntaxes (i.e., using the full property name and the relative property name) are provided where appropriate for completeness. See the :ref:`data-props` section of :ref:`data-model-terms` for additional discussion of properties.

See :ref:`storm-ref-syntax` for an explanation of the syntax format used below.

See :ref:`storm-ref-type-specific` for details on special syntax or handling for specific data types.

Simple Filters
--------------

"Simple" filters refers to the most "basic" filter operations: that is, operations to include ( ``+`` ) or exclude ( ``-`` ) a subset of nodes based on:

- The presence of a specific primary or secondary property in the working set.
- The presence of a specific primary property value or secondary property value in the working set.
- The presence of a specific tag on nodes in the working set.

The only difference between "simple" filters and "filters using comparison operators" is that we have defined simple filters as those that use the equals ( ``=`` ) comparator, which is the easiest comparator to use to explain basic filtering concepts.

**Syntax:**

*<query>* **+** | **-** *<form>* | *<form>* **=** *<valu>* | *<prop>* | *<prop>* **=** *<pval>* | *<tag>*

**Examples:**

*Filter by Form (<form>):*

- Downselect to include only domains:



.. parsed-literal::

    <query> +inet:fqdn


*Filter by Primary Property Value:*

- Downselect to exclude the domain ``google.com``:


.. parsed-literal::

    <query> -inet:fqdn=google.com


*Filter by Presence of Secondary Property:*

- Downselect to exclude DNS SOA records with an "email" property:


.. parsed-literal::

    <query> -inet:dns:soa:email



.. parsed-literal::

    <query> -:email


*Filter by Secondary Property Value:*

- Downselect to include only those domains that are also logical zones:


.. parsed-literal::

    <query> +inet:fqdn:iszone=1



.. parsed-literal::

    <query> +:iszone=1


*Filter by Presence of Universal Property:*

- Downselect to include only those domains with a ``.seen`` property:


.. parsed-literal::

    <query> +inet:fqdn.seen



.. parsed-literal::

    <query> +.seen


*Filter by tag:*

- Downselect to exclude nodes tagged as associated with Tor:


.. parsed-literal::

    <query> -#cno.infra.anon.tor


**Usage Notes:**

- The comparator (comparison operator) specifies how *<form>* or *<prop>* is evaluted with respect to *<valu>* or *<pval>*. The most common comparator is equals (``=``), although other comparators are available (see below).

Filters Using Standard Comparison Operators
-------------------------------------------

Filter operations can be performed using any of the standard mathematical / logical comparison operators (comparators):

- ``=``: equals (described above)
- ``!=`` : not equals
- ``<`` : less than
- ``>`` : greater than
- ``<=`` : less than or equal to
- ``>=`` : greater than or equal to

**Syntax:**

*<query>* **+** | **-** *<form>* | *<prop>* *<comparator>* *<valu>* | *<pval>*

**Examples:**

*Filter by Not Equals:*

- Downselect to exclude the domain ``google.com``:


.. parsed-literal::

    <query> +inet:fqdn != google.com


*Filer by Less Than:*

- Downselect to include only WHOIS records collected prior to January 1, 2017: 


.. parsed-literal::

    <query> +inet:whois:rec:asof < 2017/01/01



.. parsed-literal::

    <query> +:asof < 2017/01/01


*Filter by Greater Than:*

- Downselect to exclude files larger than 4096 bytes:


.. parsed-literal::

    <query> -file:bytes:size > 4096



.. parsed-literal::

    <query> -:size > 4096


*Filter by Less Than or Equal To:*

- Downlselect to include only WHOIS nodes for domains created on or before noon on January 1, 2018:


.. parsed-literal::

    <query> +inet:whois:rec:created <= "2018/01/01 12:00"



.. parsed-literal::

    <query> +:created <= "2018/01/01 12:00"


*Filter by Greater Than or Equal To:*

- Downlselect to include only people born on or after January 1, 1980:


.. parsed-literal::

    <query> +ps:person:dob >= 1980/01/01



.. parsed-literal::

    <query> +:dob >= 1980/01/01


**Usage Notes:**

- Storm supports both equals ( ``=`` ) and not equals ( ``!=`` ) comparators for filtering, although use of not equals is not strictly necessary. Because filters are either inclusive ( ``+`` ) or exclusive ( ``-`` ), equivalent filter logic for “not equals” can be performed with “equals”. That is, “include domains not equal to google.com” (``+inet:fqdn != google.com``) is equivalent to “exclude the domain google.com” (``-inet:fqdn = google.com``).

Filters Using Extended Comparison Operators
-------------------------------------------

Storm supports a set of extended comparison operators (comparators) for specialized filter operations. In most cases, the same extended comparators are available for both lifting and filtering:

- `Filter by Regular Expression (~=)`_
- `Filter by Prefix (^=)`_
- `Filter by Time or Interval (@=)`_
- `Filter by Range (*range=)`_
- `Filter by Set Membership (*in=)`_
- `Filter by Proximity (*near=)`_
- `Filter by Tag (#)`_

Filter by Regular Expression (~=)
+++++++++++++++++++++++++++++++++

The extended comparator ``~=`` is used to filter nodes based on standard regular expressions.

**Syntax:**

*<query>* **+** | **-** *<form>* | *<prop>* **~=** *<regex>*

**Examples:**

*Filter by Regular Expression:*

- Downselect to include only mutexes that start with the string “Net”:


.. parsed-literal::

    <query> +it:dev:mutex ~= "^Net"


**Usage Notes:**

- Filtering using regular expressions is performed by matching the regex against the relevant property of each node in the working set. Because filtering is performed on a subset of data from the Cortex (i.e., the working set) there should be no noticeable performance impact with a regex filter. However, **prefix filtering** (see below) is supported for string types and can be used as a more efficient alternative in some cases.

Filter by Prefix (^=)
+++++++++++++++++++++

Synapse performs prefix indexing on string types, which optimizes filtering nodes whose *<valu>* or *<pval>* starts with a given prefix. The extended comparator ``^=`` is used to filter nodes by prefix.

**Syntax:**

*<query>* **+** | **-** *<form>* [  **:** *<prop>* ] **^=** *<prefix>*

**Examples:**

*Filter by primary property by prefix:*

- Downselect to include only usernames that start with "pinky":


.. parsed-literal::

    <query> +inet:user ^= pinky


*Filter by secondary property by prefix:*

- Downselect to include only organizations whose name starts with "International":


.. parsed-literal::

    <query> +ou:org:name ^= international



.. parsed-literal::

    <query> +:name ^= international


**Usage Notes:**

- Extended string types that support dotted notation (such as the ``loc`` or ``syn:tag`` types) have custom behaviors with respect to lifting and filtering by prefix. See the respective sections in :ref:`storm-ref-type-specific` for additional details.

Filter by Time or Interval (@=)
+++++++++++++++++++++++++++++++

The time extended comparator (``@=``) supports filtering nodes based on comparisons among various combinations of timestamps and date/time ranges (intervals).

See :ref:`storm-ref-type-specific` for additional detail on the use of ``time`` and ``ival`` data types.

**Syntax:**

*<query>* **+** | **-** *<prop>* **@=(** *<ival_min>* **,** *<ival_max>* **)**

*<query>* **+** | **-** *<prop>* **@=** *<time>*

**Examples:**

*Filter by comparing an interval to an interval:*

- Downselect to include only those DNS A records whose ``.seen`` values fall between July 1, 2018 and August 1, 2018:



.. parsed-literal::

    <query> +inet:dns:a.seen@=(2018/07/01, 2018/08/01)



.. parsed-literal::

    <query> +.seen@=(2018/07/01, 2018/08/01)


- Downselect to include only those nodes (e.g., IP addresses) that were associated with Tor between June 1, 2016 and September 30, 2016 (note the interval here applies to the **tag** representing Tor):


.. parsed-literal::

    <query> +#cno.infra.anon.tor@=(2016/06/01, 2016/09/30)


*Filter by comparing a timestamp to an interval:*

- Downselect to include only those DNS request nodes whose requests occurred between 2:00 PM November 12, 2017 and 9:30 AM November 14, 2017:


.. parsed-literal::

    <query> +inet:dns:request:time@=("2017/11/12 14:00:00", "2017/11/14 09:30:00")



.. parsed-literal::

    <query> +:time@=("2017/11/12 14:00:00", "2017/11/14 09:30:00")


*Filter by comparing an interval to a timestamp:*

- Downselect to include only those DNS A records whose resolution time windows include the date December 1, 2017:


.. parsed-literal::

    <query> +inet:dns:a.seen@=2017/12/01



.. parsed-literal::

    <query> +.seen@=2017/12/01


*Filter by comparing a timestamp to a timestamp:*

- Downselect to include only those WHOIS records whose domain was registered (created) on March 19, 1986 at 5:00 AM:


.. parsed-literal::

    <query> +inet:whois:rec:created@="1986/03/19 05:00:00"



.. parsed-literal::

    <query> +:created@="1986/03/19 05:00:00"


*Filter using an interval with relative times:*

- Downselect to include only those ``inet:whois:email`` nodes that were observed between January 1, 2018 and the present:


.. parsed-literal::

    <query> +inet:whois:email.seen@=(2018/01/01, now)



.. parsed-literal::

    <query> +.seen@=(2018/01/01, now)


- Downselect to include only DNS requests whose requests occurred within one week after October 15, 2018:


.. parsed-literal::

    <query> +inet:dns:request:time@=(2018/10/15, "+ 7 days")



.. parsed-literal::

    <query> +:time@=(2018/10/15, "+ 7 days")


**Usage Notes:**

- When specifying an interval, the minimum value is included in the interval but the maximum value is **not** (the equivalent of “greater than or equal to *<min>* and less than *<max>*”). This behavior is slightly different than that for ``*range=``, which includes **both** the minimum and maximum.
- When comparing an **interval to an interval,** Storm will return nodes whose interval has **any** overlap with the specified interval.

  - For example, a filter interval of September 1, 2018 to October 1, 2018 (``2018/09/01, 2018/10/01``) will match nodes with **any** of the following intervals:
  
    - August 12, 2018 to September 6, 2018 (``2018/08/12, 2018/09/06``).
    - September 13, 2018 to September 17, 2018 (``2018/09/13, 2018/09/17``).
    - September 30, 20180 to November 5, 2018 (``2018/09/30, 2018/11/05``).

- When comparing a **timestamp to an interval,** Storm will return nodes whose timestamp falls **within** the specified interval.
- When comparing an **interval to a timestamp,** Storm will return nodes whose interval **encompasses** the specified timestamp.
- When comparing a **timestamp to a timestamp,** interval ( ``@=`` ) syntax is supported, although the equals comparator ( ``=`` ) can simply be used.
- Because tags can be given timestamps (min / max interval values), interval filters can also be used with tags.


Filter by Range (\*range=)
++++++++++++++++++++++++++

The range extended comparator (``*range=``) supports filtering nodes whose *<form> = <valu>* or *<prop> = <pval>* fall within a specified range of values. The comparator can be used with types such as integers and times, including types that are extensions of those types, such as IP addresses.

**Syntax:**

*<query* **+** | **-** *<form>* | *<prop>* ***range = (** *<range_min>* **,** *<range_max>* **)**

**Examples:**

*Filter by primary property in range:*

- Downselect to include all IP addresses between 192.168.0.0 and 192.168.0.10:



.. parsed-literal::

    <query> +inet:ipv4*range=(192.168.0.0, 192.168.0.10)


*Filter by secondary property in range:*

- Downselect to include files whose size in bytes is within the specified range:


.. parsed-literal::

    <query> +file:bytes:size*range=(1000, 100000)



.. parsed-literal::

    <query> +:size*range=(1000, 100000)


- Downselect to include WHOIS records that were captured between the specified dates:


.. parsed-literal::

    <query> +inet:whois:rec:asof*range=(2013/11/29, 2016/06/14)



.. parsed-literal::

    <query> +:asof*range=(2013/11/29, 2016/06/14)


- Downselect to include DNS requests made within 1 day of 12/01/2018:


.. parsed-literal::

    <query> +inet:dns:request:time*range=(2018/12/01, "+-1 day")



.. parsed-literal::

    <query> +:time*range=(2018/12/01, "+-1 day")


**Usage Notes:**

- When specifying a range (``*range=``), both the minimum and maximum values are **included** in the range (the equivalent of “greater than or equal to *<min>* and less than or equal to *<max>*”). This behavior is slightly different than that for time interval (``@=``), which includes the minimum but not the maximum.
- The ``*range=`` extended comparator can be used with time types, although the time / interval extended comparator ( ``@=`` ) is preferred.

Filter by Set Membership (\*in=)
++++++++++++++++++++++++++++++++

The set membership extended comparator (``*in=``) supports filtering nodes whose *<form> = <valu>* or *<prop> = <pval>* matches any of a set of specified values. The comparator can be used with any type.

**Syntax:**

*<query>* **+** | **-** *<form>* | *<prop>* ***in = (** *<set_1>* **,** *<set_2>* **,** ... **)**

**Examples:**

*Filter by primary property in set:*

- Downselect to include IP addresses matching any of the specified values:



.. parsed-literal::

    cli> storm [inet:ipv4=127.0.0.1 inet:ipv4=192.168.0.100 inet:ipv4=255.255.255.254]
    
    inet:ipv4=127.0.0.1
            .created = 2019/03/13 23:55:31.698
            :asn = 0
            :loc = ??
            :type = loopback
    inet:ipv4=192.168.0.100
            .created = 2019/03/13 23:55:30.941
            :asn = 0
            :loc = ??
            :type = private
    inet:ipv4=255.255.255.254
            .created = 2019/03/13 23:55:31.701
            :asn = 0
            :loc = ??
            :type = private
    complete. 3 nodes in 13 ms (230/sec).



.. parsed-literal::

    <query> +inet:ipv4*in=(127.0.0.1, 192.168.0.100, 255.255.255.254)


*Filter by secondary property in set:*

- Downselect to include files whose size in bytes matches any of the specified values:


.. parsed-literal::

    <query> +file:bytes:size*in=(4096, 16384, 65536)



.. parsed-literal::

    <query> +:size*in=(4096, 16384, 65536)


- Downselect to exclude tags that end in ``foo``, ``bar``, or ``baz``:


.. parsed-literal::

    <query> -syn:tag:base*in=(foo, bar, baz)



.. parsed-literal::

    <query> -:base*in=(foo, bar, baz)


Filter by Proximity (\*near=)
+++++++++++++++++++++++++++++

The proximity extended comparator (``*near=``) supports filtering nodes by "nearness" to another node based on a specified property type. Currently, ``*near=`` supports proximity based on geospatial location (that is, nodes within a given radius of a specified latitude / longitude).

**Syntax:**

*<query>* **+** | **-** *<form>* | *<prop>* ***near = ((** *<lat>* **,** *<long>* **),** *<radius>* **)**

**Examples:**

*Filter by proximity:*

- Downselect to include only Foo Corporation offices within 1km of a specific coffee shop:



.. parsed-literal::

    <query> +geo:place:latlong*near=((47.6050632,-122.3339756),1km)



.. parsed-literal::

    <query> +:latlong*near=((47.6050632,-122.3339756),1km)


**Usage Notes:**

- In the example above, the latitude and longitude of the desired location (i.e., the coffee shop) are explicitly specified as parameters to ``*near=``.
- Radius can be specified in the following metric units. Values of less than 1 (e.g., 0.5km) must be specified with a leading zero:

  - Kilometers (km)
  - Meters (m)
  - Centimeters (cm)
  - Millimeters (mm)

- The ``*near=`` comparator works by identifying nodes within a square bounding box centered at *<lat>, <long>*, then filters the nodes to be returned by ensuring that they are within the great-circle distance given by the *<radius>* argument.

Filter by Tag (#)
+++++++++++++++++

The tag extended comparator (``#``) supports filtering nodes based on a given tag being applied to the node.

**Syntax:**

*<query>* **+** | **-** **#** *<tag>*

**Examples:**

- Downselect to include only nodes that FireEye says are part of the GREENCAT malware family:



.. parsed-literal::

    <query> +#aka.feye.mal.greencat


- Downselect to exclude nodes tagged as sinkholes:


.. parsed-literal::

    <query> -#cno.infra.sink.hole


**Usage Notes:**

- When filtering by tag, only a single tag can be specified. To filter on multiple tags, use `Compound Filters`_.


Compound Filters
----------------

Storm allows the use of the logical operators **and**, **or**, and **not** (including **and not**) to construct compound filters. Parentheses can be used to group portions of the filter statement to indicate order of precedence and clarify logical operations when evaluating the filter.

**Syntax:**

*<query>* **+** | **-** **(** *<filter>* **and** | **or** | **not** | **and not** ... **)**

**Examples:**

- Downselect to exclude files that are less than or equal to 16384 bytes in size and were compiled prior to January 1, 2014:



.. parsed-literal::

    <query> -(file:bytes:size <= 16384 and file:bytes:mime:pe:compiled < 2014/01/01)



.. parsed-literal::

    <query> -(:size <= 16384 and :mime:pe:compiled < 2014/01/01)


- Downselect to include only files or domains that FireEye claims are associated with APT1:


.. parsed-literal::

    <query> +((file:bytes or inet:fqdn) and #aka.feye.thr.apt1)


- Downselect to include only files and domains that FireEye claims are associated with APT1 that are **not** sinkholed:


.. parsed-literal::

    <query> +((file:bytes or inet:fqdn) and (#aka.feye.thr.apt1 and not #cno.infra.sink.hole))


**Usage Notes:**

- Logical operators must be specified in lower case.
- Parentheses should be used to logically group portions of the filter statement for clarity.

Subquery Filters
----------------

Storm's subquery syntax (:ref:`storm-ref-subquery`) can be used to create filters. A subquery (denoted by curly braces ( ``{ }`` ) ) can be placed anywhere within a larger Storm query.

When nodes are passed to a subquery filter:

- Nodes are **consumed** (i.e., are **not** returned by the subquery) if they evaluate **false.**
- Nodes are **not consumed** (i.e., are **returned** by the subquery) if they evaluate **true.**

In this way subqueries act as complex filters, allowing the formation of advanced queries that would otherwise require methods such as saving the results of an initial query off to the side while running a second query, then loading the results of the first query back to the results of the second query.

**Syntax:**

*<query>* **+** | **-** **{** *<query>* **}**

**Examples:**

- From an initial set of domains, return only those domains that resolve to an IP address that Trend Micro associates with the Pawn Storm threat group (i.e., an IP address tagged `#aka.trend.thr.pawnstorm`):



.. parsed-literal::

    <query> +{ -> inet:dns:a:fqdn :ipv4 -> inet:ipv4 +#aka.trend.thr.pawnstorm }


From an initial set of IP addresses, return only those IPs registered to an Autonomous System (AS) whois name starts with “makonix”:


.. parsed-literal::

    <query> +{ :asn -> inet:asn +:name^="makonix" }

