import types
import asyncio
import logging
import weakref
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.coro as s_coro
import synapse.lib.base as s_base
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.storm as s_storm
import synapse.lib.editatom as s_editatom

logger = logging.getLogger(__name__)


class Snap(s_base.Base):
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

    async def __anit__(self, core, layers, user):
        '''
        Args:
            core (cortex):  the cortex
            layers (List[Layer]): the list of layers to access, write layer last
        '''
        await s_base.Base.__anit__(self)

        self.stack = contextlib.ExitStack()

        assert user is not None

        self.strict = True
        self.elevated = False
        self.canceled = False

        self.core = core
        self.user = user
        self.model = core.model

        # it is optimal for a snap to have layers in "bottom up" order
        self.layers = list(reversed(layers))
        self.wlyr = self.layers[-1]

        # variables used by the storm runtime
        self.vars = {}

        self.runt = {}

        self.debug = False      # Set to true to enable debug output.
        self.write = False      # True when the snap has a write lock on a layer.

        self.tagcache = s_cache.FixedCache(self._addTagNode, size=10000)
        self.buidcache = collections.deque(maxlen=100000)  # Keeps alive the most recently accessed node objects
        self.livenodes = weakref.WeakValueDictionary()  # buid -> Node

        self.onfini(self.stack.close)
        self.changelog = []
        self.tagtype = core.model.type('ival')

    @contextlib.contextmanager
    def getStormRuntime(self, opts=None, user=None):
        if user is None:
            user = self.user

        runt = s_storm.Runtime(self, opts=opts, user=user)
        self.core.stormrunts[runt.iden] = runt
        yield runt
        self.core.stormrunts.pop(runt.iden, None)

    async def iterStormPodes(self, text, opts=None, user=None):
        '''
        Yield packed node tuples for the given storm query text.
        '''
        if user is None:
            user = self.user

        dorepr = False
        dopath = False

        self.core._logStormQuery(text, user)

        if opts is not None:
            dorepr = opts.get('repr', False)
            dopath = opts.get('path', False)

        async for node, path in self.storm(text, opts=opts, user=user):
            pode = node.pack(dorepr=dorepr)
            pode[1]['path'] = path.pack(path=dopath)
            yield pode

    @s_coro.genrhelp
    async def storm(self, text, opts=None, user=None):
        '''
        Execute a storm query and yield (Node(), Path()) tuples.
        '''
        if user is None:
            user = self.user

        query = self.core.getStormQuery(text)
        with self.getStormRuntime(opts=opts, user=user) as runt:
            async for x in runt.iterStormQuery(query):
                yield x

    @s_coro.genrhelp
    async def eval(self, text, opts=None, user=None):
        '''
        Run a storm query and yield Node() objects.
        '''
        if user is None:
            user = self.user

        # maintained for backward compatibility
        query = self.core.getStormQuery(text)
        with self.getStormRuntime(opts=opts, user=user) as runt:
            async for node, path in runt.iterStormQuery(query):
                yield node

    async def setOffset(self, iden, offs):
        return await self.wlyr.setOffset(iden, offs)

    async def getOffset(self, iden, offs):
        return await self.wlyr.getOffset(iden, offs)

    async def printf(self, mesg):
        await self.fire('print', mesg=mesg)

    async def warn(self, mesg, **info):
        logger.warning(mesg)
        await self.fire('warn', mesg=mesg, **info)

    async def getNodeByBuid(self, buid):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            Optional[s_node.Node]: The node object or None.

        '''
        node = self.livenodes.get(buid)
        if node is not None:
            return node

        props = {}
        for layr in self.layers:
            layerprops = await layr.getBuidProps(buid)
            props.update(layerprops)

        node = s_node.Node(self, buid, props.items())

        # Give other tasks a chance to run
        await asyncio.sleep(0)

        if node.ndef is None:
            return None

        self.buidcache.append(node)
        self.livenodes[buid] = node
        return node

    async def getNodeByNdef(self, ndef):
        '''
        Return a single Node by (form,valu) tuple.

        Args:
            ndef ((str,obj)): A (form,valu) ndef tuple.  valu must be
            normalized.

        Returns:
            (synapse.lib.node.Node): The Node or None.
        '''
        buid = s_common.buid(ndef)
        return await self.getNodeByBuid(buid)

    async def _getNodesByTag(self, name, valu=None, cmpr='='):
        name = s_chop.tag(name)
        pref = b'#' + name.encode('utf8') + b'\x00'
        cmpf = None

        if valu is None:
            iops = (('pref', b''), )
            lops = (
                ('indx', ('byuniv', pref, iops)),
            )
        elif valu is not None and cmpr == '@=':
            lops = self.tagtype.getLiftOps('univ', cmpr, (None, '#' + name, valu))
        else:
            iops = self.tagtype.getIndxOps(valu, cmpr)
            lops = (
                ('indx', ('byuniv', pref, iops)),
            )

        async for row, node in self.getLiftNodes(lops, '#' + name, cmpr=cmpf):
            yield node

    async def _getNodesByFormTag(self, name, tag, valu=None, cmpr='='):

        filt = None
        form = self.model.form(name)

        if valu is not None:
            ctor = self.model.type('ival').getCmprCtor(cmpr)
            if ctor is not None:
                filt = ctor(valu)

        if form is None:
            raise s_exc.NoSuchForm(form=name)

        tag = s_chop.tag(tag)

        # maybe use Encoder here?
        fenc = form.name.encode('utf8') + b'\x00'
        tenc = b'#' + tag.encode('utf8') + b'\x00'

        iops = (('pref', b''), )
        lops = (
            ('indx', ('byprop', fenc + tenc, iops)),
        )

        # a small speed optimization...
        rawprop = '#' + tag
        if filt is None:

            async for row, node in self.getLiftNodes(lops, rawprop):
                yield node

            return

        async for row, node in self.getLiftNodes(lops, rawprop):

            valu = node.getTag(tag)

            if filt(valu):
                yield node

    async def getNodesBy(self, full, valu=None, cmpr='='):
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
            await self.printf(f'get nodes by: {full} {cmpr} {valu!r}')

        # special handling for by type (*type=) here...
        if cmpr == '*type=':
            async for node in self._getNodesByType(full, valu=valu):
                yield node
            return

        if full.startswith('#'):
            async for node in self._getNodesByTag(full, valu=valu, cmpr=cmpr):
                yield node
            return

        fields = full.split('#', 1)
        if len(fields) > 1:
            form, tag = fields
            async for node in self._getNodesByFormTag(form, tag, valu=valu, cmpr=cmpr):
                yield node
            return

        async for node in self._getNodesByProp(full, valu=valu, cmpr=cmpr):
            yield node

    async def _getNodesByProp(self, full, valu=None, cmpr='='):

        prop = self.model.prop(full)
        if prop is None:
            raise s_exc.NoSuchProp(name=full)

        if prop.isrunt:

            async for node in self.getRuntNodes(full, valu, cmpr):
                yield node

            return

        lops = prop.getLiftOps(valu, cmpr=cmpr)

        if prop.isform and cmpr == '=' and valu is not None and len(lops) == 1 and lops[0][1][2][0][0] == 'eq':
            # Shortcut to buid lookup if primary prop = valu
            norm, _ = prop.type.norm(valu)
            node = await self.getNodeByNdef((full, norm))
            if node is None:
                return

            yield node

            return

        cmpf = prop.type.getLiftHintCmpr(valu, cmpr=cmpr)

        async for row, node in self.getLiftNodes(lops, prop.name, cmpf):
            yield node

    async def _getNodesByType(self, name, valu=None, addform=True):

        _type = self.model.types.get(name)
        if _type is None:
            raise s_exc.NoSuchType(name=name)

        if addform:
            form = self.model.forms.get(name)
            if form is not None:
                lops = form.getLiftOps(valu)
                async for row, node in self.getLiftNodes(lops, '*' + form.name):
                    yield node

        for prop in self.model.getPropsByType(name):
            lops = prop.getLiftOps(valu)
            async for row, node in self.getLiftNodes(lops, prop):
                yield node

    async def addNode(self, name, valu, props=None):
        '''
        Add a node by form name and value with optional props.

        Args:
            name (str): The form of node to add.
            valu (obj): The value for the node.
            props (dict): Optional secondary properties for the node.
        '''

        try:

            fnib = self._getNodeFnib(name, valu)
            retn = await self._addNodeFnib(fnib, props=props)
            return retn

        except asyncio.CancelledError:
            raise

        except Exception:

            mesg = f'Error adding node: {name} {valu!r} {props!r}'
            logger.exception(mesg)
            if self.strict:
                raise

            return None

    async def addFeedNodes(self, name, items):
        '''
        Call a feed function and return what it returns (typically yields Node()s).

        Args:
            name (str): The name of the feed record type.
            items (list): A list of records of the given feed type.

        Returns:
            (object): The return value from the feed function. Typically Node() generator.

        '''
        func = self.core.getFeedFunc(name)
        if func is None:
            raise s_exc.NoSuchName(name=name)

        logger.info(f'adding feed nodes ({name}): {len(items)}')

        async for node in func(self, items):
            yield node

    async def addFeedData(self, name, items, seqn=None):

        func = self.core.getFeedFunc(name)
        if func is None:
            raise s_exc.NoSuchName(name=name)

        logger.info(f'adding feed data ({name}): {len(items)} {seqn!r}')

        retn = func(self, items)

        # If the feed function is an async generator, run it...
        if isinstance(retn, types.AsyncGeneratorType):
            retn = [x async for x in retn]
        elif s_coro.iscoro(retn):
            await retn

        if seqn is not None:

            iden, offs = seqn

            nextoff = offs + len(items)

            await self.setOffset(iden, nextoff)

            return nextoff

    async def addTagNode(self, name):
        '''
        Ensure that the given syn:tag node exists.
        '''
        return await self.tagcache.aget(name)

    async def _addTagNode(self, name):
        return await self.addNode('syn:tag', name)

    async def _addNodeFnib(self, fnib, props=None):

        with s_editatom.EditAtom(self.core.bldgbuids) as editatom:

            node = await self._addNodeFnibOps(fnib, editatom, props)
            if node is not None:
                if props is not None:
                    for name, valu in props.items():
                        await node._setops(name, valu, editatom)

            await editatom.commit(self)

            if node is None:
                node = editatom.mybldgbuids[fnib[3]]

            return node

    async def _addNodeFnibOps(self, fnib, editatom, props=None):
        '''
        Add a node via (form, norm, info, buid) and add ops to editatom
        '''
        form, norm, info, buid = fnib

        if form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot make runt nodes.',
                                   form=form.full, prop=norm)

        if props is None:
            props = {}
        # Check if this buid is already under construction
        node = editatom.getNodeBeingMade(buid)
        if node is not None:
            return node

        # Check if this buid is already fully made
        node = await self.getNodeByBuid(buid)
        if node is not None:
            return node

        # Another editatom might have created in another task during the above call, so check again
        node = editatom.getNodeBeingMade(buid)
        if node is not None:
            return node

        if props is None:
            props = {}

        # lets build a node...
        node = s_node.Node(self, None)

        node.buid = buid
        node.form = form
        node.ndef = (form.name, norm)

        sops = form.getSetOps(buid, norm)
        editatom.sops.extend(sops)

        editatom.addNode(node)

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
            await node._setops(name, valu, editatom, init=True)

        # set our global properties
        tick = s_common.now()
        await node._setops('.created', tick, editatom, init=True)

        return None

    async def _raiseOnStrict(self, ctor, mesg, **info):
        await self.warn(f'{ctor.__name__}: {mesg} {info!r}')
        if self.strict:
            raise ctor(mesg=mesg, **info)
        return False

    def splice(self, name, **info):
        '''
        Construct a partial splice record for later feeding into Snap.stor method
        '''
        return (name, info)

    #########################################################################

    def _getNodeFnib(self, name, valu):
        '''
        return a form, norm, info, buid tuple
        '''
        form = self.model.form(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        try:
            norm, info = form.type.norm(valu)
        except Exception as e:
            raise s_exc.BadPropValu(prop=form.name, valu=valu, mesg=str(e))

        buid = s_common.buid((form.name, norm))
        return form, norm, info, buid

    async def addNodes(self, nodedefs):
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
            if props is not None:
                props.pop('.created', None)

            node = await self.addNode(formname, formvalu, props=props)
            if node is not None:
                tags = forminfo.get('tags')
                if tags is not None:
                    for tag, asof in tags.items():
                        await node.addTag(tag, valu=asof)

            yield node

    async def stor(self, sops, splices=None):

        if not splices:
            await self.wlyr.stor(sops)
            return

        now = s_common.now()
        user = self.user.iden

        wasnew, providen, provstack = self.core.provstor.commit()
        if wasnew:
            await self.fire('prov:new', time=now, user=user, prov=providen, provstack=provstack)

        for splice in splices:
            name, info = splice
            info.update(time=now, user=user, prov=providen)
            await self.fire(name, **info)

        await self.wlyr.stor(sops, splices=splices)

    async def getLiftNodes(self, lops, rawprop, cmpr=None):
        genr = self.getLiftRows(lops)
        async for node in self.getRowNodes(genr, rawprop, cmpr):
            yield node

    async def getRuntNodes(self, full, valu=None, cmpr='='):

        async for buid, rows in self.core.runRuntLift(full, valu, cmpr):
            node = s_node.Node(self, buid, rows)
            if node.ndef is not None:
                yield node

    async def getLiftRows(self, lops):
        '''
        Yield row tuples from a series of lift operations.

        Row tuples only requirement is that the first element
        be the binary id of a node.

        Args:
            lops (list): A list of lift operations.

        Yields:
            (tuple): (layer_indx, (buid, ...)) rows.
        '''
        for layer_idx, layr in enumerate(self.layers):
            async for x in layr.getLiftRows(lops):
                yield layer_idx, x

    async def getRowNodes(self, rows, rawprop, cmpr=None):
        '''
        Join a row generator into (row, Node()) tuples.

        A row generator yields tuple rows where the first
        valu is the buid of a node.

        Args:
            rows: A generator of (layer_idx, (buid, ...)) tuples.
            rawprop(str):  "raw" propname i.e. if a tag, starts with "#".  Used for filtering so that we skip the props
                for a buid if we're asking from a higher layer than the row was from (and hence, we'll presumable
                get/have gotten the row when that layer is lifted.
            cmpr (func): A secondary comparison function used to filter nodes.
        Yields:
            (tuple): (row, node)
        '''
        count = 0
        async for origlayer, row in rows:
            count += 1
            if not count % 5:
                await asyncio.sleep(0)  # give other tasks some time
            props = {}
            buid = row[0]
            node = self.livenodes.get(buid)
            # Evaluate layers top-down to more quickly abort if we've found a higher layer with the property set
            for layeridx in range(len(self.layers) - 1, -1, -1):
                layr = self.layers[layeridx]
                layerprops = await layr.getBuidProps(buid)
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
                if node.ndef is None:
                    continue
                self.livenodes[buid] = node

            if cmpr:
                if rawprop == node.form.name:
                    valu = node.ndef[1]
                else:
                    valu = node.get(rawprop)
                if valu is None:
                    # cmpr required to evaluate something; cannot know if this
                    # node is valid or not without the prop being present.
                    continue
                if not cmpr(valu):
                    continue

            yield row, node
