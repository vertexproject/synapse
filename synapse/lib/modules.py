'''
Module which implements the synapse module API/convention.
'''
import logging

import synapse.dyndeps as s_dyndeps

logger = logging.getLogger(__name__)

synmods = {}
modlist = []

def call(name, *args, **kwargs):
    '''
    Call the given function on all loaded synapse modules.

    Returns a list of name,ret,exc tuples where each module
    which implements the given function returns either ret on
    successful execution or exc in the event of an exception.

    Example:

        import synapse.lib.modules as s_modules
        for name,ret,exc in s_modules.call('getFooByBar',bar):
            dostuff()

    '''
    ret = []
    for sname,smod in modlist:
        func = getattr(smod,name,None)
        if func == None:
            continue

        try:
            val = func(*args,**kwargs)
            ret.append( (sname,val,None) )

        except Exception as e:
            ret.append( (sname,None,e) )

    #print('call: %r %r %r %r' % (name,args,kwargs,ret))
    return ret

def load(name):
    '''
    Load the given python module path as a synapse module.

    Example:

        import synapse.lib.modules as s_modules
        s_modules.load('foopkg.barmod')

    '''
    smod = synmods.get(name)
    if smod == None:
        logger.info('loading syn mod: %s', name)
        smod = s_dyndeps.tryDynMod(name)
        synmods[name] = smod
        modlist.append( (name,smod) )
    return smod

