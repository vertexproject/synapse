import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibGen(s_stormtypes.Lib):
    '''
    A Storm Library for secondary property based deconfliction.
    '''
    _storm_lib_path = ('gen',)

    _storm_query = '''
        function __tryGutor(form, ctor, try) {
            if $try {
                return({[ *$form?=$ctor ]})
            }
            return({[ *$form=$ctor ]})
        }

        function _entityCampaignByName(name, reporter, try=(false)) {
            $ctor = ({
                "name": $name,
                "reporter:name": $reporter,
                "$props": {
                    "reporter": $_ouOrgByName($reporter, try=$try),
                },
            })
            return($__tryGutor(entity:campaign, $ctor, $try))
        }

        function _geoPlaceByName(name, try=(false)) {
            $ctor = ({
                "name": $name,
            })
            return($__tryGutor(geo:place, $ctor, $try))
        }

        function _itSoftwareByName(name, try=(false)) {
            $ctor = ({
                "name": $name,
            })
            return($__tryGutor(it:software, $ctor, $try))
        }

        function _langLanguageByName(name, try=(false)) {
            $ctor = ({
                "name": $name,
            })
            return($__tryGutor(lang:language, $ctor, $try))
        }

        function _ouIndustryByName(name, reporter, try=(false)) {
            $ctor = ({
                "name": $name,
                "reporter:name": $reporter,
                "$props": {
                    "reporter": $_ouOrgByName($reporter, try=$try),
                },
            })
            return($__tryGutor(ou:industry, $ctor, $try))
        }

        function _ouOrgByName(name, try=(false)) {
            $ctor = ({
                "name": $name,
            })
            return($__tryGutor(ou:org, $ctor, $try))
        }

        function _polCountryByCode(code, try=(false)) {
            $ctor = ({
                "code": $code,
            })
            return($__tryGutor(pol:country, $ctor, $try))
        }

        function _polCountryOrgByCode(code, try=(false)) {
            yield $_polCountryByCode($code, try=$try)
            [ :government*unset=$_ouOrgByName(`{:code} government`) ]
            :government -> ou:org
            return($node)
        }

        function _riskThreatByName(name, reporter, try=(false)) {
            $ctor = ({
                "name": $name,
                "reporter:name": $reporter,
                "$props": {
                    "reporter": $_ouOrgByName($reporter, try=$try),
                },
            })
            return($__tryGutor(risk:threat, $ctor, $try))
        }

        function _riskToolSoftByName(name, reporter, try=(false)) {
            $ctor = ({
                "name": $name,
                "reporter:name": $reporter,
                "$props": {
                    "reporter": $_ouOrgByName($reporter, try=$try),
                },
            })
            return($__tryGutor(risk:tool:software, $ctor, $try))
        }

        function _riskVulnByCve(cve, reporter, try=(false)) {
            if $try {
                $cve = {[ it:sec:cve?=$cve ]}
                if ($cve = null) { return() }
            } else {
                $cve = {[ it:sec:cve=$cve ]}
            }

            $ctor = ({
                "id": $cve,
                "reporter:name": $reporter,
                "$props": {
                    "reporter": $_ouOrgByName($reporter, try=$try),
                }
            })

            return($__tryGutor(risk:vuln, $ctor, $try))
        }
    '''


_tryarg = ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
          'action': 'store_true'})
stormcmds = (

    {
        'name': 'gen.ou.org',
        'descr': 'Lift (or create) an ou:org node based on the organization name.',
        'cmdargs': (
            ('name', {'help': 'The name of the organization.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._ouOrgByName($cmdopts.name, try=$cmdopts.try)',
    },
    {
        'name': 'gen.entity.campaign',
        'descr': 'Lift (or create) an entity:campaign based on the name and reporting organization.',
        'cmdargs': (
            ('name', {'help': 'The name of the campaign.'}),
            ('reporter', {'help': 'The name of the reporting organization.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._entityCampaignByName($cmdopts.name, $cmdopts.reporter, try=$cmdopts.try)',
    },
    {
        'name': 'gen.it.software',
        'descr': 'Lift (or create) an it:software node based on the software name.',
        'cmdargs': (
            ('name', {'help': 'The name of the software.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._itSoftwareByName($cmdopts.name, try=$cmdopts.try)'
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
            _tryarg,
        ),
        'storm': 'yield $lib.gen._riskThreatByName($cmdopts.name, $cmdopts.reporter, try=$cmdopts.try)',
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
            _tryarg,
        ),
        'storm': 'yield $lib.gen._riskToolSoftByName($cmdopts.name, $cmdopts.reporter, try=$cmdopts.try)',
    },
    {
        'name': 'gen.risk.vuln',
        'descr': '''
            Lift (or create) a risk:vuln node based on the CVE and reporter name.

            Examples:

                // Yield a risk:vuln node for CVE-2012-0157 reported by Mandiant.
                gen.risk.vuln CVE-2012-0157 Mandiant
        ''',
        'cmdargs': (
            ('cve', {'help': 'The CVE identifier.'}),
            ('reporter', {'help': 'The name of the reporting organization.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._riskVulnByCve($cmdopts.cve, $cmdopts.reporter, try=$cmdopts.try)',
    },
    {
        'name': 'gen.ou.industry',
        'descr': '''
            Lift (or create) an ou:industry node based on the industry name.
        ''',
        'cmdargs': (
            ('name', {'help': 'The industry name.'}),
            ('reporter', {'help': 'The name of the reporting organization.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._ouIndustryByName($cmdopts.name, $cmdopts.reporter, try=$cmdopts.try)',
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
            ('code', {'help': 'The 2 letter ISO-3166 country code.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._polCountryByCode($cmdopts.code, try=$cmdopts.try)',
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
            ('code', {'help': 'The 2 letter ISO-3166 country code.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._polCountryOrgByCode($cmdopts.code, try=$cmdopts.try)',
    },
    {
        'name': 'gen.lang.language',
        'descr': 'Lift (or create) a lang:language node based on the name.',
        'cmdargs': (
            ('name', {'help': 'The name of the language.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._langLanguageByName($cmdopts.name, try=$cmdopts.try)',
    },
    {
        'name': 'gen.geo.place',
        'descr': '''
            Lift (or create) a geo:place node based on the name.
        ''',
        'cmdargs': (
            ('name', {'help': 'The name of the place.'}),
            _tryarg,
        ),
        'storm': 'yield $lib.gen._geoPlaceByName($cmdopts.name, try=$cmdopts.try)',
    },
)
