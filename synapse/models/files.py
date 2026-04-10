
import synapse.exc as s_exc
import synapse.lib.types as s_types

class FileBase(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.exttype = self.modl.type('str')

    async def _normPyStr(self, valu, view=None):

        norm = valu.strip().lower().replace('\\', '/')
        if norm.find('/') != -1:
            mesg = 'file:base may not contain /'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        info = {}
        if norm.find('.') != -1:
            info['subs'] = {'ext': (self.exttype.typehash, norm.rsplit('.', 1)[1], {})}

        return norm, info

class FilePath(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

        self.exttype = self.modl.type('str')
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
        virts = {'base': (base, self.basetype.stortype)}

        if '.' in base:
            ext = base.rsplit('.', 1)[1]
            extsub = (self.exttype.typehash, ext, {})
            adds = (('file:base', base, {'subs': {'ext': extsub}}),)
            virts['ext'] = (ext, self.exttype.stortype)
        else:
            adds = (('file:base', base, {}),)

        if len(path) > 1:
            dirn, info = await self._normPyStr(lead + '/'.join(path[:-1]))
            adds += (('file:path', dirn, info),)
            virts['dir'] = (dirn, self.stortype)

        return fullpath, {'adds': adds, 'virts': virts}
