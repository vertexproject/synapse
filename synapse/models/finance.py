import synapse.lib.module as s_module

class FinMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'finance'
        return ((name, modl),)
