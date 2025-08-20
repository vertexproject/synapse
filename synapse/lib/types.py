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
import synapse.lib.stormtypes as s_stormtypes

import synapse.lib.scope as s_scope

logger = logging.getLogger(__name__)

class Type:

    _opt_defs = ()
    stortype: int = None  # type: ignore

    # a fast-access way to determine if the type is an array
    # ( due to hot-loop needs in the storm runtime )
    isarray = False

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

        self.opts = dict(self._opt_defs)
        self.opts.update(opts)

        self._type_norms = {}   # python type to norm function map str: _norm_str
        self._cmpr_ctors = {}   # cmpr string to filter function constructor map
        self._cmpr_ctor_lift = {}  # if set, create a cmpr which is passed along with indx ops

        self.virts = {}
        self.virtindx = {
            'created': 'created',
            'updated': 'updated'
        }
        self.virtstor = {}

        self.pivs = {}

        self.setCmprCtor('=', self._ctorCmprEq)
        self.setCmprCtor('!=', self._ctorCmprNe)
        self.setCmprCtor('~=', self._ctorCmprRe)
        self.setCmprCtor('^=', self._ctorCmprPref)
        self.setCmprCtor('in=', self._ctorCmprIn)
        self.setCmprCtor('range=', self._ctorCmprRange)

        self.setNormFunc(s_node.Node, self._normStormNode)

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

            normopts = dict(self.opts)
            for optn, valu in normopts.items():
                if isinstance(valu, float):
                    normopts[optn] = str(valu)

            ctor = '.'.join([self.__class__.__module__, self.__class__.__qualname__])
            self.typehash = sys.intern(s_common.guid((ctor, s_common.flatten(normopts))))

    def _initType(self):
        inits = [self.postTypeInit]

        subof = self.subof
        while subof is not None:
            styp = self.modl.type(subof)
            inits.append(styp.postTypeInit)
            subof = styp.subof

        for init in inits[::-1]:
            init()

        normopts = dict(self.opts)
        for optn, valu in normopts.items():
            if isinstance(valu, float):
                normopts[optn] = str(valu)

        ctor = '.'.join([self.__class__.__module__, self.__class__.__qualname__])
        self.typehash = sys.intern(s_common.guid((ctor, s_common.flatten(normopts))))

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

    async def getStorCmprs(self, cmpr, valu, virts=None):

        if virts:
            return await self.getVirtType(virts).getStorCmprs(cmpr, valu)

        func = self.storlifts.get(cmpr)
        if func is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        return await func(cmpr, valu)

    def getVirtIndx(self, virts):
        name = virts[0]
        if len(virts) > 1:
            if (virt := self.virts.get(name)) is None:
                raise s_exc.NoSuchVirt.init(name, self)
            return virt[0].getVirtIndx(virts[1:])

        indx = self.virtindx.get(name, s_common.novalu)
        if indx is s_common.novalu:
            raise s_exc.NoSuchVirt.init(name, self)

        return indx

    def getVirtType(self, virts):
        name = virts[0]
        if (virt := self.virts.get(name)) is None:
            raise s_exc.NoSuchVirt.init(name, self)

        if len(virts) > 1:
            return virt[0].getVirtType(virts[1:])
        return virt[0]

    def getVirtGetr(self, virts):
        name = virts[0]
        if (virt := self.virts.get(name)) is None:
            raise s_exc.NoSuchVirt.init(name, self)

        if len(virts) > 1:
            return (virt[1],) + virt[0].getVirtGetr(virts[1:])
        return (virt[1],)

    def getVirtInfo(self, virts):
        name = virts[0]
        if (virt := self.virts.get(name)) is None:
            raise s_exc.NoSuchVirt.init(name, self)

        if len(virts) > 1:
            vinfo = virt[0].getVirtInfo(virts[1:])
            return vinfo[0], (virt[1],) + vinfo[1]
        return virt[0], (virt[1],)

    async def normVirt(self, name, valu, newvirt):
        func = self.virtstor.get(name, s_common.novalu)
        if func is s_common.novalu:
            mesg = f'No editable virtual prop named {name} on type {self.name}.'
            raise s_exc.NoSuchVirt.init(name, self, mesg=mesg)

        return await func(valu, newvirt)

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
            props['subof'] = self.subof

        return (('syn:type', self.name), {
            'props': props,
        })

    def getCompOffs(self, name):
        '''
        If this type is a compound, return the field offset for the given
        property name or None.
        '''
        return None

    async def _normStormNode(self, node, view=None):
        return await self.norm(node.ndef[1], view=view)

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
            raise s_exc.BadCmprValu(name=self.name, valu=vals, cmpr='range=')

        if len(vals) != 2:
            raise s_exc.BadCmprValu(name=self.name, valu=vals, cmpr='range=')

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

        return await func(valu, view=None)

    def repr(self, norm):
        '''
        Return a printable representation for the value.
        This may return a string or a tuple of values for display purposes.
        '''
        return str(norm)

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

    def postTypeInit(self):

        self.isuniq = self.opts.get('uniq', False)
        self.issorted = self.opts.get('sorted', False)
        self.splitstr = self.opts.get('split', None)

        typename = self.opts.get('type')
        if typename is None:
            mesg = 'Array type requires type= option.'
            raise s_exc.BadTypeDef(mesg=mesg)

        typeopts = self.opts.get('typeopts', {})

        basetype = self.modl.type(typename)
        if basetype is None:
            mesg = f'Array type ({self.name}) based on unknown type: {typename}.'
            raise s_exc.BadTypeDef(mesg=mesg)

        self.arraytype = basetype.clone(typeopts)
        self.arraytypehash = self.arraytype.typehash

        if isinstance(self.arraytype, Array):
            mesg = 'Array type of array values is not (yet) supported.'
            raise s_exc.BadTypeDef(mesg)

        if self.arraytype.deprecated:
            mesg = f'The Array type {self.name} is based on a deprecated type {self.arraytype.name} type which ' \
                   f'which will be removed in 4.0.0'
            logger.warning(mesg)

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.stortype = s_layer.STOR_FLAG_ARRAY | self.arraytype.stortype

        self.inttype = self.modl.type('int')

        self.virts |= {
            'size': (self.inttype, self._getSize),
        }

        self.virtlifts = {
            'size': {'range=': self._storLiftSizeRange}
        }

        for oper in ('=', '<', '>', '<=', '>='):
            self.virtlifts['size'][oper] = self._storLiftSize

    async def getStorCmprs(self, cmpr, valu, virts=None):
        if virts:
            lifts = self.virtlifts
            for virt in virts:
                if (lifts := lifts.get(virt)) is None:
                    raise s_exc.NoSuchVirt.init(virt, self)
        else:
            lifts = self.storlifts

        if (func := lifts.get(cmpr)) is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        return await func(cmpr, valu)

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

    async def _normPyStr(self, text, view=None):
        if self.splitstr is None:
            mesg = f'{self.name} type has no split-char defined.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)
        parts = [p.strip() for p in text.split(self.splitstr)]
        return await self._normPyTuple(parts, view=view)

    async def _normPyTuple(self, valu, view=None):

        adds = []
        norms = []
        virts = {}

        form = self.modl.form(self.arraytype.name)

        for item in valu:
            norm, info = await self.arraytype.norm(item, view=view)
            adds.extend(info.get('adds', ()))
            if form is not None:
                adds.append((form.name, norm, info))
            norms.append(norm)

            if (virt := info.get('virts')) is not None:
                virts[norm] = virt

        if self.isuniq:

            uniqs = []
            uniqhas = set()

            for n in norms:
                if n in uniqhas:
                    continue
                uniqhas.add(n)
                uniqs.append(n)

            norms = tuple(uniqs)

        if self.issorted:
            norms = tuple(sorted(norms))

        norminfo = {'adds': adds}

        if virts:
            realvirts = {}

            for norm in norms:
                if (virt := virts.get(norm)) is not None:
                    for vkey, (vval, vtyp) in virt.items():
                        if (curv := realvirts.get(vkey)) is not None:
                            curv[0].append(vval)
                        else:
                            realvirts[vkey] = ([vval], vtyp | s_layer.STOR_FLAG_ARRAY)

            norminfo['virts'] = realvirts

        return tuple(norms), norminfo

    def repr(self, valu):
        rval = [self.arraytype.repr(v) for v in valu]
        if self.splitstr:
            rval = self.splitstr.join(rval)
        return rval

class Comp(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    def getCompOffs(self, name):
        return self.fieldoffs.get(name)

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.sepr = self.opts.get('sepr')
        if self.sepr is not None:
            self.setNormFunc(str, self._normPyStr)

        fields = self.opts.get('fields', ())

        # calc and save field offsets...
        self.fieldoffs = {n: i for (i, (n, t)) in enumerate(fields)}

        self.tcache = FieldHelper(self.modl, self.name, fields)

    async def _normPyTuple(self, valu, view=None):

        fields = self.opts.get('fields')
        if len(fields) != len(valu):
            raise s_exc.BadTypeValu(name=self.name, fields=fields, numitems=len(valu),
                                    mesg=f'invalid number of fields given for norming: {s_common.trimText(repr(valu))}')

        subs = {}
        adds = []
        norms = []

        for i, (name, _) in enumerate(fields):

            _type = self.tcache[name]

            norm, info = await _type.norm(valu[i], view=view)

            subs[name] = norm
            norms.append(norm)

            for k, v in info.get('subs', {}).items():
                subs[f'{name}:{k}'] = v

            typeform = self.modl.form(_type.name)
            if typeform is not None:
                adds.append((typeform.name, norm, info))

            adds.extend(info.get('adds', ()))

        norm = tuple(norms)
        return norm, {'subs': subs, 'adds': adds}

    async def _normPyStr(self, text, view=None):
        return await self._normPyTuple(text.split(self.sepr), view=view)

    def repr(self, valu):

        vals = []
        fields = self.opts.get('fields')

        for valu, (name, _) in zip(valu, fields):
            rval = self.tcache[name].repr(valu)
            vals.append(rval)

        if self.sepr is not None:
            return self.sepr.join(vals)

        return tuple(vals)

class FieldHelper(collections.defaultdict):
    '''
    Helper for Comp types. Performs Type lookup/creation upon first use.
    '''
    def __init__(self, modl, tname, fields):
        collections.defaultdict.__init__(self)
        self.modl = modl
        self.tname = tname
        self.fields = {name: tname for name, tname in fields}

    def __missing__(self, key):
        val = self.fields.get(key)
        if not val:
            raise s_exc.BadTypeDef(valu=key, mesg='unconfigured field requested')
        if isinstance(val, str):
            _type = self.modl.type(val)
            if not _type:
                raise s_exc.BadTypeDef(valu=val, mesg='type is not present in datamodel')
        else:
            # val is a type, opts pair
            tname, opts = val
            basetype = self.modl.type(tname)
            if not basetype:
                raise s_exc.BadTypeDef(valu=val, mesg='type is not present in datamodel')
            _type = basetype.clone(opts)
        if _type.deprecated:
            mesg = f'The type {self.tname} field {key} uses a deprecated ' \
                   f'type {_type.name} which will removed in 4.0.0'
            logger.warning(mesg)
        self.setdefault(key, _type)
        return _type

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

        props = valu.pop('$props', {})
        trycast = valu.pop('$try', False)

        if not valu:
            mesg = f'No values provided for form {form.full}'
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
            props = await self._normProps(form, props, view, trycast=tryprops)

        guid, exists = await self._getGuidByNorms(form, norms, view)

        subinfo = {}
        addinfo = []

        if not exists:
            props |= norms

        if props:
            for name, (prop, norm, info) in props.items():
                subinfo[name] = norm
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

    async def _normProps(self, form, props, view, trycast=False):

        norms = {}

        for name, valu in list(props.items()):
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

        return norms

    async def _getGuidByNorms(self, form, norms, view):

        proplist = []
        for name, info in norms.items():
            proplist.append((name, info[1]))

        # check first for an exact match via our same deconf strategy
        proplist.sort()
        guid = s_common.guid(proplist)

        if not view:
            return guid, False

        node = await view.getNodeByNdef((form.full, guid))
        if node is not None:

            # ensure we still match the property deconf criteria
            for (prop, norm, info) in norms.values():
                if not self._filtByPropAlts(node, prop, norm):
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
        async for node in view.nodesByPropAlts(prop, '=', norm, norm=False):
            await asyncio.sleep(0)

            # filter on the remaining props/alts
            for count, prop, norm in counts[1:]:
                if not self._filtByPropAlts(node, prop, norm):
                    break
            else:
                return node.valu(), True

        return guid, False

    def _filtByPropAlts(self, node, prop, valu):
        # valu must be normalized in advance
        proptype = prop.type
        for prop in prop.getAlts():
            if prop.type.isarray and prop.type.arraytype == proptype:
                arryvalu = node.get(prop.name)
                if arryvalu is not None and valu in arryvalu:
                    return True
            else:
                if node.get(prop.name) == valu:
                    return True

        return False

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
    )

    def postTypeInit(self):
        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)
        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)

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

    async def _normHugeText(self, rawtext, view=None):

        text = rawtext.lower().strip()
        text = text.replace(',', '').replace(' ', '')

        try:
            valu, off = s_grammar.chop_float(text, 0)
        except Exception:
            mesg = f'Value does not start with a number: "{rawtext}"'
            raise s_exc.BadTypeValu(mesg=mesg)

        huge = s_common.hugenum(valu)

        unit, off = s_grammar.nom(text, off, s_grammar.unitset)
        if unit:
            mult = self.units.get(unit)
            if mult is None:
                mesg = f'Unknown units for value: "{rawtext}"'
                raise s_exc.BadTypeValu(mesg=mesg)
            huge = s_common.hugemul(huge, mult)

        return huge

    async def norm(self, valu, view=None):

        if valu is None:
            mesg = 'Hugenum type may not be null.'
            raise s_exc.BadTypeValu(mesg=mesg)

        try:
            if isinstance(valu, s_stormtypes.Number):
                huge = valu.valu
            elif isinstance(valu, str):
                huge = await self._normHugeText(valu)
            else:
                huge = s_common.hugenum(valu)

            # behave modulo like int/float
            if self.modulo is not None:
                _, huge = s_common.hugemod(huge, self.modulo)
                if huge < 0:
                    huge = s_common.hugeadd(huge, self.modulo)

                huge = s_common.hugeround(huge)

        except decimal.DecimalException as e:
            mesg = f'Invalid hugenum: {e}'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg) from None

        if huge > hugemax:
            mesg = f'Value ({valu}) is too large for hugenum.'
            raise s_exc.BadTypeValu(mesg=mesg)

        if abs(huge) > hugemax:
            mesg = f'Value ({valu}) is too small for hugenum.'
            raise s_exc.BadTypeValu(mesg=mesg)

        huge = s_common.hugeround(huge).normalize(s_common.hugectx)
        return '{:f}'.format(huge), {}

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

        minval = self.opts.get('min')
        maxval = self.opts.get('max')

        minmin = -2 ** ((self.size * 8) - 1)
        if minval is None:
            minval = minmin

        maxmax = 2 ** ((self.size * 8) - 1) - 1
        if maxval is None:
            maxval = maxmax

        if minval < minmin or maxval > maxmax or maxval < minval:
            raise s_exc.BadTypeDef(self.opts, name=self.name)

        if not self.signed:
            self._indx_offset = 0
            self.minval = 0
            self.maxval = min(2 * maxval, maxval)
        else:
            self._indx_offset = maxmax + 1
            self.minval = max(minmin, minval)
            self.maxval = min(maxmax, maxval)

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bool, self._normPyBool)
        self.setNormFunc(float, self._normPyFloat)

    def merge(self, oldv, newv):

        if self.opts.get('ismin'):
            return min(oldv, newv)

        if self.opts.get('ismax'):
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

    async def getStorCmprs(self, cmpr, valu, virts=None):
        if virts:
            cmpr = f'{virts[0]}{cmpr}'

        func = self.storlifts.get(cmpr)
        if func is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        return await func(cmpr, valu)

    async def _storLiftAt(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            return await self._storLiftNorm(cmpr, valu)

        ticktock = await self.ticktype.getTickTock(valu)
        return (
            ('@=', ticktock, self.stortype),
        )

    async def _ctorCmprAt(self, valu):

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
            (cmpr, norm, self.stortype),
        )

    async def _storLiftPartAt(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            return await self._storLiftNorm(cmpr, valu)

        ticktock = await self.ticktype.getTickTock(valu)
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
        return valu[0]

    def _getMax(self, valu):
        if valu is None:
            return None

        if isinstance(ival := valu[0], int):
            return valu[1]
        return ival[1]

    def _getDuration(self, valu):
        if valu is None:
            return None

        if isinstance(ival := valu[0], int):
            ival = valu

        if (dura := ival[2]) != self.duratype.futdura:
            return dura

        if (dura := (s_common.now() - ival[0])) < 0:
            return None

        return dura

    def _getPrec(self, valu):
        if (virts := valu[2]) is None or (vval := virts.get('precision')) is None:
            return self.prec
        return vval[0]

    async def _storVirtMin(self, valu, newmin):
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

    async def _storVirtMax(self, valu, newmax):
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

    async def _storVirtDuration(self, valu, newdura):
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

    async def _storVirtPrec(self, valu, newprec):
        if valu is None:
            mesg = 'Cannot set precision on an empty ival value.'
            raise s_exc.BadTypeValu(name=self.name, mesg=mesg)

        prec = (await self.prectype.norm(newprec))[0]
        return await self._normPyIter(valu, prec=prec)

    def getTagVirtIndx(self, virts):
        name = virts[0]
        indx = self.tagvirtindx.get(name, s_common.novalu)
        if indx is s_common.novalu:
            raise s_exc.NoSuchVirt.init(name, self)

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

        tick, tock = await self.ticktype.getTickTock(valu, prec=prec)

        minv, info = await self.ticktype._normPyInt(tick, prec=prec)
        maxv, _ = await self.tocktype._normPyInt(tock, prec=prec)
        return (minv, maxv), info

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

        if valu.endswith('.*'):
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

class Ndef(Type):

    stortype = s_layer.STOR_TYPE_NDEF

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.storlifts |= {
            'form=': self._storLiftForm
        }

        self.formnametype = self.modl.type('str').clone({'lower': True, 'strip': True})
        self.virts |= {
            'form': (self.formnametype, self._getForm),
        }

        self.formfilter = None

        self.forms = self.opts.get('forms')
        self.iface = self.opts.get('interface')

        if self.forms and self.iface:
            mesg = 'Ndef type may not specify both forms and interface.'
            raise s_exc.BadTypeDef(mesg=mesg, opts=self.opts)

        if self.forms or self.iface:

            if self.forms is not None:
                forms = set(self.forms)

            def filtfunc(form):

                if self.forms is not None and form.name in forms:
                    return False

                if self.iface is not None and form.implements(self.iface):
                    return False

                return True

            self.formfilter = filtfunc

    async def getStorCmprs(self, cmpr, valu, virts=None):
        if virts:
            cmpr = f'{virts[0]}{cmpr}'

        if (func := self.storlifts.get(cmpr)) is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg, cmpr=cmpr, name=self.name)

        return await func(cmpr, valu)

    async def _storLiftForm(self, cmpr, valu):
        valu = valu.lower().strip()
        if self.modl.form(valu) is None:
            raise s_exc.NoSuchForm.init(valu)

        return (
            (cmpr, valu, self.stortype),
        )

    def _getForm(self, valu):
        valu = valu[0]
        if isinstance(valu[0], str):
            return valu[0]

        return (v[0] for v in valu)

    async def _normStormNode(self, valu, view=None):
        return await self._normPyTuple(valu.ndef)

    async def _normPyTuple(self, valu, view=None):
        try:
            formname, formvalu = valu
        except Exception as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=str(e)) from None

        form = self.modl.form(formname)
        if form is None:
            raise s_exc.NoSuchForm.init(formname)

        if self.formfilter is not None and self.formfilter(form):
            mesg = f'Ndef of form {formname} is not allowed as a value for {self.name} with form filter'
            if self.forms is not None:
                mesg += f' forms={self.forms}'

            if self.iface is not None:
                mesg += f' interface={self.iface}'

            raise s_exc.BadTypeValu(valu=formname, name=self.name, mesg=mesg, forms=self.forms, interface=self.iface)

        formnorm, forminfo = await form.type.norm(formvalu)
        norm = (form.name, formnorm)

        adds = ((form.name, formnorm, forminfo),)
        subs = {'form': form.name}

        return norm, {'adds': adds, 'subs': subs}

    def repr(self, norm):
        formname, formvalu = norm
        form = self.modl.form(formname)
        if form is None:
            raise s_exc.NoSuchForm.init(formname)

        repv = form.type.repr(formvalu)
        return (formname, repv)

class Data(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    def postTypeInit(self):
        self.validator = None
        schema = self.opts.get('schema')
        if schema is not None:
            self.validator = s_config.getJsValidator(schema)

    async def norm(self, valu, view=None):
        try:
            s_json.reqjsonsafe(valu)
            if self.validator is not None:
                self.validator(valu)
        except (s_exc.MustBeJsonSafe, s_exc.SchemaViolation) as e:
            raise s_exc.BadTypeValu(name=self.name, mesg=f'{e}: {s_common.trimText(repr(valu))}') from None
        byts = s_msgpack.en(valu)
        return s_msgpack.un(byts), {}

class NodeProp(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    async def _normPyStr(self, valu, view=None):
        valu = valu.split('=', 1)
        return await self._normPyTuple(valu)

    async def _normPyTuple(self, valu, view=None):
        if len(valu) != 2:
            mesg = f'Must be a 2-tuple: {s_common.trimText(repr(valu))}'
            raise s_exc.BadTypeValu(name=self.name, numitems=len(valu), mesg=mesg) from None

        propname, propvalu = valu

        prop = self.modl.prop(propname)
        if prop is None:
            mesg = f'No prop {propname}'
            raise s_exc.NoSuchProp(mesg=mesg, name=self.name, prop=propname)

        propnorm, info = await prop.type.norm(propvalu)
        return (prop.full, propnorm), {'subs': {'prop': prop.full}}

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

        minv = (await self.subtype.norm(valu[0]))[0]
        maxv = (await self.subtype.norm(valu[1]))[0]

        if minv > maxv:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='minval cannot be greater than maxval')

        return (minv, maxv), {'subs': {'min': minv, 'max': maxv}}

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
        ('replace', ()),
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

        self.regex = None
        restr = self.opts.get('regex')
        if restr is not None:
            self.regex = regex.compile(restr)

        self.envals = None
        enumstr = self.opts.get('enums')
        if enumstr is not None:
            self.envals = enumstr.split(',')

    async def _storLiftEq(self, cmpr, valu):

        if self.opts.get('globsuffix') and valu.endswith('*'):
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

        for look, repl in self.opts.get('replace', ()):
            valu = valu.replace(look, repl)

        # Only strip the left side of the string for prefix match
        if self.opts.get('strip'):
            valu = valu.lstrip()

        if self.opts.get('onespace'):
            valu = s_chop.onespace(valu)

        return valu

    async def _storLiftPref(self, cmpr, valu):
        valu = await self._normForLift(valu)
        return (('^=', valu, self.stortype),)

    async def _storLiftRegx(self, cmpr, valu):
        return ((cmpr, valu, self.stortype),)

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

        for look, repl in self.opts.get('replace', ()):
            norm = norm.replace(look, repl)

        if self.opts['strip']:
            norm = norm.strip()

        if self.opts['onespace']:
            norm = s_chop.onespace(norm)

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
                info['subs'] = subs

        return norm, info

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

        toks = [(await self.taxon.norm(v))[0] for v in valu]
        subs = {
            'base': toks[-1],
            'depth': len(toks) - 1,
        }

        if len(toks) > 1:
            subs['parent'] = '.'.join(toks[:-1]) + '.'

        norm = '.'.join(toks) + '.'
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

    async def _normPyList(self, valu, view=None):

        toks = [(await self.tagpart.norm(v))[0] for v in valu]
        subs = {
            'base': toks[-1],
            'depth': len(toks) - 1,
        }

        if len(toks) > 1:
            subs['up'] = '.'.join(toks[:-1])

        norm = '.'.join(toks)
        if not s_grammar.tagre.fullmatch(norm):
            mesg = f'Tag does not match tagre: [{s_grammar.tagre.pattern}]'
            raise s_exc.BadTypeValu(valu=norm, name=self.name, mesg=mesg)

        core = self.modl.core
        if core is not None:
            (ok, mesg) = core.isTagValid(norm)
            if not ok:
                raise s_exc.BadTypeValu(valu=norm, name=self.name, mesg=mesg)

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
    )

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

        self.unkdura = 0xffffffffffffffff
        self.futdura = 0xfffffffffffffffe

    async def _normPyInt(self, valu, view=None):
        if valu < 0 or valu > self.unkdura:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='Duration value is outside of valid range.')

        return valu, {}

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

        return dura, {}

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

        self.ismin = self.opts.get('ismin')
        self.ismax = self.opts.get('ismax')

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

    async def _liftByIval(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            norm, info = await self.norm(valu)
            return (
                ('=', norm, self.stortype),
            )

        ticktock = await self.getTickTock(valu)
        return (
            (cmpr, ticktock, self.stortype),
        )

    async def _storLiftRange(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            mesg = f'Range value must be a list: {valu!r}'
            raise s_exc.BadTypeValu(mesg=mesg)

        ticktock = await self.getTickTock(valu)

        return (
            (cmpr, ticktock, self.stortype),
        )

    def _getPrec(self, valu):
        if (virts := valu[2]) is None or (vval := virts.get('precision')) is None:
            return self.prec
        return vval[0]

    async def _storVirtPrec(self, valu, newprec):
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
        return valu, {'virts': {'precision': (prec, self.prectype.stortype)}}

    async def _normPyDecimal(self, valu, prec=None, view=None):
        return await self._normPyInt(int(valu), prec=prec)

    async def _normNumber(self, valu, prec=None, view=None):
        return await self._normPyInt(int(valu.valu), prec=prec)

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
                return s_common.now()

            if lowr[0] in ('-', '+'):

                delt = s_time.delta(lowr)
                if relto is None:
                    relto = s_common.now()

                return (await self._normPyInt(delt + relto, prec=prec))[0]

        return (await self.norm(valu, prec=prec))[0]

    async def getTickTock(self, vals, prec=None):
        '''
        Get a tick, tock time pair.

        Args:
            vals (list): A pair of values to norm.
            prec (int): An optional time precision value.

        Returns:
            (int, int): A ordered pair of integers.
        '''
        if len(vals) not in (2, 3):
            mesg = 'Time range must have a length of 2 or 3: %r' % (vals,)
            raise s_exc.BadTypeValu(mesg=mesg)

        val0, val1 = vals[:2]

        try:
            _tick = await self._getLiftValu(val0, prec=prec)
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
            elif val1.startswith('-'):
                sortval = True
                _tock = await self._getLiftValu(val1, relto=_tick, prec=prec)
            else:
                _tock = await self._getLiftValu(val1, relto=_tick, prec=prec)
        else:
            _tock = await self._getLiftValu(val1, relto=_tick, prec=prec)

        if sortval and _tick >= _tock:
            tick = min(_tick, _tock)
            tock = max(_tick, _tock)
            return tick, tock

        return _tick, _tock

    async def _ctorCmprRange(self, vals):
        '''
        Override default range= handler to account for relative computation.
        '''

        if not isinstance(vals, (list, tuple)):
            mesg = f'Must be a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadCmprValu(itemtype=type(vals), cmpr='range=', mesg=mesg)

        if len(vals) != 2:
            mesg = f'Must be a 2-tuple: {s_common.trimText(repr(vals))}'
            raise s_exc.BadCmprValu(itemtype=type(vals), cmpr='range=', mesg=mesg)

        tick, tock = await self.getTickTock(vals)

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
