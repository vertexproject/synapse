.. highlight:: none


.. _storm-ref-lift:

Storm Reference - Lifting
=========================

Lift operations retrieve a set of nodes from a Synapse Cortex based on specified criteria. While all lift operations are retrieval operations, they can be broken down into “types” of lifts based on the criteria, comparison operator, or special handler used:

- `Simple Lifts`_
- `Try Lifts`_
- `Lifts Using Standard Comparison Operators`_
- `Lifts Using Extended Comparison Operators`_

See :ref:`storm-ref-syntax` for an explanation of the syntax format used below.

See :ref:`storm-ref-type-specific` for details on special syntax or handling for specific data types.

Simple Lifts
------------

"Simple" lifts refers to the most "basic" lift operations. That is, operations to retrieve a set of nodes based on:

- A specific primary, secondary, or universal property.
- A specific primary, secondary, or universal property value.
- A specific tag or tag property.

The only difference between "simple" lifts and "lifts using comparison operators" is that we have defined simple lifts as those that use the equals ( ``=`` ) comparator, which is the easiest comparator to use to explain basic lift concepts.

**Syntax:**

*<form>* [ **=** *<valu>* ]

*<form>* **=** *<valu>* **:** *<prop>* [ **=** *<pval>* ] 

**#** *<tag>* [ **:** *<tagprop>* [ *<operator>* *<pval>* ] ] 

**#:** *<tagprop>* [ *<operator>* *<pval>* ]

**Examples:**

*Lift by primary property (<form>):*

- Lift all domain nodes:


::

    storm> inet:fqdn



- Lift all mutex nodes:


::

    storm> it:dev:mutex



*Lift a specific node (<form> = <valu>):*

- Lift the node for the domain ``google.com``:

::

    storm> inet:fqdn = google.com



- Lift the node for a specific MD5 hash:


::

    storm> hash:md5 = d41d8cd98f00b204e9800998ecf8427e



*Lift a specific compound node:*

- Lift the DNS A record showing that domain ``woot.com`` resolved to IP ``1.2.3.4``:


::

    storm> inet:dns:a = (woot.com, 1.2.3.4)



*Lift a specific GUID node:*

- Lift the organization node with the specified GUID:


::

    storm> ou:org=2f92bc913918f6598bcf310972ebf32e



*Lift a specific digraph (edge) node:*

- Lift the ``edge:has`` node linking the person node representing "Bob Smith" to his email address:


::

    storm> edge:has=((ps:person,12af06294ddf1a0ac8d6da34e1dabee4),(inet:email, bob.smith@gmail.com))



*Lift by the presence of a secondary property (<prop>):*

- Lift the DNS SOA record nodes that have an email property:


::

    storm> inet:dns:soa:email



*Lift by a specific property value (<prop> = <pval>):*

- Lift the organization node with the alias ``vertex``:


::

    storm> ou:org:alias = vertex



- Lift all DNS A records for the domain ``blackcake.net``:


::

    storm> inet:dns:a:fqdn = blackcake.net



- Lift all the files with a PE compiled time of ``1992-06-19 22:22:17``:


::

    storm> file:bytes:mime:pe:compiled = "1992/06/19 22:22:17"



- Lift all the files with a PE compiled time that falls within the year 2019:


::

    storm> file:bytes:mime:pe:compiled=2019*


- Lift all nodes created during July 2023:

::

    storm> .created=202307*


*Lift all nodes with a specific tag:*

- Lift all nodes with the tag ``#cno.infra.anon.tor``:


::

    storm> #cno.infra.anon.tor



*Lift all nodes with a specific tag property:*

- Lift all nodes with a tag that has a ``:risk`` tag property:

*Lift all nodes with a specific tag and tag property:*

- Lift all nodes with a ``#rep.symantec`` tag that has a ``:risk`` tag property:

::

    storm> #rep.symantec:risk



*Lift all nodes with a specific tag, tag property, and value:*

- Lift all nodes with a ``#rep.symantec`` tag with a ``:risk`` tag property and a value greater than 10:


::

    storm> #rep.symantec:risk>10



**Usage Notes:**

- Lifting nodes by form alone (e.g., lifting all ``inet:fqdn`` nodes or all ``inet:email`` nodes) is possible but generally impractical / undesirable as it will potentially return an extremely large data set.
- Lifting by form alone when piped to the Storm :ref:`storm-limit` command may be useful for returning a small number of “exemplar” nodes.
- Lifting nodes by ``<form> = <valu>`` is the most common method of lifting a single node.
- When lifting a form whose ``<valu>`` consists of multiple components (e.g., a compound node or digraph node), the components must be passed as a comma-separated list enclosed in parentheses.
- Lifting nodes by the presence of a secondary property alone (``<prop>``) may be impractical / undesirable (similar to lifting by form alone), but may be feasible in limited cases (i.e., where it is known that only a relatively small number of nodes have a given secondary property).
- Lifting nodes by the value of a secondary property (``<prop> = <pval>``) is useful for lifting all nodes that share a secondary property with the same value; and may be used to lift individual nodes with unique or relatively unique secondary properties in cases where entering the primary property is impractical (such as for GUID nodes).
- When lifting nodes by secondary property value where the value is a time (date / time), you do not need to use full ``YYYY/MM/DD hh:mm:ss.mmm`` syntax. Synapse allows the use of both lower resolution values (e.g., ``YYYY/MM/DD``) and wildcard values (e.g., ``YYYY/MM*``). In particular, wildcard syntax can be used to specify any values that match the wildcard expression. See the type-specific documentation for :ref:`type-time` types for a detailed discussion of these behaviors.
- Lifting nodes by tag alone (``#<tag>``) lifts nodes of **all** forms with that tag. To lift specific forms only, use `Lift by Tag (#)`_ or an additional filter (see :ref:`storm-ref-filter`).
- Tag properties are supported in Synapse, but no tag properties are included by default. See :ref:`tag-properties` for additional detail.

Try Lifts
---------

Try lifts refer to lifts that "try" to perform a Cortex lift operation, and fail silently if :ref:`data-type` normalization is not successful. Try lifts prevent a Cortex from throwing a runtime execution error, and terminating query execution if an invalid Type is encountered.

When lifting nodes by property value using the equals (``=``) comparator, if Type validation fails for a supplied property value,  the Cortex will throw a ``BadTypeValu`` error, and terminate the query as shown below.



::

    storm> inet:ipv4 = evil.com inet:ipv4 = 8.8.8.8
    ERROR: illegal IP address string passed to inet_aton



To suppress errors, and prevent premature query termination, Storm supports the use of the try operator (``?=``) when performing property value lifts. This operator is useful when you are performing multiple Cortex operations in succession within a single query, lifting nodes using external data that has not been normalized, or lifting nodes during automation, and do not want a query to terminate if an invalid Type is encountered.


**Syntax:**

*<form>[:<prop>]* ?= *<pval>*

**Examples:**

- Try to lift the MD5 node ``174cc541c8d9e1accef73025293923a6``:

::

    storm> hash:md5 ?= 174cc541c8d9e1accef73025293923a6



- Try to lift the DNS nodes whose ``inet:dns:a:ipv4`` secondary property value equals ``'192.168.0.100'``. Notice that an error message is not displayed, despite an invalid IPv4 address ``'192.168.0.1000'`` being entered:

::

    storm> inet:dns:a:ipv4 ?= 192.168.0.1000



- Try to lift the email address nodes ``'jack@soso.net'`` and ``'jane@goodgirl.com'``. Notice that despite the first email address being entered incorrectly, the error message is suppressed, and the query executes to completion.

::

    storm> inet:email ?= "jack[at]soso.net" inet:email ?= "jane@goodgirl.com"
    inet:email=jane@goodgirl.com
            :fqdn = goodgirl.com
            :user = jane
            .created = 2023/10/05 21:47:30.209



**Usage Notes:**

- The try operator should be used when you want Storm query execution to continue even if an invalid Type is encountered. 
- It is not recommended to use the try operator when you want to raise an error, or stop query execution if an invalid Type is encountered.

Lifts Using Standard Comparison Operators
-----------------------------------------

Lift operations can be performed using most of the standard mathematical / logical comparison operators (comparators):

- ``=`` : equals (described above)
- ``<`` : less than
- ``>`` : greater than
- ``<=`` : less than or equal to
- ``>=`` : greater than or equal to

Lifting by “not equal to” (``!=``) is not supported.

**Syntax:**

*<prop>* *<comparator>* *<pval>*

**Examples:**

*Lift using less than comparator:*

- Lift domain WHOIS records where the domain's registration (created) date was before June 1, 2014:


::

    storm> inet:whois:rec:created < 2014/06/01



*Lift using greater than comparator:*

- Lift files whose size is larger than 1MB:


::

    storm> file:bytes:size > 1048576



*Lift using less than or equal to comparator:*

- Lift people (person nodes) born on or before January 1, 1980:


::

    storm> ps:person:dob <= 1980/01/01


- Lift files that were compiled in 2012 or earlier:

::

    storm> file:bytes:mime:pe:compiled<=2012*


*Lift using greater than or equal to comparator:*

- Lift WHOIS records retrieved on or after December 1, 2018 at 12:00:


::

    storm> inet:whois:rec:asof >= "2018/12/01 12:00"


**Usage Notes:**

- When lifting nodes by secondary property value where the value is a time (date / time), you do not need to use full ``YYYY/MM/DD hh:mm:ss.mmm`` syntax. Synapse allows the use of both lower resolution values (e.g., ``YYYY/MM/DD``) and wildcard values (e.g., ``YYYY/MM*``). In particular, wildcard syntax can be used to specify any values that match the wildcard expression. See the type-specific documentation for :ref:`type-time` types for a detailed discussion of these behaviors.


Lifts Using Extended Comparison Operators
-----------------------------------------

Storm supports a set of extended comparison operators (comparators) for specialized lift operations. In most cases, the same extended comparators are available for both lifting and filtering:

- `Lift by Regular Expression (~=)`_
- `Lift by Prefix (^=)`_
- `Lift by Time or Interval (@=)`_
- `Lift by Range (*range=)`_
- `Lift by Set Membership (*in=)`_
- `Lift by Proximity (*near=)`_
- `Lift by (Arrays) (*[ ])`_
- `Lift by Tag (#)`_
- `Recursive Tag Lift (##)`_


.. _lift-regex:

Lift by Regular Expression (~=)
+++++++++++++++++++++++++++++++

The extended comparator ``~=`` is used to lift nodes based on standard regular expressions.

.. NOTE::
  `Lift by Prefix (^=)`_ is supported for string types and can be used to match the beginning of string properties.

**Syntax:**

*<form>* [ **:** *<prop>* ] **~=** *<regex>*

**Example:**

- Lift files with PDB paths containing the string ``rouji``:


::

    storm> file:bytes:mime:pe:pdbpath ~= "rouji"



.. _lift-prefix:

Lift by Prefix (^=)
+++++++++++++++++++

Synapse performs prefix indexing on string types, which optimizes lifting nodes whose *<valu>* or *<pval>* starts with a given prefix. The extended comparator ``^=`` is used to lift nodes by prefix.

**Syntax:**

*<form>* [  **:** *<prop>* ] **^=** *<prefix>*

**Examples:**

*Lift primary property by prefix:*

- Lift all usernames that start with "pinky":


::

    storm> inet:user^=pinky



*Lift secondary property by prefix:*

- Lift all organizations whose name starts with "International":


::

    storm> ou:org:name^=international



**Usage Notes:**

- Extended string types that support dotted notation (such as the :ref:`type-loc` or :ref:`type-syn-tag` types) have custom behaviors with respect to lifting and filtering by prefix. See the respective sections in :ref:`storm-ref-type-specific` for additional details.

.. _lift-interval:

Lift by Time or Interval (@=)
+++++++++++++++++++++++++++++

Synapse supports numerous data forms whose properties are date / time values (*<ptype>* = *<time>*) or time windows / intervals (*<ptype>* = *<ival>*). Storm supports the custom ``@=`` comparator to allow lifting based on comparisons among various combinations of times and intervals.

See :ref:`storm-ref-type-specific` for additional detail on the use of :ref:`type-time` and :ref:`type-ival` data types.

**Syntax:**

*<prop>* **@=(** *<ival_min>* **,** *<ival_max>* **)**

*<prop>* **@=** *<time>*

**Examples:**

*Lift by comparing an interval to an interval:*

- Lift all DNS A records whose ``.seen`` values fall between July 1, 2018 and August 1, 2018:


::

    storm> inet:dns:a.seen@=(2018/07/01, 2018/08/01)



*Lift by comparing a time to an interval:*

- Lift DNS requests that occurred on May 3, 2018 (between 05/03/2018 00:00:00 and 05/03/2018 23:59:59):


::

    storm> inet:dns:request:time@=("2018/05/03 00:00:00", "2018/05/04 00:00:00")



*Lift by comparing a time to a time:*

- Lift all WHOIS records that were retrieved on July 17, 2017:


::

    storm> inet:whois:rec:asof@=2017/07/17



*Lift using an interval with relative times:*

- Lift the WHOIS email nodes that were observed between January 1, 2019 and the present:


::

    storm> inet:whois:email.seen@=(2019/01/01, now)



- Lift the DNS requests that occurred within one day after October 15, 2018:


::

    storm> inet:dns:request:time@=(2018/10/15,"+1 day")



*Lift by comparing tag time intervals:*

- Lift all the domain nodes that were associated with Threat Group 43 between January 2013 and January 2015:


::

    storm> inet:fqdn#cno.threat.t43.tc@=(2013/01/01, 2015/01/01)



**Usage Notes:**

- When specifying an interval, the minimum value is included in the interval but the maximum value is **not** (the equivalent of “greater than or equal to *<min>* and less than *<max>*”). This behavior is slightly different than that for ``*range=``, which includes **both** the minimum and maximum.
- When comparing an **interval to an interval,** Storm will return nodes whose interval has **any** overlap with the specified interval.

  - For example, a lift interval of September 1, 2018 to October 1, 2018 (2018/09/01, 2018/10/01) will match nodes with any of the following intervals:
  
    - August 12, 2018 to September 6, 2018.
    - September 13, 2018 to September 17, 2018.
    - September 30, 2018 to November 5, 2018.

- When comparing a **time to an interval,** Storm will return nodes whose time falls **within** the specified interval.
- When comparing a **time to a time,** Storm will return nodes whose timestamp is an **exact match.** (Interval ( ``@=`` ) syntax is supported for this comparison, but the regular equals comparator ( ``=`` ) can also be used.)
- When specifying interval date/time values, Synapse allows the use of both lower resolution values (e.g., ``YYYY/MM/DD``) and wildcard values (e.g., ``YYYY/MM*``) for the minimum and/or maximum interval values. In addition, plain wildcard time syntax may provide a simpler and more intuitive means to specify some intervals. For example ``inet:whois:rec:asof=2018*`` is equivalent to ``inet:whois:rec:asof@=('2018/01/01', '2019/01/01')``.  See the type-specific documentation for :ref:`type-time` types for a detailed discussion of these behaviors.


.. _lift-range:

Lift by Range (\*range=)
++++++++++++++++++++++++

The range extended comparator (``*range=``) supports lifting nodes whose *<form>* = *<valu>* or *<prop>* = *<pval>* fall within a specified range of values. The comparator can be used with types such as integers and times (including types that are extensions of those types, such as IP addresses).

**Syntax:**

*<form>* [ **:** *<prop>* ] ***range = (** *<range_min>* **,** *<range_max>* **)**

**Examples:**

*Lift by primary property in range:*

- Lift all IP addresses between 192.168.0.0 and 192.168.0.10:


::

    storm> inet:ipv4*range=(192.168.0.0, 192.168.0.10)



*Lift by secondary property in range:*

- Lift files whose size is between 1000 and 100000 bytes:


::

    storm> file:bytes:size*range=(1000,100000)



- Lift WHOIS records that were captured between November 29, 2013 and June 14, 2016:


::

    storm> inet:whois:rec:asof*range=(2013/11/29, 2016/06/14)



- Lift DNS requests made within one day of 12/01/2018:


::

    storm> inet:dns:request:time*range=(2018/12/01, "+-1 day")



**Usage Notes:**

- When specifying a range, both the minimum and maximum values are included in the range (the equivalent of "greater than or equal to *<min>* and less than or equal to *<max>*").
- When specifying a range of time values, Synapse allows the use of both lower resolution values (e.g., ``YYYY/MM/DD``) and wildcard values (e.g., ``YYYY/MM*``) for the minimum and/or maximum range values. In addition, plain wildcard time syntax may provide a simpler and more intuitive means to specify some time ranges. For example ``inet:whois:rec:asof=2018*`` is equivalent to ``inet:whois:rec:asof*range=('2018/01/01', '2018/12/31 23:59:59.999')``.  See the type-specific documentation for :ref:`type-time` types for a detailed discussion of these behaviors.

.. _lift-set:

Lift by Set Membership (\*in=)
++++++++++++++++++++++++++++++

The set membership extended comparator (``*in=``) supports lifting nodes whose *<form> = <valu>* or *<prop> = <pval>* matches any of a set of specified values. The comparator can be used with any type.

**Syntax:**

*<form>* [ **:** *<prop>* ] ***in = (** *<set_1>* **,** *<set_2>* **,** ... **)**

**Examples:**

*Lift by primary property in a set:*

- Lift IP addresses matching any of the specified values:


::

    storm> inet:ipv4*in=(127.0.0.1, 192.168.0.100, 255.255.255.254)



*Lift by secondary property in a set:*

- Lift files whose size in bytes matches any of the specified values:


::

    storm> file:bytes:size*in=(4096, 16384, 65536)



- Lift tags that end in ``foo``, ``bar``, or ``baz``:


::

    storm> syn:tag:base*in=(foo,bar,baz)



.. _lift-proximity:

Lift by Proximity (\*near=)
+++++++++++++++++++++++++++

The proximity extended comparator (``*near=``) supports lifting nodes by "nearness" to another node based on a specified property type. Currently, ``*near=`` supports proximity based on geospatial location (that is, nodes within a given radius of a specified latitude / longitude).

**Syntax:**

*<form>* [ **:** *<prop>* ] ***near = ((** *<lat>* **,** *<long>* **),** *<radius>* **)**

**Examples:**

- Lift locations (``geo:place`` nodes) within 500 meters of the Eiffel Tower:


::

    storm> geo:place:latlong*near=((48.8583701,2.2944813),500m)



**Usage Notes:**

- In the example above, the latitude and longitude of the desired location (i.e., the Eiffel Tower) are explicitly specified as parameters to ``*near=``.
- Radius can be specified in the following metric units:
  
  - Kilometers (km)
  - Meters (m)
  - Centimeters (cm)
  - Millimeters (mm)

- Numeric values of less than 1 (e.g., 0.5km) must be specified with a leading zero.
- The ``*near=`` comparator works for geospatial data by lifting nodes within a square bounding box centered at *<lat>,<long>*, then filters the nodes to be returned by ensuring that they are within the great-circle distance given by the *<radius>* argument.

.. _lift-by-arrays:

Lift by (Arrays) (\*[ ])
++++++++++++++++++++++++

Storm uses a special "by" syntax to lift (or filter) by comparison with one or more elements of an :ref:`type-array` type. The syntax consists of an asterisk ( ``*`` ) preceding a set of square brackets ( ``[ ]`` ), where the square brackets contain a comparison operator and a value that can match one or more elements in the array. This allows users to match values in the array list without needing to know the exact order or values of the array itself.

**Syntax:**

*<form>* **:** *<prop>* **[** *<operator>* *<pval>* **]**

**Examples:**

- Lift the organization(s) (``ou:org`` nodes) whose names include "IBM":


::

    storm> ou:org:names*[=ibm]



- Lift the x509 certificates (``crypto:x509:cert``) that reference domains ending with ``.biz``:


::

    storm> crypto:x509:cert:identities:fqdns*[="*.biz"]



- Lift the organizations whose names start with "tech":


::

    storm> ou:org:names*[^=tech]



**Usage Notes:**

- The comparison operator used must be valid for lift operations for the type used in the array. For example, :ref:`type-inet-fqdn` suffix matching (i.e., ``crypto:x509:cert:identities:fqdns*[="*.com"]``), can be used to lift arrays consisting of domains, but the prefix operator (``^=``), which is only valid when **filtering** ``inet:fqdns``, cannot.
- The standard equals ( ``=`` ) operator can be used to filter nodes based on array properties, but the value specified must **exactly match** the **full** property value in question:

  - For example: ``ou:org:names=("the vertex project","the vertex project llc",vertex)``

- See the :ref:`type-array` section of the :ref:`storm-ref-type-specific` document for additional details.

.. _lift-tag:

Lift by Tag (#)
+++++++++++++++

The tag extended comparator (``#``) supports lifting nodes based on a form combined with a given tag; tag and tag property; tag, tag property, and tag property value; or tag and associated timestamp being applied to the node.

.. NOTE::
  Lifting by form and tag (``<form>#<tag>``), including similar lifts using tag properties / timestamps / etc., is actually a Synapse-optimized "lift and filter" operation as opposed to a standard lift. The operation is equivalent to `<form> +#<tag>` except that the lift by tag syntax is optimized for performance.
  
    - Using the explicit filter (`<form> +#<tag>`) lifts **all** nodes of the specified form and **then** downselects to only those forms with the specified tag.
    - Storm optimizes the lift by tag syntax to lift **only** those nodes of the specified form that have the specified tag.
    
  See :ref:`filter-tag` for additional detail on filtering with tags.

**Syntax:**

*<form>* **#** *<tag>*

*<form>* **#** *<tag>* [ **:** *<tagprop>* [ *<operator>* *<pval>* ] ]

*<form>* **#** *<tag>* **@=** *<time>* | **(** *<min_time>* **,** *<max_time>* **)**

**Examples:**

*Lift forms by tag:*

- Lift the IPv4 addresses associated with Tor infrastructure:


::

    storm> inet:ipv4#cno.infra.anon.tor



*Lift forms by tag and tag property:*

- Lift the domains that have a risk score reported by DomainTools:


::

    storm> inet:fqdn#rep.domaintools:risk



*Lift forms by tag, tag property, and value:*

- Lift the domains that have a risk score from DomainTools of 90 or higher:


::

    storm> inet:fqdn#rep.domaintools:risk>=90



*Lift forms by tag and time:*

- Lift domains that were associated with Threat Cluster 15 as of October 30, 2009:


::

    storm> inet:fqdn#cno.threat.t15.tc@=2009/10/30



*Lift forms by tag and time interval:*

- Lift IP addresses that were part of Tor infrastructure between October 1, 2018 and December 31, 2018:


::

    storm> inet:ipv4#cno.infra.anon.tor@=(2018/10/01,2018/12/31)



**Usage Notes:**

- Tag properties are supported in Synapse, but no tag properties are included by default. See :ref:`tag-properties` for additional detail.
- Currently it is not possible to lift forms by tag property alone. That is, ``inet:fqdn#:risk`` is invalid.

  - It is possible to perform an equivalent operation using a lift and filter operation, i.e., ``#:risk +inet:fqdn``.

- Tag timestamps are interval (``ival``) types. See the :ref:`type-time` and :ref:`type-ival` sections of the :ref:`storm-ref-type-specific` document for additional details on working with times and intervals.

.. _lift-tag-recursive:

Recursive Tag Lift (##)
+++++++++++++++++++++++

The recursive tag extended comparator (##) supports lifting nodes with any tag whose ``syn:tag`` node is itself tagged with a specific tag.

Tags can be applied to ``syn:tag`` nodes; that is, tags can be used to tag other tags. The ability to "tag the tags" can be used to represent certain types of analytical relationships. For example:

- ``syn:tag`` nodes representing threat groups can be tagged to indicate their assessed country of origin.
- ``syn:tag`` nodes representing malware or tools can be tagged with their assessed availability (e.g., public, private, private but shared, etc.)

A recursive tag lift performs the following actions:

1. For the specified tag (``##<sometag>``), lift the nodes that have that tag (i.e., the equivalent of ``#<sometag>``), including any ``syn:tag`` nodes.
2. For any lifted ``syn:tag`` nodes, lift all nodes tagged with those tags (including any additional ``syn:tag`` nodes).
3. Repeat #2 until no more ``syn:tag`` nodes are lifted.
4. Return the tagged nodes. Note that ``syn:tag`` nodes themselves are **not** returned.

**Syntax:**

**##** *<tag>*

**Examples:**

- Lift all nodes tagged with any tags (such as threat group tags) that FireEye claims are associated with Russia:


::

    storm> ##aka.feye.cc.ru



**Usage Notes:**

In the example above, the tag ``aka.feye.cc.ru`` could be applied to ``syn:tag`` nodes representing FireEye’s “Russian” threat groups (e.g., ``aka.feye.thr.apt28``, ``aka.feye.thr.apt29``, etc.) Using a recursive tag lift allows you to easily lift all nodes tagged by **any** of those tags.
