import copy
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

stormcmds = (
    {
        'name': 'auth.user.add',
        'descr': '''
            Add a user.

            Examples:

                // Add a user named "visi" with the email address "visi@vertex.link"
                auth.user.add visi --email visi@vertex.link
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the user.'}),
            ('--email', {'type': 'str', 'help': "The user's email address.", 'default': None}),
        ),
        'storm': '''
            $user = $lib.auth.users.add($cmdopts.name, email=$cmdopts.email)
            $lib.print('User ({name}) added with iden: {iden}', name=$user.name, iden=$user.iden)
        ''',
    },
    {
        'name': 'auth.user.list',
        'descr': '''
            List all users.

            Examples:

                // Display the list of all users
                auth.user.list
        ''',
        'storm': '''
            $users = ([])
            $locked = ([])
            for $user in $lib.auth.users.list() {
                if $user.locked { $locked.append($user.name) }
                else { $users.append($user.name) }
            }

            $lib.print("Users:")
            for $user in $lib.sorted($users) {
                $lib.print(`  {$user}`)
            }

            $lib.print("")
            $lib.print("Locked Users:")
            for $user in $lib.sorted($locked) {
                $lib.print(`  {$user}`)
            }
        ''',
    },
    {
        'name': 'auth.user.mod',
        'descr': '''
            Modify properties of a user.

            Examples:

                // Rename the user "foo" to "bar"
                auth.user.mod foo --name bar

                // Make the user "visi" an admin
                auth.user.mod visi --admin $lib.true

                // Unlock the user "visi" and set their email to "visi@vertex.link"
                auth.user.mod visi --locked $lib.false --email visi@vertex.link

                // Grant admin access to user visi for the current view
                auth.user.mod visi --admin $lib.true --gate $lib.view.get().iden

                // Revoke admin access to user visi for the current view
                auth.user.mod visi --admin $lib.false --gate $lib.view.get().iden
        ''',
        'cmdargs': (
            ('username', {'type': 'str', 'help': 'The name of the user.'}),
            ('--name', {'type': 'str', 'help': 'The new name for the user.'}),
            ('--email', {'type': 'str', 'help': 'The email address to set for the user.'}),
            ('--passwd', {'type': 'str', 'help': 'The new password for the user. This is best passed into the runtime as a variable.'}),
            ('--admin', {'type': 'bool', 'help': 'True to make the user and admin, false to remove their remove their admin status.'}),
            ('--gate', {'type': 'str', 'help': 'The auth gate iden to grant or revoke admin status on. Use in conjunction with `--admin <bool>`.'}),
            ('--locked', {'type': 'bool', 'help': 'True to lock the user, false to unlock them.'}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.username)
            if $user {
                if $cmdopts.name {
                    $user.name = $cmdopts.name
                    $lib.print(`User ({$cmdopts.username}) renamed to {$cmdopts.name}.`)
                }
                if $cmdopts.email {
                    $user.email = $cmdopts.email
                    $lib.print(`User ({$cmdopts.username}) email address set to {$cmdopts.email}.`)
                }
                if $cmdopts.passwd {
                    $user.setPasswd($cmdopts.passwd)
                    $lib.print(`User ({$cmdopts.username}) password updated.`)
                }
                if ($cmdopts.locked != $lib.null) {
                    $user.setLocked($cmdopts.locked)
                    $lib.print(`User ({$cmdopts.username}) locked status set to {$cmdopts.locked=1}.`)
                }
                if ($cmdopts.admin != $lib.null) {
                    $user.setAdmin($cmdopts.admin, gateiden=$cmdopts.gate)
                    if $cmdopts.gate {
                        $lib.print(`User ({$cmdopts.username}) admin status set to {$cmdopts.admin=1} for auth gate {$cmdopts.gate}.`)
                    } else {
                        $lib.print(`User ({$cmdopts.username}) admin status set to {$cmdopts.admin=1}.`)
                    }
                }
                if ($cmdopts.gate != $lib.null and $cmdopts.admin = $lib.null) {
                    $lib.exit('Granting/revoking admin status on an auth gate, requires the use of `--admin <true|false>` also.')
                }
            } else {
                $lib.warn(`User ({$cmdopts.username}) not found!`)
            }
        ''',
    },
    {
        'name': 'auth.role.add',
        'descr': '''
            Add a role.

            Examples:

                // Add a role named "ninjas"
                auth.role.add ninjas
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the role.'}),
        ),
        'storm': '''
            $role = $lib.auth.roles.add($cmdopts.name)
            $lib.print('Role ({name}) added with iden: {iden}', name=$role.name, iden=$role.iden)
        ''',
    },
    {
        'name': 'auth.role.list',
        'descr': '''
            List all roles.

            Examples:

                // Display the list of all roles
                auth.role.list
        ''',
        'storm': '''
            $roles = ([])
            for $role in $lib.auth.roles.list() {
                $roles.append($role.name)
            }

            $lib.print("Roles:")
            for $role in $lib.sorted($roles) {
                $lib.print(`  {$role}`)
            }
        ''',
    },
    {
        'name': 'auth.role.del',
        'descr': '''
            Delete a role.

            Examples:

                // Delete a role named "ninjas"
                auth.role.del ninjas
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the role.'}),
        ),
        'storm': '''
            $role = $lib.auth.roles.byname($cmdopts.name)
            if $role {
                $lib.auth.roles.del($role.iden)
                $lib.print(`Role ({$cmdopts.name}) deleted.`)
            } else {
                $lib.warn(`Role ({$cmdopts.name}) not found!`)
            }
        ''',
    },
    {
        'name': 'auth.role.mod',
        'descr': '''
            Modify properties of a role.

            Examples:

                // Rename the "ninjas" role to "admins"
                auth.role.mod ninjas --name admins
        ''',
        'cmdargs': (
            ('rolename', {'type': 'str', 'help': 'The name of the role.'}),
            ('--name', {'type': 'str', 'help': 'The new name for the role.'}),
        ),
        'storm': '''
            $role = $lib.auth.roles.byname($cmdopts.rolename)
            if $role {
                if $cmdopts.name {
                    $role.name = $cmdopts.name
                    $lib.print(`Role ({$cmdopts.rolename}) renamed to {$cmdopts.name}.`)
                }
            } else {
                $lib.warn(`Role ({$cmdopts.rolename}) not found!`)
            }
        ''',
    },
    {
        'name': 'auth.user.addrule',
        'descr': '''
            Add a rule to a user.

            Examples:

                // add an allow rule to the user "visi" for permission "foo.bar.baz"
                auth.user.addrule visi foo.bar.baz

                // add a deny rule to the user "visi" for permission "foo.bar.baz"
                auth.user.addrule visi "!foo.bar.baz"

                // add an allow rule to the user "visi" for permission "baz" at the first index.
                auth.user.addrule visi baz --index 0
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the user.'}),
            ('rule', {'type': 'str', 'help': 'The rule string.'}),
            ('--gate', {'type': 'str', 'help': 'The auth gate id to grant permission on.', 'default': None}),
            ('--index', {'type': 'int', 'help': 'Specify the rule location as a 0 based index.', 'default': None}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.name)
            $rule = $lib.auth.ruleFromText($cmdopts.rule)
            if $user {
                $user.addRule($rule, gateiden=$cmdopts.gate, indx=$cmdopts.index)
                $lib.print(`Added rule {$cmdopts.rule} to user {$cmdopts.name}.`)
            } else {
                $lib.warn('User ({name}) not found!', name=$cmdopts.name)
            }
        ''',
    },
    {
        'name': 'auth.user.delrule',
        'descr': '''
            Remove a rule from a user.

            Examples:

                // Delete the allow rule from the user "visi" for permission "foo.bar.baz"
                auth.user.delrule visi foo.bar.baz

                // Delete the deny rule from the user "visi" for permission "foo.bar.baz"
                auth.user.delrule visi "!foo.bar.baz"

                // Delete the rule at index 5 from the user "visi"
                auth.user.delrule visi --index  5
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the user.'}),
            ('rule', {'type': 'str', 'help': 'The rule string.'}),
            ('--gate', {'type': 'str', 'help': 'The auth gate id to grant permission on.', 'default': None}),
            ('--index', {'type': 'bool', 'action': 'store_true', 'default': False,
                'help': 'Specify the rule as a 0 based index into the list of rules.'}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.name)
            if $user {
                if $cmdopts.index {
                    $rule = $user.popRule($cmdopts.rule, gateiden=$cmdopts.gate)
                } else {
                    $rule = $lib.auth.ruleFromText($cmdopts.rule)
                    $user.delRule($rule, gateiden=$cmdopts.gate)
                }
                $ruletext = $lib.auth.textFromRule($rule)
                $lib.print(`Removed rule {$ruletext} from user {$cmdopts.name}.`)
            } else {
                $lib.warn(`User ({$cmdopts.name}) not found!`)
            }
        ''',
    },
    {
        'name': 'auth.role.addrule',
        'descr': '''
            Add a rule to a role.

            Examples:

                // add an allow rule to the role "ninjas" for permission "foo.bar.baz"
                auth.role.addrule ninjas foo.bar.baz

                // add a deny rule to the role "ninjas" for permission "foo.bar.baz"
                auth.role.addrule ninjas "!foo.bar.baz"

                // add an allow rule to the role "ninjas" for permission "baz" at the first index.
                auth.role.addrule ninjas baz --index 0
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the role.'}),
            ('rule', {'type': 'str', 'help': 'The rule string.'}),
            ('--gate', {'type': 'str', 'help': 'The auth gate id to add the rule to.', 'default': None}),
            ('--index', {'type': 'int', 'help': 'Specify the rule location as a 0 based index.', 'default': None}),
        ),
        'storm': '''
            $role = $lib.auth.roles.byname($cmdopts.name)
            $rule = $lib.auth.ruleFromText($cmdopts.rule)
            if $role {
                $role.addRule($rule, gateiden=$cmdopts.gate, indx=$cmdopts.index)
                $lib.print(`Added rule {$cmdopts.rule} to role {$cmdopts.name}.`)
            } else {
                $lib.warn('Role ({name}) not found!', name=$cmdopts.name)
            }
        ''',
    },
    {
        'name': 'auth.role.delrule',
        'descr': '''
            Remove a rule from a role.

            Examples:

                // Delete the allow rule from the role "ninjas" for permission "foo.bar.baz"
                auth.role.delrule ninjas foo.bar.baz

                // Delete the deny rule from the role "ninjas" for permission "foo.bar.baz"
                auth.role.delrule ninjas "!foo.bar.baz"

                // Delete the rule at index 5 from the role "ninjas"
                auth.role.delrule ninjas --index  5
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the role.'}),
            ('rule', {'type': 'str', 'help': 'The rule string.'}),
            ('--gate', {'type': 'str', 'help': 'The auth gate id to remove the rule from.', 'default': None}),
            ('--index', {'type': 'bool', 'action': 'store_true', 'default': False,
                'help': 'Specify the rule as a 0 based index into the list of rules.'}),
        ),
        'storm': '''
            $role = $lib.auth.roles.byname($cmdopts.name)
            if $role {
                if $cmdopts.index {
                    $rule = $role.popRule($cmdopts.rule, gateiden=$cmdopts.gate)
                } else {
                    $rule = $lib.auth.ruleFromText($cmdopts.rule)
                    $role.delRule($rule, gateiden=$cmdopts.gate)
                }
                $ruletext = $lib.auth.textFromRule($rule)
                $lib.print(`Removed rule {$ruletext} from role {$cmdopts.name}.`)
            } else {
                $lib.warn(`Role ({$cmdopts.name}) not found!`)
            }
        ''',
    },
    {
        'name': 'auth.user.grant',
        'descr': '''
            Grant a role to a user.

            Examples:

                // Grant the role "ninjas" to the user "visi"
                auth.user.grant visi ninjas

                // Grant the role "ninjas" to the user "visi" at the first index.
                auth.user.grant visi ninjas --index 0

        ''',
        'cmdargs': (
            ('username', {'type': 'str', 'help': 'The name of the user.'}),
            ('rolename', {'type': 'str', 'help': 'The name of the role.'}),
            ('--index', {'type': 'int', 'help': 'Specify the role location as a 0 based index.', 'default': None}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.username)
            if (not $user) { $lib.exit(`No user named: {$cmdopts.username}`) }

            $role = $lib.auth.roles.byname($cmdopts.rolename)
            if (not $role) { $lib.exit(`No role named: {$cmdopts.rolename}`) }

            $lib.print(`Granting role {$role.name} to user {$user.name}.`)
            $user.grant($role.iden, indx=$cmdopts.index)
        ''',
    },
    {
        'name': 'auth.user.revoke',
        'descr': '''
            Revoke a role from a user.

            Examples:

                // Revoke the role "ninjas" from the user "visi"
                auth.user.revoke visi ninjas

        ''',
        'cmdargs': (
            ('username', {'type': 'str', 'help': 'The name of the user.'}),
            ('rolename', {'type': 'str', 'help': 'The name of the role.'}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.username)
            if (not $user) { $lib.exit(`No user named: {$cmdopts.username}`) }

            $role = $lib.auth.roles.byname($cmdopts.rolename)
            if (not $role) { $lib.exit(`No role named: {$cmdopts.rolename}`) }

            if (not $user.roles().has($role)) {
                $lib.exit(`User {$cmdopts.username} does not have role {$cmdopts.rolename}`)
            }

            $lib.print(`Revoking role {$role.name} from user {$user.name}.`)
            $user.revoke($role.iden)
        ''',
    },
    {
        'name': 'auth.user.show',
        'descr': '''
            Display details for a given user by name.

            Examples:

                // Display details about the user "visi"
                auth.user.show visi
        ''',
        'cmdargs': (
            ('username', {'type': 'str', 'help': 'The name of the user.'}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.username)
            if (not $user) { $lib.exit(`No user named: {$cmdopts.username}`) }

            $lib.print(`User: {$user.name} ({$user.iden})`)
            $lib.print("")
            $lib.print(`  Locked: {$user.locked}`)
            $lib.print(`  Admin: {$user.admin}`)
            $lib.print(`  Email: {$user.email}`)
            $lib.print("  Rules:")
            for ($indx, $rule) in $lib.iters.enum($user.rules) {
                $ruletext = $lib.auth.textFromRule($rule)
                $lib.print(`    [{$lib.cast(str, $indx).ljust(3)}] - {$ruletext}`)
            }

            $lib.print("")
            $lib.print("  Roles:")
            for $role in $user.roles() {
                $lib.print(`    {$role.iden} - {$role.name}`)
            }

            $lib.print("")
            $lib.print("  Gates:")
            for $gate in $user.gates() {
                for $gateuser in $gate.users {
                    if  ( $gateuser.iden = $user.iden ) {
                        break
                    }
                }
                $lib.print(`    {$gate.iden} - ({$gate.type})`)
                $lib.print(`      Admin: {$gateuser.admin}`)
                for ($indx, $rule) in $lib.iters.enum($user.getRules(gateiden=$gate.iden)) {
                    $ruletext = $lib.auth.textFromRule($rule)
                    $indxtext = $lib.cast(str, $indx).ljust(3)
                    $lib.print(`      [{$indxtext}] - {$ruletext}`)
                }
            }
        ''',
    },
    {
        'name': 'auth.user.allowed',
        'descr': '''
            Show whether the user is allowed the given permission and why.

            Examples:

                auth.user.allowed visi foo.bar
        ''',
        'cmdargs': (
            ('username', {'type': 'str', 'help': 'The name of the user.'}),
            ('permname', {'type': 'str', 'help': 'The permission string.'}),
            ('--gate', {'type': 'str', 'help': 'An auth gate to test the perms against.'}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.username)
            if (not $user) { $lib.exit(`No user named: {$cmdopts.username}`) }

            ($allow, $reason) = $user.getAllowedReason($cmdopts.permname, gateiden=$cmdopts.gate)
            $lib.print(`allowed: {$allow} - {$reason}`)
        ''',
    },
    {
        'name': 'auth.role.show',
        'descr': '''

            Display details for a given role by name.

            Examples:

                // Display details about the role "ninjas"
                auth.role.show ninjas
        ''',
        'cmdargs': (
            ('rolename', {'type': 'str', 'help': 'The name of the role.'}),
        ),
        'storm': '''

            $role = $lib.auth.roles.byname($cmdopts.rolename)
            if (not $role) { $lib.exit(`No role named: {$cmdopts.rolename}`) }

            $lib.print(`Role: {$role.name} ({$role.iden})`)

            $lib.print("")
            $lib.print("  Rules:")
            for ($indx, $rule) in $lib.iters.enum($role.rules) {
                $ruletext = $lib.auth.textFromRule($rule)
                $indxtext = $lib.cast(str, $indx).ljust(3)
                $lib.print(`    [{$indxtext}] - {$ruletext}`)
            }

            $lib.print("")
            $lib.print("  Gates:")
            for $gate in $role.gates() {
                $lib.print(`    {$gate.iden} - ({$gate.type})`)
                for ($indx, $rule) in $lib.iters.enum($role.getRules(gateiden=$gate.iden)) {
                    $ruletext = $lib.auth.textFromRule($rule)
                    $indxtext = $lib.cast(str, $indx).ljust(3)
                    $lib.print(`      [{$indxtext}] - {$ruletext}`)
                }
            }
        '''
    },
    {
        'name': 'auth.gate.show',
        'descr': '''

            Display users, roles, and permissions for an auth gate.

            Examples:
                // Display the users and roles with permissions to the top layer of the current view.
                auth.gate.show $lib.layer.get().iden

                // Display the users and roles with permissions to the current view.
                auth.gate.show $lib.view.get().iden
        ''',
        'cmdargs': (
            ('gateiden', {'type': 'str', 'help': 'The GUID of the auth gate.'}),
        ),
        'storm': '''

            $gate = $lib.auth.gates.get($cmdopts.gateiden)
            if (not $gate) { $lib.exit(`No auth gate found for iden: {$cmdopts.gateiden}.`) }

            $lib.print(`Gate Type: {$gate.type}`)

            $lib.print("")
            $lib.print("Auth Gate Users:")
            for $gateuser in $gate.users {
                $user = $lib.auth.users.get($gateuser.iden)
                $lib.print(`  {$user.iden} - {$user.name}`)
                $lib.print(`    Admin: {$gateuser.admin}`)
                $lib.print(`    Rules:`)
                for ($indx, $rule) in $lib.iters.enum($gateuser.rules) {
                    $ruletext = $lib.auth.textFromRule($rule)
                    $indxtext = $lib.cast(str, $indx).ljust(3)
                    $lib.print(`     [{$indxtext}] - {$ruletext}`)
                }
            }

            $lib.print("")
            $lib.print("Auth Gate Roles:")
            for $gaterole in $gate.roles {
                $role = $lib.auth.roles.get($gaterole.iden)
                $lib.print(`  {$role.iden} - {$role.name}`)
                $lib.print(`    Rules:`)
                for ($indx, $rule) in $lib.iters.enum($gaterole.rules) {
                    $ruletext = $lib.auth.textFromRule($rule)
                    $indxtext = $lib.cast(str, $indx).ljust(3)
                    $lib.print(`      [{$indxtext}] - {$ruletext}`)
                }
            }
        '''
    },
    {
        'name': 'auth.perms.list',
        'descr': 'Display a list of the current permissions defined within the Cortex.',
        'cmdargs': (
            ('--find', {'type': 'str', 'help': 'A search string for permissions.'}),
        ),
        'storm': '''

            for $pdef in $lib.auth.getPermDefs() {
                $perm = $lib.str.join(".", $pdef.perm)

                if $cmdopts.find {
                    $find = $cmdopts.find.lower()
                    $match = (
                        $perm.lower().find($find) != (null) or
                        $pdef.desc.lower().find($find) != (null) or
                        $pdef.gate.lower().find($find) != (null) or
                        ($pdef.ex and $pdef.ex.lower().find($find) != (null))
                    )

                    if (not $match) { continue }
                }

                $lib.print($perm)
                $lib.print(`    {$pdef.desc}`)
                $lib.print(`    gate: {$pdef.gate}`)
                $lib.print(`    default: {$pdef.default}`)
                if $pdef.ex { $lib.print(`    example: {$pdef.ex}`) }
                $lib.print('')
            }
        '''
    },
)

def ruleFromText(text):
    '''
    Get a rule tuple from a text string.

    Args:
        text (str): The string to process.

    Returns:
        (bool, tuple): A tuple containing a bool and a list of permission parts.
    '''

    allow = True
    if text.startswith('!'):
        text = text[1:]
        allow = False

    return (allow, tuple(text.split('.')))

@s_stormtypes.registry.registerType
class UserProfile(s_stormtypes.Prim):
    '''
    The Storm deref/setitem/iter convention on top of User profile information.
    '''
    _storm_typename = 'auth:user:profile'
    _ismutable = True

    def __init__(self, runt, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt

    async def deref(self, name):
        name = await s_stormtypes.tostr(name)
        self.runt.confirm(('auth', 'user', 'get', 'profile', name))
        return await self.runt.snap.core.getUserProfInfo(self.valu, name)

    async def setitem(self, name, valu):
        name = await s_stormtypes.tostr(name)

        if valu is s_stormtypes.undef:
            self.runt.confirm(('auth', 'user', 'pop', 'profile', name))
            await self.runt.snap.core.popUserProfInfo(self.valu, name)
            return

        valu = await s_stormtypes.toprim(valu)
        self.runt.confirm(('auth', 'user', 'set', 'profile', name))
        await self.runt.snap.core.setUserProfInfo(self.valu, name, valu)

    async def iter(self):
        profile = await self.value()
        for item in list(profile.items()):
            yield item

    async def value(self):
        self.runt.confirm(('auth', 'user', 'get', 'profile'))
        return await self.runt.snap.core.getUserProfile(self.valu)

@s_stormtypes.registry.registerType
class UserJson(s_stormtypes.Prim):
    '''
    Implements per-user JSON storage.
    '''
    _storm_typename = 'auth:user:json'
    _ismutable = False
    _storm_locals = (
        {'name': 'get', 'desc': 'Return a stored JSON object or object property for the user.',
         'type': {'type': 'function', '_funcname': 'get',
                   'args': (
                        {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.'},
                        {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                    ),
                    'returns': {'type': 'prim', 'desc': 'The previously stored value or ``(null)``.'}}},

        {'name': 'set', 'desc': 'Set a JSON object or object property for the user.',
         'type': {'type': 'function', '_funcname': 'set',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path elements.'},
                       {'name': 'valu', 'type': 'prim', 'desc': 'The value to set as the JSON object or object property.'},
                       {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                   ),
                   'returns': {'type': 'boolean', 'desc': 'True if the set operation was successful.'}}},

        {'name': 'del', 'desc': 'Delete a stored JSON object or object property for the user.',
         'type': {'type': 'function', '_funcname': '_del',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.'},
                       {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                   ),
                   'returns': {'type': 'boolean', 'desc': 'True if the del operation was successful.'}}},

        {'name': 'iter', 'desc': 'Yield (<path>, <valu>) tuples for the users JSON objects.',
         'type': {'type': 'function', '_funcname': 'iter',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.', 'default': None},
                   ),
                   'returns': {'name': 'Yields', 'type': 'list', 'desc': '(<path>, <item>) tuples.'}}},
    )

    def __init__(self, runt, valu):
        s_stormtypes.Prim.__init__(self, valu)
        self.runt = runt
        self.locls.update({
            'get': self.get,
            'set': self.set,
            'has': self.has,
            'del': self._del,
            'iter': self.iter,
        })

    @s_stormtypes.stormfunc(readonly=True)
    async def has(self, path):

        path = await s_stormtypes.toprim(path)
        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path
        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'get'))

        return await self.runt.snap.core.hasJsonObj(fullpath)

    @s_stormtypes.stormfunc(readonly=True)
    async def get(self, path, prop=None):
        path = await s_stormtypes.toprim(path)
        prop = await s_stormtypes.toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'get'))

        if prop is None:
            return await self.runt.snap.core.getJsonObj(fullpath)

        return await self.runt.snap.core.getJsonObjProp(fullpath, prop=prop)

    async def set(self, path, valu, prop=None):
        path = await s_stormtypes.toprim(path)
        valu = await s_stormtypes.toprim(valu)
        prop = await s_stormtypes.toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'set'))

        if prop is None:
            await self.runt.snap.core.setJsonObj(fullpath, valu)
            return True

        return await self.runt.snap.core.setJsonObjProp(fullpath, prop, valu)

    async def _del(self, path, prop=None):
        path = await s_stormtypes.toprim(path)
        prop = await s_stormtypes.toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'set'))

        if prop is None:
            await self.runt.snap.core.delJsonObj(fullpath)
            return True

        return await self.runt.snap.core.delJsonObjProp(fullpath, prop=prop)

    @s_stormtypes.stormfunc(readonly=True)
    async def iter(self, path=None):

        path = await s_stormtypes.toprim(path)

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'get'))

        fullpath = ('users', self.valu, 'json')
        if path is not None:
            if isinstance(path, str):
                path = tuple(path.split('/'))
            fullpath += path

        async for path, item in self.runt.snap.core.getJsonObjs(fullpath):
            yield path, item

@s_stormtypes.registry.registerType
class UserVars(s_stormtypes.Prim):
    '''
    The Storm deref/setitem/iter convention on top of User vars information.
    '''
    _storm_typename = 'auth:user:vars'
    _ismutable = True

    def __init__(self, runt, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt

    async def deref(self, name):
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.getUserVarValu(self.valu, name)

    async def setitem(self, name, valu):
        name = await s_stormtypes.tostr(name)

        if valu is s_stormtypes.undef:
            await self.runt.snap.core.popUserVarValu(self.valu, name)
            return

        valu = await s_stormtypes.toprim(valu)
        await self.runt.snap.core.setUserVarValu(self.valu, name, valu)

    async def iter(self):
        async for name, valu in self.runt.snap.core.iterUserVars(self.valu):
            yield name, valu
            await asyncio.sleep(0)

@s_stormtypes.registry.registerType
class User(s_stormtypes.Prim):
    '''
    Implements the Storm API for a User.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The User iden.', 'type': 'str', },
        {'name': 'get', 'desc': 'Get a arbitrary property from the User definition.',
         'type': {'type': 'function', '_funcname': '_methUserGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the property to return.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'roles', 'desc': 'Get the Roles for the User.',
         'type': {'type': 'function', '_funcname': '_methUserRoles',
                  'returns': {'type': 'list',
                              'desc': 'A list of ``auth:roles`` which the user is a member of.', }}},
        {'name': 'pack', 'desc': 'Get the packed version of the User.',
         'type': {'type': 'function', '_funcname': '_methUserPack', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'The packed User definition.', }}},
        {'name': 'allowed', 'desc': 'Check if the user has a given permission.',
         'type': {'type': 'function', '_funcname': '_methUserAllowed',
                  'args': (
                      {'name': 'permname', 'type': 'str', 'desc': 'The permission string to check.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The authgate iden.', 'default': None, },
                      {'name': 'default', 'type': 'boolean', 'desc': 'The default value.', 'default': False, },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the rule is allowed, False otherwise.', }}},
        {'name': 'getAllowedReason', 'desc': 'Return an allowed status and reason for the given perm.',
         'type': {'type': 'function', '_funcname': '_methGetAllowedReason',
                  'args': (
                      {'name': 'permname', 'type': 'str', 'desc': 'The permission string to check.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The authgate iden.', 'default': None, },
                      {'name': 'default', 'type': 'boolean', 'desc': 'The default value.', 'default': False, },
                  ),
                  'returns': {'type': 'list', 'desc': 'An (allowed, reason) tuple.', }}},
        {'name': 'grant', 'desc': 'Grant a Role to the User.',
         'type': {'type': 'function', '_funcname': '_methUserGrant',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Role.', },
                      {'name': 'indx', 'type': 'int', 'desc': 'The position of the Role as a 0 based index.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setRoles', 'desc': '''
        Replace all the Roles of the User with a new list of roles.

        Notes:
            The roleiden for the "all" role must be present in the new list of roles. This replaces all existing roles
            that the user has with the new roles.
        ''',
         'type': {'type': 'function', '_funcname': '_methUserSetRoles',
                  'args': (
                      {'name': 'idens', 'type': 'list', 'desc': 'The idens of the Roles to set on the User.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'revoke', 'desc': 'Remove a Role from the User',
         'type': {'type': 'function', '_funcname': '_methUserRevoke',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Role.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'tell', 'desc': 'Send a tell notification to a user.',
         'type': {'type': 'function', '_funcname': '_methUserTell',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text of the message to send.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'notify', 'desc': 'Send an arbitrary user notification.',
         'type': {'type': 'function', '_funcname': '_methUserNotify',
                  'args': (
                      {'name': 'mesgtype', 'type': 'str', 'desc': 'The notification type.', },
                      {'name': 'mesgdata', 'type': 'dict', 'desc': 'The notification data.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'addRule', 'desc': 'Add a rule to the User.',
         'type': {'type': 'function', '_funcname': '_methUserAddRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to add to the User.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.',
                       'default': None, },
                      {'name': 'indx', 'type': 'int', 'desc': 'The position of the rule as a 0 based index.',
                       'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delRule', 'desc': 'Remove a rule from the User.',
         'type': {'type': 'function', '_funcname': '_methUserDelRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to removed from the User.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.', 'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'popRule', 'desc': 'Remove a rule by index from the User.',
         'type': {'type': 'function', '_funcname': '_methUserPopRule',
                  'args': (
                      {'name': 'indx', 'type': 'int', 'desc': 'The index of the rule to remove.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.', 'default': None, }
                  ),
                  'returns': {'type': 'list', 'desc': 'The rule which was removed.'}}},
        {'name': 'setRules', 'desc': 'Replace the rules on the User with new rules.',
         'type': {'type': 'function', '_funcname': '_methUserSetRules',
                  'args': (
                      {'name': 'rules', 'type': 'list', 'desc': 'A list of rule tuples.', },
                      {'name': 'gateiden', 'type': 'str',
                       'desc': 'The gate iden used for the rules.', 'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'getRules', 'desc': 'Get the rules for the user and optional auth gate.',
         'type': {'type': 'function', '_funcname': '_methGetRules',
                  'args': (
                      {'name': 'gateiden', 'type': 'str',
                       'desc': 'The gate iden used for the rules.', 'default': None},
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of rules.'}}},
        {'name': 'setAdmin', 'desc': 'Set the Admin flag for the user.',
         'type': {'type': 'function', '_funcname': '_methUserSetAdmin',
                  'args': (
                      {'name': 'admin', 'type': 'boolean',
                       'desc': 'True to make the User an admin, false to remove their admin status.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the operation.',
                       'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setEmail', 'desc': 'Set the email address of the User.',
         'type': {'type': 'function', '_funcname': '_methUserSetEmail',
                  'args': (
                      {'name': 'email', 'type': 'str', 'desc': 'The email address to set for the User.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setLocked', 'desc': 'Set the locked status for a user.',
         'type': {'type': 'function', '_funcname': '_methUserSetLocked',
                  'args': (
                      {'name': 'locked', 'type': 'boolean', 'desc': 'True to lock the user, false to unlock them.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setArchived', 'desc': '''
        Set the archived status for a user.

        Notes:
            Setting a user as "archived" will also lock the user.
            Removing a users "archived" status will not unlock the user.
        ''',
         'type': {'type': 'function', '_funcname': '_methUserSetArchived',
                  'args': (
                      {'name': 'archived', 'type': 'boolean', 'desc': 'True to archive the user, false to unarchive them.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setPasswd', 'desc': 'Set the Users password.',
         'type': {'type': 'function', '_funcname': '_methUserSetPasswd',
                  'args': (
                      {'name': 'passwd', 'type': 'str',
                       'desc': 'The new password for the user. This is best passed into the runtime as a variable.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'gates', 'desc': 'Return a list of auth gates that the user has rules for.',
         'type': {'type': 'function', '_funcname': '_methGates',
                  'args': (),
                  'returns': {'type': 'list',
                              'desc': 'A list of ``auth:gates`` that the user has rules for.', }}},
        {'name': 'name', 'desc': '''
        A user's name. This can also be used to set a user's name.

        Example:
                Change a user's name::

                    $user=$lib.auth.users.byname(bob) $user.name=robert
        ''',
         'type': {'type': 'stor', '_storfunc': '_storUserName',
                  'returns': {'type': 'str', }}},
        {'name': 'email', 'desc': '''
        A user's email. This can also be used to set the user's email.

        Example:
                Change a user's email address::

                    $user=$lib.auth.users.byname(bob) $user.email="robert@bobcorp.net"
        ''',
         'type': {'type': ['stor'], '_storfunc': '_methUserSetEmail',
                  'returns': {'type': ['str', 'null'], }}},
        {'name': 'profile', 'desc': '''
        A user profile dictionary. This can be used as an application level key-value store.

        Example:
            Set a value::

                $user=$lib.auth.users.byname(bob) $user.profile.somekey="somevalue"

            Get a value::

                $user=$lib.auth.users.byname(bob) $value = $user.profile.somekey
        ''',
        'type': {'type': ['ctor'], '_ctorfunc': '_ctorUserProfile',
                 'returns': {'type': 'auth:user:profile', }}},
        {'name': 'vars',
         'desc': "Get a dictionary representing the user's persistent variables.",
         'type': {'type': ['ctor'], '_ctorfunc': '_ctorUserVars',
                  'returns': {'type': 'auth:user:vars'}}},
        {'name': 'genApiKey', 'desc': '''Generate a new API key for the user.

        Notes:
            The secret API key returned by this function cannot be accessed again.
        ''',
         'type': {'type': 'function', '_funcname': '_methGenApiKey',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the API key.'},
                      {'name': 'duration', 'type': 'integer', 'default': None,
                       'desc': 'Duration of time for the API key to be valid, in milliseconds.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A list, containing the secret API key and a dictionary containing metadata about the key.'}}},
        {'name': 'getApiKey', 'desc': "Get information about a user's existing API key.",
         'type': {'type': 'function', '_funcname': '_methGetApiKey',
                  'args': (
                      {'name': 'iden', 'type': 'str',
                       'desc': 'The iden of the API key.'},
                  ),
                  'returns': {'type': 'dict',
                              'desc': 'A dictionary containing metadata about the key.'}}},
        {'name': 'listApiKeys', 'desc': 'Get information about all the API keys the user has.',
         'type': {'type': 'function', '_funcname': '_methListApiKeys',
                  'args': (),
                  'returns': {'type': 'list',
                              'desc': 'A list of dictionaries containing metadata about each key.'}}},
        {'name': 'modApiKey', 'desc': 'Modify metadata about an existing API key.',
         'type': {'type': 'function', '_funcname': '_methModApiKey',
                  'args': (
                      {'name': 'iden', 'type': 'str',
                       'desc': 'The iden of the API key.'},
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the valu to update.'},
                      {'name': 'valu', 'type': 'any',
                       'desc': 'The new value of the API key.'},
                  ),
                  'returns': {'type': 'dict',
                              'desc': 'An updated dictionary with metadata about the key.'}}},
        {'name': 'delApiKey', 'desc': 'Delete an existing API key.',
         'type': {'type': 'function', '_funcname': '_methDelApiKey',
                  'args': (
                      {'name': 'iden', 'type': 'str',
                       'desc': 'The iden of the API key.'},
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True when the key was deleted.'}}},
    )
    _storm_typename = 'auth:user'
    _ismutable = False

    def __init__(self, runt, valu, path=None):

        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt

        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu
        self.stors.update({
            'name': self._storUserName,
            'email': self._methUserSetEmail,
        })
        self.ctors.update({
            'json': self._ctorUserJson,
            'vars': self._ctorUserVars,
            'profile': self._ctorUserProfile,
        })

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def _ctorUserJson(self, path=None):
        return UserJson(self.runt, self.valu)

    def _ctorUserProfile(self, path=None):
        return UserProfile(self.runt, self.valu)

    def _ctorUserVars(self, path=None):
        if self.runt.user.iden != self.valu and not self.runt.isAdmin():
            mesg = '$user.vars requires admin privs when $user is not the current user.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return UserVars(self.runt, self.valu)

    def getObjLocals(self):
        return {
            'get': self._methUserGet,
            'pack': self._methUserPack,
            'tell': self._methUserTell,
            'gates': self._methGates,
            'notify': self._methUserNotify,
            'roles': self._methUserRoles,
            'allowed': self._methUserAllowed,
            'grant': self._methUserGrant,
            'revoke': self._methUserRevoke,
            'addRule': self._methUserAddRule,
            'delRule': self._methUserDelRule,
            'popRule': self._methUserPopRule,
            'setRoles': self._methUserSetRoles,
            'getRules': self._methGetRules,
            'setRules': self._methUserSetRules,
            'setAdmin': self._methUserSetAdmin,
            'setEmail': self._methUserSetEmail,
            'setLocked': self._methUserSetLocked,
            'setPasswd': self._methUserSetPasswd,
            'setArchived': self._methUserSetArchived,
            'getAllowedReason': self._methGetAllowedReason,
            'genApiKey': self._methGenApiKey,
            'getApiKey': self._methGetApiKey,
            'listApiKeys': self._methListApiKeys,
            'modApiKey': self._methModApiKey,
            'delApiKey': self._methDelApiKey,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methUserPack(self):
        return await self.value()

    async def _methUserTell(self, text):
        self.runt.confirm(('tell', self.valu), default=True)
        mesgdata = {
            'text': await s_stormtypes.tostr(text),
            'from': self.runt.user.iden,
        }
        return await self.runt.snap.core.addUserNotif(self.valu, 'tell', mesgdata)

    async def _methUserNotify(self, mesgtype, mesgdata):
        if not self.runt.isAdmin():
            mesg = '$user.notify() method requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        mesgtype = await s_stormtypes.tostr(mesgtype)
        mesgdata = await s_stormtypes.toprim(mesgdata)
        return await self.runt.snap.core.addUserNotif(self.valu, mesgtype, mesgdata)

    async def _storUserName(self, name):

        name = await s_stormtypes.tostr(name)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'name'), default=True)
            await self.runt.snap.core.setUserName(self.valu, name)
            return

        self.runt.confirm(('auth', 'user', 'set', 'name'))
        await self.runt.snap.core.setUserName(self.valu, name)

    async def _derefGet(self, name):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return udef.get(name, s_common.novalu)

    async def _methUserGet(self, name):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return udef.get(name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGates(self):
        user = self.runt.snap.core.auth.user(self.valu)
        retn = []
        for gateiden in user.authgates.keys():
            gate = await self.runt.snap.core.getAuthGate(gateiden)
            retn.append(Gate(self.runt, gate))
        return retn

    @s_stormtypes.stormfunc(readonly=True)
    async def _methUserRoles(self):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return [Role(self.runt, rdef['iden']) for rdef in udef.get('roles')]

    @s_stormtypes.stormfunc(readonly=True)
    async def _methUserAllowed(self, permname, gateiden=None, default=False):
        permname = await s_stormtypes.tostr(permname)
        gateiden = await s_stormtypes.tostr(gateiden)
        default = await s_stormtypes.tobool(default)

        perm = tuple(permname.split('.'))
        user = await self.runt.snap.core.auth.reqUser(self.valu)
        return user.allowed(perm, gateiden=gateiden, default=default)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGetAllowedReason(self, permname, gateiden=None, default=False):
        permname = await s_stormtypes.tostr(permname)
        gateiden = await s_stormtypes.tostr(gateiden)
        default = await s_stormtypes.tobool(default)

        perm = tuple(permname.split('.'))
        user = await self.runt.snap.core.auth.reqUser(self.valu)
        reason = user.getAllowedReason(perm, gateiden=gateiden, default=default)
        return reason.value, reason.mesg

    async def _methUserGrant(self, iden, indx=None):
        self.runt.confirm(('auth', 'user', 'grant'))
        indx = await s_stormtypes.toint(indx, noneok=True)
        await self.runt.snap.core.addUserRole(self.valu, iden, indx=indx)

    async def _methUserSetRoles(self, idens):
        self.runt.confirm(('auth', 'user', 'grant'))
        self.runt.confirm(('auth', 'user', 'revoke'))
        idens = await s_stormtypes.toprim(idens)
        await self.runt.snap.core.setUserRoles(self.valu, idens)

    async def _methUserRevoke(self, iden):
        self.runt.confirm(('auth', 'user', 'revoke'))
        await self.runt.snap.core.delUserRole(self.valu, iden)

    async def _methUserSetRules(self, rules, gateiden=None):
        rules = await s_stormtypes.toprim(rules)
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'user', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.setUserRules(self.valu, rules, gateiden=gateiden)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGetRules(self, gateiden=None):
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        user = self.runt.snap.core.auth.user(self.valu)
        return user.getRules(gateiden=gateiden)

    async def _methUserAddRule(self, rule, gateiden=None, indx=None):
        rule = await s_stormtypes.toprim(rule)
        indx = await s_stormtypes.toint(indx, noneok=True)
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'user', 'set', 'rules'), gateiden=gateiden)
        # TODO: Remove me in 3.0.0
        if gateiden == 'cortex':
            mesg = f'Adding rule on the "cortex" authgate. This authgate is not used ' \
                   f'for permission checks and will be removed in Synapse v3.0.0.'
            await self.runt.snap.warn(mesg, log=False)
        await self.runt.snap.core.addUserRule(self.valu, rule, indx=indx, gateiden=gateiden)

    async def _methUserDelRule(self, rule, gateiden=None):
        rule = await s_stormtypes.toprim(rule)
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'user', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.delUserRule(self.valu, rule, gateiden=gateiden)

    async def _methUserPopRule(self, indx, gateiden=None):

        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'user', 'set', 'rules'), gateiden=gateiden)

        indx = await s_stormtypes.toint(indx)
        rules = list(await self._methGetRules(gateiden=gateiden))

        if len(rules) <= indx:
            mesg = f'User {self.valu} only has {len(rules)} rules.'
            raise s_exc.BadArg(mesg=mesg)

        retn = rules.pop(indx)
        await self.runt.snap.core.setUserRules(self.valu, rules, gateiden=gateiden)
        return retn

    async def _methUserSetEmail(self, email):
        email = await s_stormtypes.tostr(email)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'email'), default=True)
            await self.runt.snap.core.setUserEmail(self.valu, email)
            return

        self.runt.confirm(('auth', 'user', 'set', 'email'))
        await self.runt.snap.core.setUserEmail(self.valu, email)

    async def _methUserSetAdmin(self, admin, gateiden=None):
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'user', 'set', 'admin'), gateiden=gateiden)
        admin = await s_stormtypes.tobool(admin)

        await self.runt.snap.core.setUserAdmin(self.valu, admin, gateiden=gateiden)

    async def _methUserSetPasswd(self, passwd):
        passwd = await s_stormtypes.tostr(passwd, noneok=True)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'passwd'), default=True)
            return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

        self.runt.confirm(('auth', 'user', 'set', 'passwd'))
        return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

    async def _methUserSetLocked(self, locked):
        self.runt.confirm(('auth', 'user', 'set', 'locked'))
        await self.runt.snap.core.setUserLocked(self.valu, await s_stormtypes.tobool(locked))

    async def _methUserSetArchived(self, archived):
        self.runt.confirm(('auth', 'user', 'set', 'archived'))
        await self.runt.snap.core.setUserArchived(self.valu, await s_stormtypes.tobool(archived))

    async def _methGenApiKey(self, name, duration=None):
        name = await s_stormtypes.tostr(name)
        duration = await s_stormtypes.toint(duration, noneok=True)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'apikey'), default=True)
            return await self.runt.snap.core.addUserApiKey(self.valu, name, duration=duration)
        self.runt.confirm(('auth', 'user', 'set', 'apikey'))
        return await self.runt.snap.core.addUserApiKey(self.valu, name, duration=duration)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGetApiKey(self, iden):
        iden = await s_stormtypes.tostr(iden)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'apikey'), default=True)
            valu = await self.runt.snap.core.getUserApiKey(iden)
        else:
            self.runt.confirm(('auth', 'user', 'set', 'apikey'))
            valu = await self.runt.snap.core.getUserApiKey(iden)
        valu.pop('shadow', None)
        return valu

    @s_stormtypes.stormfunc(readonly=True)
    async def _methListApiKeys(self):
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'apikey'), default=True)
            return await self.runt.snap.core.listUserApiKeys(self.valu)

        self.runt.confirm(('auth', 'user', 'set', 'apikey'))
        return await self.runt.snap.core.listUserApiKeys(self.valu)

    async def _methModApiKey(self, iden, name, valu):
        iden = await s_stormtypes.tostr(iden)
        name = await s_stormtypes.tostr(name)
        valu = await s_stormtypes.toprim(valu)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'apikey'), default=True)
            return await self.runt.snap.core.modUserApiKey(iden, name, valu)
        self.runt.confirm(('auth', 'user', 'set', 'apikey'))
        return await self.runt.snap.core.modUserApiKey(iden, name, valu)

    async def _methDelApiKey(self, iden):
        iden = await s_stormtypes.tostr(iden)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'apikey'), default=True)
            return await self.runt.snap.core.delUserApiKey(iden)
        self.runt.confirm(('auth', 'user', 'set', 'apikey'))
        return await self.runt.snap.core.delUserApiKey(iden)

    async def value(self):
        return await self.runt.snap.core.getUserDef(self.valu)

    async def stormrepr(self):
        return f'{self._storm_typename}: {await self.value()}'

@s_stormtypes.registry.registerType
class Role(s_stormtypes.Prim):
    '''
    Implements the Storm API for a Role.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The Role iden.', 'type': 'str', },
        {'name': 'get', 'desc': 'Get a arbitrary property from the Role definition.',
         'type': {'type': 'function', '_funcname': '_methRoleGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the property to return.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'pack', 'desc': 'Get the packed version of the Role.',
         'type': {'type': 'function', '_funcname': '_methRolePack', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'The packed Role definition.', }}},
        {'name': 'gates', 'desc': 'Return a list of auth gates that the role has rules for.',
         'type': {'type': 'function', '_funcname': '_methGates',
                  'args': (),
                  'returns': {'type': 'list',
                              'desc': 'A list of ``auth:gates`` that the role has rules for.', }}},
        {'name': 'addRule', 'desc': 'Add a rule to the Role',
         'type': {'type': 'function', '_funcname': '_methRoleAddRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to added to the Role.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.',
                       'default': None, },
                      {'name': 'indx', 'type': 'int', 'desc': 'The position of the rule as a 0 based index.',
                       'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delRule', 'desc': 'Remove a rule from the Role.',
         'type': {'type': 'function', '_funcname': '_methRoleDelRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to removed from the Role.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null', }
                  }},
        {'name': 'popRule', 'desc': 'Remove a rule by index from the Role.',
         'type': {'type': 'function', '_funcname': '_methRolePopRule',
                  'args': (
                      {'name': 'indx', 'type': 'int', 'desc': 'The index of the rule to remove.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.', 'default': None, }
                  ),
                  'returns': {'type': 'list', 'desc': 'The rule which was removed.'}}},
        {'name': 'getRules', 'desc': 'Get the rules for the role and optional auth gate.',
         'type': {'type': 'function', '_funcname': '_methGetRules',
                  'args': (
                      {'name': 'gateiden', 'type': 'str',
                       'desc': 'The gate iden used for the rules.', 'default': None},
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of rules.'}}},
        {'name': 'setRules', 'desc': 'Replace the rules on the Role with new rules.',
         'type': {'type': 'function', '_funcname': '_methRoleSetRules',
                  'args': (
                      {'name': 'rules', 'type': 'list', 'desc': 'A list of rules to set on the Role.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rules.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'name', 'desc': '''
            A role's name. This can also be used to set the role name.

            Example:
                    Change a role's name::

                        $role=$lib.auth.roles.byname(analyst) $role.name=superheroes
            ''',
         'type': {'type': 'stor', '_storfunc': '_setRoleName',
                  'returns': {'type': 'str', }}},
    )
    _storm_typename = 'auth:role'
    _ismutable = False

    def __init__(self, runt, valu, path=None):

        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu
        self.stors.update({
            'name': self._setRoleName,
        })

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def getObjLocals(self):
        return {
            'get': self._methRoleGet,
            'pack': self._methRolePack,
            'gates': self._methGates,
            'addRule': self._methRoleAddRule,
            'delRule': self._methRoleDelRule,
            'popRule': self._methRolePopRule,
            'setRules': self._methRoleSetRules,
            'getRules': self._methGetRules,
        }

    async def _derefGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name, s_common.novalu)

    async def _setRoleName(self, name):
        self.runt.confirm(('auth', 'role', 'set', 'name'))
        name = await s_stormtypes.tostr(name)
        await self.runt.snap.core.setRoleName(self.valu, name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRoleGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRolePack(self):
        return await self.value()

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGates(self):
        role = self.runt.snap.core.auth.role(self.valu)
        retn = []
        for gateiden in role.authgates.keys():
            gate = await self.runt.snap.core.getAuthGate(gateiden)
            retn.append(Gate(self.runt, gate))
        return retn

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGetRules(self, gateiden=None):
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        role = self.runt.snap.core.auth.role(self.valu)
        return role.getRules(gateiden=gateiden)

    async def _methRoleSetRules(self, rules, gateiden=None):
        rules = await s_stormtypes.toprim(rules)
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'role', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.setRoleRules(self.valu, rules, gateiden=gateiden)

    async def _methRoleAddRule(self, rule, gateiden=None, indx=None):
        rule = await s_stormtypes.toprim(rule)
        indx = await s_stormtypes.toint(indx, noneok=True)
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'role', 'set', 'rules'), gateiden=gateiden)
        # TODO: Remove me in 3.0.0
        if gateiden == 'cortex':
            mesg = f'Adding rule on the "cortex" authgate. This authgate is not used ' \
                   f'for permission checks and will be removed in Synapse v3.0.0.'
            await self.runt.snap.warn(mesg, log=False)
        await self.runt.snap.core.addRoleRule(self.valu, rule, indx=indx, gateiden=gateiden)

    async def _methRoleDelRule(self, rule, gateiden=None):
        rule = await s_stormtypes.toprim(rule)
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'role', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.delRoleRule(self.valu, rule, gateiden=gateiden)

    async def _methRolePopRule(self, indx, gateiden=None):

        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        self.runt.confirm(('auth', 'role', 'set', 'rules'), gateiden=gateiden)

        indx = await s_stormtypes.toint(indx)

        rules = list(await self._methGetRules(gateiden=gateiden))

        if len(rules) <= indx:
            mesg = f'Role {self.valu} only has {len(rules)} rules.'
            raise s_exc.BadArg(mesg=mesg)

        retn = rules.pop(indx)
        await self.runt.snap.core.setRoleRules(self.valu, rules, gateiden=gateiden)
        return retn

    async def value(self):
        return await self.runt.snap.core.getRoleDef(self.valu)

    async def stormrepr(self):
        return f'{self._storm_typename}: {await self.value()}'

@s_stormtypes.registry.registerLib
class LibAuth(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Auth in the Cortex.
    '''
    _storm_locals = (
        {'name': 'ruleFromText', 'desc': 'Get a rule tuple from a text string.',
         'type': {'type': 'function', '_funcname': 'ruleFromText',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The string to process.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A tuple containing a bool and a list of permission parts.', }}},
        {'name': 'textFromRule', 'desc': 'Return a text string from a rule tuple.',
         'type': {'type': 'function', '_funcname': 'textFromRule',
                  'args': (
                    {'name': 'rule', 'type': 'list', 'desc': 'A rule tuple.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The rule text.'}}},
        {'name': 'getPermDefs', 'desc': 'Return a list of permission definitions.',
         'type': {'type': 'function', '_funcname': 'getPermDefs',
                  'args': (),
                  'returns': {'type': 'list', 'desc': 'The list of permission definitions.'}}},
        {'name': 'getPermDef', 'desc': 'Return a single permission definition.',
         'type': {'type': 'function', '_funcname': 'getPermDef',
                  'args': (
                    {'name': 'perm', 'type': 'list', 'desc': 'A permission tuple.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A permission definition or null.'}}},
    )
    _storm_lib_path = ('auth',)

    def getObjLocals(self):
        return {
            'getPermDef': self.getPermDef,
            'getPermDefs': self.getPermDefs,
            'ruleFromText': self.ruleFromText,
            'textFromRule': self.textFromRule,
        }

    @staticmethod
    @s_stormtypes.stormfunc(readonly=True)
    def ruleFromText(text):
        return ruleFromText(text)

    @s_stormtypes.stormfunc(readonly=True)
    async def textFromRule(self, rule):
        rule = await s_stormtypes.toprim(rule)
        return s_common.reprauthrule(rule)

    @s_stormtypes.stormfunc(readonly=True)
    async def getPermDefs(self):
        return self.runt.snap.core.getPermDefs()

    @s_stormtypes.stormfunc(readonly=True)
    async def getPermDef(self, perm):
        perm = await s_stormtypes.toprim(perm)
        return self.runt.snap.core.getPermDef(perm)

@s_stormtypes.registry.registerType
class StormUserVarsDict(s_stormtypes.Prim):
    '''
    A Storm Primitive that maps the HiveDict interface to a user vars dictionary.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get the value for a user var.',
         'type': {'type': 'function', '_funcname': '_get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the var.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'The default value to return if not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'pop', 'desc': 'Remove a user var value.',
         'type': {'type': 'function', '_funcname': '_pop',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the var.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'The default value to return if not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'set', 'desc': 'Set a user var value.',
         'type': {'type': 'function', '_funcname': '_set',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the var to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value to store.', },
                  ),
                  'returns': {'type': ['null', 'prim'],
                              'desc': 'Old value of the var if it was previously set, or none.', }}},
        {'name': 'list', 'desc': 'List the vars and their values.',
         'type': {'type': 'function', '_funcname': '_list',
                  'returns': {'type': 'list', 'desc': 'A list of tuples containing var, value pairs.', }}},
    )
    _storm_typename = 'user:vars:dict'
    _ismutable = True

    def __init__(self, runt, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._get,
            'pop': self._pop,
            'set': self._set,
            'list': self._list,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _get(self, name, default=None):
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.getUserVarValu(self.valu, name, default=default)

    async def _pop(self, name, default=None):
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.popUserVarValu(self.valu, name, default=default)

    async def _set(self, name, valu):
        if not isinstance(name, str):
            mesg = 'The name of a variable must be a string.'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

        name = await s_stormtypes.tostr(name)
        oldv = await self.runt.snap.core.getUserVarValu(self.valu, name)

        valu = await s_stormtypes.toprim(valu)

        await self.runt.snap.core.setUserVarValu(self.valu, name, valu)
        return oldv

    @s_stormtypes.stormfunc(readonly=True)
    async def _list(self):
        valu = await self.value()
        return list(valu.items())

    async def iter(self):
        async for name, valu in self.runt.snap.core.iterUserVars(self.valu):
            yield name, valu
            await asyncio.sleep(0)

    async def value(self):
        varz = {}
        async for key, valu in self.runt.snap.core.iterUserVars(self.valu):
            varz[key] = valu
            await asyncio.sleep(0)

        return varz

@s_stormtypes.registry.registerType
class StormUserProfileDict(s_stormtypes.Prim):
    '''
    A Storm Primitive that maps the HiveDict interface to a user profile dictionary.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a user profile value.',
         'type': {'type': 'function', '_funcname': '_get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the user profile value.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'The default value to return if not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'pop', 'desc': 'Remove a user profile value.',
         'type': {'type': 'function', '_funcname': '_pop',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the user profile value.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'The default value to return if not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'set', 'desc': 'Set a user profile value.',
         'type': {'type': 'function', '_funcname': '_set',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the user profile value to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value to store.', },
                  ),
                  'returns': {'type': ['null', 'prim'],
                              'desc': 'Old value if it was previously set, or none.', }}},
        {'name': 'list', 'desc': 'List the user profile vars and their values.',
         'type': {'type': 'function', '_funcname': '_list',
                  'returns': {'type': 'list', 'desc': 'A list of tuples containing var, value pairs.', }}},
    )
    _storm_typename = 'user:profile:dict'
    _ismutable = True

    def __init__(self, runt, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._get,
            'pop': self._pop,
            'set': self._set,
            'list': self._list,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _get(self, name, default=None):
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.getUserProfInfo(self.valu, name, default=default)

    async def _pop(self, name, default=None):
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.popUserProfInfo(self.valu, name, default=default)

    async def _set(self, name, valu):
        if not isinstance(name, str):
            mesg = 'The name of a variable must be a string.'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

        name = await s_stormtypes.tostr(name)
        oldv = await self.runt.snap.core.getUserProfInfo(self.valu, name)

        valu = await s_stormtypes.toprim(valu)

        await self.runt.snap.core.setUserProfInfo(self.valu, name, valu)
        return oldv

    @s_stormtypes.stormfunc(readonly=True)
    async def _list(self):
        valu = await self.value()
        return list(valu.items())

    async def iter(self):
        async for name, valu in self.runt.snap.core.iterUserProfInfo(self.valu):
            yield name, valu
            await asyncio.sleep(0)

    async def value(self):
        return await self.runt.snap.core.getUserProfile(self.valu)

@s_stormtypes.registry.registerLib
class LibUser(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with data about the current user.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'Get the name of the current runtime user.',
         'type': {'type': 'function', '_funcname': '_libUserName',
                  'returns': {'type': 'str', 'desc': 'The username.', }}},
        {'name': 'allowed', 'desc': 'Check if the current user has a given permission.',
         'type': {'type': 'function', '_funcname': '_libUserAllowed',
                  'args': (
                      {'name': 'permname', 'type': 'str', 'desc': 'The permission string to check.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The authgate iden.', 'default': None, },
                      {'name': 'default', 'type': 'boolean', 'desc': 'The default value.', 'default': False, },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the user has the requested permission, false otherwise.', }}},
        {'name': 'vars', 'desc': "Get a dictionary representing the current user's persistent variables.",
         'type': 'auth:user:vars', },
        {'name': 'profile', 'desc': "Get a dictionary representing the current user's profile information.",
         'type': 'auth:user:profile', },
        {'name': 'iden', 'desc': 'The user GUID for the current storm user.', 'type': 'str'},
    )
    _storm_lib_path = ('user', )

    def getObjLocals(self):
        return {
            'name': self._libUserName,
            'iden': self.runt.user.iden,
            'allowed': self._libUserAllowed,
        }

    def addLibFuncs(self):
        super().addLibFuncs()
        self.locls.update({
            'vars': StormUserVarsDict(self.runt, self.runt.user.iden),
            'json': UserJson(self.runt, self.runt.user.iden),
            'profile': StormUserProfileDict(self.runt, self.runt.user.iden),
        })

    @s_stormtypes.stormfunc(readonly=True)
    async def _libUserName(self):
        return self.runt.user.name

    @s_stormtypes.stormfunc(readonly=True)
    async def _libUserAllowed(self, permname, gateiden=None, default=False):
        permname = await s_stormtypes.toprim(permname)
        gateiden = await s_stormtypes.tostr(gateiden, noneok=True)
        default = await s_stormtypes.tobool(default)

        perm = permname.split('.')
        return self.runt.user.allowed(perm, gateiden=gateiden, default=default)

@s_stormtypes.registry.registerLib
class LibUsers(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Auth Users in the Cortex.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a User to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methUsersAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the user.', },
                      {'name': 'passwd', 'type': 'str', 'desc': "The user's password.", 'default': None, },
                      {'name': 'email', 'type': 'str', 'desc': "The user's email address.", 'default': None, },
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden to use to create the user.', 'default': None, }
                  ),
                  'returns': {'type': 'auth:user',
                              'desc': 'The ``auth:user`` object for the new user.', }}},
        {'name': 'del', 'desc': 'Delete a User from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methUsersDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the user to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of Users in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methUsersList',
                  'returns': {'type': 'list', 'desc': 'A list of ``auth:user`` objects.', }}},
        {'name': 'get', 'desc': 'Get a specific User by iden.',
         'type': {'type': 'function', '_funcname': '_methUsersGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the user to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'auth:user'],
                              'desc': 'The ``auth:user`` object, or none if the user does not exist.', }}},
        {'name': 'byname', 'desc': 'Get a specific user by name.',
         'type': {'type': 'function', '_funcname': '_methUsersByName',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the user to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'auth:user'],
                              'desc': 'The ``auth:user`` object, or none if the user does not exist.', }}},
    )
    _storm_lib_path = ('auth', 'users')
    _storm_lib_perms = (
        {'perm': ('auth', 'role', 'set', 'name'), 'gate': 'cortex',
         'desc': 'Permits a user to change the name of a role.'},
        {'perm': ('auth', 'role', 'set', 'rules'), 'gate': 'cortex',
         'desc': 'Permits a user to modify rules of a role.'},

         {'perm': ('auth', 'self', 'set', 'email'), 'gate': 'cortex',
         'desc': 'Permits a user to change their own email address.',
         'default': True},
        {'perm': ('auth', 'self', 'set', 'name'), 'gate': 'cortex',
         'desc': 'Permits a user to change their own username.',
         'default': True},
        {'perm': ('auth', 'self', 'set', 'passwd'), 'gate': 'cortex',
         'desc': 'Permits a user to change their own password.',
         'default': True},
        {'perm': ('auth', 'self', 'set', 'apikey'), 'gate': 'cortex',
         'desc': 'Permits a user to manage their API keys.',
         'default': True},
        {'perm': ('auth', 'user', 'grant'), 'gate': 'cortex',
         'desc': 'Controls granting roles to a user.'},
        {'perm': ('auth', 'user', 'revoke'), 'gate': 'cortex',
         'desc': 'Controls revoking roles from a user.'},

        {'perm': ('auth', 'user', 'set', 'admin'), 'gate': 'cortex',
         'desc': 'Controls setting/removing a user\'s admin status.'},
        {'perm': ('auth', 'user', 'set', 'email'), 'gate': 'cortex',
         'desc': 'Controls changing a user\'s email address.'},
        {'perm': ('auth', 'user', 'set', 'locked'), 'gate': 'cortex',
         'desc': 'Controls locking/unlocking a user account.'},
        {'perm': ('auth', 'user', 'set', 'archived'), 'gate': 'cortex',
         'desc': 'Controls archiving/unarchiving a user account.'},
        {'perm': ('auth', 'user', 'set', 'passwd'), 'gate': 'cortex',
         'desc': 'Controls changing a user password.'},
        {'perm': ('auth', 'user', 'set', 'rules'), 'gate': 'cortex',
         'desc': 'Controls adding rules to a user.'},

        {'perm': ('auth', 'user', 'get', 'profile', '<name>'), 'gate': 'cortex',
         'desc': 'Permits a user to retrieve their profile information.',
         'ex': 'auth.user.get.profile.fullname'},
        {'perm': ('auth', 'user', 'pop', 'profile', '<name>'), 'gate': 'cortex',
         'desc': 'Permits a user to remove profile information.',
         'ex': 'auth.user.pop.profile.fullname'},
        {'perm': ('auth', 'user', 'set', 'profile', '<name>'), 'gate': 'cortex',
         'desc': 'Permits a user to set profile information.',
         'ex': 'auth.user.set.profile.fullname'},
        {'perm': ('auth', 'user', 'set', 'apikey'), 'gate': 'cortex',
         'desc': 'Permits a user to manage API keys for other users. USE WITH CAUTUON!'},
        {'perm': ('storm', 'lib', 'auth', 'users', 'add'), 'gate': 'cortex',
         'desc': 'Controls the ability to add a user to the system. USE WITH CAUTION!'},
        {'perm': ('storm', 'lib', 'auth', 'users', 'del'), 'gate': 'cortex',
         'desc': 'Controls the ability to remove a user from the system. USE WITH CAUTION!'},
    )

    def getObjLocals(self):
        return {
            'add': self._methUsersAdd,
            'del': self._methUsersDel,
            'list': self._methUsersList,
            'get': self._methUsersGet,
            'byname': self._methUsersByName,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methUsersList(self):
        return [User(self.runt, udef['iden']) for udef in await self.runt.snap.core.getUserDefs()]

    @s_stormtypes.stormfunc(readonly=True)
    async def _methUsersGet(self, iden):
        udef = await self.runt.snap.core.getUserDef(iden)
        if udef is not None:
            return User(self.runt, udef['iden'])

    @s_stormtypes.stormfunc(readonly=True)
    async def _methUsersByName(self, name):
        udef = await self.runt.snap.core.getUserDefByName(name)
        if udef is not None:
            return User(self.runt, udef['iden'])

    async def _methUsersAdd(self, name, passwd=None, email=None, iden=None):
        if not self.runt.allowed(('auth', 'user', 'add')):
            self.runt.confirm(('storm', 'lib', 'auth', 'users', 'add'))
        name = await s_stormtypes.tostr(name)
        iden = await s_stormtypes.tostr(iden, True)
        email = await s_stormtypes.tostr(email, True)
        passwd = await s_stormtypes.tostr(passwd, True)
        udef = await self.runt.snap.core.addUser(name, passwd=passwd, email=email, iden=iden,)
        return User(self.runt, udef['iden'])

    async def _methUsersDel(self, iden):
        if not self.runt.allowed(('auth', 'user', 'del')):
            self.runt.confirm(('storm', 'lib', 'auth', 'users', 'del'))
        await self.runt.snap.core.delUser(iden)

@s_stormtypes.registry.registerLib
class LibRoles(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Auth Roles in the Cortex.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Role to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methRolesAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the role.', },
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden to assign to the new role.', 'default': None},
                  ),
                  'returns': {'type': 'auth:role', 'desc': 'The new role object.', }}},
        {'name': 'del', 'desc': 'Delete a Role from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methRolesDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the role to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of Roles in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methRolesList',
                  'returns': {'type': 'list', 'desc': 'A list of ``auth:role`` objects.', }}},
        {'name': 'get', 'desc': 'Get a specific Role by iden.',
         'type': {'type': 'function', '_funcname': '_methRolesGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the role to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'auth:role'],
                              'desc': 'The ``auth:role`` object; or null if the role does not exist.', }}},
        {'name': 'byname', 'desc': 'Get a specific Role by name.',
         'type': {'type': 'function', '_funcname': '_methRolesByName',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the role to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'auth:role'],
                              'desc': 'The role by name, or null if it does not exist.', }}},
    )
    _storm_lib_path = ('auth', 'roles')
    _storm_lib_perms = (
        {'perm': ('storm', 'lib', 'auth', 'roles', 'add'), 'gate': 'cortex',
         'desc': 'Controls the ability to add a role to the system. USE WITH CAUTION!'},
        {'perm': ('storm', 'lib', 'auth', 'roles', 'del'), 'gate': 'cortex',
         'desc': 'Controls the ability to remove a role from the system. USE WITH CAUTION!'},
    )

    def getObjLocals(self):
        return {
            'add': self._methRolesAdd,
            'del': self._methRolesDel,
            'list': self._methRolesList,
            'get': self._methRolesGet,
            'byname': self._methRolesByName,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRolesList(self):
        return [Role(self.runt, rdef['iden']) for rdef in await self.runt.snap.core.getRoleDefs()]

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRolesGet(self, iden):
        rdef = await self.runt.snap.core.getRoleDef(iden)
        if rdef is not None:
            return Role(self.runt, rdef['iden'])

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRolesByName(self, name):
        rdef = await self.runt.snap.core.getRoleDefByName(name)
        if rdef is not None:
            return Role(self.runt, rdef['iden'])

    async def _methRolesAdd(self, name, iden=None):
        if not self.runt.allowed(('auth', 'role', 'add')):
            self.runt.confirm(('storm', 'lib', 'auth', 'roles', 'add'))
        iden = await s_stormtypes.tostr(iden, noneok=True)
        rdef = await self.runt.snap.core.addRole(name, iden=iden)
        return Role(self.runt, rdef['iden'])

    async def _methRolesDel(self, iden):
        if not self.runt.allowed(('auth', 'role', 'del')):
            self.runt.confirm(('storm', 'lib', 'auth', 'roles', 'del'))
        await self.runt.snap.core.delRole(iden)

@s_stormtypes.registry.registerLib
class LibGates(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Auth Gates in the Cortex.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a specific Gate by iden.',
         'type': {'type': 'function', '_funcname': '_methGatesGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the gate to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'auth:gate'],
                              'desc': 'The ``auth:gate`` if it exists, otherwise null.', }}},
        {'name': 'list', 'desc': 'Get a list of Gates in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGatesList',
                  'returns': {'type': 'list', 'desc': 'A list of ``auth:gate`` objects.', }}},
    )
    _storm_lib_path = ('auth', 'gates')

    def getObjLocals(self):
        return {
            'get': self._methGatesGet,
            'list': self._methGatesList,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGatesList(self):
        todo = s_common.todo('getAuthGates')
        gates = await self.runt.coreDynCall(todo)
        return [Gate(self.runt, g) for g in gates]

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGatesGet(self, iden):
        iden = await s_stormtypes.toprim(iden)
        todo = s_common.todo('getAuthGate', iden)
        gate = await self.runt.coreDynCall(todo)
        if gate:
            return Gate(self.runt, gate)

@s_stormtypes.registry.registerType
class Gate(s_stormtypes.Prim):
    '''
    Implements the Storm API for an AuthGate.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the AuthGate.', 'type': 'str', },
        {'name': 'type', 'desc': 'The type of the AuthGate.', 'type': 'str', },
        {'name': 'roles', 'desc': 'The role idens which are a member of the Authgate.', 'type': 'list', },
        {'name': 'users', 'desc': 'The user idens which are a member of the Authgate.', 'type': 'list', },
    )
    _storm_typename = 'auth:gate'
    _ismutable = False

    def __init__(self, runt, valu, path=None):

        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update({
            'iden': self.valu.get('iden'),
            'type': self.valu.get('type'),
            'roles': self.valu.get('roles', ()),
            'users': self.valu.get('users', ()),
        })

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))
