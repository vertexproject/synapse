'''
Central API for configurable objects within synapse.
'''
import collections

import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.reflect as s_reflect

from synapse.eventbus import EventBus

def confdef(name):
    '''
    A decorator used to flag configable definition functions.

    The options returned by the decorated functions are automatically loaded
    into the class upon initialization of the Configable mixin. This decorator
    must be used AFTER a @staticmethod decorator for autodoc generation to
    work properly.

    Args:
        name (str): Identifier for a given function. This is used to prevent
            reloading configable options multiple times in the case
            of multi-class inheritance or mixin use.

    Examples:
        Example class using the confdef decorator to define and (automatically
        load) a set of options into a Configable class::

            class Foo(s_config.Config):

                @staticmethod
                @s_config.confdef(name='foo')
                def foodefs():
                    defs = (
                        ('fooval', {'type': 'int', 'doc': 'what is foo val?', 'defval': 99}),
                        ('enabled', {'type': 'bool', 'doc': 'is thing enabled?', 'defval': 0}),
                    )
                    return defs
    '''
    def wrap(f):
        f._syn_config = name
        return f

    return wrap

class Configable:

    '''
    Config object base mixin to allow addition to objects which already inherit
    from the EventBus.

    '''
    def __init__(self, opts=None, defs=()):
        self._conf_defs = {}
        self._conf_opts = {}
        self._syn_confs = []
        self._syn_loaded_confs = set([])

        self.addConfDefs(defs)

        if opts is not None:
            self.setConfOpts(opts)
        self._loadDecoratedFuncs()

    def _loadDecoratedFuncs(self):

        for name, meth in s_reflect.getItemLocals(self):
            # Telepath will attempt to give you callable Method for any attr
            # you ask for which will end poorly for us when we try to call it
            if s_telepath.isProxy(meth):
                continue
            attr = getattr(meth, '_syn_config', None)
            if attr is None:
                continue
            self._syn_confs.append((attr, meth))

        for attr, meth in self._syn_confs:
            if attr in self._syn_loaded_confs:
                continue
            self.addConfDefs(meth())
            self._syn_loaded_confs.add(attr)

    def addConfDefs(self, defs):
        '''
        Add configuration definitions for this object.

        Example:

            defs = (
                ('caching',{'type':'bool','doc':'Enable caching on this object'}),
            )

            item.addConfDefs(defs)

        '''
        for name, info in defs:
            self.addConfDef(name, **info)

    def addConfDef(self, name, **info):
        self._conf_defs[name] = (name, dict(info))

        defval = info.get('defval')
        self._conf_opts.setdefault(name, defval)

        asloc = info.get('asloc')
        if asloc is not None:
            self.__dict__.setdefault(asloc, defval)

    def reqConfOk(self, opts):
        '''
        Check that that config values pass validation or raise.
        '''
        for name, valu in opts.items():
            valu, _ = self.getConfNorm(name, valu)

    def getConfOpt(self, name):
        return self._conf_opts.get(name)

    def getConfDef(self, name):
        cdef = self._conf_defs.get(name)
        if cdef is None:
            raise s_common.NoSuchOpt(name=name)
        return cdef

    def getConfDefs(self):
        '''
        Returns the configuration definitions for this object.
        '''
        return {name: dict(info) for (name, info) in self._conf_defs.items()}

    def getConfNorm(self, name, valu):
        '''
        Return a no.rmalized version of valu based on type knowledge for name.

        Args:
            name (str): The name of the config option
            valu (obj): The valu of the config option

        Returns:
            (obj):  The normalized form for valu

        '''
        cdef = self.getConfDef(name)
        ctype = cdef[1].get('type')
        if ctype is None:
            return valu, {}
        return s_datamodel.getTypeNorm(ctype, valu)

    def setConfOpt(self, name, valu):
        '''
        Set a single config option for the object.
        '''
        oldval = self._conf_opts.get(name)

        cdef = self.getConfDef(name)

        ctype = cdef[1].get('type')
        if ctype is not None:
            valu, _ = s_datamodel.getTypeNorm(ctype, valu)

        if valu == oldval:
            return False

        asloc = cdef[1].get('asloc')
        if asloc is not None:
            setattr(self, asloc, valu)

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
        for name, valu in opts.items():
            self.setConfOpt(name, valu)

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

class Config(Configable, EventBus):
    def __init__(self, opts=None, defs=()):
        EventBus.__init__(self)
        Configable.__init__(self, opts=opts, defs=defs)
