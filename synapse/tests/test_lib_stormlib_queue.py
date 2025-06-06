import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

class TestLibStormQueue(s_test.SynTest):

    async def test_stormlib_queue_add_and_list(self):
        async with self.getTestCore() as core:

            new_q1 = await core.callStorm('$q = $lib.queue.add(foo) return($q.name)')
            self.eq(new_q1, 'foo')

            with self.raises(s_exc.DupName):
                new_q1 = await core.callStorm('$q = $lib.queue.add(foo) return($q.name)')

            new_q2 = await core.callStorm('$q = $lib.queue.add(bar) return($q.iden)')
            self.nn(new_q2)

            qlist = await core.callStorm('return($lib.queue.list())')
            self.true(any(q['name'] == 'foo' for q in qlist))

    async def test_stormlib_queue_del(self):
        async with self.getTestCore() as core:
            await core.callStorm('$lib.queue.add(foo)')

            with self.raises(s_exc.NoSuchName):
                await core.callStorm('$lib.queue.del(foo)')
            qiden = await core.callStorm('$q = $lib.queue.getByName(foo) return($q.iden)')
            await core.callStorm(f'$lib.queue.del({qiden})')

            # delete a non-existent queue
            with self.raises(s_exc.NoSuchName):
                await core.callStorm('$lib.queue.del(bar)')

    async def test_stormlib_queue_gen(self):
        async with self.getTestCore() as core:
            iden1 = await core.callStorm('$q = $lib.queue.gen(genq) return($q.iden)')
            self.nn(iden1)

            iden2 = await core.callStorm('$q = $lib.queue.gen(genq) return($q.iden)')
            self.eq(iden1, iden2)

    async def test_stormlib_queue_get_byname_and_iden(self):
        async with self.getTestCore() as core:

            qname = await core.callStorm('$q = $lib.queue.add(bynq) return($q.name)')
            qbyname = await core.callStorm('$q = $lib.queue.getByName(bynq) return($q.name)')
            self.eq(qname, qbyname)

            qiden = await core.callStorm(f'$q = $lib.queue.getByName({qname}) return($q.iden)')
            qnamebyiden = await core.callStorm(f'$q = $lib.queue.get({qiden}) return($q.name)')
            self.eq(qname, qnamebyiden)

    async def test_stormlib_queue_put_get(self):
        async with self.getTestCore() as core:
            iden = await core.callStorm('$q = $lib.queue.add(putgetq) return($q.iden)')
            await core.callStorm(f'$q = $lib.queue.get({iden}) $q.put(woot)')
            val = await core.callStorm(f'$q = $lib.queue.get({iden}) return($q.get().1)')
            self.eq(val, 'woot')

    async def test_stormlib_queue_iden_perms(self):
        async with self.getTestCore() as core:
            user = await core.auth.addUser('idenspec')
            opts = {'user': user.iden}

            qiden = await core.callStorm('$q = $lib.queue.add(idq) return($q.iden)')
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(f'$lib.queue.get({qiden})', opts=opts)

            await user.addRule((True, ('queue', 'get', qiden)))
            await core.callStorm(f'$lib.queue.get({qiden})', opts=opts)

            qiden2 = await core.callStorm('$q = $lib.queue.add(idq2) return($q.iden)')
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(f'$lib.queue.get({qiden2})', opts=opts)

            qlist = await core.callStorm('return($lib.queue.list())', opts=opts)
            self.true(any(q['name'] == 'idq' for q in qlist))
            self.false(any(q['name'] == 'idq2' for q in qlist))

    async def test_stormlib_queue_authgate_perms(self):
        async with self.getTestCoreAndProxy() as (core, prox):

            user = await core.auth.addUser('authgateuser')
            qiden = await core.callStorm('$q = $lib.queue.add(authgateq) return($q.iden)')

            async with core.getLocalProxy(user='authgateuser') as usercore:
                with self.raises(s_exc.AuthDeny):
                    await usercore.callStorm(f'$lib.queue.get({qiden})')

            rule = (True, ('queue', 'get'))
            await user.addRule(rule, gateiden=qiden)
            async with core.getLocalProxy(user='authgateuser') as usercore:
                await usercore.callStorm(f'$lib.queue.get({qiden})')

            rule = (True, ('queue', 'put'))
            await prox.addUserRule(user.iden, rule, gateiden=qiden)
            async with core.getLocalProxy(user='authgateuser') as usercore:
                await usercore.callStorm(f'$q = $lib.queue.get({qiden}) $q.put(woot)')

            rule = (True, ('queue', 'del'))
            await prox.addUserRule(user.iden, rule, gateiden=qiden)
            async with core.getLocalProxy(user='authgateuser') as usercore:
                await usercore.callStorm(f'$lib.queue.del({qiden})')
