import socket
import struct
import hashlib
import logging
import ipaddress
import email.utils

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.datamodel as s_datamodel

#import synapse.lib.tufo as s_tufo
import synapse.lib.socket as s_socket
import synapse.lookup.iana as s_l_iana

#from synapse.exc import BadTypeValu
#from synapse.lib.types import DataType

import synapse.lib.types as s_types
import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

fqdnre = regex.compile(r'^[\w._-]+$', regex.U)

cidrmasks = [((0xffffffff - (2 ** (32 - i) - 1)), (2 ** (32 - i))) for i in range(33)]

class IPv4(s_types.Type):
    '''
    The base type for an IPv4 address.
    '''
    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    def _normPyInt(self, valu):
        norm = valu & 0xffffffff
        return norm, {}

    def _normPyStr(self, valu):
        valu = valu.replace('[.]', '.')
        byts = socket.inet_aton(valu)
        norm = int.from_bytes(byts, 'big')
        return self._normPyInt(norm)

    def indx(self, norm):
        return norm.to_bytes(4, 'big')

    def repr(self, norm):
        return socket.inet_ntoa(self.indx(norm))

    def liftPropEq(self, xact, fenc, penc, text):

        if text.find('/') != -1:

            addr, mask = text.split('/', 1)
            norm, info = self.norm(addr)

            mask = cidrmasks[int(mask)]

            minv = norm & mask[0]

            mini = self.indx(minv)
            maxi = self.indx(minv + mask[1])

            lops = (
                ('prop:range', {
                    'form': fenc,
                    'prop': penc,
                    'minindx': self.indx(minv),
                    'maxindx': self.indx(minv + mask[1] - 1)
                }),
            )
            return xact.lift(lops)

        norm, info = self.norm(text)
        lops = (
            ('prop:eq', {
                'form': fenc,
                'prop': penc,
                'valu': norm,
                'indx': self.indx(norm),
            }),
        )
        return xact.lift(lops)

class Fqdn(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        valu = valu.replace('[.]', '.')
        if not fqdnre.match(valu):
            self._raiseBadValu(valu)

        try:
            valu = valu.encode('idna').decode('utf8').lower()
        except UnicodeError as e:
            self._raiseBadValu(valu)

        parts = valu.split('.', 1)

        adds = []
        subs = {'host': parts[0]}

        if len(parts) == 2:
            subs['domain'] = parts[1]
        else:
            subs['sfx'] = 1

        return valu, {'subs': subs}

    def indx(self, norm):
        return norm[::-1].encode('utf8')

    def liftPropEq(self, xact, fenc, penc, text):

        valu = str(text).strip().lower()
        if not valu:
            return

        if valu[0] == '*':
            indx = valu[1:][::-1].encode('utf8')
            lops = (
                ('prop:pref', {
                    'form': fenc,
                    'prop': penc,
                    'indx': indx,
                }),
            )
            return xact.lift(lops)

        if valu.find('*') != -1:
            raise s_exc.BadLiftValu(valu=valu, mesg='Wild card may only appear at the beginning.')

        norm, info = self.norm(valu)
        indx = valu[::-1].encode('utf8')

        lops = (
            ('prop:eq', {
                'form': fenc,
                'prop': penc,
                'indx': indx,
                'valu': norm,
            }),
        )

        return xact.lift(lops)

    def repr(self, valu):
        try:
            return valu.encode('utf8').decode('idna')
        except UnicodeError as e:
            if len(valu) >= 4 and valu[0:4] == 'xn--':
                logger.exception(msg='Failed to IDNA decode ACE prefixed inet:fqdn')
                return valu
            raise  # pragma: no cover

class Email(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        user, fqdn = valu.split('@', 1)

        fqdnnorm, fqdninfo = self.modl.type('inet:fqdn').norm(fqdn)
        usernorm, userinfo = self.modl.type('inet:user').norm(user)

        norm = '%s@%s' % (usernorm, fqdnnorm)
        info = {
            'subs': {
                'fqdn': fqdnnorm,
                'user': usernorm,
            }
        }
        return norm, info

    def indx(self, norm):
        return norm.encode('utf8')

#def ipv4mask(ipv4, mask):
    #return ipv4 & masks[mask]

#def ipv4cidr(valu):
    #_ipv4str, cidr = valu.split('/', 1)
    #_ipv4addr = ipv4int(_ipv4str)
    #mask = cidrmasks[int(cidr)]
    #lowerbound = _ipv4addr & mask[0]
    #return lowerbound, lowerbound + mask[1]

#class IPv4Type(DataType):

    #def norm(self, valu, oldval=None):
        #if isinstance(valu, str):
            #return self._norm_str(valu, oldval=oldval)

# FIXME ipv6 stuff..
    #v6addr = ipaddress.IPv6Address(text)
    #v4addr = v6addr.ipv4_mapped
    #if v4addr is not None:
        #return '::ffff:%s' % (v4addr), {'ipv4': ipv4int(str(v4addr))}

    #return v6addr.compressed, {}

        #if not isinstance(valu, int):
            #self._raiseBadValu(valu)

        #return valu & 0xffffffff, {}
    #def norm(self, valu, oldval=None):
        #try:
            #return ipv6norm(valu)
        #except Exception as e:
            #self._raiseBadValu(valu)

    #def _norm_str(self, valu, oldval=None):
        #if valu.isdigit():
            #return int(valu, 0) & 0xffffffff, {}

        #valu = valu.replace('[.]', '.')
        #return ipv4int(valu), {}

    #def repr(self, valu):
        #return ipv4str(valu)


#class FqdnType(DataType):
    #subprops = (
        #('sfx', {'ptype': 'bool'}),
        #('zone', {'ptype': 'bool'}),
        #('domain', {'ptype': 'inet:fqdn'}),
        #('host', {'ptype': 'str'}),
    #)

    #def norm(self, valu, oldval=None):

        #valu = valu.replace('[.]', '.')
        #if not fqdnre.match(valu):
            #self._raiseBadValu(valu)

        #try:
            #valu = valu.encode('idna').decode('utf8').lower()
        #except UnicodeError as e:
            #self._raiseBadValu(valu)

        #parts = valu.split('.', 1)
        #subs = {'host': parts[0]}
        #if len(parts) == 2:
            #subs['domain'] = parts[1]
        #else:
            #subs['sfx'] = 1

        #return valu, subs

    #def repr(self, valu):
        #try:
            #return valu.encode('utf8').decode('idna')
        #except UnicodeError as e:
            #if len(valu) >= 4 and valu[0:4] == 'xn--':
                #logger.exception(msg='Failed to IDNA decode ACE prefixed inet:fqdn')
                #return valu
            #raise  # pragma: no cover

#class Rfc2822Addr(DataType):
    #'''
    #An RFC 2822 compatible email address parser
    #'''
    #def norm(self, valu, oldval=None):

        #if not isinstance(valu, str):
            #self._raiseBadValu(valu, mesg='requires a string')

        # remove quotes for normalized version
        #valu = valu.replace('"', ' ').replace("'", ' ')
        #valu = valu.strip().lower()
        #valu = ' '.join(valu.split())

        #subs = {}

        #try:

            #name, addr = email.utils.parseaddr(valu)

        #except Exception as e: #pragma: no cover
            # not sure we can ever really trigger this with a string as input
            #self._raiseBadValu(valu, mesg='email.utils.parsaddr failed: %s' % (e,))

        #if name:
            #subs['name'] = name

        #try:

            #mail, ssub = self.tlib.getTypeNorm('inet:email', addr)
            #subs['email'] = mail

            #if name:
                #valu = '%s <%s>' % (name, mail)

            #else:
                #valu = mail

        #except BadTypeValu as e:
            #pass # it's all good, we just dont have a valid email addr

        #return valu, subs

# RFC5952 compatible
#def ipv6norm(text):
    #'''
    #Normalize an IPv6 address into RFC5952 canonical form.

    #Example:

        #text = ipv6norm(text)

    #'''
    # This used to use socket.inet_pton for normalizing
    # ipv6 addresses. There's a bug in macOS where it
    # doesn't abbreviate the zeroes properly. See RFC
    # 5952 for IPv6 address text representation

    #v6addr = ipaddress.IPv6Address(text)
    #v4addr = v6addr.ipv4_mapped
    #if v4addr is not None:
        #return '::ffff:%s' % (v4addr)

    #return v6addr.compressed

#class IPv6Type(DataType):
    #def repr(self, valu):
        #return self.norm(valu)[0]

    #def norm(self, valu, oldval=None):
        #try:
            #return ipv6norm(valu), {}
        #except Exception as e:
            #self._raiseBadValu(valu)

# class HostPort(DataType):


#class EmailType(DataType):
    #subprops = (
        #('user', {'ptype': 'inet:user'}),
        #('fqdn', {'ptype': 'inet:fqdn'}),
    #)

    #def norm(self, valu, oldval=None):
        #try:
            #user, fqdn = valu.split('@', 1)
            #user, _ = self.tlib.getTypeNorm('inet:user', user)
            #fqdn, _ = self.tlib.getTypeNorm('inet:fqdn', fqdn)
            #norm = ('%s@%s' % (user, fqdn)).lower()
        #except ValueError as e:
            #self._raiseBadValu(valu)
        #return norm, {'user': user, 'fqdn': fqdn}

    #def repr(self, valu):
        #return valu

#urlports = {
#    'ftp': 21,
#    'http': 80,
#    'https': 443,
#}
#
#class UrlType(DataType):
#    subprops = (
#        ('proto', {'ptype': 'str'}),
#        ('path', {'ptype': 'str'}),
#        ('fqdn', {'ptype': 'inet:fqdn'}),
#        ('ipv4', {'ptype': 'inet:ipv4'}),
#        ('ipv6', {'ptype': 'inet:ipv6'}),
#        ('port', {'ptype': 'inet:port'}),
#        ('user', {'ptype': 'inet:user'}),
#        ('passwd', {'ptype': 'inet:passwd'}),
#    )
#
#    def norm(self, valu, oldval=None):
#        subs = {}
#        respath = ''
#        resauth = ''
#
#        if valu.find('://') == -1:
#            self._raiseBadValu(valu)
#
#        proto, resloc = valu.split('://', 1)
#
#        parts = resloc.split('/', 1)
#        if len(parts) == 2:
#            resloc, respath = parts
#
#        if resloc.find('@') != -1:
#            resauth, resloc = resloc.split('@', 1)
#
#            user = resauth
#            passwd = None
#
#            if user.find(':') is not None:
#                user, passwd = user.rsplit(':', 1)
#
#            if user:
#                subs['user'] = user
#
#            if passwd:
#                subs['passwd'] = passwd
#
#        port = None
#        proto = proto.lower()
#        hostpart = resloc.lower().replace('[.]', '.')
#
#        subs['proto'] = proto
#
#        host = hostpart
#        if hostpart.find(':') != -1:
#            host, portstr = hostpart.rsplit(':', 1)
#            port = self.tlib.getTypeParse('inet:port', portstr)[0]
#
#        # use of exception handling logic here is fastest way to both
#        # validate and convert the data...  normally wouldnt use....
#
#        ipv4 = None
#        try:
#
#            ipv4 = ipv4int(host)
#            subs['ipv4'] = ipv4
#
#        except BadTypeValu as e:
#            pass
#
#        if ipv4 is None and fqdnre.match(host):
#            subs['fqdn'] = host
#
#        # try for a default iana protocol lookup
#        if port is None:
#            port = s_l_iana.services.get(proto)
#
#        if port is not None:
#            subs['port'] = port
#
#        if resauth:
#            hostpart = '%s@%s' % (resauth, hostpart)
#
#        valu = '%s://%s/%s' % (proto, hostpart, respath)
#        return valu, subs
#
#    def repr(self, valu):
#        return valu
#
#class CidrType(DataType):
#    def norm(self, valu, oldval=None):
#        ipstr, maskstr = valu.split('/')
#
#        mask = int(maskstr)
#        ipv4 = ipv4int(ipstr)
#
#        if mask > 32 or mask < 0:
#            self._raiseBadValu(valu, mesg='Invalid CIDR Mask')
#
#        ipv4 = ipv4mask(ipv4, mask)
#        valu = '%s/%d' % (ipv4str(ipv4), mask)
#
#        return valu, {'ipv4': ipv4, 'mask': mask}
#
#    def repr(self, valu):
#        return valu

#class AddrType(DataType):

    #def norm(self, valu, oldval=None):

        #subs = {}
        #if valu.find('.') != -1:
            #valu = valu.split(':')[-1]
            #ipv4, subs = self.tlib.getTypeNorm('inet:ipv4', valu)
            #subs['ipv4'] = ipv4

            #valu = '::ffff:' + valu

        #addr, _ = self.tlib.getTypeNorm('inet:ipv6', valu)
        #return addr, subs

# TO MERGE UPDATED INET:ADDR
#        orig = valu
#
#        proto = 'tcp'
#        if valu.find('://') != -1:
#            proto, valu = valu.split('://', 1)
#            proto = proto.lower()
#
#        if proto not in ('tcp', 'udp', 'icmp', 'host'):
#            self._raiseBadValu(valu, mesg='inet:addr protocol must be in: tcp, udp, icmp, host')
#
#        # strip any trailing /
#        valu = valu.strip().strip('/')
#
#        subs = {'proto': proto}
#
#        # handle host proto
#        if proto == 'host':
#            if valu.find(':') != -1:
#
#                valu, portstr = valu.rsplit(':')
#                subs['port'] = port = int(portstr, 0) & 0xffff
#
#                guid, _ = self.tlib.getTypeNorm('guid', valu)
#                subs['host'] = guid
#
#                return 'host://%s:%d' % (guid, port), subs
#
#            guid, _ = self.tlib.getTypeNorm('guid', valu)
#            subs['host'] = guid
#            return 'host://%s' % (guid,), subs
#
#        # check for ipv6
#        if valu.startswith('['): # "[" <ipv6> "]" [:port]
#
#            ipv6, v6sub = self.tlib.getTypeNorm('inet:ipv6', valu[1:].split(']', 1)[0])
#            subs['ipv6'] = ipv6
#
#            text = '[%s]' % (ipv6,)
#
#            ipv4 = v6sub.get('ipv4')
#            if ipv4 is not None:
#                text = ipv4str(ipv4)
#                subs['ipv4'] = ipv4
#
#            if valu.find(']:') != -1:
#
#                if proto not in ('tcp', 'udp'):
#                    self._raiseBadValu(orig, mesg='IPv6 port syntax with non tcp/udp protocol')
#
#                subs['port'] = port = int(valu.rsplit(':', 1)[1], 0)
#                text += ':%d' % (port,)
#
#            norm = '%s://%s' % (proto, text)
#            return norm, subs
#
#        # check for DWIM ipv6 with no []s
#        try:
#
#            ipv6, v6sub = self.tlib.getTypeNorm('inet:ipv6', valu)
#            subs['ipv6'] = ipv6
#
#            text = '[%s]' % (ipv6,)
#
#            ipv4 = v6sub.get('ipv4')
#            if ipv4 is not None:
#                text = ipv4str(ipv4)
#                subs['ipv4'] = ipv4
#
#            norm = proto + '://' + text
#            return norm, subs
#
#        except BadTypeValu as e:
#            pass
#
#        # check for a port
#        port = None
#        if valu.find(':') != -1:
#
#            if proto not in ('tcp', 'udp'):
#                self._raiseBadValu(orig, mesg='IPv6 port syntax with non tcp/udp protocol')
#
#            valu, portstr = valu.rsplit(':', 1)
#            subs['port'] = port = int(portstr, 0) & 0xffff
#
#        # check for ipv4
#        try:
#
#            ipv4 = ipv4int(valu)
#            ipv6 = '::ffff:%s' % (ipv4str(ipv4),)
#
#            text = ipv4str(ipv4)
#
#            subs['ipv4'] = ipv4
#            subs['ipv6'] = ipv6
#
#            if port is not None:
#                text += ':%d' % (port,)
#
#            norm = '%s://%s' % (proto, text)
#            return norm, subs
#
#        except BadTypeValu as e:
#            pass
#
#        self._raiseBadValu(orig, mesg='inet:addr must be a <tcp|udp|icmp|host>://<ipv4|ipv6|guid>[:port]/')

class InetModule(s_module.CoreModule):

    def initCoreModule(self):
        self.model.form('inet:fqdn').onAdd(self._onAddFqdn)
        self.model.prop('inet:fqdn:zone').onSet(self._onSetFqdnZone)
        self.model.prop('inet:fqdn:iszone').onSet(self._onSetFqdnIsZone)
        self.model.prop('inet:fqdn:issuffix').onSet(self._onSetFqdnIsSuffix)

    def _onAddFqdn(self, node):

        fqdn = node.ndef[1]
        domain = node.get('domain')

        if domain is None:
            node.set('issuffix', True)
            return

        # almost certainly in the cache anyway....
        parent = node.xact.getNodeByNdef(('inet:fqdn', domain))

        if parent.get('issuffix'):
            node.set('iszone', True)
            node.set('zone', fqdn)
            return

        if parent.get('iszone'):
            node.set('zone', domain)
            return

        zone = parent.get('zone')
        if zone is not None:
            node.set('zone', zone)

    def _onSetFqdnIsSuffix(self, node, oldv):

        fqdn = node.ndef[1]

        issuffix = node.get('issuffix')
        for child in node.xact.getNodesBy('inet:fqdn:domain', fqdn):
            child.set('iszone', issuffix)

    def _onSetFqdnIsZone(self, node, oldv):

        fqdn = node.ndef[1]

        iszone = node.get('iszone')
        if iszone:
            node.set('zone', fqdn)
            return

        # we are *not* a zone and were...
        domain = node.get('domain')
        if not domain:
            node.set('zone', None)

        parent = node.xact.getNodeByNdef(('inet:fqdn', domain))
        node.set('zone', parent.get('zone'))

    def _onSetFqdnZone(self, node, oldv):

        fqdn = node.ndef[1]
        zone = node.get('zone')

        for child in node.xact.getNodesBy('inet:fqdn:domain', fqdn):

            # if they are their own zone level, skip
            if child.get('iszone'):
                continue

            # the have the same zone we do
            child.set('zone', zone)

    def getModelDefs(self):
        return (

            ('inet', {

                'ctors': (

                    ('inet:ipv4', 'synapse.models.inet.IPv4', {}, {
                        'doc': 'An IPv4 address.'}),

                    ('inet:fqdn', 'synapse.models.inet.Fqdn', {}, {
                        'doc': 'A Fully Qualified Domain Name (FQDN).'}),

                    ('inet:email', 'synapse.models.inet.Email', {}, {
                        'doc': 'An e-mail address.'}),
                ),

                'types': (

                    ('inet:user', ('str', {'lower': True}), {
                        'doc': 'A user name.'}),

                    ('inet:asn', ('int', {}), {
                        'doc': 'An autonomous system number'}),

                ),

                'forms': (

                    ('inet:ipv4', {}, (
                        ('loc', ('loc', {}), {
                            'defval': '??',
                            'doc': 'The geo-political location string for the IPv4.'}),
                    )),

                    ('inet:fqdn', {}, (

                        ('domain', ('inet:fqdn', {}), {
                            'doc': 'The parent domain for the FQDN.',
                        }),

                        ('zone', ('inet:fqdn', {}), {
                            'doc': 'The zone level parent for this FQDN.',
                        }),

                        ('iszone', ('bool', {}), {
                            'doc': 'True if the FQDN is considered a zone.',
                            'defval': 0,
                        }),

                        ('issuffix', ('bool', {}), {
                            'doc': 'True if the FQDN is considered a suffix.',
                            'defval': 0,
                        }),

                        ('host', ('str', {'lower': True}), {
                            'doc': 'The host part of the FQDN.',

                        }),

                    )),

                    ('inet:user', {}, (
                    )),


                    ('inet:email', {}, (

                        ('user', ('inet:user', {}), {
                            'ro': True,
                            'doc': 'The email address user name.'}),

                        ('fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The email address FQDN.'}),
                    )),

                ),
            }),
        )

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('inet:url', {
                    'ctor': 'synapse.models.inet.UrlType',
                    'doc': 'A Universal Resource Locator (URL).',
                    'ex': 'http://www.woot.com/files/index.html'}),

                ('inet:addr', {
                    'ctor': 'synapse.models.inet.AddrType',
                    'doc': 'A network layer URL-like format to represent tcp/udp/icmp clients and servers.',
                    'ex': 'tcp://1.2.3.4:80'}),

                ('inet:server', {
                    'subof': 'inet:addr',
                    'doc': 'A network server address.'}),

                ('inet:client', {
                    'subof': 'inet:addr',
                    'doc': 'A network client address.'}),

                ('inet:ipv4', {
                    'ctor': 'synapse.models.inet.IPv4Type',
                    'doc': 'An IPv4 address.',
                    'ex': '1.2.3.4'}),

                ('inet:ipv6', {
                    'ctor': 'synapse.models.inet.IPv6Type',
                    'doc': 'An IPv6 address.',
                    'ex': '2607:f8b0:4004:809::200e'}),

                ('inet:srv4', {
                    'ctor': 'synapse.models.inet.Srv4Type',
                    'doc': 'An IPv4 address and port.',
                    'ex': '1.2.3.4:80'}),

                ('inet:srv6', {
                    'ctor': 'synapse.models.inet.Srv6Type',
                    'doc': 'An IPv6 address and port.',
                    'ex': '[2607:f8b0:4004:809::200e]:80'}),

                ('inet:wifi:ssid', {
                    'subof': 'str',
                    'doc': 'A WiFi service set identifier (SSID) name.',
                    'ex': 'The Vertex Project'}),

                ('inet:wifi:ap', {
                    'subof': 'comp',
                    'fields': 'ssid=inet:wifi:ssid,bssid=inet:mac',
                    'doc': 'An SSID/MAC address combination for a wireless access point.'}),

                ('inet:email', {
                    'ctor': 'synapse.models.inet.EmailType',
                    'doc': 'An email address.',
                    'ex': 'visi@vertex.link'}),

                ('inet:fqdn', {
                    'ctor': 'synapse.models.inet.FqdnType',
                    'doc': 'A fully qualified domain name (FQDN).',
                    'ex': 'vertex.link'}),

                ('inet:cidr4', {
                    'ctor': 'synapse.models.inet.CidrType',
                    'doc': 'An IPv4 address block in Classless Inter-Domain Routing (CIDR) notation.',
                    'ex': '1.2.3.0/24'}),

                ('inet:urlredir', {
                    'subof': 'comp',
                    'fields': 'src=inet:url,dst=inet:url',
                    'doc': 'A URL that redirects to another URL, such as via a URL shortening service or an HTTP 302 response.',
                    'ex': '(http://foo.com/,http://bar.com/)'}),

                ('inet:urlfile', {
                    'subof': 'comp',
                    'fields': 'url=inet:url, file=file:bytes',
                    'doc': 'A file hosted at a specific Universal Resource Locator (URL).'}),

                ('inet:net4', {
                    'subof': 'sepr',
                    'sep': '-',
                    'fields': 'min,inet:ipv4|max,inet:ipv4',
                    'doc': 'An IPv4 address range.',
                    'ex': '1.2.3.4-1.2.3.20'}),

                ('inet:net6', {
                    'subof': 'sepr',
                    'sep': '-',
                    'fields': 'min,inet:ipv6|max,inet:ipv6',
                    'doc': 'An IPv6 address range.',
                    'ex': 'ff::00-ff::30'}),

                ('inet:asnet4', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'asn,inet:asn|net4,inet:net4',
                    'doc': 'An Autonomous System Number (ASN) and its associated IPv4 address range.',
                    'ex': '54959/1.2.3.4-1.2.3.20'}),

                ('inet:iface', {
                    'subof': 'guid',
                    'doc': 'A network interface with a set of associated protocol addresses.'}),

                ('inet:asn', {
                    'subof': 'int',
                    'doc': 'An Autonomous System Number (ASN).'}),

                ('inet:user', {
                    'subof': 'str:lwr',
                    'doc': 'A username string.'}),

                ('inet:group', {
                    'subof': 'str:lwr',
                    'doc': 'A group name string.'}),

                ('inet:passwd', {
                    'subof': 'str',
                    'doc': 'A password string.'}),

                ('inet:tcp4', {
                    'subof': 'inet:srv4',
                    'doc': 'A TCP server listening on an IPv4 address and port.'}),

                ('inet:udp4', {
                    'subof': 'inet:srv4',
                    'doc': 'A UDP server listening on an IPv4 address and port.'}),

                ('inet:tcp6', {
                    'subof': 'inet:srv6',
                    'doc': 'A TCP server listening on a specific IPv6 address and port.'}),

                ('inet:udp6', {
                    'subof': 'inet:srv6',
                    'doc': 'A UDP server listening on a specific IPv6 address and port.'}),

                ('inet:flow', {
                    'subof': 'guid',
                    'doc': 'An individual network connection between a given source and destination.'}),

                ('inet:port', {
                    'subof': 'int',
                    'min': 0,
                    'max': 0xffff,
                    'doc': 'A network port.',
                    'ex': '80'}),

                ('inet:mac', {
                    'subof': 'str',
                    'regex': '^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$',
                    'lower': 1,
                    'nullval': '??',
                    'doc': 'A 48-bit Media Access Control (MAC) address.',
                    'ex': 'aa:bb:cc:dd:ee:ff'}),

                ('inet:web:acct', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'site,inet:fqdn|user,inet:user',
                    'doc': 'An account with a given Internet-based site or service.',
                    'ex': 'twitter.com/invisig0th'}),

                ('inet:web:logon', {
                    'subof': 'guid',
                    'doc': 'An instance of an account authenticating to an Internet-based site or service.'}),

                ('inet:web:action', {
                    'subof': 'guid',
                    'doc': 'An instance of an account performing an action at an Internet-based site or service.'}),

                ('inet:web:actref', {
                    'subof': 'xref',
                    'source': 'act,inet:web:action',
                    'doc': 'A web action that references a given node.'}),

                ('inet:web:chprofile', {
                    'subof': 'guid',
                    'doc': 'A change to a web account. Used to capture historical properties associated with '
                        ' an account, as opposed to current data in the inet:web:acct node.'}),

                ('inet:web:group', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'site,inet:fqdn|id,inet:group',
                    'doc': 'A group hosted within or registered with a given Internet-based site or service.',
                    'ex': 'somesite.com/mycoolgroup'}),

                ('inet:web:post', {
                    'subof': 'comp',
                    'fields': 'acct,inet:web:acct|text,str:txt',
                    'doc': 'A post made by a web account.'}),

                ('inet:web:postref', {
                    'subof': 'xref',
                    'source': 'post,inet:web:post',
                    'doc': 'A web post that references a given node.'}),

                ('inet:web:file', {
                    'subof': 'comp',
                    'fields': 'acct,inet:web:acct|file,file:bytes',
                    'doc': 'A file posted by a web account.'}),

                ('inet:web:memb', {
                    'subof': 'comp',
                    'fields': 'acct,inet:web:acct|group,inet:web:group',
                    'doc': 'A web account that is a member of a web group.'}),

                ('inet:web:follows', {
                    'subof': 'comp',
                    'fields': 'follower,inet:web:acct|followee,inet:web:acct',
                    'doc': 'A web account follows or is connected to another web account.'}),

                ('inet:web:mesg', {
                    'subof': 'comp',
                    'fields': 'from,inet:web:acct|to,inet:web:acct|time,time',
                    'doc': 'A message sent from one web account to another web account.',
                    'ex': 'twitter.com/invisig0th|twitter.com/gobbles|20041012130220'}),

                ('inet:ssl:tcp4cert', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'tcp4,inet:tcp4|cert,file:bytes',
                    'doc': 'An SSL certificate file served by an IPv4 TCP server.'}),

                ('inet:whois:rar', {
                    'subof': 'str:lwr',
                    'doc': 'A domain registrar.',
                    'ex': 'godaddy, inc.'}),

                ('inet:whois:reg', {
                    'subof': 'str:lwr',
                    'doc': 'A domain registrant.',
                    'ex': 'woot hostmaster'}),

                ('inet:whois:rec', {
                    'subof': 'sepr',
                    'sep': '@',
                    'fields': 'fqdn,inet:fqdn|asof,time',
                    'doc': 'A domain whois record'}),

                ('inet:whois:recns', {
                    'subof': 'comp',
                    'fields': 'ns,inet:fqdn|rec,inet:whois:rec',
                    'doc': 'A nameserver associated with a domain whois record.'}),

                ('inet:whois:contact', {
                    'subof': 'comp',
                    'fields': 'rec,inet:whois:rec|type,str:lwr',
                    'doc': 'An individual contact from a domain whois record.'}),

                ('inet:whois:regmail', {
                    'subof': 'comp',
                    'fields': 'fqdn,inet:fqdn|email,inet:email',
                    'doc': 'An association between a domain and a registrant email address.'}),

                ('inet:rfc2822:addr', {
                    'ctor': 'synapse.models.inet.Rfc2822Addr',
                    'ex': '"Visi Kenshoto" <visi@vertex.link>',
                    'doc': 'An RFC 2822 Address field.'}),

                ('inet:http:request', {
                    'subof': 'guid',
                    'doc': 'A single client HTTP request.',
                }),
                ('inet:http:resphead', {
                    'subof': 'comp',
                    'fields': 'response=inet:http:response,header=inet:http:header',
                    'doc': 'An instance of an HTTP header within a specific HTTP response.',
                }),

                ('inet:servfile', {
                    'subof': 'comp',
                    'fields': 'server=inet:server,file=file:bytes',
                    'doc': 'A file hosted on a server for access over a network protocol.',
                }),

                ('inet:download', {
                    'subof': 'guid',
                    'doc': 'An instance of a file downloaded from a server.',
                }),

                ('inet:server', {}, (
                    ('proto', {'ptype': 'str:lwr', 'ro': 1,
                        'doc': 'The network protocol of the server.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 of the server.'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The IPv6 of the server.'}),
                    ('host', {'ptype': 'it:host', 'ro': 1,
                        'doc': 'The it:host node for the server.'}),
                    ('port', {'ptype': 'inet:port',
                        'doc': 'The server tcp/udp port.'}),
                )),

                ('inet:client', {}, (
                    ('proto', {'ptype': 'str:lwr', 'ro': 1,
                        'doc': 'The network protocol of the client.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 of the client.'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The IPv6 of the client.'}),
                    ('host', {'ptype': 'it:host', 'ro': 1,
                        'doc': 'The it:host node for the client.'}),
                    ('port', {'ptype': 'inet:port',
                        'doc': 'The client tcp/udp port.'}),
                )),

                ('inet:servfile', {}, (
                    ('file', {'ptype': 'file:bytes', 'req': 1, 'ro': 1,
                        'doc': 'The file hosted by the server.'}),
                    ('server', {'ptype': 'inet:server', 'req': 1, 'ro': 1,
                        'doc': 'The inet:addr of the server.'}),
                    ('server:proto', {'ptype': 'str:lwr', 'ro': 1,
                        'doc': 'The network protocol of the server.'}),
                    ('server:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 of the server.'}),
                    ('server:ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The IPv6 of the server.'}),
                    ('server:host', {'ptype': 'it:host', 'ro': 1,
                        'doc': 'The it:host node for the server.'}),
                    ('server:port', {'ptype': 'inet:port',
                        'doc': 'The server tcp/udp port.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known time file was hosted on the server.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The last known time the file was hosted on the server.'}),
                )),

                ('inet:download', {}, (

                    ('time', {'ptype': 'time',
                        'doc': 'The time the file was downloaded.'}),

                    ('fqdn', {'ptype': 'inet:fqdn',
                        'doc': 'The FQDN used to resolve the server.'}),

                    ('file', {'ptype': 'file:bytes',
                        'doc': 'The file that was downloaded.'}),

                    ('server', {'ptype': 'inet:server',
                        'doc': 'The inet:addr of the server.'}),
                    ('server:proto', {'ptype': 'str:lwr',
                        'doc': 'The server network layer protocol.'}),
                    ('server:ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The IPv4 of the server.'}),
                    ('server:ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The IPv6 of the server.'}),
                    ('server:host', {'ptype': 'it:host',
                        'doc': 'The it:host node for the server.'}),
                    ('server:port', {'ptype': 'inet:port',
                        'doc': 'The server tcp/udp port.'}),

                    ('client', {'ptype': 'inet:client',
                        'doc': 'The inet:addr of the client.'}),
                    ('client:proto', {'ptype': 'str:lwr',
                        'doc': 'The client network layer protocol.'}),
                    ('client:ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The IPv4 of the client.'}),
                    ('client:ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The IPv6 of the client.'}),
                    ('client:host', {'ptype': 'it:host',
                        'doc': 'The it:host node for the client.'}),
                    ('client:port', {'ptype': 'inet:port',
                        'doc': 'The client tcp/udp port.'}),

                )),

                ('inet:ipv4', {'ptype': 'inet:ipv4'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??',
                        'doc': 'The country where the IPv4 address is currently located.'}),
                    ('type', {'ptype': 'str', 'defval': '??',
                        'doc': 'The type of IP address (e.g., private, multicast, etc.).'}),
                    ('asn', {'ptype': 'inet:asn', 'defval': -1,
                        'doc': 'The ASN to which the IPv4 address is currently assigned.'}),
                    ('latlong', {'ptype': 'geo:latlong',
                        'doc': 'The last known latitude/longitude for the node'}),
                ]),

                ('inet:cidr4', {'ptype': 'inet:cidr4'}, [
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IP address from the CIDR notation.'}),
                    ('mask', {'ptype': 'int', 'ro': 1,
                        'doc': 'The mask from the CIDR notation.'})
                ]),

                ('inet:ipv6', {'ptype': 'inet:ipv6'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??',
                        'doc': 'The country where the IPv6 address is currently located.'}),
                    ('asn', {'ptype': 'inet:asn', 'defval': -1,
                        'doc': 'The ASN to which the IPv6 address is currently assigned.'}),
                    ('latlong', {'ptype': 'geo:latlong',
                        'doc': 'The last known latitude/longitude for the node'}),
                ]),

                ('inet:url', {'ptype': 'inet:url'}, [
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                         'doc': 'The IPv6 address used in the URL.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                         'doc': 'The IPv4 address used in the URL (e.g., http://1.2.3.4/page.html).'}),
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                         'doc': 'The fqdn used in the URL (e.g., http://www.woot.com/page.html).'}),
                    ('port', {'ptype': 'inet:port', 'ro': 1,
                         'doc': 'The port of the URL. URLs prefixed with http will be set to port 80 and '
                             'URLs prefixed with https will be set to port 443 unless otherwise specified.'}),
                    ('user', {'ptype': 'inet:user', 'ro': 1,
                         'doc': 'The optional username used to access the URL.'}),
                    ('passwd', {'ptype': 'inet:passwd', 'ro': 1,
                         'doc': 'The optional password used to access the URL.'}),
                ]),

                ('inet:urlredir', {}, [
                    ('src', {'ptype': 'inet:url', 'ro': 1, 'req': 1,
                        'doc': 'The original/source URL before redirect'}),
                    ('src:fqdn', {'ptype': 'inet:fqdn',
                        'doc': 'The FQDN within the src URL (if present)'}),
                    ('dst', {'ptype': 'inet:url', 'ro': 1, 'req': 1,
                        'doc': 'The redirected/destination URL'}),
                    ('dst:fqdn', {'ptype': 'inet:fqdn',
                        'doc': 'The FQDN within the dst URL (if present)'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known time the URL redirect was active.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The last known time the URL redirect was active.'}),
                ]),

                ('inet:urlfile', {'ptype': 'inet:urlfile'}, [
                    ('url', {'ptype': 'inet:url', 'ro': 1, 'req': 1,
                        'doc': 'The URL where the file was hosted.'}),
                    ('file', {'ptype': 'file:bytes', 'ro': 1, 'req': 1,
                        'doc': 'The file that was hosted at the URL.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known time the file was hosted at the URL.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known time the file was hosted at the URL.'}),
                ]),

                ('inet:asn', {'ptype': 'inet:asn'}, (
                    ('name', {'ptype': 'str:lwr', 'defval': '??',
                        'doc': 'The name of the organization currently responsible for the ASN.'}),
                    ('owner', {'ptype': 'ou:org',
                        'doc': 'The guid of the organization currently responsible for the ASN.'}),
                )),

                ('inet:asnet4', {'ptype': 'inet:asnet4'}, [
                     ('asn', {'ptype': 'inet:asn', 'ro': 1,
                         'doc': 'The Autonomous System Number (ASN) of the netblock.'}),
                     ('net4', {'ptype': 'inet:net4', 'ro': 1,
                         'doc': 'The IPv4 address range assigned to the ASN.'}),
                     ('net4:min', {'ptype': 'inet:ipv4', 'ro': 1,
                         'doc': 'The first IPv4 in the range assigned to the ASN.'}),
                     ('net4:max', {'ptype': 'inet:ipv4', 'ro': 1,
                         'doc': 'The last IPv4 in the range assigned to the ASN.'}),
                 ]),

                ('inet:user', {'ptype': 'inet:user'}, []),

                ('inet:group', {'ptype': 'inet:group'}, []),

                ('inet:passwd', {'ptype': 'inet:passwd'}, [
                    ('md5', {'ptype': 'hash:md5', 'ro': 1,
                        'doc': 'The computed MD5 hash of the password.'}),
                    ('sha1', {'ptype': 'hash:sha1', 'ro': 1,
                        'doc': 'The computed SHA1 hash of the password.'}),
                    ('sha256', {'ptype': 'hash:sha256', 'ro': 1,
                        'doc': 'The computed SHA256 hash of the password.'}),
                ]),

                ('inet:mac', {'ptype': 'inet:mac'}, [
                    ('vendor', {'ptype': 'str', 'defval': '??',
                        'doc': 'The vendor associated with the 24-bit prefix of a MAC address.'}),
                ]),

                ('inet:fqdn', {'ptype': 'inet:fqdn'}, [
                    ('sfx', {'ptype': 'bool', 'defval': 0,
                        'doc': 'Set to 1 if the fqdn is considered a "suffix".'}),
                    ('zone', {'ptype': 'bool', 'defval': 0,
                        'doc': 'Set to 1 if the fqdn is a logical zone (under a suffix).'}),
                    ('domain', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The parent fqdn of the fqdn.'}),
                    ('host', {'ptype': 'str', 'ro': 1,
                        'doc': 'The host portion of the fqdn.'}),
                    ('created', {'ptype': 'time:min',
                        'doc': 'The earliest known registration (creation) date for the fqdn.'}),
                    ('updated', {'ptype': 'time:max',
                        'doc': 'The last known updated date for the fqdn.'}),
                    ('expires', {'ptype': 'time:max',
                        'doc': 'The current expiration date for the fqdn.'}),
                ]),

                ('inet:email', {'ptype': 'inet:email'}, [
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain of the email address.'}),
                    ('user', {'ptype': 'inet:user', 'ro': 1,
                        'doc': 'The username of the email address.'}),
                ]),

                ('inet:tcp4', {'ptype': 'inet:srv4'}, [
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 address of the TCP server.'}),
                    ('port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The port of the IPv4 TCP server.'}),
                ]),

                ('inet:udp4', {'ptype': 'inet:srv4'}, [
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 address of the UDP server.'}),
                    ('port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The port of the IPv4 UDP server.'}),
                ]),

                ('inet:tcp6', {'ptype': 'inet:srv6'}, [
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The IPv6 address of the TCP server.'}),
                    ('port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The port of the IPv6 TCP server.'}),
                ]),

                ('inet:udp6', {'ptype': 'inet:srv6'}, [
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The IPv6 address of the UDP server.'}),
                    ('port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The port of the IPv6 UDP server.'}),
                ]),

                ('inet:flow', {}, (
                    ('time', {'ptype': 'time',
                        'doc': 'The time the network connection was initiated.'}),
                    ('duration', {'ptype': 'int',
                        'doc': 'The duration of the flow in seconds.'}),

                    ('dst:host', {'ptype': 'it:host',
                        'doc': 'The guid of the destination host.'}),
                    ('dst:proc', {'ptype': 'it:exec:proc',
                        'doc': 'The guid of the destination process.'}),
                    ('dst:exe', {'ptype': 'file:bytes',
                        'doc': 'The file (executable) that received the connection.'}),
                    ('dst:txbytes', {'ptype': 'int',
                        'doc': 'The number of bytes sent by the destination host / process / file.'}),

                    ('dst:tcp4', {'ptype': 'inet:tcp4',
                        'doc': 'The destination IPv4 address / port for an IPv4 TCP connection.'}),
                    ('dst:tcp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The destination IPv4 address.'}),
                    ('dst:tcp4:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The destination IPv4 port.'}),

                    ('dst:udp4', {'ptype': 'inet:udp4',
                        'doc': 'The destination IPv4 address / port for an IPv4 UDP connection.'}),
                    ('dst:udp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The destination IPv4 address.'}),
                    ('dst:udp4:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The destination IPv4 port.'}),

                    ('dst:tcp6', {'ptype': 'inet:tcp6',
                        'doc': 'The destination IPv6 address / port for an IPv6 TCP connection.'}),
                    ('dst:tcp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The destination IPv6 address.'}),
                    ('dst:tcp6:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The destination IPv6 port.'}),

                    ('dst:udp6', {'ptype': 'inet:udp6',
                        'doc': 'The destination IPv6 address / port for an IPv6 UDP connection.'}),
                    ('dst:udp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The destination IPv6 address.'}),
                    ('dst:udp6:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The destination IPv6 port.'}),

                    ('src:host', {'ptype': 'it:host',
                        'doc': 'The guid of the source host.'}),
                    ('src:proc', {'ptype': 'it:exec:proc',
                        'doc': 'The guid of the source process.'}),
                    ('src:exe', {'ptype': 'file:bytes',
                        'doc': 'The file (executable) that created the connection.'}),
                    ('src:txbytes', {'ptype': 'int',
                        'doc': 'The number of bytes sent by the source host / process / file.'}),

                    ('src:tcp4', {'ptype': 'inet:tcp4',
                        'doc': 'The source IPv4 address / port for an IPv4 TCP connection.'}),
                    ('src:tcp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The source IPv4 address.'}),
                    ('src:tcp4:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The source IPv4 port.'}),

                    ('src:udp4', {'ptype': 'inet:udp4',
                        'doc': 'The source IPv4 address / port for an IPv4 UDP connection.'}),
                    ('src:udp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The source IPv4 address.'}),
                    ('src:udp4:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The source IPv4 port.'}),

                    ('src:tcp6', {'ptype': 'inet:tcp6',
                        'doc': 'The source IPv6 address / port for an IPv6 TCP connection.'}),
                    ('src:tcp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The source IPv6 address.'}),
                    ('src:tcp6:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The source IPv6 port.'}),

                    ('src:udp6', {'ptype': 'inet:udp6',
                        'doc': 'The source IPv6 address / port for an IPv6 UDP connection.'}),
                    ('src:udp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The source IPv6 address.'}),
                    ('src:udp6:port', {'ptype': 'inet:port', 'ro': 1,
                        'doc': 'The source IPv6 port.'}),

                    ('from', {'ptype': 'guid',
                        'doc': 'The ingest source file/iden. Used for reparsing.'}),
                )),

                ('inet:iface', {}, (
                    ('latlong', {'ptype': 'geo:latlong',
                        'doc': 'The last known latitude/longitude for the node'}),
                    ('host', {'ptype': 'it:host',
                        'doc': 'The guid of the host the interface is associated with.'}),
                    ('type', {'ptype': 'str:lwr',
                        'doc': 'The free-form interface type'}),
                    ('mac', {'ptype': 'inet:mac',
                        'doc': 'The ethernet (MAC) address of the interface.'}),
                    ('ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The IPv4 address of the interface.'}),
                    ('ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The IPv6 address of the interface.'}),
                    ('phone', {'ptype': 'tel:phone',
                        'doc': 'The telephone number of the interface.'}),
                    ('wifi:ssid', {'ptype': 'inet:wifi:ssid',
                        'doc': 'The wifi SSID of the interface.'}),
                    ('wifi:bssid', {'ptype': 'inet:mac',
                        'doc': 'The wifi BSSID of the interface.'}),
                    ('mob:imei', {'ptype': 'tel:mob:imei',
                        'doc': 'The IMEI of the interface.'}),
                    ('mob:imsi', {'ptype': 'tel:mob:imsi',
                        'doc': 'The IMSI of the interface.'}),
                )),

                ('inet:wifi:ap', {}, [
                    ('ssid', {'ptype': 'inet:wifi:ssid',
                        'doc': 'The SSID for the wireless access point.'}),
                    ('bssid', {'ptype': 'inet:wifi:ssid',
                        'doc': 'The SSID for the wireless access point.'}),
                ]),

                ('inet:wifi:ssid', {}, []),

                ('inet:web:acct', {'ptype': 'inet:web:acct'}, [

                    ('site', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The site or service associated with the account.'}),

                    ('user', {'ptype': 'inet:user', 'ro': 1,
                        'doc': 'The unique identifier for the account (may be different from the common '
                            'name or display name).'}),

                    ('url', {'ptype': 'inet:url',
                        'doc': 'The service provider URL where the account is hosted.'}),

                    ('name', {'ptype': 'inet:user',
                        'doc': 'The localized name associated with the account (may be different from the '
                            'account identifier, e.g., a display name).'}),

                    ('name:en', {'ptype': 'inet:user',
                        'doc': 'The English version of the name associated with the (may be different from '
                            'the account identifier, e.g., a display name).'}),

                    ('avatar', {'ptype': 'file:bytes',
                        'doc': 'The file representing the avatar (e.g., profile picture) for the account.'}),

                    ('tagline', {'ptype': 'str:txt',
                        'doc': 'The text of the account status or tag line.'}),

                    ('webpage', {'ptype': 'inet:url',
                        'doc': 'A related URL specified by the account (e.g., a personal or company web '
                             'page, blog, etc.).'}),

                    ('latlong', {'ptype': 'geo:latlong',
                        'doc': 'The last known latitude/longitude for the node'}),

                    ('loc', {'ptype': 'str:lwr',
                        'doc': 'A self-declared location for the account.'}),

                    ('occupation', {'ptype': 'str:lwr',
                        'doc': 'A self-declared occupation for the account.'}),
                    ('dob', {'ptype': 'time',
                        'doc': 'A self-declared date of birth for the account (if the account belongs to a person).'}),

                    # ('gender',{'ptype':'inet:fqdn','ro':1}),
                    # ('bio:bt',{'ptype':'wtf','doc':'The web account's self documented blood type'}),

                    ('realname', {'ptype': 'ps:name',
                        'doc': 'The localized version of the real name of the account owner / registrant.'}),
                    ('realname:en', {'ptype': 'ps:name',
                        'doc': 'The English version of the real name of the account owner / registrant.'}),
                    ('email', {'ptype': 'inet:email',
                        'doc': 'The email address associated with the account.'}),
                    ('phone', {'ptype': 'tel:phone',
                        'doc': 'The phone number associated with the account.'}),
                    ('signup', {'ptype': 'time',
                        'doc': 'The date and time the account was registered.'}),
                    ('signup:ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The IPv4 address used to sign up for the account.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known date of activity for the account.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known date of activity for the account.'}),
                    ('passwd', {'ptype': 'inet:passwd',
                        'doc': 'The current password for the account.'})
                ]),

                ('inet:web:chprofile', {}, [
                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The web account associated with the change.'}),
                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The site or service associated with the account.'}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1,
                        'doc': 'The unique identifier for the account.'}),
                    ('ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The source IPv4 address used to make the account change.'}),
                    ('ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The source IPv6 address used to make the account change.'}),
                    ('time', {'ptype': 'time',
                        'doc': 'The date and time when the account change occurred.'}),
                    ('pv', {'ptype': 'propvalu', 'ro': 1, 'req': 1,
                        'doc': 'The prop=valu of the account property that was changed. Valu should be '
                            'the old / original value, while the new value should be updated on the '
                            'inet:web:acct form.'}),
                    ('pv:prop', {'ptype': 'str', 'ro': 1,
                        'doc': 'The property that was changed.'}),
                    ('pv:intval', {'ptype': 'int', 'ro': 1,
                        'doc': 'The normed value of the property (specified by pv), if the property is an integer.'}),
                    ('pv:strval', {'ptype': 'str', 'ro': 1,
                        'doc': 'The normed value of the property (specified by pv), if the property is a string.'}),
                ]),

                ('inet:web:logon', {'ptype': 'inet:web:logon'}, [
                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The web account associated with the logon event.'}),
                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The site or service associated with the account.'}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1,
                        'doc': 'The unique identifier for the account.'}),
                    ('time', {'ptype': 'time',
                        'doc': 'The date and time the account logged into the service.'}),
                    ('ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The source IPv4 address of the logon.'}),
                    ('ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The source IPv6 address of the logon.'}),
                    ('logout', {'ptype': 'time',
                        'doc': 'The date and time the account logged out of the service.'})
                ]),

                ('inet:web:action', {'ptype': 'inet:web:action'}, [
                    ('act', {'ptype': 'str:lwr', 'req': 1,
                        'doc': 'The action performed by the account.'}),
                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The web account associated with the action.'}),
                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The site or service associated with the account.'}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1,
                        'doc': 'The unique identifier for the account.'}),
                    ('info', {'ptype': 'json',
                        'doc': 'Any other data associated with the action.'}),
                    ('time', {'ptype': 'time',
                        'doc': 'The date and time the account performed the action.'}),
                    ('ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The source IPv4 address of the action.'}),
                    ('ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The source IPv6 address of the action.'}),
                ]),

                ('inet:web:actref', {}, [
                    ('act', {'ptype': 'inet:web:action', 'ro': 1, 'req': 1,
                        'doc': 'The action that references the given node.'}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1, 'req': 1,
                        'doc': 'The prop=valu that is referenced as part of the action.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                        'doc': 'The property (form) of the referenced object, as specified by the propvalu.'}),
                    ('xref:intval', {'ptype': 'int', 'ro': 1,
                        'doc': 'The normed value of the form that was referenced, if the value is an integer.'}),
                    ('xref:strval', {'ptype': 'str', 'ro': 1,
                        'doc': 'The normed value of the form that was referenced, if the value is a string.'}),
                ]),

                ('inet:web:group', {}, [
                    ('site', {'ptype': 'inet:fqdn', 'ro': 1,
                         'doc': 'The site or service associated with the group.'}),
                    ('id', {'ptype': 'inet:group', 'ro': 1,
                         'doc': 'The site-specific unique identifier for the group (may be different from '
                              'the common name or display name).'}),
                    ('name', {'ptype': 'inet:group',
                         'doc': 'The localized name associated with the group (may be different from '
                              'the account identifier, e.g., a display name).'}),
                    ('name:en', {'ptype': 'inet:group',
                         'doc': 'The English version of the name associated with the group (may be different '
                              'from the localized name).'}),
                    ('url', {'ptype': 'inet:url',
                         'doc': 'The service provider URL where the group is hosted.'}),
                    ('avatar', {'ptype': 'file:bytes',
                         'doc': 'The file representing the avatar (e.g., profile picture) for the group.'}),
                    ('desc', {'ptype': 'str:txt',
                         'doc': 'The text of the description of the group.'}),
                    ('webpage', {'ptype': 'inet:url',
                         'doc': 'A related URL specified by the group (e.g., primary web site, etc.).'}),
                    ('loc', {'ptype': 'str:lwr',
                         'doc': 'A self-declared location for the group.'}),
                    ('latlong', {'ptype': 'geo:latlong',
                         'doc': 'The last known latitude/longitude for the node'}),
                    ('signup', {'ptype': 'time',
                         'doc': 'The date and time the group was created on the site.'}),
                    ('signup:ipv4', {'ptype': 'inet:ipv4',
                         'doc': 'The IPv4 address used to create the group.'}),
                    ('signup:ipv6', {'ptype': 'inet:ipv6',
                         'doc': 'The IPv6 address used to create the group.'}),
                    ('seen:min', {'ptype': 'time:min',
                         'doc': 'The earliest known date of activity for the group.'}),
                    ('seen:max', {'ptype': 'time:max',
                         'doc': 'The most recent known date of activity for the group.'}),
                ]),

                ('inet:web:post', {}, [
                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The web account that made the post.'}),
                    ('text', {'ptype': 'str:txt', 'ro': 1,
                        'doc': 'The text of the post.'}),
                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The site or service associated with the account.'}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1,
                        'doc': 'The unique identifier for the account.'}),
                    ('time', {'ptype': 'time',
                        'doc': 'The date and time that the post was made.'}),
                    ('url', {'ptype': 'inet:url',
                        'doc': 'The URL where the post is published / visible.'}),
                    ('file', {'ptype': 'file:bytes',
                        'doc': 'The file that was attached to the post.'}),
                    ('replyto', {'ptype': 'inet:web:post',
                        'doc': 'The post that this post is in reply to.'}),
                    ('repost', {'ptype': 'inet:web:post',
                        'doc': 'The original post that this is a repost of.'}),
                ]),

                ('inet:web:postref', {}, [
                    ('post', {'ptype': 'inet:web:post', 'ro': 1, 'req': 1,
                        'doc': 'The web post that references the given node.'}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1, 'req': 1,
                        'doc': 'The prop=valu that is referenced by the post.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                        'doc': 'The property (form) of the referenced object, as specified by the propvalu.'}),
                    ('xref:intval', {'ptype': 'int', 'ro': 1,
                        'doc': 'The normed value of the form that was referenced, if the value is an integer.'}),
                    ('xref:strval', {'ptype': 'str', 'ro': 1,
                        'doc': 'The normed value of the form that was referenced, if the value is a string.'}),
                ]),

                ('inet:web:mesg', {}, [
                    ('from', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The web account that sent the message.'}),
                    ('to', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The web account that received the message.'}),
                    ('time', {'ptype': 'time', 'ro': 1, 'req': 1,
                        'doc': 'The date and time at which the message was sent.'}),
                    ('url', {'ptype': 'inet:url',
                        'doc': 'The URL where the message is posted / visible.'}),
                    ('text', {'ptype': 'str:txt',
                        'doc': 'The text of the message.'}),
                    ('file', {'ptype': 'file:bytes',
                        'doc': 'The file attached to or sent with the message.'}),
                ]),

                ('inet:web:follows', {}, [
                    ('follower', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The account following an account.'}),
                    ('followee', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The account followed by an account.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known date when the "follows" relationship existed.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known date when the "follows" relationship existed.'}),
                ]),

                ('inet:web:memb', {}, [
                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The account that is a member of the group.'}),
                    ('group', {'ptype': 'inet:web:group', 'ro': 1, 'req': 1,
                        'doc': 'The group that the account is a member of.'}),
                    ('title', {'ptype': 'str:lwr',
                        'doc': 'The title or status of the member (e.g., admin, new member, etc.).'}),
                    ('joined', {'ptype': 'time',
                        'doc': 'The date / time the account joined the group.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known date when the account was a member of the group.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known date when the account was a member of the group.'}),
                ]),

                ('inet:web:file', {}, [
                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1, 'req': 1,
                        'doc': 'The account that owns or is associated with the file.'}),
                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The site or service associated with the account.'}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1,
                        'doc': 'The unique identifier for the account.'}),
                    ('file', {'ptype': 'file:bytes', 'ro': 1, 'req': 1,
                        'doc': 'The file owned by or associated with the account.'}),
                    ('name', {'ptype': 'file:base',
                        'doc': 'The name of the file owned by or associated with the account.'}),
                    ('posted', {'ptype': 'time',
                        'doc': 'The date and time the file was posted / submitted.'}),
                    ('ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The source IPv4 address used to post or submit the file.'}),
                    ('ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The source IPv6 address used to post or submit the file.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known date the file was posted / submitted / associated '
                            'with the account.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known date the file was posted / submitted / associated'
                            'with the account.'}),
                ]),

                ('inet:whois:reg', {}, []),

                ('inet:whois:rar', {}, []),

                ('inet:whois:regmail', {'ptype': 'inet:whois:regmail'}, [
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1, 'req': 1,
                        'doc': 'The domain associated with the registrant email address.'}),
                    ('email', {'ptype': 'inet:email', 'ro': 1, 'req': 1,
                        'doc': 'The registrant email address associated with the domain.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known date the registrant email was associated with the domain.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known date the registrant email was associated with the domain.'}),
                ]),

                ('inet:whois:rec', {'ptype': 'inet:whois:rec'}, [
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1, 'req': 1,
                        'doc': 'The domain associated with the whois record.'}),
                    ('asof', {'ptype': 'time', 'ro': 1, 'req': 1,
                        'doc': 'The date of the whois record.'}),
                    ('text', {'ptype': 'str:lwr',
                        'doc': 'The full text of the whois record.'}),
                    ('created', {'ptype': 'time',
                        'doc': 'The "created" time from the whois record.'}),
                    ('updated', {'ptype': 'time',
                        'doc': 'The "last updated" time from the whois record.'}),
                    ('expires', {'ptype': 'time',
                        'doc': 'The "expires" time from the whois record.'}),
                    ('registrar', {'ptype': 'inet:whois:rar', 'defval': '??',
                        'doc': 'The registrar name from the whois record.'}),
                    ('registrant', {'ptype': 'inet:whois:reg', 'defval': '??',
                        'doc': 'The registrant name from the whois record.'}),
                ]),

                ('inet:whois:recns', {}, [
                    ('ns', {'ptype': 'inet:fqdn', 'ro': 1, 'req': 1,
                        'doc': 'A nameserver for a domain as listed in the domain whois record.'}),
                    ('rec', {'ptype': 'inet:whois:rec', 'ro': 1, 'req': 1,
                        'doc': 'The whois record containing the nameserver data.'}),
                    ('rec:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain associated with the whois record.'}),
                    ('rec:asof', {'ptype': 'time', 'ro': 1,
                        'doc': 'The date of the whois record.'}),
                ]),

                ('inet:whois:contact', {}, [
                    ('rec', {'ptype': 'inet:whois:rec', 'ro': 1, 'req': 1,
                        'doc': 'The whois record containing the contact data.'}),
                    ('rec:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain associated with the whois record.'}),
                    ('rec:asof', {'ptype': 'time', 'ro': 1,
                        'doc': 'The date of the whois record.'}),
                    ('type', {'ptype': 'str:lwr',
                        'doc': 'The contact type (e.g., registrar, registrant, admin, billing, tech, etc.).'}),
                    ('id', {'ptype': 'str:lwr',
                        'doc': 'The ID associated with the contact.'}),
                    ('name', {'ptype': 'str:lwr',
                        'doc': 'The name of the contact.'}),
                    ('email', {'ptype': 'inet:email',
                        'doc': 'The email address of the contact.'}),
                    ('orgname', {'ptype': 'ou:name',
                        'doc': 'The name of the contact organization.'}),
                    ('address', {'ptype': 'str:lwr',
                        'doc': 'The content of the street address field(s) of the contract.'}),  # FIXME street address type
                    ('city', {'ptype': 'str:lwr',
                        'doc': 'The content of the city field of the contact.'}),
                    # ('zip',{'ptype':'str:lwr'}),
                    ('state', {'ptype': 'str:lwr',
                        'doc': 'The content of the state field of the contact.'}),
                    ('country', {'ptype': 'pol:iso2',
                        'doc': 'The two-letter country code of the contact.'}),
                    ('phone', {'ptype': 'tel:phone',
                        'doc': 'The content of the phone field of the contact.'}),
                    ('fax', {'ptype': 'tel:phone',
                        'doc': 'The content of the fax field of the contact.'}),
                    ('url', {'ptype': 'inet:url',
                        'doc': 'The URL specified for the contact'}),
                    ('whois:fqdn', {'ptype': 'inet:fqdn',
                        'doc': 'The whois server FQDN for the given contact (most likely a registrar).'}),
                ]),

                ('inet:ssl:tcp4cert', {'ptype': 'inet:ssl:tcp4cert'}, [
                    ('tcp4', {'ptype': 'inet:tcp4', 'ro': 1, 'req': 1,
                        'doc': 'The IPv4 TCP server where the certificate was observed.'}),
                    ('cert', {'ptype': 'file:bytes', 'ro': 1, 'req': 1,
                        'doc': 'The SSL certificate.'}),
                    ('tcp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 address associated with the TCP server.'}),
                ]),

                ('inet:rfc2822:addr', {}, (
                    ('name', {'ptype': 'ps:name', 'ro': 1,
                        'doc': 'The name field parsed from an RFC 2822 address string.'}),
                    ('email', {'ptype': 'inet:email', 'ro': 1,
                        'doc': 'The email field parsed from an RFC 2822 address string.'}),
                )),

                ('inet:http:request', {}, (

                    ('flow', {'ptype': 'inet:flow',
                        'doc': 'The inet:flow which contained the HTTP request.'}),

                    ('host', {'ptype': 'it:host',
                        'doc': 'The it:host which sent the HTTP request.'}),

                    ('time', {'ptype': 'time',
                        'doc': 'The time that the HTTP request was sent.'}),

                    # HTTP protocol specific fields...
                    ('method', {'ptype': 'str',
                        'doc': 'The HTTP request method string.'}),

                    ('path', {'ptype': 'str',
                        'doc': 'The requested HTTP path (without query parameters).'}),

                    ('query', {'ptype': 'str',
                        'doc': 'The HTTP query string which optionally folows the path.'}),

                    ('body', {'ptype': 'file:bytes',
                        'doc': 'The body of the HTTP request.'})
                )),

                ('inet:http:response', {}, (

                    ('flow', {'ptype': 'inet:flow',
                        'doc': 'The inet:flow which contained the HTTP response.'}),

                    ('host', {'ptype': 'it:host',
                        'doc': 'The it:host which sent the HTTP response.'}),

                    ('time', {'ptype': 'time',
                        'doc': 'The time that the HTTP response was sent.'}),

                    ('request', {'ptype': 'inet:http:request',
                        'doc': 'The HTTP request which caused the response.'}),

                    # HTTP response protocol fields....
                    ('code', {'ptype': 'int',
                        'doc': 'The HTTP response code.'}),

                    ('reason', {'ptype': 'str',
                        'doc': 'The HTTP response reason string.'}),

                    ('body', {'ptype': 'file:bytes',
                        'doc': 'The HTTP response body data.'}),

                )),

                ('inet:http:header', {}, (

                    ('name', {'ptype': 'str:lwr', 'ro': 1,
                        'doc': 'The name of the HTTP header.'}),

                    ('value', {'ptype': 'str', 'ro': 1,
                        'doc': 'The value of the HTTP header.'}),
                )),

                ('inet:http:param', {}, (

                    ('name', {'ptype': 'str:lwr', 'ro': 1,
                        'doc': 'The name of the HTTP query parameter.'}),

                    ('value', {'ptype': 'str', 'ro': 1,
                        'doc': 'The value of the HTTP query parameter.'}),
                )),

                ('inet:http:reqhead', {}, (

                    ('request', {'ptype': 'inet:http:request', 'ro': 1,
                        'doc': 'The HTTP request which contained the header.'}),

                    ('header', {'ptype': 'inet:http:header', 'ro': 1,
                        'doc': 'The HTTP header contained in the request.'}),

                    ('header:name', {'ptype': 'str:lwr', 'ro': 1,
                        'doc': 'The HTTP header name'}),

                    ('header:value', {'ptype': 'str', 'ro': 1,
                        'doc': 'The HTTP header value.'}),
                )),

                ('inet:http:reqparam', {}, (

                    ('request', {'ptype': 'inet:http:request', 'ro': 1,
                        'doc': 'The HTTP request which contained the header.'}),

                    ('param', {'ptype': 'inet:http:header', 'ro': 1,
                        'doc': 'The HTTP query parameter contained in the request.'}),

                    ('param:name', {'ptype': 'str:lwr', 'ro': 1,
                        'doc': 'The HTTP query parameter name'}),

                    ('param:value', {'ptype': 'str', 'ro': 1,
                        'doc': 'The HTTP query parameter value.'}),
                )),
            )
        }

        return (('inet', modl),)
