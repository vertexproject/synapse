.. vim: set textwidth=79

*****************
Synapse Changelog
*****************


v2.46.0 - 2021-07-02
====================

Features and Enhancements
-------------------------
- Update the Cortex ``storm:log:level`` configuration value to accept string
  values such as ``DEBUG``, ``INFO``, etc. The default log level for Storm
  query logs is now ``INFO`` level.
  (`#2262 <https://github.com/vertexproject/synapse/pull/2262>`_)
- Add ``$lib.regex.findall()`` Stormtypes API to find all matching parts of a
  regular expression in a given string.
  (`#2265 <https://github.com/vertexproject/synapse/pull/2265>`_)
- Add ``$lib.inet.http.head()`` Stormtypes API to perform easy HEAD requests,
  and ``allow_redirects`` arguments to existing ``lib.inet.http`` APIs to
  allow controlling the redirect behavior.
  (`#2268 <https://github.com/vertexproject/synapse/pull/2268>`_)
- Add ``$lib.storm.eval()`` API to evaluate Storm values from strings.
  (`#2269 <https://github.com/vertexproject/synapse/pull/2269>`_)
- Add ``getSystemInfo()`` and ``getBackupInfo()`` APIS to the Cell for getting
  useful system information.
  (`#2267 <https://github.com/vertexproject/synapse/pull/2267>`_)
- Allow lists in rstorm bodies.
  (`#2261 <https://github.com/vertexproject/synapse/pull/2261>`_)
- Add a ``:desc`` secondary property to the ``proj:sprint`` form.
  (`#2261 <https://github.com/vertexproject/synapse/pull/2261>`_)
- Call _normStormPkg in all loadStormPkg paths, move validation to post
  normalization and remove mutation in validator
  (`#2260 <https://github.com/vertexproject/synapse/pull/2260>`_)
- Add ``SYN_SLAB_COMMIT_PERIOD`` environment variable to control the Synapse
  slab commit period. Add ``layer:lmdb:max_replay_log`` Cortex option to
  control the slab replay log size.
  (`#2266 <https://github.com/vertexproject/synapse/pull/2266>`_)
- Update Ahacell log messages.
  (`#2270 <https://github.com/vertexproject/synapse/pull/2270>`_)

Bugfixes
--------
- Fix an issue where the ``Trigger.pack()`` method failed when the user that
  created the trigger had been deleted.
  (`#2263 <https://github.com/vertexproject/synapse/pull/2263>`_)

Improved Documentation
----------------------
- Update the Cortex devops documentation for the Cortex to document the Storm
  query logging. Update the Cell devops documentation to explain the Cell
  logging and how to enable structured (JSON) logging output.
  (`#2262 <https://github.com/vertexproject/synapse/pull/2262>`_)
- Update Stormtypes API documentation for ``bool``, ``storm:project:epic``,
  ``storm:project:epics``, ``storm:project:ticket``,
  ``storm:project:tickets``, ``storm:project:sprint``,
  ``storm:project:sprints``, ``storm:project``, ``storm:stix:bundle`` types.
  (`#2261 <https://github.com/vertexproject/synapse/pull/2261>`_)


v2.45.0 - 2021-06-25
====================

Features and Enhancements
-------------------------
- Add a application level process pool the base Cell implemenation. Move the
  processing of Storm query text into the process pool.
  (`#2250 <https://github.com/vertexproject/synapse/pull/2250>`_)
  (`#2259 <https://github.com/vertexproject/synapse/pull/2259>`_)
- Minimize the re-validation of Storm code on Cortex boot.
  (`#2257 <https://github.com/vertexproject/synapse/pull/2257>`_)
- Add the ``ou:preso`` form to record conferences and presentations. Add a
  ``status`` secondary property to the ``it:mitre:attack:technique`` form to
  track if techniques are current, deprecated or withdrawn.
  (`#2254 <https://github.com/vertexproject/synapse/pull/2254>`_)

Bugfixes
--------
- Remove incorrect use of ``cmdopts`` in Storm command definitions unit tests.
  (`#2258 <https://github.com/vertexproject/synapse/pull/2258>`_


v2.44.0 - 2021-06-23
====================

This release contains an automatic data migration that may cause additional
startup time on the first boot. This only applies to a Cortex that is using
user defined tag properties or using ``ps:person:name`` properties.
Deployments with startup or liveliness probes should have those disabled while
this upgrade is performed to prevent accidental termination of the Cortex
process. Please ensure you have a tested backup available before applying this
update.

Features and Enhancements
-------------------------
- Add a ``.move()`` method on Stormtypes ``storm:trigger`` objects to allow
  moving a Trigger from one View to another View.
  (`#2252 <https://github.com/vertexproject/synapse/pull/2252>`_)
- When the Aha service marks a service as down, log why that service is being
  marked as such.
  (`#2255 <https://github.com/vertexproject/synapse/pull/2255>`_)
- Add ``:budget:price`` property to the ``ou:contract`` form. Add ``:settled``
  property to the ``econ:purchase`` form.
  (`#2253 <https://github.com/vertexproject/synapse/pull/2253>`_

Bugfixes
--------
- Make the array property ``ps:person:names`` a unique array property.
  (`#2253 <https://github.com/vertexproject/synapse/pull/2253>`_
- Add missing tagprop key migration for the bybuidv3 index.
  (`#2256 <https://github.com/vertexproject/synapse/pull/2256>`_)


v2.43.0 - 2021-06-21
====================

Features and Enhancements
-------------------------
- Add a ``.type`` string to the Stormtypes ``storm:auth:gate`` object to
  allow a user to identify the type of auth gate it is.
  (`#2238 <https://github.com/vertexproject/synapse/pull/2238>`_)
- Add ``$lib.user.iden`` reference to the Stormtype ``$lib.user`` to get the
  iden of the current user executing Storm code.
  (`#2236 <https://github.com/vertexproject/synapse/pull/2236>`_)
- Add a ``--no-build`` option to ``synapse.tools.genpkg`` to allow pushing an
  a complete Storm Package file.
  (`#2231 <https://github.com/vertexproject/synapse/pull/2231>`_)
  (`#2232 <https://github.com/vertexproject/synapse/pull/2232>`_)
  (`#2233 <https://github.com/vertexproject/synapse/pull/2233>`_)
- The Storm ``movetag`` command now checks for cycles when setting the
  ``syn:tag:isnow`` property.
  (`#2229 <https://github.com/vertexproject/synapse/pull/2229>`_)
- Deprecate the ``ou:org:has`` form, in favor of using light edges for
  storing those relationships.
  (`#2234 <https://github.com/vertexproject/synapse/pull/2234>`_)
- Add a ``description`` property to the ``ou:industry`` form.
  (`#2239 <https://github.com/vertexproject/synapse/pull/2239>`_)
- Add a ``--name`` parameter to the Storm ``trigger.add`` command to name
  triggers upon creation.
  (`#2237 <https://github.com/vertexproject/synapse/pull/2237>`_)
- Add ``regx`` to the ``BadTypeValu`` exception of the ``str`` type when
  a regular expression fails to match.
  (`#2240 <https://github.com/vertexproject/synapse/pull/2240>`_)
- Consolidate Storm parsers to a single Parser object to improve startup time.
  (`#2247 <https://github.com/vertexproject/synapse/pull/2247>`_)
- Improve error logging in the Cortex ``callStorm()`` and ``storm()`` APIs.
  (`#2243 <https://github.com/vertexproject/synapse/pull/2243>`_)
- Add ``from:contract``, ``to:contract``, and ``memo`` properties to the
  ``econ:acct:payment`` form.
  (`#2248 <https://github.com/vertexproject/synapse/pull/2248>`_)
- Improve the Cell backup streaming APIs link cleanup.
  (`#2249 <https://github.com/vertexproject/synapse/pull/2249>`_)

Bugfixes
--------
- Fix issue with grabbing the incorrect Telepath link when performing a Cell
  backup.
  (`#2246 <https://github.com/vertexproject/synapse/pull/2246>`_)
- Fix missing ``toprim`` calls in ``$lib.inet.http.connect()``.
  (`#2235 <https://github.com/vertexproject/synapse/pull/2235>`_)
- Fix missing Storm command form hint schema from the Storm Package schema.
  (`#2242 <https://github.com/vertexproject/synapse/pull/2242>`_)

Improved Documentation
----------------------
- Add documentation for deprecated model forms and properties, along with
  modeling alternatives.
  (`#2234 <https://github.com/vertexproject/synapse/pull/2234>`_)
- Update documentation for the Storm ``help`` command to add examples of
  command substring matching.
  (`#2241 <https://github.com/vertexproject/synapse/pull/2241>`_)

v2.42.2 - 2021-06-11
====================

Bugfixes
--------
- Protect against a few possible RuntimeErrors due to dictionary sizes
  changing during iteration.
  (`#2227 <https://github.com/vertexproject/synapse/pull/2227>`_)
- Fix StormType ``Lib`` lookups with imported modules which were raising
  a ``TypeError`` instead of a ``NoSuchName`` error.
  (`#2228 <https://github.com/vertexproject/synapse/pull/2228>`_)
- Drop old Storm Packages if they are present when re-adding them. This fixes
  an issue with runtime updates leaving old commands in the Cortex.
  (`#2230 <https://github.com/vertexproject/synapse/pull/2230>`_)


v2.42.1 - 2021-06-09
====================

Features and Enhancements
-------------------------
- Add a ``--no-docs`` option to the  ``synapse.tools.genpkg`` tool. When used,
  this not embed inline documentation into the generated Storm packages.
  (`#2226 <https://github.com/vertexproject/synapse/pull/2226>`_)


v2.42.0 - 2021-06-03
====================

Features and Enhancements
-------------------------
- Add a ``--headers`` and ``--parameters`` arguments to the Storm ``wget``
  command. The default headers now includes a browser like UA string.
  (`#2208 <https://github.com/vertexproject/synapse/pull/2208>`_)
- Add the ability to modify the name of a role via Storm.
  (`#2222 <https://github.com/vertexproject/synapse/pull/2222>`_)

Bugfixes
--------
- Fix an issue in the JsonStor cell where there were missing fini calls.
  (`#2223 <https://github.com/vertexproject/synapse/pull/2223>`_)
- Add a missing timeout to an ``getAhaSvc()`` call.
  (`#2224 <https://github.com/vertexproject/synapse/pull/2224>`_)
- Change how tagprops are serialized to avoid a issue with sending packed
  nodes over HTTP APIs. This changes the packed node structure of tagprops
  from a dictionary keyed with ``(tagname, propertyname)`` to a dictionary
  keyed off of the ``tagname``, which now points to a dictionary containing
  the ``propertyname`` which represents the value of the tagprop.
  (`#2221` <https://github.com/vertexproject/synapse/pull/2221>`_)


v2.41.1 - 2021-05-27
====================

Bugfixes
--------
- Add PR #2217 to bugfix list in CHANGLOG.rst for v2.41.0 :D

v2.41.0 - 2021-05-27
====================

Features and Enhancements
-------------------------
- Add an ``it:cmd`` form and update the ``it:exec:proc:cmd`` property to
  use it. This release includes an automatic data migration on startup to
  update the ``it:exec:proc:cmd`` on any existing ``it:exec:proc`` nodes.
  (`#2219 <https://github.com/vertexproject/synapse/pull/2219>`_)

Bugfixes
--------
- Fix an issue where passing a Base object to a sub-runtime in Storm
  did not correctly increase the reference count.
  (`#2216 <https://github.com/vertexproject/synapse/pull/2216>`_)
- Fix an issue where the ``tee`` command could potentially run the
  specified queries twice.
  (`#2218 <https://github.com/vertexproject/synapse/pull/2218>`_)
- Fix for rstorm using mock when the HTTP body is bytes.
  (`#2217 <https://github.com/vertexproject/synapse/pull/2217>`_)

v2.40.0 - 2021-05-26
====================

Features and Enhancements
-------------------------
- Add a ``--parallel`` switch to the ``tee`` Storm command. This allows for
  all of the Storm queries provided to the ``tee`` command to execute in
  parallel, potentially producing a mixed output stream of nodes.
  (`#2209 <https://github.com/vertexproject/synapse/pull/2209>`_)
- Convert the Storm Runtime object in a Base object, allowing for reference
  counted Storm variables which are made from Base objects and are properly
  torn down.
  (`#2203 <https://github.com/vertexproject/synapse/pull/2203>`_)
- Add ``$lib.inet.http.connect()`` method which creates a Websocket object
  inside of Storm, allowing a user to send and receive messages over a
  websocket.
  (`#2203 <https://github.com/vertexproject/synapse/pull/2203>`_)
- Support pivot join operations on tags.
  (`#2213 <https://github.com/vertexproject/synapse/pull/2213>`_)
- Add ``stormrepr()`` implementation for ``synapse.lib.stormtypes.Lib``, which
  allows for ``$lib.print()`` to display useful strings for Storm Libraries
  and imported modules.
  (`#2212 <https://github.com/vertexproject/synapse/pull/2212>`_)
- Add a storm API top updated a user name.
  (`#2214 <https://github.com/vertexproject/synapse/pull/2214>`_)

Bugfixes
--------
- Fix the logger name for ``synapse.lib.aha``.
  (`#2210 <https://github.com/vertexproject/synapse/pull/2210>`_)
- Log ``ImportError`` exceptions in ``synapse.lib.dyndeps.getDynMod``. This
  allows easier debugging when using the ``synapse.servers.cell`` server when
  running custom Cell implementations.
  (`#2211 <https://github.com/vertexproject/synapse/pull/2211>`_)
- Fix an issue where a Storm command which failed to set command arguments
  successfully would not teardown the Storm runtime.
  (`#2212 <https://github.com/vertexproject/synapse/pull/2212>`_)

v2.39.1 - 2021-05-21
====================

Bugfixes
--------
- Fix an issue with referencing the Telepath user session object prior to a
  valid user being set.
  (`#2207 <https://github.com/vertexproject/synapse/pull/2207>`_)


v2.39.0 - 2021-05-20
====================

Features and Enhancements
-------------------------

- Add more useful output to Storm when printing heavy objects with
  ``$lib.print()``.
  (`#2185 <https://github.com/vertexproject/synapse/pull/2185>`_)
- Check rule edits for roles against provided authgates in Storm.
  (`#2199 <https://github.com/vertexproject/synapse/pull/2199>`_)
- Add ``Str.rsplit()`` and maxsplit arguments to ``split()/rsplit()`` APIs
  in Storm.
  (`#2200 <https://github.com/vertexproject/synapse/pull/2200>`_)
- Add default argument values to the output of Storm command help output.
  (`#2198 <https://github.com/vertexproject/synapse/pull/2198>`_)
- Add a ``syn:tag:part`` Type and allow the ``syn:tag`` type to normalize a
  list of tag parts to create a tag string. This is intended to be used with
  the ``$lib.cast()`` function in Storm.
  (`#2192 <https://github.com/vertexproject/synapse/pull/2192>`_)
- Add debug logging to the Axon for reading, writing, or deleting of blobs.
  (`#2202 <https://github.com/vertexproject/synapse/pull/2202>`_)
- Add a timeout argument to the ``$lib.inet.http`` functions. The functions
  will all now always return a ``storm:http:resp`` object; if the ``.code``
  is -1, an unrecoverable exception occurred while making the request.
  (`#2205 <https://github.com/vertexproject/synapse/pull/2205>`_)
- Add support for embedding a logo and documentation into a Storm Package.
  (`#2204 <https://github.com/vertexproject/synapse/pull/2204>`_)

Bugfixes
--------
- Fix export filters to correctly filter tagprops.
  (`#2196 <https://github.com/vertexproject/synapse/pull/2196>`_)
- Fix an issue with Hotcount which prevented it from storing negative values.
  (`#2197 <https://github.com/vertexproject/synapse/pull/2197>`_)
- Fix an issue where ``hideconf`` configuration values were being included
  in autodoc output.
  (`#2199 <https://github.com/vertexproject/synapse/pull/2199>`_)


v2.38.0 - 2021-05-14
====================

Features and Enhancements
-------------------------
- Remove trigger inheritance from Views. Views will now only execute triggers
  which are created inside of them.
  (`#2189 <https://github.com/vertexproject/synapse/pull/2189>`_)
- Remove read-only property flags from secondary properties on ``file:bytes``
  nodes.
  (`#2191 <https://github.com/vertexproject/synapse/pull/2191>`_)
- Add a simple ``it:log:event`` form to capture log events.
  (`#2195 <https://github.com/vertexproject/synapse/pull/2195>`_)
- Add structured logging as an option for Synapse Cells. When enabled, this
  produces logs as JSONL sent to stderr. This can be set via the
  ``SYN_LOG_STRUCT`` environment variable, or adding the
  ``--structured-logging`` command line switch.
  (`#2179 <https://github.com/vertexproject/synapse/pull/2179>`_)
- Add a ``nodes.import`` command to import a ``.nodes`` file from a URL.
  (`#2186 <https://github.com/vertexproject/synapse/pull/2186>`_)
- Allow the ``desc`` key to View and Layer objects in Storm. This can be used
  to set descriptions for these objects.
  (`#2190 <https://github.com/vertexproject/synapse/pull/2190>`_)
- Use the gateiden in Storm auth when modifying rules; allowing users to share
  Views and Layers with other users.
  (`#2194 <https://github.com/vertexproject/synapse/pull/2194>`_)

Bugfixes
--------
- Fix an issue with Storm Dmon deletion not behaving properly in mirror
  configurations.
  (`#2188 <https://github.com/vertexproject/synapse/pull/2188>`_)
- Explicitly close generators in Telepath where an exception has caused the
  generator to exit early.
  (`#2183 <https://github.com/vertexproject/synapse/pull/2183>`_)
- Fix an issue where a trigger owner not having access to a view would
  cause the Storm pipeline to stop.
  (`#2189 <https://github.com/vertexproject/synapse/pull/2189>`_)


v2.37.0 - 2021-05-12
====================

Features and Enhancements
-------------------------
- Add a ``file:mime:image`` interface to the Synapse model for recording MIME
  specific metadata from image files.
  (`#2187 <https://github.com/vertexproject/synapse/pull/2187>`_)
- Add ``file:mime:jpg``, ``file:mime:tiff``, ``file:mime:gif`` and
  ``file:mime:png`` specific forms for recording metadata of those file types.
  (`#2187 <https://github.com/vertexproject/synapse/pull/2187>`_)
- Add ``$lib.pkg.has()`` Stormtype API to check for for the existence of a
  given Storm package by name.
  (`#2182 <https://github.com/vertexproject/synapse/pull/2182>`_)
- All ``None / $lib.null`` as input to setting a user password. This clears
  the password and prevents a user from being able to login.
  (`#2181 <https://github.com/vertexproject/synapse/pull/2181>`_)
- Grab any Layer push/pull offset values when calling ``Layer.pack()``.
  (`#2184 <https://github.com/vertexproject/synapse/pull/2184>`_)
- Move the retrieval of ``https:headers`` from HTTPAPI handlers into a
  function so that downstream implementers can redirect where the extra
  values are retrieved from.
  (`#2187 <https://github.com/vertexproject/synapse/pull/2187>`_)

Bugfixes
--------
- Fix an issue which allowed for deleted Storm Packages to be retrieved from
  memory.
  (`#2182 <https://github.com/vertexproject/synapse/pull/2182>`_)


v2.36.0 - 2021-05-06
====================

Features and Enhancements
-------------------------
- Add ``risk:vuln`` support to the default Stix 2.1 export, and capture
  vulnerability information used by threat actors and in campaigns. Add the
  ability to validate Stix 2.1 bundles to ensure that they are Stix 2.1 CS02
  compliant. Add the ability to lift Synapse nodes based on bundles which were
  previously exported from Synapse. The lift feature only works with bundles
  created with Synapse v2.36.0 or greater.
  (`#2174 <https://github.com/vertexproject/synapse/pull/2174>`_)
- Add a ``Str.upper()`` function for uppercasing strings in Storm.
  (`#2174 <https://github.com/vertexproject/synapse/pull/2174>`_)
- Automatically bump a user's StormDmon's when they are locked or unlocked.
  (`#2177 <https://github.com/vertexproject/synapse/pull/2177>`_)
- Add Storm Package support to ``synapse.tools.autodocs`` and update the
  rstorm implementation to capture additional directives.
  (`#2172 <https://github.com/vertexproject/synapse/pull/2172>`_)
- Tighten lark-parser version requirements.
  (`#2175 <https://github.com/vertexproject/synapse/pull/2175>`_)

Bugfixes
--------
- Fix reported layer size to represent actual disk usage.
  (`#2173 <https://github.com/vertexproject/synapse/pull/2173>`_)


v2.35.0 - 2021-04-27
====================

Features and Enhancements
-------------------------
- Add ``:issuer:cert`` and ``:selfsigned`` properties to the
  ``crypto:x509:cert`` form to enable modeling X509 certificate chains.
  (`#2163 <https://github.com/vertexproject/synapse/pull/2163>`_)
- Add a ``https:headers`` configuration option to the Cell to allow setting
  arbitrary HTTP headers for the Cell HTTPAPI server.
  (`#2164 <https://github.com/vertexproject/synapse/pull/2164>`_)
- Update the Cell HTTPAPI server to have a minimum TLS version of v1.2. Add a
  default ``/robots.txt`` route. Add ``X-XSS=Protection`` and
  ``X-Content-Type-Options`` headers to the default HTTPAPI responses.
  (`#2164 <https://github.com/vertexproject/synapse/pull/2164>`_)
- Update the minimum version of LMDB to ``1.2.1``.
  (`#2169 <https://github.com/vertexproject/synapse/pull/2169>`_)

Bugfixes
--------
- Improve the error message for Storm syntax error handling.
  (`#2162 <https://github.com/vertexproject/synapse/pull/2162>`_)
- Update the layer byarray index migration to account for arrays of
  ``inet:fqdn`` values.
  (`#2165 <https://github.com/vertexproject/synapse/pull/2165>`_)
  (`#2166 <https://github.com/vertexproject/synapse/pull/2166>`_)
- Update the ``vertexproject/synapse-aha``, ``vertexproject/synapse-axon``,
  ``vertexproject/synapse-cortex``, and ``vertexproject/synapse-cryotank``
  Docker images to use ``tini`` as a default entrypoint. This fixes an issue
  where signals were not properly being propagated to the Cells.
  (`#2168 <https://github.com/vertexproject/synapse/pull/2168>`_)
- Fix an issue with enfanged indicators which were not properly being lifted
  by Storm when operating in ``lookup`` mode.
  (`#2170 <https://github.com/vertexproject/synapse/pull/2170>`_)


v2.34.0 - 2021-04-20
====================

Features and Enhancements
-------------------------
- Storm function definitions now allow keyword arguments which may have
  default values. These must be read-only values.
  (`#2155 <https://github.com/vertexproject/synapse/pull/2155>`_)
  (`#2157 <https://github.com/vertexproject/synapse/pull/2157>`_)
- Add a ``getCellInfo()`` API to the ``Cell`` and ``CellAPI`` classes. This
  returns metadata about the cell, its version, and the currently installed
  Synapse version. Cell implementers who wish to expose Cell specific version
  information must adhere to conventiosn documented in the API docstrings of
  the function.
  (`#2151 <https://github.com/vertexproject/synapse/pull/2151>`_)
- Allow external Storm modules to be added in genpkg definitions.
  (`#2159 <https://github.com/vertexproject/synapse/pull/2159>`_)

Bugfixes
--------
- The ``$lib.layer.get()`` Stormtypes returned the top layer of the default
  view in the Cortex when called with no arguments, instead of the top layer
  of the current view. This now returns the top layer of the current view.
  (`#2156 <https://github.com/vertexproject/synapse/pull/2156>`_)
- Avoid calling ``applyNodeEdit`` when editing a tag on a Node and there are
  no edits to make.
  (`#2161 <https://github.com/vertexproject/synapse/pull/2161>`_)

Improved Documentation
----------------------
- Fix typo in docstrings from ``$lib.model.tags`` Stormtypes.
  (`#2160 <https://github.com/vertexproject/synapse/pull/2160>`_)


v2.33.1 - 2021-04-13
====================

Bugfixes
--------

- Fix a regression when expanding list objects in Storm.
  (`#2154 <https://github.com/vertexproject/synapse/pull/2154>`_)


v2.33.0 - 2021-04-12
====================

Features and Enhancements
-------------------------
- Add CWE and CVSS support to the ``risk:vuln`` form.
  (`#2143 <https://github.com/vertexproject/synapse/pull/2143>`_)
- Add a new Stormtypes library, ``$lib.infosec.cvss``, to assist with
  parsing CVSS data, computing scores, and updating ``risk:vuln`` nodes.
  (`#2143 <https://github.com/vertexproject/synapse/pull/2143>`_)
- Add ATT&CK, CWD, and CPE support to the IT model.
  (`#2143 <https://github.com/vertexproject/synapse/pull/2143>`_)
- Add ``it:network``, ``it:domain``, ``it:account``, ``it:group`` and
  ``it:login`` guid forms to model common IT concepts.
  (`#2096 <https://github.com/vertexproject/synapse/pull/2096>`_)
- Add a new model, ``project``, to model projects, tickets, sprints and epics.
  The preliminary forms for this model include ``proj:project``,
  ``proj:sprint``, ``proj:ticket``, ``proj:comment``, and ``projec:project``.
  (`#2096 <https://github.com/vertexproject/synapse/pull/2096>`_)
- Add a new Stormtypes library, ``$lib.project``, to assist with using the
  project model. The API is provisional.
  (`#2096 <https://github.com/vertexproject/synapse/pull/2096>`_)
- Allow lifting ``guid`` types with the prefix (``^=``) operator.
  (`#2096 <https://github.com/vertexproject/synapse/pull/2096>`_)
- Add ``ou:contest:result:url`` to record where to find contest results.
  (`#2144 <https://github.com/vertexproject/synapse/pull/2144>`_)
- Allow subquery as a value in additional places in Storm. This use must yield
  exactly one node. Secondary property assignments to array types may yield
  multiple nodes.
  (`#2137 <https://github.com/vertexproject/synapse/pull/2137>`_)
- Tighten up Storm iterator behavior on the backend. This should not have have
  user-facing changes in Storm behavior.
  (`#2148 <https://github.com/vertexproject/synapse/pull/2148>`_)
  (`#2096 <https://github.com/vertexproject/synapse/pull/2096>`_)
- Update the Cell backup routine so that it blocks the ioloop less.
  (`#2145 <https://github.com/vertexproject/synapse/pull/2145>`_)
- Expose the remote name and version of Storm Services in the ``service.list``
  command.
  (`#2149 <https://github.com/vertexproject/synapse/pull/2149>`_)
- Move test deprecated model elements into their own Coremodule.
  (`#2150 <https://github.com/vertexproject/synapse/pull/2150>`_)
- Update ``lark`` dependency.
  (`#2146 <https://github.com/vertexproject/synapse/pull/2146>`_)

Bugfixes
--------
- Fix incorrect grammer in model.edge commands.
  (`#2147 <https://github.com/vertexproject/synapse/pull/2147>`_)
- Reduce unit test memory usage.
  (`#2152 <https://github.com/vertexproject/synapse/pull/2152>`_)
- Pin ``jupyter-client`` library.
  (`#2153 <https://github.com/vertexproject/synapse/pull/2153>`_)


v2.32.1 - 2021-04-01
====================

Features and Enhancements
-------------------------
- The Storm ``$lib.exit()`` function now takes message arguments similar to
  ``$lib.warn()`` and fires that message into the run time as a ``warn`` prior
  to stopping the runtime.
  (`#2138 <https://github.com/vertexproject/synapse/pull/2138>`_)
- Update ``pygments`` minimum version to ``v2.7.4``.
  (`#2139 <https://github.com/vertexproject/synapse/pull/2139>`_)

Bugfixes
--------
- Do not allow light edge creation on runt nodes.
  (`#2136 <https://github.com/vertexproject/synapse/pull/2136>`_)
- Fix backup test timeout issues.
  (`#2141 <https://github.com/vertexproject/synapse/pull/2141>`_)
- Fix the ``synapse.lib.msgpack.en()`` function so that now raises the correct
  exceptions when operating in fallback mode.
  (`#2140 <https://github.com/vertexproject/synapse/pull/2140>`_)
- Fix the ``Snap.addNodes()`` API handling of deprecated model elements when
  doing bulk data ingest.
  (`#2142 <https://github.com/vertexproject/synapse/pull/2142>`_)


v2.32.0 - 2021-03-30
====================

Features and Enhancements
-------------------------
- Increase the verbosity of logging statements related to Cell backup
  operations. This allows for better visibility into what is happening
  while a backup is occurring.
  (`#2124 <https://github.com/vertexproject/synapse/pull/2124>`_)
- Add Telepath and Storm APIs for setting all the roles of a User at once.
  (`#2127 <https://github.com/vertexproject/synapse/pull/2127>`_)
- Expose the Synapse package commit hash over Telepath and Stormtypes.
  (`#2133 <https://github.com/vertexproject/synapse/pull/2133>`_)

Bugfixes
--------
- Increase the process spawn timeout for Cell backup operations. Prevent the
  Cell backup from grabbing lmdb transactions for slabs in the cell local tmp
  directory.
  (`#2124 <https://github.com/vertexproject/synapse/pull/2124>`_)


v2.31.1 - 2021-03-25
====================

Bugfixes
--------
- Fix a formatting issue preventing Python packages from being uploaded to
  PyPI.
  (`#2131 <https://github.com/vertexproject/synapse/pull/2131>`_)


v2.31.0 - 2021-03-24
====================

Features and Enhancements
-------------------------
- Add initial capability for exporting STIX 2.1 from the Cortex.
  (`#2120 <https://github.com/vertexproject/synapse/pull/2120>`_)
- Refactor how lift APIs are implemented, moving them up to the Cortex itself.
  This results in multi-layer lifts now yielding nodes in a sorted order.
  (`#2093 <https://github.com/vertexproject/synapse/pull/2093>`_)
  (`#2128 <https://github.com/vertexproject/synapse/pull/2128>`_)
- Add ``$lib.range()`` Storm function to generate ranges of integers.
  (`#2122 <https://github.com/vertexproject/synapse/pull/2122>`_)
- Add an ``errok`` option to the ``$lib.time.parse()`` Storm function to
  allow the function to return ``$lib.null`` if the time string fails to
  parse.
  (`#2126 <https://github.com/vertexproject/synapse/pull/2126>`_)
- Don't execute Cron jobs, Triggers, or StormDmons for locked users.
  (`#2123 <https://github.com/vertexproject/synapse/pull/2123>`_)
  (`#2129 <https://github.com/vertexproject/synapse/pull/2129>`_)
- The ``git`` commit hash is now embedded into the ``synapse.lib.version``
  module when building PyPi packages and Docker images.
  (`#2119 <https://github.com/vertexproject/synapse/pull/2119>`_)

Improved Documentation
----------------------
- Update Axon wget API documentation to note that we always store the body of
  the HTTP response, regardless of status code.
  (`#2125 <https://github.com/vertexproject/synapse/pull/2125>`_)


v2.30.0 - 2021-03-17
====================

Features and Enhancements
-------------------------
- Add ``$lib.trycast()`` to allow for Storm control flow based on type
  normalization.
  (`#2113 <https://github.com/vertexproject/synapse/pull/2113>`_)

Bugfixes
--------
- Resolve a bug related to pivoting to a secondary property that is an
  array value.
  (`#2111 <https://github.com/vertexproject/synapse/pull/2111>`_)
- Fix an issue with Aha and persisting the online state of services upon
  startup.
  (`#2103 <https://github.com/vertexproject/synapse/pull/2103>`_)
- Convert the type of ``inet:web:acct:singup:client:ipv6`` from a
  ``inet:ipv4`` to an ``inet:ipv6``.
  (`#2114 <https://github.com/vertexproject/synapse/pull/2114>`_)
- Fix an idempotency issue when deleting a custom form.
  (`#2112 <https://github.com/vertexproject/synapse/pull/2112>`_)

Improved Documentation
----------------------
- Update README.rst.
  (`#2215 <https://github.com/vertexproject/synapse/pull/2115>`_)
  (`#2217 <https://github.com/vertexproject/synapse/pull/2117>`_)
  (`#2216 <https://github.com/vertexproject/synapse/pull/2116>`_)


v2.29.0 - 2021-03-11
====================

This release includes a Cortex storage Layer bugfix. It does an automatic
upgrade upon startup to identify and correct invalid array index values.
Depending on time needed to perform this automatic upgrade, the Cortex may
appear unresponsive. Deployments with startup or liveliness probes should
have those disabled while this upgrade is performed to prevent accidental
termination of the Cortex process.

Features and Enhancements
-------------------------
- Add a ``reverse`` argument to ``$lib.sorted()`` to allow a Storm user
  to easily reverse an iterable item.
  (`#2109 <https://github.com/vertexproject/synapse/pull/2109>`_)
- Update minimum required versions of Tornado and PyYAML.
  (`#2108 <https://github.com/vertexproject/synapse/pull/2108>`_)

Bugfixes
--------
- Fix an issue with Array property type deletion not properly deleting values
  in the ``byarray`` index. This requires an automatic data migration done at
  Cortex startup to remove extra index values which may be present in the
  index.
  (`#2104 <https://github.com/vertexproject/synapse/pull/2104>`_)
  (`#2106 <https://github.com/vertexproject/synapse/pull/2106>`_)
- Fix issues with using the Storm ``?=`` operator with types which can
  generate multiple values from a given input string when making nodes.
  (`#2105 <https://github.com/vertexproject/synapse/pull/2105>`_)
  (`#2107 <https://github.com/vertexproject/synapse/pull/2107>`_)

Improved Documentation
----------------------
- Add Devops documentation explaining our Docker container offerings.
  (`#2104 <https://github.com/vertexproject/synapse/pull/2104>`_)
  (`#2110 <https://github.com/vertexproject/synapse/pull/2110>`_)


v2.28.1 - 2021-03-08
====================

Bugfixes
--------
- Fix ``$lib.model.prop()`` API when called with a universal property.
  It now returns ``$lib.null`` instead of raising an exception.
  (`#2100 <https://github.com/vertexproject/synapse/pull/2100>`_)
- Fix the streaming backup API when used with Telepath and SSL.
  (`#2101 <https://github.com/vertexproject/synapse/pull/2101>`_)

Improved Documentation
----------------------
- Add API documentation for the Axon.
  (`#2098 <https://github.com/vertexproject/synapse/pull/2098>`_)
- Update the Storm pivot reference documentation.
  (`#2101 <https://github.com/vertexproject/synapse/pull/2101>`_)


v2.28.0 - 2021-02-26
====================

Features and Enhancements
-------------------------
- Add ``String.reverse()`` Stormtypes API to reverse a string.
  (`#2086 <https://github.com/vertexproject/synapse/pull/2086>`_)
- Add Cell APIs for streaming compressed backups.
  (`#2084 <https://github.com/vertexproject/synapse/pull/2084>`_)
  (`#2091 <https://github.com/vertexproject/synapse/pull/2091>`_)
- Refactor ``snap.addNodes()`` to reduce the transaction count.
  (`#2087 <https://github.com/vertexproject/synapse/pull/2087>`_)
  (`#2090 <https://github.com/vertexproject/synapse/pull/2090>`_)
- Add ``$lib.axon.list()`` Stormtypes API to list hashes in an Axon.
  (`#2088 <https://github.com/vertexproject/synapse/pull/2088>`_)
- Add user permissions requirements for Aha CSR signing.
  (`#2089 <https://github.com/vertexproject/synapse/pull/2089>`_)
- Add ``aha:svcinfo`` configuration option for the base Cell.
  (`#2089 <https://github.com/vertexproject/synapse/pull/2089>`_)
- Add interfaces to the output of ``model.getModelDefs()`` and the
  ``getModelDict()`` APIs.
  (`#2092 <https://github.com/vertexproject/synapse/pull/2092>`_)
- Update pylmdb to ``v1.1.1``.
  (`#2076 <https://github.com/vertexproject/synapse/pull/2076>`_)

Bugfixes
--------
- Fix incorrect permissions check in the ``merge --diff`` Storm command.
  (`#2085 <https://github.com/vertexproject/synapse/pull/2085>`_)
- Fix service teardown issue in Aha service on fini.
  (`#2089 <https://github.com/vertexproject/synapse/pull/2089>`_)
- Fix possible ``synapse.tools.cmdr`` teardown issue when using Aha.
  (`#2089 <https://github.com/vertexproject/synapse/pull/2089>`_)
- Cast ``synapse_minversion`` from Storm Packages into a tuple to avoid
  packages added with HTTP endpoints from failing to validate.
  (`#2095 <https://github.com/vertexproject/synapse/pull/2095>`_)

Improved Documentation
----------------------
- Add documentation for the Aha discovery service.
  (`#2089 <https://github.com/vertexproject/synapse/pull/2089>`_)
- Add documentation for assigning secondary properties via subquery syntax.
  (`#2097 <https://github.com/vertexproject/synapse/pull/2097>`_)

v2.27.0 - 2021-02-16
====================

Features and Enhancements
-------------------------
- Allow property assignment and array operations from subqueries.
  (`#2072 <https://github.com/vertexproject/synapse/pull/2072>`_)
- Add APIs to the Axon to allow the deletion of blobs via Telepath and HTTP
  APIs.
  (`#2080 <https://github.com/vertexproject/synapse/pull/2080>`_)
- Add a ``str.slice()`` stormtypes method to allow easy string slicing.
  (`#2083 <https://github.com/vertexproject/synapse/pull/2083>`_)
- Modularize the Storm HTTP API handlers.
  (`#2082 <https://github.com/vertexproject/synapse/pull/2082>`_)

Bugfixes
--------
- Fix Agenda events which were not being properly tracked via the Nexus.
  (`#2078 <https://github.com/vertexproject/synapse/pull/2078>`_)

Improved Documentation
----------------------
- Add documentation for the Cortex ``/api/v1/storm/export`` HTTP endpoint.
  This also included documentation for the scrub option in Storm.
  (`#2079 <https://github.com/vertexproject/synapse/pull/2079>`_)
- Add a Code of Conduct for Synapse.
  (`#2081 <https://github.com/vertexproject/synapse/pull/2081>`_)


v2.26.0 - 2021-02-05
====================

Features and Enhancements
-------------------------
- Add Storm commands for easily adding, deleting, and listing layer push
  and pull configurations.
  (`#2071 <https://github.com/vertexproject/synapse/pull/2071>`_)

Bugfixes
--------
- Fix ``layer.getPropCount()`` API for universal properties.
  (`#2073 <https://github.com/vertexproject/synapse/pull/2073>`_)
- Add a missing async yield in ``Snap.addNodes()``.
  (`#2074 <https://github.com/vertexproject/synapse/pull/2074>`_)
- Constrain lmdb version due to unexpected behavior in ``v1.1.0``.
  (`#2075 <https://github.com/vertexproject/synapse/pull/2075>`_)

Improved Documentation
----------------------
- Update user docs for Storm flow control and data model references.
  (`#2066 <https://github.com/vertexproject/synapse/pull/2066>`_)


v2.25.0 - 2021-02-01
====================

Features and Enhancements
-------------------------
- Implement tag model based pruning behavior for controlling how individual
  tag trees are deleted from nodes.
  (`#2067 <https://github.com/vertexproject/synapse/pull/2067>`_)
- Add model interfaces for defining common sets of properties for forms,
  starting with some file mime metadata.
  (`#2040 <https://github.com/vertexproject/synapse/pull/2040>`_)
- Add ``file:mime:msdoc``, ``file:mime:msxls``, ``file:mime:msppt``, and
  ``file:mime:rtf`` forms.
  (`#2040 <https://github.com/vertexproject/synapse/pull/2040>`_)
- Tweak the ival normalizer to auto-expand intervals with a single element.
  (`#2070 <https://github.com/vertexproject/synapse/pull/2070>`_)
- Removed the experimental ``spawn`` feature of the Storm runtime.
  (`#2068 <https://github.com/vertexproject/synapse/pull/2068>`_)

Bugfixes
--------
- Add a missing async yield statement in ``View.getEdgeVerbs()``.
  (`#2069 <https://github.com/vertexproject/synapse/pull/2069>`_)

Improved Documentation
----------------------
- Correct incorrect references to the ``synapse.tools.easycert``
  documentation.
  (`#2065 <https://github.com/vertexproject/synapse/pull/2065>`_)


v2.24.0 - 2021-01-29
====================

Features and Enhancements
-------------------------
- Add support for storing model metadata for tags and support for enforcing
  tag trees using regular expressions.
  (`#2056 <https://github.com/vertexproject/synapse/pull/2056>`_)
- Add ``ou:contest:url`` secondary property.
  (`#2059 <https://github.com/vertexproject/synapse/pull/2059>`_)
- Add ``synapse.lib.autodoc`` to collect some Storm documentation helpers
  into a single library.
  (`#2034 <https://github.com/vertexproject/synapse/pull/2034>`_)
- Add ``tag.prune`` Storm command to remove parent tags when removing a
  leaf tag from a node.
  (`#2062 <https://github.com/vertexproject/synapse/pull/2062>`_)
- Update the ``msgpack`` Python dependency to version ``v1.0.2``.
  (`#1735 <https://github.com/vertexproject/synapse/pull/1735>`_)
- Add logs to Cell backup routines.
  (`#2060 <https://github.com/vertexproject/synapse/pull/2060>`_)
- Export the Layer iterrows APIs to the CoreApi.
  (`#2061 <https://github.com/vertexproject/synapse/pull/2061>`_)

Bugfixes
--------
- Do not connect to Aha servers when they are not needed.
  (`#2058 <https://github.com/vertexproject/synapse/pull/2058>`_)
- Make the array property ``ou:org:industries`` a unique array property.
  (`#2059 <https://github.com/vertexproject/synapse/pull/2059>`_)
- Add permission checks to the Storm ``movetag`` command.
  (`#2063 <https://github.com/vertexproject/synapse/pull/2063>`_)
- Add permissions checks to the Storm ``edges.del`` command.
  (`#2064 <https://github.com/vertexproject/synapse/pull/2064>`_)

Improved Documentation
----------------------
- Add documentation for the ``synapse.tools.genpkg`` utility, for loading
  Storm packages into a Cortex.
  (`#2057 <https://github.com/vertexproject/synapse/pull/2057>`_)
- Refactor the Stormtypes documentation generation to make it data driven.
  (`#2034 <https://github.com/vertexproject/synapse/pull/2034>`_)


v2.23.0 - 2021-01-21
====================

Features and Enhancements
-------------------------
- Add support for ndef based light edge definitions in the ``syn.nodes``
  feed API.
  (`#2051 <https://github.com/vertexproject/synapse/pull/2051>`_)
  (`#2053 <https://github.com/vertexproject/synapse/pull/2053>`_)
- Add ISIC codes to the ``ou:industry`` form.
  (`#2054 <https://github.com/vertexproject/synapse/pull/2054>`_)
  (`#2055 <https://github.com/vertexproject/synapse/pull/2055>`_)
- Add secondary properties ``:loc``, ``:latlong``, and ``:place`` to the
  ``inet:web:action`` and ``inet:web:logon`` forms.
  (`#2052 <https://github.com/vertexproject/synapse/pull/2052>`_)
- Add secondary property ``:enabled`` to the form ``it:app:yara:rule``.
  (`#2052 <https://github.com/vertexproject/synapse/pull/2052>`_)
- Deprecate the ``file:string`` and ``ou:member`` forms, in favor of
  using light edges for storing those relationships.
  (`#2052 <https://github.com/vertexproject/synapse/pull/2052>`_)


v2.22.0 - 2021-01-19
====================

Features and Enhancements
-------------------------
- Allow expression statements to be used in Storm filters.
  (`#2041 <https://github.com/vertexproject/synapse/pull/2041>`_)
- Add ``file:subfile:path`` secondary property to record the path a file was
  stored in a parent file. The corresponding ``file:subfile:name`` property is
  marked as deprecated.
  (`#2043 <https://github.com/vertexproject/synapse/pull/2043>`_)
- Make the Axon ``wget()`` timeout a configurable parameter.
  (`#2047 <https://github.com/vertexproject/synapse/pull/2047>`_)
- Add a ``Cortex.exportStorm()`` on the Cortex which allows for exporting
  nodes from a Storm query which can be directly ingested with the
  ``syn.nodes`` feed function. If the data is serialized using msgpack and
  stored in a Axon, it can be added to a Cortex with the new
  ``Cortex.feedFromAxon()`` API. A new HTTP API, ``/api/v1/storm/export``,
  can be used to get a msgpacked file using this export interface.
  (`#2045 <https://github.com/vertexproject/synapse/pull/2045>`_)

Bugfixes
--------
- Fix issues in the Layer push and pull loop code.
  (`#2044 <https://github.com/vertexproject/synapse/pull/2044>`_)
  (`#2048 <https://github.com/vertexproject/synapse/pull/2048>`_)
- Add missing ``toprim()`` and ``tostr()`` calls for the Stormtypes Whois
  guid generation helpers.
  (`#2046 <https://github.com/vertexproject/synapse/pull/2046>`_)
- Fix behavior in the Storm lookup mode which failed to lookup some expected
  results.
  (`#2049 <https://github.com/vertexproject/synapse/pull/2049>`_)
- Fix ``$lib.pkg.get()`` return value when the package is not present.
  (`#2050 <https://github.com/vertexproject/synapse/pull/2050>`_)


v2.21.1 - 2021-01-04
====================

Bugfixes
--------
- Fix a variable scoping issue causing a race condition.
  (`#2042 <https://github.com/vertexproject/synapse/pull/2042>`_)


v2.21.0 - 2020-12-31
====================

Features and Enhancements
-------------------------
- Add a Storm ``wget`` command which will download a file from a URL using
  the Cortex Axon and yield ``inet:urlfile`` nodes.
  (`#2035 <https://github.com/vertexproject/synapse/pull/2035>`_)
- Add a ``--diff`` option to the ``merge`` command to enumerate changes.
  (`#2037 <https://github.com/vertexproject/synapse/pull/2037>`_)
- Allow StormLib Layer API to dynamically update a Layer's logedits setting.
  (`#2038 <https://github.com/vertexproject/synapse/pull/2038>`_)
- Add StormLib APIs for adding and deleting extended model properties, forms
  and tag properties.
  (`#2039 <https://github.com/vertexproject/synapse/pull/2039>`_)

Bugfixes
--------
- Fix an issue with the JsonStor not created nested entries properly.
  (`#2036 <https://github.com/vertexproject/synapse/pull/2036>`_)


v2.20.0 - 2020-12-29
====================

Features and Enhancements
-------------------------
- Correct the StormType ``Queue.pop()`` API to properly pop and return
  only the item at the specified index or the next entry in the Queue.
  This simplifies the intent behind the ``.pop()`` operation; and removes
  the ``cull`` and ``wait`` parameters which were previously on the method.
  (`#2032 <https://github.com/vertexproject/synapse/pull/2032>`_)

Bugfixes
--------
- Use ``resp.iter_chunked`` in the Axon ``.wget()`` API to improve
  compatibility with some third party libraries.
  (`#2030 <https://github.com/vertexproject/synapse/pull/2030>`_)
- Require the use of a msgpack based deepcopy operation in handling
  storage nodes.
  (`#2031 <https://github.com/vertexproject/synapse/pull/2031>`_)
- Fix for ambiguous whitespace in Storm command argument parsing.
  (`#2033 <https://github.com/vertexproject/synapse/pull/2033>`_)


v2.19.0 - 2020-12-27
====================

Features and Enhancements
-------------------------

- Add APIs to remove decommissioned services from AHA servers.
- Add (optional) explicit network parameters to AHA APIs.
  (`#2029 <https://github.com/vertexproject/synapse/pull/2029>`_)

- Add cell.isCellActive() API to differentiate leaders/mirrors.
  (`#2028 <https://github.com/vertexproject/synapse/pull/2028>`_)

- Add pop() method to Storm list objects.
  (`#2027 <https://github.com/vertexproject/synapse/pull/2027>`_)

Bugfixes
--------

- Fix bug in dry-run output of new merge command.
  (`#2026 <https://github.com/vertexproject/synapse/pull/2026>`_)

v2.18.1 - 2020-12-24
====================

Bugfixes
--------

- Make syncIndexEvents testing more resiliant
- Make syncIndexEvents yield more often when filtering results
  (`#2025 <https://github.com/vertexproject/synapse/pull/2025>`_)

- Update push/pull tests to use new waittask() API
- Raise clear errors in ambiguous use of node.tagglobs() API
- Update model docs and examples for geo:latitude and geo:longitude
- Support deref form names in storm node add expressions
  (`#2024 <https://github.com/vertexproject/synapse/pull/2024>`_)

- Update tests to normalize equality comparison values
  (`#2023 <https://github.com/vertexproject/synapse/pull/2023>`_)

v2.18.0 - 2020-12-23
====================

Features and Enhancements
-------------------------

- Added axon.size() API and storm plumbing
  (`#2020 <https://github.com/vertexproject/synapse/pull/2020>`_)

Bugfixes
--------

- Fix active coro issue uncovered with cluster testing
  (`#2021 <https://github.com/vertexproject/synapse/pull/2021>`_)

v2.17.1 - 2020-12-22
====================

Features and Enhancements
-------------------------

- Added (BETA) RST pre-processor to embed Storm output into RST docs.
  (`#1988 <https://github.com/vertexproject/synapse/pull/1988>`_)

- Added a ``merge`` command to allow per-node Layer merge operations to
  be done.
  (`#2009 <https://github.com/vertexproject/synapse/pull/2009>`_)

- Updated storm package format to include a semver version string.
  (`#2016 <https://github.com/vertexproject/synapse/pull/2016>`_)

- Added telepath proxy getPipeline API to minimize round-trip delay.
  (`#1615 <https://github.com/vertexproject/synapse/pull/1615>`_)

- Added Node properties iteration and setitem APIs to storm.
  (`#2011 <https://github.com/vertexproject/synapse/pull/2011>`_)


Bugfixes
--------

- Fixes for active coro API and internal layer API name fixes.
  (`#2018 <https://github.com/vertexproject/synapse/pull/2018>`_)

- Allow :prop -+> * join syntax.
  (`#2015 <https://github.com/vertexproject/synapse/pull/2015>`_)

- Make getFormCount() API return a primitive dictionary.
  (`#2014 <https://github.com/vertexproject/synapse/pull/2014>`_)

- Make StormVarListError messages more user friendly.
  (`#2013 <https://github.com/vertexproject/synapse/pull/2013>`_)

v2.17.0 - 2020-12-22
====================

``2.17.0`` was not published due to CI issues.


v2.16.1 - 2020-12-17
====================

Features and Enhancements
-------------------------
- Allow the ``matchdef`` used in the ``Layer.syncIndexEvents()`` API
  to match on tagprop data.
  (`#2010 <https://github.com/vertexproject/synapse/pull/2010>`_)

Bugfixes
--------
- Properly detect and raise a client side exception in Telepath generators
  when the underlying Link has been closed.
  (`#2008 <https://github.com/vertexproject/synapse/pull/2008>`_)
- Refactor the Layer push/push test to not reach through the Layer API
  boundary.
  (`#2012 <https://github.com/vertexproject/synapse/pull/2012>`_)

Improved Documentation
----------------------
- Add documentation for Storm raw pivot syntax.
  (`#2007 <https://github.com/vertexproject/synapse/pull/2007>`_)
- Add documentation for recently added Storm commands.
  (`#2007 <https://github.com/vertexproject/synapse/pull/2007>`_)
- General cleanup and clarifications.
  (`#2007 <https://github.com/vertexproject/synapse/pull/2007>`_)


v2.16.0 - 2020-12-15
====================

Features and Enhancements
-------------------------
- Replaced the View sync APIs introduced in ``v2.14.0`` with Layer specific
  sync APIs.
  (`#2003 <https://github.com/vertexproject/synapse/pull/2003>`_)
- Add ``$lib.regex.matches()`` and ``$lib.regex.search()`` Stormtypes APIs for
  performing regular expression operations against text in Storm.
  (`#1999 <https://github.com/vertexproject/synapse/pull/1999>`_)
  (`#2005 <https://github.com/vertexproject/synapse/pull/2005>`_)
- Add ``synapse.tools.genpkg`` for generating Storm packages and loading them
  into a Cortex.
  (`#2004 <https://github.com/vertexproject/synapse/pull/2004>`_)
- Refactored the StormDmon implementation to use a single async task and allow
  the Dmons to be restarted via ``$lib.dmon.bump(iden)``. This replaces the
  outer task / inner task paradigm that was previously present. Also add the
  ability to persistently disable and enable a StomDmon.
  (`#1998 <https://github.com/vertexproject/synapse/pull/1998>`_)
- Added ``aha://`` support to the ``synapse.tools.pushfile`` and
  ``synapse.tools.pullfile`` tools.
  (`#2006 <https://github.com/vertexproject/synapse/pull/2006>`_)

Bugfixes
--------
- Properly handle whitespace in keyword arguments when calling functions in
  Storm.
  (`#1997 <https://github.com/vertexproject/synapse/pull/1997>`_)
- Fix some garbage collection issues causing periodic pauses in a Cortex due
  to failing to close some generators used in the Storm Command AST node.
  (`#2001 <https://github.com/vertexproject/synapse/pull/2001>`_)
  (`#2002 <https://github.com/vertexproject/synapse/pull/2002>`_)
- Fix scope based permission checks in Storm.
  (`#2000 <https://github.com/vertexproject/synapse/pull/2000>`_)


v2.15.0 - 2020-12-11
====================

Features and Enhancements
-------------------------
- Add two new Cortex APIs: ``syncIndexEvents`` and ``syncLayerEvents`` useful
  for external indexing.
  (`#1948 <https://github.com/vertexproject/synapse/pull/1948>`_)
  (`#1996 <https://github.com/vertexproject/synapse/pull/1996>`_)
- LMDB Slab improvements: Allow dupfixed dbs, add ``firstkey`` method, inline
  ``_ispo2``, add HotCount deletion.
  (`#1948 <https://github.com/vertexproject/synapse/pull/1948>`_)
- Add method to merge sort sorted async generators.
  (`#1948 <https://github.com/vertexproject/synapse/pull/1948>`_)

Bugfixes
--------
- Ensure parent FQDN exists even in out-of-order node edit playback.
  (`#1995 <https://github.com/vertexproject/synapse/pull/1995>`_)


v2.14.2 - 2020-12-10
====================

Bugfixes
--------
- Fix an issue with the new layer push / pull code.
  (`#1994 <https://github.com/vertexproject/synapse/pull/1994>`_)
- Fix an issue with the url sanitization function when the path contains
  an ``@`` character.
  (`#1993 <https://github.com/vertexproject/synapse/pull/1993>`_)


v2.14.1 - 2020-12-09
====================

Features and Enhancements
-------------------------
- Add a ``/api/v1/active`` HTTPAPI to the Cell that can be used as an
  unauthenticated liveliness check.
  (`#1987 <https://github.com/vertexproject/synapse/pull/1987>`_)
- Add ``$lib.pip.gen()`` Stormtypes API for ephemeral queues and bulk data
  access in Storm.
  (`#1986 <https://github.com/vertexproject/synapse/pull/1986>`_)
- Add a ``$lib.model.tagprop()`` Stormtypes API for retrieving Tagprop
  definitions.
  (`#1990 <https://github.com/vertexproject/synapse/pull/1990>`_)
- Add efficient View and Layer push/pull configurations.
  (`#1991 <https://github.com/vertexproject/synapse/pull/1991>`_)
  (`#1992 <https://github.com/vertexproject/synapse/pull/1992>`_)
- Add ``getAhaUrls()`` to the Aha service to prepare for additional
  service discovery.
  (`#1989 <https://github.com/vertexproject/synapse/pull/1989>`_)
- Add a ``/api/v1/auth/onepass/issue`` HTTPAPI for an admin to mint a
  one-time password for a Cell user.
  (`#1982 <https://github.com/vertexproject/synapse/pull/1982>`_)

Bugfixes
--------
- Make ``aha://`` urls honor local paths.
  (`#1985 <https://github.com/vertexproject/synapse/pull/1985>`_)


v2.14.0 - 2020-12-09
====================

``2.14.0`` was not published due to CI issues.


v2.13.0 - 2020-12-04
====================

Features and Enhancements
-------------------------
- Add ``$lib.pkg.get()`` StormTypes function to get the Storm Package
  definition for a given package by name.
  (`#1983 <https://github.com/vertexproject/synapse/pull/1983>`_)

Bugfixes
--------
- The user account provisioned by the ``aha:admin`` could be locked out.
  Now, upon startup, if they have been locked out or had their admin status
  removed, they are unlocked and admin is reset.
  (`#1984 <https://github.com/vertexproject/synapse/pull/1984>`_)


v2.12.3 - 2020-12-03
====================

Bugfixes
--------
- Prevent OverflowError exceptions which could have resulted from lift
  operations with integer storage types.
  (`#1980 <https://github.com/vertexproject/synapse/pull/1980>`_)
- Remove ``inet:ipv4`` norm routine wrap-around behavior for integers which
  are outside the normal bounds of IPv4 addresses.
  (`#1979 <https://github.com/vertexproject/synapse/pull/1979>`_)
- Fix ``view.add`` and fork related permissions.
  (`#1981 <https://github.com/vertexproject/synapse/pull/1981>`_)
- Read ``telepath.yaml`` when using the ``synapse.tools.cellauth`` tool.
  (`#1981 <https://github.com/vertexproject/synapse/pull/1981>`_)


v2.12.2 - 2020-12-01
====================

This release also includes the changes from v2.12.1, which was not released
due to an issue with CI pipelines.

Bugfixes
--------
- Add the missing API ``getPathObjs`` on the JsonStorCell.
  (`#1976 <https://github.com/vertexproject/synapse/pull/1976>`_)
- Fix the HasRelPropCond AST node support for Storm pivprop operations.
  (`#1972 <https://github.com/vertexproject/synapse/pull/1972>`_)
- Fix support for the ``aha:registry`` config parameter in a Cell to support
  an array of strings.
  (`#1975 <https://github.com/vertexproject/synapse/pull/1975>`_)
- Split the ``Cortex.addForm()`` Nexus handler into two parts to allow for
  safe event replay.
  (`#1978 <https://github.com/vertexproject/synapse/pull/1978>`_)
- Stop forking a large number of child layers in a View persistence test.
  (`#1977 <https://github.com/vertexproject/synapse/pull/1977>`_)


v2.12.1 - 2020-12-01
====================

Bugfixes
--------
- Add the missing API ``getPathObjs`` on the JsonStorCell.
  (`#1976 <https://github.com/vertexproject/synapse/pull/1976>`_)
- Fix the HasRelPropCond AST node support for Storm pivprop operations.
  (`#1972 <https://github.com/vertexproject/synapse/pull/1972>`_)
- Fix support for the ``aha:registry`` config parameter in a Cell to support
  an array of strings.
  (`#1975 <https://github.com/vertexproject/synapse/pull/1975>`_)


v2.12.0 - 2020-11-30
====================

Features and Enhancements
-------------------------
- Add a ``onload`` paramter to the ``stormpkg`` definition. This represents
  a Storm query which is executed every time the ``stormpkg`` is loaded in
  a Cortex.
  (`#1971 <https://github.com/vertexproject/synapse/pull/1971>`_)
  (`#1974 <https://github.com/vertexproject/synapse/pull/1974>`_)
- Add the ability, in Storm, to unset variables, remove items from
  dictionaries, and remove items from lists. This is done via assigning
  ``$lib.undef`` to the value to be removed.
  (`#1970 <https://github.com/vertexproject/synapse/pull/1970>`_)
- Add support for SOCKS proxy support for outgoing connections from an Axon
  and Cortex, using the ``'http:proxy`` configuration option. This
  configuration value must be a valid string for the
  ``aiohttp_socks.ProxyConnector.from_url()`` API. The SOCKS proxy is used by
  the Axon when downloading files; and by the Cortex when making HTTP
  connections inside of Storm.
  (`#1968 <https://github.com/vertexproject/synapse/pull/1968>`_)
- Add ``aha:admin`` to the Cell configuration to provide a common name that
  is used to create an admin user for remote access to the Cell via the
  Aha service.
  (`#1969 <https://github.com/vertexproject/synapse/pull/1969>`_)
- Add ``auth:ctor`` and ``auth:conf`` config to the Cell in order to allow
  hooking the construction of the ``HiveAuth`` object.
  (`#1969 <https://github.com/vertexproject/synapse/pull/1969>`_)


v2.11.0 - 2020-11-25
====================

Features and Enhancements
-------------------------
- Optimize Storm lift and filter queries, so that more efficient lift
  operations may be performed in some cases.
  (`#1966 <https://github.com/vertexproject/synapse/pull/1966>`_)
- Add a ``Axon.wget()`` API to allow the Axon to retrieve files directly
  from a URL.
  (`#1965 <https://github.com/vertexproject/synapse/pull/1965>`_)
- Add a JsonStor Cell, which allows for hierarchical storage and retrieval
  of JSON documents.
  (`#1954 <https://github.com/vertexproject/synapse/pull/1954>`_)
- Add a Cortex HTTP API, ``/api/v1/storm/call``. This behaves like the
  ``CoreApi.callStorm()`` API.
  (`#1967 <https://github.com/vertexproject/synapse/pull/1967>`_)
- Add ``:client:host`` and ``:server:host`` secondary properties to the
  ``inet:http:request`` form.
  (`#1955 <https://github.com/vertexproject/synapse/pull/1955>`_)
- Add ``:host`` and ``:acct`` secondary properties to the
  ``inet:search:query`` form.
  (`#1955 <https://github.com/vertexproject/synapse/pull/1955>`_)
- Add a Telepath service discovery implementation, the Aha cell. The Aha
  APIs are currently provisional and subject to change.
  (`#1954 <https://github.com/vertexproject/synapse/pull/1954>`_)


v2.10.2 - 2020-11-20
====================

Features and Enhancements
-------------------------
- The Storm ``cron.at`` command now supports a ``--now`` flag to create a
  cron job which immediately executes.
  (`#1963 <https://github.com/vertexproject/synapse/pull/1963>`_)

Bugfixes
--------
- Fix a cleanup race that caused occasional ``test_lmdbslab_base`` failures.
  (`#1962 <https://github.com/vertexproject/synapse/pull/1962>`_)
- Fix an issue with ``EDIT_NODEDATA_SET`` nodeedits missing the ``oldv``
  value.
  (`#1961 <https://github.com/vertexproject/synapse/pull/1961>`_)
- Fix an issue where ``cron.cleanup`` could have prematurely deleted some cron
  jobs.
  (`#1963 <https://github.com/vertexproject/synapse/pull/1963>`_)


v2.10.1 - 2020-11-17
====================

Bugfixes
--------
- Fix a CI issue which prevented the Python ``sdist`` package from being
  uploaded to PyPi.
  (`#1960 <https://github.com/vertexproject/synapse/pull/1960>`_)


v2.10.0 - 2020-11-17
====================

Announcements
-------------

The ``v2.10.0`` Synapse release contains support for Python 3.8. Docker images
are now built using a Python 3.8 image by default. There are also Python 3.7
images available as ``vertexproject/synapse:master-py37`` and
``vertexproject/synapse:v2.x.x-py37``.


Features and Enhancements
-------------------------
- Python 3.8 release support for Docker and PyPi.
  (`#1921 <https://github.com/vertexproject/synapse/pull/1921>`_)
  (`#1956 <https://github.com/vertexproject/synapse/pull/1956>`_)
- Add support for adding extended forms to the Cortex. This allows users to
  define their own forms using the existing types which are available in the
  Synapse data model.
  (`#1944 <https://github.com/vertexproject/synapse/pull/1944>`_)
- The Storm ``and`` and ``or`` statements now short-circuit and will return
  when their logical condition is first met. This means that subsequent
  clauses in those statements may not be executed.
  (`#1952 <https://github.com/vertexproject/synapse/pull/1952>`_)
- Add a mechanism for Storm Services to specify commands which may require
  privilege elevation to execute. An example of this may be to allow a command
  to create nodes; without managning individual permissions on what nodes a
  user may normally be allowed to create. Services using this mechanism wiill
  use the ``storm.asroot.cmd.<<cmd name>>`` hierarchy to grant this permission.
  (`#1953 <https://github.com/vertexproject/synapse/pull/1953>`_)
  (`#1958 <https://github.com/vertexproject/synapse/pull/1958>`_)
- Add ``$lib.json`` Stormtypes Library to convert between string data and
  primitives.
  (`#1949 <https://github.com/vertexproject/synapse/pull/1949>`_)
- Add a ``parallel`` command to allow for executing a portion of a Storm
  query in parallel. Add a ``background`` command to execute a Storm query
  as a detached task from the current query, capturing variables in the
  process.
  (`#1931 <https://github.com/vertexproject/synapse/pull/1931>`_)
  (`#1957 <https://github.com/vertexproject/synapse/pull/1957>`_)
- Add a ``$lib.exit()`` function to StormTypes to allow for quickly
  exiting a Storm query.
  (`#1931 <https://github.com/vertexproject/synapse/pull/1931>`_)
- Add ``$lib.bytes.upload()`` to Stormtypes for streaming bytes into the
  Axon that the Cortex is configured with.
  (`#1945 <https://github.com/vertexproject/synapse/pull/1945>`_)
- Add Storm commands to manage locking and unlocking deprecated model
  properties.
  (`#1909 <https://github.com/vertexproject/synapse/pull/1909>`_)
- Add ``cron.cleanup`` command to make it easy to clean up completed cron
  jobs.
  (`#1942 <https://github.com/vertexproject/synapse/pull/1942>`_)
- Add date of death properties and consistently named photo secondary
  properties.
  (`#1929 <https://github.com/vertexproject/synapse/pull/1929>`_)
- Add model additions for representing education and awards.
  (`#1930 <https://github.com/vertexproject/synapse/pull/1930>`_)
- Add additional account linkages to the ``inet`` model for users and groups.
  (`#1946 <https://github.com/vertexproject/synapse/pull/1946>`_)
- Add ``inet:web:hashtag`` as its own form, and add ``:hashtags`` to
  ``inet:web:post``.
  (`#1946 <https://github.com/vertexproject/synapse/pull/1946>`_)
- Add ``lang:translation`` to capture language translations of texts in a more
  comprehensive way than older ``lang`` model forms did. The ``lang:idiom``
  and ``lang:trans`` forms have been marked as deprecated.
  (`#1946 <https://github.com/vertexproject/synapse/pull/1946>`_)
- Update the ``ou`` model to add ``ou:attendee`` and ``ou:contest`` and
  ``ou:contest:result`` forms. Several secondary properties related to
  conference attendance have been marked deprecated.
  (`#1946 <https://github.com/vertexproject/synapse/pull/1946>`_)
- The ``ps:persona`` and ``ps:persona:has`` forms have been marked as
  deprecated.
  (`#1946 <https://github.com/vertexproject/synapse/pull/1946>`_)
- Add ``ps:contactlist`` to allow collecting multiple ``ps:contact`` nodes
  together.
  (`#1935 <https://github.com/vertexproject/synapse/pull/1935>`_)
- Allow the Storm Service cmdargs to accept any valid model type in the
  ``type`` value.
  (`#1923 <https://github.com/vertexproject/synapse/pull/1923>`_)
  (`#1936 <https://github.com/vertexproject/synapse/pull/1936>`_)
- Add ``>``, ``<``, ``>=`` and ``<=`` comparators for ``inet:ipv4`` type.
  (`#1938 <https://github.com/vertexproject/synapse/pull/1938>`_)
- Add configuration options to the Axon to limit the amount of data which
  can be stored in it. Add a configuration option the Cortex to limit
  the number of nodes which may be stored in a given Cortex.
  (`#1950 <https://github.com/vertexproject/synapse/pull/1950>`_)

Bugfixes
--------
- Fix a potential incorrect length for Spooled sets during fallback.
  (`#1937 <https://github.com/vertexproject/synapse/pull/1937>`_)
- Fix an issue with the Telepath ``Client`` object caching their ``Method``
  and ``GenrMethod`` attributes across re-connections of the underlying
  ``Proxy`` objects.
  (`#1939 <https://github.com/vertexproject/synapse/pull/1939>`_)
  (`#1941 <https://github.com/vertexproject/synapse/pull/1941>`_)
- Fix a bug where a temporary spool slab cleanup failed to remove all
  files from the filesystem that were created when the slab was made.
  (`#1940 <https://github.com/vertexproject/synapse/pull/1940>`_)
- Move exceptions which do not subclass ``SynErr`` out of ``synapse/exc.py``.
  (`#1947 <https://github.com/vertexproject/synapse/pull/1947>`_)
  (`#1951 <https://github.com/vertexproject/synapse/pull/1951>`_)


v2.9.2 - 2020-10-27
===================

Bugfixes
--------
- Fix an issue where a Cortex migrated from a `01x` release could
  overwrite entries in a Layer's historical nodeedit log.
  (`#1934 <https://github.com/vertexproject/synapse/pull/1934>`_)
- Fix an issue with the layer definition schema.
  (`#1927 <https://github.com/vertexproject/synapse/pull/1927>`_)


v2.9.1 - 2020-10-22
===================

Features and Enhancements
-------------------------
- Reuse existing an existing ``DateTime`` object when making time strings.
  This gives a slight performance boost for the ``synapse.lib.time.repr()``
  function.
  (`#1919 <https://github.com/vertexproject/synapse/pull/1919>`_)
- Remove deprecated use of ``loop`` arguments when calling ``asyncio``
  primitives.
  (`#1920 <https://github.com/vertexproject/synapse/pull/1920>`_)
- Allow Storm Services to define a minimum required Synapse version by the
  Cortex. If the Cortex is not running the minimum version, the Cortex will
  not load
  (`#1900 <https://github.com/vertexproject/synapse/pull/1900>`_)
- Only get the nxsindx in the ``Layer.storeNodeEdits()`` function if logging
  edits.
  (`#1926 <https://github.com/vertexproject/synapse/pull/1926>`_)
- Include the Node iden value in the ``CantDelNode`` exception when
  attempting to delete a Node failes due to existing references to the node.
  (`#1926 <https://github.com/vertexproject/synapse/pull/1926>`_)
- Take advantage of the LMDB append operation when possible.
  (`#1912 <https://github.com/vertexproject/synapse/pull/1912>`_)

Bugfixes
--------
- Fix an issues in the Telepath Client where an exception thrown by a onlink
  function could cause additional linkloop tasks to be spawned.
  (`#1924 <https://github.com/vertexproject/synapse/pull/1924>`_)


v2.9.0 - 2020-10-19
===================

Announcements
-------------

The ``v2.9.0`` Synapse release contains an automatic Cortex Layer data
migration. The updated layer storage format reduces disk and memory
requirements for a layer. It is recommended to test this process with a
backup of a Cortex before updating a production Cortex.

In order to maximize the space savings from the new layer storage format,
after the Cortex has been migrated to ``v2.9.0``, one can take a cold
backup of the Cortex and restore the Cortex from that backup. This
compacts the LMDB databases which back the Layers and reclaims disk space
as a result. This is an optional step; as LMDB will eventually re-use the
existing space on disk.

If there are any questions about this, please reach out in the Synapse Slack
channel so we can assist with any data migration questions.

Features and Enhancements
-------------------------
- Optimize the layer storage format for memory size and performance.
  (`#1877 <https://github.com/vertexproject/synapse/pull/1877>`_)
  (`#1885 <https://github.com/vertexproject/synapse/pull/1885>`_)
  (`#1899 <https://github.com/vertexproject/synapse/pull/1899>`_)
  (`#1917 <https://github.com/vertexproject/synapse/pull/1917>`_)
- Initial support Python 3.8 compatibility for the core Synapse library.
  Additional 3.8 support (such as wheels and Docker images) will be available
  in future releases.
  (`#1907 <https://github.com/vertexproject/synapse/pull/1907>`_)
- Add a read only Storm option to the Storm runtime. This option prevents
  executing commands or Stormtypes functions which may modify data in the
  Cortex.
  (`#1869 <https://github.com/vertexproject/synapse/pull/1869>`_)
  (`#1916 <https://github.com/vertexproject/synapse/pull/1916>`_)
- Allow the Telepath Dmon to disconnect clients using a ready status.
  (`#1881 <https://github.com/vertexproject/synapse/pull/1881>`_)
- Ensure that there is only one online backup of a Cell occurring at a time.
  (`#1883 <https://github.com/vertexproject/synapse/pull/1883>`_)
- Added ``.lower()``, ``.strip()``, ``.lstrip()`` and ``.rstrip()`` methods
  to the Stormtypes Str object. These behave like the Python ``str`` methods.
  (`#1886 <https://github.com/vertexproject/synapse/pull/1886>`_)
  (`#1906 <https://github.com/vertexproject/synapse/pull/1906>`_)
- When scraping text, defanged indicators are now refanged by default.
  (`#1888 <https://github.com/vertexproject/synapse/pull/1888>`_)
- Normalize read-only property declarations to use booleans in the data model.
  (`#1887 <https://github.com/vertexproject/synapse/pull/1887>`_)
- Add ``lift.byverb`` command to allow lifting nodes using a light edge verb.
  (`#1890 <https://github.com/vertexproject/synapse/pull/1890>`_)
- Add netblock and range lift helpers for ``inet:ipv6`` type, similar to the
  helpers for ``inet:ipv4``.
  (`#1869 <https://github.com/vertexproject/synapse/pull/1869>`_)
- Add a ``edges.del`` command to bulk remove light weight edges from nodes.
  (`#1893 <https://github.com/vertexproject/synapse/pull/1893>`_)
- The ``yield`` keyword in Storm now supports iterating over Stormtypes List
  and Set objects.
  (`#1898 <https://github.com/vertexproject/synapse/pull/1898>`_)
- Add ``ou:contract``, ``ou:industry`` and ``it:reveng:function:strings``
  forms to the data model.
  (`#1894 <https://github.com/vertexproject/synapse/pull/1894>`_)
- Add some display type-hinting to the data model for some string fields which
  may be multi-line fields.
  (`#1892 <https://github.com/vertexproject/synapse/pull/1892>`_)
- Add ``getFormCounts()`` API to the Stormtypes View and Layer objects.
  (`#1903 <https://github.com/vertexproject/synapse/pull/1903>`_)
- Allow Cortex layers to report their total size on disk. This is exposed in
  the Stormtypes ``Layer.pack()`` method for a layer.
  (`#1910 <https://github.com/vertexproject/synapse/pull/1910>`_)
- Expose the remote Storm Service name in the ``$lib.service.get()``
  Stormtypes API. This allows getting a service object without knowing
  the name of the service as it was locally added to a Cortex. Also add
  a ``$lib.service.has()`` API which allows checking to see if a service
  is available on a Cortex.
  (`#1908 <https://github.com/vertexproject/synapse/pull/1908>`_)
  (`#1915 <https://github.com/vertexproject/synapse/pull/1915>`_)
- Add regular expression (``~=``) and prefix matching (``^=``) expression
  comparators that can be used with logical expressions inside of Storm.
  (`#1906 <https://github.com/vertexproject/synapse/pull/1906>`_)
- Promote ``CoreApi.addFeedData()`` calls to tracked tasks which can be
  viewed and terminated.
  (`#1918 <https://github.com/vertexproject/synapse/pull/1918>`_)

Bugfixes
--------
- Fixed a Storm bug where attempting to access an undeclared variable
  silently fails. This will now raise a ``NoSuchVar`` exception. This
  is verified at runtime, not at syntax evaluation.
  (`#1916 <https://github.com/vertexproject/synapse/pull/1916>`_)
- Ensure that Storm HTTP APIs tear down the runtime task if the remote
  disconnects before consuming all of the messages.
  (`#1889 <https://github.com/vertexproject/synapse/pull/1889>`_)
- Fix an issue where the ``model.edge.list`` command could block the ioloop
  for large Cortex.
  (`#1890 <https://github.com/vertexproject/synapse/pull/1890>`_)
- Fix a regex based lifting bug.
  (`#1899 <https://github.com/vertexproject/synapse/pull/1899>`_)
- Fix a few possibly greedy points in the AST code which could have resulted
  in greedy CPU use.
  (`#1902 <https://github.com/vertexproject/synapse/pull/1902>`_)
- When pivoting across light edges, if the destination form was not a valid
  form, nothing happened. Now a StormRuntimeError is raised if the
  destination form is not valid.
  (`#1905 <https://github.com/vertexproject/synapse/pull/1905>`_)
- Fix an issue with spawn processes accessing lmdb databases after a slab
  resize event has occurred by the main process.
  (`#1914 <https://github.com/vertexproject/synapse/pull/1914>`_)
- Fix a slab teardown race seen in testing Python 3.8 on MacOS.
  (`#1914 <https://github.com/vertexproject/synapse/pull/1914>`_)

Deprecations
------------
- The ``0.1.x`` to ``2.x.x`` Migration tool and associated Cortex sync
  service has been removed from Synapse in the ``2.9.0`` release.

Improved Documentation
----------------------
- Clarify user documentation for pivot out and pivot in operations.
  (`#1891 <https://github.com/vertexproject/synapse/pull/1891>`_)
- Add a deprecation policy for Synapse Data model elements.
  (`#1895 <https://github.com/vertexproject/synapse/pull/1895>`_)
- Pretty print large data structures that may occur in the data model
  documentation.
  (`#1897 <https://github.com/vertexproject/synapse/pull/1897>`_)
- Update Storm Lift documentation to add the ``?=`` operator.
  (`#1904 <https://github.com/vertexproject/synapse/pull/1904>`_)


v2.8.0 - 2020-09-22
===================

Features and Enhancements
-------------------------
- Module updates to support generic organization identifiers, generic
  advertising identifiers, asnet6 and a few other secondary property additions.
  (`#1879 <https://github.com/vertexproject/synapse/pull/1879>`_)
- Update the Cell backup APIs to perform a consistent backup across all slabs
  for a Cell.
  (`#1873 <https://github.com/vertexproject/synapse/pull/1873>`_)
- Add support for a environment variable, ``SYN_LOCKMEM_DISABLE`` which will
  disable any memory locking of LMDB slabs.
  (`#1882 <https://github.com/vertexproject/synapse/pull/1882>`_)

Deprecations
------------

- The ``0.1.x`` to ``2.x.x`` Migration tool and and associated Cortex sync
  service will be removed from Synapse in the ``2.9.0`` release. In order to
  move forward to ``2.9.0``, please make sure that any Cortexes which still
  need to be migrated will first be migrated to ``2.8.x`` prior to attempting
  to use ``2.9.x``.

Improved Documentation
----------------------
- Add Synapse README content to the Pypi page. This was a community
  contribution from https://github.com/wesinator.  (`#1872
  <https://github.com/vertexproject/synapse/pull/1872>`_)


v2.7.3 - 2020-09-16
===================

Deprecations
------------
- The ``0.1.x`` to ``2.x.x`` Migration tool and and associated Cortex sync service will be removed from Synapse in
  the ``2.9.0`` release. In order to move forward to ``2.9.0``, please make sure that any Cortexes which still need to
  be migrated will first be migrated to ``2.8.x`` prior to attempting to use ``2.9.x``.
  (`#1880 <https://github.com/vertexproject/synapse/pull/1880>`_)

Bugfixes
--------
- Remove duplicate words in a comment. This was a community contribution from enadjoe.
  (`#1874 <https://github.com/vertexproject/synapse/pull/1874>`_)
- Fix a nested Nexus log event in Storm Service deletion. The ``del`` event causing Storm code execution could lead to
  nested Nexus events, which is incongruent with how Nexus change handlers work. This now spins off the Storm code in
  a free-running coroutine. This does change the service ``del`` semantics since any support Storm packages a service
  had may be removed by the time the handler executes.
  (`#1876 <https://github.com/vertexproject/synapse/pull/1876>`_)
- Fix an issue where the ``cull`` parameter was not being passed to the multiqueue properly when calling ``.gets()``
  on a Storm Types Queue object.
  (`#1876 <https://github.com/vertexproject/synapse/pull/1876>`_)
- Pin the ``nbconvert`` package to a known working version, as ``v6.0.0`` of that package broke the Synapse document
  generation by changing how templates work.
  (`#1876 <https://github.com/vertexproject/synapse/pull/1876>`_)
- Correct ``min`` and ``max`` integer examples in tagprop documentation and tests.
  (`#1878 <https://github.com/vertexproject/synapse/pull/1878>`_)


v2.7.2 - 2020-09-04
===================

Features and Enhancements
-------------------------
- Update tests for additional test code coverage. This was a community contribution from blackout.
  (`#1867 <https://github.com/vertexproject/synapse/pull/1867>`_)
- Add implicit links to documentation generated for Storm services, to allow for direct linking inside of documentation
  to specific Storm commands.
  (`#1866 <https://github.com/vertexproject/synapse/pull/1866>`_)
- Add future support for deprecating model elements in the Synapse data model. This support will produce client and
  server side warnings when deprecated model elements are used or loaded by custom model extensions or CoreModules.
  (`#1863 <https://github.com/vertexproject/synapse/pull/1863>`_)

Bugfixes
--------
- Update ``FixedCache.put()`` to avoid a cache miss. This was a community contribution from blackout.
  (`#1868 <https://github.com/vertexproject/synapse/pull/1868>`_)
- Fix the ioloop construction to be aware of ``SYN_GREEDY_CORO`` environment variable to put the ioloop into debug mode
  and log long-running coroutines.
  (`#1870 <https://github.com/vertexproject/synapse/pull/1870>`_)
- Fix how service permissions are checked in ``$lib.service.get()`` and ``$lib.service.wait()`` Storm library calls.
  These APIs now first check ``service.get.<service iden>`` before checking ``service.get.<service name>`` permissions.
  A successful ``service.get.<service name>`` check will result in a warning to the client and the server.
  (`#1871 <https://github.com/vertexproject/synapse/pull/1871>`_)


v2.7.1 - 2020-08-26
===================

Features and Enhancements
-------------------------
- Refactor an Axon unit test to make it easier to test alternative Axon implementations.
  (`#1862 <https://github.com/vertexproject/synapse/pull/1862>`_)

Bugfixes
--------
- Fix an issue in ``synapse.tools.cmdr`` where it did not ensure that the users Synapse directory was created before
  trying to open files in the directory.
  (`#1860 <https://github.com/vertexproject/synapse/issues/1860>`_)
  (`#1861 <https://github.com/vertexproject/synapse/pull/1861>`_)

Improved Documentation
----------------------
- Fix an incorrect statement in our documentation about the intrinsic Axon that a Cortex creates being remotely
  accessible.
  (`#1862 <https://github.com/vertexproject/synapse/pull/1862>`_)


v2.7.0 - 2020-08-21
===================

Features and Enhancements
-------------------------
- Add Telepath and HTTP API support to set and remove global Storm variables.
  (`#1846 <https://github.com/vertexproject/synapse/pull/1846>`_)
- Add Cell level APIs for performing the backup of a Cell. These APIs are exposed inside of a Cortex via a Storm Library.
  (`#1844 <https://github.com/vertexproject/synapse/pull/1844>`_)
- Add support for Cron name and doc fields to be editable.
  (`#1848 <https://github.com/vertexproject/synapse/pull/1848>`_)
- Add support for Runtime-only (``runt``) nodes in the PivotOut operation (``-> *``).
  (`#1851 <https://github.com/vertexproject/synapse/pull/1851>`_)
- Add ``:nicks`` and ``:names`` secondary properties to ``ps:person`` and ``ps:persona`` types.
  (`#1852 <https://github.com/vertexproject/synapse/pull/1852>`_)
- Add a new ``ou:position`` form and a few associated secondary properties.
  (`#1849 <https://github.com/vertexproject/synapse/pull/1849>`_)
- Add a step to the CI build process to smoke test the sdist and wheel packages before publishing them to PyPI.
  (`#1853 <https://github.com/vertexproject/synapse/pull/1853>`_)
- Add support for representing ``nodedata`` in the command hinting for Storm command implementations and expose it on
  the ``syn:cmd`` runt nodes.
  (`#1850 <https://github.com/vertexproject/synapse/pull/1850>`_)
- Add package level configuration data to Storm Packages in the ``modconf`` value of a package definition. This is added
  to the runtime variables when a Storm package is imported, and includes the ``svciden`` for packages which come from
  Storm Services.
  (`#1855 <https://github.com/vertexproject/synapse/pull/1855>`_)
- Add support for passing HTTP params when using ``$lib.inet.http.*`` functions to make HTTP calls in Storm.
  (`#1856 <https://github.com/vertexproject/synapse/pull/1856>`_)
- Log Storm queries made via the ``callStorm()`` and ``count()`` APIs.
  (`#1857 <https://github.com/vertexproject/synapse/pull/1857>`_)

Bugfixes
--------
- Fix an issue were some Storm filter operations were not yielding CPU time appropriately.
  (`#1845 <https://github.com/vertexproject/synapse/pull/1845>`_)

Improved Documentation
----------------------
- Remove a reference to deprecated ``eval()`` API from quickstart documentation.
  (`#1858 <https://github.com/vertexproject/synapse/pull/1858>`_)


v2.6.0 - 2020-08-13
===================

Features and Enhancements
-------------------------

- Support ``+hh:mm`` and ``+hh:mm`` timezone offset parsing when normalizing ``time`` values.
  (`#1833 <https://github.com/vertexproject/synapse/pull/1833>`_)
- Enable making mirrors of Cortex mirrors work.
  (`#1836 <https://github.com/vertexproject/synapse/pull/1836>`_)
- Remove read-only properties from ``inet:flow`` and ``inet:http:request`` forms.
  (`#1840 <https://github.com/vertexproject/synapse/pull/1840>`_)
- Add support for setting nodedata and light edges in the ``syn.nodes`` ingest format.
  (`#1839 <https://github.com/vertexproject/synapse/pull/1839>`_)
- Sync the LMDB Slab replay log if it gets too large instead of waiting for a force commit operation.
  (`#1838 <https://github.com/vertexproject/synapse/pull/1838>`_)
- Make the Agenda unit tests an actual component test to reduce test complexity.
  (`#1837 <https://github.com/vertexproject/synapse/pull/1837>`_)
- Support glob patterns when specifying files to upload to an Axon with ``synapse.tools.pushfile``.
  (`#1837 <https://github.com/vertexproject/synapse/pull/1837>`_)
- Use the node edit metadata to store and set the ``.created`` property on nodes, so that mirrors of Cortexes have
  consistent ``.created`` timestamps.
  (`#1765 <https://github.com/vertexproject/synapse/pull/1765>`_)
- Support parent runtime variables being accessed during the execution of a ``macro.exec`` command.
  (`#1841 <https://github.com/vertexproject/synapse/pull/1841>`_)
- Setting tags from variable values in Storm now calls ``s_stormtypes.tostr()`` on the variable value.
  (`#1843 <https://github.com/vertexproject/synapse/pull/1843>`_)

Bugfixes
--------
- The Storm ``tree`` command now catches the Synapse ``RecursionLimitHit`` error and raises a ``StormRuntimeError``
  instead. The ``RecursionLimitHit`` being raised by that command was, in practice, confusing.
  (`#1832 <https://github.com/vertexproject/synapse/pull/1832>`_)
- Resolve memory leak issues related to callStorm and Base object teardowns with exceptions.
  (`#1842 <https://github.com/vertexproject/synapse/pull/1842>`_)


v2.5.1 - 2020-08-05
===================

Features and Enhancements
-------------------------

- Add performance oriented counting APIs per layer, and expose them via Stormtypes.
  (`#1813 <https://github.com/vertexproject/synapse/pull/1813>`_)
- Add the ability to clone a layer, primarily for benchmarking and testing purposes.
  (`#1819 <https://github.com/vertexproject/synapse/pull/1819>`_)
- Update the benchmark script to run on remote Cortexes.
  (`#1829 <https://github.com/vertexproject/synapse/pull/1829>`_)

Bugfixes
--------
- Sanitize passwords from Telepath URLs during specific cases where the URL may be logged.
  (`#1830 <https://github.com/vertexproject/synapse/pull/1830>`_)

Improved Documentation
----------------------

- Fix a few typos in docstrings.
  (`#1831 <https://github.com/vertexproject/synapse/pull/1831>`_)


v2.5.0 - 2020-07-30
===================

Features and Enhancements
-------------------------

- Refactor the Nexus to remove leadership awareness.
  (`#1785 <https://github.com/vertexproject/synapse/pull/1785>`_)
- Add support for client-side certificates in Telepath for SSL connections.
  (`#1785 <https://github.com/vertexproject/synapse/pull/1785>`_)
- Add multi-dir support for CertDir.
  (`#1785 <https://github.com/vertexproject/synapse/pull/1785>`_)
- Add a ``--no-edges`` option to the Storm ``graph`` command.
  (`#1805 <https://github.com/vertexproject/synapse/pull/1805>`_)
- Add ``:doc:url`` to the ``syn:tag`` form to allow recording a URL which may document a tag.
  (`#1805 <https://github.com/vertexproject/synapse/pull/1805>`_)
- Add ``CoreApi.reqValidStorm()`` and a ``/api/v1/reqvalidstorm`` Cortex HTTPAPI endpoint to validate that a given
  Storm query is valid Storm syntax.
  (`#1806 <https://github.com/vertexproject/synapse/pull/1806>`_)
- Support Unicode white space in Storm. All Python `\s` (Unicode white space + ASCII separators) is now treated as
  white space in Storm.
  (`#1812 <https://github.com/vertexproject/synapse/pull/1812>`_)
- Refactor how StormLib and StormPrim objects access their object locals, and add them to a global registry to support
  runtime introspection of those classes.
  (`#1804 <https://github.com/vertexproject/synapse/pull/1804>`_)
- Add smoke tests for the Docker containers built in CircleCI, as well as adding Docker healthchecks to the Cortex,
  Axon and Cryotank images.
  (`#1815 <https://github.com/vertexproject/synapse/pull/1815>`_)
- Initialize the names of the default view and layer in a fresh Cortex to ``default``.
  (`#1814 <https://github.com/vertexproject/synapse/pull/1814>`_)
- Add HTTPAPI endpoints for the Axon to upload, download and check for the existend of files.
  (`#1817 <https://github.com/vertexproject/synapse/pull/1817>`_)
  (`#1822 <https://github.com/vertexproject/synapse/pull/1822>`_)
  (`#1824 <https://github.com/vertexproject/synapse/pull/1824>`_)
  (`#1825 <https://github.com/vertexproject/synapse/pull/1825>`_)
- Add a ``$lib.bytes.has()`` API to check if the Axon a Cortex is configured with knows about a given sha256 value.
  (`#1822 <https://github.com/vertexproject/synapse/pull/1822>`_)
- Add initial model for prices, currences, securities and exchanges.
  (`#1820 <https://github.com/vertexproject/synapse/pull/1820>`_)
- Add a ``:author`` field to the ``it:app:yara:rule`` form.
  (`#1821 <https://github.com/vertexproject/synapse/pull/1821>`_)
- Add an experimental option to set the NexusLog as a ``map_async`` slab.
  (`#1826 <https://github.com/vertexproject/synapse/pull/1826>`_)
- Add an initial transportation model.
  (`#1816 <https://github.com/vertexproject/synapse/pull/1816>`_)
- Add the ability to dereference an item, from a list of items, in Storm via index.
  (`#1827 <https://github.com/vertexproject/synapse/pull/1827>`_)
- Add a generic ``$lib.inet.http.request()`` Stormlib function make HTTP requests with arbitrary verbs.
  (`#1828 <https://github.com/vertexproject/synapse/pull/1828>`_)

Bugfixes
--------
- Fix an issue with the Docker builds for Synapse where the package was not being installed properly.
  (`#1815 <https://github.com/vertexproject/synapse/pull/1815>`_)

Improved Documentation
----------------------

- Update documentation for deploying Cortex mirrors.
  (`#1811 <https://github.com/vertexproject/synapse/pull/1811>`_)
- Add automatically generated documentation for all the Storm ``$lib...`` functions and Storm Primitive types.
  (`#1804 <https://github.com/vertexproject/synapse/pull/1804>`_)
- Add examples of creating a given Form to the automatically generated documentation for the automatically generated
  datamodel documentation.
  (`#1818 <https://github.com/vertexproject/synapse/pull/1818>`_)
- Add additional documentation for Cortex automation.
  (`#1797 <https://github.com/vertexproject/synapse/pull/1797>`_)
- Add Devops documentation for the list of user permissions relevant to a Cell, Cortex and Axon.
  (`#1823 <https://github.com/vertexproject/synapse/pull/1823>`_)


v2.4.0 - 2020-07-15
===================

Features and Enhancements
-------------------------

- Update the Storm ``scrape`` command to make ``refs`` light edges, instead of ``edge:refs`` nodes.
  (`#1801 <https://github.com/vertexproject/synapse/pull/1801>`_)
  (`#1803 <https://github.com/vertexproject/synapse/pull/1803>`_)
- Add ``:headers`` and ``:response:headers`` secondary properties to the ``inet:http:request`` form as Array types, so
  that requests can be directly linked to headers.
  (`#1800 <https://github.com/vertexproject/synapse/pull/1800>`_)
- Add ``:headers`` secondary property to the ``inet:email:messaage`` form as Array types, so that messages can be
  directly linked to headers.
  (`#1800 <https://github.com/vertexproject/synapse/pull/1800>`_)
- Add additional model elements to support recording additional data for binary reverse engineering.
  (`#1802 <https://github.com/vertexproject/synapse/pull/1802>`_)


v2.3.1 - 2020-07-13
===================

Bugfixes
--------
- Prohibit invalid rules from being set on a User or Role object.
  (`#1798 <https://github.com/vertexproject/synapse/pull/1798>`_)


v2.3.0 - 2020-07-09
===================

Features and Enhancements
-------------------------

- Add ``ps.list`` and ``ps.kill`` commands to Storm, to allow introspecting the runtime tasks during
  (`#1782 <https://github.com/vertexproject/synapse/pull/1782>`_)
- Add an ``autoadd`` mode to Storm, which will extract basic indicators and make nodes from them when executed. This is
  a superset of the behavior in the ``lookup`` mode.
  (`#1795 <https://github.com/vertexproject/synapse/pull/1795>`_)
- Support skipping directories in the ``synapse.tools.backup`` tool.
  (`#1792 <https://github.com/vertexproject/synapse/pull/1792>`_)
- Add prefix based lifting to the Hex type.
  (`#1796 <https://github.com/vertexproject/synapse/pull/1796>`_)

Bugfixes
--------
- Fix an issue for prop pivot out syntax where the source data is an array type.
  (`#1794 <https://github.com/vertexproject/synapse/pull/1794>`_)

Improved Documentation
----------------------

- Add Synapse data model background on light edges and update the Storm data modification and pivot references for light
  edges.
  (`#1784 <https://github.com/vertexproject/synapse/pull/1784>`_)
- Add additional terms to the Synapse glossary.
  (`#1784 <https://github.com/vertexproject/synapse/pull/1784>`_)
- Add documentation for additional Storm commands.
  (`#1784 <https://github.com/vertexproject/synapse/pull/1784>`_)
- Update documentation for Array types.
  (`#1791 <https://github.com/vertexproject/synapse/pull/1791>`_)


v2.2.2 - 2020-07-03
===================

Features and Enhancements
-------------------------

- Add some small enhancements to the Cortex benchmarking script.
  (`#1790 <https://github.com/vertexproject/synapse/pull/1790>`_)

Bugfixes
--------

- Fix an error in the help for the ``macro.del`` command.
  (`#1786 <https://github.com/vertexproject/synapse/pull/1786>`_)
- Fix rule indexing for the ``synapse.tools.cellauth`` tool to correctly print the rule offsets.
  (`#1787 <https://github.com/vertexproject/synapse/pull/1787>`_)
- Remove extraneous output from the Storm Parser output.
  (`#1789 <https://github.com/vertexproject/synapse/pull/1789>`_)
- Rewrite the language (and private APIs) for the Storm ``model.edge`` related commands to remove references to extended
  properties. That was confusing language which was unclear for users.
  (`#1789 <https://github.com/vertexproject/synapse/pull/1789>`_)
- During 2.0.0 migrations, ensure that Cortex and Layer idens are unique; and make minimum 0.1.6 version requirement for
  migration.
  (`#1788 <https://github.com/vertexproject/synapse/pull/1788>`_)


v2.2.1 - 2020-06-30
===================

Bugfixes
--------

- The Axon test suite was missing a test for calling ``Axon.get()`` on a file it did not have. This is now included in
  the test suite.
  (`#1783 <https://github.com/vertexproject/synapse/pull/1783>`_)

Improved Documentation
----------------------

- Improve Synapse devops documentation hierarchy. Add note about Cell directories being persistent.
  (`#1781 <https://github.com/vertexproject/synapse/pull/1781>`_)


v2.2.0 - 2020-06-26
===================

Features and Enhancements
-------------------------

- Add a ``postAnit()`` callback to the ``synapse.lib.base.Base()`` object which is called *after* the ``__anit__()``
  call chain is completed, but before ``Base.anit()`` returns the object instance to the caller. This is used by the
  Cell to defer certain Nexus actions until the Cell has completed initializing all of its instance attributes.
  (`#1768 <https://github.com/vertexproject/synapse/pull/1768>`_)
- Make ``synapse.lib.msgpack.en()`` raise a ``SynErr.NotMsgpackSafe`` exception instead of passing through the
  exception raised by msgpack.
  (`#1768 <https://github.com/vertexproject/synapse/pull/1768>`_)

Bugfixes
--------

- Add a missing ``toprim()`` call in ``$lib.globals.set()``.
  (`#1778 <https://github.com/vertexproject/synapse/pull/1778>`_)
- Fix an issue in the quickstart documentation related to permissions. Thank you ``enadjoe`` for your contribution.
  (`#1779 <https://github.com/vertexproject/synapse/pull/1779>`_)
- Fix an Cell/Cortex startup issue which caused errors when starting up a Cortex when the last Nexus event was
  replayed. This has a secondary effect that Cell implementers cannot be making Nexus changes during the ``__anit__``
  methods.
  (`#1768 <https://github.com/vertexproject/synapse/pull/1768>`_)

Improved Documentation
----------------------

- Add a minimal Storm Service example to the developer documentation.
  (`#1776 <https://github.com/vertexproject/synapse/pull/1776>`_)
- Reorganize the Synapse User Guide into a more hierarchical format.
  (`#1777 <https://github.com/vertexproject/synapse/pull/1777>`_)
- Fill out additional glossary items.
  (`#1780 <https://github.com/vertexproject/synapse/pull/1780>`_)


v2.1.2 - 2020-06-18
===================

Bugfixes
--------

- Disallow command and bare string contensts from starting with ``//`` and ``/*`` in Storm syntax.
  (`#1769 <https://github.com/vertexproject/synapse/pull/1769>`_)


v2.1.1 - 2020-06-16
===================

Bugfixes
--------

- Fix an issue in the autodoc tool which failed to account for Storm Service commands without cmdargs.
  (`#1775 <https://github.com/vertexproject/synapse/pull/1775>`_)


v2.1.0 - 2020-06-16
===================

Features and Enhancements
-------------------------

- Add information about light edges to graph carving output.
  (`#1762 <https://github.com/vertexproject/synapse/pull/1762>`_)
- Add a ``geo:json`` type and ``geo:place:geojson`` property to the model.
  (`#1759 <https://github.com/vertexproject/synapse/pull/1759>`_)
- Add the ability to record documentation for light edges.
  (`#1760 <https://github.com/vertexproject/synapse/pull/1760>`_)
- Add the ability to delete and set items inside of a MultiQueue.
  (`#1766 <https://github.com/vertexproject/synapse/pull/1766>`_)

Improved Documentation
----------------------

- Refactor ``v2.0.0`` changelog documentation.
  (`#1763 <https://github.com/vertexproject/synapse/pull/1763>`_)
- Add Vertex branding to the Synapse documentation.
  (`#1767 <https://github.com/vertexproject/synapse/pull/1767>`_)
- Update Backups documentation in the Devops guide.
  (`#1764 <https://github.com/vertexproject/synapse/pull/1764>`_)
- Update the autodoc tool to generate documentation for Cell confdefs and StormService information.
  (`#1772 <https://github.com/vertexproject/synapse/pull/1772>`_)
- Update to separate the devops guides into distinct sections.
  (`#1772 <https://github.com/vertexproject/synapse/pull/1772>`_)
- Add documentation for how to do boot-time configuration for a a Synapse Cell.
  (`#1772 <https://github.com/vertexproject/synapse/pull/1772>`_)
- Remove duplicate information about backups.
  (`#1774 <https://github.com/vertexproject/synapse/pull/1774>`_)

v2.0.0 - 2020-06-08
===================

Initial 2.0.0 release. See :ref:`200_changes` for notable new features and changes, as well as backwards incompatible
changes.


v0.1.X Changelog
================

For the Synapse 0.1.x changelog, see `01x Changelog`_ located in the v0.1.x documentation.

.. _01x Changelog: ../../01x/synapse/changelog.html
