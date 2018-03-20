import synapse.lib.module as s_module

class MoneyMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {}
        name = 'money'
        return ((name, modl),)
