.. toctree::
    :titlesonly:

.. _intro:

Introduction
############

**Synapse** is a versatile central intelligence and analysis system created to support analyst teams in every stage of the intelligence life cycle.

The_Vertex_Project_ designed and developed Synapse to help analysts and algorithms answer complex questions which require the fusion of large data sets from disparate sources that span multiple disciplines.

Synapse's data store (known as a :ref:`gloss-cortex`) is organized as a hypergraph_. Combined with its structured and extensible :ref:`userguide_datamodel` and the powerful and intuitive :ref:`gloss-storm` query language, Synapse gives analysts unparalleled power and flexibility to ask and answer any question, even over large and complex data sets.

Key Features
============

 - **Extensible Data Model.** Synapse includes an extensive (and extensible) :ref:`userguide_datamodel` capable of representing real-world objects, relationships, and events in an intuitive and realistic manner.
 
 - **Strong Typing.** Synapse uses :ref:`gloss-type-norm` and :ref:`gloss-type-enforce` to apply meaningful constraints to data to ensure it well-formed, preventing "bad data" from cluttering the knowledge store. :ref:`gloss-type-aware` simplifies use of the Storm query language and helps analysts discover novel relationships in the data.
 
 - **Powerful and Intuitive Query Language.** Synapse's :ref:`gloss-storm` query language is a powerful, intuitive "data language" used to interact with data in a Synapse Cortex. Storm frees analysts from the limitations of "canned" queries or hard-coded data navigation and allows them to ask - and answer - **any** analytical question.
 
 - **Unified Analysis Platform.** Synapse's unified data store provides analysts with a shared view into the same set of data and analytical annotations, allowing them to better coordinate, collaborate, and peer-review their work.
 
 - **Modular Architecture.** Synapse's functionality is extensible through **Power-Ups** (see :ref:`gloss-power-up`) that add functionality, integrate with third-party data sources, or connect to external databases.
 
 - **Record Analytical Assessments.** Synapse allows analysts to annotate data with assessments and observations through a flexible and extensible set of tags (:ref:`gloss-tag`). By recording assessments (as well as data) in a structured manner, analysts and algorithms can leverage **both** in their queries and workflows.
 
 - **"Git for Analysis".** Synapse supports the use of layers (:ref:`gloss-layer`) to comprise a :ref:`gloss-view` into Synapse's data store. Analysts can create a :ref:`gloss-fork` of a given view and use it for testing or research without modifying the underlying production data. Once work in the fork is complete, changes can be merged into the production view or discarded.
 
 - **Fine-Grained Access Controls.** Synapse provides access controls and detailed permissions that can be applied to users or roles. Permissions can be specified broadly or to a level of detail that restricts a user to setting a single property on a single form.
 
 - **Flexible Automation.** Synapse allows you to create custom automation for both analytical and administrative tasks, ensuring consistency and eliminating tedious or time-consuming workflows. Automation (see :ref:`storm-ref-automation`) is provided using event-based triggers (:ref:`gloss-trigger`), scheduled cron jobs, or stored macros.
 
 - **API Access.** Synapse includes multiple well-documented APIs (HTTP/REST, Python) for interacting with the data store and other Synapse components.
 
 - **Lightning Fast Performance.** Synapse uses LMDB for high-performance key-value indexing and storage, combined with asynchronous, streaming processing. This means queries start returning results as soon as they are available - so your "time to first node" is typically milliseconds, regardless of the size of your result set.
 
 - **Horizontally and Vertically Scalable.** A standard Synapse Cortex can store on the scale of one billion nodes. Synapse also supports <stuff / mirroring / other cool things blah blah>.

 
What's Next?
============

+------------------+-----------------------------------------------+
| **Get Started!** | Synapse_Quickstart_                           |
|                  |   Get up and running quickly with Synapse     |
|                  |     open source!                              |
|                  | :ref:`quickstart`                             |
|                  |   Detailed setup / configuration instructions |
|                  | :ref:`faq`                                    |
|                  | Attend Synapse_101_                           |
|                  | Request_ a Commercial Synapse demo instance   |
|                  |   Includes Synapse's graphical UI             |
|                  |                                               |
+------------------+-----------------------------------------------+
| **Users**        | :ref:`userguide`                              |
|                  | :ref:`userguide_storm_ref`                    |
|                  | :ref:`changelog`                              |
|                  | Ask a question or see our latest releases in  |
|                  |  Slack_                                       |
+------------------+-----------------------------------------------+
| **DevOps**       | :ref:`devopsguide`                            |
|                  | Synapse sizing_guide_                         |
+------------------+-----------------------------------------------+
| **Developers**   | :ref:`devguide`                               |
|                  | :ref:`http-api`                               |
|                  | :ref:`apidocs`                                |
|                  | :ref:`dm-index`                               |
|                  | :ref:`stormtypes_index`                       |
+------------------+-----------------------------------------------+
| **Learn More**   | Upcoming Webinars_                            |
|                  | Video Library_                                |
|                  | Visit The Vertex Project Website_             |
+------------------+-----------------------------------------------+
| **Connect!**     | Slack_                                        |
|                  | Twitter_                                      |
|                  | LinkedIn_                                     |
|                  | "Star" us on Github_                          |
+------------------+-----------------------------------------------+


.. _The_Vertex_Project: https://vertex.link/
.. _hypergraph: https://en.wikipedia.org/wiki/Hypergraph

.. _Synapse_QuickStart: https://github.com/vertexproject/synapse-quickstart
.. _Synapse_101: https://lu.ma/vertexproject
.. _Request: https://vertex.link/contact-us

.. _Slack: https://join.slack.com/t/synapsechat/shared_invite/zt-fldtp6xg-fjyFS5Z1nwiNUtmKvuo2Mg

.. _sizing_guide: https://docsend.com/view/kmbkkq9pjhtjsbmk

.. _Webinars: https://lu.ma/vertexproject
.. _Library: https://vimeo.com/vertexproject
.. _Website: https://vertex.link/

.. _Twitter: https://twitter.com/vtxproject
.. _LinkedIn: https://www.linkedin.com/company/vertexproject/
.. _Github: https://github.com/vertexproject/synapse
