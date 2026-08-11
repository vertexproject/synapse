<a id="glossary"></a>


# Synapse Glossary

This Glossary provides a quick reference for common terms related to Synapse technical and analytical concepts.

## A

<a id="gloss-addition-auto"></a>


### Addition, Automatic

See [Autoadd](glossary.md#gloss-autoadd).

<a id="gloss-addition-dependent"></a>


### Addition, Dependent

See [Depadd](glossary.md#gloss-depadd).

<a id="gloss-adv-power"></a>


### Advanced Power-Up

See [Power-Up, Advanced](glossary.md#gloss-power-adv).

<a id="gloss-admin-tool"></a>


### Admin Tool

See [Tool, Admin](glossary.md#gloss-tool-admin).

<a id="gloss-analytical-model"></a>


### Analytical Model

See [Model, Analytical](glossary.md#gloss-model-analytical).

<a id="gloss-authgate"></a>


### Auth Gate

An auth gate (short for "authorization gate", informally a "gate") is an object within a [service](glossary.md#gloss-service) that may have its own set of permissions.

Both a [layer](glossary.md#gloss-layer) and a [view](glossary.md#gloss-view) are common examples of auth gates.

<a id="gloss-autoadd"></a>


### Autoadd

Short for "automatic addition". Within Synapse, a feature of node creation where any secondary properties that are computed from a node's primary property are automatically set when the node is created. Because these secondary properties are based on the node's primary property (which cannot be changed once set), the secondary properties are read-only.

For example, creating the node `inet:email=alice@mail.somecompany.org` will result in the autoadd of the secondary properties `inet:email:username=alice` and `inet:email:fqdn=mail.somecompany.org`.

See also the related concept [depadd](glossary.md#gloss-depadd).

<a id="gloss-axon"></a>


### Axon

The Axon is a [Synapse Service](glossary.md#gloss-synapse-svc) that provides binary / blob ("file") storage within the Synapse ecosystem. An Axon indexes binaries based on their SHA-256 hash for deduplication. The default Axon implementation stores the blobs in an LMDB [Slab](glossary.md#gloss-slab).

## B

<a id="gloss-base-form"></a>


### Base Form

See [Form, Base](glossary.md#gloss-form-base).

<a id="gloss-base-tag"></a>


### Base Tag

See [Tag, Base](glossary.md#gloss-tag-base).

<a id="gloss-binary-uniq-id"></a>


### Binary Unique Identifier

See [BUID](glossary.md#gloss-buid).

<a id="gloss-buid"></a>


### BUID

Short for Binary Unique Identifier. Within Synapse, a BUID is the SHA-256 digest of a msgpack-encoded value.

Prior to Synapse 3.0.0, the BUID of a node's [ndef](glossary.md#gloss-ndef) was the node's identifier, and each [layer](glossary.md#gloss-layer) keyed its on-disk storage by that value. Nodes are now identified by an integer [NID](glossary.md#gloss-nid) instead, so a BUID is no longer used to refer to a node.

## C

<a id="gloss-callable-func"></a>


### Callable Function

See [Function, Callable](glossary.md#gloss-func-callable).

<a id="gloss-cell"></a>


### Cell

The Cell is a basic building block of a [Synapse Service](glossary.md#gloss-synapse-svc), including the [Cortex](glossary.md#gloss-cortex). See [Synapse Architecture](devguides/architecture.md#dev_architecture) for additional detail.

<a id="gloss-col-embed"></a>


### Column, Embed

In [Optic](glossary.md#gloss-optic), a column in Tabular display mode that displays a **property value from an adjacent or nearby node**.

<a id="gloss-col-path-var"></a>


### Column, Path Variable

In [Optic](glossary.md#gloss-optic), a column in Tabular display mode that displays **arbitrary data in a column** by defining the data as a [variable](glossary.md#gloss-variable) (a path variable or "path var") within a Storm query.

<a id="gloss-col-prop"></a>


### Column, Property

In [Optic](glossary.md#gloss-optic), a column in Tabular display mode that displays a **property value** from the specified form.

<a id="gloss-col-tag"></a>


### Column, Tag

In [Optic](glossary.md#gloss-optic), a column in Tabular display mode that displays the **timestamps** associated with the specified tag. (Technically, Optic displays two columns - one for each of the min / max timestamps, if present).

<a id="gloss-col-tagglob"></a>


### Column, Tag Glob

In [Optic](glossary.md#gloss-optic), a column in Tabular display mode that displays any **tags** that match the specified tag or tag glob pattern.

<a id="gloss-comparator"></a>


### Comparator

Short for [Comparison Operator](glossary.md#gloss-comp-operator).

<a id="gloss-comp-operator"></a>


### Comparison Operator

A symbol or set of symbols used in the Storm language to evaluate [node](glossary.md#gloss-node) property values against one or more specified values. Comparison operators can be grouped into standard and extended operators.

<a id="gloss-comp-op-standard"></a>


### Comparison Operator, Standard

The set of common operator symbols used to evaluate (compare) values in Storm. Standard comparison operators include equal to (`=`), greater than (`>`), less than (`<`), greater than or equal to (`>=`), and less than or equal to (`<=`).

<a id="gloss-comp-op-extended"></a>


### Comparison Operator, Extended

The set of Storm-specific operator symbols or expressions used to evaluate (compare) values in Storm based on custom or Storm-specific criteria. Extended comparison operators include regular expression (`~=`), time/interval (`@=`), set membership (`*in=`), tag (`#`), and so on.

<a id="gloss-comp-form"></a>


### Composite Form

See [Form, Composite](glossary.md#gloss-form-comp).

<a id="gloss-computed-prop"></a>


### Computed Property

See [Property, Computed](glossary.md#gloss-prop-computed).

<a id="gloss-console-tool"></a>


### Console Tool

See [Tool, Console](glossary.md#gloss-tool-console).

<a id="gloss-constant"></a>


### Constant

In Storm, a constant is a value that cannot be altered during normal execution, i.e., the value is constant.

Contrast with [Variable](glossary.md#gloss-variable). See also [Runtsafe](glossary.md#gloss-runtsafe) and [Non-Runtsafe](glossary.md#gloss-non-runtsafe).

<a id="gloss-constructor"></a>


### Constructor

Within Synapse, a constructor is code that defines how a [property](glossary.md#gloss-prop) value of a given [type](glossary.md#gloss-type) can be constructed to ensure that the value is well-formed for its type. Also known as a [ctor](glossary.md#gloss-ctor) for short. Constructors support [type normalization](glossary.md#gloss-type-norm) and [type enforcement](glossary.md#gloss-type-enforce).

<a id="gloss-constructor-guid"></a>


### Constructor, Guid

A [constructor](glossary.md#gloss-constructor) used to create [guid](glossary.md#gloss-guid) values. Sometimes shortened to [gutor](glossary.md#gloss-gutor), the term refers specifically to the use of a JSON dictionary to deconflict guid nodes and construct a predictable guid value (i.e., "dictionary guid constructor syntax" or "dictionary syntax"). See the [insertion](userguides/storm_ref_type_specific.md#guid-type-insertion) section under [guid](userguides/storm_ref_type_specific.md#type-guid) in the [Storm Reference - Type-Specific Storm Behavior](userguides/storm_ref_type_specific.md#storm-ref-type-specific) for a detailed discussion of guids, guid form deconfliction, and methods for generating guid values.

<a id="gloss-cortex"></a>


### Cortex

A Cortex is a [Synapse Service](glossary.md#gloss-synapse-svc) that implements Synapse's primary data store (as an individual [hypergraph](glossary.md#gloss-hypergraph)). Cortex features include scalability, key/value-based node properties, and a [data model](glossary.md#gloss-data-model) which facilitates normalization.

<a id="gloss-cron"></a>


### Cron

Within Synapse, cron jobs are used to create scheduled tasks, similar to the Linux/Unix "cron" utility. The task to be executed by the cron job is specified using the [Storm](glossary.md#gloss-storm) query language.

See the Storm command reference for the [cron](userguides/storm_ref_cmd.md#storm-cron) command and the [Storm Reference - Automation](userguides/storm_ref_automation.md#storm-ref-automation) document for additional detail.

<a id="gloss-ctor"></a>


### Ctor

Pronounced "see-tore". Short for [Constructor](glossary.md#gloss-constructor).

## D

<a id="gloss-daemon"></a>


### Daemon

Similar to a traditional Linux or Unix daemon, a Synapse daemon ("dmon") is a long-running or recurring query or process that runs continuously in the background. A dmon is typically implemented by a Storm [service](glossary.md#gloss-service) and may be used for tasks such as processing elements from a [queue](glossary.md#gloss-queue). A dmon allows for non-blocking background processing of non-critical tasks. Dmons are persistent and will restart if they exit.

<a id="gloss-emitter-func"></a>


### Data Emitter Function

See [Function, Data Emitter](glossary.md#gloss-func-emitter).

<a id="gloss-data-model"></a>


### Data Model

See [Model, Data](glossary.md#gloss-model-data).

<a id="gloss-data-model-explorer"></a>


### Data Model Explorer

In [Optic](glossary.md#gloss-optic), the Data Model Explorer (found in the [Help Tool](glossary.md#gloss-help-tool)) documents and cross-references the current forms and lightweight edges in the Synapse [data model](glossary.md#gloss-data-model).

<a id="gloss-deconflictable"></a>


### Deconflictable

Within Synapse, a term typically used with respect to [node](glossary.md#gloss-node) creation. A node is deconflictable if, upon node creation, Synapse can determine whether the node already exists within a Cortex (i.e., the node creation attempt is deconflicted against existing nodes). For example, on attempting to create the node `inet:fqdn=woot.com` Synapse can deconflict the node by checking whether a node of the same form with the same primary property already exists.

Most primary properties are sufficiently unique to be readily deconflictable. Guid forms (see [Form, Guid](glossary.md#gloss-form-guid)) require additional considerations for deconfliction. See the [guid](userguides/storm_ref_type_specific.md#type-guid) section of the [Storm Reference - Type-Specific Storm Behavior](userguides/storm_ref_type_specific.md#storm-ref-type-specific) document for additional detail.

<a id="gloss-depadd"></a>


### Depadd

Short for "dependent addition". Within Synapse, when a node's secondary property is set, if that secondary property is of a type that is also a form, Synapse will automatically create the node with the corresponding primary property value if it does not already exist. (You can look at this as the secondary property value being "dependent on" the existence of the node with the corresponding primary property value.)

For example, creating the node `inet:email=alice@mail.somecompany.org` will set (via [autoadd](glossary.md#gloss-autoadd)) the secondary property `inet:email:fqdn=mail.somecompany.org`. Synapse will automatically create the node `inet:fqdn=mail.somecompany.org` as a dependent addition if it does not exist.

(Note that limited recursion will occur between dependent additions (depadds) and automatic additions (autoadds). When `inet:fqdn=mail.somecompany.org` is created via depadd, Synapse will set (via autoadd) `inet:fqdn:domain=somecompany.org`, which will result in the creation (via depadd) of the node `inet:fqdn=somecompany.org` if it does not exist, etc.)

See also the related concept [autoadd](glossary.md#gloss-autoadd).

<a id="gloss-directed-edge"></a>


### Directed Edge

See [Edge, Directed](glossary.md#gloss-edge-directed).

<a id="gloss-directed-graph"></a>


### Directed Graph

See [Graph, Directed](glossary.md#gloss-graph-directed).

<a id="gloss-display-mode"></a>


### Display Mode

In [Optic](glossary.md#gloss-optic), a means of visualizing data using the [Research Tool](glossary.md#gloss-research-tool). Optic supports the following display modes:

- **Tabular mode,** which displays data and tags in tables (rows of results with configurable columns).
- **Force Graph mode,** which projects data into a directed graph-like view of nodes and their interconnections.
- **Statistics (stats) mode,** which automatically summarizes data using histogram (bar) and sunburst charts.
- **Geospatial mode,** which can be used to plot geolocation data on a map projection.
- **Tree Graph mode,** which displays nodes as a series of vertical "cards" and their property-based links to other nodes.
- **Timeline mode,** which displays nodes with a time property in time sequence order.

<a id="gloss-dmon"></a>


### Dmon

Short for [Daemon](glossary.md#gloss-daemon).

## E

<a id="gloss-easy-perms"></a>


### Easy Permissions

In Synapse, easy permissions ("easy perms" for short) are a simplified means to grant common sets of permissions for a particular object to users or roles. Easy perms specify four levels of access, each with a corresponding integer value:

- Deny = 0
- Read = 1
- Edit = 2
- Admin = 3

As an example, the [stormlibs-lib-macro-grant](stormtypes_libs.md#stormlibs-lib-macro-grant) Storm library can be used to assign easy perms to a [macro](glossary.md#gloss-macro). Contrast with [Permission](glossary.md#gloss-permission).

<a id="gloss-edge"></a>


### Edge

In a traditional [graph](glossary.md#gloss-graph), an edge is used to connect exactly two nodes (vertices). Compare with [Hyperedge](glossary.md#gloss-hyperedge).

<a id="gloss-edge-directed"></a>


### Edge, Directed

In a [directed graph](glossary.md#gloss-directed-graph), a directed edge is used to connect exactly two nodes (vertices) in a one-way (directional) relationship. Compare with [Hyperedge](glossary.md#gloss-hyperedge).

<a id="gloss-edge-light"></a>


### Edge, Lightweight (Light)

In Synapse, a lightweight (light) edge is a mechanism that links two arbitrary forms via a user-defined verb that describes the linking relationship. Light edges are not forms and so do not support secondary properties or tags. They are meant to simplify performance, representation of data, and Synapse hypergraph navigation for many use cases.

<a id="gloss-embed-col"></a>


### Embed Column

See [Column, Embed](glossary.md#gloss-col-embed).

<a id="gloss-entity-res"></a>


### Entity Resolution

Entity resolution is the process of determining whether different records or sets of data refer to the same real-world entity.

A number of data model elements in Synapse are designed to support entity resolution. For example:

- An `entity:contact` node captures a set of observed contact data for entities such as people (`ps:person`) or organizations (`ou:org`). You can link sets of contact data that you assess represent the same entity to the authoritative person or organization via the `entity:contact:resolved` property.
- A `risk:threat` node captures a set of data about a threat (potentially an unknown threat with a pseudonym such as "APT1" or "Comment Crew") according to a specific reporter. If the identity of the threat becomes known (e.g., PLA Unit 61398) you can link the `risk:threat` node(s) to the real-world organization or person via the `risk:threat:resolved` property.
- An `ind:name` node captures a term used to refer to a commercial industry. You can link variations of a name (e.g., "finance", "financial", "financial services", "banking and finance") to a single `ind:industry` via the `ind:industry:name` and `ind:industry:names` properties.

<a id="gloss-expression-syntax"></a>


### Expression Syntax

In Storm, expression syntax refers to the use of parentheses ( `( )` ) to enclose an expression to be evaluated by the Storm syntax parser. The expression may contain numbers, quoted strings, arithmetic or boolean operators, JSON values, and other Storm values.

<a id="gloss-extended-comp-op"></a>


### Extended Comparison Operator

See [Comparison Operator, Extended](glossary.md#gloss-comp-op-extended).

<a id="gloss-extended-form"></a>


### Extended Form

See [Form, Extended](glossary.md#gloss-form-extended).

<a id="gloss-extended-prop"></a>


### Extended Property

See [Property, Extended](glossary.md#gloss-prop-extended).

## F

<a id="gloss-feed"></a>


### Feed

A feed is an ingest API used to add nodes directly to a [Cortex](glossary.md#gloss-cortex). Feeds are typically used for bulk node creation, such as ingesting data from an external source or system.

Feed data is always provided in Synapse's packed node format, which may be preceded by an export metadata header identifying the version of the data.

<a id="gloss-filter"></a>


### Filter

Within Synapse, one of the primary methods for interacting with data in a [Cortex](glossary.md#gloss-cortex). A filter operation downselects a subset of nodes from a set of results. Compare with [Lift](glossary.md#gloss-lift), [Pivot](glossary.md#gloss-pivot), and [Traverse](glossary.md#gloss-traverse).

See [Storm Reference - Filtering](userguides/storm_ref_filter.md#storm-ref-filter) for additional detail.

<a id="gloss-filter-subquery"></a>


### Filter, Subquery

Within Synapse, a subquery filter is a filter that consists of a [Storm](glossary.md#gloss-storm) expression.

See [Subquery Filters](userguides/storm_ref_filter.md#filter-subquery) for additional detail.

<a id="gloss-fork"></a>


### Fork

Within Synapse, **fork** may refer to the process of forking a [view](glossary.md#gloss-view), or to the forked view itself.

When you fork a view, you create a new, empty, writable [layer](glossary.md#gloss-layer) on top of the fork's original view. The writable layer from the original view becomes read-only with respect to the fork. Any changes made within a forked view are made within the new writable layer. These changes can optionally be merged back into the original view (in whole or in part), or discarded. (Note that any view-specific automation, such as triggers, dmons, or cron jobs, is **not** copied to the forked view. However, depending on the automation, it may be activated if / when data is merged down into the original view.)

<a id="gloss-form"></a>


### Form

A form is the definition of an object in the Synapse data model. A form acts as a "template" that specifies how to create a [node](glossary.md#gloss-node) within a Cortex. A form consists of (at minimum) a [primary property](glossary.md#gloss-primary-prop) and its associated [type](glossary.md#gloss-type). Depending on the form, it may also have various secondary properties with associated types.

See the [Form](userguides/data_model.md#data-form) section in the [Data Model Objects](userguides/data_model.md#data-model-terms) document for additional detail.

<a id="gloss-form-base"></a>


### Form, Base

In Synapse's [form inheritance](glossary.md#gloss-form-inheritance), a base form is the most fundamental form that other forms inherit from.

See also [Parent Form](glossary.md#gloss-parent-form).

<a id="gloss-form-comp"></a>


### Form, Composite

A category of form whose primary property is an ordered set of two or more comma-separated typed values. Examples include DNS A records (`inet:dns:a`) and HTTP request headers (`inet:http:request:header`).

<a id="gloss-form-extended"></a>


### Form, Extended

A custom form added outside of the base Synapse [data model](glossary.md#gloss-data-model) to represent specialized data. Extended forms can be added with the [stormlibs-lib-model-ext](stormtypes_libs.md#stormlibs-lib-model-ext) libraries.

See the section on [Extending the Data Model](userguides/data_model.md#data-model-extend) for details.

<a id="gloss-form-guid"></a>


### Form, Guid

In the Synapse [data model](glossary.md#gloss-data-model), a specialized case of a [simple form](glossary.md#gloss-simple-form) whose primary property is a [guid](glossary.md#gloss-guid). The guid can be either arbitrary or constructed from a specified set of values. Guid forms have additional considerations as to whether or not they are [deconflictable](glossary.md#gloss-deconflictable) in Synapse. Examples of Guid forms include file execution data (e.g., `it:exec:file:read`) or reports (`doc:report`).

<a id="gloss-form-parent"></a>


### Parent Form

In Synapse's [form inheritance](glossary.md#gloss-form-inheritance), a parent form is a form that other form(s) inherit from. A parent form may have its own parent form, or may be a [base form](glossary.md#gloss-base-form).

<a id="gloss-form-simple"></a>


### Form, Simple

In the Synapse [data model](glossary.md#gloss-data-model), a category of form whose primary property is a single typed value. Examples include domains (`inet:fqdn`) or hashes (e.g., `crypto:hash:md5`).

<a id="gloss-form-inheritance"></a>


### Form Inheritance

In the Synapse data model, forms can be structured hierarchically so that more specific or specialized forms inherit from / extend a more generic form (a [base form](glossary.md#gloss-base-form) or [parent form](glossary.md#gloss-parent-form)). The inheriting form gains all of the properties defined on its parent form(s) and may also have its own additional unique secondary properties.

See the [Inheritance](userguides/data_model.md#data-inheritance) section of the [Data Model Objects](userguides/data_model.md#data-model-terms) document for additional detail.

Contrast with [Interface](glossary.md#gloss-interface).

<a id="gloss-func-callable"></a>


### Function, Callable

In Storm, a callable function is a "regular" function that is invoked (called) and returns exactly one value. A callable function must include a `return()` statement and must not include the `emit` keyword.

<a id="gloss-func-emitter"></a>


### Function, Data Emitter

In Storm, a data emitter function emits data. The function returns a generator object that can be iterated over. A data emitter function must include the `emit` keyword and must not include a `return()` statement.

<a id="gloss-func-yielder"></a>


### Function, Node Yielder

In Storm, a node yielder function yields nodes. The function returns a generator object that can be iterated over. A node yielder function must not include either the `emit` keyword or a `return()` statement.

<a id="gloss-fused-know"></a>


### Fused Knowledge

See [Knowledge, Fused](glossary.md#gloss-know-fused).

## G

<a id="gloss-gate"></a>


### Gate

See [Auth Gate](glossary.md#gloss-authgate).

<a id="gloss-global-workspace"></a>


### Global Default Workspace

See [Workspace, Global Default](glossary.md#gloss-workspace-global).

<a id="gloss-global-uniq-id"></a>


### Globally Unique Identifier

See [Guid](glossary.md#gloss-guid).

<a id="gloss-graph"></a>


### Graph

A graph is a mathematical structure used to model pairwise relations between objects. Graphs consist of vertices (or nodes) that represent objects and edges that connect exactly two vertices in some type of relationship. Nodes and edges in a graph are typically represented by dots or circles connected by lines.

See [Graphs and Hypergraphs](userguides/background.md#bkd-graphs-hypergraphs) for additional detail on graphs and hypergraphs.

<a id="gloss-graph-directed"></a>


### Graph, Directed

A directed graph is a [graph](glossary.md#gloss-graph) where the edges representing relationships between nodes have a "direction". Given node X and node Y connected by edge E, the relationship is valid for X -\> E -\> Y but not Y -\> E -\> X. For example, the relationship "Fred owns bank account \#01234567" is valid, but "bank account \#01234567 owns Fred" is not. Nodes and edges in a directed graph are typically represented by dots or circles connected by arrows.

See [Graphs and Hypergraphs](userguides/background.md#bkd-graphs-hypergraphs) for additional detail on graphs and hypergraphs.

<a id="gloss-guid"></a>


### Guid

Short for Globally Unique Identifier. Within Synapse, a guid is a [type](glossary.md#gloss-type) specified as a 128-bit value that is unique within a given [Cortex](glossary.md#gloss-cortex). Guids are used as primary properties for forms that cannot be uniquely represented by a specific value or set of values.

<a id="gloss-guid-constructor"></a>


### Guid Constructor

See [Constructor, Guid](glossary.md#gloss-constructor-guid).

<a id="gloss-guid-form"></a>


### Guid Form

See [Form, Guid](glossary.md#gloss-form-guid).

<a id="gloss-gutor"></a>


### Gutor

Pronounced "goo-tore". Short for "guid constructor". See [Constructor, Guid](glossary.md#gloss-constructor-guid).

## H

<a id="gloss-help-tool"></a>


### Help Tool

See [Tool, Help](glossary.md#gloss-tool-help).

<a id="gloss-hyperedge"></a>


### Hyperedge

A hyperedge is an edge within a [hypergraph](glossary.md#gloss-hypergraph) that can join any number of nodes (vs. a [graph](glossary.md#gloss-graph) or [directed graph](glossary.md#gloss-directed-graph) where an edge joins exactly two nodes). A hyperedge joining an arbitrary number of nodes can be difficult to visualize in flat, two-dimensional space; for this reason hyperedges are often represented as a line or "boundary" encircling a set of nodes, thus "joining" those nodes into a related group.

See [Graphs and Hypergraphs](userguides/background.md#bkd-graphs-hypergraphs) for additional detail on graphs and hypergraphs.

<a id="gloss-hypergraph"></a>


### Hypergraph

A hypergraph is a generalization of a [graph](glossary.md#gloss-graph) in which an edge can join any number of nodes. If a [directed graph](glossary.md#gloss-directed-graph) where edges join exactly two nodes is two-dimensional, then a hypergraph where a [hyperedge](glossary.md#gloss-hyperedge) can join any number (n-number) of nodes is n-dimensional.

See [Graphs and Hypergraphs](userguides/background.md#bkd-graphs-hypergraphs) for additional detail on graphs and hypergraphs.

## I

<a id="gloss-iden"></a>


### Iden

Short for [Identifier](glossary.md#gloss-identifier). Within Synapse, the hexadecimal representation of a unique identifier (e.g., for a task, a trigger, a view, etc.). The term "identifier" / "iden" is used regardless of how the specific identifier is generated.

Nodes are not identified by an iden; they are identified by an integer [NID](glossary.md#gloss-nid).

<a id="gloss-identifier"></a>


### Identifier

See [Iden](glossary.md#gloss-iden).

<a id="gloss-ingest-tool"></a>


### Ingest Tool

See [Tool, Ingest](glossary.md#gloss-tool-ingest).

<a id="gloss-inheritance"></a>


### Inheritance

See [Form Inheritance](glossary.md#gloss-form-inheritance).

<a id="gloss-interface"></a>


### Interface

In Synapse, an interface is used to define and group similar forms within Synapse's data model. Forms (or other interfaces) can **implement** an interface. The interface can be used to collectively refer (i.e., in data model definitions or Storm queries) to the set of forms that implement the interface. Interfaces can optionally define a set of secondary properties that should be present on forms that implement the interface.

See the [Interface](userguides/data_model.md#data-interface) section of the [Data Model Objects](userguides/data_model.md#data-model-terms) document for additional detail.

Contrast with [Form Inheritance](glossary.md#gloss-form-inheritance).

<a id="gloss-inst-know"></a>


### Instance Knowledge

See [Knowledge, Instance](glossary.md#gloss-know-inst).

## K

<a id="gloss-know-fused"></a>


### Knowledge, Fused

If a form within the Synapse data model has a time interval property (such as `:seen` or `:period`), the form typically represents **fused knowledge** - a period of time during which an object, relationship, or activity existed, occurred, or was observed. Forms representing fused knowledge can be thought of as combining *n* number of individual instance knowledge (point-in-time) observations. `inet:dns:query` and `inet:dns:a` forms are examples of fused knowledge.

See [Instance Knowledge vs. Fused Knowledge](userguides/data_model.md#instance-fused) for a more detailed discussion.

<a id="gloss-know-inst"></a>


### Knowledge, Instance

If a form within the Synapse data model has a specific time element (i.e., a single date/time value), the form typically represents **instance knowledge** - a single instance or occurrence of an object, relationship, or event. `inet:dns:request` and `inet:http:request` forms are examples of instance knowledge.

See [Instance Knowledge vs. Fused Knowledge](userguides/data_model.md#instance-fused) for a more detailed discussion.

## L

<a id="gloss-layer"></a>


### Layer

Within Synapse, a layer is the substrate that contains node data and where write permissions are enforced. This makes a layer both a storage boundary and a write permission boundary.

By default, a [Cortex](glossary.md#gloss-cortex) has a single layer and a single [view](glossary.md#gloss-view), meaning that by default all nodes are stored in one layer and all changes are written to that layer. However, multiple layers can be created for various purposes such as:

- separating data from different data sources (e.g., a read-only layer consisting of third-party data and associated tags can be created underneath a "working" layer, so that the third-party data is visible but cannot be modified);
- providing users with a personal "scratch space" where they can make changes in their layer without affecting the underlying main Cortex layer; or
- segregating data sets that should be visible/accessible to some users but not others.

Layers are closely related to views (see [View](glossary.md#gloss-view)). The order in which layers are instantiated within a view matters; in a multi-layer view, typically only the topmost layer is writable by that view's users, with subsequent (lower) layers read-only. Explicit actions can push upper-layer writes downward (merge) into lower layers.

<a id="gloss-leaf-tag"></a>


### Leaf Tag

See [Tag, Leaf](glossary.md#gloss-tag-leaf).

<a id="gloss-lift"></a>


### Lift

Within Synapse, one of the primary methods for interacting with data in a [Cortex](glossary.md#gloss-cortex). A lift is a read operation that selects a set of nodes from the Cortex. Compare with [Pivot](glossary.md#gloss-pivot), [Filter](glossary.md#gloss-filter), and [Traverse](glossary.md#gloss-traverse).

See [Storm Reference - Lifting](userguides/storm_ref_lift.md#storm-ref-lift) for additional detail.

<a id="gloss-light-edge"></a>


### Lightweight (Light) Edge

See [Edge, Lightweight (Light)](glossary.md#gloss-edge-light).

## M

<a id="gloss-macro"></a>


### Macro

A macro is a stored Storm query. Macros support the full range of Storm syntax and features.

See the Storm command reference for the [macro](userguides/storm_ref_cmd.md#storm-macro) command and the [Storm Reference - Automation](userguides/storm_ref_automation.md#storm-ref-automation) for additional detail.

<a id="gloss-merge"></a>


### Merge

Within Synapse, merge refers to the process of copying changes (additions, modifications, or deletions) made within a [fork](glossary.md#gloss-fork) to the fork's parent [view](glossary.md#gloss-view).

<a id="gloss-meta-prop"></a>


### Meta Property

See [Property, Meta](glossary.md#gloss-prop-meta).

<a id="gloss-model"></a>


### Model

Within Synapse, a system or systems used to represent data and/or assertions in a structured manner. A well-designed model allows efficient and meaningful exploration of the data to identify both known and potentially arbitrary or discoverable relationships.

<a id="gloss-model-analytical"></a>


### Model, Analytical

Within Synapse, the set of [tags](glossary.md#gloss-tag) representing analytical assessments or assertions that can be applied to objects in a [Cortex](glossary.md#gloss-cortex).

<a id="gloss-model-data"></a>


### Model, Data

Within Synapse, the set of [forms](glossary.md#gloss-form) that define the objects that can be represented in a [Cortex](glossary.md#gloss-cortex).

## N

<a id="gloss-ndef"></a>


### Ndef

Pronounced "en-deff". Short for **node definition.** A node's [form](glossary.md#gloss-form) and associated value (i.e., *\<form\> = \<valu\>* ) represented as comma-separated elements enclosed in parentheses: `(<form>,<valu>)`.

<a id="gloss-nid"></a>


### NID

Short for Node ID. Within Synapse, a NID is the integer identifier assigned to a node's [ndef](glossary.md#gloss-ndef) that uniquely identifies the node within a [Cortex](glossary.md#gloss-cortex).

A NID is assigned once, by the Cortex, and is shared by every [layer](glossary.md#gloss-layer); layers key their [storage node](glossary.md#gloss-node-storage) data by NID. A node that has not yet been persisted may not have a NID.

Contrast with [BUID](glossary.md#gloss-buid), which identified nodes prior to Synapse 3.0.0.

<a id="gloss-node"></a>


### Node

A node is a unique object within a [Cortex](glossary.md#gloss-cortex). Where a [form](glossary.md#gloss-form) is a template that defines the characteristics of a given object, a node is a specific instance of that type of object. For example, `inet:fqdn` is a form; `inet:fqdn=woot.com` is a node.

See [Nodes](userguides/data_model.md#data-node) in the [Data Model Objects](userguides/data_model.md#data-model-terms) document for additional detail.

<a id="gloss-node-action"></a>


### Node Action

In [Optic](glossary.md#gloss-optic), a saved, named Storm query or command (action) that can be executed via a right-click context menu option for specified forms (nodes).

<a id="gloss-node-data"></a>


### Node Data

Node data is a named set of structured metadata that may optionally be stored on a node in Synapse. Node data may be used for a variety of purposes. For example, a [Power-Up](glossary.md#gloss-power-up) may use node data to cache results returned by a third-party API along with the timestamp when the data was retrieved. If the same API is queried again for the same node within a specific time period, the Power-Up can use the cached node data instead of re-querying the API (helping to prevent using up any API query limits by re-querying the same data).

Node data can be accessed using the [node:data](stormtypes_prims.md#stormprims-node-data-f527) type.

<a id="gloss-node-def"></a>


### Node Definition

See [Ndef](glossary.md#gloss-ndef).

<a id="gloss-node-id"></a>


### Node ID

See [NID](glossary.md#gloss-nid).

<a id="gloss-node-runtime"></a>


### Node, Runtime

Runtime nodes (also known as "runt nodes" for short) are nodes that do not persist within a Cortex but are generated on demand when they are lifted. Because a runt node is constructed to answer the query that lifts it, it always reflects current state. Runt nodes are commonly used to represent metadata associated with Synapse, such as data model elements like forms (`syn:form`) and properties (`syn:prop`).

<a id="gloss-node-storage"></a>


### Node, Storage

A storage node ("sode") is a collection of data for a given node (i.e., the node's primary property, secondary / universal properties, tags, etc.) that is present in a specific [layer](glossary.md#gloss-layer).

<a id="gloss-yielder-func"></a>


### Node Yielder Function

See [Function, Node Yielder](glossary.md#gloss-func-yielder).

<a id="gloss-non-runtime-safe"></a>


### Non-Runtime Safe

See [Non-Runtsafe](glossary.md#gloss-non-runtsafe).

<a id="gloss-non-runtsafe"></a>


### Non-Runtsafe

Short for "non-runtime safe". Non-runtsafe refers to the use of variables within Storm. A variable that is **non-runtsafe** has a value that may change based on the specific node passing through the Storm pipeline. A variable whose value is set to a node property, such as `$fqdn = :fqdn` is an example of a non-runtsafe variable (i.e., the value of the secondary property `:fqdn` may be different for different nodes, so the value of the variable will be different based on the specific node being operated on).

Contrast with [Runtsafe](glossary.md#gloss-runtsafe).

## O

<a id="gloss-optic"></a>


### Optic

The Synapse user interface (UI), available as part of the commercial Synapse offering.

## P

<a id="gloss-package"></a>


### Package

A package is a set of commands and library code used to implement a [Storm Service](glossary.md#gloss-storm-svc). When a new Storm service is loaded into a Cortex, the Cortex verifies that the service is legitimate and then requests the single package the service provides, in order to load any extended Storm commands associated with the service and any library code used to implement the service.

<a id="gloss-parent-form"></a>


### Parent Form

See [Parent Form](glossary.md#gloss-form-parent).

<a id="gloss-path-var-col"></a>


### Path Variable Column

See [Column, Path Variable](glossary.md#gloss-col-path-var).

<a id="gloss-permission"></a>


### Permission

Within Synapse, a permission is a string (such as `node.add`) used to control access. A permission is assigned (granted or revoked) using a [rule](glossary.md#gloss-rule).

Access to some objects in Synapse may be controlled by [easy permissions](glossary.md#gloss-easy-perms).

<a id="gloss-pivot"></a>


### Pivot

Within Synapse, one of the primary methods for interacting with data in a [Cortex](glossary.md#gloss-cortex). A pivot moves from a set of nodes with one or more properties with specified value(s) to a set of nodes with a property having the same value(s). Compare with [Lift](glossary.md#gloss-lift), [Filter](glossary.md#gloss-filter), and [Traverse](glossary.md#gloss-traverse).

See [Storm Reference - Pivoting](userguides/storm_ref_pivot.md#storm-ref-pivot) for additional detail.

<a id="gloss-power-up"></a>


### Power-Up

Power-Ups provide specific add-on capabilities to Synapse. For example, Power-Ups may provide connectivity to external databases or third-party data sources, or enable functionality such as the ability to manage YARA rules, scans, and matches.

The term Power-Up is most commonly used to refer to Vertex-developed packages and services that are available as part of the commercial Synapse offering (only a few Power-Ups are available with open-source Synapse). However, many organizations write their own custom packages and services that may also be referred to as Power-Ups.

Vertex distinguishes between an [Advanced Power-Up](glossary.md#gloss-adv-power) and a [Rapid Power-Up](glossary.md#gloss-rapid-power).

<a id="gloss-power-adv"></a>


### Power-Up, Advanced

Advanced Power-Ups are implemented as Storm services (see [Service, Storm](glossary.md#gloss-svc-storm)). Vertex-developed Advanced Power-Ups are implemented as [Docker containers](https://www.docker.com/resources/what-container/) and may require DevOps support and additional resources to deploy.

<a id="gloss-power-rapid"></a>


### Power-Up, Rapid

Rapid Power-Ups are implemented as Storm packages (see [Package](glossary.md#gloss-package)). Rapid Power-Ups are written entirely in Storm and can be loaded directly into a [Cortex](glossary.md#gloss-cortex).

<a id="gloss-power-ups-tool"></a>


### Power-Ups Tool

See [Tool, Power-Ups](glossary.md#gloss-tool-power-ups).

<a id="gloss-primary-prop"></a>


### Primary Property

See [Property, Primary](glossary.md#gloss-prop-primary).

<a id="gloss-prop"></a>


### Property

Within Synapse, properties are individual elements that define a [form](glossary.md#gloss-form) or (along with their specific values) that comprise a [node](glossary.md#gloss-node). Every property in Synapse must have a defined [type](glossary.md#gloss-type).

See the [Property](userguides/data_model.md#data-prop) section in the [Data Model Objects](userguides/data_model.md#data-model-terms) document for additional detail.

<a id="gloss-prop-col"></a>


### Property Column

See [Column, Property](glossary.md#gloss-col-prop).

<a id="gloss-prop-computed"></a>


### Property, Computed

Within Synapse, a computed property is a secondary property that can be computed (e.g., extracted or derived) from a node's primary property. For example, the DNS A record `inet:dns:a=(woot.com, 1.2.3.4)` can be used to compute `inet:dns:a:fqdn=woot.com` and `inet:dns:a:ip=1.2.3.4`.

Synapse will automatically set ([Autoadd](glossary.md#gloss-autoadd)) any secondary properties that can be computed from a node's primary property. Because computed properties are based on primary property values, computed properties are always read-only (i.e., cannot be modified once set).

<a id="gloss-prop-extended"></a>


### Property, Extended

Within Synapse, an extended property is a custom property added to an existing form to capture specialized data. Extended properties can be added with the [stormlibs-lib-model-ext](stormtypes_libs.md#stormlibs-lib-model-ext) libraries.

See the section on [Extending the Data Model](userguides/data_model.md#data-model-extend) for details.

<a id="gloss-prop-meta"></a>


### Property, Meta

Within Synapse, a meta property is a [secondary property](glossary.md#gloss-secondary-prop) that is applicable to **all** forms. For example, `.created` is a meta property whose value is the date/time when the associated node was created in a Cortex.

<a id="gloss-prop-primary"></a>


### Property, Primary

Within Synapse, a primary property is the property that defines a given [form](glossary.md#gloss-form) in the data model. The primary property of a form must be defined such that the value of that property is unique across all possible instances of that form. Primary properties are always read-only (i.e., cannot be modified once set).

<a id="gloss-prop-relative"></a>


### Property, Relative

Within Synapse, a relative property is a [secondary property](glossary.md#gloss-secondary-prop) referenced using only the portion of the property's namespace that is relative to the form's [primary property](glossary.md#gloss-primary-prop). For example, `inet:dns:a:fqdn` is the full name of the "domain" secondary property of a DNS A record form (`inet:dns:a`). `:fqdn` is the relative property / relative property name for that same property.

<a id="gloss-prop-secondary"></a>


### Property, Secondary

Within Synapse, secondary properties are optional properties that provide additional detail about a [form](glossary.md#gloss-form). Within the data model, secondary properties may be defined with optional constraints, such as:

- Whether the property is read-only once set.
- Any normalization (outside of type-specific normalization) that should occur for the property (such as converting a string to all lowercase).

<a id="gloss-prop-virt"></a>


### Property, Virtual

A **virtual property** is a component of a property value (primary or secondary) that can be accessed "virtually" without being explicitly declared or set as an independent property. Virtual properties provide the flexibility to navigate (lift, filter, pivot) data in Synapse without the need to explicitly declare duplicative properties that may record conflicting values.

## Q

<a id="gloss-queue"></a>


### Queue

Within Synapse, a queue is a basic first-in, first-out (FIFO) data structure used to store and serve objects in a classic pub/sub (publish/subscribe) manner. Any primitive (such as a node nid) can be placed into a queue and then consumed from it. Queues can be used (for example) to support out-of-band processing by allowing non-critical tasks to be executed in the background. Queues are persistent; i.e., if a Cortex is restarted, the queue and any objects in the queue are retained.

## R

<a id="gloss-rapid-power"></a>


### Rapid Power-Up

See [Power-Up, Rapid](glossary.md#gloss-power-rapid).

<a id="gloss-relative-prop"></a>


### Relative Property

See [Property, Relative](glossary.md#gloss-prop-relative).

<a id="gloss-repr"></a>


### Repr

Short for "representation". The repr of a [property](glossary.md#gloss-prop) defines how the property should be displayed in cases where the display format differs from the storage format. For example, date/time values in Synapse are stored in epoch microseconds but are displayed in ISO 8601 "yyyy-mm-ddThh:mm:ss.mmmmmmZ" format.

<a id="gloss-research-tool"></a>


### Research Tool

See [Tool, Research](glossary.md#gloss-tool-research).

<a id="gloss-role"></a>


### Role

In Synapse, a role is used to group users with similar authorization needs. You can assign a set of rules (see [Rule](glossary.md#gloss-rule)) to a role, and grant the role to users who need to perform those actions.

<a id="gloss-root-tag"></a>


### Root Tag

See [Tag, Root](glossary.md#gloss-tag-root).

<a id="gloss-rule"></a>


### Rule

Within Synapse, a rule is a structure used to assign (grant or prohibit) a specific [permission](glossary.md#gloss-permission) (e.g., `node.tag` or `!view.del`). A rule is assigned to a [user](glossary.md#gloss-user) or a [role](glossary.md#gloss-role).

<a id="gloss-runtime-node"></a>


### Runtime Node

See [Node, Runtime](glossary.md#gloss-node-runtime).

<a id="gloss-runtime-safe"></a>


### Runtime Safe

See [Runtsafe](glossary.md#gloss-runtsafe).

<a id="gloss-runtsafe"></a>


### Runtsafe

Short for "runtime safe". Runtsafe refers to the use of variables within Storm. A variable that is **runtsafe** has a value that will not change based on the specific node passing through the Storm pipeline. A variable whose value is explicitly set, such as `$fqdn = woot.com` is an example of a runtsafe variable.

Contrast with [Non-Runtsafe](glossary.md#gloss-non-runtsafe).

## S

<a id="gloss-secondary-prop"></a>


### Secondary Property

See [Property, Secondary](glossary.md#gloss-prop-secondary).

<a id="gloss-service"></a>


### Service

Synapse is designed as a modular set of services. Broadly speaking, a service can be thought of as a container used to run an application. We may informally differentiate between a [Synapse Service](glossary.md#gloss-synapse-svc) and a [Storm Service](glossary.md#gloss-storm-svc).

<a id="gloss-svc-storm"></a>


### Service, Storm

A Storm service is a registerable remote component that provides a [package](glossary.md#gloss-package) and additional APIs to Storm and Storm commands. A service is identified by its cell type, which is unique for a deployment. A service resides on a [Telepath](glossary.md#gloss-telepath) API endpoint outside of the [Cortex](glossary.md#gloss-cortex).

When the Cortex is connected to a service, the Cortex queries the endpoint to determine if the service is legitimate and, if so, loads the package it provides to implement the service. In a mirrored deployment the leader retrieves the package and replicates it, so a mirror need not reach the service itself.

An advantage of Storm services (over, say, additional Python modules) is that services can be restarted to reload their service definitions and package while a Cortex is still running - thus allowing a service to be updated without having to restart the entire Cortex.

<a id="gloss-svc-synapse"></a>


### Service, Synapse

Synapse services make up the core Synapse architecture and include the [Cortex](glossary.md#gloss-cortex) (data store), [Axon](glossary.md#gloss-axon) (file storage), and the commercial [Optic](glossary.md#gloss-optic) UI. Synapse services are built on the [Cell](glossary.md#gloss-cell) object.

<a id="gloss-simple-form"></a>


### Simple Form

See [Form, Simple](glossary.md#gloss-form-simple).

<a id="gloss-slab"></a>


### Slab

A Slab is a core Synapse component which is used for persisting data on disk into an LMDB-backed database. The Slab interface offers an asyncio-friendly interface to LMDB objects, while allowing users to largely avoid having to handle native transactions themselves.

<a id="gloss-sode"></a>


### Sode

Short for "storage node". See [Node, Storage](glossary.md#gloss-node-storage).

<a id="gloss-spotlight-tool"></a>


### Spotlight Tool

See [Tool, Spotlight](glossary.md#gloss-tool-spotlight).

<a id="gloss-standard-comp-op"></a>


### Standard Comparison Operator

See [Comparison Operator, Standard](glossary.md#gloss-comp-op-standard).

<a id="gloss-storage-node"></a>


### Storage Node

See [Node, Storage](glossary.md#gloss-node-storage).

<a id="gloss-stories-tool"></a>


### Stories Tool

See [Tool, Stories](glossary.md#gloss-tool-stories).

<a id="gloss-storm"></a>


### Storm

Storm is the custom query language analysts use to interact with data in Synapse.

Storm can also be used as a programming language by advanced users and developers, though this level of expertise is not required for normal use. Many of Synapse's **Power-Ups** (see [Power-Up](glossary.md#gloss-power-up)) are written in Storm.

See [Storm Reference - Introduction](userguides/storm_ref_intro.md#storm-ref-intro) for additional detail.

<a id="gloss-storm-editor"></a>


### Storm Editor

Also "Storm Editor Tool". See [Tool, Storm Editor](glossary.md#gloss-tool-storm-editor).

<a id="gloss-storm-svc"></a>


### Storm Service

See [Service, Storm](glossary.md#gloss-svc-storm).

<a id="gloss-subquery"></a>


### Subquery

Within Synapse, a subquery is a [Storm](glossary.md#gloss-storm) query that is executed inside of another Storm query.

See [Storm Reference - Subqueries](userguides/storm_ref_subquery.md#storm-ref-subquery) for additional detail.

<a id="gloss-subquery-filter"></a>


### Subquery Filter

See [Filter, Subquery](glossary.md#gloss-filter-subquery).

<a id="gloss-synapse-svc"></a>


### Synapse Service

See [Service, Synapse](glossary.md#gloss-svc-synapse).

## T

<a id="gloss-tag"></a>


### Tag

Within Synapse, a tag is a label applied to a node that provides additional context. Tags may represent assessments about a node or can be used to group related nodes.

See the [Tag](userguides/data_model.md#data-tag) section in the [Data Model Objects](userguides/data_model.md#data-model-terms) document for additional detail.

<a id="gloss-tag-base"></a>


### Tag, Base

Within Synapse, the lowest (rightmost) tag element in a tag hierarchy. For example, for the tag `#foo.bar.baz`, `baz` is the base tag.

<a id="gloss-tag-leaf"></a>


### Tag, Leaf

The full tag path / longest tag in a given tag hierarchy. For example, for the tag `#foo.bar.baz`, `foo.bar.baz` is the leaf tag.

<a id="gloss-tag-root"></a>


### Tag, Root

Within Synapse, the highest (leftmost) tag element in a tag hierarchy. For example, for the tag `#foo.bar.baz`, `foo` is the root tag.

<a id="gloss-tag-col"></a>


### Tag Column

See [Column, Tag](glossary.md#gloss-col-tag).

<a id="gloss-tag-explorer"></a>


### Tag Explorer

In [Optic](glossary.md#gloss-optic), the Tag Explorer (found in the [Help Tool](glossary.md#gloss-help-tool)) provides an expandable, tree-based listing of all tags in your Synapse [Cortex](glossary.md#gloss-cortex), along with their definitions (if present).

<a id="gloss-tagglob-col"></a>


### Tag Glob Column

See [Column, Tag Glob](glossary.md#gloss-col-tagglob).

<a id="gloss-taxonomy"></a>


### Taxonomy

In Synapse, a taxonomy is a user-defined set of hierarchical categories that can optionally be used to further classify particular objects (forms). Taxonomies use a dotted namespace (similar to tags). Forms that support a taxonomy will have a secondary property whose [type](glossary.md#gloss-type) is the taxonomy for that form (e.g., an `ind:industry` form has a `:type` secondary property whose type is `ind:industry:type:taxonomy`).

<a id="gloss-telepath"></a>


### Telepath

Telepath is a lightweight remote procedure call (RPC) protocol used in Synapse. See [Telepath RPC](devguides/architecture.md#arch-telepath) in the [Synapse Architecture](devguides/architecture.md#dev_architecture) guide for additional detail.

<a id="gloss-tool-admin"></a>


### Tool, Admin

In [Optic](glossary.md#gloss-optic), the Admin Tool provides a unified interface to perform basic management of users, roles, and permissions; views and layers; and triggers and cron jobs.

<a id="gloss-tool-console"></a>


### Tool, Console

In [Optic](glossary.md#gloss-optic), the Console Tool provides a CLI-like interface to Synapse. It can be used to run Storm queries in a manner similar to the Storm CLI (in the community version of Synapse). In Optic the Console Tool is more commonly used to display status, error, warning, and debug messages, or to view help for built-in Storm commands (see [Storm Reference - Storm Commands](userguides/storm_ref_cmd.md#storm-ref-cmd)) and / or Storm commands installed by Power-Ups.

<a id="gloss-tool-help"></a>


### Tool, Help

In [Optic](glossary.md#gloss-optic), the central repository for Synapse documentation and assistance. The Help Tool includes the [Data Model Explorer](glossary.md#gloss-data-model-explorer), [Tag Explorer](glossary.md#gloss-tag-explorer), documentation for any installed Power-Ups (see [Power-Up](glossary.md#gloss-power-up)), links to the public Synapse, Storm, and Optic documents, and version / changelog information.

<a id="gloss-tool-ingest"></a>


### Tool, Ingest

In [Optic](glossary.md#gloss-optic), the primary tool used to load structured data in CSV, JSON, or JSONL format into Synapse using Storm. The Ingest Tool can also be used to prototype and test more formal ingest code.

<a id="gloss-tool-power-ups"></a>


### Tool, Power-Ups

In [Optic](glossary.md#gloss-optic), the tool used to view, install, update, and remove Power-Ups (see [Power-Up](glossary.md#gloss-power-up)).

<a id="gloss-tool-research"></a>


### Tool, Research

In [Optic](glossary.md#gloss-optic), the primary tool used to ingest, enrich, explore, visualize, and annotate Synapse data.

<a id="gloss-tool-spotlight"></a>


### Tool, Spotlight

Also known as simply "Spotlight". In [Optic](glossary.md#gloss-optic), a tool used to load and display PDF or HTML content, create an associated `doc:report` node, and easily extract and link relevant indicators or other nodes.

<a id="gloss-tool-stories"></a>


### Tool, Stories

Also known as simply "Stories". In [Optic](glossary.md#gloss-optic), a tool used to create, collaborate on, review, and publish finished reports. Stories allows you to integrate data directly from the [Research Tool](glossary.md#gloss-research-tool) into your report ("Story").

<a id="gloss-tool-storm-editor"></a>


### Tool, Storm Editor

Also known as simply "Storm Editor". In [Optic](glossary.md#gloss-optic), a tool used to compose, test, and store Storm queries (including macros - see [Macro](glossary.md#gloss-macro)). Storm Editor includes a number of integrated development environment (IDE) features, including syntax highlighting, auto-indenting, and auto-completion for the names of forms, properties, tags, and libraries.

<a id="gloss-tool-workflows"></a>


### Tool, Workflows

In [Optic](glossary.md#gloss-optic), the tool used to access and work with Workflows (see [Workflow](glossary.md#gloss-workflow)).

<a id="gloss-tool-workspaces"></a>


### Tool, Workspaces

In [Optic](glossary.md#gloss-optic), the tool used to configure and manage a user's Workspaces (see [Workspace](glossary.md#gloss-workspace)).

<a id="gloss-traverse"></a>


### Traverse

Within Synapse, one of the primary methods for interacting with data in a [Cortex](glossary.md#gloss-cortex). Traversal refers to navigating the data by crossing ("walking") a [lightweight (light) edge](glossary.md#gloss-edge-light) between nodes. Compare with [Lift](glossary.md#gloss-lift), [Pivot](glossary.md#gloss-pivot), and [Filter](glossary.md#gloss-filter).

See [Traversal Operations](userguides/storm_ref_pivot.md#storm-traverse) for additional detail.

<a id="gloss-trigger"></a>


### Trigger

Within Synapse, a trigger is a Storm query that is executed automatically upon the occurrence of a specified event within a Cortex (such as adding a node or applying a tag). "Trigger" refers collectively to the event and the query fired ("triggered") by the event.

See the Storm command reference for the [trigger](userguides/storm_ref_cmd.md#storm-trigger) command and the [Storm Reference - Automation](userguides/storm_ref_automation.md#storm-ref-automation) for additional detail.

<a id="gloss-type"></a>


### Type

Within Synapse, a type is the definition of a data element within the data model. A type describes what the element is and enforces how it should look, including how it should be normalized.

See the [Type](userguides/data_model.md#data-type) section in the [Data Model Objects](userguides/data_model.md#data-model-terms) document for additional detail.

<a id="gloss-type-base"></a>


### Type, Base

Within Synapse, base types include standard types such as integers and strings, as well as common types defined within or specific to Synapse, including globally unique identifiers (`guid`), date/time values (`time`), time intervals (`ival`), and tags (`syn:tag`). Many forms within the Synapse data model are built upon (extensions of) a subset of common types.

<a id="gloss-type-model"></a>


### Type, Model-Specific

Within Synapse, knowledge-domain-specific forms may themselves be specialized types. For example, an IP address (`inet:ip`) is its own specialized type. While an IP address is ultimately stored as a tuple of integers, the type has additional constraints, e.g., IP values must fall within the allowable IP address space.

<a id="gloss-type-aware"></a>


### Type Awareness

Type awareness is the feature of the [Storm](glossary.md#gloss-storm) query language that facilitates and simplifies navigation through the [hypergraph](glossary.md#gloss-hypergraph) when pivoting across nodes. Storm leverages knowledge of the Synapse [data model](glossary.md#gloss-data-model) (specifically knowledge of the type of each node property) to allow pivoting between primary and secondary properties of the same type across different nodes without the need to explicitly specify the properties involved in the pivot.

<a id="gloss-type-enforce"></a>


### Type Enforcement

Within Synapse, the process by which property values are required to conform to value and format constraints defined for that [type](glossary.md#gloss-type) within the data model before they can be set. Type enforcement helps to limit bad data being entered into a Cortex by ensuring values entered make sense for the specified data type (e.g., that an IP address cannot be set as the value of a property defined as a domain (`inet:fqdn`) type, and that the integer value of the IP falls within the allowable set of values for IP address space).

<a id="gloss-type-norm"></a>


### Type Normalization

Within Synapse, the process by which properties of a particular type are standardized and formatted in order to ensure consistency in the data model. Normalization may include processes such as converting user-friendly input into a different format for storage (e.g., converting an IP address entered in dotted-decimal notation to an integer), converting certain string-based values to all lowercase, and so on.

## U

<a id="gloss-user"></a>


### User

In Synapse, a user is represented by an account in the Cortex. An account is required to authenticate (log in) to the Cortex and is used for authorization (permissions) to access services and perform operations.

## V

<a id="gloss-variable"></a>


### Variable

In Storm, a variable is an identifier with a value that can be defined and/or changed during normal execution, i.e., the value is variable.

Contrast with [Constant](glossary.md#gloss-constant). See also [Runtsafe](glossary.md#gloss-runtsafe) and [Non-Runtsafe](glossary.md#gloss-non-runtsafe).

See [Storm Reference - Advanced - Variables](userguides/storm_adv_vars.md#storm-adv-vars) for a more detailed discussion of variables.

<a id="gloss-vault"></a>


### Vault

In Synapse, a vault is a protected storage mechanism that allows you to store secret values (such as API keys) and any associated configuration settings. Vaults support permissions and can be shared with other users or roles. Granting 'read' access to a vault allows someone to use the vault contents without allowing them to see the vault's secret values.

<a id="gloss-view"></a>


### View

Within Synapse, a view is an ordered set of layers (see [Layer](glossary.md#gloss-layer)) and associated permissions that are used to synthesize nodes from the [Cortex](glossary.md#gloss-cortex), determining both the nodes that are visible to users via that view and where (i.e., in what layer) any changes made by a view's users are recorded. A default Cortex consists of a single layer and a single view, meaning that by default all nodes are stored in one layer, all changes are written to that layer, and all users have the same visibility (view) into Synapse's data.

In multi-layer systems, a view consists of the set of layers that should be visible to users of that view, and the order in which the layers should be instantiated for that view. Order matters because typically only the topmost layer is writable by that view's users, with subsequent (lower) layers read-only. Explicit actions can push upper-layer writes downward (merge) into lower layers.

<a id="gloss-virt-prop"></a>


### Virtual Property

See [Property, Virtual](glossary.md#gloss-prop-virt).

## W

<a id="gloss-workflow"></a>


### Workflow

In [Optic](glossary.md#gloss-optic), a Workflow is a customized set of UI elements that provides an intuitive way to perform particular tasks. Workflows may be installed by Synapse Power-Ups (see [Power-Up](glossary.md#gloss-power-up)) and give users a more tailored means (compared to the [Research Tool](glossary.md#gloss-research-tool) or Storm query bar) to work with Power-Up Storm commands or associated analysis tasks.

<a id="gloss-workflows-tool"></a>


### Workflows Tool

See [Tool, Workflows](glossary.md#gloss-tool-workflows).

<a id="gloss-workspace"></a>


### Workspace

In [Optic](glossary.md#gloss-optic), a Workspace is a customizable user environment. Users may configure one or more Workspaces; different Workspaces may be designed to support different analysis tasks.

<a id="gloss-workspace-global"></a>


### Workspace, Global Default

In [Optic](glossary.md#gloss-optic), a Workspace that has been pre-configured with various custom settings and distributed for use. A Global Default Workspace can be used to share a set of baseline Workspace customizations with a particular group or team.

<a id="gloss-workspaces-tool"></a>


### Workspaces Tool

See [Tool, Workspaces](glossary.md#gloss-tool-workspaces).
