import sys
import asyncio
import argparse

import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
Add or modify a role in a Synapse service.
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='modrole', description=descr)
    pars.add_argument('--svcurl', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--add', default=False, action='store_true', help='Add the role if they do not already exist.')
    pars.add_argument('--allow', default=[], action='append', help='A permission string to allow for the role.')
    pars.add_argument('--deny', default=[], action='append', help='A permission string to deny for the role.')
    pars.add_argument('rolename', help='The rolename to add/edit.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.svcurl) as cell:

            role = await cell.getRoleDefByName(opts.rolename)
            if role is not None:
                outp.printf(f'Modifying role: {opts.rolename}')

            if role is None:
                if not opts.add:
                    outp.printf(f'ERROR: Role not found (need --add?): {opts.rolename}')
                    return 1

                outp.printf(f'Adding role: {opts.rolename}')
                role = await cell.addRole(opts.rolename)

            roleiden = role.get('iden')

            for allow in opts.allow:
                perm = allow.lower().split('.')
                outp.printf(f'...adding allow rule: {allow}')
                if not await cell.isRoleAllowed(roleiden, perm):
                    await cell.addRoleRule(roleiden, (True, perm), indx=0)

            for deny in opts.deny:
                perm = deny.lower().split('.')
                outp.printf(f'...adding deny rule: {deny}')
                if await cell.isRoleAllowed(roleiden, perm):
                    await cell.addRoleRule(roleiden, (False, perm), indx=0)
    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
