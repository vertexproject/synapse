import logging

import synapse.lib.cmd as s_cmd
import synapse.lib.mddocs as s_mddocs
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

prog = 'synapse.tools.utils.docmanifest'
desc = '''
A tool for reconciling a doc bundle's docs.sha256 against what is on disk, without
building anything. A build writes the manifest itself, so this is for the case where no
build ran: it re-hashes each directive-bearing page and the output it was built into, and
rewrites the manifest from that.

The manifest is written next to the docs source (see synapse.lib.mddocs.getManifestPath),
which is where the build and every reader of the format look for it.
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog=prog, outp=outp, description=desc)
    pars.add_argument('srcdir', metavar='<srcdir>', help='The doc source directory (containing index.md).')
    pars.add_argument('outdir', metavar='<outdir>', help='The built bundle directory the sources were built into.')

    opts = pars.parse_args(argv)

    path = s_mddocs.writeManifest(opts.srcdir, opts.outdir)

    count = len(s_mddocs.loadManifest(path))
    outp.printf(f'Wrote {count} entr{"y" if count == 1 else "ies"} to {path}')

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
