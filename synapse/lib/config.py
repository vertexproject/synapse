'''
Tools for providing a central API for configurable objects within Synapse.
'''
import copy

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
    Config object base mixin to allow addition to objects which already inherit from the EventBus.
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
        Add multiple configuration definitions for this object via addConfDef().

        Args:
            defs ((str, dict),): A tuple containing multiple configuration definitions.

        Examples:
            Set a pair of options definitions related to caching on a object::

                defs = (
                    ('caching', {'type': 'bool', 'doc': 'Enable caching on this object'}),
                    ('cache:expiretime', {'type': 'int', 'doc': 'Time to expire data', 'defval': 60})
                )
                item.addConfDefs(defs)

        Notes:
            This does not have to be explicitly called if the @confdef decorator is used to define the options for a
            class.

        Returns:
            None
        '''
        for name, info in defs:
            self.addConfDef(name, **info)

    def addConfDef(self, name, **info):
        '''
        Add a configable option to the object.

        Args:
            name (str): Name of configuration option to set.
            **info: A list of options for the Configable option. The following options have specific meanings:
              - type: A Synapse type which is used to normalize the value.
              - doc: A docstring (used for doing automatic document generation within Synapse)
              - defval: A default value for the option.  This must be copyable using copy.deepcopy(). This is done to
                avoid mutable default values from being changed.
              - asloc: A string, if present, will set the a local object attribute to the name of the string which is
                equal to the valu of the configuration option.

        Examples:
            Add a definition for a option to a object with a local attribute::

                item.addConfDef('cache:expiretime', type='int',
                                doc='Time to expire data', defval=60,
                                asloc='cache_expiretime')

            Add a untype option definition to a object with a mutable defval. This sets the value to a copy of the
            defval, leaving the default object untouched::

                item.addConfDef('foobars', defval=[], doc='A list of foobars we care about.')

        Notes:
            This does not have to be explicitly called if the @confdef decorator is used to define the options for a
            class.

        Returns:
            None
        '''
        self._conf_defs[name] = (name, dict(info))

        defval = info.get('defval')
        self._conf_opts.setdefault(name, copy.deepcopy(defval))

        asloc = info.get('asloc')
        if asloc is not None:
            self.__dict__.setdefault(asloc, defval)

    def reqConfOk(self, opts):
        '''
        Check that that config values pass validation or raise.

        Args:
            opts (dict): Dictionary containing name, valu pairs to validate.

        Raises:
            NoSuchType: If the specified type of the option is non-existent.
            BadTypeValu: If a bad valu is encountered during type normalization.
        '''
        for name, valu in opts.items():
            valu, _ = self.getConfNorm(name, valu)

    def getConfOpt(self, name):
        '''
        Get the configured value for a given option.

        Args:
            name (str): Name of the option to retrieve.

        Returns:
            Value stored in the configuration dict, or None if the name is not present.
        '''
        return self._conf_opts.get(name)

    def getConfDef(self, name):
        '''
        Get the defitition for a given

        Args:
            name (str): Name to get the definition of.

        Returns:
            dict: Dictionary containing the configuration definition for the given named option.

        Raises:
            NoSuchOpt: If the name is not a valid option.
        '''
        cdef = self._conf_defs.get(name)
        if cdef is None:
            raise s_common.NoSuchOpt(name=name)
        return cdef

    def reqConfOpts(self):
        '''
        Check for the presense of required config options and raise if missing.

        Raises:
            ReqConfOpt
        '''
        for name, info in self._conf_defs.values():

            if not info.get('req'):
                continue

            if self._conf_opts.get(name) is None:
                raise s_common.ReqConfOpt(name=name)

    def getConfDefs(self):
        '''
        Get the configuration definitions for this object.

        Returns:
            dict: Dictionary of option, values for the object.
        '''
        return {name: dict(info[1]) for (name, info) in self._conf_defs.items()}

    def getConfOpts(self):
        '''
        Get the current configuration for this object.

        Returns:
            dict: Dictionary of option and configured value for the object.
        '''
        return {key: self.getConfOpt(key) for key, _ in self.getConfDefs().items()}

    def getConfNorm(self, name, valu):
        '''
        Return a normalized version of valu based on type knowledge for name.

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

        This will perform type normalization if the configration option has a 'type' value set.

        Args:
            name (str): Configuration name
            valu: Value to set to the configuration option.

        Notes:
            This fires the following events, so that the EventBus can react to configuration changes. Each event
            includes the name, new valu and oldvalu.

            - ``syn:conf:set``
            - ``syn:conf:set:<name>``

        Returns:
            None
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

        Args:
            opts (dict):

        Examples:
            Set a pair of keys on a object using a dictionary::

                opts = {
                    'foo:enabled': True,
                    'foo:size': 1000
                }
                item.setConfOpts(opts)

        Returns:
            None
        '''
        self.reqConfOk(opts)
        for name, valu in opts.items():
            self.setConfOpt(name, valu)

    def onConfOptSet(self, name, func):
        '''
        Utility function for dynamically handling updates to config options.

        Args:
            name (str): Option name to respond too.
            func: Function to execute.  This should take one parameter, the changed value.

        Examples:
            React to a (arbitrary) cache configuration option change::

                def setCacheEnabled(self, en):
                    dostuff()
                item.onConfOptSet('caching', setCacheEnabled)

        Notes:
            The callback is fired using the ``syn:conf:set:<name>`` event. Many places through Synapse (or third party
            applications which use Synapse) may set multiple opts at once using the setConfOpts() API, typically during
            a objects ``__init__`` function.  This sets values in a random order, due to dictionary iteration; and
            relying on other options being set during these callbacks can cause race conditions, leading to differences
            between expected and observed behaviors. In order to ensure that callbacks are free of such race conditions,
            do not write callback functions which rely on other Configable options being set to a particular value.

        Returns:
            None
        '''
        def callback(mesg):
            valu = mesg[1].get('valu')
            return func(valu)

        self.on('syn:conf:set:%s' % name, callback)

class Config(Configable, EventBus):
    '''
    A EventBus classs which has the Configable mixin already added.
    '''
    def __init__(self, opts=None, defs=()):
        EventBus.__init__(self)
        Configable.__init__(self, opts=opts, defs=defs)
