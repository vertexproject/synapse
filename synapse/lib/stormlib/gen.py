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
    '''
