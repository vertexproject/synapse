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
        Return True if a type or one of its subtypes uses ndefs,
        otherwise return False.
        '''
        if isinstance(typedef, s_types.Comp):
            fields = typedef.opts.get('fields')
            for i, (name, _) in enumerate(fields):
                if self.typeHasNdefs(typedef.tcache[name]):
                    return True

        elif isinstance(typedef, s_types.Array):
            return self.typeHasNdefs(typedef.arraytype)

        elif isinstance(typedef, (s_types.Ndef, s_types.Edge)):
            return True

        return False

    def typeHasNodeprops(self, typedef):
        '''
        Return True if a type or one of its subtypes uses nodeprops,
        otherwise return False.
        '''
        if isinstance(typedef, s_types.Comp):
            fields = typedef.opts.get('fields')
            for i, (name, _) in enumerate(fields):
                if self.typeHasNodeprops(typedef.tcache[name]):
                    return True

        elif isinstance(typedef, s_types.Array):
            return self.typeHasNodeprops(typedef.arraytype)

        elif isinstance(typedef, s_types.NodeProp):
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
        ndefforms = set()
        ndefprops = set()
        nodepropprops = set()
        ndeftagprops = set()

        for name, prop in self.core.model.props.items():
            if not prop.isform and prop.univ:
                continue

            if self.typeHasStortype(prop.type, stortype):
                if prop.isform:
                    forms.add(name)
                else:
                    props.add(name)

            elif self.typeHasNdefs(prop.type):
                if prop.isform:
                    ndefforms.add(name)
                else:
                    ndefprops.add(name)

            elif self.typeHasNodeprops(prop.type):
                if not prop.isform:
                    nodepropprops.add(name)

        for tname, tprop in self.core.model.tagprops.items():
            if self.typeHasStortype(tprop.type, stortype) or self.typeHasNodeprops(tprop.type):
                tagprops.add(tname)

            elif self.typeHasNdefs(tprop.type):
                ndeftagprops.add(tname)

        return (forms, props, tagprops, ndefforms, ndefprops, ndeftagprops, nodepropprops)

    async def _updateNodeProps20220202(self, nodepropprops, uprops, layers):

        nodeedits = {layr.iden: [] for layr in layers}
        layrmap = {layr.iden: layr for layr in layers}
        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        cnt = 0
        async def save():
            for layriden, edits in nodeedits.items():
                layr = layrmap[layriden]
                await layr.storNodeEdits(edits, meta)
                edits.clear()

        for nodeprop in nodepropprops:
            realprop = self.core.model.props[nodeprop]
            realname = realprop.name
            realstor = realprop.type.stortype

            ptyp = self.core.model.props[nodeprop + ':prop']
            propstor = ptyp.type.stortype
            pname = ptyp.name

            form = ptyp.form
            if form:
                formname = form.name
                ftyp = form.type
                formstor = ftyp.stortype

            for layr in layers:
                try:
                    indxby = s_layer.IndxByProp(layr, formname, pname)
                except s_exc.NoSuchAbrv:
                    # Skip props which aren't present in the layer
                    continue

                for prop in uprops:

                    indx = layr.stortypes[propstor]._getIndxByts(prop)
                    for _, buid in indxby.keyBuidsByDups(indx):

                        sode = layr._getStorNode(buid)
                        if sode is None: # pragma: no cover
                            continue

                        props = sode.get('props')
                        if props:
                            valu = props.get(realname)
                            if valu:
                                valu = valu[0]
                                try:
                                    newvalu = realprop.type.norm(valu)[0]
                                except s_exc.BadTypeValu as e:
                                    oldm = e.errinfo.get('mesg')
                                    logger.warning(f'Bad prop value {realprop}={valu!r} : {oldm}')
                                    continue

                                if newvalu == valu:
                                    continue

                                nodeedits[layr.iden].append(
                                    (buid, formname, (
                                        (s_layer.EDIT_PROP_SET, (realname, newvalu, None, realstor), ()),
                                    )),
                                )

                                cnt += 1
                                if cnt >= 1000:
                                    await save()
                                    cnt = 0

        if cnt > 0:
            await save()

    async def _updateProps20220202(self, props, layers):
        '''
        Lift and re-norm prop values for the specified props in the specified layers.

        This will also remove old hugenum byprop and byarray index values.
        '''
        hugestorv1 = s_layer.StorTypeHugeNumV1(layers[0], s_layer.STOR_TYPE_HUGENUM)
        def arrayindx(valu):
            return set([hugestorv1.indx(aval)[0] for aval in valu])

        for prop in props:
            ptyp = self.core.model.props[prop]
            form = ptyp.form

            if form:
                form = form.name

            pname = ptyp.name
            stortype = ptyp.type.stortype

            if stortype & s_layer.STOR_FLAG_ARRAY:
                isarray = True
                realtype = stortype & 0x7fff
            else:
                isarray = False
                realtype = stortype

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

                    if realtype == s_layer.STOR_TYPE_HUGENUM:
                        if isarray:
                            for indx in arrayindx(propvalu):
                                delarrayindx.append((indxby.abrv + indx, buid))
                        else:
                            delindx.append((key, buid))

                    elif newval == propvalu:
                        continue

                    edits = []
                    if newval == propvalu:
                        edits.append((s_layer.EDIT_PROP_DEL, (pname, None, stortype), ()))
                    edits.append((s_layer.EDIT_PROP_SET, (pname, newval, None, stortype), ()))

                    nodeedits.append((buid, form, edits))

                    if len(nodeedits) + len(delindx) + len(delarrayindx) >= 1000:
                        await save()

                if nodeedits or delindx or delarrayindx:
                    await save()

    async def _updateTagProps20220202(self, tagprops, layers):
        '''
        Lift and re-norm prop values for the specified tagprops in the specified layers.

        This will also remove old hugenum bytagprop index values.
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

    async def updateNdefTagProps(self, ndeftagprops, layers, ndform, oldvalu, newvalu):
        '''
        Update tagprops with type ndef to the new value for a node.
        '''
        cnt = 0
        layrmap = {layr.iden: layr for layr in layers}
        nodeedits = {layr.iden: [] for layr in layers}

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        oldbuid = s_common.buid((ndform, oldvalu))

        async def save():
            for layriden, edits in nodeedits.items():
                layr = layrmap[layriden]
                await layr.storNodeEdits(edits, meta)
                edits.clear()

        for layr in layers:
            for form, tag, prop in layr.getTagProps():
                if form is None or prop not in ndeftagprops:
                    continue

                tptyp = self.core.model.tagprops[prop]
                stortype = tptyp.type.stortype
                indxbyftp = s_layer.IndxByTagProp(layr, form, tag, prop)

                for _, buid in indxbyftp.keyBuidsByDups(oldbuid):

                    sode = layr._getStorNode(buid)
                    if sode is None: # pragma: no cover
                        continue
                    nodeedits[layr.iden].append(
                        (buid, form, (
                            (s_layer.EDIT_TAGPROP_SET, (tag, prop, (ndform, newvalu), None, stortype), ()),
                        )),
                    )
                    cnt += 1
                    if cnt >= 1000:
                        await save()
                        cnt = 0
        await save()

    async def _updateNdefs20220202(self, props, tagprops, ndefprops, ndeftagprops, layers, ndform, oldvalu, newvalu):
        '''
        Update nodes containing a ndef values to the new value for a node.
        '''
        await self.updateNdefTagProps(ndeftagprops, layers, ndform, oldvalu, newvalu)

        cnt = 0
        uprops = set.union(props, ndefprops)
        layrmap = {layr.iden: layr for layr in layers}
        cmprvals = (('=', (ndform, oldvalu), s_layer.STOR_TYPE_MSGP),)
        hugestorv1 = s_layer.StorTypeHugeNumV1(layers[0], s_layer.STOR_TYPE_HUGENUM)

        def arrayindx(valu):
            return set([hugestorv1.indx(aval)[0] for aval in valu])

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

        for prop in ndefprops:
            ptyp = self.core.model.props[prop]
            propstor = ptyp.type.stortype
            pname = ptyp.name

            form = ptyp.form
            if form:
                formname = form.name
                ftyp = form.type
                formstor = ftyp.stortype

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

            if propstor & s_layer.STOR_FLAG_ARRAY:
                lifter = self.core._liftByPropArray
            else:
                lifter = self.core._liftByPropValu

            async for buid, sodes in lifter(formname, pname, cmprvals, layers):

                valulayrs = []
                valu = None
                for layriden, sode in sodes:
                    sodevalu = sode.get('valu')
                    if sodevalu:
                        valu = sodevalu[0]
                        valulayrs.append(layriden)

                try:
                    norm = ftyp.norm(valu)[0]
                except s_exc.BadTypeValu as e:
                    oldm = e.errinfo.get('mesg')
                    logger.warning(f'Bad form value {formname}={valu!r} : {oldm}')
                    continue

                newbuid = s_common.buid((formname, norm))

                if buid == newbuid:
                    for layriden, sode in sodes:
                        prps = sode.get('props')
                        if not prps:
                            continue

                        pval = prps.get(pname)
                        try:
                            newval = ptyp.type.norm(pval[0])[0]
                        except s_exc.BadTypeValu as e:
                            oldm = e.errinfo.get('mesg')
                            logger.warning(f'Bad prop value {ptyp.full}={pval!r} : {oldm}')
                            continue

                        if pval != newval:
                            nodeedits[layriden]['adds'].append(
                                (s_layer.EDIT_PROP_SET, (pname, newval, None, propstor), ()),
                            )
                    await save(buid, newbuid)
                    continue

                iden = s_common.ehex(buid)
                newiden = s_common.ehex(newbuid)
                nodedels = []

                # Move props, tags, and tagprops for each sode to the new buid
                for layriden, sode in sodes:

                    if 'valu' in sode:
                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_NODE_ADD, (norm, formstor), ()),
                        )
                        nodedels.append((layriden, (s_layer.EDIT_NODE_DEL, (valu, formstor), ())))
                        cnt += 1

                    for propname, (pval, ptyp) in sode.get('props', {}).items():
                        if propname.startswith('.') and propname in uprops:
                            fp = self.core.model.univs[propname]
                            try:
                                newval = fp.type.norm(pval)[0]
                            except s_exc.BadTypeValu as e:
                                oldm = e.errinfo.get('mesg')
                                logger.warning(f'Bad prop value {propname}={pval!r} : {oldm}')
                                continue

                        else:
                            fp = form.props[propname]
                            if fp.full in uprops:
                                try:
                                    newval = fp.type.norm(pval)[0]
                                except s_exc.BadTypeValu as e:
                                    oldm = e.errinfo.get('mesg')
                                    logger.warning(f'Bad prop value {fp.full}={pval!r} : {oldm}')
                                    continue
                            else:
                                newval = pval

                        if ptyp & s_layer.STOR_FLAG_ARRAY:
                            if ptyp & 0x7fff == s_layer.STOR_TYPE_HUGENUM:
                                abrv = layrmap[layriden].getPropAbrv(formname, propname)
                                for indx in arrayindx(pval):
                                    nodeedits[layriden]['delproparrayindx'].append((abrv + indx, buid))

                        elif ptyp == s_layer.STOR_TYPE_HUGENUM:
                            indx = hugestorv1.indx(pval)[0]
                            abrv = layrmap[layriden].getPropAbrv(formname, propname)
                            nodeedits[layriden]['delpropindx'].append((abrv + indx, buid))

                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_PROP_SET, (propname, newval, None, ptyp), ()),
                        )
                        nodeedits[layriden]['dels'].append(
                            (s_layer.EDIT_PROP_DEL, (propname, None, ptyp), ()),
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

                # Delete the nodes with the old buid last to prevent wiping nodedata early
                for layriden, nodedel in nodedels:
                    nodeedits[layriden]['dels'].append(nodedel)

                await save(buid, newbuid)
                cnt = 0

                # Update nodes which have this node as an ndef prop
                if valu != norm:
                    await self._updateNdefs20220202(props, tagprops, ndefprops, ndeftagprops, layers, formname, valu, norm)

    async def revModel20220202(self, layers):

        await self.core.updateModel((0, 2, 7))
        for layr in layers:
            await layr.setModelVers((0, 2, 7))

        (forms, props, tagprops, ndefforms, ndefprops, ndeftagprops, nodepropprops) = self.getElementsByStortype(s_layer.STOR_TYPE_HUGENUM)

        hugestorv1 = s_layer.StorTypeHugeNumV1(layers[0], s_layer.STOR_TYPE_HUGENUM)
        def arrayindx(valu):
            return set([hugestorv1.indx(aval)[0] for aval in valu])

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

            if stortype & s_layer.STOR_FLAG_ARRAY:
                isarray = True
                realtype = stortype & 0x7fff
            else:
                isarray = False
                realtype = stortype

            async for buid, sodes in self.core._liftByProp(formname, None, layers):

                # Find the sode with the node value to recompute the buid
                valulayrs = []
                valu = None
                for layriden, sode in sodes:
                    sodevalu = sode.get('valu')
                    if sodevalu:
                        valu = sodevalu[0]
                        valulayrs.append(layriden)

                try:
                    hnorm = ftyp.norm(valu)[0]
                except s_exc.BadTypeValu as e:
                    oldm = e.errinfo.get('mesg')
                    logger.warning(f'Bad form value {formname}={valu!r} : {oldm}')
                    continue

                newbuid = s_common.buid((formname, hnorm))

                if realtype == s_layer.STOR_TYPE_HUGENUM:
                    if isarray:
                        for indx in arrayindx(valu):
                            for vlay in valulayrs:
                                nodeedits[vlay]['delproparrayindx'].append((layrabrv[vlay] + indx, buid))
                                cnt += 1
                    else:
                        indx = hugestorv1.indx(valu)[0]
                        for vlay in valulayrs:
                            nodeedits[vlay]['delpropindx'].append((layrabrv[vlay] + indx, buid))
                            cnt += 1

                    if buid == newbuid:
                        await save(buid, newbuid)
                        cnt = 0
                        continue

                elif buid == newbuid:
                    continue

                iden = s_common.ehex(buid)
                newiden = s_common.ehex(newbuid)
                nodedels = []

                # Move props, tags, and tagprops for each sode to the new buid
                for layriden, sode in sodes:

                    if 'valu' in sode:
                        nodeedits[layriden]['adds'].append(
                            (s_layer.EDIT_NODE_ADD, (hnorm, stortype), ()),
                        )
                        nodedels.append((layriden, (s_layer.EDIT_NODE_DEL, (valu, stortype), ())))
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

                        if ptyp & s_layer.STOR_FLAG_ARRAY:
                            if ptyp & 0x7fff == s_layer.STOR_TYPE_HUGENUM:
                                abrv = layrmap[layriden].getPropAbrv(formname, prop)
                                for indx in arrayindx(pval):
                                    nodeedits[layriden]['delproparrayindx'].append((abrv + indx, buid))

                        elif ptyp == s_layer.STOR_TYPE_HUGENUM:
                            indx = hugestorv1.indx(pval)[0]
                            abrv = layrmap[layriden].getPropAbrv(formname, prop)
                            nodeedits[layriden]['delpropindx'].append((abrv + indx, buid))

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

                # Delete the nodes with the old buid last to prevent wiping nodedata early
                for layriden, nodedel in nodedels:
                    nodeedits[layriden]['dels'].append(nodedel)

                await save(buid, newbuid)
                cnt = 0

                # Update nodes which have this node as an ndef prop
                if valu != hnorm:
                    await self._updateNdefs20220202(props, tagprops, ndefprops, ndeftagprops, layers, formname, valu, hnorm)

        uprops = set.union(props, ndefprops)

        # Update props and tagprops for nodes where the buid remains the same
        await self._updateProps20220202(props, layers)
        await self._updateTagProps20220202(tagprops, layers)
        await self._updateNodeProps20220202(nodepropprops, uprops, layers)

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
