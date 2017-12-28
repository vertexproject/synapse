import synapse.common as s_common

import synapse.lib.time as s_time
import synapse.lib.interval as s_interval

'''
This module implements syntax parsing for the storm runtime.
( see synapse/lib/storm.py )
'''

whites = set(' \t\n')
binset = set('01')
decset = set('0123456789')
hexset = set('01234567890abcdef')
intset = set('01234567890abcdefx')
varset = set('$.:abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
timeset = set('01234567890')
propset = set(':abcdefghijklmnopqrstuvwxyz_0123456789')
starset = varset.union({'*'})
tagfilt = varset.union({'#', '*'})
alphaset = set('abcdefghijklmnopqrstuvwxyz')

# this may be used to meh() potentially unquoted values
valmeh = whites.union({'(', ')', '=', ',', '[', ']'})

def nom(txt, off, cset, trim=True):
    '''
    Consume chars in set from the string and return (subtxt,offset).

    Example:

        text = "foo(bar)"
        chars = set('abcdefghijklmnopqrstuvwxyz')

        name,off = nom(text,0,chars)

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

def is_literal(text, off):
    return text[off] in '("0123456789'

def parse_literal(text, off, trim=True):
    if text[off] == '(':
        return parse_list(text, off, trim=trim)

    if text[off] == '"':
        return parse_string(text, off, trim=trim)

    return parse_int(text, off, trim=trim)

def parse_int(text, off, trim=True):

    _, off = nom(text, off, whites)

    neg = False
    if nextchar(text, off, '-'):
        neg = True
        _, off = nom(text, off + 1, whites)

    valu = None
    if nextstr(text, off, '0x'):
        valu, off = nom(text, off + 2, hexset)
        if not valu:
            raise s_common.BadSyntaxError(at=off, mesg='0x expected hex')
        valu = int(valu, 16)

    elif nextstr(text, off, '0b'):
        valu, off = nom(text, off + 2, binset)
        if not valu:
            raise s_common.BadSyntaxError(at=off, mesg='0b expected bits')
        valu = int(valu, 2)

    else:

        valu, off = nom(text, off, decset)
        if not valu:
            raise s_common.BadSyntaxError(at=off, mesg='expected digits')

        if not nextchar(text, off, '.'):
            valu = int(valu)

        else:
            frac, off = nom(text, off + 1, decset)
            valu = float('%s.%s' % (valu, frac))

    if neg:
        valu = -valu

    return valu, off

def parse_float(text, off, trim=True):

    _, off = nom(text, off, whites)

    valu = ''
    if nextchar(text, off, '-'):
        valu += '-'
        _, off = nom(text, off + 1, whites)

    digs, off = nom(text, off, decset)
    if not digs:
        raise s_common.BadSyntaxError(at=off, mesg='expected digits')

    valu += digs

    if nextchar(text, off, '.'):
        frac, off = nom(text, off + 1, decset)
        if not frac:
            raise s_common.BadSyntaxError(at=off, mesg='expected .<digits>')

        valu = valu + '.' + frac

    return float(valu), off

def nom_whitespace(text, off):
    return nom(text, off, whites)

def isquote(text, off):
    return nextin(text, off, (",", '"'))

def parse_list(text, off=0, trim=True):
    '''
    Parse a list (likely for comp type) coming from a command line input.

    The string elements within the list may optionally be quoted.
    '''

    if not nextchar(text, off, '('):
        raise s_common.BadSyntaxError(at=off, mesg='expected open paren for list')

    off += 1

    valus = []
    while off < len(text):

        _, off = nom(text, off, whites)

        valu, off = parse_valu(text, off)

        _, off = nom(text, off, whites)

        # check for foo=bar kw tuple syntax
        if nextchar(text, off, '='):

            _, off = nom(text, off + 1, whites)

            vval, off = parse_valu(text, off)

            _, off = nom(text, off, whites)

            valu = (valu, vval)

        valus.append(valu)

        _, off = nom_whitespace(text, off)

        if nextchar(text, off, ')'):
            return valus, off + 1

        if not nextchar(text, off, ','):
            raise s_common.BadSyntaxError(at=off, text=text, mesg='expected comma in list')

        off += 1

    raise s_common.BadSyntaxError(at=off, mesg='unexpected and of text during list')

def parse_cmd_string(text, off, trim=True):
    '''
    Parse in a command line string which may be quoted.
    '''
    if trim:
        _, off = nom(text, off, whites)

    if isquote(text, off):
        return parse_string(text, off, trim=trim)

    if nextchar(text, off, '('):
        return parse_list(text, off)

    return meh(text, off, whites)

def parse_string(text, off, trim=True):

    if text[off] not in ('"', "'"): # lulz...
        raise s_common.BadSyntaxError(expected='String Literal', at=off)

    quot = text[off]

    if trim:
        _, off = nom(text, off, whites)

    off += 1
    vals = []
    while text[off] != quot:

        c = text[off]

        off += 1
        if c == '\\':
            c = text[off]
            off += 1

        vals.append(c)

    off += 1

    if trim:
        _, off = nom(text, off, whites)

    return ''.join(vals), off

def parse_time(text, off):
    tstr, off = nom(text, off, timeset)
    valu = s_time.parse(tstr)
    return valu, off

def parse_macro_filt(text, off=0, trim=True, mode='must'):

    _, off = nom(text, off, whites)

    # special + #tag (without prop) based filter syntax
    if nextchar(text, off, '#'):

        _, off = nom(text, off, whites)
        prop, off = nom(text, off, tagfilt, trim=True)

        _, off = nom(text, off, whites)

        if not nextchar(text, off, '@'):
            inst = ('filt', {'cmp': 'tag', 'mode': mode, 'valu': prop[1:]})
            return inst, off

        tick, off = parse_time(text, off + 1)

        _, off = nom(text, off, whites)

        if not nextchar(text, off, '-'):
            inst = ('filt', {'cmp': 'ival', 'mode': mode, 'valu': (prop, tick)})
            return inst, off

        tock, off = parse_time(text, off + 1)
        inst = ('filt', {'cmp': 'ivalival', 'mode': mode, 'valu': (prop, (tick, tock))})
        return inst, off

    # check for non-macro syntax
    name, xoff = nom(text, off, varset)
    _, xoff = nom(text, xoff, whites)

    if nextchar(text, xoff, '('):
        inst, off = parse_oper(text, off)

        opfo = {'cmp': inst[0], 'mode': mode}

        opfo['args'] = inst[1].get('args', ())
        opfo['kwlist'] = inst[1].get('kwlist', ())

        return ('filt', opfo), off

    ques, off = parse_ques(text, off, trim=trim)
    ques['mode'] = mode
    return ('filt', ques), off

def parse_macro_lift(text, off=0, trim=True):
    '''
    Parse a "lift" macro and return an inst,off tuple.
    '''
    ques, off = parse_ques(text, off, trim=trim)

    prop = ques.get('prop')
    valu = ques.get('valu')

    kwargs = {}

    limt = ques.get('limit')
    if limt is not None:
        kwargs['limit'] = limt

    by = ques.get('cmp')
    if by is not None:
        kwargs['by'] = by

    fromtag = ques.get('from')
    if fromtag is not None:
        kwargs['from'] = fromtag

    inst = oper('lift', prop, valu, **kwargs)
    return inst, off

def parse_opts(text, off=0):
    inst = ('opts', {'args': [], 'kwlist': []})
    valu = 1
    name, off = nom(text, off, varset, trim=True)

    if nextchar(text, off, '='):
        valu, off = parse_valu(text, off + 1)

    inst[1]['kwlist'].append((name, valu))
    return inst, off

def nextchar(text, off, valu):
    if len(text) <= off:
        return False
    return text[off] == valu

def nextstr(text, off, valu):
    return text.startswith(valu, off)

def nextin(text, off, vals):
    if len(text) <= off:
        return False
    return text[off] in vals

def parse_macro_join(text, off=0):
    '''
    &foo:bar
    &foo:bar=baz:faz
    &hehe.haha/foo:bar=baz:faz
    '''
    inst = ('join', {'args': [], 'kwlist': []})

    prop, off = nom(text, off, varset, trim=True)

    if len(text) == off:
        inst[1]['args'].append(prop)
        return inst, off

    if text[off] == '/':
        inst[1]['kwlist'].append(('from', prop))
        prop, off = nom(text, off + 1, varset, trim=True)

    inst[1]['args'].append(prop)

    if len(text) == off:
        return inst, off

    if nextchar(text, off, '='):
        prop, off = nom(text, off + 1, varset, trim=True)
        inst[1]['args'].append(prop)

    return inst, off

macrocmps = [
    ('<=', 'le'),
    ('>=', 'ge'),
    ('~=', 're'),
    ('!=', 'ne'),
    ('<', 'lt'),
    ('>', 'gt'),
    ('=', 'eq'),
]

def parse_ques(text, off=0, trim=True):
    '''
    Parse "query" syntax: tag/prop[@<timewin>][^<limit>][*<by>][=valu]
    '''
    ques = {}

    name, off = nom(text, off, varset, trim=True)

    if not name:
        raise s_common.BadSyntaxError(text=text, off=off, mesg='expected name')

    ques['cmp'] = 'has'
    ques['prop'] = name

    _, off = nom(text, off, whites)

    if len(text) == off:
        return ques, off

    if text[off] == '/':

        ques['from'] = name

        off += 1
        name, off = nom(text, off, varset, trim=True)

        ques['prop'] = name

    _, off = nom(text, off, whites)

    while True:

        _, off = nom(text, off, whites)

        if len(text) == off:
            return ques, off

        if text[off] == '^':
            ques['limit'], off = parse_int(text, off + 1, trim=True)
            continue

        # NOTE: "by" macro syntax only supports eq so we eat and run
        if nextchar(text, off, '*'):
            _, off = nom(text, off + 1, whites)

            ques['cmp'], off = nom(text, off, varset, trim=True)
            if len(text) == off:
                return ques, off

            if not nextchar(text, off, '='):
                raise s_common.BadSyntaxError(text=text, off=off, mesg='expected equals for by syntax')

            _, off = nom(text, off + 1, whites)

            ques['valu'], off = parse_valu(text, off)
            return ques, off

        if nextchar(text, off, '='):
            _, off = nom(text, off + 1, whites)

            ques['cmp'] = 'eq'
            ques['valu'], off = parse_valu(text, off)
            break

        textpart = text[off:]
        for ctxt, cmpr in macrocmps:

            if textpart.startswith(ctxt):
                ques['cmp'] = cmpr
                ques['valu'], off = parse_valu(text, off + len(ctxt))
                break

        break

    return ques, off

def parse_valu(text, off=0):
    '''
    Special syntax for the right side of equals in a macro
    '''
    _, off = nom(text, off, whites)

    if nextchar(text, off, '('):
        return parse_list(text, off)

    if isquote(text, off):
        return parse_string(text, off)

    # since it's not quoted, we can assume we are bound by both
    # white space and storm syntax chars ( ) , =
    valu, off = meh(text, off, valmeh)

    # for now, give it a shot as an int...  maybe eventually
    # we'll be able to disable this completely, but for now
    # lets maintain backward compatibility...
    try:
        # NOTE: this is ugly, but faster than parsing the string
        valu = int(valu, 0)
    except ValueError as e:
        pass

    return valu, off

def parse_cmd_kwarg(text, off=0):
    '''
    Parse a foo:bar=<valu> kwarg into (prop,valu),off
    '''
    _, off = nom(text, off, whites)

    prop, off = nom(text, off, varset)

    _, off = nom(text, off, whites)

    if not nextchar(text, off, '='):
        raise s_common.BadSyntaxError(expected='= for kwarg ' + prop, at=off)

    _, off = nom(text, off + 1, whites)

    valu, off = parse_cmd_string(text, off)
    return (prop, valu), off

def parse_cmd_kwlist(text, off=0):
    '''
    Parse a foo:bar=<valu>[,...] kwarg list into (prop,valu),off
    '''
    kwlist = []

    _, off = nom(text, off, whites)

    while off < len(text):

        (p, v), off = parse_cmd_kwarg(text, off=off)

        kwlist.append((p, v))

        _, off = nom(text, off, whites)
        if not nextchar(text, off, ','):
            break

    _, off = nom(text, off, whites)
    return kwlist, off

def parse_oper(text, off=0):
    '''
    Returns an inst,off tuple by parsing an operator expression.

    Example:

        inst,off = parse_oper('foo("bar",baz=20)')

    '''
    name, off = nom(text, off, varset)

    inst = (name, {'args': [], 'kwlist': []})

    _, off = nom(text, off, whites)

    if not nextchar(text, off, '('):
        raise s_common.BadSyntaxError(expected='( for operator ' + name, at=off)

    off += 1

    while True:

        _, off = nom(text, off, whites)

        if nextchar(text, off, ')'):
            off += 1
            return inst, off

        valu, off = parse_valu(text, off)
        _, off = nom(text, off, whites)

        if nextchar(text, off, '='):

            vval, off = parse_valu(text, off + 1)
            inst[1]['kwlist'].append((valu, vval))

        else:

            inst[1]['args'].append(valu)

        if not nextin(text, off, [',', ')']):
            raise s_common.BadSyntaxError(mesg='Unexpected Token: ' + text[off], at=off)

        if nextchar(text, off, ','):
            off += 1

def parse_perm(text, off=0):
    '''
    Parse a permission string
        <name> [<opt>=<match>...]
    '''
    _, off = nom(text, off, whites)

    name, off = nom(text, off, varset)
    if not name:
        raise s_common.BadSyntaxError(mesg='perm str expected name')

    retn = (name, {})

    _, off = nom(text, off, whites)

    while len(text) > off:

        _, off = nom(text, off, whites)
        meta, off = nom(text, off, varset)
        _, off = nom(text, off, whites)

        if not nextchar(text, off, '='):
            raise s_common.BadSyntaxError(mesg='perm opt expected =')

        _, off = nom(text, off + 1, whites)

        valu, off = parse_valu(text, off)
        if not isinstance(valu, str):
            raise s_common.BadSyntaxError(mesg='perm opt %s= expected string' % meta)

        _, off = nom(text, off, whites)

        retn[1][meta] = valu

    return retn, off

def oper(name, *args, **kwargs):
    kwlist = list(sorted(kwargs.items()))
    return (name, {'args': args, 'kwlist': kwlist})

def parse(text, off=0):
    '''
    Parse and return a set of instruction tufos.
    '''
    ret = []

    while True:

        # leading whitespace is irrelevant
        _, off = nom(text, off, whites)
        if off >= len(text):
            break

        # handle some special "macro" style syntaxes

        # [ ] for node modification macro syntax

        # [ inet:fqdn=woot.com ]  == addnode(inet:fqdn,woot.com)
        # [ :asn=10 ]  == setprop(asn=10)
        # [ #foo.bar ]  or [ +#foo.bar ] == addtag(foo.bar)
        # [ -#foo.bar ] == deltag(foo.bar)
        if nextchar(text, off, '['):

            off += 1

            while True:

                _, off = nom(text, off, whites)
                if nextchar(text, off, ']'):
                    off += 1
                    break

                if off == len(text):
                    raise s_common.BadSyntaxError(mesg='unexpected end of text in edit mode')

                if nextstr(text, off, '+#'):
                    valu, off = parse_valu(text, off + 2)
                    ret.append(oper('addtag', valu))
                    continue

                if nextstr(text, off, '-#'):
                    valu, off = parse_valu(text, off + 2)
                    ret.append(oper('deltag', valu))
                    continue

                if nextchar(text, off, '#'):
                    valu, off = parse_valu(text, off + 1)
                    ret.append(oper('addtag', valu))
                    continue

                if nextstr(text, off, '-:'):
                    valu, off = parse_valu(text, off + 1)
                    ret.append(oper('delprop', valu, force=1))
                    continue

                # otherwise, it should be a prop=valu (maybe relative)
                prop, off = nom(text, off, propset)
                if not prop:
                    raise s_common.BadSyntaxError(mesg='edit macro expected prop=valu syntax')

                _, off = nom(text, off, whites)
                if not nextchar(text, off, '='):
                    raise s_common.BadSyntaxError(mesg='edit macro expected prop=valu syntax')

                valu, off = parse_valu(text, off + 1)
                if prop[0] == ':':
                    kwargs = {prop: valu}
                    ret.append(oper('setprop', **kwargs))
                    continue

                ret.append(oper('addnode', prop, valu))

            continue

        # pivot() macro with no src prop:   -> foo:bar
        if nextstr(text, off, '->'):
            _, off = nom(text, off + 2, whites)
            name, off = nom(text, off, varset)
            ret.append(oper('pivot', name))
            continue

        # join() macro with no src prop:   <- foo:bar
        if nextstr(text, off, '<-'):
            _, off = nom(text, off + 2, whites)
            name, off = nom(text, off, varset)
            ret.append(oper('join', name))
            continue

        # lift by tag alone macro
        if nextstr(text, off, '#'):
            _, off = nom(text, off + 1, whites)
            name, off = nom(text, off, varset)
            ret.append(oper('alltag', name))
            continue

        # must() macro syntax: +foo:bar="woot"
        if nextchar(text, off, '+'):
            inst, off = parse_macro_filt(text, off + 1, mode='must')
            ret.append(inst)
            continue

        # cant() macro syntax: -foo:bar=10
        if nextchar(text, off, '-'):
            inst, off = parse_macro_filt(text, off + 1, mode='cant')
            ret.append(inst)
            continue

        # logical and syntax for multiple filters
        if text[off] == '&':

            if len(ret) == 0:
                raise s_common.BadSyntaxError(mesg='logical and with no previous operator')

            prev = ret[-1]

            if prev[0] != 'filt':
                raise s_common.BadSyntaxError(mesg='prev oper must be filter not: %r' % prev)

            mode = prev[1].get('mode')
            inst, off = parse_macro_filt(text, off + 1, mode=mode)

            if prev[1].get('cmp') != 'and':
                prev = ('filt', {'args': [prev, ], 'kwlist': [], 'cmp': 'and', 'mode': mode})
                ret[-1] = prev

            prev[1]['args'].append(inst)
            continue

        # logical or syntax for multiple filters
        if text[off] == '|':

            if len(ret) == 0:
                raise s_common.BadSyntaxError(mesg='logical or with no previous operator')

            prev = ret[-1]

            if prev[0] != 'filt':
                raise s_common.BadSyntaxError(mesg='prev oper must be filter not: %r' % prev)

            mode = prev[1].get('mode')
            inst, off = parse_macro_filt(text, off + 1, mode=mode)

            if prev[1].get('cmp') != 'or':
                prev = ('filt', {'args': [prev, ], 'kwlist': [], 'cmp': 'or', 'mode': mode})
                ret[-1] = prev

            prev[1]['args'].append(inst)
            continue

        # opts() macro syntax: %uniq=0 %limit=30
        if text[off] == '%':
            inst, off = parse_opts(text, off + 1)
            ret.append(inst)
            continue

        origoff = off

        name, off = nom(text, off, varset)
        _, off = nom(text, off, whites)

        # mop up in the case where we end with a macro
        if len(text) == off:
            inst, off = parse_macro_lift(text, origoff)
            ret.append(inst)
            continue

        # macro foo:bar->baz:faz prop pivot
        if nextstr(text, off, '->'):

            pivn, off = nom(text, off + 2, varset)
            inst = ('pivot', {'args': [name], 'kwlist': []})

            # FIXME make a parser for foo.bar/baz:faz*blah#40
            if nextchar(text, off, '/'):
                inst[1]['kwlist'].append(('from', pivn))
                pivn, off = nom(text, off + 1, varset)

            inst[1]['args'].append(pivn)

            ret.append(inst)
            continue

        # macro foo:bar<-baz:faz prop join
        if nextstr(text, off, '<-'):

            joinn, off = nom(text, off + 2, varset)
            inst = ('join', {'args': [name], 'kwlist': []})

            # FIXME make a parser for foo.bar/baz:faz*blah#40
            if nextchar(text, off, '/'):
                inst[1]['kwlist'].append(('from', joinn))
                joinn, off = nom(text, off + 1, varset)

            inst[1]['args'].append(joinn)

            ret.append(inst)
            continue

        # standard foo() oper syntax
        if nextchar(text, off, '('):
            inst, off = parse_oper(text, origoff)
            ret.append(inst)
            continue

        # only macro lift syntax remains
        inst, off = parse_macro_lift(text, origoff)
        ret.append(inst)

    #[ i[1]['kwlist'].sort() for i in ret ]

    return ret
