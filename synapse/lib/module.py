import collections

import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath
import synapse.lib.reflect as s_reflect

import synapse.lib.config as s_config

def modelrev(name,vers):
    '''
    A decoarator used to flag model revision functions.
    '''
    def wrap(f):
        f._syn_mrev = (name,vers)
        return f
    return wrap

class CoreModule(s_eventbus.EventBus,s_config.Configable):
    '''
    The CoreModule base class from which cortex modules must extend.

    This module interface implements helper APIs to facilitate cortex
    extensions.

    To load a module within a cortex, add it to the list of modules in
    the cortex config ( mostly likely within your dmon config ) as shown:

    # example cortex config
    {
        "modules":[
            ["foopkg.barmod.modctor", {
                "foo:opt":10,
                "bar:opt":"http://www.vertex.link"
            }]
        ]
    }

    Modules may extend the cortex in various ways such as:

        * Implement and enforce data model additions
        * Enrich properties during node creation / modification
        * Add "by" handlers and side-pocket indexes to extend queries
        * Add custom storm/swarm operators to the query language
        * etc etc etc...

    NOTE: The cortex which loads the module plumbs all events into the
          CoreModule instance using EventBus.link().
    '''

    def __init__(self, core, conf):
        s_eventbus.EventBus.__init__(self)
        s_config.Configable.__init__(self)

        s_telepath.reqNotProxy(core)

        self.core = core
        core.link( self.dist )

        def fini():
            core.unlink(self.dist)

        self.onfini(fini)

        # check for decorated functions for model rev
        self._syn_mrevs = collections.defaultdict(list)
        for name,meth in s_reflect.getItemLocals(self):
            mrev = getattr(meth,'_syn_mrev',None)
            if mrev == None:
                continue

            name,vers = mrev
            self._syn_mrevs[name].append( (vers,meth) )

        # ensure the revs are in sequential order
        [ v.sort() for v in self._syn_mrevs.values() ]

        self.initCoreModule()
        self.setConfOpts(conf)

    def form(self, form, valu, **props):
        '''
        A module shortcut for core.formTufoByProp()

        Args:
            form (str): The node form to retrieve/create
            valu (obj): The node value
            **props:    Additional node properties

        '''
        return self.core.formTufoByProp(form, valu, **props)

    def initCoreModule(self):
        '''
        Module implementers may over-ride this method to initialize the
        module during initial construction.  Any exception raised within
        this method will be raised from the constructor and mark the module
        as failed.

        Args:

        Returns:
            (None)

        NOTE: If this method is implemented in a subclass, the subclass is
              responsible for calling the base implementation or revCoreModl()
        '''
        self.revCoreModl()

    def revCoreModl(self):
        '''
        Use modelrev decorated functions within this module to update the cortex.

        Returns:
            None
        '''
        for name,revs in self.genModlRevs():
            self.core.revModlVers(name,revs)

    def genModlRevs(self):
        '''
        Generate a list of ( name, revs ) tuples for model revisions in this module.

        Returns:
            ([ (str,[ (int,func), ... ]), ... ])

        Example:

            for name,revs in modu.genModlRevs():
                core.revModlVers(name,revs)

        '''
        retn = []
        for name,revs in self._syn_mrevs.items():
            retn.append((name,tuple(revs)))
        return retn

    def onFormNode(self, form, func):
        '''
        Register a callback to run during node formation.  This callback
        will be able to set properties on the node prior to construction.

        Args:
            form (str): The name of the node creation 
            func (function): A callback

        Returns:
            (None)

        Example:

            def myFormFunc(form, valu, props, mesg):
                props['foo:bar:baz'] = 10

            self.onFormNode('foo:bar', myFormFunc)

        NOTE: This may not be used for a module loaded with a remote cortex.
        '''
        def distfunc(mesg):
            form = mesg[1].get('form')
            valu = mesg[1].get('valu')
            props = mesg[1].get('props')

            return func(form, valu, props, mesg)

        def fini():
            self.core.off('node:form', distfunc)

        self.core.on('node:form', distfunc, form=form)
        self.onfini(fini)

    # TODO: many more helper functions which wrap event conventions with APIs go here...
