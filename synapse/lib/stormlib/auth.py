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
        ''',
        'cmdargs': (
            ('username', {'type': 'str', 'help': 'The name of the user.'}),
            ('--name', {'type': 'str', 'help': 'The new name for the user.'}),
            ('--email', {'type': 'str', 'help': 'The email address to set for the user.'}),
            ('--passwd', {'type': 'str', 'help': 'The new password for the user. This is best passed into the runtime as a variable.'}),
            ('--admin', {'type': 'bool', 'help': 'True to make the user and admin, false to remove their remove their admin status.'}),
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
                    $user.setAdmin($cmdopts.admin)
                    $lib.print(`User ({$cmdopts.username}) admin status set to {$cmdopts.admin=1}.`)
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
        'cmdargs': (),
        'storm': '''

            for $pdef in $lib.auth.getPermDefs() {
                $perm = $lib.str.join(".", $pdef.perm)

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
