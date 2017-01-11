import re
import socket
import struct
import hashlib

import synapse.compat as s_compat
import synapse.lib.socket as s_socket
import synapse.lib.urlhelp as s_urlhelp

from synapse.exc import *
from synapse.lib.types import DataType

def getDataModel():
    return {
        'prefix':'inet',
        'version':201611251045,

        'types':(
            ('inet:url',    {'ctor':'synapse.models.inet.UrlType','doc':'A Universal Resource Locator (URL)'}),
            ('inet:ipv4',   {'ctor':'synapse.models.inet.IPv4Type','doc':'An IPv4 Address','ex':'1.2.3.4'}),
            ('inet:ipv6',   {'ctor':'synapse.models.inet.IPv6Type','doc':'An IPv6 Address','ex':'2607:f8b0:4004:809::200e'}),
            ('inet:srv4',   {'ctor':'synapse.models.inet.Srv4Type','doc':'An IPv4 Address and Port','ex':'1.2.3.4:80'}),
            ('inet:srv6',   {'ctor':'synapse.models.inet.Srv6Type','doc':'An IPv6 Address and Port','ex':'[2607:f8b0:4004:809::200e]:80'}),
            #('inet:email',  {'ctor':'synapse.models.inet.EmailType'}),

            ('inet:asn',        {'subof':'int','doc':'An Autonomous System Number (ASN)'}),
            ('inet:user',       {'subof':'str','doc':'A username string'}),
            ('inet:passwd',     {'subof':'str','doc':'A password string'}),
            ('inet:filepath',   {'subof':'str','doc':'An absolute file path'}),
            #('inet:filenorm',   {'subof':'str','doc':'An absolute file path'}),

            ('inet:tcp4', {'subof':'inet:srv4', 'doc':'A TCP server listening on IPv4:port'}),
            ('inet:udp4', {'subof':'inet:srv4', 'doc':'A UDP server listening on IPv4:port'}),
            ('inet:tcp6', {'subof':'inet:srv6', 'doc':'A TCP server listening on IPv6:port'}),
            ('inet:udp6', {'subof':'inet:srv6', 'doc':'A UDP server listening on IPv6:port'}),

            ('inet:port', {'subof':'int', 'min':0, 'max':0xffff,'ex':'80'}),
            ('inet:fqdn', {'subof':'str', 'regex':'^[a-z0-9._-]+$', 'lower':1,'nullval':'??','ex':'vertex.link','doc':'A Fully Qualified Domain Name (FQDN)'}),
            ('inet:mac',  {'subof':'str', 'regex':'^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$', 'lower':1, 'nullval':'??',
                           'ex':'aa:bb:cc:dd:ee:ff','doc':'A 48 bit mac address'}),

            ('inet:email',{'subof':'sepr','sep':'@','lower':1,'fields':'user,inet:user|fqdn,inet:fqdn',
                           'doc':'An e-mail address','ex':'visi@vertex.link'}),

            ('inet:netuser',  {'subof':'sepr','sep':'/','fields':'site,inet:fqdn|user,inet:user',
                               'doc':'A user account at a given web address','ex':'twitter.com/invisig0th'}),

            ('inet:netmesg',  {'subof':'sepr','sep':'/','fields':'site,inet:fqdn|from,inet:user|to,inet:user|sent,time',
                               'doc':'A message sent from one user to another within a web community',
                                'ex':'twitter.com/invisig0th/gobbles/20041012130220'}),

            ('inet:whois:reg',{'subof':'str','doc':'A whois registrant','ex':'Woot Hostmaster'}),
            ('inet:whois:rec',{'subof':'sepr','sep':'@','fields':'fqdn,inet:fqdn|asof,time','doc':'A whois record','ex':''}),

            # TODO: (port from nucleus etc)
            # inet:cidr
            # inet:cidr6
        ),

        'forms':(

            ('inet:ipv4',{'ptype':'inet:ipv4'},[
                ('cc',{'ptype':'pol:iso2','defval':'??'}),
                ('type',{'defval':'??','doc':'what type of ipv4 address ( uni, multi, priv )'}),
                ('asn',{'ptype':'inet:asn','defval':0}),
            ]),

            ('inet:ipv6',{'ptype':'inet:ipv6'},[
                ('cc',{'ptype':'pol:iso2','defval':'??'}),
                ('asn',{'ptype':'inet:asn','defval':0}),
            ]),

            ('inet:url',{'ptype':'inet:url'},[
                ('ipv6',{'ptype':'inet:ipv6','ro':1}),
                ('ipv4',{'ptype':'inet:ipv4','ro':1}),
                ('fqdn',{'ptype':'inet:fqdn','ro':1}),
                ('port',{'ptype':'inet:port','ro':1}),
            ]),

            ('inet:asn',{'ptype':'inet:asn'},[
                ('name',{'ptype':'str:lwr','defval':'??'}),
                #TODO ('cidr',{'ptype':'inet:cidr'}),
            ]),

            ('inet:user',{'ptype':'inet:user'},[]),

            ('inet:passwd',{'ptype':'inet:passwd'},[
                ('md5',{'ptype':'hash:md5','doc':'Pre-computed MD5 hash of the passwd'}),
                ('sha1',{'ptype':'hash:sha1','doc':'Pre-computed SHA1 hash of the passwd'}),
                ('sha256',{'ptype':'hash:sha256','doc':'Pre-computed SHA256 hash of the passwd'}),
            ]),

            ('inet:mac',{'ptype':'inet:mac'},[
                ('vendor',{'ptype':'str','defval':'??','doc':'The vendor name registered for the 24 bit prefix'}),
            ]),

            ('inet:fqdn',{'ptype':'inet:fqdn'},[
                ('sfx',{'ptype':'bool','defval':0,'doc':'Set to 1 if this FQDN is considered a "suffix"'}),
                ('zone',{'ptype':'bool','defval':0,'doc':'Set to 1 if this FQDN is a logical zone (under a suffix)'}),
                ('parent',{'ptype':'inet:fqdn','doc':'The parent FQDN'}),
            ]),

            ('inet:email',{'ptype':'inet:email'},[
                ('fqdn',{'ptype':'inet:fqdn','ro':1}),
                ('user',{'ptype':'inet:user','ro':1}),
            ]),

            ('inet:tcp4',{'ptype':'inet:srv4'},[
                ('ipv4',{'ptype':'inet:ipv4','ro':1}),
                ('port',{'ptype':'inet:port','ro':1}),
            ]),

            ('inet:udp4',{'ptype':'inet:srv4'},[
                ('ipv4',{'ptype':'inet:ipv4','ro':1}),
                ('port',{'ptype':'inet:port','ro':1}),
            ]),
            ('inet:tcp6',{'ptype':'inet:srv6'},[
                ('ipv6',{'ptype':'inet:ipv6','ro':1}),
                ('port',{'ptype':'inet:port','ro':1}),
            ]),

            ('inet:udp6',{'ptype':'inet:srv6'},[
                ('ipv6',{'ptype':'inet:ipv6','ro':1}),
                ('port',{'ptype':'inet:port','ro':1}),
            ]),

            ('inet:netuser',{'ptype':'inet:netuser'},[
                ('site',{'ptype':'inet:fqdn','ro':1}),
                ('user',{'ptype':'inet:user','ro':1}),
                ('signup',{'ptype':'time','defval':0,'doc':'The time the netuser account was registered'}),
                ('passwd',{'ptype':'inet:passwd','doc':'The current passwd for the netuser account'}),
                ('seen:min',{'ptype':'time:min','defval':0}),
                ('seen:max',{'ptype':'time:max','defval':0}),
            ]),

            ('inet:netmesg',{'ptype':'inet:netmesg'},[
                ('site',{'ptype':'inet:fqdn','ro':1}),
                ('to',{'ptype':'inet:user','ro':1}),
                ('from',{'ptype':'inet:user','ro':1}),
                ('sent',{'ptype':'time','ro':1,'doc':'The time at which the message was sent'}),
                ('body',{'ptype':'str'}),
            ]),

            ('inet:whois:reg',{'ptype':'inet:whois:reg'},[]),

            ('inet:whois:rec',{'ptype':'inet:whois:rec'},[
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('asof',{'ptype':'time'}),
                ('created',{'ptype':'time','defval':0,'doc':'The "created" time from the whois record'}),
                ('updated',{'ptype':'time','defval':0,'doc':'The "last updated" time from the whois record'}),
                ('expires',{'ptype':'time','defval':0,'doc':'The "expires" time from the whois record'}),
                ('registrar',{'ptype':'inet:whois:reg','defval':'??'}),
                ('registrant',{'ptype':'inet:whois:reg','defval':'??'}),
                # TODO admin/tech/billing contact info
            ]),
        ),
    }

def addCoreOns(core):

    def onTufoFormPasswd(mesg):
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')
        props['inet:passwd:md5'] = hashlib.md5( valu.encode('utf8') ).hexdigest()
        props['inet:passwd:sha1'] = hashlib.sha1( valu.encode('utf8') ).hexdigest()
        props['inet:passwd:sha256'] = hashlib.sha256( valu.encode('utf8') ).hexdigest()

    def onTufoFormFqdn(mesg):
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')
        parts = valu.split('.',1)
        if len(parts) > 1:
            props['inet:fqdn:parent'] = parts[1]
            pafo = core.formTufoByProp('inet:fqdn',parts[1])
            if pafo[1].get('inet:fqdn:sfx'):
                props['inet:fqdn:zone'] = 1

    #def onTufoAddFqdn(mesg):
        #tufo = mesg[1].get('tufo')
        #fqdn = tufo[1].get('inet:fqdn:parent')
        #core.formTufoByProp('inet:fqdn',fqdn)

    #core.on('tufo:add:inet:fqdn',onTufoAddFqdn)

    core.on('tufo:form:inet:fqdn',onTufoFormFqdn)
    core.on('tufo:form:inet:passwd',onTufoFormPasswd)

def ipv4str(valu):
    byts = struct.pack('>I',valu)
    return socket.inet_ntoa(byts)

def ipv4int(valu):
    byts = socket.inet_aton(valu)
    return struct.unpack('>I', byts)[0]

class IPv4Type(DataType):

    def norm(self, valu, oldval=None):
        if not s_compat.isint(valu):
            raise BadTypeValu(name=self.name,valu=valu)

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
        ('port', {'ptype':'inet:port'}),
        ('ipv4', {'ptype':'inet:ipv4'}),
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
        ('port', {'ptype':'inet:port'}),
        ('ipv6', {'ptype':'inet:ipv6'}),
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
        ('user',{'ptype':'inet:user'}),
        ('fqdn',{'ptype':'inet:fqdn'}),
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

    subprops = (
        ('proto',{'ptype':'str'}),
        ('path',{'ptype':'str'}),
        ('fqdn',{'ptype':'inet:fqdn'}),
        ('ipv4',{'ptype':'inet:ipv4'}),
        ('ipv6',{'ptype':'inet:ipv6'}),
        ('port',{'ptype':'inet:port'}),
    )

    def norm(self, valu, oldval=None):
        return self.chop(valu,oldval=oldval)[0]

    def chop(self, valu, oldval=None):
        respath = ''
        resauth = ''

        if valu.find('://') == -1:
            raise BadTypeValu(name=self.name,valu=valu)

        proto,resloc = valu.split('://',1)

        parts = resloc.split('/',1)
        if len(parts) == 2:
            resloc,respath = parts

        if resloc.find('@') != -1:
            resauth,resloc = resloc.split('@',1)

        # FIXME chop sub props from resloc!
        proto = proto.lower()
        hostpart = resloc.lower()

        if resauth:
            hostpart = '%s@%s' % (resauth,hostpart)

        valu = '%s://%s/%s' % (proto,hostpart,respath)
        return (valu,{'proto':proto})

    def repr(self, valu):
        return valu

