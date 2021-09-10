import synapse.exc as s_exc

import synapse.lib.stormlib.cell as s_cell

import synapse.tests.utils as s_test

class StormCellTest(s_test.SynTest):

    async def test_stormlib_cell(self):

        async with self.getTestCore() as core:

            ret = await core.callStorm('return ( $lib.cell.getCellInfo() )')
            self.eq(ret, await core.getCellInfo())

            ret = await core.callStorm('return ( $lib.cell.getBackupInfo() )')
            self.eq(ret, await core.getBackupInfo())

            ret = await core.callStorm('return ( $lib.cell.getSystemInfo() )')
            tst = await core.getSystemInfo()
            self.eq(set(ret.keys()), set(tst.keys()))

            ret = await core.callStorm('return ( $lib.cell.getHealthCheck() )')
            self.eq(ret, await core.getHealthCheck())

            # New cores have stormvar set to the current max version fix
            vers = await core.callStorm('return ( $lib.globals.get($key) )',
                                        {'vars': {'key': s_cell.runtime_fixes_key}})
            self.nn(vers)
            self.eq(vers, s_cell.getMaxHotFixes())

            user = await core.addUser('bob')
            opts = {'user': user.get('iden')}

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getCellInfo() )', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getBackupInfo() )', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getSystemInfo() )', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getHealthCheck() )', opts=opts)

    async def test_stormfix_autoadds(self):

        async def get_regression_views(cortex):
            q = '''function get_view(name) {
                        for $view in $lib.view.list() {
                            $p = $view.pack()
                            if ($p.name = $name) {
                                return ( $view.iden )
                            }
                        }
                        $lib.exit('No view found for name={name}', name=$name)
                    }
                    $ret = $lib.dict()
                    $ret.baseview=$get_view(default)
                    $ret.fork1a=$get_view(base1a)
                    $ret.fork2a=$get_view(base2a)
                    $ret.fork1b=$get_view(base1b)
                    $ret.stackview=$get_view(stackview)
                    $ret.stackview1a=$get_view(stackview1a)
                    return ($ret)'''
            ret = await cortex.callStorm(q)
            return ret

        async with self.getRegrCore('2.47.0-autoadds-fix/') as core:  # type: s_cortex.Cortex

            user = await core.auth.addUser('user', passwd='user')

            self.len(6, core.views)
            for view in core.views:
                self.len(0, await core.nodes('inet:ipv4 -inet:ipv4=1.2.3.4 -inet:ipv4=1.2.3.5',
                                             opts={'view': view}))
                self.len(0, await core.nodes('inet:ipv6', opts={'view': view}))
                self.len(0, await core.nodes('inet:fqdn', opts={'view': view}))

            msgs = await core.stormlist('$r = $lib.cell.hotFixesCheck() $lib.print("r={r}", r=$r)')
            self.stormIsInPrint('Would apply fix (1, 0, 0) for [Create nodes for known missing autoadds.]', msgs)
            self.stormIsInPrint('r=True', msgs)

            q = '$lib.debug=$lib.true $r = $lib.cell.hotFixesApply() $lib.print("r={r}", r=$r)'
            mesg = '\n'.join(['The following Views will be fixed in order:', '68695c660aa6981192d70e954af0c8e3',
                              '18520682d60c09857a12a262c4e2b1ec', '9568f8706b4ce26652dd189b77892e1f',
                              'f2edfe4a9da70308dcffd744a9a50bef', '3a3f351ea0704fc310772096c0291405',
                              'd427e8e7f2cd9b92123a80669216e763'])
            msgs = await core.stormlist(q)
            self.stormIsInPrint(mesg, msgs)
            self.stormIsInPrint('r=(1, 0, 0)', msgs)

            msgs = await core.stormlist('$r = $lib.cell.hotFixesCheck() $lib.print("r={r}", r=$r)')
            self.stormIsInPrint('r=False', msgs)

            name2view = await get_regression_views(core)

            nodes = await core.nodes('inet:ipv4', opts={'view': name2view.get('baseview')})
            self.eq({n.ndef[1] for n in nodes},
                    {16777217, 16777220, 16842753, 16842756, 16908801, 16908802, 16909060, 1347440720, 1347440721})
            nodes = await core.nodes('inet:ipv6', opts={'view': name2view.get('fork1a')})
            self.eq({n.ndef[1] for n in nodes},
                    {'::ffff:1.1.0.1', '::ffff:1.1.0.4', '::ffff:1.2.2.2', '::ffff:1.2.3.4', '::ffff:80.80.80.81', })

            nodes = await core.nodes('inet:ipv6', opts={'view': name2view.get('fork1b')})
            self.eq({n.ndef[1] for n in nodes},
                    {'::ffff:1.1.0.1', '::ffff:1.1.0.4', '::ffff:1.2.2.2', '::ffff:3.0.9.1', '::ffff:80.80.80.81', })

            nodes = await core.nodes('inet:fqdn', opts={'view': name2view.get('fork2a')})
            self.eq({n.ndef[1] for n in nodes},
                    {'com', 'woot.com', 'stuff.com'})

            nodes = await core.nodes('inet:ipv4', opts={'view': name2view.get('stackview1a')})
            self.eq({n.ndef[1] for n in nodes},
                    {16777217, 16777220, 16842753, 16842756, 167837953, 167904004, 16908801, 16908802, 16909060,
                     1347440720, 1347440721, 3232235777, 3232236031})

            nodes = await core.nodes('inet:ipv6', opts={'view': name2view.get('stackview1a')})
            self.eq({n.ndef[1] for n in nodes},
                    {'::ffff:1.1.0.1', '::ffff:1.1.0.4', '::ffff:1.2.2.2', '::ffff:80.80.80.81', '::ffff:192.168.1.1',
                     '::ffff:192.168.1.255', })

            # Sad path
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return( $lib.cell.hotFixesApply() )', opts={'user': user.iden})

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.hotFixesCheck()) ', opts={'user': user.iden})
