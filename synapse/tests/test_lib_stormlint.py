import warnings

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
import synapse.lib.stormlint as s_stormlint

import synapse.tests.utils as s_t_utils

class StormLintTest(s_t_utils.SynTest):

    def test_lib_stormlint_framework(self):

        self.isin('E001', s_stormlint.rules)
        e001 = s_stormlint.rules['E001']
        self.eq(e001.name, 'parse-failure')
        self.eq(e001.severity, 'high')
        self.true(e001.doc.startswith('The Storm code failed to parse.'))

        with self.raises(s_exc.BadArg):
            s_stormlint.rule('X999', 'bad', 'critical')

        with self.raises(s_exc.BadArg):
            s_stormlint.rule('E001', 'dup', 'high')

        seen = {}

        def libtrue(ctx):
            '''Test rule for $lib.true.'''
            for node in ctx.walk(s_ast.VarDeref):
                if ctx.isDeref(node, 'lib', 'true'):
                    ctx.report(node, 'Use true.')

        def nodeiden(ctx):
            for node in ctx.walk(s_ast.FuncCall):
                if ctx.callPath(node) == ('node', 'iden'):
                    ctx.report(node, 'Use $node.value().')

        def paths(ctx):
            seen['paths'] = [ctx.derefPath(n) for n in ctx.walk(s_ast.VarDeref)]
            seen['calls'] = [ctx.callPath(n) for n in ctx.walk(s_ast.FuncCall)]
            seen['notcall'] = ctx.callPath(ctx.query)
            seen['kinds'] = [type(n).__name__ for n in ctx.walk()]
            seen['root'] = ctx.parent(ctx.query)
            seen['setvar'] = [type(n).__name__ for n in ctx.walk(node=ctx.query.kids[0])] if ctx.query.kids else None

        def everything(ctx):
            # report the root, an unpositioned empty subquery and a Const with no AstInfo
            ctx.report(ctx.query, 'root')
            for node in ctx.walk(s_ast.SubQuery):
                ctx.report(node.kids[0], 'empty subquery')

            for node in ctx.walk(s_ast.VarValue):
                if node.kids[0].valu == 'y':
                    ctx.report(node.kids[0], 'token')

        try:
            s_stormlint.rule('T001', 'lib-true', 'high')(libtrue)
            s_stormlint.rule('T002', 'node-iden', 'medium')(nodeiden)
            s_stormlint.rule('U001', 'paths', 'low')(paths)
            s_stormlint.rule('V001', 'everything', 'low')(everything)
            s_stormlint.rule('W001', 'optional', 'low', default=False)(libtrue)

            # rules stay in ID order
            self.eq(list(s_stormlint.rules), sorted(s_stormlint.rules))
            self.eq(s_stormlint.rules['T001'].doc, 'Test rule for $lib.true.')
            self.eq(s_stormlint.rules['T002'].doc, '')
            self.eq(s_stormlint.rules['T001'].func, libtrue)
            self.true(s_stormlint.rules['T001'].default)
            self.false(s_stormlint.rules['W001'].default)
            self.false(s_stormlint.rules['S010'].default)
            self.false(s_stormlint.rules['S015'].default)

            # selection
            def idens(linter):
                return [r.iden for r in linter.rules]

            # rules which are off by default only run when a select entry names them
            defaults = [iden for iden, r in s_stormlint.rules.items() if r.default]
            self.eq(idens(s_stormlint.StormLinter()), defaults)
            self.notin('W001', defaults)
            self.notin('S010', defaults)
            self.notin('S015', defaults)
            self.eq(idens(s_stormlint.StormLinter(ignore=('T',))), [i for i in defaults if not i.startswith('T')])
            self.eq(idens(s_stormlint.StormLinter(enable=('W001',))), sorted(defaults + ['W001']))
            self.eq(idens(s_stormlint.StormLinter(select=('W',))), ['W001'])
            self.eq(idens(s_stormlint.StormLinter(select=('T', 'W'), ignore=('W001',))), ['T001', 'T002'])
            self.eq(s_stormlint.StormLinter(ignore=('V',)).lint('function f() { $m = $lib.import(foo) return($m) }'), [])
            self.eq([f.rule for f in s_stormlint.StormLinter(ignore=('V',), enable=('S015',)).lint(
                'function f() { $m = $lib.import(foo) return($m) }')], ['S015'])
            self.eq(idens(s_stormlint.StormLinter(select=('T',))), ['T001', 'T002'])
            self.eq(idens(s_stormlint.StormLinter(select=('T002', 'E001'))), ['E001', 'T002'])
            self.eq(idens(s_stormlint.StormLinter(select=('T',), enable=('U001',))), ['T001', 'T002', 'U001'])
            self.eq(idens(s_stormlint.StormLinter(select=('E001', 'T', 'U', 'V'), ignore=('T00', 'V'))),
                    ['E001', 'U001'])
            self.eq(idens(s_stormlint.StormLinter(select=('E',))), ['E001', 'E002', 'E003'])
            self.eq(idens(s_stormlint.StormLinter(select=())), [])

            for kwargs in ({'select': ('Z',)}, {'ignore': ('T003',)}, {'enable': ('',)}):
                with self.raises(s_exc.BadArg) as cm:
                    s_stormlint.StormLinter(**kwargs)
                self.isin('Unknown lint rule or prefix', cm.exception.get('mesg'))

            linter = s_stormlint.StormLinter(select=('T',))

            # findings are sorted by (line, column, rule) and positions include the leading $
            text = '$x = $lib.true\n$node.iden() $y = $lib.true'
            self.eq(linter.lint(text), (
                ('T001', 'high', 1, 6, 'Use true.'),
                ('T002', 'medium', 2, 1, 'Use $node.value().'),
                ('T001', 'high', 2, 19, 'Use true.'),
            ))
            self.true(isinstance(linter.lint(text)[0], s_stormlint.Finding))

            # empty and whitespace-only text is clean
            self.eq(linter.lint(''), [])
            self.eq(linter.lint('  \n\t\n'), [])

            # noqa
            self.eq(linter.lint('$x = $lib.true // noqa'), [])
            self.eq(linter.lint('$x = $lib.true // NOQA'), [])
            self.eq(linter.lint('$x = $lib.true //noqa:T001'), [])
            self.eq(linter.lint('$x = $lib.true // noqa: T'), [])
            self.eq(linter.lint('$x = $lib.true // noqa: X1, T001'), [])
            self.eq(linter.lint('$x = $lib.true // noqa: X1 T001'), [])
            self.eq(len(linter.lint('$x = $lib.true // noqa: T002')), 1)
            self.eq(len(linter.lint('$x = $lib.true // noqa: t001')), 1)
            self.eq(len(linter.lint('$x = $lib.true // noqawhat')), 1)
            self.eq(len(linter.lint('$x = $lib.true /* noqa */')), 1)
            self.eq(linter.lint('$x = $lib.true // noqa: T001\n$node.iden()'), (
                ('T002', 'medium', 2, 1, 'Use $node.value().'),
            ))
            self.eq(linter.lint('$x = (\n$lib.true // noqa: T001\n)'), [])

            # noqa lines are split on newlines only, matching the parser's line numbers
            self.eq(linter.lint('$x = "a b"\n$y = $lib.true // noqa\n$z = $lib.true\n'), (
                ('T001', 'high', 3, 6, 'Use true.'),
            ))
            self.eq(linter.lint('$x = 1\r\n$y = $lib.true // noqa\r\n$z = $lib.true\r\n'), (
                ('T001', 'high', 3, 6, 'Use true.'),
            ))

            # E001 is always reported, even when ignored or noqa'd, and stops the other rules
            for linter in (s_stormlint.StormLinter(), s_stormlint.StormLinter(ignore=('E',)),
                           s_stormlint.StormLinter(select=())):
                finds = linter.lint('$x = $lib.true\ninet:fqdn=( // noqa')
                self.len(1, finds)
                self.eq(finds[0][:4], ('E001', 'high', 2, 11))
                self.isin('Unexpected token', finds[0].mesg)

            # escape errors carry no position
            finds = s_stormlint.StormLinter().lint('$x = "\\u12"')
            self.len(1, finds)
            self.eq(finds[0][:4], ('E001', 'high', 1, 1))
            self.isin('Invalid character in string', finds[0].mesg)

            # invalid python escapes parse without emitting a SyntaxWarning
            with warnings.catch_warnings(record=True) as warns:
                warnings.simplefilter('always')
                self.eq(s_stormlint.StormLinter(select=('E001',)).lint('$x = "\\q"'), [])
            self.eq([w for w in warns if issubclass(w.category, SyntaxWarning)], [])

            # helpers
            linter = s_stormlint.StormLinter(select=('U',))
            self.eq(linter.lint('$lib.str.format(a) $x.$y $f() $lib.foo.$z.bar $node.iden() $lib.$q() $x = ({}).foo'), [])
            self.eq(seen['paths'], [
                ('lib', 'str', 'format'),
                ('lib', 'str'),
                None,
                None,
                None,
                ('lib', 'foo'),
                ('node', 'iden'),
                None,
                None,
            ])
            self.none(seen['notcall'])
            self.eq(seen['calls'], [('lib', 'str', 'format'), ('f',), ('node', 'iden'), None])
            self.eq(seen['kinds'][:2], ['Query', 'VarEvalOper'])
            self.none(seen['root'])
            self.eq(seen['setvar'], ['VarEvalOper', 'FuncCall', 'VarDeref', 'VarDeref', 'VarValue', 'Const',
                                     'Const', 'Const', 'CallArgs', 'Const', 'CallKwargs'])

            linter.lint('')
            self.eq(seen['paths'], [])
            self.none(seen['setvar'])

            # positions fall back to the nearest positioned ancestor, then 1:1
            linter = s_stormlint.StormLinter(select=('V',))
            self.eq(linter.lint(''), (('V001', 'low', 1, 1, 'root'),))
            self.eq(linter.lint('[ inet:fqdn=a ] { }\n$x = $lib.$y'), (
                ('V001', 'low', 1, 1, 'root'),
                ('V001', 'low', 1, 17, 'empty subquery'),
                ('V001', 'low', 2, 11, 'token'),
            ))

        finally:
            for iden in ('T001', 'T002', 'U001', 'V001', 'W001'):
                s_stormlint.rules.pop(iden, None)

        for iden in ('T001', 'T002', 'U001', 'V001', 'W001'):
            self.notin(iden, s_stormlint.rules)

    def test_lib_stormlint_rules(self):

        def lint(iden, text):
            return [f[2:] for f in s_stormlint.StormLinter(select=(iden,)).lint(text)]

        for iden in ('E002', 'E003', 'R001', 'R002', 'R003', 'R004', 'R005', 'P001', 'P002', 'S001', 'S002', 'S003',
                     'S004', 'S005', 'S006', 'S008', 'S010', 'S011', 'S012', 'S014', 'S015'):
            self.true(s_stormlint.rules[iden].doc)

        # E002 invalid escapes in double-quoted and backtick strings
        self.eq(lint('E002', r"""
            $a = "ok \\ \" \' \n \t \r \a \b \f \v \0 \17 \777 \x41 \u0041 \U00000041 \N{BULLET} \\q"
            $b = 'single \q is raw'
            $c = `ok \` \{ \n {$a} \x41 {"ok \n"} {'raw \q'}`
            $d = ${ $x = 'raw \q' }
            $lib.print('''triple \q''')
            $lib.$e
        """), [])

        self.eq(lint('E002', '$a = "a\\qb\\\\q\\d"\n$b = `x\\w{$a}\\` \\p{"\\j"}{\'\\k\'}"\\m`'), (
            (1, 8, "Invalid escape sequence '\\q' in string."),
            (1, 14, "Invalid escape sequence '\\d' in string."),
            (2, 8, "Invalid escape sequence '\\w' in string."),
            (2, 17, "Invalid escape sequence '\\p' in string."),
            (2, 21, "Invalid escape sequence '\\j' in string."),
            (2, 32, "Invalid escape sequence '\\m' in string."),
        ))

        self.eq(lint('E002', '[ inet:fqdn="a\\q" ]\n$x = ({"\\z": 1})\n$y = ${ $z = "\\y" }\nfoo.bar "\\c" --x "\\e"'), (
            (1, 15, "Invalid escape sequence '\\q' in string."),
            (2, 9, "Invalid escape sequence '\\z' in string."),
            (3, 15, "Invalid escape sequence '\\y' in string."),
            (4, 10, "Invalid escape sequence '\\c' in string."),
            (4, 19, "Invalid escape sequence '\\e' in string."),
        ))

        # a multi-line string reports the line of the escape
        self.eq(lint('E002', '$x = `a\nb\\qc`'), ((2, 2, "Invalid escape sequence '\\q' in string."),))

        # E003 duplicate functions in the same scope
        self.eq(lint('E003', '''
            function f() {}
            function g() { function f() {} function h() {} }
            function h() {}
            if $x { function f() {} }
        '''), [])

        self.eq(lint('E003', 'function f() {}\nfunction g() { function h() {} function h(x) {} }\n'
                             '$x = 10\nfunction f(y) { return($y) }\nfunction f() {}'), (
            (2, 32, 'Function h is already defined on line 2.'),
            (4, 1, 'Function f is already defined on line 1.'),
            (5, 1, 'Function f is already defined on line 1.'),
        ))

        # R001 $lib.true / $lib.false / $lib.null
        self.eq(lint('R001', '$x = (true) $y = (null) $lib.str.concat(a, b) $lib.trueish $lib $x.true $lib.$y'), [])
        self.eq(lint('R001', 'if ($lib.true) { $lib.foo(check=$lib.false) }\n$x = $lib.null.foo'), (
            (1, 5, '$lib.true was removed, use (true).'),
            (1, 33, '$lib.false was removed, use (false).'),
            (2, 6, '$lib.null was removed, use (null).'),
        ))

        # R002 gtors called as methods
        self.eq(lint('R002', '$x = $node.value $y = $node.form $z = $node.repr() $v = $n.value() $node.props.value()\n'
                             '$a = $node.ndef $b = $lib.version.synapse $c = $lib.version.commit $lib.version.matches($b, x)'), [])
        self.eq(lint('R002', '$x = $node.value()\n$lib.print($node.form())\n$y = $node.ndef()\n'
                             '$z = $lib.version.synapse() $q = $lib.version.commit()'), (
            (1, 6, '$node.value is not callable, drop the parentheses.'),
            (2, 12, '$node.form is not callable, drop the parentheses.'),
            (3, 6, '$node.ndef is not callable, drop the parentheses.'),
            (4, 6, '$lib.version.synapse is not callable, drop the parentheses.'),
            (4, 34, '$lib.version.commit is not callable, drop the parentheses.'),
        ))

        # R003 $node.iden
        self.eq(lint('R003', '$x = $node.value $y = $n.iden() $z = $node.ndef $lib.print($iden)'), [])
        self.eq(lint('R003', '$x = $node.iden()\n$y = $node.iden'), (
            (1, 6, '$node.iden was removed.'),
            (2, 6, '$node.iden was removed.'),
        ))

        # R004 bare true / false / null used as a value
        self.eq(lint('R004', '''
            $a = (true) $b = "false" $c = 'null' $d = truex
            $e.f = (false) ($g, $h) = $lib.foo(('null'), x=(null), y="true")
            inet:fqdn=true | foo.bar true --x null
            if (true) { emit false }
            return((null))
            function f(x=(null), y='null', z as int=(true)) {}
        '''), [])

        self.eq(lint('R004', '$a = true\n$b.c = false $b.$c = null ($d, $e) = true\n'
                             '$lib.foo(true, x, y=null)\nreturn(false)'), (
            (1, 6, 'Bare true is a string, use (true) or quote it.'),
            (2, 8, 'Bare false is a string, use (false) or quote it.'),
            (2, 22, 'Bare null is a string, use (null) or quote it.'),
            (2, 38, 'Bare true is a string, use (true) or quote it.'),
            (3, 10, 'Bare true is a string, use (true) or quote it.'),
            (3, 21, 'Bare null is a string, use (null) or quote it.'),
            (4, 8, 'Bare false is a string, use (false) or quote it.'),
        ))

        self.eq(lint('R004', 'function f(x=null) {}\nfunction g(y as str, x as int=true) {}'), (
            (1, 14, 'Bare null is a string, use (null) or quote it.'),
            (2, 31, 'Bare true is a string, use (true) or quote it.'),
        ))

        # R005 removed $lib APIs
        self.eq(lint('R005', '''
            $s = ('.').join($parts) $t = `hi {$n}` $u = $lib.auth.users.get() $v = $u.vars.foo
            $lib.task.kill($i) $lib.axon.put($buf) $lib.bytes.fromints($ints) $lib.infosec.cvss.vectToScore($v)
            $lib.cron.mod($i, ({"enabled": false})) $lib.utils.type($x) $lib.gen._ouOrgByName(a) $lib.gen
            $v = $lib.vars.foo $lib.vars.get = 1 $w = $lib.globals.set $lib.globals.foo = $lib.undef
            $e = $lib.env.SYN_STORM_ENV_FOO $x.str.format() $lib.$y.get() $lib.vars.$z()
            $u.vars.foo = 1 $u.vars.get $u.vars.del(x) $vars.get(x) $f() $x.$y.get() $x.vars.$z()
        '''), [])

        self.eq(lint('R005', '$a = $lib.str.format("{x}", x=1) $b = $lib.str.join(",", $c) $d = $lib.str.concat(a, b)\n'
                             '$e = $lib.str.foo $f = $lib.text(x) $g = $lib.user.name $lib.ps.kill($i)\n'
                             '$lib.notifications.list() $lib.projects.add(p) $h = $lib.inet.whois.guid(({}), x)\n'
                             '$lib.gen.orgByName(acme) $lib.bytes.put($b) $lib.bytes.has($s) $lib.bytes.size($s)\n'
                             '$lib.bytes.hashset($s) $lib.bytes.upload($g) $lib.infosec.cvss.calculate($n)\n'
                             '$lib.infosec.cvss.calculateFromProps($n) $lib.infosec.cvss.vectToProps($v)\n'
                             '$lib.infosec.cvss.saveVectToNode($n, $v) $lib.cell.hotFixesApply() $lib.cell.hotFixesCheck()\n'
                             '$b = $lib.utils.buid($x) $lib.cron.move($i, $v) $lib.cron.enable($i) $lib.cron.disable($i)\n'
                             '$lib.trigger.enable($i) $lib.trigger.disable($i)'), (
            (1, 6, '$lib.str.format was removed, use a backtick format string.'),
            (1, 39, '$lib.str.join was removed, use (sep).join(items).'),
            (1, 67, '$lib.str.concat was removed, use a backtick format string.'),
            (2, 6, '$lib.str was removed.'),
            (2, 24, '$lib.text was removed, append to a list and join it, or use a backtick format string.'),
            (2, 42, '$lib.user was removed, use $lib.auth.users.get().'),
            (2, 57, '$lib.ps was removed, use $lib.task.'),
            (3, 1, '$lib.notifications was removed.'),
            (3, 27, '$lib.projects was removed.'),
            (3, 53, '$lib.inet.whois was removed, use a guid constructor.'),
            (4, 1, '$lib.gen.orgByName was removed, use a gen.* command or a guid constructor.'),
            (4, 26, '$lib.bytes.put was removed, use $lib.axon.put().'),
            (4, 45, '$lib.bytes.has was removed, use $lib.axon.has().'),
            (4, 64, '$lib.bytes.size was removed, use $lib.axon.size().'),
            (5, 1, '$lib.bytes.hashset was removed, use $lib.axon.hashset().'),
            (5, 24, '$lib.bytes.upload was removed, use $lib.axon.upload().'),
            (5, 46, '$lib.infosec.cvss.calculate was removed, use $lib.infosec.cvss.vectToScore() and set the props.'),
            (6, 1, '$lib.infosec.cvss.calculateFromProps was removed, use $lib.infosec.cvss.vectToScore() and set the props.'),
            (6, 42, '$lib.infosec.cvss.vectToProps was removed, use $lib.infosec.cvss.vectToScore() and set the props.'),
            (7, 1, '$lib.infosec.cvss.saveVectToNode was removed, use $lib.infosec.cvss.vectToScore() and set the props.'),
            (7, 42, '$lib.cell.hotFixesApply was removed.'),
            (7, 68, '$lib.cell.hotFixesCheck was removed.'),
            (8, 6, '$lib.utils.buid was removed.'),
            (8, 26, '$lib.cron.move was removed, use $lib.cron.mod() with a view edit.'),
            (8, 49, '$lib.cron.enable was removed, use $lib.cron.mod() with an enabled edit.'),
            (8, 70, '$lib.cron.disable was removed, use $lib.cron.mod() with an enabled edit.'),
            (9, 1, '$lib.trigger.enable was removed, use $lib.trigger.mod() with an enabled edit.'),
            (9, 25, '$lib.trigger.disable was removed, use $lib.trigger.mod() with an enabled edit.'),
        ))

        self.eq(lint('R005', '$a = $lib.vars.get(x) $lib.vars.set(x, 1) $lib.vars.del(x) $lib.vars.list() $lib.vars.type($x)\n'
                             '$b = $lib.globals.get(x) $lib.globals.set(x, 1) $lib.globals.pop(x) $lib.globals.list()\n'
                             '$c = $lib.env.get(SYN_STORM_ENV_FOO) $d = $lib.auth.users.get().vars.get(x)\n'
                             '$user.vars.set(x, 1) $user.vars.pop(x) for $v in $user.vars.list() { }\n'
                             '$lib.user.vars.get(x)'), (
            (1, 6, '$lib.vars.get was removed, use $lib.vars.<name>.'),
            (1, 23, '$lib.vars.set was removed, assign $lib.vars.<name>.'),
            (1, 43, '$lib.vars.del was removed, assign $lib.undef to $lib.vars.<name>.'),
            (1, 60, '$lib.vars.list was removed, iterate $lib.vars with a for loop.'),
            (1, 77, '$lib.vars.type was removed, use $lib.utils.type().'),
            (2, 6, '$lib.globals.get was removed, use $lib.globals.<name>.'),
            (2, 26, '$lib.globals.set was removed, assign $lib.globals.<name>.'),
            (2, 49, '$lib.globals.pop was removed, assign $lib.undef to $lib.globals.<name>.'),
            (2, 69, '$lib.globals.list was removed, iterate $lib.globals with a for loop.'),
            (3, 6, '$lib.env.get was removed, use $lib.env.<NAME>.'),
            (3, 43, 'vars.get() was removed, vars are dict-like: read vars.<name>.'),
            (4, 1, 'vars.set() was removed, vars are dict-like: assign vars.<name>.'),
            (4, 22, 'vars.pop() was removed, vars are dict-like: assign $lib.undef to vars.<name>.'),
            (4, 50, 'vars.list() was removed, vars are dict-like: iterate vars with a for loop.'),
            (5, 1, '$lib.user was removed, use $lib.auth.users.get().'),
            (5, 1, 'vars.get() was removed, vars are dict-like: read vars.<name>.'),
        ))

        # P001 spin
        mesg = 'Avoid spin, use an exec { ... } block or isolate the query in a function.'
        self.eq(lint('P001', 'inet:fqdn | uniq | spinner | $lib.spin()\nexec { inet:fqdn }'), [])
        self.eq(lint('P001', 'inet:fqdn | spin\n{ inet:ipv4 | spin }'), (
            (1, 13, mesg),
            (2, 15, mesg),
        ))

        # P002 spin | return(...)
        mesg = ('Replace spin | return(...) with return(...) when only one node can flow, '
                'fini { return(...) } when more than one can, or run the query which '
                'yields the nodes in an exec { ... } block.')
        self.eq(lint('P002', 'inet:fqdn | spin | $x = 1 return($x)\nreturn($x) | spin\n{ spin } return()\n'
                             'exec { inet:fqdn } return()'), [])
        self.eq(lint('P002', 'inet:fqdn | spin | return($x)\nfunction f() { $x | spin | return() }'), (
            (1, 13, mesg),
            (2, 21, mesg),
        ))

        # spin | return() is also a P001 finding
        self.eq([f.rule for f in s_stormlint.StormLinter(select=('P',)).lint('spin | return()')], ['P001', 'P002'])

        # S001 $lib.guid() as a guid node-add value
        self.eq(lint('S001', '[ test:guid=(a, $b) test:guid=* :id=$lib.guid() test:guid=$lib.hex(a) test:guid=$x ]'), [])
        self.eq(lint('S001', '[ test:guid=$lib.guid(a, $b) ]\n[ *$form?=$lib.guid() test:guid=$lib.guid(valu=$x) ]'), (
            (1, 13, 'Use a list seed (test:guid=(...)) instead of $lib.guid(), after verifying the guid is unchanged.'),
            (2, 11, 'Use *$form=* instead of $lib.guid().'),
            (2, 33, 'Use a list seed (test:guid=(...)) instead of $lib.guid(), after verifying the guid is unchanged.'),
        ))

        # S002 unnecessary parens; required literal, dict/list value and precedence parens are kept
        self.eq(lint('S002', '''
            $a = (true) $b = (null) $c = (10) $d = ("x") $e = ([]) $f = ({"a": $x, "b": [1, true]})
            $lib.foo(({"a": 1}), ([1]), (1), x=(true), y=({}))
            $g = (($a + $b) * 2) $h = ($a and ($b or $c)) $i = (not ($a = 1)) $j = (-(1))
            $k = ($f()) $x.($y) = 1 $m = $y.$($z) [ :p=$($y) :q=$($y + 1) ] +$($y)
            if ($x) { } return(($a + 1))
        '''), [])

        mesg = 'Unnecessary parens inside an expression which is already open.'
        self.eq(lint('S002', '$conf = ({"host": ($host), "args": (["a"]), "ok": (true)})\n'
                             'if (($x = 1)) {} elif ($ok and (true)) {}\n'
                             '$n = ($y + (1)) $x = ($y) $lib.print(($x))\n'
                             '$a = (not ($b)) $c = $((1)) $d = ($e in ($f.g))\n'
                             '$lib.foo(x=($y.z)) $x.y = ($z) return(($q))'), (
            (1, 19, mesg),
            (1, 36, mesg),
            (1, 51, mesg),
            (2, 5, mesg),
            (2, 32, mesg),
            (3, 12, mesg),
            (3, 22, 'Unnecessary parens around a variable, use $y.'),
            (3, 38, 'Unnecessary parens around a variable, use $x.'),
            (4, 11, mesg),
            (4, 24, mesg),
            (4, 41, mesg),
            (5, 12, 'Unnecessary parens around a variable, use $y.z.'),
            (5, 27, 'Unnecessary parens around a variable, use $z.'),
            (5, 39, 'Unnecessary parens around a variable, use $q.'),
        ))

        # S003 edge edits with a subquery which only yields a variable
        self.eq(lint('S003', '[ +(refs)> $v <(refs)+ { inet:fqdn } -(refs)> { yield $v yield $w } +(refs)> { yield $x.y } ]'), [])
        self.eq(lint('S003', '[ +(refs)> { yield $v }\n<($verb)+ { yield $v } -(refs)> {yield $x} <(refs)- { yield $v } ]'), (
            (1, 3, 'Use +(refs)> $v instead of a subquery which only yields it.'),
            (2, 1, 'Use <($verb)+ $v instead of a subquery which only yields it.'),
            (2, 24, 'Use -(refs)> $x instead of a subquery which only yields it.'),
            (2, 44, 'Use <(refs)- $v instead of a subquery which only yields it.'),
        ))

        # S004 return((null)) / return($lib.null)
        self.eq(lint('S004', 'return() return(null) return((1)) return(($x)) return($lib.true) return($x.null)'), [])
        self.eq(lint('S004', 'return((null))\nfunction f() { return($lib.null) }'), (
            (1, 1, 'Use return() to return (null).'),
            (2, 16, 'Use return() to return (null).'),
        ))

        # S005 $lib.list() / $lib.dict()
        self.eq(lint('S005', '$x = ([]) $y = ({}) $z = $lib.lists() $lib.dict.foo() $x.list()'), [])
        self.eq(lint('S005', '$x = $lib.list(1, 2)\n$y = $lib.dict(a=1)'), (
            (1, 6, 'Use a list literal such as ([]) instead of $lib.list().'),
            (2, 6, 'Use a dict literal such as ({}) instead of $lib.dict().'),
        ))

        # S006 $lib.print() / $lib.warn() with kwargs
        self.eq(lint('S006', '$lib.print(`{$x}`) $lib.warn(hi) $lib.log.info(hi, extra=({})) $lib.fire(x, y=1)'), [])
        self.eq(lint('S006', '$lib.print("{x}", x=$x)\n$lib.warn("{y}", y=1)'), (
            (1, 1, 'Use a backtick format string instead of $lib.print() kwargs.'),
            (2, 1, 'Use a backtick format string instead of $lib.warn() kwargs.'),
        ))

        # S008 an if guarding only a for loop over the tested variable
        self.eq(lint('S008', 'if ($list) { for $x in $other { } } if $v { for $x in $v { } $lib.print(hi) }\n'
                             'if $v { for $x in $v { } } else { } if ($v = 1) { for $x in $v { } }\n'
                             'if $v.x { for $x in $v.x { } } if $v { $lib.print($v) }'), [])
        self.eq(lint('S008', 'if ($list) { for $x in $list { } }\nif $items {\n    for ($k, $v) in $items { $lib.print($k) }\n}'), (
            (1, 1, 'Drop the if guard, a for loop over an empty $list iterates zero times, if no node is in the pipeline.'),
            (2, 1, 'Drop the if guard, a for loop over an empty $items iterates zero times, if no node is in the pipeline.'),
        ))

        # S010 an if guarding only a prop set from the tested variable
        self.eq(lint('S010', '''
            if $v { [ :p=$w ] } if $v { [ :p=$v ] } else { } if ($v = 1) { [ :p=$v ] }
            if $v { [ :p=$v ] $lib.print(x) } if $v { [ :p+=$v ] } if $v.x { [ :p=$v.x ] }
        '''), [])
        self.eq(lint('S010', 'if $v { [ :p=$v ] }\nif ($v) {\n    [ :p ?= $v ]\n}'), (
            (1, 1, 'Use [ :p?=$v ] instead of an if statement, if $v can not be a false non-null value or fail to norm.'),
            (2, 1, 'Use [ :p?=$v ] instead of an if statement, if $v can not be a false non-null value or fail to norm.'),
        ))

        # S011 a prop set from a subquery lifting a form by primary value
        self.eq(lint('S011', '''
            [ :p=$g :q={ inet:fqdn:zone=$g } :r={ inet:fqdn=$g | limit 1 } :s={ inet:fqdn^=$g } :t={ *$f=$g } ]
            [ :u={ newp:form=$g } :v={ inet:fqdn } :w={ } ]
        '''), [])
        self.eq(lint('S011', '[ :p={ inet:fqdn=$g } ]\n[ :q?={inet:fqdn=$h.x} ]'), (
            (1, 6, 'Use :p=$g as inet:fqdn (or :p=$g when the property is inet:fqdn typed) '
                   'instead of a subquery which lifts by value.'),
            (2, 7, 'Use :q?=$h.x as inet:fqdn (or :q?=$h.x when the property is inet:fqdn typed) '
                   'instead of a subquery which lifts by value.'),
        ))

        # S012 a form lift followed by a filter on one of its props
        self.eq(lint('S012', '''
            inet:fqdn:zone=x | inet:fqdn +:zone=x
            { inet:fqdn -:zone=x } { inet:fqdn +(:zone=x or :zone=y) } { inet:fqdn +:zone!=x }
            { inet:fqdn +:zone={ $x } } { inet:fqdn +:zone } { inet:fqdn +:newp=x } { inet:fqdn +:zone.newp=x }
            { meta:taxonomy +:title=x } { inet:* +:zone=x } { inet:fqdn } { inet:fqdn#foo +:zone=x }
            { inet:fqdn +:zone=:domain } { inet:fqdn +:zone=$node.value() } { inet:fqdn +:zone=#foo }
            { inet:fqdn +:zone=#foo:score } { inet:fqdn +:zone=$path.vars.x } { inet:fqdn +:zone=.created }
        '''), [])
        self.eq(lint('S012', 'inet:fqdn +:zone=foo { inet:fqdn +(:zone^=$x) } {\n'
                             '  inet:fqdn +:zone*in=(a, b) | count }\n{ inet:fqdn +:zone*range=(a, b) +:zone=c }'), (
            (1, 1, 'Lift by inet:fqdn:zone=foo instead of filtering.'),
            (1, 24, 'Lift by inet:fqdn:zone^=$x instead of filtering.'),
            (2, 3, 'Lift by inet:fqdn:zone*in=(a, b) instead of filtering.'),
            (3, 3, 'Lift by inet:fqdn:zone*range=(a, b) instead of filtering.'),
        ))

        # S014 $lib.cast() in a try block
        self.eq(lint('S014', 'try { $lib.trycast(int, $x) function f() { $lib.cast(int, $x) } } '
                             'catch * as e { $lib.cast(int, $x) }\n$lib.cast(int, $x)'), [])
        self.eq(lint('S014', 'try {\n    $x = $lib.cast(int, $y)\n    if $z { [ :p=$lib.cast(time, $z) ] }\n'
                             '} catch BadTypeValu as e { }'), (
            (2, 10, 'Use $lib.trycast() instead of $lib.cast() in a try block.'),
            (3, 18, 'Use $lib.trycast() instead of $lib.cast() in a try block.'),
        ))

        # S015 a function returning a module from $lib.import()
        self.eq(lint('S015', '''
            $m = $lib.import(foo) $__n = $lib.import(bar) $o = $lib.foo(baz)
            function f(m) { return($m) }
            function g() { $m = (1) return(($m)) }
            function h() { for $m in $y { } ($__n, $z) = $q return($__n) }
            function i() { return() } function j() { return($o) }
            function l() { function inner() { $x = $lib.import(foo) } return($x) }
            return($m)
        '''), [])

        mesg = 'Never return a module from $lib.import(), in a privsep module it inherits root privileges even when bound as $__name.'
        self.eq(lint('S015', '$m = $lib.import(foo)\nfunction f() { return($m) }\n'
                             'function g() {\n    $x = $lib.import(bar)\n    return(($x))\n}\n'
                             'function h() { return($lib.import(foo)) }'), (
            (2, 16, mesg),
            (5, 5, mesg),
            (7, 16, mesg),
        ))
