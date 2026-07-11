import synapse.tests.utils as s_test

import synapse.exc as s_exc

class StormtypesModelextTest(s_test.SynTest):

    async def test_lib_stormlib_modelext_base(self):
        async with self.getTestCore() as core:
            await core.callStorm('''
                $typeinfo = ({})
                $forminfo = ({"doc": "A test form doc."})
                $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)

                $propinfo = ({"doc": "A test prop doc."})
                $lib.model.ext.addFormProp(_visi:int, _tick, (time, ({})), $propinfo)

                $tagpropinfo = ({"doc": "A test tagprop doc."})
                $lib.model.ext.addTagProp(_score, (int, ({})), $tagpropinfo)

                $pinfo = ({"doc": "Extended a core model."})
                $lib.model.ext.addFormProp(test:int, _tick, (time, ({})), $propinfo)

                $edgeinfo = ({"doc": "A test edge."})
                $lib.model.ext.addEdge(it:dev:str, _copies, *, $edgeinfo)

                $typeopts = ({"lower": true, "onespace": true})
                $typeinfo = ({"doc": "A test type doc."})
                $forminfo = ({"doc": "A test type form doc."})
                $lib.model.ext.addType(_test:type, str, $typeopts, $typeinfo)
                $lib.model.ext.addForm(_test:typeform, _test:type, ({}), $forminfo)
            ''')

            # The array type may only be used inline on a prop, never as a named type.
            with self.raises(s_exc.BadTypeDef):
                await core.callStorm(
                    '$lib.model.ext.addType(_test:typearry, array, ({"type": "_test:type"}), ({}))')

            q = '[ _visi:int=10 :_tick=20210101 +#lol:_score=99 <(_copies)+ {[ it:dev:str=visi ]} ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_visi:int', 10))
            self.propeq(nodes[0], '_tick', 1609459200000000)
            self.eq(nodes[0].getTagProp('lol', '_score'), 99)

            nodes = await core.nodes('[test:int=1234 :_tick=20210101]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1234))
            self.propeq(nodes[0], '_tick', 1609459200000000)

            nodes = await core.nodes('[_test:typeform="  FoO BaR  "]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_test:typeform', 'foo bar'))

            with self.raises(s_exc.DupTypeName):
                q = '$lib.model.ext.addType(_test:type, str, ({}), ({}))'
                await core.callStorm(q)

            with self.raises(s_exc.DupTypeName):
                q = '$lib.model.ext.addForm(_test:type, str, ({}), ({}))'
                await core.callStorm(q)

            with self.raises(s_exc.DupPropName):
                q = '''$lib.model.ext.addFormProp(_visi:int, _tick, (time, ({})), ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.DupEdgeType):
                q = '''$lib.model.ext.addEdge(it:dev:str, _copies, *, ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadFormDef):
                q = '$lib.model.ext.addForm(_test:formarry, array, ({"type": "_test:type"}), ({}))'
                await core.callStorm(q)

            self.nn(core.model.edge(('it:dev:str', '_copies', None)))

            with self.raises(s_exc.CantDelEdge):
                await core.callStorm('$lib.model.ext.delEdge(it:dev:str, _copies, *)')

            # Grab the extended model definitions
            model_defs = await core.callStorm('return ( $lib.model.ext.getExtModel() )')
            self.isinstance(model_defs, dict)

            self.len(1, await core.nodes('_visi:int:_tick'))
            await core._delAllFormProp('_visi:int', '_tick', {})
            self.len(0, await core.nodes('_visi:int:_tick'))

            # Add a tagprop to a node with a long form name so the abrv is indexed after the
            # form=None abrvs to get _delAllTagProp coverage
            await core.nodes('[ crypto:smart:effect:edittokensupply=* +#foo:_score=99 ]')

            self.len(1, await core.nodes('#lol:_score'))
            await core._delAllTagProp('_score', {})
            self.len(0, await core.nodes('#lol:_score'))

            await core.callStorm('it:dev:str=visi _visi:int=10 test:int=1234 _test:typeform | delnode')
            await core.callStorm('''
                $lib.model.ext.delTagProp(_score, force=(true))
                $lib.model.ext.delFormProp(_visi:int, _tick)
                $lib.model.ext.delFormProp(test:int, _tick, force=(true))
                $lib.model.ext.delForm(_visi:int)
                $lib.model.ext.delEdge(it:dev:str, _copies, *)
            ''')

            with self.raises(s_exc.CantDelType) as cm:
                await core.callStorm('$lib.model.ext.delType(_test:type)')
            self.isin('still in use by other types', cm.exception.get('mesg'))

            await core.callStorm('$lib.model.ext.delForm(_test:typeform)')

            await core.callStorm('$lib.model.ext.delType(_test:type)')

            self.none(core.model.type('_test:type'))
            self.none(core.model.form('_test:typeform'))
            self.none(core.model.form('_visi:int'))
            self.none(core.model.prop('_visi:int:_tick'))
            self.none(core.model.prop('test:int:_tick'))
            self.none(core.model.tagprop('score'))
            self.none(core.model.edge(('it:dev:str', '_copies', None)))

            # Underscores can exist in extended names but only at specific locations
            q = '''$l =(['str', {}]) $d=({"doc": "Foo"})
            $lib.model.ext.addFormProp('test:str', '_test:_myprop', $l, $d)
            '''
            self.none(await core.callStorm(q))

            # Extended tagprop names must begin with '_'
            q = '''$lib.model.ext.addTagProp(_score, (int, ({})), ({}))'''
            self.none(await core.callStorm(q))

            q = '''$lib.model.ext.addTagProp(_some:score, (int, ({})), ({}))'''
            self.none(await core.callStorm(q))

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addTagProp(some:_score, (int, ({})), ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadTypeDef):
                q = '$lib.model.ext.addType(test:type, str, ({}), ({}))'
                await core.callStorm(q)

            with self.raises(s_exc.BadTypeDef):
                q = '$lib.model.ext.delType(test:type)'
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$l =(['str', {}]) $d=({"doc": "Foo"})
                $lib.model.ext.addFormProp('test:str', '_test:_my^prop', $l, $d)
                '''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$l =(['str', {}]) $d=({"doc": "Foo"})
                $lib.model.ext.addFormProp('test:str', '_test::_myprop', $l, $d)
                '''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addTagProp(some^score, (int, ({})), ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addTagProp(_someones:_score^value, (int, ({})), ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadEdgeDef):
                q = '''$lib.model.ext.addEdge(*, does, *, ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadEdgeDef):
                q = '''$lib.model.ext.addEdge(*, _NEWP, *, ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadEdgeDef):
                q = '''$lib.model.ext.addEdge(*, "_ne wp", *, ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadEdgeDef):
                q = f'''$lib.model.ext.addEdge(*, "_{'a' * 201}", *, ({{}}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadEdgeDef):
                q = '''$lib.model.ext.delEdge(*, "_ne wp", *)'''
                await core.callStorm(q)

            # Permission errors
            visi = await core.auth.addUser('visi')
            opts = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $typeinfo = ({})
                    $forminfo = ({"doc": "A test form doc."})
                    $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.callStorm('''
                    $lib.model.ext.addType(_test:type, str, ({}), ({}))
                ''', opts=opts)
            self.isin('permission model.admin', cm.exception.get('mesg'))

            with self.raises(s_exc.AuthDeny) as cm:
                await core.callStorm('''
                    $lib.model.ext.delType(_test:type)
                ''', opts=opts)
            self.isin('permission model.admin', cm.exception.get('mesg'))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $propinfo = ({"doc": "A test prop doc."})
                    $lib.model.ext.addFormProp(_visi:int, _tick, (time, ({})), $propinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $tagpropinfo = ({"doc": "A test tagprop doc."})
                    $lib.model.ext.addTagProp(_score, (int, ({})), $tagpropinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                q = '''$lib.model.ext.addEdge(*, _does, *, ({}))'''
                await core.callStorm(q, opts=opts)

        # Reload the model extensions automatically
        async with self.getTestCore() as core:
            opts = {'vars': {'model_defs': model_defs}}
            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            self.true(await core.callStorm(q, opts))

            nodes = await core.nodes('[ _visi:int=10 :_tick=20210101 +#lol:_score=99 ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_visi:int', 10))
            self.propeq(nodes[0], '_tick', 1609459200000000)
            self.eq(nodes[0].getTagProp('lol', '_score'), 99)

            nodes = await core.nodes('[test:int=1234 :_tick=20210101]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1234))
            self.propeq(nodes[0], '_tick', 1609459200000000)

            # Reloading the same data works fine
            opts = {'vars': {'model_defs': model_defs}}
            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            self.true(await core.callStorm(q, opts))

        # Add props which conflict with what was previously dumped
        async with self.getTestCore() as core:
            await core.callStorm('''
                $typeopts = ({"lower": true})
                $typeinfo = ({"doc": "A test type doc."})
                $lib.model.ext.addType(_test:type, str, $typeopts, $typeinfo)

                $typeinfo = ({})
                $forminfo = ({"doc": "NEWP"})
                $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)

                $propinfo = ({"doc": "NEWP"})
                $lib.model.ext.addFormProp(_visi:int, _tick, (time, ({})), $propinfo)

                $tagpropinfo = ({"doc": "NEWP"})
                $lib.model.ext.addTagProp(_score, (int, ({})), $tagpropinfo)

                $pinfo = ({"doc": "NEWP"})
                $lib.model.ext.addFormProp(test:int, _tick, (time, ({})), $propinfo)

                $edgeinfo = ({"doc": "NEWP"})
                $lib.model.ext.addEdge(it:dev:str, _copies, *, $edgeinfo)
            ''')

            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            with self.raises(s_exc.BadTypeDef) as cm:
                opts = {'vars': {'model_defs': {'types': model_defs['types']}}}
                await core.callStorm(q, opts)

            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            with self.raises(s_exc.BadFormDef) as cm:
                opts = {'vars': {'model_defs': {'forms': model_defs['forms']}}}
                await core.callStorm(q, opts)

            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            with self.raises(s_exc.BadPropDef) as cm:
                opts = {'vars': {'model_defs': {'props': model_defs['props']}}}
                await core.callStorm(q, opts)

            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            with self.raises(s_exc.BadPropDef) as cm:
                opts = {'vars': {'model_defs': {'tagprops': model_defs['tagprops']}}}
                await core.callStorm(q, opts)

            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            with self.raises(s_exc.BadEdgeDef) as cm:
                opts = {'vars': {'model_defs': {'edges': model_defs['edges']}}}
                await core.callStorm(q, opts)

        # Reload the model extensions from the dump by hand
        async with self.getTestCore() as core:
            opts = {'vars': {'model_defs': model_defs}}
            q = '''
            for ($name, $type, $opts, $info) in $model_defs.types {
                $lib.model.ext.addType($name, $type, $opts, $info)
            }
            for ($name, $type, $opts, $info) in $model_defs.forms {
                $lib.model.ext.addForm($name, $type, $opts, $info)
            }
            for ($form, $prop, $def, $info) in $model_defs.props {
                $lib.model.ext.addFormProp($form, $prop, $def, $info)
            }
            for ($prop, $def, $info) in $model_defs.tagprops {
                $lib.model.ext.addTagProp($prop, $def, $info)
            }
            for ($edge, $info) in $model_defs.edges {
                ($n1form, $verb, $n2form) = $edge
                $lib.model.ext.addEdge($n1form, $verb, $n2form, $info)
            }
            '''
            await core.nodes(q, opts)

            nodes = await core.nodes('[ _visi:int=10 :_tick=20210101 +#lol:_score=99 ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_visi:int', 10))
            self.propeq(nodes[0], '_tick', 1609459200000000)
            self.eq(nodes[0].getTagProp('lol', '_score'), 99)

            nodes = await core.nodes('[test:int=1234 :_tick=20210101]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1234))
            self.propeq(nodes[0], '_tick', 1609459200000000)

            self.nn(core.model.edge(('it:dev:str', '_copies', None)))

        # Property values left behind in layers are cleanly removed
        async with self.getTestCore() as core:
            await core.callStorm('''
                $typeinfo = ({})
                $docinfo = ({"doc": "NEWP"})
                $lib.model.ext.addTagProp(_score, (int, ({})), $docinfo)
                $lib.model.ext.addFormProp(test:int, _tick, (time, ({})), $docinfo)
            ''')
            fork = await core.callStorm('return ( $lib.view.get().fork().iden ) ')
            nodes = await core.nodes('[test:int=1234 :_tick=2024 +#hehe:_score=10]')
            self.len(1, nodes)

            nodes = await core.nodes('test:int=1234 [:_tick=2023 +#hehe:_score=9]',
                                     opts={'view': fork})
            self.len(1, nodes)

            self.len(0, await core.nodes('test:int | delnode'))

            with self.raises(s_exc.CantDelProp):
                await core.callStorm('$lib.model.ext.delFormProp(test:int, _tick)')
            with self.raises(s_exc.CantDelProp):
                await core.callStorm('$lib.model.ext.delTagProp(_score)')

            await core.callStorm('$lib.model.ext.delFormProp(test:int, _tick, force=(true))')
            await core.callStorm('$lib.model.ext.delTagProp(_score, force=(true))')

            nodes = await core.nodes('[test:int=1234]')
            self.len(1, nodes)
            self.none(nodes[0].get('_tick'))
            nodes = await core.nodes('test:int=1234', opts={'view': fork})
            self.none(nodes[0].get('_tick'))

    async def test_lib_stormlib_behold_modelext(self):
        self.skipIfNexusReplay()
        async with self.getTestCore() as core:
            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')
            await visi.setAdmin(True)

            async with self.getHttpSess() as sess:
                async with sess.post(f'https://localhost:{port}/api/v3/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                async with sess.ws_connect(f'wss://localhost:{port}/api/v3/behold') as sock:
                    await sock.send_json({'type': 'call:init'})
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'init')

                    await core.callStorm('''
                        $lib.model.ext.addForm(_behold:score, int, ({}), ({"doc": "first string"}))
                        $lib.model.ext.addFormProp(_behold:score, _rank, (int, ({})), ({"doc": "second string"}))
                        $lib.model.ext.addFormProp(_behold:score, _codes, (int, ({})), ({"array": ({}), "doc": "third string"}))
                        $lib.model.ext.addFormProp(_behold:score, _pair, ((str, ({})), (int, ({}))), ({"doc": "poly two named types"}))
                        $lib.model.ext.addTagProp(_thingy, (int, ({})), ({"doc": "fourth string"}))
                        $lib.model.ext.addEdge(*, _goes, geo:place, ({"doc": "fifth string"}))
                    ''')

                    formmesg = await sock.receive_json()
                    self.eq(formmesg['data']['event'], 'model:form:add')
                    self.nn(formmesg['data']['info']['form'])
                    self.eq(formmesg['data']['info']['form']['name'], '_behold:score')
                    self.nn(formmesg['data']['info']['type'])
                    self.nn(formmesg['data']['info']['type']['info'])

                    propmesg = await sock.receive_json()
                    self.eq(propmesg['data']['event'], 'model:prop:add')
                    self.eq(propmesg['data']['info']['form'], '_behold:score')
                    self.eq(propmesg['data']['info']['prop']['full'], '_behold:score:_rank')
                    self.eq(propmesg['data']['info']['prop']['name'], '_rank')
                    self.eq(propmesg['data']['info']['prop']['stortype'], 29)

                    # _codes is an array ext prop: no separate model:type:add, and the prop add
                    # carries the element typedef plus the 'array' container info key.
                    codesmesg = await sock.receive_json()
                    self.eq(codesmesg['data']['event'], 'model:prop:add')
                    self.eq(codesmesg['data']['info']['form'], '_behold:score')
                    self.eq(codesmesg['data']['info']['prop']['full'], '_behold:score:_codes')
                    self.eq(('int', {}), codesmesg['data']['info']['prop']['type'])
                    self.eq({}, codesmesg['data']['info']['prop']['array'])

                    # _pair is a poly of two named types, delivered inline in the prop typedef.
                    pairmesg = await sock.receive_json()
                    self.eq(pairmesg['data']['event'], 'model:prop:add')
                    self.eq(pairmesg['data']['info']['prop']['full'], '_behold:score:_pair')
                    self.sorteq(('int', 'str'), pairmesg['data']['info']['prop']['type'][1]['types'])

                    tagpmesg = await sock.receive_json()
                    self.eq(tagpmesg['data']['event'], 'model:tagprop:add')
                    self.eq(tagpmesg['data']['info']['name'], '_thingy')
                    self.eq(tagpmesg['data']['info']['info'], {'doc': 'fourth string'})

                    edgemesg = await sock.receive_json()
                    self.eq(edgemesg['data']['event'], 'model:edge:add')
                    self.eq(edgemesg['data']['info']['edge'], (None, '_goes', 'geo:place'))
                    self.eq(edgemesg['data']['info']['info'], {'doc': 'fifth string'})

                    await core.callStorm('''
                        $lib.model.ext.delTagProp(_thingy)
                        $lib.model.ext.delFormProp(_behold:score, _rank)
                        $lib.model.ext.delFormProp(_behold:score, _codes)
                        $lib.model.ext.delFormProp(_behold:score, _pair)
                        $lib.model.ext.delForm(_behold:score)
                        $lib.model.ext.delEdge(*, _goes, geo:place)
                    ''')
                    deltagp = await sock.receive_json()
                    self.eq(deltagp['data']['event'], 'model:tagprop:del')
                    self.eq(deltagp['data']['info']['tagprop'], '_thingy')

                    delprop = await sock.receive_json()
                    self.eq(delprop['data']['event'], 'model:prop:del')
                    self.eq(delprop['data']['info']['form'], '_behold:score')
                    self.eq(delprop['data']['info']['prop'], '_rank')

                    # deleting the array prop drops just the prop.
                    delcodes = await sock.receive_json()
                    self.eq(delcodes['data']['event'], 'model:prop:del')
                    self.eq(delcodes['data']['info']['prop'], '_codes')

                    # the poly prop drops just the prop; its members are shared named types.
                    delpair = await sock.receive_json()
                    self.eq(delpair['data']['event'], 'model:prop:del')
                    self.eq(delpair['data']['info']['prop'], '_pair')

                    delform = await sock.receive_json()
                    self.eq(delform['data']['event'], 'model:form:del')
                    self.eq(delform['data']['info']['form'], '_behold:score')

                    deledge = await sock.receive_json()
                    self.eq(deledge['data']['event'], 'model:edge:del')
                    self.eq(deledge['data']['info']['edge'], (None, '_goes', 'geo:place'))

    async def test_lib_stormlib_modelext_delform(self):
        '''
        Verify extended forms can't be deleted if they have associated extended props
        '''

        async with self.getTestCore() as core:

            await core.callStorm('''
                $typeinfo = ({})
                $forminfo = ({"doc": "A test form doc."})
                $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)

                $propinfo = ({"doc": "A test prop doc."})
                $lib.model.ext.addFormProp(_visi:int, _tick, (time, ({})), $propinfo)
            ''')

            self.nn(core.model.form('_visi:int'))
            self.nn(core.model.prop('_visi:int:_tick'))

            q = '$lib.model.ext.delForm(_visi:int)'
            with self.raises(s_exc.CantDelForm) as exc:
                await core.callStorm(q)
            self.eq('Form has extended properties: _tick', exc.exception.get('mesg'))

            await core.callStorm('$lib.model.ext.addFormProp(_visi:int, _tock, (time, ({})), ({}))')

            self.nn(core.model.form('_visi:int'))
            self.nn(core.model.prop('_visi:int:_tick'))
            self.nn(core.model.prop('_visi:int:_tock'))

            q = '$lib.model.ext.delForm(_visi:int)'
            with self.raises(s_exc.CantDelForm) as exc:
                await core.callStorm(q)
            self.eq('Form has extended properties: _tick, _tock', exc.exception.get('mesg'))

            await core.callStorm('''
                $lib.model.ext.delFormProp(_visi:int, _tick)
                $lib.model.ext.delFormProp(_visi:int, _tock)
                $lib.model.ext.delForm(_visi:int)
            ''')

            self.none(core.model.form('_visi:int'))
            self.none(core.model.prop('_visi:int:_tick'))
            self.none(core.model.prop('_visi:int:_tock'))

    async def test_lib_stormlib_modelext_argtypes(self):
        '''
        Verify type checking of typedef and propdef arguments.
        '''

        vectors = (
            (
                '$lib.model.ext.addForm(inet:fqdn, _foo:bar, (guid, ()), ({}))',
                'Form type options should be a dict.'
            ),
            (
                '$lib.model.ext.addForm(inet:fqdn, _foo:bar, ({}), ())',
                'Form type info should be a dict.'
            ),
            (
                '$lib.model.ext.addType(_test:type, str, (guid, ()), ())',
                'Type options should be a dict.'
            ),
            (
                '$lib.model.ext.addType(_test:type, str, ({}), ())',
                'Type info should be a dict.'
            ),
            (
                '$lib.model.ext.addFormProp(inet:fqdn, _foo:bar, ({}), ())',
                'Form property type definitions should be a tuple.'
            ),
            (
                '$lib.model.ext.addFormProp(inet:fqdn, _foo:bar, (), ())',
                'Form property definitions should be a dict.'
            ),
            (
                '$lib.model.ext.addTagProp(_foo:bar, ({}), ())',
                'Tag property type definitions should be a tuple.'
            ),
            (
                '$lib.model.ext.addTagProp(_foo:bar, (), ())',
                'Tag property definitions should be a dict.'
            ),
            (
                '$lib.model.ext.addEdge(*, _foo, *, ())',
                'Edge info should be a dict.'
            ),
        )

        async with self.getTestCore() as core:

            for query, err in vectors:

                with self.raises(s_exc.BadArg) as exc:
                    await core.callStorm(query)
                self.eq(err, exc.exception.get('mesg'))

    async def test_lib_stormlib_modelext_interfaces(self):
        async with self.getTestCore() as core:

            await core.callStorm('''
                $forminfo = ({"interfaces": [["test:interface", {}]]})
                $lib.model.ext.addForm(_test:iface, str, ({}), $forminfo)
                $lib.model.ext.addFormProp(_test:iface, _tick, (time, ({})), ({}))
            ''')

            self.nn(core.model.form('_test:iface'))
            self.nn(core.model.prop('_test:iface:flow'))
            self.nn(core.model.prop('_test:iface:_tick'))
            self.nn(core.model.prop('_test:iface:server'))
            self.isin('_test:iface', core.model.formsbyiface['test:interface'])
            self.isin('_test:iface', core.model.formsbyiface['inet:proto:link'])
            self.isin('_test:iface', core.model.formsbyiface['inet:proto:request'])
            self.isin('_test:iface:flow', core.model.ifaceprops['inet:proto:request:flow'])
            self.isin('_test:iface:client:proc', core.model.ifaceprops['test:interface:client:proc'])
            self.isin('_test:iface:client:proc', core.model.ifaceprops['inet:proto:request:client:proc'])
            self.isin('_test:iface:server', core.model.ifaceprops['inet:proto:link:server'])

            q = '$lib.model.ext.delForm(_test:iface)'
            with self.raises(s_exc.CantDelForm) as exc:
                await core.callStorm(q)
            self.eq('Form has extended properties: _tick', exc.exception.get('mesg'))

            await core.callStorm('''
                $lib.model.ext.delFormProp(_test:iface, _tick)
                $lib.model.ext.delForm(_test:iface)
            ''')

            self.none(core.model.form('_test:iface'))
            self.none(core.model.prop('_test:iface:flow'))
            self.none(core.model.prop('_test:iface:proc'))
            self.none(core.model.prop('_test:iface:_tick'))
            self.notin('_test:iface', core.model.formsbyiface['test:interface'])
            self.notin('_test:iface', core.model.formsbyiface['inet:proto:request'])
            self.notin('_test:iface', core.model.formsbyiface['it:host:activity'])
            self.notin('_test:iface:flow', core.model.ifaceprops['inet:proto:request:flow'])
            self.notin('_test:iface:proc', core.model.ifaceprops['test:interface:proc'])
            self.notin('_test:iface:proc', core.model.ifaceprops['inet:proto:request:proc'])
            self.notin('_test:iface:proc', core.model.ifaceprops['it:host:activity:proc'])

            await core.stormlist('''
                $forminfo = ({"interfaces": [["newp", {}]]})
                $lib.model.ext.addForm(_test:iface, str, ({}), $forminfo)
            ''')
            self.nn(core.model.form('_test:iface'))

            await core.callStorm('$lib.model.ext.delForm(_test:iface)')
            self.none(core.model.form('_test:iface'))

    async def test_lib_stormlib_modelext_array_prop(self):
        '''
        Verify that extended array form props round-trip correctly through
        getExtModel/addExtModel and survive a Cortex restart.
        '''
        # Part 1: array ext prop - add, inspect, and dump extmodel
        async with self.getTestCore() as core:
            await core.callStorm('''
                $propinfo = ({"array": ({}), "doc": "A list of tags."})
                $lib.model.ext.addFormProp(test:int, _tags, (str, ({})), $propinfo)
            ''')

            # An array ext prop stores its element typedef plus the 'array' info key;
            # no separate named type is registered.
            prop = core.model.prop('test:int:_tags')
            self.nn(prop)
            self.true(prop.type.isarray)
            self.eq('array', prop.type.name)
            self.eq(prop.typedef, ('str', {}))
            self.eq(prop.info['array'], {})

            # The client model dict carries the element typedef and the 'array' info key.
            mdict = await core.getModelDict()
            propdef = mdict['forms']['test:int']['props']['_tags']
            self.eq(('str', {}), propdef['type'])
            self.eq({}, propdef['array'])

            # getExtModel() stores the element typedef and info so a fresh cortex can re-clone it.
            extmodel = await core.getExtModel()
            prop_entries = [e for e in extmodel.get('props', ()) if e[0] == 'test:int' and e[1] == '_tags']
            self.len(1, prop_entries)
            self.eq(('str', {}), prop_entries[0][2])
            self.eq({}, prop_entries[0][3].get('array'))

        # Part 2: addExtModel on a fresh core must not raise NoSuchType
        async with self.getTestCore() as core:
            await core.addExtModel(extmodel)

            prop = core.model.prop('test:int:_tags')
            self.nn(prop)
            self.true(prop.type.isarray)
            self.eq(prop.typedef, ('str', {}))
            self.eq(prop.info['array'], {})

            # Re-loading the same extmodel must be idempotent.
            await core.addExtModel(extmodel)

        # Part 3: restart (same dirn) - _applyExtModel must re-clone the array typedef
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                await core.callStorm('''
                    $propinfo = ({"array": ({}), "doc": "A list of tags."})
                    $lib.model.ext.addFormProp(test:int, _tags, (str, ({})), $propinfo)
                ''')
                self.nn(core.model.prop('test:int:_tags'))

            async with self.getTestCore(dirn=dirn) as core:
                prop = core.model.prop('test:int:_tags')
                self.nn(prop)
                self.true(prop.type.isarray)
                self.eq(prop.typedef, ('str', {}))
                self.eq(prop.info['array'], {})

                await core.callStorm('$lib.model.ext.delFormProp(test:int, _tags)')
                self.none(core.model.prop('test:int:_tags'))

    async def test_lib_stormlib_modelext_poly_tuple_prop(self):
        '''
        Verify extended form props with poly-tuple inline typedefs whose constituents carry
        real type opts are rejected -- constituents must reference named types.
        '''
        async with self.getTestCore() as core:
            with self.raises(s_exc.BadPropDef):
                await core.callStorm('''
                    $tdef = ((str, ({"regex": "^[a-z]+"})), (int, ({})))
                    $lib.model.ext.addFormProp(test:int, _altid, $tdef, ({"doc": "poly"}))
                ''')
            self.none(core.model.prop('test:int:_altid'))

            # A poly-tuple of named types (no inline opts) is accepted.
            await core.callStorm('''
                $tdef = ((str, ({})), (int, ({})))
                $lib.model.ext.addFormProp(test:int, _altid, $tdef, ({"doc": "poly"}))
            ''')
            prop = core.model.prop('test:int:_altid')
            self.nn(prop)
            self.true(prop.type.ispoly)
            await core.callStorm('$lib.model.ext.delFormProp(test:int, _altid)')
            self.none(core.model.prop('test:int:_altid'))

    async def test_lib_stormlib_modelext_poly_format_prop(self):
        '''
        Verify extended form props with ('poly', opts) format tdefs load correctly.
        '''
        async with self.getTestCore() as core:
            await core.callStorm('''
                $propinfo = ({"doc": "A plain poly prop."})
                $tdef = (poly, ({"types": ["str", "int"]}))
                $lib.model.ext.addFormProp(test:int, _polyid, $tdef, $propinfo)
            ''')

            prop = core.model.prop('test:int:_polyid')
            self.nn(prop)
            self.true(prop.type.ispoly)
            self.sorteq(('int', 'str'), prop.type.typeset)
