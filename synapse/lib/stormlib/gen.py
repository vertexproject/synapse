import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibGen(s_stormtypes.Lib):
    '''
    A Storm Library for secondary property based deconfliction.
    '''
    _storm_lib_path = ('gen',)

    _storm_query = '''
        function _tryGutor(form, ctor, try) {
            if $try {
                return({[ *$form?=$ctor ]})
            }
            return({[ *$form=$ctor ]})
        }

        function _ouOrgByName(name, try=(false)) {
            $ctor = ({
                "name": $name,
            })
            return($_tryGutor(ou:org, $ctor, $try))
        }

        function _countryByCode(code, try=(false)) {
            $ctor = ({
                "code": $code,
            })
            return($_tryGutor(pol:country, $ctor, $try))
        }

        function _governmentByCode(code, try=(false)) {
            yield $_countryByCode($code, try=$try)
            [ :government*unset=$_ouOrgByName(`{:code} government`) ]
            :government -> ou:org
            return($node)
        }

        function _vulnByCve(cve, reporter, try=(false)) {
            if $try {
                $cve = {[ it:sec:cve?=$cve ]}
                if ($cve = null) { return() }
            } else {
                $cve = {[ it:sec:cve=$cve ]}
            }

            $ctor = ({
                "id": $cve,
                "reporter:name": $reporter,
            })

            return($_tryGutor(risk:vuln, $ctor, $try))
        }
    '''


_tryarg = ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
          'action': 'store_true'})
stormcmds = (

    {
        'name': 'gen.org',
        'descr': 'Lift (or create) an ou:org node based on the organization name.',
        'cmdargs': (
            ('name', {'help': 'The name of the organization.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._ouOrgByName($cmdopts.name, try=$cmdopts.try)',
    },
    {
        'name': 'gen.campaign',
        'descr': 'Lift (or create) an entity:campaign based on the name and reporter.',
        'cmdargs': (
            ('name', {'help': 'The name of the campaign.'}),
            ('reporter', {'help': 'The name of the reporting entity.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._tryGutor(entity:campaign, ({"name": $cmdopts.name, "reporter:name": $cmdopts.reporter}), $cmdopts.try)',
    },
    {
        'name': 'gen.software',
        'descr': 'Lift (or create) an it:software node based on the software name and reporter.',
        'cmdargs': (
            ('name', {'help': 'The name of the software.'}),
            ('reporter', {'help': 'The name of the reporting entity.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._tryGutor(it:software, ({"name": $cmdopts.name, "reporter:name": $cmdopts.reporter}), $cmdopts.try)',
    },
    {
        'name': 'gen.threat',
        'descr': '''
            Lift (or create) a risk:threat node based on the threat name and reporter name.

            Examples:

                // Yield a risk:threat node for the threat cluster "APT1" reported by "Mandiant".
                gen.threat apt1 mandiant
        ''',
        'cmdargs': (
            ('name', {'help': 'The name of the threat cluster. For example: APT1'}),
            ('reporter', {'help': 'The name of the reporting entity. For example: Mandiant'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._tryGutor(risk:threat, ({"name": $cmdopts.name, "reporter:name": $cmdopts.reporter}), $cmdopts.try)',
    },
    {
        'name': 'gen.vuln',
        'descr': '''
            Lift (or create) a risk:vuln node based on the CVE and reporter name.

            Examples:

                // Yield a risk:vuln node for CVE-2012-0157 reported by Mandiant.
                gen.vuln CVE-2012-0157 Mandiant
        ''',
        'cmdargs': (
            ('cve', {'help': 'The CVE identifier.'}),
            ('reporter', {'help': 'The name of the reporting entity.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._vulnByCve($cmdopts.cve, $cmdopts.reporter, try=$cmdopts.try)',
    },
    {
        'name': 'gen.industry',
        'descr': '''
            Lift (or create) an ind:industry node based on the industry name and reporter name.
        ''',
        'cmdargs': (
            ('name', {'help': 'The industry name.'}),
            ('reporter', {'help': 'The name of the reporting entity.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._tryGutor(ind:industry, ({"name": $cmdopts.name, "reporter:name": $cmdopts.reporter}), $cmdopts.try)',
    },
    {
        'name': 'gen.country',
        'descr': '''
            Lift (or create) a pol:country node based on the 2 letter ISO-3166 country code.

            Examples:

                // Yield the pol:country node which represents the country of Ukraine.
                gen.country ua
        ''',
        'cmdargs': (
            ('code', {'help': 'The 2 letter ISO-3166 country code.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._countryByCode($cmdopts.code, try=$cmdopts.try)',
    },
    {
        'name': 'gen.government',
        'descr': '''
            Lift (or create) the ou:org node representing a country's government based on the 2 letter ISO-3166 country code.

            Examples:

                // Yield the ou:org node which represents the Government of Ukraine.
                gen.government ua
        ''',
        'cmdargs': (
            ('code', {'help': 'The 2 letter ISO-3166 country code.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._governmentByCode($cmdopts.code, try=$cmdopts.try)',
    },
    {
        'name': 'gen.language',
        'descr': 'Lift (or create) a lang:language node based on the name.',
        'cmdargs': (
            ('name', {'help': 'The name of the language.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._tryGutor(lang:language, ({"name": $cmdopts.name}), $cmdopts.try)',
    },
    {
        'name': 'gen.place',
        'descr': '''
            Lift (or create) a geo:place node based on the name.
        ''',
        'cmdargs': (
            ('name', {'help': 'The name of the place.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._tryGutor(geo:place, ({"name": $cmdopts.name}), $cmdopts.try)',
    },
)
