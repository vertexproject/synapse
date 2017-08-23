from synapse.lib.module import CoreModule

class FinMod(CoreModule):

    @staticmethod
    def getBaseModels():
        return (('finance', 0, {}), )
