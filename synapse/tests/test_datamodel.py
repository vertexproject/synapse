import copy
import synapse.exc as s_exc
import synapse.datamodel as s_datamodel

import synapse.lib.schemas as s_schemas

import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils

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

            with self.raises(s_exc.NoSuchForm) as cm:
                core.model.reqForm('biz:prodtype')
            self.isin('Did you mean biz:product:type:taxonomy?', cm.exception.get('mesg'))

            with self.raises(s_exc.NoSuchForm) as cm:
                core.model.reqForm('biz:prodtype')
            self.isin('Did you mean biz:product:type:taxonomy?', cm.exception.get('mesg'))

            with self.raises(s_exc.NoSuchForm) as cm:
                core.model.reqFormsByLook('biz:prodtype')
            self.isin('Did you mean biz:product:type:taxonomy?', cm.exception.get('mesg'))

            with self.raises(s_exc.NoSuchProp) as cm:
                core.model.reqProp('inet:dns:query:name:ipv4')
            self.isin('Did you mean inet:dns:query:name:ip?', cm.exception.get('mesg'))

            with self.raises(s_exc.NoSuchProp) as cm:
                core.model.reqPropsByLook('inet:dns:query:name:ipv4')
            self.isin('Did you mean inet:dns:query:name:ip?', cm.exception.get('mesg'))

            form = core.model.reqForm('inet:dns:query')
            with self.raises(s_exc.NoSuchProp) as cm:
                form.reqProp('name:ipv4')
            self.isin('Did you mean inet:dns:query:name:ip?', cm.exception.get('mesg'))

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
                        'interfaces': (('foo:bar', {}),),
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

        modl.addIface('test:iface', {})

        modl.addType('bar', 'int', {}, {})
        modl.addType('foo:foo', 'int', {}, {'interfaces': (('test:iface', {}),)})

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
            modl.addType('foo:bar', 'int', {}, {'interfaces': (('depr:iface', {}),)})
            modl.addForm('foo:bar', {}, ())

        dstream.seek(0)
        self.isin('Form foo:bar depends on deprecated interface depr:iface', dstream.read())

    async def test_datamodel_del_prop(self):

        modl = s_datamodel.Model()

        modl.addType('foo:bar', 'int', {}, {})
        modl.addForm('foo:bar', {}, (('x', ('int', {}), {}), ))
        modl.addFormProp('foo:bar', 'y', ('int', {}), {})

        self.nn(modl.prop('foo:bar:x'))
        self.nn(modl.prop('foo:bar:y'))

        self.nn(modl.form('foo:bar').prop('x'))
        self.nn(modl.form('foo:bar').prop('y'))

        self.len(2, modl.propsbytype['int'])

        modl.delFormProp('foo:bar', 'y')

        self.nn(modl.prop('foo:bar:x'))
        self.nn(modl.form('foo:bar').prop('x'))

        self.len(1, modl.propsbytype['int'])
        self.none(modl.prop('foo:bar:y'))
        self.none(modl.form('foo:bar').prop('y'))

    async def test_datamodel_form_refs_cache(self):
        async with self.getTestCore() as core:

            refs = core.model.form('test:comp').getRefsOut()
            self.len(1, refs['prop'])

            await core.addFormProp('test:comp', '_ip', ('inet:ip', {}), {})

            refs = core.model.form('test:comp').getRefsOut()
            self.len(2, refs['prop'])

            await core.delFormProp('test:comp', '_ip')

            refs = core.model.form('test:comp').getRefsOut()
            self.len(1, refs['prop'])

            self.len(1, [prop for prop in core.model.getPropsByType('time') if prop.full == 'it:exec:url:time'])

    async def test_model_deprecation(self):

        with self.getTestDir() as dirn:

            with self.getAsyncLoggerStream('synapse.lib.types') as tstream, \
                    self.getAsyncLoggerStream('synapse.datamodel') as dstream:
                core = await s_cortex.Cortex.anit(dirn)
                await core._addDataModels(s_t_utils.testmodel + s_t_utils.deprmodel)

            dstream.seek(0)
            ds = dstream.read()
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

            msgs = await core.stormlist('[test:depriface=tehe :pdep=beep]')
            self.stormIsInWarn('property test:depriface:pdep is deprecated', msgs)

            # Extended props and tagprops can all trigger deprecation notices
            mesg = 'tag property depr is using a deprecated type test:dep:easy'
            with self.getAsyncLoggerStream('synapse.datamodel', mesg) as dstream:
                await core.addTagProp('depr', ('test:dep:easy', {}), {})
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

            # Restarting the cortex warns again for various items that it loads
            # with deprecated types in them. This is a coverage test for extended properties.
            with self.getAsyncLoggerStream('synapse.cortex', mesg) as cstream:
                async with await s_cortex.Cortex.anit(dirn) as core:
                    await core._addDataModels(s_t_utils.testmodel + s_t_utils.deprmodel)
                    await core._loadExtModel()
                    self.true(await cstream.wait(6))

    async def test_datamodel_getmodeldefs(self):
        '''
        Make sure you can make a new model with the output of datamodel.getModelDefs
        '''
        modl = s_datamodel.Model()
        modl.addIface('test:iface', {})
        modl.addType('foo:foo', 'int', {}, {'interfaces': (('test:iface', {}),)})
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

    async def test_datamodel_edges(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchForm):
                core.model.addEdge(('hehe', 'woot', 'newp'), {})

            with self.raises(s_exc.NoSuchForm):
                core.model.addEdge(('inet:ip', 'woot', 'newp'), {})

            with self.raises(s_exc.BadArg):
                core.model.addEdge(('inet:ip', 10, 'inet:ip'), {})

            with self.raises(s_exc.BadArg):
                core.model.addEdge(('meta:rule', 'matches', None), {})

            core.model.addEdge(('inet:fqdn', 'zip', 'phys:object'), {})
            edges = core.model.edgesbyn2.get('transport:air:craft')
            self.true(core.model.edgeIsValid('inet:fqdn', 'zip', 'transport:air:craft'))
            self.isin(('inet:fqdn', 'zip', 'phys:object'), [e.edgetype for e in edges])

            core.model.addEdge(('phys:object', 'zop', 'inet:fqdn'), {})
            edges = core.model.edgesbyn1.get('transport:air:craft')
            self.isin(('phys:object', 'zop', 'inet:fqdn'), [e.edgetype for e in edges])

            core.model.delEdge(('inet:fqdn', 'zip', 'phys:object'))
            edges = core.model.edgesbyn2.get('transport:air:craft')
            self.false(core.model.edgeIsValid('inet:fqdn', 'zip', 'transport:air:craft'))
            self.notin(('inet:fqdn', 'zip', 'phys:object'), [e.edgetype for e in edges])

            core.model.delEdge(('phys:object', 'zop', 'inet:fqdn'))
            edges = core.model.edgesbyn1.get('transport:air:craft')
            self.notin(('phys:object', 'zop', 'inet:fqdn'), [e.edgetype for e in edges])

            model = await core.getModelDict()
            self.isin(('meta:rule', 'matches', None), [e[0] for e in model['edges']])

            model = (await core.getModelDefs())[0][1]
            self.isin(('meta:rule', 'matches', None), [e[0] for e in model['edges']])

            self.nn(core.model.edge(('meta:rule', 'matches', None)))

            core.model.delEdge(('meta:rule', 'matches', None))
            self.none(core.model.edge(('meta:rule', 'matches', None)))

            core.model.delEdge(('meta:rule', 'matches', None))

    async def test_datamodel_locked_subs(self):

        async with self.getTestCore() as core:

            await core._addDataModels(s_t_utils.deprmodel)

            nodes = await core.nodes('[ test:deprsub=bar :range=(1, 5) ]')
            self.eq(1, nodes[0].get('range:min'))
            self.eq(5, nodes[0].get('range:max'))

            nodes = await core.nodes('[ test:deprsub2=(foo, (2, 6)) ]')
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
