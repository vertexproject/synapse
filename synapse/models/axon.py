import synapse.compat as s_compat
from synapse.lib.types import DataType
from synapse.lib.module import CoreModule, modelrev


class AxonMod(CoreModule):

    @staticmethod
    def getBaseModels():
        model = {

            'types': (
                ('axon:path', {'ctor': 'synapse.models.axon.AxonPathType', 'doc': 'A path to a file in an axon'}),
            ),

            'forms': (

                ('axon:blob', {'ptype': 'guid'}, (
                    ('off', {'ptype': 'int', 'req': True}),
                    ('size', {'ptype': 'int', 'req': True}),
                    ('md5', {'ptype': 'hash:md5', 'req': True}),
                    ('sha1', {'ptype': 'hash:sha1', 'req': True}),
                    ('sha256', {'ptype': 'hash:sha256', 'req': True}),
                    ('sha512', {'ptype': 'hash:sha512', 'req': True}),
                )),

                ('axon:clone', {'ptype': 'guid'}, ()),

                ('axon:path', {'ptype': 'axon:path'}, (
                    ('dir', {'ptype': 'axon:path', 'req': False, 'doc': 'The parent directory for this path.'}),
                    ('base', {'ptype': 'file:base', 'req': True, 'doc': 'The final path component, such as the filename, of this path.'}),
                    ('blob', {'ptype': 'guid', 'req': False}),
                    ('st_mode', {'ptype': 'int', 'req': True}),
                    ('st_nlink', {'ptype': 'int', 'req': True}),
                    ('st_atime', {'ptype': 'int', 'req': False}),
                    ('st_ctime', {'ptype': 'int', 'req': False}),
                    ('st_mtime', {'ptype': 'int', 'req': False}),
                    ('st_size', {'ptype': 'int', 'req': False}),
                )),

            ),
        }

        return (('axon', model), )

class AxonPathType(DataType):

    def norm(self, valu, oldval=None):

        if not (s_compat.isstr(valu) and len(valu) > 0):
            self._raiseBadValu(valu)

        leadingslash = '/' if valu.startswith('/') else ''
        newval = valu.replace('\\', '/').lower().strip('/')
        parts = newval.split('/')

        dirname = leadingslash + '/'.join(parts[0:-1])
        newval = leadingslash + newval

        props = {}
        base = parts[-1]
        if base:
            props['base'] = base

        if dirname:
            props['dir'] = dirname

        return newval, props
