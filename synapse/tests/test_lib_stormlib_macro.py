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

            msgs = await core.stormlist('macro.set hehe ${ inet:ipv4 -:asn=30 }')
            self.stormIsInPrint('Set macro: hehe', msgs)

            msgs = await core.stormlist('macro.get hehe')
            self.stormIsInPrint('inet:ipv4 -:asn=30', msgs)

            msgs = await core.stormlist('macro.del hehe')
            self.stormIsInPrint('Removed macro: hehe', msgs)

            self.none(await core.callStorm('return($lib.macro.get(hehe))'))
