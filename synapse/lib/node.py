import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop

class Node:
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    def __init__(self, snap, buid):

        self.snap = snap

        self.buid = buid
        self.init = False   # True if the node is being added.

        # if set, the node is complete.
        self.ndef = None
        self.form = None

        self.tags = {}
        self.props = {}
        self.univs = {}

        # self.buid may be None during
        # initial node construction...
        if self.buid is not None:
            self._loadNodeData()

        if self.ndef is not None:
            self.form = self.snap.model.form(self.ndef[0])

    def _loadNodeData(self):

        props = list(self.snap._getBuidProps(self.buid))

        for prop, valu in props:

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

    def pack(self):
        '''
        Return the serializable/packed version of the node.

        Returns:
            (tuple): An (iden, info) node tuple.
        '''
        iden = s_common.ehex(self.buid)
        return (self.ndef, {
            'tags': self.tags,
            'props': self.props,
        })

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
            logger.warning('NoSuchProp: %s (%s)', name, self.form.name)
            return False

        if prop.info.get('ro') and not init and not self.init:
            logger.warning('trying to set read only prop: %s' % (prop.full,))
            return False

        curv = self.props.get(name)
        #if curv is not None and not init and not prop.info.get('rw'):
        if curv is not None and not init and prop.info.get('ro'):
            # not setting a set-once prop unless we are init...
            return False

        # normalize the property value...
        norm, info = prop.type.norm(valu)

        # do we already have the value?
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

    def get(self, name):
        '''
        Return a secondary property value from the Node.

        Args:
            name (str): The name of a secondary property.

        Returns:
            (obj): The secondary property value or None.
        '''
        if name.find('::') != -1:

            name, text = name.split('::', 1)

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

        if name[0] == '#':
            return self.tags.get(name)

        return self.props.get(name)

    def delete(self, name):

        prop = self.form.prop(name)
        if prop is None:
            self.snap.warn('NoSuchProp', form=self.form.name, prop=name)
            return False

        if prop.info.get('ro') and not init and not self.init:
            logger.warning('trying to set read only prop: %s' % (prop.full,))
            return False

        sops = prop.getDelOps(self.buid)
        self.snap.stor(sops)

        curv = self.props.pop(name, None)
        prop.wasDel(self, curv)

    def hasTag(self, name):
        name = s_chop.tag(name)
        return name in self.tags

    def getTag(self, name, defval=None):
        name = s_chop.tag(name)
        return self.tags.get(name, defval)

    def addTag(self, tag, valu=(None, None)):

        name = s_chop.tag(tag)

        if not self.snap.allowed('node:tag:add', name):
            raise s_exc.AuthDeny()

        if valu != (None, None):
            valu = self.snap.model.type('ival').norm(valu)[0]

        curv = self.tags.get(name)
        if curv == valu:
            return

        if curv is not None:
            # merge tag and move along...
            return

        tags = s_chop.tags(name)
        for tag in tags[:-1]:

            if self.tags.get(tag) is not None:
                continue

            self._addTagRaw(tag, (None, None))

        self._addTagRaw(tags[-1], valu)

    def _addTagRaw(self, name, norm):

        # these are cached based on norm...
        self.snap.addTagNode(name)

        info = {'univ': True}
        if norm == (None, None):
            indx = b'\x00'
        else:
            indx = self.snap.model.types['ival'].indx(norm)

        sops = (
            ('prop:set', (self.buid, self.form.name, '#' + name, norm, indx, info)),
        )

        self.tags[name] = norm
        self.snap.stor(sops)

        # TODO: fire an onTagAdd handler...
        self.snap.splice('tag:add', ndef=self.ndef, tag=name, valu=norm)
        return True

    def delTag(self, tag):
        '''
        Delete a tag from the node.
        '''
        name = s_chop.tag(tag)

        if not self.snap.allowed('node:tag:del', name):
            raise s_exc.AuthDeny()

        curv = self.tags.pop(name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        pref = name + '.'

        subtags = [(len(t), t) for t in self.tags.keys() if t.startswith(pref)]
        subtags.sort(reverse=True)

        info = {'univ': True}
        sops = []

        for sublen, subtag in subtags:
            self.tags.pop(subtag, None)
            sops.append(('prop:del', (self.buid, self.form.name, '#' + subtag, info)))

        sops.append(('prop:del', (self.buid, self.form.name, '#' + name, info)))

        self.snap.stor(sops)
        self.snap.splice('tag:add', ndef=self.ndef, tag=name, valu=name)
