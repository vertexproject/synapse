import logging

import synapse.common as s_common

import synapse.lib.config as s_config

logger = logging.getLogger(__name__)

# TODO Ensure this is consistent with other documentation.
rstlvls = [
    ('#', {'over': True}),
    ('*', {'over': True}),
    ('=', {}),
    ('-', {}),
    ('^', {}),
]

stormtype_doc_schema = {
    'definitions': {

        'stormType': {
            'type': ['string', 'array', 'object'],
            'items': {'type': 'string'},
            'properties': {
                'name': {'type': 'string'},
                'desc': {'type': 'string'},
                'type': {'$ref': '#/definitions/stormType'},
                'args': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/stormType'}
                },
                'returns': {'$ref': '#/definitions/stormType'},
                'default': {'type': ['boolean', 'integer', 'string', 'null']},
            },
            'required': ['type'],
        },

        'stormtypeDoc': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'desc': {'type': 'string'},
                'type': {'$ref': '#/definitions/stormType'}
            }
        },

    },
    'type': 'object',
    'properties': {
        'path': {
            'type': 'array',
            'items': {
                'type': 'string'
            },
            'minItems': 1,
        },
        'desc': {
            'type': 'string'
        },
        'typename': {
            'type': 'string'
        },
        'locals': {
            'type': 'array',
            'items': {'$ref': '#/definitions/stormtypeDoc'},
        }
    },
}
reqValidStormTypeDoc = s_config.getJsValidator(stormtype_doc_schema)

class RstHelp:

    def __init__(self):
        self.lines = []

    def addHead(self, name, lvl=0, link=None):
        char, info = rstlvls[lvl]
        under = char * len(name)

        lines = []

        lines.append('')

        if link:
            lines.append('')
            lines.append(link)
            lines.append('')

        if info.get('over'):
            lines.append(under)

        lines.append(name)
        lines.append(under)
        lines.append('')

        self.addLines(*lines)

    def addLines(self, *lines):
        self.lines.extend(lines)

    def getRstText(self):
        return '\n'.join(self.lines)

def ljuster(ilines):
    '''Helper to lstrip lines of whitespace an appropriate amount.'''
    baseline = ilines[0]
    assert baseline != ''
    newbaseline = baseline.lstrip()
    assert newbaseline != ''
    diff = len(baseline) - len(newbaseline)
    assert diff >= 0
    newlines = [line[diff:] for line in ilines]
    return newlines

def scrubLines(lines):
    '''Remove any empty lines until we encounter non-empty linee'''
    newlines = []
    for line in lines:
        if line == '' and not newlines:
            continue
        newlines.append(line)

    return newlines

def getDoc(obj, errstr):
    '''Helper to get __doc__'''
    doc = getattr(obj, '__doc__')
    if doc is None:
        doc = f'No doc for {errstr}'
        logger.warning(doc)
    return doc

def cleanArgsRst(doc):
    '''Clean up args strings to be RST friendly.'''
    replaces = (('*args', '\\*args'),
                ('*vals', '\\*vals'),
                ('**info', '\\*\\*info'),
                ('**kwargs', '\\*\\*kwargs'),
                )
    for (new, old) in replaces:
        doc = doc.replace(new, old)
    return doc

def prepareRstLines(doc, cleanargs=False):
    '''Prepare a __doc__ string for RST lines.'''
    if cleanargs:
        doc = cleanArgsRst(doc)
    lines = doc.split('\n')
    lines = scrubLines(lines)
    lines = ljuster(lines)
    return lines


def getArgLines(rtype):
    lines = []
    args = rtype.get('args', ())
    assert args is not None

    if args == ():
        # Zero args
        return lines

    lines.append('\n')
    lines.append('Args:')
    for arg in args:
        name = arg.get('name')
        desc = arg.get('desc')
        atyp = arg.get('type')
        assert name is not None
        assert desc is not None
        assert atyp is not None

        if isinstance(atyp, str):
            line = f'    {name} ({atyp}): {desc}'
        elif isinstance(atyp, list):
            assert len(atyp) > 1
            for obj in atyp:
                assert isinstance(obj, str)
            tdata = ', '.join([f'``{obj}``' for obj in atyp])
            rline = f'The input type may one one of the following: {tdata}.'
            line = f'    {name}: {desc} {rline}'
        elif isinstance(atyp, dict):
            logger.warning('Fully declarative return types are not yet supported.')
            rline = f"The input type is derived from the declarative type ``{atyp}``."
            line = f'    {name}: {desc} {rline}'
        else:
            raise AssertionError(f'unknown argtype: {atyp}')

        lines.extend((line, '\n'))

    return lines

def genCallsig(rtype):
    items = []

    args = rtype.get('args', ())
    assert args is not None
    for arg in args:
        name = arg.get('name')
        defv = arg.get('default', s_common.novalu)

        item = name
        if defv is not s_common.novalu:
            item = f'{item}={defv}'

        items.append(item)

    ret = f"({', '.join(items)})"
    return ret

def getReturnLines(rtype):
    lines = []
    if isinstance(rtype, str):
        lines.append(f"The type is ``{rtype}``.")
    elif isinstance(rtype, list):
        assert len(rtype) > 1
        for obj in rtype:
            assert isinstance(obj, str)
        tdata = ', '.join([f'``{obj}``' for obj in rtype])
        lines.append(f'The type may one one of the following: {tdata}.')
    elif isinstance(rtype, dict):
        logger.warning('Fully declarative return types are not yet supported.')
        lines.append(f"The type is derived from the declarative type ``{rtype}``.")

    return lines

def docStormPrims2(page: RstHelp, docinfo, linkprefix: str, islib=False):

    for info in docinfo:

        reqValidStormTypeDoc(info)

        path = info.get('path')

        sname = '.'.join(path)

        link = f'.. _{linkprefix}-{sname.replace(":", "-")}:'  # XXX Rename to objlink or something

        safesname = sname.replace(':', '\\:')
        if islib:
            page.addHead(f"${safesname}", lvl=1, link=link)
        else:
            page.addHead(safesname, lvl=1, link=link)

        typedoc = info.get('desc')
        lines = prepareRstLines(typedoc)

        page.addLines(*lines)

        locls = info.get('locals')
        locls.sort(key=lambda x: x.get('name'))

        for locl in locls:

            name = locl.get('name')
            loclname = '.'.join((sname, name))
            desc = locl.get('desc')
            rtype = locl.get('type')
            assert desc is not None
            assert rtype is not None

            link = f'.. _{linkprefix}-{loclname.replace(":", ".").replace(".", "-")}:'

            if isinstance(rtype, dict):
                rname = rtype.get('type')
                assert rname == 'function', f'Unknown type: {loclname=} {rname=}'  # FIXME py38

                lines = prepareRstLines(desc, cleanargs=True)
                arglines = getArgLines(rtype)
                lines.extend(arglines)

                callsig = genCallsig(rtype)

                header = f'{name}{callsig}'
                header = header.replace('*', r'\*')

            else:
                header = name
                lines = prepareRstLines(desc)

                lines.extend(getReturnLines(rtype))

            if islib:
                header = '.'.join((safesname, header))
                header = f'${header}'

            page.addHead(header, lvl=2, link=link)
            page.addLines(*lines)

    return page
