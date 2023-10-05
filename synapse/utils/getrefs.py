import sys
import json
import urllib
import logging
import pathlib
import argparse

import requests

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.config as s_config

logger = logging.getLogger(__name__)

def download_refs_handler(uri):
    '''
    This function downloads the JSON schema at the given URI, parses the given
    URI to get the path component, and then saves the referenced schema to the
    'jsonschemas' directory of synapse.data.
    '''

    try:
        parts = urllib.parse.urlparse(uri)
    except ValueError:
        raise s_exc.BadUrl(mesg=f'Malformed URI: {uri}.') from None

    filename = s_data.path('jsonschemas', parts.hostname, *parts.path.split('/'))
    filepath = pathlib.Path(filename)

    # Check for path traversal. Unlikely, but still check
    if not str(filepath.absolute()).startswith(s_data.path('jsonschemas')):
        raise s_exc.BadArg(mesg=f'Path traversal in schema URL: {uri} ?')

    # If we already have the file, return it
    if filepath.exists():
        logger.info(f'Schema {uri} already exists in local cache, skipping.')
        with filepath.open() as fp:
            return json.load(fp)

    # Create parent directory structure if it doesn't already exist
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Get the data from the interwebs
    logger.info(f'Downloading schema from {uri}.')
    resp = requests.get(uri)
    data = resp.json()

    # Save the json schema to disk
    with filepath.open('w') as fp:
        json.dump(data, fp, indent=2)

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
        schema = json.load(fp)

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
