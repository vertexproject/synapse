import re
import socket
import struct

import synapse.compat as s_compat
import synapse.lib.socket as s_socket
import synapse.lib.urlhelp as s_urlhelp

from synapse.exc import *
from synapse.common import tufo
from synapse.lib.types import DataType,syntype,subtype

def getDataModel():
    return {
        'prefix':'inet',
        'version':201611251045,

        'types':(
            ('inet:url',    {'ctor':'synapse.models.inet.UrlType'}),
            ('inet:ipv4',   {'ctor':'synapse.models.inet.IPv4Type'}),
            ('inet:ipv6',   {'ctor':'synapse.models.inet.IPv6Type'}),
            ('inet:srv4',   {'ctor':'synapse.models.inet.Srv4Type'}),
            ('inet:srv6',   {'ctor':'synapse.models.inet.Srv6Type'}),
            ('inet:email',  {'ctor':'synapse.models.inet.EmailType'}),

            ('inet:asn',        {'subof':'int','doc':'An Autonomous System Number (ASN)'}),
            ('inet:user',       {'subof':'str'}),
            ('inet:passwd',     {'subof':'str'}),
            ('inet:filepath',   {'subof':'str'}),

            ('inet:tcp4', {'subof':'inet:srv4', 'doc':'A TCP server listening on ipv4:port'}),
            ('inet:udp4', {'subof':'inet:srv4', 'doc':'A UDP server listening on ipv4:port'}),
            ('inet:tcp6', {'subof':'inet:srv6', 'doc':'A TCP server listening on ipv6:port'}),
            ('inet:udp6', {'subof':'inet:srv6', 'doc':'A UDP server listening on ipv6:port'}),

            ('inet:port', {'subof':'int', 'min':0, 'max':0xffff}),
            ('inet:fqdn', {'subof':'str', 'regex':'^[a-z0-9._-]+$', 'lower':1}),
            ('inet:mac',  {'subof':'str', 'regex':'^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$', 'lower':1}),
        ),

        'forms':(
            ('inet:asn',{'ptype':'inet:asn'},[]),
            ('inet:user',{'ptype':'inet:user'},[]),
            ('inet:passwd',{'ptype':'inet:passwd'},[]),

            ('inet:mac',{'ptype':'inet:mac'},[]),
            ('inet:fqdn',{'ptype':'inet:fqdn'},[]),

            ('inet:email',{},[
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('user',{'ptype':'inet:user'}),
            ]),

            ('inet:tcp4',{'ptype':'inet:srv4'},[
                ('ipv4',{'ptype':'inet:ipv4'}),
                ('port',{'ptype':'inet:port'}),
            ]),

            ('inet:udp4',{'ptype':'inet:srv4'},[
                ('ipv4',{'ptype':'inet:ipv4'}),
                ('port',{'ptype':'inet:port'}),
            ]),
            ('inet:tcp6',{'ptype':'inet:srv6'},[
                ('ipv6',{'ptype':'inet:ipv6'}),
                ('port',{'ptype':'inet:port'}),
            ]),

            ('inet:udp6',{'ptype':'inet:srv6'},[
                ('ipv6',{'ptype':'inet:ipv6'}),
                ('port',{'ptype':'inet:port'}),
            ]),

        ),
    }

def ipv4str(valu):
    byts = struct.pack('>I',valu)
    return socket.inet_ntoa(byts)

def ipv4int(valu):
    byts = socket.inet_aton(valu)
    return struct.unpack('>I', byts)[0]

class IPv4Type(DataType):

    def norm(self, valu, oldval=None):
        return valu & 0xffffffff

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            return self.parse(valu, oldval=oldval)
        return self.norm(valu, oldval=oldval)

    def repr(self, valu):
        return ipv4str(valu)

    def parse(self, text, oldval=None):
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

    def parse(self, text, oldval=None):

        try:
            astr,pstr = text.split(':')
        except ValueError as e:
            raise BadTypeValu(name=self.name,valu=text)

        addr = ipv4int(astr)
        port = int(pstr,0)
        return ( addr << 16 ) | port

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            return self.parse(valu, oldval=oldval)
        return self.norm(valu, oldval=None)

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

    def repr(self, valu):
        return valu

class UrlType(DataType):

    #subprops = (
        #tufo('fqdn',ptype='inet:fqdn'),
        #tufo('ipv4',ptype='inet:ipv4'),
        #tufo('ipv6',ptype='inet:ipv6'),
        #tufo('port',ptype='inet:port'),
    #)
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

