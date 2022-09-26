import base64
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lookup.pe as s_l_pe
import synapse.lookup.macho as s_l_macho

class FileBase(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        norm = valu.strip().lower().replace('\\', '/')
        if norm.find('/') != -1:
            mesg = 'file:base may not contain /'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        subs = {}
        if norm.find('.') != -1:
            subs['ext'] = norm.rsplit('.', 1)[1]

        return norm, {'subs': subs}

class FilePath(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):

        if len(valu) == 0:
            return '', {}

        lead = ''
        if valu[0] == '/':
            lead = '/'

        valu = valu.strip().lower().replace('\\', '/').strip('/')
        if not valu:
            return '', {}

        if valu in ('.', '..'):
            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='Cannot norm a bare relative path.')

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

class FileBytes(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyList)
        self.setNormFunc(tuple, self._normPyList)
        self.setNormFunc(bytes, self._normPyBytes)

    def _normPyList(self, valu):
        guid, info = self.modl.type('guid').norm(valu)
        norm = f'guid:{guid}'
        return norm, {}

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

            raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                    mesg='unadorned file:bytes value is not a sha256')

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
                raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                        mesg='guid is not a guid')

            return f'guid:{kval}', {}

        if kind == 'sha256':

            if len(kval) != 64:
                raise s_exc.BadTypeValu(name=self.name, valu=valu,
                                        mesg='invalid length for sha256 valu')

            s_common.uhex(kval)

            subs = {'sha256': kval}
            return f'sha256:{kval}', {'subs': subs}

        raise s_exc.BadTypeValu(name=self.name, valu=valu, kind=kind,
                                mesg='unable to norm as file:bytes')

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

    async def initCoreModule(self):
        self.model.prop('file:bytes:mime').onSet(self._onSetFileBytesMime)
        self.core._setPropSetHook('file:bytes:sha256', self._hookFileBytesSha256)

    async def _hookFileBytesSha256(self, node, prop, norm):
        # this gets called post-norm and curv checks
        if node.ndef[1].startswith('sha256:'):
            mesg = "Can't change :sha256 on a file:bytes with sha256 based primary property."
            raise s_exc.BadTypeValu(mesg=mesg)

    async def _onSetFileBytesMime(self, node, oldv):
        name = node.get('mime')
        if name == '??':
            return
        await node.snap.addNode('file:ismime', (node.ndef[1], name))

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

            'interfaces': (
                ('file:mime:meta', {
                    'props': (
                        ('file', ('file:bytes', {}), {
                            'doc': 'The file that the mime info was parsed from.'}),
                        ('file:offs', ('int', {}), {
                            'doc': 'The optional offset where the mime info was parsed from.'}),
                        ('file:data', ('data', {}), {
                            'doc': 'A mime specific arbitrary data structure for non-indexed data.',
                        }),
                    ),
                    'doc': 'Properties common to mime specific file metadata types.',
                }),
                ('file:mime:msoffice', {
                    'props': (
                        ('title', ('str', {}), {
                            'doc': 'The title extracted from Microsoft Office metadata.'}),
                        ('author', ('str', {}), {
                            'doc': 'The author extracted from Microsoft Office metadata.'}),
                        ('subject', ('str', {}), {
                            'doc': 'The subject extracted from Microsoft Office metadata.'}),
                        ('application', ('str', {}), {
                            'doc': 'The creating_application extracted from Microsoft Office metadata.'}),
                        ('created', ('time', {}), {
                            'doc': 'The create_time extracted from Microsoft Office metadata.'}),
                        ('lastsaved', ('time', {}), {
                            'doc': 'The last_saved_time extracted from Microsoft Office metadata.'}),
                    ),
                    'doc': 'Properties common to various microsoft office file formats.',
                    'interfaces': ('file:mime:meta',),
                }),
                ('file:mime:image', {
                    'props': (
                        ('desc', ('str', {}), {
                            'doc': 'MIME specific description field extracted from metadata.'}),
                        ('comment', ('str', {}), {
                            'doc': 'MIME specific comment field extracted from metadata.'}),
                        ('created', ('time', {}), {
                            'doc': 'MIME specific creation timestamp extracted from metadata.'}),
                        ('imageid', ('str', {}), {
                            'doc': 'MIME specific unique identifier extracted from metadata.'}),
                        ('author', ('ps:contact', {}), {
                            'doc': 'MIME specific contact information extracted from metadata.'}),
                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'MIME specific lat/long information extracted from metadata.'}),
                        ('altitude', ('geo:altitude', {}), {
                            'doc': 'MIME specific altitude information extracted from metadata.'}),
                    ),
                    'doc': 'Properties common to image file formats.',
                    'interfaces': ('file:mime:meta',),
                }),
                ('file:mime:macho:loadcmd', {
                    'props': (
                        ('file', ('file:bytes', {}), {
                            'doc': 'The Mach-O file containing the load command.'}),
                        ('type', ('int', {'enums': s_l_macho.getLoadCmdTypes()}), {
                            'doc': 'The type of the load command'}),
                        ('size', ('int', {}), {
                            'doc': 'The size of the load command structure in bytes.'}),
                    ),
                    'doc': 'Properties common to all Mach-O load commands',
                })
            ),

            'types': (

                ('file:subfile', ('comp', {'fields': (('parent', 'file:bytes'), ('child', 'file:bytes'))}), {
                    'doc': 'A parent file that fully contains the specified child file.',
                }),

                ('file:filepath', ('comp', {'fields': (('file', 'file:bytes'), ('path', 'file:path'))}), {
                    'doc': 'The fused knowledge of the association of a file:bytes node and a file:path.',
                }),

                ('file:mime', ('str', {'lower': 1}), {
                    'doc': 'A file mime name string.',
                    'ex': 'text/plain',
                }),

                ('file:ismime', ('comp', {'fields': (('file', 'file:bytes'), ('mime', 'file:mime'))}), {
                    'doc': 'Records one, of potentially multiple, mime types for a given file.',
                }),

                ('file:mime:msdoc', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a Microsoft Word file.',
                    'interfaces': ('file:mime:msoffice',),
                }),

                ('file:mime:msxls', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a Microsoft Excel file.',
                    'interfaces': ('file:mime:msoffice',),
                }),

                ('file:mime:msppt', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a Microsoft Powerpoint file.',
                    'interfaces': ('file:mime:msoffice',),
                }),

                ('file:mime:rtf', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a .rtf file.',
                    'interfaces': ('file:mime:meta',),
                }),

                ('file:mime:jpg', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a .jpg file.',
                    'interfaces': ('file:mime:image',),
                }),

                ('file:mime:tif', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a .tif file.',
                    'interfaces': ('file:mime:image',),
                }),

                ('file:mime:gif', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a .gif file.',
                    'interfaces': ('file:mime:image',),
                }),

                ('file:mime:png', ('guid', {}), {
                    'doc': 'The GUID of a set of mime metadata for a .png file.',
                    'interfaces': ('file:mime:image',),
                }),

                ('file:mime:pe:section', ('comp', {'fields': (
                        ('file', 'file:bytes'),
                        ('name', 'str'),
                        ('sha256', 'hash:sha256'),
                    )}), {
                    'doc': 'The fused knowledge a file:bytes node containing a pe section.',
                }),
                ('file:mime:pe:resource', ('comp', {'fields': (
                        ('file', 'file:bytes'),
                        ('type', 'pe:resource:type'),
                        ('langid', 'pe:langid'),
                        ('resource', 'file:bytes'))}), {
                    'doc': 'The fused knowledge of a file:bytes node containing a pe resource.',
                }),
                ('file:mime:pe:export', ('comp', {'fields': (
                        ('file', 'file:bytes'),
                        ('name', 'str'))}), {
                    'doc': 'The fused knowledge of a file:bytes node containing a pe named export.',
                }),
                ('file:mime:pe:vsvers:keyval', ('comp', {'fields': (
                        ('name', 'str'),
                        ('value', 'str'))}), {
                    'doc': 'A key value pair found in a PE vsversion info structure.',
                }),
                ('file:mime:pe:vsvers:info', ('comp', {'fields': (
                        ('file', 'file:bytes'),
                        ('keyval', 'file:mime:pe:vsvers:keyval'))}), {
                    'doc': 'knowledge of a file:bytes node containing vsvers info.',
                }),
                ('file:string', ('comp', {'fields': (
                        ('file', 'file:bytes'),
                        ('string', 'str'))}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use the edge -(refs)> it:dev:str.',
                }),

                ('pe:resource:type', ('int', {'enums': s_l_pe.getRsrcTypes()}), {
                    'doc': 'The typecode for the resource.',
                }),

                ('pe:langid', ('int', {'enums': s_l_pe.getLangCodes()}), {
                    'doc': 'The PE language id.',
                }),

                ('file:mime:macho:loadcmd', ('guid', {}), {
                    'doc': 'A generic load command pulled from the Mach-O headers.',
                    'interfaces': ('file:mime:macho:loadcmd',),
                }),

                ('file:mime:macho:version', ('guid', {}), {
                    'doc': 'A specific load command used to denote the version of the source used to build the Mach-O binary.',
                    'interfaces': ('file:mime:macho:loadcmd',),
                }),

                ('file:mime:macho:uuid', ('guid', {}), {
                    'doc': 'A specific load command denoting a UUID used to uniquely identify the Mach-O binary.',
                    'interfaces': ('file:mime:macho:loadcmd',),
                }),

                ('file:mime:macho:segment', ('guid', {}), {
                    'doc': 'A named region of bytes inside a Mach-O binary.',
                    'interfaces': ('file:mime:macho:loadcmd',),
                }),

                ('file:mime:macho:section', ('guid', {}), {
                    'doc': 'A section inside a Mach-O binary denoting a named region of bytes inside a segment.',
                }),

            ),

            'forms': (

                ('file:bytes', {}, (

                    ('size', ('int', {}), {'doc': 'The file size in bytes.'}),

                    ('md5', ('hash:md5', {}), {'doc': 'The md5 hash of the file.'}),

                    ('sha1', ('hash:sha1', {}), {'doc': 'The sha1 hash of the file.'}),

                    ('sha256', ('hash:sha256', {}), {'doc': 'The sha256 hash of the file.'}),

                    ('sha512', ('hash:sha512', {}), {'doc': 'The sha512 hash of the file.'}),

                    ('name', ('file:base', {}), {
                        'doc': 'The best known base name for the file.'}),

                    ('mime', ('file:mime', {}), {
                        'doc': 'The "best" mime type name for the file.'}),

                    ('mime:x509:cn', ('str', {}), {
                        'doc': 'The Common Name (CN) attribute of the x509 Subject.'}),

                    ('mime:pe:size', ('int', {}), {
                        'doc': 'The size of the executable file according to the PE file header.'}),

                    ('mime:pe:imphash', ('guid', {}), {
                        'doc': 'The PE import hash of the file as calculated by pefile; '
                               'https://github.com/erocarrera/pefile .'}),

                    ('mime:pe:compiled', ('time', {}), {
                        'doc': 'The compile time of the file according to the PE header.'}),

                    ('mime:pe:pdbpath', ('file:path', {}), {
                        'doc': 'The PDB string according to the PE.'}),

                    ('mime:pe:exports:time', ('time', {}), {
                        'doc': 'The export time of the file according to the PE.'}),

                    ('mime:pe:exports:libname', ('str', {}), {
                        'doc': 'The export library name according to the PE.'}),

                    ('mime:pe:richhdr', ('hash:sha256', {}), {
                        'doc': 'The sha256 hash of the rich header bytes.'}),

                )),

                ('file:mime', {}, ()),

                ('file:ismime', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file node that is an instance of the named mime type.',
                    }),
                    ('mime', ('file:mime', {}), {
                        'ro': True,
                        'doc': 'The mime type of the file.',
                    }),
                )),

                ('file:mime:msdoc', {}, ()),
                ('file:mime:msxls', {}, ()),
                ('file:mime:msppt', {}, ()),

                ('file:mime:jpg', {}, ()),
                ('file:mime:tif', {}, ()),
                ('file:mime:gif', {}, ()),
                ('file:mime:png', {}, ()),

                ('file:mime:rtf', {}, (
                    ('guid', ('guid', {}), {
                        'doc': 'The parsed GUID embedded in the .rtf file.'}),
                )),

                ('file:mime:pe:section', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file containing the section.',
                    }),
                    ('name', ('str', {}), {
                        'ro': True,
                        'doc': 'The textual name of the section.',
                    }),
                    ('sha256', ('hash:sha256', {}), {
                        'ro': True,
                        'doc': 'The sha256 hash of the section. Relocations must be zeroed before hashing.',
                    }),
                )),

                ('file:mime:pe:resource', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file containing the resource.',
                    }),
                    ('type', ('pe:resource:type', {}), {
                        'ro': True,
                        'doc': 'The typecode for the resource.',
                    }),
                    ('langid', ('pe:langid', {}), {
                        'ro': True,
                        'doc': 'The language code for the resource.',
                    }),
                    ('resource', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The sha256 hash of the resource bytes.',
                    }),
                )),

                ('file:mime:pe:export', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file containing the export.',
                    }),
                    ('name', ('str', {}), {
                        'ro': True,
                        'doc': 'The name of the export in the file.',
                    }),
                )),

                ('file:mime:pe:vsvers:keyval', {}, (
                    ('name', ('str', {}), {
                        'ro': True,
                        'doc': 'The key for the vsversion keyval pair.',
                    }),
                    ('value', ('str', {}), {
                        'ro': True,
                        'doc': 'The value for the vsversion keyval pair.',
                    }),
                )),

                ('file:mime:pe:vsvers:info', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file containing the vsversion keyval pair.',
                    }),
                    ('keyval', ('file:mime:pe:vsvers:keyval', {}), {
                        'ro': True,
                        'doc': 'The vsversion info keyval in this file:bytes node.',
                    }),
                )),

                ('file:string', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file containing the string.',
                    }),
                    ('string', ('str', {}), {
                        'ro': True,
                        'doc': 'The string contained in this file:bytes node.',
                    }),
                )),

                ('file:base', {}, (
                    ('ext', ('str', {}), {'ro': True,
                        'doc': 'The file extension (if any).'}),
                )),

                ('file:filepath', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file seen at a path.',
                    }),
                    ('path', ('file:path', {}), {
                        'ro': True,
                        'doc': 'The path a file was seen at.',
                    }),
                    ('path:dir', ('file:path', {}), {
                        'ro': True,
                        'doc': 'The parent directory.',
                    }),
                    ('path:base', ('file:base', {}), {
                        'ro': True,
                        'doc': 'The name of the file.',
                    }),
                    ('path:base:ext', ('str', {}), {
                        'ro': True,
                        'doc': 'The extension of the file name.',
                    }),
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
                        'deprecated': True,
                        'doc': 'Deprecated, please use the :path property.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path that the parent uses to refer to the child file.',
                    }),
                )),

                ('file:path', {}, (
                    ('dir', ('file:path', {}), {'ro': True,
                        'doc': 'The parent directory.'}),

                    ('base', ('file:base', {}), {'ro': True,
                        'doc': 'The file base name.'}),

                    ('base:ext', ('str', {}), {'ro': True,
                        'doc': 'The file extension.'}),
                )),

                ('file:mime:macho:loadcmd', {}, ()),
                ('file:mime:macho:version', {}, (
                    ('version', ('str', {}), {
                        'doc': 'The version of the Mach-O file encoded in an LC_VERSION load command.'}),
                )),
                ('file:mime:macho:uuid', {}, (
                    ('uuid', ('guid', {}), {
                        'doc': 'The UUID of the Mach-O application (as defined in an LC_UUID load command).'}),
                )),
                ('file:mime:macho:segment', {}, (
                    ('name', ('str', {}), {
                        'doc': 'The name of the Mach-O segment.'}),
                    ('memsize', ('int', {}), {
                        'doc': 'The size of the segment in bytes, when resident in memory, according to the load command structure.'}),
                    ('disksize', ('int', {}), {
                        'doc': 'The size of the segment in bytes, when on disk, according to the load command structure.'}),
                    ('sha256', ('hash:sha256', {}), {
                        'doc': 'The sha256 hash of the bytes of the segment.'}),
                    ('offset', ('int', {}), {
                        'doc': 'The file offset to the beginning of the segment.'}),
                )),
                ('file:mime:macho:section', {}, (
                    ('segment', ('file:mime:macho:segment', {}), {
                        'doc': 'The Mach-O segment that contains this section.'}),
                    ('name', ('str', {}), {
                        'doc': 'Name of the section.'}),
                    ('size', ('int', {}), {
                        'doc': 'Size of the section in bytes.'}),
                    ('type', ('int', {'enums': s_l_macho.getSectionTypes()}), {
                        'doc': 'The type of the section.'}),
                    ('sha256', ('hash:sha256', {}), {
                        'doc': 'The sha256 hash of the bytes of the Mach-O section.'}),
                    ('offset', ('int', {}), {
                        'doc': 'The file offset to the beginning of the section'}),
                )),

            ),

        }

        name = 'file'
        return ((name, modl),)
