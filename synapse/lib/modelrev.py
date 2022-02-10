import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

maxvers = (0, 2, 7)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((0, 2, 1), self.revModel20210126),
            ((0, 2, 2), self.revModel20210312),
            ((0, 2, 3), self.revModel20210528),
            ((0, 2, 5), self.revModel20210801),
            ((0, 2, 6), self.revModel20211112),
            ((0, 2, 7), self.revModel20220202),
        )

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

                async for buid, propvalu in layr.iterPropRows(formname, propreln):

                    uniqvalu = sortuniq(propvalu)
                    if uniqvalu == propvalu:
                        continue

                    nodeedits.append(
                        (buid, formname, (
                            (s_layer.EDIT_PROP_SET, (propreln, uniqvalu, propvalu, stortype), ()),
                        )),
                    )

                    if len(nodeedits) >= 1000:
                        await save()

                if nodeedits:
                    await save()

    async def revModel20211112(self, layers):
        # uniq and sort several array types
        todoprops = (
            'biz:rfp:requirements',

            'crypto:x509:cert:ext:sans',
            'crypto:x509:cert:ext:crls',
            'crypto:x509:cert:identities:fqdns',
            'crypto:x509:cert:identities:emails',
            'crypto:x509:cert:identities:ipv4s',
            'crypto:x509:cert:identities:ipv6s',
            'crypto:x509:cert:identities:urls',
            'crypto:x509:cert:crl:urls',

            'inet:whois:iprec:contacts',
            'inet:whois:iprec:links',
            'inet:whois:ipcontact:roles',
            'inet:whois:ipcontact:links',
            'inet:whois:ipcontact:contacts',

            'it:account:groups',
            'it:group:groups',

            'it:reveng:function:impcalls',
            'it:reveng:filefunc:funccalls',

            'it:sec:cve:references',

            'risk:vuln:cwes',

            'tel:txtmesg:recipients',
        )
        await self._uniqSortArray(todoprops, layers)

    async def revModel20210801(self, layers):

        # uniq and sort several array types
        todoprops = (
            'edu:course:prereqs',
            'edu:class:assistants',

            'ou:org:subs',
            'ou:org:names',
            'ou:org:dns:mx',
            'ou:org:locations',
            'ou:org:industries',

            'ou:industry:sic',
            'ou:industry:subs',
            'ou:industry:isic',
            'ou:industry:naics',

            'ou:preso:sponsors',
            'ou:preso:presenters',

            'ou:conference:sponsors',
            'ou:conference:event:sponsors',
            'ou:conference:attendee:roles',
            'ou:conference:event:attendee:roles',

            'ou:contract:types',
            'ou:contract:parties',
            'ou:contract:requirements',
            'ou:position:reports',

            'ps:person:names',
            'ps:person:nicks',
            'ps:persona:names',
            'ps:persona:nicks',
            'ps:education:classes',
            'ps:contactlist:contacts',
        )
        await self._uniqSortArray(todoprops, layers)

    async def revModel20210528(self, layers):

        cmdtype = self.core.model.type('it:cmd')
        cmdprop = self.core.model.prop('it:exec:proc:cmd')

        for layr in layers:

            done = set()
            nodeedits = []

            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                done.clear()
                nodeedits.clear()

            async for buid, propvalu in layr.iterPropRows('it:exec:proc', 'cmd'):

                cmdnorm = cmdtype.norm(propvalu)[0]

                if cmdnorm != propvalu:
                    nodeedits.append(
                        (buid, 'it:exec:proc', (
                            (s_layer.EDIT_PROP_SET, ('cmd', cmdnorm, propvalu, s_layer.STOR_TYPE_UTF8), ()),
                        )),
                    )

                if cmdnorm not in done:
                    cmdbuid = s_common.buid(('it:cmd', cmdnorm))
                    nodeedits.append(
                        (cmdbuid, 'it:cmd', (
                            (s_layer.EDIT_NODE_ADD, (cmdnorm, s_layer.STOR_TYPE_UTF8), ()),
                        )),
                    )
                    done.add(cmdnorm)

                if len(nodeedits) >= 1000:
                    await save()

            if nodeedits:
                await save()

    async def revModel20210312(self, layers):

        ipv4type = self.core.model.type('inet:ipv4')
        ipv6type = self.core.model.type('inet:ipv6')

        for layr in layers:

            nodeedits = []
            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            async for buid, propvalu in layr.iterPropRows('inet:web:acct', 'signup:client:ipv6'):

                ipv6text = ipv6type.norm(ipv4type.repr(propvalu))[0]
                nodeedits.append(
                    (buid, 'inet:web:acct', (
                        (s_layer.EDIT_PROP_SET, ('signup:client:ipv6', ipv6text, propvalu, s_layer.STOR_TYPE_IPV6), ()),
                    )),
                )

                if len(nodeedits) >= 1000:
                    await save()

            if nodeedits:
                await save()

    async def revModel20210126(self, layers):

        for layr in layers:

            nodeedits = []
            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

            # uniq values of some array types....
            def uniq(valu):
                return tuple({v: True for v in valu}.keys())

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            stortype = s_layer.STOR_TYPE_GUID | s_layer.STOR_FLAG_ARRAY
            async for buid, propvalu in layr.iterPropRows('ou:org', 'industries'):

                uniqvalu = uniq(propvalu)
                if uniqvalu == propvalu:
                    continue

                nodeedits.append(
                    (buid, 'ou:org', (
                        (s_layer.EDIT_PROP_SET, ('industries', uniqvalu, propvalu, stortype), ()),
                    )),
                )

                if len(nodeedits) >= 1000:
                    await save()

            if nodeedits:
                await save()

    def typeHasStortype(self, typedef, stortype):

        if isinstance(typedef, s_types.Comp):
            fields = typedef.opts.get('fields')
            for i, (name, _) in enumerate(fields):
                if self.typeHasStortype(typedef.tcache[name], stortype):
                    return True

        elif isinstance(typedef, s_types.Array):
            return self.typeHasStortype(typedef.arraytype, stortype)

        elif isinstance(typedef, s_types.Range):
            return self.typeHasStortype(typedef.subtype, stortype)

        elif (typedef.stortype == stortype):
            return True

        return False

    def typeHasNdefs(self, typedef):

        if isinstance(typedef, s_types.Comp):
            fields = typedef.opts.get('fields')
            for i, (name, _) in enumerate(fields):
                if self.typeHasNdefs(typedef.tcache[name]):
                    return True

        elif isinstance(typedef, s_types.Array):
            return self.typeHasNdefs(typedef.arraytype)

        elif isinstance(typedef, s_types.Ndef):
            return True

        elif isinstance(typedef, s_types.Edge):
            return True

        elif isinstance(typedef, s_types.NodeProp):
            return True

        return False

    def getElementsByStortype(self, stortype):

        forms = set()
        props = set()
        tagprops = set()

        for name, prop in self.core.model.props.items():
            if not prop.isform and prop.univ:
                continue

            if self.typeHasStortype(prop.type, stortype) or self.typeHasNdefs(prop.type):
                if prop.isform:
                    forms.add(name)
                else:
                    props.add(name)

        for tname, tprop in self.core.model.tagprops.items():
            if self.typeHasStortype(tprop.type, stortype) or self.typeHasNdefs(tprop.type):
                tagprops.add(tname)

        return (forms, props, tagprops)

    async def updateProps(self, props, layers, skip=None):

        for prop in props:
            ptyp = self.core.model.props[prop]
            form = ptyp.form

            if form:
                form = form.name
            if skip is not None and (form and form in skip):
                continue

            pname = ptyp.name
            stortype = ptyp.type.stortype

            for layr in layers:

                nodeedits = []
                meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

                async def save():
                    await layr.storNodeEdits(nodeedits, meta)
                    nodeedits.clear()

                async for buid, propvalu in layr.iterPropRows(form, pname):

                    newval = ptyp.type.norm(propvalu)[0]
                    if newval == propvalu:
                        continue

                    nodeedits.append(
                        (buid, form, (
                            (s_layer.EDIT_PROP_SET, (pname, newval, None, stortype), ()),
                        )),
                    )

                    if len(nodeedits) >= 1000:
                        await save()

                if nodeedits:
                    await save()

    async def updateTagProps(self, tagprops, layers):

        for layr in layers:

            nodeedits = []
            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            for form, tag, prop in layr.getTagProps():

                if form is None or prop not in tagprops:
                    continue

                tptyp = self.core.model.tagprops[prop]
                stortype = tptyp.type.stortype

                async for buid, valu in layr.iterTagPropRows(tag, prop, form=form):

                    newval = tptyp.type.norm(valu)[0]
                    if newval == valu:
                        continue

                    nodeedits.append(
                        (buid, form, (
                            (s_layer.EDIT_TAGPROP_SET, (tag, prop, newval, None, stortype), ()),
                        )),
                    )

                    if len(nodeedits) >= 1000:
                        await save()

            if nodeedits:
                await save()

    async def revModel20220202(self, layers):

        (forms, props, tagprops) = self.getElementsByStortype(s_layer.STOR_TYPE_HUGENUM)

        layrmap = {layr.iden: layr for layr in layers}
        nodeedits = {layr.iden: {'adds': [], 'dels': [], 'n2edges': []} for layr in layers}

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        for form in forms:

            ftyp = self.core.model.type(form)
            stortype = ftyp.stortype

            async for buid, sodes in self.core._liftByProp(form, None, layers):

                valu = None
                for _, sode in sodes:
                    valu = sode.get('valu')
                    if valu:
                        break

                hnorm = ftyp.norm(valu[0])[0]
                newbuid = s_common.buid((form, hnorm))
                if buid == newbuid:
                    continue

                meta['migr'] = {'from': buid, 'to': newbuid}

                iden = s_common.ehex(buid)
                newiden = s_common.ehex(newbuid)

                for layr in layers:
                    async for (verb, n2iden) in layr.iterNodeEdgesN1(buid):
                        nodeedits[layr.iden]['adds'].append(
                            (s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()),
                        )
                        nodeedits[layr.iden]['dels'].append(
                            (s_layer.EDIT_EDGE_DEL, (verb, n2iden), ()),
                        )

                    async for (verb, n1iden) in layr.iterNodeEdgesN2(buid):
                        n1buid = s_common.uhex(n1iden)
                        n2sodes = await self.core._getStorNodes(n1buid, layers)
                        n1form = None

                        for s2 in n2sodes:
                            n1form = s2.get('form')
                            if n1form is not None:
                                break

                        nodeedits[layr.iden]['n2edges'].append(
                            (n1buid, n1form, (
                                (s_layer.EDIT_EDGE_ADD, (verb, newiden), ()),
                                (s_layer.EDIT_EDGE_DEL, (verb, iden), ()),
                            )),
                        )

                    async for (name, nvalu) in layr.iterNodeData(buid):
                        nodeedits[layr.iden]['adds'].append(
                            (s_layer.EDIT_NODEDATA_SET, (name, nvalu, None), ()),
                        )
                        nodeedits[layr.iden]['dels'].append(
                            (s_layer.EDIT_NODEDATA_DEL, (name, None), ()),
                        )

                for layriden, sode in sodes:

                    if 'valu' in sode:
                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_NODE_ADD, (hnorm, stortype), ()),
                        )
                        nodeedits[layriden]['dels'].append(
                            (s_layer.EDIT_NODE_DEL, (valu[0], stortype), ()),
                        )

                    for prop, (pval, ptyp) in sode.get('props', {}).items():
                        if prop.startswith('.') and prop in props:
                            fp = self.core.model.univs[prop]
                            newval = fp.type.norm(pval)[0]

                        else:
                            fullprop = ':'.join((form, prop))
                            if fullprop in props:
                                fp = self.core.model.props[fullprop]
                                newval = fp.type.norm(pval)[0]
                            else:
                                newval = pval

                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_PROP_SET, (prop, newval, None, ptyp), ()),
                        )
                        nodeedits[layriden]['dels'].append(
                            (s_layer.EDIT_PROP_DEL, (prop, pval, ptyp), ()),
                        )

                    for tag, tval in sode.get('tags', {}).items():
                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_TAG_SET, (tag, tval, None), ()),
                        )
                        nodeedits[layriden]['dels'].append(
                            (s_layer.EDIT_TAG_DEL, (tag, tval), ()),
                        )

                    for tag, tprops in sode.get('tagprops', {}).items():
                        for tprop, (tpval, tptyp) in tprops.items():
                            if tprop in tagprops:
                                tp = self.core.model.tagprops[tprop]
                                newval = tp.type.norm(tpval)[0]
                            else:
                                newval = tpval

                            nodeedits[layriden]['adds'].append(
                                (s_layer.EDIT_TAGPROP_SET, (tag, tprop, newval, None, tptyp), ()),
                            )
                            nodeedits[layriden]['dels'].append(
                                (s_layer.EDIT_TAGPROP_DEL, (tag, tprop, newval, tptyp), ()),
                            )

                for layriden, edits in nodeedits.items():
                    if edits['adds']:
                        nedits = [
                            (newbuid, form, edits['adds']),
                            (buid, form, edits['dels']),
                        ]
                        await layrmap[layriden].storNodeEdits(nedits, meta)
                        await layrmap[layriden].storNodeEdits(edits['n2edges'], meta)
                        edits['adds'].clear()
                        edits['dels'].clear()
                        edits['n2edges'].clear()

        await self.updateProps(props, layers, skip=forms)

        fixprops = {'include': [], 'autofix': 'index'}
        for form in forms:
            fixprops['include'].append((form, None))

        for prop in props:
            ptyp = self.core.model.props[prop]
            form = ptyp.form

            if form:
                form = form.name
            fixprops['include'].append((form, ptyp.name))

        for layr in layers:
            async for mesg in layr.verifyAllProps(scanconf=fixprops):
                pass

        await self.updateTagProps(tagprops, layers)

        fixprops = {'include': tagprops, 'autofix': 'index'}
        for layr in layers:
            async for mesg in layr.verifyAllTagProps(scanconf=fixprops):
                pass

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
