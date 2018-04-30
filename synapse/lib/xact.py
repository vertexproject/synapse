import logging
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.node as s_node
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

class Xact(s_eventbus.EventBus):
    '''
    A Transaction across multiple Cortex layers.

    The Xact object contains the bulk of the Cortex API to
    facilitate performance through careful use of transaction
    boundaries.
    '''

    def __init__(self, core, layers, write=False):

        s_eventbus.EventBus.__init__(self)

        self.tick = s_common.now()
        self.stack = contextlib.ExitStack()

        self.core = core
        self.model = core.model

        self.write = write

        self.xacts = []

        # do the last (possibly write) first for locking
        self.layr = layers[-1]
        self.xact = self.layr.xact(write=write)

        self.stack.enter_context(self.xact)

        for layr in layers[:-1]:
            xact = layr.lenv.xact()
            self.stack.enter_context(xact)
            self.xacts.append((layr, xact))

        self.xacts.append((self.layr, self.xact))

        # no locks needed, so avoid synapse.lib.cache.FixedCache
        self.nodefifo = collections.deque()
        self.nodesbyndef = {}
        self.nodesbybuid = {}

        self.buidcurs = self.cursors('bybuid')
        [self.stack.enter_context(c) for c in self.buidcurs]

        self.onfini(self.stack.close)
        self.changelog = []

    def deltas(self):
        retn = self.changelog
        self.changelog = []

    def _addNodeCache(self, node):

        self.nodesbybuid[node.buid] = node
        self.nodesbyndef[node.ndef] = node

        self.nodefifo.append(node)

        # transaction cache at 10k for now...
        while len(self.nodefifo) > 10000:
            node = self.nodefifo.popleft()
            self.nodesbybuid.pop(node.buid, None)
            self.nodesbyndef.pop(node.ndef, None)

    def getNodeByBuid(self, buid):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            ((str,dict)): The node tuple or None.

        '''
        node = self.nodesbybuid.get(buid)
        if node is None:
            node = self._getNodeByBuid(buid)

        return node

    def getNodeByNdef(self, ndef):
        '''
        Return a single Node by (form,valu) tuple.

        Args:
            ndef ((str,obj)): A (form,valu) ndef tuple.

        Returns:
            (synapse.lib.node.Node): The Node or None.
        '''
        node = self.nodesbyndef.get(ndef)
        if node is None:
            buid = s_common.buid(ndef)
            node = self._getNodeByBuid(buid)

        return node

    def cursor(self, name):
        db = self.layr.db(name)
        return self.xact.cursor(db=db)

    def cursors(self, name):
        return [xact.cursor(db=layr.db(name)) for (layr, xact) in self.xacts]

    def getNodesBy(self, full, valu=None, cmpr='='):
        '''
        The main function for retrieving nodes by prop.

        Args:
            full (str): The full property name.
            valu (obj): A lift compatible value for the type.
            cmpr (str): An optional alternate comparator.

        Yields:
            (synapse.lib.node.Node): Node instances.
        '''
        prop = self.model.prop(full)
        if prop is None:
            raise s_exc.NoSuchProp(name=full)

        if valu is None:

            lops = (
                ('prop', {
                    'prop': prop.utf8name,
                    'form': prop.form.utf8name,
                }),
            )

            for row, node in self.lift(lops):
                yield node

            return

        for row, node in prop.lift(self, valu, cmpr=cmpr):
            yield node

    def addNode(self, name, valu, props=None):
        '''
        Add a node by form name and value with optional props.

        Args:
            name (str): The form of node to add.
            valu (obj): The value for the node.
            props (dict): Optional secondary properties for the node.
        '''
        fnib = self._getNodeFnib(name, valu)
        return self._addNodeFnib(fnib, props=props)

    def pend(self, name, **info):
        evnt = (name, info)
        self.tofire.append(evnt)

    def _addNodeFnib(self, fnib, props=None):

        # add a node via (form, norm, info, buid)

        form, norm, info, buid = fnib

        if props is None:
            props = {}

        # store an original copy of the props for the splice.
        orig = props.copy()

        sops = []

        init = False
        node = self.getNodeByBuid(buid)

        if node is not None:

            # maybe set some props...
            for name, valu in props.items():
                node.set(name, valu)

            return node

        # lets build a node...
        node = s_node.Node(self, None)

        node.init = True    # the node is initializing
        node.buid = buid
        node.form = form
        node.ndef = (form.name, norm)

        sops = form.stor(buid, norm)
        self.stor(sops)

        self._addNodeCache(node)

        # update props with any subs from form value
        subs = info.get('subs')
        if subs is not None:
            for name, valu in subs.items():
                if form.prop(name) is not None:
                    props[name] = valu

        # update props with any defvals we are missing
        for name, valu in form.defvals.items():
            props.setdefault(name, valu)

        # set all the properties with init=True
        for name, valu in props.items():
            node.set(name, valu)

        # we are done initializing.
        node.init = False

        form.wasAdded(node)

        return node

    #########################################################################
    # splice action handlers
    def _actNodeAdd(self, mesg):

        name = mesg[1].get('form')
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')

        form, norm, info, buid = self._getNodeFnib(name, valu)

        if props is None:
            props = {}

        self.addNode(formname, formvalu, props=props)

    def _actNodeSet(self, mesg):

        name = mesg[1].get('form')
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')

        form, norm, info, buid = self._getNodeFnib(name, valu)

        node = self.getNodeByBuid(buid)
        if node is None:
            return

        if props is None:
            return

        for name, valu in props.items():
            node.set(name, valu)

    def _actNodeDel(self, mesg):

        name = mesg[1].get('form')
        valu = mesg[1].get('valu')

        form, norm, info, buid = self._getNodeFnib(name, valu)

        node = self.getNodeByBuid(buid)
        self.delNode(node)

    def _actNodeTagAdd(self, mesg):

        tag = mesg[1].get('tag')
        name = mesg[1].get('form')
        valu = mesg[1].get('valu')

        form, norm, info, buid = self._getNodeFnib(name, valu)

        node = self.getNodeByBuid(buid)
        if node is None:
            return

        node.addTag(tag)

    def _actNodeTagDel(self, mesg):

        tag = mesg[1].get('tag')
        name = mesg[1].get('form')
        valu = mesg[1].get('valu')

        form, norm, info, buid = self._getNodeFnib(name, valu)

        node = self.getNodeByBuid(buid)
        if node is None:
            return

        node.delTag(tag)

    #########################################################################

    def _getNodeFnib(self, name, valu):
        # return a form, norm, info, buid tuple
        form = self.model.form(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        norm, info = form.type.norm(valu)
        buid = s_common.buid((form.name, norm))
        return form, norm, info, buid

    #def delNode(self, node):
        #pass

    def addNodes(self, nodedefs):

        for (formname, formvalu), forminfo in nodedefs:

            props = forminfo.get('props')
            node = self.addNode(formname, formvalu, props=props)

            tags = forminfo.get('tags')
            nodetags = node[1].get('tags')

            if tags is not None:
                for tag, asof in tags.items():
                    xact.addNodeTag(node, tag)

        return xact.deltas()

    def lift(self, lops):
        genr = self.rows(lops)
        return self.join(genr)

    def stor(self, sops):
        if not self.write:
            raise XactReadOnly()
        self.layr._xactRunStors(self.xact, sops)

    def rows(self, lops):
        '''
        Yield row tuples from a series of lift operations.

        Row tuples only requirement is that the first element
        be the binary id of a node.

        Args:
            lops (list): A list of lift operations.

        Yields:
            (tuple): (buid, ...) rows.
        '''
        for layr, xact in self.xacts:
            for row in layr._xactRunLifts(xact, lops):
                yield row

    def join(self, rows):
        '''
        Join a row generator into (row, Node()) tuples.

        A row generator yields tuple rows where the first
        valu is the buid of a node.

        Args:
            rows (iterable): A generator if (buid, ...) tuples.

        Yields:
            (tuple): (row, node)
        '''
        for row in rows:
            node = self.getNodeByBuid(row[0])
            yield row, node

    def _getBuidProps(self, buid):

        for curs in self.buidcurs:

            if curs.set_range(buid):

                for lkey, lval in curs.iternext():

                    if lkey[:32] != buid:
                        break

                    prop = lkey[32:].decode('utf8')
                    valu, indx = s_msgpack.un(lval)

                    yield prop, valu

    def _getNodeByBuid(self, buid):

        node = s_node.Node(self, buid)
        if node.ndef is None:
            return None

        self._addNodeCache(node)
        return node
