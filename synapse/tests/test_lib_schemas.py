import synapse.tests.utils as s_t_utils
import synapse.lib.schemas as s_schemas

class SchemaTest(s_t_utils.SynTest):

    async def test_pkgdef_endpoints(self):

        pkgdef = {
            'name': 'test',
            'version': '0.0.1',
            'commands': [
                {
                    'name': 'foo.bar',
                    'storm': '(null)',
                    'endpoints': [
                        {'path': '/v1/foo/one'},
                        {'path': '/v1/foo/two', 'host': 'vertex.link'},
                        {'path': '/v1/foo/three', 'desc': 'endpoint three'},
                        {'path': '/v1/foo/four', 'host': 'vertex.link', 'desc': 'endpoint four'},
                    ]
                }
            ]
        }
        valu = s_schemas.reqValidPkgdef(pkgdef)
        self.eq(valu, pkgdef)

        pkgdef['commands'][0]['endpoints'] = [{'host': 'vertex.link'}]
        with self.raises(Exception):
            s_schemas.reqValidPkgdef(pkgdef)

        pkgdef['commands'][0]['endpoints'] = [{'path': '/v1/foo/newp', 'newp': 'newp'}]
        with self.raises(Exception):
            s_schemas.reqValidPkgdef(pkgdef)

        pkgdef['commands'][0]['endpoints'] = 'newp'
        with self.raises(Exception):
            s_schemas.reqValidPkgdef(pkgdef)

        pkgdef['commands'][0]['endpoints'] = []
        valu = s_schemas.reqValidPkgdef(pkgdef)
        self.eq(valu, pkgdef)

        pkgdef['commands'][0].pop('endpoints')
        valu = s_schemas.reqValidPkgdef(pkgdef)
        self.eq(valu, pkgdef)
