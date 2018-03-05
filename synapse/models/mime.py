import synapse.lib.module as s_module

class MimeMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'mime'
        return ((name, modl),)
