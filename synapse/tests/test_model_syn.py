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
                self.notin('file:txtref:xref:inet:ipv4', node[1])
                self.notin('file:txtref:xref:strval', node[1])
                nodes = core.eval('file:imgof')
                self.eq(len(nodes), 1)
                node = nodes[0]
                self.eq(node[1].get('file:imgof:xref'), 'inet:fqdn=woot.com')
                self.eq(node[1].get('file:imgof:xref:strval'), 'woot.com')
                self.notin('file:imgof:xref:inet:fqdn', node[1])
                self.notin('file:imgof:xref:intval', node[1])
