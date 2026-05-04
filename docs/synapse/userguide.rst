.. _userguide:

Synapse User Guide
##################

This **User Guide** is written by and for Synapse users and provides a user-focused overview of Synapse concepts and
operations. Technical documentation appropriate for Synapse deployment, development, and administration can be found
elsewhere in the `Document Index`_.

The User Guide is a living document and will be updated and expanded as appropriate.

.. toctree::
   :maxdepth: 1
   :caption: Contents:
   
   userguides/background
   userguides/data_model
   userguides/analytical_model
   userguides/views_layers
   userguides/index_storm_ref
   userguides/index_storm_adv
   userguides/index_tools
   userguides/index_model_updates

- The **Background**, **Data Model**, and **Analytical Model** sections provide an overview of Synapse's knowledge graph and
  the elements that make up the graph.
- The **Views and Layers** section describes Synapse's basic data storage architecture, and the ways in which data
  can be stored, shared, and segregated if necessary.
- The **Storm** sections describe Synapse's native query language, including background, syntax, examples, ways to use
  Storm to automate workflows and analysis, and advanced use cases for Storm power users.
- The **Tools** section describes the built-in tools that can be used to interact with and manage your Synapse instance,
  including the :ref:`syn-tools-storm` tool (Storm CLI). (**Note:** If you are a Synapse Enterprise user, or have a Synapse
  `demo instance`_, you will typically interact with Synapse using the web-based `Optic UI`_.)
- The **Model Updates** section is a changelog that lists changes and updates to the Synapse :ref:`userguide_datamodel`.

We have made a reasonable effort to introduce concepts in a logical order. That said, we don't expect anyone to
read through the entire User Guide! It is meant to provide useful background and reference material as needed. In addition,
many of the concepts in the Guide are closely related - for example, it is difficult to fully grasp the power of Synapse
without understanding Storm (and vice versa). We encourage you to skip around or revisit sections as needed.

.. _`Document Index`:  ../index.html
.. _`demo instance`:   https://vertex.link/request-a-demo
.. _`Optic UI`:        https://synapse.docs.vertex.link/projects/optic/en/latest/index.html
