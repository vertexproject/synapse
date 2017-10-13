import synapse.axon as s_axon
import synapse.common as s_common

from synapse.lib.types import DataType
from synapse.lib.module import CoreModule, modelrev


class AxonMod(CoreModule):

    def initCoreModule(self):
        self.onFormNode('axon:path', self.onFormAxonPath)

    def onFormAxonPath(self, form, valu, props, mesg):
        # Early return for root nodes
        if valu == '/':
            return

        # Check to see if parent exists
        pval = props.get('axon:path:dir')
        ppfo = self.core.getTufoByProp('axon:path', pval)

        # If the parent node exists, return. otherwise make the parent node
        # with a default mode and nlinks value.
        if ppfo:
            return

        pval, psubs = self.core.getTypeNorm('axon:path', pval)
        # XXX Private static method should be promoted to a standalone method.
        mode = self.core.getConfOpt('axon:dirmode')
        pprops = s_axon.Axon._fs_new_dir_attrs(psubs.get('dir'), mode)
        children = self.core.getTufosByProp('axon:path:dir', pval)
        pprops['st_nlink'] += len(children) + 1 # XXX Is this correct?

        # Form the new dir node
        self.core.formTufoByProp('axon:path', pval, **pprops)

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

                ('axon:clone', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'str', 'req': 1}),
                )),

                ('axon:path', {'ptype': 'axon:path'}, (
                    ('dir', {'ptype': 'axon:path', 'req': False, 'doc': 'The parent directory for this path.'}),
                    ('base', {'ptype': 'file:base', 'req': True, 'doc': 'The final path component, such as the filename, of this path.'}),
                    ('blob', {'ptype': 'guid', 'req': False}),
                    ('st_mode', {'ptype': 'int', 'req': True,
                                 'doc': 'Specifies the mode of the file.'}),
                    ('st_nlink',
                     {'ptype': 'int', 'req': True,
                      'doc': 'The number of hard links to the file. This count keeps track of how many directories'
                             ' have entries for this file.'}
                     ),
                    ('st_atime', {'ptype': 'int', 'req': False,
                                  'doc': 'This is the last access time for the file.'}),
                    ('st_ctime', {'ptype': 'int', 'req': False,
                                  'doc': 'This is the time of the last modification to the attributes of the file.'}),
                    ('st_mtime', {'ptype': 'int', 'req': False,
                                  'doc': 'This is the time of the last modification to the contents of the file.'}),
                    ('st_size', {'ptype': 'int', 'req': False}),
                )),

            ),
        }

        return (('axon', model), )

class AxonPathType(DataType):

    def norm(self, valu, oldval=None):

        if not (isinstance(valu, str) and len(valu) > 0):
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
