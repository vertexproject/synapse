import io
import os
import base64
import hashlib
import logging

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.json as s_json
import synapse.lib.const as s_const
import synapse.lib.config as s_config
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.version as s_version
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.tinfoil as s_tinfoil

logger = logging.getLogger(__name__)

wflownamere = regex.compile(r'^([\w-]+)\.yaml$')

def getStormStr(fn):
    if not os.path.isfile(fn):
        raise s_exc.NoSuchFile(mesg='Storm file {} not found'.format(fn), path=fn)

    with open(fn, 'rb') as f:
        return f.read().decode()

def getFileSha256(path):
    '''
    Get the SHA256 hash of a file's contents.

    Args:
        path (str): Path to the file on disk.

    Returns:
        str: The hex encoded SHA256 hash of the file contents.
    '''
    if not os.path.isfile(path):
        raise s_exc.NoSuchFile(mesg=f'Package file {path} not found', path=path)

    hashy = hashlib.sha256()

    with open(path, 'rb') as fd:
        while (byts := fd.read(s_const.mebibyte)):
            hashy.update(byts)

    return s_common.ehex(hashy.digest())

def iterPkgProtoFiles(path):
    '''
    Yield (path, filepath) tuples for the files shipped by a Storm Package prototype.

    Notes:
        A package ships everything under the ``files`` directory beside its .yaml file.
        Each entry's path is relative to that directory, so it is stable across rebuilds
        no matter how the file contents change.

    Args:
        path (str): Path to the package .yaml file on disk.

    Yields:
        (str, str): The package relative path and the full path of each file.
    '''
    full = s_common.genpath(path)
    if not os.path.isfile(full):
        raise s_exc.NoSuchFile(mesg=f'File {full} does not exist.', path=full)

    filesdir = s_common.genpath(os.path.dirname(full), 'files')
    if not os.path.isdir(filesdir):
        return

    # walk in a stable order so a rebuild produces the same package definition.
    # sorting dirs in place is what steers the traversal order.
    for root, dirs, names in os.walk(filesdir):

        dirs.sort()

        for name in sorted(names):
            fullpath = os.path.join(root, name)
            relpath = os.path.relpath(fullpath, filesdir)
            yield relpath.replace(os.sep, '/'), fullpath

def getPkgProtoFiles(path):
    '''
    Get a dict of package relative path to full path for the files shipped by a
    Storm Package prototype.

    Notes:
        A Storm service uses this to serve the files declared by the package it delivers.

    Args:
        path (str): Path to the package .yaml file on disk.

    Returns:
        dict: Maps each file's package relative path to its full path on disk.
    '''
    return dict(iterPkgProtoFiles(path))

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

def tryLoadPkgProto(fp, readonly=False, encryption=False):
    '''
    Get a Storm Package prototype from disk.

    Args:
        fp (str): Path to the package .yaml file on disk.
        readonly (bool): If set, open files in read-only mode. If files are missing, that will raise a NoSuchFile
                         exception.
        encryption (bool): If set, encrypt the Storm queries within package modules and commands.

    Returns:
        dict: A Storm package definition.
    '''
    return loadPkgProto(fp, readonly=readonly, encryption=encryption)

def reqSvcPkgProto(path, readonly=True):
    '''
    Get the Storm Package prototype a Storm service delivers, requiring the advanced flag.

    Notes:
        A Storm service delivers an advanced power-up, which is deployed as a service rather
        than installed as a package. The flag is what the Vertex Hub uses to present it that
        way, so a service confirms its own package declares it rather than shipping one the
        Hub would mis-classify.

    Args:
        path (str): Path to the package .yaml file on disk.
        readonly (bool): If set, open files in read-only mode.

    Returns:
        dict: A Storm package definition.
    '''
    pkgdef = tryLoadPkgProto(path, readonly=readonly)

    if pkgdef.get('advanced') is not True:
        mesg = f'Storm service package {pkgdef.get("name")} must declare advanced: true.'
        raise s_exc.BadPkgDef(mesg=mesg, name=pkgdef.get('name'))

    return pkgdef

def loadPkgProto(path, readonly=False, encryption=False, encpubkey=None):
    '''
    Get a Storm Package definition from disk.

    Args:
        path (str): Path to the package .yaml file on disk.
        readonly (bool): If set, open files in read-only mode. If files are missing, that will raise a NoSuchFile
                         exception.
        encryption (bool): If set, encrypt the Storm queries within package modules and commands.
        encpubkey (s_rsa.PubKey): If set, encrypt the package for a specific deployment by encrypting
                                  the seed with the deployment's RSA public key (implies encryption).

    Returns:
        dict: A Storm package definition.
    '''

    full = s_common.genpath(path)
    pkgdef = s_common.yamlload(full)
    if pkgdef is None:
        raise s_exc.NoSuchFile(mesg=f'File {full} does not exist or is empty.', path=full)

    protodir = os.path.dirname(full)

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

    # everything under the files directory ships with the package. an entry may be
    # authored to carry additional fields for the file it names, but which files ship
    # is derived from that directory, so the section can never drift from what is
    # actually there.
    if (declared := pkgdef.get('files')) is None:
        declared = {}

    protofiles = dict(iterPkgProtoFiles(full))

    for path in declared:
        if path not in protofiles:
            mesg = f'The files section declares {path} which is not in the package files directory.'
            raise s_exc.BadPkgDef(mesg=mesg, path=path)

    # the file contents are never embedded in the package definition, only the path
    # they are served by ( which is the key ) and the SHA256 they are stored and
    # retrieved by. rebuilt in walk order so a rebuild produces the same definition
    # no matter what order the entries were authored in.
    filedefs = {}
    for (relpath, fullpath) in protofiles.items():

        if (filedef := declared.get(relpath)) is None:
            filedef = {}

        filedef['sha256'] = getFileSha256(fullpath)
        filedefs[relpath] = filedef

    if filedefs:
        pkgdef['files'] = filedefs

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

    # the package graph schema requires these, so a built package carries them
    # rather than relying on the Cortex or the validator to fill them in.
    for gdef in pkgdef.get('graphs', ()):
        for propname, propvalu in s_schemas.pkggraph_defaults.items():
            gdef.setdefault(propname, propvalu)

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

    if encryption or encpubkey is not None:
        seed = s_common.ehex(os.urandom(32))
        salt = s_common.ehex(os.urandom(32))
        hashname = s_tinfoil.STORM_PKG_PBKDF2_HASH
        iters = s_tinfoil.STORM_PKG_PBKDF2_ITERS

        for mod in pkgdef.get('modules', ()):
            mod['storm'] = s_tinfoil.encStorm(seed, salt, hashname, iters, mod['storm'])

        for cmd in pkgdef.get('commands', ()):
            cmd['storm'] = s_tinfoil.encStorm(seed, salt, hashname, iters, cmd['storm'])

        encdef = {
            'seed': seed,
            'salt': salt,
            'pbkdf2': {'iters': iters, 'hash': hashname},
        }

        # for a per-deployment package, encrypt the seed to the deployment's RSA
        # public key so only that deployment can recover it, and flag deploy=True
        if encpubkey is not None:
            encdef['seed'] = s_common.ehex(encpubkey.encrypt(seed.encode()))
            encdef['deploy'] = True

        pkgdef.setdefault('metadata', {})['encryption'] = encdef

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

def signPkgDef(pkgdef, signas, certdir='~/.syn/certs'):
    '''
    Add a code signature to a Storm Package definition.

    Args:
        pkgdef (dict): A Storm package definition.
        signas (str): The code signing identity to use.
        certdir (str): The certdir which contains the code signing identity.
    '''
    s_certdir.addCertPath(certdir)
    cdir = s_certdir.getCertDir()

    pkey = cdir.getCodeKey(signas)
    with io.open(cdir.getCodeCertPath(signas)) as fd:
        cert = fd.read()

    # the entire metadata value is excluded from the signed body
    signdef = s_msgpack.deepcopy(pkgdef)
    signdef.pop('metadata', None)

    sign = s_common.ehex(pkey.signitem(signdef))

    pkgdef.setdefault('metadata', {})['codesign'] = {
        'cert': cert,
        'sign': sign,
    }

async def pushPkgFiles(outp, core, pkgdef, protopath):
    '''
    Upload the files declared by a Storm Package into a Cortex Axon.

    Notes:
        The file contents are located using the package prototype, since a built package
        definition carries only each file's path and SHA256. An entry with no local file
        is warned about rather than skipped silently, since it may already be in the Axon.

    Args:
        outp (s_output.OutPut): The output object.
        core: A Cortex telepath proxy.
        pkgdef (dict): The built Storm package definition.
        protopath (str): Path to the package .yaml prototype.
    '''
    files = pkgdef.get('files')
    if not files:
        return

    filepaths = getPkgProtoFiles(protopath)

    for (path, filedef) in files.items():

        sha256 = filedef.get('sha256')

        fullpath = filepaths.get(path)
        if fullpath is None:
            outp.printf(f'WARNING: No local file for {path}; not uploaded.')
            continue

        # the files are content addressed, so an existing upload needs no repeat
        if await core.callStorm('return($lib.axon.has($sha256))', opts={'vars': {'sha256': sha256}}):
            outp.printf(f'Skipping existing file: {fullpath} ({sha256})')
            continue

        outp.printf(f'Uploading file: {fullpath} ({sha256})')

        async with await core.getAxonUpload() as upfd:

            with open(fullpath, 'rb') as fd:
                while (byts := fd.read(s_const.mebibyte)):
                    await upfd.write(byts)

            size, gotbyts = await upfd.save()

        # the file changed between being hashed and being uploaded, so the package
        # definition we are about to push does not match what the Axon now holds
        if (gotsha256 := s_common.ehex(gotbyts)) != sha256:
            mesg = f'Package file {fullpath} uploaded as {gotsha256}, expected {sha256}.'
            raise s_exc.BadPkgDef(mesg=mesg, sha256=sha256, gotsha256=gotsha256)


desc = 'A tool for generating/pushing storm packages from YAML prototypes.'

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.pkg.gen', outp=outp, description=desc)
    pars.add_argument('--push', metavar='<url>', help='A telepath URL of a Cortex.')
    pars.add_argument('--push-verify', default=False, action='store_true',
                      help='Tell the Cortex to verify the package signature.')
    pars.add_argument('--save', metavar='<path>', help='Save the completed package JSON to a file.')
    pars.add_argument('--signas', metavar='<name>', help='Specify a code signing identity to use from ~/.syn/certs/code.')
    pars.add_argument('--certdir', metavar='<dir>', default='~/.syn/certs',
                      help='Specify an alternate certdir to ~/.syn/certs.')
    pars.add_argument('--no-build', action='store_true',
                      help='Treat pkgfile argument as an already-built package')
    pars.add_argument('--encrypt', default=False, action='store_true',
                      help='Encrypt the Storm queries within package modules and commands.')
    pars.add_argument('--encrypt-pubkey', metavar='<path>',
                      help='Path to a PEM encoded RSA public key. Encrypts the package for that '
                           'specific deployment (implies --encrypt).')
    pars.add_argument('pkgfile', metavar='<pkgfile>',
                      help='Path to a storm package prototype .yaml file, or a completed package .json/.yaml file.')

    opts = pars.parse_args(argv)

    if opts.no_build:
        pkgdef = s_common.yamlload(opts.pkgfile)
        if not pkgdef:
            outp.printf(f'Unable to load pkgdef from [{opts.pkgfile}]')
            return 1
    else:
        encpubkey = None
        if opts.encrypt_pubkey is not None:
            with s_common.reqfile(opts.encrypt_pubkey) as fd:
                encpubkey = s_rsa.PubKey.load(fd.read(), fmt='pem')

        pkgdef = loadPkgProto(opts.pkgfile, encryption=opts.encrypt, encpubkey=encpubkey)

    if opts.signas is not None:
        signPkgDef(pkgdef, opts.signas, certdir=opts.certdir)

    s_schemas.reqValidPkgdef(pkgdef)

    if not opts.save and not opts.push:
        outp.printf('Neither --push nor --save provided.  Nothing to do.')
        return 1

    if opts.save:
        s_json.jssave(pkgdef, opts.save)

    if opts.push:

        async with s_telepath.withTeleEnv():

            async with await s_telepath.openurl(opts.push) as core:
                # the files must be in the Axon before an onload query may read them
                await pushPkgFiles(outp, core, pkgdef, opts.pkgfile)
                await core.addStormPkg(pkgdef, verify=opts.push_verify)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
