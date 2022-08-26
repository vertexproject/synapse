.. highlight:: none

.. _design-data-model:

Design Concepts - Data Model
============================

Synapse's ability to support powerful and effective analysis is due in large part to Synapse's **data model**. The forms,
properties, and types used in Synapse are the result of our direct experience using Synapse for a broad range of analysis
(along with lively and occasionally heated internal discussion and design sessions with our developers and analysts!).

A full discussion of the considerations (and complexities) of a well-designed data model are beyond the scope of this
documentation. However, there are several principles that we rely on that help shed light on our apprroach:

- **The model is an abstraction.** A data model (and associated tags / analytical model) provide **structure** for data
  and assertions that allow us to quickly view data, relationships, and context, and to ask questions of the data in
  powerful ways. That said, analysis often involves subtle distinctions and qualifications - which is why analysis is
  often provided in long-form reports where natural language can convey uncertainties or caveats related to conclusions.
  
  Capturing data and analysis in a structured model abstracts away some of these subtleties - in some cases, trading
  them for consistent representation and programmatic access. A data model can never fully capture the richness and
  detail of a long-form report. But a **good** data model can sufficiently capture critical relationships and analytical
  findings so that an analyst only rarely needs to refer to external reporting or original sourcing for clarification.

- **The model should be self-evident.** While the model is an abstraction, it should not be abstracted to the point
  where the data and analysis in the model cannot stand on their own. While at times supplemental external reports or
  notes may be helpful, they should not be **required** to understand the information represented in Synapse. The model
  should convey the maximum amount of information possible: objects, relationships, and annotations should be unambiguous,
  well-defined, and clearly understood. An analyst with subject matter knowledge but no prior exposure to a given set of
  findings should be able to look at that information in Synapse and understand the analytical line of thought.

- **Take the broadest perspective possible.** Many data models suffer from being "overly-fitted". They are designed for
  a specific analytical discipline and the objects and relationships they contain reflect a narrow use case. We believe
  that Synapse's data model should represent objects and relationships as they are **in the real world** - not just "as
  they are used" in a particular limited context. For example, an "organization" (``ou:org``) in Synapse can represent
  any set of people with a common goal - from a company, to a government, to a threat group, to a department, to your
  kid's soccer team. This makes the model both more flexible and more broadly applicable so we can easily incorporate
  new data sets / sources and additional types of analysis.

- **The model should be driven by real-world need and relevance.** Any model should be designed around the analytical
  questions that it needs to be answer. Some models are designed as academic abstractions ("how would we classify all
  possible exploitable vulnerabilities in software?") without consideration for the practical questions that the data
  is intended to answer. Are some exploits theoretically possible, but never yet observed in the real world? Are some
  distinctions too fine-grained (or not fine-grained enough) for your analysis needs? Subject matter experts should
  have significant input into the type of data modeled, what analysis needs to be performed on the data, and how the
  data should be represented.
  
  The best models evolve in a cycle of forethought combined with real-world stress-testing. Creating a model with little
  or no forethought can lead to a narrowly-focused and fragmented data model – in the face of some immediate need,
  analysts or developers may focus on the trees while missing the big picture of the forest. That said, even the best
  model planned in advance will fall short when faced with the inconsistencies real-world data. Experience has shown us
  that there are always edge cases that cannot be anticipated. The most effective models are typically planned up front,
  then tested against real-world data and refined before being placed fully into production.

- **Test the basics and build from there.** No data model is set in stone – in fact, a good model will expand and evolve
  with analytical need. That said, changes to the model may require revising or updating existing model elements and 
  associated analysis, and some changes are easier to make than others. When introducing a new element to the model,
  consider carefully what the "essence" of that element is - what makes it unqiue and therefore how it should "look"
  within the model - and design a form to capture that. It is perfectly fine (and even preferable!) to start with a limited
  or "stub" form while you test it against real data. It is relatitvely easy to make **additive** changes to the data model
  (introduce new forms or new secondary properties). It is more challenging to **modify** the model once you have encoded
  data into nodes, because those modifications may require migrating existing data to account for your changes. 