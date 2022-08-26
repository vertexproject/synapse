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

Forms
-----

In the majority of cases, if there is something you want to represent in Synapse, it should be a form (especially given
Synapse's hypergraph-based architecture!). Synapse's data model can represent everything from objects, to relationships,
to events as forms. (See :ref:`data-model-object-categories` for a more detailed discussion.)

Forms are more "fixed" in the data model - more structured and less likely to change. They should be used to represent
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

Properties
----------

Properties are those details that further define a form. They can be viewed as the form's characteristics - those things
that further "define" a form. When creating a form, there are probably a number of "things you want to record" about the
form that immediately come to mind. These are obvious candidates for properties.

A few considerations when designing properties:

- Properties should be highly "intrinsic" to their forms. The more closely related something is to an object, the more
  likely it should be a property. Things that are not highly intrinsic are better candidates for their own forms, for
  "relationship" forms, or for tags.

- Consider whether a property has enough "thinghood" to also be its own form (and possibly type).

- The data model supports multi-value :ref:`type-array` properties, but arrays are not meant to store an excessive
  number of values (largely for performance and visualization purposes). In this situation, a "relationship" form
  might be preferable. Another option would be to "reverse" the property relationship.
  
  For example, a compromise (``risk:compromise``) may consist of a number of different attacks (``risk:attack``)
  representing steps in the overall compromise. Instead of ``risk:compromise`` having an ``:attacks`` array with a
  large number of values, a ``risk:attack`` has a ``:compromise`` property so that multiple attacks can be linked
  back to a single compromise.
 
Light Edges
-----------

Light edges can replace "relationship" forms in cases where:

- You do not need properties to further describe the relationship.
- You do not need to apply tags to give context to the relationship.
- The object on one or both sides of the relationship could be any object.

See :ref:`data-light-edge` for additional discussion.

Tags
----

Tags should be used in for:

- Observations or assessments that may change. The flexibility to add, remove, and migrate or change tags makes
  them useful to represent information that may be re-evaluated over time.
 
- Any time you need to arbitrarily group nodes to identify a subset of data or otherwise aid your analysis. For
  example:
  
  - ``media:news`` nodes can represent a wide range of publications, from public whitepapers to internal incident
    reports. Tags could be used to identify different types of ``media:news`` nodes to make certain nodes easier
    to select (lift).
    
  - Things tracked using tags (such as threat clusters or threat groups) can easily grow to tens or hundreds of
    thousands of nodes. A report on the threat group will not include every node. A tag can be used to indicate
    the "key" nodes / data points / items of interest that form the basis of a report.

- Cases where having a tag on a node provides valuable context for an analyst looking at the node (i.e., knowing
  that an IP address is a TOR exit node).

Tags Associated with Forms
--------------------------
  
    
