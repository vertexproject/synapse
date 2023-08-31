import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibVault(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with vaults.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Create a new vault.',
         'type': {'type': 'function', '_funcname': '_addVault',
                  'args': (
                      {'name': 'vtype', 'type': 'str',
                       'desc': 'The type of this vault. Can be any free form string.'},
                      {'name': 'iden', 'type': 'str',
                       'desc': 'User/role iden for this vault if scope is "user" or "role". None for "global" scope vaults.'},
                      {'name': 'data', 'type': 'dict',
                       'desc': 'The initial data to store in this vault.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Iden of the newly created vault.'}}},
        {'name': 'get', 'desc': 'Get data from a vault by name or iden.',
         'type': {'type': 'function', '_funcname': '_getVault',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': '''
                            The name or iden of the vault to retrieve.  If user
                            only has PERM_READ, the data will not be returned.
                            If the user has PERM_EDIT or higher, data will be
                            included in the vault.
                       '''},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The requested vault.'}}},
        {'name': 'set', 'desc': 'Set data into a vault. Requires PERM_EDIT or higher on the vault.',
         'type': {'type': 'function', '_funcname': '_setVault',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name or iden of the vault to operate on.'},
                      {'name': 'data', 'type': 'dict', 'desc': 'The data to set into the vault.'},
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the data was successfully set, false otherwise.', }}},
        {'name': 'del', 'desc': 'Delete a vault.',
         'type': {'type': 'function', '_funcname': '_delVault',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name or iden of the vault to delete.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'list', 'desc': 'List vaults accessible to the current user.',
         'type': {'type': 'function', '_funcname': '_listVaults',
                  'args': (),
                  'returns': {'type': 'list', 'desc': 'Yields vaults.'}}},
        {'name': 'open', 'desc': 'Open a vault for a specified vault type.',
         'type': {'type': 'function', '_funcname': '_openVault',
                  'args': (
                      {'name': 'vtype', 'type': 'str', 'desc': 'The vault type to open.'},
                      {'name': 'scope', 'type': 'str', 'desc': 'The scope to open for the specified type. If $lib.null, then openVault will search.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Iden of the opened vault or None if no vault was opened.'}}},
        {'name': 'setPerm', 'desc': 'Set permissions on a vault. Current user must have PERM_EDIT permissions or higher.',
         'type': {'type': 'function', '_funcname': '_openVault',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name or iden of the vault to modify.'},
                      {'name': 'iden', 'type': 'str', 'desc': 'The user/role iden to add to the vault permissions.'},
                      {'name': 'level', 'type': 'int', 'desc': 'The easy perms level to add to the vault.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the permission was set on the vault, false otherwise.'}}},
        {'name': 'setDefault', 'desc': "Set default scope of a given vault type. Current user must have ('vaults', 'defaults') permission.",
         'type': {'type': 'function', '_funcname': '_openVault',
                  'args': (
                      {'name': 'vtype', 'type': 'str', 'desc': 'The vault type to modify.'},
                      {'name': 'valu', 'type': 'str', 'desc': 'The default scope for this vault type. Set to $lib.null for no default value.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the permission was set on the vault, false otherwise.'}}},
    )
    _storm_lib_path = ('vault',)

    def getObjLocals(self):
        return {
            'add': self._addVault,
            'get': self._getVaultData,
            'set': self._setVault,
            'del': self._delVault,
            'list': self._listVaults,
            'open': self._openVault,
            'setPerm': self._setPerm,
            'setDefault': self._setDefault,
        }

    async def _addVault(self, vtype, iden, data):
        vtype = await s_stormtypes.tostr(vtype)
        iden = await s_stormtypes.tostr(iden, noneok=True)
        data = await s_stormtypes.toprim(data)
        return await self.runt.snap.core.addVault(vtype, iden, data, user=self.runt.user)

    async def _getVaultData(self, name):
        name = await s_stormtypes.tostr(name)
        vault = self.runt.snap.core.getVault(name, user=self.runt.user)
        if vault:
            return vault.get('data')
        return None

    async def _setVault(self, name, data):
        name = await s_stormtypes.tostr(name)
        data = await s_stormtypes.toprim(data)
        return await self.runt.snap.core.setVaultData(name, data, user=self.runt.user)

    async def _delVault(self, name):
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.delVault(name, user=self.runt.user)

    async def _listVaults(self):
        for vault in self.runt.snap.core.listVaults(user=self.runt.user):
            yield vault

    async def _openVault(self, vtype, scope=None):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        return self.runt.snap.core.openVault(vtype, self.runt.user, scope=scope)

    async def _setPerm(self, name, iden, level):
        name = await s_stormtypes.tostr(name)
        iden = await s_stormtypes.tostr(iden)
        level = await s_stormtypes.toint(level, noneok=True)
        return await self.runt.snap.core.setVaultPerm(name, iden, level, user=self.runt.user)

    async def _setDefault(self, vtype, valu):
        vtype = await s_stormtypes.tostr(vtype)
        valu = await s_stormtypes.tostr(valu, noneok=True)
        return await self.runt.snap.core.setVaultDefault(vtype, valu, user=self.runt.user)
