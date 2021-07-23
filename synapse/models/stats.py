import synapse.lib.module as s_module

class StatsModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'types': (
                ('stats:sampleset', ('guid', {}), {
                    'doc': 'A GUID representing a statistical sample set.',
                }),
                ('stats:sample', ('guid', {}), {
                    'doc': 'A GUID representing a statistical sample.',
                }),
            ),
            'forms': (
                ('stats:sampleset', {}, (
                    ('name', ('str', {}), {
                        'doc': 'The name of the sample set.'}),
                    ('type', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                        'ex': 'histo',
                        'doc': 'The type of sample set.'}),
                    ('desc', ('str', {}), {
                        'doc': 'A prose description of the nature of the sample set.'}),
                )),
                ('stats:sample', {}, (
                    ('seqn', ('identick', {'subnames': ('set', 'time')}), {
                        'doc': 'A compound (<iden>, <time>) value used to order samples in a set.'}),
                    ('seqn:set', ('stats:sampleset', {}), {
                        'doc': 'The sample set this sample belongs to.'}),
                    ('seqn:time', ('time', {}), {
                        'doc': 'The time of the sample population.'}),
                    ('min', ('hugenum', {}), {
                        'doc': 'The smallest value from the population.'}),
                    ('max', ('hugenum', {}), {
                        'doc': 'The largest value from the population.'}),
                    ('size', ('hugenum', {}), {
                        'doc': 'The number of values in the population.'}),
                    ('sum', ('hugenum', {}), {
                        'doc': 'The sum of the values from the population.'}),
                    ('mean', ('hugenum', {}), {
                        'doc': 'The mean of the values from the population.'}),
                )),
            )
        }
        return (('stats', modl),)
