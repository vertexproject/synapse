import sys
import argparse
import traceback

import synapse.telepath as s_telepath

desc = '''
Admin users in a remote cell.
'''

denyallow = ['deny', 'allow']
def reprrule(rule):
    head = denyallow[rule[0]]
    text = '.'.join(rule[1])
    return f'{head}: {text}'

def printuser(user):

    admin = user[1].get('admin')
    authtype = user[1].get('type')

    print(f'{user[0]}')
    print(f'type: {authtype}')
    print(f'admin: {admin}')

    if authtype == 'user':
        locked = user[1].get('locked')
        print(f'locked: {locked}')

    print('rules:')

    for i, rule in enumerate(user[1].get('rules')):
        rrep = reprrule(rule)
        print(f'    {i} {rrep}')

    print('')

    if authtype == 'user':

        print('roles:')
        for rolename, roleinfo in sorted(user[1].get('roles')):
            print(f'    role: {rolename}')
            for rule in roleinfo.get('rules'):
                rrep = reprrule(rule)
                print(f'        {rrep}')

def main(argv):

    pars = argparse.ArgumentParser('synapse.tools.cellauth', description=desc)

    pars.add_argument('--debug', action='store_true', help='Show debug traceback on error.')
    pars.add_argument('--adduser', action='store_true', help='Add the named user to the cortex.')
    pars.add_argument('--addrole', action='store_true', help='Add the named role to the cortex.')

    pars.add_argument('--admin', action='store_true', help='Grant admin powers to the user/role.')
    pars.add_argument('--noadmin', action='store_true', help='Revoke admin powers from the user/role.')

    pars.add_argument('--lock', action='store_true', help='Lock the user account.')
    pars.add_argument('--unlock', action='store_true', help='Unlock the user account.')

    #pars.add_argument('--deluser', action='store_true', help='Add the named user to the cortex.')
    #pars.add_argument('--delrole', action='store_true', help='Add the named role to the cortex.')

    pars.add_argument('--passwd', help='Set the user password.')

    pars.add_argument('--grant', help='Grant the specified role to the user.')
    pars.add_argument('--revoke', help='Grant the specified role to the user.')

    pars.add_argument('--addrule', help='Add the given rule to the user/role.')
    pars.add_argument('--delrule', type=int, help='Delete the given rule number from the user/role.')

    pars.add_argument('name', help='The user/role to modify.')
    pars.add_argument('cellurl', help='The telepath URL to connect to a cell.')

    opts = pars.parse_args(argv)

    try:

        with s_telepath.openurl(opts.cellurl) as cell:

            if opts.adduser:
                print(f'adding user: {opts.name}')
                user = cell.addAuthUser(opts.name)

            if opts.addrole:
                print(f'adding role: {opts.name}')
                user = cell.addAuthRole(opts.name)

            if opts.passwd:
                print(f'setting passwd for: {opts.name}')
                cell.setUserPasswd(opts.name, opts.passwd)

            if opts.grant:
                print(f'granting {opts.grant} to: {opts.name}')
                cell.addUserRole(opts.name, opts.grant)

            if opts.revoke:
                print(f'revoking {opts.grant} from: {opts.name}')
                cell.delUserRole(opts.name, opts.revoke)

            if opts.admin:
                print(f'granting admin status: {opts.name}')
                cell.setAuthAdmin(opts.name, True)

            if opts.noadmin:
                print(f'revoking admin status: {opts.name}')
                cell.setAuthAdmin(opts.name, False)

            if opts.lock:
                print(f'locking user: {opts.name}')
                cell.setUserLocked(opts.name, True)

            if opts.unlock:
                print(f'unlocking user: {opts.name}')
                cell.setUserLocked(opts.name, False)

            if opts.addrule:

                text = opts.addrule

                #TODO: syntax for index...
                allow = True
                if text.startswith('!'):
                    allow = False
                    text = text[1:]

                rule = (allow, text.split('.'))

                print(f'adding rule to {opts.name}: {rule!r}')
                cell.addAuthRule(opts.name, rule, indx=None)

            if opts.delrule is not None:
                print(f'deleting rule index: {opts.delrule}')
                cell.delAuthRule(opts.name, opts.delrule)

            user = cell.getAuthInfo(opts.name)
            if user is None:
                print(f'no such user: {opts.name}')
                return

            printuser(user)

    except Exception as e:

        if opts.debug:
            traceback.print_exc()

        print(e)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
