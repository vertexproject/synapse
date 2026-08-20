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

logger = logging.getLogger(__name__)

# The edits which make up a fuse are carried in the payload of the nexus operations which
# apply them, so a fuse is applied in chunks of no more than this many edits rather than as
# one unbounded operation. A fuse of a heavily referenced node can need a very large number
# of edits, so this bounds the size of a single nexus log entry rather than refusing the fuse.
maxchunkedits = 1000

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

    A fuse happens in two steps. getLayerEdits() reads the current state of every layer and
    computes the edits, outside of any nexus operation. Those edits are then split into chunks
    by iterEditChunks() and each chunk is carried in the payload of one Cortex nexus operation
    which applies it, via applyLayerEdits().

    Keeping the edits in the payload means the nexus log holds the edits themselves rather
    than a request to recompute them. A mirror applies exactly the edits the leader computed,
    so the two cannot diverge because they read different state or run different versions of
    this code. Chunking bounds how large a single nexus log entry can get, so fusing a
    heavily referenced node is slower rather than impossible.

    Because the reads happen outside the nexus lock, another write may land between computing
    the edits and applying them. Most edits are expressed as "dst gains X" or "src loses X"
    against state which was actually read, so a racing write is left behind on src rather
    than lost, and checkFused() reports it so the caller can re-run.

    The edits are written straight to each layer, so none of the Snap() write path callbacks
    run and no triggers fire for a fuse. A fuse rewrites the same data across every layer in
    the Cortex rather than making an analytical change in one view, so there is no single view
    whose triggers are the right ones to run, and firing them per view would mean running
    Storm for edits which are only bookkeeping.

    NOTE: A fuse is not transactional. The edits are applied with one call per layer, and a
          large fuse spans several nexus operations, so a failure part way through can leave
          some of it applied. Within each layer the edits which add to dst and repoint
          references are ordered ahead of the edits which remove state from src, and the
          storage layer no-ops edits which have already been applied. An interruption
          therefore cannot lose state or leave a reference pointing at a deleted node, and
          re-running the fuse completes it.
    '''

    def __init__(self, core, useriden):

        self.core = core
        self.model = core.model
        self.useriden = useriden

        self.layers = []        # the layers we may write to
        self.layridens = set()

        self.sodes = {}         # buid -> {layriden: sode} as of before any edits
        self.visited = set()    # src buids which have already been fused
        self.warnings = []      # warnings for the caller to emit

        self.nodeedits = {}     # layriden -> {buid: nodeedit} being accumulated

    def _addEdit(self, layriden, buid, formname, edits):
        '''
        Queue a list of edits for the given buid in the given layer.

        The edits are coalesced by (layer, buid) so that each buid appears exactly once in
        the nodeedits list handed to a given layer, which iterEditChunks() relies on to
        avoid splitting the order dependent edits for a single buid.
        '''
        layredits = self.nodeedits.setdefault(layriden, {})

        nodeedit = layredits.get(buid)
        if nodeedit is None:
            layredits[buid] = nodeedit = (buid, formname, [])

        nodeedit[2].extend(edits)

    async def warn(self, mesg):
        '''
        Record a warning for the caller to emit.

        Computing a fuse has no Storm runtime to warn into, so these are collected and
        returned for the caller to emit.
        '''
        logger.warning(mesg)
        self.warnings.append(mesg)

    async def _getSodes(self, buid):
        '''
        Return (and cache) a {layriden: sode} mapping for the given buid.

        Computing a fuse reads the same buids repeatedly, both across layers and across the
        comp renames it discovers, so these are cached for the life of the compute pass.
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

    async def getLayerEdits(self, srcndef, dstndef):
        '''
        Compute the per-layer node edits which fuse the src node into the dst node.

        This only reads, so it deliberately runs outside of the nexus operations which apply
        the edits. Pass the result to iterEditChunks() to get those operations' payloads.

        The edits for a single buid are returned in the order they must be applied. Within each
        layer, every edit which adds to dst or repoints a reference is ordered ahead of every
        edit which removes state from src, so no state is removed from src in a layer until dst
        has gained it and every inbound reference in that layer points at dst.

        Args:
            srcndef (tuple): The (form, valu) of the node to fuse from. It will be deleted.
            dstndef (tuple): The (form, valu) of the node to fuse into. It will be kept.

        Returns:
            list: A list of (layriden, nodeedits) tuples, or an empty list if there is
                  nothing to do. Sorted by layer iden so that the payloads do not depend on
                  layer iteration order.
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

        self.nodeedits = {}

        todo = collections.deque()
        todo.append((srcndef, dstndef, None))

        while todo:

            (nextsrc, nextdst, subs) = todo.popleft()

            srcbuid = s_common.buid(nextsrc)
            if srcbuid in self.visited:
                continue

            self.visited.add(srcbuid)

            todo.extend(await self._fuseOne(nextsrc, nextdst, subs))

        layeredits = []

        for (layriden, layredits) in sorted(self.nodeedits.items()):

            # Order every edit which removes state from a node being fused away after every
            # edit which adds to dst or repoints a reference. A chunk boundary can fall between
            # two nodeedits, so without this a fuse could be interrupted after src had been
            # deleted but before an inbound reference to it had been repointed at dst.
            #
            # self.visited holds the buid of every node being fused away. A buid which is both
            # fused away and fused into keeps its adds and removes in one coalesced nodeedit,
            # which is never split, so it is safe on either side.
            gains = []
            losses = []

            for nodeedit in layredits.values():
                if nodeedit[0] in self.visited:
                    losses.append(nodeedit)
                else:
                    gains.append(nodeedit)

            layeredits.append((layriden, gains + losses))

        return layeredits

    def getResult(self):
        '''
        Return the warnings recorded while computing the edits, in the shape mergeResult()
        accumulates. Computing never fails a layer, so the failed list is always empty.

        Returns:
            dict: The warnings to emit and the layers which failed.
        '''
        return {'failed': [], 'warnings': self.warnings}

    def _getSelfRefs(self, form):
        '''
        Return a {propname: (isarray, isndef)} mapping of the props on the given form which
        can reference a node of that same form.

        This mirrors what _iterRefs() treats as an inbound reference, so that a reference
        src holds to itself is recognised as one when it is transferred to dst.
        '''
        retn = {}

        for prop in form.props.values():

            ptyp = prop.type
            isarray = ptyp.isarray

            if isarray:
                ptyp = ptyp.arraytype

            if isinstance(ptyp, s_types.Ndef):
                retn[prop.name] = (isarray, True)
                continue

            if ptyp.name == form.name:
                retn[prop.name] = (isarray, False)

        return retn

    def _swapSelfRef(self, valu, isarray, isndef, srcndef, dstndef):
        '''
        Return valu with any reference to src replaced by a reference to dst.

        A property on src which references src is a self reference, so it must follow the node
        and reference dst once it has been transferred. Leaving it pointing at src would
        dangle, and would also mean a repeat of the same fuse saw it as an inbound reference
        which still needed rewriting, making the fuse non-idempotent.
        '''
        if isndef:
            (oldv, newv) = (srcndef, dstndef)
        else:
            (oldv, newv) = (srcndef[1], dstndef[1])

        if not isarray:

            if valu == oldv:
                return newv

            return valu

        if oldv not in valu:
            return valu

        newlist = [item for item in valu if item != oldv]
        if newv not in newlist:
            newlist.append(newv)

        return newlist

    async def _fuseOne(self, srcndef, dstndef, subs):
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

        # props on src's own form which may hold a reference to src itself
        selfrefs = self._getSelfRefs(form)

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

                self._addEdit(layriden, dstbuid, formname, (
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

                            self._addEdit(layriden, dstbuid, formname, (
                                (s_layer.EDIT_PROP_SET, (name, valu, None, prop.type.stortype), ()),
                            ))

                    # .created is read only, so carry src's over when creating the node
                    created = srcsode.get('props', {}).get('.created')
                    if created is not None:
                        self._addEdit(layriden, dstbuid, formname, (
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

                selfref = selfrefs.get(name)
                if selfref is not None:
                    valu = self._swapSelfRef(valu, selfref[0], selfref[1], srcndef, dstndef)

                self._addEdit(layriden, dstbuid, formname, (
                    (s_layer.EDIT_PROP_SET, (name, valu, None, stype), ()),
                ))

            for tag, valu in srcsode.get('tags', {}).items():
                self._addEdit(layriden, dstbuid, formname, (
                    (s_layer.EDIT_TAG_SET, (tag, valu, None), ()),
                ))

            dsttagprops = dstsode.get('tagprops', {})

            for tag, propdict in srcsode.get('tagprops', {}).items():

                dstpropdict = dsttagprops.get(tag, {})

                for name, (valu, stype) in propdict.items():

                    if stype not in mergetypes and name in dstpropdict:
                        continue

                    self._addEdit(layriden, dstbuid, formname, (
                        (s_layer.EDIT_TAGPROP_SET, (tag, name, valu, None, stype), ()),
                    ))

            if nodedata:
                dstdata = {name async for name in layer.iterNodeDataKeys(dstbuid)}

                for name, valu in nodedata:

                    if name in dstdata:
                        continue

                    self._addEdit(layriden, dstbuid, formname, (
                        (s_layer.EDIT_NODEDATA_SET, (name, valu, None), ()),
                    ))

            # 3. transfer light edges. N1 edges move to dst, and for N2 edges the edge is
            #    stored under the n1 node, so it is re-pointed there.
            for verb, n2iden in n1edges:

                # an edge from src to itself must follow the node and become an edge from
                # dst to itself, for the same reason a self referencing property does
                if n2iden == srciden:
                    n2iden = dstiden

                self._addEdit(layriden, dstbuid, formname, (
                    (s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()),
                ))

            for verb, n1iden in n2edges:

                # src's edge to itself is already transferred by the N1 pass above, and
                # adding it here would put an edge on the src node we are about to delete
                if n1iden == srciden:
                    continue

                n1buid = s_common.uhex(n1iden)

                n1form = await self._getFormName(n1buid)
                if n1form is None:  # pragma: no cover
                    await self.warn(
                        f'$lib.model.migration.fuse() cannot find the form for node {n1iden} which has '
                        f'a -({verb})> light edge to {formname}={srcndef[1]!r}; that edge is not moved.')
                    continue

                self._addEdit(layriden, n1buid, n1form, (
                    (s_layer.EDIT_EDGE_ADD, (verb, dstiden), ()),
                ))

            # 4. tear src down in this layer
            for name, (valu, stype) in srcsode.get('props', {}).items():
                self._addEdit(layriden, srcbuid, formname, (
                    (s_layer.EDIT_PROP_DEL, (name, valu, stype), ()),
                ))

            for tag, valu in srcsode.get('tags', {}).items():
                self._addEdit(layriden, srcbuid, formname, (
                    (s_layer.EDIT_TAG_DEL, (tag, valu), ()),
                ))

            for tag, propdict in srcsode.get('tagprops', {}).items():
                for name, (valu, stype) in propdict.items():
                    self._addEdit(layriden, srcbuid, formname, (
                        (s_layer.EDIT_TAGPROP_DEL, (tag, name, valu, stype), ()),
                    ))

            for verb, n1iden in n2edges:

                # src's edge to itself is removed along with src below
                if n1iden == srciden:
                    continue

                n1buid = s_common.uhex(n1iden)

                n1form = await self._getFormName(n1buid)
                if n1form is None:  # pragma: no cover
                    continue

                self._addEdit(layriden, n1buid, n1form, (
                    (s_layer.EDIT_EDGE_DEL, (verb, srciden), ()),
                ))

            if hasndef:
                # deleting the node also wipes its node data and its N1 light edges
                self._addEdit(layriden, srcbuid, formname, (
                    (s_layer.EDIT_NODE_DEL, (srcndef[1], stortype), ()),
                ))

            else:
                # src has no primary property here, so nothing will clean these up
                for name, valu in nodedata:
                    self._addEdit(layriden, srcbuid, formname, (
                        (s_layer.EDIT_NODEDATA_DEL, (name, valu), ()),
                    ))

                for verb, n2iden in n1edges:
                    self._addEdit(layriden, srcbuid, formname, (
                        (s_layer.EDIT_EDGE_DEL, (verb, n2iden), ()),
                    ))

        # 5. rewrite inbound references. This is a separate pass because a layer may hold
        #    a reference to src without holding any of src's own state, and because it
        #    keeps the referrer edits ordered after dst's node add for the case where the
        #    referrer *is* dst.
        for layer in self.layers:
            todo.extend(await self._rewriteRefs(layer, srcndef, dstndef))

        return todo

    async def _rewriteRefs(self, layer, srcndef, dstndef):
        '''
        Queue the edits which repoint this layer's inbound refs from src to dst.

        Returns:
            list: (srcndef, dstndef, subs) tasks for comp forms which must be renamed.
        '''
        srcbuid = s_common.buid(srcndef)

        todo = []

        async for (refbuid, prop, isarray, isndef) in iterLayerRefs(self.model, layer, srcndef):

            if refbuid == srcbuid:
                continue

            if isndef:
                oldv = srcndef
                newv = dstndef
            else:
                oldv = srcndef[1]
                newv = dstndef[1]

            if prop.info.get('ro'):
                task = await self._rewriteRoRef(layer, refbuid, prop, oldv, newv)
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

            self._addEdit(layer.iden, refbuid, prop.form.name, (
                (s_layer.EDIT_PROP_SET, (prop.name, setv, None, stortype), ()),
            ))

        return todo

    async def _rewriteRoRef(self, layer, refbuid, prop, oldv, newv):
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

            self._addEdit(layer.iden, refbuid, refform.name, (
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

async def iterLayerRefs(model, layer, srcndef):
    '''
    Yield (refbuid, prop, isarray, isndef) for props in this layer which point at src.

    This is used both to rewrite the inbound references a fuse must repoint and, after the
    fuse, to check that none are left pointing at a node which no longer exists.

    Args:
        model (Model): The data model to resolve forms and props against.
        layer (Layer): The layer to scan.
        srcndef (tuple): The (form, valu) of the node being referenced.

    Yields:
        tuple: (refbuid, prop, isarray, isndef) for each inbound reference.
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

        refform = model.form(abrvform)
        if refform is None:  # pragma: no cover
            continue

        prop = refform.props.get(abrvprop)
        if prop is None:  # pragma: no cover
            continue

        yield refbuid, prop, prop.type.isarray, True

    # form typed refs need a lift per prop of that type. norm() is deliberately not
    # called, so the comparison values are built by hand.
    for prop in model.getPropsByType(formname):
        cmprvals = (('=', srcvalu, prop.type.stortype),)
        async for _, refbuid, _ in layer.liftByPropValu(prop.form.name, prop.name, cmprvals):
            if refbuid == srcbuid:
                continue
            yield refbuid, prop, False, False

    for prop in model.getArrayPropsByType(formname):
        stortype = prop.type.stortype & (~s_layer.STOR_FLAG_ARRAY)
        cmprvals = (('=', srcvalu, stortype),)
        async for _, refbuid, _ in layer.liftByPropArray(prop.form.name, prop.name, cmprvals):
            if refbuid == srcbuid:  # pragma: no cover
                continue
            yield refbuid, prop, True, False

def iterEditChunks(layeredits, chunk=None):
    '''
    Yield the edits from getLayerEdits() as chunks of no more than chunk edits.

    Each chunk becomes the payload of one nexus operation, which bounds how large a single
    nexus log entry can get without capping how large a fuse may be.

    Three properties are load bearing, and test_nodefuse_edit_chunks() covers each of them:

    1. A nodeedit is never split. The edits for one buid are order dependent: dst's
       EDIT_NODE_ADD must be applied before any prop set for that buid, otherwise the sode
       has props but no valu and reads as a node which does not exist. A chunk therefore
       overshoots rather than splitting a buid, so chunk is a floor and not a ceiling.

    2. The order of the nodeedits is preserved. getLayerEdits() orders every edit which adds
       to dst or repoints a reference ahead of every edit which removes state from src, so an
       interruption cannot lose state or leave a reference pointing at a deleted node.

    3. A layer appears at most once per chunk. A layer records its node edit log entry at the
       nexus offset it was applied at, so two entries for one layer at the same offset would
       overwrite each other. Spanning chunks is fine, because each chunk is its own offset.

    Args:
        layeredits (list): The (layriden, nodeedits) tuples from getLayerEdits().
        chunk (int): The maximum edits per chunk. Defaults to maxchunkedits.

    Yields:
        list: A list of (layriden, nodeedits) tuples to apply as one nexus operation.
    '''
    if chunk is None:
        chunk = maxchunkedits

    todo = []   # the (layriden, nodeedits) tuples for the chunk being built
    count = 0   # how many edits that chunk holds

    for (layriden, nodeedits) in layeredits:

        pend = []

        for nodeedit in nodeedits:

            if count >= chunk:

                # flush what this layer has contributed so far, so that the layer appears
                # in this chunk exactly once and the rest of it lands in the next one
                if pend:
                    todo.append((layriden, pend))
                    pend = []

                yield todo

                todo = []
                count = 0

            pend.append(nodeedit)
            count += len(nodeedit[2])

        if pend:
            todo.append((layriden, pend))

    if todo:
        yield todo

async def applyLayerEdits(core, layeredits, meta, nexsitem):
    '''
    Apply one chunk of the edits computed by NodeFuser.getLayerEdits(), one call per layer.

    This must be called from within the Cortex nexus operation which carries the chunk. The
    edits are handed straight to each layer rather than going through Layer.saveNodeEdits()
    because pushing a second nexus operation from in here would deadlock on the cell wide
    nexus lock. That does not hide the edits from the nexus log: they are already in it, as
    the payload of the operation which is being applied.

    Each layer is applied at most once per chunk. A layer records its node edit log entry at
    the nexus offset it was applied at, so applying to the same layer twice within one nexus
    operation would overwrite the first entry. iterEditChunks() guarantees that.

    Args:
        core (Cortex): The Cortex to apply the edits to.
        layeredits (list): One chunk of (layriden, nodeedits) tuples from iterEditChunks().
        meta (dict): The nodeedit meta to record, built from the pushed useriden and tick.
        nexsitem (tuple): The (offs, mesg) tuple of the nexus operation applying the fuse.

    Returns:
        dict: The layers which failed and any warnings, to be passed to
              NodeFuser.getResult().
    '''
    failed = []
    warnings = []

    def warn(mesg):
        logger.warning(mesg)
        warnings.append(mesg)

    # apply one layer at a time so that one failing layer cannot lose the others
    for (layriden, nodeedits) in layeredits:

        layer = core.getLayer(layriden)
        if layer is None:  # pragma: no cover
            continue

        # The edits were computed outside this operation, so re-check that the layer is still
        # one we may write to. Both flags come from the layer definition, which is replicated,
        # so this decides the same way here and on every mirror.
        if layer.readonly or layer.ismirror:
            why = 'read only' if layer.readonly else 'a mirror'
            warn(f'$lib.model.migration.fuse() did not modify layer {layriden} because it became '
                 f'{why} while the fuse was being computed. Re-run fuse() with the same arguments.')
            continue

        try:
            await layer._storNodeEdits(nodeedits, meta, nexsitem=nexsitem)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:
            errm = str(e)
            failed.append((layriden, errm))
            warn(f'$lib.model.migration.fuse() failed to apply edits to layer {layriden}: {errm}. '
                 f'That layer was not modified. Re-run fuse() with the same arguments to complete it.')
            continue

    return {'failed': failed, 'warnings': warnings}

async def checkFused(core, srcndef):
    '''
    Check that nothing is left of src in any layer a fuse may write to, and warn if there is.

    The edits which make up a fuse are computed outside of the nexus operations which apply
    them, so a write can land in between and be left behind. This is how the caller finds
    out, rather than by fuse() retrying.

    Two things are checked, because a raced write can leave state in two different places:

    1. State on src itself. A prop, tag or tag property set on src after its edits were
       computed is not in the computed deletes, so it survives.

    2. References to src. A node which starts referencing src after the reference rewrites
       were computed is not repointed, so it is left pointing at a node which no longer
       exists. Note that this costs one more reference scan per layer on top of the one the
       fuse itself already did.

    Only layers which a fuse may write to are checked. src surviving in a read only or
    mirrored layer is expected and NodeFuser already warns about those specifically.

    Args:
        core (Cortex): The Cortex the fuse was applied to.
        srcndef (tuple): The (form, valu) of the node which was fused away.

    Returns:
        dict: The warnings to emit and the layers which failed, which is always empty.
    '''
    warnings = []

    srcbuid = s_common.buid(srcndef)

    def warn(mesg):
        logger.warning(mesg)
        warnings.append(mesg)

    for layer in core.layers.values():

        if layer.readonly or layer.ismirror:
            continue

        if await layer.getStorNode(srcbuid):
            warn(f'$lib.model.migration.fuse() left state for {srcndef[0]}={srcndef[1]!r} in layer '
                 f'{layer.iden}, because it was written to while the fuse was being computed. '
                 f'Re-run fuse() with the same arguments to complete it.')

        # A reference can be left behind in a layer which holds none of src's own state, so
        # this is checked separately rather than only when src survived above.
        async for (refbuid, prop, _, _) in iterLayerRefs(core.model, layer, srcndef):

            if refbuid == srcbuid:  # pragma: no cover
                continue

            warn(f'$lib.model.migration.fuse() left a reference to {srcndef[0]}={srcndef[1]!r} in '
                 f'layer {layer.iden} from property {prop.full!r} on {s_common.ehex(refbuid)}, '
                 f'because it was created or updated while the fuse was being computed. That '
                 f'reference points at a node which no longer exists. Re-run fuse() with the '
                 f'same arguments to complete it.')
            break

    return {'failed': [], 'warnings': warnings}

def initResult():
    '''
    Return an empty result dict for mergeResult() to accumulate into.
    '''
    return {'failed': [], 'warnings': []}

def mergeResult(result, newresult):
    '''
    Merge the result of one step of a fuse into the accumulated result.

    A condition which affects more than one step, such as a layer which cannot be modified,
    produces the same message from each of them. Those are deduplicated so the caller emits
    each one once.

    Args:
        result (dict): The accumulated result, from initResult(). Updated in place.
        newresult (dict): The result of one step, from NodeFuser.getResult(),
                          applyLayerEdits() or checkFused().

    Returns:
        None
    '''
    result['failed'].extend(newresult['failed'])

    warnings = set(result['warnings'])
    for mesg in newresult['warnings']:
        if mesg in warnings:
            continue

        warnings.add(mesg)
        result['warnings'].append(mesg)
