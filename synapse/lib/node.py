import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.types as s_types

import synapse.lib.editatom as s_editatom

logger = logging.getLogger(__name__)

class Node:
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    def __init__(self, snap, buid=None, rawprops=None, proplayr=None):

        self.snap = snap

        self.buid = buid

        self.init = False  # True if the node is being added.

        # if set, the node is complete.
        self.ndef = None
        self.form = None
        self.isrunt = None

        self.tags = {}
        self.props = {}
        self.univs = {}

        # raw prop -> layer it was set at
        self.proplayr = collections.defaultdict(lambda: self.snap.wlyr, proplayr or {})

        # self.buid may be None during initial node construction...
        if rawprops is not None:
            self._loadNodeData(rawprops)

        if self.ndef is not None:
            self.form = self.snap.model.form(self.ndef[0])
            self.isrunt = self.form.isrunt

    def __repr__(self):
        return f'Node{{{self.pack()}}}'

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

    def _loadNodeData(self, rawprops):

        for prop, valu in rawprops:

            p0 = prop[0]

            # check for primary property
            if p0 == '*':
                self.ndef = (prop[1:], valu)
                continue

            # check for tag encoding
            if p0 == '#':
                self.tags[prop[1:]] = valu
                continue

            # otherwise, it's a regular property!
            self.props[prop] = valu

    def pack(self, dorepr=False):
        '''
        Return the serializable/packed version of the node.

        Returns:
            (tuple): An (iden, info) node tuple.
        '''
        node = (self.ndef, {
            'iden': self.iden(),
            'tags': self.tags,
            'props': self.props,
        })

        if dorepr:
            node[1]['repr'] = self.repr()
            node[1]['reprs'] = self.reprs()

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

        for name, valu in self.props.items():

            pobj = self.form.props.get(name)

            if isinstance(pobj.type, s_types.Ndef):
                retn.append((name, valu))
                continue

            if self.snap.model.forms.get(pobj.type.name) is None:
                continue

            ndef = (pobj.type.name, valu)
            if ndef == self.ndef:
                continue

            retn.append((name, ndef))

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
        with s_editatom.EditAtom(self.snap.core.bldgbuids) as editatom:
            retn = await self._setops(name, valu, editatom, init)
            if not retn:
                return False
            await editatom.commit(self.snap)
            return True

    async def _setops(self, name, valu, editatom, init=False):
        '''
        Generate operations to set a property on a node.
        '''
        prop = self.form.prop(name)
        if prop is None:

            if self.snap.strict:
                raise s_exc.NoSuchProp(name=name)

            await self.snap.warn(f'NoSuchProp: name={name}')
            return False

        if self.isrunt:
            if prop.info.get('ro'):
                raise s_exc.IsRuntForm(mesg='Cannot set read-only props on runt nodes',
                                       form=self.form.full, prop=name, valu=valu)
            return await self.snap.core.runRuntPropSet(self, prop, valu)

        curv = self.props.get(name)

        # normalize the property value...
        try:
            norm, info = prop.type.norm(valu)

        except Exception as e:
            mesg = f'Bad property value: {prop.full}={valu!r}'
            return await self.snap._raiseOnStrict(s_exc.BadPropValu, mesg, name=prop.name, valu=valu, emesg=str(e))

        # do we already have the value?
        if curv == norm:
            return False

        if curv is not None and not init:

            if prop.info.get('ro'):

                if self.snap.strict:
                    raise s_exc.ReadOnlyProp(name=prop.full)

                # not setting a set-once prop unless we are init...
                await self.snap.warn(f'ReadOnlyProp: name={prop.full}')
                return False

            # check for type specific merging...
            norm = prop.type.merge(curv, norm)
            if curv == norm:
                return False

        sops = prop.getSetOps(self.buid, norm)

        editatom.sops.extend(sops)

        # self.props[prop.name] = norm
        editatom.npvs.append((self, prop, curv, norm))

        # do we have any auto nodes to add?
        auto = self.snap.model.form(prop.type.name)
        if auto is not None:
            buid = s_common.buid((auto.name, norm))
            await self.snap._addNodeFnibOps((auto, norm, info, buid), editatom)

        # does the type think we have special auto nodes to add?
        # ( used only for adds which do not meet the above block )
        for autoname, autovalu in info.get('adds', ()):
            auto = self.snap.model.form(autoname)
            autonorm, autoinfo = auto.type.norm(autovalu)
            buid = s_common.buid((auto.name, autonorm))
            await self.snap._addNodeFnibOps((auto, autovalu, autoinfo, buid), editatom)

        # do we need to set any sub props?
        subs = info.get('subs')
        if subs is not None:

            for subname, subvalu in subs.items():

                full = prop.name + ':' + subname

                subprop = self.form.prop(full)
                if subprop is None:
                    continue

                await self._setops(full, subvalu, editatom, init=init)

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
                raise s_exc.NoSuchProp(name=name)
            await self.snap.warn(f'No Such Property: {name}')
            return False

        if self.isrunt:
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

        sops = prop.getDelOps(self.buid)
        splice = self.snap.splice('prop:del', ndef=self.ndef, prop=prop.name, valu=curv)
        await self.snap.stor(sops, [splice])

        await prop.wasDel(self, curv)

    def repr(self, name=None):

        if name is None:
            return self.form.type.repr(self.ndef[1])

        valu = self.props.get(name)
        return self.form.props[name].type.repr(valu)

    def reprs(self):

        reps = {}

        for name, valu in self.props.items():

            try:
                rval = self.form.props[name].type.repr(valu)
                if rval is None:
                    continue
            except KeyError:
                rval = repr(valu)

            reps[name] = rval

        return reps

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
        for size, tag, valu in sorted([(len(t), t, v) for (t, v) in self.tags.items()], reverse=True):

            look = tag + '.'
            if any([r.startswith(look) for (r, rv) in retn]):
                continue

            retn.append((tag, valu))

        return retn

    async def addTag(self, tag, valu=(None, None)):

        if self.isrunt:
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
            valu = self.snap.model.type('ival').norm(valu)[0]

        curv = self.tags.get(name)
        if curv == valu:
            return

        elif curv is None:

            tags = s_chop.tags(name)
            for tag in tags[:-1]:

                if self.tags.get(tag) is not None:
                    continue

                await self._addTagRaw(tag, (None, None))

            await self._addTagRaw(tags[-1], valu)
            return

        # merge values into one interval
        valu = s_time.ival(*valu, *curv)

        indx = self.snap.model.types['ival'].indx(valu)
        info = {'univ': True}
        await self._setTagProp(name, valu, indx, info)

    async def _setTagProp(self, name, norm, indx, info):
        self.tags[name] = norm
        splice = self.snap.splice('tag:add', ndef=self.ndef, tag=name, valu=norm)
        self.proplayr['#' + name] = self.snap.wlyr
        await self.snap.stor((('prop:set', (self.buid, self.form.name, '#' + name, norm, indx, info)),), [splice])

    async def _addTagRaw(self, name, norm):

        # these are cached based on norm...
        await self.snap.addTagNode(name)

        info = {'univ': True}
        if norm == (None, None):
            indx = b'\x00'
        else:
            indx = self.snap.model.types['ival'].indx(norm)

        await self._setTagProp(name, norm, indx, info)

        await self.snap.core.runTagAdd(self, name, norm)

        return True

    async def delTag(self, tag, init=False):
        '''
        Delete a tag from the node.
        '''
        path = s_chop.tagpath(tag)

        name = '.'.join(path)

        if self.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot delete tags from runt nodes.',
                                   form=self.form.full, tag=tag)

        curv = self.tags.pop(name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        pref = name + '.'

        subtags = [(len(t), t) for t in self.tags.keys() if t.startswith(pref)]
        subtags.sort(reverse=True)

        removed = []

        for sublen, subtag in subtags:
            valu = self.tags.pop(subtag, None)
            removed.append((subtag, valu))

        removed.append((name, curv))

        info = {'univ': True}
        sops = [('prop:del', (self.buid, self.form.name, '#' + t, info)) for (t, v) in removed]

        # fire all the splices
        splices = [self.snap.splice('tag:del', ndef=self.ndef, tag=t, valu=v) for (t, v) in removed]
        await self.snap.stor(sops, splices)

        # fire all the handlers / triggers
        [await self.snap.core.runTagDel(self, t, v) for (t, v) in removed]

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

        if self.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot delete runt nodes',
                                   form=formname, valu=formvalu)

        tags = [(len(t), t) for t in self.tags.keys()]

        # check for tag permissions
        # TODO

        # check for any nodes which reference us...
        if not force:

            # refuse to delete tag nodes with existing tags
            if self.form.name == 'syn:tag':

                async for _ in self.snap._getNodesByTag(self.ndef[1]):  # NOQA
                    mesg = 'Nodes still have this tag.'
                    return await self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname)

            async for refr in self.snap._getNodesByType(formname, formvalu, addform=False):

                if refr.buid == self.buid:
                    continue

                mesg = 'Other nodes still refer to this node.'
                return await self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname)

        for size, tag in sorted(tags, reverse=True):
            await self.delTag(tag, init=True)

        for name in list(self.props.keys()):
            await self.pop(name, init=True)

        sops = self.form.getDelOps(self.buid)

        splice = self.snap.splice('node:del', ndef=self.ndef)
        await self.snap.stor(sops, [splice])

        self.snap.livenodes.pop(self.buid)
        self.snap.core.pokeFormCount(formname, -1)

        await self.form.wasDeleted(self)

class Path:
    '''
    A path context tracked through the storm runtime.
    '''
    def __init__(self, runt, vars, nodes):

        self.node = None
        self.runt = runt
        self.snap = runt.snap
        self.nodes = nodes

        if len(nodes):
            self.node = nodes[-1]

        self.vars = vars
        self.ctors = {}

        self.vars.update({
            'node': self.node,
        })

        self.metadata = {}

    def getVar(self, name, defv=s_common.novalu):

        valu = self.vars.get(name, s_common.novalu)
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

        return Path(self.runt, dict(self.vars), nodes)

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
        leaf (bool): If True, only return the full tags.

    Returns:
        list: A list of tag strings.
    '''
    fulltags = [tag for tag in pode[1]['tags']]
    if not leaf:
        return fulltags

    # longest first
    retn = []

    # brute force rather than build a tree.  faster in small sets.
    for size, tag in sorted([(len(t), t) for t in fulltags], reverse=True):
        look = tag + '.'
        if any([r.startswith(look) for r in retn]):
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
