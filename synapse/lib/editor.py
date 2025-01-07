import asyncio
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.scope as s_scope
import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

class ProtoNode(s_node.NodeBase):
    '''
    A prototype node used for staging node adds using a NodeEditor.
    '''
    def __init__(self, editor, buid, form, valu, node, norminfo):
        self.editor = editor
        self.model = editor.view.core.model
        self.form = form
        self.valu = valu
        self.buid = buid
        self.node = node
        self.virts = norminfo.get('virts') if norminfo is not None else None

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

        if node is not None:
            self.nid = node.nid
        else:
            self.nid = self.editor.view.core.getNidByBuid(buid)

        self.multilayer = len(self.editor.view.layers) > 1

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
                        prop = self.model.getTagProp(name)
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

        if (nid := self.nid) is not None:
            nid = s_common.int64un(nid)

        return (nid, self.form.name, edits)

    def getNodeEdit(self):

        if self.delnode or self.tombnode:
            return self.getNodeDelEdits()

        edits = []

        if not self.node or not self.node.hasvalu():
            edits.append((s_layer.EDIT_NODE_ADD, (self.valu, self.form.type.stortype, self.virts)))

        for name, valu in self.props.items():
            prop = self.form.props.get(name)
            edits.append((s_layer.EDIT_PROP_SET, (name, valu[0], None, prop.type.stortype, valu[1])))

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

        for verb, n2nid in self.edges:
            edits.append((s_layer.EDIT_EDGE_ADD, (verb, s_common.int64un(n2nid))))

        for verb, n2nid in self.edgedels:
            edits.append((s_layer.EDIT_EDGE_DEL, (verb, s_common.int64un(n2nid))))

        for verb, n2nid in self.edgetombs:
            edits.append((s_layer.EDIT_EDGE_TOMB, (verb, s_common.int64un(n2nid))))

        for verb, n2nid in self.edgetombdels:
            edits.append((s_layer.EDIT_EDGE_TOMB_DEL, (verb, s_common.int64un(n2nid))))

        for (tag, name), valu in self.tagprops.items():
            prop = self.model.getTagProp(name)
            edits.append((s_layer.EDIT_TAGPROP_SET, (tag, name, valu, None, prop.type.stortype)))

        for (tag, name) in self.tagpropdels:
            prop = self.model.getTagProp(name)
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

        if (nid := self.nid) is not None:
            nid = s_common.int64un(nid)

        return (nid, self.form.name, edits)

    async def addEdge(self, verb, n2nid, n2form=None):

        if not isinstance(verb, str):
            raise s_exc.BadArg(mesg=f'addEdge() got an invalid type for verb: {verb}')

        if not isinstance(n2nid, bytes):
            raise s_exc.BadArg(mesg=f'addEdge() got an invalid type for n2nid: {n2nid}')

        if len(n2nid) != 8:
            raise s_exc.BadArg(mesg=f'addEdge() got an invalid node id: {n2nid}')

        if n2form is None:
            if (n2ndef := self.editor.view.core.getNidNdef(n2nid)) is None:
                raise s_exc.BadArg(mesg=f'addEdge() got an unknown node id: {n2nid}')
            n2form = n2ndef[0]

        if not self.model.edgeIsValid(self.form.name, verb, n2form):
            raise s_exc.NoSuchEdge.init((self.form.name, verb, n2form))

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
            if not await self.editor.view.hasNodeEdge(self.nid, verb, n2nid):
                self.edges.add(tupl)
                return True

        if tupl in self.edgetombs:
            self.edgetombs.remove(tupl)
            return True

        toplayr = await self.editor.view.wlyr.hasNodeEdge(self.nid, verb, n2nid)
        if toplayr is True:
            return False

        if toplayr is False:
            self.edgetombdels.add(tupl)

        for layr in self.editor.view.layers[1:self.node.lastlayr()]:
            if (undr := await layr.hasNodeEdge(self.nid, verb, n2nid)) is not None:
                if undr is True:
                    # we have a value underneath, if write layer wasn't a tombstone we didn't do anything
                    return toplayr is False
                break

        self.edges.add(tupl)
        return True

    async def delEdge(self, verb, n2nid):

        if not isinstance(verb, str):
            raise s_exc.BadArg(mesg=f'delEdge() got an invalid type for verb: {verb}')

        if not isinstance(n2nid, bytes):
            raise s_exc.BadArg(mesg=f'delEdge() got an invalid type for n2nid: {n2nid}')

        if len(n2nid) != 8:
            raise s_exc.BadArg(mesg=f'delEdge() got an invalid node id: {n2nid}')

        tupl = (verb, n2nid)
        if tupl in self.edgedels or tupl in self.edgetombs:
            return False

        if tupl in self.edges:
            self.edges.remove(tupl)
            return True

        if self.nid is None:
            return False

        if not self.multilayer:
            if await self.editor.view.hasNodeEdge(self.nid, verb, n2nid):
                self.edgedels.add(tupl)
                return True
            return False

        toplayr = await self.editor.view.wlyr.hasNodeEdge(self.nid, verb, n2nid)
        if toplayr is False:
            return False

        # has or none
        if toplayr is True:
            self.edgedels.add(tupl)

        for layr in self.editor.view.layers[1:self.node.lastlayr()]:
            if (undr := await layr.hasNodeEdge(self.nid, verb, n2nid)) is not None:
                if undr:
                    self.edgetombs.add(tupl)
                    return True
                break

        return toplayr is not None

    async def delEdgesN2(self, meta=None):
        '''
        Delete edge data from the NodeEditor's write layer where this is the dest node.
        '''
        dels = []
        intnid = s_common.int64un(self.nid)

        if meta is None:
            meta = self.editor.getEditorMeta()

        async for abrv, n1nid, tomb in self.editor.view.wlyr.iterNodeEdgesN2(self.nid):
            verb = self.editor.view.core.getAbrvIndx(abrv)[0]
            n1ndef = self.editor.view.core.getNidNdef(n1nid)

            if tomb:
                edit = [((s_layer.EDIT_EDGE_TOMB_DEL), (verb, intnid))]
            else:
                edit = [((s_layer.EDIT_EDGE_DEL), (verb, intnid))]

            dels.append((s_common.int64un(n1nid), n1ndef[0], edit))

            if len(dels) >= 1000:
                await self.editor.view.saveNodeEdits(dels, meta=meta)
                dels.clear()

        if dels:
            await self.editor.view.saveNodeEdits(dels, meta=meta)

    async def getData(self, name, defv=s_common.novalu):

        if (curv := self.nodedata.get(name, s_common.novalu)) is not s_common.novalu:
            return curv

        if name in self.nodedatadels or name in self.nodedatatombs:
            return defv

        if self.node is not None:
            return await self.node.getData(name, defv=defv)

        return defv

    async def hasData(self, name):
        if name in self.nodedata:
            return True

        if name in self.nodedatadels or name in self.nodedatatombs:
            return False

        if self.node is not None:
            return await self.node.hasData(name)

        return False

    async def setData(self, name, valu):

        if await self.getData(name) == valu:
            return

        s_common.reqjsonsafe(valu)

        self.nodedata[name] = valu
        self.nodedatadels.discard(name)
        self.nodedatatombs.discard(name)

    async def popData(self, name):

        if not self.multilayer:
            valu = await self.editor.view.getNodeData(self.nid, name, defv=s_common.novalu)
            if valu is not s_common.novalu:
                self.nodedatadels.add(name)
                return valu
            return None

        (ok, valu, tomb) = await self.editor.view.wlyr.getNodeData(self.nid, name)
        if (ok and not tomb):
            self.nodedatadels.add(name)

        if tomb:
            return None

        valu = await self.editor.view.getNodeDataFromLayers(self.nid, name, strt=1, defv=s_common.novalu)
        if valu is not s_common.novalu:
            self.nodedatatombs.add(name)
            return valu
        return None

    async def _getRealTag(self, tag):

        norm, info = self.editor.view.core.getTagNorm(tag)
        tagnode = await self.editor.view.getTagNode(norm)
        if tagnode is not s_common.novalu:
            return self.editor.loadNode(tagnode)

        # check for an :isnow tag redirection in our hierarchy...
        toks = info.get('toks')
        for i in range(len(toks)):

            toktag = '.'.join(toks[:i + 1])
            toknode = await self.editor.view.getTagNode(toktag)
            if toknode is s_common.novalu:
                continue

            tokvalu = toknode.ndef[1]
            if tokvalu == toktag:
                continue

            realnow = tokvalu + norm[len(toktag):]
            tagnode = await self.editor.view.getTagNode(realnow)
            if tagnode is not s_common.novalu:
                return self.editor.loadNode(tagnode)

            norm, info = self.editor.view.core.getTagNorm(realnow)
            break

        return await self.editor.addNode('syn:tag', norm, norminfo=info)

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

        if isinstance(valu, list):
            valu = tuple(valu)

        if valu != (None, None):
            try:
                valu, _ = self.model.type('ival').norm(valu)
            except s_exc.BadTypeValu as e:
                e.set('tag', tagnode.valu)
                raise e

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
        if self.node is not None:
            alltags.update(set(self.node.getTagNames()))

        return list(sorted(alltags - self.tagdels - self.tagtombs))

    def _delTag(self, name):

        self.tags.pop(name, None)

        if not self.multilayer:
            if self.node is not None and (tags := self.node.sodes[0].get('tags')) is not None and name in tags:
                self.tagdels.add(name)

            for prop in self.getTagProps(name):
                if self.tagprops.pop((name, prop), None) is None:
                    self.tagpropdels.add((name, prop))
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
        exists = self.getTag(name, defval=s_common.novalu) is not s_common.novalu

        if len(path) > 1 and exists:

            parent = '.'.join(path[:-1])

            # retrieve a list of prunable tags
            prune = await self.editor.view.core.getTagPrune(parent)
            if prune:
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

        if exists:
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

        return defv

    def getTagPropWithLayer(self, tag, name, defv=None):

        if (tag, name) in self.tagpropdels or (tag, name) in self.tagproptombs:
            return defv, None

        curv = self.tagprops.get((tag, name))
        if curv is not None:
            return curv, 0

        if self.node is not None:
            return self.node.getTagPropWithLayer(tag, name, defval=defv)

        return defv, None

    def hasTagProp(self, tag, name):
        if (tag, name) in self.tagprops:
            return True

        if (tag, name) in self.tagpropdels or (tag, name) in self.tagproptombs:
            return False

        if self.node is not None:
            return self.node.hasTagProp(tag, name)

        return False

    async def setTagProp(self, tag, name, valu):

        tagnode = await self.addTag(tag)
        if tagnode is None:
            return False

        prop = self.model.getTagProp(name)
        if prop is None:
            raise s_exc.NoSuchTagProp(mesg=f'Tagprop {name} does not exist in this Cortex.')

        if prop.locked:
            raise s_exc.IsDeprLocked(mesg=f'Tagprop {name} is locked.')

        norm, info = prop.type.norm(valu)

        curv = self.getTagProp(tagnode.valu, name)
        if curv == norm:
            return False

        self.tagprops[(tagnode.valu, name)] = norm
        self.tagpropdels.discard((tagnode.valu, name))
        self.tagproptombs.discard((tagnode.valu, name))

        return True

    async def delTagProp(self, tag, name):

        prop = self.model.getTagProp(name)
        if prop is None:
            raise s_exc.NoSuchTagProp(mesg=f'Tagprop {name} does not exist in this Cortex.', name=name)

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
            return curv[0]

        if self.node is not None:
            return self.node.get(name, defv=defv)

        return defv

    def getWithLayer(self, name, defv=None):

        # get the current value including the pending prop sets
        if name in self.propdels or name in self.proptombs:
            return defv, None

        curv = self.props.get(name, s_common.novalu)
        if curv is not s_common.novalu:
            return curv[0], 0

        if self.node is not None:
            return self.node.getWithLayer(name, defv=defv)

        return defv, None

    async def _set(self, prop, valu, norminfo=None, ignore_ro=False):

        if prop.locked:
            raise s_exc.IsDeprLocked(mesg=f'Prop {prop.full} is locked due to deprecation.')

        if isinstance(prop.type, s_types.Array):
            arrayform = self.model.form(prop.type.arraytype.name)
            if arrayform is not None and arrayform.locked:
                raise s_exc.IsDeprLocked(mesg=f'Prop {prop.full} is locked due to deprecation.')

        if norminfo is None:
            try:
                valu, norminfo = prop.type.norm(valu)
            except s_exc.BadTypeValu as e:
                oldm = e.errinfo.get('mesg')
                e.update({'prop': prop.name,
                          'form': prop.form.name,
                          'mesg': f'Bad prop value {prop.full}={valu!r} : {oldm}'})
                raise e

        if isinstance(prop.type, s_types.Ndef):
            ndefform = self.model.form(valu[0])
            if ndefform.locked:
                raise s_exc.IsDeprLocked(mesg=f'Prop {prop.full} is locked due to deprecation.')

        curv = self.get(prop.name)
        if curv == valu:
            return False

        if not ignore_ro and prop.info.get('ro') and curv is not None:
            raise s_exc.ReadOnlyProp(mesg=f'Property is read only: {prop.full}.')

        if self.node is not None:
            await self.editor.view.core._callPropSetHook(self.node, prop, valu)

        self.props[prop.name] = (valu, norminfo.get('virts'))
        self.propdels.discard(prop.name)
        self.proptombs.discard(prop.name)

        return valu, norminfo

    async def set(self, name, valu, norminfo=None, ignore_ro=False):
        prop = self.form.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(mesg=f'No property named {name} on form {self.form.name}.')

        retn = await self._set(prop, valu, norminfo=norminfo, ignore_ro=ignore_ro)
        if retn is False:
            return False

        (valu, norminfo) = retn

        propform = self.model.form(prop.type.name)
        if propform is not None:
            await self.editor.addNode(propform.name, valu, norminfo=norminfo)

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
                await self.editor.addNode(addname, addvalu, norminfo=addinfo)

        return True

    async def pop(self, name):

        prop = self.form.prop(name)
        if prop is None:
            raise s_exc.NoSuchProp(mesg=f'No property named {name}.', name=name, form=self.form.name)

        (valu, layr) = self.getWithLayer(name, defv=s_common.novalu)
        if valu is s_common.novalu:
            return False

        if prop.info.get('ro'):
            raise s_exc.ReadOnlyProp(mesg=f'Property is read only: {prop.full}.', name=prop.full)

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

        propform = self.editor.view.core.model.form(prop.type.name)
        if propform is not None:
            ops.append(self.editor.getAddNodeOps(propform.name, valu, norminfo=norminfo))

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
                ops.append(self.editor.getAddNodeOps(addname, addvalu, norminfo=addinfo))

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

class NodeEditor:
    '''
    A NodeEditor allows tracking node edits with subs/deps as a transaction.
    '''
    def __init__(self, view, user):
        self.user = user
        self.view = view
        self.protonodes = {}
        self.maxnodes = view.core.maxnodes

    def getEditorMeta(self):
        return {
            'time': s_common.now(),
            'user': self.user.iden
        }

    async def getNodeByBuid(self, buid):
        node = await self.view.getNodeByBuid(buid)
        if node:
            return self.loadNode(node)

    async def getNodeByNid(self, nid):
        node = await self.view.getNodeByNid(nid)
        if node:
            return self.loadNode(node)

    def getNodeEdits(self):
        nodeedits = []
        for protonode in self.protonodes.values():
            nodeedit = protonode.getNodeEdit()
            if nodeedit is not None:
                nodeedits.append(nodeedit)
        return nodeedits

    async def _addNode(self, form, valu, norminfo=None):

        self.view.core._checkMaxNodes()

        if form.isrunt:
            raise s_exc.IsRuntForm(mesg=f'Cannot make runt nodes: {form.name}.')

        if form.locked:
            raise s_exc.IsDeprLocked(mesg=f'Form {form.full} is locked due to deprecation for valu={valu}.')

        if norminfo is None:
            try:
                valu, norminfo = form.type.norm(valu)
            except s_exc.BadTypeValu as e:
                e.set('form', form.name)
                raise e

        return valu, norminfo

    async def addNode(self, formname, valu, props=None, norminfo=None):

        form = self.view.core.model.form(formname)
        if form is None:
            raise s_exc.NoSuchForm(mesg=f'No form named {formname} for valu={valu}.')

        retn = await self._addNode(form, valu, norminfo=norminfo)
        if retn is None:
            return None

        valu, norminfo = retn

        protonode = await self._initProtoNode(form, valu, norminfo)
        if props is not None:
            [await protonode.set(p, v) for (p, v) in props.items()]

        return protonode

    async def getAddNodeOps(self, formname, valu, props=None, norminfo=None):

        form = self.view.core.model.form(formname)
        if form is None:
            raise s_exc.NoSuchForm(mesg=f'No form named {formname} for valu={valu}.')

        retn = await self._addNode(form, valu, norminfo=norminfo)
        if retn is None:
            return ()

        norm, norminfo = retn

        ndef = (form.name, norm)

        protonode = self.protonodes.get(ndef)
        if protonode is not None:
            return ()

        buid = s_common.buid(ndef)
        node = await self.view.getNodeByBuid(buid)
        if node is not None:
            return ()

        protonode = ProtoNode(self, buid, form, norm, node, norminfo)

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
            norminfo = node.valuvirts()
            protonode = ProtoNode(self, node.buid, node.form, node.ndef[1], node, norminfo)
            self.protonodes[node.ndef] = protonode
        return protonode

    async def _initProtoNode(self, form, norm, norminfo):

        ndef = (form.name, norm)

        protonode = self.protonodes.get(ndef)
        if protonode is not None:
            return protonode

        buid = s_common.buid(ndef)
        node = await self.view.getNodeByBuid(buid, tombs=True)

        protonode = ProtoNode(self, buid, form, norm, node, norminfo)

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
