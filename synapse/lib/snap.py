from __future__ import annotations

import types
import asyncio
import logging
import weakref
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.chop as s_chop
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.storm as s_storm
import synapse.lib.types as s_types
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled

logger = logging.getLogger(__name__)

class Scrubber:

    def __init__(self, rules):
        self.rules = rules
        # TODO support props
        # TODO support tagprops
        # TODO support exclude rules
        incs = rules.get('include', {})

        self.hasinctags = incs.get('tags') is not None
        self.inctags = set(incs.get('tags', ()))
        self.inctagprefs = [f'{tag}.' for tag in incs.get('tags', ())]

    def scrub(self, pode):

        if self.hasinctags and pode[1].get('tags'):
            pode[1]['tags'] = {k: v for (k, v) in pode[1]['tags'].items() if self._isTagInc(k)}

            if pode[1].get('tagprops'):
                pode[1]['tagprops'] = {k: v for (k, v) in pode[1]['tagprops'].items() if self._isTagInc(k)}

        return pode

    @s_cache.memoizemethod()
    def _isTagInc(self, tag):
        if tag in self.inctags:
            return True
        if any(tag.startswith(pref) for pref in self.inctagprefs):
            return True
        return False

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

    async def __anit__(self, view, user):
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

        self.core = view.core
        self.view = view
        self.user = user

        self.buidprefetch = self.view.isafork()

        self.layers = list(reversed(view.layers))
        self.wlyr = self.layers[-1]

        self.readonly = self.wlyr.readonly

        # variables used by the storm runtime
        self.vars = {}

        self.runt = {}

        self.debug = False      # Set to true to enable debug output.
        self.write = False      # True when the snap has a write lock on a layer.

        self._tagcachesize = 10000
        self._buidcachesize = 100000
        self.tagcache = s_cache.FixedCache(self._addTagNode, size=self._tagcachesize)
        # Keeps alive the most recently accessed node objects
        self.buidcache = collections.deque(maxlen=self._buidcachesize)
        self.livenodes = weakref.WeakValueDictionary()  # buid -> Node
        self._warnonce_keys = set()

        self.onfini(self.stack.close)
        self.changelog = []
        self.tagtype = self.core.model.type('ival')
        self.trigson = self.core.trigson

    def disableTriggers(self):
        self.trigson = False

    async def getSnapMeta(self):
        '''
        Retrieve snap metadata to store along side nodeEdits.
        '''
        meta = {
            'time': s_common.now(),
            'user': self.user.iden
        }

        providen = self.core.provstor.precommit()
        if providen is not None:
            meta['prov'] = providen

        return meta

    @contextlib.asynccontextmanager
    async def getStormRuntime(self, query, opts=None, user=None):
        if user is None:
            user = self.user

        async with await s_storm.Runtime.anit(query, self, opts=opts, user=user) as runt:
            yield runt

    async def iterStormPodes(self, text, opts=None, user=None):
        '''
        Yield packed node tuples for the given storm query text.
        '''
        if user is None:
            user = self.user

        dorepr = False
        dopath = False

        self.core._logStormQuery(text, user)

        scrubber = None
        # NOTE: This option is still experimental and subject to change.
        if opts.get('scrub') is not None:
            scrubber = Scrubber(opts.get('scrub'))

        if opts is not None:
            dorepr = opts.get('repr', False)
            dopath = opts.get('path', False)

        async for node, path in self.storm(text, opts=opts, user=user):

            pode = node.pack(dorepr=dorepr)
            pode[1]['path'] = path.pack(path=dopath)

            if scrubber is not None:
                pode = scrubber.scrub(pode)

            yield pode

    @s_coro.genrhelp
    async def storm(self, text, opts=None, user=None):
        '''
        Execute a storm query and yield (Node(), Path()) tuples.
        '''
        if user is None:
            user = self.user

        if opts is None:
            opts = {}

        mode = opts.get('mode', 'storm')

        query = self.core.getStormQuery(text, mode=mode)
        async with self.getStormRuntime(query, opts=opts, user=user) as runt:
            async for x in runt.execute():
                yield x

    @s_coro.genrhelp
    async def eval(self, text, opts=None, user=None):
        '''
        Run a storm query and yield Node() objects.
        '''
        if user is None:
            user = self.user

        if opts is None:
            opts = {}

        mode = opts.get('mode', 'storm')

        # maintained for backward compatibility
        query = self.core.getStormQuery(text, mode=mode)
        async with self.getStormRuntime(query, opts=opts, user=user) as runt:
            async for node, path in runt.execute():
                yield node

    async def nodes(self, text, opts=None, user=None):
        return [node async for (node, path) in self.storm(text, opts=opts, user=user)]

    async def clearCache(self):
        self.tagcache.clear()
        self.buidcache.clear()
        self.livenodes.clear()

    async def printf(self, mesg):
        await self.fire('print', mesg=mesg)

    async def warn(self, mesg, log=True, **info):
        if log:
            logger.warning(mesg)
        await self.fire('warn', mesg=mesg, **info)

    async def warnonce(self, mesg, log=True, **info):
        if mesg in self._warnonce_keys:
            return
        self._warnonce_keys.add(mesg)
        await self.warn(mesg, log, **info)

    async def getNodeByBuid(self, buid):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            Optional[s_node.Node]: The node object or None.

        '''
        return await self._joinStorNode(buid, {})

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

    async def nodesByTagProp(self, form, tag, name):
        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        async for (buid, sodes) in self.core._liftByTagProp(form, tag, name, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByTagPropValu(self, form, tag, name, cmpr, valu):
        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        cmprvals = prop.type.getStorCmprs(cmpr, valu)
        # an empty return probably means ?= with invalid value
        if not cmprvals:
            return

        async for (buid, sodes) in self.core._liftByTagPropValu(form, tag, name, cmprvals, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def _joinStorNode(self, buid, cache):

        node = self.livenodes.get(buid)
        if node is not None:
            await asyncio.sleep(0)
            return node

        layrs = (layr for layr in self.layers if layr.iden not in cache)
        if layrs:
            indx = 0
            newsodes = await self.core._getStorNodes(buid, layrs)

        sodes = []
        for layr in self.layers:
            sode = cache.get(layr.iden)
            if sode is None:
                sode = newsodes[indx]
                indx += 1
            sodes.append((layr.iden, sode))

        return await self._joinSodes(buid, sodes)

    async def _joinSodes(self, buid, sodes):

        node = self.livenodes.get(buid)
        if node is not None:
            await asyncio.sleep(0)
            return node

        ndef = None
        tags = {}
        props = {}
        nodedata = {}
        tagprops = {}

        bylayer = {
            'ndef': None,
            'tags': {},
            'props': {},
            'tagprops': {},
        }

        for (layr, sode) in sodes:

            form = sode.get('form')
            valt = sode.get('valu')
            if valt is not None:
                ndef = (form, valt[0])
                bylayer['ndef'] = layr

            storprops = sode.get('props')
            if storprops is not None:
                for prop, (valu, stype) in storprops.items():
                    props[prop] = valu
                    bylayer['props'][prop] = layr

            stortags = sode.get('tags')
            if stortags is not None:
                tags.update(stortags)
                bylayer['tags'].update({p: layr for p in stortags.keys()})

            stortagprops = sode.get('tagprops')
            if stortagprops is not None:
                for tag, propdict in stortagprops.items():
                    for tagprop, (valu, stype) in propdict.items():
                        if tag not in tagprops:
                            tagprops[tag] = {}
                        tagprops[tag][tagprop] = valu
                        bylayer['tagprops'][tagprop] = layr

            stordata = sode.get('nodedata')
            if stordata is not None:
                nodedata.update(stordata)

        if ndef is None:
            await asyncio.sleep(0)
            return None

        pode = (buid, {
            'ndef': ndef,
            'tags': tags,
            'props': props,
            'nodedata': nodedata,
            'tagprops': tagprops,
        })

        node = s_node.Node(self, pode, bylayer=bylayer)
        self.livenodes[buid] = node
        self.buidcache.append(node)

        await asyncio.sleep(0)
        return node

    async def nodesByDataName(self, name):
        async for (buid, sodes) in self.core._liftByDataName(name, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByProp(self, full):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if prop.isrunt:
            async for node in self.getRuntNodes(prop.full):
                yield node
            return

        if prop.isform:
            async for (buid, sodes) in self.core._liftByProp(prop.name, None, self.layers):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        if prop.isuniv:
            async for (buid, sodes) in self.core._liftByProp(None, prop.name, self.layers):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        formname = None
        if not prop.isuniv:
            formname = prop.form.name

        # Prop is secondary prop
        async for (buid, sodes) in self.core._liftByProp(formname, prop.name, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByPropValu(self, full, cmpr, valu):
        if cmpr == 'type=':
            async for node in self.nodesByPropValu(full, '=', valu):
                yield node

            async for node in self.nodesByPropTypeValu(full, valu):
                yield node
            return

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        cmprvals = prop.type.getStorCmprs(cmpr, valu)
        # an empty return probably means ?= with invalid value
        if not cmprvals:
            return

        if prop.isrunt:
            for storcmpr, storvalu, _ in cmprvals:
                async for node in self.getRuntNodes(prop.full, valu=storvalu, cmpr=storcmpr):
                    yield node
            return

        if prop.isform:
            async for (buid, sodes) in self.core._liftByFormValu(prop.name, cmprvals, self.layers):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        if prop.isuniv:
            async for (buid, sodes) in self.core._liftByPropValu(None, prop.name, cmprvals, self.layers):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        async for (buid, sodes) in self.core._liftByPropValu(prop.form.name, prop.name, cmprvals, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByTag(self, tag, form=None):
        async for (buid, sodes) in self.core._liftByTag(tag, form, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByTagValu(self, tag, cmpr, valu, form=None):
        norm, info = self.core.model.type('ival').norm(valu)
        async for (buid, sodes) in self.core._liftByTagValu(tag, cmpr, norm, form, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def nodesByPropTypeValu(self, name, valu):

        _type = self.core.model.types.get(name)
        if _type is None:
            raise s_exc.NoSuchType(name=name)

        for prop in self.core.model.getPropsByType(name):
            async for node in self.nodesByPropValu(prop.full, '=', valu):
                yield node

    async def nodesByPropArray(self, full, cmpr, valu):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if not isinstance(prop.type, s_types.Array):
            mesg = f'Array synax is invalid on non array type: {prop.type.name}.'
            raise s_exc.BadTypeValu(mesg=mesg)

        cmprvals = prop.type.arraytype.getStorCmprs(cmpr, valu)

        if prop.isform:
            async for (buid, sodes) in self.core._liftByPropArray(prop.name, None, cmprvals, self.layers):
                node = await self._joinSodes(buid, sodes)
                if node is not None:
                    yield node
            return

        formname = None
        if prop.form is not None:
            formname = prop.form.name

        async for (buid, sodes) in self.core._liftByPropArray(formname, prop.name, cmprvals, self.layers):
            node = await self._joinSodes(buid, sodes)
            if node is not None:
                yield node

    async def getNodeAdds(self, form, valu, props, addnode=True):

        async def _getadds(f, p, formnorm, forminfo, doaddnode=True):

            if f.locked:
                mesg = f'Form {f.full} is locked due to deprecation.'
                raise s_exc.IsDeprLocked(mesg=mesg)

            edits = []  # Non-primary prop edits
            topsubedits = []  # Primary prop sub edits

            formsubs = forminfo.get('subs', {})
            for subname, subvalu in formsubs.items():
                p[subname] = subvalu

            for propname, propvalu in p.items():
                subedits: s_layer.NodeEditsT = []

                prop = f.prop(propname)
                if prop is None:
                    continue

                if prop.locked:
                    mesg = f'Prop {prop.full} is locked due to deprecation.'
                    if not self.strict:
                        await self.warn(mesg)
                        continue
                    raise s_exc.IsDeprLocked(mesg=mesg)

                assert prop.type.stortype is not None

                propnorm, typeinfo = prop.type.norm(propvalu)

                if isinstance(prop.type, s_types.Ndef):
                    ndefname, ndefvalu = propvalu
                    ndefform = self.core.model.form(ndefname)
                    if ndefform is None:
                        raise s_exc.NoSuchForm(name=ndefname)

                    if ndefform.locked:
                        mesg = f'Form {ndefform.full} is locked due to deprecation.'
                        if not self.strict:
                            await self.warn(mesg)
                            continue
                        raise s_exc.IsDeprLocked(mesg=mesg)

                    ndefnorm, ndefinfo = ndefform.type.norm(ndefvalu)
                    do_subedit = True
                    if self.buidprefetch:
                        node = await self.getNodeByBuid(s_common.buid((ndefform.name, ndefnorm)))
                        do_subedit = node is None

                    if do_subedit:
                        subedits.extend([x async for x in _getadds(ndefform, {}, ndefnorm, ndefinfo)])

                elif isinstance(prop.type, s_types.Array):
                    arrayform = self.core.model.form(prop.type.arraytype.name)
                    if arrayform is not None:
                        if arrayform.locked:
                            mesg = f'Form {arrayform.full} is locked due to deprecation.'
                            if not self.strict:
                                await self.warn(mesg)
                                continue
                            raise s_exc.IsDeprLocked(mesg=mesg)

                        for arrayvalu in propnorm:
                            arraynorm, arrayinfo = arrayform.type.norm(arrayvalu)

                            if self.buidprefetch:
                                node = await self.getNodeByBuid(s_common.buid((arrayform.name, arraynorm)))
                                if node is not None:
                                    continue

                            subedits.extend([x async for x in _getadds(arrayform, {}, arraynorm, arrayinfo)])

                propsubs = typeinfo.get('subs')
                if propsubs is not None:
                    for subname, subvalu in propsubs.items():
                        fullname = f'{prop.full}:{subname}'
                        subprop = self.core.model.prop(fullname)
                        if subprop is None:
                            continue

                        assert subprop.type.stortype is not None

                        subnorm, subinfo = subprop.type.norm(subvalu)

                        edits.append((s_layer.EDIT_PROP_SET, (subprop.name, subnorm, None, subprop.type.stortype), ()))

                propform = self.core.model.form(prop.type.name)
                if propform is not None:

                    doedit = True
                    if self.buidprefetch:
                        node = await self.getNodeByBuid(s_common.buid((propform.name, propnorm)))
                        doedit = node is None

                    if doedit:
                        subedits.extend([x async for x in _getadds(propform, {}, propnorm, typeinfo)])

                edit: s_layer.EditT = (s_layer.EDIT_PROP_SET, (propname, propnorm, None, prop.type.stortype), subedits)
                if propname in formsubs:
                    topsubedits.append(edit)
                else:
                    edits.append(edit)

            buid = s_common.buid((f.name, formnorm))

            if doaddnode:
                # Make all the sub edits for the primary property a conditional nodeEdit under a top-level NODE_ADD
                # edit
                if topsubedits:
                    subnodeedits: s_layer.NodeEditsT = [(buid, f.name, topsubedits)]
                else:
                    subnodeedits = ()
                topedit: s_layer.EditT = (s_layer.EDIT_NODE_ADD, (formnorm, f.type.stortype), subnodeedits)
                yield (buid, f.name, [topedit] + edits)
            else:
                yield (buid, f.name, edits)

        if self.core.maxnodes is not None and self.core.maxnodes <= self.core.nodecount:
            mesg = f'Cortex is at node:count limit: {self.core.maxnodes}'
            raise s_exc.HitLimit(mesg=mesg)

        if props is None:
            props = {}

        norm, info = form.type.norm(valu)
        return [x async for x in _getadds(form, props, norm, info, doaddnode=addnode)]

    async def applyNodeEdit(self, edit):
        nodes = await self.applyNodeEdits((edit,))
        return nodes[0]

    async def applyNodeEdits(self, edits):
        '''
        Sends edits to the write layer and evaluates the consequences (triggers, node object updates)
        '''
        if self.readonly:
            mesg = 'The snapshot is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        meta = await self.getSnapMeta()

        todo = s_common.todo('storNodeEdits', edits, meta)
        results = await self.core.dyncall(self.wlyr.iden, todo)

        wlyr = self.wlyr
        nodes = []
        callbacks = []
        actualedits = []  # List[Tuple[buid, form, changes]]

        # make a pass through the returned edits, apply the changes to our Nodes()
        # and collect up all the callbacks to fire at once at the end.  It is
        # critical to fire all callbacks after applying all Node() changes.

        for buid, sode, postedits in results:

            cache = {wlyr.iden: sode}

            node = await self._joinStorNode(buid, cache)

            if node is None:
                # We got part of a node but no ndef
                continue

            nodes.append(node)

            if postedits:
                actualedits.append((buid, node.form.name, postedits))

            for edit in postedits:

                etyp, parms, _ = edit

                if etyp == s_layer.EDIT_NODE_ADD:
                    node.bylayer['ndef'] = wlyr.iden
                    callbacks.append((node.form.wasAdded, (node,), {}))
                    callbacks.append((self.view.runNodeAdd, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_NODE_DEL:
                    callbacks.append((node.form.wasDeleted, (node,), {}))
                    callbacks.append((self.view.runNodeDel, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_SET:

                    (name, valu, oldv, stype) = parms

                    prop = node.form.props.get(name)
                    if prop is None: # pragma: no cover
                        logger.warning(f'applyNodeEdits got EDIT_PROP_SET for bad prop {name} on form {node.form}')
                        continue

                    node.props[name] = valu
                    node.bylayer['props'][name] = wlyr.iden

                    callbacks.append((prop.wasSet, (node, oldv), {}))
                    callbacks.append((self.view.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_DEL:

                    (name, oldv, stype) = parms

                    prop = node.form.props.get(name)
                    if prop is None: # pragma: no cover
                        logger.warning(f'applyNodeEdits got EDIT_PROP_DEL for bad prop {name} on form {node.form}')
                        continue

                    node.props.pop(name, None)
                    node.bylayer['props'].pop(name, None)

                    callbacks.append((prop.wasDel, (node, oldv), {}))
                    callbacks.append((self.view.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_TAG_SET:

                    (tag, valu, oldv) = parms

                    node.tags[tag] = valu
                    node.bylayer['tags'][tag] = wlyr.iden

                    callbacks.append((self.view.runTagAdd, (node, tag, valu), {}))
                    callbacks.append((self.wlyr.fire, ('tag:add', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_DEL:

                    (tag, oldv) = parms

                    node.tags.pop(tag, None)
                    node.bylayer['tags'].pop(tag, None)

                    callbacks.append((self.view.runTagDel, (node, tag, oldv), {}))
                    callbacks.append((self.wlyr.fire, ('tag:del', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAGPROP_SET:
                    (tag, prop, valu, oldv, stype) = parms
                    if tag not in node.tagprops:
                        node.tagprops[tag] = {}
                    node.tagprops[tag][prop] = valu
                    node.bylayer['tags'][(tag, prop)] = wlyr.iden
                    continue

                if etyp == s_layer.EDIT_TAGPROP_DEL:
                    (tag, prop, oldv, stype) = parms
                    if tag in node.tagprops:
                        node.tagprops[tag].pop(prop, None)
                        if not node.tagprops[tag]:
                            node.tagprops.pop(tag, None)
                    node.bylayer['tags'].pop((tag, prop), None)
                    continue

        [await func(*args, **kwargs) for (func, args, kwargs) in callbacks]

        if actualedits:
            providen, provstack = self.core.provstor.stor()
            if providen is not None:
                await self.fire('prov:new', time=meta['time'], user=meta['user'], prov=providen, provstack=provstack)
            await self.fire('node:edits', edits=actualedits)

        return nodes

    async def addNode(self, name, valu, props=None):
        '''
        Add a node by form name and value with optional props.

        Args:
            name (str): The form of node to add.
            valu (obj): The value for the node.
            props (dict): Optional secondary properties for the node.

        Notes:
            If a props dictionary is provided, it may be mutated during node construction.

        Returns:
            s_node.Node: A Node object. It may return None if the snap is unable to add or lift the node.
        '''
        if self.readonly:
            mesg = 'The snapshot is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        form = self.core.model.form(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        if form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot make runt nodes.',
                                   form=form.full, prop=valu)

        try:

            if self.buidprefetch:
                norm, info = form.type.norm(valu)
                node = await self.getNodeByBuid(s_common.buid((form.name, norm)))
                if node is not None:
                    # TODO implement node.setNodeProps()
                    if props is not None:
                        for p, v in props.items():
                            await node.set(p, v)
                    return node

            adds = await self.getNodeAdds(form, valu, props=props)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception as e:
            if not self.strict:
                await self.warn(f'addNode: {e}')
                return None
            raise

        nodes = await self.applyNodeEdits(adds)
        assert len(nodes) >= 1

        # Adds is top-down, so the first node is what we want
        return nodes[0]

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

        logger.info(f'User ({self.user.name}) adding feed data ({name}): {len(items)}')

        genr = func(self, items)
        if not isinstance(genr, types.AsyncGeneratorType):
            if isinstance(genr, types.CoroutineType):
                genr.close()
            mesg = f'feed func returned a {type(genr)}, not an async generator.'
            raise s_exc.BadCtorType(mesg=mesg, name=name)

        async for node in genr:
            yield node

    async def addFeedData(self, name, items):

        func = self.core.getFeedFunc(name)
        if func is None:
            raise s_exc.NoSuchName(name=name)

        logger.info(f'User ({self.user.name}) adding feed data ({name}): {len(items)}')

        retn = func(self, items)

        # If the feed function is an async generator, run it...
        if isinstance(retn, types.AsyncGeneratorType):
            retn = [x async for x in retn]
        elif s_coro.iscoro(retn):
            await retn

    async def addTagNode(self, name):
        '''
        Ensure that the given syn:tag node exists.
        '''
        return await self.tagcache.aget(name)

    async def _addTagNode(self, name):
        return await self.addNode('syn:tag', name)

    async def _raiseOnStrict(self, ctor, mesg, **info):
        if self.strict:
            raise ctor(mesg=mesg, **info)
        return False

    async def _getAddNodeEdits(self, name, valu, props=None):

        form = self.core.model.form(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        if form.isrunt:
            raise s_exc.IsRuntForm(mesg='Cannot make runt nodes.',
                                   form=form.full, prop=valu)

        if self.buidprefetch:
            norm, info = form.type.norm(valu)
            buid = s_common.buid((form.name, norm))
            node = await self.getNodeByBuid(buid)
            if node is not None:
                if props is not None:
                    return (node, await self.getNodeAdds(form, valu, props=props, addnode=False))
                else:
                    return (node, [(buid, form.name, [])])

        return (None, await self.getNodeAdds(form, valu, props=props))

    async def _getAddTagEdits(self, node, tags):

        edits = []
        for tag, valu in tags.items():

            path = s_chop.tagpath(tag)
            name = '.'.join(path)

            if not await self.core.isTagValid(name):
                await self.warn(f'Tag {tag} does not meet the regex for the tree.')
                continue

            tagnode = await self.addTagNode(name)

            isnow = tagnode.get('isnow')
            if isnow:
                await self.warn(f'Tag {name} is now {isnow}')
                name = isnow
                path = isnow.split('.')

            if isinstance(valu, list):
                valu = tuple(valu)

            if valu != (None, None):
                try:
                    valu = self.core.model.type('ival').norm(valu)[0]
                except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                    raise
                except Exception as e:
                    await self.warn(f'Bad tag value: #{tag}={valu}')
                    continue

            curv = None
            if node is not None:
                curv = node.tags.get(name)
                if curv == valu:
                    continue

            if curv is None:
                tags = s_chop.tags(name)
                for tag in tags[:-1]:
                    if node is not None and node.tags.get(tag) is not None:
                        continue

                    await self.addTagNode(tag)
                    edits.append((s_layer.EDIT_TAG_SET, (tag, (None, None), None), ()))

            else:
                valu = s_time.ival(*valu, *curv)

            edits.append((s_layer.EDIT_TAG_SET, (name, valu, None), ()))

        return edits

    async def _getAddTagPropEdits(self, node, tagprops):

        edits = []
        for tag, props in tagprops.items():
            for name, valu in props.items():

                prop = self.core.model.getTagProp(name)
                if prop is None:
                    await self.warn(f'Tagprop {name} does not exist in this Cortex.')
                    continue

                try:
                    norm, info = prop.type.norm(valu)
                except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                    raise
                except Exception as e:
                    await self.warn(f'Bad property value: #{tag}:{prop.name}={valu!r}')
                    continue

                tagkey = (tag, name)
                if node is not None:
                    curv = node.tagprops.get(tagkey)
                    if norm == curv:
                        continue

                edits.append((s_layer.EDIT_TAGPROP_SET, (tag, name, norm, None, prop.type.stortype), ()))

        return edits

    async def addNodes(self, nodedefs):
        '''
        Add/merge nodes in bulk.

        The addNodes API is designed for bulk adds which will
        also set properties, add tags, add edges, and set nodedata to existing nodes.
        Nodes are specified as a list of the following tuples:

            ( (form, valu), {'props':{}, 'tags':{}})

        Args:
            nodedefs (list): A list of nodedef tuples.

        Returns:
            (list): A list of xact messages.
        '''
        if self.readonly:
            mesg = 'The snapshot is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        nodeedits = []
        buids = set()
        n2buids = set()
        for (formname, formvalu), forminfo in nodedefs:
            try:
                props = forminfo.get('props')

                # remove any universal created props...
                if props is not None:
                    props.pop('.created', None)

                oldstrict = self.strict
                self.strict = False
                try:

                    (node, editset) = await self._getAddNodeEdits(formname, formvalu, props=props)
                    if editset is not None:
                        buid, form, edits = editset[0]

                        tags = forminfo.get('tags')
                        tagprops = forminfo.get('tagprops')
                        if tagprops is not None:
                            if tags is None:
                                tags = {}

                            for tag in tagprops.keys():
                                tags[tag] = (None, None)

                        if tags is not None:
                            tagedits = await self._getAddTagEdits(node, tags)
                            edits.extend(tagedits)

                        if tagprops is not None:
                            tpedits = await self._getAddTagPropEdits(node, tagprops)
                            edits.extend(tpedits)

                        nodedata = forminfo.get('nodedata')
                        if nodedata is not None:
                            try:
                                for name, data in nodedata.items():
                                    # make sure we have valid nodedata
                                    if not (isinstance(name, str)):
                                        await self.warn(f'Nodedata key is not a string: {name}')
                                        continue
                                    s_common.reqjsonsafe(data)
                                    edits.append((s_layer.EDIT_NODEDATA_SET, (name, data, None), ()))
                            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                                raise
                            except Exception as e:
                                await self.warn(f'Failed adding node data on {formname}, {formvalu}, {forminfo}: {e}')

                        n2edits = []
                        for verb, n2iden in forminfo.get('edges', ()):
                            # check for embedded ndef rather than n2iden
                            if isinstance(n2iden, (list, tuple)):
                                n2formname, n2valu = n2iden

                                n2form = self.core.model.form(n2formname)
                                if n2form is None:
                                    await self.warn(f'Failed to make n2 edge node for {n2iden}: invalid form')
                                    continue

                                if n2form.isrunt:
                                    await self.warn(f'Edges cannot be used with runt nodes: {n2formname}')
                                    continue

                                try:
                                    n2norm, _ = n2form.type.norm(n2valu)
                                    n2buid = s_common.buid((n2form.name, n2norm))

                                    if not (n2buid in n2buids or n2buid in buids):
                                        _, n2editset = await self._getAddNodeEdits(n2formname, n2valu)
                                        n2edits.extend(n2editset)

                                except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                                    raise
                                except:
                                    await self.warn(f'Failed to make n2 edge node for {n2iden}')
                                    continue

                                n2iden = s_common.ehex(n2buid)
                                n2buids.add(n2buid)

                            # make sure a valid iden and verb were passed in
                            elif not (isinstance(n2iden, str) and len(n2iden) == 64):
                                await self.warn(f'Invalid n2 iden {n2iden}')
                                continue

                            if not (isinstance(verb, str)):
                                await self.warn(f'Invalid edge verb {verb}')
                                continue

                            edits.append((s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()))

                        nodeedits.append((buid, form, edits))
                        nodeedits.extend(n2edits)
                        buids.add(buid)
                        await asyncio.sleep(0)

                except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                    raise

                except Exception as e:
                    if not oldstrict:
                        await self.warn(f'addNodes failed on {formname}, {formvalu}, {forminfo}: {e}')
                        await asyncio.sleep(0)
                        continue
                    raise

                finally:
                    self.strict = oldstrict

                if len(buids) >= 1000:
                    nodes = await self.applyNodeEdits(nodeedits)
                    for node in nodes:
                        if node.buid in buids:
                            yield node
                            await asyncio.sleep(0)

                    nodedits = []
                    buids.clear()
                    n2buids.clear()

            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise

            except Exception:
                logger.exception(f'Error making node: [{formname}={formvalu}]')

        nodes = await self.applyNodeEdits(nodeedits)
        for node in nodes:
            if node.buid in buids:
                yield node
                await asyncio.sleep(0)

    async def getRuntNodes(self, full, valu=None, cmpr=None):

        todo = s_common.todo('runRuntLift', full, valu, cmpr)
        async for sode in self.core.dyniter('cortex', todo):

            node = s_node.Node(self, sode)
            node.isrunt = True

            yield node

    async def iterNodeEdgesN1(self, buid, verb=None):

        async with await s_spooled.Set.anit(dirn=self.core.dirn) as edgeset:

            for layr in self.layers:

                async for edge in layr.iterNodeEdgesN1(buid, verb=verb):
                    if edge in edgeset:
                        continue

                    await edgeset.add(edge)
                    yield edge

    async def iterNodeEdgesN2(self, buid, verb=None):

        async with await s_spooled.Set.anit(dirn=self.core.dirn) as edgeset:

            for layr in self.layers:

                async for edge in layr.iterNodeEdgesN2(buid, verb=verb):
                    if edge in edgeset:
                        continue

                    await edgeset.add(edge)
                    yield edge

    async def getNodeData(self, buid, name, defv=None):
        '''
        Get nodedata from closest to write layer, no merging involved
        '''
        for layr in reversed(self.layers):
            todo = s_common.todo('getNodeData', buid, name)
            ok, valu = await self.core.dyncall(layr.iden, todo)
            if ok:
                return valu
        return defv

    async def iterNodeData(self, buid):
        '''
        Returns:  Iterable[Tuple[str, Any]]
        '''
        some = False
        for layr in reversed(self.layers):
            todo = s_common.todo('iterNodeData', buid)
            async for item in self.core.dyniter(layr.iden, todo):
                some = True
                yield item
            if some:
                return
