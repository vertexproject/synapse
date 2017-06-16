import re
import socket
import struct
import hashlib

import synapse.compat as s_compat
import synapse.lib.socket as s_socket
import synapse.lib.urlhelp as s_urlhelp

import synapse.lookup.iana as s_l_iana

from synapse.exc import BadTypeValu
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

            ('inet:urlfile', {'subof':'comp','types':'inet:url,file:bytes','names':'url,file','doc':'A File at a Universal Resource Locator (URL)'}),
            ('inet:net4',   {'subof':'sepr','sep':'-','fields':'min,inet:ipv4|max,inet:ipv4','doc':'An IPv4 address range','ex':'1.2.3.4-1.2.3.20'}),
            ('inet:net6',   {'subof':'sepr','sep':'-','fields':'min,inet:ipv6|max,inet:ipv6','doc':'An IPv6 address range','ex':'ff::00-ff::30'}),

            ('inet:asnet4', {'subof':'sepr','sep':'/','fields':'asn,inet:asn|net4,inet:net4','doc':'An IPv4 address range assigned to an autonomous system','ex':'54959/1.2.3.4-1.2.3.20'}),

            ('inet:asn',        {'subof':'int','doc':'An Autonomous System Number (ASN)'}),
            ('inet:user',       {'subof':'str:lwr','doc':'A username string'}),
            ('inet:passwd',     {'subof':'str','doc':'A password string'}),

            ('inet:tcp4', {'subof':'inet:srv4', 'doc':'A TCP server listening on IPv4:port'}),
            ('inet:udp4', {'subof':'inet:srv4', 'doc':'A UDP server listening on IPv4:port'}),
            ('inet:tcp6', {'subof':'inet:srv6', 'doc':'A TCP server listening on IPv6:port'}),
            ('inet:udp6', {'subof':'inet:srv6', 'doc':'A UDP server listening on IPv6:port'}),

            ('inet:port', {'subof':'int', 'min':0, 'max':0xffff,'ex':'80'}),
            ('inet:mac',  {'subof':'str', 'regex':'^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$', 'lower':1, 'nullval':'??',
                           'ex':'aa:bb:cc:dd:ee:ff','doc':'A 48 bit mac address'}),

            ('inet:netuser',{'subof':'sepr','sep':'/','fields':'site,inet:fqdn|user,inet:user', 'doc':'A user account at a given web address','ex':'twitter.com/invisig0th'}),

            ('inet:netgroup',   {'subof':'sepr','sep':'/','fields':'site,inet:fqdn|name,ou:name','doc':'A group within an online community'}),

            ('inet:netpost',    {'subof':'comp','fields':'netuser,inet:netuser|text,str:txt', 'doc':'A post made by a netuser'}),
            ('inet:netfile',    {'subof':'comp','fields':'netuser,inet:netuser|file,file:bytes', 'doc':'A file posted by a netuser'}),
            ('inet:netmemb',    {'subof':'comp','fields':'user,inet:netuser|group,inet:netgroup'}),
            ('inet:follows',  {'subof':'comp','fields':'follower,inet:netuser|followee,inet:netuser'}),


            ('inet:netmesg',  {'subof':'comp',
                               'fields':'from,inet:netuser|to,inet:netuser|time,time',
                               'doc':'A message sent from one netuser to another',
                               'ex':'twitter.com/invisig0th|twitter.com/gobbles|20041012130220'}),

            ('inet:ssl:tcp4cert',{'subof':'sepr','sep':'/','fields':'tcp4,inet:tcp4|cert,file:bytes','doc':'An SSL cert file served by an IPv4 server'}),

            ('inet:whois:rar',{'subof':'str:lwr','doc':'A whois registrar','ex':'blah domain registrar'}),
            ('inet:whois:reg',{'subof':'str:lwr','doc':'A whois registrant','ex':'woot hostmaster'}),
            ('inet:whois:rec',{'subof':'sepr','sep':'@','fields':'fqdn,inet:fqdn|asof,time','doc':'A whois record','ex':''}),

            ('inet:whois:contact',{'subof':'comp','fields':'rec,inet:whois:rec|type,str:lwr','doc':'A whois contact for a specific record'}),
            ('inet:whois:regmail',{'subof':'comp','fields':'fqdn,inet:fqdn|email,inet:email','doc':'A whois registration fqdn->email link'}),

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
                ('user',{'ptype':'inet:user','ro':1}),
                ('passwd',{'ptype':'inet:passwd','ro':1}),
            ]),

            ('inet:urlfile',{'ptype':'inet:urlfile'},[
                ('url',{'ptype':'inet:url','ro':1}),
                ('file',{'ptype':'file:bytes','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),

            ('inet:asn',{'ptype':'inet:asn','doc':'An Autonomous System'},(
                ('name',{'ptype':'str:lwr','defval':'??'}),
            )),

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

                ('created',{'ptype':'time:min'}),
                ('updated',{'ptype':'time:max'}),
                ('expires',{'ptype':'time:max'}),

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

                ('dob',{'ptype':'time'}),

                #('bio:bt',{'ptype':'wtf','doc':'The netusers self documented blood type'}),

                ('url',{'ptype':'inet:url'}),
                ('webpage',{'ptype':'inet:url'}),
                ('avatar',{'ptype':'file:bytes'}),

                ('tagline',{'ptype':'str:txt','doc':'A netuser status/tag line text'}),
                ('occupation',{'ptype':'str:txt','doc':'A netuser self declared occupation'}),
                #('gender',{'ptype':'inet:fqdn','ro':1}),

                ('name',{'ptype':'inet:user'}),
                ('realname',{'ptype':'ps:name'}),
                ('email',{'ptype':'inet:email'}),
                ('phone',{'ptype':'tel:phone'}),
                ('signup',{'ptype':'time','doc':'The time the netuser account was registered'}),
                ('signup:ipv4',{'ptype':'inet:ipv4','doc':'The original ipv4 address used to sign up for the account'}),
                ('passwd',{'ptype':'inet:passwd','doc':'The current passwd for the netuser account'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),

            ('inet:netgroup',{},[
                ('site',{'ptype':'inet:fqdn','ro':1}),
                ('name',{'ptype':'ou:name','ro':1}),

                ('desc',{'ptype':'str:txt'}),

                ('url',{'ptype':'inet:url'}),
                ('webpage',{'ptype':'inet:url'}),
                ('avatar',{'ptype':'file:bytes'}),
            ]),

            ('inet:netpost',{},[

                ('netuser',{'ptype':'inet:netuser','ro':1}),
                ('text',{'ptype':'str:txt','ro':1,'doc':'The text of the actual post'}),

                ('netuser:site',{'ptype':'inet:fqdn','ro':1}),
                ('netuser:user',{'ptype':'inet:user','ro':1}),

                ('time',{'ptype':'time'}),

                ('replyto',{'ptype':'inet:netpost'}),

                ('url',{'ptype':'inet:url','doc':'The (optional) URL where the post is published/visible'}),
                ('file',{'ptype':'file:bytes','doc':'The (optional) file which was posted'}),
            ]),

            ('inet:netmesg',{},[
                ('from',{'ptype':'inet:netuser','ro':1}),
                ('to',{'ptype':'inet:netuser','ro':1}),
                ('time',{'ptype':'time','ro':1,'doc':'The time at which the message was sent'}),
                ('url',{'ptype':'inet:url','doc':'Optional URL of netmesg'}),
                ('text',{'ptype':'str:txt','doc':'Optional text body of message'}),
                ('file',{'ptype':'file:bytes','doc':'Optional file attachment'}),
            ]),

            ('inet:follows',{},[

                ('follower',{'ptype':'inet:netuser','ro':1}),
                ('followee',{'ptype':'inet:netuser','ro':1}),

                ('seen:min',{'ptype':'time:min','doc':'Optional first/earliest following'}),
                ('seen:max',{'ptype':'time:max','doc':'Optional last/end of following'}),

            ]),

            ('inet:netmemb',{},[

                ('user',{'ptype':'inet:netuser','ro':1}),
                ('group',{'ptype':'inet:netgroup','ro':1}),

                ('title',{'ptype':'str:lwr'}),

                ('joined',  {'ptype':'time'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),

            ]),

            ('inet:netfile',{},[

                ('netuser',{'ptype':'inet:netuser','ro':1}),
                ('netuser:site',{'ptype':'inet:fqdn','ro':1}),
                ('netuser:user',{'ptype':'inet:user','ro':1}),

                ('file',{'ptype':'file:bytes','ro':1}),

                ('name',{'ptype':'file:base','doc':'The basename of the file in the post'}),

                ('posted',{'ptype':'time'}),

                ('ipv4',{'ptype':'inet:ipv4','doc':'The source IPv4 address of the post.'}),
                ('ipv6',{'ptype':'inet:ipv6','doc':'The source IPv6 address of the post.'}),

                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),

            ('inet:whois:reg',{},[]),
            ('inet:whois:rar',{},[]),

            ('inet:whois:regmail',{'ptype':'inet:whois:regmail'},[
                ('fqdn',{'ptype':'inet:fqdn','ro':1}),
                ('email',{'ptype':'inet:email','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),

            ('inet:whois:rec',{'ptype':'inet:whois:rec'},[
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('asof',{'ptype':'time'}),
                ('text',{'ptype':'str:lwr'}),
                ('created',{'ptype':'time','doc':'The "created" time from the whois record'}),
                ('updated',{'ptype':'time','doc':'The "last updated" time from the whois record'}),
                ('expires',{'ptype':'time','doc':'The "expires" time from the whois record'}),
                ('registrar',{'ptype':'inet:whois:rar','defval':'??'}),
                ('registrant',{'ptype':'inet:whois:reg','defval':'??'}),
                ('ns1',{'ptype':'inet:fqdn'}),
                ('ns2',{'ptype':'inet:fqdn'}),
                ('ns3',{'ptype':'inet:fqdn'}),
                ('ns4',{'ptype':'inet:fqdn'}),
            ]),

            ('inet:whois:contact',{},[

                ('rec',{'ptype':'inet:whois:rec'}),
                ('rec:fqdn',{'ptype':'inet:fqdn'}),
                ('rec:asof',{'ptype':'time'}),

                ('type',{'ptype':'str:lwr'}),

                ('id',{'ptype':'str:lwr'}),
                ('name',{'ptype':'str:lwr'}),
                ('email',{'ptype':'inet:email'}),

                ('orgname',{'ptype':'ou:name'}),
                ('address',{'ptype':'str:lwr'}), # FIXME street address type
                ('city',{'ptype':'str:lwr'}),
                #('zip',{'ptype':'str:lwr'}),
                ('state',{'ptype':'str:lwr'}),
                ('country',{'ptype':'pol:iso2'}),

                ('phone',{'ptype':'tel:phone'}),
                ('fax',{'ptype':'tel:phone'}),
            ]),

            ('inet:ssl:tcp4cert',{'ptype':'inet:ssl:tcp4cert'},[
                ('tcp4',{'ptype':'inet:tcp4'}),
                ('cert',{'ptype':'file:bytes'}),
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
    try:
        byts = socket.inet_aton(valu)
        return struct.unpack('>I', byts)[0]
    except socket.error as e:
        raise BadTypeValu(valu=valu,type='inet:ipv4',mesg=str(e))

masks = [ (0xffffffff - ( 2**(32-i) - 1 )) for i in range(33) ]
def ipv4mask(ipv4,mask):
    return ipv4 & masks[mask]

class IPv4Type(DataType):

    def norm(self, valu, oldval=None):
        if s_compat.isstr(valu):
            return self._norm_str(valu,oldval=oldval)

        if not s_compat.isint(valu):
            self._raiseBadValu(valu)

        return valu & 0xffffffff,{}

    def _norm_str(self, valu, oldval=None):
        if valu.isdigit():
            return int(valu,0) & 0xffffffff,{}

        valu = valu.replace('[.]','.')
        return ipv4int(valu),{}

    def repr(self, valu):
        return ipv4str(valu)

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

        try:
            valu = valu.encode('idna').decode('idna').lower()
        except UnicodeError as e:
            self._raiseBadValu(valu)

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
        if s_compat.isstr(valu):
            return self._norm_str(valu,oldval=oldval)

        addr = valu >> 16
        port = valu & 0xffff
        return valu,{'port':port,'ipv4':addr}

    def _norm_str(self, text, oldval=None):
        try:
            astr,pstr = text.split(':')
        except ValueError as e:
            self._raiseBadValu(text)

        addr = ipv4int(astr)
        port = int(pstr,0)
        return ( addr << 16 ) | port,{}

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

urlports = {
    'ftp':21,
    'http':80,
    'https':443,
}
class UrlType(DataType):

    subprops = (
        ('proto',{'ptype':'str'}),
        ('path',{'ptype':'str'}),
        ('fqdn',{'ptype':'inet:fqdn'}),
        ('ipv4',{'ptype':'inet:ipv4'}),
        ('ipv6',{'ptype':'inet:ipv6'}),
        ('port',{'ptype':'inet:port'}),
        ('user',{'ptype':'inet:user'}),
        ('passwd',{'ptype':'inet:passwd'}),
    )

    def norm(self, valu, oldval=None):
        subs = {}
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

            user = resauth
            passwd = None

            if user.find(':') != None:
                user,passwd = user.rsplit(':',1)

            if user:
                subs['user'] = user

            if passwd:
                subs['passwd'] = passwd

        port = None
        proto = proto.lower()
        hostpart = resloc.lower()

        subs['proto'] = proto

        if hostpart.find(':') != -1:
            host,portstr = hostpart.rsplit(':',1)
            port = self.tlib.getTypeParse('inet:port',portstr)[0]

        # try for a default iana protocol lookup
        if port == None:
            port = s_l_iana.services.get(proto)

        if port != None:
            subs['port'] = port

        if resauth:
            hostpart = '%s@%s' % (resauth,hostpart)

        valu = '%s://%s/%s' % (proto,hostpart,respath)
        return valu,subs

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
