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

        # rst = s_t_changelog._generate_model_rst(change, new_model.get('model'))
