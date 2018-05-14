# FIXME
# "it:*" - inet:client, inet:server, inet:flow, inet:http:request
# "nullvals" - inet:mac, inet:ipv4, inet:ipv6
# "file:*" - inet:passwd, inet:web:file

# stdlib
import socket
import logging
import ipaddress
import email.utils

# third party code
import regex

# custom code
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lookup.iana as s_l_iana

logger = logging.getLogger(__name__)
fqdnre = regex.compile(r'^[\w._-]+$', regex.U)
srv6re = regex.compile(r'^\[([a-f0-9:]+)\]:(\d+)$')

cidrmasks = [((0xffffffff - (2 ** (32 - i) - 1)), (2 ** (32 - i))) for i in range(33)]


class Addr(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def indx(self, norm):
        return norm.encode('utf-8')

    def _getPort(self, valu):
        port = None
        parts = valu.split(':', 1)
        if len(parts) == 2:
            valu, port = parts
            port = self.modl.type('inet:port').norm(port)[0]
            return valu, port, f':{port}'
        return valu, None, ''

    def _normPyStr(self, valu):
        orig = valu
        subs = {}

        proto = 'tcp'
        parts = valu.split('://', 1)
        if len(parts) == 2:
            proto, valu = parts

        if proto not in ('tcp', 'udp', 'icmp', 'host'):
            raise s_exc.BadTypeValu(orig, mesg='inet:addr protocol must be in: tcp, udp, icmp, host')

        # Treat as host if proto is host
        if proto == 'host':

            valu, port, pstr = self._getPort(valu)
            if port:
                subs['port'] = port

            host = s_common.guid(valu)
            subs['host'] = host

            return f'host://{host}{pstr}', {'subs': subs}

        # Treat as IPv6 if starts with [ or contains multiple :
        if valu.startswith('['):
            match = srv6re.match(valu)
            if match:
                ipv6, port = match.groups()

                ipv6 = self.modl.type('inet:ipv6').norm(ipv6)[0]
                port = self.modl.type('inet:port').norm(port)[0]
                subs['ipv6'] = ipv6
                subs['port'] = port

                return f'{proto}://[{ipv6}]:{port}', {'subs': subs}

            raise s_exc.BadTypeValu(orig, mesg='invalid IPv6 w/ port')

        elif valu.count(':') >= 2:
            ipv6 = self.modl.type('inet:ipv6').norm(valu)[0]
            subs['ipv6'] = ipv6
            return f'{proto}://{ipv6}', {'subs': subs}

        # Otherwise treat as IPv4
        valu, port, pstr = self._getPort(valu)
        if port:
            subs['port'] = port

        ipv4 = self.modl.type('inet:ipv4').norm(valu)[0]
        ipv4_repr = self.modl.type('inet:ipv4').repr(ipv4)
        subs['ipv4'] = ipv4

        return f'{proto}://{ipv4_repr}{pstr}', {'subs': subs}


class Cidr4(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):
        ip_str, mask_str = valu.split('/', 1)

        mask_int = int(mask_str)
        if mask_int > 32 or mask_int < 0:
            raise s_exc.BadTypeValu(valu, mesg='Invalid CIDR Mask')

        ip_int = self.modl.type('inet:ipv4').norm(ip_str)[0]

        mask = cidrmasks[mask_int]
        network = ip_int & mask[0]
        broadcast = network + mask[1] - 1
        network_str = self.modl.type('inet:ipv4').repr(network)

        norm = f'{network_str}/{mask_int}'
        info = {
            'subs': {
                'broadcast': broadcast,
                'mask': mask_int,
                'network': network,
            }
        }
        return norm, info

    def indx(self, norm):
        return norm.encode('utf8')

class Email(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        try:
            user, fqdn = valu.split('@', 1)

            fqdnnorm, fqdninfo = self.modl.type('inet:fqdn').norm(fqdn)
            usernorm, userinfo = self.modl.type('inet:user').norm(user)
        except Exception as e:
            raise s_exc.BadTypeValu(valu, mesg=e)

        norm = f'{usernorm}@{fqdnnorm}'
        info = {
            'subs': {
                'fqdn': fqdnnorm,
                'user': usernorm,
            }
        }
        return norm, info

    def indx(self, norm):
        return norm.encode('utf8')

class Fqdn(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        valu = valu.replace('[.]', '.')
        if not fqdnre.match(valu):
            raise s_exc.BadTypeValu(valu)

        try:
            valu = valu.encode('idna').decode('utf8').lower()
        except UnicodeError as e:
            raise s_exc.BadTypeValu(valu)

        parts = valu.split('.', 1)
        subs = {'host': parts[0]}

        if len(parts) == 2:
            subs['domain'] = parts[1]
        else:
            subs['sfx'] = 1

        return valu, {'subs': subs}

    def indx(self, norm):
        return norm[::-1].encode('utf8')

    def indxByEq(self, valu):

        if valu[0] == '*':
            indx = valu[1:][::-1].encode('utf8')
            return (
                ('pref', indx),
            )

        if valu.find('*') != -1:
            raise s_exc.BadLiftValu(valu=valu, mesg='Wild card may only appear at the beginning.')

        return s_types.Type.indxByEq(self, valu)

    def repr(self, valu):
        try:
            return valu.encode('utf8').decode('idna')
        except UnicodeError as e:
            if len(valu) >= 4 and valu[0:4] == 'xn--':
                logger.exception(msg='Failed to IDNA decode ACE prefixed inet:fqdn')
                return valu
            raise  # pragma: no cover


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

    def indxByEq(self, valu):

        if type(valu) == str and valu.find('/') != -1:
            addr, mask = valu.split('/', 1)
            norm, info = self.norm(addr)

            mask = cidrmasks[int(mask)]

            minv = norm & mask[0]

            mini = self.indx(minv)
            maxi = self.indx(minv + mask[1])

            return (
                ('range', (mini, maxi)),
            )

        return s_types.Type.indxByEq(self, valu)

class IPv6(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(int, self._normPyStr)
        self.setNormFunc(str, self._normPyStr)

    def indx(self, norm):
        return ipaddress.IPv6Address(norm).packed

    def _normPyStr(self, valu):
        try:

            v6 = ipaddress.IPv6Address(valu)
            v4 = v6.ipv4_mapped

            if v4 is not None:
                v4_int = self.modl.type('inet:ipv4').norm(v4.compressed)[0]
                v4_str = self.modl.type('inet:ipv4').repr(v4_int)
                return f'::ffff:{v4_str}', {'subs': {'ipv4': v4_int}}

            return ipaddress.IPv6Address(valu).compressed, {}

        except Exception as e:
            raise s_exc.BadTypeValu(valu)


class Rfc2822Addr(s_types.Type):
    '''
    An RFC 2822 compatible email address parser
    '''

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.indxcmpr['^='] = self.indxByPref

    def indxByPref(self, valu):
        valu = valu.replace('"', ' ').replace("'", ' ')
        valu = valu.strip().lower()
        valu = ' '.join(valu.split())
        return (
            ('pref', valu.encode('utf8')),
        )

    def indx(self, norm):
        return norm.encode('utf8')

    def _normPyStr(self, valu):

        # remove quotes for normalized version
        valu = valu.replace('"', ' ').replace("'", ' ')
        valu = valu.strip().lower()
        valu = ' '.join(valu.split())

        try:
            name, addr = email.utils.parseaddr(valu)
        except Exception as e:  # pragma: no cover
            # not sure we can ever really trigger this with a string as input
            raise s_exc.BadTypeValu(valu, mesg='email.utils.parsaddr failed: %s' % (e,))

        subs = {}
        if name:
            subs['name'] = name

        try:
            data = self.modl.type('inet:email').norm(addr)
            if len(data) is 2:
                mail = data[0]

            subs['email'] = mail
            if name:
                valu = '%s <%s>' % (name, mail)
            else:
                valu = mail
        except s_exc.BadTypeValu as e:
            pass  # it's all good, we just dont have a valid email addr

        return valu, {'subs': subs}

class Url(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def indx(self, norm):
        return norm.encode('utf8')

    def _normPyStr(self, valu):
        orig = valu
        subs = {}
        proto = ''
        authparts = None
        hostparts = ''
        pathpart = ''

        # Protocol
        try:
            proto, valu = valu.split('://', 1)
            proto = proto.lower()
            subs['proto'] = proto
        except Exception as e:
            raise s_exc.BadTypeValu(orig, mesg='Invalid/Missing protocol')

        # Resource Path
        parts = valu.split('/', 1)
        if len(parts) == 2:
            valu, pathpart = parts
            pathpart = f'/{pathpart}'
        subs['path'] = pathpart

        # Optional User/Password
        parts = valu.split('@', 1)
        if len(parts) == 2:
            authparts, valu = parts

            userpass = authparts.split(':', 1)
            subs['user'] = userpass[0]
            if len(userpass) == 2:
                subs['passwd'] = userpass[1]

        # Host (FQDN, IPv4, or IPv6)
        host = None
        port = None

        # Treat as IPv6 if starts with [ or contains multiple :
        if valu.startswith('[') or valu.count(':') >= 2:
            try:
                match = srv6re.match(valu)
                if match:
                    valu, port = match.groups()

                ipv6, ipv6_subs = self.modl.type('inet:ipv6').norm(valu)
                subs['ipv6'] = ipv6

                host = self.modl.type('inet:ipv6').repr(ipv6)
                if match:
                    host = f'[{host}]'

            except Exception as e:
                pass

        else:
            # FQDN and IPv4 handle ports the same way
            fqdnipv4_parts = valu.split(':', 1)
            part = fqdnipv4_parts[0]
            if len(fqdnipv4_parts) is 2:
                port = fqdnipv4_parts[1]

            # IPv4
            try:
                # Norm and repr to handle fangs
                ipv4 = self.modl.type('inet:ipv4').norm(part)[0]
                host = self.modl.type('inet:ipv4').repr(ipv4)
                subs['ipv4'] = ipv4
            except Exception as e:
                pass

            # FQDN
            if host is None:
                try:
                    host = self.modl.type('inet:fqdn').norm(part)[0]
                    subs['fqdn'] = host
                except Exception as e:
                    pass

        # Raise exception if there was no FQDN, IPv4, or IPv6
        if host is None:
            raise s_exc.BadTypeValu(orig, mesg='No valid host')

        # Optional Port
        if port is not None:
            port = self.modl.type('inet:port').norm(port)[0]
            subs['port'] = port
        else:
            # Look up default port for protocol, but don't add it back into the url
            defport = s_l_iana.services.get(proto)
            if defport:
                subs['port'] = self.modl.type('inet:port').norm(defport)[0]

        # Set up Normed URL
        if authparts:
            hostparts = f'{authparts}@'
        hostparts = f'{hostparts}{host}'
        if port is not None:
            hostparts = f'{hostparts}:{port}'
        norm = f'{proto}://{hostparts}{pathpart}'

        return norm, {'subs': subs}

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

                    ('inet:addr', 'synapse.models.inet.Addr', {}, {
                        'doc': 'A network layer URL-like format to represent tcp/udp/icmp clients and servers.',
                        'ex': 'tcp://1.2.3.4:80'
                    }),

                    ('inet:cidr4', 'synapse.models.inet.Cidr4', {}, {
                        'doc': 'An IPv4 address block in Classless Inter-Domain Routing (CIDR) notation.',
                        'ex': '1.2.3.0/24'
                    }),

                    ('inet:email', 'synapse.models.inet.Email', {}, {
                        'doc': 'An e-mail address.'}),

                    ('inet:fqdn', 'synapse.models.inet.Fqdn', {}, {
                        'doc': 'A Fully Qualified Domain Name (FQDN).',
                        'ex': 'vertex.link'}),

                    ('inet:ipv4', 'synapse.models.inet.IPv4', {}, {
                        'doc': 'An IPv4 address.',
                        'ex': '1.2.3.4'
                    }),

                    ('inet:ipv6', 'synapse.models.inet.IPv6', {}, {
                        'doc': 'An IPv6 address.',
                        'ex': '2607:f8b0:4004:809::200e'
                    }),

                    ('inet:rfc2822:addr', 'synapse.models.inet.Rfc2822Addr', {}, {
                        'doc': 'An RFC 2822 Address field.',
                        'ex': '"Visi Kenshoto" <visi@vertex.link>'
                    }),

                    ('inet:url', 'synapse.models.inet.Url', {}, {
                        'doc': 'A Universal Resource Locator (URL).',
                        'ex': 'http://www.woot.com/files/index.html'
                    }),

                ),

                'types': (

                    ('inet:asn', ('int', {}), {
                        'doc': 'An Autonomous System Number (ASN).'
                    }),

                    ('inet:asnet4', ('comp', {'fields': (('asn', 'inet:asn'), ('net4', 'inet:net4'))}), {
                        'doc': 'An Autonomous System Number (ASN) and its associated IPv4 address range.',
                        'ex': '(54959, ("1.2.3.4", "1.2.3.20"))',
                    }),

                    ('inet:client', ('inet:addr', {}), {
                        'doc': 'A network client address.'
                    }),

                    ('inet:download', ('guid', {}), {
                        'doc': 'An instance of a file downloaded from a server.',
                    }),

                    ('inet:group', ('str', {}), {
                        'doc': 'A group name string.'
                    }),

                    ('inet:flow', ('guid', {}), {
                        'doc': 'An individual network connection between a given source and destination.'
                    }),

                    ('inet:http:request', ('guid', {}), {
                        'doc': 'A single client HTTP request.',
                    }),

                    ('inet:iface', ('guid', {}), {
                        'doc': 'A network interface with a set of associated protocol addresses.'
                    }),

                    ('inet:mac', ('str', {'lower': True, 'regex': '^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$'}), {
                        # 'nullval': '??',  # FIXME this should not be here
                        'doc': 'A 48-bit Media Access Control (MAC) address.',
                        'ex': 'aa:bb:cc:dd:ee:ff'
                    }),

                    ('inet:net4', ('range', {'type': ('inet:ipv4', {})}), {
                        'doc': 'An IPv4 address range.',
                        'ex': '("1.2.3.4", "1.2.3.20")'
                    }),

                    ('inet:passwd', ('str', {}), {
                        'doc': 'A password string.'
                    }),

                    ('inet:port', ('int', {'min': 0, 'max': 0xffff}), {
                        'doc': 'A network port.',
                        'ex': '80'
                    }),

                    ('inet:server', ('inet:addr', {}), {
                        'doc': 'A network server address.'
                    }),

                    ('inet:urlfile', ('comp', {'fields': (('url', 'inet:url'), ('file', 'file:bytes'))}), {
                        'doc': 'A file hosted at a specific Universal Resource Locator (URL).'
                    }),

                    ('inet:urlredir', ('comp', {'fields': (('src', 'inet:url'), ('dst', 'inet:url'))}), {
                        'doc': 'A URL that redirects to another URL, such as via a URL shortening service '
                               'or an HTTP 302 response.',
                        'ex': '(http://foo.com/,http://bar.com/)'
                    }),

                    ('inet:user', ('str', {'lower': True}), {
                        'doc': 'A username string.'
                    }),

                    ('inet:web:acct', ('comp', {'fields': (('site', 'inet:fqdn'), ('user', 'inet:user'))}), {
                        'doc': 'An account with a given Internet-based site or service.',
                        'ex': 'twitter.com/invisig0th'
                    }),

                    ('inet:web:action', ('guid', {}), {
                        'doc': 'An instance of an account performing an action at an Internet-based site or service.'
                    }),

                    ('inet:web:file', ('comp', {'fields': (('acct', 'inet:web:acct'), ('file', 'file:bytes'))}), {
                        'doc': 'A file posted by a web account.'
                    }),

                    ('inet:web:follows', ('comp', {'fields': (('follower', 'inet:web:acct'), ('followee', 'inet:web:acct'))}), {
                        'doc': 'A web account follows or is connected to another web account.'
                    }),

                    ('inet:web:group', ('comp', {'fields': (('site', 'inet:fqdn'), ('id', 'inet:group'))}), {
                        'doc': 'A group hosted within or registered with a given Internet-based site or service.',
                        'ex': 'somesite.com/mycoolgroup'
                    }),

                    ('inet:web:logon', ('guid', {}), {
                        'doc': 'An instance of an account authenticating to an Internet-based site or service.'
                    }),

                    ('inet:web:post', ('comp', {'fields': (('acct', 'inet:web:acct'), ('text', 'str'))}), {
                        'doc': 'A post made by a web account.'
                    }),

                    ('inet:whois:rar', ('str', {'lower': True}), {
                        'doc': 'A domain registrar.',
                        'ex': 'godaddy, inc.'
                    }),

                    ('inet:whois:rec', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('asof', 'time'))}), {
                        'doc': 'A domain whois record'
                    }),

                    ('inet:whois:reg', ('str', {'lower': True}), {
                        'doc': 'A domain registrant.',
                        'ex': 'woot hostmaster'
                    }),

                    ('inet:wifi:ap', ('comp', {'fields': (('ssid', 'inet:wifi:ssid'), ('bssid', 'inet:mac'))}), {
                        'doc': 'An SSID/MAC address combination for a wireless access point.'
                    }),

                    ('inet:wifi:ssid', ('str', {}), {
                        'doc': 'A WiFi service set identifier (SSID) name.',
                        'ex': 'The Vertex Project'
                    }),

                ),

                # NOTE: tcp4/udp4/tcp6/udp6 are going away
                # becomes inet:server/inet:client, which are both inet:addr
                'forms': (

                    ('inet:asn', {}, (
                        ('name', ('str', {'lower': True}), {
                            'defval': '??',
                            'doc': 'The name of the organization currently responsible for the ASN.'
                        }),
                        ('owner', ('ou:org', {}), {
                            'doc': 'The guid of the organization currently responsible for the ASN.'
                        }),
                    )),

                    ('inet:asnet4', {}, (
                        ('asn', ('inet:asn', {}), {
                            'ro': 1,
                            'doc': 'The Autonomous System Number (ASN) of the netblock.'
                        }),
                        ('net4', ('inet:net4', {}), {
                            'ro': 1,
                            'doc': 'The IPv4 address range assigned to the ASN.'
                        }),
                        ('net4:min', ('inet:ipv4', {}), {
                            'ro': 1,
                            'doc': 'The first IPv4 in the range assigned to the ASN.'
                        }),
                        ('net4:max', ('inet:ipv4', {}), {
                            'ro': 1,
                            'doc': 'The last IPv4 in the range assigned to the ASN.'
                        }),
                    )),

                    ('inet:cidr4', {}, (
                        ('broadcast', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The broadcast IP address from the CIDR notation.'
                        }),

                        ('mask', ('int', {}), {
                            'ro': True,
                            'doc': 'The mask from the CIDR notation.'
                        }),

                        ('network', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The network IP address from the CIDR notation.'
                        }),
                    )),

                    ('inet:client', {}, (
                        ('proto', ('str', {'lower': True}), {
                            'ro': 1,
                            'doc': 'The network protocol of the client.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'ro': 1,
                            'doc': 'The IPv4 of the client.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'ro': 1,
                            'doc': 'The IPv6 of the client.'
                        }),
                        # FIXME port it:host
                        #('host', ('it:host', {}), {
                        #    'ro': 1,
                        #    'doc': 'The it:host node for the client.'
                        #}),
                        ('port', ('inet:port', {}), {
                            'doc': 'The client tcp/udp port.'
                        }),
                    )),

                    ('inet:download', {}, (
                        ('time', ('time', {}), {
                            'doc': 'The time the file was downloaded.'
                        }),
                        ('fqdn', ('inet:fqdn', {}), {
                            'doc': 'The FQDN used to resolve the server.'
                        }),
                        ('file', ('file:bytes', {}), {
                            'doc': 'The file that was downloaded.'
                        }),

                        ('server', ('inet:server', {}), {
                            'doc': 'The inet:addr of the server.'
                        }),
                        #('server:host', ('it:host', {}), {
                        #    'doc': 'The it:host node for the server.'
                        #}),
                        ('server:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 of the server.'
                        }),
                        ('server:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The IPv6 of the server.'
                        }),
                        ('server:port', ('inet:port', {}), {
                            'doc': 'The server tcp/udp port.'
                        }),
                        ('server:proto', ('str', {'lower': True}), {
                            'doc': 'The server network layer protocol.'
                        }),

                        ('client', ('inet:client', {}), {
                            'doc': 'The inet:addr of the client.'
                        }),
                        #('client:host', ('it:host', {}), {
                        #    'doc': 'The it:host node for the client.'
                        #}),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 of the client.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The IPv6 of the client.'
                        }),
                        ('client:port', ('inet:port', {}), {
                            'doc': 'The client tcp/udp port.'
                        }),
                        ('client:proto', ('str', {'lower': True}), {
                            'doc': 'The client network layer protocol.'
                        }),
                    )),

                    ('inet:email', {}, (

                        ('user', ('inet:user', {}), {
                            'ro': True,
                            'doc': 'The username of the email address.'}),

                        ('fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The domain of the email address.'}),
                    )),

                    ('inet:flow', {}, (
                        ('time', ('time', {}), {
                            'doc': 'The time the network connection was initiated.'
                        }),
                        ('duration', ('int', {}), {
                            'doc': 'The duration of the flow in seconds.'
                        }),
                        ('from', ('guid', {}), {
                            'doc': 'The ingest source file/iden. Used for reparsing.'
                        }),

                        # FIXME port src/dst
                        #('dst:host', {'ptype': 'it:host',
                        #    'doc': 'The guid of the destination host.'}),
                        #('dst:proc', {'ptype': 'it:exec:proc',
                        #    'doc': 'The guid of the destination process.'}),
                        #('dst:exe', {'ptype': 'file:bytes',
                        #    'doc': 'The file (executable) that received the connection.'}),
                        #('dst:txbytes', {'ptype': 'int',
                        #    'doc': 'The number of bytes sent by the destination host / process / file.'}),
                        #('src:host', {'ptype': 'it:host',
                        #    'doc': 'The guid of the source host.'}),
                        #('src:proc', {'ptype': 'it:exec:proc',
                        #    'doc': 'The guid of the source process.'}),
                        #('src:exe', {'ptype': 'file:bytes',
                        #    'doc': 'The file (executable) that created the connection.'}),
                        #('src:txbytes', {'ptype': 'int',
                        #    'doc': 'The number of bytes sent by the source host / process / file.'}),

                        ('server', ('inet:server', {}), {
                            'doc': 'The destination address / port for a connection.'
                        }),
                        ('server:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The destination IPv4 address.'
                        }),
                        ('server:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The destination IPv6 address.'
                        }),
                        ('server:port', ('inet:port', {}), {
                            'doc': 'The destination port.'
                        }),
                        ('server:proto', ('str', {'lower': True}), {
                            'doc': 'The destination port.'
                        }),

                        ('client', ('inet:client', {}), {
                            'doc': 'The source address / port for a connection.'
                        }),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address.'
                        }),
                        ('client:port', ('inet:port', {}), {
                            'doc': 'The source port.'
                        }),
                        ('client:proto', ('str', {'lower': True}), {
                            'doc': 'The source port.'
                        }),
                    )),

                    ('inet:fqdn', {}, (

                        ('created', ('time', {'ismin': True}), {
                            'doc': 'The earliest known registration (creation) date for the fqdn.'
                        }),

                        ('domain', ('inet:fqdn', {}), {
                            'doc': 'The parent domain for the FQDN.',
                        }),

                        ('expires', ('time', {'ismax': True}), {
                            'doc': 'The current expiration date for the fqdn.'
                        }),

                        ('host', ('str', {'lower': True}), {
                            'doc': 'The host part of the FQDN.',
                        }),

                        ('issuffix', ('bool', {}), {
                            'doc': 'True if the FQDN is considered a suffix.',
                            'defval': 0,
                        }),

                        ('iszone', ('bool', {}), {
                            'doc': 'True if the FQDN is considered a zone.',
                            'defval': 0,
                        }),

                        ('updated', ('time', {'ismax': True}), {
                            'doc': 'The last known updated date for the fqdn.'
                        }),

                        ('zone', ('inet:fqdn', {}), {
                            'doc': 'The zone level parent for this FQDN.',
                        }),

                    )),

                    ('inet:group', {}, ()),

                    ('inet:http:request', {}, (
                        ('flow', ('inet:flow', {}), {
                            'doc': 'The inet:flow which contained the HTTP request.'
                        }),
                        #('host', ('it:host', {}), {  # FIXME
                        #    'doc': 'The it:host which sent the HTTP request.'
                        #}),
                        ('time', ('time', {}), {
                            'doc': 'The time that the HTTP request was sent.'
                        }),
                        ('method', ('str', {}), {
                            'doc': 'The HTTP request method string.'
                        }),
                        ('path', ('str', {}), {
                            'doc': 'The requested HTTP path (without query parameters).'
                        }),
                        ('query', ('str', {}), {
                            'doc': 'The HTTP query string which optionally folows the path.'
                        }),
                        ('body', ('file:bytes', {}), {
                            'doc': 'The body of the HTTP request.'
                        }),
                    )),

                    ('inet:iface', {}, (
                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The last known latitude/longitude for the node'
                        }),
                        #('host', ('it:host', {}), {
                        #    'doc': 'The guid of the host the interface is associated with.'
                        #}),
                        ('type', ('str', {'lower': True}), {
                            'doc': 'The free-form interface type.'
                        }),
                        ('mac', ('inet:mac', {}), {
                            'doc': 'The ethernet (MAC) address of the interface.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 address of the interface.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'doc': 'The IPv6 address of the interface.'
                        }),
                        ('phone', ('tel:phone', {}), {
                            'doc': 'The telephone number of the interface.'
                        }),
                        ('wifi:ssid', ('inet:wifi:ssid', {}), {
                            'doc': 'The wifi SSID of the interface.'
                        }),
                        ('wifi:bssid', ('inet:mac', {}), {
                            'doc': 'The wifi BSSID of the interface.'
                        }),
                        ('mob:imei', ('tel:mob:imei', {}), {
                            'doc': 'The IMEI of the interface.'
                        }),
                        ('mob:imsi', ('tel:mob:imsi', {}), {
                            'doc': 'The IMSI of the interface.'
                        }),
                    )),

                    ('inet:ipv4', {}, (

                        ('asn', ('inet:asn', {}), {
                            'defval': 0,  # FIXME replace with nullval
                            'doc': 'The ASN to which the IPv4 address is currently assigned.'
                        }),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The best known latitude/longitude for the node'
                        }),

                        ('loc', ('loc', {}), {
                            'defval': '??',
                            'doc': 'The geo-political location string for the IPv4.'
                        }),

                        ('type', ('str', {}), {
                            'defval': '??',
                            'doc': 'The type of IP address (e.g., private, multicast, etc.).'
                        })

                    )),

                    ('inet:ipv6', {}, (

                        ('asn', ('inet:asn', {}), {
                            'defval': 0,  # FIXME replace with nullval
                            'doc': 'The ASN to which the IPv6 address is currently assigned.'
                        }),

                        ('ipv4', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The mapped ipv4.'
                        }),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The last known latitude/longitude for the node'
                        }),

                        ('loc', ('loc', {}), {
                            'defval': '??',
                            'doc': 'The geo-political location string for the IPv6.'
                        }),

                    )),

                    ('inet:mac', {}, [
                        ('vendor', ('str', {}), {
                            'defval': '??',
                            'doc': 'The vendor associated with the 24-bit prefix of a MAC address.'
                        }),
                    ]),

                    # FIXME implement
                    #('inet:passwd', {'ptype': 'inet:passwd'}, [
                    #    ('md5', {'ptype': 'hash:md5', 'ro': 1,
                    #        'doc': 'The computed MD5 hash of the password.'}),
                    #    ('sha1', {'ptype': 'hash:sha1', 'ro': 1,
                    #        'doc': 'The computed SHA1 hash of the password.'}),
                    #    ('sha256', {'ptype': 'hash:sha256', 'ro': 1,
                    #        'doc': 'The computed SHA256 hash of the password.'}),
                    #]),

                    ('inet:rfc2822:addr', {}, (
                        ('name', ('ps:name', {}), {
                            'ro': True,
                            'doc': 'The name field parsed from an RFC 2822 address string.'
                        }),
                        ('email', ('inet:email', {}), {
                            'ro': True,
                            'doc': 'The email field parsed from an RFC 2822 address string.'
                        }),
                    )),

                    ('inet:server', {}, (
                        ('proto', ('str', {'lower': True}), {
                            'ro': 1,
                            'doc': 'The network protocol of the server.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'ro': 1,
                            'doc': 'The IPv4 of the server.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'ro': 1,
                            'doc': 'The IPv6 of the server.'
                        }),
                        # FIXME port it:host
                        #('host', ('it:host', {}), {
                        #    'ro': 1,
                        #    'doc': 'The it:host node for the server.'
                        #}),
                        ('port', ('inet:port', {}), {
                            'doc': 'The server tcp/udp port.'
                        }),
                    )),

                    ('inet:url', {}, (
                        ('fqdn', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The fqdn used in the URL (e.g., http://www.woot.com/page.html).'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'ro': 1,
                            'doc': 'The IPv4 address used in the URL (e.g., http://1.2.3.4/page.html).'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'ro': 1,
                            'doc': 'The IPv6 address used in the URL.'
                        }),
                        ('passwd', ('inet:passwd', {}), {
                            'ro': 1,
                            'doc': 'The optional password used to access the URL.'
                        }),
                        ('path', ('str', {}), {
                            'ro': 1,
                            'doc': 'The path in the URL.'
                        }),
                        ('port', ('inet:port', {}), {
                            'ro': 1,
                            'doc': 'The port of the URL. URLs prefixed with http will be set to port 80 and '
                                   'URLs prefixed with https will be set to port 443 unless otherwise specified.'
                        }),
                        ('proto', ('str', {'lower': True}), {
                            'ro': 1,
                            'doc': 'The protocol in the URL.'
                        }),
                        ('user', ('inet:user', {}), {
                            'ro': 1,
                            'doc': 'The optional username used to access the URL.'
                        }),
                    )),

                    ('inet:urlfile', {}, (
                        ('url', ('inet:url', {}), {
                            'ro': 1,
                            'doc': 'The URL where the file was hosted.'
                        }),
                        ('file', ('file:bytes', {}), {
                            'ro': 1,
                            'doc': 'The file that was hosted at the URL.'
                        }),
                    )),

                    ('inet:urlredir', {}, (
                        ('src', ('inet:url', {}), {
                            'ro': 1,
                            'doc': 'The original/source URL before redirect'
                        }),
                        ('src:fqdn', ('inet:fqdn', {}), {
                            'doc': 'The FQDN within the src URL (if present)'
                        }),
                        ('dst', ('inet:url', {}), {
                            'ro': 1,
                            'doc': 'The redirected/destination URL'
                        }),
                        ('dst:fqdn', ('inet:fqdn', {}), {
                            'doc': 'The FQDN within the dst URL (if present)'
                        }),
                    )),

                    ('inet:user', {}, ()),

                    ('inet:web:acct', {}, (

                        ('avatar', ('file:bytes', {}), {
                            'doc': 'The file representing the avatar (e.g., profile picture) for the account.'
                        }),

                        ('dob', ('time', {}), {
                            'doc': 'A self-declared date of birth for the account (if the account belongs to a person).'
                        }),

                        ('email', ('inet:email', {}), {
                            'doc': 'The email address associated with the account.'
                        }),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The last known latitude/longitude for the node'
                        }),

                        ('loc', ('loc', {}), {
                            'doc': 'A self-declared location for the account.'
                        }),

                        ('name', ('inet:user', {}), {
                            'doc': 'The localized name associated with the account (may be different from the '
                                   'account identifier, e.g., a display name).'
                        }),

                        ('name:en', ('inet:user', {}), {
                            'doc': 'The English version of the name associated with the (may be different from '
                                   'the account identifier, e.g., a display name).'
                        }),

                        ('occupation', ('str', {'lower': True}), {
                            'doc': 'A self-declared occupation for the account.'
                        }),

                        ('passwd', ('inet:passwd', {}), {
                            'doc': 'The current password for the account.'
                        }),

                        ('phone', ('tel:phone', {}), {
                            'doc': 'The phone number associated with the account.'
                        }),

                        ('realname', ('ps:name', {}), {
                            'doc': 'The localized version of the real name of the account owner / registrant.'
                        }),

                        ('realname:en', ('ps:name', {}), {
                            'doc': 'The English version of the real name of the account owner / registrant.'
                        }),

                        ('seen:max', ('time', {'max': True}), {
                            'doc': 'The most recent known date of activity for the account.'
                        }),

                        ('seen:min', ('time', {'min': True}), {
                            'doc': 'The earliest known date of activity for the account.'
                        }),

                        ('signup', ('time', {}), {
                            'doc': 'The date and time the account was registered.'
                        }),

                        ('signup:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 address used to sign up for the account.'
                        }),

                        ('site', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The site or service associated with the account.'
                        }),

                        # NOTE was str:txt
                        ('tagline', ('str', {}), {
                            'doc': 'The text of the account status or tag line.'
                        }),

                        ('url', ('inet:url', {}), {
                            'doc': 'The service provider URL where the account is hosted.'
                        }),

                        ('user', ('inet:user', {}), {
                            'ro': 1,
                            'doc': 'The unique identifier for the account (may be different from the common '
                                   'name or display name).'
                        }),

                        ('webpage', ('inet:url', {}), {
                            'doc': 'A related URL specified by the account (e.g., a personal or company web '
                                   'page, blog, etc.).'
                        }),

                    )),

                    ('inet:web:action', {}, (
                        ('act', ('str', {'lower': True, 'strip': True}), {
                            'doc': 'The action performed by the account.'
                        }),
                        ('acct', ('inet:web:acct', {}), {
                            'ro': 1,
                            'doc': 'The web account associated with the action.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'ro': 1,
                            'doc': 'The unique identifier for the account.'
                        }),
                        # FIXME missing json
                        #('info', ('json', {}), {
                        #    'doc': 'Any other data associated with the action.'
                        #}),
                        ('time', ('time', {}), {
                            'doc': 'The date and time the account performed the action.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address of the action.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address of the action.'
                        }),
                    )),

                    ('inet:web:file', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'ro': 1,
                            'doc': 'The account that owns or is associated with the file.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'ro': 1,
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('file', ('file:bytes', {}), {
                            'ro': 1,
                            'doc': 'The file owned by or associated with the account.'
                        }),
                        # FIXME missing file:base
                        #('name', ('file:base', {}), {
                        #    'doc': 'The name of the file owned by or associated with the account.'
                        #}),
                        ('posted', ('time', {}), {
                            'doc': 'The date and time the file was posted / submitted.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address used to post or submit the file.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address used to post or submit the file.'
                        }),
                    )),

                    ('inet:web:follows', {}, (
                        ('follower', ('inet:web:acct', {}), {
                            'ro': 1,
                            'doc': 'The account following an account.'
                        }),
                        ('followee', ('inet:web:acct', {}), {
                            'ro': 1,
                            'doc': 'The account followed by an account.'
                        }),
                    )),

                    ('inet:web:group', {}, (
                        ('site', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The site or service associated with the group.'
                        }),
                        ('id', ('inet:group', {}), {
                            'ro': 1,
                            'doc': 'The site-specific unique identifier for the group (may be different from '
                                   'the common name or display name).'
                        }),
                        ('name', ('inet:group', {}), {
                            'doc': 'The localized name associated with the group (may be different from '
                                   'the account identifier, e.g., a display name).'
                        }),
                        ('name:en', ('inet:group', {}), {
                            'doc': 'The English version of the name associated with the group (may be different '
                                   'from the localized name).'
                        }),
                        ('url', ('inet:url', {}), {
                            'doc': 'The service provider URL where the group is hosted.'
                        }),
                        ('avatar', ('file:bytes', {}), {
                            'doc': 'The file representing the avatar (e.g., profile picture) for the group.'
                        }),
                        ('desc', ('str', {}), {  # NOTE was str:txt
                            'doc': 'The text of the description of the group.'
                        }),
                        ('webpage', ('inet:url', {}), {
                            'doc': 'A related URL specified by the group (e.g., primary web site, etc.).'
                        }),
                        ('loc', ('str', {'lower': True}), {
                            'doc': 'A self-declared location for the group.'
                        }),
                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The last known latitude/longitude for the node'
                        }),
                        ('signup', ('time', {}), {
                            'doc': 'The date and time the group was created on the site.'
                        }),
                        ('signup:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 address used to create the group.'
                        }),
                        ('signup:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The IPv6 address used to create the group.'
                        }),
                    )),

                    ('inet:web:logon', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'ro': 1,
                            'doc': 'The web account associated with the logon event.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'ro': 1,
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('time', ('time', {}), {
                            'doc': 'The date and time the account logged into the service.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address of the logon.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address of the logon.'
                        }),
                        ('logout', ('time', {}), {
                            'doc': 'The date and time the account logged out of the service.'
                        })
                    )),

                    ('inet:web:post', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'ro': 1,
                            'doc': 'The web account that made the post.'
                        }),
                        ('text', ('str', {}), {  # NOTE was str:txt
                            'ro': 1,
                            'doc': 'The text of the post.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'ro': 1,
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('time', ('time', {}), {
                            'doc': 'The date and time that the post was made.'
                        }),
                        ('url', ('inet:url', {}), {
                            'doc': 'The URL where the post is published / visible.'
                        }),
                        ('file', ('file:bytes', {}), {
                            'doc': 'The file that was attached to the post.'
                        }),
                        ('replyto', ('inet:web:post', {}), {
                            'doc': 'The post that this post is in reply to.'
                        }),
                        ('repost', ('inet:web:post', {}), {
                            'doc': 'The original post that this is a repost of.'
                        }),
                    )),

                    ('inet:whois:rar', {}, ()),

                    ('inet:whois:rec', {}, (
                        ('fqdn', ('inet:fqdn', {}), {
                            'ro': 1,
                            'doc': 'The domain associated with the whois record.'
                        }),
                        ('asof', ('time', {}), {
                            'ro': 1,
                            'doc': 'The date of the whois record.'
                        }),
                        ('text', ('str', {'lower': True}), {
                            'doc': 'The full text of the whois record.'
                        }),
                        ('created', ('time', {}), {
                            'doc': 'The "created" time from the whois record.'
                        }),
                        ('updated', ('time', {}), {
                            'doc': 'The "last updated" time from the whois record.'
                        }),
                        ('expires', ('time', {}), {
                            'doc': 'The "expires" time from the whois record.'
                        }),
                        ('registrar', ('inet:whois:rar', {}), {
                            'defval': '??',
                            'doc': 'The registrar name from the whois record.'
                        }),
                        ('registrant', ('inet:whois:reg', {}), {
                            'defval': '??',
                            'doc': 'The registrant name from the whois record.'
                        }),
                    )),

                    ('inet:whois:reg', {}, ()),

                    ('inet:wifi:ap', {}, (
                        ('ssid', ('inet:wifi:ssid', {}), {
                            'doc': 'The SSID for the wireless access point.'
                        }),
                        ('bssid', ('inet:mac', {}), {
                            'doc': 'The MAC address for the wireless access point.'
                        }),
                    )),

                    ('inet:wifi:ssid', {}, []),

                ),
            }),
        )
