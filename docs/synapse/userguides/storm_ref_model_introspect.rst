



.. highlight:: none

.. _storm-ref-model-introspect:

Storm Reference - Model Introspection
=====================================

This section provides a brief overview / tutorial of some basic Storm queries to allow introspection / navigation of Synapse's:

- `Data Model`_
- `Analytical Model`_

The sample queries below are meant to help users new to Synapse and Storm get started examining forms and tags within a Cortex. The queries all used standard Storm syntax and operations (such as pivots). For more detail on using Storm, see :ref:`storm-ref-intro` and related Storm topics.

Data Model
----------

Analysts working with the data in the Synapse hypergraph will quickly become familiar with the forms they work with most often. However, as the model expands - or when first learning Synapse - it is helpful to be able to easily reference forms that may be less familiar, as well as how different forms relate to each other.

While the data model can be referenced within the Synapse source code_ or via the auto-generated online documentation_, it can be inconvenient to stop in the middle of an analytical workflow to search for the correct documentation. It is even more challenging to stop and browse through extensive documentation when you’re not sure what you’re looking for (or whether an appropriate form exists for your needs).

For these reasons Synapse supports **data model introspection** within the Synapse hypergraph itself - that is, the Synapse data model is itself data stored within the Cortex. Introspection allows users to obtain the model definition for a given Cortex at run-time. The model definition contains a list of all native and custom types, forms, and properties supported by the current Cortex.

These model elements are generated as nodes in the Cortex from the current Synapse data model when a Cortex is initialized or when a new module is loaded. As nodes, they can be lifted, filtered, and pivoted across just like other nodes. However, the model-specific nodes do not persist permanently in storage and they cannot be modified (edited) or tagged. Because they are generated at run-time they are known as run-time nodes or **runt nodes.**

The following runt node forms are used to represent the Synapse data model for types, forms, and properties, respectively.

- ``syn:type``
- ``syn:form``
- ``syn:prop``

As nodes within the Cortex, these forms can be lifted, filtered, and pivoted across using the Storm query language, just like any other nodes (with the exception of editing or tagging). Refer to the various Storm documents for details on Storm syntax. A few simple example queries are provided below to illustrate some common operations for model introspection.

Example Queries
+++++++++++++++

- Display all current types / forms / properties:


.. parsed-literal::

    syn:type



.. parsed-literal::

    syn:form



.. parsed-literal::

    syn:prop


- Display all types that are sub-types of 'string':


.. parsed-literal::

    syn:type:subof = str


- Display a specific type:


.. parsed-literal::

    syn:type = inet:fqdn


- Display a specific form:


.. parsed-literal::

    syn:form = inet:fqdn


- Display a specific property of a specific form:


.. parsed-literal::

    syn:prop = inet:ipv4:loc


- Display a specific form and all its secondary properties (including universal properties):


.. parsed-literal::

    syn:prop:form = inet:fqdn


- Display all properties whose type is ``inet:fqdn``:


.. parsed-literal::

    syn:prop:type = inet:fqdn


- Display all forms **referenced by** a specific form (i.e., the specified form contains secondary properties that are themselves forms):


.. parsed-literal::

    syn:prop:form = inet:whois:rec :type -> syn:form


- Display all forms that **reference** a specific form (i.e., the specified form is a secondary property of another form):


.. parsed-literal::

    syn:form = inet:whois:rec -> syn:prop:type :form -> syn:form


Analytical Model
----------------

As the number of tags used in the hypergraph increases, analysts must be able to readily identify tags, tag hierarchies, and the precise meaning of individual tags so they can be applied and interpreted correctly.

Unlike the runt nodes used for the Synapse data model, the ``syn:tag`` nodes that represent tags are regular objects in the Cortex that can be lifted, filtered, and pivoted across (as well as edited, tagged, and deleted) just like any other nodes. In a sense it is possible to perform **"analytical model introspection"** by examining the nodes representing a Cortex's analytical model (i.e., tags).

Lifting, filtering, and pivoting across ``syn:tag`` nodes is performed using the standard Storm query syntax; refer to the various Storm documents for details on using Storm. See also the ``syn:tag`` section of :ref:`storm-ref-type-specific` for additional details on working with ``syn:tag`` nodes.

A few simple example queries are provided below to illustrate some common operations for working with tags. As Synapse does not include any pre-populated ``syn:tag`` nodes, these examples assume you have a Cortex where some number of tags have been created.

Example Queries
+++++++++++++++

- Lift a single tag:


.. parsed-literal::

    syn:tag = cno.infra.anon.tor


- Lift all root tags:


.. parsed-literal::

    syn:tag:depth = 0


- Lift all tags one level "down" from the specified tag:


.. parsed-literal::

    syn:tag:up = cno.infra.anon


- Lift all tags that start with a given prefix, regardless of depth:


.. parsed-literal::

    syn:tag ^= cno.infra


- Lift all tags that share the same base (rightmost) element:


.. parsed-literal::

    syn:tag:base = sofacy



.. _code: https://github.com/vertexproject/synapse
.. _documentation: https://vertexprojectsynapse.readthedocs.io/en/latest/
