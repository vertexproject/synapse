import socket
import asyncio
import logging
import collections
import urllib.parse

import idna
import regex
import unicodedata

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.chop as s_chop
import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
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
        self.prototype = self.modl.type('str:lower')

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
                adds = (('inet:ip', ipv6, norminfo),)
                virts['ip'] = (ipv6, self.iptype.stortype)

                portstr = ''
                if port is not None:
                    port, norminfo = await self.porttype.norm(port)
                    virts['port'] = (port, self.porttype.stortype)
                    portstr = f':{port}'

                elif self.defport:
                    virts['port'] = (self.defport, self.porttype.stortype)
                    portstr = f':{self.defport}'

                if port and proto in self.noports:
                    mesg = f'Protocol {proto} does not allow specifying ports.'
                    raise s_exc.BadTypeValu(mesg=mesg, valu=orig)

                return f'{proto}://[{host}]{portstr}', {'adds': adds, 'subs': subs, 'virts': virts}

            mesg = f'Invalid IPv6 w/port ({orig})'
            raise s_exc.BadTypeValu(valu=orig, name=self.name, mesg=mesg)

        elif valu.count(':') >= 2:
            ipv6, norminfo = await self.iptype.norm(valu)
            host = self.iptype.repr(ipv6)
            adds = (('inet:ip', ipv6, norminfo),)
            virts['ip'] = (ipv6, self.iptype.stortype)

            if self.defport:
                virts['port'] = (self.defport, self.porttype.stortype)
                return f'{proto}://[{host}]:{self.defport}', {'adds': adds, 'subs': subs, 'virts': virts}

            return f'{proto}://[{host}]', {'adds': adds, 'subs': subs, 'virts': virts}

        # Otherwise treat as IPv4
        valu, port, pstr = await self._normPort(valu)
        if port:
            virts['port'] = (port, self.porttype.stortype)

        if port and proto in self.noports:
            mesg = f'Protocol {proto} does not allow specifying ports.'
            raise s_exc.BadTypeValu(mesg=mesg, valu=orig)

        ipv4, norminfo = await self.iptype.norm(valu)
        ipv4_repr = self.iptype.repr(ipv4)
        adds = (('inet:ip', ipv4, norminfo),)
        virts['ip'] = (ipv4, self.iptype.stortype)

        return f'{proto}://{ipv4_repr}{pstr}', {'adds': adds, 'subs': subs, 'virts': virts}

    async def _normPyTuple(self, valu, view=None):
        ipaddr, norminfo = await self.iptype.norm(valu)

        ip_repr = self.iptype.repr(ipaddr)
        proto = self.defproto
        adds = (('inet:ip', ipaddr, norminfo),)
        subs = {'proto': (self.prototype.typehash, proto, {})}
        virts = {'ip': (ipaddr, self.iptype.stortype)}

        portstr = ''
        if self.defport:
            virts['port'] = (self.defport, self.porttype.stortype)
            portstr = f':{self.defport}'

        if ipaddr[0] == 6:
            return f'{proto}://[{ip_repr}]{portstr}', {'adds': adds, 'subs': subs, 'virts': virts}
        else:
            return f'{proto}://{ip_repr}{portstr}', {'adds': adds, 'subs': subs, 'virts': virts}

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

        self.storlifts.pop('range=', None)

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

    def postFormInit(self, form):
        form.onAdd(self._onAddFqdn)
        form.props['issuffix'].onSet(self._onSetIsSuffix)
        form.props['iszone'].onSet(self._onSetIsZone)
        form.props['zone'].onSet(self._onSetZone)

    async def _onAddFqdn(self, node):

        domain = node.get('domain')

        async with node.view.getEditor() as editor:
            protonode = editor.loadNode(node)
            if domain is None:
                await protonode.set('iszone', False)
                await protonode.set('issuffix', True)
                return

            if protonode.get('issuffix') is None:
                await protonode.set('issuffix', False)

            parent = await node.view.getNodeByNdef(domain)
            if parent is None:
                parent = await editor.addNode('inet:fqdn', domain[1])

            if (pval := parent.get('issuffix')) is not None and pval[1]:
                await protonode.set('iszone', True)
                await protonode.set('zone', node.ndef[1])
                return

            await protonode.set('iszone', False)

            if (pval := parent.get('iszone')) is not None and pval[1]:
                await protonode.set('zone', domain[1])
                return

            zone = parent.get('zone')
            if zone is not None:
                await protonode.set('zone', zone[1])

    async def _onSetIsSuffix(self, node):

        fqdn = node.ndef[1]

        if (issuffix := node.get('issuffix')) is not None:
            issuffix = issuffix[1]

        async with node.view.getEditor() as editor:
            async for child in node.view.nodesByPropValu('inet:fqdn:domain', '=', fqdn):
                await asyncio.sleep(0)

                if (cval := child.get('iszone')) is not None:
                    cval = cval[1]

                if cval == issuffix:
                    continue

                protonode = editor.loadNode(child)
                await protonode.set('iszone', issuffix)

    async def _onSetIsZone(self, node):

        if (iszone := node.get('iszone')) is not None and iszone[1]:
            await node.set('zone', node.ndef[1])
            return

        domain = node.get('domain')
        if not domain:
            await node.pop('zone')
            return

        parent = await node.view.addNode('inet:fqdn', domain[1])

        zone = parent.get('zone')
        if zone is None:
            await node.pop('zone')
            return

        await node.set('zone', zone[1])

    async def _onSetZone(self, node):

        todo = collections.deque([node.ndef])
        zone = node.get('zone')

        async with node.view.getEditor() as editor:
            while todo:
                fqdn = todo.pop()
                async for child in node.view.nodesByPropValu('inet:fqdn:domain', 'ndef=', fqdn, norm=False):
                    await asyncio.sleep(0)

                    if ((cval := child.get('iszone')) is not None and cval[1]) or child.get('zone') == zone:
                        continue

                    protonode = editor.loadNode(child)
                    await protonode.set('zone', zone[1])

                    todo.append(child.ndef)

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
                host = f'[{self.iptype.repr(ipv6)}]'
                subs['ip'] = (self.iptype.typehash, ipv6, norminfo)

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
