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
                $lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $propinfo)

                $univinfo = ({"doc": "A test univ doc."})
                $lib.model.ext.addUnivProp(_woot, (int, $lib.dict()), $univinfo)

                $tagpropinfo = ({"doc": "A test tagprop doc."})
                $lib.model.ext.addTagProp(score, (int, $lib.dict()), $tagpropinfo)

                $pinfo = ({"doc": "Extended a core model."})
                $lib.model.ext.addFormProp(test:int, _tick, (time, $lib.dict()), $propinfo)
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

            with self.raises(s_exc.DupPropName):
                q = '''$lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.DupPropName):
                q = '''$lib.model.ext.addUnivProp(_woot, (time, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            # Grab the extended model definitions
            model_defs = await core.callStorm('return ( $lib.model.ext.getExtModel() )')
            self.isinstance(model_defs, dict)

            await core.callStorm('_visi:int=10 test:int=1234 | delnode')
            await core.callStorm('''
                $lib.model.ext.delTagProp(score)
                $lib.model.ext.delUnivProp(_woot)
                $lib.model.ext.delFormProp(_visi:int, tick)
                $lib.model.ext.delFormProp(test:int, _tick)
                $lib.model.ext.delForm(_visi:int)
            ''')

            self.none(core.model.form('_visi:int'))
            self.none(core.model.prop('._woot'))
            self.none(core.model.prop('_visi:int:tick'))
            self.none(core.model.prop('test:int:_tick'))
            self.none(core.model.tagprop('score'))

            # Underscores can exist in extended names but only at specific locations
            q = '''$l =$lib.list('str', $lib.dict()) $d=$lib.dict(doc="Foo")
            $lib.model.ext.addFormProp('test:str', '_test:_myprop', $l, $d)
            '''
            self.none(await core.callStorm(q))
            q = '$lib.model.ext.addUnivProp(_woot:_stuff, (int, $lib.dict()), $lib.dict())'
            self.none(await core.callStorm(q))

            q = '''$lib.model.ext.addTagProp(_score, (int, $lib.dict()), $lib.dict())'''
            self.none(await core.callStorm(q))

            q = '''$lib.model.ext.addTagProp(some:_score, (int, $lib.dict()), $lib.dict())'''
            self.none(await core.callStorm(q))

            with self.raises(s_exc.BadPropDef):
                q = '''$l =$lib.list('str', $lib.dict()) $d=$lib.dict(doc="Foo")
                $lib.model.ext.addFormProp('test:str', '_test:_my^prop', $l, $d)
                '''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$l =$lib.list('str', $lib.dict()) $d=$lib.dict(doc="Foo")
                $lib.model.ext.addFormProp('test:str', '_test::_myprop', $l, $d)
                '''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addUnivProp(_woot^stuff, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addUnivProp(_woot:_stuff^2, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addTagProp(some^score, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            with self.raises(s_exc.BadPropDef):
                q = '''$lib.model.ext.addTagProp(_someones:_score^value, (int, $lib.dict()), $lib.dict())'''
                await core.callStorm(q)

            # Permission errors
            visi = await core.auth.addUser('visi')
            opts = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $typeinfo = $lib.dict()
                    $forminfo = $lib.dict(doc="A test form doc.")
                    $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $propinfo = $lib.dict(doc="A test prop doc.")
                    $lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $propinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $univinfo = $lib.dict(doc="A test univ doc.")
                    $lib.model.ext.addUnivProp(".woot", (int, $lib.dict()), $univinfo)
                ''', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    $tagpropinfo = $lib.dict(doc="A test tagprop doc.")
                    $lib.model.ext.addTagProp(score, (int, $lib.dict()), $tagpropinfo)
                ''', opts=opts)

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
                $typeinfo = ({})
                $forminfo = ({"doc": "NEWP"})
                $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)

                $propinfo = ({"doc": "NEWP"})
                $lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $propinfo)

                $univinfo = ({"doc": "NEWP"})
                $lib.model.ext.addUnivProp(_woot, (int, $lib.dict()), $univinfo)

                $tagpropinfo = ({"doc": "NEWP"})
                $lib.model.ext.addTagProp(score, (int, $lib.dict()), $tagpropinfo)

                $pinfo = ({"doc": "NEWP"})
                $lib.model.ext.addFormProp(test:int, _tick, (time, $lib.dict()), $propinfo)
            ''')

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

        # Reload the model extensions from the dump by hand
        async with self.getTestCore() as core:
            opts = {'vars': {'model_defs': model_defs}}
            q = '''
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
                        $lib.model.ext.addForm(_behold:score, int, $lib.dict(), $lib.dict(doc="first string"))
                        $lib.model.ext.addFormProp(_behold:score, rank, (int, $lib.dict()), $lib.dict(doc="second string"))
                        $lib.model.ext.addUnivProp(_beep, (int, $lib.dict()), $lib.dict(doc="third string"))
                        $lib.model.ext.addTagProp(thingy, (int, $lib.dict()), $lib.dict(doc="fourth string"))
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

                    await core.callStorm('''
                        $lib.model.ext.delTagProp(thingy)
                        $lib.model.ext.delUnivProp(_beep)
                        $lib.model.ext.delFormProp(_behold:score, rank)
                        $lib.model.ext.delForm(_behold:score)
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

    async def test_lib_stormlib_modelext_delform(self):
        '''
        Verify extended forms can't be deleted if they have associated extended props
        '''

        async with self.getTestCore() as core:

            await core.callStorm('''
                $typeinfo = $lib.dict()
                $forminfo = $lib.dict(doc="A test form doc.")
                $lib.model.ext.addForm(_visi:int, int, $typeinfo, $forminfo)

                $propinfo = $lib.dict(doc="A test prop doc.")
                $lib.model.ext.addFormProp(_visi:int, tick, (time, $lib.dict()), $propinfo)
            ''')

            self.nn(core.model.form('_visi:int'))
            self.nn(core.model.prop('_visi:int:tick'))

            q = '$lib.model.ext.delForm(_visi:int)'
            with self.raises(s_exc.CantDelForm) as exc:
                await core.callStorm(q)
            self.eq('Form has extended properties: tick', exc.exception.get('mesg'))

            await core.callStorm('$lib.model.ext.addFormProp(_visi:int, tock, (time, $lib.dict()), $lib.dict())')

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
        )

        async with self.getTestCore() as core:

            for query, err in vectors:

                with self.raises(s_exc.BadArg) as exc:
                    await core.callStorm(query)
                self.eq(err, exc.exception.get('mesg'))
