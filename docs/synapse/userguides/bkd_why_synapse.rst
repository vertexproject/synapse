.. highlight:: none

.. _bkd-why-synapse:

Background - Why Synapse?
=========================

**Synapse is a versatile central intelligence and analysis system created to support analyst teams in every stage of the intelligence life cycle.** We designed and developed Synapse to help analysts and algorithms answer complex questions which require the fusion of large data sets from disparate sources that span multiple disciplines. Analysis is based on the ability to represent data in a structured model that allows analysts to represent, annotate, and query across the collected data.

.. TIP::
  
  See Synapse's :ref:`intro-features` for an overview of Synapse's advantages!

Perhaps most importantly, **Synapse is based on a proven methodology informed by real-world experience.**

The Vertex Project did not develop Synapse as a mathematical abstraction or software engineering experiment. Instead, Synapse grew out of a **real-world need** to track a complex, diverse, and very large data set: namely, cyber threat data.

Synapse is the successor to the proprietary, directed graph-based analysis platform (Nucleus) used within Mandiant_ to produce the APT1_ Report.

The developers and analysts behind Synapse (and the earlier Nucleus system) came from a variety of government and commercial backgrounds but shared a common goal: the desire to record, annotate, and track cyber threat activity (specifically, nation-state level activity) both reliably and at scale. At the time when government and industry were just beginning to grasp the scope and scale of the problem, "tracking" this complex activity was largely done using long-form reports, spreadsheets, or domain knowledge residing in an analyst's mind. There was no way to effectively store large amounts of disparate data and associated analytical findings in such a way that relationships among those data and analytical conclusions were readily apparent or easily discoverable. More importantly, critical analytical decisions such as attribution were either impossible, or being made based on loose correlation, analysts' recollection, or generally accepted "truths" - and **not** based on concrete, verifiable data whose source and analysis could be traced and either verified or questioned.

In contrast, Synapse and its predecessors were **designed from the beginning** to support the following critical elements:

- The use of a **shared analytical workspace** to give all analysts access to the same data and assessments in real time.

- The idea that the analysis captured within the system should "speak for itself": that is, to the extent possible, data and analytical findings must be represented in such a way that **relationships among data and conclusions about data should be self-evident.**

These features give Synapse the following advantages:

- Synapse allows (and requires) analysts to "show their work" in a reasonably concise manner. Analysts should not have to refer to long-form reporting (or rely on the unquestioned word of a subject matter expert) to trace a line of analytical reasoning.

- Synapse allows analysts to better review and validate their findings. Conflicting analysis is highlighted through the structure of the data itself. Analysis can readily be questioned, reviewed, deconflicted, and ultimately improved.

Synapse's predecessor was designed to store a broad range of threat data, including:

- Network infrastructure
- Malware and malware behavior
- Host- and network-based incident response data
- Detection signatures and signature hits
- Decoded network packet captures
- Targeting of organizations, individuals, and data
- Threat groups and threat actors
- People and personas
- Newsfeeds and reference materials

Synapse is the evolution of this technology, built on approximately six years of technical and analytical lessons learned  combined with four years (and counting!) of development and real-world use of Synapse itself:

- Synapse's hypergraph design addresses many of the shortcomings identified with earlier directed graph and prototype hypergraph systems.

- Because our experience taught us the power of a flexible analysis platform over **any** large and disparate data set, Synapse has been designed to be flexible, modular, and adaptable to **any** knowledge domain - not just threat data.

Many of the real-world examples in this User Guide reference data from the fields of information technology or threat tracking, given Synapse’s history. But Synapse's structures, processes, and queries can be applied to other knowledge domains and data sets as well. **The intent of Synapse is that any data that could be represented in a spreadsheet, database, or graph database can be represented in a Synapse hypergraph using an appropriate data model.**

.. _Mandiant: https://www.mandiant.com/
.. _APT1: https://www.mandiant.com/media/9941/download

