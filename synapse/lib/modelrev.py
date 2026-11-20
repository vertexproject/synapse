import logging

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
import synapse.lib.editor as s_editor
import synapse.lib.scrape as s_scrape
import synapse.lib.spooled as s_spooled
import synapse.lib.nodefuse as s_nodefuse

import synapse.models.inet as s_inet

logger = logging.getLogger(__name__)

maxvers = (3, 3, 0)

# The end of the host of a Windows WebDAV file URL, file://host[@SSL]@port/path, as
# stored by a normalizer which took the port for an IPv4 host: host[@SSL]@0.0.x.y
urldavre = regex.compile(r'@(?:(ssl)@)?0\.0\.(\d{1,3})\.(\d{1,3})$', flags=regex.IGNORECASE)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((3, 1, 0), self.revModel_3_1_0),
            ((3, 2, 0), self.revModel_3_2_0),
            ((3, 3, 0), self.revModel_3_3_0),
        )

    async def revModel_3_2_0(self, layers):
        async with await ModelMigration_3_2_0.anit(self.core, layers) as migr:
            await migr.revModel_3_2_0()

    async def revModel_3_1_0(self, layers):

        def hasBoolType(typ):

            # a prop type is a poly, or an array of one
            if typ.isarray:
                typ = typ.arraytype

            return any(isinstance(t, s_types.Bool) for t in typ.getTypeSet())

        def boolifyTval(tval):

            if tval[0] in boolnames:
                return (tval[0], bool(tval[1]))

            return tval

        def getBoolNorm(valu, stortype):
            # returns the value with bools in place of legacy ints, or None when it already stores bools
            # props are a (type, valu) tuple or an array of them
            if stortype & s_layer.STOR_FLAG_ARRAY:
                norm = tuple(boolifyTval(tval) for tval in valu)
            else:
                norm = boolifyTval(valu)

            if not s_layer.hasBoolDiff(stortype, norm, valu):
                return None

            return norm

        boolnames = {t.name for t in self.core.model.types.values() if isinstance(t, s_types.Bool)}
        props = [p for p in self.core.model.getProps() if not p.isform and not p.isrunt and hasBoolType(p.type)]
        names = {p.name for p in self.core.model.tagprops.values() if isinstance(p.type, s_types.Bool)}

        for layr in layers:

            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

            for prop in props:

                async for rows in s_coro.chunks(layr.liftByProp(prop.form.name, prop.name), size=1000):

                    nodeedits = []
                    for _, nid, sref in rows:

                        curv = sref.sode['props'].get(prop.name)
                        if curv is None or (norm := getBoolNorm(curv[0], curv[1])) is None:
                            continue

                        nodeedits.append((s_common.int64un(nid), prop.form.name, (
                            (s_layer.EDIT_PROP_SET, (prop.name, norm, curv[1], curv[2])),
                        )))

                    if nodeedits:
                        await layr.saveNodeEdits(nodeedits, meta)

            for form, tag, name in list(layr.getTagPropIndexes()):

                if form is None or tag is None or name not in names:
                    continue

                async for rows in s_coro.chunks(layr.liftByTagProp(form, tag, name), size=1000):

                    nodeedits = []
                    for _, nid, sref in rows:

                        tpdict = sref.sode['tagprops'].get(tag)
                        if tpdict is None or (curv := tpdict.get(name)) is None or curv[0].__class__ is bool:
                            continue

                        nodeedits.append((s_common.int64un(nid), form, (
                            (s_layer.EDIT_TAGPROP_SET, (tag, name, bool(curv[0]), curv[1], curv[2])),
                        )))

                    if nodeedits:
                        await layr.saveNodeEdits(nodeedits, meta)

    async def revModel_3_3_0(self, layers):
        await self._delPolyPropTypes(layers, 'it:cloud:host:parent')

    async def _delPolyPropTypes(self, layers, propfull):

        # moves poly prop values whose type the prop no longer accepts into node data
        prop = self.core.model.prop(propfull)
        dataname = f'_migrated:{prop.full}'

        count = 0
        for layr in layers:

            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

            async for rows in s_coro.chunks(layr.liftByProp(prop.form.name, prop.name), size=1000):

                nodeedits = []
                for _, nid, sref in rows:

                    curv = sref.sode['props'].get(prop.name)
                    if curv is None or prop.type.acceptsType(curv[0][0]):
                        continue

                    nodeedits.append((s_common.int64un(nid), prop.form.name, (
                        (s_layer.EDIT_NODEDATA_SET, (dataname, curv[0])),
                        (s_layer.EDIT_PROP_DEL, (prop.name,)),
                    )))

                    ndef = self.core.getNidNdef(nid)
                    logger.warning(f'Removed {prop.full}={curv[0]} (layer: {layr.iden}, node: {ndef}), saved as node data {dataname}',
                                   extra=self.core.getLogExtra(node=ndef, layer=layr.iden))

                if nodeedits:
                    count += len(nodeedits)
                    await layr.saveNodeEdits(nodeedits, meta)

        logger.warning(f'Removed {count} {prop.full} values of a type it no longer accepts, saved as node data {dataname}.')

    async def _uniqSortArray(self, todoprops, layers):

        for layr in layers:

            for propname in todoprops:

                nodeedits = []
                meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

                def sortuniq(valu):
                    return tuple(sorted({v: True for v in valu}.keys()))

                async def save():
                    await layr.storNodeEdits(nodeedits, meta)
                    nodeedits.clear()

                prop = self.core.model.prop(propname)
                if prop is None:
                    logger.warning(f'No property named {propname} to sortuniq().')
                    continue

                propreln = prop.name
                formname = prop.form.name

                stortype = prop.type.stortype | s_layer.STOR_FLAG_ARRAY

                async for nid, propvalu in layr.iterPropRows(formname, propreln):

                    uniqvalu = sortuniq(propvalu)
                    if uniqvalu == propvalu:
                        continue

                    nodeedits.append(
                        (nid, formname, (
                            (s_layer.EDIT_PROP_SET, (propreln, uniqvalu, propvalu, stortype)),
                        )),
                    )

                    if len(nodeedits) >= 1000:
                        await save()

                if nodeedits:
                    await save()

    async def runStorm(self, text, opts=None):
        '''
        Run storm code in a schedcoro and log the output messages.

        Args:
            text (str): Storm query to execute.
            opts: Storm opts.

        Returns:
            None
        '''
        if opts is None:
            opts = {}

        async def _runStorm():
            async for mesgtype, mesginfo in self.core.storm(text, opts=opts):
                if mesgtype == 'print':
                    logger.debug(f'Storm message: {mesginfo.get("mesg")}')
                    continue
                if mesgtype == 'warn': # pragma: no cover
                    logger.warning(f'Storm warning: {mesginfo.get("mesg")}')
                    continue
                if mesgtype == 'err': # pragma: no cover
                    logger.error(f'Storm error: {mesginfo}')

        await self.core.schedCoro(_runStorm())

    async def revCoreLayers(self):

        version = self.revs[-1][0] if self.revs else maxvers

        # do a first pass to detect layers at the wrong version
        # that we are not able to rev ourselves and bail...

        layers = []
        for layr in list(self.core.layers.values()):

            if layr.fresh:
                await layr.setModelVers(version)
                continue

            vers = await layr.getModelVers()
            if vers == version:
                continue

            if not layr.canrev and vers != version:
                mesg = f'layer {layr.__class__.__name__} {layr.iden} ({layr.dirn}) can not be updated.'
                raise s_exc.CantRevLayer(layer=layr.iden, mesg=mesg, curv=version, layv=vers)

            if vers > version:
                mesg = f'layer {layr.__class__.__name__} {layr.iden} ({layr.dirn}) is from the future!'
                raise s_exc.CantRevLayer(layer=layr.iden, mesg=mesg, curv=version, layv=vers)

            # realistically all layers are probably at the same version... but...
            layers.append(layr)

        # got anything to do?
        if not layers:
            return

        for revvers, revmeth in self.revs:

            todo = [lyr for lyr in layers if await lyr.getModelVers() < revvers]
            if not todo:
                continue

            logger.warning(f'beginning model migration -> {revvers}')

            await revmeth(todo)

            [await lyr.setModelVers(revvers) for lyr in todo]

        logger.warning('...model migrations complete!')

    async def _normPropValu(self, layers, propfull):  # pragma: no cover

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            prop = self.core.model.prop(propfull)

            async for nid, propvalu in layr.iterPropRows(prop.form.name, prop.name):
                try:
                    norm, info = await prop.type.norm(propvalu)
                except s_exc.BadTypeValu as e:
                    nodeedits.append(
                        (nid, prop.form.name, (
                            (s_layer.EDIT_NODEDATA_SET, (f'_migrated:{prop.full}', propvalu, None)),
                            (s_layer.EDIT_PROP_DEL, (prop.name, propvalu, prop.type.stortype)),
                        )),
                    )
                    oldm = e.errinfo.get('mesg')
                    ndef = self.core.getNidNdef(nid)
                    logger.warning(f'error re-norming {prop.form.name}:{prop.name}={propvalu} (layer: {layr.iden}, node: {ndef}): {oldm}',
                                   extra=self.core.getLogExtra(node=ndef, layer=layr.iden))
                    continue

                if norm == propvalu:
                    continue

                nodeedits.append(
                    (nid, prop.form.name, (
                        (s_layer.EDIT_PROP_SET, (prop.name, norm, propvalu, prop.type.stortype)),
                    )),
                )

                if len(nodeedits) >= 1000:  # pragma: no cover
                    await save()

            if nodeedits:
                await save()

    async def _updatePropStortype(self, layers, propfull):

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            prop = self.core.model.prop(propfull)
            stortype = prop.type.stortype

            async for lkey, nid, sode in layr.liftByProp(prop.form.name, prop.name):

                props = sode.get('props')

                # this should be impossible, but has been observed in the wild...
                if props is None: # pragma: no cover
                    continue

                curv = props.get(prop.name)
                if curv is None or curv[1] == stortype:
                    continue

                nodeedits.append(
                    (nid, prop.form.name, (
                        (s_layer.EDIT_PROP_SET, (prop.name, curv[0], curv[0], stortype)),
                    )),
                )

                if len(nodeedits) >= 1000:  # pragma: no cover
                    await save()

            if nodeedits:
                await save()

    async def _normFormSubs(self, layers, formname, liftprop=None, cmprvalu=s_common.novalu, cmpr='='):

        # NOTE: this API may be used to re-normalize subs but *not* to change their storage types
        # and will *not* auto-populate linked forms from subs which are form types.

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        subprops = {}

        form = self.core.model.form(formname)

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            if cmprvalu is s_common.novalu:
                # This is for lifts such as:
                #   <formname>
                #   <formname>:<liftprop>
                # E.g.:
                #   inet:ipv4
                #   inet:ipv4:type
                genr = layr.liftByProp(form.name, liftprop)

            elif liftprop is None:
                # This is for lifts such as:
                #   <formname><cmpr><cmprvalu>
                # E.g.:
                #   inet:ipv4=1.2.3.4

                # Don't norm cmprvalu first because it may not be normable
                cmprvals = form.type.getStorCmprs(cmpr, cmprvalu)
                genr = layr.liftByFormValu(form.name, cmprvals)

            else: # liftprop is not None  # pragma: no cover
                # This is for lifts such as:
                #   <formname>:<liftprop><cmpr><cmprvalu>
                # E.g.:
                #   inet:ipv4:type=private

                # Don't norm cmprvalu first because it may not be normable
                cmprvals = form.type.getStorCmprs(cmpr, cmprvalu)
                genr = layr.liftByPropValu(form.name, liftprop, cmprvals)

            async for _, nid, sode in genr:

                sodevalu = sode.get('valu')
                if sodevalu is None: # pragma: no cover
                    continue

                formvalu = sodevalu[0]

                try:
                    norm, info = await form.type.norm(formvalu)
                except s_exc.BadTypeValu as e: # pragma: no cover
                    oldm = e.errinfo.get('mesg')
                    logger.warning(f'Skipping {formname}={formvalu} : {oldm}')
                    continue

                edits = []
                subs = info.get('subs')
                if subs is not None:

                    for subname, subvalu in subs.items():

                        subprop = subprops.get(subname, s_common.novalu)
                        if subprop is s_common.novalu:
                            subprop = subprops[subname] = self.core.model.prop(f'{formname}:{subname}')

                        if subprop is None: # pragma: no cover
                            continue

                        try:
                            subnorm, subinfo = await subprop.type.norm(subvalu)
                        except s_exc.BadTypeValu as e: # pragma: no cover
                            oldm = e.errinfo.get('mesg')
                            logger.warning(f'error norming subvalue {subprop.full}={subvalu}: {oldm}')
                            continue

                        props = sode.get('props')
                        if props is None: # pragma: no cover
                            continue

                        subcurv = props.get(subprop.name)
                        if subcurv is not None:
                            if subcurv[1] != subprop.type.stortype: # pragma: no cover
                                logger.warning(f'normFormSubs() may not be used to change storage types for {subprop.full}')
                                continue
                            subcurv = subcurv[0]

                        if subcurv == subnorm:
                            continue

                        edits.append((s_layer.EDIT_PROP_SET, (subprop.name, subnorm, subcurv, subprop.type.stortype)))

                    if not edits: # pragma: no cover
                        continue

                    nodeedits.append((nid, formname, edits))

                    if len(nodeedits) >= 1000:  # pragma: no cover
                        await save()

            if nodeedits:
                await save()

    async def _propToForm(self, layers, propfull, formname):

        opts = {'vars': {
            'layridens': [layr.iden for layr in layers],
            'formname': formname,
            'propfull': propfull,
            'propname': self.core.model.prop(propfull).name,
        }}

        storm = '''
        $layers = $lib.set()
        $layers.adds($layridens)

        for $view in $lib.view.list(deporder=(true)) {

            if (not $layers.has($view.layers.0.iden)) { continue }

            view.exec $view.iden {
                yield $lib.layer.get().liftByProp($propfull)
                [ *$formname=$node.props.get($propname) ]
            }
        }
        '''
        await self.runStorm(storm, opts=opts)

    async def _typeToForm(self, layers, typename, formname):
        for prop in layers[0].core.model.getPropsByType(typename):
            await self._propToForm(layers, prop.full, formname)

    async def _propArrayToForm(self, layers, propfull, formname):

        opts = {'vars': {
            'layridens': [layr.iden for layr in layers],
            'formname': formname,
            'propfull': propfull,
            'propname': self.core.model.prop(propfull).name,
        }}

        storm = '''
        $layers = $lib.set()
        $layers.adds($layridens)

        for $view in $lib.view.list(deporder=(true)) {

            if (not $layers.has($view.layers.0.iden)) { continue }

            view.exec $view.iden {

                yield $lib.layer.get().liftByProp($propfull)
                for $item in $node.props.get($propname) {
                    [ *$formname=$item ]
                }

            }
        }
        '''
        await self.runStorm(storm, opts=opts)

class ModelMigrationBase(s_base.Base):
    '''
    Shared machinery for a model migration which repairs nodes stored with values or
    properties an earlier version of Synapse should not have accepted.

    A node which can be repaired is renamed to its corrected value with a NodeFuser, which
    carries its props, tags, tag properties, node data, light edges and references over
    in each layer, and a node which cannot be repaired is removed and recorded in the
    migration's own queue so it may be reviewed and repaired by hand.

    A model migration runs in migration mode on exactly the layers ModelRev passes it,
    which may include read only layers. Every write goes through Layer.saveNodeEdits() or
    the Cortex queue APIs, so a mirror replays the same edits, and a migration which is
    interrupted before ModelRev records the new model version runs again on the next boot
    and finishes what it started: every step is computed from the state it finds rather
    than from a record of what the previous run did.
    '''
    queuename = None

    async def __anit__(self, core, layers):

        await s_base.Base.__anit__(self)

        self.core = core
        self.model = core.model
        self.layers = list(layers)
        self.layridens = {layr.iden for layr in self.layers}

        self.useriden = core.auth.rootuser.iden
        self.meta = {'time': s_common.now(), 'user': self.useriden}

        self.migrname = self.queuename.split(':')[0]

        # the (form, valu) of every node already recorded in the queue, so a migration
        # which runs again after an interruption does not record a node twice
        self.queued = await s_spooled.Set.anit(dirn=core.dirn, cell=core)
        self.onfini(self.queued)

        self.queueiden = None

        self.editor = s_editor.MigrationEditor(core, core.auth.rootuser)

        qdef = await core.getCoreQueueByName(self.queuename)
        if qdef is not None:
            self.queueiden = qdef.get('iden')
            async for (_, item) in core.coreQueueGets(self.queueiden, 0, cull=False, wait=False):
                await self.queued.add(s_common.tuplify((item.get('form'), item.get('valu'))))

    async def _reqQueue(self):

        if self.queueiden is None:
            qdef = await self.core.addCoreQueue({'name': self.queuename, 'creator': self.useriden})
            self.queueiden = qdef.get('iden')

        return self.queueiden

    async def getComputedProps(self, formname, valu):
        '''
        Return {name: (valu, stortype, virts)} for the computed props of a value.
        '''
        nodeedits = await self.editor.getNewNodeEdits(formname, valu)

        retn = {}
        for (etyp, edit) in nodeedits[0][2]:
            if etyp == s_layer.EDIT_PROP_SET:
                retn[edit[0]] = tuple(edit[1:])

        return retn

    async def saveNodeEdits(self, layr, nodeedits):
        for chunk in s_nodefuse.iterEditChunks(nodeedits):
            await layr.saveNodeEdits(chunk, self.meta)

    async def addNodeAdds(self, layr, formname, valu):
        '''
        Add the nodes a value adds (such as the inet:fqdn of an inet:url) to a layer which
        will hold that value, unless the layer already holds them.
        '''
        nodeedits = await self.editor.getNewNodeEdits(formname, valu, layr=layr)
        if len(nodeedits) > 1:
            await self.saveNodeEdits(layr, nodeedits[1:])

    async def fixComputedProps(self, formname, valu, computed=None):
        '''
        Set every computed prop of a node to the one its value derives, in every layer
        which holds its value.

        Returns:
            int: The number of layers in which a computed prop was changed.
        '''
        form = self.model.form(formname)

        nid = self.core.getNidByNdef((formname, valu))
        if nid is None:
            return 0

        if computed is None:
            computed = await self.getComputedProps(formname, valu)

        names = [p.name for p in form.props.values() if p.info.get('computed')]

        count = 0
        for layr in self.layers:

            sode = layr.getStorNode(nid)
            if sode.get('valu') is None:
                continue

            # defensive: a node whose value derives computed props is stored with them
            props = sode.get('props')
            if props is None:  # pragma: no cover
                props = {}

            edits = []
            for name in names:

                curv = props.get(name)
                newv = computed.get(name)

                if newv is None:
                    if curv is not None:
                        edits.append((s_layer.EDIT_PROP_DEL, (name,)))
                    continue

                if curv is None or tuple(curv) != tuple(newv):
                    edits.append((s_layer.EDIT_PROP_SET, (name, newv[0], newv[1], newv[2])))

            if not edits:
                continue

            count += 1

            await self.addNodeAdds(layr, formname, valu)
            await self.saveNodeEdits(layr, [(s_common.int64un(nid), formname, edits)])

        return count

    async def getRefs(self, ndef):
        '''
        Yield (layr, refnid, prop, isarray, reftyp) for every reference to a node in the
        layers this migration repairs.
        '''
        for layr in self.layers:
            async for (refnid, prop, isarray, reftyp) in s_nodefuse.iterLayerRefs(self.core, layr, ndef):
                yield layr, refnid, prop, isarray, reftyp

    def isCompSlot(self, prop):
        '''
        Return whether a prop restates a slot of its own form's comp primary value.
        '''
        if not prop.info.get('computed') or not isinstance(prop.form.type, s_types.Comp):
            return False

        return prop.name in [name for (name, _) in prop.form.type.opts['fields']]

    def getNodeValu(self, nid):
        '''
        Return the primary value of a node by nid, from any layer, or None.
        '''
        ndef = self.core.getNidNdef(nid)
        if ndef is not None:
            return ndef[1]

    async def captureNode(self, ndef, reason, mesg):
        '''
        Return the queue item recording everything a node holds in the layers this
        migration repairs, so it may be reviewed and repaired by hand.

        Values are recorded rather than nids or stortypes, which are specific to this
        Cortex and to the shape of the value: repairNode() derives them again. The
        tombstones each layer holds for the node are recorded with it, since removing the
        node deletes them too.
        '''
        nid = self.core.getNidByNdef(ndef)

        item = {
            'form': ndef[0],
            'valu': ndef[1],
            'reason': reason,
            'mesg': mesg,
            'time': self.meta['time'],
            'layers': {},
            'refs': [],
            'sources': [],
        }

        form = self.model.form(ndef[0])

        sources = set()

        for layr in self.layers:

            sode = layr.getStorNode(nid)
            if sode.get('form') is None:
                continue

            # what this layer deleted from the layers below it, so a fork does not see
            # them again once the node is repaired
            tombs = {
                'valu': sode.get('antivalu') is not None,
                'props': [],
                'tags': [],
                'tagprops': {},
                'nodedata': [],
                'n1edges': [],
                'n2edges': [],
            }

            if (antitags := sode.get('antitags')) is not None:
                tombs['tags'] = sorted(antitags.keys())

            if (antitagprops := sode.get('antitagprops')) is not None:
                tombs['tagprops'] = {tag: sorted(names.keys()) for (tag, names) in antitagprops.items()}

            props = {}
            if (sprops := sode.get('props')) is not None:
                for name, valt in sprops.items():
                    prop = form.props.get(name)
                    if prop is not None and prop.info.get('computed'):
                        continue
                    props[name] = valt[0]

            if (antiprops := sode.get('antiprops')) is not None:
                for name in antiprops.keys():
                    prop = form.props.get(name)
                    if prop is not None and prop.info.get('computed'):
                        continue
                    tombs['props'].append(name)

            tagprops = {}
            if (stagprops := sode.get('tagprops')) is not None:
                for tag, tprops in stagprops.items():
                    tagprops[tag] = {name: valt[0] for (name, valt) in tprops.items()}

            nodedata = []
            async for abrv, valu, tomb in layr.iterNodeData(nid):

                name = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    tombs['nodedata'].append(name)
                    continue

                nodedata.append((name, valu))

            n1edges = []
            async for abrv, n2nid, tomb in layr.iterNodeEdgesN1(nid):

                n2ndef = self.core.getNidNdef(n2nid)
                if n2ndef is None:  # pragma: no cover
                    continue

                verb = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    tombs['n1edges'].append((verb, n2ndef))
                    continue

                n1edges.append((verb, n2ndef))

            n2edges = []
            async for abrv, n1nid, tomb in layr.iterNodeEdgesN2(nid):

                n1ndef = self.core.getNidNdef(n1nid)
                if n1ndef is None:  # pragma: no cover
                    continue

                verb = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    tombs['n2edges'].append((verb, n1ndef))
                    continue

                n2edges.append((verb, n1ndef))

                if verb == 'seen' and n1ndef[0] == 'meta:source':
                    sources.add(n1ndef[1])

            meta = {}
            if (smeta := sode.get('meta')) is not None and (created := smeta.get('created')) is not None:
                meta['created'] = created[0]

            tags = {}
            if (stags := sode.get('tags')) is not None:
                tags = dict(stags)

            item['layers'][layr.iden] = {
                'valu': sode.get('valu') is not None,
                'meta': meta,
                'props': props,
                'tags': tags,
                'tagprops': tagprops,
                'nodedata': nodedata,
                'n1edges': n1edges,
                'n2edges': n2edges,
                'tombs': tombs,
            }

        async for (layr, refnid, prop, isarray, reftyp) in self.getRefs(ndef):
            refndef = self.core.getNidNdef(refnid)
            if refndef is None:  # pragma: no cover
                continue
            item['refs'].append((layr.iden, refndef, prop.full, isarray, self.isCompSlot(prop)))

        item['sources'] = sorted(sources)

        return item

    async def recordNode(self, ndef, reason, mesg):
        '''
        Record a node in the queue, unless an earlier run already recorded it.

        Args:
            ndef (tuple): The (form, valu) of the node to record.
            reason (str): Why the node is removed, "remove" or "comp".
            mesg (str): The error the corrected value raised, if any.
        '''
        if self.queued.has(ndef):
            return

        item = await self.captureNode(ndef, reason, mesg)
        await self.core.coreQueuePuts(await self._reqQueue(), (item,))
        await self.queued.add(ndef)

    async def removeNode(self, ndef, reason, mesg, removing):
        '''
        Record a node in the queue, clear every reference to it, and delete it from every
        layer this migration repairs.

        A computed comp slot which names the node is not cleared, since the comp node it
        belongs to is itself in removing, and is removed ahead of it.

        Args:
            ndef (tuple): The (form, valu) of the node to remove.
            reason (str): Why the node is removed, "remove" or "comp".
            mesg (str): The error the corrected value raised, if any.
            removing (Dict): The ndefs of every node this migration removes.
        '''
        nid = self.core.getNidByNdef(ndef)
        if nid is None:  # pragma: no cover
            return

        await self.recordNode(ndef, reason, mesg)

        form = self.model.form(ndef[0])

        async for (layr, refnid, prop, isarray, reftyp) in self.getRefs(ndef):

            # defensive: the comps which embed the node were removed ahead of it
            if self.isCompSlot(prop):  # pragma: no cover
                continue

            refndef = self.core.getNidNdef(refnid)
            if refndef is None or removing.has(refndef):  # pragma: no cover
                continue

            if prop.info.get('computed'):  # pragma: no cover
                logger.warning(f'{self.migrname} cannot clear computed property {prop.full} on '
                               f'{refndef[0]}={refndef[1]!r}, which references {ndef[0]}={ndef[1]!r}.')
                continue

            sode = layr.getStorNode(refnid)
            if (props := sode.get('props')) is None or (curv := props.get(prop.name)) is None:  # pragma: no cover
                continue

            edits = [(s_layer.EDIT_PROP_DEL, (prop.name,))]

            if isarray:
                newv = [v for v in curv[0] if not (v[1] == ndef[1] and v[0] in form.formtypes)]
                if newv:
                    try:
                        newv = (await prop.type.normFromTypedValu(newv))[0]
                    except Exception as e:  # pragma: no cover
                        logger.warning(f'{self.migrname} cannot re-normalize {prop.full} on '
                                       f'{refndef[0]}={refndef[1]!r}: {e}')
                        newv = tuple(newv)

                    (stortype, virts) = prop.type.getStorInfo(newv)
                    edits = [(s_layer.EDIT_PROP_SET, (prop.name, newv, stortype, virts))]

            await self.saveNodeEdits(layr, [(s_common.int64un(refnid), refndef[0], edits)])

        for layr in self.layers:
            await layr.delStorNode(nid, self.meta)

class UrlFuser(s_nodefuse.NodeFuser):
    '''
    A NodeFuser which renames a bad inet:url node to its corrected value for the 3.2.0
    model migration.
    '''
    async def __anit__(self, core, useriden, migr):

        await s_nodefuse.NodeFuser.__anit__(self, core, useriden, layers=migr.layers, keeptombs=True)

        self.migr = migr

        # {(layriden, dstnid): {kind: {key: valu}}} for the layer being processed
        self.conflicts = {}

    def _remapCompSlotValu(self, form, prop, valu):

        # another bad URL in the same comp is substituted with its own corrected value
        # rather than re-normalized, which would either fail or rename it out from
        # under its own move
        if valu[0] == 'inet:url':
            newv = self.migr.slotmoves.get(valu[1])
            if newv is not None:
                return ('inet:url', newv)

        return s_nodefuse.NodeFuser._remapCompSlotValu(self, form, prop, valu)

    async def _getSeedComputed(self, dstnid, dstform, dstndef):
        if dstform.name != 'inet:url':  # pragma: no cover
            return {}

        return await self.migr.getComputedProps(dstform.name, dstndef[1])

    async def _onConflict(self, layer, dstnid, dstform, kind, key, valu):

        if kind == 'nodedata':
            (_, dstvalu, _) = await layer.getNodeData(dstnid, key)
            if dstvalu == valu:
                return

        info = self.conflicts.setdefault((layer.iden, dstnid), {})

        if kind == 'tagprops':
            (tag, name) = key
            info.setdefault(kind, {}).setdefault(tag, {})[name] = valu
            return

        info.setdefault(kind, {})[key] = valu

    async def _flushConflicts(self, layer, srcndef, dstnid, dstform):

        info = self.conflicts.pop((layer.iden, dstnid), None)
        if info is None:
            return

        name = self.migr.migrname

        (ok, curv, tomb) = await layer.getNodeData(dstnid, name)
        if not ok or tomb or not isinstance(curv, dict):
            curv = {}

        srcform = self.model.form(srcndef[0])
        curv[srcform.type.repr(srcndef[1])] = info

        await self._addEdit(dstnid, dstform.name, (
            (s_layer.EDIT_NODEDATA_SET, (name, curv)),
        ))

class ModelMigration_3_2_0(ModelMigrationBase):
    '''
    Repair inet:url nodes stored by an inet:url normalizer which relied on assert
    statements, which python -O strips, and which misparsed the URL authority.

    Each affected node is renamed to its corrected value, has its computed properties
    set from its value, or is removed and recorded in the model_3_2_0:nodes queue.
    '''
    queuename = 'model_3_2_0:nodes'

    async def __anit__(self, core, layers):

        await ModelMigrationBase.__anit__(self, core, layers)

        self.form = self.model.form('inet:url')

        # {valu: (verdict, newvalu, mesg)} for every inet:url this migration changes
        self.verdicts = await s_spooled.Dict.anit(dirn=core.dirn, cell=core)
        self.onfini(self.verdicts)

        # {valu: newvalu} for every inet:url this migration renames
        self.slotmoves = await s_spooled.Dict.anit(dirn=core.dirn, cell=core)
        self.onfini(self.slotmoves)

        # {ndef: depth} for every node this migration removes, including comps which embed
        # one, where depth is the number of comps between the node and the inet:url
        self.removing = await s_spooled.Dict.anit(dirn=core.dirn, cell=core)
        self.onfini(self.removing)

    async def _getNormVerdict(self, candidate, valu):
        '''
        Return the verdict for a value given what it should have been stored as.
        '''
        try:
            (newvalu, _) = await self.form.type.norm(candidate)
        except s_exc.BadTypeValu as e:
            return ('remove', None, e.get('mesg'))

        if newvalu == valu:
            return ('fixprops', None, None)

        # a value which only normalizes to itself on a second pass would be renamed again
        # by the next migration rather than being repaired by this one
        try:
            (again, _) = await self.form.type.norm(newvalu)
        except s_exc.BadTypeValu as e:  # pragma: no cover
            return ('remove', None, e.get('mesg'))

        if again != newvalu:  # pragma: no cover
            return ('remove', None, f'{newvalu!r} does not normalize to itself.')

        return ('move', newvalu, None)

    async def _getVerdict(self, valu, props):
        '''
        Return (verdict, newvalu, mesg) for an inet:url node, or None if it is valid.

        The cheap string checks select candidates, and only a candidate is normalized. The
        verdict is "move" when the value normalizes to a different one, "fixprops" when the
        value is valid but its computed properties may not be, and "remove" when it does
        not normalize at all.
        '''
        def getProp(name):
            valt = props.get(name)
            if valt is not None:
                return valt[0][1]

        # the normalizer running with asserts stripped stored values such as
        # <scheme>:////<rest>, where <scheme> contains no ://. a value whose first :// is
        # not preceded by a valid scheme, such as file:/x?u=http:////y, is checked below
        scheme, sep, rest = valu.partition('://')
        if sep and rest.startswith('//') and scheme != 'file' and s_inet.schemere.fullmatch(scheme):

            if scheme not in s_scrape.urilist:
                return ('remove', None, f'Unknown scheme {scheme!r} with an empty authority.')

            return await self._getNormVerdict(f'{scheme}://{rest[2:]}', valu)

        # :proto was taken from a URL embedded in the path or query
        proto = getProp('proto')
        if proto is not None and '://' in proto:
            return await self._getNormVerdict(valu, valu)

        if sep and not s_inet.schemere.fullmatch(scheme.lower()):
            return await self._getNormVerdict(valu, valu)

        # a # in the userinfo was taken as part of it, rather than ending the host
        username = getProp('username')
        passwd = getProp('passwd')
        if username == '' or (username is not None and '#' in username) or (passwd is not None and '#' in passwd):
            return await self._getNormVerdict(valu, valu)

        if valu.startswith('file:'):

            rest = valu[5:].lstrip('/')
            offs = len(valu) - len(rest)

            hostlen = len(rest)
            for char in '/?#':
                if (indx := rest.find(char)) != -1:
                    hostlen = min(hostlen, indx)

            host = rest[:hostlen]
            if '@' in host:

                # a Windows WebDAV host suffix whose port was stored as an IPv4 host
                match = urldavre.search(host)
                if match is not None:
                    port = int(match.group(2)) * 256 + int(match.group(3))
                    ssl = f'@{match.group(1)}' if match.group(1) else ''
                    host = f'{host[:match.start()]}{ssl}@{port}'

                return await self._getNormVerdict(valu[:offs] + host + rest[hostlen:], valu)

        return None

    async def _scanLayers(self):

        for layr in self.layers:

            async for nid, sode in layr.getStorNodesByForm('inet:url'):

                valt = sode.get('valu')
                if valt is None:
                    # a layer which only holds tags, props or node data for the node, which
                    # is also how one is left if a previous run was interrupted between
                    # renaming a node in one layer and another
                    valu = self.getNodeValu(nid)
                    if valu is None:  # pragma: no cover
                        continue
                else:
                    valu = valt[0]

                if self.verdicts.get(valu) is not None:
                    continue

                props = sode.get('props')
                if props is None:
                    props = {}

                verdict = await self._getVerdict(valu, props)
                if verdict is None:
                    continue

                await self.verdicts.set(valu, verdict)

    async def _addRemoving(self, ndef):
        '''
        Add a node to the removal set, along with every comp node which embeds it.

        Each node is added with its depth, the number of comps between it and the given
        node, so that a comp can be removed before the nodes its value embeds. A comp
        reached by more than one path keeps the greatest depth.

        Returns:
            list: The (ndef, depth) of each node added, the node itself first.
        '''
        added = {}

        todo = [(ndef, 0)]
        while todo:

            (ndef, depth) = todo.pop()

            curv = self.removing.get(ndef)
            if curv is not None and curv >= depth:
                continue

            await self.removing.set(ndef, depth)
            added[ndef] = depth

            async for (layr, refnid, prop, isarray, reftyp) in self.getRefs(ndef):

                if not self.isCompSlot(prop):
                    continue

                refndef = self.core.getNidNdef(refnid)
                if refndef is not None:
                    todo.append((s_common.tuplify(refndef), depth + 1))

        return list(added.items())

    async def _removeNodes(self, getItems, mesg=None):
        '''
        Record every node in the queue, then remove each one, a comp before the nodes its
        value embeds.

        A rerun finds the comps to remove through the inet:url they embed. Recording every
        node first, and removing that inet:url last, means a migration interrupted part way
        through still finds each comp it has not removed yet, and its record of the
        inet:url still names every comp it was removed with.

        Args:
            getItems (callable): Returns an iterator of the (ndef, depth) of each node.
            mesg (str): The error recorded for each node, or None to record the verdict
                of an inet:url and none for a comp.

        Returns:
            int: The number of nodes removed.
        '''
        def getReason(ndef):
            if ndef[0] == 'inet:url':
                return ('remove', mesg if mesg is not None else self.verdicts.get(ndef[1])[2])
            return ('comp', mesg)

        maxdepth = 0
        async for (ndef, depth) in s_coro.pause(getItems()):
            ndef = s_common.tuplify(ndef)
            await self.recordNode(ndef, *getReason(ndef))
            maxdepth = max(maxdepth, depth)

        removed = 0
        for depth in range(maxdepth, -1, -1):

            async for (ndef, ndepth) in s_coro.pause(getItems()):

                if ndepth != depth:
                    continue

                ndef = s_common.tuplify(ndef)
                await self.removeNode(ndef, *getReason(ndef), self.removing)
                removed += 1

        return removed

    async def revModel_3_2_0(self):

        await self._scanLayers()

        if not len(self.verdicts):
            logger.warning('model_3_2_0 found no inet:url nodes to repair.')
            return

        async for valu, (verdict, newvalu, mesg) in s_coro.pause(self.verdicts.items()):
            if verdict == 'remove':
                await self._addRemoving(('inet:url', valu))
            elif verdict == 'move':
                await self.slotmoves.set(valu, newvalu)

        removed = await self._removeNodes(self.removing.items)

        fixed = 0
        moved = 0
        failed = []

        async for valu, (verdict, newvalu, mesg) in s_coro.pause(self.verdicts.items()):

            if verdict == 'fixprops':
                fixed += bool(await self.fixComputedProps('inet:url', valu))
                continue

            if verdict != 'move':
                continue

            srcnid = self.core.getNidByNdef(('inet:url', valu))

            sodes = [(layr, layr.getStorNode(srcnid)) for layr in self.layers]
            if not any(sode.get('form') is not None for (layr, sode) in sodes):  # pragma: no cover
                continue

            for (layr, sode) in sodes:
                if sode.get('valu') is not None:
                    await self.addNodeAdds(layr, 'inet:url', newvalu)

            async with await UrlFuser.anit(self.core, self.useriden, self) as fuser:

                try:
                    await fuser.getLayerEdits(('inet:url', valu), ('inet:url', newvalu))
                except s_exc.BadTypeValu as e:
                    # renaming a comp which embeds this node would produce an invalid
                    # comp value, so nothing was renamed and it is recorded instead
                    fusemesg = e.get('mesg')

                else:
                    fusemesg = None
                    await fuser.applyLayerEdits(self.meta)
                    failed.extend(fuser.getResult()['failed'])

            if fusemesg is not None:
                added = await self._addRemoving(('inet:url', valu))
                removed += await self._removeNodes(lambda: added, mesg=fusemesg)
                continue

            await self.fixComputedProps('inet:url', newvalu)
            moved += 1

        logger.warning(f'model_3_2_0 repaired inet:url nodes: {moved} moved, {fixed} re-normalized, '
                       f'{removed} removed and recorded in the {self.queuename} queue.')

        if failed:
            mesg = f'model_3_2_0 could not apply its edits to every layer: {failed}'
            raise s_exc.SynErr(mesg=mesg, failed=failed)
