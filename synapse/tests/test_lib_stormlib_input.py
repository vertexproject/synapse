import asyncio

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.const as s_const
import synapse.lib.storm as s_storm

import synapse.tests.utils as s_test

sendq = '$lib.input.send($iden, $info)'

class InputTest(s_test.SynTest):

    async def _waitEmpty(self, core):
        for _ in range(1000):
            if not core.storminputs:
                return

            await asyncio.sleep(0.01)

        self.fail(f'Storm input requests were not removed: {core.storminputs}')

    async def _stormInput(self, core, text, replycore=None, opts=None, replyopts=None, replies=()):
        '''
        Run a Storm query, answering each input request with a reply from a separate task.
        '''
        if replycore is None:
            replycore = core

        msgs = []
        errs = []

        async for mesg in core.storm(text, opts=opts):

            msgs.append(mesg)
            if mesg[0] != 'input':
                continue

            iden = mesg[1]['iden']

            async def reply():
                for info in replies:
                    vars = {'iden': iden, 'info': info}
                    try:
                        await replycore.callStorm(sendq, opts={'vars': vars, **(replyopts or {})})
                    except s_exc.SynErr as e:
                        errs.append(e)

            core.schedCoro(reply())

        return msgs, errs

    async def test_lib_stormlib_input(self):

        async with self.getTestCluster({'cortex': {'mirrors': 2}}) as clus:

            core = clus.cortex
            core01 = clus.svcs['001.cortex']
            core02 = clus.svcs['002.cortex']

            visi = await core.auth.addUser('visi')
            newp = await core.auth.addUser('newp')

            q = '''
                $reply = $lib.input.request(text, ({"prompt": "What is your **name**?"}))
                $lib.print(`hello {$reply.text}`)
            '''
            msgs, errs = await self._stormInput(core, q, replies=({'text': 'visi'},))
            self.len(0, errs)
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hello visi', msgs)

            imesgs = [m for m in msgs if m[0] == 'input']
            self.len(1, imesgs)
            self.eq('text', imesgs[0][1]['type'])
            self.eq({'prompt': 'What is your **name**?'}, imesgs[0][1]['info'])
            self.len(32, imesgs[0][1]['iden'])
            self.eq({}, core.storminputs)

            # invalid replies are rejected and the request keeps waiting for a valid one
            replies = ({}, {'text': 'hi', 'newp': 'newp'}, {'text': 10}, {'text': 'valid'})
            msgs, errs = await self._stormInput(core, q, replies=replies)
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hello valid', msgs)
            self.len(3, errs)
            self.true(all(isinstance(e, s_exc.SchemaViolation) for e in errs))
            self.eq({}, core.storminputs)

            # readonly queries may request and send input
            msgs, errs = await self._stormInput(core, q, opts={'readonly': True},
                                                replyopts={'readonly': True}, replies=({'text': 'ro'},))
            self.len(0, errs)
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hello ro', msgs)

            # view.exec and runas forward input requests made by the query they run
            fork = await core.callStorm('return($lib.view.get().fork().iden)')
            q = '''
                view.exec $fork {
                    $reply = $lib.input.request(text, ({"prompt": "name?"}))
                    $lib.print(`hello {$reply.text}`)
                }
            '''
            msgs, errs = await self._stormInput(core, q, opts={'vars': {'fork': fork}},
                                                replies=({'text': 'viewexec'},))
            self.len(0, errs)
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hello viewexec', msgs)
            self.len(1, [m for m in msgs if m[0] == 'input'])
            self.eq({}, core.storminputs)

            # runas registers the request to the target user, and the admin caller may reply
            q = '''
                runas visi {
                    $reply = $lib.input.request(text, ({"prompt": "name?"}))
                    $lib.print(`hello {$reply.text}`)
                }
            '''
            msgs = []
            async for mesg in core.storm(q):

                msgs.append(mesg)
                if mesg[0] != 'input':
                    continue

                iden = mesg[1]['iden']
                self.eq(visi.iden, core.storminputs[iden]['user'])
                core.schedCoro(core.callStorm(sendq, opts={'vars': {'iden': iden, 'info': {'text': 'runas'}}}))

            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hello runas', msgs)
            self.len(1, [m for m in msgs if m[0] == 'input'])
            self.eq({}, core.storminputs)

            # the requesting non-admin user may reply, another non-admin user may not
            async def other():
                while not core.storminputs:
                    await asyncio.sleep(0.01)

                iden = list(core.storminputs)[0]
                vars = {'iden': iden, 'info': {'text': 'newp'}}
                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(sendq, opts={'user': newp.iden, 'vars': vars})

                vars = {'iden': iden, 'info': {'text': 'visi'}}
                await core.callStorm(sendq, opts={'user': visi.iden, 'vars': vars})

            task = core.schedCoro(other())
            q = 'return($lib.input.request(text, ({"prompt": "name?"})))'
            self.eq({'text': 'visi'}, await core.callStorm(q, opts={'user': visi.iden}))
            await asyncio.wait_for(task, timeout=10)
            self.eq({}, core.storminputs)

            # unknown types and invalid request info
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('$lib.input.request(newp, ({"prompt": "name?"}))')
            self.eq('newp', cm.exception.get('type'))
            self.isin('Supported types: text', cm.exception.get('mesg'))

            for info in ('({})', '({"prompt": ""})', '({"prompt": 10})', '({"prompt": "hi", "newp": "newp"})'):
                with self.raises(s_exc.SchemaViolation):
                    await core.callStorm(f'$lib.input.request(text, {info})')

            self.eq({}, core.storminputs)

            # the request expires once its timeout elapses
            with self.raises(s_exc.TimeOut):
                await core.callStorm('$lib.input.request(text, ({"prompt": "name?"}), timeout=(1))')
            self.eq({}, core.storminputs)

            # the timeout must be a positive integer
            for timeout in ('(null)', '(0)', '(-1)'):
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm(f'$lib.input.request(text, ({{"prompt": "name?"}}), timeout={timeout})')
                self.isin('positive number of seconds', cm.exception.get('mesg'))

            with self.raises(s_exc.BadCast):
                await core.callStorm('$lib.input.request(text, ({"prompt": "name?"}), timeout=newp)')

            # the leader caps the timeout
            maxval = s_const.STORM_INPUT_TIMEOUT_MAX
            for timeout in (maxval + 1, 10 ** 30):
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm(f'$lib.input.request(text, ({{"prompt": "name?"}}), timeout=({timeout}))')
                self.isin(f'may not exceed {maxval} seconds', cm.exception.get('mesg'))

            self.eq({}, core.storminputs)

            # the default lifespan is used when no timeout is given
            idens = []

            async def check():
                while not core.storminputs:
                    await asyncio.sleep(0.01)

                iden, item = list(core.storminputs.items())[0]
                idens.append(item['expire'].when() - core.loop.time())
                await core.callStorm(sendq, opts={'vars': {'iden': iden, 'info': {'text': 'dflt'}}})

            task = core.schedCoro(check())
            self.eq({'text': 'dflt'}, await core.callStorm('return($lib.input.request(text, ({"prompt": "name?"})))'))
            await asyncio.wait_for(task, timeout=10)
            self.gt(idens[0], s_const.STORM_INPUT_TIMEOUT - 10)
            self.le(idens[0], s_const.STORM_INPUT_TIMEOUT)

            # a request which is never answered expires without a waiter on the leader
            iden = s_common.guid()
            await core.addStormInput(iden, visi.iden, 'text', timeout=0.1)
            await self._waitEmpty(core)
            with self.raises(s_exc.NoSuchIden):
                await core.callStorm(sendq, opts={'vars': {'iden': iden, 'info': {'text': 'late'}}})

            # unknown iden
            with self.raises(s_exc.NoSuchIden):
                await core.callStorm(sendq, opts={'vars': {'iden': s_common.guid(), 'info': {'text': 'hi'}}})

            # non json safe reply
            with self.raises(s_exc.MustBeJsonSafe):
                await core.callStorm('$lib.input.send($lib.guid(), ({"text": $lib.hex.decode(ff)}))')

            # requests made on a mirror are registered on the leader
            q = '''
                $reply = $lib.input.request(text, ({"prompt": "name?"}))
                $lib.print(`hello {$reply.text}`)
            '''

            await core01.sync()
            await core02.sync()

            opts = {'user': visi.iden}

            # request on a mirror, reply on the leader
            msgs, errs = await self._stormInput(core01, q, replycore=core, opts=opts,
                                                replies=({'text': 'leader'},))
            self.len(0, errs)
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hello leader', msgs)
            self.eq({}, core.storminputs)
            self.eq({}, core01.storminputs)

            # request on a mirror, reply on another mirror as the requesting user
            msgs, errs = await self._stormInput(core01, q, replycore=core02, opts=opts,
                                                replyopts=opts, replies=({'text': 'mirror'},))
            self.len(0, errs)
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('hello mirror', msgs)
            self.eq({}, core.storminputs)

            # cancelling a request made on a mirror removes it from the leader
            idens = []
            evnt = asyncio.Event()

            async def consume():
                async for mesg in core01.storm(q, opts=opts):
                    if mesg[0] == 'input':
                        idens.append(mesg[1]['iden'])
                        evnt.set()

            task = core01.schedCoro(consume())
            await asyncio.wait_for(evnt.wait(), timeout=10)
            self.nn(core.storminputs.get(idens[0]))

            task.cancel()
            with self.raises(asyncio.CancelledError):
                await task

            await self._waitEmpty(core)
            self.eq({}, core01.storminputs)

            # a request is removed if the query stops while emitting the input message
            fired = asyncio.Event()
            origfire = s_storm.Runtime.fire

            async def fire(self, name, **info):
                if name == 'input':
                    fired.set()
                    await asyncio.Future()

                return await origfire(self, name, **info)

            with mock.patch.object(s_storm.Runtime, 'fire', fire):

                for stormcore in (core, core01):
                    fired.clear()
                    task = stormcore.schedCoro(stormcore.callStorm(q, opts=opts))
                    await asyncio.wait_for(fired.wait(), timeout=10)
                    self.len(1, core.storminputs)

                    task.cancel()
                    with self.raises(asyncio.CancelledError):
                        await task

                    await self._waitEmpty(core)

            self.eq({}, core01.storminputs)

            # a request made on a mirror expires on the leader
            q = 'return($lib.input.request(text, ({"prompt": "name?"}), timeout=(1)))'
            with self.raises(s_exc.TimeOut):
                await core01.callStorm(q, opts=opts)
            self.eq({}, core.storminputs)
