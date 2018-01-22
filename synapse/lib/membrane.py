import synapse.eventbus as s_eventbus

import synapse.lib.auth as s_auth

class Membrane(s_eventbus.EventBus):
    '''
    A Membrane instance is an event filter that calls a
    function for messages that pass through.
    '''
    def __init__(self, name, rules, fn):
        s_eventbus.EventBus.__init__(self)

        self.name = name
        self.rules = s_auth.Rules(rules)
        self.fn = fn

    def filt(self, mesg):
        '''
        Filter a message and call the Membrane instance's function if
        the message passes.

        Args:
            mesg ((str, dict)): The given message to filter.

        Notes:
            Messages that are not explicitly allowed or denied will be dropped.

        Returns:
            The return value of calling the given function.
        '''
        if self.rules.allow(mesg):
            return self.fn(mesg)
