import copy

import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
from synapse.tests.common import *
from synapse.membrane import Membrane

class MockCore():

    def __init__(self):
        self._splicecount = 0

    def on(self, name, mesg):
        pass

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
            src = MockCore()
            dst = MockCore()
            m = Membrane(src, dst, rules=rules, default=default)
            try:
                self.eq(m.filter(msg), expected)
                self.eq(dst._splicecount, int(expected))
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
        self.raises(AttributeError, m.filter, 'why')
        self.eq(mc._splicecount, 0)

    def test_bad_rule(self):
        splice = copy.deepcopy(splice_add)
        rules = {'node:add': [{'query': 'foo'}]}
        src = MockCore()
        dst = MockCore()
        m = Membrane(src, dst, rules=rules, default=False)

        self.eq(m.filter(splice), False)
        self.eq(dst._splicecount, 0)

    def test_invalid_splice(self):
        badsplice = ('splice', {'act': 'node:add'})
        src = MockCore()
        dst = MockCore()
        m = Membrane(src, dst, default=True)

        self.eq(m.filter(badsplice), True)
        self.eq(dst._splicecount, 1)

        m.default = False
        self.eq(m.filter(badsplice), False)
        self.eq(dst._splicecount, 1)

    def _filter_add_nodes(self, core):
        core.formTufoByProp('inet:ipv4', 1337)
        core.formTufoByProp('inet:ipv4', 7331)

    def _filter_run_assertions(self, core):

        tufo = core.getTufoByProp('inet:ipv4', 1337)
        self.nn(tufo)
        self.eq(tufo[1]['inet:ipv4'], 1337)

        tufo = core.getTufoByProp('inet:ipv4', 7331)
        self.none(tufo)

    def test_filter_inbound_from_shared(self):

        # remotecore: the core we want to get splices from, shared over telepath via dmon
        # ourcore: the core we want to sync splices to, just a local ramcore
        # prox: our telepath proxy to remotecore

        hitcount = 1
        rules = {
            'node:add': [
                {'query': '+inet:ipv4=1337'}
            ]
        }

        with s_cortex.openurl('ram:///') as ourcore:
            with s_cortex.openurl('ram:///') as remotecore:
                with s_daemon.Daemon() as dmon:
                    dmon.share('remotecore', remotecore)
                    link = dmon.listen('tcp://127.0.0.1:0/remotecore')

                    waiter = ourcore.waiter(hitcount, 'splice')
                    with s_cortex.openurl('tcp://127.0.0.1:%d/remotecore' % link[1]['port']) as prox:
                        m = Membrane(src=prox, dst=ourcore, rules=rules)
                        self._filter_add_nodes(prox)
                        waiter.wait(timeout=10)  # give enough time for events to propagate
                        self._filter_run_assertions(ourcore)

    def test_filter_outbound_to_shared(self):

        # remotecore: the core we want to sync splices to, shared over telepath via dmon
        # ourcore: the core we want to sync splices from, just a local ramcore
        # prox: our telepath proxy to remotecore

        hitcount = 1
        rules = {
            'node:add': [
                {'query': '+inet:ipv4=1337'}
            ]
        }

        with s_cortex.openurl('ram:///') as ourcore:
            with s_cortex.openurl('ram:///') as remotecore:
                with s_daemon.Daemon() as dmon:
                    dmon.share('remotecore', remotecore)
                    link = dmon.listen('tcp://127.0.0.1:0/remotecore')

                    waiter = remotecore.waiter(hitcount, 'splice')
                    with s_cortex.openurl('tcp://127.0.0.1:%d/remotecore' % link[1]['port']) as prox:
                        m = Membrane(src=ourcore, dst=prox, rules=rules)
                        self._filter_add_nodes(ourcore)
                        waiter.wait(timeout=10)  # give enough time for events to propagate
                        self._filter_run_assertions(prox)

    def test_filter_inbound_from_unshared(self):

        # remotecore: the core we want to sync splices to, not shared
        # remotemembrane: the membrane attached to remote core, shared over telepath
        # ourcore: the core we want to sync splices from, just a local ramcore
        # prox: our telepath proxy to remotemembrane

        hitcount = 1
        rules = {
            'node:add': [
                {'query': '+inet:ipv4=1337'}
            ]
        }

        with s_cortex.openurl('ram:///') as ourcore:
            with s_cortex.openurl('ram:///') as remotecore:
                with s_daemon.Daemon() as dmon:
                    remotemembrane = Membrane(src=remotecore, rules=rules)
                    dmon.share('remotemembrane', remotemembrane)
                    link = dmon.listen('tcp://127.0.0.1:0/remotemembrane')

                    waiter = ourcore.waiter(hitcount, 'splice')
                    with s_cortex.openurl('tcp://127.0.0.1:%d/remotemembrane' % link[1]['port']) as prox:
                        prox.on('splice', ourcore.splice)  # FIXME not sure how to do this in dmon conf
                        self._filter_add_nodes(remotecore)
                        waiter.wait(timeout=10)  # give enough time for events to propagate
                        self._filter_run_assertions(ourcore)

    def test_filter_outbound_to_unshared(self):

        # remotecore: the core we want to sync splices to, not shared
        # remotemembrane: the membrane attached to remote core, shared over telepath
        # ourcore: the core we want to sync splices from, just a local ramcore
        # ourmembrane: our membrane
        # prox: our telepath proxy to remotemembrane

        hitcount = 1
        rules = {
            'node:add': [
                {'query': '+inet:ipv4=1337'}
            ]
        }

        with s_cortex.openurl('ram:///') as ourcore:
            with s_cortex.openurl('ram:///') as remotecore:
                with s_daemon.Daemon() as dmon:
                    remotemembrane = Membrane(dst=remotecore, rules=rules)
                    dmon.share('remotemembrane', remotemembrane)
                    link = dmon.listen('tcp://127.0.0.1:0/remotemembrane')

                    waiter = ourcore.waiter(hitcount, 'splice')
                    with s_cortex.openurl('tcp://127.0.0.1:%d/remotemembrane' % link[1]['port']) as prox:
                        ourmembrane = Membrane(src=ourcore, dst=prox, rules=rules)
                        self._filter_add_nodes(ourcore)
                        waiter.wait(timeout=10)  # give enough time for events to propagate
                        self._filter_run_assertions(remotecore)
