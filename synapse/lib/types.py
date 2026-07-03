import sys
import asyncio
import decimal
import logging
import binascii
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.json as s_json
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.grammar as s_grammar
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

import synapse.lib.scope as s_scope

logger = logging.getLogger(__name__)

pricecurre = regex.compile(r'^(?P<numer>.*?)\s*(?P<curr>[A-Za-z]+)$')

def splitPriceCurrency(text):
    '''
    Split a price string into (numeric_str, currency_or_None) by peeling a
    trailing run of ASCII letters (with optional preceding whitespace).

    A value with no trailing alpha run returns (text, None). Scientific
    notation such as "1e-24" or "1E5" ends in a digit and is left intact.
    '''
    match = pricecurre.match(text)
    if match is None:
        return text, None

    return match.group('numer'), match.group('curr')

def computeTypeHash(ctor, opts):
    '''
    Compute a stable typehash from a type constructor path and opts dict.

    This is the same formula used by Type.__init__ and Type._initType to set
    self.typehash.  Factored out so that datamodel code can compute the hash
    *before* instantiating a Type (e.g. to derive a deterministic name for an
    auto-registered prop type without instantiating it twice).

    Args:
        ctor (str): Fully-qualified Python class path, e.g.
            ``'synapse.lib.types.Array'``.
        opts (dict): The fully-merged type opts dict (base opts updated with
            inline prop opts, exactly as Type.extend produces them).

    Returns:
        str: An interned 32-char lowercase hex GUID.
    '''
    normopts = dict(opts)
    for optn, valu in normopts.items():
        if isinstance(valu, float):
            normopts[optn] = str(valu)

    return sys.intern(s_common.guid((ctor, s_common.flatten(normopts))))

class Type:

    _opt_defs = ()
    stortype: int = None  # type: ignore

    # a fast-access way to determine if the type is an array
    # ( due to hot-loop needs in the storm runtime )
    ispoly = False
    isarray = False
    ismutable = False

    def __init__(self, modl, name, info, opts, skipinit=False):
        '''
        Construct a new Type object.

        Args:
            modl (synpase.datamodel.DataModel): The data model instance.
            name (str): The name of the type.
            info (dict): The type info (docs etc).
            opts (dict): Options that are specific to the type.
        '''
        # these fields may be referenced by callers
        self.modl = modl
        self.name = name
        self.info = info
        self.form = None  # this will reference a Form() if the type is a form
        self.subof = None  # This references the name that a type was extended from.

        self.info.setdefault('bases', ('base',))
        self.types = (self.name,) + self.info['bases'][::-1]

        self.opts = dict(self._opt_defs)

        for optn in opts.keys():
            if optn not in self.opts:
                mesg = f'Type option {optn} is not valid for type {self.name}.'
                raise s_exc.BadTypeDef(mesg=mesg)

        self.opts.update(opts)

        self._type_norms = {}   # python type to norm function map str: _norm_str
        self._cmpr_ctors = {}   # cmpr string to filter function constructor map
        self._cmpr_ctor_lift = {}  # if set, create a cmpr which is passed along with indx ops
        self._expr_funcs = {}   # (oper, othertypename) to arithmetic handler map
        self._rexpr_funcs = {}  # (oper, othertypename) to reversed-operand arithmetic handler map

        self.virts = {}
        self.virtindx = {
            'created': 'created',
            'updated': 'updated'
        }
        self.virtstor = {}
        self.virtlifts = {}

        self.pivs = {}

        self.setCmprCtor('=', self._ctorCmprEq)
        self.setCmprCtor('!=', self._ctorCmprNe)
        self.setCmprCtor('~=', self._ctorCmprRe)
        self.setCmprCtor('^=', self._ctorCmprPref)
        self.setCmprCtor('in=', self._ctorCmprIn)
        self.setCmprCtor('range=', self._ctorCmprRange)

        self.setNormFunc(s_node.Node, self._normStormNode)
        self.setNormFunc(s_node.RuntNode, self._normStormNode)
        self.setNormFunc(s_stormtypes.Valu, self._normStormValu)
        self.setNormFunc(s_stormtypes.NodeRef, self._normStormNodeRef)
        self.setNormFunc(s_stormtypes.Query, self._normStormQuery)

        self.storlifts = {
            '=': self._storLiftNorm,
            '~=': self._storLiftRegx,
            '?=': self._storLiftSafe,
            'in=': self._storLiftIn,
            'range=': self._storLiftRange,
        }

        self.locked = False
        self.deprecated = bool(self.info.get('deprecated', False))

        if not skipinit:
            self.postTypeInit()

            ctor = '.'.join([self.__class__.__module__, self.__class__.__qualname__])
            self.typehash = computeTypeHash(ctor, self.opts)

    def _initType(self):
        inits = [self.postTypeInit]

        subof = self.subof
        while subof is not None:
            styp = self.modl.type(subof)
            inits.append(styp.postTypeInit)
            subof = styp.subof

        for init in inits[::-1]:
            init()

        ctor = '.'.join([self.__class__.__module__, self.__class__.__qualname__])
        self.typehash = computeTypeHash(ctor, self.opts)

    def __hash__(self):
        return hash(self.typehash)

    async def _storLiftSafe(self, cmpr, valu):
        try:
            return await self.storlifts['=']('=', valu)
        except Exception:
            return ()

    async def _storLiftIn(self, cmpr, valu):
        retn = []
        for realvalu in valu:
            retn.extend(await self.getStorCmprs('=', realvalu))
        return retn

    async def _storLiftNorm(self, cmpr, valu):
        # NOTE: this may also be used for any other supported
        #       lift operation that requires a simple norm(valu)
        norm, info = await self.norm(valu)
        return ((cmpr, norm, self.stortype),)

    async def _storLiftRange(self, cmpr, valu):
        minv, minfo = await self.norm(valu[0])
        maxv, maxfo = await self.norm(valu[1])
        return ((cmpr, (minv, maxv), self.stortype),)

    async def _storLiftRegx(self, cmpr, valu):
        return ((cmpr, valu, self.stortype),)

    def getStorType(self, valu):
        return self.stortype

    async def getStorCmprs(self, cmpr, valu, virt=None):

        lifts = self.storlifts

        if virt is not None:
            if (lifts := self.virtlifts.get(virt)) is None:
                return await self.getVirtType(virt).getStorCmprs(cmpr, valu)

        func = lifts.get(cmpr)
        if func is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        return await func(cmpr, valu)

    def getVirtIndx(self, virt):
        indx = self.virtindx.get(virt, s_common.novalu)
        if indx is s_common.novalu:
            raise s_exc.NoSuchVirt.init(virt, self)

        return indx

    def getVirtType(self, virt):
        if (info := self.virts.get(virt)) is None:
            raise s_exc.NoSuchVirt.init(virt, self)

        return info[0]

    def setVirtInfo(self, info, name, valu, vtype, norminfo=None):
        '''
        Record a virtual property value in the given norm info dict.

        When the virtual property type is also a (non-runt) form, an add is
        automatically recorded so that the referenced node is created. The
        provided norminfo is carried through to the add to avoid re-normalizing
        the value.
        '''
        if (virts := info.get('virts')) is None:
            virts = info['virts'] = {}

        virts[name] = (valu, vtype.stortype)

        if (form := self.modl.form(vtype.name)) is None or form.isrunt:
            return

        if (adds := info.get('adds')) is None:
            adds = info['adds'] = []

        adds.append((form.name, valu, norminfo))

    def getVirtGetr(self, virt):
        if (info := self.virts.get(virt)) is None:
            raise s_exc.NoSuchVirt.init(virt, self)

        return info[1]

    def getVirtInfo(self, virt):
        if (info := self.virts.get(virt)) is None:
            raise s_exc.NoSuchVirt.init(virt, self)

        return info[0], info[1]

    async def normVirt(self, name, valu, newvirt, oldvirts=None):
        func = self.virtstor.get(name, s_common.novalu)
        if func is s_common.novalu:
            mesg = f'No editable virtual prop named {name} on type {self.name}.'
            raise s_exc.NoSuchVirt.init(name, self, mesg=mesg)

        return await func(valu, newvirt, oldvirts=oldvirts)

    def getRuntPode(self):

        ctor = '.'.join([self.__class__.__module__, self.__class__.__qualname__])
        props = {
            'doc': self.info.get('doc'),
            'ctor': ctor,
        }

        opts = {k: v for k, v in self.opts.items()}
        if opts:
            props['opts'] = opts

        if self.subof is not None:
            props['parent'] = self.subof

        props = self.modl.form('syn:type').wrapRuntProps(props)

        return (('syn:type', self.name), {
            'props': props,
        })

    async def _normStormNode(self, node, view=None):
        norm, norminfo = await self.norm(node.ndef[1], view=view)
        if self.name in node.form.formtypes:
            norminfo['skipadd'] = True
            norminfo.pop('adds', None)
        return norm, norminfo

    async def _normStormValu(self, valu, view=None):
        # a Valu carries a non-form typed value; reuse the normed value when it
        # was produced by an equivalent type.
        tobj = self.modl.type(valu.valu[0])
        if tobj is not None and tobj.typehash == self.typehash:
            info = {}
            if valu.virts is not None:
                info['virts'] = valu.virts
            return valu.valu[1], info
        return await self.norm(valu.valu[1], view=view)

    async def _normStormNodeRef(self, ndef, view=None):
        # a NodeRef carries a form value; if produced by an equivalent type and the target is
        # that form, skip the node creation work when the ref already exists.

        tobj = self.modl.type(ndef.valu[0])
        if tobj is not None and tobj.typehash == self.typehash and self.modl.form(self.name) is not None:

            if ndef.exists:
                return ndef.valu[1], {'skipadd': True, 'virts': ndef.virts}

            if view is not None and await view.getNodeByNdef(ndef.valu) is not None:
                ndef.exists = True
                return ndef.valu[1], {'skipadd': True, 'virts': ndef.virts}

        return await self.norm(ndef.valu[1], view=view)

    async def _normStormQuery(self, valu, prec=None, view=None):
        '''
        Execute an embed query used as a value and normalize the yielded node(s).

        A non-array type accepts exactly one yielded node (or a return statement
        value), while an array type accepts up to 128 nodes.
        '''
        limit = 128 if self.isarray else 1

        nodes = []
        try:
            async for node in valu.nodes():
                nodes.append(node)

                if len(nodes) > limit:
                    mesg = f'Embed query used as a value yielded too many (>{limit}) nodes. {s_common.trimText(valu.text)}'
                    raise s_exc.BadTypeValu(name=self.name, mesg=mesg, text=valu.text)

        except s_stormctrl.StormReturn as e:
            # an embed query with a return statement; just use the returned value
            return await self.norm(e.item, view=view)

        if self.isarray:
            return await self.norm(nodes, view=view)

        return await self.norm(nodes[0] if nodes else None, view=view)

    def pack(self):
        info = {
            'info': dict(self.info),
            'opts': dict(self.opts),
            'stortype': self.stortype,
            'lift_cmprs': list(self.storlifts.keys()),
            'filter_cmprs': list(self._cmpr_ctors.keys()),
        }

        if self.virts:
            info['virts'] = {name: valu[0].name for (name, valu) in self.virts.items()}

        return info

    def getTypeDef(self):
        basename = self.info['bases'][-1]
        info = self.info.copy()
        info['stortype'] = self.stortype
        return (self.name, (basename, self.opts), info)

    async def getTypeVals(self, valu):
        yield valu

    def setCmprCtor(self, name, func):
        '''
        Set a comparator ctor for a given named comparison operation.

        Args:
            name (str): Name of the comparison operation.
            func: Function which returns a comparator.

        Notes:
            Comparator ctors should expect to get the right-hand-side of the
            comparison as their argument, and the returned function should
            expect to get the left hand side of the comparison and return a
            boolean from there.
        '''
        self._cmpr_ctors[name] = func

    def getCmprCtor(self, name):
        return self._cmpr_ctors.get(name)

    def setExprFunc(self, oper, othername, func, reverse=False):
        '''
        Register a handler for the arithmetic operator oper when the other
        operand is of type othername.

        Args:
            reverse (bool): If True, register a reversed-operand handler used
                when this type is the right-hand operand and the left-hand
                operand of type othername has no forward handler for this type.
                This is the analog of Python's __rsub__ family.

        Notes:
            The handler receives this type's normalized value and the other
            operand's normalized value, and returns a (typename, value) tuple
            for the typed result. For a reverse handler the result is that of
            othername oper thistype.
        '''
        funcs = self._rexpr_funcs if reverse else self._expr_funcs
        funcs[(oper, othername)] = func

    def getExprFunc(self, oper, othername, reverse=False):
        funcs = self._rexpr_funcs if reverse else self._expr_funcs
        return funcs.get((oper, othername))

    def setLiftHintCmprCtor(self, name, func):
        self._cmpr_ctor_lift[name] = func

    def getLiftHintCmprCtor(self, name):
        return self._cmpr_ctor_lift.get(name)

    def getLiftHintCmpr(self, valu, cmpr):
        ctor = self.getLiftHintCmprCtor(cmpr)
        if ctor:
            return ctor(valu)
        return None

    async def cmpr(self, val1, name, val2):
        '''
        Compare the two values using the given type specific comparator.
        '''
        ctor = self.getCmprCtor(name)
        if ctor is None:
            raise s_exc.NoSuchCmpr(cmpr=name, name=self.name)

        norm1 = (await self.norm(val1))[0]

        if name != '~=':
            # Don't norm regex patterns
            val2 = (await self.norm(val2))[0]

        cmpr = await ctor(val2)
        return await cmpr(norm1)

    async def _ctorCmprEq(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return norm == valu
        return cmpr

    async def _ctorCmprNe(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return norm != valu
        return cmpr

    async def _ctorCmprPref(self, valu):
        text = str(valu)

        async def cmpr(valu):
            vtxt = self.repr(valu)
            return vtxt.startswith(text)

        return cmpr

    async def _ctorCmprRe(self, text):
        regx = regex.compile(text, flags=regex.I)

        async def cmpr(valu):
            vtxt = self.repr(valu)
            return regx.search(vtxt) is not None

        return cmpr

    async def _ctorCmprIn(self, vals):
        norms = [(await self.norm(v))[0] for v in vals]

        async def cmpr(valu):
            return valu in norms
        return cmpr

    async def _ctorCmprRange(self, vals):

        if not isinstance(vals, (list, tuple)):
            mesg = f'Range comparison requires a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadTypeValu(name=self.name, valu=vals, mesg=mesg)

        if len(vals) != 2:
            mesg = f'Range comparison requires a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadTypeValu(name=self.name, valu=vals, mesg=mesg)

        minv = (await self.norm(vals[0]))[0]
        maxv = (await self.norm(vals[1]))[0]

        async def cmpr(valu):
            return minv <= valu <= maxv
        return cmpr

    def setNormFunc(self, typo, func):
        '''
        Register a normalizer function for a given python type.

        Args:
            typo (type): A python type/class to normalize.
            func (function): A callback which normalizes a python value.
        '''
        self._type_norms[typo] = func

    def postTypeInit(self):
        pass

    async def norm(self, valu, view=None):
        '''
        Normalize the value for a given type.

        Args:
            valu (obj): The value to normalize.
            view (obj): An optional View object to use when normalizing, or False if no View should be used.

        Returns:
            ((obj,dict)): The normalized valu, info tuple.

        Notes:
            The info dictionary uses the following key conventions:
                subs (dict): The normalized sub-fields as name: valu entries.
        '''
        func = self._type_norms.get(type(valu))
        if func is None:
            raise s_exc.BadTypeValu(name=self.name, mesg='no norm for type: %r.' % (type(valu),))

        return await func(valu, view=view)

    def repr(self, norm):
        '''
        Return a printable representation for the value.
        This may return a string or a tuple of values for display purposes.
        '''
        return str(norm)

    def reprWithVirts(self, norm, virts=None):
        '''
        Return a printable representation for the value which may incorporate
        virtual property values. The default implementation ignores virts and
        returns the same value as repr().
        '''
        return self.repr(norm)

    def merge(self, oldv, newv):
        '''
        Allow types to "merge" data from two sources based on value precedence.

        Args:
            valu (object): The current value.
            newv (object): The updated value.

        Returns:
            (object): The merged value.
        '''
        return newv

    def extend(self, name, opts, info, skipinit=False):
        '''
        Extend this type to construct a sub-type.

        Args:
            name (str): The name of the new sub-type.
            opts (dict): The type options for the sub-type.
            info (dict): The type info for the sub-type.

        Returns:
            (synapse.types.Type): A new sub-type instance.
        '''
        tifo = self.info.copy()

        # handle virts by merging them...
        v0 = tifo.get('virts', ())
        v1 = info.get('virts', ())

        virts = self.modl.mergeVirts(v0, v1)
        if virts:
            info['virts'] = virts

        tifo.update(info)

        ifaces = {}
        for iname, ifinfo in self.info.get('interfaces', ()):
            ifaces[iname] = ifinfo

        for iname, newinfo in info.get('interfaces', ()):
            if (oldinfo := ifaces.get(iname)) is not None:
                temp = {}
                temp |= oldinfo.get('template', {})
                temp |= newinfo.get('template', {})

                ifaces[iname] = oldinfo | newinfo
                if temp:
                    ifaces[iname]['template'] = temp
            else:
                ifaces[iname] = newinfo

        if ifaces:
            tifo['interfaces'] = tuple(ifaces.items())

        bases = self.info.get('bases') + (self.name,)
        tifo['bases'] = bases

        topt = self.opts.copy()
        topt.update(opts)

        tobj = self.__class__(self.modl, name, tifo, topt, skipinit=skipinit)
        tobj.subof = self.name
        return tobj

    def clone(self, opts):
        '''
        Create a new instance of this type with the specified options.

        Args:
            opts (dict): The type specific options for the new instance.
        '''
        topt = self.opts.copy()
        topt.update(opts)
        return self.__class__(self.modl, self.name, self.info, topt)

    async def tostorm(self, valu, virts=None):
        '''
        Allows type-specific modifications to values to make them safe for use in the runtime.

        Args:
            valu (any): The normalized valu to wrap.
            virts (dict): Optional virtual property values to carry on the typed value.
        '''
        if self.ismutable:
            return s_msgpack.deepcopy(valu, use_list=True)
        if valu is None:
            return None
        if self.modl.form(self.name) is not None:
            return s_stormtypes.NodeRef(((self.name, valu), virts))
        return s_stormtypes.Valu(((self.name, valu), virts))

    def __eq__(self, othr):
        if self.name != othr.name:
            return False
        if self.opts != othr.opts:
            return False
        return True

class Bool(Type):

    stortype = s_layer.STOR_TYPE_U8

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bool, self._normPyInt)
        self.setNormFunc(decimal.Decimal, self._normPyInt)
        self.setNormFunc(s_stormtypes.Number, self._normNumber)

    async def _normPyStr(self, valu, view=None):

        ival = s_common.intify(valu)
        if ival is not None:
            return int(bool(ival)), {}

        sval = valu.lower().strip()
        if sval in ('true', 't', 'y', 'yes', 'on'):
            return 1, {}

        if sval in ('false', 'f', 'n', 'no', 'off'):
            return 0, {}

        raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                mesg='Failed to norm bool')

    async def _normPyInt(self, valu, view=None):
        return int(bool(valu)), {}

    async def _normNumber(self, valu, view=None):
        return int(bool(valu.valu)), {}

    def repr(self, valu, view=None):
        return repr(bool(valu)).lower()

class Array(Type):

    isarray = True
    ismutable = True

    _opt_defs = (
        ('type', None),       # type: ignore
        ('uniq', True),       # type: ignore
        ('split', None),      # type: ignore
        ('sorted', True),     # type: ignore
        ('typeopts', None),   # type: ignore
    )

    def postTypeInit(self):

        self.isuniq = self.opts.get('uniq')
        self.issorted = self.opts.get('sorted')
        self.splitstr = self.opts.get('split')

        typename = self.opts.get('type')
        if typename is None:
            mesg = 'Array type requires type= option.'
            raise s_exc.BadTypeDef(mesg=mesg)

        if (typeopts := self.opts.get('typeopts')) is None:
            typeopts = {}

        if isinstance(typename, tuple):
            polyinfo = self.modl.convertPolyinfo(typename)
        elif isinstance(tobj := self.modl.type(typename), Poly):
            polyinfo = tobj.opts
        else:
            if (basetype := self.modl.type(typename)) is not None:
                if isinstance(basetype, Array):
                    mesg = 'Array type of array values is not supported.'
                    raise s_exc.BadTypeDef(mesg)

                if basetype.deprecated:
                    mesg = f'The Array type {self.name} is based on a deprecated type {basetype.name} type which ' \
                           f'which will be removed in 4.0.0'
                    logger.warning(mesg)

            elif typename not in self.modl.ifaces:
                mesg = f'Array type ({self.name}) based on unknown type: {typename}.'
                raise s_exc.BadTypeDef(mesg=mesg)

            typedef = ((typename, typeopts),)
            polyinfo = self.modl.convertPolyinfo(typedef)

        self.arraytype = self.modl.type('poly').clone(polyinfo)
        self.arraytypehash = self.arraytype.typehash

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.stortype = s_layer.STOR_FLAG_ARRAY | self.arraytype.stortype

        self.inttype = self.modl.type('int')

        self.virts |= {
            'size': (self.inttype, self._getSize),
        }

        self.virtlifts |= {
            'size': {'range=': self._storLiftSizeRange}
        }

        for oper in ('=', '<', '>', '<=', '>='):
            self.virtlifts['size'][oper] = self._storLiftSize

    def _getSize(self, valu):
        return len(valu[0])

    async def _storLiftSize(self, cmpr, valu):
        norm, _ = await self.inttype.norm(valu)
        return (
            (cmpr, norm, s_layer.STOR_TYPE_ARRAY),
        )

    async def _storLiftSizeRange(self, cmpr, valu):
        minx = (await self.inttype.norm(valu[0]))[0]
        maxx = (await self.inttype.norm(valu[1]))[0]
        return (
            (cmpr, (minx, maxx), s_layer.STOR_TYPE_ARRAY),
        )

    async def normSkipAddExisting(self, valu, newinfos, view=None):
        return await self._normPyTuple(valu, view=view, newinfos=newinfos)

    async def _normPyStr(self, text, view=None):
        if self.splitstr is None:
            mesg = f'{self.name} type has no split-char defined.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)
        parts = [p.strip() for p in text.split(self.splitstr)]
        return await self._normPyTuple(parts, view=view)

    async def _normPyTuple(self, valu, view=None, newinfos=None):

        adds = []
        norms = []
        virts = collections.defaultdict(lambda: collections.defaultdict(int))

        form = self.modl.form(self.arraytype.name)

        for item in valu:
            if newinfos is not None:
                if (info := newinfos.get(item)) is not None:
                    norm = item
                else:
                    typename = item[0]
                    norm, info = await self.modl.type(typename).norm(item[1], view=view)
                    norm = (typename, norm)
                    info['skipadd'] = True
            else:
                norm, info = await self.arraytype.norm(item, view=view)

            norms.append(norm)

            if not info.get('skipadd'):
                adds.extend(info.get('adds', ()))
                if form is not None:
                    adds.append((form.name, norm, info))

            if (virt := info.get('virts')) is not None:
                for vkey, vval in virt.items():
                    virts[vkey][vval] += 1

        return self._finalizeNorms(norms, adds, virts)

    async def normFromTypedValu(self, valu, view=None):
        '''
        Normalize an iterable of (typename, value) elements as produced by
        Node.pack() for array properties.
        '''
        if not isinstance(valu, (tuple, list)):
            mesg = 'Array value must be a list or tuple.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg, valu=valu)

        adds = []
        norms = []
        virts = collections.defaultdict(lambda: collections.defaultdict(int))

        for item in valu:
            norm, info = await self.arraytype.normFromTypedValu(item, view=view)
            norms.append(norm)
            adds.extend(info.get('adds', ()))

            if (virt := info.get('virts')) is not None:
                for vkey, vval in virt.items():
                    virts[vkey][vval] += 1

        return self._finalizeNorms(norms, adds, virts)

    def _finalizeNorms(self, norms, adds, virts):

        if self.isuniq:
            uniqs = []
            uniqhas = set()

            for n in norms:
                if n in uniqhas:
                    continue
                uniqhas.add(n)
                uniqs.append(n)

            norms = uniqs

        if self.issorted:
            norms = sorted(norms)

        norminfo = {
            'adds': adds,
            'virts': {vkey: dict(vval) for vkey, vval in virts.items()}
        }

        return tuple(norms), norminfo

    def repr(self, valu):
        rval = [self.arraytype.repr(v) for v in valu]
        if self.splitstr:
            rval = self.splitstr.join(rval)
        return rval

    async def tostorm(self, valu, virts=None):
        return s_stormtypes.List([await self.arraytype.tostorm(v) for v in valu])

class Comp(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    _opt_defs = (
        ('sepr', None),   # type: ignore
        ('fields', ()),   # type: ignore
    )

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.sepr = self.opts.get('sepr')
        if self.sepr is not None:
            self.setNormFunc(str, self._normPyStr)

        self._checkMutability()

        self.fieldtypes = {}
        for fname, ftypename in self.opts.get('fields'):
            if isinstance(ftypename, str):
                _type = self.modl.type(ftypename)
            else:
                ftypename, opts = ftypename
                _type = self.modl.type(ftypename).clone(opts)

            if _type.deprecated and self.name.startswith('_'):
                mesg = f'The type {self.name} field {fname} uses a deprecated ' \
                       f'type {_type.name} which will be removed in 4.0.0.'
                logger.warning(mesg, extra={'synapse': {'type': self.name, 'field': fname}})

            self.fieldtypes[fname] = _type

    def _checkMutability(self):
        for fname, ftypename in self.opts.get('fields'):
            if isinstance(ftypename, (list, tuple)):
                ftypename = ftypename[0]

            if (ftype := self.modl.type(ftypename)) is None:
                raise s_exc.BadTypeDef(valu=ftypename, mesg=f'Type {ftypename} is not present in datamodel.')

            if ftype.ismutable:
                mesg = f'Comp types with mutable fields ({self.name}:{fname}) are not allowed.'
                raise s_exc.BadTypeDef(valu=ftypename, mesg=mesg)

            elif isinstance(ftype, Comp):
                ftype._checkMutability()

    async def _normPyTuple(self, valu, view=None):

        fields = self.opts.get('fields')
        if len(fields) != len(valu):
            raise s_exc.BadTypeValu(name=self.name, fields=fields, numitems=len(valu),
                                    mesg=f'invalid number of fields given for norming: {s_common.trimText(repr(valu))}')

        subs = {}
        adds = []
        norms = []

        for i, (name, _) in enumerate(fields):

            _type = self.fieldtypes[name]

            norm, info = await _type.norm(valu[i], view=view)
            norms.append(norm)

            if (typeform := self.modl.form(_type.name)) is not None:
                adds.append((typeform.name, norm, info))
                # TODO: potentially return a NodeRef to avoid a renorm?
                subs[name] = (_type.typehash, norm, info)
            else:
                subs[name] = (_type.typehash, norm, info)

            for k, v in info.get('subs', {}).items():
                subs[f'{name}:{k}'] = v

            adds.extend(info.get('adds', ()))

        norm = tuple(norms)
        return norm, {'subs': subs, 'adds': adds}

    async def _normPyStr(self, text, view=None):
        return await self._normPyTuple(text.split(self.sepr), view=view)

    def repr(self, valu):

        vals = []
        fields = self.opts.get('fields')

        for valu, (name, _) in zip(valu, fields):
            rval = self.fieldtypes[name].repr(valu)
            vals.append(rval)

        if self.sepr is not None:
            return self.sepr.join(vals)

        return tuple(vals)

class Guid(Type):

    stortype = s_layer.STOR_TYPE_GUID

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(dict, self._normPyDict)
        self.setNormFunc(list, self._normPyList)
        self.setNormFunc(tuple, self._normPyList)
        self.storlifts.update({
            '^=': self._storLiftPref,
        })

    async def _storLiftPref(self, cmpr, valu):

        try:
            byts = s_common.uhex(valu)
        except binascii.Error:
            mesg = f'Invalid GUID prefix ({valu}). Must be even number of hex chars.'
            raise s_exc.BadTypeValu(mesg=mesg)

        return (
            ('^=', byts, self.stortype),
        )

    async def _normPyList(self, valu, view=None):
        valu = await s_stormtypes.tostor(valu, packsafe=True)
        if not valu:
            mesg = 'Guid list values cannot be empty.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)
        return s_common.guid(valu), {}

    async def _normPyStr(self, valu, view=None):

        if valu == '*':
            valu = s_common.guid()
            return valu, {}

        valu = valu.lower().replace('-', '')
        if not s_common.isguid(valu):
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='valu is not a guid.')

        return valu, {}

    async def _normPyDict(self, valu, view=None):

        if (form := self.modl.form(self.name)) is None:
            mesg = f'Type "{self.name}" is not a form and cannot be normalized using a dictionary.'
            raise s_exc.BadTypeValu(mesg=mesg)

        asname = valu.pop('$as', s_common.novalu)
        if asname is not s_common.novalu:
            if not isinstance(asname, str):
                mesg = f'Dictionary guid constructor "$as" must be a form name string for form {form.full}.'
                raise s_exc.BadTypeValu(name=self.name, valu=asname, mesg=mesg)

            if asname != self.name:
                mesg = f'Dictionary guid constructor "$as" value {asname} does not match the form {form.full} being constructed.'
                raise s_exc.BadTypeValu(name=self.name, valu=asname, mesg=mesg)

        props = valu.pop('$props', {})
        trycast = valu.pop('$try', False)
        salt = valu.pop('$salt', s_common.novalu)
        unsets = valu.pop('$unsets', ())

        if not valu:
            mesg = f'No values provided for form {form.full}'
            raise s_exc.BadTypeValu(mesg=mesg)

        if unsets:
            if not isinstance(unsets, (list, tuple)) or not all(isinstance(n, str) for n in unsets):
                mesg = f'$unsets must be a list of property name strings for form {form.full}'
                raise s_exc.BadTypeValu(mesg=mesg)

            for name in unsets:
                form.reqProp(name)

                if name in valu:
                    mesg = f'Cannot specify {name!r} in $unsets - it is also used for guid deconfliction on form {form.full}'
                    raise s_exc.BadTypeValu(mesg=mesg)

                if name in props:
                    mesg = f'Cannot specify {name!r} in $unsets - it is also being set via $props on form {form.full}'
                    raise s_exc.BadTypeValu(mesg=mesg)

        if view is None:
            # Try to grab the view from the scope runtime if possible,
            # otherwise set to False so nested norms skip this.
            view = False
            if (runt := s_scope.get('runt')) is not None:
                view = runt.view

        norms = await self._normProps(form, valu, view)
        if props:
            tryprops = props.pop('$try', trycast)
            # Pass norms as context so that virt keys in $props (e.g. "price.currency")
            # can seed their base-prop value from the deconfliction dict when the base
            # is not itself present in $props.
            props = await self._normProps(form, props, view, trycast=tryprops, context=norms)

        guid, exists = await self._getGuidByNorms(form, norms, view, salt=salt, unsets=unsets)

        subinfo = {}
        addinfo = []

        if not exists:
            # Merge deconf props into $props for new-node creation.  Use setdefault so
            # that $props values (including virt-enriched entries seeded from context)
            # take precedence over the deconf dict when the same base key appears in
            # both (e.g. "price" added to $props by context-seeded "price.currency").
            for k, v in norms.items():
                props.setdefault(k, v)

        if props:
            for name, (prop, norm, info) in props.items():
                subinfo[name] = (prop.type.typehash, norm, info)
                if info:
                    ptyp = prop.type
                    if ptyp.isarray:
                        addinfo.extend(info.get('adds', ()))
                    elif self.modl.form(ptyp.name):
                        addinfo.append((ptyp.name, norm, info))
                        addinfo.extend(info.get('adds', ()))

        norminfo = {'subs': subinfo}
        if addinfo:
            norminfo['adds'] = addinfo

        return guid, norminfo

    def _splitVirt(self, form, key):
        '''
        If ``key`` refers to a virtual property on ``form`` (e.g. ``"seen.min"``),
        return ``(base_name, virt_name)``; otherwise return ``(key, None)``.

        A key is treated as a virt reference when it contains a ``'.'`` and the
        base portion names a real property on the form.
        '''
        if '.' not in key:
            return key, None

        base, virt = key.rsplit('.', 1)
        if form.prop(base) is not None:
            return base, virt

        return key, None

    async def _normProps(self, form, props, view, trycast=False, context=None):
        '''
        Normalize a dict of secondary prop values (and optional virt keys) for
        ``form``.  Returns a mapping of name -> ``(prop, normval, info)``.

        ``context`` is an optional dict of already-normalized base-prop entries
        (same format as the return value) that is consulted when a virt key
        references a base prop that is not itself present in ``props``.  This is
        used when normalizing ``$props`` so that virt keys like ``price.currency``
        can find the base ``price`` value from the deconfliction dict.
        '''

        norms = {}
        virtsbybase = {}

        # Pass 1: normalize real secondary properties.  Virtual prop keys
        # (e.g. "seen.min", "price.currency") are collected for pass 2.
        for name, valu in list(props.items()):
            base, virt = self._splitVirt(form, name)
            if virt is not None:
                virtsbybase.setdefault(base, []).append((virt, valu))
                continue

            prop = form.reqProp(name)

            try:
                norms[name] = (prop, *(await prop.type.norm(valu, view=view)))

            except s_exc.BadTypeValu as e:
                mesg = e.get('mesg')
                if not trycast:
                    if 'prop' not in e.errinfo:
                        e.update({
                            'prop': name,
                            'form': form.name,
                            'mesg': f'Bad value for prop {form.name}:{name}: {mesg}',
                        })
                    raise e

        # Pass 2: apply virtual prop keys, threading oldv/oldvirts through each
        # application so that related virts (e.g. ival min then max) compose
        # correctly.  The resulting normalized base-prop value folds back into
        # norms so it participates in deconfliction and guid generation.
        for base, virtlist in virtsbybase.items():
            prop = form.reqProp(base)

            had_base = base in norms
            if had_base:
                _, oldv, info = norms[base]
                info = dict(info)
                oldvirts = info.get('virts')
            elif context is not None and base in context:
                # Base prop not in this dict but provided via context (e.g. the
                # deconfliction dict when processing $props).  Seed oldv from there
                # so that virts like "price.currency" can apply to a price that is
                # expressed in the outer deconf dict rather than $props.
                _, oldv, ctx_info = context[base]
                oldvirts = (ctx_info or {}).get('virts')
                info = {}
            else:
                oldv = None
                oldvirts = None
                info = {}

            # Track whether at least one virt successfully applied.  When there
            # is no base value and every virt is skipped under $try, we must not
            # write None into norms.
            any_applied = had_base

            for virt, vvalu in virtlist:
                try:
                    newv, vinfo = await prop.type.normVirt(virt, oldv, vvalu, oldvirts=oldvirts)
                    oldv = newv
                    oldvirts = vinfo.get('virts', oldvirts)
                    for k, v in vinfo.items():
                        if k == 'adds':
                            adds = list(info.get('adds') or [])
                            adds.extend(v)
                            info[k] = adds
                        else:
                            info[k] = v
                    any_applied = True

                except s_exc.BadTypeValu as e:
                    if not trycast:
                        mesg = e.get('mesg')
                        if 'prop' not in e.errinfo:
                            e.update({
                                'prop': f'{base}.{virt}',
                                'form': form.name,
                                'mesg': f'Bad value for prop {form.name}:{base}.{virt}: {mesg}',
                            })
                        raise e

            if any_applied:
                norms[base] = (prop, oldv, info)

        return norms

    async def _getGuidByNorms(self, form, norms, view, salt=s_common.novalu, unsets=()):

        proplist = []
        for name, info in norms.items():
            proplist.append((name, info[1]))

        # check first for an exact match via our same deconf strategy
        proplist.sort()

        if salt is not s_common.novalu:
            proplist.append(('$salt', salt))

        guid = s_common.guid(proplist)

        if not view:
            return guid, False

        node = await view.getNodeByNdef((form.full, guid))
        if node is not None:

            # ensure we still match the property deconf criteria
            for (prop, norm, info) in norms.values():
                if not node.hasPropAltsValu(prop, norm):
                    guid = s_common.guid()
                    break
            else:
                for name in unsets:
                    if node.get(name) is not None:
                        guid = s_common.guid()
                        break
                else:
                    return guid, True

        # TODO there is an opportunity here to populate
        # a look-aside for the alternative iden to speed
        # up future deconfliction and potentially pop them
        # if we lookup a node and it no longer passes the
        # filter...

        # no exact match. lets do some counting.
        counts = []

        for (prop, norm, info) in norms.values():
            count = await view.getPropAltCount(prop, norm)
            counts.append((count, prop, norm))

        counts.sort(key=lambda x: x[0])

        # lift starting with the lowest count
        count, prop, norm = counts[0]

        cmpr = '='
        if prop.type.ispoly:
            cmpr = 'ndef='

        async for node in view.nodesByPropAlts(prop, cmpr, norm, norm=False):
            await asyncio.sleep(0)

            # filter on the remaining props/alts
            for count, prop, norm in counts[1:]:
                if not node.hasPropAltsValu(prop, norm):
                    break
            else:
                for name in unsets:
                    if node.get(name) is not None:
                        break
                else:
                    return node.valu(), True

        return guid, False

class Hex(Type):

    stortype = s_layer.STOR_TYPE_UTF8

    _opt_defs = (
        ('size', 0),  # type: ignore
        ('zeropad', 0),
    )

    def postTypeInit(self):
        self._size = self.opts.get('size')
        self._zeropad = self.opts.get('zeropad')

        # This is for backward compat with v2.142.x where zeropad was a bool
        # TODO: Remove this compat check in 3xx
        if isinstance(self._zeropad, bool):
            if self._zeropad:
                self._zeropad = self._size
            else:
                self._zeropad = 0

        if self._size < 0:
            # zero means no width check
            raise s_exc.BadConfValu(name='size', valu=self._size,
                                    mesg='Size must be >= 0')
        if self._size % 2 != 0:
            raise s_exc.BadConfValu(name='size', valu=self._size,
                                    mesg='Size must be a multiple of 2')

        if self._zeropad < 0:
            raise s_exc.BadConfValu(name='zeropad', valu=self._zeropad,
                                    mesg='Zeropad must be >= 0')
        if self._zeropad % 2 != 0:
            raise s_exc.BadConfValu(name='zeropad', valu=self._zeropad,
                                    mesg='Zeropad must be a multiple of 2')

        if self._size:
            self._zeropad = min(self._zeropad, self._size)

        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(bytes, self._normPyBytes)
        self.storlifts.update({
            '=': self._storLiftEq,
            '^=': self._storLiftPref,
        })

    def _preNormHex(self, text):
        text = text.strip().lower()
        if text.startswith('0x'):
            text = text[2:]
        return text.replace(' ', '').replace(':', '')

    async def _storLiftEq(self, cmpr, valu):

        if isinstance(valu, str):
            valu = self._preNormHex(valu)
            if valu.endswith('*'):
                return (
                    ('^=', valu[:-1], self.stortype),
                )

        return await self._storLiftNorm(cmpr, valu)

    async def _storLiftPref(self, cmpr, valu):
        if not isinstance(valu, str):
            vtyp = type(valu).__name__
            mesg = f'Hex prefix lift values must be str, not {vtyp}.'
            raise s_exc.BadTypeValu(mesg=mesg, type=vtyp, name=self.name)

        valu = self._preNormHex(valu)
        return (
            ('^=', valu, self.stortype),
        )

    async def _normPyInt(self, valu, view=None):
        extra = 7
        if valu < 0:
            # Negative values need a little more space to store the sign
            extra = 8

        bytelen = max((valu.bit_length() + extra) // 8, self._zeropad // 2)

        try:
            byts = valu.to_bytes(bytelen, 'big', signed=(valu < 0))
            hexval = s_common.ehex(byts)

        except OverflowError as e: # pragma: no cover
            mesg = f'Invalid width for {valu}.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name)

        if self._size and len(hexval) != self._size:
            raise s_exc.BadTypeValu(valu=valu, reqwidth=self._size, name=self.name,
                                    mesg='Invalid width.')

        return hexval, {}

    async def _normPyStr(self, valu, view=None):
        valu = self._preNormHex(valu)

        if len(valu) % 2 != 0:
            valu = f'0{valu}'

        if not valu:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='No string left after stripping.')

        if self._zeropad and len(valu) < self._zeropad:
            padlen = self._zeropad - len(valu)
            valu = ('0' * padlen) + valu

        try:
            # checks for valid hex width and does character
            # checking in C without using regex
            s_common.uhex(valu)
        except (binascii.Error, ValueError) as e:
            raise s_exc.BadTypeValu(valu=valu, name='hex', mesg=str(e)) from None

        if self._size and len(valu) != self._size:
            raise s_exc.BadTypeValu(valu=valu, reqwidth=self._size, name=self.name,
                                    mesg='Invalid width.')
        return valu, {}

    async def _normPyBytes(self, valu, view=None):
        return await self._normPyStr(s_common.ehex(valu))

intstors = {
    (1, True): s_layer.STOR_TYPE_I8,
    (2, True): s_layer.STOR_TYPE_I16,
    (4, True): s_layer.STOR_TYPE_I32,
    (8, True): s_layer.STOR_TYPE_I64,
    (16, True): s_layer.STOR_TYPE_I128,
    (1, False): s_layer.STOR_TYPE_U8,
    (2, False): s_layer.STOR_TYPE_U16,
    (4, False): s_layer.STOR_TYPE_U32,
    (8, False): s_layer.STOR_TYPE_U64,
    (16, False): s_layer.STOR_TYPE_U128,
}

hugemax = 730750818665451459101842
class HugeNum(Type):

    stortype = s_layer.STOR_TYPE_HUGENUM

    _opt_defs = (
        ('units', None),   # type: ignore
        ('modulo', None),  # type: ignore
        ('defunit', None),  # A unit (which must exist in units) used as a suffix and conversion factor for repr.
        ('min', None),  # Set to a value to enforce minimum value for the type.
        ('minisvalid', True),  # Only valid if min is set. True if min is itself a valid value (i.e. closed interval)
        ('max', None),  # Set to a value to enforce maximum value for the type.
        ('maxisvalid', True),  # Only valid if max is set. True if max is itself a valid value (i.e. closed interval)
    )

    def postTypeInit(self):
        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)
        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(float, self._normPyInt)
        self.setNormFunc(s_stormtypes.Number, self._normNumber)

        self.storlifts.update({
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
        })

        self.modulo = None

        self.units = {}
        units = self.opts.get('units')
        if units is not None:
            for name, mult in units.items():
                self.units[name] = s_common.hugenum(mult)

        modulo = self.opts.get('modulo')
        if modulo is not None:
            self.modulo = s_common.hugenum(modulo)

        self.defunit = self.opts.get('defunit')
        if self.defunit is not None and self.defunit not in self.units:
            mesg = f'defunit {self.defunit!r} must be present in units for type {self.name}.'
            raise s_exc.BadTypeDef(mesg=mesg)

        self.minval = None
        self.maxval = None

        minval = self.opts.get('min')
        if minval is not None:
            self.minval = s_common.hugenum(minval)
            isopen = self.opts.get('minisvalid')
            self.mincmp = (lambda x, y: x >= y) if isopen else (lambda x, y: x > y)

        maxval = self.opts.get('max')
        if maxval is not None:
            self.maxval = s_common.hugenum(maxval)
            isopen = self.opts.get('maxisvalid')
            self.maxcmp = (lambda x, y: x <= y) if isopen else (lambda x, y: x < y)

    async def _normPyStr(self, rawtext, view=None):

        # remove all whitespace so unit suffixes match regardless of spacing
        text = ''.join(rawtext.lower().split())
        text = text.replace(',', '')

        # support hexadecimal and octal integer notation (e.g. 0xff, 0o17)
        check = text[1:] if text[:1] in ('+', '-') else text
        if check[:2] in ('0x', '0o'):
            try:
                huge = s_common.hugenum(int(text, 0))
            except ValueError:
                mesg = f'Invalid hugenum: "{rawtext}"'
                raise s_exc.BadTypeValu(name=self.name, valu=rawtext, mesg=mesg) from None

            return self._norm(huge)

        try:
            valu, off = s_grammar.chop_float(text, 0)
        except Exception:
            mesg = f'Value does not start with a number: "{rawtext}"'
            raise s_exc.BadTypeValu(mesg=mesg)

        try:
            huge = s_common.hugenum(valu)
        except decimal.DecimalException as e:
            mesg = f'Invalid hugenum: {e}'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg) from None

        unit = text[off:]
        if unit:
            mult = self.units.get(unit)
            if mult is None:
                mesg = f'Unknown units for value: "{rawtext}"'
                raise s_exc.BadTypeValu(name=self.name, valu=rawtext, mesg=mesg)
            huge = s_common.hugemul(huge, mult)

        return self._norm(huge)

    async def _normPyInt(self, valu, view=None):
        return self._norm(s_common.hugenum(valu))

    async def _normNumber(self, valu, view=None):
        return self._norm(valu.valu)

    def _norm(self, huge):

        # behave modulo like int/float
        if self.modulo is not None:
            _, huge = s_common.hugemod(huge, self.modulo)
            if huge < 0:
                huge = s_common.hugeadd(huge, self.modulo)

            huge = s_common.hugeround(huge)

        if huge > hugemax:
            mesg = f'Value ({huge}) is too large for hugenum.'
            raise s_exc.BadTypeValu(mesg=mesg)

        if abs(huge) > hugemax:
            mesg = f'Value ({huge}) is too small for hugenum.'
            raise s_exc.BadTypeValu(mesg=mesg)

        huge = s_common.hugeround(huge).normalize(s_common.hugectx)

        if self.minval is not None and not self.mincmp(huge, self.minval):
            mesg = f'value is below min={self.minval}'
            raise s_exc.BadTypeValu(valu=str(huge), name=self.name, mesg=mesg)

        if self.maxval is not None and not self.maxcmp(huge, self.maxval):
            mesg = f'value is above max={self.maxval}'
            raise s_exc.BadTypeValu(valu=str(huge), name=self.name, mesg=mesg)

        return '{:f}'.format(huge), {}

    def repr(self, norm):
        if self.defunit is None:
            return str(norm)

        huge = s_common.hugediv(s_common.hugenum(norm), self.units[self.defunit])
        huge = s_common.hugeround(huge).normalize(s_common.hugectx)
        return f'{huge:f}{self.defunit}'

    async def _ctorCmprEq(self, text):
        if isinstance(text, s_stormtypes.Number):
            base = text.valu
        else:
            base = s_common.hugenum(text)

        async def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu == base
        return cmpr

    async def _ctorCmprGt(self, text):
        if isinstance(text, s_stormtypes.Number):
            base = text.valu
        else:
            base = s_common.hugenum(text)

        async def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu > base
        return cmpr

    async def _ctorCmprLt(self, text):
        if isinstance(text, s_stormtypes.Number):
            base = text.valu
        else:
            base = s_common.hugenum(text)

        async def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu < base
        return cmpr

    async def _ctorCmprGe(self, text):
        if isinstance(text, s_stormtypes.Number):
            base = text.valu
        else:
            base = s_common.hugenum(text)

        async def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu >= base
        return cmpr

    async def _ctorCmprLe(self, text):
        if isinstance(text, s_stormtypes.Number):
            base = text.valu
        else:
            base = s_common.hugenum(text)

        async def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu <= base
        return cmpr

class Price(HugeNum):

    def postTypeInit(self):
        HugeNum.postTypeInit(self)
        self.currtype = self.modl.type('econ:currency')
        self.adjtype = self.modl.type('econ:price:adjusted')

        self.setNormFunc(str, self._normPyStrCur)

        self.virts |= {
            'currency': (self.currtype, self._getCurrency),
            'adjusted': (self.adjtype, self._getAdjusted),
        }
        self.virtstor |= {
            'currency': self._storVirtCurrency,
            'adjusted': self._storVirtAdjusted,
        }
        self.virtindx |= {
            'currency': 'currency',
            'adjusted': 'adjusted',
        }

    async def _normPyStrCur(self, valu, view=None):
        numer, curr = splitPriceCurrency(valu)

        # only treat trailing alpha as currency when a numeric part remains;
        # otherwise norm the whole value (preserving the base error message).
        if curr is None or not numer.strip():
            return await HugeNum._normPyStr(self, valu, view=view)

        huge, info = await HugeNum._normPyStr(self, numer, view=view)

        curnorm, _ = await self.currtype.norm(curr)

        virts = dict(info.get('virts') or {})
        virts['currency'] = (curnorm, self.currtype.stortype)
        return huge, {**info, 'virts': virts}

    def reprWithVirts(self, norm, virts=None):
        rval = self.repr(norm)
        if virts and virts.get('currency') is not None:
            cur = virts['currency'][0]
            return f'{rval}{cur}'

        return rval

    def _getCurrency(self, valu):
        if (virts := valu[2]) is None:
            return None
        if (vval := virts.get('currency')) is None:
            return None
        return vval[0]

    def _getAdjusted(self, valu):
        if (virts := valu[2]) is None:
            return None
        if (vval := virts.get('adjusted')) is None:
            return None
        return vval[0]

    async def _storVirtCurrency(self, valu, newcurr, oldvirts=None):
        if valu is None:
            mesg = 'Cannot set currency on an unset price value.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)

        norm, curinfo = await self.currtype.norm(newcurr)
        info = {'merge': False, 'virts': dict(oldvirts) if oldvirts else {}}
        self.setVirtInfo(info, 'currency', norm, self.currtype, curinfo)
        return valu, info

    async def _storVirtAdjusted(self, valu, newadj, oldvirts=None):
        if valu is None:
            mesg = 'Cannot set adjusted on an unset price value.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)

        norm, adjinfo = await self.adjtype.norm(newadj)
        info = {'merge': False, 'virts': dict(oldvirts) if oldvirts else {}}
        self.setVirtInfo(info, 'adjusted', norm, self.adjtype, adjinfo)
        return valu, info

class PriceRangeBase(Type):
    '''
    A base type for an inclusive range of prices (econ:pricerange) and a
    directional change of a price over an interval (econ:pricechange).
    Modeled on the Ival type with a reserved "unknown" sentinel.
    '''
    stortype = s_layer.STOR_TYPE_PRICERANGE

    def postTypeInit(self):

        # a reserved sentinel (never a valid econ:price norm) used to mark an
        # unknown endpoint/derived field so a user may capture one value now
        # and the rest later (mirrors Ival.unksize). repr is also '?'.
        self.unkprice = '?'

        self.pricetype = self.modl.type('econ:price')
        self.currtype = self.modl.type('econ:currency')

        self.virts |= {
            'currency': (self.currtype, self._getCurrency),
        }
        self.virtstor |= {
            'currency': self._storVirtCurrency,
        }
        self.virtindx |= {
            'currency': 'currency',
        }

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyIter)
        self.setNormFunc(tuple, self._normPyIter)

        self.partlifts = {}

        self._initSubType()

        for part in self.parts:
            for oper in ('=', '<', '>', '<=', '>='):
                self.storlifts[f'{part}{oper}'] = self.partlifts.get(part, self._storLiftPart)

    async def getStorCmprs(self, cmpr, valu, virt=None):
        if virt is not None:
            if virt not in self.parts:
                return await self.getVirtType(virt).getStorCmprs(cmpr, valu)

            cmpr = f'{virt}{cmpr}'

        func = self.storlifts.get(cmpr)
        if func is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        return await func(cmpr, valu)

    async def _storLiftPart(self, cmpr, valu):
        norm, _ = await self.pricetype.norm(valu)
        return (
            (cmpr, norm, self.stortype),
        )

    def _getCurrency(self, valu):
        if valu is None or (virts := valu[2]) is None:
            return None

        if (vval := virts.get('currency')) is None:
            return None

        return vval[0]

    async def _storVirtCurrency(self, valu, newcurr, oldvirts=None):
        if valu is None:
            mesg = f'Cannot set currency on an unset {self.name} value.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)

        norm, curinfo = await self.currtype.norm(newcurr)
        info = {'merge': False, 'virts': dict(oldvirts) if oldvirts else {}}
        self.setVirtInfo(info, 'currency', norm, self.currtype, curinfo)
        return valu, info

    async def _normPrice(self, valu):
        if isinstance(valu, str) and valu.strip() == '?':
            return self.unkprice

        norm, _ = await self.pricetype.norm(valu)
        return norm

    def _hugestr(self, huge):
        return '{:f}'.format(s_common.hugeround(huge).normalize(s_common.hugectx))

    def _reprPrice(self, valu):
        if valu == self.unkprice:
            return '?'

        return self.pricetype.repr(valu)

    def _getNorm(self, valt):
        # getters receive the stored value tuple (valu, stortype, virts); when
        # used as a prop these types are stored poly-wrapped, so valu is
        # (typename, normtuple). unwrap to the bare normtuple.
        valu = valt[0]
        if len(valu) == 2 and isinstance(valu[1], (tuple, list)):
            return valu[1]

        return valu

class PriceRange(PriceRangeBase):
    '''
    An inclusive range of prices with a derived delta (max - min).
    '''
    def _initSubType(self):

        self.parts = ('min', 'max', 'delta')

        self.virts |= {
            'min': (self.pricetype, self._getMin),
            'max': (self.pricetype, self._getMax),
            'delta': (self.pricetype, self._getDelta),
        }
        self.virtstor |= {
            'min': self._storVirtMin,
            'max': self._storVirtMax,
            'delta': self._storVirtDelta,
        }
        self.virtindx |= {
            'min': None,
            'max': s_layer.INDX_PRICERANGE_MAX,
            'delta': s_layer.INDX_PRICERANGE_DELTA,
        }

    def _getMin(self, valt):
        if valt is None or (minv := self._getNorm(valt)[0]) == self.unkprice:
            return None

        return minv

    def _getMax(self, valt):
        if valt is None or (maxv := self._getNorm(valt)[1]) == self.unkprice:
            return None

        return maxv

    def _getDelta(self, valt):
        if valt is None or (delta := self._getNorm(valt)[2]) == self.unkprice:
            return None

        return delta

    def _computeDelta(self, minv, maxv):
        if minv == self.unkprice or maxv == self.unkprice:
            return self.unkprice

        return self._hugestr(s_common.hugesub(s_common.hugenum(maxv), s_common.hugenum(minv)))

    async def _normPyIter(self, valu, view=None):
        if len(valu) != 2:
            mesg = f'{self.name} requires a (min, max) pair.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        minv = await self._normPrice(valu[0])
        maxv = await self._normPrice(valu[1])

        if minv != self.unkprice and maxv != self.unkprice:
            if s_common.hugenum(minv) > s_common.hugenum(maxv):
                mesg = f'{self.name} min may not be greater than max.'
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        return (minv, maxv, self._computeDelta(minv, maxv)), {}

    async def _normPyStr(self, valu, view=None):
        valu = valu.strip()

        if valu == '?':
            return (self.unkprice, self.unkprice, self.unkprice), {}

        numer, curr = splitPriceCurrency(valu)
        numer = numer.strip()

        if '-' not in numer:
            mesg = f'{self.name} string must be in "min-max" format.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        minv, maxv = numer.split('-', 1)
        norm, info = await self._normPyIter((minv.strip(), maxv.strip()))

        if curr is not None:
            curnorm, _ = await self.currtype.norm(curr)
            virts = dict(info.get('virts') or {})
            virts['currency'] = (curnorm, self.currtype.stortype)
            info = {**info, 'virts': virts}

        return norm, info

    async def _storVirtMin(self, valu, newmin, oldvirts=None):
        minv = await self._normPrice(newmin)

        if valu is None:
            return (minv, self.unkprice, self._computeDelta(minv, self.unkprice)), {'merge': False, 'virts': oldvirts}

        maxv = valu[1]

        if maxv == self.unkprice and (delta := valu[2]) != self.unkprice and minv != self.unkprice:
            newmax = self._hugestr(s_common.hugeadd(s_common.hugenum(minv), s_common.hugenum(delta)))
            return (minv, newmax, delta), {'merge': False, 'virts': oldvirts}

        if minv != self.unkprice and maxv != self.unkprice:
            if s_common.hugenum(minv) > s_common.hugenum(maxv):
                mesg = f'{self.name} min may not be greater than max.'
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        return (minv, maxv, self._computeDelta(minv, maxv)), {'merge': False, 'virts': oldvirts}

    async def _storVirtMax(self, valu, newmax, oldvirts=None):
        maxv = await self._normPrice(newmax)

        if valu is None:
            return (self.unkprice, maxv, self._computeDelta(self.unkprice, maxv)), {'merge': False, 'virts': oldvirts}

        minv = valu[0]

        if minv == self.unkprice and (delta := valu[2]) != self.unkprice and maxv != self.unkprice:
            newmin = self._hugestr(s_common.hugesub(s_common.hugenum(maxv), s_common.hugenum(delta)))
            return (newmin, maxv, delta), {'merge': False, 'virts': oldvirts}

        if minv != self.unkprice and maxv != self.unkprice:
            if s_common.hugenum(minv) > s_common.hugenum(maxv):
                mesg = f'{self.name} min may not be greater than max.'
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        return (minv, maxv, self._computeDelta(minv, maxv)), {'merge': False, 'virts': oldvirts}

    async def _storVirtDelta(self, valu, newdelta, oldvirts=None):
        delta = await self._normPrice(newdelta)

        if delta != self.unkprice and s_common.hugenum(delta) < 0:
            mesg = f'{self.name} delta may not be negative.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        minv = maxv = self.unkprice
        if valu is not None:
            (minv, maxv, _) = valu

        minunk = minv == self.unkprice
        maxunk = maxv == self.unkprice

        if minunk and maxunk:
            return (minv, maxv, delta), {'merge': False, 'virts': oldvirts}

        if maxunk:
            newmax = self._hugestr(s_common.hugeadd(s_common.hugenum(minv), s_common.hugenum(delta)))
            return (minv, newmax, delta), {'merge': False, 'virts': oldvirts}

        if minunk:
            newmin = self._hugestr(s_common.hugesub(s_common.hugenum(maxv), s_common.hugenum(delta)))
            return (newmin, maxv, delta), {'merge': False, 'virts': oldvirts}

        mesg = 'Cannot set delta on a pricerange with known min and max.'
        raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

    def repr(self, norm):
        return (self._reprPrice(norm[0]), self._reprPrice(norm[1]))

    def reprWithVirts(self, norm, virts=None):
        if virts and virts.get('currency') is not None:
            cur = virts['currency'][0]
            return f'{self._reprPrice(norm[0])}-{self._reprPrice(norm[1])}{cur}'

        return self.repr(norm)

class PriceChange(PriceRangeBase):
    '''
    A directional change of a price over an interval with a derived signed
    delta (end - start) and a settable rate (percent of the starting price).
    '''
    def _initSubType(self):

        self.parts = ('start', 'end', 'delta', 'rate')

        self.ratetype = self.modl.type('ratio')

        self.virts |= {
            'start': (self.pricetype, self._getStart),
            'end': (self.pricetype, self._getEnd),
            'delta': (self.pricetype, self._getDelta),
            'rate': (self.ratetype, self._getRate),
        }
        self.virtstor |= {
            'start': self._storVirtStart,
            'end': self._storVirtEnd,
            'delta': self._storVirtDelta,
            'rate': self._storVirtRate,
        }
        self.virtindx |= {
            'start': None,
            'end': s_layer.INDX_PRICERANGE_MAX,
            'delta': s_layer.INDX_PRICERANGE_DELTA,
            'rate': s_layer.INDX_PRICERANGE_RATE,
        }

        self.partlifts['rate'] = self._storLiftRate

    async def _storLiftRate(self, cmpr, valu):
        norm, _ = await self.ratetype.norm(valu)
        return (
            (cmpr, norm, self.stortype),
        )

    def _getStart(self, valt):
        if valt is None or (strt := self._getNorm(valt)[0]) == self.unkprice:
            return None

        return strt

    def _getEnd(self, valt):
        if valt is None or (endv := self._getNorm(valt)[1]) == self.unkprice:
            return None

        return endv

    def _getDelta(self, valt):
        if valt is None or (delta := self._getNorm(valt)[2]) == self.unkprice:
            return None

        return delta

    def _getRate(self, valt):
        if valt is None or (rate := self._getNorm(valt)[3]) == self.unkprice:
            return None

        return rate

    def _computeDelta(self, strt, endv):
        if strt == self.unkprice or endv == self.unkprice:
            return self.unkprice

        return self._hugestr(s_common.hugesub(s_common.hugenum(endv), s_common.hugenum(strt)))

    def _computeRate(self, strt, endv):
        if strt == self.unkprice or endv == self.unkprice:
            return self.unkprice

        start = s_common.hugenum(strt)
        if start == 0:
            return self.unkprice

        delta = s_common.hugesub(s_common.hugenum(endv), start)
        rate = s_common.hugemul(s_common.hugediv(delta, start), s_common.hugenum(100))
        return self._hugestr(rate)

    def _deriveEnd(self, strt, delta=None, rate=None):
        start = s_common.hugenum(strt)
        if delta is not None and delta != self.unkprice:
            return self._hugestr(s_common.hugeadd(start, s_common.hugenum(delta)))

        if rate is not None and rate != self.unkprice:
            scaled = s_common.hugemul(start, s_common.hugediv(s_common.hugenum(rate), s_common.hugenum(100)))
            return self._hugestr(s_common.hugeadd(start, scaled))

        return self.unkprice

    def _deriveStart(self, endv, delta=None):
        if delta is not None and delta != self.unkprice:
            return self._hugestr(s_common.hugesub(s_common.hugenum(endv), s_common.hugenum(delta)))

        return self.unkprice

    async def _normPyIter(self, valu, view=None):
        if len(valu) != 2:
            mesg = f'{self.name} requires a (start, end) pair.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        strt = await self._normPrice(valu[0])
        endv = await self._normPrice(valu[1])

        return (strt, endv, self._computeDelta(strt, endv), self._computeRate(strt, endv)), {}

    async def _normPyStr(self, valu, view=None):
        valu = valu.strip()

        if valu == '?':
            return (self.unkprice, self.unkprice, self.unkprice, self.unkprice), {}

        numer, curr = splitPriceCurrency(valu)
        numer = numer.strip()

        strt, sep, endv = numer.partition('-')
        strt = strt.strip()
        endv = endv.strip()

        if not sep or not strt or not endv:
            mesg = f'{self.name} string must be in "start-end" format; use a (start, end) pair for negative endpoints.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        norm, info = await self._normPyIter((strt, endv))

        if curr is not None:
            curnorm, _ = await self.currtype.norm(curr)
            virts = dict(info.get('virts') or {})
            virts['currency'] = (curnorm, self.currtype.stortype)
            info = {**info, 'virts': virts}

        return norm, info

    async def _storVirtStart(self, valu, newstart, oldvirts=None):
        strt = await self._normPrice(newstart)

        if valu is None:
            return (strt, self.unkprice, self.unkprice, self.unkprice), {'merge': False, 'virts': oldvirts}

        endv = valu[1]

        if endv == self.unkprice and strt != self.unkprice:
            (_, delta, rate) = (valu[1], valu[2], valu[3])
            if delta != self.unkprice:
                endv = self._deriveEnd(strt, delta=delta)
            elif rate != self.unkprice:
                endv = self._deriveEnd(strt, rate=rate)

        return (strt, endv, self._computeDelta(strt, endv), self._computeRate(strt, endv)), {'merge': False, 'virts': oldvirts}

    async def _storVirtEnd(self, valu, newend, oldvirts=None):
        endv = await self._normPrice(newend)

        if valu is None:
            return (self.unkprice, endv, self.unkprice, self.unkprice), {'merge': False, 'virts': oldvirts}

        strt = valu[0]

        if strt == self.unkprice and endv != self.unkprice:
            delta = valu[2]
            if delta != self.unkprice:
                strt = self._deriveStart(endv, delta=delta)

        return (strt, endv, self._computeDelta(strt, endv), self._computeRate(strt, endv)), {'merge': False, 'virts': oldvirts}

    async def _storVirtDelta(self, valu, newdelta, oldvirts=None):
        delta = await self._normPrice(newdelta)

        strt = endv = self.unkprice
        if valu is not None:
            (strt, endv, _, _) = valu

        strtunk = strt == self.unkprice
        endunk = endv == self.unkprice

        if strtunk and endunk:
            return (strt, endv, delta, self.unkprice), {'merge': False, 'virts': oldvirts}

        if endunk:
            newend = self._deriveEnd(strt, delta=delta)
            return (strt, newend, delta, self._computeRate(strt, newend)), {'merge': False, 'virts': oldvirts}

        if strtunk:
            newstart = self._deriveStart(endv, delta=delta)
            return (newstart, endv, delta, self._computeRate(newstart, endv)), {'merge': False, 'virts': oldvirts}

        mesg = 'Cannot set delta on a pricechange with known start and end.'
        raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

    async def _storVirtRate(self, valu, newrate, oldvirts=None):
        rate, _ = await self.ratetype.norm(newrate)

        strt = endv = self.unkprice
        if valu is not None:
            (strt, endv, _, _) = valu

        strtunk = strt == self.unkprice
        endunk = endv == self.unkprice

        if strtunk and endunk:
            return (strt, endv, self.unkprice, rate), {'merge': False, 'virts': oldvirts}

        if endunk:
            newend = self._deriveEnd(strt, rate=rate)
            return (strt, newend, self._computeDelta(strt, newend), rate), {'merge': False, 'virts': oldvirts}

        mesg = 'Cannot set rate on a pricechange with known start and end.'
        raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

    def repr(self, norm):
        return (self._reprPrice(norm[0]), self._reprPrice(norm[1]))

    def reprWithVirts(self, norm, virts=None):
        if virts and virts.get('currency') is not None:
            cur = virts['currency'][0]
            return f'{self._reprPrice(norm[0])}-{self._reprPrice(norm[1])}{cur}'

        return self.repr(norm)

class IntBase(Type):

    def __init__(self, modl, name, info, opts, skipinit=False):

        Type.__init__(self, modl, name, info, opts, skipinit=skipinit)

        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)
        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)

        self.storlifts.update({
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
        })

        self.storlifts.pop('~=', None)

        self.setNormFunc(decimal.Decimal, self._normPyDecimal)
        self.setNormFunc(s_stormtypes.Number, self._normNumber)

    async def _ctorCmprGe(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu >= norm
        return cmpr

    async def _ctorCmprLe(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu <= norm
        return cmpr

    async def _ctorCmprGt(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu > norm
        return cmpr

    async def _ctorCmprLt(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu < norm
        return cmpr

    async def _normPyDecimal(self, valu, view=None):
        return await self._normPyInt(int(valu))

    async def _normNumber(self, valu, view=None):
        return await self._normPyInt(int(valu.valu))

class Int(IntBase):

    _opt_defs = (
        ('size', 8),  # type: ignore # Set the storage size of the integer type in bytes.
        ('signed', True),
        ('enums', None),
        ('enums:strict', True),

        ('fmt', '%d'),  # Set to an integer compatible format string to control repr.

        ('min', None),  # Set to a value to enforce minimum value for the type.
        ('max', None),  # Set to a value to enforce maximum value for the type.

        ('ismin', False),  # Set to True to enable ismin behavior on value merge.
        ('ismax', False),  # Set to True to enable ismax behavior on value merge.
    )

    def postTypeInit(self):

        self.size = self.opts.get('size')
        self.signed = self.opts.get('signed')
        self.stortype = intstors.get((self.size, self.signed))
        if self.stortype is None:
            mesg = f'Invalid integer size ({self.size})'
            raise s_exc.BadTypeDef(mesg=mesg)

        self.ismin = self.opts.get('ismin')
        self.ismax = self.opts.get('ismax')

        if self.opts.get('ismin') and self.opts.get('ismax'):
            mesg = f'Int type ({self.name}) has both ismin and ismax set.'
            raise s_exc.BadTypeDef(mesg=mesg)

        self.enumnorm = {}
        self.enumrepr = {}

        self.fmt = self.opts.get('fmt')
        self.enumstrict = self.opts.get('enums:strict')

        enums = self.opts.get('enums')
        if enums is not None:
            self.enumrepr.update(dict(enums))
            self.enumnorm.update({(n.lower(), v) for (v, n) in enums})

            if len(enums) != len(self.enumrepr):
                mesg = 'Number of enums does not match the number of string reprs.'
                raise s_exc.BadTypeDef(mesg=mesg,
                                       name=self.name)

            if len(enums) != len(self.enumnorm):
                mesg = 'Number of enums does not match the number of string norms.'
                raise s_exc.BadTypeDef(mesg=mesg,
                                       name=self.name)

        if not self.signed:
            minmin = 0
            maxmax = 2 ** (self.size * 8) - 1
        else:
            minmin = -2 ** ((self.size * 8) - 1)
            maxmax = 2 ** ((self.size * 8) - 1) - 1

        if (minval := self.opts.get('min')) is None:
            minval = minmin

        if (maxval := self.opts.get('max')) is None:
            maxval = maxmax

        if minval < minmin or maxval > maxmax or maxval < minval:
            raise s_exc.BadTypeDef(self.opts, name=self.name)

        self.minval = minval
        self.maxval = maxval

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bool, self._normPyBool)
        self.setNormFunc(float, self._normPyFloat)

    def merge(self, oldv, newv):

        if self.ismin:
            return min(oldv, newv)

        if self.ismax:
            return max(oldv, newv)

        return newv

    async def _normPyStr(self, valu, view=None):

        if self.enumnorm:
            ival = self.enumnorm.get(valu.lower())
            if ival is not None:
                return await self._normPyInt(ival)

        # strip leading 0s that do not change base...
        if len(valu) >= 2 and valu[0] == '0' and valu[1].isdigit():
            valu = valu.lstrip('0')

        try:
            valu = int(valu, 0)
        except ValueError as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg=str(e)) from None
        return await self._normPyInt(valu)

    async def _normPyBool(self, valu, view=None):
        return await self._normPyInt(int(valu))

    async def _normPyInt(self, valu, view=None):

        if self.minval is not None and valu < self.minval:
            mesg = f'value is below min={self.minval}'
            raise s_exc.BadTypeValu(valu=repr(valu), name=self.name, mesg=mesg)

        if self.maxval is not None and valu > self.maxval:
            mesg = f'value is above max={self.maxval}'
            raise s_exc.BadTypeValu(valu=repr(valu), name=self.name, mesg=mesg)

        if self.enumrepr and self.enumstrict and valu not in self.enumrepr:
            mesg = 'Value is not a valid enum value.'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        return valu, {}

    async def _normPyFloat(self, valu, view=None):
        return await self._normPyInt(int(valu))

    def repr(self, norm):

        text = self.enumrepr.get(norm)
        if text is not None:
            return text

        return self.fmt % norm

class Float(Type):
    _opt_defs = (
        # Note: currently unused
        ('fmt', '%f'),  # type:ignore # Set to an float compatible format string to control repr.

        ('min', None),  # Set to a value to enforce minimum value for the type.
        ('minisvalid', True),  # Only valid if min is set.  True if min is itself a valid value (i.e. closed interval)
        ('max', None),  # Set to a value to enforce maximum value for the type.
        ('maxisvalid', True),  # Only valid if max is set.  True if max is itself a valid value (i.e. closed interval)
    )

    stortype = s_layer.STOR_TYPE_FLOAT64

    def __init__(self, modl, name, info, opts, skipinit=False):

        Type.__init__(self, modl, name, info, opts, skipinit=skipinit)

        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)

        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)

        self.storlifts.update({
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
        })

    async def _ctorCmprGe(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu >= norm
        return cmpr

    async def _ctorCmprLe(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu <= norm
        return cmpr

    async def _ctorCmprGt(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu > norm
        return cmpr

    async def _ctorCmprLt(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu < norm
        return cmpr

    def postTypeInit(self):

        self.enumnorm = {}
        self.enumrepr = {}

        self.minval = self.opts.get('min')
        self.maxval = self.opts.get('max')

        if self.minval is not None:
            isopen = self.opts.get('minisvalid')
            self.mincmp = (lambda x, y: x >= y) if isopen else (lambda x, y: x > y)

        if self.maxval is not None:
            isopen = self.opts.get('maxisvalid')
            self.maxcmp = (lambda x, y: x <= y) if isopen else (lambda x, y: x < y)

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(float, self._normPyFloat)
        self.setNormFunc(decimal.Decimal, self._normPyInt)
        self.setNormFunc(s_stormtypes.Number, self._normNumber)

    async def _normPyStr(self, valu, view=None):

        try:
            valu = float(valu)
        except ValueError as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg=str(e)) from None
        return await self._normPyFloat(valu)

    async def _normPyInt(self, valu, view=None):
        valu = float(valu)
        return await self._normPyFloat(valu)

    async def _normNumber(self, valu, view=None):
        return await self._normPyFloat(float(valu.valu))

    async def _normPyFloat(self, valu, view=None):

        if self.minval is not None and not self.mincmp(valu, self.minval):
            mesg = f'value is below min={self.minval}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        if self.maxval is not None and not self.maxcmp(valu, self.maxval):
            mesg = f'value is above max={self.maxval}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        return valu, {}

    def repr(self, norm):

        return str(norm)

class Ival(Type):
    '''
    An interval, i.e. a range, of times
    '''
    stortype = s_layer.STOR_TYPE_IVAL

    _opt_defs = (
        ('precision', 'microsecond'),
        # ``names`` renames the min/max virtual properties (e.g. for an
        # it:lifespan that exposes :created / :deleted). The renamed virts
        # behave identically; the comparators are translated back to the
        # canonical min/max before reaching the storage layer.
        ('names', None),
    )

    def postTypeInit(self):
        self.unksize = 0x7fffffffffffffff
        self.futsize = 0x7ffffffffffffffe
        self.maxsize = 253402300799999999  # 9999/12/31 23:59:59.999999

        precstr = self.opts.get('precision')
        self.prec = s_time.precisions.get(precstr)

        if self.prec is None:
            mesg = f'Ival type ({self.name}) has invalid precision: {precstr}.'
            raise s_exc.BadTypeDef(mesg=mesg)

        self.prectype = self.modl.type('timeprecision')

        self.ticktype = self.modl.type('time').clone({'precision': precstr})
        self.tocktype = self.modl.type('time').clone({'precision': precstr, 'maxfill': True})
        self.duratype = self.modl.type('duration')

        self.virts |= {
            'min': (self.ticktype, self._getMin),
            'max': (self.tocktype, self._getMax),
            'duration': (self.duratype, self._getDuration),
            'precision': (self.prectype, self._getPrec),
        }

        self.virtstor |= {
            'min': self._storVirtMin,
            'max': self._storVirtMax,
            'duration': self._storVirtDuration,
            'precision': self._storVirtPrec,
        }

        self.virtindx |= {
            'min': None,
            'max': s_layer.INDX_IVAL_MAX,
            'duration': s_layer.INDX_IVAL_DURATION
        }

        self.tagvirtindx = {
            'min': s_layer.INDX_TAG,
            'max': s_layer.INDX_TAG_MAX,
            'duration': s_layer.INDX_TAG_DURATION
        }

        # Range stuff with ival's don't make sense
        self.storlifts.pop('range=', None)
        self._cmpr_ctors.pop('range=', None)

        self.setCmprCtor('@=', self._ctorCmprAt)

        # _ctorCmprAt implements its own custom norm-style resolution
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyIter)
        self.setNormFunc(tuple, self._normPyIter)
        self.setNormFunc(decimal.Decimal, self._normPyDecimal)
        self.setNormFunc(s_stormtypes.Number, self._normNumber)
        self.storlifts.update({
            '@=': self._storLiftAt,
        })

        for part in ('min', 'max'):
            self.storlifts[f'{part}@='] = self._storLiftPartAt

        for part in ('min', 'max'):
            for oper in ('=', '<', '>', '<=', '>='):
                self.storlifts[f'{part}{oper}'] = self._storLiftPart

        for oper in ('=', '<', '>', '<=', '>='):
            self.storlifts[f'duration{oper}'] = self._storLiftDuration

        # map a renamed virt back to its canonical min/max name
        self._virtcanon = {}
        if (names := self.opts.get('names')):
            self._renameVirts(names)

    def _renameVirts(self, names):
        # ``names`` maps a canonical virt name to its replacement, e.g.
        # {'min': 'created', 'max': 'deleted'}. The renamed virts reuse the same
        # getters, storage funcs and indexes; only the model-facing name changes.
        for canon in names:
            if canon not in ('min', 'max'):
                mesg = f'Ival type ({self.name}) may only rename the min/max virts, not {canon}.'
                raise s_exc.BadTypeDef(mesg=mesg)

        # Note: the min/max virts may safely be renamed to "created"/"updated"
        # ( otherwise reserved node meta virt names ) because Ival types carry
        # editable virts and so can never be used to declare a form ( enforced
        # in datamodel.addForm ), which is the only place those meta virts apply.
        self._virtcanon = {custom: canon for canon, custom in names.items()}

        def rekey(item):
            return {names.get(key, key): valu for key, valu in item.items()}

        self.virts = rekey(self.virts)
        self.virtstor = rekey(self.virtstor)
        self.virtindx = rekey(self.virtindx)
        self.tagvirtindx = rekey(self.tagvirtindx)

        storlifts = {}
        for key, func in self.storlifts.items():
            for canon, custom in names.items():
                if key.startswith(canon):
                    key = f'{custom}{key[len(canon):]}'
                    break

            storlifts[key] = func

        self.storlifts = storlifts

        # rename the declarative virt metadata so doc-only overrides and the
        # generated model docs use the renamed names ( copy first to avoid
        # mutating virt metadata shared with the base ival type ).
        if (infovirts := self.info.get('virts')) is not None:
            self.info = dict(self.info)
            self.info['virts'] = tuple(
                (names.get(name, name), tdef, vinfo) for (name, tdef, vinfo) in infovirts
            )

    def _toCanonCmpr(self, cmpr):
        # translate a renamed virt comparator (e.g. 'created<=') back to the
        # canonical comparator the storage layer understands (e.g. 'min<=').
        for custom, canon in self._virtcanon.items():
            if cmpr.startswith(custom):
                return f'{canon}{cmpr[len(custom):]}'

        return cmpr

    async def getStorCmprs(self, cmpr, valu, virt=None):
        if virt is not None:
            cmpr = f'{virt}{cmpr}'

        func = self.storlifts.get(cmpr)
        if func is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        return await func(cmpr, valu)

    async def _storLiftAt(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            return await self._storLiftNorm(cmpr, valu)

        ticktock = (await self.ticktype.getTickTock(valu))[:2]
        return (
            ('@=', ticktock, self.stortype),
        )

    async def _ctorCmprAt(self, valu):

        # unwrap a typed Storm value (e.g. a tag timestamp or ival prop value)
        # so the comparison works when the @= operand is passed in directly.
        if isinstance(valu, s_stormtypes.Valu):
            valu = valu.value()

        if valu is None or valu == (None, None, None):
            async def cmpr(item):
                return False
            return cmpr

        if isinstance(valu, (str, int)):
            minv, maxv, _ = (await self.norm(valu))[0]
        elif isinstance(valu, (list, tuple)):
            minv, maxv = (await self._normByTickTock(valu))[0]
            # Use has input the nullset in a comparison operation.
            if minv >= maxv:
                async def cmpr(item):
                    return False
                return cmpr
        else:
            raise s_exc.NoSuchFunc(name=self.name,
                                   mesg='no norm for @= operator: %r' % (type(valu),))

        async def cmpr(item):
            if item is None:
                return False

            if item == (None, None, None):
                return False

            othr, info = await self.norm(item)

            if othr[0] >= maxv:
                return False

            if othr[1] <= minv:
                return False

            return True

        return cmpr

    async def _storLiftPart(self, cmpr, valu):
        norm, _ = await self.ticktype.norm(valu)
        return (
            (self._toCanonCmpr(cmpr), norm, self.stortype),
        )

    async def _storLiftPartAt(self, cmpr, valu):

        cmpr = self._toCanonCmpr(cmpr)

        if type(valu) not in (list, tuple):
            return await self._storLiftNorm(cmpr, valu)

        ticktock = (await self.ticktype.getTickTock(valu))[:2]
        return (
            (cmpr, ticktock, self.stortype),
        )

    async def _storLiftDuration(self, cmpr, valu):
        norm, _ = await self.duratype.norm(valu)
        futstart = None

        if norm not in (self.duratype.futdura, self.duratype.unkdura):
            futstart = s_common.now() - norm

        return (
            (cmpr, (norm, futstart), self.stortype),
        )

    def _getMin(self, valu):
        if valu is None:
            return None

        if isinstance(valu := valu[0], int):
            return valu

        if isinstance(valu[0], int):
            return valu[0]

        return valu[1][0]

    def _getMax(self, valu):
        if valu is None:
            return None

        if isinstance(ival := valu[0], int):
            return valu[1]

        if isinstance(ival[0], int):
            return ival[1]

        return ival[1][1]

    def _getDuration(self, valu):
        if valu is None:
            return None

        if isinstance(ival := valu[0], int):
            ival = valu
        elif not isinstance(ival[0], int):
            ival = ival[1]

        if (dura := ival[2]) != self.duratype.futdura:
            return dura

        if (dura := (s_common.now() - ival[0])) < 0:
            return None

        return dura

    def _getPrec(self, valu):
        if (virts := valu[2]) is None or (vval := virts.get('precision')) is None:
            return self.prec
        return vval[0]

    async def _storVirtMin(self, valu, newmin, oldvirts=None):
        newv, norminfo = await self.norm(newmin)
        minv = newv[0]

        if valu is None:
            return (minv, self.unksize, self.duratype.unkdura), norminfo

        maxv = valu[1]
        norminfo['merge'] = False

        if maxv == self.futsize:
            return (minv, maxv, self.duratype.futdura), norminfo

        elif minv == self.unksize:
            return (minv, maxv, self.duratype.unkdura), norminfo

        elif maxv == self.unksize:
            if (dura := valu[2]) not in (self.duratype.unkdura, self.duratype.futdura):
                newmax, _ = await self.ticktype.norm(minv + dura)
                return (minv, newmax, dura), norminfo
            return (minv, maxv, self.duratype.unkdura), norminfo

        maxv = max(newv[1], maxv)
        return (minv, maxv, maxv - minv), norminfo

    async def _storVirtMax(self, valu, newmax, oldvirts=None):
        minv = self.unksize
        if valu is not None:
            minv = valu[0]

        maxv, norminfo = await self.tocktype.norm(newmax)
        norminfo['merge'] = False

        if maxv == self.unksize:
            return (minv, maxv, self.duratype.unkdura), norminfo

        if maxv == self.futsize:
            return (minv, maxv, self.duratype.futdura), norminfo

        if minv == self.unksize:
            if valu is not None and (dura := valu[2]) not in (self.duratype.unkdura, self.duratype.futdura):
                newmin, _ = await self.ticktype.norm(maxv - dura)
                return (newmin, maxv, dura), norminfo
            return (minv, maxv, self.duratype.unkdura), norminfo

        newmin, _ = await self.ticktype.norm(maxv - 1)
        minv = min(minv, newmin)

        return (minv, maxv, maxv - minv), norminfo

    async def _storVirtDuration(self, valu, newdura, oldvirts=None):
        dura, norminfo = await self.duratype.norm(newdura)
        norminfo['merge'] = False

        minv = maxv = self.unksize
        if valu is not None:
            (minv, maxv, _) = valu

        if minv == self.unksize:
            if dura == self.duratype.futdura:
                return (minv, self.futsize, dura), norminfo

            elif maxv == self.unksize:
                return (minv, maxv, dura), norminfo

            elif maxv == self.futsize:
                return (minv, self.unksize, dura), norminfo

            newmin, _ = await self.ticktype.norm(maxv - dura)
            return (newmin, maxv, dura), norminfo

        elif maxv in (self.unksize, self.futsize):
            newmax, _ = await self.ticktype.norm(minv + dura)
            return (minv, newmax, dura), norminfo

        mesg = 'Cannot set duration on an ival with known start/end times.'
        raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

    async def _storVirtPrec(self, valu, newprec, oldvirts=None):
        if valu is None:
            mesg = 'Cannot set precision on an empty ival value.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)

        prec = (await self.prectype.norm(newprec))[0]
        return await self._normPyIter(valu, prec=prec)

    def getTagVirtIndx(self, virt):
        indx = self.tagvirtindx.get(virt, s_common.novalu)
        if indx is s_common.novalu:
            raise s_exc.NoSuchVirt.init(virt, self)

        return indx

    async def _normPyInt(self, valu, view=None):
        minv, _ = await self.ticktype._normPyInt(valu)
        if minv == self.unksize:
            return (minv, minv, self.duratype.unkdura), {}

        if minv == self.futsize:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Ival min may not be *')

        maxv, _ = await self.tocktype._normPyInt(minv + 1)
        return (minv, maxv, 1), {}

    async def _normPyDecimal(self, valu, view=None):
        return await self._normPyInt(int(valu))

    async def _normNumber(self, valu, view=None):
        return await self._normPyInt(int(valu.valu))

    async def _normPyStr(self, valu, view=None):
        valu = valu.strip().lower()

        if ',' in valu:
            return await self._normPyIter(valu.split(',', 2))

        minv, _ = await self.ticktype.norm(valu)
        if minv == self.unksize:
            return (minv, minv, self.duratype.unkdura), {}

        if minv == self.futsize:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Ival min may not be *')

        maxv, _ = await self.tocktype._normPyInt(minv + 1)
        return (minv, maxv, 1), {}

    async def _normPyIter(self, valu, prec=None, view=None):
        (minv, maxv), info = await self._normByTickTock(valu, prec=prec)

        if minv == self.futsize:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Ival min may not be *')

        if minv != self.unksize:
            if minv == maxv:
                maxv = maxv + 1

            # Norm via iter must produce an actual range if not unknown.
            if minv > maxv:
                raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                        mesg='Ival range must in (min, max) format')

        if maxv == self.futsize:
            return (minv, maxv, self.duratype.futdura), info

        elif minv == self.unksize or maxv == self.unksize:
            return (minv, maxv, self.duratype.unkdura), info

        return (minv, maxv, maxv - minv), info

    async def _normByTickTock(self, valu, prec=None, view=None):
        if len(valu) not in (2, 3):
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='Ival _normPyIter requires 2 or 3 items')

        tick, tock, newprec = await self.ticktype.getTickTock(valu, prec=prec)

        minv, mininfo = await self.ticktype._normPyInt(tick, prec=newprec)
        maxv, maxinfo = await self.tocktype._normPyInt(tock, prec=newprec)
        return (minv, maxv), (mininfo or maxinfo)

    def merge(self, oldv, newv):
        minv = min(oldv[0], newv[0])

        if oldv[1] == self.unksize:
            maxv = newv[1]
        elif newv[1] != self.unksize:
            maxv = max(oldv[1], newv[1])
        else:
            maxv = oldv[1]

        if maxv == self.futsize:
            return (minv, maxv, self.duratype.futdura)

        elif minv == self.unksize or maxv == self.unksize:
            return (minv, maxv, self.duratype.unkdura)

        return (minv, maxv, maxv - minv)

    def repr(self, norm):
        mint = self.ticktype.repr(norm[0])
        maxt = self.tocktype.repr(norm[1])
        return (mint, maxt)

class Loc(Type):

    stortype = s_layer.STOR_TYPE_LOC

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setCmprCtor('^=', self._ctorCmprPref)
        self.setLiftHintCmprCtor('^=', self._ctorCmprPref)
        self.storlifts.update({
            '=': self._storLiftEq,
            '^=': self._storLiftPref,
        })

        self.stemcache = s_cache.FixedCache(self._stems, size=1000)

    async def _storLiftEq(self, cmpr, valu):

        if isinstance(valu, str) and valu.endswith('.*'):
            norm, info = await self.norm(valu[:-2])
            return (
                ('^=', norm, self.stortype),
            )

        norm, info = await self.norm(valu)
        return (
            ('=', norm, self.stortype),
        )

    async def _storLiftPref(self, cmpr, valu):
        norm, info = await self.norm(valu)
        return (
            ('^=', norm, self.stortype),
        )

    async def _normPyStr(self, valu, view=None):

        valu = valu.lower().strip()

        norms = []
        for part in valu.split('.'):
            part = ' '.join(part.split())
            norms.append(part)

        norm = '.'.join(norms)
        return norm, {}

    async def _stems(self, valu):
        norm, info = await self.norm(valu)
        parts = norm.split('.')
        ret = []
        for i in range(len(parts)):
            part = '.'.join(parts[:i + 1])
            ret.append(part)
        return ret

    async def _ctorCmprPref(self, text):
        norm, _ = await self.norm(text)

        async def cmpr(valu):
            # Shortcut equality
            if valu == norm:
                return True

            vstems = await self.stemcache.aget(valu)
            return norm in vstems

        return cmpr

    def repr(self, norm):
        return norm

class Poly(Type):

    stortype = s_layer.STOR_TYPE_POLY

    ispoly = True

    _opt_defs = (
        ('default_types', None),    # type: ignore
        ('docs', None),             # type: ignore
        ('interfaces', None),       # type: ignore
        ('types', None),            # type: ignore
    )

    def postTypeInit(self):

        self.typetype = self.modl.type('syn:type')
        self.valuetype = self.modl.type('data')
        self.virts |= {
            'type': (self.typetype, self._getType),
            'value': (self.valuetype, self._getValue),
        }

        self.virtindx |= {
            'type': None,
        }

        self.virtlifts |= {
            'type': {'=': self._storLiftType},
        }

        self.ifaces = frozenset(self.opts.get('interfaces') or ())
        self.typeset = frozenset(self.opts.get('types') or ())
        self.formtypes = frozenset(name for name in self.typeset if name in self.modl.forminfos)

        self.hasforms = bool(self.ifaces or self.formtypes)

        self.defaulttypes = self.opts.get('default_types')
        if self.defaulttypes is not None:
            for tname in self.defaulttypes:
                if not self.typeset or tname not in self.typeset:
                    mesg = f'Default types must be all be allowed on {self.name}.'
                    raise s_exc.BadTypeDef(self.opts, name=self.name, mesg=mesg)

            # guid types are left out of the default norming list so a value cannot
            # be inadvertently normed into the wrong guid type.
            self.defaulttypes = tuple(tname for tname in self.defaulttypes
                                      if self.modl.type(tname).stortype != s_layer.STOR_TYPE_GUID)

    def typefilter(self, tobj):
        if not self.typeset:
            return False
        return tobj.name in self.typeset

    def ifacefilter(self, form):
        if not self.ifaces:
            return False
        return any(iface in self.ifaces for iface in form.ifaces)

    def formfilter(self, form):
        if self.formtypes and any(f in self.formtypes for f in form.formtypes):
            return True
        return self.ifacefilter(form)

    def getTypeSet(self):
        return self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces)

    def getCmprCtor(self, name):
        typeset = self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces)

        if not any(ntyp.getCmprCtor(name) is not None for ntyp in typeset):
            return None

        async def ctor(val1):

            ndefcmpr = isinstance(val1, (s_node.NodeBase, s_stormtypes.Valu))
            if isinstance(val1, s_node.NodeBase):
                realv = val1.ndef[1]
            elif isinstance(val1, s_stormtypes.Valu):
                realv = val1.valu[1]
            else:
                realv = val1

            # build a comparator per member type. the comparison value must be
            # valid for at least one member type or the comparison is malformed.
            cmprs = {}
            lasterr = None
            for ntyp in typeset:
                if (tctor := ntyp.getCmprCtor(name)) is None:
                    continue
                try:
                    cmprs[ntyp.name] = await tctor(realv)
                except s_exc.BadTypeValu as e:
                    lasterr = e

            if not cmprs and lasterr is not None:
                raise lasterr

            async def cmprfunc(val2):

                # a poly value is compared using its concrete stored type rather
                # than across the entire poly typeset.
                if ndefcmpr:
                    nval = val1.ndef if isinstance(val1, s_node.NodeBase) else val1.valu
                    if nval == val2:
                        return True

                if (cmpr := cmprs.get(val2[0])) is None:
                    return name == '!='

                return await cmpr(val2[1])

            return cmprfunc

        return ctor

    async def normVirt(self, name, valu, newvirt, oldvirts=None):

        if valu is not None:
            typename = valu[0]
            ntyp = self.modl.type(typename)
            newv, norminfo = await ntyp.normVirt(name, valu[1], newvirt, oldvirts=oldvirts)
            return (typename, newv), norminfo

        for ntyp in self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces):
            if name in ntyp.virtstor:
                newv, norminfo = await ntyp.normVirt(name, None, newvirt, oldvirts=oldvirts)
                return (ntyp.name, newv), norminfo

        mesg = f'No editable virtual prop named {name} on type {self.name}.'
        raise s_exc.NoSuchVirt.init(name, self, mesg=mesg)

    def getVirtIndx(self, virt):
        for ntyp in self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces):
            if (indx := ntyp.virtindx.get(virt, s_common.novalu)) is not s_common.novalu:
                return indx
        else:
            mesg = f'Virtual prop {virt} is not valid for any types supported by {self.name}.'
            raise s_exc.NoSuchVirt.init(virt, self, mesg=mesg)

    def getVirtType(self, virt):
        if (info := self.virts.get(virt)) is not None:
            return info[0]

        for ntyp in self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces):
            if virt in ntyp.virts:
                return ntyp.virts[virt][0]

        raise s_exc.NoSuchVirt.init(virt, self)

    def getVirtGetr(self, virt):
        if (info := self.virts.get(virt)) is not None:
            return info[1]

        for ntyp in self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces):
            if virt in ntyp.virts:
                return ntyp.virts[virt][1]

        raise s_exc.NoSuchVirt.init(virt, self)

    def getVirtInfo(self, virt):
        if (info := self.virts.get(virt)) is not None:
            return info[0], info[1]

        for ntyp in self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces):
            if virt in ntyp.virts:
                info = ntyp.virts[virt]
                return info[0], info[1]

        raise s_exc.NoSuchVirt.init(virt, self)

    def _raiseBadTypeValu(self, valu):
        typeset = tuple(sorted(self.typeset))
        ifaces = tuple(sorted(self.ifaces))

        mesg = f'Value of type {valu} is not allowed for {self.name}'
        if typeset:
            mesg += f' types=({", ".join(typeset)})'

        if ifaces:
            mesg += f' interfaces=({", ".join(ifaces)})'

        raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg, types=typeset, interfaces=ifaces)

    async def _storLiftType(self, cmpr, valu):
        valu = valu.lower().strip()

        if (tobj := self.modl.type(valu)) is None or not self.typefilter(tobj):
            if (form := self.modl.form(valu)) is None or not self.formfilter(form):
                self._raiseBadTypeValu(valu)

        return (('type=', valu, self.stortype),)

    def _getType(self, valu):
        return valu[0][0]

    def _getValue(self, valu):
        return valu[0][1]

    def getStorType(self, valu):
        tobj = self.modl.reqType(valu[0])
        return s_layer.STOR_FLAG_POLY | tobj.stortype

    async def getStorCmprs(self, cmpr, valu, virt=None):

        if virt is not None:
            if (vlifts := self.virtlifts.get(virt)) is not None:
                if (func := vlifts.get(cmpr)) is not None:
                    return await func(cmpr, valu)

        if isinstance(valu, s_node.NodeBase):
            if cmpr == '=':
                if self.formfilter(valu.form):
                    return (('ndef=', valu.ndef, s_layer.STOR_TYPE_POLY),)

            valu = valu.ndef[1]

        elif isinstance(valu, s_stormtypes.Valu):
            if cmpr == '=':
                typename = valu.valu[0]

                if self.typefilter(self.modl.type(typename)):
                    return (('ndef=', valu.valu, s_layer.STOR_TYPE_POLY),)

                elif (form := self.modl.form(typename)) is not None and self.formfilter(form):
                    return (('ndef=', valu.valu, s_layer.STOR_TYPE_POLY),)

            valu = valu.valu[1]

        cmprs = []
        isvalid = False
        novirts = False
        badtype = False

        typeset = self.modl.getTypeSet(types=self.typeset, interfaces=self.ifaces)

        if len(typeset) == 0:
            if cmpr == '?=':
                return ()

            mesg = f'Value {s_common.trimText(repr(valu))} is not valid for any types supported by {self.name}.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, cmpr=cmpr, mesg=mesg)

        for ntyp in typeset:
            try:
                # group value lifts that share a (cmpr, value, stortype) and collect the types they are
                # valid for, so the layer can constrain the lift to those types rather than every type that
                # happens to share a storage type.

                tname = ntyp.name if virt is None else None
                for (ncmpr, ncval, nstor) in await ntyp.getStorCmprs(cmpr, valu, virt=virt):
                    for item in cmprs:
                        if item[:3] == (ncmpr, ncval, nstor):
                            if tname is not None:
                                item[3].add(tname)
                            break
                    else:
                        cmprs.append((ncmpr, ncval, nstor, None if tname is None else {tname}))
                isvalid = True
            except s_exc.NoSuchVirt:
                novirts = True
            except s_exc.BadTypeValu:
                badtype = True
            except s_exc.NoSuchCmpr:
                pass

        if not isvalid:
            if badtype:
                mesg = f'Value {s_common.trimText(repr(valu))} is not valid for any types supported by {self.name}.'
                raise s_exc.BadTypeValu(name=self.name, valu=valu, cmpr=cmpr, mesg=mesg)
            elif novirts:
                mesg = f'Virtual prop {virt} is not valid for any types supported by {self.name}.'
                raise s_exc.NoSuchVirt.init(virt, self, mesg=mesg)
            else:
                mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
                raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        retn = []
        for (ncmpr, ncval, stortype, tnames) in cmprs:
            stortype |= s_layer.STOR_FLAG_POLY
            if tnames is not None:
                retn.append((ncmpr, (ncval, tuple(tnames)), stortype))
            else:
                retn.append((ncmpr, ncval, stortype))

        return tuple(retn)

    async def norm(self, valu, view=None):
        vtyp = type(valu)

        if vtyp in (s_node.Node, s_node.RuntNode):
            return await self._normStormNode(valu, view=view)

        if vtyp in (s_stormtypes.NodeRef, s_stormtypes.Valu):
            return await self._normStormValu(valu, view=view)

        if vtyp is s_stormtypes.Query:
            return await self._normStormQuery(valu, view=view)

        if vtyp is dict and (asname := valu.get('$as', s_common.novalu)) is not s_common.novalu:
            return await self._normDictAs(asname, valu, view=view)

        if self.defaulttypes is not None:
            for typename in self.defaulttypes:
                tobj = self.modl.type(typename)
                form = self.modl.form(typename)

                if form is not None and form.locked:
                    continue

                if tobj.locked:
                    continue

                try:
                    norm, typeinfo = await tobj.norm(valu, view=view)

                    if view is None:
                        view = False
                        if (runt := s_scope.get('runt')) is not None:
                            view = runt.view

                    return await self._packFormNorm(typename, norm, typeinfo, view)

                except s_exc.BadTypeValu:
                    if len(self.defaulttypes) > 1:
                        continue
                    raise

        if vtyp is dict:
            mesg = f'Dictionary guid constructor for {self.name} requires a "$as" key naming the form to construct.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)

        raise s_exc.BadTypeValu(name=self.name, mesg=f'no norm for type: {vtyp}.')

    async def _normDictAs(self, asname, valu, view=None):

        if not isinstance(asname, str):
            mesg = f'Dictionary guid constructor "$as" must be a form name string for {self.name}.'
            raise s_exc.BadTypeValu(name=self.name, valu=asname, mesg=mesg)

        form = self.modl.form(asname)
        if form is None or not isinstance(form.type, Guid):
            mesg = f'Dictionary guid constructor "$as" value {asname} is not a guid form.'
            raise s_exc.BadTypeValu(name=self.name, valu=asname, mesg=mesg)

        if not self.formfilter(form):
            self._raiseBadTypeValu(asname)

        norm, typeinfo = await form.type.norm(valu, view=view)

        return await self._packFormNorm(asname, norm, typeinfo, view)

    async def _packFormNorm(self, typename, norm, typeinfo, view):

        form = self.modl.form(typename)

        exists = False
        if view and form is not None:
            for cform in self.modl.getChildForms(typename):
                if await view.getNodeByNdef((cform, norm)) is not None:
                    typename = cform
                    exists = True
                    break

        info = {}

        if not exists and form is not None:
            info['adds'] = ((typename, norm, typeinfo),)

        if (subs := typeinfo.get('subs')) is not None:
            info['subs'] = subs

        if (virts := typeinfo.get('virts')) is not None:
            info['virts'] = dict(virts)

        return (typename, norm), info

    async def _normStormNode(self, valu, view=None):

        if not self.formfilter(valu.form):
            self._raiseBadTypeValu(valu.form.name)

        if valu.form.locked or valu.form.type.locked:
            formname = valu.form.name
            raise s_exc.IsDeprLocked(mesg=f'Value of form {formname} is locked due to deprecation.', form=formname)

        return valu.ndef, {'skipadd': True, 'virts': valu.valuvirts()}

    async def _normStormValu(self, valu, view=None):

        typename = valu.valu[0]
        tobj = self.modl.type(typename)
        form = self.modl.form(typename)

        if not self.typefilter(tobj) and (form is None or not self.formfilter(form)):
            self._raiseBadTypeValu(typename)

        if tobj.locked or (form is not None and form.locked):
            raise s_exc.IsDeprLocked(mesg=f'Value of type {typename} is locked due to deprecation.', type=typename)

        if form is not None:
            if valu.exists:
                return valu.valu, {'skipadd': True, 'virts': valu.virts}
            elif view is not None and await view.getNodeByNdef(valu.valu) is not None:
                valu.exists = True
                return valu.valu, {'skipadd': True, 'virts': valu.virts}

        norm, typeinfo = await tobj.norm(valu.valu[1], view=view)

        info = {}
        if form is not None:
            info['adds'] = ((typename, norm, typeinfo),)

        if (virts := typeinfo.get('virts')) is not None:
            info['virts'] = dict(virts)

        return (typename, norm), info

    async def normFromTypedValu(self, valu, view=None):
        '''
        Normalize a (typename, value) pair as produced by Node.pack().
        '''
        if not (type(valu) in (tuple, list) and len(valu) == 2 and isinstance(valu[0], str)):
            mesg = 'Value must be a (typename, value) tuple.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg, valu=valu)

        typename, pval = valu

        if (tobj := self.modl.type(typename)) is None:
            mesg = f'No such type for value: {typename}.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg, type=typename)

        form = self.modl.form(typename)

        if not self.typefilter(tobj) and (form is None or not self.formfilter(form)):
            self._raiseBadTypeValu(typename)

        if tobj.locked or (form is not None and form.locked):
            raise s_exc.IsDeprLocked(mesg=f'Value of type {typename} is locked due to deprecation.', type=typename)

        norm, typeinfo = await tobj.norm(pval, view=view)

        info = {}
        if form is not None:
            if view is not None and await view.getNodeByNdef((typename, norm)) is not None:
                info['skipadd'] = True
            else:
                info['adds'] = ((typename, norm, typeinfo),)

        if (virts := typeinfo.get('virts')) is not None:
            info['virts'] = dict(virts)

        return (typename, norm), info

    def merge(self, oldv, newv):
        if oldv is None:  # pragma: no cover
            return newv

        if (typename := oldv[0]) != newv[0]:
            return newv

        tobj = self.modl.type(typename)
        return (typename, tobj.merge(oldv[1], newv[1]))

    def repr(self, norm):
        typename, valu = norm

        if (tobj := self.modl.type(typename)) is None:
            raise s_exc.NoSuchType.init(typename)

        return tobj.repr(valu)

    def reprWithVirts(self, norm, virts=None):
        typename, valu = norm

        if (tobj := self.modl.type(typename)) is None:  # pragma: no cover
            raise s_exc.NoSuchType.init(typename)

        return tobj.reprWithVirts(valu, virts)

    async def tostorm(self, valu, virts=None):
        typename = valu[0]
        if self.modl.form(typename) is not None:
            return s_stormtypes.NodeRef((valu, virts))
        return s_stormtypes.Valu((valu, virts))

class Data(Type):

    ismutable = True

    stortype = s_layer.STOR_TYPE_MSGP

    _opt_defs = (
        ('schema', None),  # type: ignore
    )

    def postTypeInit(self):
        self.validator = None
        schema = self.opts.get('schema')
        if schema is not None:
            self.validator = s_config.getJsValidator(schema)

    async def norm(self, valu, view=None):
        try:
            valu = await s_stormtypes.toprim(valu)
            s_json.reqjsonsafe(valu)
            if self.validator is not None:
                self.validator(valu)
        except (s_exc.MustBeJsonSafe, s_exc.SchemaViolation) as e:
            raise s_exc.BadTypeValu(name=self.name, mesg=f'{e}: {s_common.trimText(repr(valu))}') from None
        byts = s_msgpack.en(valu)
        return s_msgpack.un(byts), {}

class Range(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    _opt_defs = (
        ('type', None),  # type: ignore
    )

    def postTypeInit(self):
        subtype = self.opts.get('type')
        if not(type(subtype) is tuple and len(subtype) == 2):
            raise s_exc.BadTypeDef(self.opts, name=self.name)

        try:
            self.subtype = self.modl.type(subtype[0]).clone(subtype[1])
        except Exception:
            logger.exception('subtype invalid or unavailable')
            raise s_exc.BadTypeDef(self.opts, name=self.name, mesg='subtype invalid or unavailable')

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(tuple, self._normPyTuple)
        self.setNormFunc(list, self._normPyTuple)

    async def _normPyStr(self, valu, view=None):
        valu = valu.split('-', 1)
        return await self._normPyTuple(valu)

    async def _normPyTuple(self, valu, view=None):
        if len(valu) != 2:
            mesg = f'Must be a 2-tuple of type {self.subtype.name}: {s_common.trimText(repr(valu))}'
            raise s_exc.BadTypeValu(numitems=len(valu), name=self.name, mesg=mesg)

        minv, minfo = await self.subtype.norm(valu[0])
        maxv, maxfo = await self.subtype.norm(valu[1])

        if minv > maxv:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='minval cannot be greater than maxval')

        typehash = self.subtype.typehash
        return (minv, maxv), {'subs': {'min': (typehash, minv, minfo), 'max': (typehash, maxv, maxfo)}}

    def repr(self, norm):
        subx = self.subtype.repr(norm[0])
        suby = self.subtype.repr(norm[1])
        return (subx, suby)

class Str(Type):

    stortype = s_layer.STOR_TYPE_UTF8

    _opt_defs = (
        ('enums', None),  # type: ignore
        ('regex', None),
        ('lower', False),
        ('strip', True),
        ('upper', False),
        ('replace', ()),
        ('mapping', None),
        ('onespace', False),
        ('globsuffix', False),
    )

    def repr(self, norm):
        return norm

    def postTypeInit(self):

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bool, self._normPyBool)
        self.setNormFunc(float, self._normPyFloat)
        self.setNormFunc(decimal.Decimal, self._normPyInt)
        self.setNormFunc(s_stormtypes.Number, self._normNumber)

        self.storlifts.update({
            '=': self._storLiftEq,
            '^=': self._storLiftPref,
        })

        self.strtype = self.modl.type('str')

        if self.opts.get('lower') and self.opts.get('upper'):
            mesg = f'Str type ({self.name}) has both lower and upper set.'
            raise s_exc.BadTypeDef(mesg=mesg)

        self.regex = None
        restr = self.opts.get('regex')
        if restr is not None:
            self.regex = regex.compile(restr)

        self.envals = None
        enumstr = self.opts.get('enums')
        if enumstr is not None:
            self.envals = enumstr.split(',')

        self.valumap = self.opts.get('mapping')
        if self.valumap is not None and not isinstance(self.valumap, dict):
            mesg = f'Str type ({self.name}) mapping option must be a dict.'
            raise s_exc.BadTypeDef(mesg=mesg)

    async def _storLiftEq(self, cmpr, valu):

        if isinstance(valu, str) and self.opts.get('globsuffix') and valu.endswith('*'):
            return (
                ('^=', valu[:-1], self.stortype),
            )

        return await self._storLiftNorm(cmpr, valu)

    async def _storLiftRange(self, cmpr, valu):
        minx = await self._normForLift(valu[0])
        maxx = await self._normForLift(valu[1])
        return (
            (cmpr, (minx, maxx), self.stortype),
        )

    async def _normForLift(self, valu):

        # doesnt have to be normable...
        if self.opts.get('lower'):
            valu = valu.lower()
        elif self.opts.get('upper'):
            valu = valu.upper()

        for look, repl in self.opts.get('replace', ()):
            valu = valu.replace(look, repl)

        # Only strip the left side of the string for prefix match
        if self.opts.get('strip'):
            valu = valu.lstrip()

        if self.opts.get('onespace'):
            valu = s_chop.onespace(valu)

        if self.valumap is not None:
            valu = self.valumap.get(valu, valu)

        return valu

    async def _storLiftPref(self, cmpr, valu):
        valu = await self._normForLift(valu)
        return (('^=', valu, self.stortype),)

    async def _storLiftRegx(self, cmpr, valu):
        return ((cmpr, valu, self.stortype),)

    async def _ctorCmprPref(self, valu):
        text = await self._normForLift(str(valu))

        async def cmpr(valu):
            return self.repr(valu).startswith(text)

        return cmpr

    async def _normPyBool(self, valu, view=None):
        return await self._normPyStr(str(valu).lower())

    async def _normPyInt(self, valu, view=None):
        return await self._normPyStr(str(valu))

    async def _normNumber(self, valu, view=None):
        return await self._normPyStr(str(valu))

    async def _normPyFloat(self, valu, view=None):
        deci = s_common.hugectx.create_decimal(str(valu))
        return await self._normPyStr(format(deci, 'f'))

    async def _normPyStr(self, valu, view=None):

        info = {}
        norm = str(valu)

        if self.opts['lower']:
            norm = norm.lower()
        elif self.opts['upper']:
            norm = norm.upper()

        for look, repl in self.opts.get('replace', ()):
            norm = norm.replace(look, repl)

        if self.opts['strip']:
            norm = norm.strip()

        if self.opts['onespace']:
            norm = s_chop.onespace(norm)

        if self.valumap is not None:
            norm = self.valumap.get(norm, norm)

        if self.envals is not None:
            if norm not in self.envals:
                raise s_exc.BadTypeValu(valu=valu, name=self.name, enums=self.info.get('enums'),
                                        mesg='Value not in enums')

        if self.regex is not None:

            match = self.regex.match(norm)
            if match is None:
                raise s_exc.BadTypeValu(name=self.name, valu=valu, regx=self.regex.pattern,
                                        mesg=f'[{valu}] does not match [{self.regex.pattern}]')

            subs = match.groupdict()
            if subs:
                info['subs'] = {k: (self.strtype.typehash, v, {}) for k, v in subs.items()}

        return norm, info

class Text(Str):
    stortype = s_layer.STOR_TYPE_TEXT

    _opt_defs = (
        ('enums', None),  # type: ignore
        ('regex', None),
        ('lower', False),
        ('strip', False),
        ('upper', False),
        ('replace', ()),
        ('mapping', None),
        ('onespace', False),
        ('globsuffix', False),
    )

    async def _ctorCmprEq(self, text):
        norm, info = await self.norm(text)
        norm = norm.lower()

        async def cmpr(valu):
            return norm == valu.lower()
        return cmpr

    async def _ctorCmprNe(self, text):
        norm, info = await self.norm(text)
        norm = norm.lower()

        async def cmpr(valu):
            return norm != valu.lower()
        return cmpr

    async def _ctorCmprPref(self, valu):
        text = str(valu)
        text = text.lower()

        async def cmpr(valu):
            return valu.lower().startswith(text)

        return cmpr

    async def _ctorCmprIn(self, vals):
        norms = [(await self.norm(v))[0].lower() for v in vals]

        async def cmpr(valu):
            return valu.lower() in norms
        return cmpr

    async def _ctorCmprRange(self, vals):

        if not isinstance(vals, (list, tuple)):
            mesg = f'Range comparison requires a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadTypeValu(name=self.name, valu=vals, mesg=mesg)

        if len(vals) != 2:
            mesg = f'Range comparison requires a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadTypeValu(name=self.name, valu=vals, mesg=mesg)

        minv = (await self.norm(vals[0]))[0].lower()
        maxv = (await self.norm(vals[1]))[0].lower()

        async def cmpr(valu):
            return minv <= valu.lower() <= maxv
        return cmpr

class Title(Text):
    '''
    A single line variant of Text which collapses runs of whitespace and
    strips leading/trailing whitespace while preserving case.
    '''
    _opt_defs = (
        ('enums', None),  # type: ignore
        ('regex', None),
        ('lower', False),
        ('strip', True),
        ('upper', False),
        ('replace', ()),
        ('onespace', True),
        ('globsuffix', False),
    )

taxonre = regex.compile('\\w+')
class Taxon(Str):

    def postTypeInit(self):
        Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    async def _normForLift(self, valu):
        return (await self.norm(valu))[0]

    async def _normPyStr(self, valu, view=None):
        valu = valu.lower().strip()
        parts = taxonre.findall(valu)
        valu = '_'.join(parts)
        if len(valu) == 0:
            mesg = 'Each taxon must be non-zero length.'
            raise s_exc.BadTypeValu(mesg=mesg)

        return valu, {}

class Taxonomy(Str):

    def postTypeInit(self):
        Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyList)
        self.setNormFunc(tuple, self._normPyList)
        self.taxon = self.modl.type('taxon')
        self.inttype = self.modl.type('int')

    async def _ctorCmprPref(self, valu):
        norm = await self._normForLift(valu)

        async def cmpr(valu):
            return valu.startswith(norm)

        return cmpr

    async def _normForLift(self, valu):
        norm = (await self.norm(valu))[0]
        if isinstance(valu, str) and not valu.strip().endswith('.'):
            return norm.rstrip('.')
        return norm

    async def _normPyList(self, valu, view=None):

        toknorms = [await self.taxon.norm(v) for v in valu]
        toks = [norm[0] for norm in toknorms]

        norm = '.'.join(toks) + '.'
        subs = pinfo = {}

        while toknorms:
            pnorm, info = toknorms.pop(-1)
            toks.pop(-1)

            pinfo |= {
                'base': (self.taxon.typehash, pnorm, info),
                'depth': (self.inttype.typehash, len(toks), {}),
            }

            if toknorms:
                nextfo = {}
                pinfo['parent'] = (self.typehash, '.'.join(toks) + '.', {'subs': nextfo})
                pinfo = nextfo
                await asyncio.sleep(0)

        return norm, {'subs': subs}

    async def _normPyStr(self, text, view=None):
        return await self._normPyList(text.strip().strip('.').split('.'))

    def repr(self, norm):
        return norm.rstrip('.')

class Tag(Str):

    def postTypeInit(self):
        Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyList)
        self.setNormFunc(tuple, self._normPyList)
        self.tagpart = self.modl.type('syn:tag:part')
        self.inttype = self.modl.type('int')

    async def _normPyList(self, valu, view=None):

        toknorms = [await self.tagpart.norm(v) for v in valu]
        toks = [norm[0] for norm in toknorms]

        norm = '.'.join(toks)
        if not s_grammar.tagre.fullmatch(norm):
            mesg = f'Tag does not match tagre: [{s_grammar.tagre.pattern}]'
            raise s_exc.BadTypeValu(valu=norm, name=self.name, mesg=mesg)

        core = self.modl.core
        if core is not None:
            (ok, mesg) = core.isTagValid(norm)
            if not ok:
                raise s_exc.BadTypeValu(valu=norm, name=self.name, mesg=mesg)

        subs = pinfo = {}

        while toknorms:
            pnorm, info = toknorms.pop(-1)

            pinfo |= {
                'base': (self.tagpart.typehash, pnorm, info),
                'depth': (self.inttype.typehash, len(toknorms), {}),
            }

            if toknorms:
                nextfo = {}
                pinfo['up'] = (self.typehash, '.'.join([norm[0] for norm in toknorms]), {'subs': nextfo})
                pinfo = nextfo
                await asyncio.sleep(0)

        return norm, {'subs': subs, 'toks': toks}

    async def _normPyStr(self, text, view=None):
        toks = text.strip('#').split('.')
        return await self._normPyList(toks)

tagpartre = regex.compile('\\w+')
class TagPart(Str):

    def postTypeInit(self):
        Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    async def _normPyStr(self, valu, view=None):
        valu = valu.lower().strip()
        parts = tagpartre.findall(valu)
        valu = '_'.join(parts)
        if len(valu) == 0:
            mesg = 'Each tag part must be non-zero length.'
            raise s_exc.BadTypeValu(mesg=mesg)

        return valu, {}

speed_dist = {
    'mm': 1,
    'millimeters': 1,
    'k': 1000000,
    'km': 1000000,
    'kilometers': 1000000,
    'nmi': 1852000,
    'in': 25.4,
    'inches': 25.4,
    'ft': 304.8,
    'feet': 304.8,
    'mi': 1609344,
    'miles': 1609344,
}

speed_dura = {
    's': 1,
    'sec': 1,
    'min': 60,
    'minute': 60,
    'h': 3600,
    'hr': 3600,
    'hour': 3600,
}

class Velocity(IntBase):
    oflight = 299792458000
    stortype = s_layer.STOR_TYPE_I64

    _opt_defs = (
        ('relative', False),
    )

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    async def _normPyStr(self, valu, view=None):

        valu = valu.lower().strip()
        if not valu:
            mesg = 'Empty string is not a valid velocity.'
            raise s_exc.BadTypeValu(mesg=mesg)

        nums, offs = s_grammar.nom(valu, 0, cset='-0123456789.')
        if not nums:
            nums = '1'

        base = float(nums)
        if base < 0 and not self.opts.get('relative'):
            mesg = 'Non-relative velocities may not be negative.'
            raise s_exc.BadTypeValu(mesg=mesg)

        unit = valu[offs:].strip()
        if not unit:
            return int(base), {}

        if unit.find('/') != -1:
            dist, dura = unit.split('/', 1)
            distmod = speed_dist.get(dist)
            if distmod is None:
                mesg = f'Unrecognized distance type: {dist}.'
                raise s_exc.BadTypeValu(mesg=mesg)

            duramod = speed_dura.get(dura)
            if duramod is None:
                mesg = f'Unrecognized duration type: {dura}.'
                raise s_exc.BadTypeValu(mesg=mesg)

            norm = int((base * distmod) / duramod)
            return norm, {}

        if unit == 'mph':
            norm = int((base * 1609344) / 3600)
            return norm, {}

        if unit == 'kph':
            norm = int((base * 1000000) / 3600)
            return norm, {}

        if unit in ('knots', 'kts'):
            norm = int((base * 1852000) / 3600)
            return norm, {}

        if unit == 'c':
            return int(base * self.oflight), {}

        mesg = f'Unknown velocity unit: {unit}.'
        raise s_exc.BadTypeValu(mesg=mesg)

    async def _normPyInt(self, valu, view=None):
        if valu < 0 and not self.opts.get('relative'):
            mesg = 'Non-relative velocities may not be negative.'
            raise s_exc.BadTypeValu(mesg=mesg)
        return valu, {}

class Duration(IntBase):

    stortype = s_layer.STOR_TYPE_U64

    _opt_defs = (
        ('signed', False),
        ('precision', 'microsecond'),
    )

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

        self.unkdura = 0xffffffffffffffff
        self.futdura = 0xfffffffffffffffe

        self.setExprFunc('+', 'duration', self._exprAddDura)
        self.setExprFunc('-', 'duration', self._exprSubDura)
        self.setExprFunc('+', 'time', self._exprAddTime)
        self.setExprFunc('*', 'int', self._exprMulInt)
        self.setExprFunc('*', 'int', self._exprMulInt, reverse=True)

        # a bare string operand is normed as a duration, or as a time when only
        # that interpretation is valid (e.g. (:duration + "2020") yields a time)
        self.setExprFunc('+', 'str', self._exprAddStr)
        self.setExprFunc('-', 'str', self._exprSubStr)
        self.setExprFunc('+', 'str', self._exprAddStr, reverse=True)

        precstr = self.opts.get('precision')
        self.precision = s_time.durprecisions.get(precstr)

        if self.precision is None:
            mesg = f'Duration type ({self.name}) has invalid precision: {precstr}.'
            raise s_exc.BadTypeDef(mesg=mesg)

    def _snap(self, valu):
        if self.precision > 1 and valu not in (self.unkdura, self.futdura):
            valu -= valu % self.precision

        return valu

    async def _exprAddDura(self, valu, othr):
        return ('duration', valu + othr)

    async def _exprSubDura(self, valu, othr):
        return ('duration', valu - othr)

    async def _exprAddTime(self, valu, othr):
        return ('time', valu + othr)

    async def _exprMulInt(self, valu, othr):
        return ('duration', valu * othr)

    async def _exprAddStr(self, valu, othr):
        # a string operand may be a time (yielding a time) or a duration
        # (yielding a duration). Prefer the time interpretation: an ambiguous
        # numeric string like "2020" is far more useful as a year than as a
        # count of microseconds.
        try:
            timev, _ = await self.modl.type('time').norm(othr)
        except s_exc.BadTypeValu:
            durv, _ = await self.norm(othr)
            return await self._exprAddDura(valu, durv)

        return await self._exprAddTime(valu, timev)

    async def _exprSubStr(self, valu, othr):
        # subtracting a time from a duration is not meaningful, so a string
        # operand is only normed as a duration
        durv, _ = await self.norm(othr)
        return await self._exprSubDura(valu, durv)

    async def _normPyInt(self, valu, view=None):
        if valu < 0 or valu > self.unkdura:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Duration value is outside of valid range.')

        return self._snap(valu), {}

    async def _normPyStr(self, text, view=None):

        text = text.strip()
        if not text:
            mesg = 'Duration string must have non-zero length.'
            raise s_exc.BadTypeValu(mesg=mesg)

        if text == '?':
            return self.unkdura, {}

        if text == '*':
            return self.futdura, {}

        dura = 0

        try:

            if text.find('D') != -1:
                daystext, text = text.split('D', 1)
                dura += int(daystext.strip(), 0) * s_time.oneday
                text = text.strip()

            if text:
                if text.find(':') != -1:
                    parts = text.split(':')
                    if len(parts) == 2:
                        dura += int(parts[0].strip()) * s_time.onemin
                        dura += int(float(parts[1].strip()) * s_time.onesec)
                    elif len(parts) == 3:
                        dura += int(parts[0].strip()) * s_time.onehour
                        dura += int(parts[1].strip()) * s_time.onemin
                        dura += int(float(parts[2].strip()) * s_time.onesec)
                    else:
                        mesg = 'Invalid number of : characters for duration.'
                        raise s_exc.BadTypeValu(mesg=mesg)
                else:
                    dura += int(float(text) * s_time.onesec)

        except ValueError:
            mesg = f'Invalid numeric value in duration: {text}.'
            raise s_exc.BadTypeValu(mesg=mesg) from None

        if dura < 0 or dura > self.unkdura:
            raise s_exc.BadTypeValu(name=self.name, valu=dura, mesg='Duration value is outside of valid range.')

        return self._snap(dura), {}

    def repr(self, valu):

        if valu == self.futdura:
            return '*'
        elif valu == self.unkdura:
            return '?'

        days, rem = divmod(valu, s_time.oneday)
        hours, rem = divmod(rem, s_time.onehour)
        minutes, rem = divmod(rem, s_time.onemin)
        seconds, micros = divmod(rem, s_time.onesec)

        retn = ''
        if days:
            retn += f'{days}D '

        mstr = ''
        if micros > 0:
            mstr = f'.{micros:06d}'.rstrip('0')

        retn += f'{hours:02}:{minutes:02}:{seconds:02}{mstr}'
        return retn

class Time(IntBase):

    stortype = s_layer.STOR_TYPE_TIME

    _opt_defs = (
        ('ismin', False),  # type: ignore
        ('ismax', False),
        ('maxfill', False),
        ('precision', 'microsecond'),
    )

    def postTypeInit(self):

        self.unksize = 0x7fffffffffffffff
        self.futsize = 0x7ffffffffffffffe
        self.maxsize = 253402300799999999  # -9999/12/31 23:59:59.999999
        self.minsize = -377705116800000000 # -9999/01/01 00:00:00.000000

        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(decimal.Decimal, self._normPyDecimal)
        self.setNormFunc(s_stormtypes.Number, self._normNumber)

        self.setCmprCtor('@=', self._ctorCmprAt)

        self.setExprFunc('-', 'time', self._exprSubTime)
        self.setExprFunc('+', 'duration', self._exprAddDura)
        self.setExprFunc('-', 'duration', self._exprSubDura)

        # a bare string operand on a time is only meaningful as a duration, so
        # norm it as such (e.g. (:time + "1D") yields a new time)
        self.setExprFunc('+', 'str', self._exprAddStr)
        self.setExprFunc('-', 'str', self._exprSubStr)
        self.setExprFunc('+', 'str', self._exprAddStr, reverse=True)

        self.ismin = self.opts.get('ismin')
        self.ismax = self.opts.get('ismax')

        if self.ismin and self.ismax:
            mesg = f'Time type ({self.name}) has both ismin and ismax set.'
            raise s_exc.BadTypeDef(mesg=mesg)

        precstr = self.opts.get('precision')
        self.prec = s_time.precisions.get(precstr)

        if self.prec is None:
            mesg = f'Time type ({self.name}) has invalid precision: {precstr}.'
            raise s_exc.BadTypeDef(mesg=mesg)

        self.maxfill = self.opts.get('maxfill')
        self.prectype = self.modl.type('timeprecision')
        self.precfunc = s_time.precfuncs.get(self.prec)

        self.storlifts.update({
            '@=': self._liftByIval,
        })

        self.virts |= {
            'precision': (self.prectype, self._getPrec),
        }

        self.virtstor |= {
            'precision': self._storVirtPrec,
        }

        if self.ismin:
            self.stortype = s_layer.STOR_TYPE_MINTIME
        elif self.ismax:
            self.stortype = s_layer.STOR_TYPE_MAXTIME

    async def _exprSubTime(self, valu, othr):
        return ('duration', valu - othr)

    async def _exprAddDura(self, valu, othr):
        return ('time', valu + othr)

    async def _exprSubDura(self, valu, othr):
        return ('time', valu - othr)

    async def _exprAddStr(self, valu, othr):
        durv, _ = await self.modl.type('duration').norm(othr)
        return await self._exprAddDura(valu, durv)

    async def _exprSubStr(self, valu, othr):
        # a string operand may be another time (yielding a duration) or a
        # duration (yielding a time). Prefer the time interpretation: an
        # ambiguous numeric string like "2020" is far more useful as a year
        # than as a count of microseconds.
        try:
            timev, _ = await self.norm(othr)
        except s_exc.BadTypeValu:
            durv, _ = await self.modl.type('duration').norm(othr)
            return await self._exprSubDura(valu, durv)

        return await self._exprSubTime(valu, timev)

    async def _liftByIval(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            norm, info = await self.norm(valu)
            return (
                ('=', norm, self.stortype),
            )

        ticktock = (await self.getTickTock(valu))[:2]
        return (
            (cmpr, ticktock, self.stortype),
        )

    async def _storLiftRange(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            mesg = f'Range value must be a list: {valu!r}'
            raise s_exc.BadTypeValu(mesg=mesg)

        ticktock = (await self.getTickTock(valu))[:2]

        return (
            (cmpr, ticktock, self.stortype),
        )

    def _getPrec(self, valu):
        if (virts := valu[2]) is None or (vval := virts.get('precision')) is None:
            return self.prec
        return vval[0]

    async def _storVirtPrec(self, valu, newprec, oldvirts=None):
        if valu is None:
            mesg = 'Cannot set precision on an empty time value.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)

        prec = (await self.prectype.norm(newprec))[0]
        valu, norminfo = await self._normPyInt(valu, prec=prec)
        return valu, norminfo

    async def _ctorCmprAt(self, valu):
        return await self.modl.types.get('ival')._ctorCmprAt(valu)

    async def _normPyStr(self, valu, prec=None, view=None):

        valu = valu.strip().lower()
        if valu == 'now':
            return await self._normPyInt(s_common.now(), prec=prec)

        # an unspecififed time in the future...
        if valu == '?':
            return self.unksize, {}

        if valu == '*':
            return self.futsize, {}

        # parse timezone
        valu, base = s_time.parsetz(valu)

        # we need to be pretty sure this is meant for us, otherwise it might
        # just be a slightly messy time parse
        unitcheck = [u for u in s_time.timeunits.keys() if u in valu]
        if unitcheck and ('-' in valu or '+' in valu):
            splitter = '+'
            if '-' in valu:
                splitter = '-'

            bgn, end = valu.split(splitter, 1)
            delt = s_time.delta(splitter + end)
            if bgn:
                bgn = (await self._normPyStr(bgn, prec=prec))[0] + base
            else:
                bgn = s_common.now()

            return await self._normPyInt(delt + bgn, prec=prec)

        valu, strprec = s_time.parseprec(valu, base=base, chop=True)
        if prec is None:
            prec = strprec

        return await self._normPyInt(valu, prec=prec)

    async def _normPyInt(self, valu, prec=None, view=None):
        if valu in (self.futsize, self.unksize):
            return valu, {}

        if valu > self.maxsize or valu < self.minsize:
            mesg = f'Time outside of allowed range [{self.minsize} to {self.maxsize}], got {valu}'
            raise s_exc.BadTypeValu(mesg=mesg, valu=valu, prec=prec, maxfill=self.maxfill, name=self.name)

        if prec is None or prec == self.prec:
            valu = self.precfunc(valu, maxfill=self.maxfill)
            return valu, {}

        if (precfunc := s_time.precfuncs.get(prec)) is None:
            mesg = f'Invalid time precision specifier {prec}'
            raise s_exc.BadTypeValu(mesg=mesg, valu=valu, prec=prec, name=self.name)

        valu = precfunc(valu, maxfill=self.maxfill)
        info = {}
        self.setVirtInfo(info, 'precision', prec, self.prectype)
        return valu, info

    async def _normPyDecimal(self, valu, prec=None, view=None):
        return await self._normPyInt(int(valu), prec=prec)

    async def _normNumber(self, valu, prec=None, view=None):
        return await self._normPyInt(int(valu.valu), prec=prec)

    async def _normStormValu(self, valu, prec=None, view=None):
        tobj = self.modl.type(valu.valu[0])
        if tobj is not None and tobj.typehash == self.typehash:
            info = {}
            if valu.virts is not None:
                info['virts'] = valu.virts
            return valu.valu[1], info
        return await self.norm(valu.valu[1], prec=prec)

    async def _normStormNodeRef(self, nref, prec=None, view=None):
        return await self.norm(nref.valu[1], prec=prec)

    async def norm(self, valu, prec=None, view=None):
        func = self._type_norms.get(type(valu))
        if func is None:
            raise s_exc.BadTypeValu(name=self.name, mesg='no norm for type: %r.' % (type(valu),))

        return await func(valu, prec=prec, view=view)

    def merge(self, oldv, newv):

        if oldv == self.unksize:
            return newv

        if self.ismin:
            return min(oldv, newv)

        if self.ismax:
            return max(oldv, newv)

        return newv

    def repr(self, valu):

        if valu == self.futsize:
            return '*'
        elif valu == self.unksize:
            return '?'

        return s_time.repr(valu)

    async def _getLiftValu(self, valu, relto=None, prec=None):

        if isinstance(valu, str):

            lowr = valu.strip().lower()
            if not lowr:
                mesg = f'Invalid time provided, got [{valu}]'
                raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=valu)

            if lowr == 'now':
                return s_common.now(), {}

            if lowr[0] in ('-', '+'):

                delt = s_time.delta(lowr)
                if relto is None:
                    relto = s_common.now()

                return await self._normPyInt(delt + relto, prec=prec)

        return await self.norm(valu, prec=prec)

    def _getTickPrec(self, valu):
        if virts := valu.get('virts'):
            if precision := virts.get('precision'):
                return precision[0]

    async def getTickTock(self, vals, prec=None):
        '''
        Get a tick, tock time pair.

        Args:
            vals (list): A pair of values to norm.
            prec (int): An optional time precision value.

        Returns:
            (int, int, int): A ordered 3 tuple of integers.
        '''
        if len(vals) not in (2, 3):
            mesg = 'Time range must have a length of 2 or 3: %r' % (vals,)
            raise s_exc.BadTypeValu(mesg=mesg)

        val0, val1 = vals[:2]

        try:
            _tick, tickinfo = await self._getLiftValu(val0, prec=prec)
        except ValueError:
            mesg = f'Unable to process the value for val0 in _getLiftValu, got {val0}'
            raise s_exc.BadTypeValu(name=self.name, valu=val0,
                                    mesg=mesg) from None

        sortval = False
        if isinstance(val1, str):
            if val1.startswith(('+-', '-+')):
                sortval = True
                delt = s_time.delta(val1[2:])
                # order matters
                _tock = _tick + delt
                _tick = _tick - delt
                tockinfo = {}
            elif val1.startswith('-'):
                sortval = True
                _tock, tockinfo = await self._getLiftValu(val1, relto=_tick, prec=prec)
            else:
                _tock, tockinfo = await self._getLiftValu(val1, relto=_tick, prec=prec)
        else:
            _tock, tockinfo = await self._getLiftValu(val1, relto=_tick, prec=prec)

        tickprec = self._getTickPrec(tickinfo)
        tockprec = self._getTickPrec(tockinfo)
        precs = [x for x in (tickprec, tockprec, prec) if x is not None]
        if precs:
            prec = max(precs)

        if sortval and _tick >= _tock:
            tick = min(_tick, _tock)
            tock = max(_tick, _tock)
            return tick, tock, prec

        return _tick, _tock, prec

    async def _ctorCmprRange(self, vals):
        '''
        Override default range= handler to account for relative computation.
        '''

        if not isinstance(vals, (list, tuple)):
            mesg = f'Range comparison requires a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadTypeValu(name=self.name, valu=vals, mesg=mesg)

        if len(vals) != 2:
            mesg = f'Range comparison requires a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadTypeValu(name=self.name, valu=vals, mesg=mesg)

        tick, tock, prec = await self.getTickTock(vals)

        if tick > tock:
            # User input has requested a nullset
            async def cmpr(valu):
                return False

            return cmpr

        async def cmpr(valu):
            return tick <= valu <= tock

        return cmpr

    async def _ctorCmprLt(self, text):

        if isinstance(text, str):
            strip = text.strip()
            if strip.endswith('*'):
                tick, tock = s_time.wildrange(strip[:-1])
                async def cmpr(valu):
                    return valu < tock
                return cmpr

        return await IntBase._ctorCmprLt(self, text)

    async def _ctorCmprLe(self, text):

        if isinstance(text, str):
            strip = text.strip()
            if strip.endswith('*'):
                tick, tock = s_time.wildrange(strip[:-1])
                async def cmpr(valu):
                    return valu <= tock
                return cmpr

        return await IntBase._ctorCmprLe(self, text)

    async def _ctorCmprEq(self, text):

        if isinstance(text, str):
            strip = text.strip()
            if strip.endswith('*'):
                tick, tock = s_time.wildrange(strip[:-1])
                async def cmpr(valu):
                    return valu >= tick and valu < tock
                return cmpr

        norm, info = await self.norm(text)

        async def cmpr(valu):
            return norm == valu

        return cmpr

    async def _storLiftNorm(self, cmpr, valu):

        if isinstance(valu, str):
            text = valu.strip()
            if text.endswith('*'):
                if cmpr == '=':
                    tick, tock = s_time.wildrange(text[:-1])
                    return (
                        ('range=', (tick, tock), self.stortype),
                    )

                if cmpr == '<':
                    tick, tock = s_time.wildrange(text[:-1])
                    return (
                        ('<', tock, self.stortype),
                    )

                if cmpr == '<=':
                    tick, tock = s_time.wildrange(text[:-1])
                    return (
                        ('<=', tock, self.stortype),
                    )

        return await IntBase._storLiftNorm(self, cmpr, valu)

class TimePrecision(IntBase):

    stortype = s_layer.STOR_TYPE_U8

    _opt_defs = (
        ('signed', False),
    )

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    async def _normPyStr(self, valu, view=None):

        if (ival := s_common.intify(valu)) is not None:
            if ival not in s_time.preclookup:
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Invalid time precision value.')
            return int(ival), {}

        sval = valu.lower().strip()
        if (retn := s_time.precisions.get(sval)) is not None:
            return retn, {}
        raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Invalid time precision value.')

    async def _normPyInt(self, valu, view=None):
        valu = int(valu)
        if valu not in s_time.preclookup:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Invalid time precision value.')
        return valu, {}

    def repr(self, valu):
        if (rval := s_time.preclookup.get(valu)) is not None:
            return rval
        raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Invalid time precision value.')
