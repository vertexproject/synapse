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

# IANA DNS Resource Record (RR) TYPEs and QTYPEs.
dnsquerytypes = (
    (1, 'A'),
    (2, 'NS'),
    (3, 'MD'),
    (4, 'MF'),
    (5, 'CNAME'),
    (6, 'SOA'),
    (7, 'MB'),
    (8, 'MG'),
    (9, 'MR'),
    (10, 'NULL'),
    (11, 'WKS'),
    (12, 'PTR'),
    (13, 'HINFO'),
    (14, 'MINFO'),
    (15, 'MX'),
    (16, 'TXT'),
    (17, 'RP'),
    (18, 'AFSDB'),
    (19, 'X25'),
    (20, 'ISDN'),
    (21, 'RT'),
    (22, 'NSAP'),
    (23, 'NSAP-PTR'),
    (24, 'SIG'),
    (25, 'KEY'),
    (26, 'PX'),
    (27, 'GPOS'),
    (28, 'AAAA'),
    (29, 'LOC'),
    (30, 'NXT'),
    (31, 'EID'),
    (32, 'NIMLOC'),
    (33, 'SRV'),
    (34, 'ATMA'),
    (35, 'NAPTR'),
    (36, 'KX'),
    (37, 'CERT'),
    (38, 'A6'),
    (39, 'DNAME'),
    (40, 'SINK'),
    (41, 'OPT'),
    (42, 'APL'),
    (43, 'DS'),
    (44, 'SSHFP'),
    (45, 'IPSECKEY'),
    (46, 'RRSIG'),
    (47, 'NSEC'),
    (48, 'DNSKEY'),
    (49, 'DHCID'),
    (50, 'NSEC3'),
    (51, 'NSEC3PARAM'),
    (52, 'TLSA'),
    (53, 'SMIMEA'),
    (55, 'HIP'),
    (56, 'NINFO'),
    (57, 'RKEY'),
    (58, 'TALINK'),
    (59, 'CDS'),
    (60, 'CDNSKEY'),
    (61, 'OPENPGPKEY'),
    (62, 'CSYNC'),
    (63, 'ZONEMD'),
    (64, 'SVCB'),
    (65, 'HTTPS'),
    (99, 'SPF'),
    (100, 'UINFO'),
    (101, 'UID'),
    (102, 'GID'),
    (103, 'UNSPEC'),
    (104, 'NID'),
    (105, 'L32'),
    (106, 'L64'),
    (107, 'LP'),
    (108, 'EUI48'),
    (109, 'EUI64'),
    (249, 'TKEY'),
    (250, 'TSIG'),
    (251, 'IXFR'),
    (252, 'AXFR'),
    (253, 'MAILB'),
    (254, 'MAILA'),
    (255, 'ANY'),
    (256, 'URI'),
    (257, 'CAA'),
    (258, 'AVC'),
    (259, 'DOA'),
    (260, 'AMTRELAY'),
    (261, 'RESINFO'),
    (262, 'WALLET'),
    (263, 'CLA'),
    (264, 'IPN'),
    (32768, 'TA'),
    (32769, 'DLV'),
)

modeldefs = (
    {

        'interfaces': (
            ('inet:dns:record', {
                'doc': 'An interface for DNS records.'}),
        ),

        'types': (

            ('inet:dns:query:name', (
                    ('inet:fqdn', {}),
                    ('it:dev:str', {}),
                ), {
                'ex': 'vertex.link',
                'doc': 'A DNS query name.'}),

            ('inet:dns:a', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv4'))}), {
                'template': {'title': 'DNS A record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,1.2.3.4)',
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                        'doc': 'The domain queried for its DNS A record.'}),
                    ('ip', ('inet:ip', {}), {'computed': True,
                        'doc': 'The IPv4 address returned in the A record.',
                        'prevnames': ('ipv4',)}),
                ),
                'doc': 'The result of a DNS A record lookup.'}),

            ('inet:dns:aaaa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv6'))}), {
                'template': {'title': 'DNS AAAA record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,2607:f8b0:4004:809::200e)',
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                        'doc': 'The domain queried for its DNS AAAA record.'}),
                    ('ip', ('inet:ip', {}), {'computed': True,
                        'doc': 'The IPv6 address returned in the AAAA record.',
                        'prevnames': ('ipv6',)}),
                ),
                'doc': 'The result of a DNS AAAA record lookup.'}),

            ('inet:dns:rev', ('comp', {'fields': (('ip', 'inet:ip'), ('fqdn', 'inet:fqdn'))}), {
                'template': {'title': 'Reverse DNS record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(1.2.3.4,vertex.link)',
                'prevnames': ('inet:dns:rev6',),
                'props': (
                    ('ip', ('inet:ip', {}), {'computed': True,
                        'doc': 'The IP address queried for its DNS PTR record.',
                        'prevnames': ('ipv4', 'ipv6')}),

                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain returned in the PTR record.'}),
                ),
                'doc': 'The transformed result of a DNS PTR record lookup.'}),

            ('inet:dns:ns', ('comp', {'fields': (('zone', 'inet:fqdn'), ('ns', 'inet:fqdn'))}), {
                'template': {'title': 'DNS NS record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,ns.dnshost.com)',
                'props': (
                    ('zone', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain queried for its DNS NS record.'}),
                    ('ns', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain returned in the NS record.'}),
                ),
                'doc': 'The result of a DNS NS record lookup.'}),

            ('inet:dns:cname', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('cname', 'inet:fqdn'))}), {
                'template': {'title': 'DNS CNAME record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(foo.vertex.link,vertex.link)',
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain queried for its CNAME record.'}),
                    ('cname', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain returned in the CNAME record.'}),
                ),
                'doc': 'The result of a DNS CNAME record lookup.'}),

            ('inet:dns:mx', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('mx', 'inet:fqdn'))}), {
                'template': {'title': 'DNS MX record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(vertex.link,mail.vertex.link)',
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain queried for its MX record.'}),
                    ('mx', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain returned in the MX record.'}),
                ),
                'doc': 'The result of a DNS MX record lookup.'}),

            ('inet:dns:soa', ('guid', {}), {
                'template': {'title': 'DNS SOA record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {
                         'doc': 'The domain queried for its SOA record.'}),
                    ('ns', ('inet:fqdn', {}), {
                         'doc': 'The domain (MNAME) returned in the SOA record.'}),
                    ('email', ('inet:email', {}), {
                         'doc': 'The email address (RNAME) returned in the SOA record.'}),
                ),
                'doc': 'The result of a DNS SOA record lookup.'}),

            ('inet:dns:txt', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('text', 'text'))}), {
                'template': {'title': 'DNS TXT record'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('inet:dns:record', {}),
                ),
                'ex': '(hehe.vertex.link,"fancy TXT record")',
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                         'doc': 'The domain queried for its TXT record.'}),
                    ('text', ('text', {}), {'computed': True,
                         'doc': 'The string returned in the TXT record.'}),
                ),
                'doc': 'The result of a DNS TXT record lookup.'}),

            ('inet:dns:query',
                ('comp', {'fields': (('client', 'inet:client'), ('name', 'inet:dns:query:name'), ('type', 'inet:dns:query:type'))}), {
                    'template': {'title': 'DNS query'},
                    'interfaces': (
                        ('meta:observable', {}),
                    ),
                    'ex': '(1.2.3.4, woot.com, 1)',
                    'props': (

                        ('client', ('inet:client', {}), {
                            'computed': True,
                            'doc': 'The client that performed the DNS query.'}),

                        ('name', ('inet:dns:query:name', {}), {
                            'computed': True,
                            'doc': 'The DNS query name string.'}),

                        ('type', ('inet:dns:query:type', {}), {
                            'computed': True,
                            'doc': 'The type of record that was queried.'}),
                    ),
                    'doc': 'A DNS query unique to a given client.'}),

            ('inet:dns:request', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:request', {}),
                ),
                'props': (

                    ('query:name', ('inet:dns:query:name', {}), {
                        'doc': 'The DNS query name string in the request.'}),

                    ('query:type', ('inet:dns:query:type', {}), {
                        'doc': 'The type of record requested in the query.'}),

                    ('response', ('inet:dns:response', {}), {
                        'doc': 'The response sent by the DNS server.'}),
                ),
                'doc': 'A DNS protocol request.'}),

            ('inet:dns:response', ('guid', {}), {
                'interfaces': (
                    ('inet:proto:response', {}),
                ),
                'props': (

                    ('code', ('dns:reply:code', {}), {
                        'doc': 'The DNS server reply code.'}),

                    ('answers', ('inet:dns:answer', {}), {
                        'array': {},
                        'doc': 'The DNS answers included in the response.'}),
                ),
                'doc': 'A DNS protocol response.'}),

            ('inet:dns:answer', ('guid', {}), {
                'props': (

                    ('ttl', ('duration:seconds', {}), {
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


            ('inet:dns:wild:a', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))}), {
                'template': {'title': 'DNS wildcard A record'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                        'doc': 'The domain containing a wild card record.'}),
                    ('ip', ('inet:ip', {}), {'computed': True,
                        'doc': 'The IPv4 address returned by wild card resolutions.',
                        'prevnames': ('ipv4',)}),
                ),
                'doc': 'A DNS A wild card record and the IPv4 it resolves to.'}),

            ('inet:dns:wild:aaaa', ('comp', {'fields': (('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))}), {
                'template': {'title': 'DNS wildcard AAAA record'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'props': (
                    ('fqdn', ('inet:fqdn', {}), {'computed': True,
                        'doc': 'The domain containing a wild card record.'}),
                    ('ip', ('inet:ip', {}), {'computed': True,
                        'doc': 'The IPv6 address returned by wild card resolutions.',
                        'prevnames': ('ipv6',)}),
                ),
                'doc': 'A DNS AAAA wild card record and the IPv6 it resolves to.'}),

            ('inet:dns:dynreg', ('guid', {}), {
                'template': {'title': 'dynamic DNS registration'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'props': (

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
                ),
                'doc': 'A dynamic DNS registration.'}),

            ('dns:reply:code', ('int', {'enums': dnsreplycodes, 'enums:strict': False}), {
                'doc': 'A DNS reply code.'}),

            ('inet:dns:query:type', ('int', {'enums': dnsquerytypes, 'enums:strict': False}), {
                'doc': 'A DNS query type. The IANA assigned DNS record types are declared as enums.'}),

        ),
    },
)
