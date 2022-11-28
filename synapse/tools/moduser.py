import sys
import yaml
import asyncio
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
Add or modify a user of a Synapse service.
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='moduser', description=descr)
    pars.add_argument('--svcurl', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--add', default=False, action='store_true', help='Add the user if they do not already exist.')
    pars.add_argument('--del', dest='delete', default=False, action='store_true', help='Delete the user if they exist.')
    pars.add_argument('--admin', choices=('true', 'false'), default=None, help='Set the user admin status.')
    pars.add_argument('--passwd', action='store', type=str, help='A password to set for the user.')
    pars.add_argument('--email', action='store', type=str, help='An email to set for the user.')
    pars.add_argument('--locked', choices=('true', 'false'), default=None, help='Set the user locked status.')
    pars.add_argument('--grant', default=[], action='append', help='A role to grant to the user.')
    pars.add_argument('--revoke', default=[], action='append', help='A role to revoke from the user.')
    pars.add_argument('--allow', default=[], action='append', help='A permission string to allow for the user.')
    pars.add_argument('--deny', default=[], action='append', help='A permission string to deny for the user.')
    pars.add_argument('username', help='The username to add/edit.')

    opts = pars.parse_args(argv)

    if opts.add and opts.delete:
        outp.printf('ERROR: Cannot specify --add and --del together.')
        return 1

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.svcurl) as cell:

            grants = []
            revokes = []

            for rolename in opts.grant:
                role = await cell.getRoleDefByName(rolename)
                if role is None:
                    outp.printf(f'ERROR: Role not found: {rolename}')
                    return 1
                grants.append(role)

            for rolename in opts.revoke:
                role = await cell.getRoleDefByName(rolename)
                if role is None:
                    outp.printf(f'ERROR: Role not found: {rolename}')
                    return 1
                revokes.append(role)

            user = await cell.getUserDefByName(opts.username)

            if user is None:
                if not opts.add:
                    outp.printf(f'ERROR: User not found (need --add?): {opts.username}')
                    return 1

                outp.printf(f'Adding user: {opts.username}')
                user = await cell.addUser(opts.username)

            else:
                outp.printf(f'Modifying user: {opts.username}')

            useriden = user.get('iden')
            if not s_common.isguid(useriden):  # pragma: no cover
                outp.printf(f'ERROR: Invalid useriden: {useriden}')
                return 1

            if opts.delete:
                outp.printf(f'...deleting user: {opts.username}')
                await cell.delUser(useriden)
                return 0

            if opts.admin is not None:
                admin = yaml.safe_load(opts.admin)
                outp.printf(f'...setting admin: {opts.admin}')
                await cell.setUserAdmin(useriden, admin)

            if opts.locked is not None:
                locked = yaml.safe_load(opts.locked)
                outp.printf(f'...setting locked: {opts.locked}')
                await cell.setUserLocked(useriden, locked)

            if opts.passwd is not None:
                outp.printf(f'...setting passwd: {opts.passwd}')
                await cell.setUserPasswd(useriden, opts.passwd)

            if opts.email is not None:
                outp.printf(f'...setting email: {opts.email}')
                await cell.setUserEmail(useriden, opts.email)

            for role in grants:
                rolename = role.get('name')
                outp.printf(f'...granting role: {rolename}')
                await cell.addUserRole(useriden, role.get('iden'))

            for role in revokes:
                rolename = role.get('name')
                outp.printf(f'...revoking role: {rolename}')
                await cell.delUserRole(useriden, role.get('iden'))

            for allow in opts.allow:
                perm = allow.lower().split('.')
                outp.printf(f'...adding allow rule: {allow}')
                if not await cell.isUserAllowed(useriden, perm):
                    await cell.addUserRule(useriden, (True, perm), indx=0)

            for deny in opts.deny:
                perm = deny.lower().split('.')
                outp.printf(f'...adding deny rule: {deny}')
                if await cell.isUserAllowed(useriden, perm):
                    await cell.addUserRule(useriden, (False, perm), indx=0)
    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
