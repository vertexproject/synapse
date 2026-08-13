import copy
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

def getIvalStorVirts(ival, virts, proptype):
    names = proptype.opts.get('names') or {}
    parts = [
        'min',
        'max',
        'duration',
    ]

    retn = {}
    for idx, canon in enumerate(parts):
        name = names.get(canon, canon)
        retn[name] = ival[idx]

    name = names.get('precision', 'precision')
    if virts and (prec := virts.get('precision')):
        retn[name] = prec[0]
    else:
        retn[name] = proptype.prec

    return retn

def getPriceRangeStorVirts(chng, virts, proptype):
    names = proptype.opts.get('names') or {}
    if 'econ:pricerange' in proptype.types:
        parts = ['min', 'max', 'delta']
    else:
        parts = ['start', 'end', 'delta']
    retn = {}
    for idx, canon in enumerate(parts):
        name = names.get(canon, canon)
        retn[name] = chng[idx]

    if len(chng) > 3:
        name = names.get('rate', 'rate')
        retn[name] = chng[3]

    name = names.get('currency', 'currency')
    if virts and (curr := virts.get('currency')):
        retn[name] = curr[0]

    return retn

storvirts = {
    s_layer.STOR_TYPE_IVAL: getIvalStorVirts,
    s_layer.STOR_TYPE_PRICERANGE: getPriceRangeStorVirts
}

def getPropVirts(modl, valt):
    '''
    Return the virtual property values for a storage property tuple.

    Args:
        modl (synapse.datamodel.Model): The data model.
        valt (tuple): A storage (tval, stortype, storvirts) property tuple.

    Returns:
        (dict): The virtual property values by name. A non-array value carries a
                ``type`` entry naming the concrete type of the value. An array
                value carries a ``size`` entry instead.
    '''
    valu, stortype, vprops = valt

    retn = {}

    stortype = stortype & s_layer.STOR_MASK_POLY

    if stortype & s_layer.STOR_FLAG_ARRAY:

        for vname, vvals in vprops.items():
            if vname[0] == '_':
                continue

            retn[vname] = [(vval[0], vcnt) for vval, vcnt in vvals.items()]

        retn['size'] = len(valu)

        return retn

    if vprops is not None:
        for vname, vval in vprops.items():
            if vname[0] == '_':
                continue

            retn[vname] = vval[0]

    retn['type'] = valu[0]

    if (virtfunc := storvirts.get(stortype)) is not None:
        proptype = modl.type(valu[0])
        retn.update(virtfunc(valu[1], vprops, proptype))

    return retn

class NodeBase:

    __slots__ = ()

    def repr(self, name=None, defv=None):

        virt = None
        if name is not None:
            parts = name.strip().split('.')
            if len(parts) > 1:
                name = parts[0] or None
                virt = parts[1]

        if name is None:
            typeitem = self.form.type
            if virt is None:
                return typeitem.repr(self.valu())

            if (mtyp := self.view.core.model.metatypes.get(virt)) is not None:
                return mtyp.repr(self.getMeta(virt))

            virttype, virtgetr = typeitem.getVirtInfo(virt)
            return virttype.repr(self.valu(getr=virtgetr))

        prop = self.form.props.get(name)
        if prop is None:
            mesg = f'No property named {name}.'
            raise s_exc.NoSuchProp(mesg=mesg, form=self.form.name, prop=name)

        typeitem = prop.type

        if virt is None:
            valu, virts = self.getWithVirts(name)
            if valu is None:
                return defv
            return typeitem.reprWithVirts(valu, virts)

        if typeitem.virts.get(virt) is None:
            if (valu := self.get(name)) is None:
                return defv
            typeitem = self.view.core.model.type(valu[0])

        virttype, virtgetr = typeitem.getVirtInfo(virt)

        if (valu := self.get(name, getr=virtgetr)) is None:
            return defv
        return virttype.repr(valu)

    def reprs(self):
        '''
        Return a dictionary of repr values for props whose repr is different than
        the system mode value.
        '''
        props = self.getProps()
        return self._getPropReprs(props)

    def _reqValidProp(self, name):
        prop = self.form.prop(name)
        if prop is None:
            mesg = f'No property named {name} on form {self.form.name}.'
            raise s_exc.NoSuchProp(mesg=mesg)
        return prop

    def _getPropRepr(self, prop, valu, virts):
        '''
        Return the repr for a property value, or None if it adds nothing over
        the system mode value.
        '''
        rval = prop.type.reprWithVirts(valu, virts)

        if prop.type.isarray:
            if rval == [v[1] for v in valu]:
                return None

        elif rval == valu[1]:
            return None

        return rval

    def _getPropReprs(self, props):

        reps = {}
        for name, valu in props.items():

            prop = self.form.prop(name)
            if prop is None:
                continue

            _, virts = self.getWithVirts(name)

            if (rval := self._getPropRepr(prop, valu, virts)) is not None:
                reps[name] = rval

        return reps

    def _addPodeRepr(self, pode):

        rval = self.repr()
        if rval is not None and rval != self.ndef[1]:
            pode[1]['repr'] = rval

    def _packTags(self, tags, dorepr=False):
        '''
        Return the packed tag envelopes.

        A tag envelope carries no ``t``, since a tag value is always an ival.
        '''
        retn = {}

        ivaltype = self.form.modl.type('ival')

        for name, valu in tags.items():

            info = {}

            if dorepr and valu != (None, None, None):
                info['r'] = ivaltype.repr(valu)

            retn[name] = (valu, info)

        return retn

    def _packTagProps(self, tagprops, dorepr=False):
        '''
        Return the packed tag property envelopes.

        A tag property envelope carries no ``t``, since a tag property name is
        globally unique and names its own type within the model.
        '''
        retn = {}

        for tag, propdict in tagprops.items():

            packed = retn[tag] = {}

            for name, valu in propdict.items():

                info = {}

                if dorepr and (prop := self.form.modl.tagprop(name)) is not None:

                    rval = prop.type.repr(valu)
                    if rval is not None and rval != valu:
                        info['r'] = rval

                packed[name] = (valu, info)

        return retn

    def _packProps(self, storprops, dorepr=False, dovirts=False):
        '''
        Return the packed property envelopes for a set of storage property tuples.

        Args:
            storprops (dict): Storage (tval, stortype, storvirts) tuples by name.
            dorepr (bool): Include repr values.
            dovirts (bool): Include virtual property values.

        Returns:
            (dict): A (valu, info) envelope by property name. See pack() for
                    the reserved info keys.
        '''
        retn = {}

        for name, valt in storprops.items():

            prop = self.form.prop(name)
            if prop is None:
                # extra model data from a lower layer has no type or repr.
                retn[name] = (valt[0], {})
                continue

            valu = valt[0]
            info = {}

            if prop.type.isarray:

                elems = []
                for elem in valu:

                    einfo = {'t': elem[0]}

                    if dorepr and (erepr := prop.type.arraytype.repr(elem)) != elem[1]:
                        einfo['r'] = erepr

                    elems.append((elem[1], einfo))

                pvalu = tuple(elems)

                # An array container repr is never suppressed. It is the only
                # thing which lets a consumer without the model render an array
                # without inspecting the shape of the value.
                if dorepr:
                    info['r'] = prop.type.repr(valu)

            else:
                pvalu = valu[1]
                info['t'] = valu[0]

                if dorepr and (rval := self._getPropRepr(prop, valu, valt[2])) is not None:
                    info['r'] = rval

            if dovirts and valt[1] is not None:

                pvirts = getPropVirts(self.form.modl, valt)
                pvirts.pop('type', None)

                if pvirts:
                    info['v'] = {vname: (vval, {}) for (vname, vval) in pvirts.items()}

            retn[name] = (pvalu, info)

        return retn

    def _getTagTree(self):

        root = (None, {})
        for tag in self.getTagNames():
            node = root

            for part in tag.split('.'):

                kidn = node[1].get(part)

                if kidn is None:

                    full = part
                    if node[0] is not None:
                        full = f'{node[0]}.{full}'

                    kidn = node[1][part] = (full, {})

                node = kidn

        return root

    def getTagNames(self):
        return ()

    async def getStorNodes(self):
        return ()

    def getByLayer(self):
        return {}

    def valuvirts(self, defv=None):
        return defv

    def hasPropAltsValu(self, prop, valu):
        # valu must be normalized in advance
        prophash = prop.type.typehash
        for prop in prop.getAlts():
            if prop.type.isarray and prop.type.arraytype.typehash is prophash:
                arryvalu = self.get(prop.name)
                if arryvalu is not None and valu in arryvalu:
                    return True
            else:
                if self.get(prop.name) == valu:
                    return True

        return False

    async def iterEdgesN1(self, verb=None):
        if False:  # pragma: no cover
            yield None

    async def iterEdgesN2(self, verb=None):
        if False:  # pragma: no cover
            yield None

    async def iterEdgeVerbs(self, n2nid):
        if False:  # pragma: no cover
            yield None

class Node(NodeBase):
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    __slots__ = ('view', 'nid', '_ndef', 'soderefs', 'sodes', 'form', '__weakref__')

    def __init__(self, view, nid, ndef, soderefs):
        self.view = view

        self.nid = nid
        self._ndef = ndef

        # must hang on to these to keep the weakrefs alive
        self.soderefs = soderefs

        self.sodes = [sref.sode for sref in soderefs]

        self.form = view.core.model.form(ndef[0])

    @property
    def ndef(self):
        # Resolve the ndef from the sodes (like props) so it can never go stale.
        # The form is fixed; only the primary value can change (case-retention re-adds).
        # Store in _ndef and fall back to it when no layer has a valu, so a held
        # reference to a deleted node still reports its last-known ndef.
        for sode in self.sodes:
            valu = sode.get('valu')
            if valu is not None:
                self._ndef = (self.form.name, valu[0])
                return self._ndef

        return self._ndef

    async def getStorNodes(self):
        '''
        Return a list of the raw storage nodes for each layer.
        '''
        return copy.deepcopy(self.sodes)

    def getByLayer(self):
        '''
        Return a dictionary that translates the node's bylayer dict to a primitive.
        '''
        retn = collections.defaultdict(dict)
        for indx, sode in enumerate(self.sodes):
            if sode.get('antivalu') is not None:
                return(retn)

            iden = self.view.layers[indx].iden

            if sode.get('valu') is not None:
                retn.setdefault('ndef', iden)

            for prop in sode.get('props', {}).keys():
                retn['props'].setdefault(prop, iden)

            for prop in sode.get('antiprops', {}).keys():
                retn['props'].setdefault(prop, iden)

            for tag in sode.get('tags', {}).keys():
                retn['tags'].setdefault(tag, iden)

            for tag in sode.get('antitags', {}).keys():
                retn['tags'].setdefault(tag, iden)

            for tag, props in sode.get('tagprops', {}).items():
                if len(props) > 0 and tag not in retn['tagprops']:
                    retn['tagprops'][tag] = {}

                for prop in props.keys():
                    retn['tagprops'][tag].setdefault(prop, iden)

            for tag, props in sode.get('antitagprops', {}).items():
                if len(props) > 0 and tag not in retn['tagprops']:
                    retn['tagprops'][tag] = {}

                for prop in props.keys():
                    retn['tagprops'][tag].setdefault(prop, iden)

        return dict(retn)

    def __repr__(self):
        return f'Node{{{self.pack()}}}'

    async def addEdge(self, verb, n2nid, n2form=None, extra=None):
        async with self.view.getNodeEditor(self) as editor:
            return await editor.addEdge(verb, n2nid, n2form=n2form)

    async def delEdge(self, verb, n2nid, extra=None):
        async with self.view.getNodeEditor(self) as editor:
            return await editor.delEdge(verb, n2nid)

    async def iterEdgesN1(self, verb=None):
        async for edge in self.view.iterNodeEdgesN1(self.nid, verb=verb, stop=self.lastlayr()):
            yield edge

    async def iterEdgesN2(self, verb=None):
        async for edge in self.view.iterNodeEdgesN2(self.nid, verb=verb):
            yield edge

    async def iterEdgeVerbs(self, n2nid):
        async for verb in self.view.iterEdgeVerbs(self.nid, n2nid, stop=self.lastlayr()):
            yield verb

    async def storm(self, runt, text, opts=None, path=None):
        '''
        Args:
            path (Path):
                If set, then vars from path are copied into the new runtime, and vars are copied back out into path
                at the end

        Note:
            If opts is not None and opts['vars'] is set and path is not None, then values of path vars take precedent
        '''
        query = await self.view.core.getStormQuery(text)

        if opts is None:
            opts = {}

        opts.setdefault('vars', {})
        if path is not None:
            opts['vars'].update(path.vars)

        async with runt.getSubRuntime(query, opts=opts) as subr:

            subr.addInput(self)

            async for subn, subp in subr.execute():
                yield subn, subp

            if path is not None:
                path.vars.update(subr.vars)

    async def filter(self, runt, text, opts=None, path=None):
        async for item in self.storm(runt, text, opts=opts, path=path):
            return False
        return True

    def intnid(self):
        return s_common.int64un(self.nid)

    def pack(self, dorepr=False, virts=False):
        '''
        Return the serializable/packed version of the node.

        Args:
            dorepr (bool): Include repr information for human readable versions of properties.
            virts (bool): Include virtual properties.

        Returns:
            (tuple): An (ndef, info) node tuple.

        Each value within the ``props`` dict is a ``(valu, info)`` envelope. The
        two element envelope is invariant; the info dict keys are not. Consumers
        index ``[0]`` and ``[1]`` unconditionally and must never inspect lengths
        or element types to decide what they are holding.

        The reserved info keys are:

            ``t``: The concrete type name of the value.
            ``r``: A human readable rendering of the value.
            ``v``: Virtual property values, as ``{name: (valu, info)}``.

        New keys are registered here first. Model derived names never appear at
        the top level of an info dict; they appear only as keys within ``v``.

        ``t`` is present only where the concrete type is carried by the data
        rather than derivable from the model. It is present on a scalar property
        and on each array element, whose types vary per value, and absent on an
        array container, a tag, a tag property, and a property which is not in
        the model.

        Envelope nesting is bounded at one level: an array member is a scalar
        envelope, never another array. Array of array is rejected at type
        definition time and a comp field may not be an array.
        '''

        pode = (self.ndef, {
            'nid': s_common.int64un(self.nid),
            'meta': self.getMetaDict(),
            'tags': self._packTags(self._getTagsDict(), dorepr=dorepr),
            'props': self._packProps(self._getStorProps(), dorepr=dorepr, dovirts=virts),
            'tagprops': self._packTagProps(self._getTagPropsDict(), dorepr=dorepr),
        })

        pode[1]['n1verbs'] = self.getEdgeCounts()
        pode[1]['n2verbs'] = self.getEdgeCounts(n2=True)

        if virts:
            pode[1]['virts'] = vvals = {}

            for sode in self.sodes:
                if sode.get('antivalu') is not None:
                    break

                if (valu := sode.get('valu')) is not None:
                    valu, stortype, vprops = valu

                    if vprops is not None:
                        for vname, vval in vprops.items():
                            if vname[0] == '_':
                                continue

                            vvals[vname] = vval[0]
                    break

        if dorepr:
            self._addPodeRepr(pode)

        return pode

    def getEdgeCounts(self, verb=None, n2=False):

        if n2:
            keys = (('n2verbs', 1), ('n2antiverbs', -1))
        else:
            keys = (('n1verbs', 1), ('n1antiverbs', -1))

        ecnts = {}

        for sode in self.sodes:
            if not n2 and sode.get('antivalu') is not None:
                break

            for (key, inc) in keys:
                if (verbs := sode.get(key)) is None:
                    continue

                if verb is not None:
                    if (forms := verbs.get(verb)) is not None:
                        if (formcnts := ecnts.get(verb)) is None:
                            ecnts[verb] = formcnts = {}

                        for form, cnt in forms.items():
                            formcnts[form] = formcnts.get(form, 0) + (cnt * inc)
                else:
                    for vkey, forms in verbs.items():
                        if (formcnts := ecnts.get(vkey)) is None:
                            ecnts[vkey] = formcnts = {}

                        for form, cnt in forms.items():
                            formcnts[form] = formcnts.get(form, 0) + (cnt * inc)

        retn = {}
        for verb, formcnts in ecnts.items():
            real = {form: cnt for form, cnt in formcnts.items() if cnt > 0}
            if real:
                retn[verb] = real

        return retn

    async def getEmbeds(self, embeds):
        '''
        Return a dictionary of property embeddings.
        '''
        retn = {}
        cache = {}
        view = self.view

        async def walk(n, p):

            valu = n.get(p)
            if valu is None:
                return None

            prop = n.form.prop(p)
            if prop is None:
                return None

            if not prop.type.hasforms:
                return None

            form, nval = valu
            if (ntyp := view.core.model.type(form)) is None:
                return None

            nval = view.wlyr.stortypes[ntyp.stortype].nidNorm(nval)
            nid = view.core.getNidByNdef((form, nval))
            if nid is None:
                return None

            step = cache.get(nid, s_common.novalu)
            if step is s_common.novalu:
                step = cache[nid] = await view.getNodeByNid(nid)

            return step

        for nodepath, relprops in embeds.items():

            steps = nodepath.split('::')

            node = self
            for propname in steps:
                node = await walk(node, propname)
                if node is None:
                    break

            if node is None:
                continue

            embdnode = retn.get(nodepath)
            if embdnode is None:
                embdnode = retn[nodepath] = {
                    '$nid': s_common.int64un(node.nid),
                    '$form': node.form.name,
                }

            storprops = {}

            for relp in relprops:

                if not relp:
                    continue

                if relp[0] == '.':
                    metaname = relp[1:]
                    if metaname in view.core.model.metatypes:
                        # an embed is shaped like a property, so a meta value is
                        # carried in an envelope like every other embedded value.
                        embdnode[relp] = (node.getMeta(metaname), {})
                    continue

                valt = node.getRawWithLayer(relp)[0]

                if valt[0] is None:
                    embdnode[relp] = None
                    continue

                storprops[relp] = valt

            # pack through the embedded node so an embed is shaped exactly like
            # a property on the node it came from.
            embdnode.update(node._packProps(storprops, dovirts=True))

        return retn

    def getNodeRefs(self):
        '''
        Return a list of (prop, (form, valu)) refs out for the node.
        '''
        retn = []

        refs = self.form.getRefsOut()

        for name, dest in refs.get('prop', ()):
            valu = self.get(name)
            if valu is None:
                continue

            retn.append((name, (dest, valu)))

        for name in refs.get('ndef', ()):
            valu = self.get(name)
            if valu is None:
                continue
            retn.append((name, valu))

        for name, dest in refs.get('array', ()):

            valu = self.get(name)
            if valu is None:
                continue

            for item in valu:
                retn.append((name, (dest, item)))

        for name in refs.get('ndefarray', ()):
            if (valu := self.get(name)) is None:
                continue

            for item in valu:
                retn.append((name, item))

        return retn

    async def setValue(self, valu):
        if self.view.wlyr.readonly:
            mesg = 'Cannot set value in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        async with self.view.getNodeEditor(self) as editor:
            return await editor.setValue(valu)

    async def set(self, name, valu, norminfo=None):
        '''
        Set a property on the node.

        Args:
            name (str): The name of the property.
            valu (obj): The value of the property.
            norminfo (obj): Norm info for valu if it has already been normalized.

        Returns:
            (bool): True if the property was changed.
        '''
        if self.view.wlyr.readonly:
            mesg = 'Cannot set property in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        async with self.view.getNodeEditor(self) as editor:
            return await editor.set(name, valu, norminfo=norminfo)

    def has(self, name, getr=None):

        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return False

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return False

            props = sode.get('props')
            if props is None:
                continue

            if (valt := props.get(name)) is not None:
                if getr and getr(valt) is None:
                    return False
                return True

        return False

    def lastlayr(self):
        for indx, sode in enumerate(self.sodes):
            if sode.get('antivalu') is not None:
                return indx

    def istomb(self):
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return True

            if (valu := sode.get('valu')) is not None:
                return False

        return False

    def hasvalu(self):
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return False

            if (valu := sode.get('valu')) is not None:
                return True

        return False

    def valu(self, defv=None, getr=None):
        if getr is None:
            return self.ndef[1]

        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defv

            if (valu := sode.get('valu')) is not None:
                return getr(valu)

        return defv

    def valuvirts(self, defv=None):
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defv

            if (valu := sode.get('valu')) is not None:
                return valu[-1]

        return defv

    def get(self, name, defv=None, getr=None):
        '''
        Return a secondary property or tag value from the Node.

        Args:
            name (str): The name of a secondary property or tag.

        Returns:
            (obj): The secondary property or tag value, or None.
        '''
        if name.startswith('#'):
            return self.getTag(name[1:], defval=defv)

        elif '.' in name:
            parts = name.split('.')
            name = parts[0]
            vname = parts[1]

            if not name:
                if (mtyp := self.view.core.model.metatypes.get(vname)) is not None:
                    return self.getMeta(vname)

                getr = self.form.type.getVirtGetr(vname)
                return self.valu(getr=getr)
            else:
                if (prop := self.form.props.get(name)) is None:
                    raise s_exc.NoSuchProp.init(name)

                getr = prop.type.getVirtGetr(vname)

        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defv

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return defv

            if (item := sode.get('props')) is None:
                continue

            if (valt := item.get(name)) is not None:
                if getr:
                    return getr(valt)
                return valt[0]

        return defv

    def getWithVirts(self, name, defv=None):
        '''
        Return a secondary property with virtual property information from the Node.

        Args:
            name (str): The name of a secondary property.

        Returns:
            (tuple): The secondary property and virtual property information or (defv, None).
        '''
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defv, None

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return defv, None

            if (item := sode.get('props')) is None:
                continue

            if (valt := item.get(name)) is not None:
                return valt[0], valt[2]

        return defv, None

    def getWithLayer(self, name, defv=None, getr=None):
        '''
        Return a secondary property value from the Node with the index of the sode.

        Args:
            name (str): The name of a secondary property.

        Returns:
            (obj): The secondary property value or None.
            (int): Index of the sode or None.
        '''
        for indx, sode in enumerate(self.sodes):
            if sode.get('antivalu') is not None:
                return defv, None

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return defv, None

            if (item := sode.get('props')) is None:
                continue

            if (valt := item.get(name)) is not None:
                if getr:
                    return getr(valt), indx
                return valt[0], indx

        return defv, None

    def getRawWithLayer(self, name, defv=None):
        '''
        Return full secondary property information from the Node and the index of the sode.

        Args:
            name (str): The name of a secondary property.

        Returns:
            (tuple): The raw secondary property information or (defv, None, None).
            (int): Index of the sode or None.
        '''
        for indx, sode in enumerate(self.sodes):
            if sode.get('antivalu') is not None:
                return (defv, None, None), None

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return (defv, None, None), None

            if (item := sode.get('props')) is None:
                continue

            if (valt := item.get(name)) is not None:
                return valt, indx

        return (defv, None, None), None

    def getFromLayers(self, name, strt=0, stop=None, defv=None):
        for sode in self.sodes[strt:stop]:
            if sode.get('antivalu') is not None:
                return defv

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return defv

            if (item := sode.get('props')) is None:
                continue

            if (valt := item.get(name)) is not None:
                return valt[0]

        return defv

    def hasInLayers(self, name, strt=0, stop=None):
        for sode in self.sodes[strt:stop]:
            if sode.get('antivalu') is not None:
                return False

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return False

            if (item := sode.get('props')) is None:
                continue

            if (valt := item.get(name)) is not None:
                return True

        return False

    async def pop(self, name):
        '''
        Remove a property from a node and return the value
        '''
        async with self.view.getNodeEditor(self) as protonode:
            return await protonode.pop(name)

    def hasTag(self, name):
        name = s_chop.tag(name)
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return False

            if (tagtomb := sode.get('antitags')) is not None and tagtomb.get(name):
                return False

            if (tags := sode.get('tags')) is None:
                continue

            if tags.get(name) is not None:
                return True

        return False

    def hasTagInLayers(self, name, strt=0, stop=None):
        name = s_chop.tag(name)
        for sode in self.sodes[strt:stop]:
            if sode.get('antivalu') is not None:
                return False

            if (tagtomb := sode.get('antitags')) is not None and tagtomb.get(name):
                return False

            if (tags := sode.get('tags')) is None:
                continue

            if tags.get(name) is not None:
                return True

        return False

    def getTag(self, name, defval=None):
        name = s_chop.tag(name)
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defval

            if (tagtomb := sode.get('antitags')) is not None and tagtomb.get(name):
                return defval

            if (tags := sode.get('tags')) is None:
                continue

            if (valu := tags.get(name)) is not None:
                return valu

        return defval

    def getTagFromLayers(self, name, strt=0, stop=None, defval=None):
        name = s_chop.tag(name)
        for sode in self.sodes[strt:stop]:
            if sode.get('antivalu') is not None:
                return defval

            if (tagtomb := sode.get('antitags')) is not None and tagtomb.get(name):
                return defval

            if (tags := sode.get('tags')) is None:
                continue

            if (valu := tags.get(name)) is not None:
                return valu

        return defval

    def getTagNames(self):
        names = self._getTagsDict()
        return list(sorted(names.keys()))

    def getTags(self, leaf=False):

        tags = self._getTagsDict()
        if not leaf:
            return list(tags.items())

        # longest first
        retn = []

        # brute force rather than build a tree.  faster in small sets.
        for _, tag, valu in sorted([(len(t), t, v) for (t, v) in tags.items()], reverse=True):

            look = tag + '.'
            if any([r.startswith(look) for (r, rv) in retn]):
                continue

            retn.append((tag, valu))

        return retn

    def getMeta(self, name):
        for sode in self.sodes:
            if (meta := sode.get('meta')) is not None and (valu := meta.get(name)) is not None:
                return valu[0]

    def getMetaDict(self):
        retn = {}

        for sode in reversed(self.sodes):
            if sode.get('antivalu') is not None:
                retn.clear()
                continue

            if (meta := sode.get('meta')) is None:
                continue

            for name, valu in meta.items():
                retn[name] = valu[0]

        return retn

    def getPropNames(self):
        return list(self.getProps().keys())

    def _getStorProps(self):
        '''
        Return the storage (tval, stortype, storvirts) property tuples from the Node.
        '''
        retn = {}

        for sode in reversed(self.sodes):
            if sode.get('antivalu') is not None:
                retn.clear()
                continue

            if (proptomb := sode.get('antiprops')) is not None:
                for name in proptomb.keys():
                    retn.pop(name, None)

            if (props := sode.get('props')) is None:
                continue

            retn.update(props)

        return retn

    def getProps(self, virts=False):

        storprops = self._getStorProps()

        if not virts:
            return {name: valt[0] for (name, valt) in storprops.items()}

        retn = {}
        for name, valt in storprops.items():

            retn[name] = valt[0]

            for vname, vval in getPropVirts(self.form.modl, valt).items():
                retn[f'{name}.{vname}'] = vval

        return retn

    def getStormProps(self):
        '''
        Return the property values as typed values carrying the virts they were stored
        with, for use in the runtime. An array member arrives as a typed value of its own,
        so callers hand the result to tostor() before storing it again.
        '''
        refs = {}

        for name, (valu, styp, virts) in self._getStorProps().items():
            refs[name] = self.form.prop(name).type.tostorm(valu, virts=virts)

        return refs

    def _getTagsDict(self):
        retn = {}

        for sode in reversed(self.sodes):
            if sode.get('antivalu') is not None:
                retn.clear()
                continue

            if (tagtomb := sode.get('antitags')) is not None:
                for name in tagtomb.keys():
                    retn.pop(name, None)

            if (tags := sode.get('tags')) is None:
                continue

            for name, valu in tags.items():
                retn[name] = valu

        return retn

    def _getStorTagProps(self):
        '''
        Return the storage (valu, stortype, storvirts) tag property tuples from the Node,
        keyed by tag name. See _getStorProps() for the property equivalent.
        '''
        retn = collections.defaultdict(dict)

        for sode in reversed(self.sodes):
            if sode.get('antivalu') is not None:
                retn.clear()
                continue

            if (antitags := sode.get('antitagprops')) is not None:
                for tagname, antiprops in antitags.items():
                    for propname in antiprops.keys():
                        retn[tagname].pop(propname, None)

                        if len(retn[tagname]) == 0:
                            retn.pop(tagname)

            if (tagprops := sode.get('tagprops')) is None:
                continue

            for tagname, propvals in tagprops.items():
                for propname, valt in propvals.items():
                    retn[tagname][propname] = valt

        return dict(retn)

    def _getTagPropsDict(self):

        return {tagname: {propname: valt[0] for (propname, valt) in propvals.items()}
                for (tagname, propvals) in self._getStorTagProps().items()}

    def getStormTagProps(self):
        '''
        Return the tag property values as typed values carrying the virts they were
        stored with, the way getStormProps() does for properties.
        '''
        retn = {}

        for tagname, propvals in self._getStorTagProps().items():
            props = {}
            for propname, (valu, styp, virts) in propvals.items():
                ptyp = self.view.core.model.reqTagProp(propname).type
                props[propname] = ptyp.tostorm(valu, virts=virts)

            retn[tagname] = props

        return retn

    async def addTag(self, tag, valu=(None, None, None), norminfo=None):
        '''
        Add a tag to a node.

        Args:
            tag (str): The tag to add to the node.
            valu: The optional tag value.  If specified, this must be a value that
                  norms as a valid time interval as an ival.
            norminfo (obj): Norm info for valu if it has already been normalized.

        Returns:
            None: This returns None.
        '''
        async with self.view.getNodeEditor(self) as protonode:
            await protonode.addTag(tag, valu=valu, norminfo=norminfo)

    async def delTag(self, tag):
        '''
        Delete a tag from the node.
        '''
        async with self.view.getNodeEditor(self) as editor:
            await editor.delTag(tag)

    def getTagProps(self, tag):

        propnames = set()

        for sode in reversed(self.sodes):
            if sode.get('antivalu') is not None:
                propnames.clear()
                continue

            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None:
                    propnames.difference_update(antiprops.keys())

            if (tagprops := sode.get('tagprops')) is None:
                continue

            if (propvals := tagprops.get(tag)) is None:
                continue

            propnames.update(propvals.keys())

        return list(propnames)

    def getTagPropsWithLayer(self, tag):

        props = {}

        for indx in range(len(self.sodes) - 1, -1, -1):
            sode = self.sodes[indx]

            if sode.get('antivalu') is not None:
                props.clear()
                continue

            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None:
                    for propname in antiprops.keys():
                        props.pop(propname, None)

            if (tagprops := sode.get('tagprops')) is None:
                continue

            if (propvals := tagprops.get(tag)) is None:
                continue

            for propname in propvals.keys():
                props[propname] = indx

        return list(props.items())

    def hasTagProp(self, tag, prop):
        '''
        Check if a #foo.bar:baz tag property exists on the node.
        '''
        # TODO discuss caching these while core.nexusoffset is stable?
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return False

            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None and prop in antiprops:
                    return False

            if (tagprops := sode.get('tagprops')) is None:
                continue

            if (propvals := tagprops.get(tag)) is None:
                continue

            if prop in propvals:
                return True

        return False

    def hasTagPropInLayers(self, tag, prop, strt=0, stop=None):
        '''
        Check if a #foo.bar:baz tag property exists in specific layers on the node.
        '''
        # TODO discuss caching these while core.nexusoffset is stable?
        for sode in self.sodes[strt:stop]:
            if sode.get('antivalu') is not None:
                return False

            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None and prop in antiprops:
                    return False

            if (tagprops := sode.get('tagprops')) is None:
                continue

            if (propvals := tagprops.get(tag)) is None:
                continue

            if prop in propvals:
                return True

        return False

    def getTagProp(self, tag, prop, defval=None, getr=None):
        '''
        Return the value (or defval) of the given tag property.
        '''
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defval

            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None and prop in antiprops:
                    return defval

            if (tagprops := sode.get('tagprops')) is None:
                continue

            if (propvals := tagprops.get(tag)) is None:
                continue

            if (valt := propvals.get(prop)) is not None:
                if getr:
                    return getr(valt)
                return valt[0]

        return defval

    def getTagPropWithVirts(self, tag, prop, defval=None):
        '''
        Return a tag property with virtual property information from the Node.

        Args:
            tag (str): The name of the tag.
            prop (str): The name of the property on the tag.

        Returns:
            (tuple): The tag property and virtual property information or (defv, None).
        '''
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defval, None

            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None and prop in antiprops:
                    return defval, None

            if (tagprops := sode.get('tagprops')) is None:
                continue

            if (propvals := tagprops.get(tag)) is None:
                continue

            if (valt := propvals.get(prop)) is not None:
                return valt[0], valt[2]

        return defval, None

    def getTagPropWithLayer(self, tag, prop, defval=None):
        '''
        Return the value (or defval) of the given tag property.
        '''
        for indx, sode in enumerate(self.sodes):
            if sode.get('antivalu') is not None:
                return defval, None

            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None and prop in antiprops:
                    return defval, None

            if (tagprops := sode.get('tagprops')) is None:
                continue

            if (propvals := tagprops.get(tag)) is None:
                continue

            if (valt := propvals.get(prop)) is not None:
                return valt[0], indx

        return defval, None

    async def setTagProp(self, tag, name, valu, norminfo=None):
        '''
        Set the value of the given tag property.
        '''
        async with self.view.getNodeEditor(self) as editor:
            await editor.setTagProp(tag, name, valu, norminfo=norminfo)

    async def delTagProp(self, tag, name):
        async with self.view.getNodeEditor(self) as editor:
            await editor.delTagProp(tag, name)

    async def delete(self, force=False):
        '''
        Delete a node from the cortex.

        The following tear-down operations occur in order:

            * validate that you have permissions to delete the node
            * validate that you have permissions to delete all tags
            * validate that there are no remaining references to the node.

            * delete all the tags (bottom up)
                * fire onDelTag() handlers
                * delete tag properties from storage

            * delete all secondary properties
                * fire onDelProp handler
                * delete secondary property from storage

            * delete the primary property
                * fire onDel handlers for the node
                * delete primary property from storage

        '''
        formname, formvalu = self.ndef

        # check for any nodes which reference us...
        if not force:

            # refuse to delete tag nodes with existing tags
            if self.form.name == 'syn:tag':

                async for _ in self.view.nodesByTag(self.ndef[1]):  # NOQA
                    mesg = 'Nodes still have this tag.'
                    raise s_exc.CantDelNode(mesg=mesg, form=formname, ndef=self.ndef)

            # formvalu is already normalized (it is our stored primary value), so
            # search referencing props by the normed value without re-norming.
            async for refr in self.view.nodesByPropTypeNorm(self.form.formtypes[0], formvalu, virts=self.valuvirts()):

                if refr.nid == self.nid:
                    continue

                mesg = 'Other nodes still refer to this node.'
                raise s_exc.CantDelNode(mesg=mesg, form=self.form.name, ndef=self.ndef)

            async for edge in self.iterEdgesN2():

                if self.nid == edge[1]:
                    continue

                mesg = 'Other nodes still have light edges to this node.'
                raise s_exc.CantDelNode(mesg=mesg, form=formname, ndef=self.ndef)

        async with self.view.getNodeEditor(self) as protonode:
            await protonode.delete()

        self.view.clearCachedNode(self.nid)

    async def hasData(self, name):
        return await self.view.hasNodeData(self.nid, name, stop=self.lastlayr())

    async def getData(self, name, defv=None):
        return await self.view.getNodeData(self.nid, name, defv=defv, stop=self.lastlayr())

    async def setData(self, name, valu):
        async with self.view.getNodeEditor(self) as protonode:
            await protonode.setData(name, valu)

    async def popData(self, name):
        async with self.view.getNodeEditor(self) as protonode:
            return await protonode.popData(name)

    async def iterData(self):
        async for item in self.view.iterNodeData(self.nid, stop=self.lastlayr()):
            yield item

    async def iterDataKeys(self):
        async for name in self.view.iterNodeDataKeys(self.nid, stop=self.lastlayr()):
            yield name

class RuntNode(NodeBase):
    '''
    Runtime node instances are a separate class to minimize isrunt checking in
    real node code.
    '''
    __slots__ = ('view', 'ndef', 'pode', 'form', 'nid')

    def __init__(self, view, pode, nid=None):
        self.view = view
        self.ndef = pode[0]
        self.pode = pode
        self.form = view.core.model.form(self.ndef[0])

        self.nid = nid

    def get(self, name, defv=None, virts=None):
        return self.pode[1]['props'].get(name, defv)

    def getWithVirts(self, name, defv=None, virts=None):
        return self.pode[1]['props'].get(name, defv), None

    def has(self, name, virts=None):
        return self.pode[1]['props'].get(name) is not None

    def _getStorProps(self):
        '''
        Return the storage property tuples from the runt node.

        A runt node has no sodes, so it carries neither a stortype nor any
        virtual property values.
        '''
        return {name: (valu, None, None) for (name, valu) in self.pode[1]['props'].items()}

    def intnid(self):
        if self.nid is None:
            return None
        return s_common.int64un(self.nid)

    def pack(self, dorepr=False, virts=False):

        pode = s_msgpack.deepcopy(self.pode)

        pode[1]['props'] = self._packProps(self._getStorProps(), dorepr=dorepr, dovirts=virts)

        if dorepr:
            self._addPodeRepr(pode)

        return pode

    def valu(self, defv=None, getr=None):
        valu = self.ndef[1]
        if getr is None:
            return valu

        return getr((valu,))

    async def set(self, name, valu):
        prop = self._reqValidProp(name)
        norm = (await prop.type.norm(valu))[0]
        return await self.view.core.runRuntPropSet(self, prop, norm)

    async def pop(self, name):
        prop = self._reqValidProp(name)
        return await self.view.core.runRuntPropDel(self, prop)

    async def addTag(self, name, valu=None, norminfo=None):
        mesg = f'You can not add a tag to a runtime only node (form: {self.form.name})'
        raise s_exc.IsRuntForm(mesg=mesg)

    async def addEdge(self, verb, n2nid, n2form=None, extra=None):
        mesg = f'You can not add an edge to a runtime only node (form: {self.form.name})'
        exc = s_exc.IsRuntForm(mesg=mesg)
        if extra is not None:
            exc = extra(exc)

        raise exc

    async def delEdge(self, verb, n2nid, extra=None):
        mesg = f'You can not delete an edge from a runtime only node (form: {self.form.name})'
        exc = s_exc.IsRuntForm(mesg=mesg)
        if extra is not None:
            exc = extra(exc)

        raise exc

    async def delTag(self, name, valu=None):
        mesg = f'You can not remove a tag from a runtime only node (form: {self.form.name})'
        raise s_exc.IsRuntForm(mesg=mesg)

    async def delete(self, force=False):
        mesg = f'You can not delete a runtime only node (form: {self.form.name})'
        raise s_exc.IsRuntForm(mesg=mesg)

class Path:
    '''
    A path context tracked through the storm runtime.
    '''
    __slots__ = ('node', 'links', 'vars', 'frames', 'ctors', 'builtins',
                 'display', 'metadata', 'nodedata')

    def __init__(self, vars, node, links=None):

        self.node = node

        if links is not None:
            self.links = links
        else:
            self.links = []

        self.vars = vars
        self.frames = []
        self.ctors = {}

        # "builtins" which are *not* vars
        # ( this allows copying variable context )
        self.builtins = {
            'path': self,
            'node': self.node,
        }

        self.display = None
        self.metadata = {}
        self.nodedata = collections.defaultdict(dict)

    def getVar(self, name, defv=s_common.novalu):

        # check if the name is in our variables
        valu = self.vars.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        # check if it's in builtins
        valu = self.builtins.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        ctor = self.ctors.get(name)
        if ctor is not None:
            valu = ctor(self)
            self.vars[name] = valu
            return valu

        return s_common.novalu

    async def setVar(self, name, valu):
        self.vars[name] = valu

    async def popVar(self, name):
        return self.vars.pop(name, s_common.novalu)

    def meta(self, name, valu):
        '''
        Add node specific metadata to be returned with the node.
        '''
        self.metadata[name] = valu

    async def pack(self):
        return await s_stormtypes.toprim(dict(self.metadata))

    def setData(self, nid, name, valu):
        self.nodedata[nid][name] = valu

    def popData(self, nid, name, defv=None):
        if (nodedata := self.nodedata.get(nid, s_common.novalu)) is s_common.novalu:
            return defv

        return nodedata.pop(name, defv)

    def getData(self, nid, name=None, defv=None):
        if (nodedata := self.nodedata.get(nid, s_common.novalu)) is s_common.novalu:
            return defv

        if name is not None:
            return nodedata.get(name, defv)

        return nodedata

    def fork(self, node, link):

        links = list(self.links)
        if self.node is not None and link is not None:
            links.append((self.node.intnid(), link))

        return Path(self.vars.copy(), node, links=links)

    def clone(self):
        path = Path(copy.copy(self.vars), self.node, copy.copy(self.links))
        path.frames = [v.copy() for v in self.frames]
        return path

    def initframe(self, initvars=None):

        framevars = {}
        if initvars is not None:
            framevars.update(initvars)

        self.frames.append(self.vars)

        self.vars = framevars

    def finiframe(self):
        '''
        Pop a scope frame from the path, restoring runt if at the top
        Args:
            runt (Runtime): A storm runtime to restore if we're at the top
            merge (bool): Set to true to merge vars back up into the next frame
        '''
        if not self.frames:
            self.vars.clear()
            return

        self.vars = self.frames.pop()

def props(pode):
    '''
    Get the props from the node.

    Args:
        pode (tuple): A packed node.

    Returns:
        dict: A dictionary of (valu, info) property envelopes by name.
    '''
    return pode[1]['props'].copy()

def prop(pode, prop):
    '''
    Return the envelope of a given property on the node.

    Args:
        pode (tuple): A packed node.
        prop (str): Relative property name, without a leading colon.

    Returns:
        tuple: The (valu, info) property envelope, or None.
    '''
    return pode[1]['props'].get(prop)


def getPodeTval(form, prop, item, member=False):
    '''
    Return the typed value carried by a packed node property envelope.

    Args:
        form (synapse.datamodel.Form): The form being added.
        prop (synapse.datamodel.Prop): The property being set.
        item (tuple): A (valu, info) property envelope.
        member (bool): The envelope is an array member rather than a container.

    Returns:
        The typed value expected by Type.normFromTypedValu().
    '''
    if not isinstance(item, (tuple, list)) or len(item) != 2 or not isinstance(item[1], dict):
        mesg = f'Property {form.name}:{prop.name} is not a packed node property envelope.'
        raise s_exc.BadTypeValu(mesg=mesg, form=form.name, prop=prop.name, valu=item)

    valu, info = item

    if (typename := info.get('t')) is not None:
        return (typename, valu)

    # envelope nesting is bounded at one level, so an array member carries
    # its own type name and may not itself be a container.
    if member or not prop.type.isarray:
        mesg = f'Property {form.name}:{prop.name} envelope is missing a type name.'
        raise s_exc.BadTypeValu(mesg=mesg, form=form.name, prop=prop.name, valu=item)

    if not isinstance(valu, (tuple, list)):
        mesg = f'Property {form.name}:{prop.name} array container value is not a sequence.'
        raise s_exc.BadTypeValu(mesg=mesg, form=form.name, prop=prop.name, valu=item)

    # an array container carries no type of its own. Its members do.
    return tuple([getPodeTval(form, prop, elem, member=True) for elem in valu])

def tags(pode, leaf=False):
    '''
    Get all the tags for a given node.

    Args:
        pode (tuple): A packed node.
        leaf (bool): If True, only return leaf tags

    Returns:
        list: A list of tag strings.
    '''
    if not leaf:
        return list(pode[1]['tags'].keys())
    return _tagscommon(pode, True)

def tagsnice(pode):
    '''
    Get all the leaf tags and the tags that have values or tagprops.

    Args:
        pode (tuple): A packed node.

    Returns:
        list: A list of tag strings.
    '''
    ret = _tagscommon(pode, False)
    for tag in pode[1].get('tagprops', {}):
        if tag not in ret:
            ret.append(tag)
    return ret

def _tagscommon(pode, leafonly):
    '''
    Return either all the leaf tags or all the leaf tags and all the internal tags with values
    '''
    retn = []

    tags = pode[1].get('tags')
    if tags is None:
        return retn

    # brute force rather than build a tree.  faster in small sets.
    for tag, val in sorted((t for t in pode[1]['tags'].items()), reverse=True, key=lambda x: len(x[0])):
        look = tag + '.'
        val = tuple(val[0])
        if (leafonly or val == (None, None, None)) and any([r.startswith(look) for r in retn]):
            continue
        retn.append(tag)
    return retn

def tagged(pode, tag):
    '''
    Check if a packed node has a given tag.

    Args:
        pode (tuple): A packed node.
        tag (str): The tag to check.

    Examples:
        Check if a node is tagged with "woot" and dostuff if it is.

            if s_node.tagged(node,'woot'):
                dostuff()

    Notes:
        If the tag starts with `#`, this is removed prior to checking.

    Returns:
        bool: True if the tag is present. False otherwise.
    '''
    if tag.startswith('#'):
        tag = tag[1:]
    return pode[1]['tags'].get(tag) is not None

def ndef(pode):
    '''
    Return a node definition (<form>,<valu>) tuple from the node.

    Args:
        pode (tuple): A packed node.

    Returns:
        ((str,obj)):    The (<form>,<valu>) tuple for the node
    '''
    return pode[0]

def reprNdef(pode):
    '''
    Get the ndef of the pode with a human readable value.

    Args:
        pode (tuple): A packed node.

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

    Returns:
        (str, str): A tuple of form and the human readable value.

    '''
    ((form, valu), info) = pode
    formvalu = info.get('repr')
    if formvalu is None:
        formvalu = str(valu)
    return form, formvalu

def reprProp(pode, prop):
    '''
    Get the human readable value for a secondary property from the pode.

    Args:
        pode (tuple): A packed node.
        prop:

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

    Returns:
        str: The human readable property value.  If the property is not present, returns None.
    '''
    if (envl := pode[1]['props'].get(prop)) is None:
        return None

    valu, info = envl

    if (rval := info.get('r')) is not None:
        return rval

    return str(valu)

def reprTag(pode, tag):
    '''
    Get the human readable value for the tag timestamp from the pode.

    Args:
        pode (tuple): A packed node.
        tag (str): The tag to get the value for.

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

        If the tag does not have a timestamp, this returns a empty string.

    Returns:
        str: The human readable value for the tag. If the tag is not present, returns None.
    '''
    tag = tag.lstrip('#')
    envl = pode[1]['tags'].get(tag)
    if envl is None:
        return None

    valu, info = envl

    valu = tuple(valu)
    if valu == (None, None, None):
        return ''

    if (rval := info.get('r')) is not None:
        return rval

    mint = s_time.repr(valu[0])
    maxt = s_time.reprmax(valu[1])
    return f'{mint} - {maxt}'

def reprTagProps(pode, tag):
    '''
    Get the human readable values for any tagprops on a tag for a given node.

    Args:
        pode (tuple): A packed node.
        tag (str): The tag to get the tagprops reprs for.

    Notes:
        The human readable value is only available if the node came from a
        storm query execution where the ``repr`` key was passed into the
        ``opts`` argument with a True value.

        If the tag does not have any tagprops associated with it, this returns an empty list.

    Returns:
        list: A list of tuples, containing the name of the tagprop and the repr value.
    '''
    ret = []
    exists = pode[1]['tags'].get(tag)
    if exists is None:
        return ret
    tagprops = pode[1].get('tagprops', {}).get(tag)
    if tagprops is None:
        return ret
    for prop, (valu, info) in tagprops.items():

        if (rval := info.get('r')) is None:
            rval = str(valu)

        ret.append((prop, rval))

    return sorted(ret, key=lambda x: x[0])
