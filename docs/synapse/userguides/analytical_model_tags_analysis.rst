



.. highlight:: none

.. _analytical-model-tags-analysis:

Analytical Model - Tags as Analysis
===================================

Research and analysis consists of collecting and evaluating data and drawing conclusions based on that available data. Assuming data is initially collected and recorded (modeled) accurately within a Cortex, the underlying **data** (typically encoded in nodes and their properties) should not change. However, as you collect more data or different types of data, or as you re-evaluate existing data, your **assessment** of that data - typically encoded in tags - may change. Nodes and properties are meant to be largely stable; tags are meant to be flexible and evolving.

Every knowledge domain has its own focus and set of questions it attempts to answer. The "answers" to some of these questions can be recorded as tags applied to relevant nodes in a Cortex.

While the Synapse data model related to tags is straightforward (consisting of only the single ``syn:tag`` form), the appropriate use of tags for data annotation is more complex. Tags can be thought of as being part of an **analytical model** that relies on the Synapse data model, but that:

- **Exists largely independently from the data model.** You do not need to write code to implement new tags or design a tag structure; you simply need to create the appropriate ``syn:tag`` nodes.
- **Is knowledge domain-specific.** Tags used for cyber threat analysis will be very different from tags used for biomedical research.
- **Is tightly coupled with the specific analytical questions the Synapse hypergraph is intended to answer.** The questions you want to answer should dictate the tags you create and apply.

In short, effective use of Synapse to conduct analysis is dependent on:

- **The data model:** how you define types, forms, and properties to represent data within your knowledge domain.
- **The analytical model:** how you design a set of tags to annotate data within your knowledge domain.

A well-designed tag structure should:

- **Represent relevant observations.** Tags should annotate assessments and conclusions that are important to your analysis.
- **Facilitate effective analysis.** Tags should be structured to allow you to ask meaningful questions of your data.

Tag Examples
------------

The sections below provide a few examples of the types of observations and analysis that can be represented by tags.

Note that these are meant simply to illustrate a few potential "real-world" applications for tags - there is no "right" or "wrong" tag hierarchy (although there are "better" and "worse" ways to design tag hierarchies that may impact your ability to answer analytical questions efficiently).

See :ref:`design-analytical-model` for considerations in designing a set of tags and tag hierarchies.

See :ref:`design-forms-vs-tags` for considerations on whether something should be modeled as a form, a property, or a tag.

Domain-Relevant Facts
+++++++++++++++++++++

The Synapse data model itself is meant to represent objective information related to a given knowledge domain - facts or observables whose validity is not in dispute. An IP address is an IP address - there should be no disagreement or debate whether an IP "exists" or is part of a given Autonomous System (AS), for example.

Not all details about objects are relevant to all knowledge domains. An IP address is an IP address in any data model. Whether that IP address is a Tor node or a shared web host or an anonymous proxy may be irrelevant to someone using that data model to analyze Internet traffic flow and patterns, for example. However, those additional facts may be very relevant to someone using the model to analyze cyber threat data.

These additional details can be considered to be "domain-relevant facts". That is, they are domain-relevant in that they are pertinent to certain types of analysis attempting to answer certain types of questions. They are facts in that an IP is either a Tor node or it isn’t, although your determination as to whether it is a Tor node may include some degree of assessment or evaluation. For example, you can verify directly that the IP is a Tor node if you have access to the host using the IP. Alternately, you can verify indirectly via a trusted third party ("Foo Tor Tracking Service says this is a Tor node"), or infer that the IP is a Tor node from other evidence available to you.

One option to record this information is to encode it in a set of tags that can be applied to the relevant nodes. The advantages of using tags include:

- Eliminates the need to record an excessive number of secondary properties within the data model that may only be relevant to a subset of users.
- Allows flexibility in creating a tag structure appropriate to the analytical questions being asked.
- Allows flexibility in applying or removing tags if data changes (i.e., an IP may be a Tor node for a period of time and then be reconfigured to no longer host that service).
- Allows flexibility to apply time boundaries to the observations if necessary (i.e., can apply a timestamp / date range to the Tor tag to show when the IP was a Tor node).

When creating a set of domain-specific tags, it may be useful to structure them under a root tag representing that knowledge domain. For example, the root tag ``cno`` could be used as the root for other domain-specific tags pertaining to computer network operations / cyber threat data. For example:

- Tor nodes: ``cno.infra.anon.tor``
- Anonymous proxies: ``cno.infra.anon.proxy``
- Web servers: ``cno.infra.web``

The ``infra`` element under ``cno`` denotes that these tags all relate to infrastructure. The ``anon`` sub-tag specifies anonymous infrastructure (tor, anonymous proxies, etc.) and so on.

Domain-Specific Assessments
+++++++++++++++++++++++++++

The purpose of analysis is to draw relevant conclusions from the data at hand. The specific analytical conclusions will vary based on the knowledge domain but could include assessments such as “The increase in widget manufacturing due to lower production costs has had a negative effect on the demand for gizmos ” or “The threat group Vicious Wombat is working on behalf of the Derpistan government”.

Those big-picture assessments are made based on numerous smaller assessments (tags) which are themselves based on the facts (nodes) in the hypergraph. However, to build up to those larger assessments, one must start by recording those smaller domain-specific assessments within the Synapse hypergraph.

The folowing examples from the knowledge domain of cyber threat data illustrate the types of assessments that can be recorded using tags:

Threat Clusters
***************

A common practice in threat tracking and cyber security involves determining not only whether an indicator (e.g., a file, domain, IP address, or email address) is malicious, but whether it is part of a **threat cluster.** That is, whether the indicator can be linked to a known set of related activity presumed to be carried out by some (generally unknown) set of malicious actors (a "threat group").

An analyst researching an unknown indicator - such as a newly-identified domain - will evaluate a variety of data to determine whether the domain can be linked to a known threat cluster. This may include:

- whether any malware is associated with the domain
- current and historical domain registration (whois) data
- current and historical domain resolution / DNS data

If the analyst determines that there is sufficient evidence to link the domain to an existing threat cluster, it is helpful to record that assessment. Not only does this make the assessment available to other analysts, it also means that other analysts do not need to spend time evaluating the same or similar data to come to the same conclusion (barring any new data that prompts a re-evaluation of the assessment).

A set of tags can be used to denote that nodes are part of or associated with a given threat cluster, such as:

- ``cno.threat.<cluster>``

The value of ``<cluster>`` may vary depending on an organization’s method to distinguish different clusters (i.e., naming convention, numbering system, etc.)

Third-Party Assessments
***********************

Many commercial organizations conduct their own threat tracking and analysis and publish their research on cyber threats. From blogs to white papers, this type of research commonly includes "indicators of compromise" (hashes, domains, IP addresses, etc. purported to be malicious and / or associated with specific activity) and summarizes the author’s findings. However, these publications rarely contain sufficient data or detail to allow the findings to be fully verified independently.

If you trust Foo Security’s assessment that a set of indicators are in fact associated with the threat group Vicious Wombat, you can simply tag those indicators as such using threat cluster tags similar to the example above and move on. However, many organizations conduct their own analysis to identify and track "threat groups" or to identify and group malware samples into "families". For users or analysts actively engaged in this work, their own analysis (presumably supported by direct access to supporting data / evidence) may be considered "higher fidelity" than analysis published by a third party where the supporting evidence is not available. 

It may be preferable to track these third-party assessments separately and annotate the data with "Foo Security says this is associated with Vicious Wombat" as opposed to "this is Vicious Wombat". This allows you to keep track of what Foo Security says as opposed to what Bar Infosec says. It may also (over time) highlight discrepancies in the collective body of public reporting (which is not closely tracked and rarely, if ever, revised). For example tags could allow you to determine that Foo Security says the domain ``woot.com`` is associated with Vicious Wombat, while Bar Infosec later reported that the domain was associated with Spurious Unicorn. If nothing else, seeing both tags on the same node highlights that these assessments merit further analysis: is one company’s analysis incorrect? Are Vicious Wombat and Spurious Unicorn the same group? Was the domain controlled by two different groups at different times? Is the domain not actually malicious?

A set of tags can be used to annotate "other people’s analysis", such as:

- FireEye claims this is the APT1 threat group: ``aka.feye.thr.apt1``
- ESET claims this is X-Agent malware: ``aka.eset.mal.xagent``
- Trend Micro claims this is part of Operation Wilted Tulip: ``aka.trend.op.wiltedtulip``

Tactics, Techniques, and Procedures (TTPs)
******************************************

The methodologies (sometimes known as tactics, techniques, and procedures or TTPs) that a threat group uses to conduct its activity can provide insight into the group and its operations. Knowledge of past TTPs may help predict future actions or operations. Sets of TTPs observed together may provide a "fingerprint" of a group’s activity. General knowledge of TTPs in current use can help organizations more effectively protect and defend their assets.

"TTP" can cover a broad range of observed activity, from whether a group uses zero-day exploits to the specific packer used to obfuscate a piece of malware. A simple example of a TTP is whether a group uses "masquerading" - imitating a legitimate resource such as a valid domain name or a trusted email sender - to facilitate an attack. A masquerade is a social engineering technique intended to gain the potential victim’s trust, making them more likely to visit a web site or open an email attachment.

An analyst evaluating whether a domain imitates the name of a legitimate company or service for malicious purposes may first note the domain's similarity with that of a known company, and then evaluate additional information such as:

- whether the similar domain is actually registered to the legitimate company (as a less well-known site, or a domain registered for purposes of brand protection).
- whether the similar domain is associated with known malicious activity.
- whether any malicious activity appeared targeted at individuals who would have a personal or professional interest in the legitimate site that the similar domain imitates.

If the analyst determines that the similar domain is not associated with the legitimate site or company, and that the domain appears to have been crafted for malicious use, a tag can be used to note this assessment. For example:

- A node (such as a domain) is meant to imitate a legitimate resource associated with Google: ``cno.ttp.se.masq.google``

Tags as Hypotheses
------------------

Another way to look at tags is as hypotheses. If a tag represents the outcome of an assessment, then every tag can be considered to have an underlying question or hypothesis it is attempting to answer. Making the decision to apply the relevant tag equates to assessing the tag's underlying hypothesis to be true. Making these assessments often involves the judgment of a human analyst; hence evaluating and tagging data within the hypergraph is one of the primary analyst tasks.

Hypotheses may be simple or complex; most often individual tags represent relatively simple concepts that are then used collectively to support (or refute) more complex theories. Because the concept of encoding assessments, judgments, or analytical conclusions within a graph or hypergraph may be unfamiliar to some, a few examples may be helpful.

**Example 1**

The broad cyber threat question "can this newly identified domain be associated with any known threat cluster?" can be thought of as comprised of *n* number of individual hypotheses based on the number of known threat clusters:

- Hypothesis: This domain is associated with Threat Cluster 1.
- Hypothesis: This domain is associated with Threat Cluster 2.
- ...
- Hypothesis: This domain is associated with Threat Cluster n.

If an analyst determines that the domain is associated with Threat Cluster 46, placing a Threat Cluster 46 tag (e.g., ``cno.threat.t46``) on the node for that domain effectively means that the hypothesis "This domain is associated with Threat Cluster 46" has been assessed to be true.

**Example 2**

The criteria used to evaluate whether an indicator is part of a threat cluster may be complex. Tags (and their underlying hypotheses) can also represent concepts that are simpler (easier to evaluate). The use of "masquerading" as a TTP is one example.

Let’s say an analyst comes across the domain ``g00gle.com``, which bears a resemblance to the legitimate ``google.com`` domain. The mere similarity is not enough to determine whether the similar domain is malicious or used for malicious purposes. However, the analyst may have access to additional data (such as a phishing email with a link to a ``g00gle.com`` web site that prompts the user to enter their password). The analyst determines that the domain is malicious and likely intended for credential theft. Applying the tag ``cno.ttp.se.masq.google`` effectively means that the hypothesis "A threat actor created this domain to imitate Google for malicious purposes" has been assessed to be true.

Individual Hypotheses to Broader Reasoning
++++++++++++++++++++++++++++++++++++++++++

More complex hypotheses may not be explicitly annotated within the graph (that is, as tags applied to individual nodes), but may be supported (or refuted) by the presence of individual tags or combinations of tags on sets of nodes.

For example, an analyst tracking Threat Cluster 12 believes (has a hypothesis) that they frequently register domains that imitate technology companies. In the absence of a detailed data modeling and tracking system (such as a Synapse hypergraph), such an assessment is often made based on an analyst’s "impression" of historical Threat Cluster 12 data / domains.

A better way to make this determination based on tracked data and assessments would be to:

- review all of the domains associated with Threat Cluster 12 (i.e., tagged ``cno.threat.t12``)
- determine how many of those domains have ``cno.ttp.se.masq.*`` tags, and
- determine the types of organizations represented by the ``masq`` tags (technology, media, government, etc.)

This allows you to determine the number or percentage of known Threat Cluster 12 domains that represent masquerades, and what types of masquerades they represent, providing a much more concrete basis to evaluate your hypothesis than the recollection of a "subject matter expert" or an impression gleaned from looking at a list of domains.
