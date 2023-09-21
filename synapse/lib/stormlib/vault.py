import synapse.exc as s_exc

import synapse.lib.cell as s_cell
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
            $vault = $lib.vault.byname($cmdopts.name)
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
            $vault = $lib.vault.byiden($cmdopts.viden)
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
            $vault = $lib.vault.bytype($cmdopts.type, $cmdopts.scope)
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
            $vault = $lib.vault.get($cmdopts.name)

            $ok = $vault.set($cmdopts.key, $cmdopts.value)
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
            $vault = $lib.vault.get($cmdopts.name)
            $ok = $vault.del()
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
            $vault = $lib.vault.get($cmdopts.name)

            $ok = $vault.setPerm($cmdopts.iden, $cmdopts.level)
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
        {'name': 'get', 'desc': 'Get a vault by iden or name.',
         'type': {'type': 'function', '_funcname': '_getVault',
                  'args': (
                      {'name': 'vault', 'type': 'str', 'desc': 'The vault name or iden to retrieve.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The requested vault.'}}},
        {'name': 'byname', 'desc': 'Get a vault by name.',
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
        {'name': 'byiden', 'desc': 'Get a vault by iden.',
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
        {'name': 'bytype', 'desc': 'Get a vault for a specified vault type.',
         'type': {'type': 'function', '_funcname': '_getByType',
                  'args': (
                      {'name': 'vtype', 'type': 'str', 'desc': 'The vault type to retrieved.'},
                      {'name': 'scope', 'type': 'str', 'default': None,
                       'desc': 'The scope for the specified type. If $lib.null, then getByType will search.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Vault data or None if the vault could not be retrieved.'}}},
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
            'get': self._getVault,
            'byname': self._getByName,
            'byiden': self._getByIden,
            'bytype': self._getByType,
            'list': self._listVaults,
            'setDefault': self._setDefault,
        }

    def _reqEasyPerm(self, vault, perm):
        check = self.runt.snap.core._hasEasyPerm(vault, self.runt.user, perm)

        if not check and not self.runt.asroot:
            mesg = f'Insufficient permissions for user {self.runt.user.name} to vault {self.valu}.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user)

    async def _addVault(self, name, vtype, scope, iden, data):
        name = await s_stormtypes.tostr(name)
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        iden = await s_stormtypes.tostr(iden, noneok=True)
        data = await s_stormtypes.toprim(data)

        user = None
        if not self.runt.asroot:
            user = self.runt.user

        return await self.runt.snap.core.addVault(name, vtype, scope, iden, data, user=user)

    async def _getVault(self, name):
        vault = self.runt.snap.core.getVaultByIden(name)
        if not vault:
            vault = self.runt.snap.core.reqVaultByName(name)

        self._reqEasyPerm(vault, s_cell.PERM_READ)

        iden = vault.get('iden')
        return Vault(self.runt, iden)

    async def _getByName(self, name):
        name = await s_stormtypes.tostr(name)

        vault = self.runt.snap.core.reqVaultByName(name)
        self._reqEasyPerm(vault, s_cell.PERM_READ)

        iden = vault.get('iden')
        return Vault(self.runt, iden)

    async def _getByIden(self, viden):
        viden = await s_stormtypes.tostr(viden)

        vault = self.runt.snap.core.reqVaultByIden(viden)
        self._reqEasyPerm(vault, s_cell.PERM_READ)

        return Vault(self.runt, viden)

    async def _getByType(self, vtype, scope=None):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)

        vault = self.runt.snap.core.getVaultByType(vtype, self.runt.user.iden, scope)
        self._reqEasyPerm(vault, s_cell.PERM_READ)

        iden = vault.get('iden')
        return Vault(self.runt, iden)

    async def _listVaults(self):
        for vault in self.runt.snap.core.listVaults(user=self.runt.user):
            yield vault

    async def _setDefault(self, vtype, scope):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)

        user = None
        if not self.runt.asroot:
            user = self.runt.user

        return await self.runt.snap.core.setVaultDefault(vtype, scope, user=user)

@s_stormtypes.registry.registerType
class Vault(s_stormtypes.Prim):
    '''
    Implements the Storm API for a Vault.

    Callers (instantiation) of this class must have already checked that the user has at least
    PERM_READ to the vault.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The Vault iden.', 'type': 'str', },
        {'name': 'type', 'desc': 'The Vault type.', 'type': 'str', },
        {'name': 'scope', 'desc': 'The Vault scope.', 'type': 'str', },
        {'name': 'ident', 'desc': 'The Vault ident (user or role iden).', 'type': 'str', },
        {'name': 'permissions', 'desc': 'The Vault permissions.', 'type': 'dict', },
        {'name': 'data', 'desc': 'The Vault data.', 'type': 'dict', },

        {'name': 'name',
         'desc': 'The Vault name.',
         'type': {
             'type': ['gtor', 'stor'],
             '_storfunc': '_storName',
             '_gtorfunc': '_gtorName',
             'returns': {'type': 'str'}}},

        {'name': 'get', 'desc': 'Get an arbitrary property from the Vault data.',
         'type': {'type': 'function', '_funcname': '_methGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the property to return.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},

        {'name': 'set', 'desc': 'Get an arbitrary property from the Vault data.',
         'type': {'type': 'function', '_funcname': '_methGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the property to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value of the property to set. $lib.undef to remove an existing value.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': '$lib.true if the assignment was successful, $lib.false otherwise.', }}},

        {'name': 'pack', 'desc': 'Get the packed version of the Vault.',
         'type': {'type': 'function', '_funcname': '_methPack', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'The packed Vault definition.', }}},

        {'name': 'setPerm', 'desc': 'Set easy permissions on the Vault.',
         'type': {'type': 'function', '_funcname': '_methSetPerm',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The user or role to modify.'},
                      {'name': 'level', 'type': 'str', 'desc': 'The easyperm level for the iden. $lib.undef to remove an existing permission.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': '$lib.true if the permission was set, $lib.false otherwise.', }}},

        {'name': 'delete', 'desc': 'Delete the Vault.',
         'type': {'type': 'function', '_funcname': '_methDelete',
                  'args': (),
                  'returns': {'type': 'boolean', 'desc': '$lib.true if the vault was deleted, $lib.false otherwise.', }}},
    )
    _storm_typename = 'vault'
    _ismutable = False

    def __init__(self, runt, valu, path=None):

        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt

        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu

        self.stors.update({
            'name': self._storName,
        })

        self.gtors.update({
            'name': self._gtorName,
            'type': self._gtorType,
            'scope': self._gtorScope,
            'ident': self._gtorIdent,
            'data': self._gtorData,
            'permissions': self._gtorPermissions,
        })

    def getObjLocals(self):
        return {
            'get': self._methGet,
            'set': self._methSet,
            'pack': self._methPack,
            'setPerm': self._methSetPerm,
            'delete': self._methDelete,
        }

    def __hash__(self):
        return hash((self._storm_typename, self.valu))

    def _reqEasyPerm(self, vault, perm):
        check = self.runt.snap.core._hasEasyPerm(vault, self.runt.user, perm)

        if not check and not self.runt.asroot:
            mesg = f'Insufficient permissions for user {self.runt.user.name} to vault {self.valu}.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user)

    async def _storName(self, name):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        self._reqEasyPerm(vault, s_cell.PERM_EDIT)

        name = await s_stormtypes.tostr(name)
        iden = vault.get('iden')
        await self.runt.snap.core.renameVault(iden, name)
        return name

    async def _gtorName(self):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        return vault.get('name')

    async def _gtorType(self):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        return vault.get('type')

    async def _gtorScope(self):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        return vault.get('scope')

    async def _gtorIdent(self):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        return vault.get('ident')

    async def _gtorPermissions(self):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        return vault.get('permissions')

    async def _methGet(self, name):
        name = await s_stormtypes.tostr(name)
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        self._reqEasyPerm(vault, s_cell.PERM_EDIT)
        return vault.get(name)

    async def _methSet(self, name, valu):
        name = await s_stormtypes.tostr(name)
        valu = await s_stormtypes.toprim(valu)

        user = None
        if not self.runt.asroot:
            user = self.runt.user

        return self.runt.snap.core.setVaultData(self.valu, name, valu, user=user)

    async def _methPack(self):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)

        edit = self.runt.snap.core._hasEasyPerm(self.valu, self.runt.user, s_cell.PERM_EDIT)
        if edit or self.runt.asroot:
            return vault

        vault.pop('data')
        return vault

    async def _methSetPerm(self, iden, level):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        self._reqEasyPerm(vault, s_cell.PERM_ADMIN)

        iden = s_stormtypes.tostr(iden)
        level = s_stormtypes.toint(level)

        return self.runt.snap.core.setVaultPerm(self.valu, iden, level)

    async def _methDelete(self):
        vault = self.runt.snap.core.reqVaultByIden(self.valu)
        self._reqEasyPerm(vault, s_cell.PERM_ADMIN)

        return self.runt.snap.core.delVault(self.valu)

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.valu}'
