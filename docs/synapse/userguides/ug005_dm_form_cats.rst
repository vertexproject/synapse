
Data Model - Form Categories
============================

Recall that within the Synapse data model:

  * **Nodes** commonly represent “things”: objects, facts, or observables.
  * **Tags** commonly represent “assessments”: judgements or evaluations that may change given new data or revised analysis.

Within Synapse, forms are the building blocks for any analysis system. Forms are those objects relevant to a given knowledge domain that will be used to represent that knowledge and answer analytical questions about the captured information. As such, the proper design of forms is essential.

In a hypergraph - where there are no edges, and thus everything is a node - forms take on additional significance. Specifically, forms must be used to represent more than just “nouns”. Broadly speaking, forms must be used to capture three general categories of “things”: objects, relationships, and events.

  * `Forms as Objects`_
  * `Forms as Relationships`_
  * `Forms as Events`_
  * `Instance Knowledge vs. Fused Knowledge`_

Forms as Objects
----------------

Forms can represent atomic objects, whether real or abstract. In the knowledge domain of cyber threat data, object-type forms include domains, IP addresses (IPv4 or IPv6), hosts (computers / devices), usernames, passwords, accounts, files, social media posts, and so on. Other object types include people, organizations, countries, bank or financial accounts, units of currency, chemical elements or formulas, telephone numbers, airline flights, and so on. Any object can be defined by a form and represented by a node. Object-type forms are often represented as **simple forms.**

**Example**

An email address (``inet:email``) is a basic example of an object-type node / simple form:

::

  inet:email = kilkys@yandex.ru
          .created = 2018/05/17 21:15:52.766
          :fqdn = yandex.ru
          :user = kilkys

Forms as Relationships
----------------------

Forms can represent specific relationships among objects. Recall that in a directed graph a relationship is represented as a directed edge joining exactly two nodes; but in a hypergraph the entire relationship is represented by a single node (form), and the relationship can encompass any number of objects – not just two.

For cyber threat data, relationships include a domain resolving to an IP address, a malware binary writing a file to disk, or a threat actor moving laterally between two hosts. Other types of relationships include a company being a subsidiary of another business, an employee working for a company, or a person being a member of a group.

As an example of a “multi-dimensional” relationship, biological parentage could be represented by a three-way relationship among two genetic parents and an offspring.

Relationship-type forms are often represented as **composite (comp) forms.**

**Example**

A DNS A record (``inet:dns:a``) is a basic example of a relationship-type node / comp form:

::

  inet:dns:a = ('code4app.com', '127.0.0.1')
          .created = 2018/06/05 08:40:32.595
          :fqdn = code4app.com
          :ipv4 = 127.0.0.1

Forms as Events
---------------

Forms can represent individual time-based occurrences. The term “event” implies that an object existed or a relationship occurred at a specific point in time. As such events explicitly represent the intersection of the data represented by a form and a timestamp for the form’s existence or observation.

Examples of event-type forms include an individual login to an account, the response to a specific DNS query, the high temperature reading in a city on a particular day, or a domain registration (“whois”) record captured on a specific date.

Event-type forms are often represented as **GUID forms.**

**Example**

An ``inet:dns:answer``, which represents a specific response received for a given DNS query, is an example of an event-type form:

::

  inet:dns:answer = ('b91bcb3535abb81d46072b49a0e892ab')
          .created = 2017/11/08 17:10:34.570
          :a = ('ping3.teamviewer.com', '162.220.223.28')
          :request = ('006202fbd2dc379d88ca669910928efe')
          :time = 2017/09/15 05:37:23.000

Instance Knowledge vs. Fused Knowledge
--------------------------------------

For certain types of data, event forms and relationship forms can encode similar information but represent the difference between **instance knowledge** and **fused knowledge.**

Event forms represent the specific point-in-time existence of an object or occurrence of a relationship - an **instance** of that knowledge. Relationship forms can leverage the universal ``.seen`` property to set “first observed” and “last observed” times during which an object existed or a relationship was true. This date range can be viewed as **fused** knowledge - knowledge that summarizes or “fuses” the data from any number of instance knowledge nodes over time.

Instance knowledge and fused knowledge represent differences in data granularity. Whether to create an event form or a relationship form depends on how much detail is required for a given analytical purpose. This consideration often applies to relationships that change over time, particularly those that may change frequently.

**Example**

DNS A records are a good example of these differences. The IP address that a domain resolves to may change infrequently (e.g., for a website hosted on a stable server) or may change quite often (e.g., where the IP is dynamically assigned or where load balancing is used). 

One option to represent and track DNS A records would be to create individual timestamped forms (events) every time you check the domain’s current resolution (e.g., ``inet:dns:request`` and ``inet:dns:answer`` forms). This represents a very high degree of granularity as the nodes will record the exact time a domain resolved to a given IP, potentially down to the millisecond. However, the number of such nodes could readily reach into the hundreds of millions, if not billions, if you create nodes for every resolution of every domain you want to track.

An alternative would be to decide that it is sufficient to know that a domain resolved to an IP address during a given period of time – a “first observed” and “last observed” (``.seen``) range. A single ``inet:dns:a`` node can be created to show that domain woot.com resolved to IP address 1.2.3.4, where the earliest observed resolution was 8/6/2011 at 13:56 and the most recently observed resolution was 5/29/2016 at 7:32. These timestamps can be extended (earlier or later) if additional data changes our observation boundaries.

This second approach loses some granularity:

  * The domain is not guaranteed to have resolved to that IP consistently throughout the entire time period.
  * Given only this node, we don’t know exactly when it the domain resolved there during that time period. 

However, this fused knowledge may be sufficient for our needs and may be preferable to creating thousands of nodes for individual DNS resolutions. 

Of course, a hybrid approach is also possible, where most DNS A record data is recorded in fused ``inet:dns:a`` nodes but it is also possible to record high-resolution, point-in-time ``inet:dns:answer`` nodes when needed.

Additional examples include:

  * **Malware behavior.** In some circumstances, it may be enough to know that when a malware binary is executed, it drops (writes) a specific file (a set of bytes with a specific hash) to disk; this would represent relationship-type “fused knowledge” (e.g., “file1 writes file2”). In other circumstances, it may be important to know not only what file was dropped, but also the specific filename and directory path used, or the specific configuration of the computer or sandbox where the malware executed; this would represent specific event-based “instance knowledge”.

  * **Environmental observations** (temperature, humidity, barometric pressure, etc.). It may be sufficient to know that in a given location (city, latitude / longitude), the recorded temperature has varied between two upper and lower bounds; in other circumstances, it may be important to know the specific temperature observation at a specific point in time.
