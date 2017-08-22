import copy

import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
from synapse.tests.common import *
from synapse.membrane import Membrane

class MockCore():

    def __init__(self):
        self._splicecount = 0

    def splice(self, msg):
        self._splicecount += 1

splice_add = (
    'splice',
    {
        'time': 1503412197031, 'props': {'baz': 'faz'}, 'act': 'node:add',
        'user': None, 'valu': 'bar', 'form': 'foo'
    }
)
splice_add_tests = (
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '-food +foo'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True'
    ),
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '-food'}, {'query': '+foo'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True. 2 rules'
    ),
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '+food +foo'}]},
        False,
        False,
        'first filter: matching cant, return False'
    ),
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '+food'}, {'query': '+foo'}]},
        False,
        False,
        'first filter: matching cant, return False. 2 rules'
    ),
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '-food -foo'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: matching cant, return False'
    ),
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '-food'}, {'query': '-foo'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: matching cant, return False. 2 rules'
    ),
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '-food -foot'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: non-matching cant, continue. use default'
    ),
    (
        copy.deepcopy(splice_add),
        {'node:add': [{'query': '-food -foot'}]},
        True,
        True,
        'first filter: non-matching cant, continue. second filter: non-matching cant, continue. use default'
    ),
    (
        copy.deepcopy(splice_add),
        None,
        True,
        True,
        'no rules added. use default'
    ),
    (
        copy.deepcopy(splice_add),
        None,
        False,
        False,
        'no rules added. use default'
    ),
)

splice_prop = (
    'splice',
    {
        'time': 1503321381151, 'act': 'node:prop:set', 'form': 'foo', 'valu': 7, 'prop': 'baz',
        'node': ('a0a5363e76f09981135f50cc4805b1ad', {
                'foo:baz': 'lol', '.new': True, 'tufo:form': 'foo', 'foo': 'bar'
            }
        ),
        'user': None, 'newv': 'lol', 'oldv': 'faz'
    }
)
splice_prop_tests = (
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo'}]},
        False,
        False,
        'first filter: non-matching cant. second filter: doesnt match like w/ add since it looks at full prop.'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz=7'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz!=1337'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz=1337'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: failing must, return False'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz>7'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: failing must, return False'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz<6'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: failing must, return False'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz>=7'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: passes, return True'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food +foo:baz<=7'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: passes, return True'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food'}, {'query': '+foo:baz'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True. 2 rules'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '+food +foo:baz'}]},
        False,
        False,
        'first filter: matching cant, return False'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '+food'}, {'query': '+foo:baz'}]},
        False,
        False,
        'first filter: matching cant, return False. 2 rules'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food -foo:baz'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: matching cant, return False'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food'}, {'query': '-foo:baz'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: matching cant, return False. 2 rules'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food -foot:baz'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: non-matching cant, continue. use default'
    ),
    (
        copy.deepcopy(splice_prop),
        {'node:prop:set': [{'query': '-food -foot:baz'}]},
        True,
        True,
        'first filter: non-matching cant, continue. second filter: non-matching cant, continue. use default'
    ),
    (
        copy.deepcopy(splice_prop),
        None,
        True,
        True,
        'no rules added. use default'
    ),
    (
        copy.deepcopy(splice_prop),
        None,
        False,
        False,
        'no rules added. use default'
    ),
)

splice_tag = (
    'splice',
    {
        'form': 'foo', 'valu': 'bar', 'time': 1503362767955,
        'tag': 'hehe.hoho.haha', 'act': 'node:tag:add', 'user': None
    }
)

splice_tag_tests = (
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '-#nohere +#hehe.hoho.haha'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True'
    ),
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '-#nohere'}, {'query': '+#hehe.hoho.haha'}]},
        False,
        True,
        'first filter: non-matching cant, continue. second filter: matching must, return True. 2 rules'
    ),
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '+#nohere +#hehe.hoho.haha'}]},
        False,
        False,
        'first filter: matching cant, return False'
    ),
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '+#nohere'}, {'query': '+#hehe.hoho.haha'}]},
        False,
        False,
        'first filter: matching cant, return False. 2 rules'
    ),
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '-#nohere -#hehe.hoho.haha'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: matching cant, return False'
    ),
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '-#nohere'}, {'query': '-#hehe.hoho.haha'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: matching cant, return False. 2 rules'
    ),
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '-#nohere -#nothere'}]},
        False,
        False,
        'first filter: non-matching cant, continue. second filter: non-matching cant, continue. use default'
    ),
    (
        copy.deepcopy(splice_tag),
        {'node:tag:add': [{'query': '-#nohere -#nothere'}]},
        True,
        True,
        'first filter: non-matching cant, continue. second filter: non-matching cant, continue. use default'
    ),
    (
        copy.deepcopy(splice_tag),
        None,
        True,
        True,
        'no rules added. use default'
    ),
    (
        copy.deepcopy(splice_tag),
        None,
        False,
        False,
        'no rules added. use default'
    ),
)

class MembraneTest(SynTest):

    def _run_basic_tests(self, tests):
        for msg, rules, default, expected, explanation in tests:
            mc = MockCore()
            m = Membrane(mc, rules, default=default)
            try:
                self.eq(m.filter(msg), expected)
                self.eq(mc._splicecount, int(expected))
            except Exception as e:
                print(explanation)
                raise e

    def test_splice_add(self):
        self._run_basic_tests(splice_add_tests)

    def test_splice_prop(self):
        self._run_basic_tests(splice_prop_tests)

    def test_splice_tags(self):
        self._run_basic_tests(splice_tag_tests)

    def test_bad_msg(self):
        mc = MockCore()
        m = Membrane(mc, None, default=True)
        self.eq(m.filter('why'), None)
        self.eq(mc._splicecount, 0)

    def test_bad_rule(self):
        splice = copy.deepcopy(splice_add)
        rules = {'node:add': [{'query': 'foo'}]}
        mc = MockCore()
        m = Membrane(mc, rules, default=False)

        self.eq(m.filter(splice), False)
        self.eq(mc._splicecount, 0)

    def test_invalid_splice(self):
        badsplice = ('splice', {'act': 'node:add'})
        mc = MockCore()
        m = Membrane(mc, None, default=True)

        self.eq(m.filter(badsplice), True)
        self.eq(mc._splicecount, 1)

        m.default = False
        self.eq(m.filter(badsplice), False)
        self.eq(mc._splicecount, 1)

    def test_inbound_filter(self):

        # spin up and share a core
        with s_cortex.openurl('ram:///') as core:
            with s_daemon.Daemon() as dmon:
                dmon.share('core', core)
                link = dmon.listen('tcp://127.0.0.1:0/core')

                # form a proxy to the core we created, spin up a membrane and point it out our proxy
                with s_cortex.openurl('tcp://127.0.0.1:%d/core' % link[1]['port']) as prox:
                    rules = {'node:add': [{'query': '+foo'}]}
                    m = Membrane(prox, rules)

                    # fire some messages at the membrane then perform assertions on nodes in our code
                    msg = copy.deepcopy(splice_add)
                    m.filter(msg)
                    tufos = core.getTufosByProp('foo')
                    self.eq(len(tufos), 1)
                    self.eq(tufos[0][1]['foo:baz'], 'faz')

                    msg[1]['form'] = 'goo'
                    m.filter(msg)
                    tufos = core.getTufosByProp('goo')
                    self.eq(len(tufos), 0)

    def test_outbound_filter(self):

        # spin up a "local" and "remote" core, don't share either.
        # "remote" core is not directly accessible by "local" by any means.
        with s_cortex.openurl('ram:///') as remotecore:
            with s_cortex.openurl('ram:///') as mycore:
                with s_daemon.Daemon() as dmon:

                    # spin up and share a membrane pointed at our "local" core
                    rules = {'node:add': [{'query': '+inet:ipv4=1337'}]}
                    m = Membrane(mycore, rules)
                    dmon.share('membrane', m)
                    link = dmon.listen('tcp://127.0.0.1:0/membrane')

                    # form a proxy to our membrane
                    with s_cortex.openurl('tcp://127.0.0.1:%d/membrane' % link[1]['port']) as prox:

                        # set the "remote" core to fire splices at our telepath proxy to our membrane
                        remotecore.on('splice', prox.filter)

                        # form some nodes in the remote core, operating on it directly
                        remotecore.formTufoByProp('inet:ipv4', 1337)
                        remotecore.formTufoByProp('inet:ipv4', 7331)

                # assert that nodes matching our rules are present in our local core, operating on it directly
                tufo = mycore.getTufoByProp('inet:ipv4', 1337)
                self.nn(tufo)
                self.eq(tufo[1]['inet:ipv4'], 1337)

                # assert that filtered nodes are not present
                tufo = mycore.getTufoByProp('inet:ipv4', 7331)
                self.none(tufo)
