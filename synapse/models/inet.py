import socket
import asyncio
import logging
import urllib.parse

import idna
import regex
import collections
import unicodedata

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.chop as s_chop
import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
import synapse.lib.scrape as s_scrape
import synapse.lookup.iana as s_l_iana

import synapse.vendor.cpython.lib.email.utils as s_v_email_utils

logger = logging.getLogger(__name__)

ipaddress = s_common.ipaddress

drivre = regex.compile(r'^\w[:|]')
fqdnre = regex.compile(r'^[\w._-]+$', regex.U)
srv6re = regex.compile(r'^\[([a-f0-9\.:]+)\](?::(\d+))?$', regex.IGNORECASE)

udots = regex.compile(r'[\u3002\uff0e\uff61]')

cidrmasks = [((0xffffffff - (2 ** (32 - i) - 1)), (2 ** (32 - i))) for i in range(33)]
ipv4max = 2 ** 32 - 1

rfc6598 = ipaddress.IPv4Network('100.64.0.0/10')

urlfangs = regex.compile('^(hxxp|hxxps)$')

# defined from https://x.com/4A4133/status/1887269972545839559
ja4_regex = r'^([tqd])([sd\d]\d)([di])(\d{2})(\d{2})([a-zA-Z0-9]{2})_([0-9a-f]{12})_([0-9a-f]{12})$'
ja4s_regex = r'^([tq])([sd\d]\d)(\d{2})([a-zA-Z0-9]{2})_([0-9a-f]{4})_([0-9a-f]{12})$'

def getAddrType(ip):

    if ip.is_multicast:
        return 'multicast'

    if ip.is_loopback:
        return 'loopback'

    if ip.is_link_local:
        return 'linklocal'

    if ip.is_private:
        return 'private'

    if ip.is_reserved:
        return 'reserved'

    if ip in rfc6598:
        return 'shared'

    return 'unicast'

# https://en.wikipedia.org/wiki/IPv6_address#Address_scopes
ipv6_multicast_scopes = {
    'ff00:': 'reserved',
    'ff01:': 'interface-local',
    'ff02:': 'link-local',
    'ff03:': 'realm-local',
    'ff04:': 'admin-local',
    'ff05:': 'site-local',
    'ff08:': 'organization-local',
    'ff0e:': 'global',
    'ff0f:': 'reserved',
}

scopes_enum = 'reserved,interface-local,link-local,realm-local,admin-local,site-local,organization-local,global,unassigned'

svcobjstatus = (
    (10, 'draft'),
    (30, 'available'),
    (40, 'offline'),
    (50, 'removed'),
)

svcaccesstypes = (
    (10, 'create'),
    (30, 'read'),
    (40, 'update'),
    (50, 'delete'),
    (60, 'list'),
    (70, 'execute'),
)

def getAddrScope(ipv6):

    if ipv6.is_loopback:
        return 'link-local'

    if ipv6.is_link_local:
        return 'link-local'

    if ipv6.is_multicast:
        pref = ipv6.compressed[:5]
        return ipv6_multicast_scopes.get(pref, 'unassigned')

    return 'global'

class IPAddr(s_types.Type):

    stortype = s_layer.STOR_TYPE_IPADDR

    _opt_defs = (
        ('version', None),   # type: ignore
    )

    def postTypeInit(self):

        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)
        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.storlifts.update({
            '=': self._storLiftEq,
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
        })

        self.reqvers = self.opts.get('version')

        self.typetype = self.modl.type('str')
        self.verstype = self.modl.type('int').clone({'enums': ((4, '4'), (6, '6'))})
        self.scopetype = self.typetype.clone({'enums': scopes_enum})

    async def _ctorCmprEq(self, valu):

        if isinstance(valu, str):

            if valu.find('/') != -1:
                minv, maxv = await self.getCidrRange(valu)

                async def cmpr(norm):
                    return norm >= minv and norm <= maxv
                return cmpr

            if valu.find('-') != -1:
                minv, maxv = await self.getNetRange(valu)

                async def cmpr(norm):
                    return norm >= minv and norm <= maxv
                return cmpr

        return await s_types.Type._ctorCmprEq(self, valu)

    async def getTypeVals(self, valu):

        if isinstance(valu, str):

            if valu.find('/') != -1:

                minv, maxv = await self.getCidrRange(valu)
                while minv <= maxv:
                    yield minv
                    minv = (minv[0], minv[1] + 1)

                return

            if valu.find('-') != -1:

                minv, maxv = await self.getNetRange(valu)
                while minv <= maxv:
                    yield minv
                    minv = (minv[0], minv[1] + 1)

                return

        yield valu

    async def _normPyTuple(self, valu, view=None):

        if any((len(valu) != 2,
                type(valu[0]) is not int,
                type(valu[1]) is not int)):

            mesg = f'Invalid IP address tuple: {valu}'
            raise s_exc.BadTypeValu(mesg=mesg)

        vers = valu[0]

        if self.reqvers is not None and vers != self.reqvers:
            mesg = f'Invalid IP address version: got {vers} expected {self.reqvers}'
            raise s_exc.BadTypeValu(mesg=mesg)

        subs = {'version': (self.verstype.typehash, vers, {})}

        if vers == 4:
            try:
                ipaddr = ipaddress.IPv4Address(valu[1])
            except ValueError as e:
                mesg = f'Invalid IP address tuple: {valu}'
                raise s_exc.BadTypeValu(mesg=mesg)

        elif vers == 6:
            try:
                ipaddr = ipaddress.IPv6Address(valu[1])
                subs['scope'] = (self.scopetype.typehash, getAddrScope(ipaddr), {})
            except ValueError as e:
                mesg = f'Invalid IP address tuple: {valu}'
                raise s_exc.BadTypeValu(mesg=mesg)

        else:
            mesg = f'Invalid IP address tuple: {valu}'
            raise s_exc.BadTypeValu(mesg=mesg)

        subs['type'] = (self.typetype.typehash, getAddrType(ipaddr), {})

        return valu, {'subs': subs}

    async def _normPyStr(self, text, view=None):

        valu = text.replace('[.]', '.')
        valu = valu.replace('(.)', '.')

        valu = s_chop.printables(valu)

        subs = {}

        if valu.find(':') != -1:
            if self.reqvers is not None and self.reqvers != 6:
                mesg = f'Invalid IP address version, expected an IPv4, got: {text}'
                raise s_exc.BadTypeValu(mesg=mesg)

            try:
                byts = socket.inet_pton(socket.AF_INET6, valu)
                addr = (6, int.from_bytes(byts, 'big'))
                ipaddr = ipaddress.IPv6Address(addr[1])
                subs |= {'version': (self.verstype.typehash, 6, {}),
                         'scope': (self.scopetype.typehash, getAddrScope(ipaddr), {})}
                # v4 = v6.ipv4_mapped
            except OSError as e:
                mesg = f'Invalid IP address: {text}'
                raise s_exc.BadTypeValu(mesg=mesg) from None
        else:
            if self.reqvers is not None and self.reqvers != 4:
                mesg = f'Invalid IP address version, expected an IPv6, got: {text}'
                raise s_exc.BadTypeValu(mesg=mesg)

            try:
                byts = socket.inet_pton(socket.AF_INET, valu)
            except OSError:
                try:
                    byts = socket.inet_aton(valu)
                except OSError as e:
                    mesg = f'Invalid IP address: {text}'
                    raise s_exc.BadTypeValu(mesg=mesg) from None

            addr = (4, int.from_bytes(byts, 'big'))
            ipaddr = ipaddress.IPv4Address(addr[1])
            subs['version'] = (self.verstype.typehash, 4, {})

        subs['type'] = (self.typetype.typehash, getAddrType(ipaddr), {})

        return addr, {'subs': subs}

    def repr(self, norm):

        vers, addr = norm

        if vers == 4:
            byts = addr.to_bytes(4, 'big')
            return socket.inet_ntop(socket.AF_INET, byts)

        if vers == 6:
            byts = addr.to_bytes(16, 'big')
            return socket.inet_ntop(socket.AF_INET6, byts)

        mesg = 'IP proto version {vers} is not supported!'
        raise s_exc.BadTypeValu(mesg=mesg)

    async def getNetRange(self, text):
        minstr, maxstr = text.split('-', 1)
        minv, info = await self.norm(minstr)
        maxv, info = await self.norm(maxstr)

        if minv[0] != maxv[0]:
            raise s_exc.BadTypeValu(valu=text, name=self.name,
                                    mesg=f'IP address version mismatch in range "{text}"')

        return minv, maxv

    async def getCidrRange(self, text):
        addr, mask_str = text.split('/', 1)
        (vers, addr), info = await self.norm(addr)

        if vers == 4:
            try:
                mask_int = int(mask_str)
            except ValueError:
                raise s_exc.BadTypeValu(valu=text, name=self.name,
                                        mesg=f'Invalid CIDR Mask "{text}"')

            if mask_int > 32 or mask_int < 0:
                raise s_exc.BadTypeValu(valu=text, name=self.name,
                                        mesg=f'Invalid CIDR Mask "{text}"')

            mask = cidrmasks[mask_int]

            minv = addr & mask[0]
            return (vers, minv), (vers, minv + mask[1] - 1)

        else:
            try:
                netw = ipaddress.IPv6Network(text, strict=False)
            except Exception as e:
                raise s_exc.BadTypeValu(valu=text, name=self.name, mesg=str(e)) from None

            minv = int(netw[0])
            maxv = int(netw[-1])
            return (6, minv), (6, maxv)

    async def _storLiftEq(self, cmpr, valu):

        if isinstance(valu, str):

            if valu.find('/') != -1:
                minv, maxv = await self.getCidrRange(valu)
                maxv = (maxv[0], maxv[1])
                return (
                    ('range=', (minv, maxv), self.stortype),
                )

            if valu.find('-') != -1:
                minv, maxv = await self.getNetRange(valu)
                return (
                    ('range=', (minv, maxv), self.stortype),
                )

        return await self._storLiftNorm(cmpr, valu)

    async def _ctorCmprGe(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu >= norm
        return cmpr

    async def _ctorCmprLe(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu <= norm
        return cmpr

    async def _ctorCmprGt(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu > norm
        return cmpr

    async def _ctorCmprLt(self, text):
        norm, info = await self.norm(text)

        async def cmpr(valu):
            return valu < norm
        return cmpr

class SockAddr(s_types.Str):

    _opt_defs = (
        ('defport', None),     # type: ignore
        ('defproto', 'tcp'),   # type: ignore
    ) + s_types.Str._opt_defs

    protos = ('tcp', 'udp', 'icmp', 'gre')
    noports = ('gre', 'icmp')

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.iptype = self.modl.type('inet:ip')
        self.porttype = self.modl.type('inet:port')
        self.prototype = self.modl.type('str').clone({'lower': True})

        self.defport = self.opts.get('defport')
        self.defproto = self.opts.get('defproto')

        self.virtindx |= {
            'ip': 'ip',
            'port': 'port',
        }

        self.virts |= {
            'ip': (self.iptype, self._getIP),
            'port': (self.porttype, self._getPort),
        }

    def _getIP(self, valu):
        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('ip')) is None:
            return None

        return valu[0]

    def _getPort(self, valu):
        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('port')) is None:
            return None

        return valu[0]

    async def _normPort(self, valu):
        parts = valu.split(':', 1)
        if len(parts) == 2:
            valu, port = parts
            port = (await self.porttype.norm(port))[0]
            return valu, port, f':{port}'

        if self.defport:
            return valu, self.defport, f':{self.defport}'

        return valu, None, ''

    async def _normPyStr(self, valu, view=None):
        orig = valu
        subs = {}
        virts = {}

        # no protos use case sensitivity yet...
        valu = valu.lower()

        proto = self.defproto
        parts = valu.split('://', 1)
        if len(parts) == 2:
            proto, valu = parts

        if proto not in self.protos:
            protostr = ','.join(self.protos)
            mesg = f'inet:sockaddr protocol must be one of: {protostr}'
            raise s_exc.BadTypeValu(mesg=mesg, valu=orig, name=self.name)

        subs['proto'] = (self.prototype.typehash, proto, {})

        valu = valu.strip().strip('/')

        # Treat as IPv6 if starts with [ or contains multiple :
        if valu.startswith('['):
            match = srv6re.match(valu)
            if match:
                ipv6, port = match.groups()

                ipv6, norminfo = await self.iptype.norm(ipv6)
                host = self.iptype.repr(ipv6)
                subs['ip'] = (self.iptype.typehash, ipv6, norminfo)
                virts['ip'] = (ipv6, self.iptype.stortype)

                portstr = ''
                if port is not None:
                    port, norminfo = await self.porttype.norm(port)
                    subs['port'] = (self.porttype.typehash, port, norminfo)
                    virts['port'] = (port, self.porttype.stortype)
                    portstr = f':{port}'

                elif self.defport:
                    subs['port'] = (self.porttype.typehash, self.defport, {})
                    virts['port'] = (self.defport, self.porttype.stortype)
                    portstr = f':{self.defport}'

                if port and proto in self.noports:
                    mesg = f'Protocol {proto} does not allow specifying ports.'
                    raise s_exc.BadTypeValu(mesg=mesg, valu=orig)

                return f'{proto}://[{host}]{portstr}', {'subs': subs, 'virts': virts}

            mesg = f'Invalid IPv6 w/port ({orig})'
            raise s_exc.BadTypeValu(valu=orig, name=self.name, mesg=mesg)

        elif valu.count(':') >= 2:
            ipv6, norminfo = await self.iptype.norm(valu)
            host = self.iptype.repr(ipv6)
            subs['ip'] = (self.iptype.typehash, ipv6, norminfo)
            virts['ip'] = (ipv6, self.iptype.stortype)

            if self.defport:
                subs['port'] = (self.porttype.typehash, self.defport, {})
                virts['port'] = (self.defport, self.porttype.stortype)
                return f'{proto}://[{host}]:{self.defport}', {'subs': subs, 'virts': virts}

            return f'{proto}://{host}', {'subs': subs, 'virts': virts}

        # Otherwise treat as IPv4
        valu, port, pstr = await self._normPort(valu)
        if port:
            subs['port'] = (self.porttype.typehash, port, {})
            virts['port'] = (port, self.porttype.stortype)

        if port and proto in self.noports:
            mesg = f'Protocol {proto} does not allow specifying ports.'
            raise s_exc.BadTypeValu(mesg=mesg, valu=orig)

        ipv4, norminfo = await self.iptype.norm(valu)
        ipv4_repr = self.iptype.repr(ipv4)
        subs['ip'] = (self.iptype.typehash, ipv4, norminfo)
        virts['ip'] = (ipv4, self.iptype.stortype)

        return f'{proto}://{ipv4_repr}{pstr}', {'subs': subs, 'virts': virts}

    async def _normPyTuple(self, valu, view=None):
        ipaddr, norminfo = await self.iptype.norm(valu)

        ip_repr = self.iptype.repr(ipaddr)
        subs = {'ip': (self.iptype.typehash, ipaddr, norminfo)}
        virts = {'ip': (ipaddr, self.iptype.stortype)}
        proto = self.defproto

        if self.defport:
            subs['port'] = (self.porttype.typehash, self.defport, {})
            virts['port'] = (self.defport, self.porttype.stortype)
            if ipaddr[0] == 6:
                return f'{proto}://[{ip_repr}]:{self.defport}', {'subs': subs, 'virts': virts}
            else:
                return f'{proto}://{ip_repr}:{self.defport}', {'subs': subs, 'virts': virts}

        return f'{proto}://{ip_repr}', {'subs': subs, 'virts': virts}

class Email(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.fqdntype = self.modl.type('inet:fqdn')
        self.usertype = self.modl.type('inet:user')
        self.plustype = self.modl.type('str').clone({'lower': True})

    async def _normPyStr(self, valu, view=None):

        try:
            user, fqdn = valu.split('@', 1)
        except ValueError:
            mesg = f'Email address expected in <user>@<fqdn> format, got "{valu}"'
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=mesg) from None

        plus = None
        if len(parts := user.split('+', 1)) == 2:
            baseuser, plus = parts
            plus = plus.strip().lower()

        try:
            fqdnnorm, fqdninfo = await self.fqdntype.norm(fqdn)
            usernorm, userinfo = await self.usertype.norm(user)
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=str(e)) from None

        norm = f'{usernorm}@{fqdnnorm}'

        info = {
            'subs': {
                'fqdn': (self.fqdntype.typehash, fqdnnorm, fqdninfo),
                'user': (self.usertype.typehash, usernorm, userinfo),
            }
        }

        if plus is not None:
            info['subs']['plus'] = (self.plustype.typehash, plus, {})
            info['subs']['base'] = (self.typehash, f'{baseuser}@{fqdnnorm}', {
                'subs': {
                    'fqdn': (self.fqdntype.typehash, fqdnnorm, fqdninfo),
                    'user': (self.usertype.typehash, baseuser, {}),
                }
            })

        return norm, info

class Fqdn(s_types.Type):

    stortype = s_layer.STOR_TYPE_FQDN

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.storlifts.update({
            '=': self._storLiftEq,
        })

        self.hosttype = self.modl.type('str').clone({'lower': True})
        self.booltype = self.modl.type('bool')

    async def _storLiftEq(self, cmpr, valu):

        if isinstance(valu, str):

            if valu == '':
                mesg = 'Cannot generate fqdn index bytes for a empty string.'
                raise s_exc.BadLiftValu(valu=valu, name=self.name, mesg=mesg)

            if valu == '*':
                return (
                    ('=', '*', self.stortype),
                )

            if valu.startswith('*.'):
                norm, info = await self.norm(valu[2:])
                return (
                    ('=', f'*.{norm}', self.stortype),
                )

            if valu.startswith('*'):
                norm, info = await self.norm(valu[1:])
                return (
                    ('=', f'*{norm}', self.stortype),
                )

            if '*' in valu:
                mesg = 'Wild card may only appear at the beginning.'
                raise s_exc.BadLiftValu(valu=valu, name=self.name, mesg=mesg)

        return await self._storLiftNorm(cmpr, valu)

    async def _ctorCmprEq(self, text):
        if text == '':
            # Asking if a +inet:fqdn='' is a odd filter, but
            # the intuitive answer for that filter is to return False
            async def cmpr(valu):
                return False
            return cmpr

        if text[0] == '*':
            cval = text[1:]
            async def cmpr(valu):
                return valu.endswith(cval)
            return cmpr

        norm, info = await self.norm(text)

        async def cmpr(valu):
            return norm == valu
        return cmpr

    async def _normPyStr(self, valu, view=None):

        valu = unicodedata.normalize('NFKC', valu)

        valu = regex.sub(udots, '.', valu)
        valu = valu.replace('[.]', '.')
        valu = valu.replace('(.)', '.')

        # strip leading/trailing .
        valu = valu.strip().strip('.')

        try:
            valu = idna.encode(valu, uts46=True).decode('utf8')
        except idna.IDNAError:
            try:
                valu = valu.encode('idna').decode('utf8').lower()
            except UnicodeError:
                mesg = 'Failed to encode/decode the value with idna/utf8.'
                raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                        mesg=mesg) from None

        if not fqdnre.match(valu):
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=f'FQDN failed to match fqdnre [{fqdnre.pattern}]')

        # Make sure we *don't* get an IP address
        try:
            socket.inet_pton(socket.AF_INET, valu)
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='FQDN Got an IP address instead')
        except OSError:
            pass

        parts = valu.split('.', 1)
        subs = pinfo = {'host': (self.hosttype.typehash, parts[0], {})}

        while len(parts) == 2:
            nextfo = {}
            domain = parts[1]
            pinfo['domain'] = (self.typehash, domain, {'subs': nextfo})

            parts = domain.split('.', 1)
            nextfo['host'] = (self.hosttype.typehash, parts[0], {})

            pinfo = nextfo
            await asyncio.sleep(0)

        pinfo['issuffix'] = (self.booltype.typehash, 1, {})

        return valu, {'subs': subs}

    def repr(self, valu):
        try:
            return idna.decode(valu.encode('utf8'), uts46=True)
        except idna.IDNAError:
            try:
                return valu.encode('utf8').decode('idna')
            except UnicodeError:
                return valu

class HttpCookie(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.strtype = self.modl.type('str')

    async def _normPyStr(self, text, view=None):

        text = text.strip()
        parts = text.split('=', 1)

        name = parts[0].split(';', 1)[0].strip()
        if len(parts) == 1:
            return text, {'subs': {'name': (self.strtype.typehash, name, {})}}

        valu = parts[1].split(';', 1)[0].strip()
        return text, {'subs': {'name': (self.strtype.typehash, name, {}), 'value': (self.strtype.typehash, valu, {})}}

    async def getTypeVals(self, valu):

        if isinstance(valu, str):
            cookies = valu.split(';')
            for cookie in [c.strip() for c in cookies]:
                if not cookie:
                    continue

                yield cookie

            return

        if isinstance(valu, (list, tuple)):

            for cookie in valu:
                if not cookie:
                    continue

                yield cookie

            return

        yield valu

class IPRange(s_types.Range):

    def postTypeInit(self):
        self.opts['type'] = ('inet:ip', {})
        s_types.Range.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.masktype = self.modl.type('int').clone({'size': 1, 'signed': False})
        self.sizetype = self.modl.type('int').clone({'size': 16, 'signed': False})

        self.pivs |= {
            'inet:ip': ('range=', None),
        }

        self.virtindx |= {
            'mask': 'mask',
            'size': 'size',
        }

        self.virts |= {
            'mask': (self.masktype, self._getMask),
            'size': (self.sizetype, self._getSize),
        }

    def _getMask(self, valu):
        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('mask')) is None:
            return None

        return valu[0]

    def _getSize(self, valu):
        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('size')) is None:
            return None

        return valu[0]

    def repr(self, norm):
        if (cidr := self._getCidr(norm)) is not None:
            return str(cidr)

        minv, maxv = s_types.Range.repr(self, norm)
        return f'{minv}-{maxv}'

    def _getCidr(self, norm):
        (minv, maxv) = norm

        if minv[0] == 4:
            minv = ipaddress.IPv4Address(minv[1])
            maxv = ipaddress.IPv4Address(maxv[1])
        else:
            minv = ipaddress.IPv6Address(minv[1])
            maxv = ipaddress.IPv6Address(maxv[1])

        cidr = None
        for iprange in ipaddress.summarize_address_range(minv, maxv):
            if cidr is not None:
                return
            cidr = iprange

        return cidr

    async def _normPyStr(self, valu, view=None):

        if '-' in valu:
            norm, info = await super()._normPyStr(valu)
            size = (await self.sizetype.norm(norm[1][1] - norm[0][1] + 1))[0]
            info['virts'] = {'size': (size, self.sizetype.stortype)}

            if (cidr := self._getCidr(norm)) is not None:
                info['virts']['mask'] = (cidr.prefixlen, self.masktype.stortype)

            return norm, info

        try:
            ip_str, mask_str = valu.split('/', 1)
            mask_int = int(mask_str)
        except ValueError:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Invalid/Missing CIDR Mask')

        (vers, ip_int) = (await self.subtype.norm(ip_str))[0]

        if vers == 4:
            if mask_int > 32 or mask_int < 0:
                raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                        mesg='Invalid CIDR Mask')

            mask = cidrmasks[mask_int]
            network, netinfo = await self.subtype.norm((4, ip_int & mask[0]))
            broadcast, binfo = await self.subtype.norm((4, network[1] + mask[1] - 1))

        else:
            try:
                netw = ipaddress.IPv6Network(valu)
            except Exception as e:
                raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=str(e)) from None

            network, netinfo = await self.subtype.norm((6, int(netw.network_address)))
            broadcast, binfo = await self.subtype.norm((6, int(netw.broadcast_address)))

        size = (await self.sizetype.norm(broadcast[1] - network[1] + 1))[0]

        return (network, broadcast), {'subs': {'min': (self.subtype.typehash, network, netinfo),
                                               'max': (self.subtype.typehash, broadcast, binfo)},
                                      'virts': {'mask': (mask_int, self.masktype.stortype),
                                                'size': (size, self.sizetype.stortype)}}

    async def _normPyTuple(self, valu, view=None):
        if len(valu) != 2:
            raise s_exc.BadTypeValu(numitems=len(valu), name=self.name,
                                    mesg=f'Must be a 2-tuple of type {self.subtype.name}: {s_common.trimText(repr(valu))}')

        minv, minfo = await self.subtype.norm(valu[0])
        maxv, maxfo = await self.subtype.norm(valu[1])

        if minv[0] != maxv[0]:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=f'IP address version mismatch in range "{valu}"')

        if minv[1] > maxv[1]:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='minval cannot be greater than maxval')

        size = (await self.sizetype.norm(maxv[1] - minv[1] + 1))[0]

        info = {'subs': {'min': (self.subtype.typehash, minv, minfo),
                         'max': (self.subtype.typehash, maxv, maxfo)},
                'virts': {'size': (size, self.sizetype.stortype)}}

        if (cidr := self._getCidr((minv, maxv))) is not None:
            info['virts']['mask'] = (cidr.prefixlen, self.masktype.stortype)

        return (minv, maxv), info

class Rfc2822Addr(s_types.Str):
    '''
    An RFC 2822 compatible email address parser
    '''

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.metatype = self.modl.type('meta:name')
        self.emailtype = self.modl.type('inet:email')

    async def _normPyStr(self, valu, view=None):

        # remove quotes for normalized version
        valu = valu.replace('"', ' ').replace("'", ' ')
        valu = valu.strip().lower()
        valu = ' '.join(valu.split())

        try:
            name, addr = s_v_email_utils.parseaddr(valu, strict=True)
        except Exception as e:  # pragma: no cover
            # not sure we can ever really trigger this with a string as input
            mesg = f'email.utils.parsaddr failed: {str(e)}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=mesg) from None

        if not name and not addr:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=f'No name or email parsed from {valu}')

        subs = {}
        if name:
            subs['name'] = (self.metatype.typehash, name, {})

        try:
            mail, norminfo = await self.emailtype.norm(addr)

            subs['email'] = (self.emailtype.typehash, mail, norminfo)
            if name:
                valu = '%s <%s>' % (name, mail)
            else:
                valu = mail
        except s_exc.BadTypeValu as e:
            pass  # it's all good, we just dont have a valid email addr

        return valu, {'subs': subs}

class Url(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.iptype = self.modl.type('inet:ip')
        self.fqdntype = self.modl.type('inet:fqdn')
        self.porttype = self.modl.type('inet:port')
        self.passtype = self.modl.type('auth:passwd')
        self.strtype = self.modl.type('str')
        self.lowstrtype = self.modl.type('str').clone({'lower': True})

    async def _ctorCmprEq(self, text):
        if text == '':
            # Asking if a +inet:url='' is a odd filter, but
            # the intuitive answer for that filter is to return False
            async def cmpr(valu):
                return False
            return cmpr

        norm, info = await self.norm(text)

        async def cmpr(valu):
            return norm == valu

        return cmpr

    async def _normPyStr(self, valu, view=None):
        valu = valu.strip()
        orig = valu
        subs = {}
        proto = ''
        authparts = None
        hostparts = ''
        pathpart = ''
        parampart = ''
        local = False
        isUNC = False

        if valu.startswith('\\\\'):
            orig = s_chop.uncnorm(valu)
            # Fall through to original norm logic

        # Protocol
        for splitter in ('://///', ':////'):
            try:
                proto, valu = orig.split(splitter, 1)
                proto = proto.lower()
                assert proto == 'file'
                isUNC = True
                break
            except Exception:
                proto = valu = ''

        if not proto:
            try:
                proto, valu = orig.split('://', 1)
                proto = proto.lower()
            except Exception:
                pass

        if not proto:
            try:
                proto, valu = orig.split(':', 1)
                proto = proto.lower()
                assert proto == 'file'
                assert valu
                local = True
            except Exception:
                proto = valu = ''

        if not proto or not valu:
            raise s_exc.BadTypeValu(valu=orig, name=self.name,
                                    mesg='Invalid/Missing protocol') from None

        proto = urlfangs.sub(lambda match: 'http' + match.group(0)[4:], proto)

        subs['proto'] = (self.lowstrtype.typehash, proto, {})
        # Query params first
        queryrem = ''
        if '?' in valu:
            valu, queryrem = valu.split('?', 1)
            # TODO break out query params separately

        # Resource Path
        parts = valu.split('/', 1)
        subs['path'] = (self.strtype.typehash, '', {})
        if len(parts) == 2:
            valu, pathpart = parts
            if local:
                if drivre.match(valu):
                    pathpart = '/'.join((valu, pathpart))
                    valu = ''
            # Ordering here matters due to the differences between how windows and linux filepaths are encoded
            # *nix paths: file://<host>/some/chosen/path
            # for windows path: file://<host>/c:/some/chosen/path
            # the split above will rip out the starting slash on *nix, so we need it back before making the path
            # sub, but for windows we need to only when constructing the full url (and not the path sub)
            if proto == 'file' and drivre.match(pathpart):
                # make the path sub before adding in the slash separator so we don't end up with "/c:/foo/bar"
                # as part of the subs
                # per the rfc, only do this for things that start with a drive letter
                subs['path'] = (self.strtype.typehash, pathpart, {})
                pathpart = f'/{pathpart}'
            else:
                pathpart = f'/{pathpart}'
                subs['path'] = (self.strtype.typehash, pathpart, {})

        if queryrem:
            parampart = f'?{queryrem}'
        subs['params'] = (self.strtype.typehash, parampart, {})

        # Optional User/Password
        parts = valu.rsplit('@', 1)
        if len(parts) == 2:
            authparts, valu = parts
            userpass = authparts.split(':', 1)
            subs['user'] = (self.lowstrtype.typehash, urllib.parse.unquote(userpass[0].lower()), {})
            if len(userpass) == 2:
                passnorm, passinfo = await self.passtype.norm(urllib.parse.unquote(userpass[1]))
                subs['passwd'] = (self.passtype.typehash, passnorm, passinfo)

        # Host (FQDN, IPv4, or IPv6)
        host = None
        port = None

        # Treat as IPv6 if starts with [ or contains multiple :
        if valu.startswith('[') or valu.count(':') >= 2:
            try:
                match = srv6re.match(valu)
                if match:
                    valu, port = match.groups()

                ipv6, norminfo = await self.iptype.norm(valu)
                host = self.iptype.repr(ipv6)
                subs['ip'] = (self.iptype.typehash, ipv6, norminfo)

                if match:
                    host = f'[{host}]'

            except Exception:
                pass

        else:
            # FQDN and IPv4 handle ports the same way
            fqdnipv4_parts = valu.split(':', 1)
            part = fqdnipv4_parts[0]
            if len(fqdnipv4_parts) == 2:
                port = fqdnipv4_parts[1]

            # IPv4
            try:
                # Norm and repr to handle fangs
                ipv4, norminfo = await self.iptype.norm(part)
                host = self.iptype.repr(ipv4)
                subs['ip'] = (self.iptype.typehash, ipv4, norminfo)
            except Exception:
                pass

            # FQDN
            if host is None:
                try:
                    host, norminfo = await self.fqdntype.norm(part)
                    subs['fqdn'] = (self.fqdntype.typehash, host, norminfo)
                except Exception:
                    pass

            # allow MSFT specific wild card syntax
            # https://learn.microsoft.com/en-us/windows/win32/http/urlprefix-strings
            if host is None and part == '+':
                host = '+'

        if host and local:
            raise s_exc.BadTypeValu(valu=orig, name=self.name,
                                    mesg='Host specified on local-only file URI') from None

        # Optional Port
        if port is not None:
            port, norminfo = await self.porttype.norm(port)
            subs['port'] = (self.porttype.typehash, port, norminfo)
        else:
            # Look up default port for protocol, but don't add it back into the url
            defport = s_l_iana.services.get(proto)
            if defport:
                subs['port'] = (self.porttype.typehash, *(await self.porttype.norm(defport)))

        # Set up Normed URL
        if isUNC:
            hostparts += '//'

        if authparts:
            hostparts = f'{authparts}@'

        if host is not None:
            hostparts = f'{hostparts}{host}'
            if port is not None:
                hostparts = f'{hostparts}:{port}'

        if proto != 'file' and host is None:
            raise s_exc.BadTypeValu(valu=orig, name=self.name, mesg='Missing address/url')

        if not hostparts and not pathpart:
            raise s_exc.BadTypeValu(valu=orig, name=self.name,
                                    mesg='Missing address/url') from None

        base = f'{proto}://{hostparts}{pathpart}'
        subs['base'] = (self.strtype.typehash, base, {})
        norm = f'{base}{parampart}'
        return norm, {'subs': subs}

async def _onAddFqdn(node):

    fqdn = node.ndef[1]
    domain = node.get('domain')

    async with node.view.getEditor() as editor:
        protonode = editor.loadNode(node)
        if domain is None:
            await protonode.set('iszone', False)
            await protonode.set('issuffix', True)
            return

        if protonode.get('issuffix') is None:
            await protonode.set('issuffix', False)

        parent = await node.view.getNodeByNdef(('inet:fqdn', domain))
        if parent is None:
            parent = await editor.addNode('inet:fqdn', domain)

        if parent.get('issuffix'):
            await protonode.set('iszone', True)
            await protonode.set('zone', fqdn)
            return

        await protonode.set('iszone', False)

        if parent.get('iszone'):
            await protonode.set('zone', domain)
            return

        zone = parent.get('zone')
        if zone is not None:
            await protonode.set('zone', zone)

async def _onSetFqdnIsSuffix(node):

    fqdn = node.ndef[1]

    issuffix = node.get('issuffix')

    async with node.view.getEditor() as editor:
        async for child in node.view.nodesByPropValu('inet:fqdn:domain', '=', fqdn):
            await asyncio.sleep(0)

            if child.get('iszone') == issuffix:
                continue

            protonode = editor.loadNode(child)
            await protonode.set('iszone', issuffix)

async def _onSetFqdnIsZone(node):

    fqdn = node.ndef[1]

    iszone = node.get('iszone')
    if iszone:
        await node.set('zone', fqdn)
        return

    # we are not a zone...

    domain = node.get('domain')
    if not domain:
        await node.pop('zone')
        return

    parent = await node.view.addNode('inet:fqdn', domain)

    zone = parent.get('zone')
    if zone is None:
        await node.pop('zone')
        return

    await node.set('zone', zone)

async def _onSetFqdnZone(node):

    todo = collections.deque([node.ndef[1]])
    zone = node.get('zone')

    async with node.view.getEditor() as editor:
        while todo:
            fqdn = todo.pop()
            async for child in node.view.nodesByPropValu('inet:fqdn:domain', '=', fqdn):
                await asyncio.sleep(0)

                # if they are their own zone level, skip
                if child.get('iszone') or child.get('zone') == zone:
                    continue

                # the have the same zone we do
                protonode = editor.loadNode(child)
                await protonode.set('zone', zone)

                todo.append(child.ndef[1])

modeldefs = (
    ('inet', {
        'ctors': (

            ('inet:ip', 'synapse.models.inet.IPAddr', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IP address'}}),
                    ('geo:locatable', {'template': {'title': 'IP address'}}),
                ),
                'ex': '1.2.3.4',
                'doc': 'An IPv4 or IPv6 address.'}),

            ('inet:net', 'synapse.models.inet.IPRange', {}, {
                'ex': '1.2.3.4-1.2.3.8',
                'virts': (
                    ('mask', ('int', {}), {
                        'computed': True,
                        'doc': 'The mask if the range can be represented in CIDR notation.'}),

                    ('size', ('int', {}), {
                        'computed': True,
                        'doc': 'The number of addresses in the range.'}),
                ),
                'doc': 'An IPv4 or IPv6 address range.'}),

            ('inet:sockaddr', 'synapse.models.inet.SockAddr', {}, {
                'ex': 'tcp://1.2.3.4:80',
                'virts': (
                    ('ip', ('inet:ip', {}), {
                        'computed': True,
                        'doc': 'The IP address contained in the socket address URL.'}),

                    ('port', ('inet:port', {}), {
                        'computed': True,
                        'doc': 'The port contained in the socket address URL.'}),
                ),
                'doc': 'A network layer URL-like format to represent tcp/udp/icmp clients and servers.'}),

            ('inet:email', 'synapse.models.inet.Email', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'email address'}}),
                ),
                'doc': 'An email address.'}),

            ('inet:fqdn', 'synapse.models.inet.Fqdn', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'FQDN'}}),
                ),
                'ex': 'vertex.link',
                'doc': 'A Fully Qualified Domain Name (FQDN).'}),

            ('inet:rfc2822:addr', 'synapse.models.inet.Rfc2822Addr', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'RFC 2822 address'}}),
                ),
                'ex': '"Visi Kenshoto" <visi@vertex.link>',
                'doc': 'An RFC 2822 Address field.'}),

            ('inet:url', 'synapse.models.inet.Url', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'URL'}}),
                ),
                'ex': 'http://www.woot.com/files/index.html',
                'doc': 'A Universal Resource Locator (URL).'}),

            ('inet:http:cookie', 'synapse.models.inet.HttpCookie', {}, {
                'ex': 'PHPSESSID=el4ukv0kqbvoirg7nkp4dncpk3',
                'doc': 'An individual HTTP cookie string.'}),
        ),

        'edges': (
            (('inet:whois:iprecord', 'has', 'inet:ip'), {
                'doc': 'The IP whois record describes the IP address.'}),

            (('inet:net', 'has', 'inet:ip'), {
                'doc': 'The IP address range contains the IP address.'}),

            (('inet:fqdn', 'uses', 'meta:technique'), {
                'doc': 'The source FQDN was selected or created using the target technique.'}),

            (('inet:url', 'uses', 'meta:technique'), {
                'doc': 'The source URL was created using the target technique.'}),
        ),

        'types': (

            ('inet:ipv4', ('inet:ip', {'version': 4}), {
                'doc': 'An IPv4 address.'}),

            ('inet:ipv6', ('inet:ip', {'version': 6}), {
                'doc': 'An IPv4 address.'}),

            ('inet:asn', ('int', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'ASN'}}),
                ),
                'doc': 'An Autonomous System Number (ASN).'}),

            ('inet:proto', ('str', {'lower': True, 'regex': '^[a-z0-9+-]+$'}), {
                'doc': 'A network protocol name.'}),

            ('inet:asnip', ('comp', {'fields': (('asn', 'inet:asn'), ('ip', 'inet:ip'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IP ASN assignment'}}),
                ),
                'ex': '(54959, 1.2.3.4)',
                'doc': 'A historical record of an IP address being assigned to an AS.'}),

            ('inet:asnet', ('comp', {'fields': (('asn', 'inet:asn'), ('net', 'inet:net'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'address range'}}),
                ),
                'ex': '(54959, (1.2.3.4, 1.2.3.20))',
                'doc': 'An Autonomous System Number (ASN) and its associated IP address range.'}),

            ('inet:client', ('inet:sockaddr', {}), {
                'virts': (
                    ('ip', None, {'doc': 'The IP address of the client.'}),
                    ('port', None, {'doc': 'The port the client connected from.'}),
                ),
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'network client'}}),
                ),
                'doc': 'A network client address.'}),

            ('inet:download', ('guid', {}), {
                'doc': 'An instance of a file downloaded from a server.'}),

            ('inet:flow', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:link', {'template': {'link': 'flow'}}),
                ),
                'doc': 'A network connection between a client and server.'}),

            ('inet:tunnel:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of tunnel types.'}),

            ('inet:tunnel', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'tunnel'}}),
                ),
                'doc': 'A specific sequence of hosts forwarding connections such as a VPN or proxy.'}),

            ('inet:egress', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'egress client'}}),
                ),
                'doc': 'A host using a specific network egress client address.'}),

            ('inet:http:header:name', ('str', {'lower': True}), {}),

            ('inet:http:header', ('comp', {'fields': (('name', 'inet:http:header:name'), ('value', 'str'))}), {
                'doc': 'An HTTP protocol header key/value.'}),

            ('inet:http:request:header', ('inet:http:header', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'HTTP request header'}}),
                ),
                'doc': 'An HTTP request header.'}),

            ('inet:http:response:header', ('inet:http:header', {}), {
                'doc': 'An HTTP response header.'}),

            ('inet:http:param', ('comp', {'fields': (('name', 'str'), ('value', 'str'))}), {
                'doc': 'An HTTP request path query parameter.'}),

            ('inet:http:session', ('guid', {}), {
                'doc': 'An HTTP session.'}),

            ('inet:http:request', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:request', {}),
                ),
                'doc': 'A single HTTP request.'}),

            ('inet:iface:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of network interface types.'}),

            ('inet:iface', ('guid', {}), {
                'doc': 'A network interface with a set of associated protocol addresses.'}),

            ('inet:mac', ('str', {'lower': True, 'regex': '^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$'}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'MAC address'}}),
                ),
                'ex': 'aa:bb:cc:dd:ee:ff',
                'doc': 'A 48-bit Media Access Control (MAC) address.'}),

            ('inet:port', ('int', {'min': 0, 'max': 0xffff}), {
                'ex': '80',
                'doc': 'A network port.'}),

            ('inet:server', ('inet:sockaddr', {}), {
                'virts': (
                    ('ip', None, {'doc': 'The IP address of the server.'}),
                    ('port', None, {'doc': 'The port the server is listening on.'}),
                ),
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'network server'}}),
                ),
                'doc': 'A network server address.'}),

            ('inet:banner', ('comp', {'fields': (('server', 'inet:server'), ('text', 'it:dev:str'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'banner'}}),
                ),
                'doc': 'A network protocol banner string presented by a server.'}),

            ('inet:serverfile', ('comp', {'fields': (('server', 'inet:server'), ('file', 'file:bytes'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'host server and file'}}),
                ),
                'doc': 'A file hosted by a server.'}),

            ('inet:urlfile', ('comp', {'fields': (('url', 'inet:url'), ('file', 'file:bytes'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'hosted file and URL'}}),
                ),
                'doc': 'A file hosted at a specific Universal Resource Locator (URL).'}),

            ('inet:url:redir', ('comp', {'fields': (('source', 'inet:url'), ('target', 'inet:url'))}), {
                'template': {'title': 'URL redirection'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'ex': '(http://foo.com/,http://bar.com/)',
                'doc': 'A URL that redirects to another URL, such as via a URL shortening service '
                       'or an HTTP 302 response.'}),

            ('inet:url:mirror', ('comp', {'fields': (('of', 'inet:url'), ('at', 'inet:url'))}), {
                'template': {'title': 'URL mirror'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'doc': 'A URL mirror site.'}),

            ('inet:user', ('str', {'lower': True}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'username'}}),
                ),
                'doc': 'A username string.'}),

            ('inet:service:object', ('ndef', {'interface': 'inet:service:object'}), {
                'doc': 'A node which inherits the inet:service:object interface.'}),

            ('inet:search:query', ('guid', {}), {
                'interfaces': (
                    ('inet:service:action', {}),
                ),
                'doc': 'An instance of a search query issued to a search engine.'}),

            ('inet:search:result', ('guid', {}), {
                'doc': 'A single result from a web search.'}),

            ('inet:whois:record', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'registration record'}}),
                ),
                'prevnames': ('inet:whois:rec',),
                'doc': 'An FQDN whois registration record.'}),

            ('inet:whois:ipquery', ('guid', {}), {
                'doc': 'Query details used to retrieve an IP record.'}),

            ('inet:whois:iprecord', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'registration record'}}),
                ),
                'doc': 'An IPv4/IPv6 block registration record.'}),

            ('inet:wifi:ap', ('guid', {}), {
                'template': {'title': 'Wi-Fi access point'},
                'interfaces': (
                    ('meta:havable', {}),
                    ('geo:locatable', {}),
                    ('meta:observable', {}),
                ),
                'doc': 'An SSID/MAC address combination for a wireless access point.'}),

            ('inet:wifi:ssid', ('str', {'strip': False}), {
                'template': {'title': 'Wi-Fi SSID'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'ex': 'The Vertex Project',
                'doc': 'A Wi-Fi service set identifier (SSID) name.'}),

            ('inet:email:message', ('guid', {}), {
                'doc': 'An individual email message delivered to an inbox.'}),

            ('inet:email:header:name', ('str', {'lower': True}), {
                'ex': 'subject',
                'doc': 'An email header name.'}),

            ('inet:email:header', ('comp', {'fields': (('name', 'inet:email:header:name'), ('value', 'str'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'email header'}}),
                ),
                'doc': 'A unique email message header.'}),

            ('inet:email:message:attachment', ('guid', {}), {
                'doc': 'A file which was attached to an email message.'}),

            ('inet:email:message:link', ('guid', {}), {
                'doc': 'A url/link embedded in an email message.'}),

            ('inet:tls:jarmhash', ('str', {'lower': True, 'regex': '^(?<ciphers>[0-9a-f]{30})(?<extensions>[0-9a-f]{32})$'}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JARM fingerprint'}}),
                ),
                'doc': 'A TLS JARM fingerprint hash.'}),

            ('inet:tls:jarmsample', ('comp', {'fields': (('server', 'inet:server'), ('jarmhash', 'inet:tls:jarmhash'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JARM sample'}}),
                ),
                'doc': 'A JARM hash sample taken from a server.'}),

            ('inet:service:platform:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A service platform type taxonomy.'}),

            ('inet:service:platform', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'platform'}}),
                ),
                'doc': 'A network platform which provides services.'}),

            ('inet:service:agent', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'template': {'service:base': 'agent'},
                'doc': 'An instance of a deployed agent or software integration which is part of the service architecture.',
                'prevnames': ('inet:service:app',)}),

            ('inet:service:object:status', ('int', {'enums': svcobjstatus}), {
                'doc': 'An object status enumeration.'}),

            ('inet:service:account', ('guid', {}), {
                'template': {'title': 'service account'},
                'interfaces': (
                    ('entity:singular', {}),
                    ('entity:multiple', {}),
                    ('econ:pay:instrument', {}),
                    ('inet:service:subscriber', {}),
                ),
                'doc': 'An account within a service platform. Accounts may be instance specific.'}),

            ('inet:service:relationship:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A service object relationship type taxonomy.'}),

            ('inet:service:relationship', ('guid', {}), {
                'template': {'title': 'relationship'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'A relationship between two service objects.'}),

            ('inet:service:permission:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of service permission types.'}),

            ('inet:service:permission', ('guid', {}), {
                'template': {'title': 'permission'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'A permission which may be granted to a service account or role.'}),

            ('inet:service:rule', ('guid', {}), {
                'template': {'title': 'rule'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'A rule which grants or denies a permission to a service account or role.'}),

            ('inet:service:login', ('guid', {}), {
                'interfaces': (
                    ('inet:service:action', {}),
                ),
                'doc': 'A login event for a service account.'}),

            ('inet:service:login:method:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of service login methods.'}),

            ('inet:service:session', ('guid', {}), {
                'template': {'title': 'session'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'An authenticated session.'}),

            ('inet:service:joinable', ('ndef', {'interface': 'inet:service:joinable'}), {
                'doc': 'A node which implements the inet:service:joinable interface.'}),

            ('inet:service:role', ('guid', {}), {
                'template': {'title': 'service role'},
                'interfaces': (
                    ('inet:service:object', {}),
                    ('inet:service:joinable', {}),
                ),
                'doc': 'A role which contains member accounts.'}),

            ('inet:service:channel', ('guid', {}), {
                'template': {'title': 'channel'},
                'interfaces': (
                    ('inet:service:object', {}),
                    ('inet:service:joinable', {}),
                ),
                'doc': 'A channel used to distribute messages.'}),

            ('inet:service:thread', ('guid', {}), {
                'template': {'title': 'thread'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'A message thread.'}),

            ('inet:service:member', ('guid', {}), {
                'template': {'title': 'membership'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'Represents a service account being a member of a channel or group.'}),

            ('inet:service:message', ('guid', {}), {
                'interfaces': (
                    ('inet:service:action', {}),
                ),
                'doc': 'A message or post created by an account.'}),

            ('inet:service:message:link', ('guid', {}), {
                'doc': 'A URL link included within a message.'}),

            ('inet:service:message:attachment', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'file attachment'}}),
                ),
                'doc': 'A file attachment included within a message.'}),

            ('inet:service:message:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of message types.'}),

            ('inet:service:emote', ('guid', {}), {
                'template': {'title': 'emote'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'An emote or reaction by an account.'}),

            ('inet:service:access:action:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of service actions.'}),

            ('inet:service:access', ('guid', {}), {
                'interfaces': (
                    ('inet:service:action', {}),
                ),
                'doc': 'Represents a user access request to a service resource.'}),

            ('inet:service:tenant', ('guid', {}), {
                'template': {'title': 'tenant'},
                'interfaces': (
                    ('inet:service:subscriber', {}),
                ),
                'doc': 'A tenant which groups accounts and instances.'}),

            ('inet:service:subscription:level:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of platform specific subscription levels.'}),

            ('inet:service:subscription', ('guid', {}), {
                'template': {'title': 'subscription'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'A subscription to a service platform or instance.'}),

            ('inet:service:subscriber', ('ndef', {'interface': 'inet:service:subscriber'}), {
                'doc': 'A node which may subscribe to a service subscription.'}),

            ('inet:service:resource:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of service resource types.'}),

            ('inet:service:resource', ('guid', {}), {
                'template': {'title': 'resource'},
                'interfaces': (
                    ('inet:service:object', {}),
                ),
                'doc': 'A generic resource provided by the service architecture.'}),

            ('inet:service:bucket', ('inet:service:resource', {}), {
                'template': {'title': 'bucket'},
                'doc': 'A file/blob storage object within a service architecture.'}),

            ('inet:service:bucket:item', ('inet:service:resource', {}), {
                'template': {'title': 'bucket item'},
                'doc': 'An individual file stored within a bucket.'}),

            ('inet:rdp:handshake', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:request', {}),
                ),
                'doc': 'An instance of an RDP handshake between a client and server.'}),

            ('inet:ssh:handshake', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:request', {}),
                ),
                'doc': 'An instance of an SSH handshake between a client and server.'}),

            ('inet:tls:handshake', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:request', {}),
                ),
                'doc': 'An instance of a TLS handshake between a client and server.'}),

            ('inet:tls:ja4', ('str', {'regex': ja4_regex}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JA4 fingerprint'}}),
                ),
                'doc': 'A JA4 TLS client fingerprint.'}),

            ('inet:tls:ja4s', ('str', {'regex': ja4s_regex}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JA4S fingerprint'}}),
                ),
                'doc': 'A JA4S TLS server fingerprint.'}),

            ('inet:tls:ja4:sample', ('comp', {'fields': (('client', 'inet:client'), ('ja4', 'inet:tls:ja4'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JA4 sample'}}),
                ),
                'doc': 'A JA4 TLS client fingerprint used by a client.'}),

            ('inet:tls:ja4s:sample', ('comp', {'fields': (('server', 'inet:server'), ('ja4s', 'inet:tls:ja4s'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JA4S sample'}}),
                ),
                'doc': 'A JA4S TLS server fingerprint used by a server.'}),

            ('inet:tls:ja3s:sample', ('comp', {'fields': (('server', 'inet:server'), ('ja3s', 'crypto:hash:md5'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JA3S sample'}}),
                ),
                'doc': 'A JA3 sample taken from a server.'}),

            ('inet:tls:ja3:sample', ('comp', {'fields': (('client', 'inet:client'), ('ja3', 'crypto:hash:md5'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'JA3 sample'}}),
                ),
                'doc': 'A JA3 sample taken from a client.'}),

            ('inet:tls:servercert', ('comp', {'fields': (('server', 'inet:server'), ('cert', 'crypto:x509:cert'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'TLS server certificate'}}),
                ),
                'ex': '(1.2.3.4:443, c7437790af01ae1bb2f8f3b684c70bf8)',
                'doc': 'An x509 certificate sent by a server for TLS.'}),

            ('inet:tls:clientcert', ('comp', {'fields': (('client', 'inet:client'), ('cert', 'crypto:x509:cert'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'TLS client certificate'}}),
                ),
                'ex': '(1.2.3.4:443, 3fdf364e081c14997b291852d1f23868)',
                'doc': 'An x509 certificate sent by a client for TLS.'}),

        ),

        'interfaces': (

            ('inet:proto:link', {

                'doc': 'Properties common to network protocol requests and transports.',
                'template': {'link': 'link'},
                'props': (

                    ('flow', ('inet:flow', {}), {
                        'doc': 'The network flow which contained the {link}.'}),

                    ('client', ('inet:client', {}), {
                        'doc': 'The socket address of the client.'}),

                    ('client:host', ('it:host', {}), {
                        'doc': 'The client host which initiated the {link}.'}),

                    ('client:proc', ('it:exec:proc', {}), {
                        'doc': 'The client process which initiated the {link}.'}),

                    ('client:exe', ('file:bytes', {}), {
                        'doc': 'The client executable which initiated the {link}.'}),

                    ('server', ('inet:server', {}), {
                        'doc': 'The socket address of the server.'}),

                    ('server:host', ('it:host', {}), {
                        'doc': 'The server host which received the {link}.'}),

                    ('server:proc', ('it:exec:proc', {}), {
                        'doc': 'The server process which received the {link}.'}),

                    ('server:exe', ('file:bytes', {}), {
                        'doc': 'The server executable which received the {link}.'}),

                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'}),
                ),
            }),

            ('inet:proto:request', {

                'doc': 'Properties common to network protocol requests and responses.',
                'interfaces': (
                    ('inet:proto:link', {'template': {'link': 'request'}}),
                ),

                'props': (
                    ('time', ('time', {}), {
                        'doc': 'The time the request was sent.'}),
                ),
            }),

            ('inet:service:base', {
                'doc': 'Properties common to most forms within a service platform.',
                'template': {'title': 'node'},
                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'A platform specific ID which identifies the {title}.'}),

                    ('platform', ('inet:service:platform', {}), {
                        'doc': 'The platform which defines the {title}.'}),
                ),
            }),

            ('inet:service:object', {

                'doc': 'Properties common to objects within a service platform.',
                'template': {'title': 'object'},
                'interfaces': (
                    ('inet:service:base', {}),
                    ('meta:observable', {}),
                ),
                'props': (

                    ('url', ('inet:url', {}), {
                        'doc': 'The primary URL associated with the {title}.'}),

                    ('status', ('inet:service:object:status', {}), {
                        'doc': 'The status of the {title}.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period when the {title} existed.'}),

                    ('creator', ('inet:service:account', {}), {
                        'doc': 'The service account which created the {title}.'}),

                    ('remover', ('inet:service:account', {}), {
                        'doc': 'The service account which removed or decommissioned the {title}.'}),
                ),
            }),

            ('inet:service:joinable', {
                'doc': 'An interface common to nodes which can have accounts as members.'}),

            ('inet:service:subscriber', {
                'doc': 'Properties common to the nodes which subscribe to services.',
                'template': {'title': 'subscriber'},
                'interfaces': (
                    ('entity:actor', {}),
                    ('entity:abstract', {}),
                    ('inet:service:object', {}),
                ),
                'props': (
                    ('name', ('entity:name', {}), {
                        'doc': 'The primary entity name of the {title}.'}),
                    ('email', ('inet:email', {}), {
                        'doc': 'The primary email address for the {title}.'}),
                    ('user', ('inet:user', {}), {
                        'doc': 'The primary user name for the {title}.'}),
                    ('creds', ('array', {'type': 'auth:credential'}), {
                        'doc': 'An array of non-ephemeral credentials.'}),
                    ('profile', ('entity:contact', {}), {
                        'doc': 'Current detailed contact information for the {title}.'}),
                ),
            }),

            ('inet:service:action', {

                'doc': 'Properties common to events within a service platform.',
                'interfaces': (
                    ('inet:service:base', {}),
                ),
                'props': (

                    ('agent', ('inet:service:agent', {}), {
                        'doc': 'The service agent which performed the action potentially on behalf of an account.',
                        'prevnames': ('app',)}),

                    ('time', ('time', {}), {
                        'doc': 'The time that the account initiated the action.'}),

                    ('account', ('inet:service:account', {}), {
                        'doc': 'The account which initiated the action.'}),

                    ('success', ('bool', {}), {
                        'doc': 'Set to true if the action was successful.'}),

                    ('rule', ('inet:service:rule', {}), {
                        'doc': 'The rule which allowed or denied the action.'}),

                    ('error:code', ('str', {}), {
                        'doc': 'The platform specific error code if the action was unsuccessful.'}),

                    ('error:reason', ('str', {}), {
                        'doc': 'The platform specific friendly error reason if the action was unsuccessful.'}),

                    ('platform', ('inet:service:platform', {}), {
                        'doc': 'The platform where the action was initiated.'}),

                    ('session', ('inet:service:session', {}), {
                        'doc': 'The session which initiated the action.'}),

                    ('client', ('inet:client', {}), {
                        'doc': 'The network address of the client which initiated the action.'}),

                    ('client:software', ('it:software', {}), {
                        'doc': 'The client software used to initiate the action.',
                        'prevnames': ('client:app',)}),

                    ('client:host', ('it:host', {}), {
                        'doc': 'The client host which initiated the action.'}),

                    ('server', ('inet:server', {}), {
                        'doc': 'The network address of the server which handled the action.'}),

                    ('server:host', ('it:host', {}), {
                        'doc': 'The server host which handled the action.'}),

                ),
            }),
        ),

        'forms': (

            ('inet:proto', {}, (
                ('port', ('inet:port', {}), {
                    'doc': 'The default port this protocol typically uses if applicable.'}),
            )),

            ('inet:email:message', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The ID parsed from the "message-id" header.'}),

                ('to', ('inet:email', {}), {
                    'doc': 'The email address of the recipient.'}),

                ('from', ('inet:email', {}), {
                    'doc': 'The email address of the sender.'}),

                ('replyto', ('inet:email', {}), {
                    'doc': 'The email address parsed from the "reply-to" header.'}),

                ('cc', ('array', {'type': 'inet:email'}), {
                    'doc': 'Email addresses parsed from the "cc" header.'}),

                ('subject', ('str', {}), {
                    'doc': 'The email message subject parsed from the "subject" header.'}),

                ('body', ('text', {}), {
                    'doc': 'The body of the email message.'}),

                ('date', ('time', {}), {
                    'doc': 'The time the email message was delivered.'}),

                ('bytes', ('file:bytes', {}), {
                    'doc': 'The file bytes which contain the email message.'}),

                ('headers', ('array', {'type': 'inet:email:header', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of email headers from the message.'}),

                ('received:from:ip', ('inet:ip', {}), {
                    'doc': 'The sending SMTP server IP, potentially from the Received: header.',
                    'prevnames': ('received:from:ipv4', 'received:from:ipv6')}),

                ('received:from:fqdn', ('inet:fqdn', {}), {
                    'doc': 'The sending server FQDN, potentially from the Received: header.'}),

                ('flow', ('inet:flow', {}), {
                    'doc': 'The inet:flow which delivered the message.'}),

                ('links', ('array', {'type': 'inet:email:message:link'}), {
                    'doc': 'An array of links embedded in the email message.'}),

                ('attachments', ('array', {'type': 'inet:email:message:attachment'}), {
                    'doc': 'An array of files attached to the email message.'}),
            )),

            ('inet:email:header', {}, (
                ('name', ('inet:email:header:name', {}), {
                    'computed': True,
                    'doc': 'The name of the email header.'}),
                ('value', ('str', {}), {
                    'computed': True,
                    'doc': 'The value of the email header.'}),
            )),

            ('inet:email:message:attachment', {}, (
                ('file', ('file:bytes', {}), {
                    'doc': 'The attached file.'}),
                ('name', ('file:path', {}), {
                    'doc': 'The name of the attached file.'}),
            )),

            ('inet:email:message:link', {}, (
                ('url', ('inet:url', {}), {
                    'doc': 'The url contained within the email message.'}),
                ('text', ('str', {}), {
                    'doc': 'The displayed hyperlink text if it was not the URL.'}),
            )),

            ('inet:asn', {}, (

                ('owner', ('entity:actor', {}), {
                    'doc': 'The entity which registered the ASN.'}),

                ('owner:name', ('entity:name', {}), {
                    'doc': 'The name of the entity which registered the ASN.'}),
            )),

            ('inet:asnip', {}, (

                ('asn', ('inet:asn', {}), {
                    'computed': True,
                    'doc': 'The ASN that the IP was assigned to.'}),

                ('ip', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The IP that was assigned to the ASN.'}),
            )),

            ('inet:asnet', {
                'prevnames': ('inet:asnet4', 'inet:asnet6')}, (

                ('asn', ('inet:asn', {}), {
                    'computed': True,
                    'doc': 'The Autonomous System Number (ASN) of the netblock.'
                }),
                ('net', ('inet:net', {}), {
                    'computed': True,
                    'doc': 'The IP address range assigned to the ASN.',
                    'prevnames': ('net4', 'net6')}),

                ('net:min', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The first IP in the range assigned to the ASN.',
                    'prevnames': ('net4:min', 'net6:min')}),

                ('net:max', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The last IP in the range assigned to the ASN.',
                    'prevnames': ('net4:max', 'net6:max')}),
            )),

            ('inet:net', {
                'prevnames': ('inet:cidr4', 'inet:cidr6')}, (

                ('min', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The first IP address in the network range.'}),

                ('max', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The last IP address in the network range.'}),
            )),

            ('inet:client', {}, (
                ('proto', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The network protocol of the client.'
                }),
                ('ip', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The IP of the client.',
                    'prevnames': ('ipv4', 'ipv6')}),

                ('port', ('inet:port', {}), {
                    'doc': 'The client tcp/udp port.'
                }),
            )),

            ('inet:email', {}, (

                ('user', ('inet:user', {}), {
                    'computed': True,
                    'doc': 'The username of the email address.'}),

                ('fqdn', ('inet:fqdn', {}), {
                    'computed': True,
                    'doc': 'The domain of the email address.'}),

                ('plus', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The optional email address "tag".'}),

                ('base', ('inet:email', {}), {
                    'computed': True,
                    'doc': 'The base email address which is populated if the email address contains a user with a +<tag>.'}),
            )),

            ('inet:flow', {}, (

                ('period', ('ival', {}), {
                    'doc': 'The period when the flow was active.'}),

                ('server:txfiles', ('array', {'type': 'file:attachment'}), {
                    'doc': 'An array of files sent by the server.'}),

                ('server:txcount', ('int', {}), {
                    'doc': 'The number of packets sent by the server.'}),

                ('server:txbytes', ('int', {}), {
                    'doc': 'The number of bytes sent by the server.'}),

                ('server:handshake', ('text', {}), {
                    'doc': 'A text representation of the initial handshake sent by the server.'}),

                ('client:txfiles', ('array', {'type': 'file:attachment'}), {
                    'doc': 'An array of files sent by the client.'}),

                ('client:txcount', ('int', {}), {
                    'doc': 'The number of packets sent by the client.'}),

                ('client:txbytes', ('int', {}), {
                    'doc': 'The number of bytes sent by the client.'}),

                ('client:handshake', ('text', {}), {
                    'doc': 'A text representation of the initial handshake sent by the client.'}),

                ('tot:txcount', ('int', {}), {
                    'doc': 'The number of packets sent in both directions.'}),

                ('tot:txbytes', ('int', {}), {
                    'doc': 'The number of bytes sent in both directions.'}),

                ('server:cpes', ('array', {'type': 'it:sec:cpe'}), {
                    'doc': 'An array of NIST CPEs identified on the server.'}),

                ('server:softnames', ('array', {'type': 'meta:name'}), {
                    'doc': 'An array of software names identified on the server.'}),

                ('client:cpes', ('array', {'type': 'it:sec:cpe'}), {
                    'doc': 'An array of NIST CPEs identified on the client.'}),

                ('client:softnames', ('array', {'type': 'meta:name'}), {
                    'doc': 'An array of software names identified on the client.'}),

                ('ip:proto', ('int', {'min': 0, 'max': 0xff}), {
                    'doc': 'The IP protocol number of the flow.'}),

                ('ip:tcp:flags', ('int', {'min': 0, 'max': 0xff}), {
                    'doc': 'An aggregation of observed TCP flags commonly provided by flow APIs.'}),

                ('capture:host', ('it:host', {}), {
                    'doc': 'The host which captured the flow.'}),
            )),

            ('inet:tunnel:type:taxonomy', {}, ()),
            ('inet:tunnel', {}, (

                ('anon', ('bool', {}), {
                    'doc': 'Indicates that this tunnel provides anonymization.'}),

                ('type', ('inet:tunnel:type:taxonomy', {}), {
                    'doc': 'The type of tunnel such as vpn or proxy.'}),

                ('ingress', ('inet:server', {}), {
                    'doc': 'The server where client traffic enters the tunnel.'}),

                ('egress', ('inet:server', {}), {
                    'doc': 'The server where client traffic leaves the tunnel.'}),

                ('operator', ('entity:actor', {}), {
                    'doc': 'The contact information for the tunnel operator.'}),
            )),

            ('inet:egress', {}, (

                ('host', ('it:host', {}), {
                    'doc': 'The host that used the network egress.'}),

                ('host:iface', ('inet:iface', {}), {
                    'doc': 'The interface which the host used to connect out via the egress.'}),

                ('account', ('inet:service:account', {}), {
                    'doc': 'The service account which used the client address to egress.'}),

                ('client', ('inet:client', {}), {
                    'doc': 'The client address the host used as a network egress.'}),
            )),

            ('inet:fqdn', {}, (
                ('domain', ('inet:fqdn', {}), {
                    'computed': True,
                    'doc': 'The parent domain for the FQDN.',
                }),
                ('host', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The host part of the FQDN.',
                }),
                ('issuffix', ('bool', {}), {
                    'doc': 'True if the FQDN is considered a suffix.',
                }),
                ('iszone', ('bool', {}), {
                    'doc': 'True if the FQDN is considered a zone.',
                }),
                ('zone', ('inet:fqdn', {}), {
                    'doc': 'The zone level parent for this FQDN.',
                }),
            )),

            ('inet:http:request:header', {}, (

                ('name', ('inet:http:header:name', {}), {'computed': True,
                    'doc': 'The name of the HTTP request header.'}),

                ('value', ('str', {}), {'computed': True,
                    'doc': 'The value of the HTTP request header.'}),

            )),

            ('inet:http:response:header', {}, (

                ('name', ('inet:http:header:name', {}), {'computed': True,
                    'doc': 'The name of the HTTP response header.'}),

                ('value', ('str', {}), {'computed': True,
                    'doc': 'The value of the HTTP response header.'}),

            )),

            ('inet:http:param', {}, (

                ('name', ('str', {'lower': True}), {'computed': True,
                    'doc': 'The name of the HTTP query parameter.'}),

                ('value', ('str', {}), {'computed': True,
                    'doc': 'The value of the HTTP query parameter.'}),

            )),

            ('inet:http:cookie', {}, (
                ('name', ('str', {}), {
                    'doc': 'The name of the cookie preceding the equal sign.'}),
                ('value', ('str', {}), {
                    'doc': 'The value of the cookie after the equal sign if present.'}),
            )),

            ('inet:http:request', {}, (

                ('method', ('str', {}), {
                    'doc': 'The HTTP request method string.'}),

                ('path', ('str', {}), {
                    'doc': 'The requested HTTP path (without query parameters).'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The reconstructed URL for the request if known.'}),

                ('query', ('str', {}), {
                    'doc': 'The HTTP query string which optionally follows the path.'}),

                ('headers', ('array', {'type': 'inet:http:request:header', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of HTTP headers from the request.'}),

                ('header:host', ('inet:fqdn', {}), {
                    'doc': 'The FQDN parsed from the "Host:" header in the request.'}),

                ('header:referer', ('inet:url', {}), {
                    'doc': 'The referer URL parsed from the "Referer:" header in the request.'}),

                ('body', ('file:bytes', {}), {
                    'doc': 'The body of the HTTP request.'}),

                ('cookies', ('array', {'type': 'inet:http:cookie'}), {
                    'doc': 'An array of HTTP cookie values parsed from the "Cookies:" header in the request.'}),

                ('response:time', ('time', {}), {
                    'doc': 'The time a response to the request was received.'}),

                ('response:code', ('int', {}), {
                    'doc': 'The HTTP response code received.'}),

                ('response:reason', ('str', {}), {
                    'doc': 'The HTTP response reason phrase received.'}),

                ('response:headers', ('array', {'type': 'inet:http:response:header', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of HTTP headers from the response.'}),

                ('response:body', ('file:bytes', {}), {
                    'doc': 'The HTTP response body received.'}),

                ('session', ('inet:http:session', {}), {
                    'doc': 'The HTTP session this request was part of.'}),
            )),

            ('inet:http:session', {}, (

                ('contact', ('entity:contact', {}), {
                    'doc': 'The entity contact which owns the session.'}),

                ('cookies', ('array', {'type': 'inet:http:cookie'}), {
                    'doc': 'An array of cookies used to identify this specific session.'}),
            )),

            ('inet:iface:type:taxonomy', {}, ()),
            ('inet:iface', {}, (
                ('host', ('it:host', {}), {
                    'doc': 'The guid of the host the interface is associated with.'}),

                ('name', ('str', {}), {
                    'ex': 'eth0',
                    'doc': 'The interface name.'}),

                ('network', ('it:network', {}), {
                    'doc': 'The guid of the it:network the interface connected to.'}),

                ('type', ('inet:iface:type:taxonomy', {}), {
                    'doc': 'The interface type.'}),

                ('mac', ('inet:mac', {}), {
                    'doc': 'The ethernet (MAC) address of the interface.'}),

                ('ip', ('inet:ip', {}), {
                    'doc': 'The IP address of the interface.',
                    'prevnames': ('ipv4', 'ipv6')}),

                ('phone', ('tel:phone', {}), {
                    'doc': 'The telephone number of the interface.'}),

                ('wifi:ap:ssid', ('inet:wifi:ssid', {}), {
                    'doc': 'The SSID of the Wi-Fi AP the interface connected to.'}),

                ('wifi:ap:bssid', ('inet:mac', {}), {
                    'doc': 'The BSSID of the Wi-Fi AP the interface connected to.'}),

                ('adid', ('it:adid', {}), {
                    'doc': 'An advertising ID associated with the interface.'}),

                ('mob:imei', ('tel:mob:imei', {}), {
                    'doc': 'The IMEI of the interface.'}),

                ('mob:imsi', ('tel:mob:imsi', {}), {
                    'doc': 'The IMSI of the interface.'}),
            )),

            ('inet:ip', {
                'prevnames': ('inet:ipv4', 'inet:ipv6')}, (

                ('asn', ('inet:asn', {}), {
                    'doc': 'The ASN to which the IP address is currently assigned.'}),

                ('type', ('str', {}), {
                    'doc': 'The type of IP address (e.g., private, multicast, etc.).'}),

                ('dns:rev', ('inet:fqdn', {}), {
                    'doc': 'The most current DNS reverse lookup for the IP.'}),

                ('scope', ('str', {'enums': scopes_enum}), {
                    'doc': 'The IPv6 scope of the address (e.g., global, link-local, etc.).'}),

                ('version', ('int', {'enums': ((4, '4'), (6, '6'))}), {
                    'doc': 'The IP version of the address.'}),
            )),


            ('inet:mac', {}, (

                ('vendor', ('ou:org', {}), {
                    'doc': 'The vendor associated with the 24-bit prefix of a MAC address.'}),

                ('vendor:name', ('entity:name', {}), {
                    'doc': 'The name of the vendor associated with the 24-bit prefix of a MAC address.'}),
            )),

            ('inet:rfc2822:addr', {}, (
                ('name', ('entity:name', {}), {
                    'computed': True,
                    'doc': 'The name field parsed from an RFC 2822 address string.'
                }),
                ('email', ('inet:email', {}), {
                    'computed': True,
                    'doc': 'The email field parsed from an RFC 2822 address string.'
                }),
            )),

            ('inet:server', {}, (
                ('proto', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The network protocol of the server.'
                }),
                ('ip', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The IP of the server.',
                    'prevnames': ('ipv4', 'ipv6')}),

                ('port', ('inet:port', {}), {
                    'doc': 'The server tcp/udp port.'
                }),
            )),

            ('inet:banner', {}, (

                ('server', ('inet:server', {}), {'computed': True,
                    'doc': 'The server which presented the banner string.'}),

                ('text', ('it:dev:str', {}), {'computed': True,
                    'doc': 'The banner text.'}),
            )),

            ('inet:url', {}, (

                ('fqdn', ('inet:fqdn', {}), {
                    'computed': True,
                    'doc': 'The fqdn used in the URL (e.g., http://www.woot.com/page.html).'}),

                ('ip', ('inet:ip', {}), {
                    'computed': True,
                    'doc': 'The IP address used in the URL (e.g., http://1.2.3.4/page.html).',
                    'prevnames': ('ipv4', 'ipv6')}),

                ('passwd', ('auth:passwd', {}), {
                    'computed': True,
                    'doc': 'The optional password used to access the URL.'}),

                ('base', ('str', {}), {
                    'computed': True,
                    'doc': 'The base scheme, user/pass, fqdn, port and path w/o parameters.'}),

                ('path', ('str', {}), {
                    'computed': True,
                    'doc': 'The path in the URL w/o parameters.'}),

                ('params', ('str', {}), {
                    'computed': True,
                    'doc': 'The URL parameter string.'}),

                ('port', ('inet:port', {}), {
                    'computed': True,
                    'doc': 'The port of the URL. URLs prefixed with http will be set to port 80 and '
                           'URLs prefixed with https will be set to port 443 unless otherwise specified.'}),

                ('proto', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The protocol in the URL.'}),

                ('user', ('inet:user', {}), {
                    'computed': True,
                    'doc': 'The optional username used to access the URL.'}),

            )),

            ('inet:serverfile', {}, (
                ('server', ('inet:server', {}), {
                    'computed': True,
                    'doc': 'The server which hosted the file.'}),

                ('file', ('file:bytes', {}), {
                    'computed': True,
                    'doc': 'The file that was hosted on the server.'}),
            )),

            ('inet:urlfile', {}, (

                ('url', ('inet:url', {}), {
                    'computed': True,
                    'doc': 'The URL where the file was hosted.'}),

                ('file', ('file:bytes', {}), {
                    'computed': True,
                    'doc': 'The file that was hosted at the URL.'}),
            )),

            ('inet:url:redir', {}, (
                ('source', ('inet:url', {}), {
                    'computed': True,
                    'doc': 'The original/source URL before redirect.'}),

                ('target', ('inet:url', {}), {
                    'computed': True,
                    'doc': 'The redirected/destination URL.'}),
            )),

            ('inet:url:mirror', {}, (

                ('of', ('inet:url', {}), {
                    'computed': True,
                    'doc': 'The URL being mirrored.'}),

                ('at', ('inet:url', {}), {
                    'computed': True,
                    'doc': 'The URL of the mirror.'}),
            )),

            ('inet:user', {}, ()),

            ('inet:search:query', {}, (

                ('text', ('text', {}), {
                    'doc': 'The search query text.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the web search was issued.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host that issued the query.'}),

                ('engine', ('base:name', {}), {
                    'ex': 'google',
                    'doc': 'A simple name for the search engine used.'}),

                ('request', ('inet:http:request', {}), {
                    'doc': 'The HTTP request used to issue the query.'}),
            )),

            ('inet:search:result', {}, (

                ('query', ('inet:search:query', {}), {
                    'doc': 'The search query that produced the result.'}),

                ('title', ('str', {'lower': True}), {
                    'doc': 'The title of the matching web page.'}),

                ('rank', ('int', {}), {
                    'doc': 'The rank/order of the query result.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL hosting the matching content.'}),

                ('text', ('str', {'lower': True}), {
                    'doc': 'Extracted/matched text from the matched content.'}),
            )),

            ('inet:whois:record', {}, (

                ('fqdn', ('inet:fqdn', {}), {
                    'doc': 'The domain associated with the whois record.'}),

                ('text', ('text', {'lower': True}), {
                    'doc': 'The full text of the whois record.'}),

                ('created', ('time', {}), {
                    'doc': 'The "created" time from the whois record.'}),

                ('updated', ('time', {}), {
                    'doc': 'The "last updated" time from the whois record.'}),

                ('expires', ('time', {}), {
                    'doc': 'The "expires" time from the whois record.'}),

                ('registrar', ('entity:name', {}), {
                    'doc': 'The registrar name from the whois record.'}),

                ('registrant', ('entity:name', {}), {
                    'doc': 'The registrant name from the whois record.'}),

                ('contacts', ('array', {'type': 'entity:contact'}), {
                    'doc': 'The whois registration contacts.'}),

                ('nameservers', ('array', {'type': 'inet:fqdn', 'uniq': False, 'sorted': False}), {
                    'doc': 'The DNS nameserver FQDNs for the registered FQDN.'}),

            )),

            ('inet:whois:ipquery', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time the request was made.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The query URL when using the HTTP RDAP Protocol.'}),

                ('fqdn', ('inet:fqdn', {}), {
                    'doc': 'The FQDN of the host server when using the legacy WHOIS Protocol.'}),

                ('ip', ('inet:ip', {}), {
                    'doc': 'The IP address queried.',
                    'prevnames': ('ipv4', 'ipv6')}),

                ('success', ('bool', {}), {
                    'doc': 'Whether the host returned a valid response for the query.'}),

                ('rec', ('inet:whois:iprecord', {}), {
                    'doc': 'The resulting record from the query.'}),
            )),

            ('inet:whois:iprecord', {}, (

                ('net', ('inet:net', {}), {
                    'prevnames': ('net4', 'net6'),
                    'doc': 'The IP address range assigned.'}),

                ('desc', ('text', {}), {
                    'doc': 'The description of the network from the whois record.'}),

                ('created', ('time', {}), {
                    'doc': 'The "created" time from the record.'}),

                ('updated', ('time', {}), {
                    'doc': 'The "last updated" time from the record.'}),

                ('text', ('text', {'lower': True}), {
                    'doc': 'The full text of the record.'}),

                ('asn', ('inet:asn', {}), {
                    'doc': 'The associated Autonomous System Number (ASN).'}),

                ('id', ('meta:id', {}), {
                    'doc': 'The registry unique identifier (e.g. NET-74-0-0-0-1).'}),

                ('parentid', ('meta:id', {}), {
                    'doc': 'The registry unique identifier of the parent whois record (e.g. NET-74-0-0-0-0).'}),

                ('name', ('meta:id', {}), {
                    'doc': 'The name ID assigned to the network by the registrant.'}),

                ('country', ('iso:3166:alpha2', {}), {
                    'doc': 'The ISO 3166 Alpha-2 country code.'}),

                ('status', ('str', {'lower': True}), {
                    'doc': 'The state of the registered network.'}),

                ('type', ('str', {'lower': True}), {
                    'doc': 'The classification of the registered network (e.g. direct allocation).'}),

                ('links', ('array', {'type': 'inet:url'}), {
                    'doc': 'URLs provided with the record.'}),

                ('contacts', ('array', {'type': 'entity:contact'}), {
                    'doc': 'The whois registration contacts.'}),
            )),

            ('inet:wifi:ap', {}, (

                ('ssid', ('inet:wifi:ssid', {}), {
                    'doc': 'The SSID for the wireless access point.', 'computed': True, }),

                ('bssid', ('inet:mac', {}), {
                    'doc': 'The MAC address for the wireless access point.', 'computed': True, }),

                ('channel', ('int', {}), {
                    'doc': 'The WIFI channel that the AP was last observed operating on.'}),

                ('encryption', ('str', {'lower': True}), {
                    'doc': 'The type of encryption used by the WIFI AP such as "wpa2".'}),

                # FIXME ownable interface? currently has :owner via meta:havable
                ('org', ('ou:org', {}), {
                    'doc': 'The organization that owns/operates the access point.'}),
            )),

            ('inet:wifi:ssid', {}, ()),

            ('inet:tls:jarmhash', {}, (
                ('ciphers', ('str', {'lower': True, 'regex': '^[0-9a-f]{30}$'}), {
                    'computed': True,
                    'doc': 'The encoded cipher and TLS version of the server.'}),
                ('extensions', ('str', {'lower': True, 'regex': '^[0-9a-f]{32}$'}), {
                    'computed': True,
                    'doc': 'The truncated SHA256 of the TLS server extensions.'}),
            )),
            ('inet:tls:jarmsample', {}, (
                ('jarmhash', ('inet:tls:jarmhash', {}), {
                    'computed': True,
                    'doc': 'The JARM hash computed from the server responses.'}),
                ('server', ('inet:server', {}), {
                    'computed': True,
                    'doc': 'The server that was sampled to compute the JARM hash.'}),
            )),

            ('inet:tls:ja4', {}, ()),
            ('inet:tls:ja4s', {}, ()),

            ('inet:tls:ja4:sample', {}, (

                ('ja4', ('inet:tls:ja4', {}), {
                    'computed': True,
                    'doc': 'The JA4 TLS client fingerprint.'}),

                ('client', ('inet:client', {}), {
                    'computed': True,
                    'doc': 'The client which initiated the TLS handshake with a JA4 fingerprint.'}),
            )),

            ('inet:tls:ja4s:sample', {}, (

                ('ja4s', ('inet:tls:ja4s', {}), {
                    'computed': True,
                    'doc': 'The JA4S TLS server fingerprint.'}),

                ('server', ('inet:server', {}), {
                    'computed': True,
                    'doc': 'The server which responded to the TLS handshake with a JA4S fingerprint.'}),
            )),

            ('inet:rdp:handshake', {}, (

                ('client:hostname', ('it:hostname', {}), {
                    'doc': 'The hostname sent by the client as part of an RDP session setup.'}),

                ('client:keyboard:layout', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The keyboard layout sent by the client as part of an RDP session setup.'}),
            )),

            ('inet:ssh:handshake', {}, (

                ('server:key', ('crypto:key', {}), {
                    'doc': 'The key used by the SSH server.'}),

                ('client:key', ('crypto:key', {}), {
                    'doc': 'The key used by the SSH client.'}),
            )),

            ('inet:tls:handshake', {}, (

                ('server:cert', ('crypto:x509:cert', {}), {
                    'doc': 'The x509 certificate sent by the server during the handshake.'}),

                ('server:ja3s', ('crypto:hash:md5', {}), {
                    'doc': 'The JA3S fingerprint of the server response.'}),

                ('server:ja4s', ('inet:tls:ja4s', {}), {
                    'doc': 'The JA4S fingerprint of the server response.'}),

                ('server:jarmhash', ('inet:tls:jarmhash', {}), {
                    'doc': 'The JARM hash computed from the server response.'}),

                ('client:cert', ('crypto:x509:cert', {}), {
                    'doc': 'The x509 certificate sent by the client during the handshake.'}),

                ('client:ja3', ('crypto:hash:md5', {}), {
                    'doc': 'The JA3 fingerprint of the client request.'}),

                ('client:ja4', ('inet:tls:ja4', {}), {
                    'doc': 'The JA4 fingerprint of the client request.'}),
            )),

            ('inet:tls:ja3s:sample', {}, (

                ('server', ('inet:server', {}), {
                    'computed': True,
                    'doc': 'The server that was sampled to produce the JA3S hash.'}),

                ('ja3s', ('crypto:hash:md5', {}), {
                    'computed': True,
                    'doc': "The JA3S hash computed from the server's TLS hello packet."})
            )),

            ('inet:tls:ja3:sample', {}, (

                ('client', ('inet:client', {}), {
                    'computed': True,
                    'doc': 'The client that was sampled to produce the JA3 hash.'}),

                ('ja3', ('crypto:hash:md5', {}), {
                    'computed': True,
                    'doc': "The JA3 hash computed from the client's TLS hello packet."})
            )),

            ('inet:tls:servercert', {}, (

                ('server', ('inet:server', {}), {
                    'computed': True,
                    'doc': 'The server associated with the x509 certificate.'}),

                ('cert', ('crypto:x509:cert', {}), {
                    'computed': True,
                    'doc': 'The x509 certificate sent by the server.'})
            )),

            ('inet:tls:clientcert', {}, (

                ('client', ('inet:client', {}), {
                    'computed': True,
                    'doc': 'The client associated with the x509 certificate.'}),

                ('cert', ('crypto:x509:cert', {}), {
                    'computed': True,
                    'doc': 'The x509 certificate sent by the client.'})
            )),

            ('inet:service:platform:type:taxonomy', {}, ()),
            ('inet:service:platform', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'An ID which identifies the platform.'}),

                ('url', ('inet:url', {}), {
                    'ex': 'https://twitter.com',
                    'alts': ('urls',),
                    'doc': 'The primary URL of the platform.'}),

                ('urls', ('array', {'type': 'inet:url'}), {
                    'doc': 'An array of alternate URLs for the platform.'}),

                ('zone', ('inet:fqdn', {}), {
                    'alts': ('zones',),
                    'doc': 'The primary zone for the platform.'}),

                ('zones', ('array', {'type': 'inet:fqdn'}), {
                    'doc': 'An array of alternate zones for the platform.'}),

                ('name', ('meta:name', {}), {
                    'ex': 'twitter',
                    'alts': ('names',),
                    'doc': 'A friendly name for the platform.'}),

                ('names', ('array', {'type': 'meta:name'}), {
                    'doc': 'An array of alternate names for the platform.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the service platform.'}),

                ('type', ('inet:service:platform:type:taxonomy', {}), {
                    'doc': 'The type of service platform.'}),

                ('family', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'A family designation for use with instanced platforms such as Slack, Discord, or Mastodon.'}),

                ('parent', ('inet:service:platform', {}), {
                    'doc': 'A parent platform which owns this platform.'}),

                ('status', ('inet:service:object:status', {}), {
                    'doc': 'The status of the platform.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period when the platform existed.'}),

                ('creator', ('inet:service:account', {}), {
                    'doc': 'The service account which created the platform.'}),

                ('remover', ('inet:service:account', {}), {
                    'doc': 'The service account which removed or decommissioned the platform.'}),

                ('provider', ('ou:org', {}), {
                    'doc': 'The organization which operates the platform.'}),

                ('provider:name', ('entity:name', {}), {
                    'doc': 'The name of the organization which operates the platform.'}),

                ('software', ('it:software', {}), {
                    'doc': 'The latest known software version that the platform is running.'}),
            )),


            ('inet:service:agent', {}, (

                ('name', ('str', {'lower': True, 'onespace': True}), {
                    'alts': ('names',),
                    'doc': 'The name of the service agent instance.'}),

                ('names', ('array', {'type': 'str', 'typeopts': {'onespace': True, 'lower': True}}), {
                    'doc': 'An array of alternate names for the service agent instance.'}),

                ('desc', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A description of the deployed service agent instance.'}),

                ('software', ('it:software', {}), {
                    'doc': 'The latest known software version running on the service agent instance.'}),
            )),

            ('inet:service:account', {}, (
                ('tenant', ('inet:service:tenant', {}), {
                    'doc': 'The tenant which contains the account.'}),

                ('parent', ('inet:service:account', {}), {
                    'doc': 'A parent account which owns this account.'}),

                ('rules', ('array', {'type': 'inet:service:rule', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of rules associated with this account.'}),
            )),

            ('inet:service:relationship:type:taxonomy', {}, ()),
            ('inet:service:relationship', {}, (

                ('source', ('inet:service:object', {}), {
                    'doc': 'The source object.'}),

                ('target', ('inet:service:object', {}), {
                    'doc': 'The target object.'}),

                ('type', ('inet:service:relationship:type:taxonomy', {}), {
                    'ex': 'follows',
                    'doc': 'The type of relationship between the source and the target.'}),
            )),

            ('inet:service:role', {}, (

                ('name', ('base:name', {}), {
                    'doc': 'The name of the role on this platform.'}),

                ('profile', ('entity:contact', {}), {
                    'doc': 'Current detailed contact information for this role.'}),

                ('rules', ('array', {'type': 'inet:service:rule', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of rules associated with this role.'}),
            )),

            ('inet:service:permission:type:taxonomy', {}, ()),

            ('inet:service:permission', {}, (

                ('name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'The name of the permission.'}),

                ('type', ('inet:service:permission:type:taxonomy', {}), {
                    'doc': 'The type of permission.'}),

            )),

            ('inet:service:rule', {}, (

                ('permission', ('inet:service:permission', {}), {
                    'doc': 'The permission which is granted.'}),

                ('denied', ('bool', {}), {
                    'doc': 'Set to (true) to denote that the rule is an explicit deny.'}),

                ('object', ('ndef', {'interface': 'inet:service:object'}), {
                    'doc': 'The object that the permission controls access to.'}),

                ('grantee', ('ndef', {'forms': ('inet:service:account', 'inet:service:role')}), {
                    'doc': 'The user or role which is granted the permission.'}),
            )),

            ('inet:service:session', {}, (

                ('creator', ('inet:service:account', {}), {
                    'doc': 'The account which authenticated to create the session.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period where the session was valid.'}),

                ('http:session', ('inet:http:session', {}), {
                    'doc': 'The HTTP session associated with the service session.'}),
            )),

            ('inet:service:login:method:taxonomy', {}, ()),
            ('inet:service:login', {}, (

                ('url', ('inet:url', {}), {
                    'doc': 'The URL of the login endpoint used for this login attempt.'}),

                ('method', ('inet:service:login:method:taxonomy', {}), {
                    'doc': 'The type of authentication used for the login. For example "password" or "multifactor.sms".'}),

                ('creds', ('array', {'type': 'auth:credential'}), {
                    'doc': 'The credentials that were used to login.'}),
            )),

            ('inet:service:message:type:taxonomy', {}, ()),
            ('inet:service:message', {}, (

                ('account', ('inet:service:account', {}), {
                    'doc': 'The account which sent the message.'}),

                ('to', ('inet:service:account', {}), {
                    'doc': 'The destination account. Used for direct messages.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the message may be viewed.'}),

                ('role', ('inet:service:role', {}), {
                    'doc': 'The role that the message was sent to.'}),

                ('channel', ('inet:service:channel', {}), {
                    'doc': 'The channel that the message was sent to.'}),

                ('thread', ('inet:service:thread', {}), {
                    'doc': 'The thread which contains the message.'}),

                ('public', ('bool', {}), {
                    'doc': 'Set to true if the message is publicly visible.'}),

                ('title', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The message title.'}),

                ('text', ('text', {}), {
                    'doc': 'The text body of the message.'}),

                ('status', ('inet:service:object:status', {}), {
                    'doc': 'The message status.'}),

                ('replyto', ('inet:service:message', {}), {
                    'doc': 'The message that this message was sent in reply to. Used for message threading.'}),

                ('repost', ('inet:service:message', {}), {
                    'doc': 'The original message reposted by this message.'}),

                ('links', ('array', {'type': 'inet:service:message:link'}), {
                    'doc': 'An array of links contained within the message.'}),

                ('attachments', ('array', {'type': 'inet:service:message:attachment'}), {
                    'doc': 'An array of files attached to the message.'}),

                ('hashtags', ('array', {'type': 'lang:hashtag', 'split': ','}), {
                    'doc': 'An array of hashtags mentioned within the message.'}),

                ('place', ('geo:place', {}), {
                    'doc': 'The place that the message was sent from.'}),

                ('place:name', ('meta:name', {}), {
                    'doc': 'The name of the place that the message was sent from.'}),

                ('client:software', ('it:software', {}), {
                    'doc': 'The client software version used to send the message.'}),

                ('client:software:name', ('meta:name', {}), {
                    'doc': 'The name of the client software used to send the message.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The raw file that the message was extracted from.'}),

                ('type', ('inet:service:message:type:taxonomy', {}), {
                    'doc': 'The type of message.'}),

                ('mentions', ('array', {'type': 'ndef',
                                        'typeopts': {'forms': ('inet:service:account', 'inet:service:role')}}), {
                    'doc': 'Contactable entities mentioned within the message.'}),
            )),

            ('inet:service:message:link', {}, (

                ('title', ('str', {}), {
                    'doc': 'The displayed hyperlink text if it was not the URL.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL contained within the message.'}),
            )),

            ('inet:service:message:attachment', {}, (

                ('name', ('file:path', {}), {
                    'doc': 'The name of the attached file.'}),

                ('text', ('str', {}), {
                    'doc': 'Any text associated with the file such as alt-text for images.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file which was attached to the message.'}),
            )),

            ('inet:service:emote', {}, (

                ('about', ('inet:service:object', {}), {
                    'doc': 'The node that the emote is about.'}),

                ('text', ('str', {}), {
                    'ex': ':partyparrot:',
                    'doc': 'The unicode or emote text of the reaction.'}),
            )),

            ('inet:service:channel', {}, (

                ('name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'The name of the channel.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period where the channel was available.'}),

                ('topic', ('base:name', {}), {
                    'doc': 'The visible topic of the channel.'}),

                ('profile', ('entity:contact', {}), {
                    'doc': 'Current detailed contact information for this channel.'}),
            )),

            ('inet:service:thread', {}, (

                ('title', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The title of the thread.'}),

                ('channel', ('inet:service:channel', {}), {
                    'doc': 'The channel that contains the thread.'}),

                ('message', ('inet:service:message', {}), {
                    'doc': 'The message which initiated the thread.'}),
            )),

            ('inet:service:member', {}, (

                ('of', ('inet:service:joinable', {}), {
                    'doc': 'The channel or group that the account was a member of.'}),

                ('account', ('inet:service:account', {}), {
                    'doc': 'The account that was a member of the channel or group.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period where the account was a member.'}),
            )),

            ('inet:service:resource:type:taxonomy', {}, {}),
            ('inet:service:resource', {}, (

                ('name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'The name of the service resource.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the service resource.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The primary URL where the resource is available from the service.'}),

                ('type', ('inet:service:resource:type:taxonomy', {}), {
                    'doc': 'The resource type. For example "rpc.endpoint".'}),
            )),

            ('inet:service:bucket', {}, (

                ('name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'The name of the service resource.'}),
            )),

            ('inet:service:bucket:item', {}, (

                ('bucket', ('inet:service:bucket', {}), {
                    'doc': 'The bucket which contains the item.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The bytes stored within the bucket item.'}),

                ('file:name', ('file:path', {}), {
                    'doc': 'The name of the file stored in the bucket item.'}),
            )),

            ('inet:service:access', {}, (

                ('action', ('inet:service:access:action:taxonomy', {}), {
                    'doc': 'The platform specific action which this access records.'}),

                ('resource', ('inet:service:resource', {}), {
                    'doc': 'The resource which the account attempted to access.'}),

                ('type', ('int', {'enums': svcaccesstypes}), {
                    'doc': 'The type of access requested.'}),
            )),

            ('inet:service:tenant', {}, ()),

            ('inet:service:subscription:level:taxonomy', {}, ()),

            ('inet:service:subscription', {}, (

                ('level', ('inet:service:subscription:level:taxonomy', {}), {
                    'doc': 'A platform specific subscription level.'}),

                ('pay:instrument', ('econ:pay:instrument', {}), {
                    'doc': 'The primary payment instrument used to pay for the subscription.'}),

                ('subscriber', ('inet:service:subscriber', {}), {
                    'doc': 'The subscriber who owns the subscription.'}),
            )),
        ),
        'hooks': {
            'post': {
                'forms': (
                    ('inet:fqdn', _onAddFqdn),
                ),
                'props': (
                    ('inet:fqdn:zone', _onSetFqdnZone),
                    ('inet:fqdn:iszone', _onSetFqdnIsZone),
                    ('inet:fqdn:issuffix', _onSetFqdnIsSuffix),
                )
            }
        },
    }),
)
