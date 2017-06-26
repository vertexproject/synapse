from synapse.lib.module import CoreModule

def getDataModel():
    return MoneyMod.getBaseModels()[0][1]

class MoneyMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'money'
        return ((name, modl),)
