
Data Model - Node Properties
============================

Primary Properties
------------------

In `Data Model – Basics`__, we noted that a node's **primary property** consisted of the node's **form** (its type or "template") plus its specific value. More importantly, we noted that a primary property **must be unique for a given form.** From this standpoint, the design of a form and selection of its primary property are critical.

Looked at another way, when creating a form (node type) for a given knowledge domain, the most important question you must ask is: **what is it about this object / relationship / event that makes it unique** and allows it to be deconflicted from all other instances of this form? That is, what gives it "thinghood"? That unique feature (or set of features) will determine an appropriate primary property. Whether that primary property is a simple property (e.g., a single ``<form>=<value>``), a GUID, or a set of properties will determine the type of node (simple, composite, or cross-reference – described in `Data Model - Node Types`__) that should be used.

Once defined, the primary property of a form cannot be changed. To modify a form's primary property, you would need to create a new node type and then migrate any existing nodes to use the new form.

Secondary Properties
--------------------

Secondary properties are those characteristics that are not necessarily unique for a given form, but that provide relevant detail to help describe an individual node. Once you have determined the primary property for a given form, consider what additional details about that form should be captured as secondary properties. Since much navigation and analysis within a Synapse hypergraph is based on querying and pivoting across properties and / or values, a basic rule of thumb is that any piece of data that you might want to search on, pivot across, or otherwise correlate should be broken out as a secondary property (if not already a primary property).

Secondary properties can be added or removed from a given form by updating the form within Synapse. Depending on the specific changes made, you may need to retroactively update previously-created nodes of the same form.

Secondary Properties vs. Relationship Nodes vs. Tags
----------------------------------------------------

One of the difficulties in designing an effective data model is making effective design choices as to whether data is best represented as a property (primary or secondary) of a node; as a component of the relationship represented by a relationship node; or as a tag applied to relevant nodes. While every modeling decision is unique, there are some basic principles that can be used to guide your choices:

- **One-to-one vs. one-to-many.** Since properties (both primary and secondary) are structured as ``<prop>=<value>``, properties must have only a single value for a given node. Looked at another way: if there is a characteristic associated with a node that can have more than one value, it should not be represented as a secondary property and is a better candidate for a relationship node or a tag.

- **Intrinsic-ness.** The more closely related or "intrinsic" a thing is to an object, the more likely the thing should be a secondary property (if it exists in a one-to-one relationship with the object) or a component of a relationship node (if the thing exists in a one-to-many relationship with the object). Things that are not highly intrinsic are better candidates for tags that can be applied to relevant nodes.

A few examples will help to better illustrate these concepts.

**Example 1 - People and Email Addresses**

An email address is a common piece of data associated with a person. In creating a person node (``ps:person``), one’s first thought may be to include the email address as a secondary property on the node (``ps:person:email``). However, it is common for people to have more than one email address, such as a work email and and a personal email. One option would be to create multiple secondary properties: ``ps:person:wemail`` for a work email and ``ps:person:pemail`` for a personal email. This is also problematic, for several reasons: first, an individual may have multiple work or personal email addresses. Also, those email addresses may change (for example, if the person changes jobs). This would potentially require creating an unlimited number of secondary properties (``ps:person:wemail1, ps:person:wemail2...ps:person:wemailn``), and also makes querying and pivoting extremely difficult if you have to account for dozens of differently-named secondary properties that may contain the data you're looking for.

Because “person” and “email address” is typically a **one-to-many relationship** (a person may have many email addresses), capturing the data in a secondary property is a poor choice. But should the data be captured in a relationship node or a tag? For “person has email address”, the relationship is best captured in a relationship node (``ps:hasemail``) for the following reasons:

- “Email address” is a defined type within the Synapse data model (``inet:email``), making it suitable as a component of a primary property (e.g., in a composite node) and ideal for querying or pivoting. In other words, structuring this as a node makes it easier (more performant, syntactically simpler) to answer relevant analytical questions.

- An email address is a fairly **intrinsic** characteristic of a person in the sense that the same email address cannot be assigned to two different people at the same time. This “intrinsic-ness” makes it a better candidate for a component of a relationship node than a tag. Looked at another way, if the email address were represented as a tag, you would be unlikely to apply that tag to more than one node.

- While the data may change over time (a person may obtain a new email address), you likely don’t want to lose the historical knowledge of a previously used address. You can capture both current and historical email address associations in multiple relationship nodes (and time-bound the nodes with secondary ``seen:min`` and ``seen:max`` dates if necessary).

**Example 2 - Threat Group Indicators**

The ability to identify and correlate activity with a specific threat group, often to aid in the detection of malicious activity or to drive incident response, is central to the knowledge domain of cyber threat data. We refer to the process of associating indicators (domains, IP addresses, files representing tools or malware binaries) with threat groups as “threat clustering”, though others may refer to it as “attribution”.

Let’s say you determine that an IP address (``inet:ipv4``) is being used by a group tracked as “Threat Group 12” (``t12``). One option would be to create a secondary property on the ``inet:ipv4`` node for an associated threat cluster (``tc``) to show the IP is associated with Threat Group 12 (``inet:ipv4:tc=t12``). This is problematic for a few reasons:

- Association with a threat group typically implies that an object (IP address, domain, file) is “bad” or malicious. While threat actors may pay for infrastructure and thus control a “dedicated” IP (which therefore is likely "fully bad"), they may also compromise infrastructure that hosts legitimate content - such that the IP may be “bad” under some circumstances but “good” under others. The property does not allow us to make that distinction.

- The IP address may not be used exclusively by Threat Group 12, either over time or at a single point in time. For example, different threat groups may compromise the same vulnerable system, either concurrently or at different times. Alternately, an IP address may represent specialized infrastructure (a TOR exit node, a proxy, a VPN endpoint) designed to be used concurrently by multiple individuals.

It should be clear that if we try to represent threat clustering as a secondary property, we run into similar issues as our previous example. In particular, for some indicators threat clustering may be a **one-to-many relationship,** and we quickly multiply the number of secondary properties we might need to track this information (``:tc1, :tc2...:tcn``). But should this "threat cluster" information be represented as a relationship node (perhaps “threat group has IP address”?) or as a tag?

In this case, use of a tag is a better option for the following reasons:

- “Threat group” or “threat cluster” is **not intrinsic** to an IP address (or a domain, or a file). It’s an analytical assessment specific to a given knowledge domain. This lack of “intrinsic-ness” makes it a poor candidate for a component property of a relationship node.

- Recording threat clustering data as a property (``<prop>=<value>``, or ``:tc=t12``) means you would need to ask about this data by lifting and / or pivoting. In particular if you wanted to ask the question “what are all the things associated with Threat Group 12?”, you would need to lift data where the secondary property on multiple node types (domains, files, IP addresses, email addresses) had a value of ``t12``. “Lift by value” (as opposed to “lift by <prop>=<value>”) is a computationally intense action. If the threat cluster data is stored as a tag (``#tc.t12``), it is much easier to lift the set of nodes that have that tag. The use of a tag better supports the ability to ask analytically relevant questions.


.. _Basics: ../userguides/ug003_dm_basics.html
__ Basics_

.. _Types: ../userguides/ug007_dm_nodetypes.html
__ Types_
