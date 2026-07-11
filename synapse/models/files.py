
import synapse.exc as s_exc
import synapse.lib.types as s_types
import synapse.lookup.pe as s_l_pe
import synapse.lookup.macho as s_l_macho

class FileBase(s_types.Text):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.exttype = self.modl.type('text')

    async def _normPyStr(self, valu, view=None):

        norm = valu.strip().replace('\\', '/')
        if norm.find('/') != -1:
            mesg = 'file:base may not contain /'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        info = {}
        if norm.find('.') != -1:
            info['subs'] = {'ext': (self.exttype.typehash, norm.rsplit('.', 1)[1], {})}

        return norm, info

class FilePath(s_types.Text):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.exttype = self.modl.type('text')
        self.basetype = self.modl.type('file:base')

        self.virtindx |= {
            'dir': 'dir',
            'base': 'base',
            'ext': 'ext',
        }

        self.virts |= {
            'dir': (self, self._getDir),
            'base': (self.basetype, self._getBase),
            'ext': (self.exttype, self._getExt),
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

    async def _normPyStr(self, valu, view=None):

        if len(valu) == 0:
            return '', {}

        valu = valu.strip().replace('\\', '/')
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
        info = {}

        if '.' in base:
            ext = base.rsplit('.', 1)[1]
            baseinfo = {'subs': {'ext': (self.exttype.typehash, ext, {})}}
            self.setVirtInfo(info, 'base', base, self.basetype, baseinfo)
            self.setVirtInfo(info, 'ext', ext, self.exttype)
        else:
            self.setVirtInfo(info, 'base', base, self.basetype, {})

        if len(path) > 1:
            dirn, dirinfo = await self._normPyStr(lead + '/'.join(path[:-1]))
            self.setVirtInfo(info, 'dir', dirn, self, dirinfo)

        return fullpath, info

modeldefs = (
    {
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
                    ('title', ('text', {}), {
                        'doc': 'The title extracted from Microsoft Office metadata.'}),
                    ('author', ('entity:contact', {}), {
                        'doc': 'The author extracted from Microsoft Office metadata.'}),
                    ('author:name', ('entity:name', {}), {
                        'doc': 'The author name extracted from Microsoft Office metadata.'}),
                    ('subject', ('text', {}), {
                        'doc': 'The subject extracted from Microsoft Office metadata.'}),
                    ('application', ('it:software', {}), {
                        'doc': 'The creating application extracted from Microsoft Office metadata.'}),
                    ('application:name', ('it:softwarename', {}), {
                        'doc': 'The creating application name extracted from Microsoft Office metadata.'}),
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

                    ('id', ('base:id', {}), {
                        'prevnames': ('imageid',),
                        'doc': 'MIME specific unique identifier extracted from metadata.'}),

                    ('desc', ('text', {}), {
                        'doc': 'MIME specific description field extracted from metadata.'}),

                    ('comment', ('text', {}), {
                        'doc': 'MIME specific comment field extracted from metadata.'}),

                    ('created', ('time', {}), {
                        'doc': 'MIME specific creation timestamp extracted from metadata.'}),

                    ('author', ('entity:contact', {}), {
                        'doc': 'MIME specific contact information extracted from metadata.'}),

                    ('author:name', ('entity:name', {}), {
                        'doc': 'MIME specific author name extracted from metadata.'}),

                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'MIME specific lat/long information extracted from metadata.'}),

                    ('altitude', ('geo:altitude', {}), {
                        'doc': 'MIME specific altitude information extracted from metadata.'}),

                    ('text', ('text', {}), {
                        'doc': 'The text contained within the image.'}),
                ),
                'doc': 'Properties common to image file formats.',
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
            }),
            ('file:mime:exe', {
                'doc': 'Properties common to executable file formats.',
                'template': {'executable': 'executable'},
                'props': (
                    ('compiler', ('it:software', {}), {
                        'doc': 'The software used to compile the {executable}.'}),

                    ('compiler:name', ('it:softwarename', {}), {
                        'doc': 'The name of the software used to compile the {executable}.'}),

                    ('packer', ('it:software', {}), {
                        'doc': 'The software used to pack the {executable}.'}),

                    ('packer:name', ('it:softwarename', {}), {
                        'doc': 'The name of the software used to pack the {executable}.'}),
                ),
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
            }),
            ('file:entry', {
                'template': {'title': 'file entry'},
                'doc': 'Properties common to forms representing a file at a path.',
                'props': (
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file associated with the {title}.'}),

                    ('path', ('file:path', {}), {
                        'doc': 'The path of the file associated with the {title}.'}),
                ),
            }),
        ),

        'types': (

            ('file:base', (None, {'ctor': 'synapse.models.files.FileBase'}), {
                'template': {'title': 'file name'},
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:observable', {}),
                ),
                'ex': 'woot.exe',
                'props': (
                    ('ext', ('text', {}), {'computed': True,
                        'doc': 'The file extension (if any).'}),
                ),
                'doc': 'A file name with no path.'}),

            ('file:path', (None, {'ctor': 'synapse.models.files.FilePath'}), {
                'template': {'title': 'file path'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'virts': (
                    ('dir', ('file:path', {}), {
                        'computed': True,
                        'doc': 'The directory from the path.'}),

                    ('base', ('file:base', {}), {
                        'computed': True,
                        'doc': 'The file base name from the path.'}),

                    ('ext', ('text', {}), {
                        'computed': True,
                        'doc': 'The file extension from the path.'}),
                ),
                'ex': 'c:/windows/system32/calc.exe',
                'props': (),
                'doc': 'A normalized file path.'}),

            ('file:bytes', ('guid', {}), {
                'template': {'title': 'file'},
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:observable', {}),
                ),
                'props': (

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

                    ('ssdeeps', ('crypto:hash:ssdeep', {}), {
                        'array': {},
                        'doc': 'The ssdeep fuzzy hashes of the file.'}),

                    ('name', ('file:base', {}), {
                        'doc': 'The best known base name for the file.'}),

                    ('mime', ('file:mime', {}), {
                        'doc': 'The "best" mime type name for the file.'}),

                    ('mimes', ('file:mime', {}), {
                        'array': {},
                        'doc': 'An array of alternate mime types for the file.'}),
                ),
                'doc': 'A file.'}),

            ('file:exemplar:entry', ('guid', {}), {
                'template': {'title': 'exemplar file entry'},
                'interfaces': (
                    ('file:entry', {}),
                    ('meta:observable', {}),
                ),
                'props': (),
                'doc': 'An exemplar file entry used to model behavior.'}),

            ('file:stored:entry', ('guid', {}), {
                'template': {'title': 'stored file entry'},
                'interfaces': (
                    ('file:entry', {}),
                    ('meta:observable', {}),
                ),
                'props': (
                    ('added', ('time', {}), {
                        'doc': 'The time that the file entry was added.'}),

                    ('created', ('time', {}), {
                        'doc': 'The created time of the file.'}),

                    ('modified', ('time', {}), {
                        'doc': 'The last known modified time of the file.'}),

                    ('accessed', ('time', {}), {
                        'doc': 'The last known accessed time of the file.'}),
                ),
                'doc': 'A stored file entry.'}),

            ('file:system:entry', ('file:stored:entry', {}), {
                'props': (

                    ('host', ('it:host', {}), {
                        'doc': 'The host which contains the filesystem.'}),

                    ('owner', ('it:host:account', {}), {
                        'doc': 'The host account which owns the file.'}),

                    ('creator', ('it:host:account', {}), {
                        'doc': 'The host account which created the file.'}),

                    # TODO: volume=<it:host:volume>?
                ),
                'doc': 'A file entry contained by a host filesystem.'}),

            # we can now extend types of filesystem entries to capture details!
            # ('file:system:ext3:entry', ('file:system:entry', {}), {}),
            # ('file:system:ntfs:entry', ('file:system:entry', {}), {}),

            ('file:subfile:entry', ('file:stored:entry', {}), {
                'template': {'title': 'subfile entry'},
                'props': (

                    ('parent', ('file:bytes', {}), {
                        'doc': 'The parent file which contains the {title}.'}),

                    ('offset', ('size', {}), {
                        'doc': 'The offset to the beginning of the file within the parent file.'}),
                ),
                'doc': 'A file entry contained by a parent file.'}),

            ('file:archive:entry', ('file:subfile:entry', {}), {
                'template': {'title': 'archive file entry'},
                'props': (
                    ('archived:size', ('size', {}), {
                        'doc': 'The storage size of the file within the archive.'}),
                ),
                'doc': 'A file entry contained by an archive file.'}),

            ('file:mime:rar:entry', ('file:archive:entry', {}), {
                'props': (
                    ('extra:posix:perms', ('int', {}), {
                        'doc': 'The POSIX permissions mask of the archived file.'}),
                ),
                'template': {'title': 'RAR archive file entry'},
                'doc': 'A file entry contained by a RAR archive file.'}),

            ('file:mime:zip:entry', ('file:archive:entry', {}), {
                'template': {'title': 'ZIP archive file entry'},
                'props': (

                    ('comment', ('text', {}), {
                        'doc': 'The comment field from the CDFH in the ZIP archive.'}),

                    ('extra:posix:uid', ('int', {}), {
                        'doc': 'A POSIX UID extracted from a ZIP Extra Field.'}),

                    ('extra:posix:gid', ('int', {}), {
                        'doc': 'A POSIX GID extracted from a ZIP Extra Field.'}),
                ),
                'doc': 'A file entry contained by a ZIP archive file.'}),

            ('file:attachment', ('guid', {}), {
                'template': {'title': 'file attachment'},
                'interfaces': (
                    ('file:entry', {}),
                    ('meta:usable', {}),
                    ('meta:observable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'path'}},
                        {'type': 'prop', 'opts': {'name': 'file'}},
                        {'type': 'prop', 'opts': {'name': 'text'}},
                    ),
                },
                'props': (

                    ('text', ('text', {}), {
                        'doc': 'Any text associated with the file such as alt-text for images.'}),
                ),
                'doc': 'A file attachment.'}),

            ('file:mime', ('str', {'lower': True}), {
                'ex': 'text/plain',
                'props': (),
                'doc': 'A file mime name string.'}),

            ('file:mime:pdf', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'doc': 'The "DocumentID" field extracted from PDF metadata.'}),

                    ('title', ('text', {}), {
                        'doc': 'The "Title" field extracted from PDF metadata.'}),

                    ('author:name', ('entity:name', {}), {
                        'doc': 'The "Author" field extracted from PDF metadata.'}),

                    ('language:name', ('lang:name', {}), {
                        'doc': 'The "Language" field extracted from PDF metadata.'}),

                    ('created', ('time', {}), {
                        'doc': 'The "CreatedDate" field extracted from PDF metadata.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The "ModifyDate" field extracted from PDF metadata.'}),

                    ('producer:name', ('it:softwarename', {}), {
                        'doc': 'The "Producer" field extracted from PDF metadata.'}),

                    ('tool:name', ('it:softwarename', {}), {
                        'doc': 'The "CreatorTool" field extracted from PDF metadata.'}),

                    ('subject', ('text', {}), {
                        'doc': 'The "Subject" field extracted from PDF metadata.'}),

                    ('keywords', ('meta:topic', {}), {
                        'array': {},
                        'doc': 'The "Keywords" field extracted from PDF metadata.'}),
                ),
                'doc': 'Metadata extracted from a Portable Document Format (PDF) file.'}),

            ('file:mime:msdoc', ('guid', {}), {
                'interfaces': (
                    ('file:mime:msoffice', {}),
                ),
                'props': (),
                'doc': 'Metadata about a Microsoft Word file.'}),

            ('file:mime:msxls', ('guid', {}), {
                'interfaces': (
                    ('file:mime:msoffice', {}),
                ),
                'props': (),
                'doc': 'Metadata about a Microsoft Excel file.'}),

            ('file:mime:msppt', ('guid', {}), {
                'interfaces': (
                    ('file:mime:msoffice', {}),
                ),
                'props': (),
                'doc': 'Metadata about a Microsoft Powerpoint file.'}),

            ('file:mime:pe', ('guid', {}), {
                'interfaces': (
                    ('file:mime:exe', {'template': {'executable': 'PE executable'}}),
                ),
                'props': (

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

                    ('exports:libname', ('file:path', {}), {
                        'doc': 'The export library name according to the PE.'}),

                    ('versioninfo', ('file:mime:pe:vsvers:keyval', {}), {
                        'array': {},
                        'doc': 'The VS_VERSIONINFO key/value data from the PE file.'}),
                ),
                'doc': 'Metadata about a Microsoft Portable Executable (PE) file.',
            }),

            ('file:mime:elf', ('guid', {}), {
                'interfaces': (
                    ('file:mime:exe', {'template': {'executable': 'ELF executable'}}),
                ),
                'props': (),
                'doc': 'Metadata about an ELF executable file.',
            }),

            ('file:mime:macho', ('guid', {}), {
                'interfaces': (
                    ('file:mime:exe', {'template': {'executable': 'Mach-O executable'}}),
                ),
                'props': (),
                'doc': 'Metadata about a Mach-O executable file.',
            }),

            ('file:mime:rtf', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (
                    ('guid', ('guid', {}), {
                        'doc': 'The parsed GUID embedded in the .rtf file.'}),
                ),
                'doc': 'The GUID of a set of mime metadata for a .rtf file.'}),

            ('file:mime:jpg', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'props': (),
                'doc': 'The GUID of a set of mime metadata for a .jpg file.'}),

            ('file:mime:tif', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'props': (),
                'doc': 'The GUID of a set of mime metadata for a .tif file.'}),

            ('file:mime:gif', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'props': (),
                'doc': 'The GUID of a set of mime metadata for a .gif file.'}),

            ('file:mime:png', ('guid', {}), {
                'interfaces': (
                    ('file:mime:image', {}),
                ),
                'props': (),
                'doc': 'The GUID of a set of mime metadata for a .png file.'}),

            ('file:mime:pe:section', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (

                    ('name', ('str', {}), {
                        'doc': 'The textual name of the section.'}),

                    ('sha256', ('crypto:hash:sha256', {}), {
                        'doc': 'The sha256 hash of the section. Relocations must be zeroed before hashing.'}),
                ),
                'doc': 'A PE section contained in a file.'}),

            ('file:mime:pe:resource', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (

                    ('type', ('pe:resource:type', {}), {
                        'doc': 'The typecode for the resource.'}),

                    ('langid', ('pe:langid', {}), {
                        'doc': 'The language code for the resource.'}),

                    ('sha256', ('crypto:hash:sha256', {}), {
                        'doc': 'The SHA256 hash of the resource bytes.'}),
                ),
                'doc': 'A PE resource contained in a file.'}),

            ('file:mime:pe:export', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (

                    ('name', ('it:dev:str', {}), {
                        'doc': 'The name of the export in the file.'}),

                    ('rva', ('int', {}), {
                        'doc': 'The Relative Virtual Address of the exported function entry point.'}),
                ),
                'doc': 'A named PE export contained in a file.'}),

            ('file:mime:pe:vsvers:keyval', ('comp', {'fields': (('name', 'str'), ('value', 'str'))}), {
                'props': (

                    ('name', ('str', {}), {
                        'computed': True,
                        'doc': 'The key for the VS_VERSIONINFO keyval pair.'}),

                    ('value', ('str', {}), {
                        'computed': True,
                        'doc': 'The value for the VS_VERSIONINFO keyval pair.'}),
                ),
                'doc': 'A key value pair found in a PE VS_VERSIONINFO structure.'}),

            ('file:macho:loadcmd:type', ('int', {'enums': s_l_macho.getLoadCmdTypes()}), {
                'doc': 'A Mach-O load command type.'}),

            ('file:macho:section:type', ('int', {'enums': s_l_macho.getSectionTypes()}), {
                'doc': 'A Mach-O section type.'}),

            ('pe:resource:type', ('int', {'enums': s_l_pe.getRsrcTypes()}), {
                'doc': 'The typecode for the resource.'}),

            ('pe:langid', ('int', {'min': 0, 'max': 0xffff, 'enums': s_l_pe.getLangCodes(), 'enums:strict': False}), {
                'doc': 'The PE language id.'}),

            ('file:mime:macho:loadcmd', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (
                    ('type', ('file:macho:loadcmd:type', {}), {
                        'doc': 'The type of the load command.'}),
                ),
                'doc': 'A generic load command pulled from the Mach-O headers.'}),

            ('file:mime:macho:version', ('file:mime:macho:loadcmd', {}), {
                'props': (
                    ('version', ('it:version', {}), {
                        'doc': 'The version of the Mach-O file encoded in an LC_VERSION load command.'}),
                ),
                'doc': 'A specific load command used to denote the version of the source used to build the Mach-O binary.'}),

            ('file:mime:macho:uuid', ('file:mime:macho:loadcmd', {}), {
                'props': (
                    ('uuid', ('guid', {}), {
                        'doc': 'The UUID of the Mach-O application (as defined in an LC_UUID load command).'}),
                ),
                'doc': 'A specific load command denoting a UUID used to uniquely identify the Mach-O binary.'}),

            ('file:mime:macho:segment', ('file:mime:macho:loadcmd', {}), {
                'props': (

                    ('name', ('str', {}), {
                        'doc': 'The name of the Mach-O segment.'}),

                    ('memsize', ('int', {}), {
                        'doc': 'The size of the segment in bytes, when resident in memory, according to the load command structure.'}),

                    ('disksize', ('int', {}), {
                        'doc': 'The size of the segment in bytes, when on disk, according to the load command structure.'}),

                    ('sha256', ('crypto:hash:sha256', {}), {
                        'doc': 'The sha256 hash of the bytes of the segment.'}),
                ),
                'doc': 'A named region of bytes inside a Mach-O binary.'}),

            ('file:mime:macho:section', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (

                    ('segment', ('file:mime:macho:segment', {}), {
                        'doc': 'The Mach-O segment that contains this section.'}),

                    ('name', ('str', {}), {
                        'doc': 'Name of the section.'}),

                    ('type', ('file:macho:section:type', {}), {
                        'doc': 'The type of the section.'}),

                    ('sha256', ('crypto:hash:sha256', {}), {
                        'doc': 'The sha256 hash of the bytes of the Mach-O section.'}),
                ),
                'doc': 'A section inside a Mach-O binary denoting a named region of bytes inside a segment.'}),

            ('file:mime:lnk', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {}),
                ),
                'props': (

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

                    ('relative', ('file:path', {}), {
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
                ),
                'doc': 'The GUID of the metadata pulled from a Windows shortcut or LNK file.'}),
        ),
        'edges': (

            (('file:bytes', 'refs', 'it:dev:str'), {
                'doc': 'The source file contains the target string.'}),

            (('file:bytes', 'uses', 'meta:technique'), {
                'doc': 'The source file uses the target technique.'}),

            # FIXME picturable?
            # (('file:mime:image', 'imageof', None), {
        ),
    },
)
