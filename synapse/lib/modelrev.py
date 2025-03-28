import regex
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled

import synapse.models.infotech as s_infotech

logger = logging.getLogger(__name__)

maxvers = (0, 2, 33)

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
            ((0, 2, 32), self.revModel_0_2_32),
            ((0, 2, 33), self.revModel_0_2_33),
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
        migr = await ModelMigration_0_2_31.anit(self.core, layers)
        await migr.revModel_0_2_31()
        await self._normFormSubs(layers, 'it:sec:cpe')

    async def revModel_0_2_32(self, layers):
        await self._normPropValu(layers, 'transport:air:craft:model')
        await self._normPropValu(layers, 'transport:sea:vessel:model')

    async def revModel_0_2_33(self, layers):
        await self._propToForm(layers, 'transport:sea:vessel:name', 'entity:name')

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
    async def anit(cls, core, layers):
        self = cls()

        self.core = core
        self.layers = layers

        self.meta = {'time': s_common.now(), 'user': self.core.auth.rootuser.iden}

        self.editcount = 0
        self.nodeedits = {}

        self.nodes = await s_spooled.Dict.anit(dirn=self.core.dirn)
        self.todos = await s_spooled.Set.anit(dirn=self.core.dirn)

        self.core.onfini(self.nodes)
        self.core.onfini(self.todos)

        try:
            await self.core.getCoreQueue('model_0_2_31:nodes')
            self.hasq = True
        except s_exc.NoSuchName:
            self.hasq = False

        return self

    async def _queueEdit(self, layriden, edit):
        self.nodeedits.setdefault(layriden, {})
        buid, formname, edits = edit
        self.nodeedits[layriden].setdefault(buid, (buid, formname, []))
        self.nodeedits[layriden][buid][2].extend(edits)
        self.editcount += 1

        if self.editcount >= 1000: # pragma: no cover
            await self._flushEdits()

    async def _flushEdits(self):
        for layriden, layredits in self.nodeedits.items():
            layer = self.core.getLayer(layriden)
            if layer is None: # pragma: no cover
                continue

            await layer.storNodeEditsNoLift(list(layredits.values()), self.meta)

        self.editcount = 0
        self.nodeedits = {}

    # NOTE: For the edit* functions below, we only need precise state tracking for nodes and properties. Don't precisely
    # track the rest.
    async def editNodeAdd(self, layriden, buid, formname, formvalu, stortype):
        if not self.nodes.has(buid):

            node = {
                'formname': formname,
                'formvalu': formvalu,
                'sodes': {},
                'nodedata': {},
                'n1edges': {},
                'n2edges': {},
            }
            await self.nodes.set(buid, node)

        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_NODE_ADD, (formvalu, stortype), ()),
            )),
        )

    async def editPropSet(self, layriden, buid, formname, propname, newvalu, oldvalu, stortype):
        assert self.nodes.has(buid)
        node = self.getNode(buid)

        sode = node['sodes'].get(layriden, {})
        node['sodes'][layriden] = sode

        props = sode.get('props', {})
        sode['props'] = props

        if oldvalu is not None:
            assert props.get(propname) == (oldvalu, stortype), f'GOT: {props.get(propname)} EXPECTED: {(oldvalu, stortype)}'
        props[propname] = (newvalu, stortype)

        await self.nodes.set(buid, node)

        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_PROP_SET, (propname, newvalu, oldvalu, stortype), ()),
            )),
        )

    async def editTagSet(self, layriden, buid, formname, tagname, newvalu, oldvalu):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_TAG_SET, (tagname, newvalu, oldvalu), ()),
            )),
        )

    async def editTagpropSet(self, layriden, buid, formname, tagname, propname, newvalu, oldvalu, stortype):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_TAGPROP_SET, (tagname, propname, newvalu, oldvalu, stortype), ()),
            )),
        )

    async def editNodedataSet(self, layriden, buid, formname, name, newvalu, oldvalu):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_NODEDATA_SET, (name, newvalu, oldvalu), ()),
            )),
        )

    async def editEdgeAdd(self, layriden, buid, formname, verb, iden):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_EDGE_ADD, (verb, iden), ()),
            )),
        )

    async def editNodeDel(self, layriden, buid, formname, formvalu):
        assert self.nodes.has(buid)
        node = self.nodes.pop(buid)

        for layriden in node['layers']:
            await self._queueEdit(layriden,
                (buid, formname, (
                    (s_layer.EDIT_NODE_DEL, formvalu, ()),
                )),
            )

    async def editPropDel(self, layriden, buid, formname, propname, propvalu, stortype):
        assert self.nodes.has(buid)
        node = self.getNode(buid)

        sode = node['sodes'][layriden]
        props = sode.get('props', {})

        assert props.get(propname) == (propvalu, stortype), f'GOT: {props.get(propname)} EXPECTED: {(propvalu, stortype)}'

        props.pop(propname)

        await self.nodes.set(buid, node)

        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_PROP_DEL, (propname, propvalu, stortype), ()),
            )),
        )

    async def editTagDel(self, layriden, buid, formname, tagname, tagvalu):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_TAG_DEL, (tagname, tagvalu), ()),
            )),
        )

    async def editTagpropDel(self, layriden, buid, formname, tagname, propname, propvalu, stortype):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_TAGPROP_DEL, (tagname, propname, propvalu, stortype), ()),
            )),
        )

    async def editNodedataDel(self, layriden, buid, formname, name, valu):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_NODEDATA_DEL, (name, valu), ()),
            )),
        )

    async def editEdgeDel(self, layriden, buid, formname, verb, iden):
        await self._queueEdit(layriden,
            (buid, formname, (
                (s_layer.EDIT_EDGE_DEL, (verb, iden), ()),
            )),
        )

    def getNode(self, buid):
        node = self.nodes.get(buid, {})
        if not node:
            node.setdefault('refs', {})
            node.setdefault('sodes', {})
            node.setdefault('layers', [])
            node.setdefault('n1edges', {})
            node.setdefault('n2edges', {})
            node.setdefault('verdict', None)
            node.setdefault('nodedata', {})
        return node

    async def _loadNode(self, layer, buid, node=None):
        if node is None:
            node = self.getNode(buid)

        sode = await layer.getStorNode(buid)
        if sode:
            node['sodes'].setdefault(layer.iden, {})
            node['sodes'][layer.iden] = sode

            if (formvalu := sode.get('valu')) is not None:
                if node.get('formvalu') is None:
                    node['formvalu'] = formvalu[0]
                    node['formname'] = sode.get('form')

                if layer.iden not in node['layers']:
                    layers = list(node['layers'])
                    layers.append(layer.iden)
                    node['layers'] = layers

        # Get nodedata
        nodedata = [k async for k in layer.iterNodeData(buid)]
        if nodedata:
            node['nodedata'][layer.iden] = nodedata

        # Collect N1 edges
        n1edges = [k async for k in layer.iterNodeEdgesN1(buid)]
        if n1edges:
            node['n1edges'][layer.iden] = n1edges

        # Collect N2 edges
        n2edges = []
        async for verb, iden in layer.iterNodeEdgesN2(buid):
            n2edges.append((verb, iden))

            await self.todos.add(('getvalu', (s_common.uhex(iden), False)))

        if n2edges:
            node['n2edges'][layer.iden] = n2edges

        await self.nodes.set(buid, node)
        return node

    async def revModel_0_2_31(self):

        form = self.core.model.form('it:sec:cpe')

        logger.info(f'Collecting and classifying it:sec:cpe nodes in {len(self.layers)} layers')

        # Pick up and classify all bad CPE nodes
        for idx, layer in enumerate(self.layers):
            logger.debug('Classifying nodes in layer %s %s', idx, layer.iden)

            async for buid, sode in layer.getStorNodesByForm('it:sec:cpe'):

                verdict = 'remove'

                # Delete invalid v2_2 props while we're iterating
                props = sode.get('props', {})
                if (v2_2 := props.get('v2_2')) is not None:
                    propvalu, stortype = v2_2
                    if not s_infotech.isValidCpe22(propvalu):
                        await self._queueEdit(
                            layer.iden,
                            (buid, 'it:sec:cpe', (
                                (s_layer.EDIT_PROP_DEL, ('v2_2', propvalu, stortype), ()),
                            ))
                        )
                    else:
                        verdict = 'migrate'

                if (formvalu := sode.get('valu')) is None:
                    continue

                formvalu = formvalu[0]
                if s_infotech.isValidCpe23(formvalu):
                    continue

                node = self.getNode(buid)
                node['formvalu'] = formvalu
                node['formname'] = 'it:sec:cpe'
                node['verdict'] = verdict
                layers = list(node['layers'])
                layers.append(layer.iden)
                node['layers'] = layers

                await self.nodes.set(buid, node)

        await self._flushEdits()

        invalid = len(self.nodes)
        logger.info(f'Processing {invalid} invalid it:sec:cpe nodes in {len(self.layers)} layers')

        # Pick up all related CPE node info. The majority of the work happens in this loop
        for idx, layer in enumerate(self.layers):
            logger.debug('Processing nodes in layer %s %s', idx, layer.iden)

            for buid, node in self.nodes.items():
                await self._loadNode(layer, buid, node=node)

                formvalu = node.get('formvalu')
                formname = node.get('formname')
                formndef = (formname, formvalu)

                refs = node['refs'].get(layer.iden, [])

                for refinfo in self.getRefInfo(formname):
                    (refform, refprop, reftype, isarray, isro) = refinfo

                    if reftype == 'ndef':
                        propvalu = formndef
                    else:
                        propvalu = formvalu

                    async for refbuid, refsode in self.getSodeByPropValuNoNorm(layer, refform, refprop, propvalu):
                        # Save the reference info
                        refs.append((s_common.ehex(refbuid), refinfo))

                        # Add a todo to get valu and refs to the new nodes
                        await self.todos.add(('getvalu', (refbuid, True)))

                if refs:
                    node['refs'][layer.iden] = refs

                await self.nodes.set(buid, node)

        logger.info('Processing invalid it:sec:cpe node references (this may happen multiple times)')

        # Collect sources, direct references, second-degree references, etc.
        while len(self.todos):
            # Copy the list of todos and then clear the original list. This makes it so we will process all the todos
            # but we can add new todos (that will iterate over all the layers) below to gather supporting data as
            # needed.
            todotmp = await self.todos.copy()
            await self.todos.clear()

            for idx, layer in enumerate(self.layers):
                logger.debug('Processing references in layer %s %s', idx, layer.iden)

                async for entry in todotmp:
                    match entry:
                        case ('getvalu', (buid, fullnode)):
                            if fullnode:
                                node = await self._loadNode(layer, buid)
                                formvalu = node.get('formvalu')
                                if formvalu is None:
                                    continue

                                formname = node.get('formname')

                                await self.todos.add(('getrefs', (buid, formname, formvalu)))
                            else:
                                sode = await layer.getStorNode(buid)

                                if (formvalu := sode.get('valu')) is None:
                                    continue

                                formvalu = formvalu[0]
                                formname = sode.get('form')

                                node = self.getNode(buid)
                                node['formvalu'] = formvalu
                                node['formname'] = formname
                                layers = list(node['layers'])
                                layers.append(layer.iden)
                                node['layers'] = layers

                                await self.nodes.set(buid, node)

                        case ('getrefs', (buid, formname, formvalu)):

                            node = self.getNode(buid)
                            formndef = (formname, formvalu)

                            node.setdefault('refs', {})
                            refs = node['refs'].get(layer.iden, [])

                            for refinfo in self.getRefInfo(formname):
                                (refform, refprop, reftype, isarray, isro) = refinfo

                                if reftype == 'ndef':
                                    propvalu = formndef
                                else:
                                    propvalu = formvalu

                                async for refbuid, refsode in self.getSodeByPropValuNoNorm(layer, refform, refprop, propvalu):
                                    # Save the reference info
                                    refs.append((s_common.ehex(refbuid), refinfo))

                                    # Add a todo to get valu and refs to the new nodes
                                    await self.todos.add(('getvalu', (refbuid, True)))

                            if refs:
                                node['refs'][layer.iden] = refs

                            await self.nodes.set(buid, node)

            await todotmp.fini()

        logger.info(f'Migrating/removing {invalid} invalid it:sec:cpe nodes')

        count = 0
        removed = 0
        migrated = 0
        for buid, node in self.nodes.items():
            action = node.get('verdict')

            if action is None:
                continue

            if action == 'migrate':
                propvalu = None
                for layriden, sode in node.get('sodes').items():
                    props = sode.get('props', {})
                    propvalu, stortype = props.get('v2_2', (None, None))
                    if propvalu is not None:
                        break

                newvalu, _ = form.type.norm(propvalu)
                await self.moveNode(buid, newvalu)

                migrated += 1

            elif action == 'remove':
                newvalu = None
                # Before removing the node, iterate over the sodes looking for a good :v2_2 value
                for layriden, sode in node.get('sodes').items():
                    props = sode.get('props', {})
                    propvalu, stortype = props.get('v2_2', (None, None))
                    if propvalu is None:
                        continue

                    newvalu, _ = form.type.norm(propvalu)
                    # This prop is going to be the new primary value so delete the secondary prop
                    await self.editPropDel(layriden, buid, 'it:sec:cpe', 'v2_2', propvalu, stortype)

                    # Oh yeah! Migrate the node instead of removing it
                    await self.moveNode(buid, newvalu)

                    migrated += 1
                    break

                else:
                    await self.removeNode(buid)
                    removed += 1

            count = migrated + removed
            if count % 1000 == 0: # pragma: no cover
                logger.info(f'Processed {count} it:sec:cpe nodes')

        await self._flushEdits()

        logger.info(f'Finished processing {count} it:sec:cpe nodes: {migrated} migrated, {removed} removed')

        await self.todos.fini()
        await self.nodes.fini()

    @s_cache.memoizemethod()
    def getRoProps(self, formname):
        roprops = []

        form = self.core.model.form(formname)
        for propname, prop in form.props.items():
            if prop.info.get('ro', False):
                roprops.append(propname)

        return roprops

    @s_cache.memoizemethod()
    def getRefInfo(self, formname):
        props = []
        props.extend(self.core.model.getPropsByType(formname))
        props.extend(self.core.model.getPropsByType('array'))
        props.extend(self.core.model.getPropsByType('ndef'))

        props = [k for k in props if k.form.name != formname]

        refinfo = []
        for prop in props:

            if prop.form.name == formname: # pragma: no cover
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

    async def removeNode(self, buid):
        assert self.nodes.has(buid)
        node = self.getNode(buid)

        await self.storeNode(buid)

        formname = node.get('formname')
        formvalu = node.get('formvalu')
        formndef = (formname, formvalu)
        refs = node.get('refs')

        # Delete references
        for reflayr, reflist in refs.items():
            for refiden, refinfo in reflist:
                refbuid = s_common.uhex(refiden)
                (refform, refprop, reftype, isarray, isro) = refinfo

                if reftype == 'ndef':
                    propvalu = formndef
                else:
                    propvalu = formvalu

                if isro:
                    await self.removeNode(refbuid)
                    continue

                refnode = self.getNode(refbuid)
                refsode = refnode['sodes'].get(reflayr)

                curv, stortype = refsode['props'].get(refprop, (None, None))

                if isarray:

                    _curv = curv

                    newv = list(_curv).copy()

                    while propvalu in newv:
                        newv.remove(propvalu)

                    if not newv:
                        await self.editPropDel(reflayr, refbuid, refform, refprop, curv, stortype)

                    else:
                        await self.editPropSet(reflayr, refbuid, refform, refprop, newv, curv, stortype)

                else:
                    await self.editPropDel(reflayr, refbuid, refform, refprop, curv, stortype)

        await self.delNode(buid)

    async def storeNode(self, buid):
        assert self.nodes.has(buid)
        node = self.getNode(buid)

        formname = node.get('formname')
        formvalu = node.get('formvalu')

        sources = set()
        # Resolve sources
        n2edges = {}
        for layriden, edges in node['n2edges'].items():
            n2edges.setdefault(layriden, [])

            for verb, n2iden in edges:
                n2buid = s_common.uhex(n2iden)
                assert self.nodes.has(n2buid)
                n2node = self.nodes.get(n2buid)
                if n2node is None: # pragma: no cover
                    continue

                n2edges[layriden].append((verb, n2iden, n2node['formname']))

                if verb == 'seen':
                    formvalu = n2node.get('formvalu')
                    assert formvalu is not None
                    sources.add(formvalu)

        # Make some changes before serializing
        item = s_msgpack.deepcopy(node)
        item.pop('verdict', None)
        item['iden'] = s_common.ehex(buid)
        item['sources'] = list(sources)
        item['n2edges'] = n2edges

        roprops = self.getRoProps(formname)
        for layriden, sode in node['sodes'].items():
            props = sode.get('props')
            if props is None: # pragma: no cover
                continue

            props = {name: valu for name, valu in list(props.items()) if name not in roprops}
            if props:
                item['sodes'][layriden]['props'] = props
            else:
                item['sodes'][layriden].pop('props')

        if not self.hasq:
            await self.core.addCoreQueue('model_0_2_31:nodes', {})
            self.hasq = True

        await self.core.coreQueuePuts('model_0_2_31:nodes', (item,))

    async def getSodeByPropValuNoNorm(self, layer, formname, propname, valu, cmpr='='):
        prop = self.core.model.reqProp(f'{formname}:{propname}')

        stortype = prop.type.stortype

        # Normally we'd call proptype.getStorCmprs() here to get the cmprvals
        # but getStorCmprs() calls norm() which we're  trying to avoid so build
        # cmprvals manually here.

        if prop.type.isarray:
            stortype &= (~s_layer.STOR_FLAG_ARRAY)
            liftfunc = layer.liftByPropArray
        else:
            liftfunc = layer.liftByPropValu

        cmprvals = ((cmpr, valu, stortype),)

        async for _, buid, sode in liftfunc(formname, propname, cmprvals):
            yield buid, sode

    async def delNode(self, buid):
        assert self.nodes.has(buid)
        node = self.getNode(buid)

        formname = node.get('formname')
        formvalu = node.get('formvalu')

        # Edits
        for layriden, sode in node['sodes'].items():
            props = sode.get('props', {}).copy()
            for propname, propvalu in props.items():
                propvalu, stortype = propvalu
                await self.editPropDel(layriden, buid, formname, propname, propvalu, stortype)

            tags = sode.get('tags', {})
            for tagname, tagvalu in tags.items():
                await self.editTagDel(layriden, buid, formname, tagname, tagvalu)

            tagprops = sode.get('tagprops', {})
            for tagname, propvalus in tagprops.items():
                for propname, propvalu in propvalus.items():
                    propvalu, stortype = propvalu
                    await self.editTagpropDel(layriden, buid, formname, tagname, propname, propvalu, stortype)

        # Nodedata
        for layriden, data in node['nodedata'].items():
            for name, valu in data:
                await self.editNodedataDel(layriden, buid, formname, name, valu)

        # Edges
        for layriden, edges in node['n1edges'].items():
            for verb, iden in edges:
                await self.editEdgeDel(layriden, buid, formname, verb, iden)

        for layriden, edges in node['n2edges'].items():
            for verb, iden in edges:
                n2buid = s_common.uhex(iden)

                n2node = self.nodes.get(n2buid)
                if n2node is None: # pragma: no cover
                    continue

                n2form = n2node.get('formname')
                await self.editEdgeDel(layriden, n2buid, n2form, verb, s_common.ehex(buid))

        # Node
        await self.editNodeDel(layriden, buid, formname, formvalu)

    async def moveNode(self, buid, newvalu):
        assert self.nodes.has(buid)
        node = self.getNode(buid)

        formname = node.get('formname')
        formvalu = node.get('formvalu')
        refs = node.get('refs')

        oldndef = (formname, formvalu)
        newndef = (formname, newvalu)
        newbuid = s_common.buid((formname, newvalu))

        form = self.core.model.reqForm(formname)

        # Node
        for layriden in node['layers']:
            # Create the new node in the same layers as the old node
            await self.editNodeAdd(layriden, newbuid, formname, newvalu, form.type.stortype)

        # Edits
        for layriden, sode in node['sodes'].items():
            props = sode.get('props', {})
            for propname, propvalu in props.items():
                propvalu, stortype = propvalu
                await self.editPropSet(layriden, newbuid, formname, propname, propvalu, None, stortype)

            tags = sode.get('tags', {})
            for tagname, tagvalu in tags.items():
                await self.editTagSet(layriden, newbuid, formname, tagname, tagvalu, None)

            tagprops = sode.get('tagprops', {})
            for tagname, propvalus in tagprops.items():
                for propname, propvalu in propvalus.items():
                    propvalu, stortype = propvalu

                    await self.editTagpropSet(layriden, newbuid, formname, tagname, propname, propvalu, None, stortype)

        # Nodedata
        for layriden, data in node['nodedata'].items():
            for name, valu in data:
                await self.editNodedataSet(layriden, newbuid, formname, name, valu, None)

        # Edges
        for layriden, edges in node['n1edges'].items():
            for verb, iden in edges:
                await self.editEdgeAdd(layriden, newbuid, formname, verb, iden)

        for layriden, edges in node['n2edges'].items():
            for verb, iden in edges:
                n2buid = s_common.uhex(iden)

                n2node = self.nodes.get(n2buid)
                if n2node is None: # pragma: no cover
                    continue

                n2form = n2node.get('formname')
                await self.editEdgeAdd(layriden, n2buid, n2form, verb, s_common.ehex(newbuid))

        # Move references
        for reflayr, reflist in refs.items():
            for refiden, refinfo in reflist:
                refbuid = s_common.uhex(refiden)
                (refform, refprop, reftype, isarray, isro) = refinfo

                if isro:
                    await self.removeNode(refbuid)
                    continue

                if reftype == 'ndef':
                    oldpropv = oldndef
                    newpropv = newndef
                else:
                    oldpropv = formvalu
                    newpropv = newvalu

                refnode = self.getNode(refbuid)
                refsode = refnode['sodes'].get(reflayr)

                curv, stortype = refsode.get('props', {}).get(refprop, (None, None))
                assert stortype is not None

                if isarray:

                    _curv = curv

                    newv = list(_curv).copy()

                    while oldpropv in newv:
                        newv.remove(oldpropv)

                    newv.append(newpropv)

                    await self.editPropSet(reflayr, refbuid, refform, refprop, newv, curv, stortype)

                else:
                    await self.editPropSet(reflayr, refbuid, refform, refprop, newpropv, curv, stortype)

        await self.delNode(buid)
