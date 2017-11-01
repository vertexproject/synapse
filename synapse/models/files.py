import synapse.common as s_common

from synapse.lib.types import DataType
from synapse.common import addpref, guid
from synapse.lib.module import CoreModule, modelrev

class FileBaseType(DataType):
    def norm(self, valu, oldval=None):
        if not (isinstance(valu, str) and not valu.find('/') > -1):
            self._raiseBadValu(valu)

        return valu.lower(), {}

    def repr(self, valu):
        return valu

class FilePathType(DataType):
    def norm(self, valu, oldval=None):

        if not isinstance(valu, str):
            self._raiseBadValu(valu)

        lead = ''

        valu = valu.replace('\\', '/').lower()
        if valu and valu[0] == '/':
            lead = '/'

        valu = valu.strip('/')

        vals = [v for v in valu.split('/') if v]

        fins = []

        # canonicalize . and ..
        for v in vals:
            if v == '.':
                continue

            if v == '..' and fins:
                fins.pop()
                continue

            fins.append(v)

        subs = {'dir': '', 'depth': len(fins)}
        valu = lead + ('/'.join(fins))

        if fins:
            base = fins[-1]
            subs['base'] = base

            pext = base.rsplit('.', 1)
            if len(pext) > 1:
                subs['ext'] = pext[1]

            if len(fins) > 1:
                subs['dir'] = lead + ('/'.join(fins[:-1]))

        return valu, subs

class FileRawPathType(DataType):
    def norm(self, valu, oldval=None):
        if not isinstance(valu, str):
            self._raiseBadValu(valu)

        subs = {}

        subs['norm'], subsubs = self.tlib.getTypeNorm('file:path', valu)
        subs.update(addpref('norm', subsubs))

        return valu, subs

class FileMod(CoreModule):

    def initCoreModule(self):
        self.core.addSeedCtor('file:bytes:md5', self.seedFileMd5)
        self.core.addSeedCtor('file:bytes:sha1', self.seedFileSha1)
        # sha256 / sha512 are good enough for now
        self.core.addSeedCtor('file:bytes:sha256', self.seedFileGoodHash)
        self.core.addSeedCtor('file:bytes:sha512', self.seedFileGoodHash)

    def seedFileGoodHash(self, prop, valu, **props):
        '''
        Hashes that we consider "cardinal enough" to pivot.
        '''
        name = prop.rsplit(':', 1)[-1]
        # Normalize the valu before we go any further
        valu, _ = self.core.getPropNorm(prop, valu)
        props[name] = valu

        # FIXME could we update additional hashes here and
        # maybe (gasp) update the primary property if we
        # finally have enough, then update all other known
        # records that reference this file guid?

        tufo = self.core.getTufoByProp(prop, valu)
        if tufo is not None:
            # add more hashes if we know them...
            tufo = self.core.setTufoProps(tufo, **props)
            return tufo

        iden = self.core.getTypeCast('make:guid', valu)
        tufo = self.core.formTufoByProp('file:bytes', iden, **props)
        # update with any additional hashes we have...
        tufo = self.core.setTufoProps(tufo, **props)
        return tufo

    def seedFileMd5(self, prop, valu, **props):
        valu, _ = self.core.getPropNorm('file:bytes:md5', valu)
        props['md5'] = valu
        return self.core.formTufoByProp('file:bytes', valu, **props)

    def seedFileSha1(self, prop, valu, **props):
        valu, _ = self.core.getPropNorm('file:bytes:sha1', valu)
        props['sha1'] = valu
        valu = guid(valu)
        return self.core.formTufoByProp('file:bytes', valu, **props)

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('file:bytes', {
                    'subof': 'guid',
                    'doc': 'A unique file identifier'}),

                ('file:sub', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'parent,file:bytes|child,file:bytes',
                    'doc': 'A parent file that fully contains the specified child file.'}),

                ('file:rawpath', {
                    'ctor': 'synapse.models.files.FileRawPathType',
                    'doc': 'A raw file path in its default (non-normalized) form. Can consist of a directory '
                        'path, a path and file name, or a file name.'}),

                ('file:base', {
                    'ctor': 'synapse.models.files.FileBaseType',
                    'doc': 'A file or directory name (without a full path), such as system32 or foo.exe.'}),

                ('file:path', {
                    'ctor': 'synapse.models.files.FilePathType',
                    'doc': 'A file path that has been normalized by Synapse. Can consist of a directory path, '
                        'a path and file name, or a file name.'}),

                ('file:imgof', {
                    'subof': 'xref',
                    'source': 'file,file:bytes',
                    'doc': 'A file that contains an image of the specified node.'}),

                ('file:txtref', {
                    'subof': 'xref',
                    'source': 'file,file:bytes',
                    'doc': 'A file that contains a reference to the specified node.'}),
            ),

            'forms': (

                ('file:imgof', {}, [
                    ('file', {'ptype': 'file:bytes', 'doc': 'The guid of the file containing the image.', 'ro': 1}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1,
                         'doc': 'The form=valu of the object referenced in the image, e.g., geo:place=<guid_of_place>.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                         'doc': 'The property (form) of the referenced object, as specified by the propvalu.'}),
                    ('xref:intval', {'ptype': 'int', 'ro': 1,
                         'doc': 'The value of the property of the referenced object, as specified by the propvalu, if '
                             'the value is an integer.'}),
                    ('xref:strval', {'ptype': 'str', 'ro': 1,
                          'doc': 'The value of the property of the referenced object, as specified by the propvalu, if '
                              'the value is a string.'}),
                ]),

                ('file:txtref', {}, [
                    ('file', {'ptype': 'file:bytes', 'ro': 1,
                        'doc': 'The guid of the file containing the reference.'}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1,
                         'doc': 'The form=valu of the object referenced in the file, e.g., inet:fqdn=foo.com.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                         'doc': 'The property (form) of the referenced object, as specified by the propvalu.'}),
                    ('xref:intval', {'ptype': 'int', 'ro': 1,
                         'doc': 'The value of the property of the referenced object, as specified by the propvalu, if '
                             'the value is an integer.'}),
                    ('xref:strval', {'ptype': 'str', 'ro': 1,
                         'doc': 'The value of the property of the referenced object, as specified by the propvalu, '
                             'if the value is a string.'}),
                ]),

                ('file:path', {}, (
                    ('dir', {'ptype': 'file:path', 'ro': 1,
                         'doc': 'The parent directory of the file path.'}),
                    ('ext', {'ptype': 'str:lwr', 'ro': 1,
                         'doc': 'The file extension of the file name, (if present); for example: exe, bat, py, docx.'}),
                    ('base', {'ptype': 'file:base', 'ro': 1,
                          'doc': 'The final component of the file path. Can be a file name (if present) or the final '
                              'directory.'}),
                )),

                ('file:base', {'ptype': 'file:base'}, (
                )),

                ('file:bytes', {'ptype': 'file:bytes'}, (
                    ('size', {'ptype': 'int', 'ro': 1,
                        'doc': 'The size of the file in bytes.'}),
                    ('md5', {'ptype': 'hash:md5', 'ro': 1,
                        'doc': 'The md5 hash of the file.'}),
                    ('sha1', {'ptype': 'hash:sha1', 'ro': 1,
                        'doc': 'The sha1 hash of the file.'}),
                    ('sha256', {'ptype': 'hash:sha256', 'ro': 1,
                        'doc': 'The sha256 hash of the file.'}),
                    ('sha512', {'ptype': 'hash:sha512', 'ro': 1,
                        'doc': 'The sha512 hash of the file.'}),
                    ('name', {'ptype': 'file:base',
                          'doc': 'The name of the file. Because a given set of bytes can have any number of '
                              'arbitrary names, this field is used for display purposes only.'}),
                    ('mime', {'ptype': 'str', 'defval': '??',
                          'doc': 'The MIME type of the file.'}),

                    # FIXME could another model define props for this form?
                    ('mime:x509:cn', {'ptype': 'str', 'ro': 1,
                        'doc': 'The Common Name (CN) attribute of the x509 Subject.'}),

                    ('mime:pe:size', {'ptype': 'int', 'ro': 1,
                        'doc': 'The size of the executable file according to the file headers.'}),
                    ('mime:pe:imphash', {'ptype': 'guid', 'ro': 1,
                        'doc': 'The PE import hash of the file as calculated by Vivisect; this method excludes '
                            'imports referenced as ordinals and may fail to calculate an import hash for files '
                            'that use ordinals.'}),
                    ('mime:pe:compiled', {'ptype': 'time', 'ro': 1,
                        'doc': 'The compile time of the file according to the PE header.'}),

                    # once we have dark prop based text token indexes...
                    # ('mime:pe:imports',{'ptype':'time','doc':'Compile time from the PE header'}),

                    ('mime:*', {'glob': 1,
                        'doc': 'Namespace for high-value mime details'})
                )),

                ('file:subfile', {'ptype': 'file:sub'}, (
                    ('parent', {'ptype': 'file:bytes', 'ro': 1,
                        'doc': 'The guid of the parent file.'}),
                    ('child', {'ptype': 'file:bytes', 'ro': 1,
                        'doc': 'The guid of the child file.'}),
                    ('name', {'ptype': 'file:base',
                          'doc': 'The name of the child file. Because a given set of bytes can have any '
                              'number of arbitrary names, this field is used for display purposes only.'}),
                    # TODO others....
                )),
            ),
        }
        name = 'file'
        return ((name, modl), )
