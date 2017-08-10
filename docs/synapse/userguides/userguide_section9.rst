Tags - Analytical Model
=======================

While the Synapse data model related to tags is straightforward (consisting of only two forms), the appropriate use of tags for analysis is more complex. Tags can be thought of as being part of an **analytical model** that relies on the Synapse data model, but that:

* Exists independently from the data model (you do not need to write code to implement new tags or design a tag structure).
* Is knowledge domain-specific (tags used for cyber threat analysis will be very different from tags used for biomedical research).
* Is tightly coupled with the specific analytical questions or types of questions the hypergraph is intended to answer (the questions you want to answer should dictate the tags you create and apply).

In short, effective use of Synapse to conduct analysis is dependent on:

* the **data model** (how you define forms to represent data within your knowledge domain).
* the **analytical model** (how you design an effective set of tags to annotate data within your knowledge domain).

A well-designed tag structure should:

* **Represent relevant observations:** tags should annotate assessments and conclusions that are important to your analysis.
* **Facilitate effective analysis:** tags should be structured to allow you to ask meaningful questions of your data.

Tags as Assessments
-------------------

Research and analysis consists of testing theories or hypotheses and drawing conclusions based on available data. Assuming data is initially collected and recorded accurately within a hypergraph, that underlying data (typically encoded in nodes and properties) should not change. However, as you collect more data or different types of data, or as you re-evaluate existing data, your assessment of that data (typically encoded in tags) may change. Nodes and properties are meant to be largely stable; tags are meant to be flexible and evolving.

If a tag represents the outcome of an assessment, then every tag can be considered to have an underlying question or hypothesis it is attempting to answer. Answering this question often involves the judgment of a human analyst; hence evaluating and tagging data within the hypergraph is one of the primary analyst tasks.

Hypotheses may be simple or complex; most often individual tags represent relatively simple concepts that are then used collectively to support (or refute) more complex theories. Because the concept of encoding assessments, judgments, or analytical conclusions within a graph or hypergraph may be unfamiliar to some, a few examples may be helpful.

A common concept in tracking cyber threat data is the idea of determining whether an indicator (a file, domain, IP address, email address, etc.) is part of a "threat cluster" associated with a particular threat group or set of malicious actors. For something to be part of a threat cluster, it must be considered to be **unique** to that threat group – that is, if the indicator (such as a domain) is observed on a network, it can be considered a sure sign that the threat group is present in that network.

An analyst reviewing new threat data – say a piece of malware containing a never-before-observed domain – will try to determine whether the activity can be associated with any known threat group. The broad question "can this be associated with any known group?" can be thought of as comprised of *n* number of individual hypotheses based on the number of known threat groups ("This activity is associated with the threat cluster for Threat Group 1...for Threat Group 2...for Threat Group *n*").

Let's say the analyst determines the activity is related to Threat Group 12 and therefore applies the tag ``tc.t12`` (``tc`` to indicate the “threat cluster” name space, ``t12`` to indicate Threat Group 12) to the malicious domain (``inet:fqdn``). The presence of that tag indicates that the hypothesis "This domain is associated with the threat cluster for Threat Group 12" has been assessed to be true, based on the available data.

The criteria used to evaluate whether an indicator is part of a threat cluster may be complex. Tags (and their underlying hypotheses) can also represent concepts that are much simpler (easier to evaluate).

In tracking cyber threat data, let's say that you want to know how often malicious domains (e.g., domains used in malware communications, or to host phishing or exploit sites) mimic the names of legitimate companies or services, and which companies or services are imitated most often. A tag such as ``mimic.<name_of_company>`` could be used to indicate this.

An analyst evaluating whether a domain mimics the name of a legitimate company or service may first identify some similarity with a known company, and then determine whether the domain is legitimately registered to that company. For example, if the analyst determines that the domain ``g00gle.com`` is **not** a legitimate domain registered to Google, they may apply the tag ``mimic.google`` to the domain. The hypothesis "This domain mimics Google" has been assessed to be true.

More complex hypotheses may not be explicitly annotated within the graph (that is, as individual tags), but may be supported (or refuted) by the presence of other tags or combinations of tags. For example, if your hypothesis is "Threat Group 12 frequently registers domains that imitate technology companies", you could ask Synapse to show you all the domains (``inet:fqdn`` nodes) associated with Threat Group 12 (tagged with ``tc.t12``) and then show you which of those domains have a ``mimic`` tag:

* Comparing the number of mimic domains to the total number of Threat Group 12 domains can indicate how often the group attempts to imitate other services.
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
* Hierarchy #2: ``ask syn:tag:base=us fromtags() +#economics.banking``
(Alternatlely, it is possible to use a regular expression to filter for tags containing "banking", for example, before calling the ``fromtags()`` operators: ``ask syn:tag:base=us +syn:tag~=banking fromtags()``.)

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



_Storm: ../userguides/userguide_section11.html
_Storm: ../userguides/userguide_section11.html

.. _Concepts: ../userguides/userguide_section4.html
__ Concepts_
