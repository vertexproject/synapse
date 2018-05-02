import json
import math
import base64
import struct
import logging
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps

import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.lib.syntax as s_syntax
import synapse.lib.modules as s_modules
import synapse.lib.msgpack as s_msgpack

import synapse.lookup.iso3166 as s_l_iso3166

logger = logging.getLogger(__name__)

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

        self.liftcmpr = {
            '=': self.liftPropEq,
            '*in=': self.liftPropIn,
        }

        self.setCmprCtor('=', self._ctorCmprEq)

        self.postTypeInit()

    def setCmprCtor(self, name, func):
        self._cmpr_ctors[name] = func

    def getCmprCtor(self, name):
        return self._cmpr_ctors.get(name)

    def _ctorCmprEq(self, text):
        norm, info = self.norm(text)
        def cmpr(valu):
            return norm == valu
        return cmpr

    #def setFiltCtor(self, cmpr, func):
        #self._cmpr_ctors[cmpr] = func

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

        #def func(valu):
            #s_cmpr.
            #return cmprfunc(

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
                repr (str): The repr form of the normalized value.
                subs (dict): The normalized sub-fields as name: valu entries.
                toks (list): A list of seach tokens for the normalized value.
                indx (bytes): The bytes to use in a btree index for the value.
        '''
        func = self._type_norms.get(type(valu))
        if func is None:
            raise s_exc.NoSuchFunc(mesg='no norm for type: %r' % (type(valu),))

        return func(valu)

    def repr(self, norm):
        return str(norm)

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

    def liftByProp(self, xact, prop, valu, cmpr='='):

        func = self.liftcmpr.get(cmpr)
        if func is None:
            s_exc.BadLiftCmpr(cmpr=cmpr, type=self.name, prop=prop.full)

        penc = prop.utf8name
        fenc = prop.form.utf8name
        return func(xact, fenc, penc, valu)

    def liftByForm(self, xact, form, valu, cmpr='='):

        func = self.liftcmpr.get(cmpr)
        if func is None:
            s_exc.BadLiftCmpr(cmpr=cmpr, type=self.name, form=form.name)

        penc = b''
        fenc = form.utf8name
        return func(xact, fenc, penc, valu)

    def liftPropIn(self, xact, fenc, penc, valu):

        for item in valu:
            for row, node in self.liftByProp(xact, fenc, penc, valu):
                yield row, node

    def liftPropEq(self, xact, fenc, penc, valu):

        norm, info = self.norm(valu)
        lops = (
            ('prop:eq', {
                'form': fenc,
                'prop': penc,
                'valu': norm,
                'indx': self.indx(norm),
            }),
        )
        return xact.lift(lops)


class Str(Type):

    _opt_defs = {
        ('regex', None),
        ('lower', False),
    }

    def postTypeInit(self):

        self.regex = None
        restr = self.opts.get('regex')
        if restr is not None:
            self.regex = regex.compile(restr)

    def norm(self, valu):

        norm = str(valu)

        if self.opts['lower']:
            norm = norm.lower()

        if self.regex is not None:
            if self.regex.match(norm) is None:
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg='regex does not match')

        return norm, {}

    def indx(self, norm):
        return norm.encode('utf8')

class Int(Type):

    _opt_defs = (

        ('size', 8),

        ('fmt', '%d'),

        ('min', None),
        ('max', None),

        ('ismin', False),
        ('ismax', False),

#        ('fmt', {'cast': 'str', 'defval': '%d',
#            'doc': 'Set to an integer compatible format string to control repr.'}),
#
#        ('size', {'cast': 'int', 'defval': 8,
#            'doc': 'Set the storage size of the integer type in bytes.'}),
#
#        ('max', {'cast': 'int', 'defval': None,
#            'doc': 'Set to a value to enforce maximum value for the type.'}),
#
#        ('min', {'cast': 'int', 'defval': None,
#            'doc': 'Set to a value to enforce minimum value for the type.'}),
#
#        ('ismin', {'cast': 'bool', 'defval': False,
#            'doc': 'Set to True to enable ismin behavior on value merge.'}),
#
#        ('ismax', {'cast': 'bool', 'defval': False,
#            'doc': 'Set to True to enable ismax behavior on value merge.'}),
    )

    def postTypeInit(self):
        #self.setFiltCtor('=', self._cmpr_eq)
        #self.setFiltCtor('>=', self._cmpr_ge)
        #self.setFiltCtor('<=', self._cmpr_le)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    def merge(self, oldv, newv):

        if self.opts.get('ismin'):
            return min(oldv, newv)

        if self.opts.get('ismax'):
            return max(oldv, newv)

        return newv

    #def runCmprFunc(self, x, y, cmpr='='):

    def getCmprCtor(self, cmpr):
        return self._cmpr_ctors.get(cmpr)

    def cmprCtorEq(self, text):

        norm, info = self.norm(text)

        def cmpr(valu):
            return valu == norm

        return cmpr

    #def _cmpr_le(self, text):
        #norm = self.norm(text)[0]
        #def filt(valu):
            #return valu <= norm
        #return filt

    def _cmpr_ge(self, text):

        norm = self.norm(text)[0]
        def filt(valu):
            return valu >= norm

        return filt

    def _cmpr_eq(self, text):

        if text.find(':') != -1:

            minv, maxv = s_chop.intrange(text)

            def filt(valu):
                return valu >= minv and valu < maxv

            return filt

        norm = self.norm(text)[0]
        def filt(valu):
            return norm == valu

        return filt

    def _chopIntRange(self, text):
        mins, maxs = text.split(':', 1)
        minv = s_common.intify(mins)
        maxv = s_common.intify(maxs)
        return int(x, 0), int(y, 0)

    def _lift_eq(self, text):

        if text.find(':') != -1:

            minv, maxv = s_chop.intrange(text)

            vmin = struct.pack('>Q', int(smin, 0))
            vmax = struct.pack('>Q', int(smax, 0))

            return (('prop:range', {'vmin': vmin, 'vmax': vmax}),)

        valu, infos = self.norm(text)
        return ('prop:eq', {'valu': valu})

    def _lift(self, name, text, cmpr='='):

        if cmpr == '=':

            if text.find(':') != -1:

                smin, smax = text.split(':', 1)

                vmin = struct.pack('>Q', int(smin, 0))
                vmax = struct.pack('>Q', int(smax, 0))

                return ('prop:range', {}), ((vmin, vmax), )

            valu, infos = self.norm(text)
            return ('prop:eq', (name, valu), {})

        raise NoSuchLift(name=name, valu=text, cmpr=cmpr)

        if text.find(':') != -1:
            try:

                smin, smax = text.split(':', 1)

                vmin = struct.pack('>Q', int(smin, 0))
                vmax = struct.pack('>Q', int(smax, 0))

                return ('prop:range', (name, (vmin, vmax)), {})

            except Exception as e:
                logger.exception(e)
                raise s_exc.BadLiftValu(name=name, text=text)

        return Type.lift(self, name, text, cmp=cmp)

    def _normPyStr(self, valu):
        return self._normPyInt(int(valu, 0))

    def _normPyInt(self, valu):
        return valu, {}
        ## TODO check min/max values

    #def norm(self, valu):
        #return int(valu, 0), {}

    def indx(self, valu):
        size = self.opts.get('size')
        return valu.to_bytes(size, 'big')

class Bool(Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bool, self._normPyInt)

        #self.setCmprFunc('=', s_cmpr.eq)

    def indx(self, norm):
        return norm.to_bytes(length=1, byteorder='big')

    def _lift(self, name, text, cmpr='='):

        if cmpr != '=':
            raise BadTypeCmpr(name=self._type_name, cmpr=cmpr)

        valu, info = self.norm(text)
        indx = struct.pack('B', valu)
        return ('prop:eq', (name, indx, valu), {})

    def _stor(self, name, valu):
        valu, info = self.norm(valu)
        indx = struct.pack('B', valu)
        return (name, indx, valu)

    def _normPyStr(self, valu):

        ival = s_common.intify(valu)
        if ival is not None:
            return int(bool(ival)), {}

        if valu in ('true', 't', 'y', 'yes', 'on'):
            return 1, {}

        if valu in ('false', 'f', 'n', 'no', 'off'):
            return 0, {}

        raise s_exc.BadTypeValu(name=self._type_name, valu=valu)

    def _normPyInt(self, valu):
        return int(bool(valu)), {}

    def repr(self, valu):
        return repr(bool(valu))

class Time(Type):

    _opt_defs = (
        ('ismin', False),
        ('ismax', False),
    )

    def postTypeInit(self):

        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)

        self.ismin = self.opts.get('ismin')
        self.ismax = self.opts.get('ismax')

    def _normPyStr(self, valu):

        valu = valu.strip().lower()
        if valu == 'now':
            return self._normPyInt(s_common.now())

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

    def repr(self, valu):
        return s_time.repr(valu)

    def indx(self, norm):
        # offset to prevent pre-epoch negative values from
        # wreaking havoc with the btree range indexing...
        return (norm + 0x8000000000000000).to_bytes(8, 'big')

    def _liftTimeRange(self, xact, fenc, penc, minv, maxv):
        tick, info = self.norm(minv)
        tock, info = self.norm(maxv)

        lops = (
            ('prop:range', {
                'form': fenc,
                'prop': penc,
                'minindx': self.indx(tick),
                'maxindx': self.indx(tock - 1),
            }),
        )

        return xact.lift(lops)

    def liftPropEq(self, xact, fenc, penc, valu):

        # fancy pants time syntax...

        valutype = type(valu)
        if valutype == int:
            return Type.liftPropEq(self, xact, fenc, penc, valu)

        if valutype == str:

            if not valu.strip().endswith('*'):
                return Type.liftPropEq(self, xact, fenc, penc, valu)

            # do a prefix syntax range based lift

            valu = s_chop.digits(valu)
            maxv = str(int(valu) + 1)
            return self._liftTimeRange(xact, fenc, penc, valu, maxv)

        if valutype in (list, tuple):

            try:
                minv, maxv = valu
            except Exception as e:
                mesg = 'Invalid time window has too many fields'
                raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

            return self._liftTimeRange(xact, fenc, penc, minv, maxv)

        return Type.liftPropEq(self, xact, fenc, penc, valu)

class Guid(Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        if valu == '*':
            valu = s_common.guid()
            return valu, {}

        valu = valu.lower()
        if not s_common.isguid(valu):
            raise s_exc.BadTypeValu(name=self.name, valu=valu)

        return valu, {}

    def indx(self, norm):
        return s_common.uhex(norm)

class Loc(Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        valu = valu.lower().strip()

        norms = []
        for part in valu.split():
            part = ' '.join(part.split())
            norms.append(part)

        norm = '.'.join(norms)
        return norm, {}

    def indx(self, norm):
        parts = norm.split('.')
        valu = '\x00'.join(parts) + '\x00'
        return valu.encode('utf8')

    def liftPropEq(self, xact, fenc, penc, text):

        norm, info = self.norm(text)
        indx = self.indx(norm)

        lops = (
            ('prop:pref', {
                'form': fenc,
                'prop': penc,
                'indx': indx,
            }),
        )

        return xact.lift(lops)

class Comp(Type):

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _normPyTuple(self, valu):

        fields = self.opts.get('fields')
        if len(fields) != len(valu):
            raise s_exc.BadTypeValu(name=self.name, valu=valu)

        subs = {}
        norms = []

        for i, (name, typename) in enumerate(fields):

            _type = self.modl.type(typename)
            if _type is None:
                raise FIXME # we need a postModelInit()?

            norm, info = _type.norm(valu[i])

            subs[name] = norm
            norms.append(norm)

        norm = tuple(norms)
        return norm, {'subs': subs}

    def indx(self, norm):
        return s_common.buid(norm)

class Hex(Type):
    _opt_defs = (
        ('width', 0),
    )

    def postTypeInit(self):
        self._width = self.opts.get('width')
        if self._width < 0:
            # zero means no width check
            raise s_exc.BadConfValu(name='width', valu=self._width,
                                    mesg='Width must be > 0')
        self._bsize = int(math.ceil(self._width / 2))
        self._regex = regex.compile(r'^[0-9a-f]+$')
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(bytes, self._normPyBytes)

    def _normPyStr(self, valu):
        valu = valu.strip().lower()
        if valu.startswith('0x'):
            valu = valu[2:]

        if not valu:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='No string left after stripping')

        if not self._regex.match(valu):
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='regex fail')
        if self._width and len(valu) != self._width:
            raise s_exc.BadTypeValu(valu=valu, reqwidth=self._width,
                                    mesg='invalid width')
        return valu, {}

    def _normPyInt(self, valu):
        if valu < 0:
            raise s_exc.BadTypeValu(valu=valu, mesg='Hex cannot handle negative integers')
        valu = f'{valu:x}'
        return valu, {}

    def _normPyBytes(self, valu):
        return self._normPyInt(int.from_bytes(valu, 'big'))

    def indx(self, norm):
        valu = int(norm, 16)
        if self._width:
            size = self._bsize
        else:
            size = int(math.ceil(len(norm) / 2))
        return valu.to_bytes(size, 'big')

class Ndef(Type):

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _normPyTuple(self, valu):
        try:
            formname, formvalu = valu
        except Exception as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu)

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

class NodeProp(Type):

    def postTypeInit(self):
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

    def _normPyTuple(self, valu):
        try:
            propname, propvalu = valu
        except Exception as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu)

        prop = self.modl.prop(propname)
        if prop is None:
            raise s_exc.NoSuchProp(name=propname)

        propnorm, info = prop.type.norm(propvalu)
        return (prop.full, propnorm), {}

    def indx(self, norm):
        return s_common.buid(norm)

######################################################################
# TODO FROM HERE DOWN....
######################################################################

class JsonType(Type):

    def norm(self, valu, oldval=None):

        if not isinstance(valu, str):
            try:
                return json.dumps(valu, sort_keys=True, separators=(',', ':')), {}
            except Exception as e:
                raise s_exc.BadTypeValu(valu, mesg='Unable to normalize object as json.')

        try:
            return json.dumps(json.loads(valu), sort_keys=True, separators=(',', ':')), {}
        except Exception as e:
            raise s_exc.BadTypeValu(valu, mesg='Unable to norm json string')


def islist(x):
    return type(x) in (list, tuple)


tagre = regex.compile(r'^([\w]+\.)*[\w]+$')

class TagType(Type):

    def norm(self, valu, oldval=None):

        parts = valu.split('@', 1)

        subs = {}

        if len(parts) == 2:
            strs = parts[1].split('-')
            tims = [self.modl.getTypeNorm('time', s)[0] for s in strs]

            tmin = min(tims)
            tmax = max(tims)

            subs['seen:min'] = tmin
            subs['seen:max'] = tmax

        retn = parts[0].lower()
        if not tagre.match(retn):
            raise s_exc.BadTypeValu(valu)

        return retn, subs

class StormType(Type):

    def norm(self, valu, oldval=None):
        try:
            s_syntax.parse(valu)
        except Exception as e:
            raise s_exc.BadTypeValu(valu)
        return valu, {}

class PermType(Type):
    '''
    Enforce that the permission string and options are known.
    '''
    def norm(self, valu, oldval=None):

        try:
            pnfo, off = s_syntax.parse_perm(valu)
        except Exception as e:
            raise s_exc.BadTypeValu(valu)

        if off != len(valu):
            raise s_exc.BadTypeValu(valu)
        return valu, {}
