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
import synapse.lib.chop as s_chop
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.storm as s_storm
import synapse.lib.types as s_types

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
        self.ndef = (form, valu)

        self.tags = {}
        self.props = {}
        self.edges = set()
        self.tagprops = {}
        self.nodedata = {}

        self.delnode = False
        self.tombnode = False
        self.tagdels = set()
        self.tagtombs = set()
        self.propdels = set()
        self.proptombs = set()
        self.tagpropdels = set()
        self.tagproptombs = set()
        self.edgedels = set()
        self.edgetombs = set()
        self.edgetombdels = set()
        self.nodedatadels = set()
        self.nodedatatombs = set()
        self.nodedatatombdels = set()

        if self.node is not None:
            self.nid = self.node.nid
        else:
            self.nid = None

        self.multilayer = len(self.ctx.snap.layers) > 1

        if node is not None:
            self.nid = node.nid
        else:
            self.nid = self.ctx.snap.core.getNidByBuid(buid)

    def iden(self):
        return s_common.ehex(self.buid)

    def istomb(self):
        if self.tombnode:
            return True

        if self.node is not None:
            return self.node.istomb()

        return False

    def getNodeDelEdits(self):

        edits = []
        sode = self.node.sodes[0]

        if self.delnode:
            edits.append((s_layer.EDIT_NODE_DEL, (self.valu, self.form.type.stortype)))
            if (tags := sode.get('tags')) is not None:
                for name in sorted(tags.keys(), key=lambda t: len(t), reverse=True):
                    edits.append((s_layer.EDIT_TAG_DEL, (name, None)))

            if (props := sode.get('props')) is not None:
                for name in props.keys():
                    prop = self.form.props.get(name)
                    edits.append((s_layer.EDIT_PROP_DEL, (name, None, prop.type.stortype)))

            if (tagprops := sode.get('tagprops')) is not None:
                for tag, props in tagprops.items():
                    for name in props.keys():
                        prop = self.ctx.snap.core.model.getTagProp(name)
                        edits.append((s_layer.EDIT_TAGPROP_DEL, (tag, name, None, prop.type.stortype)))

        if self.tombnode:
            edits.append((s_layer.EDIT_NODE_TOMB, ()))

            if (tags := sode.get('antitags')) is not None:
                for tag in sorted(tags.keys(), key=lambda t: len(t), reverse=True):
                    edits.append((s_layer.EDIT_TAG_TOMB_DEL, (tag,)))

            if (props := sode.get('antiprops')) is not None:
                for prop in props.keys():
                    edits.append((s_layer.EDIT_PROP_TOMB_DEL, (prop,)))

            if (tagprops := sode.get('antitagprops')) is not None:
                for tag, props in tagprops.items():
                    for name in props.keys():
                        edits.append((s_layer.EDIT_TAGPROP_TOMB_DEL, (tag, name)))

        return (self.nid, self.form.name, edits)

    def getNodeEdit(self):

        if self.delnode or self.tombnode:
            return self.getNodeDelEdits()

        edits = []

        if not self.node:
            edits.append((s_layer.EDIT_NODE_ADD, (self.valu, self.form.type.stortype)))

        for name, valu in self.props.items():
            prop = self.form.props.get(name)
            edits.append((s_layer.EDIT_PROP_SET, (name, valu, None, prop.type.stortype)))

        for name in self.propdels:
            prop = self.form.props.get(name)
            edits.append((s_layer.EDIT_PROP_DEL, (name, None, prop.type.stortype)))

        for name in self.proptombs:
            edits.append((s_layer.EDIT_PROP_TOMB, (name,)))

        for name, valu in self.tags.items():
            edits.append((s_layer.EDIT_TAG_SET, (name, valu, None)))

        for name in sorted(self.tagdels, key=lambda t: len(t), reverse=True):
            edits.append((s_layer.EDIT_TAG_DEL, (name, None)))

        for name in self.tagtombs:
            edits.append((s_layer.EDIT_TAG_TOMB, (name,)))

        for verb, n2iden in self.edges:
            edits.append((s_layer.EDIT_EDGE_ADD, (verb, n2iden)))

        for verb, n2iden in self.edgedels:
            edits.append((s_layer.EDIT_EDGE_DEL, (verb, n2iden)))

        for verb, n2iden in self.edgetombs:
            edits.append((s_layer.EDIT_EDGE_TOMB, (verb, n2iden)))

        for verb, n2iden in self.edgetombdels:
            edits.append((s_layer.EDIT_EDGE_TOMB_DEL, (verb, n2iden)))

        for (tag, name), valu in self.tagprops.items():
            prop = self.ctx.snap.core.model.getTagProp(name)
            edits.append((s_layer.EDIT_TAGPROP_SET, (tag, name, valu, None, prop.type.stortype)))

        for (tag, name) in self.tagpropdels:
            prop = self.ctx.snap.core.model.getTagProp(name)
            edits.append((s_layer.EDIT_TAGPROP_DEL, (tag, name, None, prop.type.stortype)))

        for (tag, name) in self.tagproptombs:
            edits.append((s_layer.EDIT_TAGPROP_TOMB, (tag, name)))

        for name, valu in self.nodedata.items():
            edits.append((s_layer.EDIT_NODEDATA_SET, (name, valu, None)))

        for name in self.nodedatadels:
            edits.append((s_layer.EDIT_NODEDATA_DEL, (name, None)))

        for name in self.nodedatatombs:
            edits.append((s_layer.EDIT_NODEDATA_TOMB, (name,)))

        if not edits:
            return None

        return (self.nid, self.form.name, edits)

    async def addEdge(self, verb, n2nid):

        if not isinstance(verb, str):
            mesg = f'addEdge() got an invalid type for verb: {verb}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if not isinstance(n2nid, bytes):
            mesg = f'addEdge() got an invalid type for n2nid: {n2nid}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if len(n2nid) != 8:
            mesg = f'addEdge() got an invalid node id: {n2nid}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        tupl = (verb, n2nid)
        if tupl in self.edges:
            return False

        if self.nid is None:
            self.edges.add(tupl)
            return True

        if tupl in self.edgedels:
            self.edgedels.remove(tupl)
            return True

        if not self.multilayer:
            if not await self.ctx.snap.hasNodeEdge(self.nid, verb, n2nid):
                self.edges.add(tupl)
                return True

        if tupl in self.edgetombs:
            self.edgetombs.remove(tupl)
            return True

        toplayr = await self.ctx.snap.layers[0].hasNodeEdge(self.nid, verb, n2nid)
        if toplayr is True:
            return False

        for layr in self.ctx.snap.layers[1:self.node.lastlayr()]:
            if (undr := await layr.hasNodeEdge(self.nid, verb, n2nid)) is not None:
                if undr and toplayr is False:
                    self.edgetombdels.add(tupl)
                    return True
                break

        self.edges.add(tupl)
        return True

    async def delEdge(self, verb, n2nid):

        if not isinstance(verb, str):
            mesg = f'delEdge() got an invalid type for verb: {verb}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if not isinstance(n2nid, bytes):
            mesg = f'delEdge() got an invalid type for n2nid: {n2nid}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        if len(n2nid) != 8:
            mesg = f'delEdge() got an invalid node id: {n2nid}'
            await self.ctx.snap._raiseOnStrict(s_exc.BadArg, mesg)
            return False

        tupl = (verb, n2nid)
        if tupl in self.edgedels or tupl in self.edgetombs:
            return False

        if tupl in self.edges:
            self.edges.remove(tupl)
            return True

        if self.nid is None:
            return False

        if not self.multilayer:
            if await self.ctx.snap.hasNodeEdge(self.nid, verb, n2nid):
                self.edgedels.add(tupl)
                return True
            return False

        toplayr = await self.ctx.snap.layers[0].hasNodeEdge(self.nid, verb, n2nid)
        if toplayr is False:
            return False

        # has or none
        if toplayr is True:
            self.edgedels.add(tupl)

        for layr in self.ctx.snap.layers[1:self.node.lastlayr()]:
            if (undr := await layr.hasNodeEdge(self.nid, verb, n2nid)) is not None:
                if undr:
                    self.edgetombs.add(tupl)
                    return True
                break

        return toplayr is not None

    async def delEdgesN2(self, meta=None):
        '''
        Delete edge data from the SnapEditor's write layer where this is the dest node.
        '''
        dels = []
        nid = self.nid

        async for abrv, n1nid, tomb in self.ctx.snap.layers[0].iterNodeEdgesN2(self.nid):
            verb = self.ctx.snap.core.getAbrvVerb(abrv)
            n1ndef = self.ctx.snap.core.getNidNdef(n1nid)

            if tomb:
                edit = [((s_layer.EDIT_EDGE_TOMB_DEL), (verb, nid))]
            else:
                edit = [((s_layer.EDIT_EDGE_DEL), (verb, nid))]

            dels.append((n1nid, n1ndef[0], edit))

            if len(dels) >= 1000:
                await self.ctx.snap.saveNodeEdits(dels, meta=meta)
                dels.clear()

        if dels:
            await self.ctx.snap.saveNodeEdits(dels, meta=meta)

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

    async def popData(self, name):

        if not self.multilayer:
            valu = await self.ctx.snap.getNodeData(self.nid, name, defv=s_common.novalu)
            if valu is not s_common.novalu:
                self.nodedatadels.add(name)
                return valu
            return None

        (ok, valu, tomb) = await self.ctx.snap.layers[0].getNodeData(self.nid, name)
        if (ok and not tomb):
            self.nodedatadels.add(name)

        if tomb:
            return None

        valu = await self.ctx.snap.getNodeDataFromLayers(self.nid, name, strt=1, defv=s_common.novalu)
        if valu is not s_common.novalu:
            self.nodedatatombs.add(name)
            return valu
        return None

    async def _getRealTag(self, tag):

        normtupl = await self.ctx.snap.getTagNorm(tag)
        if normtupl is None:
            return None

        norm, info = normtupl

        tagnode = await self.ctx.snap.getTagNode(norm)
        if tagnode is not s_common.novalu:
            return self.ctx.loadNode(tagnode)

        return await self.ctx.addNode('syn:tag', norm, norminfo=info)

    def getTag(self, tag, defval=None):

        if tag in self.tagdels or tag in self.tagtombs:
            return defval

        curv = self.tags.get(tag)
        if curv is not None:
            return curv

        if self.node is not None:
            return self.node.getTag(tag, defval=defval)

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
        self.tagdels.discard(tagnode.valu)
        self.tagtombs.discard(tagnode.valu)

        return tagnode

    def getTagNames(self):
        alltags = set(self.tags.keys())
        alltags.update(set(self.node.getTagNames()))
        return alltags - self.tagdels - self.tagtombs

    def _getTagTree(self):

        root = (None, {})
        for tag in self.getTagNames():

            node = root

            for part in tag.split('.'):

                kidn = node[1].get(part)

                if kidn is None:

                    full = part
                    if node[0] is not None:
                        full = f'{node[0]}.{full}'

                    kidn = node[1][part] = (full, {})

                node = kidn

        return root

    def _delTag(self, name):

        self.tags.pop(name, None)

        if not self.multilayer:
            if self.node is not None and (tags := self.node.sodes[0].get('tags')) is not None and name in tags:
                self.tagdels.add(name)

            for prop in self.getTagProps(name):
                self.tagpropdels.add((name, prop))
                self.tagprops.pop((name, prop), None)
            return

        if self.node is not None:
            if (tags := self.node.sodes[0].get('tags')) is not None and name in tags:
                self.tagdels.add(name)

            if self.node.hasTagInLayers(name, strt=1):
                self.tagtombs.add(name)

            for (prop, layr) in self.getTagPropsWithLayer(name):
                if layr == 0:
                    self.tagpropdels.add((name, prop))

                if layr > 0 or (self.node is not None and self.node.hasTagPropInLayers(name, prop, strt=1)):
                    self.tagproptombs.add((name, prop))

        return True

    async def delTag(self, tag):

        path = s_chop.tagpath(tag)

        name = '.'.join(path)
        tree = None

        if len(path) > 1:

            parent = '.'.join(path[:-1])

            # retrieve a list of prunable tags
            prune = await self.ctx.snap.core.getTagPrune(parent)
            if prune:

                if tree is None:
                    tree = self._getTagTree()

                for prunetag in reversed(prune):

                    node = tree
                    for step in prunetag.split('.'):

                        node = node[1].get(step)
                        if node is None:
                            break

                    if node is not None and len(node[1]) == 1:
                        self._delTag(node[0])
                        continue

                    break

        pref = name + '.'

        for tname in self.getTagNames():
            if tname.startswith(pref):
                self._delTag(tname)

        if self.getTag(name) is not None:
            self._delTag(name)

        return True

    def getTagProps(self, tag):
        props = set()
        for (tagn, prop) in self.tagprops:
            if tagn == tag:
                props.add(prop)

        if self.node is not None:
            for prop in self.node.getTagProps(tag):
                if (tag, prop) not in self.tagpropdels and (tag, prop) not in self.tagproptombs:
                    props.add(prop)

        return(props)

    def getTagPropsWithLayer(self, tag):
        props = set()
        for (tagn, prop) in self.tagprops:
            if tagn == tag:
                props.add((prop, 0))

        if self.node is not None:
            for (prop, layr) in self.node.getTagPropsWithLayer(tag):
                if (tag, prop) not in self.tagpropdels and (tag, prop) not in self.tagproptombs:
                    props.add((prop, layr))

        return(props)

    def getTagProp(self, tag, name, defv=None):

        if (tag, name) in self.tagpropdels or (tag, name) in self.tagproptombs:
            return defv

        curv = self.tagprops.get((tag, name))
        if curv is not None:
            return curv

        if self.node is not None:
            return self.node.getTagProp(tag, name, defval=defv)

    def getTagPropWithLayer(self, tag, name, defv=None):

        if (tag, name) in self.tagpropdels or (tag, name) in self.tagproptombs:
            return defv, None

        curv = self.tagprops.get((tag, name))
        if curv is not None:
            return curv, 0

        if self.node is not None:
            return self.node.getTagPropWithLayer(tag, name, defval=defv)

    async def setTagProp(self, tag, name, valu):

        tagnode = await self.addTag(tag)
        if tagnode is None:
            return False

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
            return False

        curv = self.getTagProp(tagnode.valu, name)
        if curv == norm:
            return False

        self.tagprops[(tagnode.valu, name)] = norm
        self.tagpropdels.discard((tagnode.valu, name))
        self.tagproptombs.discard((tagnode.valu, name))

        return True

    async def delTagProp(self, tag, name):

        prop = self.ctx.snap.core.model.getTagProp(name)
        if prop is None:
            mesg = f'Tagprop {name} does not exist in this Cortex.'
            return await self.ctx.snap._raiseOnStrict(s_exc.NoSuchTagProp, mesg, name=name)

        (curv, layr) = self.getTagPropWithLayer(tag, name)
        if curv is None:
            return False

        self.tagprops.pop((tag, name), None)

        if layr == 0:
            self.tagpropdels.add((tag, name))

        if self.multilayer:
            if layr > 0 or (self.node is not None and self.node.hasTagPropInLayers(tag, name, strt=1)):
                self.tagproptombs.add((tag, name))

        return True

    def get(self, name, defv=None):

        # get the current value including the pending prop sets
        if name in self.propdels or name in self.proptombs:
            return defv

        curv = self.props.get(name, s_common.novalu)
        if curv is not s_common.novalu:
            return curv

        if self.node is not None:
            return self.node.get(name, defv=defv)

    def getWithLayer(self, name, defv=None):

        # get the current value including the pending prop sets
        if name in self.propdels or name in self.proptombs:
            return defv, None

        curv = self.props.get(name, s_common.novalu)
        if curv is not s_common.novalu:
            return curv, 0

        if self.node is not None:
            return self.node.getWithLayer(name, defv=defv)

    async def _set(self, prop, valu, norminfo=None):

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

        curv = self.get(prop.name)
        if curv == valu:
            return False

        if prop.info.get('ro') and curv is not None:
            mesg = f'Property is read only: {prop.full}.'
            await self.ctx.snap._raiseOnStrict(s_exc.ReadOnlyProp, mesg)
            return False

        if self.node is not None:
            await self.ctx.snap.core._callPropSetHook(self.node, prop, valu)

        self.props[prop.name] = valu
        self.propdels.discard(prop.name)
        self.proptombs.discard(prop.name)

        return valu, norminfo

    async def set(self, name, valu, norminfo=None):
        prop = self.form.props.get(name)
        if prop is None:
            return False

        retn = await self._set(prop, valu, norminfo=norminfo)
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
                if self.form.props.get(full) is not None:
                    await self.set(full, subvalu)

        propadds = norminfo.get('adds')
        if propadds is not None:
            for addname, addvalu, addinfo in propadds:
                await self.ctx.addNode(addname, addvalu, norminfo=addinfo)

        return True

    async def pop(self, name):

        prop = self.form.prop(name)
        if prop is None:
            mesg = f'No property named {name}.'
            await self.ctx.snap._raiseOnStrict(s_exc.NoSuchProp, mesg, name=name, form=self.form.name)
            return False

        (valu, layr) = self.getWithLayer(name, defv=s_common.novalu)
        if valu is s_common.novalu:
            return False

        if prop.info.get('ro'):
            mesg = f'Property is read only: {prop.full}.'
            await self.ctx.snap._raiseOnStrict(s_exc.ReadOnlyProp, mesg, name=prop.full)
            return False

        self.props.pop(name, None)

        if layr == 0:
            self.propdels.add(name)

        if self.multilayer:
            if layr > 0 or (self.node is not None and self.node.hasInLayers(name, strt=1)):
                self.proptombs.add(name)

        return True

    async def getSetOps(self, name, valu, norminfo=None):
        prop = self.form.props.get(name)
        if prop is None:
            return ()

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
                if self.form.props.get(full) is not None:
                    ops.append(self.getSetOps(full, subvalu))

        propadds = norminfo.get('adds')
        if propadds is not None:
            for addname, addvalu, addinfo in propadds:
                ops.append(self.ctx.getAddNodeOps(addname, addvalu, norminfo=addinfo))

        return ops

    async def delete(self):
        if self.node is None or self.istomb():
            return

        if self.node.sodes[0].get('valu') is not None:
            self.delnode = True

        for sode in self.node.sodes[1:]:
            if sode.get('valu') is not None:
                self.tombnode = True
                return
            elif sode.get('antivalu') is not None:
                return

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

    async def getNodeByNid(self, nid):
        node = await self.snap.getNodeByNid(nid)
        if node:
            return self.loadNode(node)

    def getNodeEdits(self):
        nodeedits = []
        for protonode in self.protonodes.values():
            nodeedit = protonode.getNodeEdit()
            if nodeedit is not None:
                nodeedits.append(nodeedit)
        return nodeedits

    async def _addNode(self, form, valu, props=None, norminfo=None):

        self.snap.core._checkMaxNodes()

        if form.isrunt:
            mesg = f'Cannot make runt nodes: {form.name}.'
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
                ops.append(protonode.getSetOps(prop, valu))

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
                ops.append(protonode.getSetOps(prop, valu))

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

        assert user is not None

        self.strict = True

        self.core = view.core
        self.view = view
        self.user = user

        self.layers = view.layers
        self.wlyr = self.layers[0]

        self.readonly = self.wlyr.readonly

        self.tagnorms = s_cache.FixedCache(self._getTagNorm, size=self.tagcachesize)
        self.tagcache = s_cache.FixedCache(self._getTagNode, size=self.tagcachesize)

        # Keeps alive the most recently accessed node objects
        self.nodecache = collections.deque(maxlen=self.nodecachesize)
        self.livenodes = weakref.WeakValueDictionary()  # nid -> Node
        self._warnonce_keys = set()

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

        show_storage = False

        self.core._logStormQuery(text, user, info={'mode': opts.get('mode', 'storm'), 'view': self.view.iden})

        # { form: ( embedprop, ... ) }
        embeds = opts.get('embeds')

        if opts is not None:
            dorepr = opts.get('repr', False)
            dopath = opts.get('path', False)
            show_storage = opts.get('show:storage', False)

        async for node, path in self.storm(text, opts=opts, user=user):

            pode = node.pack(dorepr=dorepr)
            pode[1]['path'] = await path.pack(path=dopath)

            if show_storage:
                pode[1]['storage'] = await node.getStorNodes()

            if embeds is not None:
                embdef = embeds.get(node.form.name)
                if embdef is not None:
                    pode[1]['embeds'] = await node.getEmbeds(embdef)

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
        self.nodecache.clear()
        self.livenodes.clear()

    def clearCachedNode(self, nid):
        self.livenodes.pop(nid, None)

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

    async def getNodeByBuid(self, buid, tombs=False):
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

        return await self._joinStorNode(nid, tombs=tombs)

    async def getNodeByNid(self, nid, tombs=False):
        return await self._joinStorNode(nid, tombs=tombs)

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

    async def nodesByTagProp(self, form, tag, name, reverse=False, subtype=None):
        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        indx = None
        if subtype is not None:
            indx = prop.type.getSubIndx(subtype)

        async for nid, srefs in self.view.liftByTagProp(form, tag, name, reverse=reverse, indx=indx):
            node = await self._joinSodes(nid, srefs)
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

        async for nid, srefs in self.view.liftByTagPropValu(form, tag, name, cmprvals, reverse=reverse):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def _joinStorNode(self, nid, tombs=False):

        node = self.livenodes.get(nid)
        if node is not None:
            await asyncio.sleep(0)

            if not tombs and node.istomb():
                return None
            return node

        soderefs = []
        for layr in self.layers:
            sref = layr.genStorNodeRef(nid)
            if tombs is False:
                if sref.sode.get('antivalu') is not None:
                    return None
                elif sref.sode.get('valu') is not None:
                    tombs = True

            soderefs.append(sref)

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
        async for nid, srefs in self.view.liftByDataName(name):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByProp(self, full, reverse=False, subtype=None):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if prop.isrunt:
            async for node in self.getRuntNodes(prop):
                yield node
            return

        indx = None
        if subtype is not None:
            indx = prop.type.getSubIndx(subtype)

        if prop.isform:
            genr = self.view.liftByProp(prop.name, None, reverse=reverse, indx=indx)

        elif prop.isuniv:
            genr = self.view.liftByProp(None, prop.name, reverse=reverse, indx=indx)

        else:
            genr = self.view.liftByProp(prop.form.name, prop.name, reverse=reverse, indx=indx)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByPropValu(self, full, cmpr, valu, reverse=False):

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
            genr = self.view.liftByFormValu(prop.name, cmprvals, reverse=reverse)

        elif prop.isuniv:
            genr = self.view.liftByPropValu(None, prop.name, cmprvals, reverse=reverse)

        else:
            genr = self.view.liftByPropValu(prop.form.name, prop.name, cmprvals, reverse=reverse)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTag(self, tag, form=None, reverse=False, subtype=None):

        indx = None
        if subtype is not None:
            indx = self.core.model.type('ival').getTagSubIndx(subtype)

        async for nid, srefs in self.view.liftByTag(tag, form=form, reverse=reverse, indx=indx):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTagValu(self, tag, cmpr, valu, form=None, reverse=False):

        cmprvals = self.core.model.type('ival').getStorCmprs(cmpr, valu)
        async for nid, srefs in self.view.liftByTagValu(tag, cmprvals, form, reverse=reverse):
            node = await self._joinSodes(nid, srefs)
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

    async def nodesByPropArray(self, full, cmpr, valu, reverse=False):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if not isinstance(prop.type, s_types.Array):
            mesg = f'Array syntax is invalid on non array type: {prop.type.name}.'
            raise s_exc.BadTypeValu(mesg=mesg)

        cmprvals = prop.type.arraytype.getStorCmprs(cmpr, valu)

        if prop.isform:
            genr = self.view.liftByPropArray(prop.name, None, cmprvals, reverse=reverse)

        else:
            formname = None
            if prop.form is not None:
                formname = prop.form.name

            genr = self.view.liftByPropArray(formname, prop.name, cmprvals, reverse=reverse)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    @contextlib.asynccontextmanager
    async def getNodeEditor(self, node, transaction=False):

        if node.form.isrunt:
            mesg = f'Cannot edit runt nodes: {node.form.name}.'
            raise s_exc.IsRuntForm(mesg=mesg)

        errs = False
        editor = SnapEditor(self)
        protonode = editor.loadNode(node)

        self.livenodes[node.nid] = protonode

        try:
            yield protonode
        except Exception:
            errs = True
            raise
        finally:
            self.livenodes[node.nid] = node
            if not (errs and transaction):
                nodeedits = editor.getNodeEdits()
                if nodeedits:
                    await self.saveNodeEdits(nodeedits)

    @contextlib.asynccontextmanager
    async def getEditor(self, transaction=False):

        errs = False
        editor = SnapEditor(self)

        try:
            yield editor
        except Exception:
            errs = True
            raise
        finally:
            if not (errs and transaction):
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
        nodes = {e[0]: await self.getNodeByNid(e[0]) for e in edits if e[0] is not None}

        saveoff, nodeedits = await wlyr.saveNodeEdits(edits, meta)

        # make a pass through the returned edits, apply the changes to our Nodes()
        # and collect up all the callbacks to fire at once at the end.  It is
        # critical to fire all callbacks after applying all Node() changes.

        for nid, form, edits in nodeedits:

            node = nodes.get(nid)
            if node is None:
                node = await self.getNodeByNid(nid)

            if node is None:  # pragma: no cover
                continue

            for edit in edits:

                etyp, parms = edit

                if etyp == s_layer.EDIT_NODE_ADD:
                    callbacks.append((node.form.wasAdded, (node,), {}))
                    callbacks.append((self.view.runNodeAdd, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_NODE_DEL or etyp == s_layer.EDIT_NODE_TOMB:
                    callbacks.append((node.form.wasDeleted, (node,), {}))
                    callbacks.append((self.view.runNodeDel, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_NODE_TOMB_DEL:
                    if not node.istomb():
                        callbacks.append((node.form.wasAdded, (node,), {}))
                        callbacks.append((self.view.runNodeAdd, (node,), {}))
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

                if etyp == s_layer.EDIT_PROP_TOMB_DEL:

                    (name,) = parms

                    if (oldv := node.get(name)) is not None:
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

                if etyp == s_layer.EDIT_PROP_TOMB:

                    (name,) = parms

                    oldv = node.getFromLayers(name, strt=1, defv=s_common.novalu)
                    if oldv is s_common.novalu:  # pragma: no cover
                        continue

                    prop = node.form.props.get(name)
                    if prop is None:  # pragma: no cover
                        logger.warning(f'saveNodeEdits got EDIT_PROP_TOMB for bad prop {name} on form {node.form.full}')
                        continue

                    callbacks.append((prop.wasDel, (node, oldv), {}))
                    callbacks.append((self.view.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_TAG_SET:

                    (tag, valu, oldv) = parms

                    callbacks.append((self.view.runTagAdd, (node, tag, valu), {}))
                    callbacks.append((self.wlyr.fire, ('tag:add', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_TOMB_DEL:
                    (tag,) = parms

                    if (oldv := node.getTag(tag)) is not None:
                        callbacks.append((self.view.runTagAdd, (node, tag, oldv), {}))
                        callbacks.append((self.wlyr.fire, ('tag:add', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_DEL:

                    (tag, oldv) = parms

                    callbacks.append((self.view.runTagDel, (node, tag, oldv), {}))
                    callbacks.append((self.wlyr.fire, ('tag:del', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_TOMB:

                    (tag,) = parms

                    oldv = node.getTagFromLayers(tag, strt=1, defval=s_common.novalu)
                    if oldv is s_common.novalu:  # pragma: no cover
                        continue

                    callbacks.append((self.view.runTagDel, (node, tag, oldv), {}))
                    callbacks.append((self.wlyr.fire, ('tag:del', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAGPROP_SET or etyp == s_layer.EDIT_TAGPROP_TOMB_DEL:
                    continue

                if etyp == s_layer.EDIT_TAGPROP_DEL or etyp == s_layer.EDIT_TAGPROP_TOMB:
                    continue

                if etyp == s_layer.EDIT_NODEDATA_SET:
                    name, data, oldv = parms
                    node.nodedata[name] = data
                    continue

                if etyp == s_layer.EDIT_NODEDATA_TOMB_DEL:
                    name = parms[0]
                    if (data := await node.getData(name, s_common.novalu)) is not s_common.novalu:
                        node.nodedata[name] = data
                    continue

                if etyp == s_layer.EDIT_NODEDATA_DEL:
                    name, oldv = parms
                    node.nodedata.pop(name, None)
                    continue

                if etyp == s_layer.EDIT_NODEDATA_TOMB:
                    continue

                if etyp == s_layer.EDIT_EDGE_ADD:
                    verb, n2nid = parms
                    n2 = await self.getNodeByNid(n2nid)
                    callbacks.append((self.view.runEdgeAdd, (node, verb, n2), {}))

                if etyp == s_layer.EDIT_EDGE_DEL or etyp == s_layer.EDIT_EDGE_TOMB:
                    verb, n2nid = parms
                    n2 = await self.getNodeByNid(n2nid)
                    callbacks.append((self.view.runEdgeDel, (node, verb, n2), {}))

        [await func(*args, **kwargs) for (func, args, kwargs) in callbacks]

        if nodeedits:
            await self.fire('node:edits', edits=nodeedits)

        return saveoff, nodeedits

    async def delTombstone(self, nid, tombtype, tombinfo):

        if (ndef := self.core.getNidNdef(nid)) is None:
            mesg = f'delTombstone() got an invalid nid: {nid}'
            await self._raiseOnStrict(s_exc.BadArg, mesg)
            return

        edit = None

        if tombtype == s_layer.INDX_PROP:
            (form, prop) = tombinfo
            if prop is None:
                edit = [((s_layer.EDIT_NODE_TOMB_DEL), ())]
            else:
                edit = [((s_layer.EDIT_PROP_TOMB_DEL), (prop,))]

        elif tombtype == s_layer.INDX_TAG:
            (form, tag) = tombinfo
            edit = [((s_layer.EDIT_TAG_TOMB_DEL), (tag,))]

        elif tombtype == s_layer.INDX_TAGPROP:
            (form, tag, prop) = tombinfo
            edit = [((s_layer.EDIT_TAGPROP_TOMB_DEL), (tag, prop))]

        elif tombtype == s_layer.INDX_NODEDATA:
            (name,) = tombinfo
            edit = [((s_layer.EDIT_NODEDATA_TOMB_DEL), (name,))]

        elif tombtype == s_layer.INDX_EDGE_VERB:
            (verb, n2iden) = tombinfo
            edit = [((s_layer.EDIT_EDGE_TOMB_DEL), (verb, n2iden))]

        if edit is not None:
            await self.saveNodeEdits([(nid, ndef[0], edit)])

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

        async with self.getEditor(transaction=True) as editor:
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

            if (edges := forminfo.get('edges')) is not None:
                n2adds = []
                for verb, n2iden in edges:
                    if isinstance(n2iden, (tuple, list)):
                        (n2formname, n2valu) = n2iden
                        n2form = self.core.model.form(n2formname)
                        if n2form is None:
                            continue

                        try:
                            n2valu, _ = n2form.type.norm(n2valu)
                        except s_exc.BadTypeValu as e:
                            e.errinfo['form'] = n2form.name
                            await self.warn(f'addNodes() BadTypeValu {n2form.name}={n2valu} {e}')
                            continue

                        n2buid = s_common.buid((n2formname, n2valu))
                        n2nid = self.core.getNidByBuid(n2buid)
                        if n2nid is None:
                            n2adds.append((n2iden, verb, n2buid))
                            continue

                    elif isinstance(n2iden, str) and s_common.isbuidhex(n2iden):
                        n2nid = self.core.getNidByBuid(s_common.uhex(n2iden))
                        if n2nid is None:
                            continue
                    else:
                        continue

                    await protonode.addEdge(verb, n2nid)

                if n2adds:
                    async with self.getEditor() as n2editor:
                        for (n2ndef, verb, n2buid) in n2adds:
                            await n2editor.addNode(*n2ndef)
                            break

                    for (n2ndef, verb, n2buid) in n2adds:
                        if (nid := self.core.getNidByBuid(n2buid)) is not None:
                            await protonode.addEdge(verb, nid)
                        break

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

    async def iterNodeEdgesN1(self, nid, verb=None, strt=0, stop=None):

        last = None
        gens = [layr.iterNodeEdgesN1(nid, verb=verb) for layr in self.layers[strt:stop]]

        async for item in s_common.merggenr2(gens, cmprkey=lambda x: x[:2]):
            edge = item[:2]
            if edge == last:
                continue

            await asyncio.sleep(0)
            last = edge

            if item[-1]:
                continue

            if verb is None:
                yield self.core.getAbrvVerb(edge[0]), edge[1]
            else:
                yield verb, edge[1]

    async def iterNodeEdgesN2(self, nid, verb=None):

        last = None

        async def wrap_liftgenr(lidn, genr):
            async for abrv, n1nid, tomb in genr:
                yield abrv, n1nid, lidn, tomb

        gens = []
        for indx, layr in enumerate(self.layers):
            gens.append(wrap_liftgenr(indx, layr.iterNodeEdgesN2(nid, verb=verb)))

        async for (abrv, n1nid, indx, tomb) in s_common.merggenr2(gens, cmprkey=lambda x: x[:3]):
            if (abrv, n1nid) == last:
                continue

            await asyncio.sleep(0)
            last = (abrv, n1nid)

            if tomb:
                continue

            if indx > 0:
                for layr in self.layers[0:indx]:
                    sode = layr._getStorNode(n1nid)
                    if sode is not None and sode.get('antivalu') is not None:
                        break
                else:
                    if verb is None:
                        yield self.core.getAbrvVerb(abrv), n1nid
                    else:
                        yield verb, n1nid

            else:
                if verb is None:
                    yield self.core.getAbrvVerb(abrv), n1nid
                else:
                    yield verb, n1nid

    async def hasNodeEdge(self, n1nid, verb, n2nid, strt=0, stop=None):
        for layr in self.layers[strt:stop]:
            if (retn := await layr.hasNodeEdge(n1nid, verb, n2nid)) is not None:
                return retn

    async def iterEdgeVerbs(self, n1nid, n2nid, strt=0, stop=None):

        last = None
        gens = [layr.iterEdgeVerbs(n1nid, n2nid) for layr in self.layers[strt:stop]]

        async for abrv, tomb in s_common.merggenr2(gens, cmprkey=lambda x: x[0]):
            if abrv == last:
                continue

            await asyncio.sleep(0)
            last = abrv

            if tomb:
                continue

            yield self.core.getAbrvVerb(abrv)

    async def hasNodeData(self, nid, name, strt=0, stop=None):
        '''
        Return True if the nid has nodedata set on it under the given name,
        False otherwise.
        '''
        for layr in self.layers[strt:stop]:
            if (retn := await layr.hasNodeData(nid, name)) is not None:
                return retn
        return False

    async def getNodeData(self, nid, name, defv=None, strt=0, stop=None):
        '''
        Get nodedata from closest to write layer, no merging involved.
        '''
        for layr in self.layers[strt:stop]:
            ok, valu, tomb = await layr.getNodeData(nid, name)
            if ok:
                if tomb:
                    return defv
                return valu
        return defv

    async def getNodeDataFromLayers(self, nid, name, strt=0, stop=None, defv=None):
        '''
        Get nodedata from closest to write layer, within a specific set of layers.
        '''
        for layr in self.layers[strt:stop]:
            ok, valu, tomb = await layr.getNodeData(nid, name)
            if ok:
                if tomb:
                    return defv
                return valu
        return defv

    async def iterNodeData(self, nid):
        '''
        Returns:  Iterable[Tuple[str, Any]]
        '''
        last = None
        gens = [layr.iterNodeData(nid) for layr in self.layers]

        async for abrv, valu, tomb in s_common.merggenr2(gens, cmprkey=lambda x: x[0]):
            if abrv == last:
                continue

            await asyncio.sleep(0)
            last = abrv

            if tomb:
                continue

            yield self.core.getAbrvIndx(abrv)[0], valu

    async def iterNodeDataKeys(self, nid):
        '''
        Yield each data key from the given node by nid.
        '''
        last = None
        gens = [layr.iterNodeDataKeys(nid) for layr in self.layers]

        async for abrv, tomb in s_common.merggenr2(gens, cmprkey=lambda x: x[0]):
            if abrv == last:
                continue

            await asyncio.sleep(0)
            last = abrv

            if tomb:
                continue

            yield self.core.getAbrvIndx(abrv)[0]
