import pathlib
import tempfile

import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.lib.iq as s_iq
import synapse.lib.msgpack as s_msgpack

import synapse.tools.migrate_010 as s_migrate

class Migrate010Test(s_iq.SynTest):

    def get_formfile(self, formname, fh):
        fh.seek(0)
        nodes = list(node for node in s_msgpack.iterfd(fh) if node[0][0] == formname)
        return nodes

    def test_basic(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, s_cortex.openurl('sqlite:///:memory:') as core:
            # with self.getTestDir() as dirn, self.getRamCore() as core:

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

            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            now = s_common.now()

            nodes = self.get_formfile('ps:contact', fh)
            self.eq(len(nodes), 1)
            node = nodes[0]
            self.eq(type(node), tuple)
            self.eq(len(node[0]), 2)
            self.eq(node[0][0], 'ps:contact')
            self.eq(node[1]['props']['title'], 'ceo')

            acct_nodes = self.get_formfile('inet:web:acct', fh)
            self.eq(len(acct_nodes), 1)
            node = acct_nodes[0]
            self.eq(type(node), tuple)
            self.eq(len(node[0]), 2)
            self.eq(node[0], ('inet:web:acct', ('twitter.com', 'ironman')))

            props = {'a': 'WOOT.com/1.002.3.4', 'rcode': 0, 'time': now, 'ipv4': '5.5.5.5',
                     'udp4': '8.8.8.8:80'}
            core.formTufoByProp('inet:dns:look', '*', **props)
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            look_nodes = self.get_formfile('inet:dns:look', fh)
            self.eq(len(look_nodes), 1)
            self.eq(look_nodes[0][1]['props']['inet:dns:look:udp4'], 'udp://134744072:80/')

            tufo = core.formTufoByProp('inet:web:logon', '*', acct='vertex.link/pennywise', time=now,
                                       ipv4=0x01020304)
            core.addTufoTag(tufo, 'test')
            core.addTufoTag(tufo, 'hehe.haha@2016-2017')
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:web:logon', fh)
            self.eq(len(nodes), 1)
            self.eq(nodes[0][1]['props']['client'], 'tcp://16909060/')
            tags = nodes[0][1]['tags']
            self.eq(tags['test'], None)
            self.eq(tags['hehe.haha'], (1451606400000, 1483228800000))

            core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:web:post', fh)
            self.eq(len(nodes), 1)
            # Make sure the primary val is a guid
            self.eq(len(nodes[0][0][1]), 32)

            node = core.formTufoByProp('it:exec:reg:get', '*', host=s_common.guid(), reg=['foo/bar', ('int', 20)],
                                       exe=s_common.guid(), proc=s_common.guid(), time=now)
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('it:exec:reg:get', fh)
            self.eq(len(nodes), 1)
            reg = nodes[0][1]['props']['reg']
            self.eq(type(reg), tuple)
            self.eq(len(reg), 2)
            self.eq(reg[0], 'it:dev:regval')
