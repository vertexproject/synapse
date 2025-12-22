import copy
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

storvirts = {
    s_layer.STOR_TYPE_NDEF: {
        'form': lambda x: x[0]
    },
    s_layer.STOR_TYPE_IVAL: {
        'min': lambda x: x[0],
        'max': lambda x: x[1],
        'duration': lambda x: x[2],
    },
}

class NodeBase:

    def repr(self, name=None, defv=None):

        virts = None
        if name is not None:
            parts = name.strip().split('.')
            if len(parts) > 1:
                name = parts[0] or None
                virts = parts[1:]

        if name is None:
            typeitem = self.form.type
            if virts is None:
                return typeitem.repr(self.valu())

            if (mtyp := self.view.core.model.metatypes.get(virts[0])) is not None:
                return mtyp.repr(self.getMeta(virts[0]))

            virtgetr = typeitem.getVirtGetr(virts)
            virttype = typeitem.getVirtType(virts)
            return virttype.repr(self.valu(virts=virtgetr))

        prop = self.form.props.get(name)
        if prop is None:
            mesg = f'No property named {name}.'
            raise s_exc.NoSuchProp(mesg=mesg, form=self.form.name, prop=name)

        typeitem = prop.type

        if virts is None:
            if (valu := self.get(name)) is None:
                return defv
            return typeitem.repr(valu)

        virtgetr = typeitem.getVirtGetr(virts)
        virttype = typeitem.getVirtType(virts)

        if (valu := self.get(name, virts=virtgetr)) is None:
            return defv
        return virttype.repr(valu)

    def reprs(self):
        '''
        Return a dictionary of repr values for props whose repr is different than
        the system mode value.
        '''
        reps = {}
        props = self.getProps()
        return self._getPropReprs(props)

    def protocols(self, name=None):

        retn = []

        pdefs = self.form.info.get('protocols')
        if pdefs is not None:
            for pname, pdef in pdefs.items():

                # TODO we could eventually optimize this...
                if name is not None and name != pname:
                    continue

                retn.append(self._pdefToProto(pname, pdef, None))

        for prop in self.form.props.values():

            pdefs = prop.info.get('protocols')
            if pdefs is None:
                continue

            for pname, pdef in pdefs.items():

                if name is not None and name != pname:
                    continue

                retn.append(self._pdefToProto(pname, pdef, prop.name))

        return retn

    def protocol(self, name, propname=None):
        pdef = self.form.reqProtoDef(name, propname=propname)
        return self._pdefToProto(name, pdef, propname)

    def _pdefToProto(self, name, pdef, propname):

        proto = {
            'name': name,
            'vars': {},
        }

        if propname is not None:
            proto['prop'] = propname

        for varn, vdef in pdef['vars'].items():

            if vdef.get('type') != 'prop': # pragma: no cover
                mesg = f'Invalid protocol var type: {pdef.get("type")}.'
                raise s_exc.BadFormDef(mesg=mesg)

            varprop = vdef.get('name')
            if varprop is None: # pragma: no cover
                mesg = 'Protocol variable type "prop" requires a "name" key.'
                raise s_exc.BadFormDef(mesg=mesg)

            proto['vars'][varn] = self.get(varprop)

        return proto

    def _reqValidProp(self, name):
        prop = self.form.prop(name)
        if prop is None:
            mesg = f'No property named {name} on form {self.form.name}.'
            raise s_exc.NoSuchProp(mesg=mesg)
        return prop

    def _getPropReprs(self, props):

        reps = {}
        for name, valu in props.items():

            prop = self.form.prop(name)
            if prop is None:
                continue

            rval = prop.type.repr(valu)
            if rval is None or rval == valu:
                continue

            reps[name] = rval

        return reps

    def _addPodeRepr(self, pode):

        rval = self.repr()
        if rval is not None and rval != self.ndef[1]:
            pode[1]['repr'] = rval

        props = pode[1].get('props')
        if props:
            pode[1]['reprs'] = self._getPropReprs(props)

        tagprops = pode[1].get('tagprops')
        if tagprops:
            pode[1]['tagpropreprs'] = self._getTagPropReprs(tagprops)

    def _getTagPropReprs(self, tagprops):

        reps = collections.defaultdict(dict)

        for tag, propdict in tagprops.items():

            for name, valu in propdict.items():

                prop = self.form.modl.tagprop(name)
                if prop is None:
                    continue

                rval = prop.type.repr(valu)
                if rval is None or rval == valu:
                    continue
                reps[tag][name] = rval

        return dict(reps)

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

    def hasPropAltsValu(self, prop, valu):
        # valu must be normalized in advance
        proptype = prop.type
        for prop in prop.getAlts():
            if prop.type.isarray and prop.type.arraytype == proptype:
                arryvalu = self.get(prop.name)
                if arryvalu is not None and valu in arryvalu:
                    return True
            else:
                if self.get(prop.name) == valu:
                    return True

        return False

class Node(NodeBase):
    '''
    A Cortex hypergraph node.

    NOTE: This object is for local Cortex use during a single Xact.
    '''
    def __init__(self, view, nid, ndef, soderefs):
        self.view = view

        self.nid = nid
        self.ndef = ndef

        # TODO should we get this from somewhere?
        self.buid = s_common.buid(ndef)

        # must hang on to these to keep the weakrefs alive
        self.soderefs = soderefs

        self.sodes = [sref.sode for sref in soderefs]

        self.form = view.core.model.form(self.ndef[0])

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

    def iden(self):
        return s_common.ehex(self.buid)

    def intnid(self):
        return s_common.int64un(self.nid)

    def pack(self, dorepr=False, virts=False, verbs=True):
        '''
        Return the serializable/packed version of the node.

        Args:
            dorepr (bool): Include repr information for human readable versions of properties.
            virts (bool): Include virtual properties.
            verbs (bool): Include edge verb counts.

        Returns:
            (tuple): An (ndef, info) node tuple.
        '''

        pode = (self.ndef, {
            'nid': s_common.int64un(self.nid),
            'iden': self.iden(),
            'meta': self.getMetaDict(),
            'tags': self._getTagsDict(),
            'props': self.getProps(virts=virts),
            'tagprops': self._getTagPropsDict(),
        })

        if verbs:
            pode[1]['n1verbs'] = self.getEdgeCounts()
            pode[1]['n2verbs'] = self.getEdgeCounts(n2=True)

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
        async def walk(n, p):

            valu = n.get(p)
            if valu is None:
                return None

            prop = n.form.prop(p)
            if prop is None:
                return None

            if prop.modl.form(prop.type.name) is not None:
                buid = s_common.buid((prop.type.name, valu))
            elif 'ndef' in prop.type.types:
                buid = s_common.buid(valu)
            else:
                return None

            step = cache.get(buid, s_common.novalu)
            if step is s_common.novalu:
                step = cache[buid] = await node.view.getNodeByBuid(buid)

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

            for relp in relprops:
                valu, virts = node.getWithVirts(relp)
                embdnode[relp] = valu

                if valu is None:
                    continue

                if virts is not None:
                    for vname, vval in virts.items():
                        embdnode[f'{relp}.{vname}'] = vval[0]

                stortype = node.form.prop(relp).type.stortype
                if stortype & s_layer.STOR_FLAG_ARRAY:
                    embdnode[f'{relp}.size'] = len(valu)
                    if (svirts := storvirts.get(stortype & 0x7fff)) is not None:
                        for vname, getr in svirts.items():
                            embdnode[f'{relp}.{vname}'] = [getr(v) for v in valu]
                else:
                    if (svirts := storvirts.get(stortype)) is not None:
                        for vname, getr in svirts.items():
                            embdnode[f'{relp}.{vname}'] = getr(valu)

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
        if self.view.readonly:
            mesg = 'Cannot set property in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        async with self.view.getNodeEditor(self) as editor:
            return await editor.set(name, valu, norminfo=norminfo)

    def has(self, name, virts=None):

        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return False

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return False

            props = sode.get('props')
            if props is None:
                continue

            if (valt := props.get(name)) is not None:
                if virts:
                    for virt in virts:
                        if (valt := virt(valt)) is None:
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

    def valu(self, defv=None, virts=None):
        if virts is None:
            return self.ndef[1]

        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defv

            if (valu := sode.get('valu')) is not None:
                for virt in virts:
                    valu = virt(valu)
                return valu

        return defv

    def valuvirts(self, defv=None):
        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defv

            if (valu := sode.get('valu')) is not None:
                return valu[-1]

        return defv

    def get(self, name, defv=None, virts=None):
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
            vnames = parts[1:]

            if not name:
                if (mtyp := self.view.core.model.metatypes.get(vnames[0])) is not None:
                    return self.getMeta(vnames[0])

                virtgetr = self.form.type.getVirtGetr(vnames)
                return self.valu(virts=virtgetr)
            else:
                if (prop := self.form.props.get(name)) is None:
                    raise s_exc.NoSuchProp.init(name)

                virts = prop.type.getVirtGetr(vnames)

        for sode in self.sodes:
            if sode.get('antivalu') is not None:
                return defv

            if (proptomb := sode.get('antiprops')) is not None and proptomb.get(name):
                return defv

            if (item := sode.get('props')) is None:
                continue

            if (valt := item.get(name)) is not None:
                if virts:
                    for virt in virts:
                        valt = virt(valt)
                    return valt
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

    def getWithLayer(self, name, defv=None, virts=None):
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
                if virts:
                    for virt in virts:
                        valt = virt(valt)
                    return valt, indx
                return valt[0], indx

        return defv, None

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

    def getProps(self, virts=False):
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

            for name, valt in props.items():
                if virts:
                    retn[name] = valt
                else:
                    retn[name] = valt[0]

        if virts:
            for name, valt in list(retn.items()):
                retn[name] = valu = valt[0]

                if (vprops := valt[2]) is not None:
                    for vname, vval in vprops.items():
                        retn[f'{name}.{vname}'] = vval[0]

                stortype = valt[1]
                if stortype & s_layer.STOR_FLAG_ARRAY:
                    retn[f'{name}.size'] = len(valu)
                    if (svirts := storvirts.get(stortype & 0x7fff)) is not None:
                        for vname, getr in svirts.items():
                            retn[f'{name}.{vname}'] = [getr(v) for v in valu]
                else:
                    if (svirts := storvirts.get(stortype)) is not None:
                        for vname, getr in svirts.items():
                            retn[f'{name}.{vname}'] = getr(valu)

        return retn

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

    def _getTagPropsDict(self):

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
                    retn[tagname][propname] = valt[0]

        return dict(retn)

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

    def getTagProp(self, tag, prop, defval=None, virts=None):
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
                if virts:
                    for virt in virts:
                        valt = virt(valt)
                    return valt
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
                    raise s_exc.CantDelNode(mesg=mesg, form=formname, iden=self.iden())

            for formtype in self.form.formtypes:
                async for refr in self.view.nodesByPropTypeValu(formtype, formvalu):

                    if refr.nid == self.nid:
                        continue

                    mesg = 'Other nodes still refer to this node.'
                    raise s_exc.CantDelNode(mesg=mesg, form=self.form.name, iden=self.iden())

            async for edge in self.iterEdgesN2():

                if self.nid == edge[1]:
                    continue

                mesg = 'Other nodes still have light edges to this node.'
                raise s_exc.CantDelNode(mesg=mesg, form=formname, iden=self.iden())

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
        async for item in self.view.iterNodeData(self.nid):
            yield item

    async def iterDataKeys(self):
        async for name in self.view.iterNodeDataKeys(self.nid):
            yield name

class RuntNode(NodeBase):
    '''
    Runtime node instances are a separate class to minimize isrunt checking in
    real node code.
    '''
    def __init__(self, view, pode, nid=None):
        self.view = view
        self.ndef = pode[0]
        self.pode = pode
        self.buid = s_common.buid(self.ndef)
        self.form = view.core.model.form(self.ndef[0])

        self.nid = nid

    def get(self, name, defv=None, virts=None):
        return self.pode[1]['props'].get(name, defv)

    def has(self, name, virts=None):
        return self.pode[1]['props'].get(name) is not None

    def iden(self):
        return s_common.ehex(s_common.buid(self.ndef))

    def intnid(self):
        if self.nid is None:
            return None
        return s_common.int64un(self.nid)

    def pack(self, dorepr=False, virts=False, verbs=True):
        pode = s_msgpack.deepcopy(self.pode)
        if dorepr:
            self._addPodeRepr(pode)
        return pode

    def valu(self, defv=None, virts=None):
        valu = self.ndef[1]
        if virts is None:
            return valu

        for virt in virts:
            valu = virt((valu,))
        return valu

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
    def __init__(self, vars, nodes, links=None):

        self.node = None
        self.nodes = nodes

        if links is not None:
            self.links = links
        else:
            self.links = []

        if len(nodes):
            self.node = nodes[-1]

        self.vars = vars
        self.frames = []
        self.ctors = {}

        # "builtins" which are *not* vars
        # ( this allows copying variable context )
        self.builtins = {
            'path': self,
            'node': self.node,
        }

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

    async def pack(self, path=False):
        info = await s_stormtypes.toprim(dict(self.metadata))
        if path:
            info['nodes'] = [node.iden() for node in self.nodes]

        return info

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

        nodes = list(self.nodes)
        nodes.append(node)

        path = Path(self.vars.copy(), nodes, links=links)

        return path

    def clone(self):
        path = Path(copy.copy(self.vars), copy.copy(self.nodes), copy.copy(self.links))
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
        dict: A dictionary of properties.
    '''
    return pode[1]['props'].copy()

def prop(pode, prop):
    '''
    Return the valu of a given property on the node.

    Args:
        pode (tuple): A packed node.
        prop (str): Property to retrieve.

    Notes:
        The prop argument may be the full property name (foo:bar:baz), relative property name (:baz) , or the unadorned
        property name (baz).

    Returns:

    '''
    form = pode[0][0]
    if prop.startswith(form):
        prop = prop[len(form):]
    if prop[0] == ':':
        prop = prop[1:]
    return pode[1]['props'].get(prop)

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
        val = tuple(val)
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

def iden(pode):
    '''
    Return the iden (buid) of the packed node.

    Args:
        pode (tuple): A packed node.

    Returns:
        str: The node iden.
    '''
    return pode[1].get('iden')

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

        The prop argument may be the full property name (foo:bar:baz), relative
        property name (:baz) , or the unadorned property name (baz).

    Returns:
        str: The human readable property value.  If the property is not present, returns None.
    '''
    form = pode[0][0]
    if prop.startswith(form):
        prop = prop[len(form):]
    if prop[0] == ':':
        prop = prop[1:]
    opropvalu = pode[1].get('props').get(prop)
    if opropvalu is None:
        return None
    propvalu = pode[1].get('reprs', {}).get(prop)
    if propvalu is None:
        return str(opropvalu)
    return propvalu

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
    valu = pode[1]['tags'].get(tag)
    if valu is None:
        return None
    valu = tuple(valu)
    if valu == (None, None, None):
        return ''
    mint = s_time.repr(valu[0])
    maxt = s_time.repr(valu[1])
    valu = f'({mint}, {maxt})'
    return valu

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
    for prop, valu in tagprops.items():
        rval = pode[1].get('tagpropreprs', {}).get(tag, {}).get(prop)
        if rval is not None:
            ret.append((prop, rval))
        else:
            ret.append((prop, str(valu)))
    return sorted(ret, key=lambda x: x[0])
