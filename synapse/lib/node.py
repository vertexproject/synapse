import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

class Node:
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    def __init__(self, snap, buid=None, rawprops=None):

        self.snap = snap

        self.buid = buid

        self.init = False  # True if the node is being added.

        # if set, the node is complete.
        self.ndef = None
        self.form = None

        self.tags = {}
        self.props = {}
        self.univs = {}

        # self.buid may be None during
        # initial node construction...
        if rawprops is not None:
            self._loadNodeData(rawprops)

        if self.ndef is not None:
            self.form = self.snap.model.form(self.ndef[0])

    def __repr__(self):
        return f'Node{{{self.pack()}}}'

    async def storm(self, text, opts=None, user=None):
        query = self.snap.core.getStormQuery(text)
        with self.snap.getStormRuntime(opts=opts, user=user) as runt:
            runt.addInput(self)
            async for item in runt.iterStormQuery(query):
                yield item

    async def filter(self, text, opts=None, user=None):
        async for item in self.storm(text, opts=opts, user=user):
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
            seen = await self.snap.addNode('seen', (source, self.ndef))
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

    async def _sethelper(self, name, valu, init=False):
        '''
        Shared code between initprop and set

        Returns False if valu is improper or already set, else
        returns Tuple of prop, old valu, new normed valu, type info, storage ops
        '''
        prop = self.form.prop(name)
        if prop is None:

            if self.snap.strict:
                raise s_exc.NoSuchProp(name=name)

            await self.snap.warn(f'NoSuchProp: name={name}')
            return False

        curv = self.props.get(name)

        # normalize the property value...
        try:
            norm, info = prop.type.norm(valu)

        except Exception as e:
            mesg = f'Bad property value: {prop.full}={valu!r}'
            return await self.snap._raiseOnStrict(s_exc.BadPropValu, mesg, valu=valu, emesg=str(e))

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

        return prop, curv, norm, info, sops

    async def initprop(self, name, valu, fnibtxn):
        '''
        Set a property on the node for the first time.

        Args:
            name (str): The name of the property.
            valu (obj): The value of the property.
            init (bool): Set to True to force initialization.

        Returns:
            (bool): True if the property was changed.
        '''
        valu = await self._sethelper(name, valu, init=True)
        if valu is False:
            return False
        prop, curv, norm, info, sops = valu

        fnibtxn.sops.extend(sops)

        self.props[prop.name] = norm

        # do we have any auto nodes to add?
        auto = self.snap.model.form(prop.type.name)
        if auto is not None:
            buid = s_common.buid((auto.name, norm))
            await self.snap.addNodeFnibOps((auto, norm, info, buid), fnibtxn)

        # does the type think we have special auto nodes to add?
        # (used only for adds which do not meet the above block)
        for autoname, autovalu in info.get('adds', ()):
            auto = self.snap.model.form(autoname)
            autonorm, autoinfo = auto.type.norm(autovalu)
            buid = s_common.buid((auto.name, autonorm))
            await self.snap.addNodeFnibOps((auto, autovalu, autoinfo, buid), fnibtxn)

        # do we need to set any sub props?
        subs = info.get('subs')
        if subs is not None:

            for subname, subvalu in subs.items():

                full = prop.name + ':' + subname

                subprop = self.form.prop(full)
                if subprop is None:
                    continue

                await self.initprop(full, subvalu, fnibtxn)

        return True

    # FIXME: refactor with initprop
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
        valu = await self._sethelper(name, valu, init)
        if valu is False:
            return False
        prop, curv, norm, info, sops = valu

        await self.snap.stor(sops)
        await self.snap.splice('prop:set', ndef=self.ndef, prop=prop.name, valu=norm, oldv=curv)

        self.props[prop.name] = norm

        # do we have any auto nodes to add?
        auto = self.snap.model.form(prop.type.name)
        if auto is not None:
            buid = s_common.buid((auto.name, norm))
            await self.snap._addNodeFnib((auto, norm, info, buid))

        # does the type think we have special auto nodes to add?
        # ( used only for adds which do not meet the above block )
        for autoname, autovalu in info.get('adds', ()):
            auto = self.snap.model.form(autoname)
            autonorm, autoinfo = auto.type.norm(autovalu)
            buid = s_common.buid((auto.name, autonorm))
            await self.snap._addNodeFnib((auto, autovalu, autoinfo, buid))

        # do we need to set any sub props?
        subs = info.get('subs')
        if subs is not None:

            for subname, subvalu in subs.items():

                full = prop.name + ':' + subname

                subprop = self.form.prop(full)
                if subprop is None:
                    continue

                await self.set(full, subvalu, init=init)

        await self.snap.notifyPropSet(self, prop, curv)

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
        parts = name.split('::', 1)

        if len(parts) is 1:
            name = parts[0]
            if name.startswith('#'):
                return self.tags.get(name[1:])
            return self.props.get(name)

        # FIXME
        raise Exception('Temporarily disabled implicit pivoting in get')

        name, text = parts
        prop = self.form.props.get(name)
        if prop is None:
            raise s_exc.NoSuchProp(prop=name, form=self.form.name)

        valu = self.props.get(name, s_common.novalu)
        if valu is s_common.novalu:
            return None

        form = self.snap.model.form(prop.type.name)
        if form is None:
            raise s_exc.NoSuchForm(form=prop.type.name)

        # node = await self.snap.getNodeByNdef((form.name, valu))
        # return await node.get(text)

    async def pop(self, name, init=False):

        prop = self.form.prop(name)
        if prop is None:
            if self.snap.strict:
                raise s_exc.NoSuchProp(name=name)
            await self.snap.warn(f'No Such Property: {name}')
            return False

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
        await self.snap.stor(sops)

        await self.snap.splice('prop:del', ndef=self.ndef, prop=prop.name, valu=curv)

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
        await self.snap.stor((('prop:set', (self.buid, self.form.name, '#' + name, norm, indx, info)),))
        await self.snap.splice('tag:add', ndef=self.ndef, tag=name, valu=norm)

    async def _addTagRaw(self, name, norm):

        # these are cached based on norm...
        await self.snap.addTagNode(name)

        info = {'univ': True}
        if norm == (None, None):
            indx = b'\x00'
        else:
            indx = self.snap.model.types['ival'].indx(norm)

        await self._setTagProp(name, norm, indx, info)

        await self.snap.splice('tag:add', ndef=self.ndef, tag=name, valu=norm)
        await self.snap.core.runTagAdd(self, name, norm)
        await self.snap.core.triggers.run(self, 'tag:add', info={'form': self.form.name, 'tag': name})

        return True

    async def delTag(self, tag, init=False):
        '''
        Delete a tag from the node.
        '''
        path = s_chop.tagpath(tag)

        name = '.'.join(path)

        curv = self.tags.pop(name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        pref = name + '.'

        subtags = [(len(t), t) for t in self.tags.keys() if t.startswith(pref)]
        subtags.sort(reverse=True)

        info = {'univ': True}
        sops = []

        for sublen, subtag in subtags:
            valu = self.tags.pop(subtag, None)
            await self.snap.core.runTagDel(self, subtag, valu)
            sops.append(('prop:del', (self.buid, self.form.name, '#' + subtag, info)))

        await self.snap.core.runTagDel(self, name, curv)
        await self.snap.core.triggers.run(self, 'tag:del', info={'form': self.form.name, 'tag': name})
        sops.append(('prop:del', (self.buid, self.form.name, '#' + name, info)))

        await self.snap.stor(sops)
        await self.snap.splice('tag:del', ndef=self.ndef, tag=name, valu=curv)

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

        tags = [(len(t), t) for t in self.tags.keys()]

        # check for tag permissions
        # TODO

        # check for any nodes which reference us...
        if not force:

            # refuse to delete tag nodes with existing tags
            if self.form.name == 'syn:tag':

                async for _ in self.snap._getNodesByTag(self.ndef[1]):
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

        await self.snap.stor(sops)
        await self.snap.splice('node:del', ndef=self.ndef)

        self.snap.buidcache.pop(self.buid)
        self.snap.core.pokeFormCount(formname, -1)

        await self.form.wasDeleted(self)

class Path:
    '''
    A path context tracked through the storm runtime.
    '''
    def __init__(self, runt, vars, nodes):

        self.node = None
        self.runt = runt
        self.nodes = nodes

        if len(nodes):
            self.node = nodes[-1]

        self.vars = vars
        self.ctors = {}

        self.vars.update({
            'node': self.node,
        })

        self.metadata = {}

    def get(self, name, defv=s_common.novalu):

        valu = self.vars.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        ctor = self.ctors.get(name)
        if ctor is not None:
            valu = ctor(self)
            self.vars[name] = valu
            return valu

        return self.runt.getVar(name, defv=defv)

    def set(self, name, valu):
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
    Return a node definition (<form>,<valu> tuple from the node.

    Args:
        node (tuple): A packed node.

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
