from __future__ import absolute_import,unicode_literals

import re
import json
#import time
import base64
import collections
#import socket
#import struct
import logging
#import datetime

import synapse.compat as s_compat
import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus
import synapse.lib.modules as s_modules

from synapse.common import *

logger = logging.getLogger(__name__)

def syntype(name,ctor,**info):
    return (name,ctor,info)
    
def subtype(name,subof,**info):
    # syntax sugar for model constructors
    return (name,subof,info)

class DataType:

    subprops = ()

    def __init__(self, tlib, name, **info):
        self.tlib = tlib
        self.name = name
        self.info = info
        reqStorDict(info)

    def _raiseBadValu(self, valu, **info):
        raise BadTypeValu(name=self.name, valu=valu, **info)

    def subs(self):
        '''
        Implement if the presence of a property with this type requires sub props.
        '''
        return self.subprops

    def chop(self, valu):
        '''
        Returns a tuple of (norm,subs) for the given valu.
        '''
        return self.norm(valu),{}

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
        return str(valu)

class StrType(DataType):

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        self.regex = None
        self.envals = None
        self.restrip = None

        enumstr = info.get('enums')
        if enumstr != None:
            self.envals = enumstr.split(',')

        regex = info.get('regex')
        if regex != None:
            self.regex = re.compile(regex)
        restrip = info.get('restrip')
        if restrip != None:
            self.restrip = re.compile(restrip)

    def norm(self, valu, oldval=None):

        if not s_compat.isstr(valu):
            self._raiseBadValu(valu)

        if self.info.get('lower'):
            valu = valu.lower()

        if self.envals != None and valu not in self.envals:
            self._raiseBadValu(valu,enums=self.info.get('enums'))

        if self.regex != None and not self.regex.match(valu):
            self._raiseBadValu(valu,regex=self.info.get('regex'))

        return valu

    def parse(self, text, oldval=None):
        if self.restrip:
            text = self.restrip.sub('', text)

        return self.norm(text, oldval=oldval)


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

        return valu

    def parse(self, valu, oldval=None):
        try:
            valu = int(valu,0)
        except Exception as e:
            raise self._raiseBadValu(valu)

        return self.norm(valu)

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            valu = self.parse(valu, oldval=oldval)
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
        self.subprops = []
        self.comptypes = []

        for name,tnam in fields:
            tobj = self.tlib.getDataType(tnam)
            self.comptypes.append((name,tobj))

            self.subprops.append( tufo(name,ptype=tnam) )
            for subp in tobj.subs():
                subn = '%s:%s' % (name,subp[0])
                self.subprops.append( tufo(subn,**subp[1]) )

    def norm(self, valu, oldval=None):
        # NOTE: handles both b64 blob *and* (text,text,text) list/tuple.
        if islist(valu):
            vals = valu
        else:
            vals = deMsgB64(valu)

        norms = [ t.norm(v) for v,(n,t) in self._zipvals(vals) ]
        return enMsgB64(norms)

    def chop(self, valu):
        # NOTE: handles both b64 blob *and* (text,text,text) list/tuple.
        if islist(valu):
            vals = valu
        else:
            vals = deMsgB64(valu)

        subs = {}
        norms = []

        for v,(name,tobj) in self._zipvals(vals):

            nval,nsub = tobj.chop(v)
            norms.append(nval)

            subs[name] = nval
            for subn,subv in nsub.items():
                subs['%s:%s' % (name,subn)] = subv

        return enMsgB64(norms),subs

    def repr(self, valu):
        vals = deMsgB64(valu)
        reps = [ t.repr(v) for v,(n,t) in self._zipvals(vals) ]
        return json.dumps(reps,separators=jsseps)

    def parse(self, text, oldval=None):

        # NOTE: handles both text *and* (text,text,text) list/tuple.

        if islist(text):
            reps = text
        else:
            reps = json.loads(text)

        vals = [ t.parse(r) for r,(n,t) in self._zipvals(reps) ]
        return enMsgB64(vals)

    def frob(self, valu, oldval=None):
        if islist(valu):
            vals = valu
        else:
            vals = deMsgB64(valu)

        frobs = [ t.frob(v) for v,(n,t) in self._zipvals(vals) ]
        return enMsgB64(frobs)

    def _zipvals(self, vals):
        return s_compat.iterzip(vals,self.comptypes)

class BoolType(DataType):

    def norm(self, valu, oldval=None):
        return int(bool(valu))

    def repr(self, valu):
        return repr(bool(valu))

    def parse(self, text, oldval=None):
        text = text.lower()
        if text in ('true','t','y','yes','1','on'):
            return 1

        if text in ('false','f','n','no','0','off'):
            return 0

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
        self.typedefs = {}

        # pend creation of subtypes for non-existant base types
        # until the base type gets loaded.
        self.pended = collections.defaultdict(list)

        self.addType('str',ctor='synapse.lib.types.StrType')
        self.addType('int',ctor='synapse.lib.types.IntType')
        self.addType('bool',ctor='synapse.lib.types.BoolType')
        self.addType('comp',ctor='synapse.lib.types.CompType')

        # add base synapse types
        self.addType('syn:tag',subof='str', regex=r'^([\w]+\.)*[\w]+$', lower=1)
        self.addType('syn:prop',subof='str', regex=r'^([\w]+:)*[\w]+$', lower=1)
        self.addType('syn:type',subof='str', regex=r'^([\w]+:)*[\w]+$', lower=1)
        self.addType('syn:glob',subof='str', regex=r'^([\w]+:)*[\w]+:\*$', lower=1)

        self.addType('guid',subof='str', regex='^[0-9a-f]{32}$', lower=1, restrip='[-]')

        self.addType('int:min', subof='int', ismin=1)
        self.addType('int:max', subof='int', ismax=1)

        self.addType('str:lwr', subof='str', lower=1)
        self.addType('str:txt', subof='str', doc='Multi-line text or text blob.')

        if load:
            self.loadModModels()

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
            item = s_dyndeps.tryDynFunc(ctor,self,name)
            self.types[name] = item
            self._bumpBasePend(name)
            return True

        if not self.types.get(subof):
            self.pended[subof].append( (name,info) )
            return False

        base = self.reqDataType(subof)
        item = base.extend(name, **info)
        self.types[name] = item

        self._bumpBasePend(name)
        return True

    def getTypeNorm(self, name, valu, oldval=None):
        '''
        Normalize a type specific value in system mode.

        Example:

            fqdn = tlib.getTypeNorm('inet:fqdn','Foo.Com')

        '''
        return self.reqDataType(name).norm(valu, oldval=oldval)

    def getTypeFrob(self, name, valu, oldval=None):
        '''
        Return a system normalized value for the given input value which
        may be in system mode or in display mode.

        Example:

            valu = tlib.getTypeFrob('inet:ipv4',valu)

        '''
        return self.reqDataType(name).frob(valu, oldval=oldval)

    def getTypeChop(self, name, valu):
        return self.reqDataType(name).chop(valu)

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

            ipv4 = tlib.getTypeParse('inet:ipv4','1.2.3.4')

        '''
        return self.reqDataType(name).parse(text)
