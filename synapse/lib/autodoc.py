import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.config as s_config

logger = logging.getLogger(__name__)

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
                '_funcname': {'type': 'string',
                              'description': 'The name of the python function implementing the method.'},
                'name': {'type': 'string',
                         'description': 'For a function argument, the name of the argument.'},
                'desc': {'type': 'string',
                         'description': 'For a function argument or return value, the description of the value.'},
                'deprecated': {'$ref': '#/definitions/deprecatedItem'},
                'type': {'$ref': '#/definitions/stormType'},
                'args': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/stormType'},
                    'description': 'Arguments to document.',
                },
                'returns': {'$ref': '#/definitions/stormType',
                            'description': 'Function return types to document'},
                'default': {'type': ['boolean', 'integer', 'string', 'null'],
                            'description': 'For a function argument, the default value, if applicable.'},
            },
            'required': ['type'],
            'description': 'A multi-purpose container for holding types information. If this '
                           'is a string or list of strings, it represents simple return types.'
                           ' If it is a object, it should represent a function to generate '
                           'documentation for.',
            'additionalProperties': False,
        },
        'deprecatedItem': {
            'type': 'object',
            'properties': {
                'eolvers': {'type': 'string', 'minLength': 1,
                            'description': "The version which will not longer support the item."},
                'eoldate': {'type': 'string', 'minLength': 1,
                            'description': 'Optional string indicating Synapse releases after this date may no longer support the item.'},
                'mesg': {'type': ['string', 'null'], 'default': None,
                         'description': 'Optional message to include in the warning text.'}
            },
            'oneOf': [
                {
                    'required': ['eolvers'],
                    'not': {'required': ['eoldate']}
                },
                {
                    'required': ['eoldate'],
                    'not': {'required': ['eolvers']}
                }
            ],
            'additionalProperties': False,
        },
        'stormtypeDoc': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string',
                         'description': 'The name of the object.'},
                'desc': {'type': 'string',
                         'description': 'The docstring of the object.'},
                'deprecated': {'$ref': '#/definitions/deprecatedItem'},
                'type': {'$ref': '#/definitions/stormType'}
            },
            'additionalProperties': False,
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
            'description': 'The path of the object.'
        },
        'desc': {
            'type': 'string',
            'description': 'The doc for the object itself.'
        },
        'locals': {
            'type': 'array',
            'items': {'$ref': '#/definitions/stormtypeDoc'},
            'description': 'A list of attributes, functions, getters, and setters to document.',
        },
        'additionalProperties': False,
    },
}
reqValidStormTypeDoc = s_config.getJsValidator(stormtype_doc_schema)

class RstHelp:

    def __init__(self):
        self.lines = []

    def addHead(self, name, lvl=0, link=None, addprefixline=True, addsuffixline=True):
        char, info = rstlvls[lvl]
        under = char * len(name)

        lines = []

        if addprefixline:
            lines.append('')

        if link:
            lines.append('')
            lines.append(link)
            lines.append('')

        if info.get('over'):
            lines.append(under)

        lines.append(name)
        lines.append(under)
        if addsuffixline:
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

def prepareRstLines(doc):
    '''Prepare a desc string for RST lines.'''
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
        name = name.replace('*', '\\*')
        if isinstance(atyp, str):
            line = f'    {name} ({atyp}): {desc}'
        elif isinstance(atyp, (list, tuple)):
            assert len(atyp) > 1
            for obj in atyp:
                assert isinstance(obj, str)
            tdata = ', '.join([f'``{obj}``' for obj in atyp])
            rline = f'The input type may be one of the following: {tdata}.'
            line = f'    {name}: {desc} {rline}'
        elif isinstance(atyp, dict):
            logger.warning('Fully declarative input types are not yet supported.')
            rline = f"The input type is derived from the declarative type ``{atyp}``."
            line = f'    {name}: {desc} {rline}'
        else:
            raise AssertionError(f'unknown argtype: {atyp}')

        lines.extend((line, '\n'))

    return lines

def genDeprecationWarning(name, depr, runt=False):
    assert name is not None
    assert depr is not None
    lines = []
    if runt:
        lines.append('.. warning::')
    else:
        lines.append('Warning:')

    mesg = depr.get('mesg')
    date = depr.get('eoldate')
    vers = depr.get('eolvers')

    ws = ''
    if runt:
        ws = '   '

    if date:
        lines.append(f'{ws}``{name}`` has been deprecated and will be removed on or after {date}.')
    else:
        lines.append(f'{ws}``{name}`` has been deprecated and will be removed in version {vers}.')
    if mesg:
        lines.append(f'{ws}{mesg}')

    lines.append('\n')

    return lines

def runtimeGetArgLines(rtype):
    lines = []
    args = rtype.get('args', ())
    assert args is not None

    if args == ():
        # Zero args
        return lines

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
        elif isinstance(atyp, (list, tuple)):
            assert len(atyp) > 1
            for obj in atyp:
                assert isinstance(obj, str)
            tdata = ', '.join(atyp)
            rline = f'The input type may one one of the following: {tdata}.'
            line = f'    {name}: {desc} {rline}'
        elif isinstance(atyp, dict):
            logger.warning('Fully declarative input types are not yet supported.')
            rline = f"The input type is derived from the declarative type ``{atyp}``."
            line = f'    {name}: {desc} {rline}'
        else:
            raise AssertionError(f'unknown argtype: {atyp}')

        lines.append(line)

    return lines

def genCallsig(rtype):
    items = []

    args = rtype.get('args', ())
    assert args is not None
    for arg in args:
        name = arg.get('name')
        defv = arg.get('default', s_common.novalu)

        if defv is s_common.novalu:
            item = name
        elif defv is None:
            item = f'{name}=(null)'
        elif defv is True:
            item = f'{name}=(true)'
        elif defv is False:
            item = f'{name}=(false)'
        elif isinstance(defv, str):
            item = f'{name}={defv}'
        elif isinstance(defv, int):
            item = f'{name}=({defv})'
        else:  # pragma: no cover
            raise s_exc.BadArg(mesg=f'Failed to make call sig for {arg=}')

        items.append(item)

    ret = f"({', '.join(items)})"
    return ret

def getLink(sname, linkprefix, ref=False, suffix=None):
    sname = sname.replace(":", ".").replace(".", "-")
    if suffix:
        sname = f'{sname}-{suffix}'
    if ref:
        link = f':ref:`{linkprefix}-{sname}`'
    else:
        link = f'.. _{linkprefix}-{sname}:'
    return link

def getRtypeStr(rtype, known_types, types_prefix, suffix):
    if rtype in known_types:
        rtype = getLink(rtype, types_prefix, ref=True, suffix=suffix)
    else:
        rtype = f'``{rtype}``'
    return rtype

def getReturnLines(rtype, known_types=None, types_prefix=None, suffix=None, isstor=False):
    # Allow someone to plumb in name=Yields as a return type.
    lines = ['']
    whitespace = '   '
    if known_types is None:
        known_types = set()

    if isinstance(rtype, str):
        lines.append('Returns:')
        lines.append(f'    The type is {getRtypeStr(rtype, known_types, types_prefix, suffix)}.')
    elif isinstance(rtype, (list, tuple)):
        assert len(rtype) > 1
        tdata = ', '.join([f'{getRtypeStr(obj, known_types, types_prefix, suffix)}' for obj in rtype])
        lines.append('Returns:')
        lines.append(f'    The type may be one of the following: {tdata}.')
    elif isinstance(rtype, dict):
        returns = rtype.get('returns')
        assert returns is not None, f'Invalid returns for {rtype}'
        name = returns.get('name', 'Returns').title()

        desc = returns.get('desc')
        rettype = returns.get('type')

        lines.append(f'{name}:')
        # Now switch on the type.

        parts = [whitespace]
        if desc:
            parts.append(desc)

        if isinstance(rettype, str):
            parts.append(f"The return type is {getRtypeStr(rettype, known_types, types_prefix, suffix)}.")
        elif isinstance(rettype, (list, tuple)):
            assert len(rettype) > 1
            tdata = ', '.join([f'{getRtypeStr(obj, known_types, types_prefix, suffix)}' for obj in rettype])
            rline = f'The return type may be one of the following: {tdata}.'
            parts.append(rline)
        elif isinstance(rettype, dict):
            logger.warning('Fully declarative input types are not yet supported.')
            rline = f"The return type is derived from the declarative type ``{rettype}``."
            parts.append(rline)
        else:
            raise AssertionError(f'unknown return type: {rettype}')
        line = ' '.join(parts)
        lines.append(line)
    if isstor:
        line = f'{whitespace} When this is used to set the value, it does not have a return type.'
        lines.append(line)
    return lines

def runtimeGetReturnLines(rtype, isstor=False):
    # Allow someone to plumb in name=Yields as a return type.
    lines = ['']
    whitespace = '   '
    if isinstance(rtype, str):
        lines.append('Returns:')
        lines.append(f'    The type is {rtype}.')
    elif isinstance(rtype, (list, tuple)):
        assert len(rtype) > 1
        tdata = ', '.join(rtype)
        lines.append('Returns:')
        lines.append(f'    The type may be one of the following: {tdata}.')
    elif isinstance(rtype, dict):
        returns = rtype.get('returns')
        assert returns is not None, f'Invalid returns for {rtype}'
        name = returns.get('name', 'Returns')

        desc = returns.get('desc')
        rettype = returns.get('type')

        lines.append(f'{name}:')
        # Now switch on the type.

        parts = [whitespace]
        if desc:
            parts.append(desc)

        if isinstance(rettype, str):
            parts.append(f"The return type is {rettype}.")
        elif isinstance(rettype, (list, tuple)):
            assert len(rettype) > 1
            tdata = ', '.join(rettype)
            rline = f'The return type may be one of the following: {tdata}.'
            parts.append(rline)
        elif isinstance(rettype, dict):
            logger.warning('Fully declarative return types are not yet supported.')
            rline = f"The return type is derived from the declarative type ``{rettype}``."
            parts.append(rline)
        else:
            raise AssertionError(f'unknown return type: {rettype}')
        line = ' '.join(parts)
        lines.append(line)
    if isstor:
        line = f'{whitespace} When this is used to set the value, it does not have a return type.'
        lines.append(line)
    return lines

def docStormTypes(page, docinfo, linkprefix, islib=False, lvl=1,
                  known_types=None, types_prefix=None, types_suffix=None,
                  ):
    '''
    Process a list of StormTypes doc information to add them to an RstHelp object.

    Notes
        This will create internal hyperlink link targets for each header item. The
        link prefix string must be given with the ``linkprefix`` argument.

    Args:
        page (RstHelp): The RST page to add .
        docinfo (dict): A Stormtypes Doc.
        linkprefix (str): The RST link prefix string to use.
        islib (bool): Treat the data as a library. This will preface the header and
            attribute values with ``$`` and use full paths for attributes.
        lvl (int): The base header level to use when adding headers to the page.

    Returns:
        None
    '''

    if known_types is None:
        known_types = set()

    for info in docinfo:
        reqValidStormTypeDoc(info)

        path = info.get('path')

        sname = '.'.join(path)

        safesname = sname.replace(':', '\\:')
        if islib:
            link = getLink(sname, linkprefix)
            page.addHead(f"${safesname}", lvl=lvl, link=link)
        else:
            link = getLink(sname, linkprefix, suffix=types_suffix)
            page.addHead(safesname, lvl=lvl, link=link)

        typedoc = info.get('desc')
        lines = prepareRstLines(typedoc)

        page.addLines(*lines)

        locls = info.get('locals', ())
        locls = sorted(locls, key=lambda x: x.get('name'))
        libdepr = info.get('deprecated')

        for locl in locls:

            name = locl.get('name')
            loclname = '.'.join((sname, name))
            desc = locl.get('desc')
            rtype = locl.get('type')
            assert desc is not None
            assert rtype is not None

            link = f'.. _{linkprefix}-{loclname.replace(":", ".").replace(".", "-")}:'
            lines = []
            if depr := locl.get('deprecated'):
                lines.extend(genDeprecationWarning(f'${loclname}', depr, True))
            elif libdepr is not None:
                lines.extend(genDeprecationWarning(f'${loclname}', libdepr, True))

            if isinstance(rtype, dict):
                rname = rtype.get('type')

                if isinstance(rname, dict):
                    raise AssertionError(f'rname as dict not supported loclname={loclname} rname={rname}')

                isstor = False
                isfunc = False
                isgtor = False
                isctor = False

                if rname == 'ctor' or 'ctor' in rname:
                    isctor = True
                if rname == 'function' or 'function' in rname:
                    isfunc = True
                if rname == 'gtor' or 'gtor' in rname:
                    isgtor = True
                if rname == 'stor' or 'stor' in rname:
                    isstor = True

                lines.extend(prepareRstLines(desc))
                arglines = getArgLines(rtype)
                lines.extend(arglines)

                retlines = getReturnLines(rtype, known_types=known_types, types_prefix=types_prefix,
                                          suffix=types_suffix, isstor=isstor)
                lines.extend(retlines)

                callsig = ''
                if isfunc:
                    callsig = genCallsig(rtype)
                header = f'{name}{callsig}'
                header = header.replace('*', r'\*')

            else:
                header = name
                lines.extend(prepareRstLines(desc))

                retlines = getReturnLines(rtype, known_types=known_types, types_prefix=types_prefix,
                                          suffix=types_suffix)
                lines.extend(retlines)

            if islib:
                header = '.'.join((safesname, header))
                header = f'${header}'

            page.addHead(header, lvl=lvl + 1, link=link)

            page.addLines(*lines)

def runtimeDocStormTypes(page, docinfo, islib=False, lvl=1,
                         oneline=False,
                         addheader=True,
                         preamble=None,
                         ):
    '''
    Process a list of StormTypes doc information to add them to a RstHelp object.

    Used for Storm runtime help generation.

    Args:
        page (RstHelp): The RST page to add .
        docinfo (dict): A Stormtypes Doc.
        linkprefix (str): The RST link prefix string to use.
        islib (bool): Treat the data as a library. This will preface the header and
            attribute values with ``$`` and use full paths for attributes.
        lvl (int): The base header level to use when adding headers to the page.
        oneline (bool): Only display the first line of description. Omits local headers.
        preamble (list): Lines added after the header; and before locls.

    Returns:
        None
    '''
    if preamble is None:
        preamble = []

    for info in docinfo:
        reqValidStormTypeDoc(info)

        path = info.get('path')

        sname = '.'.join(path)

        if addheader:

            if islib:
                page.addHead(f"${sname}", lvl=lvl, addprefixline=False, addsuffixline=False)
            else:
                page.addHead(sname, lvl=lvl, addprefixline=False, addsuffixline=False)

            typedoc = info.get('desc')
            lines = prepareRstLines(typedoc)

            page.addLines(*lines)

        page.addLines(*preamble)

        libdepr = info.get('deprecated')
        locls = info.get('locals', ())
        locls = sorted(locls, key=lambda x: x.get('name'))

        funcs = []
        nofuncs = []

        for locl in locls:
            name = locl.get('name')
            loclname = '.'.join((sname, name))
            rtype = locl.get('type')

            if isinstance(rtype, dict):
                rname = rtype.get('type')

                if isinstance(rname, dict):
                    raise AssertionError(f'rname as dict not supported loclname={loclname} rname={rname}')

                isstor = False
                isfunc = False
                isgtor = False
                isctor = False

                if rname == 'ctor' or 'ctor' in rname:
                    isctor = True
                if rname == 'function' or 'function' in rname:
                    isfunc = True
                if rname == 'gtor' or 'gtor' in rname:
                    isgtor = True
                if rname == 'stor' or 'stor' in rname:
                    isstor = True

                if isfunc:
                    funcs.append((locl, isstor, isfunc, isgtor, isctor))
                else:
                    nofuncs.append((locl, isstor, isfunc, isgtor, isctor))
                continue

            nofuncs.append((locl, False, False, False, False))

        def renderer(locl, isstor, isfunc, isgtor, isctor):
            name = locl.get('name')
            loclname = '.'.join((sname, name))
            desc = locl.get('desc')
            rtype = locl.get('type')
            assert desc is not None
            assert rtype is not None

            lines = []
            if not oneline:
                if (depr := locl.get('deprecated')):
                    lines.extend(genDeprecationWarning(f'${loclname}', depr))
                elif libdepr is not None:
                    lines.extend(genDeprecationWarning(f'${loclname}', libdepr))

            if isinstance(rtype, dict):
                rname = rtype.get('type')

                if isinstance(rname, dict):
                    raise AssertionError(f'rname as dict not supported loclname={loclname} rname={rname}')

                lines.extend(prepareRstLines(desc))
                arglines = runtimeGetArgLines(rtype)
                lines.extend(arglines)

                retlines = runtimeGetReturnLines(rtype, isstor=isstor)
                lines.extend(retlines)

                callsig = ''
                if isfunc:
                    callsig = genCallsig(rtype)
                header = f'{name}{callsig}'

            else:
                header = name
                lines.extend(prepareRstLines(desc))

                retlines = runtimeGetReturnLines(rtype)
                lines.extend(retlines)

            if islib:
                header = '.'.join((sname, header))
                header = f'${header}'

            if oneline:
                page.addLines(header, lines[0], '')
            else:
                page.addHead(header, lvl=lvl + 1, addsuffixline=False)
                page.addLines(*lines)

        more_than_one_item = (len(funcs) + len(nofuncs)) > 1

        if funcs:
            if more_than_one_item:
                page.addLines('The following functions are available:', '')
            for locl, isstor, isfunc, isgtor, isctor in funcs:
                renderer(locl, isstor, isfunc, isgtor, isctor)

        if nofuncs:
            if more_than_one_item:
                page.addLines('', 'The following references are available:', '')
            for locl, isstor, isfunc, isgtor, isctor in nofuncs:
                renderer(locl, isstor, isfunc, isgtor, isctor)

        return
