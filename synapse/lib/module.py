import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.config as s_config

class CoreModule(s_eventbus.EventBus,s_config.Configable):
    '''
    The CoreModule base class from which cortex modules must extend.

    This module interface implements helper APIs to facilitate cortex
    extensions.  It is highly encouraged

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
    '''

    def __init__(self, core, conf):
        s_eventbus.EventBus.__init__(self)
        s_config.Configable.__init__(self)

        s_telepath.reqNotProxy(core)

        self.core = core

        self.setConfOpts(conf)

        self.initCoreModule()

    def initCoreModule(self):
        '''
        Module implementers may over-ride this method to initialize the
        module during initial construction.  Any exception raised within
        this method will be raised from the constructor and mark the module
        as failed.

        Args:

        Returns:
            (None)
        '''
        pass

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
        evnt = 'tufo:form:' + form

        def distfunc(mesg):
            form = mesg[1].get('form')
            valu = mesg[1].get('valu')
            props = mesg[1].get('props')

            return func(form, valu, props, mesg)

        def fini():
            self.core.off(evnt, distfunc)

        self.core.on(evnt, distfunc)
        self.onfini(fini)

    # TODO: many more helper functions which wrap event conventions with APIs go here...
