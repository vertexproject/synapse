import pathlib

import synapse.lib.msgpack as s_msgpack
import synapse.lib.iq as s_iq

import synapse.tools.migrate_010 as s_migrate

class Migrate010Test(s_iq.SynTest):

    def get_formfile(self, formname, dirn, expected):
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
            contact_nodes = self.get_formfile('ps:contact', dirn, [{}])
            self.eq(len(contact_nodes), 1)
            node = contact_nodes[0]
            self.eq(type(node), tuple)
            self.eq(len(node[0]), 2)
            self.eq(node[0][0], 'ps:contact')
            self.eq(node[1]['props']['title'], 'ceo')
