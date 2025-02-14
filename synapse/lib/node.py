import copy
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

class Node:
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    def __init__(self, snap, sode, bylayer=None):
        self.snap = snap
        self.sode = sode

        self.buid = sode[0]

        # Tracks which property is retrieved from which layer
        self.bylayer = bylayer

        # if set, the node is complete.
        self.ndef = sode[1].get('ndef')
        self.form = snap.core.model.form(self.ndef[0])

        self.props = sode[1].get('props')
        if self.props is None:
            self.props = {}

        self.tags = sode[1].get('tags')
        if self.tags is None:
            self.tags = {}

        self.tagprops = sode[1].get('tagprops')
        if self.tagprops is None:
            self.tagprops = {}

        self.nodedata = sode[1].get('nodedata')
        if self.nodedata is None:
            self.nodedata = {}

    async def getStorNodes(self):
        '''
        Return a list of the raw storage nodes for each layer.
        '''
        return await self.snap.view.getStorNodes(self.buid)

    def getByLayer(self):
        '''
        Return a dictionary that translates the node's bylayer dict to a primitive.
        '''
        return s_msgpack.deepcopy(self.bylayer)

    def __repr__(self):
        return f'Node{{{self.pack()}}}'

    async def addEdge(self, verb, n2iden, extra=None):
        if self.form.isrunt:
            mesg = f'Edges cannot be used with runt nodes: {self.form.full}'
            exc = s_exc.IsRuntForm(mesg=mesg, form=self.form.full)
            if extra is not None:
                exc = extra(exc)
            raise exc

        async with self.snap.getNodeEditor(self) as editor:
            return await editor.addEdge(verb, n2iden)

    async def delEdge(self, verb, n2iden, extra=None):
        if self.form.isrunt:
            mesg = f'Edges cannot be used with runt nodes: {self.form.full}'
            exc = s_exc.IsRuntForm(mesg=mesg, form=self.form.full)
            if extra is not None:
                exc = extra(exc)
            raise exc

        async with self.snap.getNodeEditor(self) as editor:
            return await editor.delEdge(verb, n2iden)

    async def iterEdgesN1(self, verb=None):
        async for edge in self.snap.iterNodeEdgesN1(self.buid, verb=verb):
            yield edge

    async def iterEdgesN2(self, verb=None):
        async for edge in self.snap.iterNodeEdgesN2(self.buid, verb=verb):
            yield edge

    async def iterEdgeVerbs(self, n2buid):
        async for verb in self.snap.iterEdgeVerbs(self.buid, n2buid):
            yield verb

    async def storm(self, runt, text, opts=None, path=None):
        '''
        Args:
            path (Path):
                If set, then vars from path are copied into the new runtime, and vars are copied back out into path
                at the end

        Note:
            If opts is not None and opts['vars'] is set and path is not None, then values of path vars take precedent
        '''
        query = await self.snap.core.getStormQuery(text)

        if opts is None:
            opts = {}

        opts.setdefault('vars', {})
        if path is not None:
            opts['vars'].update(path.vars)

        async with runt.getSubRuntime(query, opts=opts) as subr:

            subr.addInput(self)

            async for subn, subp in subr.execute():
                yield subn, subp

            if path is not None:
                path.vars.update(subr.vars)

    async def filter(self, runt, text, opts=None, path=None):
        async for item in self.storm(runt, text, opts=opts, path=path):
            return False
        return True

    def iden(self):
        return s_common.ehex(self.buid)

    def pack(self, dorepr=False):
        '''
        Return the serializable/packed version of the node.

        Args:
            dorepr (bool): Include repr information for human readable versions of properties.

        Returns:
            (tuple): An (ndef, info) node tuple.
        '''

        node = (self.ndef, {
            'iden': self.iden(),
            'tags': self.tags,
            'props': self.props,
            'tagprops': self.tagprops,
            'nodedata': self.nodedata,
        })
        if dorepr:

            rval = self.repr()
            if rval is not None and rval != self.ndef[1]:
                node[1]['repr'] = self.repr()

            node[1]['reprs'] = self.reprs()
            node[1]['tagpropreprs'] = self.tagpropreprs()

        return node

    async def getEmbeds(self, embeds):
        '''
        Return a dictionary of property embeddings.
        '''
        retn = {}
        cache = {}
        async def walk(n, p):

            valu = n.props.get(p)
            if valu is None:
                return None

            prop = n.form.prop(p)
            if prop is None:
                return None

            if prop.modl.form(prop.type.name) is not None:
                buid = s_common.buid((prop.type.name, valu))
            elif prop.type.name == 'ndef':
                buid = s_common.buid(valu)
            else:
                return None

            step = cache.get(buid, s_common.novalu)
            if step is s_common.novalu:
                step = cache[buid] = await node.snap.getNodeByBuid(buid)

            return step

        for nodepath, relprops in embeds.items():

            steps = nodepath.split('::')

            node = self
            for propname in steps:
                node = await walk(node, propname)
                if node is None:
                    break

            if node is None:
                continue

            embdnode = retn.get(nodepath)
            if embdnode is None:
                embdnode = retn[nodepath] = {}
                embdnode['*'] = s_common.ehex(node.buid)

            for relp in relprops:
                embdnode[relp] = node.props.get(relp)

        return retn

    def getNodeRefs(self):
        '''
        Return a list of (prop, (form, valu)) refs out for the node.
        '''
        retn = []

        refs = self.form.getRefsOut()

        for name, dest in refs.get('prop', ()):
            valu = self.props.get(name)
            if valu is None:
                continue

            retn.append((name, (dest, valu)))

        for name in refs.get('ndef', ()):
            valu = self.props.get(name)
            if valu is None:
                continue
            retn.append((name, valu))

        for name, dest in refs.get('array', ()):

            valu = self.props.get(name)
            if valu is None:
                continue

            for item in valu:
                retn.append((name, (dest, item)))

        for name in refs.get('ndefarray', ()):
            if (valu := self.props.get(name)) is None:
                continue

            for item in valu:
                retn.append((name, item))

        return retn

    async def set(self, name, valu, init=False):
        '''
        Set a property on the node.

        Args:
            name (str): The name of the property.
            valu (obj): The value of the property.
            init (bool): Set to True to disable read-only enforcement

        Returns:
            (bool): True if the property was changed.
        '''
        if self.snap.readonly:
            mesg = 'Cannot set property in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        prop = self.form.props.get(name)
        if prop is None:
            mesg = f'No property named {name} on form {self.form.name}.'
            await self.snap._raiseOnStrict(s_exc.NoSuchProp, mesg)
            return False

        if self.form.isrunt:
            if prop.info.get('ro'):
                mesg = f'Cannot set read-only props on runt nodes: {s_common.trimText(repr(valu))}'
                raise s_exc.IsRuntForm(mesg=mesg, form=self.form.full, prop=name)

            await self.snap.core.runRuntPropSet(self, prop, valu)
            return True

        async with self.snap.getNodeEditor(self) as editor:
            return await editor.set(name, valu)

    def has(self, name):
        return name in self.props

    def get(self, name):
        '''
        Return a secondary property value from the Node.

        Args:
            name (str): The name of a secondary property.

        Returns:
            (obj): The secondary property value or None.
        '''
        if name.startswith('#'):
            return self.tags.get(name[1:])
        return self.props.get(name)

    async def _getPropDelEdits(self, name, init=False):

        prop = self.form.prop(name)
        if prop is None:
            if self.snap.strict:
                mesg = f'No property named {name}.'
                raise s_exc.NoSuchProp(mesg=mesg, name=name, form=self.form.name)
            await self.snap.warn(f'No Such Property: {name}')
            return ()

        if not init:

            if prop.info.get('ro'):
                if self.snap.strict:
                    raise s_exc.ReadOnlyProp(name=name)
                await self.snap.warn(f'Property is read-only: {name}')
                return ()

        curv = self.props.get(name, s_common.novalu)
        if curv is s_common.novalu:
            return ()

        edits = (
            (s_layer.EDIT_PROP_DEL, (prop.name, None, prop.type.stortype), ()),
        )
        return edits

    async def pop(self, name, init=False):
        '''
        Remove a property from a node and return the value
        '''
        if self.form.isrunt:
            prop = self.form.prop(name)
            if prop.info.get('ro'):
                raise s_exc.IsRuntForm(mesg='Cannot delete read-only props on runt nodes',
                                       form=self.form.full, prop=name)
            return await self.snap.core.runRuntPropDel(self, prop)

        edits = await self._getPropDelEdits(name, init=init)
        if not edits:
            return False

        await self.snap.applyNodeEdit((self.buid, self.form.name, edits), nodecache={self.buid: self})
        return True

    def repr(self, name=None, defv=None):

        if name is None:
            return self.form.type.repr(self.ndef[1])

        prop = self.form.props.get(name)
        if prop is None:
            mesg = f'No property named {name}.'
            raise s_exc.NoSuchProp(mesg=mesg, form=self.form.name, prop=name)

        valu = self.props.get(name)
        if valu is None:
            return defv

        return prop.type.repr(valu)

    def reprs(self):
        '''
        Return a dictionary of repr values for props whose repr is different than
        the system mode value.
        '''
        reps = {}

        for name, valu in self.props.items():

            prop = self.form.prop(name)
            if prop is None:
                continue

            rval = prop.type.repr(valu)
            if rval is None or rval == valu:
                continue

            reps[name] = rval

        return reps

    def tagpropreprs(self):
        '''
        Return a dictionary of repr values for tagprops whose repr is different than
        the system mode value.
        '''
        reps = collections.defaultdict(dict)

        for tag, propdict in self.tagprops.items():
            for name, valu in propdict.items():

                prop = self.form.modl.tagprop(name)
                if prop is None:
                    continue

                rval = prop.type.repr(valu)
                if rval is None or rval == valu:
                    continue
                reps[tag][name] = rval

        return dict(reps)

    def hasTag(self, name):
        name = s_chop.tag(name)
        return name in self.tags

    def getTag(self, name, defval=None):
        name = s_chop.tag(name)
        return self.tags.get(name, defval)

    def getTags(self, leaf=False):

        if not leaf:
            return list(self.tags.items())

        # longest first
        retn = []

        # brute force rather than build a tree.  faster in small sets.
        for _, tag, valu in sorted([(len(t), t, v) for (t, v) in self.tags.items()], reverse=True):

            look = tag + '.'
            if any([r.startswith(look) for (r, rv) in retn]):
                continue

            retn.append((tag, valu))

        return retn

    async def addTag(self, tag, valu=(None, None)):
        '''
        Add a tag to a node.

        Args:
            tag (str): The tag to add to the node.
            valu: The optional tag value.  If specified, this must be a value that
                  norms as a valid time interval as an ival.

        Returns:
            None: This returns None.
        '''
        if self.form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot add tags to runt nodes.',
                                   form=self.form.full, tag=tag)

        async with self.snap.getNodeEditor(self) as protonode:
            await protonode.addTag(tag, valu=valu)

    def _getTagTree(self):

        root = (None, {})
        for tag in self.tags.keys():

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

    async def _getTagDelEdits(self, tag, init=False):

        path = s_chop.tagpath(tag)

        name = '.'.join(path)

        if self.form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot delete tags from runt nodes.',
                                   form=self.form.full, tag=tag)

        pref = name + '.'
        exists = self.tags.get(name, s_common.novalu) is not s_common.novalu

        todel = [(len(t), t) for t in self.tags.keys() if t.startswith(pref)]

        # only prune when we're actually deleting a tag
        if len(path) > 1 and exists:

            parent = '.'.join(path[:-1])

            # retrieve a list of prunable tags
            prune = await self.snap.core.getTagPrune(parent)
            if prune:

                tree = self._getTagTree()

                for prunetag in reversed(prune):

                    node = tree
                    for step in prunetag.split('.'):

                        node = node[1].get(step)
                        if node is None:
                            break

                    if node is not None and len(node[1]) == 1:
                        todel.append((len(node[0]), node[0]))
                        continue

                    break

        todel.sort(reverse=True)

        # order matters...
        edits = []

        for _, subtag in todel:

            edits.extend(self._getTagPropDel(subtag))
            edits.append((s_layer.EDIT_TAG_DEL, (subtag, None), ()))

        edits.extend(self._getTagPropDel(name))
        if exists:
            edits.append((s_layer.EDIT_TAG_DEL, (name, None), ()))

        return edits

    async def delTag(self, tag, init=False):
        '''
        Delete a tag from the node.
        '''
        edits = await self._getTagDelEdits(tag, init=init)
        if edits:
            nodeedit = (self.buid, self.form.name, edits)
            await self.snap.applyNodeEdit(nodeedit, nodecache={self.buid: self})

    def _getTagPropDel(self, tag):

        edits = []
        for tagprop in self.getTagProps(tag):

            prop = self.snap.core.model.getTagProp(tagprop)

            if prop is None:  # pragma: no cover
                logger.warn(f'Cant delete tag prop ({tagprop}) without model prop!')
                continue
            edits.append((s_layer.EDIT_TAGPROP_DEL, (tag, tagprop, None, prop.type.stortype), ()))

        return edits

    def getTagProps(self, tag):
        propdict = self.tagprops.get(tag)
        if not propdict:
            return []
        return list(propdict.keys())

    def hasTagProp(self, tag, prop):
        '''
        Check if a #foo.bar:baz tag property exists on the node.
        '''
        return tag in self.tagprops and prop in self.tagprops[tag]

    def getTagProp(self, tag, prop, defval=None):
        '''
        Return the value (or defval) of the given tag property.
        '''
        propdict = self.tagprops.get(tag)
        if propdict:
            return propdict.get(prop, defval)
        return defval

    async def setTagProp(self, tag, name, valu):
        '''
        Set the value of the given tag property.
        '''
        async with self.snap.getNodeEditor(self) as editor:
            await editor.setTagProp(tag, name, valu)

    async def delTagProp(self, tag, name):
        prop = self.snap.core.model.getTagProp(name)
        if prop is None:
            raise s_exc.NoSuchTagProp(name=name)

        propdict = self.tagprops.get(tag)
        if not propdict:
            return False

        curv = propdict.get(name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        edits = (
            (s_layer.EDIT_TAGPROP_DEL, (tag, name, None, prop.type.stortype), ()),
        )

        await self.snap.applyNodeEdit((self.buid, self.form.name, edits), nodecache={self.buid: self})

    async def delete(self, force=False):
        '''
        Delete a node from the cortex.

        The following tear-down operations occur in order:

            * validate that you have permissions to delete the node
            * validate that you have permissions to delete all tags
            * validate that there are no remaining references to the node.

            * delete all the tags (bottom up)
                * fire onDelTag() handlers
                * delete tag properties from storage

            * delete all secondary properties
                * fire onDelProp handler
                * delete secondary property from storage

            * delete the primary property
                * fire onDel handlers for the node
                * delete primary property from storage

        '''

        formname, formvalu = self.ndef

        if self.form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot delete runt nodes',
                                   form=formname, valu=formvalu)

        # top level tags will cause delete cascades
        tags = [t for t in self.tags.keys() if len(t.split('.')) == 1]

        # check for any nodes which reference us...
        if not force:

            # refuse to delete tag nodes with existing tags
            if self.form.name == 'syn:tag':

                async for _ in self.snap.nodesByTag(self.ndef[1]):  # NOQA
                    mesg = 'Nodes still have this tag.'
                    return await self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname,
                                                          iden=self.iden())

            async for refr in self.snap.nodesByPropTypeValu(formname, formvalu):

                if refr.buid == self.buid:
                    continue

                mesg = 'Other nodes still refer to this node.'
                return await self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname,
                                                      iden=self.iden())

            async for edge in self.iterEdgesN2():

                if self.iden() == edge[1]:
                    continue

                mesg = 'Other nodes still have light edges to this node.'
                return await self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname,
                                                      iden=self.iden())

        edits = []
        for tag in tags:
            edits.extend(await self._getTagDelEdits(tag, init=True))

        for name in self.props.keys():
            edits.extend(await self._getPropDelEdits(name, init=True))

        # Only remove nodedata if we're in a layer that doesn't have the full node
        if self.snap.wlyr.iden != self.bylayer['ndef']:
            async for name in self.iterDataKeys():
                edits.append((s_layer.EDIT_NODEDATA_DEL, (name, None), ()))

        edits.append(
            (s_layer.EDIT_NODE_DEL, (formvalu, self.form.type.stortype), ()),
        )

        await self.snap.applyNodeEdit((self.buid, formname, edits))
        self.snap.livenodes.pop(self.buid, None)

    async def hasData(self, name):
        if name in self.nodedata:
            return True
        return await self.snap.hasNodeData(self.buid, name)

    async def getData(self, name, defv=None):
        valu = self.nodedata.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu
        return await self.snap.getNodeData(self.buid, name, defv=defv)

    async def setData(self, name, valu):
        async with self.snap.getNodeEditor(self) as protonode:
            await protonode.setData(name, valu)

    async def popData(self, name):
        retn = await self.snap.getNodeData(self.buid, name)

        edits = (
            (s_layer.EDIT_NODEDATA_DEL, (name, None), ()),
        )
        await self.snap.applyNodeEdits(((self.buid, self.form.name, edits),))

        return retn

    async def iterData(self):
        async for item in self.snap.iterNodeData(self.buid):
            yield item

    async def iterDataKeys(self):
        async for name in self.snap.iterNodeDataKeys(self.buid):
            yield name

class Path:
    '''
    A path context tracked through the storm runtime.
    '''
    def __init__(self, vars, nodes, links=None):

        self.node = None
        self.nodes = nodes

        if links is not None:
            self.links = links
        else:
            self.links = []

        if len(nodes):
            self.node = nodes[-1]

        self.vars = vars
        self.frames = []
        self.ctors = {}

        # "builtins" which are *not* vars
        # ( this allows copying variable context )
        self.builtins = {
            'path': self,
            'node': self.node,
        }

        self.metadata = {}

    def getVar(self, name, defv=s_common.novalu):

        # check if the name is in our variables
        valu = self.vars.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        # check if it's in builtins
        valu = self.builtins.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        ctor = self.ctors.get(name)
        if ctor is not None:
            valu = ctor(self)
            self.vars[name] = valu
            return valu

        return s_common.novalu

    async def setVar(self, name, valu):
        self.vars[name] = valu

    async def popVar(self, name):
        return self.vars.pop(name, s_common.novalu)

    def meta(self, name, valu):
        '''
        Add node specific metadata to be returned with the node.
        '''
        self.metadata[name] = valu

    async def pack(self, path=False):
        info = await s_stormtypes.toprim(dict(self.metadata))
        if path:
            info['nodes'] = [node.iden() for node in self.nodes]

        return info

    def fork(self, node, link):

        links = list(self.links)
        if self.node is not None and link is not None:
            links.append((self.node.iden(), link))

        nodes = list(self.nodes)
        nodes.append(node)

        path = Path(self.vars.copy(), nodes, links=links)

        return path

    def clone(self):
        path = Path(copy.copy(self.vars), copy.copy(self.nodes), copy.copy(self.links))
        path.frames = [v.copy() for v in self.frames]
        return path

    def initframe(self, initvars=None):

        framevars = {}
        if initvars is not None:
            framevars.update(initvars)

        self.frames.append(self.vars)

        self.vars = framevars

    def finiframe(self):
        '''
        Pop a scope frame from the path, restoring runt if at the top
        Args:
            runt (Runtime): A storm runtime to restore if we're at the top
            merge (bool): Set to true to merge vars back up into the next frame
        '''
        if not self.frames:
            self.vars.clear()
            return

        self.vars = self.frames.pop()

def props(pode):
    '''
    Get the props from the node.

    Args:
        pode (tuple): A packed node.

    Notes:
        This will include any universal props present on the node.

    Returns:
        dict: A dictionary of properties.
    '''
    return pode[1]['props'].copy()

def prop(pode, prop):
    '''
    Return the valu of a given property on the node.

    Args:
        pode (tuple): A packed node.
        prop (str): Property to retrieve.

    Notes:
        The prop argument may be the full property name (foo:bar:baz), relative property name (:baz) , or the unadorned
        property name (baz).

    Returns:

    '''
    form = pode[0][0]
    if prop.startswith(form):
        prop = prop[len(form):]
    if prop[0] == ':':
        prop = prop[1:]
    return pode[1]['props'].get(prop)

def tags(pode, leaf=False):
    '''
    Get all the tags for a given node.

    Args:
        pode (tuple): A packed node.
        leaf (bool): If True, only return leaf tags

    Returns:
        list: A list of tag strings.
    '''
    if not leaf:
        return list(pode[1]['tags'].keys())
    return _tagscommon(pode, True)

def tagsnice(pode):
    '''
    Get all the leaf tags and the tags that have values or tagprops.

    Args:
        pode (tuple): A packed node.

    Returns:
        list: A list of tag strings.
    '''
    ret = _tagscommon(pode, False)
    for tag in pode[1].get('tagprops', {}):
        if tag not in ret:
            ret.append(tag)
    return ret

def _tagscommon(pode, leafonly):
    '''
    Return either all the leaf tags or all the leaf tags and all the internal tags with values
    '''
    retn = []

    # brute force rather than build a tree.  faster in small sets.
    for tag, val in sorted((t for t in pode[1]['tags'].items()), reverse=True, key=lambda x: len(x[0])):
        look = tag + '.'
        val = tuple(val)
        if (leafonly or val == (None, None)) and any([r.startswith(look) for r in retn]):
            continue
        retn.append(tag)
    return retn

def tagged(pode, tag):
    '''
    Check if a packed node has a given tag.

    Args:
        pode (tuple): A packed node.
        tag (str): The tag to check.

    Examples:
        Check if a node is tagged with "woot" and dostuff if it is.

            if s_node.tagged(node,'woot'):
                dostuff()

    Notes:
        If the tag starts with `#`, this is removed prior to checking.

    Returns:
        bool: True if the tag is present. False otherwise.
    '''
    if tag.startswith('#'):
        tag = tag[1:]
    return pode[1]['tags'].get(tag) is not None

def ndef(pode):
    '''
    Return a node definition (<form>,<valu>) tuple from the node.

    Args:
        pode (tuple): A packed node.

    Returns:
        ((str,obj)):    The (<form>,<valu>) tuple for the node
    '''
    return pode[0]

def iden(pode):
    '''
    Return the iden (buid) of the packed node.

    Args:
        pode (tuple): A packed node.

    Returns:
        str: The node iden.
    '''
    return pode[1].get('iden')

def reprNdef(pode):
    '''
    Get the ndef of the pode with a human readable value.

    Args:
        pode (tuple): A packed node.

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

    Returns:
        (str, str): A tuple of form and the human readable value.

    '''
    ((form, valu), info) = pode
    formvalu = info.get('repr')
    if formvalu is None:
        formvalu = str(valu)
    return form, formvalu

def reprProp(pode, prop):
    '''
    Get the human readable value for a secondary property from the pode.

    Args:
        pode (tuple): A packed node.
        prop:

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

        The prop argument may be the full property name (foo:bar:baz), relative
        property name (:baz) , or the unadorned property name (baz).

    Returns:
        str: The human readable property value.  If the property is not present, returns None.
    '''
    form = pode[0][0]
    if prop.startswith(form):
        prop = prop[len(form):]
    if prop[0] == ':':
        prop = prop[1:]
    opropvalu = pode[1].get('props').get(prop)
    if opropvalu is None:
        return None
    propvalu = pode[1].get('reprs', {}).get(prop)
    if propvalu is None:
        return str(opropvalu)
    return propvalu

def reprTag(pode, tag):
    '''
    Get the human readable value for the tag timestamp from the pode.

    Args:
        pode (tuple): A packed node.
        tag (str): The tag to get the value for.

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

        If the tag does not have a timestamp, this returns a empty string.

    Returns:
        str: The human readable value for the tag. If the tag is not present, returns None.
    '''
    tag = tag.lstrip('#')
    valu = pode[1]['tags'].get(tag)
    if valu is None:
        return None
    valu = tuple(valu)
    if valu == (None, None):
        return ''
    mint = s_time.repr(valu[0])
    maxt = s_time.repr(valu[1])
    valu = f'({mint}, {maxt})'
    return valu

def reprTagProps(pode, tag):
    '''
    Get the human readable values for any tagprops on a tag for a given node.

    Args:
        pode (tuple): A packed node.
        tag (str): The tag to get the tagprops reprs for.

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

        If the tag does not have any tagprops associated with it, this returns an empty list.

    Returns:
        list: A list of tuples, containing the name of the tagprop and the repr value.
    '''
    ret = []
    exists = pode[1]['tags'].get(tag)
    if exists is None:
        return ret
    tagprops = pode[1].get('tagprops', {}).get(tag)
    if tagprops is None:
        return ret
    for prop, valu in tagprops.items():
        rval = pode[1].get('tagpropreprs', {}).get(tag, {}).get(prop)
        if rval is not None:
            ret.append((prop, rval))
        else:
            ret.append((prop, str(valu)))
    return sorted(ret, key=lambda x: x[0])
