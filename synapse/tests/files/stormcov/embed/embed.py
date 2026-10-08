# Storm embedded in python for the stormcov tests.
_storm_query = '''
    [ inet:fqdn=vertex.link ]
    if (true) {
        [ inet:fqdn=vtx.lk ]
    }
'''

cmds = (
    {'name': 'foo.bar', 'storm': '''
        $x = 1
        $lib.print($x)
    '''},
    {'name': 'foo.baz', 'storm': 'inet:fqdn=vertex.link'},
)

notstorm = '''
    [ inet:fqdn=nope.link ]
'''

escaped = {'storm': '[ inet:fqdn=esc.link ]\n[ inet:fqdn=esc2.link ]'}

concat = {'storm': 'inet:fqdn=a.link '
                   '| limit 1'}

class Foo:
    _storm_query = 'inet:fqdn=class.link'

    def notliteral(self, name):
        self.storm = f'inet:fqdn={name}'
        self._storm_query = name

_storm_query: str = 'inet:fqdn=ann.link'
storm: str
