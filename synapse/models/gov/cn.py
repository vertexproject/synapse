from synapse.common import guid
import synapse.lib.module as s_module

class GovCnModule(s_module.CoreModule):
    def getModelDefs(self):
        return (
            ('gov:cn', {
                'types': (
                    ('gov:cn:icp', ('int', {}), {
                        'doc': 'A Chinese Internet Content Provider ID'}),
                    ('gov:cn:mucd', ('int', {}), {
                        'doc': 'A Chinese PLA MUCD'}),

                    #('gov:cn:orgicp', ('comp', {'fields': (('org': 'ou:org'), ('icp', 'gov:cn:icp'))}), {
                        #'doc': 'The assignment of a ICP number to a specific organization.'}),

                ),
                'forms': (
                    ('gov:cn:icp', {}, ()),
                    ('gov:cn:mucd', {}, ()),
                ),
            }),
        )
