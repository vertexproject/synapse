import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.time as s_time
import synapse.lib.output as s_output

descr = '''
Add, list, or delete user API keys from a Synapse service.
'''

def printkey(outp, info, apikey=None):
    iden = info.get('iden')
    name = info.get('name')
    created = info.get('created')
    updated = info.get('updated')
    expires = info.get('expires')

    outp.printf(f'Iden: {iden}')
    if apikey:
        outp.printf(f'  API Key: {apikey}')
    outp.printf(f'  Name: {name}')
    outp.printf(f'  Created: {s_time.repr(created)}')
    outp.printf(f'  Updated: {s_time.repr(updated)}')
    if expires:
        outp.printf(f'  Expires: {s_time.repr(expires)}')

    outp.printf('')

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='apikey', description=descr)
    pars.add_argument('--svcurl', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')

    subpars = pars.add_subparsers(dest='action', required=True)

    addp = subpars.add_parser('add', help='Add a user API key.')
    addp.add_argument('-d', '--duration', type=int, help='The duration of the API key in seconds.')
    addp.add_argument('-u', '--username', type=str, help='The username to add an API key to (restricted to admins).')
    addp.add_argument('name', help='The name of the API key to add.')

    listp = subpars.add_parser('list', help='List user API keys.')
    listp.add_argument('-u', '--username', type=str, help='The username to list API keys for (restricted to admins).')

    delp = subpars.add_parser('del', help='Delete a user API key.')
    delp.add_argument('iden', help='The iden of the API key to delete.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.svcurl) as cell:

            try:
                useriden = None
                if opts.action in ('add', 'list') and opts.username:
                    user = await cell.getUserInfo(opts.username)
                    useriden = user.get('iden')

                if opts.action == 'add':
                    if (duration := opts.duration) is not None:
                        # Convert from seconds to milliseconds
                        duration *= 1000

                    apikey, info = await cell.addUserApiKey(opts.name, duration=duration, useriden=useriden)
                    outp.printf(f'Successfully added API key with name={opts.name}.')
                    printkey(outp, info, apikey)

                elif opts.action == 'del':
                    await cell.delUserApiKey(opts.iden)
                    outp.printf(f'Successfully deleted API key with iden={opts.iden}.')

                elif opts.action == 'list':
                    apikeys = await cell.listUserApiKeys(useriden=useriden)
                    if not apikeys:
                        outp.printf('No API keys found.')
                        return 0

                    for info in apikeys:
                        printkey(outp, info)

            except s_exc.SynErr as exc:
                mesg = exc.get('mesg')
                outp.printf(f'ERROR: {exc.__class__.__name__}: {mesg}')
                return 1

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
