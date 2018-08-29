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

        #self.vars = {}  # runtime storm variables
        # self.runt = {}  # a runtime info dict for things like storm

        # self.buid may be None during
        # initial node construction...
        if rawprops is not None:
            self._loadNodeData(rawprops)

        if self.ndef is not None:
            self.form = self.snap.model.form(self.ndef[0])

    def storm(self, text, opts=None, user=None):
        query = self.snap.core.getStormQuery(text)
        with self.snap.getStormRuntime(opts=opts, user=user) as runt:
            runt.addInput(self)
            yield from runt.iterStormQuery(query)

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

    def seen(self, tick, source=None):
        '''
        Update the .seen interval and optionally a source specific seen node.
        '''
        self.set('.seen', tick)

        if source is not None:
            seen = self.snap.addNode('seen', (source, self.ndef))
            seen.set('.seen', tick)

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

    def set(self, name, valu, init=False):
        '''
        Set a property on the node.

        Args:
            name (str): The name of the property.
            valu (obj): The value of the property.
            init (bool): Set to True to force initialization.

        Returns:
            (bool): True if the property was changed.
        '''
        prop = self.form.prop(name)
        if prop is None:

            if self.snap.strict:
                raise s_exc.NoSuchProp(name=name)

            self.snap.warn(f'NoSuchProp: name={name}')
            return False

        curv = self.props.get(name)

        # normalize the property value...
        try:

            norm, info = prop.type.norm(valu)

        except Exception as e:
            mesg = f'Bad property value: {prop.full}={valu!r}'
            return self.snap._raiseOnStrict(s_exc.BadPropValu, mesg, valu=valu, emesg=str(e))

        # do we already have the value?
        if curv == norm:
            return False

        if curv is not None and not init:

            if prop.info.get('ro'):

                if self.snap.strict:
                    raise s_exc.ReadOnlyProp(name=prop.full)

                # not setting a set-once prop unless we are init...
                self.snap.warn(f'ReadOnlyProp: name={prop.full}')
                return False

            # check for type specific merging...
            norm = prop.type.merge(curv, norm)
            if curv == norm:
                return False

        sops = prop.getSetOps(self.buid, norm)

        self.snap.stor(sops)
        self.snap.splice('prop:set', ndef=self.ndef, prop=prop.name, valu=norm, oldv=curv)

        self.props[prop.name] = norm

        # do we have any auto nodes to add?
        auto = self.snap.model.form(prop.type.name)
        if auto is not None:
            buid = s_common.buid((auto.name, norm))
            self.snap._addNodeFnib((auto, norm, info, buid))

        # does the type think we have special auto nodes to add?
        # ( used only for adds which do not meet the above block )
        for autoname, autovalu in info.get('adds', ()):
            auto = self.snap.model.form(autoname)
            autonorm, autoinfo = auto.type.norm(autovalu)
            buid = s_common.buid((auto.name, autonorm))
            self.snap._addNodeFnib((auto, autovalu, autoinfo, buid))

        # do we need to set any sub props?
        subs = info.get('subs')
        if subs is not None:

            for subname, subvalu in subs.items():

                full = prop.name + ':' + subname

                subprop = self.form.prop(full)
                if subprop is None:
                    continue

                self.set(full, subvalu, init=init)

        # last but not least, if we are *not* in init
        # we need to fire a Prop.onset() callback.
        if not self.init:
            prop.wasSet(self, curv)
            if prop.univ:
                univ = self.snap.model.prop(prop.univ)
                univ.wasSet(self, curv)

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
                return self.tags.get(name)
            return self.props.get(name)

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

        node = self.snap.getNodeByNdef((form.name, valu))
        return node.get(text)

    def pop(self, name, init=False):

        prop = self.form.prop(name)
        if prop is None:
            self.warn(f'No Such Property: {name}')
            return False

        if not init:

            if prop.info.get('ro'):
                self.warn(f'Property is read-only: {name}')
                return False

        curv = self.props.pop(name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        sops = prop.getDelOps(self.buid)
        self.snap.stor(sops)

        self.snap.splice('prop:del', ndef=self.ndef, prop=prop.name, valu=curv)

        prop.wasDel(self, curv)

    def repr(self, name=None):

        if name is None:
            return self.form.type.repr(self.ndef[1])

        valu = self.props.get(name)
        return self.form.props[name].type.repr(valu)

    def reprs(self):

        reps = {}

        for name, valu in self.props.items():

            rval = self.form.props[name].type.repr(valu)
            if rval is None:
                continue

            reps[name] = rval

        return reps

    def hasTag(self, name):
        name = s_chop.tag(name)
        return name in self.tags

    def getTag(self, name, defval=None):
        name = s_chop.tag(name)
        return self.tags.get(name, defval)

    def addTag(self, tag, valu=(None, None)):

        path = s_chop.tagpath(tag)

        name = '.'.join(path)

        tagnode = self.snap.addTagNode(name)

        # implement tag renames...
        isnow = tagnode.get('isnow')
        if isnow:
            self.snap.warn(f'tag {name} is now {isnow}')
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

                self._addTagRaw(tag, (None, None))

            self._addTagRaw(tags[-1], valu)
            return

        # merge values into one interval
        valu = s_time.ival(*valu, *curv)

        indx = self.snap.model.types['ival'].indx(valu)
        info = {'univ': True}
        self._setTagProp(name, valu, indx, info)

    def _setTagProp(self, name, norm, indx, info):
        self.tags[name] = norm
        self.snap.stor((('prop:set', (self.buid, self.form.name, '#' + name, norm, indx, info)),))

    def _addTagRaw(self, name, norm):

        # these are cached based on norm...
        self.snap.addTagNode(name)

        info = {'univ': True}
        if norm == (None, None):
            indx = b'\x00'
        else:
            indx = self.snap.model.types['ival'].indx(norm)

        self._setTagProp(name, norm, indx, info)

        # TODO: fire an onTagAdd handler...
        self.snap.splice('tag:add', ndef=self.ndef, tag=name, valu=norm)
        self.snap.core.runTagAdd(self, name, norm)

        return True

    def delTag(self, tag, init=False):
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
            self.snap.core.runTagDel(self, subtag, valu)
            sops.append(('prop:del', (self.buid, self.form.name, '#' + subtag, info)))

        self.snap.core.runTagDel(self, name, curv)
        sops.append(('prop:del', (self.buid, self.form.name, '#' + name, info)))

        self.snap.stor(sops)
        self.snap.splice('tag:del', ndef=self.ndef, tag=name, valu=curv)

    def delete(self, force=False):
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
        for size, tag in tags:
            tagpath = s_chop.tagpath(tag)

        # check for any nodes which reference us...
        if not force:

            if any(self.snap._getNodesByType(formname, formvalu, addform=False)):
                mesg = 'Other nodes still refer to this node.'
                return self.snap._raiseOnStrict(s_exc.CantDelNode, mesg, form=formname)

        for size, tag in sorted(tags, reverse=True):
            self.delTag(tag, init=True)

        for name in list(self.props.keys()):
            self.pop(name, init=True)

        sops = self.form.getDelOps(self.buid)

        self.snap.stor(sops)
        self.snap.splice('node:del', ndef=self.ndef)

        self.snap.buidcache.pop(self.buid)

        self.form.wasDeleted(self)

class Path:
    '''
    A path context tracked through the storm runtime.
    '''
    def __init__(self, runt, vars, nodes):

        self.runt = runt
        self.nodes = nodes

        self.vars = vars
        self.metadata = {}

    def get(self, name, defv=s_common.novalu):
        return self.vars.get(name, defv)

    def set(self, name, valu):
        self.vars[name] = valu

    def meta(self, name, valu):
        '''
        Add node specific metadata to be returned with the node.
        '''
        self.metadata[name] = valu

    def pack(self):
        return dict(self.metadata)

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
        The prop argument may be the full property name (foo:bar:baz), relative property name (:baz) , or the unadorned property name (baz).

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
