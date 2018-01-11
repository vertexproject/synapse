from synapse.lib.module import CoreModule, modelrev

class DnsMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('inet:dns:look', {
                    'subof': 'guid',
                    'doc': 'The instance (point-in-time) result of a DNS record lookup.'}),

                ('inet:dns:a', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'fqdn,inet:fqdn|ipv4,inet:ipv4',
                    'doc': 'The result of a DNS A record lookup.',
                    'ex': 'vertex.link/1.2.3.4'}),

                ('inet:dns:ns', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'zone,inet:fqdn|ns,inet:fqdn',
                    'doc': 'The result of a DNS NS record lookup.',
                    'ex': 'vertex.link/ns.dnshost.com'}),

                ('inet:dns:rev', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'ipv4,inet:ipv4|fqdn,inet:fqdn',
                    'doc': 'The transformed result of a DNS PTR record lookup.',
                    'ex': '1.2.3.4/vertex.link'}),

                ('inet:dns:rev6', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'ipv6,inet:ipv6|fqdn,inet:fqdn',
                    'doc': 'The transformed result of a DNS PTR record for an IPv6 address.',
                    'ex': '2607:f8b0:4004:809::200e/vertex.link'}),

                ('inet:dns:aaaa', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'fqdn,inet:fqdn|ipv6,inet:ipv6',
                    'doc': 'The result of a DNS AAAA record lookup.',
                    'ex': 'vertex.link/2607:f8b0:4004:809::200e'}),

                ('inet:dns:cname', {
                     'subof': 'sepr',
                     'sep': '/',
                     'fields': 'fqdn,inet:fqdn|cname,inet:fqdn',
                     'doc': 'The result of a DNS CNAME record lookup.',
                     'ex': 'foo.vertex.link/vertex.link'}),

                ('inet:dns:mx', {
                     'subof': 'sepr',
                     'sep': '/',
                     'fields': 'fqdn,inet:fqdn|mx,inet:fqdn',
                     'doc': 'The result of a DNS MX record lookup.',
                     'ex': 'vertex.link/mail.vertex.link'}),

                ('inet:dns:soa', {
                     'subof': 'comp',
                     'fields': 'fqdn=inet:fqdn',
                     'optfields': 'ns=inet:fqdn,email=inet:email',
                     'doc': 'The result of a DNS SOA record lookup.'}),

                ('inet:dns:txt', {
                     'subof': 'comp',
                     'fields': 'fqdn=inet:fqdn,txt=str',
                     'doc': 'The result of a DNS TXT record lookup.'}),

                ('inet:dns:type', {'subof': 'str', 'lower': 1,
                    'enums': 'soa,ns,mx,a,aaaa,txt,srv,ptr,cname,hinfo,isdn',
                    'doc': 'A DNS request type enum'}),

                ('inet:dns:req', {'subof': 'comp', 'fields': 'addr=inet:addr,fqdn=inet:fqdn,type=inet:dns:type',
                    'doc': 'A fused DNS request record'}),
            ),

            'forms': (
                ('inet:dns:a', {'ptype': 'inet:dns:a', 'doc': 'Fused knowledge of a DNS A record.'}, [
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain queried for its DNS A record.'}),
                      ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                          'doc': 'The IPv4 address returned in the A record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the A record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the A record.'}),
                ]),

                ('inet:dns:ns',
                   {'ptype': 'inet:dns:ns', 'doc': 'Fused knowledge of a DNS NS record.'}, [
                      ('zone', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain queried for its DNS NS record.'}),
                      ('ns', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain returned in the NS record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the NS record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the NS record.'}),
                ]),

                ('inet:dns:rev',
                   {'ptype': 'inet:dns:rev', 'doc': 'Fused knowledge of a DNS PTR record.'}, [
                      ('ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                          'doc': 'The IPv4 address queried for its DNS PTR record.'}),
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain returned in the PTR record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the PTR record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the PTR record.'}),
                 ]),

                ('inet:dns:req', {'doc': 'Fused knowledge of a DNS request origin'}, [
                    ('addr', {'ptype': 'inet:addr', 'ro': 1, 'req': 1,
                        'doc': 'The IPv4 address which requested the FQDN'}),
                    ('addr:ipv4', {'ptype': 'inet:ipv4', 'ro': 1,
                        'doc': 'The IPv4 address which requested the FQDN'}),
                    ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1, 'req': 1,
                        'doc': 'The requested FQDN'}),
                    ('type', {'ptype': 'inet:dns:type', 'ro': 1, 'req': 1,
                        'doc': 'The type of DNS record requested'}),
                ]),

                ('inet:dns:rev6',
                   {'ptype': 'inet:dns:rev6', 'doc': 'Fused knowledge of a DNS PTR record for IPv6.'}, [
                      ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                          'doc': 'The IPv6 address queried for its DNS PTR record.'}),
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain returned in the PTR record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the PTR record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the PTR record.'}),
                 ]),

                ('inet:dns:aaaa',
                   {'ptype': 'inet:dns:aaaa', 'doc': 'Fused knowledge of a DNS AAAA record.'}, [
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain queried for its DNS AAAA record.'}),
                      ('ipv6', {'ptype': 'inet:ipv6', 'ro': 1,
                          'doc': 'The IPv6 address returned in the AAAA record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the AAAA record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the AAAA record.'}),
                 ]),

                ('inet:dns:cname',
                   {'ptype': 'inet:dns:cname', 'doc': 'Consolidated knowledge of a DNS CNAME record.'}, [
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain queried for its CNAME record.'}),
                      ('cname', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain returned in the CNAME record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the CNAME record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the CNAME record.'}),
                ]),

                ('inet:dns:mx',
                   {'ptype': 'inet:dns:mx', 'doc': 'Consolidated knowledge of a DNS MX record.'}, [
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain queried for its MX record.'}),
                      ('mx', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain returned in the MX record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the MX record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the MX record.'}),
                ]),

                ('inet:dns:soa',
                   {'ptype': 'inet:dns:soa', 'doc': 'Consolidated knowledge of a DNS SOA record.'}, [
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain queried for its SOA record.'}),
                      ('ns', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain (MNAME) returned in the SOA record'}),
                      ('email', {'ptype': 'inet:email', 'ro': 1,
                          'doc': 'The email address (RNAME) returned in the SOA record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the SOA record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the SOA record.'}),
                ]),

                #TXT records may have different formats (freeform, attribute=value, used for special purposes like
                #Sender Policy Framework, DKIM, etc. Those are not taken into account here except as raw strings.

                ('inet:dns:txt',
                   {'ptype': 'inet:dns:txt', 'doc': 'Consolidated knowledge of a DNS TXT record.'}, [
                      ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1,
                          'doc': 'The domain queried for its TXT record.'}),
                      ('txt', {'ptype': 'str', 'ro': 1,
                          'doc': 'The string returned in the TXT record.'}),
                      ('seen:min', {'ptype': 'time:min',
                          'doc': 'The earliest observed time for the data in the TXT record.'}),
                      ('seen:max', {'ptype': 'time:max',
                          'doc': 'The most recent observed time for the data in the TXT record.'}),
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
