import base64
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.types as s_types
import synapse.lib.module as s_module

class FileBase(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.indxcmpr['^='] = self.indxByPref

    def indxByPref(self, valu):
        valu = valu.strip().lower().replace('\\', '/')
        indx = valu.encode('utf8')
        return (
            ('pref', indx),
        )

    def _normPyStr(self, valu):

        norm = valu.strip().lower().replace('\\', '/')
        if norm.find('/') != -1:
            mesg = 'file:base may not contain /'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        subs = {}
        if norm.find('.') != -1:
            subs['ext'] = norm.rsplit('.', 1)[1]

        return norm, {'subs': subs}

    def indx(self, norm):
        return norm.encode('utf8')

class FilePath(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.indxcmpr['^='] = self.indxByPref

    def indxByPref(self, valu):
        valu = valu.strip().lower().replace('\\', '/')
        indx = valu.encode('utf8')
        return (
            ('pref', indx),
        )

    def _normPyStr(self, valu):

        if len(valu) == 0:
            return '', {}

        lead = ''
        if valu[0] == '/':
            lead = '/'

        valu = valu.strip().lower().replace('\\', '/').strip('/')
        if not valu:
            return '', {}

        path = []
        vals = [v for v in valu.split('/') if v]
        for part in vals:
            if part == '.':
                continue

            if part == '..':
                if len(path):
                    path.pop()

                continue

            path.append(part)

        fullpath = lead + '/'.join(path)

        base = path[-1]
        subs = {'base': base}
        if '.' in base:
            subs['ext'] = base.rsplit('.', 1)[1]
        if len(path) > 1:
            subs['dir'] = lead + '/'.join(path[:-1])

        return fullpath, {'subs': subs}

    def indx(self, norm):
        return norm.encode('utf8')

class FileBytes(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(bytes, self._normPyBytes)

    def indx(self, norm):
        return norm.encode('utf8')

    def _normPyStr(self, valu):

        if valu == '*':
            guid = s_common.guid()
            norm = f'guid:{guid}'
            return norm, {}

        if valu.find(':') == -1:

            # we're ok with un-adorned sha256s
            if len(valu) == 64 and s_common.uhex(valu):
                valu = valu.lower()
                subs = {'sha256': valu}
                return f'sha256:{valu}', {'subs': subs}

            raise s_exc.BadTypeValu(name=self.name, valu=valu)

        kind, kval = valu.split(':', 1)

        if kind == 'base64':
            byts = base64.b64decode(kval)
            return self._normPyBytes(byts)

        kval = kval.lower()

        if kind == 'hex':
            byts = s_common.uhex(kval)
            return self._normPyBytes(byts)

        if kind == 'guid':

            kval = kval.lower()
            if not s_common.isguid(kval):
                raise s_exc.BadTypeValu(name=self.name, valu=valu)

            return f'guid:{kval}', {}

        if kind == 'sha256':

            if len(kval) != 64:
                raise s_exc.BadTypeValu(name=self.name, valu=valu)

            s_common.uhex(kval)

            subs = {'sha256': kval}
            return f'sha256:{kval}', {'subs': subs}

        raise s_exc.BadTypeValu(name=self.name, valu=valu)

    def _normPyBytes(self, valu):

        sha256 = hashlib.sha256(valu).hexdigest()

        norm = f'sha256:{sha256}'

        subs = {
            'md5': hashlib.md5(valu).hexdigest(),
            'sha1': hashlib.sha1(valu).hexdigest(),
            'sha256': sha256,
            'sha512': hashlib.sha512(valu).hexdigest(),
            'size': len(valu),
        }
        return norm, {'subs': subs}

class FileModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'ctors': (

                ('file:bytes', 'synapse.models.files.FileBytes', {}, {
                    'doc': 'The file bytes type with SHA256 based primary property.'}),

                ('file:base', 'synapse.models.files.FileBase', {}, {
                    'doc': 'A file name with no path.',
                    'ex': 'woot.exe'}),

                ('file:path', 'synapse.models.files.FilePath', {}, {
                    'doc': 'A normalized file path.',
                    'ex': 'c:/windows/system32/calc.exe'}),

            ),

            'types': (

                ('file:ref', ('comp', {'fields': (('file', 'file:bytes'), ('node', 'ndef'))}), {
                    'doc': 'A file that contains an image of the specififed node.'}),

                ('file:subfile', ('comp', {'fields': (('parent', 'file:bytes'), ('child', 'file:bytes'))}), {
                    'doc': 'A parent file that fully contains the specified child file.',
                }),

            ),

            'forms': (

                ('file:bytes', {}, (

                    ('size', ('int', {}), {
                        'doc': 'The file size in bytes.'}),

                    ('md5', ('hash:md5', {}), {'ro': 1,
                                               'doc': 'The md5 hash of the file.'}),

                    ('sha1', ('hash:sha1', {}), {'ro': 1,
                                                 'doc': 'The sha1 hash of the file.'}),

                    ('sha256', ('hash:sha256', {}), {'ro': 1,
                                                     'doc': 'The sha256 hash of the file.'}),

                    ('sha512', ('hash:sha512', {}), {'ro': 1,
                                                     'doc': 'The sha512 hash of the file.'}),

                    ('name', ('file:base', {}), {
                        'doc': 'The best known base name for the file.'}),

                    ('mime', ('str', {'lower': 1}), {'defval': '??',
                                                     'doc': 'The MIME type of the file.'}),

                    ('mime:x509:cn', ('str', {}), {
                        'doc': 'The Common Name (CN) attribute of the x509 Subject.'}),

                    ('mime:pe:size', ('int', {}), {
                        'doc': 'The size of the executable file according to the PE file header.'}),

                    ('mime:pe:imphash', ('guid', {}), {
                        'doc': 'The PE import hash of the file as calculated by Vivisect; this method excludes '
                               'imports referenced as ordinals and may fail to calculate an import hash for files '
                               'that use ordinals.'}),

                    ('mime:pe:compiled', ('time', {}), {
                        'doc': 'The compile time of the file according to the PE header.'}),

                )),

                ('file:base', {}, (
                    ('ext', ('str', {}), {'ro': 1,
                                          'doc': 'The file extension (if any).'}),
                )),

                ('file:ref', {}, (

                    ('file', ('file:bytes', {}), {'ro': 1,
                                                  'doc': 'The file that refers to a node.'}),

                    ('node', ('ndef', {}), {'ro': 1,
                                            'doc': 'The node referenced by the file.'}),

                    ('node:form', ('str', {}), {'ro': 1,
                                                'doc': 'The form of node which is referenced.'}),

                    ('type', ('str', {'lower': 1}), {
                        'doc': 'A convention based name for the type of reference.'}),
                )),

                ('file:subfile', {}, (
                    ('parent', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The parent file containing the child file.',
                    }),
                    ('child', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The child file contained in the parent file.',
                    }),
                    ('name', ('file:base', {}), {
                        'doc': 'The name of the child file. Because a given set of bytes '
                               'can have any number of arbitrary names, this field is '
                               'used for display purposes only.'
                    })
                )),

                ('file:path', {}, (
                    ('dir', ('file:path', {}), {'ro': 1,
                                                'doc': 'The parent directory.'}),

                    ('base', ('file:base', {}), {'ro': 1,
                                                 'doc': 'The file base name.'}),

                    ('base:ext', ('str', {}), {'ro': 1,
                                               'doc': 'The file extension.'}),
                )),
            ),

        }

        name = 'file'
        return ((name, modl),)
