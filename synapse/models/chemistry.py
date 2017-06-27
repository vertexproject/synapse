from synapse.lib.module import CoreModule

class ChemMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'chem'
        return ((name, modl),)
