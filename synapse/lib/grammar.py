import regex

import synapse.exc as s_exc

# TODO:  commonize with storm.lark
re_scmd = '^[a-z][a-z0-9.]+$'
scmdre = regex.compile(re_scmd)
univrestr = r'\.[a-z_][a-z0-9_]*([:.][a-z0-9_]+)*'
univre = regex.compile(univrestr)
proprestr = r'[a-z_][a-z0-9_]*(:[a-z0-9_]+)+([:.][a-z_ ][a-z0-9_]+)*'
proporunivrestr = f'({univrestr})|({proprestr})'
proporunivre = regex.compile(proporunivrestr)
propre = regex.compile(proprestr)
formrestr = r'[a-z_][a-z0-9_]*(:[a-z0-9_]+)+'
formre = regex.compile(formrestr)
tagrestr = r'(\w+\.)*\w+'
tagre = regex.compile(tagrestr)
edgerestr = r'[\w\.:]{1,200}'
edgere = regex.compile(edgerestr)
basepropnopivpropstr = r'[a-z_][a-z0-9_]*(?:(\:|\.)[a-z_][a-z0-9_]*)*'
basepropnopivpropre = regex.compile(basepropnopivpropstr)

whites = set(' \t\n')
alphaset = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

unitset = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZµ')

def isPropName(name):
    return propre.fullmatch(name) is not None

def isCmdName(name):
    return scmdre.fullmatch(name) is not None

def isUnivName(name):
    return univre.fullmatch(name) is not None

def isFormName(name):
    return formre.fullmatch(name) is not None

def isBasePropNoPivprop(name):
    return basepropnopivpropre.fullmatch(name) is not None

def isEdgeVerb(verb):
    return edgere.fullmatch(verb) is not None

floatre = regex.compile(r'\s*-?\d+(\.\d+)?([eE][-+]\d+)?')

def parse_float(text, off):
    match = floatre.match(text[off:])
    if match is None:
        raise s_exc.BadSyntax(at=off, mesg='Invalid float')

    s = match.group(0)

    return float(s), len(s) + off

def chop_float(text, off):
    match = floatre.match(text[off:])
    if match is None:
        raise s_exc.BadSyntax(at=off, mesg='Invalid float')

    s = match.group(0)

    return s, len(s) + off

def nom(txt, off, cset, trim=True):
    '''
    Consume chars in set from the string and return (subtxt,offset).

    Example:

        text = "foo(bar)"
        chars = set('abcdefghijklmnopqrstuvwxyz')

        name,off = nom(text,0,chars)

    Note:

    This really shouldn't be used for new code
    '''
    if trim:
        while len(txt) > off and txt[off] in whites:
            off += 1

    r = ''
    while len(txt) > off and txt[off] in cset:
        r += txt[off]
        off += 1

    if trim:
        while len(txt) > off and txt[off] in whites:
            off += 1

    return r, off

def meh(txt, off, cset):
    r = ''
    while len(txt) > off and txt[off] not in cset:
        r += txt[off]
        off += 1
    return r, off
