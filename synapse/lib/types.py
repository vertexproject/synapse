from __future__ import absolute_import,unicode_literals

import re
import json
import base64
import hashlib
import logging
import collections

import synapse.compat as s_compat
import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus
import synapse.lib.modules as s_modules

from synapse.common import *

logger = logging.getLogger(__name__)

class DataType:

    subprops = ()

    def __init__(self, tlib, name, **info):
        self.tlib = tlib
        self.name = name
        self.info = info
        reqStorDict(info)

    def _raiseBadValu(self, valu, **info):
        raise BadTypeValu(name=self.name, valu=valu, **info)

    def get(self, prop, defval=None):
        '''
        Retrieve a type info property from this type or parent types.

        Example:

            ex = item.get('doc')

        '''
        return self.tlib.getTypeInfo(self.name,prop,defval=defval)

    def subs(self):
        '''
        Implement if the presence of a property with this type requires sub props.
        '''
        return self.subprops

    def extend(self, name, **info):
        '''
        Construct a new subtype from this instance.
        '''
        for k,v in self.info.items():
            info.setdefault(k,v)

        return self.__class__(self.tlib, name,**info)

    def frob(self, valu, oldval=None):
        '''
        Attempt to take either repr *or* system form and normalize.

        Example:

            valu = tobj.frob(valu)

        Note:

            This API is mostly for use in simplifying parser / syntax
            use cases and should be avoided if input abiguity is not required.

        '''
        return self.norm(valu, oldval=oldval)

    def parse(self, text, oldval=None):
        '''
        Parse input text and return the system mode (normalized) value for the type.

        Example:

            valu = tobj.parse(text)

        '''
        return self.norm(text, oldval=oldval)

    def repr(self, valu):
        return valu

class StrType(DataType):

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        self.regex = None
        self.envals = None
        self.restrip = None
        self.frobintfmt = None

        self.nullval = info.get('nullval')

        enumstr = info.get('enums')
        if enumstr != None:
            self.envals = enumstr.split(',')

        regex = info.get('regex')
        if regex != None:
            self.regex = re.compile(regex)

        restrip = info.get('restrip')
        if restrip != None:
            self.restrip = re.compile(restrip)

        frobintfmt = info.get('frob_int_fmt')
        if frobintfmt != None:
            self.frobintfmt = frobintfmt

    def frob(self, valu, oldval=None):
        if self.frobintfmt and s_compat.isint(valu):
                valu = self.frobintfmt % valu
        return self.norm(valu, oldval=oldval)

    def norm(self, valu, oldval=None):

        if not s_compat.isstr(valu):
            self._raiseBadValu(valu)

        if self.info.get('lower'):
            valu = valu.lower()

        if valu == self.nullval:
            return valu,{}

        if self.envals != None and valu not in self.envals:
            self._raiseBadValu(valu,enums=self.info.get('enums'))

        if self.regex != None and not self.regex.match(valu):
            self._raiseBadValu(valu,regex=self.info.get('regex'))

        return valu,{}

    def parse(self, text, oldval=None):
        if self.restrip:
            text = self.restrip.sub('', text)

        return self.norm(text, oldval=oldval)

class JsonType(DataType):

    def frob(self, valu, oldval=None):
        if not s_compat.isstr(valu):
            return json.dumps(valu,separators=(',', ':')),{}

        return self.norm(valu,oldval=None)

    def norm(self, valu, oldval=None):
        try:
            return json.dumps( json.loads(valu), separators=(',', ':') ),{}
        except Exception as e:
            self._raiseBadValu(valu)

class IntType(DataType):

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        self.fmt = info.get('fmt','%d')
        #self.modval = info.get('mod',None)
        self.minval = info.get('min',None)
        self.maxval = info.get('max',None)

        self.ismin = info.get('ismin',False)
        self.ismax = info.get('ismax',False)

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

        if not s_compat.isint(valu):
            self._raiseBadValu(valu)

        if oldval != None and self.minmax:
            valu = self.minmax(valu,oldval)

        if self.minval != None and valu < self.minval:
            self._raiseBadValu(valu,minval=self.minval)

        if self.maxval != None and valu > self.maxval:
            self._raiseBadValu(valu,maxval=self.maxval)

        return valu,{}

    def parse(self, valu, oldval=None):
        try:
            valu = int(valu,0)
        except Exception as e:
            raise self._raiseBadValu(valu)

        return self.norm(valu)

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            valu,_ = self.parse(valu, oldval=oldval)
        return self.norm(valu, oldval=oldval)

def enMsgB64(item):
    # FIXME find a way to go directly from binary bytes to
    # base64 *string* to avoid the extra decode pass..
    return base64.b64encode(msgenpack(item)).decode('utf8')

def deMsgB64(text):
    # FIXME see above
    return msgunpack(base64.b64decode(text.encode('utf8')))

jsseps = (',',':')

def islist(x):
    return type(x) in (list,tuple)

class CompType(DataType):

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        fields = []

        fieldstr = info.get('fields','')
        if fieldstr:
            try:
                for fpair in fieldstr.split('|'):
                    fname,ftype = fpair.split(',')
                    fields.append( (fname,ftype) )

            except Exception as e:
                raise BadInfoValu(name='fields',valu=fieldstr,mesg='expected: <propname>,<typename>[|...]')

        # each of our composit sub-fields is a sub-prop if wanted
        self.fields = []
        self.subprops = []

        for fname,tnam in fields:
            if tnam == name:
                # this is a recursive type, so can't fetch its definition yet.
                # fortunately, that definition is us!
                tobj = self
            else:
                tobj = self.tlib.reqDataType(tnam)
            self.fields.append((fname,tobj))

            self.subprops.append( tufo(fname,ptype=tnam) )
            if tnam != name:
                # don't support subprops on recursive fields, or we'll infinite loop.
                for subp in tobj.subs():
                    subn = '%s:%s' % (fname,subp[0])
                    self.subprops.append( tufo(subn,**subp[1]) )

    def norm(self, valu, oldval=None):
        '''handles both b64 blob *and* (text,text,text) list/tuple.'''
        if islist(valu):
            vals = valu
        else:
            vals = deMsgB64(valu)

        norms,subs = [], {}
        for v,(name,tobj) in self._zipvals(vals):

            nval,nsub = tobj.norm(v)
            norms.append(nval)
            subs[name] = nval

            for subn,subv in nsub.items():
                subs['%s:%s' % (name,subn)] = subv

        return enMsgB64(norms),subs

    def frob(self, valu, oldval=None):
        if islist(valu):
            vals = valu
        else:
            vals = deMsgB64(valu)

        frobs,subs = [], {}
        for v,(name,tobj) in self._zipvals(vals):

            nval,nsub = tobj.frob(v)
            frobs.append(nval)

            subs[name] = nval
            for subn,subv in nsub.items():
                subs['%s:%s' % (name,subn)] = subv

        return enMsgB64(frobs),subs

    def repr(self, valu):
        vals = deMsgB64(valu)
        reps = [ t.repr(v) for v,(n,t) in self._zipvals(vals) ]
        return json.dumps(reps,separators=jsseps)

    def parse(self, text, oldval=None):
        '''handles both text *and* (text,text,text) list/tuple.'''

        if islist(text):
            reps = text
        else:
            reps = json.loads(text)

        vals = [ t.parse(r)[0] for r,(n,t) in self._zipvals(reps) ]
        return enMsgB64(vals),{}


    def _zipvals(self, vals):
        return s_compat.iterzip(vals,self.fields)

class SeprType(CompType):

    def __init__(self, tlib, name, **info):
        CompType.__init__(self, tlib, name, **info)
        self.sepr = info.get('sep',',')
        self.reverse = info.get('reverse',0)

    def norm(self, valu, oldval=None):
        subs = {}
        reprs = []
        parts = self._split_str(valu)

        for part,(name,tobj) in self._zipvals(parts):

            if tobj == self:
                norm,nsub = part, {}
                reprs.append(norm)
            else:
                norm,nsub = tobj.parse(part)
                reprs.append(tobj.repr(norm))

            subs[name] = norm
            for subn,subv in nsub.items():
                subs['%s:%s' % (name,subn)] = subv

        return self.sepr.join(reprs),subs

    def frob(self, valu, oldval=None):
        subs = {}
        reprs = []
        if not islist(valu):
            parts = self._split_str(valu)
        else:
            parts = valu

        for part,(name,tobj) in self._zipvals(parts):
            if tobj == self:
                norm, nsub = part, {}
                reprs.append(norm)
            else:
                frob,nsub = tobj.frob(part)
                reprs.append(tobj.repr(frob))

            subs[name] = frob
            for subn,subv in nsub.items():
                subs['%s:%s' % (name,subn)] = subv

        return self.sepr.join(reprs),subs

    def parse(self, text, oldval=None):
        return self.norm(text, oldval=None)

    def repr(self, valu, oldval=None):
        return valu

    def _split_str(self, text):

        if self.reverse:
            parts = text.rsplit(self.sepr,len(self.fields)-1)
        else:
            parts = text.split(self.sepr,len(self.fields)-1)

        return parts

    def _zipvals(self, vals):
        return s_compat.iterzip(vals,self.fields)

class BoolType(DataType):

    def norm(self, valu, oldval=None):
        return int(bool(valu)),{}

    def repr(self, valu):
        return repr(bool(valu))

    def parse(self, text, oldval=None):
        text = text.lower()
        if text in ('true','t','y','yes','1','on'):
            return 1,{}

        if text in ('false','f','n','no','0','off'):
            return 0,{}

        self._raiseBadValu(text)

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            return self.parse(valu, oldval=oldval)
        return self.norm(valu, oldval=oldval)

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

        # pend creation of subtypes for non-existant base types
        # until the base type gets loaded.
        self.pended = collections.defaultdict(list)

        self.addType('str',ctor='synapse.lib.types.StrType', doc='The base string type')
        self.addType('int',ctor='synapse.lib.types.IntType', doc='The base integer type')
        self.addType('bool',ctor='synapse.lib.types.BoolType', doc='A boolean type')
        self.addType('json',ctor='synapse.lib.types.JsonType', doc='A json type (stored as str)')

        self.addType('comp',ctor='synapse.lib.types.CompType', doc='A multi-field composite type which uses base64 encoded msgpack')
        self.addType('sepr',ctor='synapse.lib.types.SeprType', doc='A multi-field composite type which uses separated repr values')

        # add base synapse types
        self.addType('syn:tag',subof='str', regex=r'^([\w]+\.)*[\w]+$', lower=1)
        self.addType('syn:prop',subof='str', regex=r'^([\w]+:)*([\w]+|\*)$', lower=1)
        self.addType('syn:type',subof='str', regex=r'^([\w]+:)*[\w]+$', lower=1)
        self.addType('syn:glob',subof='str', regex=r'^([\w]+:)*[\w]+:\*$', lower=1)

        self.addType('guid',subof='str', regex='^[0-9a-f]{32}$', lower=1, restrip='[-]')

        self.addType('int:min', subof='int', ismin=1)
        self.addType('int:max', subof='int', ismax=1)

        self.addType('str:lwr', subof='str', lower=1)
        self.addType('str:txt', subof='str', doc='Multi-line text or text blob.')
        self.addType('str:hex', subof='str', frob_int_fmt='%x', regex=r'^[0-9a-f]+$', lower=1)

        self.addTypeCast('make:guid', self._castMakeGuid )

        if load:
            self.loadModModels()

    def _castMakeGuid(self, valu):
        return hashlib.md5(valu.encode('utf8')).hexdigest()

    def getTypeInst(self, name):
        '''
        Return the DataType instance for the given type name.

        Example:

            dtype = tlib.getTypeInst('foo:bar')

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
        while todo != None:
            done.append(todo)
            todo = self.typetree.get(todo)

        done.reverse()
        return done

    def isSubType(self, name, base):
        '''
        Returns True if the given type name is a sub-type of the base name.

        Example:

            if tlib.isSubType('foo','str'):
                dostuff()

        '''
        key = (name,base)

        ret = self.subscache.get(key)
        if ret == None:
            ret = base in self.getTypeBases(name)
            self.subscache[key] = ret

        return ret

    def loadDataModels(self, modtups):
        '''
        Load a list of (name,model) tuples into the TypeLib.
        '''
        subtodo = []

        for modname,moddict in modtups:
            # add all base types first to simplify deps
            for name,info in moddict.get('types',()):
                try:
                    self.addType(name,**info)
                except Exception as e:
                    logger.exception('type %s: %s' % (name, e))

    def loadModModels(self):

        modls = s_modules.call('getDataModel')

        models = [ (name,modl) for (name,modl,excp) in modls if modl != None ]

        self.loadDataModels(models)

    def _bumpBasePend(self, name):
        for name,info in self.pended.pop(name,()):
            try:
                self.addType(name,**info)
            except Exception as e:
                logger.exception('pended: addType %s' % (name,), e)

    def getDataType(self, name):
        '''
        Return the DataType subclass for the given type name.
        '''
        return self.types.get(name)

    def reqDataType(self, name):
        '''
        Return a reference to the named DataType or raise NoSuchType.
        '''
        item = self.getDataType(name)
        if item == None:
            raise NoSuchType(name=name)
        return item

    def addType(self, name, **info):
        '''
        '''
        if self.types.get(name) != None:
            raise DupTypeName(name=name)

        ctor = info.get('ctor')
        subof = info.get('subof')
        if ctor == None and subof == None:
            raise Exception('addType must have either ctor= or subof=')

        if ctor != None:
            self.typeinfo[name] = info

            try:
                item = s_dyndeps.tryDynFunc(ctor,self,name,**info)
                self.types[name] = item
                self._bumpBasePend(name)
                return True

            except Exception as e:
                logger.warning('failed to ctor type %s', name, exc_info=True)
                logger.debug('failed to ctor type %s', name, exc_info=True)
                self.typeinfo.pop(name,None)
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

        except NoSuchType as e:
            tnam = e.errinfo.get('name')
            self.typeinfo.pop(name,None)
            self.pended[tnam].append( (name,info) )
            return False

    def getTypeInfo(self, name, prop, defval=None):
        '''
        A helper to return an info prop for the type or it's parents.

        Example:

            ex = tlib.getTypeInfo('inet:tcp4','ex')

        '''
        todo = name
        while todo != None:

            info = self.typeinfo.get(todo)
            if info == None:
                return defval

            ret = info.get(prop)
            if ret != None:
                return ret

            todo = info.get('subof')

        return defval

    def getTypeNorm(self, name, valu, oldval=None):
        '''
        Normalize a type specific value in system mode.

        Example:

            fqdn,subs = tlib.getTypeNorm('inet:fqdn','Foo.Com')

        '''
        return self.reqDataType(name).norm(valu, oldval=oldval)

    def getTypeFrob(self, name, valu, oldval=None):
        '''
        Return a system normalized value for the given input value which
        may be in system mode or in display mode.

        Returns None,{} on Exception

        Example:

            valu,subs = tlib.getTypeFrob('inet:ipv4',valu)

        '''
        try:
            return self.reqDataType(name).frob(valu, oldval=oldval)
        except Exception as e:
            logger.warn(e)
            return None,{}

    def getTypeCast(self, name, valu):
        '''
        Use either a type or a registered "cast" name to normalize
        the given input.

        Example:

            valu = tlib.getTypeCast("foo:bar","hehe")

        '''
        func = self.casts.get(name)
        if func != None:
            return func(valu)

        return self.getTypeNorm(name,valu)[0]

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
