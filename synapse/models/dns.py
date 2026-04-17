import synapse.exc as s_exc

import synapse.lib.types as s_types

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

        self.iptype = self.modl.type('inet:ip')
        self.fqdntype = self.modl.type('inet:fqdn')

        self.setNormFunc(str, self._normPyStr)

    async def _normPyStr(self, valu, view=None):
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
                ipv4norm, info = await self.iptype.norm(temp)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = (self.iptype.typehash, ipv4norm, info)
        elif norm.endswith(self.inarpa6):
            parts = [c for c in norm[:-len(self.inarpa6)][::-1] if c != '.']
            try:
                if len(parts) != 32:
                    raise s_exc.BadTypeValu(mesg='Invalid number of ipv6 parts')
                temp = (6, int(''.join(parts), 16))
                ipv6norm, info = await self.iptype.norm(temp)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = (self.iptype.typehash, ipv6norm, info)
        else:
            # Try fallbacks to parse out possible ipv4/ipv6 garbage queries
            try:
                ipnorm, info = await self.iptype.norm(norm)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = (self.iptype.typehash, ipnorm, info)
                return norm, {'subs': subs}

            # Lastly, try give the norm'd valu a shot as an inet:fqdn
            try:
                fqdnnorm, info = await self.fqdntype.norm(norm)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['fqdn'] = (self.fqdntype.typehash, fqdnnorm, info)

        return norm, {'subs': subs}

modeldefs = (
    {

        'interfaces': (
            ('inet:dns:record', {
                'doc': 'An interface for DNS records.'}),
        ),

        'types': (

            ('inet:dns:name', (None, {'ctor': 'synapse.models.dns.DnsName'}), {
                'ex': 'vertex.link',
                'doc': 'A DNS query name string. Likely an FQDN but not always.'}),

            ('inet:dns:a', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv4'))}), {
                'template': {'title': 'DNS A record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,1.2.3.4)',
                'doc': 'The result of a DNS A record lookup.'}),

            ('inet:dns:aaaa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv6'))}), {
                'template': {'title': 'DNS AAAA record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,2607:f8b0:4004:809::200e)',
                'doc': 'The result of a DNS AAAA record lookup.'}),

            ('inet:dns:rev', ('comp', {'fields': (('ip', 'inet:ip'), ('fqdn', 'inet:fqdn'))}), {
                'template': {'title': 'Reverse DNS record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(1.2.3.4,vertex.link)',
                'doc': 'The transformed result of a DNS PTR record lookup.'}),

            ('inet:dns:ns', ('comp', {'fields': (('zone', 'inet:fqdn'), ('ns', 'inet:fqdn'))}), {
                'template': {'title': 'DNS NS record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,ns.dnshost.com)',
                'doc': 'The result of a DNS NS record lookup.'}),

            ('inet:dns:cname', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('cname', 'inet:fqdn'))}), {
                'template': {'title': 'DNS CNAME record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(foo.vertex.link,vertex.link)',
                'doc': 'The result of a DNS CNAME record lookup.'}),

            ('inet:dns:mx', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('mx', 'inet:fqdn'))}), {
                'template': {'title': 'DNS MX record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,mail.vertex.link)',
                'doc': 'The result of a DNS MX record lookup.'}),

            ('inet:dns:soa', ('guid', {}), {
                'template': {'title': 'DNS SOA record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'doc': 'The result of a DNS SOA record lookup.'}),

            ('inet:dns:txt', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('txt', 'str'))}), {
                'template': {'title': 'DNS TXT record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(hehe.vertex.link,"fancy TXT record")',
                'doc': 'The result of a DNS TXT record lookup.'}),

            ('inet:dns:query',
                ('comp', {'fields': (('client', 'inet:client'), ('name', 'inet:dns:name'), ('type', 'int'))}), {
                    'interfaces': (
                        ('meta:observable', {'template': {'title': 'DNS query'}}),
                    ),
                    'ex': '(1.2.3.4, woot.com, 1)',
                    'doc': 'A DNS query unique to a given client.'}),

            ('inet:dns:request', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:request', {}),
                ),
                'props': (

                    ('query:name', ('inet:dns:name', {}), {
                        'doc': 'The DNS query name string in the request.'}),

                    ('query:type', ('int', {}), {
                        'doc': 'The type of record requested in the query.'}),

                    ('response', ('inet:dns:response', {}), {
                        'doc': 'The response sent by the DNS server.'}),
                ),
                'doc': 'A DNS protocol request.'}),

            ('inet:dns:response', {
                'interfaces': (
                    ('inet:proto:response', {}),
                ),
                'props': (

                    ('code', ('dns:reply:code', {}), {
                        'doc': 'The DNS server reply code.'}),

                    ('answers', ('inet:dns:answers', {}), {
                        'doc': 'The DNS answers included in the response.'}),
                ),
                'doc': 'A DNS protocol response.'}),

            ('inet:dns:answer', ('guid', {}), {
                'props': (

                    ('ttl', ('int', {}), {
                        'doc': 'The time to live value of the DNS record in the response.'}),

                    ('record', ('inet:dns:record', {}), {
                        'doc': 'The DNS record contained in the answer.'}),
                ),
                'doc': 'A single answer from within a DNS reply.'}),

            ('inet:dns:mx:answer', ('inet:dns:answer', {}), {
                'props': (
                    ('record', ('inet:dns:mx', {}), {
                        'doc': 'The MX record in the answer.'}),

                    ('priority', ('int', {}), {
                        'doc': 'The DNS MX record priority.'}),
                ),
                'doc': 'A single MX answer from within a DNS reply.'}),

            ('inet:dns:answers', ('array', {'type': 'inet:dns:answer'}), {
                'doc': 'An array of DNS answers.'}),

            ('inet:dns:wild:a', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'DNS wildcard A record'}}),
                ),
                'doc': 'A DNS A wild card record and the IPv4 it resolves to.'}),

            ('inet:dns:wild:aaaa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'DNS wildcard AAAA record'}}),
                ),
                'doc': 'A DNS AAAA wild card record and the IPv6 it resolves to.'}),

            ('inet:dns:dynreg', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'dynamic DNS registration'}}),
                ),
                'doc': 'A dynamic DNS registration.'}),

            ('dns:reply:code', ('int', {'enums': dnsreplycodes, 'enums:strict': False}), {
                'doc': 'A DNS reply code.'}),

        ),

        'forms': (
            ('inet:dns:a', {}, (
                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                    'doc': 'The domain queried for its DNS A record.'}),
                ('ip', ('inet:ip', {}), {'computed': True,
                    'doc': 'The IPv4 address returned in the A record.',
                    'prevnames': ('ipv4',)}),
                ('seen', ('ival', {}), {
                    'doc': 'The time range where the record was observed.'}),
            )),
            ('inet:dns:aaaa', {}, (
                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                    'doc': 'The domain queried for its DNS AAAA record.'}),
                ('ip', ('inet:ip', {}), {'computed': True,
                    'doc': 'The IPv6 address returned in the AAAA record.',
                    'prevnames': ('ipv6',)}),
            )),
            ('inet:dns:rev', {'prevnames': ('inet:dns:rev6',)}, (
                ('ip', ('inet:ip', {}), {'computed': True,
                    'doc': 'The IP address queried for its DNS PTR record.',
                    'prevnames': ('ipv4', 'ipv6')}),

                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                     'doc': 'The domain returned in the PTR record.'}),
            )),
            ('inet:dns:ns', {}, (
                ('zone', ('inet:fqdn', {}), {'computed': True,
                     'doc': 'The domain queried for its DNS NS record.'}),
                ('ns', ('inet:fqdn', {}), {'computed': True,
                     'doc': 'The domain returned in the NS record.'}),
            )),
            ('inet:dns:cname', {}, (
                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                     'doc': 'The domain queried for its CNAME record.'}),
                ('cname', ('inet:fqdn', {}), {'computed': True,
                     'doc': 'The domain returned in the CNAME record.'}),
            )),
            ('inet:dns:mx', {}, (
                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                     'doc': 'The domain queried for its MX record.'}),
                ('mx', ('inet:fqdn', {}), {'computed': True,
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
                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                     'doc': 'The domain queried for its TXT record.'}),
                ('txt', ('str', {}), {'computed': True,
                     'doc': 'The string returned in the TXT record.'}),
            )),

            ('inet:dns:query', {}, (

                ('client', ('inet:client', {}), {
                    'computed': True,
                    'doc': 'The client that performed the DNS query.'}),

                ('name', ('inet:dns:name', {}), {
                    'computed': True,
                    'doc': 'The DNS query name string.'}),

                ('type', ('int', {}), {
                    'computed': True,
                    'doc': 'The type of record that was queried.'}),
            )),

            ('inet:dns:wild:a', {}, (
                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                    'doc': 'The domain containing a wild card record.'}),
                ('ip', ('inet:ip', {}), {'computed': True,
                    'doc': 'The IPv4 address returned by wild card resolutions.',
                    'prevnames': ('ipv4',)}),
            )),

            ('inet:dns:wild:aaaa', {}, (
                ('fqdn', ('inet:fqdn', {}), {'computed': True,
                    'doc': 'The domain containing a wild card record.'}),
                ('ip', ('inet:ip', {}), {'computed': True,
                    'doc': 'The IPv6 address returned by wild card resolutions.',
                    'prevnames': ('ipv6',)}),
            )),

            ('inet:dns:dynreg', {}, (

                ('fqdn', ('inet:fqdn', {}), {
                    'doc': 'The FQDN registered within a dynamic DNS provider.'}),

                ('provider', ('ou:org', {}), {
                    'doc': 'The organization which provides the dynamic DNS FQDN.'}),

                ('provider:name', ('entity:name', {}), {
                    'doc': 'The name of the organization which provides the dynamic DNS FQDN.'}),

                ('provider:fqdn', ('inet:fqdn', {}), {
                    'doc': 'The FQDN of the organization which provides the dynamic DNS FQDN.'}),

                ('contact', ('entity:contact', {}), {
                    'doc': 'The contact information of the registrant.'}),

                ('created', ('time', {}), {
                    'doc': 'The time that the dynamic DNS registration was first created.'}),

                ('client', ('inet:client', {}), {
                    'doc': 'The network client address used to register the dynamic FQDN.'}),
            )),
        )
    },
)
