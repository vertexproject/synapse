.. highlight:: none

Tags - Analytical Model
=======================

While the Synapse data model related to tags is straightforward (consisting of only two forms), the appropriate use of tags for analysis is more complex. Tags can be thought of as being part of an **analytical model** that relies on the Synapse data model, but that:

* Exists independently from the data model (you do not need to write code to implement new tags or design a tag structure).
* Is knowledge domain-specific (tags used for cyber threat analysis will be very different from tags used for biomedical research).
* Is tightly coupled with the specific analytical questions or types of questions the hypergraph is intended to answer (the questions you want to answer should dictate the tags you create and apply).

In short, effective use of Synapse to conduct analysis is dependent on:

* the **data model** (how you define forms to represent data within your knowledge domain).
* the **analytical model** (how you design a set of tags to annotate data within your knowledge domain).

A well-designed tag structure should:

* **Represent relevant observations:** tags should annotate assessments and conclusions that are important to your analysis.
* **Facilitate effective analysis:** tags should be structured to allow you to ask meaningful questions of your data.

Tags as Assessments
-------------------

Research and analysis consists of testing theories or hypotheses and drawing conclusions based on available data. Assuming data is initially collected and recorded accurately within a hypergraph, that underlying data (typically encoded in nodes and properties) should not change. However, as you collect more data or different types of data, or as you re-evaluate existing data, your assessment of that data (typically encoded in tags) may change. Nodes and properties are meant to be largely stable; tags are meant to be flexible and evolving.

If a tag represents the outcome of an assessment, then every tag can be considered to have an underlying question or hypothesis it is attempting to answer. Answering this question often involves the judgment of a human analyst; hence evaluating and tagging data within the hypergraph is one of the primary analyst tasks.

Hypotheses may be simple or complex; most often individual tags represent relatively simple concepts that are then used collectively to support (or refute) more complex theories. Because the concept of encoding assessments, judgments, or analytical conclusions within a graph or hypergraph may be unfamiliar to some, a few examples may be helpful.

*Example 1*

A common concept in tracking cyber threat data is the idea of determining whether an indicator (a file, domain, IP address, email address, etc.) is part of a "threat cluster" associated with a particular threat group or set of malicious actors. For something to be part of a threat cluster, it must be considered to be **unique** to that threat group – that is, if the indicator (such as a domain) is observed on a network, it can be considered a sure sign that the threat group is present in that network.

An analyst reviewing new threat data – say a piece of malware containing a never-before-observed domain – will try to determine whether the activity can be associated with any known threat group. The broad question "can this be associated with any known group?" can be thought of as comprised of *n* number of individual hypotheses based on the number of known threat groups ("This activity is associated with the threat cluster for Threat Group 1...for Threat Group 2...for Threat Group *n*").

Let's say the analyst determines the activity is related to Threat Group 12 and therefore applies the tag ``tc.t12`` (``tc`` to indicate the “threat cluster” name space, ``t12`` to indicate Threat Group 12) to the malicious domain (``inet:fqdn``). The presence of that tag indicates that the hypothesis "This domain is associated with the threat cluster for Threat Group 12" has been assessed to be true, based on the available data.

*Example 2*

The criteria used to evaluate whether an indicator is part of a threat cluster may be complex. Tags (and their underlying hypotheses) can also represent concepts that are much simpler (easier to evaluate).

In tracking cyber threat data, let's say that you want to know how often malicious domains (e.g., domains used in malware communications, or to host phishing or exploit sites) mimic the names of legitimate companies or services, and which companies or services are imitated most often. A tag such as ``mimic.<name_of_company>`` could be used to indicate this.

An analyst evaluating whether a domain mimics the name of a legitimate company or service may first identify some similarity with a known company, and then determine whether the domain is legitimately registered to that company. For example, if the analyst determines that the domain ``g00gle.com`` is **not** a legitimate domain registered to Google, they may apply the tag ``mimic.google`` to the domain. The hypothesis "This domain mimics Google" has been assessed to be true.

More complex hypotheses may not be explicitly annotated within the graph (that is, as individual tags), but may be supported (or refuted) by the presence of other tags or combinations of tags. For example, if your hypothesis is "Threat Group 12 frequently registers domains that imitate technology companies", you could ask Synapse to show you all the domains (``inet:fqdn`` nodes) associated with Threat Group 12 (tagged with ``tc.t12``) and then show you which of those domains have a ``mimic`` tag:

* Comparing the number of ``mimic`` domains to the total number of Threat Group 12 domains can indicate how often the group attempts to imitate other services.
* The companies or services reflected in the ``mimic`` tags can indicate the types of organizations the group imitates.

This information will help you evaluate whether or not your hypothesis is true based on currently available data. A corresponding Storm_ query to help evaluate the above would be:

``cli> ask inet:fqdn*tag=tc.t12 +#mimic``

Tag Considerations
------------------

The ability to use tags effectively to make assessments and facilitate further analysis depends on a well-designed analytical model – the set of tags used to annotate data, and the structure of those tags. The specific structure used may be highly specific to a given knowledge domain and given research purpose. However, the following points should be taken into consideration in designing your analytical model.

**Tag Hierarchies**

The structure of a tag hierarchy is an important consideration, as the “order” of the tags can affect the types of analytical questions you can most easily answer. Because hierarchies are generally structured from “less specific” to “more specific”, the hierarchy you choose affects how (or whether) you can narrow your focus effectively. **Consider whether the structure you create allows you to increase specificity in a way that is analytically relevant or meaningful to the questions you’re trying to answer.**

For example, let’s say you are storing copies of articles from various news feeds within a Synapse Cortex. You want to use tags to annotate the subject matter of the articles. Two possible options would be:

*Hierarchy #1* ::
  
  <country>.<topic>.<subtopic>.<subtopic>:
    us.economics.trade.gdp
    us.economics.trade.deficit
    us.economics.banking.lending
    us.economics.banking.regulatory
    us.politics.elections.national
    france.politics.elections.national
    france.politics.elections.local
    china.economics.banking.lending
  
*Hierarchy #2* ::
  
  <topic>.<subtopic>.<subtopic>.<country>:
    economics.trade.gdp.us
    economics.trade.deficit.us
    economics.banking.lending.us
    economics.banking.regulatory.us
    politics.elections.national.us
    politics.elections.national.france
    politics.elections.local.france
    economics.banking.lending.china
  
Using Synapse's Storm_ query language, it is easy to ask about nodes that have a specific tag (``ask #<tag>``). Storm also allows you to ask about tag nodes (``syn:tag`` forms) that share a common base element (``:base`` secondary property) and then locate all nodes that have any of those tags. While this is a slightly more complex query, it is not overly difficult (``ask syn:tag:base=<value> fromtags()``).

Based on this, you can see how the choice of hierarchy makes it easier (or harder) to ask certain questions. (**Note:** examples simplified for discussion purposes. See the Storm reference and Storm tutorial for detailed information on using Storm.)

“Show me all the articles related to France”:

* Hierarchy #1: ``ask #france``
* Hierarchy #2: ``ask syn:tag:base=france fromtags()``

“Show me all the articles on to banking within the US”:

* Hierarchy #1: ``ask #us.economics.banking``
* Hierarchy #2: ``ask syn:tag:base=us fromtags() +#economics.banking`` or
  ``ask syn:tag:base=us +syn:tag~=banking fromtags()``

“Show me all the articles about global trade”:

* Hierarchy #1: ``ask syn:tag:base=trade fromtags()``
* Hierarchy #2: ``ask #economics.trade``

“Show me all the articles about national elections”:

* Hierarchy #1: ``ask syn:tag:base=national fromtags()``
* Hierarchy #2: ``ask #politics.elections.national``

Hierarchy #1 makes it easier to ask the first two questions; Hierarchy #2 makes it easier to ask the last two questions. As you can see, choosing one hierarchy over the other doesn’t necessarily **prevent** you from asking certain questions – if you choose the first hierarchy, you can still ask about global trade issues. However, asking that question (structuring an appropriate Storm query) is a bit harder, and the potential complexity of a query across a poorly-structured set of tags increases as both the tag depth and the total number of tags increases.

While the differences in query structure may seem relatively minor, structuring your tags to make it “easier” to ask questions has two important effects:

* **More efficient / performant for Synapse to return the requested data:** in general, lifting data by tag will be more efficient than lifting nodes by property and then pivoting from tag nodes to nodes that have those tags. Efficiency may be further impacted if additional operations (filtering, additional pivots) are performed on the results. While these performance impacts may be measured in fractions of seconds or seconds at most, they still impact an analyst’s workflow.
* **Simpler for analysts to remember:** you want analysts to spend their time analyzing data, not figuring out how to ask the right question to retrieve the data in the first place. This has a much bigger impact on an analyst’s workflow.

Neither hierarchy is right or wrong; which is more **suitable** depends on the types of questions you want to answer. If your analysis focuses primarily on news content within a particular geography, the first option (which places "country" at the root of the hierarchy) is probably more suitable. If your analysis focuses more on global geopolitical topics, the second hierarchy is probably better. As a general rule, **the analytical focus that you "care about most" should generally go at the top of the hierarchy in order to make it “easier” to ask those questions.**

**Tag Definitions**

The form of a tag (``syn:tag``) allows both short-form and long-form definitions to be stored directly on the tag's node. Consistently using these definition fields to clearly define a tag's meaning is extremely helpful for analysis.

Recall from `Data Model – Concepts`__ that a well-designed Synapse data model should be "self-evident": the structure of the hypergraph (data model) combined with the set of associated tags (analytical model) is able to convey key relationships and assessments in a concise way. In other words, understanding nodes and tags is meant to be simpler (and faster) than reading a long form report about why an analyst interprets X to mean Y.

That said, a data model is still an abstraction: it trades the precision and detail of long-form reporting for the power of a consistent model and programmatic access to data and analysis. Within this framework, tags are the "shorthand" for analytical observations and annotations. Nuances of meaning that may be essential for proper analysis get lost if a complex observation is reduced to the tag ``foo.bar.baz``. There is a risk that different analysts may interpret and use the same tag in different ways, particularly as the number of analysts using the system increases. The risk also increases as the number of tags increases, as there may be hundreds or even thousands of tags being used to annotate the data.

By convention, the ``:title`` secondary property has been used for a "short" definition for the tag – a phrase or sentence at most – while ``:doc`` has been used for a detailed definition to more completely explain the meaning of a given tag. The idea is that ``:title`` would be suitable to be exposed via an API or UI as a simple definition (such as a label or hover-over), while ``:doc`` would be suitable for display on request by a user who wanted more detailed information or clarification.

Storing a tag's definition directly within the Synapse data model helps to make Synapse "self-documenting": an analyst can view the tag’s definition at any time directly within Synapse simply by viewing the tag node’s properties (``ask --props syn:tag=<tag>``). There is no need to refer to an external application or dictionary to look up a tag's precise meaning and appropriate use.

The same principle applies to ``syn:tagform`` ("tagform") nodes, which were created to document the precise meaning of a tag **when it is applied to a specific form** (node type). Tagforms support use cases where a tag embodying a particular concept may still have subtle differences in meaning when the tag is applied to different node types – say an ``inet:ipv4`` vs. an ``inet:fqdn``. While these nuances could be documented on the ``syn:tag`` node itself, it could make for a very lengthy definition. In those cases it may be preferable to create ``syn:tagform`` nodes to separately document the various meanings for a given tag / form combination.

**Tag Governance**

Because tags are simply nodes, any user with the ability to create nodes can create a new tag. On one hand, this ability to create tags on the fly makes tags extremely powerful, flexible, and convenient for analysts – they can create annotations to reflect their observations as they are conducting analysis, without the need to wait for code changes or approval cycles.

However, there is also risk to this approach, particularly with large numbers of analysts, as analysts may create tags in an uncoordinated and haphazard fashion. The creation of arbitrary (and potentially duplicative or contradictory) tags can work against effective analysis.

A middle ground between tag free-for-all and tight tag restrictions ("no new tags without prior approval") is usually the best approach. It is useful for an analyst to be able to create a tag on demand to record an observation in the moment. However, it is also helpful to have some type of regular governance or review process to ensure the tags are being used in a consistent manner and that any newly created tags fit appropriately into the overall analytical model.

This governance and consistency is important across all analysts using a specific instance of Synapse, but is especially important within a broader community. If you plan to exchange data, analysis, or annotations with other groups with their own instances of Synapse, you should use an agreed-upon, consistent data model as well as an agreed-upon set of tags.

**Level of Detail**

Tag hierarchies can be arbitrarily deep. If one function of hierarchies is to represent an increasing level of detail, then deep hierarchies have the potential to represent extremely fine-grained analytical observations.

More detail is often better; however, tag hierarchies should reflect the level of detail that is relevant for your analysis, and no more. That is, the analysis being performed should drive the set of tags being used and the level of detail they support. (Contrast that approach with taking an arbitrary taxonomy and using it to create tags without consideration for the taxonomy's relevance or applicability.) Not only is an excess of detail potentially unnecessary to the analysis at hand, it can actually create more work and be detrimental to the analysis you are trying to conduct.

Tags typically represent an analytical assertion, which means in most cases a human analyst needs to evaluate the data, make an assessment, and subsequently annotate data with the appropriate tag(s). Using an excessive number of tags or excessively detailed tags means an analyst needs to do more work (keystrokes or mouse clicks) to annotate the data. There is also a certain amount of overhead associated with tag creation itself, particularly if newly created tags need to be reviewed for governance, or if administrative tasks (such as ensuring tags have associated definitions) need to be performed.

More importantly, while the physical act of applying a tag to a node may be "easy", the analytical decision to apply the tag often requires careful review and evaluation of the evidence. If tags are overly detailed, representing shades of meaning that aren't really relevant, analysts may get bogged down splitting hairs – worrying about whether tag A or tag B is more precise or appropriate. In that situation, the analysis is being driven by the overly detailed tags, instead of the tag structure being driven by the analytical need. Where detail is necessary or helpful it should be used; but beware of becoming overly detailed where it isn't relevant, as the act of annotating can take over from real analysis.

**Flexibility**

Just as a good data model will evolve and adapt to meet changing analytical needs, the analytical model represented by a set of tags or tag hierarchies should be able to evolve and adapt. No matter how well-thought-out your tag structure is, you will identify exceptions, edge cases, and observations you didn't realize you wanted to capture. To the extent possible, your tag structure should be flexible enough to account for future changes.

Note that it is relatively easy to "bulk change" tags (to decide a tag should have a different name or structure, and to re-tag existing nodes with the new tag) as long as the change is one-to-one. That is, while the tag name may change, the meaning of the tag does not, so that everything tagged with the old name should remain tagged with the new name.

For example, if you decide that ``foo.bar.baz.hurr`` and ``foo.bar.baz.derp`` provide too much granularity and should both be rolled up into ``foo.bar.baz``, the change is relatively easy. Similarly, if you create the tag ``foo.bar`` and later decide that tag should reside under a top-level tag ``wut``, you can rename ``foo.bar`` to ``wut.foo.bar`` and re-tag the relevant nodes. (**Note:** Changing the tags is still a manual process as Synapse does not currently support “mass renaming” of tags. However, it is relatively straightforward to lift all nodes that have a given tag, apply the new “renamed” tag to all the nodes, and then delete the ``syn:tag`` node for the original tag, which will also remove the old tag from any nodes.)

This flexibility provides a safety net when designing tag hierarchies, as it allows some freedom to "not get it right" the first time. Particularly when implementing a new tag or set of tags, it can be helpful to test them out on real-world data before finalizing the tags or tag structure. The ability to say "if we don't get it quite right we can rename it later" can free up analysts or developers to experiment.

It is harder to modify tags through means such as "splitting" tags. For example, if you create the tag ``foo.bar`` and later decide that ``bar`` should really be tracked as two variants (``foo.bar.um`` and ``foo.bar.wut``), it can be painstaking to separate those out, particularly if the set of nodes currently tagged ``foo.bar`` is large. For the sake of flexibility it is often preferable to err on the side of "more detail", particularly during early testing.

**Consistency of Use**

Creating a well-thought out set of tags to support your analytical model is ineffective if those tags aren't used consistently – that is, by a majority of analysts across a majority of relevant data. 100% visibility into a given data set and 100% analyst review and annotation of that data is an unrealistic goal; but for data and annotations that represent your most pressing analytical questions, you should strive for as much completeness as possible. Looked at another way, inconsistent use of tags can result in gaps that can skew your assessment of the data. At best, this can lead to the inability to draw conclusions; at worst, to faulty analysis.

This inconsistency often occurs as both the number of analysts and the number of tags used for analysis increase. The larger the team of analysts, the more difficult it is for that team to work closely and consistently together. Similarly, the more tags available to represent different assessments, the fewer tags an analyst can work with and apply within a given time frame. In both cases, analysts may tend to "drift" towards analytical tasks that are most immediately relevant to their work, or most interesting to them – thus losing sight of the collective analytical goals of the entire team.

Consider the example above of tracking Internet domains that mimic legitimate companies. If some analysts are annotating this data but others are not, your ability to answer questions about this data is skewed. Let’s say Threat Group 12 has registered 200 domains, and 173 of them imitate real companies, but only 42 have been annotated with ``mimic`` tags. If you try to use the data to answer the question "does Threat Group 12 consistently register domains that imitate valid companies?", your assessment is likely to be "no" based on the incompletely annotated data. There are gaps in your analysis because the information to answer this question has only been partially recorded.

As the scope of analysis within a given instance of Synapse increases, it is essential to recognize these gaps as a potential shortcoming that may need to be addressed. Options include establishing policy around which analytical tasks (and associated observations) are essential (perhaps even required) and which are secondary ("as time allows"); or designating individual analysts to be responsible for particular analytical tasks.

**Tag Example**

It may be helpful to walk through an example of designing a tag structure. While somewhat simplified, it illustrates some of the considerations taken into account.

Internet domains (``inet:fqdn``) used for malicious activity are often taken over by security researchers in a process known as "sinkholing". The security firm takes control of the domain, either after it expires or in coordination with a domain registrar, and updates the domain's DNS A record to point to the IP address of a server controlled by the security firm. This allows the security firm to help identify (and ideally notify) victims who are attempting to communicate with the malicious domain. It may also provide insight into the individuals or organizations being targeted by the malicious actors.

The process of sinkholing also requires supporting infrastructure used by the security firm. This typically includes (at minimum):

* The DNS name servers (``inet:fqdn``) used to resolve the sinkholed domains.
* The IP address(es) (``inet:ipv4``) the name servers resolve to.
* The IP address(es) that the sinkholed domains resolve to.
* Any email address(es) (``inet:email``) used by the security firm to register the sinkholed domains.

For cyber threat data purposes, it is useful to know when a domain has been "sinkholed" and is no longer under direct control of a threat group. It is also useful to identify sinkhole infrastructure, which can then be used to identify other sinkholed domains.

All of the objects listed above are associated with sinkhole operations, so one option would be to simply use a single tag ``sinkhole`` (or ``sink`` for short, if you want to save on keystrokes) to denote they are associated with this activity. However, a single tag is not useful if you want to be able to distinguish (and ask about) sinkholed domains separately from legitimate domains associated with the security firm's sinkhole name servers.

A second set of tag elements can be used in combination with ``sink`` to distinguish these different components:

* ``dom`` – the sinkholed domain
* ``ns`` – the name server used to resolve the domain
* ``nsip`` – the name server IP address
* ``domip`` – the sinkhole domain IP address
* ``reg`` – the email used to register the sinkhole domain

Use of a second tag element helps draw better distinctions among the different components, but creates a larger number of tags. However, the sinkholed domain and its IP (as well as the sinkhole name server and its IP) can be considered two aspects of the same concept (“sinkhole domain” and “sinkhole name server”). This could allow you to consolidate some of the tags because the combination of tag plus form allows you to distinguish between "sinkholed domains" (``inet:fqdn``) and "IP addresses hosting sinkholed domains" (``inet:ipv4``) even if you use the same tag for both:

* ``dom`` – a sinkholed domain or the IP address the domain resolves to
* ``ns`` – a sinkhole name server or the IP address the name server resolves to
* ``reg`` – the email used to register the sinkhole domain

Another consideration is the "order" in which to structure these elements. Does ``dom.sink`` make more sense, or ``sink.dom``?

Placing ``dom`` (and ``ns`` and ``reg``) first makes sense if, in your analysis, you are most interested in domains (in general) followed by sinkholed domains (in particular). In this case, the purpose is to track sinkhole operations (in general) and then to be able to distinguish among the different types of infrastructure associated with these operations; so ``sink.dom`` makes more sense to allow you to go from "more general" to "more specific". As a small tweak, because the term "sinkhole" is widely recognized within the security community, changing ``sink.dom`` to ``sink.hole`` may be a bit more intuitive.

Additional information that may be interesting to note is the specific organization responsible for the sinkholed domains and associated infrastructure. In some cases it may be possible to identify the responsible organization (through domain registration records or reverse IP lookups). An additional optional element ``<org_name>`` could be placed at the end of the tag for cases where the organization is known (e.g., ``sink.hole.kaspersky`` for Kaspersky Lab).

That gives you the following tag structure::
  
  sink
  sink.hole
  sink.ns
  sink.reg
  sink.hole.kaspersky
  sink.hole.microsoft
  sink.ns.microsoft
  
...etc.

This structure allows you to use Storm to ask questions such as:

“Show me all of the domains sinkholed by Kaspersky”:

* ``ask inet:fqdn*tag=sink.hole.kaspersky``

“Show me all of the IP addresses associated with sinkhole name servers”:

* ``ask inet:ipv4*tag=sink.ns``

“Show me all of the Threat Group 12 domains sinkholed by Microsoft”:

* ``ask inet:fqdn*tag=sink.hole.microsoft +#tc.t12``

For each of these tags, the corresponding ``syn:tag`` nodes can be given a definition (secondary property ``:title`` and / or ``:doc``) within Synapse. Since we are using ``sink.hole`` and ``sink.ns`` with two different node types (``inet:fqdn`` and ``inet:ipv4``), we can also optionally create ``syn:tagform`` nodes with custom definitions for the meaning of the tag when used on each type of node.

A ``syn:tag`` node might look like this::
  
  cli> ask --props syn:tag=sink.hole
  
  syn:tag = sink.hole
      :base = hole
      :depth = 1
      :doc = A malicious domain that has been sinkholed, or an IP address to which sinkholed domains resolve.
      :title = A sinkholed domain or associated IP address
      :up = sink
  (1 results)

An optional ``syn:tagform`` node representing ``sink.hole`` specifically when applied to ``inet:ipv4`` nodes might look like this::
  
  cli> ask --props syn:tagform:tag=sink.hole +syn:tagform:form=inet:ipv4
  
   syn:tagform = 6343cfbdb736d988a72801be48ea07e2
      :doc = An IP address used as the DNS A record for a sinkholed domain.
      :form = inet:ipv4
      :tag = sink.hole
      :title = IP address of a sinkholed domain
  (1 results)


.. _Storm: ../userguides/userguide_section11.html

.. _Concepts: ../userguides/userguide_section4.html
__ Concepts_

