import io
import unittest

from synapse.statemach import StateMachine, keepstate

from synapse.tests.common import *

class StateMachTest(SynTest):

    def getFooMachine(self, fd):
        class Foo(StateMachine):
            def __init__(self, statefd=None):
                self.stuff = {}

                StateMachine.__init__(self, statefd=statefd)

            @keepstate
            def setthing(self, name, valu):
                self.stuff[name] = valu
                return valu

        return Foo(statefd=fd)

    def test_statemach_loadnsave(self):

        fd = io.BytesIO()
        foo = self.getFooMachine(fd)

        foo.setthing('woot', 20)

        self.eq(foo.stuff.get('woot'), 20)

        fd.seek(0)

        foo = self.getFooMachine(fd)
        self.eq(foo.stuff.get('woot'), 20)

    def test_statemach_nofd(self):
        foo = self.getFooMachine(None)
        self.eq(foo.setthing('foo', 20), 20)
