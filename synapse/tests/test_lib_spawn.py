import os
import signal
import asyncio
import logging
import multiprocessing

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.cortex as s_cortex

import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.spawn as s_spawn
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_test
import synapse.tests.test_lib_stormsvc as s_test_svc

logger = logging.getLogger(__name__)

def make_core(dirn, conf, queries, queue, event):
    '''
    Multiprocessing target for making a Cortex for local use of a SpawnCore instance.
    '''

    async def workloop():
        s_glob.iAmLoop()
        async with await s_cortex.Cortex.anit(dirn=dirn, conf=conf) as core:
            await core.addTagProp('added', ('time', {}), {})
            for q in queries:
                await core.nodes(q)

            await core.view.layers[0].layrslab.sync()

            spawninfo = await core.getSpawnInfo()
            queue.put(spawninfo)
            # Don't block the ioloop..
            await s_coro.executor(event.wait)

    asyncio.run(workloop())

class CoreSpawnTest(s_test.SynTest):

    async def test_spawncore(self):
        # This test makes a real Cortex in a remote process, and then
        # gets the spawninfo from that real Cortex in order to make a
        # local SpawnCore. This avoids the problem of being unable to
        # open lmdb environments multiple times by the same process
        # and allows direct testing of the SpawnCore object.

        mpctx = multiprocessing.get_context('spawn')
        queue = mpctx.Queue()
        event = mpctx.Event()

        conf = {
            'storm:log': True,
            'storm:log:level': logging.INFO,
            'modules': [('synapse.tests.utils.TestModule', {})],
        }
        queries = [
            '[test:str="Cortex from the aether!"]',
        ]
        with self.getTestDir() as dirn:
            args = (dirn, conf, queries, queue, event)
            proc = mpctx.Process(target=make_core, args=args)
            try:
                proc.start()
                spawninfo = queue.get(timeout=30)

                async with await s_spawn.SpawnCore.anit(spawninfo) as core:
                    root = await core.auth.getUserByName('root')
                    q = '''test:str
                    $lib.print($lib.str.format("{n}", n=$node.repr()))
                    | limit 1'''
                    item = {
                        'user': root.iden,
                        'view': list(core.views.keys())[0],
                        'storm': {
                            'query': q,
                            'opts': None,
                        }
                    }

                    # Test the storm implementation used by spawncore
                    msgs = await s_test.alist(s_spawn.storm(core, item))
                    podes = [m[1] for m in msgs if m[0] == 'node']
                    e = 'Cortex from the aether!'
                    self.len(1, podes)
                    self.eq(podes[0][0], ('test:str', e))
                    self.stormIsInPrint(e, msgs)

                    # Direct test of the _innerloop code.
                    todo = mpctx.Queue()
                    done = mpctx.Queue()

                    # Test poison - this would cause the corework to exit
                    todo.put(None)
                    self.none(await s_spawn._innerloop(core, todo, done))

                    # Test a real item with a link associated with it. This ends
                    # up getting a bunch of telepath message directly.
                    todo_item = item.copy()
                    link0, sock0 = await s_link.linksock()
                    todo_item['link'] = link0.getSpawnInfo()
                    todo.put(todo_item)
                    self.true(await s_spawn._innerloop(core, todo, done))
                    resp = done.get(timeout=12)
                    self.false(resp)
                    buf0 = sock0.recv(1024 * 16)
                    unpk = s_msgpack.Unpk()
                    msgs = [msg for (offset, msg) in unpk.feed(buf0)]
                    self.eq({'t2:genr', 't2:yield'},
                            {m[0] for m in msgs})

                    await link0.fini()  # We're done with the link now
                    todo.close()
                    done.close()

                # Test the workloop directly - this again just gets telepath
                # messages back. This does use poison to kill the workloop.
                todo = mpctx.Queue()
                done = mpctx.Queue()

                task = asyncio.create_task(s_spawn._workloop(spawninfo, todo, done))
                await asyncio.sleep(0.01)
                link1, sock1 = await s_link.linksock()
                todo_item = item.copy()
                todo_item['link'] = link1.getSpawnInfo()
                todo.put(todo_item)
                # Don't block the IO loop!
                resp = await s_coro.executor(done.get, timeout=12)
                self.false(resp)
                buf0 = sock1.recv(1024 * 16)
                unpk = s_msgpack.Unpk()
                msgs = [msg for (offset, msg) in unpk.feed(buf0)]
                self.eq({'t2:genr', 't2:yield'},
                        {m[0] for m in msgs})
                await link1.fini()  # We're done with the link now
                # Poison the queue - this should close the task
                todo.put(None)
                self.none(await asyncio.wait_for(task, timeout=12))

                todo.close()
                done.close()

            finally:

                queue.close()
                event.set()
                proc.join(12)

    async def test_cortex_spawn_telepath(self):
        conf = {
            'storm:log': True,
            'storm:log:level': logging.INFO,
        }

        async with self.getTestCore(conf=conf) as core:
            pkgdef = {
                'name': 'spawn',
                'version': (0, 0, 1),
                'synapse_minversion': (2, 8, 0),
                'commands': (
                    {
                        'name': 'passthrough',
                        'desc': 'passthrough input nodes and print their ndef',
                        'storm': '$lib.print($node.ndef())',
                    },
                ),
            }

            await self.runCoreNodes(core, '[ inet:dns:a=(vertex.link, 1.2.3.4) ] -> inet:ipv4 [ :asn=0 ]')

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
                msgs = await prox.storm('inet:ipv4=1.2.3.4 | testcmd', opts=opts).list()
                self.stormIsInPrint("testcmd: ('inet:ipv4', 16909060)", msgs)
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, podes)

                # Test a macro execution
                msgs = await prox.storm('macro.set macrotest ${ inet:ipv4 }', opts=opts).list()
                self.stormIsInPrint('Set macro: macrotest', msgs)
                msgs = await prox.storm('macro.list', opts=opts).list()
                self.stormIsInPrint('macrotest', msgs)
                self.stormIsInPrint('owner: root', msgs)
                msgs = await prox.storm('macro.exec macrotest', opts=opts).list()
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, podes)
                self.eq(podes[0][0], ('inet:ipv4', 0x01020304))
                msgs = await prox.storm('macro.del macrotest', opts=opts).list()
                self.stormIsInPrint('Removed macro: macrotest', msgs)
                msgs = await prox.storm('macro.exec macrotest', opts=opts).list()
                self.stormIsInErr('Macro name not found: macrotest', msgs)

                # Test a simple stormlib command
                msgs = await prox.storm('$lib.print("hello")', opts=opts).list()
                self.stormIsInPrint("hello", msgs)

                # test a complex stormlib command using lib deferences
                marsopts = {'spawn': True, 'vars': {'world': 'mars'}}
                q = '$lib.print($lib.str.format("hello {world}", world=$world))'
                msgs = await prox.storm(q, opts=marsopts).list()
                self.stormIsInPrint("hello mars", msgs)

                # Model deference off of the snap via stormtypes
                q = '''$valu=$lib.time.format('200103040516', '%Y %m %d')
                $lib.print($valu)
                '''
                msgs = await prox.storm(q, opts=opts).list()
                self.stormIsInPrint('2001 03 04', msgs)

                # Test sleeps / fires from a spawnproc
                q = '''$tick=$lib.time.now()
                $lib.time.sleep(0.1)
                $tock=$lib.time.now()
                $lib.fire(took, tick=$tick, tock=$tock)
                '''
                msgs = await prox.storm(q, opts=opts).list()
                fires = [m[1] for m in msgs if m[0] == 'storm:fire']
                self.len(1, fires)
                fire_data = fires[0].get('data')
                self.ne(fire_data.get('tick'), fire_data.get('tock'))

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

                await self.runCoreNodes(core, '[test:int=1]')
                # force a commit
                await s_lmdbslab.Slab.syncLoopOnce()

                async def taskfunc(i):
                    nonlocal donecount
                    msgs = await prox.storm('test:int=1 | sleep 3', opts=opts).list()
                    if len(msgs) == 3:
                        donecount += 1

                n = 4
                tasks = [taskfunc(i) for i in range(n)]
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks), timeout=80)
                except asyncio.TimeoutError:
                    self.fail('Timeout awaiting for spawn tasks to finish.')

                self.eq(donecount, n)

                # test a remote boss kill of the client side task
                logger.info('telepath ps/kill test.')
                evnt = asyncio.Event()
                msgs = {'msgs': []}

                tf2opts = {'spawn': True, 'vars': {'hehe': 'haha'}}

                async def taskfunc2():
                    async for mesg in prox.storm('test:int=1 | sleep 15', opts=tf2opts):
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

                await self.asyncraises(s_exc.LinkShutDown, fut)
                # We did not get a fini message since the proc was killed
                self.eq({m[0] for m in msgs.get('msgs')}, {'init', 'node'})

                # test kill -9 ing a spawn proc
                logger.info('sigkill test')
                assert len(core.spawnpool.spawnq)
                victimproc = core.spawnpool.spawnq[0]  # type: s_spawn.SpawnProc
                victimpid = victimproc.proc.pid
                sig = signal.SIGKILL

                retn = []

                async def taskfunc3():
                    async for item in prox.storm('test:int=1 | sleep 15', opts=opts):
                        retn.append(item)

                fut = core.schedCoro(taskfunc3())
                await asyncio.sleep(1)
                os.kill(victimpid, sig)
                self.true(await victimproc.waitfini(6))
                await self.asyncraises(s_exc.LinkShutDown, fut)
                # We did not get a fini messages since the proc was killed
                self.eq({m[0] for m in retn}, {'init', 'node'})

    async def test_queues(self):
        conf = {
            'storm:log': True,
            'storm:log:level': logging.INFO,
        }

        # Largely mimics test_storm_lib_queue
        async with self.getTestCore(conf=conf) as core:
            opts = {'spawn': True}

            async with core.getLocalProxy() as prox:

                msgs = await prox.storm('queue.add visi', opts=opts).list()
                self.stormIsInPrint('queue added: visi', msgs)

                with self.raises(s_exc.DupName):
                    await core.nodes('queue.add visi')

                msgs = await prox.storm('queue.list', opts=opts).list()
                self.stormIsInPrint('Storm queue list:', msgs)
                self.stormIsInPrint('visi', msgs)

                # Make a node and put it into the queue
                q = '$q = $lib.queue.get(visi) [ inet:ipv4=1.2.3.4 ] $q.put( $node.repr() )'
                nodes = await core.nodes(q)
                self.len(1, nodes)

                await s_lmdbslab.Slab.syncLoopOnce()

                q = '$q = $lib.queue.get(visi) ($offs, $ipv4) = $q.get(0) inet:ipv4=$ipv4'
                msgs = await prox.storm(q, opts=opts).list()

                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, podes)
                self.eq(podes[0][0], ('inet:ipv4', 0x01020304))

                # test iter use case
                q = '$q = $lib.queue.add(blah) [ inet:ipv4=1.2.3.4 inet:ipv4=5.5.5.5 ] $q.put( $node.repr() )'
                nodes = await core.nodes(q)
                self.len(2, nodes)

                await s_lmdbslab.Slab.syncLoopOnce()

                # Put a value into the queue that doesn't exist in the cortex so the lift can nop
                q = '$q = $lib.queue.get(blah) $q.put("8.8.8.8")'
                msgs = await prox.storm(q, opts=opts).list()

                msgs = await prox.storm('''
                    $q = $lib.queue.get(blah)
                    for ($offs, $ipv4) in $q.gets(0, cull=$lib.false, wait=$lib.false) {
                        inet:ipv4=$ipv4
                    }
                ''', opts=opts).list()
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(2, podes)

                msgs = await prox.storm('''
                    $q = $lib.queue.get(blah)
                    for ($offs, $ipv4) in $q.gets(wait=$lib.false) {
                        inet:ipv4=$ipv4
                        $q.cull($offs)
                    }
                ''', opts=opts).list()
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(2, podes)

                q = '''$q = $lib.queue.get(blah)
                for ($offs, $ipv4) in $q.gets(wait=0) {
                    inet:ipv4=$ipv4
                }'''
                msgs = await prox.storm(q, opts=opts).list()
                podes = [m[1] for m in msgs if m[0] == 'node']
                self.len(0, podes)

                msgs = await prox.storm('queue.del visi', opts=opts).list()
                self.stormIsInPrint('queue removed: visi', msgs)

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('queue.del visi')

                msgs = await prox.storm('$lib.queue.get(newp).get()', opts=opts).list()
                # err = msgs[-2]
                errs = [m[1] for m in msgs if m[0] == 'err']
                self.len(1, errs)
                self.eq(errs[0][0], 'NoSuchName')

                # Attempting to use a queue to make nodes in spawn town fails.
                await core.nodes('''
                    $doit = $lib.queue.add(doit)
                    $doit.puts((foo,bar))
                ''')
                q = 'for ($offs, $name) in $lib.queue.get(doit).gets(size=2) { [test:str=$name] }'
                msgs = await prox.storm(q, opts=opts).list()
                errs = [m[1] for m in msgs if m[0] == 'err']
                self.len(1, errs)
                self.eq(errs[0][0], 'IsReadOnly')

            # test other users who have access to this queue can do things to it
            async with core.getLocalProxy() as root:
                # add users
                await root.addUser('synapse')
                await root.addUser('wootuser')

                synu = await core.auth.getUserByName('synapse')
                woot = await core.auth.getUserByName('wootuser')

                async with core.getLocalProxy(user='synapse') as prox:
                    msgs = await prox.storm('queue.add synq', opts=opts).list()
                    errs = [m[1] for m in msgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][0], 'AuthDeny')

                    rule = (True, ('queue', 'add'))
                    await synu.addRule(rule)
                    msgs = await prox.storm('queue.add synq', opts=opts).list()
                    self.stormIsInPrint('queue added: synq', msgs)

                    rule = (True, ('queue', 'put'))
                    await synu.addRule(rule, gateiden='queue:synq')

                    q = '$q = $lib.queue.get(synq) $q.puts((bar, baz))'
                    msgs = await prox.storm(q, opts=opts).list()

                    # Ensure that the data was put into the queue by the spawnproc
                    q = '$q = $lib.queue.get(synq) $lib.print($q.get(wait=$lib.false, cull=$lib.false))'
                    msgs = await core.stormlist(q)
                    self.stormIsInPrint("(0, 'bar')", msgs)

                async with core.getLocalProxy(user='wootuser') as prox:
                    # now let's see our other user fail to add things
                    msgs = await prox.storm('$lib.queue.get(synq).get()', opts=opts).list()
                    errs = [m[1] for m in msgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][0], 'AuthDeny')

                    rule = (True, ('queue', 'get'))
                    await woot.addRule(rule, gateiden='queue:synq')

                    q = '$lib.print($lib.queue.get(synq).get(wait=$lib.false))'
                    msgs = await prox.storm(q, opts=opts).list()
                    self.stormIsInPrint("(0, 'bar')", msgs)

                    msgs = await prox.storm('$lib.queue.del(synq)', opts=opts).list()
                    errs = [m[1] for m in msgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][0], 'AuthDeny')

                    rule = (True, ('queue', 'del'))
                    await woot.addRule(rule, gateiden='queue:synq')

                    msgs = await prox.storm('$lib.queue.del(synq)', opts=opts).list()
                    with self.raises(s_exc.NoSuchName):
                        await core.nodes('$lib.queue.get(synq)')

    async def test_stormpkg(self):
        otherpkg = {
            'name': 'foosball',
            'version': (0, 0, 1),
            'synapse_minversion': (2, 8, 0),
        }

        stormpkg = {
            'name': 'stormpkg',
            'version': (1, 2, 3),
            'synapse_minversion': (2, 8, 0),
        }
        conf = {
            'storm:log': True,
            'storm:log:level': logging.INFO,
        }
        async with self.getTestDmon() as dmon:
            dmon.share('real', s_test_svc.RealService())
            host, port = dmon.addr

            lurl = f'tcp://127.0.0.1:{port}/real'
            async with self.getTestCore(conf=conf) as core:

                await core.nodes(f'service.add real {lurl}')
                await core.nodes('$lib.service.wait(real)')
                msgs = await core.stormlist('help')
                self.stormIsInPrint('foobar', msgs)

                async with core.getLocalProxy() as prox:
                    opts = {'spawn': True}

                    # Ensure the spawncore loaded the service
                    coro = prox.storm('$lib.service.wait(real)', opts).list()
                    msgs = await asyncio.wait_for(coro, 30)

                    msgs = await prox.storm('help', opts=opts).list()
                    self.stormIsInPrint('foobar', msgs)

                    msgs = await prox.storm('pkg.del asdf', opts=opts).list()
                    self.stormIsInPrint('No package names match "asdf". Aborting.', msgs)

                    await core.addStormPkg(otherpkg)
                    msgs = await prox.storm('pkg.list', opts=opts).list()
                    self.stormIsInPrint('foosball', msgs)

                    msgs = await prox.storm(f'pkg.del foosball', opts=opts).list()
                    self.stormIsInPrint('Removing package: foosball', msgs)

                    # Direct add via stormtypes
                    msgs = await prox.storm('$lib.pkg.add($pkg)',
                                            opts={'vars': {'pkg': stormpkg}, 'spawn': True}).list()
                    msgs = await prox.storm('pkg.list', opts=opts).list()
                    self.stormIsInPrint('stormpkg', msgs)

    async def test_spawn_node_data(self):

        # Largely mimics test_storm_node_data
        async with self.getTestCore() as core:
            opts = {'spawn': True}

            async with core.getLocalProxy() as prox:

                await core.nodes('[test:int=10]')
                msgs = await prox.storm('test:int=10 $node.data.set(foo, hehe)', opts=opts).list()
                errs = [m[1] for m in msgs if m[0] == 'err']
                self.eq(errs[0][0], 'IsReadOnly')

                await core.nodes('test:int=10 $node.data.set(foo, hehe)')

                msgs = await prox.storm('test:int $foo=$node.data.get(foo) $lib.print($foo)', opts=opts).list()
                self.stormIsInPrint('hehe', msgs)

                q = 'test:int for $item in $node.data.list() { $lib.print($item) }'
                msgs = await prox.storm(q, opts=opts).list()
                self.stormIsInPrint("('foo', 'hehe')", msgs)

                await core.nodes('test:int=10 $node.data.set(woot, woot)')
                q = 'test:int=10 $node.data.pop(woot)'

                msgs = await prox.storm(q, opts=opts).list()
                errs = [m[1] for m in msgs if m[0] == 'err']
                self.eq(errs[0][0], 'IsReadOnly')

    async def test_model_extensions(self):
        async with self.getTestCoreAndProxy() as (core, prox):
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            opts = {'spawn': True}
            # Adding model extensions must work
            await core.addFormProp('inet:ipv4', '_woot', ('int', {}), {})
            await core.nodes('[inet:ipv4=1.2.3.4 :_woot=10]')
            await s_lmdbslab.Slab.syncLoopOnce()
            msgs = await prox.storm('inet:ipv4=1.2.3.4', opts=opts).list()
            self.len(3, msgs)
            self.eq(msgs[1][1][1]['props'].get('_woot'), 10)

            msgs = await prox.storm('inet:ipv4:_woot=10', opts=opts).list()
            self.len(3, msgs)
            self.eq(msgs[1][1][1]['props'].get('_woot'), 10)

            # tag props must work
            await prox.addTagProp('added', ('time', {}), {})
            await prox.storm('inet:ipv4=1.2.3.4 [ +#foo.bar:added="2049" ]').list()
            msgs = await prox.storm('inet:ipv4#foo.bar:added', opts=opts).list()
            self.len(3, msgs)

    async def test_spawn_dmon_cmds(self):
        '''
        Copied from test-cortex_storm_lib_dmon_cmds
        '''
        async with self.getTestCoreAndProxy() as (core, prox):
            opts = {'spawn': True}
            await prox.storm('''
                $q = $lib.queue.add(visi)
                $lib.queue.add(boom)

                $lib.dmon.add(${
                    $lib.print('Starting wootdmon')
                    $lib.queue.get(visi).put(blah)
                    for ($offs, $item) in $lib.queue.get(boom).gets(wait=1) {
                        [ inet:ipv4=$item ]
                    }
                }, name=wootdmon)

                for ($offs, $item) in $q.gets(size=1) { $q.cull($offs) }
            ''', opts=opts).list()

            await asyncio.sleep(0)

            # dmon is now fully running
            msgs = await prox.storm('dmon.list', opts=opts).list()
            self.stormIsInPrint('(wootdmon            ): running', msgs)

            dmon = list(core.stormdmons.dmons.values())[0]

            # make the dmon blow up
            q = '''$lib.queue.get(boom).put(hehe)
            $q = $lib.queue.get(visi)
            for ($offs, $item) in $q.gets(size=1) { $q.cull($offs) }
            '''
            _ = await prox.storm(q, opts=opts).list()

            self.true(await s_coro.event_wait(dmon.err_evnt, 6))

            msgs = await prox.storm('dmon.list').list()
            self.stormIsInPrint('(wootdmon            ): error', msgs)

    async def test_spawn_forked_view(self):
        async with self.getTestCoreAndProxy() as (core, prox):
            await core.nodes('[ test:str=1234 ]')
            mainview = await core.callStorm('$iden=$lib.view.get().pack().iden '
                                            'return ( $iden )')
            forkview = await core.callStorm(f'$fork=$lib.view.get({mainview}).fork() '
                                            f'return ( $fork.pack().iden )')
            await core.nodes('[ test:str=beep ]', {'view': forkview})

            opts = {'spawn': True, 'view': forkview}
            msgs = await prox.storm('test:str $lib.print($node.value()) | spin', opts).list()

            self.stormIsInPrint('1234', msgs)
            self.stormIsInPrint('beep', msgs)
