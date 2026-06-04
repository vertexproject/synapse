import io
import os
import base64
import logging

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.schemas as s_schemas
import synapse.lib.version as s_version
import synapse.lib.stormbin as s_stormbin

logger = logging.getLogger(__name__)

wflownamere = regex.compile(r'^([\w-]+)\.yaml$')

# TODO - Update this minversion before tagging the release to ensure that
# our mininum required version for compilation is valid for the release.
_MINVER_FOR_COMPILATION = (2, 244, 0)
_MINVER_STR_FOR_COMPILATION = '.'.join([str(x) for x in _MINVER_FOR_COMPILATION])

def _reqValidForCompilation(pkgdef):
    pkgname = pkgdef.get('name')
    reqversion = pkgdef.get('synapse_version')
    if reqversion is not None:
        if not s_version.verLteFloor(_MINVER_STR_FOR_COMPILATION, reqversion):
            mesg = f'Storm package {pkgname} requires Synapse {reqversion} but ' \
                   f'compiled Storm requires a minimum version of {_MINVER_STR_FOR_COMPILATION}'
            raise s_exc.BadVersion(mesg=mesg)

    elif (minversion := pkgdef.get('synapse_minversion')) is not None:
        # This is for older packages that might not have the
        # `synapse_version` field.
        # TODO: Remove this whole else block after Synapse 3.0.0.
        if tuple(minversion) < _MINVER_FOR_COMPILATION:
            mesg = f'Storm package {pkgname} requires Synapse {minversion} but ' \
                   f'compiled Storm requires a minimum version of {_MINVER_STR_FOR_COMPILATION}'
            raise s_exc.BadVersion(mesg=mesg)

def getStormStr(fn):
    if not os.path.isfile(fn):
        raise s_exc.NoSuchFile(mesg='Storm file {} not found'.format(fn), path=fn)

    with open(fn, 'rb') as f:
        return f.read().decode()

def loadOpticFiles(pkgdef, path):

    pkgfiles = pkgdef['optic']['files']

    abspath = s_common.genpath(path)
    for root, dirs, files, in os.walk(path):

        for name in files:

            if name.startswith('.'):  # pragma: no cover
                continue

            fullname = s_common.genpath(root, name)
            if not os.path.isfile(fullname):  # pragma: no cover
                continue

            pkgfname = fullname[len(abspath) + 1:]

            with open(fullname, 'rb') as fd:
                pkgfiles[pkgfname] = {
                    'file': base64.b64encode(fd.read()).decode(),
                }

def loadOpticWorkflows(pkgdef, path):

    wdefs = pkgdef['optic']['workflows']

    for root, dirs, files in os.walk(path):

        for name in files:

            match = wflownamere.match(name)

            if match is None:
                logger.warning('Skipping workflow "%s" that does not match pattern "%s"' % (name, wflownamere.pattern))
                continue

            wname = match.groups()[0]

            fullname = s_common.genpath(root, name)
            if not os.path.isfile(fullname):  # pragma: no cover
                continue

            wdefs[wname] = s_common.yamlload(fullname)

def tryLoadPkgProto(fp, opticdir=None, readonly=False, compiled=False):
    '''
    Try to get a Storm Package prototype from disk with or without inline documentation.

    Args:
        fp (str): Path to the package .yaml file on disk.
        opticdir (str): Path to optional Optic module code to add to the Storm Package.
        readonly (bool): If set, open files in read-only mode. If files are missing, that will raise a NoSuchFile
                         exception.
        compiled (bool): If set, pre-compile Storm queries into stormbin binary format.

    Returns:
        dict: A Storm package definition.
    '''
    try:
        return loadPkgProto(fp, opticdir=opticdir, readonly=readonly, compiled=compiled)
    except s_exc.NoSuchFile:
        return loadPkgProto(fp, opticdir=opticdir, no_docs=True, readonly=readonly, compiled=compiled)

def loadPkgProto(path, opticdir=None, no_docs=False, readonly=False, compiled=False):
    '''
    Get a Storm Package definition from disk.

    Args:
        path (str): Path to the package .yaml file on disk.
        opticdir (str): Path to optional Optic module code to add to the Storm Package.
        no_docs (bool): If true, omit inline documentation content if it is not present on disk.
        readonly (bool): If set, open files in read-only mode. If files are missing, that will raise a NoSuchFile
                         exception.
        compiled (bool): If set, pre-compile Storm queries into stormbin binary format.

    Returns:
        dict: A Storm package definition.
    '''

    full = s_common.genpath(path)
    pkgdef = s_common.yamlload(full)
    if pkgdef is None:
        raise s_exc.NoSuchFile(mesg=f'File {full} does not exist or is empty.', path=full)

    version = pkgdef.get('version')
    if isinstance(version, (tuple, list)):
        pkgdef['version'] = '%d.%d.%d' % tuple(version)

    protodir = os.path.dirname(full)
    pkgname = pkgdef.get('name')

    genopts = pkgdef.pop('genopts', {})

    # Stamp build info into the pkgdef if it doesn't already exist
    pkgdef.setdefault('build', {})
    pkgdef['build'].setdefault('time', s_common.now())
    pkgdef['build'].setdefault('synapse:version', s_version.verstring)
    pkgdef['build'].setdefault('synapse:commit', s_version.commit)

    # Allow the genopts to influence compilation
    compiled = genopts.get('compiled', compiled)

    logodef = pkgdef.get('logo')
    if logodef is not None:

        path = logodef.pop('path', None)

        if path is not None:
            with s_common.reqfile(protodir, path) as fd:
                logodef['file'] = base64.b64encode(fd.read()).decode()

        if logodef.get('mime') is None:
            mesg = 'Mime type must be specified for logo file.'
            raise s_exc.BadPkgDef(mesg=mesg)

        if logodef.get('file') is None:
            mesg = 'Logo def must contain path or file.'
            raise s_exc.BadPkgDef(mesg=mesg)

    for docdef in pkgdef.get('docs', ()):

        if docdef.get('title') is None:
            mesg = 'Each entry in docs must have a title.'
            raise s_exc.BadPkgDef(mesg=mesg)

        if no_docs:
            docdef['content'] = ''
            continue

        path = docdef.pop('path', None)
        if path is not None:
            with s_common.reqfile(protodir, path) as fd:
                docdef['content'] = fd.read().decode()

        if docdef.get('content') is None:
            mesg = 'Docs entry has no path or content.'
            raise s_exc.BadPkgDef(mesg=mesg)

    for mod in pkgdef.get('modules', ()):

        name = mod.get('name')

        basename = name
        if genopts.get('dotstorm', False):
            basename = f'{basename}.storm'

        mod_path = s_common.genpath(protodir, 'storm', 'modules', basename)
        if readonly:
            mod['storm'] = getStormStr(mod_path)
        else:
            with s_common.genfile(mod_path) as fd:
                mod['storm'] = fd.read().decode()

    for extmod in pkgdef.get('external_modules', ()):
        fpth = extmod.get('file_path')
        if fpth is not None:
            extmod['storm'] = getStormStr(fpth)
        else:
            path = extmod.get('package_path')
            extpkg = s_dyndeps.reqDynMod(extmod.get('package'))
            extmod['storm'] = extpkg.getAssetStr(path)

        extname = extmod.get('name')
        extmod['name'] = f'{pkgname}.{extname}'

        pkgdef.setdefault('modules', [])
        pkgdef['modules'].append(extmod)

    pkgdef.pop('external_modules', None)

    for cmd in pkgdef.get('commands', ()):
        name = cmd.get('name')

        basename = name
        if genopts.get('dotstorm'):
            basename = f'{basename}.storm'

        cmd_path = s_common.genpath(protodir, 'storm', 'commands', basename)
        if readonly:
            cmd['storm'] = getStormStr(cmd_path)
        else:
            with s_common.genfile(cmd_path) as fd:
                cmd['storm'] = fd.read().decode()

    for gdef in pkgdef.get('graphs', ()):
        gdef['iden'] = s_common.guid((pkgname, gdef.get('name')))
        gdef['scope'] = 'power-up'
        gdef['power-up'] = pkgname

    inits = pkgdef.get('inits')
    if inits is not None:
        lastver = None
        for initdef in inits.get('versions'):
            curver = initdef.get('version')
            if lastver is not None and not curver > lastver:
                raise s_exc.BadPkgDef(mesg='Init versions must be monotonically increasing.', version=curver)
            lastver = curver

    wflowdir = s_common.genpath(protodir, 'workflows')
    if os.path.isdir(wflowdir):
        pkgdef.setdefault('optic', {})
        pkgdef['optic'].setdefault('workflows', {})
        loadOpticWorkflows(pkgdef, wflowdir)

    if opticdir is None:
        opticdir = s_common.genpath(protodir, 'optic')

    if os.path.isdir(opticdir):
        pkgdef.setdefault('optic', {})
        pkgdef['optic'].setdefault('files', {})
        loadOpticFiles(pkgdef, opticdir)

    if compiled:

        _reqValidForCompilation(pkgdef)

        for mod in pkgdef.get('modules', ()):
            text = mod.get('storm')
            if text is not None:
                mod['storm'] = s_stormbin.compile(text, ascii=True)

        for cmd in pkgdef.get('commands', ()):
            text = cmd.get('storm')
            if text is not None:
                cmd['storm'] = s_stormbin.compile(text, ascii=True)

        onload = pkgdef.get('onload')
        if onload is not None:
            pkgdef['onload'] = s_stormbin.compile(onload, ascii=True)

        inits = pkgdef.get('inits')
        if inits is not None:
            for initdef in inits.get('versions', ()):
                text = initdef.get('query')
                if text is not None:
                    initdef['query'] = s_stormbin.compile(text, ascii=True)

    s_schemas.reqValidPkgdef(pkgdef)

    # Ensure the package is json safe and tuplify it.
    s_json.reqjsonsafe(pkgdef, strict=True)
    pkgdef = s_common.tuplify(pkgdef)
    return pkgdef


desc = 'A tool for generating/pushing storm packages from YAML prototypes.'

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.pkg.gen', outp=outp, description=desc)
    pars.add_argument('--push', metavar='<url>', help='A telepath URL of a Cortex or PkgRepo.')
    pars.add_argument('--push-verify', default=False, action='store_true',
                      help='Tell the Cortex to verify the package signature.')
    pars.add_argument('--save', metavar='<path>', help='Save the completed package JSON to a file.')
    pars.add_argument('--optic', metavar='<path>', help='Load Optic module files from a directory.')
    pars.add_argument('--signas', metavar='<name>', help='Specify a code signing identity to use from ~/.syn/certs/code.')
    pars.add_argument('--certdir', metavar='<dir>', default='~/.syn/certs',
                      help='Specify an alternate certdir to ~/.syn/certs.')
    pars.add_argument('--no-build', action='store_true',
                      help='Treat pkgfile argument as an already-built package')
    pars.add_argument('--no-docs', default=False, action='store_true',
                      help='Do not require docs to be present and replace any doc content with empty strings.')
    pars.add_argument('--compiled', default=False, action='store_true',
                      help='Pre-compile Storm queries into stormbin binary format to skip parsing at load time.')
    pars.add_argument('pkgfile', metavar='<pkgfile>',
                      help='Path to a storm package prototype .yaml file, or a completed package .json/.yaml file.')

    opts = pars.parse_args(argv)

    if opts.no_build:
        pkgdef = s_common.yamlload(opts.pkgfile)
        if not pkgdef:
            outp.printf(f'Unable to load pkgdef from [{opts.pkgfile}]')
            return 1
        if opts.save:
            outp.printf(f'File {opts.pkgfile} is treated as already built (--no-build); incompatible with --save.')
            return 1
    else:
        pkgdef = loadPkgProto(opts.pkgfile, opticdir=opts.optic, no_docs=opts.no_docs, compiled=opts.compiled)

    if opts.signas is not None:

        s_certdir.addCertPath(opts.certdir)
        certdir = s_certdir.getCertDir()

        pkey = certdir.getCodeKey(opts.signas)
        with io.open(certdir.getCodeCertPath(opts.signas)) as fd:
            cert = fd.read()

        sign = s_common.ehex(pkey.signitem(pkgdef))

        pkgdef['codesign'] = {
            'cert': cert,
            'sign': sign,
        }

    s_schemas.reqValidPkgdef(pkgdef)

    if not opts.save and not opts.push:
        outp.printf('Neither --push nor --save provided.  Nothing to do.')
        return 1

    if opts.save:
        s_json.jssave(pkgdef, opts.save)

    if opts.push:

        async with s_telepath.withTeleEnv():

            async with await s_telepath.openurl(opts.push) as core:
                await core.addStormPkg(pkgdef, verify=opts.push_verify)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
