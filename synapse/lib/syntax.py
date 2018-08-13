import collections

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache

'''
This module implements syntax parsing for the storm runtime.
( see synapse/lib/storm.py )
'''

whites = set(' \t\n')
binset = set('01')
decset = set('0123456789')
hexset = set('01234567890abcdef')
intset = set('01234567890abcdefx')
setset = set('.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
varset = set('$.:abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
timeset = set('01234567890')
propset = set(':abcdefghijklmnopqrstuvwxyz_0123456789')
tagfilt = varset.union({'#', '*'})
alphaset = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

mustquote = set(' \t\n),=]}')

# this may be used to meh() potentially unquoted values
valmeh = whites.union({'(', ')', '=', ',', '[', ']', '{', '}'})

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
            raise s_exc.BadSyntaxError(at=off, mesg='0x expected hex')
        valu = int(valu, 16)

    elif nextstr(text, off, '0b'):
        valu, off = nom(text, off + 2, binset)
        if not valu:
            raise s_exc.BadSyntaxError(at=off, mesg='0b expected bits')
        valu = int(valu, 2)

    else:

        valu, off = nom(text, off, decset)
        if not valu:
            raise s_exc.BadSyntaxError(at=off, mesg='expected digits')

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
        raise s_exc.BadSyntaxError(at=off, mesg='expected digits')

    valu += digs

    if nextchar(text, off, '.'):
        frac, off = nom(text, off + 1, decset)
        if not frac:
            raise s_exc.BadSyntaxError(at=off, mesg='expected .<digits>')

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
        raise s_exc.BadSyntaxError(at=off, mesg='expected open paren for list')

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
            raise s_exc.BadSyntaxError(at=off, text=text, mesg='expected comma in list')

        off += 1

    raise s_exc.BadSyntaxError(at=off, mesg='unexpected and of text during list')

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
        raise s_exc.BadSyntaxError(expected='String Literal', at=off)

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
        raise s_exc.BadSyntaxError(text=text, off=off, mesg='expected name')

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
                raise s_exc.BadSyntaxError(text=text, off=off, mesg='expected equals for by syntax')

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
        raise s_exc.BadSyntaxError(expected='= for kwarg ' + prop, at=off)

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
        raise s_exc.BadSyntaxError(expected='( for operator ' + name, at=off)

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
            raise s_exc.BadSyntaxError(mesg='Unexpected Token: ' + text[off], at=off)

        if nextchar(text, off, ','):
            off += 1

def parse_perm(text, off=0):
    # FIXME dead?
    '''
    Parse a permission string
        <name> [<opt>=<match>...]
    '''
    _, off = nom(text, off, whites)

    name, off = nom(text, off, varset)
    if not name:
        raise s_exc.BadSyntaxError(mesg='perm str expected name')

    retn = (name, {})

    _, off = nom(text, off, whites)

    while len(text) > off:

        _, off = nom(text, off, whites)
        meta, off = nom(text, off, varset)
        _, off = nom(text, off, whites)

        if not nextchar(text, off, '='):
            raise s_exc.BadSyntaxError(mesg='perm opt expected =')

        _, off = nom(text, off + 1, whites)

        valu, off = parse_valu(text, off)
        if not isinstance(valu, str):
            raise s_exc.BadSyntaxError(mesg='perm opt %s= expected string' % meta)

        _, off = nom(text, off, whites)

        retn[1][meta] = valu

    return retn, off

def oper(name, *args, **kwargs):
    kwlist = list(sorted(kwargs.items()))
    return (name, {'args': args, 'kwlist': kwlist})

def parse_stormsub(text, off=0):

    _, off = nom(text, off, whites)

    if not nextchar(text, off, '{'):
        raise s_exc.BadSyntaxError('expected { at %d' % (off,))

    _, off = nom(text, off + 1, whites)

    opers, off = parse_storm(text, off)

    if not nextchar(text, off, '}'):
        raise s_exc.BadSyntaxError('expected } at %d' % (off,))

    _, off = nom(text, off + 1, whites)

    return opers, off

tagterm = set('*=)]},@ \t\n')
whitespace = set(' \t\n')

optset = set('abcdefghijklmnopqrstuvwxyz')
varset = set('$.:abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
cmprset = set('!<>@^~=')
cmprstart = set('*@!<>^~=')

cmdset = set('abcdefghijklmnopqrstuvwxyz1234567890.')
alphanum = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

optcast = {
    'limit': int,
    'uniq': bool,
}

class Parser:

    '''
    must be quoted:  ,  )  =
    must be quoted at beginning: . : # @ ( $ etc....
    '''

    def __init__(self, view, text, offs=0):

        self.offs = offs
        self.text = text.strip()
        self.size = len(self.text)

        self.view = view
        self.model = view.model

    def _raiseSyntaxError(self, mesg):
        at = self.text[self.offs:self.offs + 12]
        raise s_exc.BadStormSyntax(mesg=mesg, at=at, text=self.text, offs=self.offs)

    def _raiseSyntaxExpects(self, text):
        self._raiseSyntaxError(f'expected: {text}')

    def more(self):
        return self.offs < self.size

    def query(self):

        self.ignore(whitespace)

        query = s_ast.Query(self.view)
        query.text = self.text

        while True:

            self.ignore(whitespace)

            if not self.more():
                break

            # if we are sub-query, time to go...
            if self.nextstr('}'):
                break

            # | <command> syntax...
            if self.nextstr('|'):

                self.offs += 1

                # trailing | case...
                self.ignore(whitespace)
                if not self.more():
                    break

                # switch to command interpreter...
                name = self.cmdname()
                text = self.cmdtext()

                oper = s_ast.CmdOper(kids=(name, text))
                query.addKid(oper)

                # command is last query text case...
                if not self.more():
                    break

                # back to storm mode...
                if self.nextstr('|'):
                    self.offs += 1
                    continue

                self._raiseSyntaxError('expected | or end of input for cmd')

            # parse a query option: %foo=10
            if self.nextstr('%'):

                self.offs += 1

                self.ignore(whitespace)
                name = self.noms(optset)

                self.ignore(whitespace)
                self.nextmust('=')

                valu = self.noms(alphanum)

                cast = optcast.get(name)
                if cast is None:
                    raise s_exc.NoSuchOpt(name=name)

                try:
                    valu = cast(valu)
                except Exception as e:
                    raise s_exc.BadOptValu(name=name, valu=valu)

                query.opts[name] = valu

                continue

            # edit operations...
            if self.nextstr('['):

                self.offs += 1

                self.ignore(whitespace)
                while not self.nextstr(']'):
                    oper = self.editoper()
                    query.kids.append(oper)
                    self.ignore(whitespace)

                self.offs += 1
                continue

            oper = self.oper()
            query.addKid(oper)

            self.ignore(whitespace)

            #if self.nextstr('{'):
                #self.offs += 1
                #oper = self.query()

        return query

    def editoper(self):

        self.ignore(whitespace)

        if self.nextstr(':'):
            return self.editpropset()

        if self.nextstr('.'):
            return self.editunivset()

        if self.nextstr('+#'):
            return self.edittagadd()

        if self.nextstr('-:'):
            return self.editpropdel()

        if self.nextstr('-#'):
            return self.edittagdel()

        if self.nextstr('-'):
            return self.editnodedel()

        return self.editnodeadd()

    def editnodeadd(self):
        '''
        foo:bar = hehe
        '''

        self.ignore(whitespace)

        absp = self.absprop()

        self.ignore(whitespace)

        if not self.nextstr('='):
            self._raiseSyntaxExpects('=')

        self.offs += 1

        self.ignore(whitespace)

        valu = self.valu()

        return s_ast.EditNodeAdd(kids=(absp, valu))

    def editnodedel(self):
        '''
        -foo:bar
        '''
        self.ignore(whitespace)

        self.nextmust('-')

        absp = self.absprop()
        return s_ast.EditNodeDel(kids=(absp,))

    def nextmust(self, text):

        if not self.nextstr(text):
            raise self._raiseSyntaxExpects(text)

        self.offs += len(text)

    def editpropset(self):
        '''
        :foo=10
        '''

        self.ignore(whitespace)

        if not self.nextstr(':'):
            self._raiseSyntaxExpects(':')

        relp = self.relprop()
        self.ignore(whitespace)

        self.nextmust('=')

        self.ignore(whitespace)

        valu = self.valu()
        return s_ast.EditPropSet(kids=(relp, valu))

    def editunivset(self):
        '''
        .foo = bar
        '''
        self.ignore(whitespace)

        if not self.nextstr('.'):
            self._raiseSyntaxExpects('.')

        univ = self.univprop()
        self.ignore(whitespace)

        self.nextmust('=')

        self.ignore(whitespace)

        valu = self.valu()
        return s_ast.EditPropSet(kids=(univ, valu))

    def editpropdel(self):

        self.ignore(whitespace)

        self.nextmust('-')

        relp = self.relprop()
        return s_ast.EditPropDel(kids=(relp,))

    def edittagadd(self):

        self.ignore(whitespace)

        self.nextmust('+')

        tag = self.tag()

        self.ignore(whitespace)

        if not self.nextstr('='):
            return s_ast.EditTagAdd(kids=(tag,))

        self.offs += 1

        valu = self.valu()
        return s_ast.EditTagAdd(kids=(tag, valu))

    def edittagdel(self):

        self.ignore(whitespace)

        self.nextmust('-')

        tag = self.tag()

        return s_ast.EditTagDel(kids=(tag,))

    def formpivotin(self):
        '''
        <- *
        '''

        self.ignore(whitespace)

        self.nextmust('<-')

        self.ignore(whitespace)

        if self.nextchar() == '*':
            self.offs += 1
            return s_ast.PivotIn()

        prop = self.absprop()
        return s_ast.PivotInFrom(kids=(prop,))

    def formjoinin(self):
        '''
        <+- *
        '''

        self.ignore(whitespace)

        self.nextmust('<+-')

        self.ignore(whitespace)

        self.nextmust('*')

        return s_ast.PivotIn(isjoin=True)

    def formpivot(self):

        self.ignore(whitespace)

        self.nextmust('->')

        self.ignore(whitespace)

        # check for pivot out syntax
        if self.nextchar() == '*':
            self.offs += 1
            return s_ast.PivotOut()

        prop = self.absprop()
        return s_ast.FormPivot(kids=(prop,))

    def formjoin(self):

        self.ignore(whitespace)

        self.nextmust('-+>')

        self.ignore(whitespace)

        # check for pivot out syntax
        if self.nextchar() == '*':
            self.offs += 1
            return s_ast.PivotOut(isjoin=True)

        prop = self.absprop()
        return s_ast.FormPivot(kids=(prop,), isjoin=True)

    def proppivot(self, prop):
        '''
        :foo:bar -> baz:faz
        '''
        pval = s_ast.RelPropValue(kids=(prop,))

        self.ignore(whitespace)

        self.nextmust('->')

        self.ignore(whitespace)

        if self.nextchar() == '*':
            self.offs += 1
            return s_ast.PropPivotOut(kids=(prop,))

        dest = self.absprop()
        return s_ast.PropPivot(kids=(pval, dest))

    def propjoin(self, prop):
        '''
        :foo:bar -+> baz:faz
        '''
        pval = s_ast.RelPropValue(kids=(prop,))

        self.ignore(whitespace)

        self.nextmust('-+>')

        self.ignore(whitespace)

        dest = self.absprop()
        return s_ast.PropPivot(kids=(pval, dest), isjoin=True)

    def oper(self):
        '''
        '''

        self.ignore(whitespace)

        if not self.more():
            self._raiseSyntaxError('unexpected end of query text')

        if self.nextstr('{'):
            return self.subquery()

        # some syntax elements prior to a prop/oper name...
        if self.nextstr('->'):
            return self.formpivot()

        if self.nextstr('-+>'):
            return self.formjoin()

        if self.nextstr('<-'):
            return self.formpivotin()

        if self.nextstr('<+-'):
            return self.formjoinin()

        char = self.nextchar()

        # $foo = valu var assignment
        if char == '$':

            varn = self.varname()

            self.ignore(whitespace)

            # TODO special var assigments for lists?
            self.nextmust('=')

            self.ignore(whitespace)

            valu = self.valu()

            kids = (varn, valu)
            return s_ast.VarSetOper(kids=kids)

        if char in ('+', '-'):
            return self.filtoper()

        if char == '#':
            return self.liftbytag()

        # :foo:bar relative property
        if char == ':':

            prop = self.relprop()

            # :foo=10 here could be assignment...

            self.ignore(whitespace)
            if self.nextstr('->'):
                return self.proppivot(prop)

            if self.nextstr('-+>'):
                return self.propjoin(prop)

            if self.nextstrs('<-', '<+-'):
                self._raiseSyntaxError('Pivot in syntax does not currently support relative properties.')

        name = self.noms(varset)
        if not name:
            self._raiseSyntaxError('unknown query syntax')

        # before ignoring more whitespace, check for form#tag=time
        if self.model.forms.get(name) is not None and self.nextstr('#'):

            tag = self.tag()
            form = s_ast.Const(name)

            self.ignore(whitespace)

            if self.nextchar() not in cmprstart:
                return s_ast.LiftFormTag(kids=(form, tag))

            cmpr = self.cmpr()

            self.ignore(whitespace)

            valu = self.valu()

            return s_ast.LiftFormTag(kids=(form, tag, cmpr, valu))

        if self.model.props.get(name) is None:

            if self.view.core.getStormCmd(name) is not None:

                text = self.cmdtext()
                self.ignore(whitespace)

                # eat a trailing | from a command at the beginning
                if self.nextstr('|'):
                    self.offs += 1

                return s_ast.CmdOper(kids=(s_ast.Const(name), text))

        # we have a prop <cmpr> <valu>!
        if self.nextchar() in cmprstart:

            # TODO: check for :: pivot syntax and raise

            cmpr = self.cmpr()
            valu = self.valu()

            kids = (s_ast.Const(name), cmpr, valu)
            return s_ast.LiftPropBy(kids=kids)

        # lift by prop only
        return s_ast.LiftProp(kids=(s_ast.Const(name),))

    def liftbytag(self):

        self.ignore(whitespace)

        tag = self.tag()

        self.ignore(whitespace)
        cmprstart

        #TODO
        #if self.nextstr('@='):

        return s_ast.LiftTag(kids=(tag,))

    def filtoper(self):

        self.ignore(whitespace)

        pref = self.nextchar()
        if pref not in ('+', '-'):
            self._raiseSyntaxError('expected: + or -')

        self.offs += 1

        cond = self.cond()

        kids = (
            s_ast.Const(pref),
            cond,
        )
        return s_ast.FiltOper(kids=kids)

    def cond(self):
        '''

        :foo
        :foo=20
        :foo:bar=$baz
        :foo:bar=:foo:baz

        foo:bar
        foo:bar:baz=20

        #foo.bar

        #foo.bar@2013

        (:foo=10 and ( #foo or #bar ))

        '''

        self.ignore(whitespace)

        if self.nextstr('('):
            return self.condexpr()

        if self.nextstr(':'):

            name = self.relprop()

            self.ignore(whitespace)

            if self.nextchar() not in cmprstart:
                return s_ast.HasRelPropCond(kids=(name,))

            cmpr = self.cmpr()

            self.ignore(whitespace)
            valu = self.valu()

            return s_ast.RelPropCond(kids=(name, cmpr, valu))

        if self.nextstr('.'):

            name = self.univprop()
            self.ignore(whitespace)

            if self.nextchar() not in cmprstart:
                return s_ast.HasRelPropCond(kids=(name,))

            cmpr = self.cmpr()

            self.ignore(whitespace)
            valu = self.valu()

            return s_ast.RelPropCond(kids=(name, cmpr, valu))

        if self.nextstr('#'):

            tag = self.tag()

            self.ignore(whitespace)

            if self.nextchar() not in cmprstart:
                return s_ast.TagCond(kids=(tag,))

            cmpr = self.cmpr()
            self.ignore(whitespace)

            valu = self.valu()

            return s_ast.TagValuCond(kids=(tag, cmpr, valu))

        prop = self.absprop()

        self.ignore(whitespace)

        if self.nextchar() not in cmprstart:
            return s_ast.HasAbsPropCond(kids=(prop,))
        # Special case of pivot operations which ALSO start with cmprstart chars
        if self.nextstrs('<-', '<+-'):
            return s_ast.HasAbsPropCond(kids=(prop,))

        cmpr = self.cmpr()

        self.ignore(whitespace)
        valu = self.valu()

        return s_ast.AbsPropCond(kids=(prop, cmpr, valu))

    def condexpr(self):

        self.ignore(whitespace)

        self.nextmust('(')

        cond = self.cond()

        while True:

            self.ignore(whitespace)

            if self.nextchar() == ')':
                self.offs += 1
                return cond

            if self.nextstr('and'):
                self.offs += 3
                othr = self.cond()
                cond = s_ast.AndCond(kids=(cond, othr))
                continue

            if self.nextstr('or'):
                self.offs += 2
                othr = self.cond()
                cond = s_ast.OrCond(kids=(cond, othr))
                continue

            if self.nextstr('not'):
                self.offs += 3
                othr = self.cond()
                cond = s_ast.NotCond(kids=(cond, othr))
                continue

            self._raiseSyntaxError('un-recognized condition expression')

    def absprop(self):
        '''
        foo:bar
        '''
        self.ignore(whitespace)

        name = self.noms(varset)

        if self.model.prop(name) is None:
            self._raiseSyntaxError(f'no such property: {name!r}')

        return s_ast.AbsProp(name)

    def relprop(self):
        '''
        :foo:bar
        '''
        self.ignore(whitespace)

        self.nextmust(':')

        name = self.noms(varset)
        if not name:
            self._raiseBadSyntax('empty relative property name')

        return s_ast.RelProp(name)

    def univprop(self):
        '''
        .foo
        '''
        self.ignore(whitespace)

        if not self.nextstr('.'):
            self._raiseBadSyntax('universal property expected .')

        name = self.noms(varset)
        if not name:
            self._raiseBadSyntax('empty relative property name')

        return s_ast.RelProp(name)

    def cmpr(self):

        self.ignore(whitespace)

        if self.nextstr('*'):

            text = self.expect('=')
            if text is None:
                raise self._raiseSyntaxError('comparison with * but not =')

            return s_ast.Const(text)

        if self.nextchar() not in cmprset:
            self._raiseSyntaxError('expected valid comparison char')

        text = self.noms(cmprset)
        return s_ast.Const(text)

    def valu(self):

        self.ignore(whitespace)

        # a simple whitespace separated string
        nexc = self.nextchar()
        if nexc in alphanum or nexc == '-':
            text = self.noms(until=mustquote)
            return s_ast.Const(text)

        if self.nextstr('('):
            kids = self.valulist()
            # TODO Value() ctor convention...
            return s_ast.List(None, kids=kids)

        if self.nextstr(':'):
            prop = self.relprop()
            return s_ast.RelPropValue(kids=(prop,))

        if self.nextstr('#'):
            tag = self.tag()
            return s_ast.TagPropValue(kids=(tag,))

        if self.nextstr('$'):
            varn = self.varname()
            return s_ast.VarValue(kids=(varn,))

        if self.nextstr('"'):
            text = self.quoted()
            return s_ast.Const(text)

        self._raiseSyntaxError('unrecognized value prefix')

    def varname(self):

        self.ignore(whitespace)

        self.nextmust('$')

        self.ignore(whitespace)

        name = self.noms(alphanum)
        if not name:
            self._raiseSyntaxError('expected variable name')

        return s_ast.Const(name)

    def cmdname(self):

        self.ignore(whitespace)

        name = self.noms(cmdset)
        if not name:
            self._raiseSyntaxError(f'expected cmd name')

        return s_ast.Const(name)

    def cmdtext(self):
        '''
        --bar baz faz

        Terminated by unescaped |
        '''
        # TODO: pipe escape syntax...
        self.ignore(whitespace)
        text = self.noms(until='|').strip()
        return s_ast.Const(text)

    def quoted(self):

        self.ignore(whitespace)

        self.nextmust('"')

        text = ''

        offs = self.offs
        while offs < self.size:

            c = self.text[offs]
            offs += 1

            if c == '"':

                self.offs = offs
                return text

            if c == '\\':
                text += self.text[offs]
                offs += 1
                continue

            text += c

        self._raiseSytaxError('unexpected end of query text')

    def valulist(self):

        self.ignore(whitespace)

        self.nextmust('(')

        vals = []

        while True:

            self.ignore(whitespace)

            if self.nextstr(')'):
                self.offs += 1
                return vals

            vals.append(self.valu())
            self.ignore(whitespace)

            if self.nextstr(')'):
                self.offs += 1
                return vals

            self.nextmust(',')

    def subquery(self):

        self.ignore(whitespace)

        if not self.nextstr('{'):
            raise FOO

        self.eat(1, ignore=whitespace)

        subq = s_ast.SubQuery()

        while self.more():

            self.ignore(whitespace)

            oper = self.oper()
            if self.nextchar() == '}':
                self.offs += 1
                break

        self.ignore(whitespace)
        return subq

    def tag(self):

        self.ignore(whitespace)

        self.nextmust('#')

        self.ignore(whitespace)

        # a bit odd, but the tag could require quoting...
        #if self.nextchar() == '"':

        text = self.noms(until=tagterm)

        return s_ast.Tag(text)

    ###########################################################################
    # parsing helpers from here down...

    def expect(self, text):

        retn = ''

        offs = self.offs

        while offs < len(self.text):

            retn += self.text[offs]

            offs += 1

            if retn.endswith(text):
                self.offs = offs
                return retn

        raise self._raiseSyntaxExpects(text)

    def noms(self, chars=None, until=None, ignore=None):

        if ignore is not None:
            self.ignore(ignore)

        rets = []

        while self.more():

            c = self.nextchar()
            if until is not None and c in until:
                break

            if chars is not None and c not in chars:
                break

            self.offs += 1
            rets.append(c)

        if ignore is not None:
            self.ignore(ignore)

        return ''.join(rets)

    def nextstr(self, text):

        if not self.more():
            return False

        size = len(text)
        subt = self.text[self.offs:self.offs + size]
        return subt == text

    def nextstrs(self, *texts):
        if not self.more():
            return False
        sd = self.getSortedDict(*texts)
        for size, valus in sd.items():
            subt = self.text[self.offs:self.offs + size]
            if subt in valus:
                return True
        return False

    @s_cache.memoize()
    def getSortedDict(self, *texts):
        d = collections.defaultdict(list)
        for text in texts:
            d[len(text)].append(text)
        ret = {k: d[k] for k in sorted(d.keys())}
        return ret

    def nextchar(self):
        if not self.more():
            return None
        return self.text[self.offs]

    def ignore(self, charset):
        while self.nextchar() in charset:
            self.offs += 1

    def eat(self, size, ignore=None):
        self.offs += size
        if ignore is not None:
            self.ignore(ignore)

def parse_storm(text, off=0):

    ret = []
    while True:

        # leading whitespace is irrelevant
        _, off = nom(text, off, whites)
        if off >= len(text):
            break

        # handle a sub-query terminator
        if nextchar(text, off, '}'):
            break

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
                    raise s_exc.BadSyntaxError(mesg='unexpected end of query text in edit mode')

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
                    raise s_exc.BadSyntaxError(mesg='edit macro expected prop=valu syntax')

                _, off = nom(text, off, whites)
                if not nextchar(text, off, '='):
                    raise s_exc.BadSyntaxError(mesg='edit macro expected prop=valu syntax')

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

            _, off = nom(text, off + 1, whites)

            # subquery filter syntax
            if nextchar(text, off, '{'):
                opers, off = parse_stormsub(text, off)
                ret.append(oper('filtsub', True, opers))
                continue

            inst, off = parse_macro_filt(text, off, mode='must')
            ret.append(inst)
            continue

        # cant() macro syntax: -foo:bar=10
        if nextchar(text, off, '-'):

            _, off = nom(text, off + 1, whites)

            # subquery filter syntax
            if nextchar(text, off, '{'):
                opers, off = parse_stormsub(text, off)
                ret.append(oper('filtsub', False, opers))
                continue

            inst, off = parse_macro_filt(text, off, mode='cant')
            ret.append(inst)
            continue

        # logical and syntax for multiple filters
        if text[off] == '&':

            if len(ret) == 0:
                raise s_exc.BadSyntaxError(mesg='logical and with no previous operator')

            prev = ret[-1]

            if prev[0] != 'filt':
                raise s_exc.BadSyntaxError(mesg='prev oper must be filter not: %r' % prev)

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
                raise s_exc.BadSyntaxError(mesg='logical or with no previous operator')

            prev = ret[-1]

            if prev[0] != 'filt':
                raise s_exc.BadSyntaxError(mesg='prev oper must be filter not: %r' % prev)

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

    return ret, off

def parse(text, off=0):
    '''
    Parse and return a set of instruction tufos.
    '''
    retn, off = parse_storm(text, off=off)
    if off != len(text):
        raise s_exc.BadSyntaxError('trailing text: %s' % (text[off:],))

    return retn
