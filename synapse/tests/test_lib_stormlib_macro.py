import synapse.exc as s_exc
import synapse.tests.utils as s_test

class MacroTest(s_test.SynTest):

    async def test_stormlib_macro(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}

            await core.nodes('[ inet:ipv4=1.2.3.4 ]')

            msgs = await core.stormlist('macro.set hehe ${ inet:ipv4 }')
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('macro.set hoho "+#foo"')
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('macro.list')

            self.stormIsInPrint('hehe', msgs)
            self.stormIsInPrint('hoho', msgs)
            self.stormIsInPrint('root', msgs)
            self.stormIsInPrint('2 macros found', msgs)

            nodes = await core.nodes('macro.exec hehe', opts=asvisi)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('$name="hehe" | macro.exec $name',)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('macro.exec hehe | macro.exec hoho', opts=asvisi)
            self.len(0, nodes)

            await core.nodes('macro.set bam ${ [ +#foo ] }')
            nodes = await core.nodes('inet:ipv4 | macro.exec bam')
            self.len(1, nodes)
            self.isin('foo', [t[0] for t in nodes[0].getTags()])

            self.len(1, await core.nodes('inet:ipv4 | macro.exec hoho'))

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('[ test:str=hehe ] $name=$node.value() | macro.exec $name')

            with self.raises(s_exc.NoSuchName):
                await core.nodes('macro.exec newp')

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.macro.del(haha)')

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.macro.del(hehe)', opts=asvisi)

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.macro.set("", ${ inet:ipv4 })')

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.macro.get("")')

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.macro.del("")')

            with self.raises(s_exc.BadArg):
                await core.delStormMacro('', user=None)

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.macro.grant("", users, hehe, 3)')

            with self.raises(s_exc.SchemaViolation):
                await core.nodes('$lib.macro.mod("hehe", ({"name": ""}))')

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.macro.mod("", ({"name": "foobar"}))')

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.macro.set(hehe, ${ inet:ipv6 })', opts=asvisi)

            await core.addStormMacro({'name': 'foo', 'storm': '$lib.print(woot)'})

            with self.raises(s_exc.BadArg):
                await core.addStormMacro({'name': 'foo', 'storm': '$lib.print(woot)'})

            with self.raises(s_exc.DupName):
                await core.modStormMacro('foo', {'name': 'hehe'})

            # Maximum size a macro name can currently be.
            name = 'v' * 491
            q = '$lib.macro.set($name, ${ help }) return ( $lib.macro.get($name) )'
            mdef = await core.callStorm(q, opts={'vars': {'name': name}})
            self.eq(mdef.get('storm'), ' help ')

            badname = 'v' * 492
            with self.raises(s_exc.BadArg):
                q = '$lib.macro.set($name, ${ help })'
                await core.nodes(q, opts={'vars': {'name': badname}})

            with self.raises(s_exc.BadArg):
                q = '$lib.macro.get($name)'
                await core.nodes(q, opts={'vars': {'name': badname}})

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.macro.mod(foo, bar)', opts=asvisi)

            msgs = await core.stormlist('macro.set hehe ${ inet:ipv4 -:asn=30 }')
            self.stormIsInPrint('Set macro: hehe', msgs)

            msgs = await core.stormlist('macro.get hehe')
            self.stormIsInPrint('inet:ipv4 -:asn=30', msgs)

            msgs = await core.stormlist('macro.del hehe')
            self.stormIsInPrint('Removed macro: hehe', msgs)

            self.none(await core.callStorm('return($lib.macro.get(hehe))'))

            # readonly tests
            msgs = await core.stormlist('macro.set print { $lib.print("macro has words") }')
            self.stormHasNoWarnErr(msgs)
            msgs = await core.stormlist('macro.set node { [test:guid=*] }')
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('macro.exec print', opts={'readonly': True})
            self.stormIsInPrint('macro has words', msgs)

            msgs = await core.stormlist('macro.exec node', opts={'readonly': True})
            self.stormIsInErr('runtime is in readonly mode', msgs)
            self.len(0, await core.nodes('test:guid'))

            msgs = await core.stormlist('macro.list', opts={'readonly': True})
            self.stormIsInPrint('node', msgs)
            self.stormIsInPrint('print', msgs)
            msgs = await core.stormlist('macro.get print', opts={'readonly': True})
            self.stormIsInPrint('$lib.print("macro', msgs)

            msgs = await core.stormlist('macro.set newp { }', opts={'readonly': True})
            self.stormIsInErr('not marked readonly safe', msgs)

            msgs = await core.stormlist('macro.del print', opts={'readonly': True})
            self.stormIsInErr('not marked readonly safe', msgs)

            msgs = await core.stormlist('macro.set blorpblorp "+#foo"', opts=asvisi)
            self.stormHasNoWarnErr(msgs)

            await core.auth.delUser(visi.iden)
            msgs = await core.stormlist('macro.list')
            self.stormIsInPrint("User not found", msgs)
            self.stormIsInPrint(visi.iden, msgs)

    async def test_stormlib_macro_vars(self):

        async with self.getTestCore() as core:

            # Make a macro that operates on a variable to make a node
            q = 'macro.set data ${ [test:str=$data.value +#cool.story ] }'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('Set macro: data', msgs)

            data = {'value': 'stuff'}
            q = 'macro.exec data'
            nodes = await core.nodes(q, opts={'vars': {'data': data}})
            self.len(1, nodes)
            self.eq(('test:str', 'stuff'), nodes[0].ndef)

            q = 'macro.set data3 ${ [test:str=$val] }'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('Set macro: data3', msgs)

            q = '[test:str=cat] $val=$node.value() | macro.exec data3'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq({'cat'}, {n.ndef[1] for n in nodes})

            q = '[test:str=cat] $val=cool | macro.exec data3'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq({'cool', 'cat'}, {n.ndef[1] for n in nodes})

            q = '$val=cooler macro.exec data3'
            nodes = await core.nodes(q)
            self.eq([('test:str', 'cooler')], [n.ndef for n in nodes])

            # Inner vars win on conflict
            q = 'macro.set data2 ${ $data=({"value": "beef"}) [test:str=$data.value +#cool.story] }'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('Set macro: data2', msgs)

            data = {'value': 'otherstuff'}
            q = 'macro.exec data2'
            nodes = await core.nodes(q, opts={'vars': {'data': data}})
            self.len(1, nodes)
            self.eq(('test:str', 'beef'), nodes[0].ndef)

    async def test_stormlib_macro_meta_and_perms(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            asvisi = {'user': visi.iden}

            msgs = await core.stormlist('macro.set foo {$lib.print(woot)}')
            self.stormHasNoWarnErr(msgs)

            mdef = await core.callStorm('return( $lib.macro.get(foo) )')
            self.eq(mdef.get('creator'), core.auth.rootuser.iden)

            msgs = await core.stormlist('macro.list', opts=asvisi)
            self.stormIsInPrint('foo', msgs)

            msgs = await core.stormlist('$lib.macro.grant(foo, users, hehe, 3)')
            self.stormIsInErr('No user with iden hehe', msgs)

            msgs = await core.stormlist('$lib.macro.grant(foo, roles, hehe, 3)')
            self.stormIsInErr('No role with iden hehe', msgs)

            msgs = await core.stormlist('$lib.macro.grant(foo, newp, hehe, 3)')
            self.stormIsInErr('Invalid permissions scope: newp', msgs)

            msgs = await core.stormlist('$lib.macro.grant(foo, users, hehe, 4)')
            self.stormIsInErr('Invalid permission level: 4 (must be <= 3 and >= 0, or None)', msgs)

            self.raises(s_exc.BadArg, core._hasEasyPerm, {}, 'newp', 4)

            opts = {'user': visi.iden, 'vars': {'visi': visi.iden}}
            msgs = await core.stormlist('$lib.macro.grant(foo, users, $visi, 3)', opts=opts)
            self.stormIsInErr('User requires admin permission on macro: foo', msgs)

            macros = await core.callStorm('return($lib.macro.list())', opts=asvisi)
            self.len(1, macros)

            opts = {'vars': {'visi': visi.iden}}
            msgs = await core.stormlist('$lib.macro.grant(foo, users, $visi, 0)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            macros = await core.callStorm('return($lib.macro.list())', opts=asvisi)
            self.len(0, macros)

            await self.asyncraises(s_exc.AuthDeny, core.nodes('$lib.macro.get(foo)', opts=asvisi))

            opts = {'vars': {'visi': visi.iden}}
            msgs = await core.stormlist('$lib.macro.grant(foo, users, $visi, $lib.null)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            macros = await core.callStorm('return($lib.macro.list())', opts=asvisi)
            self.len(1, macros)

            # remove global read access from the macro
            opts = {'vars': {'allrole': core.auth.allrole.iden}}
            msgs = await core.stormlist('$lib.macro.grant(foo, roles, $allrole, 0)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            macros = await core.callStorm('return($lib.macro.list())', opts=asvisi)
            self.len(0, macros)

            opts = {'vars': {'allrole': core.auth.allrole.iden}}
            msgs = await core.stormlist('$lib.macro.grant(foo, roles, $allrole, $lib.null)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            macros = await core.callStorm('return($lib.macro.list())', opts=asvisi)
            self.len(1, macros)

            msgs = await core.stormlist('$lib.macro.mod(foo, ({"desc": "i am a macro!"}))', opts=asvisi)
            self.stormIsInErr('User requires edit permission on macro: foo', msgs)

            opts = {'vars': {'visi': visi.iden}}
            msgs = await core.stormlist('$lib.macro.grant(foo, users, $visi, 2)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('$lib.macro.mod(foo, ({"desc": "i am a macro!"}))', opts=asvisi)
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('$lib.macro.mod(foo, ({"newp": "i am a macro!"}))', opts=asvisi)
            self.stormIsInErr('User may not edit the field: newp', msgs)

            mdef = await core.callStorm('return($lib.macro.get(foo))')
            self.eq(mdef['desc'], 'i am a macro!')

            msgs = await core.stormlist('$lib.macro.mod(foo, ({"name": "bar"}))', opts=asvisi)
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('$lib.macro.mod(bar, ({"storm": "$lib.print(woot)"}))', opts=asvisi)
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('$lib.macro.mod(bar, ({"storm": " | | | "}))', opts=asvisi)
            self.stormIsInErr('Unexpected token', msgs)

            self.nn(await core.callStorm('return($lib.macro.get(bar))'))
            self.none(await core.callStorm('return($lib.macro.get(foo))'))

            msgs = await core.stormlist('$lib.macro.del(bar)', opts=asvisi)
            self.stormIsInErr('User requires admin permission on macro: bar', msgs)

            opts = {'vars': {'allrole': core.auth.allrole.iden}}
            msgs = await core.stormlist('$lib.macro.grant(bar, roles, $allrole, 3)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('$lib.macro.del(bar)', opts=asvisi)
            self.stormHasNoWarnErr(msgs)

            self.none(await core.callStorm('return($lib.macro.get(bar))'))

            # Non-admin can create / delete their own macro
            msgs = await core.stormlist('macro.set vmac { $lib.print(woot) }', opts=asvisi)
            self.stormIsInPrint('Set macro: vmac', msgs)

            mdef = await core.callStorm('return( $lib.macro.get(vmac) )')
            self.eq(mdef.get('creator'), visi.iden)

            await core.callStorm('return ( $lib.macro.del(vmac) )', opts=asvisi)
            self.none(await core.callStorm('return( $lib.macro.get(vmac) )', opts=asvisi))

            # Invalid macro names
            opts = {'vars': {'aaaa': 'A' * 512}}
            msgs = await core.stormlist('macro.set $aaaa {$lib.print(hi)}', opts=opts)
            self.stormIsInErr('Macro names may only be up to 491 chars.', msgs)

            msgs = await core.stormlist('$lib.macro.del($aaaa)', opts=opts)
            self.stormIsInErr('Macro names may only be up to 491 chars.', msgs)

            msgs = await core.stormlist('$lib.macro.set($aaaa, hi)', opts=opts)
            self.stormIsInErr('Macro names may only be up to 491 chars.', msgs)

            msgs = await core.stormlist('$lib.macro.mod($aaaa, ({"desc": "woot"}))', opts=opts)
            self.stormIsInErr('Macro names may only be up to 491 chars.', msgs)

            msgs = await core.stormlist('$lib.macro.grant($aaaa, users, woot, 10)', opts=opts)
            self.stormIsInErr('Macro names may only be up to 491 chars.', msgs)

    async def test_stormlib_macro_globalperms(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('macro.set asdf {inet:fqdn}')
            self.stormHasNoWarnErr(msgs)

            visi = await core.auth.addUser('visi')
            msgs = await core.stormlist('macro.set asdf {inet:ipv4}', opts={'user': visi.iden})
            self.stormIsInErr('User requires edit permission on macro: asdf', msgs)

            await visi.addRule((True, ('storm', 'macro', 'edit')))
            msgs = await core.stormlist('macro.set asdf {inet:ipv4}', opts={'user': visi.iden})
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('macro.del asdf', opts={'user': visi.iden})
            self.stormIsInErr('User requires admin permission on macro: asdf', msgs)

            await visi.addRule((True, ('storm', 'macro', 'admin')))
            msgs = await core.stormlist('macro.del asdf', opts={'user': visi.iden})
            self.stormHasNoWarnErr(msgs)

    async def test_stormlib_behold_macro(self):
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
                        $lib.macro.set('foobar', ${ file:bytes | [+#neato] })
                        $lib.macro.set('foobar', ${ inet:ipv4 | [+#burrito] })
                        $lib.macro.mod('foobar', ({'name': 'bizbaz'}))
                        $lib.macro.grant('bizbaz', users, $visi, 3)
                        $lib.macro.del('bizbaz')
                    ''', opts={'vars': {'visi': visi.iden}})

                    addmesg = await sock.receive_json()
                    self.eq('storm:macro:add', addmesg['data']['event'])
                    macro = addmesg['data']['info']['macro']
                    self.eq(macro['name'], 'foobar')
                    self.eq(macro['storm'], ' file:bytes | [+#neato] ')
                    self.ne(visi.iden, macro['user'])
                    self.ne(visi.iden, macro['creator'])
                    self.nn(macro['iden'])

                    setmesg = await sock.receive_json()
                    self.eq('storm:macro:mod', setmesg['data']['event'])
                    event = setmesg['data']['info']
                    self.nn(event['macro'])
                    self.eq(event['info']['storm'], ' inet:ipv4 | [+#burrito] ')
                    self.nn(event['info']['updated'])

                    modmesg = await sock.receive_json()
                    self.eq('storm:macro:mod', modmesg['data']['event'])
                    event = modmesg['data']['info']
                    self.nn(event['macro'])
                    self.eq(event['info']['name'], 'bizbaz')
                    self.nn(event['info']['updated'])

                    grantmesg = await sock.receive_json()
                    self.eq('storm:macro:set:perm', grantmesg['data']['event'])
                    event = grantmesg['data']['info']
                    self.nn(event['macro'])
                    self.eq(event['info']['level'], 3)
                    self.eq(event['info']['scope'], 'users')
                    self.eq(event['info']['iden'], visi.iden)

                    delmesg = await sock.receive_json()
                    self.eq('storm:macro:del', delmesg['data']['event'])
                    event = delmesg['data']['info']
                    self.nn(event['iden'])
                    self.eq(event['name'], 'bizbaz')
