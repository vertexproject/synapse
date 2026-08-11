<a id="vtx_300_index"></a>
<a id="300_changes"></a>


# Synapse 3.0.0 Changes

These notes describe what changed between Synapse 2.x and Synapse 3.0.0 for people already familiar with Synapse 2.x. They are organized into topic-oriented pages grouped by audience: Storm authors, Cortex administrators, and DevOps / deployment, plus data model changes and a catch-all for breaking API changes.

## Highlights

For a high-level summary of the new user-facing features and functionality, start here.

```mdtoc
300changes.md
```

## Guides

Cross-cutting guides for upgrading to and operating Synapse 3.0.0.

```mdtoc
300migration.md
300breakingchanges.md
300devops.md
```

## Storm

User-facing changes to the Storm query language: libraries, object access conventions, syntax/operators, virtual properties, tag matching, and the cron/trigger APIs.

```mdtoc
storm-lib-removed.md
storm-lib-new.md
storm-object-conventions.md
storm-opts.md
storm-syntax-operators.md
storm-virtual-properties-syntax.md
storm-tag-glob-matching.md
storm-http-ssl-options.md
storm-cron-and-trigger-api.md
storm-macros.md
storm-package-command-desc.md
storm-package-strict-keys.md
storm-package-docs-removed.md
```

## Data Model

Structural and form/property changes to the Synapse data model. A full, generated per-form/property reference lives in the data model documentation; these pages cover the high-traffic and breaking changes.

```mdtoc
datamodel-ip-unification.md
datamodel-typed-values.md
datamodel-interfaces.md
datamodel-form-inheritance.md
datamodel-virtual-properties.md
datamodel-timestamps.md
datamodel-intervals.md
datamodel-extended-model.md
datamodel-typed-names-ids.md
datamodel-form-renames.md
datamodel-removed-forms.md
datamodel-inet-service.md
datamodel-new-structural-forms.md
datamodel-gis-bbox.md
```

## Administration

Changes that affect a Cortex administrator: runt nodes, core modules, permissions, cardinality tracking, and tombstones / forked-view deletes.

```mdtoc
admin-runt-nodes-removed.md
admin-core-modules-removed.md
admin-permissions.md
admin-counts-cardinality.md
admin-tombstones.md
```

## DevOps

Changes that affect deploying and operating Synapse services: storage format, the Nexus log, configuration, Telepath, feeds, layer synchronization, Python version, logging, and CLI tooling.

```mdtoc
devops-layer-storage-nid.md
devops-nexus-deconfliction.md
devops-storage-config-changes.md
devops-telepath-async-only.md
devops-telepath-clientv2.md
devops-feed-single-format.md
devops-layer-sync-pushpull.md
devops-python-version.md
devops-logging.md
devops-cli-tools.md
devops-aha-service-discovery.md
devops-service-provisioning.md
devops-stormsvc-single-package.md
```

## Miscellaneous / API

Breaking API changes for integrators that are not covered by the sections above.

```mdtoc
misc-breaking-api.md
misc-http-api-v3.md
```
