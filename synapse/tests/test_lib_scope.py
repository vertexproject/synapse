import synapse.tests.utils as s_t_utils

import synapse.lib.scope as s_scope

class ScopeTest(s_t_utils.SynTest):

    def test_lib_scope(self):

        syms = {'foo': 'woot', 'bar': 30, 'baz': [1, 2]}
        scope = s_scope.Scope(**syms)

        self.eq(scope.get('bar'), 30)
        self.eq(scope.get('foo'), 'woot')
        self.eq(tuple(scope.iter('baz')), (1, 2))

        scope.update((('hehe', 1), ('haha', 'wow')))
        self.eq(scope.get('hehe'), 1)
        self.eq(scope.get('haha'), 'wow')

        with scope:

            scope.set('bar', 20)
            scope.add('baz', 3, 4)
            scope.update((('hehe', 2), ('haha', 'oh my')))

            self.eq(scope.get('bar'), 20)
            self.eq(scope.get('foo'), 'woot')
            self.eq(tuple(scope.iter('baz')), (1, 2, 3, 4))

            self.eq(scope.get('hehe'), 2)
            self.eq(scope.get('haha'), 'oh my')

        self.eq(scope.get('hehe'), 1)
        self.eq(scope.get('haha'), 'wow')

        self.eq(scope.get('bar'), 30)
        self.eq(scope.get('foo'), 'woot')
        self.eq(tuple(scope.iter('baz')), (1, 2))

        self.eq(scope.pop('bar'), 30)
        self.none(scope.get('bar'))

    async def test_lib_scope_task(self):
        s_scope.set('test:foo', 10)
        self.eq(s_scope.get('test:foo'), 10)
        self.eq(s_scope.pop('test:foo'), 10)
        self.none(s_scope.get('test:foo'))
        s_scope.update([('test:hehe', 1), ('test:haha', 'wow')])
        self.eq(s_scope.get('test:hehe'), 1)
        self.eq(s_scope.get('test:haha'), 'wow')

    async def test_lib_scope_enter(self):

        with s_scope.enter({'woot': 10}):
            self.eq(s_scope.get('woot'), 10)
            self.none(s_scope.get('newp'))

        self.none(s_scope.get('woot'))
        self.none(s_scope.get('newp'))

        scope = s_scope.Scope()
        scope.enter({'yes': 1})
        self.eq(scope.get('yes'), 1)
        scope.set('no', 0)
        frame = scope.leave()
        self.eq(frame, {'yes': 1, 'no': 0})
        self.none(scope.get('yes'))
        self.none(scope.get('no'))
        self.raises(IndexError, scope.leave)

    def test_lib_scope_get_defval(self):
        syms = {'foo': None, 'bar': 123}
        scope = s_scope.Scope(**syms)
        self.eq(scope.get('foo'), None)
        self.eq(scope.get('foo', defval=None), None)
        self.eq(scope.get('bar'), 123)
        self.eq(scope.get('bar', defval=123), 123)
        self.eq(scope.get('boo'), None)
        self.eq(scope.get('boo', defval=None), None)

        scope.enter({'bar': 321})
        self.eq(scope.get('bar'), 321)
        self.eq(scope.get('bar', defval=321), 321)
        scope.leave()
