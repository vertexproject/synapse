Synapse User Guide - Why Synapse?
=================================

**Synapse is a distributed key-value hypergraph analysis framework.** Synapse is designed to support analysis conducted over very large and disparate data sets. Analysis is predicated on the representation of data from a given knowledge domain in a structured data model that allows analysts to represent, annotate, and query across the collected data.

Synapse offers several advantages:

**Free and Open Source**

Unlike costly commercial analysis systems, Synapse is available on Github under the Apache License 2.0.

**Performance**

Synapse was designed to address the performance limitations that constrain many large-scale analysis systems and eventually make them unworkable in practice. Synapse supports multiple storage and indexing options (RAM, LMDB, Postgres) that can be tailored to support the type and volume of data stored, as well as the proportion of read (query / retrieval) vs. write (node creation and deconfliction) operations. For detailed performance benchmarks, see `Synapse Performance`_ for more information.

**Extensible Comprehensive Data Model**

Synapse’s hypergraph framework allows for representation of more disparate data types and complex relationships. The extensible data model can be adapted to any knowledge domain.

**Powerful Analysis Framework**

Synapse provides a shared analytical workspace that consolidates research and prevents “stovepiping” of findings. Analytical knowledge is preserved in a central representational framework instead of residing solely within a specialized research team or with an individual “subject matter expert” who may leave the organization.

Synapse’s shared workspace allows real-time annotation of data with analytical observations; the work of one analyst is immediately visible to all others in the same workspace. The ability to “analyze once, record for all” means that analysts no longer need to waste effort independently reviewing the same data to come to the same conclusions. Finally, the incorporation of new data or new analytical findings dynamically highlights supporting or conflicting analysis, allowing assessments and hypotheses to be revisited as needed.

**Proven Methodology Informed by Real-World Experience**

Synapse was not developed as a mathematical abstraction. Instead, Synapse grew out of a real-world need to track a complex, diverse, and very large data set: namely, cyber threat data.

The developers and analysts who worked on early Synapse prototypes came from a variety of government and commercial backgrounds but shared a common goal: the desire to record, annotate, and track cyber threat activity (specifically, Advanced Persistent Threat activity) both reliably and at scale. At a time when government and industry were beginning to grasp the scope and scale of the problem, “tracking” this complex activity was largely being done using long-form reports, spreadsheets, or domain knowledge residing in an analyst’s mind. There was no way to effectively store and analyze large amounts of data, and critical analytical decisions – such as attribution – were either impossible, or being made based on loose correlation, analysts’ recollection, or generally accepted “truths” - and not on concrete, verifiable data whose source and analysis could be traced and either verified or questioned.

In contrast, Synapse and its predecessors were designed from the beginning to support the following critical elements:

- The use of a shared analytical workspace to give all analysts access to the same data in real time (as noted above).
- The concept that the analysis captured within the system should “speak for itself”: that is, to the extent possible, data and analytical findings must be represented in such a way that relationships and conclusions should be self-evident.

These features provide the following benefits:

- It allows (and requires) analysts to “show their work” in a reasonably concise manner. Analysts should not have to refer to long-form reporting (or rely on the unquestioned word of a subject matter expert) to trace an analytical line of reasoning.
- It allows analysts to better vet and verify each other’s findings. Conflicting analytical lines are highlighted through the structure of the data itself. Analysis can readily be questioned, reviewed, and deconflicted.

The original Synapse prototype was designed to store a broad range of threat data, including:

- Network infrastructure
- Malware and malware behavior
- Host- and network-based incident response data
- Detection signatures and signature hits
- Decoded network packet captures
- Targeting of organizations, individuals, and data
- Threat groups and threat actors
- People and personas
- Newsfeeds and reference materials

Prototype systems eventually stored **nearly one billion** nodes, edges, and analyst annotations. Data modeled by this system was used to produce some of the most groundbreaking public reporting on APT activity to date.

Synapse is the next generation of technology built on approximately five years of technical and analytical lessons learned. The new hypergraph design addresses many of the shortcomings identified with earlier directed graph systems. And because the experience of working with threat data taught us the power of a flexible analysis platform over *any* large and disparate data set, Synapse has been designed to be flexible, modular, and adaptable to any knowledge domain. Many of the real-world examples in this User Guide reference data from the field of information technology or threat tracking, given Synapse’s history; **but the structures, processes, and queries can be applied to other domains and data sets as well.** The intent of Synapse is that any data that could be represented in a spreadsheet, database, or graph database, could be represented in a Synapse hypergraph using an appropriate data model.

.. _`Synapse Performance`: ../performance.html
