import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils

import synapse.tools.fixes.autoadds as s_f_autoadds

class FixAutoadds(s_t_utils.SynTest):

    async def get_views(self, core):
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
        ret = await core.callStorm(q)
        return ret

    async def test_autoadds_fix(self):
        ephemeral_address = 'tcp://0.0.0.0:0/'
        async with self.getRegrCore('2.47.0-autoadds-fix/') as core:  # type: s_cortex.Cortex

            outp = self.getTestOutp()
            views = await core.callStorm(s_f_autoadds.view_query)
            orderd_views = s_f_autoadds.getOrderedViews(views, outp, debug=True)

            self.eq(orderd_views, ['68695c660aa6981192d70e954af0c8e3', '18520682d60c09857a12a262c4e2b1ec',
                                   '9568f8706b4ce26652dd189b77892e1f', 'f2edfe4a9da70308dcffd744a9a50bef',
                                   '3a3f351ea0704fc310772096c0291405', 'd427e8e7f2cd9b92123a80669216e763'])

            for view in orderd_views:
                self.len(0, await core.nodes('inet:ipv4 -inet:ipv4=1.2.3.4 -inet:ipv4=1.2.3.5',
                                             opts={'view': view}))
                self.len(0, await core.nodes('inet:ipv6', opts={'view': view}))
                self.len(0, await core.nodes('inet:fqdn', opts={'view': view}))

            outp.clear()
            url = core.getLocalUrl()
            argv = [url, ]
            ret = await s_f_autoadds._main(argv, outp=outp)
            self.eq(0, ret)

            name2view = await self.get_views(core)

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
