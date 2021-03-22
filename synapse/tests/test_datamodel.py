import synapse.exc as s_exc
import synapse.datamodel as s_datamodel

import synapse.lib.module as s_module

import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils

depmodel = {
    'ctors': (
        ('test:dep:str', 'synapse.lib.types.Str', {'strip': True}, {'deprecated': True}),
    ),
    'types': (
        ('test:dep:easy', ('test:str', {}), {'deprecated': True}),
        ('test:dep:comp', ('comp', {'fields': (('int', 'test:int'), ('str', 'test:dep:easy'))}), {}),
        ('test:dep:array', ('array', {'type': 'test:dep:easy'}), {})
    ),
    'forms': (
        ('test:dep:easy', {'deprecated': True}, (
            ('guid', ('test:guid', {}), {'deprecated': True}),
            ('array', ('test:dep:array', {}), {}),
            ('comp', ('test:dep:comp', {}), {}),
        )),
        ('test:dep:str', {}, (
            ('beep', ('test:dep:str', {}), {}),
        )),
    ),
    'univs': (
        ('udep', ('test:dep:easy', {}), {}),
        ('pdep', ('test:str', {}), {'deprecated': True})
    )
}

class DeprecatedModel(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('test:dep', depmodel),
        )

class DataModelTest(s_t_utils.SynTest):

    async def test_datamodel_formname(self):
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

    async def test_datamodel_no_interface(self):
        modl = s_datamodel.Model()
        mods = (
            ('hehe', {
                'types': (
                    ('test:derp', ('int', {}), {
                        'interfaces': ('foo:bar',),
                    }),
                ),
                'forms': (
                    ('test:derp', {}, ()),
                ),
            }),
        )

        with self.raises(s_exc.NoSuchName):
            modl.addDataModels(mods)

    async def test_datamodel_dynamics(self):

        modl = s_datamodel.Model()

        with self.raises(s_exc.NoSuchType):
            modl.addType('he:he', 'ha:ha', {}, {})

        with self.raises(s_exc.NoSuchType):
            modl.addForm('he:he', {}, [])

        self.none(modl.delForm('newp'))

        self.none(modl.delType('newp'))

        with self.raises(s_exc.BadPropDef):
            modl.addType('he:he', 'int', {}, {})
            modl.addForm('he:he', {}, [
                ('asdf',),
            ])

        with self.raises(s_exc.NoSuchProp):
            modl.delFormProp('he:he', 'newp')

        with self.raises(s_exc.NoSuchForm):
            modl.delFormProp('ne:wp', 'newp')

        with self.raises(s_exc.NoSuchUniv):
            modl.delUnivProp('newp')

        modl.addIface('test:iface', {})

        modl.addType('bar', 'int', {}, {})
        modl.addType('foo:foo', 'int', {}, {'interfaces': ('test:iface',)})

        modl.addForm('foo:foo', {}, ())
        modl.addFormProp('foo:foo', 'bar', ('bar', {}), {})

        with self.raises(s_exc.CantDelType):
            modl.delType('bar')

        modl.delForm('foo:foo')

    async def test_datamodel_del_prop(self):

        modl = s_datamodel.Model()

        modl.addType('foo:bar', 'int', {}, {})
        modl.addForm('foo:bar', {}, (('x', ('int', {}), {}), ))
        modl.addUnivProp('hehe', ('int', {}), {})
        modl.addFormProp('foo:bar', 'y', ('int', {}), {})

        self.nn(modl.prop('foo:bar:x'))
        self.nn(modl.prop('foo:bar:y'))
        self.nn(modl.prop('foo:bar.hehe'))

        self.nn(modl.form('foo:bar').prop('x'))
        self.nn(modl.form('foo:bar').prop('y'))
        self.nn(modl.form('foo:bar').prop('.hehe'))

        self.len(3, modl.propsbytype['int'])

        modl.delFormProp('foo:bar', 'y')

        self.nn(modl.prop('foo:bar:x'))
        self.nn(modl.prop('foo:bar.hehe'))
        self.nn(modl.form('foo:bar').prop('x'))
        self.nn(modl.form('foo:bar').prop('.hehe'))

        self.len(2, modl.propsbytype['int'])
        self.none(modl.prop('foo:bar:y'))
        self.none(modl.form('foo:bar').prop('y'))

        modl.delUnivProp('hehe')

        self.none(modl.prop('.hehe'))
        self.none(modl.form('foo:bar').prop('.hehe'))

    async def test_datamodel_form_refs_cache(self):
        async with self.getTestCore() as core:

            refs = core.model.form('test:comp').getRefsOut()
            self.len(1, refs['prop'])

            await core.addFormProp('test:comp', '_ipv4', ('inet:ipv4', {}), {})

            refs = core.model.form('test:comp').getRefsOut()
            self.len(2, refs['prop'])

            await core.delFormProp('test:comp', '_ipv4')

            refs = core.model.form('test:comp').getRefsOut()
            self.len(1, refs['prop'])

    async def test_model_deprecation(self):
        # Note: Inverting these currently causes model loading to fail (20200831)
        mods = ['synapse.tests.utils.TestModule',
                'synapse.tests.test_datamodel.DeprecatedModel',
                ]
        conf = {'modules': mods}

        with self.getTestDir() as dirn:

            with self.getAsyncLoggerStream('synapse.lib.types') as tstream, \
                    self.getAsyncLoggerStream('synapse.datamodel') as dstream:
                core = await s_cortex.Cortex.anit(dirn, conf)

            dstream.seek(0)
            ds = dstream.read()
            self.isin('universal property .udep is using a deprecated type', ds)
            self.isin('type test:dep:easy is based on a deprecated type test:dep:easy', ds)
            tstream.seek(0)
            ts = tstream.read()
            self.isin('Array type test:dep:array is based on a deprecated type test:dep:easy', ts)

            # Using deprecated forms and props is warned to the user
            msgs = await core.stormlist('[test:dep:easy=test1 :guid=(t1,)] [:guid=(t2,)]')
            self.stormIsInWarn('The form test:dep:easy is deprecated', msgs)
            self.stormIsInWarn('The property test:dep:easy:guid is deprecated or using a deprecated type', msgs)

            # Comp type warning is logged by the server, not sent back to users
            mesg = 'type test:dep:comp field str uses a deprecated type test:dep:easy'
            with self.getAsyncLoggerStream('synapse.lib.types', mesg) as tstream:
                _ = await core.stormlist('[test:dep:easy=test2 :comp=(1, two)]')
                self.true(await tstream.wait(6))

            msgs = await core.stormlist('[test:str=tehe .pdep=beep]')
            self.stormIsInWarn('property test:str.pdep is deprecated', msgs)

            # Extended props, custom universals and tagprops can all trigger deprecation notices
            mesg = 'tag property depr is using a deprecated type test:dep:easy'
            with self.getAsyncLoggerStream('synapse.datamodel', mesg) as dstream:
                await core.addTagProp('depr', ('test:dep:easy', {}), {})
                self.true(await dstream.wait(6))

            mesg = 'universal property ._test is using a deprecated type test:dep:easy'
            with self.getAsyncLoggerStream('synapse.datamodel', mesg) as dstream:
                await core.addUnivProp('_test', ('test:dep:easy', {}), {})
                self.true(await dstream.wait(6))

            mesg = 'extended property test:str:_depr is using a deprecated type test:dep:easy'
            with self.getAsyncLoggerStream('synapse.cortex', mesg) as cstream:
                await core.addFormProp('test:str', '_depr', ('test:dep:easy', {}), {})
                self.true(await cstream.wait(6))

            # Deprecated ctor information propagates upward to types and forms
            msgs = await core.stormlist('[test:dep:str=" test" :beep=" boop "]')
            self.stormIsInWarn('form test:dep:str is deprecated or using a deprecated type', msgs)
            self.stormIsInWarn('property test:dep:str:beep is deprecated or using a deprecated type', msgs)

            await core.fini()

            # Restarting the cortex warns again for various items that it loads from the hive
            # with deprecated types in them. This is a coverage test for extended properties.
            with self.getAsyncLoggerStream('synapse.cortex', mesg) as cstream:
                async with await s_cortex.Cortex.anit(dirn, conf) as core:
                    self.true(await cstream.wait(6))

    async def test_datamodel_getmodeldefs(self):
        '''
        Make sure you can make a new model with the output of datamodel.getModelDefs
        '''
        modl = s_datamodel.Model()
        modl.addIface('test:iface', {})
        modl.addType('foo:foo', 'int', {}, {'interfaces': ('test:iface',)})
        modl.addForm('foo:foo', {}, ())
        mdef = modl.getModelDefs()
        modl2 = s_datamodel.Model()
        modl2.addDataModels(mdef)
