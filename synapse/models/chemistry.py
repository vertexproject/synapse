from synapse.lib.module import CoreModule

def getDataModel():
    return ChemMod.getBaseModels()[0][1]

class ChemMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'chem'
        return ((name, modl),)
