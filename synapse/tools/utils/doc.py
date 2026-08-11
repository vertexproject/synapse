import logging

import synapse.lib.cmd as s_cmd
import synapse.lib.mddocs as s_mddocs
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

prog = 'synapse.tools.utils.doc'
desc = '''
A tool for building a Markdown doc bundle from a docs/ source tree that has no Storm package
pkgdef of its own (e.g. the synapse or synapse-enterprise docs bundles). Use
synapse.tools.storm.pkg.doc instead for a Storm package's own docs/ directory.
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog=prog, outp=outp, description=desc)
    pars.add_argument('srcdir', metavar='<srcdir>', help='The doc source directory (containing index.md).')
    pars.add_argument('outdir', metavar='<outdir>',
                       help='The canonical, committed bundle directory to merge built output into.')
    pars.add_argument('--staticdir', metavar='<dir>',
                       help='Fallback read location for a mdtoc target or internal link that resolves '
                            'to a page living only in the committed bundle. Defaults to <outdir>.')
    pars.add_argument('--ci', default=False, action='store_true',
                       help='Collect warnings/validation issues into --warnfile instead of '
                            'failing the build (see docs/Makefile mddocs_ciflag for why).')
    pars.add_argument('--warnfile', metavar='<path>',
                       help='With --ci, write warnings/validation issues here instead of raising.')

    opts = pars.parse_args(argv)

    outp.printf(f'Building docs for {opts.srcdir}')

    await s_mddocs.buildBundle(opts.srcdir, opts.outdir, staticdir=opts.staticdir, ci=opts.ci,
                                warnfile=opts.warnfile)

    outp.printf(f'Built {opts.srcdir} -> {opts.outdir}')

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
