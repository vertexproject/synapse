*****************
Synapse Changelog
*****************

v0.1.5 - TBD
===================

Features and Enhancements
-------------------------

- Make Ndef, Edge and TimeEdge repr implementations consistent. (`#1217 <https://github.com/vertexproject/synapse/pull/1217>`_)
- Add jsonl support the ``synapse.tools.feed`` tool. (`#1220 <https://github.com/vertexproject/synapse/pull/1220>`_)
- Add ``/api/v1/model`` API route for the Cortex HTTPAPI to expose the data model for a running Cortex. (`#1221 <https://github.com/vertexproject/synapse/pull/1221>`_)
- Add ``fire()`` function to Storm types to fire ``storm:fire`` messages during Storm command execution. (`#1221 <https://github.com/vertexproject/synapse/pull/1221>`_)
- Add ``$()`` expression syntax to Storm for mathematical operations, along with a new parsing engine built around Lark.  (`#1216 <https://github.com/vertexproject/synapse/pull/1216>`_)
- Add a warning when Synapse is imported if the user is running Python with ``-OO`` optimizations, since that can degrade the library capabilities. (`#1219 <https://github.com/vertexproject/synapse/pull/1219>`_)
- Cleanup some exception chains so that type normalization errors do not result in large tracebacks on the server. (`#1224 <https://github.com/vertexproject/synapse/pull/1224>`_)

Bugfixes
--------

- Fix an issue in Storm with lifting or filtering nodes by tags when the tag value is a variable. (`#1223 <https://github.com/vertexproject/synapse/pull/1223>`_)

Improved Documentation
----------------------

- Write awesome docs (`#XXX <https://github.com/vertexproject/synapse/pull/XXX>`_)


v0.1.4 - 2019-05-01
===================

Features and Enhancements
-------------------------

- Add POST support to the ``/api/v1/model/norm`` HTTP API endpoint. (`#1207 <https://github.com/vertexproject/synapse/pull/1207>`_)
- Add ``getPropNorm()`` and ``getTypeNorm()`` Telepath API endpoints to the Cortex and CoreApi. (`#1207 <https://github.com/vertexproject/synapse/pull/1207>`_)
- Add list ``length()`` and ``index()`` methods to Storm types. (`#1208 <https://github.com/vertexproject/synapse/pull/1208>`_)
- Add helper functions to ``synapse.lib.node`` for extracting repr values from packed nodes. (`#1212 <https://github.com/vertexproject/synapse/pull/1212>`_)
- Add ``--nodes-only`` to the Cmdr ``log`` command to only record raw nodes. (`#1213 <https://github.com/vertexproject/synapse/pull/1213>`_)
- Add ``guid()``, ``min()``, ``max()`` functions to Storm types.  (`#1215 <https://github.com/vertexproject/synapse/pull/1215>`_)
- Add ``getStormEval()`` to the ``synapse.lib.storm.Cmd`` class. This helper can be used by Storm command implementers in resolving variables, full property, and relative property values off of the Storm runtime.  (`#1215 <https://github.com/vertexproject/synapse/pull/1215>`_)
- The Storm ``min`` and ``max`` commands may now accept a relative property path, a full property path, or a variable.  (`#1215 <https://github.com/vertexproject/synapse/pull/1215>`_)
- Add a ``--mirror`` to ``synapse.servers.cortex`` to allow easier mirroring of a backup Cortex from its source Cortex.  (`#1197 <https://github.com/vertexproject/synapse/pull/1197>`_)

Bugfixes
--------

- Fix an error in PropPivotOut and FormPivot where a None object could be yielded in the Storm pipeline. (`#1210 <https://github.com/vertexproject/synapse/pull/1210>`_)
- Shut down HTTP API servers on Cell ``fini()``.  (`#1211 <https://github.com/vertexproject/synapse/pull/1211>`_)

Improved Documentation
----------------------

- Convert developer guide from static RST to Jupyter Notebook.  (`#1209 <https://github.com/vertexproject/synapse/pull/1209>`_)
- Convert HTTP API guide from static RST to Jupyter Notebook.  (`#1211 <https://github.com/vertexproject/synapse/pull/1211>`_)
- Add a note about backing up and restoring a cortex to the quickstart guide.  (`#1214 <https://github.com/vertexproject/synapse/pull/1214>`_)


v0.1.3 - 2019-04-17
===================

Features and Enhancements
-------------------------

- Add the ability to delete a role via HTTP API, as well as being able to mark a user as being archived. Archiving a user will also lock a user. (`#1205 <https://github.com/vertexproject/synapse/pull/1205>`_)
- Add support to archiving for user to the CellApi for use via Telepath. (`#1206 <https://github.com/vertexproject/synapse/pull/1206>`_)

Bugfixes
--------

- Fix remote layer bug injected by previous optimization that would result in missing nodes from lifts when the node
  only resides in the distant layer. (`#1203 <https://github.com/vertexproject/synapse/pull/1203>`_)

Improved Documentation
----------------------

- Fix error in the HTTP API documentation. (`#1204 <https://github.com/vertexproject/synapse/pull/1204>`_)


v0.1.2 - 2019-04-10
===================

Features and Enhancements
-------------------------

- Automatically run unit tests for the master every day. (`#1192 <https://github.com/vertexproject/synapse/pull/1192>`_)
- Add test suite for ``synapse.lib.urlhelp``. (`#1195 <https://github.com/vertexproject/synapse/pull/1195>`_)
- Improve multi-layer and single layer performance. This is a backwards-incompatible API change in that 0.1.2 cortex
  will not interoperate with 0.1.2 remote layers before version 0.1.2. Persistent storage format has not changed.
  (`#1196 <https://github.com/vertexproject/synapse/pull/1196>`_)
- Add skeleton for reverse engineering model. (`#1198 <https://github.com/vertexproject/synapse/pull/1198>`_)

Bugfixes
--------

- When using ``synapse.tools.cmdr``, issuing ctrl-c to cancel a running command in could result in the Telepath Proxy object being fini'd. This has been resolved by adding a signal handler to the ``synapse.lib.cli.Cli`` class which is registered by cmdr. (`#1199 <https://github.com/vertexproject/synapse/pull/1199>`_)
- Fix an issue where deleting a property which has no index failed. (`#1200 <https://github.com/vertexproject/synapse/pull/1200>`_)
- Single letter form and property names were improperly disallowed.  They are now allowed. (`#1201 <https://github.com/vertexproject/synapse/pull/1201>`_)


Improved Documentation
----------------------

- Add some example developer guide documentation. (`#1193 <https://github.com/vertexproject/synapse/pull/1193>`_)


v0.1.1 - 2019-04-03
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


v0.1.0 - 2019-03-19
===================

* Synapse version 0.1.0 released.
