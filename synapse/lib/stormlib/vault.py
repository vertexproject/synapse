import synapse.lib.stormtypes as s_stormtypes

stormcmds = (
    {
        'name': 'vault.add',
        'descr': '''
            Add a vault.

            Examples:

                // Add a global vault with type `synapse-test`
                vault.add "synapse-test:global" synapse-test global $lib.null ({'apikey': 'foobar'})

                // Add a user vault with type `synapse-test`
                vault.add "synapse-test:visi" synapse-test user $lib.auth.users.byname(visi).iden ({'apikey': 'barbaz'})

                // Add a role vault with type `synapse-test`
                vault.add "synapse-test:contributor" synapse-test role $lib.auth.roles.byname(contributor).iden ({'apikey': 'bazquux'})

                // Add an unscoped vault with type `synapse-test`
                vault.add "my_synapse-test_vault" synapse-test $lib.null $lib.null ({'apikey': 'quuxquo'})
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name.'}),
            ('type', {'type': 'str', 'help': 'The vault type.'}),
            ('scope', {'type': 'str', 'help': 'The scope of the vault (user, role, global, or $lib.null for unscoped vaults).'}),
            ('iden', {'help': 'The user iden or role iden to add the vault for ($lib.null for global and unscoped vaults).'}),
            ('data', {'help': 'The data to store in the new vault.'}),
        ),
        'storm': '''
            $iden = $lib.vault.add($cmdopts.name, $cmdopts.type, $cmdopts.scope, $cmdopts.iden, $cmdopts.data)
            if $iden {
                $lib.print(`Vault created with iden: {$iden}.`)
            } else {
                $lib.warn('Error creating vault.')
            }
            return($iden)
        ''',
    },
    {
        'name': 'vault.get',
        'descr': '''
            Get vault by vault name.

            Examples:

                // Get vault from visi's user vault
                vault.get "synapse-test:visi"

                // Get vault from contributor's role vault
                vault.get "synapse-test:contributor"

                // Get vault from unscoped vault
                vault.get "my_synapse-test_vault"
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name.'}),
        ),
        'storm': '''
            return($lib.vault.getByName($cmdopts.name))
        ''',
    },
    {
        'name': 'vault.get.byiden',
        'descr': '''
            Get vault by vault iden.

            Examples:

                // Get vault by iden
                vault.get.byiden $iden
        ''',
        'cmdargs': (
            ('iden', {'type': 'str', 'help': 'The vault iden.'}),
        ),
        'storm': '''
            return($lib.vault.getByIden($cmdopts.iden))
        ''',
    },
    {
        'name': 'vault.set',
        'descr': '''
            Set vault data.

            Examples:

                // Set data to visi's user vault
                vault.set "synapse-test:visi" apikey foobar

                // Set data to contributor's role vault
                vault.set "synapse-test:contributor" apikey barbaz
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name or iden.'}),
            ('key', {'type': 'str', 'help': 'The key for the data to store in the vault.'}),
            ('value', {'help': 'The data value to store in the vault.'}),
        ),
        'storm': '''
            return($lib.vault.set($cmdopts.name, $cmdopts.key, $cmdopts.value))
        ''',
    },
    {
        'name': 'vault.del',
        'descr': '''
            Delete a vault.

            Examples:

                // Delete visi's user vault
                vault.del "synapse-test:visi"

                // Delete contributor's role vault
                vault.del "synapse-test:contributor"
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name.'}),
        ),
        'storm': '''
            return($lib.vault.del($cmdopts.name))
        ''',
    },
    {
        'name': 'vault.list',
        'descr': '''
            List available vaults.
        ''',
        'cmdargs': (),
        'storm': '''
            $lvlnames = ({})
            for ($name, $level) in $lib.auth.easyperm.level {
                $level = $lib.cast(str, $level)
                $lvlnames.$level = $name
            }

            $lib.print("Available Vaults")
            $lib.print("----------------")

            for $vault in $lib.vault.list() {
                $lib.print(`Vault: {$vault.name}`)
                $lib.print(`  Type: {$vault.type}`)
                $lib.print(`  Scope: {$vault.scope}`)
                $lib.print(`  Iden: {$vault.iden}`)
                $lib.print('  Permissions:')

                if $vault.permissions.users {
                    $lib.print('    Users:')
                    for ($iden, $level) in $vault.permissions.users {
                        $user = $lib.auth.users.get($iden)
                        $level = $lib.cast(str, $level)
                        $lib.print(`      {$user.name}: {$lvlnames.$level}`)
                    }
                } else {
                    $lib.print('    Users: None')
                }

                if $vault.permissions.roles {
                    $lib.print('    Roles:')
                    for ($iden, $level) in $vault.permissions.roles {
                        $user = $lib.auth.roles.get($iden)
                        $level = $lib.cast(str, $level)
                        $lib.print(`      {$user.name}: {$lvlnames.$level}`)
                    }
                } else {
                    $lib.print('    Roles: None')
                }

                $lib.print('')
            }
        ''',
    },
    {
        'name': 'vault.open',
        'descr': '''
            Open a vault by type.

            Examples:

                // Open the default or first available vault for the
                // synapse-test type
                vault.open "synapse-test"

                // Open a role vault for the synapse-test type
                vault.open "synapse-test" --scope role

                // Open the global vault for the synapse-test type
                vault.open "synapse-test" --scope global
        ''',
        'cmdargs': (
            ('type', {'type': 'str', 'help': 'The vault type to open.'}),
            ('--scope', {'type': 'str', 'default': None, 'help': 'Restrict the vault to this scope.'}),
        ),
        'storm': '''
            return($lib.vault.openByType($cmdopts.type, $cmdopts.scope))
        ''',
    },
    {
        'name': 'vault.open.byname',
        'descr': '''
            Open a vault by name.

            Examples:

                // Open visi's user vault by name
                vault.open.byname "synapse-test:visi"

                // Open the contributor role vault by name
                vault.open.byname "synapse-test:contributor"
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name to open.'}),
        ),
        'storm': '''
            $vault = $lib.vault.getByName($cmdopts.name)
            return($lib.vault.openByIden($vault.iden))
        ''',
    },
    {
        'name': 'vault.open.byiden',
        'descr': '''
            Open a vault by iden.

            Examples:

                // Open a vault by iden
                vault.open.byiden f2f147c66d91484fc0cfcc70cf248bca
        ''',
        'cmdargs': (
            ('iden', {'type': 'str', 'help': 'The vault iden to open.'}),
        ),
        'storm': '''
            return($lib.vault.openByIden($cmdopts.iden))
        ''',
    },
    {
        'name': 'vault.setperm',
        'descr': '''
            Set permissions on a vault.

            Examples:

                // Give blackout read permissions to visi's user vault
                vault.setperm synapse-test:visi $lib.auth.users.byname(blackout).iden $lib.auth.easyperm.read

                // Give the contributor role read permissions to visi's user vault
                vault.setperm synapse-test:visi $lib.auth.roles.byname(contributor).iden $lib.auth.easyperm.read

                // Revoke blackout's permissions from visi's user vault
                vault.setperm synapse-test:visi $lib.auth.users.byname(blackout).iden $lib.null

                // Give visi read permissions to the contributor role vault. (Assume
                // visi is not a member of the contributor role).
                vault.setperm synapse-test:contributor $lib.auth.users.byname(visi).iden $lib.auth.easyperm.read
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name or iden to set permissiosn on.'}),
            ('iden', {'type': 'str', 'help': 'The user iden or role iden to add the vault.'}),
            ('level', {'type': 'str', 'help': 'The permission level to grant, $lib.null to revoke an existing permission.'}),
        ),
        'storm': '''
            return($lib.vault.setPerm($cmdopts.name, $cmdopts.iden, $cmdopts.level))
        ''',
    },
    {
        'name': 'vault.setdefault',
        'descr': '''
            Set default scope for a vault type.

            Examples:

                // Set the global vault as default for the synapse-test vault type
                vault.setdefault synapse-test global

                // Set the user vault as default for the synapse-test vault type
                vault.setdefault synapse-test user

                // Unset a default scope for the synapse-test vault type
                vault.setdefault synapse-test $lib.null
        ''',
        'cmdargs': (
            ('type', {'type': 'str', 'help': 'The vault type to set the default for.'}),
            ('scope', {'type': 'str', 'help': 'The default scope. One of "user", "role", "global", or $lib.null to remove the value.'}),
        ),
        'storm': '''
            return($lib.vault.setDefault($cmdopts.type, $cmdopts.scope))
        ''',
    },
)

@s_stormtypes.registry.registerLib
class LibVault(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with vaults.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Create a new vault.',
         'type': {'type': 'function', '_funcname': '_addVault',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the new vault.'},
                      {'name': 'vtype', 'type': 'str',
                       'desc': 'The type of this vault.'},
                      {'name': 'scope', 'type': 'str',
                       'desc': 'Scope for this vault. One of "user", "role", "global", or $lib.null for unscoped vaults.'},
                      {'name': 'iden', 'type': 'str',
                       'desc': 'User/role iden for this vault if scope is "user" or "role". None for "global" scope vaults.'},
                      {'name': 'data', 'type': 'dict',
                       'desc': 'The initial data to store in this vault.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Iden of the newly created vault.'}}},
        {'name': 'getByName', 'desc': 'Get data from a vault by name.',
         'type': {'type': 'function', '_funcname': '_getByName',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': '''
                            The name of the vault to retrieve.  If user only has
                            PERM_READ, the data will not be returned.  If the
                            user has PERM_EDIT or higher, data will be included
                            in the vault.
                       '''},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The requested vault.'}}},
        {'name': 'getByIden', 'desc': 'Get data from a vault by iden.',
         'type': {'type': 'function', '_funcname': '_getByIden',
                  'args': (
                      {'name': 'iden', 'type': 'str',
                       'desc': '''
                            The iden of the vault to retrieve.  If user only has
                            PERM_READ, the data will not be returned.  If the
                            user has PERM_EDIT or higher, data will be included
                            in the vault.
                       '''},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The requested vault.'}}},
        {'name': 'set', 'desc': 'Set data into a vault. Requires PERM_EDIT or higher on the vault.',
         'type': {'type': 'function', '_funcname': '_setVault',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name or iden of the vault to operate on.'},
                      {'name': 'key', 'type': 'str', 'desc': 'The data key to set into the vault.'},
                      {'name': 'valu', 'type': 'str', 'desc': 'The data value to set into the vault.'},
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the data was successfully set, false otherwise.', }}},
        {'name': 'del', 'desc': 'Delete a vault.',
         'type': {'type': 'function', '_funcname': '_delVault',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the vault to delete.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'list', 'desc': 'List vaults accessible to the current user.',
         'type': {'type': 'function', '_funcname': '_listVaults',
                  'args': (),
                  'returns': {'type': 'list', 'desc': 'Yields vaults.'}}},
        {'name': 'openByIden', 'desc': 'Open a vault for a specified vault type.',
         'type': {'type': 'function', '_funcname': '_openByIden',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The vault iden to open.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Vault data or None if the vault could not be opened.'}}},
        {'name': 'openByType', 'desc': 'Open a vault for a specified vault type.',
         'type': {'type': 'function', '_funcname': '_openByType',
                  'args': (
                      {'name': 'vtype', 'type': 'str', 'desc': 'The vault type to open.'},
                      {'name': 'scope', 'type': 'str', 'default': None,
                       'desc': 'The scope to open for the specified type. If $lib.null, then openByType will search.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Vault data or None if the vault could not be opened.'}}},
        {'name': 'setPerm', 'desc': 'Set permissions on a vault. Current user must have PERM_EDIT permissions or higher.',
         'type': {'type': 'function', '_funcname': '_setPerm',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name or iden of the vault to modify.'},
                      {'name': 'iden', 'type': 'str', 'desc': 'The user/role iden to add to the vault permissions.'},
                      {'name': 'level', 'type': 'int', 'desc': 'The easy perms level to add to the vault.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the permission was set on the vault, false otherwise.'}}},
        {'name': 'setDefault', 'desc': "Set default scope of a given vault type. Current user must have ('vaults', 'defaults') permission.",
         'type': {'type': 'function', '_funcname': '_setDefault',
                  'args': (
                      {'name': 'vtype', 'type': 'str', 'desc': 'The vault type to modify.'},
                      {'name': 'scope', 'type': 'str', 'desc': 'The default scope for this vault type. Set to $lib.null for no default value.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the permission was set on the vault, false otherwise.'}}},
    )
    _storm_lib_path = ('vault',)

    def getObjLocals(self):
        return {
            'add': self._addVault,
            'getByName': self._getByName,
            'getByIden': self._getByIden,
            'set': self._setVault,
            'del': self._delVault,
            'list': self._listVaults,
            'openByIden': self._openByIden,
            'openByType': self._openByType,
            'setPerm': self._setPerm,
            'setDefault': self._setDefault,
        }

    async def _addVault(self, name, vtype, scope, iden, data):
        name = await s_stormtypes.tostr(name)
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        iden = await s_stormtypes.tostr(iden, noneok=True)
        data = await s_stormtypes.toprim(data)
        return await self.runt.snap.core.addVault(name, vtype, scope, iden, data, user=self.runt.user)

    async def _getByName(self, name):
        name = await s_stormtypes.tostr(name)
        return self.runt.snap.core.getVaultByName(name, user=self.runt.user)

    async def _getByIden(self, iden):
        iden = await s_stormtypes.tostr(iden)
        return self.runt.snap.core.getVaultByIden(iden, user=self.runt.user)

    async def _setVault(self, name, key, valu):
        name = await s_stormtypes.tostr(name)
        key = await s_stormtypes.tostr(key)
        valu = await s_stormtypes.toprim(valu)
        return await self.runt.snap.core.setVaultData(name, key, valu, user=self.runt.user)

    async def _delVault(self, name):
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.delVault(name, user=self.runt.user)

    async def _listVaults(self):
        for vault in self.runt.snap.core.listVaults(user=self.runt.user):
            yield vault

    async def _openByIden(self, iden):
        iden = await s_stormtypes.tostr(iden)
        return self.runt.snap.core.openVaultByIden(iden, self.runt.user)

    async def _openByType(self, vtype, scope=None):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        return self.runt.snap.core.openVaultByType(vtype, scope, self.runt.user)

    async def _setPerm(self, name, iden, level):
        name = await s_stormtypes.tostr(name)
        iden = await s_stormtypes.tostr(iden)
        level = await s_stormtypes.toint(level, noneok=True)
        return await self.runt.snap.core.setVaultPerm(name, iden, level, user=self.runt.user)

    async def _setDefault(self, vtype, scope):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        return await self.runt.snap.core.setVaultDefault(vtype, scope, user=self.runt.user)
