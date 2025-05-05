import os

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.hashset as s_hashset

import synapse.tests.utils as s_test

class UtilsTest(s_test.SynTest):

    async def test_lib_stormlib_utils_todo(self):

        async with self.getTestCore() as core:

            valu = await core.callStorm('return($lib.utils.todo(foo))')
            self.eq(valu, ('foo', (), {}))

            valu = await core.callStorm('return($lib.utils.todo(fooName, arg1, arg2, keyword=bar, anotherkeyword=hehe))')
            self.eq(valu, ('fooName', ('arg1', 'arg2'), {'keyword': 'bar', 'anotherkeyword': 'hehe'}))

    async def test_lib_stormlib_utils_tofile(self):
        data = os.urandom(128)
        hashset = s_hashset.HashSet()
        hashset.update(data)

        hashes = dict(hashset.digests())

        sha256b = hashes.get('sha256')
        sha256 = s_common.ehex(sha256b)

        async with self.getTestCore() as core:
            # Create a file:bytes node from bytes

            self.false(await core.axon.has(sha256b))

            opts = {'vars': {'data': data}}
            nodes = await core.nodes('yield $lib.utils.tofile($data)', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('file:bytes', f'sha256:{sha256}'))

            for hashname in ('md5', 'sha1', 'sha256', 'sha512'):
                hashvalu = nodes[0].get(hashname)
                self.nn(hashvalu)
                self.eq(nodes[0].get(hashname), s_common.ehex(hashes.get(hashname)))

            self.true(await core.axon.has(sha256b))

            valu = b''
            async for byts in core.axon.get(sha256b):
                valu += byts

            self.eq(valu, data)

        async with self.getTestCore() as core:
            # Update/link a file:bytes node with bytes

            opts = {'vars': {'sha256': sha256}}
            nodes = await core.nodes('[ file:bytes=$sha256 ]', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('file:bytes', f'sha256:{sha256}'))
            self.eq(nodes[0].get('sha256'), sha256)
            self.none(nodes[0].get('md5'))
            nid = nodes[0].nid

            opts = {'vars': {'data': data}}
            nodes = await core.nodes('yield $lib.utils.tofile($data)', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('file:bytes', f'sha256:{sha256}'))
            self.eq(nodes[0].get('sha256'), sha256)
            self.eq(nodes[0].get('md5'), s_common.ehex(hashes.get('md5')))
            self.eq(nodes[0].nid, nid)

        async with self.getTestCore() as core:
            # Verify permission checks

            layriden = core.view.layers[0].iden
            lowuser = await core.auth.addUser('lowuser')

            opts = {
                'user': lowuser.iden,
                'vars': {'data': data}
            }

            with self.raises(s_exc.AuthDeny) as exc:
                await core.nodes('yield $lib.utils.tofile($data)', opts=opts)

            mesg = f"User 'lowuser' ({lowuser.iden}) must have permission axon.upload"
            self.eq(exc.exception.get('mesg'), mesg)

            await lowuser.allow(('axon', 'upload'))

            with self.raises(s_exc.AuthDeny) as exc:
                await core.nodes('yield $lib.utils.tofile($data)', opts=opts)

            mesg = f"User 'lowuser' ({lowuser.iden}) must have permission node.add.file:bytes on object {layriden} (layer)."
            self.eq(exc.exception.get('mesg'), mesg)

            await lowuser.allow(('node', 'add', 'file:bytes'))

            with self.raises(s_exc.AuthDeny) as exc:
                await core.nodes('yield $lib.utils.tofile($data)', opts=opts)

            mesg = f"User 'lowuser' ({lowuser.iden}) must have permission node.prop.set.file:bytes on object {layriden} (layer)."
            self.eq(exc.exception.get('mesg'), mesg)

            await lowuser.allow(('node', 'prop', 'set', 'file:bytes'))

            opts = {
                'user': lowuser.iden,
                'vars': {'data': data}
            }
            nodes = await core.nodes('yield $lib.utils.tofile($data)', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('file:bytes', f'sha256:{sha256}'))
