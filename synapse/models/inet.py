from encodings import idna
import re
import socket
import struct
import hashlib

import synapse.compat as s_compat
import synapse.lib.socket as s_socket
import synapse.lib.urlhelp as s_urlhelp

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
            ('inet:email',  {'ctor':'synapse.models.inet.EmailType','doc':'An e-mail address','ex':'visi@vertex.link'}),
            ('inet:fqdn',   {'ctor':'synapse.models.inet.FqdnType', 'ex':'vertex.link','doc':'A Fully Qualified Domain Name (FQDN)'}),

            ('inet:cidr4',   {'ctor':'synapse.models.inet.CidrType','doc':'An IPv4 CIDR type','ex':'1.2.3.0/24'}),

            ('inet:net4',   {'subof':'sepr','sep':'-','fields':'min,inet:ipv4|max,inet:ipv4','doc':'An IPv4 address range','ex':'1.2.3.4-1.2.3.20'}),
            ('inet:net6',   {'subof':'sepr','sep':'-','fields':'min,inet:ipv6|max,inet:ipv6','doc':'An IPv6 address range','ex':'ff::00-ff::30'}),

            ('inet:asnet4', {'subof':'sepr','sep':'/','fields':'asn,inet:asn|net4,inet:net4','doc':'An IPv4 address range assigned to an autonomous system','ex':'54959/1.2.3.4-1.2.3.20'}),

            ('inet:asn',        {'subof':'int','doc':'An Autonomous System Number (ASN)'}),
            ('inet:user',       {'subof':'str','doc':'A username string'}),
            ('inet:passwd',     {'subof':'str','doc':'A password string'}),
            #('inet:filepath',   {'subof':'str','doc':'An absolute file path'}),
            #('inet:filenorm',   {'subof':'str','doc':'An absolute file path'}),

            ('inet:tcp4', {'subof':'inet:srv4', 'doc':'A TCP server listening on IPv4:port'}),
            ('inet:udp4', {'subof':'inet:srv4', 'doc':'A UDP server listening on IPv4:port'}),
            ('inet:tcp6', {'subof':'inet:srv6', 'doc':'A TCP server listening on IPv6:port'}),
            ('inet:udp6', {'subof':'inet:srv6', 'doc':'A UDP server listening on IPv6:port'}),

            ('inet:port', {'subof':'int', 'min':0, 'max':0xffff,'ex':'80'}),
            ('inet:mac',  {'subof':'str', 'regex':'^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$', 'lower':1, 'nullval':'??',
                           'ex':'aa:bb:cc:dd:ee:ff','doc':'A 48 bit mac address'}),

            ('inet:netuser',  {'subof':'sepr','sep':'/','fields':'site,inet:fqdn|user,inet:user',
                               'doc':'A user account at a given web address','ex':'twitter.com/invisig0th'}),

            ('inet:netmesg',  {'subof':'sepr','sep':'/','fields':'site,inet:fqdn|from,inet:user|to,inet:user|sent,time',
                               'doc':'A message sent from one user to another within a web community',
                                'ex':'twitter.com/invisig0th/gobbles/20041012130220'}),

            ('inet:ssl:tcp4cert',{'subof':'sepr','sep':'/','fields':'tcp4,inet:tcp4|cert,file:guid','doc':'An SSL cert file served by an IPv4 server'}),

            ('inet:whois:reg',{'subof':'str','doc':'A whois registrant','ex':'Woot Hostmaster'}),
            ('inet:whois:rec',{'subof':'sepr','sep':'@','fields':'fqdn,inet:fqdn|asof,time','doc':'A whois record','ex':''}),
            ('inet:whois:regmail',{'subof':'sepr','sep':'/','fields':'fqdn,inet:fqdn|email,inet:email','doc':'A whois registration fqdn->email link'}),

            # TODO: (port from nucleus etc)
            # inet:cidr6
        ),

        'forms':(

            ('inet:ipv4',{'ptype':'inet:ipv4'},[
                ('cc',{'ptype':'pol:iso2','defval':'??'}),
                ('type',{'defval':'??','doc':'what type of ipv4 address ( uni, multi, priv )'}),
                ('asn',{'ptype':'inet:asn','defval':-1}),
            ]),

            ('inet:cidr4',{'ptype':'inet:cidr4'},[
                ('ipv4',{'ptype':'inet:ipv4','doc':'The CIDR Network Address','ro':1}),
                ('mask',{'ptype':'int','doc':'The CIDR mask','ro':1})
            ]),

            ('inet:ipv6',{'ptype':'inet:ipv6'},[
                ('cc',{'ptype':'pol:iso2','defval':'??'}),
                ('asn',{'ptype':'inet:asn','defval':-1}),
            ]),

            ('inet:url',{'ptype':'inet:url'},[
                ('ipv6',{'ptype':'inet:ipv6','ro':1}),
                ('ipv4',{'ptype':'inet:ipv4','ro':1}),
                ('fqdn',{'ptype':'inet:fqdn','ro':1}),
                ('port',{'ptype':'inet:port','ro':1}),
            ]),

            ('inet:asn',{'ptype':'inet:asn','doc':'An Autonomous System'},[
                ('name',{'ptype':'str:lwr','defval':'??'}),
            ]),

            ('inet:asnet4',{'ptype':'inet:asnet4','doc':'A netblock IPv4 range assigned to an Autonomous System'},[
                ('asn',{'ptype':'inet:asn'}),
                ('net4',{'ptype':'inet:net4'}),
                ('net4:min',{'ptype':'inet:ipv4'}),
                ('net4:max',{'ptype':'inet:ipv4'}),
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
                ('domain',{'ptype':'inet:fqdn','doc':'The parent FQDN of the FQDN'}),
                ('host',{'ptype':'str','doc':'The hostname of the FQDN'}),
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
                ('name',{'ptype':'str','defval':'??'}),
                ('email',{'ptype':'inet:email'}),
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

            ('inet:whois:regmail',{'ptype':'inet:whois:regmail'},[
                ('fqdn',{'ptype':'inet:fqdn','ro':1}),
                ('email',{'ptype':'inet:email','ro':1}),
            ]),

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

            ('inet:ssl:tcp4cert',{'ptype':'inet:ssl:tcp4cert'},[
                ('tcp4',{'ptype':'inet:tcp4'}),
                ('cert',{'ptype':'file:guid'}),
                ('tcp4:ipv4',{'ptype':'inet:ipv4'}),
            ]),
        ),
    }

def castInetDeFang(valu):
    return valu.replace('[.]','.')

def addCoreOns(core):

    # add an inet:defang cast to swap [.] to .
    core.addTypeCast('inet:defang',castInetDeFang)

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
            props['inet:fqdn:domain'] = parts[1]
            pafo = core.formTufoByProp('inet:fqdn',parts[1])
            if pafo[1].get('inet:fqdn:sfx'):
                props['inet:fqdn:zone'] = 1

    def onTufoSetFqdnSfx(mesg):
        sfx = mesg[1].get('valu')
        fqdn = mesg[1].get('tufo')[1].get('inet:fqdn')
        for tufo in core.getTufosByProp('inet:fqdn:domain', fqdn):
            core.setTufoProp(tufo, 'zone', sfx)

    core.on('tufo:form:inet:fqdn',onTufoFormFqdn)
    core.on('tufo:set:inet:fqdn:sfx',onTufoSetFqdnSfx)
    core.on('tufo:form:inet:passwd',onTufoFormPasswd)

def ipv4str(valu):
    byts = struct.pack('>I',valu)
    return socket.inet_ntoa(byts)

def ipv4int(valu):
    byts = socket.inet_aton(valu)
    return struct.unpack('>I', byts)[0]

masks = [ (0xffffffff - ( 2**(32-i) - 1 )) for i in range(33) ]
def ipv4mask(ipv4,mask):
    return ipv4 & masks[mask]

class IPv4Type(DataType):

    def norm(self, valu, oldval=None):
        if not s_compat.isint(valu):
            self._raiseBadValu(valu)

        return valu & 0xffffffff,{}

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            # handle decimal integer strings...
            if valu.isdigit():
                return int(valu) & 0xffffffff,{}
            return self.parse(valu, oldval=oldval)
        return self.norm(valu, oldval=oldval)

    def repr(self, valu):
        return ipv4str(valu)

    def parse(self, text, oldval=None):
        # deal with "defanged" ipv4
        if s_compat.isstr(text):
            text = text.replace('[.]','.')
            return ipv4int(text),{}
        self._raiseBadValu(text)

fqdnre = re.compile(r'^[\w._-]+$', re.U)
class FqdnType(DataType):

    subprops = (
        ('sfx',{'ptype':'bool'}),
        ('zone',{'ptype':'bool'}),
        ('domain',{'ptype':'inet:fqdn'}),
        ('host',{'ptype':'str'}),
    )

    def norm(self, valu, oldval=None):
        valu = valu.replace('[.]','.')
        if not fqdnre.match(valu):
            self._raiseBadValu(valu)
        if valu.startswith('xn--'):
            valu = idna.ToUnicode(valu)
        valu = valu.lower()

        parts = valu.split('.', 1)
        subs = {'host': parts[0]}
        if len(parts) == 2:
            subs['domain'] = parts[1]
        else:
            subs['sfx'] = 1
        return valu,subs


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
            return ipv6norm(valu),{}
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

    def repr(self, valu):
        addr = valu >> 16
        port = valu & 0xffff
        return '%s:%d' % ( ipv4str(addr), port )

    def norm(self, valu, oldval=None):
        addr = valu >> 16
        port = valu & 0xffff
        return valu,{'port':port,'ipv4':addr}

    def parse(self, text, oldval=None):

        try:
            astr,pstr = text.split(':')
        except ValueError as e:
            self._raiseBadValu(text)

        addr = ipv4int(astr)
        port = int(pstr,0)
        return ( addr << 16 ) | port,{}

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
            user,_ = self.tlib.getTypeNorm('inet:user', user)
            fqdn,_ = self.tlib.getTypeNorm('inet:fqdn', fqdn)
            norm = ('%s@%s' % (user, fqdn)).lower()
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
        respath = ''
        resauth = ''

        if valu.find('://') == -1:
            self._raiseBadValu(valu)

        proto,resloc = valu.split('://',1)

        parts = resloc.split('/',1)
        if len(parts) == 2:
            resloc,respath = parts

        if resloc.find('@') != -1:
            resauth,resloc = resloc.split('@',1)

        proto = proto.lower()
        hostpart = resloc.lower()

        if resauth:
            hostpart = '%s@%s' % (resauth,hostpart)

        valu = '%s://%s/%s' % (proto,hostpart,respath)
        return (valu,{'proto':proto})

    def repr(self, valu):
        return valu


class CidrType(DataType):

    def norm(self, valu, oldval=None):

        ipstr,maskstr = valu.split('/')

        mask = int(maskstr)
        ipv4 = ipv4int(ipstr)

        if mask > 32 or mask < 0:
            self._raiseBadValu(valu, mesg='Invalid CIDR Mask')

        ipv4 = ipv4mask(ipv4,mask)
        valu = '%s/%d' % ( ipv4str(ipv4), mask )

        return valu,{'ipv4':ipv4,'mask':mask}

    def repr(self, valu):
        return valu
