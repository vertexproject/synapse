'''
Storm Compiled Binary Format (stormbin).

Provides serialization/deserialization of Storm AST trees using msgpack.
Pre-compiled queries skip the Lark parser entirely and are deserialized
straight into AST nodes.

Binary format envelope::

    (VERSION, AST_TREE, META)

Each AST node::

    (NODE_TYPE_ID, KIDS, META)

Attribute keys use short names (e.g. ``a`` instead of ``attrs``,
``v`` instead of ``valu``) to minimize serialized size.
'''
import base64
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.ast as s_ast
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack
import synapse.lib.parser as s_parser

logger = logging.getLogger(__name__)

FORMAT_VERSION = 1

MAX_DEPTH = 256

# Closing brace used as a base64 envelope marker so that an older Storm parser
# fails immediately on this prefix.
BASE64_PREFIX = s_const.STORMBIN_BASE64_PREFIX

validModes = {'storm', 'lookup', 'autoadd', 'search'}

# AST class <-> integer ID mapping.
# IDs are defined via _bin_id class variables on each AST class.
# Build the lookup dicts by scanning all AstNode subclasses.
classToId = {}
idToClass = {}

def _initRegistry():
    '''Scan all AstNode subclasses for _bin_id and build the registry.'''
    seen = set()
    queue = list(s_ast.AstNode.__subclasses__())
    while queue:
        cls = queue.pop()
        if cls in seen: # pragma: no cover
            continue
        seen.add(cls)
        queue.extend(cls.__subclasses__())

        # Only register classes that directly define _bin_id
        binid = cls._bin_id
        if binid is s_common.novalu:
            continue

        if binid in idToClass:
            mesg = f'Duplicate _bin_id {binid}: {cls.__name__} and {idToClass[binid].__name__}'
            raise s_exc.BadArg(mesg=mesg)

        classToId[cls] = binid
        idToClass[binid] = cls

_initRegistry()

def en(node):
    '''
    Serialize an AST node tree into a compact tuple format.

    Args:
        node: An AstNode instance.

    Returns:
        tuple: Serialized AST node tuple.
    '''
    cls = node.__class__
    typeid = cls._bin_id
    if typeid is s_common.novalu:
        mesg = f'Unknown AST class: {cls.__name__}'
        raise s_exc.BadArg(mesg=mesg)

    # Recurse into children
    kids = [en(kid) for kid in node.kids]

    # Build per-node metadata
    meta = {}

    # Collect non-default attributes into meta (defined via _bin_attrs on AST classes)
    attrdict = {}
    for attrname, key, default in cls._bin_attrs:
        val = getattr(node, attrname, default)
        if val is not default and val != default:
            attrdict[key] = val

    if attrdict:
        meta['a'] = attrdict

    info = node.astinfo
    meta['pos'] = (info.soff, info.eoff, info.sline, info.eline, info.scol, info.ecol, info.isterm)

    return (typeid, kids, meta)

def un(data, depth=0):
    '''
    Deserialize an AST node tree from a compact tuple format.

    Args:
        data (tuple): Serialized AST node tuple.
        depth (int): Current recursion depth.

    Returns:
        AstNode: Reconstructed AST node.
    '''
    if depth > MAX_DEPTH:
        mesg = f'AST exceeds maximum depth of {MAX_DEPTH}'
        raise s_exc.BadArg(mesg=mesg)

    if not isinstance(data, (tuple, list)) or len(data) != 3:
        mesg = 'Invalid AST node format: expected 3-element tuple'
        raise s_exc.BadArg(mesg=mesg)

    typeid, kids, meta = data

    if not isinstance(meta, dict):
        mesg = 'Invalid AST node metadata: expected dict'
        raise s_exc.BadArg(mesg=mesg)

    attrs = meta.get('a')

    cls = idToClass.get(typeid)
    if cls is None:
        mesg = f'Unknown AST type ID: {typeid}'
        raise s_exc.BadArg(mesg=mesg)

    # Reconstruct AstInfo
    pos = meta.get('pos')
    if pos is None:
        mesg = 'Invalid AST node metadata: missing pos info'
        raise s_exc.BadArg(mesg=mesg)

    soff, eoff, sline, eline, scol, ecol, isterm = pos
    astinfo = s_parser.AstInfo('', soff, eoff, sline, eline, scol, ecol, isterm)

    # Deserialize children
    childnodes = [un(k, depth=depth + 1) for k in kids]

    # Build constructor kwargs from _bin_attrs defined on the AST class
    kwargs = {}

    if attrs:
        for attrname, key, default in cls._bin_attrs:
            if key in attrs:
                val = attrs[key]
            else:
                val = default
            kwargs[attrname] = val

    # EmbedQuery.valu is normally the source text of the embedded query.
    # Synthesize a compiled-form (}-prefixed base64) so consumers that
    # round-trip through getStormQuery() pick up the fast path.
    if cls is s_ast.EmbedQuery:
        node = cls(astinfo, kids=childnodes)
        if childnodes:
            node.valu = dump(childnodes[0], ascii=True)

    # Like EmbedQuery, populate .text with the compiled form so any consumer
    # that reads it round-trips through getStormQuery() on the fast path.
    elif cls is s_ast.SubQuery:
        node = cls(astinfo, kids=childnodes, **kwargs)
        if childnodes:
            node.text = dump(childnodes[0], ascii=True)

    # Query.text is what ArgvQuery.compute() returns for command-arg
    # subqueries (background, batch, view.exec). Populate it with the
    # compiled-form so those commands execute via the compiled fast path.
    elif cls is s_ast.Query:
        node = cls(astinfo, kids=childnodes, **kwargs)
        node.text = dump(node, ascii=True)

    else:
        node = cls(astinfo, kids=childnodes, **kwargs)

    return node

def dump(node, ascii=False):
    '''
    Dump an AST node into a stormbin payload.

    Args:
        node: An AstNode instance.
        ascii (bool): If True, return a ``}``-prefixed base64 string. If
                      False (default), return raw bytes.

    Returns:
        bytes or str: A stormbin payload that can be passed to ``load()``.
    '''
    envelope = (FORMAT_VERSION, en(node), {})
    byts = s_msgpack.en(envelope)
    if ascii:
        return enBase64(byts)
    return byts

def compile(text, mode='storm', ascii=False):
    '''
    Compile a Storm query string into the binary format.

    Args:
        text (str): Storm query text to compile.
        mode (str): Parse mode (storm, lookup, autoadd, search).
        ascii (bool): If True, return a ``}``-prefixed base64 string. If
                      False (default), return raw bytes.

    Returns:
        bytes or str: Compiled stormbin payload.
    '''
    if mode not in validModes:
        mesg = f'Invalid storm mode: {mode}'
        raise s_exc.BadArg(mesg=mesg)

    query = s_parser.parseQuery(text, mode=mode)

    tree = en(query)

    meta = {}
    if mode != 'storm':
        meta['mode'] = mode

    envelope = (FORMAT_VERSION, tree, meta)
    byts = s_msgpack.en(envelope)
    if ascii:
        return enBase64(byts)
    return byts

def load(byts):
    '''
    Load a compiled binary stormbin payload into an AST Query node.

    Args:
        byts (bytes): Compiled binary data.

    Returns:
        AstNode: Reconstructed AST Query node.
    '''
    if isinstance(byts, str):
        if byts.startswith(BASE64_PREFIX):
            byts = unBase64(byts)
        else:
            mesg = 'Expected bytes or base64-prefixed string'
            raise s_exc.BadArg(mesg=mesg)

    try:
        envelope = s_msgpack.un(byts, use_list=True)
    except Exception as e:
        mesg = f'Failed to decode stormbin data: {e}'
        raise s_exc.BadArg(mesg=mesg) from e

    if not isinstance(envelope, (tuple, list)) or len(envelope) != 3:
        mesg = 'Invalid stormbin envelope: expected 3-element tuple'
        raise s_exc.BadArg(mesg=mesg)

    version, tree, meta = envelope

    if version != FORMAT_VERSION:
        mesg = f'Unsupported stormbin version: {version} (expected {FORMAT_VERSION})'
        raise s_exc.BadArg(mesg=mesg)

    if not isinstance(meta, dict):
        mesg = 'Invalid stormbin metadata: expected dict'
        raise s_exc.BadArg(mesg=mesg)

    mode = meta.get('mode', 'storm')
    if mode not in validModes:
        mesg = f'Invalid stormbin mode: {mode}'
        raise s_exc.BadArg(mesg=mesg)

    query = un(tree)

    return query

def enBase64(byts):
    '''
    Encode compiled binary bytes as a base64-prefixed string.

    Args:
        byts (bytes): Compiled binary data.

    Returns:
        str: base64-prefixed string.
    '''
    return BASE64_PREFIX + base64.b64encode(byts).decode()

def unBase64(text):
    '''
    Decode a base64-prefixed string to binary bytes.

    Args:
        text (str): base64-prefixed string.

    Returns:
        bytes: Decoded binary data.
    '''
    if not text.startswith(BASE64_PREFIX):
        mesg = 'String does not have stormbin base64 prefix'
        raise s_exc.BadArg(mesg=mesg)

    try:
        return base64.b64decode(text[len(BASE64_PREFIX):])
    except Exception as e:
        mesg = f'Failed to decode base64 data: {e}'
        raise s_exc.BadArg(mesg=mesg) from e

def isCompiled(qinput):
    '''
    Detect whether query input is in compiled binary format.

    Args:
        qinput: Query input (str or bytes).

    Returns:
        bool: True if the input is compiled binary or base64-encoded.
    '''
    if isinstance(qinput, bytes):
        return True

    if isinstance(qinput, str) and qinput.startswith(BASE64_PREFIX):
        return True

    return False
