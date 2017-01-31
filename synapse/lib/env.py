'''
A unified place to declare/default/hook synapse env var loading.
'''
import os

import synapse.lib.threads as s_threads

declvars = {
    'SYN_USER_REGISTRY':{'doc':'Cortex URL for the user registry'},
}

globs = {
}

def get(name, defval=None):
    '''
    Return an environment variable or default.

    Example:

        foo = s_env.get('SYN_FOO')

    '''
    # thread local env first...
    synenv = s_threads.local('synenv',{})
    if synenv != None:

        valu = synenv.get(name)
        if valu != None:
            return valu

    # then check runtime globals
    valu = globs.get(name)
    if valu != None:
        return valu

    # then actual OS env
    valu = os.getenv(name)
    if valu != None:
        return valu

    # did the caller specify a defualt?
    if defval != None:
        return defval

    # Does the var have a default?
    vdef = declvars.get(name)
    if vdef != None:
        return vdef.get('defval')

    return None

def put(name,valu):
    '''
    Set global environement variable overrides.
    '''
    putenv = s_threads.local('synenv')
    if putenv == None:
        putenv = globs

    putenv[name] = valu

def scope():
    '''
    Construct a with-block for thread local env overrides.
    '''
    synenv = dict( s_threads.local('synenv',{}) )
    return s_threads.scope({'synenv':synenv})
