from synapse.lib.module import CoreModule

def getDataModel():
    return SciMod.getBaseModels()[0][1]

class SciMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'sci'
        return ((name, modl),)
