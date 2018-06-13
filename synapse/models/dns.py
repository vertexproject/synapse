import synapse.lib.module as s_module

class DnsModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (
                ('inet:dns:a', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ipv4', 'inet:ipv4'))}), {
                    'doc': 'The result of a DNS A record lookup.',
                    'ex': '(vertex.link,1.2.3.4)',
                }),
                ('inet:dns:aaaa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ipv6', 'inet:ipv6'))}), {
                    'doc': 'The result of a DNS AAAA record lookup.',
                    'ex': '(vertex.link,2607:f8b0:4004:809::200e)',
                }),
                ('inet:dns:rev', ('comp', {'fields': (('ipv4', 'inet:ipv4'), ('fqdn', 'inet:fqdn'))}), {
                    'doc': 'The transformed result of a DNS PTR record lookup.',
                    'ex': '(1.2.3.4,vertex.link)',
                }),
                ('inet:dns:rev6', ('comp', {'fields': (('ipv6', 'inet:ipv6'), ('fqdn', 'inet:fqdn'))}), {
                    'doc': 'The transformed result of a DNS PTR record for an IPv6 address.',
                    'ex': '(2607:f8b0:4004:809::200e,vertex.link)',
                }),
                ('inet:dns:ns', ('comp', {'fields': (('zone', 'inet:fqdn'), ('ns', 'inet:fqdn'))}), {
                    'doc': 'The result of a DNS NS record lookup.',
                    'ex': '(vertex.link,ns.dnshost.com)'
                }),
                ('inet:dns:cname', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('cname', 'inet:fqdn'))}), {
                    'doc': 'The result of a DNS CNAME record lookup.',
                    'ex': '(foo.vertex.link,vertex.link)',
                }),
                ('inet:dns:mx', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('mx', 'inet:fqdn'))}), {
                    'doc': 'The result of a DNS MX record lookup.',
                    'ex': '(vertex.link,mail.vertex.link)',
                }),
                ('inet:dns:soa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ns', 'inet:fqdn'), ('email', 'inet:email'))}), {
                    'doc': 'The result of a DNS SOA record lookup.'
                }),
                ('inet:dns:txt', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('txt', 'str'))}), {
                    'doc': 'The result of a DNS MX record lookup.',
                    'ex': '(hehe.vertex.link,"fancy TXT record")',
                }),

                ('inet:dns:name', ('str', {'lower': True, 'strip': True}), {
                    'doc': 'A DNS query name string.  Likely an FQDN but not always.'}),

                ('inet:dns:query',
                    ('comp', {'fields': (('client', 'inet:client'), ('name', 'inet:dns:name'), ('type', 'int'))}), {
                        'ex': '(1.2.3.4, woot.com, 1)',
                        'doc': 'A DNS query unique to a given client.'}),

                ('inet:dns:request', ('guid', {}), {
                    'doc': 'A single instance of a DNS resolver request.'}),

                ('inet:dns:reply', ('guid', {}), {
                    'doc': 'A reply to an inet:dns:request.'}),
            ),

            'forms': (
                ('inet:dns:a', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                        'doc': 'The domain queried for its DNS A record.'}),
                    ('ipv4', ('inet:ipv4', {}), {'ro': 1,
                        'doc': 'The IPv4 address returned in the A record.'}),
                )),
                ('inet:dns:aaaa', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain queried for its DNS AAAA record.'}),
                    ('ipv6', ('inet:ipv6', {}), {'ro': 1,
                         'doc': 'The IPv6 address returned in the AAAA record.'}),
                )),
                ('inet:dns:rev', {}, (
                    ('ipv4', ('inet:ipv4', {}), {'ro': 1,
                         'doc': 'The IPv4 address queried for its DNS PTR record.'}),
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain returned in the PTR record.'}),
                )),
                ('inet:dns:rev6', {}, (
                    ('ipv6', ('inet:ipv6', {}), {'ro': 1,
                         'doc': 'The IPv6 address queried for its DNS PTR record.'}),
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain returned in the PTR record.'}),
                )),
                ('inet:dns:ns', {}, (
                    ('zone', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain queried for its DNS NS record.'}),
                    ('ns', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain returned in the NS record.'}),
                )),
                ('inet:dns:cname', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain queried for its CNAME record.'}),
                    ('cname', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain returned in the CNAME record.'}),
                )),
                ('inet:dns:mx', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain queried for its MX record.'}),
                    ('mx', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain returned in the MX record.'}),
                )),

                ('inet:dns:soa', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain queried for its SOA record.'}),
                    ('ns', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain (MNAME) returned in the SOA record.'}),
                    ('email', ('inet:email', {}), {'ro': 1,
                         'doc': 'The email address (RNAME) returned in the SOA record.'}),
                )),

                ('inet:dns:txt', {}, (
                    ('fqdn', ('inet:fqdn', {}), {'ro': 1,
                         'doc': 'The domain queried for its TXT record.'}),
                    ('txt', ('str', {}), {'ro': 1,
                         'doc': 'The string returned in the TXT record.'}),
                )),

                ('inet:dns:query', {}, (
                    ('client', ('inet:client', {}), {}),
                    ('name', ('inet:dns:name', {}), {}),
                    ('type', ('int', {}), {}),
                )),

                ('inet:dns:request', {}, (

                    ('time', ('time', {}), {}),
                    ('query', ('inet:dns:query', {}), {}),

                    ('server', ('inet:server', {}), {}),

                    ('rcode', ('int', {}), {
                        'doc': 'The DNS server response code.'}),

                    ('exe', ('file:bytes', {}), {
                        'doc': 'The file containing the code that attempted the DNS lookup.'}),

                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The process that attempted the DNS lookup.'}),

                    ('host', ('it:host', {}), {
                        'doc': 'The host that attempted the DNS lookup.'}),

                )),

                ('inet:dns:reply', {}, (

                    ('ttl', ('int', {}), {}),
                    ('request', ('inet:dns:request', {}), {}),

                    ('a', ('inet:dns:a', {}), { 'ro': True,
                        'doc': 'The DNS A record returned by the lookup.',
                    }),
                    ('ns', ('inet:dns:ns', {}), { 'ro': True,
                        'doc': 'The DNS NS record returned by the lookup.',
                    }),
                    ('rev', ('inet:dns:rev', {}), { 'ro': True,
                        'doc': 'The DNS PTR record returned by the lookup.',
                    }),
                    ('aaaa', ('inet:dns:aaaa', {}), { 'ro': True,
                        'doc': 'The DNS AAAA record returned by the lookup.',
                    }),
                    ('rev6', ('inet:dns:rev6', {}), { 'ro': True,
                        'doc': 'The DNS PTR record returned by the lookup of a IPv6 address.',
                    }),
                    ('cname', ('inet:dns:cname', {}), { 'ro': True,
                        'doc': 'The DNS CNAME record returned by the lookup',
                    }),
                    ('mx', ('inet:dns:mx', {}), { 'ro': True,
                        'doc': 'The DNS MX record returned by the lookup.',
                    }),
                    ('soa', ('inet:dns:soa', {}), { 'ro': True,
                        'doc': 'The domain queried for its SOA record.',
                    }),
                    ('txt', ('inet:dns:txt', {}), { 'ro': True,
                        'doc': 'The DNS TXT record returned by the lookup.',
                    }),
                )),
            )

        }
        name = 'inet:dns'
        return ((name, modl), )
