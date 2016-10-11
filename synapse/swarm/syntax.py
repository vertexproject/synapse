import synapse.lib.sched as s_sched
import synapse.lib.service as s_service

from synapse.common import *
from synapse.eventbus import EventBus

whites = set(' \t\n')
intset = set('01234567890abcdefx')
varset = set('.:abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345678910')
whenset = set('0123456789abcdefghijklmnopqrstuvwxyz+,')

def nom(txt,off,cset,trim=True):
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

    return r,off

def is_literal(text,off):
    return text[off] in '("0123456789'

def parse_literal(text, off,trim=True):
    if text[off] == '(':
        return parse_list(text,off,trim=trim)

    if text[off] == '"':
        return parse_string(text,off,trim=trim)

    return parse_int(text,off,trim=trim)

def parse_int(text,off,trim=True):
    numstr,off = nom(text,off,intset,trim=trim)
    try:
        return int(numstr,0),off
    except Exception as e:
        raise Exception('Expected Literal At: %d (got: %s)' % (off,text[off:off+10],))

def parse_list(text,off,trim=True):
    if text[off] != '(':
        raise Exception('Expected List At: %d' % (off,))

    off += 1
    valus = []
    while True:

        valu,off = parse_literal(text,off,trim=trim)

        valus.append(valu)

        if text[off] == ')':
            return valus, off + 1

        if text[off] != ',':
            raise Exception('Invalid List Syntax At: %d' % (off,))

        off += 1

def parse_string(text,off,trim=True):

    if text[off] != '"':
        raise Exception('Expected String Literal: %d' % (off,))

    if trim:
        _,off = nom(text,off,whites)

    off += 1
    vals = []
    while text[off] != '"':
        c = text[off]

        off += 1
        if c == '\\':
            c = text[off]
            off += 1

        vals.append(c)

    off += 1

    if trim:
        _,off = nom(text,off,whites)

    return ''.join(vals),off

def parse_macro(text,off=0,trim=True, mode='lift'):
    '''
    Parse a "lift" expression and return an inst,off tuple.
    '''
    ques,off = parse_ques(text,off,trim=trim)

    cmpr = ques.get('cmp')
    inst = (cmpr,{'args':[],'kwlist':[],'mode':mode})

    inst[1]['args'].append( ques.pop('prop',None) )
    inst[1]['kwlist'].extend( ques.items() )

    return inst,off

def parse_opts(text,off=0):
    inst = ('opts',{'args':[],'kwlist':[]})
    valu = 1
    name,off = nom(text,off,varset,trim=True)

    if nextchar(text,off,'='):
        valu,off = parse_literal(text,off+1,trim=True)

    inst[1]['kwlist'].append((name,valu))
    return inst,off

def nextchar(text,off,valu):
    if len(text) <= off:
        return False
    return text[off] == valu

def nextin(text,off,vals):
    if len(text) <= off:
        return False
    return text[off] in vals

def parse_pivot(text,off=0):
    '''
    ^foo:bar
    ^foo:bar=baz:faz
    ^hehe.haha/foo:bar=baz:faz
    '''
    inst = ('pivot',{'args':[],'kwlist':[]})

    prop,off = nom(text,off,varset,trim=True)

    if len(text) == off:
        inst[1]['args'].append(prop)
        return inst,off

    if text[off] == '/':
        inst[1]['kwlist'].append( ('from',prop) )
        prop,off = nom(text,off+1,varset,trim=True)

    inst[1]['args'].append( prop )

    if len(text) == off:
        return inst,off

    if nextchar(text,off,'='):
        prop,off = nom(text,off+1,varset,trim=True)
        inst[1]['args'].append( prop )

    return inst,off

def parse_macro_join(text,off=0):
    '''
    &foo:bar
    &foo:bar=baz:faz
    &hehe.haha/foo:bar=baz:faz
    '''
    inst = ('join',{'args':[],'kwlist':[]})

    prop,off = nom(text,off,varset,trim=True)

    if len(text) == off:
        inst[1]['args'].append(prop)
        return inst,off

    if text[off] == '/':
        inst[1]['kwlist'].append( ('from',prop) )
        prop,off = nom(text,off+1,varset,trim=True)

    inst[1]['args'].append( prop )

    if len(text) == off:
        return inst,off

    if nextchar(text,off,'='):
        prop,off = nom(text,off+1,varset,trim=True)
        inst[1]['args'].append( prop )

    return inst,off

def parse_ques(text,off=0,trim=True):
    '''
    Parse "query" syntax: tag/prop[@<timewin>][#<limit>][*<by>][=valu]
    '''
    ques = {}

    name,off = nom(text,off,varset,trim=True)

    if not name:
        raise SyntaxError(text=text,off=off,mesg='expected name')

    ques['cmp'] = 'has'
    ques['prop'] = name

    if len(text) == off:
        return ques,off

    if text[off] == '/':

        ques['from'] = name

        off += 1
        name,off = nom(text,off,varset,trim=True)

        ques['prop'] = name

    while True:

        if len(text) == off:
            return ques,off

        if text[off] == '#':
            ques['limit'],off = parse_int(text,off+1,trim=True)
            continue

        if text[off] == '@':
            ques['when'],off = parse_when(text,off+1,trim=True)
            continue

        # NOTE: "by" macro syntax only supports eq so we eat and run
        if text[off] == '*':

            ques['cmp'] = 'by'

            ques['by'],off = nom(text,off+1,varset,trim=True)
            if len(text) == off:
                return ques,off

            if text[off] != '=':
                raise SyntaxError(text=text, off=off, mesg='expected equals for by syntax')

            ques['valu'],off = parse_literal(text,off+1,trim=True)
            return ques,off

        if text[off] == '=':
            ques['cmp'] = 'eq'
            ques['valu'],off = parse_literal(text,off+1,trim=True)
            break

        # TODO: handle "by" syntax

        textpart = text[off:]

        if textpart.startswith('<='):
            ques['cmp'] = 'le'
            ques['valu'],off = parse_literal(text,off+2,trim=True)
            break

        if textpart.startswith('>='):
            ques['cmp'] = 'ge'
            ques['valu'],off = parse_literal(text,off+2,trim=True)
            break

        if textpart.startswith('~='):
            ques['cmp'] = 're'
            ques['valu'],off = parse_literal(text,off+2,trim=True)
            break

        if textpart.startswith('<'):
            ques['cmp'] = 'lt'
            ques['valu'],off = parse_literal(text,off+1,trim=True)
            break

        if textpart.startswith('>'):
            ques['cmp'] = 'gt'
            ques['valu'],off = parse_literal(text,off+1,trim=True)
            break

        break

    return ques,off

def parse_when(text,off,trim=True):
    whenstr,off = nom(text,off,whenset)
    # FIXME validate syntax
    if whenstr.find(',') != -1:
        return tuple(whenstr.split(',',1)),off
    return (whenstr,None),off

def parse_oper(text, off=0):
    '''
    Returns an inst,off tuple by parsing an operator expression.

    Example:

        inst,off = parse_oper('foo("bar",baz=20)')

    '''
    name,off = nom(text,off,varset)

    inst = (name,{'args':[],'kwlist':[]})

    _,off = nom(text,off,whites)

    if text[off] != '(':
        raise Exception('Expected ( for operator %s (at: %d)' % (name,off))

    off += 1
    _,off = nom(text,off,whites)

    # parse arg literals
    while is_literal(text,off):
        valu,off = parse_literal(text,off)
        _,off = nom(text,off,whites)

        inst[1]['args'].append(valu)

        if text[off] == ',':
            off += 1
            _,off = nom(text,off,whites)

    # short circuit with no kwlist...
    if text[off] == ')':
        off += 1
        return inst,off

    while True:
        kwname,off = nom(text,off,varset)
        if not kwname:
            raise Exception('Expected kwarg (at: %d)' % (off,))

        _,off = nom(text,off,whites)

        if text[off] != '=':
            raise Exception('kwarg w/o = (at: %d)' % (off,))

        off += 1

        kwvalu,off = parse_literal(text,off)
        _,off = nom(text,off,whites)

        inst[1]['kwlist'].append( (kwname,kwvalu) )

        if text[off] not in (',',')'):
            raise Exception('Unexpected Token: %s (at: %d)' % (text[off],off))

        if text[off] == ')':
            off += 1
            return inst,off

        # eat the comma
        off += 1
    
    # parse kwlist

def parse(text, off=0):
    '''
    Parse and return a set of instruction tufos.
    '''
    ret = []

    while True:

        # leading whitespace is irrelevant
        _,off = nom(text,off,whites)
        if off >= len(text):
            break

        # handle some special "macro" style syntaxes

        # must() macro syntax: +foo:bar="woot"
        if text[off] == '+':
            inst,off = parse_macro(text,off+1,mode='must')
            ret.append(inst)
            continue

        # cant() macro syntax: -foo:bar=10
        if text[off] == '-':
            inst,off = parse_macro(text,off+1,mode='cant')
            ret.append(inst)
            continue

        # pivot() macro syntax ^foo:bar=baz:faz
        if text[off] == '^':
            inst,off = parse_pivot(text,off+1)
            ret.append(inst)
            continue

        # logical and syntax for multiple filters
        if text[off] == '&':

            if len(ret) == 0:
                raise Exception('logical and with no previous operator')

            prev = ret[-1]
            mode = prev[1].get('mode')

            if mode not in ('cant','must'):
                raise Exception('logical and previous mode: %s (must be must/cant)' % (mode,))

            inst,off = parse_macro(text,off+1,mode=mode)

            if prev[0] != 'and':
                prev = ('and',{'args':[prev,],'kwlist':[],'mode':mode})
                ret[-1] = prev

            prev[1]['args'].append(inst)
            continue

        # logical or syntax for multiple filters
        if text[off] == '|':

            if len(ret) == 0:
                raise Exception('logical or with no previous operator')

            prev = ret[-1]
            mode = prev[1].get('mode')

            if mode not in ('cant','must'):
                raise Exception('logical or previous mode: %s (must be must/cant)' % (mode,))

            inst,off = parse_macro(text,off+1,mode=mode)

            if prev[0] != 'or':
                prev = ('or',{'args':[prev,],'kwlist':[],'mode':mode})
                ret[-1] = prev

            prev[1]['args'].append(inst)
            continue

        # opts() macro syntax: %uniq=0
        if text[off] == '%':
            inst,off = parse_opts(text,off+1)
            ret.append(inst)
            continue

        origoff = off

        name,off = nom(text,off,varset)
        _,off = nom(text,off,whites)

        if len(text) == off:
            inst,off = parse_macro(text,origoff)
            ret.append(inst)
            continue

        # standard foo() oper syntax
        if text[off] == '(':
            inst,off = parse_oper(text,origoff)
            ret.append(inst)
            continue

        # only macro lift syntax remains
        inst,off = parse_macro(text,origoff)
        ret.append(inst)

    [ i[1]['kwlist'].sort() for i in ret ]

    return ret
