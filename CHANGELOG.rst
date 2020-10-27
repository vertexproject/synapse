.. vim: set textwidth=79

*****************
Synapse Changelog
*****************


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
- Add support for Runtime-only (``runt``) nodes in the PivotOut operation (``-> * ``).
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
