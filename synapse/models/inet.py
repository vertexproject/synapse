import socket
import struct
import hashlib
import logging
import ipaddress
import email.utils

import regex

import synapse.common as s_common
import synapse.lib.tufo as s_tufo
import synapse.datamodel as s_datamodel
import synapse.lib.socket as s_socket
import synapse.lookup.iana as s_l_iana

from synapse.exc import BadTypeValu
from synapse.lib.types import DataType
from synapse.lib.module import CoreModule, modelrev

logger = logging.getLogger(__name__)

def castInetDeFang(valu):
    return valu.replace('[.]', '.')

def ipv4str(valu):
    byts = struct.pack('>I', valu)
    return socket.inet_ntoa(byts)

def ipv4int(valu):
    try:
        byts = socket.inet_aton(valu)
        return struct.unpack('>I', byts)[0]
    except socket.error as e:
        raise BadTypeValu(valu=valu, type='inet:ipv4', mesg=str(e))

masks = [(0xffffffff - (2 ** (32 - i) - 1)) for i in range(33)]
cidrmasks = [((0xffffffff - (2 ** (32 - i) - 1)), (2 ** (32 - i))) for i in range(33)]

def ipv4mask(ipv4, mask):
    return ipv4 & masks[mask]

def ipv4cidr(valu):
    _ipv4str, cidr = valu.split('/', 1)
    _ipv4addr = ipv4int(_ipv4str)
    mask = cidrmasks[int(cidr)]
    lowerbound = _ipv4addr & mask[0]
    return lowerbound, lowerbound + mask[1]

class IPv4Type(DataType):

    def norm(self, valu, oldval=None):
        if isinstance(valu, str):
            return self._norm_str(valu, oldval=oldval)

        if not isinstance(valu, int):
            self._raiseBadValu(valu)

        return valu & 0xffffffff, {}

    def _norm_str(self, valu, oldval=None):
        if valu.isdigit():
            return int(valu, 0) & 0xffffffff, {}

        valu = valu.replace('[.]', '.')
        return ipv4int(valu), {}

    def repr(self, valu):
        return ipv4str(valu)

fqdnre = regex.compile(r'^[\w._-]+$', regex.U)

class FqdnType(DataType):
    subprops = (
        ('sfx', {'ptype': 'bool'}),
        ('zone', {'ptype': 'bool'}),
        ('domain', {'ptype': 'inet:fqdn'}),
        ('host', {'ptype': 'str'}),
    )

    def norm(self, valu, oldval=None):

        valu = valu.replace('[.]', '.')
        if not fqdnre.match(valu):
            self._raiseBadValu(valu)

        try:
            valu = valu.encode('idna').decode('utf8').lower()
        except UnicodeError as e:
            self._raiseBadValu(valu)

        if not fqdnre.match(valu):
            self._raiseBadValu(valu)

        parts = valu.split('.', 1)
        subs = {'host': parts[0]}
        if len(parts) == 2:
            subs['domain'] = parts[1]
        else:
            subs['sfx'] = 1

        return valu, subs

    def repr(self, valu):
        return valu.encode('utf8').decode('idna')

class Rfc2822Addr(DataType):
    '''
    An RFC 2822 compatible email address parser
    '''
    def norm(self, valu, oldval=None):

        if not isinstance(valu, str):
            self._raiseBadValu(valu, mesg='requires a string')

        # remove quotes for normalized version
        valu = valu.replace('"', ' ').replace("'", ' ')
        valu = valu.strip().lower()
        valu = ' '.join(valu.split())

        subs = {}

        try:

            name, addr = email.utils.parseaddr(valu)

        except Exception as e: #pragma: no cover
            # not sure we can ever really trigger this with a string as input
            self._raiseBadValu(valu, mesg='email.utils.parsaddr failed: %s' % (e,))

        if name:
            subs['name'] = name

        try:

            mail, ssub = self.tlib.getTypeNorm('inet:email', addr)
            subs['email'] = mail

            if name:
                valu = '%s <%s>' % (name, mail)

            else:
                valu = mail

        except BadTypeValu as e:
            pass # it's all good, we just dont have a valid email addr

        return valu, subs

# RFC5952 compatible
def ipv6norm(text):
    '''
    Normalize an IPv6 address into RFC5952 canonical form.

    Example:

        text = ipv6norm(text)

    '''
    # This used to use socket.inet_pton for normalizing
    # ipv6 addresses. There's a bug in macOS where it
    # doesn't abbreviate the zeroes properly. See RFC
    # 5952 for IPv6 address text representation

    v6addr = ipaddress.IPv6Address(text)
    v4addr = v6addr.ipv4_mapped
    if v4addr is not None:
        return '::ffff:%s' % (v4addr)

    return v6addr.compressed

class IPv6Type(DataType):
    def repr(self, valu):
        return self.norm(valu)[0]

    def norm(self, valu, oldval=None):
        try:
            return ipv6norm(valu), {}
        except Exception as e:
            self._raiseBadValu(valu)

# class HostPort(DataType):

class Srv4Type(DataType):
    '''
    Base type for <ipv4>:<port> format.
    '''
    subprops = (
        ('port', {'ptype': 'inet:port'}),
        ('ipv4', {'ptype': 'inet:ipv4'}),
    )

    def repr(self, valu):
        addr = valu >> 16
        port = valu & 0xffff
        return '%s:%d' % (ipv4str(addr), port)

    def norm(self, valu, oldval=None):
        if isinstance(valu, str):
            return self._norm_str(valu, oldval=oldval)

        if valu < 0 or valu > 281474976710655:
            self._raiseBadValu(valu, mesg='Srv4Type integer is out of bounds')

        addr = valu >> 16
        port = valu & 0xffff
        return valu, {'port': port, 'ipv4': addr}

    def _norm_str(self, text, oldval=None):
        if ':' not in text:
            try:
                valu = int(text)
            except ValueError:
                self._raiseBadValu(text, mesg='Srv4Type string is not a integer or a colon delimited string.')
            return self.norm(valu)

        try:
            astr, pstr = text.split(':')
        except ValueError as e:
            self._raiseBadValu(text, mesg='Unable to split Srv4Type into two parts')

        addr = ipv4int(astr)
        port = int(pstr, 0)
        if port < 0 or port > 65535:
            self._raiseBadValu(text, port=port,
                               mesg='Srv4 Port number is out of bounds')
        return (addr << 16) | port, {'port': port, 'ipv4': addr}

srv6re = regex.compile('^\[([a-f0-9:]+)\]:(\d+)$')

class Srv6Type(DataType):
    '''
    Base type for [IPv6]:port format.
    '''
    subprops = (
        ('port', {'ptype': 'inet:port'}),
        ('ipv6', {'ptype': 'inet:ipv6'}),
    )

    def repr(self, valu):
        return self.norm(valu)[0]

    def norm(self, valu, oldval=None):

        valu = valu.lower()
        m = srv6re.match(valu)
        if m is None:
            self._raiseBadValu(valu, ex='[af::2]:80')

        host, portstr = m.groups()

        port = int(portstr, 0)
        if port > 0xffff or port < 0:
            self._raiseBadValu(valu, port=port)

        try:
            host = ipv6norm(host)
        except Exception as e:
            self._raiseBadValu(valu)

        valu = '[%s]:%d' % (host, port)
        return valu, {'ipv6': host, 'port': port}

class EmailType(DataType):
    subprops = (
        ('user', {'ptype': 'inet:user'}),
        ('fqdn', {'ptype': 'inet:fqdn'}),
    )

    def norm(self, valu, oldval=None):
        try:
            user, fqdn = valu.split('@', 1)
            user, _ = self.tlib.getTypeNorm('inet:user', user)
            fqdn, _ = self.tlib.getTypeNorm('inet:fqdn', fqdn)
            norm = ('%s@%s' % (user, fqdn)).lower()
        except ValueError as e:
            self._raiseBadValu(valu)
        return norm, {'user': user, 'fqdn': fqdn}

    def repr(self, valu):
        return valu

urlports = {
    'ftp': 21,
    'http': 80,
    'https': 443,
}

class UrlType(DataType):
    subprops = (
        ('proto', {'ptype': 'str'}),
        ('path', {'ptype': 'str'}),
        ('fqdn', {'ptype': 'inet:fqdn'}),
        ('ipv4', {'ptype': 'inet:ipv4'}),
        ('ipv6', {'ptype': 'inet:ipv6'}),
        ('port', {'ptype': 'inet:port'}),
        ('user', {'ptype': 'inet:user'}),
        ('passwd', {'ptype': 'inet:passwd'}),
    )

    def norm(self, valu, oldval=None):
        subs = {}
        respath = ''
        resauth = ''

        if valu.find('://') == -1:
            self._raiseBadValu(valu)

        proto, resloc = valu.split('://', 1)

        parts = resloc.split('/', 1)
        if len(parts) == 2:
            resloc, respath = parts

        if resloc.find('@') != -1:
            resauth, resloc = resloc.split('@', 1)

            user = resauth
            passwd = None

            if user.find(':') is not None:
                user, passwd = user.rsplit(':', 1)

            if user:
                subs['user'] = user

            if passwd:
                subs['passwd'] = passwd

        port = None
        proto = proto.lower()
        hostpart = resloc.lower().replace('[.]', '.')

        subs['proto'] = proto

        host = hostpart
        if hostpart.find(':') != -1:
            host, portstr = hostpart.rsplit(':', 1)
            port = self.tlib.getTypeParse('inet:port', portstr)[0]

        # use of exception handling logic here is fastest way to both
        # validate and convert the data...  normally wouldnt use....

        ipv4 = None
        try:

            ipv4 = ipv4int(host)
            subs['ipv4'] = ipv4

        except BadTypeValu as e:
            pass

        if ipv4 is None and fqdnre.match(host):
            subs['fqdn'] = host

        # try for a default iana protocol lookup
        if port is None:
            port = s_l_iana.services.get(proto)

        if port is not None:
            subs['port'] = port

        if resauth:
            hostpart = '%s@%s' % (resauth, hostpart)

        valu = '%s://%s/%s' % (proto, hostpart, respath)
        return valu, subs

    def repr(self, valu):
        return valu

class CidrType(DataType):
    def norm(self, valu, oldval=None):
        ipstr, maskstr = valu.split('/')

        mask = int(maskstr)
        ipv4 = ipv4int(ipstr)

        if mask > 32 or mask < 0:
            self._raiseBadValu(valu, mesg='Invalid CIDR Mask')

        ipv4 = ipv4mask(ipv4, mask)
        valu = '%s/%d' % (ipv4str(ipv4), mask)

        return valu, {'ipv4': ipv4, 'mask': mask}

    def repr(self, valu):
        return valu

class AddrType(DataType):

    def norm(self, valu, oldval=None):

        subs = {}
        if valu.find('.') != -1:
            valu = valu.split(':')[-1]
            ipv4, subs = self.tlib.getTypeNorm('inet:ipv4', valu)
            subs['ipv4'] = ipv4

            valu = '::ffff:' + valu

        addr, _ = self.tlib.getTypeNorm('inet:ipv6', valu)
        return addr, subs

class InetMod(CoreModule):

    def initCoreModule(self):
        # add an inet:defang cast to swap [.] to .
        self.core.addTypeCast('inet:defang', castInetDeFang)
        self.core.addTypeCast('inet:ipv4:cidr', ipv4cidr)
        self.onFormNode('inet:fqdn', self.onTufoFormFqdn)
        self.onFormNode('inet:passwd', self.onTufoFormPasswd)

        self.on('node:prop:set', self.onSetFqdnSfx, prop='inet:fqdn:sfx')

    def onTufoFormFqdn(self, form, valu, props, mesg):
        parts = valu.split('.', 1)
        if len(parts) > 1:
            props['inet:fqdn:domain'] = parts[1]
            pafo = self.core.formTufoByProp('inet:fqdn', parts[1])
            if pafo[1].get('inet:fqdn:sfx'):
                props['inet:fqdn:zone'] = 1

    def onTufoFormPasswd(self, form, valu, props, mesg):
        props['inet:passwd:md5'] = hashlib.md5(valu.encode('utf8')).hexdigest()
        props['inet:passwd:sha1'] = hashlib.sha1(valu.encode('utf8')).hexdigest()
        props['inet:passwd:sha256'] = hashlib.sha256(valu.encode('utf8')).hexdigest()

    def onSetFqdnSfx(self, mesg):
        sfx = mesg[1].get('newv')
        fqdn = mesg[1].get('valu')
        for tufo in self.core.getTufosByProp('inet:fqdn:domain', fqdn):
            self.core.setTufoProp(tufo, 'zone', sfx)

    @modelrev('inet', 201706201837)
    def _revModl201706201837(self):
        '''
        Add :port and :ipv4 to inet:tcp4 and inet:udp4 nodes.
        '''
        tick = s_common.now()

        forms = ('inet:tcp4', 'inet:udp4')
        for form in forms:
            adds = []
            portprop = '{}:port'.format(form)
            ipv4prop = '{}:ipv4'.format(form)

            rows = self.core.getRowsByProp(form)
            for i, p, v, _ in rows:
                norm, subs = s_datamodel.tlib.getTypeNorm(form, v)

                port = subs.get('port')
                if port:
                    adds.append((i, portprop, port, tick))

                ipv4 = subs.get('ipv4')
                if ipv4:
                    adds.append((i, ipv4prop, ipv4, tick))

            if adds:
                self.core.addRows(adds)

    @modelrev('inet', 201706121318)
    def _revModl201706121318(self):

        # account for the updated sub-property extraction for inet:url nodes
        adds = []
        rows = self.core.getRowsByProp('inet:url')

        for i, p, v, t in rows:
            norm, subs = s_datamodel.tlib.getTypeNorm('inet:url', v)

            fqdn = subs.get('fqdn')
            if fqdn is not None:
                adds.append((i, 'inet:url:fqdn', fqdn, t))

            ipv4 = subs.get('ipv4')
            if ipv4 is not None:
                adds.append((i, 'inet:url:ipv4', ipv4, t))

        if adds:
            self.core.addRows(adds)

    @modelrev('inet', 201708231646)
    def _revModl201708231646(self):
        pass # for legacy/backward compat

    @modelrev('inet', 201709181501)
    def _revModl201709181501(self):
        '''
        Replace inet:whois:rec:ns<int> rows with inet:whos:recns nodes.
        '''
        adds = []
        srcprops = ('inet:whois:rec:ns1', 'inet:whois:rec:ns2', 'inet:whois:rec:ns3', 'inet:whois:rec:ns4')
        delprops = set()

        tick = s_common.now()

        # We could use the joins API but we would have to still fold rows into tufos for the purpose of migration.
        nodes = self.core.getTufosByProp('inet:whois:rec')

        for node in nodes:
            rec = node[1].get('inet:whois:rec')
            for prop in srcprops:
                ns = node[1].get(prop)
                if not ns:
                    continue
                delprops.add(prop)
                iden = s_common.guid()
                pprop = s_common.guid([ns, rec])
                fqdn = node[1].get('inet:whois:rec:fqdn')
                asof = node[1].get('inet:whois:rec:asof')
                rows = [
                    (iden, 'tufo:form', 'inet:whois:recns', tick),
                    (iden, 'inet:whois:recns', pprop, tick),
                    (iden, 'inet:whois:recns:ns', ns, tick),
                    (iden, 'inet:whois:recns:rec', rec, tick),
                    (iden, 'inet:whois:recns:rec:fqdn', fqdn, tick),
                    (iden, 'inet:whois:recns:rec:asof', asof, tick),
                ]
                adds.extend(rows)

        if adds:
            self.core.addRows(adds)

        for prop in delprops:
            self.core.delRowsByProp(prop)

    @modelrev('inet', 201709271521)
    def _revModl201709271521(self):
        '''
        Rename inet:net* to inet:web*
        '''
        darks = []
        forms = [
            ('inet:netuser', 'inet:web:acct'),
            ('inet:netgroup', 'inet:web:group'),
            ('inet:netmemb', 'inet:web:memb'),
            ('inet:follows', 'inet:web:follows'),
            ('inet:netpost', 'inet:web:post'),
            ('inet:netfile', 'inet:web:file'),
            ('ps:hasnetuser', 'ps:haswebacct'),
            ('ou:hasnetuser', 'ou:haswebacct'),
        ]
        props = [
            ('inet:netuser:site', 'inet:web:acct:site'),
            ('inet:netuser:user', 'inet:web:acct:user'),
            ('inet:netuser:dob', 'inet:web:acct:dob'),
            ('inet:netuser:url', 'inet:web:acct:url'),
            ('inet:netuser:webpage', 'inet:web:acct:webpage'),
            ('inet:netuser:avatar', 'inet:web:acct:avatar'),
            ('inet:netuser:tagline', 'inet:web:acct:tagline'),
            ('inet:netuser:occupation', 'inet:web:acct:occupation'),
            ('inet:netuser:name', 'inet:web:acct:name'),
            ('inet:netuser:realname', 'inet:web:acct:realname'),
            ('inet:netuser:email', 'inet:web:acct:email'),
            ('inet:netuser:phone', 'inet:web:acct:phone'),
            ('inet:netuser:signup', 'inet:web:acct:signup'),
            ('inet:netuser:signup:ipv4', 'inet:web:acct:signup:ipv4'),
            ('inet:netuser:passwd', 'inet:web:acct:passwd'),
            ('inet:netuser:seen:min', 'inet:web:acct:seen:min'),
            ('inet:netuser:seen:max', 'inet:web:acct:seen:max'),

            ('inet:netgroup:site', 'inet:web:group:site'),
            ('inet:netgroup:name', 'inet:web:group:name'),
            ('inet:netgroup:desc', 'inet:web:group:desc'),
            ('inet:netgroup:url', 'inet:web:group:url'),
            ('inet:netgroup:webpage', 'inet:web:group:webpage'),
            ('inet:netgroup:avatar', 'inet:web:group:avatar'),

            ('inet:netmemb:user', 'inet:web:memb:acct'),  # renamed from user -> acct
            ('inet:netmemb:group', 'inet:web:memb:group'),
            ('inet:netmemb:title', 'inet:web:memb:title'),
            ('inet:netmemb:joined', 'inet:web:memb:joined'),
            ('inet:netmemb:seen:min', 'inet:web:memb:seen:min'),
            ('inet:netmemb:seen:max', 'inet:web:memb:seen:max'),

            ('inet:follows:follower', 'inet:web:follows:follower'),
            ('inet:follows:followee', 'inet:web:follows:followee'),
            ('inet:follows:seen:min', 'inet:web:follows:seen:min'),
            ('inet:follows:seen:max', 'inet:web:follows:seen:max'),

            ('inet:netpost:netuser', 'inet:web:post:acct'), # renamed from netuser -> acct
            ('inet:netpost:netuser:site', 'inet:web:post:acct:site'), # renamed from netuser -> acct
            ('inet:netpost:netuser:user', 'inet:web:post:acct:user'), # renamed from netuser -> acct
            ('inet:netpost:text', 'inet:web:post:text'),
            ('inet:netpost:replyto', 'inet:web:post:replyto'),
            ('inet:netpost:url', 'inet:web:post:url'),
            ('inet:netpost:file', 'inet:web:post:file'),
            ('inet:netpost:time', 'inet:web:post:time'),

            ('inet:netfile:file', 'inet:web:file:file'),
            ('inet:netfile:netuser', 'inet:web:file:acct'), # renamed from netuser -> acct
            ('inet:netfile:netuser:site', 'inet:web:file:acct:site'), # renamed from netuser -> acct
            ('inet:netfile:netuser:user', 'inet:web:file:acct:user'), # renamed from netuser -> acct
            ('inet:netfile:name', 'inet:web:file:name'),
            ('inet:netfile:posted', 'inet:web:file:posted'),
            ('inet:netfile:ipv4', 'inet:web:file:ipv4'),
            ('inet:netfile:ipv6', 'inet:web:file:ipv6'),
            ('inet:netfile:seen:min', 'inet:web:file:seen:min'),
            ('inet:netfile:seen:max', 'inet:web:file:seen:max'),

            ('inet:web:logon:netuser', 'inet:web:logon:acct'),
            ('inet:web:logon:netuser:site', 'inet:web:logon:acct:site'),
            ('inet:web:logon:netuser:user', 'inet:web:logon:acct:user'),

            ('ps:hasnetuser:netuser', 'ps:haswebacct:acct'),
            ('ps:hasnetuser:person', 'ps:haswebacct:person'),

            ('ou:hasnetuser:netuser', 'ou:haswebacct:acct'),
            ('ou:hasnetuser:org', 'ou:haswebacct:org'),

            # The following props are extra-model which may have been created if enforce=0 was set on a cortex.
            ('inet:netgroup:site:domain', 'inet:web:group:site:domain'),
            ('inet:netgroup:site:host', 'inet:web:group:site:host'),

            ('inet:netmemb:group:name', 'inet:web:memb:group:name'),
            ('inet:netmemb:group:site', 'inet:web:memb:group:site'),
            ('inet:netmemb:group:site:domain', 'inet:web:memb:group:site:domain'),
            ('inet:netmemb:group:site:host', 'inet:web:memb:group:site:hos'),
            ('inet:netmemb:user:site', 'inet:web:memb:acct:site'),
            ('inet:netmemb:user:site:domain', 'inet:web:memb:acct:site:domain'),
            ('inet:netmemb:user:site:host', 'inet:web:memb:acct:site:host'),
            ('inet:netmemb:user:user', 'inet:web:memb:acct:user'),

            ('inet:netpost:netuser:site:domain', 'inet:web:post:acct:site:domain'),
            ('inet:netpost:netuser:site:host', 'inet:web:post:acct:acctquit:site:host'),

            ('inet:netuser:site:domain', 'inet:acct:site:domain'),
            ('inet:netuser:site:host', 'inet:acct:site:host'),

            ('inet:web:logon:netuser:site:domain', 'inet:web:logon:acct:site:domain'),
            ('inet:web:logon:netuser:site:host', 'inet:web:logon:acct:site:host'),

            ('ou:hasnetuser:netuser:site', 'ou:haswebacct:acct:site'),
            ('ou:hasnetuser:netuser:site:domain', 'ou:haswebacct:acct:domain'),
            ('ou:hasnetuser:netuser:site:host', 'ou:haswebacct:acct:host'),
            ('ou:hasnetuser:netuser:user', 'ou:haswebacct:acct:user'),

            ('ps:hasnetuser:netuser:site', 'ps:haswebacct:acct:site'),
            ('ps:hasnetuser:netuser:site:domain', 'ps:haswebacct:acct:site:domain'),
            ('ps:hasnetuser:netuser:site:host', 'ps:haswebacct:acct:site:host'),
            ('ps:hasnetuser:netuser:user', 'ps:haswebacct:acct:user'),

        ]

        def _updateTagForm(old, new):

            # make a set of all of the syn:tagforms that should exist based on existing tagforms
            tag_valus = set()
            for tagform_tufo in self.core.getTufosByProp('syn:tagform:form', old):
                parts = tagform_tufo[1].get('syn:tagform:tag', '').split('.')
                for i in range(len(parts)):
                    tag_valus.add('.'.join(parts[0:i + 1]))

            for tag_valu in tag_valus:
                self.core.formTufoByProp('syn:tagform', (tag_valu, new))
                self.core.delTufoByProp('syn:tagform', (tag_valu, old))

            _updateTagDarks(tag_valus, old, new)

        def _updateTagDarks(existing_tagforms, old, new):

            # create a set of all of the tags on all of the nodes of a given form
            tags = set()
            for tufo in self.core.getTufosByProp(old):
                tags.update(s_tufo.tags(tufo))

            # for each tag, update the dark tag row and form a tagform if it is missing
            for tag in tags:

                if tag not in existing_tagforms:
                    self.core.formTufoByProp('syn:tagform', (tag, new))
                    existing_tagforms.add(tag)

                olddark = '_:*%s#%s' % (old, tag)
                newdark = '_:*%s#%s' % (new, tag)
                self.core.store.updateProperty(olddark, newdark)

        def _getXrefPropSrc():
            retval = []

            for prop in self.core.props:
                if isinstance(prop, str):
                    pdef = self.core.getPropDef(prop)
                    ptype = pdef[1]['ptype']
                    tdef = self.core.getTypeDef(ptype)
                    tsub = tdef[1].get('subof')
                    tsrc = tdef[1].get('source', '').split(',')[0]
                    if tsrc and tsub == 'xref':
                        retval.append((prop, prop + ':' + tsrc),)

            return retval

        def _updateXref(xref_props, oldform, newform):

            for xref_base_prop, xref_src_prop in xref_props:

                xref_prop = xref_base_prop + ':xref'
                xref_prop_prop = xref_base_prop + ':xref:prop'

                while True:
                    tufos = self.core.getTufosByProp(xref_prop_prop, oldform, limit=100000)
                    if not tufos:
                        break

                    for tufo in tufos:
                        i, p, v, t = self.core.getRowsByIdProp(tufo[0], xref_prop_prop)[0] # unavoidable until we have `node:created` prop
                        adds, dels = [], []

                        # modify :xref:prop
                        adds.append((i, p, newform, t),)
                        dels.append((i, p, v),)

                        # modify :xref
                        old_xref_valu = tufo[1][xref_prop]
                        new_xref_valu = tufo[1][xref_prop].replace(oldform, newform)
                        adds.append((i, xref_prop, new_xref_valu, t),)
                        dels.append((i, xref_prop, old_xref_valu),)

                        # modify the src prop. ex: `file:imgof:file`
                        src_valu = tufo[1][xref_src_prop]
                        new_formvalu = tufo[1][xref_prop].split('=', 1)[1]
                        xref_valu, _ = self.core.getTypeNorm(xref_base_prop, (src_valu, (newform, new_formvalu)))
                        adds.append((i, xref_base_prop, xref_valu, t),)
                        dels.append((i, xref_base_prop, tufo[1][xref_base_prop]),)

                        if adds:
                            self.core.addRows(adds)

                        for i, p, v in dels:
                            self.core.delRowsByIdProp(i, p, v)

        with self.core.getCoreXact() as xact:

            xref_propsrc = _getXrefPropSrc()

            for old, new in forms:
                self.core.store.updatePropertyValu('tufo:form', old, new)
                _updateTagForm(old, new)
                _updateXref(xref_propsrc, old, new)

            for old, new in forms + props:
                if old == new:
                    continue
                self.core.store.updateProperty(old, new)

    @modelrev('inet', 201710111553)
    def _revModl201710111553(self):

        adds, dels = [], []
        with self.core.getCoreXact() as xact:
            for i, p, v, t in self.core.getRowsByProp('inet:web:acct:occupation'):
                newv = v.lower()
                if newv != v:
                    adds.append((i, p, newv, t),)
                    dels.append((i, p, v),)

            if adds:
                self.core.addRows(adds)

            for i, p, v in dels:
                self.core.delRowsByIdProp(i, p, v)

    @modelrev('inet', 201802131725)
    def _revModel201802131725(self):
        # mark changed nodes with a dark row...
        dvalu = 'inet:201802131725'
        dprop = '_:dark:syn:modl:rev'

        with self.core.getCoreXact() as xact:
            rows = self.core.getRowsByProp('inet:web:group:name')
            darks = [(i[::-1], dprop, dvalu, t) for (i, p, v, t) in rows]
            self.core.store.updateProperty('inet:web:group:name',
                                           'inet:web:group:id')
            self.core.addRows(darks)
            # Make the inet:group nodes
            for (i, p, v, t) in rows:
                self.core.formTufoByProp('inet:group', v)

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
                    'doc': 'An IPv4 or IPv6 address',
                    'ex': '1.2.3.4'}),

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
            ),

            'forms': (

                # TODO: prep for atomic cut over?
#                ('inet:addr', {}, (
#                    ('ipv4', {'ptype': 'inet:ipv4',
#                        'doc': 'The IPv4 part of the address.'}),
#                    ('cc', {'ptype': 'pol:iso2', 'defval': '??',
#                        'doc': 'The country where the address is currently located.'}),
#                    ('type', {'ptype': 'str', 'defval': '??',
#                        'doc': 'The type of IP address (e.g., private, multicast, etc.).'}),
#                    ('asn', {'ptype': 'inet:asn', 'defval': -1,
#                        'doc': 'The ASN to which the address is currently assigned.'}),
#                )),

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
            ),
        }
        name = 'inet'
        return ((name, modl),)
