from synapse.lib.module import CoreModule, modelrev

class DnsMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('inet:dns:look', {
                    'subof': 'guid',
                    'doc': 'The instance (point-in-time) result of a DNS record lookup'}),

                ('inet:dns:a', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'fqdn,inet:fqdn|ipv4,inet:ipv4',
                    'doc': 'The result of a DNS A record lookup',
                    'ex': 'vertex.link/1.2.3.4'}),

                ('inet:dns:ns', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'zone,inet:fqdn|ns,inet:fqdn',
                    'doc': 'The result of a DNS NS record lookup',
                    'ex': 'vertex.link/ns.dnshost.com'}),

                ('inet:dns:rev', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'ipv4,inet:ipv4|fqdn,inet:fqdn',
                    'doc': 'The transformed result of a DNS PTR record lookup',
                    'ex': '1.2.3.4/vertex.link'}),

                ('inet:dns:aaaa', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'fqdn,inet:fqdn|ipv6,inet:ipv6',
                    'doc': 'The result of a DNS AAAA record lookup',
                    'ex': 'vertex.link/2607:f8b0:4004:809::200e'}),
            ),

            'forms': (
                ('inet:dns:a', {'ptype': 'inet:dns:a', 'doc': 'Fused knowledge of a DNS A record'}, [
                    ('fqdn', {'ptype': 'inet:fqdn', 'doc': 'The domain queried for its DNS A record', 'ro': 1}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 address returned in the DNS A record', 'ro': 1}),
                    ('seen:min', {'ptype': 'time:min',
                                  'doc': 'The earliest observed time for the data in the A record'}),
                    ('seen:max', {'ptype': 'time:max',
                                  'doc': 'The most recent observed time for the data in the A record'}),
                ]),

                ('inet:dns:ns', {'ptype': 'inet:dns:ns', 'doc': 'Fused knowledge of a DNS NS record'}, [
                    ('zone', {'ptype': 'inet:fqdn', 'doc': 'The domain queried for its DNS NS record', 'ro': 1}),
                    ('ns', {'ptype': 'inet:fqdn', 'doc': 'The domain returned in the DNS NS record', 'ro': 1}),
                    ('seen:min', {'ptype': 'time:min',
                                  'doc': 'The earliest observed time for the data in the NS record'}),
                    ('seen:max', {'ptype': 'time:max',
                                  'doc': 'The most recent observed time for the data in the NS record'}),
                ]),

                ('inet:dns:rev', {'ptype': 'inet:dns:rev', 'doc': 'Fused knowledge of a DNS PTR record'}, [
                     ('ipv4', {'ptype': 'inet:ipv4',
                               'doc': 'The IPv4 address queried for its DNS PTR record', 'ro': 1}),
                     ('fqdn', {'ptype': 'inet:fqdn', 'doc': 'The domain returned in the DNS PTR record', 'ro': 1}),
                     ('seen:min', {'ptype': 'time:min',
                                   'doc': 'The earliest observed time for the data in the PTR record'}),
                     ('seen:max', {'ptype': 'time:max',
                                   'doc': 'The most recent observed time for the data in the PTR record'}),
                 ]),

                ('inet:dns:aaaa', {'ptype': 'inet:dns:aaaa', 'doc': 'Fused knowledge of a DNS AAAA record'}, [
                     ('fqdn', {'ptype': 'inet:fqdn', 'doc': 'The domain queried for its DNS AAAA record', 'ro': 1}),
                     ('ipv6', {'ptype': 'inet:ipv6',
                               'doc': 'The IPv6 address returned in the DNS AAAA record', 'ro': 1}),
                     ('seen:min', {'ptype': 'time:min',
                                   'doc': 'The earliest observed time for the data in the DNS AAAA record'}),
                     ('seen:max', {'ptype': 'time:max',
                                   'doc': 'The most recent observed time for the data in the DNS AAAA record'}),
                 ]),

                ('inet:dns:look', {'ptype': 'inet:dns:look', 'doc': 'Instance knowledge of a DNS record lookup'}, [
                    ('time', {'ptype': 'time', 'req': 1, 'ro': 1}),
                    # one of the following should be set...
                    # FIXME define a way to add subfields to prop decl so we dont have to declare them all
                    ('a', {'ptype': 'inet:dns:a', 'doc': 'The DNS A record returned by the lookup', 'ro': 1}),
                    ('a:fqdn', {'ptype': 'inet:fqdn', 'doc': 'The domain queried for its DNS A record', 'ro': 1}),
                    ('a:ipv4', {'ptype': 'inet:ipv4', 'doc': ' The IPv4 address returned in the DNS A record',
                                'ro': 1}),

                    ('ns', {'ptype': 'inet:dns:ns', 'doc': 'The DNS NS record returned by the lookup', 'ro': 1}),
                    ('ns:zone', {'ptype': 'inet:fqdn', 'doc': 'The domain queried for its DNS NS record', 'ro': 1}),
                    ('ns:ns', {'ptype': 'inet:fqdn', 'doc': 'The domain returned in the DNS NS record', 'ro': 1}),

                    ('rev', {'ptype': 'inet:dns:rev', 'doc': 'The DNS PTR record returned by the lookup', 'ro': 1}),
                    ('rev:ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 address queried for its DNS PTR record',
                                  'ro': 1}),
                    ('rev:fqdn', {'ptype': 'inet:fqdn', 'doc': 'The domain returned in the DNS PTR record',
                                  'ro': 1}),

                    ('aaaa', {'ptype': 'inet:dns:aaaa', 'doc': 'The DNS AAAA record returned by the lookup',
                              'ro': 1}),
                    ('aaaa:fqdn', {'ptype': 'inet:fqdn', 'doc': 'The domain queried for its DNS AAAA record',
                                   'ro': 1}),
                    ('aaaa:ipv6', {'ptype': 'inet:ipv6', 'doc': 'The IPv6 address returned in the DNS AAAA record',
                                   'ro': 1}),

                ]),
            ),
        }
        name = 'inet:dns'
        return ((name, modl), )
