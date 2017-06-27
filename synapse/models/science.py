from synapse.lib.module import CoreModule

class SciMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'sci'
        return ((name, modl),)
