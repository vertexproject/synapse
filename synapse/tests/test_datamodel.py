import synapse.exc as s_exc
import synapse.datamodel as s_datamodel
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils

class DataModelTest(s_t_utils.SynTest):

    async def test_datmodel_formname(self):
        modl = s_datamodel.Model()
        mods = (
            ('hehe', {
                'types': (
                    ('derp', ('int', {}), {}),
                ),
                'forms': (
                    ('derp', {}, ()),
                ),
            }),
        )

        with self.raises(s_exc.BadFormDef):
            modl.addDataModels(mods)

    async def test_datamodel_getModelDef(self):

        async with self.getTestCore() as core:
            modeldef = core.model.getModelDef()

            # Verify it doesn't have any unmarshallable elements
            s_msgpack.en(modeldef)

            for field in ('ctors', 'types', 'forms', 'univs'):
                self.isin(field, modeldef[0][1])
                self.lt(0, len(modeldef[0][1][field]))

            modelinfo = s_datamodel.ModelInfo()
            modelinfo.addDataModels(modeldef)
            self.true(modelinfo.isform('test:str'))
            self.true(modelinfo.isuniv('.seen'))
            self.false(modelinfo.isuniv('seen'))
            self.true(modelinfo.isprop('test:type10:intprop'))
            self.true(modelinfo.isprop('test:type10.seen'))

    async def test_datamodel_indx_too_big(self):
        async with self.getTestCore() as core:
            with self.raises(s_exc.BadIndxValu):
                core.model.form('test:type').getSetOps('test:type', 'A' * 512)
