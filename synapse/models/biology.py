import synapse.lib.module as s_module

class BioMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'bio'
        return ((name, modl),)
