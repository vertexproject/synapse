.. _vtx_300_index:
.. _300_changes:

Synapse 3.0.0 Changes
=====================

These notes describe what changed between Synapse 2.x and Synapse 3.0.0 for people already
familiar with Synapse 2.x. They are organized into topic-oriented pages grouped by audience:
Storm authors, Cortex administrators, and DevOps / deployment, plus data model changes and a
catch-all for breaking API changes.

Highlights
----------

For a high-level summary of the new user-facing features and functionality, start here.

.. toctree::
    :maxdepth: 1

    300changes

Guides
------

Cross-cutting guides for upgrading to and operating Synapse 3.0.0.

.. toctree::
    :maxdepth: 1

    300migration
    300breakingchanges
    300devops

Storm
-----

User-facing changes to the Storm query language: libraries, object access conventions,
syntax/operators, virtual properties, tag matching, and the cron/trigger APIs.

.. toctree::
    :maxdepth: 1

    storm-lib-removed
    storm-lib-new
    storm-object-conventions
    storm-opts
    storm-syntax-operators
    storm-virtual-properties-syntax
    storm-tag-glob-matching
    storm-http-ssl-options
    storm-cron-and-trigger-api
    storm-macros

Data Model
----------

Structural and form/property changes to the Synapse data model. A full, generated
per-form/property reference lives in the data model documentation; these pages cover the
high-traffic and breaking changes.

.. toctree::
    :maxdepth: 1

    datamodel-ip-unification
    datamodel-typed-values
    datamodel-interfaces
    datamodel-form-inheritance
    datamodel-virtual-properties
    datamodel-timestamps
    datamodel-intervals
    datamodel-extended-model
    datamodel-typed-names-ids
    datamodel-form-renames
    datamodel-removed-forms
    datamodel-inet-service
    datamodel-new-structural-forms
    datamodel-gis-bbox

Administration
--------------

Changes that affect a Cortex administrator: runt nodes, core modules, permissions,
cardinality tracking, and tombstones / forked-view deletes.

.. toctree::
    :maxdepth: 1

    admin-runt-nodes-removed
    admin-core-modules-removed
    admin-permissions
    admin-counts-cardinality
    admin-tombstones

DevOps
------

Changes that affect deploying and operating Synapse services: storage format, the Nexus
log, configuration, Telepath, feeds, layer synchronization, Python version, logging,
and CLI tooling.

.. toctree::
    :maxdepth: 1

    devops-layer-storage-nid
    devops-nexus-deconfliction
    devops-storage-config-changes
    devops-telepath-async-only
    devops-feed-single-format
    devops-layer-sync-pushpull
    devops-python-version
    devops-logging
    devops-cli-tools
    devops-aha-service-discovery
    devops-service-provisioning

Miscellaneous / API
-------------------

Breaking API changes for integrators that are not covered by the sections above.

.. toctree::
    :maxdepth: 1

    misc-breaking-api
    misc-http-api-v3
