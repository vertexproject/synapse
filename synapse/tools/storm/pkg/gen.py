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
import synapse.lib.config as s_config
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.schemas as s_schemas
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

wflownamere = regex.compile(r'^([\w-]+)\.yaml$')

def getStormStr(fn):
    if not os.path.isfile(fn):
        raise s_exc.NoSuchFile(mesg='Storm file {} not found'.format(fn), path=fn)

    with open(fn, 'rb') as f:
        return f.read().decode()

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

def tryLoadPkgProto(fp, readonly=False):
    '''
    Try to get a Storm Package prototype from disk with or without inline documentation.

    Args:
        fp (str): Path to the package .yaml file on disk.
        readonly (bool): If set, open files in read-only mode. If files are missing, that will raise a NoSuchFile
                         exception.

    Returns:
        dict: A Storm package definition.
    '''
    try:
        return loadPkgProto(fp, readonly=readonly)
    except s_exc.NoSuchFile:
        return loadPkgProto(fp, no_docs=True, readonly=readonly)

def loadPkgProto(path, no_docs=False, readonly=False):
    '''
    Get a Storm Package definition from disk.

    Args:
        path (str): Path to the package .yaml file on disk.
        no_docs (bool): If true, omit inline documentation content if it is not present on disk.
        readonly (bool): If set, open files in read-only mode. If files are missing, that will raise a NoSuchFile
                         exception.

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
    pkgdef['build'].setdefault('synapse:version', s_version.version)
    pkgdef['build'].setdefault('synapse:commit', s_version.commit)

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

        # A module loads its storm from a python package asset (package + path),
        # a file (path), or by convention from storm/modules/<name>.storm.
        modpkg = mod.pop('package', None)
        modpth = mod.pop('path', None)

        if modpkg is not None:
            mod['storm'] = s_dyndeps.reqDynMod(modpkg).getAssetStr(modpth)

        elif modpth is not None:
            if not os.path.isabs(modpth):
                modpth = os.path.join(protodir, modpth)
            mod['storm'] = getStormStr(modpth)

        else:
            name = f'{mod.get("name")}.storm'
            mod_path = s_common.genpath(protodir, 'storm', 'modules', name)
            if readonly:
                mod['storm'] = getStormStr(mod_path)
            else:
                with s_common.genfile(mod_path) as fd:
                    mod['storm'] = fd.read().decode()

    for cmd in pkgdef.get('commands', ()):

        name = f'{cmd.get("name")}.storm'

        cmd_path = s_common.genpath(protodir, 'storm', 'commands', name)
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

    s_schemas.reqValidPkgdef(pkgdef)

    # the pkgdef schema treats each vault type schema as an opaque object; check
    # it is a well-formed JSON Schema here (the Cortex does the same at type
    # registration) so a bad schema fails at build time rather than install time
    for vdef in (pkgdef.get('vaults') or {}).values():
        sch = vdef.get('schema')
        if sch is not None:
            s_config.validateSchemaDef(sch)

    # Ensure the package is json safe and tuplify it.
    s_json.reqjsonsafe(pkgdef)
    pkgdef = s_common.tuplify(pkgdef)
    return pkgdef


desc = 'A tool for generating/pushing storm packages from YAML prototypes.'

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.pkg.gen', outp=outp, description=desc)
    pars.add_argument('--push', metavar='<url>', help='A telepath URL of a Cortex or PkgRepo.')
    pars.add_argument('--push-verify', default=False, action='store_true',
                      help='Tell the Cortex to verify the package signature.')
    pars.add_argument('--save', metavar='<path>', help='Save the completed package JSON to a file.')
    pars.add_argument('--signas', metavar='<name>', help='Specify a code signing identity to use from ~/.syn/certs/code.')
    pars.add_argument('--certdir', metavar='<dir>', default='~/.syn/certs',
                      help='Specify an alternate certdir to ~/.syn/certs.')
    pars.add_argument('--no-build', action='store_true',
                      help='Treat pkgfile argument as an already-built package')
    pars.add_argument('--no-docs', default=False, action='store_true',
                      help='Do not require docs to be present and replace any doc content with empty strings.')
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
        pkgdef = loadPkgProto(opts.pkgfile, no_docs=opts.no_docs)

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
