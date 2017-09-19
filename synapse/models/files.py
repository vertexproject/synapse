import synapse.compat as s_compat

from synapse.lib.types import DataType
from synapse.common import addpref, guid
from synapse.lib.module import CoreModule, modelrev

class FileBaseType(DataType):
    def norm(self, valu, oldval=None):
        if not (s_compat.isstr(valu) and not valu.find('/') > -1):
            self._raiseBadValu(valu)

        return valu.lower(), {}

    def repr(self, valu):
        return valu

class FilePathType(DataType):
    def norm(self, valu, oldval=None):

        if not s_compat.isstr(valu):
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
        if not s_compat.isstr(valu):
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
                ('file:bytes', {'subof': 'guid', 'doc': 'A unique file identifier'}),
                ('file:sub', {'subof': 'sepr', 'sep': '/', 'fields': 'parent,file:bytes|child,file:bytes'}),
                ('file:rawpath', {'ctor': 'synapse.models.files.FileRawPathType', 'doc': 'A file path'}),
                ('file:base', {'ctor': 'synapse.models.files.FileBaseType', 'doc': 'A file basename such as foo.exe'}),

                ('file:path', {'ctor': 'synapse.models.files.FilePathType', 'doc': 'A normalized file path'}),

                ('file:imgof', {'subof': 'xref', 'source': 'file,file:bytes',
                                'doc': 'The file is an image file which shows the referenced node'}),
                ('file:txtref',
                 {'subof': 'xref', 'source': 'file,file:bytes', 'doc': 'The file content refereneces the given node'}),

            ),

            'forms': (

                ('file:imgof', {}, [
                    ('file', {'ptype': 'file:bytes'}),
                    ('xref:*', {'glob': 1}),
                ]),

                ('file:txtref', {}, [
                    ('file', {'ptype': 'file:bytes'}),
                    ('xref:*', {'glob': 1}),
                ]),

                ('file:path', {}, (
                    ('dir', {'ptype': 'file:path', 'doc': 'The parent directory for this path.'}),
                    ('ext', {'ptype': 'str:lwr', 'doc': 'The file extension ( if present ).'}),
                    ('base',
                     {'ptype': 'file:base', 'doc': 'The final path component, such as the filename, of this path.'}),
                )),

                ('file:base', {'ptype': 'file:base', 'doc': 'A final path component, such as the filename.'}, ()),

                ('file:bytes', {'ptype': 'file:bytes'}, (
                    ('size', {'ptype': 'int'}),
                    ('md5', {'ptype': 'hash:md5'}),
                    ('sha1', {'ptype': 'hash:sha1'}),
                    ('sha256', {'ptype': 'hash:sha256'}),
                    ('sha512', {'ptype': 'hash:sha512'}),
                    ('name', {'ptype': 'file:base', 'doc': 'For display purposes only'}),
                    ('mime', {'ptype': 'str', 'defval': '??', 'doc': 'Mime type for the file bytes'}),

                    # FIXME could another model define props for this form?
                    ('mime:x509:cn', {'ptype': 'str', 'doc': 'X509 Subject Common Name'}),

                    ('mime:pe:size', {'ptype': 'int', 'doc': 'Size of the executable according to headers'}),
                    ('mime:pe:imphash', {'ptype': 'guid', 'doc': 'PE Import hash as calculated by vivisect'}),
                    ('mime:pe:compiled', {'ptype': 'time', 'doc': 'Compile time from the PE header'}),

                    # once we have dark prop based text token indexes...
                    # ('mime:pe:imports',{'ptype':'time','doc':'Compile time from the PE header'}),

                    ('mime:*', {'glob': 1, 'doc': 'Namespace for high-value mime details'})
                )),

                ('file:subfile', {'ptype': 'file:sub'}, (
                    ('parent', {'ptype': 'file:bytes'}),
                    ('child', {'ptype': 'file:bytes'}),
                    ('name', {'ptype': 'file:base'}),
                    # TODO others....
                )),

            ),
        }
        name = 'file'
        return ((name, modl), )
