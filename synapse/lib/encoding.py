import csv
import regex
import base64
import codecs
import xml.etree.ElementTree as x_etree

import synapse.exc as s_exc

import synapse.lib.json as s_json
import synapse.lib.msgpack as s_msgpack

def _de_base64(item, **opts):

    # transparently handle the strings/bytes issue...
    wasstr = isinstance(item, str)
    if wasstr:
        item = item.encode('utf8')

    item = base64.b64decode(item)

    if wasstr:
        item = item.decode('utf8')

    return item

def _en_base64(byts, **opts):
    return base64.b64encode(byts)

def _en_utf8(text, **opts):
    return text.encode('utf8')

def _de_utf8(byts, **opts):
    return byts.decode('utf8')

decoders = {
    'utf8': _de_utf8,  # type: ignore
    'base64': _de_base64,  # type: ignore
}

encoders = {
    'utf8': _en_utf8,  # type: ignore
    'base64': _en_base64,  # type: ignore
}

def decode(name, byts, **opts):
    '''
    Decode the given byts with the named decoder.
    If name is a comma separated list of decoders,
    loop through and do them all.

    Example:

        byts = s_encoding.decode('base64',byts)

    Note: Decoder names may also be prefixed with +
          to *encode* for that name/layer.

    '''
    for name in name.split(','):

        if name.startswith('+'):
            byts = encode(name[1:], byts, **opts)
            continue

        func = decoders.get(name)
        if func is None:
            raise s_exc.NoSuchDecoder(name=name)

        byts = func(byts, **opts)

    return byts

def encode(name, item, **opts):

    for name in name.split(','):

        if name.startswith('-'):
            item = decode(name[1:], item, **opts)
            continue

        func = encoders.get(name)
        if func is None:
            raise s_exc.NoSuchEncoder(name=name)

        item = func(item, **opts)

    return item

def _xml_stripns(e):

    # believe it or not, this is the recommended
    # way to strip XML namespaces...
    if e.tag.find('}') != -1:
        e.tag = e.tag.split('}')[1]

    for name, valu in e.attrib.items():
        if name.find('}') != -1:
            e.attrib[name.split('{')[1]] = valu

    for x in e:
        _xml_stripns(x)


def _fmt_xml(fd, gest):
    # TODO stream XML for huge files
    elem = x_etree.fromstring(fd.read())
    _xml_stripns(elem)
    yield {elem.tag: elem}

def _fmt_csv(fd, gest):

    opts = {}

    quot = gest.get('format:csv:quote')
    cmnt = gest.get('format:csv:comment')
    dial = gest.get('format:csv:dialect')
    delm = gest.get('format:csv:delimiter')

    if dial is not None:
        opts['dialect'] = dial

    if delm is not None:
        opts['delimiter'] = delm

    if quot is not None:
        opts['quotechar'] = quot

    # do we need to strip a comment char?
    if cmnt is not None:

        # use this if we need to strip comments
        # (but avoid it otherwise for perf )
        def lineiter():
            for line in fd:
                if not line.startswith(cmnt):
                    yield line

        return csv.reader(lineiter(), **opts)

    return csv.reader(fd, **opts)

def _fmt_lines(fd, gest):

    skipre = None
    mustre = None

    lowr = gest.get('format:lines:lower')
    cmnt = gest.get('format:lines:comment', '#')

    skipstr = gest.get('format:lines:skipre')
    if skipstr is not None:
        skipre = regex.compile(skipstr)

    muststr = gest.get('format:lines:mustre')
    if muststr is not None:
        mustre = regex.compile(muststr)

    for line in fd:

        line = line.strip()

        if not line:
            continue

        if line.startswith(cmnt):
            continue

        if lowr:
            line = line.lower()

        if skipre is not None and skipre.match(line) is not None:
            continue

        if mustre is not None and mustre.match(line) is None:
            continue

        yield line

def _fmt_json(fd, info):
    yield s_json.load(fd)

def _fmt_jsonl(fd, info):
    for line in fd:
        yield s_json.loads(line)

def _fmt_mpk(fd, info):
    yield from s_msgpack.iterfd(fd)

fmtyielders = {
    'csv': _fmt_csv,
    'mpk': _fmt_mpk,
    'xml': _fmt_xml,
    'json': _fmt_json,
    'jsonl': _fmt_jsonl,
    'lines': _fmt_lines,
}

fmtopts = {
    'mpk': {},
    'xml': {'mode': 'r', 'encoding': 'utf8'},
    'csv': {'mode': 'r', 'encoding': 'utf8'},
    'json': {'mode': 'r', 'encoding': 'utf8'},
    'jsonl': {'mode': 'r', 'encoding': 'utf8'},
    'lines': {'mode': 'r', 'encoding': 'utf8'},
}

def addFormat(name, fn, opts):
    '''
    Add an additional ingest file format
    '''
    fmtyielders[name] = fn
    fmtopts[name] = opts

def iterdata(fd, close_fd=True, **opts):
    '''
    Iterate through the data provided by a file like object.

    Optional parameters may be used to control how the data
    is deserialized.

    Examples:
        The following example show use of the iterdata function.::

            with open('foo.csv','rb') as fd:
                for row in iterdata(fd, format='csv', encoding='utf8'):
                    dostuff(row)

    Args:
        fd (file) : File like object to iterate over.
        close_fd (bool) : Default behavior is to close the fd object.
                          If this is not true, the fd will not be closed.
        **opts (dict): Ingest open directive.  Causes the data in the fd
                       to be parsed according to the 'format' key and any
                       additional arguments.

    Yields:
        An item to process. The type of the item is dependent on the format
        parameters.
    '''
    fmt = opts.get('format', 'lines')
    fopts = fmtopts.get(fmt, {})

    # set default options for format
    for opt, val in fopts.items():
        opts.setdefault(opt, val)

    ncod = opts.get('encoding')
    if ncod is not None:
        fd = codecs.getreader(ncod)(fd)

    fmtr = fmtyielders.get(fmt)
    if fmtr is None:
        raise s_exc.NoSuchImpl(name=fmt, knowns=fmtyielders.keys())

    for item in fmtr(fd, opts):
        yield item

    if close_fd:
        fd.close()
