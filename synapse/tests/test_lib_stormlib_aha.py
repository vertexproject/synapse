import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.cell as s_cell

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
                nevents = 10 if replay else 5

                waiter = aha.waiter(nevents, 'aha:svcadd')

                cell00 = await aha.enter_context(self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=dirn00))
                cell01 = await aha.enter_context(self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=dirn01,
                                                                  provinfo={'mirror': 'cell'}))
                cell02 = await aha.enter_context(self.addSvcToAha(aha, 'mysvc', s_cell.Cell, dirn=dirn02))
                core00 = await aha.enter_context(self.addSvcToAha(aha, 'core', s_cortex.Cortex, dirn=dirn03))

                self.len(nevents, await waiter.wait(timeout=12))

                svcs = await core00.callStorm('$l=() for $i in $lib.aha.list() { $l.append($i) } fini { return ($l) }')
                self.len(5, svcs)

                svc = await core00.callStorm('return( $lib.aha.get(core...) )')
                self.eq('core.synapse', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(core.synapse))')
                self.eq('core.synapse', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(00.cell...))')
                self.eq('00.cell.synapse', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(cell...))')
                self.eq('cell.synapse', svc.get('name'))
                svc = await core00.callStorm('$f=({"mirror": (true)}) return( $lib.aha.get(cell..., filters=$f))')
                self.eq('01.cell.synapse', svc.get('name'))

                # List the aha services available
                msgs = await core00.stormlist('aha.svc.list --nexus')
                self.stormIsInPrint('Nexus', msgs)
                self.stormIsInPrint('00.cell.synapse                      true   true   true', msgs, whitespace=False)
                self.stormIsInPrint('01.cell.synapse                      false  true   true', msgs, whitespace=False)
                self.stormIsInPrint('cell.synapse                         true   true   true', msgs, whitespace=False)
                self.stormIsInPrint('core.synapse                         null   true   true', msgs, whitespace=False)
                self.stormIsInPrint('mysvc.synapse                        null   true   true', msgs, whitespace=False)

                msgs = await core00.stormlist('aha.svc.list')
                self.stormNotInPrint('Nexus', msgs)
                msgs = await core00.stormlist('aha.svc.stat cell...')

                # The connections information includes runtime information such as port/host info.
                # Omit checking part of that.
                emsg = '''Resolved cell... to an AHA Service.

Name:       cell.synapse
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     cell
Connection information:
    ca:         synapse
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)
                self.stormIsInPrint('    hostname:   00.cell.synapse', msgs)
                self.stormIsInPrint('    scheme:     ssl', msgs)
                self.stormIsInPrint('    user:       root', msgs)

                msgs = await core00.stormlist('aha.svc.stat --nexus cell...')
                emsg = '''Resolved cell... to an AHA Service.

Name:       cell.synapse
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     cell
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
Leader:     cell
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

                # No item for pool00 yet..
                msgs = await core00.stormlist('aha.svc.stat pool00...')
                self.stormIsInPrint('No service found for: "pool00..."', msgs)

                msgs = await core00.stormlist('aha.pool.add pool00...')
                self.stormHasNoWarnErr(msgs)
                msgs = await core00.stormlist('aha.pool.svc.add pool00... 00.cell...')
                self.stormHasNoWarnErr(msgs)

                msgs = await core00.stormlist('aha.svc.stat --nexus pool00...')
                emsg = '''Resolved pool00... to an AHA Pool.

The pool currently has 1 members.
AHA Pool:   pool00.synapse
Member:     00.cell.synapse'''
                self.stormIsInPrint(emsg, msgs)

                # Shut down a service
                nevents = 2 if replay else 1
                waiter = aha.waiter(nevents, 'aha:svcdown')
                await cell01.fini()
                self.len(nevents, await waiter.wait(timeout=12))

                msgs = await core00.stormlist('aha.svc.list')
                self.stormIsInPrint('01.cell.synapse false  false  false', msgs, whitespace=False)

                # Fake a record
                await aha.addAhaSvc('00.newp', info={'urlinfo': {'scheme': 'tcp', 'host': '0.0.0.0', 'port': '3030'}},
                                    network='synapse')

                msgs = await core00.stormlist('aha.svc.list --nexus')
                emsg = '00.newp.synapse                      null   false  null  0.0.0.0         3030  <offline>'
                self.stormIsInPrint(emsg, msgs, whitespace=False)

                self.none(await core00.callStorm('return($lib.aha.del(00.newp...))'))
                msgs = await core00.stormlist('aha.svc.list')
                self.stormNotInPrint('00.newp', msgs)

                # Fake a online record
                guid = s_common.guid()
                await aha.addAhaSvc('00.newp', info={'urlinfo': {'scheme': 'tcp',
                                                                 'host': '0.0.0.0',
                                                                 'port': '3030'},
                                                     'online': guid,
                                                     },
                                    network='synapse')
                msgs = await core00.stormlist('aha.svc.list --nexus')
                emsg = '00.newp.synapse null   true   null  0.0.0.0         3030  ' \
                       'Failed to connect to Telepath service: "aha://00.newp.synapse/" error:'
                self.stormIsInPrint(emsg, msgs, whitespace=False)

                msgs = await core00.stormlist('aha.svc.stat --nexus 00.newp...')
                emsg = '''Resolved 00.newp... to an AHA Service.

Name:       00.newp.synapse
Online:     true
Ready:      null
Run iden:   $lib.null
Cell iden:  $lib.null
Leader:     Service did not register itself with a leader name.
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
                with self.raises(s_exc.BadArg):
                    await core00.callStorm('$lib.aha.del(pool00...)')

                with self.raises(s_exc.NoSuchName):
                    await core00.callStorm('$lib.aha.del(axon...)')

    async def test_stormlib_aha_mirror(self):

        async with self.getTestAha() as aha:

            with self.getTestDir() as dirn:

                dirn00 = s_common.genpath(dirn, 'cell00')
                dirn01 = s_common.genpath(dirn, 'cell01')
                dirn02 = s_common.genpath(dirn, 'cell02')

                async with aha.waiter(3, 'aha:svcadd', timeout=10):

                    cell00 = await aha.enter_context(self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=dirn00))
                    cell01 = await aha.enter_context(self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=dirn01,
                                                                      provinfo={'mirror': 'cell'}))
                    core00 = await aha.enter_context(self.addSvcToAha(aha, 'core', s_cortex.Cortex, dirn=dirn02))
                    await cell01.sync()

                # PeerGenr
                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getTasks')
                    for ($name, $info) in $lib.aha.callPeerGenr(cell..., $todo) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(0, resp)

                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                    for ($name, $info) in $lib.aha.callPeerGenr(cell..., $todo) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(4, resp)

                cell00_rid = (await cell00.getCellInfo())['cell']['run']
                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                    for $info in $lib.aha.callPeerGenr(cell..., $todo, skiprun=$skiprun) {
                        $resps.append($info)
                    }
                    return($resps)
                ''', opts={'vars': {'skiprun': cell00_rid}})
                self.len(2, resp)

                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getTasks')
                    $lib.aha.callPeerGenr(null, $todo)
                '''))

                # PeerApi
                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getCellInfo')
                    for ($name, $info) in $lib.aha.callPeerApi(cell..., $todo) {
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
                    for ($name, $info) in $lib.aha.callPeerApi(cell..., $todo) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(2, resp)

                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo(getCellInfo)
                    for ($name, $info) in $lib.aha.callPeerApi(cell..., $todo, skiprun=$skiprun) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''', opts={'vars': {'skiprun': cell00_rid}})
                self.len(1, resp)

                resp = await core00.callStorm('''
                    $resps = ()
                    $todo = $lib.utils.todo('getCellInfo')
                    for ($name, $info) in $lib.aha.callPeerApi(cell..., $todo, timeout=(10)) {
                        $resps.append(($name, $info))
                    }
                    return($resps)
                ''')
                self.len(2, resp)

                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getCellInfo')
                    $lib.aha.callPeerApi(newp..., $todo)
                '''))

                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getCellInfo')
                    $lib.aha.callPeerApi(null, $todo)
                '''))

                await self.asyncraises(s_exc.NoSuchMeth, core00.callStorm('''
                    $todo = $lib.utils.todo('bogusMethod')
                    for $info in $lib.aha.callPeerApi(cell..., $todo) {
                        ($ok, $info) = $info.1
                        if (not $ok) {
                            $lib.raise($info.err, $info.errmsg)
                        }
                    }
                '''))

                await aha.addAhaSvc('noiden.cell', info={'urlinfo': {'scheme': 'tcp',
                                                                     'host': '0.0.0.0',
                                                                     'port': '3030'}},
                                  network='synapse')
                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getTasks')
                    $lib.aha.callPeerGenr(noiden.cell..., $todo)
                '''))
                await self.asyncraises(s_exc.NoSuchName, core00.callStorm('''
                    $todo = $lib.utils.todo('getCellInfo')
                    $lib.aha.callPeerApi(noiden.cell..., $todo)
                '''))

                lowuser = await core00.auth.addUser('lowuser')
                await lowuser.addRule((True, ('storm',)))
                lowopts = {'user': lowuser.iden}
                with self.raises(s_exc.AuthDeny):
                    await core00.callStorm('''
                        $todo = $lib.utils.todo('getCellInfo')
                        for ($name, $info) in $lib.aha.callPeerApi(cell..., $todo) {}
                    ''', opts=lowopts)

                with self.raises(s_exc.AuthDeny):
                    await core00.callStorm('''
                        $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                        for ($name, $info) in $lib.aha.callPeerGenr(cell..., $todo) {}
                    ''', opts=lowopts)

                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormIsInPrint('Service Mirror Groups:', msgs)
                self.stormIsInPrint('cell.synapse', msgs)
                self.stormIsInPrint('00.cell.synapse', msgs)
                self.stormIsInPrint('01.cell.synapse', msgs)
                self.stormIsInPrint('Group Leader: 00.cell.synapse', msgs)
                self.stormIsInPrint('Group Status: In Sync', msgs)

                # Each member reports the service it mirrors from.
                self.stormIsInPrint('follows', msgs)
                self.stormIsInPrint('00.cell.synapse leader True True', msgs, whitespace=False)
                self.stormIsInPrint('<none - write root>', msgs)
                self.stormIsInPrint('aha://root@cell...', msgs)

                msgs = await core00.stormlist('aha.svc.mirror --timeout 30')
                self.stormIsInPrint('Service Mirror Groups:', msgs)
                self.stormIsInPrint('Group Status: In Sync', msgs)

                # AHA de-duplicates peer responses by run iden and may label the leader
                # response with the leader alias name rather than the member name. The
                # leader must still be attributed to its member row.
                cell01_rid = (await cell01.getCellInfo())['cell']['run']

                async def mock_alias_named(*args, **kwargs):
                    yield ('cell.synapse', (True, {
                        'cell': {'run': cell00_rid, 'ready': True, 'nexsindx': 99, 'active': True,
                                 'verstring': '2.190.0', 'mirror': None},
                        'synapse': {'verstring': '2.190.0'},
                    }))
                    yield ('01.cell.synapse', (True, {
                        'cell': {'run': cell01_rid, 'ready': True, 'nexsindx': 99, 'active': False,
                                 'verstring': '2.190.0', 'mirror': 'aha://root@cell...'},
                        'synapse': {'verstring': '2.190.0'},
                    }))

                with mock.patch.object(aha, 'callAhaPeerApi', mock_alias_named):
                    msgs = await core00.stormlist('aha.svc.mirror')
                    self.stormIsInPrint('00.cell.synapse leader', msgs, whitespace=False)
                    self.stormIsInPrint('01.cell.synapse follower', msgs, whitespace=False)
                    self.stormIsInPrint('Group Status: In Sync', msgs)
                    self.stormNotInPrint('<unknown>', msgs)

                async def mockCellInfo():
                    return {
                        'cell': {'ready': True, 'nexsindx': 10, 'active': True},
                        'synapse': {'verstring': '2.190.0'},
                    }

                async def mockOutOfSyncCellInfo():
                    return {
                        'cell': {'ready': True, 'nexsindx': 5, 'active': False},
                        'synapse': {'verstring': '2.190.0'},
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

                # No member reports as active, so the group has no claimed leader and
                # there is nothing to wait on.
                async def mockNoLeaderCellInfo():
                    return {
                        'cell': {'ready': True, 'nexsindx': 7, 'active': False},
                        'synapse': {'verstring': '2.190.0'},
                    }

                with mock.patch.object(cell00, 'getCellInfo', mockNoLeaderCellInfo):
                    with mock.patch.object(cell01, 'getCellInfo', mockOutOfSyncCellInfo):

                        msgs = await core00.stormlist('aha.svc.mirror --timeout 1')
                        self.stormIsInPrint('Group Leader: <none>', msgs)
                        self.stormIsInPrint('Group Status: Out of Sync', msgs)
                        self.stormNotInPrint('leader', msgs)

                        msgs = await core00.stormlist('aha.svc.mirror --timeout 1 --wait')
                        self.stormIsInWarn('Skipping --wait: the group has no active leader.', msgs)
                        self.stormNotInPrint('Updated status:', msgs)

                # Two services both claiming to be active is a split brain.
                with mock.patch.object(cell00, 'getCellInfo', mockCellInfo):
                    with mock.patch.object(cell01, 'getCellInfo', mockCellInfo):
                        msgs = await core00.stormlist('aha.svc.mirror --timeout 1')
                        self.stormIsInPrint('Group Leader: <multiple: 00.cell.synapse, 01.cell.synapse>', msgs)

                # A group where no member responded tells us nothing about replication
                # and must not be reported as in sync.
                async def mock_all_failed(*args, **kwargs):
                    yield ('00.cell.synapse', (False, 'error'))
                    yield ('01.cell.synapse', (False, 'error'))

                with mock.patch.object(aha, 'callAhaPeerApi', mock_all_failed):
                    msgs = await core00.stormlist('aha.svc.mirror --timeout 1')
                    self.stormIsInPrint('Group Status: Unknown', msgs)
                    self.stormIsInPrint('Group Leader: <none>', msgs)

                    msgs = await core00.stormlist('aha.svc.mirror --timeout 1 --wait')
                    self.stormIsInWarn('Skipping --wait: the group has no active leader.', msgs)

                # An unresponsive member can never satisfy the wait loop.
                async def mock_partial(*args, **kwargs):
                    yield ('00.cell.synapse', (True, {
                        'cell': {'run': cell00_rid, 'ready': True, 'nexsindx': 12, 'active': True,
                                 'verstring': '2.190.0', 'mirror': None},
                        'synapse': {'verstring': '2.190.0'},
                    }))

                with mock.patch.object(aha, 'callAhaPeerApi', mock_partial):
                    msgs = await core00.stormlist('aha.svc.mirror --timeout 1 --wait')
                    self.stormIsInWarn('Skipping --wait: one or more group members did not respond.', msgs)

                await cell01.nexsroot.client.fini()
                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormIsInPrint('follower', msgs)

                # A service which registered without the group leader name still belongs
                # to the group, since mirrors share a cell iden.
                svcinfo = dict((await aha.getAhaSvc('00.cell...'))['svcinfo'])
                svcinfo.pop('leader', None)
                svcinfo['run'] = s_common.guid()
                svcinfo['urlinfo'] = dict(svcinfo['urlinfo'])
                svcinfo['urlinfo']['hostname'] = '02.cell.synapse'
                await aha.addAhaSvc('02.cell', info=svcinfo, network='synapse')

                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormIsInPrint('02.cell.synapse', msgs)

                await aha.delAhaSvc('02.cell', network='synapse')

                # Entries with no cell iden or no run iden cannot be correlated at all.
                await aha.addAhaSvc('noiden.cell', info={'urlinfo': {'scheme': 'tcp',
                                                                    'host': '0.0.0.0',
                                                                    'port': '3030'}},
                                    network='synapse')
                norun = dict(svcinfo)
                norun.pop('run', None)
                await aha.addAhaSvc('norun.cell', info=norun, network='synapse')

                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormNotInPrint('noiden.cell.synapse', msgs)
                self.stormNotInPrint('norun.cell.synapse', msgs)

                await aha.delAhaSvc('norun.cell', network='synapse')

                # The group is still reported when no service has claimed the leader
                # name, which is when an operator most needs to see it.
                await aha.delAhaSvc('cell', network='synapse')

                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormIsInPrint('Service Mirror Groups:', msgs)
                self.stormIsInPrint('cell.synapse (leader alias not registered)', msgs)
                self.stormIsInPrint('00.cell.synapse', msgs)
                self.stormIsInPrint('01.cell.synapse', msgs)

                await aha.delAhaSvc('00.cell', network='synapse')
                msgs = await core00.stormlist('aha.svc.mirror')
                self.stormNotInPrint('Service Mirror Groups:', msgs)
                self.stormIsInPrint('No mirror groups found.', msgs)
