'''
The synapse registry persists system and user data.
'''
import os

import synapse
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.dyndeps as s_dyndeps

import synapse.lib.modules as s_modules

from synapse.eventbus import EventBus

syndir = os.path.dirname(synapse.__file__)
syspath = s_common.genpath(syndir,'registry.db')
userpath = s_common.genpath('~','.syn','registry.db')

sysurl = os.getenv('SYNAPSE_SYSTEM_REGISTRY')
if sysurl == None and os.path.isfile(syspath):
    sysurl = 'sqlite:///%s' % syspath

userurl = os.getenv('SYNAPSE_USER_REGISTRY')
if userurl == None and os.path.isfile(userpath):
    userurl = 'sqlite:///%s' % userpath

sysreg = None
userreg = None

def getUserReg():
    '''
    Open and return the users registry.
    '''
    return openurl(userurl)

def getSysReg():
    '''
    Open and return the system registry.
    '''
    if sysurl == None:
        return None

    return openurl(syurl)

def openurl(url,**opts):
    core = s_cortex.openurl(url,**opts)
    return Registry(core)

class Registry(EventBus):

    def __init__(self, core):
        EventBus.__init__(self)
        self.core = core

        self.onfini( self.core.fini )

    def addSynMod(self, name):
        '''
        Add a python module by name as a synapse module.

        Example:

            ureg = getUserReg()
            ureg.addSynMod('foo.bar.baz')

        '''
        smod = loadSynMod(name)
        self.core.formTufoByProp('syn:module', name)

    def getSynMods(self):
        '''
        Return a list of syn:module tufos.
        '''
        return self.core.getTufosByProp('syn:module')

    def loadSynMods(self):
        '''
        Load the registered synapse modules from this registry.
        '''
        ret = []
        for mofo in self.getSynMods():

            name = mofo[1].get('syn:module')
            try:
                smod = s_modules.load(name)
                ret.append( (name,smod,None) )

            except Exception as e:
                ret.append( (name,None,e) )

        return ret

