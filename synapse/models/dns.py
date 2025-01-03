import synapse.exc as s_exc

import synapse.lib.types as s_types
import synapse.lib.module as s_module

dnsreplycodes = (
    (0, 'NOERROR'),
    (1, 'FORMERR'),
    (2, 'SERVFAIL'),
    (3, 'NXDOMAIN'),
    (4, 'NOTIMP'),
    (5, 'REFUSED'),
    (6, 'YXDOMAIN'),
    (7, 'YXRRSET'),
    (8, 'NXRRSET'),
    (9, 'NOTAUTH'),
    (10, 'NOTZONE'),
    (11, 'DSOTYPENI'),
    (16, 'BADSIG'),
    (17, 'BADKEY'),
    (18, 'BADTIME'),
    (19, 'BADMODE'),
    (20, 'BADNAME'),
    (21, 'BADALG'),
    (22, 'BADTRUNC'),
    (23, 'BADCOOKIE'),
)

class DnsName(s_types.Str):

    def postTypeInit(self):

        s_types.Str.postTypeInit(self)
        self.inarpa = '.in-addr.arpa'
        self.inarpa6 = '.ip6.arpa'

        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):
        # Backwards compatible
        norm = valu.lower()
        norm = norm.strip()  # type: str
        # Break out fqdn / ipv4 / ipv6 subs :D
        subs = {}
        # ipv4
        if norm.isnumeric():
            # do-nothing for integer only strs
            pass
        elif norm.endswith(self.inarpa):
            # Strip, reverse, check if ipv4
            temp = norm[:-len(self.inarpa)]
            temp = '.'.join(temp.split('.')[::-1])
            try:
                ipv4norm, info = self.modl.type('inet:ip').norm(temp)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = ipv4norm
        elif norm.endswith(self.inarpa6):
            parts = [c for c in norm[:-len(self.inarpa6)][::-1] if c != '.']
            try:
                if len(parts) != 32:
                    raise s_exc.BadTypeValu(mesg='Invalid number of ipv6 parts')
                temp = (6, int(''.join(parts), 16))
                ipv6norm, info = self.modl.type('inet:ip').norm(temp)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = ipv6norm
        else:
            # Try fallbacks to parse out possible ipv4/ipv6 garbage queries
            try:
                ipnorm, info = self.modl.type('inet:ip').norm(norm)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = ipnorm
                return norm, {'subs': subs}

            # Lastly, try give the norm'd valu a shot as an inet:fqdn
            try:
                fqdnnorm, info = self.modl.type('inet:fqdn').norm(norm)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['fqdn'] = fqdnnorm

        return norm, {'subs': subs}

class DnsModule(s_module.CoreModule):

    def getModelDefs(self):

        modl = {

            'ctors': (

                ('inet:dns:name', 'synapse.models.dns.DnsName', {}, {
                    'doc': 'A DNS query name string. Likely an FQDN but not always.',
                    'ex': 'vertex.link',
                }),

            ),

            'types': (

                ('inet:dns:a', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv4'))}), {
                    'ex': '(vertex.link,1.2.3.4)',
                    'doc': 'The result of a DNS A record lookup.'}),

                ('inet:dns:aaaa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv6'))}), {
                    'ex': '(vertex.link,2607:f8b0:4004:809::200e)',
                    'doc': 'The result of a DNS AAAA record lookup.'}),

                ('inet:dns:rev', ('comp', {'fields': (('ip', 'inet:ip'), ('fqdn', 'inet:fqdn'))}), {
                    'ex': '(1.2.3.4,vertex.link)',
                    'doc': 'The transformed result of a DNS PTR record lookup.'}),

                ('inet:dns:ns', ('comp', {'fields': (('zone', 'inet:fqdn'), ('ns', 'inet:fqdn'))}), {
                    'ex': '(vertex.link,ns.dnshost.com)',
                    'doc': 'The result of a DNS NS record lookup.'}),

                ('inet:dns:cname', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('cname', 'inet:fqdn'))}), {
                    'ex': '(foo.vertex.link,vertex.link)',
                    'doc': 'The result of a DNS CNAME record lookup.'}),

                ('inet:dns:mx', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('mx', 'inet:fqdn'))}), {
                    'ex': '(vertex.link,mail.vertex.link)',
                    'doc': 'The result of a DNS MX record lookup.'}),

                ('inet:dns:soa', ('guid', {}), {
                    'doc': 'The result of a DNS SOA record lookup.'}),

                ('inet:dns:txt', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('txt', 'str'))}), {
                    'ex': '(hehe.vertex.link,"fancy TXT record")',
                    'doc': 'The result of a DNS MX record lookup.'}),

                ('inet:dns:record', ('ndef', {
                    'forms': (
                        'inet:dns:a',
                        'inet:dns:aaaa',
                        'inet:dns:cname',
                        'inet:dns:mx',
                        'inet:dns:ns',
                        'inet:dns:rev',
                        'inet:dns:soa',
                        'inet:dns:txt',
                    )}), {
                    'doc': 'An ndef type including all forms which represent DNS records.'}),

                ('inet:dns:type', ('int', {}), {
                    'doc': 'A DNS query/answer type integer.'}),

                ('inet:dns:query',
                    ('comp', {'fields': (('client', 'inet:client'), ('name', 'inet:dns:name'), ('type', 'int'))}), {
                        'ex': '(1.2.3.4, woot.com, 1)',
                        'doc': 'A DNS query unique to a given client.'}),

                ('inet:dns:request', ('guid', {}), {
                    'doc': 'A single instance of a DNS resolver request and optional reply info.'}),

                ('inet:dns:answer', ('guid', {}), {
                    'doc': 'A single answer from within a DNS reply.'}),

                ('inet:dns:wild:a', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))}), {
                    'doc': 'A DNS A wild card record and the IPv4 it resolves to.'}),

                ('inet:dns:wild:aaaa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))}), {
                    'doc': 'A DNS AAAA wild card record and the IPv6 it resolves to.'}),

                ('inet:dns:dynreg', ('guid', {}), {
                    'doc': 'A dynamic DNS registration.'}),

            ),

            'forms': (
                ('inet:dns:a', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                        'doc': 'The domain queried for its DNS A record.'}),
                    ('ip', ('inet:ip', {}), {'ro': True,
                        'doc': 'The IPv4 address returned in the A record.',
                        'prevnames': ('ipv4',)}),
                )),
                ('inet:dns:aaaa', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                        'doc': 'The domain queried for its DNS AAAA record.'}),
                    ('ip', ('inet:ip', {}), {'ro': True,
                        'doc': 'The IPv6 address returned in the AAAA record.',
                        'prevnames': ('ipv6',)}),
                )),
                ('inet:dns:rev', {'prevnames': ('inet:dns:rev6',)}, (
                    ('ip', ('inet:ip', {}), {'ro': True,
                        'doc': 'The IP address queried for its DNS PTR record.',
                        'prevnames': ('ipv4', 'ipv6')}),

                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain returned in the PTR record.'}),
                )),
                ('inet:dns:ns', {}, (
                    ('zone', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain queried for its DNS NS record.'}),
                    ('ns', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain returned in the NS record.'}),
                )),
                ('inet:dns:cname', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain queried for its CNAME record.'}),
                    ('cname', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain returned in the CNAME record.'}),
                )),
                ('inet:dns:mx', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain queried for its MX record.'}),
                    ('mx', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain returned in the MX record.'}),
                )),

                ('inet:dns:soa', {}, (
                    ('fqdn', ('inet:fqdn', {}), {
                         'doc': 'The domain queried for its SOA record.'}),
                    ('ns', ('inet:fqdn', {}), {
                         'doc': 'The domain (MNAME) returned in the SOA record.'}),
                    ('email', ('inet:email', {}), {
                         'doc': 'The email address (RNAME) returned in the SOA record.'}),
                )),

                ('inet:dns:txt', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                         'doc': 'The domain queried for its TXT record.'}),
                    ('txt', ('str', {}), {'ro': True,
                         'doc': 'The string returned in the TXT record.'}),
                )),

                ('inet:dns:query', {}, (
                    ('client', ('inet:client', {}), {'ro': True, }),
                    ('name', ('inet:dns:name', {}), {'ro': True, }),
                    ('name:ip', ('inet:ip', {}), {
                        'prevnames': ('name:ipv4', 'name:ipv6')}),

                    ('name:fqdn', ('inet:fqdn', {}), {}),
                    ('type', ('int', {}), {'ro': True, }),
                )),

                ('inet:dns:request', {}, (

                    ('time', ('time', {}), {}),

                    ('query', ('inet:dns:query', {}), {}),
                    ('query:name', ('inet:dns:name', {}), {}),
                    ('query:name:ip', ('inet:ip', {}), {
                        'prevnames': ('query:name:ipv4', 'query:name:ipv6')}),

                    ('query:name:fqdn', ('inet:fqdn', {}), {}),
                    ('query:type', ('int', {}), {}),

                    ('server', ('inet:server', {}), {}),

                    ('reply:code', ('int', {'enums': dnsreplycodes, 'enums:strict': False}), {
                        'doc': 'The DNS server response code.'}),

                    ('exe', ('file:bytes', {}), {
                        'doc': 'The file containing the code that attempted the DNS lookup.'}),

                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The process that attempted the DNS lookup.'}),

                    ('host', ('it:host', {}), {
                        'doc': 'The host that attempted the DNS lookup.'}),

                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'}),

                )),

                ('inet:dns:answer', {}, (

                    ('ttl', ('int', {}), {}),
                    ('request', ('inet:dns:request', {}), {}),
                    ('record', ('inet:dns:record', {}), {
                        'doc': 'The DNS record returned by the lookup.',
                        'prevnames': ('a', 'aaaa', 'cname', 'mx', 'ns', 'rev', 'soa', 'txt')}),

                    ('mx:priority', ('int', {}), {
                        'doc': 'The DNS MX record priority.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time that the DNS response was transmitted.'}),
                )),

                ('inet:dns:wild:a', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                        'doc': 'The domain containing a wild card record.'}),
                    ('ip', ('inet:ip', {}), {'ro': True,
                        'doc': 'The IPv4 address returned by wild card resolutions.',
                        'prevnames': ('ipv4',)}),
                )),

                ('inet:dns:wild:aaaa', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': True,
                        'doc': 'The domain containing a wild card record.'}),
                    ('ip', ('inet:ip', {}), {'ro': True,
                        'doc': 'The IPv6 address returned by wild card resolutions.',
                        'prevnames': ('ipv6',)}),
                )),

                ('inet:dns:dynreg', {}, (

                    ('fqdn', ('inet:fqdn', {}), {
                        'doc': 'The FQDN registered within a dynamic DNS provider.'}),

                    ('provider', ('ou:org', {}), {
                        'doc': 'The organization which provides the dynamic DNS FQDN.'}),

                    ('provider:name', ('ou:name', {}), {
                        'doc': 'The name of the organization which provides the dynamic DNS FQDN.'}),

                    ('provider:fqdn', ('inet:fqdn', {}), {
                        'doc': 'The FQDN of the organization which provides the dynamic DNS FQDN.'}),

                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact information of the registrant.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time that the dynamic DNS registration was first created.'}),

                    ('client', ('inet:client', {}), {
                        'doc': 'The network client address used to register the dynamic FQDN.'}),
                )),
            )

        }
        name = 'inet:dns'
        return ((name, modl), )
