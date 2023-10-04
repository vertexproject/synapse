import os
import sys
import json
import urllib
import aiohttp
import logging
import argparse

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.config as s_config

logger = logging.getLogger(__name__)

def download_refs(uri):
    '''
    This function downloads the JSON schema at the given URI, parses the given
    URI to get the path component, and then saves the referenced schema to the
    'jsonschemas' directory of synapse.data.
    '''

    try:
        parts = urllib.parse.urlparse(uri)
    except ValueError:
        raise s_exc.BadUrl(f'Malformed URI: {uri}.') from None

    filename = s_data.path('jsonschemas', *parts.path.split('/'))
    if not os.path.exists(filename) or not os.path.isfile(filename):
        raise s_exc.NoSuchFile(f'Local JSON schema not found for {uri}.')

    # Check for path traversal. Unlikely, but still check
    if not filename.startswith(s_data.path('jsonschemas')):
        raise s_exc.BadArg(f'Path traversal in schema URL: {uri}.')

    async with aiohttp.ClientSession() as session:
        async with session.get('http://python.org') as response:

            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

            html = await response.text()
            print("Body:", html[:15], "...")

    with open(filename, 'r') as fp:
        return json.load(fp)

handlers = {
    'http': download_refs,
    'https': download_refs,
}

def main(argv):
    return 0

def parse_args(argv):
    desc = 'Locally cache external `$ref`s from a JSON schema file.'
    parser = argparse.ArgumentParser('synapse.tools.getrefs', description=desc)
    parser.add_argument('schema', help='The source schema to get `$ref`s from.')
    args = parser.parse_args(argv)
    return args

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, defval='DEBUG')
    argv = parse_args(sys.argv[1:])
    sys.exit(main(argv))
