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
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.storm as s_storm
import synapse.lib.types as s_types
import synapse.lib.spooled as s_spooled

logger = logging.getLogger(__name__)

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
            return True

        return False

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
            return True

        return False

    async def getData(self, name):

        curv = self.nodedata.get(name, s_common.novalu)
        if curv is not s_common.novalu:
            return curv

        if self.node is not None:
            return await self.node.getData(name, defv=s_common.novalu)

        return s_common.novalu

    async def setData(self, name, valu):

        if await self.getData(name) == valu:
            return

        try:
            s_common.reqjsonsafe(valu)
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

    async def setTagProp(self, tag, name, valu):

        tagnode = await self.addTag(tag)
        if tagnode is None:
            return

        prop = self.ctx.snap.core.model.getTagProp(name)
        if prop is None:
            mesg = f'Tagprop {name} does not exist in this Cortex.'
            return await self.ctx.snap._raiseOnStrict(s_exc.NoSuchTagProp, mesg)

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

    async def set(self, name, valu, norminfo=None):

        prop = self.form.props.get(name)
        if prop is None:
            return False

        if prop.locked:
            mesg = f'Prop {prop.full} is locked due to deprecation.'
            await self.ctx.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg)
            return False

        if isinstance(prop.type, s_types.Array):
            arrayform = self.ctx.snap.core.model.form(prop.type.arraytype.name)
            if arrayform is not None and arrayform.locked:
                mesg = f'Prop {prop.full} is locked due to deprecation.'
                await self.ctx.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg)
                return False

        if norminfo is None:
            try:
                valu, norminfo = prop.type.norm(valu)
            except s_exc.BadTypeValu as e:
                oldm = e.errinfo.get('mesg')
                e.errinfo['prop'] = prop.name
                e.errinfo['form'] = prop.form.name
                e.errinfo['mesg'] = f'Bad prop value {prop.full}={valu!r} : {oldm}'
                if self.ctx.snap.strict:
                    raise e
                await self.ctx.snap.warn(e)
                return False

        if isinstance(prop.type, s_types.Ndef):
            ndefform = self.ctx.snap.core.model.form(valu[0])
            if ndefform.locked:
                mesg = f'Prop {prop.full} is locked due to deprecation.'
                await self.ctx.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg)
                return False

        curv = self.get(name)
        if curv == valu:
            return False

        if prop.info.get('ro') and curv is not None:
            mesg = f'Property is read only: {prop.full}.'
            await self.ctx.snap._raiseOnStrict(s_exc.ReadOnlyProp, mesg)
            return False

        if self.node is not None:
            await self.ctx.snap.core._callPropSetHook(self.node, prop, valu)

        self.props[name] = valu

        propform = self.ctx.snap.core.model.form(prop.type.name)
        if propform is not None:
            await self.ctx.addNode(propform.name, valu, norminfo=norminfo)

        # TODO can we mandate any subs are returned pre-normalized?
        propsubs = norminfo.get('subs')
        if propsubs is not None:
            for subname, subvalu in propsubs.items():
                full = f'{prop.name}:{subname}'
                if self.form.props.get(full) is not None:
                    await self.set(full, subvalu)

        propadds = norminfo.get('adds')
        if propadds is not None:
            for addname, addvalu, addinfo in propadds:
                await self.ctx.addNode(addname, addvalu, norminfo=addinfo)

        return True

class SnapEditor:
    '''
    A SnapEditor allows tracking node edits with subs/deps as a transaction.
    '''
    def __init__(self, snap):
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

    async def addNode(self, formname, valu, props=None, norminfo=None):

        self.snap.core._checkMaxNodes()

        form = self.snap.core.model.form(formname)
        if form is None:
            mesg = f'No form named {formname} for valu={valu}.'
            return await self.snap._raiseOnStrict(s_exc.NoSuchForm, mesg)

        if form.isrunt:
            mesg = f'Cannot make runt nodes: {formname}.'
            return await self.snap._raiseOnStrict(s_exc.IsRuntForm, mesg)

        if form.locked:
            mesg = f'Form {form.full} is locked due to deprecation for valu={valu}.'
            return await self.snap._raiseOnStrict(s_exc.IsDeprLocked, mesg)

        if norminfo is None:
            try:
                valu, norminfo = form.type.norm(valu)
            except s_exc.BadTypeValu as e:
                e.errinfo['form'] = form.name
                if self.snap.strict: raise e
                await self.snap.warn(f'addNode() BadTypeValu {formname}={valu} {e}')
                return None

        protonode = await self._initProtoNode(form, valu, norminfo)
        if props is not None:
            [await protonode.set(p, v) for (p, v) in props.items()]

        return protonode

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

        subs = norminfo.get('subs')
        if subs is not None:
            [await protonode.set(p, v) for (p, v) in subs.items()]

        adds = norminfo.get('adds')
        if adds is not None:
            for addname, addvalu, addinfo in adds:
                await self.addNode(addname, addvalu, norminfo=addinfo)

        return protonode

class Snap(s_base.Base):
    '''
    A "snapshot" is a transaction across multiple Cortex layers.

    The Snap object contains the bulk of the Cortex API to
    facilitate performance through careful use of transaction
    boundaries.
    '''
    tagcachesize = 1000
    nodecachesize = 100000

    async def __anit__(self, view, user):
        '''
        Args:
            core (cortex):  the cortex
            layers (List[Layer]): the list of layers to access, write layer last
        '''
        await s_base.Base.__anit__(self)

        self.stack = contextlib.ExitStack()

        assert user is not None

        self.strict = True

        self.core = view.core
        self.view = view
        self.user = user

        self.layers = list(reversed(view.layers))
        self.wlyr = self.layers[-1]

        self.readonly = self.wlyr.readonly

        self.tagnorms = s_cache.FixedCache(self._getTagNorm, size=self.tagcachesize)
        self.tagcache = s_cache.FixedCache(self._getTagNode, size=self.tagcachesize)

        # Keeps alive the most recently accessed node objects
        self.nodecache = collections.deque(maxlen=self.nodecachesize)
        self.livenodes = weakref.WeakValueDictionary()  # nid -> Node
        self._warnonce_keys = set()

        self.onfini(self.stack.close)

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

    async def iterStormPodes(self, text, opts, user=None):
        '''
        Yield packed node tuples for the given storm query text.
        '''
        if user is None:
            user = self.user

        dorepr = False
        dopath = False

        self.core._logStormQuery(text, user, info={'mode': opts.get('mode', 'storm'), 'view': self.view.iden})

        # { form: ( embedprop, ... ) }
        embeds = opts.get('embeds')

        if opts is not None:
            dorepr = opts.get('repr', False)
            dopath = opts.get('path', False)

        async for node, path in self.storm(text, opts=opts, user=user):

            pode = node.pack(dorepr=dorepr)
            pode[1]['path'] = await path.pack(path=dopath)

            if embeds is not None:
                embdef = embeds.get(node.form.name)
                if embdef is not None:
                    pode[1]['embeds'] = await node.getEmbeds(embdef)

            yield pode

    @s_coro.genrhelp
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

    @s_coro.genrhelp
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
        self.nodecache.clear()
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

    async def getNodeByBuid(self, buid):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            Optional[s_node.Node]: The node object or None.

        '''
        nid = self.core.getNidByBuid(buid)
        if nid is None:
            return None

        return await self._joinStorNode(nid)

    async def getNodeByNid(self, nid):
        return await self._joinStorNode(nid)

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

    async def nodesByTagProp(self, form, tag, name):
        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        async for nid, srefs in self.view.liftByTagProp(form, tag, name):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTagPropValu(self, form, tag, name, cmpr, valu):

        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        cmprvals = prop.type.getStorCmprs(cmpr, valu)
        # an empty return probably means ?= with invalid value
        if not cmprvals:
            return

        async for nid, srefs in self.view.liftByTagPropValu(form, tag, name, cmprvals):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def _joinStorNode(self, nid):

        node = self.livenodes.get(nid)
        if node is not None:
            await asyncio.sleep(0)
            return node

        # must do this in view layer order not our reversed order
        soderefs = [layr.genStorNodeRef(nid) for layr in self.view.layers]

        return await self._joinSodes(nid, soderefs)

    async def _joinSodes(self, nid, soderefs):

        node = self.livenodes.get(nid)
        if node is not None:
            await asyncio.sleep(0)
            return node

        ndef = None
        # make sure at least one layer has the primary property
        for envl in soderefs:
            valt = envl.sode.get('valu')
            if valt is not None:
                ndef = (envl.sode.get('form'), valt[0])
                break

        if ndef is None:
            await asyncio.sleep(0)
            return None

        node = s_node.Node(self, nid, ndef, soderefs)

        self.livenodes[nid] = node
        self.nodecache.append(node)

        await asyncio.sleep(0)
        return node

    async def nodesByDataName(self, name):
        async for (nid, sodes) in self.core._liftByDataName(name, self.layers):
            node = await self._joinSodes(nid, sodes)
            if node is not None:
                yield node

    async def nodesByProp(self, full):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if prop.isrunt:
            async for node in self.getRuntNodes(prop):
                yield node
            return

        if prop.isform:
            genr = self.view.liftByProp(prop.name, None)

        elif prop.isuniv:
            genr = self.view.liftByProp(None, prop.name)

        else:
            genr = self.view.liftByProp(prop.form.name, prop.name)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByPropValu(self, full, cmpr, valu):

        if cmpr == 'type=':
            async for node in self.nodesByPropValu(full, '=', valu):
                yield node

            async for node in self.nodesByPropTypeValu(full, valu):
                yield node
            return

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        cmprvals = prop.type.getStorCmprs(cmpr, valu)
        # an empty return probably means ?= with invalid value
        if not cmprvals:
            return

        if prop.isrunt:
            for storcmpr, storvalu, _ in cmprvals:
                async for node in self.getRuntNodes(prop, cmprvalu=(storcmpr, storvalu)):
                    yield node
            return

        if prop.isform:
            genr = self.view.liftByFormValu(prop.name, cmprvals)

        elif prop.isuniv:
            genr = self.view.liftByPropValu(None, prop.name, cmprvals)

        else:
            genr = self.view.liftByPropValu(prop.form.name, prop.name, cmprvals)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTag(self, tag, form=None):
        async for nid, srefs in self.view.liftByTag(tag, form=form):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTagValu(self, tag, cmpr, valu, form=None):

        norm, info = self.core.model.type('ival').norm(valu)
        async for nid, srefs in self.view.liftByTagValu(tag, cmpr, norm, form):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByPropTypeValu(self, name, valu):

        _type = self.core.model.types.get(name)
        if _type is None:
            raise s_exc.NoSuchType(name=name)

        for prop in self.core.model.getPropsByType(name):
            async for node in self.nodesByPropValu(prop.full, '=', valu):
                yield node

        for prop in self.core.model.getArrayPropsByType(name):
            async for node in self.nodesByPropArray(prop.full, '=', valu):
                yield node

    async def nodesByPropArray(self, full, cmpr, valu):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if not isinstance(prop.type, s_types.Array):
            mesg = f'Array synax is invalid on non array type: {prop.type.name}.'
            raise s_exc.BadTypeValu(mesg=mesg)

        cmprvals = prop.type.arraytype.getStorCmprs(cmpr, valu)

        if prop.isform:
            genr = self.view.liftByPropArray(prop.name, None, cmprvals)

        else:
            formname = None
            if prop.form is not None:
                formname = prop.form.name

            genr = self.view.liftByPropArray(formname, prop.name, cmprvals)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
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
            await self.saveNodeEdits(nodeedits)

    @contextlib.asynccontextmanager
    async def getEditor(self):

        editor = SnapEditor(self)

        yield editor

        nodeedits = editor.getNodeEdits()
        if nodeedits:
            await self.saveNodeEdits(nodeedits)

    async def saveNodeEdits(self, edits, meta=None):
        '''
        Save node edits and run triggers/callbacks.
        '''

        if self.readonly:
            mesg = 'The snapshot is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        if meta is None:
            meta = await self.getSnapMeta()

        wlyr = self.wlyr
        callbacks = []

        # hold a reference to  all the nodes about to be edited...
        nodes = {e[0]: await self.getNodeByBuid(e[0]) for e in edits}

        saveoff, nodeedits = await wlyr.saveNodeEdits(edits, meta)

        # make a pass through the returned edits, apply the changes to our Nodes()
        # and collect up all the callbacks to fire at once at the end.  It is
        # critical to fire all callbacks after applying all Node() changes.

        for buid, form, edits in nodeedits:

            node = nodes.get(buid)
            if node is None:
                node = await self.getNodeByBuid(buid)

            if node is None:
                continue

            for edit in edits:

                etyp, parms, _ = edit

                if etyp == s_layer.EDIT_NODE_ADD:
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
                        logger.warning(f'saveNodeEdits got EDIT_PROP_SET for bad prop {name} on form {node.form.full}')
                        continue

                    callbacks.append((prop.wasSet, (node, oldv), {}))
                    callbacks.append((self.view.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_DEL:

                    (name, oldv, stype) = parms

                    prop = node.form.props.get(name)
                    if prop is None:  # pragma: no cover
                        logger.warning(f'saveNodeEdits got EDIT_PROP_DEL for bad prop {name} on form {node.form.full}')
                        continue

                    callbacks.append((prop.wasDel, (node, oldv), {}))
                    callbacks.append((self.view.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_TAG_SET:

                    (tag, valu, oldv) = parms

                    callbacks.append((self.view.runTagAdd, (node, tag, valu), {}))
                    callbacks.append((self.wlyr.fire, ('tag:add', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_DEL:

                    (tag, oldv) = parms

                    callbacks.append((self.view.runTagDel, (node, tag, oldv), {}))
                    callbacks.append((self.wlyr.fire, ('tag:del', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAGPROP_SET:
                    continue

                if etyp == s_layer.EDIT_TAGPROP_DEL:
                    continue

                if etyp == s_layer.EDIT_NODEDATA_SET:
                    name, data, oldv = parms
                    node.nodedata[name] = data
                    continue

                if etyp == s_layer.EDIT_NODEDATA_DEL:
                    name, oldv = parms
                    node.nodedata.pop(name, None)
                    continue

        [await func(*args, **kwargs) for (func, args, kwargs) in callbacks]

        if nodeedits:
            await self.fire('node:edits', edits=nodeedits)

        return saveoff, nodeedits

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

        async with self.getEditor() as editor:
            protonode = await editor.addNode(name, valu, props=props, norminfo=norminfo)
            if protonode is None:
                return None

        # the newly constructed node is cached
        return await self.getNodeByBuid(protonode.buid)

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

        if not self.core.isTagValid(tagname):
            mesg = f'The tag ({tagname}) does not meet the regex for the tree.'
            await self._raiseOnStrict(s_exc.BadTag, mesg)
            return None

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

    async def getRuntNodes(self, prop, cmprvalu=None):

        now = s_common.now()

        filt = None
        if cmprvalu is not None:

            cmpr, valu = cmprvalu

            ctor = prop.type.getCmprCtor(cmpr)
            if ctor is None:
                mesg = f'Bad comparison ({cmpr}) for type {prop.type.name}.'
                raise s_exc.BadCmprType(mesg=mesg, cmpr=cmpr)

            filt = ctor(valu)
            if filt is None:
                mesg = f'Bad value ({valu}) for comparison {cmpr} {prop.type.name}.'
                raise s_exc.BadCmprValu(mesg=mesg, cmpr=cmpr)

        async for pode in self.view.getRuntPodes(prop, cmprvalu=cmprvalu):

            # for runt nodes without a .created time
            pode[1]['props'].setdefault('.created', now)

            # filter based on any specified prop / cmpr / valu
            if filt is None:
                if not prop.isform:
                    pval = pode[1]['props'].get(prop.name, s_common.novalu)
                    if pval == s_common.novalu:
                        await asyncio.sleep(0)
                        continue
            else:

                if prop.isform:
                    nval = pode[0][1]
                else:
                    nval = pode[1]['props'].get(prop.name, s_common.novalu)

                if nval is s_common.novalu or not filt(nval):
                    await asyncio.sleep(0)
                    continue

            yield s_node.RuntNode(self, pode)

    async def iterNodeEdgesN1(self, nid, verb=None):

        last = None
        gens = [layr.iterNodeEdgesN1(nid, verb=verb) for layr in self.layers]

        async for edge in s_common.merggenr2(gens):

            if edge == last: # pragma: no cover
                await asyncio.sleep(0)
                continue

            last = edge
            yield edge

    async def iterNodeEdgesN2(self, nid, verb=None):

        last = None
        gens = [layr.iterNodeEdgesN2(nid, verb=verb) for layr in self.layers]

        async for edge in s_common.merggenr2(gens):

            if edge == last: # pragma: no cover
                await asyncio.sleep(0)
                continue

            last = edge
            yield edge

    async def hasNodeEdge(self, n1nid, verb, n2nid):
        for layr in self.layers:
            if await layr.hasNodeEdge(n1nid, verb, n2nid):
                return True
        return False

    async def iterNodeEdgesN1N2(self, n1nid, n2nid):

        last = None
        gens = [layr.iterNodeEdgesN1N2(n1nid, n2nid) for layr in self.layers]

        async for edge in s_common.merggenr2(gens):

            if edge == last: # pragma: no cover
                await asyncio.sleep(0)
                continue

            last = edge
            yield edge

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

    async def iterNodeData(self, nid):
        '''
        Returns:  Iterable[Tuple[str, Any]]
        '''
        async with self.core.getSpooledSet() as sset:

            for layr in reversed(self.layers):

                async for name, valu in layr.iterNodeData(nid):
                    if name in sset:
                        continue

                    await sset.add(name)
                    yield name, valu

    async def iterNodeDataKeys(self, nid):
        '''
        Yield each data key from the given node by nid.
        '''
        async with self.core.getSpooledSet() as sset:

            for layr in reversed(self.layers):

                async for name in layr.iterNodeDataKeys(nid):
                    if name in sset:
                        continue

                    await sset.add(name)
                    yield name
