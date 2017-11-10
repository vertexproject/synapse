from synapse.tests.common import *

class SynModelTest(SynTest):

    def test_model_syn_201709051630(self):

        data = {}
        with s_cortex.openstore('ram:///') as stor:

            # force model migration callbacks
            stor.setModlVers('syn', 0)

            tden = guid()
            fden = guid()
            pden = guid()
            mden = guid()

            tick = now()

            def addrows(mesg):
                rows = (
                    (tden, 'syn:type', 'hehe', tick),
                    (tden, 'syn:type:lulz', 'newp', tick),

                    (fden, 'syn:form', 'hehe', tick),
                    (fden, 'syn:form:lulz', 'newp', tick),

                    (pden, 'syn:prop', 'hehe', tick),
                    (pden, 'syn:prop:lulz', 'newp', tick),

                    (mden, '.:modl:vers:syn:core', 0, tick)
                )
                stor.addRows(rows)
                data['added'] = True

            stor.on('modl:vers:rev', addrows, name='syn', vers=201709051630)

            with s_cortex.fromstore(stor) as core:
                self.true(data.get('added'))
                self.eq(len(core.getRowsById(tden)), 0)
                self.eq(len(core.getRowsById(fden)), 0)
                self.eq(len(core.getRowsById(pden)), 0)
                self.eq(len(core.getRowsById(mden)), 0)

    def test_model_syn_201709191412(self):
        data = {}
        iden0 = guid()
        iden1 = guid()
        iden2 = guid()
        iden3 = guid()
        iden4 = guid()
        tick = now()
        rows = [(iden0, 'inet:ipv4:type', '??', tick),
                (iden0, 'inet:ipv4', 16909060, tick),
                (iden0, 'tufo:form', 'inet:ipv4', tick),
                (iden0, 'inet:ipv4:cc', '??', tick),
                (iden0, 'inet:ipv4:asn', -1, tick),
                (iden1, 'file:bytes', 'd41d8cd98f00b204e9800998ecf8427e', tick),
                (iden1, 'file:bytes:mime', '??', tick),
                (iden1, 'file:bytes:md5', 'd41d8cd98f00b204e9800998ecf8427e', tick),
                (iden1, 'tufo:form', 'file:bytes', tick),
                (iden2, 'file:txtref:xref:inet:ipv4', 16909060, tick),
                (iden2, 'tufo:form', 'file:txtref', tick),
                (iden2, 'file:txtref', 'd7b82a6328c2483bf583871031f573bf', tick),
                (iden2, 'file:txtref:file', 'd41d8cd98f00b204e9800998ecf8427e', tick),
                (iden2, 'file:txtref:xtype', 'inet:ipv4', tick),
                (iden3, 'file:imgof:xref:inet:fqdn', 'woot.com', tick),
                (iden3, 'tufo:form', 'file:imgof', tick),
                (iden3, 'file:imgof', 'ccea21ac0a1442aeffde9fd3893625ab', tick),
                (iden3, 'file:imgof:file', 'd41d8cd98f00b204e9800998ecf8427e', tick),
                (iden3, 'file:imgof:xtype', 'inet:fqdn', tick),
                (iden4, 'file:imgof:xref:inet:fqdn', 'vertex.link', tick),
                (iden4, 'tufo:form', 'file:imgof', tick),
                (iden4, 'file:imgof', 'ccea21ac0a1442aeffde9fd3893625ab', tick),
                (iden4, 'file:imgof:file', 'd41d8cd98f00b204e9800998ecf8427e', tick),
                ]

        with s_cortex.openstore('ram:///') as stor:
            # force model migration callbacks
            stor.setModlVers('syn', 0)

            def addrows(mesg):
                stor.addRows(rows)
                data['added'] = True

            stor.on('modl:vers:rev', addrows, name='syn', vers=201709191412)

            with s_cortex.fromstore(stor) as core:
                nodes = core.eval('file:txtref')
                self.eq(len(nodes), 1)
                node = nodes[0]
                self.eq(node[1].get('file:txtref:xref'), 'inet:ipv4=1.2.3.4')
                self.eq(node[1].get('file:txtref:xref:intval'), 0x01020304)
                self.eq(node[1].get('file:txtref:xref:prop'), 'inet:ipv4')
                self.notin('file:txtref:xref:xtype', node[1])
                self.notin('file:txtref:xref:inet:ipv4', node[1])
                self.notin('file:txtref:xref:strval', node[1])

                nodes = core.eval('file:imgof')
                self.eq(len(nodes), 2)

                node = core.eval('guid({})'.format(iden3))[0]
                self.eq(node[1].get('file:imgof:xref'), 'inet:fqdn=woot.com')
                self.eq(node[1].get('file:imgof:xref:strval'), 'woot.com')
                self.eq(node[1].get('file:imgof:xref:prop'), 'inet:fqdn')
                self.notin('file:imgof:xref:xtype', node[1])
                self.notin('file:imgof:xref:inet:fqdn', node[1])
                self.notin('file:imgof:xref:intval', node[1])

                node = core.eval('guid({})'.format(iden4))[0]
                self.eq(node[1].get('file:imgof:xref'), 'inet:fqdn=vertex.link')
                self.eq(node[1].get('file:imgof:xref:strval'), 'vertex.link')
                self.eq(node[1].get('file:imgof:xref:prop'), 'inet:fqdn')
                self.notin('file:imgof:xref:xtype', node[1])
                self.notin('file:imgof:xref:inet:fqdn', node[1])
                self.notin('file:imgof:xref:intval', node[1])

    def test_model_syn_201710191144(self):
        data = {}
        old_formed = 12345
        iden0, iden1 = guid(), guid()
        tick = now() - 10000  # putting tick in the past to show that preexisting node:created rows will have their stamps removed
        rows = [
            (iden0, 'inet:ipv4:type', '??', tick),
            (iden0, 'inet:ipv4', 16909060, tick),
            (iden0, 'tufo:form', 'inet:ipv4', tick),
            (iden0, 'inet:ipv4:cc', '??', tick),
            (iden0, 'inet:ipv4:asn', -1, tick),

            (iden1, 'file:bytes', 'd41d8cd98f00b204e9800998ecf8427e', tick),
            (iden1, 'file:bytes:mime', '??', tick),
            (iden1, 'file:bytes:md5', 'd41d8cd98f00b204e9800998ecf8427e', tick),
            (iden1, 'tufo:form', 'file:bytes', tick),
            (iden1, 'node:created', tick, tick),  # NOTE: this row should not exist pre-migration
        ]

        with s_cortex.openstore('ram:///') as stor:
            # force model migration callbacks
            stor.setModlVers('syn', 0)

            def addrows(mesg):
                stor.addRows(rows)
                data['added'] = True

            stor.on('modl:vers:rev', addrows, name='syn', vers=201710191144)

            with s_cortex.fromstore(stor) as core:

                # 1 file:bytes, 1 inet:ipv4
                self.ge(len(core.eval('node:created')), 3)

                tufos = core.eval('node:created +tufo:form=inet:ipv4')
                self.len(1, tufos)
                iden, props = tufos[0]
                self.eq(props['tufo:form'], 'inet:ipv4')
                self.eq(props['node:created'], tick)
                self.eq(props['inet:ipv4'], 16909060)
                self.eq(props['inet:ipv4:asn'], -1)
                self.eq(props['inet:ipv4:cc'], '??')
                rows = core.getRowsByIdProp(iden, 'node:created')
                _, _, valu, stamp = rows[0]
                self.gt(stamp, valu)  # node:created row's stamp will be higher than its valu

                tufos = core.eval('node:created +tufo:form=file:bytes')
                self.len(1, tufos)
                props = tufos[0][1]
                self.eq(props['tufo:form'], 'file:bytes')
                self.eq(props['node:created'], tick)
                self.eq(props['file:bytes'], 'd41d8cd98f00b204e9800998ecf8427e')
                self.eq(props['file:bytes:mime'], '??')
                self.eq(props['file:bytes:md5'], 'd41d8cd98f00b204e9800998ecf8427e')
                rows = core.getRowsByIdProp(iden, 'node:created')
                _, _, valu, stamp = rows[0]
                self.gt(stamp, valu)  # node:created row's stamp will be higher than its valu

    def test_model_syn_201711012123(self):
        data = {}
        iden0, iden1 = guid(), guid()
        tick = now()
        rows = [
            (iden0, 'inet:ipv4:type', '??', tick),
            (iden0, 'inet:ipv4', 16909060, tick),
            (iden0, 'tufo:form', 'inet:ipv4', tick),
            (iden0, 'node:created', tick, tick),
            (iden0, 'inet:ipv4:cc', '??', tick),
            (iden0, 'inet:ipv4:asn', -1, tick),

            (iden1, 'file:bytes', 'd41d8cd98f00b204e9800998ecf8427e', tick),
            (iden1, 'file:bytes:mime', '??', tick),
            (iden1, 'file:bytes:md5', 'd41d8cd98f00b204e9800998ecf8427e', tick),
            (iden1, 'tufo:form', 'file:bytes', tick),
            (iden1, 'node:created', tick, tick),
        ]

        with s_cortex.openstore('ram:///') as stor:
            # force model migration callbacks
            stor.setModlVers('syn', 0)

            def addrows(mesg):
                stor.addRows(rows)
                data['added'] = True

            stor.on('modl:vers:rev', addrows, name='syn', vers=201711012123)

            with s_cortex.fromstore(stor) as core:
                self.true(data.get('added'))

                # 1 file:bytes, 1 inet:ipv4, 1 syn:core
                self.ge(len(core.eval('node:ndef')), 3)

                tufos = core.eval('node:ndef +tufo:form=inet:ipv4')
                self.eq(len(tufos), 1)
                node = tufos[0]
                self.eq(node[1].get('node:ndef'), 'cbc65d5e373205b31b9be06155c186db')

                tufos = core.eval('node:ndef +tufo:form=file:bytes')
                self.eq(len(tufos), 1)
                node = tufos[0]
                self.eq(node[1].get('node:ndef'), 'ab91b96076bd6f2b1acd5b19f0e06d05')
