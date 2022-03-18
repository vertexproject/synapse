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

        async with self.getRegrCore('2.47.0-autoadds-fix') as core:  # type: s_cortex.Cortex

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
                              '3a3f351ea0704fc310772096c0291405', '18520682d60c09857a12a262c4e2b1ec',
                              '9568f8706b4ce26652dd189b77892e1f', 'd427e8e7f2cd9b92123a80669216e763',
                              'f2edfe4a9da70308dcffd744a9a50bef'])
            msgs = await core.stormlist(q)
            self.stormIsInPrint(mesg, msgs)
            self.stormIsInPrint('fix (1, 0, 0)', msgs)
            self.stormIsInPrint('fix (2, 0, 0)', msgs)

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

    async def test_stormfix_cryptocoin(self):

        async with self.getRegrCore('2.68.0-cryptocoin-fix') as core:  # type: s_cortex.Cortex

            self.len(0, await core.nodes('crypto:currency:coin'))

            msgs = await core.stormlist('$r = $lib.cell.hotFixesCheck() $lib.print("r={r}", r=$r)')
            m = 'Would apply fix (2, 0, 0) for [Populate crypto:currency:coin nodes from existing addresses.]'
            self.stormIsInPrint(m, msgs)
            self.stormIsInPrint('r=True', msgs)

            q = '$lib.debug=$lib.true $r = $lib.cell.hotFixesApply() $lib.print("r={r}", r=$r)'

            msgs = await core.stormlist(q)
            self.stormIsInPrint('Applied hotfix (2, 0, 0)', msgs)

            self.len(2, await core.nodes('crypto:currency:coin'))

    async def test_stormfix_cpe2_2(self):

        async with self.getTestCore() as core:
            view0 = core.getView().iden
            view1 = await core.callStorm('return ( $lib.view.get().fork().iden )')
            view2 = await core.callStorm('return($lib.view.add(($lib.layer.add().iden,)).iden)')
            # Create it:sec:cpe nodes and strip off the :v2_2 property
            nodes = await core.nodes('[it:sec:cpe=cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:*] [-:v2_2]',
                                      opts={'view': view0})
            self.none(nodes[0].get('v2_2'))
            nodes = await core.nodes('[it:sec:cpe=cpe:2.3:a:vertex:testsss:*:*:*:*:*:*:*:*] [-:v2_2]',
                                     opts={'view': view1})
            self.none(nodes[0].get('v2_2'))
            nodes = await core.nodes('[it:sec:cpe=cpe:2.3:a:vertex:stuffff:*:*:*:*:*:*:*:*] [-:v2_2]',
                                     opts={'view': view2})
            self.none(nodes[0].get('v2_2'))

            self.len(0, await core.nodes('it:sec:cpe:v2_2', opts={'view': view0}))
            self.len(0, await core.nodes('it:sec:cpe:v2_2', opts={'view': view1}))
            self.len(0, await core.nodes('it:sec:cpe:v2_2', opts={'view': view2}))

            # Set the hotfix valu
            opts = {'vars': {'key': s_cell.runtime_fixes_key, 'valu': (2, 0, 0)}}
            await core.callStorm('$lib.globals.set($key, $valu)', opts)

            # Run all hotfixes.
            msgs = await core.stormlist('$lib.cell.hotFixesApply()')

            self.stormIsInPrint('Applying hotfix (3, 0, 0) for [Populate it:sec:cpe:v2_2', msgs)
            self.stormIsInPrint('Applied hotfix (3, 0, 0)', msgs)

            self.len(1, await core.nodes('it:sec:cpe:v2_2', opts={'view': view0}))
            self.len(2, await core.nodes('it:sec:cpe:v2_2', opts={'view': view1}))
            self.len(1, await core.nodes('it:sec:cpe:v2_2', opts={'view': view2}))
