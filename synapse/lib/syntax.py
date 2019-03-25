import collections

import regex

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
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


cmdquote = set(' \t\n|}')
mustquote = set(' \t\n),=]}|')

# this may be used to meh() potentially unquoted values
valmeh = whites.union({'(', ')', '=', ',', '[', ']', '{', '}'})

recache = {}

scmdre = regex.compile('[a-z][a-z0-9.]+')
univre = regex.compile(r'\.[a-z][a-z0-9]+([:.][a-z0-9]+)*')
propre = regex.compile(r'[a-z][a-z0-9]+(:[a-z0-9]+)+([:.][a-z][a-z0-9]+)*')
formre = regex.compile(r'[a-z][a-z0-9]+(:[a-z0-9]+)+')

def isPropName(name):
    return propre.fullmatch(name) is not None

def isCmdName(name):
    return scmdre.fullmatch(name) is not None

def isUnivName(name):
    return univre.fullmatch(name) is not None

def isFormName(name):
    return formre.fullmatch(name) is not None

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
            raise s_exc.BadSyntax(at=off, mesg='0x expected hex')
        valu = int(valu, 16)

    elif nextstr(text, off, '0b'):
        valu, off = nom(text, off + 2, binset)
        if not valu:
            raise s_exc.BadSyntax(at=off, mesg='0b expected bits')
        valu = int(valu, 2)

    else:

        valu, off = nom(text, off, decset)
        if not valu:
            raise s_exc.BadSyntax(at=off, mesg='expected digits')

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
        raise s_exc.BadSyntax(at=off, mesg='expected digits')

    valu += digs

    if nextchar(text, off, '.'):
        frac, off = nom(text, off + 1, decset)
        if not frac:
            raise s_exc.BadSyntax(at=off, mesg='expected .<digits>')

        valu = valu + '.' + frac

    return float(valu), off

def nom_whitespace(text, off):
    return nom(text, off, whites)

def isquote(text, off):
    return nextin(text, off, (",", '"', "'"))

def parse_list(text, off=0, trim=True):
    '''
    Parse a list (likely for comp type) coming from a command line input.

    The string elements within the list may optionally be quoted.
    '''

    if not nextchar(text, off, '('):
        raise s_exc.BadSyntax(at=off, mesg='expected open paren for list')

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
            raise s_exc.BadSyntax(at=off, text=text, mesg='expected comma in list')

        off += 1

    raise s_exc.BadSyntax(at=off, mesg='unexpected and of text during list')

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
        raise s_exc.BadSyntax(expected='String Literal', at=off)

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
    except ValueError:
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
        raise s_exc.BadSyntax(expected='= for kwarg ' + prop, at=off)

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


tagterm = set('*=)]},@ \t\n')
tagmatchterm = set('=)]},@ \t\n')

whitespace = set(' \t\n')

optset = set('abcdefghijklmnopqrstuvwxyz')
varset = set('$.:abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
cmprset = set('!<>@^~=')
cmprstart = set('*@!<>^~=')

cmdset = set('abcdefghijklmnopqrstuvwxyz1234567890.')
alphanum = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

varchars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')

class Parser:

    '''
    must be quoted:  ,  )  =
    must be quoted at beginning: . : # @ ( $ etc....
    '''

    def __init__(self, text, offs=0):
        '''
        Args:
            text (str): The query text to parse.
        '''
        self.offs = offs
        assert text is not None
        self.text = text.strip()
        self.size = len(self.text)

    def _raiseSyntaxError(self, mesg, **kwargs):
        at = self.text[self.offs:self.offs + 12]
        raise s_exc.BadSyntax(mesg=mesg, at=at, text=self.text, offs=self.offs, **kwargs)

    def _raiseSyntaxExpects(self, text):
        self._raiseSyntaxError(f'expected: {text}')

    def more(self):
        return self.offs < self.size

    def query(self):

        self.ignore(whitespace)

        query = s_ast.Query()
        query.text = self.text

        while True:

            self.ignorespace()

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

                if self.nextchar() in (None, '}', '|'):
                    self._raiseSyntaxError('Trailing | with no subsequent query/cmd.')

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

            self.ignorespace()

        return query

    def stormcmd(self):
        '''
        A storm sub-query aware command line splitter.
        ( not for storm commands, but for commands which may take storm )
        '''
        argv = []
        while self.more():
            self.ignore(whitespace)
            if self.nextstr('{'):
                self.offs += 1
                start = self.offs
                self.query()
                argv.append('{' + self.text[start:self.offs] + '}')
                self.nextmust('}')
                continue

            argv.append(self.cmdvalu(until=whitespace))
        return argv

    def cmdvalu(self, until=cmdquote):
        '''
        Consume and return one command argument, stopping when it hits a character (not in a quotation) in `until`.
        '''
        self.ignore(whitespace)
        if self.nextstr('"'):
            return self.quoted()
        if self.nextstr("'"):
            return self.singlequoted()
        return self.noms(until=until)

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

        if self.nextstr('-.'):
            return self.editunivdel()

        if self.nextstr('-#'):
            return self.edittagdel()

        if self.nextstr('-'):
            self._raiseSyntaxError('Cannot delete nodes via edit syntax. Use the delnode command instead.')

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

    def editunivdel(self):

        self.ignore(whitespace)

        self.nextmust('-')

        univ = self.univprop()
        return s_ast.EditUnivDel(kids=(univ,))

    def edittagadd(self):

        self.ignore(whitespace)

        self.nextmust('+')

        tag = self.tagname()

        self.ignore(whitespace)

        if not self.nextstr('='):
            return s_ast.EditTagAdd(kids=(tag,))

        self.offs += 1

        valu = self.valu()
        return s_ast.EditTagAdd(kids=(tag, valu))

    def edittagdel(self):

        self.ignore(whitespace)

        self.nextmust('-')

        tag = self.tagname()

        return s_ast.EditTagDel(kids=(tag,))

    def formpivotin(self):
        '''
        <- * / <- prop
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
        <+- * / <+- prop
        '''

        self.ignore(whitespace)

        self.nextmust('<+-')

        self.ignore(whitespace)

        if self.nextchar() == '*':
            self.offs += 1
            return s_ast.PivotIn(isjoin=True)

        prop = self.absprop()
        return s_ast.PivotInFrom(kids=(prop,), isjoin=True)

    def formpivot(self):
        '''
        -> *
        -> #tag.match
        -> form:prop
        -> form
        '''

        self.ignore(whitespace)

        self.nextmust('->')

        self.ignore(whitespace)

        if self.nextchar() == '#':
            match = self.tagmatch()
            return s_ast.PivotToTags(kids=(match,))

        # check for pivot out syntax
        if self.nextchar() == '*':
            self.offs += 1
            return s_ast.PivotOut()

        prop = self.absprop()
        return s_ast.FormPivot(kids=(prop,))

    def tagmatch(self):

        self.ignore(whitespace)

        self.nextmust('#')

        if self.nextstr('$'):
            return self.varvalu()

        text = self.noms(until=tagmatchterm)

        return s_ast.TagMatch(text)

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

    def ignorespace(self):
        '''
        Ignore whitespace as well as comment syntax // and /* */
        '''

        while True:

            self.ignore(whitespace)

            if self.nextstr('//'):
                self.noms(until='\n')
                continue

            if self.nextstr('/*'):
                self.expect('*/')
                continue

            break

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

        if self.nextstr('##'):
            return self.lifttagtag()

        char = self.nextchar()

        # var list assignment
        # ($foo, $bar) = $baz
        if char == '(':
            varl = self.varlist()

            self.ignore(whitespace)

            self.nextmust('=')
            self.ignore(whitespace)

            valu = self.valu()

            return s_ast.VarListSetOper(kids=(varl, valu))

        # $foo = valu var assignment
        if char == '$':

            varn = self.varname()

            self.ignore(whitespace)

            if self.nextstr('='):

                self.offs += 1

                self.ignore(whitespace)

                valu = self.valu()

                kids = (varn, valu)
                return s_ast.VarSetOper(kids=kids)

            # we will allow a free-standing varvalu to be
            # evaluated here to allow library calls...
            valu = self.varvalu(varn=varn)
            return s_ast.VarEvalOper(kids=(valu,))

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

        tokn = self.peek(varset)
        if tokn == 'for':
            return self.forloop()

        if tokn == 'switch':
            return self.switchcase()

        if tokn == 'break':
            self.offs += 5
            return s_ast.BreakOper()

        if tokn == 'continue':
            self.offs += 8
            return s_ast.ContinueOper()

        name = self.noms(varset)
        if not name:
            self._raiseSyntaxError('unknown query syntax')

        if isPropName(name) or isUnivName(name):

            # before ignoring more whitespace, check for form#tag[=time]
            if self.nextstr('#'):

                tag = self.tagname()
                form = s_ast.Const(name)

                self.ignore(whitespace)

                kids = [form, tag]

                if self.nextchar() in cmprstart:
                    kids.append(self.cmpr())
                    kids.append(self.valu())

                return s_ast.LiftFormTag(kids=kids)

            self.ignore(whitespace)

            # we need pivots to take prec over cmpr
            if not self.nextstrs('->', '<-', '-+>', '<+-'):

                if self.nextchar() in cmprstart:

                    cmpr = self.cmpr()
                    valu = self.valu()

                    kids = (s_ast.Const(name), cmpr, valu)
                    return s_ast.LiftPropBy(kids=kids)

            # lift by prop only
            return s_ast.LiftProp(kids=(s_ast.Const(name),))

        # If we get here it must be either <cmdname>[ <args...>]<|EOF>
        if isCmdName(name):

            argv = self.cmdargv()

            self.ignore(whitespace)

            char = self.nextchar()
            if char not in ('|', '}', None):
                mesg = 'Expected | or end of input for cmd.'
                self._raiseSyntaxError(mesg=mesg)

            return s_ast.CmdOper(kids=(s_ast.Const(name), argv))

        self._raiseSyntaxError(mesg=f'Expected a property name or command.', name=name)

    def casevalu(self):

        self.ignorespace()

        if self.nextstr('"'):
            text = self.quoted()
            self.ignorespace()
            self.nextmust(':')
            return s_ast.Const(text)

        text = self.noms(until=':').strip()
        if not text:
            self._raiseSyntaxError('empty case statement')

        self.nextmust(':')
        return s_ast.Const(text)

    def switchcase(self):

        self.ignore(whitespace)
        self.nextmust('switch')
        self.ignore(whitespace)

        varn = self.varvalu()

        self.ignore(whitespace)

        self.nextmust('{')

        kids = [varn]

        while self.more():

            self.ignorespace()

            if self.nextstr('}'):
                self.offs += 1
                break

            if self.nextstr('*'):

                self.offs += 1
                self.ignore(whitespace)
                self.nextmust(':')

                subq = self.subquery()

                cent = s_ast.CaseEntry(kids=[subq])
                kids.append(cent)
                continue

            valu = self.casevalu()
            if not isinstance(valu, s_ast.Const):
                self._raiseSyntaxError('Switch case syntax only supports const values.')

            self.ignorespace()

            subq = self.subquery()
            cent = s_ast.CaseEntry(kids=[valu, subq])

            kids.append(cent)

        return s_ast.SwitchCase(kids=kids)

    def varlist(self):

        self.ignore(whitespace)
        self.nextmust('(')

        names = []
        while True:

            self.ignore(whitespace)

            varn = self.varname()
            names.append(varn.value())

            self.ignore(whitespace)
            if self.nextstr(')'):
                self.offs += 1
                break

            self.nextmust(',')

        return s_ast.VarList(names)

    def forloop(self):

        self.ignore(whitespace)

        self.nextmust('for')

        self.ignore(whitespace)

        if self.nextstr('$'):
            vkid = self.varname()

        elif self.nextstr('('):
            vkid = self.varlist()

        else:
            self._raiseSyntaxError('expected variable name or variable list')

        self.ignore(whitespace)

        self.nextmust('in')
        self.ignore(whitespace)

        ikid = self.varvalu()
        qkid = self.subquery()

        return s_ast.ForLoop(kids=(vkid, ikid, qkid))

    def liftbytag(self):

        self.ignore(whitespace)

        kids = [self.tagname()]

        self.ignore(whitespace)

        if self.nextstr('@='):
            kids.append(self.cmpr())
            kids.append(self.valu())

        return s_ast.LiftTag(kids=kids)

    def lifttagtag(self):

        self.ignore(whitespace)

        self.nextmust('#')

        kids = [self.tagname()]

        if self.nextstr('@='):
            kids.append(self.cmpr())
            kids.append(self.valu())

        return s_ast.LiftTagTag(kids=kids)

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

        if self.nextstr('{'):
            return self.condsubq()

        if self.nextstr('not'):
            self.offs += 3
            cond = self.cond()
            return s_ast.NotCond(kids=(cond,))

        if self.nextstr(':'):

            name = self.relprop()

            self.ignore(whitespace)

            if self.nextchar() not in cmprstart:
                return s_ast.HasRelPropCond(kids=[name])

            prop = s_ast.RelPropValue(kids=[name])

            cmpr = self.cmpr()

            self.ignore(whitespace)
            valu = self.valu()

            return s_ast.RelPropCond(kids=(prop, cmpr, valu))

        if self.nextstr('.'):

            name = self.univprop()
            self.ignore(whitespace)

            if self.nextchar() not in cmprstart:
                return s_ast.HasRelPropCond(kids=(name,))

            prop = s_ast.RelPropValue(kids=[name])
            cmpr = self.cmpr()

            self.ignore(whitespace)
            valu = self.valu()

            return s_ast.RelPropCond(kids=(prop, cmpr, valu))

        if self.nextstr('#'):

            tag = self.tagmatch()

            self.ignore(whitespace)

            if self.nextchar() not in cmprstart:
                return s_ast.TagCond(kids=(tag,))

            # Special case of pivot operations which ALSO start with cmprstart chars
            if self.nextstrs('<-', '<+-'):
                return s_ast.TagCond(kids=(tag,))

            if '*' in tag.value():
                self._raiseSyntaxError('* globbing is not supported in tag/value combinations.')

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

    def condsubq(self):

        self.ignorespace()

        self.nextmust('{')

        quer = self.query()

        self.nextmust('}')

        self.ignorespace()

        if self.nextchar() not in cmprstart:
            return s_ast.SubqCond(kids=(quer,))

        cmpr = self.cmpr()

        self.ignorespace()

        valu = self.valu()

        return s_ast.SubqCond(kids=(quer, cmpr, valu))

    def condexpr(self):

        self.ignore(whitespace)

        self.nextmust('(')

        self.ignore(whitespace)

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

            self._raiseSyntaxError('un-recognized condition expression')

    def absprop(self):
        '''
        foo:bar
        '''
        self.ignore(whitespace)

        name = self.noms(varset)

        if not name:
            mesg = 'Expected a form/prop name.'
            self._raiseSyntaxError(mesg=mesg)

        if not isPropName(name):
            self._raiseSyntaxError(f'invalid property: {name!r}')

        return s_ast.AbsProp(name)

    def relprop(self):
        '''
        :foo:bar
        '''
        self.ignore(whitespace)

        self.nextmust(':')

        name = self.noms(varset)
        if not name:
            self._raiseSyntaxError('empty relative property name')

        return s_ast.RelProp(name)

    def univprop(self):
        '''
        .foo
        '''
        self.ignore(whitespace)

        if not self.nextstr('.'):
            self._raiseSyntaxError('universal property expected .')

        name = self.noms(varset)
        if not name:
            mesg = 'Expected a univeral property name.'
            self._raiseSyntaxError(mesg=mesg)

        if not isUnivName(name):
            self._raiseSyntaxError(f'no such universal property: {name!r}')

        return s_ast.UnivProp(name)

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

    def relpropvalu(self):
        self.ignore(whitespace)
        name = self.relprop()
        return s_ast.RelPropValue(kids=[name])

    def univpropvalu(self):
        prop = self.univprop()
        return s_ast.UnivPropValue(kids=(prop,))

    def valu(self):

        self.ignore(whitespace)

        # a simple whitespace separated string
        nexc = self.nextchar()
        if nexc in alphanum or nexc in ('-', '?'):
            text = self.noms(until=mustquote)
            return s_ast.Const(text)

        if self.nextstr('('):
            kids = self.valulist()
            # TODO Value() ctor convention...
            return s_ast.List(None, kids=kids)

        if self.nextstr(':'):
            return self.relpropvalu()

        if self.nextstr('.'):
            return self.univpropvalu()

        if self.nextstr('#'):
            tag = self.tagname()
            return s_ast.TagPropValue(kids=(tag,))

        if self.nextstr('$'):
            return self.varvalu()

        if self.nextstr('"'):
            text = self.quoted()
            return s_ast.Const(text)

        if self.nextstr("'"):
            text = self.singlequoted()
            return s_ast.Const(text)

        self._raiseSyntaxError('unrecognized value prefix')

    def varname(self):

        self.ignore(whitespace)

        self.nextmust('$')
        return self.vartokn()

    def vartokn(self):

        self.ignore(whitespace)

        name = self.noms(varchars)
        if not name:
            self._raiseSyntaxError('expected variable name')

        return s_ast.Const(name)

    def varderef(self, varv):
        self.nextmust('.')
        varn = self.vartokn()
        return s_ast.VarDeref(kids=[varv, varn])

    def varcall(self, varv):
        args, kwargs = self.callargs()

        args = s_ast.CallArgs(kids=args)
        kwargs = s_ast.CallKwargs(kids=kwargs)

        return s_ast.FuncCall(kids=[varv, args, kwargs])

    def kwarg(self):
        name = s_ast.Const(self.noms(varchars))
        self.nextmust('=')
        valu = self.valu()
        return s_ast.CallKwarg(kids=(name, valu))

    def callargs(self):

        self.nextmust('(')

        args = []
        kwargs = []

        while True:

            self.ignore(whitespace)

            if self.nextstr(')'):
                self.offs += 1
                return args, kwargs

            if self.nextre('^[a-zA-Z][a-zA-Z0-9_]*='):
                kwargs.append(self.kwarg())
            else:
                args.append(self.valu())

            self.ignore(whitespace)

            if self.nextstr(')'):
                self.offs += 1
                return args, kwargs

            self.nextmust(',')

    def varvalu(self, varn=None):
        '''
        $foo
        $foo.bar
        $foo.bar()
        $foo[0]
        $foo.bar(10)
        '''

        self.ignore(whitespace)

        if varn is None:
            varn = self.varname()

        varv = s_ast.VarValue(kids=[varn])

        # handle derefs and calls...
        while self.more():

            if self.nextstr('.'):
                varv = self.varderef(varv)
                continue

            if self.nextstr('('):
                varv = self.varcall(varv)
                continue

            #if self.nextstr('['):
                #varv = self.varslice(varv)

            break

        return varv

    def cmdname(self):

        self.ignore(whitespace)

        name = self.noms(cmdset)
        if not name:
            self._raiseSyntaxError(f'expected cmd name')

        return s_ast.Const(name)

    def cmdargv(self):
        '''
        cmdargv *must* have leading whitespace to prevent
        foo@bar from becoming cmdname foo with argv=[@bar]
        '''

        argv = []
        while self.more():

            # cmdargv *requires* whitespace
            if not self.ignore(whitespace):
                break

            # if we hit a | or a } we're done
            if self.nextstr('|'):
                break

            if self.nextstr('}'):
                break

            if not self.nextstr('{'):
                valu = self.cmdvalu()
                argv.append(valu)
                continue

            start = self.offs
            self.subquery()

            text = self.text[start:self.offs]

            argv.append(text)

        return s_ast.Const(tuple(argv))

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

        self._raiseSyntaxError('unexpected end of query text')

    def singlequoted(self):

        self.ignore(whitespace)

        self.nextmust("'")

        text = ''

        offs = self.offs
        while offs < self.size:

            c = self.text[offs]
            offs += 1

            if c == "'":

                self.offs = offs
                return text

            text += c

        self._raiseSyntaxError('unexpected end of query text')

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

        self.nextmust('{')

        q = self.query()

        subq = s_ast.SubQuery(kids=(q,))

        self.ignore(whitespace)

        self.nextmust('}')

        return subq

    def tagname(self):

        self.ignore(whitespace)

        self.nextmust('#')

        self.ignore(whitespace)

        if self.nextstr('$'):
            return self.varvalu()

        text = self.noms(until=tagterm)

        return s_ast.TagName(text)

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

    def peek(self, chars):
        tokn = ''
        offs = self.offs
        while offs < len(self.text):

            char = self.text[offs]
            offs += 1

            if char not in chars:
                break

            tokn += char

        return tokn

    def nextre(self, text):
        regx = recache.get(text)
        if regx is None:
            recache[text] = regx = regex.compile(text)

        return regx.match(self.text[self.offs:])

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
        size = 0
        while self.nextchar() in charset:
            size += 1
            self.offs += 1
        return size

    def eat(self, size, ignore=None):
        self.offs += size
        if ignore is not None:
            self.ignore(ignore)
