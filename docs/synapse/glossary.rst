
.. highlight:: none

.. _glossary:

Synapse Glossary
################

This Glossary provides a quick reference for common terms related to Synapse technical and analytical concepts.

A
=

.. _gloss-addition-auto:

Addition, Automatic
-------------------

See :ref:`gloss-autoadd`.

.. _gloss-addition-dependent:

Addition, Dependent
-------------------

See :ref:`gloss-depadd`.

.. _gloss-adv-power:

Advanced Power-Up
-----------------

See :ref:`gloss-power-adv`.

.. _gloss-admin-tool:

Admin Tool
----------

See :ref:`gloss-tool-admin`.

.. _gloss-analytical-model:

Analytical Model
----------------

See :ref:`gloss-model-analytical`.

.. _gloss-authgate:

Auth Gate
---------

An auth gate (short for "authorization gate", informally a "gate") is an object within a :ref:`gloss-service`
that may have its own set of permissions.

Both a :ref:`gloss-layer` and a :ref:`gloss-view` are common examples of auth gates.

.. _gloss-autoadd:

Autoadd
-------

Short for "automatic addition". Within Synapse, a feature of node creation where any secondary properties that
are derived from a node's primary property are automatically set when the node is created. Because these secondary
properties are based on the node's primary property (which cannot be changed once set), the secondary properties
are read-only.

For example, creating the node ``inet:email=alice@mail.somecompany.org`` will result in the autoadd of the secondary
properties ``inet:email:user=alice`` and ``inet:email:domain=mail.somecompany.org``.

See also the related concept :ref:`gloss-depadd`.

.. _gloss-axon:

Axon
----

The Axon is a :ref:`gloss-synapse-svc` that provides binary / blob ("file") storage within the Synapse ecosystem. An Axon indexes
binaries based on their SHA-256 hash for deduplication. The default Axon implemenation stores the blobs in an LMDB
:ref:`gloss-slab`.

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

.. _gloss-callable-func:

Callable Function
-----------------

See :ref:`gloss-func-callable`.

.. _gloss-cell:

Cell
----

The Cell is a basic building block of a :ref:`gloss-synapse-svc`, including the :ref:`gloss-cortex`. See :ref:`dev_architecture`
for additional detail.

.. _gloss-col-embed:

Column, Embed
-------------

In :ref:`gloss-optic`, a column in Tabular display mode that displays a **property value from an adjacent or nearby
node**.

.. _gloss-col-path-var:

Column, Path Variable
---------------------

In :ref:`gloss-optic`, a column in Tabular display mode that displays **arbitrary data in a column** by defining
the data as a :ref:`gloss-variable` (a path variable or "path var") within a Storm query.


.. _gloss-col-prop:

Column, Property
----------------

In :ref:`gloss-optic`, a column in Tabular display mode that displays a **property value** from the specified form.

.. _gloss-col-tag:

Column, Tag
-----------

In :ref:`gloss-optic`, a column in Tabular display mode that displays the **timestamps** associated with the
specified tag. (Technically, Optic displays two columns - one for each of the min / max timestamps, if present).

.. _gloss-col-tagglob:

Column, Tag Glob
----------------

In :ref:`gloss-optic`, a column in Tabular display mode that displays any **tags** that match the specified tag
or tag glob pattern.

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

.. _gloss-console-tool:

Console Tool
------------

See :ref:`gloss-tool-console`.

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

A Cortex is a :ref:`gloss-synapse-svc` that implements Synapse's primary data store (as an individual
:ref:`gloss-hypergraph`). Cortex features include scalability, key/value-based node properties, and a
:ref:`gloss-data-model` which facilitates normalization.

.. _gloss-cron:

Cron
----

Within Synapse, cron jobs are used to create scheduled tasks, similar to the Linux/Unix "cron" utility. The task to be
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

Similar to a traditional Linux or Unix daemon, a Synapse daemon ("dmon") is a long-running or recurring query or process that
runs continuously in the background. A dmon is typically implemented by a Storm :ref:`gloss-service` and may be used
for tasks such as processing elements from a :ref:`gloss-queue`. A dmon allows for non-blocking background processing
of non-critical tasks. Dmons are persistent and will restart if they exit.

.. _gloss-emitter-func:

Data Emitter Function
---------------------

See :ref:`gloss-func-emitter`.

.. _gloss-data-model:

Data Model
----------

See :ref:`gloss-model-data`.

.. _gloss-data-model-explorer:

Data Model Explorer
-------------------

In :ref:`gloss-optic`, the Data Model Explorer (found in the :ref:`gloss-help-tool`) documents and cross-references
the current forms and lightweight edges in the Synapse :ref:`gloss-data-model`.

.. _gloss-deconflictable:

Deconflictable
--------------

Within Synapse, a term typically used with respect to :ref:`gloss-node` creation. A node is deconflictable if, upon node
creation, Synapse can determine whether the node already exists within a Cortex (i.e., the node creation attempt is
deconflicted against existing nodes). For example, on attempting to create the node ``inet:fqdn=woot.com`` Synapse can
deconflict the node by checking whether a node of the same form with the same primary property already exists.

Most primary properties are sufficiently unique to be readily deconflictable. GUID forms (see :ref:`gloss-form-guid`)
require additional considerations for deconfliction. See the :ref:`type-guid` section of the :ref:`storm-ref-type-specific`
document for additional detail.

.. _gloss-depadd:

Depadd
------

Short for "dependent addition". Within Synapse, when a node's secondary property is set, if that secondary property
is of a type that is also a form, Synapse will automatically create the node with the corresponding primary property
value if it does not already exist. (You can look at this as the secondary property value being "dependent on" the
existence of the node with the corresponding primary property value.)

For example, creating the node ``inet:email=alice@mail.somecompany.org`` will set (via :ref:`gloss-autoadd`) the
secondary property ``inet:email:domain=mail.somecompany.org``. Synapse will automatically create the node 
``inet:fqdn=mail.somecompany.org`` as a dependent addition if it does not exist.

(Note that limited recursion will occur between dependent additions (depadds) and automatic additions (autoadds).
When ``inet:fqdn=mail.somecompany.org`` is created via depadd, Synapse will set (via autoadd) 
``inet:fqdn:domain=somecompany.org``, which will result in the creation (via depadd) of the node
``inet:fqdn=somecompany.org`` if it does not exist, etc.)

See also the related concept :ref:`gloss-autoadd`.

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

.. _gloss-display-mode:

Display Mode
------------

In :ref:`gloss-optic`, a means of visualizing data using the :ref:`gloss-research-tool`. Optic supports the following display modes:

- **Tabular mode,** which displays data and tags in tables (rows of results with configurable columns).
- **Force Graph mode,** which projects data into a directed graph-like view of nodes and their interconnections.
- **Statistics (stats) mode,** which automatically summarizes data using histogram (bar) and sunburst charts.
- **Geospatial mode,** which can be used to plot geolocation data on a map projection.
- **Tree Graph mode,** which displays nodes as a series of vertical "cards" and their property-based links to other nodes.
- **Timeline mode,** which displays nodes with a time property in time sequence order.

.. _gloss-dmon:

Dmon
----

Short for :ref:`gloss-daemon`.

E
=

.. _gloss-easy-perms:

Easy Permissions
----------------

In Synapse, easy permissions ("easy perms" for short) are a simplified means to grant common sets of permissions
for a particular object to users or roles. Easy perms specify four levels of access, each with a corresponding
integer value:

- Deny = 0
- Read = 1
- Edit = 2
- Admin = 3


As an example, the :ref:`stormlibs-lib-macro-grant` Storm library can be used to assign easy perms to a :ref:`gloss-macro`.
Contrast with :ref:`gloss-permission`.

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

.. _gloss-embed-col:

Embed Column
------------

See :ref:`gloss-col-embed`.

.. _gloss-entity-res:

Entity Resolution
-----------------

Entity resolution is the process of determining whether different records or sets of data refer to the same
real-world entity.

A number of data model elements in Synapse are designed to support entity resolution. For example:

- A ``ps:contact`` node can capture "a set of observed contact data" for a person (``ps:person``) or organization
  (``ou:org``). You can link sets of contact data that you assess represent "the same" entity via their
  ``ps:contact:person`` or ``ps:contact:org`` properties.

- A ``risk:threat`` node can capture "a set of reported data about a threat". If you assess that multiple sources
  are reporting on "the same" threat, you can link them to an authoritative threat organization via their
  ``risk:threat:org`` property.
  
- An ``ou:industryname`` node can capture a term used to refer to a commercial industry. You can link variations
  of a name (e.g., "finance", "financial", "financial services", "banking and finance") to a single ``ou:industry``
  via the ``ou:industry:name`` and ``ou:industry:names`` properties.


.. _gloss-extended-comp-op:

Extended Comparison Operator
----------------------------

See :ref:`gloss-comp-op-extended`.

.. _gloss-extended-form:

Extended Form
-------------

See :ref:`gloss-form-extended`.


.. _gloss-extended-prop:

Extended Property
-----------------

See :ref:`gloss-prop-extended`.

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

Within Synapse, one of the primary methods for interacting with data in a :ref:`gloss-cortex`. A filter operation
downselects a subset of nodes from a set of results. Compare with :ref:`gloss-lift`, :ref:`gloss-pivot`, and
:ref:`gloss-traverse`.

See :ref:`storm-ref-filter` for additional detail.

.. _gloss-filter-subquery:

Filter, Subquery
----------------

Within Synapse, a subquery filter is a filter that consists of a :ref:`gloss-storm` expression.


See :ref:`filter-subquery` for additional detail.

.. _gloss-fork:

Fork
----

Within Synapse, **fork** may refer to the process of forking a :ref:`gloss-view`, or to the forked view itself.

When you fork a view, you create a new, empty, writable :ref:`gloss-layer` on top of the fork's original view.
The writable layer from the original view becomes read-only with respect to the fork. Any changes made within a
forked view are made within the new writable layer. These changes can optionally be merged back into the original
view (in whole or in part), or discarded. (Note that any view-specific automation, such as triggers, dmons, or cron
jobs, are **not** copied to the forked view. However, depending on the automation, it may be activated if / when 
data is merged down into the original view.

.. _gloss-form:

Form
----

A form is the definition of an object in the Synapse data model. A form acts as a "template" that specifies how
to create an object (:ref:`gloss-node`) within a Cortex. A form consists of (at minimum) a :ref:`gloss-primary-prop`
and its associated :ref:`gloss-type`. Depending on the form, it may also have various secondary properties with
associated types.

See the :ref:`data-form` section in the :ref:`data-model-terms` document for additional detail.


.. _gloss-form-comp:

Form, Composite
---------------

A category of form whose primary property is an ordered set of two or more comma-separated typed values. Examples
include DNS A records (``inet:dns:a``) and web-based accounts (``inet:web:acct``).

.. _gloss-form-digraph:

See also :ref:`gloss-form-edge`.

.. _gloss-form-edge:

Form, Edge
----------

A specialized **composite form** (:ref:`gloss-form-comp`) whose primary property consists of two :ref:`gloss-ndef`
values. Edge forms can be used to link two arbitrary forms via a generic relationship where additional information
needs to be captured about that relationship (i.e., via secondary properties and/or tags). Contrast with
:ref:`gloss-edge-light`.

.. _gloss-form-extended:

Form, Extended
--------------

A custom form added outside of the base Synapse :ref:`gloss-data-model` to represent specialized data. Extended
forms can be added with the :ref:`stormlibs-lib-model-ext` libraries. **Note** that whenever possible, it is
preferable to expand the base Synapse data model to account for novel use cases instead of creating specialized
extended forms.


.. _gloss-form-guid:

Form, GUID
----------

In the Synpase :ref:`gloss-data-model`, a specialized case of a :ref:`gloss-simple-form` whose primary property is a
:ref:`gloss-guid`. The GUID can be either arbitrary or constructed from a specified set of values. GUID forms have
additional considerations as to whether or not they are :ref:`gloss-deconflictable` in Synapse. Examples of GUID
forms include file execution data (e.g., ``inet:file:exec:read``) or articles (``media:news``).

.. _gloss-form-simple:

Form, Simple
------------

In the Synapse :ref:`gloss-data-model`, a category of form whose primary property is a single typed value. Examples
include domains (``inet:fqdn``) or hashes (e.g., ``hash:md5``).

.. _gloss-func-callable:

Function, Callable
------------------

In Storm, a callable function is a "regular" function that is invoked (called) and returns exactly one value.
A callable function must include a ``return()`` statement and must not include the ``emit`` keyword.

.. _gloss-func-emitter:

Function, Data Emitter
----------------------

In Storm, a data emitter function emits data. The function returns a generator object that can be iterated over.
A data emitter function must include the ``emit`` keyword and must not include a ``return()`` statement.

.. _gloss-func-yielder:

Function, Node Yielder
----------------------

In Storm, a node yielder function yields nodes. The function returns a generator object that can be iterated
over. A node yielder function must not include either the ``emit`` keyword or a ``return()`` statement.

.. _gloss-fused-know:

Fused Knowledge
---------------

See :ref:`gloss-know-fused`.

G
=

.. _gloss-gate:

Gate
----

See :ref:`gloss-authgate`.

.. _gloss-global-workspace:

Global Default Workspace
------------------------

See :ref:`gloss-workspace-global`.

.. _gloss-global-uniq-id:

Globally Unique Identifier
--------------------------

See :ref:`gloss-guid`.

.. _gloss-graph:

Graph
-----

A graph is a mathematical structure used to model pairwise relations between objects. Graphs consist of vertices
(or nodes) that represent objects and edges that connect exactly two vertices in some type of relationship.
Nodes and edges in a graph are typically represented by dots or circles connected by lines.

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
represented by a specific value or set of values.

.. _gloss-guid-form:

GUID Form
---------

See :ref:`gloss-form-guid`.

H
=

.. _gloss-help-tool:

Help Tool
---------

See :ref:`gloss-tool-help`.

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

.. _gloss-ingest-tool:

Ingest Tool
-----------

See :ref:`gloss-tool-ingest`.

.. _gloss-interface:

Interface
---------

In Synapse, an interface is a data model element that defines a set of secondary properties that are common to a
subset of related forms. Forms that should have the set of secondary properties can be defined so as to "inherit"
the interface and its properties, as opposed to explicitly declaring each property on every form.

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
another way, a layer is a storage and write permission boundary.

By default, a :ref:`gloss-cortex` has a single layer and a single :ref:`gloss-view`, meaning that by default all
nodes are stored in one layer and all changes are written to that layer. However, multiple layers can be created
for various purposes such as:

- separating data from different data sources (e.g., a read-only layer consisting of third-party data and associated
  tags can be created underneath a "working" layer, so that the third-party data is visible but cannot be modified);
- providing users with a personal "scratch space" where they can make changes in their layer without affecting the
  underlying main Cortex layer; or
- segregating data sets that should be visible/accessible to some users but not others.

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

Within Synapse, one of the primary methods for interacting with data in a :ref:`gloss-cortex`. A lift is a read
operation that selects a set of nodes from the Cortex. Compare with :ref:`gloss-pivot`, :ref:`gloss-filter`, and
:ref:`gloss-traverse`.

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

.. _gloss-merge:

Merge
-----

Within Synapse, merge refers to the process of copying changes made within a forked (see :ref:`gloss-fork`) 
:ref:`gloss-view` into the original view.

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

.. _gloss-node-action:

Node Action
-----------

In :ref:`gloss-optic`, a saved, named Storm query or command (action) that can be executed via a right-click
context menu option for specified forms (nodes).

.. _gloss-node-data:

Node Data
---------

Node data is a named set of structured metadata that may optionally be stored on a node in Synapse. Node data
may be used for a variety of purposes. For example, a :ref:`gloss-power-up` may use node data to cache results returned by
a third-party API along with the timestamp when the data was retrieved. If the same API is queried again for 
the same node within a specific time period, the Power-Up can use the cached node data instead of re-querying
the API (helping to prevent using up any API query limits by re-querying the same data).

Node data can be accessed using the `node:data`_ type.

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

.. _gloss-node-storage:

Node, Storage
-------------

A storage node ("sode") is a collection of data for a given node (i.e., the node's primary property,
secondary / universal properties, tags, etc.) that is present in a specific :ref:`gloss-layer`.

.. _gloss-yielder-func:

Node Yielder Function
---------------------

See :ref:`gloss-func-yielder`.

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

O
=

.. _gloss-optic:

Optic
-----

The Synapse user interface (UI), available as part of the commercial Synapse offering.

P
=

.. _gloss-package:

Package
-------

A package is a set of commands and library code used to implement a :ref:`gloss-storm-svc`. When a new Storm
service is loaded into a Cortex, the Cortex verifies that the service is legitimate and then requests the service's
packages in order to load any extended Storm commands associated with the service and any library code used to
implement the service.

.. _gloss-path-var-col:

Path Variable Column
--------------------

See :ref:`gloss-col-path-var`.

.. _gloss-permission:

Permission
----------

Within Synapse, a permission is a string (such as ``node.add``) used to control access. A permission is assigned
(granted or revoked) using a :ref:`gloss-rule`.

Access to some objects in Synapse may be controlled by :ref:`gloss-easy-perms`.

.. _gloss-pivot:

Pivot
-----

Within Synapse, one of the primary methods for interacting with data in a :ref:`gloss-cortex`. A pivot moves from
a set of nodes with one or more properties with specified value(s) to a set of nodes with a property having the
same value(s). Compare with :ref:`gloss-lift`, :ref:`gloss-filter`, and :ref:`gloss-traverse`.

See :ref:`storm-ref-pivot` for additional detail.

.. _gloss-power-up:

Power-Up
--------

Power-Ups provide specific add-on capabilities to Synapse. For example, Power-Ups may provide connectivity to
external databases or third-party data sources, or enable functionality such as the ability to manage YARA rules,
scans, and matches.

The term Power-Up is most commonly used to refer to Vertex-developed packages and services that are available as
part of the commercial Synapse offering (only a few Power-Ups are available with open-source Synapse). However,
many organizations write their own custom packages and services that may also be referred to as Power-Ups.

Vertex distinguishes between an :ref:`gloss-adv-power` and a :ref:`gloss-rapid-power`.

.. _gloss-power-adv:

Power-Up, Advanced
------------------

Advanced Power-Ups are implemented as Storm services (see :ref:`gloss-svc-storm`). Vertex-developed Advanced
Power-Ups are implemented as `Docker containers`_ and may require DevOps support and additional resources to
deploy.

.. _gloss-power-rapid:

Power-Up, Rapid
---------------

Rapid Power-Ups are implemented as Storm packages (see :ref:`gloss-package`). Rapid Power-Ups are written
entirely in Storm and can be loaded directly into a :ref:`gloss-cortex`.

.. _gloss-power-ups-tool:

Power-Ups Tool
--------------

See :ref:`gloss-tool-power-ups`.

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

.. _gloss-prop-col:

Property Column
---------------

See :ref:`gloss-col-prop`.

.. _gloss-prop-derived:

Property, Derived
-----------------

Within Synapse, a derived property is a secondary property that can be extracted (derived) from a node's primary
property. For example, the domain ``inet:fqdn=www.google.com`` can be used to derive ``inet:fqdn:domain=google.com``
and ``inet:fqdn:host=www``; the DNS A record ``inet:dns:a=(woot.com, 1.2.3.4)`` can be used to derive 
``inet:dns:a:fqdn=woot.com`` and ``inet:dns:a:ipv4=1.2.3.4``. 

Synapse will automatically set (:ref:`gloss-autoadd`) any secondary properties that can be derived from a node's
primary property. Because derived properties are based on primary property values, derived
secondary properties are always read-only (i.e., cannot be modified once set).


.. _gloss-prop-extended:

Property, Extended
------------------

Within Synapse, an extended property is a custom property added to an existing form to capture specialized data.
For example, extended properties may be added to the data model by a :ref:`gloss-power-up` in order to record
vendor-specific data (such as a "risk" score).

Extended properties can be added with the :ref:`stormlibs-lib-model-ext` libraries. **Note** that we strongly
recommend that any extended properties be added within a custom namespace; specifically, that property names
begin with an underscore and include a vendor or source name (if appropriate) as the first namespace element.

An example of an extended property is the ``:_virustotal:reputation`` score added to some forms to account
for VirusTotal-specific data returned by that Power-Up (e.g., ``inet:fqdn:_virustotal:reputation``).


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

.. _gloss-rapid-power:

Rapid Power-Up
--------------

See :ref:`gloss-power-rapid`.


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

.. _gloss-research-tool:

Research Tool
-------------

See :ref:`gloss-tool-research`.

.. _gloss-role:

Role
----

In Synapse, a role is used to group users with similar authorization needs. You can assign a set of rules (see
:ref:`gloss-rule`) to a role, and grant the role to users who need to perform those actions.

.. _gloss-root-tag:

Root Tag
--------

See :ref:`gloss-tag-root`.

.. _gloss-rule:

Rule
----

Within Synapse, a rule is a structure used to assign (grant or prohibit) a specific :ref:`gloss-permission` (e.g.,
``node.tag`` or ``!view.del``). A rule is assigned to a :ref:`gloss-user` or a :ref:`gloss-role`.


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
explicitly set, such as ``$fqdn = woot.com`` is an example of a runtsafe varaible.

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

Synapse is designed as a modular set of services. Broadly speaking, a service can be thought of as a container
used to run an application. We may informally differentiate between a :ref:`gloss-synapse-svc` and a
:ref:`gloss-storm-svc`.

.. _gloss-svc-storm:

Service, Storm
--------------

A Storm service is a registerable remote component that can provide packages (:ref:`gloss-package`) and
additional APIs to Storm and Storm commands. A service resides on a :ref:`gloss-telepath` API endpoint outside
of the :ref:`gloss-cortex`.

When the Cortex is connected to a service, the Cortex queries the endpoint to determine if the service is legitimate
and, if so, loads the associated package to implement the service.

An advantage of Storm services (over, say, additional Python modules) is that services can be restarted to reload
their service definitions and packages while a Cortex is still running -- thus allowing a service to be updated
without having to restart the entire Cortex.


.. _gloss-svc-synapse:

Service, Synapse
----------------

Synapse services make up the core Synapse architecture and include the :ref:`gloss-cortex` (data store),
:ref:`gloss-axon` (file storage), and the commercial :ref:`gloss-optic` UI. Synapse services are built on the
:ref:`gloss-cell` object.


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

.. _gloss-sode:

Sode
----

Short for "storage node". See :ref:`gloss-node-storage`.

.. _gloss-splice:

Splice
------

A splice is an atomic change made to data within a Cortex, such as node creation or deletion, adding or removing a tag,
or setting, modifying, or removing a property. All changes within a Cortex may be retrieved as individual splices within
the Cortex's splice log.

.. _gloss-spotlight-tool:

Spotlight Tool
--------------

See :ref:`gloss-tool-spotlight`.

.. _gloss-standard-comp-op:

Standard Comparison Operator
----------------------------

See :ref:`gloss-comp-op-standard`.

.. _gloss-storage-node:

Storage Node
------------

See :ref:`gloss-node-storage`.

.. _gloss-stories-tool:

Stories Tool
------------

See :ref:`gloss-tool-stories`.

.. _gloss-storm:

Storm
-----

Storm is the custom query language analysts use to interact with data in Synapse.

Storm can also be used as a programming language by advanced users and developers, though this level of expertise
is not required for normal use. Many of Synapse's **Power-Ups** (see :ref:`gloss-power-up`) are written in Storm.

See :ref:`storm-ref-intro` for additional detail.

.. _gloss-storm-editor:

Storm Editor
------------

Also "Storm Editor Tool". See :ref:`gloss-tool-storm-editor`.

.. _gloss-storm-svc:

Storm Service
-------------

See :ref:`gloss-svc-storm`.

.. _gloss-subquery:

Subquery
--------

Within Synapse, a subquery is a :ref:`gloss-storm` query that is executed inside of another Storm query.


See :ref:`storm-ref-subquery` for additional detail.

.. _gloss-subquery-filter:

Subquery Filter
---------------

See :ref:`gloss-filter-subquery`.

.. _gloss-synapse-svc:

Synapse Service
---------------

See :ref:`gloss-svc-synapse`.


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

.. _gloss-tag-col:

Tag Column
----------

See :ref:`gloss-col-tag`.

.. _gloss-tag-explorer:

Tag Explorer
------------

In :ref:`gloss-optic`, the Tag Explorer (found in the :ref:`gloss-help-tool`) provides an expandable,
tree-based listing of all tags in your Synapse :ref:`gloss-cortex`, along with their definitions (if
present).

.. _gloss-tagglob-col:

Tag Glob Column
---------------

See :ref:`gloss-col-tagglob`.

.. _gloss-taxonomy:

Taxonomy
--------

In Synapse, a taxonomy is a user-defined set of hierarchical categories that can optionally be used to further
classify particular objects (forms). Taxonomies use a dotted namespace (similar to tags). Forms that support
a taxonomy will have a secondary property whose :ref:`gloss-type` is the taxonomy for that form (e.g., an
``ou:industry`` form has a ``:type`` secondary property whose type is ``ou:industry:type:taxonomy``).

.. _gloss-telepath:

Telepath
--------

Telepath is a lightweight remote procedure call (RPC) protocol used in Synapse. See :ref:`arch-telepath` in the
:ref:`dev_architecture` guide for additional detail.

.. _gloss-tool-admin:

Tool, Admin
-----------

In :ref:`gloss-optic`, the Admin Tool provides a unified interface to perform basic management of
users, roles, and permissions; views and layers; and triggers and cron jobs.

.. _gloss-tool-console:

Tool, Console
-------------

In :ref:`gloss-optic`, the Console Tool provides a CLI-like interface to Synapse. It can be used to run
Storm queries in a manner similar to the Storm CLI (in the community version of Synapse). In Optic the
Console Tool is more commonly used to display status, error, warning, and debug messages, or to view help
for built-in Storm commands (see :ref:`storm-ref-cmd`) and / or Storm commands installed by Power-Ups.

.. _gloss-tool-help:

Tool, Help
----------

In :ref:`gloss-optic`, the central repository for Synapse documentation and assistance. The Help Tool
includes the :ref:`gloss-data-model-explorer`, :ref:`gloss-tag-explorer`, documentation for any
installed Power-Ups (see :ref:`gloss-power-up`), links to the public Synapse, Storm, and Optic
documents, and version / changelog information.

.. _gloss-tool-ingest:

Tool, Ingest
------------

In :ref:`gloss-optic`, the primary tool used to load structured data in CSV, JSON, or JSONL format into
Synapse using Storm. The Ingest Tool can also be used to prototype and test more formal ingest code.

.. _gloss-tool-power-ups:

Tool, Power-Ups
---------------

In :ref:`gloss-optic`, the tool used to view, install, update, and remove Power-Ups (see :ref:`gloss-power-up`).

.. _gloss-tool-research:

Tool, Research
--------------

In :ref:`gloss-optic`, the primary tool used to ingest, enrich, explore, visualize, and annotate Synapse data.

.. _gloss-tool-spotlight:

Tool, Spotlight
---------------

Also known as simply "Spotlight". In :ref:`gloss-optic`, a tool used to load and display PDF or HTML content,
create an associated ``media:news`` node, and easily extract and link relevant indicators or other nodes.

.. _gloss-tool-stories:

Tool, Stories
-------------

Also known as simply "Stories". In :ref:`gloss-optic`, a tool used to create, collaborate on, review, and publish
finished reports. Stories allows you to integrate data directly from the :ref:`gloss-research-tool` into your
report ("Story").

.. _gloss-tool-storm-editor:

Tool, Storm Editor
------------------

Also known as simply "Storm Editor". In :ref:`gloss-optic`, a tool used to compose, test, and store Storm
queries (including macros - see :ref:`gloss-macro`). Storm Editor includes a number of integrated development
environment (IDE) features, including syntax highlighting, auto-indenting, and auto-completion for the names
of forms, properties, tags, and libraries.

.. _gloss-tool-workflows:

Tool, Workflows
---------------

In :ref:`gloss-optic`, the tool used to access and work with Workflows (see :ref:`gloss-workflow`).

.. _gloss-tool-workspaces:

Tool, Workspaces
----------------

In :ref:`gloss-optic`, the tool used to configure and manage a user's Workspaces (see :ref:`gloss-workspace`).

.. _gloss-traverse:

Traverse
--------

Within Synapse, one of the primary methods for interacting with data in a :ref:`gloss-cortex`. Traversal refers
to navigating the data by crossing ("walking") a lighweight (light) edge (:ref:`gloss-edge-light`) betweeen 
nodes. Compare with :ref:`gloss-lift`, :ref:`gloss-pivot`, and :ref:`gloss-filter`.

See :ref:`storm-traverse` for additional detail.

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

.. _gloss-user:

User
----

In Synapse, a user is represented by an account in the Cortex. An account is required to authenticate (log in)
to the Cortex and is used for authorization (permissions) to access services and perform operations.


V
=

.. _gloss-variable:

Variable
--------

In Storm, a variable is an identifier with a value that can be defined and/or changed during normal execution, i.e.,
the value is variable.

Contrast with :ref:`gloss-constant`. See also :ref:`gloss-runtsafe` and :ref:`gloss-non-runtsafe`.

See :ref:`storm-adv-vars` for a more detailed discussion of variables.


.. _gloss-vault:

Vault
-----

In Synapse, a vault is a protected storage mechanism that allows you to store secret values (such as API keys) and
any associated configuration settings. Vaults support permissions and can be shared with other users or roles.
Granting 'read' access to a vault allows someone to use the vault contents without allowing them to see the
vault's secret values.


.. _gloss-view:

View
----

Within Synapse, a view is a ordered set of layers (see :ref:`gloss-layer`) and associated permissions that are used to
synthesize nodes from the :ref:`gloss-cortex`, determining both the nodes that are visible to users via that view and
where (i.e., in what layer) any changes made by a view's users are recorded. A default Cortex consists of a single
layer and a single view, meaning that by default all nodes are stored in one layer, all changes are written to that
layer, and all users have the same visibility (view) into Synapse's data.

In multi-layer systems, a view consists of the set of layers that should be visible to users of that view, and the
order in which the layers should be instantiated for that view.  Order matters because typically only the topmost layer
is writeable by that view's users, with subsequent (lower) layers read-only. Explicit actions can push upper-layer
writes downward (merge) into lower layers.

W
=

.. _gloss-workflow:

Workflow
--------

In :ref:`gloss-optic`, a Workflow is a customized set of UI elements that provides an intuitive way to perform
particular tasks. Workflows may be installed by Synapse Power-Ups (see :ref:`gloss-power-up`) and give users a
more tailored means (compared to the :ref:`gloss-research-tool` or Storm query bar) to work with Power-Up Storm
commands or associated analysis tasks.

.. _gloss-workflows-tool:

Workflows Tool
--------------

See :ref:`gloss-tool-workflows`.

.. _gloss-workspace:

Workspace
---------

In :ref:`gloss-optic`, a Workspace is a customizable user environment. Users may configure one or more Workspaces; different Workspaces may be designed to support different analysis tasks.

.. _gloss-workspace-global:

Workspace, Global Default
-------------------------

In :ref:`gloss-optic`, a Workspace that has been pre-configured with various custom settings and distributed for use. A Global Default Workspace can be used to share a set of baseline Workspace customizations with a particular group or team.

.. _gloss-workspaces-tool:

Workspaces Tool
---------------

See :ref:`gloss-tool-workspaces`.


.. _node:data: https://synapse.docs.vertex.link/en/latest/synapse/autodocs/stormtypes_prims.html#node-data

.. _`Docker containers`: https://www.docker.com/resources/what-container/
