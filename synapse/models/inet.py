import re
import socket
import struct
import hashlib
import logging

import synapse.common as s_common
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

fqdnre = re.compile(r'^[\w._-]+$', re.U)

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

# RFC5952 compatible
def ipv6norm(text):
    '''
    Normalize an IPv6 address into RFC5952 canonical form.

    Example:

        text = ipv6norm(text)

    '''
    # use inet_ntop / inet_pton from synapse.lib.socket for portability
    return s_socket.inet_ntop(socket.AF_INET6, s_socket.inet_pton(socket.AF_INET6, text))

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

srv6re = re.compile('^\[([a-f0-9:]+)\]:(\d+)$')

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
        # TODO: move the inner migration functions into the core

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

            darks = []

            for i, _, _, _ in self.core.getRowsByProp('syn:tagform:form', old):
                for _, _, tag, _ in self.core.getRowsByIdProp(i, 'syn:tagform:tag'):
                    oldark = '_:*%s#%s' % (old, tag)
                    newdark = '_:*%s#%s' % (new, tag)
                    darks.append((oldark, newdark),)

            for olddark, newdark in darks:
                self.core.store.updateProperty(olddark, newdark)

            self.core.store.updatePropertyValu('syn:tagform:form', old, new)

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
                    tufos = self.core.getTufosByProp(xref_prop_prop, oldform, limit=1000)
                    if not tufos:
                        break

                    for tufo in tufos:
                        i, p, v, t = self.core.getRowsByIdProp(tufo[0], xref_prop_prop)[0] # unavoidable until we have `tufo:formed` prop
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
            for old, new in forms + props:
                if old == new:
                    continue

                self.core.store.updateProperty(old, new)
                self.core.store.updatePropertyValu('tufo:form', old, new)
                _updateTagForm(old, new)
                _updateXref(xref_propsrc, old, new)

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('inet:url', {'ctor': 'synapse.models.inet.UrlType', 'doc': 'A Universal Resource Locator (URL)'}),
                ('inet:ipv4', {'ctor': 'synapse.models.inet.IPv4Type', 'doc': 'An IPv4 Address', 'ex': '1.2.3.4'}),
                ('inet:ipv6', {'ctor': 'synapse.models.inet.IPv6Type', 'doc': 'An IPv6 Address',
                               'ex': '2607:f8b0:4004:809::200e'}),
                ('inet:srv4', {'ctor': 'synapse.models.inet.Srv4Type', 'doc': 'An IPv4 Address and Port',
                               'ex': '1.2.3.4:80'}),
                ('inet:srv6', {'ctor': 'synapse.models.inet.Srv6Type', 'doc': 'An IPv6 Address and Port',
                               'ex': '[2607:f8b0:4004:809::200e]:80'}),
                ('inet:email',
                 {'ctor': 'synapse.models.inet.EmailType', 'doc': 'An e-mail address', 'ex': 'visi@vertex.link'}),
                ('inet:fqdn', {'ctor': 'synapse.models.inet.FqdnType', 'ex': 'vertex.link',
                               'doc': 'A Fully Qualified Domain Name (FQDN)'}),

                (
                    'inet:cidr4',
                    {'ctor': 'synapse.models.inet.CidrType', 'doc': 'An IPv4 CIDR type', 'ex': '1.2.3.0/24'}),

                ('inet:urlfile', {'subof': 'comp', 'fields': 'url=inet:url,file=file:bytes',
                                  'doc': 'A File at a Universal Resource Locator (URL)'}),
                ('inet:net4',
                 {'subof': 'sepr', 'sep': '-', 'fields': 'min,inet:ipv4|max,inet:ipv4', 'doc': 'An IPv4 address range',
                  'ex': '1.2.3.4-1.2.3.20'}),
                ('inet:net6',
                 {'subof': 'sepr', 'sep': '-', 'fields': 'min,inet:ipv6|max,inet:ipv6', 'doc': 'An IPv6 address range',
                  'ex': 'ff::00-ff::30'}),

                ('inet:asnet4', {'subof': 'sepr', 'sep': '/', 'fields': 'asn,inet:asn|net4,inet:net4',
                                 'doc': 'An IPv4 address range assigned to an autonomous system',
                                 'ex': '54959/1.2.3.4-1.2.3.20'}),

                ('inet:asn', {'subof': 'int', 'doc': 'An Autonomous System Number (ASN)'}),
                ('inet:user', {'subof': 'str:lwr', 'doc': 'A username string'}),
                ('inet:passwd', {'subof': 'str', 'doc': 'A password string'}),

                ('inet:tcp4', {'subof': 'inet:srv4', 'doc': 'A TCP server listening on IPv4:port'}),
                ('inet:udp4', {'subof': 'inet:srv4', 'doc': 'A UDP server listening on IPv4:port'}),
                ('inet:tcp6', {'subof': 'inet:srv6', 'doc': 'A TCP server listening on IPv6:port'}),
                ('inet:udp6', {'subof': 'inet:srv6', 'doc': 'A UDP server listening on IPv6:port'}),

                ('inet:flow', {'subof': 'guid', 'doc': 'An individual network connection'}),

                ('inet:port', {'subof': 'int', 'min': 0, 'max': 0xffff, 'ex': '80'}),
                (
                    'inet:mac',
                    {'subof': 'str', 'regex': '^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$', 'lower': 1, 'nullval': '??',
                     'ex': 'aa:bb:cc:dd:ee:ff', 'doc': 'A 48 bit mac address'}),

                ('inet:web:acct', {'subof': 'sepr', 'sep': '/', 'fields': 'site,inet:fqdn|user,inet:user',
                                  'doc': 'A user account at a given web address', 'ex': 'twitter.com/invisig0th'}),
                ('inet:web:logon', {'subof': 'guid',
                                   'doc': 'An instance of a user account authenticating to a service.', }),

                ('inet:web:action', {'subof': 'guid',
                                   'doc': 'An instance of a user account performing an action.'}),
                ('inet:web:actref',
                 {'subof': 'xref', 'source': 'act,inet:web:action', 'doc': 'The web action refereneces the given node'}),

                ('inet:web:group', {'subof': 'sepr', 'sep': '/', 'fields': 'site,inet:fqdn|name,ou:name',
                                   'doc': 'A group within an online community'}),

                ('inet:web:post',
                 {'subof': 'comp', 'fields': 'acct,inet:web:acct|text,str:txt', 'doc': 'A post made by a web account'}),
                ('inet:web:postref',
                 {'subof': 'xref', 'source': 'post,inet:web:post', 'doc': 'The web post refereneces the given node'}),

                ('inet:web:file', {'subof': 'comp', 'fields': 'acct,inet:web:acct|file,file:bytes',
                                  'doc': 'A file posted by a web account'}),
                ('inet:web:memb', {'subof': 'comp', 'fields': 'acct,inet:web:acct|group,inet:web:group'}),
                ('inet:web:follows', {'subof': 'comp', 'fields': 'follower,inet:web:acct|followee,inet:web:acct'}),

                ('inet:web:mesg', {'subof': 'comp',
                                  'fields': 'from,inet:web:acct|to,inet:web:acct|time,time',
                                  'doc': 'A message sent from one web account to another',
                                  'ex': 'twitter.com/invisig0th|twitter.com/gobbles|20041012130220'}),

                ('inet:ssl:tcp4cert', {'subof': 'sepr', 'sep': '/', 'fields': 'tcp4,inet:tcp4|cert,file:bytes',
                                       'doc': 'An SSL cert file served by an IPv4 server'}),

                ('inet:whois:rar', {'subof': 'str:lwr', 'doc': 'A whois registrar', 'ex': 'blah domain registrar'}),
                ('inet:whois:reg', {'subof': 'str:lwr', 'doc': 'A whois registrant', 'ex': 'woot hostmaster'}),
                ('inet:whois:rec',
                 {'subof': 'sepr', 'sep': '@', 'fields': 'fqdn,inet:fqdn|asof,time', 'doc': 'A whois record',
                  'ex': ''}),
                ('inet:whois:recns', {'subof': 'comp', 'fields': 'ns,inet:fqdn|rec,inet:whois:rec',
                                      'doc': 'A nameserver associated with a given WHOIS record.'}),

                ('inet:whois:contact', {'subof': 'comp', 'fields': 'rec,inet:whois:rec|type,str:lwr',
                                        'doc': 'A whois contact for a specific record'}),
                ('inet:whois:regmail', {'subof': 'comp', 'fields': 'fqdn,inet:fqdn|email,inet:email',
                                        'doc': 'A whois registration fqdn->email link'}),
            ),

            'forms': (

                ('inet:ipv4', {'ptype': 'inet:ipv4'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??'}),
                    ('type', {'ptype': 'str', 'defval': '??',
                              'doc': 'what type of ipv4 address ( uni, multi, priv )'}),
                    ('asn', {'ptype': 'inet:asn', 'defval': -1}),
                ]),

                ('inet:cidr4', {'ptype': 'inet:cidr4'}, [
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The CIDR Network Address', 'ro': 1}),
                    ('mask', {'ptype': 'int', 'doc': 'The CIDR mask', 'ro': 1})
                ]),

                ('inet:ipv6', {'ptype': 'inet:ipv6'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??'}),
                    ('asn', {'ptype': 'inet:asn', 'defval': -1}),
                ]),

                ('inet:url', {'ptype': 'inet:url'}, [
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1}),
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('port', {'ptype': 'inet:port', 'ro': 1}),
                    ('user', {'ptype': 'inet:user', 'ro': 1}),
                    ('passwd', {'ptype': 'inet:passwd', 'ro': 1}),
                ]),

                ('inet:urlfile', {'ptype': 'inet:urlfile'}, [
                    ('url', {'ptype': 'inet:url', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'ro': 1}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                ]),

                ('inet:asn', {'ptype': 'inet:asn', 'doc': 'An Autonomous System'}, (
                    ('name', {'ptype': 'str:lwr', 'defval': '??'}),
                    ('owner', {'ptype': 'ou:org', 'doc': 'Organization which controls an ASN'}),
                )),

                ('inet:asnet4',
                 {'ptype': 'inet:asnet4', 'doc': 'A netblock IPv4 range assigned to an Autonomous System'}, [
                     ('asn', {'ptype': 'inet:asn'}),
                     ('net4', {'ptype': 'inet:net4'}),
                     ('net4:min', {'ptype': 'inet:ipv4'}),
                     ('net4:max', {'ptype': 'inet:ipv4'}),
                 ]),

                ('inet:user', {'ptype': 'inet:user'}, []),

                ('inet:passwd', {'ptype': 'inet:passwd'}, [
                    ('md5', {'ptype': 'hash:md5', 'doc': 'Pre-computed MD5 hash of the passwd'}),
                    ('sha1', {'ptype': 'hash:sha1', 'doc': 'Pre-computed SHA1 hash of the passwd'}),
                    ('sha256', {'ptype': 'hash:sha256', 'doc': 'Pre-computed SHA256 hash of the passwd'}),
                ]),

                ('inet:mac', {'ptype': 'inet:mac'}, [
                    ('vendor',
                     {'ptype': 'str', 'defval': '??', 'doc': 'The vendor name registered for the 24 bit prefix'}),
                ]),

                ('inet:fqdn', {'ptype': 'inet:fqdn'}, [
                    ('sfx', {'ptype': 'bool', 'defval': 0, 'doc': 'Set to 1 if this FQDN is considered a "suffix"'}),
                    ('zone',
                     {'ptype': 'bool', 'defval': 0, 'doc': 'Set to 1 if this FQDN is a logical zone (under a suffix)'}),
                    ('domain', {'ptype': 'inet:fqdn', 'doc': 'The parent FQDN of the FQDN'}),
                    ('host', {'ptype': 'str', 'doc': 'The hostname of the FQDN'}),

                    ('created', {'ptype': 'time:min'}),
                    ('updated', {'ptype': 'time:max'}),
                    ('expires', {'ptype': 'time:max'}),

                ]),

                ('inet:email', {'ptype': 'inet:email'}, [
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('user', {'ptype': 'inet:user', 'ro': 1}),
                ]),

                ('inet:tcp4', {'ptype': 'inet:srv4'}, [
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1}),
                    ('port', {'ptype': 'inet:port', 'ro': 1}),
                ]),

                ('inet:udp4', {'ptype': 'inet:srv4'}, [
                    ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1}),
                    ('port', {'ptype': 'inet:port', 'ro': 1}),
                ]),

                ('inet:tcp6', {'ptype': 'inet:srv6'}, [
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1}),
                    ('port', {'ptype': 'inet:port', 'ro': 1}),
                ]),

                ('inet:udp6', {'ptype': 'inet:srv6'}, [
                    ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1}),
                    ('port', {'ptype': 'inet:port', 'ro': 1}),
                ]),

                ('inet:flow', {}, (

                    ('time', {'ptype': 'time', 'doc': 'The time the connection was initiated'}),
                    ('duration', {'ptype': 'int', 'doc': 'The duration of the flow in seconds'}),

                    ('dst:host', {'ptype': 'it:host', 'doc': 'The destination host guid'}),
                    ('dst:proc', {'ptype': 'it:exec:proc', 'doc': 'The destination proc guid'}),
                    ('dst:txbytes', {'ptype': 'int', 'doc': 'The number of bytes sent by the destination'}),

                    ('dst:tcp4', {'ptype': 'inet:tcp4'}),
                    ('dst:tcp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1}),
                    ('dst:tcp4:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('dst:udp4', {'ptype': 'inet:udp4'}),
                    ('dst:udp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1}),
                    ('dst:udp4:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('dst:tcp6', {'ptype': 'inet:tcp6'}),
                    ('dst:tcp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1}),
                    ('dst:tcp6:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('dst:udp6', {'ptype': 'inet:udp6'}),
                    ('dst:udp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1}),
                    ('dst:udp6:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('src:host', {'ptype': 'it:host', 'doc': 'The source host guid'}),
                    ('src:proc', {'ptype': 'it:exec:proc', 'doc': 'The source proc guid'}),
                    ('src:txbytes', {'ptype': 'int', 'doc': 'The number of bytes sent by the source'}),

                    ('src:tcp4', {'ptype': 'inet:tcp4'}),
                    ('src:tcp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1}),
                    ('src:tcp4:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('src:udp4', {'ptype': 'inet:udp4'}),
                    ('src:udp4:ipv4', {'ptype': 'inet:ipv4', 'ro': 1}),
                    ('src:udp4:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('src:tcp6', {'ptype': 'inet:tcp6'}),
                    ('src:tcp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1}),
                    ('src:tcp6:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('src:udp6', {'ptype': 'inet:udp6'}),
                    ('src:udp6:ipv6', {'ptype': 'inet:ipv6', 'ro': 1}),
                    ('src:udp6:port', {'ptype': 'inet:port', 'ro': 1}),

                    ('from', {'ptype': 'guid', 'doc': 'The ingest source file/iden.  Used for reparsing'}),

                )),

                ('inet:web:acct', {'ptype': 'inet:web:acct'}, [
                    ('site', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('user', {'ptype': 'inet:user', 'ro': 1}),

                    ('dob', {'ptype': 'time'}),

                    # ('bio:bt',{'ptype':'wtf','doc':'The web account's self documented blood type'}),

                    ('url', {'ptype': 'inet:url'}),
                    ('webpage', {'ptype': 'inet:url'}),
                    ('avatar', {'ptype': 'file:bytes'}),

                    ('tagline', {'ptype': 'str:txt', 'doc': 'A web account status/tag line text'}),
                    ('loc', {'ptype': 'str:lwr', 'doc': 'The web account self declared location'}),
                    ('occupation', {'ptype': 'str:txt', 'doc': 'A web account self declared occupation'}),
                    # ('gender',{'ptype':'inet:fqdn','ro':1}),

                    ('name', {'ptype': 'inet:user'}),
                    ('realname', {'ptype': 'ps:name'}),
                    ('email', {'ptype': 'inet:email'}),
                    ('phone', {'ptype': 'tel:phone'}),
                    ('signup', {'ptype': 'time', 'doc': 'The time the web account was registered'}),
                    ('signup:ipv4', {'ptype': 'inet:ipv4', 'doc': 'The original ipv4 address used to sign up for the account'}),
                    ('passwd', {'ptype': 'inet:passwd', 'doc': 'The current passwd for the web account'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                ]),

                ('inet:web:logon', {'ptype': 'inet:web:logon'}, [
                    ('acct', {'ptype': 'inet:web:acct', 'doc': 'The account associated with the logon event.', }),
                    ('acct:site', {'ptype': 'inet:fqdn', }),
                    ('acct:user', {'ptype': 'inet:user', }),
                    ('time', {'ptype': 'time', 'doc': 'The time the account logged into the service', }),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The source IPv4 address of the logon.'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The source IPv6 address of the logon.'}),
                    ('logout', {'ptype': 'time', 'doc': 'The time the account logged out of the service.'})
                ]),

                ('inet:web:action', {'ptype': 'inet:web:action'}, [
                    ('act', {'ptype': 'str:lwr', 'req': 1, 'doc': 'The action performed'}),
                    ('acct', {'ptype': 'inet:web:acct', 'req': 1, 'ro': 1, 'doc': 'The web account associated with the action'}),
                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1}),
                    ('info', {'ptype': 'json', 'doc': 'Other information about the action'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the netuser performed the action'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The source IPv4 address of the action'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The source IPv6 address of the action'}),
                ]),
                ('inet:web:actref', {}, [
                    ('act', {'ptype': 'inet:web:action', 'ro': 1}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1}),
                    ('xref:intval', {'ptype': 'int', 'ro': 1}),
                    ('xref:strval', {'ptype': 'str', 'ro': 1}),
                ]),

                ('inet:web:group', {}, [
                    ('site', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('name', {'ptype': 'ou:name', 'ro': 1}),

                    ('desc', {'ptype': 'str:txt'}),

                    ('url', {'ptype': 'inet:url'}),
                    ('webpage', {'ptype': 'inet:url'}),
                    ('avatar', {'ptype': 'file:bytes'}),
                ]),

                ('inet:web:post', {}, [

                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1}),
                    ('text', {'ptype': 'str:txt', 'ro': 1, 'doc': 'The text of the actual post'}),

                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1}),

                    ('time', {'ptype': 'time'}),

                    ('replyto', {'ptype': 'inet:web:post'}),

                    ('url', {'ptype': 'inet:url', 'doc': 'The (optional) URL where the post is published/visible'}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The (optional) file which was posted'}),
                ]),
                ('inet:web:postref', {}, [
                    ('post', {'ptype': 'inet:web:post', 'ro': 1}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1}),
                    ('xref:intval', {'ptype': 'int', 'ro': 1}),
                    ('xref:strval', {'ptype': 'str', 'ro': 1}),
                ]),

                ('inet:web:mesg', {}, [
                    ('from', {'ptype': 'inet:web:acct', 'ro': 1}),
                    ('to', {'ptype': 'inet:web:acct', 'ro': 1}),
                    ('time', {'ptype': 'time', 'ro': 1, 'doc': 'The time at which the message was sent'}),
                    ('url', {'ptype': 'inet:url', 'doc': 'Optional URL of netmesg'}),
                    ('text', {'ptype': 'str:txt', 'doc': 'Optional text body of message'}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'Optional file attachment'}),
                ]),

                ('inet:web:follows', {}, [

                    ('follower', {'ptype': 'inet:web:acct', 'ro': 1}),
                    ('followee', {'ptype': 'inet:web:acct', 'ro': 1}),

                    ('seen:min', {'ptype': 'time:min', 'doc': 'Optional first/earliest following'}),
                    ('seen:max', {'ptype': 'time:max', 'doc': 'Optional last/end of following'}),

                ]),

                ('inet:web:memb', {}, [

                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1}),
                    ('group', {'ptype': 'inet:web:group', 'ro': 1}),

                    ('title', {'ptype': 'str:lwr'}),

                    ('joined', {'ptype': 'time'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),

                ]),

                ('inet:web:file', {}, [

                    ('acct', {'ptype': 'inet:web:acct', 'ro': 1}),
                    ('acct:site', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('acct:user', {'ptype': 'inet:user', 'ro': 1}),

                    ('file', {'ptype': 'file:bytes', 'ro': 1}),

                    ('name', {'ptype': 'file:base', 'doc': 'The basename of the file in the post'}),

                    ('posted', {'ptype': 'time'}),

                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The source IPv4 address of the post.'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The source IPv6 address of the post.'}),

                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                ]),

                ('inet:whois:reg', {}, []),
                ('inet:whois:rar', {}, []),

                ('inet:whois:regmail', {'ptype': 'inet:whois:regmail'}, [
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('email', {'ptype': 'inet:email', 'ro': 1}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                ]),

                ('inet:whois:rec', {'ptype': 'inet:whois:rec'}, [
                    ('fqdn', {'ptype': 'inet:fqdn'}),
                    ('asof', {'ptype': 'time'}),
                    ('text', {'ptype': 'str:lwr'}),
                    ('created', {'ptype': 'time', 'doc': 'The "created" time from the whois record'}),
                    ('updated', {'ptype': 'time', 'doc': 'The "last updated" time from the whois record'}),
                    ('expires', {'ptype': 'time', 'doc': 'The "expires" time from the whois record'}),
                    ('registrar', {'ptype': 'inet:whois:rar', 'defval': '??'}),
                    ('registrant', {'ptype': 'inet:whois:reg', 'defval': '??'}),
                ]),

                ('inet:whois:recns', {}, [
                    ('ns', {'ptype': 'inet:fqdn', 'ro': 1, 'doct': 'Nameserver for a given FQDN'}),
                    ('rec', {'ptype': 'inet:whois:rec', 'ro': 1}),
                    ('rec:fqdn', {'ptype': 'inet:fqdn', 'ro': 1}),
                    ('rec:asof', {'ptype': 'time', 'ro': 1}),
                ]),

                ('inet:whois:contact', {}, [

                    ('rec', {'ptype': 'inet:whois:rec'}),
                    ('rec:fqdn', {'ptype': 'inet:fqdn'}),
                    ('rec:asof', {'ptype': 'time'}),

                    ('type', {'ptype': 'str:lwr'}),

                    ('id', {'ptype': 'str:lwr'}),
                    ('name', {'ptype': 'str:lwr'}),
                    ('email', {'ptype': 'inet:email'}),

                    ('orgname', {'ptype': 'ou:name'}),
                    ('address', {'ptype': 'str:lwr'}),  # FIXME street address type
                    ('city', {'ptype': 'str:lwr'}),
                    # ('zip',{'ptype':'str:lwr'}),
                    ('state', {'ptype': 'str:lwr'}),
                    ('country', {'ptype': 'pol:iso2'}),

                    ('phone', {'ptype': 'tel:phone'}),
                    ('fax', {'ptype': 'tel:phone'}),
                ]),

                ('inet:ssl:tcp4cert', {'ptype': 'inet:ssl:tcp4cert'}, [
                    ('tcp4', {'ptype': 'inet:tcp4'}),
                    ('cert', {'ptype': 'file:bytes'}),
                    ('tcp4:ipv4', {'ptype': 'inet:ipv4'}),
                ]),
            ),
        }
        name = 'inet'
        return ((name, modl),)
