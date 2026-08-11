

<a id="intro"></a>

# Introduction

**Synapse** is a versatile central intelligence and analysis system created to support analyst teams in every stage of the intelligence life cycle.

[The Vertex Project](https://vertex.link/) designed and developed Synapse to help analysts and algorithms answer complex questions which require the fusion of large data sets from disparate sources that span multiple disciplines.

Synapse's data store (known as a [Cortex](glossary.md#gloss-cortex)) is organized as a [hypergraph](https://en.wikipedia.org/wiki/Hypergraph). Combined with its structured and extensible [Data Model](userguides/data_model.md#userguide_datamodel) and the powerful and intuitive [Storm](glossary.md#gloss-storm) query language, Synapse gives analysts unparalleled power and flexibility to ask and answer any question, even over large and complex data sets.

> [!NOTE]
> A [Cortex](glossary.md#gloss-cortex) may easily grow to billions of nodes, but is not designed to consume and create billions of nodes per day. In other words, Synapse is not meant to replace your big-data/data-lake storage; Synapse is designed to connect to your data sources on demand in order to ingest data relevant for your analysis into the Synapse intelligence platform.

<a id="intro-features"></a>

## Key Features

**Extensible Data Model**

Synapse includes an extensive (and extensible) [Data Model](userguides/data_model.md#userguide_datamodel) capable of representing real-world objects, relationships, and events in an intuitive and realistic manner.

**Strong Typing**

Synapse uses [Type Normalization](glossary.md#gloss-type-norm) and [Type Enforcement](glossary.md#gloss-type-enforce) to apply meaningful constraints to data to ensure it is well-formed, preventing "bad data" from cluttering the knowledge store. [Type Awareness](glossary.md#gloss-type-aware) simplifies use of the Storm query language and helps analysts discover novel relationships in the data.

**Powerful and Intuitive Query Language**

Synapse's [Storm](glossary.md#gloss-storm) query language is a powerful, intuitive "data language" used to interact with data in a Synapse Cortex. Storm frees analysts from the limitations of "canned" queries or hard-coded data navigation and allows them to ask - and answer - **any** analytical question.

**Unified Analysis Platform**

Synapse's unified data store provides analysts with a shared view into the same set of data and analytical annotations, allowing them to better coordinate, collaborate, and peer-review their work.

**Designed and Tested in Partnership with Analysts**

Synapse is the product of a unique close collaboration between Vertex developers and analysts that leverages innovative software design and engineering to directly support analyst needs and workflows.

**Modular Architecture**

Synapse is extensible through **Power-Ups** (see [Power-Up](glossary.md#gloss-power-up)) that add functionality, integrate with third-party data sources, or connect to external databases.

**Record Analytical Assessments**

Synapse allows analysts to annotate data with assessments and observations through a flexible and extensible set of tags (see [Tag](glossary.md#gloss-tag)). By recording assessments **and** data in a structured manner, analysts and algorithms can leverage **both** in their queries and workflows.

**"Git for Analysis"**

Synapse supports the use of layers (see [Layer](glossary.md#gloss-layer)) to comprise a [View](glossary.md#gloss-view) into Synapse's data store. Analysts can create a [Fork](glossary.md#gloss-fork) of a given view and use it for testing or research without modifying the underlying production data. Once work in the fork is complete, changes can be merged into the production view or discarded.

**Fine-Grained Access Controls**

Synapse provides access controls and detailed permissions that can be applied to users or roles. Permissions can be specified broadly or to a level of detail that restricts a user to setting a single property on a single form.

**Flexible Automation**

Synapse allows you to create custom automation for both analytical and administrative tasks, ensuring consistency and eliminating tedious or time-consuming workflows. Automation (see [Storm Reference - Automation](userguides/storm_ref_automation.md#storm-ref-automation)) is provided using event-based triggers ([Trigger](glossary.md#gloss-trigger)), scheduled cron jobs, or stored macros.

**API Access**

Synapse includes multiple well-documented APIs for interacting with the data store and other Synapse components (see [Synapse HTTP/REST API](httpapi.md#http-api)).

**Lightning Fast Performance**

Synapse uses LMDB for high-performance key-value indexing and storage, combined with asynchronous, streaming processing. This means queries start returning results as soon as they are available -so your "time to first node" is typically milliseconds, regardless of the size of your result set.

**Horizontally and Vertically Scalable**

A single Synapse Cortex can easily scale vertically to hold tens of billions of nodes. In addition, Synapse supports high-availability topologies such as mirroring.

## What's Next?

<table style="width:99%;">
<colgroup>
<col style="width: 28%" />
<col style="width: 59%" />
<col style="width: 11%" />
</colgroup>
<tbody>
<tr class="odd">
<td><strong>Get Started!</strong></td>
<td colspan="2"><ul>
<li>There are several options for you to deploy | and start using Synapse! See our | [Getting Started](getting_started.md#getting_started) guide to see which | right for you. | |</li>
<li><dl>
<dt>Watch a [Guided Tour](https://v.vtx.lk/synapse-tour)</dt>
<dd>
<div class="line-block"></div>
</dd>
</dl></li>
</ul></td>
</tr>
<tr class="even">
<td><strong>Users</strong></td>
<td colspan="2"><ul>
<li>[Synapse User Guide](userguide.md#userguide) |</li>
<li>[Storm Reference](userguides/index_storm_ref.md#userguide_storm_ref) |</li>
<li>[Changelog](changelog.md) |</li>
<li>Ask a question in <a href="https://v.vtx.lk/join-slack">Slack</a> |</li>
</ul></td>
</tr>
<tr class="odd">
<td><strong>DevOps</strong></td>
<td colspan="2"><ul>
<li>[Synapse Devops Guide](devopsguide.md#devopsguide) |</li>
<li>[Synapse Deployment Guide](deploymentguide.md#deploymentguide) |</li>
<li>Synapse [sizing guide](https://vertex.link/files/docs/synapse/Synapse-Sizing-Guidance.pdf)</li>
</ul></td>
</tr>
<tr class="even">
<td><strong>Developers</strong></td>
<td colspan="2"><ul>
<li>[Synapse Developer Guide](devguide.md#devguide) |</li>
<li>[Synapse HTTP/REST API](httpapi.md#http-api) |</li>
<li>[Synapse Data Model](datamodel.md#dm-index) |</li>
<li>[Storm Library Documentation](stormtypes.md#stormtypes_index) |</li>
</ul></td>
</tr>
<tr class="odd">
<td><strong>Admins</strong></td>
<td colspan="2"><ul>
<li>[Synapse Admin Guide](adminguide.md#adminguide) |</li>
</ul></td>
</tr>
<tr class="even">
<td><strong>Synapse UI</strong> (commercial)</td>
<td colspan="2"><ul>
<li>[Synapse UI](/docs/synapse-enterprise-optic/latest/index.md) ("Optic") documentation (includes guides for users, devops, and | developers) |</li>
</ul></td>
</tr>
<tr class="odd">
<td><strong>Learn More</strong></td>
<td><ul>
<li>Video <a href="https://v.vtx.lk/youtube">Library</a></li>
<li>Visit The Vertex Project <a href="https://vertex.link/">Website</a></li>
</ul></td>
<td></td>
</tr>
<tr class="even">
<td><strong>Connect With Us!</strong></td>
<td colspan="2"><ul>
<li><a href="https://v.vtx.lk/join-slack">Slack</a> |</li>
<li><a href="https://v.vtx.lk/linkedin">LinkedIn</a> |</li>
<li>[X/Twitter](https://v.vtx.lk/twitter)</li>
<li><a href="https://v.vtx.lk/bluesky">Bluesky</a> |</li>
<li>"Star" us on <a href="https://github.com/vertexproject/synapse">Github</a> |</li>
</ul></td>
</tr>
</tbody>
</table>
