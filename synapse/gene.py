import operator

import synapse.exc as s_exc
import synapse.lib.syntax as s_syntax

class GeneLab:

    def __init__(self, globs=None):

        if globs == None:
            globs = {}

        self.globs = globs
        self.exprcache = {}

    def clear(self):
        self.exprcache.clear()

    def getGeneExpr(self, text):
        expr = self.exprcache.get(text)
        if expr == None:
            toks = tokenize(text)
            node,off = expression(toks)
            self.exprcache[text] = expr = node.eval
        return expr

        #self.geneexprs = {}
        #self.genenodes = {}

    #def clear(self):

    #def scope(self):
        #scop = Scope(self)
        #return Scope(**self.globs)

    #def addGeneFunc(self, name, func):
    #def addGeneExpr(self, name, text):

    #def eval(self, text, **syms):

    #def evalGeneExpr(self, name, **syms):

tokstrs = [
    '!=',
    '==',
    '<=',
    '&&',
    '||',
    '<=',
    '>=',

    '**',

    '<',
    '>',

    '(',
    ')',

    '+',
    '-',
    '*',
    '/',

    '^',
    '|',
    '&',
]

def asint(f):
    def oper(x,y):
        return int(f(x,y))
    return oper

opers = {
    '==':asint(operator.eq),
    '!=':asint(operator.ne),
    '<=':asint(operator.le),
    '>=':asint(operator.ge),

    #'~=':

    '<':asint(operator.lt),
    '>':asint(operator.gt),

    '**':operator.pow,

    '^':operator.xor,
    '&':operator.and_,
    '|':operator.or_,
    '!':operator.not_,

    '+':operator.add,
    '-':operator.sub,
    '*':operator.mul,
    '/':operator.truediv,
}

class GeneNode:
    def __init__(self, tokn, kids=()):
        self.tokn = tokn
        self.kids = kids

    def eval(self, syms):
        return self._eval(syms)

class ValuNode(GeneNode):
    def _eval(self, syms):
        return self.tokn[1].get('valu')

class VarNode(GeneNode):
    def _eval(self, syms):
        name = self.tokn[1].get('name')
        valu = syms.get(name)
        if valu == None:
            raise s_exc.NoSuchName(name=name)
        return valu

class CallNode(GeneNode):
    def _eval(self, syms):
        func = self.kids[0].eval(syms)
        args = [ k.eval(syms) for k in self.kids[1:] ]
        return func(*args)

class OperNode(GeneNode):
    def _eval(self, syms):
        func = opers.get(self.tokn[0])
        return func( self.kids[0].eval(syms), self.kids[1].eval(syms) )

varset = set(':abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345678910')

def tokenize(text):
    '''
    Produce a token list from the given text string.

    [ (<tok>,<info>), ... ]
    '''
    off = 0
    tlen = len(text)

    toks = []

    while off < tlen:

        _,off = s_syntax.nom_whitespace(text,off)
        if off >= tlen:
            break

        if s_syntax.nextin(text,off,'"\''):
            tokn =('valu',{'off':off,'type':'str'})
            tokn[1]['valu'],off = s_syntax.parse_string(text,off,trim=False)

            tokn[1]['end'] = off
            toks.append(tokn)

            continue

        if s_syntax.nextin(text,off,'0123456789'):
            tokn =('valu',{'off':off,'type':'int'})
            tokn[1]['valu'],off = s_syntax.parse_int(text,off)

            tokn[1]['end'] = off
            toks.append(tokn)

            continue

        tokdone = False
        for tok in tokstrs:

            if text.startswith(tok,off):
                tokn = (tok,{'off':off})

                off += len(tok)
                tokn[1]['end'] = off

                toks.append(tokn)

                tokdone = True
                break

        if tokdone:
            continue

        if not s_syntax.nextin(text,off,varset):
            raise s_exc.SyntaxError(at=off,mesg='no valid tokens found')

        tokn = ('var',{'off':off})
        tokn[1]['name'],off = s_syntax.nom(text,off,varset,trim=False)

        toks.append(tokn)

    return toks

def istok(toks,off,c):
    '''
    Returns True if the tokn at offset is c.
    '''
    if off >= len(toks):
        return False
    return toks[off][0] == c

def istokoper(toks,off):
    '''
    Returns True if the tokn at offset is an oper.
    '''
    if off >= len(toks):
        return False
    return opers.get(toks[off][0]) != None

def istokin(toks,off,vals):
    '''
    Returns True if the tokn at offset is in vals.
    '''
    if off >= len(toks):
        return False
    return toks[off][0] in vals

def nexttok(toks,off):
    '''
    Return the next tokn,off (or None,off) from toks at off.
    '''
    if off >= len(toks):
        raisetok(toks[-1],'End of Input')
    return toks[off],off+1

def exprlist(toks,off):
    '''
    Parse an expression list from the token stream.
    Returns a list of expression nodes and offset.
    '''
    ret = []

    while istokin(toks,off,('var','valu')):

        node,off = expression(toks,off)

        ret.append(node)

        if not istok(toks,off,','):
            break

        off += 1

    return ret,off

def raisetok(tokn,mesg):
    off = tokn[1].get('off')
    raise s_exc.SyntaxError(mesg=mesg,off=off)

def expression(toks, off=0):
    '''
    Parse an expression from the token stream.
    Returns node,off.
    '''
    # expression:
    #    <var|valu>
    #    <var|valu> <oper> <expression>
    #    <var> ( [<expression>...] ) ]

    tokn,off = nexttok(toks,off)

    if tokn[0] not in ('var','valu'):
        raisetok(tokn,'Expected var or valu')

    if tokn[0] == 'var':
        node = VarNode(tokn)
    else:
        node = ValuNode(tokn)

    # FIXME make this a loop for call/deref/slice syntax

    # CallNode: <var> ( [<expr> [,...] ] )
    if tokn[0] == 'var' and istok(toks,off,'('):

        kids = [ node ]
        args,off = exprlist(toks,off+1)

        kids.extend(args)

        ntok,off = nexttok(toks,off)
        if ntok[0] != ')':
            raisetok(ntok,'Expected ")"')

        node = CallNode(tokn,kids=kids)

    # now, do we have an operator next?
    if istokoper(toks,off):
        tokn,off = nexttok(toks,off)
        # FIXME precedence goes here... :D
        rnode,off = expression(toks,off)
        node = OperNode(tokn,kids=[node,rnode])

    return node,off

def eval(text,syms=None):
    '''
    Evaluate the given expression (with specified symbols).

    Example:

        eval('foo:bar <= baz + 10', syms=tufo[1])

    '''
    if syms == None:
        syms = {}
    toks = tokenize(text)
    node,off = expression(toks)
    return node.eval(syms)
