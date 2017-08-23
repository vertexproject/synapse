from synapse.lib.module import CoreModule

class BioMod(CoreModule):

    @staticmethod
    def getBaseModels():
        return (('bio', 0, {}), )
