Storm Reference - Lift Operators
================================

The operators below can be used to retrieve a set of nodes from a Synapse hypergraph based on a set of specified criteria.

All of these operators are defined in storm.py_.

See the `Storm Syntax Conventions`__ for an explanation of the usage format used below.

Where specific query examples are given, they are commonly provided in pairs using operator syntax followed by the equivalent macro syntax (if available).

lift()
------

Lifts (retrieves) a set of nodes from a Cortex based on specified criteria.

Optional parameters:

* **"by" handler:** a "by" handler is a modifier that limits the lift criteria in various ways (e.g., "lift by <thing>"). Use of a "by" handler is similar to performing a filter_ operation concurrent with lifting instead of after lifting.

  * ``by=`` (operator syntax)
  * ``*`` (macro syntax)
  
  "By" handlers have specific use cases and are documented <<separately>>.

* **Return limit:** specify the maximum number of nodes to be returned by the lift query.

  * ``limit=`` (operator syntax)
  * ``^`` (macro syntax)
  
Lift operations are highly flexible. Only basic examples of ``lift()`` usage are provided here. See the section on `by handlers`__ for specialized lift operations using the "by" parameter.




guid()
------
Todo

alltag()
--------
Todo

.. _storm.py: https://github.com/vertexproject/synapse/blob/master/synapse/lib/storm.py

.. _conventions: ../userguides/ug011_storm_basics.html#syntax-conventions
__ conventions_

.. _filter: ../userguides/ug014_storm_ref_filter.rst

.. _handlers: ../userguides/ug016_storm_ref_byhandlers.rst
__ handlers_
