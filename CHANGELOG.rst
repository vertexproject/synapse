*****************
Synapse Changelog
*****************


v0.1.2 - TBD
===================

Features and Enhancements
-------------------------

- Automatically run unit tests for the master every day. (`#1192 <https://github.com/vertexproject/synapse/pull/1192>`_)

Bugfixes
--------

- Fix old bugs (`#XXX <https://github.com/vertexproject/synapse/pull/XXX>`_)

Improved Documentation
----------------------

- Add some example developer guide documentation. (`#1193 <https://github.com/vertexproject/synapse/pull/1193>`_)


v0.1.1 - 2018-04-03
===================


Features and Enhancements
-------------------------

- Allow ``synapse.servers`` tools to specify a custom Telepath share name. (`#1170 <https://github.com/vertexproject/synapse/pull/1170>`_)
- Add ``$lib.print()``, ``$lib.len()``, ``$lib.min()``, ``$lib.max()``, and ``$lib.dict()`` Storm library functions. (`#1179 <https://github.com/vertexproject/synapse/pull/1179>`_)
- Add ``$lib.str.concat()`` and ``$lib.str.format()`` Storm library functions. (`#1179 <https://github.com/vertexproject/synapse/pull/1179>`_)
- Initial economic model for tracking purchases. (`#1177 <https://github.com/vertexproject/synapse/pull/1177>`_)
- Add progress logging for the ``(0, 1, 0)`` layer migration. (`#1180 <https://github.com/vertexproject/synapse/pull/1180>`_)
- Remove references to ``Cortex.layer`` as a Cortex level attribute. There was no guarantee that this was the correct write layer for a arbitrary view and could lead to incorrect usage. (`#1181 <https://github.com/vertexproject/synapse/pull/1181>`_)
- Optimize the ``snap.getNodesBy()`` API to shortcut true equality lift operations to become pure lifts by buid. (`#1183 <https://github.com/vertexproject/synapse/pull/1183>`_)
- Add a generic Cell server, ``synapse.servers.cell`` that can be used to launch any Cell by python class path and file path.  This can be used to launch custom Cell objects. (`#1182 <https://github.com/vertexproject/synapse/pull/1182>`_)
- Add server side remote event processing to ``.storm()`` API calls. (`#1171 <https://github.com/vertexproject/synapse/pull/1171>`_)
- Add Telepath user proxying. (`#1171 <https://github.com/vertexproject/synapse/pull/1171>`_)
- Migrate Dockerhub docker container builds and pypi packaging and release processes to CircleCI. (`#1185 <https://github.com/vertexproject/synapse/pull/1185>`_)
- Improve performance.  Add a small layer-level cache.  Replace home-grown `synapse.lib.cache.memoize` implementation with standard one.  Make layer microoptimizations. (`#1191 <https://github.com/vertexproject/synapse/pull/1191>`_)

Bugfixes
--------

- Fixes for lmdblab.dropdb and lmdbslab.initdb mapfull safety. (`#1174 <https://github.com/vertexproject/synapse/pull/1174>`_)
- Graceful recovery for pre v0.1.0 database migrations for lmdbslab backed databases. (`#1175 <https://github.com/vertexproject/synapse/pull/1175>`_)
- Syntax parser did not allow for multiple dot hierarchies in universal properties. (`#1178 <https://github.com/vertexproject/synapse/pull/1178>`_)
- Fix for lmdbslab mapfull error during shutdown (`#1184 <https://github.com/vertexproject/synapse/pull/1184>`_)
- ``synapse.lib.reflect.getShareInfo()`` could return incorrect data depending on execution order and object type inheritance. (`#1186 <https://github.com/vertexproject/synapse/pull/1186>`_)
- Add missing test for Str types extracting named regular expression matches as subs. (`#1187 <https://github.com/vertexproject/synapse/pull/1187>`_)

Improved Documentation
----------------------

- Minor documentation updates for permissions. (`#1172 <https://github.com/vertexproject/synapse/pull/1172>`_)
- Added docstring and test for ``synapse.lib.coro.executor()``. (`#1189 <https://github.com/vertexproject/synapse/pull/1189>`_)


v0.1.0 - 2018-03-19
===================

* Synapse version 0.1.0 released.
