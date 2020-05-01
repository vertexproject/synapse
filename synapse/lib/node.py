import copy
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer

logger = logging.getLogger(__name__)

class Node:
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    # def __init__(self, snap, buid=None, rawprops=None, proplayr=None):
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

    def __repr__(self):
        return f'Node{{{self.pack()}}}'

    async def addEdge(self, verb, n2iden):
        nodeedits = (
            (self.buid, self.form.name, (
                (s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()),
            )),
        )
        await self.snap.applyNodeEdits(nodeedits)

    async def delEdge(self, verb, n2iden):
        nodeedits = (
            (self.buid, self.form.name, (
                (s_layer.EDIT_EDGE_DEL, (verb, n2iden), ()),
            )),
        )
        await self.snap.applyNodeEdits(nodeedits)

    async def iterEdgesN1(self, verb=None):
        async for edge in self.snap.iterNodeEdgesN1(self.buid, verb=verb):
            yield edge

    async def iterEdgesN2(self, verb=None):
        async for edge in self.snap.iterNodeEdgesN2(self.buid, verb=verb):
            yield edge

    async def storm(self, text, opts=None, user=None, path=None):
        '''
        Args:
            path (Path):
                If set, then vars from path are copied into the new runtime, and vars are copied back out into path
                at the end

        Note:
            If opts is not None and opts['vars'] is set and path is not None, then values of path vars take precedent
        '''
        query = self.snap.core.getStormQuery(text)

        # Merge vars from path into opts.vars
        pathvars = path.vars if path is not None else None
        if opts is None:
            if pathvars is None:
                newopts = None
            else:
                newopts = {'vars': pathvars}
        else:
            vars = opts.get('vars')
            if pathvars is None:
                newopts = opts
            elif vars is None:
                newopts = {**opts, **{'vars': pathvars}}
            else:
                newopts = {**opts, **{'vars': {**vars, **pathvars}}}

        with self.snap.getStormRuntime(opts=newopts, user=user) as runt:
            runt.addInput(self)
            async for item in runt.iterStormQuery(query):
                yield item
            if path:
                path.vars.update(runt.vars)

    async def filter(self, text, opts=None, user=None, path=None):
        async for item in self.storm(text, opts=opts, user=user, path=path):
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
        tagprops = collections.defaultdict(dict)
        [tagprops[tag].__setitem__(prop, valu) for (tag, prop), valu in self.tagprops.items()]

        node = (self.ndef, {
            'iden': self.iden(),
            'tags': self.tags,
            'props': self.props,
            'tagprops': tagprops,
            'nodedata': self.nodedata,
        })

        if dorepr:

            rval = self.repr()
            if rval is not None and rval != self.ndef[1]:
                node[1]['repr'] = self.repr()

            node[1]['reprs'] = self.reprs()
            node[1]['tagpropreprs'] = self.tagpropreprs()

        return node

    async def seen(self, tick, source=None):
        '''
        Update the .seen interval and optionally a source specific seen node.
        '''
        await self.set('.seen', tick)

        if source is not None:
            seen = await self.snap.addNode('meta:seen', (source, self.ndef))
            await seen.set('.seen', tick)

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

        prop = self.form.prop(name)
        if prop is None:

            if self.snap.strict:
                raise s_exc.NoSuchProp(name=name, form=self.form.name)

            await self.snap.warn(f'NoSuchProp: name={name}')
            return False

        if self.form.isrunt:

            if prop.info.get('ro'):
                mesg = 'Cannot set read-only props on runt nodes'
                raise s_exc.IsRuntForm(mesg=mesg, form=self.form.full, prop=name, valu=valu)

            await self.snap.core.runRuntPropSet(self, prop, valu)
            return True

        curv = self.props.get(name)

        # normalize the property value...
        try:
            norm, info = prop.type.norm(valu)

        except Exception as e:
            mesg = f'Bad property value: {prop.full}={valu!r}'
            return await self.snap._raiseOnStrict(s_exc.BadTypeValu, mesg, name=prop.name, valu=valu, emesg=str(e))

        # do we already have the value?
        if curv == norm:
            return False

        if curv is not None and not init:

            if prop.info.get('ro'):

                if self.snap.strict:
                    raise s_exc.ReadOnlyProp(name=prop.full)

                # not setting a set-once prop unless we are init...
                return False

            # check for type specific merging...
            norm = prop.type.merge(curv, norm)
            if curv == norm:
                return False

        props = {prop.name: norm}
        nodeedits = await self.snap.getNodeAdds(self.form, self.ndef[1], props, addnode=False)

        await self.snap.applyNodeEdits(nodeedits)

        return True

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

    async def pop(self, name, init=False):
        '''
        Remove a property from a node and return the value
        '''
        prop = self.form.prop(name)
        if prop is None:
            if self.snap.strict:
                raise s_exc.NoSuchProp(name=name, form=self.form.name)
            await self.snap.warn(f'No Such Property: {name}')
            return False

        if self.form.isrunt:
            if prop.info.get('ro'):
                raise s_exc.IsRuntForm(mesg='Cannot delete read-only props on runt nodes',
                                       form=self.form.full, prop=name)
            return await self.snap.core.runRuntPropDel(self, prop)

        if not init:

            if prop.info.get('ro'):
                if self.snap.strict:
                    raise s_exc.ReadOnlyProp(name=name)
                await self.snap.warn(f'Property is read-only: {name}')
                return False

        curv = self.props.pop(name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        edits = (
            (s_layer.EDIT_PROP_DEL, (prop.name, None, prop.type.stortype), ()),
        )

        await self.snap.applyNodeEdit((self.buid, self.form.name, edits))

    def repr(self, name=None, defv=None):

        if name is None:
            return self.form.type.repr(self.ndef[1])

        prop = self.form.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(form=self.form.name, prop=name)

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

        for (tag, name), valu in self.tagprops.items():

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

        path = s_chop.tagpath(tag)

        name = '.'.join(path)

        tagnode = await self.snap.addTagNode(name)

        # implement tag renames...
        isnow = tagnode.get('isnow')
        if isnow:
            await self.snap.warn(f'tag {name} is now {isnow}')
            name = isnow
            path = isnow.split('.')

        if isinstance(valu, list):
            valu = tuple(valu)

        if valu != (None, None):
            valu = self.snap.core.model.type('ival').norm(valu)[0]

        curv = self.tags.get(name)
        if curv == valu:
            return

        edits = []
        if curv is None:

            tags = s_chop.tags(name)
            for tag in tags[:-1]:

                if self.tags.get(tag) is not None:
                    continue

                await self.snap.addTagNode(tag)

                edits.append((s_layer.EDIT_TAG_SET, (tag, (None, None), None), ()))

        else:
            # merge values into one interval
            valu = s_time.ival(*valu, *curv)

        if valu == curv:
            return

        edits.append((s_layer.EDIT_TAG_SET, (name, valu, None), ()))

        nodeedit = (self.buid, self.form.name, edits)

        await self.snap.applyNodeEdit(nodeedit)

    async def delTag(self, tag, init=False):
        '''
        Delete a tag from the node.
        '''
        path = s_chop.tagpath(tag)

        name = '.'.join(path)

        if self.form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot delete tags from runt nodes.',
                                   form=self.form.full, tag=tag)

        curv = self.tags.get(name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        pref = name + '.'

        subtags = [(len(t), t) for t in self.tags.keys() if t.startswith(pref)]
        subtags.sort(reverse=True)

        # order matters...
        edits = []

        for _, subtag in subtags:

            edits.extend(self._getTagPropDel(subtag))
            edits.append((s_layer.EDIT_TAG_DEL, (subtag, None), ()))

        edits.extend(self._getTagPropDel(name))
        edits.append((s_layer.EDIT_TAG_DEL, (name, None), ()))

        nodeedit = (self.buid, self.form.name, edits)

        await self.snap.applyNodeEdit(nodeedit)

    def _getTagPropDel(self, tag):

        edits = []
        for tagprop in self.getTagProps(tag):

            prop = self.snap.core.model.getTagProp(tagprop)

            if prop is None: # pragma: no cover
                logger.warn(f'Cant delete tag prop ({tagprop}) without model prop!')
                continue

            edits.append((s_layer.EDIT_TAGPROP_DEL, (tag, tagprop, None, prop.type.stortype), ()))

        return edits

    def getTagProps(self, tag):
        return [p for (t, p) in self.tagprops.keys() if t == tag]

    def hasTagProp(self, tag, prop):
        '''
        Check if a #foo.bar:baz tag property exists on the node.
        '''
        return (tag, prop) in self.tagprops

    def getTagProp(self, tag, prop, defval=None):
        '''
        Return the value (or defval) of the given tag property.
        '''
        return self.tagprops.get((tag, prop), defval)

    async def setTagProp(self, tag, name, valu):
        '''
        Set the value of the given tag property.
        '''
        if not self.hasTag(tag):
            await self.addTag(tag)

        prop = self.snap.core.model.getTagProp(name)
        if prop is None:
            raise s_exc.NoSuchTagProp(mesg='Tag prop does not exist in this Cortex.',
                                      name=name)

        try:
            norm, info = prop.type.norm(valu)
        except Exception as e:
            mesg = f'Bad property value: #{tag}:{prop.name}={valu!r}'
            return await self.snap._raiseOnStrict(s_exc.BadTypeValu, mesg, name=prop.name, valu=valu, emesg=str(e))

        tagkey = (tag, name)

        edits = (
            (s_layer.EDIT_TAGPROP_SET, (tag, name, norm, None, prop.type.stortype), ()),
        )

        await self.snap.applyNodeEdit((self.buid, self.form.name, edits))

        self.tagprops[tagkey] = norm

    async def delTagProp(self, tag, name):

        prop = self.snap.core.model.getTagProp(name)
        if prop is None:
            raise s_exc.NoSuchTagProp(name=name)

        curv = self.tagprops.get((tag, name), s_common.novalu)
        if curv is s_common.novalu:
            return False

        edits = (
            (s_layer.EDIT_TAGPROP_DEL, (tag, name, None, prop.type.stortype), ()),
        )

        await self.snap.applyNodeEdit((self.buid, self.form.name, edits))

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
                * log tag:del splices

            * delete all secondary properties
                * fire onDelProp handler
                * delete secondary property from storage
                * log prop:del splices

            * delete the primary property
                * fire onDel handlers for the node
                * delete primary property from storage
                * log node:del splices
        '''

        formname, formvalu = self.ndef

        if self.form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot delete runt nodes',
                                   form=formname, valu=formvalu)

        tags = [(len(t), t) for t in self.tags.keys()]

        # check for any nodes which reference us...
        if not force:

            # refuse to delete tag nodes with existing tags
            if self.form.name == 'syn:tag':

                async for _ in self.snap.nodesByTag(self.ndef[1]):  # NOQA
                    mesg = 'Nodes still have this tag.'
                    return await self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname)

            async for refr in self.snap.nodesByPropTypeValu(formname, formvalu):

                if refr.buid == self.buid:
                    continue

                mesg = 'Other nodes still refer to this node.'
                return await self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname)

        # TODO put these into one edit...

        for _, tag in sorted(tags, reverse=True):
            await self.delTag(tag, init=True)

        for name in list(self.props.keys()):
            await self.pop(name, init=True)

        edits = (
            (s_layer.EDIT_NODE_DEL, (formvalu, self.form.type.stortype), ()),
        )

        await self.snap.applyNodeEdit((self.buid, formname, edits))

        self.snap.livenodes.pop(self.buid, None)

    async def getData(self, name):
        valu = self.nodedata.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu
        return await self.snap.getNodeData(self.buid, name)

    async def setData(self, name, valu):
        edits = (
            (s_layer.EDIT_NODEDATA_SET, (name, valu, None), ()),
        )
        await self.snap.applyNodeEdits(((self.buid, self.form.name, edits),))

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

class Path:
    '''
    A path context tracked through the storm runtime.
    '''
    def __init__(self, runt, vars, nodes):

        self.node = None
        self.runt = runt
        # we must "smell" like a runt for some AST ops
        self.snap = runt.snap
        self.model = runt.model
        self.nodes = nodes

        self.traces = []

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

    def trace(self):
        '''
        Construct and return a Trace object for this path.
        '''
        trace = Trace(self)
        self.traces.append(trace)
        return trace

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

        return self.runt.getVar(name, defv=defv)

    def setVar(self, name, valu):
        self.vars[name] = valu

    def meta(self, name, valu):
        '''
        Add node specific metadata to be returned with the node.
        '''
        self.metadata[name] = valu

    def pack(self, path=False):
        ret = dict(self.metadata)
        if path:
            ret['nodes'] = [node.iden() for node in self.nodes]
        return ret

    def fork(self, node):

        nodes = list(self.nodes)
        nodes.append(node)

        path = Path(self.runt, dict(self.vars), nodes)
        path.traces.extend(self.traces)

        [t.addFork(path) for t in self.traces]

        return path

    def clone(self):
        path = Path(self.runt,
                    copy.copy(self.vars),
                    copy.copy(self.nodes),)
        path.traces = list(self.traces)
        path.frames = [(copy.copy(vars), runt) for (vars, runt) in self.frames]
        return path

    def initframe(self, initvars=None, initrunt=None):

        # full copy for now...
        framevars = self.vars.copy()
        if initvars is not None:
            framevars.update(initvars)

        if initrunt is None:
            initrunt = self.runt

        self.frames.append((self.vars, self.runt))

        self.runt = initrunt
        self.vars = framevars

    def finiframe(self, runt):

        if not self.frames:
            self.vars.clear()
            self.runt = runt
            return

        (self.vars, self.runt) = self.frames.pop()

class Trace:
    '''
    A trace for pivots taken and nodes involved from a given path's subsequent forks.
    '''
    def __init__(self, path):
        self.edges = set()
        self.nodes = set()

        self.addPath(path)

    def addPath(self, path):

        [self.nodes.add(n) for n in path.nodes]

        for i in range(len(path.nodes[:-1])):
            n1 = path.nodes[i]
            n2 = path.nodes[i + 1]
            self.edges.add((n1, n2))

    def addFork(self, path):
        self.nodes.add(path.node)
        self.edges.add((path.nodes[-2], path.nodes[-1]))

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
