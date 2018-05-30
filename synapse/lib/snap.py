import logging
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.chop as s_chop
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.eventbus as s_eventbus

logger = logging.getLogger(__name__)


class Snap(s_eventbus.EventBus):
    '''
    A "snapshot" is a transaction across multiple Cortex layers.

    The Snap object contains the bulk of the Cortex API to
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
        self.strict = True
        self.elevated = False

        self.permcache = s_cache.FixedCache({}, size=1000)

        self.core = core
        self.model = core.model
        self.layers = layers

        self.bulk = False
        self.bulksops = []

        # variables used by the storm runtime
        self.vars = {}

        self.runt = {}
        self.splices = []

        self.debug = False      # Set to true to enable debug output.
        self.write = write      # True when the snap has a write lock on a layer.

        self.xacts = []

        # do the last (possibly write) first for locking
        self.xact = layers[-1].xact(write=write)

        for layr in layers[:-1]:
            self.xacts.append(layr.xact())

        self.xacts.append(self.xact)

        self.tagcache = s_cache.FixedCache(self._addTagNode, size=10000)
        self.buidcache = s_cache.FixedCache(self._getNodeByBuid, size=100000)

        self.onfini(self.stack.close)
        self.changelog = []

        def fini():

            if self.exitok:

                if self.write and self.splices:
                    self.xact.save(self.splices)

                for x in self.xacts:
                    try:
                        x.commit()
                    except Exception as e:
                        logger.exception('commit error for layer xact')

            else:

                for x in self.xacts:
                    try:
                        x.abort()
                    except Exception as e:
                        logger.exception('abort error for layer xact')

        self.onfini(fini)

    def setOffset(self, iden, offs):
        return self.xact.setOffset(iden, offs)

    def getOffset(self, iden, offs):
        return self.xact.getOffset(iden, offs)

    def setUser(self, user):

        self.user = user
        self.permcache.clear()
        self.permcache.callback = {}

        if self.user is not None:
            self.permcache.callback = self.user.allowed

    def allowed(self, *args):
        # a user will be set by auth subsystem if enabled
        if self.user is None:
            return True

        else:
            # TODO elevated()
            return self.permcache.get(args)

    def printf(self, mesg):
        self.fire('print', mesg=mesg)

    def warn(self, mesg, **info):
        logger.warning(mesg)
        self.fire('warn', mesg=mesg, **info)

    def getNodeByBuid(self, buid):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            ((str,dict)): The node tuple or None.

        '''
        return self.buidcache.get(buid)

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
        if self.debug:
            self.printf(f'get nodes by: {full} {cmpr} {valu!r}')

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
        with self.bulkload():

            try:

                fnib = self._getNodeFnib(name, valu)
                return self._addNodeFnib(fnib, props=props)

            except Exception as e:

                mesg = f'{name} {valu!r} {props!r}'
                logger.exception(mesg)
                if self.strict:
                    raise

                return None

    def addFeedData(self, name, items, seqn=None):

        func = self.core.getFeedFunc(name)
        if func is None:
            raise s_exc.NoSuchName(name=name)

        logger.warning(f'adding feed data ({name}): {len(items)} {seqn!r}')

        func(self, items)

        if seqn is not None:

            iden, offs = seqn

            nextoff = offs + len(items)

            self.setOffset(iden, nextoff)

            return nextoff

    def addTagNode(self, name):
        '''
        Ensure that the given syn:tag node exists.
        '''
        self.tagcache.get(name)

    def _addTagNode(self, name):
        self.addNode('syn:tag', name)
        return True

    def _addNodeFnib(self, fnib, props=None):

        # add a node via (form, norm, info, buid)

        form, norm, info, buid = fnib

        if props is None:
            props = {}

        sops = []

        node = self.getNodeByBuid(buid)
        if node is not None:

            # maybe set some props...
            for name, valu in props.items():
                # TODO: node.merge(name, valu)
                node.set(name, valu)

            return node

        # time for the perms check...
        if not self.allowed('node:add', form.name):

            if self.strict:
                mesg = 'Not allowed to add the node.'
                raise s_exc.AuthDeny(mesg=mesg, form=form.name)

        # lets build a node...
        node = s_node.Node(self, None)

        node.init = True    # the node is initializing
        node.buid = buid
        node.form = form
        node.ndef = (form.name, norm)

        sops = form.getSetOps(buid, norm)
        self.stor(sops)

        self.splice('node:add', ndef=node.ndef)

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
        node.set('.created', tick, init=True)

        # we are done initializing.
        node.init = False

        form.wasAdded(node)

        # now we must fire all his prop sets
        for name, valu in tuple(node.props.items()):
            prop = node.form.props.get(name)
            prop.wasSet(node, None)

        return node

    def splice(self, name, **info):
        '''
        Construct and log a splice record to be saved on commit().
        '''
        user = '?'
        if self.user is not None:
            user = self.user.name

        info['user'] = user
        info['time'] = s_common.now()

        self.fire(name, **info)

        mesg = (name, info)
        self.splices.append(mesg)

        return (name, info)

    #########################################################################

    def _getNodeFnib(self, name, valu):
        # return a form, norm, info, buid tuple
        form = self.model.form(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        try:
            norm, info = form.type.norm(valu)
        except Exception as e:
            raise s_exc.BadPropValu(prop=form.name, valu=valu)

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
        with self.bulkload():

            for (formname, formvalu), forminfo in nodedefs:

                props = forminfo.get('props')

                # remove any universal created props...
                if props is not None:
                    props.pop('.created', None)

                node = self.addNode(formname, formvalu, props=props)
                if node is not None:
                    tags = forminfo.get('tags')
                    if tags is not None:
                        for tag, asof in tags.items():
                            node.addTag(tag, valu=asof)

                yield node

    def stor(self, sops):

        if not self.write:
            # jump up to a write xact
            raise s_exc.ReadOnlySnap()

        if self.bulk:
            self.bulksops.extend(sops)
            return

        self.xact.stor(sops)

    @contextlib.contextmanager
    def bulkload(self):

        yield None

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
        for xact in self.xacts:
            yield from xact.getLiftRows(lops)

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
        props = []
        [props.extend(x.getBuidProps(buid)) for x in self.xacts]
        return props

    def _getNodeByBuid(self, buid):
        node = s_node.Node(self, buid)
        if node.ndef is None:
            return None

        return node
