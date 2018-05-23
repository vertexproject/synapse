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
                ('inet:dns:type', ('str', {'lower': True, 'strip': True, 'enums': 'soa,ns,mx,a,aaaa,txt,srv,ptr,cname,hinfo,isdn'}), {
                   'doc': 'A DNS Request type enum.'
                }),
                ('inet:dns:req',
                 ('comp', {'fields': (('client', 'inet:client'), ('fqdn', 'inet:fqdn'), ('type', 'inet:dns:type'))}), {
                     'doc': 'A fused DNS request record.'
                 }),
                ('inet:dns:look', ('guid', {}), {
                    'doc': 'The instance (point-in-time) result of a DNS record lookup.',
                }),
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
                ('inet:dns:req', {}, (
                    # FIXME break out client subs for ipv4/ipv6
                    ('client', ('inet:client', {}), {
                        'ro': True,
                        'doc': 'The inet:addr which requested the FQDN',
                    }),
                    ('client:ipv4', ('inet:ipv4', {}), {
                        'ro': True,
                        'doc': 'The IPv4 of the client.',
                    }),
                    ('client:ipv6', ('inet:ipv6', {}), {
                        'ro': True,
                        'doc': 'The IPv6 of the client.',
                    }),
                    ('fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The requested FQDN',
                    }),
                    ('type', ('inet:dns:type', {}), {
                        'ro': True,
                        'doc': 'The type of DNS record requested.',
                    }),

                )),
                ('inet:dns:look', {}, (
                    ('time', ('time', ()), {
                        'ro': True,
                        'doc': 'The time thel ookup occured.',
                    }),
                    ('client', ('inet:client', {}), {
                        'doc': 'The client that requested the lookup.',
                    }),
                    ('client:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The IPv4 of the client that requested the lookup.',
                    }),
                    ('client:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The IPv6 of the client that requested the lookup.',
                    }),
                    ('client:port', ('inet:ipv4', {}), {
                        'doc': 'The port of the client that requested the lookup.',
                    }),
                    ('server', ('inet:server', {}), {
                        'doc': 'The server that responded to the lookup.',
                    }),
                    ('server:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The IPv4 of the server that responded to the lookup.',
                    }),
                    ('server:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The IPv6 of the server that responded to the lookup.',
                    }),
                    ('server:port', ('inet:ipv4', {}), {
                        'doc': 'The port of the server that responded to the lookup.',
                    }),
                    ('rcode', ('int', {}), {
                        'doc': 'The DNS server response code.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The file containing the code that attempted the DNS lookup.',
                    }),
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The process that attempted the DNS lookup.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host that attempted the DNS lookup.',
                    }),
                    # one of the following should be set...
                    ('a', ('inet:dns:a', {}), {
                        'ro': True,
                        'doc': 'The DNS A record returned by the lookup.',
                    }),
                    ('a:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its A record.',
                    }),
                    ('a:ipv4', ('inet:ipv4', {}), {
                        'ro': True,
                        'doc': 'The IPv4 address returend in the A record.',
                    }),
                    ('ns', ('inet:dns:ns', {}), {
                        'ro': True,
                        'doc': 'The DNS NS record returned by the lookup.',
                    }),
                    ('ns:zone', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its NS record.',
                    }),
                    ('ns:ns', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain returned in the NS record.',
                    }),
                    ('rev', ('inet:dns:rev', {}), {
                        'ro': True,
                        'doc': 'The DNS PTR record returned by the lookup.',
                    }),
                    ('rev:ipv4', ('inet:ipv4', {}), {
                        'ro': True,
                        'doc': 'The IPv4 address queried for its PTR record.',
                    }),
                    ('rev:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain returned in the PTR record.',
                    }),
                    ('aaaa', ('inet:dns:aaaa', {}), {
                        'ro': True,
                        'doc': 'The DNS AAAA record returned by the lookup.',
                    }),
                    ('aaaa:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its AAAA record.',
                    }),
                    ('aaaa:ipv6', ('inet:ipv6', {}), {
                        'ro': True,
                        'doc': 'The IPv6 address returned in the AAAA record.',
                    }),
                    ('rev6', ('inet:dns:rev6', {}), {
                        'ro': True,
                        'doc': 'The DNS PTR record returned by the lookup of a IPv6 address.',
                    }),
                    ('rev6:ipv6', ('inet:ipv6', {}), {
                        'ro': True,
                        'doc': 'The IPv6 address queried for its PTR record.',
                    }),
                    ('rev6:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain returned in the PTR record.',
                    }),
                    ('cname', ('inet:dns:cname', {}), {
                        'ro': True,
                        'doc': 'The DNS CNAME record returned by the lookup',
                    }),
                    ('cname:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its CNAME record.',
                    }),
                    ('cname:cname', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain returned in the CNAME record.',
                    }),
                    ('mx', ('inet:dns:mx', {}), {
                        'ro': True,
                        'doc': 'The DNS MX record returned by the lookup.',
                    }),
                    ('mx:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its MX record.',
                    }),
                    ('mx:mx', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain returned in the MX record.',
                    }),
                    ('soa', ('inet:dns:soa', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its SOA record.',
                    }),
                    ('soa:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its SOA record.',
                    }),
                    ('soa:ns', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain (MNAME) returned in the SOA record.',
                    }),
                    ('soa:email', ('inet:email', {}), {
                        'ro': True,
                        'doc': 'The normalized email address (RNAME) returned in the SOA record.',
                    }),
                    ('soa:serial', ('int', {}), {
                        'ro': True,
                        'doc': 'The SERIAL value returned in the SOA record.',
                    }),
                    ('soa:refresh', ('int', {}), {
                        'ro': True,
                        'doc': 'The REFRESH value returned in the SOA record.',
                    }),
                    ('soa:retry', ('int', {}), {
                        'ro': True,
                        'doc': 'The RETRY value returned in the SOA record.',
                    }),
                    ('soa:expire', ('int', {}), {
                        'ro': True,
                        'doc': 'The EXPIRE value returned in the SOA record.',
                    }),
                    ('soa:min', ('int', {}), {
                        'ro': True,
                        'doc': 'The MINIMUM value returned in the SOA record.',
                    }),
                    ('txt', ('inet:dns:txt', {}), {
                        'ro': True,
                        'doc': 'The DNS TXT record returned by the lookup.',
                    }),
                    ('txt:fqdn', ('inet:fqdn', {}), {
                        'ro': True,
                        'doc': 'The domain queried for its TXT record.',
                    }),
                    ('txt:txt', ('str', {}), {
                        'ro': True,
                        'doc': 'The string returned in the TXT record.',
                    }),
                )),
            )
        }
        name = 'inet:dns'
        return ((name, modl), )
