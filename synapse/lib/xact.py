import logging
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.chop as s_chop
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

class Xact(s_eventbus.EventBus):
    '''
    A Transaction across multiple Cortex layers.

    The Xact object contains the bulk of the Cortex API to
    facilitate performance through careful use of transaction
    boundaries.

    Transactions produce the following EventBus events:

    (...any splice...)
    ('log', {'level': 'mesg': })
    ('print', {}),
    '''

    def __init__(self, core, layers, write=False):

        s_eventbus.EventBus.__init__(self)

        self.tick = s_common.now()
        self.stack = contextlib.ExitStack()

        self.user = None
        self.core = core
        self.model = core.model
        self.layers = layers

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

        # no locks needed...
        #self.nodefifo = collections.deque()
        #self.nodesbyndef = {}
        #self.nodesbybuid = {}
        self.buidcache = s_cache.FixedCache(self._getNodeByBuid, size=100000)

        self.buidcurs = self.cursors('bybuid')
        [self.stack.enter_context(c) for c in self.buidcurs]

        # keep a cache so bulk is *fast*
        self.permcache = {}

        self.onfini(self.stack.close)
        self.changelog = []

    def allowed(self, *args):

        # a user will be set by auth subsystem if enabled
        if self.user is None:
            return True

        valu = self.permcache.get(args)
        if valu is not None:
            return valu

        perm = args

        # expand tag perms...
        if args[0] in ('node:tag:add', 'node:tag:del'):
            perm = (perm[0],) + tuple(perm[1].split('.'))

        valu = self.user.allowed(perm)
        self.permcache[args] = valu
        return valu

    def printf(self, mesg):
        self.fire('print', mesg=mesg)

    def log(self, mesg, level='WARNING'):
        self.fire('log', mesg=mesg, level=level)

    def deltas(self):
        retn = self.changelog
        self.changelog = []

    def getNodeByBuid(self, buid):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            ((str,dict)): The node tuple or None.

        '''
        node = self.buidcache.get(buid)
        if node is not s_common.novalu:
            return node

    def getNodeByNdef(self, ndef):
        '''
        Return a single Node by (form,valu) tuple.

        Args:
            ndef ((str,obj)): A (form,valu) ndef tuple.

        Returns:
            (synapse.lib.node.Node): The Node or None.
        '''
        buid = s_common.buid(ndef)
        return self.getNodeByBuid(buid)

    def cursor(self, name):
        db = self.layr.db(name)
        return self.xact.cursor(db=db)

    def cursors(self, name):
        return [xact.cursor(db=layr.db(name)) for (layr, xact) in self.xacts]

    def _getNodesByTag(self, name, valu=None, cmpr='='):

        # TODO interval indexing for valu... and @=
        name = s_chop.tag(name)
        pref = b'#' + name.encode('utf8') + b'\x00'

        iops = (('pref', b''), )
        lops = (
            ('indx', ('byuniv', pref, iops)),
        )

        for row, node in self.getLiftNodes(lops):
            yield node

    def _getNodesByFormTag(self, name, tag, valu=None, cmpr='='):

        form = self.model.form(name)
        if form is None:
            raise s_exc.NoSuchForm(form=name)

        # TODO interval indexing for valu... and @=

        tag = s_chop.tag(tag)

        # maybe use Encoder here?
        fenc = form.name.encode('utf8') + b'\x00'
        tenc = b'#' + tag.encode('utf8') + b'\x00'

        pref = fenc + tenc

        iops = (('pref', b''), )

        lops = (
            ('indx', ('byprop', fenc + tenc, iops)),
        )

        for row, node in self.getLiftNodes(lops):
            yield node

    def getNodesBy(self, full, valu=None, cmpr='='):
        '''
        The main function for retrieving nodes by prop.

        Args:
            full (str): The property/tag name.
            valu (obj): A lift compatible value for the type.
            cmpr (str): An optional alternate comparator.

        Yields:
            (synapse.lib.node.Node): Node instances.
        '''
        if full.startswith('#'):
            return self._getNodesByTag(full, valu=valu, cmpr=cmpr)

        if full.find('#') != -1:
            form, tag = full.split('#', 1)
            return self._getNodesByFormTag(form, tag, valu=valu, cmpr=cmpr)

        return self._getNodesByProp(full, valu=valu, cmpr=cmpr)

    def _getNodesByProp(self, full, valu=None, cmpr='='):

        prop = self.model.prop(full)
        if prop is None:
            raise s_exc.NoSuchProp(name=full)

        lops = prop.getLiftOps(valu, cmpr=cmpr)
        for row, node in self.getLiftNodes(lops):
            yield node

    def addNode(self, name, valu, props=None):
        '''
        Add a node by form name and value with optional props.

        Args:
            name (str): The form of node to add.
            valu (obj): The value for the node.
            props (dict): Optional secondary properties for the node.
        '''
        try:
            fnib = self._getNodeFnib(name, valu)
            return self._addNodeFnib(fnib, props=props)
        except Exception as e:
            mesg = f'{name} {valu!r} {props!r}'
            logger.exception(mesg)
            raise

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
                #TODO: node.merge(name, valu)
                node.set(name, valu)

            return node

        # lets build a node...
        node = s_node.Node(self, None)

        node.init = True    # the node is initializing
        node.buid = buid
        node.form = form
        node.ndef = (form.name, norm)

        sops = form.getSetOps(buid, norm)

        self.stor(sops)

        self.buidcache.put(buid, node)

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
            node.set(name, valu, init=True)

        # set our global properties
        tick = s_common.now()
        node.set('.created', tick)

        # we are done initializing.
        node.init = False

        form.wasAdded(node)

        return node

    def splice(self, name, **info):

        user = '?'
        if self.user is not None:
            user = self.user.name

        info['user'] = user
        info['time'] = s_common.now()

        return (name, info)

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

    def addNodes(self, nodedefs):
        '''
        Add/merge nodes in bulk.

        The addNodes API is designed for bulk adds which will
        also set properties and add tags to existing nodes.
        Nodes are specified as a list of the following tuples:

            ( (form, valu), {'props':{}, 'tags':{}})

        Args:
            nodedefs (list): A list of nodedef tuples.

        Returns:
            (list): A list of xact messages.
        '''

        for (formname, formvalu), forminfo in nodedefs:

            props = forminfo.get('props')

            # remove any universal created props...
            props.pop('.created', None)

            node = self.addNode(formname, formvalu, props=props)

            tags = forminfo.get('tags')
            if tags is not None:
                for tag, asof in tags.items():
                    node.addTag(tag)

    def stor(self, sops):
        if not self.write:
            raise s_exc.ReadOnlyXact()

        self.layr._xactRunStors(self.xact, sops)

    def getLiftNodes(self, lops):
        genr = self.getLiftRows(lops)
        return self.getRowNodes(genr)

    def getLiftRows(self, lops):
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

    def getRowNodes(self, rows):
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
            return s_common.novalu

        return node
