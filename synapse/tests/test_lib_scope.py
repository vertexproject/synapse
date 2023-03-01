import asyncio

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

        with self.raises(ValueError) as cm:
            with s_scope.enter({'foo': 'bar'}):
                self.eq(s_scope.get('foo'), 'bar')
                raise ValueError('bad value')
        self.none(s_scope.get('foo'))

        with s_scope.enter({'foo': 'bar'}):
            self.eq(s_scope.get('foo'), 'bar')
            with s_scope.enter({'hehe': 'haha'}):
                self.eq(s_scope.get('hehe'), 'haha')
                self.eq(s_scope.get('foo'), 'bar')
                with s_scope.enter({'foo': 'woah'}):
                    self.eq(s_scope.get('foo'), 'woah')
                self.eq(s_scope.get('foo'), 'bar')
            self.none(s_scope.get('hehe'))
            self.eq(s_scope.get('foo'), 'bar')

    async def test_lib_task_clone(self):
        # Ensure that scope task clones are shallow
        evt0 = asyncio.Event()
        evt1 = asyncio.Event()

        # Ensure the following rules are met with scope copies:
        # 1. The frames of the scope.copy are shallow copies of the parent
        #    scope.
        # 2. Changes in the parent scope, after being copied, are not seen
        #    by the child scope.
        #    Example: In chained scopes ( example, three copied scopes ) a
        #    member of he chain leaving scope does not affect subsequent
        #    copies.
        #

        async def func2():
            self.eq(s_scope.get('foo'), 'bar')
            self.eq(s_scope.get('dict'), {'hehe': 'haha'})
            s_scope.get('dict')['beep'] = 'boop'  # mutable object being modified
            s_scope.set('f2', 'notseen')
            evt0.set()
            await asyncio.wait_for(evt1.wait(), timeout=6)
            self.eq(s_scope.get('f2'), 'notseen')
            return

        async def func1():
            s_scope.set('foo', 'bar')
            s_scope.set('dict', {'hehe': 'haha'})
            t2 = asyncio.create_task(func2())
            s_scope.clone(t2)
            await asyncio.sleep(0)
            await asyncio.wait_for(evt0.wait(), timeout=6)
            self.eq(s_scope.get('dict').get('beep'), 'boop')
            self.none(s_scope.get('f2'))
            s_scope.set('f2', 'setbyf1')
            evt1.set()
            self.eq(s_scope.get('f2'), 'setbyf1')
            await t2
            # change made in dict still is present
            self.eq(s_scope.get('dict').get('beep'), 'boop')
            return

        task = asyncio.create_task(func1())
        s_scope.clone(task)
        self.none(await task)

    def test_scope_copy(self):
        # Ensure scope copies are shallow copies
        # Scope keys do not mutate in copies.
        # Mutable data structures stored in scopes may change.
        scope00 = s_scope.Scope()
        scope00.enter()
        scope00.update(vals={'key': 'valu', 'dict': {'foo': 'bar'}})
        self.eq(scope00.get('key'), 'valu')
        self.eq(scope00.get('dict'), {'foo': 'bar'})

        scope01 = scope00.copy()
        scope01.enter()
        self.eq(scope01.get('key'), 'valu')
        scope01.set('s1', True)
        scope01.get('dict')['hehe'] = 'haha'
        self.none(scope00.get('s1'))
        self.eq(scope00.get('dict').get('hehe'), 'haha')
        scope00.set('key', 'newp')
        self.eq(scope01.get('key'), 'valu')

        # If an earlier scope leaves, it does not affect the copied scope.
        scope00.leave()
        self.none(scope00.get('key'))
        self.eq(scope01.get('key'), 'valu')
        self.eq(scope01.get('dict'), {'foo': 'bar', 'hehe': 'haha'})
        scope01.leave()

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
