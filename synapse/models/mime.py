from synapse.lib.module import CoreModule

class MimeMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'mime'
        return ((name, 0, modl),)
