import asyncio
import logging
import synapse.tests.utils as s_test

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

                if 0:
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

                await asyncio.sleep(1)
                print('-------')

                donecount = 0

                import os
                print(f'{{ {os.getpid() % 219}:writing node', flush=True)
                await prox.storm('[test:int=1]').list()
                await asyncio.sleep(2)
                print(f'}} {os.getpid() % 219}:done writing node', flush=True)

                async def taskfunc(i):
                    nonlocal donecount
                    msgs = await prox.storm('test:int=1 | sleep 45', opts=opts).list()
                    # if len(nodes) == 3:
                    #     donecount += 1
                    print(msgs)
                    print('taskfunc done')

                n = 1
                tasks = [taskfunc(i) for i in range(n)]
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks), timeout=16000)
                except asyncio.TimeoutError:
                    print('timed out')
                    self.false(1)
                # tmp
                # self.eq(donecount, n)

                await asyncio.sleep(3)
                print('End of test', flush=True)

                # test adding model extensions
                #await core.addFormProp('inet:ipv4', '_woot', ('int', {}), {})
                #await core.nodes('[inet:ipv4=1.2.3.4 :_woot=10]')
                #msgs = await prox.storm('inet:ipv4:_woot=10', opts=opts).list()
                #podes = [m[1] for m in msgs if m[0] == 'node']
                #self.len(1, podes)
                #self.eq(podes[0][0], ('inet:ipv4', 0x01020304))
