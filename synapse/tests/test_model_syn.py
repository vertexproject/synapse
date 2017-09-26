import synapse.cortex as s_cortex

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
