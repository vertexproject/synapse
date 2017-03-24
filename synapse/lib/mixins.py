import collections

import synapse.dyndeps as s_dyndeps

def ldict():
    return collections.defaultdict(list)

mixins = collections.defaultdict(ldict)

#tele_mixins = collections.defaultdict(list)
#core_mixins = collections.defaultdict(list)

def addSynMixin(subsys, name, cname=None):
    '''
    Add a mixin class to the specified subsystem.

    Example:

        s_mixins.addSynMixin('telepath','synapse.axon.AxonMixin')

    '''
    if cname == None:
        cname = name
    mixins[subsys][name].append(cname)

def getSynMixins(subsys,name):
    '''
    Return a list of mixin classes for the given subsystem class.

    Example:

        for clas in getSynMixins('telepath','foo.bar.Baz'):
            dostuff()

    '''
    names = mixins[subsys].get(name,())
    if not names:
        return ()
    return [ s_dyndeps.getDynLocal(name) for name in names ]

#addTeleMixin('synapse.axon.AxonMixin')
