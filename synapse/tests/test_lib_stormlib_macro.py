import synapse.exc as s_exc
import synapse.tests.utils as s_test

class MacroTest(s_test.SynTest):

    async def test_stormlib_macro(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}

            await core.nodes('[ inet:ipv4=1.2.3.4 ]')

            await core.callStorm('macro.set hehe ${ inet:ipv4 }')
            await core.callStorm('macro.set hoho "+#foo"')

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

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.macro.set(hehe, ${ inet:ipv6 })', opts=asvisi)

            # Maximum size a macro name can currently be.
            name = 'v' * 491
            q = '$lib.macro.set($name, ${ help }) return ( $lib.macro.get($name) )'
            mdef = await core.callStorm(q, opts={'vars': {'name': name}})
            self.eq(mdef.get('storm'), 'help')

            with self.raises(s_exc.BadArg):
                badname = 'v' * 492
                q = '$lib.macro.set($name, ${ help })'
                await core.nodes(q, opts={'vars': {'name': badname}})

            msgs = await core.stormlist('macro.set hehe ${ inet:ipv4 -:asn=30 }')
            self.stormIsInPrint('Set macro: hehe', msgs)

            msgs = await core.stormlist('macro.get hehe')
            self.stormIsInPrint('inet:ipv4 -:asn=30', msgs)

            msgs = await core.stormlist('macro.del hehe')
            self.stormIsInPrint('Removed macro: hehe', msgs)

            self.none(await core.callStorm('return($lib.macro.get(hehe))'))

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
            q = 'macro.set data2 ${ $data=$lib.dict(value=beef) [test:str=$data.value +#cool.story] }'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('Set macro: data2', msgs)

            data = {'value': 'otherstuff'}
            q = 'macro.exec data2'
            nodes = await core.nodes(q, opts={'vars': {'data': data}})
            self.len(1, nodes)
            self.eq(('test:str', 'beef'), nodes[0].ndef)
