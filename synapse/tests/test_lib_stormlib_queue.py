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

    async def test_stormlib_queue_all_perms(self):

        async def delRules(user):
            for rule in list(user.getRules()):
                await user.delRule(rule)

        async with self.getTestCore() as core:
            user = await core.auth.addUser('permuser')
            opts = {'user': user.iden}

            # No permissions, all actions denied
            for storm, exc in [
                ('$lib.queue.add(q)', s_exc.AuthDeny),
                ('$lib.queue.get(q)', s_exc.AuthDeny),
                ('$lib.queue.del(q)', s_exc.AuthDeny),
            ]:
                with self.raises(exc):
                    await core.callStorm(storm, opts=opts)

            # Grant add only, other actions denied
            await user.addRule((True, ('queue', 'add')))
            qiden = await core.callStorm('$q = $lib.queue.add(q) return($q.iden)', opts=opts)
            for storm, exc in [
                ('$lib.queue.get(q)', s_exc.AuthDeny),
                ('$lib.queue.getByName(q)', s_exc.AuthDeny),
                ('$lib.queue.del(q)', s_exc.AuthDeny),
                ('$q = $lib.queue.get(q) $q.put(woot)', s_exc.AuthDeny),
            ]:
                with self.raises(exc):
                    await core.callStorm(storm, opts=opts)

            # Grant get only, other actions denied
            await delRules(user)
            await user.addRule((True, ('queue', 'get')))
            await core.callStorm('$lib.queue.getByName(q)', opts=opts)
            for storm, exc in [
                ('$lib.queue.add(q2)', s_exc.AuthDeny),
                ('$lib.queue.del(q)', s_exc.AuthDeny),
                ('$q = $lib.queue.getByName(q) $q.put(woot)', s_exc.AuthDeny),
            ]:
                with self.raises(exc):
                    await core.callStorm(storm, opts=opts)

            # Grant get/put, other actions denied
            await delRules(user)
            await user.addRule((True, ('queue', 'get')))
            await user.addRule((True, ('queue', 'put')))
            await core.callStorm('$q = $lib.queue.getByName(q) $q.put(woot)', opts=opts)
            for storm, exc in [
                ('$lib.queue.add(q2)', s_exc.AuthDeny),
                ('$lib.queue.del(q)', s_exc.AuthDeny),
            ]:
                with self.raises(exc):
                    await core.callStorm(storm, opts=opts)

            # Grant del only, other actions denied
            await delRules(user)
            await user.addRule((True, ('queue', 'del')))
            await core.callStorm(f'$lib.queue.del({qiden})', opts=opts)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.queue.add(q2)', opts=opts)

            # Grant all
            await delRules(user)
            for perm in ['add', 'get', 'put', 'del']:
                await user.addRule((True, ('queue', perm)))
            await core.callStorm('$lib.queue.add(q)', opts=opts)
            await core.callStorm('$lib.queue.getByName(q)', opts=opts)
            await core.callStorm('$q = $lib.queue.getByName(q) $q.put(woot)', opts=opts)
            qiden = await core.callStorm('$q = $lib.queue.getByName(q) return($q.iden)', opts=opts)
            await core.callStorm(f'$lib.queue.del({qiden})', opts=opts)

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
