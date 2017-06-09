'''
Central API for configurable objects within synapse.
'''
from synapse.exc import *
from synapse.eventbus import EventBus
from synapse.datamodel import getTypeNorm

class Configable:

    '''
    Config object base mixin to allow addition to objects which already inherit
    from the EventBus.

    '''
    def __init__(self, opts=None, defs=()):
        self._conf_defs = {}
        self._conf_opts = {}

        self.addConfDefs(defs)

        if opts != None:
            self.setConfOpts(opts)

    def addConfDefs(self, defs):
        '''
        Add configuration definitions for this object.

        Example:

            defs = (
                ('caching',{'type':'bool','doc':'Enable caching on this object'}),
            )

            item.addConfDefs(defs)

        '''
        for name,info in defs:
            self.addConfDef(name,**info)

    def addConfDef(self, name, **info):
        self._conf_defs[name] = (name,dict(info))

        defval = info.get('defval')
        self._conf_opts.setdefault(name,defval)

        asloc = info.get('asloc')
        if asloc != None:
            self.__dict__.setdefault(asloc,defval)

    def reqConfOk(self, opts):
        '''
        Check that that config values pass validation or raise.
        '''
        for name,valu in opts.items():
            valu,_ = self.getConfNorm(name,valu)

    def getConfOpt(self, name):
        return self._conf_opts.get(name)

    def getConfDef(self, name):
        cdef = self._conf_defs.get(name)
        if cdef == None:
            raise NoSuchOpt(name=name)
        return cdef

    def getConfDefs(self):
        '''
        Returns the configuration definitions for this object.
        '''
        return { name:dict(info) for (name,info) in self._conf_defs.items() }

    def getConfNorm(self, name, valu):
        cdef = self.getConfDef(name)
        ctype = cdef[1].get('type')
        if ctype == None:
            return valu
        return getTypeNorm(ctype,valu)

    def setConfOpt(self, name, valu):
        '''
        Set a single config option for the object.
        '''
        oldval = self._conf_opts.get(name)

        cdef = self.getConfDef(name)

        ctype = cdef[1].get('type')
        if ctype != None:
            valu,_ = getTypeNorm(ctype,valu)

        if valu == oldval:
            return False

        asloc = cdef[1].get('asloc')
        if asloc != None:
            setattr(self,asloc,valu)

        self._conf_opts[name] = valu
        self._conf_defs[name][1]['valu'] = valu

        self.fire('syn:conf:set', name=name, valu=valu, oldval=oldval)
        self.fire('syn:conf:set:%s' % name, name=name, valu=valu, oldval=oldval)

    def setConfOpts(self, opts):
        '''
        Use settings from the given dict to update the object config.

        Example:

            opts = {
                'foo:enabled':True,
                'foo:size':1000
            }

            item.setConfOpts(opts)
        '''
        self.reqConfOk(opts)
        for name,valu in opts.items():
            self.setConfOpt(name,valu)

    def onConfOptSet(self, name, func):
        '''
        Utility function for dynamically handling updates to config options.

        Example:

            def setCacheEnabled(self, en):
                dostuff()

            item.onConfOptSet('caching',setCacheEnabled)

        '''
        def callback(mesg):
            valu = mesg[1].get('valu')
            return func(valu)

        self.on('syn:conf:set:%s' % name, callback)

class Config(Configable,EventBus):
    def __init__(self, opts=None, defs=()):
        EventBus.__init__(self)
        Configable.__init__(self,opts=opts,defs=defs)
