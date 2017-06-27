from synapse.lib.module import CoreModule

class BioMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'bio'
        return ((name, modl),)
