import regex
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.layer as s_layer

logger = logging.getLogger(__name__)

maxvers = (0, 2, 26)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = ()

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

        # Migrations only run on leaders
        opts['mirror'] = False

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
        for layr in self.core.layers.values():

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

    async def _normPropValu(self, layers, propfull):

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            prop = self.core.model.prop(propfull)

            async for nid, propvalu in layr.iterPropRows(prop.form.name, prop.name):
                try:
                    norm, info = prop.type.norm(propvalu)
                except s_exc.BadTypeValu as e:
                    nodeedits.append(
                        (nid, prop.form.name, (
                            (s_layer.EDIT_NODEDATA_SET, (f'_migrated:{prop.full}', propvalu, None)),
                            (s_layer.EDIT_PROP_DEL, (prop.name, propvalu, prop.type.stortype)),
                        )),
                    )
                    oldm = e.errinfo.get('mesg')
                    iden = s_common.ehex(self.core.getBuidByNid(nid))
                    logger.warning(f'error re-norming {prop.form.name}:{prop.name}={propvalu} (layer: {layr.iden}, node: {iden}): {oldm}',
                                   extra={'synapse': {'node': iden, 'layer': layr.iden}})
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

    async def _normVelocityProps(self, layers, form, props):

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            async for buid, formvalu in layr.iterFormRows(form):
                sode = layr._getStorNode(buid)
                if (nodeprops := sode.get('props')) is None:
                    continue

                for prop in props:
                    if (curv := nodeprops.get(prop.name)) is None:
                        continue

                    propvalu = curv[0]
                    if prop.type.isarray:
                        hasfloat = False
                        strvalu = []
                        for valu in propvalu:
                            if isinstance(valu, float):
                                strvalu.append(str(valu))
                                hasfloat = True

                        if not hasfloat:
                            continue
                    else:
                        if not isinstance(propvalu, float):
                            continue
                        strvalu = str(propvalu)

                    nodeprops.pop(prop.name)

                    try:
                        norm, info = prop.type.norm(strvalu)
                    except s_exc.BadTypeValu as e:
                        nodeedits.append(
                            (buid, form, (
                                (s_layer.EDIT_NODEDATA_SET, (f'_migrated:{prop.full}', propvalu, None), ()),
                                (s_layer.EDIT_PROP_DEL, (prop.name, propvalu, prop.type.stortype), ()),
                            )),
                        )

                        oldm = e.errinfo.get('mesg')
                        iden = s_common.ehex(buid)
                        logger.warning(f'error re-norming {prop.full}={propvalu} (layer: {layr.iden}, node: {iden}): {oldm}',
                                       extra={'synapse': {'node': iden, 'layer': layr.iden}})
                        continue

                    nodeedits.append(
                        (buid, form, (
                            (s_layer.EDIT_PROP_SET, (prop.name, norm, propvalu, prop.type.stortype), ()),
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
                    norm, info = form.type.norm(formvalu)
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
                            subnorm, subinfo = subprop.type.norm(subvalu)
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

        for $view in $lib.view.list(deporder=$lib.true) {

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

        for $view in $lib.view.list(deporder=$lib.true) {

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
