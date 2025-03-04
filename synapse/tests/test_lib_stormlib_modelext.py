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
                $lib.model.ext.addFormProp(_visi:int, tick, (time, ({})), $propinfo)

                $univinfo = ({"doc": "A test univ doc."})
                $lib.model.ext.addUnivProp(_woot, (int, ({})), $univinfo)

                $tagpropinfo = ({"doc": "A test tagprop doc."})
                $lib.model.ext.addTagProp(score, (int, ({})), $tagpropinfo)

                $pinfo = ({"doc": "Extended a core model."})
                $lib.model.ext.addFormProp(test:int, _tick, (time, ({})), $propinfo)

                $edgeinfo = ({"doc": "A test edge."})
                $lib.model.ext.addEdge(inet:user, _copies, *, $edgeinfo)

                $typeopts = ({"lower": true, "onespace": true})
                $typeinfo = ({"doc": "A test type doc."})
                $forminfo = ({"doc": "A test type form doc."})
                $lib.model.ext.addType(_test:type, str, $typeopts, $typeinfo)
                $lib.model.ext.addForm(_test:typeform, _test:type, ({}), $forminfo)
                $lib.model.ext.addForm(_test:typearry, array, ({"type": "_test:type"}), $forminfo)
            ''')

            nodes = await core.nodes('[ _visi:int=10 :tick=20210101 ._woot=30 +#lol:score=99 ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_visi:int', 10))
            self.eq(nodes[0].get('tick'), 1609459200000)
            self.eq(nodes[0].get('._woot'), 30)
            self.eq(nodes[0].getTagProp('lol', 'score'), 99)

            nodes = await core.nodes('[test:int=1234 :_tick=20210101]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1234))
            self.eq(nodes[0].get('_tick'), 1609459200000)

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
                q = '''$lib.model.ext.addFormProp(_visi:int, tick, (time, ({})), ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.DupPropName):
                q = '''$lib.model.ext.addUnivProp(_woot, (time, ({})), ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.DupEdgeType):
                q = '''$lib.model.ext.addEdge(inet:user, _copies, *, ({}))'''
                await core.callStorm(q)

            self.nn(core.model.edge(('inet:user', '_copies', None)))

            # Grab the extended model definitions
            model_defs = await core.callStorm('return ( $lib.model.ext.getExtModel() )')
            self.isinstance(model_defs, dict)

            self.len(1, await core.nodes('_visi:int:tick'))
            await core._delAllFormProp('_visi:int', 'tick', {})
            self.len(0, await core.nodes('_visi:int:tick'))

            self.len(1, await core.nodes('._woot'))
            await core._delAllUnivProp('_woot', {})
            self.len(0, await core.nodes('._woot'))

            self.len(1, await core.nodes('#lol:score'))
            await core._delAllTagProp('score', {})
            self.len(0, await core.nodes('#lol:score'))

            await core.callStorm('_visi:int=10 test:int=1234 _test:typeform | delnode')
            await core.callStorm('''
                $lib.model.ext.delTagProp(score, force=(true))
                $lib.model.ext.delUnivProp(_woot, force=(true))
                $lib.model.ext.delFormProp(_visi:int, tick)
                $lib.model.ext.delFormProp(test:int, _tick, force=(true))
                $lib.model.ext.delForm(_visi:int)
                $lib.model.ext.delEdge(inet:user, _copies, *)
            ''')

            with self.raises(s_exc.CantDelType) as cm:
                await core.callStorm('$lib.model.ext.delType(_test:type)')
            self.isin('still in use by other types', cm.exception.get('mesg'))

            await core.callStorm('$lib.model.ext.delForm(_test:typeform)')

            with self.raises(s_exc.CantDelType) as cm:
                await core.callStorm('$lib.model.ext.delType(_test:type)')
            self.isin('still in use by array types', cm.exception.get('mesg'))

            await core.callStorm('$lib.model.ext.delForm(_test:typearry)')
            await core.callStorm('$lib.model.ext.delType(_test:type)')

            self.none(core.model.type('_test:type'))
            self.none(core.model.form('_test:typeform'))
            self.none(core.model.form('_test:typearry'))
            self.none(core.model.form('_visi:int'))
            self.none(core.model.prop('._woot'))
            self.none(core.model.prop('_visi:int:tick'))
            self.none(core.model.prop('test:int:_tick'))
            self.none(core.model.tagprop('score'))
            self.none(core.model.edge(('inet:user', '_copies', None)))

            # Underscores can exist in extended names but only at specific locations
            q = '''$l =(['str', {}]) $d=({"doc": "Foo"})
            $lib.model.ext.addFormProp('test:str', '_test:_myprop', $l, $d)
            '''
            self.none(await core.callStorm(q))
            q = '$lib.model.ext.addUnivProp(_woot:_stuff, (int, ({})), ({}))'
            self.none(await core.callStorm(q))

            q = '''$lib.model.ext.addTagProp(_score, (int, ({})), ({}))'''
            self.none(await core.callStorm(q))

            q = '''$lib.model.ext.addTagProp(some:_score, (int, ({})), ({}))'''
            self.none(await core.callStorm(q))

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
                q = '''$lib.model.ext.addUnivProp(_woot^stuff, (int, ({})), ({}))'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addUnivProp(_woot:_stuff^2, (int, ({})), ({}))'''
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
                q = f'''$lib.model.ext.addEdge(*, "_{'a'*201}", *, ({{}}))'''
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
            self.isin('permission model.type.add._test:type', cm.exception.get('mesg'))

            with self.raises(s_exc.AuthDeny) as cm:
                await core.callStorm('''
                    $lib.model.ext.delType(_test:type)
                ''', opts=opts)
            self.isin('permission model.type.del._test:type', cm.exception.get('mesg'))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $propinfo = ({"doc": "A test prop doc."})
                    $lib.model.ext.addFormProp(_visi:int, tick, (time, ({})), $propinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $univinfo = ({"doc": "A test univ doc."})
                    $lib.model.ext.addUnivProp(".woot", (int, ({})), $univinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $tagpropinfo = ({"doc": "A test tagprop doc."})
                    $lib.model.ext.addTagProp(score, (int, ({})), $tagpropinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                q = '''$lib.model.ext.addEdge(*, _does, *, ({}))'''
                await core.callStorm(q, opts=opts)

        # Reload the model extensions automatically
        async with self.getTestCore() as core:
            opts = {'vars': {'model_defs': model_defs}}
            q = '''return ($lib.model.ext.addExtModel($model_defs))'''
            self.true(await core.callStorm(q, opts))

            nodes = await core.nodes('[ _visi:int=10 :tick=20210101 ._woot=30 +#lol:score=99 ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_visi:int', 10))
            self.eq(nodes[0].get('tick'), 1609459200000)
            self.eq(nodes[0].get('._woot'), 30)
            self.eq(nodes[0].getTagProp('lol', 'score'), 99)

            nodes = await core.nodes('[test:int=1234 :_tick=20210101]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1234))
            self.eq(nodes[0].get('_tick'), 1609459200000)

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
                $lib.model.ext.addFormProp(_visi:int, tick, (time, ({})), $propinfo)

                $univinfo = ({"doc": "NEWP"})
                $lib.model.ext.addUnivProp(_woot, (int, ({})), $univinfo)

                $tagpropinfo = ({"doc": "NEWP"})
                $lib.model.ext.addTagProp(score, (int, ({})), $tagpropinfo)

                $pinfo = ({"doc": "NEWP"})
                $lib.model.ext.addFormProp(test:int, _tick, (time, ({})), $propinfo)

                $edgeinfo = ({"doc": "NEWP"})
                $lib.model.ext.addEdge(inet:user, _copies, *, $edgeinfo)
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
            with self.raises(s_exc.BadPropDef) as cm:
                opts = {'vars': {'model_defs': {'univs': model_defs['univs']}}}
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
            for ($prop, $def, $info) in $model_defs.univs {
                $lib.model.ext.addUnivProp($prop, $def, $info)
            }
            for ($edge, $info) in $model_defs.edges {
                ($n1form, $verb, $n2form) = $edge
                $lib.model.ext.addEdge($n1form, $verb, $n2form, $info)
            }
            '''
            await core.nodes(q, opts)

            nodes = await core.nodes('[ _visi:int=10 :tick=20210101 ._woot=30 +#lol:score=99 ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_visi:int', 10))
            self.eq(nodes[0].get('tick'), 1609459200000)
            self.eq(nodes[0].get('._woot'), 30)
            self.eq(nodes[0].getTagProp('lol', 'score'), 99)

            nodes = await core.nodes('[test:int=1234 :_tick=20210101]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1234))
            self.eq(nodes[0].get('_tick'), 1609459200000)

            self.nn(core.model.edge(('inet:user', '_copies', None)))

        # Property values left behind in layers are cleanly removed
        async with self.getTestCore() as core:
            await core.callStorm('''
                $typeinfo = ({})
                $docinfo = ({"doc": "NEWP"})
                $lib.model.ext.addUnivProp(_woot, (int, ({})), $docinfo)
                $lib.model.ext.addTagProp(score, (int, ({})), $docinfo)
                $lib.model.ext.addFormProp(test:int, _tick, (time, ({})), $docinfo)
            ''')
            fork = await core.callStorm('return ( $lib.view.get().fork().iden ) ')
            nodes = await core.nodes('[test:int=1234 :_tick=2024 ._woot=1 +#hehe:score=10]')
            self.len(1, nodes)
            self.eq(nodes[0].get('._woot'), 1)

            nodes = await core.nodes('test:int=1234 [:_tick=2023 ._woot=2 +#hehe:score=9]',
                                     opts={'view': fork})
            self.len(1, nodes)
            self.eq(nodes[0].get('._woot'), 2)

            self.len(0, await core.nodes('test:int | delnode'))

            with self.raises(s_exc.CantDelUniv):
                await core.callStorm('$lib.model.ext.delUnivProp(_woot)')
            with self.raises(s_exc.CantDelProp):
                await core.callStorm('$lib.model.ext.delFormProp(test:int, _tick)')
            with self.raises(s_exc.CantDelProp):
                await core.callStorm('$lib.model.ext.delTagProp(score)')

            await core.callStorm('$lib.model.ext.delUnivProp(_woot, force=(true))')
            await core.callStorm('$lib.model.ext.delFormProp(test:int, _tick, force=(true))')
            await core.callStorm('$lib.model.ext.delTagProp(score, force=(true))')

            nodes = await core.nodes('[test:int=1234]')
            self.len(1, nodes)
            self.none(nodes[0].get('._woot'))
            self.none(nodes[0].get('_tick'))
            nodes = await core.nodes('test:int=1234', opts={'view': fork})
            self.none(nodes[0].get('._woot'))
            self.none(nodes[0].get('_tick'))

    async def test_lib_stormlib_behold_modelext(self):
        self.skipIfNexusReplay()
        async with self.getTestCore() as core:
            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')
            await visi.setAdmin(True)

            async with self.getHttpSess() as sess:
                async with sess.post(f'https://localhost:{port}/api/v1/login', json={'user': 'visi', 'passwd': 'secret'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('visi', retn['result']['name'])

                async with sess.ws_connect(f'wss://localhost:{port}/api/v1/behold') as sock:
                    await sock.send_json({'type': 'call:init'})
                    mesg = await sock.receive_json()
                    self.eq(mesg['type'], 'init')

                    await core.callStorm('''
                        $lib.model.ext.addForm(_behold:score, int, ({}), ({"doc": "first string"}))
                        $lib.model.ext.addFormProp(_behold:score, rank, (int, ({})), ({"doc": "second string"}))
                        $lib.model.ext.addUnivProp(_beep, (int, ({})), ({"doc": "third string"}))
                        $lib.model.ext.addTagProp(thingy, (int, ({})), ({"doc": "fourth string"}))
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
                    self.eq(propmesg['data']['info']['prop']['full'], '_behold:score:rank')
                    self.eq(propmesg['data']['info']['prop']['name'], 'rank')
                    self.eq(propmesg['data']['info']['prop']['stortype'], 9)

                    univmesg = await sock.receive_json()
                    self.eq(univmesg['data']['event'], 'model:univ:add')
                    self.eq(univmesg['data']['info']['name'], '._beep')
                    self.eq(univmesg['data']['info']['full'], '._beep')
                    self.eq(univmesg['data']['info']['doc'], 'third string')

                    tagpmesg = await sock.receive_json()
                    self.eq(tagpmesg['data']['event'], 'model:tagprop:add')
                    self.eq(tagpmesg['data']['info']['name'], 'thingy')
                    self.eq(tagpmesg['data']['info']['info'], {'doc': 'fourth string'})

                    edgemesg = await sock.receive_json()
                    self.eq(edgemesg['data']['event'], 'model:edge:add')
                    self.eq(edgemesg['data']['info']['edge'], (None, '_goes', 'geo:place'))
                    self.eq(edgemesg['data']['info']['info'], {'doc': 'fifth string'})

                    await core.callStorm('''
                        $lib.model.ext.delTagProp(thingy)
                        $lib.model.ext.delUnivProp(_beep)
                        $lib.model.ext.delFormProp(_behold:score, rank)
                        $lib.model.ext.delForm(_behold:score)
                        $lib.model.ext.delEdge(*, _goes, geo:place)
                    ''')
                    deltagp = await sock.receive_json()
                    self.eq(deltagp['data']['event'], 'model:tagprop:del')
                    self.eq(deltagp['data']['info']['tagprop'], 'thingy')

                    deluniv = await sock.receive_json()
                    self.eq(deluniv['data']['event'], 'model:univ:del')
                    self.eq(deluniv['data']['info']['prop'], '._beep')

                    delprop = await sock.receive_json()
                    self.eq(delprop['data']['event'], 'model:prop:del')
                    self.eq(delprop['data']['info']['form'], '_behold:score')
                    self.eq(delprop['data']['info']['prop'], 'rank')

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
                $lib.model.ext.addFormProp(_visi:int, tick, (time, ({})), $propinfo)
            ''')

            self.nn(core.model.form('_visi:int'))
            self.nn(core.model.prop('_visi:int:tick'))

            q = '$lib.model.ext.delForm(_visi:int)'
            with self.raises(s_exc.CantDelForm) as exc:
                await core.callStorm(q)
            self.eq('Form has extended properties: tick', exc.exception.get('mesg'))

            await core.callStorm('$lib.model.ext.addFormProp(_visi:int, tock, (time, ({})), ({}))')

            self.nn(core.model.form('_visi:int'))
            self.nn(core.model.prop('_visi:int:tick'))
            self.nn(core.model.prop('_visi:int:tock'))

            q = '$lib.model.ext.delForm(_visi:int)'
            with self.raises(s_exc.CantDelForm) as exc:
                await core.callStorm(q)
            self.eq('Form has extended properties: tick, tock', exc.exception.get('mesg'))

            await core.callStorm('''
                $lib.model.ext.delFormProp(_visi:int, tick)
                $lib.model.ext.delFormProp(_visi:int, tock)
                $lib.model.ext.delForm(_visi:int)
            ''')

            self.none(core.model.form('_visi:int'))
            self.none(core.model.prop('_visi:int:tick'))
            self.none(core.model.prop('_visi:int:tock'))

    async def test_lib_stormlib_modelext_argtypes(self):
        '''
        Verify type checking of typedef and propdef arguments.
        '''

        vectors = (
            (
                '$lib.model.ext.addForm(inet:fqdn, _foo:bar, (guid, ()), ())',
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
                '$lib.model.ext.addUnivProp(_foo, ({}), ())',
                'Universal property type definitions should be a tuple.'
            ),
            (
                '$lib.model.ext.addUnivProp(_foo, (), ())',
                'Universal property definitions should be a dict.'
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
                $forminfo = ({"interfaces": ["test:interface"]})
                $lib.model.ext.addForm(_test:iface, str, ({}), $forminfo)
                $lib.model.ext.addFormProp(_test:iface, tick, (time, ({})), ({}))
            ''')

            self.nn(core.model.form('_test:iface'))
            self.nn(core.model.prop('_test:iface:flow'))
            self.nn(core.model.prop('_test:iface:proc'))
            self.nn(core.model.prop('_test:iface:tick'))
            self.isin('_test:iface', core.model.formsbyiface['test:interface'])
            self.isin('_test:iface', core.model.formsbyiface['inet:proto:request'])
            self.isin('_test:iface', core.model.formsbyiface['it:host:activity'])
            self.isin('_test:iface:flow', core.model.ifaceprops['inet:proto:request:flow'])
            self.isin('_test:iface:proc', core.model.ifaceprops['test:interface:proc'])
            self.isin('_test:iface:proc', core.model.ifaceprops['inet:proto:request:proc'])
            self.isin('_test:iface:proc', core.model.ifaceprops['it:host:activity:proc'])

            q = '$lib.model.ext.delForm(_test:iface)'
            with self.raises(s_exc.CantDelForm) as exc:
                await core.callStorm(q)
            self.eq('Form has extended properties: tick', exc.exception.get('mesg'))

            await core.callStorm('''
                $lib.model.ext.delFormProp(_test:iface, tick)
                $lib.model.ext.delForm(_test:iface)
            ''')

            self.none(core.model.form('_test:iface'))
            self.none(core.model.prop('_test:iface:flow'))
            self.none(core.model.prop('_test:iface:proc'))
            self.none(core.model.prop('_test:iface:tick'))
            self.notin('_test:iface', core.model.formsbyiface['test:interface'])
            self.notin('_test:iface', core.model.formsbyiface['inet:proto:request'])
            self.notin('_test:iface', core.model.formsbyiface['it:host:activity'])
            self.notin('_test:iface:flow', core.model.ifaceprops['inet:proto:request:flow'])
            self.notin('_test:iface:proc', core.model.ifaceprops['test:interface:proc'])
            self.notin('_test:iface:proc', core.model.ifaceprops['inet:proto:request:proc'])
            self.notin('_test:iface:proc', core.model.ifaceprops['it:host:activity:proc'])

            await core.stormlist('''
                $forminfo = ({"interfaces": ["newp"]})
                $lib.model.ext.addForm(_test:iface, str, ({}), $forminfo)
            ''')
            self.nn(core.model.form('_test:iface'))

            await core.callStorm('$lib.model.ext.delForm(_test:iface)')
            self.none(core.model.form('_test:iface'))
