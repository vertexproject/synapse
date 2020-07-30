import asyncio
import logging
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.grammar as s_grammar

logger = logging.getLogger(__name__)

class Type:

    _opt_defs = ()
    stortype: int = None  # type: ignore

    # a fast-access way to determine if the type is an array
    # ( due to hot-loop needs in the storm runtime )
    isarray = False

    def __init__(self, modl, name, info, opts):
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
        self.form = None # this will reference a Form() if the type is a form
        self.subof = None  # This references the name that a type was extended from.

        self.info.setdefault('bases', ())

        self.opts = dict(self._opt_defs)
        self.opts.update(opts)

        self._type_norms = {}   # python type to norm function map str: _norm_str
        self._cmpr_ctors = {}   # cmpr string to filter function constructor map
        self._cmpr_ctor_lift = {} # if set, create a cmpr which is passed along with indx ops

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

        self.postTypeInit()

    def _storLiftSafe(self, cmpr, valu):
        try:
            return self.storlifts['=']('=', valu)
        except asyncio.CancelledError: # pragma: no cover
            raise
        except Exception:
            return ()

    def _storLiftIn(self, cmpr, valu):
        retn = []
        for realvalu in valu:
            retn.extend(self.getStorCmprs('=', realvalu))
        return retn

    def _storLiftNorm(self, cmpr, valu):
        # NOTE: this may also be used for any other supported
        #       lift operation that requires a simple norm(valu)
        norm, info = self.norm(valu)
        return ((cmpr, norm, self.stortype),)

    def _storLiftRange(self, cmpr, valu):
        minv, minfo = self.norm(valu[0])
        maxv, maxfo = self.norm(valu[1])
        return ((cmpr, (minv, maxv), self.stortype),)

    def _storLiftRegx(self, cmpr, valu):
        return ((cmpr, valu, self.stortype),)

    def getStorCmprs(self, cmpr, valu):

        func = self.storlifts.get(cmpr)
        if func is None:
            mesg = f'Type ({self.name}) has no cmpr: "{cmpr}".'
            raise s_exc.NoSuchCmpr(mesg=mesg)

        return func(cmpr, valu)

    def getStorNode(self, form):
        ndef = (form.name, form.type.norm(self.name)[0])
        buid = s_common.buid(ndef)

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

        pnorms = {}
        for prop, valu in props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {
            'ndef': ndef,
            'props': pnorms,
        })

    def getCompOffs(self, name):
        '''
        If this type is a compound, return the field offset for the given
        property name or None.
        '''
        return None

    def _normStormNode(self, node):
        return self.norm(node.ndef[1])

    def pack(self):
        return {
            'info': dict(self.info),
            'opts': dict(self.opts),
            'stortype': self.stortype,
        }

    def getTypeDef(self):
        basename = self.info['bases'][-1]
        info = self.info.copy()
        info['stortype'] = self.stortype
        return (self.name, (basename, self.opts), info)

    def getTypeVals(self, valu):
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

    def cmpr(self, val1, name, val2):
        '''
        Compare the two values using the given type specific comparator.
        '''
        ctor = self.getCmprCtor(name)
        if ctor is None:
            raise s_exc.NoSuchCmpr(cmpr=name, name=self.name)

        norm1 = self.norm(val1)[0]
        norm2 = self.norm(val2)[0]

        return ctor(norm2)(norm1)

    def _ctorCmprEq(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return norm == valu
        return cmpr

    def _ctorCmprNe(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return norm != valu
        return cmpr

    def _ctorCmprPref(self, valu):
        text = str(valu)

        def cmpr(valu):
            vtxt = self.repr(valu)
            return vtxt.startswith(text)

        return cmpr

    def _ctorCmprRe(self, text):
        regx = regex.compile(text)

        def cmpr(valu):
            vtxt = self.repr(valu)
            return regx.search(vtxt) is not None

        return cmpr

    def _ctorCmprIn(self, vals):
        norms = [self.norm(v)[0] for v in vals]

        def cmpr(valu):
            return valu in norms
        return cmpr

    def _ctorCmprRange(self, vals):

        if not isinstance(vals, (list, tuple)):
            raise s_exc.BadCmprValu(name=self.name, valu=vals, cmpr='range=')

        if len(vals) != 2:
            raise s_exc.BadCmprValu(name=self.name, valu=vals, cmpr='range=')

        minv = self.norm(vals[0])[0]
        maxv = self.norm(vals[1])[0]

        def cmpr(valu):
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

    def norm(self, valu):
        '''
        Normalize the value for a given type.

        Args:
            valu (obj): The value to normalize.

        Returns:
            ((obj,dict)): The normalized valu, info tuple.

        Notes:
            The info dictionary uses the following key conventions:
                subs (dict): The normalized sub-fields as name: valu entries.
        '''
        func = self._type_norms.get(type(valu))
        if func is None:
            raise s_exc.BadTypeValu(name=self.name, mesg='no norm for type: %r.' % (type(valu),))

        return func(valu)

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

    def extend(self, name, opts, info):
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
        tifo.update(info)

        bases = self.info.get('bases') + (self.name,)
        tifo['bases'] = bases

        topt = self.opts.copy()
        topt.update(opts)

        tobj = self.__class__(self.modl, name, tifo, topt)
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

class Bool(Type):

    stortype = s_layer.STOR_TYPE_U8

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bool, self._normPyInt)

    def _normPyStr(self, valu):

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

    def _normPyInt(self, valu):
        return int(bool(valu)), {}

    def repr(self, valu):
        return repr(bool(valu))

class Array(Type):

    isarray = True

    def postTypeInit(self):

        self.isuniq = self.opts.get('uniq', False)
        self.issorted = self.opts.get('sorted', False)

        typename = self.opts.get('type')
        if typename is None:
            mesg = 'Array type requires type= option.'
            raise s_exc.BadTypeDef(mesg=mesg)

        typeopts = self.opts.get('typeopts', {})
        self.arraytype = self.modl.type(typename).clone(typeopts)

        if isinstance(self.arraytype, Array):
            mesg = 'Array type of array values is not (yet) supported.'
            raise s_exc.BadTypeDef(mesg)

        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.stortype = s_layer.STOR_FLAG_ARRAY | self.arraytype.stortype

    def _normPyTuple(self, valu):

        adds = []
        norms = []

        for item in valu:
            norm, info = self.arraytype.norm(item)
            adds.extend(info.get('adds', ()))
            norms.append(norm)

        form = self.modl.form(self.arraytype.name)
        if form is not None:
            adds.extend([(form.name, n) for n in norms])

        adds = list(set(adds))

        if self.isuniq:
            norms = tuple(set(norms))

        if self.issorted:
            norms = tuple(sorted(norms))

        return tuple(norms), {'adds': adds}

    def repr(self, valu):
        return [self.arraytype.repr(v) for v in valu]

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

        self.tcache = FieldHelper(self.modl, fields)

    def _normPyTuple(self, valu):

        fields = self.opts.get('fields')
        if len(fields) != len(valu):
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='invalid number of fields given for norming')

        subs = {}
        adds = []
        norms = []

        for i, (name, _) in enumerate(fields):

            _type = self.tcache[name]

            norm, info = _type.norm(valu[i])

            subs[name] = norm
            norms.append(norm)

            for k, v in info.get('subs', {}).items():
                subs[f'{name}:{k}'] = v
            adds.extend(info.get('adds', ()))

        norm = tuple(norms)
        return norm, {'subs': subs, 'adds': adds}

    def _normPyStr(self, text):
        return self._normPyTuple(text.split(self.sepr))

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
    def __init__(self, modl, fields):
        collections.defaultdict.__init__(self)
        self.modl = modl
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
        self.setdefault(key, _type)
        return _type

class Guid(Type):

    stortype = s_layer.STOR_TYPE_GUID

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyList)
        self.setNormFunc(tuple, self._normPyList)

    def _normPyList(self, valu):
        return s_common.guid(valu), {}

    def _normPyStr(self, valu):

        if valu == '*':
            valu = s_common.guid()
            return valu, {}

        valu = valu.lower()
        if not s_common.isguid(valu):
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='valu is not a guid.')

        return valu, {}

class Hex(Type):

    stortype = s_layer.STOR_TYPE_UTF8

    _opt_defs = (
        ('size', 0),  # type: ignore
    )

    def postTypeInit(self):
        self._size = self.opts.get('size')
        if self._size < 0:
            # zero means no width check
            raise s_exc.BadConfValu(name='size', valu=self._size,
                                    mesg='Size must be > 0')
        if self._size % 2 != 0:
            raise s_exc.BadConfValu(name='size', valu=self._size,
                                    mesg='Size must be a multiple of 2')
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(bytes, self._normPyBytes)
        self.storlifts.update({
            '=': self._storLiftEq,
            '^=': self._storLiftPref,
        })

    def _storLiftEq(self, cmpr, valu):

        if type(valu) == str:
            if valu.endswith('*'):
                return (
                    ('^=', valu[:-1].lower(), self.stortype),
                )

        return self._storLiftNorm(cmpr, valu)

    def _storLiftPref(self, cmpr, valu):
        return (
            ('^=', valu.lower(), self.stortype),
        )

    def _normPyStr(self, valu):
        valu = s_chop.hexstr(valu)
        if self._size and len(valu) != self._size:
            raise s_exc.BadTypeValu(valu=valu, reqwidth=self._size, name=self.name,
                                    mesg='invalid width')
        return valu, {}

    def _normPyBytes(self, valu):
        return self._normPyStr(s_common.ehex(valu))

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

hugemax = 170141183460469231731687
class HugeNum(Type):

    _opt_defs = (
        ('norm', True),
    )

    stortype = s_layer.STOR_TYPE_HUGENUM

    def __init__(self, modl, name, info, opts):

        Type.__init__(self, modl, name, info, opts)

        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)
        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)

        self.storlifts.update({
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
            'range=': self._storLiftRange,
        })

    def norm(self, valu):

        huge = s_common.hugenum(valu)
        if huge > hugemax:
            mesg = f'Value ({valu}) is too large for hugenum.'
            raise s_exc.BadTypeValu(mesg)

        if abs(huge) > hugemax:
            mesg = f'Value ({valu}) is too small for hugenum.'
            raise s_exc.BadTypeValu(mesg)

        if self.opts.get('norm'):
            huge.normalize(), {}
        return huge.to_eng_string(), {}

    def _ctorCmprEq(self, text):
        base = s_common.hugenum(text)
        def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu == base
        return cmpr

    def _ctorCmprGt(self, text):
        base = s_common.hugenum(text)
        def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu > base
        return cmpr

    def _ctorCmprLt(self, text):
        base = s_common.hugenum(text)
        def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu < base
        return cmpr

    def _ctorCmprGe(self, text):
        base = s_common.hugenum(text)
        def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu >= base
        return cmpr

    def _ctorCmprLe(self, text):
        base = s_common.hugenum(text)
        def cmpr(valu):
            valu = s_common.hugenum(valu)
            return valu <= base
        return cmpr

    def _storLiftRange(self, cmpr, valu):
        minv, minfo = self.norm(valu[0])
        maxv, maxfo = self.norm(valu[1])
        return ((cmpr, (minv, maxv), self.stortype),)

class IntBase(Type):

    def __init__(self, modl, name, info, opts):

        Type.__init__(self, modl, name, info, opts)

        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)

        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)

        self.storlifts.update({
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
            'range=': self._storLiftRange,
        })

    def _storLiftRange(self, cmpr, valu):
        minv, minfo = self.norm(valu[0])
        maxv, maxfo = self.norm(valu[1])
        return ((cmpr, (minv, maxv), self.stortype),)

    def _ctorCmprGe(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu >= norm
        return cmpr

    def _ctorCmprLe(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu <= norm
        return cmpr

    def _ctorCmprGt(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu > norm
        return cmpr

    def _ctorCmprLt(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu < norm
        return cmpr

class Int(IntBase):

    _opt_defs = (
        ('size', 8),  # type: ignore # Set the storage size of the integer type in bytes.
        ('signed', True),

        # Note: currently unused
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

    def merge(self, oldv, newv):

        if self.opts.get('ismin'):
            return min(oldv, newv)

        if self.opts.get('ismax'):
            return max(oldv, newv)

        return newv

    def _normPyStr(self, valu):

        if self.enumnorm:
            ival = self.enumnorm.get(valu.lower())
            if ival is not None:
                return self._normPyInt(ival)

        try:
            valu = int(valu, 0)
        except ValueError as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg=str(e)) from None
        return self._normPyInt(valu)

    def _normPyBool(self, valu):
        return self._normPyInt(int(valu))

    def _normPyInt(self, valu):

        if self.minval is not None and valu < self.minval:
            mesg = f'value is below min={self.minval}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        if self.maxval is not None and valu > self.maxval:
            mesg = f'value is above max={self.maxval}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        if self.enumrepr and valu not in self.enumrepr:
            mesg = 'Value is not a valid enum value.'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        return valu, {}

    def repr(self, norm):

        text = self.enumrepr.get(norm)
        if text is not None:
            return text

        return str(norm)

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

    def __init__(self, modl, name, info, opts):

        Type.__init__(self, modl, name, info, opts)

        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)

        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)

        self.storlifts.update({
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
            'range=': self._storLiftRange,
        })

    def _storLiftRange(self, cmpr, valu):
        minv, minfo = self.norm(valu[0])
        maxv, maxfo = self.norm(valu[1])
        return ((cmpr, (minv, maxv), self.stortype),)

    def _ctorCmprGe(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu >= norm
        return cmpr

    def _ctorCmprLe(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu <= norm
        return cmpr

    def _ctorCmprGt(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu > norm
        return cmpr

    def _ctorCmprLt(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
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

    def _normPyStr(self, valu):

        try:
            valu = float(valu)
        except ValueError as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg=str(e)) from None
        return self._normPyFloat(valu)

    def _normPyInt(self, valu):
        valu = float(valu)
        return self._normPyFloat(valu)

    def _normPyFloat(self, valu):
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

    def postTypeInit(self):
        self.futsize = 0x7fffffffffffffff
        self.maxsize = 253402300799999  # 9999/12/31 23:59:59.999

        self.timetype = self.modl.type('time')

        # Range stuff with ival's don't make sense
        # self.indxcmpr.pop('range=', None)
        self._cmpr_ctors.pop('range=', None)

        self.setCmprCtor('@=', self._ctorCmprAt)
        # _ctorCmprAt implements its own custom norm-style resolution
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyIter)
        self.setNormFunc(tuple, self._normPyIter)
        self.storlifts.update({
            '@=': self._storLiftAt,
        })

    def _storLiftAt(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            return self._storLiftNorm(cmpr, valu)

        ticktock = self.timetype.getTickTock(valu)
        return (
            ('@=', ticktock, self.stortype),
        )

    def _ctorCmprAt(self, valu):

        if valu is None or valu == (None, None):
            def cmpr(item):
                return False
            return cmpr

        if isinstance(valu, (str, int)):
            norm = self.norm(valu)[0]
        elif isinstance(valu, (list, tuple)):
            minv, maxv = self._normByTickTock(valu)[0]
            # Use has input the nullset in a comparison operation.
            if minv >= maxv:
                def cmpr(item):
                    return False
                return cmpr
            else:
                norm = (minv, maxv)
        else:
            raise s_exc.NoSuchFunc(name=self.name,
                                   mesg='no norm for @= operator: %r' % (type(valu),))

        def cmpr(item):
            if item is None:
                return False

            if item == (None, None):
                return False

            othr, info = self.norm(item)

            if othr[0] >= norm[1]:
                return False

            if othr[1] <= norm[0]:
                return False

            return True

        return cmpr

    def _normPyInt(self, valu):
        minv, _ = self.timetype._normPyInt(valu)
        maxv, info = self.timetype._normPyInt(minv + 1)
        return (minv, maxv), info

    def _normRelStr(self, valu, relto=None):
        valu = valu.strip().lower()
        # assumes the relative string starts with a - or +

        delt = s_time.delta(valu)
        if not relto:
            relto = s_common.now()

        return self.timetype._normPyInt(delt + relto)[0]

    def _normPyStr(self, valu):
        valu = valu.strip().lower()

        if valu == '?':
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='interval requires begin time')

        if ',' in valu:
            return self._normByTickTock(valu.split(',', 1))

        minv, _ = self.timetype.norm(valu)
        # Norm is guaranteed to be a valid time value, but norm +1 may not be
        maxv, info = self.timetype._normPyInt(minv + 1)
        return (minv, maxv), info

    def _normPyIter(self, valu):
        (minv, maxv), info = self._normByTickTock(valu)

        # Norm via iter must produce an actual range.
        if minv >= maxv:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='Ival range must in (min, max) format')

        return (minv, maxv), info

    def _normByTickTock(self, valu):
        if len(valu) != 2:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='Ival _normPyIter requires 2 items')

        tick, tock = self.timetype.getTickTock(valu)

        minv, _ = self.timetype._normPyInt(tick)
        maxv, _ = self.timetype._normPyInt(tock)
        return (minv, maxv), {}

    def merge(self, oldv, newv):
        mint = min(oldv[0], newv[0])
        maxt = max(oldv[1], newv[1])
        return (mint, maxt)

    def repr(self, norm):
        mint = self.timetype.repr(norm[0])
        maxt = self.timetype.repr(norm[1])
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

    def _storLiftEq(self, cmpr, valu):

        if valu.endswith('.*'):
            norm, info = self.norm(valu[:-2])
            return (
                ('^=', norm, self.stortype),
            )

        norm, info = self.norm(valu)
        return (
            ('=', norm, self.stortype),
        )

    def _storLiftPref(self, cmpr, valu):
        norm, info = self.norm(valu)
        return (
            ('^=', norm, self.stortype),
        )

    def _normPyStr(self, valu):

        valu = valu.lower().strip()

        norms = []
        for part in valu.split('.'):
            part = ' '.join(part.split())
            norms.append(part)

        norm = '.'.join(norms)
        return norm, {}

    @s_cache.memoize()
    def stems(self, valu):
        norm, info = self.norm(valu)
        parts = norm.split('.')
        ret = []
        for i in range(len(parts)):
            part = '.'.join(parts[:i + 1])
            ret.append(part)
        return ret

    def _ctorCmprPref(self, text):
        norm, _ = self.norm(text)

        def cmpr(valu):
            # Shortcut equality
            if valu == norm:
                return True

            vstems = self.stems(valu)
            return norm in vstems

        return cmpr

    def repr(self, norm):
        return norm

class Ndef(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _normStormNode(self, valu):
        return self._normPyTuple(valu.ndef)

    def _normPyTuple(self, valu):
        try:
            formname, formvalu = valu
        except Exception as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=str(e)) from None

        form = self.modl.form(formname)
        if form is None:
            raise s_exc.NoSuchForm(name=self.name, form=formname)

        formnorm, info = form.type.norm(formvalu)
        norm = (form.name, formnorm)

        adds = (norm,)
        subs = {'form': form.name}

        return norm, {'adds': adds, 'subs': subs}

    def repr(self, norm):
        formname, formvalu = norm
        form = self.modl.form(formname)
        if form is None:
            raise s_exc.NoSuchForm(name=self.name, form=formname)

        repv = form.type.repr(formvalu)
        return (formname, repv)

class Edge(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    def getCompOffs(self, name):
        return self.fieldoffs.get(name)

    def postTypeInit(self):

        self.fieldoffs = {'n1': 0, 'n2': 1}

        self.ndeftype = self.modl.types.get('ndef')  # type: Ndef

        self.n1forms = None
        self.n2forms = None

        self.n1forms = self.opts.get('n1:forms', None)
        self.n2forms = self.opts.get('n2:forms', None)

        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _initEdgeBase(self, n1, n2):

        subs = {}

        n1, info = self.ndeftype.norm(n1)

        if self.n1forms is not None:
            if n1[0] not in self.n1forms:
                raise s_exc.BadTypeValu(valu=n1[0], name=self.name, mesg='Invalid source node for edge type')

        subs['n1'] = n1
        subs['n1:form'] = n1[0]

        n2, info = self.ndeftype.norm(n2)

        if self.n2forms is not None:
            if n2[0] not in self.n2forms:
                raise s_exc.BadTypeValu(valu=n2[0], name=self.name, mesg='Invalid dest node for edge type')

        subs['n2'] = n2
        subs['n2:form'] = n2[0]

        return (n1, n2), {'subs': subs}

    def _normPyTuple(self, valu):

        if len(valu) != 2:
            mesg = 'edge requires (ndef, ndef)'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=valu)

        n1, n2 = valu
        return self._initEdgeBase(n1, n2)

    def repr(self, norm):
        n1, n2 = norm
        n1repr = self.ndeftype.repr(n1)
        n2repr = self.ndeftype.repr(n2)
        return (n1repr, n2repr)

class TimeEdge(Edge):

    stortype = s_layer.STOR_TYPE_MSGP

    def getCompOffs(self, name):
        return self.fieldoffs.get(name)

    def postTypeInit(self):
        Edge.postTypeInit(self)
        self.fieldoffs['time'] = 2

    def _normPyTuple(self, valu):

        if len(valu) != 3:
            mesg = 'timeedge requires (ndef, ndef, time)'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=valu)

        n1, n2, tick = valu

        tick, info = self.modl.types.get('time').norm(tick)

        (n1, n2), info = self._initEdgeBase(n1, n2)

        info['subs']['time'] = tick

        return (n1, n2, tick), info

    def repr(self, norm):

        n1, n2, tick = norm

        n1repr = self.ndeftype.repr(n1)
        n2repr = self.ndeftype.repr(n2)
        trepr = self.modl.type('time').repr(tick)

        return (n1repr, n2repr, trepr)

class Data(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    def postTypeInit(self):
        self.validator = None
        schema = self.opts.get('schema')
        if schema is not None:
            self.validator = s_config.getJsValidator(schema)

    def norm(self, valu):
        try:
            s_common.reqjsonsafe(valu)
            if self.validator is not None:
                self.validator(valu)
        except s_exc.MustBeJsonSafe as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=str(e)) from None
        byts = s_msgpack.en(valu)
        return s_msgpack.un(byts), {}

class NodeProp(Type):

    stortype = s_layer.STOR_TYPE_MSGP

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _normPyStr(self, valu):
        valu = valu.split('=', 1)
        return self._normPyTuple(valu)

    def _normPyTuple(self, valu):
        try:
            propname, propvalu = valu
        except Exception as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=str(e)) from None

        prop = self.modl.prop(propname)
        if prop is None:
            raise s_exc.NoSuchProp(name=self.name, prop=propname)

        propnorm, info = prop.type.norm(propvalu)
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

    def _normPyStr(self, valu):
        valu = valu.split('-', 1)
        return self._normPyTuple(valu)

    def _normPyTuple(self, valu):
        if len(valu) != 2:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=f'Must be a 2-tuple of type {self.subtype.name}')

        minv = self.subtype.norm(valu[0])[0]
        maxv = self.subtype.norm(valu[1])[0]

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
        ('strip', False),
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

        self.storlifts.update({
            '=': self._storLiftEq,
            '^=': self._storLiftPref,
            '~=': self._storLiftRegx,
            'range=': self._storLiftRange,
        })

        self.regex = None
        restr = self.opts.get('regex')
        if restr is not None:
            self.regex = regex.compile(restr)

        self.envals = None
        enumstr = self.opts.get('enums')
        if enumstr is not None:
            self.envals = enumstr.split(',')

    def _storLiftEq(self, cmpr, valu):

        if self.opts.get('globsuffix') and valu.endswith('*'):
            return (
                ('^=', valu[:-1], self.stortype),
            )

        return self._storLiftNorm(cmpr, valu)

    def _storLiftRange(self, cmpr, valu):
        minx = self._normForLift(valu[0])
        maxx = self._normForLift(valu[1])
        return (
            (cmpr, (minx, maxx), self.stortype),
        )

    def _normForLift(self, valu):

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

    def _storLiftPref(self, cmpr, valu):
        valu = self._normForLift(valu)
        return (('^=', valu, self.stortype),)

    def _storLiftRegx(self, cmpr, valu):
        return ((cmpr, valu, self.stortype),)

    def _normPyBool(self, valu):
        return self._normPyStr(str(valu).lower())

    def _normPyInt(self, valu):
        return self._normPyStr(str(valu))

    def _normPyStr(self, valu):

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
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='regex does not match')

            subs = match.groupdict()
            if subs:
                info['subs'] = subs

        return norm, info

class Tag(Str):

    def postTypeInit(self):
        Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, text):

        valu = text.lower().strip('#').strip()
        toks = [v.strip() for v in valu.split('.')]

        subs = {
            'base': toks[-1],
            'depth': len(toks) - 1,
        }

        norm = '.'.join(toks)
        if not s_grammar.tagre.fullmatch(norm):
            raise s_exc.BadTypeValu(valu=text, name=self.name,
                                    mesg=f'Tag does not match tagre: [{s_grammar.tagre.pattern}]')

        if len(toks) > 1:
            subs['up'] = '.'.join(toks[:-1])

        return norm, {'subs': subs}

class Time(IntBase):

    stortype = s_layer.STOR_TYPE_TIME

    _opt_defs = (
        ('ismin', False),  # type: ignore
        ('ismax', False),
    )

    def postTypeInit(self):

        self.futsize = 0x7fffffffffffffff
        self.maxsize = 253402300799999  # 9999/12/31 23:59:59.999

        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)

        self.setCmprCtor('@=', self._ctorCmprAt)

        self.ismin = self.opts.get('ismin')
        self.ismax = self.opts.get('ismax')

        self.storlifts.update({
            '@=': self._liftByIval,
        })

        if self.ismin:
            self.stortype = s_layer.STOR_TYPE_MINTIME

    def _liftByIval(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            norm, info = self.norm(valu)
            return (
                ('=', norm, self.stortype),
            )

        ticktock = self.getTickTock(valu)
        return (
            (cmpr, ticktock, self.stortype),
        )

    def _storLiftRange(self, cmpr, valu):

        if type(valu) not in (list, tuple):
            mesg = f'Range value must be a list: {valu!r}'
            raise s_exc.BadTypeValu(mesg=mesg)

        ticktock = self.getTickTock(valu)

        return (
            (cmpr, ticktock, self.stortype),
        )

    def _ctorCmprAt(self, valu):
        return self.modl.types.get('ival')._ctorCmprAt(valu)

    def _normPyStr(self, valu):

        valu = valu.strip().lower()
        if valu == 'now':
            return self._normPyInt(s_common.now())

        # an unspecififed time in the future...
        if valu == '?':
            return self.futsize, {}

        # self contained relative time string

        # we need to be pretty sure this is meant for us, otherwise it might
        # just be a slightly messy time parse
        unitcheck = [u for u in s_time.timeunits.keys() if u in valu]
        if unitcheck and '-' in valu or '+' in valu:
            splitter = '+'
            if '-' in valu:
                splitter = '-'

            bgn, end = valu.split(splitter, 1)
            delt = s_time.delta(splitter + end)
            if bgn:
                bgn = self._normPyStr(bgn)[0]
            else:
                bgn = s_common.now()

            return self._normPyInt(delt + bgn)

        valu = s_time.parse(valu)
        return self._normPyInt(valu)

    def _normPyInt(self, valu):
        if valu > self.maxsize and valu != self.futsize:
            mesg = f'Time exceeds max size [{self.maxsize}] allowed for a non-future marker.'
            raise s_exc.BadTypeValu(mesg=mesg, valu=valu, name=self.name)
        return valu, {}

    def merge(self, oldv, newv):

        if self.ismin:
            return min(oldv, newv)

        if self.ismax:
            return max(oldv, newv)

        return newv

    def repr(self, valu):

        if valu == self.futsize:
            return '?'

        return s_time.repr(valu)

    def _getLiftValu(self, valu, relto=None):

        if isinstance(valu, str):

            lowr = valu.strip().lower()
            if not lowr:
                raise s_exc.BadTypeValu(name=self.name, valu=valu)

            if lowr == 'now':
                return s_common.now()

            if lowr[0] in ('-', '+'):

                delt = s_time.delta(lowr)
                if relto is None:
                    relto = s_common.now()

                return self._normPyInt(delt + relto)[0]

        return self.norm(valu)[0]

    def getTickTock(self, vals):
        '''
        Get a tick, tock time pair.

        Args:
            vals (list): A pair of values to norm.

        Returns:
            (int, int): A ordered pair of integers.
        '''
        if len(vals) != 2:
            mesg = 'Time range must have a length of 2: %r' % (vals,)
            raise s_exc.BadTypeValu(mesg=mesg)

        val0, val1 = vals

        try:
            _tick = self._getLiftValu(val0)
        except ValueError:
            mesg = 'Unable to process the value for val0 in _getLiftValu.'
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
                _tock = self._getLiftValu(val1, relto=_tick)
            else:
                _tock = self._getLiftValu(val1, relto=_tick)
        else:
            _tock = self._getLiftValu(val1, relto=_tick)

        if sortval and _tick >= _tock:
            tick = min(_tick, _tock)
            tock = max(_tick, _tock)
            return tick, tock

        return _tick, _tock

    def _ctorCmprRange(self, vals):
        '''
        Override default range= handler to account for relative computation.
        '''

        if not isinstance(vals, (list, tuple)):
            raise s_exc.BadCmprValu(valu=vals, cmpr='range=')

        if len(vals) != 2:
            raise s_exc.BadCmprValu(valu=vals, cmpr='range=')

        tick, tock = self.getTickTock(vals)

        if tick > tock:
            # User input has requested a nullset
            def cmpr(valu):
                return False

            return cmpr

        def cmpr(valu):
            return tick <= valu <= tock

        return cmpr

    def _ctorCmprEq(self, text):

        norm, info = self.norm(text)

        def cmpr(valu):
            return norm == valu

        return cmpr
