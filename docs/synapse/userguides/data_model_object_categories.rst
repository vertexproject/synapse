



.. highlight:: none

.. _data-model-object-categories:

Data Model - Object Categories
==============================

Recall that within the Synapse data model:

- **Nodes** commonly represent "things": objects, facts, or observables.
- **Tags** commonly represent "assessments": judgements or evaluations that may change given new data or revised analysis.

Within Synapse, forms are the building blocks for any analysis system. Forms are those objects relevant to a given knowledge domain that will be used to represent (model) that knowledge and answer analytical questions about the captured information. As such, the proper design of forms is essential.

In a hypergraph - where there are no edges, and thus everything is a node - forms take on additional significance. Specifically, forms must be used to represent more than just "nouns" and must be used to capture several general categories of objects. These categories can be broadly defined as entities, relationships, and events.

- `Entity`_
- `Relationship`_
- `Event`_
- `Instance Knowledge vs. Fused Knowledge`_

This section discusses informal categories of objects that can be modeled in Synapse. See :ref:`data-model-form-categories` for a discussion of some of the common "categories" of forms used to represent various objects.

.. _form-entity:

Entity
------

Forms can represent atomic **entities,** whether real or abstract. In the knowledge domain of cyber threat data, entity-type forms include domains, IP addresses (IPv4 or IPv6), hosts (computers / devices), usernames, passwords, accounts, files, social media posts, and so on. Other entity types include people, organizations, countries, bank or financial accounts, units of currency, chemical elements or formulas, telephone numbers, and so on. Any entity can be defined by a form and represented by a node. Entity-type forms are often represented as a :ref:`form-simple`. The term "simple" is used to denote that these forms can be represented as a primary property with a single value that uniquely defines the entity.

**Example**

An email address (``inet:email``) is a basic example of an entity-type node / simple form:




.. parsed-literal::

    cli> storm inet:email=kilkys@yandex.ru
    
    inet:email=kilkys@yandex.ru
            .created = 2019/03/13 23:55:10.882
            :fqdn = yandex.ru
            :user = kilkys
    complete. 1 nodes in 2 ms (500/sec).


.. _form-relationship:

Relationship
------------

Forms can represent specific **relationships** among entities. Recall that in a directed graph a relationship is represented as a directed edge joining exactly two nodes; but in a hypergraph the entire relationship is represented by a single node (form), and the relationship can encompass any number of entities or elements – not just two.

For cyber threat data, relationships include a domain resolving to an IP address, a malware dropper containing or extracting another file, or a threat actor moving laterally between two hosts. Other types of relationships include a company being a subsidiary of another business, an employee working for a company, or a person being a member of a group.

As an example of a “multi-dimensional” relationship, biological parentage could be represented by a three-way relationship among two genetic parents and an offspring.

Relationship-type forms are often represented as a :ref:`form-comp`. Comp forms have a primary property consisting of a comma-separated list of two or more values that uniquely define the relationship.

**Example**

A DNS A record (``inet:dns:a``) is a basic example of a relationship-type form / comp form:


.. parsed-literal::

    cli> storm inet:dns:a=(google.com,172.217.9.142)
    
    inet:dns:a=('google.com', '172.217.9.142')
            .created = 2019/03/13 23:55:10.923
            :fqdn = google.com
            :ipv4 = 172.217.9.142
    complete. 1 nodes in 2 ms (500/sec).


.. _form-event:

Event
-----

Forms can represent individual time-based occurrences. The term **event** implies that an entity existed or a relationship occurred at a specific point in time. As such events explicitly represent the intersection of the data represented by a form and an individual timestamp for the form’s existence or observation.

Examples of event-type forms include an individual login to an account, a specific DNS query, the high temperature reading in a city on a particular day, or a domain registration ("whois") record captured on a specific date.

The structure of an event-type form may vary depending on the specific event being modeled. For "simple" events that can be uniquely represented by the combination of a timestamp and an entity, the form may be a :ref:`form-comp` that happens to include a timestamp as one element of the form’s value (i.e., as in an ``inet:whois:rec`` form which captures the whois data that existed or was present at a given point in time).

For more "multi-dimensional" events involving several components, the form may be a :ref:`form-guid` with the timestamp as one of several secondary properties on the form (i.e., as in an ``inet:dns:request`` form).

**Example**

A specific, individual DNS query (``inet:dns:request``) is an example of an event-type form:


.. parsed-literal::

    cli> storm inet:dns:request=00000a17dbe261d10ce6ed514872bd37
    
    inet:dns:request=00000a17dbe261d10ce6ed514872bd37
            .created = 2019/03/13 23:55:10.958
            :query = ('tcp://199.68.196.162', 'download.applemusic.itemdb.com', '1')
            :query:name = download.applemusic.itemdb.com
            :query:name:fqdn = download.applemusic.itemdb.com
            :query:type = 1
            :reply:code = 0
            :server = tcp://178.62.239.55
            :time = 2018/09/30 16:01:27.506
    complete. 1 nodes in 4 ms (250/sec).


Instance Knowledge vs. Fused Knowledge
--------------------------------------

For certain types of data, event forms and relationship forms can encode similar information but represent the difference between **instance knowledge** and **fused knowledge.**

- Event forms represent the specific point-in-time existence of an entity or occurrence of a relationship - an **instance** of that knowledge. 

- Relationship forms can leverage the universal ``.seen`` property to set "first observed" and "last observed" times during which an entity existed or a relationship was true. This date range can be viewed as **fused** knowledge - knowledge that summarizes or "fuses" the data from any number of instance knowledge nodes over time.

Instance knowledge and fused knowledge represent differences in data granularity. Whether to create an event form or a relationship form (or both) depends on how much detail is required for a given analytical purpose. This consideration often applies to relationships that change over time, particularly those that may change frequently.

**Example**

DNS A records are a good example of these differences. The IP address that a domain resolves to may change infrequently (e.g., for a website hosted on a stable server) or may change quite often (e.g., where the IP is dynamically assigned or where load balancing is used). 

One option to represent and track DNS A records would be to create individual timestamped forms (events) every time you check the domain’s current resolution (e.g., ``inet:dns:request`` and ``inet:dns:answer`` forms). This represents a very high degree of granularity as the nodes will record the exact time a domain resolved to a given IP, potentially down to the millisecond. The nodes can also capture additional detail such as the querying client, the responding server, the response code, and so on. However, the number of such nodes could readily reach into the hundreds of millions, if not billions, if you create nodes for every resolution of every domain you want to track.

An alternative would be to decide that it is sufficient to know that a domain resolved to an IP address during a given period of time – a "first observed" and "last observed" (``.seen``) range. A single ``inet:dns:a`` node can be created to show that domain ``woot.com`` resolved to IP address ``1.2.3.4``, where the earliest observed resolution was 8/6/2014 at 13:56 and the most recently observed resolution was 5/29/2018 at 7:32. These timestamps can be extended (earlier or later) if additional data changes our observation boundaries.

This second approach loses some granularity:

- The domain is not guaranteed to have resolved to that IP **consistently** throughout the entire time period.
- Given only this node, we don’t know **exactly** when it the domain resolved there during that time period, outside of the earliest and most recent observations.

However, this fused knowledge may be sufficient for our needs and may be preferable to creating thousands of nodes for individual DNS resolutions. 

Of course, a hybrid approach is also possible, where most DNS A record data is recorded in fused ``inet:dns:a`` nodes but it is also possible to record high-resolution, point-in-time nodes when needed.
