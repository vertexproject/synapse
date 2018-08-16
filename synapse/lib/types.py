import logging
import collections

import regex
import xxhash

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)
tagre = regex.compile(r'^([\w]+\.)*[\w]+$')

class Type:

    _opt_defs = ()

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

        self.opts = dict(self._opt_defs)
        self.opts.update(opts)

        self._type_norms = {}   # python type to norm function map str: _norm_str
        self._cmpr_ctors = {}   # cmpr string to filter function constructor map

        self.indxcmpr = {
            '=': self.indxByEq,
            '*in=': self.indxByIn,
            '*range=': self.indxByRange,
        }

        self.setCmprCtor('=', self._ctorCmprEq)
        self.setCmprCtor('!=', self._ctorCmprNe)
        self.setCmprCtor('~=', self._ctorCmprRe)
        self.setCmprCtor('^=', self._ctorCmprPref)
        self.setCmprCtor('*in=', self._ctorCmprIn)

        self.postTypeInit()

    def _getIndxChop(self, indx):

        # cut down an index value to 256 bytes...
        if len(indx) <= 256:
            return indx

        base = indx[:248]
        sufx = xxhash.xxh64(indx).digest()
        return base + sufx

    def pack(self):
        return {'info': dict(self.info), 'opts': dict(self.opts)}

    def getTypeVals(self, valu):
        yield valu

    def setCmprCtor(self, name, func):
        self._cmpr_ctors[name] = func

    def getCmprCtor(self, name):
        return self._cmpr_ctors.get(name)

    def cmpr(self, val1, name, val2):
        '''
        Compare the two values using the given type specific comparitor.
        '''
        ctor = self.getCmprCtor(name)
        if ctor is None:
            raise s_exc.NoSuchCmpr(name=name)

        norm1 = self.norm(val1)[0]
        norm2 = self.norm(val2)[0]

        return ctor(norm1)(norm2)

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
            vtxt = self.repr(valu, defval=valu)
            return vtxt.startswith(text)

        return cmpr

    def _ctorCmprRe(self, text):
        regx = regex.compile(text)

        def cmpr(valu):
            vtxt = self.repr(valu, defval=valu)
            return regx.match(vtxt) is not None

        return cmpr

    def _ctorCmprIn(self, vals):
        norms = [self.norm(v)[0] for v in vals]

        def cmpr(valu):
            return valu in norms
        return cmpr

    def indxByEq(self, valu):
        norm, info = self.norm(valu)

        indx = self.indx(norm)
        if indx is None:
            raise s_exc.NoSuchIndx(name=self.name)

        return (
            ('eq', indx),
        )

    def getStorIndx(self, norm):

        indx = self.indx(norm)
        if indx is None:
            return b''

        if len(indx) <= 256:
            return indx

        return self._getIndxChop(indx)

    def indxByIn(self, vals):

        opers = []
        if type(vals) not in (list, tuple):
            raise s_exc.BadCmprValu(valu=vals, cmpr='*in=')

        for valu in vals:
            opers.extend(self.getIndxOps(valu))

        return opers

    def indxByRange(self, valu):

        if type(valu) not in (list, tuple):
            raise s_exc.BadCmprValu(valu=valu, cmpr='*range=')

        if len(valu) != 2:
            raise s_exc.BadCmprValu(valu=valu, cmpr='*range=')

        minv, _ = self.norm(valu[0])
        maxv, _ = self.norm(valu[1])

        mini = self.indx(minv)
        maxi = self.indx(maxv)

        return (
            ('range', (mini, maxi)),
        )

    def getFiltFunc(self, cmpr, text):
        '''
        Return a filter function for the given value and comparison.

        Args:
            cmpr (str): Comparison operator such as '='.
            text (str): The query text to compare against.
        '''
        ctor = self._cmpr_ctors.get(cmpr)
        if ctor is not None:
            return ctor(text)

        norm, info = self.norm(text)

        #cmprfunc = s_cmpr.get(cmpr)
        #if cmprfunc is None:
            #raise s_exc.NoSuchCmpr(name=cmpr)

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
            raise s_exc.NoSuchFunc(type=self.name, mesg='no norm for type: %r' % (type(valu),))

        return func(valu)

    def repr(self, norm, defval=None):
        '''
        Return a printable representation for the value.  For types which need no
        display processing, the normalized value should be returned.
        '''
        return defval

    def indx(self, norm):
        '''
        Return the property index bytes for the given *normalized* value.
        '''
        name = self.__class__.__name__
        raise s_exc.NoSuchImpl(name='%s.indx' % name)

    def merge(self, oldv, newv):
        '''
        Allow types to "merge" data from two sources based on value precidence.

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

        topt = self.opts.copy()
        topt.update(opts)

        return self.__class__(self.modl, name, tifo, topt)

    def clone(self, opts):
        '''
        Create a new instance of this type with the specified options.

        Args:
            opts (dict): The type specific options for the new instance.
        '''
        topt = self.opts.copy()
        topt.update(opts)
        return self.__class__(self.modl, self.name, self.info, topt)

    def getIndxOps(self, valu, cmpr='='):
        '''
        Return a list of index operation tuples to lift values in a table.

        Valid index operations include:
            ('eq', <indx>)
            ('pref', <indx>)
            ('range', (<minindx>, <maxindx>))
        '''
        func = self.indxcmpr.get(cmpr)

        if func is None:
            raise s_exc.NoSuchCmpr(type=self.name, cmpr=cmpr)

        return func(valu)

class Bool(Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bool, self._normPyInt)

    def indx(self, norm):
        return norm.to_bytes(length=1, byteorder='big')

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

    def repr(self, valu, defval=None):
        return repr(bool(valu))

class Comp(Type):

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)
        self.tcache = FieldHelper(self.modl, self.opts.get('fields', ()))

    def _normPyTuple(self, valu):

        fields = self.opts.get('fields')
        if len(fields) != len(valu):
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='invalid number of fields given for norming')

        subs = {}
        adds = []
        norms = []

        for i, (name, typename) in enumerate(fields):
            _type = self.tcache[name]

            norm, info = _type.norm(valu[i])

            subs[name] = norm
            norms.append(norm)

            for k, v in info.get('subs', {}).items():
                subs[f'{name}:{k}'] = v
            adds.extend(info.get('adds', ()))

        norm = tuple(norms)
        return norm, {'subs': subs, 'adds': adds}

    def repr(self, valu, defval=None):

        vals = []
        fields = self.opts.get('fields')

        hit = False
        for valu, (name, typename) in zip(valu, fields):

            # if any of our comp fields need repr we do too...
            rval = self.tcache[name].repr(valu)

            if rval is not None:
                hit = True
                vals.append(rval)
            else:
                vals.append(valu)

        if hit:
            return tuple(vals)

        return defval

    def indx(self, norm):
        return s_common.buid(norm)


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
        return _type


class Guid(Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        if valu == '*':
            valu = s_common.guid()
            return valu, {}

        valu = valu.lower()
        if not s_common.isguid(valu):
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='valu is not a guid.')

        return valu, {}

    def indx(self, norm):
        return s_common.uhex(norm)


class Hex(Type):

    _opt_defs = (
        ('size', 0),
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

    def indxByEq(self, valu):
        if isinstance(valu, str) and valu.endswith('*'):
            valu = valu.rstrip('*')
            norm = s_chop.hexstr(valu)
            return (
                ('pref', self.indx(norm)),
            )

        return Type.indxByEq(self, valu)

    def _normPyStr(self, valu):
        valu = s_chop.hexstr(valu)
        if self._size and len(valu) != self._size:
            raise s_exc.BadTypeValu(valu=valu, reqwidth=self._size, name=self.name,
                                    mesg='invalid width')
        return valu, {}

    def _normPyBytes(self, valu):
        return self._normPyStr(s_common.ehex(valu))

    def indx(self, norm):
        return s_common.uhex(norm)

class IntBase(Type):

    def __init__(self, modl, name, info, opts):

        Type.__init__(self, modl, name, info, opts)

        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)

        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)

        self.indxcmpr['>='] = self.indxByGe
        self.indxcmpr['<='] = self.indxByLe

        self.indxcmpr['>'] = self.indxByGt
        self.indxcmpr['<'] = self.indxByLt

    def indxByGe(self, valu):

        norm, info = self.norm(valu)

        indx = self.indx(norm)
        imax = b'\xff' * len(indx)

        return (
            ('range', (indx, imax)),
        )

    def indxByLe(self, valu):

        norm, info = self.norm(valu)

        indx = self.indx(norm)
        imin = b'\x00' * len(indx)

        return (
            ('range', (imin, indx)),
        )

    def indxByGt(self, valu):

        norm, info = self.norm(valu)

        indx = self.indx(norm + 1)
        imax = b'\xff' * len(indx)

        return (
            ('range', (indx, imax)),
        )

    def indxByLt(self, valu):

        norm, info = self.norm(valu)

        indx = self.indx(norm - 1)
        imin = b'\x00' * len(indx)

        return (
            ('range', (imin, indx)),
        )

    def _ctorCmprGe(self, text):
        norm, info = self.norm(text)
        def cmpr(valu):
            return norm >= valu
        return cmpr

    def _ctorCmprLe(self, text):
        norm, info = self.norm(text)
        def cmpr(valu):
            return norm <= valu
        return cmpr

    def _ctorCmprGt(self, text):
        norm, info = self.norm(text)
        def cmpr(valu):
            return norm > valu
        return cmpr

    def _ctorCmprLt(self, text):
        norm, info = self.norm(text)
        def cmpr(valu):
            return norm < valu
        return cmpr

class Int(IntBase):

    _opt_defs = (
        ('size', 8),  # Set the storage size of the integer type in bytes.
        ('signed', True),

        ('fmt', '%d'),  # Set to an integer compatible format string to control repr.

        ('min', None),  # Set to a value to enforce minimum value for the type.
        ('max', None),  # Set to a value to enforce maximum value for the type.

        ('ismin', False),  # Set to True to enable ismin behavior on value merge.
        ('ismax', False),  # Set to True to enable ismax behavior on value merge.
    )

    def postTypeInit(self):

        self.size = self.opts.get('size')
        self.signed = self.opts.get('signed')

        minval = self.opts.get('min')
        maxval = self.opts.get('max')

        minmin = -2 ** ((self.size * 8) - 1)
        if minval is None:
            minval = minmin

        maxmax = 2 ** ((self.size * 8) - 1) - 1
        if maxval is None:
            maxval = maxmax

        if minval < minmin or maxval > maxmax or maxval < minval:
            raise s_exc.BadTypeDef(self.opts)

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

    def merge(self, oldv, newv):

        if self.opts.get('ismin'):
            return min(oldv, newv)

        if self.opts.get('ismax'):
            return max(oldv, newv)

        return newv

    def _normPyStr(self, valu):
        try:
            valu = int(valu, 0)
        except ValueError as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg=str(e))
        return self._normPyInt(valu)

    def _normPyInt(self, valu):

        if self.minval is not None and valu < self.minval:
            mesg = f'value is below min={self.minval}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        if self.maxval is not None and valu > self.maxval:
            mesg = f'value is above max={self.maxval}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg)

        return valu, {}

    def indx(self, valu):
        return (valu + self._indx_offset).to_bytes(self.size, 'big')

    def repr(self, norm, defval=None):
        return str(norm)

class Ival(Type):
    '''
    An interval, i.e. a range, of times
    '''

    def postTypeInit(self):

        self.timetype = self.modl.type('time')

        self.setCmprCtor('@=', self._ctorCmprAt)

        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyIter)
        self.setNormFunc(tuple, self._normPyIter)
        #self.setNormFunc(None.__class__, self._normPyNone)

    def _ctorCmprAt(self, valu):

        if valu is None or valu == (None, None):
            def cmpr(item):
                return False
            return cmpr

        norm = self.norm(valu)[0]

        def cmpr(item):

            if item is None or item == (None, None):
                return False

            othr, info = self.norm(item)

            if othr[0] >= norm[1]:
                return False

            if othr[1] <= norm[0]:
                return False

            return True

        return cmpr

    #def _normPyNone(self, valu):
        # none is an ok interval (unknown...)
        #return valu, {}

    def _normPyInt(self, valu):
        return (valu, valu + 1), {}

    def _normPyStr(self, valu):
        norm, info = self.timetype.norm(valu)
        # TODO until we support 2013+2years syntax...
        return (norm, norm + 1), {}

    def _normPyIter(self, valu):

        vals = [self.timetype.norm(v)[0] for v in valu if v is not None]
        if len(vals) == 1:
            vals.append(vals[0] + 1)

        norm = (min(vals), max(vals))
        return norm, {}

    def merge(self, oldv, newv):
        mint = min(oldv[0], newv[0])
        maxt = max(oldv[1], newv[1])
        return (mint, maxt)

    def indx(self, norm):

        if norm is None:
            return b''

        indx = self.timetype.indx(norm[0])
        indx += self.timetype.indx(norm[1])

        return indx

    def repr(self, norm, defval=None):
        mint = self.timetype.repr(norm[0])
        maxt = self.timetype.repr(norm[1])
        return (mint, maxt)

class Loc(Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        valu = valu.lower().strip()

        norms = []
        for part in valu.split('.'):
            part = ' '.join(part.split())
            norms.append(part)

        norm = '.'.join(norms)
        return norm, {}

    def indx(self, norm):
        parts = norm.split('.')
        valu = '\x00'.join(parts) + '\x00'
        return valu.encode('utf8', 'surrogatepass')

    def indxByEq(self, valu):

        norm, info = self.norm(valu)
        indx = self.indx(norm)

        return (
            ('pref', indx),
        )

class Ndef(Type):

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _normPyTuple(self, valu):
        try:
            formname, formvalu = valu
        except Exception as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=str(e))

        form = self.modl.form(formname)
        if form is None:
            raise s_exc.NoSuchForm(name=formname)

        formnorm, info = form.type.norm(formvalu)
        norm = (form.name, formnorm)

        adds = (norm,)
        subs = {'form': form.name}

        return norm, {'adds': adds, 'subs': subs}

    def indx(self, norm):
        return s_common.buid(norm)

#class List(Type):

    #def postTypeInit(self):

        #self.setNormFunc(list, self._normPyTuple)
        #self.setNormFunc(tuple, self._normPyTuple)

        # *contains= cmpr and eventually lift

        #typename = self.opts.get('type')
        #if typename is None:
            #mesg = 'type option is required for list type'
            #raise s_exc.BadConfValu(name='type', valu=None, mesg=mesg)

        #self.itemtype = self.modl.types.get(typename)
        #if self.itemtype is None:
            #raise s_exc.NoSuchType(typename)

    #def _normPyTuple(self, valu):

        #retn = []

        #for item in valu:
            #norm, info = self.itemtype.norm(item)
            #retn.append(norm)

        #return tuple(retn), {}

    #def indx(self, norm):
        #return None

class Edge(Type):

    def postTypeInit(self):

        self.ndeftype = self.modl.types.get('ndef')

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

    def indx(self, norm):
        return s_common.buid(norm)

class TimeEdge(Edge):

    def _normPyTuple(self, valu):

        if len(valu) != 3:
            mesg = 'timeedge requires (ndef, ndef, time)'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=valu)

        n1, n2, tick = valu

        tick, info = self.modl.types.get('time').norm(tick)

        (n1, n2), info = self._initEdgeBase(n1, n2)

        info['subs']['time'] = tick

        return (n1, n2, tick), info

class Data(Type):

    def norm(self, valu):
        byts = s_msgpack.en(valu)
        return s_msgpack.un(byts), {}

    def indx(self, norm):
        return None

class NodeProp(Type):

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
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=str(e))

        prop = self.modl.prop(propname)
        if prop is None:
            raise s_exc.NoSuchProp(name=propname)

        propnorm, info = prop.type.norm(propvalu)
        return (prop.full, propnorm), {'subs': {'prop': prop.full}}

    def indx(self, norm):
        return s_common.buid(norm)


class Range(Type):

    _opt_defs = (
        ('type', None),
    )

    def postTypeInit(self):
        subtype = self.opts.get('type')
        if not(type(subtype) is tuple and len(subtype) is 2):
            raise s_exc.BadTypeDef(self.opts)

        try:
            self.subtype = self.modl.type(subtype[0]).clone(subtype[1])
        except Exception as e:
            logger.exception('subtype invalid or unavailable')
            raise s_exc.BadTypeDef(self.opts, mesg='subtype invalid or unavailable')

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(tuple, self._normPyTuple)

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

    def indx(self, norm):
        return self.subtype.indx(norm[0]) + self.subtype.indx(norm[1])

    def repr(self, norm, defval=None):

        subx = self.subtype.repr(norm[0])
        suby = self.subtype.repr(norm[1])

        if subx is not None:
            return (subx, suby)

        return defval

class Str(Type):

    _opt_defs = (
        ('enums', None),
        ('regex', None),
        ('lower', False),
        ('strip', False),
        ('onespace', False),
    )

    def postTypeInit(self):

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyStr)

        self.regex = None
        restr = self.opts.get('regex')
        if restr is not None:
            self.regex = regex.compile(restr)

        self.envals = None
        enumstr = self.opts.get('enums')
        if enumstr is not None:
            self.envals = enumstr.split(',')

        self.indxcmpr['^='] = self.indxByPref

    def indxByPref(self, valu):

        # doesnt have to be normable...
        if self.opts.get('lower'):
            valu = valu.lower()

        # Only strip the left side of the string for prefix match
        if self.opts.get('strip'):
            valu = valu.lstrip()

        if self.opts.get('onespace'):
            valu = s_chop.onespace(valu)

        return (
            ('pref', valu.encode('utf8', 'surrogatepass')),
        )

    def _normPyStr(self, valu):

        norm = str(valu)

        if self.opts['lower']:
            norm = norm.lower()

        if self.opts['strip']:
            norm = norm.strip()

        if self.opts['onespace']:
            norm = s_chop.onespace(norm)

        if self.envals is not None:
            if norm not in self.envals:
                raise s_exc.BadTypeValu(valu=valu, name=self.name, enums=self.info.get('enums'),
                                        mesg='Value not in enums')

        if self.regex is not None:
            if self.regex.match(norm) is None:
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='regex does not match')

        return norm, {}

    def indx(self, norm):
        return norm.encode('utf8', 'surrogatepass')


class Tag(Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.indxcmpr['^='] = self.indxByPref

    def indxByPref(self, valu):
        norm, info = self.norm(valu)
        return (
            ('pref', norm.encode('utf8')),
        )

    def _normPyStr(self, text):

        valu = text.lower().strip('#').strip()
        toks = [v.strip() for v in valu.split('.')]

        subs = {
            'base': toks[-1],
            'depth': len(toks) - 1,
        }

        norm = '.'.join(toks)
        if not tagre.match(norm):
            raise s_exc.BadTypeValu(valu=text, name=self.name,
                                    mesg=f'Tag does not match tagre: [{tagre.pattern}]')

        if len(toks) > 1:
            subs['up'] = '.'.join(toks[:-1])

        return norm, {'subs': subs}

    def indx(self, norm):
        return norm.encode('utf8')


class Time(IntBase):

    _opt_defs = (
        ('ismin', False),
        ('ismax', False),
    )

    def postTypeInit(self):

        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)

        self.setCmprCtor('@=', self._ctorCmprAt)

        self.ismin = self.opts.get('ismin')
        self.ismax = self.opts.get('ismax')

    def _ctorCmprAt(self, valu):
        return self.modl.types.get('ival')._ctorCmprAt(valu)

    def _normPyStr(self, valu):

        valu = valu.strip().lower()
        if valu == 'now':
            return self._normPyInt(s_common.now())

        # an unspecififed time in the future...
        if valu == '?':
            return 0x7fffffffffffffff, {}

        valu = s_time.parse(valu)
        return self._normPyInt(valu)

    def _normPyInt(self, valu):
        return valu, {}

    def merge(self, oldv, newv):

        if self.ismin:
            return min(oldv, newv)

        if self.ismax:
            return max(oldv, newv)

        return newv

    def repr(self, valu, defval=None):

        if valu == 0x7fffffffffffffff:
            return '?'

        return s_time.repr(valu)

    def indx(self, norm):
        # offset to prevent pre-epoch negative values from
        # wreaking havoc with the btree range indexing...
        return (norm + 0x8000000000000000).to_bytes(8, 'big')

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

                return delt + relto

        return self.norm(valu)[0]

    def _indxTimeRange(self, mint, maxt):
        minv, _ = self.norm(mint)
        maxv, _ = self.norm(maxt)
        return (
            ('range', (self.indx(minv), self.indx(maxv))),
        )

    def indxByEq(self, valu):

        if isinstance(valu, str):

            if valu.endswith('*'):
                valu = s_chop.digits(valu)
                maxv = str(int(valu) + 1)
                return self._indxTimeRange(valu, maxv)

            if valu and valu[0] == '-':
                tock = s_common.now()
                delt = s_time.delta(valu)
                return self._indxTimeRange(tock + delt, tock)

        if type(valu) in (tuple, list):
            tick = self._getLiftValu(valu[0])
            tock = self._getLiftValu(valu[1], relto=tick)
            return self._indxTimeRange(tick, tock)

        return Type.indxByEq(self, valu)
