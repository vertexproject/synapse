<a id="userguide"></a>


# Synapse User Guide

This **User Guide** is written by and for Synapse users and provides a user-focused overview of Synapse concepts and operations. Technical documentation appropriate for Synapse deployment, development, and administration can be found elsewhere in the [Document Index](index.md).

The User Guide is a living document and will be updated and expanded as appropriate.

```mdtoc --caption 'Contents:'
userguides/background.md
userguides/data_model.md
userguides/analytical_model.md
userguides/views_layers.md
userguides/index_storm_ref.md
userguides/index_storm_adv.md
userguides/index_tools.md
```

- The **Background**, **Data Model**, and **Analytical Model** sections provide an overview of Synapse's knowledge graph and the elements that make up the graph.
- The **Views and Layers** section describes Synapse's basic data storage architecture, and the ways in which data can be stored, shared, and segregated if necessary.
- The **Storm** sections describe Synapse's native query language, including background, syntax, examples, ways to use Storm to automate workflows and analysis, and advanced use cases for Storm power users.
- The **Tools** section describes the built-in tools that can be used to interact with and manage your Synapse instance, including the [storm](userguides/syn_tools_storm.md#syn-tools-storm) tool (Storm CLI). (**Note:** If you are a Synapse Enterprise user, or have a Synapse [demo instance](https://vertex.link/request-a-demo), you will typically interact with Synapse using the web-based [Optic UI](/docs/synapse-enterprise-optic/latest/index.md).)

We have made a reasonable effort to introduce concepts in a logical order. That said, we don't expect anyone to read through the entire User Guide! It is meant to provide useful background and reference material as needed. In addition, many of the concepts in the Guide are closely related - for example, it is difficult to fully grasp the power of Synapse without understanding Storm (and vice versa). We encourage you to skip around or revisit sections as needed.
