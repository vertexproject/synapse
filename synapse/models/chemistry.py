import synapse.lib.module as s_module

class ChemMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'chem'
        return ((name, modl),)
