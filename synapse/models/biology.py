from synapse.lib.module import CoreModule

def getDataModel():
    return BioMod.getBaseModels()[0][1]

class BioMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'bio'
        return ((name, modl),)
