'''
Read manifests of Storm queries embedded in other source files.

A manifest is either JSON, ``{"queries": [<query>, ...]}``, or, when its path ends in ``.jsonl``, one
query object per line. Each query has ``path``, ``line`` and ``text`` keys and an optional ``site``.
'''
import itertools

import synapse.exc as s_exc

import synapse.lib.json as s_json
import synapse.lib.config as s_config

# JSONL lines are parsed one at a time but validated in chunks of this many
CHUNK_SIZE = 500

QUERY_SCHEMA = {
    'type': 'object',
    'properties': {
        'path': {'type': 'string', 'minLength': 1},
        'line': {'type': 'integer', 'minimum': 1},
        'text': {'type': 'string'},
        'site': {'type': 'string', 'minLength': 1},
    },
    'required': ['path', 'line', 'text'],
    'additionalProperties': False,
}

MANIFEST_SCHEMA = {
    'type': 'object',
    'properties': {
        'queries': {
            'type': 'array',
            'items': QUERY_SCHEMA,
        },
    },
    'required': ['queries'],
}

reqValidQuery = s_config.getJsValidator(QUERY_SCHEMA)
reqValidQueries = s_config.getJsValidator({'type': 'array', 'items': QUERY_SCHEMA})
reqValidManifest = s_config.getJsValidator(MANIFEST_SCHEMA)

def iterManifest(path):
    '''
    Yield the query dicts listed in a JSON or JSONL Storm query manifest.

    Raises:
        synapse.exc.BadArg: The manifest can not be read or is not valid. A JSONL error names its line.
    '''
    try:
        if path.endswith('.jsonl'):
            yield from _iterJsonl(path)
            return

        with open(path, 'rb') as fd:
            info = reqValidManifest(s_json.load(fd))

    except OSError as e:
        raise s_exc.BadArg(mesg=str(e)) from None

    except (s_exc.BadJsonText, s_exc.SchemaViolation) as e:
        raise s_exc.BadArg(mesg=e.get('mesg')) from None

    yield from info['queries']

def _iterJsonl(path):

    with open(path, 'rb') as fd:

        lines = ((lineno, line) for lineno, line in enumerate(fd, start=1) if line.strip())

        while (chunk := list(itertools.islice(lines, CHUNK_SIZE))):

            items = []
            for lineno, line in chunk:
                try:
                    items.append(s_json.loads(line))
                except s_exc.BadJsonText as e:
                    raise s_exc.BadArg(mesg=f'line {lineno}: {e.get("mesg")}') from None

            try:
                yield from reqValidQueries(items)

            except s_exc.SchemaViolation:
                # Find the first invalid line to report it
                for (lineno, line), item in zip(chunk, items):
                    try:
                        reqValidQuery(item)
                    except s_exc.SchemaViolation as e:
                        raise s_exc.BadArg(mesg=f'line {lineno}: {e.get("mesg")}') from None
