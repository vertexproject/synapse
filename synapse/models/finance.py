from synapse.lib.module import CoreModule

def getDataModel():
    return FinMod.getBaseModels()[0][1]

class FinMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'finance'
        return ((name, modl),)
