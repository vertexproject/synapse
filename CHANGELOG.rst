.. vim: set textwidth=79

.. _changelog:

*****************
Synapse Changelog
*****************

v2.189.0 - 2024-11-21
=====================

Model Changes
-------------
- Added ``:technique`` to the ``risk:vulnerable`` form to represent a node
  being susceptible to a technique.
  (`#4006 <https://github.com/vertexproject/synapse/pull/4006>`_)
- See :ref:`userguide_model_v2_189_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Updated the ``pkg.list`` command to use a tabular printer and added a
  ``--verbose`` option to view build time.
  (`#4007 <https://github.com/vertexproject/synapse/pull/4007>`_)

v2.188.1 - 2024-11-13
=====================

Bugfixes
--------
- Fix an issue in the type schema enforcement of a Cell's Drive where a list of
  types for a field would cause schema checking to always fail after a Cell
  reboot.
  (`#4002 <https://github.com/vertexproject/synapse/pull/4002>`_)

v2.188.0 - 2024-11-08
=====================

Model Changes
-------------
- Added ``meta:aggregate`` to represent aggregate counts.
  (`#3968 <https://github.com/vertexproject/synapse/pull/3968>`_)
- Added ``risk:outage`` to represent outage events.
  (`#3968 <https://github.com/vertexproject/synapse/pull/3968>`_)
- Added ``:reporter`` and ``:reporter:name`` to the ``ou:industry`` form to
  allow reporter specific industries.
  (`#3968 <https://github.com/vertexproject/synapse/pull/3968>`_)
- Added ``file:attachment`` to unify file attachment types.
  (`#3969 <https://github.com/vertexproject/synapse/pull/3969>`_)
- Added ``ou:candidate`` to track job applications and candidates.
  (`#3969 <https://github.com/vertexproject/synapse/pull/3969>`_)
- Added ``:src:txfiles`` and ``:dst:txfiles`` to ``inet:flow`` to capture
  transferred files.
  (`#3969 <https://github.com/vertexproject/synapse/pull/3969>`_)
- Added ``inet:service:emote`` to track account emotes.
  (`#3988 <https://github.com/vertexproject/synapse/pull/3988>`_)
- Added ``inet:service:relationship`` to track service object relationships.
  (`#3988 <https://github.com/vertexproject/synapse/pull/3988>`_)
- Add a ``uses`` light edge between ``ou:technique`` and ``risk:vuln`` forms.
  (`#3994 <https://github.com/vertexproject/synapse/pull/3994>`_)
- See :ref:`userguide_model_v2_188_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add support for `ndef` types in embed property definitions.
  (`#3979 <https://github.com/vertexproject/synapse/pull/3979>`_)
- Add ``children()`` method on Storm ``view`` objects.
  (`#3984 <https://github.com/vertexproject/synapse/pull/3984>`_)
- Update the ``cron.list`` command to use a tabular printer for table
  generation.
  (`#3986 <https://github.com/vertexproject/synapse/pull/3986>`_)
- Add ``$lib.model.ext.addType()`` and ``$lib.model.ext.delType()`` Storm APIs
  for managing extended model types.
  (`#3989 <https://github.com/vertexproject/synapse/pull/3989>`_)
- Allow optionally specifying typeopts to the ``Cortex.getPropNorm`` and
  ``Cortex.getTypeNorm`` APIs.
  (`#3992 <https://github.com/vertexproject/synapse/pull/3992>`_)
- Update async scrape APIs to use the forked process pool rather than spawned
  processes.
  (`#3993 <https://github.com/vertexproject/synapse/pull/3993>`_)

Bugfixes
--------
- Fixed an issue where creating a cron job with a stable iden could overlap
  with existing authgates.
  (`#3981 <https://github.com/vertexproject/synapse/pull/3981>`_)
- Fixed an issue where Nexus events from updated mirrors pushed to a leader on
  an older version which did not yet support those events were not handled
  correctly.
  (`#3985 <https://github.com/vertexproject/synapse/pull/3985>`_)
- Fix an issue where extended model types could be deleted while still in use
  by other extended model types.
  (`#3989 <https://github.com/vertexproject/synapse/pull/3989>`_)
- Fix an issue where the Storm ``background`` and ``parallel`` commands could
  incorrectly throw NoSuchVar exceptions when validating query arguments.
  (`#3991 <https://github.com/vertexproject/synapse/pull/3991>`_)

v2.187.0 - 2024-11-01
=====================

Automatic Migrations
--------------------
- WARNING - It is strongly advised to perform a backup before upgrading to or
  above this version. The ``it:sec:cpe`` migration described below WILL remove
  invalid ``it:sec:cpe`` and some associated nodes from the Cortex.

  Migrate invalid ``it:sec:cpe`` nodes if possible. Migration of these nodes
  will only be successful if one of the CPE 2.3 (primary property) or the CPE
  2.2 (``:v2_2``) strings are valid CPEs. If both CPE strings are invalid, the
  node will be removed from the Cortex and stored in a Cortex queue
  (``model_0_2_31:nodes``).

  The structure of items in this queue is opaque. The intent is for Power-Ups
  to be able to process the queue in an attempt to fix the invalid nodes on a
  per Power-Up basis (the idea being that Power-Up data vendors probably make
  the same mistake consistently).

  During migration or removal of invalid ``it:sec:cpe`` nodes, referencing
  nodes with readonly properties will be removed and also stored in the queue.
  We are unable to automatically migrate these nodes due to the dynamic nature
  of their construction.
  (`#3918 <https://github.com/vertexproject/synapse/pull/3918>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Update the parsing of CPE 2.2 and CPE 2.3 strings to be strict according
  to the CPE specification (NISTIR 7695).
  (`#3918 <https://github.com/vertexproject/synapse/pull/3918>`_)
- See :ref:`userguide_model_v2_187_0` for more detailed model changes.

Features and Enhancements
-------------------------

- Update storm ``queue.put()`` and ``queue.puts()`` methods to return the
  offset of the queued item.
  (`#3918 <https://github.com/vertexproject/synapse/pull/3918>`_)
- Add CPE migration helper functions. The following functions were added to
  assist with invalid nodes that were queued as part of the CPE model
  migration: ``$lib.model.migration.s.model_0_2_31.listNodes()``,
  ``$lib.model.migration.s.model_0_2_31.printNode()``, and
  ``$lib.model.migration.s.model_0_2_31.repairNode()``
  (`#3918 <https://github.com/vertexproject/synapse/pull/3918>`_)

v2.186.0 - 2024-10-29
=====================

Model Changes
-------------
- Added ``risk:tool:software:id`` to model an ID for a tool.
  (`#3970 <https://github.com/vertexproject/synapse/pull/3970>`_)
- See :ref:`userguide_model_v2_186_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Update tag type normalization to verify the tag is valid for any configured
  tag model specifications in the Cortex. Tags which fail validation will now
  raise a ``BadTypeValu`` exception rather than a ``BadTag`` exception.
  (`#3973 <https://github.com/vertexproject/synapse/pull/3973>`_)
- Implemented ``synapse.tools.snapshot`` CLI tool which can be used to pause
  edits and sync dirty buffers to disk to safely generate a volume snaphot.
  (`#3977 <https://github.com/vertexproject/synapse/pull/3977>`_)

Bugfixes
--------
- Fixed several CLI commands usage output formatting.
  (`#3977 <https://github.com/vertexproject/synapse/pull/3977>`_)

v2.185.0 - 2024-10-25
=====================
                                              
Model Changes                                                                               
-------------                                                                               
- Added ``proj:task`` interface to ensure consistent properties on task-like
  forms.                                                                                    
  (`#3962 <https://github.com/vertexproject/synapse/pull/3962>`_)           
- Added ``doc:document`` interface to ensure consistent properties on document
  forms.                                                                                    
  (`#3962 <https://github.com/vertexproject/synapse/pull/3962>`_)      
- Added ``ou:enacted`` to track an organization enacting policies and
  standards.                                                                                
  (`#3962 <https://github.com/vertexproject/synapse/pull/3962>`_)              
- Added ``doc:policy`` and ``doc:standard`` forms to model policies and
  standards.                                                                                
  (`#3962 <https://github.com/vertexproject/synapse/pull/3962>`_)            
- See :ref:`userguide_model_v2_185_0` for more detailed model changes. 

Features and Enhancements
-------------------------
- Added support for ``syn:user`` and ``syn:role`` types to be converted to/from
  names.
  (`#3959 <https://github.com/vertexproject/synapse/pull/3959>`_)
- Added ``$lib.repr()`` to convert a system mode value to a display mode
  string.
  (`#3959 <https://github.com/vertexproject/synapse/pull/3959>`_)
- Added support for templates in interface doc strings.
  (`#3962 <https://github.com/vertexproject/synapse/pull/3962>`_)
- Added ``storm.lib.stix.export.maxsize`` permission to allow STIX export
  configurations to set maxsize > 10,000.
  (`#3963 <https://github.com/vertexproject/synapse/pull/3963>`_)
- Added syntax for lifting nodes by embedded property values.
  (`#3964 <https://github.com/vertexproject/synapse/pull/3964>`_)
- Add the ``mirror`` URL to the output of the ``getCellInfo()`` APIs to
  indicate which service is being followed for change events. This URL has
  password information sanitized from it.
  (`#3966 <https://github.com/vertexproject/synapse/pull/3966>`_)
- Improve text alignment with multiline command argument help descriptions.
  (`#3967 <https://github.com/vertexproject/synapse/pull/3967>`_)
- Update Storm grammar to allow embed queries in JSON expressions.
  (`#3972 <https://github.com/vertexproject/synapse/pull/3972>`_)

Bugfixes
--------
- Fixed issue where interfaces took precedence over properties declared on a
  form.
  (`#3962 <https://github.com/vertexproject/synapse/pull/3962>`_)
- Fixed incorrect coercion behavior in ``$lib.dict.pop()`` and docs for
  ``$lib.dict.has()``.
  (`#3965 <https://github.com/vertexproject/synapse/pull/3965>`_)
- Update ``synapse.tools.promote`` to prevent a graceful promotion of a service
  where a detectable leadership schism would occur.
  (`#3966 <https://github.com/vertexproject/synapse/pull/3966>`_)
- Fixed an issue where list variables could be passed into the ``background``
  command or Storm Dmons in such a way that they could not be modified.
  (`#3971 <https://github.com/vertexproject/synapse/pull/3971>`_)
  (`#3976 <https://github.com/vertexproject/synapse/pull/3976>`_)

v2.184.0 - 2024-10-18
=====================

Model Changes
-------------
- Added ``ou:requirement:type`` taxonomy property to track requirement types.
  (`#3954 <https://github.com/vertexproject/synapse/pull/3954>`_)
- Added ``it:app:snort:hit:dropped`` property to track when hits result in the
  traffic being dropped.
  (`#3954 <https://github.com/vertexproject/synapse/pull/3954>`_)
- Added ``ou:vitals:budget`` property to track budget allocations.
  (`#3954 <https://github.com/vertexproject/synapse/pull/3954>`_)
- Added ``risk:mitigation:type`` as a ``taxonomy`` to track mitigation types.
  (`#3957 <https://github.com/vertexproject/synapse/pull/3957>`_)
- Added ``ou:asset`` form and associated properties to model organizational
  asset tracking.
  (`#3957 <https://github.com/vertexproject/synapse/pull/3957>`_)
- See :ref:`userguide_model_v2_184_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add ``$lib.graph.revoke()`` API for revoking user/role permissions on a graph
  projection.
  (`#3950 <https://github.com/vertexproject/synapse/pull/3950>`_)
- Mark all functions in a deprecated Storm library as deprecated.
  (`#3952 <https://github.com/vertexproject/synapse/pull/3952>`_)

Bugfixes
--------
- Fix a Storm bug where a runtsafe list unpacking operation which was executed
  per-node would be executed one additional time after all nodes had finished
  moving through the pipeline.
  (`#3949 <https://github.com/vertexproject/synapse/pull/3949>`_)
- Fix an issue where the default permission level specified when adding a graph
  projection was overwritten.
  (`#3950 <https://github.com/vertexproject/synapse/pull/3950>`_)
- Fixed an issue where extended model forms which implemented interfaces could
  not be removed due to inherited props.
  (`#3958 <https://github.com/vertexproject/synapse/pull/3958>`_)

Deprecations
------------
- Deprecate ``$lib.inet.whois.guid``.
  (`#3951 <https://github.com/vertexproject/synapse/pull/3951>`_)

v2.183.0 - 2024-10-09
=====================

Model Changes
-------------
- Fix an issue where the ``:path:base``, ``:path:dir``, and ``:path:ext``
  secondary properties were marked readonly on the ``it:fs:file``,
  ``it:exec:file:add``, ``it:exec:file:del``, ``it:exec:file:read``, and
  ``it:exec:file:write`` forms.
  (`#3942 <https://github.com/vertexproject/synapse/pull/3942>`_)
- See :ref:`userguide_model_v2_183_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Expose Stormlib deprecation status from the Python API.
  (`#3929 <https://github.com/vertexproject/synapse/pull/3929>`_)
- Add ``$lib.random.generator()`` to get a random number generator in Storm.
  (`#3945 <https://github.com/vertexproject/synapse/pull/3945>`_)

Bugfixes
--------
- Tag add operations with the try syntax ( ``+?#`` ) now catch BadTag
  exceptions raised by tags which are not valid for a defined tag model.
  (`#3941 <https://github.com/vertexproject/synapse/pull/3941>`_)
- Added ``task.get`` and ``task.del`` permissions declarations so they get
  included in the output of the ``auth.perms.list`` command.
  (`#3944 <https://github.com/vertexproject/synapse/pull/3944>`_)

Improved documentation
----------------------
- Clarify parts of the Storm automation guide.
  (`#3938 <https://github.com/vertexproject/synapse/pull/3938>`_)
- Clarify Storm type specific documentation for ``guid`` types.
  (`#3939 <https://github.com/vertexproject/synapse/pull/3939>`_)

v2.182.0 - 2024-09-27
=====================

Features and Enhancements
-------------------------
- Update the allowed version of the ``packaging`` and ``xxhash`` libraries.
  (`#3931 <https://github.com/vertexproject/synapse/pull/3931>`_)
- Allow a user to specify a role iden when creating a role with the
  ``$lib.auth.role.add()`` Storm API.
  (`#3932 <https://github.com/vertexproject/synapse/pull/3932>`_)

Bugfixes
--------
- Fix an issue in the ``merge`` command where errors in establishing the node
  in the parent view could result in an exception. These errors are now
  surfaced as warnings in the runtime, and the node will be skipped.
  (`#3925 <https://github.com/vertexproject/synapse/pull/3925>`_)
- Fix an issue where the Cell would log that the free space write hold was
  removed irrespective of the write hold reason.
  (`#3934 <https://github.com/vertexproject/synapse/pull/3934>`_)

v2.181.0 - 2024-09-25
=====================

Automatic Migrations
--------------------
- Update ``inet:ipv4`` and ``inet:ipv6`` sub properties for values affected by
  IANA Special Purpose Registry updates.
  (`#3902 <https://github.com/vertexproject/synapse/pull/3902>`_)
- A small migration to populate ``ou:industry:type:taxonomy`` nodes from
  existing ``ou:industry:type`` values.
  (`#3912 <https://github.com/vertexproject/synapse/pull/3912>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- The ``inet:rfc2822:addr`` type now rejects malformed inputs which could cause
  incorrect email addresses to be recorded.
  (`#3902 <https://github.com/vertexproject/synapse/pull/3902>`_)
- The ``inet:ipv4:type`` and ``inet:ipv6:type`` secondary properties now
  reflect updated behaviors from the IANA Special Purposes registries.
  (`#3902 <https://github.com/vertexproject/synapse/pull/3902>`_)
- Added ``math:algorithm`` form to model algorithms and link to generated
  output.
  (`#3906 <https://github.com/vertexproject/synapse/pull/3906>`_)
- Added ``:mitigated=<bool>`` and ``:mitigations=[<risk:mitigation>]``
  properties to the ``risk:vulnerable`` form to track mitigations used to
  address vulnerable nodes.
  (`#3910 <https://github.com/vertexproject/synapse/pull/3910>`_)
  (`#3911 <https://github.com/vertexproject/synapse/pull/3911>`_)
- Added ``ou:org:motto`` and ``ou:campaign:slogan`` properties and the
  ``lang:phrase`` form.
  (`#3915 <https://github.com/vertexproject/synapse/pull/3915>`_)
- See :ref:`userguide_model_v2_181_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Storm lists now have a ``remove`` method that can be used to remove a single
  item from the list without having to iterate through the list.
  (`#3815 <https://github.com/vertexproject/synapse/pull/3815>`_)
- Added ``opts`` field to ``model:type`` Storm type. This field contains the
  property type options as defined in the data model.
  (`#3815 <https://github.com/vertexproject/synapse/pull/3815>`_)
- Updated Storm coverage tracker to support ``pragma: no cover`` for ignoring
  single lines of code and ``pragma: no cover start``/``pragma: no cover stop``
  for ignoring multi-line blocks of Storm code.
  (`#3815 <https://github.com/vertexproject/synapse/pull/3815>`_)
- Make the ``Slab.putmulti()`` API an async function.
  (`#3896 <https://github.com/vertexproject/synapse/pull/3896>`_)
- Expose the response URL on the Storm ``http:resp`` object.
  (`#3898 <https://github.com/vertexproject/synapse/pull/3898>`_)
- Expose the HTTP request headers on the Storm ``http:resp`` object.
  (`#3899 <https://github.com/vertexproject/synapse/pull/3899>`_)
- Add request history on the Storm ``inet:http:resp`` object.
  (`#3900 <https://github.com/vertexproject/synapse/pull/3900>`_)
- Add a ``getPropValues()`` API to Storm View and Layer objects for yielding
  distinct values of a property.
  (`#3903 <https://github.com/vertexproject/synapse/pull/3903>`_)
- Update Storm language to add support for matching multiple switch case values
  to a single Storm query.
  (`#3904 <https://github.com/vertexproject/synapse/pull/3904>`_)
- Provide additional handling for Storm pool members who are online but
  unresponsive to new Telepath calls.
  (`#3914 <https://github.com/vertexproject/synapse/pull/3914>`_)
- Add the ability to provide an iden when creating a new HTTP Extended API.
  (`#3920 <https://github.com/vertexproject/synapse/pull/3920>`_)
- Added initial dictionary validator and deconfliction for guid based node
  constructor logic to Storm.
  (`#3917 <https://github.com/vertexproject/synapse/pull/3917>`_)

Bugfixes
--------
- Fix an issue where user defined Storm functions could be greedy with the IO
  loop.
  (`#3894 <https://github.com/vertexproject/synapse/pull/3894>`_)
- Fixed bug where nodedata may not be properly removed when it's in a
  view/layer above the actual node.
  (`#3923 <https://github.com/vertexproject/synapse/pull/3923>`_)

Improved documentation
----------------------
- Added documentation about ``tls:ca:dir`` configuration option for specifying
  custom TLS CA certificates.
  (`#3895 <https://github.com/vertexproject/synapse/pull/3895>`_)
- Added an example of using ``scrape`` on the primary property to the command
  usage statement.
  (`#3907 <https://github.com/vertexproject/synapse/pull/3907>`_)

Deprecations
------------
- Remove deprecated ``synapse.lib.jupyter`` module.
  (`#3897 <https://github.com/vertexproject/synapse/pull/3897>`_)

v2.180.1 - 2024-09-04
=====================

Features and Enhancements
-------------------------
- Update the ``cryptography`` library to require its latest version.
  (`#3890 <https://github.com/vertexproject/synapse/pull/3890>`_)

Improved documentation
----------------------
- Fixed a typo in the ``trigger.enable`` docs which mistakenly referred to the
  ``trigger-enable`` command.
  (`#3889 <https://github.com/vertexproject/synapse/pull/3889>`_)

v2.180.0 - 2024-08-30
=====================

Automatic Migrations
--------------------
- A small migration to normalize ``it:dev:repo:commit:id`` to remove leading
  and trailing whitespace.
  (`#3884 <https://github.com/vertexproject/synapse/pull/3884>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Added ``pol:candidate:id`` to track election authority issued candidate IDs.
  (`#3878 <https://github.com/vertexproject/synapse/pull/3878>`_)
- Updated ``it:dev:repo`` elements to inherit ``inet:service:object``.
  (`#3879 <https://github.com/vertexproject/synapse/pull/3879>`_)
- Add ``inet:service:account`` properties to forms with ``inet:web:acct``
  properties.
  (`#3880 <https://github.com/vertexproject/synapse/pull/3880>`_)
- See :ref:`userguide_model_v2_180_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Include detailed link traversal information from the Storm runtime when the
  ``link`` option is set.
  (`#3862 <https://github.com/vertexproject/synapse/pull/3862>`_)
- Add support for disabling readahead on layer slabs by setting the
  ``SYNDEV_CORTEX_LAYER_READAHEAD`` environment variable.
  (`#3877 <https://github.com/vertexproject/synapse/pull/3877>`_)

Improved documentation
----------------------
- Add Devops task for using ``onboot:optimize`` to optimize LMDB databases in
  services.
  (`#3876 <https://github.com/vertexproject/synapse/pull/3876>`_)
- Clarify documentation on taxonomy types.
  (`#3883 <https://github.com/vertexproject/synapse/pull/3883>`_)

v2.179.0 - 2024-08-23
=====================

Model Changes
-------------
- Update ``pe:langid`` to include all language IDs and tags from MS-LCID.
  (`#3851 <https://github.com/vertexproject/synapse/pull/3851>`_)
- Add additional fields to ``it:sec:stix:indicator``.
  (`#3858 <https://github.com/vertexproject/synapse/pull/3858>`_)
- Add ``geo:telem:node`` property to more directly track where a node has been.
  (`#3864 <https://github.com/vertexproject/synapse/pull/3864>`_)
- Add DNS reply code enumeration values to ``inet:dns:request:reply:code``.
  (`#3868 <https://github.com/vertexproject/synapse/pull/3868>`_)
- See :ref:`userguide_model_v2_179_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add support for a ``ca_cert`` key to ``$ssl_opts`` on Storm APIs. This can be
  used to provide a CA chain for a specific HTTP API call.
  (`#3849 <https://github.com/vertexproject/synapse/pull/3849>`_)
- Optimize pivot behavior in Storm to avoid unnecessarily re-normalizing
  values.
  (`#3853 <https://github.com/vertexproject/synapse/pull/3853>`_)
- Added ``force`` option to extended property delete APIs to automatically
  remove data.
  (`#3863 <https://github.com/vertexproject/synapse/pull/3863>`_)

Bugfixes
--------
- Fix a bug where trigger name and doc updates set via ``syn:trigger`` nodes
  did not persist.
  (`#3848 <https://github.com/vertexproject/synapse/pull/3848>`_)
- Fix an issue that prevented removing permissions from vaults.
  (`#3865 <https://github.com/vertexproject/synapse/pull/3865>`_)
- Fix an issue that prevented the old name reference from being removed when a
  vault is renamed.
  (`#3865 <https://github.com/vertexproject/synapse/pull/3865>`_)
- When generating the AHA provisioning URL, the AHA service now binds to
  0.0.0.0 instead of the ``dns:name`` configuration value.
  (`#3866 <https://github.com/vertexproject/synapse/pull/3866>`_)
- Catch additional Python exceptions which could be raised by malformed input
  to ``$lib.stix.import.ingest()`` and raise ``BadArg`` instead.
  (`#3867 <https://github.com/vertexproject/synapse/pull/3867>`_)
- Catch Python ``TypeError`` exceptions in ``$lib.math.number()`` and raise
  ``BadCast`` exceptions.
  (`#3871 <https://github.com/vertexproject/synapse/pull/3871>`_)

Deprecations
------------
- Deprecate the ``$tag`` variable in triggers in favor of ``$auto.opts.tag``
  (`#3854 <https://github.com/vertexproject/synapse/pull/3854>`_)

v2.178.0 - 2024-08-09
=====================

Features and Enhancements
-------------------------
- Setting the ``aha:network`` value on the AHA service, as demonstrated in the
  deployment guide, is now mandatory.
  (`#3783 <https://github.com/vertexproject/synapse/pull/3783>`_)
- Added ``synapse.tools.aha.clone`` command to make it easy to bootstrap AHA
  mirrors.
  (`#3783 <https://github.com/vertexproject/synapse/pull/3783>`_)
- Added support for dynamically registered AHA mirrors.
  (`#3783 <https://github.com/vertexproject/synapse/pull/3783>`_)
- Updated service base class to retrieve updated AHA servers on startup.
  (`#3783 <https://github.com/vertexproject/synapse/pull/3783>`_)
- Update ``$lib.inet.imap`` and ``$lib.inet.smtp`` APIs to use certificates
  present in the Cortex ``tls:ca:dir`` directory. Add ``ssl_verify`` options to
  the ``$lib.inet.imap.connect()`` and ``inet:smtp:message.send()`` APIs to
  disable TLS verification.
  (`#3842 <https://github.com/vertexproject/synapse/pull/3842>`_)
- Update the ``aioimaplib`` library constraints to ``>=1.1.0,<1.2.0``.
  (`#3842 <https://github.com/vertexproject/synapse/pull/3842>`_)
- Log the path of the LMDB file that was backed up in
  ``synapse.tools.backup.backup_lmdb``.
  (`#3843 <https://github.com/vertexproject/synapse/pull/3843>`_)

Bugfixes
--------
- Remove a potential race condition in onfini handler registration.
  (`#3840 <https://github.com/vertexproject/synapse/pull/3840>`_)
- Cause service startup to fail with a clear error message when attempting to
  bootstrap a service with a ``mirror`` configuration and the ``aha:provision``
  configuration option is missing, or the service storage has been manipulated
  into a invalid state.
  (`#3844 <https://github.com/vertexproject/synapse/pull/3844>`_)

Improved documentation
----------------------
- Update deployment guide to include optional steps to deploy AHA mirrors.
  (`#3783 <https://github.com/vertexproject/synapse/pull/3783>`_)
- Update deployment guide to clarify ``aha:network`` selection vs ``dns:name``
  selection.
  (`#3783 <https://github.com/vertexproject/synapse/pull/3783>`_)
- Move data model update information for the ``v2.133.0`` release and above
  from the changelog and into their own section of the User Guide.
  (`#3839 <https://github.com/vertexproject/synapse/pull/3839>`_)
- Update Synapse tool examples to use ``aha://`` URLs.
  (`#3839 <https://github.com/vertexproject/synapse/pull/3839>`_)

Deprecations
------------
- Deprecate the ``Cell.conf.reqConfValu()`` API. This has been replaced with
  ``Cell.conf.req()``.
  (`#3783 <https://github.com/vertexproject/synapse/pull/3783>`_)


v2.177.0 - 2024-08-01
=====================

Automatic Migrations
--------------------
- Migrate Axon metrics from hive to hotcounts. Migrate Cryotank names storage
  from hive to SafeKeyVal storage. Migrate Cortex configuration data from hive
  to SafeKeyVal storage. Migrate Cell info and auth configuration from hive to
  SafeKeyVal storage.
  (`#3698 <https://github.com/vertexproject/synapse/pull/3698>`_)
  (`#3825 <https://github.com/vertexproject/synapse/pull/3825>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Add model elements to represent the DriveSerialNumber and MachineID
  properties of an LNK file.
  (`#3817 <https://github.com/vertexproject/synapse/pull/3817>`_)
- Add ``biz:deal:id`` property to track deal identifiers.
  (`#3832 <https://github.com/vertexproject/synapse/pull/3832>`_)
- Add ``inet:service:message:type`` property to capture message types.
  (`#3832 <https://github.com/vertexproject/synapse/pull/3832>`_)
- Added ``meta:rule:type`` taxonomy.
  (`#3834 <https://github.com/vertexproject/synapse/pull/3834>`_)
- See :ref:`userguide_model_v2_177_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add a new Cell configuration option, ``auth:password:policy``. This can be
  used to configure password policy options for authentication.
  (`#3698 <https://github.com/vertexproject/synapse/pull/3698>`_)
- Add ``$lib.gen.cryptoX509CertBySha256()`` helper function to create
  ``crypto:x509:cert`` nodes from a SHA256.
  (`#3801 <https://github.com/vertexproject/synapse/pull/3801>`_)
- Add ``$lib.gen.fileBytesBySha256()`` helper function to create ``file:bytes``
  nodes from a SHA256.
  (`#3801 <https://github.com/vertexproject/synapse/pull/3801>`_)
- Add ``$lib.model.migration.s.inetSslCertToTlsServercert()`` migration helper
  to migrate ``inet:ssl:cert`` nodes to ``inet:tls:servercert`` nodes.
  (`#3801 <https://github.com/vertexproject/synapse/pull/3801>`_)
- Add ``$lib.gen.inetTlsServerCertByServerAndSha256()`` helper function to
  create ``inet:tls:servercert`` nodes from a server (or URI) and SHA256.
  (`#3801 <https://github.com/vertexproject/synapse/pull/3801>`_)
- Added Storm library for creating printable tables: ``$lib.tabular``.
  (`#3818 <https://github.com/vertexproject/synapse/pull/3818>`_)
- Add ``$lib.model.ext.addEdge()`` and ``$lib.model.ext.delEdge()`` APIs for
  managing extended model edge definitions.
  (`#3824 <https://github.com/vertexproject/synapse/pull/3824>`_)
- Added ``--wipe`` option to the ``merge`` command which replaces the top layer
  of the view once the merge is complete. Using ``--wipe`` makes incremental
  merges more performant.
  (`#3828 <https://github.com/vertexproject/synapse/pull/3828>`_)
- Updated ``view.merge`` command to use ``$view.swapLayer()`` for improved
  performance.
  (`#3828 <https://github.com/vertexproject/synapse/pull/3828>`_)
- Added ``$view.swapLayer()`` API to allow users to start fresh with an
  existing view.
  (`#3828 <https://github.com/vertexproject/synapse/pull/3828>`_)
- Update the ``aiohttp`` library constraints to ``>=3.10.0,<4.0``. Update the
  ``aiohttp-socks`` library constraints to ``>=0.10.0,<0.11.0``.
  (`#3830 <https://github.com/vertexproject/synapse/pull/3830>`_)
- Tightened up ``aha.svc.list`` Storm command output when using ``--nexus``.
  (`#3835 <https://github.com/vertexproject/synapse/pull/3835>`_)

Bugfixes
--------
- Prevent the root user for a Synapse service from being locked, archived, or
  having its admin status removed.
  (`#3698 <https://github.com/vertexproject/synapse/pull/3698>`_)
- Catch Python ``TypeError`` exceptions that could be raised by
  ``$lib.base64.decode()`` and now raise ``StormRuntimeError`` detailing the
  problem.
  (`#3827 <https://github.com/vertexproject/synapse/pull/3827>`_)
- Fix ``Bad file descriptor`` errors that could happen during link teardown.
  (`#3831 <https://github.com/vertexproject/synapse/pull/3831>`_)

v2.176.0 - 2024-07-18
=====================

Model Changes
-------------
- Updates to the ``inet`` model.
  (`#3811 <https://github.com/vertexproject/synapse/pull/3811>`_)
  (`#3814 <https://github.com/vertexproject/synapse/pull/3814>`_)
- See :ref:`userguide_model_v2_176_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add ``storm.exec`` command for executing arbitrary text as Storm.
  (`#3807 <https://github.com/vertexproject/synapse/pull/3807>`_)
  (`#3812 <https://github.com/vertexproject/synapse/pull/3812>`_)
- Ensure the ``synapse.storm`` structured log messages contain the view iden.
  (`#3812 <https://github.com/vertexproject/synapse/pull/3812>`_)
- Added ``$lib.storm.run()`` to programmatically invoke Storm.
  (`#3813 <https://github.com/vertexproject/synapse/pull/3813>`_)
- Remove the per-node pivot errors from the Cortex log output.
  (`#3819 <https://github.com/vertexproject/synapse/pull/3819>`_)

v2.175.0 - 2024-07-15
=====================

Automatic Migrations
--------------------
- Migrate existing ndef secondary properties to use the new ndef property
  indexing.
  (`#3794 <https://github.com/vertexproject/synapse/pull/3794>`_)
  (`#3809 <https://github.com/vertexproject/synapse/pull/3809>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Update Cell with ``_getCellHttpOpts()`` method to allow for overriding default
  HTTP options.
  (`#3770 <https://github.com/vertexproject/synapse/pull/3770>`_)
- Add additional indexing for ndef based secondary properties.
  (`#3794 <https://github.com/vertexproject/synapse/pull/3794>`_)
  (`#3809 <https://github.com/vertexproject/synapse/pull/3809>`_)
- Implement ``--prs-from-git`` in ``synapse.tools.changelog``.
  (`#3800 <https://github.com/vertexproject/synapse/pull/3800>`_)
- Update the ``getCellInfo()`` API to include HTTPS listener addresses and
  ports.
  (`#3802 <https://github.com/vertexproject/synapse/pull/3802>`_)
- Improve permissions checking performance in the Storm ``merge`` command.
  (`#3804 <https://github.com/vertexproject/synapse/pull/3804>`_)
- Support multiple tags in the diff command, which also allows for more
  efficient deduplication (e.g. ``diff --tag foo bar``
  versus ``diff --tag foo | diff --tag bar | uniq``).
  (`#3806 <https://github.com/vertexproject/synapse/pull/3806>`_)
- Add information about the remote link when logging common server side
  Telepath errors.
  (`#3808 <https://github.com/vertexproject/synapse/pull/3808>`_)

Bugfixes
--------
- Fix an AttributeError in ``synapse.tools.changelog``.
  (`#3798 <https://github.com/vertexproject/synapse/pull/3798>`_)
- Fix for large array props causing system lag.
  (`#3799 <https://github.com/vertexproject/synapse/pull/3799>`_)

Improved documentation
----------------------
- Remaining docs have been converted from Jupyter notebook format to RST.
  (`#3803 <https://github.com/vertexproject/synapse/pull/3803>`_)

Deprecations
------------
- Deprecate the use of the ``synapse.lib.jupyter`` library. This will be
  removed on 2024-08-26.
  (`#3803 <https://github.com/vertexproject/synapse/pull/3803>`_)

v2.174.0 - 2024-07-09
=====================

Automatic Migrations
--------------------
- Renormalize ``ou:position:title``, ``ou:conference:name``, and
  ``ou:conference:names`` secondary properties.
  (`#3701 <https://github.com/vertexproject/synapse/pull/3701>`_)
- Populate new ``econ:currency`` nodes from existing secondary properties.
  (`#3790 <https://github.com/vertexproject/synapse/pull/3790>`_)
- Add a Cortex storage migration to set the correct View iden value on all
  Trigger definitions.
  (`#3760 <https://github.com/vertexproject/synapse/pull/3760>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Add a new model, ``entity``, for modeling elements related to entity
  resolution.
  (`#3781 <https://github.com/vertexproject/synapse/pull/3781>`_)
- Updates to the ``crypto``, ``econ``, ``files``, ``ou``, and ``pol`` models.
  (`#3790 <https://github.com/vertexproject/synapse/pull/3790>`_)
  (`#3781 <https://github.com/vertexproject/synapse/pull/3781>`_)
- See :ref:`userguide_model_v2_174_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add additional context to structured log information when a long LMDB commit
  is detected.
  (`#3747 <https://github.com/vertexproject/synapse/pull/3747>`_)
- Add support to ``synapse.lib.msgpack`` functions for handling integers
  requiring more than 64 bits to store them.
  (`#3767 <https://github.com/vertexproject/synapse/pull/3767>`_)
  (`#3780 <https://github.com/vertexproject/synapse/pull/3780>`_)
- Add support for Storm variables in array filters.
  (`#3775 <https://github.com/vertexproject/synapse/pull/3775>`_)
- Add a ``kill()`` API to the Storm ``cron`` objects.
  (`#3787 <https://github.com/vertexproject/synapse/pull/3787>`_)
  (`#3796 <https://github.com/vertexproject/synapse/pull/3796>`_)
- Add log messages when a cron job is enabled or disabled.
  (`#3793 <https://github.com/vertexproject/synapse/pull/3793>`_)

Bugfixes
--------
- Trigger definitions now always have the View iden that they belong to set
  upon View creation. The Storm ``$lib.trigger.set()`` API now uses the trigger
  view instead of the current view when checking permissions.
  (`#3760 <https://github.com/vertexproject/synapse/pull/3760>`_)
- Add missing item information when an error occurs while replaying a nexus
  change entry upon startup
  (`#3778 <https://github.com/vertexproject/synapse/pull/3778>`_)
- Fix the startup order for the Cortex embedded JSONStor to avoid an issue with
  the nexus replay on startup.
  (`#3779 <https://github.com/vertexproject/synapse/pull/3779>`_)
- Wrap the Nexus mirror loop setup code in a try/except block to handle
  unexpected errors.
  (`#3781 <https://github.com/vertexproject/synapse/pull/3781>`_)
- Only fire the beholder ``pkg:add`` events when the contents of a Storm
  package change.
  (`#3785 <https://github.com/vertexproject/synapse/pull/3785>`_)

v2.173.1 - 2024-06-25
=====================

This release also includes the changes from v2.173.0, which was not released
due to an issue with CI pipelines.

Model Changes
-------------
- Updates to the ``ou``, ``plan``, and ``ps`` models.
  (`#3772 <https://github.com/vertexproject/synapse/pull/3772>`_)
  (`#3773 <https://github.com/vertexproject/synapse/pull/3773>`_)
- See :ref:`userguide_model_v2_173_1` for more detailed model changes.

Bugfixes
--------
- Fix a bug in the ``view.merge`` optimizations from ``v2.172.0`` where deny
  rules were not properly accounted for when checking for fast paths on the
  ``node`` permission hierarchy.
  (`#3771 <https://github.com/vertexproject/synapse/pull/3771>`_)

v2.173.0 - 2024-06-25
=====================

This release was replaced with ``v2.173.1``.

v2.172.0 - 2024-06-24
=====================

Model Changes
-------------
- Updates to the ``biz``, ``econ``, ``inet``, ``meta``, ``ou`` ``risk``,
  and ``transit`` models.
  (`#3561 <https://github.com/vertexproject/synapse/pull/3561>`_)
  (`#3756 <https://github.com/vertexproject/synapse/pull/3756>`_)
- See :ref:`userguide_model_v2_172_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Update the permission checking for View merging ( ``view.merge`` ) to
  optimize the permission checking based on user permissions and layer index
  data.
  (`#3736 <https://github.com/vertexproject/synapse/pull/3736>`_)
  (`#3750 <https://github.com/vertexproject/synapse/pull/3750>`_)
  (`#3758 <https://github.com/vertexproject/synapse/pull/3758>`_)
- Add a hotfix that can be used to migrate ``risk:hasvuln`` nodes to
  ``risk:vulnerable`` nodes.
  (`#3745 <https://github.com/vertexproject/synapse/pull/3745>`_)
- Add a Storm API, ``$lib.env.get()``, to get environment variables from
  the Cortex process which start with the prefix ``SYN_STORM_ENV_``.
  (`#3761 <https://github.com/vertexproject/synapse/pull/3761>`_)
- Add a ``edited()`` API to the ``layer`` object in Storm. This API can be
  used to get the last time a given layer was edited. Add a ``reverse``
  argument to the ``layer.edits()`` API to return the node edits in reverse
  order.
  (`#3763 <https://github.com/vertexproject/synapse/pull/3763>`_)
- Add a ``setArchived()`` API to the ``auth:user`` object in Storm.
  (`#3759 <https://github.com/vertexproject/synapse/pull/3759>`_)
- The ``synapse.tool.storm`` tool now returns a non-zero status code when
  it is invoked to execute a single command and the command encounters an
  error.
  (`#3765 <https://github.com/vertexproject/synapse/pull/3765>`_)
- Add a ``nodup`` option to the ``slab.scanKeys()`` API. Use this to increase
  the efficiency of the the Storm ``model.edge.list`` command.
  (`#3762 <https://github.com/vertexproject/synapse/pull/3762>`_)
- Add a ``synapse.common.trimText()`` API for trimming strings in a consistent
  fashion. Use that API to trim long text strings that may be included in
  exception messages.
  (`#3753 <https://github.com/vertexproject/synapse/pull/3753>`_)
- When a Storm subquery assignment yields more than a single node, add the
  trimmed subquery text to the ``BadTypeValu`` exception that is raised.
  (`#3753 <https://github.com/vertexproject/synapse/pull/3753>`_)

Bugfixes
--------
- Fix a typo in the Storm ``gen.it.av.scan.result`` command help output.
  (`#3766 <https://github.com/vertexproject/synapse/pull/3766>`_)
- Fix a typo in the Rapid Power-Up development documentation.
  (`#3766 <https://github.com/vertexproject/synapse/pull/3766>`_)

Improved Documentation
----------------------

- Add documentation for ``$lib.auth.easyperm.level`` constants and the
  ``$lib.dict.has()`` function.
  (`#3706 <https://github.com/vertexproject/synapse/pull/3706>`_)


v2.171.0 - 2024-06-07
=====================

Features and Enhancements
-------------------------
- Update ``synapse.test.utils.SynTest`` helpers to disable sysctl checks
  for test services by default.
  (`#3741 <https://github.com/vertexproject/synapse/pull/3741>`_)

Bugfixes
--------
- Fix a key positioning error in the LMDBSlab when scanning backwards
  by prefix.
  (`#3739 <https://github.com/vertexproject/synapse/pull/3739>`_)
- Fix a bug in the ``str`` type normalization routine for handling floating
  point values. The floating point values are now also run through the
  string norming logic.
  (`#3742 <https://github.com/vertexproject/synapse/pull/3742>`_)
- Add missing beholder messages for view layer modifications.
  (`#3743 <https://github.com/vertexproject/synapse/pull/3743>`_)

Improved Documentation
----------------------
- Update Devops documentation to add additional information about low downtime
  service updates, Rapid Power-Up updates, and release cadence information.
  Update references from ``docker-compose`` to use ``docker compose``.
  (`#3722 <https://github.com/vertexproject/synapse/pull/3722>`_)

v2.170.0 - 2024-06-04
=====================

Automatic Migrations
--------------------
- Populate an additional index of buids by form in Layers.
  (`#3729 <https://github.com/vertexproject/synapse/pull/3729>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Updates to the ``infotech`` and ``file`` models.
  (`#3702 <https://github.com/vertexproject/synapse/pull/3702>`_)
  (`#3725 <https://github.com/vertexproject/synapse/pull/3725>`_)
  (`#3732 <https://github.com/vertexproject/synapse/pull/3732>`_)
- See :ref:`userguide_model_v2_170_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Added ``$lib.model.migration.s.riskHasVulnToVulnerable`` migration helper
  to create ``risk:vulnerable`` nodes from ``risk:hasvuln`` nodes.
  (`#3734 <https://github.com/vertexproject/synapse/pull/3734>`_)
- Added ``$lib.model.migration.s.itSecCpe_2_170_0()`` migration helper to update
  ``it:sec:cpe`` nodes created before this release. Details about the migration
  helper can be found in the help (``help -v $lib.model.migration.s.itSecCpe_2_170_0``)
  (`#3515 <https://github.com/vertexproject/synapse/pull/3515>`_)
- Update Storm lift optimization for tag filters to also allow hinting
  based on runtsafe variable values.
  (`#3733 <https://github.com/vertexproject/synapse/pull/3733>`_)
- Log an info message with the current Cell and Synapse version on startup.
  (`#3723 <https://github.com/vertexproject/synapse/pull/3723>`_)
- Add per-Cell version checks to prevent accidental downgrades of services.
  (`#3728 <https://github.com/vertexproject/synapse/pull/3728>`_)
- Add a check to Cells that will warn when performance related sysctl values
  are not configured correctly on the host. This warning can be disabled with
  the ``health:sysctl:checks`` configuration option.
  (`#3712 <https://github.com/vertexproject/synapse/pull/3712>`_)
- Add ``forms`` and ``interfaces`` type options to the ``ndef`` type, which
  require the value to be one of the specified forms, or inherit one of the
  specified interfaces.
  (`#3724 <https://github.com/vertexproject/synapse/pull/3724>`_)
- Add support for pivoting from an ``ndef`` secondary prop to specific form. 
  (`#3715 <https://github.com/vertexproject/synapse/pull/3715>`_)
- Add support for pivoting to or from ``ndef`` array properties.
  (`#3720 <https://github.com/vertexproject/synapse/pull/3720>`_)
- Add an index of buids by form to Layers. A ``getStorNodesByForm()`` API has
  been added to Storm Layer objects to retrieve storage nodes using this index.
  (`#3729 <https://github.com/vertexproject/synapse/pull/3729>`_)
- Storm Dmon APIs called on a Cortex mirror now call up to the leader to
  retrieve their result.
  (`#3735 <https://github.com/vertexproject/synapse/pull/3735>`_)
- Add a ``insertParentFork()`` API on Storm View objects to insert a new
  View between an existing fork and its parent View.
  (`#3731 <https://github.com/vertexproject/synapse/pull/3731>`_)
- Quorum merge requests are now allowed on Views which have forks.
  (`#3738 <https://github.com/vertexproject/synapse/pull/3738>`_)

Bugfixes
--------
- Fix a formatting issue in an error message that could be raised during
  JSON decoding in a Storm ``http:api:request`` object.
  (`#3730 <https://github.com/vertexproject/synapse/pull/3730>`_)
- Fix an issue where ``inet:url`` norming did not handle IPv6 addresses
  in the host portion of the URL correctly.
  (`#3727 <https://github.com/vertexproject/synapse/pull/3727>`_)
- Fix an issue where executing the ``view.exec`` command from within a
  privileged Storm runtime still checked user permissions for the specified
  view.
  (`#3726 <https://github.com/vertexproject/synapse/pull/3726>`_)
- Update logic for parsing CPE 2.2 and CPE 2.3 strings to be more compliant with
  the specification. This resulted in better conversions from CPE 2.2 to CPE 2.3
  and CPE 2.3 to CPE 2.2.
  (`#3515 <https://github.com/vertexproject/synapse/pull/3515>`_)

v2.169.0 - 2024-05-10
=====================

Features and Enhancements
-------------------------
- Add a data migration helper library, ``$lib.model.migration``. This
  contains functions to help with migrating data via Storm.
  (`#3714 <https://github.com/vertexproject/synapse/pull/3714>`_)
- Add Extended HTTP API iden values to structured Storm query logs.
  (`#3710 <https://github.com/vertexproject/synapse/pull/3710>`_)
- Add ``node.data.set`` and ``node.data.pop`` to the list of declared
  Cortex permissions.
  (`#3716 <https://github.com/vertexproject/synapse/pull/3716>`_)

Bugfixes
--------
- Restore cron iden values in structured Storm query logs.
  (`#3710 <https://github.com/vertexproject/synapse/pull/3710>`_)
- The Storm APIs ``$lib.min()`` and ``$lib.max()`` now handle a single
  input. The Storm APIs ``$lib.min()`` and ``$lib.max()`` now raise a
  ``StormRuntimeError`` when there is no input provided to them. Previously
  these conditions caused a Python exception in the Storm runtime.
  (`#3711 <https://github.com/vertexproject/synapse/pull/3711>`_)
- The ``onboot:optimize`` configuration now skips optimizing any LMDB files
  found in the Cell local backup storage.
  (`#3713 <https://github.com/vertexproject/synapse/pull/3713>`_)

Deprecations
------------
- Removed the Telepath APIs ``CoreApi.enableMigrationMode`` and
  ``CoreApi.disableMigrationMode``.  Remove support for the Cell
  ``hiveboot.yaml`` file. These had a removal date of 2025-05-05.
  (`#3717 <https://github.com/vertexproject/synapse/pull/3717>`_)

v2.168.0 - 2024-05-03
=====================

Model Changes
-------------
- Add a new model, ``plan``, for modeling elements of plannings systems.
  (`#3697 <https://github.com/vertexproject/synapse/pull/3697>`_)
- See :ref:`userguide_model_v2_168_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Cortex data model migrations will now be checked and executed when the
  service is promoted to being a leader. This allows for Cortex updates
  which use mirrors to have minimal downtime. Cortex model migrations which
  are executed using Storm will always run directly on the Cortex leader.
  (`#3694 <https://github.com/vertexproject/synapse/pull/3694>`_)
  (`#3695 <https://github.com/vertexproject/synapse/pull/3695>`_)
- The Storm ``aha:pool.del()`` method now returns the full name of the
  service that was removed.
  (`#3704 <https://github.com/vertexproject/synapse/pull/3704>`_)

Bugfixes
--------
- The Storm command  ``aha.pool.svc.del`` now prints out the name of the
  service that was removed from the pool or notes that there were no
  services removed.
  (`#3704 <https://github.com/vertexproject/synapse/pull/3704>`_)
- When setting a service "down" with AHA, conditionally clear the ``ready``
  flag as well. Previously this flag was not cleared, and offline services
  could still report as ``ready``.
  (`#3705 <https://github.com/vertexproject/synapse/pull/3705>`_)
- Add missing sleep statements to callers of ``Layer.syncNodeEdits2()``.
  (`#3700 <https://github.com/vertexproject/synapse/pull/3700>`_)

Improved Documentation
----------------------
- Update Storm command reference documentation to add additional examples
  for the ``uniq`` command. Update Storm command reference documentation to
  add ``gen.geo.place`` and ``gen.it.av.scan.result`` commands.
  (`#3699 <https://github.com/vertexproject/synapse/pull/3699>`_)
- Update type specific documentation. Add additional information about ``loc``
  and ``syn:tag`` behavior with prefixes and wlidcards. Add a section on the
  ``duration`` and ``taxonomy`` types.
  (`#3703 <https://github.com/vertexproject/synapse/pull/3703>`_)
- Add documentation for ``$lib.auth.easyperm.level`` constants and the
  ``$lib.dict.has()`` function.
  (`#3706 <https://github.com/vertexproject/synapse/pull/3706>`_)

v2.167.0 - 2024-04-19
=====================

Automatic Migrations
--------------------
- Set the ``protected`` flag on all Views in the Cortex, using the existing
  value of the ``nomerge`` flag.
  (`#3681 <https://github.com/vertexproject/synapse/pull/3681>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Updates to the ``base`` and ``file`` models.
  (`#3674 <https://github.com/vertexproject/synapse/pull/3674>`_)
  (`#3688 <https://github.com/vertexproject/synapse/pull/3688>`_)
- See :ref:`userguide_model_v2_167_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add ``aha.svc.list`` and ``aha.svc.stat`` commands to enumerate the AHA
  services. Add ``$lib.aha`` Storm APIs to delete, get, and list the AHA
  services.
  (`#3685 <https://github.com/vertexproject/synapse/pull/3685>`_)
  (`#3692 <https://github.com/vertexproject/synapse/pull/3692>`_)
  (`#3693 <https://github.com/vertexproject/synapse/pull/3693>`_)
- Add a ``protected`` option that can be set on Views to prevent
  merging and deletion. This replaces the ``nomerge`` option.
  (`#3679 <https://github.com/vertexproject/synapse/pull/3679>`_)
- Add Beholder events for creating, deleting, and updating Macros.
  (`#3681 <https://github.com/vertexproject/synapse/pull/3681>`_)
- Update the ``StormPkgTest.getTestCore()`` API to add a ``prepkghook``
  callback option. This can be used to execute code prior to loading Storm
  packages. The ``getTestCore()`` API now waits for ``onload`` handlers to
  complete for each package it loads.
  (`#3687 <https://github.com/vertexproject/synapse/pull/3687>`_)
- Ensure that the ``Cell.ahaclient`` is fully owned and managed by the
  ``Cell``. It will no longer use a global client that may exist.
  (`#3677 <https://github.com/vertexproject/synapse/pull/3677>`_)
- Update the ``stix2-validator`` library constraints to ``>=3.2.0,<4.0.0``.
  Update the allowed range of the ``idna`` library  to ``>=3.6,<3.8``.
  (`#3672 <https://github.com/vertexproject/synapse/pull/3672>`_)
  (`#3684 <https://github.com/vertexproject/synapse/pull/3684>`_)

Bugfixes
--------
- Asyncio Tasks created by signal handlers on the Base object are now held
  onto, to ensure that they cannot be garbage collected before or during
  their task execution.
  (`#3686 <https://github.com/vertexproject/synapse/pull/3686>`_)
- Update the ``Axon.postfiles`` and ``Axon.wput`` APIs to check for the
  existence of files before attempting to send them over an HTTP connection.
  (`#3682 <https://github.com/vertexproject/synapse/pull/3682>`_)
- Fix an issue where pruning a non-existent tag mistakenly pruned related
  tags.
  (`#3673 <https://github.com/vertexproject/synapse/pull/3673>`_)
- Ensure that macro names are at least 1 character in length.
  (`#3679 <https://github.com/vertexproject/synapse/pull/3679>`_)
- Fix a bug where ``$lib.telepath.open()`` could leak Python exceptions into
  the Storm runtime.
  (`#3685 <https://github.com/vertexproject/synapse/pull/3685>`_)

Improved Documentation
----------------------
- Add documentation for ``$lib.aha``, ``$lib.aha.pool``, and the ``aha:pool``
  type.
  (`#3685 <https://github.com/vertexproject/synapse/pull/3685>`_)

Deprecations
------------
- Deprecate the use of ``hiveboot.yaml`` to configure a Cell hive. This will be
  removed on 2024-05-05.
  (`#3678 <https://github.com/vertexproject/synapse/pull/3678>`_)
- The ``nomerge`` option on views has been deprecated. It is automatically
  redirected to the ``protected`` option. This redirection will be removed in
  ``v3.0.0``.
  (`#3681 <https://github.com/vertexproject/synapse/pull/3681>`_)
- The Telepath APIs for interacting with a Cell Hive, ``listHiveKey``,
  ``getHiveKeys``, ``getHiveKey``, ``setHiveKey``, ``popHiveKey``, and
  ``saveHiveTree`` have been deprecated. The tools ``synapse.tools.hive.load``
  and ``synapse.tools.hive.save`` have been deprecated. These will be removed
  in ``v3.0.0``.
  (`#3683 <https://github.com/vertexproject/synapse/pull/3683>`_)
- The ``Telepath.Pipeline`` class has been marked as deprecated and will be
  removed in ``v3.0.0``.
  (`#3691 <https://github.com/vertexproject/synapse/pull/3691>`_)

v2.166.0 - 2024-04-05
=====================

Model Changes
-------------
- Updates to the ``inet``, ``ou``, ``person`` and ``risk`` models.
  (`#3649 <https://github.com/vertexproject/synapse/pull/3649>`_)
  (`#3653 <https://github.com/vertexproject/synapse/pull/3653>`_)
  (`#3657 <https://github.com/vertexproject/synapse/pull/3657>`_)
- See :ref:`userguide_model_v2_166_0` for more detailed model changes.

Features and Enhancements
-------------------------
- When setting a tag on a node, the tag value is now redirected based on
  parent tags having ``:isnow`` properties set.
  (`#3650 <https://github.com/vertexproject/synapse/pull/3650>`_)
- Add a ``$lib.spooled.set()`` Storm API. This can be used to get a
  ``spooled:set`` object. This set will offload the storage of its members
  to a temporary location on disk when it grows above a certain size.
  (`#3632 <https://github.com/vertexproject/synapse/pull/3632>`_)
- Add a ``$lib.cache.fixed()`` Storm API. This can be used to get a
  ``cache:fixed`` object. This cache will execute user provided callbacks
  written in Storm upon a cache miss.
  (`#3661 <https://github.com/vertexproject/synapse/pull/3661>`_)
- Add a ``pool`` option to Cron jobs. This can be set to True to enable a
  Cron job storm query to be executed on a Storm pool member.
  (`#3652 <https://github.com/vertexproject/synapse/pull/3652>`_)
- Add a ``pool`` option to Extended HTTP API handlers. This can be set to
  True to enable an HTTP request handler to be executed on a Storm pool member.
  (`#3663 <https://github.com/vertexproject/synapse/pull/3663>`_)
  (`#3667 <https://github.com/vertexproject/synapse/pull/3667>`_)
- Add a new Storm API, ``$lib.cortex.httpapi.getByPath()``, that can be
  used to get an ``http:api`` object by its path. The ``path`` value is
  evaluated in the same order that the HTTP endpoint resolves the handlers.
  (`#3663 <https://github.com/vertexproject/synapse/pull/3663>`_)
- Add ``--list`` and ``--gate`` options to ``synapse.tools.modrole`` and
  ``synapse.tools.moduser``.
  (`#3632 <https://github.com/vertexproject/synapse/pull/3632>`_)
- Add a ``view.getMergingViews()`` Storm API. This returns a list of view
  idens that have open merge requests on a view.
  (`#3666 <https://github.com/vertexproject/synapse/pull/3666>`_)
- The Storm API ``show:storage`` option now includes storage information for
  any embedded properties.
  (`#3656 <https://github.com/vertexproject/synapse/pull/3656>`_)
- Update the ``LinkShutDown`` exception that a Telepath client may raise to
  indicate that the connection has been disconnected.
  (`#3640 <https://github.com/vertexproject/synapse/pull/3640>`_)
- Add repr functions for printing the ``aha:pool`` and ``http:api`` objects
  in Storm.
  (`#3663 <https://github.com/vertexproject/synapse/pull/3663>`_)
  (`#3665 <https://github.com/vertexproject/synapse/pull/3665>`_)
- The Telepath ``Pool`` object has been replaced with a new object,
  ``ClientV2``. This is now the only object returned by the
  ``synapse.telepath.open()`` API. This is an AHA pool aware Client which
  can be used to connect to an AHA pool.
  (`#3662 <https://github.com/vertexproject/synapse/pull/3662>`_)
- Remove the unused Provenance subsystem from the Cortex.
  (`#3655 <https://github.com/vertexproject/synapse/pull/3655>`_)
- Constrain the ``stix2-validator`` library to ``3.0.0,<3.2.0`` due to
  an API change. This constraint is expected be changed in the next
  release.
  (`#3669 <https://github.com/vertexproject/synapse/pull/3669>`_)

Bugfixes
--------
- Fix a bug where a Cortex ``promote()`` call could hang when tearing down
  any running Cron jobs. Cron jobs cancelled during a promotion event will
  be logged but their cancelled status will not be recorded in the Nexus.
  (`#3658 <https://github.com/vertexproject/synapse/pull/3658>`_)
- Fix a bug where the Storm pool configuration could cause a Cortex to fail
  to start up. The Storm pool is now configured upon startup but its use is
  blocked until the Storm pool is ready to service requests.
  (`#3662 <https://github.com/vertexproject/synapse/pull/3662>`_)
- Ensure that the URL argument provided to ``cortex.storm.pool.set`` can be
  parsed as a Telepath URL. Previously any string input was accepted.
  (`#3665 <https://github.com/vertexproject/synapse/pull/3665>`_)

Improved Documentation
----------------------
- Update the list of Cortex permissions in the Admin Guide to include
  ``service.add``, ``service.del``, ``service.get``,  and ``service.list``.
  (`#3647 <https://github.com/vertexproject/synapse/pull/3647>`_)
- Update the docstring for the Storm ``cortex.storm.pool.del`` command to note
  the effects of removing a pool and the interruption of running queries.
  (`#3665 <https://github.com/vertexproject/synapse/pull/3665>`_)
- Update the documentation for the Storm ``http:api`` object to include the
  ``methods`` attribute.
  (`#3663 <https://github.com/vertexproject/synapse/pull/3663>`_)

Deprecations
------------
- The Telepath ``task:init`` message format has been marked as deprecated and
  will be removed in ``v3.0.0``. This should not affect any users using Synapse
  ``v2.x.x`` in their client code.
  (`#3640 <https://github.com/vertexproject/synapse/pull/3640>`_)
- The authgate with the name ``cortex`` is not used for permission checking and
  will be removed in ``v3.0.0``. At startup, the Cortex will now check for any
  use of this authgate and log warning messages. Attempts to set permissions
  with this gateiden via Storm will produce ``warn`` messages.
  (`#3648 <https://github.com/vertexproject/synapse/pull/3648>`_)

v2.165.0 - 2024-03-25
=====================

Automatic Migrations
--------------------
- Re-normalize ``risk:mitigation:name``, ``it:mitre:attack:technique:name``,
  and ``it:mitre:attack:mitigation:name`` secondary properties.
  (`#3585 <https://github.com/vertexproject/synapse/pull/3585>`_)
- Re-normalize ``velocity`` properties which are float values.
  (`#3616 <https://github.com/vertexproject/synapse/pull/3616>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Add a new model, ``sci``, for modeling elements of the scientific method. Updates to
  the ``econ``, ``file``, ``infotech``, ``inet``, ``ou``, ``ps``, and ``risk``
  models.
  (`#3559 <https://github.com/vertexproject/synapse/pull/3559>`_)
  (`#3585 <https://github.com/vertexproject/synapse/pull/3585>`_)
  (`#3595 <https://github.com/vertexproject/synapse/pull/3595>`_)
  (`#3604 <https://github.com/vertexproject/synapse/pull/3604>`_)
  (`#3606 <https://github.com/vertexproject/synapse/pull/3606>`_)
  (`#3622 <https://github.com/vertexproject/synapse/pull/3622>`_)
  (`#3635 <https://github.com/vertexproject/synapse/pull/3635>`_)
- See :ref:`userguide_model_v2_165_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Change the compression mode used when streaming Cell backups to speed up
  the backup process.
  (`#3608 <https://github.com/vertexproject/synapse/pull/3608>`_)
- When a Cell is mirroring, gracefully go into read-only mode if the leader is
  a greater version than the mirror.
  (`#3581 <https://github.com/vertexproject/synapse/pull/3581>`_)
  (`#3631 <https://github.com/vertexproject/synapse/pull/3631>`_)
- Add ``null`` as a constant that can be used in Storm expression syntax.
  (`#3600 <https://github.com/vertexproject/synapse/pull/3600>`_)
- Add ``cortex.storm.pool.get``, ``cortex.storm.pool.set``, and
  ``cortex.storm.pool.del`` commands to manage the Storm query pool which may
  be used by the Cortex. This replaces the experimental support added in
  ``v2.160.0`` for Storm query pool configuration. The experimental Cortex
  configurations options ``storm:pool``, ``storm:pool:timeout:sync``, and
  ``storm:pool:timeout:connection`` have been removed.
  (`#3602 <https://github.com/vertexproject/synapse/pull/3602>`_)
- Add ``$lib.regex.escape()`` API for escaping strings which may be used as
  regular expression patterns.
  (`#3605 <https://github.com/vertexproject/synapse/pull/3605>`_)
- Add ``View.setMergeComment()`` and ``View.setMergeVoteComment()`` Storm APIs
  for setting comments on merge requests and merge votes.
  (`#3597 <https://github.com/vertexproject/synapse/pull/3597>`_)
- Add handlers to the ``float``, ``int``, and ``str`` types to handle norming
  Storm ``Number`` objects.
  (`#3601 <https://github.com/vertexproject/synapse/pull/3601>`_)
- Add a new Storm command, ``gen.geo.place``, to generate a ``geo:place`` node
  by name.
  (`#3620 <https://github.com/vertexproject/synapse/pull/3620>`_)
- Add an optional reporter name argument to the Storm command
  ``gen.risk.vuln``.
  (`#3628 <https://github.com/vertexproject/synapse/pull/3628>`_)
- Add a ``norm`` option to the ``$node.difftags()`` command.
  (`#3612 <https://github.com/vertexproject/synapse/pull/3612>`_)
- Add logging around the leader promotion and handoff actions.
  (`#3615 <https://github.com/vertexproject/synapse/pull/3615>`_)
- Add Telepath APIs to AHA for clearing unused provisioning information.
  (`#3607 <https://github.com/vertexproject/synapse/pull/3607>`_)

Bugfixes
--------
- Fix a bug where Cortex Cron jobs could start prior to data migrations
  having completed running.
  (`#3610 <https://github.com/vertexproject/synapse/pull/3610>`_)
- Fix an issue where ``node.prop.set`` and ``node.prop.del`` permissions were
  not being properly checked.
  (`#3627 <https://github.com/vertexproject/synapse/pull/3627>`_)
- Fix a bug in the Storm ``merge`` command where the destination layer was
  not being properly checked for property set and deletion permissions.
  (`#3627 <https://github.com/vertexproject/synapse/pull/3627>`_)
- Fix a bug in the Storm ``copyto`` command where the destination layer was
  not being properly checked for property set permissions.
  (`#3641 <https://github.com/vertexproject/synapse/pull/3641>`_)
- Fix an error when granting a role admin permissions on a vault.
  (`#3603 <https://github.com/vertexproject/synapse/pull/3603>`_)
- Prevent the ``synapse.tools.easycert`` tool from making certificates with
  names greater than 64 characters in length. Prevent AHA provisioning from
  creating provisioning requests which would exceed that length.
  (`#3609 <https://github.com/vertexproject/synapse/pull/3609>`_)
- Fix an issue with the ``velocity`` base type returning a float instead
  of an integer when handling a string value without a unit.
  (`#3616 <https://github.com/vertexproject/synapse/pull/3616>`_)
- Fix an issue that could occur when pivoting from a secondary property to
  a form when using variables for the source and target values.
  (`#3618 <https://github.com/vertexproject/synapse/pull/3618>`_)
- Fix a syntax parsing issue when using the try-set-plus or try-set-minus
  operator to update an array property on a node using a variable for the
  property name.
  (`#3630 <https://github.com/vertexproject/synapse/pull/3630>`_)
- Fix an issue with AHA service pools where their Telepath Clients were
  not configured for use as ``aha://`` clients.
  (`#3643 <https://github.com/vertexproject/synapse/pull/3643>`_)
- Fix an issue with AHA service pools where a fini'd Proxy was not properly
  cleaned up.
  (`#3645 <https://github.com/vertexproject/synapse/pull/3645>`_)

Improved Documentation
----------------------
- Update Storm pivot documentation to add additional examples.
  (`#3599 <https://github.com/vertexproject/synapse/pull/3599>`_)
- Update the Cortex deployment guide to include a step to configure a
  Storm query pool.
  (`#3602 <https://github.com/vertexproject/synapse/pull/3602>`_)

Deprecations
------------
- The tool ``synapse.tools.cellauth`` has been marked as deprecated and will
  be removed in ``v3.0.0``.
  (`#3587 <https://github.com/vertexproject/synapse/pull/3587>`_)
- The tool ``synapse.tools.cmdr`` has been marked as deprecated and will
  be removed in ``v3.0.0``.
  (`#3589 <https://github.com/vertexproject/synapse/pull/3589>`_)
- The Storm ``$lib.model.edge`` APIs have been marked as deprecated and will
  be removed in ``v3.0.0``.
  (`#3623 <https://github.com/vertexproject/synapse/pull/3623>`_)
- The ``CoreAPI.enableMigrationMode()`` and ``CoreAPI.disableMigrationMode()``
  Telepath methods have been marked as deprecated and will be removed after
  2024-05-05.
  (`#3610 <https://github.com/vertexproject/synapse/pull/3610>`_)
- The Cortex configuration options ``cron:enable`` and ``trigger:enable`` have
  been marked as deprecated and will be removed in ``v3.0.0``. These
  configuration options no longer control cron or trigger behavior.
  (`#3610 <https://github.com/vertexproject/synapse/pull/3610>`_)
- The Storm Package  ``synapse_minversion`` key has been deprecated and will
  be removed in ``v3.0.0``. Package authors should use the ``synapse_version``
  key to specify a version range for Synapse they support. An example is
  the string ``>=2.165.0,<3.0.0``.
  (`#3593 <https://github.com/vertexproject/synapse/pull/3593>`_)

v2.164.0 - 2024-03-01
=====================

Features and Enhancements
-------------------------
- Update the Beholder messages ``view:merge:init``, ``view:merge:prog``, and
  ``view:merge:fini`` to add ``merge`` and ``vote`` information.
  (`#3580 <https://github.com/vertexproject/synapse/pull/3580>`_)
- When optimizing Storm lift operations, skip lifts that would be fully
  filtered out.
  (`#3582 <https://github.com/vertexproject/synapse/pull/3582>`_)
- Add ``tmpdir`` information to the ``getSystemInfo()`` APIs. This is the
  directory that the service would use for creating any temporary files.
  (`#3583 <https://github.com/vertexproject/synapse/pull/3583>`_)
- Update the ``synapse.tools.modrole`` tool to add a ``--del`` option to
  delete a role.
  (`#3586 <https://github.com/vertexproject/synapse/pull/3586>`_)
- Add the ``reporter`` ``ou:org`` to ``ou:campaign`` nodes generated with
  ``gen.ou.campaign``
  (`#3594 <https://github.com/vertexproject/synapse/pull/3594>`_)
- The ``synapse.lib.certdir.CertDir`` class has been updated to use the
  ``cryptography`` APIs instead of the ``PyOpenSSL`` APIs where possible.
  The ``CertDir`` APIs no longer return ``PyOpenSSL`` objects, and now
  return ``cryptography`` related objects.
  (`#3568 <https://github.com/vertexproject/synapse/pull/3568>`_)
- Update the ``cryptography`` and ``PyOpenSSL`` libraries to require their
  latest versions.
  (`#3568 <https://github.com/vertexproject/synapse/pull/3568>`_)

Bugfixes
--------
- Model interfaces now populate properties for the sub-interfaces.
  (`#3582 <https://github.com/vertexproject/synapse/pull/3582>`_)
- Use ``tostr`` on property and form names when computing lifts and pivots
  to avoid a Python ``AttributeError`` exception. Invalid types will now
  raise a ``StormRuntimeException``.
  (`#3584 <https://github.com/vertexproject/synapse/pull/3584>`_)

Deprecations
------------
- The tool ``synapse.tools.cellauth`` has been marked as deprecated and will
  be removed in ``v3.0.0``.
  (`#3587 <https://github.com/vertexproject/synapse/pull/3587>`_)
- The tool ``synapse.tools.cmdr`` has been marked as deprecated and will
  be removed in ``v3.0.0``.
  (`#3589 <https://github.com/vertexproject/synapse/pull/3589>`_)

v2.163.0 - 2024-02-21
=====================

Features and Enhancements
-------------------------
- Add Storm API methods to ``$lib.axon`` which share the functionality of
  ``$lib.bytes`` APIs. These include ``$lib.axon.has``, ``$lib.axon.hashset``,
  ``$lib.axon.put``, ``$lib.axon.size``, and ``$lib.axon.upload``.
  (`#3570 <https://github.com/vertexproject/synapse/pull/3570>`_)
  (`#3576 <https://github.com/vertexproject/synapse/pull/3576>`_)
- Add support for user provided certificates for doing mTLS in Storm HTTP
  requests.
  (`#3566 <https://github.com/vertexproject/synapse/pull/3566>`_)
- Enable constructing a guid in Storm from a single value with
  ``$lib.guid(valu=$item)``.
  (`#3575 <https://github.com/vertexproject/synapse/pull/3575>`_)

v2.162.0 - 2024-02-15
=====================

Model Changes
-------------
- Updates to the ``inet``, ``infotech``,  ``ou``,  ``proj``, and ``risk`` models.
  (`#3549 <https://github.com/vertexproject/synapse/pull/3549>`_)
  (`#3551 <https://github.com/vertexproject/synapse/pull/3551>`_)
  (`#3564 <https://github.com/vertexproject/synapse/pull/3564>`_)
- See :ref:`userguide_model_v2_162_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add Storm API methods for inspecting and manipulating dictionary objects
  in Storm. These are ``$lib.dict.has()``, ``$lib.dict.keys()``,
  ``$lib.dict.pop()``, ``$lib.dict.update()``, and ``$lib.dict.values()``.
  (`#3548 <https://github.com/vertexproject/synapse/pull/3548>`_)
- Add a ``json()`` method to the ``str`` type in Storm to deserialize a string
  as JSON data.
  (`#3555 <https://github.com/vertexproject/synapse/pull/3555>`_)
- Add an ``_ahainfo`` attribute to the ``Telepath.Proxy``, containing AHA
  service name information if that is provided to the Dmon.
  (`#3552 <https://github.com/vertexproject/synapse/pull/3552>`_)
- Add permissions checks to ``$lib.bytes`` APIs using ``axon.has`` for APIs
  that check for information about the Axon or metrics; and ``axon.upload``
  for APIs which put bytes in the Axon. These are checked with
  ``default=True`` for backward compatibility.
  (`#3563 <https://github.com/vertexproject/synapse/pull/3563>`_)
- The rstorm ``storm-svc`` and ``storm-pkg`` directives now wait for any
  ``onload`` handlers to complete.
  (`#3567 <https://github.com/vertexproject/synapse/pull/3567>`_)
- Update the Synapse Python package trove classifiers to list the platforms
  we support using Synapse with.
  (`#3557 <https://github.com/vertexproject/synapse/pull/3557>`_)

Bugfixes
--------
- Fix a bug in the ``Cell.updateHttpSessInfo()`` API when the Cell does not
  have the session in memory.
  (`#3556 <https://github.com/vertexproject/synapse/pull/3556>`_)
- Fix a bug where a user was allowed to vote for their own View merge request.
  (`#3565 <https://github.com/vertexproject/synapse/pull/3565>`_)
- Include Storm variables from the current and parent scopes when resolving
  STIX properties and relationships.
  (`#3571 <https://github.com/vertexproject/synapse/pull/3571>`_)

Improved Documentation
----------------------
- Update the Storm automation documentation. Added additional information
  about permissions used to manage automations. Added examples for
  ``edge:add`` and ``edge:del`` triggers. Added examples for managing Macro
  permissions.
  (`#3547 <https://github.com/vertexproject/synapse/pull/3547>`_)
- Update the Storm filtering and lifting documentation to add information
  about using interfaces and wildcard values with those operations.
  (`#3560 <https://github.com/vertexproject/synapse/pull/3560>`_)
- Update the Synapse introduction to note that Synapse is not intended to
  replace big-data or data-lake solutions.
  (`#3553 <https://github.com/vertexproject/synapse/pull/3553>`_)

Deprecations
------------
- The Storm function ``$lib.dict()`` has been deprecated, in favor of using
  the ``({"key": "value"})`` style syntax for directly declaring a dictionary
  in Storm.
  (`#3548 <https://github.com/vertexproject/synapse/pull/3548>`_)
- Writeback layer mirrors and upstream layer mirrors have been marked as
  deprecated configuration options.
  (`#3562 <https://github.com/vertexproject/synapse/pull/3562>`_)

v2.161.0 - 2024-02-06
=====================

Features and Enhancements
-------------------------
- Add a Storm command ``gen.it.av.scan.result`` to help generate
  ``it:av:scan:result`` nodes.
  (`#3516 <https://github.com/vertexproject/synapse/pull/3516>`_)
- Add item specific error message when users do not have sufficient permissions
  on an object which is using easyperms.
  (`#3532 <https://github.com/vertexproject/synapse/pull/3532>`_)
- Ensure that Nexus events which are written to the log are always applied and
  cannot be cancelled while the Nexus handler is running.
  (`#3518 <https://github.com/vertexproject/synapse/pull/3518>`_)
- Add ``getMergeRequest()`` and ``getMergeRequestSummary()`` Storm APIs to the
  ``View`` object, in order to get information about View merges via Storm.
  (`#3541 <https://github.com/vertexproject/synapse/pull/3541>`_)
- Add AHA information to the output of the ``Cell.getCellInfo()`` API. This
  includes the service name, leader, and network.
  (`#3519 <https://github.com/vertexproject/synapse/pull/3519>`_)
- Logs related to AHA service registration and setting services as offline are
  now logged at the ``INFO`` level.
  (`#3534 <https://github.com/vertexproject/synapse/pull/3534>`_)
- When creating Cron jobs and Triggers, record their creation time.
  (`#3521 <https://github.com/vertexproject/synapse/pull/3521>`_)
  (`#3538 <https://github.com/vertexproject/synapse/pull/3538>`_)
- Add a ``Cell.updateHttpSessInfo()`` API to set multiple keys at once on a
  HTTP session.
  (`#3544 <https://github.com/vertexproject/synapse/pull/3544>`_)
- Update the allowed versions of the ``cbor2`` and `` pycryptodome``
  libraries.
  (`#3540 <https://github.com/vertexproject/synapse/pull/3540>`_)

Bugfixes
--------
- The Storm API for creating websockets, ``$lib.inet.http.connect()``, did not
  properly handle the ``ssl_verify`` argument, causing SSL verification of
  Websocket requests to default to being disabled. This argument is now
  handled correctly, with SSL verification being enabled by default.
  (`#3527 <https://github.com/vertexproject/synapse/pull/3527>`_)
- Fix a bug in embedded Storm queries where they failed to grab their variables
  properly.
  (`#3531 <https://github.com/vertexproject/synapse/pull/3531>`_)
- Fix a bad variable reference in the Storm ``graph`` implementation.
  (`#3531 <https://github.com/vertexproject/synapse/pull/3531>`_)
- Fix a bug where modifying nodes in a Storm Dmon did not properly update the
  in-flight node.
  (`#3520 <https://github.com/vertexproject/synapse/pull/3520>`_)

Improved Documentation
----------------------
- Update the Cortex admin guide with additional information about removing
  extended forms and properties.
  (`#3510 <https://github.com/vertexproject/synapse/pull/3510>`_)
- Update the Data Model documentation to include additional information about
  extended forms and properties.
  (`#3523 <https://github.com/vertexproject/synapse/pull/3523>`_)
- Update the Data Model documentation to include information about property
  interfaces.
  (`#3523 <https://github.com/vertexproject/synapse/pull/3523>`_)

v2.160.0 - 2024-01-24
=====================

Automatic Migrations
--------------------
- Update ``inet:ipv6`` nodes to set their ``:type`` and ``:scope`` properties.
  (`#3498 <https://github.com/vertexproject/synapse/pull/3498>`_)
- Update existing layer push and layer pull configurations to set the default
  chunk size and queue size values on them.
  (`#3480 <https://github.com/vertexproject/synapse/pull/3480>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Updates to the ``infotech``, ``ou``,  and ``risk`` models.
  (`#3501 <https://github.com/vertexproject/synapse/pull/3501>`_)
  (`#3504 <https://github.com/vertexproject/synapse/pull/3504>`_)
  (`#3498 <https://github.com/vertexproject/synapse/pull/3498>`_)
- See :ref:`userguide_model_v2_160_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add tab completion of commands, forms, properties, tags, and ``$lib.``
  functions the Storm CLI tool.
  (`#3493 <https://github.com/vertexproject/synapse/pull/3493>`_)
  (`#3507 <https://github.com/vertexproject/synapse/pull/3507>`_)
- Add ``node.set.<form>.<prop>`` and ``node.del.<form>.<prop>`` permissions
  conventions to the Cortex for property sets and deletes.
  (`#3505 <https://github.com/vertexproject/synapse/pull/3505>`_)
- Add experimental support for Storm query offloading to the Cortex. This can
  be used to offload Storm queries to an AHA service pool. This can be
  configured with the ``storm:pool`` option on the Cortex.
  (`#3452 <https://github.com/vertexproject/synapse/pull/3452>`_)
  (`#3513 <https://github.com/vertexproject/synapse/pull/3513>`_)
- Add a ``--deledges`` option to the ``delnode`` command. This deletes the N2
  edges for a node before deleting the node.
  (`#3503 <https://github.com/vertexproject/synapse/pull/3503>`_)
- When creating layer push or pull configurations, the chunk size and queue
  size can now be set.
  (`#3480 <https://github.com/vertexproject/synapse/pull/3480>`_)
- Add a ``cell.hasHttpSess()`` API to check if a given Cell has a known HTTP
  session.
  (`#3485 <https://github.com/vertexproject/synapse/pull/3485>`_)
- Fire a ``core:pkg:onload:complete`` event when a Storm package ``onload``
  handler is completed. This can be used when writing unit tests for Rapid
  Power-ups.
  (`#3497 <https://github.com/vertexproject/synapse/pull/3497>`_)

Bugfixes
--------
- Remove dataname index entries when removing all nodedata from a node.
  (`#3499 <https://github.com/vertexproject/synapse/pull/3499>`_)
- Fix an issue with ``tagprops`` not being correctly returned in
  ``$node.getByLayer()``.
  (`#3500 <https://github.com/vertexproject/synapse/pull/3500>`_)
- Fix an issue with the ``edges.del`` command when using the ``--n2`` option.
  This now behaves correctly when the N1 node does not exist.
  (`#3506 <https://github.com/vertexproject/synapse/pull/3506>`_)
- Fix an issue with duplicate properties being tracked in the property type
  map of the data model. This could have resulted in multiple nodes being
  lifted with interface properties.
  (`#3512 <https://github.com/vertexproject/synapse/pull/3512>`_)

Improved Documentation
----------------------
- Update Storm filter documentation. Additional information about tag globbing
  and interval filtering has been included.
  (`#3489 <https://github.com/vertexproject/synapse/pull/3489>`_)

v2.159.0 - 2024-01-16
=====================

Automatic Migrations
--------------------
- Update any extended model elements which used the ``taxonomy`` interface
  to now use the ``meta:taxonomy`` interface.
  (`#3334 <https://github.com/vertexproject/synapse/pull/3334>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Add support for lifting, pivoting, and filtering using wildcards, lists,
  variables, and interfaces as form and property names.
  (`#3334 <https://github.com/vertexproject/synapse/pull/3334>`_)
- Migrate the name of the ``taxonomy`` interface to ``meta:taxonomy``.
  (`#3334 <https://github.com/vertexproject/synapse/pull/3334>`_)
- Update the pinned version of the ``lark`` library to ``1.1.9`` for
  compatibility with Python 3.11.7.
  (`#3488 <https://github.com/vertexproject/synapse/pull/3488>`_)

Bugfixes
--------
- Prevent re-adding extended model elements in Nexus handlers.
  (`#3486 <https://github.com/vertexproject/synapse/pull/3486>`_)
- Add missing permissions checks on the ``$lib.axon.urlfile()`` API. This now
  requires the ``node.add.file:bytes`` and ``node.add.inet:urlfile``
  permissions.
  (`#3490 <https://github.com/vertexproject/synapse/pull/3490>`_)
- Fix the permission checking for Vaults to check the Storm runtime ``asroot``
  status.
  (`#3492 <https://github.com/vertexproject/synapse/pull/3492>`_)
- Fix an issue with ``$lib.stix.import.ingest()`` not converting ``bundle``
  to a dictionary.
  (`#3495 <https://github.com/vertexproject/synapse/pull/3495>`_)

Improved Documentation
----------------------
- Add documentation for the ``reverse`` keyword.
  (`#3487 <https://github.com/vertexproject/synapse/pull/3487>`_)
- Clarify the use of the "try" operator ( ``+?`` ) in edit operations.
  (`#3482 <https://github.com/vertexproject/synapse/pull/3482>`_)
  (`#3487 <https://github.com/vertexproject/synapse/pull/3487>`_)
- Update Storm lift documentation to add additional examples and clarify
  existing documentation.
  (`#3487 <https://github.com/vertexproject/synapse/pull/3487>`_)
- Update Storm data modification documentation to add additional examples and
  clarify existing documentation.
  (`#3482 <https://github.com/vertexproject/synapse/pull/3482>`_)

v2.158.0 - 2024-01-03
=====================

Features and Enhancements
-------------------------
- Update the allowed versions of the``fastjsonschema``, ``idna``, ``pygments``,
  and ``aiosmtplib`` libraries.
  (`#3478 <https://github.com/vertexproject/synapse/pull/3478>`_)

Bugfixes
--------
- Fix a bug where the ``role:add`` and ``user:add`` Nexus handlers could raise
  an exception when being called by a service mirror.
  (`#3483 <https://github.com/vertexproject/synapse/pull/3483>`_)

Improved Documentation
----------------------
- Update the Storm command reference guide.
  (`#3481 <https://github.com/vertexproject/synapse/pull/3481>`_)
- Update the Synapse glossary.
  (`#3481 <https://github.com/vertexproject/synapse/pull/3481>`_)

v2.157.0 - 2023-12-21
=====================

Features and Enhancements
-------------------------
- Added vaults feature for storing and sharing secret values (such as API
  keys) and associated configuration settings. Vaults can be shared with and
  used by another user without them being able to see the enclosed secret
  values.
  (`#3319 <https://github.com/vertexproject/synapse/pull/3319>`_)
  (`#3461 <https://github.com/vertexproject/synapse/pull/3461>`_)
- Added Storm commands to interact with vaults: ``vaults.*``.
  (`#3319 <https://github.com/vertexproject/synapse/pull/3319>`_)
- Added Storm library to interact with vaults: ``$lib.vaults.*``.
  (`#3319 <https://github.com/vertexproject/synapse/pull/3319>`_)
- Add merge request voting and history tracking for full View merges.
  (`#3466 <https://github.com/vertexproject/synapse/pull/3466>`_)
  (`#3473 <https://github.com/vertexproject/synapse/pull/3473>`_)
  (`#3475 <https://github.com/vertexproject/synapse/pull/3475>`_)
- Add service pooling support to AHA. This allows for dynamic service
  topologies and distributed Telepath API calls.
  (`#3353 <https://github.com/vertexproject/synapse/pull/3353>`_)
  (`#3477 <https://github.com/vertexproject/synapse/pull/3477>`_)
- Add user managed API keys that can be used to access HTTP API endpoints.
  (`#3470 <https://github.com/vertexproject/synapse/pull/3470>`_)
- Added an ``--optsfile`` option to the Storm CLI tool. This can be used to
  specify opts to the CLI tool via YAML. See :ref:`dev_storm_opts`  for
  details about available options.
  (`#3468 <https://github.com/vertexproject/synapse/pull/3468>`_)
- Cron status changes are now persisted through the Nexus.
  (`#3460 <https://github.com/vertexproject/synapse/pull/3460>`_)
- Add a ``show:storage`` option to the Storm runtime opts to include the
  storage node data in the ``node`` message.
  (`#3471 <https://github.com/vertexproject/synapse/pull/3471>`_)

Bugfixes
--------
- Log a warning message when calling the Python ``User.pack(packroles=True)``
  method when a user role is missing from the Auth subsystem. A missing
  role previously caused an ``AttributeError`` exception.
  (`#3469 <https://github.com/vertexproject/synapse/pull/3469>`_)
- Ensure the Nexus ``view:detach`` event is idempotent.
  (`#3474 <https://github.com/vertexproject/synapse/pull/3474>`_)
- Fix an issue where Storm subqueries containing non-runtsafe values could
  potentially not execute.
  (`#3443 <https://github.com/vertexproject/synapse/pull/3443>`_)

v2.156.0 - 2023-12-08
=====================

Model Changes
-------------
- Updates to the ``infotech``, ``ou``,  and ``risk`` models.
  (`#3436 <https://github.com/vertexproject/synapse/pull/3436>`_)
  (`#3438 <https://github.com/vertexproject/synapse/pull/3438>`_)
  (`#3446 <https://github.com/vertexproject/synapse/pull/3447>`_)
  (`#3447 <https://github.com/vertexproject/synapse/pull/3447>`_)
- See :ref:`userguide_model_v2_156_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add an ``empty`` keyword to Storm to conditionally execute queries when
  there are no nodes in the pipeline.
  (`#3434 <https://github.com/vertexproject/synapse/pull/3434>`_)
- Add Storm APIs for getting property counts for a given ``layer`` or
  ``view.``. These APIs are ``getPropCount()``, ``getPropArrayCount()``,
  ``getTagPropCount()``.
  (`#3435 <https://github.com/vertexproject/synapse/pull/3435>`_)
- Add a new permission, ``view.fork``, which can be used to control access
  for forking a view. This permission defaults to being allowed.
  (`#3437 <https://github.com/vertexproject/synapse/pull/3437>`_)
- Add Storm operators to allow pivoting and joining across light edges. The
  following examples show pivoting across ``refs`` edges and joining the
  destination nodes with the inbound nodes: ``-(refs)+>`` and ``<+(refs)-``.
  (`#3441 <https://github.com/vertexproject/synapse/pull/3441>`_)
- Add Storm operators to do pivot out and join ( ``--+>`` ) and pivot in
  and join ( ``<+--``) operations across light edges.
  (`#3441 <https://github.com/vertexproject/synapse/pull/3441>`_)
  (`#3442 <https://github.com/vertexproject/synapse/pull/3442>`_)
- Storm subqueries used to assign a value now always run.
  (`#3445 <https://github.com/vertexproject/synapse/pull/3445>`_)
- Non-runtsafe ``try...catch`` blocks in Storm now run when there are no
  inbound nodes.
  (`#3445 <https://github.com/vertexproject/synapse/pull/3445>`_)
- The Storm API ``$lib.storm.eval()`` now logs its ``text`` argument to the
  ``synapse.storm`` logger.
  (`#3448 <https://github.com/vertexproject/synapse/pull/3448>`_)
- Add a ``--by-name`` argument to the Storm ``stats.countby`` command. This
  can be used to sort the results by name instead of count.
  (`#3450 <https://github.com/vertexproject/synapse/pull/3450>`_)
- Add a new Storm API ``$lib.gis.bbox()`` to allow computing geospatial
  bounding boxes.
  (`#3455 <https://github.com/vertexproject/synapse/pull/3455>`_)

Bugfixes
--------
- Prevent recursion errors in ``inet:fqdn`` onset handlers.
  (`#3433 <https://github.com/vertexproject/synapse/pull/3433>`_)
- When dereferencing a list or dictionary object off of a Node in Storm, the
  returned value is now a copy of the value. This avoids the situation where
  modifying the deferenced value appeared to alter the node but did not
  actually result in any edits to the underlying data.
  (`#3439 <https://github.com/vertexproject/synapse/pull/3439>`_)
- Add a missing sub-query example to Storm ``for`` loop documentation.
  (`#3451 <https://github.com/vertexproject/synapse/pull/3451>`_)
- Fix an issue where attempting to norm an IPv4 with an invalid netmask
  would raise a Python error.
  (`#3459 <https://github.com/vertexproject/synapse/pull/3459>`_)

Deprecations
------------
- Deprecated Cortex and splice related APIs which were marked for removal
  after 2023-10-01 have been removed. The list of these APIs can be found
  at  :ref:`changelog-depr-20231001`. These additional splice related changes
  have also been made:

    The HTTP API ``/api/v1/storm`` now sets the default ``editformat`` opt
    value to ``nodeedits``. Previously this API produced splice changes by
    default.

    The ``synapse.tools.cmdr`` ``storm`` command no longer displays splices.

    The ``synapse.tools.cmdr`` ``log`` command no longer records splices.

    The ``synapse.tools.csvtool`` tool no longer records or displays splices.

    The ``synapse.tools.feed`` tool no longer supports splices or nodeedits as
    input and the splice documentation example has been removed.

  (`#3449 <https://github.com/vertexproject/synapse/pull/3449>`_)
- The deprecated function ``synapse.common.aclosing()`` has been removed.
  (`#3449 <https://github.com/vertexproject/synapse/pull/3449>`_)
- Provisioning a Synapse service with AHA now always updates the local CA
  certificate and generates new host and user certificates for the service.
  Previously these would not be regenerated if the CA or service names did
  not change.
  (`#3457 <https://github.com/vertexproject/synapse/pull/3457>`_)

v2.155.0 - 2023-11-17
=====================

Model Changes
-------------
- Updates to the ``infotech``, ``proj``,  and ``risk`` models.
  (`#3422 <https://github.com/vertexproject/synapse/pull/3422>`_)
- See :ref:`userguide_model_v2_155_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add a ``detach()`` method to the Storm ``view`` object. This will detach a
  forked View from its parent.
  (`#3423 <https://github.com/vertexproject/synapse/pull/3423>`_)
- Change the method used to generate the ``took`` value in the Storm ``fini``
  message to use a monotonic clock.
  (`#3425 <https://github.com/vertexproject/synapse/pull/3425>`_)
- Performing an invalid "pivot in" operation with a form target
  (``<- some:form``) now raises a ``StormRuntimeError`` instead of silently
  doing nothing.
  (`#3426 <https://github.com/vertexproject/synapse/pull/3426>`_)
- Allow relative properties on the right hand side of a filter operation
  when using Storm expression syntax.
  (`#3424 <https://github.com/vertexproject/synapse/pull/3424>`_)
- Add an ``/api/v1/logout`` method on the Cell to allow HTTPS users to logout
  of their sessions.
  (`#3430 <https://github.com/vertexproject/synapse/pull/3430>`_)
- Allow taxonomy prefix lift and filter operations to work with taxon parts.
  (`#3429 <https://github.com/vertexproject/synapse/pull/3429>`_)
- Update the allowed versions of the ``cbor2``, ``pycryptodome``,
  ``pygments``, ``vcrpy``, and ``xxhash`` libraries. Update the pinned version
  of the ``lark`` library.
  (`#3418 <https://github.com/vertexproject/synapse/pull/3418>`_)

Bugfixes
--------
- Fix a performance regression in graph projection for computing large graphs
  in Storm.
  (`#3375 <https://github.com/vertexproject/synapse/pull/3375>`_)
- Fix a conflict between Storm ``$lib.inet.http`` functions and ``vcrpy``
  where ``json`` and ``data`` args shouldn't be passed together.
  (`#3428 <https://github.com/vertexproject/synapse/pull/3428>`_)

Improved Documentation
----------------------
- Fix an error in the Cortex mirror deployment guide. The example
  ``docker-compose.yaml`` was missing the environment variables for
  ``SYN_CORTEX_AXON`` and ``SYN_CORTEX_JSONSTOR``.
  (`#3430 <https://github.com/vertexproject/synapse/pull/3430>`_)

v2.154.1 - 2023-11-15
=====================

This release is for updating the version of the ``cryptography`` package in
Synapse containers to ``41.0.5``.

v2.154.0 - 2023-11-15
=====================

Automatic Migrations
--------------------
- Update the ``inet:ipv4:type`` value for RFC6598 addresses to ``shared``.
  (`#3410 <https://github.com/vertexproject/synapse/pull/3410>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Update to the ``inet`` and ``ou`` models.

  (`#3406 <https://github.com/vertexproject/synapse/pull/3406>`_)
  (`#3407 <https://github.com/vertexproject/synapse/pull/3407>`_)
  (`#3410 <https://github.com/vertexproject/synapse/pull/3410>`_)
  (`#3416 <https://github.com/vertexproject/synapse/pull/3416>`_)
- See :ref:`userguide_model_v2_154_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add ``edge:add`` and ``edge:del`` as trigger conditions. These trigger when
  light edges are added or removed from a node.
  (`#3389 <https://github.com/vertexproject/synapse/pull/3389>`_)
- Storm lift and filter operations using regular expressions (``~=``) are now
  case insensitive by default.
  (`#3403 <https://github.com/vertexproject/synapse/pull/3403>`_)
- Add a ``unique()`` method to the Storm ``list`` object. This returns a new
  list with only unique elements in it.
  (`#3415 <https://github.com/vertexproject/synapse/pull/3415>`_)
- Add support for ``synapse.tools.autodoc`` to generate documentation for
  API definitions declared in Storm packages.
  (`#3382 <https://github.com/vertexproject/synapse/pull/3382>`_)
- A review of Storm library functions was performed and all ``readonly`` safe
  functions have been marked for execution in a ``readonly`` Storm runtime.
  (`#3402 <https://github.com/vertexproject/synapse/pull/3402>`_)
- Allow setting the layers on a root View with forks.
  (`#3413 <https://github.com/vertexproject/synapse/pull/3413>`_)

Bugfixes
--------
- Per-node Storm variables are now passed into subquery assignment
  expressions.
  (`#3405 <https://github.com/vertexproject/synapse/pull/3405>`_)
- Fix an issue with Storm Dmon hive storage being opened too late in the
  Cortex startup sequence.
  (`#3411 <https://github.com/vertexproject/synapse/pull/3411>`_)
- Remove a check when deleting tags from a node which prevented tag deletion
  from a node when the root tag was deleted in a parent view.
  (`#3408 <https://github.com/vertexproject/synapse/pull/3408>`_)

v2.153.0 - 2023-10-27
=====================

Model Changes
-------------
- Update to the ``inet`` and ``ou`` models.
  (`#3393 <https://github.com/vertexproject/synapse/pull/3393>`_)
  (`#3396 <https://github.com/vertexproject/synapse/pull/3396>`_)
- See :ref:`userguide_model_v2_153_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add a new Storm API, ``$lib.cortex.httpapi``, for creating and managing
  Extended HTTP API endpoints. These Cortex HTTP API endpoints allow a user to
  create custom responses via Storm. Documentation for this feature can be
  found at :ref:`devops-svc-cortex-ext-http`.
  (`#3366 <https://github.com/vertexproject/synapse/pull/3366>`_)
- Add a new Storm API, ``$lib.iters.zip()``, to iterate over sequences of
  items together.
  (`#3392 <https://github.com/vertexproject/synapse/pull/3392>`_)
  (`#3398 <https://github.com/vertexproject/synapse/pull/3398>`_)
- Add a Storm command ``stats.countby`` to tally occurrences of values and
  display a barchart representing the values.
  (`#3385 <https://github.com/vertexproject/synapse/pull/3385>`_)
- Update the Storm command ``auth.user.mod`` to allow setting a user as admin
  on a specific auth gate.
  (`#3391 <https://github.com/vertexproject/synapse/pull/3391>`_)
- The ``proxy`` argument to ``$lib.inet.http.*``, ``$lib.axon.wget()``,
  ``$lib.axon.urlfile()``, and ``$lib.axon.wput()`` APIs is now gated behind
  the permission ``storm.lib.inet.http.proxy``. Previously this required
  admin permission to utilize.
  (`#3397 <https://github.com/vertexproject/synapse/pull/3397>`_)
- Add an ``errors`` parameter to ``$lib.axon.readlines()``,
  ``$lib.axon.csvrows()``, and ``$lib.axon.jsonlines()``. This parameter
  defaults to ``ignore`` to ignore any decoding errors that are encountered
  when decoding text.
  (`#3395 <https://github.com/vertexproject/synapse/pull/3395>`_)
- Lower the maximum allowed version of the ``pyopenssl`` library.
  (`#3399 <https://github.com/vertexproject/synapse/pull/3399>`_)

Bugfixes
--------
- Fix a bug in the ``Cortex.syncLayersEvents()`` and
  ``Cortex.syncIndexEvents()`` APIs which caused layers to stop sending their
  node edits under certain conditions.
  (`#3394 <https://github.com/vertexproject/synapse/pull/3394>`_)
- Storm now raises a ``BadSyntaxError`` when attempting to filter by wildcard
  tags or tagprops when a value is specified for the filter.
  (`#3373 <https://github.com/vertexproject/synapse/pull/3373>`_)

v2.152.0 - 2023-10-17
=====================

Model Changes
-------------
- Update to the  ``biz``, ``crypto``, ``geo``, ``it``, ``mat``, ``media``,
  and ``risk`` models.
  (`#3341 <https://github.com/vertexproject/synapse/pull/3341>`_)
  (`#3377 <https://github.com/vertexproject/synapse/pull/3377>`_)
  (`#3376 <https://github.com/vertexproject/synapse/pull/3376>`_)
  (`#3381 <https://github.com/vertexproject/synapse/pull/3381>`_)
- See :ref:`userguide_model_v2_152_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Update the Storm string repr for ``$lib.null`` and ``$lib.undef`` values to
  ``$lib.null`` and ``$lib.undef``. Previously these printed ``None`` and an
  opaque Python object repr.
  (`#3361 <https://github.com/vertexproject/synapse/pull/3361>`_)
- The ``synapse.tools.aha.list`` CLI tool now checks if it is connected to an
  Aha server prior to enumerating Aha services.
  (`#3371 <https://github.com/vertexproject/synapse/pull/3371>`_)

Bugfixes
--------
- Update the ``file:path`` support for scrape related APIs to address an
  issue when matching against Linux style paths.
  (`#3378 <https://github.com/vertexproject/synapse/pull/3378>`_)
- Update the ``hex`` type to ``zeropad`` strings prior to checking their
  validity.
  (`#3387 <https://github.com/vertexproject/synapse/pull/3387>`_)
- Update the ``yaml.CSafeLoader`` check to not require the class to be
  available.
  (`#3386 <https://github.com/vertexproject/synapse/pull/3386>`_)

Improved Documentation
----------------------
- Update the documentation for the Storm ``view.exec`` command to explain the
  separation of events and nodes between the parent and sub-runtimes.
  (`#3379 <https://github.com/vertexproject/synapse/pull/3379>`_)

v2.151.0 - 2023-10-06
=====================

Model Changes
-------------
- Update to the ``it`` model.
  (`#3361 <https://github.com/vertexproject/synapse/pull/3361>`_)
- See :ref:`userguide_model_v2_151_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add a new Storm library ``$lib.infosec.mitre.attack.flow``. This can be used
  to normalize and create ``it:mitre:attack:flow`` nodes from MITRE ATT&CK
  Flow Diagrams.
  (`#3361 <https://github.com/vertexproject/synapse/pull/3361>`_)
  (`#3372 <https://github.com/vertexproject/synapse/pull/3372>`_)
- Update the Storm ``note.add`` command to set the ``meta:note:created``
  property on the note.
  (`#3569 <https://github.com/vertexproject/synapse/pull/3569>`_)
- Add the Axon HTTP APIs to the Cortex. These API endpoints use the Axon that
  the Cortex is configured to use.
  (`#3550 <https://github.com/vertexproject/synapse/pull/3550>`_)
- Allow user defined functions in Storm to execute in a ``readonly`` Storm
  runtime.
  (`#3552 <https://github.com/vertexproject/synapse/pull/3552>`_)
- Clarify the Nexus ``IsReadOnly`` exception to include the common cause for
  the error, which is normally insufficent space on disk.
  (`#3359 <https://github.com/vertexproject/synapse/pull/3359>`_)
- Add a ``SYN_LOG_DATEFORMAT`` environment variable to allow specifying custom
  timestamp formats for Synapse services.
  (`#3362 <https://github.com/vertexproject/synapse/pull/3362>`_)
- Add a ``status`` attribute to structured log events for user and role
  related log events. This attribute indicates if the event was a ``CREATE``,
  ``DELETE``, or ``MODIFY`` operation.
  (`#3363 <https://github.com/vertexproject/synapse/pull/3363>`_)
- Update ``Cell.getLogExtra()`` to prefer using the ``user`` key from the task
  scope before using the ``sess`` key from the task scope. Cortex APIs which
  execute Storm queries now set the ``user`` scope to the user the query is
  running as. This increases the accuracy of log events caused by Storm
  queries when the ``user`` is specified in the ``opts``.
  (`#3356 <https://github.com/vertexproject/synapse/pull/3356>`_)
- Update Storm setitem AST operator to check the readonly flag on functions
  when operating in a ``readonly`` Storm runtime.
  (`#3364 <https://github.com/vertexproject/synapse/pull/3364>`_)
- Update the minimum required version of the ``fastjsonschema`` library.
  (`#3358 <https://github.com/vertexproject/synapse/pull/3358>`_)
- Update tests and remove the use of deprecated functions for improved
  Python 3.12 compatibility.
  (`#3355 <https://github.com/vertexproject/synapse/pull/3355>`_)
  (`#3567 <https://github.com/vertexproject/synapse/pull/3567>`_)

Bugfixes
--------
- Fixed a bug when parenting a View to another View where the bottom view has
  more than one layer in it omitted non-write layers. The set of layers is now
  properly computed.
  (`#3354 <https://github.com/vertexproject/synapse/pull/3354>`_)

Improved Documentation
----------------------
- Update the list of Cortex permissions in the Admin Guide.
  (`#3331 <https://github.com/vertexproject/synapse/pull/3331>`_)
- The Form documentation has been updated to project the secondary properties
  and associated light edges as tables.
  (`#3348 <https://github.com/vertexproject/synapse/pull/3348>`_)


v2.150.0 - 2023-09-22
=====================

Model Changes
-------------
- Updates to the ``inet`` model.
  (`#3347 <https://github.com/vertexproject/synapse/pull/3347>`_)
- See :ref:`userguide_model_v2_150_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Allow Storm trigger APIs to reference triggers from other views.
  (`#3342 <https://github.com/vertexproject/synapse/pull/3342>`_)
- Update the ``synapse.lib.scrape`` and associated APIs to capture
  additional data:
  (`#3223 <https://github.com/vertexproject/synapse/pull/3223>`_)
  (`#3347 <https://github.com/vertexproject/synapse/pull/3347>`_)

  ``it:sec:cpe``
    CPE 2.3 strings are now identified.

  ``inet:url``
    UNC based paths are now identified.

- Update the ``synapse.lib.scrape`` and associated APIs to use subprocesses
  when scraping large volumes of text.
  (`#3344 <https://github.com/vertexproject/synapse/pull/3344>`_)
- Add additional logging for HTTP API endpoints when a request has invalid
  login information.
  (`#3345 <https://github.com/vertexproject/synapse/pull/3345>`_)
- The CryoTank service has had permissions added to it.
  (`#3328 <https://github.com/vertexproject/synapse/pull/3328>`_)

Bugfixes
--------
- Stormtypes ``stor`` functions were not previously checked during
  ``readonly`` runtime execution. These are now validated and ``stor``
  functions which would result in changing data in the Cortex will now
  raise an exception when used with a ``readonly`` Storm runtime.
  (`#3349 <https://github.com/vertexproject/synapse/pull/3349>`_)

Improved Documentation
----------------------
- Update the list of Cortex permissions in the Admin Guide.
  (`#3331 <https://github.com/vertexproject/synapse/pull/3331>`_)
- The Form documentation has been updated to project the secondary properties
  and associated light edges as tables.
  (`#3348 <https://github.com/vertexproject/synapse/pull/3348>`_)

v2.149.0 - 2023-09-14
=====================

Model Changes
-------------
- Updates to the ``it``, ``meta``, and ``ou`` models.
  (`#3338 <https://github.com/vertexproject/synapse/pull/3338>`_)
- See :ref:`userguide_model_v2_149_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add best-effort support to scrape APIs to identify Windows and Linux file
  paths.
  (`#3343 <https://github.com/vertexproject/synapse/pull/3343>`_)
- Update the Storm ``view.add`` command to add a ``--worldreadable`` flag to
  create a view which is readable by the ``all`` role. The ``$lib.view.add()``
  Storm API now also accepts an optional ``worldreadable`` argument as well.
  (`#3333 <https://github.com/vertexproject/synapse/pull/3333>`_)
- Update the Storm ``note.add`` command to add a ``--yield`` flag which yields
  the newly created note.
  (`#3337 <https://github.com/vertexproject/synapse/pull/3337>`_)
- Add Storm commands ``gen.ou.id.number`` and ``gen.ou.id.type`` to help
  generate ``ou:id:number`` and ``ou:id:type`` nodes.
  (`#3339 <https://github.com/vertexproject/synapse/pull/3339>`_)
- Support dynamically setting a Layer to ``readonly`` using the Storm
  ``$layer.set()`` API.
  (`#3332 <https://github.com/vertexproject/synapse/pull/3332>`_)
- Update the Storm command ``help`` to display information about Storm types,
  Storm Libraries and functions.
  (`#3335 <https://github.com/vertexproject/synapse/pull/3335>`_)

Bugfixes
--------
- Ensure that the Cell ``tmp`` directory is on the same volume as the Cell
  storage directory prior to attempting to run the onboot optimization
  process. If the volumes are different this now issues a warning message and
  skips the optimization process.
  (`#3336 <https://github.com/vertexproject/synapse/pull/3336>`_)
- Protect the Cortex Cron scheduling loop from errors that could happen when
  starting an agenda item.
  (`#3340 <https://github.com/vertexproject/synapse/pull/3340>`_)

v2.148.0 - 2023-09-05
=====================

Features and Enhancements
-------------------------
- Add a ``$lib.jsonstor.cachedel()`` API to allow for the removal of data
  created by ``$lib.jsonstor.cacheget()``.
  (`#3322 <https://github.com/vertexproject/synapse/pull/3322>`_)

Bugfixes
--------
- Ensure the base Cell ``fini()``'s the Aha client that it creates. This fixes
  a unit test performance issue.
  (`#3324 <https://github.com/vertexproject/synapse/pull/3324>`_)

Deprecations
------------
- Mark the following Cryotank related API arguments and functions as
  deprecated. These APIs are related to server-side offset tracking for
  callers. Code which relies on these should be updated to do local offset
  tracking. These APIs and arguments will be removed in v2.150.0.
  (`#3326 <https://github.com/vertexproject/synapse/pull/3326>`_)

    - ``CryoApi.puts(seqn=...)`` argument.
    - ``CryoApi.rows(seqn=...)`` argument.
    - ``CryoApi.slice(iden=...)`` argument.
    - ``CryoApi.offset()`` function.
    - ``CryoTank.getOffset()`` function.
    - ``CryoTank.setOffset()`` function.
    - ``CryoTank.puts(seqn=...)`` argument.
    - ``CryoTank.rows(seqn=...)`` argument.
    - ``CryoTank.slice(iden=...)`` argument.
    - ``TankAPI.offset()`` function.
    - ``TankApi.puts(seqn=...)`` argument.
    - ``TankAPI.slice(iden=...)`` argument.

v2.147.0 - 2023-08-31
=====================

Features and Enhancements
-------------------------
- Add ``wait`` and ``timeout`` arguments to Cryotank ``slice()`` APIs.
  (`#3320 <https://github.com/vertexproject/synapse/pull/3320>`_)
- Add a ``charset`` parameter to the Storm ``inet:imap:server.search()`` API.
  This can be used to specify the ``CHARSET`` value when crafting a search
  query.
  (`#3318 <https://github.com/vertexproject/synapse/pull/3318>`_)

Bugfixes
--------
- Vendor the ``asyncio.timeouts.Timeout`` class from Python 3.11.3 to ensure
  correct task cancellation behavior is available for
  ``synapse.common.wait_for()``.
  (`#3321 <https://github.com/vertexproject/synapse/pull/3321>`_)

v2.146.0 - 2023-08-29
=====================

Features and Enhancements
-------------------------
- Update Storm ``graph`` projection to only include edges between nodes in the
  result set and include a `"reverse": true` in the edge info when embedding
  an edge on its target node once it is yielded.
  (`#3305 <https://github.com/vertexproject/synapse/pull/3305>`_)
- Map the Nexus LMDB slab with ``map_async=True`` by default.
  (`#3314 <https://github.com/vertexproject/synapse/pull/3314>`_)
- Mark the Storm ``macro.exec`` as a ``readonly`` safe command. Mark the
  Storm APIs ``$lib.macro.list()`` and ``$lib.macro.get()`` as ``readonly``
  safe. Mark the ``str`` APIs as ``readonly`` safe.
  (`#3316 <https://github.com/vertexproject/synapse/pull/3316>`_)

Bugfixes
--------
- Fix an issue where Layer data migrations failed when a layer was marked
  as ``readonly``.
  (`#3313 <https://github.com/vertexproject/synapse/pull/3313>`_)
- Fix an issue where utility functions for packed nodes in
  ``synapse.lib.node`` did not handle nodes from HTTP API endpoints.
  (`#3315 <https://github.com/vertexproject/synapse/pull/3315>`_)

v2.145.0 - 2023-08-25
=====================

Automatic Migrations
--------------------
- Update indexing for light edges to index the N1 and N2 node identifiers
  together.
  (`#3302 <https://github.com/vertexproject/synapse/pull/3302>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Update to the ``inet``, ``it``, and ``meta`` models.
  (`#3285 <https://github.com/vertexproject/synapse/pull/3285>`_)
  (`#3298 <https://github.com/vertexproject/synapse/pull/3298>`_)
  (`#3301 <https://github.com/vertexproject/synapse/pull/3301>`_)
  (`#3310 <https://github.com/vertexproject/synapse/pull/3310>`_)
- See :ref:`userguide_model_v2_145_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add a new Storm keyword, ``reverse( ... )``, which can be used to run a lift
  operation in reverse order.
  (`#3266 <https://github.com/vertexproject/synapse/pull/3266>`_)
- Update indexing for light edges to index the N1 and N2 node identifiers
  together.
  (`#3302 <https://github.com/vertexproject/synapse/pull/3302>`_)
- Update the Storm ``once`` command behavior and documentation to be more
  intuitive when setting its timestamp and allowing nodes through it.
  (`#3282 <https://github.com/vertexproject/synapse/pull/3282>`_)
- Add a ``synapse_version`` key to the Storm Package schema. This can be used
  to provide a string version indentifier with a minimum and maximum version,
  such as ``>=2.145.0,<3.0.0``.
  (`#3304 <https://github.com/vertexproject/synapse/pull/3304>`_)
- Update the Storm runtime to respect permissions declared with a ``default``
  value of ``true``. This allows Storm packages to define permissions which
  are defaulted to ``true``.
  (`#3287 <https://github.com/vertexproject/synapse/pull/3287>`_)
- Add a ``SIGHUP`` handler to the base Cell which can be used to reload HTTPS
  certificate files from disk. The ``synapse.tools.reload`` tool can also be
  used to trigger this behavior.
  (`#3293 <https://github.com/vertexproject/synapse/pull/3293>`_)
- The optional ``max:users`` feature no longer counts ``locked`` or
  ``archived`` users when adding users.
  (`#3295 <https://github.com/vertexproject/synapse/pull/3295>`_)
- Update the YAML functions to use the ``yaml.CSafeLoader`` and
  ``yaml.CSafeDumper``.
  (`#3289 <https://github.com/vertexproject/synapse/pull/3289>`_)

Bugfixes
--------
- Replace ``asyncio.wait_for()`` use with a copy of the Python 3.12
  implementation to avoid a race condition when cancelling tasks.
  (`#3299 <https://github.com/vertexproject/synapse/pull/3299>`_)
  (`#3307 <https://github.com/vertexproject/synapse/pull/3307>`_)
- Fix an issue with the Storm trigger ``set()`` method not properly checking
  the values that it allows to be set.
  (`#3290 <https://github.com/vertexproject/synapse/pull/3290>`_)
- Fix an off-by-one bug in the ``SlabSeqn.aiter()`` method.
  (`#3300 <https://github.com/vertexproject/synapse/pull/3300>`_)
- Fix a performance issue with the IPv6 regular expression used in the scrape
  APIs.
  (`#3311 <https://github.com/vertexproject/synapse/pull/3311>`_)

Improved Documentation
----------------------
- Revise the Storm User Guide to consolidate the background information
  and data modeling sections. Add a user focused section on Views and Layers.
  (`#3303 <https://github.com/vertexproject/synapse/pull/3303>`_)
- Add ``int`` type specific information to the Storm documentation.
  (`#3288 <https://github.com/vertexproject/synapse/pull/3288>`_)
- The Storm ``movetag`` command now moves the ``doc:url`` property from the
  old ``syn:tag`` node to the new ``syn:tag`` node.
  (`#3294 <https://github.com/vertexproject/synapse/pull/3294>`_)
- Storm Library and Type documentation no longer renders function signatures
  with Python style defaults.
  (`#3296 <https://github.com/vertexproject/synapse/pull/3296>`_)

Deprecations
------------
- Many deprecated Cortex and splice related APIs have been marked for removal
  after 2023-10-01.  The full list of APIs which will be removed can be found
  at :ref:`changelog-depr-20231001`.
  (`#3292 <https://github.com/vertexproject/synapse/pull/3292>`_)
- The use of ``synapse.common.aclosing()`` has been replaced with
  ``contextlib.aclosing()``.  The vendored ``aclosing()`` implementation will
  be removed in ``v2.250.0``.
  (`#3206 <https://github.com/vertexproject/synapse/pull/3206>`_)

v2.144.0 - 2023-08-09
=====================

Model Changes
-------------
- Updates to the ``inet:dns`` and ``it`` model.
  (`#3257 <https://github.com/vertexproject/synapse/pull/3257>`_)
  (`#3276 <https://github.com/vertexproject/synapse/pull/3276>`_)
- See :ref:`userguide_model_v2_144_0` for more detailed model changes.

Features and Enhancements
-------------------------
- The iden of the Cron job is now added to the Storm query log made with
  the ``synapse.storm`` logger when using structured logging.
  (`#3235 <https://github.com/vertexproject/synapse/pull/3235>`_)
- Add a ``keepalive`` option to the Storm query ``opts``. This may be used
  with long-running Storm queries when behind a network proxy or load balancer
  which may terminate idle connections.
  (`#3272 <https://github.com/vertexproject/synapse/pull/3272>`_)
- Update the allowed versions of the ``cryptography`` library.
  (`#3281 <https://github.com/vertexproject/synapse/pull/3281>`_)

Bugfixes
--------
- Fix an issue where Storm Dmons could start prior to data model migrations.
  (`#3279 <https://github.com/vertexproject/synapse/pull/3279>`_)
- Adjust the storage convention for ``once`` state data to fix an edge case
  and clarify documentation.
  (`#3282 <https://github.com/vertexproject/synapse/pull/3282>`_)
- Fix an issue with missing keys in storage nodes during migrations.
  (`#3284 <https://github.com/vertexproject/synapse/pull/3284>`_)


v2.143.0 - 2023-07-28
=====================

Model Changes
-------------
- Update to the ``crypto`` model.
  (`#3256 <https://github.com/vertexproject/synapse/pull/3256>`_)
- See :ref:`userguide_model_v2_143_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add ``$lib.model.ext.getExtModel()`` and
  ``$lib.model.ext.addExtModel()`` Storm APIs to get all the extended model
  definitions in a Cortex and to add extended model definitions to
  a Cortex in bulk.
  (`#3252 <https://github.com/vertexproject/synapse/pull/3252>`_)
- Add ``inet:ipv6`` to the list of types identified with scrape APIs. The
  ``inet:server`` form identified by scrape APIs now also identifies IPv6
  server addresses.
  (`#3259 <https://github.com/vertexproject/synapse/pull/3259>`_)
- Add a check to the Cortex startup to identify and log the presence of
  deprecated model elements and direct users to check and lock them
  at :ref:`storm-model-deprecated-check`.
  (`#3253 <https://github.com/vertexproject/synapse/pull/3253>`_)
  (`#3264 <https://github.com/vertexproject/synapse/pull/3264>`_)
- Add a new Storm function, ``$lib.vars.type()``,  to get the type
  value of an object.
  (`#3100 <https://github.com/vertexproject/synapse/pull/3100>`_)
- Add a Storm library, ``$lib.pack``, for packing and unpacking structured
  byte values.
  (`#3261 <https://github.com/vertexproject/synapse/pull/3261>`_)
- The Storm ``$lib.gen()`` functions and associated commands now generate
  stable guid values based on their inputs when making nodes.
  (`#3268 <https://github.com/vertexproject/synapse/pull/3268>`_)
- Add the ``.bazar`` TLD to the list of TLDs identified by the Synapse scrape
  functionality.
  (`#3271 <https://github.com/vertexproject/synapse/pull/3271>`_)
- Add the View iden to the task identifier for running Storm tasks.
  (`#3247 <https://github.com/vertexproject/synapse/pull/3247>`_)
- Add performance related sysctl values to the output of the Storm
  ``Cell.getSystemInfo()`` and ``$lib.cell.getSystemInfo()`` APIs.
  (`#3236 <https://github.com/vertexproject/synapse/pull/3236>`_)
- Update the allowed versions of the ``vcrpy`` library. Thank you
  ``captainGeech42`` for the contribution.
  (`#3204 <https://github.com/vertexproject/synapse/pull/3204>`_)

Bugfixes
--------
- Ensure the input to the ``CoreAPI.storm()`` ( and related APIs ) is a
  string.
  (`#3255 <https://github.com/vertexproject/synapse/pull/3255>`_)
  (`#3269 <https://github.com/vertexproject/synapse/pull/3269>`_)
- Fix a bug in ``synapse.tools.aha.enroll`` where a user with a
  ``telepath.yaml`` file containing an ``aha:servers`` key with a list of
  lists failed to enroll a local user.
  (`#3260 <https://github.com/vertexproject/synapse/pull/3260>`_)
- Fix an issue where Storm functions using ``emit`` failed to cleanup their
  sub-runtimes.
  (`#3250 <https://github.com/vertexproject/synapse/pull/3250>`_)
- Add verification that a Storm function call is being made on a callable
  object and raise a ``StormRuntimeError`` if the object cannot be called.
  Previously invalid calls could raise a ``TypeError``.
  (`#3243 <https://github.com/vertexproject/synapse/pull/3243>`_)
- Fix the order of the Beholder ``cron:stop`` message firing when a Cron job
  is stopped.
  (`#3265 <https://github.com/vertexproject/synapse/pull/3265>`_)

Improved Documentation
----------------------
- Add a section to the Storm reference for user defined functions in Storm.
  That can be found at :ref:`storm-adv-functions`.
  (`#3245 <https://github.com/vertexproject/synapse/pull/3245>`_)
- Update the devops documentation to add a note about the Telepath ``aha://``
  protocol using a ``mirror=true`` parameter to connect to a service mirror
  instead of a leader.
  (`#3267 <https://github.com/vertexproject/synapse/pull/3267>`_)
- Update the ``preboot.sh`` example script to account for Docker changes
  introduced in ``v2.133.0``.

v2.142.2 - 2023-07-19
=====================

Bugfixes
--------
- Fix an issue which caused the Docker image tags for
  ``vertexproject/synapse-cryotank:v2.141.1``,
  ``vertexproject/synapse-jsonstor:v2.141.1``, and
  ``vertexproject/synapse-stemcell:v2.141.1``, to refer to same image.
  (`#3249 <https://github.com/vertexproject/synapse/pull/3249>`_)

v2.142.1 - 2023-07-19
=====================

Bugfixes
--------
- Fix an issue which prevented the publication of the Synapse containers with
  ``v2.x.x`` tags.
  (`#3248 <https://github.com/vertexproject/synapse/pull/3248>`_)

v2.142.0 - 2023-07-19
=====================

Automatic Migrations
--------------------
- Renormalize the ``risk:vuln:cvss:v2`` and ``risk:vuln:cvss:v3`` properties.
  (`#3224 <https://github.com/vertexproject/synapse/pull/3224>`_)
- Migrate the ``risk:vuln:name`` type from a ``str`` to a ``risk:vulnname``
  form.
  (`#3227 <https://github.com/vertexproject/synapse/pull/3227>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Update to the ``it``, ``ou``, and  ``risk`` models.
  (`#3224 <https://github.com/vertexproject/synapse/pull/3224>`_)
  (`#3227 <https://github.com/vertexproject/synapse/pull/3227>`_)
  (`#3237 <https://github.com/vertexproject/synapse/pull/3237>`_)
- See :ref:`userguide_model_v2_142_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Always convert dictionary keys to their primitive values when working with
  dictionary objects in Storm. Dictionary objects can no longer have keys
  set which are mutable objects, such as Nodes.
  (`#3233 <https://github.com/vertexproject/synapse/pull/3233>`_)
- Add support for octal constants, such as ``0o755``, in Storm expressions.
  (`#3231 <https://github.com/vertexproject/synapse/pull/3231>`_)
- Add additional events to the Behold API message stream for the addition
  and removal of extended model elements.
  (`#3228 <https://github.com/vertexproject/synapse/pull/3228>`_)
- Update the ``$lib.dmon.add()`` variable capture to record variables
  from embedded query objects.
  (`#3230 <https://github.com/vertexproject/synapse/pull/3230>`_)
- Add a ``.title()`` method on Storm strings to get title case formatted
  strings.
  (`#3242 <https://github.com/vertexproject/synapse/pull/3242>`_)
- Add a general purpose process pool using forked workers in order to speed
  up certain processing operations. This includes the Storm operations for
  JSONSchema parsing, HTML parsing, STIX validation, and XML parsing.
  (`#3033 <https://github.com/vertexproject/synapse/pull/3033>`_)
  (`#3229 <https://github.com/vertexproject/synapse/pull/3229>`_)
- Add a new Cell configuration option, ``max:users``. This can be set to limit
  the maximum number of non-``root`` users on Cell.
  (`#3244 <https://github.com/vertexproject/synapse/pull/3244>`_)
- Add an ``/api/v1/aha/services`` HTTP API to the Aha service. This
  can be used to get a list of the services registered with Aha.
  (`#3238 <https://github.com/vertexproject/synapse/pull/3238>`_)
- Add support for Cosign signatures of tagged Synapse containers. See
  additional information at :ref:`dev_docker_verification`.
  (`#3196 <https://github.com/vertexproject/synapse/pull/3196>`_)
- Adjust internal names for Storm objects.
  (`#3229 <https://github.com/vertexproject/synapse/pull/3229>`_)

Bugfixes
--------
- Fix a bug in the scrape for ``inet:ipv4`` where IP addresses were found
  when there was leading or trailing numbers around the IP addresses.
  (`#3234 <https://github.com/vertexproject/synapse/pull/3234>`_)
- Fix a bug where ``$lib.model.ext.delForm()`` did not check for extended
  property definitions before deletion. Extended properties on a custom form
  must be deleted prior to deleting the form.
  (`#3223 <https://github.com/vertexproject/synapse/pull/3223>`_)
- Always remove the ``mirror`` configuration option from ``cell.yaml`` file
  when provisioning a service via Aha. The previous behavior prevented the
  correct restoration of a service from a backup which was previously
  provisioned as a mirror and is being restored as a leader.
  (`#3240 <https://github.com/vertexproject/synapse/pull/3240>`_)
- Add additional type checking when adding extended model forms and properties
  to the Cortex. Previously invalid types could raise an ``AttributeError``.
  (`#3243 <https://github.com/vertexproject/synapse/pull/3243>`_)

Improved Documentation
----------------------
- Update the Storm lift reference to add an example of lifting nodes by the
  universal ``.created`` property.
  (`#3245 <https://github.com/vertexproject/synapse/pull/3245>`_)

v2.141.0 - 2023-07-07
=====================

Model Changes
-------------
- Update to the ``it`` and ``lang`` models.
  (`#3219 <https://github.com/vertexproject/synapse/pull/3219>`_)
- See :ref:`userguide_model_v2_141_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Update ``$lib.infosec.cvss.vectToScore()`` to include a normalized
  CVSS vector in the output.
  (`#3211 <https://github.com/vertexproject/synapse/pull/3211>`_)
- Optimize the addition and removal of lightweight edges when operating
  on N1 edges in Storm.
  (`#3214 <https://github.com/vertexproject/synapse/pull/3214>`_)
- Added ``$lib.gen.langByCode``.
  (`#3219 <https://github.com/vertexproject/synapse/pull/3219>`_)

Bugfixes
--------
- Fix bug with regular expression comparisons for some types.
  (`#3213 <https://github.com/vertexproject/synapse/pull/3213>`_)
- Fix a ``TypeError`` being raised when passing a heavy Number object to
  ``$lib.math.number()``.
  (`#3215 <https://github.com/vertexproject/synapse/pull/3215>`_)
- Fix an issue with the Cell backup space checks. They now properly calculate
  the amount of free space when the Cell backup directory is configured
  on a separate volume from the Cell storage directory.
  (`#3216 <https://github.com/vertexproject/synapse/pull/3216>`_)
- Prevent the ``yield`` operator from directly emitting nodes into the Storm
  pipeline if those node objects came from a different view. Nodes previously
  lifted in this manner must be lifted by calling the ``iden()`` function on
  the object to ensure the node being lifted into the pipeline reflects the
  current view.
  (`#3218 <https://github.com/vertexproject/synapse/pull/3218>`_)
- Always remove the ``mirror`` configuration option from ``cell.mods.yaml``
  when provisioning a service via Aha. The previous behavior prevented the
  correct restoration of a service from a backup which had been changed from
  being a leader to being a mirror.
  (`#3220 <https://github.com/vertexproject/synapse/pull/3220>`_)

v2.140.1 - 2023-06-30
=====================

Bugfixes
--------
- Fix a typo which prevented the Synapse package for ``v2.140.0`` from being
  published on PyPI.
  (`#3212 <https://github.com/vertexproject/synapse/pull/3212>`_)

v2.140.0 - 2023-06-30
=====================

Announcement
------------

Synapse now only supports Python 3.11+.

Model Changes
-------------
- Update to the ``inet``, ``file``, and ``ou`` models.
  (`#3192 <https://github.com/vertexproject/synapse/pull/3192>`_)
  (`#3202 <https://github.com/vertexproject/synapse/pull/3202>`_)
  (`#3207 <https://github.com/vertexproject/synapse/pull/3207>`_)
- See :ref:`userguide_model_v2_140_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Synapse now only supports Python 3.11+. The library will now fail to import
  on earlier Python interpeters, and the published modules on PyPI will no
  longer install on Python versions < 3.11.
  (`#3156 <https://github.com/vertexproject/synapse/pull/3156>`_)
- Replace ``setup.py`` with a ``pyproject.toml`` file.
  (`#3156 <https://github.com/vertexproject/synapse/pull/3156>`_)
  (`#3195 <https://github.com/vertexproject/synapse/pull/3195>`_)
- Usages of ``hashlib.md5()`` and ``hashlib.sha1()`` have been updated to add
  the ``usedforsecurity=False`` argument.
  (`#3163 <https://github.com/vertexproject/synapse/pull/3163>`_)
- The Storm ``diff`` command is now marked as safe for ``readonly`` execution.
  (`#3207 <https://github.com/vertexproject/synapse/pull/3207>`_)
- Add a ``svc:set`` event to the Behold API message stream. This event is
  fired when a Cortex connects to a Storm Service.
  (`#3205 <https://github.com/vertexproject/synapse/pull/3205>`_)

Bugfixes
--------
- Catch ``ZeroDivisionError`` and ``decimal.InvalidOperation`` errors in Storm
  expressions and raise a ``StormRuntimeError``.
  (`#3203 <https://github.com/vertexproject/synapse/pull/3203>`_)
- Fix a bug where ``synapse.lib.platforms.linux.getTotalMemory()`` did not
  return the correct value in a process running in cgroupsv1 without a
  maximum memory limit set.
  (`#3198 <https://github.com/vertexproject/synapse/pull/3198>`_)
- Fix a bug where a Cron job could be created with an invalid Storm query.
  Cron jobs now have their queries parsed as part of creation to ensure that
  they are valid Storm. ``$lib.cron`` APIs now accept heavy Storm query
  objects as query inputs.
  (`#3201 <https://github.com/vertexproject/synapse/pull/3201>`_)
  (`#3207 <https://github.com/vertexproject/synapse/pull/3207>`_)
- Field data sent via Storm ``$lib.inet.http`` APIs that uses a multipart
  upload without a valid ``name`` field now raises a ``BadArg`` error.
  Previously this would result in a Python ``TypeError``.
  (`#3199 <https://github.com/vertexproject/synapse/pull/3199>`_)
  (`#3206 <https://github.com/vertexproject/synapse/pull/3206>`_)

Deprecations
------------
- Remove the deprecated ``synapse.common.lockfile()`` function.
  (`#3191 <https://github.com/vertexproject/synapse/issue/3191>`_)

v2.139.0 - 2023-06-16
=====================

Announcement
------------

Due to the introduction of several powerful new APIs and performance
improvements, Synapse will be updating to *only* support Python >=3.11.
Our current plan is to drop support for Python <=3.10 in ~4 weeks on
2023-06-19. The next release after 2023-06-19 will include changes that
are not backward compatible to earlier versions of Python.

If you currently deploy Synapse Open-Source or Synapse Enterprise via
the standard docker containers, you will be unaffected.  If you install
Synapse via PyPI, you will need to ensure that your environment is
updated to Python 3.11+.

Model Changes
-------------
- Update ``it:sec:cpe`` normalization to extend truncated CPE2.3 strings.
  (`#3186 <https://github.com/vertexproject/synapse/pull/3186>`_)

Features and Enhancements
-------------------------
- The ``str`` type now accepts ``float`` values to normalize.
  (`#3174 <https://github.com/vertexproject/synapse/pull/3174>`_)

Bugfixes
--------
- Fix an issue where the ``file:bytes:sha256`` property set handler could fail
  during data merging.
  (`#3180 <https://github.com/vertexproject/synapse/pull/3180>`_)
- Fix an issue where iterating light edges on nodes could result in degraded
  Cortex performance.
  (`#3186 <https://github.com/vertexproject/synapse/pull/3186>`_)

Improved Documentation
----------------------
- Update the Cortex admin guide to include additional examples for setting up
  user and role permissions.
  (`#3187 <https://github.com/vertexproject/synapse/pull/3187>`_)

v2.138.0 - 2023-06-13
=====================

Features and Enhancements
-------------------------
- Add ``it:sec:cwe`` to the list of types identified with scrape APIs.
  (`#3182 <https://github.com/vertexproject/synapse/pull/3182>`_)
- Update the calculations done by ``$lib.infosec.cvss.vectToScore()`` to more
  closely emulate the NVD CVSS calculator.
  (`#3181 <https://github.com/vertexproject/synapse/pull/3181>`_)

Bugfixes
--------
- Fix an issue with ``synapse.tools.storm`` where the ``!export`` command did
  not use the view specified when starting the tool.
  (`#3184 <https://github.com/vertexproject/synapse/pull/3184>`_)
- The ``synapse.common.getSslCtx()`` API now only attempts to load files in
  the target directory. This avoids confusing errors that may be logged when
  the target directory contains sub directories.
  (`#3179 <https://github.com/vertexproject/synapse/pull/3179>`_)
- Fix an edge case in ``$lib.infosec.cvss.vectToScore()``  when calculating
  CVSS v2 scores.
  (`#3181 <https://github.com/vertexproject/synapse/pull/3181>`_)

Deprecations
------------
- Mark the Python function ``synapse.common.lockfile()`` as deprecated. It
  will be removed in ``v2.140.0``.
  (`#3183 <https://github.com/vertexproject/synapse/issue/3183>`_)

v2.137.0 - 2023-06-09
=====================

Automatic Migrations
--------------------
- Migrate any ``inet:url`` nodes with ``:user`` and ``:passwd`` properties
  which may have been URL encoded. These values are now decoded.
  (`#3169 <https://github.com/vertexproject/synapse/pull/3169>`_)
- Migrate the storage type for the ``file:bytes:mime:pe:imphash`` property.
  (`#3173 <https://github.com/vertexproject/synapse/pull/3173>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Updates to the ``geospace``, ``inet``, ``infotech``, ``ou``, ``risk``,
  and ``transport`` models.
  (`#3169 <https://github.com/vertexproject/synapse/pull/3169>`_)
- See :ref:`userguide_model_v2_137_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add a modulo arithmetic operator ( ``%`` ) to Storm expression parsing.
  (`#3168 <https://github.com/vertexproject/synapse/pull/3168>`_)
- Add ``$lib.auth.easyperm`` Storm library for interacting with objects that
  use a simplified permissions model.
  (`#3167 <https://github.com/vertexproject/synapse/pull/3167>`_)
- Add  ``.vars`` attribute to the Storm ``auth:user`` object. This can
  be used to access user variables.
  (`#3167 <https://github.com/vertexproject/synapse/pull/3167>`_)
- Add ``$lib.infosec.cvss.vectToScore()`` to calculate CVSS scores.
  (`#3171 <https://github.com/vertexproject/synapse/pull/3171>`_)
- The Storm ``delnode`` command node now requires the use of ``--force`` to
  delete a node which has lightweight edges pointing to it.
  (`#3176 <https://github.com/vertexproject/synapse/pull/3176>`_)
- The STIX export configuration may now include a ``synapse_extension`` value
  set to ``$lib.false`` to disable the Synapse STIX extension data from being
  added to objects in the bundle.
  (`#3177 <https://github.com/vertexproject/synapse/pull/3177>`_)
- Remove whitespace stripping from Storm queries prior to parsing them. This
  allows any error highlighting information to accurately reflect the query
  submitted to the Cortex.
  (`#3175 <https://github.com/vertexproject/synapse/pull/3175>`_)

Bugfixes
--------
- Fix an issue where raising an integer value to a fractional power
  in Storm was not handled correctly.
  (`#3170 <https://github.com/vertexproject/synapse/pull/3170>`_)
- Handle a SyntaxError that may occur during Storm parsing due to a change
  in CPython 3.11.4.
  (`#3170 <https://github.com/vertexproject/synapse/pull/3170>`_)
- The ``inet:url`` type now URL decodes the ``user`` and ``passwd``
  properties when normalizing them. Thank you ``captainGeech42`` for the
  bug report.
  (`#2568 <https://github.com/vertexproject/synapse/issue/2568>`_)
  (`#3169 <https://github.com/vertexproject/synapse/pull/3169>`_)
- The URL parser in ``synapse.lib.urlhelp`` now URL decodes the ``user``
  and ``passwd`` values when parsing URLs.
  (`#3178 <https://github.com/vertexproject/synapse/issue/3178>`_)

Deprecations
------------
- Mark the Storm functions ``$lib.infosec.cvss.saveVectToNode()`` and
  ``$lib.infosec.cvss.vectToProps()`` as deprecated.
  (`#3178 <https://github.com/vertexproject/synapse/issue/3178>`_)

v2.136.0 - 2023-06-02
=====================

Model Changes
-------------
- Boolean values in the Synapse model now have lowercase ``true`` and
  ``false`` repr values.
  (`#3159 <https://github.com/vertexproject/synapse/pull/3159>`_)
- The trailing ``.`` on the taxonomy repr has been removed.
  (`#3159 <https://github.com/vertexproject/synapse/pull/3159>`_)

Features and Enhancements
-------------------------
- Normalize tag names when performing lift and filter operations.
  (`#3094 <https://github.com/vertexproject/synapse/pull/3094>`_)
- Add ``$lib.compression.bzip2``, ``$lib.compression.gzip``, and
  ``$lib.compression.zlib`` Storm libraries to assist with compressing
  and decompressing bytes.
  (`#3155 <https://github.com/vertexproject/synapse/pull/3155>`_)
  (`#3162 <https://github.com/vertexproject/synapse/pull/3162>`_)
- Add a new Cell configuration option, ``https:parse:proxy:remoteip``. When
  this is set to ``true``, the Cell HTTPS server will parse
  ``X-Forwarded-For`` and ``X-Real-IP`` headers to determine the remote IP
  of an request.
  (`#3160 <https://github.com/vertexproject/synapse/pull/3160>`_)
- Update the allowed versions of the ``fastjsonschema`` and ``pycryptodome``
  libraries. Update the required version of the ``vcrpy`` library to account
  for changes in ``urllib3``. Remove the pinned requirement for the
  ``requests`` library.
  (`#3164 <https://github.com/vertexproject/synapse/pull/3164>`_)

Bugfixes
--------
- Prevent zero length tag lift operations.
  (`#3094 <https://github.com/vertexproject/synapse/pull/3094>`_)
- Fix an issue where tag properties with the type ``ival``, or ``time``
  types with ``ismin`` or ``ismax`` options set, were not properly merged
  when being set.
  (`#3161 <https://github.com/vertexproject/synapse/pull/3161>`_)
- Fix a missing ``mesg`` value on ``NoSuchForm`` exception raised by
  the ``layer`` ``liftByTag()`` API.
  (`#3165 <https://github.com/vertexproject/synapse/pull/3165>`_)

v2.135.0 - 2023-05-24
=====================

Features and Enhancements
-------------------------
- Add a ``--index`` option to the Storm ``auth.user.grant`` command.
  (`#3150 <https://github.com/vertexproject/synapse/pull/3150>`_)
- Add additional type handling in the Storm view and layer ``set()`` APIs.
  (`#3147 <https://github.com/vertexproject/synapse/pull/3147>`_)
- Add a new Storm command, ``auth.perms.list``, to list all of the permissions
  registered with the Cortex.
  (`#3135 <https://github.com/vertexproject/synapse/pull/3135>`_)
  (`#3154 <https://github.com/vertexproject/synapse/pull/3154>`_)

Bugfixes
--------
- Fix an issue where attempting a tag lift with a variable containing
  a zero-length string would raise an MDB error.
  (`#3094 <https://github.com/vertexproject/synapse/pull/3094>`_)
- Fix an issue in the Axon ``csvrows()`` and ``readlines()`` APIs
  where certain exceptions would not be raised.
  (`#3141 <https://github.com/vertexproject/synapse/pull/3141>`_)
- Fix an issue with the Storm ``runas`` command which prevented it being used
  with a privileged Storm runtime.
  (`#3147 <https://github.com/vertexproject/synapse/pull/3147>`_)
- Fix support for Storm list objects in ``$lib.max()`` and ``$lib.min()``.
  (`#3153 <https://github.com/vertexproject/synapse/pull/3153>`_)

Improved Documentation
----------------------
- Update the Cortex admin guide to include the output of the
  ``auth.perms.list`` command.
  (`#3135 <https://github.com/vertexproject/synapse/pull/3135>`_)

v2.134.0 - 2023-05-17
=====================

Model Changes
-------------
- Updates to the ``risk`` model.
  (`#3137 <https://github.com/vertexproject/synapse/pull/3137>`_)
- See :ref:`userguide_model_v2_134_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Add a ``--forms`` option to the Storm ``scrape`` command. This can be used
  to limit the forms that are made from scraping the input text. The
  ``scrape`` command now uses the View scrape interface to generate its
  matches, which may include scrape functionality added via power-ups.
  The ``scrape`` command no longer produces warning messages when matched
  text is not valid for making nodes.
  (`#3127 <https://github.com/vertexproject/synapse/pull/3127>`_)
- Add a ``revs`` definition to the STIX export configuration, to allow for
  adding in reverse relationships.
  (`#3137 <https://github.com/vertexproject/synapse/pull/3137>`_)
- Add a ``--delbytes`` option to the Storm ``delnode`` command. This can be
  used to delete the bytes from an Axon when deleting a ``file:bytes`` node.
  (`#3140 <https://github.com/vertexproject/synapse/pull/3140>`_)
- Add support for printing nice versions of the Storm ``model:form``,
  ``model:property``, ``model:tagprop``, and ``model:type``
  objects.
  (`#3134 <https://github.com/vertexproject/synapse/pull/3134>`_)
  (`#3139 <https://github.com/vertexproject/synapse/pull/3139>`_)

Bugfixes
--------
- Fix an exception that was raised when setting the parent of a View.
  (`#3131 <https://github.com/vertexproject/synapse/pull/3131>`_)
  (`#3132 <https://github.com/vertexproject/synapse/pull/3132>`_)
- Fix an issue with the text scrape regular expressions misidentifying the
  ``ftp://`` scheme.
  (`#3127 <https://github.com/vertexproject/synapse/pull/3127>`_)
- Correctly handle ``readonly`` properties in the Storm ``copyto`` command.
  (`#3142 <https://github.com/vertexproject/synapse/pull/3142>`_)
- Fix an issue were partial service backups were not able to be removed.
  (`#3143 <https://github.com/vertexproject/synapse/pull/3143>`_)
  (`#3145 <https://github.com/vertexproject/synapse/pull/3145>`_)

v2.133.1 - 2023-05-09
=====================

Bugfixes
--------
- Fix an issue where the Storm query hashing added in ``v2.133.0`` did not
  account for handling erroneous surrogate pairs in query text.
  (`#3130 <https://github.com/vertexproject/synapse/pull/3130>`_)

Improved Documentation
----------------------
- Update the Storm API Guide to include the ``hash`` key in the ``init``
  message.
  (`#3130 <https://github.com/vertexproject/synapse/pull/3130>`_)

v2.133.0 - 2023-05-08
=====================

Model Changes
-------------
- Updates to the ``risk`` model.
  (`#3123 <https://github.com/vertexproject/synapse/pull/3123>`_)
- See :ref:`userguide_model_v2_133_0` for more detailed model changes.

Features and Enhancements
-------------------------
- Update the base Synapse images to use Debian bookworm and use Python 3.11
  as the Python runtime. For users which build custom images from our
  published images, see additional information at
  :ref:`dev_docker_working_with_images` for changes which may affect you.
  (`#3025 <https://github.com/vertexproject/synapse/pull/3025>`_)
- Add a ``highlight`` parameter to BadSyntaxError and some exceptions raised
  during the execution of a Storm block. This contains detailed information
  about where an error occurred in the Storm code.
  (`#3063 <https://github.com/vertexproject/synapse/pull/3063>`_)
- Allow callers to specify an ``iden`` value when creating a Storm Dmon or a
  trigger.
  (`#3121 <https://github.com/vertexproject/synapse/pull/3121>`_)
- Add support for STIX export configs to specify pivots to include additional
  nodes.
  (`#3122 <https://github.com/vertexproject/synapse/pull/3122>`_)
- The Storm ``auth.user.addrule`` and ``auth.role.addrule`` now have an
  optional ``--index`` argument that allows specifying the rule location
  as a 0-based index value.
  (`#3124 <https://github.com/vertexproject/synapse/pull/3124>`_)
- The Storm ``auth.user.show`` command now shows the user's ``admin`` status
  on authgates.
  (`#3124 <https://github.com/vertexproject/synapse/pull/3124>`_)
- Add a ``--only-url`` flag to the ``synapse.tools.aha.provision.service`` and
  ``synapse.tools.aha.provision.user`` CLI tools. When set, the tool only
  prints the URL to stdout.
  (`#3125 <https://github.com/vertexproject/synapse/pull/3125>`_)
- Add additional layer validation in the View schema.
  (`#3128 <https://github.com/vertexproject/synapse/pull/3128>`_)
- Update the allowed version of the ``cryptography``, ``coverage``,
  ``idna``,  ``pycryptodome``, ``python-bitcoin``, and ``vcrpy`` libraries.
  (`#3025 <https://github.com/vertexproject/synapse/pull/3025>`_)

Bugfixes
--------
- Ensure the CLI tools ``synapse.tools.cellauth``, ``synapse.tools.csvtool``,
  and ``synapse.tools.easycert`` now return ``1`` on an execution failure. In
  some cases they previously returned ``-1``.
  (`#3118 <https://github.com/vertexproject/synapse/pull/3118>`_)

v2.132.0 - 2023-05-02
=====================

Features and Enhancements
-------------------------
- Update the minimum required version of the ``fastjsonschema``, ``lark``,
  and ``pytz`` libraries. Update the allowed version of the ``packaging`` and
  ``scalecodec`` libraries.
  (`#3118 <https://github.com/vertexproject/synapse/pull/3118>`_)

Bugfixes
--------
- Cap the maximum version of the ``requests`` library until downstream use of
  that library has been updated to account for changes in ``urllib3``.
  (`#3119 <https://github.com/vertexproject/synapse/pull/3119>`_)

- Properly add parent scope vars to ``background`` command context.
  (`#3120 <https://github.com/vertexproject/synapse/pull/3120>`_)

v2.131.0 - 2023-05-02
=====================

Automatic Migrations
--------------------
- Migrate the ``ou:campaign:name`` property from a ``str`` to an
  ``ou:campname`` type and create the ``ou:campname`` nodes as needed.
  (`#3082 <https://github.com/vertexproject/synapse/pull/3082>`_)
- Migrate the ``risk:vuln:type`` property from a ``str`` to a
  ``risk:vuln:type:taxonomy`` type and create the ``risk:vuln:type:taxonomy``
  nodes as needed.
  (`#3082 <https://github.com/vertexproject/synapse/pull/3082>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the ``dns``, ``inet``, ``it``, ``ou``, ``ps``, and ``risk``
  models.
  (`#3082 <https://github.com/vertexproject/synapse/pull/3082>`_)
  (`#3108 <https://github.com/vertexproject/synapse/pull/3108>`_)
  (`#3113 <https://github.com/vertexproject/synapse/pull/3113>`_)

  ``inet:dns:answer``
    Add a ``mx:priority`` property to record the priority of the MX response.

  ``inet:dns:dynreg``
    Add a form to record the registration of a domain with a dynamic DNS
    provider.

  ``inet:proto``
    Add a form to record a network protocol name.

  ``inet:web:attachment``
    Add a form to record the instance of a file being sent to a web service
    by an account.

  ``inet:web:file``
    Deprecate the ``client``, ``client:ipv4``, and ``client:ipv6`` properties
    in favor of using ``inet:web:attachment``.

  ``inet:web:logon``
    Remove incorrect ``readonly`` markings for properties.

  ``it:app:snort:rule``
    Add an ``id`` property to record the snort rule id.
    Add an ``author`` property to record contact information for the rule
    author.
    Add ``created`` and ``updated`` properties to track when the rule was
    created and last updated.
    Add an ``enabled`` property to record if the rule should be used for
    snort evaluation engines.
    Add a ``family`` property to record the software family the rule is
    designed to detect.

  ``it:prod:softid``
    Add a form to record an identifier issued to a given host by a specific
    software application.

  ``ou:campname``
    Add a form to record the name of campaigns.

  ``ou:campaign``
    Change the ``name`` and ``names`` secondary properties from ``str`` to
    ``ou:campname`` types.

  ``ps:contact``
    Add a ``place:name`` to record the name of the place associated with the
    contact.

  ``risk:threat``
    Add an ``active`` property to record the interval of time when the threat
    cluster is assessed to have been active.
    Add a ``reporter:published`` property to record the time that a reporting
    organization first publicly disclosed the threat cluster.

  ``risk:tool:software``
    Add a ``used`` property to record the interval when the tool is assessed
    to have been deployed.
    Add a ``reporter:discovered`` property to record the time that a reporting
    organization first discovered the tool.
    Add a ``reporter:published`` property to record the time that a reporting
    organization first publicly disclosed the tool.

  ``risk:vuln:soft:range``
    Add a form to record a contiguous range of software versions which
    contain a vulnerability.

  ``risk:vuln``
    Change the ``type`` property from a ``str`` to a
    ``risk:vuln:type:taxonomy``.

  ``risk:vuln:type:taxonomy``
    Add a form to record a taxonomy of vulnerability types.

- Add a new Storm command, ``auth.user.allowed`` that can be used to check
  if a user is allowed to use a given permission and why.
  (`#3114 <https://github.com/vertexproject/synapse/pull/3114>`_)
- Add a new Storm command, ``gen.ou.campaign``, to assist with generating or
  creating ``ou:campaign`` nodes.
  (`#3082 <https://github.com/vertexproject/synapse/pull/3082>`_)
- Add a boolean ``default`` key to the permissions schema definition. This
  allows a Storm package permission to note what its default value is.
  (`#3099 <https://github.com/vertexproject/synapse/pull/3099>`_)
- Data model migrations which fail to normalize existing secondary values into
  their new types now store those values in Node data on the affected nodes
  and remove those bad properties from the affected nodes.
  (`#3117 <https://github.com/vertexproject/synapse/pull/3117>`_)

Bugfixes
--------
- Fix an issue with the search functionality in our documentation missing
  the required jQuery library.
  (`#3111 <https://github.com/vertexproject/synapse/pull/3111>`_)
- Unique nodes when performing multi-layer lifts on secondary properties
  without a value.
  (`#3110 <https://github.com/vertexproject/synapse/pull/3110>`_)

Improved Documentation
----------------------
- Add a section about managing data model deprecations to the Synapse
  Admin guide.
  (`#3102 <https://github.com/vertexproject/synapse/pull/3102>`_)

Deprecations
------------
- Remove the deprecated ``synapse.lib.httpapi.HandlerBase.user()`` and
  ``synapse.lib.httpapi.HandlerBase.getUserBody()`` functions. Remove the
  deprecated ``synapse.axon.AxonFileHandler.axon()`` function.
  (`#3115 <https://github.com/vertexproject/synapse/pull/3115>`_)

v2.130.2 - 2023-04-26
=====================

Bugfixes
--------
- Fix an issue where the ``proxy`` argument was not being passed to the Axon
  when attempting to post a file via Storm with the ``$lib.inet.http.post()``
  API.
  (`#3109 <https://github.com/vertexproject/synapse/pull/3109>`_)
- Fix an issue where adding a readonly layer that does not already exist
  would raise an error.
  (`#3106 <https://github.com/vertexproject/synapse/pull/3106>`_)

v2.130.1 - 2023-04-25
=====================

Bugfixes
--------
- Fix a race condition in a Telepath unit test which was happening
  during CI testing.
  (`#3104 <https://github.com/vertexproject/synapse/pull/3104>`_)

v2.130.0 - 2023-04-25
=====================

Features and Enhancements
-------------------------
- Updates to the ``infotech`` model.
  (`#3095 <https://github.com/vertexproject/synapse/pull/3095>`_)

  ``it:host``
    Add an ``ext:id`` property for recording an external identifier for
    a host.

- Add support for deleting node properties by assigning ``$lib.undef`` to
  the property to be removed through ``$node.props``.
  (`#3098 <https://github.com/vertexproject/synapse/pull/3098>`_)
- The ``Cell.ahaclient`` is longer cached in the
  ``synapse.telepath.aha_clients`` dictionary. This isolates the Cell
  connection to Aha from other clients.
  (`#3008 <https://github.com/vertexproject/synapse/pull/3008>`_)
- When the Cell mirror loop exits, it now reports the current ``ready`` status
  to the Aha service. This allows a service to mark itself as "not ready" when
  the loop restarts and it is a follower, since it may no longer be in the
  realtime change window.
  (`#3008 <https://github.com/vertexproject/synapse/pull/3008>`_)
- Update the required versions of the ``nbconvert``, ``sphinx`` and
  ``hide-code`` libraries used for building documentation. Increased the
  allowed ranges for the ``pygments`` and ``jupyter-client`` libraries.
  (`#3103 <https://github.com/vertexproject/synapse/pull/3103>`_)

Bugfixes
--------
- Fix an issue in backtick format strings where single quotes in
  certain positions would raise a syntax error.
  (`#3096 <https://github.com/vertexproject/synapse/pull/3096>`_)
- Fix an issue where permissions were not correctly checked when
  assigning a property value through ``$node.props``. 
  (`#3098 <https://github.com/vertexproject/synapse/pull/3098>`_)
- Fix an issue where the Cell would report a static ``ready`` value to the Aha
  service upon reconnecting, instead of the current ``ready`` status. The
  ``Cell.ahainfo`` value was replaced with a ``Cell.getAhaInfo()`` API which
  returns the current information to report to the Aha service.
  (`#3008 <https://github.com/vertexproject/synapse/pull/3008>`_)

v2.129.0 - 2023-04-17
=====================

Features and Enhancements
-------------------------
- Updates to the ``ou`` and ``risk`` models.
  (`#3080 <https://github.com/vertexproject/synapse/pull/3080>`_)

  ``ou:campaign``
    Add a ``names`` property to record alternative names for the campaign.
    Add ``reporter`` and ``reporter:name`` properties to record information
    about a reporter of the campaign.

  ``risk:attack``
    Add ``reporter`` and ``reporter:name`` properties to record information
    about a reporter of the attack.

  ``risk:compromise``
    Add ``reporter`` and ``reporter:name`` properties to record information
    about a reporter of the compromise.

  ``risk:vuln``
    Add ``reporter`` and ``reporter:name`` properties to record information
    about a reporter of the vulnerability.

- Add leader status to the ``synapse.tools.aha.list`` tool output.
  This will only be available if a leader has been registered for
  the service.
  (`#3078 <https://github.com/vertexproject/synapse/pull/3078>`_)
- Add support for private values in Storm modules, which are specified
  by beginning the name with a double underscore (``__``). These values
  cannot be dereferenced outside of the module they are declared in.
  (`#3079 <https://github.com/vertexproject/synapse/pull/3079>`_)
- Update error messages for Axon.wget, Axon.wput, and Axon.postfiles
  to include more helpful information.
  (`#3077 <https://github.com/vertexproject/synapse/pull/3077>`_)
- Update ``it:semver`` string normalization to attempt parsing
  improperly formatted semver values.
  (`#3080 <https://github.com/vertexproject/synapse/pull/3080>`_)
- Update Axon to always pass size value when saving bytes.
  (`#3084 <https://github.com/vertexproject/synapse/pull/3084>`_)

Bugfixes
--------
- Add missing ``toprim()`` calls on arguments to some ``auth:user``
  and ``auth:role`` APIs.
  (`#3086 <https://github.com/vertexproject/synapse/pull/3086>`_)
- Fix the regular expression used to validate custom STIX types.
  (`#3093 <https://github.com/vertexproject/synapse/pull/3093>`_)

Improved Documentation
----------------------
- Add sections on user and role permissions to the Synapse Admin guide.
  (`#3073 <https://github.com/vertexproject/synapse/pull/3073>`_)

v2.128.0 - 2023-04-11
=====================

Automatic Migrations
--------------------
- Migrate the ``file:bytes:mime:pe:imphash`` property from a ``guid`` to a
  ``hash:md5`` type and create the ``hash:md5`` nodes as needed.
  (`#3056 <https://github.com/vertexproject/synapse/pull/3056>`_)
- Migrate the ``ou:goal:name`` property from a ``str`` to a ``ou:goalname``
  type and create the ``ou:goalname`` nodes as needed.
  (`#3056 <https://github.com/vertexproject/synapse/pull/3056>`_)
- Migrate the ``ou:goal:type`` property from a ``str`` to a
  ``ou:goal:type:taxonomy`` type and create the ``ou:goal:type:taxonomy``
  nodes as needed.
  (`#3056 <https://github.com/vertexproject/synapse/pull/3056>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the ``belief``, ``file``, ``lang``, ``it``, ``meta``, ``ou``,
  ``pol``, and ``risk`` models.
  (`#3056 <https://github.com/vertexproject/synapse/pull/3056>`_)

  ``belief:tenet``
    Add a ``desc`` property to record the description of the tenet.

  ``file:bytes``
    Change the type of the ``mime:pe:imphash`` from ``guid`` to ``hash:md5``.

  ``inet:flow``
    Add a ``raw`` property which may be used to store additional protocol
    data about the flow.

  ``it:app:snort:rule``
    Add a ``desc`` property to record a brief description of the snort rule.

  ``ou:goal``
    Change the type of ``name`` from ``str`` to ``ou:goalname``.
    Change the type of ``type`` from ``str`` to ``ou:goal:type:taxonomy``.
    Add a ``names`` array to record alternative names for the goal.
    Deprecate the ``prev`` property in favor of types.

  ``ou:goalname``
    Add a form to record the name of a goal.

  ``ou:goalname:type:taxonomy``
    Add a taxonomy of goal types.

  ``ou:industry``
    Add a ``type`` property to record the industry taxonomy.

  ``ou:industry:type:taxonomy``
    Add a taxonomy to record industry types.

  ``pol:immigration:status``
    Add a form to track the immigration status of a contact.

  ``pol:immigration:status:type:taxonomy``
    Add a taxonomy of immigration types.

  ``risk:attack``
    Add a ``detected`` property to record the first confirmed detection time
    of the attack.
    Add a ``url`` property to record a URL that documents the attack.
    Add a ``ext:id`` property to record an external identifier for the attack.

  ``risk:compromise``
    Add a ``detected`` property to record the first confirmed detection time
    of the compromise.

- Add a Storm command ``copyto`` that can be used to create a copy of a node
  from the current view to a different view.
  (`#3061 <https://github.com/vertexproject/synapse/pull/3061>`_)
- Add the current View iden to the structured log output of a Cortex executing
  a Storm query.
  (`#3068 <https://github.com/vertexproject/synapse/pull/3068>`_)
- Update the allowed versions of the ``lmdb``, ``msgpack``, ``tornado`` and
  ``xxhash`` libraries.
  (`#3070 <https://github.com/vertexproject/synapse/pull/3070>`_)
- Add Python 3.11 tests to the CircleCI configuration. Update some unit tests
  to account for Python 3.11 related changes.
  (`#3070 <https://github.com/vertexproject/synapse/pull/3070>`_)
- Allow dereferencing from Storm expressions.
  (`#3071 <https://github.com/vertexproject/synapse/pull/3071>`_)
- Add an ``ispart`` parameter to ``$lib.tags.prefix`` to skip ``syn:tag:part``
  normalization of tag names.
  (`#3074 <https://github.com/vertexproject/synapse/pull/3074>`_)
- Add ``getEdges()``, ``getEdgesByN1()``, and ``getEdgesByN2()`` APIs to the
  ``layer`` object.
  (`#3076 <https://github.com/vertexproject/synapse/pull/3076>`_)

Bugfixes
--------
- Fix an issue which prevented the ``auth.user.revoke`` Storm command from
  executing.
  (`#3069 <https://github.com/vertexproject/synapse/pull/3069>`_)
- Fix an issue where ``$node.data.list()`` only returned the node data from
  the topmost layer containing node data. It now returns all the node data
  accessible for the node from the current view.
  (`#3061 <https://github.com/vertexproject/synapse/pull/3061>`_)

Improved Documentation
----------------------
- Update the Developer guide to note that the underlying Python runtime in
  Synapse images may change between releases.
  (`#3070 <https://github.com/vertexproject/synapse/pull/3070>`_)

v2.127.0 - 2023-04-05
=====================

Features and Enhancements
-------------------------
- Set ``Link`` high water mark to one byte in preparation for Python 3.11
  support.
  (`#3064 <https://github.com/vertexproject/synapse/pull/3064>`_)
- Allow specifying dictionary keys in Storm with expressions and backtick
  format strings.
  (`#3065 <https://github.com/vertexproject/synapse/pull/3065>`_)
- Allow using deref syntax (``*$form``) when lifting by form with tag
  (``*$form#tag``) and form with tagprop (``*$form#tag:tagprop``).
  (`#3065 <https://github.com/vertexproject/synapse/pull/3065>`_)
- Add ``cron:start`` and ``cron:stop`` messages to the events emitted by the
  ``behold()`` API on the Cortex. These events are only emitted by the leader.
  (`#3062 <https://github.com/vertexproject/synapse/pull/3062>`_)

Bugfixes
--------
- Fix an issue where an Aha service running on a non-default port would
  not have that port included in the default Aha URLs.
  (`#3049 <https://github.com/vertexproject/synapse/pull/3049>`_)
- Restore the ``view.addNode()`` Storm API behavior where making a node on
  a View object that corresponds to the currently executing view re-used the
  current Snap object. This allows nodeedits to be emitted from the Storm
  message stream.
  (`#3066 <https://github.com/vertexproject/synapse/pull/3066>`_)

v2.126.0 - 2023-03-30
=====================

Features and Enhancements
-------------------------
- Add additional Storm commands to assist with managing Users and Roles in
  the Cortex.
  (`#2923 <https://github.com/vertexproject/synapse/pull/2923>`_)
  (`#3054 <https://github.com/vertexproject/synapse/pull/3054>`_)

  ``auth.gate.show``
    Shows the definition for an AuthGate.

  ``auth.role.delrule``
    Used to delete a rule from a Role.

  ``auth.role.mod``
    Used to modify properties of a Role.

  ``auth.role.del``
    Used to delete a Role.

  ``auth.role.show``
    Shows the definition for a Role.

  ``auth.role.list``
    List all Roles.

  ``auth.user.delrule``
    Used to delete a rule from a User.

  ``auth.user.grant``
    Used to grant a Role to a User.

  ``auth.user.revoke``
    Used to revoke a Role from a User.

  ``auth.role.mod``
    Used to modify properties of a User.

  ``auth.user.show``
    Shows the definition of a User.

  ``auth.user.list``
    List all Users.

- Update some of the auth related objects in Storm:
  (`#2923 <https://github.com/vertexproject/synapse/pull/2923>`_)

  ``auth:role``
    Add ``popRule()`` and ``getRules()`` functions. Add a ``.gates``
    accessor to get all of the AuthGates associated with a role.

  ``auth:user``
    Add ``popRule()`` and ``getRules()`` functions. Add a ``.gates``
    accessor to get all of the AuthGates associated with a user.

- Add ``$lib.auth.textFromRule()``, ``$lib.auth.getPermDefs()`` and
  ``$lib.auth.getPermDef()`` Storm library APIs to assist with working
  with permissions.
  (`#2923 <https://github.com/vertexproject/synapse/pull/2923>`_)
- Add a new Storm library function, ``$lib.iters.enum()``, to assist with
  enumerating an iterable object in Storm.
  (`#2923 <https://github.com/vertexproject/synapse/pull/2923>`_)
- Update the ``NoSuchName`` exceptions which can be raised by Aha during
  service provisioning to clarify they are likely caused by re-using the
  one-time use URL.
  (`#3047 <https://github.com/vertexproject/synapse/pull/3047>`_)
- Update ``gen.ou.org.hq`` command to set ``ps:contact:org`` if unset.
  (`#3052 <https://github.com/vertexproject/synapse/pull/3052>`_)
- Add an ``optional`` flag for Storm package dependencies.
  (`#3058 <https://github.com/vertexproject/synapse/pull/3058>`_)
- Add ``.]``, ``[.``, ``http[:``, ``https[:``, ``hxxp[:`` and ``hxxps[:``
  to the list of known defanging strategies which are identified and
  replaced during text scraping.
  (`#3057 <https://github.com/vertexproject/synapse/pull/3057>`_)

Bugfixes
--------
- Fix an issue where passing a non-string value to ``$lib.time.parse``
  with ``errok=$lib.true`` would still raise an exception.
  (`#3046 <https://github.com/vertexproject/synapse/pull/3046>`_)
- Fix an issue where context managers could potentially not release
  resources after exiting.
  (`#3055 <https://github.com/vertexproject/synapse/pull/3055>`_)
- Fix an issue where variables with non-string names could be passed
  into Storm runtimes.
  (`#3059 <https://github.com/vertexproject/synapse/pull/3059>`_)
- Fix an issue with the Cardano regex used for scraping addresses.
  (`#3057 <https://github.com/vertexproject/synapse/pull/3057>`_)
- Fix an issue where scraping a partial Cardano address could raise
  an error.
  (`#3057 <https://github.com/vertexproject/synapse/pull/3057>`_)
- Fix an issue where the Storm API ``view.addNode()`` checked permissions
  against the incorrect authgate. This API now only returns a node if the
  View object is the same as the View the Storm query is executing in.
  (`#3060 <https://github.com/vertexproject/synapse/pull/3060>`_)

Improved Documentation
----------------------
- Fix link to Storm tool in Synapse Power-Ups section.
  (`#3053 <https://github.com/vertexproject/synapse/pull/3053>`_)
- Add Kubernetes deployment examples, which show deploying Synapse services
  with Aha based provisioning. Add an example showing one mechanism to set
  ``sysctl``'s in a managed Kubernetes deployment.
  (`#3047 <https://github.com/vertexproject/synapse/pull/3047>`_)

v2.125.0 - 2023-03-14
=====================

Features and Enhancements
-------------------------
- Add a ``size()`` method on the STIX bundle object.
  (`#3043 <https://github.com/vertexproject/synapse/pull/3043>`_)
- Update the minimum version of the ``aio-socks`` library to ``0.8.0``.
  Update some unittests related to SOCKS proxy support to account for
  multiple versions of the ``python-socks`` library.
  (`#3044 <https://github.com/vertexproject/synapse/pull/3044>`_)

Improved Documentation
----------------------
- Update the Synapse documentation to add PDF and HTMLZip formats.

v2.124.0 - 2023-03-09
=====================

Features and Enhancements
-------------------------
- Added ``--try`` option to ``gen.risk.vuln``, ``gen.pol.country``,
  ``gen.pol.country.government``, and ``gen.ps.contact.email`` commands
  and their associated Storm functions.
  (`#3030 <https://github.com/vertexproject/synapse/pull/3030>`_)
- Added ``$lib.gen.orgHqByName`` and ``$lib.gen.langByName``.
  (`#3030 <https://github.com/vertexproject/synapse/pull/3030>`_)
- Added the configuration option ``onboot:optimize`` to all services
  to allow devops to delay service startup and allow LMDB to optimize
  storage for both size and performance. May also be set by environment
  variable ``SYN_<SERVICE>_ONBOOT_OPTIMIZE=1``
  (`#3001 <https://github.com/vertexproject/synapse/pull/3001>`_)
- Ensure that ``AuthDeny`` exceptions include the user iden in the ``user``
  key, and the name in the ``username`` field. Previously the ``AuthDeny``
  exceptions had multiple identifiers for these fields.
  (`#3035 <https://github.com/vertexproject/synapse/pull/3035>`_)
- Add an optional ``--view`` argument to the ``synapse.tools.storm`` CLI
  tool. This allows a user to specify their working View for the Storm CLI.
  This was contributed by captainGeech42.
  (`#2937 <https://github.com/vertexproject/synapse/pull/2937>`_)
- Updates to ``synapse.lib.scope`` and the ``Scope`` class. A ``Scope.copy()``
  method has been added to create a shallow copy of a ``Scope``. A module
  level ``clone(task)`` function has been added which clones the current task
  scope to the target ``task``.  Async Tasks created with ``Base.schedCoro()``
  calls now get a shallow copy of the parent task scope.
  (`#3021 <https://github.com/vertexproject/synapse/pull/3021>`_)
- Add a new Storm command, ``batch``, to assist in processing nodes in batched
  sets.
  (`#3034 <https://github.com/vertexproject/synapse/pull/3034>`_)
- Add global permissions, ```storm.macro.admin`` and ``storm.macro.edit``, to
  allow users to administer or edit macros.
  (`#3037 <https://github.com/vertexproject/synapse/pull/3037>`_)
- Mark the following Storm APIs as safe to execute in read-only queries:
  ``$lib.auth.users.get()``, ``$lib.auth.users.list()``,
  ``$lib.auth.users.byname()``, ``$lib.auth.roles.get()``,
  ``$lib.auth.roles.list()``, ``$lib.auth.roles.byname()``,
  ``$lib.auth.gates.get()`` and ``$lib.auth.gates.list()``.
  (`#3038 <https://github.com/vertexproject/synapse/pull/3038>`_)
- Added ``uplink`` key to ``getCellInfo()``, which indicates whether
  the Cell is currently connected to an upstream mirror.
  (`#3041 <https://github.com/vertexproject/synapse/pull/3041>`_)

Bugfixes
--------
- Fix an issue in the Storm grammar where part of a query could potentially
  be incorrectly parsed as an unquoted case statement.
  (`#3032 <https://github.com/vertexproject/synapse/pull/3032>`_)
- Fix an issue where exceptions could be raised which contained data that was
  not JSON serializable. ``$lib.raise`` arguments must now also be JSON safe.
  (`#3029 <https://github.com/vertexproject/synapse/pull/3029>`_)
- Fix an issue where a spawned process returning a non-pickleable exception
  would not be handled properly.
  (`#3036 <https://github.com/vertexproject/synapse/pull/3036>`_)
- Fix an issue where a locked user could login to a Synapse service on a TLS
  Telepath connection if the connection presented a trusted client certificate
  for the locked user.
  (`#3035 <https://github.com/vertexproject/synapse/pull/3035>`_)
- Fix a bug in ``Scope.enter()`` where the added scope frame was not removed
  when the context manager was exited.
  (`#3021 <https://github.com/vertexproject/synapse/pull/3021>`_)
- Restoring a service via the ``SYN_RESTORE_HTTPS_URL`` environment variable
  could timeout when downloading the file. The total timeout for this process
  has been disabled.
  (`#3042 <https://github.com/vertexproject/synapse/pull/3042>`_)

Improved Documentation
----------------------
- Update the Synapse glossary to add terms related to the permissions system.
  (`#3031 <https://github.com/vertexproject/synapse/pull/3031>`_)
- Update the model docstrings for the ``risk`` model.
  (`#3027 <https://github.com/vertexproject/synapse/pull/3027>`_)

Deprecations
------------
- The ``ctor`` support in ``Scope`` has been removed. The population of the
  global default scope with environment variables has been removed.
  (`#3021 <https://github.com/vertexproject/synapse/pull/3021>`_)

v2.123.0 - 2023-02-22
=====================

Automatic Migrations
--------------------
- If the ``risk:vuln:cvss:av`` property equals ``V`` it is migrated to ``P``.
  (`#3013 <https://github.com/vertexproject/synapse/pull/3013>`_)
- Parse ``inet:http:cookie`` nodes to populate the newly added
  ``:name`` and ``:value`` properties.
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Added the ``belief`` model which includes the following new forms:
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

  ``belief:system``
    A belief system such as an ideology, philosophy, or religion.

  ``belief:tenet``
    A concrete tenet potentially shared by multiple belief systems.

  ``belief:subscriber``
    A contact which subscribes to a belief system.

  ``belief:system:type:taxonomy``
    A hierarchical taxonomy of belief system types.

- Added declaration for ``risk:compromise -(uses)> ou:technique``
  light-weight edges.
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

- Updated ``inet:http:session`` and ``inet:http:request`` forms to
  include the following property:
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

  ``:cookies``
    An array of ``inet:http:cookie`` values associated with the node.

- Updated the ``inet:http:cookie`` form to include the following properties:
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

  ``name``
    The name of the cookie preceding the equal sign.

  ``value``
    The value of the cookie after the equal sign if present.

- Added logic to allow constructing multiple ``inet:http:cookie``
  nodes by automatically splitting on ``;`` such as ``foo=bar; baz=faz``
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

- Updated ``it:log:event`` to add the following properties:
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

  ``type``
    An ``it:log:event:type:taxonomy`` type for the log entry.

  ``ext:id``
    An external ID that uniquely identifies this log entry.

  ``product``
    An ``it:prod:softver`` of the product which produced the log entry.

- Updated the ``risk:compromise`` form to include the following properties:
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

  ``goal``
    An ``ou:goal`` node representing the assessed primary goal of the
    compromise.

  ``goals``
    An array of ``ou:goal`` nodes representing additional goals of the
    compromise.

- Updated ``risk:attack`` and ``risk:compromise`` forms to deprecate the
  ``techniques`` property in favor of using ``-(uses)> ou:technique``
  light-weight edges.
  (`#3015 <https://github.com/vertexproject/synapse/pull/3015>`_)

- Updates to the ``inet:dns``, and ``media`` models.
  (`#3005 <https://github.com/vertexproject/synapse/pull/3005>`_)
  (`#3017 <https://github.com/vertexproject/synapse/pull/3017>`_)

  ``inet:dns:answer``
    Remove all read-only flags present on the secondary properties for this
    form.

  ``media:news``
    Add an ``updated`` property to record last time the news item was updated.

- Updated ``inet:flow`` to include the following properties:
  (`#3017 <https://github.com/vertexproject/synapse/pull/3017>`_)

  ``src:ssh:key``
    The key sent by the client as part of an SSH session setup.

  ``dst:ssh:key``
    The key sent by the server as part of an SSH session setup.

  ``src:ssl:cert``
    The x509 certificate sent by the client as part of an SSL/TLS negotiation.

  ``dst:ssl:cert``
    The x509 certificate sent by the server as part of an SSL/TLS negotiation.

  ``src:rdp:hostname``
    The hostname sent by the client as part of an RDP session setup.

  ``src:rdp:keyboard:layout``
    The keyboard layout sent by the client as part of an RDP session setup.

- Add ``synapse.utils.stormcov``, a Coverage.py plugin for measuring code
  coverage of Storm files.
  (`#2961 <https://github.com/vertexproject/synapse/pull/2961>`_)
- Clean up several references to the ``cell.auth`` object in HTTP API
  handlers. Move the logic in ``/api/v1/auth/onepass/issue`` API handler to
  the base Cell.
  (`#2998 <https://github.com/vertexproject/synapse/pull/2998>`_)
  (`#3004 <https://github.com/vertexproject/synapse/pull/3004>`_)
- Clarify the error message encountered by a Synapse mirrored service if
  the mirror gets desynchronized from its upstream service.
  (`#3006 <https://github.com/vertexproject/synapse/pull/3006>`_)
- Update how read-only properties are handled during merges. The ``.created``
  property will always be set when merging a node down. If two nodes have
  other conflicting read-only property values, those will now emit a warning
  in the Storm runtime.
  (`#2989 <https://github.com/vertexproject/synapse/pull/2989>`_)
- The ``Axon.wget()`` API response now includes HTTP request history, which is
  added when the API request encounters redirects. The ``$lib.axon.wget()``
  Storm API now includes information about the original request URL. This data
  is now used to create ``inet:urlredir`` nodes, such as when the Storm
  ``wget`` command is used to retrieve a file.
  (`#3011 <https://github.com/vertexproject/synapse/pull/3011>`_)
- Ensure that ``BadTypeValu`` exceptions raised when normalizing invalid
  data with the ``time`` type includes the value in the exception message.
  (`#3009 <https://github.com/vertexproject/synapse/pull/3009>`_)
- Add a callback on Slab size expansion to trigger a free disk space check
  on the related cell.
  (`#3016 <https://github.com/vertexproject/synapse/pull/3016>`_)
- Add support for choices in Storm command arguments.
  (`#3019 <https://github.com/vertexproject/synapse/pull/3019>`_)
- Add an optional parameter to the Storm ``uniq`` command to allow specifying
  a relative property or variable to operate on rather than node iden.
  (`#3018 <https://github.com/vertexproject/synapse/pull/3018>`_)
- Synapse HTTP API logs now include the user iden and username when that
  information is available. For deployments with structured logging enabled,
  the HTTP path, HTTP status code, user iden, and username are added to
  that log message.
  (`#3007 <https://github.com/vertexproject/synapse/pull/3007>`_)
- Add ``web_useriden`` and ``web_username`` attributes to the Synapse HTTP
  Handler class. These are used for HTTP request logging to populate
  the user iden and username data. These are automatically set when a user
  authenticates using a session token or via basic authentication.
  The HTTP Session tracking now tracks the username at the time the session
  was created. The ``_web_user`` value, which previously pointed to a heavy
  HiveUser object, is no longer populated by default.
  (`#3007 <https://github.com/vertexproject/synapse/pull/3007>`_)
- Add ``$lib.inet.http.codereason`` Storm API for translating HTTP status
  codes to reason phrases. ``inet:http:resp`` objects now also have a
  ``reason`` value populated.
  (`#3023 <https://github.com/vertexproject/synapse/pull/3023>`_)
- Update the minimum version of the ``cryptography`` library to ``39.0.1`` and
  the minimum version of the ``pyopenssl`` library to ``23.0.0``.
  (`#3022 <https://github.com/vertexproject/synapse/pull/3022>`_)

Bugfixes
--------
- The Storm ``wget`` command created ``inet:urlfile`` nodes with the ``url``
  property of the resolved URL from ``aiohttp``. This made it so that a user
  could not pivot from an ``inet:url`` node which had a URL encoded parameter
  string to the resulting ``inet:urlfile`` node. The ``inet:urlfile`` nodes
  are now made with the original request URL to allow that pivoting to occur.
  (`#3011 <https://github.com/vertexproject/synapse/pull/3011>`_)
- The ``Axon.wget()`` and ``$lib.axon.wget()`` APIs returned URLs in the
  ``url`` field of their responses which did not contain fragment identifiers.
  These API responses now include the fragment identifier if it was present in
  the resolved URL.
  (`#3011 <https://github.com/vertexproject/synapse/pull/3011>`_)
- The Storm ``tree`` command did not properly handle Storm query arguments
  which were declared as ``storm:query`` types.
  (`#3012 <https://github.com/vertexproject/synapse/pull/3012>`_)
- Remove an unnecessary permission check in the Storm ``movenodes`` command
  which could cause the command to fail.
  (`#3002 <https://github.com/vertexproject/synapse/pull/3002>`_)
- When a user email address was provided to the HTTP API
  ``/api/v1/auth/adduser``, the handler did not properly set the email using
  change controlled APIs, so that information would not be sent to mirrored
  cells. The email is now being set properly.
  (`#2998 <https://github.com/vertexproject/synapse/pull/2998>`_)
- The ``risk:vuln:cvss:av`` enum incorrectly included ``V`` instead of ``P``.
  (`#3013 <https://github.com/vertexproject/synapse/pull/3013>`_)
- Fix an issue where the ``ismax`` specification on time types did not merge
  time values correctly.
  (`#3017 <https://github.com/vertexproject/synapse/pull/3017>`_)
- Fix an issue where using a function call to specify the tag in a tagprop
  operation would not be correctly parsed.
  (`#3020 <https://github.com/vertexproject/synapse/pull/3020>`_)

Improved Documentation
----------------------
- Update copyright notice to always include the current year.
  (`#3010 <https://github.com/vertexproject/synapse/pull/3010>`_)

Deprecations
------------
- The ``synapse.lib.httpapi.Handler.user()`` and
  ``synapse.lib.httpapi.Handler.getUserBody()`` methods are marked as
  deprecated. These methods will be removed in Synapse ``v2.130.0``.
  (`#3007 <https://github.com/vertexproject/synapse/pull/3007>`_)

v2.122.0 - 2023-01-27
=====================

Features and Enhancements
-------------------------

- Updates to the ``biz``, ``file``, ``lang``, ``meta``, ``pol``, and
  ``risk`` models.
  (`#2984 <https://github.com/vertexproject/synapse/pull/2984>`_)

  ``biz:service``
    Add a ``launched`` property to record when the operator first made the
    service available.

  ``file:bytes``
    Add ``exe:compiler`` and ``exe:packer`` properties to track the software
    used to compile and encode the file.

  ``lang:language``
    Add a new guid form to represent a written or spoken language.

  ``lang:name``
    Add a new form to record the name of a language.

  ``meta:node``
    Add a ``type`` property to record the note type.

  ``meta:note:type:taxonomy``
    Add a form to record an analyst defined taxonomy of note types.

  ``pol:country``
    Correct the ``vitals`` property type from ``ps:vitals`` to ``pol:vitals``.

  ``ps:contact``
    Add a ``lang`` property to record the language specified for the contact.

    Add a ``langs`` property to record the alternative languages specified for
    the contact.

  ``ps:skill``
    Add a form to record a specific skill which a person or organization may
    have.

  ``ps:skill:type:taxonomy``
    Add a form to record a taxonomy of skill types.

  ``ps:proficiency``
    Add a form to record the assessment that a given contact possesses a
    specific skill.

  ``risk:alert``
    Add a ``priority`` property that can be used to rank alerts by priority.

  ``risk:compromise``
    Add a ``severity`` property that can be used as a relative severity score
    for the compromise.

  ``risk:threat``
    Add a ``type`` property to record the type of the threat cluster.

  ``risk:threat:type:taxonomy``
    Add a form to record a taxonomy of threat types.

- Add support for Python 3.10 to Synapse.
  (`#2962 <https://github.com/vertexproject/synapse/pull/2962>`_)
- Update the Synapse docker containers to be built from a Debian based image,
  instead of an Ubuntu based image. These images now use Python 3.10 as the
  Python runtime.
  (`#2962 <https://github.com/vertexproject/synapse/pull/2962>`_)
- Add an optional ``--type`` argument to the Storm ``note.add`` command.
  (`#2984 <https://github.com/vertexproject/synapse/pull/2984>`_)
- Add a Storm command, ``gen.lang.language``, to lift or generate a
  ``lang:language`` node by name.
  (`#2984 <https://github.com/vertexproject/synapse/pull/2984>`_)
- Update the allowed versions of the ``cbor2`` library; and upgrade the
  versions of ``aiostmplib`` and ``aiohttp-socks`` to their latest versions.
  (`#2986 <https://github.com/vertexproject/synapse/pull/2986>`_)
- The ``X-XSS-Protection`` header was removed from the default HTTP API
  handlers. This header is non-standard and only supported by Safari browsers.
  Service deployments which rely on this header should use the
  ``https:headers`` configuration option to inject that header into their
  HTTP responses.
  (`#2997 <https://github.com/vertexproject/synapse/pull/2997>`_)

Bugfixes
--------
- Malformed hash values normalized as ``file:bytes`` raised exceptions which
  were not properly caught, causing Storm ``?=`` syntax to fail. Malformed
  values are now properly handled in ``file:bytes``.
  (`#3000 <https://github.com/vertexproject/synapse/pull/3000>`_)

Improved Documentation
----------------------
- Update the Storm filters user guide to include expression filters
  (`#2997 <https://github.com/vertexproject/synapse/pull/2997>`_)
- Update Storm type-specific behavior user guide to clarify ``guid``
  deconfliction use cases and some associated best practices.
  (`#2997 <https://github.com/vertexproject/synapse/pull/2997>`_)
- Update Storm command reference user guide to document ``gen.*`` commands.
  (`#2997 <https://github.com/vertexproject/synapse/pull/2997>`_)

Deprecations
------------
- The Cortex APIs ``provStacks()`` and ``getProvStack(iden)`` have been
  removed.
  (`#2995 <https://github.com/vertexproject/synapse/pull/2995>`_)

v2.121.1 - 2022-01-23
=====================

Bugfixes
--------
- When creating Storm Macros using ``v2.121.0``, the creator of the Macro was
  incorrectly set to the ``root`` user. This is now set to the user that
  created the macro using the Storm ``macro.set`` command or the
  ``$lib.macro.set()`` API.
  (`#2993 <https://github.com/vertexproject/synapse/pull/2993>`_)

v2.121.0 - 2022-01-20
=====================

Automatic Migrations
--------------------
- Storm Macros stored in the Cortex are migrated from the Hive to the Cortex
  LMDB slab.
  (`#2973 <https://github.com/vertexproject/synapse/pull/2973>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------

- Updates to the  ``inet`` and  ``ou`` models.
  (`#2982 <https://github.com/vertexproject/synapse/pull/2982>`_)
  (`#2987 <https://github.com/vertexproject/synapse/pull/2987>`_)

  ``inet:dns:soa``
    The ``fqdn``, ``ns`` and ``email`` properties had the read-only flag
    removed from them.

  ``ou:org``
    Add a ``goals`` property to record the assessed goals of the organization.

- Add extended permissions for Storm Macro functionality using a new
  simplified permissions system. This allows users to opt into assigning
  users or roles the permission to read, write, administrate, or deny access
  to their Macros. These permissions can be set by the Storm
  ``$lib.macro.grant()`` API.
  (`#2973 <https://github.com/vertexproject/synapse/pull/2973>`_)
- Add extended information about a Storm Macro, including its creation time,
  update time, and a description. The Macro name, description and Storm can
  now be set via the Storm ``$lib.macro.mod()`` API.
  (`#2973 <https://github.com/vertexproject/synapse/pull/2973>`_)
- Allow users and Power-Ups to store graph projection definitions in the
  Cortex. Graph projections have the same simplified permissions system
  applied to them as introduced for Storm Macros. Storm users can now also
  load a stored graph projection into a running Storm query. These new
  features are exposed via the Storm ``$lib.graph`` APIs.
  (`#2914 <https://github.com/vertexproject/synapse/pull/2914>`_)
- The disk space required to make the backup of a Synapse service is now
  checked prior to a live backup being made. If there is insufficient storage
  to make the backup on the volume storing the backup, a LowSpace exception
  will be raised.
  (`#2990 <https://github.com/vertexproject/synapse/pull/2990>`_)

Bugfixes
--------
- When normalizing the ``inet:email`` type, an unclear Python ``ValueError``
  could have been raised to a user. This is now caught and a specific
  ``BadTypeValu`` exception is raised.
  (`#2982 <https://github.com/vertexproject/synapse/pull/2982>`_)
- The ``synapse.exc.StormRaise`` exception caused an error when recreating
  the exception on the client side of a Telepath connection. This exception
  will now raise properly on the caller side.
  (`#2985 <https://github.com/vertexproject/synapse/pull/2985>`_)
- When using the Storm ``diff`` command to examine a forked View, if a node
  was deleted out from the base layer and edited in the fork, an exception
  would be raised. This situation is now properly handled.
  (`#2988 <https://github.com/vertexproject/synapse/pull/2988>`_)

Improved Documentation
----------------------
- Update the Storm User Guide section on variables for clarity.
  (`#2968 <https://github.com/vertexproject/synapse/pull/2968>`_)
- Correct Provenance API deprecation notice from ``v2.221.0`` to ``v2.122.0``.
  (`#2981 <https://github.com/vertexproject/synapse/pull/2981>`_)

v2.120.0 - 2023-01-11
=====================

Features and Enhancements
-------------------------

- Update to the ``risk`` models.
  (`#2978 <https://github.com/vertexproject/synapse/pull/2978>`_)

  ``risk:threat``
    Add a ``merge:time`` and ``merged:isnow`` properties to track when a
    threat cluster was merged with another threat cluster.

  ``risk:alert``
    Add an ``engine`` property to track the software engine that generated the
    alert.

- Add events for ``trigger:add``, ``trigger:del``, and ``trigger:set`` to the
  Beholder API.
  (`#2975 <https://github.com/vertexproject/synapse/pull/2975>`_)

Bugfixes
--------
- Fix an infinite loop in ``synapse.tools.storm`` when using the tool in
  an environment without write access to the history file.
  (`#2977 <https://github.com/vertexproject/synapse/pull/2977>`_)

v2.119.0 - 2023-01-09
=====================

Features and Enhancements
-------------------------

- Updates to the  ``biz``, ``econ``, ``ou``, and ``risk`` models.
  (`#2931 <https://github.com/vertexproject/synapse/pull/2931>`_)

  ``biz:listing``
    Add a form to track a specific product or service listed for sale
    at a given price by a specific seller.

  ``biz:service``
    Add a form to track a service performed by a specific organization.

  ``biz:service:type``
    Add a form to record an analyst defined taxonomy of business services.

  ``biz:bundle``
    Add a ``service`` property to record the service included in the bundle.

    Deprecate the ``deal`` and ``purchase`` secondary properties in favor of
    ``econ:receipt:item`` to represent bundles being sold.

  ``biz:product``
    Add a ``price:currency`` property to denote the currency of the prices.

    Add a ``maker`` property to represent the contact information for the
    maker of a product.

    Deprecate the ``madeby:org``, ``madeby:orgname``, ``madeby:orgfqdn``
    properties in favor of using the new ``maker`` property.

  ``econ:receipt:item``
    Add a form to represent a line item included as part of a purchase.

  ``econ:acquired``
    Deprecate the form in favor of an ``acquired`` light edge.

  ``ou:campaign``
    Add a ``budget`` property to record the budget allocated for the campaign.

    Add a ``currency`` property to record the currency of the ``econ:price``
    secondary properties.

    Add a ``result:revenue`` property to record the revenue resulting from the
    campaign.

    Add a ``result:pop`` property to record the count of people affected by
    the campaign.

  ``risk:alert:verdict:taxonomy``
    Add a form to record an analyst defined taxonomy of the origin and
    validity of an alert.

  ``risk:alert``
    Add a ``benign`` property to record if the alert has been confirmed as
    benign or malicious.

    Add a ``verdict`` property to record the analyst verdict taxonomy about
    why an alert is marked as benign or malicious.

- Annotate the following light edges.
  (`#2931 <https://github.com/vertexproject/synapse/pull/2931>`_)

  ``acquired``
    When used with an ``econ:purchase`` node, the edge indicates the purchase
    was used to acquire the target node.

  ``ipwhois``
    When used with an ``inet:whois:iprec`` node and ``inet:ipv4`` or
    ``inet:ipv6`` nodes, the edge indicates the source IP whois record
    describes the target IP address.

- Add a new Cell configuration option, ``limit:disk:free``. This represents
  the minimum percentage of free disk space on the volume hosting a Synapse
  service that is required in order to start up. This value is also
  monitored every minute and will disable the Cell Nexus if the free space
  drops below the specified value. This value defaults to five percent
  ( ``5 %`` ) free disk space.
  (`#2920 <https://github.com/vertexproject/synapse/pull/2920>`_)

Improved Documentation
----------------------
- Add a Devops task related to configuration of the free space requirement.
  (`#2920 <https://github.com/vertexproject/synapse/pull/2920>`_)

v2.118.0 - 2023-01-06
=====================

Features and Enhancements
-------------------------
- Updates to the  ``inet``, ``pol``, and ``ps`` models.
  (`#2970 <https://github.com/vertexproject/synapse/pull/2970>`_)
  (`#2971 <https://github.com/vertexproject/synapse/pull/2971>`_)

  ``inet:tunnel``
    Add a form to represent the specific sequence of hosts forwarding
    connections, such as a VPN or proxy.

  ``inet:tunnel:type:taxonomy``
    Add a form to record an analyst defined taxonomy of network tunnel types.

  ``pol:country``
    Add a ``government`` property to represent the organization for the
    government of the country.

  ``ps:contact``
    Add a ``type`` property to record the taxonomy of the node. This may be
    used for entity resolution.

  ``ps:contact:type:taxonomy``
    Add a form to record an analyst defined taxonomy of contact types.

- Add the following Storm commands to help with analyst generation of several
  guid node types:
  (`#2970 <https://github.com/vertexproject/synapse/pull/2970>`_)

  ``gen.it.prod.soft``
    Lift (or create) an ``it:prod:soft`` node based on the software name.

  ``gen.ou.industry``
    Lift (or create) an ``ou:industry`` node based on the industry name.

  ``gen.ou.org``
    Lift (or create) an ``ou:org`` node based on the organization name.

  ``gen.ou.org.hq``
    Lift (or create) the primary ``ps:contact`` node for the ou:org based on
    the organization name.

  ``gen.pol.country``
    Lift (or create) a ``pol:country`` node based on the 2 letter ISO-3166
    country code.

  ``gen.pol.country.government``
    Lift (or create) the ``ou:org`` node representing a country's government
    based on the 2 letter ISO-3166 country code.

  ``gen.ps.contact.email``
    Lift (or create) the ``ps:contact`` node by deconflicting the email and
    type.

  ``gen.risk.threat``
    Lift (or create) a ``risk:threat`` node based on the threat name and
    reporter name.

  ``gen.risk.tool.software``
    Lift (or create) a ``risk:tool:software`` node based on the tool name and
    reporter name.

  ``gen.risk.vuln``
    Lift (or create) a ``risk:vuln`` node based on the CVE.

- Add ``$lib.gen.riskThreat()``, ``$lib.gen.riskToolSoftware()``,
  ``$lib.gen.psContactByEmail()``, and ``$lib.gen.polCountryByIso2()`` Storm
  API functions to assist in generating ``risk:threat``, ``risk:tool:software``,
  ``ps:contact`` and ``pol:country`` nodes.
  (`#2970 <https://github.com/vertexproject/synapse/pull/2970>`_)
- Update the CRL bundled within Synapse to revoke the
  ``The Vertex Project Code Signer 00`` key.
  (`#2972 <https://github.com/vertexproject/synapse/pull/2972>`_)

Bugfixes
--------
- Fix an issue in the Axon ``csvrows()`` and ``readlines()`` APIs
  which could cause the Axon service to hang.
  (`#2969 <https://github.com/vertexproject/synapse/pull/2969>`_)

v2.117.0 - 2023-01-04
=====================

Automatic Migrations
--------------------
- The ``risk:tool:software:soft:names`` and ``risk:tool:software:techniques``
  properties are migrated to being unique arrays.
  (`#2950 <https://github.com/vertexproject/synapse/pull/2950>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the  ``risk`` model.
  (`#2950 <https://github.com/vertexproject/synapse/pull/2950>`_)

  ``risk:tool:software``
    The ``soft:names`` and ``techniques`` properties are converted into sorted
    and uniqued arrays.

- Add support to the Cortex ``addStormPkg()`` and ``$lib.pkg.add()`` APIs to
  load Storm Packages which have been signed to allow cryptographic signature
  verification. Root CA and intermediate CA certificates have been embedded
  into Synapse to allow for verification of Rapid Power-Ups signed by
  The Vertex Project.
  (`#2940 <https://github.com/vertexproject/synapse/pull/2940>`_)
  (`#2957 <https://github.com/vertexproject/synapse/pull/2957>`_)
  (`#2963 <https://github.com/vertexproject/synapse/pull/2963>`_)
- Update ``synapse.tools.genpkg`` to add optional code signing to Storm packages
  that it creates.
  (`#2940 <https://github.com/vertexproject/synapse/pull/2940>`_)
- Update ``synapse.tools.genpkg`` to require the packages it produces will be
  JSON compatible when serialized, to avoid possible type coercion issues
  introduced by the Python ``json`` library.
  (`#2958 <https://github.com/vertexproject/synapse/pull/2958>`_)
- Update ``synapse.tools.easycert`` to allow for creating code signing
  certificates and managing certificate revocation lists (CRLs).
  (`#2940 <https://github.com/vertexproject/synapse/pull/2940>`_)
- Add the Nexus index ( ``nexsindx`` ) value to the data returned by the
  ``getCellInfo()`` APIs.
  (`#2949 <https://github.com/vertexproject/synapse/pull/2949>`_)
- Allow the Storm backtick format strings to work with multiline strings.
  (`#2956 <https://github.com/vertexproject/synapse/pull/2956>`_)
- The Storm ``Bytes.json()`` method now raises exceptions that are ``SynErr``
  subclasses when encountering errors. This method has been updated to add
  optional ``encoding`` and ``errors`` arguments, to control how data is
  deserialized.
  (`#2945 <https://github.com/vertexproject/synapse/pull/2945>`_)
- Add support for registering an OAuth2 provider in the Cortex and having
  user tokens automatically refreshed in the background. These APIs are
  exposed in Storm under the ``$lib.inet.http.oauth.v2`` library.
  (`#2910 <https://github.com/vertexproject/synapse/pull/2910>`_)
- STIX validation no longer caches any downloaded files it may use when
  attempting to validate STIX objects.
  (`#2966 <https://github.com/vertexproject/synapse/pull/2966>`_)
- Modified the behavior of Storm emitter functions to remove the read-ahead
  behavior.
  (`#2953 <https://github.com/vertexproject/synapse/pull/2953>`_)

Bugfixes
--------
- Fix some error messages in the Snap which did not properly add variables
  to the message.
  (`#2951 <https://github.com/vertexproject/synapse/pull/2951>`_)
- Fix an error in the ``synapse.tools.aha.enroll`` command example.
  (`#2948 <https://github.com/vertexproject/synapse/pull/2948>`_)
- Fix an error with the ``merge`` command creating ``No form named None``
  warnings in the Cortex logs.
  (`#2952 <https://github.com/vertexproject/synapse/pull/2952>`_)
- Fix the Storm ``inet:smtp:message`` getter and setter for the ``html``
  property so it will correctly produce HTML formatted messages.
  (`#2955 <https://github.com/vertexproject/synapse/pull/2955>`_)
- Several ``certdir`` APIs previously allowed through
  ``openssl.crypto.X509StoreContextError`` and ``openssl.crypto.Error``
  exceptions. These now raise Synapse ``BadCertVerify`` and ``BadCertBytes``
  exceptions.
  (`#2940 <https://github.com/vertexproject/synapse/pull/2940>`_)
- Fix an issue where a Storm package's ``modconf`` values were mutable.
  (`#2964 <https://github.com/vertexproject/synapse/pull/2964>`_)

Improved Documentation
----------------------
- Removed outdated Kubernetes related devops documentation as it is in
  the process of being rewritten.
  (`#2948 <https://github.com/vertexproject/synapse/pull/2948>`_)

Deprecations
------------
- The Cortex APIs ``provStacks()`` and ``getProvStack(iden)`` and the
  corresponding Cortex configuration option ``provenance:en`` have been marked
  as deprecated and are planned to be removed in ``v2.122.0``.
  (`#2682 <https://github.com/vertexproject/synapse/pull/2682>`_)

v2.116.0 - 2022-12-14
=====================

Automatic Migrations
--------------------
- The ``ou:contract:award:price`` and ``ou:contract:budget:price`` properties
  are migrated from ``econ:currency`` to ``econ:price`` types.
  (`#2943 <https://github.com/vertexproject/synapse/pull/2943>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the  ``ou`` model.
  (`#2943 <https://github.com/vertexproject/synapse/pull/2943>`_)

  ``ou:contract``
    The ``award:price`` and ``budget:price`` properties had their types
    changed from ``econ:currency`` to ``econ:price``.
    Add a ``currency`` secondary property to record the currency of the
    ``econ:price`` values.

Bugfixes
--------
- The ``synapse.tools.genpkg`` tool could raise a Python ``TypeError`` when
  the specified package file did not exist. It now raises a ``NoSuchFile``
  exception.
  (`#2941 <https://github.com/vertexproject/synapse/pull/2941>`_)
- When a service is provisioned with an ``aha:provision`` URL placed in a
  ``cell.yaml`` file, that could create an issue when a mirror is deployed
  from that service, preventing it from starting up a second time. Services
  now remove the ``aha:provision`` key from a ``cell.yaml`` file when they
  are booted from a mirror if the URL does not match the boot URL.
  (`#2939 <https://github.com/vertexproject/synapse/pull/2939>`_)
- When deleting a node from the Cortex, secondary properties defined as arrays
  were not checked for their references to other nodes. These references are
  now properly checked prior to node deletion.
  (`#2942 <https://github.com/vertexproject/synapse/pull/2942>`_)

Improved Documentation
----------------------
- Add a Devops task for stamping custom users into Synapse containers to run
  services with arbitrary user and group id values.
  (`#2921 <https://github.com/vertexproject/synapse/pull/2921>`_)
- Remove an invalid reference to ``insecure`` mode in HTTP API documentation.
  (`#2938 <https://github.com/vertexproject/synapse/pull/2938>`_)

v2.115.1 - 2022-12-02
=====================

Features and Enhancements
-------------------------
- Patch release to include an updated version of the ``pytest`` library in
  containers.

v2.115.0 - 2022-12-01
=====================

Automatic Migrations
--------------------
- The ``inet:flow:dst:softnames`` and ``inet:flow:dst:softnames`` properties
  are migrated from ``it:dev:str`` to ``it:prod:softname`` types.
  (`#2930 <https://github.com/vertexproject/synapse/pull/2930>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the  ``inet`` model.
  (`#2930 <https://github.com/vertexproject/synapse/pull/2930>`_)

  ``inet:flow``
    The ``dst:softnames`` and ``src:softnames`` properties had their types
    changed from ``it:dev:str`` values to ``it:prod:softname``.

- Add support for secondary property pivots where the target property is an
  array type.
  (`#2922 <https://github.com/vertexproject/synapse/pull/2922>`_)
- The Storm API ``$lib.bytes.has()`` now returns a false value when the input
  is null.
  (`#2924 <https://github.com/vertexproject/synapse/pull/2924>`_)
- When unpacking loop values in Storm, use the primitive value when the item
  being unpacked is a Storm primitive.
  (`#2928 <https://github.com/vertexproject/synapse/pull/2928>`_)
- Add a ``--del`` option to the ``synapse.tools.moduser`` tool to allow
  removing a user from a service.
  (`#2933 <https://github.com/vertexproject/synapse/pull/2933>`_)
- Add entrypoint hooks to the Aha, Axon, Cortex, Cryotank, and JsonStor
  containers that allow a user to hook the container boot process.
  (`#2919 <https://github.com/vertexproject/synapse/pull/2919>`_)
- Temporary files created by the Axon, Cortex and base Cell class are now
  created in the cell local ``tmp`` directory. In many deployments, this would
  be located in ``/vertex/storage/tmp``.
  (`#2925 <https://github.com/vertexproject/synapse/pull/2925>`_)
- Update the allowed versions of the ``cbor2`` and ``pycryptodome``
  libraries. For users installing ``synapse[dev]``, ``coverage``,
  ``pytest``, ``pytest-cov`` and ``pytest-xdist`` are also updated to
  their latest versions.
  (`#2935 <https://github.com/vertexproject/synapse/pull/2935>`_)

Bugfixes
--------
- When a Storm Dmon definition lacked a ``view`` iden, it would previously
  default to using the Cortex default view. Dmons now prefer to use the user
  default view before using the Cortex default view. This situation would only
  happen with Dmons created via the Telepath API where the ``view`` iden was
  not provided in the Dmon definition.
  (`#2929 <https://github.com/vertexproject/synapse/pull/2929>`_)
- Non-integer mask values provided to ``inet:cidr4`` types now raise a
  ``BadTypeValu`` exception.
  (`#2932 <https://github.com/vertexproject/synapse/pull/2932>`_)
- Fix an incorrect call to ``os.unlink`` in ``synapse.tools.aha.enroll``.
  (`#2926 <https://github.com/vertexproject/synapse/pull/2926>`_)

Improved Documentation
----------------------
- Update the automation section of the Synapse User guide, expanding upon
  the use of cron jobs and triggers across views and forks.
  (`#2917 <https://github.com/vertexproject/synapse/pull/2917>`_)

v2.114.0 - 2022-11-15
=====================

Features and Enhancements
-------------------------
- Updates to the ``crypto`` model.
  (`#2909 <https://github.com/vertexproject/synapse/pull/2909>`_)

  ``crypto:key``
    Add ``iv`` and ``mode`` properties to record initialization vectors
    and cipher modes used with a key.

- Allow the creator for Cron jobs and the user for Triggers to be set. This
  can be used to effectively change the ownership of these automation
  elements.
  (`#2908 <https://github.com/vertexproject/synapse/pull/2908>`_)
- When Storm package ``onload`` queries produce print, warning, or error
  messages, those now have the package name included in the message that
  is logged.
  (`#2913 <https://github.com/vertexproject/synapse/pull/2913>`_)
- Update the Storm package schema to allow declaring configuration variables.
  (`#2880 <https://github.com/vertexproject/synapse/pull/2880>`_)

Bugfixes
--------
- The ``delCertPath()`` APIs in ``synapse.lib.easycert`` no longer attempt
  to create a file path on disk when removing the reference count to a
  certificate path.
  (`#2907 <https://github.com/vertexproject/synapse/pull/2907>`_)
- Fix error handling when Axon is streaming files with the ``readlines()`` and
  ``csvrows()`` APIs.
  (`#2911 <https://github.com/vertexproject/synapse/pull/2911>`_)
- The Storm ``trigger.list`` command failed to print triggers which were
  created in a Cortex prior to ``v2.71.0``. These triggers no longer generate
  an exception when listed.
  (`#2915 <https://github.com/vertexproject/synapse/pull/2915>`_)
- Fix an error in the HTTP API example documentation for the ``requests``
  example.
  (`#2918 <https://github.com/vertexproject/synapse/pull/2918>`_)

Improved Documentation
----------------------
- Add a Devops task to enable the Python warnings filter to log the use of
  deprecated Synapse APIs. Python APIs which have been deprecated have had
  their docstrings updated to reflect their deprecation status.
  (`#2905 <https://github.com/vertexproject/synapse/pull/2905>`_)

v2.113.0 - 2022-11-04
=====================

Automatic Migrations
--------------------
- The ``risk:tool:software:type`` property is migrated to the
  ``risk:tool:software:taxonomy`` type.
  (`#2900 <https://github.com/vertexproject/synapse/pull/2900>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the ``inet``, ``infotech``, ``media``, ``meta``, ``ou``, and
  ``risk`` models.
  (`#2897 <https://github.com/vertexproject/synapse/pull/2897>`_)
  (`#2900 <https://github.com/vertexproject/synapse/pull/2900>`_)
  (`#2903 <https://github.com/vertexproject/synapse/pull/2903>`_)

  ``inet:email:message:link``
    Add a ``text`` property to record the displayed hypertext link if it was
    not a raw URL.

  ``inet:web:acct``
    Add a ``banner`` property representing the banner image for the account.

  ``inet:web:mesg``
    Add a ``deleted`` property to mark if a message was deleted.

  ``inet:web:post:link``
    Add a form to record a link contained in the post text.

  ``it:mitre:attack:group``
    Add an ``isnow`` property to record the potential for MITRE groups to be
    deprecated and renamed.

  ``it:mitre:attack:software``
    Add an ``isnow`` property to record the potential for MITRE software to be
    deprecated and renamed.

  ``it:prod:soft:taxonomy``
    Add a form to record an analyst defined taxonomy of software.

  ``it:prod:soft``
    Add a ``type`` property to record the taxonomy of the software.
    Deprecated the ``techniques`` property in favor of the ``uses`` light edge.

  ``it:sec:cve``
    Deprecated the ``desc``, ``url`` and ``references`` properties in favor of
    using the ``risk:vuln:cve:desc``, ``risk:vuln:cve:url``, and
    ``risk:vuln:cve:references`` properties.

  ``media:news``
    Add a ``topics`` array property to record a list of relevant topics in the
    article.

  ``media:topic``
    Add a form for recording different media topics.

  ``meta:rule``
    Add a ``url`` property to record a URL that documents as rule.

    Add an ``ext:id`` property to record an external identifier for the rule.

  ``meta:sophistication``
    Add a form to record sophistication score with named values: ``very low``,
    ``low``, ``medium``, ``high``, and ``very high``.

  ``ou:campaign``
    Add a ``sophistication`` property to record the assessed sophistication of
    a campaign.

    Deprecate the ``techniques`` property in favor of using the ``uses`` light
    edge.

  ``ou:hasgoal``
    Deprecate the ``ou:hasgoal`` form in favor of using the ``ou:org:goals``
    property.

  ``ou:org``
    Deprecate the ``techniques`` property in favor of using the ``uses`` light
    edge.

  ``ou:technique``
    Add a ``sophistication`` property to record the assessed sophistication of
    a technique.

  ``risk:alert``
    Add a ``url`` property for a URL that documents the alert.

    Add an ``ext:id`` property to record an external ID for the alert.

  ``risk:attack``
    Add a ``sophistication`` property to record the assessed sophistication of
    an attack.

  ``risk:availability``
    Add a taxonomy for availability status values.

  ``risk:threat``
    Add a ``sophistication`` property to record the assessed sophistication of
    a threat cluster.

    Deprecate the ``techniques`` property in favor of the ``uses`` light edge.

  ``risk:tool:software``
    Add an ``availability`` property to record the assessed availability of the
    tool.

    Add a ``sophistication`` property to record the assessed sophistication of
    the software.

    Migrate the ``type`` property to ``risk:tool:software:taxonomy``.

    Deprecate the ``techniques`` property in favor of the ``uses`` light edge.

  ``risk:tool:software:taxonomy``
    Rename the type ``risk:tool:taxonomy`` to ``risk:tool:software:taxonomy``.

  ``risk:vuln``
    Add a ``mitigated`` property to record if a mitigation or fix is available
    for the vulnerability.

    Add an ``exploited`` property to record if the vulnerability has been
    exploited in the wild.

    Add ``timeline:discovered``, ``timeline:published``,
    ``timeline:vendor:notified``, ``timeline:vendor:fixed``, and
    ``timeline:exploited`` properties to record the timeline for significant
    events on a vulnerability.

    Add ``cve:desc``, ``cve:url``, and ``cve:references`` secondary properties
    to record information about the CVE associated with a vulnerability.

    Add ```nist:nvd:source`` to record the name of the organization which
    reported the vulnerability in the NVD.

    Add ``nist:nvd:published`` and ``nist:nvd:modified`` to record when the
    vulnerability was first published, and later modified, in the NVD.

    Add ``cisa:kev:name``, ``cisa:kev:desc``, ``cisa:kev:action``,
    ``cisa:kev:vendor``, ``cisa:kev:product``, ``cisa:kev:added``,
    ``cisa:kev:duedate`` properties to record information about the CISA KEV
    database entry for the vulnerability.

- Annotate the following light edges.
  (`#2900 <https://github.com/vertexproject/synapse/pull/2900>`_)

  ``seen``
    When used with ``meta:source`` nodes, the edge indicates the target
    node was observed by the source node.

  ``stole``
    When used with a ``risk:compromise`` node, the edge indicates the target
    node was stolen or copied as a result of the compromise.

  ``targets``
    When used with ``risk:attack``, the edge indicates the target
    node is targeted by the attack.

    When used with ``risk:attack`` and ``ou:industry`` nodes, the edge
    indicates the attack targeted the industry

    When used with ``risk:threat``, the edge indicates the target
    node is targeted by the threat cluster.

    When used with ``risk:threat`` and ``ou:industry`` nodes, the edge
    indicates the threat cluster targets the industry.

  ``uses``
    When used with ``ou:campaign`` and ``ou:technique`` nodes, the edge
    indicates the campaign used a given technique.

    When used with ``ou:org`` and ``ou:technique`` nodes, the edge
    indicates the organization used a given technique.

    When used with ``risk:threat``, the edge indicates the target
    node was used to facilitate the attack.

    When used with ``risk:attack`` and ``ou:technique`` nodes, the edge
    indicates the attack used a given technique.

    When used with ``risk:attack`` and ``risk:vuln`` nodes, the edge
    indicates the attack used the vulnerability.

    When used with ``risk:tool:software``, the edge indicates the target
    node is used by the tool.

    When used with ``risk:tool:software`` and ``ou:technique`` nodes, the edge
    indicates the tool uses the technique.

    When used with ``risk:tool:software`` and ``risk:vuln`` nodes, the edge
    indicates the tool used the vulnerability.

    When used with ``risk:threat``, the edge indicates the target
    node was used by threat cluster.

    When used with ``risk:threat`` and ``ou:technique`` nodes, the edge
    indicates the threat cluster uses the technique.

    When used with ``risk:threat`` and ``risk:vuln`` nodes, the edge
    indicates the threat cluster uses the vulnerability.

- Add ``$lib.gen.vulnByCve()`` to help generate ``risk:vuln`` nodes for CVEs.
  (`#2903 <https://github.com/vertexproject/synapse/pull/2903>`_)
- Add a unary negation operator to Storm expression syntax.
  (`#2886 <https://github.com/vertexproject/synapse/pull/2886>`_)
- Add ``$lib.crypto.hmac.digest()`` to compute RFC2104 digests in Storm.
  (`#2902 <https://github.com/vertexproject/synapse/pull/2902>`_)
- Update the Storm ``inet:http:resp.json()`` method to add optional
  ``encoding`` and ``errors`` arguments, to control how data is deserialized.
  (`#2898 <https://github.com/vertexproject/synapse/pull/2898>`_)
- Update the Storm ``bytes.decode()`` method to add an optional
  ``errors`` argument, to control how errors are handled when decoding data.
  (`#2898 <https://github.com/vertexproject/synapse/pull/2898>`_)
- Logging of role and user permission changes now includes the authgate iden
  for the changes.
  (`#2891 <https://github.com/vertexproject/synapse/pull/2891>`_)

Bugfixes
--------
- Catch ``RecursionError`` exceptions that can occur in very deep Storm
  pipelines.
  (`#2890 <https://github.com/vertexproject/synapse/pull/2890>`_)

Improved Documentation
----------------------
- Update the Storm reference guide to explain backtick format strings.
  (`#2899 <https://github.com/vertexproject/synapse/pull/2899>`_)
- Update ``guid`` section on Storm type-specific behavior doc with
  some additional guid generation examples.
  (`#2901 <https://github.com/vertexproject/synapse/pull/2901>`_)
- Update Storm control flow documentation to include ``init``, ``fini``, and
  ``try`` / ``catch`` examples.
  (`#2901 <https://github.com/vertexproject/synapse/pull/2901>`_)
- Add examples for creating extended model forms and properties to the
  Synapse admin guide.
  (`#2904 <https://github.com/vertexproject/synapse/pull/2904>`_)

v2.112.0 - 2022-10-18
=====================

Features and Enhancements
-------------------------
- Add ``--email`` as an argument to ``synapse.tools.moduser`` to allow setting
  a user's email address.
  (`#2891 <https://github.com/vertexproject/synapse/pull/2891>`_)
- Add support for ``hxxp[s]:`` prefixes in scrape functions.
  (`#2887 <https://github.com/vertexproject/synapse/pull/2887>`_)
- Make the SYNDEV_NEXUS_REPLAY resolution use ``s_common.envbool()`` in the
  ``SynTest.withNexusReplay()`` helper. Add ``withNexusReplay()`` calls to
  all test helpers which make Cells which previously did not have it
  available.
  (`#2889 <https://github.com/vertexproject/synapse/pull/2889>`_)
  (`#2890 <https://github.com/vertexproject/synapse/pull/2890>`_)
- Add implementations of ``getPermDef()`` and ``getPermDefs()`` to the base
  Cell class.
  (`#2888 <https://github.com/vertexproject/synapse/pull/2888>`_)

Bugfixes
--------
- Fix an idempotency issue in the JsonStor multiqueue implementation.
  (`#2890 <https://github.com/vertexproject/synapse/pull/2890>`_)

Improved Documentation
----------------------
- Add Synapse-GCS (Google Cloud Storage) Advanced Power-Up to the Power-Ups
  list.

v2.111.0 - 2022-10-12
=====================

Features and Enhancements
-------------------------
- Update the Storm grammar to allow specifying a tag property with a variable.
  (`#2881 <https://github.com/vertexproject/synapse/pull/2881>`_)
- Add log messages for user and role management activities in the Cell.
  (`#2877 <https://github.com/vertexproject/synapse/pull/2877>`_)
- The logging of service provisioning steps on Aha and when services were
  starting up was previously done at the ``DEBUG`` level. These are now done
  at the ``INFO`` level.
  (`#2883 <https://github.com/vertexproject/synapse/pull/2883>`_)
- The ``vertexproject/synapse:`` docker images now have the environment
  variable ``SYN_LOG_LEVEL`` set to ``INFO``. Previously this was ``WARNING``.
  (`#2883 <https://github.com/vertexproject/synapse/pull/2883>`_)

Bugfixes
--------
- Move the Nexus ``runMirrorLoop`` task to hang off of the Telepath Proxy
  and not the Telepath client. This results in a faster teardown of the
  ``runMirrorLoop`` task during Nexus shutdown.
  (`#2878 <https://github.com/vertexproject/synapse/pull/2878>`_)
- Remove duplicate tokens presented to users in Storm syntax errors.
  (`#2879 <https://github.com/vertexproject/synapse/pull/2879>`_)
- When bootstrapping a service mirror with Aha provisioning, the ``prov.done``
  file that was left in the service storage directory was the value from the
  upstream service, and not the service that has been provisioned. This
  resulted in ``NoSuchName`` exceptions when restarting mirrors.
  The bootstrapping process now records the correct value in the ``prov.done``
  file.
  (`#2882 <https://github.com/vertexproject/synapse/pull/2882>`_)

v2.110.0 - 2022-10-07
=====================

Features and Enhancements
-------------------------
- Updates to the ``geo`` model.
  (`#2872 <https://github.com/vertexproject/synapse/pull/2872>`_)

  ``geo:telem``
    Add an ``accuracy`` property to record the accuracy of the telemetry reading.

- Add Nexus support to the Axon, to enable mirrored Axon deployments.
  (`#2871 <https://github.com/vertexproject/synapse/pull/2871>`_)
- Add Nexus support for HTTP API sessions.
  (`#2869 <https://github.com/vertexproject/synapse/pull/2869>`_)
- Add support for runtime string formatting in Storm. This is done with
  backtick ( `````) encapsulated strings.
  An example of this is ``$world='world' $lib.print(`hello {$world}`)``
  (`#2870 <https://github.com/vertexproject/synapse/pull/2870>`_)
  (`#2875 <https://github.com/vertexproject/synapse/pull/2875>`_)
- Expose user profile storage on the ``auth:user`` object, with the
  ``profile`` ctor.
  (`#2876 <https://github.com/vertexproject/synapse/pull/2876>`_)
- Storm package command names are now validated against the same regex used
  by the grammar. The ``synapse.tools.genpkg`` tool now validates the compiled
  package against the same schema used by the Cortex.
  (`#2864 <https://github.com/vertexproject/synapse/pull/2864>`_)
- Add ``$lib.gen.newsByUrl()`` and ``$lib.gen.softByName()`` to help generate
  ``media:news`` and ``it:prod:soft`` nodes, respectively.
  (`#2866 <https://github.com/vertexproject/synapse/pull/2866>`_)
- Add a new realtime event stream system to the Cell, accessible remotely via
  ``CellApi.behold()`` and a websocket endpoint, ``/api/v1/behold``. This can
  be used to get realtime changes about services, such as user creation or
  modification events; or layer and view change events in the Cortex.
  (`#2851 <https://github.com/vertexproject/synapse/pull/2851>`_)
- Update stored user password hashing to use PBKDF2. Passwords are migrated
  to this format as successful user logins are performed.
  (`#2868 <https://github.com/vertexproject/synapse/pull/2868>`_)
- Add the ability to restore a backup tarball from a URL to the Cell startup
  process. When a Cell starts via ``initFromArgv()``, if the environment
  variable ``SYN_RESTORE_HTTPS_URL`` is present, that value will be used to
  retrieve a tarball via HTTPS and extract it to the service local storage,
  removing any existing data in the directory. This is done prior to any
  Aha based provisioning.
  (`#2859 <https://github.com/vertexproject/synapse/pull/2859>`_)

Bugfixes
--------
- The embedded Axon inside of a Cortex (used when the ``axon`` config option
  is not set) did not properly have its cell parent set to the Cortex. This
  has been corrected.
  (`#2857 <https://github.com/vertexproject/synapse/pull/2857>`_)
- Fix a typo in the ``cron.move`` help.
  (`#2858 <https://github.com/vertexproject/synapse/pull/2858>`_)

Improved Documentation
----------------------
- Update Storm and Storm HTTP API documentation to show the set of ``opts``
  and different types of message that may be streamed by from Storm APIs.
  Add example HTTP API client code to the Synapse repository.
  (`#2834 <https://github.com/vertexproject/synapse/pull/2834>`_)
- Update the Data Model and Analytical model background documentation.
  Expand on the discussion of light edges use. Expand discussion of tags
  versus forms, linking the two via ``:tag`` props.
  (`#2848 <https://github.com/vertexproject/synapse/pull/2848>`_)

Deprecations
------------
- The Cortex HTTP API endpoint ``/api/v1/storm/nodes`` has been marked as
  deprecated.
  (`#2682 <https://github.com/vertexproject/synapse/pull/2682>`_)
- Add deprecation notes to the help for the Storm ``splice.undo`` and
  ``splice.list`` commands.
  (`#2861 <https://github.com/vertexproject/synapse/pull/2861>`_)
- Provisional Telepath support for Consul based lookups was removed.
  (`#2873 <https://github.com/vertexproject/synapse/pull/2873>`_)

v2.109.0 - 2022-09-27
=====================

Features and Enhancements
-------------------------
- Add a ``format()`` API to ``str`` variables in Storm.
  (`#2849 <https://github.com/vertexproject/synapse/pull/2849>`_)
- Update the Telepath user resolution for TLS links to prefer resolving users
  by the Cell ``aha:network`` over the certificate common name.
  (`#2850 <https://github.com/vertexproject/synapse/pull/2850>`_)
- Update all Synapse tools which make telepath connections to use the
  ``withTeleEnv()`` helper.
  (`#2844 <https://github.com/vertexproject/synapse/pull/2844>`_)
- Update the Telepath and HTTPs TLS listeners to drop RSA based key exchanges
  and disable client initiated renegotiation.
  (`#2845 <https://github.com/vertexproject/synapse/pull/2845>`_)
- Update the minimum allowed versions of the ``aioimaplib`` and ``oauthlib``
  libraries.
  (`#2847 <https://github.com/vertexproject/synapse/pull/2847>`_)
  (`#2854 <https://github.com/vertexproject/synapse/pull/2854>`_)

Bugfixes
--------
- Correct default Telepath ``cell://`` paths in Synapse tools.
  (`#2853 <https://github.com/vertexproject/synapse/pull/2853>`_)
- Fix typos in the inline documentation for several model elements.
  (`#2852 <https://github.com/vertexproject/synapse/pull/2852>`_)
- Adjust expression syntax rules in Storm grammar to remove incorrect
  whitespace sensitivity in certain expression operators.
  (`#2846 <https://github.com/vertexproject/synapse/pull/2846>`_)

Improved Documentation
----------------------
- Update Storm and Storm HTTP API documentation to show the set of ``opts``
  and different types of message that may be streamed by from Storm APIs.
  Add example HTTP API client code to the Synapse repository.
  (`#2834 <https://github.com/vertexproject/synapse/pull/2834>`_)
- Update the Data Model and Analytical model background documentation.
  Expand on the discussion of light edges use. Expand discussion of tags
  versus forms, linking the two via ``:tag`` props.
  (`#2848 <https://github.com/vertexproject/synapse/pull/2848>`_)


v2.108.0 - 2022-09-12
=====================

Features and Enhancements
-------------------------
- Update the Telepath TLS connections to require a minimum TLS version of 1.2.
  (`#2833 <https://github.com/vertexproject/synapse/pull/2833>`_)
- Update the Axon implementation to use the ``initServiceStorage()`` and
  ``initServiceRuntime()`` methods, instead of overriding ``__anit__``.
  (`#2837 <https://github.com/vertexproject/synapse/pull/2837>`_)
- Update the minimum allowed versions of the ``aiosmtplib`` and ``regex``
  libraries.
  (`#2832 <https://github.com/vertexproject/synapse/pull/2832>`_)
  (`#2841 <https://github.com/vertexproject/synapse/pull/2841>`_)

Bugfixes
--------
- Catch ``LarkError`` exceptions in all Storm query parsing modes.
  (`#2840 <https://github.com/vertexproject/synapse/pull/2840>`_)
- Catch ``FileNotFound`` errors in ``synapse.tools.healthcheck``. This could
  be caused by the tool running during container startup, and prior to a
  service making its Unix listening socket available.
  (`#2836 <https://github.com/vertexproject/synapse/pull/2836>`_)
- Fix an issue in ``Axon.csvrows()`` where invalid data would cause
  processing of a file to stop.
  (`#2835 <https://github.com/vertexproject/synapse/pull/2835>`_)
- Address a deprecation warning in the Synapse codebase.
  (`#2842 <https://github.com/vertexproject/synapse/pull/2842>`_)
- Correct the type of ``syn:splice:splice`` to be ``data``. Previously it
  was ``str``.
  (`#2839 <https://github.com/vertexproject/synapse/pull/2839>`_)

Improved Documentation
----------------------
- Replace ``livenessProbe`` references with ``readinessProbe`` in the
  Kubernetes documentation and examples. The ``startupProbe.failureThreshold``
  value was increased to its maximum value.
  (`#2838 <https://github.com/vertexproject/synapse/pull/2838>`_)
- Fix a typo in the Rapid Power-Up documentation.
  (`#2831 <https://github.com/vertexproject/synapse/pull/2831>`_)

v2.107.0 - 2022-09-01
=====================

Automatic Migrations
--------------------
- Migrate the ``risk:alert:type`` property to a ``taxonomy`` type
  and create new nodes as needed.
  (`#2828 <https://github.com/vertexproject/synapse/pull/2828>`_)
- Migrate the ``pol:country:name`` property to a ``geo:name`` type
  and create new nodes as needed.
  (`#2828 <https://github.com/vertexproject/synapse/pull/2828>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the ``geo``, ``inet``, ``media``, ``pol``, ``proj``, and
  ``risk`` models.
  (`#2828 <https://github.com/vertexproject/synapse/pull/2828>`_)
  (`#2829 <https://github.com/vertexproject/synapse/pull/2829>`_)

  ``geo:area``
    Add a new type to record the size of a geographic area.

  ``geo:place:taxonomy``
    Add a form to record an analyst defined taxonomy of different places.

  ``geo:place``
    Add a ``type`` property to record the taxonomy of a place.

  ``inet:web:memb``
    This form has been deprecated.

  ``inet:web:member``
    Add a guid form that represents a web account's membership in a channel or group.

  ``media:news:taxonomy``
    Add a form to record an analyst defined taxonomy of different types or sources of news.

  ``media:news``
    Add a ``type`` property to record the taxonomy of the news.
    Add an ``ext:id`` property to record an external identifier provided by a publisher.

  ``pol:vitals``
    Add a guid form to record the vitals for a country.

  ``pol:country``
    Add ``names``, ``place``, ``dissolved`` and ``vitals`` secondary properties.
    The ``name`` is changed from a ``str`` to a ``geo:name`` type.
    Deprecate the ``pop`` secondary property.

  ``pol:candidate``
    Add an ``incumbent`` property to note if the candidate was an incumbent
    in a race.

  ``proj``
    Add missing docstrings to the ``proj`` model forms.

  ``risk:alert:taxonomy``
    Add a form to record an analyst defined taxonomy of alert types.

  ``risk:alert``
    The ``type`` property is changed from a ``str`` to the
    ``risk:alert:taxonomy`` type.

- Add ``**`` as a power operator for Storm expression syntax.
  (`#2827 <https://github.com/vertexproject/synapse/pull/2827>`_)
- Add a new test helper, ``synapse.test.utils.StormPkgTest`` to assist with
  testing Rapid Power-Ups.
  (`#2819 <https://github.com/vertexproject/synapse/pull/2819>`_)
- Add ``$lib.axon.metrics()`` to get the metrics from the Axon that the
  Cortex is connected to.
  (`#2818 <https://github.com/vertexproject/synapse/pull/2818>`_)
- Add ``pack()`` methods to the ``auth:user`` and ``auth:role``
  objects. This API returns the definitions of the User and Role objects.
  (`#2823 <https://github.com/vertexproject/synapse/pull/2823>`_)
- Change the Storm Package ``require`` values to log debug messages instead
  of raising exceptions if the requirements are not met. Add a
  ``$lib.pkg.deps()`` API that allows inspecting if a package has its
  dependencies met or has conflicts.
  (`#2820 <https://github.com/vertexproject/synapse/pull/2820>`_)

Bugfixes
--------
- Prevent ``None`` objects from being normalized as tag parts from variables
  in Storm.
  (`#2822 <https://github.com/vertexproject/synapse/pull/2822>`_)
- Avoid intermediate conversion to floats during storage operations related to
  Synapse Number objects in Storm.
  (`#2825 <https://github.com/vertexproject/synapse/pull/2825>`_)

Improved Documentation
----------------------
- Add Developer documentation for writing Rapid Power-Ups.
  (`#2803 <https://github.com/vertexproject/synapse/pull/2803>`_)
- Add the ``synapse.tests.utils`` package to the Synapse API autodocs.
  (`#2819 <https://github.com/vertexproject/synapse/pull/2819>`_)
- Update Devops documentation to note the storage requirements for taking
  backups of Synapse services.
  (`#2824 <https://github.com/vertexproject/synapse/pull/2824>`_)
- Update the Storm ``min`` and ``max`` command help to clarify their usage.
  (`#2826 <https://github.com/vertexproject/synapse/pull/2826>`_)

v2.106.0 - 2022-08-23
=====================

Features and Enhancements
-------------------------
- Add a new tool, ``synapse.tools.axon2axon``, for copying the data from one
  Axon to another Axon.
  (`#2813 <https://github.com/vertexproject/synapse/pull/2813>`_)
  (`#2816 <https://github.com/vertexproject/synapse/pull/2816>`_)

Bugfixes
--------
- Subquery filters did not update runtime variables in the outer scope. This
  behavior has been updated to make subquery filter behavior consistent with
  regular subqueries.
  (`#2815 <https://github.com/vertexproject/synapse/pull/2815>`_)
- Fix an issue with converting the Number Storm primitive into its Python
  primitive.
  (`#2811 <https://github.com/vertexproject/synapse/pull/2811>`_)

v2.105.0 - 2022-08-19
=====================

Features and Enhancements
-------------------------
- Add a Number primitive to Storm to facilitate fixed point math
  operations. Values in expressions which are parsed as floating
  point values will now be Numbers by default. Values can also
  be cast to Numbers with ``$lib.math.number()``.
  (`#2762 <https://github.com/vertexproject/synapse/pull/2762>`_)
- Add ``$lib.basex.encode()`` and ``$lib.basex.decode()`` for
  encoding and decoding strings using arbitrary charsets.
  (`#2807 <https://github.com/vertexproject/synapse/pull/2807>`_)
- The tag removal operator (``-#``) now accepts lists of tags
  to remove.
  (`#2808 <https://github.com/vertexproject/synapse/pull/2808>`_)
- Add a ``$node.difftags()`` API to calculate and optionally apply
  the difference between a list of tags and those present on a node.
  (`#2808 <https://github.com/vertexproject/synapse/pull/2808>`_)
- Scraped Ethereum addresses are now returned in their EIP55
  checksummed form. This change also applies to lookup mode.
  (`#2809 <https://github.com/vertexproject/synapse/pull/2809>`_)
- Updates to the ``mat``, ``ps``, and ``risk`` models.
  (`#2804 <https://github.com/vertexproject/synapse/pull/2804>`_)

  ``mass``
    Add a type for storing mass with grams as a base unit.

  ``ps:vitals``
    Add a form to record statistics and demographic data about a person
    or contact.

  ``ps:person``
    Add a ``vitals`` secondary property to record the most recent known
    vitals for the person.

  ``ps:contact``
    Add a ``vitals`` secondary property to record the most recent known
    vitals for the contact.

  ``risk:tool:taxonomy``
    Add a form to record an analyst defined taxonomy of different tools.

  ``risk:tool:software``
    Add a form to record software tools used in threat activity.

  ``risk:threat``
    Add ``reporter``, ``reporter:name``, ``org:loc``, ``org:names``,
    and ``goals`` secondary properties.

- Annotate the following light edges.
  (`#2804 <https://github.com/vertexproject/synapse/pull/2804>`_)

  ``uses``
    When used with ``risk:threat`` nodes, the edge indicates the target
    node is used by the source node.

Bugfixes
--------
- Fix language used in the ``model.deprecated.check`` command.
  (`#2806 <https://github.com/vertexproject/synapse/pull/2806>`_)
- Remove the ``-y`` switch in the ``count`` command.
  (`#2806 <https://github.com/vertexproject/synapse/pull/2806>`_)

v2.104.0 - 2022-08-09
=====================

Automatic Migrations
--------------------
- Migrate `crypto:x509:cert:serial` from `str` to `hex` type. Existing values
  which cannot be converted as integers or hex values will be moved into
  nodedata under the key ``migration:0_2_10`` as ``{'serial': value}``
  (`#2789 <https://github.com/vertexproject/synapse/pull/2789>`_)
- Migrate ``ps:contact:title`` to the ``ou:jobtitle`` type and create
  ``ou:jobtitle`` nodes.
  (`#2789 <https://github.com/vertexproject/synapse/pull/2789>`_)
- Correct hugenum property index values for values with more than
  28 digits of precision.
  (`#2766 <https://github.com/vertexproject/synapse/pull/2766>`_)
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the ``crypto`` and ``ps`` models.
  (`#2789 <https://github.com/vertexproject/synapse/pull/2789>`_)

  ``crypto:x509:cert``
    The ``serial`` secondary property has been changed from a ``str`` to a
    ``hex`` type.

  ``ps:contact``
    The type of the ``title`` secondary property has been changed from a
    ``str`` to an ``ou:jobtitle``.

- Add ``$lib.hex.toint()``, ``$lib.hex.fromint()``, ``$lib.hex.trimext()``
  and ``$lib.hex.signext()`` Storm APIs for handling hex encoded integers.
  (`#2789 <https://github.com/vertexproject/synapse/pull/2789>`_)
- Add ``set()`` and ``setdefault()`` APIs on the SynErr exception class.
  Improve support for unpickling SynErr exceptions.
  (`#2797 <https://github.com/vertexproject/synapse/pull/2797>`_)
- Add logging configuration to methods which are called in spawned processes,
  and log exceptions occurring in the processes before tearing them down.
  (`#2795 <https://github.com/vertexproject/synapse/pull/2795>`_)

Bugfixes
--------
- BadTypeValu errors raised when normalizing a tag timestamp now include
  the name of the tag being set.
  (`#2797 <https://github.com/vertexproject/synapse/pull/2797>`_)
- Correct a CI issue that prevented the v2.103.0 Docker images from
  being published.
  (`#2798 <https://github.com/vertexproject/synapse/pull/2798>`_)

Improved Documentation
----------------------
- Update data model documentation.
  (`#2796 <https://github.com/vertexproject/synapse/pull/2796>`_)

v2.103.0 - 2022-08-05
=====================

Features and Enhancements
-------------------------
- Updates to the ``it``, ``ou``, and ``risk`` models.
  (`#2778 <https://github.com/vertexproject/synapse/pull/2778>`_)

  ``it:prod:soft``
    Add a ``techniques`` secondary property to record techniques employed by
    the author of the software.

  ``ou:campaign``
    Add a ``techniques`` secondary property to record techniques employed by
    the campaign.

  ``ou:org``
    Add a ``techniques`` secondary property to record techniques employed by
    the org.

  ``ou:technique``
    Add a form to record specific techniques used to achieve a goal.

  ``ou:technique:taxonomy``
    Add a form to record an analyst defined taxonomy of different techniques.

  ``risk:attack``
    Add a ``techniques`` secondary property to record techniques employed
    during the attack.
    Deprecate the following secondary properties, in favor of using light
    edges.

      - ``target``
      - ``target:host``
      - ``target:org``
      - ``target:person``
      - ``target:place``
      - ``used:email``
      - ``used:file``
      - ``used:host``
      - ``used:server``
      - ``used:software``
      - ``used:url``
      - ``used:vuln``
      - ``via:email``
      - ``via:ipv4``
      - ``via:ipv6``
      - ``via:phone``

  ``risk:compromise``
    Add a ``techniques`` secondary property to record techniques employed
    during the compromise.

  ``risk:threat``
    Add a form to record a threat cluster or subgraph of threat activity
    attributable to one group.

- Annotate the following light edges.
  (`#2778 <https://github.com/vertexproject/synapse/pull/2778>`_)

  ``targets``
    When used with ``ou:org``, ``ou:campaign``, ``risk:threat``, or
    ``risk:attack`` nodes, the edge indicates the target node was targeted
    by the source node.

  ``uses``
    When used with an ``ou:campaign`` or ``risk:attack`` node, the edge
    indicates the target node is used by the source node.

- Change the behavior of the Storm ``count`` command to consume nodes.
  If the previous behavior is desired, use the ``--yield`` option when
  invoking the ``count`` command.
  (`#2779 <https://github.com/vertexproject/synapse/pull/2779>`_)
- Add ``$lib.random.int()`` API to Storm for generating random integers.
  (`#2783 <https://github.com/vertexproject/synapse/pull/2783>`_)
- Add a new tool, ``synapse.tools.livebackup`` for taking a live backup of
  a service.
  (`#2788 <https://github.com/vertexproject/synapse/pull/2788>`_)
- The Storm ``$lib.jsonstor.cacheset()`` API now returns a dict containing the
  path and time. The ``$lib.jsonstor.cacheget()`` API now has an argument to
  retrieve the entire set of enveloped data.
  (`#2790 <https://github.com/vertexproject/synapse/pull/2790>`_)
- Add a HTTP 404 handler for the Axon ``v1/by/sha256/<sha256>`` endpoint which
  catches invalid ``<sha256>`` values.
  (`#2780 <https://github.com/vertexproject/synapse/pull/2780>`_)
- Add helper scripts for doing bulk Synapse Docker image builds and testing.
  (`#2716 <https://github.com/vertexproject/synapse/pull/2716>`_)
- Add ``aha:\\`` support to ``synapse.tools.csvtool``.
  (`#2791 <https://github.com/vertexproject/synapse/pull/2791>`_)

Bugfixes
--------
- Ensure that errors that occur when backing up a service are logged prior
  to tearing down the subprocess performing the backup.
  (`#2781 <https://github.com/vertexproject/synapse/pull/2781>`_)
- Add missing docstring for ``$lib.stix.import``.
  (`#2786 <https://github.com/vertexproject/synapse/pull/2786>`_)
- Allow setting tags on a Node from a Storm ``List`` object.
  (`#2782 <https://github.com/vertexproject/synapse/pull/2782>`_)

Improved Documentation
----------------------
- Remove ``synapse-google-ct`` from the list of Rapid Power-Ups.
  (`#2779 <https://github.com/vertexproject/synapse/pull/2779>`_)
- Add developer documentation for building Synapse Docker containers.
  (`#2716 <https://github.com/vertexproject/synapse/pull/2716>`_)
- Fix spelling errors in model documentation.
  (`#2782 <https://github.com/vertexproject/synapse/pull/2782>`_)

Deprecations
------------
- The ``vertexproject/synapse:master-py37`` and
  ``vertexproject/synapse:v2.x.x-py37`` Docker containers are no longer being
  built.
  (`#2716 <https://github.com/vertexproject/synapse/pull/2716>`_)

v2.102.0 - 2022-07-25
=====================

Features and Enhancements
-------------------------
- Updates to the ``crypto``, ``geo``, ``inet``, ``mat``, ``media``, ``ou``,
  ``pol``, and ``proj`` models.
  (`#2757 <https://github.com/vertexproject/synapse/pull/2757>`_)
  (`#2771 <https://github.com/vertexproject/synapse/pull/2771>`_)

  ``crypto:key``
    Add ``public:md5``, ``public:sha1``, and ``public:sha256`` secondary
    properties to record those hashes for the public key.
    Add ``private:md5``, ``private:sha1``, and ``private:sha256`` secondary
    properties to record those hashes for the public key.

  ``geo:nloc``
    The ``geo:nloc`` form has been deprecated.

  ``geo:telem``
    Add a new form to record a the location of a given node at a given time.
    This replaces the use of ``geo:nloc``.

  ``it:sec:c2:config``
    Add a ``proxies`` secondary property to record proxy URLS used to
    communicate to a C2 server.
    Add a ``listens`` secondary property to record urls the software should
    bind.
    Add a ``dns:resolvers`` secondary property to record DNS servers the
    software should use.
    Add a ``http:headers`` secondary property to record HTTP headers the
    software should use.

  ``it:exec:query``
    Add a new form to record an instance of a query executed on a host.

  ``it:query``
    Add a new form to record query strings.

  ``mat:type``
    Add a taxonomy type to record taxonomies of material specifications or
    items.

  ``mat:item``
    Add a ``type`` secondary property to record the item type.

  ``mat:spec``
    Add a ``type`` secondary property to record the item type.

  ``media:news``
    Add a ``publisher`` secondary property to record the org that published
    the news.
    Add a ``publisher:name`` secondary property to record the name of the org.
    Deprecate the ``org`` secondary property.

  ``ou:campaign``
    Add a ``conflict`` secondary property to record the primary conflict
    associated the campaign.

  ``ou:conflict``
    Add a new form to record a conflict between two or more campaigns which
    have mutually exclusive goals.

  ``ou:contribution``
    Add a new form to represent contributing material support to a campaign.

  ``pol:election``
    Add a new form to record an election.

  ``pol:race``
    Add a new form to record indivdual races in an election.

  ``pol:office``
    Add a new form to record an appointed or elected office.

  ``pol:term``
    Add a new form to record the term in office for an individual.

  ``pol:candidate``
    Add a form to record a candidate for a given race.

  ``pol:pollingplace``
    Add a form to record the polling locations for a given election.

  ``proj:ticket``
    Add a ``ext:creator`` secondary form to record contact information from
    and external system.

- Annotate the following light edges.
  (`#2757 <https://github.com/vertexproject/synapse/pull/2757>`_)

  ``about``
    A light edge created by the Storm ``note.add`` command, which records
    the relationship between a ``meta:note`` node and the target node.

  ``includes``
    When used with a ``ou:contribution`` node, the edge indicates the target
    node was the contribution made.

  ``has``
    When used with a ``meta:ruleset`` and ``meta:rule`` node, indicates
    the ruleset contains the rule.

  ``matches``
    When used with a ``meta:rule`` node, the edge indicates the target
    node matches the rule.

  ``refs``
    A light edge where the source node refers to the target node.

  ``seenat``
    When used with a ``geo:telem`` target node, the edge indicates the source
    node was seen a given location.

  ``uses``
    When used with a ``ou:org`` node, the edge indicates the target node
    is used by the organization.

- Commonly used light edges are now being annotated in the model, and are
  available through Cortex APIs which expose the data model.
  (`#2757 <https://github.com/vertexproject/synapse/pull/2757>`_)
- Make Storm command argument parsing errors into exceptions. Previously the
  argument parsing would cause the Storm runtime to be torn down with
  ``print`` messages, which could be missed. This now means that automations
  which have a invalid Storm command invocation will fail loudly.
  (`#2769 <https://github.com/vertexproject/synapse/pull/2769>`_)
- Allow a Storm API caller to set the task identifier by setting the ``task``
  value in the Storm ``opts`` dictionary.
  (`#2768 <https://github.com/vertexproject/synapse/pull/2768>`_)
  (`#2774 <https://github.com/vertexproject/synapse/pull/2774>`_)
- Add support for registering and exporting custom STIX objects with the
  ``$lib.stix`` Storm APIS.
  (`#2773 <https://github.com/vertexproject/synapse/pull/2773>`_)
- Add APIS and Storm APIs for enumerating mirrors that have been registered
  with AHA.
  (`#2760 <https://github.com/vertexproject/synapse/pull/2760>`_)

Bugfixes
--------
- Ensure that auto-adds are created when merging part of a View when using
  the Storm ``merge --apply`` command.
  (`#2770 <https://github.com/vertexproject/synapse/pull/2770>`_)
- Add missing support for handling timezone offsets without colon separators
  when normalizing ``time`` values. ``time`` values which contain timezone
  offsets and not enough data to resolve minute level resolution will now fail
  to parse.
  (`#2772 <https://github.com/vertexproject/synapse/pull/2772>`_)
- Fix an issue when normalizing ``inet:url`` values when the host value was
  the IPv4 address ``0.0.0.0``.
  (`#2771 <https://github.com/vertexproject/synapse/pull/2771>`_)
- Fix an issue with the Storm ``cron.list`` command, where the command failed
  to run when a user had been deleted.
  (`#2776 <https://github.com/vertexproject/synapse/pull/2776>`_)

Improved Documentation
----------------------
- Update the Storm user documentation to include the Embedded Property syntax,
  which is a shorthand (``::``) that can be used to reference properties on
  adjacent nodes.
  (`#2767 <https://github.com/vertexproject/synapse/pull/2767>`_)
- Update the Synapse Glossary.
  (`#2767 <https://github.com/vertexproject/synapse/pull/2767>`_)
- Update Devops documentation to clarify the Aha URLs which end with``...``
  are intentional.
  (`#2775 <https://github.com/vertexproject/synapse/pull/2775>`_)

v2.101.1 - 2022-07-14
=====================

Bugfixes
--------
- Fix an issue where the Storm ``scrape`` command could fail to run with
  inbound nodes.
  (`#2761 <https://github.com/vertexproject/synapse/pull/2761>`_)
- Fix broken links in documentation.
  (`#2763 <https://github.com/vertexproject/synapse/pull/2763>`_)
- Fix an issue with the Axon ``AxonHttpBySha256V1`` API handler related to
  detecting ``Range`` support in the Axon.
  (`#2764 <https://github.com/vertexproject/synapse/pull/2764>`_)


v2.101.0 - 2022-07-12
=====================

Automatic Migrations
--------------------
- Create nodes in the Cortex for the updated properties noted in the data
  model updates listed below.
- Axon indices are migrated to account for storing offset information to
  support the new offset and size API options.
- See :ref:`datamigration` for more information about automatic migrations.

Features and Enhancements
-------------------------
- Updates to the ``crypto``, ``infotech``, ``ps``, and ``transport`` models.
  (`#2720 <https://github.com/vertexproject/synapse/pull/2720>`_)
  (`#2738 <https://github.com/vertexproject/synapse/pull/2738>`_)
  (`#2739 <https://github.com/vertexproject/synapse/pull/2739>`_)
  (`#2747 <https://github.com/vertexproject/synapse/pull/2747>`_)

  ``crypto:smart:effect:minttoken``
    Add a new form to model smart contract effects which create
    non-fungible tokens.

  ``crypto:smart:effect:burntoken```
    Add a new form to model smart contract effects which destroy
    non-fungible tokens.

  ``crypto:smart:effect:proxytoken``
    Add a new form that tracks grants for a non-owner address the ability to
    manipulate a specific non-fungible token.

  ``crypto:smart:effect:proxytokenall``
    Add a new form that tracks grants for a non-owner address the ability to
    manipulate all of the non-fungible tokens.

  ``crypto:smart:effect:proxytokens``
    Add a new form that tracks grants for a non-owner address to manipulate
    fungible tokens.

  ``it:av:signame``
    Add a new form to track AV signature names. Migrate
    ``it:av:filehit:sig:name`` and ``it:av:sig:name`` to use the new form.

  ``it:exec:proc``
    Add a ``name`` secondary property to track the display name of a process.
    Add a ``path:base`` secondary property to track the basename of the
    executable for the process.

  ``ps:contact``
    Add an ``orgnames`` secondary property to track an array of orgnames
    associated with a contact.

  ``transport:sea:vessel``
    Add ``make`` and ``model`` secondary properties to track information
    about the vessel.

- Add a new Storm command, ``movenodes``, that can be used to move a node
  entirely from one layer to another.
  (`#2714 <https://github.com/vertexproject/synapse/pull/2714>`_)
- Add a new Storm library, ``$lib.gen``, to assist with creating nodes based
  on secondary property based deconfliction.
  (`#2754 <https://github.com/vertexproject/synapse/pull/2754>`_)
- Add a ``sorted()`` method to the ``stat:tally`` object, to simplify
  handling of tallied data.
  (`#2748 <https://github.com/vertexproject/synapse/pull/2748>`_)
- Add a new Storm function, ``$lib.mime.html.totext()``, to extract inner tag
  text from HTML strings.
  (`#2744 <https://github.com/vertexproject/synapse/pull/2744>`_)
- Add Storm functions ``$lib.crypto.hashes.md5()``,
  ``$lib.crypto.hashes.sha1()``, ``$lib.crypto.hashes.sha256()`` and
  ``$lib.crypto.hashes.sha512()`` to allow hashing bytes directly in Storm.
  (`#2743 <https://github.com/vertexproject/synapse/pull/2743>`_)
- Add an ``Axon.csvrows()`` API for streaming CSV rows from an Axon, and a
  corresponding ``$lib.axon.csvrows()`` Storm API.
  (`#2719 <https://github.com/vertexproject/synapse/pull/2719>`_)
- Expand Synapse requirements to include updated versions of the
  ``pycryptome``, ``pygments``, and ``scalecodec`` modules.
  (`#2752 <https://github.com/vertexproject/synapse/pull/2752>`_)
- Add range support to ``Axon.get()`` to read bytes from a given offset and
  size. The ``/api/v1/axon/files/by/sha256/<SHA-256>`` HTTP API has been
  updated to support a ``Range`` header that accepts a ``bytes`` value to read
  a subset of bytes that way as well.
  (`#2731 <https://github.com/vertexproject/synapse/pull/2731>`_)
  (`#2755 <https://github.com/vertexproject/synapse/pull/2755>`_)
  (`#2758 <https://github.com/vertexproject/synapse/pull/2758>`_)

Bugfixes
--------
- Fix ``$lib.time.parse()`` when ``%z`` is used in the format specifier.
  (`#2749 <https://github.com/vertexproject/synapse/pull/2749>`_)
- Non-string form-data fields are now serialized as JSON when using the
  ``Axon.postfiles()`` API.
  (`#2751 <https://github.com/vertexproject/synapse/pull/2751>`_)
  (`#2759 <https://github.com/vertexproject/synapse/pull/2759>`_)
- Fix a byte-alignment issue in the ``Axon.readlines()`` API.
  (`#2719 <https://github.com/vertexproject/synapse/pull/2719>`_)


v2.100.0 - 2022-06-30
=====================

Features and Enhancements
-------------------------
- Support parsing CVSS version 3.1 prefix values.
  (`#2732 <https://github.com/vertexproject/synapse/pull/2732>`_)

Bugfixes
--------
- Normalize tag value lists in ``snap.addTag()`` to properly handle JSON
  inputs from HTTP APIs.
  (`#2734 <https://github.com/vertexproject/synapse/pull/2734>`_)
- Fix an issue that allowed multiple concurrent streaming backups to occur.
  (`#2725 <https://github.com/vertexproject/synapse/pull/2725>`_)

Improved Documentation
----------------------
- Add an entry to the devops task documentation for trimming Nexus logs.
  (`#2730 <https://github.com/vertexproject/synapse/pull/2730>`_)
- Update the list of available Rapid Power-Ups.
  (`#2735 <https://github.com/vertexproject/synapse/pull/2735>`_)


v2.99.0 - 2022-06-23
====================

Features and Enhancements
-------------------------
- Add an extensible STIX 2.1 import library, ``$lib.stix.import``. The
  function ``$lib.stix.import.ingest()`` can be used to STIX bundles into a
  Cortex via Storm.
  (`#2727 <https://github.com/vertexproject/synapse/pull/2727>`_)
- Add a Storm ``uptime`` command to display the uptime of a Cortex or a Storm
  Service configured on the Cortex.
  (`#2728 <https://github.com/vertexproject/synapse/pull/2728>`_)
- Add ``--view`` and ``--optsfile`` arguments to ``synapse.tools.csvtool``.
  (`#2726 <https://github.com/vertexproject/synapse/pull/2726>`_)

Bugfixes
--------
- Fix an issue getting the maximum available memory for a host running with
  Linux cgroupsv2 apis.
  (`#2728 <https://github.com/vertexproject/synapse/pull/2728>`_)

v2.98.0 - 2022-06-17
====================

Features and Enhancements
-------------------------
- Updates to the ``econ`` model.
  (`#2717 <https://github.com/vertexproject/synapse/pull/2717>`_)

  ``econ:acct:balance``
    Add ``total:received`` and ``total:sent`` properties to record total
    currency sent and received by the account.

- Add additional debug logging for Aha provisioning.
  (`#2722 <https://github.com/vertexproject/synapse/pull/2722>`_)
- Adjust whitespace requirements on Storm grammar related to tags.
  (`#2721 <https://github.com/vertexproject/synapse/pull/2721>`_)
- Always run the function provided to the Storm ``divert`` command per node.
  (`#2718 <https://github.com/vertexproject/synapse/pull/2718>`_)

Bugfixes
--------
- Fix an issue that prevented function arguments named ``func`` in Storm
  function calls.
  (`#2715 <https://github.com/vertexproject/synapse/pull/2715>`_)
- Ensure that active coroutines have been cancelled when changing a Cell from
  active to passive status; before starting any passive coroutines.
  (`#2713 <https://github.com/vertexproject/synapse/pull/2713>`_)
- Fix an issue where ``Nexus._tellAhaReady`` was registering with the Aha
  service when the Cell did not have a proper Aha service name set.
  (`#2723 <https://github.com/vertexproject/synapse/pull/2723>`_)


v2.97.0 - 2022-06-06
====================

Features and Enhancements
-------------------------
- Add an ``/api/v1/aha/provision/service`` HTTP API to the Aha service. This
  can be used to generate ``aha:provision`` URLs.
  (`#2707 <https://github.com/vertexproject/synapse/pull/2707>`_)
- Add ``proxy`` options to ``$lib.inet.http`` Storm APIs, to allow an admin
  user to specify an alternative (or to disable) proxy setting.
  (`#2706 <https://github.com/vertexproject/synapse/pull/2706>`_)
- Add a ``--tag`` and ``--prop`` option to the Storm ``diff`` command. Update
  the Storm ``merge`` command examples to show more real-world use cases.
  (`#2710 <https://github.com/vertexproject/synapse/pull/2710>`_)
- Add the ability to set the layers in a non-forked view with the
  ``$view.set(layers, $iden)`` API on the Storm view object.
  (`#2711 <https://github.com/vertexproject/synapse/pull/2711>`_)
- Improve Storm parser logic for handling list and expression syntax.
  (`#2698 <https://github.com/vertexproject/synapse/pull/2698>`_)
  (`#2708 <https://github.com/vertexproject/synapse/pull/2708>`_)

Bugfixes
--------
- Improve error handling of double quoted strings in Storm when null
  characters are present in the raw query string. This situation now raises a
  BadSyntax error instead of an opaque Python ValueError.
  (`#2709 <https://github.com/vertexproject/synapse/pull/2709>`_)
- Fix unquoted JSON keys which were incorrectly allowed in Storm JSON style
  expression syntax.
  (`#2698 <https://github.com/vertexproject/synapse/pull/2698>`_)
- When merging layer data, add missing permission checks for light edge and
  node data changes.
  (`#2671 <https://github.com/vertexproject/synapse/pull/2671>`_)


v2.96.0 - 2022-05-31
====================

Features and Enhancements
-------------------------
- Updates to the ``transport`` model.
  (`#2697 <https://github.com/vertexproject/synapse/pull/2697>`_)

  ``velocity``
    Add a new base type to record velocities in millimeters/second.

  ``transport:direction``
    Add a new type to indicate a direction of movement with respect to true
    North.

  ``transport:air:telem``
    Add ``:course`` and ``:heading`` properties to record the direction of travel.
    Add ``:speed``, ``:airspeed`` and ``:verticalspeed`` properties to record
    the speed of travel.

  ``transport:sea:telem``
    Add ``:course`` and ``:heading`` properties to record the direction of travel.
    Add a ``:speed`` property to record the speed of travel.
    Add ``:destination``, ``:destination:name`` and ``:destination:eta`` to record
    information about the destination.

- Restore the precedence of environment variables over ``cell.yaml`` options
  during Cell startup. API driven overrides are now stored in the
  ``cell.mods.yaml`` file.
  (`#2699 <https://github.com/vertexproject/synapse/pull/2699>`_)
- Add ``--dmon-port`` and ``--https-port`` options to the
  ``synapse.tools.aha.provision.service`` tool in order to specify fixed
  listening ports during provisioning.
  (`#2703 <https://github.com/vertexproject/synapse/pull/2703>`_)
- Add the ability of ``synapse.tools.moduser`` to set user passwords.
  (`#2695 <https://github.com/vertexproject/synapse/pull/2695>`_)
- Restore the call to the ``recover()`` method on the Nexus during Cell
  startup.
  (`#2701 <https://github.com/vertexproject/synapse/pull/2701>`_)
- Add ``mesg`` arguments to ``NoSuchLayer`` exceptions.
  (`#2696 <https://github.com/vertexproject/synapse/pull/2696>`_)
- Make the LMDB slab startup more resilient to a corrupted ``cell.opts.yaml``
  file.
  (`#2694 <https://github.com/vertexproject/synapse/pull/2694>`_)

Bugfixes
--------
- Fix missing variable checks in Storm.
  (`#2702 <https://github.com/vertexproject/synapse/pull/2702>`_)

Improved Documentation
----------------------
- Add a warning to the deployment guide about using Docker on Mac OS.
  (`#2700 <https://github.com/vertexproject/synapse/pull/2700>`_)

v2.95.1 - 2022-05-24
====================

Bugfixes
--------
- Fix a regression in the Telepath ``aha://`` update from ``v2.95.0``.
  (`#2693 <https://github.com/vertexproject/synapse/pull/2693>`_)


v2.95.0 - 2022-05-24
====================

Features and Enhancements
-------------------------
- Add a ``search`` mode to Storm. The ``search`` mode utilizes the Storm
  search interface to lift nodes. The ``lookup`` mode no longer uses the
  search interface.
  (`#2689 <https://github.com/vertexproject/synapse/pull/2689>`_)
- Add a ``?mirror=true`` flag to ``aha://`` Telepath URLs which will cause
  the Aha service lookups to prefer using a mirror of the service rather than
  the leader.
  (`#2681 <https://github.com/vertexproject/synapse/pull/2681>`_)
- Add ``$lib.inet.http.urlencode()`` and ``$lib.inet.http.urldecode()`` Storm
  APIs for handling URL encoding.
  (`#2688 <https://github.com/vertexproject/synapse/pull/2688>`_)
- Add type validation for all Cell configuration options throughout the
  lifetime of the Cell and all operations which modify its configuration
  values. This prevents invalid values from being persisted on disk.
  (`#2687 <https://github.com/vertexproject/synapse/pull/2687>`_)
  (`#2691 <https://github.com/vertexproject/synapse/pull/2691>`_)

Bugfixes
--------
- Fix an issue where the ``=`` sign in the Storm grammar was assigned an
  anonymous terminal name by the grammar parser. This caused an issue with
  interpreting various syntax errors.
  (`#2690 <https://github.com/vertexproject/synapse/pull/2690>`_)


v2.94.0 - 2022-05-18
====================

Automatic Migrations
--------------------
- Re-normalize the migrated properties noted in the data model updates listed
  below. See :ref:`datamigration` for more information about automatic
  migrations.

Features and Enhancements
-------------------------
- Updates to the ``crypto``, ``infotech``, ``ou``, and ``person`` models.
  (`#2620 <https://github.com/vertexproject/synapse/pull/2620>`_)
  (`#2684 <https://github.com/vertexproject/synapse/pull/2684>`_)

  ``crypto:algorithm``
    Add a form to represent a named cryptography algorithm.

  ``crypto:key``
    Add a form to represent a cryptographic key and algorithm.

  ``crypto:smart:effect:transfertoken``
    Add a form to represent the effect of transferring ownership of a
    non-fungible token.

  ``crypto:smart:effect:transfertokens``
    Add a form to represent the effect of transferring multiple fungible
    tokens.

  ``crypto:smart:effect:edittokensupply``
    Add a form to represent the increase or decrease in the supply of
    fungible tokens.

  ``it:prod:softname``
    Add a form to represent a software name.

  ``it:host``
    Add a ``:os:name`` secondary property.

  ``it:mitre:attack:software``
    Migrate the ``:name`` and ``:names`` properties to ``it:prod:softname``
    type.

  ``it:prod:soft``
    Migrate the ``:name`` and ``:names`` properties to ``it:prod:softname``
    type.

  ``it:prod:softver``
    Deprecate the ``:software:name`` property.
    Migrate the ``:name`` and ``:names`` properties to ``it:prod:softname``
    type.

  ``it:app:yara:rule``
    Add a ``:family`` property to represent the software family the rule is
    designed to detect.

  ``it:sec:c2:config``
    Add a form to represent C2 configuration data.

  ``ou:campaign``
    Add a ``:org:name`` property to represent the name of the organization
    responsible the campaign.
    Add a ``:org:fqdn`` property to represent the fqdn of the organization
    responsible the campaign.
    Add a ``:team`` property to represent the team responsible for the
    campaign.

  ``ou:team``
    Add a form to represent a team within an organization.

  ``ou:industry``
    Migrate the ``:name`` property to ``ou:industryname`` type.
    Add a ``:names`` property for alternative names.

  ``ou:industryname``
    Add a form to represent the name of an industry.

  ``ou:position``
    Add a ``:team`` property to represent the team associated with a given
    position.

  ``ps:contact``
    Add a ``:crypto:address`` property to represent the crypto currency
    address associated with the contact.

- Add ``$lib.copy()`` to Storm. This allows making copies of objects which
  are compatible with being serialized with msgpack.
  (`#2678 <https://github.com/vertexproject/synapse/pull/2678>`_)
- Remove `print` events from the Storm `limit` command.
  (`#2674 <https://github.com/vertexproject/synapse/pull/2674>`_)

Bugfixes
--------
- Fix an issue where client certificates presented in Telepath ``ssl``
  connections could fallback to resolving users by a prefix. This was not
  intended to be allowed when client certificates are used with Telepath.
  (`#2675 <https://github.com/vertexproject/synapse/pull/2675>`_)
- Fix an issue where ``node:del`` triggers could fail to fire when adding
  nodeedits directly to a view or snap.
  (`#2654 <https://github.com/vertexproject/synapse/pull/2654>`_)
- Fix header escaping when generating autodoc content for Synapse Cells.
  (`#2677 <https://github.com/vertexproject/synapse/pull/2677>`_)
- Assorted unit tests fixes to make tests more stable.
  (`#2680 <https://github.com/vertexproject/synapse/pull/2680>`_)
- Fix an issue with Storm function argument parsing.
  (`#2685 <https://github.com/vertexproject/synapse/pull/2685>`_)

Improved Documentation
----------------------
- Add an introduction to Storm libraries and types.
  (`#2670 <https://github.com/vertexproject/synapse/pull/2670>`_)
  (`#2683 <https://github.com/vertexproject/synapse/pull/2683>`_)
- Fix small typos and corrections in the devops documentation.
  (`#2673 <https://github.com/vertexproject/synapse/pull/2673>`_)


v2.93.0 - 2022-05-04
====================

Features and Enhancements
-------------------------
- Updates to the ``inet`` and ``infotech`` models.
  (`#2666 <https://github.com/vertexproject/synapse/pull/2666>`_)

  ``:sandbox:file``
      Add a ``sandbox:file`` property to record an initial sample from a
      sandbox environment to the following forms:

        ``it:exec:proc``
        ``it:exec:thread``
        ``it:exec:loadlib``
        ``it:exec:mmap``
        ``it:exec:mutex``
        ``it:exec:pipe``
        ``it:exec:url``
        ``it:exec:bind``
        ``it:exec:file:add``
        ``it:exec:file:del``
        ``it:exec:file:read``
        ``it:exec:file:write``
        ``it:exec:reg:del``
        ``it:exec:reg:get``
        ``it:exec:reg:set``


  ``it:host:activity``
    Update the interface to add a ``sandbox:file`` property to record an
    initial sample from a sandbox environment.

- Changed primary Storm parser to a LALR compatible syntax to gain 80x speed
  up in parsing Storm queries
  (`#2649 <https://github.com/vertexproject/synapse/pull/2649>`_)
- Added service provisioning API to AHA service and associated tool
  ``synapse.tools.aha.provision.service`` and documentation to make
  it easy to bootstrap Synapse services using service discovery and
  SSL client-side certificates to identify service accounts.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added user provisioning API to AHA service and associated tools
  ``synapse.tools.aha.provision.user`` and ``synapse.tools.aha.enroll``
  to make it easy to bootstrap new users with SSL client-side certificates
  and AHA service discovery configuration.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added automatic mirror initialization logic to Synapse services to
  enable new mirrors to be initilized dynamically via AHA provisioning
  rather than from a pre-existing backup.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added ``handoff()`` API to Synapse services to allow mirrors to be
  gracefully promoted to leader.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added ``synapse.tools.promote`` to allow easy promotion of mirror to
  leader using the new ``handoff()`` API.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added ``aha:provision`` configuration to Synapse services to allow
  them to automatically provision and self-configure using AHA.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Adjusted Synapse service configuration preference to allow runtime settings
  to be stored in ``cell.yaml``.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added optional ``certhash`` parameter to telepath ``ssl://`` URLs to
  allow cert-pinning behavior and automatic trust of provisioning URLs.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added ``synapse.tools.moduser`` and ``synapse.tools.modrole`` commands
  to modernize and ease user/role management from within Synapse service
  docker containers.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Add ``$lib.jsonstor.cacheget()`` and ``lib.jsonstor.cacheset()`` functions
  in Storm to easily implement data caching in the JSONStor.
  (`#2662 <https://github.com/vertexproject/synapse/pull/2662>`_)
- Add a ``params`` option to ``$lib.inet.http.connect()`` to pass parameters
  when creating Websocket connections in Storm.
  (`#2664 <https://github.com/vertexproject/synapse/pull/2664>`_)

Bugfixes
--------
- Added ``getCellRunId()`` API to Synapse services to allow them to detect
  incorrect mirror configurations where they refer to themselves.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Ensure that CLI history files can be read and written upon
  starting interactive CLI tools.
  (`#2660 <https://github.com/vertexproject/synapse/pull/2660>`_)
- Assorted unit tests fixes to make tests more stable.
  (`#2656 <https://github.com/vertexproject/synapse/pull/2656>`_)
  (`#2665 <https://github.com/vertexproject/synapse/pull/2665>`_)
- Fix several uses of Python features which are formally deprecated
  and may be removed in future Python versions.
  (`#2668 <https://github.com/vertexproject/synapse/pull/2668>`_)

Improved Documentation
----------------------
- Added new Deployment Guide with step-by-step production ready deployment
  instructions
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Refactored Devops Guide to give task-oriented instructions on performing
  common devops tasks.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added new minimal Admin Guide as a place for documenting Cortex admin tasks.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Updated Getting Started to direct users to synapse-quickstart instructions.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Added ``easycert`` tool documentation.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Removed ``cmdr`` tool documentation to emphasize newer tools such as
  ``storm``.
  (`#2641 <https://github.com/vertexproject/synapse/pull/2641>`_)
- Update the list of available Advanced and Rapid Power-Ups.
  (`#2667 <https://github.com/vertexproject/synapse/pull/2667>`_)


v2.92.0 - 2022-04-28
====================

Features and Enhancements
-------------------------
- Update the allowed versions of the ``pyopenssl`` and ``pytz`` libraries.
  (`#2657 <https://github.com/vertexproject/synapse/pull/2657>`_)
  (`#2658 <https://github.com/vertexproject/synapse/pull/2658>`_)

Bugfixes
--------
- When setting ival properties, they are now properly merged with existing
  values. This only affected multi-layer views.
  (`#2655 <https://github.com/vertexproject/synapse/pull/2655>`_)


v2.91.1 - 2022-04-24
====================

Bugfixes
--------
- Fix a parsing regression in inet:url nodes related to unencoded "@" symbols
  in URLs.
  (`#2653 <https://github.com/vertexproject/synapse/pull/2653>`_)


v2.91.0 - 2022-04-21
====================

Features and Enhancements
-------------------------
- Updates to the ``inet`` and ``infotech`` models.
  (`#2634 <https://github.com/vertexproject/synapse/pull/2634>`_)
  (`#2644 <https://github.com/vertexproject/synapse/pull/2644>`_)
  (`#2652 <https://github.com/vertexproject/synapse/pull/2652>`_)

  ``inet:url``
    The ``inet:url`` type now recognizes various ``file:///`` values from
    RFC 8089.

  ``it:sec:cve``
    The ``it:sec:cve`` type now replaces various Unicode dashes with hyphen
    characters when norming. This allows a wider range of inputs to be
    accepted for the type. Scrape related APIs have also been updated to
    match on this wider range of inputs.

- The Cell now uses ``./backup`` as a default path for storing backups in, if
  the ``backup:dir`` path is not set.
  (`#2648 <https://github.com/vertexproject/synapse/pull/2648>`_)
- Add POSIX advisory locking around the Cell ``cell.guid`` file, to prevent
  multiple processes from attempting to start a Cell from the same directory.
  (`#2642 <https://github.com/vertexproject/synapse/pull/2642>`_)
- Change the default ``SLAB_COMMIT_WARN`` time from 5 seconds to 1 second, in
  order to quickly identify slow storage performance.
  (`#2630 <https://github.com/vertexproject/synapse/pull/2630>`_)
- Change the Cell ``iterBackupArchive`` and ``iterNewBackupArchive`` routines
  to always log exceptions they encounter, and report the final log message
  at the appropriate log level for success and failure.
  (`#2629 <https://github.com/vertexproject/synapse/pull/2629>`_)
- When normalizing the ``str`` types, when ``onespace`` is specified, we skip
  the ``strip`` behavior since it is redundant.
  (`#2635 <https://github.com/vertexproject/synapse/pull/2635>`_)
- Log exceptions raised by Cell creation in ``initFromArgv``. Catch
  ``lmdb.LockError`` when opening a LMDB database and re-raise an exception
  with a clear error message.
  (`#2638 <https://github.com/vertexproject/synapse/pull/2638>`_)
- Update schema validation for Storm packages to ensure that cmd arguments do
  not have excess fields in them.
  (`#2650 <https://github.com/vertexproject/synapse/pull/2650>`_)

Bugfixes
--------
- Adjust comma requirements for the JSON style list and dictionary expressions
  in Storm.
  (`#2636 <https://github.com/vertexproject/synapse/pull/2636>`_)
- Add Storm query logging in a code execution path where it was missing.
  (`#2647 <https://github.com/vertexproject/synapse/pull/2647>`_)
- Tuplify the output of ``synapse.tools.genpkg.loadPkgProto`` to ensure that
  Python list constructs ``[...]`` do not make it into Power-Up documentation.
  (`#2646 <https://github.com/vertexproject/synapse/pull/2646>`_)
- Fix an issue with heavy Stormtypes objects where caching was preventing
  some objects from behaving in a dynamic fashion as they were intended to.
  (`#2640 <https://github.com/vertexproject/synapse/pull/2640>`_)
- In norming ``int`` values, when something is outside of the minimum or
  maximum size of the type, we now include the string representation of the
  valu instead of the raw value.
  (`#2643 <https://github.com/vertexproject/synapse/pull/2643>`_)
- Raise a ``NotReady`` exception when a client attempts to resolve an
  ``aha://`` URL and there have not been any ``aha`` servers registered.
  (`#2645 <https://github.com/vertexproject/synapse/pull/2645>`_)

Improved Documentation
----------------------
- Update Storm command reference to add additional commands.
  (`#2633 <https://github.com/vertexproject/synapse/pull/2633>`_)
- Expand Stormtypes API documentation.
  (`#2637 <https://github.com/vertexproject/synapse/pull/2637>`_)
  (`#2639 <https://github.com/vertexproject/synapse/pull/2639>`_)


v2.90.0 - 2022-04-04
====================

Features and Enhancements
-------------------------
- Updates to the ``meta`` and ``infotech`` models.
  (`#2624 <https://github.com/vertexproject/synapse/pull/2624>`_)

  ``meta:rule``
    Add a new form for generic rules, which should be linked to
    the nodes they match with a ``matches`` light edge.

  ``meta:ruleset``
    Add ``:author``, ``:created``, and ``:updated`` secondary properties.

  ``it:app:yara:rule``
    Add ``:created`` and ``:updated`` secondary properties.

- Add a new Docker image ``vertexproject/synapse-jsonstor``.
  (`#2627 <https://github.com/vertexproject/synapse/pull/2627>`_)

- Allow passing a version requirement string to ``$lib.import()``.
  (`#2626 <https://github.com/vertexproject/synapse/pull/2626>`_)

Bugfixes
--------
- Fix an issue where using a regex lift on an array property could
  incorrectly yield the same node multiple times.
  (`#2625 <https://github.com/vertexproject/synapse/pull/2625>`_)

Improved Documentation
----------------------
- Update documentation regarding mirroring to be clearer about
  whether a given cell supports it.
  (`#2619 <https://github.com/vertexproject/synapse/pull/2619>`_)


v2.89.0 - 2022-03-31
====================

Features and Enhancements
-------------------------
- Update the ``meta`` model.
  (`#2621 <https://github.com/vertexproject/synapse/pull/2621>`_)

  ``meta:ruleset``
    Add a new form to denote the collection of a set of nodes representing
    rules, which should be linked together with a ``has`` light edge.

- Add additional filter options for the Storm ``merge`` command.
  (`#2615 <https://github.com/vertexproject/synapse/pull/2615>`_)
- Update the ``BadSyntaxError`` exception thrown when parsing Storm queries to
  additionally include line and column when available. Fix an issue
  where a ``!`` character being present in the exception text could truncate
  the output.
  (`#2618 <https://github.com/vertexproject/synapse/pull/2618>`_)


v2.88.0 - 2022-03-23
====================

Automatic Migrations
--------------------
- Re-normalize the ``geo:place:name``, ``crypto:currency:block:hash``, and
  ``crypto:currency:transaction:hash`` values to account for their modeling
  changes. Migrate ``crypto:currency:transaction:input`` and
  ``crypto:currency:transaction:output`` values to the secondary properties
  on the respective ``crypto:payment:input`` and ``crypto:payment:output``
  nodes to account for the modeling changes. Make ``geo:name`` nodes for
  ``geo:place:name`` secondary properties to account for the modeling changes.
  See :ref:`datamigration` for more information about automatic
  migrations.

Features and Enhancements
-------------------------
- Several updates for the ``crypto``, ``geospace``, ``inet``, and ``meta``
  models.
  (`#2594 <https://github.com/vertexproject/synapse/pull/2594>`_)
  (`#2608 <https://github.com/vertexproject/synapse/pull/2608>`_)
  (`#2611 <https://github.com/vertexproject/synapse/pull/2611>`_)
  (`#2616 <https://github.com/vertexproject/synapse/pull/2616>`_)

  ``crypto:payment:input``
    Add a secondary property ``:transaction`` to denote the transaction
    for the payment.

  ``crypto:payment:output``
    Add a secondary property ``:transaction`` to denote the transaction
    for the payment.

  ``crypto:currency:block``
    Change the type of the ``:hash`` property from a ``0x`` prefixed ``str``
    to a ``hex`` type.

  ``crypto:currency:transaction``
    Change the type of the ``:hash`` property from a ``0x`` prefixed ``str``
    to a ``hex`` type.
    Deprecate the ``:inputs`` and ``:outputs`` secondary properties.

  ``geo:place``
    Change the type of the ``:name`` secondary property to ``geo:name``.

  ``inet:web:channel``
    Add a new form to denote a channel within a web service or instance.

  ``inet:web:instance``
    Add a new form to track an instance of a web service, such as a channel
    based messaging platform.

  ``inet:web:mesg``
    Add ``:channel``, ``:place``, and ``:place:name`` secondary properties.

  ``inet:web:post``
    Add ``:channel`` and ``:place:name`` secondary properties.

  ``meta:event``
    Add a new form to denote an analytically relevant event in a curated
    timeline.

  ``meta:event:taxonomy``
    Add a new form to represent a taxonomy of ``meta:event:type`` values.

  ``meta:timeline``
    Add a new form to denote a curated timeline of analytically relevant
    events.

  ``meta:timeline:taxonomy``
    Add a new form to represent a taxonomy of ``meta:timeline:type`` values.

- Add support for ``$lib.len()`` to count the length of emitter or generator
  functions.
  (`#2603 <https://github.com/vertexproject/synapse/pull/2603>`_)
- Add support for scrape APIs to handle text that has been defanged with
  ``\\.`` characters.
  (`#2605 <https://github.com/vertexproject/synapse/pull/2605>`_)
- Add a ``nomerge`` option to View objects that can be set to prevent merging
  a long lived fork.
  (`#2614 <https://github.com/vertexproject/synapse/pull/2614>`_)
- Add ``liftByProp()`` and ``liftByTag()`` methods to the Stormtypes
  ``layer`` objects. These allow lifting of nodes based on data stored
  in a specific layer.
  (`#2613 <https://github.com/vertexproject/synapse/pull/2613>`_)
- Expand Synapse requirements to include updated versions of the ``pygments``
  library.
  (`#2602 <https://github.com/vertexproject/synapse/pull/2602>`_)

Improved Documentation
----------------------
- Fix the example regular expressions used in the ``$lib.scrape.genMatches()``
  Storm library API examples.
  (`#2606 <https://github.com/vertexproject/synapse/pull/2606>`_)


v2.87.0 - 2022-03-18
====================

Features and Enhancements
-------------------------
- Several updates for the ``inet`` and ``meta`` models.
  (`#2589 <https://github.com/vertexproject/synapse/pull/2589>`_)
  (`#2592 <https://github.com/vertexproject/synapse/pull/2592>`_)

  ``inet:ssl:jarmhash``
    Add a form to record JARM hashes.

  ``inet:ssl:jarmsample``
    Add a form to record JARM hashes being present on a server.

  ``meta:note``
    Add a form for recording free text notes.

- Update the Synapse docker containers to be built from a Ubuntu based image,
  instead of a Debian based image.
  (`#2596 <https://github.com/vertexproject/synapse/pull/2596>`_)
- Add a Storm ``note.add`` command that creates a ``meta:note`` node to record
  freeform text, and links that node to the input nodes using a ``about`` light
  edge.
  (`#2592 <https://github.com/vertexproject/synapse/pull/2592>`_)
- Support non-writeable or non-existing directories within Synapse ``certdir``
  directories.
  (`#2590 <https://github.com/vertexproject/synapse/pull/2590>`_)
- Add an optional ``tick`` argument to the
  ``synapse.lib.lmdbslab.Hist.add()`` function. This is exposed internally
  for Axon implementations to use.
  (`#2593 <https://github.com/vertexproject/synapse/pull/2593>`_)
- Expand Synapse requirements to include updated versions of the
  ``pycryptome``, ``pygments``, ``scalecodec`` and ``xxhash`` modules.
  (`#2598 <https://github.com/vertexproject/synapse/pull/2598>`_)

Bugfixes
--------
- Fix an issue where the StormDmon stop/start status was not properly being
  updated in the runtime object, despite being properly updated in the Hive.
  (`#2598 <https://github.com/vertexproject/synapse/pull/2598>`_)
- Calls to ``addUnivProp()`` APIs when the universal property name already
  exists now raise a ``DupPropName`` exception.
  (`#2601 <https://github.com/vertexproject/synapse/pull/2601>`_)


v2.86.0 - 2022-03-09
====================

Automatic Migrations
--------------------
- Migrate secondary properties in Cortex nodes which use ``hugenum`` type to
  account for updated ranges. See :ref:`datamigration` for more
  information about automatic migrations.

Features and Enhancements
-------------------------
- Extend the number of decimal places the ``hugenum`` type can store to 24
  places, with a new maximum value of 730750818665451459101842.
  (`#2584 <https://github.com/vertexproject/synapse/pull/2584>`_)
  (`#2586 <https://github.com/vertexproject/synapse/pull/2586>`_)
- Update ``fastjsonschema`` to version ``2.15.3``.
  (`#2581 <https://github.com/vertexproject/synapse/pull/2581>`_)

Bugfixes
--------
- Add missing read-only flags to secondary properties of Comp type forms which
  were computed from the primary property of the node. This includes the
  following:
  (`#2587 <https://github.com/vertexproject/synapse/pull/2587>`_)

    - ``crypto:currency:address:coin``
    - ``crypto:currency:address:iden``
    - ``crypto:currency:block:coin``
    - ``crypto:currency:block:offset``
    - ``crypto:currency:client:coinaddr``
    - ``crypto:currency:client:inetaddr``
    - ``crypto:currency:smart:token:contract``
    - ``crypto:currency:smart:token:tokenid``
    - ``crypto:x509:revoked:crl``
    - ``crypto:x509:revoked:cert``
    - ``crypto:x509:signedfile:cert``
    - ``crypto:x509:signedfile:file``
    - ``econ:acquired:item``
    - ``econ:acquired:purchase``
    - ``inet:dns:query:client``
    - ``inet:dns:query:name``
    - ``inet:dns:query:type``
    - ``inet:whois:contact:type``
    - ``inet:wifi:ap:bssid``
    - ``inet:wifi:ap:ssid``
    - ``mat:itemimage:file``
    - ``mat:itemimage:item``
    - ``mat:specimage:file``
    - ``mat:specimage:spec``
    - ``ou:id:number:type``
    - ``ou:id:number:value``
    - ``ou:hasgoal:goal``
    - ``ou:hasgoal:org``
    - ``tel:mob:cell:carrier``
    - ``tel:mob:cell:carrier:mcc``
    - ``tel:mob:cell:carrier:mnc``
    - ``tel:mob:cell:cid``
    - ``tel:mob:cell:lac``

- Fix an issue where Layers configured with writeback mirrors did not properly
  handle results which did not have any changes.
  (`#2583 <https://github.com/vertexproject/synapse/pull/2583>`_)

Improved Documentation
----------------------
- Fix spelling issues in documentation and API docstrings.
  (`#2582 <https://github.com/vertexproject/synapse/pull/2582>`_)
  (`#2585 <https://github.com/vertexproject/synapse/pull/2585>`_)


v2.85.1 - 2022-03-03
====================

Bugfixes
--------
- Fix a permission enforcement issue in autoadd mode that allowed
  users with view read permissions to add automatically detected and
  validated nodes but make no further edits.
  (`#2579 <https://github.com/vertexproject/synapse/pull/2579>`_)
- Log errors encountered in the Layer mirror loop which don't have a
  local caller waiting on the change.
  (`#2580 <https://github.com/vertexproject/synapse/pull/2580>`_)


v2.85.0 - 2022-03-03
====================

Features and Enhancements
-------------------------

- Several updates for the ``crypto``, ``geo``, ``inet``, ``it``, ``ps`` and
  ``risk`` models.
  (`#2570 <https://github.com/vertexproject/synapse/pull/2570>`_)
  (`#2573 <https://github.com/vertexproject/synapse/pull/2573>`_)
  (`#2574 <https://github.com/vertexproject/synapse/pull/2574>`_)

  ``crypto:payment:input``
    Add a new form to record payments made into a transaction.

  ``crypto:payment:output``
    Add a new form to record payments receieved from a transaction.

  ``crypto:currency:transaction``
    Add ``inputs`` and ``outputs`` array secondary properties to record inputs
    and outputs for a given transaction.

  ``geo:name``
    Add a new form representing an unstructured place name or address.

  ``geo:place``
    Add a ``names`` secondary property which is an array of ``geo:name``
    values.

  ``inet:flow``
    Add ``dst:txcount``, ``src:txcount``, ``tot:txcount`` and ``tot:txbytes``
    secondary properties.

  ``it:exec:proc``
    Add an ``account`` secondary property as a ``it:account`` type. Mark the
    ``user`` secondary property as deprecated.

  ``ps:contact``
    Add ``birth:place``, ``birth:place:loc``, ``birth:place:name``,
    ``death:place``, ``death:place:loc`` and ``death:place:name`` secondary
    properties.

  ``risk:compromise``
    Add a ``theft:price`` secondary property to represent value of stolen
    assets.

- Embed Cron, StormDmon, and Trigger iden values and automation types into
  the Storm runtime when those automations are run. This information is
  populated in a dictionary variable named ``$auto``.
  (`#2565 <https://github.com/vertexproject/synapse/pull/2565>`_)
- Add ``$lib.crypto.coin.ethereum.eip55()`` to convert an Ethereum address to a
  checksummed address.
  (`#2577 <https://github.com/vertexproject/synapse/pull/2577>`_)
- Add a ``default`` argument to the  ``$lib.user.allowed()`` and ``allowed()``
  method on ``user`` StormType.
  (`#2570 <https://github.com/vertexproject/synapse/pull/2570>`_)
- Add a ``inaugural`` configuration key to the base ``Cell`` class. This can
  currently be used to bootstrap roles, permissions, and users in a Cell upon
  the first time it is started.
  (`#2570 <https://github.com/vertexproject/synapse/pull/2570>`_)
- De-duplicate nodes when running the Storm ``lookup`` mode to lift nodes.
  (`#2567 <https://github.com/vertexproject/synapse/pull/2567>`_)
- Add a test helper that can be used to isolate the
  ``synapse.lib.certdir.certdir`` singleton behavior via context manager.
  (`#2564 <https://github.com/vertexproject/synapse/pull/2564>`_)

Bugfixes
--------
- Calls to ``addFormProp()`` APIs when the property name already exists now
  raise a ``DupPropName`` exception.
  (`#2566 <https://github.com/vertexproject/synapse/pull/2566>`_)
- Do not allow Storm ``macro``'s to be created that have names greater than
  492 characters in length.
  (`#2569 <https://github.com/vertexproject/synapse/pull/2569>`_)
- Fix a bug in the scrape logic for Ethereum where the regular expression
  matched on ``0X`` prefixed strings but the validation logic did not account
  for that uppercase character.
  (`#2575 <https://github.com/vertexproject/synapse/pull/2575>`_)

Improved Documentation
----------------------
- Add documentation for the ``$auto`` variable embedded into the Cron,
  StormDmon, and Trigger automations. Add documentation for variables
  representing the form, node value, properties and tags which are responsible
  for Triggers running.
  (`#2565 <https://github.com/vertexproject/synapse/pull/2565>`_)


v2.84.0 - 2022-02-22
====================

Features and Enhancements
-------------------------
- Add ``$lib.time.toUTC()`` to adjust a local epoch milliseconds time to
  UTC.
  (`#2550 <https://github.com/vertexproject/synapse/pull/2550>`_)
- Add a optional ``timeout`` argument to ``$lib.service.wait()``. The function
  now returns ``$lib.true`` if the service is available, or ``$lib.false`` if
  the service does not become available during the timeout window.
  (`#2561 <https://github.com/vertexproject/synapse/pull/2561>`_)
- Update the ``Layer.verify()`` routines to add verification of tagprop and
  array indexes in layers.  These routines are in a beta status and are
  subject to change.
  (`#2560 <https://github.com/vertexproject/synapse/pull/2560>`_)
- Update the Cortex's connection to a remote Axon to use a Telepath Client.
  (`#2559 <https://github.com/vertexproject/synapse/pull/2559>`_)


v2.83.0 - 2022-02-17
====================

Features and Enhancements
-------------------------
- Add ``:ip:proto`` and ``:ip:tcp:flags`` properties to the ``inet:flow``
  form.
  (`#2554 <https://github.com/vertexproject/synapse/pull/2554>`_)
- Add ``$lib.log.debug()``, ``$lib.log.info()``, ``$lib.log.warning()``, and
  ``$lib.log.error()`` Stormtypes APIs. These allow a user to send log
  messages to the Cortex logging output directly.
- Update the ``synapse.tools.genpkg`` tool to support using files with the
  ``.storm`` extension. This is enabled by adding the following option to a
  Storm package definition.
  (`#2555 <https://github.com/vertexproject/synapse/pull/2555>`_)

  ::

    genopts:
      dotstorm: true


- Add form and prop values to ``BadTypeValu`` exceptions when raised during
  node edit generation.
  (`#2552 <https://github.com/vertexproject/synapse/pull/2552>`_)

Bugfixes
--------
- Correct a race condition in the ``CoreApi.syncLayersEvents`` and
  ``CoreApi.syncIndexEvents`` APIs.
  (`#2553 <https://github.com/vertexproject/synapse/pull/2553>`_)

Improved Documentation
----------------------
- Remove outdated documentation related to making ``CoreModule`` classes.
  (`#2556 <https://github.com/vertexproject/synapse/pull/2556>`_)


v2.82.1 - 2022-02-11
====================

Bugfixes
--------
- Re-order node edit validation to only check read-only status of properties
  if the value would change.
  (`#2547 <https://github.com/vertexproject/synapse/pull/2547>`_)
- Raise the correct exception when parsing invalid time values, like
  ``0000-00-00``.
  (`#2548 <https://github.com/vertexproject/synapse/pull/2548>`_)
- Disable node caching for ``StormDmon`` runtimes to avoid potential
  cache coherency issues.
  (`#2549 <https://github.com/vertexproject/synapse/pull/2549>`_)


v2.82.0 - 2022-02-10
====================

Features and Enhancements
-------------------------
- Add an ``addNode()`` API to the Stormtypes ``view`` object. This
  allows the programmatic creation of a node with properties being set in
  a transactional fashion.
  (`#2540 <https://github.com/vertexproject/synapse/pull/2540>`_)
- Add support to Storm for creating JSON style list and dictionary objects.
  (`#2544 <https://github.com/vertexproject/synapse/pull/2544>`_)
- The ``AhaCell`` now bootstraps TLS CA certificates for the configured
  ``aha:network`` value, a host certificate for the ``aha:name`` value,
  and a user certificate for the ``aha:admin`` value.
  (`#2542 <https://github.com/vertexproject/synapse/pull/2542>`_)
- Add ``mesg`` arguments to all exceptions raised in ``synapse.lib.certdir``.
  (`#2546 <https://github.com/vertexproject/synapse/pull/2546>`_)

Improved Documentation
----------------------
- Fix some missing and incorrect docstrings for Stormtypes.
  (`#2545 <https://github.com/vertexproject/synapse/pull/2545>`_)

Deprecations
------------
- Telepath APIs and Storm commands related to ``splices`` have been marked as
  deprecated.
  (`#2541 <https://github.com/vertexproject/synapse/pull/2541>`_)


v2.81.0 - 2022-01-31
====================

Features and Enhancements
-------------------------
- The ``it:sec:cpe`` now recognizes CPE 2.2 strings during type normalization.
  CPE 2.2 strings will be upcast to CPE 2.3 and the 2.2 string will be added
  to the ``:v2_2`` secondary property of ``it:sec:cpe``. The Storm hotfix
  ``$lib.cell.hotFixesApply()`` can be used to populate the ``:v2_2``
  property on existing ``it:sec:cpe`` nodes where it is not set.
  (`#2537 <https://github.com/vertexproject/synapse/pull/2537>`_)
  (`#2538 <https://github.com/vertexproject/synapse/pull/2538>`_)
  (`#2539 <https://github.com/vertexproject/synapse/pull/2539>`_)
- Setting properties on nodes may now take a fast path if the normed property
  has no subs, no autoadds and is not a locked property.
  (`#2539 <https://github.com/vertexproject/synapse/pull/2539>`_)

Bugfixes
--------
- Fix an issue with ``Ival`` ``norm()`` routines when norming a tuple or list
  of values. The max value returned previously could have exceeded the value
  of the future marker ``?``, which would have been then caused an a
  ``BadTypeValu`` exception during node edit construction. This is  is now
  caught during the initial ``norm()`` call.
  (`#2539 <https://github.com/vertexproject/synapse/pull/2539>`_)


v2.80.1 - 2022-01-26
====================

Bugfixes
--------
- The embedded JsonStor added to the Cortex in ``v2.80.0`` needed to have a
  stable iden for the Cell and and auth subsystem. This has been added.
  (`#2536 <https://github.com/vertexproject/synapse/pull/2536>`_)


v2.80.0 - 2022-01-25
====================

Features and Enhancements
-------------------------
- Add a triple quoted string ``'''`` syntax to Storm for defining multiline
  strings.
  (`#2530 <https://github.com/vertexproject/synapse/pull/2530>`_)
- Add a JSONStor to the Cortex, and expose that in Storm for storing user
  related content.
  (`#2530 <https://github.com/vertexproject/synapse/pull/2530>`_)
  (`#2513 <https://github.com/vertexproject/synapse/pull/2513>`_)
- Add durable user notifications to Storm that can be used to send and receive
  messages between users.
  (`#2513 <https://github.com/vertexproject/synapse/pull/2513>`_)
- Add a ``leaf`` argument to ``$node.tags()`` that causes the function to only
  return the leaf tags.
  (`#2535 <https://github.com/vertexproject/synapse/pull/2535>`_)
- Add an error message in the default help text in pure Storm commands when a
  user provides additional arguments or switches, in addition to the
  ``--help`` switch.
  (`#2533 <https://github.com/vertexproject/synapse/pull/2533>`_)
- Update ``synapse.tools.genpkg`` to automatically bundle Optic workflows from
  files on disk.
  (`#2531 <https://github.com/vertexproject/synapse/pull/2531>`_)
- Expand Synapse requirements to include updated versions of the
  ``packaging``, ``pycryptome`` and ``scalecodec`` modules.
  (`#2534 <https://github.com/vertexproject/synapse/pull/2534>`_)

Bugfixes
--------
- Add a missing ``tostr()`` call to the Storm ``background`` query argument.
  (`#2532 <https://github.com/vertexproject/synapse/pull/2532>`_)


v2.79.0 - 2022-01-18
====================

Features and Enhancements
-------------------------
- Add ``$lib.scrape.ndefs()`` and ``$lib.scrape.context()`` to scrape text.
  The ``ndefs()`` API yields a unique set of node form and value pairs,
  while the ``context()`` API yields node form, value, and context information
  for all matches in the text.
  (`#2508 <https://github.com/vertexproject/synapse/pull/2508>`_)
- Add ``:name`` and ``:desc`` properties to the ``it:prod:softver`` form.
  (`#2528 <https://github.com/vertexproject/synapse/pull/2528>`_)
- Update the ``Layer.verify()`` routines to reduce false errors related to
  array types. The method now takes a dictionary of configuration options.
  These routines are in a beta status and are subject to change.
  (`#2527 <https://github.com/vertexproject/synapse/pull/2527>`_)
- Allow setting a View's parent if does not have an existing parent View
  and only has a single layer.
  (`#2515 <https://github.com/vertexproject/synapse/pull/2515>`_)
- Add ``hxxp[:\\]`` and ``hxxps[:\\]`` to the list of known defanging
  strategies which are identified and replaced during text scraping.
  (`#2526 <https://github.com/vertexproject/synapse/pull/2526>`_)
- Expand Synapse requirements to include updated versions of the
  ``typing-extensions`` module.
  (`#2525 <https://github.com/vertexproject/synapse/pull/2525>`_)

Bugfixes
--------
- Storm module interfaces now populate ``modconf`` data when loaded.
  (`#2508 <https://github.com/vertexproject/synapse/pull/2508>`_)
- Fix a missing keyword argument from the ``AxonApi.wput()`` method.
  (`#2527 <https://github.com/vertexproject/synapse/pull/2527>`_)

Deprecations
------------
- The ``$lib.scrape()`` function has been deprecated in favor the new
  ``$lib.scrape`` library functions.
  (`#2508 <https://github.com/vertexproject/synapse/pull/2508>`_)


v2.78.0 - 2022-01-14
====================

Automatic Migrations
--------------------
- Migrate Cortex nodes which may have been skipped in an earlier migration due
  to missing tagprop indexes. See :ref:`datamigration` for more
  information about automatic migrations.

Features and Enhancements
-------------------------
- Expand Synapse requirements to include updated versions of the ``base58``,
  ``cbor2``, ``lmdb``, ``pycryptodome``, ``PyYAML``, ``xxhash``.
  (`#2520 <https://github.com/vertexproject/synapse/pull/2520>`_)

Bugfixes
--------
- Fix an issue with the Tagprop migration from ``v2.42.0`` where a missing
  index could have resulted in Layer storage nodes not being updated.
  (`#2522 <https://github.com/vertexproject/synapse/pull/2522>`_)
  (`#2523 <https://github.com/vertexproject/synapse/pull/2523>`_)
- Fix an issue with ``synapse.lib.platforms.linux.getTotalMemory()`` when
  using a process segregated with the Linux cgroups2 API.
  (`#2517 <https://github.com/vertexproject/synapse/pull/2517>`_)

Improved Documentation
----------------------
- Add devops instructions related to automatic data migrations for Synapse
  components.
  (`#2523 <https://github.com/vertexproject/synapse/pull/2523>`_)
- Update the model deprecation documentation for the ``it:host:model`` and
  ``it:host:make`` properties.
  (`#2521 <https://github.com/vertexproject/synapse/pull/2521>`_)


v2.77.0 - 2022-01-07
====================

Features and Enhancements
-------------------------
- Add Mach-O metadata support the file model. This includes the following
  new forms: ``file:mime:macho:loadcmd``, ``file:mime:macho:version``,
  ``file:mime:macho:uuid``, ``file:mime:macho:segment``, and
  ``file:mime:macho:section``.
  (`#2503 <https://github.com/vertexproject/synapse/pull/2503>`_)
- Add ``it:screenshot``, ``it:prod:hardware``, ``it:prod:component``,
  ``it:prod:hardwaretype``, and ``risk:mitigation`` forms to the model. Add
  ``:hardware`` property to ``risk:hasvuln`` form. Add ``:hardware`` property
  to ``it:host`` form. The ``:manu`` and ``:model`` secondary properties on
  ``it:host`` have been deprecated.
  (`#2514 <https://github.com/vertexproject/synapse/pull/2514>`_)
- The ``guid`` type now strips hyphen (``-``) characters when doing norm. This
  allows users to provide external UUID / GUID strings for use.
  (`#2514 <https://github.com/vertexproject/synapse/pull/2514>`_)
- Add a ``Axon.postfiles()`` to allow POSTing files as multi-part form encoded
  files over HTTP. This is also exposed through the ``fields`` argument on the
  Storm ``$lib.inet.http.post()`` and ``$lib.inet:http:request`` APIs.
  (`#2516 <https://github.com/vertexproject/synapse/pull/2516>`_)
- Add ``.yu`` ccTLD to the list of TLDs identified by the Synapse scrape
  functionality.
  (`#2518 <https://github.com/vertexproject/synapse/pull/2518>`_)
- Add ``mesg`` arguments to all instances of ``NoSuchProp`` exceptions.
  (`#2519 <https://github.com/vertexproject/synapse/pull/2519>`_)


v2.76.0 - 2022-01-04
====================

Features and Enhancements
-------------------------
- Add ``emit`` and ``stop`` keywords to Storm. The ``emit`` keyword is used
  in functions to make them behave as generators, which can yield arbitrary
  values. The ``stop`` keyword can be used to prematurely end a function which
  is ``emit``'ing values.
  (`#2475 <https://github.com/vertexproject/synapse/pull/2475>`_)
- Add Storm Module Interfaces. This allows Storm Package authors to define
  common module interfaces, so that multiple modules can implement the API
  convention to provide a consistent set of data across multiple Storm
  modules. A ``search`` convention is added to the Cortex, which will be used
  in ``lookup`` mode when the ``storm:interface:search`` configuration option
  is set.
  (`#2475 <https://github.com/vertexproject/synapse/pull/2475>`_)
- Storm queries in ``lookup`` mode now fire ``look:miss`` events into the
  Storm message stream when the lookup value contains a valid node value,
  but the node is not present in the current View.
  (`#2475 <https://github.com/vertexproject/synapse/pull/2475>`_)
- Add a ``:host`` secondary property to ``risk:hasvuln`` form to record
  ``it:host`` instances which have a vulnerability.
  (`#2512 <https://github.com/vertexproject/synapse/pull/2512>`_)
- Add ``synapse.lib.scrape`` support for identifying ``it:sec:cve`` values.
  (`#2509 <https://github.com/vertexproject/synapse/pull/2509>`_)

Bugfixes
--------
- Fix an ``IndexError`` that can occur during ``Layer.verify()`` routines.
  These routines are in a beta status and are subject to change.
  (`#2507 <https://github.com/vertexproject/synapse/pull/2507>`_)
- Ensure that parameter and header arguments passed to Storm
  ``$lib.inet.http`` functions are cast into strings values.
  (`#2510 <https://github.com/vertexproject/synapse/pull/2510>`_)


v2.75.0 - 2021-12-16
====================

This release contains an automatic data migration that may cause additional
startup time on the first boot. This is done to unique array properties which
previously were not uniqued. Deployments with startup or liveliness probes
should have those disabled while this upgrade is performed to prevent
accidental termination of the Cortex process. Please ensure you have a tested
backup available before applying this update.

Features and Enhancements
-------------------------

- Update the following array properties to be unique sets, and add a data
  model migration to update the data at rest:
  (`#2469 <https://github.com/vertexproject/synapse/pull/2469>`_)

    - ``biz:rfp:requirements``
    - ``crypto:x509:cert:ext:sans``
    - ``crypto:x509:cert:ext:crls``
    - ``crypto:x509:cert:identities:fqdns``
    - ``crypto:x509:cert:identities:emails``
    - ``crypto:x509:cert:identities:ipv4s``
    - ``crypto:x509:cert:identities:ipv6s``
    - ``crypto:x509:cert:identities:urls``
    - ``crypto:x509:cert:crl:urls``
    - ``inet:whois:iprec:contacts``
    - ``inet:whois:iprec:links``
    - ``inet:whois:ipcontact:roles``
    - ``inet:whois:ipcontact:links``
    - ``inet:whois:ipcontact:contacts``
    - ``it:account:groups``
    - ``it:group:groups``
    - ``it:reveng:function:impcalls``
    - ``it:reveng:filefunc:funccalls``
    - ``it:sec:cve:references``
    - ``risk:vuln:cwes``
    - ``tel:txtmesg:recipients``

- Add Layer index verification routines, to compare the Layer indices against
  the stored data for Nodes. This is exposed via the ``.verify()`` API on the
  Stormtypes ``layer`` object.
  These routines are in a beta status and are subject to change.
  (`#2488 <https://github.com/vertexproject/synapse/pull/2488>`_)
- The ``.json()`` API on ``inet:http:resp`` now raises a
  ``s_exc.BadJsonText`` exception, which can be caught with the Storm
  ``try ... catch`` syntax.
  (`#2500 <https://github.com/vertexproject/synapse/pull/2500>`_)
- Add ``$lib.inet.ipv6.expand()`` to expand an IPv6 address to its long form.
  (`#2502 <https://github.com/vertexproject/synapse/pull/2502>`_)
- Add ``hasPathObj()``, ``copyPathObj()`` and ``copyPathObjs()`` APIs to the
  ``JsonStor``.
  (`#2438 <https://github.com/vertexproject/synapse/pull/2438>`_)
- Allow setting a custom title when making documentation for Cell
  ``confdefs`` with the ``synapse.tools.autodoc`` tool.
  (`#2504 <https://github.com/vertexproject/synapse/pull/2504>`_)
- Update the minimum version of the ``aiohttp`` library to ``v3.8.1``.
  (`#2495 <https://github.com/vertexproject/synapse/pull/2495>`_)

Improved Documentation
----------------------
- Add content previously hosted at ``commercial.docs.vertex.link`` to the
  mainline Synapse documentation. This includes some devops information
  related to orchestration, information about Advanced and Rapid Power-Ups,
  information about the Synapse User Interface, as well as some support
  information.
  (`#2498 <https://github.com/vertexproject/synapse/pull/2498>`_)
  (`#2499 <https://github.com/vertexproject/synapse/pull/2499>`_)
  (`#2501 <https://github.com/vertexproject/synapse/pull/2501>`_)
- Add ``Synapse-Malshare`` and ``Synapse-TeamCymru`` Rapid Power-Ups to the
  list of available Rapid Power-Ups.
  (`#2506 <https://github.com/vertexproject/synapse/pull/2506>`_)
- Document the ``jsonlines`` option for the ``api/v1/storm`` and
  ``api/v1/storm/nodes`` HTTP APIs.
  (`#2505 <https://github.com/vertexproject/synapse/pull/2505>`_)


v2.74.0 - 2021-12-08
====================

Features and Enhancements
-------------------------
- Add ``.onion`` and ``.bit`` to the TLD list used for scraping text. Update
  the TLD list from the latest IANA TLD list.
  (`#2483 <https://github.com/vertexproject/synapse/pull/2483>`_)
  (`#2497 <https://github.com/vertexproject/synapse/pull/2497>`_)
- Add support for writeback mirroring of layers.
  (`#2463 <https://github.com/vertexproject/synapse/pull/2463>`_)
  (`#2489 <https://github.com/vertexproject/synapse/pull/2489>`_)
- Add ``$lib.scrape()`` Stormtypes API. This can be used to do programmatic
  scraping of text using the same regular expressions used by the Storm
  ``scrape`` command and the ``synapse.lib.scrape`` APIs.
  (`#2486 <https://github.com/vertexproject/synapse/pull/2486>`_)
- Add a ``jsonlines`` output mode to Cortex streaming HTTP endpoints.
  (`#2493 <https://github.com/vertexproject/synapse/pull/2493>`_)
- Add a ``--raw`` argument to the Storm ``pkg.load`` command. This loads the
  raw JSON response as a Storm package.
  (`#2491 <https://github.com/vertexproject/synapse/pull/2491>`_)
- Add a ``blocked`` enum to the ``proj:ticket:status`` property to represent a
  blocked ticket.
  (`#2490 <https://github.com/vertexproject/synapse/pull/2490>`_)

Bugfixes
--------
- Fix a behavior with ``$path`` losing variables in pure Storm command
  execution.
  (`#2492 <https://github.com/vertexproject/synapse/pull/2492>`_)

Improved Documentation
----------------------
- Update the description of the Storm ``scrape`` command.
  (`#2494 <https://github.com/vertexproject/synapse/pull/2494>`_)


v2.73.0 - 2021-12-02
====================

Features and Enhancements
-------------------------
- Add a Storm ``runas`` command. This allows admin users to execute Storm
  commands as other users.
  (`#2473 <https://github.com/vertexproject/synapse/pull/2473>`_)
- Add a Storm ``intersect`` command. This command produces the intersection
  of nodes emitted by running a Storm query over all inbound nodes to the
  ``intersect`` command.
  (`#2480 <https://github.com/vertexproject/synapse/pull/2480>`_)
- Add ``wait`` and ``timeout`` parameters to the ``Axon.hashes()`` and
  ``$lib.axon.list()`` APIs.
  (`#2481 <https://github.com/vertexproject/synapse/pull/2481>`_)
- Add a ``readonly`` flag to ``synapse.tools.genpkg.loadPkgProto()`` and
  ``synapse.tools.genpkg.tryLoadPkgProto()`` APIs. If set to ``True`` this
  will open files in read only mode.
  (`#2485 <https://github.com/vertexproject/synapse/pull/2485>`_)
- Allow Storm Prim objects to be capable of directly yielding nodes when used
  in ``yield`` statements.
  (`#2479 <https://github.com/vertexproject/synapse/pull/2479>`_)
- Update the StormDmon subsystem to add debug log information about state
  changes, as well as additional data for structured logging output.
  (`#2455 <https://github.com/vertexproject/synapse/pull/2455>`_)

Bugfixes
--------
- Catch a fatal application error that can occur in the Cortex if the forked
  process pool becomes unusable. Previously this would cause the Cortex to
  appear unresponsive for executing Storm queries; now this causes the Cortex
  to shut down gracefully.
  (`#2472 <https://github.com/vertexproject/synapse/pull/2472>`_)
- Fix a Storm path variable scoping issue where variables were improperly
  scoped when nodes were passed into pure Storm commands.
  (`#2459 <https://github.com/vertexproject/synapse/pull/2459>`_)


v2.72.0 - 2021-11-23
====================

Features and Enhancements
-------------------------
- Update the cron subsystem logs to include the cron name, as well as adding
  additional data for structured logging output.
  (`#2477 <https://github.com/vertexproject/synapse/pull/2477>`_)
- Add a ``sort_keys`` argument to the ``$lib.yaml.save()`` Stormtype API.
  (`#2474 <https://github.com/vertexproject/synapse/pull/2474>`_)

Bugfixes
--------
- Update the ``asyncio-socks`` version to a version which has a pinned version
  range for the ``python-socks`` dependency.
  (`#2478 <https://github.com/vertexproject/synapse/pull/2478>`_)


v2.71.1 - 2021-11-22
====================

Bugfixes
--------
- Update the ``PyOpenSSL`` version to ``21.0.0`` and pin a range of modern
  versions of the ``cryptography`` which have stronger API compatibility.
  This resolves an API compatibility issue with the two libraries which
  affected SSL certificate generation.
  (`#2476 <https://github.com/vertexproject/synapse/pull/2476>`_)


v2.71.0 - 2021-11-19
====================

Features and Enhancements
-------------------------
- Add support for asynchronous triggers. This mode of trigger operation queues
  up the trigger event in the View for eventual processing.
  (`#2464 <https://github.com/vertexproject/synapse/pull/2464>`_)
- Update the crypto model to add a ``crypto:smart:token`` form to represent a
  token managed by a smart contract.
  (`#2462 <https://github.com/vertexproject/synapse/pull/2462>`_)
- Add ``$lib.axon.readlines()`` and ``$lib.axon.jsonlines()`` to Stormtypes.
  (`#2468 <https://github.com/vertexproject/synapse/pull/2468>`_)
- Add the Storm ``mode`` to the structured log output of a Cortex executing a
  Storm query.
  (`#2466 <https://github.com/vertexproject/synapse/pull/2466>`_)

Bugfixes
--------
- Fix an error when converting Lark exceptions to Synapse ``BadSyntaxError``.
  (`#2471 <https://github.com/vertexproject/synapse/pull/2471>`_)

Improved Documentation
----------------------
- Revise the Synapse documentation layout.
  (`#2460 <https://github.com/vertexproject/synapse/pull/2460>`_)
- Update type specific behavior documentation for ``time`` types, including
  the recently added wildcard time syntax.
  (`#2467 <https://github.com/vertexproject/synapse/pull/2467>`_)
- Sort the Storm Type documentation by name.
  (`#2465 <https://github.com/vertexproject/synapse/pull/2465>`_)
- Add 404 handler pages to our documentation.
  (`#2461 <https://github.com/vertexproject/synapse/pull/2461>`_)
  (`#2470 <https://github.com/vertexproject/synapse/pull/2470>`_)

Deprecations
------------
- Remove ``$path.trace()`` objects.
  (`#2445 <https://github.com/vertexproject/synapse/pull/2445>`_)


v2.70.1 - 2021-11-08
====================

Bugfixes
--------
- Fix an issue where ``$path.meta`` data was not being properly serialized
  when heavy Stormtype objects were set on the ``$path.meta`` dictionary.
  (`#2456 <https://github.com/vertexproject/synapse/pull/2456>`_)
- Fix an issue with Stormtypes ``Str.encode()`` and ``Bytes.decode()`` methods
  when handling potentially malformed Unicode string data.
  (`#2457 <https://github.com/vertexproject/synapse/pull/2457>`_)

Improved Documentation
----------------------
- Update the Storm Control Flow documentation with additional examples.
  (`#2443 <https://github.com/vertexproject/synapse/pull/2443>`_)


v2.70.0 - 2021-11-03
====================

Features and Enhancements
-------------------------
- Add ``:dst:handshake`` and ``src:handshake`` properties to ``inet:flow`` to
  record text representations of the handshake strings of a given connection.
  (`#2451 <https://github.com/vertexproject/synapse/pull/2451>`_)
- Add a ``proj:attachment`` form to the ``project`` model to represent
  attachments to a given ``proj:ticket``.
  (`#2451 <https://github.com/vertexproject/synapse/pull/2451>`_)
- Add a implicit wildcard behavior to the ``time`` type when lifting or
  filtering nodes. Dates ending in a ``*`` are converted into ranges covering
  all possible times in them. For example, ``.created=202101*`` would lift all
  nodes created on the first month of 2021.
  (`#2446 <https://github.com/vertexproject/synapse/pull/2446>`_)
- Add the following ``$lib.time`` functions to chop information from a time
  value.
  (`#2446 <https://github.com/vertexproject/synapse/pull/2446>`_)

    - ``$lib.time.year()``
    - ``$lib.time.month()``
    - ``$lib.time.day()``
    - ``$lib.time.hour()``
    - ``$lib.time.minute()``
    - ``$lib.time.second()``
    - ``$lib.time.dayofweek()``
    - ``$lib.time.dayofmonth()``
    - ``$lib.time.monthofyear()``

- Add ``List.extend()``, ``List.slice()``, ``Str.find()``, and ``Str.size()``
  functions to Stormtypes.
  (`#2450 <https://github.com/vertexproject/synapse/pull/2450>`_)
  (`#2451 <https://github.com/vertexproject/synapse/pull/2451>`_)
- Add ``$lib.json.schema()`` and a ``json:schema`` object to Stormtypes.
  These can be used to validate arbitrary data JSON structures in Storm using
  JSON Schema.
  (`#2448 <https://github.com/vertexproject/synapse/pull/2448>`_)
- Update syntax checking rules and address deprecation warnings for strings
  in the Synapse codebase.
  (`#2426 <https://github.com/vertexproject/synapse/pull/2426>`_)


v2.69.0 - 2021-11-02
====================

Features and Enhancements
-------------------------
- Add support for building Optic Workflows for Storm Packages in the
  ``synapse.tools.genpkg`` tool.
  (`#2444 <https://github.com/vertexproject/synapse/pull/2444>`_)
- The ``synapse.tools.storm`` CLI tool now prints out node properties in
  precedence order.
  (`#2449 <https://github.com/vertexproject/synapse/pull/2449>`_)
- Update the global Stormtypes registry to better track types when they are
  added or removed.
  (`#2447 <https://github.com/vertexproject/synapse/pull/2447>`_)


v2.68.0 - 2021-10-29
====================

Features and Enhancements
-------------------------
- Add ``crypto:currency:transaction``, ``crypto:currency:block``,
  ``crypto:smart:contract`` and ``econ:acct:balanc`` forms.
  (`#2423 <https://github.com/vertexproject/synapse/pull/2423>`_)
- Add ``$lib.hex.decode()`` and ``$lib.hex.encode()`` Stormtypes functions to
  encode and decode hexidecimal data as bytes. Add ``slice()`` and
  ``unpack()`` methods to the Storm Bytes object.
  (`#2441 <https://github.com/vertexproject/synapse/pull/2441>`_)
- Add ``$lib.yaml`` and ``$lib.xml`` Stormtypes libraries for interacting with
  YAML and XML text, respectively.
  (`#2434 <https://github.com/vertexproject/synapse/pull/2434>`_)
- Add a Storm ``version`` command to show the user the current version of
  Synapse the Cortex is using.
  (`#2440 <https://github.com/vertexproject/synapse/pull/2440>`_)

Bugfixes
--------
- Fix overzealous ``if`` statement caching in Storm.
  (`#2442 <https://github.com/vertexproject/synapse/pull/2442>`_)


v2.67.0 - 2021-10-27
====================

Features and Enhancements
-------------------------
- Add ``$node.addEdge()`` and ``$node.delEdge()`` APIs in Storm to allow for
  programatically setting edges. Add a ``reverse`` argument to
  ``$node.edges()`` that allows traversing edges in reverse.
  (`#2351 <https://github.com/vertexproject/synapse/pull/2351>`_)

Bugfixes
--------
- Fix a pair of regressions related to unicode/IDNA support for scraping and
  normalizing FQDNs.
  (`#2436 <https://github.com/vertexproject/synapse/pull/2436>`_)

Improved Documentation
----------------------
- Add documentation for the Cortex ``api/v1/storm/call`` HTTP API endpoint.
  (`#2435 <https://github.com/vertexproject/synapse/pull/2435>`_)


v2.66.0 - 2021-10-26
====================

Features and Enhancements
-------------------------
- Improve unicode/IDNA support for scraping and normalizing FQDNs.
  (`#2408 <https://github.com/vertexproject/synapse/pull/2408>`_)
- Add ``$lib.inet.http.ouath`` to support OAuth based workflows in Storm,
  starting with OAuth v1.0 support.
  (`#2413 <https://github.com/vertexproject/synapse/pull/2413>`_)
- Replace ``pysha3`` requirement with ``pycryptodome``.
  (`#2422 <https://github.com/vertexproject/synapse/pull/2422>`_)
- Add a ``tls:ca:dir`` configuration option to the Cortex and Axon. This can
  be used to provide a directory of CA certificate files which are used in
  Storm HTTP API and Axon wget/wput APIs.
  (`#2429 <https://github.com/vertexproject/synapse/pull/2429>`_)

Bugfixes
--------
- Catch and raise bad ctors given in RStorm ``storm-cortex`` directives.
  (`#2424 <https://github.com/vertexproject/synapse/pull/2424>`_)
- Fix an issue with the ``cron.at`` command not properly capturing the current
  view when making the Cron job.
  (`#2425 <https://github.com/vertexproject/synapse/pull/2425>`_)
- Disallow the creation of extended properties, universal properties, and tag
  properties which are not valid properties in the Storm grammar.
  (`#2428 <https://github.com/vertexproject/synapse/pull/2428>`_)
- Fix an issue with ``$lib.guid()`` missing a ``toprim()`` call on its input.
  (`#2421 <https://github.com/vertexproject/synapse/pull/2421>`_)

Improved Documentation
----------------------
- Update our Cell devops documentation to note how to replace the TLS keypair
  used by the built in webserver with third party certificates.
  (`#2432 <https://github.com/vertexproject/synapse/pull/2432>`_)


v2.65.0 - 2021-10-16
====================

Features and Enhancements
-------------------------
- Add support for interacting with IMAP email servers though Storm, using the
  ``$lib.inet.imap.connect()`` function. This returns a object that can be
  used to delete, read, and search emails in a given IMAP mailbox.
  (`#2399 <https://github.com/vertexproject/synapse/pull/2399>`_)
- Add a new Storm command, ``once``. This command can be used to 'gate' a node
  in a Storm pipeline such that the node only passes through the command
  exactly one time for a given named 'gate'. The gate information is stored in
  nodedata, so it is inspectable and subject to all other features that
  apply to nodedata.
  (`#2404 <https://github.com/vertexproject/synapse/pull/2404>`_)
- Add a ``:released`` property to ``it:prod:softver`` to record when a
  software version was released.
  (`#2419 <https://github.com/vertexproject/synapse/pull/2419>`_)
- Add a ``tryLoadPkgProto`` convenience function to the
  ``synapse.tools.genpkg`` for Storm service package generation with inline
  documentation.
  (`#2414 <https://github.com/vertexproject/synapse/pull/2414>`_)

Bugfixes
--------
- Add ``asyncio.sleep(0)`` calls in the ``movetag`` implementation to address
  some possible hot-loops.
  (`#2411 <https://github.com/vertexproject/synapse/pull/2411>`_)
- Clarify and sanitize URLS in a Aha related log message i
  ``synapse.telepath``.
  (`#2415 <https://github.com/vertexproject/synapse/pull/2415>`_)

Improved Documentation
----------------------
- Update our ``fork`` definition documentation.
  (`#2409 <https://github.com/vertexproject/synapse/pull/2409>`_)
- Add documentation for using client-side TLS certificates in Telepath.
  (`#2412 <https://github.com/vertexproject/synapse/pull/2412>`_)
- Update the Storm CLI tool documentation.
  (`#2406 <https://github.com/vertexproject/synapse/pull/2406>`_)
- The Storm types and Storm library documentation now automatically links
  from return values to return types.
  (`#2410 <https://github.com/vertexproject/synapse/pull/2410>`_)

v2.64.1 - 2021-10-08
====================

Bugfixes
--------
- Add a retry loop in the base ``Cell`` class when attempting to register with
  an ``Aha`` server.
  (`#2405 <https://github.com/vertexproject/synapse/pull/2405>`_)
- Change the behavior of ``synapse.common.yamlload()`` to not create files
  when the expected file is not present on disk, and open existing files in
  read-only mode.
  (`#2396 <https://github.com/vertexproject/synapse/pull/2396>`_)


v2.64.0 - 2021-10-06
====================

Features and Enhancements
-------------------------
- Add support for scraping the following cryptocurrency addresses to the
  ``synapse.lib.scrape`` APIs and Storm ``scrape`` command.
  (`#2387 <https://github.com/vertexproject/synapse/pull/2387>`_)
  (`#2401 <https://github.com/vertexproject/synapse/pull/2401>`_)

    - Bitcoin
    - Bitcoin Cash
    - Ethereum
    - Ripple
    - Cardano
    - Polkadot

  The internal cache of regular expressions in the ``synapse.lib.scrape``
  library is also now a private member; API users should use the
  ``synapse.lib.scrape.scrape()`` function moving forward.

- Add ``:names`` property to the ``it:mitre:attack:software`` form.
  (`#2397 <https://github.com/vertexproject/synapse/pull/2397>`_)
- Add a ``:desc`` property to the ``inet:whois:iprec`` form.
  (`#2392 <https://github.com/vertexproject/synapse/pull/2392>`_)
- Added several new Rstorm directives.
  (`#2359 <https://github.com/vertexproject/synapse/pull/2359>`_)
  (`#2400 <https://github.com/vertexproject/synapse/pull/2400>`_)

  - ``storm-cli`` - Runs a Storm query with the Storm CLI tool
  - ``storm-fail`` - Toggles whether or not the following Storm command
    should fail or not.
  - ``storm-multiline`` - Allows embedding a multiline Storm query as a JSON
    encoded string for future execution.
  - ``storm-vcr-callback`` - Allows specifying a custom callback which a VCR
    object is sent too.

Bugfixes
--------
- Fix a missing ``toprim()`` call when loading a Storm package directly with
  Storm.
  (`#2359 <https://github.com/vertexproject/synapse/pull/2359>`_)
- Fix a caching issue where tagprops were not always being populated in a
  ``Node`` tagprop dictionary.
  (`#2396 <https://github.com/vertexproject/synapse/pull/2396>`_)
- Add a ``mesg`` argument to a few ``NoSuchVar`` and ``BadTypeValu``
  exceptions.
  (`#2403 <https://github.com/vertexproject/synapse/pull/2403>`_)

Improved Documentation
----------------------
- Storm reference docs have been converted from Jupyter notebook format to
  Synapse ``.rstorm`` format, and now display examples using the Storm CLI
  tool, instead of the Cmdr CLI tool.
  (`#2359 <https://github.com/vertexproject/synapse/pull/2359>`_)


v2.63.0 - 2021-09-29
====================

Features and Enhancements
-------------------------
- Add a ``risk:attacktype`` taxonomy to the risk model. Add ``:desc`` and
  ``:type`` properties to the ``risk:attack`` form.
  (`#2386 <https://github.com/vertexproject/synapse/pull/2386>`_)
- Add ``:path`` property to the ``it:prod:softfile`` form.
  (`#2388 <https://github.com/vertexproject/synapse/pull/2388>`_)

Bugfixes
--------
- Fix the repr for the``auth:user``  Stormtype when printing a user
  object in Storm.
  (`#2383 <https://github.com/vertexproject/synapse/pull/2383>`_)


v2.62.1 - 2021-09-22
====================

Bugfixes
--------
- Fix an issue in the Nexus log V1 to V2 migration code which resulted in
  LMDB file copies being made instead of having directories renamed. This can
  result in a sparse file copy of the Nexus log, resulting in a condition
  where the volume containing the Cell directory may run out of space.
  (`#2374 <https://github.com/vertexproject/synapse/pull/2374>`_)


v2.62.0 - 2021-09-21
====================

Features and Enhancements
-------------------------
- Add APIs to support trimming, rotating and culling Nexus logs from Cells
  with Nexus logging enabled. These operations are distributed to downstream
  consumers, of the Nexus log (e.g. mirrors). For the Cortex, this can be
  invoked in Storm with the ``$lib.cell.trimNexsLog()`` Stormtypes API. The
  Cortex devops documentation contains more information about Nexus log
  rotation.
  (`#2339 <https://github.com/vertexproject/synapse/pull/2339>`_)
  (`#2371 <https://github.com/vertexproject/synapse/pull/2371>`_)
- Add ``.size()`` API to the Stormtypes ``storm:query`` object. This will run
  the query and return the number of nodes it would have yielded.
  (`#2363 <https://github.com/vertexproject/synapse/pull/2363>`_)

Improved Documentation
----------------------
- Document the tag glob meanings on the Stormtypes ``$node.tags()`` API.
  (`#2368 <https://github.com/vertexproject/synapse/pull/2368>`_)


v2.61.0 - 2021-09-17
====================

Features and Enhancements
-------------------------
- Add a ``!export`` command to the Storm CLI to save query results to a
  ``.nodes`` file.
  (`#2356 <https://github.com/vertexproject/synapse/pull/2356>`_)
- Add ``$lib.cell.hotFixesCheck()`` and ``$lib.cell.hotFixesApply()``
  Stormtypes functions. These can be used to apply optional hotfixes to a
  Cortex on demand by an admin.
  (`#2348 <https://github.com/vertexproject/synapse/pull/2348>`_)
- Add ``$lib.infosec.cvss.calculateFromProps()`` to allow calculating a CVSS
  score from a dictionary of CVSS properties.
  (`#2353 <https://github.com/vertexproject/synapse/pull/2353>`_)
- Add ``$node.data.has()`` API to Stormtypes to allow easy checking if a node
  has nodedata for a given name.
  (`#2350 <https://github.com/vertexproject/synapse/pull/2350>`_)

Bugfixes
--------
- Fix for large return values with ``synapse.lib.coro.spawn()``.
  (`#2355 <https://github.com/vertexproject/synapse/pull/2355>`_)
- Fix ``synapse.lib.scrape.scrape()`` capturing various common characters used
  to enclose URLs.
  (`#2352 <https://github.com/vertexproject/synapse/pull/2352>`_)
- Ensure that generators being yielded from are always being closed.
  (`#2358 <https://github.com/vertexproject/synapse/pull/2358>`_)
- Fix docstring for ``str.upper()`` in Stormtypes.
  (`#2354 <https://github.com/vertexproject/synapse/pull/2354>`_)

Improved Documentation
----------------------
- Add link to the Power-Ups blog post from the Cortex dev-ops documentation.
  (`#2357 <https://github.com/vertexproject/synapse/pull/2357>`_)


v2.60.0 - 2021-09-07
====================

Features and Enhancements
-------------------------
- Add new ``risk:compromise`` and ``risk:compromisetype`` forms. Add
  ``attacker``, ``compromise``, and ``target`` secondary properties to the
  ``risk:attack`` form.
  (`#2348 <https://github.com/vertexproject/synapse/pull/2348>`_)

Bugfixes
--------
- Add a missing ``wait()`` call when calling the ``CoreApi.getAxonUpload()``
  and ``CoreApi.getAxonBytes()`` Telepath APIs.
  (`#2349 <https://github.com/vertexproject/synapse/pull/2349>`_)

Deprecations
------------
- Deprecate the ``actor:org``, ``actor:person``, ``target:org`` and
  ``target:person`` properties on ``risk:attack`` in favor of new ``attacker``
  and ``target`` secondary properties. Deprecate the ``type`` property on
  ``ou:campaign`` in favor of the ``camptype`` property.
  (`#2348 <https://github.com/vertexproject/synapse/pull/2348>`_)


v2.59.0 - 2021-09-02
====================

Features and Enhancements
-------------------------
- Add a new Storm command, ``pkg.docs``, to enumerate any documentation that
  has been bundled with a Storm package.
  (`#2341 <https://github.com/vertexproject/synapse/pull/2341>`_)
- Add support for manipulating ``'proj:comment`` nodes via Stormtypes.
  (`#2345 <https://github.com/vertexproject/synapse/pull/2345>`_)
- Add ``Axon.wput()`` and ``$lib.axon.wput()`` to allow POSTing a file from
  an Axon to a given URL.
  (`#2347 <https://github.com/vertexproject/synapse/pull/2347>`_)
- Add ``$lib.export.toaxon()`` to allow exporting a ``.nodes`` file directly
  to an Axon based on a given storm query and opts.
  (`#2347 <https://github.com/vertexproject/synapse/pull/2347>`_)
- The ``synapse.tools.feed`` tool now accepts a ``--view`` argument to feed
  data to a specific View.
  (`#2342 <https://github.com/vertexproject/synapse/pull/2342>`_)
- The ``synapse.tools.feed`` tool now treats ``.nodes`` files as msgpack files
  for feeding data to a Cortex.
  (`#2343 <https://github.com/vertexproject/synapse/pull/2343>`_)
- When the Storm ``help`` command has an argument without any matching
  commands, it now prints a helpful message.
  (`#2338 <https://github.com/vertexproject/synapse/pull/2338>`_)

Bugfixes
--------
- Fix a caching issue between ``$lib.lift.byNodeData()`` and altering the
  existing node data on a given node.
  (`#2344 <https://github.com/vertexproject/synapse/pull/2344>`_)
- Fix an issue with backups were known lmdbslabs could be omitted from being
  treated as lmdb databases, resulting in inefficient file copies being made.
  (`#2346 <https://github.com/vertexproject/synapse/pull/2346>`_)


v2.58.0 - 2021-08-26
====================

Features and Enhancements
-------------------------
- Add ``!pushfile``, ``!pullfile``, and ``!runfile`` commands to the
  ``synapse.tools.storm`` tool.
  (`#2334 <https://github.com/vertexproject/synapse/pull/2334>`_)
- Add multiname SNI support to ``ssl://`` listening configurations for
  the Daemon.
  (`#2336 <https://github.com/vertexproject/synapse/pull/2336>`_)
- Add a new Cortex HTTP API Endpoint, ``/api/v1/feed``. This can be used to
  add nodes to the Cortex in bulk.
  (`#2337 <https://github.com/vertexproject/synapse/pull/2337>`_)
- Refactor the ``syn.nodes`` feed API implementation to smooth out the ingest
  rate.
  (`#2337 <https://github.com/vertexproject/synapse/pull/2337>`_)
- Sort the Storm Package commands in documentation created by
  ``synpse.tools.autodoc`` alphabetically.
  (`#2335 <https://github.com/vertexproject/synapse/pull/2335>`_)

Deprecations
------------
- Deprecate the ``syn.splices`` and ``syn.nodedata`` feed API formats.
  (`#2337 <https://github.com/vertexproject/synapse/pull/2337>`_)


v2.57.0 - 2021-08-24
====================

Features and Enhancements
-------------------------
- Add a basic ``synapse.tools.storm`` CLI tool. This can be used to connect
  to a Cortex via Telepath and directly execute Storm commands.
  (`#2332 <https://github.com/vertexproject/synapse/pull/2332>`_)
- Add an ``inet:http:session`` form to track the concept of a prolonged
  session a user may have with a webserver across multiple HTTP requests.
  Add an ``:success` property to the ``ou:campaign`` form to track if a
  campaign was sucessful or not. Add an ``:goal`` property to the
  ``risk:attack`` form to track the specific goal of the attack. Add an
  ``:desc`` property to the ``proj:project`` form to capture a description of
  the project.
  (`#2333 <https://github.com/vertexproject/synapse/pull/2333>`_)

Bugfixes
--------
- Fix an issue with ``synapse.lib.rstorm`` where multiline node properties
  could produce RST which did not render properly.
  (`#2331 <https://github.com/vertexproject/synapse/pull/2331>`_)

Improved Documentation
----------------------
- Clean up the documentation for the Storm ``wget`` command.
  (`#2325 <https://github.com/vertexproject/synapse/pull/2325>`_)


v2.56.0 - 2021-08-19
====================

Features and Enhancements
-------------------------
- Refactor some internal Axon APIs for downstream use.
  (`#2330 <https://github.com/vertexproject/synapse/pull/2330>`_)

Bugfixes
--------
- Resolve an ambiguity in the Storm grammar with yield statement and dollar
  expressions inside filter expression. There is a slight backwards
  incompatibility with this change, as dollar expressions insider of filter
  expressions now require a ``$`` prepended where before it was optional.
  (`#2322 <https://github.com/vertexproject/synapse/pull/2322>`_)


v2.55.0 - 2021-08-18
====================

Features and Enhancements
-------------------------

- Add ``$node.props.set()`` Stormtypes API to allow programmatically setting
  node properties.
  (`#2324 <https://github.com/vertexproject/synapse/pull/2324>`_)
- Deny non-runtsafe invocations of the following Storm commands:
  (`#2326 <https://github.com/vertexproject/synapse/pull/2326>`_)

    - ``graph``
    - ``iden``
    - ``movetag``
    - ``parallel``
    - ``tee``
    - ``tree``

- Add a ``Axon.hashset()`` API to get the md5, sha1, sha256 and sha512 hashes
  of file in the Axon. This is exposed in Stormtypes via the
  ``$lib.bytes.hashset()`` API.
  (`#2327 <https://github.com/vertexproject/synapse/pull/2327>`_)
- Add the ``synapse.servers.stemcell`` server and a new Docker image,
  ``vertexproject/synaspe-stemcell``. The Stemcell server is similar to the
  ``synapse.servers.cell`` server, except it resolves the Cell ctor from the
  ``cell:ctor`` key from the ``cell.yaml`` file, or from the
  ``SYN_STEM_CELL_CTOR`` environment variable.
  (`#2328 <https://github.com/vertexproject/synapse/pull/2328>`_)


v2.54.0 - 2021-08-05
====================

Features and Enhancements
-------------------------

- Add ``storm-envvar`` directive to RST preprocessor to include environment
  variables in ``storm-pre`` directive execution context.
  (`#2321 <https://github.com/vertexproject/synapse/pull/2321>`_)
- Add new ``diff`` storm command to allow users to easily lift the set of nodes
  with changes in the top layer of a forked view.  Also adds the ``--no-tags``
  option to the ``merge`` command to allow users to omit ``tag:add`` node edits
  and newly constructed ``syn:tag`` nodes when merging selected nodes.
  (`#2320 <https://github.com/vertexproject/synapse/pull/2320>`_)
- Adds the following properties to the data model:
  (`#2319 <https://github.com/vertexproject/synapse/pull/2319>`_)

    - ``biz:deal:buyer:org``
    - ``biz:deal:buyer:orgname``
    - ``biz:deal:buyer:orgfqdn``
    - ``biz:deal:seller:org``
    - ``biz:deal:seller:orgname``
    - ``biz:deal:seller:orgfqdn``
    - ``biz:prod:madeby:org``
    - ``biz:prod:madeby:orgname``
    - ``biz:prod:madeby:orgfqdn``
    - ``ou:opening:posted``
    - ``ou:opening:removed``
    - ``ou:org:vitals``

- Updates ``storm-mock-http`` to support multiple HTTP requests/responses
  in RST preprocessor.
  (`#2317 <https://github.com/vertexproject/synapse/pull/2317>`_)

v2.53.0 - 2021-08-05
====================

This release contains an automatic data migration that may cause additional
startup time on the first boot. This is done to unique array properties which
previously were not uniqued. Deployments with startup or liveliness probes
should have those disabled while this upgrade is performed to prevent
accidental termination of the Cortex process. Please ensure you have a tested
backup available before applying this update.

Features and Enhancements
-------------------------
- Add an ``embeds`` option to Storm to allow extracting additional data
  when performing queries.
  (`#2314 <https://github.com/vertexproject/synapse/pull/2314>`_)
- Enforce node data permissions at the Layer boundary. Remove the
  ``node.data.get`` and ``node.data.list`` permissions.
  (`#2311 <https://github.com/vertexproject/synapse/pull/2311>`_)
- Add ``auth.self.set.email``, ``auth.self.set.name``,
  ``auth.self.set.passwd`` permissions on users when changing those values.
  These permissions default to being allowed, allowing a rule to be created
  that can deny users from changing these values.
  (`#2311 <https://github.com/vertexproject/synapse/pull/2311>`_)
- Add ``$lib.inet.smtp`` to allow sending email messages from Storm.
  (`#2315 <https://github.com/vertexproject/synapse/pull/2315>`_)
- Warn if a LMDB commit operation takes too long.
  (`#2316 <https://github.com/vertexproject/synapse/pull/2316>`_)
- Add new data types, ``taxon`` and ``taxonomy``, to describe hierarchical
  taxonomies.
  (`#2312 <https://github.com/vertexproject/synapse/pull/2312>`_)
- Add a new Business Development model. This allows tracking items related to
  contract, sales, and purchasing lifecycles. This adds the following new forms
  to the data model: ``biz:dealtype``, ``biz:prodtype``, ``biz:dealstatus``,
  ``biz:rfp``, ``biz:deal``, ``biz:bundle``, ``biz:product``, and
  ``biz:stake``. The Org model is also updated to add new forms for supporting
  parts of the business lifecycle, adding ``ou:jobtype``,
  ``ou:jobtitle``, ``ou:employment``, ``ou:opening``, ``ou:vitals``,
  ``ou:camptype``, and ``ou:orgtype``, ``ou:conttype`` forms. The Person model
  got a new form, ``ps:workhist``.
  (`#2312 <https://github.com/vertexproject/synapse/pull/2312>`_)
- Add a ``:deleted`` property to ``inet:web:post``.
  (`#2312 <https://github.com/vertexproject/synapse/pull/2312>`_)
- Update the following array properties to be unique sets, and add a data
  model migration to update the data at rest:
  (`#2312 <https://github.com/vertexproject/synapse/pull/2312>`_)

    - ``edu:course:prereqs``
    - ``edu:class:assistants``
    - ``ou:org:subs``
    - ``ou:org:names``
    - ``ou:org:dns:mx``
    - ``ou:org:locations``
    - ``ou:org:industries``
    - ``ou:industry:sic``
    - ``ou:industry:subs``
    - ``ou:industry:isic``
    - ``ou:industry:naics``
    - ``ou:preso:sponsors``
    - ``ou:preso:presenters``
    - ``ou:conference:sponsors``
    - ``ou:conference:event:sponsors``
    - ``ou:conference:attendee:roles``
    - ``ou:conference:event:attendee:roles``
    - ``ou:contract:types``
    - ``ou:contract:parties``
    - ``ou:contract:requirements``
    - ``ou:position:reports``
    - ``ps:person:names``
    - ``ps:person:nicks``
    - ``ps:persona:names``
    - ``ps:persona:nicks``
    - ``ps:education:classes``
    - ``ps:contactlist:contacts``

Bugfixes
--------
- Prevent renaming the ``all`` role.
  (`#2313 <https://github.com/vertexproject/synapse/pull/2313>`_)

Improved Documentation
----------------------
- Add documentation about Linux kernel parameteres which can be tuned to
  affect Cortex performance.
  (`#2316 <https://github.com/vertexproject/synapse/pull/2316>`_)


v2.52.1 - 2021-07-30
====================

Bugfixes
--------
- Fix a display regression when enumerating Cron jobs with the Storm
  ``cron.list`` command.
  (`#2309 <https://github.com/vertexproject/synapse/pull/2309>`_)


v2.52.0 - 2021-07-29
====================

Features and Enhancements
-------------------------
- Add a new specification for defining input forms that a pure Storm command
  knows how to natively handle.
  (`#2301 <https://github.com/vertexproject/synapse/pull/2301>`_)
- Add ``Lib.reverse()`` and ``Lib.sort()`` methods to Stormtypes API.
  (`#2306 <https://github.com/vertexproject/synapse/pull/2306>`_)
- Add ``View.parent`` property in Stormtypes API.
  (`#2306 <https://github.com/vertexproject/synapse/pull/2306>`_)
- Support Telepath Share objects in Storm.
  (`#2293 <https://github.com/vertexproject/synapse/pull/2293>`_)
- Allow users to specify a view to run a cron job against, move a cron job to
  a new view, and update permission check for adding/moving cron jobs to views.
  (`#2292 <https://github.com/vertexproject/synapse/pull/2292>`_)
- Add CPE and software name infomation to the ``inet:flow`` form. Add
  ``it:av:prochit``, ``it:exec:thread``, ``it:exec:loadlib``,
  ``it:exec:mmap``, ``it:app:yara:procmatch`` forms to the infotech model.
  Add ``:names`` arrays to ``it:prod:soft`` and ``it:prod:softver`` forms
  to assist in entity resolution of software. Add a ``risk:alert`` form to
  the risk model to allow for capturing arbitrary alerts.
  (`#2304 <https://github.com/vertexproject/synapse/pull/2304>`_)
- Allow Storm packages to specify other packages they require and possible
  conflicts would prevent them from being installed in a Cortex.
  (`#2307 <https://github.com/vertexproject/synapse/pull/2307>`_)

Bugfixes
--------
- Specify the View when lifting ``syn:trigger`` runt nodes.
  (`#2300 <https://github.com/vertexproject/synapse/pull/2300>`_)
- Update the scrape URL regular expression to ignore trailing periods and
  commas.
  (`#2302 <https://github.com/vertexproject/synapse/pull/2302>`_)
- Fix a bug in Path scope for nodes yielding by pure Storm commands.
  (`#2305 <https://github.com/vertexproject/synapse/pull/2305>`_)


v2.51.0 - 2021-07-26
====================

Features and Enhancements
-------------------------
- Add a ``--size`` option to the Storm ``divert`` command to limit the number
  of times the generator is iterated.
  (`#2297 <https://github.com/vertexproject/synapse/pull/2297>`_)
- Add a ``perms`` key to the pure Storm command definition. This allows for
  adding intuitive permission boundaries for pure Storm commands which are
  checked prior to command execution.
  (`#2297 <https://github.com/vertexproject/synapse/pull/2297>`_)
- Allow full properties with comparators when specifying the destination
  or source when walking light edges.
  (`#2298 <https://github.com/vertexproject/synapse/pull/2298>`_)

Bugfixes
--------
- Fix an issue with LMDB slabs not being backed up if their directories did
  not end in ``.lmdb``.
  (`#2296 <https://github.com/vertexproject/synapse/pull/2296>`_)


v2.50.0 - 2021-07-22
====================

Features and Enhancements
-------------------------
- Add ``.cacheget()`` and ``cacheset()`` APIs to the Storm ``node:data``
  object for easy caching of structured data on nodes based on time.
  (`#2290 <https://github.com/vertexproject/synapse/pull/2290>`_)
- Make the Stormtypes unique properly with a Set type. This does disallow the
  use of mutable types such as dictionaries inside of a Set.
  (`#2225 <https://github.com/vertexproject/synapse/pull/2225>`_)
- Skip executing non-runtsafe commands when there are no inbound nodes.
  (`#2291 <https://github.com/vertexproject/synapse/pull/2291>`_)
- Add ``asroot:perms`` key to Storm Package modules. This allows package
  authors to easily declare permissions their packages. Add Storm commands
  ``auth.user.add``, ``auth.role.add``, ``auth.user.addrule``,
  ``auth.role.addrule``, and ``pkg.perms.list`` to help with some of the
  permission management.
  (`#2294 <https://github.com/vertexproject/synapse/pull/2294>`_)


v2.49.0 - 2021-07-19
====================

Features and Enhancements
-------------------------
- Add a ``iden`` parameter when creating Cron jobs to allow the creation of
  jobs with stable identifiers.
  (`#2264 <https://github.com/vertexproject/synapse/pull/2264>`_)
- Add ``$lib.cell`` Stormtypes library to allow for introspection of the
  Cortex from Storm for Admin users.
  (`#2285 <https://github.com/vertexproject/synapse/pull/2285>`_)
- Change the Telepath Client connection loop error logging to log at the
  Error level instead of the Info level.
  (`#2283 <https://github.com/vertexproject/synapse/pull/2283>`_)
- Make the tag part normalization more resilient to data containing non-word
  characters.
  (`#2289 <https://github.com/vertexproject/synapse/pull/2289>`_)
- Add ``$lib.tags.prefix()`` Stormtypes to assist with normalizing a list of
  tags with a common prefix.
  (`#2289 <https://github.com/vertexproject/synapse/pull/2289>`_)
- Do not allow the Storm ``divert`` command to work with non-generator
  functions.
  (`#2282 <https://github.com/vertexproject/synapse/pull/2282>`_)

Bugfixes
--------
- Fix an issue with Storm command execution with non-runtsafe options.
  (`#2284 <https://github.com/vertexproject/synapse/pull/2284>`_)
- Log when the process pool fails to initialize. This may occur in certain
  where CPython multiprocessing primitives are not completely supported.
  (`#2288 <https://github.com/vertexproject/synapse/pull/2288>`_)
- In the Telepath Client, fix a race condition which could have raised an
  AttributeError in Aha resolutions.
  (`#2286 <https://github.com/vertexproject/synapse/pull/2286>`_)
- Prevent the reuse of a Telepath Client object when it has been fini'd.
  (`#2286 <https://github.com/vertexproject/synapse/pull/2286>`_)
- Fix a race condition in the Aha server when handling distributed changes
  which could have left the service in a desynchronized state.
  (`#2287 <https://github.com/vertexproject/synapse/pull/2287>`_)

Improved Documentation
----------------------
- Update the documentation for the ``synapse.tools.feed`` tool.
  (`#2279 <https://github.com/vertexproject/synapse/pull/2279>`_)


v2.48.0 - 2021-07-13
====================

Features and Enhancements
-------------------------
- Add a Storm ``divert`` command to ease the implementation of ``--yield``
  constructs in Storm commands. This optionally yields nodes from a generator,
  or yields inbound nodes, while still ensuring the generator is conusmed.
  (`#2277 <https://github.com/vertexproject/synapse/pull/2277>`_)
- Add Storm runtime debug tracking. This is a boolean flag that can be set or
  unset via ``$lib.debug``. It can be used by Storm packages to determine if
  they should take extra actions, such as additional print statements, without
  needing to track additional function arguments in their implementations.
  (`#2278 <https://github.com/vertexproject/synapse/pull/2278>`_)

Bugfixes
--------
- Fix an ambiguity in the Storm grammar.
  (`#2280 <https://github.com/vertexproject/synapse/pull/2280>`_)
- Fix an issue where form autoadds could fail to be created in specific cases of
  the model.
  (`#2273 <https://github.com/vertexproject/synapse/pull/2273>`_)


v2.47.0 - 2021-07-07
====================

Features and Enhancements
-------------------------
- Add ``$lib.regex.replace()`` Stormtypes API to perform regex based
  replacement of string parts.
  (`#2274 <https://github.com/vertexproject/synapse/pull/2274>`_)
- Add universal properties to the dictionary returned by
  ``Cortex.getModelDict()`` as a ``univs`` key.
  (`#2276 <https://github.com/vertexproject/synapse/pull/2276>`_)
- Add additional ``asyncio.sleep(0)`` statements to ``Layer._storNodeEdits``
  to improve Cortex responsiveness when storing large numbers of edits at
  once.
  (`#2275 <https://github.com/vertexproject/synapse/pull/2275>`_)


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
- Update Stormtypes API documentation for ``bool``, ``proj:epic``,
  ``proj:epics``, ``proj:ticket``, ``proj:tickets``, ``proj:sprint``,
  ``proj:sprints``, ``proj:project``, ``stix:bundle`` types.
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
- Add a ``.move()`` method on Stormtypes ``trigger`` objects to allow
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
- Add a ``.type`` string to the Stormtypes ``auth:gate`` object to
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
- Add PR ``#2117`` to bugfix list in CHANGLOG.rst for v2.41.0 :D

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
  will all now always return a ``inet:http:resp`` object; if the ``.code``
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
- Move the retrieval of ``https:headers`` from HTTP API handlers into a
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
  arbitrary HTTP headers for the Cell HTTP API server.
  (`#2164 <https://github.com/vertexproject/synapse/pull/2164>`_)
- Update the Cell HTTP API server to have a minimum TLS version of v1.2. Add a
  default ``/robots.txt`` route. Add ``X-XSS=Protection`` and
  ``X-Content-Type-Options`` headers to the default HTTP API responses.
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
  (`#2115 <https://github.com/vertexproject/synapse/pull/2115>`_)
  (`#2117 <https://github.com/vertexproject/synapse/pull/2117>`_)
  (`#2116 <https://github.com/vertexproject/synapse/pull/2116>`_)


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
- Add a ``/api/v1/active`` HTTP API to the Cell that can be used as an
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
- Add a ``/api/v1/auth/onepass/issue`` HTTP API for an admin to mint a
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
- Add ``CoreApi.reqValidStorm()`` and a ``/api/v1/reqvalidstorm`` Cortex HTTP API endpoint to validate that a given
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
- Add HTTP API endpoints for the Axon to upload, download and check for the existend of files.
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
- Add documentation for how to do boot-time configuration for a Synapse Cell.
  (`#1772 <https://github.com/vertexproject/synapse/pull/1772>`_)
- Remove duplicate information about backups.
  (`#1774 <https://github.com/vertexproject/synapse/pull/1774>`_)

v2.0.0 - 2020-06-08
===================

Initial 2.0.0 release.

.. _changelog-depr-20231001:

API Deprecation Notice - 2023-10-01
===================================

It's time to shed some long standing deprecations to reduce technical debt
and prepare for some new features and subsystems!  The following deprecated
APIs and commands will be removed on 2023-10-01:

Storm Commands
--------------

- ``sudo``
- ``splice.list``
- ``splice.undo``

Storm Options
-------------

- ``editformat=splices``

Cortex Telepath APIs
--------------------

- ``stat()``
- ``addCronJob()``
- ``delCronJob()``
- ``updateCronJob()``
- ``enableCronJob()``
- ``disableCronJob()``
- ``listCronJobs()``
- ``editCronJob()``
- ``setStormCmd()``
- ``delStormCmd()``
- ``addNodeTag()``
- ``delNodeTag()``
- ``setNodeProp()``
- ``delNodeProp()``
- ``eval()``
- ``watch()``
- ``splices()``
- ``splicesBack()``
- ``spliceHistory()``
- ``addFeedData(syn.splice, ...)``
- ``addFeedData(syn.nodeedits, ...)``

Layer Telepath APIs
-------------------

- ``splices()``
- ``splicesBack()``
- ``truncate()``

Cmdr Commands
-------------

- ``at``
- ``cron``
- ``trigger``
