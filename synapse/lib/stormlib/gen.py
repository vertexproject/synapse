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
        {'name': 'softByName', 'desc': 'Returns it:software node by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the software.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'An it:software node with the given name.'}}},
        {'name': 'vulnByCve', 'desc': 'Returns risk:vuln node by CVE and source, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'cve', 'type': 'str', 'desc': 'The CVE id.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                      {'name': 'source', 'type': 'str', 'default': None,
                       'desc': 'The name of the organization which reported the vulnerability.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A risk:vuln node with the given CVE.'}}},

        {'name': 'riskThreat',
         'desc': 'Returns a risk:threat node based on the threat and source names, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The reported name of the threat cluster.'},
                      {'name': 'source', 'type': 'str', 'desc': 'The name of the organization which reported the threat cluster.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A risk:threat node.'}}},

        {'name': 'riskToolSoftware',
         'desc': 'Returns a risk:tool:software node based on the tool and source names, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The reported name of the tool.'},
                      {'name': 'source', 'type': 'str', 'desc': 'The name of the organization which reported the tool.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A risk:tool:software node.'}}},

        {'name': 'psContactByEmail', 'desc': 'Returns a entity:contact by deconflicting the type and email address.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'type', 'type': 'str', 'desc': 'The entity:contact:type property.'},
                      {'name': 'email', 'type': 'str', 'desc': 'The entity:contact:email property.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A entity:contact node.'}}},

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
        {'name': 'campaign',
         'desc': 'Returns an ou:campaign node based on the campaign and source names, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The reported name of the campaign.'},
                      {'name': 'source', 'type': 'str', 'desc': 'The name of the organization which reported the campaign.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'An ou:campaign node.'}}},
        {'name': 'itAvScanResultByTarget',
         'desc': 'Returns an it:av:scan:result node by deconflicting with a target and signature name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'form', 'type': 'str', 'desc': 'The target form.'},
                      {'name': 'value', 'type': 'str', 'desc': 'The target value.'},
                      {'name': 'signame', 'type': 'str', 'desc': 'The signature name.'},
                      {'name': 'scanner', 'type': 'str', 'default': None,
                       'desc': 'An optional scanner software name to include in deconfliction.'},
                      {'name': 'time', 'type': 'time', 'default': None,
                       'desc': 'An optional time when the scan was run to include in the deconfliction.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'An it:av:scan:result node.'}}},
        {'name': 'geoPlaceByName', 'desc': 'Returns a geo:place node by name, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the place.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A geo:place node with the given name.'}}},
        {'name': 'fileBytesBySha256',
         'desc': 'Returns a file:bytes node by SHA256, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'sha256', 'type': ['str', 'hash:sha256'], 'desc': 'The SHA256 fingerprint for the file:bytes node.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A file:bytes node with the given SHA256.'}}},
        {'name': 'cryptoX509CertBySha256',
         'desc': 'Returns a crypto:x509:cert node by SHA256, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'sha256', 'type': ['str', 'hash:sha256'], 'desc': 'The SHA256 fingerprint for the certificate.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'A crypto:x509:cert node with the given SHA256.'}}},
        {'name': 'inetTlsServerCertByServerAndSha256',
         'desc': 'Returns an inet:tls:servercert node by server and SHA256, adding the node if it does not exist.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'server', 'type': ['str', 'inet:server'], 'desc': 'The server associated with the x509 certificate.'},
                      {'name': 'sha256', 'type': ['str', 'hash:sha256'], 'desc': 'The SHA256 fingerprint for the certificate.'},
                      {'name': 'try', 'type': 'boolean', 'default': False,
                       'desc': 'Type normalization will fail silently instead of raising an exception.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'An inet:tls:servercert node with the given server and SHA256.'}}},
    )
    _storm_lib_path = ('gen',)

    _storm_query = '''
        function __maybeCast(try, type, valu) {
            if $try {
                return($lib.trycast($type, $valu))
            }
            return(($lib.true, $lib.cast($type, $valu)))
        }

        function orgByName(name, try=$lib.false) {
            [ ou:org=({"name": $name, "$try": $try}) ]
            return($node)
        }

        function orgByFqdn(fqdn, try=$lib.false) {
            ($ok, $fqdn) = $__maybeCast($try, inet:fqdn, $fqdn)
            if (not $ok) { return() }

            inet:fqdn=$fqdn -> ou:org
            return($node)

            [ ou:org=(gen, fqdn, $fqdn) :dns:mx+=$fqdn ]
            return($node)
        }

        function industryByName(name) {
            [ ou:industry=({"name": $name}) ]
            return($node)
        }

        function newsByUrl(url, try=$lib.false) {
            ($ok, $url) = $__maybeCast($try, inet:url, $url)
            if (not $ok) { return() }

            media:news:url=$url
            return($node)

            [ media:news=(gen, url, $url) :url=$url ]
            return($node)
        }

        // FIXME remove?
        function softByName(name) {
            [ it:software=({"name": $name}) ]
            return($node)
        }

        function vulnByCve(cve, try=$lib.false, source=$lib.null) {
            ($ok, $cve) = $__maybeCast($try, it:sec:cve, $cve)
            if (not $ok) { return() }

            risk:vuln:cve=$cve
            if $source {
                +:source:name=$source
                { -:source [ :source=$orgByName($source) ] }
            }
            return($node)

            $guid = (gen, cve, $cve)
            if $source {
                $source = $lib.cast(meta:name, $source)
                $guid.append($source)
            }

            [ risk:vuln=$guid :cve=$cve ]
            if $source {
                [ :source:name=$source :source=$orgByName($source) ]
            }
            return($node)
        }

        function riskThreat(name, source) {
            meta:name=$name -> risk:threat
            +:source:name=$source
            { -:source [ :source=$orgByName($source) ] }
            return($node)

            $name = $lib.cast(meta:name, $name)
            $source = $lib.cast(meta:name, $source)

            [ risk:threat=(gen, name, reporter, $name, $source)
                :name=$name
                :source = { yield $orgByName($source) }
                :source:name = $source
            ]
            return($node)
        }

        function riskToolSoftware(name, source) {

            meta:name = $name
            -> risk:tool:software
            +:source:name = $source
            { -:source [ :source=$orgByName($source) ] }
            return($node)

            $name = $lib.cast(meta:name, $name)
            $source = $lib.cast(meta:name, $source)

            [ risk:tool:software=(gen, $name, $source)
                :name = $name
                :source:name = $source
                :source = { yield $orgByName($source) }
            ]

            return($node)
        }

        function psContactByEmail(type, email, try=$lib.false) {
            ($ok, $email) = $__maybeCast($try, inet:email, $email)
            if (not $ok) { return() }

            ($ok, $type) = $__maybeCast($try, entity:contact:type:taxonomy, $type)
            if (not $ok) { return() }

            entity:contact:email = $email
            +:type = $type
            return($node)

            [ entity:contact=(gen, type, email, $type, $email)
                :email = $email
                :type = $type
            ]
            return($node)
        }

        function polCountryByIso2(iso2, try=$lib.false) {
            ($ok, $iso2) = $__maybeCast($try, pol:iso2, $iso2)
            if (not $ok) { return() }

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
            [ lang:language=({"name": $name}) ]
            return($node)
        }

        function langByCode(code, try=(false)) {
            [ lang:language=({"code": $code, "$try": $try}) ]
            return($node)
        }

        function campaign(name, source) {
            $reporg = {[ ou:org=({"name": $source}) ]}
            [ ou:campaign=({"name": $name, "source": ["ou:org", $reporg]}) ]
            [ :source:name*unset=$source ]
            return($node)
        }

        function itAvScanResultByTarget(form, value, signame, scanner=$lib.null, time=$lib.null, try=$lib.false) {

            ($ok, $target) = $__maybeCast($try, it:av:scan:result:target, ($form, $value))
            if (not $ok) { return() }

            ($ok, $signame) = $__maybeCast($try, it:av:signame, $signame)
            if (not $ok) { return() }

            $dict = ({"target": $target, "signame": $signame})

            if ($scanner != $lib.null) {
                ($ok, $scanner) = $__maybeCast($try, meta:name, $scanner)
                if (not $ok) { return() }
                $dict."scanner:name" = $scanner
            }

            if ($time != $lib.null) {
                ($ok, $time) = $__maybeCast($try, time, $time)
                if (not $ok) { return() }
                $dict.time = $time
            }

            [ it:av:scan:result=$dict ]

            return($node)
        }

        function geoPlaceByName(name) {
            $geoname = $lib.cast(meta:name, $name)

            meta:name=$geoname -> geo:place
            return($node)

            [ geo:place=(gen, name, $geoname) :name=$geoname ]
            return($node)
        }

        // FIXME remove?
        function fileBytesBySha256(sha256, try=$lib.false) {
            [ file:bytes=({"$try": $try, "sha256": $sha256}) ]
            return($node)
        }

        function cryptoX509CertBySha256(sha256, try=$lib.false) {

            ($ok, $sha256) = $lib.trycast(hash:sha256, $sha256)
            if (not $ok and $try) { return() }

            $file = {[ file:bytes=({"sha256": $sha256}) ]}

            [ crypto:x509:cert=({"sha256": $sha256, "file": $file}) ]

            return($node)
        }

        function inetTlsServerCertByServerAndSha256(server, sha256, try=$lib.false) {
            ($ok, $server) = $__maybeCast($try, inet:server, $server)
            if (not $ok) { return() }

            $crypto = $cryptoX509CertBySha256($sha256, try=$try)
            if (not $crypto) { return() }

            [ inet:tls:servercert=($server, $crypto) ]
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
        'name': 'gen.ou.campaign',
        'descr': 'Lift (or create) an ou:campaign based on the name and reporting organization.',
        'cmdargs': (
            ('name', {'help': 'The name of the campaign.'}),
            ('source', {'help': 'The name of the reporting organization.'}),
        ),
        'storm': 'yield $lib.gen.campaign($cmdopts.name, $cmdopts.source)',
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
            Lift (or create) a risk:threat node based on the threat name and source name.

            Examples:

                // Yield a risk:threat node for the threat cluster "APT1" reported by "Mandiant".
                gen.risk.threat apt1 mandiant
        ''',
        'cmdargs': (
            ('name', {'help': 'The name of the threat cluster. For example: APT1'}),
            ('source', {'help': 'The name of the reporting organization. For example: Mandiant'}),
        ),
        'storm': 'yield $lib.gen.riskThreat($cmdopts.name, $cmdopts.source)',
    },
    {
        'name': 'gen.risk.tool.software',
        'descr': '''
            Lift (or create) a risk:tool:software node based on the tool name and source name.

            Examples:

                // Yield a risk:tool:software node for the "redtree" tool reported by "vertex".
                gen.risk.tool.software redtree vertex
        ''',
        'cmdargs': (
            ('name', {'help': 'The tool name.'}),
            ('source', {'help': 'The name of the reporting organization. For example: "recorded future"'}),
        ),
        'storm': 'yield $lib.gen.riskToolSoftware($cmdopts.name, $cmdopts.source)',
    },
    {
        'name': 'gen.risk.vuln',
        'descr': '''
            Lift (or create) a risk:vuln node based on the CVE and source name.

            Examples:

                // Yield a risk:vuln node for CVE-2012-0157 reported by Mandiant.
                gen.risk.vuln CVE-2012-0157 Mandiant
        ''',
        'cmdargs': (
            ('cve', {'help': 'The CVE identifier.'}),
            ('source', {'help': 'The name of the reporting organization.', 'nargs': '?'}),
            ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
                       'action': 'store_true'}),
        ),
        'storm': 'yield $lib.gen.vulnByCve($cmdopts.cve, try=$cmdopts.try, source=$cmdopts.source)',
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
            Lift (or create) the entity:contact node by deconflicting the email and type.

            Examples:

                // Yield the entity:contact node for the type and email
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
    {
        'name': 'gen.it.av.scan.result',
        'descr': '''
            Lift (or create) the it:av:scan:result node by deconflicting the target and signature name.

            The scan time and scanner name may also optionally be provided for deconfliction.

            Examples:

                // Yield the it:av:scan:result node for an FQDN and signature name
                gen.it.av.scan.result inet:fqdn vertex.link foosig

                // Also deconflict by scanner name and scan time
                gen.it.av.scan.result inet:fqdn fqdn vertex.link foosig --scanner-name barscanner --time 2022-11-03
        ''',
        'cmdargs': (
            ('form', {'help': 'The target form.'}),
            ('value', {'help': 'The target value.'}),
            ('signame', {'help': 'The signature name.'}),
            ('--scanner-name', {'help': 'An optional scanner software name to include in deconfliction.'}),
            ('--time', {'help': 'An optional time when the scan was run to include in the deconfliction.'}),
            ('--try', {'help': 'Type normalization will fail silently instead of raising an exception.',
                       'action': 'store_true'}),
        ),
        'storm': '''
            yield $lib.gen.itAvScanResultByTarget($cmdopts.form, $cmdopts.value, $cmdopts.signame,
                                                  scanner=$cmdopts.scanner_name, time=$cmdopts.time, try=$cmdopts.try)
        ''',
    },
    {
        'name': 'gen.geo.place',
        'descr': '''
            Lift (or create) a geo:place node based on the name.
        ''',
        'cmdargs': (
            ('name', {'help': 'The name of the place.'}),
        ),
        'storm': 'yield $lib.gen.geoPlaceByName($cmdopts.name)',
    },
)
