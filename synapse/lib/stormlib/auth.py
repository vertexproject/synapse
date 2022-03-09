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
                $lib.print('User ({name}) added rule: {rule}', name=$cmdopts.name, rule=$cmdopts.rule)
            } else {
                $lib.warn('User ({name}) not found!', name=$cmdopts.name)
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
                $lib.print('Role ({name}) added rule: {rule}', name=$cmdopts.name, rule=$cmdopts.rule)
            } else {
                $lib.warn('Role ({name}) not found!', name=$cmdopts.name)
            }
        ''',
    },
    # TODO auth.user/set.set
    # TODO auth.user.grant/revoke
)
