
Background - Model Introspection
================================

In order to query and pivot through data in the Synapse hypergraph effectively, analysts must have some familiarity with the Synapse data model. Analysts will quickly become familiar with forms they work with most often; but as the model expands it is helpful to be able to easily reference forms that may be less familiar. Similarly, as the number of tags used in the hypergraph increases, analysts must be able to readily identify tags, tag hierarchies, and the precise meaning of individual tags so they can be applied and interpreted correctly.

  * `Data Model (Form) Introspection`_
  * `Analytical Model (Tag) Introspection`_

Data Model (Form) Introspection
-------------------------------

The Synapse data model can be referenced directly within the `source code`_ of the appropriate Synapse module. Similarly, the Synapse documentation includes a `data model dictionary`_ that is automatically built from the Synapse source code.

However, the “definition” of the Synapse data model is also part of the data model itself - that is, elements of the model can be queried and viewed from within Synapse itself.

**TBD**

Analytical Model (Tag) Introspection
------------------------------------

In Synapse, tags are nodes within the hypergraph (of the form ``syn:tag``) and can be lifted, filtered, and pivoted across just like any other nodes. The ``syn:tag`` form includes secondary properties (``:title`` and ``:doc``) that are meant to store a definition for the tag. In practice, ``:title`` is often used for a brief definition and ``:doc`` is used for a more lengthy and detailed description.

A sample tag node might look like this:

::

  syn:tag = aka.feye.thr.apt1
          .created = 2018/05/17 17:11:36.967
          :base = apt1
          :depth = 3
          :doc = Indicator or activity FireEye calls (or associates with) the APT1 threat group.
          :title = APT1 (FireEye)
          :up = aka.feye.thr

The ``:base``, ``:depth``, and ``:up`` secondary properties help to describe a tag in relation to other tags (within or across tag hierarchies) and can be used to pivot to other relevant tag nodes.

Synapse’s Storm query language can be used to view and examine tags and tag trees:

To lift a single tag:

    ``cli> storm syn:tag=<tag>``

To list all root tags:

    ``cli> storm syn:tag:depth=0``

To list all tags one level “down” from the current tag:

    ``cli> storm syn:tag=<tag> -> syn:tag:up``

To list all tags that share the same base (leaf) element:

    ``cli> storm syn:tag:base=<base>``


.. _`source code`: 
.. _`data model dictionary`: ../../datamodel.html
