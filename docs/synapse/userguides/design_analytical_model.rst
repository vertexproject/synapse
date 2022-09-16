.. highlight:: none

.. _design-analytical-model:

Design Concepts - Analytical Model
==================================

The tag hierarchies (tag trees) that you use to annotate data reprsent your **analytical model**. Your ability to
conduct meaningful analysis depends in part on whether your analytical model is well-designed to meet your needs.
The tags and tag trees that work best for you may be different from those that work well for another organization.

A full discussion of tag tree design is beyond the scope of this document. However, the following points should be taken into consideration in designing your tags and associated analytical model:

- `Tag Trees`_
- `Tag Definitions`_
- `Tag Management`_
- `Level of Detail`_
- `Flexibility`_
- `Precision`_
- `Consistency of Use`_

Tag Trees
---------

The structure of a tag tree is an important consideration because the order of tag elements can affect the types of
analysis questions you can most easily answer. Because tag trees generally move from "less specific" to "more specific",
the structure you choose affects how (or whether) you can narrow your focus effectively. The structure you create should
allow you to increase specificity in a way that is meaningful to the questions you’re trying to answer.

For example, let’s say you are storing copies of articles from various news feeds within Synapse (i.e., as ``media:news``
nodes). You want to use tags to annotate the subject matter of the articles. Two possible options would be:

**Tag Tree #1**

::
  
  <country>.<topic>.<subtopic>.<subtopic>:
    us.economics.trade.gdp
    us.economics.trade.deficit
    us.economics.banking.lending
    us.economics.banking.regulatory
    us.politics.elections.national
    france.politics.elections.national
    france.politics.elections.local
    china.economics.banking.lending

**Tag Tree #2**

::
  
  <topic>.<subtopic>.<subtopic>.<country>:
    economics.trade.gdp.us
    economics.trade.deficit.us
    economics.banking.lending.us
    economics.banking.regulatory.us
    politics.elections.national.us
    politics.elections.national.france
    politics.elections.local.france
    economics.banking.lending.china

Using Synapse's Storm (:ref:`storm-ref-intro`) query language, it is easy to ask about nodes that have a specific tag
(``#my.tag``). With Storm you can also ask about tag nodes (``syn:tag = my.tag``) in various ways based on their properties,
and then pivot from the ``syn:tag`` nodes to nodes that have those tags applied. These latter queries are not difficult but
may be less intuitive in practice.

The example questions below illustrate how your choice of tag structure makes it easier (or harder) to ask certain questions.

**Example 1:** "Show me all the articles related to France":

- Tag Tree #1:
  
  ``storm> #france``

- Tag Tree #2:
  
  ``storm> syn:tag:base=france -> *``

**Example 2:** "Show me all the articles on banking within the US":

- Tag Tree #1:
  
  ``storm> #us.economics.banking``

- Tag Tree #2:
  
  ``storm> syn:tag^=economics.banking +syn:tag:base=us -> *``

**Example #3:** "Show me all the articles about global trade":

- Tag Tree #1:
  
  ``storm> syn:tag:base=trade -> *``

- Tag Tree #2:
  
  ``storm> #economics.trade``

**Example #4:** "Show me all the articles about national elections":

- Tag Tree #1:
  
  ``storm> syn:tag:base=national -> *``

- Tag Tree #2:
  
  ``storm> #politics.elections.national``

Tag Tree #1 makes it easier to ask the first two questions; Tag Tree #2 makes it easier to ask the last two questions.
As you can see, choosing one tag tree over the other doesn’t **prevent** you from asking certain questions. If you choose
the first tree, you can still ask about global trade issues. But asking that question (creating an appropriate Storm query)
is a bit move involved. Creating a query based on a poorly-structured set of tags can get more difficult as both the tag
depth (nubmer of tag elements) and the total number of tags increases.

These differences in query structure may seem relatively minor. But structuring your tags to make it "easier" to ask the
questions that are most important to you has two important effects:

- **More efficient for Synapse to return the requested data:** In general, lifting data (selecting nodes) by the tag
  present on a node is more efficient than lifting ``syn:tag`` nodes and then pivoting to nodes that have those tags.
  This efficiency may be further affected if you are performing additional operations (filtering, additional pivots) on
  the results. These performance impacts may be relatively minor but can compound over larger data sets.

- **Simpler for analysts to remember:** Analysts want to spend their time analyzing data, not figuring out how to ask the
  right question (craft the right query) to retrieve the data in the first place. This has a much bigger impact on an
  analyst’s workflow - simpler is better!

Neither tag tree is right or wrong; which is more suitable depends on the types of questions you want to answer. If your
analysis focuses primarily on news content within a particular region, the first option (which places "country" at the root
of the tree) is probably more suitable. If your analysis focuses more on global geopolitical topics, the second option is
probably better. As a general rule, the analytical focus that you "care about most" should generally go at the top of the
hierarchy in order to make it easier to ask those questions.

Tag Definitions
---------------

Tag (``syn:tag``) nodes allow you to store both short-form and long-form definitions directly on the node itself (as
``:title`` and ``:doc`` properties, respectively). We recommend that you consistently use these properties to clearly
define the meaning of the tags you create within Synapse.

Synapse's forms (the data model) and your set of tags (analytical model) should convey key relationships and assessments
in a concise way. Your ability to view nodes and tags and understand their meaning should be simpler (and faster) than
reading a report about why an analyst interprets X to mean Y.

That said, tags are a "shorthand" used to represent specific observations and annotations. The meaning of a tag such as
``cno.infra.anon.tor`` may not be readily apparent. There is a risk that different analysts may interpret and use the
same tag in different ways. This risk increases as both the number of tags and the number of different analysts increases.

Storing a tag’s definition directly within Synapse on the associated ``syn:tag`` node makes Synapse "self-documenting":
an analyst can view the tag’s definition at any time directly within Synapse. You do not need to refer to an external
application or dictionary to look up a tag’s precise meaning and appropriate use.

Tag Management
--------------

Because tags are simply nodes, any user with the appropriate permissions can create a new tag. This ability to create tags
on the fly makes tags extremely powerful, flexible, and convenient for analysts – they can create annotations to reflect
their observations right when they are conducting analysis, without the need to wait for code changes or approval cycles.

There is also some risk to this approach, particularly with large numbers of analysts, as analysts may create tags in an
uncoordinated and haphazard fashion. Creating arbitrary (and potentially duplicative or contradictory) tags can work
against effective analysis.

Your approach to tag creation and approval will depend on your needs and your environment. Where possible, we recommend a
middle ground between "tag free-for-all" and "tightly-enforced change management". It is useful for an analyst to have the
ability to create a tag on demand to record an observation in the moment; if the analyst must wait for review and approval,
the observation is likely to be lost as the analyst moves on to other tasks. That said, it is also helpful to have some
type of regular review process to ensure the tags are being used in a consistent manner, fit appropriately into your
analytical model, and have been given clear definitions.

Level of Detail
---------------

Tag trees can be arbitrarily deep (that is, can support an arbitrary number of tag elements). If one function of tag
trees is to represent an increasing level of detail, then deep tag trees can potentially represent very fine-grained
observations.

While more detail is sometimes helpful, tag trees should reflect the level of detail that is relevant for **your** analysis,
and no more. That is, **the analysis being performed should drive the set of tags being used.**

Contrast this with taking an arbitrary model or taxonomy and using it to create associated tags without considering whether
that taxonomy is relevant or applicable to your analysis. In the best case, using a set of tags that is not well-suited is
simply be unnecessary - it may provide more detail than you really need. In the worst case, it can actually create **more**
work for analysts and be detrimental to the analysis process.

Tags often represent an analytical assertion - this generally means that **a human analyst** needs to evaluate the data, 
make an assessment, and decide what tag (or tags) to apply to the data. If you use too many tags, or overly detailed (deep)
tags, this translates directly in to "more work" (keystrokes or mouse clicks) that an analyst has to perform to annotate
the data. There is also overhead associated with tag creation itself, particularly if someone needs to review or approve
newly created tags.

More importantly, while the act of **applying a tag** to a node may be relatively easy, the **analytical decision** to
apply the tag may require careful review and evaluation of the evidence. If tags are overly detailed and represent shades
of meaning that are irrelevant, analysts may get bogged down in "analysis paralysis" - worrying about whether tag A or
tag B is correct when that distinction doesn’t matter to the analysis at hand.

In that situation, the (inappropriate or overly detailed) tags are driving the analysis instead of the analysis driving
the tags needed to support the analytical work. When tags drive the analysis, the act of annotating the data - figuring out
which tags to apply - takes over from performing real analysis.

.. TIP::
  
  When designing a tag tree, we recommend that tags have no more than five elements. For example:
  
  ``syn:tag = foo.bar.baz.faz.fuzz``
  
  As always, your specific use case may vary but this works well as general guidance.

Flexibility
-----------

Just as a good data model evolves to meet changing needs, your analytical model (tag trees) will expand and change
over time. No matter how carefully you plan your tag structure, you will identify exceptions, edge cases, and new
observations that you want to capture. As far as possible, your tag structure should be flexible enough to account for
future changes.

Within Synapse, it is relatively easy to "migrate" tags (i.e., to decide that a tag should have a different name or reside
in a different part of the tag tree, and to re-tag existing nodes with the new tag) **as long as the change is one-to-one.**
Migration works best where the tag **name** changes but the **meaning** of the tag does not. (See the Storm :ref:`storm-movetag`
command for details.)

For example, if you decide that ``foo.bar.baz.hurr`` and ``foo.bar.baz.derp`` are overly specific and should both be
represented by ``foo.bar.baz``, it is easy to merge those tags. Similarly, if you create the tag ``foo.bar`` and later
decide that tag should live under the top-level tag ``wut``, you can migrate ``foo.bar`` to ``wut.foo.bar``.

This flexibility provides a safety net when designing your tag trees. It gives you the freedom to "not get it right" the
first time (or the second, or the third!). Especially when you roll out a new set of tags, it is helpful to test them
in practice before you finalize the tags or tag structure. The ability to say "if we don’t get it quite right we can rename
it later" frees up analysts or developers to experiment.

It is harder to modify tags by "splitting" them. For example, if you create the tag ``foo.bar`` and later decide that you
really want to track two variations of ``bar`` (such as ``foo.bar.um`` and ``foo.bar.wut``), it can be painstaking to review
your existing ``foo.bar`` nodes to separate them into the appropraite categories.

Precision
---------

Each tag should have a single, specific meaning. This means that each assessment represented by a tag can be evaluated
(and the associated tags applied) independently. If you combine multiple assessments into a single tag, then you run into
problems if one portion of that assessment turns out to be true and another portion turns out to be false.

As a simple example, let's say you want to tag indicators with both the threat group and malware family the indicator is
associated with. It might be tempting to create a tag such as:

- ``syn:tag = cno.viciouswombat.redtree``

...to show that an indicator with that tag (such as an FQDN) is associated with both the Vicous Wombat threat group and
the Redtree malware family.

That's all well and good, until:

- You find out that the FQDN is used by both Redtree and Blueflower malware.
- You change your mind and decide the FQDN is associated with the Paisley Unicorn threat group, not Vicious Wombat.

By limiting a tag's meaning to a single assessment or assertion, you can easily change or remove the individual tag
if that particular assessment changes:

- ``syn:tag = cno.threat.viciouswombat``
- ``syn:tag = cno.threat.paisleyunicorn``
- ``syn:tag = cno.mal.redtree``
- ``syn:tag = cno.mal.blueflower``

Consistency of Use
------------------

Creating a set of well-designed tag trees is ineffective if those tags aren’t used consistently – that is, by a majority of
analysts across a majority of relevant data. It’s true that 100% visibility into a given data set and 100% analyst review and
annotation of that data is an unrealistic goal. However, for data and annotations that represent your **most pressing**
analytical questions, you should strive for as much completeness as possible.

Looked at another way, inconsistent use of tags can result in gaps that can skew your assessment of the data. At best, this
can lead to the inability to draw meaningful conclusions; at worst, to faulty analysis.

This inconsistency often occurs as both the number of analysts and the number of tags increase. The larger the team of
analysts, the more difficult it is for that team to work closely and consistently together. Similarly, the more tags
available to represent different assessments, the fewer tags an analyst can reasonably work with. In both cases, analysts
may tend to drift towards analytical tasks that are most immediately relevant to their work or most interesting to them –
thus losing sight of the collective analytical goals of the entire team.

Consider an example of tracking Internet domains that masquerade as legitimate companies for malicious purposes. If some
analysts are annotating this data but others are not, your ability to answer questions about this data is skewed. Let’s say
Threat Cluster 12 is associated with 200 domains, and 173 of them imitate real companies, but only 42 have been annotated
with "masquerade" tags (``cno.ttp.se.masq``).

If you try to use the data to answer the question "does Threat Cluster 12 consistently register domains that imitate valid
companies?", your assessment is likely to be "no" (only 42 out of 200 domains have the associated tag) based on the
incompletely annotated data. There are gaps in your analysis because the information to answer this question has only been
partially recorded.

As the scope of analysis within Synapse increases, it is essential to recognize these gaps as a potential shortcoming that
may need to be addressed. Options include:

- Establish policy around which assessments and observations (and associated tags) are essential or "required", and
  which are secondary ("as time allows").

- Designate individual analysts or teams to be responsible for particular tasks and associated tags - often matching
  their expertise, such as "malware analysis".

- Leverage Synapse’s tools such as triggers, cron jobs, or macros to apply tags in cases where this can be automated.
  Automation also helps to ensure tags are applied consistently. (See :ref:`storm-ref-automation` for a more detailed
  discussion of Synapse's automation tools.)