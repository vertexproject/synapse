.. highlight:: none

.. _data-model-form-categories:

Data Model - Form Categories
============================

Synapse forms can be broadly grouped into conceptual categories based on the **object** a form is meant to
represent - an :ref:`form-entity`, a :ref:`form-relationship`, or an :ref:`form-event`.

Synapse forms can also be broadly grouped based on how their **primary properties** (``<form> = <valu>``)
are formed.

Recall that ``<form> = <valu>`` must be unique for all forms of a given type. In other words, the ``<valu>``
must be defined so that it uniquely identifies any given node of that form; it represents that form’s "essence"
or "thinghood" in a way that allows the unambiguous deconfliction of all possible nodes of that form.

Conceptually speaking, the general categories of forms in Synapse are:

- `Simple Form`_
- `Composite (Comp) Form`_
- `Guid Form`_
- `Generic Form`_
- `Digraph (Edge) Form`_

This list represents a conceptual framework for understanding the Synapse data model.

.. _form-simple:

Simple Form
-----------

A simple form refers to a form whose primary property is a single typed ``<valu>``. They are commonly used
to represent an :ref:`form-entity`, and so tend to be the most readily understood from a modeling perspective.

**Examples**

- **IP addresses.** An IP address (IPv4 or IPv6) must be unique within its address space and can be defined by
  the address itself: ``inet:ipv4 = 1.2.3.4``. Secondary properties include the associated Autonomous System
  number and whether the IP belongs to a specialized or reserved group (e.g., private, multicast, etc.).

- **Email addresses.** An email address must be unique in order to route email to the correct account / individual
  and can be defined by the address itself: ``inet:email = joe.smith@company.com``. Secondary properties include
  the domain where the account receives mail and the username for the account.

.. _form-comp:

Composite (Comp) Form
---------------------

A composite (comp) form is one where the primary property is a comma-separated list of two or more typed ``<valu>``
elements. While no single element makes the form unique, a combination of elements can uniquely define a given
node of that form. Comp forms are often (though not universally) used to represent a :ref:`form-relationship`.

**Examples**

- **Fused DNS A records.** A DNS A record can be uniquely defined by the combination of the domain (``inet:fqdn``)
  and the IP address (``inet:ipv4``) in the A record. Synapse’s ``inet:dns:a`` form represents the knowledge that
  a given domain resolved to a specific IP at some time, or within a time window (fused knowledge):
  ``inet:dns:a = (woot.com, 1.2.3.4)``. The time window is captured by the universal ``.seen`` property.

- **Web-based accounts.** An account at an online service (such as Github or Twitter) can be uniquely defined by
  the combination of the domain where the service is hosted (``inet:fqdn``) and the unique user ID (``inet:user``)
  used to identify the account: ``inet:web:acct = (twitter.com, vtxproject)``.

- **Social networks.** Many online services allow users to establish relationships with other users of that
  service. These relationships may be one-way (you can follow someone on Twitter) or two-way (you can mutually
  connect with someone on LinkedIn). A given one-way social network relationship ("Alice follows Bob") can be
  uniquely defined by the two users (``inet:web:acct``) involved in the relationship:
  ``inet:web:follows = ( (twitter.com,alice), (twitter.com,bob) )``. (A two-way relationship can be defined by
  two one-way relationships.)
  
  Note that each of the elements in the ``inet:web:follows`` comp form is itself a comp form (``inet:web:acct``).

.. _form-guid:

Guid Form
---------

A guid (Globally Unique Identifier) form is uniquely defined by a machine-generated 128-bit number. Guids account
for cases where it is impossible to uniquely define a thing based on a property or set of properties. Guids are
also useful for cases where the amount of data available to create a particular object (node) may vary greatly
(i.e., not all properties / details are available from all data sources).

A guid form can be considered a special case of a :ref:`form-simple` where the typed ``<valu>`` is of type ``<guid>``.

.. NOTE::
  Guid forms can be arbitrary (generated ad-hoc by Synapse) or predictable / deconflictable (generated based on
  a specific set of inputs). See the :ref:`type-guid` section of :ref:`storm-ref-type-specific` for a more
  detailed discussion of this concept.

**Examples**

- **People.** Synapse uses a guid as the primary property for a person (``ps:person``) node. There is no single
  property or set of properties that uniquely and unambiguously define a person. A person’s full name, date of
  birth, or place of birth (or the combination of all three) are not guaranteed to be fully unique across an
  entire population. Identification numbers (such as Social Security or National ID numbers) are country-specific,
  and not all countries require each citizen to have an ID number.

- **Host execution / sandbox data.** The ability to model detailed behavior of a process executing on a host
  (or in a sandbox) is important for disciplines such as incident response and malware analysis. Modeling this
  data is challenging because of the number of effects that execution may have on a system (files read, written,
  or deleted; network activity initiated). Even if we focus on a specific effect ("a process wrote a new file
  to disk"), there are still a number of details that may define a "unique instance" of "process writes file":
  the specific host where the process ran, the program that wrote the file to disk, the process that launched
  the program, the time the execution occurred, the file that was written, the file’s path, and so on. While all
  of these elements could be used to create a comp form, in the "real world" not all of this data may be
  available in all cases, making a guid a better option for forms such as ``it:exec:file:write``.

.. _form-generic:

Generic Form
------------

The Synapse data model includes a number of "generic" forms that can be used to represent metadata and / or arbitrary data. 

In an ideal world, all data represented in Synapse would be accurately modeled using an appropriate form. However,
designing a new form for the data model may require extended discussion, subject matter expertise, and testing
against "real world" data - not to mention time to implement model changes. In addition, sometimes data needs
to be added to a Cortex for reference or analysis purposes where the data simply does not have sufficient detail
to be represented accurately, even if an appropriate form existed.

The use of generic forms is not ideal - the representation of "generic" data may be lossy, which may impact effective
analysis. But generic forms may be necessary for adding arbitrary to Synapse, either because an appropriate model
element does not yet exist but the data is needed now; or because there is no other effective way to represent the data.

These generic forms exist in two primary parts of the data model: ``meta:*`` forms and ``graph:*`` forms. Examples
include:

- ``meta:seen`` nodes, used to represent a data source used to ingest data into Synapse. Data sources may include sensors
  or third-party connectors such as Synapse Power-Ups. A ``meta:source`` is linked to the data it provides via a
  ``-(seen)>`` light edge.

- ``meta:rule`` nodes, used to represent a generic detection rule for cases where a more specific form (such as ``it:av:sig``
  or ``it:app:yara:rule``) is not available.

Some generic forms are "edge forms" (see :ref:`form-edge`, below) used to represent relationships between arbitrary
forms.

.. _form-edge:

Digraph (Edge) Form
-------------------

.. NOTE::
  
  The use of light edges (see :ref:`data-light-edge`) is preferred over edge forms (which predate light edges)
  where possible.

A digraph form ("edge" form) is a specialized :ref:`form-comp` whose primary property value consists of two
``<form>,<valu>`` pairs  ("node definitions", or ndefs). An edge form is a specialized relationship form that
can be used to link two arbitrary forms in a generic relationship.

Edge forms have not been officially deprecated. However, edge forms (used to create nodes) incur some additional performance
overhead vs. light edges (particularly for large numbers of edge nodes). In addition, there are some nuances to working with
edge nodes using Storm (see :ref:`pivot-to-edge`, for example) that can make navigating Synapse data more complex. For these
reasons, light edges are now preferred.
