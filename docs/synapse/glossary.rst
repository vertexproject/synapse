
.. highlight:: none

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

The Axon is an interface for providing binary / blob storage inside of the Synapse ecosystem. This indexes binaries
based on SHA-256 hash so we do not duplicate the storage of the same set of bytes twice. The default implemenation
stores the blobs in a LMDB :ref:`gloss-slab`.

B
=

.. _gloss-base-tag:

Base Tag
--------

See :ref:`gloss-tag-base`.

.. _gloss-binary-uniq-id:

Binary Unique Identifier
------------------------

See :ref:`gloss-buid`.

.. _gloss-buid:

BUID
----

Short for Binary Unique Identifier. Within Synapse, a BUID is the globally unique (within a :ref:`gloss-cortex`) SHA-256
digest of a node’s msgpack-encoded :ref:`gloss-ndef`.


C
=

.. _gloss-cell:

Cell
----

The Cell is a basic building block of Synapse services, including the Cortex. See :ref:`dev_architecture` for more
information about what a Cell provides.

.. _gloss-comparator:

Comparator
----------

Short for :ref:`gloss-comp-operator`.

.. _gloss-comp-operator:

Comparison Operator
-------------------

A symbol or set of symbols used in the Storm language to evaluate :ref:`gloss-node` property values against one or more
specified values. Comparison operators can be grouped into standard and extended operators.

.. _gloss-comp-op-standard:

Comparison Operator, Standard
-----------------------------

The set of common operator symbols used to evaluate (compare) values in Storm. Standard comparison operators include
equal to (``=``), greater than (``>``), less than (``<``), greater than or equal to (``>=``), and less than or equal
to (``<=``).

.. _gloss-comp-op-extended:

Comparison Operator, Extended
-----------------------------

The set of Storm-specific operator symbols or expressions used to evaluate (compare) values in Storm based on custom or
Storm-specific criteria. Extended comparison operators include regular expression (``~=``), time/interval (``@=``), set
membership (``*in=``), tag (``#``), and so on.

.. _gloss-comp-form:

Composite Form
--------------

See :ref:`gloss-form-comp`.

.. _gloss-constant:

Constant
--------

In Storm, a constant is a value that cannot be altered during normal execution, i.e., the value is constant.

Contrast with :ref:`gloss-variable`. See also :ref:`gloss-runtsafe` and :ref:`gloss-non-runtsafe`.


.. _gloss-constructor:

Constructor
-----------

Within Synapse, a constructor is code that defines how a :ref:`gloss-prop` value of a given :ref:`gloss-type` can be
constructed to ensure that the value is well-formed for its type. Also known as a :ref:`gloss-ctor` for short.
Constructors support :ref:`gloss-type-norm` and :ref:`gloss-type-enforce`.

.. _gloss-cortex:

Cortex
------

A Cortex is Synapse's implementation of an individual :ref:`gloss-hypergraph`. Cortex features include scalability,
key/value-based node properties, and a :ref:`gloss-data-model` which facilitates normalization.

.. _gloss-cron:

Cron
----

Within Synapse cron jobs are used to create scheduled tasks, similar to the Linux/Unix "cron" utility. The task to be
executed by the cron job is specified using the :ref:`gloss-storm` query language.

See the Storm command reference for the :ref:`storm-cron` command and the :ref:`storm-ref-automation` document for
additional detail.

.. _gloss-ctor:

Ctor
----

Pronounced "see-tore". Short for :ref:`gloss-constructor`.

D
=

.. _gloss-daemon:

Daemon
------

Similar to a traditional Linux or Unix daemon, a Synapse daemon is a long-running or recurring query or process that
runs continuously in the background. A daemon is typically implemented by a Storm :ref:`gloss-service` and may be used
for tasks such as processing elements from a :ref:`gloss-queue`. A daemon allows for non-blocking background processing
of non-critical tasks. Daemons are persistent and will restart if they exit.

.. _gloss-data-model:

Data Model
----------

See :ref:`gloss-model-data`.

.. _gloss-deconflictable:

Deconflictable
--------------

Within Synapse, a term typically used with respect to :ref:`gloss-node` creation. A node is deconflictable if, upon node
creation, Synapse can determine whether the node already exists within a Cortex (i.e., the node creation attempt is
deconflicted against existing nodes). For example, on attempting to create the node ``inet:fqdn=woot.com`` Synapse can
deconflict the node by checking whether a node of the same form with the same primary property already exists.

Whether a node is deconflictable is often an issue with GUID forms. A :ref:`gloss-guid-form` whose primary property is
an arbitrary GUID is not deconflictable. A GUID form whose primary property is generated from a defined or predictable
set of strings (such as a subset of the form's secondary property values) may be deconflictable. See the
:ref:`type-guid` section of the :ref:`storm-ref-type-specific` document for additional detail.

.. _gloss-derived-prop:

Derived Property
-----------------

See :ref:`gloss-prop-derived`.

.. _gloss-directed-edge:

Directed Edge
-------------

See :ref:`gloss-edge-directed`.

.. _gloss-directed-graph:

Directed Graph
--------------

See :ref:`gloss-graph-directed`.

Dmon
----

Abbreviation for :ref:`gloss-daemon`.

E
=

.. _gloss-edge:

Edge
----

In a traditional :ref:`gloss-graph`, an edge is used to connect exactly two nodes (vertexes). Compare with
:ref:`gloss-hyperedge`.

.. _gloss-edge-directed:

Edge, Directed
--------------

In a :ref:`gloss-directed-graph`, a directed edge is used to connect exactly two nodes (vertexes) in a one-way
(directional) relationship. Compare with :ref:`gloss-hyperedge`.

.. _gloss-edge-light:

Edge, Lightweight (Light)
-------------------------

In Synapse, a lightweight (light) edge is a mechanism that links two arbitrary forms via a user-defined
verb that describes the linking relationship. Light edges are not forms and so do not support secondary 
properties or tags. They are meant to simplify performance, representation of data, and Synapse hypergraph
navigation for many use cases. Contrast with :ref:`gloss-form-edge`.

.. _gloss-extended-comp-op:

Extended Comparison Operator
----------------------------

See :ref:`gloss-comp-op-extended`.

F
=

.. _gloss-feed:

Feed
----

A feed is an ingest API consisting of a set of ingest formats (e.g., file formats, record formats) used to parse
records directly into nodes. Feeds are typically used for bulk node creation, such as ingesting data from an external
source or system.

.. _gloss-filter:

Filter
------

Within Synapse, one of the three primary methods for interacting with data in a :ref:`gloss-cortex`. A filter operation
downselects a subset of nodes following a lift operation. Compare with :ref:`gloss-lift` and :ref:`gloss-pivot`.

See :ref:`storm-ref-filter` for additional detail.

.. _gloss-filter-subquery:

Filter, Subquery
----------------

Within Synapse, a subquery filter is a filter that consists of a :ref:`gloss-storm` expression.


See :ref:`filter-subquery` for additional detail.

.. _gloss-form:

Form
----

Within Synapse, a form is the definition of an object in the Synapse data model. A form acts as a "template" that
specifies how to create an object (:ref:`gloss-node`) within a Cortex. A form consists of (at minimum) a
:ref:`gloss-primary-prop` and its associated :ref:`gloss-type`. Depending on the form, it may also have various
secondary properties with associated types.

See the :ref:`data-form` section in the :ref:`data-model-terms` document for additional detail.


.. _gloss-form-comp:

Form, Composite
---------------

In the Synpase :ref:`gloss-data-model`, a category of form whose primary property is an ordered set of two or more
comma-separated typed values. Examples include DNS A records (``inet:dns:a``) and web-based
accounts (``inet:web:acct``).

.. _gloss-form-digraph:

See :ref:`gloss-form-edge`.

.. _gloss-form-edge:

Form, Edge
----------

In the Synapse :ref:`gloss-data-model`, a specialized **composite form** (:ref:`gloss-form-comp`) whose primary
property consists of two :ref:`gloss-ndef` values. Edge forms can be used to link two arbitrary forms via a 
generic relationship where additional information needs to be captured about that relationship (i.e., via secondary
properpties and/or tags). Contrast with :ref:`gloss-edge-light`.


.. _gloss-form-guid:

Form, GUID
----------

In the Synpase :ref:`gloss-data-model`, a specialized case of a :ref:`gloss-simple-form` whose primary property is a
:ref:`gloss-guid`. The GUID can be either arbitrary (in which case it is **not** considered
:ref:`gloss-deconflictable`) or constructed from a specified set of values (with the goal of being
:ref:`gloss-deconflictable`). Examples include file execution data (e.g., ``inet:file:exec:read``) or
articles (``media:news``).

.. _gloss-form-simple:

Form, Simple
------------

In the Synapse :ref:`gloss-data-model`, a category of form whose primary property is a single typed value. Examples
include domains (``inet:fqdn``) or hashes (e.g., ``hash:md5``).

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

A graph is a mathematical structure used to model pairwise relations between objects. Graphs consist of vertices
(or nodes) that represent objects and edges that connect exactly two vertices in some type of relationship.
Nodes and edges in a graph are typically represented by dots or circles conneted by lines.

See :ref:`bkd-graphs-hypergraphs` for additional detail on graphs and hypergraphs.

.. _gloss-graph-directed:

Graph, Directed
---------------

A directed graph is a :ref:`gloss-graph` where the edges representing relationships between nodes have a "direction".
Given node X and node Y connected by edge E, the relationship is valid for X -> E -> Y but not Y -> E -> X. For
example, the relationship "Fred owns bank account #01234567" is valid, but "bank account #01234567 owns Fred" is not.
Nodes and edges in a directed graph are typically represented by dots or circles connected by arrows.

See :ref:`bkd-graphs-hypergraphs` for additional detail on graphs and hypergraphs.

.. _gloss-guid:

GUID
----

Short for Globally Unique Identifier. Within Synapse, a GUID is a :ref:`gloss-type` specified as a 128-bit value that
is unique within a given :ref:`gloss-cortex`. GUIDs are used as primary properties for forms that cannot be uniquely
represented by a specific value or set of values. Not to be confused with the Microsoft-specific definition of GUID,
which is a 128-bit value with a specific format (see https://msdn.microsoft.com/en-us/library/aa373931.aspx).

.. _gloss-guid-form:

GUID Form
---------

See :ref:`gloss-form-guid`.

H
=

.. _gloss-hive:

Hive
----

The Hive is a key/value storage mechanism which is used to persist various data structures required for operating a
Synapse :ref:`gloss-cell`.

.. _gloss-hyperedge:

Hyperedge
---------

A hyperedge is an edge within a :ref:`gloss-hypergraph` that can join any number of nodes (vs. a :ref:`gloss-graph` or
:ref:`gloss-directed-graph` where an edge joins exactly two nodes). A hyperedge joining an arbitrary number of nodes
can be difficult to visualize in flat, two-dimensional space; for this reason hyperedges are often represented as a
line or "boundary" encircling a set of nodes, thus "joining" those nodes into a related group.

See :ref:`bkd-graphs-hypergraphs` for additional detail on graphs and hypergraphs.

.. _gloss-hypergraph:

Hypergraph
----------

A hypergraph is a generalization of a :ref:`gloss-graph` in which an edge can join any number of nodes. If a
:ref:`gloss-directed-graph` where edges join exactly two nodes is two-dimensional, then a hypergraph where a
:ref:`gloss-hyperedge` can join any number (n-number) of nodes is n-dimensional.

See :ref:`bkd-graphs-hypergraphs` for additional detail on graphs and hypergraphs.

I
=

.. _gloss-iden:

Iden
----

Short for :ref:`gloss-identifier`. Within Synapse, the hexadecimal representation of a unique identifier (e.g., for a
node, a task, a trigger, etc.) The term "identifier" / "iden" is used regardless of how the specific identifier is
generated.

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

If a form within the Synapse data model has a "range" of time elements (i.e., an interval such as "first seen"/"last
seen"), the form typically represents **fused knowledge** -- a period of time during which an object, relationship, or
event was known to exist. Forms representing fused knowledge can be thought of as combining *n* number of instance
knowledge observations. ``inet:dns:query``, ``inet:dns:a``, and ``inet:whois:email`` forms are examples of fused
knowledge.

See :ref:`instance-fused` for a more detailed discussion.

.. _gloss-know-inst:

Knowledge, Instance
-------------------

If a form within the Synapse data model has a specific time element (i.e., a single date/time value), the form
typically represents **instance knowledge** -- a single instance or occurrence of an object, relationship, or event.
``inet:dns:request`` and ``inet:whois:rec`` forms are examples of instance knowledge.

See :ref:`instance-fused` for a more detailed discussion.

L
=

.. _gloss-layer:

Layer
-----

Within Synapse, a layer is the substrate that contains node data and where permissions enforcement occurs. Viewed
another way, a layer is a storage and write permission boundary. By default, a :ref:`gloss-cortex` has a single layer
and a single :ref:`gloss-view`, meaning that by default all nodes are stored in one layer and all changes are written
to that layer. However, multiple layers can be created for various purposes such as: separating data from different
data sources (e.g., a read-only layer consisting of third-party data and associated tags can be created underneath
a "working" layer, so that the third-party data is visible but cannot be modified); providing users with a personal
"scratch space" where they can make changes in their layer without affecting the underlying main Cortex layer; or
segregating data sets that should be visible/accessible to some users but not others.

Layers are closely related to views (see :ref:`gloss-view`). The order in which layers are instantiated within a view
matters; in a multi-layer view, typically only the topmost layer is writeable by that view's users, with subsequent
(lower) layers read-only. Explicit actions can push upper-layer writes downward (merge) into lower layers.

.. _gloss-leaf-tag:

Leaf Tag
--------

See :ref:`gloss-tag-leaf`.

.. _gloss-lift:

Lift
----

Within Synapse, one of the three primary methods for interacting with data in a :ref:`gloss-cortex`. A lift is a read
operation that selects a set of nodes from the Cortex. Compare with :ref:`gloss-filter` and :ref:`gloss-pivot`.

See :ref:`storm-ref-lift` for additional detail.

.. _gloss-light-edge:

Lightweight (Light) Edge
------------------------

See :ref:`gloss-edge-light`.

M
=

.. _gloss-macro:

Macro
-----

A macro is a stored Storm query. Macros support the full range of Storm syntax and features.

See the Storm command reference for the :ref:`storm-macro` command and the :ref:`storm-ref-automation` for
additional detail.


.. _gloss-model:

Model
-----

Within Synapse, a system or systems used to represent data and/or assertions in a structured manner. A well-designed
model allows efficient and meaningful exploration of the data to identify both known and potentially arbitrary or
discoverable relationships.

.. _gloss-model-analytical:

Model, Analytical
-----------------

Within Synapse, the set of tags (:ref:`gloss-tag`) representing analytical assessments or assertions that can be
applied to objects in a :ref:`gloss-cortex`.

.. _gloss-model-data:

Model, Data
-----------

Within Synapse, the set of forms (:ref:`gloss-form`) that define the objects that can be represented in a
:ref:`gloss-cortex`.

N
=

.. _gloss-ndef:

Ndef
----

Pronounced "en-deff". Short for **node definition.** A node’s :ref:`gloss-form` and associated value
(i.e., *<form> = <valu>* ) represented as comma-separated elements enclosed in parentheses: ``(<form>,<valu>)``.

.. _gloss-node:

Node
----

A node is a unique object within a :ref:`gloss-cortex`. Where a :ref:`gloss-form` is a template that defines the
charateristics of a given object, a node is a specific instance of that type of object. For example, ``inet:fqdn``
is a form; ``inet:fqdn=woot.com`` is a node.

See :ref:`data-node` in the :ref:`data-model-terms` document for additional detail.

.. _gloss-node-def:

Node Definition
---------------

See :ref:`gloss-ndef`.

.. _gloss-node-runt:

Node, Runt
----------

Short for "runtime node". A runt node is a node that does not persist within a Cortex but is created at runtime when
a Cortex is initiated. Runt nodes are commonly used to represent metadata associated with Synapse, such as data model
elements like forms (``syn:form``) and properties (``syn:prop``) or automation elements like triggers (``syn:trigger``)
or cron jobs (``syn:cron``).

.. _gloss-non-runtime-safe:

Non-Runtime Safe
----------------

See :ref:`gloss-non-runtsafe`.

.. _gloss-non-runtsafe:

Non-Runtsafe
------------

Short for "non-runtime safe". Non-runtsafe refers to the use of variables within Storm. A variable that is
**non-runtsafe** has a value that may change based on the specific node passing through the Storm pipeline. A variable
whose value is set to a node property, such as ``$fqdn = :fqdn`` is an example of a non-runtsafe variable (i.e., the
value of the secondary property ``:fqdn`` may be different for different nodes, so the value of the variable will be
different based on the specific node being operated on).

Contrast with :ref:`gloss-runtsafe`.

P
=

.. _gloss-package:

Package
-------

A package is a set of commands and library code used to implement a Storm :ref:`gloss-service`. When a new Storm
service is loaded into a Cortex, the Cortex verifes that the service is legitimate and then requests the service's
packages in order to load any extended Storm commands associated with the service and any library code used to
implement the service.

.. _gloss-pivot:

Pivot
-----

Within Synapse, one of the three primary methods for interacting with data in a :ref:`gloss-cortex`. A pivot operation
allows navigation of the hypergraph following a lift operation. A pivot moves from a set of nodes with one or more
properties with specified value(s) to a set of nodes with a property having the same value(s).  Compare with
:ref:`gloss-lift` and :ref:`gloss-filter`.

See :ref:`storm-ref-pivot` for additional detail.

.. _gloss-primary-prop:

Primary Property
----------------

See :ref:`gloss-prop-primary`.

.. _gloss-prop:

Property
--------

Within Synapse, properties are individual elements that define a :ref:`gloss-form` or (along with their specific
values) that comprise a :ref:`gloss-node`. Every property in Synapse must have a defined :ref:`gloss-type`.

See the :ref:`data-props` section in the :ref:`data-model-terms` document for additional detail.

.. _gloss-prop-derived:

Property, Derived
-----------------

Within Synapse, a derived property is a secondary property that can be extracted (derived) from a node's primary
property. For example, the domain ``inet:fqdn=www.google.com`` can be used to derive ``inet:fqdn:domain=google.com``
and ``inet:fqdn:host=www``; the DNS A record ``inet:dns:a=(woot.com, 1.2.3.4)`` can be used to derive 
``inet:dns:a:fqdn=woot.com`` and ``inet:dns:a:ipv4=1.2.3.4``. Synapse will automatically set any secondary properties
that can be derived from a node's primary property; if the seconday property can be used to define a node in its own
right (i.e., ``inet:fqdn=google.com`` from ``inet:fqdn=www.google.com``) the additional nodes will be automatically
created if they do not already exist. Because derived properties are based on primary property values, derived
secondary properties are always read-only (i.e., cannot be modified once set).

.. _gloss-prop-primary:

Property, Primary
-----------------

Within Synapse, a primary property is the property that defines a given :ref:`gloss-form` in the data model. The
primary property of a form must be defined such that the value of that property is unique across all possible
instances of that form. Primary properties are always read-only (i.e., cannot be modified once set).

.. _gloss-prop-relative:

Property, Relative
------------------

Within Synapse, a relative property is a :ref:`gloss-secondary-prop` referenced using only the portion of the
property's namespace that is relative to the form's :ref:`gloss-primary-prop`. For example, ``inet:dns:a:fqdn`` is
the full name of the "domain" secondary property of a DNS A record form (``inet:dns:a``). ``:fqdn`` is the relative
property / relative property name for that same property.

.. _gloss-prop-secondary:

Property, Secondary
-------------------

Within Synapse, secondary properties are optional properties that provide additional detail about a :ref:`gloss-form`.
Within the data model, secondary properties may be defined with optional constraints, such as:

  - Whether the property is read-only once set.
  - Any normalization (outside of type-specific normalization) that should occur for the property (such as converting
    a string to all lowercase).

.. _gloss-prop-universal:

Property, Universal
-------------------

Within Synapse, a universal property is a :ref:`gloss-secondary-prop` that is applicable to all forms and may
optionally be set for any form where the property is applicable. For example, ``.created`` is a universal property
whose value is the date/time when the associated node was created in a Cortex.

Q
=

.. _gloss-queue:

Queue
-----

Within Synapse, a queue is a basic first-in, first-out (FIFO) data structure used to store and serve objects in a
classic pub/sub (publish/subscribe) manner. Any primitive (such as a node iden) can be placed into a queue and then
consumed from it. Queues can be used (for example) to support out-of-band processing by allowing non-critical tasks
to be executed in the background. Queues are persistent; i.e., if a Cortex is restarted, the queue and any objects
in the queue are retained.

R
=

.. _gloss-relative-prop:

Relative Property
-----------------

See :ref:`gloss-prop-relative`.

.. _gloss-repr:

Repr
----

Short for "representation". The repr of a :ref:`gloss-prop` defines how the property should be displayed in cases where
the display format differs from the storage format. For example, date/time values in Synapse are stored in epoch
milliseconds but are displayed in human-friendly "yyyy/mm/dd hh:mm:ss.mmm" format.

.. _gloss-root-tag:

Root Tag
--------

See :ref:`gloss-tag-root`.

.. _gloss-runt-node:

Runt Node
---------

See :ref:`gloss-node-runt`.

.. _gloss-runtime-safe:

Runtime Safe
------------

See :ref:`gloss-runtsafe`.

.. _gloss-runtsafe:

Runtsafe
--------

Short for "runtime safe". Runtsafe refers to the use of variables within Storm. A variable that is **runtsafe** has a
value that will not change based on the specific node passing through the Storm pipeline. A variable whose value is
explcitly set, such as ``$fqdn = woot.com`` is an example of a runtsafe varaible.

Contrast with :ref:`gloss-non-runtsafe`.

S
=

.. _gloss-secondary-prop:

Secondary Property
------------------

See :ref:`gloss-prop-secondary`.


.. _gloss-service:

Service
-------

A Storm service is a registerable remote component that can provide packages (:ref:`gloss-package`) and additional APIs
to Storm and Storm commands. A service resides on a :ref:`gloss-telepath` API endpoint outside of the Cortex. When a
service is loaded into a Cortex, the Cortex queries the endpoint to determine if the service is legitimate and, if so,
loads the associated :ref:`gloss-package` to implement the service. An advantage of Storm services (over, say,
additional Python modules) is that services can be restarted to reload their service definitions and packages while
a Cortex is still running -- thus allowing a service to be updated without having to restart the entire Cortex.

.. _gloss-simple-form:

Simple Form
-----------

See :ref:`gloss-form-simple`.

.. _gloss-slab:

Slab
----

A Slab is a core Synapse component which is used for persisting data on disk into a LMDB backed database. The Slab
interface offers an asyncio friendly interface to LMDB objects, while allowing users to largely avoid having to
handle native transactions themselves.

.. _gloss-splice:

Splice
------

A splice is an atomic change made to data within a Cortex, such as node creation or deletion, adding or removing a tag,
or setting, modifying, or removing a property. All changes within a Cortex may be retrieved as individual splices within
the Cortex's splice log.

.. _gloss-standard-comp-op:

Standard Comparison Operator
----------------------------

See :ref:`gloss-comp-op-standard`.

.. _gloss-storm:

Storm
-----

Storm is the custom, domain-specific language used to interact with data in a Synapse :ref:`gloss-cortex`.

See :ref:`storm-ref-intro` for additional detail.

.. _gloss-subquery:

Subquery
--------

Within Synapse, a subquery is a :ref:`gloss-storm` query that is executed inside of another Storm query.


See :ref:`storm-ref-subquery` for additional detail.

.. _gloss-subquery-filter:

Subquery Filter
---------------

See :ref:`gloss-filter-subquery`.


T
=

.. _gloss-tag:

Tag
---

Within Synapse, a tag is a label applied to a node that provides additional context about the node. Tags typically
represent assessments or judgements about the data represented by the node.

See the :ref:`data-tag` section in the :ref:`data-model-terms` document for additional detail.

.. _gloss-tag-base:

Tag, Base
---------

Within Synapse, the lowest (rightmost) tag element in a tag hierarchy. For example, for the tag ``#foo.bar.baz``,
``baz`` is the base tag.

.. _gloss-tag-leaf:

Tag, Leaf
---------

The full tag path / longest tag in a given tag hierarchy. For example, for the tag ``#foo.bar.baz``, ``foo.bar.baz``
is the leaf tag.

.. _gloss-tag-root:

Tag, Root
---------

Within Synapse, the highest (leftmost) tag element in a tag hierarchy. For example, for the tag ``#foo.bar.baz``,
``foo`` is the root tag.

.. _gloss-telepath:

Telepath
--------

Telepath is a lightweight remote procedure call (RPC) protocol used in Synapse. See :ref:`arch-telepath` in the
:ref:`dev_architecture` guide for additional detail.

.. _gloss-traverse:

Traverse
--------

In a :ref:`gloss-graph` or :ref:`gloss-directed-graph`, traversal refers to navigating the data in the graph by
pathing along the edges between nodes. In a :ref:`gloss-hypergraph`, because there are no edges, navigation between
nodes is commonly performed using a :ref:`gloss-pivot`.

.. _gloss-trigger:

Trigger
-------

Within Synapse, a trigger is a Storm query that is executed automatically upon the occurrence of a specified event
within a Cortex (such as adding a node or applying a tag). "Trigger" refers collectively to the event and the query
fired ("triggered") by the event.

See the Storm command reference for the :ref:`storm-trigger` command and the :ref:`storm-ref-automation` for
additional detail.

.. _gloss-type:

Type
----

Within Synapse, a type is the definition of a data element within the data model. A type describes what the element
is and enforces how it should look, including how it should be normalized.

See the :ref:`data-type` section in the :ref:`data-model-terms` document for additional detail.

.. _gloss-type-base:

Type, Base
----------

Within Synapse, base types include standard types such as integers and strings, as well as common types defined within
or specific to Synapse, including globally unique identifiers (``guid``), date/time values (``time``), time intervals
(``ival``), and tags (``syn:tag``). Many forms within the Synapse data model are built upon (extensions of) a subset
of common types.

.. _gloss-type-model:

Type, Model-Specific
--------------------

Within Synapse, knowledge-domain-specific forms may themselves be specialized types. For example, an IPv4 address
(``inet:ipv4``) is its own specialized type. While an IPv4 address is ultimately stored as an integer, the type has
additional constraints, e.g., IPv4 values must fall within the allowable IPv4 address space.

.. _gloss-type-aware:

Type Awareness
--------------

Type awareness is the feature of the :ref:`gloss-storm` query language that facilitates and simplifies navigation
through the :ref:`gloss-hypergraph` when pivoting across nodes. Storm leverages knowledge of the Synapse
:ref:`gloss-data-model` (specifically knowledge of the type of each node property) to allow pivoting between primary
and secondary properties of the same type across different nodes without the need to explicitly specify the properties
involved in the pivot.

.. _gloss-type-enforce:

Type Enforcement
----------------

Within Synapse, the process by which property values are required to conform to value and format constraints defined
for that :ref:`gloss-type` within the data model before they can be set. Type enforcement helps to limit bad data being
entered in to a Cortex by ensuring values entered make sense for the specified data type (e.g., that an IP address
cannot be set as the value of a property defined as a domain (``inet:fqdn``) type, and that the integer value of the
IP falls within the allowable set of values for IP address space).

.. _gloss-type-norm:

Type Normalization
------------------

Within Synapse, the process by which properties of a particular type are standardized and formatted in order to ensure
consistency in the data model. Normalization may include processes such as converting user-friendly input into a
different format for storage (e.g., converting an IP address entered in dotted-decimal notation to an integer),
converting certain string-based values to all lowercase, and so on.

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

In Storm, a variable is an identifier with a value that can be defined and/or changed during normal execution, i.e.,
the value is variable.

Contrast with :ref:`gloss-constant`. See also :ref:`gloss-runtsafe` and :ref:`gloss-non-runtsafe`.

See :ref:`storm-adv-vars` for a more detailed discussion of variables.

.. _gloss-view:

View
----

Within Synapse, a view is a ordered set of layers (see :ref:`gloss-layer`) and associated permissions that are used to
synthesize nodes from the :ref:`gloss-cortex`, determining both the nodes that are visible to users via that view and
where (i.e., in what layer) any changes made by a view's users are recorded. A default Cortex consists of a single
layer and a single view, meaning that by default all nodes are stored in one layer and all changes are written to that
layer.

In multi-layer systems, a view consists of the set of layers that should be visible to users of that view, and the
order in which the layers should be instantiated for that view.  Order matters because typically only the topmost layer
is writeable by that view's users, with subsequent (lower) layers read-only. Explicit actions can push upper-layer
writes downward (merge) into lower layers.
