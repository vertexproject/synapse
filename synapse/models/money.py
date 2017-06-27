from synapse.lib.module import CoreModule

class MoneyMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'money'
        return ((name, modl),)
