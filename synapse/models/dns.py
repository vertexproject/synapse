
def getDataModel():
    return {
        'prefix':'dns',
        'version':201611301619,

        'types':(
            ('dns:look',{'subof':'guid'}),
            ('dns:a',{'subof':'sepr','sep':'/','fields':'fqdn,inet:fqdn|ipv4,inet:ipv4'}),
            ('dns:ns',{'subof':'sepr','sep':'/','fields':'zone,inet:fqdn|ns,inet:fqdn'}),
            ('dns:rev',{'subof':'sepr','sep':'/','fields':'ipv4,inet:ipv4|fqdn,inet:fqdn'}),
            ('dns:aaaa',{'subof':'sepr','sep':'/','fields':'fqdn,inet:fqdn|ipv6,inet:ipv6'}),
        ),

        'forms':(
            ('dns:a',{'ptype':'dns:a','doc':'One-time-knowledge represenation of a DNS A record'},[
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('ipv4',{'ptype':'inet:ipv4'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('dns:ns',{'ptype':'dns:ns','doc':'One-time-knowledge represenation of a DNS NS record'},[
                ('ns',{'ptype':'inet:fqdn'}),
                ('zone',{'ptype':'inet:fqdn'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('dns:rev',{'ptype':'dns:rev','doc':'One-time-knowledge represenation of a DNS PTR reverse'},[
                ('ipv4',{'ptype':'inet:ipv4'}),
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('dns:aaaa',{'ptype':'dns:aaaa','doc':'One-time-knowledge represenation of a DNS AAAA record'},[
                ('fqdn',{'ptype':'inet:fqdn'}),
                ('ipv6',{'ptype':'inet:ipv6'}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),

            ('dns:look',{'ptype':'dns:look','doc':'Occurance knowledge of a DNS record lookup'},[
                ('time',{'ptype':'time','req':1}),
                # one of the following should be set...
                # FIXME define a way to add subfields to prop decl so we dont have to declare them all
                ('a',{'ptype':'dns:a'}),
                ('a:fqdn',{'ptype':'inet:fqdn'}),
                ('a:ipv4',{'ptype':'inet:ipv4'}),

                ('ns',{'ptype':'dns:ns'}),
                ('ns:ns',{'ptype':'inet:fqdn'}),
                ('ns:zone',{'ptype':'inet:fqdn'}),

                ('rev',{'ptype':'dns:rev'}),
                ('rev:ipv4',{'ptype':'inet:ipv4'}),
                ('rev:fqdn',{'ptype':'inet:fqdn'}),

                ('aaaa',{'ptype':'dns:aaaa'}),
                ('aaaa:fqdn',{'ptype':'inet:fqdn'}),
                ('aaaa:ipv6',{'ptype':'inet:ipv6'}),
            ]),
        ),
    }
