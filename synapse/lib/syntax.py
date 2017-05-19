import re

import synapse.lib.sched as s_sched
import synapse.lib.service as s_service

import synapse.exc
from synapse.common import *
from synapse.eventbus import EventBus

'''
This module implements syntax parsing for the storm runtime.
( see synapse/lib/storm.py )
'''

whites = set(' \t\n')
intset = set('01234567890abcdefx')
varset = set('$.:abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345678910')
starset = varset.union({'*'})
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

def meh(txt,off,cset):
    r = ''
    while len(txt) > off and txt[off] not in cset:
        r += txt[off]
        off += 1
    return r,off

def is_literal(text,off):
    return text[off] in '("0123456789'

def parse_literal(text, off,trim=True):
    if text[off] == '(':
        return parse_cmd_list(text,off,trim=trim)

    if text[off] == '"':
        return parse_string(text,off,trim=trim)

    return parse_int(text,off,trim=trim)

def parse_int(text,off,trim=True):
    numstr,off = nom(text,off,intset,trim=trim)
    try:
        return int(numstr,0),off
    except Exception as e:
        raise synapse.exc.SyntaxError(expected='Literal', at=off, got=text[off:off+10])

def parse_list(text,off,trim=True):
    if text[off] != '(':
        raise synapse.exc.SyntaxError(expected='List', at=off)

    off += 1
    valus = []
    while True:

        valu,off = parse_literal(text,off,trim=trim)

        valus.append(valu)

        if text[off] == ')':
            return valus, off + 1

        if text[off] != ',':
            raise synapse.exc.SyntaxError(invalid='List Syntax', at=off)

        off += 1

def nom_whitespace(text,off):
    return nom(text,off,whites)

def isquote(text,off):
    return nextin(text,off,(",",'"'))

def parse_cmd_list(text,off=0,trim=True):
    '''
    Parse a list (likely for comp type) coming from a command line input.

    The string elements within the list may optionally be quoted.
    '''

    if not nextchar(text,off,'('):
        raise synapse.exc.SyntaxError(at=off,mesg='expected open paren for list')

    off += 1

    valus = []
    while off < len(text):

        _,off = nom_whitespace(text,off)

        if isquote(text,off):
            valu,off = parse_string(text,off,trim=trim)
        else:
            valu,off = meh(text,off,',)')
            valu = valu.strip()

        valus.append(valu)

        _,off = nom_whitespace(text,off)

        if nextchar(text,off,')'):
            return valus, off + 1

        if not nextchar(text,off,','):
            raise synapse.exc.SyntaxError(at=off,mesg='expected comma in list')

        off += 1

    raise synapse.exc.SyntaxError(at=off,mesg='unexpected and of text during list')

def parse_cmd_string(text,off,trim=True):
    '''
    Parse in a command line string which may be quoted.
    '''
    if trim:
        _,off = nom(text,off,whites)

    if isquote(text,off):
        return parse_string(text,off,trim=trim)

    if nextchar(text,off,'('):
        return parse_cmd_list(text,off)

    return meh(text,off,whites)

def parse_string(text,off,trim=True):

    if text[off] not in ('"',"'"): # lulz...
        raise synapse.exc.SyntaxError(expected='String Literal', at=off)

    quot = text[off]

    if trim:
        _,off = nom(text,off,whites)

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
        _,off = nom(text,off,whites)

    return ''.join(vals),off

def parse_macro_filt(text,off=0,trim=True, mode='must'):

    if trim:
        _,off = nom(text,off,whites)

    # special + #tag (without prop) based filter syntax
    if nextchar(text,off,'#'):
        _,off = nom(text,off,whites)
        tag,off = nom(text,off+1,starset,trim=True)
        oper = ('filt',{'cmp':'tag','mode':mode,'valu':tag})
        return oper,off

    # check for non-macro syntax
    name,xoff = nom(text,off,varset)
    _,xoff = nom(text,xoff,whites)
    if nextchar(text,xoff,'('):
        inst,off = parse_oper(text,off)

        opfo = {'cmp':inst[0],'mode':mode}

        opfo['args'] = inst[1].get('args',())
        opfo['kwlist'] = inst[1].get('kwlist',())

        return ('filt',opfo),off

    ques,off = parse_ques(text,off,trim=trim)
    ques['mode'] = mode
    return ('filt',ques),off

def parse_macro_lift(text,off=0,trim=True):
    '''
    Parse a "lift" macro and return an inst,off tuple.
    '''
    ques,off = parse_ques(text,off,trim=trim)
    return ('lift',ques),off

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

def nextstr(text,off,valu):
    return text.startswith(valu,off)

def nextin(text,off,vals):
    if len(text) <= off:
        return False
    return text[off] in vals

#def parse_pivot(text,off=0):
    #'''
    #^foo:bar
    #^foo:bar=baz:faz
    #^hehe.haha/foo:bar=baz:faz
    #'''
    #inst = ('pivot',{'args':[],'kwlist':[]})

    #prop,off = nom(text,off,varset,trim=True)

    #if len(text) == off:
        #inst[1]['args'].append(prop)
        #return inst,off

    #if text[off] == '/':
        #inst[1]['kwlist'].append( ('from',prop) )
        #prop,off = nom(text,off+1,varset,trim=True)

    #inst[1]['args'].append( prop )

    #if len(text) == off:
        #return inst,off

    #if nextchar(text,off,'='):
        #prop,off = nom(text,off+1,varset,trim=True)
        #inst[1]['args'].append( prop )

    #return inst,off

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

macrocmps = [
    ('<=','le'),
    ('>=','ge'),
    ('~=','re'),
    ('!=','ne'),
    ('<','lt'),
    ('>','gt'),
    ('=','eq'),
]

def parse_ques(text,off=0,trim=True):
    '''
    Parse "query" syntax: tag/prop[@<timewin>][#<limit>][*<by>][=valu]
    '''
    ques = {}

    name,off = nom(text,off,varset,trim=True)

    if not name:
        raise SyntaxError(text=text, off=off, mesg='expected name')

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

            ques['cmp'],off = nom(text,off+1,varset,trim=True)
            if len(text) == off:
                return ques,off

            if text[off] != '=':
                raise SyntaxError(text=text, off=off, mesg='expected equals for by syntax')

            ques['valu'],off = parse_macro_valu(text,off+1)
            return ques,off

        if text[off] == '=':
            ques['cmp'] = 'eq'
            ques['valu'],off = parse_macro_valu(text,off+1)
            break

        # TODO: handle "by" syntax

        textpart = text[off:]
        for ctxt,cmpr in macrocmps:

            if textpart.startswith(ctxt):
                ques['cmp'] = cmpr
                ques['valu'],off = parse_oarg(text,off+len(ctxt))
                break

        break

    return ques,off

def parse_macro_valu(text,off=0):
    '''
    Special syntax for the right side of equals in a macro
    '''
    if nextchar(text,off,'('):
        return parse_cmd_list(text,off)

    if isquote(text,off):
        return parse_string(text,off)

    # since it's not quoted, we can assume we are white
    # space bound ( only during macro syntax )
    valu,off =  meh(text,off,whites)

    # for now, give it a shot as an int...  maybe eventually
    # we'll be able to disable this completely, but for now
    # lets maintain backward compatibility...
    try:
        # NOTE: this is ugly, but faster than parsing the string
        valu = int(valu,0)
    except ValueError as e:
        pass

    return valu,off


def parse_when(text,off,trim=True):
    whenstr,off = nom(text,off,whenset)
    # FIXME validate syntax
    if whenstr.find(',') != -1:
        return tuple(whenstr.split(',',1)),off
    return (whenstr,None),off

def parse_cmd_kwarg(text, off=0):
    '''
    Parse a foo:bar=<valu> kwarg into (prop,valu),off
    '''
    _,off = nom(text,off,whites)

    prop,off = nom(text,off,varset)

    _,off = nom(text,off,whites)

    if not nextchar(text,off,'='):
        raise synapse.exc.SyntaxError(expected='= for kwarg ' + prop, at=off)

    _,off = nom(text,off+1,whites)

    valu,off = parse_cmd_string(text,off)
    return (prop,valu),off

def parse_cmd_kwlist(text, off=0):
    '''
    Parse a foo:bar=<valu>[,...] kwarg list into (prop,valu),off
    '''
    kwlist = []

    _,off = nom(text,off,whites)

    while off < len(text):

        (p,v),off = parse_cmd_kwarg(text,off=off)

        kwlist.append( (p,v) )

        _,off = nom(text,off,whites)
        if not nextchar(text,off,','):
            break

    _,off = nom(text,off,whites)
    return kwlist,off

def parse_oarg(text, off=0):
    '''
    Parse something that might be a literal *or*
    a kwarg name, *or* an unadorned literal string
    ( which may not use any context sensitive chars )
    '''
    _,off = nom(text,off,whites)

    if is_literal(text,off):
        valu,off = parse_literal(text,off)

    else:
        valu,off = nom(text,off,varset)

    _,off = nom(text,off,whites)
    return valu,off

def parse_oper(text, off=0):
    '''
    Returns an inst,off tuple by parsing an operator expression.

    Example:

        inst,off = parse_oper('foo("bar",baz=20)')

    '''
    name,off = nom(text,off,varset)

    inst = (name,{'args':[],'kwlist':[]})

    _,off = nom(text,off,whites)

    #if text[off] != '(':
    if not nextchar(text,off,'('):
        raise synapse.exc.SyntaxError(expected='( for operator ' + name, at=off)

    off += 1

    while True:

        _,off = nom(text,off,whites)

        if nextchar(text,off,')'):
            off += 1
            return inst,off

        oarg,off = parse_oarg(text,off)

        if nextchar(text,off,'='):
            off += 1
            valu,off = parse_oarg(text,off)
            inst[1]['kwlist'].append( (oarg,valu) )
        else:
            inst[1]['args'].append(oarg)

        if not nextin(text,off,[',',')']):
            raise synapse.exc.SyntaxError(mesg='Unexpected Token: ' + text[off], at=off)

        if nextchar(text,off,','):
            off += 1

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

        # pivot() macro with no src prop:   -> foo:bar
        if nextstr(text,off,'->'):
            _,off = nom(text,off+2,whites)
            name,off = nom(text,off,varset)
            inst = ('pivot',{'args':[name],'kwlist':[]})
            ret.append(inst)
            continue

        # lift by tag alone macro
        if nextstr(text,off,'#'):
            _,off = nom(text,off+1,whites)
            name,off = nom(text,off,varset)
            inst = ('alltag',{'args':[name],'kwlist':[]})
            ret.append(inst)
            continue

        # must() macro syntax: +foo:bar="woot"
        if nextchar(text,off,'+'):
            inst,off = parse_macro_filt(text,off+1,mode='must')
            ret.append(inst)
            continue

        # cant() macro syntax: -foo:bar=10
        if nextchar(text,off,'-'):
            inst,off = parse_macro_filt(text,off+1,mode='cant')
            ret.append(inst)
            continue

        # logical and syntax for multiple filters
        if text[off] == '&':

            if len(ret) == 0:
                raise synapse.exc.SyntaxError(mesg='logical and with no previous operator')

            prev = ret[-1]

            if prev[0] != 'filt':
                raise synapse.exc.SyntaxError(mesg='prev oper must be filter not: %r' % prev)

            mode = prev[1].get('mode')
            inst,off = parse_macro_filt(text,off+1,mode=mode)

            if prev[1].get('cmp') != 'and':
                prev = ('filt',{'args':[prev,],'kwlist':[],'cmp':'and','mode':mode})
                ret[-1] = prev

            prev[1]['args'].append(inst)
            continue

        # logical or syntax for multiple filters
        if text[off] == '|':

            if len(ret) == 0:
                raise synapse.exc.SyntaxError(mesg='logical or with no previous operator')

            prev = ret[-1]

            if prev[0] != 'filt':
                raise synapse.exc.SyntaxError(mesg='prev oper must be filter not: %r' % prev)

            mode = prev[1].get('mode')
            inst,off = parse_macro_filt(text,off+1,mode=mode)

            if prev[1].get('cmp') != 'or':
                prev = ('filt',{'args':[prev,],'kwlist':[],'cmp':'or','mode':mode})
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

        # mop up in the case where we end with a macro
        if len(text) == off:
            inst,off = parse_macro_lift(text,origoff)
            ret.append(inst)
            continue

        # macro foo:bar->baz:faz prop pivot
        if nextstr(text,off,'->'):

            pivn,off = nom(text,off+2,varset)
            inst = ('pivot',{'args':[name],'kwlist':[]})

            # FIXME make a parser for foo.bar/baz:faz*blah#40
            if nextchar(text,off,'/'):
                inst[1]['kwlist'].append( ('from',pivn) )
                pivn,off = nom(text,off+1,varset)

            inst[1]['args'].insert(0, pivn)

            ret.append(inst)
            continue

        # standard foo() oper syntax
        if text[off] == '(':
            inst,off = parse_oper(text,origoff)
            ret.append(inst)
            continue

        # only macro lift syntax remains
        inst,off = parse_macro_lift(text,origoff)
        ret.append(inst)

    #[ i[1]['kwlist'].sort() for i in ret ]

    return ret
