import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.cell as s_cell

import synapse.tests.utils as s_test

class AhaLibTest(s_test.SynTest):

    async def test_stormlib_aha_basics(self):

        async with self.getTestAhaProv() as aha:

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
                self.eq('core.loop.vertex.link', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(core.loop.vertex.link))')
                self.eq('core.loop.vertex.link', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(00.cell...))')
                self.eq('00.cell.loop.vertex.link', svc.get('name'))
                svc = await core00.callStorm('return( $lib.aha.get(cell...))')
                self.eq('cell.loop.vertex.link', svc.get('name'))
                svc = await core00.callStorm('$f=({"mirror": (true)}) return( $lib.aha.get(cell..., filters=$f))')
                self.eq('01.cell.loop.vertex.link', svc.get('name'))

                # List the aha services available
                msgs = await core00.stormlist('aha.svc.list --nexus')
                self.stormIsInPrint('Nexus', msgs)
                self.stormIsInPrint('00.cell.loop.vertex.link                      true   true   true', msgs)
                self.stormIsInPrint('01.cell.loop.vertex.link                      false  true   true', msgs)
                self.stormIsInPrint('cell.loop.vertex.link                         true   true   true', msgs)
                self.stormIsInPrint('core.loop.vertex.link                         null   true   true', msgs)
                self.stormIsInPrint('mysvc.loop.vertex.link                        null   true   true', msgs)

                msgs = await core00.stormlist('aha.svc.list')
                self.stormNotInPrint('Nexus', msgs)
                msgs = await core00.stormlist('aha.svc.stat cell...')

                # The connections information includes runtime information such as port/host info.
                # Omit checking part of that.
                emsg = '''Resolved cell... to an AHA Service.

Name:       cell.loop.vertex.link
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     cell
Connection information:
    ca:         loop.vertex.link
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)
                self.stormIsInPrint('    hostname:   00.cell.loop.vertex.link', msgs)
                self.stormIsInPrint('    scheme:     ssl', msgs)
                self.stormIsInPrint('    user:       root', msgs)

                msgs = await core00.stormlist('aha.svc.stat --nexus cell...')
                emsg = '''Resolved cell... to an AHA Service.

Name:       cell.loop.vertex.link
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     cell
Nexus:      1
Connection information:
    ca:         loop.vertex.link
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)

                msgs = await core00.stormlist('aha.svc.stat --nexus 01.cell...')
                emsg = '''Resolved 01.cell... to an AHA Service.

Name:       01.cell.loop.vertex.link
Online:     true
Ready:      true
Run iden:   ********************************
Cell iden:  ********************************
Leader:     cell
Nexus:      1
Connection information:
    ca:         loop.vertex.link
'''
                self.stormIsInPrint(emsg, msgs, deguid=True)

                # Full name works
                msgs = await core00.stormlist('aha.svc.stat 01.cell.loop.vertex.link')
                emsg = '''Resolved 01.cell.loop.vertex.link to an AHA Service.

Name:       01.cell.loop.vertex.link
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
AHA Pool:   pool00.loop.vertex.link
Member:     00.cell.loop.vertex.link'''
                self.stormIsInPrint(emsg, msgs)

                # Shut down a service
                nevents = 2 if replay else 1
                waiter = aha.waiter(nevents, 'aha:svcdown')
                await cell01.fini()
                self.len(nevents, await waiter.wait(timeout=12))

                msgs = await core00.stormlist('aha.svc.list')
                self.stormIsInPrint('01.cell.loop.vertex.link                      false  false  false', msgs)

                # Fake a record
                await aha.addAhaSvc('00.newp', info={'urlinfo': {'scheme': 'tcp', 'host': '0.0.0.0', 'port': '3030'}},
                                    network='loop.vertex.link')

                msgs = await core00.stormlist('aha.svc.list --nexus')
                emsg = '00.newp.loop.vertex.link                      null   false  null  0.0.0.0         3030  ' \
                       'Service is not online. Will not attempt to retrieve its nexus offset.'
                self.stormIsInPrint(emsg, msgs)

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
                                    network='loop.vertex.link')
                msgs = await core00.stormlist('aha.svc.list --nexus')
                emsg = '00.newp.loop.vertex.link                      null   true   null  0.0.0.0         3030  ' \
                       'Failed to connect to Telepath service: "aha://00.newp.loop.vertex.link/" error:'
                self.stormIsInPrint(emsg, msgs)

                msgs = await core00.stormlist('aha.svc.stat --nexus 00.newp...')
                emsg = '''Resolved 00.newp... to an AHA Service.

Name:       00.newp.loop.vertex.link
Online:     true
Ready:      null
Run iden:   $lib.null
Cell iden:  $lib.null
Leader:     Service did not register itself with a leader name.
Nexus:      Failed to connect to Telepath service: "aha://00.newp.loop.vertex.link/" error: [Errno 111] Connect call failed ('0.0.0.0', 3030)
Connection information:
    host:       0.0.0.0
    port:       3030
    scheme:     tcp
    user:       root'''
                self.stormIsInPrint(emsg, msgs)

                # Delete the fake service with its full service name
                self.none(await core00.callStorm('return($lib.aha.del(00.newp.loop.vertex.link))'))
                self.none(await core00.callStorm('return($lib.aha.get(00.newp...))'))

                # Coverage for sad paths
                with self.raises(s_exc.BadArg):
                    await core00.callStorm('$lib.aha.del(pool00...)')

                with self.raises(s_exc.NoSuchName):
                    await core00.callStorm('$lib.aha.del(axon...)')
