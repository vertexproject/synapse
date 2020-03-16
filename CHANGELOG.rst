*****************
Synapse Changelog
*****************

v0.2.0 - 2020-xx-xx
===================

Features and Enhancements
-------------------------

- Refactored Layer Storage Format

This release includes significant storage optimizations for both performance and size.  However, the `0.2.0` migration contains no *model* migrations and is strictly limited to the internal LMDB layer storage format.  The new format provides performance enhancements that significantly improve data ingest performance and reduce the memory footprint of the layer.  See :ref:`devops` for details on migrating your `0.1.x` Cortex to `0.2.0`.

- View/Layer Management

Views and layers may now be managed via simple storm commands or manipulated by the storm API.  Additionally, permissions may be assigned on a per-view or per-layer basis allowing granular control of users and roles.
With proper permission, a view may now be easily forked to create an analyst owned "sandbox" where their edits are written to a separate layer which can later be merged by someone with appropriate permissions.  A user
may now set a "default view" profile option to specify the view to be used when they issue a default storm query.

- Mirrors Are Now A Fully Operational Battle Station

Previous support for Cortex "mirrors" has been limited to mirroring data from a single layer.  The mechanism for change control and distribution within a Cortex has been updated to facilitate true mirroring of all changes within a Cortex.  Each change within a Cortex is assigned a sequential identifier which allows mirrors to be taken offline and catch-up once they are returned to operation.  Additionally, mirrors have been updated to facilitate "write-back" edits which propagate changes via their upstream mirror, making the mirror appear writable.  With this new mechanism, a set of mirrors may be configured to handle read offloading as well as write consolidation.

- Cron/Trigger Management

Cron jobs and triggers may now be managed via simple storm commands or manipulated by the storm API.  Additionally, permissions are now enforced on a per-object basis.

- Experimental Spawn Runtime Improvements

The (still experimental) ``spawn: True`` option to the storm runtime, which facilitates execution of a storm query in a sub-process, has made progress toward feature parity.  Specifically, a number of storm library APIs have been updated to facilitate access from within a spawned sub-process transparently.  While the spawn option is still considered experimental, it has reached a level of maturity which may warrant review due to the powerful performance benefit for large or long running read queries.

Backward Compatibility Breaks
-----------------------------

Modified Node Permission Names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What changed
    Node permissions were modified to allow all basic node edits to fall within a single hierarchy in order to facilitate easily granting permissions for all node edits.

    The following permission table provides translation:

    ============== ==============
    Old Permission New Permission
    ============== ==============
    node:add       node.add
    node:del       node.del
    prop:set       node.prop.set
    prop:del       node.prop.del
    tag:add        node.tag.add
    tag:del        node.tag.del
    ============== ==============

Why make the change
    By placing all node edit permissions under a single hierarchy, administrators may easily grant access to all node modifications by adding the permission ``node``.  As previously, more granular versions of the given permissions are available to individually control access.

What you need to do
    The Synpase ``0.2.x`` migration tool should take care of translating all relevant permissions changes within a migrated Cortex.  However, any 3rd party code that modifies permissions should be updated to the new naming convention.

Node Edits vs Splices
~~~~~~~~~~~~~~~~~~~~~

What changed
    The various splice events provided by the storm runtime have been consolidated and streamlined into a single ``node:edits`` event type.  The new ``node:edits`` events contain a more compressed and aggregated representation of node changes and include changes that were previous unreported.  Callers may now specify the format for the node edits reported by the storm runtime by using the ``editformat`` optional parameter to the storm runtime, but the default output will now be ``node:edits`` rather than splices.  The following table enumerates the options for the ``editformat`` parameter:

    ========== =========================================================
    editformat Storm runtime behavior
    ========== =========================================================
    nodeedits  Provide new ``node:edits`` events.
    splices    Provide ``0.1.x`` backward-compatible splice events.
    count      Provide ``node:edits:count`` events with simple counts.
    none       Do not transmit any representation for node edits.
    ========== =========================================================

Why make the change
    The splice format was originally designed to facilitate a single atomic edit per-splice.  As such, it required the potentially large primary property value to be embedded in each splice.  When making multiple edits, this representation is inefficient and causes the retransmission, and potential storage, of duplicate data.  Additionally, the key-value structure of the splice format provided unnecessary extensibility at the cost of transmission/storage size.

What you need to do
    Update any code that consumes/indexes the various splice events to handle the new ``node:edits`` format.  Additionally, callers may specify ``editformat: "splices"`` within their storm runtime options to enable backward compatible splice generation.

Removed Remote Layers
~~~~~~~~~~~~~~~~~~~~~

What changed
    Support for remote layers has been removed.

Why make the change
    The performance characteristics and stability of remote layers has never reached what we consider production deployable status.  Additionally, complexities with model versions, migrations, and model synchronization have made the use of remote layers highly fragile.  While we may eventually design a new remote layer capability, the current implementation is being removed due to being unsupportable.

What you need to do
    If you have remote layers deployed in production, you should update the view configuration to contain an "upstream" layer.  This will create a copy of the remote layer data to the local Cortex and keep it in sync.

Removed Pushing Splices
~~~~~~~~~~~~~~~~~~~~~~~

What changed
    The configuration options to enable pushing splices to a cryotank or to another cortex have been removed.

Why make the change
    The archival of splices to a cryotank and the responsibility of a Cortex to "push" changes to another Cortex have long been essentially vestigial.  Additionally, these options required a Cortex reboot to take effect and were not runtime configurable.  The current mechanisms for mirroring and upstream layers allow for a more scalable and dynamic configuration.

What you need to do
    It is unlikely that this change will effect any known deployments.

Removed Monolithic Feed Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What changed
    The monolithic configuration option for pulling "feed" data from a Cryotank has been removed.

Why make the change
    The ability to feed a Cortex directly from a Cryotank represents a very early approach to automate data ingest into a Cortex.  This capability has been superseded by Storm Services which provide a dynamically configurable way to integrate services and data.

What you need to do
    It is unlikely that this change will effect any known deployments.

Removed Tag Prop Lifting Without Tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What changed
    The ability to lift nodes by the presence of a tag property *without* specifying the tag name has been removed.  Given a tag property of "confidence", the ``#:confidence`` and ``#:confidence>90`` style syntax are no longer valid.  However, lifting by tag property *with* the tag, such as ``#foo.bar:confidence`` and ``#foo.bar:confidence>90`` remain valid.

Why make the change
    The necessary indexing to provide a performant way to lift nodes by the tag property without the tag is too expensive for the analytically dubious use case.

What you need to do
    Any instances of lifting nodes by tag property without the tag will need to be updated to include the tag name.

Removed Insecure Mode
~~~~~~~~~~~~~~~~~~~~~

What changed
    The "insecure" option in cell.yaml has been removed.

Why make the change
    Insecure mode of operation was a vestigial option originally designed to aid in bootstrapping and setting up initial admin users.  Telepath now allows for ``cell://`` and ``unix://`` connection schemes that can bypass authentication for local users making insecure mode unnecessary.  Additionally, it is currently possible to bootstrap a root password directly using command line arguments, environment variables, or configuration files.

What you need to do
    If you have services deployed in insecure mode, they will need to be transitioned to using proper authentication.

Removed Default Values From Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What changed
    Model properties may no longer have default values.

Why make the change
    The root reason for this change is a complex cascade of requirements which hinge on the simple concept of populating a default value.  In Synapse ``0.2.x``, nodes may be created and edited without lifting them.  This means that ingest speeds can be significantly increased by taking an "upsert" approach.  However, it also has the side effect of making it very difficult to know if a given node already has a value specified in another layer without lifting and fusing the node from all the properties in all the layers within the view.  Ultimately, by removing the expectation of default values for a given property, we have been able to allow the Cortex to create nodes without needing to lift them, creating a large performance benefit.

What you need to do
    If you have custom model elements that have default values, they will no longer be populated by default.  As a work around, you may create a trigger which populates the property when the node is added, but use caution when merging properties from multiple layers when populating defaults.

Additional Changes
------------------

- map_async is now enabled by default for all slabs
- Synapse tools may not be used to connect to services of a different minor version.
- Deprecated annotations added to APIs that will be removed in ``0.3.0``
- Removed sudo cmd
- Removed cortex offset storage
- SYNDEV_OMIT_FINI_WARNS was added to silence tear down warnings
- Provenance is disabled by default. Enable by setting ``provenance:en: True`` in ``cell.yaml``.

v0.1.X Changelog
================

For the Synapse 0.1.x changelog, see `01x Changelog`_ located in the v0.1.x documentation.

.. _01x Changelog: https://vertexprojectsynapse.readthedocs.io/en/01x/synapse/changelog.html
