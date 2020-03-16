*****************
Synapse Changelog
*****************

v0.2.0 - 2020-xx-xx
===================

Features and Enhancements
-------------------------
- This release includes significant storage optimizations that require a data migration.
  However, the 0.2.0 migration contains no *model* migrations and is strictly limited to the internal
  LMDB layer storage format.  The new format provides performance enhancements that significantly
  improve data ingest performance and reduce the memory footprint of the layer.

- This release includes feature enhancements to the authorization subsystem to facilitate permissions
  on a per-view and per-layer basis.

  FIXME:  words
- Mirroring is fully featured, robust to communication drops

- Spawn queries can run more things

- SYNDEV_OMIT_FINI_WARNS

- Provenance is disabled by default. Enable via SETTING

- Added new graph cmd options

Backward Compatibility Breaks
-----------------------------
- Pointer to migration process

- LMDB format changed

- The change message format has been optimized to be both smaller and to allow several atomic edits
  to be contained in one message.  This speeds up performance of the runtime, minimizes bandwidth,  The old change
  format is called "splice".  The new message format is called "NodeEdits".  (Option to emit either in cmdr)

- FIXME add one liners and/or additional bullets here and visi will explain them :D

- Removed sudo cmd

- Cortex map_async is now default

- Lots of remote API changes

- Old clients in synapse.tools can't talk to new (>=0.2.0) cortex.  New clients in synapse.tools can't talk to < 0.2.0 cortex.

- Remote layer removed

- Deprecation of lots of methods

- Removed cortex offset storage

- Removed splices to cryotank

- Removed pushing splices

- Removed feeds, feed loop

- Consolidated datamodel APIs

- Triggers/cron/queues have creators and each may have admins

- Removed #:score tagprop lift

- Removed insecure mode

- snap.model is now accessible at snap.core.model

- no default values anymore

- snap methods nodesby are now different

- auth.getUserByName now async (why?)

- user.admin -> user.isAdmin()

- node data and 'data' type must be json-serializable

v0.1.X Changelog
================

For the Synapse 0.1.x changelog, see `01x Changelog`_ located in the v0.1.x documentation.

.. _01x Changelog: https://vertexprojectsynapse.readthedocs.io/en/01x/synapse/changelog.html
