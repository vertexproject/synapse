import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.layer as s_layer
import synapse.lib.editor as s_editor

import synapse.tests.utils as s_t_utils

class EditorTest(s_t_utils.SynTest):

    async def test_migration_editor(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:url="https://visi@vertex.link:81/x?a=1" inet:ip=1.2.3.4 ]')

            layr = core.view.layers[0]

            newlayr = core.getLayer((await core.addLayer())['iden'])

            editor = s_editor.MigrationEditor(core, core.auth.rootuser)

            # an existing node still gets its node add and every computed prop
            nodeedits = await editor.getNewNodeEdits('inet:url', 'https://visi@vertex.link:81/x?a=1')
            self.eq({}, editor.protonodes)

            (nid, form, edits) = nodeedits[0]
            self.eq(s_common.int64un(core.getNidByNdef(('inet:url', 'https://visi@vertex.link:81/x?a=1'))), nid)
            self.eq('inet:url', form)
            self.eq(s_layer.EDIT_NODE_ADD, edits[0][0])

            props = {edit[0]: edit[1] for (etyp, edit) in edits if etyp == s_layer.EDIT_PROP_SET}
            self.eq(('inet:fqdn', 'vertex.link'), props['host'])
            self.eq(('inet:port', 81), props['port'])
            self.eq(('entity:name', 'visi'), props['username'])
            self.eq(('str', '?a=1'), props['params'])

            # the nodes its value adds are not resolved against the view either
            fqdnnid = s_common.int64un(core.getNidByNdef(('inet:fqdn', 'vertex.link')))
            self.eq([(fqdnnid, 'inet:fqdn')], [ne[:2] for ne in nodeedits[1:]])
            self.eq(s_layer.EDIT_NODE_ADD, nodeedits[1][2][0][0])

            # a layer which already holds them leaves them out, an empty one does not
            nodeedits = await editor.getNewNodeEdits('inet:url', 'https://1.2.3.4/y')
            self.eq(['inet:url', 'inet:ip'], [ne[1] for ne in nodeedits])
            self.eq(s_common.int64un(core.getNidByNdef(('inet:ip', (4, 0x01020304)))), nodeedits[1][0])

            nodeedits = await editor.getNewNodeEdits('inet:url', 'https://1.2.3.4/y', layr=layr)
            self.eq([(None, 'inet:url')], [ne[:2] for ne in nodeedits])

            nodeedits = await editor.getNewNodeEdits('inet:url', 'https://1.2.3.4/y', layr=newlayr)
            self.eq(['inet:url', 'inet:ip'], [ne[1] for ne in nodeedits])

            # a value new to the cortex has no nid yet
            nodeedits = await editor.getNewNodeEdits('inet:url', 'https://5.6.7.8/z', layr=newlayr)
            self.eq([(None, 'inet:url'), (None, 'inet:ip')], [ne[:2] for ne in nodeedits])

            with self.raises(s_exc.NoSuchForm):
                await editor.getNewNodeEdits('newp:newp', 'newp')

            with self.raises(s_exc.BadTypeValu):
                await editor.getNewNodeEdits('inet:url', 'newp')

            self.eq({}, editor.protonodes)

            # nothing was saved
            self.len(1, await core.nodes('inet:url'))
            self.len(1, await core.nodes('inet:ip'))
