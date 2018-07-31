import sys
import argparse
import traceback

import synapse.exc as s_exc
import synapse.lib.output as s_output
import synapse.telepath as s_telepath

desc = '''
Admin users in a remote cell.
'''
outp = None

denyallow = ['deny', 'allow']
def reprrule(rule):
    head = denyallow[rule[0]]
    text = '.'.join(rule[1])
    return f'{head}: {text}'

def printuser(user):

    admin = user[1].get('admin')
    authtype = user[1].get('type')

    outp.printf(f'{user[0]}')
    outp.printf(f'type: {authtype}')
    outp.printf(f'admin: {admin}')

    if authtype == 'user':
        locked = user[1].get('locked')
        outp.printf(f'locked: {locked}')

    outp.printf('rules:')

    for i, rule in enumerate(user[1].get('rules')):
        rrep = reprrule(rule)
        outp.printf(f'    {i} {rrep}')

    outp.printf('')

    if authtype == 'user':

        outp.printf('roles:')
        for rolename, roleinfo in sorted(user[1].get('roles')):
            outp.printf(f'    role: {rolename}')
            for rule in roleinfo.get('rules'):
                rrep = reprrule(rule)
                outp.printf(f'        {rrep}')

def handleModify(opts):
    try:

        with s_telepath.openurl(opts.cellurl) as cell:

            if opts.adduser:
                outp.printf(f'adding user: {opts.name}')
                user = cell.addAuthUser(opts.name)

            if opts.addrole:
                outp.printf(f'adding role: {opts.name}')
                user = cell.addAuthRole(opts.name)

            if opts.passwd:
                outp.printf(f'setting passwd for: {opts.name}')
                cell.setUserPasswd(opts.name, opts.passwd)

            if opts.grant:
                outp.printf(f'granting {opts.grant} to: {opts.name}')
                cell.addUserRole(opts.name, opts.grant)

            if opts.revoke:
                outp.printf(f'revoking {opts.revoke} from: {opts.name}')
                cell.delUserRole(opts.name, opts.revoke)

            if opts.admin:
                outp.printf(f'granting admin status: {opts.name}')
                cell.setAuthAdmin(opts.name, True)

            if opts.noadmin:
                outp.printf(f'revoking admin status: {opts.name}')
                cell.setAuthAdmin(opts.name, False)

            if opts.lock:
                outp.printf(f'locking user: {opts.name}')
                cell.setUserLocked(opts.name, True)

            if opts.unlock:
                outp.printf(f'unlocking user: {opts.name}')
                cell.setUserLocked(opts.name, False)

            if opts.addrule:

                text = opts.addrule

                #TODO: syntax for index...
                allow = True
                if text.startswith('!'):
                    allow = False
                    text = text[1:]

                rule = (allow, text.split('.'))

                outp.printf(f'adding rule to {opts.name}: {rule!r}')
                cell.addAuthRule(opts.name, rule, indx=None)

            if opts.delrule is not None:
                outp.printf(f'deleting rule index: {opts.delrule}')
                cell.delAuthRule(opts.name, opts.delrule)

            try:
                user = cell.getAuthInfo(opts.name)
            except s_exc.NoSuchName as e:
                outp.printf(f'no such user: {opts.name}')
                return

            printuser(user)

    except Exception as e: # pragma: no cover

        if opts.debug:
            traceback.print_exc()

        outp.printf(e)

def handleList(opts):
    try:
        with s_telepath.openurl(opts.cellurl) as cell:

            if opts.name:
                user = cell.getAuthInfo(opts.name)
                if user is None:
                    outp.printf(f'no such user: {opts.name}')
                    return

                printuser(user)
                return

            outp.printf(f'getting users and roles')

            outp.printf('users:')
            for user in cell.getAuthUsers():
                outp.printf(f'    {user}')

            outp.printf('roles:')
            for role in cell.getAuthRoles():
                outp.printf(f'    {role}')
            return

    except Exception as e: # pragma: no cover

        if opts.debug:
            traceback.print_exc()

        outp.printf(e)

def main(argv, outprint=None):
    if outprint is None:  # pragma: no cover
        outprint = s_output.OutPut()
    global outp
    outp = outprint

    pars = argparse.ArgumentParser('synapse.tools.cellauth', description=desc)

    pars.add_argument('--debug', action='store_true', help='Show debug traceback on error.')
    pars.add_argument('cellurl', help='The telepath URL to connect to a cell.')

    subpars = pars.add_subparsers()

    # list
    pars_list = subpars.add_parser('list', help='List users/roles')
    pars_list.add_argument('name', nargs='*', default=None, help='The name of the user/role to list')
    pars_list.set_defaults(func=handleList)

    # create / modify / delete
    pars_mod = subpars.add_parser('modify', help='Create, modify, delete the names user/role')
    pars_mod.add_argument('--adduser', action='store_true', help='Add the named user to the cortex.')
    pars_mod.add_argument('--addrole', action='store_true', help='Add the named role to the cortex.')

    pars_mod.add_argument('--admin', action='store_true', help='Grant admin powers to the user/role.')
    pars_mod.add_argument('--noadmin', action='store_true', help='Revoke admin powers from the user/role.')

    pars_mod.add_argument('--lock', action='store_true', help='Lock the user account.')
    pars_mod.add_argument('--unlock', action='store_true', help='Unlock the user account.')

    #pars_mod.add_argument('--deluser', action='store_true', help='Add the named user to the cortex.')
    #pars_mod.add_argument('--delrole', action='store_true', help='Add the named role to the cortex.')

    pars_mod.add_argument('--passwd', help='Set the user password.')

    pars_mod.add_argument('--grant', help='Grant the specified role to the user.')
    pars_mod.add_argument('--revoke', help='Grant the specified role to the user.')

    pars_mod.add_argument('--addrule', help='Add the given rule to the user/role.')
    pars_mod.add_argument('--delrule', type=int, help='Delete the given rule number from the user/role.')

    pars_mod.add_argument('name', help='The user/role to modify.')
    pars_mod.set_defaults(func=handleModify)

    opts = pars.parse_args(argv)
    opts.func(opts)

if __name__ == '__main__': # pragma: no cover
    sys.exit(main(sys.argv[1:]))
