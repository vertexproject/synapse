import os

import aiohttp

import synapse.exc as s_exc

import synapse.lib.cmd as s_cmd
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.httpapi as s_httpapi
import synapse.lib.schemas as s_schemas

import synapse.tools.storm.pkg.doc as s_gendocs
import synapse.tools.storm.pkg.gen as s_genpkg

PKGS_PATH = '/api/v3/hub/packages'

APIKEY_ENVAR = 'VERTEX_HUB_APIKEY'

# the same hub a Cortex installs from ( see Cortex._vertex_hub_url )
HUB_URL = 'https://hub.vertex.link'

def getRestData(byts):
    '''
    Parse a REST response body, returning None if it is not JSON at all.

    Args:
        byts (bytes): The response body.

    Returns:
        The parsed JSON body, or None.
    '''
    try:
        return s_json.loads(byts)
    except s_exc.BadJsonText:
        return None

async def uploadPkgFiles(outp, sess, baseurl, pkgdef, protopath):
    '''
    Upload the files declared by a Storm Package to the Vertex Hub.

    Notes:
        The file contents are located using the package prototype, since a built package
        definition carries only each file's SHA256.

    Args:
        outp (s_output.OutPut): The output object.
        sess (aiohttp.ClientSession): The client session.
        baseurl (str): The Vertex Hub base URL.
        pkgdef (dict): The built Storm package definition.
        protopath (str): Path to the package .yaml prototype.

    Raises:
        synapse.exc.SynErr: If the Vertex Hub rejects an upload.
    '''
    name = pkgdef.get('name')
    version = pkgdef.get('version')

    # the hub stores a package file by the sha256 the package declares, while the
    # prototype locates the contents by the path the file is served under
    filepaths = s_genpkg.getPkgProtoFiles(protopath)

    if (files := pkgdef.get('files')) is None:
        return

    for (path, filedef) in files.items():

        sha256 = filedef.get('sha256')

        fullpath = filepaths.get(path)
        if fullpath is None:  # pragma: no cover
            outp.printf(f'WARNING: No local file for {path}; not uploaded.')
            continue

        url = f'{baseurl}{PKGS_PATH}/{name}/{version}/files/{sha256}'

        # the files are content addressed, so an existing upload needs no repeat
        async with sess.head(url) as resp:
            if resp.status == 200:
                outp.printf(f'Skipping existing file: {fullpath} ({sha256})')
                continue

        outp.printf(f'Uploading file: {fullpath} ({sha256})')

        with open(fullpath, 'rb') as fd:
            headers = {'Content-Type': 'application/octet-stream'}
            async with sess.put(url, data=fd, headers=headers) as resp:
                data = await resp.read()

            s_httpapi.result(resp.status, getRestData(data))

async def publishPkgDef(outp, sess, baseurl, pkgdef):
    '''
    Publish a Storm Package definition to the Vertex Hub.

    Args:
        outp (s_output.OutPut): The output object.
        sess (aiohttp.ClientSession): The client session.
        baseurl (str): The Vertex Hub base URL.
        pkgdef (dict): The built Storm package definition.

    Raises:
        synapse.exc.SynErr: If the Vertex Hub rejects the package.
    '''
    url = f'{baseurl}{PKGS_PATH}'

    outp.printf(f'Publishing package to {url}')

    headers = {'Content-Type': 'application/json'}
    async with sess.post(url, data=s_json.dumps(pkgdef), headers=headers) as resp:
        data = await resp.read()

    retn = s_httpapi.result(resp.status, getRestData(data))
    outp.printf(f'Published package iden {retn.get("iden")}')

desc = '''
A tool for publishing a storm package to the Vertex Hub from a YAML prototype.

The package documentation is built first via synapse.tools.storm.pkg.doc, which does nothing
for a package that ships no docs directory. The Storm queries within the package modules and
commands are always encrypted. The package files are uploaded before the package definition
is published, so the Vertex Hub always has the file contents of a published package. The api
key must belong to a Vertex Hub account with the builder role.
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.pkg.publish', outp=outp, description=desc)
    pars.add_argument('--url', metavar='<url>', default=HUB_URL,
                      help=f'The base URL of the Vertex Hub. Defaults to {HUB_URL}.')
    pars.add_argument('--apikey', metavar='<key>',
                      help=f'A Vertex Hub api key with the builder role. Defaults to ${APIKEY_ENVAR}. '
                           'A key beginning with "-" must be given as --apikey=<key>.')
    pars.add_argument('--signas', metavar='<name>', help='Specify a code signing identity to use from ~/.syn/certs/code.')
    pars.add_argument('--certdir', metavar='<dir>', default='~/.syn/certs',
                      help='Specify an alternate certdir to ~/.syn/certs.')
    pars.add_argument('pkgfile', metavar='<pkgfile>',
                      help='Path to a storm package prototype .yaml file.')

    opts = pars.parse_args(argv)

    apikey = opts.apikey
    if apikey is None:
        apikey = os.getenv(APIKEY_ENVAR)

    if apikey is None:
        outp.printf(f'An api key is required. Use --apikey or set ${APIKEY_ENVAR}.')
        return 1

    # build the docs first (synapse.tools.storm.pkg.doc.buildPkgDocs); a package's
    # docs/ sources render into files/docs, so they are declared/published
    # alongside every other file under files/ (see genpkg.iterPkgProtoFiles).
    # Documentation is optional: a package with no docs/ directory builds
    # nothing here and publishes with no doc pages.
    await s_gendocs.buildPkgDocs(opts.pkgfile)

    # a published package always has its Storm queries encrypted
    pkgdef = s_genpkg.loadPkgProto(opts.pkgfile, encryption=True)

    if opts.signas is not None:
        s_genpkg.signPkgDef(pkgdef, opts.signas, certdir=opts.certdir)

    s_schemas.reqValidPkgdef(pkgdef)

    baseurl = opts.url.rstrip('/')

    headers = {'X-API-KEY': apikey}

    async with aiohttp.ClientSession(headers=headers) as sess:
        await uploadPkgFiles(outp, sess, baseurl, pkgdef, opts.pkgfile)
        await publishPkgDef(outp, sess, baseurl, pkgdef)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
