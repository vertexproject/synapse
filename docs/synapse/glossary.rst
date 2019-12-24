.. _glossary:

Synapse Glossary
################

This Glossary provides a quick reference for common terms related to Synapse technical and analytical concepts.

A
=

.. _gloss-analytical-model:

Analytical Model
----------------

See :ref:`gloss-model-analytical`.

.. _gloss-axon:

Axon
----

TBD

B
=

.. _gloss-binary-uniq-id:

Binary Unique Identifier
------------------------

See :ref:`gloss-buid`.

.. _gloss-buid:

BUID
----

Short for Binary Unique Identifier. Within Synapse, a BUID is the globally unique (within a :ref:`gloss-cortex`) SHA256 digest of a node’s msgpack-encoded :ref:`gloss-ndef`.


C
=

.. _gloss-cell:

Cell
----

TBD

.. _gloss-comparator:

Comparator
----------

Short for :ref:`gloss-comp-operator`.

.. _gloss-comp-operator:

Comparison Operator
-------------------

A symbol or set of symbols used in the Storm language to evaluate :ref:`gloss-node` property values against one or more specified values. Comparison operators can be grouped into standard and extended operators.

.. _gloss-comp-op-standard:

Comparison Operator, Standard
-----------------------------

The set of common operator symbols used to evaluate (compare) values in Storm. Standard comparison operators include equal to (``=``), greater than (``>``), less than (``<``), greater than or equal to (``>=``), and less than or equal to (``<=``).

.. _gloss-comp-op-extended:

Extended Comparison Operator
----------------------------

The set of Storm-specific operator symbols or expressions used to evaluate (compare) values in Storm based on custom or Storm-specific criteria. Extended comparison operators include regular expression (``~=``), time / interval (``@=``), set membership (``*in=``), tag (``#``), and so on.

.. _gloss-constructor:

Constructor
-----------

Within Synapse, code that defines how a :ref:`gloss-prop` of a given :ref:`gloss-type` can be constructed to ensure that the property is well-formed for its type. Also known as a :ref:`gloss-ctor` for short. Constructors support :ref:`gloss-type-norm` and :ref:`gloss-type-enforce`.

.. _gloss-cortex:

Cortex
------

TBD

.. _gloss-ctor:

Ctor
----

Pronounced "see-tore". Short for :ref:`gloss-constructor`.

D
=

.. _gloss-daemon:

Daemon
------

TBD

.. _gloss-data-model:

Data Model
----------

See :ref:`gloss-model-data`.

.. _gloss-derived-prop:

Derived Property
-----------------

See :ref:`gloss-prop-derived`.

E
=

.. _gloss-edge:

Edge
----

TBD

.. _gloss-edge-directed:

Edge, Directed
--------------

TBD

F
=

.. _gloss-feed:

Feed
----

TBD

.. _gloss-filter:

Filter
------

TBD

.. _gloss-form:

Form
----

Within Synapse, a form is the definition of an object in the Synapse data model. A form acts as a "template" that specifies how to create an object (:ref:`gloss-node`) within a Cortex. A form consists of (at minimum) a :ref:`gloss-prop-primary` and its associated :ref:`gloss-type`. Depending on the form, it may also have various secondary properties with associated types.

See the :ref:`data-form` section in :ref:`data-model-terms` for additional detail.


.. _gloss-form-comp:

Form, Composite
---------------

TBD

.. _gloss-form-guid:

Form, GUID
----------

TBD

.. _gloss-form-simple:

Form, Simple
------------

TBD

.. _gloss-fused-know:

Fused Knowledge
---------------

See :ref:`gloss-know-fused`.

G
=

.. _gloss-global-uniq-id:

Globally Unique Identifier
--------------------------

See :ref:`gloss-guid`.

.. _gloss-graph:

Graph
-----

TBD

.. _gloss-graph-directed:

Graph, Directed
---------------

TBD

.. _gloss-guid:

GUID
----

Short for Globally Unique Identifier. Within Synapse, a GUID is a :ref:`gloss-type` specified as a 128-bit value that is unique within a given Cortex. GUIDs are used as primary properties for forms that cannot be uniquely represented by a specific value or set of values. Not to be confused with the Microsoft-specific definition of GUID, which is a 128-bit value with a specific format (see https://msdn.microsoft.com/en-us/library/aa373931.aspx).

H
=

.. _gloss-hive:

Hive
----

TBD

.. _gloss-hyperedge:

Hyperedge
---------

TBD

.. _gloss-hypergraph:

Hypergraph
----------

TBD

I
=

.. _gloss-iden:

Iden
----

Short for :ref:`gloss-identifier`. Within Synapse, the hexadecimal representation of a unique identifier (e.g., for a node, a task, a trigger, etc.) The term "identifier" / "iden" is used regardless of how the specific identifier is generated.

.. _gloss-identifier:

Identifier
----------

See :ref:`gloss-iden`.

.. _gloss-inst-know:

Instance Knowledge
------------------

See :ref:`gloss-know-inst`.

K
=

.. _gloss-know-fused:

Knowledge, Fused
----------------

TBD

.. _gloss-know-inst:

Knowledge, Instance
-------------------

TBD

L
=

.. _gloss-layer:

Layer
-----

TBD

.. _gloss-lift:

Lift
----

TBD

M
=

.. _gloss-model:

Model
-----

TBD

.. _gloss-model-analytical:

Model, Analytical
-----------------

TBD

.. _gloss-model-data:

Model, Data
-----------

TBD

N
=

.. _gloss-ndef:

Ndef
----

Pronounced "en-deff". Short for **node definition.** A node’s :ref:`gloss-form` and associated value (i.e., *<form> = <valu>* ) represented as comma-separated elements enclosed in parentheses: ``(<form>,<valu>)``.

.. _gloss-node:

Node
----

TBD

.. _gloss-node-def:

Node Definition
---------------

See :ref:`gloss-ndef`.

P
=

.. _gloss-package:

Package
-------

TBD

.. _gloss-pivot:

Pivot
-----

TBD

.. _gloss-prefix-index:

Prefix Indexing
---------------

TBD

.. _gloss-primary-prop:

Primary Property
----------------

See :ref:`gloss-prop-primary`.

.. _gloss-prop:

Property
--------

Within Synapse, a properties are individual elements that define a :ref:`gloss-form` or (along with their specific values) that comprise a :ref:`gloss-node`. Every property in Synapse must have a defined :ref:`gloss-type`.

See the :ref:`data-props` section in :ref:`data-model-terms` for additional detail.

.. _gloss-prop-derived:

Property, Derived
-----------------

TBD

.. _gloss-prop-primary:

Property, Primary
-----------------

Within Synapse, a primary property is the property that defines a given :ref:`gloss-form` in the data model. The primary property of a form must be selected / defined such that the value of that property is unique across all possible instances of that form.

.. _gloss-prop-relative:

Property, Relative
------------------

Within Synapse, a relative property is a :ref:`gloss-secondary-prop` referenced using only the portion the property's namespace that is relative to the form's :ref:`gloss-primary-prop`. For example, ``inet:dns:a:fqdn`` is the full name of the "domain" secondary property of a DNS A record form (``inet:dns:a``). ``:fqdn`` is the relative property / relative property name for that same property.

.. _gloss-prop-secondary:

Property, Secondary
-------------------

Within Synapse, secondary properties are optional properties that provide additional detail about a :ref:`gloss-form`. Within the data model, secondary properties may be defined with optional constraints, such as:

  - Whether the property is read-only once set.
  - Whether a default value should be set for the property if no value is specified.
  - Any normalization (outside of type-specific normalization) that should occur for the property (such as converting a string to all lowercase).

.. _gloss-prop-universal:

Property, Universal
-------------------

Within Synapse, a universal property is a :ref:`gloss-secondary-prop` that is applicable to all forms and may optionally be set for any form where the property is applicable. For example, ``.created`` is a universal property whose value is the date/time when the associated node was created in a Cortex.

R
=

.. _gloss-relative-prop:

Relative Property
-----------------

See :ref:`gloss-prop-relative`.

.. _gloss-repr:

Repr
----

Short for "representation". The repr of a :ref:`gloss-prop` defines how the property should be displayed, where the display format differs from the storage format. For example, date/time values in Synapse are stored in epoch milliseconds but are displayed in human-friendly "yyyy/mm/dd hh:mm:ss.mmm" format.

S
=

.. _gloss-secondary-prop:

Secondary Property
------------------

See :ref:`gloss-prop-secondary`.


.. _gloss-service:

Service
-------

TBD

.. _gloss-slab:

Slab
----

TBD

.. _gloss-splice:

Splice
------

TBD

.. _gloss-storm:

Storm
-----

The custom language used to interact with data in a Synapse :ref:`gloss-cortex`. See :ref:`storm-ref-intro` for additional detail.

T
=

.. _gloss-tag:

Tag
---

TBD

.. _gloss-tag-base:

Tag, Base
---------

TBD

.. _gloss-tag-leaf:

Tag, Leaf
---------

TBD

.. _gloss-tag-root:

Tag, Root
---------

TBD

.. _gloss-traverse:

Traverse
--------

TBD

.. _gloss-type:

Type
----

Within Synapse, a type is the definition of a data element within the data model. A type describes what the element is and enforces how it should look, including how it should be normalized, if necessary, for both storage (including indexing) and representation (display). See the :ref:`data-type` section in :ref:`data-model-terms` for additional detail.

.. _gloss-type-base:

Type, Base
----------

Within Synapse, base types include standard types such as integers and strings, as well as common types defined within or specific to Synapse, including globally unique identifiers (``guid``), date/time values (``time``), time intervals (``ival``), and tags (``syn:tag``). Many forms within the Synapse data model are built upon (extensions of) a subset of common types.

.. _gloss-type-model:

Type, Model-Specific
--------------------

Within Synapse, knowledge domain-specific forms may themselves be specialized types. For example, an IPv4 address (``inet:ipv4``) is its own specialized type. While an IPv4 address is ultimately stored as an integer, the type has additional constraints (i.e., to ensure that IPv4 objects in the Cortex can only be created using integer values that fall within the allowable IPv4 address space).

.. _gloss-type-aware:

Type Awareness
--------------

Type awareness is the feature of the :ref:`gloss-storm` query language that facilitates and simplifies navigation through the :ref:`gloss-hypergraph` when pivoting across nodes. Storm leverages knowledge of the Synapse :ref:`gloss-data-model` (specifically knowledge of the type of each node property) to allow pivoting between primary and secondary properties of the same type across different nodes without the need to explicitly specify the properties involved in the pivot.

.. _gloss-type-enforce:

Type Enforcement
----------------

Within Synapse, the process by which property values are required to conform to value and format constraints defined for that :ref:`gloss-type` within the data model before they can be set. Type enforcement helps to limit bad data being entered in to a Cortex by ensuring values entered make sense for the specified data type (i.e., that an IP address cannot be set as the value of a property defined as a domain (``inet:fqdn``) type).

.. _gloss-type-norm:

Type Normalization
------------------

Within Synapse, the process by which properties of a particular type are standardized and formatted in order to ensure consistency in the data model. Normalization may include processes such as converting user-friendly input into a different format for storage (e.g., converting an IP address entered in dotted-decimal notation to an integer), converting certain string-based values to all lowercase, and so on.

U
=

.. _gloss-universal-prop:

Universal Property
------------------

See :ref:`gloss-prop-universal`.

V
=

.. _gloss-variable:

Variable
--------

TBD

.. _gloss-vertex:

Vertex
------

TBD

.. _gloss-view:

View
----

TBD