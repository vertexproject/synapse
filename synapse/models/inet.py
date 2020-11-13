import socket
import hashlib
import logging
import ipaddress
import email.utils

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.chop as s_chop
import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
import synapse.lib.scrape as s_scrape
import synapse.lib.module as s_module
import synapse.lookup.iana as s_l_iana

logger = logging.getLogger(__name__)
fqdnre = regex.compile(r'^[\w._-]+$', regex.U)
srv6re = regex.compile(r'^\[([a-f0-9\.:]+)\]:(\d+)$')

cidrmasks = [((0xffffffff - (2 ** (32 - i) - 1)), (2 ** (32 - i))) for i in range(33)]

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

    return 'unicast'

class Addr(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

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

        # no protos use case sensitivity yet...
        valu = valu.lower()

        proto = 'tcp'
        parts = valu.split('://', 1)
        if len(parts) == 2:
            proto, valu = parts

        if proto not in ('tcp', 'udp', 'icmp', 'host'):
            raise s_exc.BadTypeValu(valu=orig, name=self.name,
                                    mesg='inet:addr protocol must be in: tcp, udp, icmp, host')
        subs['proto'] = proto

        valu = valu.strip().strip('/')

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

                ipv6, v6info = self.modl.type('inet:ipv6').norm(ipv6)

                v6subs = v6info.get('subs')
                if v6subs is not None:
                    v6v4addr = v6subs.get('ipv4')
                    if v6v4addr is not None:
                        subs['ipv4'] = v6v4addr

                port = self.modl.type('inet:port').norm(port)[0]
                subs['ipv6'] = ipv6
                subs['port'] = port

                return f'{proto}://[{ipv6}]:{port}', {'subs': subs}

            mesg = f'Invalid IPv6 w/port ({orig})'
            raise s_exc.BadTypeValu(valu=orig, name=self.name, mesg=mesg)

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

class Cidr4(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):
        ip_str, mask_str = valu.split('/', 1)

        mask_int = int(mask_str)
        if mask_int > 32 or mask_int < 0:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Invalid CIDR Mask')

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

class Cidr6(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):
        try:
            network = ipaddress.IPv6Network(valu)
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=str(e)) from None

        norm = str(network)
        info = {
            'subs': {
                'broadcast': str(network.broadcast_address),
                'mask': network.prefixlen,
                'network': str(network.network_address),
            }
        }
        return norm, info

class Email(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        try:
            user, fqdn = valu.split('@', 1)

            fqdnnorm, fqdninfo = self.modl.type('inet:fqdn').norm(fqdn)
            usernorm, userinfo = self.modl.type('inet:user').norm(user)
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=str(e)) from None

        norm = f'{usernorm}@{fqdnnorm}'
        info = {
            'subs': {
                'fqdn': fqdnnorm,
                'user': usernorm,
            }
        }
        return norm, info

class Fqdn(s_types.Type):

    stortype = s_layer.STOR_TYPE_FQDN

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.storlifts.update({
            '=': self._storLiftEq,
        })

    def _storLiftEq(self, cmpr, valu):

        if type(valu) == str:

            if valu == '':
                mesg = 'Cannot generate fqdn index bytes for a empty string.'
                raise s_exc.BadLiftValu(valu=valu, name=self.name, mesg=mesg)

            if valu == '*':
                return (
                    ('=', '*', self.stortype),
                )

            if valu.startswith('*.'):
                norm, info = self.norm(valu[2:])
                return (
                    ('=', f'*.{norm}', self.stortype),
                )

            if valu.startswith('*'):
                norm, info = self.norm(valu[1:])
                return (
                    ('=', f'*{norm}', self.stortype),
                )

            if '*' in valu:
                mesg = 'Wild card may only appear at the beginning.'
                raise s_exc.BadLiftValu(valu=valu, name=self.name, mesg=mesg)

        return self._storLiftNorm(cmpr, valu)

    def _ctorCmprEq(self, text):
        if text == '':
            # Asking if a +inet:fqdn='' is a odd filter, but
            # the intuitive answer for that filter is to return False
            def cmpr(valu):
                return False
            return cmpr

        if text[0] == '*':
            cval = text[1:]
            def cmpr(valu):
                return valu.endswith(cval)
            return cmpr

        norm, info = self.norm(text)

        def cmpr(valu):
            return norm == valu
        return cmpr

    def _normPyStr(self, valu):

        valu = valu.replace('[.]', '.')
        valu = valu.replace('(.)', '.')

        # strip leading/trailing .
        valu = valu.strip().strip('.')

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

        try:
            valu = valu.encode('idna').decode('utf8').lower()
        except UnicodeError:
            mesg = 'Failed to encode/decode the value with idna/utf8.'
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=mesg) from None

        parts = valu.split('.', 1)
        subs = {'host': parts[0]}

        if len(parts) == 2:
            subs['domain'] = parts[1]
        else:
            subs['issuffix'] = 1

        return valu, {'subs': subs}

    def repr(self, valu):
        try:
            return valu.encode('utf8').decode('idna')
        except UnicodeError:
            return valu

import synapse.lib.layer as s_layer

class IPv4(s_types.Type):
    '''
    The base type for an IPv4 address.
    '''
    stortype = s_layer.STOR_TYPE_U32

    def postTypeInit(self):
        self.setCmprCtor('>=', self._ctorCmprGe)
        self.setCmprCtor('<=', self._ctorCmprLe)
        self.setCmprCtor('>', self._ctorCmprGt)
        self.setCmprCtor('<', self._ctorCmprLt)

        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

        self.storlifts.update({
            '=': self._storLiftEq,
            '<': self._storLiftNorm,
            '>': self._storLiftNorm,
            '<=': self._storLiftNorm,
            '>=': self._storLiftNorm,
        })

    def _ctorCmprEq(self, valu):

        if type(valu) == str:

            if valu.find('/') != -1:
                minv, maxv = self.getCidrRange(valu)

                def cmpr(norm):
                    return norm >= minv and norm < maxv
                return cmpr

            if valu.find('-') != -1:
                minv, maxv = self.getNetRange(valu)

                def cmpr(norm):
                    return norm >= minv and norm <= maxv
                return cmpr

        return s_types.Type._ctorCmprEq(self, valu)

    def getTypeVals(self, valu):

        if isinstance(valu, str):

            if valu.find('/') != -1:

                minv, maxv = self.getCidrRange(valu)
                while minv < maxv:
                    yield minv
                    minv += 1

                return

            if valu.find('-') != -1:

                minv, maxv = self.getNetRange(valu)

                while minv <= maxv:
                    yield minv
                    minv += 1

                return

        yield valu

    def _normPyInt(self, valu):
        norm = valu & 0xffffffff
        addr = ipaddress.IPv4Address(norm)
        subs = {'type': getAddrType(addr)}
        return norm, {'subs': subs}

    def _normPyStr(self, valu):

        valu = valu.replace('[.]', '.')
        valu = valu.replace('(.)', '.')

        valu = s_chop.printables(valu)

        try:
            byts = socket.inet_aton(valu)
        except OSError as e:
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg=str(e)) from None

        norm = int.from_bytes(byts, 'big')
        return self._normPyInt(norm)

    def repr(self, norm):
        byts = norm.to_bytes(4, 'big')
        return socket.inet_ntoa(byts)

    def getNetRange(self, text):
        minstr, maxstr = text.split('-')
        minv, info = self.norm(minstr)
        maxv, info = self.norm(maxstr)
        return minv, maxv

    def getCidrRange(self, text):
        addr, mask = text.split('/', 1)
        norm, info = self.norm(addr)

        mask = cidrmasks[int(mask)]

        minv = norm & mask[0]
        return minv, minv + mask[1]

    def _storLiftEq(self, cmpr, valu):

        if type(valu) == str:

            if valu.find('/') != -1:
                minv, maxv = self.getCidrRange(valu)
                maxv -= 1
                return (
                    ('range=', (minv, maxv), self.stortype),
                )

            if valu.find('-') != -1:
                minv, maxv = self.getNetRange(valu)
                return (
                    ('range=', (minv, maxv), self.stortype),
                )

        return self._storLiftNorm(cmpr, valu)

    def _ctorCmprGe(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu >= norm
        return cmpr

    def _ctorCmprLe(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu <= norm
        return cmpr

    def _ctorCmprGt(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu > norm
        return cmpr

    def _ctorCmprLt(self, text):
        norm, info = self.norm(text)

        def cmpr(valu):
            return valu < norm
        return cmpr

class IPv6(s_types.Type):

    stortype = s_layer.STOR_TYPE_IPV6

    def postTypeInit(self):
        self.setNormFunc(int, self._normPyStr)
        self.setNormFunc(str, self._normPyStr)

        self.storlifts.update({
            '=': self._storLiftEq,
        })

    def _normPyStr(self, valu):

        try:

            if type(valu) == str:
                valu = s_chop.printables(valu)
                if valu.find(':') == -1:
                    valu = '::ffff:' + valu

            v6 = ipaddress.IPv6Address(valu)
            v4 = v6.ipv4_mapped

            subs = {'type': getAddrType(v6)}

            if v4 is not None:
                v4_int = self.modl.type('inet:ipv4').norm(v4.compressed)[0]
                v4_str = self.modl.type('inet:ipv4').repr(v4_int)
                subs['ipv4'] = v4_int
                return f'::ffff:{v4_str}', {'subs': subs}

            return ipaddress.IPv6Address(valu).compressed, {'subs': subs}

        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name, mesg=str(e)) from None

    def getTypeVals(self, valu):

        if isinstance(valu, str):

            if valu.find('/') != -1:

                minv, maxv = self.getCidrRange(valu)
                while minv <= maxv:
                    yield minv.compressed
                    minv += 1

                return

            if valu.find('-') != -1:

                minv, maxv = self.getNetRange(valu)
                while minv <= maxv:
                    yield minv.compressed
                    minv += 1

                return

        yield valu

    def getCidrRange(self, text):
        netw = ipaddress.IPv6Network(text, strict=False)
        minv = netw[0]
        maxv = netw[-1]
        return minv, maxv

    def getNetRange(self, text):
        minv, maxv = text.split('-')
        return ipaddress.IPv6Address(minv), ipaddress.IPv6Address(maxv)

    def _ctorCmprEq(self, valu):

        if type(valu) == str:

            if valu.find('/') != -1:
                minv, maxv = self.getCidrRange(valu)

                def cmpr(norm):
                    norm = ipaddress.IPv6Address(norm)
                    return norm >= minv and norm <= maxv
                return cmpr

            if valu.find('-') != -1:
                minv, maxv = self.getNetRange(valu)

                def cmpr(norm):
                    norm = ipaddress.IPv6Address(norm)
                    return norm >= minv and norm <= maxv
                return cmpr

        return s_types.Type._ctorCmprEq(self, valu)

    def _storLiftEq(self, cmpr, valu):

        if type(valu) == str:

            if valu.find('/') != -1:
                minv, maxv = self.getCidrRange(valu)
                return (
                    ('range=', (minv.compressed, maxv.compressed), self.stortype),
                )

            if valu.find('-') != -1:
                minv, maxv = self.getNetRange(valu)
                return (
                    ('range=', (minv.compressed, maxv.compressed), self.stortype),
                )

        return self._storLiftNorm(cmpr, valu)

class IPv4Range(s_types.Range):

    def postTypeInit(self):
        self.opts['type'] = ('inet:ipv4', {})
        s_types.Range.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.cidrtype = self.modl.type('inet:cidr4')

    def _normPyStr(self, valu):
        if '-' in valu:
            return super()._normPyStr(valu)
        cidrnorm = self.cidrtype._normPyStr(valu)
        tupl = cidrnorm[1]['subs']['network'], cidrnorm[1]['subs']['broadcast']
        return self._normPyTuple(tupl)

class IPv6Range(s_types.Range):

    def postTypeInit(self):
        self.opts['type'] = ('inet:ipv6', {})
        s_types.Range.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.cidrtype = self.modl.type('inet:cidr6')

    def _normPyStr(self, valu):
        if '-' in valu:
            return super()._normPyStr(valu)
        cidrnorm = self.cidrtype._normPyStr(valu)
        tupl = cidrnorm[1]['subs']['network'], cidrnorm[1]['subs']['broadcast']
        return self._normPyTuple(tupl)

    def _normPyTuple(self, valu):
        if len(valu) != 2:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=f'Must be a 2-tuple of type {self.subtype.name}')

        minv = self.subtype.norm(valu[0])[0]
        maxv = self.subtype.norm(valu[1])[0]

        if ipaddress.ip_address(minv) > ipaddress.ip_address(maxv):
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='minval cannot be greater than maxval')

        return (minv, maxv), {'subs': {'min': minv, 'max': maxv}}

class Rfc2822Addr(s_types.Str):
    '''
    An RFC 2822 compatible email address parser
    '''

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        # remove quotes for normalized version
        valu = valu.replace('"', ' ').replace("'", ' ')
        valu = valu.strip().lower()
        valu = ' '.join(valu.split())

        try:
            name, addr = email.utils.parseaddr(valu)
        except Exception as e:  # pragma: no cover
            # not sure we can ever really trigger this with a string as input
            mesg = f'email.utils.parsaddr failed: {str(e)}'
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=mesg) from None

        subs = {}
        if name:
            subs['name'] = name

        try:
            data = self.modl.type('inet:email').norm(addr)
            if len(data) == 2:
                mail = data[0]

            subs['email'] = mail
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

    def _ctorCmprEq(self, text):
        if text == '':
            # Asking if a +inet:url='' is a odd filter, but
            # the intuitive answer for that filter is to return False
            def cmpr(valu):
                return False
            return cmpr

        norm, info = self.norm(text)

        def cmpr(valu):
            return norm == valu

        return cmpr

    def _normPyStr(self, valu):
        orig = valu
        subs = {}
        proto = ''
        authparts = None
        hostparts = ''
        pathpart = ''
        parampart = ''

        # Protocol
        try:
            proto, valu = valu.split('://', 1)
            proto = proto.lower()
            subs['proto'] = proto
        except Exception:
            raise s_exc.BadTypeValu(valu=orig, name=self.name,
                                    mesg='Invalid/Missing protocol') from None

        # Query params first
        queryrem = ''
        if '?' in valu:
            valu, queryrem = valu.split('?', 1)
            # TODO break out query params separately

        # Resource Path
        parts = valu.split('/', 1)
        if len(parts) == 2:
            valu, pathpart = parts
            pathpart = f'/{pathpart}'
        subs['path'] = pathpart

        if queryrem:
            parampart = f'?{queryrem}'
        subs['params'] = parampart

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

                host, ipv6_subs = self.modl.type('inet:ipv6').norm(valu)
                subs['ipv6'] = host

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
                ipv4 = self.modl.type('inet:ipv4').norm(part)[0]
                host = self.modl.type('inet:ipv4').repr(ipv4)
                subs['ipv4'] = ipv4
            except Exception:
                pass

            # FQDN
            if host is None:
                try:
                    host = self.modl.type('inet:fqdn').norm(part)[0]
                    subs['fqdn'] = host
                except Exception:
                    pass

        # Raise exception if there was no FQDN, IPv4, or IPv6
        if host is None:
            raise s_exc.BadTypeValu(valu=orig, name=self.name, mesg='No valid host')

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

        base = f'{proto}://{hostparts}{pathpart}'
        subs['base'] = base
        norm = f'{base}{parampart}'
        return norm, {'subs': subs}

class InetModule(s_module.CoreModule):

    async def initCoreModule(self):
        self.model.form('inet:fqdn').onAdd(self._onAddFqdn)
        self.model.prop('inet:fqdn:zone').onSet(self._onSetFqdnZone)
        self.model.prop('inet:fqdn:iszone').onSet(self._onSetFqdnIsZone)
        self.model.prop('inet:fqdn:issuffix').onSet(self._onSetFqdnIsSuffix)
        self.model.form('inet:passwd').onAdd(self._onAddPasswd)

        self.model.prop('inet:whois:rec:text').onSet(self._onSetWhoisText)

    async def _onSetWhoisText(self, node, oldv):

        text = node.get('text')
        fqdn = node.get('fqdn')
        asof = node.get('asof')

        for form, valu in s_scrape.scrape(text):

            if form == 'inet:email':

                whomail = await node.snap.addNode('inet:whois:email', (fqdn, valu))
                await whomail.set('.seen', asof)

    async def _onAddPasswd(self, node):

        byts = node.ndef[1].encode('utf8')
        await node.set('md5', hashlib.md5(byts).hexdigest())
        await node.set('sha1', hashlib.sha1(byts).hexdigest())
        await node.set('sha256', hashlib.sha256(byts).hexdigest())

    async def _onAddFqdn(self, node):

        fqdn = node.ndef[1]
        domain = node.get('domain')

        if domain is None:
            await node.set('iszone', False)
            await node.set('issuffix', True)
            return

        if node.get('issuffix') is None:
            await node.set('issuffix', False)

        # almost certainly in the cache anyway....
        parent = await node.snap.getNodeByNdef(('inet:fqdn', domain))

        if parent.get('issuffix'):
            await node.set('iszone', True)
            await node.set('zone', fqdn)
            return

        await node.set('iszone', False)

        if parent.get('iszone'):
            await node.set('zone', domain)
            return

        zone = parent.get('zone')
        if zone is not None:
            await node.set('zone', zone)

    async def _onSetFqdnIsSuffix(self, node, oldv):

        fqdn = node.ndef[1]

        issuffix = node.get('issuffix')
        async for child in node.snap.nodesByPropValu('inet:fqdn:domain', '=', fqdn):
            await child.set('iszone', issuffix)

    async def _onSetFqdnIsZone(self, node, oldv):

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

        parent = await node.snap.getNodeByNdef(('inet:fqdn', domain))

        zone = parent.get('zone')
        if zone is None:
            await node.pop('zone')
            return

        await node.set('zone', zone)

    async def _onSetFqdnZone(self, node, oldv):

        fqdn = node.ndef[1]
        zone = node.get('zone')

        async for child in node.snap.nodesByPropValu('inet:fqdn:domain', '=', fqdn):

            # if they are their own zone level, skip
            if child.get('iszone'):
                continue

            # the have the same zone we do
            await child.set('zone', zone)

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

                    ('inet:cidr6', 'synapse.models.inet.Cidr6', {}, {
                        'doc': 'An IPv6 address block in Classless Inter-Domain Routing (CIDR) notation.',
                        'ex': '2001:db8::/101'
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

                    ('inet:ipv4range', 'synapse.models.inet.IPv4Range', {}, {
                        'doc': 'An IPv4 address range.',
                        'ex': '1.2.3.4-1.2.3.8'
                    }),

                    ('inet:ipv6', 'synapse.models.inet.IPv6', {}, {
                        'doc': 'An IPv6 address.',
                        'ex': '2607:f8b0:4004:809::200e'
                    }),

                    ('inet:ipv6range', 'synapse.models.inet.IPv6Range', {}, {
                        'doc': 'An IPv6 address range.',
                        'ex': '(2607:f8b0:4004:809::200e, 2607:f8b0:4004:809::2011)'
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
                        'ex': '(54959, (1.2.3.4, 1.2.3.20))',
                    }),

                    ('inet:asnet6', ('comp', {'fields': (('asn', 'inet:asn'), ('net6', 'inet:net6'))}), {
                        'doc': 'An Autonomous System Number (ASN) and its associated IPv6 address range.',
                        'ex': '(54959, (ff::00, ff::02))',
                    }),

                    ('inet:client', ('inet:addr', {}), {
                        'doc': 'A network client address.'
                    }),

                    ('inet:download', ('guid', {}), {
                        'doc': 'An instance of a file downloaded from a server.',
                    }),

                    ('inet:flow', ('guid', {}), {
                        'doc': 'An individual network connection between a given source and destination.'
                    }),

                    ('inet:group', ('str', {}), {
                        'doc': 'A group name string.'
                    }),

                    ('inet:http:cookie', ('str', {}), {
                        'doc': 'An HTTP cookie string.'}),

                    ('inet:http:header:name', ('str', {'lower': True}), {}),

                    ('inet:http:header', ('comp', {'fields': (('name', 'inet:http:header:name'), ('value', 'str'))}), {
                        'doc': 'An HTTP protocol header key/value.'}),

                    ('inet:http:request:header', ('inet:http:header', {}), {
                        'doc': 'An HTTP request header.'}),

                    ('inet:http:response:header', ('inet:http:header', {}), {
                        'doc': 'An HTTP response header.'}),

                    ('inet:http:param', ('comp', {'fields': (('name', 'str'), ('value', 'str'))}), {
                        'doc': 'An HTTP request path query parameter.'}),

                    ('inet:http:request', ('guid', {}), {
                        'doc': 'A single HTTP request.'}),

                    ('inet:iface', ('guid', {}), {
                        'doc': 'A network interface with a set of associated protocol addresses.'
                    }),

                    ('inet:mac', ('str', {'lower': True, 'regex': '^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$'}), {
                        'doc': 'A 48-bit Media Access Control (MAC) address.',
                        'ex': 'aa:bb:cc:dd:ee:ff'
                    }),

                    ('inet:net4', ('inet:ipv4range', {}), {
                        'doc': 'An IPv4 address range.',
                        'ex': '(1.2.3.4, 1.2.3.20)'
                    }),

                    ('inet:net6', ('inet:ipv6range', {}), {
                        'doc': 'An IPv6 address range.',
                        'ex': "('ff::00', 'ff::30')"
                    }),

                    ('inet:passwd', ('str', {}), {
                        'doc': 'A password string.'
                    }),

                    ('inet:ssl:cert', ('comp', {'fields': (('server', 'inet:server'), ('file', 'file:bytes'))}), {
                        'doc': 'An SSL certificate file served by a server.',
                        'ex': '(1.2.3.4:443, guid:d41d8cd98f00b204e9800998ecf8427e)',
                    }),

                    ('inet:port', ('int', {'min': 0, 'max': 0xffff}), {
                        'doc': 'A network port.',
                        'ex': '80'
                    }),

                    ('inet:server', ('inet:addr', {}), {
                        'doc': 'A network server address.'
                    }),

                    ('inet:banner', ('comp', {'fields': (('server', 'inet:server'), ('text', 'it:dev:str'))}), {
                        'doc': 'A network protocol banner string presented by a server.',
                    }),

                    ('inet:servfile', ('comp', {'fields': (('server', 'inet:server'), ('file', 'file:bytes'))}), {
                        'doc': 'A file hosted on a server for access over a network protocol.',
                    }),

                    ('inet:urlfile', ('comp', {'fields': (('url', 'inet:url'), ('file', 'file:bytes'))}), {
                        'doc': 'A file hosted at a specific Universal Resource Locator (URL).'
                    }),

                    ('inet:urlredir', ('comp', {'fields': (('src', 'inet:url'), ('dst', 'inet:url'))}), {
                        'doc': 'A URL that redirects to another URL, such as via a URL shortening service '
                               'or an HTTP 302 response.',
                        'ex': '(http://foo.com/,http://bar.com/)'
                    }),

                    ('inet:url:mirror', ('comp', {'fields': (('of', 'inet:url'), ('at', 'inet:url'))}), {
                        'doc': 'A URL mirror site.',
                    }),

                    ('inet:user', ('str', {'lower': True}), {
                        'doc': 'A username string.'
                    }),

                    ('inet:search:query', ('guid', {}), {
                        'doc': 'An instance of a search query issued to a search engine.',
                    }),

                    ('inet:search:result', ('guid', {}), {
                        'doc': 'A single result from a web search.',
                    }),

                    ('inet:web:acct', ('comp', {'fields': (('site', 'inet:fqdn'), ('user', 'inet:user')), 'sepr': '/'}), {
                        'doc': 'An account with a given Internet-based site or service.',
                        'ex': 'twitter.com/invisig0th'
                    }),

                    ('inet:web:action', ('guid', {}), {
                        'doc': 'An instance of an account performing an action at an Internet-based site or service.'
                    }),

                    ('inet:web:chprofile', ('guid', {}), {
                        'doc': 'A change to a web account. Used to capture historical properties associated with '
                               ' an account, as opposed to current data in the inet:web:acct node.'
                    }),

                    ('inet:web:file', ('comp', {'fields': (('acct', 'inet:web:acct'), ('file', 'file:bytes'))}), {
                        'doc': 'A file posted by a web account.'
                    }),

                    ('inet:web:follows', ('comp', {'fields': (('follower', 'inet:web:acct'), ('followee', 'inet:web:acct'))}), {
                        'doc': 'A web account follows or is connected to another web account.'
                    }),

                    ('inet:web:group', ('comp', {'fields': (('site', 'inet:fqdn'), ('id', 'inet:group')), 'sepr': '/'}), {
                        'doc': 'A group hosted within or registered with a given Internet-based site or service.',
                        'ex': 'somesite.com/mycoolgroup'
                    }),

                    ('inet:web:logon', ('guid', {}), {
                        'doc': 'An instance of an account authenticating to an Internet-based site or service.'
                    }),

                    ('inet:web:memb', ('comp', {'fields': (('acct', 'inet:web:acct'), ('group', 'inet:web:group'))}), {
                        'doc': 'A web account that is a member of a web group.'
                    }),

                    ('inet:web:mesg', ('comp', {'fields': (('from', 'inet:web:acct'), ('to', 'inet:web:acct'), ('time', 'time'))}), {
                        'doc': 'A message sent from one web account to another web account.',
                        'ex': '((twitter.com, invisig0th), (twitter.com, gobbles), 20041012130220)'
                    }),

                    ('inet:web:post', ('guid', {}), {
                        'doc': 'A post made by a web account.'
                    }),
                    ('inet:web:hashtag', ('str', {'lower': True, 'regex': r'^#[\w]+$'}), {
                        'doc': 'A hashtag used in a web post.',
                    }),

                    ('inet:whois:contact', ('comp', {'fields': (('rec', 'inet:whois:rec'), ('type', ('str', {'lower': True})))}), {
                        'doc': 'An individual contact from a domain whois record.'
                    }),

                    ('inet:whois:rar', ('str', {'lower': True}), {
                        'doc': 'A domain registrar.',
                        'ex': 'godaddy, inc.'
                    }),

                    ('inet:whois:rec', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('asof', 'time'))}), {
                        'doc': 'A domain whois record.'
                    }),

                    ('inet:whois:recns', ('comp', {'fields': (('ns', 'inet:fqdn'), ('rec', 'inet:whois:rec'))}), {
                        'doc': 'A nameserver associated with a domain whois record.'
                    }),

                    ('inet:whois:reg', ('str', {'lower': True}), {
                        'doc': 'A domain registrant.',
                        'ex': 'woot hostmaster'
                    }),

                    ('inet:whois:email', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('email', 'inet:email'))}), {
                        'doc': 'An email address associated with an FQDN via whois registration text.',
                    }),

                    ('inet:whois:ipquery', ('guid', {}), {
                        'doc': 'Query details used to retrieve an IP record.'
                    }),

                    ('inet:whois:iprec', ('guid', {}), {
                        'doc': 'An IPv4/IPv6 block registration record.'
                    }),

                    ('inet:whois:ipcontact', ('guid', {}), {
                        'doc': 'An individual contact from an IP block record.'
                    }),

                    ('inet:whois:regid', ('str', {}), {
                        'doc': 'The registry unique identifier of the registration record.',
                        'ex': 'NET-10-0-0-0-1'
                    }),

                    ('inet:wifi:ap', ('comp', {'fields': (('ssid', 'inet:wifi:ssid'), ('bssid', 'inet:mac'))}), {
                        'doc': 'An SSID/MAC address combination for a wireless access point.'
                    }),

                    ('inet:wifi:ssid', ('str', {}), {
                        'doc': 'A WiFi service set identifier (SSID) name.',
                        'ex': 'The Vertex Project'
                    }),

                    ('inet:email:message', ('guid', {}), {
                        'doc': 'A unique email message.',
                    }),

                    ('inet:email:header:name', ('str', {'lower': True}), {
                        'doc': 'An email header name.',
                        'ex': 'subject',
                    }),
                    ('inet:email:header', ('comp', {'fields': (('name', 'inet:email:header:name'), ('value', 'str'))}), {
                        'doc': 'A unique email message header.',
                    }),
                    ('inet:email:message:attachment', ('comp', {'fields': (('message', 'inet:email:message'), ('file', 'file:bytes'))}), {
                        'doc': 'A file which was attached to an email message.',
                    }),
                    ('inet:email:message:link', ('comp', {'fields': (('message', 'inet:email:message'), ('url', 'inet:url'))}), {
                        'doc': 'A url/link embedded in an email message.',
                    }),
                ),

                'forms': (

                    ('inet:email:message', {}, (

                        ('to', ('inet:email', {}), {
                            'doc': 'The email address of the recipient.'
                        }),
                        ('from', ('inet:email', {}), {
                            'doc': 'The email address of the sender.'
                        }),
                        ('replyto', ('inet:email', {}), {
                            'doc': 'The email address from the reply-to header.'
                        }),
                        ('subject', ('str', {}), {
                            'doc': 'The email message subject line.'
                        }),
                        ('body', ('str', {}), {
                            'doc': 'The body of the email message.',
                            'disp': {'hint': 'text'},
                        }),
                        ('date', ('time', {}), {
                            'doc': 'The time the email message was received.'
                        }),
                        ('bytes', ('file:bytes', {}), {
                            'doc': 'The file bytes which contain the email message.'
                        }),
                        ('headers', ('array', {'type': 'inet:email:header'}), {
                            'doc': 'An array of email headers from the message.'
                        }),
                    )),

                    ('inet:email:header', {}, (
                        ('name', ('inet:email:header:name', {}), {
                            'ro': True,
                            'doc': 'The name of the email header.'}),
                        ('value', ('str', {}), {
                            'ro': True,
                            'doc': 'The value of the email header.'}),
                    )),

                    ('inet:email:message:attachment', {}, (
                        ('message', ('inet:email:message', {}), {
                            'ro': True,
                            'doc': 'The message containing the attached file.'}),
                        ('file', ('file:bytes', {}), {
                            'ro': True,
                            'doc': 'The attached file.'}),
                        ('name', ('file:base', {}), {
                            'doc': 'The name of the attached file.'}),
                    )),

                    ('inet:email:message:link', {}, (
                        ('message', ('inet:email:message', {}), {
                            'ro': True,
                            'doc': 'The message containing the embedded link.'}),
                        ('url', ('inet:url', {}), {
                            'ro': True,
                            'doc': 'The url contained within the email message.'}),
                    )),

                    ('inet:asn', {}, (
                        ('name', ('str', {'lower': True}), {
                            'doc': 'The name of the organization currently responsible for the ASN.'
                        }),
                        ('owner', ('ou:org', {}), {
                            'doc': 'The guid of the organization currently responsible for the ASN.'
                        }),
                    )),

                    ('inet:asnet4', {}, (
                        ('asn', ('inet:asn', {}), {
                            'ro': True,
                            'doc': 'The Autonomous System Number (ASN) of the netblock.'
                        }),
                        ('net4', ('inet:net4', {}), {
                            'ro': True,
                            'doc': 'The IPv4 address range assigned to the ASN.'
                        }),
                        ('net4:min', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The first IPv4 in the range assigned to the ASN.'
                        }),
                        ('net4:max', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The last IPv4 in the range assigned to the ASN.'
                        }),
                    )),

                    ('inet:asnet6', {}, (
                        ('asn', ('inet:asn', {}), {
                            'ro': True,
                            'doc': 'The Autonomous System Number (ASN) of the netblock.'
                        }),
                        ('net6', ('inet:net6', {}), {
                            'ro': True,
                            'doc': 'The IPv6 address range assigned to the ASN.'
                        }),
                        ('net6:min', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The first IPv6 in the range assigned to the ASN.'
                        }),
                        ('net6:max', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The last IPv6 in the range assigned to the ASN.'
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

                    ('inet:cidr6', {}, (
                        ('broadcast', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The broadcast IP address from the CIDR notation.'
                        }),
                        ('mask', ('int', {}), {
                            'ro': True,
                            'doc': 'The mask from the CIDR notation.'
                        }),
                        ('network', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The network IP address from the CIDR notation.'
                        }),
                    )),


                    ('inet:client', {}, (
                        ('proto', ('str', {'lower': True}), {
                            'ro': True,
                            'doc': 'The network protocol of the client.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The IPv4 of the client.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The IPv6 of the client.'
                        }),
                        ('host', ('it:host', {}), {
                            'ro': True,
                            'doc': 'The it:host node for the client.'
                        }),
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
                        ('server:host', ('it:host', {}), {
                            'doc': 'The it:host node for the server.'
                        }),
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
                        ('client:host', ('it:host', {}), {
                            'doc': 'The it:host node for the client.'
                        }),
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
                        ('dst', ('inet:server', {}), {
                            'doc': 'The destination address / port for a connection.'
                        }),
                        ('dst:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The destination IPv4 address.'
                        }),
                        ('dst:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The destination IPv6 address.'
                        }),
                        ('dst:port', ('inet:port', {}), {
                            'doc': 'The destination port.'
                        }),
                        ('dst:proto', ('str', {'lower': True}), {
                            'doc': 'The destination protocol.'
                        }),
                        ('dst:host', ('it:host', {}), {
                            'doc': 'The guid of the destination host.'
                        }),
                        ('dst:proc', ('it:exec:proc', {}), {
                            'doc': 'The guid of the destination process.'
                        }),
                        ('dst:exe', ('file:bytes', {}), {
                            'doc': 'The file (executable) that received the connection.'
                        }),
                        ('dst:txbytes', ('int', {}), {
                            'doc': 'The number of bytes sent by the destination host / process / file.'
                        }),
                        ('src', ('inet:client', {}), {
                            'doc': 'The source address / port for a connection.'
                        }),
                        ('src:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address.'
                        }),
                        ('src:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address.'
                        }),
                        ('src:port', ('inet:port', {}), {
                            'doc': 'The source port.'
                        }),
                        ('src:proto', ('str', {'lower': True}), {
                            'doc': 'The source protocol.'
                        }),
                        ('src:host', ('it:host', {}), {
                            'doc': 'The guid of the source host.'
                        }),
                        ('src:proc', ('it:exec:proc', {}), {
                            'doc': 'The guid of the source process.'
                        }),
                        ('src:exe', ('file:bytes', {}), {
                            'doc': 'The file (executable) that created the connection.'
                        }),
                        ('src:txbytes', ('int', {}), {
                            'doc': 'The number of bytes sent by the source host / process / file.'
                        }),
                    )),

                    ('inet:fqdn', {}, (
                        ('domain', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The parent domain for the FQDN.',
                        }),
                        ('host', ('str', {'lower': True}), {
                            'ro': True,
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

                    ('inet:group', {}, ()),

                    ('inet:http:request:header', {}, (

                        ('name', ('inet:http:header:name', {}), {'ro': True,
                            'doc': 'The name of the HTTP request header.'}),

                        ('value', ('str', {}), {'ro': True,
                            'doc': 'The value of the HTTP request header.'}),

                    )),

                    ('inet:http:response:header', {}, (

                        ('name', ('inet:http:header:name', {}), {'ro': True,
                            'doc': 'The name of the HTTP response header.'}),

                        ('value', ('str', {}), {'ro': True,
                            'doc': 'The value of the HTTP response header.'}),

                    )),

                    ('inet:http:param', {}, (

                        ('name', ('str', {'lower': True}), {'ro': True,
                            'doc': 'The name of the HTTP query parameter.'}),

                        ('value', ('str', {}), {'ro': True,
                            'doc': 'The value of the HTTP query parameter.'}),

                    )),

                    ('inet:http:cookie', {}, ()),

                    ('inet:http:request', {}, (

                        ('flow', ('inet:flow', {}), {}),

                        ('client', ('inet:client', {}), {}),
                        ('client:ipv4', ('inet:ipv4', {}), {}),
                        ('client:ipv6', ('inet:ipv6', {}), {}),

                        ('server', ('inet:server', {}), {}),
                        ('server:ipv4', ('inet:ipv4', {}), {}),
                        ('server:ipv6', ('inet:ipv6', {}), {}),
                        ('server:port', ('inet:port', {}), {}),

                        ('time', ('time', {}), {
                            'doc': 'The time that the HTTP request was sent.'}),

                        ('method', ('str', {}), {
                            'doc': 'The HTTP request method string.'}),

                        ('path', ('str', {}), {
                            'doc': 'The requested HTTP path (without query parameters).'}),

                        ('url', ('inet:url', {}), {
                            'doc': 'The reconstructed URL for the request if known.'}),

                        ('query', ('str', {}), {
                            'doc': 'The HTTP query string which optionally follows the path.'}),

                        ('headers', ('array', {'type': 'inet:http:request:header'}), {
                            'doc': 'An array of HTTP headers from the request.'}),

                        ('body', ('file:bytes', {}), {
                            'doc': 'The body of the HTTP request.'}),

                        ('response:time', ('time', {}), {}),
                        ('response:code', ('int', {}), {}),
                        ('response:reason', ('str', {}), {}),
                        ('response:headers', ('array', {'type': 'inet:http:response:header'}), {
                            'doc': 'An array of HTTP headers from the response.'}),
                        ('response:body', ('file:bytes', {}), {}),

                    )),

                    ('inet:iface', {}, (
                        ('host', ('it:host', {}), {
                            'doc': 'The guid of the host the interface is associated with.'
                        }),
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
                        ('adid', ('it:adid', {}), {
                            'doc': 'An advertising ID associated with the interface.',
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
                            'doc': 'The ASN to which the IPv4 address is currently assigned.'}),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The best known latitude/longitude for the node.'}),

                        ('loc', ('loc', {}), {
                            'doc': 'The geo-political location string for the IPv4.'}),

                        ('place', ('geo:place', {}), {
                            'doc': 'The geo:place associated with the latlong property.'}),

                        ('type', ('str', {}), {
                            'doc': 'The type of IP address (e.g., private, multicast, etc.).'}),

                        ('dns:rev', ('inet:fqdn', {}), {
                            'doc': 'The most current DNS reverse lookup for the IPv4.'}),
                    )),

                    ('inet:ipv6', {}, (

                        ('asn', ('inet:asn', {}), {
                            'doc': 'The ASN to which the IPv6 address is currently assigned.'}),

                        ('ipv4', ('inet:ipv4', {}), {
                            'doc': 'The mapped ipv4.'}),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The last known latitude/longitude for the node.'}),

                        ('place', ('geo:place', {}), {
                            'doc': 'The geo:place associated with the latlong property.'}),

                        ('dns:rev', ('inet:fqdn', {}), {
                            'doc': 'The most current DNS reverse lookup for the IPv6.'}),

                        ('loc', ('loc', {}), {
                            'doc': 'The geo-political location string for the IPv6.'}),
                    )),

                    ('inet:mac', {}, (
                        ('vendor', ('str', {}), {
                            'doc': 'The vendor associated with the 24-bit prefix of a MAC address.'
                        }),
                    )),

                    ('inet:passwd', {}, (
                        ('md5', ('hash:md5', {}), {
                            'ro': True,
                            'doc': 'The MD5 hash of the password.'
                        }),
                        ('sha1', ('hash:sha1', {}), {
                            'ro': True,
                            'doc': 'The SHA1 hash of the password.'
                        }),
                        ('sha256', ('hash:sha256', {}), {
                            'ro': True,
                            'doc': 'The SHA256 hash of the password.'
                        }),
                    )),

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
                            'ro': True,
                            'doc': 'The network protocol of the server.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The IPv4 of the server.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The IPv6 of the server.'
                        }),
                        ('host', ('it:host', {}), {
                            'ro': True,
                            'doc': 'The it:host node for the server.'
                        }),
                        ('port', ('inet:port', {}), {
                            'doc': 'The server tcp/udp port.'
                        }),
                    )),

                    ('inet:banner', {}, (

                        ('server', ('inet:server', {}), {'ro': True,
                            'doc': 'The server which presented the banner string.'}),

                        ('server:ipv4', ('inet:ipv4', {}), {'ro': True,
                            'doc': 'The IPv4 address of the server.'}),

                        ('server:ipv6', ('inet:ipv6', {}), {'ro': True,
                            'doc': 'The IPv6 address of the server.'}),

                        ('server:port', ('inet:port', {}), {'ro': True,
                            'doc': 'The network port.'}),

                        ('text', ('it:dev:str', {}), {'ro': True,
                            'doc': 'The banner text.',
                            'disp': {'hint': 'text'},
                        }),
                    )),

                    ('inet:servfile', {}, (
                        ('file', ('file:bytes', {}), {
                            'ro': True,
                            'doc': 'The file hosted by the server.'
                        }),
                        ('server', ('inet:server', {}), {
                            'ro': True,
                            'doc': 'The inet:addr of the server.'
                        }),
                        ('server:proto', ('str', {'lower': True}), {
                            'ro': True,
                            'doc': 'The network protocol of the server.'
                        }),
                        ('server:ipv4', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The IPv4 of the server.'
                        }),
                        ('server:ipv6', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The IPv6 of the server.'
                        }),
                        ('server:host', ('it:host', {}), {
                            'ro': True,
                            'doc': 'The it:host node for the server.'
                        }),
                        ('server:port', ('inet:port', {}), {
                            'doc': 'The server tcp/udp port.'
                        }),
                    )),

                    ('inet:ssl:cert', {}, (
                        ('file', ('file:bytes', {}), {
                            'ro': True,
                            'doc': 'The file bytes for the SSL certificate.'
                        }),
                        ('server', ('inet:server', {}), {
                            'ro': True,
                            'doc': 'The server that presented the SSL certificate.'
                        }),
                        ('server:ipv4', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The SSL server IPv4 address.'
                        }),
                        ('server:ipv6', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The SSL server IPv6 address.'
                        }),
                        ('server:port', ('inet:port', {}), {
                            'ro': True,
                            'doc': 'The SSL server listening port.'
                        }),
                    )),

                    ('inet:url', {}, (
                        ('fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The fqdn used in the URL (e.g., http://www.woot.com/page.html).'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'ro': True,
                            'doc': 'The IPv4 address used in the URL (e.g., http://1.2.3.4/page.html).'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'ro': True,
                            'doc': 'The IPv6 address used in the URL.'
                        }),
                        ('passwd', ('inet:passwd', {}), {
                            'ro': True,
                            'doc': 'The optional password used to access the URL.'
                        }),
                        ('base', ('str', {}), {
                            'ro': True,
                            'doc': 'The base scheme, user/pass, fqdn, port and path w/o parameters.'
                        }),
                        ('path', ('str', {}), {
                            'ro': True,
                            'doc': 'The path in the URL w/o parameters.'
                        }),
                        ('params', ('str', {}), {
                            'ro': True,
                            'doc': 'The URL parameter string.'
                        }),
                        ('port', ('inet:port', {}), {
                            'ro': True,
                            'doc': 'The port of the URL. URLs prefixed with http will be set to port 80 and '
                                   'URLs prefixed with https will be set to port 443 unless otherwise specified.'
                        }),
                        ('proto', ('str', {'lower': True}), {
                            'ro': True,
                            'doc': 'The protocol in the URL.'
                        }),
                        ('user', ('inet:user', {}), {
                            'ro': True,
                            'doc': 'The optional username used to access the URL.'
                        }),
                    )),

                    ('inet:urlfile', {}, (
                        ('url', ('inet:url', {}), {
                            'ro': True,
                            'doc': 'The URL where the file was hosted.'
                        }),
                        ('file', ('file:bytes', {}), {
                            'ro': True,
                            'doc': 'The file that was hosted at the URL.'
                        }),
                    )),

                    ('inet:urlredir', {}, (
                        ('src', ('inet:url', {}), {
                            'ro': True,
                            'doc': 'The original/source URL before redirect.'
                        }),
                        ('src:fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The FQDN within the src URL (if present).'
                        }),
                        ('dst', ('inet:url', {}), {
                            'ro': True,
                            'doc': 'The redirected/destination URL.'
                        }),
                        ('dst:fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The FQDN within the dst URL (if present).'
                        }),
                    )),

                    ('inet:url:mirror', {}, (
                        ('of', ('inet:url', {}), {
                            'ro': True,
                            'doc': 'The URL being mirrored.',
                        }),
                        ('at', ('inet:url', {}), {
                            'ro': True,
                            'doc': 'The URL of the mirror.',
                        }),
                    )),

                    ('inet:user', {}, ()),

                    ('inet:search:query', {}, (

                        ('text', ('str', {}), {
                            'doc': 'The search query text.',
                            'disp': {'hint': 'text'},
                        }),

                        ('time', ('time', {}), {
                            'doc': 'The time the web search was issued.'}),

                        ('engine', ('str', {'lower': True}), {
                            'ex': 'google',
                            'doc': 'A simple name for the search engine used.'}),
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
                        ('linked:accts', ('array', {'type': 'inet:web:acct', 'uniq': True, 'sorted': True}), {
                            'doc': 'Linked accounts specified in the account profile.',
                        }),
                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The last known latitude/longitude for the node.'
                        }),
                        ('place', ('geo:place', {}), {
                            'doc': 'The geo:place associated with the latlong property.'
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
                                   'the account identifier, e.g., a display name).',
                        }),
                        ('aliases', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                            'doc': 'An array of alternate names for the user.',
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
                        ('signup', ('time', {}), {
                            'doc': 'The date and time the account was registered.'
                        }),
                        ('signup:client', ('inet:client', {}), {
                            'doc': 'The client address used to sign up for the account.'
                        }),
                        ('signup:client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 address used to sign up for the account.'
                        }),
                        ('signup:client:ipv6', ('inet:ipv4', {}), {
                            'doc': 'The IPv6 address used to sign up for the account.'
                        }),
                        ('site', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('tagline', ('str', {}), {
                            'doc': 'The text of the account status or tag line.'
                        }),
                        ('url', ('inet:url', {}), {
                            'doc': 'The service provider URL where the account is hosted.'
                        }),
                        ('user', ('inet:user', {}), {
                            'ro': True,
                            'doc': 'The unique identifier for the account (may be different from the common '
                                   'name or display name).'
                        }),
                        ('webpage', ('inet:url', {}), {
                            'doc': 'A related URL specified by the account (e.g., a personal or company web '
                                   'page, blog, etc.).'
                        }),
                        ('recovery:email', ('inet:email', {}), {
                            'doc': 'An email address registered as a recovery email address for the account.',
                        }),
                    )),

                    ('inet:web:action', {}, (
                        ('act', ('str', {'lower': True, 'strip': True}), {
                            'doc': 'The action performed by the account.'
                        }),
                        ('acct', ('inet:web:acct', {}), {
                            'doc': 'The web account associated with the action.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('time', ('time', {}), {
                            'doc': 'The date and time the account performed the action.'
                        }),
                        ('client', ('inet:client', {}), {
                            'doc': 'The source client address of the action.'
                        }),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address of the action.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address of the action.'
                        }),
                    )),

                    ('inet:web:chprofile', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'doc': 'The web account associated with the change.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('client', ('inet:client', {}), {
                            'doc': 'The source address used to make the account change.'
                        }),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address used to make the account change.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address used to make the account change.'
                        }),
                        ('time', ('time', {}), {
                            'doc': 'The date and time when the account change occurred.'
                        }),
                        ('pv', ('nodeprop', {}), {
                            'doc': 'The prop=valu of the account property that was changed. Valu should be '
                                   'the old / original value, while the new value should be updated on the '
                                   'inet:web:acct form.'}),
                        ('pv:prop', ('str', {}), {
                            'doc': 'The property that was changed.'
                        }),
                    )),

                    ('inet:web:file', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'ro': True,
                            'doc': 'The account that owns or is associated with the file.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'ro': True,
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('file', ('file:bytes', {}), {
                            'ro': True,
                            'doc': 'The file owned by or associated with the account.'
                        }),
                        ('name', ('file:base', {}), {
                            'doc': 'The name of the file owned by or associated with the account.'
                        }),
                        ('posted', ('time', {}), {
                            'doc': 'The date and time the file was posted / submitted.'
                        }),
                        ('client', ('inet:client', {}), {
                            'doc': 'The source client address used to post or submit the file.'
                        }),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address used to post or submit the file.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address used to post or submit the file.'
                        }),
                    )),

                    ('inet:web:follows', {}, (
                        ('follower', ('inet:web:acct', {}), {
                            'ro': True,
                            'doc': 'The account following an account.'
                        }),
                        ('followee', ('inet:web:acct', {}), {
                            'ro': True,
                            'doc': 'The account followed by an account.'
                        }),
                    )),

                    ('inet:web:group', {}, (
                        ('site', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The site or service associated with the group.'
                        }),
                        ('id', ('inet:group', {}), {
                            'ro': True,
                            'doc': 'The site-specific unique identifier for the group (may be different from '
                                   'the common name or display name).'
                        }),
                        ('name', ('inet:group', {}), {
                            'doc': 'The localized name associated with the group (may be different from '
                                   'the account identifier, e.g., a display name).'
                        }),
                        ('aliases', ('array', {'type': 'inet:group', 'uniq': True, 'sorted': True}), {
                            'doc': 'An array of alternate names for the group.',
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
                        ('desc', ('str', {}), {
                            'doc': 'The text of the description of the group.'
                        }),
                        ('webpage', ('inet:url', {}), {
                            'doc': 'A related URL specified by the group (e.g., primary web site, etc.).'
                        }),
                        ('loc', ('str', {'lower': True}), {
                            'doc': 'A self-declared location for the group.'
                        }),
                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The last known latitude/longitude for the node.'
                        }),
                        ('place', ('geo:place', {}), {
                            'doc': 'The geo:place associated with the latlong property.'
                        }),
                        ('signup', ('time', {}), {
                            'doc': 'The date and time the group was created on the site.'
                        }),
                        ('signup:client', ('inet:client', {}), {
                            'doc': 'The client address used to create the group.'
                        }),
                        ('signup:client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 address used to create the group.'
                        }),
                        ('signup:client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The IPv6 address used to create the group.'
                        }),
                    )),

                    ('inet:web:logon', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'ro': True,
                            'doc': 'The web account associated with the logon event.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'ro': True,
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('time', ('time', {}), {
                            'ro': True,
                            'doc': 'The date and time the account logged into the service.'
                        }),
                        ('client', ('inet:client', {}), {
                            'doc': 'The source address of the logon.'
                        }),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address of the logon.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address of the logon.'
                        }),
                        ('logout', ('time', {}), {
                            'ro': True,
                            'doc': 'The date and time the account logged out of the service.'
                        })
                    )),

                    ('inet:web:memb', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'ro': True,
                            'doc': 'The account that is a member of the group.'
                        }),
                        ('group', ('inet:web:group', {}), {
                            'ro': True,
                            'doc': 'The group that the account is a member of.'
                        }),
                        ('title', ('str', {'lower': True}), {
                            'doc': 'The title or status of the member (e.g., admin, new member, etc.).'
                        }),
                        ('joined', ('time', {}), {
                            'doc': 'The date / time the account joined the group.'
                        }),
                    )),

                    ('inet:web:mesg', {}, (
                        ('from', ('inet:web:acct', {}), {
                            'ro': True,
                            'doc': 'The web account that sent the message.'
                        }),
                        ('to', ('inet:web:acct', {}), {
                            'ro': True,
                            'doc': 'The web account that received the message.'
                        }),
                        ('client', ('inet:client', {}), {
                            'doc': 'The source address of the message.'
                        }),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address of the message.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address of the message.'
                        }),
                        ('time', ('time', {}), {
                            'ro': True,
                            'doc': 'The date and time at which the message was sent.'
                        }),
                        ('url', ('inet:url', {}), {
                            'doc': 'The URL where the message is posted / visible.'
                        }),
                        ('text', ('str', {}), {
                            'doc': 'The text of the message.',
                            'disp': {'hint': 'text'},
                        }),
                        ('file', ('file:bytes', {}), {
                            'doc': 'The file attached to or sent with the message.'
                        }),
                    )),

                    ('inet:web:post', {}, (
                        ('acct', ('inet:web:acct', {}), {
                            'doc': 'The web account that made the post.'
                        }),
                        ('acct:site', ('inet:fqdn', {}), {
                            'doc': 'The site or service associated with the account.'
                        }),
                        ('client', ('inet:client', {}), {
                            'doc': 'The source address of the post.'
                        }),
                        ('client:ipv4', ('inet:ipv4', {}), {
                            'doc': 'The source IPv4 address of the post.'
                        }),
                        ('client:ipv6', ('inet:ipv6', {}), {
                            'doc': 'The source IPv6 address of the post.'
                        }),
                        ('acct:user', ('inet:user', {}), {
                            'doc': 'The unique identifier for the account.'
                        }),
                        ('text', ('str', {}), {
                            'doc': 'The text of the post.',
                            'disp': {'hint': 'text'},
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
                        ('hashtags', ('array', {'type': 'inet:web:hashtag', 'uniq': True, 'sorted': True, 'split': ','}), {
                            'doc': 'Hashtags mentioned within the post.',
                        }),
                        ('mentions:users', ('array', {'type': 'inet:web:acct', 'uniq': True, 'sorted': True, 'split': ','}), {
                            'doc': 'Accounts mentioned within the post.',
                        }),
                        ('mentions:groups', ('array', {'type': 'inet:web:group', 'uniq': True, 'sorted': True, 'split': ','}), {
                            'doc': 'Groups mentioned within the post.',
                        }),
                        # location protocol...
                        ('loc', ('loc', {}), {
                            'doc': 'The location that the post was reportedly sent from.',
                        }),
                        ('place', ('geo:place', {}), {
                            'doc': 'The place that the post was reportedly sent from.',
                        }),
                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The place that the post was reportedly sent from.',
                        }),

                    )),

                    ('inet:web:hashtag', {}, ()),

                    ('inet:whois:contact', {}, (
                        ('rec', ('inet:whois:rec', {}), {
                            'ro': True,
                            'doc': 'The whois record containing the contact data.'
                        }),
                        ('rec:fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The domain associated with the whois record.'
                        }),
                        ('rec:asof', ('time', {}), {
                            'ro': True,
                            'doc': 'The date of the whois record.'
                        }),
                        ('type', ('str', {'lower': True}), {
                            'doc': 'The contact type (e.g., registrar, registrant, admin, billing, tech, etc.).'
                        }),
                        ('id', ('str', {'lower': True}), {
                            'doc': 'The ID associated with the contact.'
                        }),
                        ('name', ('str', {'lower': True}), {
                            'doc': 'The name of the contact.'
                        }),
                        ('email', ('inet:email', {}), {
                            'doc': 'The email address of the contact.'
                        }),
                        ('orgname', ('ou:name', {}), {
                            'doc': 'The name of the contact organization.'
                        }),
                        ('address', ('str', {'lower': True}), {
                            'doc': 'The content of the street address field(s) of the contact.'
                        }),
                        ('city', ('str', {'lower': True}), {
                            'doc': 'The content of the city field of the contact.'
                        }),
                        ('state', ('str', {'lower': True}), {
                            'doc': 'The content of the state field of the contact.'
                        }),
                        ('country', ('str', {'lower': True}), {
                            'doc': 'The two-letter country code of the contact.'
                        }),
                        ('phone', ('tel:phone', {}), {
                            'doc': 'The content of the phone field of the contact.'
                        }),
                        ('fax', ('tel:phone', {}), {
                            'doc': 'The content of the fax field of the contact.'
                        }),
                        ('url', ('inet:url', {}), {
                            'doc': 'The URL specified for the contact.'
                        }),
                        ('whois:fqdn', ('inet:fqdn', {}), {
                            'doc': 'The whois server FQDN for the given contact (most likely a registrar).'
                        }),
                    )),

                    ('inet:whois:rar', {}, ()),

                    ('inet:whois:rec', {}, (
                        ('fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The domain associated with the whois record.'
                        }),
                        ('asof', ('time', {}), {
                            'ro': True,
                            'doc': 'The date of the whois record.'
                        }),
                        ('text', ('str', {'lower': True}), {
                            'doc': 'The full text of the whois record.',
                            'disp': {'hint': 'text'},
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
                            'doc': 'The registrar name from the whois record.'
                        }),
                        ('registrant', ('inet:whois:reg', {}), {
                            'doc': 'The registrant name from the whois record.'
                        }),
                    )),

                    ('inet:whois:recns', {}, (
                        ('ns', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'A nameserver for a domain as listed in the domain whois record.'
                        }),
                        ('rec', ('inet:whois:rec', {}), {
                            'ro': True,
                            'doc': 'The whois record containing the nameserver data.'
                        }),
                        ('rec:fqdn', ('inet:fqdn', {}), {
                            'ro': True,
                            'doc': 'The domain associated with the whois record.'
                        }),
                        ('rec:asof', ('time', {}), {
                            'ro': True,
                            'doc': 'The date of the whois record.'
                        }),
                    )),

                    ('inet:whois:reg', {}, ()),

                    ('inet:whois:email', {}, (
                        ('fqdn', ('inet:fqdn', {}), {'ro': True,
                            'doc': 'The domain with a whois record containing the email address.',
                        }),
                        ('email', ('inet:email', {}), {'ro': True,
                            'doc': 'The email address associated with the domain whois record.',
                        }),
                    )),

                    ('inet:whois:ipquery', {}, (
                        ('time', ('time', {}), {
                            'doc': 'The time the request was made.'
                        }),
                        ('url', ('inet:url', {}), {
                            'doc': 'The query URL when using the HTTP RDAP Protocol.'
                        }),
                        ('fqdn', ('inet:fqdn', {}), {
                            'doc': 'The FQDN of the host server when using the legacy WHOIS Protocol.'
                        }),
                        ('ipv4', ('inet:ipv4', {}), {
                            'doc': 'The IPv4 address queried.'
                        }),
                        ('ipv6', ('inet:ipv6', {}), {
                            'doc': 'The IPv6 address queried.'
                        }),
                        ('success', ('bool', {}), {
                            'doc': 'Whether the host returned a valid response for the query.'
                        }),
                        ('rec', ('inet:whois:iprec', {}), {
                            'doc': 'The resulting record from the query.'
                        }),
                    )),

                    ('inet:whois:iprec', {}, (
                        ('net4', ('inet:net4', {}), {
                            'doc': 'The IPv4 address range assigned.'
                        }),
                        ('net4:min', ('inet:ipv4', {}), {
                            'doc': 'The first IPv4 in the range assigned.'
                        }),
                        ('net4:max', ('inet:ipv4', {}), {
                            'doc': 'The last IPv4 in the range assigned.'
                        }),
                        ('net6', ('inet:net6', {}), {
                            'doc': 'The IPv6 address range assigned.'
                        }),
                        ('net6:min', ('inet:ipv6', {}), {
                            'doc': 'The first IPv6 in the range assigned.'
                        }),
                        ('net6:max', ('inet:ipv6', {}), {
                            'doc': 'The last IPv6 in the range assigned.'
                        }),
                        ('asof', ('time', {}), {
                            'doc': 'The date of the record.'
                        }),
                        ('created', ('time', {}), {
                            'doc': 'The "created" time from the record.'
                        }),
                        ('updated', ('time', {}), {
                            'doc': 'The "last updated" time from the record.'
                        }),
                        ('text', ('str', {'lower': True}), {
                            'doc': 'The full text of the record.',
                            'disp': {'hint': 'text'},
                        }),
                        ('asn', ('inet:asn', {}), {
                            'doc': 'The associated Autonomous System Number (ASN).'
                        }),
                        ('id', ('inet:whois:regid', {}), {
                            'doc': 'The registry unique identifier (e.g. NET-74-0-0-0-1).'
                        }),
                        ('name', ('str', {}), {
                            'doc': 'The name assigned to the network by the registrant.'
                        }),
                        ('parentid', ('inet:whois:regid', {}), {
                            'doc': 'The registry unique identifier of the parent whois record (e.g. NET-74-0-0-0-0).'
                        }),
                        ('registrant', ('inet:whois:ipcontact', {}), {
                            'doc': 'The registrant contact from the record.'
                        }),
                        ('contacts', ('array', {'type': 'inet:whois:ipcontact'}), {
                            'doc': 'Additional contacts from the record.',
                        }),
                        ('country', ('str', {'lower': True, 'regex': '^[a-z]{2}$'}), {
                            'doc': 'The two-letter ISO 3166 country code.'
                        }),
                        ('status', ('str', {'lower': True}), {
                            'doc': 'The state of the registered network.'
                        }),
                        ('type', ('str', {'lower': True}), {
                            'doc': 'The classification of the registered network (e.g. direct allocation).'
                        }),
                        ('links', ('array', {'type': 'inet:url'}), {
                            'doc': 'URLs provided with the record.',
                        }),
                    )),

                    ('inet:whois:ipcontact', {}, (
                        ('contact', ('ps:contact', {}), {
                            'doc': 'Contact information associated with a registration.'
                        }),
                        ('asof', ('time', {}), {
                            'doc': 'The date of the record.'
                        }),
                        ('created', ('time', {}), {
                            'doc': 'The "created" time from the record.'
                        }),
                        ('updated', ('time', {}), {
                            'doc': 'The "last updated" time from the record.'
                        }),
                        ('role', ('str', {'lower': True}), {
                            'doc': 'The primary role for the contact.'
                        }),
                        ('roles', ('array', {'type': 'str'}), {
                            'doc': 'Additional roles assigned to the contact.',
                        }),
                        ('asn', ('inet:asn', {}), {
                            'doc': 'The associated Autonomous System Number (ASN).'
                        }),
                        ('id', ('inet:whois:regid', {}), {
                            'doc': 'The registry unique identifier (e.g. NET-74-0-0-0-1).'
                        }),
                        ('links', ('array', {'type': 'inet:url'}), {
                            'doc': 'URLs provided with the record.',
                        }),
                        ('status', ('str', {'lower': True}), {
                            'doc': 'The state of the registered contact (e.g. validated, obscured).'
                        }),
                        ('contacts', ('array', {'type': 'inet:whois:ipcontact'}), {
                            'doc': 'Additional contacts referenced by this contact.',
                        }),
                    )),

                    ('inet:whois:regid', {}, ()),

                    ('inet:wifi:ap', {}, (

                        ('ssid', ('inet:wifi:ssid', {}), {
                            'doc': 'The SSID for the wireless access point.'}),

                        ('bssid', ('inet:mac', {}), {
                            'doc': 'The MAC address for the wireless access point.'}),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The best known latitude/longitude for the wireless access point.'}),

                        ('accuracy', ('geo:dist', {}), {
                            'doc': 'The reported accuracy of the latlong telemetry reading.',
                        }),
                        ('channel', ('int', {}), {
                            'doc': 'The WIFI channel that the AP was last observed operating on.',
                        }),
                        ('encryption', ('str', {'lower': True, 'strip': True}), {
                            'doc': 'The type of encryption used by the WIFI AP such as "wpa2".',
                        }),
                        ('place', ('geo:place', {}), {
                            'doc': 'The geo:place associated with the latlong property.'}),

                        ('loc', ('loc', {}), {
                            'doc': 'The geo-political location string for the wireless access point.'}),

                        ('org', ('ou:org', {}), {
                            'doc': 'The organization that owns/operates the access point.'}),
                    )),

                    ('inet:wifi:ssid', {}, ()),

                ),
            }),
        )
