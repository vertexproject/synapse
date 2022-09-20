.. highlight:: none

.. _analytical-model-tags-analysis:

Analytical Model - Tags as Analysis
===================================

Analysis consists of collecting and evaluating data and drawing conclusions based on the data available to you.
Assuming data is collected and modeled accurately within Synapse, the data itself - nodes and their properties
- should not change. But as you collect more data or re-evaluate existing data, your **assessment** of that data
- often encoded in tags - may change over time. Nodes and properties are largely stable; tags are meant to be
flexible and readily modified if needed.

Every knowledge domain has its own focus and set of analytical questions it attempts to answer. The "answers" to some
of these questions can be recorded in Synapse as tags applied to relevant nodes. These tags provide **context** to
the data in Synapse.

The Synapse **data model** for tags is simple - it consists of the single ``syn:tag`` form. The appropriate **use** of
tags to annotate data is more nuanced. You can think of tags - their structure and application - as an
**analytical model** that complements and extends the power of the data model.

This analytical model:

- **Is largely independent from the data model.** You do not need to write code to implement new tags or design
  a tag structure; you simply need to create the appropriate ``syn:tag`` nodes.
- **Is specific to an analytical discipline.** Tags used for cyber threat analysis may be very different from tags used
  to track financial fraud.
- **Is tightly coupled with the specific questions you want to answer.** The tags you create and apply should be driven
  by your particular analysis goals.
  
  - The tags should annotate assessments and conclusions that are **important to your analysis.**
  - The tags should allow you to ask **meaningful questions** of your data.

The effective use of Synapse to conduct analysis depends on:

- **The data model:** how you represent the data you care about using Synapse's forms, properties, and types.
- **The analytical model:** how you design and use a set of tags to annotate data, provide context, and answer the
  questions that matter to you.

Tag Examples
------------

The sections below provide a few examples of the kinds of context - observations and assessments - that you can
represent with tags. Recording these assessments in Synapse alongside the relevant data provides immediate **context**
to that data, and allows you to query both data (nodes) and assessments (tags).

These examples are simply meant to illustrate a few possible "real-world" applications for tags. There is no "right" or
"wrong" set of tags (although there are "better" and "worse" design decisions that may impact your ability to answer
questions efficiently).

See :ref:`design-analytical-model` for considerations in designing tags and tag trees.

See :ref:`design-general` for considerations on whether to model something as a form, a property, a tag, or a
tag associated with a node.

See :ref:`design-tags-and-forms` for Synapse's ability to link tags to nodes to more easily cross-reference tags
with data model elements that those tags represent.

Domain-Specific Assessments
+++++++++++++++++++++++++++

The purpose of analysis is to draw relevant conclusions from the data at hand. The conclusions will vary based on the
knowledge domain, but could include big-picture assessments such as "The increase in widget manufacturing due to lower
production costs has had a negative effect on the demand for gizmos" or "The threat group Vicious Wombat is working
on behalf of the Derpistan government".

Those large assessments can be made based on numerous smaller assessments (tags) which are themselves based on the
observables (nodes) in Synapse. To build up to those larger assessments, you must start by recording those smaller
assessments as tags on nodes.

The folowing examples from cyber threat intelligence illustrate some of the assessments that can be recorded using
tags.

.. TIP::
  
  The specific tags referenced below are based on The Vertex Project's tag trees and use our conventions. Use
  what works for you!


Threat Clusters
***************

A common practice in threat intelligence involves deciding not only whether an indicator (such as a file, domain, or
IP address) is malicious, but whether it should be associated with a **threat cluster.** That is, can an indicator
be linked to other indicators (e.g., from the same indcident or intrusion) to create a known set of related indicators
and activity. "Threat clusters" may be built up and expanded over time to represent a broader set of activity presumed
to be carried out by some (generally unknown) set of malicious actors (a "threat group").

You can tag nodes to indicate that the node is associated with a particular threat cluster. For example:

``cno.threat.<cluster>``

Where ``cno`` is a top-level tag for assessments related to Computer Network Operations (CNO), ``threat`` is a
sub-tag used for threat clusters / threat groups, and ``<cluster>`` is the "name" of the particular threat cluster
based on your organization's conventions (names, numbers, etc.)

Tactics, Techniques, and Procedures (TTPs)
******************************************

The methodologies (sometimes known as tactics, techniques, and procedures or TTPs) that a threat group uses to conduct
activity provide insight into the group and its operations. Knowledge of past TTPs may help predict future actions or
operations. Sets of TTPs observed together may provide a "fingerprint" of a group’s activity. General knowledge of TTPs
in current use can help organizations more effectively protect and defend their assets.

"TTP" can cover a broad range of observed activity, from whether a group uses zero-day exploits to the specific packer
used to obfuscate a piece of malware. When a node represents an instance of the use of a TTP, it may be useful to
tag the node with the TTP in question.

For example, you have an email message (RFC822 file) that you assess is a phishing attack. You can tag the relevant
node or nodes (such as the ``file:bytes`` of the message and / or the ``inet:email:message`` node representing the
message metadata) with that TTP:

``cno.ttp.phish.message``

Where ``cno`` is our top-level tag, ``ttp`` represents the TTP sub-tree, ``phish`` represents assessments related to
phishing, and ``message`` indicates the node(s) represent the phishing email (e.g., as opposed to an attachment or
URL representing the phishing ``payload``, or the sending email address or IP representing the ``source``).

Third-Party Assertions
++++++++++++++++++++++

Some third-party data sources provide both data and tags or labels associated with that data. For example, Shodan may
provide data on an IPv4 address (such as which ports were open as of the last Shodan scan) as well as tags such as
``self-signed`` or ``vpn``. Similarly, VirusTotal may provide metadata and multiscanner data for files along with
tags such as ``peexe`` or ``invalid-signature``.

In addition, many commercial organizations conduct their own threat tracking and analysis and publish their research.
This type of research commonly includes "indicators of compromise" or IOCs - hashes, domains, IP addresses, and so on
indicative of the reported activity. These reports do not necessarily include tags provided by the reporting organization.
But the report may make it clear that the reporter associates the IOCs with particular malware families, "campaigns",
or threat groups.

Shodan's label indicating that an IPv4 address hosted a VPN and ESET's reporting that a SHA1 hash is associated with
the X-Agent malware family are both assertions. These assertions are valuable data and can be useful to your analysis.

That said, you may not have the means to **verify** these assertions yourself. To accept the assertion at face value
means you need to trust the third-party in question. "Trust" may include things like understanding the source of the
data; knowing their general reputation (i.e., within your analysis community); or building trust over time as you
determine the reliabilty and accuracy of their reporting.

Your own assertions are presumably "more trustworthy" based on direct access to your internal data and processes.
Assertions made by others may be open to question or validation, so it can be useful to record these third-party
assessments separately. This allows you to retain the context of what "other people" say while keeping those
(potentially lower-confidence) assertions separate from your own.

You can use tags to annotate "other people’s analysis" by tagging relevant nodes with what "other people" say about
them:

- ``rep.eset.sednit``: ESET says this SHA1 hash is associated with Sednit
- ``rep.shodan.vpn``: Shodan says this IPv4 hosts a VPN
- ``rep.vt.peexe``: VirusTotal says this file is a PE executable

Where ``rep`` is a top-level tag for third-party reporting, the second tag element (e.g., ``eset``) is the name
of the reporting organization, and the third tag element is the information the third party is reporting.

Domain-Relevant Observations
++++++++++++++++++++++++++++

Within a particular knowledge domain, it may be useful to record observations that **support** your analysis
process in some way. In other words, the observations are **relevant** to your analysis, but do not represent the
specific output or objective of your analysis.

In cyber threat intelligence, a primary goal is to track malicious activity and maintain awareness of the current
threat landscape, often in terms of malware, threat groups, and techniques / TTPs. Part of this tracking includes
noting infrastructure (such as IP addresses, netblocks, or domains) used in malicious activity.

Identifying network infrastructure as TOR nodes, anonymous VPN endpoints, or sinkhole IPs is not a primary goal
of threat intelligence, but knowing this information can be useful and help prevent analysts from mis-identifying
threat actor infrastructure.

You can use tags to annotate identified infrastructure (such as ``inet:ipv4`` nodes) of interest:

- ``cno.infra.anon.tor``: The IPv4 is a TOR exit node
- ``cno.infra.anon.vpn``: The IPv4 is an anonymous VPN exit point
- ``cno.infra.dns.sink.hole``: The IPv4 is used to resolve sinkholed FQDNs

Once again ``cno`` is our top-level tag for Computer Network Operations, ``infra`` indicates the "infrastructure"
sub-tree, the third element indicates the kind of infrastructure (``anon`` for anonymous, ``dns`` for DNS, etc.),
and so on.

Tags as Hypotheses
------------------

Another way to look at tags is as hypotheses. If a tag represents the outcome of an assessment, then every tag can be
seen as having an underlying question - a hypothesis - it is attempting to answer. Deciding to apply the tag is equivalent
to deciding that the underlying hypothesis is **true.**

Making these assessments typically involves the judgment of a human analyst; so evaluating and tagging data within
Synapse is one of an analyst's primary tasks.

Hypotheses may be simple or complex; tags typically represent relatively simple concepts that are used collectively to
support (or refute) more complex theories. Because the concept of encoding analytical conclusions within a system like
Synapse may be unfamiliar, a few examples may be helpful.

**Example 1**

The question "can this newly identified FQDN be associated with any known threat cluster?" can be thought of as *n*
number of individual hypotheses based on the number of known threat clusters:

- Hypothesis 1: This domain is associated with Threat Cluster 1.
- Hypothesis 2: This domain is associated with Threat Cluster 2.
- ...
- Hypothesis n: This domain is associated with Threat Cluster n.

If an analyst determines that the domain is associated with Threat Cluster 46, placing a Threat Cluster 46 tag (e.g.,
``cno.threat.t46``) on that FQDN effectively means that the hypothesis "This domain is associated with
Threat Cluster 46" has been assessed to be **true** (and by implication, that all competing hypotheses are false).

**Example 2**

Deciding whether a domain is meant to imitate (masquerade as) a legitimate domain for malicious purposes can also be
thought of as a set of hypotheses.

"Masquerading" is a threat actor technique (TTP) designed to influence a targeted user to trust something enough to
perform an action. A domain that "looks like" a valid FQDN or an email address that "looks like" a trusted sender
may encourage the victim to click a link or open an attachment. In threat intelligence, the focus is on **threat actor**
TTPs, so the TTPs we're interested in are (by definition) malicious.

Let’s say an analyst comes across the suspicious domain ``akcdndata.com``. To decide whether this is an example of a
masquerade, the analyst needs to decide:

- Is the FQDN ``akcdndata.com`` associated with known malicious activity?
- Does the FQDN ``akcdndata.com`` imitate a legitimate company, site, or service?


A number of possibilities (hypotheses) exist, such as:

- Hypothesis 1: The domain is NOT malicious.
- Hypothesis 2: The domain IS malicious, but is not meant to imitate anything.
- Hypothesis 3: The domain IS malicious, and is meant to imitate a legitimate resource.

The tag (or tags) the analyst decides to apply depend on which hypotheses they can prove or disprove (assert are
true, or not).

Deciding on Hypothesis 1 vs. Hypothesis 2 may involve things like reviewing domain registration data, associated
DNS infrastructure, or seeing if the FQDN shows up in public reporting of malicious activity.

If Hypothesis 1 is true, we would not tag the FQDN. If Hypothesis 2 is true, we can simply assert that the FQDN is
malicious (with a tag such as ``cno.mal``).

If Hypothesis 2 is true, deciding on Hypothesis 3 may be trickier. Does the FQDN "look like" anything
familiar? It may "look like" Akamai CDN (content delivery network) but that's a bit of a stretch...maybe it is just
a coincidence? Do we have any context around **how** the FQDN was used maliciously that might indicate that the
threat actors wanted to mislead victims into thinking the FQDN was associated with Akamai?

If we have enough evidence to support Hypothesis 3, we can apply a TTP tag such as ``cno.ttp.se.masq`` (``cno`` as
our top-level tag, ``ttp`` for our TTP sub-tree, ``se`` for social engineering TTPs, and ``masq`` for masquerade).

Individual Hypotheses to Broader Reasoning
++++++++++++++++++++++++++++++++++++++++++

The hypotheses represented by the tags in the examples above are fairly narrow in scope - an indicator is
associated with a threat cluster (``cno.threat.t42``), a domain was designed to mislead users by imitating a
legitimate web site or service (``cno.ttp.se.masq``). With Synapse, you can leverage these more focused
hypotheses to answer broader, more complex questions.

A newly identified zero-day exploit has been circulating in the wild and is in use by multiple threat groups. The
associated vulnerability has been assigned CVE-2021-9999 (a number we made up). The exploit is delivered via a
malicious XLSX file sent as an email (phishing) attachment.

You believe that "Threat Group 12 was the first group to use the zero day associated with CVE-2021-9999". To prove
or disprove this hypothesis, you could query Synapse for all files (``file:bytes`` nodes) that:

- exploit CVE-2021-9999 (i.e., have a tag such as ``rep.vt.cve_2021_9999``), and
- are associated with a known threat cluster or threat group (i.e., are tagged ``cno.threat.<cluster>``)

If you have data for any associated phishing messages, you can pivot from the malicious XLSX files to their
associated emails (``inet:email:message:attachment -> inet:email:message``) and look for the phishing message
with the oldest date. By identifying the threat group associated with the earliest known email, you can determine
whether the zero-day was first used by Threat Group 12 or some other group.

You are able to take tags associated with simple assessments ("this file exploits CVE-2021-9999" or "this file is
associated with Threat Cluster 12") and combine nodes (files / ``file:bytes``), properties (``inet:email:message:date``),
and tags to answer a more complex question. That's the power of Synapse!

.. NOTE::
  
  This example is simplified; you would of course perform additional research besides what is described above
  (such as searching for additional samples that exploit the vulnerability and any associated phishing
  attempts, attributing identified samples that are not yet associated with a Threat Cluster, etc.)
  
  Assuming you have completed your research and the data is in Synapse and tagged appropriately, you can easily
  answer the above question using the Storm query language using a query such as the following:
  
  ::
    
    file:bytes#rep.vt.cve_2021_9999 +#cno.threat -> inet:email:message:attachment 
      -> inet:email:message | min :date | -> # +syn:tag^=cno.threat
  

