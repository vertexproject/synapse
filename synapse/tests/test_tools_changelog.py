import synapse.tests.utils as s_test_utils

import synapse.tools.changelog as s_t_changelog

class ChangelogToolTest(s_test_utils.SynTest):

    async def test_model_diff(self):
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
