import sys
import urllib
import asyncio
import logging
import pathlib
import argparse

import aiohttp

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.config as s_config

logger = logging.getLogger(__name__)

BASEDIR = s_data.path('jsonschemas')

def download_refs_handler(uri):
    '''
    This function downloads the JSON schema at the given URI, parses the given
    URI to get the path component, and then saves the referenced schema to the
    'jsonschemas' directory of synapse.data.

    This function runs its own asyncio loop for each URI being requested.
    '''
    ret = asyncio.run(_download_refs_handler(uri))
    return ret

async def _download_refs_handler(uri):

    try:
        parts = urllib.parse.urlparse(uri)
    except ValueError:
        raise s_exc.BadUrl(mesg=f'Malformed URI: {uri}.') from None

    filename = s_common.genpath(BASEDIR, parts.hostname, *parts.path.split('/'))
    filepath = pathlib.Path(filename)

    # Check for path traversal. Unlikely, but still check
    if not str(filepath.absolute()).startswith(BASEDIR):
        raise s_exc.BadArg(mesg=f'Path traversal in schema URL: {uri} ?')

    # If we already have the file, return it
    if filepath.exists():
        logger.info(f'Schema {uri} already exists in local cache, skipping.')
        with filepath.open() as fp:
            return s_json.load(fp)

    # Create parent directory structure if it doesn't already exist
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Get the data from the interwebs
    logger.info(f'Downloading schema from {uri}.')
    async with aiohttp.ClientSession() as session:
        async with session.get(uri) as resp:
            resp.raise_for_status()
            buf = await resp.read()

    data = s_json.loads(buf)

    # Save the json schema to disk
    with filepath.open('wb') as fp:
        s_json.dump(data, fp, indent=True)

    # Return the schema to satisfy fastjsonschema
    return data

def download_refs(schema):
    handlers = {
        'http': download_refs_handler,
        'https': download_refs_handler,
    }

    s_config.getJsValidator(schema, handlers=handlers)

def main(argv):
    with argv.schema.open() as fp:
        schema = s_json.load(fp)

    download_refs(schema)

    return 0

def parse_args(argv):
    desc = 'Locally cache external `$ref`s from a JSON schema file.'
    parser = argparse.ArgumentParser('synapse.utils.getrefs', description=desc)
    parser.add_argument('schema', help='The source schema to get `$ref`s from.', type=pathlib.Path)
    args = parser.parse_args(argv)
    return args

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, defval='DEBUG')
    argv = parse_args(sys.argv[1:])
    sys.exit(main(argv))
