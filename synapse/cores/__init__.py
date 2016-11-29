

class CortexLoader:
    def __init__(self, core, loadcore):
        for iden, _, _, _ in loadcore.getRowsByProp('tufo:form'):
            rows = loadcore.getRowsById(iden)
            core.addRows(rows)


class CortexSaver:
    def __init__(self, core, savecore, savefilter=None):
        if savefilter:
            def dist(evtfo):
                if savefilter(evtfo):
                    savecore.loadbus.dist(evtfo)
            core.savebus.link(dist)
        else:
            core.savebus.link(savecore.loadbus.dist)
