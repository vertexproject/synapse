



.. highlight:: none

.. _storm-ref-lift:

Storm Reference - Lifting
=========================

Lift operations retrieve a set of nodes from a Synapse Cortex based on specified criteria. While all lift operations are retrieval operations, they can be broken down into “types” of lifts based on the criteria, comparison operator, or special handler used:

- `Simple Lifts`_
- `Lifts Using Standard Comparison Operators`_
- `Lifts Using Extended Comparison Operators`_

See :ref:`storm-ref-syntax` for an explanation of the syntax format used below.

See :ref:`storm-ref-type-specific` for details on special syntax or handling for specific data types.

Simple Lifts
------------

"Simple" lifts refers to the most "basic" lift operations. That is, operations to retrieve a set of nodes based on:

- The presence of a specific primary or secondary property.
- The presence of a specific primary property value or secondary property value.
- The presence of a specific tag.

The only difference between "simple" lifts and "lifts using comparison operators" is that we have defined simple lifts as those that use the equals ( ``=`` ) comparator, which is the easiest comparator to use to explain basic lift concepts.

**Syntax:**

*<form>* | *<form>* **=** *<valu>* | *<valu>* | *<prop>* | *<prop>* **=** *<pval>* | **#** *<tag>*

**Examples:**

*Lift by primary property (<form>):*

- Lift all domain nodes:


.. parsed-literal::

    inet:fqdn



- Lift all mutex nodes:


.. parsed-literal::

    it:dev:mutex



*Lift a specific node (<form> = <valu>):*

- Lift the node for the domain ``google.com``:


.. parsed-literal::

    inet:fqdn = google.com



- Lift the node for a specific MD5 hash:


.. parsed-literal::

    hash:md5 = d41d8cd98f00b204e9800998ecf8427e



*Lift a specific compound node:*

- Lift the DNS A record showing that domain ``woot.com`` resolved to IP ``1.2.3.4``:


.. parsed-literal::

    inet:dns:a = (woot.com, 1.2.3.4)



*Lift a specific GUID node:*

* Lift the organization node with the specified GUID:


.. parsed-literal::

    ou:org=2f92bc913918f6598bcf310972ebf32e



*Lift a specific digraph (edge) node:*

- Lift the ``has`` node linking the person node representing "Bob Smith" to his email address:


.. parsed-literal::

    has=((ps:person,12af06294ddf1a0ac8d6da34e1dabee4),(inet:email, bob.smith@gmail.com))



*Lift by the presence of a secondaray property (<prop>):*

- Lift the DNS SOA record nodes that have an email property:


.. parsed-literal::

    inet:dns:soa:email



*Lift by a specific property value (<prop> = <pval>):*

- Lift the organization node with the alias ``vertex``:


.. parsed-literal::

    ou:org:alias = vertex



- Lift all DNS A records for the domain ``blackcake.net``:


.. parsed-literal::

    inet:dns:a:fqdn = blackcake.net



- Lift all the files with a PE compiled time of ``1992-06-19 22:22:17``:


.. parsed-literal::

    file:bytes:mime:pe:compiled = "1992/06/19 22:22:17"



*Lift all nodes with a specific tag:*


.. parsed-literal::

    #cno.infra.anon.tor


**Usage Notes:**

- Lifting nodes by form alone (e.g., lifting all ``inet:fqdn`` nodes or all ``inet:email`` nodes) is possible but generally impractical / undesirable as it will potentially return an extremely large data set.
- Because of the risk of accidentally lifting all nodes of a given form, the Storm query planner will automatically optimize lifts that:
  
  - specify a form with no value (e.g., attempt to lift by form alone); and
  - are immediately followed by a positive tag filter (``+#sometag``).
  
  - For example, the following queries are executed in the same manner by the Storm runtime:
    
    - Lift followed by tag filter: ``inet:fqdn +#hehe.haha``
    - Lift by tag (described below): ``inet:fqdn#hehe.haha``

- Lifting by form alone when piped to the Storm :ref:`storm-limit` command may be useful for returning a small number of “exemplar” nodes.
- Lifting nodes by ``<form> = <valu>`` is the most common method of lifting a single node.
- When lifting a form whose ``<valu>`` consists of multiple components (e.g., a compound node or digraph node), the components must be passed as a comma-separated list enclosed in parentheses.
- Lifting nodes by the presence of a secondary property alone (``<prop>``) may be impractical / undesirable (similar to lifting by form alone), but may be feasible in limited cases (i.e., where it is known that only a relatively small number of nodes have a given secondary property).
- Lifting nodes by the value of a secondary property (``<prop> = <pval>``) is useful for lifting all nodes that share a secondary property with the same value; and may be used to lift individual nodes with unique or relatively unique secondary properties in cases where entering the primary property is impractical (such as for GUID nodes).
- Lifting nodes by tag alone (``#<tag>``) lifts nodes of **all** forms with that tag. To lift specific forms only, use `Lift by Tag (#)`_ or an additional filter (see :ref:`storm-ref-filter`).

Lifts Using Standard Comparison Operators
-----------------------------------------

Lift operations can be performed using most of the standard mathematical / logical comparison operators (comparators), as well as lifting via regular expression:

- ``=`` : equals (described above)
- ``<`` : less than
- ``>`` : greater than
- ``<=`` : less than or equal to
- ``>=`` : greater than or equal to

Lifting by “not equal to” (``!=``) is not currently supported.

**Syntax:**

*<prop>* *<comparator>* *<pval>*

**Examples:**

*Lift using less than comparator:*

- Lift domain WHOIS records where the domain's registration (created) date was before June 1, 2014:


.. parsed-literal::

    inet:whois:rec:created < 2014/06/01



*Lift using greater than comparator:*

- Lift files whose size is larger than 1MB:


.. parsed-literal::

    file:bytes:size > 1048576



*Lift using less than or equal to comparator:*

- Lift people (person nodes) born on or before January 1, 1980:


.. parsed-literal::

    ps:person:dob <= 1980/01/01



*Lift using greater than or equal to comparator:*

- Lift WHOIS records retrieved on or after December 1, 2018 at 12:00:


.. parsed-literal::

    inet:whois:rec:asof >= "2018/12/01 12:00"


Lifts Using Extended Comparison Operators
-----------------------------------------

Storm supports a set of extended comparison operators (comparators) for specialized lift operations. In most cases, the same extended comparators are available for both lifting and filtering:

- `Lift by Regular Expression (~=)`_
- `Lift by Prefix (^=)`_
- `Lift by Range (*range=)`_
- `Lift by Set Membership (*in=)`_
- `Lift by Proximity (*near=)`_
- `Lift by Tag (#)`_
- `Recursive Tag Lift (##)`_


Lift by Regular Expression (~=)
+++++++++++++++++++++++++++++++

The extended comparator ``~=`` is used to lift nodes based on standard regular expressions.

.. WARNING::
  While lifting using regular expressions is possible, matching is performed via brute force comparison of the relevant properties. Lifting by regex may thus be time consuming when lifting over large data sets. `Lift by Prefix (^=)`_ is supported for string types and should be considered as a more efficient alternative when possible.

**Syntax:**

*<prop>* **~=** *<regex>*

**Example:**

- Lift files with PDB paths containing the string ``rouji``:


.. parsed-literal::

    file:bytes:mime:pe:pdbpath ~= "rouji"


Lift by Prefix (^=)
+++++++++++++++++++

Synapse performs prefix indexing on string types, which optimizes lifting nodes whose *<valu>* or *<pval>* starts with a given prefix. This improves performance by avoiding regex brute-forcing.  The extended comparator ``^=`` is used to lift nodes by prefix.

**Syntax:**

*<form>* [  **:** *<prop>* ] **^=** *<prefix>*

**Examples:**

*Lift primary property by prefix:*

- Lift all usernames that start with "pinky":



.. parsed-literal::

    inet:user^=pinky


*Lift secondary property by prefix:*

- Lift all organizations whose name starts with "International":



.. parsed-literal::

    ou:org:name^=international


**Usage Notes:**

- Extended string types that support dotted notation (such as the ``loc`` or ``syn:tag`` types) have custom behaviors with respect to lifting and filtering by prefix. See the respective sections in :ref:`storm-ref-type-specific` for additional details.

Lift by Range (\*range=)
++++++++++++++++++++++++

The range extended comparator (``*range=``) supports lifting nodes whose *<form>* = *<valu>* or *<prop>* = *<pval>* fall within a specified range of values. The comparator can be used with types such as integers and times (including types that are extensions of those types, such as IP addresses).

**Syntax:**

*<form>* [ **:** *<prop>* ] ***range = (** *<range_min>* **,** *<range_max>* **)**

**Examples:**

*Lift by primary property in range:*

- Lift all IP addresses between 192.168.0.0 and 192.168.0.10:



.. parsed-literal::

    inet:ipv4*range=(192.168.0.0, 192.168.0.10)


*Lift by secondary property in range:*

- Lift files whose size is between 1000 and 100000 bytes:



.. parsed-literal::

    file:bytes:size*range=(1000,100000)


- Lift WHOIS records that were captured between November 29, 2013 and June 14, 2016:



.. parsed-literal::

    inet:whois:rec:asof*range=(2013/11/29, 2016/06/14)


- Lift DNS requests made within one day of 12/01/2018:


.. parsed-literal::

    inet:dns:request:time*range=(2018/12/01, "+-1 day")


**Usage Notes:**

- When specifying a range, both the minimum and maximum values are included in the range (the equivalent of "greater than or equal to *<min>* and less than or equal to *<max>*").

Lift by Set Membership (\*in=)
++++++++++++++++++++++++++++++

The set membership extended comparator (``*in=``) supports lifting nodes whose *<form> = <valu>* or *<prop> = <pval>* matches any of a set of specified values. The comparator can be used with any type.

**Syntax:**

*<form>* [ **:** *<prop>* ] ***in = (** *<set_1>* **,** *<set_2>* **,** ... **)**

**Examples:**

*Lift by primary property in a set:*

- Lift IP addresses matching any of the specified values:



.. parsed-literal::

    inet:ipv4*in=(127.0.0.1, 192.168.0.100, 255.255.255.254)


*Lift by secondary property in a set:*

- Lift files whose size in bytes matches any of the specified values:



.. parsed-literal::

    file:bytes:size*in=(4096, 16384, 65536)


- Lift tags that end in ``foo``, ``bar``, or ``baz``:



.. parsed-literal::

    syn:tag:base*in=(foo,bar,baz)


Lift by Proximity (\*near=)
+++++++++++++++++++++++++++

The proximity extended comparator (``*near=``) supports lifting nodes by "nearness" to another node based on a specified property type. Currently, ``*near=`` supports proximity based on geospatial location (that is, nodes within a given radius of a specified latitude / longitude).

**Syntax:**

*<form>* [ **:** *<prop>* ] ***near = ((** *<lat>* **,** *<long>* **),** *<radius>* **)**

**Examples:**

- Lift locations (``geo:place`` nodes) within 500 meters of the Eiffel Tower:



.. parsed-literal::

    geo:place:latlong*near=((48.8583701,2.2944813),500m)


**Usage Notes:**

- In the example above, the latitude and longitude of the desired location (i.e., the Eiffel Tower) are explicitly specified as parameters to ``*near=``.
- Radius can be specified in the following metric units. Values of less than 1 (e.g., 0.5km) must be specified with a leading zero:
  
  - Kilometers (km)
  - Meters (m)
  - Centimeters (cm)
  - Millimeters (mm)

- The ``*near=`` comparator works for geospatial data by lifting nodes within a square bounding box centered at *<lat>,<long>*, then filters the nodes to be returned by ensuring that they are within the great-circle distance given by the *<radius>* argument.


.. _lift-tag:

Lift by Tag (#)
+++++++++++++++

The tag extended comparator (``#``) supports lifting nodes based on a given tag being applied to the node.

**Syntax:**

[ *<form>* ] **#** *<tag>*

**Examples:**

*Lift all nodes associated with Tor infrastructure:*



.. parsed-literal::

    #cno.infra.anon.tor


- Lift the domains that Palo Alto Networks says are associated with the OilRig threat group:



.. parsed-literal::

    inet:fqdn#aka.paloalto.thr.oilrig


Recursive Tag Lift (##)
+++++++++++++++++++++++

The recursive tag extended comparator (``##``) supports lifting nodes tagged with any tag that is itself tagged with a given tag.

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



.. parsed-literal::

    ##aka.feye.cc.ru


**Usage Notes:**

In the example above, the tag ``aka.feye.cc.ru`` could be applied to ``syn:tag`` nodes representing FireEye’s “Russian” threat groups (e.g., ``aka.feye.thr.apt28``, ``aka.feye.thr.apt29``, etc.) Using a recursive tag lift allows you to easily lift all nodes tagged by **any** of those tags.

