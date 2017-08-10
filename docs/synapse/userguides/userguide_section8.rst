Data Model - Tag Concepts
=========================

Recall from `Data Model – Basics`__ that the key data model components within Synapse are nodes and tags. Broadly speaking:

* **Nodes** commonly represent “facts” or “observables”: things that are objectively true or verifiable.

* **Tags** commonly represent information that may evolve over time. Most commonly, tags represent “analytical assessments”: conclusions drawn from observables that may change if data or the assessment of the data changes. In some cases, tags represent facts that may change over time. Facts that may be true for a limited period include the geolocation of an IP address or the association of an IP address with a specialized service, such as a TOR exit node or a VPN provider.

(See the section on `Secondary Properties vs. Relationship Nodes vs. Tags`__ for some general considerations when determining whether something should be represented as a node, a node property, or a tag.)

Tags can be thought of as labels applied to nodes; within the Synapse hypergraph, a given tag can be applied to any number of nodes. As such, a tag is a hyperedge that joins any number of arbitrary nodes into a set. Grouping nodes together in Synapse using tags is typically done to further some analytical goal.

Conversely, a node can have any number of tags applied to it, thus having any number of hyperedges or belonging to any number of analytical sets.

Tag Structure
-------------

Tags use a dotted naming convention, with the period ( . ) used as a separator character to delimit individual "components" of a tag if necessary. This dotted notation means it is possible to create **tag hierarchies** of arbitrary depth that support increasingly detailed or specific observations. For example, the top level tag ``foo`` can represent a broad set of observations, while ``foo.bar`` and ``foo.baz`` could represent subsets of ``foo`` or more specific observations related to ``foo``.

In a tag hierarchy, the full tag (down through and including the lowest or rightmost element) is known as the **leaf** tag for that hierarchy. For the tag ``foo.bar.baz``, ``foo.bar.baz`` is the leaf. The “top” or leftmost component ``foo`` may be informally referred to as the **root** of that hierarchy. The lowest (rightmost) element in a tag hierarchy is known as the **base** of the tag.

When you apply a tag to a node, all of the tags in the tag hierarchy are applied; that is, if you apply tag ``foo.bar.baz`` to a node, Synapse automatically applies the tags ``foo.bar`` and ``foo`` as well.

When you delete a tag from a node, the tag and **all tags below it** in the hierarchy are deleted. If you delete the tag ``foo.bar.baz`` from a node, the tags ``foo.bar`` and ``foo`` will remain. However, if you delete the tag ``foo`` from a node with the tag ``foo.bar.baz``, then all three tags (``foo``, ``foo.bar``, and ``foo.bar.baz``) are deleted.

Tag Timestamps
--------------

Applying a tag to a node has a particular analytical meaning; it typically represents the recording of an assessment or judgment about the existing data within the hypergraph. Many assessments are "binary" in the sense that they are always either true or false; in these cases, the presence or absence of a tag is sufficient to accurately reflect the current analytical assessment, based on available data.

There are other cases where an assessment may be true only for a period of time or within a specified time frame. Internet infrastructure is one example; whether an IP address is part of an anonymization service (such as TOR or an anonymous VPN provider) can be annotated using tags. However, this information can change over time as the IP address is reallocated to a different provider or repurposed for another use. Although the relevant tag (for example, ``anon.vpn``) can be applied while the IP is part of an anonymous VPN service and removed when that is no longer true, completely removing the tag causes us to lose the historical knowledge that the IP was part of a VPN network **at one time.**

To address these use cases, Synapse supports the use of **timestamps** with tags. When a tag is applied to a node, optional "first seen" and "last seen" timestamps can be used to indicate "when" the condition represented by that tag was valid. The timestamps can be "pushed out" if additional data indicates the condition was true earlier or later than initially observed.

Tag timestamps represent a time **range,** and not necessarily specific occurrences (other than the "first known" and "last known" observations). This means that the assessment represented by the tag is not guaranteed to have been true throughout the entire date range. That said, the use of timestamps allows much greater granularity in recording analytical observations in cases where the timing of an assessment ("when" something was true) is relevant.

Tag Display
-----------

If any tags are applied to a node, detailed tag information will be displayed with the node properties regardless of "how" you ask about a node (e.g., ``ask`` and ``ask --props`` will display the same tag information, even though they display different details about the node properties). This includes:

* the lowest (leaf) tags (e.g., for display purposes Synapse will list ``foo.bar.baz`` but not ``foo.bar`` and ``foo``, even though they are also separate tags on the node).
* the timestamp when the tag was first applied to the node.
* the minimum / maximum times during which the tag was applicable to the node, if present.

For example::

  cli> ask inet:fqdn=woot.com

  inet:fqdn = woot.com
      #foo.bar (added 2017/06/20 19:59:02.854)
      #hurr.derp (added 2017/08/02 21:11:37.866) 2017/05/23 00:00:00.000  -  2017/08/03 00:00:00.000
  (1 results)

blah

.. _Basics: ../userguides/userguide_section3.html
__ Basics_

.. _Compare: ../userguide_section6.html#secondary-properties-vs-relationship-nodes-vs-tags
__ Compare_
