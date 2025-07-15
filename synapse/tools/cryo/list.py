import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.cryo.list', outp=outp, description='List tanks within a cryo cell.')
    pars.add_argument('cryocell', nargs='+', help='Telepath URLs to cryo cells.')

    opts = pars.parse_args(argv)

    for url in opts.cryocell:

        outp.printf(url)

        async with s_telepath.withTeleEnv():

            async with await s_telepath.openurl(url) as cryo:

                for name, info in await cryo.list():
                    outp.printf(f'    {name}: {info}')

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
