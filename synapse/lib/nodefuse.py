'''
Cortex wide fusion of one node into another.
'''
import asyncio
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.types as s_types
import synapse.lib.layer as s_layer
import synapse.lib.spooled as s_spooled

logger = logging.getLogger(__name__)

# The edits which make up a fuse are carried in the payload of the layer nexus operations
# which apply them, so a layer's edits are applied in chunks of no more than this many edits
# rather than as one unbounded operation. A fuse of a heavily referenced node can need a very
# large number of edits, so this bounds the size of a single nexus log entry rather than
# refusing the fuse.
maxchunkedits = 1000

# stortypes which _editPropSet/_editTagPropSet union with the existing value rather than
# overwrite it. Those are always transferred so the storage layer can merge them; every
# other stortype is a plain overwrite, so dst's existing value wins on conflict.
mergetypes = (s_layer.STOR_TYPE_IVAL, s_layer.STOR_TYPE_MINTIME, s_layer.STOR_TYPE_MAXTIME)

class NodeFuser(s_base.Base):
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

    A fuse happens in two steps. getLayerEdits() discovers every rename this fuse makes -
    the original (srcndef, dstndef) pair, plus every comp-form cascade reachable from it -
    before any edits are computed or applied anywhere. Discovery only resolves identity: a
    comp node's primary value, or which layers hold a given buid, are cortex-wide concepts
    read fresh across every layer, not per-layer ones. applyLayerEdits() then computes and
    applies each layer's actual edits, one layer at a time, using the now-complete rename
    map, and hands each layer its own edits with Layer.storNodeEditsNoLift(), split into
    chunks by iterEditChunks() so that each chunk is the payload of one of that layer's
    nexus operations.

    Doing discovery in full before any edit is computed matters for more than tidiness: a
    comp-form cascade discovered from the same parent as an earlier sibling - not just an
    ancestor further up the chain - would not yet be in the rename map if edits were
    computed as each rename was found, and a self reference or edge on that earlier
    sibling could be copied over rather than redirected. Finishing discovery first means
    every rename this fuse will ever make is known before any of them are transferred.

    Keeping the edits in the payload means the nexus log holds the edits themselves rather
    than a request to recompute them. A mirror applies exactly the edits the leader computed,
    so the two cannot diverge because they read different state or run different versions of
    this code. Chunking bounds how large a single nexus log entry can get, so fusing a
    heavily referenced node is slower rather than impossible.

    Each layer's edits are accumulated in a spooled dict scoped to that layer alone: created,
    applied, and finalized before moving on to the next layer, so a fuse of a heavily
    referenced node spills to disk rather than being held whole in memory, and a Cortex with
    many layers never needs more than one layer's worth of spooled state at a time, no matter
    how many of them this fuse touches.

    Because the reads happen before any of the edits are applied, another write may land in
    between. That window is not detected or reported: executing the fuse the caller asked for
    is this class's job, and a write racing that specific call is out of scope for it, the same
    way an ordinary concurrent property write is never flagged as having been overwritten by
    another writer. Running a fuse during a maintenance window, as the Storm API docs
    recommend, avoids the window entirely.

    The edits are written straight to each layer, so none of the Snap() write path callbacks
    run and no triggers fire for a fuse. A fuse rewrites the same data across every layer in
    the Cortex rather than making an analytical change in one view, so there is no single view
    whose triggers are the right ones to run, and firing them per view would mean running
    Storm for edits which are only bookkeeping.

    A NodeFuser is single use. It owns the spooled state it accumulates, so it must be run
    inside an "async with" and a second fuse needs a new instance.

    NOTE: A fuse is not transactional. Each layer is written separately, and a large fuse
          spans several nexus operations per layer, so a failure part way through can leave
          some of it applied. Within each layer the edits which add to dst and repoint
          references are ordered ahead of the edits which remove state from src, and the
          storage layer no-ops edits which have already been applied. An interruption
          therefore cannot lose state or leave a reference pointing at a deleted node, and
          re-running the fuse completes it.
    '''

    async def __anit__(self, core, useriden):

        await s_base.Base.__anit__(self)

        self.core = core
        self.model = core.model
        self.useriden = useriden

        self.layers = []        # the layers we may write to
        self.layridens = set()

        self.failed = []        # (layriden, errm) for each layer which could not be written
        self.warnings = []      # warnings for the caller to emit

        # every rename this fuse makes, including the original (srcndef, dstndef) pair and
        # every comp-form cascade discovered along the way. Populated in full by
        # getLayerEdits(), before applyLayerEdits() computes or applies anything.
        self.renames = []

        # buidmap is keyed by hex iden for edges; ndefmap is keyed by (form, valu) for props.
        # Both are populated alongside self.renames, at discovery time, so a self reference
        # or an edge to any node being fused away in this operation - not just the one
        # currently being transferred - is always redirected correctly regardless of which
        # order the renames were discovered in.
        self.buidmap = {}
        self.ndefmap = {}

        # buid -> nodeedit, scoped to whichever one layer applyLayerEdits() is currently
        # processing. Created fresh and finalized for each layer in turn, so a Cortex with
        # many layers never needs more than one layer's worth of spooled state at a time,
        # no matter how many of them this fuse touches. None outside that scope.
        self.nodeedits = None

        # src buids which have already been discovered. spooled, because a fuse of a heavily
        # referenced comp form discovers one rename per referring node.
        self.visited = await s_spooled.Set.anit(dirn=core.dirn, cell=core)
        self.onfini(self.visited)

    async def _addEdit(self, buid, formname, edits):
        '''
        Queue a list of edits for the given buid in the layer applyLayerEdits() is
        currently processing.

        self.nodeedits is scoped to that one layer, so buid alone is a unique key here -
        every call while it is open targets the same layer. The edits are coalesced by
        buid so that each buid appears exactly once in the nodeedits handed to that layer,
        which lets iterEditChunks() avoid splitting the order dependent edits for a single
        buid.
        '''
        nodeedit = self.nodeedits.get(buid)
        if nodeedit is None:
            await self.nodeedits.set(buid, (buid, formname, list(edits)))
            return

        # the nodeedit may have made a msgpack round trip if the dict has spilled, which
        # returns the edits as a tuple, so it is rebuilt rather than extended in place.
        await self.nodeedits.set(buid, (buid, formname, list(nodeedit[2]) + list(edits)))

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
        Return a {layriden: sode} mapping for the given buid.

        Every layer in the Cortex is read, including the ones a fuse may not write to, so that
        state which only exists in a read only or mirrored layer is still seen.

        This is deliberately uncached, since the compute pass must see the state as it was
        immediately before any edits were applied.
        '''
        sodes = {}

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
        Discover every rename this fuse makes: the original (srcndef, dstndef) pair, plus
        every comp-form cascade reachable from it.

        This only resolves identity - a comp node's primary value, and which layers hold a
        given buid - which are cortex-wide concepts read fresh across every layer, before
        any edits are computed or applied anywhere. No edits are queued here.
        applyLayerEdits() computes and applies each layer's actual edits once every rename
        in self.renames is known, so that a reference is redirected off of any node this
        fuse is fusing away, not just off of the one whose own discovery found it: a comp
        cascade found from the same parent as an earlier sibling would not yet be known if
        edits were computed as each rename was discovered, rather than after discovery
        finishes.

        Args:
            srcndef (tuple): The (form, valu) of the node to fuse from. It will be deleted.
            dstndef (tuple): The (form, valu) of the node to fuse into. It will be kept.

        Returns:
            None. self.renames holds the discovered work for applyLayerEdits().
        '''
        # A read-only layer cannot be written to, and a mirrored layer would forward our
        # edits to its upstream. Both are skipped, and a rename which finds any of its own
        # state stranded there warns below.
        #
        # Sorted by iden so applyLayerEdits() pushes one nexus operation per layer in a
        # deterministic order, rather than one which depends on how self.core.layers - a
        # plain dict - happens to iterate.
        for layer in sorted(self.core.layers.values(), key=lambda layer: layer.iden):

            if layer.readonly or layer.ismirror:
                continue

            self.layers.append(layer)
            self.layridens.add(layer.iden)

        # subs are not exclusive to comp forms - any type's norm() may derive read-only subs
        # from the primary value, and only a comp-form cascade rename ever gets a chance to
        # discover them elsewhere (_discoverCascades() only ever finds comp-form renames, so
        # every entry queued by anything other than this initial seed is already a comp).
        # This initial seed can be any form the caller asked to fuse, so it is normed the
        # same way here regardless of its type.
        form = self.model.reqForm(srcndef[0])
        (_, norminfo) = form.type.norm(dstndef[1])
        subs = norminfo.get('subs')

        todo = collections.deque()
        todo.append((srcndef, dstndef, subs))

        while todo:

            (nextsrc, nextdst, subs) = todo.popleft()

            srcbuid = s_common.buid(nextsrc)
            if self.visited.has(srcbuid):
                continue

            await self.visited.add(srcbuid)

            srciden = s_common.ehex(srcbuid)
            dstiden = s_common.ehex(s_common.buid(nextdst))

            # Recorded the moment this rename is discovered, well before applyLayerEdits()
            # ever transfers anything, so a sibling rename discovered from the same parent
            # - not just an ancestor further up the chain - is always already here too.
            self.buidmap[srciden] = dstiden
            self.ndefmap[nextsrc] = nextdst
            self.renames.append((nextsrc, nextdst, subs))

            # warn about any layer holding this node which we are not allowed to modify
            for layriden in (await self._getSodes(srcbuid)).keys():

                if layriden in self.layridens:
                    continue

                badlayer = self.core.getLayer(layriden)
                why = 'read only' if badlayer.readonly else 'a mirror'

                await self.warn(
                    f'$lib.model.migration.fuse() cannot modify layer {layriden} because it is {why}. '
                    f'{nextsrc[0]}={nextsrc[1]!r} will not be removed from it, and will still be visible '
                    f'in any view which includes that layer.')

            for layer in self.layers:
                todo.extend(await self._discoverCascades(layer, nextsrc, nextdst))

    async def _discoverCascades(self, layer, srcndef, dstndef):
        '''
        Find every comp-form cascade this layer's references to srcndef require.

        A comp form's primary value embeds srcndef's value, so a read-only sub-property
        referencing srcndef means the comp node's own buid is changing too - that is
        itself a rename this fuse must make, discovered here so getLayerEdits() can walk
        it like any other. A read-only reference which is *not* part of a comp key is not
        a rename: it is deferred to _rewriteRefs(), which rewrites it in place once every
        rename is known.

        This only reads and warns; it queues no edits.

        Returns:
            list: (srcndef, dstndef, subs) cascade tasks discovered in this layer.
        '''
        todo = []

        async for (refbuid, prop, isarray, isndef) in self._iterLayerRefs(layer, srcndef):

            if not prop.info.get('ro'):
                continue

            refform = prop.form
            if not isinstance(refform.type, s_types.Comp) or prop.compoffs is None:
                continue

            newv = dstndef if isndef else dstndef[1]

            refvalu = None
            for sode in (await self._getSodes(refbuid)).values():
                valt = sode.get('valu')
                if valt is not None:
                    refvalu = valt[0]
                    break

            if refvalu is None:  # pragma: no cover
                continue

            newcomp = list(refvalu)
            newcomp[prop.compoffs] = newv

            try:
                (newvalu, norminfo) = refform.type.norm(tuple(newcomp))

            except Exception as e:
                await self.warn(
                    f'$lib.model.migration.fuse() cannot re-normalize comp form {refform.name!r} '
                    f'for {s_common.ehex(refbuid)}: {e}. That reference is not rewritten.')
                continue

            if newvalu == refvalu:  # pragma: no cover
                continue

            # renaming the comp is itself a fuse of the old comp node into the new one
            todo.append(((refform.name, refvalu), (refform.name, newvalu), norminfo.get('subs')))

        return todo

    def _iterNodeEdits(self):
        '''
        Yield the current layer's nodeedits, with every edit which removes state from a
        node being fused away ordered after every edit which adds to dst or repoints a
        reference.

        A chunk boundary can fall between two nodeedits, so without this a fuse could be
        interrupted after src had been deleted but before an inbound reference to it had been
        repointed at dst.

        self.visited holds the buid of every node being fused away. A buid which is both
        fused away and fused into keeps its adds and removes in one coalesced nodeedit,
        which is never split, so it is safe on either side.
        '''
        for (buid, nodeedit) in self.nodeedits.items():
            if not self.visited.has(buid):
                yield nodeedit

        for (buid, nodeedit) in self.nodeedits.items():
            if self.visited.has(buid):
                yield nodeedit

    def getResult(self):
        '''
        Return the warnings recorded and the layers which could not be written.

        Returns:
            dict: The warnings to emit and the layers which failed.
        '''
        return {'failed': self.failed, 'warnings': self.warnings}

    def _getSelfRefs(self, form):
        '''
        Return a {propname: (isarray, isndef, refform)} mapping of the props on the given
        form which can hold a value this fuse's ndefmap may need to remap.

        This is not limited to props typed as this same form: the ndefmap this fuse
        populates can hold renames of more than one form in the same operation - a
        comp-form cascade renames whatever form held the read-only reference, not
        necessarily src's own - so a prop on src typed as any one of them can hold a stale
        reference which must follow along the same way a literal self reference does.
        refform is None for an ndef-typed prop, since an ndef value already carries its own
        form.

        This mirrors what _iterLayerRefs() treats as an inbound reference, so that a reference
        src holds to itself, or to any other node being fused away in this operation, is
        recognised as one when it is transferred to dst.
        '''
        retn = {}

        for prop in form.props.values():

            ptyp = prop.type
            isarray = ptyp.isarray

            if isarray:
                ptyp = ptyp.arraytype

            if isinstance(ptyp, s_types.Ndef):
                retn[prop.name] = (isarray, True, None)
                continue

            refform = self.model.form(ptyp.name)
            if refform is not None:
                retn[prop.name] = (isarray, False, refform)

        return retn

    def _remapSelfRef(self, form, isndef, valu):
        '''
        Return the rename map's replacement for valu, or valu unchanged if it does not name a
        node being fused away in this operation.

        valu is an ndef tuple for an Ndef-typed prop, or a raw value of form for a form typed
        prop; both are looked up the same way once expressed as an ndef. form is whatever form
        the prop is typed as - src's own form for a self reference, but not necessarily, since
        a prop may just as well be typed as some other form this same fuse is also renaming.
        '''
        key = valu if isndef else (form.name, valu)

        mapped = self.ndefmap.get(key)
        if mapped is None:
            return valu

        return mapped if isndef else mapped[1]

    async def _swapArrayValu(self, prop, buid, newvalu):
        '''
        Return newvalu re-normalized.

        The elements are swapped in place by the caller and the array is then re-normalized
        here, because an array type may be uniq and/or sorted. Rebuilding the value by hand
        would produce one which the type would never have produced, and the storage layer
        stores what it is given rather than re-normalizing it, so the node would no longer
        lift by its own array value.

        Callers only reach here once they have already determined newvalu differs from the
        array's current value, so that is not re-checked.
        '''
        try:
            return prop.type.norm(newvalu)[0]

        except Exception as e:
            # the reference is still repointed, because leaving it pointing at a node which is
            # about to be deleted is worse than leaving the array un-normalized
            await self.warn(
                f'$lib.model.migration.fuse() cannot re-normalize array property {prop.full!r} on '
                f'{s_common.ehex(buid)}: {e}. That reference is rewritten but the array is not '
                f'normalized.')

            return tuple(newvalu)

    async def _swapSelfRef(self, prop, valu, isarray, isndef, form, dstbuid):
        '''
        Return valu with any reference to src, or to any other node being fused away earlier
        in this same operation, replaced by a reference to what it was fused into.

        A property on src which references src is a self reference, so it must follow the node
        and reference dst once it has been transferred. The same applies to a property which
        references an ancestor a comp-form cascade rename is derived from, or any other node
        this same fuse is renaming: it must be redirected the same way.
        '''
        if not isarray:
            return self._remapSelfRef(form, isndef, valu)

        newvalu = [self._remapSelfRef(form, isndef, item) for item in valu]
        if newvalu == list(valu):
            return valu

        return await self._swapArrayValu(prop, dstbuid, newvalu)

    async def _fuseOneLayer(self, layer, srcndef, dstndef, subs):
        '''
        Queue this one layer's edits for one rename discovered by getLayerEdits().

        buidmap/ndefmap are already complete by the time this runs, so a self reference or
        an edge to any node being fused away in this operation - not just this one - is
        redirected correctly regardless of which order the renames are processed in.
        '''
        formname = srcndef[0]
        form = self.model.reqForm(formname)
        stortype = form.type.stortype

        srcbuid = s_common.buid(srcndef)
        dstbuid = s_common.buid(dstndef)

        srcsode = await layer.getStorNode(srcbuid) or {}
        dstsode = await layer.getStorNode(dstbuid) or {}

        srciden = s_common.ehex(srcbuid)
        dstiden = s_common.ehex(dstbuid)

        hasndef = srcsode.get('valu') is not None

        # a destination which does not exist in *this layer* yet is one we are creating
        # here, so it needs its read only properties filled in, regardless of whether dst
        # already exists in some other layer this fuse also touches.
        isnew = dstsode.get('valu') is None

        # props on src's own form which may hold a reference to src itself
        selfrefs = self._getSelfRefs(form)

        # 1. create dst in the same layer that src lives in. this must precede any
        #    prop sets, otherwise the sode has props but no valu, which reads as a
        #    node which does not exist.
        if hasndef:

            await self._addEdit(dstbuid, formname, (
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

                        await self._addEdit(dstbuid, formname, (
                            (s_layer.EDIT_PROP_SET, (name, valu, None, prop.type.stortype), ()),
                        ))

                # .created is read only, so carry src's over when creating the node
                created = srcsode.get('props', {}).get('.created')
                if created is not None:
                    await self._addEdit(dstbuid, formname, (
                        (s_layer.EDIT_PROP_SET, ('.created', created[0], None, created[1]), ()),
                    ))

        # 2. transfer props, tags, tagprops and node data. dst is the survivor, so its
        #    existing value wins wherever both nodes hold a conflicting value in this
        #    layer. ival/mintime/maxtime values are unioned by the storage layer rather
        #    than overwritten, so those are always transferred regardless of conflict.
        dstprops = dstsode.get('props', {})

        for name, (valu, stype) in srcsode.get('props', {}).items():

            prop = form.props.get(name)

            # read only props on dst are derived from dst's own primary value. .created
            # is read only and is handled above.
            #
            # A prop which is no longer in the model can still hold a value in the sode.
            # It has no derivation on dst and cannot be a self reference, so it is
            # transferred as-is: the teardown below removes every prop it finds, so
            # skipping it here would delete it from src without moving it to dst.
            if prop is not None and prop.info.get('ro'):
                continue

            if stype not in mergetypes and name in dstprops:
                continue

            # selfrefs is keyed off the form's props, so this is never set for a prop
            # which is no longer in the model
            selfref = selfrefs.get(name)
            if selfref is not None:
                (isarray, isndef, refform) = selfref
                valu = await self._swapSelfRef(prop, valu, isarray, isndef, refform, dstbuid)

            await self._addEdit(dstbuid, formname, (
                (s_layer.EDIT_PROP_SET, (name, valu, None, stype), ()),
            ))

        for tag, valu in srcsode.get('tags', {}).items():
            await self._addEdit(dstbuid, formname, (
                (s_layer.EDIT_TAG_SET, (tag, valu, None), ()),
            ))

        dsttagprops = dstsode.get('tagprops', {})

        for tag, propdict in srcsode.get('tagprops', {}).items():

            dstpropdict = dsttagprops.get(tag, {})

            for name, (valu, stype) in propdict.items():

                if stype not in mergetypes and name in dstpropdict:
                    continue

                await self._addEdit(dstbuid, formname, (
                    (s_layer.EDIT_TAGPROP_SET, (tag, name, valu, None, stype), ()),
                ))

        # node data values are arbitrary blobs and a node may hold any number of them, so
        # these are streamed rather than read into memory. dst keeping its own value on a
        # conflict is a probe per name rather than a full listing of dst's keys.
        async for name, valu in s_coro.pause(layer.iterNodeData(srcbuid)):

            if await layer.hasNodeData(dstbuid, name):
                continue

            await self._addEdit(dstbuid, formname, (
                (s_layer.EDIT_NODEDATA_SET, (name, valu, None), ()),
            ))

        # 3. transfer light edges. N1 edges move to dst, and for N2 edges the edge is
        #    stored under the n1 node, so it is re-pointed there.
        async for verb, n2iden in s_coro.pause(layer.iterNodeEdgesN1(srcbuid)):

            # an edge from src to itself, or to any other node being fused away in this
            # same operation (e.g. the node a comp-form cascade rename is derived from),
            # must follow along rather than being left pointing at a node which is about
            # to be deleted.
            n2iden = self.buidmap.get(n2iden, n2iden)

            await self._addEdit(dstbuid, formname, (
                (s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()),
            ))

        async for verb, n1iden in s_coro.pause(layer.iterNodeEdgesN2(srcbuid)):

            # src's edge to itself is already transferred by the N1 pass above, and it is
            # removed along with src below, so it is not re-pointed here
            if n1iden == srciden:
                continue

            n1buid = s_common.uhex(n1iden)

            n1form = await self._getFormName(n1buid)
            if n1form is None:  # pragma: no cover
                await self.warn(
                    f'$lib.model.migration.fuse() cannot find the form for node {n1iden} which has '
                    f'a -({verb})> light edge to {formname}={srcndef[1]!r}; that edge is not moved.')
                continue

            # the add is queued ahead of the del so the edge is never absent, and both
            # land in the one coalesced nodeedit for n1buid, which is never split
            await self._addEdit(n1buid, n1form, (
                (s_layer.EDIT_EDGE_ADD, (verb, dstiden), ()),
                (s_layer.EDIT_EDGE_DEL, (verb, srciden), ()),
            ))

        # 4. tear src down in this layer
        for name, (valu, stype) in srcsode.get('props', {}).items():
            await self._addEdit(srcbuid, formname, (
                (s_layer.EDIT_PROP_DEL, (name, valu, stype), ()),
            ))

        for tag, valu in srcsode.get('tags', {}).items():
            await self._addEdit(srcbuid, formname, (
                (s_layer.EDIT_TAG_DEL, (tag, valu), ()),
            ))

        for tag, propdict in srcsode.get('tagprops', {}).items():
            for name, (valu, stype) in propdict.items():
                await self._addEdit(srcbuid, formname, (
                    (s_layer.EDIT_TAGPROP_DEL, (tag, name, valu, stype), ()),
                ))

        if hasndef:
            # deleting the node also wipes its node data and its N1 light edges
            await self._addEdit(srcbuid, formname, (
                (s_layer.EDIT_NODE_DEL, (srcndef[1], stortype), ()),
            ))

        else:
            # src has no primary property here, so nothing will clean these up. the edit
            # handler fills the value in from what it pops, so it is not carried here.
            async for name, _ in s_coro.pause(layer.iterNodeData(srcbuid)):
                await self._addEdit(srcbuid, formname, (
                    (s_layer.EDIT_NODEDATA_DEL, (name, None), ()),
                ))

            async for verb, n2iden in s_coro.pause(layer.iterNodeEdgesN1(srcbuid)):
                await self._addEdit(srcbuid, formname, (
                    (s_layer.EDIT_EDGE_DEL, (verb, n2iden), ()),
                ))

        # 5. rewrite this layer's inbound refs to src. This is a separate pass because a
        #    layer may hold a reference to src without holding any of src's own state, and
        #    because it keeps the referrer edits ordered after dst's node add for the case
        #    where the referrer *is* dst. Every comp-form cascade was already discovered by
        #    getLayerEdits(), so no new task is returned here.
        await self._rewriteRefs(layer, srcndef, dstndef)

    async def _rewriteRefs(self, layer, srcndef, dstndef):
        '''
        Queue this layer's edits which repoint inbound refs from src to dst.

        Every comp-key cascade rename was already discovered by getLayerEdits(), so a
        read-only reference is always rewritten here rather than returning a new task: if
        it is a true comp-key reference, the comp node it belongs to already has its own
        entry in self.renames, discovered by _discoverCascades(), and is handled by its own
        call to this method. A read-only reference which is *not* part of a comp key is
        rewritten in place - a stale but valid reference beats a dangling one, at the cost
        of the referring node's own primary property no longer matching it, which is
        documented as fuse() behavior.

        An array is rewritten via the ndefmap rather than by swapping only this call's own
        (srcndef, dstndef) pair, because a comp-form cascade means more than one rename can
        share this same fuse() call. Each rename's pass over a given layer reads the array
        fresh, before any of this fuse's edits have been applied to storage, so a pass which
        only patched the one item it was looking for would clobber an earlier pass's fix to
        a different item in that same array with a stale copy of it. Remapping every item
        through the ndefmap fixes every stale item on every pass, so whichever pass's edit
        ends up applied last still leaves the array fully correct.
        '''
        formname = srcndef[0]
        form = self.model.reqForm(formname)

        async for (refbuid, prop, isarray, isndef) in self._iterLayerRefs(layer, srcndef):

            refform = prop.form

            if prop.info.get('ro') and isinstance(refform.type, s_types.Comp) and prop.compoffs is not None:
                continue

            refsode = await layer.getStorNode(refbuid)

            curv = refsode.get('props', {}).get(prop.name)
            if curv is None:  # pragma: no cover
                continue

            (curv, stortype) = curv

            if isarray:
                newvalu = [self._remapSelfRef(form, isndef, item) for item in curv]
                setv = await self._swapArrayValu(prop, refbuid, newvalu)
            else:
                setv = dstndef if isndef else dstndef[1]

            await self._addEdit(refbuid, refform.name, (
                (s_layer.EDIT_PROP_SET, (prop.name, setv, None, stortype), ()),
            ))

    async def _iterLayerRefs(self, layer, srcndef):
        '''
        Yield (refbuid, prop, isarray, isndef) for props in this layer which point at src.

        This is used both to discover which comp-form references require a cascade rename,
        and to rewrite every inbound reference once every rename this fuse makes is known.

        A reference src holds to itself is never yielded. Those follow the node rather than
        being repointed in place, so _fuseOneLayer() transfers them to dst along with the
        rest of src's state; queueing an edit for them here would target a buid which is
        being torn down in the same pass.

        Args:
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
        async for (refbuid, abrv) in s_coro.pause(layer.getNdefRefs(srcbuid)):

            if refbuid == srcbuid:
                continue

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
            async for _, refbuid, _ in s_coro.pause(layer.liftByPropValu(prop.form.name, prop.name, cmprvals)):
                if refbuid == srcbuid:
                    continue
                yield refbuid, prop, False, False

        for prop in self.model.getArrayPropsByType(formname):
            stortype = prop.type.stortype & (~s_layer.STOR_FLAG_ARRAY)
            cmprvals = (('=', srcvalu, stortype),)
            async for _, refbuid, _ in s_coro.pause(layer.liftByPropArray(prop.form.name, prop.name, cmprvals)):
                if refbuid == srcbuid:
                    continue
                yield refbuid, prop, True, False

    async def applyLayerEdits(self, meta):
        '''
        Compute and apply every layer's edits, one layer at a time.

        getLayerEdits() must already have discovered every rename this fuse makes
        (self.renames) and fully populated buidmap/ndefmap before this runs, since
        computing a layer's edits here uses that map to redirect a reference off of any
        node being fused away in this operation, not just off of the one currently being
        processed - see getLayerEdits() for why a partial map is not enough.

        Each layer's edits are queued into a spool scoped to that layer alone: created,
        applied, and finalized before moving on to the next layer, so a fuse touching many
        layers never needs more than one layer's worth of spooled state at a time - the
        same bound a single spool shared across the whole operation used to provide, just
        realized one layer at a time instead.

        Args:
            meta (dict): The nodeedit meta to record, built from the useriden and tick.

        Returns:
            None. The warnings and the layers which failed are recorded on this NodeFuser and
            returned together by getResult().
        '''
        for layer in self.layers:

            layriden = layer.iden

            # The renames were discovered before any of them were applied, so re-check that
            # the layer is still one we may write to. A read only layer would raise, and
            # writing to a mirrored layer here would apply the edits locally rather than via
            # its upstream. Checked before computing anything for this layer, so a layer
            # which is no longer writable does not pay for the computation either.
            if layer.readonly or layer.ismirror:
                why = 'read only' if layer.readonly else 'a mirror'
                await self.warn(
                    f'$lib.model.migration.fuse() did not modify layer {layriden} because it became '
                    f'{why} while the fuse was being computed. Re-run fuse() with the same arguments.')
                continue

            async with await s_spooled.Dict.anit(dirn=self.core.dirn, cell=self.core) as nodeedits:

                self.nodeedits = nodeedits

                for (srcndef, dstndef, subs) in self.renames:
                    await self._fuseOneLayer(layer, srcndef, dstndef, subs)

                try:
                    for editchunk in iterEditChunks(self._iterNodeEdits()):
                        await layer.storNodeEditsNoLift(editchunk, meta)

                except asyncio.CancelledError:  # pragma: no cover
                    raise

                except Exception as e:
                    errm = str(e)
                    self.failed.append((layriden, errm))
                    await self.warn(
                        f'$lib.model.migration.fuse() failed to apply edits to layer {layriden}: {errm}. '
                        f'That layer may be only partly modified. Re-run fuse() with the same arguments '
                        f'to complete it.')

def iterEditChunks(nodeedits, chunk=None):
    '''
    Yield one layer's nodeedits as chunks of no more than chunk edits.

    Each chunk becomes the payload of one of that layer's nexus operations, which bounds how
    large a single nexus log entry can get without capping how large a fuse may be.

    Two properties are load bearing, and test_nodefuse_edit_chunks() covers each of them:

    1. A nodeedit is never split. The edits for one buid are order dependent: dst's
       EDIT_NODE_ADD must be applied before any prop set for that buid, otherwise the sode
       has props but no valu and reads as a node which does not exist. A chunk therefore
       overshoots rather than splitting a buid, so chunk is a floor and not a ceiling.

    2. The order of the nodeedits is preserved. NodeFuser._iterNodeEdits() orders every edit
       which adds to dst or repoints a reference ahead of every edit which removes state from
       src, so an interruption cannot lose state or leave a reference pointing at a deleted
       node.

    Args:
        nodeedits (iterable): One layer's nodeedits from NodeFuser._iterNodeEdits().
        chunk (int): The maximum edits per chunk. Defaults to maxchunkedits.

    Yields:
        list: A list of nodeedits to apply with one call to Layer.storNodeEditsNoLift().
    '''
    if chunk is None:
        chunk = maxchunkedits

    todo = []   # the nodeedits for the chunk being built
    count = 0   # how many edits that chunk holds

    for nodeedit in nodeedits:

        if count >= chunk:

            yield todo

            todo = []
            count = 0

        todo.append(nodeedit)
        count += len(nodeedit[2])

    if todo:
        yield todo
