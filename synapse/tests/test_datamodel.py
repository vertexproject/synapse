import synapse.exc as s_exc
import synapse.datamodel as s_datamodel

import synapse.lib.module as s_module
import synapse.lib.schemas as s_schemas

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

    async def test_datamodel_basics(self):
        async with self.getTestCore() as core:
            iface = core.model.ifaces.get('phys:object')
            self.eq('object', iface['template']['phys:object'])
            core.model.addType('woot:one', 'guid', {}, {
                'display': {
                    'columns': (
                        {'type': 'newp', 'opts': {}},
                    ),
                },
            })
            with self.raises(s_exc.BadFormDef):
                core.model.addForm('woot:one', {}, ())

            core.model.addType('woot:two', 'guid', {}, {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'hehe'}},
                    ),
                },
            })
            with self.raises(s_exc.BadFormDef):
                core.model.addForm('woot:two', {}, ())

            with self.raises(s_exc.NoSuchForm):
                core.model.reqForm('newp:newp')

            with self.raises(s_exc.NoSuchProp):
                core.model.reqForm('inet:asn').reqProp('newp')

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

        with self.raises(s_exc.NoSuchForm):
            modl.addFormProp('foo:newp', 'bar', ('bar', {}), {})

        with self.raises(s_exc.CantDelType):
            modl.delType('bar')

        with self.raises(s_exc.CantDelForm):
            modl.delForm('foo:foo')

        modl.delFormProp('foo:foo', 'bar')
        modl.delForm('foo:foo')

        modl.addIface('depr:iface', {'deprecated': True})

        with self.getAsyncLoggerStream('synapse.datamodel') as dstream:
            modl.addType('foo:bar', 'int', {}, {'interfaces': ('depr:iface',)})
            modl.addForm('foo:bar', {}, ())

        dstream.seek(0)
        self.isin('Form foo:bar depends on deprecated interface depr:iface', dstream.read())

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

            self.len(1, [prop for prop in core.model.getPropsByType('time') if prop.full == 'it:exec:url:time'])

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

            dstream.expect('universal property .udep is using a deprecated type')
            dstream.expect('type test:dep:easy is based on a deprecated type test:dep:easy')
            dstream.noexpect('type test:dep:comp field str uses a deprecated type test:dep:easy')
            tstream.expect('Array type test:dep:array is based on a deprecated type test:dep:easy')

            # Using deprecated forms and props is warned to the user
            msgs = await core.stormlist('[test:dep:easy=test1 :guid=(t1,)] [:guid=(t2,)]')
            self.stormIsInWarn('The form test:dep:easy is deprecated', msgs)
            self.stormIsInWarn('The property test:dep:easy:guid is deprecated or using a deprecated type', msgs)

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

    async def test_model_comp_readonly_props(self):
        async with self.getTestCore() as core:
            q = '''
            syn:type:subof=comp $opts=:opts
            -> syn:form:type $valu=$node.value()
            for ($name, $thing) in $opts.fields {
                $v=`{$valu}:{$name}`  syn:prop=$v
            }
            +syn:prop
            -:ro=1
            '''
            nodes = await core.nodes(q)
            mesg = f'Comp forms with secondary properties that are not read-only ' \
                   f'are present in the model: {[n.ndef[1] for n in nodes]}'
            self.len(0, nodes, mesg)

    async def test_model_invalid_comp_types(self):

        mutmesg = 'Comp types with mutable fields (_bad:comp:hehe) are deprecated and will be removed in 3.0.0.'

        # Comp type with a direct data field
        badmodel = ('badmodel', {
            'types': (
                ('_bad:comp', ('comp', {'fields': (
                    ('hehe', 'data'),
                    ('haha', 'int'))
                }), {'doc': 'A fake comp type with a data field.'}),
            ),
            'forms': (
                ('_bad:comp', {}, (
                    ('hehe', ('data', {}), {}),
                    ('haha', ('int', {}), {}),
                )),
            ),
        })

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addDataModels([badmodel])
        stream.expect(mutmesg)

        # Comp type with an indirect data field (and out of order definitions)
        badmodel = ('badmodel', {
            'types': (
                ('_bad:comp', ('comp', {'fields': (
                    ('hehe', 'bad:data'),
                    ('haha', 'int'))
                }), {'doc': 'A fake comp type with a data field.'}),
                ('bad:data', ('data', {}), {}),
            ),
            'forms': (
                ('_bad:comp', {}, (
                    ('hehe', ('bad:data', {}), {}),
                    ('haha', ('int', {}), {}),
                )),
            ),
        })

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addDataModels([badmodel])
        stream.expect(mutmesg)

        # Comp type with double indirect data field
        badmodel = ('badmodel', {
            'types': (
                ('bad:data00', ('data', {}), {}),
                ('bad:data01', ('bad:data00', {}), {}),
                ('_bad:comp', ('comp', {'fields': (
                    ('hehe', 'bad:data01'),
                    ('haha', 'int'))
                }), {'doc': 'A fake comp type with a data field.'}),
            ),
            'forms': (
                ('_bad:comp', {}, (
                    ('hehe', ('bad:data01', {}), {}),
                    ('haha', ('int', {}), {}),
                )),
            ),
        })

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addDataModels([badmodel])
        stream.expect(mutmesg)

        # API direct
        typeopts = {
            'fields': (
                ('hehe', 'data'),
                ('haha', 'int'),
            )
        }

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addType('_bad:comp', 'comp', typeopts, {})
        stream.expect(mutmesg)

        # Non-existent types
        typeopts = {
            'fields': (
                ('hehe', 'newp'),
                ('haha', 'int'),
            )
        }

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addType('_bad:comp', 'comp', typeopts, {})
        stream.expect('The _bad:comp field hehe is declared as a type (newp) that does not exist.')

        # deprecated types
        badmodel = ('badmodel', {
            'types': (
                ('depr:type', ('int', {}), {'deprecated': True}),
                ('_bad:comp', ('comp', {'fields': (
                    ('hehe', 'depr:type'),
                    ('haha', 'int'))
                }), {'doc': 'A fake comp type with a deprecated field.'}),
            ),
            'forms': (
                ('_bad:comp', {}, (
                    ('hehe', ('depr:type', {}), {}),
                    ('haha', ('int', {}), {}),
                )),
            ),
        })

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addDataModels([badmodel])
        stream.expect('The type _bad:comp field hehe uses a deprecated type depr:type.')

        # Comp type not extended does not gen mutable warning
        badmodel = ('badmodel', {
            'types': (
                ('bad:comp', ('comp', {'fields': (
                    ('hehe', 'data'),
                    ('haha', 'int'))
                }), {'doc': 'A fake comp type with a data field.'}),
            ),
            'forms': (
                ('bad:comp', {}, (
                    ('hehe', ('data', {}), {}),
                    ('haha', ('int', {}), {}),
                )),
            ),
        })

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addDataModels([badmodel])
        stream.noexpect('Comp types with mutable fields')

        # Comp type not extended does not gen deprecated warning
        badmodel = ('badmodel', {
            'types': (
                ('depr:type', ('int', {}), {'deprecated': True}),
                ('bad:comp', ('comp', {'fields': (
                    ('hehe', 'depr:type'),
                    ('haha', 'int'))
                }), {'doc': 'A fake comp type with a deprecated field.'}),
            ),
            'forms': (
                ('bad:comp', {}, (
                    ('hehe', ('depr:type', {}), {}),
                    ('haha', ('int', {}), {}),
                )),
            ),
        })

        with self.getLoggerStream('synapse.datamodel') as stream:
            s_datamodel.Model().addDataModels([badmodel])
        stream.noexpect('uses a deprecated type')

    async def test_datamodel_edges(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchForm):
                core.model.addEdge(('hehe', 'woot', 'newp'), {})

            with self.raises(s_exc.NoSuchForm):
                core.model.addEdge(('inet:ipv4', 'woot', 'newp'), {})

            with self.raises(s_exc.BadArg):
                core.model.addEdge(('inet:ipv4', 10, 'inet:ipv4'), {})

            with self.raises(s_exc.BadArg):
                core.model.addEdge(('meta:rule', 'matches', None), {})

            model = await core.getModelDict()
            self.isin(('meta:rule', 'matches', None), [e[0] for e in model['edges']])

            model = (await core.getModelDefs())[0][1]
            self.isin(('meta:rule', 'matches', None), [e[0] for e in model['edges']])

            self.nn(core.model.edge(('meta:rule', 'matches', None)))

            core.model.delEdge(('meta:rule', 'matches', None))
            self.none(core.model.edge(('meta:rule', 'matches', None)))

            core.model.delEdge(('meta:rule', 'matches', None))

    async def test_datamodel_locked_subs(self):

        conf = {'modules': [('synapse.tests.utils.DeprModule', {})]}
        async with self.getTestCore(conf=conf) as core:

            msgs = await core.stormlist('[ test:deprsub=bar :range=(1, 5) ]')
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('[ test:deprsub2=(foo, (2, 6)) ]')
            self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes('test:deprsub=bar')
            self.eq(1, nodes[0].get('range:min'))
            self.eq(5, nodes[0].get('range:max'))

            nodes = await core.nodes('test:deprsub2=(foo, (2, 6))')
            self.eq(2, nodes[0].get('range:min'))
            self.eq(6, nodes[0].get('range:max'))

            await core.setDeprLock('test:deprsub:range:min', True)
            nodes = await core.nodes('[ test:deprsub=foo :range=(1, 5) ]')
            self.none(nodes[0].get('range:min'))
            self.eq(5, nodes[0].get('range:max'))

            await core.nodes('test:deprsub2 | delnode')
            await core.setDeprLock('test:deprsub2:range:max', True)
            nodes = await core.nodes('[ test:deprsub2=(foo, (2, 6)) ]')
            self.none(nodes[0].get('range:max'))
            self.eq(2, nodes[0].get('range:min'))

    def test_datamodel_schema_basetypes(self):
        # N.B. This test is to keep synapse.lib.schemas.datamodel_basetypes const
        # in sync with the default s_datamodel.Datamodel().types
        basetypes = list(s_datamodel.Model().types)
        self.eq(s_schemas.datamodel_basetypes, basetypes)
