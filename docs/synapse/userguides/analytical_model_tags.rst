



.. highlight:: none

.. _analytical-model-tags:

Analytical Model - Tag Concepts
===============================

Recall from :ref:`data-model-terms` that two of the key components within Synapse are nodes and tags. Broadly speaking:

- **Nodes** commonly represent "facts" or "observables": things that are objectively true or verifiable and not subject to change.
- **Tags** commonly represent information that may change or evolve over time. In some cases this information may be a fact that is true for a given period, but then is no longer true (such as the association of an IP address with a specialized service such as Tor). In most cases, tags represent assessments or analytical evaluations: conclusions drawn from observables that may change in light of new data or re-evaluation of existing data.

The types, forms, and properties that define nodes make up the Synapse **data model.** The **tags** representing labels applied to those nodes can be thought of as the **analytical model** used to record observations or assessments about that data. This section provides some additional background on tags before a more in-depth discussion on their use:

- `Tags as Nodes`_
- `Tags as Labels`_

Tags as Nodes
-------------

While tags primarily record analytical observations, tags are also nodes within the Synapse data model. Every tag is a node of the form ``syn:tag`` (whose type is ``syn:tag``).

A tag node's primary property (``<form> = <valu>``) is the name of the tag; so the tag ``foo.bar`` has the primary property ``syn:tag = foo.bar``. The dotted notation can be used to construct "tag hierarchies" that can represent varying levels of specificity (see below).

This example shows the **node** for the tag ``syn:tag = aka.feye.thr.apt1``:


.. parsed-literal::

    cli> storm syn:tag=aka.feye.thr.apt1
    
    syn:tag=aka.feye.thr.apt1
            .created = 2019/03/13 23:55:41.110
            :base = apt1
            :depth = 3
            :doc = Indicator or activity FireEye calls (or associates with) the APT1 threat group.
            :title = APT1 (FireEye)
            :up = aka.feye.thr
    complete. 1 nodes in 3 ms (333/sec).


The following properties are present for this node:

- ``.created``, which is a universal property showing when the node was added to a Cortex.
- ``:title`` and ``:doc``, which are meant to store concise and more detailed (if necessary) definitions for the tag, respectively. Applying explicit definitions to tag nodes limits ambiguity and helps ensure tags are being applied (and interpreted) correctly by Synapse analysts and other users.

The ``:depth``, ``:up``, and ``:base`` secondary properties help to lift and pivot across tag nodes:

- ``:depth`` is the "location" of the tag in a given dotted tag hierarchy, with the count starting from zero. A single-element tag (``syn:tag = aka``) has ``:depth = 0``, while a three-element tag (``syn:tag = aka.feye.thr``) has ``:depth = 2``.

- ``:base`` is the final (rightmost) element in the dotted tag hierarchy.

- ``:up`` is the tag one "level" up in the dotted tag hierarchy.

Additional information on viewing and pivoting across tags can be found in :ref:`storm-ref-model-introspect`. For detail on the Storm query language, see :ref:`storm-ref-intro`.

Tags (``syn:tag`` forms) have a number of type-specific behaviors within Synapse with respect to how they are indexed, created, and manipulated via Storm. Most important for practical purposes is that ``syn:tag`` nodes are created "on the fly" when a tag is applied to another node. That is, the ``syn:tag`` node does not need to be created manually before the tag can be used; the act of applying a tag will cause the creation of the appropriate ``syn:tag`` node (or nodes).

See the ``syn:tag`` section within :ref:`storm-ref-type-specific` for additional detail on tags and tag behavior within Synapse and Storm.

Tags as Labels
--------------

Synapse does not include any pre-populated tags (``syn:form = <tag>``), just as it does not include any pre-populated domains (``inet:fqdn = <domain>``). Because tags can be highly specific to both a given knowledge domain and to the type of analysis being done within that domain, organizations have the flexibility to create a tag structure that is most useful to them.

A tag node's value (``syn:tag = <valu>``) is simply a string and can be set to any user-defined alphanumeric value. However, the strings are designed to use a dotted naming convention, with the period ( ``.`` ) used as a separator character to delimit individual elements of a tag if necessary. This dotted notation means it is possible to create tag hierarchies of arbitrary depth that support increasingly detailed or specific observations. For example, the top level tag ``foo`` can represent a broad set of observations, while ``foo.bar`` and ``foo.baz`` could represent subsets of ``foo`` or more specific observations related to ``foo``.

Within this hierarchy, specific terms are used for the tag and its various components:

- **Leaf tag:** The full tag path / longest tag in a given tag hierarchy.
- **Root tag:** The top / leftmost element in a given tag hierarchy.
- **Base tag:** The bottom / rightmost element in a given tag hierarchy.

For the tag ``foo.bar.baz``:

- ``foo.bar.baz`` is the leaf tag / leaf.
- ``foo`` is the root tag / root.
- ``baz`` is the base tag / base.

When you apply a tag to a node, all of the tags **above** that tag in the tag hierarchy are automatically applied as well (and the appropriate ``syn:tag`` forms are created if they do not exist). That is, when you apply tag ``foo.bar.baz`` to a node, Synapse automatically applies the tags ``foo.bar`` and ``foo`` as well. Because tags are meant to be hierarchical, if the specific assessment ``foo.bar.baz`` is applicable to a node and ``foo.bar.baz`` is a subset of ``foo``, it follows that the broader assessment ``foo`` is applicable as well.

When you delete (remove) a tag from a node, the tag and all tags **below** it in the hierarchy are deleted. If you delete the tag ``foo.bar.baz`` from a node, the tags ``foo.bar`` and ``foo`` will remain. However, if you delete the tag ``foo`` from a node with the tag ``foo.bar.baz``, then all three tags (``foo``, ``foo.bar``, and ``foo.bar.baz``) are deleted.

See the ``syn:tag`` section within :ref:`storm-ref-type-specific` for additional detail on tags and tag behavior within Synapse and Storm.

See :ref:`analytical-model-tags-analysis` and :ref:`design-analytical-model` for additional considerations for tag use and creating tag hierarchies.

Tag Timestamps
++++++++++++++

Applying a tag to a node has a particular meaning; it typically represents the recording of an assessment about that node with respect to the existing data in the Cortex. Many assessments are binary in the sense that they are either always true or always false; in these cases, the presence or absence of a tag is sufficient to accurately reflect the current analytical assessment, based on available data.

There are other cases where an assessment may be true only for a period of time or within a specified time frame. Internet infrastructure is one example; whether an IP address is part of an anonymization service such as Tor can be annotated using tags (e.g., ``cno.infra.anon.tor``). However, this information can change over time as the IP address is reallocated to a different client or repurposed for another use. Although the relevant tag can be applied while the IP is a Tor node and removed when that is no longer true, completely removing the tag causes us to lose the historical knowledge that the IP was a Tor node **at one time.**

To address these use cases, Synapse supports the optional use of **timestamps** (technically, time intervals) with tags applied to nodes. These timestamps can represent "when" (first known / last known times) the **assessment represented by the tag** was relevant for the node to which the tag is applied. (These timestamps are analogous to the ``.seen`` universal property that can be used to represent the first and last known times the **data represented by a node** was true / real / in existence.)

Applying a timestamp to a tag affects that specific tag only. The timestamps are not automatically propagated to tags higher up (or lower down) in the tag tree. This is because the specific tag to which the timestamps are applied is the most relevant with respect to those timestamps; tags elsewhere in the tree may have different shades of meaning and the timestamps may not apply to those tags in the same way (or at all).

Like ``.seen`` properties, tag timestamps represent a time **range** and not necessarily specific instances (other than the "first known" and "last known" observations). This means that the assessment represented by the tag is not guaranteed to have been true throughout the entire date range (though depending on the meaning of the tag, that may in fact be the case). That said, the use of timestamps allows much greater granularity in recording analytical observations in cases where the timing of an assessment ("when" something was true or applicable) is relevant.

**Example - Tor Exit Nodes**

Many web sites provide lists of Tor nodes or allow users to query IP addresses to determine whether they are Tor nodes. These sites may provide a "first seen" date for when the IP was first identified as part of the Tor network. The "first seen" date and date the site was queried (assuming the site status is current) can be used as timestamps for "when" the tag ``cno.infra.anon.tor`` was applicable to that IP address.

If we have a data source that verifies that IP address ``197.231.221.211`` was a Tor exit node between December 19, 2017 and February 15, 2019, we can apply the tag ``#cno.anon.tor.exit`` with the appropriate time range as follows:


.. parsed-literal::

    cli> storm inet:ipv4 = 197.231.221.211 [ +#cno.anon.tor.exit = (2017/12/19, 2019/02/15) ]
    
    inet:ipv4=197.231.221.211
            .created = 2019/03/13 23:55:41.148
            :asn = 37560
            :dns:rev = exit1.ipredator.se
            :latlong = 8.4219,-9.7478
            :loc = lr.lo.voinjama
            :type = unicast
            #cno.anon.tor.exit = (2017/12/19 00:00:00.000, 2019/02/15 00:00:00.000)
    complete. 1 nodes in 3 ms (333/sec).


Tag Display
+++++++++++

By default, Storm displays only the leaf tags applied to a node in the node’s output. Recall that applying the tag ``foo.bar.baz`` also applies the tags ``foo`` and ``foo.bar``; however these are not shown in the Storm output by default (full details of a node, including **all** tags applied to the node, can be viewed with the ``--raw`` or ``--debug`` options to the :ref:`syn-storm` command). Any timestamps associated with a tag are displayed in parentheses following the tag:


.. parsed-literal::

    cli> storm inet:ipv4 = 197.231.221.211
    
    inet:ipv4=197.231.221.211
            .created = 2019/03/13 23:55:41.148
            :asn = 37560
            :dns:rev = exit1.ipredator.se
            :latlong = 8.4219,-9.7478
            :loc = lr.lo.voinjama
            :type = unicast
            #cno.anon.tor.exit = (2017/12/19 00:00:00.000, 2019/02/15 00:00:00.000)
    complete. 1 nodes in 2 ms (500/sec).

