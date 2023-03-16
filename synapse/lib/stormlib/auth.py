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
        'name': 'auth.user.addrule',
        'descr': '''
            Add a rule to a user.

            Examples:

                // add an allow rule to the user "visi" for permission "foo.bar.baz"
                auth.user.addrule visi foo.bar.baz

                // add a deny rule to the user "visi" for permission "foo.bar.baz"
                auth.user.addrule visi "!foo.bar.baz"
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the user.'}),
            ('rule', {'type': 'str', 'help': 'The rule string.'}),
            ('--gate', {'type': 'str', 'help': 'The auth gate id to grant permission on.', 'default': None}),
        ),
        'storm': '''
            $user = $lib.auth.users.byname($cmdopts.name)
            $rule = $lib.auth.ruleFromText($cmdopts.rule)
            if $user {
                $user.addRule($rule, gateiden=$cmdopts.gate)
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
        ''',
        'cmdargs': (
            ('name', {'type': 'str', 'help': 'The name of the role.'}),
            ('rule', {'type': 'str', 'help': 'The rule string.'}),
            ('--gate', {'type': 'str', 'help': 'The auth gate id to grant permission on.', 'default': None}),
        ),
        'storm': '''
            $role = $lib.auth.roles.byname($cmdopts.name)
            $rule = $lib.auth.ruleFromText($cmdopts.rule)
            if $role {
                $role.addRule($rule, gateiden=$cmdopts.gate)
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
            ('--gate', {'type': 'str', 'help': 'The auth gate id to grant permission on.', 'default': None}),
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

            $lib.print(`Granting role {$role.name} to user {$user.name}.`)
            $user.grant($role.iden)
        ''',
    },
    {
        'name': 'auth.user.revoke',
        'descr': '''
            Revoke a role from a user.

            Examples:
                // Revoke the role "ninjas" from the user "visi"
                auth.user.grant visi ninjas

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

            if (not $user.roles.has($role.iden)) {
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
            $lib.print(`  Admin: {$user.admin}`)
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
                $lib.print(`    {$gate.iden} - ({$gate.type})`)
                for ($indx, $rule) in $lib.iters.enum($user.getRules(gateiden=$gate.iden)) {
                    $ruletext = $lib.auth.textFromRule($rule)
                    $indxtext = $lib.cast(str, $indx).ljust(3)
                    $lib.print(`      [{$indxtext}] - {$ruletext}`)
                }
            }
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
)
