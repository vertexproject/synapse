from synapse.common import *

class Reactor:
    '''
    A class for registraction of one-to-one callbacks using
    synapse event tufo conventions.  Unlike an EventBus, only
    one action may be registered for a given event type and the
    function is expected to return a result.

    rtor = Reactor()

    def doFooBar(mesg):
        return 20 + mesg[1].get('x')

    rtor.act('foo:bar', doFooBar)

    y = rtor.react( tufo('foo:bar', x=30) )

    # y is now 50...

    '''
    def __init__(self):
        self.actfuncs = {}

    def act(self, name, func):
        '''
        Register a handler for an action by name.

        Example:

            rtor.act('foo:bar', doFooBar)

        '''
        self.actfuncs[name] = func

    def react(self, event):
        '''
        Dispatch to the handler and return his response.

        Example:

            resp = rtor.react(event)

        Notes:

            * Handler exceptions *will* propigate upward
        '''
        func = self.actfuncs.get(event[0])
        if func == None:
            raise NoSuchAct(event[0])

        return func(event)
