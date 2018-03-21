import json
import base64
import logging
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps

import synapse.lib.time as s_time
import synapse.lib.syntax as s_syntax
import synapse.lib.modules as s_modules
import synapse.lib.msgpack as s_msgpack

import synapse.lookup.iso3166 as s_l_iso3166

logger = logging.getLogger(__name__)

class Type:

    def __init__(self, name, modl, info, opts):
        self._type_name = name
        self._type_modl = modl
        self._type_info = info
        self._type_opts = opts

        self._reqTypeOpts()
        self.postTypeInit()

    def addTypeNorm(self, typo, func):
        '''
        Register a normalizer function for a given python type.
        '''
        self._type_norms[typo] = func

    def postTypeInit(self):
        pass

    def _reqTypeOpts(self):
        pass

    def name(self):
        return self._type_name

    def info(self, name):
        return self._type_info.get(name)

    def opts(self):
        return dict(self._type_opts)

    def opt(self, name):
        return self._type_opts.get(name)

    def get(self, prop, defval=None):
        '''
        Retrieve a type info property from this type or parent types.

        Example:

            ex = item.get('doc')

        '''
        return self.modl.getTypeInfo(self.name, prop, defval=defval)

    def norm(self, valu):

        func = self._type_norms.get(type(valu))
        if func is None:
            raise NoTypeNorm(name=self._type_name, type=type(valu))

        return func(valu)

    def repr(self, valu):
        return str(valu)

    def adds(self, text):
        '''
        Return a list of values to create from the given text.
        '''
        return (self.norm(text)[0], )

    def lift(self, name, text, cmp='='):
        '''
        Return a lift operation tuple for the given query text.
        '''
        valu, infos = self.norm(text)
        return ('prop:eq', (name, valu), {})

    def clone(self, name, info, **opts):
        '''
        Extend this type for sub-type or prop construction.
        '''
        tifo = self._type_info.copy()
        tifo.update(info)

        topt = self._type_opts.copy()
        topt.update(opts)

        return self.__class__(name, self._type_modl, tifo, opts=topt)

class Str(Type):

    _opt_defs = {
        'regex': None,
        'lower': False,
    }

    def norm(self, valu):
        return str(valu), {}

class Int(Type):

    #def postTypeInit(self):
        #self.addTypeNorm(str, self._norm_str)
        #self.addTypeNorm(str, self._norm_int)

    #def lift(self, text, cmp='='):
        #if text.find(',') != -1:

    #def adds(self, text):
        #if text.find(','

    def lift(self, name, text, cmp='='):

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

    def norm(self, valu):
        return int(valu, 0), {}

class Bool(Type):

    def postTypeInit(self):
        self.addTypeNorm(str, self._norm_str)
        self.addTypeNorm(int, self._norm_int)
        self.addTypeNorm(bool, self._norm_int)

    def _norm_str(self, valu):

        valu = valu.lower()
        if valu in ('true', 't', 'y', 'yes', '1', 'on'):
            return 1, {}

        if valu in ('false', 'f', 'n', 'no', '0', 'off'):
            return 0, {}

        raise BadTypeValu(name=self._type_name, valu=valu)

    def _norm_int(self, valu):
        return int(bool(valu)), {}

    def repr(self, valu):
        return repr(bool(valu))


class Guid(Type):

    #def __init__(self, modl, name, **info):
        #Type.__init__(self, modl, name, **info)
        #self._guid_alias = info.get('alias')
        # TODO figure out what to do about modl vs core issues
        #self._getTufoByProp = getattr(modl, 'getTufoByProp', None)
        #self._reqPropNorm = getattr(modl, 'reqPropNorm', None)

    def norm(self, valu, oldval=None):

        if isinstance(valu, dict):
            vals = list(valu.items())
            return self._norm_list(vals, oldval)

        if isinstance(valu, (list, tuple)):
            return self._norm_list(valu, oldval)

        if not isinstance(valu, str) or len(valu) < 1:
            self._raiseBadValu(valu)

        return self._norm_str(valu, oldval)

    def _norm_str(self, text, oldval=None):
        text = text.strip()
        if not text:
            self._raiseBadValu(text, mesg='No text left after strip().')

        if text[0] == '(':
            vals, off = s_syntax.parse_list(text)
            if off != len(text):
                self._raiseBadValu(text, off=off, vals=vals,
                                   mesg='List parting for guid type did not consume all of the input text.')
            return self._norm_list(vals, oldval)

        # generate me one.  we dont care.
        if text == '*':
            return s_common.guid(), {}

        #if text[0] != '$':
            ##retn = text.lower().replace('-', '')
            #if not s_common.isguid(retn):
                #self._raiseBadValu(text, mesg='Expected a 32 char guid string')

            #return retn, {}

        #node = self.modl.getTufoByProp('syn:alias', text)
        #if node is not None:
            #return node[1].get('syn:alias:iden'), {}

        # TODO remove legacy model aliases
        #if self._guid_alias is None:
            #self._raiseBadValu(text, mesg='guid resolver syntax used with non-aliased guid')

        #if self._getTufoByProp is None:
            #self._raiseBadValu(text, mesg='guid resolver syntax used with non-cortex modl')

        # ( sigh... eventually everything will be a cortex... )
        #node = self._getTufoByProp(self._guid_alias, text[1:])
        #if node is None:
            #self._raiseBadValu(text, mesg='no result for guid resolver',
                               #alias=self._guid_alias)

        #iden = node[1].get(node[1].get('tufo:form'))
        #return iden, {}

    def _norm_list(self, valu, oldval=None):

        if not valu:
            self._raiseBadValu(valu=valu, mesg='No valus present in list to make a guid with')

        if not self.prop:
            self._raiseBadValu(valu,
                               mesg='Unable to norm a list for a guidtype which is not associated with a property.')

        vals = []
        subs = {}

        for kv in valu:
            if not isinstance(kv, (list, tuple)) or not len(kv) == 2:
                self._raiseBadValu(valu, kv=kv, mesg='Expected a list or tuple of length 2')

            k, v = kv
            fullprop = self.prop + ':' + k
            try:
                v, ssubs = self._reqPropNorm(fullprop, v)
            except s_common.NoSuchProp:
                logger.exception('Error while norming list of props for guid type.')
                self._raiseBadValu(valu, prop=k, fullprop=fullprop,
                                   mesg='Non-model property provided when making a stable guid.')
            subs.update({':'.join([k, _k]): _v for _k, _v in ssubs.items()})
            vals.append((k, v))

        # Stable sort based on the property
        vals.sort(key=lambda x: x[0])
        valu = s_common.guid(valu=vals)
        subs.update(vals)
        return valu, subs

class Fqdn(Type):
    subprops = (
        ('sfx', {'ptype': 'bool'}),
        ('zone', {'ptype': 'bool'}),
        ('domain', {'ptype': 'inet:fqdn'}),
        ('host', {'ptype': 'str'}),
    )

    def norm(self, valu):

        valu = valu.replace('[.]', '.')
        if not fqdnre.match(valu):
            self._raiseBadValu(valu)

        try:
            valu = valu.encode('idna').decode('utf8').lower()
        except UnicodeError as e:
            self._raiseBadValu(valu)

        parts = valu.split('.', 1)
        subs = {'host': parts[0]}

        if len(parts) == 2:
            subs['domain'] = parts[1]
        else:
            subs['sfx'] = 1

        return valu, {'subs':subs}

    def lift(self, name, text, cmp='='):

        valu = text.strip().lower()
        if not valu:
            return None

        indx = valu=[::-1]

        if indx[-1] == '*':
            return ('prop:pref', (name, indx[:-1]), {})

        return ('prop:eq', (name, indx), {'indx': indx})

        if valu[0] == '*':
            indx = valu[::-1]
            return ('prop:pref', (name, 

    def repr(self, valu):
        try:
            return valu.encode('utf8').decode('idna')
        except UnicodeError as e:
            if len(valu) >= 4 and valu[0:4] == 'xn--':
                logger.exception(msg='Failed to IDNA decode ACE prefixed inet:fqdn')
                return valu
            raise  # pragma: no cover

class NDefType(Type):

    def __init__(self, modl, name, **info):
        DataType.__init__(self, modl, name, **info)
        # TODO figure out what to do about modl vs core issues
        self._isTufoForm = getattr(modl, 'isTufoForm', None)
        self._getPropNorm = getattr(modl, 'getPropNorm', None)

    def norm(self, valu):

        if isinstance(valu, (list, tuple)):
            return self._norm_list(valu, oldval)

        if not isinstance(valu, str) or len(valu) < 1:
            self._raiseBadValu(valu)

        return self._norm_str(valu, oldval)

    def _norm_str(self, text, oldval=None):
        text = text.strip()
        if not text:
            self._raiseBadValu(text, mesg='No text left after strip().')

        if text[0] == '(':
            vals, off = s_syntax.parse_list(text)
            if off != len(text):  # pragma: no cover
                self._raiseBadValu(text, off=off, vals=vals,
                                   mesg='List parting for ndef type did not consume all of the input text.')
            return self._norm_list(vals, oldval)

        if not s_common.isguid(text):
            self._raiseBadValu(text, mesg='Expected a 32 char guid string')

        return text, {}

    def _norm_list(self, valu, oldval=None):

        if not valu:
            self._raiseBadValu(valu=valu, mesg='No valus present in list to make a guid with')

        form, fvalu = valu
        if not self._isTufoForm(form):
            self._raiseBadValu(valu=valu, form=form,
                               mesg='Form is not a valid form.')
        # NDefType specifically does not care about the subs since
        # they aren't useful for universal node identification
        fvalu, _ = self._getPropNorm(form, fvalu)
        retn = s_common.guid((form, fvalu))
        return retn, {}

class StrType(Type):

    def __init__(self, modl, name, **info):
        DataType.__init__(self, modl, name, **info)

        self.regex = None
        self.envals = None
        self.restrip = None
        self.frobintfmt = None

        self.strip = info.get('strip', 0)
        self.nullval = info.get('nullval')

        enumstr = info.get('enums')
        if enumstr is not None:
            self.envals = enumstr.split(',')

        regexp = info.get('regex')
        if regexp is not None:
            self.regex = regex.compile(regexp)

        restrip = info.get('restrip')
        if restrip is not None:
            self.restrip = regex.compile(restrip)

        frobintfmt = info.get('frob_int_fmt')
        if frobintfmt is not None:
            self.frobintfmt = frobintfmt

    def norm(self, valu, oldval=None):

        if self.frobintfmt and isinstance(valu, int):
            valu = self.frobintfmt % valu

        if not isinstance(valu, str):
            self._raiseBadValu(valu)

        if self.info.get('lower'):
            valu = valu.lower()

        if valu == self.nullval:
            return valu, {}

        if self.restrip:
            valu = self.restrip.sub('', valu)

        if self.strip:
            valu = valu.strip()

        if self.envals is not None and valu not in self.envals:
            self._raiseBadValu(valu, enums=self.info.get('enums'))

        if self.regex is not None and not self.regex.match(valu):
            self._raiseBadValu(valu, regex=self.info.get('regex'))

        return valu, {}

class JsonType(Type):

    def norm(self, valu, oldval=None):

        if not isinstance(valu, str):
            try:
                return json.dumps(valu, sort_keys=True, separators=(',', ':')), {}
            except Exception as e:
                self._raiseBadValu(valu, mesg='Unable to normalize object as json.')

        try:
            return json.dumps(json.loads(valu), sort_keys=True, separators=(',', ':')), {}
        except Exception as e:
            self._raiseBadValu(valu, mesg='Unable to norm json string')

class IntType(Type):

    def __init__(self, modl, name, **info):
        DataType.__init__(self, modl, name, **info)

        self.fmt = info.get('fmt', '%d')
        # self.modval = info.get('mod',None)
        self.minval = info.get('min', None)
        self.maxval = info.get('max', None)

        self.ismin = info.get('ismin', False)
        self.ismax = info.get('ismax', False)

        # cache the min or max function to avoid cond logic
        # during norm() for perf
        self.minmax = None

        if self.ismin:
            self.minmax = min

        elif self.ismax:
            self.minmax = max

    def repr(self, valu):
        return self.fmt % valu

    def norm(self, valu, oldval=None):

        if isinstance(valu, str):
            try:
                valu = int(valu, 0)
            except ValueError as e:
                self._raiseBadValu(valu, mesg='Unable to cast valu to int')

        if not isinstance(valu, int):
            self._raiseBadValu(valu, mesg='Valu is not an int')

        if valu < -9223372036854775808:
            self._raiseBadValu(valu, mesg='Value less than 64bit signed integer minimum (-9223372036854775808)')
        if valu > 9223372036854775807:
            self._raiseBadValu(valu, mesg='Value greater than 64bit signed integer maximum (9223372036854775807)')

        if oldval is not None and self.minmax:
            valu = self.minmax(valu, oldval)

        if self.minval is not None and valu < self.minval:
            self._raiseBadValu(valu, minval=self.minval)

        if self.maxval is not None and valu > self.maxval:
            self._raiseBadValu(valu, maxval=self.maxval)

        return valu, {}

jsseps = (',', ':')

def islist(x):
    return type(x) in (list, tuple)

class MultiFieldType(Type):

    def __init__(self, modl, name, **info):
        DataType.__init__(self, modl, name, **info)
        self.fields = None

    def _norm_fields(self, valu):

        fields = self._get_fields()

        if len(valu) != len(fields):
            self._raiseBadValu(valu, mesg='field count != %d' % (len(fields),))

        vals = []
        subs = {}

        for valu, (name, item) in s_common.iterzip(valu, fields):

            norm, fubs = item.norm(valu)

            vals.append(norm)

            subs[name] = norm
            for fubk, fubv in fubs.items():
                subs[name + ':' + fubk] = fubv

        return vals, subs

    def _get_fields(self):

        if self.fields is None:

            self.fields = []

            # maintain legacy "fields=" syntax for a bit yet...
            fields = self.info.get('fields')
            if fields is not None:
                if fields:
                    for part in fields.split('|'):
                        fname, ftype = part.split(',')
                        fitem = self.modl.getTypeInst(ftype)
                        if self.prop:
                            _fitem = self._getPropType(ftype)
                            if _fitem:
                                fitem = _fitem
                        self.fields.append((fname, fitem))

                return self.fields

            # process names= and types= info fields
            fnames = []
            ftypes = []

            fnstr = self.info.get('names')
            if fnstr:
                fnames.extend(fnstr.split(','))

            ftstr = self.info.get('types', '')
            if ftstr:
                ftypes.extend(ftstr.split(','))

            self.flen = len(ftypes)

            if len(fnames) != self.flen:
                raise s_common.BadInfoValu(name='types', valu=ftstr, mesg='len(names) != len(types)')

            for i in range(self.flen):
                item = self.modl.getTypeInst(ftypes[i])
                self.fields.append((fnames[i], item))

        return self.fields

def _splitpairs(text, sep0, sep1):
    '''
    Split parts via sep0 and then pairs by sep2
    '''
    for part in text.split(sep0):
        k, v = part.split(sep1)
        yield k.strip(), v.strip()

class CompType(Type):

    def __init__(self, modl, name, **info):
        DataType.__init__(self, modl, name, **info)
        self.fields = []
        self.optfields = []

        fstr = self.info.get('fields')
        if fstr:

            if fstr.find('=') != -1:
                self.fields.extend(_splitpairs(fstr, ',', '='))

            else:
                self.fields.extend(_splitpairs(fstr, '|', ','))

        self.fsize = len(self.fields)

        ostr = self.info.get('optfields')
        if ostr:
            self.optfields.extend(_splitpairs(ostr, ',', '='))
            # stabilize order to alphabetical since it effects
            # the eventual guid generation
            self.optfields.sort()

    def _norm_str(self, text, oldval=None):

        text = text.strip()

        if not text:
            self._raiseBadValu(text, mesg='No text left after strip().')

        if text[0] != '(':
            return self.modl.getTypeNorm('guid', text)

        vals, off = s_syntax.parse_list(text)
        if off != len(text):
            self._raiseBadValu(text, off=off, vals=vals,
                               mesg='List parting for comp type did not consume all of the input text.')

        return self._norm_list(vals)

    def _norm_list(self, valu, oldval=None):

        opts = {}
        subs = {}
        retn = []

        vlen = len(valu)

        if vlen < self.fsize:
            self._raiseBadValu(valu, mesg='Expected %d fields and got %d' % (self.fsize, len(valu)))

        for k, v in valu[self.fsize:]:
            opts[k] = v

        vals = valu[:self.fsize]
        for v, (name, tname) in s_common.iterzip(vals, self.fields):

            # FIXME - this if/else is a artifact of typelib/datamodel separation
            if self.prop:
                if self.modl.isTufoProp(tname):
                    norm, ssubs = self._getPropNorm(tname, v)
                else:
                    norm, ssubs = self.modl.getTypeNorm(tname, v)
            else:
                norm, ssubs = self.modl.getTypeNorm(tname, v)

            subs[name] = norm
            for subkey, subval in ssubs.items():
                subs[name + ':' + subkey] = subval
            retn.append(norm)

        for name, tname in self.optfields:

            v = opts.get(name)
            if v is None:
                continue

            norm, ssubs = self.modl.getTypeNorm(tname, v)

            subs[name] = norm
            for subkey, subval in ssubs.items():
                subs[name + ':' + subkey] = subval

            retn.append((name, norm))

        return s_common.guid(retn), subs

    def _norm_dict(self, valu, oldval=None):

        newv = []
        for name, ftype in self.fields:

            fval = valu.get(name)
            if fval is None:
                self._raiseBadValu(valu, mesg='missing field: %s' % (name,))

            newv.append(fval)

        for name, ftype in self.optfields:
            fval = valu.get(name)
            if fval is not None:
                newv.append((name, fval))

        return self._norm_list(newv)

    def norm(self, valu, oldval=None):

        # if it's already a guid, we have nothing to normalize...
        if isinstance(valu, str):
            return self._norm_str(valu, oldval=oldval)

        if isinstance(valu, dict):
            return self._norm_dict(valu, oldval=oldval)

        if not islist(valu):
            self._raiseBadValu(valu, mesg='Expected guid or list/tuple')

        return self._norm_list(valu)

class XrefType(Type):
    '''
    The XrefType allows linking a specific type of node to an inspecific
    set of node forms.

    Example Sub Type:

        addType('foo:barrefs', subof='xref', source='bar,foo:bar')

    '''

    def __init__(self, modl, name, **info):
        DataType.__init__(self, modl, name, **info)
        self._sorc_type = None
        self._sorc_name = None

        sorc = info.get('source')

        if sorc is not None:
            parts = sorc.split(',')
            if len(parts) != 2:
                raise s_common.BadInfoValu(name='source', valu=sorc, mesg='expected source=<name>,<type>')

            self._sorc_name = parts[0]
            self._sorc_type = parts[1]

    def norm(self, valu, oldval=None):

        if isinstance(valu, str):
            return self._norm_str(valu, oldval=oldval)

        if not islist(valu):
            self._raiseBadValu(valu, mesg='Expected guid, psv, or list')

        return self._norm_list(valu, oldval=None)

    def _norm_str(self, text, oldval=None):

        text = text.strip()

        if not text:
            self._raiseBadValu(text, mesg='No text left after strip().')

        if len(text) == 32 and text.find('=') == -1:
            return self.modl.getTypeNorm('guid', text)

        vals, off = s_syntax.parse_list(text)

        if off != len(text):
            self._raiseBadValu(text, off=off, vals=vals,
                               mesg='List parting for comp type did not consume all of the input text.')

        return self._norm_list(vals)

    def _norm_list(self, valu, oldval=None):

        if len(valu) != 2:
            self._raiseBadValu(valu, mesg='xref type requires 2 fields')

        valu, pvval = valu

        pvval, pvsub = self.modl.getTypeNorm('propvalu', pvval)

        tstr, tval = pvval.split('=', 1)

        valu, vsub = self.modl.getTypeNorm(self._sorc_type, valu)
        tval, tsub = self.modl.getTypeNorm(tstr, tval)

        tndef = s_common.guid((tstr, tval))
        iden = s_common.guid((valu, tstr, tval))

        subs = {
            self._sorc_name: valu,
            'xref:node': tndef,
            'xref': pvval,
        }

        for k, v in vsub.items():
            k = self._sorc_name + ':' + k
            subs[k] = v

        for k, v in pvsub.items():
            k = 'xref:' + k
            subs[k] = v

        return iden, subs

class TimeType(Type):
    # FIXME subfields for various time parts (year,month,etc)

    def __init__(self, modl, name, **info):

        DataType.__init__(self, modl, name, **info)

        self.ismin = info.get('ismin', False)
        self.ismax = info.get('ismax', False)

        self.minmax = None

        if self.ismin:
            self.minmax = min

        elif self.ismax:
            self.minmax = max

    def norm(self, valu, oldval=None):

        subs = {}

        # make the string into int form then apply our min/max
        if isinstance(valu, str):
            valu, subs = self._norm_str(valu, oldval=oldval)

        if oldval is not None and self.minmax:
            valu = self.minmax(valu, oldval)

        return valu, subs

    def _norm_str(self, text, oldval=None):
        if text.strip().lower() == 'now':
            return s_common.now(), {}
        return s_time.parse(text), {}

    def repr(self, valu):
        return s_time.repr(valu)

class SeprType(MultiFieldType):

    def __init__(self, modl, name, **info):
        MultiFieldType.__init__(self, modl, name, **info)
        self.sepr = info.get('sep', ',')
        self.reverse = info.get('reverse', 0)

    def norm(self, valu, oldval=None):
        subs = {}
        reprs = []

        if isinstance(valu, str):
            valu = self._split_str(valu)

        # only other possiblity should be that it was a list
        for part, (name, tobj) in self._zipvals(valu):

            if tobj == self:
                norm, nsub = part, {}
                reprs.append(norm)
            else:
                norm, nsub = tobj.norm(part)
                reprs.append(tobj.repr(norm))

            subs[name] = norm
            for subn, subv in nsub.items():
                subs['%s:%s' % (name, subn)] = subv

        return self.sepr.join(reprs), subs

    def _split_str(self, text):

        fields = self._get_fields()

        if self.reverse:
            parts = text.rsplit(self.sepr, len(fields) - 1)
        else:
            parts = text.split(self.sepr, len(fields) - 1)

        if len(parts) != len(fields):
            self._raiseBadValu(text, sep=self.sepr, mesg='split: %d fields: %d' % (len(parts), len(fields)))

        return parts

    def _zipvals(self, vals):
        return s_common.iterzip(vals, self._get_fields())

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
            self._raiseBadValu(valu)

        return retn, subs

class StormType(Type):

    def norm(self, valu, oldval=None):
        try:
            s_syntax.parse(valu)
        except Exception as e:
            self._raiseBadValu(valu)
        return valu, {}

class PermType(Type):
    '''
    Enforce that the permission string and options are known.
    '''
    def norm(self, valu, oldval=None):

        try:
            pnfo, off = s_syntax.parse_perm(valu)
        except Exception as e:
            self._raiseBadValu(valu)

        if off != len(valu):
            self._raiseBadValu(valu)
        return valu, {}

class PropValuType(Type):
    def __init__(self, modl, name, **info):
        Type.__init__(self, modl, name, **info)

    def norm(self, valu, oldval=None):
        # if it's already a str, we'll need to split it into its two parts to norm.
        if isinstance(valu, str):
            return self._norm_str(valu, oldval=oldval)

        if not islist(valu):
            self._raiseBadValu(valu, mesg='Expected str or list/tuple.')

        return self._norm_list(valu)

    def _norm_str(self, text, oldval=None):

        text = text.strip()

        if not text:
            self._raiseBadValu(text, mesg='No text left after strip().')

        if '=' not in text:
            self._raiseBadValu(text, mesg='PropValu is missing a =')

        valu = text.split('=', 1)

        return self._norm_list(valu)

    def _norm_list(self, valu, oldval=None):
        if len(valu) != 2:
            self._raiseBadValu(valu=valu, mesg='PropValu requires two values to norm.')

        prop, valu = valu

        try:
            nvalu, nsubs = self._reqPropNorm(prop, valu, oldval=oldval)
        except (s_common.BadTypeValu, s_common.NoSuchProp) as e:
            logger.exception('Failed to norm PropValu.')
            self._raiseBadValu(valu, mesg='Unable to norm PropValu', prop=prop)

        subs = {'prop': prop}
        if isinstance(nvalu, str):
            subs['strval'] = nvalu
        else:
            subs['intval'] = nvalu

        nrepr = self._getPropRepr(prop, nvalu)
        retv = '='.join([prop, nrepr])
        return retv, subs


class TypeLib:
    '''
    An extensible type library for use in cortex data models.
    '''
    def __init__(self, load=True):
        self.types = {}
        self.casts = {}
        self.typeinfo = {}
        self.typetree = {}
        self.subscache = {}
        self.modlnames = set()

        # pend creation of subtypes for non-existant base types
        # until the base type gets loaded.
        self.pended = collections.defaultdict(list)

        self.addType('str', ctor='synapse.lib.types.StrType', doc='The base string type')
        self.addType('int', ctor='synapse.lib.types.IntType', doc='The base integer type')
        self.addType('bool', ctor='synapse.lib.types.BoolType', doc='A boolean type')
        self.addType('json', ctor='synapse.lib.types.JsonType', doc='A json type (stored as str)')

        self.addType('guid', ctor='synapse.lib.types.GuidType', doc='A Globally Unique Identifier type')
        self.addType('sepr', ctor='synapse.lib.types.SeprType',
                     doc='A multi-field composite type which uses separated repr values')
        self.addType('comp', ctor='synapse.lib.types.CompType',
                     doc='A multi-field composite type which generates a stable guid from normalized fields')
        self.addType('xref', ctor='synapse.lib.types.XrefType',
                     doc='A multi-field composite type which can be used to link a known form to an unknown form')
        self.addType('time', ctor='synapse.lib.types.TimeType',
                     doc='Timestamp in milliseconds since epoch', ex='20161216084632')
        self.addType('ndef', ctor='synapse.lib.types.NDefType',
                     doc='The type used for normalizing node:ndef values.')

        self.addType('syn:tag', ctor='synapse.lib.types.TagType', doc='A synapse tag', ex='foo.bar')
        self.addType('syn:perm', ctor='synapse.lib.types.PermType', doc='A synapse permission string')
        self.addType('syn:storm', ctor='synapse.lib.types.StormType', doc='A synapse storm query string')
        self.addType('propvalu', ctor='synapse.lib.types.PropValuType', ex='foo:bar=1234',
                     doc='An equal sign delimited property/valu combination.',)

        # add base synapse types
        self.addType('syn:core', subof='str')
        self.addType('syn:prop', subof='str', regex=r'^([\w]+:)*([\w]+|\*)$', lower=1)
        self.addType('syn:type', subof='str', regex=r'^([\w]+:)*[\w]+$', lower=1)
        self.addType('syn:glob', subof='str', regex=r'^([\w]+:)*[\w]+:\*$', lower=1)

        self.addType('int:min', subof='int', ismin=1)
        self.addType('int:max', subof='int', ismax=1)

        self.addType('str:lwr', subof='str', lower=1, strip=1)
        self.addType('str:txt', subof='str', doc='Multi-line text or text blob.')
        self.addType('str:hex', subof='str', frob_int_fmt='%x', regex=r'^[0-9a-f]+$', lower=1)

        self.addTypeCast('country:2:cc', self._castCountry2CC)
        self.addTypeCast('int:2:str10', self._castMakeInt10)
        self.addTypeCast('make:guid', self._castMakeGuid)
        self.addTypeCast('make:json', self._castMakeJson)

        if load:
            self.loadModModels()

    #def addTypeDef(self, 
    #def addPropDef(self, form, prop, 

    def _castCountry2CC(self, valu):
        valu = valu.replace('.', '').lower()
        return s_l_iso3166.country2iso.get(valu)

    def _castMakeGuid(self, valu):
        return s_common.guid(valu)

    def _castMakeJson(self, valu):
        valu = json.dumps(valu, sort_keys=True, separators=(',', ':'))
        return valu

    def _castMakeInt10(self, valu):
        if isinstance(valu, int):
            valu = str(valu)
            return valu
        return valu

    def getTypeInst(self, name):
        '''
        Return the Type instance for the given type name.

        Example:

            dtype = modl.getTypeInst('foo:bar')

        NOTE: This API returns non-primitive objects and can not be
              used over telepath RMI.
        '''
        return self.types.get(name)

    def getTypeBases(self, name):
        '''
        Return a list of type inheritence names beginning with the base type.

        Example:

            for base in tlib.getTypeBases('foo:minval'):
                print('base type: %s' % (name,))

        '''
        done = [name]

        todo = self.typetree.get(name)
        while todo is not None:
            done.append(todo)
            todo = self.typetree.get(todo)

        done.reverse()
        return done

    def isSubType(self, name, base):
        '''
        Returns True if the given type name is a sub-type of the base name.

        Example:

            if modl.isSubType('foo','str'):
                dostuff()

        '''
        key = (name, base)

        ret = self.subscache.get(key)
        if ret is None:
            ret = base in self.getTypeBases(name)
            self.subscache[key] = ret

        return ret

    def addDataModels(self, modtups):
        '''
        Load a list of (name,model) tuples.

        Args:
            modtups ([(str,dict)]): A list of (name,modl) tuples.

        Returns:
            (None)

        NOTE: This API loads all types first and may therefor be used to
              prevent type dependency ordering issues between multiple models.

        '''
        return self._addDataModels(modtups)

    def addDataModel(self, name, modl):
        return self.addDataModels([(name, modl)])

    def isDataModl(self, name):
        '''
        Return True if the given data model name exists.

        Args:
            name (str): The name of the data model

        Returns:
            (boolean):  True if the model exists
        '''
        return name in self.modlnames

    def _addDataModels(self, modtups):
        for modname, moddict in modtups:
            self.modlnames.add(modname)
            # add all base types first to simplify deps
            for name, info in moddict.get('types', ()):
                try:
                    self.addType(name, **info)
                except Exception as e:
                    logger.exception('type %s: %s' % (name, e))

    def loadModModels(self):

        dynmodls = s_modules.call_ctor('getBaseModels')

        models = []
        for name, modls, excp in dynmodls:
            if not modls:
                logger.warning('dyn model empty: %r %r' % (name, excp))
                continue

            models.extend(modls)

        self.addDataModels(models)

    def _bumpBasePend(self, name):
        for name, info in self.pended.pop(name, ()):
            try:
                self.addType(name, **info)
            except Exception as e:
                logger.exception('pended: addType %s' % name)

    def getType(self, name):
        '''
        Return the Type subclass for the given type name.
        '''
        return self.types.get(name)

    def isType(self, name):
        '''
        Return boolean which is true if the given name is a data type.

        Example:

            if modl.isType('foo:bar'):
                dostuff()

        '''
        return self.types.get(name) is not None

    def reqDataType(self, name):
        '''
        Return a reference to the named DataType or raise NoSuchType.

        Args:
            name (str): Name of the type to get a reference for.

        Returns:
            DataType: Instance of a DataType for that name.

        Raises:
            NoSuchType: If the type is not valid.
        '''
        item = self.getDataType(name)
        if item is None:
            raise s_common.NoSuchType(name=name)
        return item

    def addType(self, name, **info):
        '''
        Add a type to the cached types.

        Args:
            name (str): Name of the type to add.
            **info (dict): Type properties to include.

        Example:
            Add a new foo:bar type::

                modl.addType('foo:bar', subof='str', doc='A foo bar.')

        Raises:
            DupTypeName: If the type already exists.

        '''
        if self.types.get(name) is not None:
            raise s_common.DupTypeName(name=name)

        ctor = info.get('ctor')
        subof = info.get('subof')
        if ctor is None and subof is None:
            raise Exception('addType must have either ctor= or subof=')

        if ctor is not None:
            self.typeinfo[name] = info

            try:
                item = s_dyndeps.tryDynFunc(ctor, self, name, **info)
                self.types[name] = item
                self._bumpBasePend(name)
                return True

            except Exception as e:
                logger.warning('failed to ctor type %s', name, exc_info=True)
                logger.debug('failed to ctor type %s', name, exc_info=True)
                self.typeinfo.pop(name, None)
        try:

            base = self.reqDataType(subof)
            # inherit docs and examples from parent types
            self.typeinfo[name] = info
            item = base.extend(name, **info)

            self.types[name] = item

            self._bumpBasePend(name)
            self.typetree[name] = subof
            self.subscache.clear()
            return True

        except s_common.NoSuchType as e:
            tnam = e.errinfo.get('name')
            self.typeinfo.pop(name, None)
            self.pended[tnam].append((name, info))
            return False

    #def getTypeDefs(self):
        #'''
        #Return a list of (name,info) tuples for all the types.

        #Returns:
            #([(name,info)]):    The loaded types
        #'''
        #return list(self.typeinfo.items())

    def getTypeDef(self, name):
        '''
        Get the definition for a given type.

        Args:
            name (str): Name of the type to look up.

        Examples:
            Do stuff with the type definition of 'int'::

                tdef = modl.getTypeDef('int')
                dostuff(tdef)

        Returns:
            ((str, dict)): The type definition tufo. The str is the name of the type, and the dictionary are any type
             options (ctor and subof values). If the name is not a registered type, this is None.
        '''
        info = self.typeinfo.get(name)
        if info is None:
            return None
        return (name, info)

    def getTypeInfo(self, name, prop, defval=None):
        '''
        A helper to return an info prop for the type or it's parents.

        Example:

            ex = modl.getTypeInfo('inet:tcp4','ex')

        '''
        todo = name
        while todo is not None:

            info = self.typeinfo.get(todo)
            if info is None:
                return defval

            ret = info.get(prop)
            if ret is not None:
                return ret

            todo = info.get('subof')

        return defval

    def getTypeNorm(self, name, valu, oldval=None):
        '''
        Normalize a type specific value in system mode.

        Example:

            fqdn,subs = modl.getTypeNorm('inet:fqdn','Foo.Com')

        '''
        return self.reqDataType(name).norm(valu, oldval=oldval)

    def getTypeCast(self, name, valu):
        '''
        Use either a type or a registered "cast" name to normalize
        the given input.

        Example:

            valu = modl.getTypeCast("foo:bar","hehe")

        '''
        func = self.casts.get(name)
        if func is not None:
            return func(valu)

        return self.getTypeNorm(name, valu)[0]

    def addTypeCast(self, name, func):
        '''
        Add a "cast" function to do normalization without
        creating a complete type.
        '''
        self.casts[name] = func

    def getTypeRepr(self, name, valu):
        '''
        Return the humon readable form of the given type value.

        Example:

            print( tlib.getTypeRepr('inet:ipv4', ipv4addr) )

        '''
        return self.reqDataType(name).repr(valu)

    def getTypeParse(self, name, text):
        '''
        Parse input text for the given type into it's system form.

        Example:

            ipv4,subs = tlib.getTypeParse('inet:ipv4','1.2.3.4')

        '''
        return self.reqDataType(name).parse(text)
