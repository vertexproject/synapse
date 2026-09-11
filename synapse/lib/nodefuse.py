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
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

# The edits which make up a fuse are carried in the payload of the layer nexus operations
# which apply them, so a layer's edits are applied in chunks of no more than this many edits
# rather than as one unbounded operation. A fuse of a heavily referenced node can need a very
# large number of edits, so this bounds the size of a single nexus log entry rather than
# refusing the fuse.
maxchunkedits = 1000

class NodeFuser(s_base.Base):
    '''
    Fuse a source node into a destination node across every layer in a Cortex.

    Rather than iterating views, this iterates layers. A view is a list of layers, so
    covering every layer covers every view, including views the caller cannot read and
    views which do not exist yet. It also means a layer shared by several views is only
    processed once.

    Within each layer the source node's state is transferred to the destination node's
    nid *in that same layer*, so properties stay in the layer they were written to.
    Inbound references are rewritten in the layer which holds them, and the source is
    then deleted from every writable layer which held it.

    A fuse happens in two steps. getLayerEdits() discovers every rename this fuse makes -
    the original (srcndef, dstndef) pair, plus every comp-form cascade reachable from it -
    before any edits are computed or applied anywhere. Discovery only resolves identity: a
    comp node's primary value, or which layers hold a given nid, are cortex-wide concepts
    read fresh across every layer, not per-layer ones. applyLayerEdits() then computes and
    applies each layer's actual edits, one layer at a time, using the now-complete rename
    map, and hands each layer its own edits with Layer.saveNodeEdits(), split into chunks
    by iterEditChunks() so that each chunk is the payload of one of that layer's nexus
    operations.

    Discovery is itself in two parts, for a reason worth stating plainly. Which nodes this
    fuse renames is found first, breadth first over inbound computed comp key references.
    What each of them renames to is worked out afterwards by _computeRenames(), iterated to
    a fixpoint. They cannot be one pass, because a comp form may embed more than one node
    this same fuse renames - inet:dns:a has one fqdn slot but a comp of two accounts has
    two - and a comp is only discovered once however many of its slots name a renamed node.
    Deriving its new value from whichever slot found it first left every other slot naming
    a node this fuse then deleted, which corrupts the surviving node's own identity rather
    than merely leaving a stale reference behind.

    Finishing discovery before any edit is computed matters for the same family of reasons:
    a comp-form cascade discovered from the same parent as an earlier sibling - not just an
    ancestor further up the chain - would not yet be in the rename map if edits were
    computed as each rename was found, and a self reference or edge on that earlier
    sibling could be copied over rather than redirected. Finishing discovery first means
    every rename this fuse will ever make is known before any of them are transferred.

    Because the rename map is complete before anything is transferred, no rename needs to
    write to a node another rename is fusing away: that node's own pass redirects what it
    holds. Both places which would otherwise queue an edit against another rename's nid -
    _rewriteRefs() and the N2 light edge pass in _fuseOneLayer() - therefore skip it. That
    is not merely an optimisation. An edit queued against a nid whose teardown was queued
    by an earlier rename lands after it, in the one coalesced nodeedit for that nid, and
    the storage layer does not no-op it: a prop set leaves a sode holding props with no
    valu, and an edge add strands edge rows under a nid which no longer resolves to a
    node. Neither is reachable by any lift, and neither is cleaned up by re-running.

    Keeping the edits in the payload means the nexus log holds the edits themselves rather
    than a request to recompute them. Layer.saveNodeEdits() resolves the edits against the
    current sodes in calcEdits() and nexus-pushes the *resolved* edits, so a mirror applies
    exactly the edits the leader computed and the two cannot diverge because they read
    different state or run different versions of this code. Chunking bounds how large a
    single nexus log entry can get, so fusing a heavily referenced node is slower rather
    than impossible.

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

    The edits are written straight to each layer, so none of the NodeEditor write path
    callbacks run and no triggers fire for a fuse. A fuse rewrites the same data across every
    layer in the Cortex rather than making an analytical change in one view, so there is no
    single view whose triggers are the right ones to run, and firing them per view would mean
    running Storm for edits which are only bookkeeping.

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

        # prop names already warned about as dropped by a cross form fuse. _fuseOneLayer()
        # runs once per layer, but a prop dst's form does not declare is a property of the
        # two forms rather than of any one layer, so it is warned about once.
        self.dropped = set()

        # comp field name tuples, keyed by form name. Replaces 2.x's Prop.compoffs, which
        # 3.x does not have: a comp field's position is its index in the type's ordered
        # "fields" opt.
        self.compfields = {}

        # dst's own computed properties, keyed by nid. Read once rather than once per layer:
        # a computed property restates dst's own primary value, so it does not change while
        # the fuse runs, and reading it means reading every layer.
        self.dstcomputed = {}

        # Every rename this fuse makes, including the original (srcndef, dstndef) pair and
        # every comp-form cascade discovered along the way. Keyed by the (form, valu) each
        # rename is from, and valued with a (dstndef, slotmap) tuple - or None between the
        # point a rename is discovered by getLayerEdits() and the point _computeRenames()
        # works out what it renames to.
        #
        # slotmap is {fieldname: newvalu} for the comp key slots a cascade rename changed,
        # or None for the seed. It is what lets _fuseOneLayer() rebuild the renamed node's
        # computed sub properties from the ones already in storage rather than re-deriving
        # them, so the stored (valu, stortype, virts) shape is never guessed at.
        #
        # Populated in full before applyLayerEdits() computes or applies anything, so that
        # a self reference or an edge to any node being fused away in this operation - not
        # just the one currently being transferred - is redirected correctly no matter
        # which order the renames are processed in.
        #
        # Spooled for the same reason self.visited is: a fuse of a heavily referenced comp
        # form discovers one rename per referring node, so this scales with the size of the
        # fuse rather than with the two nodes the caller actually named.
        self.ndefmap = await s_spooled.Dict.anit(dirn=core.dirn, cell=core)
        self.onfini(self.ndefmap)

        # The same renames keyed by the typed value a poly property would have stored, for
        # every form in the renamed node's inheritance chain. A poly declared for an
        # ancestor form may store a reference tagged with the ancestor rather than with the
        # concrete form, so a stored reference cannot be looked up by the renamed node's
        # own form name alone. The value is the replacement typed value, which keeps the
        # stored tag when both forms share it and moves to dst's form when the tag was
        # specific to src.
        self.polymap = await s_spooled.Dict.anit(dirn=core.dirn, cell=core)
        self.onfini(self.polymap)

        # the same renames keyed by integer nid, for redirecting light edges, which name
        # their far end by nid rather than by value.
        self.nidmap = await s_spooled.Dict.anit(dirn=core.dirn, cell=core)
        self.onfini(self.nidmap)

        # nid -> nodeedit, scoped to whichever one layer applyLayerEdits() is currently
        # processing. Created fresh and finalized for each layer in turn, so a Cortex with
        # many layers never needs more than one layer's worth of spooled state at a time,
        # no matter how many of them this fuse touches. None outside that scope.
        self.nodeedits = None

        # src nids which have already been discovered. spooled, because a fuse of a heavily
        # referenced comp form discovers one rename per referring node.
        self.visited = await s_spooled.Set.anit(dirn=core.dirn, cell=core)
        self.onfini(self.visited)

    async def _addEdit(self, nid, formname, edits):
        '''
        Queue a list of edits for the given nid in the layer applyLayerEdits() is
        currently processing.

        self.nodeedits is scoped to that one layer, so nid alone is a unique key here -
        every call while it is open targets the same layer. The edits are coalesced by
        nid so that each nid appears exactly once in the nodeedits handed to that layer,
        which lets iterEditChunks() avoid splitting the order dependent edits for a single
        nid.

        nid is the eight byte encoded form the layer read APIs take. The nodeedit carries
        the integer form, which is what Layer.saveNodeEdits() expects.
        '''
        nodeedit = self.nodeedits.get(nid)
        if nodeedit is None:
            await self.nodeedits.set(nid, (s_common.int64un(nid), formname, list(edits)))
            return

        # the nodeedit may have made a msgpack round trip if the dict has spilled, which
        # returns the edits as a tuple, so it is rebuilt rather than extended in place.
        await self.nodeedits.set(nid, (nodeedit[0], formname, list(nodeedit[2]) + list(edits)))

    async def warn(self, mesg):
        '''
        Record a warning for the caller to emit.

        Computing a fuse has no Storm runtime to warn into, so these are collected and
        returned for the caller to emit.
        '''
        logger.warning(mesg)
        self.warnings.append(mesg)

    async def _getSodes(self, nid):
        '''
        Return a {layriden: sode} mapping for the given nid.

        Every layer in the Cortex is read, including the ones a fuse may not write to, so that
        state which only exists in a read only layer is still seen.

        This is deliberately uncached, since the compute pass must see the state as it was
        immediately before any edits were applied. Layer.getStorNode() is synchronous in
        3.x and returns an empty defaultdict rather than None for a nid the layer holds
        nothing for, so presence is tested by the "form" key which every edit handler sets.
        '''
        sodes = {}

        for layer in self.core.layers.values():

            sode = layer.getStorNode(nid)
            if sode.get('form') is not None:
                sodes[layer.iden] = sode

            await asyncio.sleep(0)

        return sodes

    def _getCompFields(self, form):
        '''
        Return the ordered comp field names for a form, or None if it is not a comp.

        3.x has no Prop.compoffs, so a comp key slot is identified by the field's position
        in the type's ordered "fields" opt and matched to a property by name.
        '''
        fields = self.compfields.get(form.name, s_common.novalu)
        if fields is not s_common.novalu:
            return fields

        fields = None
        if isinstance(form.type, s_types.Comp):
            fields = tuple(fname for (fname, _) in form.type.opts.get('fields', ()))

        self.compfields[form.name] = fields
        return fields

    def _isCompSlot(self, form, prop):
        '''
        Return whether a property restates one of its own form's comp key slots.

        A nested comp sub is flattened by Comp.norm() into a "field:sub" name, which is not
        itself a slot of the outer tuple and so is not a rename: it is deferred to
        _rewriteRefs() and rewritten in place like any other non-comp-key computed
        reference.
        '''
        fields = self._getCompFields(form)
        if fields is None:
            return False

        return prop.name in fields

    async def getLayerEdits(self, srcndef, dstndef):
        '''
        Discover every rename this fuse makes: the original (srcndef, dstndef) pair, plus
        every comp-form cascade reachable from it.

        This only resolves identity - a comp node's primary value, and which layers hold a
        given nid - which are cortex-wide concepts read fresh across every layer, before
        any edits are computed or applied anywhere. No edits are queued here.
        applyLayerEdits() computes and applies each layer's actual edits once every rename
        in self.ndefmap is known, so that a reference is redirected off of any node this
        fuse is fusing away, not just off of the one whose own discovery found it: a comp
        cascade found from the same parent as an earlier sibling would not yet be known if
        edits were computed as each rename was discovered, rather than after discovery
        finishes.

        Args:
            srcndef (tuple): The (form, valu) of the node to fuse from. It will be deleted.
            dstndef (tuple): The (form, valu) of the node to fuse into. It will be kept.

        Returns:
            None. self.ndefmap holds the resolved renames for applyLayerEdits().
        '''
        # A read only layer cannot be written to and is skipped, and a rename which finds
        # any of its own state stranded there warns below. 3.x has no per layer mirror
        # flag: a follower Cortex forwards every layer write to the leader rather than
        # individual layers forwarding to an upstream, so there is no equivalent of 2.x's
        # layer.ismirror to skip here.
        #
        # Sorted by iden so applyLayerEdits() processes the layers in a deterministic
        # order, rather than one which depends on how self.core.layers - a plain dict -
        # happens to iterate.
        for layer in sorted(self.core.layers.values(), key=lambda layer: layer.iden):

            if layer.readonly:
                continue

            self.layers.append(layer)
            self.layridens.add(layer.iden)

        # Which nodes this fuse renames is discovered first, and what each of them renames
        # to is computed afterwards by _computeRenames(). The two are separable because a
        # cascade is discovered by scanning inbound references to a node's *stored* value,
        # which does not depend on what anything is being renamed to.
        #
        # They must be separate because a comp form may embed more than one node this same
        # fuse renames, so deriving a comp's new value from the single slot whose reference
        # happened to be discovered first, and then treating the dedup below as final, left
        # every other slot naming a node this fuse deletes.
        todo = collections.deque()
        todo.append(srcndef)

        while todo:

            nextsrc = todo.popleft()

            srcnid = await self.core.genNdefNid(nextsrc)
            if self.visited.has(srcnid):
                continue

            await self.visited.add(srcnid)

            # recorded with no destination yet, so that _computeRenames() has the full set
            # of renames to resolve against however deep the cascade turns out to be
            await self.ndefmap.set(nextsrc, None)

            # warn about any layer holding this node which we are not allowed to modify
            for layriden in (await self._getSodes(srcnid)).keys():

                if layriden in self.layridens:
                    continue

                await self.warn(
                    f'$lib.model.migration.fuse() cannot modify layer {layriden} because it is read only. '
                    f'{nextsrc[0]}={nextsrc[1]!r} will not be removed from it, and will still be visible '
                    f'in any view which includes that layer.')

            for layer in self.layers:
                todo.extend(await self._discoverCascadeSrcs(layer, nextsrc))

        # Only the pair the caller named can change form: a comp-form cascade rename always
        # keeps its own form. So this is the one rename whose inbound references may turn out
        # to be unable to hold what they are being repointed at, and it is checked here,
        # before any edit is computed, so a refusal leaves the Cortex untouched.
        if srcndef[0] != dstndef[0]:
            await self._reqRefsCompatible(srcndef, dstndef)

        await self._computeRenames(srcndef, dstndef)

    async def _reqRefsCompatible(self, srcndef, dstndef):
        '''
        Refuse a cross form fuse whose inbound references cannot hold dst.

        A property accepts the types it declares and their subtypes, and form inheritance
        runs one way: a property declared for src's form accepts src and anything which
        inherits from src, but not src's parent. So where dst is an ancestor of src, such a
        property cannot hold dst unless it also declares a type or interface dst carries.
        Repointing one which cannot would write a value the property's type rejects, so the
        fuse is refused instead. This runs during discovery, before any edit has been
        computed, let alone applied.
        '''
        dstform = self.model.reqForm(dstndef[0])

        checked = set()

        for layer in self.layers:

            async for (refnid, prop, isarray, reftyp) in self._iterLayerRefs(layer, srcndef):

                if prop.full in checked:
                    continue

                checked.add(prop.full)

                if self._propAcceptsForm(prop, dstform):
                    continue

                mesg = (f'$lib.model.migration.fuse() cannot repoint {prop.full} from '
                        f'{srcndef[0]}={srcndef[1]!r} to {dstndef[0]}={dstndef[1]!r} because that '
                        f'property cannot hold a {dstform.name} node. Nothing was changed.')
                raise s_exc.BadTypeValu(mesg=mesg, prop=prop.full, form=dstform.name)

    def _propAcceptsForm(self, prop, dstform):
        '''
        Return whether the given property can hold a reference to dst.

        Every model property is poly typed (see _getSelfRefs), so this is answered from the
        poly's own declared types and interfaces. An array is asked about its member type,
        since that is what holds the reference.
        '''
        ptyp = prop.type
        if ptyp.isarray:
            ptyp = ptyp.arraytype

        return ptyp.acceptsType(dstform.name)

    async def _discoverCascadeSrcs(self, layer, srcndef):
        '''
        Find every comp node in this layer whose own primary value embeds srcndef, and is
        therefore itself renamed by this fuse.

        A comp form's primary value embeds srcndef's value, so a computed sub-property
        referencing srcndef means the comp node's own primary value is changing too - that
        is itself a rename this fuse must make, discovered here so getLayerEdits() can walk
        it like any other. A computed reference which is *not* part of a comp key is not a
        rename: it is deferred to _rewriteRefs(), which rewrites it in place once every
        rename is known.

        Only the identity of the comp node is resolved here. What it renames *to* is left to
        _computeRenames(), because that depends on every other rename this fuse makes and so
        cannot be known while discovery is still running.

        This only reads; it queues no edits and emits no warnings.

        Returns:
            list: The (form, valu) of each comp node this layer's references require.
        '''
        todo = []

        async for (refnid, prop, isarray, reftyp) in self._iterLayerRefs(layer, srcndef):

            if not prop.info.get('computed'):
                continue

            refform = prop.form
            if not self._isCompSlot(refform, prop):
                continue

            refvalu = None
            for sode in (await self._getSodes(refnid)).values():
                valt = sode.get('valu')
                if valt is not None:
                    refvalu = valt[0]
                    break

            if refvalu is None:  # pragma: no cover
                continue

            todo.append((refform.name, refvalu))

        return todo

    def _remapCompSlots(self, form, valu):
        '''
        Return (changed, newvalu, slotmap) for a comp value with every computed comp key
        slot which names a node being fused away in this operation remapped to what it is
        fused into.

        Every slot is remapped, rather than only the one whose own reference happened to
        find this node, because a comp form may embed more than one node this same fuse
        renames.

        slotmap is the {fieldname: newvalu} of the slots which actually changed, which
        _fuseOneLayer() uses to rebuild the renamed node's computed sub properties from the
        ones already in storage.

        A comp key slot is never an array: a comp field must name a named type
        (Comp._checkMutability) and the array type may not be the base for a named type
        (Model.addType), so unlike an ordinary array property a slot only ever holds one
        value. A slot whose poly names no form at all cannot hold a node reference, so
        _getSelfRefs() does not report it and it is left alone.
        '''
        fields = self._getCompFields(form)
        if fields is None:  # pragma: no cover
            return False, valu, None

        newcomp = list(valu)
        slotmap = {}

        selfrefs = self._getSelfRefs(form)

        for prop in form.props.values():

            if not prop.info.get('computed') or prop.name not in fields:
                continue

            # a slot typed as something which names no form at all - a bare int or str field
            # of the comp key - cannot name a node, so there is nothing to remap
            if prop.name not in selfrefs:
                continue

            offs = fields.index(prop.name)
            curv = newcomp[offs]

            newv = self._remapSelfRef(curv)

            if newv != curv:
                newcomp[offs] = newv
                slotmap[prop.name] = newv

        return bool(slotmap), tuple(newcomp), slotmap

    async def _computeRenames(self, srcndef, dstndef):
        '''
        Work out what each rename discovered by getLayerEdits() renames to.

        The seed's destination is the one the caller named. Every other rename is a comp
        node whose new value is its stored value with each of its computed comp key slots
        remapped through the renames this fuse makes - which is why this cannot run until
        discovery has finished, and why it is iterated to a fixpoint rather than computed in
        one pass: a comp's slot may name another comp which is itself still being resolved,
        to any depth.

        Each pass recomputes every destination from the node's own stored value rather than
        from the previous pass's result, so a pass is idempotent and cannot accumulate a
        partially remapped value. The renames form a DAG - a comp's slots are discovered
        before the comp, and no comp can embed itself - so the number of passes needed is
        bounded by the depth of the deepest cascade.

        Args:
            srcndef (tuple): The (form, valu) of the node the caller is fusing from.
            dstndef (tuple): The (form, valu) of the node the caller is fusing into.

        Returns:
            None. self.ndefmap, self.polymap and self.nidmap hold the resolved renames.
        '''
        await self._setRename(srcndef, dstndef, None)

        while True:

            changed = False

            async for (nextsrc, rename) in s_coro.pause(self.ndefmap.items()):

                if nextsrc == srcndef:
                    continue

                refform = self.model.reqForm(nextsrc[0])

                (slotchanged, newvalu, slotmap) = self._remapCompSlots(refform, nextsrc[1])
                if not slotchanged:
                    # This node was discovered because one of its computed comp key properties
                    # names a node this fuse renames, so its own primary value must embed that
                    # same node - a computed comp key property is a restatement of the slot it
                    # is derived from. Reaching here means the two disagree in storage, so
                    # there is no new value to rename this node to. Everything downstream
                    # requires every discovered rename to have a destination (see the check
                    # after this loop), so this refuses while it is still safe to: no edit has
                    # been computed yet, let alone applied.
                    mesg = (f'$lib.model.migration.fuse() cannot rename {nextsrc[0]}={nextsrc[1]!r}: a '
                            f'computed comp key property names a node being fused away, but the '
                            f'primary value does not embed it. No node edits were applied.')
                    raise s_exc.BadTypeValu(mesg=mesg, form=refform.name)

                try:
                    # a comp field which names a form is a poly, so a stored comp value is a
                    # tuple of typed values. normFromTypedValu() re-norms each field through
                    # the type it already carries; a plain norm() would try to re-derive each
                    # field's type from its value and mis-read a typed value as a raw one.
                    (newvalu, _) = await refform.type.normFromTypedValu(newvalu)

                except Exception as e:
                    # This runs before any edit has been queued, let alone applied, so
                    # raising here applies no node edits and the operator can fix the
                    # offending node and re-run fuse.
                    mesg = (f'$lib.model.migration.fuse() cannot re-normalize comp form '
                            f'{refform.name!r} for {nextsrc[0]}={nextsrc[1]!r}: {e}')
                    raise s_exc.BadTypeValu(mesg=mesg, form=refform.name) from e

                newndef = (refform.name, newvalu)

                if rename is not None and rename[0] == newndef:
                    continue

                await self._setRename(nextsrc, newndef, slotmap)
                changed = True

            if not changed:
                break

        await self._reqRenamesResolved()

    async def _reqRenamesResolved(self):
        '''
        Require that no rename this fuse makes resolves to a value which is itself renamed.

        A destination is only ever a value with every slot already remapped off of the nodes
        this fuse deletes, so it can never itself be one of the values this fuse renames
        away. _remapSelfRef() and polymap rely on that to resolve in a single hop, and this
        checks the property rather than leaving it to be inferred.

        Every rename is resolved by the time this runs. A comp is only ever discovered
        because one of its computed comp key slots named another rename, and such a slot is
        always form or poly typed - so _getSelfRefs() reports it and _remapCompSlots() remaps
        it as soon as its own referent resolves, which either happens or _computeRenames()
        refuses the fuse when it re-normalizes. There is no unresolved entry left to skip.

        No model construct reaches this today: only s_types.Comp cascades, and
        test_stormlib_model_migration_fuse_model_canary() fails if another one appears, so
        that a new construct is checked against this assumption rather than silently
        inheriting it. This raises rather than being left to that test alone because the
        cost of the assumption being wrong is not an error - it is a reference which
        resolves halfway and is written to a layer looking valid.
        '''
        async for (nextsrc, rename) in s_coro.pause(self.ndefmap.items()):

            (renamed, _) = rename

            if self.ndefmap.get(renamed) is not None:
                mesg = (f'$lib.model.migration.fuse() computed a rename of {nextsrc[0]}={nextsrc[1]!r} '
                        f'to {renamed[0]}={renamed[1]!r}, which is itself being renamed.')
                raise s_exc.SynErr(mesg=mesg)

    async def _setRename(self, srcndef, dstndef, slotmap):
        '''
        Record what srcndef renames to, keyed by ndef, by stored typed value, and by nid.
        '''
        await self.ndefmap.set(srcndef, (dstndef, slotmap))

        srcnid = await self.core.genNdefNid(srcndef)
        dstnid = await self.core.genNdefNid(dstndef)

        await self.nidmap.set(s_common.int64un(srcnid), s_common.int64un(dstnid))

        srcform = self.model.reqForm(srcndef[0])
        dstform = self.model.reqForm(dstndef[0])

        # A poly property declared for an ancestor form stores its reference tagged with
        # whichever form in the chain the value was filed under, so every ancestor of src
        # is a typed value some property may be holding. A tag both forms share is kept, so
        # a reference filed under an ancestor stays filed under it; a tag specific to src
        # has to move to dst's own form, which is only reachable under a cross form fuse.
        for ftyp in srcform.formtypes:

            newtyp = ftyp if ftyp in dstform.formtypes else dstform.name

            await self.polymap.set((ftyp, srcndef[1]), (newtyp, dstndef[1]))

    def _iterNodeEdits(self):
        '''
        Yield the current layer's nodeedits, with every edit which removes state from a
        node being fused away ordered after every edit which adds to dst or repoints a
        reference.

        A chunk boundary can fall between two nodeedits, so without this a fuse could be
        interrupted after src had been deleted but before an inbound reference to it had been
        repointed at dst.

        self.visited holds the nid of every node being fused away, so this splits the
        nodeedits into the ones which build dst up and the ones which tear src down, and
        emits them in that order. Within a single nid the order _addEdit() coalesced them
        in is preserved, and a nodeedit is never split by iterEditChunks(), so a nid whose
        adds and removes are both queued keeps them in the right order either way.

        No nodeedit here mixes another rename's teardown with this one's adds: a rename
        never queues an edit against a nid another rename is fusing away, because that
        node's own pass redirects what it holds. See the class docstring for why an edit
        which landed after such a teardown was not simply redundant.
        '''
        for (nid, nodeedit) in self.nodeedits.items():
            if not self.visited.has(nid):
                yield nodeedit

        for (nid, nodeedit) in self.nodeedits.items():
            if self.visited.has(nid):
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
        Return a {propname: isarray} mapping of the props on the given form which can hold a
        value this fuse's rename map may need to remap.

        This is not limited to props typed as this same form: the rename map this fuse
        populates can hold renames of more than one form in the same operation - a
        comp-form cascade renames whatever form held the computed reference, not
        necessarily src's own - so a prop on src typed as any one of them can hold a stale
        reference which must follow along the same way a literal self reference does.

        Every model property's member type is poly typed, so a stored value is always a
        typed value and the rename map is always consulted through polymap.
        Model.processPropdefs() routes every prop typedef through Model.convertTypedef(),
        which wraps whatever it is handed in a poly, and Array.postTypeInit() likewise
        clones the poly type for its member type. For an array prop that poly is
        prop.type.arraytype rather than prop.type, which is why the loop below steps to
        arraytype before testing hasforms: prop.type.ispoly is False for an array prop.
        What still varies is whether the poly names any form or interface at all: one which
        names none cannot hold a node reference, and that is what hasforms selects for here.

        This mirrors what _iterLayerRefs() treats as an inbound reference, so that a
        reference src holds to itself, or to any other node being fused away in this
        operation, is recognised as one when it is transferred to dst.
        '''
        retn = {}

        for prop in form.props.values():

            ptyp = prop.type
            isarray = ptyp.isarray

            if isarray:
                ptyp = ptyp.arraytype

            if ptyp.hasforms:
                retn[prop.name] = isarray

        return retn

    def _remapSelfRef(self, valu):
        '''
        Return the rename map's replacement for the given typed value, or the value unchanged
        if it does not name a node being fused away in this operation.

        valu is always a (typename, valu) typed value, since every property which can hold a
        node reference is poly typed - see _getSelfRefs(). It is looked up through polymap,
        which is keyed by every form in the renamed node's inheritance chain, because the
        stored type name may be an ancestor of the renamed node's own form rather than the
        form itself.
        '''
        # None covers both a value this fuse does not rename and one which has been
        # discovered but not yet resolved, which is what lets _computeRenames() iterate:
        # an unresolved slot is left alone and picked up by a later pass.
        mapped = self.polymap.get(tuple(valu))
        if mapped is None:
            return valu

        return mapped

    async def _swapArrayValu(self, prop, nid, newvalu):
        '''
        Return newvalu re-normalized.

        The elements are swapped in place by the caller and the array is then re-normalized
        here, because an array type may be uniq and/or sorted. Rebuilding the value by hand
        would produce one which the type would never have produced, and the storage layer
        stores what it is given rather than re-normalizing it, so the node would no longer
        lift by its own array value.

        Callers only reach here once they have already determined newvalu differs from the
        array's current value, so that is not re-checked.

        An array's member type is always a poly, so a stored array is a list of typed
        values. normFromTypedValu() is the entry point which re-norms those through the type
        each element already carries; a plain norm() would try to re-derive each element's
        type from the value and mis-read a typed value as a raw one.
        '''
        try:
            return (await prop.type.normFromTypedValu(newvalu))[0]

        except Exception as e:
            # the reference is still repointed, because leaving it pointing at a node which is
            # about to be deleted is worse than leaving the array un-normalized
            await self.warn(
                f'$lib.model.migration.fuse() cannot re-normalize array property {prop.full!r} on '
                f'node {s_common.int64un(nid)}: {e}. That reference is rewritten but the array is '
                f'not normalized.')

            return tuple(newvalu)

    async def _swapSelfRef(self, prop, valu, isarray, nid):
        '''
        Return valu with any reference to src, or to any other node being fused away earlier
        in this same operation, replaced by a reference to what it was fused into.

        A property on src which references src is a self reference, so it must follow the node
        and reference dst once it has been transferred. The same applies to a property which
        references an ancestor a comp-form cascade rename is derived from, or any other node
        this same fuse is renaming: it must be redirected the same way.

        An array whose items name no node this fuse renames is returned as it was stored,
        rather than being re-normalized to the same value, so a property which merely could
        have held a reference does not get rewritten for no reason.
        '''
        if not isarray:
            return self._remapSelfRef(valu)

        newvalu = [self._remapSelfRef(item) for item in valu]
        if newvalu == list(valu):
            return valu

        return await self._swapArrayValu(prop, nid, newvalu)

    async def _fuseOneLayer(self, layer, srcndef, dstndef, slotmap):
        '''
        Queue this one layer's edits for one rename discovered by getLayerEdits().

        polymap/ndefmap/nidmap are already complete by the time this runs, so a self
        reference or an edge to any node being fused away in this operation - not just this
        one - is redirected correctly regardless of which order the renames are processed
        in.
        '''
        srcform = self.model.reqForm(srcndef[0])
        dstform = self.model.reqForm(dstndef[0])

        srcnid = await self.core.genNdefNid(srcndef)
        dstnid = await self.core.genNdefNid(dstndef)

        srcintnid = s_common.int64un(srcnid)
        dstintnid = s_common.int64un(dstnid)

        srcsode = layer.getStorNode(srcnid)
        dstsode = layer.getStorNode(dstnid)

        hasvalu = srcsode.get('valu') is not None

        # a destination which does not exist in *this layer* yet is one we are creating
        # here, so it needs its computed properties filled in, regardless of whether dst
        # already exists in some other layer this fuse also touches.
        isnew = dstsode.get('valu') is None

        # props on dst's own form which may hold a reference to a node being fused away
        selfrefs = self._getSelfRefs(dstform)

        srcprops = srcsode.get('props', {})
        srcantiprops = srcsode.get('antiprops', {})

        dstprops = dstsode.get('props', {})

        # 1. create dst in the same layer that src lives in. this must precede any
        #    prop sets, otherwise the sode has props but no valu, which reads as a
        #    node which does not exist.
        if hasvalu:

            (dstvalu, dststortype, dstvirts) = self._getStorValu(dstsode, dstform, dstndef)

            await self._addEdit(dstnid, dstform.name, (
                (s_layer.EDIT_NODE_ADD, (dstvalu, dststortype, dstvirts)),
            ))

            if isnew:
                await self._addComputedProps(dstnid, dstform, dstndef, srcsode, slotmap)

                # .created is node meta rather than a property in 3.x and is stamped with
                # "now" by the node add above. The meta set is applied after that node add
                # and overwrites it, so src's creation time replaces the "now" stamp on a
                # freshly created dst - no isnew branch of its own required.
                created = srcsode.get('meta', {}).get('created')
                if created is not None:
                    await self._addEdit(dstnid, dstform.name, (
                        (s_layer.EDIT_META_SET, ('created', created[0], created[1])),
                    ))

        # 2. transfer props, tags, tagprops and node data. dst is the survivor, so its
        #    existing value wins wherever both nodes hold a conflicting value in this
        #    layer. Where the property's type merges rather than overwrites - an ival, or
        #    a min/max time - Type.merge() unions the two instead. 3.x storage does not
        #    merge on its own, so the merge is computed here.
        for name, valt in srcprops.items():

            # defensive: a layer keeps a live value and a tombstone mutually exclusive, so
            # a name in srcprops is never also in srcantiprops
            if name in srcantiprops:  # pragma: no cover
                continue

            prop = dstform.props.get(name)

            # A computed prop belongs to the node's own identity rather than being an
            # analytical value src can hand over, so src's is never transferred. Where dst's
            # own type derives the prop from its primary value it is already set above from
            # dst's own stored properties. Where it does not, src's value would contradict
            # dst's primary value rather than fill a gap in it, because such a prop is a
            # decomposition of the value rather than data of its own: fusing
            # inet:url=https://visi@vertex.link/ into inet:url=https://vertex.link/ would
            # put :username=visi on a URL which contains no user, so the node would lift by
            # inet:url:username=visi while its own primary value says otherwise. .created
            # is node meta and is carried over above.
            #
            # A prop which is no longer in the model can still hold a value in the sode.
            # It has no derivation on dst and cannot be a self reference, so it is
            # transferred as-is: the teardown below removes every prop it finds, so
            # skipping it here would delete it from src without moving it to dst.
            if prop is not None and prop.info.get('computed'):
                continue

            # Only reachable under a cross form fuse: props flow from a parent form to its
            # children and never the other way, so a prop declared only on src's child form
            # has no slot on a parent form dst. Warned once rather than once per layer,
            # because it is a property of the two forms rather than of any one layer.
            if prop is None and srcform.props.get(name) is not None:
                if name not in self.dropped:
                    self.dropped.add(name)
                    await self.warn(
                        f'$lib.model.migration.fuse() cannot transfer {srcform.name}:{name} to '
                        f'{dstform.name}, which does not declare it. That value is discarded.')
                continue

            (valu, stortype, virts) = valt

            dstvalt = dstprops.get(name)

            if dstvalt is not None and prop is not None:
                # dst holds a conflicting value. A type which does not merge returns the
                # value it is handed second, so passing dst's second is what makes dst the
                # survivor, and an ival or a min/max time unions the two symmetrically.
                merged = prop.type.merge(valu, dstvalt[0])
                if merged == dstvalt[0]:
                    continue

                (valu, stortype, virts) = self._getStorInfo(prop, merged)

            elif dstvalt is not None:  # pragma: no cover
                # a prop which is no longer in the model has no type to merge through, so
                # dst's value simply wins
                continue

            else:
                # selfrefs is keyed off the form's props, so this is never set for a prop
                # which is no longer in the model
                isarray = selfrefs.get(name)
                if isarray is not None:
                    newvalu = await self._swapSelfRef(prop, valu, isarray, dstnid)
                    if newvalu != valu:
                        (valu, stortype, virts) = self._getStorInfo(prop, newvalu)

            await self._addEdit(dstnid, dstform.name, (
                (s_layer.EDIT_PROP_SET, (name, valu, stortype, virts)),
            ))

        srctags = srcsode.get('tags', {})
        srcantitags = srcsode.get('antitags', {})

        dsttags = dstsode.get('tags', {})

        ivaltype = self.model.type('ival')

        for tag, valu in srctags.items():

            if tag in srcantitags:  # pragma: no cover
                continue

            dstvalu = dsttags.get(tag)

            if dstvalu is not None:

                # dst is the survivor, so an unbounded tag on src must not overwrite a real
                # interval dst already holds. 3.x storage stores whatever the edit carries
                # rather than merging, so the union is computed here, and only when both
                # sides are real intervals.
                if valu == (None, None, None) or dstvalu == (None, None, None):
                    continue

                merged = ivaltype.merge(valu, dstvalu)
                if merged == dstvalu:
                    continue

                valu = merged

            await self._addEdit(dstnid, dstform.name, (
                (s_layer.EDIT_TAG_SET, (tag, valu)),
            ))

        srctagprops = srcsode.get('tagprops', {})
        srcantitagprops = srcsode.get('antitagprops', {})

        dsttagprops = dstsode.get('tagprops', {})

        for tag, propdict in srctagprops.items():

            srcanti = srcantitagprops.get(tag, {})
            dstpropdict = dsttagprops.get(tag, {})

            for name, (valu, stortype, virts) in propdict.items():

                if name in srcanti:  # pragma: no cover
                    continue

                tagprop = self.model.getTagProp(name)

                dstvalt = dstpropdict.get(name)
                if dstvalt is not None:
                    if tagprop is None:  # pragma: no cover
                        continue

                    merged = tagprop.type.merge(valu, dstvalt[0])
                    if merged == dstvalt[0]:
                        continue

                    (valu, stortype, virts) = self._getStorInfo(tagprop, merged)

                await self._addEdit(dstnid, dstform.name, (
                    (s_layer.EDIT_TAGPROP_SET, (tag, name, valu, stortype, virts)),
                ))

        # node data values are arbitrary blobs and a node may hold any number of them, so
        # these are streamed rather than read into memory. dst keeping its own value on a
        # conflict is a probe per name rather than a full listing of dst's keys. The keys
        # come back as index abbreviations rather than names, so each is decoded before it
        # can be named in an edit.
        async for abrv, valu, tomb in s_coro.pause(layer.iterNodeData(srcnid)):

            if tomb:
                continue

            name = self.core.getAbrvIndx(abrv)[0]

            # hasNodeData() is tri-state in 3.x: True for a live value, False for a
            # tombstone and None for neither. Only a live value on dst wins. A tombstone is
            # treated the same way it is for props, tags and tagprops: it would mask the
            # value being transferred, so src's value is written and EDIT_NODEDATA_SET
            # clears the tombstone along with it.
            if await layer.hasNodeData(dstnid, name):
                continue

            await self._addEdit(dstnid, dstform.name, (
                (s_layer.EDIT_NODEDATA_SET, (name, valu)),
            ))

        # 3. transfer light edges. N1 edges move to dst, and for N2 edges the edge is
        #    stored under the n1 node, so it is re-pointed there. Both ends are named by
        #    nid, and the verb comes back as an index abbreviation.
        async for abrv, n2nid, tomb in s_coro.pause(layer.iterNodeEdgesN1(srcnid)):

            if tomb:
                continue

            verb = self.core.getAbrvIndx(abrv)[0]

            # an edge from src to itself, or to any other node being fused away in this
            # same operation (e.g. the node a comp-form cascade rename is derived from),
            # must follow along rather than being left pointing at a node which is about
            # to be deleted.
            n2intnid = s_common.int64un(n2nid)
            n2intnid = self.nidmap.get(n2intnid, n2intnid)

            await self._addEdit(dstnid, dstform.name, (
                (s_layer.EDIT_EDGE_ADD, (verb, n2intnid)),
            ))

        async for abrv, n1nid, tomb in s_coro.pause(layer.iterNodeEdgesN2(srcnid)):

            if tomb:
                continue

            # src's edge to itself is already transferred by the N1 pass above, and it is
            # removed along with src below, so it is not re-pointed here
            if n1nid == srcnid:
                continue

            # an n1 which is itself being fused away in this operation transfers its own N1
            # edges in its own pass, remapping the far end through nidmap, so this edge is
            # already moved. Queueing it here as well would append an edge add after that
            # nid's own EDIT_NODE_DEL in the one coalesced nodeedit for it, and the storage
            # layer still writes the edge index rows, stranding an edge under a nid which
            # no longer resolves to a node.
            if self.visited.has(n1nid):
                continue

            verb = self.core.getAbrvIndx(abrv)[0]

            n1ndef = self.core.getNidNdef(n1nid)
            if n1ndef is None:  # pragma: no cover
                await self.warn(
                    f'$lib.model.migration.fuse() cannot find the form for node '
                    f'{s_common.int64un(n1nid)} which has a -({verb})> light edge to '
                    f'{srcform.name}={srcndef[1]!r}; that edge is not moved.')
                continue

            # the add is queued ahead of the del so the edge is never absent, and both
            # land in the one coalesced nodeedit for n1nid, which is never split
            await self._addEdit(n1nid, n1ndef[0], (
                (s_layer.EDIT_EDGE_ADD, (verb, dstintnid)),
                (s_layer.EDIT_EDGE_DEL, (verb, srcintnid)),
            ))

        # 4. tear src down in this layer
        for name in srcprops.keys():
            await self._addEdit(srcnid, srcform.name, (
                (s_layer.EDIT_PROP_DEL, (name,)),
            ))

        for name in srcantiprops.keys():
            await self._addEdit(srcnid, srcform.name, (
                (s_layer.EDIT_PROP_TOMB_DEL, (name,)),
            ))

        for tag in srctags.keys():
            await self._addEdit(srcnid, srcform.name, (
                (s_layer.EDIT_TAG_DEL, (tag,)),
            ))

        for tag in srcantitags.keys():
            await self._addEdit(srcnid, srcform.name, (
                (s_layer.EDIT_TAG_TOMB_DEL, (tag,)),
            ))

        for tag, propdict in srctagprops.items():
            for name in propdict.keys():
                await self._addEdit(srcnid, srcform.name, (
                    (s_layer.EDIT_TAGPROP_DEL, (tag, name)),
                ))

        for tag, propdict in srcantitagprops.items():
            for name in propdict.keys():
                await self._addEdit(srcnid, srcform.name, (
                    (s_layer.EDIT_TAGPROP_TOMB_DEL, (tag, name)),
                ))

        if hasvalu:
            # deleting the node also wipes its node data and its N1 light edges
            await self._addEdit(srcnid, srcform.name, (
                (s_layer.EDIT_NODE_DEL, ()),
            ))

        else:
            if srcsode.get('antivalu') is not None:
                await self._addEdit(srcnid, srcform.name, (
                    (s_layer.EDIT_NODE_TOMB_DEL, ()),
                ))

            # src has no primary property here, so nothing will clean these up
            async for abrv, tomb in s_coro.pause(layer.iterNodeDataKeys(srcnid)):
                name = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    await self._addEdit(srcnid, srcform.name, (
                        (s_layer.EDIT_NODEDATA_TOMB_DEL, (name,)),
                    ))
                else:
                    await self._addEdit(srcnid, srcform.name, (
                        (s_layer.EDIT_NODEDATA_DEL, (name,)),
                    ))

            async for abrv, n2nid, tomb in s_coro.pause(layer.iterNodeEdgesN1(srcnid)):
                verb = self.core.getAbrvIndx(abrv)[0]
                n2intnid = s_common.int64un(n2nid)
                if tomb:
                    await self._addEdit(srcnid, srcform.name, (
                        (s_layer.EDIT_EDGE_TOMB_DEL, (verb, n2intnid)),
                    ))
                else:
                    await self._addEdit(srcnid, srcform.name, (
                        (s_layer.EDIT_EDGE_DEL, (verb, n2intnid)),
                    ))

        # 5. rewrite this layer's inbound refs to src. This is a separate pass because a
        #    layer may hold a reference to src without holding any of src's own state, and
        #    because it keeps the referrer edits ordered after dst's node add for the case
        #    where the referrer *is* dst. Every comp-form cascade was already discovered by
        #    getLayerEdits(), so no new task is returned here.
        await self._rewriteRefs(layer, srcndef, dstndef)

    def _getStorValu(self, dstsode, dstform, dstndef):
        '''
        Return the (valu, stortype, virts) triple to create dst with.

        Where dst already exists in this layer the stored triple is authoritative and is
        reused verbatim, so a fuse cannot disagree with a shape the layer itself produced.
        Otherwise it is derived from dst's own primary value, which is what a comp form
        needs: EDIT_NODE_ADD carries the per-field stortypes a comp is indexed by in its
        virts, and Layer.calcEdits() reads them back to resolve the nid.
        '''
        valt = dstsode.get('valu')
        if valt is not None:
            return valt

        (stortype, virts) = dstform.type.getStorInfo(dstndef[1])

        return (dstndef[1], stortype, virts)

    def _getStorInfo(self, prop, valu):
        '''
        Return the (valu, stortype, virts) triple to store a rewritten value with.

        The layer indexes and, critically, de-indexes a value using only the stortype and
        virts stored alongside it, so a pair which does not describe the value it
        accompanies leaves index rows no lift can find. Type.getStorInfo() is the only
        sanctioned way to build the pair, so every value this fuse changes goes through it
        rather than reusing the stortype the old value was stored with.
        '''
        (stortype, virts) = prop.type.getStorInfo(valu)

        return (valu, stortype, virts)

    async def _addComputedProps(self, dstnid, dstform, dstndef, srcsode, slotmap):
        '''
        Queue the computed property sets a dst being created in this layer needs.

        A computed property restates part of the node's own primary value, so it cannot be
        copied from src: it has to describe dst. Rather than re-deriving it from norm() -
        which would mean rebuilding the stored shape of a poly or comp typed sub property
        by hand - it is copied from storage, which is authoritative about that shape:

        - For the pair the caller named, dst is a node which already exists somewhere, so
          its own computed properties are read from whichever layer holds them.
        - For a comp-form cascade rename, dst is a value no node has held yet, so they are
          copied from the node being renamed with the slots this fuse changed substituted.
          A poly slot keeps the type name it was stored under, so the substituted value has
          the same shape as the one it replaces.
        '''
        if slotmap is None:

            # collected across every layer rather than taken from one of them, since dst
            # may have been created in a layer this fuse cannot write to and a computed
            # prop restates dst's own primary value, so every layer holding one agrees on
            # it. First writer wins per name, which is why the layer order does not matter.
            computed = self.dstcomputed.get(dstnid)

            if computed is None:

                computed = {}

                for sode in (await self._getSodes(dstnid)).values():
                    for name, valt in sode.get('props', {}).items():

                        if name in computed:
                            continue

                        prop = dstform.props.get(name)
                        if prop is None or not prop.info.get('computed'):
                            continue

                        computed[name] = valt

                self.dstcomputed[dstnid] = computed

            for name, valt in computed.items():
                await self._addEdit(dstnid, dstform.name, (
                    (s_layer.EDIT_PROP_SET, (name, valt[0], valt[1], valt[2])),
                ))

            return

        for name, valt in srcsode.get('props', {}).items():

            prop = dstform.props.get(name)
            if prop is None or not prop.info.get('computed'):
                continue

            valu = slotmap.get(name, s_common.novalu)
            if valu is s_common.novalu:
                # a computed prop this rename did not change restates a part of the value
                # which did not move, so the stored triple still describes dst
                await self._addEdit(dstnid, dstform.name, (
                    (s_layer.EDIT_PROP_SET, (name, valt[0], valt[1], valt[2])),
                ))
                continue

            (valu, stortype, virts) = self._getStorInfo(prop, valu)

            await self._addEdit(dstnid, dstform.name, (
                (s_layer.EDIT_PROP_SET, (name, valu, stortype, virts)),
            ))

    async def _rewriteRefs(self, layer, srcndef, dstndef):
        '''
        Queue this layer's edits which repoint inbound refs from src to dst.

        Every comp-key cascade rename was already discovered by getLayerEdits(), so a
        computed reference is always rewritten here rather than returning a new task: if
        it is a true comp-key reference, the comp node it belongs to already has its own
        entry in self.ndefmap, discovered by _discoverCascadeSrcs(), and is handled by its
        own call to this method. A computed reference which is *not* part of a comp key is
        rewritten in place - a stale but valid reference beats a dangling one, at the cost
        of the referring node's own primary property no longer matching it, which is
        documented as fuse() behavior.

        An array is rewritten via the rename map rather than by swapping only this call's
        own (srcndef, dstndef) pair, because a comp-form cascade means more than one rename
        can share this same fuse() call. Each rename's pass over a given layer reads the
        array fresh, before any of this fuse's edits have been applied to storage, so a pass
        which only patched the one item it was looking for would clobber an earlier pass's
        fix to a different item in that same array with a stale copy of it. Remapping every
        item through the rename map fixes every stale item on every pass, so whichever
        pass's edit ends up applied last still leaves the array fully correct.
        '''
        async for (refnid, prop, isarray, reftyp) in self._iterLayerRefs(layer, srcndef):

            refform = prop.form

            if prop.info.get('computed') and self._isCompSlot(refform, prop):
                continue

            # a referrer which is itself being fused away in this operation has its own
            # transfer pass, which reads this same prop and redirects it through the rename
            # map (see _swapSelfRef()), so the redirect is already accounted for. Queueing
            # it here as well would append a prop set after that nid's own EDIT_NODE_DEL in
            # the one coalesced nodeedit for it, and the storage layer does not no-op a
            # prop set against a deleted node: it would leave a sode holding props with no
            # valu, which no lift can reach and no re-run of this fuse can clean up.
            if self.visited.has(refnid):
                continue

            refsode = layer.getStorNode(refnid)

            curv = refsode.get('props', {}).get(prop.name)
            if curv is None:  # pragma: no cover
                continue

            # only the value is needed: the stortype and virts stored with it describe the
            # value being replaced, so the replacement derives its own pair below
            curv = curv[0]

            if isarray:
                newvalu = [self._remapSelfRef(item) for item in curv]
                setv = await self._swapArrayValu(prop, refnid, newvalu)
            else:
                # keyed by the type name the reference was actually stored under, which may be
                # an ancestor of src's own form, so the replacement stays filed the same way
                setv = self.polymap.get((reftyp, srcndef[1]))

            (setv, stortype, virts) = self._getStorInfo(prop, setv)

            await self._addEdit(refnid, refform.name, (
                (s_layer.EDIT_PROP_SET, (prop.name, setv, stortype, virts)),
            ))

    async def _iterLayerRefs(self, layer, srcndef):
        '''
        Yield (refnid, prop, isarray, reftyp) for props in this layer which point at src.

        This is used both to discover which comp-form references require a cascade rename,
        and to rewrite every inbound reference once every rename this fuse makes is known.

        3.x has no reverse index for node valued properties: the Ndef type and its index
        are gone, a node valued property is a poly, and the model's own registry of which
        properties accept a given type is what answers "who points at this node". So rather
        than one index scan per layer, this is one indexed lift per property the model says
        could hold a reference - the same shape Storm's reverse pivot uses (see
        PivotIn.getPivsIn) - and it walks the whole inheritance chain, because
        Model.getPropsByType() is keyed by the exact declared type and a poly declared for
        an ancestor form may hold, and may have filed the reference under, either the
        ancestor or the concrete form.

        A reference src holds to itself is never yielded. Those follow the node rather than
        being repointed in place, so _fuseOneLayer() transfers them to dst along with the
        rest of src's state; queueing an edit for them here would target a nid which is
        being torn down in the same pass.

        Args:
            layer (Layer): The layer to scan.
            srcndef (tuple): The (form, valu) of the node being referenced.

        Yields:
            tuple: (refnid, prop, isarray, reftyp) for each inbound reference.
        '''
        srcform = self.model.reqForm(srcndef[0])
        srcnid = await self.core.genNdefNid(srcndef)

        # Which form in the chain a property is *declared* for and which one a stored value
        # is *tagged* with are two separate things, so both are varied. A property declared
        # for an ancestor accepts the ancestor and everything below it, and Poly._canonType
        # keeps whichever of those the value was given, so the pair to try for a property
        # declared at ftyps[idx] is every tag from there down to the concrete form. Ordered
        # ancestor first so that idx slice means "this declared type and everything more
        # specific", the same pairing View.nodesByPropTypeNorm() makes.
        ftyps = srcform.formtypes[::-1]
        nrefs = [s_stormtypes.NodeRef(((ftyp, srcndef[1]), None)) for ftyp in ftyps]

        # A property is reachable from more than one form in the chain when it is a poly
        # declared for an interface, since Model.getPropsByType() merges the interface polys
        # of every form it is asked about and a child form implements everything its parent
        # does. Such a property is scanned once per form which reaches it, so the same
        # reference can be found more than once and must only be rewritten the first time.
        seen = set()

        # No property found this way can refuse the reference: Model.getPropsByType() returns
        # properties declared for ftyps[idx], and both Poly.formfilter() and Poly.typefilter()
        # test the whole inheritance chain of the candidate, so a poly which accepts a form
        # accepts every form below it - which is exactly the set reftyp ranges over.
        for idx, ftyp in enumerate(ftyps):

            for prop in self.model.getPropsByType(ftyp):

                for reftyp, nref in zip(ftyps[idx:], nrefs[idx:]):

                    cmprvals = await prop.type.getStorCmprs('=', nref)

                    async for _, refnid, _ in s_coro.pause(
                            layer.liftByPropValu(prop.form.name, prop.name, cmprvals)):

                        if refnid == srcnid:
                            continue

                        if (refnid, prop.full) in seen:
                            continue

                        seen.add((refnid, prop.full))

                        yield refnid, prop, False, reftyp

            for prop in self.model.getArrayPropsByType(ftyp):

                for reftyp, nref in zip(ftyps[idx:], nrefs[idx:]):

                    # an array is lifted by element through the member type; the array type
                    # itself only compares whole arrays and refuses a bare value
                    cmprvals = await prop.type.arraytype.getStorCmprs('=', nref)

                    async for _, refnid, _ in s_coro.pause(
                            layer.liftByPropArray(prop.form.name, prop.name, cmprvals)):

                        if refnid == srcnid:
                            continue

                        if (refnid, prop.full) in seen:
                            continue

                        seen.add((refnid, prop.full))

                        yield refnid, prop, True, reftyp

    async def applyLayerEdits(self, meta):
        '''
        Compute and apply every layer's edits, one layer at a time.

        getLayerEdits() must already have discovered every rename this fuse makes and
        resolved every destination into the rename map before this runs, since computing a
        layer's edits here uses that map to redirect a reference off of any node being
        fused away in this operation, not just off of the one currently being processed -
        see getLayerEdits() for why a partial map is not enough.

        Each layer's edits are queued into a spool scoped to that layer alone: created,
        applied, and finalized before moving on to the next layer, so a fuse touching many
        layers never needs more than one layer's worth of spooled state at a time.

        Args:
            meta (dict): The nodeedit meta to record, built from the useriden and tick.

        Returns:
            None. The warnings and the layers which failed are recorded on this NodeFuser and
            returned together by getResult().
        '''
        for layer in self.layers:

            layriden = layer.iden

            # The renames were discovered before any of them were applied, so re-check that
            # the layer is still one we may write to, since a read only layer would raise.
            # Checked before computing anything for this layer, so a layer which is no
            # longer writable does not pay for the computation either.
            if layer.readonly:
                await self.warn(
                    f'$lib.model.migration.fuse() did not modify layer {layriden} because it became '
                    f'read only while the fuse was being computed. Re-run fuse() with the same '
                    f'arguments.')
                continue

            # A layer deleted while the fuse was being computed is the same window as the
            # read only case above. saveNodeEdits() on it would raise and be recorded as a
            # failed layer, which tells the operator to re-run against a layer which no
            # longer exists - so it is reported as skipped rather than failed instead.
            if layer.isfini:
                await self.warn(
                    f'$lib.model.migration.fuse() did not modify layer {layriden} because it was '
                    f'deleted while the fuse was being computed. Nodes it held are gone with it '
                    f'and no re-run is needed for that layer.')
                continue

            async with await s_spooled.Dict.anit(dirn=self.core.dirn, cell=self.core) as nodeedits:

                self.nodeedits = nodeedits

                # getLayerEdits() resolves every rename before it returns, or refuses the
                # fuse, so each of these carries a destination - see _computeRenames().
                for (srcndef, rename) in self.ndefmap.items():

                    (dstndef, slotmap) = rename

                    await self._fuseOneLayer(layer, srcndef, dstndef, slotmap)

                try:
                    for editchunk in iterEditChunks(self._iterNodeEdits()):
                        await layer.saveNodeEdits(editchunk, meta)

                except asyncio.CancelledError:  # pragma: no cover
                    raise

                except Exception as e:
                    errm = str(e)
                    self.failed.append((layriden, errm))
                    await self.warn(
                        f'$lib.model.migration.fuse() failed to apply edits to layer {layriden}: {errm}. '
                        f'That layer may be only partly modified. Re-run fuse() with the same arguments '
                        f'to complete it.')

                self.nodeedits = None

def iterEditChunks(nodeedits, chunk=None):
    '''
    Yield one layer's nodeedits as chunks of no more than chunk edits.

    Each chunk becomes the payload of one of that layer's nexus operations, which bounds how
    large a single nexus log entry can get without capping how large a fuse may be.
    Layer.saveNodeEdits() resolving the edits against current state makes a re-run
    idempotent, but it still writes the whole list it is handed as one nexus payload, so
    the bound is still needed.

    Two properties are load bearing, and test_nodefuse_edit_chunks() covers each of them:

    1. A nodeedit is never split. The edits for one nid are order dependent: dst's
       EDIT_NODE_ADD must be applied before any prop set for that nid, otherwise the sode
       has props but no valu and reads as a node which does not exist. A chunk therefore
       overshoots rather than splitting a nid, so chunk is a floor and not a ceiling.

    2. The order of the nodeedits is preserved. NodeFuser._iterNodeEdits() orders every edit
       which adds to dst or repoints a reference ahead of every edit which removes state from
       src, so an interruption cannot lose state or leave a reference pointing at a deleted
       node.

    Args:
        nodeedits (iterable): One layer's nodeedits from NodeFuser._iterNodeEdits().
        chunk (int): The maximum edits per chunk. Defaults to maxchunkedits.

    Yields:
        list: A list of nodeedits to apply with one call to Layer.saveNodeEdits().
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
