import synapse.datamodel as s_datamodel

import synapse.tests.utils as s_t_utils

import unittest
raise unittest.SkipTest()

class DataModelTest(s_t_utils.SynTest):

    def test_datamodel_types(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'bar', ptype='int')
        model.addTufoProp('foo', 'baz', ptype='str')
        model.addTufoProp('foo', 'faz', ptype='syn:tag')
        model.addTufoProp('foo', 'zip', ptype='str:lwr')

        self.eq(model.getPropRepr('foo:bar', 10), '10')
        self.eq(model.getPropRepr('foo:baz', 'woot'), 'woot')
        self.eq(model.getPropRepr('foo:faz', 'woot.toow'), 'woot.toow')
        self.eq(model.getPropRepr('foo:zip', 'woot'), 'woot')
        self.eq(model.getPropRepr('foo:nonexistent', 'stillwoot'), 'stillwoot')

        self.eq(model.getPropType('foo:bar').name, 'int')

        self.eq(model.getPropNorm('foo:bar', 10)[0], 10)
        self.eq(model.getPropNorm('foo:baz', 'woot')[0], 'woot')
        self.eq(model.getPropNorm('foo:faz', 'WOOT.toow')[0], 'woot.toow')
        self.eq(model.getPropNorm('foo:zip', 'WOOT')[0], 'woot')

        self.eq(model.getPropParse('foo:bar', '10')[0], 10)
        self.eq(model.getPropParse('foo:baz', 'woot')[0], 'woot')
        self.eq(model.getPropParse('foo:faz', 'WOOT.toow')[0], 'woot.toow')
        self.eq(model.getPropParse('foo:zip', 'WOOT')[0], 'woot')
        self.eq(model.getPropParse('foo:nonexistent', 'stillwoot'), 'stillwoot')

    def test_datamodel_glob(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'bar:*', ptype='str:lwr', glob=1)
        self.eq(model.getPropNorm('foo:bar:baz', 'Woot')[0], 'woot')

    def test_datamodel_fail_notype(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        self.raises(NoSuchType, model.addTufoProp, 'foo', 'bar', ptype='hehe')

    def test_datamodel_fail_noprop(self):
        model = s_datamodel.DataModel()

        self.raises(NoSuchForm, model.addTufoProp, 'foo', 'bar')

        model.addTufoForm('foo')
        self.raises(DupPropName, model.addTufoForm, 'foo')

        model.addTufoProp('foo', 'bar')
        self.raises(DupPropName, model.addTufoProp, 'foo', 'bar')

    def test_datamodel_cortex(self):
        core = s_cortex.openurl('ram:///')

        core.addTufoForm('foo', ptype='str')
        core.addTufoProp('foo', 'bar', ptype='int', defval=10)

        core.formTufoByProp('foo', 'hehe')
        core.formTufoByProp('foo', 'haha')

        core.formTufoByProp('foo', 'blah', bar=99)

        tufo0 = core.formTufoByProp('foo', 'hehe')
        self.eq(tufo0[1].get('foo:bar'), 10)

        core.setTufoProp(tufo0, 'bar', 30)
        self.eq(tufo0[1].get('foo:bar'), 30)

        tufo1 = core.formTufoByProp('foo', 'hehe')
        self.eq(tufo0[0], tufo1[0])

        tufos = core.getTufosByProp('foo')
        self.len(3, tufos)

        tufos = core.getTufosByProp('foo:bar', valu=30, limit=20)
        self.len(1, tufos)

        tufos = core.getTufosByProp('foo:bar', valu=99, limit=20)
        self.len(1, tufos)

    def test_datamodel_subs(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'bar', ptype='int')

        subs = model.getSubProps('foo')

        self.len(1, subs)
        self.eq(subs[0][0], 'foo:bar')

        model.addTufoProp('foo', 'baz', ptype='int', defval=20)

        defs = model.getSubPropDefs('foo')
        self.eq(defs.get('foo:baz'), 20)

    def test_datamodel_bool(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'bar', ptype='bool', defval=0)

        self.eq(model.getPropRepr('foo:bar', 1), 'True')
        self.eq(model.getPropRepr('foo:bar', 0), 'False')

        self.eq(model.getPropNorm('foo:bar', True)[0], 1)
        self.eq(model.getPropNorm('foo:bar', False)[0], 0)

        self.eq(model.getPropParse('foo:bar', '1')[0], 1)
        self.eq(model.getPropParse('foo:bar', '0')[0], 0)

        self.raises(BadTypeValu, model.getPropParse, 'foo:bar', 'asdf')

    def test_datamodel_hash(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')

        model.addTufoProp('foo', 'md5', ptype='hash:md5')
        model.addTufoProp('foo', 'sha1', ptype='hash:sha1')
        model.addTufoProp('foo', 'sha256', ptype='hash:sha256')

        fakemd5 = 'AA' * 16
        fakesha1 = 'AA' * 20
        fakesha256 = 'AA' * 32

        self.eq(model.getPropNorm('foo:md5', fakemd5)[0], fakemd5.lower())
        self.eq(model.getPropNorm('foo:sha1', fakesha1)[0], fakesha1.lower())
        self.eq(model.getPropNorm('foo:sha256', fakesha256)[0], fakesha256.lower())

        self.raises(BadTypeValu, model.getPropNorm, 'foo:md5', 'asdf')
        self.raises(BadTypeValu, model.getPropNorm, 'foo:sha1', 'asdf')
        self.raises(BadTypeValu, model.getPropNorm, 'foo:sha256', 'asdf')

        self.eq(model.getPropParse('foo:md5', fakemd5)[0], fakemd5.lower())
        self.eq(model.getPropParse('foo:sha1', fakesha1)[0], fakesha1.lower())
        self.eq(model.getPropParse('foo:sha256', fakesha256)[0], fakesha256.lower())

        self.raises(BadTypeValu, model.getPropParse, 'foo:md5', 'asdf')
        self.raises(BadTypeValu, model.getPropParse, 'foo:sha1', 'asdf')
        self.raises(BadTypeValu, model.getPropParse, 'foo:sha256', 'asdf')

    def test_datamodel_parsetypes(self):

        class Woot:
            @s_datamodel.parsetypes('int', 'str:lwr')
            def getFooBar(self, size, flag):
                return {'size': size, 'flag': flag}

            @s_datamodel.parsetypes('int', flag='str:lwr')
            def getBazFaz(self, size, flag=None):
                return {'size': size, 'flag': flag}

        woot = Woot()

        ret = woot.getFooBar('30', 'ASDF')

        self.eq(ret.get('size'), 30)
        self.eq(ret.get('flag'), 'asdf')

        ret = woot.getBazFaz('10')

        self.eq(ret.get('size'), 10)
        self.eq(ret.get('flag'), None)

        ret = woot.getBazFaz('10', flag='ASDF')
        self.eq(ret.get('size'), 10)
        self.eq(ret.get('flag'), 'asdf')

    def test_datamodel_inet(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'addr', ptype='inet:ipv4')
        model.addTufoProp('foo', 'serv', ptype='inet:srv4')
        model.addTufoProp('foo', 'port', ptype='inet:port')

        self.eq(model.getPropNorm('foo:port', 20)[0], 20)
        self.eq(model.getPropParse('foo:port', '0x10')[0], 16)

        self.eq(model.getPropRepr('foo:addr', 0x01020304), '1.2.3.4')
        self.eq(model.getPropNorm('foo:addr', 0x01020304)[0], 0x01020304)
        self.eq(model.getPropParse('foo:addr', '1.2.3.4')[0], 0x01020304)

        self.eq(model.getPropRepr('foo:serv', 0x010203040010), '1.2.3.4:16')
        self.eq(model.getPropNorm('foo:serv', 0x010203040010)[0], 0x010203040010)
        self.eq(model.getPropParse('foo:serv', '1.2.3.4:255')[0], 0x0102030400ff)

        self.raises(BadTypeValu, model.getPropNorm, 'foo:port', 0xffffff)
        self.raises(BadTypeValu, model.getPropParse, 'foo:port', '999999')

    def test_datamodel_time(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'meow', ptype='time:epoch')

        jan1_2016 = 1451606400
        self.eq(model.getPropNorm('foo:meow', jan1_2016)[0], jan1_2016)
        self.eq(model.getPropRepr('foo:meow', jan1_2016), '2016/01/01 00:00:00')
        self.eq(model.getPropParse('foo:meow', '2016/01/01 00:00:00')[0], jan1_2016)

    def test_datamodel_badprop(self):
        model = s_datamodel.DataModel()

        self.raises(BadPropName, model.addTufoForm, 'foo.bar')

        model.addTufoForm('foo:bar')
        self.raises(BadPropName, model.addTufoProp, 'foo:bar', 'b*z')

    def test_datatype_syn_prop(self):
        model = s_datamodel.DataModel()

        self.raises(BadTypeValu, model.getTypeNorm, 'syn:prop', 'asdf qwer')
        self.raises(BadTypeValu, model.getTypeNorm, 'syn:prop', 'foo::bar')

        self.eq(model.getTypeNorm('syn:prop', 'BAR')[0], 'bar')
        self.eq(model.getTypeParse('syn:prop', 'BAR')[0], 'bar')
        self.eq(model.getTypeNorm('syn:prop', 'foo:BAR')[0], 'foo:bar')
        self.eq(model.getTypeParse('syn:prop', 'foo:BAR')[0], 'foo:bar')

    def test_datatype_syn_tag(self):
        model = s_datamodel.DataModel()

        self.raises(BadTypeValu, model.getTypeNorm, 'syn:tag', 'asdf qwer')
        self.raises(BadTypeValu, model.getTypeNorm, 'syn:tag', 'foo..bar')

        self.eq(model.getTypeNorm('syn:tag', 'BAR')[0], 'bar')
        self.eq(model.getTypeParse('syn:tag', 'BAR')[0], 'bar')
        self.eq(model.getTypeNorm('syn:tag', 'foo.BAR')[0], 'foo.bar')
        self.eq(model.getTypeParse('syn:tag', 'foo.BAR')[0], 'foo.bar')

    def test_datamodel_forms(self):
        model = s_datamodel.DataModel(load=False)
        forms = model.getTufoForms()
        self.isinstance(forms, list)
        self.notin('syn:prop', forms)
        self.notin('inet:ipv4', forms)

        model = s_datamodel.DataModel()
        forms = model.getTufoForms()
        self.isin('syn:prop', forms)
        self.isin('inet:ipv4', forms)

    def test_datamodel_getPropInfo(self):
        model = s_datamodel.DataModel()

        model.addType('foo:bar', subof='str', doc='foo bar doc')
        model.addType('foo:baz', subof='foo:bar')

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'meow', ptype='foo:baz')
        model.addTufoProp('foo', 'bark', doc='lala')
        model.addTufoProp('foo', 'meow:purr', ptype='foo:baz', title='purr', doc='The sound a purr makes')

        self.eq(model.getPropInfo('foo:meow', 'req'), False)
        self.eq(model.getPropInfo('foo:meow', 'base'), 'meow')
        self.eq(model.getPropInfo('foo:meow', 'relname'), 'meow')
        self.eq(model.getPropInfo('foo:meow', 'defval'), None)
        self.eq(model.getPropInfo('foo:meow', 'title'), '')
        self.eq(model.getPropInfo('foo:meow', 'doc'), 'foo bar doc')

        self.eq(model.getPropInfo('foo:bark', 'doc'), 'lala')
        self.eq(model.getPropInfo('foo:bark', 'title'), '')
        self.eq(model.getPropInfo('foo:bark', 'base'), 'bark')
        self.eq(model.getPropInfo('foo:bark', 'relname'), 'bark')
        self.eq(model.getPropInfo('foo:meow', 'defval'), None)
        self.eq(model.getPropInfo('foo:meow', 'req'), False)

        self.eq(model.getPropInfo('foo:meow:purr', 'req'), False)
        self.eq(model.getPropInfo('foo:meow:purr', 'base'), 'purr')
        self.eq(model.getPropInfo('foo:meow:purr', 'relname'), 'meow:purr')
        self.eq(model.getPropInfo('foo:meow:purr', 'defval'), None)
        self.eq(model.getPropInfo('foo:meow:purr', 'title'), 'purr')
        self.eq(model.getPropInfo('foo:meow:purr', 'doc'), 'The sound a purr makes')

        self.eq(model.getPropInfo('foo:nonexistent', 'doc'), None)

    def test_datamodel_getPropDef(self):
        model = s_datamodel.DataModel()

        model.addTufoForm('foo')
        model.addTufoProp('foo', 'meow', ptype='int')

        self.eq(model.getPropDef('foo:meow'),
                ('foo:meow', {'title': '',
                              'req': False,
                              'form': 'foo',
                              'relname': 'meow',
                              'base': 'meow',
                              'defval': None,
                              'ptype': 'int',
                              'doc': 'The base integer type',
                              'univ': False,
                              }
                 )
                )
        self.eq(model.getPropDef('foo:meow:nonexistent'), None)
        self.eq(model.getPropDef('foo:meow:nonexistent', glob=False), None)

    def test_datamodel_typefns(self):
        self.eq(s_datamodel.getTypeRepr('str', 'haha'), 'haha')
        self.eq(s_datamodel.getTypeRepr('inet:ipv4', 0x01020304), '1.2.3.4')

        self.eq(s_datamodel.getTypeNorm('str', 'haha'), ('haha', {}))
        self.eq(s_datamodel.getTypeNorm('inet:ipv4', 0x01020304), (16909060, {}))
        self.eq(s_datamodel.getTypeNorm('inet:ipv4', '1.2.3.4'), (16909060, {}))

        self.raises(BadTypeValu, s_datamodel.getTypeNorm, 'inet:ipv4', 'hahaha')

        self.eq(s_datamodel.getTypeParse('str', 'haha'), ('haha', {}))
        self.eq(s_datamodel.getTypeParse('inet:ipv4', '1.2.3.4'), (16909060, {}))

    def test_datamodel_filepath(self):
        model = s_datamodel.DataModel()
        prop = 'file:path'

        data = (
            ('/', ('/', {'dir': '', 'depth': 0}), '/'),
            ('//', ('/', {'dir': '', 'depth': 0}), '//'),
            ('////////////', ('/', {'dir': '', 'depth': 0}), '////////////'),
            ('weirD', ('weird', {'base': 'weird', 'dir': '', 'depth': 1}), 'weirD'),

            ('foo1', ('foo1', {'base': 'foo1', 'dir': '', 'depth': 1}), 'foo1'),
            ('/foo2', ('/foo2', {'base': 'foo2', 'dir': '', 'depth': 1}), '/foo2'),
            ('/foo/bar3', ('/foo/bar3', {'base': 'bar3', 'dir': '/foo', 'depth': 2}), '/foo/bar3'),
            ('/foo/bar4    ', ('/foo/bar4    ', {'base': 'bar4    ', 'dir': '/foo', 'depth': 2}), '/foo/bar4    '),  # These are valid filepaths
            ('/foo/bar5/', ('/foo/bar5', {'base': 'bar5', 'dir': '/foo', 'depth': 2}), '/foo/bar5/'),

            ('C:\\', ('c:', {'base': 'c:', 'depth': 1, 'dir': ''}), 'C:\\'),
            ('C:\\Program Files\\Foo.bAr.BAZ.exe',
                ('c:/program files/foo.bar.baz.exe', {'base': 'foo.bar.baz.exe', 'dir': 'c:/program files', 'depth': 3, 'ext': 'exe'}), 'C:\\Program Files\\Foo.bAr.BAZ.exe')
        )

        for valu, expected, expected_repr in data:

            self.eq(expected, model.getTypeNorm(prop, valu))
            self.eq(expected, model.getTypeParse(prop, valu))
            self.eq(expected_repr, model.getTypeRepr(prop, valu))

    def test_datamodel_filebase(self):
        model = s_datamodel.DataModel()
        prop = 'file:base'

        data = (
            ('my_COOL_file', ('my_cool_file', {}), 'my_COOL_file'),
            ('my      file', ('my      file', {}), 'my      file'),
            ('!@#$%^&.jpeg', ('!@#$%^&.jpeg', {}), '!@#$%^&.jpeg'),
        )

        for valu, expected, expected_repr in data:

            self.eq(expected, model.getTypeNorm(prop, valu))
            self.eq(expected, model.getTypeParse(prop, valu))
            self.eq(expected_repr, model.getTypeRepr(prop, valu))

        bads = (None, [], {}, 1, '/teehee', 'hoho/haha')
        for bad in bads:
            self.raises(BadTypeValu, model.getTypeNorm, prop, bad)
            self.raises(BadTypeValu, model.getTypeParse, prop, bad)

    def test_datamodel_formbase(self):

        modl = s_datamodel.DataModel()
        modl.addTufoForm('foo:bar')
        modl.addTufoProp('foo:bar', 'baz')

        form, base = modl.getPropFormBase('foo:bar:baz')

        self.eq(form, 'foo:bar')
        self.eq(base, 'baz')

        self.raises(NoSuchProp, modl.getPropFormBase, 'newp:newp')

    def test_datamodel_reqpropnorm(self):
        with self.getRamCore() as core:
            v, _ = core.reqPropNorm('strform:foo', '1')
            self.eq(v, '1')
            self.raises(NoSuchProp, core.reqPropNorm, 'strform:beepbeep', '1')

    def test_datamodel_istufoform(self):
        modl = s_datamodel.DataModel()
        self.true(modl.isTufoForm('file:bytes'))
        self.false(modl.isTufoForm('file:bytes:size'))
        self.false(modl.isTufoForm('node:ndef'))

        self.none(modl.reqTufoForm('file:bytes'))
        self.raises(NoSuchForm, modl.reqTufoForm, 'file:bytes:size')

    def test_datamodel_cast_json(self):
        modl = s_datamodel.DataModel()
        self.eq(modl.getTypeCast('make:json', 1), '1')
        self.eq(modl.getTypeCast('make:json', 'hehe'), '"hehe"')
        self.eq(modl.getTypeCast('make:json', '"hehe"'), '"\\"hehe\\""')
        self.eq(modl.getTypeCast('make:json', {"z": 1, 'yo': 'dawg', }), '{"yo":"dawg","z":1}')

    def test_datamodel_cast_int10(self):
        modl = s_datamodel.DataModel()
        self.eq(modl.getTypeCast('int:2:str10', 1), '1')
        self.eq(modl.getTypeCast('int:2:str10', 100), '100')
        self.eq(modl.getTypeCast('int:2:str10', 0x11), '17')
        self.eq(modl.getTypeCast('int:2:str10', 'hehe'), 'hehe')

    def test_datamodel_type_hook(self):
        defs = []
        modl = s_datamodel.DataModel()
        modl.addType('gronk', subof='guid')
        modl.addPropDef('foo:bar', ptype='gronk')
        modl.addPropTypeHook('gronk', defs.append)

        self.len(1, defs)
        self.eq(defs[0][0], 'foo:bar')

        modl.addPropDef('foo:baz', ptype='gronk')

        self.len(2, defs)
        self.eq(defs[1][0], 'foo:baz')

    def test_datamodel_istufoprop(self):
        modl = s_datamodel.DataModel()

        # Types are not props
        self.false(modl.isTufoProp('str:lwr'))

        # Prop does not yet exist
        self.false(modl.isTufoProp('foo:meow'))
        modl.addTufoForm('foo')
        modl.addTufoProp('foo', 'meow', ptype='str:lwr')
        # Forms are props
        self.true(modl.isTufoProp('foo'))
        # And props are props!
        self.true(modl.isTufoProp('foo:meow'))
