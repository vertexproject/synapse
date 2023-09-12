import synapse.common as s_common

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
        ''',
    },
    {
        'name': 'vault.byname',
        'descr': '''
            Get vault by vault name.

            Examples:

                // Get vault from visi's user vault
                vault.byname "synapse-test:visi"

                // Get vault from contributor's role vault
                vault.byname "synapse-test:contributor"

                // Get vault from unscoped vault
                vault.byname "my_synapse-test_vault"
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name.'}),
            ('--showdata', {'type': 'bool', 'action': 'store_true',
                'default': False, 'help': 'Print vault data if permissible.'}),
        ),
        'storm': '''
            $vault = $lib.vault.getByName($cmdopts.name)
            $lib.vault.print($vault, $cmdopts.showdata)
            $lib.print('')
        ''',
    },
    {
        'name': 'vault.byiden',
        'descr': '''
            Get vault by vault iden.

            Examples:

                // Get vault by iden
                vault.byiden $iden
        ''',
        'cmdargs': (
            ('viden', {'type': 'str', 'help': 'The vault iden.'}),
            ('--showdata', {'type': 'bool', 'action': 'store_true',
                'default': False, 'help': 'Print vault data.'}),
        ),
        'storm': '''
            $vault = $lib.vault.getByIden($cmdopts.viden)
            $lib.vault.print($vault, $cmdopts.showdata)
            $lib.print('')
        ''',
    },
    {
        'name': 'vault.bytype',
        'descr': '''
            Get a vault by type.

            Examples:

                // Get the default or first available vault for the
                // synapse-test type
                vault.bytype "synapse-test"

                // Get a role vault for the synapse-test type
                vault.bytype "synapse-test" --scope role

                // Get the global vault for the synapse-test type
                vault.bytype "synapse-test" --scope global
        ''',
        'cmdargs': (
            ('type', {'type': 'str', 'help': 'The vault type to retrieve.'}),
            ('--scope', {'type': 'str', 'default': None,
                'help': 'Restrict the vault to this scope.'}),
            ('--showdata', {'type': 'bool', 'action': 'store_true',
                'default': False, 'help': 'Print vault data.'}),
        ),
        'storm': '''
            $vault = $lib.vault.getByType($cmdopts.type, $cmdopts.scope)
            $lib.vault.print($vault, $cmdopts.showdata)
            $lib.print('')
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
            $vault = $lib.vault.getVaultByIdenOrName($cmdopts.name)
            if (not $vault) {
                $lib.warn(`Vault with name or iden not found: {$cmdopts.name}.`)
                return($lib.null)
            }

            $ok = $lib.vault.set($vault.iden, $cmdopts.key, $cmdopts.value)
            if $ok {
                $lib.print(`Successfully set {$cmdopts.key}={$cmdopts.value} into vault {$cmdopts.name}.`)
            } else {
                $lib.warn(`Error setting {$cmdopts.key}={$cmdopts.value} into vault {$cmdopts.name}.`)
            }
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
            ('name', {'type': 'str', 'help': 'The vault name or iden.'}),
        ),
        'storm': '''
            $vault = $lib.vault.getVaultByIdenOrName($cmdopts.name)
            if (not $vault) {
                $lib.warn(`Vault with name or iden not found: {$cmdopts.name}.`)
                return($lib.null)
            }

            $ok = $lib.vault.del($vault.iden)
            if $ok {
                $lib.print(`Successfully deleted vault {$cmdopts.name}.`)
            } else {
                $lib.warn(`Error deleting vault {$cmdopts.name}.`)
            }
        ''',
    },
    {
        'name': 'vault.list',
        'descr': '''
            List available vaults.
        ''',
        'cmdargs': (
            ('--showdata', {'type': 'bool', 'action': 'store_true',
                'default': False, 'help': 'Print vault data.'}),
        ),
        'storm': '''
            $lib.print("Available Vaults")
            $lib.print("----------------")

            for $vault in $lib.vault.list() {
                $lib.vault.print($vault, $cmdopts.showdata)
                $lib.print('')
            }
        ''',
    },
    {
        'name': 'vault.set.perm',
        'descr': '''
            Set permissions on a vault.

            Examples:

                // Give blackout read permissions to visi's user vault
                vault.set.perm synapse-test:visi $lib.auth.users.byname(blackout).iden $lib.auth.easyperm.read

                // Give the contributor role read permissions to visi's user vault
                vault.set.perm synapse-test:visi $lib.auth.roles.byname(contributor).iden $lib.auth.easyperm.read

                // Revoke blackout's permissions from visi's user vault
                vault.set.perm synapse-test:visi $lib.auth.users.byname(blackout).iden $lib.null

                // Give visi read permissions to the contributor role vault. (Assume
                // visi is not a member of the contributor role).
                vault.set.perm synapse-test:contributor $lib.auth.users.byname(visi).iden $lib.auth.easyperm.read
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name or iden to set permissions on.'}),
            ('iden', {'type': 'str', 'help': 'The user iden or role iden to add the vault.'}),
            ('level', {'type': 'str', 'help': 'The permission level to grant, $lib.null to revoke an existing permission.'}),
        ),
        'storm': '''
            $vault = $lib.vault.getVaultByIdenOrName($cmdopts.name)
            if (not $vault) {
                $lib.warn(`Vault with name or iden not found: {$cmdopts.name}.`)
                return($lib.null)
            }

            $ok = $lib.vault.setPerm($vault.iden, $cmdopts.iden, $cmdopts.level)
            if $ok {
                $lib.print(`Successfully set permissions on vault {$cmdopts.name}.`)
            } else {
                $lib.warn(`Error setting permissions on vault {$cmdopts.name}.`)
            }
        ''',
    },
    {
        'name': 'vault.set.default',
        'descr': '''
            Set default scope for a vault type.

            Examples:

                // Set the global vault as default for the synapse-test vault type
                vault.set.default synapse-test global

                // Set the user vault as default for the synapse-test vault type
                vault.set.default synapse-test user

                // Unset a default scope for the synapse-test vault type
                vault.set.default synapse-test $lib.null
        ''',
        'cmdargs': (
            ('type', {'type': 'str', 'help': 'The vault type to set the default for.'}),
            ('scope', {'type': 'str', 'help': 'The default scope. One of "user", "role", "global", or $lib.null to remove the value.'}),
        ),
        'storm': '''
            $ok = $lib.vault.setDefault($cmdopts.type, $cmdopts.scope)
            if $ok {
                $lib.print(`Successfully set default scope to {$cmdopts.scope} for vault type {$cmdopts.type}.`)
            } else {
                $lib.warn(`Error setting default scope to {$cmdopts.scope} for vault type {$cmdopts.type}.`)
            }
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
        {'name': 'getByName', 'desc': 'Get a vault by name.',
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
        {'name': 'getByIden', 'desc': 'Get a vault by iden.',
         'type': {'type': 'function', '_funcname': '_getByIden',
                  'args': (
                      {'name': 'viden', 'type': 'str',
                       'desc': '''
                            The iden of the vault to retrieve.  If user only has
                            PERM_READ, the data will not be returned.  If the
                            user has PERM_EDIT or higher, data will be included
                            in the vault.
                       '''},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The requested vault.'}}},
        {'name': 'getByType', 'desc': 'Get a vault for a specified vault type.',
         'type': {'type': 'function', '_funcname': '_getByType',
                  'args': (
                      {'name': 'vtype', 'type': 'str', 'desc': 'The vault type to retrieved.'},
                      {'name': 'scope', 'type': 'str', 'default': None,
                       'desc': 'The scope for the specified type. If $lib.null, then getByType will search.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Vault data or None if the vault could not be retrieved.'}}},
        {'name': 'set', 'desc': 'Set data into a vault. Requires PERM_EDIT or higher on the vault.',
         'type': {'type': 'function', '_funcname': '_setVault',
                  'args': (
                      {'name': 'viden', 'type': 'str', 'desc': 'The vault iden to operate on.'},
                      {'name': 'key', 'type': 'str', 'desc': 'The data key to set into the vault.'},
                      {'name': 'valu', 'type': 'str', 'desc': 'The data value to set into the vault.'},
                  ),
                  'returns': {'type': 'boolean',
                              'desc': '`$lib.true` if the data was successfully set, `$lib.false` otherwise.', }}},
        {'name': 'del', 'desc': 'Delete a vault.',
         'type': {'type': 'function', '_funcname': '_delVault',
                  'args': (
                      {'name': 'viden', 'type': 'str', 'desc': 'The vault iden to delete.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'list', 'desc': 'List vaults accessible to the current user.',
         'type': {'type': 'function', '_funcname': '_listVaults',
                  'args': (),
                  'returns': {'type': 'list', 'desc': 'Yields vaults.'}}},
        {'name': 'print', 'desc': 'Print the details of the specified vault.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'vault', 'type': 'dict', 'desc': 'The vault to print.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'getByIdenOrName', 'desc': 'Get a vault by iden or name.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'vault', 'type': 'dict', 'desc': 'The vault name or iden to retrieve.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The requested vault.'}}},
        {'name': 'setPerm', 'desc': 'Set permissions on a vault. Current user must have PERM_EDIT permissions or higher.',
         'type': {'type': 'function', '_funcname': '_setPerm',
                  'args': (
                      {'name': 'viden', 'type': 'str', 'desc': 'The vault iden to modify.'},
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
    _storm_query = '''
        function getVaultByIdenOrName(name) {
            $vault = $lib.null

            try {
                $vault = $lib.vault.getByIden($name)
            } catch BadArg as err {}

            if $vault {
                return($vault)
            }

            return($lib.vault.getByName($name))
        }

        function print(vault, showdata=$lib.false) {
            $lvlnames = ({})
            for ($name, $level) in $lib.auth.easyperm.level {
                $level = $lib.cast(str, $level)
                $lvlnames.$level = $name
            }

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

            if $showdata {
                if $vault.data {
                    $lib.print('  Data:')
                    for ($key, $valu) in $vault.data {
                        $lib.print(`    {$key}: {$valu}`)
                    }
                } else {
                    $lib.print('  Data: None (or only PERM_READ)')
                }
            }
        }
    '''

    def getObjLocals(self):
        return {
            'add': self._addVault,
            'getByName': self._getByName,
            'getByIden': self._getByIden,
            'getByType': self._getByType,
            'set': self._setVault,
            'del': self._delVault,
            'list': self._listVaults,
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

    async def _getByIden(self, viden):
        viden = await s_stormtypes.tostr(viden)
        return self.runt.snap.core.getVaultByIden(viden, user=self.runt.user)

    async def _getByType(self, vtype, scope=None):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        return self.runt.snap.core.getVaultByType(vtype, scope, user=self.runt.user)

    async def _setVault(self, viden, key, valu):
        viden = await s_stormtypes.tostr(viden)
        key = await s_stormtypes.tostr(key)

        if valu is s_stormtypes.undef:
            valu = s_common.novalu
        else:
            valu = await s_stormtypes.toprim(valu)

        return await self.runt.snap.core.setVaultData(viden, key, valu, user=self.runt.user)

    async def _delVault(self, viden):
        viden = await s_stormtypes.tostr(viden)
        return await self.runt.snap.core.delVault(viden, user=self.runt.user)

    async def _listVaults(self):
        for vault in self.runt.snap.core.listVaults(user=self.runt.user):
            yield vault

    async def _setPerm(self, viden, iden, level):
        viden = await s_stormtypes.tostr(viden)
        iden = await s_stormtypes.tostr(iden)
        level = await s_stormtypes.toint(level, noneok=True)
        return await self.runt.snap.core.setVaultPerm(viden, iden, level, user=self.runt.user)

    async def _setDefault(self, vtype, scope):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        return await self.runt.snap.core.setVaultDefault(vtype, scope, user=self.runt.user)
