.. highlight:: none

.. _design-general:

Design Concepts - General
=========================

In designing both data and analytical models, one of the first choices that must be made is whether something should be represented as:

- a form
- a property
- a light edge
- a tag
- a tag associated with a form

Every modeling decision is unique, and a full discussion of the modeling process is beyond the scope of these documents.
We include some basic guidance below as background.

.. _design-forms:

Forms
-----

In the majority of cases, if there is something you want to represent in Synapse, it should be a form. Synapse's data
model can represent everything from objects, to relationships, to events as forms. (See :ref:`data-model-object-categories`
for a more detailed discussion.)

As part of Synapse's data model, forms are more structured and less likely to change. This structure allows you to more
easily identify relationships between objects in Synapse and to navigate the data. Forms should be used to represent
things that are observable or verifiable at some level - this is true even for more abstract forms like "vulnerabilities"
(``risk:vuln``) or "goals" (``ou:goal``). If something represents an assessment or conclusion, it is likely a better
candidate for a tag.

In designing a form, we recommend not "over-fitting" the form to a specific use case. As a simple example, an email 
address is an email address - there is no difference between a email address used as an email sender and an email address
used to register a domain. Creating two separate objects for ``email:sender`` and ``email:registrant`` confuses the
**object** (an email address) with **how the object is used**. The "how" is apparent in other parts of the data model (e.g.,
when used as an email sender, the email address will be present in the ``:from`` property of an ``inet:email:message``).

We also recommend desiging forms broadly - this may require some out-of-the-box thinking to consider how the form may
apply to other fields, disciplines, or even locales ("how something works" in the United States may be different from how
it works in Argentina or Malaysia).

.. _design-props:

Properties
----------

Properties are details that further define a form. When creating a form, there are probably a number of "things you want
to record" about the form that immediately come to mind. These are obvious candidates for properties.

A few considerations when designing properties:

- Properties should be highly "intrinsic" to their forms. The more closely related something is to an object, the more
  likely it should be a property of that object. Things that are not highly intrinsic are better candidates for their own
  forms, for "relationship" forms, or for tags.

- Consider whether a property has enough "thinghood" to also be its own form (and possibly type).

- The data model supports multi-value :ref:`type-array` properties, but arrays are not meant to store an excessive
  number of values (largely for performance and visualization purposes). In this situation, a "relationship" form
  might be preferable. Another option would be to "reverse" the property relationship.
  
  For example, a compromise (``risk:compromise``) may consist of a number of different attacks (``risk:attack`` nodes)
  representing steps in the overall compromise. Instead of ``risk:compromise`` having an ``:attacks`` array with a
  large number of values, a ``risk:attack`` has a ``:compromise`` property so that multiple attacks can be linked
  back to a single compromise.

.. _design-edges:

Light Edges
-----------

While it is preferable to represent most relationships as forms (which can record additional properties as well as
tags), light edges can replace "relationship" forms in cases where additional properties or tags are unnecessary.

A more important criteria is where the object on one or both sides of the relationship could be any object.

- A data source (``meta:source`` node) can observe or provide data on various objects (such as a hash or an FQDN).
  Creating a relationship form to represent each possible combination of ``meta:source`` node and object complicates
  the data model. This "one-to-many" relationship can be represented more efficiently with a ``seen`` light edge.

- Similarly, a variety of objects (articles / ``media:news`` nodes, presenatations / ``ou:presentation`` nodes,
  files / ``file:bytes`` nodes, etc.) may contain references to a range of objects of interest, from indicators to
  people to events. This "many-to-many" relationship can be represented more efficiently with a ``refs`` (references)
  light edge.

See :ref:`data-light-edge` for additional discussion.

.. _design-tags:

Tags
----

Tags should be used for:

- Observations or assessments that may change. The flexibility to add, remove, and migrate or change tags makes
  them useful to represent information that may be re-evaluated over time.
 
- Any time you need to arbitrarily group nodes to identify a subset of data or otherwise aid your analysis. For
  example:
  
  - ``media:news`` nodes can represent a wide range of publications, from public whitepapers to internal incident
    reports. Tags could be used to identify different types of ``media:news`` nodes to make certain nodes easier
    to select (lift).
    
  - Data tracked using tags (such as indicators or other objects associated with threat clusters - i.e.,
    ``#cno.threat.<threat>``) can easily grow to tens or hundreds of thousands of nodes. A report on the threat
    group will not include every tagged node. A tag can be used to indicate the "key" nodes / data points / items
    of interest that form the basis of a report. (The Vertex Project uses "story" tags and subtags to represent key
    elements of a report / "story" - for example ``vtx.story.<storyname>``, ``vtx.story.<storyname>.core``, etc.)

- Cases where having a tag **on a node** provides valuable context for an analyst looking at the node (i.e., knowing
  that an IP address is a TOR exit node). While this same context may be available by examining nearby connections in
  the data model (e.g., an IP address may be linked to a server with an open port running the TOR service), having
  the context on the node itself is particularly useful.
  
Tags can also be used as an initial or interim means to track or record observations before transitioning to a more
structured representation using the Synapse data model. For example, cyber threat intelligence often tracks targeted
organizations based on the industry or industries they are a part of. This can be modeled in Synapse by linking an
organization (``ou:org`` node) to a set of industries (``ou:industry``) that the organization belongs to. But it is up
to Synapse users to decide on and create the set of named industries (``ou:industry`` nodes) that are most useful to
their analysis.

It may be easier to initially represent industries using tags placed on ``ou:org`` nodes (such as ``#ind.finance`` or
``#ind.telecommunications``). This allows you to "try out" (and easily change) a set of industries / industry names
before making a final decision. Later you can create the ``ou:industry`` nodes and convert the tags into model elements.

.. _design-tags-and-forms:

Tags Associated with Forms
--------------------------

In some cases, it may be useful to leverage both tags **and** forms for your analysis. This is useful in cases where
both of the following apply:

- The tag is associated with an assertion about something "concrete" (such as an event or entity) where that object
  should exist in its own right (i.e., as a node). This allows you to:
  
  - record information about the object (properties or other tags).
  - identify relationships (such as shared property values) with other objects.
  - navigate to related objects within Synapse.
  
- The tag is still useful in order to provide valuable context to **other nodes**, where this context would not be
  clear if a user had to identify it by navigating to other "nearby" data.
  
To address this need, forms in the Synapse data model can be directly linked to a tag (``syn:tag`` node) they are
associated with via an explicit ``:tag`` property. This allows you to still apply the relevant tag to other nodes
for context, but easily navigate from nodes that have the tag, to the associated ``syn:tag`` node, to the node
associated with the tag (via the ``:tag`` property).

An example from cyber threat intelligence is the idea of a threat group or threat cluster. A "threat group" is often
a notional concept that represents an unknown organization or set of individuals responsible for a set of malicious
activity. It is common to use tags (``#cno.threat.t42``) applied to nodes (such as FQDNs, files, hashes, and so on)
to associate those indicators with a specific threat group. This is valuable context to immediately identify that an
indicator is "bad" and assocaited with known activity.

But threat groups - even notional ones - still ultimately represent something in the real world. It is useful to
record additional information about the threat group, such as other names the group is known by, or a known or
suspected country of origin. Representing this information as properties makes it easier to query and pivot across,
and provides greater flexibility over trying to somehow record all of this information on the node
``syn:tag=cno.threat.t42``.

Since **both** approaches are useful, the threat group can be represented as a ``risk:threat`` node with associated
properties, but **also** linked to its associated tag (``syn:tag = cno.threat.t42``) via the ``risk:threat:tag``
property.

.. TIP::
  
  Tracking threat activity is a good example of how initially using tags can evolve into more concrete and
  structured representation in the Synapse data model. When researchers identify activity that cannot be associated
  with a known threat, they commonly create a new threat cluster to track the new incident and associated data.
  Because little is known about the activity (and associated threat), it's easiest to simply create a tag to represent
  this. As additional related activity is identified, this new threat may be linked to (and merged with) an existing
  group (``risk:threat`` node). Or, the new threat cluster may grow on its own to the point where researchers believe
  it is its own entity - at which point a new ``risk:threat`` node can be created. If, over time, the threat can be
  tied to a real world entity or organization, the ``risk:threat`` can be linked to an organization (``ou:org``) via
  the ``risk:threat:org`` property.

    
