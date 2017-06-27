from synapse.lib.module import CoreModule, modelrev

class CsciMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('csci:host', {'subof': 'guid'}),
                ('csci:hostfile', {'subof': 'guid'}),
            ),

            'forms': (
                ('csci:hostfile', {'ptype': 'csci:hostfile'}, [
                ]),
            ),
        }
        name = 'csci'
        return ((name, modl), )
