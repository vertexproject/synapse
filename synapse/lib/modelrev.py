import regex
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.spooled as s_spooled

import synapse.models.infotech as s_infotech

logger = logging.getLogger(__name__)

maxvers = (0, 2, 31)

class ModelRev:

    def __init__(self, core):
        self.core = core
        self.revs = (
            ((0, 2, 1), self.revModel20210126),
            ((0, 2, 2), self.revModel20210312),
            ((0, 2, 3), self.revModel20210528),
            ((0, 2, 5), self.revModel20210801),
            ((0, 2, 6), self.revModel20211112),
            ((0, 2, 7), self.revModel20220307),
            ((0, 2, 8), self.revModel20220315),
            ((0, 2, 9), self.revModel20220509),
            ((0, 2, 10), self.revModel20220706),
            ((0, 2, 11), self.revModel20220803),
            ((0, 2, 12), self.revModel20220901),
            ((0, 2, 13), self.revModel20221025),
            ((0, 2, 14), self.revModel20221123),
            ((0, 2, 15), self.revModel20221212),
            ((0, 2, 16), self.revModel20221220),
            ((0, 2, 17), self.revModel20230209),
            ((0, 2, 18), self.revModel_0_2_18),
            ((0, 2, 19), self.revModel_0_2_19),
            ((0, 2, 20), self.revModel_0_2_20),
            ((0, 2, 21), self.revModel_0_2_21),
            ((0, 2, 22), self.revModel_0_2_22),
            ((0, 2, 23), self.revModel_0_2_23),
            ((0, 2, 24), self.revModel_0_2_24),
            ((0, 2, 25), self.revModel_0_2_25),
            ((0, 2, 26), self.revModel_0_2_26),
            ((0, 2, 27), self.revModel_0_2_27),
            # Model revision 0.2.28 skipped
            ((0, 2, 29), self.revModel_0_2_29),
            ((0, 2, 30), self.revModel_0_2_30),
            ((0, 2, 31), self.revModel_0_2_31),
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

    async def _normHugeProp(self, layers, prop):

        proptype = prop.type
        propname = prop.name
        formname = prop.form.name
        stortype = prop.type.stortype

        for layr in layers:

            nodeedits = []
            meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            async for buid, propvalu in layr.iterPropRows(formname, propname):

                try:
                    newval = proptype.norm(propvalu)[0]
                except s_exc.BadTypeValu as e:
                    oldm = e.errinfo.get('mesg')
                    logger.warning(f'Bad prop value {propname}={propvalu!r} : {oldm}')
                    continue

                if newval == propvalu:
                    continue

                nodeedits.append(
                    (buid, formname, (
                        (s_layer.EDIT_PROP_SET, (propname, newval, None, stortype), ()),
                    )),
                )

                if len(nodeedits) >= 1000:
                    await save()

            if nodeedits:
                await save()

    async def _normHugeTagProps(self, layr, tagprops):

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

            async for buid, propvalu in layr.iterTagPropRows(tag, prop, form):

                try:
                    newval = tptyp.type.norm(propvalu)[0]
                except s_exc.BadTypeValu as e:
                    oldm = e.errinfo.get('mesg')
                    logger.warning(f'Bad prop value {tag}:{prop}={propvalu!r} : {oldm}')
                    continue

                if newval == propvalu:
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

    async def revModel20220307(self, layers):

        for name, prop in self.core.model.props.items():
            if prop.form is None:
                continue

            stortype = prop.type.stortype
            if stortype & s_layer.STOR_FLAG_ARRAY:
                stortype = stortype & 0x7fff

            if stortype == s_layer.STOR_TYPE_HUGENUM:
                await self._normHugeProp(layers, prop)

        tagprops = set()
        for name, prop in self.core.model.tagprops.items():
            if prop.type.stortype == s_layer.STOR_TYPE_HUGENUM:
                tagprops.add(prop.name)

        for layr in layers:
            await self._normHugeTagProps(layr, tagprops)

    async def revModel20220315(self, layers):

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            for formname, propname in (
                    ('geo:place', 'name'),
                    ('crypto:currency:block', 'hash'),
                    ('crypto:currency:transaction', 'hash')):

                prop = self.core.model.prop(f'{formname}:{propname}')
                async for buid, propvalu in layr.iterPropRows(formname, propname):
                    try:
                        norm = prop.type.norm(propvalu)[0]
                    except s_exc.BadTypeValu as e: # pragma: no cover
                        oldm = e.errinfo.get('mesg')
                        logger.warning(f'error re-norming {formname}:{propname}={propvalu} : {oldm}')
                        continue

                    if norm == propvalu:
                        continue

                    nodeedits.append(
                        (buid, formname, (
                            (s_layer.EDIT_PROP_SET, (propname, norm, propvalu, prop.type.stortype), ()),
                        )),
                    )

                    if len(nodeedits) >= 1000:  # pragma: no cover
                        await save()

                if nodeedits:
                    await save()

        layridens = [layr.iden for layr in layers]

        storm_geoplace_to_geoname = '''
        $layers = $lib.set()
        $layers.adds($layridens)
        for $view in $lib.view.list(deporder=$lib.true) {
            if (not $layers.has($view.layers.0.iden)) { continue }
            view.exec $view.iden {
                yield $lib.layer.get().liftByProp(geo:place:name)
                [ geo:name=:name ]
            }
        }
        '''

        storm_crypto_txin = '''
        $layers = $lib.set()
        $layers.adds($layridens)
        for $view in $lib.view.list(deporder=$lib.true) {
            if (not $layers.has($view.layers.0.iden)) { continue }
            view.exec $view.iden {

                function addInputXacts() {
                    yield $lib.layer.get().liftByProp(crypto:payment:input)
                    -:transaction $xact = $lib.null
                    { -> crypto:currency:transaction $xact=$node.value() }
                    if $xact {
                        [ :transaction=$xact ]
                    }
                    fini { return() }
                }

                function addOutputXacts() {
                    yield $lib.layer.get().liftByProp(crypto:payment:output)
                    -:transaction $xact = $lib.null
                    { -> crypto:currency:transaction $xact=$node.value() }
                    if $xact {
                        [ :transaction=$xact ]
                    }
                    fini { return() }
                }

                function wipeInputsArray() {
                    yield $lib.layer.get().liftByProp(crypto:currency:transaction:inputs)
                    [ -:inputs ]
                    fini { return() }
                }

                function wipeOutputsArray() {
                    yield $lib.layer.get().liftByProp(crypto:currency:transaction:outputs)
                    [ -:outputs ]
                    fini { return() }
                }

                $addInputXacts()
                $addOutputXacts()
                $wipeInputsArray()
                $wipeOutputsArray()
            }
        }
        '''

        storm_crypto_lockout = '''
        model.deprecated.lock crypto:currency:transaction:inputs
        | model.deprecated.lock crypto:currency:transaction:outputs
        '''

        logger.debug('Making geo:name nodes from geo:place:name values.')
        opts = {'vars': {'layridens': layridens}}
        await self.runStorm(storm_geoplace_to_geoname, opts=opts)
        logger.debug('Update crypto:currency:transaction :input and :output property use.')
        await self.runStorm(storm_crypto_txin, opts=opts)
        logger.debug('Locking out crypto:currency:transaction :input and :output properties.')
        await self.runStorm(storm_crypto_lockout)

    async def revModel20220509(self, layers):

        await self._normPropValu(layers, 'ou:industry:name')
        await self._propToForm(layers, 'ou:industry:name', 'ou:industryname')

        await self._normPropValu(layers, 'it:prod:soft:name')
        await self._normPropValu(layers, 'it:prod:soft:names')
        await self._normPropValu(layers, 'it:prod:softver:name')
        await self._normPropValu(layers, 'it:prod:softver:names')
        await self._normPropValu(layers, 'it:mitre:attack:software:name')
        await self._normPropValu(layers, 'it:mitre:attack:software:names')

        await self._propToForm(layers, 'it:prod:soft:name', 'it:prod:softname')
        await self._propToForm(layers, 'it:prod:softver:name', 'it:prod:softname')
        await self._propToForm(layers, 'it:mitre:attack:software:name', 'it:prod:softname')

        await self._propArrayToForm(layers, 'it:prod:soft:names', 'it:prod:softname')
        await self._propArrayToForm(layers, 'it:prod:softver:names', 'it:prod:softname')
        await self._propArrayToForm(layers, 'it:mitre:attack:software:names', 'it:prod:softname')

    async def revModel20220706(self, layers):
        await self._propToForm(layers, 'it:av:sig:name', 'it:av:signame')
        await self._propToForm(layers, 'it:av:filehit:sig:name', 'it:av:signame')

    async def revModel20220803(self, layers):

        await self._normPropValu(layers, 'ps:contact:title')
        await self._propToForm(layers, 'ps:contact:title', 'ou:jobtitle')

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        valid = regex.compile(r'^[0-9a-f]{40}$')
        repl = regex.compile(r'[\s:]')

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            formname = 'crypto:x509:cert'
            prop = self.core.model.prop('crypto:x509:cert:serial')

            async def movetodata(buid, valu):
                nodeedits.append(
                    (buid, formname, (
                        (s_layer.EDIT_PROP_DEL, (prop.name, valu, prop.type.stortype), ()),
                        (s_layer.EDIT_NODEDATA_SET, ('migration:0_2_10', {'serial': valu}, None), ()),
                    )),
                )
                if len(nodeedits) >= 1000:
                    await save()

            async for buid, propvalu in layr.iterPropRows(formname, prop.name):

                if not isinstance(propvalu, str):  # pragma: no cover
                    logger.warning(f'error re-norming {formname}:{prop.name}={propvalu} '
                                   f'for node {s_common.ehex(buid)} : invalid prop type')
                    await movetodata(buid, propvalu)
                    continue

                if valid.match(propvalu):
                    continue

                newv = repl.sub('', propvalu)

                try:
                    newv = int(newv)
                except ValueError:
                    try:
                        newv = int(newv, 16)
                    except ValueError:
                        logger.warning(f'error re-norming {formname}:{prop.name}={propvalu} '
                                       f'for node {s_common.ehex(buid)} : invalid prop value')
                        await movetodata(buid, propvalu)
                        continue

                try:
                    newv = s_common.ehex(newv.to_bytes(20, 'big', signed=True))
                    norm, info = prop.type.norm(newv)

                except (OverflowError, s_exc.BadTypeValu):
                    logger.warning(f'error re-norming {formname}:{prop.name}={propvalu} '
                                   f'for node {s_common.ehex(buid)} : invalid prop value')
                    await movetodata(buid, propvalu)
                    continue

                nodeedits.append(
                    (buid, formname, (
                        (s_layer.EDIT_PROP_SET, (prop.name, norm, propvalu, prop.type.stortype), ()),
                    )),
                )

                if len(nodeedits) >= 1000:
                    await save()

            if nodeedits:
                await save()

    async def revModel20220901(self, layers):

        await self._normPropValu(layers, 'pol:country:name')
        await self._propToForm(layers, 'pol:country:name', 'geo:name')

        await self._normPropValu(layers, 'risk:alert:type')
        await self._propToForm(layers, 'risk:alert:type', 'risk:alert:taxonomy')

    async def revModel20221025(self, layers):
        await self._propToForm(layers, 'risk:tool:software:type', 'risk:tool:software:taxonomy')

    async def revModel20221123(self, layers):
        await self._normPropValu(layers, 'inet:flow:dst:softnames')
        await self._normPropValu(layers, 'inet:flow:src:softnames')

        await self._propArrayToForm(layers, 'inet:flow:dst:softnames', 'it:prod:softname')
        await self._propArrayToForm(layers, 'inet:flow:src:softnames', 'it:prod:softname')

    async def revModel20221212(self, layers):

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        props = [
            'ou:contract:award:price',
            'ou:contract:budget:price'
        ]

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            for propname in props:
                prop = self.core.model.prop(propname)

                async def movetodata(buid, valu):
                    (retn, data) = await layr.getNodeData(buid, 'migration:0_2_15')
                    if retn:
                        data[prop.name] = valu
                    else:
                        data = {prop.name: valu}

                    nodeedits.append(
                        (buid, prop.form.name, (
                            (s_layer.EDIT_PROP_DEL, (prop.name, valu, s_layer.STOR_TYPE_UTF8), ()),
                            (s_layer.EDIT_NODEDATA_SET, ('migration:0_2_15', data, None), ()),
                        )),
                    )
                    if len(nodeedits) >= 1000:
                        await save()

                async for buid, propvalu in layr.iterPropRows(prop.form.name, prop.name):
                    try:
                        norm, info = prop.type.norm(propvalu)
                    except s_exc.BadTypeValu as e:
                        oldm = e.errinfo.get('mesg')
                        logger.warning(f'error re-norming {prop.form.name}:{prop.name}={propvalu} : {oldm}')
                        await movetodata(buid, propvalu)
                        continue

                    nodeedits.append(
                        (buid, prop.form.name, (
                            (s_layer.EDIT_PROP_DEL, (prop.name, propvalu, s_layer.STOR_TYPE_UTF8), ()),
                            (s_layer.EDIT_PROP_SET, (prop.name, norm, None, prop.type.stortype), ()),
                        )),
                    )

                    if len(nodeedits) >= 1000:  # pragma: no cover
                        await save()

                if nodeedits:
                    await save()

    async def revModel20221220(self, layers):
        todoprops = (
            'risk:tool:software:soft:names',
            'risk:tool:software:techniques'
        )
        await self._uniqSortArray(todoprops, layers)

    async def revModel20230209(self, layers):

        await self._normFormSubs(layers, 'inet:http:cookie')

        meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        nodeedits = []
        for layr in layers:

            async def save():
                await layr.storNodeEdits(nodeedits, meta)
                nodeedits.clear()

            prop = self.core.model.prop('risk:vuln:cvss:av')
            propname = prop.name
            formname = prop.form.name
            stortype = prop.type.stortype

            oldvalu = 'V'
            newvalu = 'P'

            async for buid, propvalu in layr.iterPropRows(formname, propname, stortype=stortype, startvalu=oldvalu):

                if propvalu != oldvalu:  # pragma: no cover
                    break

                nodeedits.append(
                    (buid, formname, (
                        (s_layer.EDIT_PROP_DEL, (propname, propvalu, stortype), ()),
                        (s_layer.EDIT_PROP_SET, (propname, newvalu, None, stortype), ()),
                    )),
                )

                if len(nodeedits) >= 1000:  # pragma: no cover
                    await save()

            if nodeedits:
                await save()

    async def revModel_0_2_18(self, layers):
        await self._propToForm(layers, 'file:bytes:mime:pe:imphash', 'hash:md5')
        await self._normPropValu(layers, 'ou:goal:type')
        await self._propToForm(layers, 'ou:goal:type', 'ou:goal:type:taxonomy')

        await self._normPropValu(layers, 'ou:goal:name')
        await self._propToForm(layers, 'ou:goal:name', 'ou:goalname')

    async def revModel_0_2_19(self, layers):
        await self._normPropValu(layers, 'ou:campaign:name')
        await self._propToForm(layers, 'ou:campaign:name', 'ou:campname')
        await self._normPropValu(layers, 'risk:vuln:type')
        await self._propToForm(layers, 'risk:vuln:type', 'risk:vuln:type:taxonomy')

    async def revModel_0_2_20(self, layers):
        await self._normFormSubs(layers, 'inet:url', liftprop='user')
        await self._propToForm(layers, 'inet:url:user', 'inet:user')
        await self._propToForm(layers, 'inet:url:passwd', 'inet:passwd')

        await self._updatePropStortype(layers, 'file:bytes:mime:pe:imphash')

    async def revModel_0_2_21(self, layers):
        await self._normPropValu(layers, 'risk:vuln:cvss:v2')
        await self._normPropValu(layers, 'risk:vuln:cvss:v3')

        await self._normPropValu(layers, 'risk:vuln:name')
        await self._propToForm(layers, 'risk:vuln:name', 'risk:vulnname')

    async def revModel_0_2_22(self, layers):
        await self._normFormSubs(layers, 'inet:ipv4', cmprvalu='100.64.0.0/10')

    async def revModel_0_2_23(self, layers):
        await self._normFormSubs(layers, 'inet:ipv6')

    async def revModel_0_2_24(self, layers):
        await self._normPropValu(layers, 'risk:mitigation:name')
        await self._normPropValu(layers, 'it:mitre:attack:technique:name')
        await self._normPropValu(layers, 'it:mitre:attack:mitigation:name')

        formprops = {}
        for prop in self.core.model.getPropsByType('velocity'):
            formname = prop.form.name
            if formname not in formprops:
                formprops[formname] = []

            formprops[formname].append(prop)

        for prop in self.core.model.getArrayPropsByType('velocity'):
            formname = prop.form.name
            if formname not in formprops:
                formprops[formname] = []

            formprops[formname].append(prop)

        for form, props in formprops.items():
            await self._normVelocityProps(layers, form, props)

    async def revModel_0_2_25(self, layers):
        await self._typeToForm(layers, 'econ:currency', 'econ:currency')
        await self._normPropValu(layers, 'ou:position:title')
        await self._propToForm(layers, 'ou:position:title', 'ou:jobtitle')

        await self._normPropValu(layers, 'ou:conference:name')
        await self._propToForm(layers, 'ou:conference:name', 'entity:name')

        await self._normPropValu(layers, 'ou:conference:names')
        await self._propArrayToForm(layers, 'ou:conference:names', 'entity:name')

    async def revModel_0_2_26(self, layers):
        for name, prop in list(self.core.model.props.items()):
            if prop.isform:
                continue

            stortype = prop.type.stortype
            if stortype & s_layer.STOR_FLAG_ARRAY:
                stortype = stortype & 0x7fff

            if stortype == s_layer.STOR_TYPE_NDEF:
                logger.info(f'Updating ndef indexing for {name}')
                await self._updatePropStortype(layers, prop.full)

    async def revModel_0_2_27(self, layers):
        await self._normPropValu(layers, 'it:dev:repo:commit:id')

    async def revModel_0_2_29(self, layers):
        await self._propToForm(layers, 'ou:industry:type', 'ou:industry:type:taxonomy')

    async def revModel_0_2_30(self, layers):
        await self._normFormSubs(layers, 'inet:ipv4', cmprvalu='192.0.0.0/24')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='64:ff9b:1::/48')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='2002::/16')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='2001:1::1/128')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='2001:1::2/128')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='2001:3::/32')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='2001:4:112::/48')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='2001:20::/28')
        await self._normFormSubs(layers, 'inet:ipv6', cmprvalu='2001:30::/28')

    async def revModel_0_2_31(self, layers):

        layridens = [layr.iden for layr in layers]

        migr = await ModelMigration_0_2_31.anit(self.core, layridens)
        await migr.revModel_0_2_31()

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

            todo = [lyr for lyr in layers if not lyr.ismirror and await lyr.getModelVers() < revvers]
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

            async for buid, propvalu in layr.iterPropRows(prop.form.name, prop.name):
                try:
                    norm, info = prop.type.norm(propvalu)
                except s_exc.BadTypeValu as e:
                    nodeedits.append(
                        (buid, prop.form.name, (
                            (s_layer.EDIT_NODEDATA_SET, (f'_migrated:{prop.full}', propvalu, None), ()),
                            (s_layer.EDIT_PROP_DEL, (prop.name, propvalu, prop.type.stortype), ()),
                        )),
                    )
                    oldm = e.errinfo.get('mesg')
                    iden = s_common.ehex(buid)
                    logger.warning(f'error re-norming {prop.form.name}:{prop.name}={propvalu} (layer: {layr.iden}, node: {iden}): {oldm}',
                                   extra={'synapse': {'node': iden, 'layer': layr.iden}})
                    continue

                if norm == propvalu:
                    continue

                nodeedits.append(
                    (buid, prop.form.name, (
                        (s_layer.EDIT_PROP_SET, (prop.name, norm, propvalu, prop.type.stortype), ()),
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

            async for lkey, buid, sode in layr.liftByProp(prop.form.name, prop.name):

                props = sode.get('props')

                # this should be impossible, but has been observed in the wild...
                if props is None: # pragma: no cover
                    continue

                curv = props.get(prop.name)
                if curv is None or curv[1] == stortype:
                    continue

                nodeedits.append(
                    (buid, prop.form.name, (
                        (s_layer.EDIT_PROP_SET, (prop.name, curv[0], curv[0], stortype), ()),
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

            async for _, buid, sode in genr:

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

                        edits.append((s_layer.EDIT_PROP_SET, (subprop.name, subnorm, subcurv, subprop.type.stortype), ()))

                    if not edits: # pragma: no cover
                        continue

                    nodeedits.append((buid, formname, edits))

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

class ModelMigration_0_2_31:
    @classmethod
    async def anit(cls, core, layridens):
        self = cls()

        self.core = core
        self.layridens = layridens

        self.views = await self.core.getViewDefs(deporder=True)
        self.rviews = self.views.copy()
        self.rviews.reverse()

        return self

    async def iterViews(self, reverse=False):
        views = self.views
        if reverse:
            views = self.rviews

        rootuser = self.core.auth.rootuser

        for view in views:
            viewiden = view.get('iden')
            hview = self.core.getView(viewiden)

            layriden = hview.layers[0].iden
            if layriden not in self.layridens:
                continue

            snap = await hview.snap(rootuser)

            yield (snap, hview)

    @s_cache.memoize
    def getRefInfo(self, formname):
        props = []
        props.extend(self.core.model.getPropsByType(formname))
        props.extend(self.core.model.getPropsByType('array'))
        props.extend(self.core.model.getPropsByType('ndef'))

        props = [k for k in props if k.form.name != formname]

        refinfo = []
        for prop in props:

            if prop.form.name == formname:
                continue

            proptype = prop.type

            if prop.type.isarray:
                proptype = prop.type.arraytype

                if proptype.name not in (formname, 'ndef'):
                    continue

            refinfo.append((
                prop.form.name,
                prop.name,
                proptype.name,
                prop.type.isarray,
                prop.info.get('ro', False)
            ))

        return refinfo

    @s_cache.memoize
    def getRoProps(self, formname):
        roprops = []

        form = self.core.model.form(formname)
        for propname, prop in form.props.items():
            if prop.info.get('ro', False):
                roprops.append(propname)

        return roprops

    async def revModel_0_2_31(self):

        queues = await self.core.listCoreQueues()
        queues = {k['name']: k for k in queues}

        if queues.get('model_0_2_31:nodes') is None:
            await self.core.addCoreQueue('model_0_2_31:nodes', {})

        if queues.get('model_0_2_31:nodes:refs') is None:
            await self.core.addCoreQueue('model_0_2_31:nodes:refs', {})

        if queues.get('model_0_2_31:nodes:edges') is None:
            await self.core.addCoreQueue('model_0_2_31:nodes:edges', {})

        if queues.get('model_0_2_31:nodes:edits') is None:
            await self.core.addCoreQueue('model_0_2_31:nodes:edits', {})

        # Delete invalid floating :v2_2 props in all views
        async for snap, view in self.iterViews(reverse=True):

            async for buid, info in snap.wlyr.getStorNodesByForm('it:sec:cpe'):
                if info.get('valu') or (props := info.get('props')) is None or (v2_2 := props.get('v2_2')) is None:
                    continue

                if s_infotech.isValidCpe22(v2_2[0]):
                    continue

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    continue

                await node.pop('v2_2')

        migrated = 0
        async for snap, view in self.iterViews():

            async for _, buid, sode in view.layers[0].liftByProp('it:sec:cpe', None):
                oldcpe = await snap.getNodeByBuid(buid)
                if not oldcpe:
                    continue

                ok, valu = await self.tryMigrateCpeNode(snap, oldcpe)

                if ok and valu is None:
                    # No primary property changes, nothing to do. Node has been fully migrated.
                    continue

                if not ok:
                    logger.debug(f'Could not migrate {oldcpe}, storing/removing.')
                    # Remove the old :v2_2 prop because it's invalid and it could cause problems during node restoration
                    await oldcpe.pop('v2_2')

                    # Bad node, remove it and any immutable references
                    await self.storeNode(oldcpe, view.iden, view.layers[0].iden)
                    await self.removeNode(oldcpe)

                else:
                    # At this point, we have a node that can be fixed but needs to be migrated to a new node because the
                    # primary property needs to be changed. We'll create a new (correct) node, and copy everything from
                    # the old node. Then we complete the migration by iterating through all the views to fix the
                    # references.

                    logger.debug(f'Migrating {oldcpe} -> {valu}.')
                    props = {}
                    if (seen := oldcpe.props.get('.seen')) is not None:
                        props['.seen'] = seen

                    newcpe = await snap.addNode('it:sec:cpe', valu, props=props)

                    await self.copyNodeLayer(snap, oldcpe, newcpe)
                    await self.migrateCpeNode(oldcpe, newcpe)

                    # Iterate through the views in reverse deporder looking for floating node edits
                    async for rsnap, rview in self.iterViews(reverse=True):
                        if rview.iden == view.iden:
                            # Only process views that are higher than the original view
                            continue

                        _oldcpe = await rsnap.getNodeByBuid(buid)
                        if _oldcpe is None:
                            continue

                        async for _newcpe in rsnap.nodesByPropValu('it:sec:cpe', '=', valu):
                            await self.copyNodeLayer(rsnap, _oldcpe, _newcpe)

                        await self.delNodeEdges(rsnap, _oldcpe)
                        await _oldcpe.delete(force=True)

                    await self.delNodeEdges(snap, oldcpe)
                    await oldcpe.delete(force=True)

                migrated += 1
                if migrated % 100 == 0:
                    logger.info(f'Migrated {migrated} nodes.')

    async def tryMigrateCpeNode(self, snap, node):
        # This function is a heavily modified version of
        # synapse.lib.stormlib.model.LibModelMigrations._itSecCpe_2_170_0_internal

        if node.form.name != 'it:sec:cpe':
            raise s_exc.BadArg(f'itSecCpeFix only accepts it:sec:cpe nodes, not {node.form.name}')

        curv = node.repr()

        modl = snap.core.model.type('it:sec:cpe')

        valu23 = None
        valu22 = None

        # Check the primary property for validity.
        if s_infotech.isValidCpe23(curv):
            valu23 = curv

        # Check the v2_2 property for validity.
        if (v2_2 := node.props.get('v2_2')) is not None and s_infotech.isValidCpe22(v2_2):
            valu22 = v2_2

        # If both values are populated, this node is valid
        if valu23 is not None and valu22 is not None:
            # Node ok, no primary property changes
            return (True, None)

        if valu23 is None and valu22 is None:
            # Bad node
            return (False, None)

        valu = valu23 or valu22

        # Re-normalize the data from the 2.3 or 2.2 string, whichever was valid.
        norm, info = modl.norm(valu)
        subs = info.get('subs')

        if norm != curv:
            # Good node, bad primary property
            return (True, norm)

        async with snap.getNodeEditor(node) as proto:

            # Iterate over the existing properties
            for propname, propcurv in node.props.items():
                subscurv = subs.get(propname)
                if subscurv is None:
                    continue

                if propname == 'v2_2' and isinstance(subscurv, list):
                    subscurv = s_infotech.zipCpe22(subscurv)

                # Values are the same, go around
                if propcurv == subscurv:
                    continue

                # Update the existing property with the re-normalized property value.
                await proto.set(propname, subscurv, ignore_ro=True)

            # Good node
            return (True, None)

    async def migrateCpeNode(self, oldcpe, newcpe):
        refinfos = self.getRefInfo(oldcpe.form.name)

        async for snap, view in self.iterViews():
            for formname, propname, proptype, isarray, isro in refinfos:
                if proptype == 'ndef':
                    oldvalu = oldcpe.ndef
                    newvalu = newcpe.ndef
                else:
                    oldvalu = oldcpe.repr()
                    newvalu = newcpe.repr()

                async for node in self.liftByPropValuNoNorm(snap, formname, propname, oldvalu):
                    if isro:
                        # The property is readonly so we can only delete it
                        await self.storeNode(node, view.iden, view.layers[0].iden)
                        await self.removeNode(node)
                        await node.delete()
                        continue

                    if isarray:
                        # We can't just [ :$prop-=$oldvalu :$prop+=$newvalu ] because the norm() function gets called
                        # on the array type deep down in the AST. So, instead, we have to operate on the whole array.

                        propval = list(node.props.get(propname, ()))
                        while oldvalu in propval:
                            propval.remove(oldvalu)

                        if newvalu not in propval:
                            propval.append(newvalu)

                        await self.setNodePropValuNoNorm(snap, node, propname, propval)

                    else:
                        await node.set(propname, newvalu)

    async def storeNode(self, node, viewiden, layriden):

        buid = node.buid
        valu = node.repr()
        form = node.form.name
        ndef = node.ndef

        offsets = {
            'refs': [],
            'edges': [],
            'edits': [],
        }

        refinfos = self.getRefInfo(form)
        sources = set()
        roprops = self.getRoProps(form)

        references = []
        edits = []
        edges = []

        async def queueRefs(threshold=1):
            nonlocal references
            if len(references) < threshold:
                return
            offset = await self.core.coreQueuePuts('model_0_2_31:nodes:refs', (references,))
            offsets['refs'].append(offset)
            references = []

        async def queueEdits(threshold=1):
            nonlocal edits
            if len(edits) < threshold:
                return
            offset = await self.core.coreQueuePuts('model_0_2_31:nodes:edits', (edits,))
            offsets['edits'].append(offset)
            edits = []

        async def queueEdges(threshold=1):
            nonlocal edges
            if len(edges) < threshold:
                return
            offset = await self.core.coreQueuePuts('model_0_2_31:nodes:edges', (edges,))
            offsets['edges'].append(offset)
            edges = []

        async for snap, view in self.iterViews(reverse=True):
            layer = view.layers[0]

            edit = {}
            data = {}

            data = {name: valu async for name, valu in layer.iterNodeData(buid)}
            if data:
                edit['data'] = data

            sode = await layer.getStorNode(buid)
            if sode:
                props = sode.get('props')
                [props.pop(roprop) for roprop in roprops if roprop in props]
                if props:
                    edit['props'] = props

                if (tags := sode.get('tags')):
                    edit['tags'] = tags

                if (tagprops := sode.get('tagprops')):
                    edit['tagprops'] = tagprops

                if edit:
                    edit['view'] = view.iden
                    edit['layer'] = layer.iden
                    edits.append(edit)

                await queueEdits(threshold=1000)

            async for verb, dst in layer.iterNodeEdgesN1(buid):
                edges.append({
                    'verb': verb,
                    'node': dst,
                    'direction': 'n1',
                    'layer': layer.iden,
                    'view': view.iden,
                })

                await queueEdges(threshold=1000)

            async for verb, src in layer.iterNodeEdgesN2(buid):
                edges.append({
                    'verb': verb,
                    'node': src,
                    'direction': 'n2',
                    'layer': layer.iden,
                    'view': view.iden,
                })

                # Capture the '<(seen)- meta:source' sources while we're iterating the edges
                if verb == 'seen':
                    srcnode = await snap.getNodeByBuid(s_common.uhex(src))
                    if srcnode is not None and srcnode.form.name == 'meta:source':
                        sources.add(srcnode.repr())

                await queueEdges(threshold=1000)

            for formname, propname, proptype, isarray, isro in refinfos:
                if proptype == 'ndef':
                    oldvalu = ndef
                else:
                    oldvalu = valu

                async for ref in self.liftByPropValuNoNorm(snap, formname, propname, oldvalu):
                    if isro:
                        continue

                    references.append({
                        'iden': ref.iden(),
                        'layer': view.layers[0].iden,
                        'view': view.iden,
                        'refinfo': (formname, propname, proptype, isarray),
                    })

                    await queueRefs(threshold=1000)

        await queueEdits()
        await queueEdges()
        await queueRefs()

        item = {
            'iden': node.iden(),
            'form': form,
            'valu': valu,
            'view': viewiden,
            'layer': layriden,
            'offsets': offsets,
            'sources': list(sources),
        }
        await self.core.coreQueuePuts('model_0_2_31:nodes', (item,))

    async def removeNode(self, node):
        buid = node.buid
        valu = node.repr()
        form = node.form.name
        ndef = node.ndef

        refinfos = self.getRefInfo(form)

        async for snap, view in self.iterViews():
            for formname, propname, proptype, isarray, isro in refinfos:
                if proptype == 'ndef':
                    oldvalu = ndef
                else:
                    oldvalu = valu

                async for ref in self.liftByPropValuNoNorm(snap, formname, propname, oldvalu):
                    if isro:
                        await self.storeNode(ref, view.iden, view.layers[0].iden)
                        await self.removeNode(ref)
                        await ref.delete()
                        continue

                    if isarray:
                        # We can't just [ :$prop-=$oldvalu :$prop+=$newvalu ] because the norm() function gets called
                        # on the array type deep down in the AST. So, instead, we have to operate on the whole array.

                        propval = list(ref.props.get(propname, ()))
                        while oldvalu in propval:
                            propval.remove(oldvalu)

                        if not propval:
                            await ref.pop(propname)
                        else:
                            await self.setNodePropValuNoNorm(snap, ref, propname, propval)

                    else:
                        await ref.pop(propname)

        # This loop removes all the edits and edges from every layer
        async for snap, view in self.iterViews(reverse=True):
            node = await snap.getNodeByBuid(buid)
            if node is None:
                continue
            await self.delNodeEdges(snap, node)
            await node.delete(force=True)

    async def delNodeEdges(self, snap, node):
        async with await s_spooled.Set.anit(dirn=self.core.dirn) as edges:
            seenverbs = set()

            async for (verb, n2iden) in node.iterEdgesN2():
                if verb not in seenverbs:
                    seenverbs.add(verb)
                await edges.add((verb, n2iden))

            async with snap.getEditor() as editor:
                async for (verb, n2iden) in edges:
                    n2 = await editor.getNodeByBuid(s_common.uhex(n2iden))
                    if n2 is not None:
                        if await n2.delEdge(verb, node.iden()) and len(editor.protonodes) >= 1000:
                            await snap.applyNodeEdits(editor.getNodeEdits())
                            editor.protonodes.clear()

    async def copyNodeLayer(self, snap, src, dst):
        '''
        Copy props/tags/edges/data changes that reside in this layer from src to dst.
        '''

        layer = snap.wlyr

        form = src.form

        async with snap.getEditor() as editor:
            proto = editor.loadNode(dst)

            # Copy N1 edges
            async for verb, n1iden in layer.iterNodeEdgesN1(src.buid):
                await proto.addEdge(verb, n1iden)

            # Copy N2 edges
            async for verb, n2iden in layer.iterNodeEdgesN2(src.buid):
                n2 = await editor.getNodeByBuid(s_common.uhex(n2iden))
                await n2.addEdge(verb, dst.iden())

            # Copy node data
            async for name, valu in layer.iterNodeData(src.buid):
                await proto.setData(name, valu)

            if (sode := await layer.getStorNode(src.buid)):
                # Copy props
                for name, valu in sode.get('props', {}).items():
                    if (prop := form.props.get(name)) is not None and prop.info.get('ro', False):
                        continue
                    await proto.set(name, valu[0])

                # Copy tags
                for name, valu in sode.get('tags', {}).items():
                    await proto.addTag(name, valu=valu)

                # Copy tagprops
                for tagname, tagprops in sode.get('tagprops', {}).items():
                    for propname, valu in tagprops.items():
                        await proto.setTagProp(tagname, propname, valu[0])

    async def liftByPropValuNoNorm(self, snap, formname, propname, valu, cmpr='=', reverse=False):
        '''
        No storm docs for this on purpose. It is restricted for use during model migrations only.
        '''
        prop = snap.core.model.prop(f'{formname}:{propname}')
        if prop is None:
            mesg = f'Could not find prop: {formname}:{propname}'
            raise s_exc.NoSuchProp(mesg=mesg, formname=formname, propname=propname)

        stortype = prop.type.stortype

        # Normally we'd call proptype.getStorCmprs() here to get the cmprvals
        # but getStorCmprs() calls norm() which we're  trying to avoid so build
        # cmprvals manually here.

        if prop.type.isarray:
            stortype &= (~s_layer.STOR_FLAG_ARRAY)
            liftfunc = snap.wlyr.liftByPropArray
        else:
            liftfunc = snap.wlyr.liftByPropValu

        cmprvals = ((cmpr, valu, stortype),)

        layriden = snap.wlyr.iden
        async for _, buid, sode in liftfunc(formname, propname, cmprvals, reverse=reverse):
            yield await snap._joinStorNode(buid, {layriden: sode})

    async def setNodePropValuNoNorm(self, snap, node, propname, valu):
        '''
        No storm docs for this on purpose. It is restricted for use during model migrations only.
        '''

        # NB: I'm sure there are all kinds of edges cases that this function doesn't account for. At the time of it's
        # creation, this was intended to be used to update array properties with bad it:sec:cpe values in them. It works
        # for that use case (see model migration 0.2.31). Any additional use of this function should perform heavy
        # testing.

        async with snap.getNodeEditor(node) as proto:
            await proto.set(propname, valu, norminfo={})

        return node
