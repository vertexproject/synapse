import unittest

import synapse.cortex as s_cortex
import synapse.datamodel as s_datamodel

class DataModelTest(unittest.TestCase):

    def test_datamodel_types(self):
        model = s_datamodel.DataModel()
        model.addDataTufo('foo')
        model.addTufoProp('foo', 'foo:bar', ptype='int')
        model.addTufoProp('foo', 'foo:baz', ptype='str')
        model.addTufoProp('foo', 'foo:faz', ptype='tag')
        model.addTufoProp('foo', 'foo:zip', ptype='lwr')

        self.assertEqual( model.getPropRepr('foo:bar', 10), '10')
        self.assertEqual( model.getPropRepr('foo:baz', 'woot'), 'woot')
        self.assertEqual( model.getPropRepr('foo:faz', 'woot.toow'), 'woot.toow')
        self.assertEqual( model.getPropRepr('foo:zip', 'woot'), 'woot')

        self.assertEqual( model.getPropNorm('foo:bar', 10), 10)
        self.assertEqual( model.getPropNorm('foo:baz', 'woot'), 'woot')
        self.assertEqual( model.getPropNorm('foo:faz', 'WOOT.toow'), 'woot.toow')
        self.assertEqual( model.getPropNorm('foo:zip', 'WOOT'), 'woot')

        self.assertEqual( model.getPropParse('foo:bar', '10'), 10)
        self.assertEqual( model.getPropParse('foo:baz', 'woot'), 'woot')
        self.assertEqual( model.getPropParse('foo:faz', 'WOOT.toow'), 'woot.toow')
        self.assertEqual( model.getPropParse('foo:zip', 'WOOT'), 'woot')

    def test_datamodel_glob(self):
        model = s_datamodel.DataModel()
        model.addDataTufo('foo')
        model.addTufoGlob('foo', 'foo:bar:*', 'tag')
        self.assertEqual( model.getPropNorm('foo:bar:baz','Woot'), 'woot' )

    def test_datamodel_fail_notype(self):
        model = s_datamodel.DataModel()

        model.addDataTufo('foo')
        self.assertRaises( s_datamodel.NoSuchType, model.addTufoProp, 'foo', 'foo:bar', ptype='hehe' )

    def test_datamodel_fail_duptype(self):
        model = s_datamodel.DataModel()
        model.addDataType('foo', s_datamodel.StrType())
        self.assertRaises( s_datamodel.DupDataType, model.addDataType, 'foo', s_datamodel.StrType())

    def test_datamodel_fail_noprop(self):
        model = s_datamodel.DataModel()
        self.assertRaises( s_datamodel.NoSuchTufo, model.addTufoProp, 'foo', 'foo:bar' )

        model.addDataTufo('foo')
        self.assertRaises( s_datamodel.DupTufoName, model.addDataTufo, 'foo' )

        self.assertRaises( s_datamodel.NoSuchProp, model.getPropNorm, 'foo:bar', 'hehe' )
        self.assertRaises( s_datamodel.NoSuchProp, model.getPropRepr, 'foo:bar', 'hehe' )
        self.assertRaises( s_datamodel.NoSuchProp, model.getPropParse, 'foo:bar', 'hehe' )

        model.addTufoProp('foo','foo:bar')
        self.assertRaises( s_datamodel.DupTufoProp, model.addTufoProp, 'foo', 'foo:bar' )

    def test_datamodel_cortex(self):

        model = s_datamodel.DataModel()
        model.addDataTufo('foo')
        model.addTufoProp('foo', 'foo:bar', ptype='int', defval=10)

        core = s_cortex.openurl('ram:///')
        core.setDataModel( model )

        core.formTufoByProp('foo','hehe')
        core.formTufoByProp('foo','haha')

        props = {'foo:bar':99}
        core.formTufoByProp('foo','blah', **props)

        tufo0 = core.formTufoByProp('foo','hehe')
        self.assertEqual( tufo0[1].get('foo:bar'), 10 )

        core.setTufoProp(tufo0,'foo:bar',30)
        self.assertEqual( tufo0[1].get('foo:bar'), 30 )

        tufo1 = core.formTufoByProp('foo','hehe')
        self.assertEqual( tufo0[0], tufo1[0] )

        tufos = core.getTufosByProp('foo')
        self.assertEqual( len(tufos) , 3 )

        tufos = core.getTufosByProp('foo:bar', valu=30, limit=20)
        self.assertEqual( len(tufos) , 1 )

        tufos = core.getTufosByProp('foo:bar', valu=99, limit=20)
        self.assertEqual( len(tufos) , 1 )
