.. toctree::
    :titlesonly:

.. _intro:

Introduction
############

**Synapse** is a versatile central intelligence and analysis system created to support analyst teams
in every stage of the intelligence life cycle.

`The Vertex Project`_ designed and developed Synapse to help analysts and algorithms answer complex
questions which require the fusion of large data sets from disparate sources that span multiple disciplines.

Synapse's data store (known as a :ref:`gloss-cortex`) is organized as a hypergraph_. Combined with its
structured and extensible :ref:`userguide_datamodel` and the powerful and intuitive :ref:`gloss-storm`
query language, Synapse gives analysts unparalleled power and flexibility to ask and answer any question,
even over large and complex data sets.

.. note::

    A :ref:`gloss-cortex` may easily grow to billions of nodes, but is not designed to consume and create billions of
    nodes per day. In other words, Synapse is not meant to replace your big-data/data-lake storage; Synapse is
    designed to connect to your data sources on demand in order to ingest data relevant for your analysis into the
    Synapse intelligence platform.

.. _intro-features:

Key Features
============

**Extensible Data Model**

Synapse includes an extensive (and extensible) :ref:`userguide_datamodel` capable of representing
real-world objects, relationships, and events in an intuitive and realistic manner.
 
**Strong Typing**

Synapse uses :ref:`gloss-type-norm` and :ref:`gloss-type-enforce` to apply meaningful constraints to data
to ensure it is well-formed, preventing "bad data" from cluttering the knowledge store. :ref:`gloss-type-aware`
simplifies use of the Storm query language and helps analysts discover novel relationships in the data.
 
**Powerful and Intuitive Query Language**

Synapse's :ref:`gloss-storm` query language is a powerful, intuitive "data language" used to interact
with data in a Synapse Cortex. Storm frees analysts from the limitations of "canned" queries or
hard-coded data navigation and allows them to ask - and answer - **any** analytical question.
 
**Unified Analysis Platform**

Synapse's unified data store provides analysts with a shared view into the same set of data and
analytical annotations, allowing them to better coordinate, collaborate, and peer-review their work.

**Designed and Tested in Partnership with Analysts**

Synapse is the product of a unique close collaboration between Vertex developers and analysts that
leverages innovative software design and engineering to directly support analyst needs and workflows.
 
**Modular Architecture**

Synapse is extensible through **Power-Ups** (see :ref:`gloss-power-up`) that add functionality,
integrate with third-party data sources, or connect to external databases.
 
**Record Analytical Assessments**

Synapse allows analysts to annotate data with assessments and observations through a flexible and 
extensible set of tags (see :ref:`gloss-tag`). By recording assessments **and** data in a
structured manner, analysts and algorithms can leverage **both** in their queries and workflows.
 
**"Git for Analysis"**

Synapse supports the use of layers (see :ref:`gloss-layer`) to comprise a :ref:`gloss-view` into
Synapse's data store. Analysts can create a :ref:`gloss-fork` of a given view and use it for testing
or research without modifying the underlying production data. Once work in the fork is complete,
changes can be merged into the production view or discarded.
 
**Fine-Grained Access Controls**

Synapse provides access controls and detailed permissions that can be applied to users or roles. 
Permissions can be specified broadly or to a level of detail that restricts a user to setting a
single property on a single form.
 
**Flexible Automation**

Synapse allows you to create custom automation for both analytical and administrative tasks, 
ensuring consistency and eliminating tedious or time-consuming workflows. Automation
(see :ref:`storm-ref-automation`) is provided using event-based triggers (:ref:`gloss-trigger`),
scheduled cron jobs, or stored macros.
 
**API Access**

Synapse includes multiple well-documented APIs for interacting with the data store and other
Synapse components. (See :ref:`http-api` and :ref:`apidocs`.)
 
**Lightning Fast Performance**

Synapse uses LMDB for high-performance key-value indexing and storage, combined with asynchronous,
streaming processing. This means queries start returning results as soon as they are available -
so your "time to first node" is typically milliseconds, regardless of the size of your result set.
 
**Horizontally and Vertically Scalable**

A single Synapse Cortex can easily scale vertically to hold tens of billions of nodes. In addition,
Synapse supports high-availability topologies such as mirroring.

 
What's Next?
============

+----------------------+-----------------------------------------------+
| **Get Started!**     | - There are several options for you to deploy |
|                      |   and start using Synapse! See our            |
|                      |   :ref:`quickstart` guide to see which one is |
|                      |   right for you.                              |
|                      |                                               | 
|                      | - Watch `Synapse 101`_                        |
|                      |                                               |
+----------------------+-----------------------------------------------+
| **Users**            | - :ref:`userguide`                            |
|                      | - :ref:`userguide_storm_ref`                  |
|                      | - Changelog_                                  |
|                      | - Ask a question in Slack_                    |
+----------------------+-----------------------------------------------+
| **DevOps**           | - :ref:`devopsguide`                          |
|                      | - :ref:`deploymentguide`                      |
|                      | - Synapse `sizing guide`_                     |
+----------------------+-----------------------------------------------+
| **Developers**       | - :ref:`devguide`                             |
|                      | - :ref:`http-api`                             |
|                      | - :ref:`apidocs`                              |
|                      | - :ref:`dm-index`                             |
|                      | - :ref:`stormtypes_index`                     |
+----------------------+-----------------------------------------------+
| **Admins**           | - :ref:`adminguide`                           |
+----------------------+-----------------------------------------------+
| **Synapse UI**       | - `Synapse UI`_ ("Optic") documentation       |
| (commercial)         |   (includes guides for users, devops, and     |
|                      |   developers)                                 |
+----------------------+-----------------------------------------------+
| **Learn More**       | - Upcoming Webinars_                          |
|                      | - Video Library_                              |
|                      | - Visit The Vertex Project Website_           |
+----------------------+-----------------------------------------------+
| **Connect With Us!** | - Slack_                                      |
|                      | - Twitter_                                    |
|                      | - LinkedIn_                                   |
|                      | - "Star" us on Github_                        |
+----------------------+-----------------------------------------------+

.. _`The Vertex Project`: https://vertex.link/
.. _hypergraph: https://en.wikipedia.org/wiki/Hypergraph

.. _`Synapse 101`: https://v.vtx.lk/syn101

.. _Changelog: https://synapse.docs.vertex.link/en/latest/synapse/changelog.html
.. _Slack: https://v.vtx.lk/join-slack

.. _`sizing guide`: https://docsend.com/view/kmbkkq9pjhtjsbmk

.. _`Synapse UI`: https://synapse.docs.vertex.link/projects/optic/en/latest/index.html

.. _Webinars: https://v.vtx.lk/luma
.. _Library: https://v.vtx.lk/youtube
.. _Website: https://vertex.link/

.. _Twitter: https://v.vtx.lk/twitter
.. _LinkedIn: https://v.vtx.lk/linkedin
.. _Github: https://github.com/vertexproject/synapse
