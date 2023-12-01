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
                  'returns': {'type': 'node', 'desc': 'An ou:org node with the given name.'}}},
        {'name': 'orgHqByName', 'desc': 'Returns a ps:contact node for the ou:org, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the org.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A ps:contact node for the ou:org with the given name.'}}},
        {'name': 'orgByFqdn', 'desc': 'Returns an ou:org node by FQDN, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'fqdn', 'type': 'str', 'desc': 'The FQDN of the org.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'An ou:org node with the given FQDN.'}}},
        {'name': 'industryByName', 'desc': 'Returns an ou:industry by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the industry.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'An ou:industry node with the given name.'}}},
        {'name': 'newsByUrl', 'desc': 'Returns a media:news node by URL, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'url', 'type': 'inet:url', 'desc': 'The URL where the news is published.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A media:news node with the given URL.'}}},
        {'name': 'softByName', 'desc': 'Returns it:prod:soft node by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the software.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'An it:prod:soft node with the given name.'}}},
        {'name': 'vulnByCve', 'desc': 'Returns risk:vuln node by CVE, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'cve', 'type': 'str', 'desc': 'The CVE id.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A risk:vuln node with the given CVE.'}}},

        {'name': 'riskThreat',
         'desc': 'Returns a risk:threat node based on the threat and reporter names, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The reported name of the threat cluster.'},
                      {'name': 'reporter', 'type': 'str', 'desc': 'The name of the organization which reported the threat cluster.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A risk:threat node.'}}},

        {'name': 'riskToolSoftware',
         'desc': 'Returns a risk:tool:software node based on the tool and reporter names, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The reported name of the tool.'},
                      {'name': 'reporter', 'type': 'str', 'desc': 'The name of the organization which reported the tool.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A risk:tool:software node.'}}},

        {'name': 'psContactByEmail', 'desc': 'Returns a ps:contact by deconflicting the type and email address.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'type', 'type': 'str', 'desc': 'The ps:contact:type property.'},
                      {'name': 'email', 'type': 'str', 'desc': 'The ps:contact:email property.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A ps:contact node.'}}},

        {'name': 'polCountryByIso2', 'desc': 'Returns a pol:country node by deconflicting the :iso2 property.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'iso2', 'type': 'str', 'desc': 'The pol:country:iso2 property.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A pol:country node.'}}},
        {'name': 'langByName', 'desc': 'Returns a lang:language node by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the language.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A lang:language node with the given name.'}}},
        {'name': 'langByCode', 'desc': 'Returns a lang:language node by language code, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The language code for the language.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A lang:language node with the given code.'}}},
    )
    _storm_lib_path = ('gen',)

    _storm_query = '''
        function orgIdType(name) {
            ou:id:type:name=$name
            return($node)

            [ ou:id:type=(gen, name, $name) :name=$name ]
            return($node)
        }

        function orgIdNumber(type, value) {
            $idtype = $orgIdType($type)

            ou:id:number=($idtype, $value)
            return($node)

            [ ou:id:number=($idtype, $value) ]
            return($node)
        }

        function orgByName(name, try=$lib.false) {
            if $try {
                ($ok, $name) = $lib.trycast(ou:name, $name)
                if (not $ok) { return() }
            } else {
                $name = $lib.cast(ou:name, $name)
            }

            ou:name=$name -> ou:org
            return($node)

            [ ou:org=(gen, name, $name) :name=$name ]
            return($node)
        }

        function orgByFqdn(fqdn, try=$lib.false) {
            if $try {
                ($ok, $fqdn) = $lib.trycast("inet:fqdn", $fqdn)
                if (not $ok) { return() }
            } else {
                $fqdn = $lib.cast(inet:fqdn, $fqdn)
            }

            inet:fqdn=$fqdn -> ou:org
            return($node)

            [ ou:org=(gen, fqdn, $fqdn) :dns:mx+=$fqdn ]
            return($node)
        }

        function orgHqByName(name) {
            yield $lib.gen.orgByName($name)
            $org=$node
            $name = :name

            { -:hq [ :hq = {[ ps:contact=(gen, hq, name, $name) :orgname=$name ]} ] }

            :hq -> ps:contact
            { -:org [ :org=$org ] }

            return($node)
        }

        function industryByName(name) {
            ou:industryname=$name -> ou:industry
            return($node)

            $name = $lib.cast(ou:industryname, $name)
            [ ou:industry=(gen, name, $name)  :name=$name ]
            return($node)
        }

        function newsByUrl(url, try=$lib.false) {
            if $try {
                ($ok, $url) = $lib.trycast(inet:url, $url)
                if (not $ok) { return() }
            } else {
                $url = $lib.cast(inet:url, $url)
            }

            media:news:url=$url
            return($node)

            [ media:news=(gen, url, $url) :url=$url ]
            return($node)
        }

        function softByName(name) {
            it:prod:softname=$name
            -> it:prod:soft
            return($node)

            $name = $lib.cast(it:prod:softname, $name)
            [ it:prod:soft=(gen, name, $name) :name=$name ]
            return($node)
        }

        function vulnByCve(cve, try=$lib.false) {
            if $try {
                ($ok, $cve) = $lib.trycast("it:sec:cve", $cve)
                if (not $ok) { return() }
            } else {
                $cve = $lib.cast(it:sec:cve, $cve)
            }

            risk:vuln:cve=$cve
            return($node)

            [ risk:vuln=(gen, cve, $cve) :cve=$cve ]
            return($node)
        }

        function riskThreat(name, reporter) {
            ou:name=$name
            tee { -> risk:threat:org:name } { -> risk:threat:org:names } |
            +:reporter:name=$reporter
            { -:reporter [ :reporter=$orgByName($reporter) ] }
            return($node)

            $name = $lib.cast(ou:name, $name)
            $reporter = $lib.cast(ou:name, $reporter)

            [ risk:threat=(gen, name, reporter, $name, $reporter)
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

            $name = $lib.cast(it:prod:softname, $name)
            $reporter = $lib.cast(ou:name, $reporter)

            [ risk:tool:software=(gen, $name, $reporter)
                :soft:name = $name
                :reporter:name = $reporter
                :reporter = { yield $orgByName($reporter) }
            ]

            return($node)
        }

        function psContactByEmail(type, email, try=$lib.false) {

            if $try {
                ($ok, $email) = $lib.trycast("inet:email", $email)
                if (not $ok) { return() }
            } else {
                $type = $lib.cast(ps:contact:type:taxonomy, $type)
                $email = $lib.cast(inet:email, $email)
            }

            ps:contact:email = $email
            +:type = $type
            return($node)

            [ ps:contact=(gen, type, email, $type, $email)
                :email = $email
                :type = $type
            ]
            return($node)
        }

        function polCountryByIso2(iso2, try=$lib.false) {
            if $try {
                ($ok, $iso2) = $lib.trycast("pol:iso2", $iso2)
                if (not $ok) { return() }
            } else {
                $iso2 = $lib.cast(pol:iso2, $iso2)
            }

            pol:country:iso2=$iso2
            return($node)

            [ pol:country=(gen, iso2, $iso2) :iso2=$iso2 ]
            return($node)
        }

        function polCountryOrgByIso2(iso2, try=$lib.false) {

            yield $lib.gen.polCountryByIso2($iso2, try=$try)

            { -:government [ :government = $lib.gen.orgByName(`{:iso2} government`) ] }
            :government -> ou:org
            return($node)
        }

        function langByName(name) {

            lang:name=$name -> lang:language
            return($node)

            $name = $lib.cast(lang:name, $name)
            [ lang:language=(gen, name, $name) :name=$name ]
            return($node)
        }

        function langByCode(code, try=$lib.false) {

            if $try {
                ($ok, $code) = $lib.trycast(lang:code, $code)
                if (not $ok) { return() }
            } else {
                $code = $lib.cast(lang:code, $code)
            }

            lang:language:code=$code
            return($node)

            [ lang:language=(bycode, $code) :code=$code ]
            return($node)
        }

        function campaign(name, reporter) {

            ou:campname = $name -> ou:campaign +:reporter:name=$reporter
            return($node)

            $name = $lib.cast(ou:campname, $name)
            $reporter = $lib.cast(ou:name, $reporter)

            [ ou:campaign=(gen, name, reporter, $name, $reporter) :name=$name :reporter:name=$reporter ]
            return($node)
        }
    '''

stormcmds = (

    {
        'name': 'gen.ou.id.number',
        'descr': 'Lift (or create) an ou:id:number node based on the organization ID type and value.',
        'cmdargs': (
            ('type', {'help': 'The type of the organization ID.'}),
            ('value', {'help': 'The value of the organization ID.'}),
        ),
        'storm': 'yield $lib.gen.orgIdNumber($cmdopts.type, $cmdopts.value)',
    },
    {
        'name': 'gen.ou.id.type',
        'descr': 'Lift (or create) an ou:id:type node based on the name of the type.',
        'cmdargs': (
            ('name', {'help': 'The friendly name of the organization ID type.'}),
        ),
        'storm': 'yield $lib.gen.orgIdType($cmdopts.name)',
    },
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
        'storm': 'yield $lib.gen.orgHqByName($cmdopts.name)',
    },
    {
        'name': 'gen.ou.campaign',
        'descr': 'Lift or create an ou:campaign based on the name and reporting organization.',
        'cmdargs': (
            ('name', {'help': 'The name of the campaign.'}),
            ('reporter', {'help': 'The name of the reporting organization.'}),
        ),
        'storm': 'yield $lib.gen.campaign($cmdopts.name, $cmdopts.reporter)',
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
            ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
                       'action': 'store_true'}),
        ),
        'storm': 'yield $lib.gen.vulnByCve($cmdopts.cve, try=$cmdopts.try)',
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
            ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
                       'action': 'store_true'}),
        ),
        'storm': 'yield $lib.gen.polCountryByIso2($cmdopts.iso2, try=$cmdopts.try)',
    },
    {
        'name': 'gen.pol.country.government',
        'descr': '''
            Lift (or create) the ou:org node representing a country's government based on the 2 letter ISO-3166 country code.

            Examples:

                // Yield the ou:org node which represents the Government of Ukraine.
                gen.pol.country.government ua
        ''',
        'cmdargs': (
            ('iso2', {'help': 'The 2 letter ISO-3166 country code.'}),
            ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
                       'action': 'store_true'}),
        ),
        'storm': 'yield $lib.gen.polCountryOrgByIso2($cmdopts.iso2, try=$cmdopts.try)',
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
            ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
                       'action': 'store_true'}),
        ),
        'storm': 'yield $lib.gen.psContactByEmail($cmdopts.type, $cmdopts.email, try=$cmdopts.try)',
    },
    {
        'name': 'gen.lang.language',
        'descr': 'Lift (or create) a lang:language node based on the name.',
        'cmdargs': (
            ('name', {'help': 'The name of the language.'}),
        ),
        'storm': 'yield $lib.gen.langByName($cmdopts.name)',
    },
)
