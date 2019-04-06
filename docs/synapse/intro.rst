.. toctree::
    :titlesonly:

.. _intro:

Introduction
############

**Synapse** is a "batteries included" intelligence analysis platform designed to help analysts and algorithms answer complex questions which require the fusion of data across different disciplines.  It was developed as the successor to a proprietary graph-based analysis platform named **Nucleus** which was used within Mandiant_ to produce the APT1_Report_.  While Synapse was initially designed for use in the cyber threat intelligence discipline, the built-in data model has expanded into including a wide variety of subject matter areas such as geopolitical, geospatial, human behavior, and even the physical world.  For an analyst's perspective see the :ref:`bkd-why-synapse` section of the :ref:`userguide`.

Within a Synapse **Cortex**, knowledge is organized within a hypergraph_. Access to the unified Cortex data model allows subject matter experts to perform and record detailed analysis within their area of expertise and answer inter-disciplinary questions facilitated by other analyst's annotations.  Each assertion made by an analyst or algorithm may be recorded to build toward higher-level assertions, such as cyber threat actor attribution, which require extensive supporting evidence.  The "decomposability" of higher-level assertions allows peer review and decision-maker confirmation.  This helps to prevent analysis predicated on "because so-and-so said so" and helps analysts collaborate and learn from each other's work.

Features
========

*High Performance / Streaming*

A Synapse Cortex uses the high-performance key-value store LMDB_ for indexing and storage.  Additionally, the **Storm** query engine is designed to produce results as a stream rather than a set.  This means a query will begin returning results as soon as they are available rather than waiting for the complete result set.  Streaming results means that even a complex multi-pivot query which will eventually return millions of nodes will begin producing results immediately.  API interfaces facilitate streaming "back-pressure" which allows a query consumer to incrementally read result sets no matter how large they are.

*Rich Built-In/Extensible Data Model*

The Synapse data model has been battle-hardened over 5 years through the lessons learned during intelligence analysis and production.  See the :ref:`userguide` for extensive details.

*Simple/Powerful Query Language*

The Storm query language was designed with analysts in mind.  Storm seeks to strike a balance of simplicity and power to provide analysts a lightweight syntax to quickly express the desired data and relationships of interest while also making it possible to perform complex analysis.  Years of analyst use cases and observations have gone into creating an efficient way to not only perform analysis, but record the resulting assertions.  See the :ref:`userguide` for details on the Storm query language and Cortex-based analysis concepts.

*HTTPS API*

An HTTPS API allows stream-based access to the Storm query language through HTTP chunked-encoding results.  Additionally, REST APIs may be used to configure and control additional subsystems and components.

*Granular Access Controls*

Individual users and roles may be configured with permissions to restrict changes to the Cortex based on areas of expertise.

*Automation/Triggers*

Analysts may configure Cortex **Triggers** which execute additional Storm queries when particular changes occur within the Cortex.

*Scheduled Queries*

A Cortex provides a cron-like interface for scheduling background execution of one-time or recurring Storm queries.

*Change Auditing / Provenance*

A Cortex produces a stream of potentially reversible changes called **splices** which can account for every change to the hypergraph_.  Additionally, provenance tracking for splices records the cause for individual changes, even in the event of firing Triggers or other automation that could make it difficult to understand the cause for a splice.

What's New?
===========

The release of Synapse 0.1.0 represents a huge leap forward from the previous Synapse releases.  Rather than attempt to list them here, please see the :ref:`userguide` for details!

Moving forward, subsequent ``0.1.x`` releases will be documented in the :ref:`changelog`.

FAQ
===

What's the state of interface stability for 0.1.x?
--------------------------------------------------

With the release of Synapse 0.1.0, we are committed to maintaining a stable and backward-compatible release process.  Public-facing interfaces such as Storm, the HTTPS API, and the **Telepath** API will not be changed in any way that will break existing deployments.  The data model will only be updated with additions which do not change existing property names or relationships.

Performance, big-data, scalability, and best use?
-------------------------------------------------

A Synapse Cortex is a knowledge system which must deconflict each new piece of information received to determine if the knowledge is already present.  This makes it ideal for creating a permanent record of relevant observations and analysis results.  However, the deconfliction required for a knowledge system is fundamentally at-odds with the idea of an infinitely scalable stream of instance/temporal data.  A Cortex may easily grow to billions of nodes, but is not designed for use cases involving billions of records per-day.  In a typical big-data/data-lake architecture, a Cortex is optimally used to analyze data resulting from queries to existing platforms and fuse data relevant to an analyst's investigation.

We currently operate several Cortex instances in production use that contain on the order of billions of nodes on a single server.  Additionally, a Cortex may also be configured to fuse data from a remote Cortex into a single view.  This allows for simple sharding based on data ingest sources.  To parallelize read-performance and maximize availability, a Cortex may have one or more mirrors configured.  Additional information on advanced configurations will be available shortly in the :ref:`devopsguide`.

What kind of server(s) should I spec out?
-----------------------------------------

The performance profile and system requirements for a Cortex are very similar to a typical large RDBMS such as **PostgreSQL**.  For high performance, use low-latency (flash style) storage and a RAM optimized server build.  A Cortex must deconflict each new node it adds, which means that RAM availability and storage latency directly effect throughput.

Did you consider SPARQL/GraphQL/etc rather than Storm?
------------------------------------------------------

The short answer on this is *yes*.  After extensive review of the data languages and query languages available on several platforms, none met the ambitious requirements for simultaneously providing a terse analyst-friendly syntax and the expressive power needed for analysis within a hypergraph_.

.. _Mandiant: https://www.fireeye.com/services.html 
.. _APT1_Report: https://www.fireeye.com/content/dam/fireeye-www/services/pdfs/mandiant-apt1-report.pdf
.. _LMDB: https://symas.com/lmdb/
.. _hypergraph: https://en.wikipedia.org/wiki/Hypergraph
