import pathlib

import synapse.common as s_common
import synapse.lib.iq as s_iq
import synapse.lib.msgpack as s_msgpack

import synapse.tools.migrate_010 as s_migrate

class Migrate010Test(s_iq.SynTest):

    def get_formfile(self, formname, dirn):
        fnam = (dirn / formname.replace(':', '_')).with_suffix('.dump')
        nodes = list(s_msgpack.iterfile(fnam))
        return nodes

    def test_basic(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:

            dirn = pathlib.Path(dirn)

            info = {
                'org': '*',
                'person': '*',

                'name': 'Stark,Tony',

                'title': 'CEO',
                'orgname': 'Stark Industries, INC',

                'user': 'ironman',
                'web:acct': 'twitter.com/ironman',

                'dob': '1976-12-17',
                'url': 'https://starkindustries.com/',

                'email': 'tony.stark@gmail.com',
                'email:work': 'tstark@starkindustries.com',

                'phone': '12345678910',
                'phone:fax': '12345678910',
                'phone:work': '12345678910',

                'address': '1 Iron Suit Drive, San Francisco, CA, 22222, USA',
            }

            core.formTufoByProp('ps:contact', info)

            s_migrate.migrateInto010(core, dirn)
            nodes = self.get_formfile('ps:contact', dirn)
            self.eq(len(nodes), 1)
            node = nodes[0]
            self.eq(type(node), tuple)
            self.eq(len(node[0]), 2)
            self.eq(node[0][0], 'ps:contact')
            self.eq(node[1]['props']['title'], 'ceo')

            acct_nodes = self.get_formfile('inet:web:acct', dirn)
            self.eq(len(acct_nodes), 1)
            node = acct_nodes[0]
            self.eq(type(node), tuple)
            self.eq(len(node[0]), 2)
            self.eq(node[0], ('inet:web:acct', ('twitter.com', 'ironman')))

            props = {'a': 'WOOT.com/1.002.3.4', 'rcode': 0, 'time': s_common.now(), 'ipv4': '5.5.5.5',
                     'udp4': '8.8.8.8:80'}
            core.formTufoByProp('inet:dns:look', '*', **props)
            s_migrate.migrateInto010(core, dirn)
            look_nodes = self.get_formfile('inet:dns:look', dirn)
            self.eq(len(look_nodes), 1)
            self.eq(look_nodes[0][1]['props']['inet:dns:look:udp4'], 'udp://134744072:80/')

            tufo = core.formTufoByProp('inet:web:logon', '*', acct='vertex.link/pennywise', time=s_common.now(),
                                       ipv4=0x01020304)
            core.addTufoTag(tufo, 'test')
            s_migrate.migrateInto010(core, dirn, tag='test')
            nodes = self.get_formfile('inet:web:logon', dirn)
            self.eq(len(nodes), 1)
            self.eq(nodes[0][1]['props']['client'], 'tcp://16909060/')

            core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            s_migrate.migrateInto010(core, dirn)
            nodes = self.get_formfile('inet:web:post', dirn)
            self.eq(len(nodes), 1)
            # Make sure the primary val is a guid
            self.eq(len(nodes[0][0][1]), 32)
