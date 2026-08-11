import os
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cmd as s_cmd
import synapse.lib.mddocs as s_mddocs
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

async def buildPkgDocs(pkgpath, save=None, ci=False, warnfile=None):
    '''
    Build a package's docs/ directory into a doc bundle at files/docs, next
    to the package's own pkgdef -- so the built docs are picked up as
    ordinary package files (see synapse.tools.storm.pkg.gen.loadPkgProto)
    and travel with the package to the Axon/Hub like any other declared
    file.

    Notes:
        A package which ships no docs directory builds nothing and returns
        None -- documentation is optional.

    Args:
        pkgpath (str): Path to a storm package prototype yaml file.
        save (str): Output directory for the built bundle. Defaults to
            <dir-of-pkgpath>/files/docs.
        ci (bool): Passed through to synapse.lib.mddocs.buildBundle -- write
            issues to warnfile (or drop them) instead of failing the build.
        warnfile (str): Passed through to synapse.lib.mddocs.buildBundle --
            where any --ci warnings/validation issues are written.

    Returns:
        dict: The built bundle's metadata (see synapse.lib.mddocs.buildDocs),
            or None if the package has no docs directory.
    '''
    logger.info(f'Building pkg docs for {pkgpath}')
    pkgdef = s_common.yamlload(pkgpath)
    if pkgdef is None:
        raise s_exc.BadArg(mesg=f'Package does not exist or does not contain yaml: {pkgpath}')

    dirn = os.path.dirname(s_common.genpath(pkgpath))

    # a package is not required to ship documentation, so there is simply
    # nothing to build here ( the same way genpkg.iterPkgProtoFiles treats a
    # package with no files directory )
    docsdir = os.path.join(dirn, 'docs')
    if not os.path.isdir(docsdir):
        logger.info(f'Package has no docs directory, skipping doc build: {docsdir}')
        return None

    outdir = save if save is not None else os.path.join(dirn, 'files', 'docs')

    # staticdir is always the package's REAL files/docs -- independent of
    # --save. --save exists so a doc-build test that boots the same
    # package as a live, self-referential Storm service (e.g.
    # test/fileparser/test_docs.py, test/playwright/test_docs.py) can
    # build without writing into the real files/docs mid-test; but a
    # page's ```mdtoc target or internal link may resolve to static
    # content (changelog.md, an image, any plain .md with no
    # mdstorm/mdtoc directive) that only ever lives in the real
    # files/docs, never in a --save override location. Falling back to
    # the real files/docs here -- rather than to outdir, which may be the
    # --save override -- keeps that resolution working in both cases.
    staticdir = os.path.join(dirn, 'files', 'docs')

    # stagedir_parent is the package's own directory -- a sibling of
    # files/ itself, not merely of outdir (files/docs, one level inside
    # files/) -- so a live, self-referential ```mdstorm-setup --load-svc
    # fence (synapse.tools.storm.pkg.gen walks the package's WHOLE files/
    # tree) never sees the staging dir as one of its own declared files.
    metadata = await s_mddocs.buildBundle(docsdir, outdir, staticdir=staticdir, ci=ci, warnfile=warnfile,
                                           stagedir_parent=dirn)

    logger.info(f'buildPkgDocs complete for {pkgpath} -> {outdir}')

    return metadata

prog = 'synapse.tools.storm.pkg.doc'
desc = 'A tool for building a storm package docs/ directory into a files/docs bundle.'

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog=prog, outp=outp, description=desc)
    pars.add_argument('pkgfile', metavar='<pkgfile>', help='Path to a storm package prototype yaml file.')
    pars.add_argument('--save', metavar='<dir>',
                       help='Output directory to build the bundle into. Defaults to <pkgdir>/files/docs.')
    pars.add_argument('--ci', default=False, action='store_true',
                       help='Collect warnings/validation issues into --warnfile instead of '
                            'failing the build (see docs/Makefile mddocs_ciflag for why).')
    pars.add_argument('--warnfile', metavar='<path>',
                       help='With --ci, write warnings/validation issues here instead of raising.')

    opts = pars.parse_args(argv)

    await buildPkgDocs(opts.pkgfile, save=opts.save, ci=opts.ci, warnfile=opts.warnfile)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
