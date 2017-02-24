import unittest

import synapse.cortex as s_cortex
import synapse.datamodel as s_datamodel

from synapse.tests.common import *

class DataModelTest(SynTest):

    def test_datamodel_types(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'bar', ptype='int')
        model.addTufoProp('foo', 'baz', ptype='str')
        model.addTufoProp('foo', 'faz', ptype='syn:tag')
        model.addTufoProp('foo', 'zip', ptype='str:lwr')

        self.assertEqual( model.getPropRepr('foo:bar', 10), '10')
        self.assertEqual( model.getPropRepr('foo:baz', 'woot'), 'woot')
        self.assertEqual( model.getPropRepr('foo:faz', 'woot.toow'), 'woot.toow')
        self.assertEqual( model.getPropRepr('foo:zip', 'woot'), 'woot')

        self.assertEqual( model.getPropNorm('foo:bar', 10)[0], 10)
        self.assertEqual( model.getPropNorm('foo:baz', 'woot')[0], 'woot')
        self.assertEqual( model.getPropNorm('foo:faz', 'WOOT.toow')[0], 'woot.toow')
        self.assertEqual( model.getPropNorm('foo:zip', 'WOOT')[0], 'woot')

        self.assertEqual( model.getPropParse('foo:bar', '10')[0], 10)
        self.assertEqual( model.getPropParse('foo:baz', 'woot')[0], 'woot')
        self.assertEqual( model.getPropParse('foo:faz', 'WOOT.toow')[0], 'woot.toow')
        self.assertEqual( model.getPropParse('foo:zip', 'WOOT')[0], 'woot')

        self.assertEqual( model.getPropFrob('foo:bar', 10), (10, {}))
        self.assertEqual( model.getPropFrob('foo:bar', '10'), (10, {}))
        self.assertEqual( model.getPropFrob('foo:baz', 'woot'), ('woot', {}))
        self.assertEqual( model.getPropFrob('foo:faz', 'WOOT.toow'), ('woot.toow',{}))
        self.assertEqual( model.getPropFrob('foo:zip', 'WOOT'), ('woot',{}))
        self.assertEqual( model.getPropFrob('foo:bar', 'not an integer'), (None, {}))

    def test_datamodel_glob(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo','bar:*', ptype='str:lwr', glob=1)
        self.assertEqual( model.getPropNorm('foo:bar:baz','Woot')[0], 'woot' )

    def test_datamodel_fail_notype(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        self.assertRaises( s_datamodel.NoSuchType, model.addTufoProp, 'foo', 'bar', ptype='hehe' )

    def test_datamodel_fail_noprop(self):
        model = s_datamodel.DataModel()

        self.assertRaises( NoSuchForm, model.addTufoProp, 'foo', 'bar' )

        model.addTufoForm('foo')
        self.assertRaises( DupPropName, model.addTufoForm, 'foo' )

        model.addTufoProp('foo','bar')
        self.assertRaises( DupPropName, model.addTufoProp, 'foo', 'bar' )

    def test_datamodel_cortex(self):
        core = s_cortex.openurl('ram:///')

        core.addTufoForm('foo')
        core.addTufoProp('foo', 'bar', ptype='int', defval=10)

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

        self.assertEqual( model.getPropNorm('foo:bar', True)[0] , 1 )
        self.assertEqual( model.getPropNorm('foo:bar', False)[0] , 0 )

        self.assertEqual( model.getPropParse('foo:bar', '1')[0], 1 )
        self.assertEqual( model.getPropParse('foo:bar', '0')[0], 0 )

        self.assertRaises( BadTypeValu, model.getPropParse, 'foo:bar', 'asdf' )

    def test_datamodel_hash(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')

        model.addTufoProp('foo','md5', ptype='hash:md5')
        model.addTufoProp('foo','sha1', ptype='hash:sha1')
        model.addTufoProp('foo','sha256', ptype='hash:sha256')

        fakemd5 = 'AA' * 16
        fakesha1 = 'AA' * 20
        fakesha256= 'AA' * 32

        self.assertEqual( model.getPropNorm('foo:md5', fakemd5)[0] , fakemd5.lower() )
        self.assertEqual( model.getPropNorm('foo:sha1', fakesha1)[0] , fakesha1.lower() )
        self.assertEqual( model.getPropNorm('foo:sha256', fakesha256)[0] , fakesha256.lower() )

        self.assertRaises( BadTypeValu, model.getPropNorm, 'foo:md5', 'asdf' )
        self.assertRaises( BadTypeValu, model.getPropNorm, 'foo:sha1', 'asdf' )
        self.assertRaises( BadTypeValu, model.getPropNorm, 'foo:sha256', 'asdf' )

        self.assertEqual( model.getPropParse('foo:md5', fakemd5)[0] , fakemd5.lower() )
        self.assertEqual( model.getPropParse('foo:sha1', fakesha1)[0] , fakesha1.lower() )
        self.assertEqual( model.getPropParse('foo:sha256', fakesha256)[0] , fakesha256.lower() )

        self.assertRaises( BadTypeValu, model.getPropParse, 'foo:md5', 'asdf' )
        self.assertRaises( BadTypeValu, model.getPropParse, 'foo:sha1', 'asdf' )
        self.assertRaises( BadTypeValu, model.getPropParse, 'foo:sha256', 'asdf' )

    def test_datamodel_parsetypes(self):

        class Woot:
            @s_datamodel.parsetypes('int','str:lwr')
            def getFooBar(self, size, flag):
                return {'size':size, 'flag':flag}

            @s_datamodel.parsetypes('int',flag='str:lwr')
            def getBazFaz(self, size, flag=None):
                return {'size':size, 'flag':flag }

        woot = Woot()

        ret = woot.getFooBar('30','ASDF')

        self.assertEqual( ret.get('size'), 30 )
        self.assertEqual( ret.get('flag'), 'asdf')

        ret = woot.getBazFaz('10')

        self.assertEqual( ret.get('size'), 10 )
        self.assertEqual( ret.get('flag'), None )

        ret = woot.getBazFaz('10', flag='ASDF')
        self.assertEqual( ret.get('size'), 10 )
        self.assertEqual( ret.get('flag'), 'asdf')

    def test_datamodel_inet(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo','addr', ptype='inet:ipv4')
        model.addTufoProp('foo','serv', ptype='inet:srv4')
        model.addTufoProp('foo','port', ptype='inet:port')

        self.assertEqual( model.getPropNorm('foo:port',20)[0], 20 )
        self.assertEqual( model.getPropParse('foo:port','0x10')[0], 16 )

        self.assertEqual( model.getPropRepr('foo:addr', 0x01020304), '1.2.3.4')
        self.assertEqual( model.getPropNorm('foo:addr',0x01020304)[0], 0x01020304 )
        self.assertEqual( model.getPropParse('foo:addr','1.2.3.4')[0], 0x01020304 )

        self.assertEqual( model.getPropRepr('foo:serv', 0x010203040010), '1.2.3.4:16')
        self.assertEqual( model.getPropNorm('foo:serv',0x010203040010)[0], 0x010203040010 )
        self.assertEqual( model.getPropParse('foo:serv','1.2.3.4:255')[0], 0x0102030400ff )

        self.assertRaises( BadTypeValu, model.getPropNorm, 'foo:port', 0xffffff )
        self.assertRaises( BadTypeValu, model.getPropParse, 'foo:port', '999999' )

    def test_datamodel_time(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo','meow', ptype='time:epoch')

        jan1_2016 = 1451606400
        self.assertEqual( model.getPropNorm('foo:meow',jan1_2016)[0], jan1_2016)
        self.assertEqual( model.getPropRepr('foo:meow', jan1_2016), '2016/01/01 00:00:00')
        self.assertEqual( model.getPropParse('foo:meow','2016/01/01 00:00:00')[0], jan1_2016)

    def test_datamodel_badprop(self):
        model = s_datamodel.DataModel()

        self.assertRaises( s_datamodel.BadPropName, model.addTufoForm, 'foo.bar' )

        model.addTufoForm('foo:bar')
        self.assertRaises( s_datamodel.BadPropName, model.addTufoProp, 'foo:bar', 'b*z' )

    def test_datatype_syn_prop(self):
        model = s_datamodel.DataModel()

        self.assertRaises(BadTypeValu, model.getTypeNorm, 'syn:prop', 'asdf qwer' )
        self.assertRaises(BadTypeValu, model.getTypeNorm, 'syn:prop', 'foo::bar' )

        self.eq( model.getTypeFrob('syn:prop','BAR')[0], 'bar' )
        self.eq( model.getTypeNorm('syn:prop','BAR')[0], 'bar' )
        self.eq( model.getTypeParse('syn:prop','BAR')[0], 'bar' )
        self.eq( model.getTypeNorm('syn:prop','foo:BAR')[0], 'foo:bar' )
        self.eq( model.getTypeParse('syn:prop','foo:BAR')[0], 'foo:bar' )

    def test_datatype_syn_tag(self):
        model = s_datamodel.DataModel()

        self.assertRaises(BadTypeValu, model.getTypeNorm, 'syn:tag', 'asdf qwer' )
        self.assertRaises(BadTypeValu, model.getTypeNorm, 'syn:tag', 'foo..bar' )

        self.eq( model.getTypeNorm('syn:tag','BAR')[0], 'bar' )
        self.eq( model.getTypeParse('syn:tag','BAR')[0], 'bar' )
        self.eq( model.getTypeNorm('syn:tag','foo.BAR')[0], 'foo.bar' )
        self.eq( model.getTypeParse('syn:tag','foo.BAR')[0], 'foo.bar' )

    def test_datamodel_getPropInfo(self):
        model = s_datamodel.DataModel()

        model.addType('foo:bar', subof='str', doc='foo bar doc')
        model.addType('foo:baz', subof='foo:bar')

        model.addTufoForm('foo')
        model.addTufoProp('foo','meow', ptype='foo:baz')

        self.eq( model.getPropInfo('foo:meow','doc'), 'foo bar doc' )
