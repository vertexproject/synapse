*****************
Synapse Changelog
*****************

v0.2.0 - 2020-xx-xx
===================

Features and Enhancements
-------------------------
- This release includes significant storage optimizations that require a data migration.
  However, the 0.2.0 migration contains NO model migrations and is strictly limited to the internal
  LMDB layer storage format.  The new format provides performance enhancements that significantly
  improve data ingest performance and reduce the memory footprint of the layer.

- This release includes feature enhancments to the authorization subsystem to facilitate permissions
  on a per-view and per-layer basis.  Additionally, APIs and tools for manipulating the auth subsystem
  have been integrated into storm to allow user/role/rule editing from within storm queries.

Backward Compatibility Breaks
-----------------------------
- The splice message format has been optimized to be both smaller and to allow several atomic edits
  to be contained in one message.  This speeds up performance of the runtime, minimizes bandwidth,

- The cellauth command has been removed as a stand alone tool.  Users should now use
  the "auth" commands that are built into synapse.tools.cmdr or the commands / API built into the Storm
  runtime.  This change was partially needed due to breaking API changes that eliminate ambiguity between
  "user" manipulation APIs vs "role" manipulation APIs.

- FIXME add one liners and/or additional bullets here and visi will explain them :D

v0.1.X Changelog
================

For the Synapse 0.1.x changelog, see `01x Changelog`_ located in the v0.1.x documentation.

.. _01x Changelog: https://vertexprojectsynapse.readthedocs.io/en/01x/synapse/changelog.html
