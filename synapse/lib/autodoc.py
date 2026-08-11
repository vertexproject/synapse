import copy
import inspect
import logging
import collections

from typing import List, Tuple, Dict, Union

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.config as s_config
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.version as s_version
import synapse.lib.stormtypes as s_stormtypes

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
                'default': {'type': ['boolean', 'integer', 'string', 'null', 'array'],
                            'items': {'type': ['boolean', 'integer', 'string', 'null']},
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
        'deprecated': {
            'anyOf': [
                {'type': 'null'},
                {'$ref': '#/definitions/deprecatedItem'},
            ],
            'description': 'Deprecation information for the object itself, if any.',
        },
    },
    'additionalProperties': False,
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

_callsig_escapes = {
    '\b': '\\b',
    '\t': '\\t',
    '\n': '\\n',
    '\f': '\\f',
    '\r': '\\r',
    '"': '\\"',
    '\\': '\\\\',
}

def _genCallsigStr(defv):
    '''
    Render a string default as the Storm string literal a caller would type for it.

    A string is always quoted. A bare token is valid Storm for many values but not all
    of them, and the ones it silently mangles ( an empty string, a comparison operator
    such as ``=``, anything containing whitespace or a comma ) are not distinguishable
    from a safe value without reimplementing the grammar.

    Of the three Storm string forms, only the double quoted one can represent every
    value. The single and triple quoted forms are raw, so neither can hold its own
    delimiter, and the triple quoted regex is non greedy besides. The double quoted
    form is decoded by parser.unescape(), which is ast.literal_eval, so it carries
    Python string literal semantics where only a backslash and a double quote are
    special. Escaping those two plus every control character therefore makes this
    total, rather than an enumeration of the cases someone has thought of. The single
    quoted form is kept only because it reads better for the values it can hold.

    The one value that cannot be expressed is the text ``$lib.undef``, which is
    reserved below to document the undef constant.
    '''
    # $lib.undef is declared as a string but documents the undef constant, which is a
    # variable reference rather than a value. See StormTypesRegistry._validateFunction.
    # A default whose real value is that text renders as the constant instead, which no
    # declaration in the tree has and which this deliberately does not try to resolve.
    if defv == '$lib.undef':
        return defv

    # a single quoted string is raw, so anything it cannot hold -- a single quote, or a
    # control character -- uses the double quoted form.
    if regex.search(r"['\x00-\x1f\x7f]", defv):

        chars = []
        for char in defv:
            esc = _callsig_escapes.get(char)
            if esc is None and (char < ' ' or char == '\x7f'):
                esc = f'\\u{ord(char):04x}'

            chars.append(char if esc is None else esc)

        valu = ''.join(chars)
        return f'"{valu}"'

    return f"'{defv}'"

def _genCallsigDefv(defv):
    '''
    Render a default value as the Storm literal a caller would type for it.
    '''
    # bool must be checked before int, since bool is a subclass of int.
    if defv is None:
        return '(null)'

    if defv is True:
        return '(true)'

    if defv is False:
        return '(false)'

    if isinstance(defv, str):
        return _genCallsigStr(defv)

    if isinstance(defv, int):
        return f'({defv})'

    if isinstance(defv, (list, tuple)):
        # a single item list literal requires a trailing comma; (foo) is not a list.
        valus = ', '.join([_genCallsigDefv(v) for v in defv])
        if len(defv) == 1:
            valus = f'{valus},'

        return f'({valus})'

    raise s_exc.BadArg(mesg=f'Failed to make call sig for {defv=}')

def genCallsig(rtype):
    items = []

    args = rtype.get('args', ())
    assert args is not None
    for arg in args:
        name = arg.get('name')
        defv = arg.get('default', s_common.novalu)

        if defv is s_common.novalu:
            item = name
        else:
            item = f'{name}={_genCallsigDefv(defv)}'

        items.append(item)

    ret = f"({', '.join(items)})"
    return ret

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

_slug_strip_re = regex.compile(r'[^\p{L}\p{N}\-_\s]+', flags=regex.UNICODE)

def mdSlugify(text, seen=None):
    '''
    Port of frontend/src/ts/optic/utils/markdown/slug.ts -- GFM-style heading
    anchor slug generation, kept byte-for-byte compatible so cross-links
    generated by hand-authored markdown (Stage 2-4 content) resolve the same
    way in the Optic client-side renderer (Stage 5) as they do here.

    Args:
        text (str): The heading text to slugify.
        seen (dict or None): Mutable dedup counter map, shared across all
            headings rendered on one page. Pass the same dict for every
            heading in a document to get GitHub's -1/-2/... disambiguation.

    Returns:
        str: The slug.
    '''
    base = _slug_strip_re.sub('', text.lower()).strip()
    base = regex.sub(r'\s+', '-', base)

    if seen is None:
        return base

    count = seen.get(base, 0)
    seen[base] = count + 1

    return base if count == 0 else f'{base}-{count}'

class MdHelp:
    '''
    Markdown analog of RstHelp, used by the doc*Md page generators below.
    RstHelp itself is untouched -- it remains in live use by
    synapse/lib/storm.py for interactive Storm CLI help text.
    '''

    def __init__(self):
        self.lines = []

    def addHead(self, name, lvl=0, anchor=None, addprefixline=True, addsuffixline=True):
        lines = []

        if addprefixline:
            lines.append('')

        if anchor:
            lines.append(f'<a id="{anchor}"></a>')
            lines.append('')

        lines.append(f'{"#" * (lvl + 1)} {name}')

        if addsuffixline:
            lines.append('')

        self.addLines(*lines)

    def addLines(self, *lines):
        self.lines.extend(lines)

    def getMdText(self):
        return '\n'.join(self.lines)

def _mdAnchorName(sname):
    return sname.replace(':', '-').replace('.', '-')

def getMdLink(sname, linkprefix, suffix=None):
    '''
    Compute the explicit anchor id for a given source name, mirroring the
    old RST getLink()'s target-name half (the `.. _prefix-name:` side).

    Args:
        sname (str): The dotted/colon source name (e.g. "inet:fqdn").
        linkprefix (str): The namespace prefix (e.g. "dm-type", "stormprims").
        suffix (str or None): Optional disambiguation suffix.

    Returns:
        str: The anchor id, e.g. "dm-type-inet-fqdn".
    '''
    name = _mdAnchorName(sname)
    if suffix:
        name = f'{name}-{suffix}'
    return f'{linkprefix}-{name}'

def mdRef(text, anchorid, mdfile=None):
    '''
    Render an inline markdown link to an explicit anchor id, optionally in
    another file (cross-file reference).

    Args:
        text (str): The visible link text (no markdown escaping applied by
            this helper -- callers pass pre-escaped/backtick-wrapped text).
        anchorid (str): The target anchor id (see getMdLink).
        mdfile (str or None): The relative path to the target file, or None
            for a same-file link.

    Returns:
        str: The markdown link, e.g. "[`inet:fqdn`](#dm-type-inet-fqdn)" or
            "[`inet:fqdn`](datamodel_types.md#dm-type-inet-fqdn)".
    '''
    target = f'{mdfile}#{anchorid}' if mdfile else f'#{anchorid}'
    return f'[`{text}`]({target})'

def getRtypeStrMd(rtype, known_types, types_prefix, suffix, mdfile=None):
    if rtype in known_types:
        anchorid = getMdLink(rtype, types_prefix, suffix=suffix)
        return mdRef(rtype, anchorid, mdfile=mdfile)
    return f'`{rtype}`'

def getArgLinesMd(rtype):
    lines = []
    args = rtype.get('args', ())

    if args == ():
        return lines

    lines.append('')
    lines.append('**Args:**')
    lines.append('')
    for arg in args:
        name = arg.get('name')
        desc = arg.get('desc')
        atyp = arg.get('type')

        if isinstance(atyp, str):
            line = f'- `{name}` (`{atyp}`): {desc}'
        elif isinstance(atyp, (list, tuple)):
            tdata = ', '.join([f'`{obj}`' for obj in atyp])
            line = f'- `{name}`: {desc} The input type may be one of the following: {tdata}.'
        elif isinstance(atyp, dict):
            logger.warning('Fully declarative input types are not yet supported.')
            line = f'- `{name}`: {desc} The input type is derived from the declarative type `{atyp}`.'
        else:
            raise s_exc.BadArg(mesg=f'unknown argtype: {atyp}')

        lines.append(line)

    lines.append('')
    return lines

def getReturnLinesMd(rtype, known_types=None, types_prefix=None, suffix=None, isstor=False, mdfile=None):
    lines = ['']
    if known_types is None:
        known_types = set()

    if isinstance(rtype, str):
        lines.append('**Returns:**')
        lines.append(f'The type is {getRtypeStrMd(rtype, known_types, types_prefix, suffix, mdfile=mdfile)}.')
    elif isinstance(rtype, (list, tuple)):
        tdata = ', '.join([getRtypeStrMd(obj, known_types, types_prefix, suffix, mdfile=mdfile) for obj in rtype])
        lines.append('**Returns:**')
        lines.append(f'The type may be one of the following: {tdata}.')
    elif isinstance(rtype, dict):
        returns = rtype.get('returns')
        if returns is None:
            raise s_exc.BadArg(mesg=f'Invalid returns for {rtype}')
        name = returns.get('name', 'Returns').title()

        desc = returns.get('desc')
        rettype = returns.get('type')

        lines.append(f'**{name}:**')

        parts = []
        if desc:
            parts.append(desc)

        if isinstance(rettype, str):
            parts.append(f'The return type is {getRtypeStrMd(rettype, known_types, types_prefix, suffix, mdfile=mdfile)}.')
        elif isinstance(rettype, (list, tuple)):
            tdata = ', '.join([getRtypeStrMd(obj, known_types, types_prefix, suffix, mdfile=mdfile) for obj in rettype])
            parts.append(f'The return type may be one of the following: {tdata}.')
        elif isinstance(rettype, dict):
            logger.warning('Fully declarative input types are not yet supported.')
            parts.append(f'The return type is derived from the declarative type `{rettype}`.')
        else:
            raise s_exc.BadArg(mesg=f'unknown return type: {rettype}')

        lines.append(' '.join(parts))
    if isstor:
        lines.append('When this is used to set the value, it does not have a return type.')
    return lines

def genDeprecationWarningMd(name, depr):
    lines = ['> **Warning:**']

    mesg = depr.get('mesg')
    date = depr.get('eoldate')
    vers = depr.get('eolvers')

    if date:
        lines.append(f'> `{name}` has been deprecated and will be removed on or after {date}.')
    else:
        lines.append(f'> `{name}` has been deprecated and will be removed in version {vers}.')
    if mesg:
        lines.append(f'> {mesg}')

    lines.append('')
    return lines

def prepareMdLines(doc):
    '''Prepare a desc string for markdown lines (reuses the RST whitespace utilities, which are format-agnostic).'''
    lines = doc.split('\n')
    lines = scrubLines(lines)
    lines = ljuster(lines)
    return lines

def docStormTypesMd(md, docinfo, linkprefix, islib=False, lvl=1,
                    known_types=None, types_prefix=None, types_suffix=None, mdfile=None):
    '''
    Add a list of StormTypes doc information to an MdHelp page. Used by
    docStormTypesLibsMd/docStormTypesPrimsMd (whole-registry pages) and by
    the Storm runtime `help` command for individual libraries/types.

    Notes
        This will create explicit anchor ids for each header item. The
        anchor namespace prefix must be given with the ``linkprefix``
        argument.

    Args:
        md (MdHelp): The markdown page to add to.
        docinfo (dict): A Stormtypes Doc.
        linkprefix (str): The anchor namespace prefix string to use.
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

        if islib:
            anchor = getMdLink(sname, linkprefix)
            md.addHead(f'${sname}', lvl=lvl, anchor=anchor)
        else:
            anchor = getMdLink(sname, linkprefix, suffix=types_suffix)
            md.addHead(sname, lvl=lvl, anchor=anchor)

        typedoc = info.get('desc')
        lines = prepareMdLines(typedoc)
        md.addLines(*lines)

        locls = info.get('locals', ())
        locls = sorted(locls, key=lambda x: x.get('name'))
        libdepr = info.get('deprecated')

        for locl in locls:

            name = locl.get('name')
            loclname = '.'.join((sname, name))
            desc = locl.get('desc')
            rtype = locl.get('type')

            locl_anchor = _mdAnchorName(loclname)
            local_anchor_id = f'{linkprefix}-{locl_anchor}'

            lines = []
            if depr := locl.get('deprecated'):
                lines.extend(genDeprecationWarningMd(f'${loclname}', depr))
            elif libdepr is not None:
                lines.extend(genDeprecationWarningMd(f'${loclname}', libdepr))

            if isinstance(rtype, dict):
                rname = rtype.get('type')

                if isinstance(rname, dict):  # pragma: no cover
                    raise s_exc.BadArg(mesg=f'rname as dict not supported loclname={loclname} rname={rname}')

                isstor = 'stor' in rname
                isfunc = 'function' in rname

                lines.extend(prepareMdLines(desc))
                lines.extend(getArgLinesMd(rtype))
                lines.extend(getReturnLinesMd(rtype, known_types=known_types, types_prefix=types_prefix,
                                              suffix=types_suffix, isstor=isstor, mdfile=mdfile))

                callsig = genCallsig(rtype) if isfunc else ''
                header = f'{name}{callsig}'

            else:
                header = name
                lines.extend(prepareMdLines(desc))
                lines.extend(getReturnLinesMd(rtype, known_types=known_types, types_prefix=types_prefix,
                                              suffix=types_suffix, mdfile=mdfile))

            if islib:
                header = f'${sname}.{header}'

            md.addHead(header, lvl=lvl + 1, anchor=local_anchor_id)
            md.addLines(*lines)

# Google-style docstring sections recognized by parseApiDocstring/docApiMd.
# This is a lightweight, deliberately narrow subset of what Sphinx's
# napoleon extension supports -- just what the monorepo's Telepath API
# method docstrings (CellApi subclasses) actually use -- not a
# general-purpose Napoleon replacement.
_api_doc_sections = ('Args', 'Arguments', 'Returns', 'Yields', 'Raises', 'Examples', 'Example', 'Note', 'Notes')
_re_api_section_header = regex.compile(r'^(' + '|'.join(_api_doc_sections) + r'):\s*$')
_re_api_item = regex.compile(r'^(.+?)(?:\s*\(([^)]*)\))?:\s*(.*)$')

def parseApiDocstring(doc):
    '''
    Parse a Google-style docstring into a summary paragraph and an ordered
    list of (header, body-lines) sections. See _api_doc_sections for the
    recognized section headers.

    Args:
        doc (str): The docstring, as returned by inspect.getdoc() (already
            dedented and free of leading/trailing blank lines).

    Returns:
        (str, list): The summary text, and a list of (header, list-of-lines)
            tuples in document order.
    '''
    if not doc:
        return '', []

    summary = []
    sections = []
    curhead = None
    curlines = []

    for line in doc.splitlines():
        match = _re_api_section_header.match(line.strip())
        if match is not None:
            if curhead is not None:
                sections.append((curhead, curlines))
            else:
                summary = curlines
            curhead = match.group(1)
            curlines = []
            continue
        curlines.append(line)

    if curhead is not None:
        sections.append((curhead, curlines))
    else:
        summary = curlines

    summarytext = '\n'.join(summary).strip()
    return summarytext, sections

def _apiSectionItems(lines):
    '''
    Split an Args/Returns/Yields/Raises section body into items, one per
    top-level line matching "name (type): desc" or "name: desc" -- a
    continuation line (indented further than its item's first line) is
    folded into that item's description, and lines that never contained a
    top-level "name (type): desc" and appear before any item are dropped.

    Args:
        lines (list): The section's raw body lines.

    Returns:
        list: A list of {'name', 'type', 'desc'} dicts, in order.
    '''
    items = []
    curindent = None

    for line in lines:
        if not line.strip():
            continue

        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if items and curindent is not None and indent > curindent:
            items[-1]['desc'] = f"{items[-1]['desc']} {stripped}".strip()
            continue

        match = _re_api_item.match(stripped)
        if match is None:
            if items:
                items[-1]['desc'] = f"{items[-1]['desc']} {stripped}".strip()
            continue

        name, styp, desc = match.groups()
        items.append({'name': name, 'type': styp, 'desc': desc})
        curindent = indent

    return items

def renderApiItemsMd(lines, israises=False):
    '''
    Render an Args/Raises section's body as a Markdown bullet list, one
    bullet per parameter/exception.

    Args:
        lines (list): The section's raw body lines.
        israises (bool): True for a Raises section (bullets show only the
            exception name and description, no "type").

    Returns:
        list: Rendered Markdown lines.
    '''
    out = []
    for item in _apiSectionItems(lines):
        if israises or not item['type']:
            out.append(f"- **{item['name']}**: {item['desc']}")
        else:
            out.append(f"- **{item['name']}** (*{item['type']}*): {item['desc']}")
    return out

def renderApiReturnMd(lines):
    '''
    Render a Returns/Yields section's body as Markdown. Unlike Args/Raises,
    a Returns/Yields entry has no parameter name -- its leading token is the
    return type -- so each item renders as "*type*: desc" rather than a
    bulleted, bolded parameter.

    Args:
        lines (list): The section's raw body lines.

    Returns:
        list: Rendered Markdown lines.
    '''
    out = []
    for item in _apiSectionItems(lines):
        if item['type']:
            # "name (type): desc" is not the expected Returns/Yields shape,
            # but render it faithfully rather than silently dropping the type.
            out.append(f"*{item['name']} ({item['type']})*: {item['desc']}")
        else:
            out.append(f"*{item['name']}*: {item['desc']}")
    return out

def renderApiPassthroughMd(lines):
    '''
    Render an Examples/Note/Notes section's body as a Markdown blockquote --
    a reasonable generic fallback for free-form prose (and RST literal
    blocks, which this does not attempt to specially reformat).

    Args:
        lines (list): The section's raw body lines.

    Returns:
        list: Rendered Markdown lines.
    '''
    trimmed = list(lines)
    while trimmed and not trimmed[0].strip():
        trimmed.pop(0)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()

    return [f'> {line.strip()}' if line.strip() else '>' for line in trimmed]

# src / name / target
EdgeDef = Tuple[Union[str, None], str, Union[str, None]]
EdgeDict = Dict[str, str]
Edge = Tuple[EdgeDef, EdgeDict]
Edges = List[Edge]

poptsToWords = {
    'ex': 'Example',
    'computed': 'Computed',
    'deprecated': 'Deprecated',
    'disp': 'Display',
}

info_ignores = (
    'stortype',
    'bases',
    'custom',
    'template',
    'display',
    'deprecated',
    'props',
    'virts',
    'interfaces',
)

class DocHelp:
    '''
    Helper to pre-compute all doc strings hierarchically, for the data model
    Markdown generators (docModelTypesMd/docModelFormsMd).
    '''

    def __init__(self, ctors, types, forms, props, ifaces=()):
        self.ctors = {c[0]: c[3].get('doc', 'BaseType has no doc string.') for c in ctors}
        self.types = {name: valu['info'].get('doc', self.ctors.get(name)) for name, valu in types.items()}
        self.ifaces = {name: info.get('doc', '') for name, info in ifaces}
        self.forms = {f[0]: f[1].get('doc', self.types.get(f[0], self.ctors.get(f[0]))) for f in forms}

        self.props = {}
        for form, props in props.items():
            for prop in props:
                tn = prop[1][0]
                # A poly typedef has a tuple of constituents in the type slot (no single doc source).
                if isinstance(tn, str):
                    doc = prop[2].get('doc', self.forms.get(tn, self.types.get(tn, self.ifaces.get(tn, self.ctors.get(tn)))))
                else:
                    doc = prop[2].get('doc', '')
                self.props[(form, prop[0])] = doc

        ctord = {c[0]: c for c in ctors}
        self.formhelp = {}  # form name -> ex string for a given type
        for form in forms:
            formname = form[0]
            tnfo = types.get(formname)
            ctor = ctord.get(formname)
            if tnfo:
                example = tnfo['info'].get('ex')
                self.formhelp[formname] = example
            elif ctor:
                ctor = ctor[3]
                example = ctor.get('ex')
                self.formhelp[formname] = example
            else:  # pragma: no cover
                logger.warning(f'No ctor/type available for [{formname}]')

def processCtorsMd(md, dochelp, ctors, types):
    '''
    Args:
        md (MdHelp):
        dochelp (DocHelp):
        ctors (list):
        types (dict):

    Returns:
        None
    '''
    md.addHead('Base Types', lvl=1, anchor='dm-base-types')
    md.addLines('Base types are defined via Python classes.', '')

    for name, ctor, opts, info in ctors:

        doc = dochelp.ctors.get(name)
        if not doc.endswith('.'):
            logger.warning(f'Docstring for ctor {name} does not end with a period.]')
            doc = doc + '.'

        anchor = getMdLink(name, 'dm-type')
        md.addHead(name, lvl=2, anchor=anchor)

        md.addLines(doc, f'It is implemented by the following class: `{ctor}`.')
        _ = info.pop('doc', None)
        ex = info.pop('ex', None)
        if ex:
            md.addLines('', f'An example of `{name}`:', '', f'- `{ex}`')

        tnfo = types.get(name)
        if (virts := tnfo.get('virts')) is not None:
            md.addLines('', 'This type has the following virtual properties:', '')
            for virt in virts:
                md.addLines(f'- `{virt}`')

        md.addLines('', 'This type supports lifting using the following operators:', '')
        for cmpr in tnfo.get('lift_cmprs'):
            md.addLines(f'- `{cmpr}`')

        if opts:
            md.addLines('', f'The base type `{name}` has the following default options set:', '')
            for k, v in opts.items():
                md.addLines(f'- {k}: `{v}`')

        for key in info_ignores:
            info.pop(key, None)

        if info:
            logger.warning(f'Base type {name} has unhandled info: {info}')

def _renderEnumMd(valu):
    lines = ['', '| valu |', '|------|']
    if isinstance(valu, str):
        for enum in valu.split(','):
            lines.append(f'| {enum} |')
    elif isinstance(valu, (list, tuple)):
        valu = sorted(valu, key=lambda x: x[0])
        lines = ['', '| int | valu |', '|-----|------|']
        for (a, b) in valu:
            lines.append(f'| {a} | {b} |')
    else:  # pragma: no cover
        raise ValueError(f'Unknown enum type {type(valu)}')
    lines.append('')
    return lines

def processTypesMd(md, dochelp, types):
    '''
    Args:
        md (MdHelp):
        dochelp (DocHelp):
        types (dict):

    Returns:
        None
    '''
    md.addHead('Types', lvl=1, anchor='dm-types')
    md.addLines('Regular types are derived from BaseTypes.', '')

    for name, tnfo in types.items():
        if name in dochelp.ctors:
            continue

        doc = dochelp.types.get(name)
        if not doc.endswith('.'):
            logger.warning(f'Docstring for type {name} does not end with a period.]')
            doc = doc + '.'

        anchor = getMdLink(name, 'dm-type')
        md.addHead(name, lvl=2, anchor=anchor)

        info = tnfo['info']
        base_anchor = getMdLink(info['bases'][-1], 'dm-type')
        baseref = mdRef(info['bases'][-1], base_anchor)
        md.addLines(doc, f'The `{name}` type is derived from the base type: {baseref}.')

        ifaces = info.pop('interfaces', None)
        if ifaces:
            md.addLines('', 'This type implements the following interfaces:', '')
            for iface in ifaces:
                md.addLines(f'- `{iface}`')

        _ = info.pop('doc', None)
        ex = info.pop('ex', None)
        if ex:
            md.addLines('', f'An example of `{name}`:', '', f'- `{ex}`')

        if (opts := tnfo.get('opts')):
            md.addLines('', 'This type has the following options set:', '')

            for key, valu in sorted(opts.items(), key=lambda x: x[0]):
                if key == 'enums':
                    if valu is None:
                        continue
                    md.addLines(f'- {key}:')
                    md.addLines(*_renderEnumMd(valu))
                elif key in ('fields', 'schema'):
                    if len(str(valu)) < 80:
                        md.addLines(f'- {key}: `{valu}`')
                        continue
                    md.addLines(f'- {key}:', '', '```json')
                    md.addLines(s_json.dumps(valu, indent=True, sort_keys=True).decode())
                    md.addLines('```', '')
                else:
                    md.addLines(f'- {key}: `{valu}`')

        for key in info_ignores:
            info.pop(key, None)

        if info:
            logger.warning(f'Type {name} has unhandled info: {info}')

def processInterfacesMd(md, ifaces, knownnames=None):
    '''
    Emit markdown documentation for all model interfaces.

    Each interface gets a ``dm-type-<name>`` anchor so that
    ``processFormsPropsMd`` cross-references resolve correctly.

    Args:
        md (MdHelp): the markdown output helper (shared with
            processCtorsMd/processTypesMd).
        ifaces (list[tuple[str, dict]]): sorted (name, info) pairs from
            ``core.getModelDict()['interfaces']``.
        knownnames (set[str] or None): names that have a ``dm-type-<name>``
            anchor in this build. Used to skip emitting broken links for
            typenames produced by unresolved interface template defaults
            (e.g. empty strings or bare placeholders).

    Returns:
        None
    '''
    if knownnames is None:
        knownnames = set(name for name, _ in ifaces)

    def _typeref(tname, fallback):
        if not tname or '{' in tname or '}' in tname or tname not in knownnames:
            return f'`{tname}`' if tname else fallback
        anchor = getMdLink(tname, 'dm-type')
        return mdRef(tname, anchor)

    md.addHead('Interfaces', lvl=1, anchor='dm-interfaces')
    md.addLines('Interfaces define common properties inherited by multiple forms.', '')

    for name, info in ifaces:
        doc = info.get('doc', '')
        if not doc:
            doc = f'The `{name}` interface.'
        if not doc.endswith('.'):
            logger.warning(f'Docstring for interface {name} does not end with a period.')
            doc = doc + '.'

        anchor = getMdLink(name, 'dm-type')
        md.addHead(name, lvl=2, anchor=anchor)

        md.addLines(doc)

        parents = info.get('interfaces')
        if parents:
            md.addLines('', 'This interface extends the following interfaces:', '')
            for piface in parents:
                pifname = piface[0] if isinstance(piface, (tuple, list)) else piface
                md.addLines(f'- {_typeref(pifname, "`unknown`")}')

        props = info.get('props')
        if props:
            md.addLines('', 'This interface defines the following properties:', '')
            for pname, typedef, pinfo in sorted(props, key=lambda x: x[0]):
                pdoc = pinfo.get('doc', '')
                if not pdoc:
                    pdoc = f'The `{pname}` property.'
                if isinstance(typedef[0], (tuple, list)):
                    md.addLines(f'- `:{pname}` (poly) - {pdoc}')
                else:
                    ptname = typedef[0]
                    tref = _typeref(ptname, '`unknown`')
                    md.addLines(f'- `:{pname}` ({tref}) - {pdoc}')

def has_popts_data(props):
    # Props contain "doc" which we pop out, and "array" (rendered in the type column).
    # Check if a list of props has any keys which are not 'doc' or 'array'.
    for _, _, popts in props:
        keys = set(popts.keys())
        keys.discard('doc')
        keys.discard('array')
        if keys:
            return True

    return False

def lookupedgesforform(form: str, edges: Edges) -> Dict[str, Edges]:
    ret = collections.defaultdict(list)

    for edge in edges:
        src, name, dst = edge[0]

        # src and dst may be None, form==name, or form!=name.
        # This gives us 9 possible states to consider.
        # src  |  dst | -> ret
        # ===================================
        # none | none | -> generic
        # none |   != | -> source
        # none |    = | -> target
        #   != | none | -> target
        #    = | none | -> source
        #   != |    = | -> target
        #    = |   != | -> source
        #   != |   != | -> no-op
        #    = |    = | -> source, target

        if src is None and dst is None:
            ret['generic'].append(edge)
            continue
        if src is None and dst != form:
            ret['source'].append(edge)
            continue
        if src is None and dst == form:
            ret['target'].append(edge)
            continue
        if src != form and dst is None:
            ret['target'].append(edge)
            continue
        if src == form and dst is None:
            ret['source'].append(edge)
            continue
        if src != form and dst == form:
            ret['target'].append(edge)
            continue
        if src == form and dst != form:
            ret['source'].append(edge)
            continue
        if src != form and dst != form:
            # no-op
            continue
        if src == form and dst == form:
            ret['source'].append(edge)
            ret['target'].append(edge)

    return copy.deepcopy(dict(ret))

def processFormsPropsMd(md, dochelp, forms, alledges):
    '''
    Args:
        md (MdHelp):
        dochelp (DocHelp):
        forms (list):
        alledges (list):

    Returns:
        None
    '''
    md.addHead('Forms', lvl=1, anchor='dm-forms')
    md.addLines('Forms are derived from types, or base types. Forms represent node types in the graph.', '')

    for name, info, props in forms:

        formedges = lookupedgesforform(name, alledges)

        doc = dochelp.forms.get(name)
        if not doc.endswith('.'):
            logger.warning(f'Docstring for form {name} does not end with a period.]')
            doc = doc + '.'

        anchor = getMdLink(name, 'dm-form')
        md.addHead(name, lvl=2, anchor=anchor)

        type_anchor = getMdLink(name, 'dm-type')
        typeref = mdRef(name, type_anchor, mdfile=_TYPES_MD_FILE)
        md.addLines(doc, '', f'The base type for the form can be found at {typeref}.', '')

        ex = dochelp.formhelp.get(name)
        if ex:
            md.addLines('', f'An example of `{name}`:', '', f'- `{ex}`', '')

        if props:
            has_popts = has_popts_data(props)

            header = ['name', 'type', 'doc']
            if has_popts:
                header.append('opts')

            md.addLines('', '**Properties:**', '')
            md.addLines('| ' + ' | '.join(header) + ' |')
            md.addLines('|' + '|'.join(['---'] * len(header)) + '|')

            for pname, typedef, popts in props:

                popts = dict(popts)
                popts.pop('doc', None)
                arrayinfo = popts.pop('array', None)

                doc = dochelp.props.get((name, pname))
                if not doc.endswith('.'):
                    logger.warning(f'Docstring for prop ({name}, {pname}) does not end with a period.]')
                    doc = doc + '.'

                if isinstance(typedef[0], (tuple, list)):
                    ptname, ptopts = 'poly', {}
                else:
                    ptname, ptopts = typedef

                type_anchor2 = getMdLink(ptname, 'dm-type', suffix=None)
                typecell = mdRef(ptname, type_anchor2, mdfile=_TYPES_MD_FILE)

                extra = []
                for k, v in (arrayinfo or {}).items():
                    extra.append(f'{k}: `{v}`')
                for k, v in ptopts.items():
                    extra.append(f'{k}: `{v}`')
                if arrayinfo is not None:
                    typecell = f'array of {typecell}'
                if extra:
                    typecell += '<br>' + '<br>'.join(extra)

                docsafe = doc.replace('|', '\\|')

                row = [f'`:{pname}`', typecell, docsafe]

                if has_popts:
                    if popts:
                        optparts = []
                        for k, v in popts.items():
                            k = poptsToWords.get(k, k.replace(':', '-'))
                            optparts.append(f'{k}: `{v}`')
                        row.append('<br>'.join(optparts))
                    else:
                        row.append('')

                md.addLines('| ' + ' | '.join(row) + ' |')

        if formedges:

            source_edges = formedges.pop('source', None)
            dst_edges = formedges.pop('target', None)
            generic_edges = formedges.pop('generic', None)

            def _edgeRows(edges):
                _edges = []
                for (edef, enfo) in edges:
                    src, enam, dst = edef
                    doc = enfo.pop('doc', None)
                    if src is None:
                        src = '*'
                    if dst is None:
                        dst = '*'
                    for key in info_ignores:
                        enfo.pop(key, None)
                    if enfo:
                        logger.warning(f'{name} => Light edge {enam} has unhandled info: {enfo}')
                    _edges.append((src, enam, dst, doc))
                _edges.sort(key=lambda x: x[:2])
                return _edges

            if source_edges:
                if generic_edges:
                    source_edges.extend(generic_edges)

                md.addLines('', '**Source Edges:**', '')
                md.addLines('| source | verb | target | doc |')
                md.addLines('|---|---|---|---|')
                for src, enam, dst, doc in _edgeRows(source_edges):
                    md.addLines(f'| `{src}` | `-({enam})>` | `{dst}` | {doc} |')

            if dst_edges:
                if generic_edges:
                    dst_edges.extend(generic_edges)

                md.addLines('', '**Target Edges:**', '')
                md.addLines('| source | verb | target | doc |')
                md.addLines('|---|---|---|---|')
                for src, enam, dst, doc in _edgeRows(dst_edges):
                    md.addLines(f'| `{src}` | `-({enam})>` | `{dst}` | {doc} |')
                md.addLines('', '')

            if formedges:  # pragma: no cover
                # lookupedgesforform() only ever populates 'source'/'target'/
                # 'generic' (all popped above), so this is unreachable via
                # its own logic -- kept as a defensive check.
                logger.warning(f'{name} has unhandled light edges: {formedges}')

_TYPES_MD_FILE = 'datamodel_types.md'

async def _getModelDocHelp(core):
    '''
    Gather and validate the data model info shared by docModelTypesMd and
    docModelFormsMd, so a page requesting only one of them (via a single
    ```mdautodoc fence) still gets a fully cross-referenced result.

    Args:
        core (s_cortex.Cortex):

    Returns:
        dict: {'ctors', 'forms', 'edges', 'modeldict', 'types', 'ifaces', 'dochelp'}
    '''
    model = await core.getModelDef()

    ctors = []
    for typename, typedef, typeinfo in model.get('types', ()):
        if typedef[0] is None:
            typeopts = dict(typedef[1])
            ctor = typeopts.pop('ctor')
            ctors.append((typename, ctor, typeopts, dict(typeinfo)))

    forms = model.get('forms')
    edges = model.get('edges')
    props = collections.defaultdict(list)

    ctors = sorted(ctors, key=lambda x: x[0])
    forms = sorted(forms, key=lambda x: x[0])

    modeldict = await core.getModelDict()
    types = modeldict.get('types')
    ifaces = sorted(modeldict.get('interfaces', {}).items(), key=lambda x: x[0])
    for fname, fnfo, fprops in forms:
        for prop in fprops:
            props[fname].append(prop)

    [v.sort() for k, v in props.items()]

    dochelp = DocHelp(ctors, types, forms, props, ifaces=ifaces)

    return {
        'ctors': ctors,
        'forms': forms,
        'edges': edges,
        'modeldict': modeldict,
        'types': types,
        'ifaces': ifaces,
        'dochelp': dochelp,
    }

async def docModelTypesMd(core):
    '''
    Generate the "Synapse Data Model - Types" page (base types, regular
    types, and interfaces).

    Args:
        core (s_cortex.Cortex):

    Returns:
        MdHelp: the rendered page.
    '''
    info = await _getModelDocHelp(core)

    md = MdHelp()
    md.addHead('Synapse Data Model - Types', lvl=0)

    processCtorsMd(md, info['dochelp'], info['ctors'], info['types'])
    processTypesMd(md, info['dochelp'], info['types'])

    knownnames = set(info['modeldict'].get('types', {}).keys())
    knownnames.update(name for name, _ in info['ifaces'])
    processInterfacesMd(md, info['ifaces'], knownnames=knownnames)

    return md

async def docModelFormsMd(core):
    '''
    Generate the "Synapse Data Model - Forms" page. Also validates every
    form's ``ex`` example by running ``[form=example]`` against the Cortex.

    Args:
        core (s_cortex.Cortex):

    Returns:
        MdHelp: the rendered page.
    '''
    info = await _getModelDocHelp(core)
    dochelp = info['dochelp']

    # Validate examples
    for form, example in dochelp.formhelp.items():
        if example is None:
            continue
        if example.startswith('('):
            q = f"[{form}={example}]"
        else:
            q = f"[{form}='{example}']"
        node = False
        async for (mtyp, mnfo) in core.storm(q):
            if mtyp in ('init', 'fini'):
                continue
            if mtyp == 'err':  # pragma: no cover
                raise s_exc.SynErr(mesg='Invalid example', form=form, example=example, info=mnfo)
            if mtyp == 'node':
                node = True
        if not node:  # pragma: no cover
            raise s_exc.SynErr(mesg='Unable to make a node from example.', form=form, example=example)

    md = MdHelp()
    md.addHead('Synapse Data Model - Forms', lvl=0)

    processFormsPropsMd(md, dochelp, info['forms'], info['edges'])

    return md

async def docConfdefsMd(ctor):
    '''
    Generate a Cell subclass's confdefs page.

    Args:
        ctor (str): Dotted path to the class to document.

    Returns:
        MdHelp: the rendered page.
    '''
    cls = s_dyndeps.reqDynLocal(ctor)

    if not hasattr(cls, 'confdefs'):
        raise s_exc.BadArg(mesg='ctor must have a confdefs attr', ctor=ctor)

    md = MdHelp()

    conf = cls.initCellConf()

    name2envar = conf.getEnvarMapping()

    schema = conf.json_schema.get('properties', {})

    for name, conf in sorted(schema.items(), key=lambda x: x[0]):

        if conf.get('hideconf'):
            continue

        if conf.get('hidedocs'):
            continue

        nodesc = f'No description available for `{name}`.'

        desc = conf.get('description', nodesc)
        if not desc.endswith('.'):  # pragma: no cover
            logger.warning(f'Description for [{name}] is missing a period.')

        lines = []
        anchor = getMdLink(name, 'conf')
        lines.append(f'<a id="{anchor}"></a>')
        lines.append('')
        lines.append(f'### {name}')
        lines.append('')
        lines.append(desc)

        extended_description = conf.get('extended_description')
        if extended_description:
            lines.append('')
            lines.append(extended_description)

        lines.append('')

        ctyp = conf.get('type')
        lines.append('**Type**')
        lines.append('')
        lines.append(f'`{ctyp}`')
        lines.append('')

        if ctyp == 'object':
            if conf.get('properties'):
                lines.append('**Properties**')
                lines.append('')
                lines.append('The object expects the following properties:')
                lines.append('')
                data = {k: v for k, v in conf.items() if k not in (
                    'description', 'default', 'type', 'hideconf', 'hidecmdl',
                )}
                lines.append('```json')
                lines.append(s_json.dumps(data, sort_keys=True, indent=True).decode())
                lines.append('```')
                lines.append('')

        defval = conf.get('default', s_common.novalu)
        if defval is not s_common.novalu:
            lines.append('**Default Value**')
            lines.append('')
            lines.append(f'`{repr(defval)}`')
            lines.append('')

        envar = name2envar.get(name)
        if envar:
            lines.append('**Environment Variable**')
            lines.append('')
            lines.append(f'`{envar}`')
            lines.append('')

        md.addLines(*lines)

    return md

def _stripSelfFromSignature(sig):
    '''
    Drop a leading "self" (and the comma/space following it, if any) from a
    rendered method signature string, e.g. "(self, sha256, *, offs=None)" ->
    "(sha256, *, offs=None)".
    '''
    if not sig.startswith('(self'):
        return sig
    rest = sig[len('(self'):]
    if rest.startswith(','):
        rest = rest[1:].lstrip()
    return f'({rest}'

async def docApiMd(ctor):
    '''
    Generate Markdown API documentation for a class's own public methods,
    replacing the old Sphinx ``.. autoclass:: ... :members: :undoc-members:
    :show-inheritance::`` directive used for hand-authored Telepath API
    pages (e.g. a CellApi subclass). Absent ``:inherited-members:``, that
    Sphinx directive only ever documented members defined directly in the
    class body -- this mirrors that scope exactly by walking cls.__dict__
    rather than the full MRO, so it works for any class, not just CellApi
    subclasses.

    Args:
        ctor (str): Dotted path to the class to document.

    Returns:
        MdHelp: the rendered page.
    '''
    cls = s_dyndeps.reqDynLocal(ctor)

    if not inspect.isclass(cls):
        raise s_exc.BadArg(mesg='ctor must resolve to a class', ctor=ctor)

    clsname = cls.__name__

    md = MdHelp()
    md.addHead(clsname, lvl=0)

    clsdoc = inspect.getdoc(cls)
    if clsdoc:
        summary, _ = parseApiDocstring(clsdoc)
        if summary:
            md.addLines(summary, '')

    methods = [
        (name, valu) for name, valu in cls.__dict__.items()
        if not name.startswith('_')
        and (inspect.iscoroutinefunction(valu) or inspect.isasyncgenfunction(valu) or inspect.isfunction(valu))
    ]

    for name, valu in sorted(methods, key=lambda x: x[0]):

        sig = _stripSelfFromSignature(str(inspect.signature(valu)))
        anchor = getMdLink(name, 'api')
        md.addHead(f'{name}{sig}', lvl=1, anchor=anchor)

        doc = inspect.getdoc(valu)
        if not doc:
            md.addLines('No description available.', '')
            continue

        summary, sections = parseApiDocstring(doc)
        if summary:
            md.addLines(summary, '')

        for header, lines in sections:
            md.addLines(f'**{header}**', '')
            if header in ('Args', 'Arguments', 'Raises'):
                rendered = renderApiItemsMd(lines, israises=(header == 'Raises'))
            elif header in ('Returns', 'Yields'):
                rendered = renderApiReturnMd(lines)
            else:
                rendered = renderApiPassthroughMd(lines)
            md.addLines(*rendered, '')

    return md

async def processStormCmdsMd(md, pkgname, commands):
    # Local import: synapse.lib.storm imports this module at module level.
    import synapse.lib.storm as s_storm

    md.addHead('Storm Commands', lvl=1)
    md.addLines('This package implements the following Storm Commands.', '')

    commands = sorted(commands, key=lambda x: x.get('name'))

    for cdef in commands:

        cname = cdef.get('name')
        cdesc = cdef.get('desc')
        cargs = cdef.get('cmdargs')

        anchor = f'stormcmd-{pkgname.replace(":", "-")}-{cname.replace(".", "-")}'
        md.addHead(cname, lvl=2, anchor=anchor)

        lines = ['```text']

        pars = s_storm.Parser(prog=cname, descr=cdesc, cdef=cdef)
        if cargs:
            for (argname, arginfo) in cargs:
                pars.add_argument(argname, **arginfo)
        pars.help()

        for line in pars.mesgs:
            lines.append(line)

        lines.append('```')
        lines.append('')

        if (perms := cdef.get('perms')) is not None:
            perms = sorted('.'.join(perm) for perm in perms)
            lines.append('The command is accessible to users with one or more of the following permissions:')
            lines.append('')
            for perm in perms:
                lines.append(f'- `{perm}`')
            lines.append('')

        md.addLines(*lines)

async def processStormModulesMd(md, pkgname, modules):
    md.addHead('Storm Modules', lvl=1)

    hasapi = False
    modules = sorted(modules, key=lambda x: x.get('name'))

    for mdef in modules:

        apidefs = mdef.get('apidefs')
        if not apidefs:
            continue

        if not hasapi:
            md.addLines('This package implements the following Storm Modules.', '')
            hasapi = True

        mname = mdef['name']

        anchor = f'stormmod-{pkgname.replace(":", "-")}-{mname.replace(".", "-")}'
        md.addHead(mname, lvl=2, anchor=anchor)

        for apidef in apidefs:

            apiname = apidef['name']
            apidesc = apidef['desc']
            apitype = apidef['type']

            callsig = genCallsig(apitype)
            md.addHead(f'{apiname}{callsig}', lvl=3)
            if depr := apidef.get('deprecated'):
                md.addLines(*genDeprecationWarningMd(apiname, depr))
            md.addLines(*prepareMdLines(apidesc))
            md.addLines(*getArgLinesMd(apitype))
            md.addLines(*getReturnLinesMd(apitype))

    if not hasapi:
        md.addLines('This package does not export any Storm APIs.', '')

def _renderDepsTableMd(rows):
    lines = ['| Name | Version | Optional | Description |', '|---|---|---|---|']
    for name, vers, optional, desc in rows:
        name = name.replace('|', '\\|')
        vers = vers.replace('|', '\\|')
        opttext = 'yes' if optional else 'no'
        desctext = (desc or '').replace('|', '\\|')
        lines.append(f'| {name} | {vers} | {opttext} | {desctext} |')
    return lines

async def processStormDepsMd(md, pkgname, dependencies):
    md.addHead('Dependencies', lvl=1)
    md.addLines('This package depends on the following packages.', '')

    rows = []
    for name in sorted(dependencies.keys()):
        depinfo = dependencies[name]
        vers = depinfo.get('version', '')
        optional = depinfo.get('optional', False)
        desc = depinfo.get('desc')
        rows.append((name, vers, optional, desc))

    md.addLines(*_renderDepsTableMd(rows))
    md.addLines('')

_unconfigured_base_md = '(user-configured base URL)'

def _renderEndpointTableMd(rows):
    lines = ['| Path | Description |', '|---|---|']
    for path, desc in rows:
        path = path.replace('|', '\\|')
        desctext = (desc or '').replace('|', '\\|')
        lines.append(f'| {path} | {desctext} |')
    return lines

async def processModEndpointsMd(md, pkgname, endpoints):
    '''
    Args:
        md (MdHelp):
        pkgname (str):
        endpoints (dict):

    Returns:
        None
    '''
    groups = collections.OrderedDict()

    if not endpoints:
        return

    for ename, edef in sorted(endpoints.items()):

        path = edef.get('path')
        desc = edef.get('desc')
        base = edef.get('url') or _unconfigured_base_md

        groups.setdefault(base, []).append((path, desc))

    md.addHead('Endpoints', lvl=1)
    md.addLines('This package communicates with the following API endpoints.', '')

    for base in sorted(groups.keys(), key=lambda b: (b != _unconfigured_base_md, b)):
        md.addHead(base, lvl=2)
        md.addLines(*_renderEndpointTableMd(groups[base]))
        md.addLines('')

async def docStormpkgMd(pkgpath):
    '''
    Generate a Storm package's command/module/dependency/endpoint reference
    page, given the package prototype .yaml path.

    Args:
        pkgpath (str): Path to the package's prototype yaml.

    Returns:
        MdHelp: the rendered page.
    '''
    # Local import: synapse.tools.storm.pkg.gen imports this module at
    # module level.
    import synapse.tools.storm.pkg.gen as s_genpkg

    pkgdef = s_genpkg.loadPkgProto(pkgpath)
    pkgname = pkgdef.get('name')

    md = MdHelp()

    md.addHead(f'Storm Package: {pkgname}')
    lines = [
        'The following Commands are available from this package.',
        f'This documentation is generated for version {s_version.fmtVersion(pkgdef.get("version"))} of the package.',
    ]
    md.addLines(*lines)

    if dependencies := pkgdef.get('dependencies'):
        await processStormDepsMd(md, pkgname, dependencies)

    commands = pkgdef.get('commands')
    if commands:
        await processStormCmdsMd(md, pkgname, commands)

    if modules := pkgdef.get('modules'):
        await processStormModulesMd(md, pkgname, modules)

    await processModEndpointsMd(md, pkgname, pkgdef.get('endpoints'))

    return md

# This value is appended to the end of a type's anchor id. It prevents
# accidental cross-linking between parts of the docs, which can happen when
# secondary properties of a type may overlap with the main name of the type.
_stormtypes_suffix = 'f527'

async def docStormTypesLibsMd():
    '''
    Generate the "Storm Libraries" reference page (every registered Storm library).

    Returns:
        MdHelp: the rendered page.
    '''
    registry = s_stormtypes.registry
    libsinfo = registry.getLibDocs()

    libspage = MdHelp()
    libspage.addHead('Storm Libraries', lvl=0, anchor='stormtypes-libs-header')
    libspage.addLines('', 'Storm Libraries represent powerful tools available inside of the Storm query language.', '')

    docStormTypesMd(libspage, libsinfo, linkprefix='stormlibs', islib=True,
                    known_types=registry.known_types, types_prefix='stormprims',
                    types_suffix=_stormtypes_suffix, mdfile='stormtypes_prims.md')

    return libspage

async def docStormTypesPrimsMd():
    '''
    Generate the "Storm Types" reference page (every registered Storm primitive type).

    Returns:
        MdHelp: the rendered page.
    '''
    registry = s_stormtypes.registry
    priminfo = registry.getTypeDocs()

    typespage = MdHelp()
    typespage.addHead('Storm Types', lvl=0, anchor='stormtypes-prim-header')
    typespage.addLines('', 'Storm Objects are used as view objects for manipulating data in the Storm Runtime and in the Cortex itself.', '')

    docStormTypesMd(typespage, priminfo, linkprefix='stormprims', known_types=registry.known_types,
                    types_prefix='stormprims', types_suffix=_stormtypes_suffix)

    return typespage
