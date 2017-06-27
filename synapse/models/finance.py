from synapse.lib.module import CoreModule

class FinMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'finance'
        return ((name, modl),)
