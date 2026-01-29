import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibEasyPerm(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with easy perm dictionaries.
    '''
    _storm_locals = (
        {'name': 'init', 'desc': '''
            Add the easy perm structure to a new or existing dictionary.

            Note:
                The current user will be given admin permission in the new
                easy perm structure.
        ''',
         'type': {'type': 'function', '_funcname': '_initEasyPerm',
                  'args': (
                      {'name': 'edef', 'type': 'dict', 'default': None,
                       'desc': 'A dictionary to add easy perms to.'},
                      {'name': 'default', 'type': 'int', 'default': s_cell.PERM_READ,
                       'desc': 'Specify the default permission level for this item.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'Dictionary with the easy perm structure.'}}},
        {'name': 'set', 'desc': 'Set the permission level for a user or role in an easy perm dictionary.',
         'type': {'type': 'function', '_funcname': '_setEasyPerm',
                  'args': (
                      {'name': 'edef', 'type': 'dict', 'desc': 'The easy perm dictionary to modify.'},
                      {'name': 'scope', 'type': 'str', 'desc': 'The scope, either "users" or "roles".'},
                      {'name': 'iden', 'type': 'str', 'desc': 'The user/role iden depending on scope.'},
                      {'name': 'level', 'type': 'int', 'desc': 'The permission level number, or None to remove the permission.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'Dictionary with the updated easy perm structure.'}}},
        {'name': 'allowed', 'desc': 'Check if the current user has a permission level in an easy perm dictionary.',
         'type': {'type': 'function', '_funcname': '_allowedEasyPerm',
                  'args': (
                      {'name': 'edef', 'type': 'dict', 'desc': 'The easy perm dictionary to check.'},
                      {'name': 'level', 'type': 'int', 'desc': 'The required permission level number.'},
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the user meets the requirement, false otherwise.', }}},
        {'name': 'confirm', 'desc': 'Require that the current user has a permission level in an easy perm dictionary.',
         'type': {'type': 'function', '_funcname': '_confirmEasyPerm',
                  'args': (
                      {'name': 'edef', 'type': 'dict', 'desc': 'The easy perm dictionary to check.'},
                      {'name': 'level', 'type': 'int', 'desc': 'The required permission level number.'},
                      {'name': 'mesg', 'type': 'str', 'default': None,
                       'desc': 'Optional error message to present if user does not have required permission level.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'level.admin', 'desc': 'Constant for admin permission.',
         'type': 'int', },
        {'name': 'level.deny', 'desc': 'Constant for deny permission.',
         'type': 'int', },
        {'name': 'level.edit', 'desc': 'Constant for edit permission.',
         'type': 'int', },
        {'name': 'level.read', 'desc': 'Constant for read permission.',
         'type': 'int', },
    )
    _storm_lib_path = ('auth', 'easyperm')

    def getObjLocals(self):
        return {
            'set': self._setEasyPerm,
            'init': self._initEasyPerm,
            'allowed': self._allowedEasyPerm,
            'confirm': self._confirmEasyPerm,
            'level': {
                'deny': s_cell.PERM_DENY,
                'read': s_cell.PERM_READ,
                'edit': s_cell.PERM_EDIT,
                'admin': s_cell.PERM_ADMIN,
            }
        }

    async def _setEasyPerm(self, edef, scope, iden, level):
        edef = await s_stormtypes.toprim(edef)
        scope = await s_stormtypes.tostr(scope)
        iden = await s_stormtypes.tostr(iden)
        level = await s_stormtypes.toint(level, noneok=True)

        if not isinstance(edef, dict):
            raise s_exc.BadArg(mesg='Object to set easy perms on must be a dictionary.')

        await self.runt.snap.core._setEasyPerm(edef, scope, iden, level)
        return edef

    async def _initEasyPerm(self, edef=None, default=s_cell.PERM_READ):
        edef = await s_stormtypes.toprim(edef)
        if edef is None:
            edef = {}

        default = await s_stormtypes.toint(default)

        if not isinstance(edef, dict):
            raise s_exc.BadArg(mesg='Object to add easy perms to must be a dictionary.')

        self.runt.snap.core._initEasyPerm(edef, default=default)

        await self.runt.snap.core._setEasyPerm(edef, 'users', self.runt.user.iden, s_cell.PERM_ADMIN)
        return edef

    async def _allowedEasyPerm(self, edef, level):
        edef = await s_stormtypes.toprim(edef)
        level = await s_stormtypes.toint(level)

        if not isinstance(edef, dict):
            raise s_exc.BadArg(mesg='Object to check easy perms on must be a dictionary.')

        return self.runt.snap.core._hasEasyPerm(edef, self.runt.user, level)

    async def _confirmEasyPerm(self, edef, level, mesg=None):
        edef = await s_stormtypes.toprim(edef)
        level = await s_stormtypes.toint(level)
        mesg = await s_stormtypes.tostr(mesg, noneok=True)

        if not isinstance(edef, dict):
            raise s_exc.BadArg(mesg='Object to check easy perms on must be a dictionary.')

        self.runt.snap.core._reqEasyPerm(edef, self.runt.user, level, mesg=mesg)
