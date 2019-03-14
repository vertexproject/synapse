



.. highlight:: none

.. _design-forms-vs-tags:

Design Concepts - Forms vs. Tags
================================

In designing both data and analytical models, one of the first choices that must be made is whether something should be represented as:

- a form
- a property on a form
- a tag

While every modeling decision is unique, there are some basic principles that can be used to guide your choices:

- **One-to-one vs. one-to-many.** Since properties (both primary and secondary) are structured as ``<form> = <valu>`` or ``<prop> = <valu>``, any property must have only a single value for a given node. Looked at another way: if there is a characteristic associated with a form that can have more than one value, it should not be represented as a secondary property and is a better candidate for a relationship-type form or a tag.

- **"Intrinsic-ness".** The more closely related or "intrinsic" something is to an object, the more likely it should be a secondary property (if it exists in a one-to-one relationship with the object) or a component of a relationship form (if it exists in a one-to-many relationship with the object). Things that are not highly intrinsic are better candidates for tags that can be applied to relevant nodes.

- **Objective vs. Assessed.** Broadly speaking, things that are objectively real, factual, or verifiable should be represented in the data model (as forms or properties). Things that represent evaluations or assessments should be represented as tags. (See :ref:`analytical-model-tags-analysis` for further discussion on the types of things commonly represented by tags.)

While detailed discussion of data and analytical model concepts is beyond the scope of these documents, this section attempts to provide a few concrete examples to illustrate the process.

**Example 1 - People and Email Addresses**

An email address is a common piece of data associated with a person. What is the best way to represent an email address belonging to a specific person?

One option is to include the email address as a secondary property on the person node (i.e., ``ps:person:email``). However, it is common for people to have more than one email address, such as a work email and and a personal email. While you could create multiple secondary properties, one for work email (``ps:person:wemail``) and one for a personal email (``ps:person:pemail``), it is also common for people to have multiple work emails (such as through changing jobs over time) or even multiple personal emails (for different purposes). This quickly leads to numerous secondary properties that make pivoting difficult if an analyst has to pivot to multiple properties (``:wemail1``, ``:wemail2``, etc.)

"Person" and "email address" is potentially a **one-to-many** relationship, so it is problematic to attempt to record "email address" in a set of secodnary properties associated with a person node.

In addition, if we consider **intrinsic-ness** an email address is not "intrinsic" to a person. There is nothing that makes a particular email address inherently "mine" other than the fact I signed up for it. This is another indication that "email address" should not be a property on a person node.

Similarly, it doesn't make sense for an email address to be associated with a person node via a tag. First, an email address is an objective "thing" (as opposed something representing an assessment or an evaluation), so is more suitable to be represented as a form in the data model as opposed to a tag in the analytical model. Similarly, a person having a particular email address is something that is objectively verifiable (given enough information) as opposed to something that is an assessment or evaluation.

A person having an email address is a relationship so is most suitable for a relationship-type form / :ref:`form-comp`. This could be a custom form specifically representing this relationship (i.e., ``ps:hasemail``) if there is something particularly unique or important about a person having an email address. Alternately, it can be reperesnted with the generic ``edge:has`` form which links two arbitrary forms (in this case person (``ps:person``) and email address (``inet:email``)) in a "has" or "owns" relationship.

Using a comp form allows us to capture multiple instances of a person having an email address (through multiple ``edge:has`` nodes). In addition, we can capture "when" a person had a given email address (if we know that information) using the ``.seen`` universal property. This allows us to also record both current and historical knowledge of when a given email address was in use.

**Example 2 - Threat Cluster Indicators**

The ability to associate activity with a specific threat cluster, often to aid in the detection of malicious activity or to drive incident response, is central to the knowledge domain of cyber threat data. We refer to the process of associating indicators (domains, IP addresses, files representing tools or malware binaries) with a set of related activity as **threat clustering** (though others may refer to it as "attributing" indicators to a specific "threat group").

Let’s say you determine that an IP address (``inet:ipv4``) is associated with activity tracked as Threat Cluster 12. Is this association best represented as a form, a property, or a tag?

One option would be to create a secondary property on the IPv4 form to indicate that the node was used by Threat Cluster 12 (i.e., ``inet:ipv4:tc=t12``). However, this is problematic for a few reasons:

- **One-to-many.** An IP address may not be used exclusively by Threat Cluster 12, either over time or at a single point in time. Different threat actors may compromise the same vulnerable system, either concurrently or at different times. Alternately, an IP address may represent specialized infrastructure (such as a Tor exit node or anonymous VPN endpoint) designed to be used concurrently by multiple individuals. This implies we would potentially need multiple "threat cluster" secondary properties on the node.

- **Intrinsic-ness.** A threat cluster "using" an IP address (even if they own the IP range or purchase a VPS hosted on the IP) is not an "intrinsic" characteristic of the IP address itself. This impiles that the association of threat cluster and IP should not be tightly coupled in the form of a secondary property.

A second option would be to create a relationship-type form. This potentially addresses our "intrinsic" concerns by no longer tightly coupling the IP and the threat cluster (via a secondary property) and addresses our one-to-many concern by allowing multiple "relationship" nodes to indicate that a threat cluster uses or has used multiple IP addresses. As with our person-and-email-address example, this could be a generic ``edge:has`` form ("threat cluster has IP address") or a custom form representing this specific relationship.

This is also a non-optimal design choice based on our **objective vs. assessed** criteria. Theoretically speaking, it should be possible to verify that Threat Cluster 12 did in fact use a particular IP address. However, that statement is really more of an assessment than a "fact":

- "Threat Cluster 12" is really a collection of indicators (hashes, domains, IPs, email addresses, etc.) that someone has assessed are "related" (part of the same Threat Cluster), typically based on evidence that may include phishing emails, similarities in malware binaries, domain whois data, domain resolution data, incident response data, and so on. While it is assumed that Threat Cluster 12 (the set of indicators) is in fact used by an individual, group, or organization (a "threat group"), analysts generally have no concrete idea of the identity or membership of that group. The chance of objectively verifying that the set of indicators assocaited with "Threat Cluster 12" (including the IP address in question) were in fact all created or used by the same group is typically slim to none. This means that the association of a given IP with Threat Cluster 12 is an assessment as opposed to a verifiable objective fact. This implies that the information should be recorded as a tag as opposed to encoded in a form.

- Assessments by their nature change over time. As we obtain more data, our original evaluation may need to be revised. New information may result in deciding that the IP address was really associated with Threat Cluster 18 and not Threat Cluster 12. Alternately, new information may indicate that Threat Cluster 12 and Threat Cluster 47 are really the same group / set of activity and need to be merged. If information about indicators associated with Threat Clusters is encoded in nodes - and particularly in those nodes' primary properties - the only way to revise this data is to delete and recreate the nodes. It is much simpler to update or change a tag if the assessment represented by that tag later changes.

Using a tag (such as applying ``#cno.threat.t12`` to the ``inet:ipv4`` node) gives us the most flexibility in recording the information that the IP was associated with a specific set of malicious activty. In addition, if we know "when" the IP was used by or associated with the threat cluster, we can leverage tag timestamps to record that information.
