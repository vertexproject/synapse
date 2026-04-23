import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.parser as s_parser
import synapse.lib.msgpack as s_msgpack
import synapse.lib.processpool as s_processpool

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

def raiseNoSuchForm(name, mesg=None):
    raise s_exc.NoSuchForm.init(name, mesg)

class ExcTest(s_t_utils.SynTest):
    def test_basic(self):
        e = s_exc.SynErr(mesg='words', foo='bar')
        self.eq(e.get('foo'), 'bar')
        self.eq(e.items(), {'mesg': 'words', 'foo': 'bar'})
        self.eq("SynErr: foo='bar' mesg='words'", str(e))
        e.set('hehe', 1234)
        e.set('foo', 'words')
        self.eq("SynErr: foo='words' hehe=1234 mesg='words'", str(e))

        e.setdefault('defv', 1)
        self.eq("SynErr: defv=1 foo='words' hehe=1234 mesg='words'", str(e))

        e.setdefault('defv', 2)
        self.eq("SynErr: defv=1 foo='words' hehe=1234 mesg='words'", str(e))

        e.update({'foo': 'newwords', 'bar': 'baz'})
        self.eq("SynErr: bar='baz' defv=1 foo='newwords' hehe=1234 mesg='words'", str(e))

        self.eq(e.errname, 'SynErr')

        e2 = s_exc.BadTypeValu(mesg='haha')
        self.eq(e2.errname, 'BadTypeValu')

    async def test_pickled_synerr(self):
        with self.raises(s_exc.BadSyntax) as cm:
            _ = await s_parser._forkedParseEval('| | | ')
        self.isin('BadSyntax', str(cm.exception))
        self.isin('Unexpected token', str(cm.exception))

        # init() pattern
        with self.raises(s_exc.NoSuchForm) as cm:
            await s_processpool.forked(raiseNoSuchForm, 'test:newp', mesg='test:newp pickle!')
        self.isin('NoSuchForm', str(cm.exception))
        self.isin('test:newp pickle', str(cm.exception))

    def test_stormraise(self):
        e = s_exc.StormRaise(mesg='hehe', errname='fooErr', info={'key': 'valu'})
        self.eq(e.errname, 'fooErr')

        with self.raises(s_exc.BadArg):
            s_exc.StormRaise(mesg='newp')

    async def test_reprexc(self):
        exc = s_exc.SynErr(mesg='woot')
        self.eq('woot', s_exc.reprexc(exc))
        self.eq('ValueError()', s_exc.reprexc(ValueError()))
        self.eq("ValueError('woot')", s_exc.reprexc(ValueError('woot')))

    def test_badtypevalu_init(self):
        # frozenset inputs coerce to sorted tuples
        e = s_exc.BadTypeValu.init('poly', 'x', typeset=frozenset(('b', 'a')), ifaces=frozenset())
        self.eq(e.get('types'), ('a', 'b'))
        self.true(type(e.get('types')) is tuple)
        self.eq(e.get('interfaces'), ())
        self.true(type(e.get('interfaces')) is tuple)
        self.eq(e.get('name'), 'poly')
        self.eq(e.get('valu'), 'x')

        # plain set also coerces
        e2 = s_exc.BadTypeValu.init('poly', 'x', typeset={'b', 'a'})
        self.eq(e2.get('types'), ('a', 'b'))

        # str output is clean — no frozenset repr, no raw braces
        self.isin('types=(a, b)', str(e))
        self.notin('frozenset', str(e))
        self.notin('{', str(e))

        # empty ifaces omitted from the mesg value
        self.notin('interfaces', e.get('mesg'))

        # msgpack round-trip — proves wire-safety
        byts = s_msgpack.en(e.items())
        restored = s_msgpack.un(byts)
        self.eq(restored.get('types'), ('a', 'b'))

        # mesg= override leaves kwargs coerced
        e3 = s_exc.BadTypeValu.init('poly', 'x', typeset=frozenset(('b', 'a')), mesg='custom')
        self.eq(e3.get('mesg'), 'custom')
        self.eq(e3.get('types'), ('a', 'b'))

        # mutually-incomparable fallback: no TypeError, value is a tuple
        e4 = s_exc.BadTypeValu.init('poly', 'x', typeset=frozenset((1, 'a')))
        self.true(type(e4.get('types')) is tuple)
        self.eq(set(e4.get('types')), {1, 'a'})

        # client-side reconstruction via direct constructor works on already-coerced data
        info = e.items()
        e5 = s_exc.BadTypeValu(**info)
        self.eq(e5.get('types'), ('a', 'b'))

        # telepath-style round-trip: retnexc -> msgpack -> result re-raises cleanly
        orig = s_exc.BadTypeValu.init('poly', 'x', typeset=frozenset(('b', 'a')))
        retn = s_common.retnexc(orig)
        byts = s_msgpack.en(retn)
        with self.raises(s_exc.BadTypeValu) as cm:
            s_common.result(s_msgpack.un(byts))
        self.eq(cm.exception.get('types'), ('a', 'b'))
