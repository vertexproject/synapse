import sys
import asyncio
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

descr = '''
Add or modify a role in a Synapse service.
'''

def printrole(role, outp):

    outp.printf(f'Role: {role.get("name")} ({role.get("iden")})')
    outp.printf('')
    outp.printf('  Rules:')
    for indx, rule in enumerate(role.get('rules')):
        outp.printf(f'    [{str(indx).ljust(3)}] - {s_common.reprauthrule(rule)}')

    outp.printf('')
    outp.printf('  Gates:')
    for gateiden, gateinfo in role.get('authgates', {}).items():
        outp.printf(f'    {gateiden}')
        outp.printf(f'      Admin: {gateinfo.get("admin") == True}')
        for indx, rule in enumerate(gateinfo.get('rules', ())):
            outp.printf(f'      [{str(indx).ljust(3)}] - {s_common.reprauthrule(rule)}')

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='modrole', description=descr)
    pars.add_argument('--svcurl', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--add', default=False, action='store_true', help='Add the role if they do not already exist.')
    pars.add_argument('--del', dest='delete', default=False, action='store_true', help='Delete the role if it exists.')
    pars.add_argument('--list', default=False, action='store_true',
                      help='List existing roles, or rules of a specific role.')
    pars.add_argument('--allow', default=[], action='append', help='A permission string to allow for the role.')
    pars.add_argument('--deny', default=[], action='append', help='A permission string to deny for the role.')
    pars.add_argument('--gate', default=None, help='The iden of an auth gate to add/del rules on.')
    pars.add_argument('rolename', nargs='?', help='The rolename to add/edit.')

    opts = pars.parse_args(argv)

    if opts.add and opts.delete:
        outp.printf('ERROR: Cannot specify --add and --del together.')
        return 1

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.svcurl) as cell:

            if opts.list:
                if opts.rolename:
                    role = await cell.getRoleDefByName(opts.rolename)
                    if role is None:
                        outp.printf(f'ERROR: Role not found: {opts.rolename}')
                        return 1

                    printrole(role, outp)

                else:
                    outp.printf('Roles:')
                    for role in await cell.getRoleDefs():
                        outp.printf(f'  {role.get("iden")} - {role.get("name")}')

                return 0
            elif opts.rolename is None:
                outp.printf(f'ERROR: A rolename argument is required when --list is not specified.')
                return 1

            if opts.gate:
                gate = await cell.getAuthGate(opts.gate)
                if gate is None:
                    outp.printf(f'ERROR: No auth gate found with iden: {opts.gate}')
                    return 1

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

            if opts.delete:
                outp.printf(f'...deleting role: {opts.rolename}')
                await cell.delRole(roleiden)
                return 0

            for allow in opts.allow:
                perm = allow.lower().split('.')
                mesg = f'...adding allow rule: {allow}'
                if opts.gate:
                    mesg += f' on gate {opts.gate}'

                outp.printf(mesg)
                if not await cell.isRoleAllowed(roleiden, perm, gateiden=opts.gate):
                    await cell.addRoleRule(roleiden, (True, perm), indx=0, gateiden=opts.gate)

            for deny in opts.deny:
                perm = deny.lower().split('.')
                mesg = f'...adding deny rule: {deny}'
                if opts.gate:
                    mesg += f' on gate {opts.gate}'

                outp.printf(mesg)
                if await cell.isRoleAllowed(roleiden, perm, gateiden=opts.gate):
                    await cell.addRoleRule(roleiden, (False, perm), indx=0, gateiden=opts.gate)
    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
