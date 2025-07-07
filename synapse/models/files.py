import base64
import hashlib
import binascii

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.types as s_types
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

        self.exttype = self.modl.type('str')
        self.basetype = self.modl.type('file:base')

        self.virtindx |= {
            'dir': 'dir',
            'ext': 'ext',
            'base': 'base',
        }

        self.virts |= {
            'dir': (self, self._getDir),
            'ext': (self.exttype, self._getExt),
            'base': (self.basetype, self._getBase),
        }

    def _getDir(self, valu):
        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('dir')) is None:
            return None

        return valu[0]

    def _getExt(self, valu):
        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('ext')) is None:
            return None

        return valu[0]

    def _getBase(self, valu):
        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('base')) is None:
            return None

        return valu[0]

    def _normPyStr(self, valu):

        if len(valu) == 0:
            return '', {}

        valu = valu.strip().lower().replace('\\', '/')
        if not valu:
            return '', {}

        lead = ''
        if valu[0] == '/':
            lead = '/'

        valu = valu.strip('/')
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

        if len(path) == 0:
            return '', {}

        fullpath = lead + '/'.join(path)

        base = path[-1]
        subs = {'base': base}
        virts = {'base': (base, self.basetype.stortype)}

        if '.' in base:
            ext = base.rsplit('.', 1)[1]
            subs['ext'] = ext
            virts['ext'] = (ext, self.exttype.stortype)

        if len(path) > 1:
            dirn = lead + '/'.join(path[:-1])
            subs['dir'] = dirn
            virts['dir'] = (dirn, self.stortype)

        return fullpath, {'subs': subs, 'virts': virts}

modeldefs = (
    ('file', {
        'ctors': (

            ('file:base', 'synapse.models.files.FileBase', {}, {
                'doc': 'A file name with no path.',
                'ex': 'woot.exe'}),

            ('file:path', 'synapse.models.files.FilePath', {}, {
                'doc': 'A normalized file path.',
                'ex': 'c:/windows/system32/calc.exe'}),
        ),

        'interfaces': (
            ('file:mime:meta', {
                'template': {'metadata': 'metadata'},
                'props': (
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file that the mime info was parsed from.'}),

                    ('file:offs', ('int', {}), {
                        'doc': 'The offset of the {metadata} within the file.'}),

                    ('file:size', ('int', {}), {
                        'doc': 'The size of the {metadata} within the file.'}),

                    ('file:data', ('data', {}), {
                        'doc': 'A mime specific arbitrary data structure for non-indexed data.'}),
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
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
            }),
            ('file:mime:image', {
                'props': (

                    ('id', ('meta:id', {}), {
                        'prevnames': ('imageid',),
                        'doc': 'MIME specific unique identifier extracted from metadata.'}),

                    ('desc', ('str', {}), {
                        'doc': 'MIME specific description field extracted from metadata.'}),

                    ('comment', ('str', {}), {
                        'doc': 'MIME specific comment field extracted from metadata.'}),

                    ('created', ('time', {}), {
                        'doc': 'MIME specific creation timestamp extracted from metadata.'}),

                    ('author', ('entity:contact', {}), {
                        'doc': 'MIME specific contact information extracted from metadata.'}),

                    # FIXME geo:locatable?
                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'MIME specific lat/long information extracted from metadata.'}),

                    ('altitude', ('geo:altitude', {}), {
                        'doc': 'MIME specific altitude information extracted from metadata.'}),

                    ('text', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The text contained within the image.'}),
                ),
                'doc': 'Properties common to image file formats.',
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
            }),
            ('file:mime:macho:loadcmd', {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (
                    ('type', ('int', {'enums': s_l_macho.getLoadCmdTypes()}), {
                        'doc': 'The type of the load command.'}),
                ),
                'doc': 'Properties common to all Mach-O load commands.',
            })
        ),

        'types': (

            ('file:bytes', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'observable': 'file'}}),
                ),
                'doc': 'A file.'}),

            ('file:subfile', ('comp', {'fields': (('parent', 'file:bytes'), ('child', 'file:bytes'))}), {
                'doc': 'A parent file that fully contains the specified child file.'}),

            ('file:attachment', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'file'}},
                        {'type': 'prop', 'opts': {'name': 'text'}},
                    ),
                },
                'doc': 'A file attachment.'}),

            ('file:archive:entry', ('guid', {}), {
                'doc': 'An archive entry representing a file and metadata within a parent archive file.'}),

            ('file:filepath', ('comp', {'fields': (('file', 'file:bytes'), ('path', 'file:path'))}), {
                'doc': 'The fused knowledge of the association of a file:bytes node and a file:path.'}),

            ('file:mime', ('str', {'lower': True}), {
                'ex': 'text/plain',
                'doc': 'A file mime name string.'}),

            ('file:mime:msdoc', ('guid', {}), {
                'interfaces': (
                    ('file:mime:msoffice', {}),
                ),
                'doc': 'Metadata about a Microsoft Word file.'}),

            ('file:mime:msxls', ('guid', {}), {
                'interfaces': (
                    ('file:mime:msoffice', {}),
                ),
                'doc': 'Metadata about a Microsoft Excel file.'}),

            ('file:mime:msppt', ('guid', {}), {
                'interfaces': (
                    ('file:mime:msoffice', {}),
                ),
                'doc': 'Metadata about a Microsoft Powerpoint file.'}),

            ('file:mime:pe', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'doc': 'Metadata about a Microsoft Portable Executable (PE) file.',
            }),

            ('file:mime:rtf', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'doc': 'The GUID of a set of mime metadata for a .rtf file.'}),

            ('file:mime:jpg', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'doc': 'The GUID of a set of mime metadata for a .jpg file.'}),

            ('file:mime:tif', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'doc': 'The GUID of a set of mime metadata for a .tif file.'}),

            ('file:mime:gif', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'doc': 'The GUID of a set of mime metadata for a .gif file.'}),

            ('file:mime:png', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'doc': 'The GUID of a set of mime metadata for a .png file.'}),

            ('file:mime:pe:section', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'doc': 'A PE section contained in a file.'}),

            ('file:mime:pe:resource', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'doc': 'A PE resource contained in a file.'}),

            ('file:mime:pe:export', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'doc': 'A named PE export contained in a file.'}),

            ('file:mime:pe:vsvers:keyval', ('comp', {'fields': (('name', 'str'), ('value', 'str'))}), {
                'doc': 'A key value pair found in a PE VS_VERSIONINFO structure.'}),

            ('pe:resource:type', ('int', {'enums': s_l_pe.getRsrcTypes()}), {
                'doc': 'The typecode for the resource.'}),

            ('pe:langid', ('int', {'enums': s_l_pe.getLangCodes()}), {
                'doc': 'The PE language id.'}),

            ('file:mime:macho:loadcmd', ('guid', {}), {
                'interfaces': (
                    ('file:mime:macho:loadcmd', {}),
                ),
                'doc': 'A generic load command pulled from the Mach-O headers.'}),

            ('file:mime:macho:version', ('guid', {}), {
                'interfaces': (
                    ('file:mime:macho:loadcmd', {}),
                ),
                'doc': 'A specific load command used to denote the version of the source used to build the Mach-O binary.'}),

            ('file:mime:macho:uuid', ('guid', {}), {
                'interfaces': (
                    ('file:mime:macho:loadcmd', {}),
                ),
                'doc': 'A specific load command denoting a UUID used to uniquely identify the Mach-O binary.'}),

            ('file:mime:macho:segment', ('guid', {}), {
                'interfaces': (
                    ('file:mime:macho:loadcmd', {}),
                ),
                'doc': 'A named region of bytes inside a Mach-O binary.'}),

            ('file:mime:macho:section', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'doc': 'A section inside a Mach-O binary denoting a named region of bytes inside a segment.'}),

            ('file:mime:lnk', ('guid', {}), {
                'doc': 'The GUID of the metadata pulled from a Windows shortcut or LNK file.'}),
        ),
        'edges': (

            (('file:bytes', 'refs', 'it:dev:str'), {
                'doc': 'The source file contains the target string.'}),

            # FIXME picturable?
            # (('file:mime:image', 'imageof', None), {
        ),
        'forms': (

            ('file:bytes', {}, (

                ('size', ('int', {}), {
                    'doc': 'The file size in bytes.'}),

                ('md5', ('crypto:hash:md5', {}), {
                    'doc': 'The MD5 hash of the file.'}),

                ('sha1', ('crypto:hash:sha1', {}), {
                    'doc': 'The SHA1 hash of the file.'}),

                ('sha256', ('crypto:hash:sha256', {}), {
                    'doc': 'The SHA256 hash of the file.'}),

                ('sha512', ('crypto:hash:sha512', {}), {
                    'doc': 'The SHA512 hash of the file.'}),

                ('name', ('file:base', {}), {
                    'doc': 'The best known base name for the file.'}),

                ('mime', ('file:mime', {}), {
                    'doc': 'The "best" mime type name for the file.'}),

                ('mimes', ('array', {'type': 'file:mime', 'sorted': True, 'uniq': True}), {
                    'doc': 'An array of alternate mime types for the file.'}),

                # FIXME file:mime:exe interface?
                # ('exe:compiler', ('it:software', {}), {
                #     'doc': 'The software used to compile the file.'}),

                # ('exe:packer', ('it:software', {}), {
                #     'doc': 'The packer software used to encode the file.'}),
            )),

            ('file:mime', {}, ()),

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

            ('file:mime:pe', {}, (

                ('size', ('int', {}), {
                    'doc': 'The size of the executable file according to the PE file header.'}),

                ('imphash', ('crypto:hash:md5', {}), {
                    'doc': 'The PE import hash of the file as calculated by pefile; '
                           'https://github.com/erocarrera/pefile .'}),

                ('richheader', ('crypto:hash:sha256', {}), {
                    'doc': 'The sha256 hash of the rich header bytes.'}),

                ('compiled', ('time', {}), {
                    'doc': 'The PE compile time of the file.'}),

                ('pdbpath', ('file:path', {}), {
                    'doc': 'The PDB file path.'}),

                ('exports:time', ('time', {}), {
                    'doc': 'The export time of the file.'}),

                ('exports:libname', ('str', {}), {
                    'doc': 'The export library name according to the PE.'}),

                ('versioninfo', ('array', {'type': 'file:mime:pe:vsvers:keyval', 'sorted': True, 'uniq': True}), {
                    'doc': 'The VS_VERSIONINFO key/value data from the PE file.'}),
            )),

            ('file:mime:pe:section', {}, (

                ('name', ('str', {}), {
                    'doc': 'The textual name of the section.'}),

                ('sha256', ('crypto:hash:sha256', {}), {
                    'doc': 'The sha256 hash of the section. Relocations must be zeroed before hashing.'}),
            )),

            ('file:mime:pe:resource', {}, (

                ('type', ('pe:resource:type', {}), {
                    'doc': 'The typecode for the resource.'}),

                ('langid', ('pe:langid', {}), {
                    'doc': 'The language code for the resource.'}),

                ('sha256', ('crypto:hash:sha256', {}), {
                    'doc': 'The SHA256 hash of the resource bytes.'}),
            )),

            ('file:mime:pe:export', {}, (

                ('name', ('str', {}), {
                    'doc': 'The name of the export in the file.'}),

                ('rva', ('int', {}), {
                    'doc': 'The Relative Virtual Address of the exported function entry point.'}),
            )),

            ('file:mime:pe:vsvers:keyval', {}, (

                ('name', ('str', {}), {
                    'ro': True,
                    'doc': 'The key for the VS_VERSIONINFO keyval pair.'}),

                ('value', ('str', {}), {
                    'ro': True,
                    'doc': 'The value for the VS_VERSIONINFO keyval pair.'}),
            )),

            ('file:base', {}, (
                ('ext', ('str', {}), {'ro': True,
                    'doc': 'The file extension (if any).'}),
            )),

            ('file:filepath', {}, (

                ('file', ('file:bytes', {}), {
                    'ro': True,
                    'doc': 'The file seen at a path.'}),

                ('path', ('file:path', {}), {
                    'ro': True,
                    'doc': 'The path a file was seen at.'}),

            )),

            ('file:attachment', {}, (

                ('name', ('file:path', {}), {
                    'doc': 'The name of the attached file.'}),

                ('text', ('str', {}), {
                    'doc': 'Any text associated with the file such as alt-text for images.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file which was attached.'}),
            )),

            ('file:archive:entry', {}, (

                ('parent', ('file:bytes', {}), {
                    'doc': 'The parent archive file.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file contained within the archive.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The file path of the archived file.'}),

                ('user', ('inet:user', {}), {
                    'doc': 'The name of the user who owns the archived file.'}),

                ('added', ('time', {}), {
                    'doc': 'The time that the file was added to the archive.'}),

                ('created', ('time', {}), {
                    'doc': 'The created time of the archived file.'}),

                ('modified', ('time', {}), {
                    'doc': 'The modified time of the archived file.'}),

                ('comment', ('str', {}), {
                    'doc': 'The comment field for the file entry within the archive.'}),

                ('posix:uid', ('int', {}), {
                    'doc': 'The POSIX UID of the user who owns the archived file.'}),

                ('posix:gid', ('int', {}), {
                    'doc': 'The POSIX GID of the group who owns the archived file.'}),

                ('posix:perms', ('int', {}), {
                    'doc': 'The POSIX permissions mask of the archived file.'}),

                ('archived:size', ('int', {}), {
                    'doc': 'The encoded or compressed size of the archived file within the parent.'}),
            )),

            ('file:subfile', {}, (
                ('parent', ('file:bytes', {}), {
                    'ro': True,
                    'doc': 'The parent file containing the child file.'}),

                ('child', ('file:bytes', {}), {
                    'ro': True,
                    'doc': 'The child file contained in the parent file.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path that the parent uses to refer to the child file.'}),
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

                ('sha256', ('crypto:hash:sha256', {}), {
                    'doc': 'The sha256 hash of the bytes of the segment.'}),
            )),
            ('file:mime:macho:section', {}, (

                ('segment', ('file:mime:macho:segment', {}), {
                    'doc': 'The Mach-O segment that contains this section.'}),

                ('name', ('str', {}), {
                    'doc': 'Name of the section.'}),

                ('type', ('int', {'enums': s_l_macho.getSectionTypes()}), {
                    'doc': 'The type of the section.'}),

                ('sha256', ('crypto:hash:sha256', {}), {
                    'doc': 'The sha256 hash of the bytes of the Mach-O section.'}),
            )),

            ('file:mime:lnk', {}, (

                ('flags', ('int', {}), {
                    'doc': 'The flags specified by the LNK header that control the structure of the LNK file.'}),

                ('entry:primary', ('file:path', {}), {
                    'doc': 'The primary file path contained within the FileEntry structure of the LNK file.'}),

                ('entry:secondary', ('file:path', {}), {
                    'doc': 'The secondary file path contained within the FileEntry structure of the LNK file.'}),

                ('entry:extended', ('file:path', {}), {
                    'doc': 'The extended file path contained within the extended FileEntry structure of the LNK file.'}),

                ('entry:localized', ('file:path', {}), {
                    'doc': 'The localized file path reconstructed from references within the extended FileEntry structure of the LNK file.'}),

                ('entry:icon', ('file:path', {}), {
                    'doc': 'The icon file path contained within the StringData structure of the LNK file.'}),

                ('environment:path', ('file:path', {}), {
                    'doc': 'The target file path contained within the EnvironmentVariableDataBlock structure of the LNK file.'}),

                ('environment:icon', ('file:path', {}), {
                    'doc': 'The icon file path contained within the IconEnvironmentDataBlock structure of the LNK file.'}),

                ('iconindex', ('int', {}), {
                    'doc': 'A resource index for an icon within an icon location.'}),

                ('working', ('file:path', {}), {
                    'doc': 'The working directory used when activating the link target.'}),

                ('relative', ('str', {'strip': True}), {
                    'doc': 'The relative target path string contained within the StringData structure of the LNK file.'}),

                ('arguments', ('it:cmd', {}), {
                    'doc': 'The command line arguments passed to the target file when the LNK file is activated.'}),

                ('desc', ('text', {}), {
                    'doc': 'The description of the LNK file contained within the StringData section of the LNK file.'}),

                ('target:attrs', ('int', {}), {
                    'doc': 'The attributes of the target file according to the LNK header.'}),

                ('target:size', ('int', {}), {
                    'doc': 'The size of the target file according to the LNK header. The LNK format specifies that this is only the lower 32 bits of the target file size.'}),

                ('target:created', ('time', {}), {
                    'doc': 'The creation time of the target file according to the LNK header.'}),

                ('target:accessed', ('time', {}), {
                    'doc': 'The access time of the target file according to the LNK header.'}),

                ('target:written', ('time', {}), {
                    'doc': 'The write time of the target file according to the LNK header.'}),

                ('driveserial', ('int', {}), {
                    'doc': 'The drive serial number of the volume the link target is stored on.'}),

                ('machineid', ('it:hostname', {}), {
                    'doc': 'The NetBIOS name of the machine where the link target was last located.'}),
            )),
        ),
    }),
)
