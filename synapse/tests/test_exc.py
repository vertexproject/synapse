import logging

import synapse.exc as s_exc

import synapse.lib.parser as s_parser

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class ExcTest(s_t_utils.SynTest):
    def test_basic(self):
        e = s_exc.SynErr(mesg='words', foo='bar')
        self.eq(e.get('foo'), 'bar')
        self.eq("SynErr: foo='bar' mesg='words'", str(e))
        e.set('hehe', 1234)
        e.set('foo', 'words')
        self.eq("SynErr: foo='words' hehe=1234 mesg='words'", str(e))

        e.setdefault('defv', 1)
        self.eq("SynErr: defv=1 foo='words' hehe=1234 mesg='words'", str(e))

        e.setdefault('defv', 2)
        self.eq("SynErr: defv=1 foo='words' hehe=1234 mesg='words'", str(e))

        self.eq(e.errname, 'SynErr')

        e2 = s_exc.BadTypeValu(mesg='haha')
        self.eq(e2.errname, 'BadTypeValu')

    async def test_pickled_synerr(self):
        with self.raises(s_exc.BadSyntax) as cm:
            _ = await s_parser._forkedParseEval('| | | ')
        self.isin('BadSyntax', str(cm.exception))
        self.isin('Unexpected token', str(cm.exception))

    def test_stormraise(self):
        e = s_exc.StormRaise(mesg='hehe', errname='fooErr', info={'key': 'valu'})
        self.eq(e.errname, 'fooErr')

        with self.raises(s_exc.BadArg):
            s_exc.StormRaise(mesg='newp')
