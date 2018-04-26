import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.common as s_common

class Node:
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    def __init__(self, xact, buid):

        self.xact = xact

        self.buid = buid
        self.init = False   # True if the node is being added.

        # if set, the node is complete.
        self.ndef = None
        self.form = None

        self.tags = {}
        self.props = {}

        # self.buid may be None during
        # initial node construction...
        if self.buid is not None:
            self._loadNodeData()

        if self.ndef is not None:
            self.form = self.xact.model.form(self.ndef[0])

    def _loadNodeData(self):

        props = list(self.xact._getBuidProps(self.buid))

        for prop, valu in props:

            # check for primary property
            if prop[0] == '*':
                self.ndef = (prop[1:], valu)
                continue

            # check for tag encoding
            if prop[0] == '#':
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
        return (iden, {
            'ndef': self.ndef,
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
            self.xact.warn('NoSuchProp', form=self.form.name, prop=name)
            return False

        if prop.info.get('ro') and not init and not self.init:
            logger.warning('trying to set read only prop: %s' % (prop.full,))
            return False

        # normalize the property value...
        norm, info = prop.type.norm(valu)

        # do we already have the value?
        curv = self.props.get(name)
        if curv == norm:
            return False

        sops = prop.stor(self.buid, norm)
        self.xact.stor(sops)

        self.props[prop.name] = norm

        # do we have any auto nodes to add?
        auto = self.xact.model.form(prop.type.name)
        if auto is not None:
            buid = s_common.buid((auto.name, norm))
            self.xact._addNodeFnib((auto, norm, info, buid))

        # do we need to set any sub props?
        subs = info.get('subs')
        if subs is not None:

            for subname, subvalu in subs.items():

                full = prop.name + ':' + name

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
        return self.props.get(name)

    def addTag(self, tag):
        '''
        Add a tag to the Node.

        Args:
            tag (str): A tag str with no leading #.

        Returns:
            (bool): True if the tag was newly added.
        '''
        if self.tags.get(tag) is not None:
            return False

        tick = s_common.now()

        #FIXME: join tags down...
        sops = (
            ('node:tag:add', {
                'buid': self.buid,
                'form': self.form.utf8name,
                'tag': tag.encode('utf8'),
            }),
        )
        self.xact.stor(sops)

    def delTag(self, tag):
        '''
        Delete a tag from the node.
        '''
        valu = self.tags.get(tag)
        if valu is None:
            return False

        #TODO: remove the tag
