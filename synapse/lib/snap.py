import logging
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.datamodel as s_datamodel

import synapse.lib.chop as s_chop
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache

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

        self.stack = contextlib.ExitStack()

        self.user = None
        self.strict = True
        self.elevated = False
        self.canceled = False

        self.permcache = s_cache.FixedCache({}, size=1000)

        self.core = core
        self.model = core.model
        self.layers = layers

        self.bulk = False
        self.bulksops = []

        # variables used by the storm runtime
        self.vars = {}

        self.runt = {}

        self.debug = False      # Set to true to enable debug output.
        self.write = False      # True when the snap has a write lock on a layer.

        self.wtick = None       # Last time we wrote ( used by tick() to commit/release )

        self.xact = None
        self.xacts = [l.xact() for l in layers]

        self.tagcache = s_cache.FixedCache(self._addTagNode, size=10000)
        self.buidcache = s_cache.FixedCache(self._getNodeByBuid, size=100000)

        self.onfini(self.stack.close)
        self.changelog = []
        self.tagtype = core.model.type('ival')

        def fini():

            if self.exitok:

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

    def cancel(self):
        self.canceled = True

    def tick(self):
        '''
        The time-checking tick counter for the snap.

        This should be called frequently while routines do their work
        to ensure write timeouts and maximum snap duration is enforced.

        NOTE: tick() may commit() a current write transaction to release the
              writer lock.  As such, it should only be called at positions where
              model coherence is ensured.
        '''
        if self.canceled:
            raise s_exc.Canceled()

        # TODO give up write lock if wtick is too long ago...

    def writeable(self):
        '''
        Ensure that the snap() is writable and record our write tick.
        '''
        self.wtick = s_common.now()

        if self.write:
            return True

        self.xacts[-1].decref()

        self.xact = self.layers[-1].xact(write=True)

        self.write = True
        self.xacts[-1] = self.xact

    def setOffset(self, iden, offs):
        self.writeable()
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

        return self.user.allowed(args, elev=self.elevated)

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
        self.tick()
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

        if valu is None:
            iops = (('pref', b''), )
        else:
            iops = self.tagtype.getIndxOps(valu, cmpr)

        lops = (
            ('indx', ('byuniv', pref, iops)),
        )

        for row, node in self.getLiftNodes(lops, '#' + name):
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

        if valu is None:
            iops = (('pref', b''), )
        else:
            iops = self.tagtype.getIndxOps(valu, cmpr)

        lops = (
            ('indx', ('byprop', fenc + tenc, iops)),
        )

        for row, node in self.getLiftNodes(lops, '#' + tag):
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

        # special handling for by type (*type=) here...
        if cmpr == '*type=':
            return self._getNodesByType(full, valu=valu)

        if full.startswith('#'):
            return self._getNodesByTag(full, valu=valu, cmpr=cmpr)

        fields = full.split('#', 1)
        if len(fields) > 1:
            form, tag = fields
            return self._getNodesByFormTag(form, tag, valu=valu, cmpr=cmpr)

        return self._getNodesByProp(full, valu=valu, cmpr=cmpr)

    def _getNodesByProp(self, full, valu=None, cmpr='='):

        prop = self.model.prop(full)
        if prop is None:
            raise s_exc.NoSuchProp(name=full)

        lops = prop.getLiftOps(valu, cmpr=cmpr)
        for row, node in self.getLiftNodes(lops, prop.name):
            yield node

    def _getNodesByType(self, name, valu=None, addform=True):

        _type = self.model.types.get(name)
        if _type is None:
            raise s_exc.NoSuchType(name=name)

        if addform:
            form = self.model.forms.get(name)
            if form is not None:
                lops = form.getLiftOps(valu)
                for row, node in self.getLiftNodes(lops, '*' + form.name):
                    yield node

        for prop in self.model.getPropsByType(name):
            lops = prop.getLiftOps(valu)
            for row, node in self.getLiftNodes(lops, prop):
                yield node

    def addNode(self, name, valu, props=None, syst=False):
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
                return self._addNodeFnib(fnib, props=props, syst=syst)

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
        return self.tagcache.get(name)

    def _addTagNode(self, name):
        return self.addNode('syn:tag', name, syst=True)

    def _addNodeFnib(self, fnib, props=None, syst=False):
        '''
        Add a node via (form, norm, info, buid)
        '''
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
        if not syst and not self.allowed('node:add', form.name):
            self._onAuthDeny('Not allowed to add the node.', form=form.name)
            return None

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

    def _onAuthDeny(self, mesg, **info):

        if self.strict:
            raise s_exc.AuthDeny(mesg=mesg, **info)

        self.warn(f'AuthDeny: {mesg} {info!r}')
        return False

    def _raiseOnStrict(self, ctor, mesg, **info):
        self.warn(f'{ctor.__name__}: {mesg} {info!r}')
        if self.strict:
            raise ctor(mesg=mesg, **info)
        return False

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
        self.xact.splices.append(mesg)

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

        self.writeable()

        if self.bulk:
            self.bulksops.extend(sops)
            return

        self.xact.stor(sops)

    @contextlib.contextmanager
    def bulkload(self):

        yield None

    def getLiftNodes(self, lops, rawprop):
        genr = self.getLiftRows(lops)
        return self.getRowNodes(genr, rawprop)

    def getLiftRows(self, lops):
        '''
        Yield row tuples from a series of lift operations.

        Row tuples only requirement is that the first element
        be the binary id of a node.

        Args:
            lops (list): A list of lift operations.

        Yields:
            (tuple): (layer_indx, (buid, ...)) rows.
        '''
        for layer_idx, xact in enumerate(self.xacts):
            with xact.incref():
                yield from ((layer_idx, x) for x in xact.getLiftRows(lops))

    def getRowNodes(self, rows, rawprop):
        '''
        Join a row generator into (row, Node()) tuples.

        A row generator yields tuple rows where the first
        valu is the buid of a node.

        Args:
            rows: A generator of (layer_idx, (buid, ...)) tuples.
            rawprop(str):  "raw" propname i.e. if a tag, starts with "#".  Used for filtering so that we skip the props
                for a buid if we're asking from a higher layer than the row was from (and hence, we'll presumable
                get/have gotten the row when that layer is lifted.
        Yields:
            (tuple): (row, node)
        '''
        for origlayer, row in rows:
            props = {}
            buid = row[0]
            node = self.buidcache.cache.get(buid)
            self.tick()
            # Evaluate layers top-down to more quickly abort if we've found a higher layer with the property set
            for layeridx in range(len(self.xacts) - 1, -1, -1):
                x = self.xacts[layeridx]
                layerprops = x.getBuidProps(buid)
                # We mark this node to drop iff we see the prop set in this layer *and* we're looking at the props
                # from a higher (i.e. closer to write, higher idx) layer.
                if layeridx > origlayer and rawprop in layerprops:
                    props = None
                    break
                if node is None:
                    for k, v in layerprops.items():
                        if k not in props:
                            props[k] = v
            if props is None:
                continue
            if node is None:
                node = s_node.Node(self, buid, props.items())
                if node and node.ndef is not None:
                    self.buidcache.put(buid, node)

            if node.ndef is not None:
                yield row, node

    def _getNodeByBuid(self, buid):
        props = {}
        # this is essentially atomic and doesn't need xact.incref
        for layeridx, x in enumerate(self.xacts):
            layerprops = x.getBuidProps(buid)
            props.update(layerprops)

        node = s_node.Node(self, buid, props.items())
        return None if node.ndef is None else node
