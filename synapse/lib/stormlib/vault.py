import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.stormtypes as s_stormtypes

stormcmds = (
    {
        'name': 'vault.add',
        'descr': '''
            Add a vault.

            Examples:

                // Add a global vault with type `synapse-test`
                vault.add "shared-global-vault" synapse-test ({'apikey': 'foobar'}) --scope global

                // Add a user vault with type `synapse-test`
                vault.add "visi-user-vault" synapse-test ({'apikey': 'barbaz'}) --scope user --user visi

                // Add a role vault with type `synapse-test`
                vault.add "contributor-role-vault" synapse-test ({'apikey': 'bazquux'}) --scope role --user contributor

                // Add an unscoped vault with type `synapse-test`
                vault.add "unscoped-vault" synapse-test ({'apikey': 'quuxquo'})
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name.'}),
            ('type', {'type': 'str', 'help': 'The vault type.'}),
            ('data', {'help': 'The data to store in the new vault.'}),
            ('--user', {'type': 'str',
                        'help': 'This vault is a user-scoped vault, for the specified user name.'}),
            ('--role', {'type': 'str',
                        'help': 'This vault is a role-scoped vault, for the specified role name.'}),
            ('--unscoped', {'type': 'str',
                            'help': 'This vault is an unscoped vault, for the specified user name.'}),
            ('--global', {'type': 'bool', 'action': 'store_true', 'default': False,
                          'help': 'This vault is a global-scoped vault.'}),
        ),
        'storm': '''
            $owner = $lib.null
            $scope = $lib.null

            $exclusive_args = (0)
            if $cmdopts.user { $exclusive_args = ($exclusive_args + 1) }
            if $cmdopts.role { $exclusive_args = ($exclusive_args + 1) }
            if $cmdopts.unscoped { $exclusive_args = ($exclusive_args + 1) }
            if $cmdopts.global { $exclusive_args = ($exclusive_args + 1) }

            if ($exclusive_args != 1) {
                $lib.exit('Must specify one of --user <username>, --role <rolename>, --unscoped <username>, --global.')
            }

            if $cmdopts.user {
                $scope = user
                $owner = $lib.auth.users.byname($cmdopts.user).iden
            }

            if $cmdopts.role {
                $scope = role
                $owner = $lib.auth.roles.byname($cmdopts.role).iden
            }

            if $cmdopts.unscoped {
                $owner = $lib.auth.users.byname($cmdopts.user).iden
            }

            if $cmdopts.global {
                $scope = global
            }

            $iden = $lib.vault.add($cmdopts.name, $cmdopts.type, $scope, $owner, $cmdopts.data)
            $lib.print(`Vault created with iden: {$iden}.`)
            $vault = $lib.vault.get($iden)
            $lib.vault.print($vault)
        ''',
    },
    {
        'name': 'vault.set',
        'descr': '''
            Set vault data.

            Examples:

                // Set data to visi's user vault
                vault.set "visi-user-vault" apikey --value foobar

                // Set data to contributor's role vault
                vault.set "contributor-role-vault" apikey --value barbaz

                // Remove apikey from a global vault
                vault.set "some-global-vault" apikey --delete
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name or iden.'}),
            ('key', {'type': 'str', 'help': 'The key in the vault data to operate on.'}),
            ('--value', {'help': 'The data value to store in the vault.'}),
            ('--delete', {'type': 'bool', 'action': 'store_true', 'default': False,
                          'help': 'Specify this flag to remove the key/value from the vault data.'}),
        ),
        'storm': '''
            if ((not $cmdopts.value and not $cmdopts.delete) or ($cmdopts.value and $cmdopts.delete)) {
                $lib.exit('One of `--value <value>` or `--delete` is required.')
            }

            // Try iden first then name
            try {
                $vault = $lib.vault.get($cmdopts.name)
            } catch (BadArg, NoSuchIden) as exc {
                $vault = $lib.vault.byname($cmdopts.name)
            }

            if $cmdopts.value {
                $vault.data.($cmdopts.key) = $cmdopts.value
                $lib.print(`Set {$cmdopts.key}={$cmdopts.value} into vault {$cmdopts.name}.`)
            } else {
                $vault.data.($cmdopts.key) = $lib.undef
                $lib.print(`Removed {$cmdopts.key} from vault {$cmdopts.name}.`)
            }
        ''',
    },
    {
        'name': 'vault.del',
        'descr': '''
            Delete a vault.

            Examples:

                // Delete visi's user vault
                vault.del "visi-user-vault"

                // Delete contributor's role vault
                vault.del "contributor-role-vault"
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name or iden.'}),
        ),
        'storm': '''
            // Try iden first then name
            try {
                $vault = $lib.vault.get($cmdopts.name)
            } catch (BadArg, NoSuchIden) as exc {
                $vault = $lib.vault.byname($cmdopts.name)
            }

            $vault.delete()
            $lib.print(`Successfully deleted vault {$cmdopts.name}.`)
        ''',
    },
    {
        'name': 'vault.list',
        'descr': '''
            List available vaults.
        ''',
        'cmdargs': (
            ('--name', {'type': 'str', 'help': 'Only list vaults with the specified name or iden.'}),
            ('--type', {'type': 'str', 'help': 'Only list vaults with the specified type.'}),
            ('--showdata', {'type': 'bool', 'action': 'store_true', 'default': False, 'help': 'Print vault data.'}),
        ),
        'storm': '''
            $lib.print("Available Vaults")
            $lib.print("----------------")

            for $vault in $lib.vault.list() {
                if $cmdopts.name {
                    if ($vault.name != $cmdopts.name and $vault.iden != $cmdopts.name) {
                        continue
                    }
                }

                if $cmdopts.type {
                    if ($vault.type != $cmdopts.type) {
                        continue
                    }
                }

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
                vault.set.perm "my-user-vault" blackout --level read

                // Give the contributor role read permissions to visi's user vault
                vault.set.perm "my-user-vault" --role contributor --level read

                // Revoke blackout's permissions from visi's user vault
                vault.set.perm "my-user-vault" blackout --revoke

                // Give visi read permissions to the contributor role vault. (Assume
                // visi is not a member of the contributor role).
                vault.set.perm "contributor-role-vault" visi read
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The vault name or iden to set permissions on.'}),
            ('--user', {'type': 'str',
                        'help': 'The user name or role name to update in the vault.'}),
            ('--role', {'type': 'str',
                        'help': 'Specified when `user` is a role name.'}),
            ('--level', {'type': 'str', 'help': 'The permission level to grant.'}),
            ('--revoke', {'type': 'bool', 'action': 'store_true', 'default': False,
                          'help': 'Specify this flag when revoking an existing permission.'}),
        ),
        'storm': '''
            if ((not $cmdopts.level and not $cmdopts.revoke) or ($cmdopts.level and $cmdopts.revoke)) {
                $lib.exit('One of `--level <level>` or `--revoke` is required.')
            }

            if ((not $cmdopts.user and not $cmdopts.role) or ($cmdopts.user and $cmdopts.role)) {
                $lib.exit('One of `--user <username>` or `--role <rolename>` is required.')
            }

            $level = $lib.null
            if $cmdopts.level {
                $level = $lib.auth.easyperm.level.($cmdopts.level)
                if (not $level) {
                    $levels = ([])
                    for ($key, $val) in $lib.auth.easyperm.level {
                        $levels.append($key)
                    }

                    $levels = $lib.str.join(", ", $levels)

                    $lib.exit(`Invalid level specified: {$cmdopts.level}. Level must be one of: {$levels}.`)
                }
            }

            if $cmdopts.role {
                $iden = $lib.auth.roles.byname($cmdopts.user).iden
                $type = "Role"
            } else {
                $iden = $lib.auth.users.byname($cmdopts.user).iden
                $type = "User"
            }

            if (not $iden) {
                $lib.exit(`{$type} with value {$cmdopts.user} not found.`)
            }

            // Try iden first then name
            try {
                $vault = $lib.vault.get($cmdopts.name)
            } catch (BadArg, NoSuchIden) as exc {
                $vault = $lib.vault.byname($cmdopts.name)
            }

            $ok = $vault.setPerm($iden, $level)
            if $ok {
                $lib.print(`Successfully set permissions on vault {$cmdopts.name}.`)
            } else {
                $lib.warn(`Error setting permissions on vault {$cmdopts.name}.`)
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
                      {'name': 'owner', 'type': 'str',
                       'desc': 'User/role iden for this vault if scope is "user" or "role". None for "global" scope vaults.'},
                      {'name': 'data', 'type': 'dict',
                       'desc': 'The initial data to store in this vault.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'Iden of the newly created vault.'}}},
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
        {'name': 'get', 'desc': 'Get a vault by iden.',
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
    )
    _storm_lib_path = ('vault',)
    _storm_query = '''
        function print(vault, showdata=$lib.false) {
            $lvlnames = ({})
            for ($name, $level) in $lib.auth.easyperm.level {
                $level = $lib.cast(str, $level)
                $lvlnames.$level = $name
            }

            $lib.print(`Vault: {$vault.iden}`)
            $lib.print(`  Name: {$vault.name}`)
            $lib.print(`  Type: {$vault.type}`)
            $lib.print(`  Scope: {$vault.scope}`)
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
                if ($vault.data = $lib.null) {
                    $lib.print('  Data: Cannot display data - no read permission to vault.')
                } elif ($lib.len($vault.data) != (0)) {
                    $lib.print('  Data:')
                    for ($key, $valu) in $vault.data {
                        $lib.print(`    {$key}: {$valu}`)
                    }
                } else {
                    $lib.print('  Data: None')
                }
            }
        }
    '''

    def getObjLocals(self):
        return {
            'add': self._addVault,
            'get': self._getByIden,
            'byname': self._getByName,
            'bytype': self._getByType,
            'list': self._listVaults,
        }

    def _reqEasyPerm(self, vault, perm):
        check = self.runt.snap.core._hasEasyPerm(vault, self.runt.user, perm)

        if not check and not self.runt.asroot:
            iden = vault.get('iden')
            mesg = f'Insufficient permissions for user {self.runt.user.name} to vault {iden}.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user)

    async def _addVault(self, name, vtype, scope, owner, data):
        name = await s_stormtypes.tostr(name)
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)
        owner = await s_stormtypes.tostr(owner, noneok=True)
        data = await s_stormtypes.toprim(data)

        if not self.runt.asroot:
            user = self.runt.user

            if scope in ('global', 'role') and not user.isAdmin():
                mesg = f'User {user.name} cannot create {scope} vaults.'
                raise s_exc.AuthDeny(mesg=mesg, user=user)

            if scope == 'user' and user.iden != owner and not user.isAdmin():
                mesg = f'User {user.name} cannot create vaults for user {owner.name}.'
                raise s_exc.AuthDeny(mesg=mesg)

        vault = {
            'name': name,
            'type': vtype,
            'scope': scope,
            'owner': owner,
            'data': data,
        }

        return await self.runt.snap.core.addVault(vault)

    async def _getByName(self, name):
        name = await s_stormtypes.tostr(name)

        vault = self.runt.snap.core.reqVaultByName(name)
        self._reqEasyPerm(vault, s_cell.PERM_READ)

        return Vault(self.runt, vault.get('iden'))

    async def _getByIden(self, iden):
        iden = await s_stormtypes.tostr(iden)

        vault = self.runt.snap.core.reqVault(iden)
        self._reqEasyPerm(vault, s_cell.PERM_READ)

        return Vault(self.runt, iden)

    async def _getByType(self, vtype, scope=None):
        vtype = await s_stormtypes.tostr(vtype)
        scope = await s_stormtypes.tostr(scope, noneok=True)

        vault = self.runt.snap.core.reqVaultByType(vtype, self.runt.user.iden, scope)
        self._reqEasyPerm(vault, s_cell.PERM_READ)

        return Vault(self.runt, vault.get('iden'))

    async def _listVaults(self):
        for vault in self.runt.snap.core.listVaults():
            if not self.runt.snap.core._hasEasyPerm(vault, self.runt.user, s_cell.PERM_READ):
                continue

            yield Vault(self.runt, vault.get('iden'))

@s_stormtypes.registry.registerType
class VaultData(s_stormtypes.Prim):
    '''
    Implements the Storm API for Vault data.

    Callers (instantiation) of this class must have already checked that the user has at least
    PERM_EDIT to the vault.
    '''
    _storm_typename = 'vault:data'
    _ismutable = False

    def __init__(self, runt, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt

    @s_stormtypes.stormfunc(readonly=False)
    async def setitem(self, name, valu):
        vault = self.runt.snap.core.reqVault(self.valu)

        name = await s_stormtypes.tostr(name)

        if valu is s_stormtypes.undef:
            valu = s_common.novalu
        else:
            valu = await s_stormtypes.toprim(valu)

        return await self.runt.snap.core.setVaultData(self.valu, name, valu)

    async def deref(self, name):
        vault = self.runt.snap.core.reqVault(self.valu)

        name = await s_stormtypes.tostr(name)

        data = vault.get('data')
        valu = data.get(name, s_common.novalu)

        if valu is not s_common.novalu:
            return valu

        raise s_exc.NoSuchName(mesg=f'Cannot find name [{name}]', name=name, styp=self.__class__.__name__)

    async def iter(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        data = vault.get('data')

        for item in data.items():
            yield item

    def __len__(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        data = vault.get('data')
        return len(data)

    def stormrepr(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        data = vault.get('data')
        return repr(data)

    def value(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        return vault.get('data')

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
        {'name': 'data', 'desc': 'The Vault data.', 'type': 'vault:data'},
        {'name': 'permissions', 'desc': 'The Vault permissions.', 'type': 'dict', },

        {'name': 'name',
         'desc': 'The Vault name.',
         'type': {
             'type': ['gtor', 'stor'],
             '_storfunc': '_storName',
             '_gtorfunc': '_gtorName',
             'returns': {'type': 'str'}}},

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

        vault = self.runt.snap.core.reqVault(self.valu)

        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu
        self.locls['type'] = vault.get('type')
        self.locls['scope'] = vault.get('scope')

        self.stors.update({
            'name': self._storName,
        })

        self.gtors.update({
            'name': self._gtorName,
            'data': self._gtorData,
            'permissions': self._gtorPermissions,
        })

    def getObjLocals(self):
        return {
            'setPerm': self._methSetPerm,
            'delete': self._methDelete,
        }

    def __hash__(self):  # pragma: no cover
        return hash((self._storm_typename, self.valu))

    def _reqEasyPerm(self, vault, perm):
        check = self.runt.snap.core._hasEasyPerm(vault, self.runt.user, perm)

        if not check and not self.runt.asroot:
            mesg = f'Insufficient permissions for user {self.runt.user.name} to vault {self.valu}.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user)

    async def _storName(self, name):
        vault = self.runt.snap.core.reqVault(self.valu)
        self._reqEasyPerm(vault, s_cell.PERM_EDIT)

        name = await s_stormtypes.tostr(name)

        await self.runt.snap.core.renameVault(self.valu, name)

    async def _gtorName(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        return vault.get('name')

    async def _gtorData(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        if not self.runt.asroot and not self.runt.user.isAdmin():
            edit = self.runt.snap.core._hasEasyPerm(vault, self.runt.user, s_cell.PERM_EDIT)
            if not edit:
                return None

        return VaultData(self.runt, self.valu)

    async def _gtorPermissions(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        return vault.get('permissions')

    async def _methSetPerm(self, iden, level):
        vault = self.runt.snap.core.reqVault(self.valu)
        self._reqEasyPerm(vault, s_cell.PERM_ADMIN)

        iden = await s_stormtypes.tostr(iden)
        level = await s_stormtypes.toint(level)

        return await self.runt.snap.core.setVaultPerm(self.valu, iden, level)

    async def _methDelete(self):
        vault = self.runt.snap.core.reqVault(self.valu)
        self._reqEasyPerm(vault, s_cell.PERM_ADMIN)

        return await self.runt.snap.core.delVault(self.valu)

    async def stormrepr(self):
        return f'vault: {self.valu}'

    def value(self):
        vault = self.runt.snap.core.reqVault(self.valu)

        if not self.runt.asroot and not self.runt.user.isAdmin():
            edit = self.runt.snap.core._hasEasyPerm(vault, self.runt.user, s_cell.PERM_EDIT)
            if not edit:
                vault.pop('data')

        return vault
