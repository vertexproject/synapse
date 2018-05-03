import json
import pprint
import shutil

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.cores.common as s_cores_commmon

import synapse.lib.cli as s_cli
import synapse.lib.auth as s_auth
import synapse.lib.tufo as s_tufo

class AuthCmd(s_cli.Cmd):
    '''
    Helper for managing AuthMixin instances.

    Examples:
        # Get users
        auth
        # Get roles
        auth --type role
        # Get a specific user
        auth --name root@localhost
        # Make a user
        auth --act add --name user@localhost
        # Add a rule to a user
        auth --act add --name user@localhost --rule node:tag:add --tag *
        # Make a role
        auth --act add --name creators --type role
        # Add a rule to a role
        auth --act add --name creators --type role --rule node:add --form strform
        # Get a specific role details
        auth --type role --name creators
        # Grant a user a role
        auth --act add --name user@localhost --role creators
        # Grant a user admin
        auth --act add --name user@localhost --admin
        # Remove admin from a user
        auth --act del --name user@localhost --admin
        # Remove a role from a user
        auth --act del --name user@localhost --role creators
        # Remove a rule from a role
        auth --act del --name creators --type role --rule node:add --form strform
        # Remove a rule from a user
        auth --act del --name user@localhost --rule node:tag:add --tag *
        # Delete a role
        auth --act del --name creators --type role
        # Delete a user
        auth --act del --name user@localhost
    '''
    _cmd_name = 'auth'
    _cmd_syntax = (
        ('--act', {'type': 'enum',
                   'defval': 'get',
                   'enum:vals': ('add', 'del', 'get')}),
        ('--type', {'type': 'enum',
                    'defval': 'user',
                    'enum:vals': ('user', 'role')}),
        ('--name', {'type': 'valu'}),
        ('--rule', {'type': 'valu'}),
        ('--form', {'type': 'valu'}),
        ('--prop', {'type': 'valu'}),
        ('--tag', {'type': 'valu'}),
        ('--role', {'type': 'valu'}),
        ('--admin', {}),
        ('--json', {})
    )
    getmap = {'user': 'users',
              'role': 'roles'}
    typmap = {'user': 'user',
              'role': 'role'}
    modmap = {'user': 'urule',
               'role': 'rrule'}

    def __init__(self, cli, **opts):
        s_cli.Cmd.__init__(self, cli, **opts)
        s = '\n    '.join([str(stx) for stx in self._cmd_syntax])
        self.__doc__ = '\n    '.join([self.__doc__, 'Command Syntax:\n', s])

    def formRulefo(self, opts):
        rtype = opts.pop('rule', None)
        if not rtype:
            return None
        form = opts.get('form')
        prop = opts.get('prop')
        tag = opts.get('tag')
        if tag:
            if form or prop:
                raise s_exc.BadSyntaxError(mesg='Cannot form rulefo with tag and (form OR prop)')
            else:
                return s_tufo.tufo(rtype, tag=tag)
        if form and prop:
            return s_tufo.tufo(rtype, form=form, prop=prop)
        if form and not prop:
            return s_tufo.tufo(rtype, form=form)
        raise s_exc.BadSyntaxError(mesg='Unable to form rulefo',
                                   prop=prop, form=form, tag=tag, rule=rtype)

    def getMsg(self, stub, name, typ, opts):
        if not name:
            raise s_exc.BadSyntaxError(mesg='Action requires a name')
        args = {typ: name}
        admin = opts.pop('admin', None)
        if admin and typ == 'user':
            msg = s_tufo.tufo(':'.join([stub, 'admin']),
                              **args)
            return msg
        role = opts.pop('role', None)
        if role and typ == 'user':
            args['role'] = role
            msg = s_tufo.tufo(':'.join([stub, 'urole']),
                              **args)
            return msg
        rulefo = self.formRulefo(opts)
        if rulefo is None:
            msg = s_tufo.tufo(':'.join([stub, typ]),
                              **args)
            return msg
        mod = self.modmap.get(typ)
        if not mod:  # pragma: no cover
            raise s_exc.BadSyntaxError(mesg='Unknown type encountered',
                                       type=typ)
        args['rule'] = rulefo
        msg = s_tufo.tufo(':'.join([stub, mod]),
                          **args)
        return msg

    def runCmdOpts(self, opts):
        core = self.getCmdItem()  # type: s_auth.AuthMixin

        act = opts.pop('act')
        typ = opts.pop('type')
        name = opts.pop('name', None)
        astub = 'auth:add'
        dstub = 'auth:del'

        # Form our mesg
        if act == 'get':
            if name:
                mesg = s_tufo.tufo('auth:req:%s' % typ,
                                   **{self.typmap.get(typ): name})
            else:
                mesg = ('auth:get:%s' % self.getmap.get(typ),
                        {})
        elif act == 'add':
            mesg = self.getMsg(astub, name, typ, opts)
        elif act == 'del':
            mesg = self.getMsg(dstub, name, typ, opts)
        else:  # pragma: no cover
            raise s_exc.BadSyntaxError(mesg='Unknown action provided',
                                       act=act)

        # Execute remote call
        isok, retn = core.authReact(mesg)
        retn = s_common.reqok(isok, retn)

        # Format output
        if opts.get('json'):
            outp = json.dumps(retn, indent=2, sort_keys=True)
        else:
            width, _ = shutil.get_terminal_size((120, 24))
            if width == 0:
                # In CI we may not have a tty available.
                width = 120
            outp = pprint.pformat(retn, width=width)
        self.printf(outp)
        return retn
