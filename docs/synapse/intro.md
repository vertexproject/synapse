```mdtoc

```

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

### Getting Started

There are several options for you to deploy and start using Synapse! See our [Getting Started](getting_started.md#getting_started) guide to see which option is
right for you.

Watch a [Guided Tour](https://v.vtx.lk/synapse-tour)

### Users
- [Synapse User Guide](userguide.md)
- [Storm Reference](userguides/index_storm_ref.md)
- [Changelog](changelog.md)
- Ask a question in [Slack](https://v.vtx.lk/join-slack)

### DevOps
- [Synapse Devops Guide](devopsguide.md)
- [Synapse Deployment Guide](deploymentguide.md)
- Synapse [sizing guide](https://vertex.link/files/docs/synapse/Synapse-Sizing-Guidance.pdf)

### Developers
- [Synapse Developer Guide](devguide.md)
- [Synapse HTTP/REST API](httpapi.md)
- [Synapse Data Mode](datamodel.md)
- [Storm Library Documentation](stormtypes.md)

### Admins
- [Synapse Admin Guide](adminguide.md)

### Synapse UI (commercial)
- [Synapse UI](/docs/synapse-enterprise-optic/latest/index.md) ("Optic") documentation (includes guides for users, devops, and developers)

### Learn More
- Video [Library](https://v.vtx.lk/youtube)
- Visit The Vertex Project [Website](https://vertex.link/)

### Connect With Us!
- [Slack](https://v.vtx.lk/join-slack)
- [LinkedIn](https://v.vtx.lk/linkedin)
- [X/Twitter](https://v.vtx.lk/twitter)
- [Bluesky](https://v.vtx.lk/bluesky)
- "Star" us on [Github](https://github.com/vertexproject/synapse)
