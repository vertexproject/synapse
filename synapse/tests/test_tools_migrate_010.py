import pathlib
import tempfile

import synapse.cortex as s_cortex
import synapse.common as s_common

import synapse.lib.iq as s_iq
import synapse.lib.tufo as s_tufo
import synapse.lib.hashset as s_hashset
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

            file_guid = s_common.guid()
            file_tufo = core.formTufoByProp('file:bytes', file_guid)
            core.formTufoByProp('inet:web:acct', 'twitter.com/ironman', avatar=file_guid,
                                **{'seen:min': 1000, 'seen:max': 2000, 'signup:ipv4': '1.2.3.4'})
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

            contact_tufo = core.formTufoByProp('ps:contact', info)

            fh = tempfile.TemporaryFile(dir=str(dirn))
            m = s_migrate.Migrator(core, fh, tmpdir=str(dirn))
            m.migrate()
            now = s_common.now()

            nodes = self.get_formfile('ps:contact', fh)
            self.eq(len(nodes), 1)
            node = nodes[0]
            self.eq(type(node), tuple)
            self.eq(len(node[0]), 2)
            self.eq(node[0][0], 'ps:contact')
            self.eq(node[1]['props']['title'], 'ceo')
            self.eq(node[1]['props']['name'], 'stark,tony')

            acct_nodes = self.get_formfile('inet:web:acct', fh)
            self.eq(len(acct_nodes), 1)
            node = acct_nodes[0]
            self.eq(type(node), tuple)
            self.eq(len(node[0]), 2)
            self.eq(node[0], ('inet:web:acct', ('twitter.com', 'ironman')))
            # Verify that redundant secondary props of seprs aren't included
            self.notin('site', node[1]['props'])
            self.eq(node[1]['props']['.seen'], (1000, 2000))

            self.eq(node[1]['props']['avatar'], 'guid:' + file_guid)

            # test that secondary props make it in
            nodes = self.get_formfile('ps:name', fh)
            self.eq(len(nodes), 1)
            self.eq(nodes[0][1]['props'].get('given'), 'tony')

            fh.close()

            props = {
                'rcode': 99,
                'time': now,
                'ipv4': '5.5.5.5',
                'udp4': '8.8.8.8:80',
                'ns': 'foo.org/blah.info',
                'ns:ns': 'blah.info',
                'ns:zone': 'foo.org'
            }
            tufo = core.formTufoByProp('inet:dns:look', '*', **props)
            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            look_nodes = self.get_formfile('inet:dns:request', fh)
            self.eq(len(look_nodes), 1)
            self.eq(look_nodes[0][1]['props']['server'], 'udp://8.8.8.8:80')
            self.eq(look_nodes[0][1]['props']['query'], ('tcp://5.5.5.5', 'foo.org', 99))

            answer_nodes = self.get_formfile('inet:dns:answer', fh)
            self.eq(len(answer_nodes), 1)
            self.eq(answer_nodes[0][1]['props']['ns'], ('foo.org', 'blah.info'))

            nodes = self.get_formfile('inet:server', fh)
            self.eq(len(nodes), 1)
            self.eq(nodes[0][0], ('inet:server', 'udp://8.8.8.8:80'))
            fh.close()

            tufo = core.formTufoByProp('inet:web:logon', '*', acct='vertex.link/pennywise', time=now,
                                       ipv4=0x01020304)
            core.addTufoTag(tufo, 'test')
            core.addTufoTag(tufo, 'hehe.haha@2016-2017')
            core.formTufoByProp('inet:web:logon', '*', acct='vertex.link/pennywise2', time=now,
                                ipv6='::ffff:1.2.3.4')
            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:web:logon', fh)
            self.eq(len(nodes), 2)
            node1, node2 = nodes
            if node1[1]['props']['acct'][1][-1] == '2':
                node1, node2 = node2, node1
            tags = node1[1]['tags']
            self.eq(tags['test'], (None, None))
            self.eq(tags['hehe.haha'], (1451606400000, 1483228800000))
            nodes = self.get_formfile('syn:tagform', fh)
            self.eq(nodes, [])
            fh.close()

            wp_tufo = core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            core.formTufoByProp('inet:web:postref',
                                (wp_tufo[1]['inet:web:post'], ('file:bytes', file_tufo[1]['file:bytes'])))
            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:web:post', fh)
            self.eq(len(nodes), 1)
            # Make sure the primary val is a guid
            self.eq(len(nodes[0][0][1]), 32)
            fh.close()

            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:web:postref', fh)
            self.eq(len(nodes), 1)
            self.eq(nodes[0][0], ('inet:web:postref',
                                  (wp_tufo[1]['inet:web:post'], ('file:bytes', 'guid:' + file_guid))))
            fh.close()

            node = core.formTufoByProp('it:exec:reg:get', '*', host=s_common.guid(), reg=['foo/bar', ('int', 20)],
                                       exe=s_common.guid(), proc=s_common.guid(), time=now)
            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('it:exec:reg:get', fh)
            self.eq(len(nodes), 1)
            fh.close()

            # file:imgof
            person_guid = contact_tufo[1]['ps:contact:person']
            core.formTufoByProp('file:imgof', (file_guid, ('ps:person', person_guid)))
            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('file:ref', fh)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node[1]['props']['type'], 'image')
            ndef = node[0]
            self.eq(ndef, ('file:ref', ('guid:' + file_guid, ('ps:person', person_guid))))
            fh.close()

            # ps:person:has
            core.formTufoByProp('ps:person:has', (person_guid, ('file:bytes', file_guid)),
                                **{'seen:min': 1000, 'seen:max': 1000})
            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('has', fh)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('has', (('ps:person', person_guid), ('file:bytes', 'guid:' + file_guid))))
            self.eq(nodes[0][1]['props']['.seen'], (1000, 1001))
            fh.close()

            # ps:image
            core.formTufoByProp('ps:image', person_guid + '/' + file_guid)
            fh = tempfile.TemporaryFile(dir=str(dirn))
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('file:ref', fh)
            self.len(2, nodes)
            # Just verify that the ps:image conversion looks like the file:imgof conversion above
            self.eq(nodes[0][0], nodes[1][0])
            fh.close()

    def test_filebytes(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:

            hset = s_hashset.HashSet()
            hset.update(b'visi')
            valu, props = hset.guid()
            core.formTufoByProp('file:bytes', valu, **props)
            core.formTufoByProp('file:bytes', s_common.guid(), size=42)

            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            node1, node2 = self.get_formfile('file:bytes', fh)
            if node1[1]['props']['size'] == 42:
                node1, node2 = node2, node1

            self.isin('sha256', node1[1]['props'])
            self.notin('sha256', node2[1]['props'])
            self.true(node1[0][1].startswith('sha256:'))
            self.true(node2[0][1].startswith('guid:'))
            fh.close()

            # inet:ssl:tcp4cert
            core.formTufoByProp('inet:ssl:tcp4cert', '5.5.5.5:80/' + valu)
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:ssl:cert', fh)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('inet:ssl:cert', ('tcp://5.5.5.5:80', node1[0][1])))
            fh.close()

    def test_bigval(self):
        with self.getTestDir() as dirn, self.getRamCore() as core:

            for i in range(1000):
                core.formTufoByProp('ps:contact', s_common.guid(), title=str(i), address='x' * (512 + i))

            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('ps:contact', fh)
            self.len(1000, nodes)
            for n in nodes:
                self.len(512 + int(n[1]['props']['title']), n[1]['props']['address'])
            fh.close()

    def test_flow(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:
            props = {
                'dst:tcp4': '1.2.3.4:80',
                'dst:udp4': '2.3.4.5:80',
                'src:tcp6': '[0:0:0:0:0:3:2:1]:443',
                'src:udp6': '[1:0:0:0:0:3:3:3]:80'
            }
            core.formTufoByProp('inet:flow', s_common.guid(), **props)

            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:flow', fh)
            self.len(1, nodes)
            self.eq(nodes[0][1]['props']['dst'], 'tcp://1.2.3.4:80')
            self.eq(nodes[0][1]['props']['src'], 'tcp://[::3:2:1]:443')
            fh.close()

    def test_it_exec_bind(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:
            host1 = s_common.guid()
            host2 = s_common.guid()

            core.formTufoByProp('it:exec:bind:tcp', '*', host=host1, port=80, ipv4='1.2.3.4')
            core.formTufoByProp('it:exec:bind:udp', '*', host=host2, port=81, ipv6='::1')
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('it:exec:bind', fh)
            self.len(2, nodes)
            node1, node2 = nodes
            if node2[1]['props']['host'] == host1:
                node2, node1 = node1, node2
            self.eq(node1[1]['props']['server'], 'tcp://1.2.3.4:80')
            self.eq(node2[1]['props']['server'], 'udp://[::1]:81')
            fh.close()

    def test_file_base(self):
        '''
        A file:base with a backslash shall be corrected and a new file:path node shall be added
        with the same tags.
        '''
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:
            tufo = core.formTufoByProp('file:base', '%temp%\\bar.exe')
            core.addTufoTag(tufo, 'test')
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('file:base', fh)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('file:base', 'bar.exe'))
            self.eq(nodes[0][1]['tags'], {'test': (None, None)})
            nodes = self.get_formfile('file:path', fh)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('file:path', '%temp%/bar.exe'))
            self.eq(nodes[0][1]['tags'], {'test': (None, None)})
            fh.close()

    def test_ipv4(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:
            tufo = core.formTufoByProp('inet:ipv4', '5.5.5.5')
            core.addTufoTag(tufo, 'test')
            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:ipv4', fh)
            self.len(1, nodes)
            self.eq(nodes[0][1]['tags'], {'test': (None, None)})
            fh.close()

    def test_inet_dns_soa(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:
            # This is kind of worst case - where someone made a inet:dns:soa
            # node as a comp with optional field and set a third property
            # after the fact.
            node = core.formTufoByProp('inet:dns:soa',
                                       {'fqdn': 'vertex.link', 'ns': 'foo.bar.com'},
                                       email='bob@foo.bar.com')
            _, pprop = s_tufo.ndef(node)
            self.true(s_common.isguid(pprop))

            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('inet:dns:soa', fh)
            self.eq(len(nodes), 1)
            self.eq(nodes[0][0], ('inet:dns:soa', pprop))
            self.eq(nodes[0][1].get('props').get('fqdn'), 'vertex.link')
            self.eq(nodes[0][1].get('props').get('email'), 'bob@foo.bar.com')
            self.eq(nodes[0][1].get('props').get('ns'), 'foo.bar.com')
            fh.close()

    def test_it_dev_regval(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:
            # This is kind of worst case - where someone made a it:dev:regval
            # node as a comp with optional field and set a property
            # after the fact.
            node = core.formTufoByProp('it:dev:regval',
                                       {'key': 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\\Run'},
                                       str='c:\\temp\\good.exe')
            _, pprop = s_tufo.ndef(node)
            self.true(s_common.isguid(pprop))

            fh = tempfile.TemporaryFile(dir=dirn)
            s_migrate.Migrator(core, fh, tmpdir=dirn).migrate()
            nodes = self.get_formfile('it:dev:regval', fh)
            self.eq(len(nodes), 1)
            self.eq(nodes[0][0], ('it:dev:regval', pprop))
            self.eq(nodes[0][1].get('props').get('key'),
                    'hkey_local_machine\\software\\microsoft\\windows\\currentversion\\run')
            self.eq(nodes[0][1].get('props').get('str'), 'c:\\temp\\good.exe')
            fh.close()

    def test_ps_personx(self):
        ''' Test both ps:person and ps:persona '''
        self.maxDiff = None
        for personx in ('person', 'persona'):
            with self.getTestDir() as dirn, self.getRamCore() as core:
                props = {
                    'name': 'Gnaeus Pompeius Magnus',
                    'guidname': 'guidname',
                    'name:given': 'Gnaeus',
                    'name:en': 'Pompey the Great',
                    'name:en:sur': 'Pompey'
                }
                guid = s_common.guid()
                core.formTufoByProp('ps:%s' % personx, guid, **props)
                fh = tempfile.TemporaryFile(dir=dirn)
                m = s_migrate.Migrator(core, fh, tmpdir=dirn)
                m.migrate()
                nodes = self.get_formfile('ps:%s' % personx, fh)
                self.len(1, nodes)

                self.isin('name:given', nodes[0][1]['props'])
                self.notin('name:en', nodes[0][1]['props'])
                self.notin('name:en:sur', nodes[0][1]['props'])

                # test that secondary prop drop works
                self.notin('guidname', nodes[0][1]['props'])

                nodes = self.get_formfile('has', fh)
                self.len(1, nodes)
                first_node = nodes[0]
                self.eq(first_node[0][1], (('ps:%s' % personx, guid), ('ps:name', 'pompey the great')))

                nodes = self.get_formfile('ps:name', fh)
                self.len(3, nodes)
                en_node = [n for n in nodes if n[0][1] == 'pompey the great'][0]
                latin_node = [n for n in nodes if n[0][1] == 'gnaeus pompeius magnus'][0]
                self.eq('pompey', en_node[1]['props'].get('sur'))
                self.eq('gnaeus', latin_node[1]['props'].get('given'))
                fh.close()

                core.formTufoByProp('ps:%s:has' % personx, (guid, ('inet:fqdn', 'pompeius.respublica.rm')))
                fh = tempfile.TemporaryFile(dir=dirn)
                m = s_migrate.Migrator(core, fh, tmpdir=dirn)
                m.migrate()
                nodes = self.get_formfile('has', fh)
                self.len(2, nodes)
                other_node = nodes[0] if first_node == nodes[1] else nodes[1]
                self.eq(other_node[0], ('has', (('ps:%s' % personx, guid), ('inet:fqdn', 'pompeius.respublica.rm'))))
                self.len(0, self.get_formfile('ps:%s:has' % personx, fh))
                fh.close()

    def test_ou_org(self):
        self.maxDiff = None
        with self.getTestDir() as dirn, self.getRamCore() as core:
            props = {
                'name': 'Senatus Romanum',
                'name:en': 'The Roman Senate',
            }
            guid = s_common.guid()
            core.formTufoByProp('ou:org', guid, **props)
            fh = tempfile.TemporaryFile(dir=dirn)
            m = s_migrate.Migrator(core, fh, tmpdir=dirn)
            m.migrate()
            nodes = self.get_formfile('ou:org', fh)
            self.len(1, nodes)
            self.notin('name:en', nodes[0][1]['props'])
            nodes = self.get_formfile('has', fh)
            self.len(1, nodes)
            first_node = nodes[0]
            self.eq(first_node[0][1][1], ('ou:name', 'the roman senate'))
            fh.close()

            core.formTufoByProp('ou:org:has', (guid, ('inet:fqdn', 'respublica.rm')))
            fh = tempfile.TemporaryFile(dir=dirn)
            m = s_migrate.Migrator(core, fh, tmpdir=dirn)
            m.migrate()
            nodes = self.get_formfile('has', fh)
            self.len(2, nodes)
            other_node = nodes[0] if first_node == nodes[1] else nodes[1]
            self.eq(other_node[0], ('has', (('ou:org', guid), ('inet:fqdn', 'respublica.rm'))))
            self.len(0, self.get_formfile('ou:org:has', fh))
            fh.close()

    def test_dns_query(self):
        with self.getTestDir() as dirn, self.getRamCore() as core:
            core.formTufoByProp('inet:dns:req', ('1.2.3.4', 'VERTEX.link', 'AAAA'))
            fh = tempfile.TemporaryFile(dir=dirn)
            m = s_migrate.Migrator(core, fh, tmpdir=dirn)
            m.migrate()
            nodes = self.get_formfile('inet:dns:query', fh)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('inet:dns:query', ('tcp://1.2.3.4', 'vertex.link', 28)))
            fh.close()

    def test_subfile(self):
        g1 = s_common.guid()
        g2 = s_common.guid()
        with self.getTestDir() as dirn, self.getRamCore() as core:
            core.formTufoByProp('file:subfile', (g1, g2), name='hehe.txt')
            fh = tempfile.TemporaryFile(dir=dirn)
            m = s_migrate.Migrator(core, fh, tmpdir=dirn)
            m.migrate()
            nodes = self.get_formfile('file:subfile', fh)
            self.len(1, nodes)
            self.eq(nodes[0][0][1], ('guid:' + g1, 'guid:' + g2))
            fh.close()

    def test_txtref_tcp4(self):
        with self.getTestDir() as dirn, s_cortex.openurl('sqlite:///:memory:') as core:

            dirn = pathlib.Path(dirn)

            iden = s_common.guid()
            core.formTufoByProp('file:txtref', (iden, ('inet:tcp4', '1.2.3.4:4567')))
            fh = tempfile.TemporaryFile(dir=str(dirn))
            m = s_migrate.Migrator(core, fh, tmpdir=str(dirn))
            m.migrate()

            nodes = self.get_formfile('file:ref', fh)
            self.eq(len(nodes), 1)
            node = nodes[0]
            self.eq(node[0][1][1][0], 'inet:server')
            fh.close()

    def test_inet_web_chprofile(self):
        ''' Just make sure we drop all the 'seen:max ' instances of chprofile, and keep the rest as is '''
        with self.getTestDir() as dirn, s_cortex.openurl('sqlite:///:memory:') as core:

            dirn = pathlib.Path(dirn)

            props = {
                'acct': 'twitter.com/foobar',
                'acct:site': 'twitter.com',
                'acct:user': 'foobar',
                'pv': 'inet:web:acct:seen:max=2018/02/02 22:43:22.000',
                'pv:prop': 'inet:web:acct:seen:max',
            }
            core.formTufoByProp('inet:web:chprofile', s_common.guid(), **props)
            fh = tempfile.TemporaryFile(dir=str(dirn))
            m = s_migrate.Migrator(core, fh, tmpdir=str(dirn))
            m.migrate()

            nodes = self.get_formfile('inet:web:chprofile', fh)
            self.eq(len(nodes), 0)
            fh.close()

            props = {
                'acct': 'twitter.com/foobar2',
                'acct:site': 'twitter.com',
                'acct:user': 'foobar2',
                'pv': 'inet:web:acct:occupation=digital janitor',
                'pv:prop': 'inet:web:acct:occupation',
            }
            core.formTufoByProp('inet:web:chprofile', s_common.guid(), **props)
            fh = tempfile.TemporaryFile(dir=str(dirn))
            m = s_migrate.Migrator(core, fh, tmpdir=str(dirn))
            m.migrate()

            nodes = self.get_formfile('inet:web:chprofile', fh)
            self.eq(len(nodes), 1)
            fh.close()
