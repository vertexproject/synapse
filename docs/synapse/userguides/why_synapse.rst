.. note::
   This document needs to be updated.

Background - Why Synapse?
=========================

**Synapse is a distributed key-value hypergraph analysis framework.** Synapse is designed to support analysis conducted over very large and disparate data sets. Analysis is predicated on the representation of data from a given knowledge domain in a structured data model that allows analysts to represent, annotate, and query across the collected data.

Synapse offers several advantages:

* `Free and Open Source`_
* `Highly Optimized Performance`_
* `Comprehensive, Extensible Data Model`_
* `Data Model Introspection`_
* `Powerful Query Language`_
* `Shared Analysis Framework`_
* `Flexible, Granular Permissions`_
* `Detailed Logging`_
* `Distributed Architecture`_
* `Proven Methodology Informed by Real-World Experience`_

Free and Open Source
--------------------

Unlike costly commercial analysis systems, Synapse is available on Github_ under the `Apache License 2.0`_.

Highly Optimized Performance
----------------------------

Synapse was designed to address the performance limitations that constrain many large-scale analysis systems and eventually make them unworkable in practice. Synapse developers conducted extensive performance testing during Synapse’s initial development phase, and selected LMDB as the storage backing that provides optimal performance to meet Synapse’s goals. In addition, Synapse uses type-optimized indexing so that each type of data can be indexed in a manner that is optimized for how that data is typically queried and used.

Comprehensive, Extensible Data Model
------------------------------------

Synapse’s hypergraph framework allows for representation of widely disparate types of data as well as complex relationships. The extensible data model can be adapted to any knowledge domain.

Data Model Introspection
------------------------

The Synapse data model is itself data that is modeled in Synapse. This means that an analyst can query and view the model elements from within Synapse just as they can query data represented by the model. In other words, it is not necessary for an analyst to interrupt their workflow to refer to external documentation if they have questions about the model.

Powerful Query Language
-----------------------

Synapse includes a powerful native query language called Storm. Storm is designed to be both flexible and concise. Because many analysts are not programmers, Storm is designed as a "data language", functioning in a manner that feels more like "asking questions" in a natural manner as opposed to a "programming language" based on functions and parameters.

Shared Analysis Framework
-------------------------

Synapse provides a shared analytical workspace that consolidates research and encourages collaboration both within and across teams. Analytical knowledge is preserved in a central representational framework instead of residing solely within a specialized research group or with an individual “subject matter expert” whose knowledge will be lost if they leave the organization.

Synapse’s shared workspace allows real-time updates of data and analytical observations; both new data and the annotations of individual analysts are immediately visible to all others in the same workspace. The ability to “analyze once, record for all” means that analysts no longer need to waste effort researching the same data to come to the same conclusions.

Finally, the incorporation of new data or new analytical findings into a single framework dynamically highlights supporting or conflicting analysis, allowing assessments and hypotheses to be revisited as needed.

Flexible, Granular Permissions
------------------------------

Synapse includes a flexible role-based access control (RBAC) permissions system. Synapse allows the creation of both users and groups and supports fine-grained control over who can create, modify, and annotate data. Organizations with basic user management needs who want to be up and running quickly can set simple and broad permissions (create / modify / delete nodes, add / remove tags). Alternately, organizations with detailed needs or who support specialized types analysis can manage permissions down to the individual property or sub-sub-tag level if necessary - even to the extent of allowing a user to add or change only a single property on a single type of node.

Detailed Logging
----------------

TBD

Distributed Architecture
------------------------

TBD


Proven Methodology Informed by Real-World Experience
----------------------------------------------------

Most importantly, Synapse was not developed as a mathematical abstraction. Instead, Synapse grew out of a real-world need to track a complex, diverse, and very large data set: namely, cyber threat data.

The developers and analysts who worked on early Synapse prototypes came from a variety of government and commercial backgrounds but shared a common goal: the desire to record, annotate, and track cyber threat activity (specifically, nation-state level activity) both reliably and at scale. At the time when government and industry were beginning to grasp the scope and scale of the problem, “tracking” this complex activity was largely done using long-form reports, spreadsheets, or domain knowledge residing in an analyst’s mind. There was no way to effectively store large amounts of disparate data and associated analytical findings in such a way that relationships among those data and analytical conclusions were readily apparent or easily discoverable. More importantly, critical analytical decisions such as attribution were either impossible, or being made based on loose correlation, analysts’ recollection, or generally accepted “truths” - and **not** based on concrete, verifiable data whose source and analysis could be traced and either verified or questioned.

In contrast, Synapse and its predecessors were designed from the beginning to support the following critical elements:

* The use of a **shared analytical workspace** to give all analysts access to the same data in real time, as noted above.
* The concept that the analysis captured within the system should “speak for itself”: that is, to the extent possible, data and analytical findings must be represented in such a way that **relationships among data and conclusions about data should be self-evident**.

These features provide the following benefits:

* Synapse allows (and requires) analysts to “show their work” in a reasonably concise manner. Analysts should not have to refer to long-form reporting (or rely on the unquestioned word of a subject matter expert) to trace an analytical line of reasoning.
* Synapse allows analysts to better vet and verify each other’s findings. Conflicting analytical lines are highlighted through the structure of the data itself. Analysis can readily be questioned, reviewed, deconflicted, and ultimately improved.

The original Synapse prototype was designed to store a broad range of threat data, including:

* Network infrastructure
* Malware and malware behavior
* Host- and network-based incident response data
* Detection signatures and signature hits
* Decoded network packet captures
* Targeting of organizations, individuals, and data
* Threat groups and threat actors
* People and personas
* Newsfeeds and reference materials

Prototype systems eventually stored **nearly one billion** nodes, edges, and analyst annotations. Data modeled by this system was used to produce some of the most groundbreaking public reporting on nation-state ("Advanced Persistent Threat", or APT) activity to date.

Synapse is the next generation of technology built on approximately five years of technical and analytical lessons learned:

* The new hypergraph design addresses many of the shortcomings identified with earlier directed graph systems.
* Because the experience of working with threat data taught us the power of a flexible analysis platform over **any** large and disparate data set, Synapse has been designed to be flexible, modular, and adaptable to any knowledge domain.

Many of the real-world examples in this User Guide reference data from the field of information technology or threat tracking, given Synapse’s history; but the structures, processes, and queries can be applied to other domains and data sets as well. **The intent of Synapse is that any data that could be represented in a spreadsheet, database, or graph database can be represented in a Synapse hypergraph using an appropriate data model.**

.. _Github:                https://github.com/vertexproject

.. _`Apache License 2.0`:  https://github.com/vertexproject/synapse/blob/master/LICENSE
