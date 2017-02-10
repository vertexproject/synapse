
def getDataModel():
    return {
        'prefix':'inet:dns',
        'version':201611301619,

        'types':(
            ('inet:dns:look',{'subof':'guid'}),
            ('inet:dns:a',{'subof':'sepr','sep':'/','fields':'fqdn,inet:fqdn|ipv4,inet:ipv4',
                      'ex':'vertex.link/1.2.3.4','doc':'The result of a DNS A record lookup'}),
            ('inet:dns:ns',{'subof':'sepr','sep':'/','fields':'zone,inet:fqdn|ns,inet:fqdn',
                       'ex':'vertex.link/ns.dnshost.com','doc':'The result of a DNS NS record lookup'}),
            ('inet:dns:rev',{'subof':'sepr','sep':'/','fields':'ipv4,inet:ipv4|fqdn,inet:fqdn',
                        'ex':'1.2.3.4/vertex.link','doc':'The transformed result of a DNS PTR record lookup'}),
            ('inet:dns:aaaa',{'subof':'sepr','sep':'/','fields':'fqdn,inet:fqdn|ipv6,inet:ipv6',
                         'ex':'vertex.link/2607:f8b0:4004:809::200e','doc':'The result of a DNS AAAA record lookup'}),
        ),

        'forms':(
            ('inet:dns:a',{'ptype':'inet:dns:a','doc':'One-time-knowledge represenation of a DNS A record'},[
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('ipv4',{'ptype':'inet:ipv4'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('inet:dns:ns',{'ptype':'inet:dns:ns','doc':'One-time-knowledge represenation of a DNS NS record'},[
                ('ns',{'ptype':'inet:fqdn'}),
                ('zone',{'ptype':'inet:fqdn'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('inet:dns:rev',{'ptype':'inet:dns:rev','doc':'One-time-knowledge represenation of a DNS PTR reverse'},[
                ('ipv4',{'ptype':'inet:ipv4'}),
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('inet:dns:aaaa',{'ptype':'inet:dns:aaaa','doc':'One-time-knowledge represenation of a DNS AAAA record'},[
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('ipv6',{'ptype':'inet:ipv6'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),

            ('inet:dns:look',{'ptype':'inet:dns:look','doc':'Occurance knowledge of a DNS record lookup'},[
                ('time',{'ptype':'time','req':1}),
                # one of the following should be set...
                # FIXME define a way to add subfields to prop decl so we dont have to declare them all
                ('a',{'ptype':'inet:dns:a'}),
                ('a:fqdn',{'ptype':'inet:fqdn'}),
                ('a:ipv4',{'ptype':'inet:ipv4'}),

                ('ns',{'ptype':'inet:dns:ns'}),
                ('ns:ns',{'ptype':'inet:fqdn'}),
                ('ns:zone',{'ptype':'inet:fqdn'}),

                ('rev',{'ptype':'inet:dns:rev'}),
                ('rev:ipv4',{'ptype':'inet:ipv4'}),
                ('rev:fqdn',{'ptype':'inet:fqdn'}),

                ('aaaa',{'ptype':'inet:dns:aaaa'}),
                ('aaaa:fqdn',{'ptype':'inet:fqdn'}),
                ('aaaa:ipv6',{'ptype':'inet:ipv6'}),
            ]),
        ),
    }
