```mdstorm-setup
```

<a id="analytical-model"></a>

# Analytical Model

Synapse's [Data Model](data_model.md#userguide_datamodel) provides a structured way to record, query, and navigate observables - objects, relationships, events, and activities that can be captured and are unlikely to change.

Synapse also gives analysts a structured way to record observations or assessments through the use of labels (**tags**) applied to data (nodes). Assessments represent conclusions based on the data available to you at the time. As new data becomes available, your analysis is revised. Because they are labels on nodes, tags are flexible and can be easily added, updated, or removed when assessments change.

Tags provide immediate **context** to individual nodes, and can be used to group related nodes together. In addition, because Synapse represents both data (nodes) and assessments (tags) structurally and consistently, analysts can use Synapse to query both in very powerful ways.

Synapse uses the `syn:tag` form to represent tags, which is simple and straightforward. The appropriate **use** of tags to annotate data is more nuanced. You can think of the structure and application of tags as an **analytical model** that complements and extends the power of the data model.

The specific annotations and assessments that are useful for analysis may vary widely based on the analytical discipline in question, or even the needs of individual organizations within the same discipline. For this reason, Synapse does not include any built in tags. Organizations are free to design and use tags and tag trees that are most useful and relevant to them.

> [!TIP]
> We encourage the design and use of tags that:
>
> - annotate assessments and conclusions that are relevant to **your** analysis.
> - allow you to ask the analytical questions that are most important to **your organization.**
>
> While many disciplines will have similar tagging needs, tags are not necessarily "one size fits all". For an example of tags/tag trees used by The Vertex Project, see our [Vertex Tag Tree Overview](https://vertex.link/blogs/vtx-tag-trees/) blog.

This section discusses tags, their unique features, and their uses in more detail.

<a id="analytical-tags-nodes"></a>

## Tags as Nodes

Tags in Synapse are nodes (`syn:tag` nodes) in their own right. As nodes, they can be viewed directly within Synapse, making them self-documenting (see [Storm Reference - Model Introspection](storm_ref_model_introspect.md#storm-ref-model-introspect) or Optic's [Tag Explorer](/docs/synapse-enterprise-optic/latest/user_interface/userguides/get_help.md#using-tag-explorer) for details on viewing and working with tags).

A tag's primary property is the name of the tag; so the tag `foo.bar` has the primary property `syn:tag=foo.bar`. The dotted notation can be used to construct tag hierarchies / tag trees to organize tags and represent varying levels of specificity. Other `syn:tag` properties allow you to record a definition for the tag and support navigation of tag nodes.

This example shows the **node** for the tag `syn:tag=rep.mandiant.apt1`:

```mdstorm --hide
[syn:tag=rep.mandiant.apt1 :title="APT1 (Mandiant)" :doc="Indicator or activity Mandiant calls (or associates with) APT1."]
```

```mdstorm
syn:tag=rep.mandiant.apt1
```

The `syn:tag` node has the following properties:

- `:title` and `:doc`, which store concise and more detailed definitions for the tag. Definitions on tag nodes help to ensure the tags are applied (and interpreted) correctly by analysts and other Synapse users.
- `.created` and `.updated`, which are meta properties showing when the node was added to a Cortex and when it was last modified, respectively.

The `:depth`, `:up`, and `:base` secondary properties help to lift and pivot across tag nodes:

- `:depth` is the "location" of the tag in a given tag tree, with the count starting from zero. A single-element tag (`syn:tag=rep`) has `:depth=0`, while a three-element tag (`syn:tag=rep.mandiant.apt1`) has `:depth=2`.
- `:base` is the final (rightmost) element in the tag tree.
- `:up` is the tag one "level" up in the tag tree.

Tags (`syn:tag` forms) have some specialized behaviors within Synapse with respect to how they are indexed, created, and manipulated via Storm. Most important for practical purposes is that `syn:tag` nodes are created automatically when a tag is applied to another node. You do not need to create the `syn:tag` node before the tag can be used; applying the tag will also create the appropriate `syn:tag` node (or nodes) if it does not exist.

See the [syn:tag](storm_ref_type_specific.md#type-syn-tag) section within [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for additional detail.

<a id="analytical-tags-labels"></a>

## Tags as Labels

A tag's value (`syn:tag=<valu>`) is simply a string and can be set to any user-defined alphanumeric value. Tags do not support special characters except for the underscore ( `_` ).

Tag strings use a dotted naming convention, with the period ( `.` ) used as a separator to delimit individual elements of a tag if necessary. This dotted notation supports the creation of tag hierarchies or tag trees. These trees can be used to group different types of tags (with each top-level or root tag representing a particular category). The structure can also support increasingly detailed or specific observations.

Within a tag tree, specific terms are used for the tags and their components:

- **Leaf tag:** The full tag.
- **Root tag:** The top / leftmost element in a given tag.
- **Base tag:** The bottom / rightmost element in a given tag.

For the tag `rep.microsoft.forest_blizzard`:

- `rep.microsoft.forest_blizzard` is the leaf tag (leaf).
- `rep` is the root tag (root).
- `forest_blizzard` is the base tag (base).

When you apply a tag to a node, all of the tags **above** that tag in the tag tree are automatically applied as well (and the appropriate `syn:tag` nodes are created if they do not exist). That is, when you apply the tag `rep.microsoft.forest_blizzard` to a node, Synapse automatically applies the tags `rep.microsoft` and `rep` as well. This allows you to ask about (query) tags at any depth:

- `#rep.microsoft.forest_blizzard`: all things Microsoft associates with "Forest Blizzard".
- `#rep.microsoft`: all things reported by Microsoft.
- `#rep`: all things reported by any third party.

When you delete (remove) a tag from a node, the tag and all tags **below** it in the tag tree are deleted. If a node has the tag `rep.microsoft.forest_blizzard`:

- when you delete the tag `rep.microsoft.forest_blizzard` (the base tag), the tags `rep.microsoft` and `rep` will remain.
- when you delete the tag `rep` (the root or full tag) then all three tags are deleted.

Deleting a tag from a node does **not** delete the `syn:tag` node for the tag itself.

See the [syn:tag](storm_ref_type_specific.md#type-syn-tag) section within [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for additional detail on tags and tag behavior.

<a id="tag-timestamps"></a>

### Tag Timestamps

Synapse supports the use of optional tag **timestamps** to indicate the period when the assessment represented by a tag was true, relevant, or observed. Tag timestamps are intervals (pairs of date / time values).

Tag timestamps represent a time **range** and not necessarily specific instances (other than the "first known" and "last known" observations). This means that the assessment represented by the tag is not guaranteed to have been true throughout the entire date range (though depending on the meaning of the tag, that may be the case). That said, the use of timestamps allows much greater granularity in recording observations in cases where the timing of an assessment ("when" something was true or applicable) is relevant.

As an example, tag timestamps can be used to indicate when an IP address was used as a TOR exit node. This knowledge can aid with both current and historical analysis of network infrastructure.

```mdstorm --hide
[inet:ip=185.29.8.215 :asn=60567 :place:loc=se.ab.stockholm :type=unicast +#cno.infra.anon.tor.exit=('2023/05/08 14:30:51', '2023/08/17 19:39:48') ]
```

```mdstorm
inet:ip = 185.29.8.215
```

The tag `cno.infra.anon.tor.exit` indicates that the IP has been used as a TOR exit node; the dates associated with the tag indicate the "first seen" and "last seen" times.

<a id="tag-properties"></a>

### Tag Properties

Synapse supports the use of **tag properties** to provide additional context to a tag or set of tags. Unlike tags (which can be applied and created on the fly), tag properties must be defined and declared within the data model before they can be used.

Once declared, tag properties can be applied (appended) to **any** tag; they are not (and cannot be) restricted to specific tags. Tag properties are best suited for use cases that would be applicable to all (or at least most) tags in your environment.

Synapse v3 includes two tag properties in the base data model:

- `:confidence`, a measure of confidence in the assertion represented by the tag. `:confidence` has a type of `meta:score`.
- `:tlp`, a measure of data sensitivity that uses the conventions of the [Traffic Light Protocol](https://www.cisa.gov/news-events/news/traffic-light-protocol-tlp-definitions-and-usage). `:tlp` has a type of `it:sec:tlp`.

You can add tag properties by [extending the data model](data_model.md#extending-the-data-model). Extended tag property names (like all extended model element names) must begin with an underscore.

> [!TIP]
> In some cases, creating an **extended model property** is a better option than an extended tag property to represent the information in question. For example, a third-party data vendor might provide a custom risk score associated with an indicator such as an FQDN. While this could be added as a custom `:risk` tag property (`#rep.somevendor:_risk=80`), the `:_risk` property could be used with any / all tags in the environment, which may not be applicable.
> 
> Instead, an extended property can be added to the data model and the risk score recorded as a property on the FQDN:
> 
> `inet:fqdn:_somevendor:risk=80`
>
> This limits the use of the vendor's "risk" score to only those forms / nodes where it is relevant, and also allows you to work with (select/lift, filter, pivot, etc.) the value the same way as any other property in the data model.

> [!NOTE]
> Users should weigh the pros and cons of using tag properties to record information that may change frequently. Synapse is a dynamic intelligence platform, designed to be continually updated and to always represent your current state of knowledge. This means that assessments like "confidence" may quickly become stale if they are not consistently reviewed and updated based on new data and assessments. It may be appropriate for your analysis to make selective use of tag properties for key assessments. However, widespread use of some tag properties may generate more work (for analysts and / or automation) than it is worth, and may actually hinder effective analysis by recording information that is quickly dated or incorrect.

<a id="analytical-tags-asnodes"></a>

## Tags Associated with Nodes

Tags can represent observations or assessments. In some cases tags can stand on their own - the tag `cno.infra.anon.tor.exit` used to indicate that a node (such as an IP address) represents anonymous network infrastructure (specifically, a TOR exit node) is straightforward. In other cases, a tag may represent a larger concept. The tag `rep.mandiant.apt1` means that Mandiant associates an indicator (such as a malware binary) with the threat group APT1. This provides context to the malware binary, but may create additional questions. Who or what is APT1? Where are they located? When did Mandiant first observe them?

When a tag references something and you want to record additional information about that thing, the tag can be associated with a node (via a `:tag` secondary property). For example `risk:threat` nodes represent reporting of threat activity by a particular organization (such as Mandiant). The node's `risk:threat:tag` property can be set to `rep.mandiant.apt1`. You can then navigate from nodes that have the `rep.mandiant.apt1` tag, to the node `syn:tag=rep.mandiant.apt1`, to the `risk:threat` node with that `:tag` value to learn more about Mandiant's APT1.

<a id="analytical-tag-best"></a>

## Tag Best Practices

The tags that you use to annotate data represent your **analytical model**. Your ability to conduct meaningful analysis depends in part on whether your analytical model is well-designed to meet your needs. The tags that work best for you may be different from those that work well for another organization.

The following recommendations should be considered when creating, maintaining, and using tags and tag trees.

### Tag Trees

Tag trees generally move from "less specific" to "more specific" the deeper you go within a hierarchy. The order of elements in your hierarchy can affect the types of analysis questions you can most easily answer. The structure you create should allow you to increase specificity in a way that is meaningful to the questions you're trying to answer.

For example, let's say you are storing copies of articles from various news feeds within Synapse (i.e., as `doc:report` nodes). You want to use tags to annotate the subject matter of the articles. Two possible options would be:

**Tag Tree \#1**

``` text
<country>.<topic>.<subtopic>.<subtopic>:
  us.economics.trade.gdp
  us.economics.trade.deficit
  us.economics.banking.lending
  us.economics.banking.regulatory
  us.politics.elections.national
  france.politics.elections.national
  france.politics.elections.local
  china.economics.banking.lending
```

**Tag Tree \#2**

``` text
<topic>.<subtopic>.<subtopic>.<country>:
  economics.trade.gdp.us
  economics.trade.deficit.us
  economics.banking.lending.us
  economics.banking.regulatory.us
  politics.elections.national.us
  politics.elections.national.france
  politics.elections.local.france
  economics.banking.lending.china
```

Neither tag tree is right or wrong; which is more suitable depends on the types of questions you want to answer. If your analysis focuses primarily on news content within a particular region, the first option (which places "country" at the root of the tree) is probably more suitable. If your analysis focuses more on global geopolitical topics, the second option is probably better. As a general rule, the analytical focus that you "care about most" should generally go at the top of the hierarchy in order to make it easier to ask those questions.

**Note:** the above example is a bit contrived. While tags are one option, the `doc:report:topics` property provides a more structured way to record (and pivot among) article subjects or keywords. 

### Tag Elements

Each positional element within a tag tree should have the same "category" or meaning. This makes it easier to work with portions of the tag tree in a consistent manner. For example, if you are tagging indicators of compromise with assessments related to third-party reporting, you should maintain a consistent structure. For example, the tags `rep.paloalto.stately_taurus` and `rep.paloalto.bookworm` use the structure:

`rep.<reporter>.<thing reported>`

In this example `rep` is a top-level namespace for third party reporting, the second element refers to the reporter (`paloalto` for Palo Alto Networks), and the third element refers to what is being reported (threat group and malware family, respectively).

### Tag Precision

A tag should represent one thing - an atomic assessment. This makes it easier to change that specific assessment without impacting other assessments. For example, let's say you assess that an IP address was used by the Vicious Wombat threat group as a C2 location for Redtree malware. It might be tempting to create a tag such as:

`cno.threat.vicious_wombat.redtree.c2`

By combining three assessments (who used the IP, the malware associated with the IP, and how the IP was used) you have made it much more difficult to update the context on the IP if any one of those three assessments changes. What if you realize the IP was used by Sparkling Unicorn instead? Or that the IP was used for data exfiltration and not C2? Using three separate tags makes it much easier to revise your assessments if necessary:

- `cno.threat.vicious_wombat.use`
- `cno.mal.redtree`
- `cno.role.c2`

### Tag Definitions

You can store both short-form and long-form definitions directly on `syn:tag` nodes using the `:title` and `:doc` properties, respectively. We recommend that you use these properties to clearly define the meaning of the tags you create within Synapse to ensure they are both applied and interpreted consistently.

### Tag Depth

Tag trees can be arbitrarily deep (that is, can support an arbitrary number of tag elements). This implies that deep tag trees can potentially represent very fine-grained observations. While more detail is sometimes helpful, tag trees should reflect the level of detail that is **relevant** for your analysis, and no more. Overly-detailed tag trees can actually hamper analysis by providing too many choices for analysts.

Tags that represent analytical assertions mean that **a human analyst** typically needs to evaluate the data, make an assessment, and decide what tag (or tags) to apply to the data. If tags are overly detailed, analysts may get bogged down in "analysis paralysis" - worrying about whether tag A or tag B is correct when that distinction really doesn't matter to the analysis at hand.

We recommend that tags have no more than five elements at most. As always, your specific use case may vary but this works well as general guidance.

### Tag Rollout

Tagging data with assessments may represent a novel approach to analysis for many users. As analysts adjust to new workflows, it may be helpful to implement a subset of tags at first. Getting used to applying some basic tags may be easier than suddenly being asked to annotate data with a broad range of observations. As analysts get comfortable with the process, you can introduce additional tags or tag trees as appropriate.

### Tag Flexibility

Tags are meant to be flexible - the ability to easily add, remove, and modify tags is a built-in aspect of Synapse. Synapse also includes tools to help move, migrate, or restructure entire tag trees (e.g., the Storm [movetag](storm_ref_cmd.md#storm-movetag) command).

**No one designs a complete, perfect tag structure from the start.** It is common to design an initial tag tree and then make changes once you have tested it in practice. Your tag trees will grow over time as analysts identify new observations they want to record. Your analytical needs may change, requiring you to reorganize multiple trees.

This is fine (and expected)! **Don't be afraid to try things or change your mind.** In most cases, bulk changes and migrations can be made using Storm.

### Tag Management

Any user with the appropriate permissions can create a new tag. The ability to create tags on the fly makes tags extremely flexible and convenient for analysts - they can create annotations to reflect their observations "in the moment" without the need to wait for code changes or approval cycles.

There is also some risk to this approach, particularly with large numbers of analysts, as analysts may create tags in an uncoordinated and haphazard fashion. Creating arbitrary (and potentially duplicative or contradictory) tags can work against effective analysis.

Your approach to tag creation and approval will depend on your needs and your environment. Where possible, we recommend a middle ground between "tag free-for-all" and "tightly-enforced change management". It is useful for an analyst to create a tag on demand; if they have to wait for review and approval, their observation is likely to be lost as they move on to other tasks. That said, it is also helpful to have some type of regular review process to ensure the tags are being used in a consistent manner, fit appropriately into your analytical model, and have been given clear definitions.

### Official vs. Unofficial Tags

Not all tags and tag trees need to be formally defined and approved. Many organizations define an official set of tag trees that are approved for production use and also define (or allow) analysts to use unofficial, personal, or "scratch" tags as needed to help with ongoing research. Unofficial tags should use their own namespace (for example, "int" for internal, "temp" for temporary, or "\<username\d>" for users' personal trees) to clearly separate them from official tags / trees but are otherwise encouraged (and highly useful).

### Tag Consistency

No matter how well-designed a tag tree is, it is ineffective if the tags are not used consistently. Tags that are most important to your organization's analysis must be used by a majority of analysts across a majority of relevant data. Complete visibility into a data set and 100% analyst review and annotation of that data is an unrealistic goal. However, for data and annotations that represent your **most pressing** analytical questions, you should strive for as much completeness as possible.

Looked at another way, inconsistent use of tags can result in gaps that can skew your assessment of the data. At best, this can lead to the inability to draw meaningful conclusions; at worst, it leads to faulty analysis.

Inconsistency often occurs as both the number of analysts and the number of tags increase. The larger the team of analysts, the more difficult it is for that team to work closely and consistently together. Similarly, the more tags available to represent different assessments, the fewer tags an analyst can reasonably work with. In both cases, analysts may tend to drift towards analytical tasks that are most immediately relevant to their work or most interesting to them - thus losing sight of the collective analytical goals of the entire team.

Consider an example of tracking Internet domains that masquerade as legitimate companies for malicious purposes. If some analysts are annotating this data but others are not, your ability to answer questions about this data is skewed. Let's say Threat Cluster 12 is associated with 200 domains, and 173 of them imitate real companies, but only 42 have been annotated with "masquerade" tags (e.g., `cno.ttp.se.masq`).

If you try to use the data to answer the question "does Threat Cluster 12 consistently register domains that imitate valid companies?", your assessment is likely to be "no" (only 42 out of 200 domains have the associated tag) based on the incompletely annotated data. There are gaps in your analysis because the information to answer this question has only been partially recorded.

As the scope of analysis within Synapse increases, it is essential to recognize these gaps as a potential shortcoming that may need to be addressed. Options include:

- Establish policy around which assessments and observations (and associated tags) are essential or **required**, and which are secondary (optional or "as time allows").
- Designate individual analysts or teams to be responsible for particular tasks and associated tags - often matching their area of expertise, such as "malware analysis".
- Leverage Synapse's tools such as triggers, cron jobs, or macros to apply tags in cases where this can be automated. Automation also helps to ensure tags are applied consistently. (See [Storm Reference - Automation](storm_ref_automation.md#storm-ref-automation) for a more detailed discussion of Synapse's automation tools.)
