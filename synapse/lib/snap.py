from __future__ import annotations

import types
import asyncio
import logging
import weakref
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.json as s_json
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.storm as s_storm
import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

class Scrubber:

    def __init__(self, rules):
        self.rules = rules
        # TODO support props
        # TODO support tagprops
        # TODO support exclude rules
        incs = rules.get('include', {})

        self.hasinctags = incs.get('tags') is not None
        self.inctags = set(incs.get('tags', ()))
        self.inctagprefs = [f'{tag}.' for tag in incs.get('tags', ())]

    def scrub(self, pode):

        if self.hasinctags and pode[1].get('tags'):
            pode[1]['tags'] = {k: v for (k, v) in pode[1]['tags'].items() if self._isTagInc(k)}

            if pode[1].get('tagprops'):
                pode[1]['tagprops'] = {k: v for (k, v) in pode[1]['tagprops'].items() if self._isTagInc(k)}

        return pode

    @s_cache.memoizemethod()
    def _isTagInc(self, tag):
        if tag in self.inctags:
            return True
        if any(tag.startswith(pref) for pref in self.inctagprefs):
            return True
        return False

class ProtoNode:
    '''
    A prototype node used for staging node adds using a SnapEditor.

    TODO: This could eventually fully mirror the synapse.lib.node.Node API and be used
          to slipstream into sections of the pipeline to facilitate a bulk edit / transaction
    '''
    def __init__(self, ctx, buid, form, valu, node):
        self.ctx = ctx
        self.form = form
        self.valu = valu
        self.buid = buid
        self.node = node

        self.tags = {}
        self.props = {}
        self.edges = set()
        self.tagprops = {}
        self.nodedata = {}

        self.edgedels = set()

    def iden(self):
        return s_common.ehex(self.buid)

    def getNodeEdit(self):

        edits = []

        if not self.node:
            edits.append((s_layer.EDIT_NODE_ADD, (self.valu, self.form.type.stortype), ()))

        for name, valu in self.props.items():
            prop = self.form.props.get(name)
            edits.append((s_layer.EDIT_PROP_SET, (name, valu, None, prop.type.stortype), ()))

        for name, valu in self.tags.items():
            edits.append((s_layer.EDIT_TAG_SET, (name, valu, None), ()))

        for verb, n2iden in self.edges:
            edits.append((s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()))

        for verb, n2iden in self.edgedels:
            edits.append((s_layer.EDIT_EDGE_DEL, (verb, n2iden), ()))

        for (tag, name), valu in self.tagprops.items():
            prop = self.ctx.snap.core.model.getTagProp(name)
            edits.append((s_layer.EDIT_TAGPROP_SET, (tag, name, valu, None, prop.type.stortype), ()))

        for name, valu in self.nodedata.items():
            edits.append((s_layer.EDIT_NODEDATA_SET, (name, valu, None), ()))

        if not edits:
            return None

        return (self.buid, self.form.name, edits)

    async def addEdge(self, verb, n2iden):

        if not isinstance(verb, str):
            mesg = f'addEdge() got an invalid type for verb: {verb}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if not isinstance(n2iden, str):
            mesg = f'addEdge() got an invalid type for n2iden: {n2iden}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if not s_common.isbuidhex(n2iden):
            mesg = f'addEdge() got an invalid node iden: {n2iden}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        tupl = (verb, n2iden)
        if tupl in self.edges:
            return False

        if tupl in self.edgedels:
            self.edgedels.remove(tupl)
            return True

        if not await self.ctx.snap.hasNodeEdge(self.buid, verb, s_common.uhex(n2iden)):
            self.edges.add(tupl)
            if len(self.edges) >= 1000:
                await self.flushEdits()
            return True

        return False

    async def flushEdits(self):
        if (nodeedit := self.getNodeEdit()) is not None:
            nodecache = {self.buid: self.node}
            nodes = await self.ctx.snap.applyNodeEdits((nodeedit,), nodecache=nodecache, meta=self.ctx.meta)

            if self.node is None:
                if nodes and nodes[0].buid == self.buid:
                    self.node = nodes[0]
                else:  # pragma: no cover
                    self.node = await self.ctx.snap.getNodeByBuid(self.buid)

            self.tags.clear()
            self.props.clear()
            self.tagprops.clear()
            self.edges.clear()
            self.edgedels.clear()
            self.nodedata.clear()

    async def delEdge(self, verb, n2iden):

        if not isinstance(verb, str):
            mesg = f'delEdge() got an invalid type for verb: {verb}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if not isinstance(n2iden, str):
            mesg = f'delEdge() got an invalid type for n2iden: {n2iden}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if not s_common.isbuidhex(n2iden):
            mesg = f'delEdge() got an invalid node iden: {n2iden}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        tupl = (verb, n2iden)
        if tupl in self.edgedels:
            return False

        if tupl in self.edges:
            self.edges.remove(tupl)
            return True

        if await self.ctx.snap.layers[-1].hasNodeEdge(self.buid, verb, s_common.uhex(n2iden)):
            self.edgedels.add(tupl)
            if len(self.edgedels) >= 1000:
                await self.flushEdits()
            return True

        return False

    async def getData(self, name):

        curv = self.nodedata.get(name, s_common.novalu)
        if curv is not s_common.novalu:
            return curv

        if self.node is not None:
            return await self.node.getData(name, defv=s_common.novalu)

        return s_common.novalu

    async def hasData(self, name):
        if name in self.nodedata:
            return True

        if self.node is not None:
            return await self.node.hasData(name)

        return False

    async def setData(self, name, valu):

        if await self.getData(name) == valu:
            return

        try:
            s_json.reqjsonsafe(valu)
        except s_exc.MustBeJsonSafe as e:
            if self.ctx.snap.strict:
                raise e
            return await self.ctx.snap.warn(str(e))

        self.nodedata[name] = valu

    async def _getRealTag(self, tag):

        normtupl = await self.ctx.snap.getTagNorm(tag)
        if normtupl is None:
            return None

        norm, info = normtupl

        tagnode = await self.ctx.snap.getTagNode(norm)
        if tagnode is not s_common.novalu:
            return self.ctx.loadNode(tagnode)

        # check for an :isnow tag redirection in our hierarchy...
        toks = info.get('toks')
        for i in range(len(toks)):

            toktag = '.'.join(toks[:i + 1])
            toknode = await self.ctx.snap.getTagNode(toktag)
            if toknode is s_common.novalu:
                continue

            tokvalu = toknode.ndef[1]
            if tokvalu == toktag:
                continue

            realnow = tokvalu + norm[len(toktag):]
            tagnode = await self.ctx.snap.getTagNode(realnow)
            if tagnode is not s_common.novalu:
                return self.ctx.loadNode(tagnode)

            norm, info = await self.ctx.snap.getTagNorm(realnow)
            break

        return await self.ctx.addNode('syn:tag', norm, norminfo=info)

    def getTag(self, tag):

        curv = self.tags.get(tag)
        if curv is not None:
            return curv

        if self.node is not None:
            return self.node.getTag(tag)

    async def addTag(self, tag, valu=(None, None), tagnode=None):

        if tagnode is None:
            tagnode = await self._getRealTag(tag)

        if tagnode is None:
            return

        if isinstance(valu, list):
            valu = tuple(valu)

        if valu != (None, None):
            try:
                valu, _ = self.ctx.snap.core.model.type('ival').norm(valu)
            except s_exc.BadTypeValu as e:
                if self.ctx.snap.strict:
                    e.set('tag', tagnode.valu)
                    raise e
                return await self.ctx.snap.warn(f'Invalid Tag Value: {tagnode.valu}={valu}.')

        tagup = tagnode.get('up')
        if tagup:
            await self.addTag(tagup)

        curv = self.getTag(tagnode.valu)
        if curv == valu:
            return tagnode

        if curv is None:
            self.tags[tagnode.valu] = valu
            return tagnode

        valu = s_time.ival(*valu, *curv)
        self.tags[tagnode.valu] = valu

        return tagnode

    def getTagProp(self, tag, name):

        curv = self.tagprops.get((tag, name))
        if curv is not None:
            return curv

        if self.node is not None:
            return self.node.getTagProp(tag, name)

    def hasTagProp(self, tag, name):
        if (tag, name) in self.tagprops:
            return True

        if self.node is not None:
            return self.node.hasTagProp(tag, name)

        return False

    async def setTagProp(self, tag, name, valu):

        tagnode = await self.addTag(tag)
        if tagnode is None:
            return

        prop = self.ctx.snap.core.model.getTagProp(name)
        if prop is None:
            mesg = f'Tagprop {name} does not exist in this Cortex.'
            return await self.ctx.snap._raiseOnStrict(s_exc.NoSuchTagProp, mesg)

        if prop.locked:
            mesg = f'Tagprop {name} is locked.'
            return await self.ctx.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg, prop=name)

        try:
            norm, info = prop.type.norm(valu)
        except s_exc.BadTypeValu as e:
            if self.ctx.snap.strict:
                raise e
            await self.ctx.snap.warn(f'Bad property value: #{tagnode.valu}:{prop.name}={valu!r}')
            return

        curv = self.getTagProp(tagnode.valu, name)
        if curv == norm:
            return

        self.tagprops[(tagnode.valu, name)] = norm

    def get(self, name):

        # get the current value including the pending prop sets
        curv = self.props.get(name)
        if curv is not None:
            return curv

        if self.node is not None:
            return self.node.get(name)

    async def _set(self, prop, valu, norminfo=None, ignore_ro=False):

        if prop.locked:
            mesg = f'Prop {prop.full} is locked due to deprecation.'
            await self.ctx.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg, prop=prop.full)
            return False

        if isinstance(prop.type, s_types.Array):
            arrayform = self.ctx.snap.core.model.form(prop.type.arraytype.name)
            if arrayform is not None and arrayform.locked:
                mesg = f'Prop {prop.full} is locked due to deprecation.'
                await self.ctx.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg, prop=prop.full)
                return False

        if norminfo is None:
            try:
                valu, norminfo = prop.type.norm(valu)
            except s_exc.BadTypeValu as e:
                oldm = e.get('mesg')
                e.update({'prop': prop.name,
                          'form': prop.form.name,
                          'mesg': f'Bad prop value {prop.full}={valu!r} : {oldm}'})
                if self.ctx.snap.strict:
                    raise e
                await self.ctx.snap.warn(e)
                return False

        if isinstance(prop.type, s_types.Ndef):
            ndefform = self.ctx.snap.core.model.form(valu[0])
            if ndefform.locked:
                mesg = f'Prop {prop.full} is locked due to deprecation.'
                await self.ctx.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg, prop=prop.full)
                return False

        curv = self.get(prop.name)
        if curv == valu:
            return False

        if not ignore_ro and prop.info.get('ro') and curv is not None:
            mesg = f'Property is read only: {prop.full}.'
            await self.ctx.snap._raiseOnStrict(s_exc.ReadOnlyProp, mesg)
            return False

        if self.node is not None:
            await self.ctx.snap.core._callPropSetHook(self.node, prop, valu)

        self.props[prop.name] = valu

        return valu, norminfo

    async def set(self, name, valu, norminfo=None, ignore_ro=False):
        prop = self.form.props.get(name)
        if prop is None:
            return False

        retn = await self._set(prop, valu, norminfo=norminfo, ignore_ro=ignore_ro)
        if retn is False:
            return False

        (valu, norminfo) = retn

        propform = self.ctx.snap.core.model.form(prop.type.name)
        if propform is not None:
            await self.ctx.addNode(propform.name, valu, norminfo=norminfo)

        # TODO can we mandate any subs are returned pre-normalized?
        propsubs = norminfo.get('subs')
        if propsubs is not None:
            for subname, subvalu in propsubs.items():
                full = f'{prop.name}:{subname}'
                subprop = self.form.props.get(full)
                if subprop is not None and not subprop.locked:
                    if subprop.deprecated:
                        self.ctx.snap._skipPropDeprWarn(subprop.full)

                    await self.set(full, subvalu)

        propadds = norminfo.get('adds')
        if propadds is not None:
            for addname, addvalu, addinfo in propadds:
                await self.ctx.addNode(addname, addvalu, norminfo=addinfo)

        return True

    async def getSetSubOps(self, name, valu, norminfo=None):
        prop = self.form.props.get(name)
        if prop is None or prop.locked:
            return ()

        if prop.deprecated:
            self.ctx.snap._skipPropDeprWarn(prop.full)

        retn = await self._set(prop, valu, norminfo=norminfo)
        if retn is False:
            return ()

        (valu, norminfo) = retn
        ops = []

        propform = self.ctx.snap.core.model.form(prop.type.name)
        if propform is not None:
            ops.append(self.ctx.getAddNodeOps(propform.name, valu, norminfo=norminfo))

        # TODO can we mandate any subs are returned pre-normalized?
        propsubs = norminfo.get('subs')
        if propsubs is not None:
            for subname, subvalu in propsubs.items():
                full = f'{prop.name}:{subname}'
                ops.append(self.getSetSubOps(full, subvalu))

        propadds = norminfo.get('adds')
        if propadds is not None:
            for addname, addvalu, addinfo in propadds:
                ops.append(self.ctx.getAddNodeOps(addname, addvalu, norminfo=addinfo))

        return ops

class SnapEditor:
    '''
    A SnapEditor allows tracking node edits with subs/deps as a transaction.
    '''
    def __init__(self, snap, meta=None):
        self.meta = meta
        self.snap = snap
        self.protonodes = {}
        self.maxnodes = snap.core.maxnodes

    async def getNodeByBuid(self, buid):
        node = await self.snap.getNodeByBuid(buid)
        if node:
            return self.loadNode(node)

    def getNodeEdits(self):
        nodeedits = []
        for protonode in self.protonodes.values():
            nodeedit = protonode.getNodeEdit()
            if nodeedit is not None:
                nodeedits.append(nodeedit)
        return nodeedits

    async def flushEdits(self):
        nodecache = {}
        nodeedits = []
        for protonode in self.protonodes.values():
            if (nodeedit := protonode.getNodeEdit()) is not None:
                nodeedits.append(nodeedit)
                nodecache[protonode.buid] = protonode.node

        if nodeedits:
            await self.snap.applyNodeEdits(nodeedits, nodecache=nodecache, meta=self.meta)

        self.protonodes.clear()

    async def _addNode(self, form, valu, props=None, norminfo=None):

        self.snap.core._checkMaxNodes()

        if form.isrunt:
            mesg = f'Cannot make runt nodes: {form.name}.'
            return await self.snap._raiseOnStrict(s_exc.IsRuntForm, mesg)

        if form.locked:
            mesg = f'Form {form.full} is locked due to deprecation for valu={valu}.'
            return await self.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg, prop=form.full)

        if norminfo is None:
            try:
                valu, norminfo = form.type.norm(valu)
            except s_exc.BadTypeValu as e:
                e.set('form', form.name)
                if self.snap.strict: raise e
                await self.snap.warn(f'addNode() BadTypeValu {form.name}={valu} {e}')
                return None

        return valu, norminfo

    async def addNode(self, formname, valu, props=None, norminfo=None):

        form = self.snap.core.model.form(formname)
        if form is None:
            mesg = f'No form named {formname} for valu={valu}.'
            return await self.snap._raiseOnStrict(s_exc.NoSuchForm, mesg)

        retn = await self._addNode(form, valu, props=props, norminfo=norminfo)
        if retn is None:
            return None

        valu, norminfo = retn

        protonode = await self._initProtoNode(form, valu, norminfo)
        if props is not None:
            [await protonode.set(p, v) for (p, v) in props.items()]

        return protonode

    async def getAddNodeOps(self, formname, valu, props=None, norminfo=None):

        form = self.snap.core.model.form(formname)
        if form is None:
            mesg = f'No form named {formname} for valu={valu}.'
            await self.snap._raiseOnStrict(s_exc.NoSuchForm, mesg)
            return()

        retn = await self._addNode(form, valu, props=props, norminfo=norminfo)
        if retn is None:
            return ()

        norm, norminfo = retn

        ndef = (form.name, norm)

        protonode = self.protonodes.get(ndef)
        if protonode is not None:
            return ()

        buid = s_common.buid(ndef)
        node = await self.snap.getNodeByBuid(buid)
        if node is not None:
            return ()

        protonode = ProtoNode(self, buid, form, norm, node)

        self.protonodes[ndef] = protonode

        ops = []

        subs = norminfo.get('subs')
        if subs is not None:
            for prop, valu in subs.items():
                ops.append(protonode.getSetSubOps(prop, valu))

        adds = norminfo.get('adds')
        if adds is not None:
            for addname, addvalu, addinfo in adds:
                ops.append(self.getAddNodeOps(addname, addvalu, norminfo=addinfo))

        return ops

    def loadNode(self, node):
        protonode = self.protonodes.get(node.ndef)
        if protonode is None:
            protonode = ProtoNode(self, node.buid, node.form, node.ndef[1], node)
            self.protonodes[node.ndef] = protonode
        return protonode

    async def _initProtoNode(self, form, norm, norminfo):

        ndef = (form.name, norm)

        protonode = self.protonodes.get(ndef)
        if protonode is not None:
            return protonode

        buid = s_common.buid(ndef)
        node = await self.snap.getNodeByBuid(buid)

        protonode = ProtoNode(self, buid, form, norm, node)

        self.protonodes[ndef] = protonode

        ops = collections.deque()

        subs = norminfo.get('subs')
        if subs is not None:
            for prop, valu in subs.items():
                ops.append(protonode.getSetSubOps(prop, valu))

            while ops:
                oset = ops.popleft()
                ops.extend(await oset)

        adds = norminfo.get('adds')
        if adds is not None:
            for addname, addvalu, addinfo in adds:
                ops.append(self.getAddNodeOps(addname, addvalu, norminfo=addinfo))

            while ops:
                oset = ops.popleft()
                ops.extend(await oset)

        return protonode

class Snap(s_base.Base):
    '''
    A "snapshot" is a transaction across multiple Cortex layers.

    The Snap object contains the bulk of the Cortex API to
    facilitate performance through careful use of transaction
    boundaries.

    Transactions produce the following EventBus events:

    ('print', {}),
    '''
    tagcachesize = 1000
    buidcachesize = 100000

    async def __anit__(self, view, user):
        '''
        Args:
            core (cortex):  the cortex
            layers (List[Layer]): the list of layers to access, write layer last
        '''
        await s_base.Base.__anit__(self)

        assert user is not None

        self.strict = True
        self.elevated = False
        self.canceled = False

        self.core = view.core
        self.view = view
        self.user = user

        self.layers = list(reversed(view.layers))
        self.wlyr = self.layers[-1]

        self.readonly = self.wlyr.readonly

        # variables used by the storm runtime
        self.vars = {}

        self.runt = {}

        self.debug = False      # Set to true to enable debug output.
        self.write = False      # True when the snap has a write lock on a layer.
        self.cachebuids = True

        self.tagnorms = s_cache.FixedCache(self._getTagNorm, size=self.tagcachesize)
        self.tagcache = s_cache.FixedCache(self._getTagNode, size=self.tagcachesize)
        # Keeps alive the most recently accessed node objects
        self.buidcache = collections.deque(maxlen=self.buidcachesize)
        self.livenodes = weakref.WeakValueDictionary()  # buid -> Node
        self._warnonce_keys = set()

        self.changelog = []
        self.tagtype = self.core.model.type('ival')

    async def getSnapMeta(self):
        '''
        Retrieve snap metadata to store along side nodeEdits.
        '''
        meta = {
            'time': s_common.now(),
            'user': self.user.iden
        }

        return meta

    @contextlib.asynccontextmanager
    async def getStormRuntime(self, query, opts=None, user=None):
        if user is None:
            user = self.user

        if opts is not None:
            varz = opts.get('vars')
            if varz is not None:
                for valu in varz.keys():
                    if not isinstance(valu, str):
                        mesg = f"Storm var names must be strings (got {valu} of type {type(valu)})"
                        raise s_exc.BadArg(mesg=mesg)

        async with await s_storm.Runtime.anit(query, self, opts=opts, user=user) as runt:
            yield runt

    async def addStormRuntime(self, query, opts=None, user=None):
        # use this snap *as* a context manager and build a runtime that will live as long
        # as the snap does...
        if user is None:
            user = self.user

        runt = await s_storm.Runtime.anit(query, self, opts=opts, user=user)
        self.onfini(runt)
        return runt

    async def _joinEmbedStor(self, storage, embeds):
        for nodePath, relProps in embeds.items():
            await asyncio.sleep(0)
            iden = relProps.get('*')
            if not iden:
                continue

            stor = await self.view.getStorNodes(s_common.uhex(iden))
            for relProp in relProps.keys():
                await asyncio.sleep(0)
                if relProp == '*':
                    continue

                for idx, layrstor in enumerate(stor):
                    await asyncio.sleep(0)
                    props = layrstor.get('props')
                    if not props:
                        continue

                    if relProp not in props:
                        continue

                    if 'embeds' not in storage[idx]:
                        storage[idx]['embeds'] = {}

                    storage[idx]['embeds'][f'{nodePath}::{relProp}'] = props[relProp]

    async def iterStormPodes(self, text, opts, user=None):
        '''
        Yield packed node tuples for the given storm query text.
        '''
        if user is None:
            user = self.user

        dorepr = False
        dopath = False
        dolink = False

        show_storage = False

        info = opts.get('_loginfo', {})
        info.update({'mode': opts.get('mode', 'storm'), 'view': self.view.iden})
        self.core._logStormQuery(text, user, info=info)

        # { form: ( embedprop, ... ) }
        embeds = opts.get('embeds')

        scrubber = None
        # NOTE: This option is still experimental and subject to change.
        if opts.get('scrub') is not None:
            scrubber = Scrubber(opts.get('scrub'))

        if opts is not None:
            dorepr = opts.get('repr', False)
            dopath = opts.get('path', False)
            dolink = opts.get('links', False)
            show_storage = opts.get('show:storage', False)

        async for node, path in self.storm(text, opts=opts, user=user):

            pode = node.pack(dorepr=dorepr)
            pode[1]['path'] = await path.pack(path=dopath)

            if dolink:
                pode[1]['links'] = path.links

            if show_storage:
                pode[1]['storage'] = await node.getStorNodes()

            if scrubber is not None:
                pode = scrubber.scrub(pode)

            if embeds is not None:
                embdef = embeds.get(node.form.name)
                if embdef is not None:
                    pode[1]['embeds'] = await node.getEmbeds(embdef)
                    if show_storage:
                        await self._joinEmbedStor(pode[1]['storage'], pode[1]['embeds'])

            yield pode

    async def storm(self, text, opts=None, user=None):
        '''
        Execute a storm query and yield (Node(), Path()) tuples.
        '''
        if user is None:
            user = self.user

        if opts is None:
            opts = {}

        mode = opts.get('mode', 'storm')

        query = await self.core.getStormQuery(text, mode=mode)
        async with self.getStormRuntime(query, opts=opts, user=user) as runt:
            async for x in runt.execute():
                yield x

    async def eval(self, text, opts=None, user=None):
        '''
        Run a storm query and yield Node() objects.
        '''
        if user is None:
            user = self.user

        if opts is None:
            opts = {}

        mode = opts.get('mode', 'storm')

        # maintained for backward compatibility
        query = await self.core.getStormQuery(text, mode=mode)
        async with self.getStormRuntime(query, opts=opts, user=user) as runt:
            async for node, path in runt.execute():
                yield node

    async def nodes(self, text, opts=None, user=None):
        return [node async for (node, path) in self.storm(text, opts=opts, user=user)]

    async def clearCache(self):
        self.tagcache.clear()
        self.tagnorms.clear()
        self.buidcache.clear()
        self.livenodes.clear()

    def clearCachedNode(self, buid):
        self.livenodes.pop(buid, None)

    async def keepalive(self, period):
        while not await self.waitfini(period):
            await self.fire('ping')

    async def printf(self, mesg):
        await self.fire('print', mesg=mesg)

    async def warn(self, mesg, log=True, **info):
        if log:
            logger.warning(mesg)
        await self.fire('warn', mesg=mesg, **info)

    async def warnonce(self, mesg, log=True, **info):
        if mesg in self._warnonce_keys:
            return
        self._warnonce_keys.add(mesg)
        await self.warn(mesg, log, **info)

    def _skipPropDeprWarn(self, name):
        mesg = f'The property {name} is deprecated or using a deprecated type and will be removed in 3.0.0'
        self._warnonce_keys.add(mesg)

    async def getNodeByBuid(self, buid):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            Optional[s_node.Node]: The node object or None.

        '''
        return await self._joinStorNode(buid, {})

    async def getNodeByNdef(self, ndef):
        '''
        Return a single Node by (form,valu) tuple.

        Args:
            ndef ((str,obj)): A (form,valu) ndef tuple.  valu must be
            normalized.

        Returns:
            (synapse.lib.node.Node): The Node or None.
        '''
        buid = s_common.buid(ndef)
        return await self.getNodeByBuid(buid)

    async def nodesByTagProp(self, form, tag, name, reverse=False):
        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        async for (buid, sodes) in self.core._liftByTagProp(form, tag, name, self.layers, reverse=reverse):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByTagPropValu(self, form, tag, name, cmpr, valu, reverse=False):
        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        cmprvals = prop.type.getStorCmprs(cmpr, valu)
        # an empty return probably means ?= with invalid value
        if not cmprvals:
            return

        async for (buid, sodes) in self.core._liftByTagPropValu(form, tag, name, cmprvals, self.layers, reverse=reverse):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def _joinStorNode(self, buid, cache):

        node = self.livenodes.get(buid)
        if node is not None:
            await asyncio.sleep(0)
            return node

        layrs = [layr for layr in self.layers if layr.iden not in cache]
        if layrs:
            indx = 0
            newsodes = await self.core._getStorNodes(buid, layrs)

        sodes = []
        for layr in self.layers:
            sode = cache.get(layr.iden)
            if sode is None:
                sode = newsodes[indx]
                indx += 1
            sodes.append((layr.iden, sode))

        return await self._joinSodes(buid, sodes)

    async def _joinSodes(self, buid, sodes):

        node = self.livenodes.get(buid)
        if node is not None:
            await asyncio.sleep(0)
            return node

        ndef = None
        tags = {}
        props = {}
        nodedata = {}
        tagprops = {}

        bylayer = {
            'ndef': None,
            'tags': {},
            'props': {},
            'tagprops': {},
        }

        for (layr, sode) in sodes:

            form = sode.get('form')
            valt = sode.get('valu')
            if valt is not None:
                ndef = (form, valt[0])
                bylayer['ndef'] = layr

            storprops = sode.get('props')
            if storprops is not None:
                for prop, (valu, stype) in storprops.items():
                    props[prop] = valu
                    bylayer['props'][prop] = layr

            stortags = sode.get('tags')
            if stortags is not None:
                tags.update(stortags)
                bylayer['tags'].update({p: layr for p in stortags.keys()})

            stortagprops = sode.get('tagprops')
            if stortagprops is not None:
                for tag, propdict in stortagprops.items():
                    for tagprop, (valu, stype) in propdict.items():
                        if tag not in tagprops:
                            tagprops[tag] = {}
                            bylayer['tagprops'][tag] = {}

                        tagprops[tag][tagprop] = valu
                        bylayer['tagprops'][tag][tagprop] = layr

            stordata = sode.get('nodedata')
            if stordata is not None:
                nodedata.update(stordata)

        if ndef is None:
            await asyncio.sleep(0)
            return None

        pode = (buid, {
            'ndef': ndef,
            'tags': tags,
            'props': props,
            'nodedata': nodedata,
            'tagprops': tagprops,
        })

        node = s_node.Node(self, pode, bylayer=bylayer)
        if self.cachebuids:
            self.livenodes[buid] = node
            self.buidcache.append(node)

        await asyncio.sleep(0)
        return node

    async def nodesByDataName(self, name):
        async for (buid, sodes) in self.core._liftByDataName(name, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByProp(self, full, reverse=False):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if prop.isrunt:
            async for node in self.getRuntNodes(prop.full):
                yield node
            return

        if prop.isform:
            async for (buid, sodes) in self.core._liftByProp(prop.name, None, self.layers, reverse=reverse):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        if prop.isuniv:
            async for (buid, sodes) in self.core._liftByProp(None, prop.name, self.layers, reverse=reverse):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        formname = None
        if not prop.isuniv:
            formname = prop.form.name

        # Prop is secondary prop
        async for (buid, sodes) in self.core._liftByProp(formname, prop.name, self.layers, reverse=reverse):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByPropValu(self, full, cmpr, valu, reverse=False, norm=True):
        if cmpr == 'type=':
            if reverse:
                async for node in self.nodesByPropTypeValu(full, valu, reverse=reverse):
                    yield node

                async for node in self.nodesByPropValu(full, '=', valu, reverse=reverse):
                    yield node
            else:
                async for node in self.nodesByPropValu(full, '=', valu, reverse=reverse):
                    yield node

                async for node in self.nodesByPropTypeValu(full, valu, reverse=reverse):
                    yield node
            return

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if isinstance(valu, dict) and isinstance(prop.type, s_types.Guid) and cmpr == '=':
            if prop.isform:
                if (node := await self._getGuidNodeByDict(prop, valu)) is not None:
                    yield node
                return

            fname = prop.type.name
            if (form := prop.modl.form(fname)) is None:
                mesg = f'The property "{full}" type "{fname}" is not a form and cannot be lifted using a dictionary.'
                raise s_exc.BadTypeValu(mesg=mesg)

            if (node := await self._getGuidNodeByDict(form, valu)) is None:
                return

            norm = False
            valu = node.ndef[1]

        if norm:
            cmprvals = prop.type.getStorCmprs(cmpr, valu)
            # an empty return probably means ?= with invalid value
            if not cmprvals:
                return
        else:
            cmprvals = ((cmpr, valu, prop.type.stortype),)

        if prop.isrunt:
            for storcmpr, storvalu, _ in cmprvals:
                async for node in self.getRuntNodes(prop.full, valu=storvalu, cmpr=storcmpr):
                    yield node
            return

        if prop.isform:
            async for (buid, sodes) in self.core._liftByFormValu(prop.name, cmprvals, self.layers, reverse=reverse):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node

            return

        if prop.isuniv:
            async for (buid, sodes) in self.core._liftByPropValu(None, prop.name, cmprvals, self.layers, reverse=reverse):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        async for (buid, sodes) in self.core._liftByPropValu(prop.form.name, prop.name, cmprvals, self.layers, reverse=reverse):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByTag(self, tag, form=None, reverse=False):
        async for (buid, sodes) in self.core._liftByTag(tag, form, self.layers, reverse=reverse):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByTagValu(self, tag, cmpr, valu, form=None, reverse=False):
        norm, info = self.core.model.type('ival').norm(valu)
        async for (buid, sodes) in self.core._liftByTagValu(tag, cmpr, norm, form, self.layers, reverse=reverse):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByPropTypeValu(self, name, valu, reverse=False):

        _type = self.core.model.types.get(name)
        if _type is None:
            raise s_exc.NoSuchType(name=name)

        for prop in self.core.model.getPropsByType(name):
            async for node in self.nodesByPropValu(prop.full, '=', valu, reverse=reverse):
                yield node

        for prop in self.core.model.getArrayPropsByType(name):
            async for node in self.nodesByPropArray(prop.full, '=', valu, reverse=reverse):
                yield node

    async def nodesByPropArray(self, full, cmpr, valu, reverse=False, norm=True):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if not isinstance(prop.type, s_types.Array):
            mesg = f'Array syntax is invalid on non array type: {prop.type.name}.'
            raise s_exc.BadTypeValu(mesg=mesg)

        if norm:
            cmprvals = prop.type.arraytype.getStorCmprs(cmpr, valu)
        else:
            cmprvals = ((cmpr, valu, prop.type.arraytype.stortype),)

        if prop.isform:
            async for (buid, sodes) in self.core._liftByPropArray(prop.name, None, cmprvals, self.layers, reverse=reverse):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        formname = None
        if prop.form is not None:
            formname = prop.form.name

        async for (buid, sodes) in self.core._liftByPropArray(formname, prop.name, cmprvals, self.layers, reverse=reverse):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    @contextlib.asynccontextmanager
    async def getNodeEditor(self, node):

        if node.form.isrunt:
            mesg = f'Cannot edit runt nodes: {node.form.name}.'
            raise s_exc.IsRuntForm(mesg=mesg)

        editor = SnapEditor(self)
        protonode = editor.loadNode(node)

        yield protonode

        nodeedits = editor.getNodeEdits()
        if nodeedits:
            nodecache = {proto.buid: proto.node for proto in editor.protonodes.values()}
            await self.applyNodeEdits(nodeedits, nodecache=nodecache)

    @contextlib.asynccontextmanager
    async def getEditor(self):

        editor = SnapEditor(self)

        yield editor

        nodeedits = editor.getNodeEdits()
        if nodeedits:
            nodecache = {proto.buid: proto.node for proto in editor.protonodes.values()}
            await self.applyNodeEdits(nodeedits, nodecache=nodecache)

    async def applyNodeEdit(self, edit, nodecache=None):
        nodes = await self.applyNodeEdits((edit,), nodecache=nodecache)
        if nodes:
            return nodes[0]

    async def applyNodeEdits(self, edits, nodecache=None, meta=None):
        '''
        Sends edits to the write layer and evaluates the consequences (triggers, node object updates)
        '''
        if meta is None:
            meta = await self.getSnapMeta()

        saveoff, changes, nodes = await self._applyNodeEdits(edits, meta, nodecache=nodecache)
        return nodes

    async def saveNodeEdits(self, edits, meta):
        if meta is None:
            meta = await self.getSnapMeta()

        saveoff = -1
        changes = []

        for edit in edits:
            await self.getNodeByBuid(edit[0])
            saveoff, changes_, _ = await self._applyNodeEdits((edit,), meta)
            changes.extend(changes_)

        return saveoff, changes

    async def _applyNodeEdits(self, edits, meta, nodecache=None):

        if self.readonly:
            mesg = 'The snapshot is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        wlyr = self.wlyr
        nodes = []
        callbacks = []
        actualedits = []  # List[Tuple[buid, form, changes]]

        saveoff, changes, results = await wlyr._realSaveNodeEdits(edits, meta)

        # make a pass through the returned edits, apply the changes to our Nodes()
        # and collect up all the callbacks to fire at once at the end.  It is
        # critical to fire all callbacks after applying all Node() changes.

        for buid, sode, postedits in results:

            cache = {wlyr.iden: sode}

            node = None
            if nodecache is not None:
                node = nodecache.get(buid)

            if node is None:
                node = await self._joinStorNode(buid, cache)
                if node is None:
                    # We got part of a node but no ndef
                    continue
            else:
                await asyncio.sleep(0)

            nodes.append(node)

            if postedits:
                actualedits.append((buid, node.form.name, postedits))

            for edit in postedits:

                etyp, parms, _ = edit

                if etyp == s_layer.EDIT_NODE_ADD:
                    node.bylayer['ndef'] = wlyr.iden
                    callbacks.append((node.form.wasAdded, (node,), {}))
                    callbacks.append((self.view.runNodeAdd, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_NODE_DEL:
                    callbacks.append((node.form.wasDeleted, (node,), {}))
                    callbacks.append((self.view.runNodeDel, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_SET:

                    (name, valu, oldv, stype) = parms

                    prop = node.form.props.get(name)
                    if prop is None:  # pragma: no cover
                        logger.warning(f'applyNodeEdits got EDIT_PROP_SET for bad prop {name} on form {node.form}')
                        continue

                    node.props[name] = valu
                    node.bylayer['props'][name] = wlyr.iden

                    callbacks.append((prop.wasSet, (node, oldv), {}))
                    callbacks.append((self.view.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_DEL:

                    (name, oldv, stype) = parms

                    prop = node.form.props.get(name)
                    if prop is None:  # pragma: no cover
                        logger.warning(f'applyNodeEdits got EDIT_PROP_DEL for bad prop {name} on form {node.form}')
                        continue

                    node.props.pop(name, None)
                    node.bylayer['props'].pop(name, None)

                    callbacks.append((prop.wasDel, (node, oldv), {}))
                    callbacks.append((self.view.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_TAG_SET:

                    (tag, valu, oldv) = parms

                    node.tags[tag] = valu
                    node.bylayer['tags'][tag] = wlyr.iden

                    callbacks.append((self.view.runTagAdd, (node, tag, valu), {}))
                    callbacks.append((self.wlyr.fire, ('tag:add', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_DEL:

                    (tag, oldv) = parms

                    node.tags.pop(tag, None)
                    node.bylayer['tags'].pop(tag, None)

                    callbacks.append((self.view.runTagDel, (node, tag, oldv), {}))
                    callbacks.append((self.wlyr.fire, ('tag:del', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAGPROP_SET:
                    (tag, prop, valu, oldv, stype) = parms
                    if tag not in node.tagprops:
                        node.tagprops[tag] = {}
                        node.bylayer['tagprops'][tag] = {}
                    node.tagprops[tag][prop] = valu
                    node.bylayer['tagprops'][tag][prop] = wlyr.iden
                    continue

                if etyp == s_layer.EDIT_TAGPROP_DEL:
                    (tag, prop, oldv, stype) = parms
                    if tag in node.tagprops:
                        node.tagprops[tag].pop(prop, None)
                        node.bylayer['tagprops'][tag].pop(prop, None)
                        if not node.tagprops[tag]:
                            node.tagprops.pop(tag, None)
                            node.bylayer['tagprops'].pop(tag, None)
                    continue

                if etyp == s_layer.EDIT_NODEDATA_SET:
                    name, data, oldv = parms
                    node.nodedata[name] = data
                    continue

                if etyp == s_layer.EDIT_NODEDATA_DEL:
                    name, oldv = parms
                    node.nodedata.pop(name, None)
                    continue

                if etyp == s_layer.EDIT_EDGE_ADD:
                    verb, n2iden = parms
                    n2 = await self.getNodeByBuid(s_common.uhex(n2iden))
                    callbacks.append((self.view.runEdgeAdd, (node, verb, n2), {}))

                if etyp == s_layer.EDIT_EDGE_DEL:
                    verb, n2iden = parms
                    n2 = await self.getNodeByBuid(s_common.uhex(n2iden))
                    callbacks.append((self.view.runEdgeDel, (node, verb, n2), {}))

        [await func(*args, **kwargs) for (func, args, kwargs) in callbacks]

        if actualedits:
            await self.fire('node:edits', edits=actualedits)

        return saveoff, changes, nodes

    async def addNode(self, name, valu, props=None, norminfo=None):
        '''
        Add a node by form name and value with optional props.

        Args:
            name (str): The form of node to add.
            valu (obj): The value for the node.
            props (dict): Optional secondary properties for the node.

        Notes:
            If a props dictionary is provided, it may be mutated during node construction.

        Returns:
            s_node.Node: A Node object. It may return None if the snap is unable to add or lift the node.
        '''
        if self.readonly:
            mesg = 'The snapshot is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        if isinstance(valu, dict):
            form = self.core.model.reqForm(name)
            if isinstance(form.type, s_types.Guid):
                return await self._addGuidNodeByDict(form, valu, props=props)

        async with self.getEditor() as editor:
            protonode = await editor.addNode(name, valu, props=props, norminfo=norminfo)
            if protonode is None:
                return None

        # the newly constructed node is cached
        return await self.getNodeByBuid(protonode.buid)

    async def _addGuidNodeByDict(self, form, vals, props=None):

        if props is None:
            props = {}

        trycast = vals.pop('$try', False)
        addprops = vals.pop('$props', None)

        if not vals:
            mesg = f'No values provided for form {form.full}'
            raise s_exc.BadTypeValu(mesg=mesg)

        for name, valu in list(props.items()):
            try:
                props[name] = form.reqProp(name).type.norm(valu)
            except s_exc.BadTypeValu as e:
                mesg = e.get('mesg')
                e.update({
                    'prop': name,
                    'form': form.name,
                    'mesg': f'Bad value for prop {form.name}:{name}: {mesg}',
                })
                raise e

        if addprops is not None:
            for name, valu in addprops.items():
                try:
                    props[name] = form.reqProp(name).type.norm(valu)
                except s_exc.BadTypeValu as e:
                    mesg = e.get("mesg")
                    if not trycast:
                        e.update({
                            'prop': name,
                            'form': form.name,
                            'mesg': f'Bad value for prop {form.name}:{name}: {mesg}'
                        })
                        raise e
                    await self.warn(f'Skipping bad value for prop {form.name}:{name}: {mesg}')

        norms, proplist = self._normGuidNodeDict(form, vals)

        iden = s_common.guid(proplist)
        node = await self._getGuidNodeByNorms(form, iden, norms)

        async with self.getEditor() as editor:

            if node is not None:
                proto = editor.loadNode(node)
            else:
                proto = await editor.addNode(form.name, iden)
                for name, (prop, valu, info) in norms.items():
                    await proto.set(name, valu, norminfo=info)

            # ensure the non-deconf props are set
            for name, (valu, info) in props.items():
                await proto.set(name, valu, norminfo=info)

        return await self.getNodeByBuid(proto.buid)

    def _normGuidNodeDict(self, form, props):

        norms = {}
        proplist = []

        for name, valu in props.items():

            try:
                prop = form.reqProp(name)
                norm, norminfo = prop.type.norm(valu)

                norms[name] = (prop, norm, norminfo)
                proplist.append((name, norm))
            except s_exc.BadTypeValu as e:
                mesg = e.get('mesg')
                e.update({
                    'prop': name,
                    'form': form.name,
                    'mesg': f'Bad value for prop {form.name}:{name}: {mesg}',
                })
                raise e

        proplist.sort()

        return norms, proplist

    async def _getGuidNodeByDict(self, form, props):
        norms, proplist = self._normGuidNodeDict(form, props)
        return await self._getGuidNodeByNorms(form, s_common.guid(proplist), norms)

    async def _getGuidNodeByNorms(self, form, iden, norms):

        # check first for an exact match via our same deconf strategy

        node = await self.getNodeByNdef((form.full, iden))
        if node is not None:

            # ensure we still match the property deconf criteria
            for (prop, norm, info) in norms.values():
                if not self._filtByPropAlts(node, prop, norm):
                    break
            else:
                return node

        # TODO there is an opportunity here to populate
        # a look-aside for the alternative iden to speed
        # up future deconfliction and potentially pop them
        # if we lookup a node and it no longer passes the
        # filter...

        counts = []

        # no exact match. lets do some counting.
        for (prop, norm, info) in norms.values():
            count = await self._getPropAltCount(prop, norm)
            counts.append((count, prop, norm))

        counts.sort(key=lambda x: x[0])

        # lift starting with the lowest count
        count, prop, norm = counts[0]
        async for node in self._nodesByPropAlts(prop, norm):
            await asyncio.sleep(0)

            # filter on the remaining props/alts
            for count, prop, norm in counts[1:]:
                if not self._filtByPropAlts(node, prop, norm):
                    break
            else:
                return node

        return None

    async def _getPropAltCount(self, prop, valu):
        count = 0
        proptype = prop.type
        for prop in prop.getAlts():
            if prop.type.isarray and prop.type.arraytype == proptype:
                count += await self.view.getPropArrayCount(prop.full, valu=valu)
            else:
                count += await self.view.getPropCount(prop.full, valu=valu)
        return count

    def _filtByPropAlts(self, node, prop, valu):
        # valu must be normalized in advance
        proptype = prop.type
        for prop in prop.getAlts():
            if prop.type.isarray and prop.type.arraytype == proptype:
                arryvalu = node.get(prop.name)
                if arryvalu is not None and valu in arryvalu:
                    return True
            else:
                if node.get(prop.name) == valu:
                    return True

        return False

    async def _nodesByPropAlts(self, prop, valu):
        # valu must be normalized in advance
        proptype = prop.type
        for prop in prop.getAlts():
            if prop.type.isarray and prop.type.arraytype == proptype:
                async for node in self.nodesByPropArray(prop.full, '=', valu, norm=False):
                    yield node
            else:
                async for node in self.nodesByPropValu(prop.full, '=', valu, norm=False):
                    yield node

    async def addFeedNodes(self, name, items):
        '''
        Call a feed function and return what it returns (typically yields Node()s).

        Args:
            name (str): The name of the feed record type.
            items (list): A list of records of the given feed type.

        Returns:
            (object): The return value from the feed function. Typically Node() generator.

        '''
        func = self.core.getFeedFunc(name)
        if func is None:
            raise s_exc.NoSuchName(name=name)

        logger.info(f'User ({self.user.name}) adding feed data ({name}): {len(items)}')

        genr = func(self, items)
        if not isinstance(genr, types.AsyncGeneratorType):
            if isinstance(genr, types.CoroutineType):
                genr.close()
            mesg = f'feed func returned a {type(genr)}, not an async generator.'
            raise s_exc.BadCtorType(mesg=mesg, name=name)

        async for node in genr:
            yield node

    async def addFeedData(self, name, items):

        func = self.core.getFeedFunc(name)
        if func is None:
            raise s_exc.NoSuchName(name=name)

        logger.info(f'User ({self.user.name}) adding feed data ({name}): {len(items)}')

        await func(self, items)

    async def getTagNorm(self, tagname):
        return await self.tagnorms.aget(tagname)

    async def _getTagNorm(self, tagname):
        try:
            return self.core.model.type('syn:tag').norm(tagname)
        except s_exc.BadTypeValu as e:
            if self.strict: raise e
            await self.warn(f'Invalid tag name {tagname}: {e}')

    async def getTagNode(self, name):
        '''
        Retrieve a cached tag node. Requires name is normed. Does not add.
        '''
        return await self.tagcache.aget(name)

    async def _getTagNode(self, tagnorm):

        tagnode = await self.getNodeByBuid(s_common.buid(('syn:tag', tagnorm)))
        if tagnode is not None:
            isnow = tagnode.get('isnow')
            while isnow is not None:
                tagnode = await self.getNodeByBuid(s_common.buid(('syn:tag', isnow)))
                isnow = tagnode.get('isnow')

        if tagnode is None:
            return s_common.novalu

        return tagnode

    async def _raiseOnStrict(self, ctor, mesg, **info):
        if self.strict:
            raise ctor(mesg=mesg, **info)
        await self.warn(mesg)
        return None

    async def addNodes(self, nodedefs):
        '''
        Add/merge nodes in bulk.

        The addNodes API is designed for bulk adds which will
        also set properties, add tags, add edges, and set nodedata to existing nodes.
        Nodes are specified as a list of the following tuples:

            ( (form, valu), {'props':{}, 'tags':{}})

        Args:
            nodedefs (list): A list of nodedef tuples.

        Returns:
            (list): A list of xact messages.
        '''
        if self.readonly:
            mesg = 'The snapshot is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        oldstrict = self.strict
        self.strict = False
        try:
            for nodedefn in nodedefs:
                try:
                    node = await self._addNodeDef(nodedefn)
                    if node is not None:
                        yield node

                    await asyncio.sleep(0)

                except asyncio.CancelledError:
                    raise

                except Exception as e:
                    if oldstrict:
                        raise
                    await self.warn(f'addNodes failed on {nodedefn}: {e}')
                    await asyncio.sleep(0)
        finally:
            self.strict = oldstrict

    async def _addNodeDef(self, nodedefn):

        n2buids = set()

        (formname, formvalu), forminfo = nodedefn

        props = forminfo.get('props')

        # remove any universal created props...
        if props is not None:
            props.pop('.created', None)

        async with self.getEditor() as editor:

            protonode = await editor.addNode(formname, formvalu, props=props)
            if protonode is None:
                return

            tags = forminfo.get('tags')
            if tags is not None:
                for tagname, tagvalu in tags.items():
                    await protonode.addTag(tagname, tagvalu)

            nodedata = forminfo.get('nodedata')
            if isinstance(nodedata, dict):
                for dataname, datavalu in nodedata.items():
                    if not isinstance(dataname, str):
                        continue
                    await protonode.setData(dataname, datavalu)

            tagprops = forminfo.get('tagprops')
            if tagprops is not None:
                for tag, props in tagprops.items():
                    for name, valu in props.items():
                        await protonode.setTagProp(tag, name, valu)

            for verb, n2iden in forminfo.get('edges', ()):

                if isinstance(n2iden, (tuple, list)):
                    n2proto = await editor.addNode(*n2iden)
                    if n2proto is None:
                        continue

                    n2iden = n2proto.iden()

                await protonode.addEdge(verb, n2iden)

        return await self.getNodeByBuid(protonode.buid)

    async def getRuntNodes(self, full, valu=None, cmpr=None):

        todo = s_common.todo('runRuntLift', full, valu, cmpr, self.view.iden)
        async for sode in self.core.dyniter('cortex', todo):
            await asyncio.sleep(0)

            node = s_node.Node(self, sode)
            node.isrunt = True

            yield node

    async def iterNodeEdgesN1(self, buid, verb=None):

        last = None
        gens = [layr.iterNodeEdgesN1(buid, verb=verb) for layr in self.layers]

        async for edge in s_common.merggenr2(gens):

            if edge == last: # pragma: no cover
                await asyncio.sleep(0)
                continue

            last = edge
            yield edge

    async def iterNodeEdgesN2(self, buid, verb=None):

        last = None
        gens = [layr.iterNodeEdgesN2(buid, verb=verb) for layr in self.layers]

        async for edge in s_common.merggenr2(gens):

            if edge == last: # pragma: no cover
                await asyncio.sleep(0)
                continue

            last = edge
            yield edge

    async def hasNodeEdge(self, buid1, verb, buid2):
        for layr in self.layers:
            if await layr.hasNodeEdge(buid1, verb, buid2):
                return True
        return False

    async def iterEdgeVerbs(self, n1buid, n2buid):

        last = None
        gens = [layr.iterEdgeVerbs(n1buid, n2buid) for layr in self.layers]

        async for verb in s_common.merggenr2(gens):

            if verb == last: # pragma: no cover
                await asyncio.sleep(0)
                continue

            last = verb
            yield verb

    async def _getLayrNdefProp(self, layr, buid):
        async for refsbuid, refsabrv in layr.getNdefRefs(buid):
            yield refsbuid, layr.getAbrvProp(refsabrv)

    async def getNdefRefs(self, buid, props=False):
        last = None
        if props:
            gens = [self._getLayrNdefProp(layr, buid) for layr in self.layers]
        else:
            gens = [layr.getNdefRefs(buid) for layr in self.layers]

        async for refsbuid, xtra in s_common.merggenr2(gens):
            if refsbuid == last:
                continue

            await asyncio.sleep(0)
            last = refsbuid

            if props:
                yield refsbuid, xtra[1]
            else:
                yield refsbuid

    async def hasNodeData(self, buid, name):
        '''
        Return True if the buid has nodedata set on it under the given name
        False otherwise
        '''
        for layr in reversed(self.layers):
            if await layr.hasNodeData(buid, name):
                return True
        return False

    async def getNodeData(self, buid, name, defv=None):
        '''
        Get nodedata from closest to write layer, no merging involved
        '''
        for layr in reversed(self.layers):
            ok, valu = await layr.getNodeData(buid, name)
            if ok:
                return valu
        return defv

    async def iterNodeData(self, buid):
        '''
        Returns:  Iterable[Tuple[str, Any]]
        '''
        async with self.core.getSpooledSet() as sset:

            for layr in reversed(self.layers):

                async for name, valu in layr.iterNodeData(buid):
                    if name in sset:
                        continue

                    await sset.add(name)
                    yield name, valu

    async def iterNodeDataKeys(self, buid):
        '''
        Yield each data key from the given node by buid.
        '''
        async with self.core.getSpooledSet() as sset:

            for layr in reversed(self.layers):

                async for name in layr.iterNodeDataKeys(buid):
                    if name in sset:
                        continue

                    await sset.add(name)
                    yield name
