import unittest

import synapse.cortex as s_cortex
import synapse.datamodel as s_datamodel

class DataModelTest(unittest.TestCase):

    def test_datamodel_types(self):
        model = s_datamodel.DataModel()
        model.addTufoForm('foo')
        model.addTufoProp('foo', 'bar', ptype='int')
        model.addTufoProp('foo', 'baz', ptype='str')
        model.addTufoProp('foo', 'faz', ptype='tag')
        model.addTufoProp('foo', 'zip', ptype='lwr')

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
        model.addTufoForm('foo')
        model.addPropGlob('foo:bar:*',ptype='lwr')
        self.assertEqual( model.getPropNorm('foo:bar:baz','Woot'), 'woot' )

    def test_datamodel_fail_notype(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        self.assertRaises( s_datamodel.NoSuchType, model.addTufoProp, 'foo', 'bar', ptype='hehe' )

    def test_datamodel_fail_duptype(self):
        model = s_datamodel.DataModel()
        model.addDataType('foo', s_datamodel.StrType())
        self.assertRaises( s_datamodel.DupDataType, model.addDataType, 'foo', s_datamodel.StrType())

    def test_datamodel_fail_noprop(self):
        model = s_datamodel.DataModel()
        self.assertRaises( s_datamodel.NoSuchForm, model.addTufoProp, 'foo', 'bar' )

        model.addTufoForm('foo')
        self.assertRaises( s_datamodel.DupPropName, model.addTufoForm, 'foo' )

        model.addTufoProp('foo','bar')
        self.assertRaises( s_datamodel.DupPropName, model.addTufoProp, 'foo', 'bar' )

    def test_datamodel_cortex(self):

        model = s_datamodel.DataModel()
        model.addTufoForm('foo')
        model.addTufoProp('foo', 'bar', ptype='int', defval=10)

        core = s_cortex.openurl('ram:///')
        core.setDataModel( model )

        core.formTufoByProp('foo','hehe')
        core.formTufoByProp('foo','haha')

        core.formTufoByProp('foo','blah', bar=99)

        tufo0 = core.formTufoByProp('foo','hehe')
        self.assertEqual( tufo0[1].get('foo:bar'), 10 )

        core.setTufoProp(tufo0,'bar',30)
        self.assertEqual( tufo0[1].get('foo:bar'), 30 )

        tufo1 = core.formTufoByProp('foo','hehe')
        self.assertEqual( tufo0[0], tufo1[0] )

        tufos = core.getTufosByProp('foo')
        self.assertEqual( len(tufos) , 3 )

        tufos = core.getTufosByProp('foo:bar', valu=30, limit=20)
        self.assertEqual( len(tufos) , 1 )

        tufos = core.getTufosByProp('foo:bar', valu=99, limit=20)
        self.assertEqual( len(tufos) , 1 )

    def test_datamodel_subs(self):
        model = s_datamodel.DataModel()
        model.addTufoForm('foo')
        model.addTufoProp('foo','bar',ptype='int')

        subs = model.getSubProps('foo')

        self.assertEqual( len(subs), 1 )
        self.assertEqual( subs[0][0], 'foo:bar' )

        model.addTufoProp('foo','baz',ptype='int', defval=20)

        defs = model.getSubPropDefs('foo')
        self.assertEqual( defs.get('foo:baz'), 20 )

    def test_datamodel_bool(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo','bar',ptype='bool', defval=0)

        self.assertEqual( model.getPropRepr('foo:bar', 1), 'True')
        self.assertEqual( model.getPropRepr('foo:bar', 0), 'False')

        self.assertEqual( model.getPropNorm('foo:bar', True) , 1 )
        self.assertEqual( model.getPropNorm('foo:bar', False) , 0 )

        self.assertEqual( model.getPropParse('foo:bar', 'TRUE'), 1 )
        self.assertEqual( model.getPropParse('foo:bar', 'FaLsE'), 0 )

        self.assertRaises( s_datamodel.BadTypeParse, model.getPropParse, 'foo:bar', 'asdf' )
