import sys
import logging
import functools
import traceback
import synapse.exc as s_exc
import synapse.common as s_common

import synapse.glob as s_glob
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

desc = '''
Manage permissions of users, roles, and objects in a remote cell.
'''
outp = None

min_authgate_vers = (0, 1, 33)
reqver = '>=0.2.0,<3.0.0'

denyallow = ['deny', 'allow']
def reprrule(rule):
    head = denyallow[rule[0]]
    text = '.'.join(rule[1])
    return f'{head}: {text}'

async def printuser(user, details=False, cell=None):

    iden = user.get('iden')
    name = user.get('name')
    admin = user.get('admin')
    authtype = user.get('type')

    outp.printf(f'{name} ({iden})')
    outp.printf(f'type: {authtype}')
    if admin is not None:
        outp.printf(f'admin: {admin}')

    if authtype == 'user':
        locked = user.get('locked')
        outp.printf(f'locked: {locked}')

    outp.printf('rules:')

    i = 0

    for rule in user.get('rules'):
        rrep = reprrule(rule)
        outp.printf(f'    {i} {rrep}')
        i += 1

    for gateiden, gateinfo in user.get('authgates', {}).items():
        outp.printf(f'  auth gate: {gateiden}')
        for rule in gateinfo.get('rules', ()):
            rrep = reprrule(rule)
            outp.printf(f'    {i} {rrep}')
            i += 1

    outp.printf('')

    if authtype == 'user':

        outp.printf('roles:')
        for rolename in sorted(user.get('roles')):
            outp.printf(f'    role: {rolename}')

            if details:
                i = 0
                role = await cell.getAuthInfo(rolename)
                for rule in role.get('rules', ()):
                    rrep = reprrule(rule)
                    outp.printf(f'        {i} {rrep}')
                    i += 1

                for gateiden, gateinfo in role.get('authgates', {}).items():
                    outp.printf(f'    auth gate: {gateiden}')
                    for rule in gateinfo.get('rules', ()):
                        rrep = reprrule(rule)
                        outp.printf(f'      {i} {rrep}')
                        i += 1

async def handleModify(opts):

    cell_supports_authgate = False

    if opts.object and not opts.addrule:
        outp.printf('--object option only valid with --addrule')
        return -1

    try:
        async with await s_telepath.openurl(opts.cellurl) as cell:

            async def useriden(name):
                udef = await cell.getUserDefByName(name)
                return udef['iden']

            async def roleiden(name):
                rdef = await cell.getRoleDefByName(name)
                return rdef['iden']

            s_version.reqVersion(cell._getSynVers(), reqver)
            if cell._getSynVers() >= min_authgate_vers:
                cell_supports_authgate = True

            if opts.adduser:
                outp.printf(f'adding user: {opts.name}')
                user = await cell.addUser(opts.name)

            if opts.deluser:
                outp.printf(f'deleting user: {opts.name}')
                await cell.delUser(await useriden(opts.name))

            if opts.addrole:
                outp.printf(f'adding role: {opts.name}')
                user = await cell.addRole(opts.name)

            if opts.delrole:
                outp.printf(f'deleting role: {opts.name}')
                await cell.delRole(await roleiden(opts.name))

            if opts.passwd:
                outp.printf(f'setting passwd for: {opts.name}')
                await cell.setUserPasswd(await useriden(opts.name), opts.passwd)

            if opts.grant:
                outp.printf(f'granting {opts.grant} to: {opts.name}')
                await cell.addUserRole(await useriden(opts.name), await roleiden(opts.grant))

            if opts.revoke:
                outp.printf(f'revoking {opts.revoke} from: {opts.name}')
                await cell.delUserRole(await useriden(opts.name), await roleiden(opts.revoke))

            if opts.admin:
                outp.printf(f'granting admin status: {opts.name}')
                await cell.setAuthAdmin(opts.name, True)

            if opts.noadmin:
                outp.printf(f'revoking admin status: {opts.name}')
                await cell.setAuthAdmin(opts.name, False)

            if opts.lock:
                outp.printf(f'locking user: {opts.name}')
                await cell.setUserLocked(await useriden(opts.name), True)

            if opts.unlock:
                outp.printf(f'unlocking user: {opts.name}')
                await cell.setUserLocked(await useriden(opts.name), False)

            if opts.addrule:

                text = opts.addrule

                # TODO: syntax for index...
                allow = True
                if text.startswith('!'):
                    allow = False
                    text = text[1:]

                rule = (allow, text.split('.'))

                outp.printf(f'adding rule to {opts.name}: {rule!r}')
                if cell_supports_authgate:
                    await cell.addAuthRule(opts.name, rule, indx=None, gateiden=opts.object)
                else:
                    await cell.addAuthRule(opts.name, rule, indx=None)

            if opts.delrule is not None:
                ruleind = opts.delrule
                outp.printf(f'deleting rule index: {ruleind}')

                user = await cell.getAuthInfo(opts.name)
                userrules = user.get('rules', ())

                delrule = None
                delgate = None

                if ruleind < len(userrules):
                    delrule = userrules[ruleind]

                else:
                    i = len(userrules)
                    for gateiden, gateinfo in user.get('authgates', {}).items():
                        for rule in gateinfo.get('rules', ()):
                            if i == ruleind:
                                delrule = rule
                                delgate = gateiden
                            i += 1

                if delrule is not None:
                    await cell.delAuthRule(opts.name, delrule, gateiden=delgate)
                else:
                    outp.printf(f'rule index is out of range')

            try:
                user = await cell.getAuthInfo(opts.name)
            except s_exc.NoSuchName:
                outp.printf(f'no such user: {opts.name}')
                return 1

            await printuser(user)

    except s_exc.BadVersion as e:
        valu = s_version.fmtVersion(*e.get('valu'))
        outp.printf(f'Cell version {valu} is outside of the cellauth supported range ({reqver}).')
        outp.printf(f'Please use a version of Synapse which supports {valu}; current version is {s_version.verstring}.')
        return 1

    except Exception as e:  # pragma: no cover

        if opts.debug:
            traceback.print_exc()

        outp.printf(str(e))
        return 1

    else:
        return 0

async def handleList(opts):
    try:
        async with await s_telepath.openurl(opts.cellurl) as cell:
            s_version.reqVersion(cell._getSynVers(), reqver)
            if opts.name:
                user = await cell.getAuthInfo(opts.name[0])
                if user is None:
                    outp.printf(f'no such user: {opts.name}')
                    return 1

                await printuser(user, cell=cell, details=opts.detail)
                return 0

            outp.printf(f'getting users and roles')

            outp.printf('users:')
            for user in await cell.getAuthUsers():
                outp.printf(f'    {user.get("name")}')

            outp.printf('roles:')
            for role in await cell.getAuthRoles():
                outp.printf(f'    {role.get("name")}')

    except s_exc.BadVersion as e:
        valu = s_version.fmtVersion(*e.get('valu'))
        outp.printf(f'Cell version {valu} is outside of the cellauth supported range ({reqver}).')
        outp.printf(f'Please use a version of Synapse which supports {valu}; current version is {s_version.verstring}.')
        return 1

    except Exception as e:  # pragma: no cover

        if opts.debug:
            traceback.print_exc()

        outp.printf(str(e))
        return 1

    else:
        return 0

async def main(argv, outprint=None):
    if outprint is None:   # pragma: no cover
        outprint = s_output.OutPut()
    global outp
    outp = outprint

    pars = makeargparser()
    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit:
        return -1

    return await opts.func(opts)

def makeargparser():
    global outp
    pars = s_cmd.Parser('synapse.tools.cellauth', outp=outp, description=desc)

    pars.add_argument('--debug', action='store_true', help='Show debug traceback on error.')
    pars.add_argument('cellurl', help='The telepath URL to connect to a cell.')

    subpars = pars.add_subparsers(required=True,
                                  title='subcommands',
                                  dest='cmd',
                                  parser_class=functools.partial(s_cmd.Parser, outp=outp))

    # list
    pars_list = subpars.add_parser('list', help='List users/roles')
    pars_list.add_argument('name', nargs='*', default=None, help='The name of the user/role to list')
    pars_list.add_argument('-d', '--detail', default=False, action='store_true',
                           help='Show rule details for roles associated with a user.')
    pars_list.set_defaults(func=handleList)

    # create / modify / delete
    pars_mod = subpars.add_parser('modify', help='Create, modify, delete the names user/role')
    muxp = pars_mod.add_mutually_exclusive_group()
    muxp.add_argument('--adduser', action='store_true', help='Add the named user to the cortex.')
    muxp.add_argument('--addrole', action='store_true', help='Add the named role to the cortex.')

    muxp.add_argument('--deluser', action='store_true', help='Delete the named user to the cortex.')
    muxp.add_argument('--delrole', action='store_true', help='Delete the named role to the cortex.')

    muxp.add_argument('--admin', action='store_true', help='Grant admin powers to the user/role.')
    muxp.add_argument('--noadmin', action='store_true', help='Revoke admin powers from the user/role.')

    muxp.add_argument('--lock', action='store_true', help='Lock the user account.')
    muxp.add_argument('--unlock', action='store_true', help='Unlock the user account.')

    muxp.add_argument('--passwd', help='Set the user password.')

    muxp.add_argument('--grant', help='Grant the specified role to the user.')
    muxp.add_argument('--revoke', help='Grant the specified role to the user.')

    muxp.add_argument('--addrule', help='Add the given rule to the user/role.')
    muxp.add_argument('--delrule', type=int, help='Delete the given rule number from the user/role.')

    pars_mod.add_argument('--object', type=str, help='The iden of the object to which to apply the new rule. Only '
                                                     'supported on Cells running Synapse >= 0.1.33.')

    pars_mod.add_argument('name', help='The user/role to modify.')
    pars_mod.set_defaults(func=handleModify)
    return pars

async def _main():  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    return await main(sys.argv[1:])

if __name__ == '__main__':  # pragma: no cover
    sys.exit(s_glob.sync(_main()))
