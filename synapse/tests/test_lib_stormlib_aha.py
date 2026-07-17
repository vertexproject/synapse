import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex


import synapse.tests.utils as s_test

import unittest.mock as mock

class AhaLibTest(s_test.SynTest):

    async def test_stormlib_aha_basics(self):

        async with self.getTestAha() as aha:

            with self.getTestDir() as dirn:

                dirn00 = s_common.genpath(dirn, 'cell00')
                dirn01 = s_common.genpath(dirn, 'cell01')
                dirn02 = s_common.genpath(dirn, 'cell02')
                dirn03 = s_common.genpath(dirn, 'cell03')

                replay = s_common.envbool('SYNDEV_NEXUS_REPLAY')
                # one aha:svc:add per service; registration is idempotent so a
                # nexus replay does not double the events.
                nevents = 4

                waiter = aha.waiter(nevents, 'aha:svc:add')

                cell00 = await aha.enter_context(self.addSvcToAha(aha, '00.cell', s_test.TestCell00, dirn=dirn00))
                cell01 = await aha.enter_context(self.addSvcToAha(aha, '01.cell', s_test.TestCell00, dirn=dirn01))
                cell02 = await aha.enter_context(self.addSvcToAha(aha, 'mysvc', s_test.TestCell01, dirn=dirn02))
                core00 = await aha.enter_context(self.addSvcToAha(aha, 'core', s_cortex.Cortex, dirn=dirn03))

                self.len(nevents, await waiter.wait(timeout=12))

                svcs = await core00.callStorm('$l=() for $i in $lib.aha.list() { $l.append($i) } fini { return ($l) }')
                self.len(4, svcs)

                svc = await core00.callStorm('return( $lib.aha.get(core...) )')
                self.eq('core.synapse', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(core.synapse))')
                self.eq('core.synapse', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(00.cell...))')
                self.eq('00.cell.synapse', svc.get('name'))
                # the type resolves to the current ( term-elected ) leader
                svc = await core00.callStorm('return( $lib.aha.get(testcell00...))')
                self.eq('00.cell.synapse', svc.get('name'))
                svc = await core00.callStorm('$f=({"mirror": (true)}) return( $lib.aha.get(testcell00..., filters=$f))')
                self.eq('01.cell.synapse', svc.get('name'))

                # List the aha services available
                msgs = await core00.stormlist('aha.svc.list --nexus')
                self.stormIsInPrint('Nexus', msgs)
                self.stormIsInPrint('00.cell.synapse                      true   true   true', msgs, whitespace=False)
                self.stormIsInPrint('01.cell.synapse                      false  true   true', msgs, whitespace=False)
                self.stormIsInPrint('core.synapse                         true   true   true', msgs, whitespace=False)
                self.stormIsInPrint('mysvc.synapse                        true   true   true', msgs, whitespace=False)

                msgs = await core00.stormlist('aha.svc.list')
                self.stormNotInPrint('Nexus', msgs)
                msgs = await core00.stormlist('aha.svc.stat testcell00...')

                # The connections information includes runtime information such as port/host info.
                # Omit checking part of that.
                emsg = '''Resolved testcell00... to an AHA Service.

Name:       00.cell.synapse
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     00.cell.synapse
Connection information:
    ca:         synapse
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)
                self.stormIsInPrint('    hostname:   00.cell.synapse', msgs)
                self.stormIsInPrint('    scheme:     ssl', msgs)
                self.stormIsInPrint('    user:       root', msgs)

                msgs = await core00.stormlist('aha.svc.stat --nexus testcell00...')
                emsg = '''Resolved testcell00... to an AHA Service.

Name:       00.cell.synapse
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     00.cell.synapse
Nexus:      1
Connection information:
    ca:         synapse
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)

                msgs = await core00.stormlist('aha.svc.stat --nexus 01.cell...')
                emsg = '''Resolved 01.cell... to an AHA Service.

Name:       01.cell.synapse
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     00.cell.synapse
Nexus:      1
Connection information:
    ca:         synapse
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)

                # Full name works
                msgs = await core00.stormlist('aha.svc.stat 01.cell.synapse')
                emsg = '''Resolved 01.cell.synapse to an AHA Service.

Name:       01.cell.synapse
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)

                # Shut down a service
                nevents = 2 if replay else 1
                waiter = aha.waiter(nevents, 'aha:svc:down')
                await cell01.fini()
                self.len(nevents, await waiter.wait(timeout=12))

                msgs = await core00.stormlist('aha.svc.list')
                self.stormIsInPrint('01.cell.synapse false  false  false', msgs, whitespace=False)

                # Fake a record
                await aha.addAhaSvc('00.newp...', info={'urlinfo': {'scheme': 'tcp', 'host': '0.0.0.0', 'port': '3030'}})

                msgs = await core00.stormlist('aha.svc.list --nexus')
                emsg = '00.newp.synapse                      null   false  null  0.0.0.0         3030  <offline>'
                self.stormIsInPrint(emsg, msgs, whitespace=False)

                self.none(await core00.callStorm('return($lib.aha.del(00.newp...))'))
                msgs = await core00.stormlist('aha.svc.list')
                self.stormNotInPrint('00.newp', msgs)

                # Fake a online record
                guid = s_common.guid()
                await aha.addAhaSvc('00.newp...', info={'urlinfo': {'scheme': 'tcp',
                                                                 'host': '0.0.0.0',
                                                                 'port': '3030'},
                                                     'session': guid,
                                                     })

                msgs = await core00.stormlist('aha.svc.list --nexus')
                emsg = '00.newp.synapse null   true   null  0.0.0.0         3030  ' \
                       'Failed to connect to Telepath service: "aha://00.newp.synapse/" error:'
                self.stormIsInPrint(emsg, msgs, whitespace=False)

                msgs = await core00.stormlist('aha.svc.stat --nexus 00.newp...')
                emsg = '''Resolved 00.newp... to an AHA Service.

Name:       00.newp.synapse
Online:     true
Ready:      null
Run iden:   null
Cell iden:  null
Leader:     No leadership term for this service type.
Nexus:      Failed to connect to Telepath service: "aha://00.newp.synapse/" error: [Errno 111] Connect call failed ('0.0.0.0', 3030)
Connection information:
    host:       0.0.0.0
    port:       3030
    scheme:     tcp
    user:       root'''
                self.stormIsInPrint(emsg, msgs)

                # Delete the fake service with its full service name
                self.none(await core00.callStorm('return($lib.aha.del(00.newp.synapse))'))
                self.none(await core00.callStorm('return($lib.aha.get(00.newp...))'))

                # Coverage for sad paths
                with self.raises(s_exc.NoSuchName):
                    await core00.callStorm('$lib.aha.del(axon...)')

    async def test_stormlib_aha_mirror(self):

        async with self.getTestAha() as aha:

            with self.getTestDir() as dirn:

                dirn00 = s_common.genpath(dirn, 'cell00')
                dirn01 = s_common.genpath(dirn, 'cell01')
                dirn02 = s_common.genpath(dirn, 'cell02')

                async with aha.waiter(3, 'aha:svc:add', timeout=10):

                    cell00 = await aha.enter_context(self.addSvcToAha(aha, '00.cell', s_test.TestCell00, dirn=dirn00))
                    cell01 = await aha.enter_context(self.addSvcToAha(aha, '01.cell', s_test.TestCell00, dirn=dirn01))
                    core00 = await aha.enter_context(self.addSvcToAha(aha, 'core', s_cortex.Cortex, dirn=dirn02))
                    await cell01.sync()

                # PeerGenr
                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getTasks')
                    for ($name, $info) in $lib.aha.callPeerGenr(testcell00..., $todo) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(0, resp)

                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                    for ($name, $info) in $lib.aha.callPeerGenr(testcell00..., $todo) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(4, resp)

                cell00_rid = (await cell00.getCellInfo())['cell']['run']
                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                    for $info in $lib.aha.callPeerGenr(testcell00..., $todo, skiprun=$skiprun) {
                        $resps.append($info)
                    }
                    return($resps)
                ''', opts={'vars': {'skiprun': cell00_rid}})
                self.len(2, resp)

                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getTasks')
                    for $info in $lib.aha.callPeerGenr(null, $todo) {}
                '''))

                # PeerApi
                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getCellInfo')
                    for ($name, $info) in $lib.aha.callPeerApi(testcell00..., $todo) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(2, resp)
                self.eq(resp[0][0], '00.cell.synapse')
                self.eq(resp[0][1][0], True)
                self.isinstance(resp[0][1][1], dict)

                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo(getCellInfo)
                    for ($name, $info) in $lib.aha.callPeerApi(testcell00..., $todo) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(2, resp)

                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo(getCellInfo)
                    for ($name, $info) in $lib.aha.callPeerApi(testcell00..., $todo, skiprun=$skiprun) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''', opts={'vars': {'skiprun': cell00_rid}})
                self.len(1, resp)

                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getCellInfo')
                    for ($name, $info) in $lib.aha.callPeerApi(testcell00..., $todo, timeout=(10)) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(2, resp)

                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getCellInfo')
                    for $info in $lib.aha.callPeerApi(newp..., $todo) {}
                '''))

                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getCellInfo')
                    for $info in $lib.aha.callPeerApi(null, $todo) {}
                '''))

                await self.asyncraises(s_exc.NoSuchMeth, core00.callStorm('''
                    $todo = $lib.utils.todo('bogusMethod')
                    for $info in $lib.aha.callPeerApi(testcell00..., $todo) {
                        ($ok, $info) = $info.1
                        if (not $ok) {
                            $lib.raise($info.err, $info.errmsg)
                        }
                    }
                '''))

                await aha.addAhaSvc('noiden.cell...', info={'urlinfo': {'scheme': 'tcp',
                                                                     'host': '0.0.0.0',
                                                                     'port': '3030'}})

                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getTasks')
                    for $info in $lib.aha.callPeerGenr(noiden.cell..., $todo) {}
                '''))
                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getCellInfo')
                    for $info in $lib.aha.callPeerApi(noiden.cell..., $todo) {}
                '''))

                lowuser = await core00.auth.addUser('lowuser')
                await lowuser.addRule((True, ('storm',)))
                lowopts = {'user': lowuser.iden}
                with self.raises(s_exc.AuthDeny):
                    await core00.callStorm('''
                        $todo = $lib.utils.todo('getCellInfo')
                        for ($name, $info) in $lib.aha.callPeerApi(testcell00..., $todo) {}
                    ''', opts=lowopts)

                with self.raises(s_exc.AuthDeny):
                    await core00.callStorm('''
                        $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                        for ($name, $info) in $lib.aha.callPeerGenr(testcell00..., $todo) {}
                    ''', opts=lowopts)

                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormIsInPrint('Service Mirror Groups:', msgs)
                self.stormIsInPrint('00.cell.synapse', msgs)
                self.stormIsInPrint('01.cell.synapse', msgs)
                self.stormIsInPrint('Group Status: In Sync', msgs)

                msgs = await core00.stormlist('aha.svc.mirror --timeout 30')
                self.stormIsInPrint('Service Mirror Groups:', msgs)
                self.stormIsInPrint('Group Status: In Sync', msgs)

                async def mockCellInfo():
                    return {
                        'cell': {'ready': True, 'nexsindx': 10, 'active': True},
                        'synapse': {'version': '2.190.0'},
                    }

                async def mockOutOfSyncCellInfo():
                    return {
                        'cell': {'ready': True, 'nexsindx': 5, 'active': False},
                        'synapse': {'version': '2.190.0'},
                    }

                with mock.patch.object(cell00, 'getCellInfo', mockCellInfo):
                    with mock.patch.object(cell01, 'getCellInfo', mockOutOfSyncCellInfo):
                        async def mock_call_aha(*args, **kwargs):
                            todo = args[1]
                            if todo[0] == 'waitNexsOffs':
                                yield ('00.cell.synapse', (True, True))
                                yield ('01.cell.synapse', (True, True))
                            elif todo[0] == 'getCellInfo':
                                if not hasattr(mock_call_aha, 'called'):
                                    mock_call_aha.called = True
                                    yield ('00.cell.synapse', (True, await mockCellInfo()))
                                    yield ('01.cell.synapse', (True, await mockOutOfSyncCellInfo()))
                                else:
                                    yield ('00.cell.synapse', (True, await mockCellInfo()))
                                    yield ('01.cell.synapse', (True, await mockCellInfo()))

                        with mock.patch.object(aha, 'callAhaPeerApi', mock_call_aha):
                            msgs = await core00.stormlist('aha.svc.mirror --wait')
                            self.stormIsInPrint('Group Status: Out of Sync', msgs)
                            self.stormIsInPrint('Updated status:', msgs)
                            self.stormIsInPrint('Group Status: In Sync', msgs)

                with mock.patch.object(cell00, 'getCellInfo', mockCellInfo):
                    with mock.patch.object(cell01, 'getCellInfo', mockOutOfSyncCellInfo):
                        msgs = await core00.stormlist('aha.svc.mirror --timeout 1')
                        self.stormIsInPrint('Group Status: Out of Sync', msgs)

                await cell01.nexsroot.client.fini()
                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormIsInPrint('follower', msgs)

                await aha.delAhaSvc('00.cell...')
                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormNotInPrint('Service Mirror Groups:', msgs)
