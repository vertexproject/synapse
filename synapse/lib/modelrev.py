import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

minvers = (0, 2, 6)
maxvers = (0, 2, 8)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((0, 2, 1), self.revModel20210126),
            ((0, 2, 2), self.revModel20210312),
            ((0, 2, 3), self.revModel20210528),
            ((0, 2, 5), self.revModel20210801),
            ((0, 2, 6), self.revModel20211112),
            ((0, 2, 8), self.revModel20220202),
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
        '''
        Return True if a type or one of its subtypes uses a specific stortype,
        otherwise return False.
        '''
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
        '''
        Return True if a type or one of its subtypes uses ndefs or nodeprops,
        otherwise return False.
        '''
        if isinstance(typedef, s_types.Comp):
            fields = typedef.opts.get('fields')
            for i, (name, _) in enumerate(fields):
                if self.typeHasNdefs(typedef.tcache[name]):
                    return True

        elif isinstance(typedef, s_types.Array):
            return self.typeHasNdefs(typedef.arraytype)

        elif isinstance(typedef, (s_types.Ndef, s_types.Edge, s_types.NodeProp)):
            return True

        return False

    def getElementsByStortype(self, stortype):
        '''
        Get the names of form, prop and tagprop model elements which use a specific
        stortype, or refer to other nodes via ndefs/nodeprops.
        '''
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

    async def updateProps(self, props, layers):
        '''
        Lift and re-norm prop values for the specified props in the specified layers.
        '''
        hugestorv1 = s_layer.StorTypeHugeNumV1(layers[0], s_layer.STOR_TYPE_HUGENUM)

        for prop in props:
            ptyp = self.core.model.props[prop]
            form = ptyp.form

            if form:
                form = form.name

            pname = ptyp.name
            stortype = ptyp.type.stortype
            isarray = False
            if stortype & s_layer.STOR_FLAG_ARRAY:
                isarray = True
                realtype = stortype & 0x7fff
                if realtype == s_layer.STOR_TYPE_HUGENUM:
                    realstor = hugestorv1
                else:
                    realstor = layers[0].stortypes[realtype]

                def arrayindx(valu):
                    return set([realstor.indx(aval)[0] for aval in valu])

            for layr in layers:

                delindx = []
                delarrayindx = []
                nodeedits = []
                meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden,
                        'migr': {'delpropindx': delindx, 'delproparrayindx': delarrayindx}}

                async def save():
                    await layr.storNodeEdits(nodeedits, meta)
                    nodeedits.clear()
                    delindx.clear()
                    delarrayindx.clear()

                try:
                    indxby = s_layer.IndxByProp(layr, form, pname)
                except s_exc.NoSuchAbrv:
                    # Skip props which aren't present in the layer
                    continue

                for key, buid in layr.layrslab.scanByPref(indxby.abrv, db=indxby.db):

                    if stortype == s_layer.STOR_TYPE_HUGENUM and len(key) == 28:
                        continue

                    propvalu = indxby.getNodeValu(buid)

                    if propvalu is None:
                        delindx.append((key, buid))
                        continue

                    try:
                        newval = ptyp.type.norm(propvalu)[0]
                    except s_exc.BadTypeValu as e:
                        oldm = e.errinfo.get('mesg')
                        logger.warning(f'Bad prop value {prop}={propvalu!r} : {oldm}')
                        continue

                    if isarray:
                        if realtype == s_layer.STOR_TYPE_HUGENUM:
                            for indx in arrayindx(propvalu):
                                delarrayindx.append((indxby.abrv + indx, buid))

                        elif newval == propvalu:
                            continue
                    else:
                        if stortype != s_layer.STOR_TYPE_HUGENUM and newval == propvalu:
                            continue

                        delindx.append((key, buid))

                    edits = []
                    if newval == propvalu:
                        edits.append((s_layer.EDIT_PROP_DEL, (pname, None, stortype), ()))
                    edits.append((s_layer.EDIT_PROP_SET, (pname, newval, None, stortype), ()))

                    nodeedits.append((buid, form, edits))

                    if len(nodeedits) + len(delindx) + len(delarrayindx) >= 1000:
                        await save()

                if nodeedits or delindx or delarrayindx:
                    await save()

    async def updateTagProps(self, tagprops, layers):
        '''
        Lift and re-norm prop values for the specified tagprops in the specified layers.
        '''
        for layr in layers:

            delindx = []
            nodeedits = []
            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden,
                    'migr': {'deltagpropindx': delindx}}

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()
                delindx.clear()

            for form, tag, prop in layr.getTagProps():

                if form is None or prop not in tagprops:
                    continue

                tptyp = self.core.model.tagprops[prop]
                stortype = tptyp.type.stortype

                indxbyftp = s_layer.IndxByTagProp(layr, form, tag, prop)
                indxbytp = s_layer.IndxByTagProp(layr, None, tag, prop)
                abrvlen = indxbyftp.abrvlen

                for key, buid in layr.layrslab.scanByPref(indxbyftp.abrv, db=indxbyftp.db):

                    if stortype == s_layer.STOR_TYPE_HUGENUM and len(key) == 28:
                        continue

                    indx = key[abrvlen:]
                    valu = indxbyftp.getNodeValu(buid)

                    if valu is None:
                        delindx.append((key, buid))
                        delindx.append((indxbytp.abrv + indx, buid))
                        continue

                    try:
                        newval = tptyp.type.norm(valu)[0]
                    except s_exc.BadTypeValu as e:
                        oldm = e.errinfo.get('mesg')
                        logger.warning(f'Bad prop value {tag}:{prop}={valu!r} : {oldm}')
                        continue

                    if stortype != s_layer.STOR_TYPE_HUGENUM and newval == valu:
                        continue

                    delindx.append((key, buid))
                    delindx.append((indxbytp.abrv + indx, buid))

                    edits = []
                    if newval == valu:
                        edits.append((s_layer.EDIT_TAGPROP_DEL, (tag, prop, None, stortype), ()))
                    edits.append((s_layer.EDIT_TAGPROP_SET, (tag, prop, newval, None, stortype), ()))

                    nodeedits.append((buid, form, edits))

                    if len(nodeedits) + len(delindx) >= 1000:
                        await save()

            if nodeedits or delindx:
                await save()

    async def revModel20220202(self, layers):

        await self.core.updateModel((0, 2, 7))
        for layr in layers:
            await layr.setModelVers((0, 2, 7))

        (forms, props, tagprops) = self.getElementsByStortype(s_layer.STOR_TYPE_HUGENUM)

        hugestorv1 = s_layer.StorTypeHugeNumV1(layers[0], s_layer.STOR_TYPE_HUGENUM)

        cnt = 0
        layrmap = {layr.iden: layr for layr in layers}

        nodeedits = {}
        for layr in layers:
            nodeedits[layr.iden] = {
                'adds': [],
                'dels': [],
                'n2edges': [],
                'delpropindx': [],
                'delproparrayindx': [],
            }

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        for formname in forms:

            async def save(buid, newbuid):

                for layriden, edits in nodeedits.items():

                    layr = layrmap[layriden]

                    if edits['adds']:
                        await layr.storNodeEdits([(newbuid, formname, edits['adds'])], meta)
                        edits['adds'].clear()

                    if edits['dels']:
                        await layr.storNodeEdits([(buid, formname, edits['dels'])], meta)
                        edits['dels'].clear()

                    if edits['n2edges']:
                        await layr.storNodeEdits(edits['n2edges'], meta)
                        edits['n2edges'].clear()

                    if edits['delpropindx'] or edits['delproparrayindx']:
                        meta['migr'] = {'delpropindx': edits['delpropindx'],
                                        'delproparrayindx': edits['delproparrayindx']}

                        await layr.storNodeEdits([(buid, formname, ())], meta)
                        edits['delpropindx'].clear()
                        edits['delproparrayindx'].clear()
                        del(meta['migr'])

            layrabrv = {}
            for layr in layers:
                try:
                    layrabrv[layr.iden] = layr.getPropAbrv(formname, None)
                except s_exc.NoSuchAbrv:
                    continue

            form = self.core.model.forms[formname]
            ftyp = form.type
            stortype = ftyp.stortype

            isarray = False
            if stortype & s_layer.STOR_FLAG_ARRAY:
                isarray = True
                realtype = stortype & 0x7fff
                if realtype == s_layer.STOR_TYPE_HUGENUM:
                    realstor = hugestorv1
                else:
                    realstor = layers[0].stortypes[realtype]

                def arrayindx(valu):
                    return set([realstor.indx(aval)[0] for aval in valu])

            async for buid, sodes in self.core._liftByProp(formname, None, layers):

                # Find the sode with the node value to recompute the buid
                valulayrs = []
                valu = None
                for layriden, sode in sodes:
                    valu = sode.get('valu')
                    if valu:
                        valu = valu[0]
                        valulayrs.append(layriden)

                try:
                    hnorm = ftyp.norm(valu)[0]
                except s_exc.BadTypeValu as e:
                    oldm = e.errinfo.get('mesg')
                    logger.warning(f'Bad form value {formname}={valu!r} : {oldm}')
                    continue

                newbuid = s_common.buid((formname, hnorm))

                if isarray:
                    if realtype != s_layer.STOR_TYPE_HUGENUM and newbuid == buid:
                        continue

                    if realtype == s_layer.STOR_TYPE_HUGENUM:
                        for indx in arrayindx(valu):
                            for vlay in valulayrs:
                                nodeedits[vlay]['delproparrayindx'].append((layrabrv[vlay] + indx, buid))
                                cnt += 1

                else:
                    if stortype != s_layer.STOR_TYPE_HUGENUM and newbuid == buid:
                        continue

                    if stortype == s_layer.STOR_TYPE_HUGENUM:
                        indx = hugestorv1.indx(valu)[0]
                        for vlay in valulayrs:
                            nodeedits[vlay]['delpropindx'].append((layrabrv[vlay] + indx, buid))
                            cnt += 1

                if buid == newbuid:
                    await save(buid, newbuid)
                    cnt = 0
                    continue

                iden = s_common.ehex(buid)
                newiden = s_common.ehex(newbuid)
                nodedel = None

                # Move props, tags, and tagprops for each sode to the new buid
                for layriden, sode in sodes:

                    if 'valu' in sode:
                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_NODE_ADD, (hnorm, stortype), ()),
                        )
                        nodedel = (layriden, (s_layer.EDIT_NODE_DEL, (valu, stortype), ()))
                        cnt += 1

                    for prop, (pval, ptyp) in sode.get('props', {}).items():
                        if prop.startswith('.') and prop in props:
                            fp = self.core.model.univs[prop]
                            try:
                                newval = fp.type.norm(pval)[0]
                            except s_exc.BadTypeValu as e:
                                oldm = e.errinfo.get('mesg')
                                logger.warning(f'Bad prop value {prop}={pval!r} : {oldm}')
                                continue

                        else:
                            fp = form.props[prop]
                            if fp.full in props:
                                try:
                                    newval = fp.type.norm(pval)[0]
                                except s_exc.BadTypeValu as e:
                                    oldm = e.errinfo.get('mesg')
                                    logger.warning(f'Bad prop value {fp.full}={pval!r} : {oldm}')
                                    continue
                            else:
                                newval = pval

                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_PROP_SET, (prop, newval, None, ptyp), ()),
                        )
                        nodeedits[layriden]['dels'].append(
                            (s_layer.EDIT_PROP_DEL, (prop, None, ptyp), ()),
                        )
                        cnt += 2
                        if cnt >= 1000:
                            await save(buid, newbuid)
                            cnt = 0

                    for tag, tval in sode.get('tags', {}).items():
                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_TAG_SET, (tag, tval, None), ()),
                        )
                        nodeedits[layriden]['dels'].append(
                            (s_layer.EDIT_TAG_DEL, (tag, None), ()),
                        )
                        cnt += 2
                        if cnt >= 1000:
                            await save(buid, newbuid)
                            cnt = 0

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
                                (s_layer.EDIT_TAGPROP_DEL, (tag, tprop, None, tptyp), ()),
                            )
                            cnt += 2
                            if cnt >= 1000:
                                await save(buid, newbuid)
                                cnt = 0

                # Move edges and nodedata for each layer to the new buid
                for layr in layers:
                    async for (verb, n2iden) in layr.iterNodeEdgesN1(buid):

                        if n2iden == iden:
                            n2iden = newiden

                        nodeedits[layr.iden]['adds'].append(
                            (s_layer.EDIT_EDGE_ADD, (verb, n2iden), ()),
                        )
                        nodeedits[layr.iden]['dels'].append(
                            (s_layer.EDIT_EDGE_DEL, (verb, n2iden), ()),
                        )
                        cnt += 2
                        if cnt >= 1000:
                            await save(buid, newbuid)
                            cnt = 0

                    async for (verb, n1iden) in layr.iterNodeEdgesN2(buid):

                        if n1iden == iden:
                            continue

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
                        cnt += 2
                        if cnt >= 1000:
                            await save(buid, newbuid)
                            cnt = 0

                    async for (name, nvalu) in layr.iterNodeData(buid):
                        nodeedits[layr.iden]['adds'].append(
                            (s_layer.EDIT_NODEDATA_SET, (name, nvalu, None), ()),
                        )
                        nodeedits[layr.iden]['dels'].append(
                            (s_layer.EDIT_NODEDATA_DEL, (name, None), ()),
                        )
                        cnt += 2
                        if cnt >= 1000:
                            await save(buid, newbuid)
                            cnt = 0

                # Delete the node with the old buid last to prevent wiping nodedata early
                if nodedel:
                    nodeedits[nodedel[0]]['dels'].append(nodedel[1])

                await save(buid, newbuid)
                cnt = 0

        # Update props and tagprops for nodes where the buid remains the same
        await self.updateProps(props, layers)
        await self.updateTagProps(tagprops, layers)

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

            await self.core.updateModel(revvers)
            [await lyr.setModelVers(revvers) for lyr in todo]

        logger.warning('...model migrations complete!')
