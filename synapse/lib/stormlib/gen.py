import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibGen(s_stormtypes.Lib):
    '''
    A Storm Library for secondary property based deconfliction.
    '''
    _storm_locals = (
        {'name': 'orgByName', 'desc': 'Returns an ou:org by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the org.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'An ou:org node with the given name.'}}},
        {'name': 'orgByFqdn', 'desc': 'Returns an ou:org node by FQDN, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'fqdn', 'type': 'str', 'desc': 'The FQDN of the org.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'An ou:org node with the given FQDN.'}}},
        {'name': 'industryByName', 'desc': 'Returns an ou:industry by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the industry.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'An ou:industry node with the given name.'}}},
        {'name': 'newsByUrl', 'desc': 'Returns a media:news node by URL, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'url', 'type': 'inet:url', 'desc': 'The URL where the news is published.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'A media:news node with the given URL.'}}},
        {'name': 'softByName', 'desc': 'Returns it:prod:soft node by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the software.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'An it:prod:soft node with the given name.'}}},
        {'name': 'vulnByCve', 'desc': 'Returns risk:vuln node by CVE, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'cve', 'type': 'str', 'desc': 'The CVE id.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'A risk:vuln node with the given CVE.'}}},

        {'name': 'riskThreat',
         'desc': 'Returns a risk:threat node based on the threat and reporter names, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The reported name of the threat cluster.'},
                      {'name': 'reporter', 'type': 'str', 'desc': 'The name of the organization which reported the threat cluster.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'A risk:threat node.'}}},

        {'name': 'riskToolSoftware',
         'desc': 'Returns a risk:tool:software node based on the tool and reporter names, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The reported name of the tool.'},
                      {'name': 'reporter', 'type': 'str', 'desc': 'The name of the organization which reported the tool.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'A risk:tool:software node.'}}},

        {'name': 'psContactByEmail', 'desc': 'Returns a ps:contact by deconflicting the type and email address.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'type', 'type': 'str', 'desc': 'The ps:contact:type property.'},
                      {'name': 'email', 'type': 'str', 'desc': 'The ps:contact:email property.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'A ps:contact node.'}}},

        {'name': 'polCountryByIso2', 'desc': 'Returns a pol:country node by deconflicting the :iso2 property.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'iso2', 'type': 'str', 'desc': 'The pol:country:iso2 property.'},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'A pol:country node.'}}},
    )
    _storm_lib_path = ('gen',)

    _storm_query = '''
        function orgByName(name) {
            ou:name=$name -> ou:org
            return($node)
            [ ou:org=* :name=$name ]
            return($node)
        }

        function orgByFqdn(fqdn) {
            inet:fqdn=$fqdn -> ou:org
            return($node)
            [ ou:org=* :dns:mx+=$fqdn ]
            return($node)
        }

        function industryByName(name) {
            ou:industryname=$name -> ou:industry
            return($node)
            [ ou:industry=* :name=$name ]
            return($node)
        }

        function newsByUrl(url) {
            media:news:url=$url
            return($node)
            [ media:news=* :url=$url ]
            return($node)
        }

        function softByName(name) {
            it:prod:softname=$name
            -> it:prod:soft
            return($node)
            [ it:prod:soft=* :name=$name ]
            return($node)
        }

        function vulnByCve(cve) {
            risk:vuln:cve=$cve
            return($node)
            [ risk:vuln=* :cve=$cve ]
            return($node)
        }

        function riskThreat(name, reporter) {
            ou:name=$name
            tee { -> risk:threat:org:name } { -> risk:threat:org:names } |
            +:reporter:name=$reporter
            { -:reporter [ :reporter=$orgByName($reporter) ] }
            return($node)

            [ risk:threat=*
                :org:name=$name
                :reporter = { yield $orgByName($reporter) }
                :reporter:name = $reporter
            ]
            return($node)
        }

        function riskToolSoftware(name, reporter) {

            it:prod:softname = $name
            -> risk:tool:software
            +:reporter:name = $reporter
            { -:reporter [ :reporter=$orgByName($reporter) ] }
            return($node)

            [ risk:tool:software=*
                :soft:name = $name
                :reporter:name = $reporter
                :reporter = { yield $orgByName($reporter) }
            ]

            return($node)
        }

        function psContactByEmail(type, email) {
            ps:contact:email = $email
            +:type = $type
            return($node)
            [ ps:contact=*
                :email = $email
                :type = $type
            ]
            return($node)
        }

        function polCountryByIso2(iso2) {
            pol:country:iso2=$iso2
            return($node)
            [ pol:country=* :iso2=$iso2 ]
            return($node)
        }
    '''

stormcmds = (

    {
        'name': 'gen.ou.org',
        'descr': 'Lift (or create) an ou:org node based on the organization name.',
        'cmdargs': (
            ('name', {'help': 'The name of the organization.'}),
        ),
        'storm': 'yield $lib.gen.orgByName($cmdopts.name)',
    },
    {
        'name': 'gen.ou.org.hq',
        'descr': 'Lift (or create) the primary ps:contact node for the ou:org based on the organization name.',
        'cmdargs': (
            ('name', {'help': 'The name of the organization.'}),
        ),
        'storm': '''
            yield $lib.gen.orgByName($cmdopts.name)
            { -:hq [ :hq = {[ ps:contact=* :orgname=$cmdopts.name ]} ] }
            :hq -> ps:contact
        '''
    },
    {
        'name': 'gen.it.prod.soft',
        'descr': 'Lift (or create) an it:prod:soft node based on the software name.',
        'cmdargs': (
            ('name', {'help': 'The name of the software.'}),
        ),
        'storm': 'yield $lib.gen.softByName($cmdopts.name)',
    },
    {
        'name': 'gen.risk.threat',
        'descr': '''
            Lift (or create) a risk:threat node based on the threat name and reporter name.

            Examples:

                // Yield a risk:threat node for the threat cluster "APT1" reported by "Mandiant".
                gen.risk.threat apt1 mandiant
        ''',
        'cmdargs': (
            ('name', {'help': 'The name of the threat cluster. For example: APT1'}),
            ('reporter', {'help': 'The name of the reporting organization. For example: Mandiant'}),
        ),
        'storm': 'yield $lib.gen.riskThreat($cmdopts.name, $cmdopts.reporter)',
    },
    {
        'name': 'gen.risk.tool.software',
        'descr': '''
            Lift (or create) a risk:tool:software node based on the tool name and reporter name.

            Examples:

                // Yield a risk:tool:software node for the "redtree" tool reported by "vertex".
                gen.risk.tool.software redtree vertex
        ''',
        'cmdargs': (
            ('name', {'help': 'The tool name.'}),
            ('reporter', {'help': 'The name of the reporting organization. For example: "recorded future"'}),
        ),
        'storm': 'yield $lib.gen.riskToolSoftware($cmdopts.name, $cmdopts.reporter)',
    },
    {
        'name': 'gen.risk.vuln',
        'descr': '''
            Lift (or create) a risk:vuln node based on the CVE.
        ''',
        'cmdargs': (
            ('cve', {'help': 'The CVE identifier.'}),
        ),
        'storm': 'yield $lib.gen.vulnByCve($cmdopts.cve)',
    },
    {
        'name': 'gen.ou.industry',
        'descr': '''
            Lift (or create) an ou:industry node based on the industry name.
        ''',
        'cmdargs': (
            ('name', {'help': 'The industry name.'}),
        ),
        'storm': 'yield $lib.gen.industryByName($cmdopts.name)',
    },
    {
        'name': 'gen.pol.country',
        'descr': '''
            Lift (or create) a pol:country node based on the 2 letter ISO-3166 country code.

            Examples:

                // Yield the pol:country node which represents the country of Ukraine.
                gen.pol.country ua
        ''',
        'cmdargs': (
            ('iso2', {'help': 'The 2 letter ISO-3166 country code.'}),
        ),
        'storm': 'yield $lib.gen.polCountryByIso2($cmdopts.iso2)',
    },
    {
        'name': 'gen.pol.country.government',
        'descr': '''
            Lift (or create) the ou:org node representing a country's
            government based on the 2 letter ISO-3166 country code.

            Examples:

                // Yield the ou:org node which represents the Government of Ukraine.
                gen.pol.country.government ua
        ''',
        'cmdargs': (
            ('iso2', {'help': 'The 2 letter ISO-3166 country code.'}),
        ),
        'storm': '''
            yield $lib.gen.polCountryByIso2($cmdopts.iso2)
            { -:government [ :government = $lib.gen.orgByName(`{$cmdopts.iso2} government`) ] }
            :government -> ou:org
        ''',
    },
    {
        'name': 'gen.ps.contact.email',
        'descr': '''
            Lift (or create) the ps:contact node by deconflicting the email and type.

            Examples:

                // Yield the ps:contact node for the type and email
                gen.ps.contact.email vertex.employee visi@vertex.link
        ''',
        'cmdargs': (
            ('type', {'help': 'The contact type.'}),
            ('email', {'help': 'The contact email address.'}),
        ),
        'storm': 'yield $lib.gen.psContactByEmail($cmdopts.type, $cmdopts.email)',
    },
)
