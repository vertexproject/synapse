import os
import signal
import asyncio
import logging

import synapse.lib.spawn as s_spawn

import synapse.tests.utils as s_test

logger = logging.getLogger(__name__)

class CoreSpawnTest(s_test.SynTest):

    async def test_cortex_spawn_telepath(self):
        conf = {
            'storm:log': True,
            'storm:log:level': logging.INFO,
        }

        async with self.getTestCore(conf=conf) as core:
            pkgdef = {
                'name': 'spawn',
                'version': (0, 0, 1),
                'commands': (
                    {
                        'name': 'passthrough',
                        'desc': 'passthrough input nodes and print their ndef',
                        'storm': '$lib.print($node.ndef())',
                    },
                ),
            }

            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            await core.nodes('queue.add visi')

            async with core.getLocalProxy() as prox:

                opts = {'spawn': True}

                # check that regular node lifting / pivoting works
                msgs = await prox.storm('inet:fqdn=vertex.link -> inet:dns:a -> inet:ipv4', opts=opts).list()
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, podes)
                self.eq(podes[0][0], ('inet:ipv4', 0x01020304))

                # test that runt node lifting works
                msgs = await prox.storm('syn:prop=inet:dns:a:fqdn :form -> syn:form', opts=opts).list()
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, podes)
                self.eq(podes[0][0], ('syn:form', 'inet:dns:a'))

                # make sure node creation fails cleanly
                msgs = await prox.storm('[ inet:email=visi@vertex.link ]', opts=opts).list()
                errs = [m[1] for m in msgs if m[0] == 'err']
                self.eq(errs[0][0], 'IsReadOnly')

                # make sure storm commands are loaded
                msgs = await prox.storm('inet:ipv4=1.2.3.4 | limit 1', opts=opts).list()
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, podes)
                self.eq(podes[0][0], ('inet:ipv4', 0x01020304))

                # make sure graph rules work
                msgs = await prox.storm('inet:dns:a', opts={'spawn': True, 'graph': True}).list()
                podes = [m[1] for m in msgs if m[0] == 'node']

                ndefs = list(sorted(p[0] for p in podes))

                self.eq(ndefs, (
                    ('inet:asn', 0),
                    ('inet:dns:a', ('vertex.link', 16909060)),
                    ('inet:fqdn', 'link'),
                    ('inet:fqdn', 'vertex.link'),
                    ('inet:ipv4', 16909060),
                ))

                # Test a python cmd that came in via a ctor
                msgs = await prox.storm('inet:ipv4=1.2.3.4 | testechocmd :asn', opts=opts).list()
                self.stormIsInPrint('Echo: [0]', msgs)
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, podes)

                # Test a simple stormlib command
                msgs = await prox.storm('$lib.print("hello")', opts=opts).list()
                self.stormIsInPrint("hello", msgs)

                # test a complex stormlib command using lib deferences
                marsopts = {'spawn': True, 'vars': {'world': 'mars'}}
                q = '$lib.print($lib.str.format("hello {world}", world=$world))'
                msgs = await prox.storm(q, opts=marsopts).list()
                self.stormIsInPrint("hello mars", msgs)

                # Add a stormpkg - this should fini the spawnpool spawnprocs
                procs = [p for p in core.spawnpool.spawns.values()]
                self.isin(len(procs), (1, 2, 3))

                await core.addStormPkg(pkgdef)

                for proc in procs:
                    self.true(await proc.waitfini(6))

                self.len(0, core.spawnpool.spawnq)
                self.len(0, core.spawnpool.spawns)

                # Test a pure storm commands
                msgs = await prox.storm('inet:fqdn=vertex.link | passthrough', opts=opts).list()
                self.stormIsInPrint("('inet:fqdn', 'vertex.link')", msgs)

                # No guarantee that we've gotten the proc back into
                # the pool so we cannot check the size of spawnq
                self.len(1, core.spawnpool.spawns)

                # Test launching a bunch of spawn queries at the same time
                donecount = 0

                await prox.storm('[test:int=1]').list()
                # wait for commit
                await core.view.layers[0].layrslab.waiter(1, 'commit').wait()

                async def taskfunc(i):
                    nonlocal donecount
                    msgs = await prox.storm('test:int=1 | sleep 3', opts=opts).list()
                    if len(msgs) == 3:
                        donecount += 1

                n = 4
                tasks = [taskfunc(i) for i in range(n)]
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks), timeout=40)
                except asyncio.TimeoutError:
                    self.fail('Timeout awaiting for spawn tasks to finish.')

                self.eq(donecount, n)

                # test a remote boss kill of the client side task
                logger.info('telepath ps/kill test.')
                evnt = asyncio.Event()
                msgs = {'msgs': []}

                async def taskfunc2():
                    async for mesg in prox.storm('test:int=1 | sleep 15', opts=opts):
                        msgs['msgs'].append(mesg)
                        if mesg[0] == 'node':
                            evnt.set()
                    return True

                victimproc = core.spawnpool.spawnq[0]  # type: s_spawn.SpawnProc
                fut = core.schedCoro(taskfunc2())
                self.true(await asyncio.wait_for(evnt.wait(), timeout=6))
                tasks = await prox.ps()
                new_idens = [task.get('iden') for task in tasks]
                self.len(1, new_idens)
                await prox.kill(new_idens[0])

                # Ensure the task cancellation tore down the spawnproc
                self.true(await victimproc.waitfini(6))

                resp = await fut
                self.true(resp)
                # We did not get a fini messages since the proc was killed
                self.eq({m[0] for m in msgs.get('msgs')}, {'init', 'node'})

                # test kill -9 ing a spawn proc
                logger.info('sigkill test')
                victimproc = core.spawnpool.spawnq[0]  # type: s_spawn.SpawnProc
                victimpid = victimproc.proc.pid
                sig = signal.SIGKILL

                async def taskfunc3():
                    retn = await prox.storm('test:int=1 | sleep 15', opts=opts).list()
                    return retn

                fut = core.schedCoro(taskfunc3())
                await asyncio.sleep(1)
                os.kill(victimpid, sig)
                self.true(await victimproc.waitfini(6))
                msgs = await fut
                # We did not get a fini messages since the proc was killed
                self.eq({m[0] for m in msgs}, {'init', 'node'})

    async def test_queues(self):
        conf = {
            'storm:log': True,
            'storm:log:level': logging.INFO,
        }

        async with self.getTestCore(conf=conf) as core:
            await core.nodes('queue.add visi')
            async with core.getLocalProxy() as prox:

                opts = {'spawn': True}

                msgs = await prox.storm('queue.list', opts=opts).list()
                self.stormIsInPrint('visi', msgs)

    async def test_model_extensions(self):
        self.skip('Model extensions not supported for spawn.')
        async with self.getTestCore() as core:
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            async with core.getLocalProxy() as prox:
                opts = {'spawn': True}
                # test adding model extensions
                await core.addFormProp('inet:ipv4', '_woot', ('int', {}), {})
                await core.nodes('[inet:ipv4=1.2.3.4 :_woot=10]')
                await core.view.layers[0].layrslab.waiter(1, 'commit').wait()
                msgs = await prox.storm('inet:ipv4=1.2.3.4', opts=opts).list()
                self.len(3, msgs)
                self.eq(msgs[1][1][1]['props'].get('_woot'), 10)
                # TODO:  implement TODO in core.getModelDefs
                # msgs = await prox.storm('inet:ipv4:_woot=10', opts=opts).list()
                # self.len(3, msgs)
                # self.eq(msgs[1][1][1]['props'].get('_woot'), 10)
