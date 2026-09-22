import os
import shutil
import importlib

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils

import synapse.tools.aha.list as s_a_list
import synapse.tools.aha.clone as s_a_clone
import synapse.tools.aha.enroll as s_a_enroll
import synapse.tools.aha.mirror as s_a_mirror
import synapse.tools.aha.easycert as s_a_easycert
import synapse.tools.aha.provision.user as s_a_provision_user

class AhaToolsTest(s_t_utils.SynTest):

    async def test_aha_list(self):

        async with self.getTestAha() as aha:

            conf0 = {'aha:provision': await aha.addAhaSvcProv('cell0')}

            ahaurl = aha.getLocalUrl()

            async with self.getTestCell(s_t_utils.TestCell00, conf=conf0) as cell0:

                await aha._waitAhaSvcOnline('cell0...')

                # register a synthetic leader / follower pair to exercise the
                # Leader column, which is managed by the AHA leadership terms.
                await aha.addAhaSvc('00.mir.synapse', {
                    'iden': 'mirror-iden',
                    'run': 'run00',
                    'type': 'mir',
                    'urlinfo': {'scheme': 'tcp', 'host': '127.0.0.1', 'port': 4400},
                })
                await aha.addAhaSvc('01.mir.synapse', {
                    'iden': 'mirror-iden',
                    'run': 'run01',
                    'type': 'mir',
                    'urlinfo': {'scheme': 'tcp', 'host': '127.0.0.1', 'port': 4401},
                })
                await aha.setLeadTerm('mir', '00.mir.synapse', 1)

                argv = ['--url', ahaurl]
                retn, outp = await self.execToolMain(s_a_list.main, argv)
                self.eq(retn, 0)

                outp.expect('Service Leader', whitespace=False)
                outp.expect('cell0.synapse True', whitespace=False)

                outs = ' '.join(str(outp).split())
                self.isin('00.mir.synapse True', outs)
                self.isin('01.mir.synapse False', outs)

        async with self.getTestCore() as core:
            curl = core.getLocalUrl()
            argv = ['--url', curl]
            retn, outp = await self.execToolMain(s_a_list.main, argv)
            self.eq(1, retn)
            outp.expect(f'Service at {curl} is not an Aha server')

    async def test_aha_del(self):

        # 'del' is a keyword, so the module cannot be imported by name
        s_a_del = importlib.import_module('synapse.tools.aha.del')

        async with self.getTestAha() as aha:

            ahaurl = aha.getLocalUrl()

            # register a synthetic service entry to remove
            await aha.addAhaSvc('000.del.synapse', {
                'iden': 'del-iden',
                'run': 'run00',
                'type': 'del',
                'urlinfo': {'scheme': 'tcp', 'host': '127.0.0.1', 'port': 4400},
            })
            self.nn(await aha.getAhaSvc('000.del.synapse'))

            argv = ['--url', ahaurl, '000.del.synapse']
            retn, outp = await self.execToolMain(s_a_del.main, argv)
            self.eq(retn, 0)
            outp.expect('Removed AHA service entry: 000.del.synapse')

            # the entry is gone
            self.none(await aha.getAhaSvc('000.del.synapse'))

        # a non-AHA service reports an error rather than deleting anything
        async with self.getTestCore() as core:
            curl = core.getLocalUrl()
            retn, outp = await self.execToolMain(s_a_del.main, ['--url', curl, '000.del.synapse'])
            self.eq(1, retn)
            outp.expect('ERROR:')

    async def test_aha_easycert(self):

        async with self.getTestAha() as aha:

            ahaurl = aha.getLocalUrl()

            with self.getTestSynDir() as syndir, self.getTestDir() as dirn:

                argvbase = ['--aha', ahaurl, '--certdir', dirn]

                argv = argvbase + ['--server', '--server-sans', 'DNS:beeper.demo.net,DNS:booper.demo.net',
                                   'beep.demo.net']

                retn, outp = await self.execToolMain(s_a_easycert.main, argv)

                self.eq(retn, 0)
                outp.expect('key saved')
                outp.expect('hosts/beep.demo.net.key')
                outp.expect('crt saved')
                outp.expect('hosts/beep.demo.net.crt')

                argv = argvbase + ['mallory@synapse']
                retn, outp = await self.execToolMain(s_a_easycert.main, argv)
                self.eq(retn, 0)
                outp.expect('key saved')
                outp.expect('users/mallory@synapse.key')
                outp.expect('crt saved')
                outp.expect('users/mallory@synapse.crt')

    async def test_aha_enroll(self):

        async with self.getTestAha() as aha:

            argv = ['--url', aha.getLocalUrl(), '01.aha.loop.vertex.link']
            retn, outp = await self.execToolMain(s_a_clone.main, argv)
            self.eq(retn, 0)
            self.isin('one-time use URL:', str(outp))

            argv = ['--url', aha.getLocalUrl(), '01.aha.loop.vertex.link', '--only-url']
            retn, outp = await self.execToolMain(s_a_clone.main, argv)
            self.eq(retn, 0)
            self.notin('one-time use URL:', str(outp))

            argv = ['--url', 'newp://1.2.3.4', '01.aha.loop.vertex.link']
            retn, outp = await self.execToolMain(s_a_clone.main, argv)
            self.eq(retn, 1)
            self.isin('ERROR: Invalid URL scheme: newp', str(outp))

            argv = ['--url', aha.getLocalUrl(), 'visi']
            retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
            self.isin('one-time use URL:', str(outp))

            provurl = str(outp).split(':', 1)[1].strip()
            with self.getTestSynDir() as syndir:

                capath = s_common.genpath(syndir, 'certs', 'cas', 'synapse.crt')
                crtpath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.crt')
                keypath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.crt')

                retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))
                self.eq(0, retn)

                for path in (capath, crtpath, keypath):
                    self.true(os.path.isfile(path))
                    self.gt(os.path.getsize(path), 0)

                teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                self.eq(teleyaml.get('version'), 1)
                self.len(1, teleyaml.get('aha:servers'))

                shutil.rmtree(s_common.genpath(syndir, 'certs'))

                argv = ['--again', '--url', aha.getLocalUrl(), 'visi']
                retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
                self.eq(retn, 0)
                self.isin('one-time use URL:', str(outp))

                provurl = str(outp).split(':', 1)[1].strip()

                retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))

                # Just return the URL
                retn, outp = await self.execToolMain(s_a_provision_user.main, argv + ['--only-url'])
                self.eq(retn, 0)
                self.notin('one-time use URL:', str(outp))
                self.isin('ssl://', str(outp))

            with self.getTestSynDir() as syndir:

                argv = ['--again', '--url', aha.getLocalUrl(), 'visi']
                retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
                self.eq(retn, 0)
                provurl = str(outp).split(':', 1)[1].strip()

                capath = s_common.genpath(syndir, 'certs', 'cas', 'synapse.crt')
                crtpath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.crt')
                keypath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.key')

                for path in (capath, crtpath, keypath):
                    s_common.genfile(path)

                retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))
                self.eq(0, retn)

                for path in (capath, crtpath, keypath):
                    self.gt(os.path.getsize(path), 0)

                teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                self.eq(teleyaml.get('version'), 1)

    async def test_aha_mirror(self):

        async with self.getTestAha() as aha:

            base_svcinfo = {
                'iden': 'test_iden',
                'parent': 'leader',
                'urlinfo': {
                    'scheme': 'tcp',
                    'host': '127.0.0.1',
                    'port': 0,
                    'hostname': 'test.host'
                }
            }

            conf_no_iden = {'aha:provision': await aha.addAhaSvcProv('no.iden')}
            async with self.getTestCell(s_t_utils.TestCell00, conf=conf_no_iden) as cell_no_iden:
                # getTestCell does not wait for AHA registration; ensure the real
                # service is registered so its later removal pops the lead term.
                await aha._waitAhaSvcOnline('no.iden...', timeout=10)
                svcinfo = {k: v for k, v in base_svcinfo.items() if k != 'iden'}
                await aha.addAhaSvc('no.iden', svcinfo)

                argv = ['--url', aha.getLocalUrl()]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 0)
                outp.expect('No mirror groups found.')
                self.notin('no.iden', str(outp))

            # remove the record so its ( now offline ) service type does not
            # block the next generic service of the same type from registering.
            await aha._waitAhaSvcDown('no.iden...', timeout=10)
            await aha.delAhaSvc('no.iden...')

            conf_no_host = {'aha:provision': await aha.addAhaSvcProv('no.host')}
            async with self.getTestCell(s_t_utils.TestCell00, conf=conf_no_host) as cell_no_host:
                await aha._waitAhaSvcOnline('no.host...', timeout=10)
                svcinfo = dict(base_svcinfo)
                # a unique iden keeps this a singleton ( non-grouped ) mock entry
                svcinfo['iden'] = 'iden_no_host'
                svcinfo['urlinfo'] = {k: v for k, v in base_svcinfo['urlinfo'].items() if k != 'hostname'}
                await aha.addAhaSvc('no.host', svcinfo)

                argv = ['--url', aha.getLocalUrl()]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 0)
                outp.expect('No mirror groups found.')
                self.notin('no.host', str(outp))

            await aha._waitAhaSvcDown('no.host...', timeout=10)
            await aha.delAhaSvc('no.host...')

            conf_no_parent = {'aha:provision': await aha.addAhaSvcProv('no.parent')}
            async with self.getTestCell(s_t_utils.TestCell00, conf=conf_no_parent) as cell_no_parent:
                await aha._waitAhaSvcOnline('no.parent...', timeout=10)
                svcinfo = {k: v for k, v in base_svcinfo.items() if k != 'parent'}
                # a unique iden keeps this a singleton ( non-grouped ) mock entry
                svcinfo['iden'] = 'iden_no_parent'
                await aha.addAhaSvc('no.parent', svcinfo)

                argv = ['--url', aha.getLocalUrl()]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 0)
                outp.expect('No mirror groups found.')
                self.notin('no.parent', str(outp))

            await aha._waitAhaSvcDown('no.parent...', timeout=10)
            await aha.delAhaSvc('no.parent...')

            conf_no_primary = {'aha:provision': await aha.addAhaSvcProv('no.primary')}
            async with self.getTestCell(s_t_utils.TestCell00, conf=conf_no_primary) as cell_no_primary:
                await aha._waitAhaSvcOnline('no.primary...', timeout=10)
                svcinfo = dict(base_svcinfo)
                svcinfo['urlinfo']['hostname'] = 'nonexistent.host'
                await aha.addAhaSvc('no.primary', svcinfo)

            await aha._waitAhaSvcDown('no.primary...', timeout=10)
            await aha.delAhaSvc('no.primary...')

            # the churn above registered and removed several testcell00 services;
            # wait for the leadership term to be popped so 00.cell boots as a
            # clean leader rather than following a stale ( removed ) term.
            for _ in range(100):
                if aha._getLeadTerm('testcell00') is None:
                    break

                await aha.waitfini(timeout=0.1)  # pragma: no cover

            self.none(aha._getLeadTerm('testcell00'))

            conf = {'aha:provision': await aha.addAhaSvcProv('00.cell')}
            cell00 = await aha.enter_context(self.getTestCell(s_t_utils.TestCell00, conf=conf))

            # ensure the type resolves to an online leader before booting the
            # mirror, which follows the leader via aha://testcell00...
            await aha._waitAhaSvcLeader(cell00.getCellType(), timeout=10)

            conf = {'aha:provision': await aha.addAhaSvcProv('01.cell')}
            cell01 = await aha.enter_context(self.getTestCell(s_t_utils.TestCell00, conf=conf))

            await cell01.sync()

            ahaurl = aha.getLocalUrl()

            argv = ['--url', ahaurl]
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 0)
            outp.expect('Service Mirror Groups:')
            outp.expect('00.cell.synapse')
            outp.expect('01.cell.synapse')
            outp.expect('Group Status: In Sync')

            argv = ['--url', ahaurl, '--timeout', '30']
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 0)

            argv = ['--url', 'tcp://newp:1234/']
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 1)
            outp.expect('ERROR:')

            async def mockCellInfo():
                return {
                    'cell': {'ready': True, 'nexus': {'indx': 10}, 'active': True},
                    'synapse': {'version': s_version.version},
                }

            async def mockOutOfSyncCellInfo():
                return {
                    'cell': {'ready': True, 'nexus': {'indx': 5}, 'active': False},
                    'synapse': {'version': s_version.version},
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
                        argv = ['--url', ahaurl, '--wait']
                        retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                        self.eq(retn, 0)
                        outp.expect('Group Status: Out of Sync')
                        outp.expect('Updated status:')
                        outp.expect('Group Status: In Sync')

            with mock.patch.object(cell00, 'getCellInfo', mockCellInfo):
                with mock.patch.object(cell01, 'getCellInfo', mockOutOfSyncCellInfo):
                    argv = ['--url', ahaurl, '--timeout', '1']
                    retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                    self.eq(retn, 0)
                    outp.expect('Group Status: Out of Sync')

            async with self.getTestCore() as core:
                curl = core.getLocalUrl()
                argv = ['--url', curl]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(1, retn)
                outp.expect(f'Service at {curl} is not an Aha server')

            async with aha.waiter(1, 'aha:svc:add', timeout=10):

                conf = {'aha:provision': await aha.addAhaSvcProv('02.cell')}
                cell02 = await aha.enter_context(self.getTestCell(s_t_utils.TestCell00, conf=conf))
                await cell02.sync()

            async def mock_failed_api(*args, **kwargs):
                yield ('00.cell.synapse', (True, {'cell': {'ready': True, 'nexus': {'indx': 10}, 'active': True}}))
                yield ('01.cell.synapse', (False, 'error'))
                yield ('02.cell.synapse', (True, {'cell': {'ready': True, 'nexus': {'indx': 12}, 'active': False}}))

            with mock.patch.object(aha, 'callAhaPeerApi', mock_failed_api):
                argv = ['--url', ahaurl, '--timeout', '1']
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                outp.expect('00.cell.synapse                          leader     True     True    127.0.0.1', whitespace=False)
                outp.expect('02.cell.synapse                          follower   True     True    127.0.0.1', whitespace=False)
                outp.expect('01.cell.synapse                          <unknown>  True     True', whitespace=False)

                # the responding peers report their nexus offset; the failed one does
                # not, so the group cannot be in sync. ( SYN-11129 )
                outp.expect('10 <unknown>', whitespace=False)
                outp.expect('12 <unknown>', whitespace=False)
                outp.expect('Group Leader: 00.cell.synapse')
                outp.expect('Group Status: Out of Sync')

        self.eq(s_a_mirror.timeout_type('30'), 30)
        self.eq(s_a_mirror.timeout_type('0'), 0)

        with self.raises(s_exc.BadArg) as cm:
            s_a_mirror.timeout_type('-1')
        self.isin('is not a valid non-negative integer', cm.exception.get('mesg'))

        with self.raises(s_exc.BadArg) as cm:
            s_a_mirror.timeout_type('foo')
        self.isin('is not a valid non-negative integer', cm.exception.get('mesg'))

        synerr = s_exc.SynErr(mesg='Oof')
        with mock.patch('synapse.telepath.openurl', side_effect=synerr):
            argv = ['--url', 'tcp://test:1234/']
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 1)
            outp.expect('ERROR: Oof')

    async def test_aha_mirror_leader_status(self):
        '''
        AHA derives the leader flag from the leadership term name alone, so it stays
        set on a service which is down. Check that the reported leader distinguishes
        the term holder from the service actually running as leader.
        '''
        def svcentry(name, iden, leader=False, online=True):
            return {
                'name': name,
                'leader': leader,
                'online': online,
                'info': {
                    'iden': iden,
                    'run': f'run_{name}',
                    'type': 'testcell00',
                    'urlinfo': {'scheme': 'tcp', 'host': '127.0.0.1', 'port': 0, 'hostname': name},
                },
            }

        def cellinfo(active, indx=10):
            return {'cell': {'active': active, 'nexus': {'indx': indx}, 'version': '3.0.0',
                             'parent': None},
                    'synapse': {'version': '3.0.0'}}

        async with self.getTestAha() as aha:

            argv = ['--url', aha.getLocalUrl(), '--timeout', '1']

            async def run(svcs, infos, extra=(), raises=None):
                async def mock_svcs(*a, **k):
                    for svc in svcs:
                        yield svc

                async def mock_peers(*a, **k):
                    if raises is not None:
                        raise raises
                    for name, info in infos.items():
                        yield (name, (True, info))

                with mock.patch.object(aha, 'getAhaSvcs', mock_svcs):
                    with mock.patch.object(aha, 'callAhaPeerApi', mock_peers):
                        retn, outp = await self.execToolMain(s_a_mirror.main, argv + list(extra))
                        self.eq(retn, 0)
                        return outp

            lead = svcentry('00.cell.synapse', 'iden00', leader=True)
            mirr = svcentry('01.cell.synapse', 'iden00')

            # the term holder is the service reporting itself active
            outp = await run([lead, mirr],
                             {'00.cell.synapse': cellinfo(True), '01.cell.synapse': cellinfo(False)})
            outp.expect('Group Leader: 00.cell.synapse')
            outp.expect('Group Status: In Sync')

            # the term holder is live but another service is actually running as leader
            outp = await run([lead, mirr],
                             {'00.cell.synapse': cellinfo(False), '01.cell.synapse': cellinfo(True)})
            outp.expect('Group Leader: 00.cell.synapse (inactive; 01.cell.synapse reports active)')

            # nobody is running as leader
            outp = await run([lead, mirr],
                             {'00.cell.synapse': cellinfo(False), '01.cell.synapse': cellinfo(False)})
            outp.expect('Group Leader: 00.cell.synapse (inactive)')

            # two services both claiming to be active is a split brain
            outp = await run([lead, mirr],
                             {'00.cell.synapse': cellinfo(True), '01.cell.synapse': cellinfo(True)})
            outp.expect('Group Leader: 00.cell.synapse (also active: 01.cell.synapse)')

            # the term holder is registered but down
            downlead = svcentry('00.cell.synapse', 'iden00', leader=True, online=False)
            outp = await run([downlead, mirr], {'01.cell.synapse': cellinfo(False)})
            outp.expect('Group Leader: 00.cell.synapse (offline)')

            # no service of this type holds a leadership term
            outp = await run([svcentry('00.cell.synapse', 'iden00'), mirr],
                             {'00.cell.synapse': cellinfo(False), '01.cell.synapse': cellinfo(False)})
            outp.expect('Group Leader: <no term>')

            # no member responded, so nothing can be said about replication
            outp = await run([lead, mirr], {})
            outp.expect('Group Status: Unknown')

            # AHA never reaps entries, so an entirely offline group is not reported
            outp = await run([svcentry('00.cell.synapse', 'iden00', leader=True, online=False),
                              svcentry('01.cell.synapse', 'iden00', online=False)], {})
            outp.expect('No mirror groups found.')

            # an error raised while querying the group members must not abort the report
            outp = await run([lead, mirr], {}, raises=s_exc.SynErr(mesg='boom'))
            outp.expect('WARNING: Failed to query mirror group members: boom')
            outp.expect('Group Status: Unknown')

            # without a single active leader there is no replication to wait on
            # ( the offsets differ so the group is out of sync and --wait is reached )
            outp = await run([lead, mirr],
                             {'00.cell.synapse': cellinfo(False), '01.cell.synapse': cellinfo(False, indx=5)},
                             extra=['--wait'])
            outp.expect('WARNING: Skipping --wait: the group has no active leader.')

            # a member which never responded can never satisfy the wait loop
            outp = await run([lead, mirr], {'00.cell.synapse': cellinfo(True)}, extra=['--wait'])
            outp.expect('WARNING: Skipping --wait: one or more group members did not respond.')

            # a leader which reported no nexus offset gives us nothing to wait on
            noindx = {'cell': {'active': True, 'version': '3.0.0', 'parent': None},
                      'synapse': {'version': '3.0.0'}}
            outp = await run([lead, mirr],
                             {'00.cell.synapse': noindx, '01.cell.synapse': cellinfo(False, indx=5)},
                             extra=['--wait'])
            outp.expect('WARNING: Skipping --wait: the leader did not report a nexus index.')
