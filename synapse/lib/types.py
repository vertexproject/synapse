from __future__ import absolute_import,unicode_literals

import re
import json
import time
import base64
import socket
import struct
import datetime

import synapse.compat as s_compat
import synapse.lib.socket as s_socket
import synapse.lib.urlhelp as s_urlhelp
import synapse.swarm.syntax as s_syntax

from synapse.common import *

class DataType:

    subprops = ()

    def __init__(self, tlib, name, **info):
        self.tlib = tlib
        self.name = name
        self.info = info

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

class StrType(DataType):

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        self.regex = None

        regex = info.get('regex')
        if regex != None:
            self.regex = re.compile(regex)

    def repr(self, valu):
        return valu

    def norm(self, valu, oldval=None):

        if not s_compat.isstr(valu):
            self._raiseBadValu(valu)

        if self.info.get('lower'):
            valu = valu.lower()

        enums = self.info.get('enums')
        if enums != None and valu not in enums:
            self._raiseBadValu(valu,enums=enums)

        if self.regex != None and not self.regex.match(valu):
            self._raiseBadValu(valu,regex=self.info.get('regex'))

        return valu

    def parse(self, valu):
        return self.norm(valu)

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

    def parse(self, valu):
        try:
            valu = int(valu,0)
        except Exception as e:
            raise self._raiseBadValu(valu)

        return self.norm(valu)

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

        fields = info.get('fields',())
        #self.comptypes = self._initCompTypes(fields)

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

    def parse(self, text):

        # NOTE: handles both text *and* (text,text,text) list/tuple.

        if islist(text):
            reps = text
        else:
            reps = json.loads(text)

        vals = [ t.parse(r) for r,(n,t) in self._zipvals(reps) ]
        return enMsgB64(vals)

    def _zipvals(self, vals):
        return s_compat.iterzip(vals,self.comptypes)

class BoolType(DataType):

    def norm(self, valu, oldval=None):
        return int(bool(valu))

    def repr(self, valu):
        return repr(bool(valu))

    def parse(self, text):
        text = text.lower()
        if text in ('true','t','y','yes','1','on'):
            return 1

        if text in ('false','f','n','no','0','off'):
            return 0

        self._raiseBadValu(text)

def ipv4str(valu):
    byts = struct.pack('>I',valu)
    return socket.inet_ntoa(byts)

def ipv4int(valu):
    byts = socket.inet_aton(valu)
    return struct.unpack('>I', byts)[0]

class IPv4Type(DataType):

    def norm(self, valu, oldval=None):
        return valu & 0xffffffff

    def repr(self, valu):
        return ipv4str(valu)

    def parse(self, text):
        return ipv4int(text)

# RFC5952 compatible
def ipv6norm(text):
    '''
    Normalize an IPv6 address into RFC5952 canonical form.

    Example:

        text = ipv6norm(text)

    '''
    # use inet_ntop / inet_pton from synapse.lib.socket for portability
    return s_socket.inet_ntop( socket.AF_INET6, s_socket.inet_pton( socket.AF_INET6, text ) )

class IPv6Type(DataType):

    def norm(self, valu, oldval=None):
        try:
            return ipv6norm(valu)
        except Exception as e:
            self._raiseBadValu(valu)

    def parse(self, text):
        return self.norm(text)

    def repr(self, valu):
        return valu

#class HostPort(DataType):

class Srv4Type(DataType):
    '''
    Base type for <ipv4>:<port> format.
    '''
    subprops = (
        tufo('port', ptype='inet:port'),
        tufo('ipv4', ptype='inet:ipv4'),
    )

    def norm(self, valu, oldval=None):
        return valu & 0xffffffffffff

    def repr(self, valu):
        addr = valu >> 16
        port = valu & 0xffff
        return '%s:%d' % ( ipv4str(addr), port )

    def chop(self, valu):
        addr = valu >> 16
        port = valu & 0xffff
        return valu,{'port':port,'ipv4':addr}

    def parse(self, text):

        try:
            astr,pstr = text.split(':')
        except ValueError as e:
            raise BadTypeValu(name=self.name,valu=text)

        addr = ipv4int(astr)
        port = int(pstr,0)
        return ( addr << 16 ) | port

srv6re = re.compile('^\[([a-f0-9:]+)\]:(\d+)$')

class Srv6Type(DataType):
    '''
    Base type for [IPv6]:port format.
    '''
    subprops = (
        tufo('port', ptype='inet:port'),
        tufo('ipv6', ptype='inet:ipv6'),
    )

    def norm(self, valu, oldval=None):
        return self.chop(valu)[0]

    def chop(self, valu):

        valu = valu.lower()
        m = srv6re.match(valu)
        if m == None:
            self._raiseBadValu(valu, ex='[af::2]:80')

        host,portstr = m.groups()

        port = int(portstr,0)
        if port > 0xffff or port < 0:
            self._raiseBadValu(valu, port=port)

        try:
            host = ipv6norm(host)
        except Exception as e:
            self._raiseBadValu(valu)

        valu = '[%s]:%d' % (host,port)
        return valu,{'ipv6':host,'port':port}

    def parse(self, text):
        return self.norm(text)

    def repr(self, valu):
        return valu

class EmailType(DataType):

    subprops = (
        tufo('user',ptype='inet:user'),
        tufo('fqdn',ptype='inet:fqdn'),
    )

    def norm(self, valu, oldval=None):
        try:
            user,fqdn = valu.split('@',1)
        except ValueError as e:
            self._raiseBadValu(valu)

        return valu.lower()

    def chop(self, valu):
        norm = valu.lower()
        try:
            user,fqdn = valu.split('@',1)
        except ValueError as e:
            self._raiseBadValu(valu)
        return norm,{'user':user,'fqdn':fqdn}

    def parse(self, text):
        return self.norm(text)

    def repr(self, valu):
        return valu

class UrlType(DataType):

    #subprops = (
        #tufo('fqdn',ptype='inet:fqdn'),
        #tufo('ipv4',ptype='inet:ipv4'),
        #tufo('ipv6',ptype='inet:ipv6'),
        #tufo('port',ptype='inet:port'),
    #)

    def parse(self, text):
        return self.norm(text)

    def norm(self, valu, oldval=None):
        respath = ''
        resauth = ''

        if valu.find('://') == -1:
            raise BadTypeValu(name=self.name,valu=valu)

        scheme,resloc = valu.split('://',1)

        parts = resloc.split('/',1)
        if len(parts) == 2:
            resloc,respath = parts

        if resloc.find('@') != -1:
            resauth,resloc = resloc.split('@',1)

        # FIXME chop sub props from resloc!
        scheme = scheme.lower()
        hostpart = resloc.lower()

        if resauth:
            hostpart = '%s@%s' % (resauth,hostpart)

        return '%s://%s/%s' % (scheme,hostpart,respath)

    def repr(self, valu):
        return valu

class EpochType(DataType):

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        self.ismin = info.get('ismin',False)
        self.ismax = info.get('ismax',False)

        self.minmax = None

        if self.ismin:
            self.minmax = min

        elif self.ismax:
            self.minmax = max

    def norm(self, valu, oldval=None):

        if not s_compat.isint(valu):
            self._raiseBadValu(valu)

        if oldval != None and self.minmax:
            valu = self.minmax(valu,oldval)

        return valu

    def parse(self, text):

        text = text.strip().lower()
        text = (''.join([ c for c in text if c.isdigit() ]))[:14]

        tlen = len(text)
        if tlen == 4:
            st = time.strptime(text, '%Y')

        elif tlen == 6:
            st = time.strptime(text, '%Y%m')

        elif tlen == 8:
            st = time.strptime(text, '%Y%m%d')

        elif tlen == 10:
            st = time.strptime(text, '%Y%m%d%H')

        elif tlen == 12:
            st = time.strptime(text, '%Y%m%d%H%M')

        elif tlen == 14:
            st = time.strptime(text, '%Y%m%d%H%M%S')

        else:
            raise Exception('Unknown time format: %s' % text)

        e = datetime.datetime(1970,1,1)
        d = datetime.datetime(st.tm_year, st.tm_mon, st.tm_mday)

        epoch = int((d - e).total_seconds())
        epoch += st.tm_hour*3600
        epoch += st.tm_min*60
        epoch += st.tm_sec

        return epoch

    def repr(self, valu):
        dt = datetime.datetime(1970,1,1) + datetime.timedelta(seconds=int(valu))
        return '%d/%.2d/%.2d %.2d:%.2d:%.2d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

class TypeLib:
    '''
    An extensible type library for use in cortex data models.
    '''
    def __init__(self):
        self.types = {}
        self.subtypes = []

        self.addType(IntType(self,'int'))
        self.addType(StrType(self,'str'))
        self.addType(BoolType(self,'bool'))
        self.addType(CompType(self,'comp'))

        self.addSubType('int:min','int', ismin=1)
        self.addSubType('int:max','int', ismax=1)

        self.addSubType('syn:tag','str', regex=r'^([\w]+\.)*[\w]+$', lower=1)
        self.addSubType('syn:prop','str', regex=r'^([\w]+:)*[\w]+$', lower=1)
        self.addSubType('syn:type','str', regex=r'^([\w]+:)*[\w]+$', lower=1)

        self.addSubType('text', 'str')

        self.addSubType('str:lwr', 'str', lower=1)

        self.addSubType('geo:latlong', 'str', regex='^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$')

        self.addSubType('guid', 'str', regex='^[0-9a-f]{32}$', lower=1)

        self.addSubType('hash:md5','str', regex='^[0-9a-f]{32}$', lower=1)
        self.addSubType('hash:sha1','str', regex='^[0-9a-f]{40}$', lower=1)
        self.addSubType('hash:sha256','str', regex='^[0-9a-f]{64}$', lower=1)
        self.addSubType('hash:sha384','str', regex='^[0-9a-f]{96}$', lower=1)
        self.addSubType('hash:sha512','str', regex='^[0-9a-f]{128}$', lower=1)

        # time types
        self.addType( EpochType(self,'time:epoch') )
        self.addSubType('time:epoch:min','time:epoch',ismin=1)
        self.addSubType('time:epoch:max','time:epoch',ismax=1)

        # inet types
        self.addType(IPv4Type(self,'inet:ipv4'))
        self.addType(IPv6Type(self,'inet:ipv6'))

        self.addType(Srv4Type(self,'inet:srv4'))
        self.addType(Srv6Type(self,'inet:srv6'))

        self.addSubType('inet:tcp4','inet:srv4')
        self.addSubType('inet:udp4','inet:srv4')
        self.addSubType('inet:tcp6','inet:srv6')
        self.addSubType('inet:udp6','inet:srv6')

        self.addType(UrlType(self,'inet:url'))
        self.addType(EmailType(self,'inet:email'))

        self.addSubType('inet:asn', 'int')
        self.addSubType('inet:user','str')
        self.addSubType('inet:passwd','str')
        self.addSubType('inet:filepath','str')

        self.addSubType('inet:fqdn','str', regex='^[a-z0-9._-]+$', lower=1)
        self.addSubType('inet:mac', 'str', regex='^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$', lower=1)

        self.addSubType('inet:port', 'int', min=0, max=0xffff)

    def addSubType(self, name, subof, **info):
        '''
        Add a new type which extends from parent type's class.

        Example:

            tlib.addSubType('guid:org', 'guid', doc='guid for an org')

        '''
        if self.types.get(name) != None:
            raise DupTypeName(name=name)

        info['subof'] = subof
        base = self.reqDataType(subof)
        self.addType( base.extend(name, **info) )
        self.subtypes.append( (name,info) )

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

    def addType(self, item):
        '''
        Add a type object which extends from DataType.

        class MyType(DataType):
            def __init__(self):
                DataType.__init__(self,'my:type')

            #def repr(self, valu):
            #def norm(self, valu, oldval=None):
            #def parse(self, text):

        tlib.addType( MyType() )
        '''
        self.types[item.name] = item

    def getTypeNorm(self, name, valu, oldval=None):
        '''
        Normalize a type specific value in system mode.

        Example:

            fqdn = tlib.getTypeNorm('inet:fqdn','Foo.Com')

        '''
        return self.reqDataType(name).norm(valu, oldval=oldval)

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
