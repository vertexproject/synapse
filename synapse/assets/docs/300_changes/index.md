<a id="vtx_300_index"></a>
<a id="300_changes"></a>

# Synapse 3.0.0 Changes

These notes describe what changed between Synapse 2.x and Synapse 3.0.0 for people already familiar with Synapse 2.x. They are organized into topic-oriented pages grouped by audience: Storm authors, Cortex administrators, and DevOps / deployment, plus data model changes and a catch-all for breaking API changes.

## Highlights

For a high-level summary of the new user-facing features and functionality, start here.

- [Synapse 3.0.0 Feature Highlights](300changes.md)


## Guides

Cross-cutting guides for upgrading to and operating Synapse 3.0.0.

- [Synapse 3.0.0 Migration Guide](300migration.md)
- [Synapse 3.0.0 Breaking Changes](300breakingchanges.md)
- [Synapse 3.0.0 DevOps Guide](300devops.md)


## Storm

User-facing changes to the Storm query language: libraries, object access conventions, syntax/operators, virtual properties, tag matching, and the cron/trigger APIs.

- [Removed and Relocated Storm Libraries](storm-lib-removed.md)
- [New and Changed Storm Libraries](storm-lib-new.md)
- [Storm Object Access Conventions](storm-object-conventions.md)
- [Storm opts API Changes](storm-opts.md)
- [Storm Syntax and Operator Changes](storm-syntax-operators.md)
- [Virtual Properties in Storm](storm-virtual-properties-syntax.md)
- [Tag Glob Zero-Length Matching](storm-tag-glob-matching.md)
- [HTTP/Axon SSL Option Changes](storm-http-ssl-options.md)
- [Cron and Trigger API Changes](storm-cron-and-trigger-api.md)
- [Storm Macro Definition Changes](storm-macros.md)
- [Package description fields renamed to `desc`](storm-package-command-desc.md)
- [Package definitions reject unknown keys](storm-package-strict-keys.md)
- [Package definition `docs` key removed](storm-package-docs-removed.md)


## Data Model

Structural and form/property changes to the Synapse data model. A full, generated per-form/property reference lives in the data model documentation; these pages cover the high-traffic and breaking changes.

- [Merged inet:ipv4 / inet:ipv6 into inet:ip](datamodel-ip-unification.md)
- [Typed Property Values](datamodel-typed-values.md)
- [Interfaces and the alts Behavior](datamodel-interfaces.md)
- [Form Inheritance (Subforms)](datamodel-form-inheritance.md)
- [Virtual Properties (Model Mechanism)](datamodel-virtual-properties.md)
- [Microsecond Timestamps and ISO-8601 Repr](datamodel-timestamps.md)
- [Intervals and Timestamps](datamodel-intervals.md)
- [Extended Model Changes (Edges, Universal Props)](datamodel-extended-model.md)
- [Typed Name/Id Forms](datamodel-typed-names-ids.md)
- [Form and Property Renames](datamodel-form-renames.md)
- [Removed Forms](datamodel-removed-forms.md)
- [inet:service:\* Model Updates](datamodel-inet-service.md)
- [New Structural Forms](datamodel-new-structural-forms.md)
- [Geospatial lat/long and bbox Consistency](datamodel-gis-bbox.md)


## Administration

Changes that affect a Cortex administrator: runt nodes, core modules, permissions, cardinality tracking, and tombstones / forked-view deletes.

- [syn:cron and syn:trigger Runt Nodes Removed](admin-runt-nodes-removed.md)
- [Cortex Core Modules Removed](admin-core-modules-removed.md)
- [Permission Changes](admin-permissions.md)
- [Form/Property Counts and Cardinality Tracking](admin-counts-cardinality.md)
- [Tombstones and Forked-View Deletes](admin-tombstones.md)


## DevOps

Changes that affect deploying and operating Synapse services: storage format, the Nexus log, configuration, Telepath, feeds, layer synchronization, Python version, logging, and CLI tooling.

- [NID Layer Storage Format](devops-layer-storage-nid.md)
- [Deconflicted Node Edits in the Nexus Log](devops-nexus-deconfliction.md)
- [Removed and Changed Configuration Options](devops-storage-config-changes.md)
- [Synchronous Telepath Removed](devops-telepath-async-only.md)
- [Telepath Client Replaced by ClientV2](devops-telepath-clientv2.md)
- [Single Feed Data Format](devops-feed-single-format.md)
- [Layer upstream/mirror Removed (use push/pull)](devops-layer-sync-pushpull.md)
- [Minimum Python Version 3.14](devops-python-version.md)
- [Logging](devops-logging.md)
- [CLI Tool Changes (cmdr, cellauth, reorg)](devops-cli-tools.md)
- [AHA Service Discovery, Leadership, and Provisioning](devops-aha-service-discovery.md)
- [Automatic Service Provisioning (SYN_PROVISION_SECRET)](devops-service-provisioning.md)
- [Storm Service Single Package](devops-stormsvc-single-package.md)


## Miscellaneous / API

Breaking API changes for integrators that are not covered by the sections above.

- [Breaking API Changes for Integrators](misc-breaking-api.md)
- [HTTP API Endpoints Moved from /api/v1 to /api/v3](misc-http-api-v3.md)

