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
            )
        }
        omodl = {
            'types': (
                ('inet:dns:look', {
                    'subof': 'guid',
                    'doc': 'The instance (point-in-time) result of a DNS record lookup.'}),

                ('inet:dns:type', {'subof': 'str', 'lower': 1,
                    'enums': 'soa,ns,mx,a,aaaa,txt,srv,ptr,cname,hinfo,isdn',
                    'doc': 'A DNS request type enum'}),

                ('inet:dns:req', {'subof': 'comp', 'fields': 'client=inet:client,fqdn=inet:fqdn,type=inet:dns:type',
                    'doc': 'A fused DNS request record'}),
            ),

            'forms': (

                ('inet:dns:req', {'doc': 'Fused knowledge of a DNS request origin'}, [
                    ('client', {'ptype': 'inet:client', 'ro': 1, 'req': 1,
                        'doc': 'The inet:addr which requested the FQDN'}),
                    ('client:ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The IPv4 of the client.'}),
                    ('client:ipv6', {'ptype': 'inet:ipv6',
                        'doc': 'The IPv6 of the client.'}),
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1, 'req': 1,
                        'doc': 'The requested FQDN'}),
                    ('type', {'ptype': 'inet:dns:type', 'ro': 1, 'req': 1,
                        'doc': 'The type of DNS record requested'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest observed time that the address made the specified request.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent observed time that the address made the specified request.'}),
                ]),

                ('inet:dns:look', {'ptype': 'inet:dns:look', 'doc': 'Instance knowledge of a DNS record lookup.'}, [

                    ('time', {'ptype': 'time', 'ro': 1,
                        'doc': 'The date and time that the lookup occurred.'}),

                    ('ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The IPv4 address that requested the lookup.'}),

                    ('tcp4', {'ptype': 'inet:tcp4',
                        'doc': 'The IPv4/TCP server that responded to the lookup.'}),

                    ('tcp4:ipv4', {'ptype': 'inet:ipv4',
                        'doc': 'The IPv4 of the server that responded to the lookup.'}),

                    ('tcp4:port', {'ptype': 'inet:port',
                        'doc': 'The TCP port of the server that responded to the lookup.'}),

                    ('rcode', {'ptype': 'int',
                        'doc': 'The DNS server response code.'}),

                    ('udp4', {'ptype': 'inet:udp4',
                        'doc': 'The IPv4/UDP server that responded to the lookup.'}),
                    ('udp4:ipv4', {'ptype': 'inet:ipv4',
                                   'doc': 'The IPv4 of the server that responded to the lookup.'}),
                    ('udp4:port', {'ptype': 'inet:port',
                                   'doc': 'The UDP port of the server that responded to the lookup.'}),

                    ('exe', {'ptype': 'file:bytes',
                        'doc': 'The file containing the code that attempted the DNS lookup.'}),

                    ('proc', {'ptype': 'it:exec:proc',
                        'doc': 'The process that attempted the DNS lookup.'}),

                    ('host', {'ptype': 'it:host',
                        'doc': 'The host that attempted the DNS lookup.'}),

                    # one of the following should be set...
                    # FIXME define a way to add subfields to prop decl so we dont have to declare them all
                    ('a', {'ptype': 'inet:dns:a', 'ro': 1,
                        'doc': 'The DNS A record returned by the lookup.'}),
                    ('a:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain queried for its A record.'}),
                    ('a:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': ' The IPv4 address returned in the A record.'}),

                    ('ns', {'ptype': 'inet:dns:ns', 'ro': 1,
                        'doc': 'The DNS NS record returned by the lookup.'}),
                    ('ns:zone', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain queried for its NS record.'}),
                    ('ns:ns', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain returned in the NS record.'}),

                    ('rev', {'ptype': 'inet:dns:rev', 'ro': 1,
                        'doc': 'The DNS PTR record returned by the lookup.'}),
                    ('rev:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 address queried for its PTR record.'}),
                    ('rev:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                         'doc': 'The domain returned in the PTR record.'}),

                    ('aaaa', {'ptype': 'inet:dns:aaaa', 'ro': 1,
                        'doc': 'The DNS AAAA record returned by the lookup.'}),
                    ('aaaa:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain queried for its AAAA record.'}),
                    ('aaaa:ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                        'doc': 'The IPv6 address returned in the AAAA record.'}),

                    ('cname', {'ptype': 'inet:dns:cname', 'ro': 1,
                        'doc': 'The DNS CNAME record returned by the lookup.'}),
                    ('cname:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain queried for its CNAME record.'}),
                    ('cname:cname', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain returned in the CNAME record.'}),

                    ('mx', {'ptype': 'inet:dns:mx', 'ro': 1,
                        'doc': 'The DNS MX record returned by the lookup.'}),
                    ('mx:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain queried for its MX record.'}),
                    ('mx:mx', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain returned in the MX record.'}),

                    ('soa', {'ptype': 'inet:dns:soa', 'ro': 1,
                        'doc': 'The DNS SOA record returned by the lookup.'}),
                    ('soa:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain queried for its SOA record.'}),
                    ('soa:ns', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain (MNAME) returned in the SOA record.'}),
                    ('soa:email', {'ptype': 'inet:email', 'ro': 1,
                        'doc': 'The normalized email address (RNAME) returned in the SOA record.'}),
                    ('soa:serial', {'ptype': 'int', 'ro': 1,
                        'doc': 'The SERIAL value returned in the SOA record.'}),
                    ('soa:refresh', {'ptype': 'int', 'ro': 1,
                        'doc': 'The REFRESH value returned in the SOA record.'}),
                    ('soa:retry', {'ptype': 'int', 'ro': 1,
                        'doc': 'The RETRY value returned in the SOA record.'}),
                    ('soa:expire', {'ptype': 'int', 'ro': 1,
                        'doc': 'The EXPIRE value returned in the SOA record.'}),
                    ('soa:min', {'ptype': 'int', 'ro': 1,
                        'doc': 'The MINIMUM value returned in the SOA record.'}),

                    ('txt', {'ptype': 'inet:dns:txt', 'ro': 1,
                        'doc': 'The DNS TXT record returned by the lookup.'}),
                    ('txt:fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                        'doc': 'The domain queried for its TXT record.'}),
                    ('txt:txt', {'ptype': 'str', 'ro': 1,
                        'doc': 'The string returned in the TXT record.'}),
                ]),
            ),
        }
        name = 'inet:dns'
        return ((name, modl), )
