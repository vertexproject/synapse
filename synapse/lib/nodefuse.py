'''
Cortex wide fusion of one node into another.
'''
import asyncio
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.types as s_types
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

# Once a single fuse has queued this many edits we flush early. This gives up per-layer
# atomicity, so it is warned about rather than done silently.
maxlayeredits = 100000

# stortypes which _editPropSet/_editTagPropSet union with the existing value rather than
# overwrite it. Those are always transferred so the storage layer can merge them; every
# other stortype is a plain overwrite, so dst's existing value wins on conflict.
mergetypes = (s_layer.STOR_TYPE_IVAL, s_layer.STOR_TYPE_MINTIME, s_layer.STOR_TYPE_MAXTIME)

class NodeFuser:
    '''
    Fuse a source node into a destination node across every layer in a Cortex.

    Rather than iterating views, this iterates layers. A view is a list of layers, so
    covering every layer covers every view, including views the caller cannot read and
    views which do not exist yet. It also means a layer shared by several views is only
    processed once.

    Within each layer the source node's state is transferred to the destination node's
    buid *in that same layer*, so properties stay in the layer they were written to.
    Inbound references are rewritten in the layer which holds them, and the source is
    then deleted from every writable layer which held it.

    NOTE: This is logically a single operation but it is not transactional across layers.
          Each layer is its own nexus Pusher, so the edits for each layer are atomic and
          replicated individually. Every edit is expressed as "dst gains X" or "src loses
          X" and the storage layer no-ops edits which have already been applied, so
          re-running a fuse which was interrupted will complete it.
    '''

    def __init__(self, core, useriden, warn=None, maxedits=None):

        self.core = core
        self.model = core.model
        self.useriden = useriden

        if maxedits is None:
            maxedits = maxlayeredits

        self.maxedits = maxedits

        self._warnfunc = warn

        self.meta = {'time': s_common.now(), 'user': useriden}

        self.layers = []        # the layers we may write to
        self.layridens = set()

        self.sodes = {}         # buid -> {layriden: sode} as of before any edits
        self.newbuids = set()   # buids which this fuse creates
        self.visited = set()    # src buids which have already been fused
        self.failed = []        # (layriden, mesg) for each layer which failed

        self.degraded = False

    async def warn(self, mesg):
        logger.warning(mesg)
        if self._warnfunc is not None:
            await self._warnfunc(mesg)

    async def _getSodes(self, buid):
        '''
        Return (and cache) a {layriden: sode} mapping for the given buid.

        The cache means these reflect the state from before any edits were applied, which
        is what the trigger dispatch in phase two needs to rebuild a deleted node.
        '''
        sodes = self.sodes.get(buid)
        if sodes is None:
            sodes = self.sodes[buid] = {}
            for layer in self.core.layers.values():
                sode = await layer.getStorNode(buid)
                if sode:
                    sodes[layer.iden] = sode

        return sodes

    async def _getFormName(self, buid):
        '''
        Return the form name for a buid by checking each layer which holds state for it.
        '''
        for sode in (await self._getSodes(buid)).values():
            formname = sode.get('form')
            if formname is not None:
                return formname

        return None  # pragma: no cover

    def _hasNdef(self, buid, layers):
        '''
        Return True if any of the given layers holds the primary property for buid.
        '''
        sodes = self.sodes.get(buid, {})
        for layer in layers:
            if sodes.get(layer.iden, {}).get('valu') is not None:
                return True

        return False

    async def fuse(self, srcndef, dstndef):
        '''
        Fuse the src node into the dst node across every layer in the Cortex.

        Args:
            srcndef (tuple): The (form, valu) of the node to fuse from. It will be deleted.
            dstndef (tuple): The (form, valu) of the node to fuse into. It will be kept.

        Returns:
            None
        '''
        self.layers = []
        self.layridens = set()

        # A read-only layer cannot be written to, and a mirrored layer would forward our
        # edits to its upstream. Both are skipped, and _fuseOne() warns for each one which
        # actually held any of src's state.
        for layer in self.core.layers.values():

            if layer.readonly or layer.ismirror:
                continue

            self.layers.append(layer)
            self.layridens.add(layer.iden)

        batch = s_layer.LayerEditBatch(self.core, self.meta)

        applied = {}

        todo = collections.deque()
        todo.append((srcndef, dstndef, None))

        while todo:

            (nextsrc, nextdst, subs) = todo.popleft()

            srcbuid = s_common.buid(nextsrc)
            if srcbuid in self.visited:
                continue

            self.visited.add(srcbuid)

            todo.extend(await self._fuseOne(nextsrc, nextdst, subs, batch))

            if batch.size() >= self.maxedits:

                if not self.degraded:
                    self.degraded = True
                    await self.warn(
                        f'$lib.model.migration.fuse() exceeded {self.maxedits} queued edits and must '
                        f'flush early. The edits for each layer will span several transactions, so '
                        f'they are no longer atomic per layer. Re-run fuse() with the same arguments '
                        f'if it is interrupted.')

                self._addApplied(applied, await self._flush(batch))

        self._addApplied(applied, await self._flush(batch))

        await self._runConsequences(applied)

        if self.failed:
            mesg = '$lib.model.migration.fuse() failed to apply edits to some layers: '
            mesg += ', '.join([f'{iden} ({errm})' for iden, errm in self.failed])
            raise s_exc.SynErr(mesg=mesg, layers=[iden for iden, _ in self.failed])

    async def _runConsequences(self, applied):
        '''
        Fire the trigger consequences of the applied edits, once per affected view.

        A layer may be part of several views, and a view may include several of the layers
        we wrote to, so the edits are inverted to a per-view set and coalesced per buid.
        Each view then decides which of them are actually observable there.
        '''
        byview = {}

        for layriden, changes in applied.items():

            for view in self.core.viewsbylayer[layriden]:

                entry = byview.get(view.iden)
                if entry is None:
                    entry = byview[view.iden] = (view, {}, set())

                (_, nodeedits, seen) = entry

                for (buid, formname, edits) in changes:

                    nodeedit = nodeedits.get(buid)
                    if nodeedit is None:
                        nodeedit = nodeedits[buid] = (buid, formname, [])

                    for edit in edits:
                        # the same edit may have been applied to more than one of this
                        # view's layers, but it is only observable here once
                        key = (buid, s_msgpack.en(edit))
                        if key in seen:
                            continue

                        seen.add(key)
                        nodeedit[2].append(edit)

        for (view, nodeedits, _) in byview.values():

            flatedits = [nodeedit for nodeedit in nodeedits.values() if nodeedit[2]]
            if not flatedits:  # pragma: no cover
                continue

            # which of the nodes we created were not already visible in this view?
            added = set([buid for buid in self.newbuids if not self._hasNdef(buid, view.layers)])

            await view.runNodeEdits(flatedits, self.useriden, added=added, sodecache=self.sodes)

    def _addApplied(self, applied, flushed):
        for layriden, changes in flushed.items():
            applied.setdefault(layriden, []).extend(changes)

    async def _flush(self, batch):
        '''
        Flush the batch, warning about (and recording) any layer which fails.
        '''
        retn = {}

        # flush one layer at a time so that one failing layer cannot lose the others
        for layriden, layredits in batch.popLayerEdits().items():

            layer = self.core.getLayer(layriden)
            if layer is None:  # pragma: no cover
                continue

            try:
                _, changes = await layer.saveNodeEdits(list(layredits.values()), self.meta)

            except asyncio.CancelledError:  # pragma: no cover
                raise

            except Exception as e:
                errm = str(e)
                self.failed.append((layriden, errm))
                await self.warn(
                    f'$lib.model.migration.fuse() failed to apply edits to layer {layriden}: {errm}. '
                    f'That layer was not modified. Re-run fuse() with the same arguments to complete it.')
                continue

            changes = [change for change in changes if change[2]]
            if changes:
                retn[layriden] = changes

        return retn

    async def _fuseOne(self, srcndef, dstndef, subs, batch):
        '''
        Queue the edits which fuse one src node into one dst node in every writable layer.

        Returns:
            list: Additional (srcndef, dstndef, subs) tasks discovered for comp renames.
        '''
        formname = srcndef[0]
        form = self.model.reqForm(formname)
        stortype = form.type.stortype

        srcbuid = s_common.buid(srcndef)
        dstbuid = s_common.buid(dstndef)

        srcsodes = await self._getSodes(srcbuid)
        dstsodes = await self._getSodes(dstbuid)

        srciden = s_common.ehex(srcbuid)
        dstiden = s_common.ehex(dstbuid)

        # dst gets a node add in each layer which holds src, so it is a candidate for a
        # node:add consequence in any view where it was not already visible. Which views
        # those are is decided per view in _runConsequences().
        self.newbuids.add(dstbuid)

        # a destination which does not exist in any layer yet is one we are creating, so
        # it needs its read only properties filled in
        isnew = not any([sode.get('valu') is not None for sode in dstsodes.values()])

        # warn about any layer holding src which we are not allowed to modify
        for layriden in srcsodes.keys():

            if layriden in self.layridens:
                continue

            layer = self.core.getLayer(layriden)
            why = 'read only' if layer.readonly else 'a mirror'

            await self.warn(
                f'$lib.model.migration.fuse() cannot modify layer {layriden} because it is {why}. '
                f'{formname}={srcndef[1]!r} will not be removed from it, and will still be visible '
                f'in any view which includes that layer.')

        todo = []

        for layer in self.layers:

            layriden = layer.iden

            srcsode = srcsodes.get(layriden, {})
            dstsode = dstsodes.get(layriden, {})

            nodedata = [item async for item in layer.iterNodeData(srcbuid)]
            n1edges = [item async for item in layer.iterNodeEdgesN1(srcbuid)]
            n2edges = [item async for item in layer.iterNodeEdgesN2(srcbuid)]

            if not srcsode and not nodedata and not n1edges and not n2edges:
                continue

            hasndef = srcsode.get('valu') is not None

            # 1. create dst in the same layer that src lives in. this must precede any
            #    prop sets, otherwise the sode has props but no valu, which reads as a
            #    node which does not exist.
            if hasndef:

                batch.addEdit(layriden, dstbuid, formname, (
                    (s_layer.EDIT_NODE_ADD, (dstndef[1], stortype), ()),
                ))

                if isnew:
                    # a freshly created node needs its read only subs, which are derived
                    # from its own primary value rather than copied from src.
                    if subs is not None:
                        for name, valu in subs.items():

                            prop = form.props.get(name)
                            if prop is None:  # pragma: no cover
                                continue

                            batch.addEdit(layriden, dstbuid, formname, (
                                (s_layer.EDIT_PROP_SET, (name, valu, None, prop.type.stortype), ()),
                            ))

                    # .created is read only, so carry src's over when creating the node
                    created = srcsode.get('props', {}).get('.created')
                    if created is not None:
                        batch.addEdit(layriden, dstbuid, formname, (
                            (s_layer.EDIT_PROP_SET, ('.created', created[0], None, created[1]), ()),
                        ))

            # 2. transfer props, tags, tagprops and node data. dst is the survivor, so its
            #    existing value wins wherever both nodes hold a conflicting value in this
            #    layer. ival/mintime/maxtime values are unioned by the storage layer rather
            #    than overwritten, so those are always transferred regardless of conflict.
            dstprops = dstsode.get('props', {})

            for name, (valu, stype) in srcsode.get('props', {}).items():

                prop = form.props.get(name)
                if prop is None:  # pragma: no cover
                    continue

                # read only props on dst are derived from dst's own primary value. .created
                # is read only and is handled above.
                if prop.info.get('ro'):
                    continue

                if stype not in mergetypes and name in dstprops:
                    continue

                batch.addEdit(layriden, dstbuid, formname, (
                    (s_layer.EDIT_PROP_SET, (name, valu, None, stype), ()),
                ))

            for tag, valu in srcsode.get('tags', {}).items():
                batch.addEdit(layriden, dstbuid, formname, (
                    (s_layer.EDIT_TAG_SET, (tag, valu, None), ()),
                ))

            dsttagprops = dstsode.get('tagprops', {})

            for tag, propdict in srcsode.get('tagprops', {}).items():

                dstpropdict = dsttagprops.get(tag, {})

                for name, (valu, stype) in propdict.items():

                    if stype not in mergetypes and name in dstpropdict:
                        continue

                    batch.addEdit(layriden, dstbuid, formname, (
                        (s_layer.EDIT_TAGPROP_SET, (tag, name, valu, None, stype), ()),
                    ))

            if nodedata:
                dstdata = {name async for name in layer.iterNodeDataKeys(dstbuid)}

                for name, valu in nodedata:

                    if name in dstdata:
                        continue

                    batch.addEdit(layriden, dstbuid, formname, (
                        (s_layer.EDIT_NODEDATA_SET, (name, valu, None), ()),
                    ))

            # 3. transfer light edges. N1 edges move to dst, and for N2 edges the edge is
            #    stored under the n1 node, so it is re-pointed there.
            for verb, n2iden in n1edges:
                batch.addEdit(layriden, dstbuid, formname, (
                    (s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()),
                ))

            for verb, n1iden in n2edges:

                n1buid = s_common.uhex(n1iden)

                n1form = await self._getFormName(n1buid)
                if n1form is None:  # pragma: no cover
                    await self.warn(
                        f'$lib.model.migration.fuse() cannot find the form for node {n1iden} which has '
                        f'a -({verb})> light edge to {formname}={srcndef[1]!r}; that edge is not moved.')
                    continue

                batch.addEdit(layriden, n1buid, n1form, (
                    (s_layer.EDIT_EDGE_ADD, (verb, dstiden), ()),
                ))

            # 4. tear src down in this layer
            for name, (valu, stype) in srcsode.get('props', {}).items():
                batch.addEdit(layriden, srcbuid, formname, (
                    (s_layer.EDIT_PROP_DEL, (name, valu, stype), ()),
                ))

            for tag, valu in srcsode.get('tags', {}).items():
                batch.addEdit(layriden, srcbuid, formname, (
                    (s_layer.EDIT_TAG_DEL, (tag, valu), ()),
                ))

            for tag, propdict in srcsode.get('tagprops', {}).items():
                for name, (valu, stype) in propdict.items():
                    batch.addEdit(layriden, srcbuid, formname, (
                        (s_layer.EDIT_TAGPROP_DEL, (tag, name, valu, stype), ()),
                    ))

            for verb, n1iden in n2edges:

                n1buid = s_common.uhex(n1iden)

                n1form = await self._getFormName(n1buid)
                if n1form is None:  # pragma: no cover
                    continue

                batch.addEdit(layriden, n1buid, n1form, (
                    (s_layer.EDIT_EDGE_DEL, (verb, srciden), ()),
                ))

            if hasndef:
                # deleting the node also wipes its node data and its N1 light edges
                batch.addEdit(layriden, srcbuid, formname, (
                    (s_layer.EDIT_NODE_DEL, (srcndef[1], stortype), ()),
                ))

            else:
                # src has no primary property here, so nothing will clean these up
                for name, valu in nodedata:
                    batch.addEdit(layriden, srcbuid, formname, (
                        (s_layer.EDIT_NODEDATA_DEL, (name, valu), ()),
                    ))

                for verb, n2iden in n1edges:
                    batch.addEdit(layriden, srcbuid, formname, (
                        (s_layer.EDIT_EDGE_DEL, (verb, n2iden), ()),
                    ))

        # 5. rewrite inbound references. This is a separate pass because a layer may hold
        #    a reference to src without holding any of src's own state, and because it
        #    keeps the referrer edits ordered after dst's node add for the case where the
        #    referrer *is* dst.
        for layer in self.layers:
            todo.extend(await self._rewriteRefs(layer, srcndef, dstndef, batch))

        return todo

    async def _iterRefs(self, layer, srcndef):
        '''
        Yield (refbuid, prop, isarray, isndef) for props in this layer which point at src.
        '''
        formname = srcndef[0]
        srcvalu = srcndef[1]
        srcbuid = s_common.buid(srcndef)

        # ndef typed refs, both scalar and array, come from the reverse index. one index
        # scan per layer covers every ndef prop and cannot miss one.
        async for (refbuid, abrv) in layer.getNdefRefs(srcbuid):

            try:
                (abrvform, abrvprop) = layer.getAbrvProp(abrv)
            except s_exc.NoSuchAbrv:  # pragma: no cover
                continue

            refform = self.model.form(abrvform)
            if refform is None:  # pragma: no cover
                continue

            prop = refform.props.get(abrvprop)
            if prop is None:  # pragma: no cover
                continue

            yield refbuid, prop, prop.type.isarray, True

        # form typed refs need a lift per prop of that type. norm() is deliberately not
        # called, so the comparison values are built by hand.
        for prop in self.model.getPropsByType(formname):
            cmprvals = (('=', srcvalu, prop.type.stortype),)
            async for _, refbuid, _ in layer.liftByPropValu(prop.form.name, prop.name, cmprvals):
                if refbuid == srcbuid:
                    continue
                yield refbuid, prop, False, False

        for prop in self.model.getArrayPropsByType(formname):
            stortype = prop.type.stortype & (~s_layer.STOR_FLAG_ARRAY)
            cmprvals = (('=', srcvalu, stortype),)
            async for _, refbuid, _ in layer.liftByPropArray(prop.form.name, prop.name, cmprvals):
                if refbuid == srcbuid:  # pragma: no cover
                    continue
                yield refbuid, prop, True, False

    async def _rewriteRefs(self, layer, srcndef, dstndef, batch):
        '''
        Queue the edits which repoint this layer's inbound refs from src to dst.

        Returns:
            list: (srcndef, dstndef, subs) tasks for comp forms which must be renamed.
        '''
        srcbuid = s_common.buid(srcndef)

        todo = []

        async for (refbuid, prop, isarray, isndef) in self._iterRefs(layer, srcndef):

            if refbuid == srcbuid:
                continue

            if isndef:
                oldv = srcndef
                newv = dstndef
            else:
                oldv = srcndef[1]
                newv = dstndef[1]

            if prop.info.get('ro'):
                task = await self._rewriteRoRef(layer, refbuid, prop, oldv, newv, batch)
                if task is not None:
                    todo.append(task)
                continue

            refsode = (await self._getSodes(refbuid)).get(layer.iden, {})

            curv = refsode.get('props', {}).get(prop.name)
            if curv is None:  # pragma: no cover
                continue

            (curv, stortype) = curv

            if isarray:
                newlist = [item for item in curv if item != oldv]
                if newv not in newlist:
                    newlist.append(newv)
                setv = newlist
            else:
                setv = newv

            batch.addEdit(layer.iden, refbuid, prop.form.name, (
                (s_layer.EDIT_PROP_SET, (prop.name, setv, None, stortype), ()),
            ))

        return todo

    async def _rewriteRoRef(self, layer, refbuid, prop, oldv, newv, batch):
        '''
        Handle a read-only prop which references src.

        A read-only sub-property of a comp form cannot be rewritten in place, because the
        comp's primary value embeds src's value, so renaming the sub-property changes the
        comp's buid. That is expressed as another fuse of the old comp node into the new
        one, which is returned for the caller's worklist.

        Returns:
            tuple: A (srcndef, dstndef, subs) task, or None.
        '''
        refform = prop.form

        if not isinstance(refform.type, s_types.Comp) or prop.compoffs is None:

            # read-only is enforced when setting a property, not by the storage layer, so
            # this can be rewritten. A stale but valid reference beats a dangling one.
            refsode = (await self._getSodes(refbuid)).get(layer.iden, {})

            curv = refsode.get('props', {}).get(prop.name)
            if curv is None:  # pragma: no cover
                return None

            (curv, stortype) = curv

            batch.addEdit(layer.iden, refbuid, refform.name, (
                (s_layer.EDIT_PROP_SET, (prop.name, newv, None, stortype), ()),
            ))

            await self.warn(
                f'$lib.model.migration.fuse() rewrote read-only property {prop.full!r} on '
                f'{s_common.ehex(refbuid)} because it referenced the node being fused away. '
                f'{refform.name!r} is not a comp form, so its primary property is unchanged.')

            return None

        refvalu = None
        for sode in (await self._getSodes(refbuid)).values():
            valt = sode.get('valu')
            if valt is not None:
                refvalu = valt[0]
                break

        if refvalu is None:  # pragma: no cover
            return None

        newcomp = list(refvalu)
        newcomp[prop.compoffs] = newv

        try:
            (newvalu, norminfo) = refform.type.norm(tuple(newcomp))

        except Exception as e:
            await self.warn(
                f'$lib.model.migration.fuse() cannot re-normalize comp form {refform.name!r} '
                f'for {s_common.ehex(refbuid)}: {e}. That reference is not rewritten.')
            return None

        if newvalu == refvalu:  # pragma: no cover
            return None

        # renaming the comp is itself a fuse of the old comp node into the new one
        return ((refform.name, refvalu), (refform.name, newvalu), norminfo.get('subs'))
