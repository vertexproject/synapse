import os
import gzip

import synapse.common as s_common

import synapse.tests.utils as s_test_utils

import synapse.tools.utils.changelog as s_t_changelog

multiline_feature = '''---
desc: |
  - This is a pre-formatted RST block as YAML literal scalar.

    It has stuff in it already formatted all nice like.

    +-------------------+---------------------------+
    | Beep              | Boop                      |
    +===================+===========================+
    | hahaha            | lasers                    |
    +-------------------+---------------------------+
    | wowow             | stufff                    |
    +-------------------+---------------------------+

    These are more lines. They can have things like RST string literals in
    them ``like this``. You can even do a literal block!

    ::

      wow

    So this is a example.
desc:literal: true
prs: []
type: feat
...
'''

changelog_format_output = '''CHANGELOG ENTRY:


v0.1.22 - 2025-10-03
====================

Automatic Migrations
--------------------
- Migrated the widget storage to use acme lasers.
- See :ref:`datamigration` for more information about automatic migrations.

Model Changes
-------------
- Added lasers to the sci model.

Features and Enhancements
-------------------------
- This is a pre-formatted RST block as YAML literal scalar.

  It has stuff in it already formatted all nice like.

  +-------------------+---------------------------+
  | Beep              | Boop                      |
  +===================+===========================+
  | hahaha            | lasers                    |
  +-------------------+---------------------------+
  | wowow             | stufff                    |
  +-------------------+---------------------------+

  These are more lines. They can have things like RST string literals in
  them ``like this``. You can even do a literal block!

  ::

    wow

  So this is a example.
- I am a earlier feature.
  (`#1230 <https://github.com/vertexproject/synapse/pull/1230>`_)
- I am a feature.
  (`#1234 <https://github.com/vertexproject/synapse/pull/1234>`_)

Bugfixes
--------
- I am a bug which has quite a large amount of text in it. The amount of text
  will span across multiple lines after being formatted by the changelog tool.

Notes
-----
- I am a fancy note.

Improved documentation
----------------------
- Documented the lasers.

Deprecations
------------
- For widget maker has been deprecated in favor of the new acme corp laser
  cannons.
'''

class ChangelogToolTest(s_test_utils.SynTest):

    async def test_changelog_model_diff_class(self):
        outp = self.getTestOutp()
        old_fp = self.getTestFilePath('changelog', 'model_2.176.0_16ee721a6b7221344eaf946c3ab4602dda546b1a.yaml.gz')
        new_fp = self.getTestFilePath('changelog', 'model_2.176.0_2a25c58bbd344716cd7cbc3f4304d8925b0f4ef2.yaml.gz')
        oldmodel = s_t_changelog._getModelFile(old_fp)
        newmodel = s_t_changelog._getModelFile(new_fp)

        differ = s_t_changelog.ModelDiffer(newmodel.get('model'), oldmodel.get('model'))

        self.eq(differ.cur_type2iface['it:host'], ['inet:service:object', 'inet:service:base'])
        self.eq(differ.cur_type2iface['mat:type'], ['meta:taxonomy'])
        self.eq(differ.cur_iface_to_allifaces['it:host:activity'], ['it:host:activity'])
        self.eq(differ.cur_iface_to_allifaces['file:mime:msoffice'], ['file:mime:msoffice', 'file:mime:meta'])
        changes = differ.diffModl(outp)

        self.len(4, changes.get('edges').get('new_edges'))

        form_chng = changes.get('forms')
        self.isin('it:beeper:thingy', form_chng.get('new_forms'))
        self.notin('it:beeper:name', form_chng.get('new_forms'))
        updt_frms = form_chng.get('updated_forms')
        self.isin('new_properties', updt_frms.get('file:mime:pe:resource'))
        self.isin('new_properties_no_interfaces', updt_frms.get('file:mime:pe:resource'))
        self.isin('new_properties', updt_frms.get('inet:http:request'))
        self.notin('new_properties_no_interfaces', updt_frms.get('inet:http:request'))
        self.isin('updated_properties', updt_frms.get('file:mime:macho:section'))
        self.isin('deprecated_properties', updt_frms.get('file:mime:lnk'))
        self.isin('deprecated_properties_no_interfaces', updt_frms.get('file:mime:lnk'))
        self.isin('deprecated_properties', updt_frms.get('inet:http:request'))
        self.notin('deprecated_properties_no_interfaces', updt_frms.get('inet:http:request'))
        self.isin('new_properties', updt_frms.get('file:mime:lnk'))
        self.isin('new_properties_no_interfaces', updt_frms.get('file:mime:lnk'))
        self.isin('updated_properties', updt_frms.get('file:mime:lnk'))
        self.isin('updated_properties_no_interfaces', updt_frms.get('file:mime:lnk'))
        self.isin('updated_properties', updt_frms.get('inet:service:access'))
        self.notin('updated_properties_no_interfaces', updt_frms.get('inet:service:access'))

        self.isin('it:host:beeper', changes.get('interfaces').get('new_interfaces'))
        updt_iface = changes.get('interfaces').get('updated_interfaces')
        self.isin('deprecated_properties', updt_iface.get('it:host:activity'))
        self.isin('new_properties', updt_iface.get('it:host:activity'))
        self.isin('updated_properties', updt_iface.get('inet:service:base'))

        self.eq(changes.get('tagprops'), {})

        self.isin('it:reveng:function', changes.get('types').get('deprecated_types'))
        self.isin('inet:port', changes.get('types').get('deprecated_types'))
        self.isin('it:beeper:thingy', changes.get('types').get('new_types'))
        self.isin('it:beeper:name', changes.get('types').get('new_types'))
        uptd_types = changes.get('types').get('updated_types')
        self.isin('updated_opts', uptd_types.get('it:query'))
        self.isin('updated_interfaces', uptd_types.get('it:reveng:impfunc'))

        rst = s_t_changelog._gen_model_rst('v2.177.0', 'userguide_model_v2_177_0',
                                           changes, newmodel.get('model'), outp)
        text = rst.getRstText()
        self.isin('v2.177.0 Model Updates', text)
        self.isin('''**************
New Interfaces
**************

``it:host:beeper``
  Properties common to instances of beepers.''', text)
        self.isin('''*********
New Types
*********

``it:beeper:name``
  The friendly name of a beeper.
''', text)
        self.isin('''*********
New Forms
*********

``it:beeper:thingy``
  A beeper thingy.
''', text)
        self.isin('''**************
New Properties
**************

``file:mime:lnk``
  The form had the following properties added to it:


  ``driveserial``
    The drive serial number of the volume the link target is stored on.


  ``iconindex``
    A resource index for an icon within an icon location.
''', text)
        self.isin('''``inet:http:request``
  The form had the following property added to it:

  ``beep``
    The time that the host went beep.
''', text)
        # Some updates will require manual intervention to rewrite.
        self.isin('''******************
Updated Interfaces
******************

``inet:service:base``
  The property ``id`` has been modified from ['str', {'strip': True}] to ['str',
  {'lower': True, 'strip': True}].


``it:host:activity``
  The interface property ``time`` has been deprecated.


  The property ``beep`` has been added to the interface.
''', text)
        self.isin('''*************
Updated Types
*************

``it:query``
  The type has been modified from {'enums': None, 'globsuffix': False, 'lower':
  False, 'onespace': False, 'regex': None, 'replace': [], 'strip': True} to
  {'enums': None, 'globsuffix': False, 'lower': True, 'onespace': False,
  'regex': None, 'replace': [], 'strip': True}.


``it:reveng:impfunc``
  The type interface has been modified from None to ['it:host:beeper'].
''', text)
        self.isin('''******************
Updated Properties
******************

``file:mime:lnk``
  The form had the following property updated:


    The property ``entry:icon`` has been modified from ['file:path', {}] to
    ['time', {}].
''', text)
        self.isin('''***********
Light Edges
***********

``jenkies``
    When used with a ``it:prod:soft`` node, the edge indicates The software uses
    the jenkies technique.


``loves``
    The source node loves the target node.


``sneaky``
    When used with a ``ou:technique`` target node, the edge indicates The
    technique referred to is sneakily used.


``zoinks``
    When used with a ``it:prod:soft`` and an ``ou:technique`` node, the edge
    indicates The software uses the zoinks technique.
''', text)
        self.isin('''****************
Deprecated Types
****************

The following types have been marked as deprecated:


* ``inet:port``

''', text)
        self.isin('''****************
Deprecated Types
****************

The following forms have been marked as deprecated:


* ``it:reveng:function``
''', text)
        self.isin('''*********************
Deprecated Properties
*********************

``file:mime:lnk``
  The form had the following property deprecated:

  ``target:attrs``
    The attributes of the target file according to the LNK header.
''', text)

    async def test_changelog_model_diff_tool(self):
        # diff the stored test asset model vs the current runtime model :fingers_crossed:
        with self.getTestDir() as dirn:
            cdir = s_common.gendir(s_common.genpath(dirn, 'changes'))
            outp = self.getTestOutp()
            argv = ['gen', '--cdir', cdir, '--verbose', '--type', 'feat', 'I am a mighty feature!']
            self.eq(0, await s_t_changelog.main(argv, outp))

            modl_dirn = s_common.gendir(s_common.genpath(dirn, 'model'))
            old_fp = self.getTestFilePath('changelog', 'model_2.176.0_16ee721a6b7221344eaf946c3ab4602dda546b1a.yaml.gz')

            argv = ['format', '--cdir', cdir, '--version', 'v0.1.2', '--date', '2025-10-03',
                    '--model-doc-dir', modl_dirn, '--model-ref', old_fp,
                    '--model-doc-no-git', '--verbose', '--no-prs-from-git',
                    ]
            self.eq(0, await s_t_changelog.main(argv, outp))
            # We have many assertions we may run over outp where using outp.expect()
            # not not be the most efficient
            outp_str = str(outp)
            # model diff data
            self.isin('Not adding model changes to git.', outp_str)
            # Changelog data
            self.isin('v0.1.2 - 2025-10-03', outp_str)
            self.isin('- See :ref:`userguide_model_v0_1_2` for more detailed model changes.', outp_str)
            self.isin('- I am a mighty feature!', outp_str)

    async def test_changelog_model_save_compare(self):
        with self.getTestDir() as dirn:
            outp = self.getTestOutp()
            argv = ['model', '--cdir', dirn, '--save',]
            self.eq(0, await s_t_changelog.main(argv, outp))
            modelrefs_dirn = s_common.genpath(dirn, 'modelrefs')

            files = os.listdir(modelrefs_dirn)
            self.len(1, files)

            model_fp = s_common.genpath(modelrefs_dirn, files[0])

            with s_common.genfile(model_fp) as fd:
                buf = fd.read()
            buf = gzip.decompress(buf)
            data = s_common.yamlloads(buf)
            self.isin('commit', data)
            self.isin('model', data)
            self.isin('version', data)

            # Test compare vs self - no changes
            outp.clear()
            argv = ['model', '-c', model_fp, '--verbose']
            self.eq(0, await s_t_changelog.main(argv, outp))
            outp.expect("'edges': {}")
            outp.expect("'forms': {}")
            outp.expect("'interfaces': {}")
            outp.expect("'tagprops': {}")
            outp.expect("'types': {}")
            outp.expect("'univs': {}")

    async def test_changelog_gen_format(self):
        with self.getTestDir() as dirn:
            outp = self.getTestOutp()
            argv = ['gen', '--cdir', dirn, '--type', 'feat', '--pr', '1234', 'I am a feature.']
            self.eq(0, await s_t_changelog.main(argv, outp))

            outp = self.getTestOutp()
            argv = ['gen', '--cdir', dirn, '--type', 'feat', '--pr', '1230', 'I am a earlier feature.']
            self.eq(0, await s_t_changelog.main(argv, outp))

            outp.clear()
            desc = '''I am a bug which has quite a large amount of text in it. The amount of text will span across'''\
                ''' multiple lines after being formatted by the changelog tool.'''
            argv = ['gen', '--cdir', dirn, '--type', 'bug', desc]
            self.eq(0, await s_t_changelog.main(argv, outp))

            outp.clear()
            desc = 'I am a fancy note.'
            argv = ['gen', '--cdir', dirn, '--type', 'note', desc]
            self.eq(0, await s_t_changelog.main(argv, outp))

            outp.clear()
            desc = 'For widget maker has been deprecated in favor of the new acme corp laser cannons.'
            argv = ['gen', '--cdir', dirn, '--type', 'deprecation', desc,]
            self.eq(0, await s_t_changelog.main(argv, outp))

            outp.clear()
            desc = 'Documented the lasers.'
            argv = ['gen', '--cdir', dirn, '--type', 'doc', desc]
            self.eq(0, await s_t_changelog.main(argv, outp))

            outp.clear()
            desc = 'Migrated the widget storage to use acme lasers.'
            argv = ['gen', '--cdir', dirn, '--type', 'migration', desc]
            self.eq(0, await s_t_changelog.main(argv, outp))

            outp.clear()
            desc = 'Added lasers to the sci model.'
            argv = ['gen', '--cdir', dirn, '--type', 'model', desc]
            self.eq(0, await s_t_changelog.main(argv, outp))

            with s_common.genfile(dirn, f'{s_common.guid()}.yaml') as fd:
                fd.write(multiline_feature.encode())

            outp.clear()
            argv = ['format', '--cdir', dirn, '--version', 'v0.1.22', '--date', '2025-10-03', '--no-prs-from-git']
            self.eq(0, await s_t_changelog.main(argv, outp))

            self.eq(str(outp).strip(), changelog_format_output.strip())

        # Sad path tests
        with self.getTestDir() as dirn:
            outp = self.getTestOutp()

            fp = s_common.genpath(dirn, s_common.guid())
            with s_common.genfile(fp) as fd:
                fd.write('hello world'.encode())

            argv = ['format', '--cdir', dirn, '--version', 'v0.1.22', '--date', '2025-10-03']
            self.eq(1, await s_t_changelog.main(argv, outp))
            outp.expect('Error running')

            with s_common.genfile(fp) as fd:
                fd.truncate(0)
                fd.write(s_common.buid())
            outp.clear()
            argv = ['format', '--cdir', dirn, '--version', 'v0.1.22', '--date', '2025-10-03']
            self.eq(1, await s_t_changelog.main(argv, outp))
            outp.expect('No files passed validation')

            with s_common.genfile(fp) as fd:
                fd.truncate(0)
                fd.write('''desc:literal: true
desc: |
    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
type: feat
'''.encode())
            outp.clear()
            argv = ['format', '--cdir', dirn, '--version', 'v0.1.22', '--date', '2025-10-03', '--no-prs-from-git']
            self.eq(1, await s_t_changelog.main(argv, outp))
            outp.expect('desc line 0 must start with "- "')

            with s_common.genfile(fp) as fd:
                fd.truncate(0)
                fd.write('''desc:literal: true
desc: |
    - xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    xxxxxx
type: feat
            '''.encode())
            outp.clear()
            argv = ['format', '--cdir', dirn, '--version', 'v0.1.22', '--date', '2025-10-03', '--no-prs-from-git']
            self.eq(1, await s_t_changelog.main(argv, outp))
            outp.expect('desc line 1 must start with "  "')

            with s_common.genfile(fp) as fd:
                fd.truncate(0)
                fd.write('''desc:literal: true
desc: |
    - xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
type: feat
            '''.encode())
            outp.clear()
            argv = ['format', '--cdir', dirn, '--version', 'v0.1.22', '--date', '2025-10-03', '--no-prs-from-git']
            self.eq(1, await s_t_changelog.main(argv, outp))
            outp.expect('desc line 0 is too long, 79 > 79')
