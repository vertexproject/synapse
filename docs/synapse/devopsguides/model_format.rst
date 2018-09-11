CoreModule: Model Definitions
#############################

Quick Start
-----------

This is intended as a reference for developers working on Synapse who are creating, or adding models to the base models
or for developers who are looking to extend Synapse for their own use by the creation of new models.

This is not intended as a 'how-to' guide for Synapse hypergraph modeling, rather a document for how models may be
defined and loaded into a Cortex.

Models As Code
--------------

The the core models used in Synapse hypergraph implementations are a part of the codebase which makes up Synapse.
This allows the model definitions to grow along with the codebase over time.  One feature we have in Synapse is the
ability to track model revisions over time. By using the Cortex extensions class, CoreModule, we can implement our
modules, and specific handlers for them, and migration steps over time in a single place.  By placing some
conventions around how the CoreModule is used for modeling, we can ensure consistency across the Cortex, DataModel
and TypeLib classes; as well as ensuring that consistent data migrations are available to Cortex users.

An example of a simple model definition file is the following ::

    import synapse.lib.module as s_module

    class FooBarModule(s_module.CoreModule):

        # getBaseModels is a method designed to be overridden in
        # CoreModules which implement Synapse models.  It must return
        # an iterable of name, model tuples.
        @staticmethod
        def getBaseModels():
            modl = {
                'types': (
                    ('foo:bar', {'subof': 'str', 'doc': 'A foo bar!'}),
                ),
                'forms': (
                    ('foo:bar',
                     {'ptype': 'foo:bar'},
                     [])
                )
            }
            name = 'foobar'
            return ((name, modl), )

This example module inherits from the the Synapse CoreModule. The initial model is defined as a tuple of (name, dict)
pairs; which are returned by the getBaseModels() function.  One @staticmethod, getBaseModels, is defined which returns
a iterable of name, model tuples. This serves two purposes:

  #. The @staticmethod nature of the getBaseModels function allows for the data model to directly available.
     This allows the path to be loaded as a dynamic Synapse module; which is used by the TypeLib and DataModel
     classes.  This way, those classes may always have the latest versions of the model available.

  #. Upon loading the the CoreModule implementation into a Cortex, each name & model pair is considered as the
     'revision 0' for that named model.  This allows new Cortexes to always be created with the latest base model.
     On existing Cortexes which do not have nodes storing the model revision, the revision 0 of the model will be
     created and the base model automatically loaded.

When model updates need to be done, these updates are to be delivered as functions in the CoreModule sublcass. These
functions must be decorated with the @s_module.modelrev function.  This decorator takes two arguments:

  #. The name of the model to be updated.
  #. The timestamp of the model revision, in integer form.  This is validated using the "%Y%m%d%H%M" format string.

These decorated functions should implement any changes neccesary for the data model; and perform any neccesary data
migrations.  For performance reasons, these migrations should be performed using the **storage layer** APIs.  The use
of node (tufo) level APIs when doing data migrations may result in terrible performance, causing migrations to take
a significant amount of time.

Under the hood, when the model is loaded by the Cortex, the rev0 function and any @modelrev decorated functions are
sorted by model version, and these functions are then executed when CoreModule initialization is completed. This has
the following effects:

    - On new Cortexes, the rev0 function will be loaded (adding the complete data model). Then subsequent functions
      will be executed.  These should perform any model changes and data migrations as needed.
    - On existing Cortexes which have already had the base model loaded; the rev0 function will be skipped and
      subsequent functions executed until the last function has been executed.  These functions should perform a model
      addition of the basemodel contents, and perform any required migration actions using the **storage layer** APIs.

The following is a second revision of the earlier FooBarModule - it add a property for the foo:bar type, and performs
a storage layer migration of nodes to set a default value for the new property. The model revision for the foobar model
will be updated to 201707210101 in the Cortex.::

    import synapse.lib.module as s_module

    class FooBarModule(s_module.CoreModule):

        @staticmethod
        def getBaseModels():
            modl = {
                'types': (
                    ('foo:bar', {'subof': 'str', 'doc': 'A foo bar!'}),
                ),
                'forms': (
                    ('foo:bar',
                     {'ptype': 'foo:bar'},
                     [('duck', {'defval': 'mallard', 'ptype': 'str', 'doc': 'Duck type.'})]
                     ),
                ),
            }
            name = 'foobar'
            return ((name, modl), )

        @s_module.modelrev('foobar', 201707210101)
        def _testRev1(self):
            '''
            This revision adds the 'duck' property to our foo:bar nodes with its default value.
            '''
            self.core.addPropDef('foo:bar:duck', form='foo:bar', defval='mallard', ptype='str', doc='Duck value!')
            # Now lets migrate existing nodes to accommodate model changes.
            rows = []
            tick = s_common.now()
            for iden, p, v, t in self.core.getRowsByProp('foo:bar'):
                rows.append((iden, 'foo:bar:duck', 'mallard', tick))
            self.core.addRows(rows)

It is highly encouraged for model developers to write unit tests for any migrations which they do, in order to ensure
that their migration functions are working correctly.

Advanced CoreModule Usage
-------------------------

The CoreModule class can also be used to extend the functionality of the Cortex beyond simply adding additional model
definitions. The CoreModule has access to the Cortex is loaded with, for example, we can use it to add additional
event handlers; type casts; or other functionality. The Cortex on method (from eventbus.py) can be used to quickly strap
in additional actions, and the CoreModule class itself has specific event helpers as well (with more coming soon).
An example of extending the previous example is shown below (minus migration functions). ::

    import logging
    import synpase.eventbus as s_eventbus
    import synapse.lib.module as s_module

    logger = logging.getLogger(__name__)

    class FooBarModule(s_module.CoreModule):

        # Override the default initCoreModule function
        async def initCoreModule(self):

            # Define a function used for helping out during node creation.
            self.onFormNode('foo:knight', self.onTufoFormKnight)

            # Calling self.revCoreModl() is required by classes which override
            # initCoreModule and define module revisions.
            self.revCoreModl()

        def onTufoFormKnight(self, form, valu, props, mesg):
            if valu in ['erec', 'lancelot', 'blumenthal']:
                props['foo:knight:court'] = 'round table'

        # Use an eventhandler to do an action during the property set.
        @s_eventbus.on('node:prop:set', prop='foo:bar:duck')
        def onTufoSetDuck(self, mesg):
            newv = mesg[1].get('newv')
            for tufo in self.core.getTufosByProp('foo:bar:duck', newv):
                msg = 'Already seen duck {} on {}'.format(newv, tufo[1].get('foo:bar'))
                logger.info(msg)

        @staticmethod
        def getBaseModels():
            modl = {
                'types': (
                    ('foo:bar', {'subof': 'str', 'doc': 'A foo bar!'}),
                    ('foo:knight', {'subof': 'str', 'doc': 'A knight!'}
                ),
                'forms': (
                    ('foo:bar',
                     {'ptype': 'foo:bar'},
                     [('duck', {'defval': 'mallard', 'ptype': 'str', 'doc': 'Duck type.'})]
                     ),
                    ('foo:knight',
                     {'ptype': 'foo:knight'},
                     [('court', {'ptype': 'str', 'doc': 'Knight court'})]
                     ),
                ),
            }
            name = 'foobar'
            return ((name, modl), )

This example shows the overriding of the initCoreModule() function, which registers a single function as a helper
during node creation, and calls the revCoreModl() to cache the model revision functions for model initalization use by
the Cortex.  The helper is used to set a secondary property based on the primary property of the node.  In addition,
the @s_eventbus.on decorator is used to perform any action when an event is fired in the Cortex attached to the class.
In the example, a message is logged; but other data could be retrieved, or looked up or modified; etc.

Core Synapse Model Conventions
------------------------------

The core Synapse modules are defined in the synapse/__init__.py file, in the BASE_MODELS list.  This is a list of
tuple values; containing the path to the CoreModule ctor, and the options.  The base modules typically do not have
options in them.  New modules which contain new models should be added to the BASE_MODELs list.

During the import process of Synapse, the python modules will be loaded and cached by the
synapse.lib.modules.load_ctor() function. In addition, any ctors present in the environmental variable
SYN_CORE_MODULES will also be loaded. The models contained in these ctors will be used to populate model information
for instances of the TypeLib and DataModel classes, as well as serve as the CoreModules loaded into Cortexes upon
creation.

The convention for CoreModules which implement data models within the core Synapse codebase shall maintain a
single CoreModule subclass per file, and this subclass will be responsible for maintaining a single named model.

Gotchas
-------

The following modeling gotchas exist:

  - The implementation of getBaseModels should be a @staticMethod, since it may be called directly by TypeLib or
    DataModel creation if the ctor has been loaded by synapse.lib.modules.load_ctor().
  - It is possible for a single CoreModule to implement multiple named models, and revision them separately with
    @s_module.modelrev() decorators. The core Synapse modules will not be implemented in such a manner for the sake
    of simplicity in the codebase.
  - While it is possible for the model revision functions to simply add the base model data; it should really only
    do the changes neccesary to support the model changes. Currently, there are self.core.addTufoForm,
    self.core.addPropDef, and self.core.addType functions available for doing model additions. These functions may
    throw exceptions - see their docstrings for more information.  We anticipate adding additional functions for doing
    removal of types, forms and props soon.

