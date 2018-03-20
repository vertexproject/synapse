import synapse.lib.module as s_module

class SciMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'sci'
        return ((name, modl),)
