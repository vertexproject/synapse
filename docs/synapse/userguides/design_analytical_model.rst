



.. highlight:: none

.. _design-analytical-model:

Design Concepts - Analytical Model
==================================

The ability to use tags effectively to make assessments and facilitate further analysis depends on a well-designed **analytical model** – the set of tags used to annotate data and the structure of those tags. The specific structure used may be highly specific to a given knowledge domain and given research purpose, and a full discussion of the design of a tag structure is beyond the scope of this document. However, the following points should be taken into consideration in designing your analytical model:

- `Tag Hierarchies`_
- `Tag Definitions`_
- `Tag Governance`_
- `Level of Detail`_
- `Flexibility`_
- `Consistency of Use`_

Tag Hierarchies
---------------

The structure of a tag hierarchy is an important consideration, as the "order" of tag elements can affect the types of analytical questions you can most easily answer. Because hierarchies are generally structured from "less specific" to "more specific", the hierarchy you choose affects how (or whether) you can narrow your focus effectively. Consider whether the structure you create allows you to increase specificity in a way that is analytically relevant or meaningful to the questions you’re trying to answer.

For example, let’s say you are storing copies of articles from various news feeds within a Cortex (i.e., as ``media:news`` nodes). You want to use tags to annotate the subject matter of the articles. Two possible options would be:

**Hierarchy #1**

.. parsed-literal::
  
  <country>.<topic>.<subtopic>.<subtopic>:
    us.economics.trade.gdp
    us.economics.trade.deficit
    us.economics.banking.lending
    us.economics.banking.regulatory
    us.politics.elections.national
    france.politics.elections.national
    france.politics.elections.local
    china.economics.banking.lending

**Hierarchy #2**

.. parsed-literal::
  
  <topic>.<subtopic>.<subtopic>.<country>:
    economics.trade.gdp.us
    economics.trade.deficit.us
    economics.banking.lending.us
    economics.banking.regulatory.us
    politics.elections.national.us
    politics.elections.national.france
    politics.elections.local.france
    economics.banking.lending.china

Using Synapse's Storm (:ref:`storm-ref-intro`) query language, it is easy to ask about nodes that have a specific tag (``storm #<tag>``). Storm also allows you to ask about tag nodes (``syn:tag`` forms) in various ways based on their properties, and then pivot from the ``syn:tag`` nodes to nodes that have those tags applied. These latter queries are still feasible but are more complex.

The example questions below illustrate how the choice of hierarchy makes it easier (or harder) to ask certain questions.

**Example 1:** "Show me all the articles related to France":

- Hierarchy #1:
  
  ``storm #france``

- Hierarchy #2:
  
  ``storm syn:tag:base=france -> *``

**Example 2:** "Show me all the articles on banking within the US":

- Hierarchy #1:
  
  ``storm #us.economics.banking``

- Hierarchy #2:
  
  ``storm syn:tag^=economics.banking +syn:tag:base=us -> *``

**Example #3:** "Show me all the articles about global trade":

- Hierarchy #1:
  
  ``storm syn:tag:base=trade -> *``

- Hierarchy #2:
  
  ``storm #economics.trade``

**Example #4:** "Show me all the articles about national elections":

- Hierarchy #1:
  
  ``storm syn:tag:base=national -> *``

- Hierarchy #2:
  
  ``storm #politics.elections.national``

Hierarchy #1 makes it easier to ask the first two questions; Hierarchy #2 makes it easier to ask the last two questions. As you can see, choosing one hierarchy over the other doesn’t necessarily prevent you from asking certain questions – if you choose the first hierarchy, you can still ask about global trade issues. However, asking that question (structuring an appropriate Storm query) is a bit harder, and the potential complexity of a query across a poorly-structured set of tags increases as both the tag depth and the total number of tags increases.

While the differences in query structure may seem relatively minor, structuring your tags to make it "easier" to ask the questions that are most important to you has two important effects:

- **More efficient for Synapse to return the requested data:** in general, lifting data by tag will be more efficient than lifting tag nodes by property and then pivoting from tag nodes to nodes that have those tags. Efficiency may be further impacted if additional operations (filtering, additional pivots) are performed on the results. While these performance impacts may be measured in seconds at most, they still impact an analyst’s workflow.

- **Simpler for analysts to remember:** you want analysts to spend their time analyzing data, not figuring out how to ask the right question (craft the right query) to retrieve the data in the first place. This has a much bigger impact on an analyst’s workflow.

Neither hierarchy is right or wrong; which is more suitable depends on the types of questions you want to answer. If your analysis focuses primarily on news content within a particular geography, the first option (which places "country" at the root of the hierarchy) is probably more suitable. If your analysis focuses more on global geopolitical topics, the second hierarchy is probably better. As a general rule, the analytical focus that you "care about most" should generally go at the top of the hierarchy in order to make it easier to ask those questions.

Tag Definitions
---------------

The form of a tag (``syn:tag``) allows both short-form and long-form definitions to be stored directly on the tag’s node. Consistently using these definition fields to clearly define a tag’s meaning is extremely helpful for analysis.

Synapse's forms (the data model) combined with the set of associated tags (analytical model) should be able to convey key relationships and assessments in a concise way. In other words, understanding nodes and tags is meant to be simpler (and faster) than reading a long form report about why an analyst interprets X to mean Y.

That said, a data model is still an abstraction: it trades the precision and detail of long-form reporting for the power of a consistent model and programmatic access to data and analysis. Within this framework, tags are the "shorthand" for analytical observations and annotations. Nuances of meaning that may be essential for proper analysis get lost if a complex observation is reduced to the tag ``foo.bar.baz``. There is a risk that different analysts may interpret and use the same tag in different ways, particularly as the number of analysts using the system increases. The risk also increases as the number of tags increases, as there may be hundreds or even thousands of tags being used to annotate the data.

By convention, the ``:title`` secondary property is often used for a "short" definition for the tag – a phrase or sentence at most – while ``:doc`` is used for a detailed definition to more completely explain the meaning of a given tag. The idea is that ``:title`` would be suitable to be exposed via an API or UI as a simple definition (such as a label or mouse-over), while ``:doc`` would be suitable for display on request by a user who wanted more detailed information or clarification.

Storing a tag’s definition directly within the Synapse data model helps to make Synapse "self-documenting": an analyst can view the tag’s definition at any time directly within Synapse simply by viewing the tag node’s properties (``syn:tag = <tag>``). There is no need to refer to an external application or dictionary to look up a tag’s precise meaning and appropriate use.

Tag Governance
--------------

Because tags are simply nodes, any user with the appropriate permissions can create a new tag. On one hand, this ability to create tags on the fly makes tags extremely powerful, flexible, and convenient for analysts – they can create annotations to reflect their observations as they are conducting analysis, without the need to wait for code changes or approval cycles.

However, there is also risk to this approach, particularly with large numbers of analysts, as analysts may create tags in an uncoordinated and haphazard fashion. The creation of arbitrary (and potentially duplicative or contradictory) tags can work against effective analysis.

A middle ground between tag free-for-all and tightly-enforced change management for tags is usually the best approach. It is useful for an analyst to be able to create a tag on demand to record an observation in the moment. However, it is also helpful to have some type of regular governance or review process to ensure the tags are being used in a consistent manner and that any newly created tags fit appropriately into the overall analytical model.

This governance and consistency is important across all analysts using a specific Cortex, but is especially important within a broader community. If you plan to exchange data, analysis, or annotations with other groups (each with their own Cortex), you should use an agreed-upon, consistent data model as well as an agreed-upon set of tags.

Level of Detail
---------------

Tag hierarchies can be arbitrarily deep. If one function of hierarchies is to represent an increasing level of detail, then deep hierarchies have the potential to represent extremely fine-grained analytical observations.

More detail is often better; however, tag hierarchies should reflect the level of detail that is relevant for your analysis, and no more. That is, the analysis being performed should drive the set of tags being used and the level of detail they support. (Contrast that approach with taking an arbitrary taxonomy and using it to create tags without consideration for the taxonomy’s relevance or applicability.) Not only is an excess of detail potentially unnecessary to the analysis at hand, it can actually create more work and be detrimental to the analysis you are trying to conduct.

Tags typically represent an analytical assertion, which means in most cases a human analyst needs to evaluate the data, make an assessment, and subsequently annotate data with the appropriate tag(s). Using an excessive number of tags or excessively detailed tags means an analyst needs to do more work (keystrokes or mouse clicks) to annotate the data. There is also a certain amount of overhead associated with tag creation itself, particularly if newly created tags need to be reviewed for governance, or if administrative tasks (such as ensuring tags have associated definitions) need to be performed.

More importantly, while the act of applying a tag to a node may be relatively easy, the analytical decision to apply the tag often requires careful review and evaluation of the evidence. If tags are overly detailed, representing shades of meaning that aren’t really relevant, analysts may get bogged down splitting hairs – worrying about whether tag A or tag B is more precise or appropriate when that distinction doesn’t matter to the analysis at hand. In that situation, the analysis is being driven by the overly detailed tags, instead of the tag structure being driven by the analytical need. Where detail is necessary or helpful it should be used; but beware of becoming overly detailed where it isn’t relevant, as the act of annotating can take over from real analysis.

Flexibility
-----------

Just as a good data model will evolve and adapt to meet changing needs, the analytical model represented by a set of tags or tag hierarchies should do the same. No matter how well-thought-out your tag structure is, you will identify exceptions, edge cases, and observations you didn’t realize you wanted to capture. To the extent possible, your tag structure should be flexible enough to account for future changes.

Note that it is relatively easy to "bulk change" tags (to decide a tag should have a different name or should exist within a different location in the tag hierarchy, and to re-tag existing nodes with the new tag) **as long as the change is one-to-one.** That is, while the tag name may change, the meaning of the tag does not, so that everything tagged with the old name should remain tagged with the new name. (See the Storm :ref:`storm-movetag` command for details.)

For example, if you decide that ``foo.bar.baz.hurr`` and ``foo.bar.baz.derp`` provide too much granularity and should both be rolled up into ``foo.bar.baz``, the change is relatively easy. Similarly, if you create the tag ``foo.bar`` and later decide that tag should reside under a top-level tag ``wut``, you can "rename" (move) ``foo.bar`` to ``wut.foo.bar`` and re-tag the relevant nodes.

This flexibility provides a safety net when designing tag hierarchies, as it allows some freedom to "not get it right" the first time. Particularly when implementing a new tag or set of tags, it can be helpful to test them out on real-world data before finalizing the tags or tag structure. The ability to say "if we don’t get it quite right we can rename it later" can free up analysts or developers to experiment.

It is harder to modify tags through means such as "splitting" tags. For example, if you create the tag ``foo.bar`` and later decide that ``bar`` should really be tracked as two variants (``foo.bar.um`` and ``foo.bar.wut``), it can be painstaking to separate those out, particularly if the set of nodes currently tagged ``foo.bar`` is large. For the sake of flexibility it is often preferable to err on the side of "more detail", particularly during early testing.

Consistency of Use
------------------

Creating a well-thought out set of tags to support your analytical model is ineffective if those tags aren’t used consistently – that is, by a majority of analysts across a majority of relevant data. It’s true that 100% visibility into a given data set and 100% analyst review and annotation of that data is an unrealistic goal. However, for data and annotations that represent your most pressing analytical questions, you should strive for as much completeness as possible. Looked at another way, inconsistent use of tags can result in gaps that can skew your assessment of the data. At best, this can lead to the inability to draw meaningful conclusions; at worst, to faulty analysis.

This inconsistency often occurs as both the number of analysts and the number of tags used for analysis increase. The larger the team of analysts, the more difficult it is for that team to work closely and consistently together. Similarly, the more tags available to represent different assessments, the fewer tags an analyst can work with and apply within a given time frame. In both cases, analysts may tend to drift towards analytical tasks that are most immediately relevant to their work or most interesting to them – thus losing sight of the collective analytical goals of the entire team.

Consider an example of tracking Internet domains that masquerade as legitimate companies for malicious purposes. If some analysts are annotating this data but others are not, your ability to answer questions about this data is skewed. Let’s say Threat Cluster 12 is associated with 200 domains, and 173 of them imitate real companies, but only 42 have been annotated with "masquerade" tags (``cno.ttp.se.masq.*``). If you try to use the data to answer the question "does Threat Cluster 12 consistently register domains that imitate valid companies?", your assessment is likely to be "no" based on the incompletely annotated data. There are gaps in your analysis because the information to answer this question has only been partially recorded.

As the scope of analysis within a Cortex increases, it is essential to recognize these gaps as a potential shortcoming that may need to be addressed. Options include establishing policy around which analytical tasks (and associated observations) are essential (perhaps even required) and which are secondary ("as time allows"); or designating individual analysts to be responsible for particular analytical tasks. Where automation can be leveraged, Synapse’s automation tools such as triggers (:ref:`syn-trigger`), :ref:`syn-cron` jobs, or stored queries may also help to ensure consistency.
