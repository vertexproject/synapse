import synapse.exc as s_exc
import synapse.datamodel as s_datamodel

import synapse.lib.json as s_json
import synapse.lib.schemas as s_schemas

import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils

class DataModelTest(s_t_utils.SynTest):

    async def test_datamodel_basics(self):
        async with self.getTestCore() as core:
            iface = core.model.ifaces.get('phys:tangible')
            self.eq('object', iface['template']['title'])
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

            core.model.addType('woot:array', 'array', {'type': 'str'}, {})
            with self.raises(s_exc.BadFormDef):
                core.model.addForm('woot:array', {}, ())

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

            with self.raises(s_exc.NoSuchType) as cm:
                core.model.addFormProp('test:str', 'bar', ('newp', {}), {})
            self.isin('No type named newp while declaring prop test:str:bar.', cm.exception.get('mesg'))

            with self.raises(s_exc.BadTypeDef) as cm:
                core.model.addType('_foo:type', 'int', {'foo': 'bar'}, {})
            self.isin('Type option foo is not valid', cm.exception.get('mesg'))

            with self.raises(s_exc.NoSuchType):
                core.model.reqType('newp:newp')

    async def test_datamodel_formname(self):
        modl = s_datamodel.getBaseModel()
        mods = (
            {
                'types': (
                    ('derp', ('int', {}), {}),
                ),
                'forms': (
                    ('derp', {}, ()),
                ),
            },
        )

        with self.raises(s_exc.BadFormDef):
            modl.addModelDefs(mods)

    async def test_datamodel_virtstor(self):
        modl = s_datamodel.getBaseModel()
        modl.addType('test:virt', 'int', {}, {})
        modl.types['test:virt'].virtstor['fake'] = lambda: None
        with self.raises(s_exc.BadFormDef):
            modl.addForm('test:virt', {}, ())

    async def test_datamodel_no_interface(self):
        modl = s_datamodel.getBaseModel()
        mods = (
            {
                'types': (
                    ('test:derp', ('int', {}), {
                        'interfaces': (('foo:bar', {}),),
                    }),
                ),
                'forms': (
                    ('test:derp', {}, ()),
                ),
            },
        )

        with self.raises(s_exc.NoSuchIface):
            modl.addModelDefs(mods)

    async def test_datamodel_dynamics(self):

        modl = s_datamodel.getBaseModel()

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
            modl.addForm('he:he', {}, [])
            modl.delFormProp('he:he', 'newp')

        with self.raises(s_exc.NoSuchForm):
            modl.delFormProp('ne:wp', 'newp')

        modl.addIface('test:iface', {})

        modl.addType('test:form', 'guid', {}, {})
        modl.addForm('test:form', {}, ())

        with self.raises(s_exc.DupName):
            modl.addIface('test:iface', {})

        with self.raises(s_exc.DupName):
            modl.addIface('test:form', {})

        with self.raises(s_exc.DupName):
            modl.addForm('test:iface', {}, ())

        with self.raises(s_exc.DupName):
            modl.addForm('test:form', {}, ())

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

        with self.getLoggerStream('synapse.datamodel') as stream:
            modl.addType('foo:bar', 'int', {}, {'interfaces': (('depr:iface', {}),)})
            modl.addForm('foo:bar', {}, ())

        self.isin('Form foo:bar depends on deprecated interface depr:iface', stream.getvalue())

    async def test_datamodel_del_prop(self):

        modl = s_datamodel.getBaseModel()

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
            ndeflen = len(refs['ndef'])

            await core.addFormProp('test:comp', '_ip', ('inet:ip', {}), {})

            refs = core.model.form('test:comp').getRefsOut()
            self.eq(ndeflen + 1, len(refs['ndef']))

            await core.delFormProp('test:comp', '_ip')

            refs = core.model.form('test:comp').getRefsOut()
            self.eq(ndeflen, len(refs['ndef']))

            self.len(1, [prop for prop in core.model.getPropsByType('time') if prop.full == 'it:exec:fetch:time'])

    async def test_model_deprecation(self):

        with self.getTestDir() as dirn:

            with self.getLoggerStream('synapse.lib.types') as tstream, \
                 self.getLoggerStream('synapse.datamodel') as dstream:

                core = await s_cortex.Cortex.anit(dirn)
                await core._addModelDefs(s_t_utils.testmodel + s_t_utils.deprmodel)

                await dstream.expect('type test:dep:easy is based on a deprecated type test:dep:easy')
                await tstream.expect('Array type test:dep:array is based on a deprecated type test:dep:easy')
                self.notin('type test:dep:comp field str uses a deprecated type test:dep:easy', dstream.getvalue())

                # Using deprecated forms and props is warned to the user
                msgs = await core.stormlist('[test:dep:easy=test1 :guid=(t1,)] [:guid=(t2,)]')
                self.stormIsInWarn('The form test:dep:easy is deprecated', msgs)
                self.stormIsInWarn('The property test:dep:easy:guid is deprecated or using a deprecated type', msgs)

                msgs = await core.stormlist('[test:depriface=tehe :pdep=beep]')
                self.stormIsInWarn('property test:depriface:pdep is deprecated', msgs)

                # Extended props and tagprops can all trigger deprecation notices
                mesg = 'tag property depr is using a deprecated type test:dep:easy'
                await core.addTagProp('depr', ('test:dep:easy', {}), {})
                await dstream.expect('tag property depr is using a deprecated type test:dep:easy', timeout=6)

            # TODO: how do we want to warn for polyprops which allow deprecated types?
            # mesg = 'extended property test:str:_depr is using a deprecated type test:dep:easy'
            # with self.getLoggerStream('synapse.cortex') as cstream:
            #    await core.addFormProp('test:str', '_depr', ('test:dep:easy', {}), {})
            #    await cstream.expect(mesg, timeout=6)

            # Deprecated ctor information propagates upward to types and forms
            msgs = await core.stormlist('[test:dep:str=" test" :beep=" boop "]')
            self.stormIsInWarn('form test:dep:str is deprecated or using a deprecated type', msgs)
            # self.stormIsInWarn('property test:dep:str:beep is deprecated or using a deprecated type', msgs)

            await core.fini()

            # Restarting the cortex warns again for various items that it loads
            # with deprecated types in them. This is a coverage test for extended properties.
            with self.getLoggerStream('synapse.cortex', mesg) as cstream:
                async with await s_cortex.Cortex.anit(dirn) as core:
                    await core._addModelDefs(s_t_utils.testmodel + s_t_utils.deprmodel)
                    await core._loadExtModel()
                    # await cstream.expect(mesg, timeout=6)

    async def test_datamodel_getmodeldefs(self):
        '''
        Make sure you can make a new model with the output of datamodel.getModelDef
        '''
        modl = s_datamodel.getBaseModel()
        modl.addIface('test:iface', {})
        modl.addType('foo:foo', 'int', {}, {'interfaces': (('test:iface', {}),)})
        modl.addForm('foo:foo', {}, ())
        mdef = modl.getModelDef()
        modl2 = s_datamodel.getBaseModel()
        modl2.addModelDefs([mdef])

    async def test_model_comp_readonly_props(self):
        async with self.getTestCore() as core:
            q = '''
            syn:type:subof=comp $opts=:opts
            -> syn:form:type $valu=$node.value()
            for ($name, $thing) in $opts.fields {
                $v=`{$valu}:{$name}`  syn:prop=$v
            }
            +syn:prop
            -:computed=1
            '''
            nodes = await core.nodes(q)
            mesg = f'Comp forms with secondary properties that are not computed ' \
                   f'are present in the model: {[n.ndef[1] for n in nodes]}'
            self.len(0, nodes, mesg)

    async def test_model_invalid_comp_types(self):

        mutmesg = 'Comp types with mutable fields (_bad:comp:hehe) are not allowed'

        # Comp type with a direct data field
        badmodel = {
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
        }

        with self.raises(s_exc.BadTypeDef) as cm:
            s_datamodel.getBaseModel().addModelDefs([badmodel])
        self.isin(mutmesg, cm.exception.get('mesg'))

        # Comp type with an indirect data field (and out of order definitions)
        badmodel = {
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
        }

        with self.raises(s_exc.BadTypeDef) as cm:
            s_datamodel.getBaseModel().addModelDefs([badmodel])
        self.isin(mutmesg, cm.exception.get('mesg'))

        # Comp type with double indirect data field
        badmodel = {
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
        }

        with self.raises(s_exc.BadTypeDef) as cm:
            s_datamodel.getBaseModel().addModelDefs([badmodel])
        self.isin(mutmesg, cm.exception.get('mesg'))

        # API direct
        typeopts = {
            'fields': (
                ('hehe', 'data'),
                ('haha', 'int'),
            )
        }

        with self.raises(s_exc.BadTypeDef) as cm:
            s_datamodel.getBaseModel().addType('_bad:comp', 'comp', typeopts, {})
        self.isin(mutmesg, cm.exception.get('mesg'))

        # Non-existent types
        typeopts = {
            'fields': (
                ('hehe', 'newp'),
                ('haha', 'int'),
            )
        }

        with self.raises(s_exc.BadTypeDef) as cm:
            s_datamodel.getBaseModel().addType('_bad:comp', 'comp', typeopts, {})
        self.isin('Type newp is not present in datamodel.', cm.exception.get('mesg'))

        # deprecated types
        badmodel = {
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
        }

        with self.getLoggerStream('synapse.lib.types') as stream:
            s_datamodel.getBaseModel().addModelDefs([badmodel])
            await stream.expect('The type _bad:comp field hehe uses a deprecated type depr:type', timeout=1)

        # Comp type not extended does not gen deprecated warning
        badmodel = {
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
        }

        with self.getLoggerStream('synapse.lib.types') as stream:
            s_datamodel.getBaseModel().addModelDefs([badmodel])
        self.notin('uses a deprecated type', stream.getvalue())

    async def test_datamodel_edges(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchForm):
                core.model.addEdge(('hehe', 'woot', 'newp'), {})

            with self.raises(s_exc.NoSuchForm):
                core.model.addEdge(('inet:ip', 'woot', 'newp'), {})

            with self.raises(s_exc.BadArg):
                core.model.addEdge(('inet:ip', 10, 'inet:ip'), {})

            with self.raises(s_exc.BadArg):
                core.model.addEdge(('test:interface', 'matches', None), {})

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
            self.isin('created', [m[0] for m in model['metas']])
            self.isin('updated', [m[0] for m in model['metas']])
            self.isin(('test:interface', 'matches', None), [e[0] for e in model['edges']])

            # Verify interface template variables are resolved in getModelDict
            ifaces = model['interfaces']

            obsinfo = ifaces.get('meta:observable')
            obsprops = {p[0]: p for p in obsinfo['props']}
            self.eq(obsprops['seen'][2]['doc'], 'The node was observed during the time interval.')

            locinfo = ifaces.get('geo:locatable')
            locprops = {p[0]: p for p in locinfo['props']}
            self.isin('The place where the item was located.', locprops[''][2]['doc'])
            self.notin('{title}', locprops[''][2]['doc'])
            self.notin('{happened}', locprops[''][2]['doc'])

            taxinfo = ifaces.get('meta:taxonomy')
            taxprops = {p[0]: p for p in taxinfo['props']}
            self.eq(taxprops['parent'][1][0], 'meta:taxonomy')

            model = await core.getModelDef()
            self.isin(('test:interface', 'matches', None), [e[0] for e in model['edges']])

            self.nn(core.model.edge(('test:interface', 'matches', None)))

            core.model.delEdge(('test:interface', 'matches', None))
            self.none(core.model.edge(('test:interface', 'matches', None)))

            core.model.delEdge(('test:interface', 'matches', None))

    async def test_datamodel_locked_subs(self):

        async with self.getTestCore() as core:

            await core._addModelDefs(s_t_utils.deprmodel)

            nodes = await core.nodes('[ test:deprsub=bar :range=(1, 5) ]')
            self.propeq(nodes[0], 'range:min', 1)
            self.propeq(nodes[0], 'range:max', 5)

            nodes = await core.nodes('[ test:deprsub2=(foo, (2, 6)) ]')
            self.propeq(nodes[0], 'range:min', 2)
            self.propeq(nodes[0], 'range:max', 6)

            await core.setDeprLock('test:deprsub:range:min', True)
            nodes = await core.nodes('[ test:deprsub=foo :range=(1, 5) ]')
            self.none(nodes[0].get('range:min'))
            self.propeq(nodes[0], 'range:max', 5)

            await core.nodes('test:deprsub2 | delnode')
            await core.setDeprLock('test:deprsub2:range:max', True)
            nodes = await core.nodes('[ test:deprsub2=(foo, (2, 6)) ]')
            self.none(nodes[0].get('range:max'))
            self.propeq(nodes[0], 'range:min', 2)

            await core.nodes('[ test:str=poly :poly={[ test:dep:easy=depr ]} ]')
            await core.setDeprLock('test:dep:easy', True)

            with self.raises(s_exc.IsDeprLocked):
                await core.nodes('[ test:str=newp :poly={ test:dep:easy=depr } ]')

            with self.raises(s_exc.IsDeprLocked):
                await core.nodes('$n={ test:str=poly } [ test:str=newp :poly=$n.props.poly ]')

    def test_datamodel_schema_basetypes(self):
        # N.B. This test is to keep synapse.lib.schemas.datamodel_basetypes const
        # in sync with the default s_datamodel.Datamodel().types
        basetypes = list(s_datamodel.getBaseModel().types)
        self.sorteq(s_schemas.datamodel_basetypes, basetypes)

    async def test_datamodel_virts(self):

        async with self.getTestCore() as core:

            vdef = ('ip', ('inet:ip', {}), {'doc': 'The IP address of the server.', 'computed': True})
            self.eq(core.model.form('inet:server').info['virts'][0], vdef)

            vdef = ('ip', ('inet:ip', {}), {'doc': 'The IP address contained in the socket address URL.', 'computed': True})
            self.eq(core.model.type('inet:sockaddr').info['virts'][0], vdef)

            vdef = ('precision', ('timeprecision', {}), {'doc': 'The precision for display and rounding the time.'})
            self.eq(core.model.prop('it:exec:proc:create:time').info['virts'][0], vdef)

            # poly value virt type has `hidden` set in `display`
            self.eq(core.model.type('poly').info['virts'][1][0], 'value')
            self.eq(core.model.type('poly').info['virts'][1][2]['display'], {'hidden': True})

            with self.raises(s_exc.NoSuchType):
                vdef = ('newp', ('newp', {}), {})
                core.model.addFormProp('test:str', 'bar', ('str', {}), {'virts': (vdef, )})

    async def test_datamodel_form_inheritance(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:

                await core.addTagProp('score', ('int', {}), {})
                await core.addTagProp('inhstr', ('test:inhstr2', {}), {})

                await core.nodes('[ test:inhstr=parent :name=p1]')
                await core.nodes('[ test:inhstr2=foo :name=foo :child1=subv +#foo=2020 +#foo:score=10]')
                await core.nodes('[ test:inhstr3=bar :name=bar :child1=subv :child2=specific]')

                await core.nodes('[ test:str=tagprop +#bar:inhstr=bar ]')

                self.len(3, await core.nodes('test:inhstr'))
                self.len(1, await core.nodes('test:inhstr:name=bar'))
                self.len(2, await core.nodes('test:inhstr2:child1=subv'))
                self.len(1, await core.nodes('test:inhstr3'))
                self.len(1, await core.nodes('test:inhstr3:child2=specific'))
                self.len(1, await core.nodes('test:inhstr#foo'))
                self.len(1, await core.nodes('test:inhstr#foo@=2020'))
                self.len(1, await core.nodes('test:inhstr#(foo).min>2019'))
                self.len(1, await core.nodes('test:inhstr#foo:score'))
                self.len(1, await core.nodes('test:inhstr#foo:score=10'))

                await core.nodes('[ test:str=prop :inhstr=foo ]')
                nodes = await core.nodes('test:str=prop -> *')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:inhstr2', 'foo'))

                nodes = await core.nodes('test:str=prop :inhstr -> *')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:inhstr2', 'foo'))

                nodes = await core.nodes('test:str=prop -> test:inhstr')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:inhstr2', 'foo'))

                nodes = await core.nodes('test:str=prop -> test:inhstr2')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:inhstr2', 'foo'))

                nodes = await core.nodes('test:str=prop :inhstr -> test:inhstr')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:inhstr2', 'foo'))

                nodes = await core.nodes('test:inhstr3 <- *')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:str', 'tagprop'))

                await core.nodes('[ test:str=prop2 :inhstrarry=(foo, bar) ]')
                nodes = await core.nodes('test:str=prop2 -> test:inhstr')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('test:inhstr3', 'bar'))
                self.eq(nodes[1].ndef, ('test:inhstr2', 'foo'))

                nodes = await core.nodes('test:str=prop2 -> test:inhstr3')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:inhstr3', 'bar'))

                await core.nodes("$lib.model.ext.addForm(_test:inhstr5, test:inhstr3, ({}), ({}))")
                await core.nodes("$lib.model.ext.addForm(_test:inhstr4, _test:inhstr5, ({}), ({}))")
                await core.nodes("$lib.model.ext.addFormProp(test:inhstr3, _xtra, ('test:str', ({})), ({'doc': 'inherited extprop'}))")

                self.len(1, await core.nodes('[ _test:inhstr4=ext :name=bar :_xtra=here ]'))
                self.len(1, await core.nodes('[ _test:inhstr5=ext2 :name=bar :_xtra=here ]'))

                nodes = await core.nodes('test:inhstr:name=bar')
                self.len(3, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'ext'))
                self.eq(nodes[1].ndef, ('_test:inhstr5', 'ext2'))
                self.eq(nodes[2].ndef, ('test:inhstr3', 'bar'))

                nodes = await core.nodes('test:inhstr:name=bar +_test:inhstr5')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'ext'))
                self.eq(nodes[1].ndef, ('_test:inhstr5', 'ext2'))

                nodes = await core.nodes('test:inhstr:name=bar +_test:inhstr5:name')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'ext'))
                self.eq(nodes[1].ndef, ('_test:inhstr5', 'ext2'))

                nodes = await core.nodes('test:inhstr:name=bar +_test:inhstr5:name=bar')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'ext'))
                self.eq(nodes[1].ndef, ('_test:inhstr5', 'ext2'))

                await core.nodes('[ test:str=extprop :inhstr=ext ]')
                nodes = await core.nodes('test:str=extprop -> *')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'ext'))

                await core.nodes('[ test:str=extprop2 :inhstr=ext2 ]')
                nodes = await core.nodes('test:str:inhstr::name=bar')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('test:str', 'extprop'))
                self.eq(nodes[1].ndef, ('test:str', 'extprop2'))

                # Pivot prop lifts can use props on child forms
                nodes = await core.nodes('test:str:inhstr::_xtra=here')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('test:str', 'extprop'))
                self.eq(nodes[1].ndef, ('test:str', 'extprop2'))

                await core.nodes('[test:str=here :hehe=foo]')
                nodes = await core.nodes('test:str:inhstr::_xtra::hehe=foo')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('test:str', 'extprop'))
                self.eq(nodes[1].ndef, ('test:str', 'extprop2'))

                await core.nodes("$lib.model.ext.addForm(_test:xtra, test:inhstr, ({}), ({}))")
                await core.nodes("$lib.model.ext.addForm(_test:xtra2, test:inhstr, ({}), ({}))")
                await core.nodes("$lib.model.ext.addFormProp(_test:xtra, _xtra, ('test:str', ({})), ({}))")
                await core.nodes("$lib.model.ext.addFormProp(_test:xtra2, _xtra, ('test:int', ({})), ({}))")

                await core.nodes('[ _test:xtra=xtra :_xtra=here ]')
                await core.nodes('[ _test:xtra2=xtra2 :_xtra=3 ]')
                await core.nodes('[ test:str=extprop3 :inhstr=xtra ]')
                await core.nodes('[ test:str=extprop4 :inhstr=xtra2 ]')
                await core.nodes('[ test:str2=extprop5 :inhstr=xtra ]')

                # Pivot prop lifts when child props have different types work
                nodes = await core.nodes('test:str:inhstr::_xtra=here')
                self.len(4, nodes)
                self.eq(nodes[0].ndef, ('test:str2', 'extprop5'))
                self.eq(nodes[1].ndef, ('test:str', 'extprop'))
                self.eq(nodes[2].ndef, ('test:str', 'extprop2'))
                self.eq(nodes[3].ndef, ('test:str', 'extprop3'))

                nodes = await core.nodes('test:str:inhstr::_xtra=3')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:str', 'extprop4'))

                nodes = await core.nodes('test:str:inhstr::_xtra::hehe=foo')
                self.len(4, nodes)
                self.eq(nodes[0].ndef, ('test:str2', 'extprop5'))
                self.eq(nodes[1].ndef, ('test:str', 'extprop'))
                self.eq(nodes[2].ndef, ('test:str', 'extprop2'))
                self.eq(nodes[3].ndef, ('test:str', 'extprop3'))

                await core.nodes('_test:xtra=xtra | delnode --force')
                nodes = await core.nodes('test:str:inhstr::_xtra::hehe=foo')
                self.len(2, nodes)
                self.eq(nodes[0].ndef, ('test:str', 'extprop'))
                self.eq(nodes[1].ndef, ('test:str', 'extprop2'))

                # Cannot add a prop to a parent form which already exists on a child
                with self.raises(s_exc.DupPropName):
                    await core.nodes("$lib.model.ext.addFormProp(test:inhstr, _xtra, ('str', ({})), ({}))")

                # Props on child forms of the target are checked during form -> form pivots
                await core.nodes("$lib.model.ext.addFormProp(_test:inhstr5, _refs, ('test:int', ({})), ({}))")
                await core.nodes('[ _test:inhstr5=refs :_refs=5 ]')
                nodes = await core.nodes('test:int=5 -> test:inhstr2')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr5', 'refs'))

                await core.nodes('_test:inhstr5=refs | delnode')
                await core.nodes("$lib.model.ext.delFormProp(_test:inhstr5, _refs)")

            # Verify extended model reloads correctly
            async with self.getTestCore(dirn=dirn) as core:
                nodes = await core.nodes('test:inhstr:name=bar')
                self.len(3, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'ext'))
                self.eq(nodes[1].ndef, ('_test:inhstr5', 'ext2'))
                self.eq(nodes[2].ndef, ('test:inhstr3', 'bar'))

                nodes = await core.nodes('test:str=extprop -> *')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'ext'))

                # Lifting gets us all nodes with a value when multiple exist
                await core.nodes('[ test:inhstr2=dup _test:inhstr4=dup ]')
                nodes = await core.nodes('test:inhstr=dup')
                self.len(2, nodes)

                # Pivoting only goes to the most specific form with that value
                await core.nodes('[ test:str=dup :inhstr=dup ]')
                nodes = await core.nodes('test:str=dup -> *')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'dup'))

                # Attempting to add a less specific node when a more specific node exists will just
                # lift the more specific node instead of creating a new node
                nodes = await core.nodes('[ _test:inhstr5=dup ]')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('_test:inhstr4', 'dup'))

                mdef = await core.callStorm('return($lib.model.ext.getExtModel())')

                with self.raises(s_exc.CantDelNode):
                    await core.nodes("_test:inhstr5=ext2 | delnode")

                await core.nodes("test:str=extprop2 _test:inhstr5=ext2 | delnode")

                # Can't delete a form with child forms
                with self.raises(s_exc.CantDelType):
                    await core.nodes("$lib.model.ext.delForm(_test:inhstr5)")

                # Can't delete a prop which is in use on child forms
                with self.raises(s_exc.CantDelProp):
                    await core.nodes("$lib.model.ext.delFormProp(test:inhstr3, _xtra)")

                await core.nodes('test:inhstr3:_xtra [ -:_xtra ]')
                await core.nodes("$lib.model.ext.delFormProp(test:inhstr3, _xtra)")

                with self.raises(s_exc.NoSuchProp):
                    await core.nodes('_test:inhstr4:_xtra')

                await core.nodes("test:str _test:inhstr4 | delnode --force")
                await core.nodes("$lib.model.ext.delForm(_test:inhstr4)")
                await core.nodes("$lib.model.ext.delForm(_test:inhstr5)")

        async with self.getTestCore() as core:
            opts = {'vars': {'mdef': mdef}}
            self.true(await core.callStorm('return($lib.model.ext.addExtModel($mdef))', opts=opts))

            self.len(1, await core.nodes('[ _test:inhstr4=ext :name=bar :_xtra=here ]'))
            self.len(1, await core.nodes('test:inhstr:name=bar'))

            # Coverage for bad propdefs
            await core.addType('_test:newp', 'test:inhstr', {}, {})

            with self.raises(s_exc.BadPropDef):
                core.model.addForm('_test:newp', {}, ((1, 2),))

            with self.raises(s_exc.BadPropDef):
                core.model.addForm('_test:newp', {}, (('name', ('int', {}), {}),))

            core.model.addForm('_test:newp', {}, (('name', ('str', {}), {}),))

            # Test poly prop narrowing on subforms
            await core.addType('_test:polyid', 'poly', {'types': ('str', 'int')}, {})
            await core.addType('_test:polypar', 'guid', {}, {})
            await core.addType('_test:polychild', '_test:polypar', {}, {})
            await core.addType('_test:polybad', '_test:polypar', {}, {})

            core.model.addForm('_test:polypar', {}, (('ident', ('_test:polyid', {}), {}),))

            # Narrowing to a valid subset type works
            core.model.addForm('_test:polychild', {}, (('ident', ('str', {}), {}),))

            # Narrowing to a type not in the poly fails
            with self.raises(s_exc.BadPropDef):
                core.model.addForm('_test:polybad', {}, (('ident', ('float', {}), {}),))

            # Overriding with a different named poly type fails
            await core.addType('_test:polybad2', '_test:polypar', {}, {})
            await core.addType('_test:otherpoly', 'poly', {'types': ('str',)}, {})
            with self.raises(s_exc.BadPropDef):
                core.model.addForm('_test:polybad2', {}, (('ident', ('_test:otherpoly', {}), {}),))

            # Test poly prop interface narrowing on subforms
            await core.addType('_test:ifacepar', 'guid', {}, {})
            await core.addType('_test:ifacechild', '_test:ifacepar', {}, {})

            core.model.addForm('_test:ifacepar', {}, (('ref', ('entity:identifier', {}), {}),))

            # Narrowing a parent interface to a specific form type fails (cross-lane)
            with self.raises(s_exc.BadPropDef):
                core.model.addForm('_test:ifacechild', {}, (('ref', ('meta:id', {}), {}),))

            # Test interface subset narrowing
            await core.addType('_test:ifacepoly', 'poly', {'types': ('str',), 'interfaces': ('entity:identifier',)}, {})
            await core.addType('_test:ifsubpar', 'guid', {}, {})
            await core.addType('_test:ifsubchild', '_test:ifsubpar', {}, {})
            await core.addType('_test:ifsubbad', '_test:ifsubpar', {}, {})

            core.model.addForm('_test:ifsubpar', {}, (('ref', ('_test:ifacepoly', {}), {}),))

            # Narrowing to a valid interface subset works
            core.model.addForm('_test:ifsubchild', {}, (('ref', ('entity:identifier', {}), {}),))

            # Narrowing to an interface not in the parent poly fails
            with self.raises(s_exc.BadPropDef):
                core.model.addForm('_test:ifsubbad', {}, (('ref', ('meta:taxonomy', {}), {}),))

            await core.nodes("$lib.model.ext.addForm(_test:ip, inet:ip, ({}), ({}))")
            await core.nodes("$lib.model.ext.addFormProp(it:host, _ip2, ('_test:ip', ({})), ({}))")

            await core.nodes('[ it:network=* :net=(1.2.3.4, 1.2.3.6) _test:ip=1.2.3.4 inet:ip=1.2.3.5 ]')

            self.len(1, await core.nodes('it:network :net -> _test:ip'))
            self.len(4, await core.nodes('it:network :net -> inet:ip'))

            await core.nodes('[ it:host=* :ip=1.2.3.4 ]')
            await core.nodes('[ it:host=* :ip=1.2.3.5 ]')
            await core.nodes('[ it:host=* :_ip2=1.2.3.4 ]')
            await core.nodes('[ it:host=* :_ip2=1.2.3.6 ]')

            self.len(2, await core.nodes('it:network :net -> it:host:ip'))
            self.len(2, await core.nodes('it:network :net -> it:host:_ip2'))

            await core.nodes('[ inet:net=1.0.0.0/8 ]')

            self.len(2, await core.nodes('inet:net=1.0.0.0/8 -> _test:ip'))
            # TODO: avoid min/max duplication somehow?
            self.len(9, await core.nodes('inet:net=1.0.0.0/8 -> inet:ip'))

            self.len(2, await core.nodes('inet:net=1.0.0.0/8 -> it:host:ip'))
            self.len(2, await core.nodes('inet:net=1.0.0.0/8 -> it:host:_ip2'))

            # Handling for lift/pivot where children have more restrictive norming
            core.model.addType('_test:cve', 'meta:id', {'upper': True, 'regex': r'(?i)^CVE-[0-9]{4}-[0-9]{4,}$'}, {})
            core.model.addForm('_test:cve', {}, ())

            await core.nodes('[ meta:rule=* :id={[ meta:id=foo ]} ]')

            self.len(1, await core.nodes('meta:id=foo'))
            self.len(1, await core.nodes('meta:id=foo -> meta:rule'))
            self.len(1, await core.nodes('meta:id=foo -> meta:rule:id'))
            self.len(1, await core.nodes('meta:rule -> *'))
            self.len(1, await core.nodes('meta:rule :id -> *'))
            self.len(1, await core.nodes('meta:rule -> meta:id'))
            self.len(1, await core.nodes('meta:rule :id -> meta:id'))

            core.model.addFormProp('test:str', 'cve', ('_test:cve', {}), {})
            core.model.addFormProp('test:str', 'cves', ('array', {'type': '_test:cve'}), {})

            await core.nodes('''[
                (test:str=bar :cve=cve-2020-1234)
                (test:str=bararry :cves=(cve-2020-1234, cve-2021-1234))
            ]''')

            msgs = await core.stormlist('meta:id -> test:str:cve')
            self.stormHasNoWarnErr(msgs)
            self.len(1, [m for m in msgs if m[0] == 'node'])

            msgs = await core.stormlist('meta:id -> test:str:cves')
            self.stormHasNoWarnErr(msgs)
            self.len(2, [m for m in msgs if m[0] == 'node'])

            await core.nodes('[ meta:rule=* :id={[ _test:cve=cve-2020-1234 ] }]')
            msgs = await core.stormlist('meta:rule:id :id -> test:str:cves')
            self.stormHasNoWarnErr(msgs)
            self.len(1, [m for m in msgs if m[0] == 'node'])

    async def test_datamodel_polyprop(self):

        async with self.getTestCore() as core:

            # very specific lift to hit a difficult NoSuchAbrv
            await core.nodes('[ test:str=foo :poly={[ test:str=p1 ]} ]')
            self.len(0, await core.nodes('test:str:poly=$lib.cast(test:str:poly, 3)'))

            nodes = await core.nodes('''[
                (test:str=bar :poly={[ test:int=3 ]})
                (test:str=baz :poly={[ test:hasiface=p2 ]})
                (test:str=faz :poly={[ test:lowstr=p1 ]})
                (test:str=nop :poly={[ test:int=1 ]})
            ]''')

            # non-form specific lifts
            self.len(1, await core.nodes('test:str:poly>2'))
            self.len(1, await core.nodes('test:str:poly=3'))
            self.len(1, await core.nodes('test:str:poly=p2'))

            nodes = await core.nodes('test:str:poly>0')
            self.len(2, nodes)
            self.eq(nodes[::-1], await core.nodes('reverse(test:str:poly>0)'))

            # lifts using both test:str/test:lowstr norms
            nodes = await core.nodes('test:str:poly=p1')
            self.len(2, nodes)
            self.eq(nodes[::-1], await core.nodes('reverse(test:str:poly=p1)'))

            self.len(3, await core.nodes('test:str:poly^=p'))

            nodes = await core.nodes('test:str:poly^=P')
            self.len(3, nodes)
            self.eq(nodes[::-1], await core.nodes('reverse(test:str:poly^=P)'))

            # regex works too
            self.len(3, await core.nodes('test:str:poly~=P'))

            # prop pivots
            self.len(3, await core.nodes('test:str:poly^=P :poly -> *'))
            self.len(2, await core.nodes('test:str:poly^=P :poly -> test:str'))

            # repr is just the valu
            msgs = await core.stormlist('test:str:poly^=P $lib.print(:poly)')
            msgs = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.eq(msgs, ['p1', 'p1', 'p2'])

            q = '''
            test:str:poly^=P
            $foo=:poly
            $lib.print($foo.type)
            $lib.print($foo.ndef)
            $lib.print($foo.value)
            yield $foo
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1][0] for m in msgs if m[0] == 'node']
            self.eq(nodes, [
                ('test:str', 'p1'),
                ('test:str', 'foo'),
                ('test:lowstr', 'p1'),
                ('test:str', 'faz'),
                ('test:hasiface', 'p2'),
                ('test:str', 'baz')
            ])

            msgs = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.eq(msgs, [
                'test:str', "('test:str', 'p1')", 'p1',
                'test:lowstr', "('test:lowstr', 'p1')", 'p1',
                'test:hasiface', "('test:hasiface', 'p2')", 'p2'
            ])

            self.len(1, await core.nodes('test:str:poly^=P +:poly=p2'))

            # default form priority
            nodes = await core.nodes('''[
                (test:str=def1 :poly=p3)
                (test:str=def2 :poly=4)
            ]''')
            self.propeq(nodes[0], 'poly', 'p3', form='test:str')
            self.propeq(nodes[1], 'poly', 4, form='test:int')

            # using an ndef for assignment skips re-norming
            nodes = await core.nodes('''
                test:str=bar
                $valu = :poly
                [(test:str=ez1 :poly=$valu)]
            ''')
            self.propeq(nodes[0], 'poly', 3, form='test:int')
            self.propeq(nodes[1], 'poly', 3, form='test:int')

            nodes = await core.nodes('''[
                (test:str=a1 :polyarry={[ test:str=p10 test:int=5 test:hasiface=p11 test:lowstr=p10 ]})
                (test:str=a2 :polyarry=(p10, 5, p11, p10, 2))
            ]''')

            # poly array lift without specific type
            self.len(3, await core.nodes('test:str:polyarry*[=p10]'))
            self.len(2, await core.nodes('test:str:polyarry*[>4]'))

            # poly lift by node
            self.len(1, await core.nodes('test:str:poly={test:lowstr=p1}'))

            # poly lift by form
            self.len(1, await core.nodes('test:str:poly.type=test:lowstr'))

            # poly array lift by node
            self.len(1, await core.nodes('test:str:polyarry*[={test:lowstr=p10}]'))

            # poly array lift by form
            self.len(1, await core.nodes('test:str:polyarry*[.type=test:lowstr]'))
            self.len(3, await core.nodes('test:str:polyarry*[.type=test:str]'))

            # pivot in to poly reference
            self.len(1, await core.nodes('test:hasiface=p2 <- *'))

            # pivot in to poly array reference
            self.len(1, await core.nodes('test:hasiface=p11 <- *'))

            await core.nodes('[ test:str=ip :poly={[inet:server=tcp://1.2.3.4:80]} ]')

            # using a ndef in a var to set a prop bring virts along correctly
            await core.nodes('test:str=ip $foo=:poly [(test:str=ip2 :poly=$foo)]')
            msgs = await core.stormlist('test:str=ip2 $foo=:poly $lib.print($foo.port)')
            self.stormIsInPrint('80', msgs)

            # virtual prop of a form in a poly prop
            msgs = await core.stormlist('test:str=ip $lib.print(:poly.port)')
            self.stormIsInPrint('80', msgs)

            # virtual prop of a ndef in a var is accessible
            msgs = await core.stormlist('test:str=ip $foo=:poly $lib.print($foo.port)')
            self.stormIsInPrint('80', msgs)

            # poly virtual on a form lift
            self.len(2, await core.nodes('test:str:poly.port=80'))

            # poly virtual on a HasRelPropCond filter
            self.len(2, await core.nodes('test:str:poly +:poly.ip'))

            await core.nodes('[ test:str=iparry :polyarry={[inet:server=tcp://1.2.3.4:80 inet:server=tcp://1.2.3.4:90 inet:server=tcp://1.2.3.5:80]} ]')

            # poly array virtual on a form lift
            self.len(2, await core.nodes('test:str:polyarry*[.port=80]'))

            await core.nodes('test:str=iparry [ :polyarry-={ inet:server=tcp://1.2.3.4:80 } ]')
            self.len(1, await core.nodes('test:str:polyarry*[.port=80]'))

            nodes = await core.nodes('[ test:str=ifarray :polyint={[ test:hasiface=p123 ]} ]')
            self.len(1, await core.nodes('test:hasiface=p123 <- *'))

            opts = {'vars': {'long1': 'a' * 500, 'long2': 'a' * 500 + 'b'}}
            q = '[ test:str=nonuniq :polynonuniq={[ test:int=1 test:int=1 test:hasiface=1 test:str=$long1 test:str=$long2]} ]'
            await core.nodes(q, opts=opts)

            self.len(3, await core.nodes('test:str:polynonuniq*[=1]'))
            self.len(1, await core.nodes('test:str:polynonuniq*[=$long1]', opts=opts))
            self.len(1, await core.nodes('test:str:polynonuniq*[=$long2]', opts=opts))
            self.len(2, await core.nodes('test:str:polynonuniq*[^=a]'))
            self.len(2, await core.nodes('test:str:polynonuniq*[~=a]'))

            await core.nodes('[ test:str=piv1 :poly={[test:str=piv2 :poly={ test:str=nonuniq } ]} ]')
            self.len(1, await core.nodes('test:str:poly::poly::polynonuniq*[=1]'))

            self.none(await core.callStorm('[ test:str=empty ] return($node.props.poly)'))
            self.eq(6, await core.callStorm('[ test:str=intcast :poly={[ test:str=5 ]} ] return((:poly + 1))'))
            self.eq(6, await core.callStorm('[ test:str=len :poly={[ test:str=foobar ]} ] return($lib.len(:poly))'))

            q = '''
            $set=$lib.set()
            [ test:str=h1 test:str=h2 :poly=5 ]
            [( test:str=h3 :poly=6 )]
            $set.add(:poly)
            fini { return($set) }
            '''
            self.len(2, await core.callStorm(q))

            await core.nodes('[ test:str=if1 :poly={[ test:str2=inh ]} ]')
            self.true(await core.callStorm('test:str=if1 return((:poly).istype(test:str))'))
            self.true(await core.callStorm('test:str=if1 return((:poly).istype(test:str2))'))

            await core.nodes('[ test:str=if2 :poly={[ test:str=base ]} ]')
            self.true(await core.callStorm('test:str=if2 return((:poly).istype(test:str))'))
            self.false(await core.callStorm('test:str=if2 return((:poly).istype(test:str2))'))

            self.len(2, await core.nodes('test:str +:polyarry*[=p10]'))
            self.len(2, await core.nodes('test:str +:polyarry*[.type=test:str]'))

            await core.nodes('[ test:str=cov1 :inhstr=inh ]')
            self.len(1, await core.nodes('$n={ test:str=cov1 } test:str:poly=$n.props.inhstr'))
            self.len(1, await core.nodes('$n={ test:str=cov1 } test:str=cov1 +:inhstr=$n.props.inhstr'))

            self.len(0, await core.nodes('test:str:poly.type=test:hasiface2'))

            await core.nodes('[ test:str=long :poly={[ test:str=$long1 ]} ]', opts=opts)
            self.len(3, await core.nodes('test:str:poly~=a'))
            self.len(1, await core.nodes('test:str:poly~=aa'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('$n={ test:str=cov1 } [ test:str=cov2 :poly=$n.props.inhstr ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:poly.type=test:float')

            with self.raises(s_exc.BadTypeDef):
                tdef = ('poly', {'forms': ('test:str',), 'default_types': ('test:float',)})
                core.model.addFormProp('test:str', 'polyfail', tdef, {})

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:str:poly.newp')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str:poly.newp.newp')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str:poly.type.newp')

            with self.raises(s_exc.NoSuchType):
                core.model.type('poly').repr(('newp', 'newp'))

            msgs = await core.stormlist('''
                test:str
                if (:poly="p1") { $lib.print(cmpr1) }
                +:polyarry
                if (:polyarry).has(p10) { $lib.print(cmpr2) }
                $lib.print(:polyarry)
            ''')
            self.len(2, [m for m in msgs if m[0] == 'print' and m[1]['mesg'] == 'cmpr1'])
            self.len(2, [m for m in msgs if m[0] == 'print' and m[1]['mesg'] == 'cmpr2'])

            self.stormIsInPrint('[2, 5, p10, p11]', msgs)

            msgs = await core.stormlist('$set=$lib.set(p1, foo) test:str=faz if $set.has(:poly) { $lib.print(yes) }')
            self.stormIsInPrint('yes', msgs)

            msgs = await core.stormlist('$set=$lib.set(newp, nope) test:str=faz if $set.has(:poly) { $lib.print(yes) }')
            self.stormNotInPrint('yes', msgs)

            msgs = await core.stormlist('''
                $set=$lib.set()
                $s1 = {[ test:str=s1 :poly={[ test:str=v1 ]} ]}
                $s2 = {[ test:str=s2 :poly={[ test:lowstr=v1 ]} ]}
                $set.add($s1.props.poly)
                $set.add($s2.props.poly)

                $lib.print(`size={$set.size()}`)
                $lib.print($set.has($s1.props.poly))
                $lib.print($set.has($s2.props.poly))
                $lib.print($set.has(v1))
            ''')
            self.stormIsInPrint('size=1', msgs)
            self.stormIsInPrint('true', msgs)
            self.stormNotInPrint('false', msgs)

            # Poly.getCmprCtor raises BadTypeValu when all types fail
            await core.addFormProp('test:str', '_polyint', (('test:int', {}), ('test:comp', {})), {})
            await core.nodes('[test:str=foo :_polyint=1234]')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str +test:str:_polyint=haha')

            # Poly.getVirtGetr handles self.virts (e.g., .type)
            nodes = await core.nodes('[test:str=foo :bar=vertex.link]')
            node = nodes[0]
            self.isinstance(node.get('bar.type'), str)
            self.isinstance(node.get('bar.value'), str)

            # NodeRef.exists optimization works when reusing the same ref
            await core.nodes('[test:str=src :bar=vertex.link]')
            q = '''
                test:str=src $ref = :bar
                { [test:str=dst1 :bar=$ref] }
                { [test:str=dst2 :bar=$ref] }
            '''
            await core.nodes(q)
            self.len(1, await core.nodes('test:str=dst1 +:bar'))
            self.len(1, await core.nodes('test:str=dst2 +:bar'))

            form = core.model.form('test:str')
            with self.raises(s_exc.NoSuchType):
                core.model._addFormProp(form, '_badpoly', ('poly', {'types': ('newp:newp',)}), {})

            await core.addType('_test:myint', 'int', {}, {})
            await core.addFormProp('test:str', '_arryprop', ('array', {'type': '_test:myint'}), {})

            with self.raises(s_exc.CantDelType):
                core.model.reqTypeNotInUse('_test:myint')

            await core.delFormProp('test:str', '_arryprop')

            await core.addFormProp('test:str', '_ifpoly', (('inet:fqdn', {}), ('meta:observable', {})), {})
            self.nn(core.model.prop('test:str:_ifpoly'))
            await core.delFormProp('test:str', '_ifpoly')
            self.none(core.model.prop('test:str:_ifpoly'))

            await core.addFormProp('test:str', '_ifarry', ('array', {'type': (('inet:fqdn', {}), ('meta:observable', {}))}), {})
            self.nn(core.model.prop('test:str:_ifarry'))
            await core.delFormProp('test:str', '_ifarry')
            self.none(core.model.prop('test:str:_ifarry'))

            ptyp = core.model.prop('test:str:seen').type
            self.true(ptyp.ispoly)

            # getVirtType via getTypeSet path (ival's min virt)
            vtyp = ptyp.getVirtType('min')
            self.nn(vtyp)

            # getVirtType raise for unknown virt
            with self.raises(s_exc.NoSuchVirt):
                ptyp.getVirtType('newp')

            # getVirtInfo via getTypeSet path (ival's min virt)
            vinfo = ptyp.getVirtInfo('min')
            self.nn(vinfo[0])
            self.nn(vinfo[1])

            # getVirtInfo raise for unknown virt
            with self.raises(s_exc.NoSuchVirt):
                ptyp.getVirtInfo('newp')

            # invalid virtual prop with tryoper still raises NoSuchVirt
            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('inet:flow:server.newp?=1.2.3.4')

            # handling for poly with no valid types
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:polyempty=newp')

            self.len(0, await core.nodes('test:str:polyempty?=okay'))

            msgs = await core.stormlist('[test:str=foobar :polyarry++={[inet:server=tcp://1.2.3.4:9000]}]')
            for m in msgs:
                s_json.reqjsonsafe(m)

            nodes = await core.nodes('test:str=foobar')
            s_json.reqjsonsafe(nodes[0].pack(virts=True))
