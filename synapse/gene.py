import operator

import synapse.common as s_common
import synapse.lib.syntax as s_syntax


class UndefinedValue: pass
undefined = UndefinedValue()

class GeneLab:

    def __init__(self, globs=None):

        if globs is None:
            globs = {}

        self.globs = globs
        self.exprcache = {}

    def clear(self):
        self.exprcache.clear()

    def getGeneExpr(self, text):
        expr = self.exprcache.get(text)
        if expr is None:
            toks = tokenize(text)
            node, off = expression(toks)
            self.exprcache[text] = expr = node.eval
        return expr

tokstrs = [

    '!=',
    '==',
    '<=',
    '&&',
    '||',
    '<=',
    '>=',

    '>>',
    '<<',

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
    ',',
]

def asint(f):
    def oper(x, y):
        return int(f(x, y))
    return oper

def bint(x):
    '''
    Return a boolean integer from a normal integer.
    ( ie 0 if x == 0, else 1 )
    '''
    return int(x != 0)

def logical_and(x, y):
    return bint(x) & bint(y)

def logical_or(x, y):
    return bint(x) | bint(y)

opers = {
    '==': asint(operator.eq),
    '!=': asint(operator.ne),
    '<=': asint(operator.le),
    '>=': asint(operator.ge),

    #'~=':

    '<': asint(operator.lt),
    '>': asint(operator.gt),

    '**': operator.pow,

    '^': operator.xor,
    '&': operator.and_,
    '|': operator.or_,
    '!': operator.not_,

    '<<': operator.lshift,
    '>>': operator.rshift,

    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,

    '&&': logical_and,
    '||': logical_or,

}

# similar to CPP as described in: http://en.cppreference.com/w/cpp/language/operator_precedence
tokninfo = {

    #'var':{'prec':0},
    #'valu':{'prec':0},

    #'(':{'prec':2},
    #'[':{'prec':2},

    #'!':{'prec':3}, # R

    '**': {'prec': 4}, # not in cpp

    '*': {'prec': 5},
    '/': {'prec': 5},

    '+': {'prec': 6},
    '-': {'prec': 6},

    '<<': {'prec': 7},
    '>>': {'prec': 7},

    '<=': {'prec': 8, 'rtol': 1},
    '>=': {'prec': 8, 'rtol': 1},

    '<': {'prec': 8, 'rtol': 1},
    '>': {'prec': 8, 'rtol': 1},

    '==': {'prec': 9, 'rtol': 1},
    '!=': {'prec': 9, 'rtol': 1},

    '&': {'prec': 10},
    '^': {'prec': 11},
    '|': {'prec': 12},

    '&&': {'prec': 13},
    '||': {'prec': 14},
}

class GeneNode:
    def __init__(self, tokn, kids=()):
        self.tokn = tokn
        self.kids = kids

    def eval(self, syms):
        return self._eval(syms)

    def getNodePrec(self):
        return self.tokn[1].get('prec')

class ValuNode(GeneNode):
    def _eval(self, syms):
        return self.tokn[1].get('valu')

class VarNode(GeneNode):
    def _eval(self, syms):
        name = self.tokn[1].get('name')
        valu = syms.get(name, undefined)
        if valu is undefined:
            raise s_common.NoSuchName(name=name)
        return valu

class CallNode(GeneNode):
    def _eval(self, syms):
        func = self.kids[0].eval(syms)
        argv = self.kids[1].eval(syms)
        return func(*argv)

class ListNode(GeneNode):
    def _eval(self, syms):
        return [k.eval(syms) for k in self.kids]

class OperNode(GeneNode):
    def _eval(self, syms):
        func = opers.get(self.tokn[0])
        return func(self.kids[0].eval(syms), self.kids[1].eval(syms))

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

        _, off = s_syntax.nom_whitespace(text, off)
        if off >= tlen:
            break

        if s_syntax.nextin(text, off, '"\''):
            tokn = ('valu', {'off': off, 'type': 'str'})
            tokn[1]['valu'], off = s_syntax.parse_string(text, off, trim=False)

            tokn[1]['end'] = off
            toks.append(tokn)

            continue

        if s_syntax.nextin(text, off, '0123456789'):
            tokn = ('valu', {'off': off, 'type': 'int'})
            tokn[1]['valu'], off = s_syntax.parse_int(text, off)

            tokn[1]['end'] = off
            toks.append(tokn)

            continue

        tokdone = False
        for tok in tokstrs:

            if text.startswith(tok, off):
                tokn = (tok, {'off': off})

                off += len(tok)
                tokn[1]['end'] = off

                toks.append(tokn)

                tokdone = True
                break

        if tokdone:
            continue

        if not s_syntax.nextin(text, off, varset):
            raise s_common.BadSyntaxError(at=off, mesg='no valid tokens found')

        tokn = ('var', {'off': off})
        tokn[1]['name'], off = s_syntax.nom(text, off, varset, trim=False)

        toks.append(tokn)

    for tokn in toks:
        tokn[1].update(tokninfo.get(tokn[0], {}))

    return toks

def istok(toks, off, c):
    '''
    Returns True if the tokn at offset is c.
    '''
    if off >= len(toks):
        return False
    return toks[off][0] == c

def istokoper(toks, off):
    '''
    Returns True if the tokn at offset is an oper.
    '''
    if off >= len(toks):
        return False
    return opers.get(toks[off][0]) is not None

#def istokin(toks,off,vals):
    #'''
    #Returns True if the tokn at offset is in vals.
    #'''
    #if off >= len(toks):
        #return False
    #return toks[off][0] in vals

def nexttok(toks, off):
    '''
    Return the next tokn,off (or None,off) from toks at off.
    '''
    if off >= len(toks):
        raisetok(toks[-1], 'End of Input')
    return toks[off], off + 1

def exprlist(toks, off=0):
    '''
    Parse an expression list from the token stream.
    Returns a list of expression nodes and offset.
    '''
    kids = []

    tok0, off = nexttok(toks, off)
    if tok0[0] != '(':
        raisetok(tok0, 'Expected ([expr, ...])')

    if istok(toks, off, ')'):
        _, off = nexttok(toks, off)
        return ListNode(tok0, kids=[]), off

    while True:
        node, off = expression(toks, off)
        if node is None:
            raisetok(tok0, 'Expected expression list')

        kids.append(node)

        if istok(toks, off, ')'):
            tend, off = nexttok(toks, off)
            break

        tokn, off = nexttok(toks, off)
        if tokn[0] != ',':
            raisetok(tokn, 'Expected , or )')

    return ListNode(tok0, kids=kids), off

def raisetok(tokn, mesg):
    off = tokn[1].get('off')
    raise s_common.BadSyntaxError(mesg=mesg, off=off)

def exprbase(toks, off=0):
    '''
    Parse a simple base expression.

    ( <expr> )
    <valu>
    <var>
    <var> (...)
    '''

    tokn, off = nexttok(toks, off)

    if tokn[0] == 'valu':
        return ValuNode(tokn), off

    # right recurse based on (<expr>)
    if tokn[0] == '(':

        node, off = expression(toks, off)
        if node is None:
            raisetok(tokn, 'expected (<expression>)')

        node.tokn[1]['prec'] = 2 #NOTE: (<expr>) is precedence 2

        junk, off = nexttok(toks, off)
        if junk[0] != ')':
            raisetok(junk, 'expected )')

        return node, off

    if tokn[0] != 'var':
        raisetok(tokn, 'Expected var, valu, or (<expr>)')

    node = VarNode(tokn)

    # CallNode: <var> ( [<expr> [,...] ] )
    if istok(toks, off, '('):
        argv, off = exprlist(toks, off)
        node = CallNode(tokn, kids=[node, argv])

    return node, off

def expression(toks, off=0):
    '''
    Parse an expression from the token stream.
    Returns node,off.
    '''
    node, off = exprbase(toks, off)

    while off < len(toks):

        # CallNode: <expr> ( [<expr> [,...] ] )
        if istok(toks, off, '('):
            tokn = toks[off]
            argv, off = exprlist(toks, off)
            node = CallNode(tokn, kids=[node, argv])
            continue

        #FIXME subscript ( foo[x] ) goes here.

        # If it's not a valid 2 part oper, we're at the end
        if not istokoper(toks, off):
            break

        # this should be an operator now...
        tokn, off = nexttok(toks, off)

        # classic left recursion
        nod1, off = exprbase(toks, off)
        if isinstance(node, OperNode) and node.getNodePrec() > tokn[1].get('prec'):
            # classic tree rotate
            node.kids[1] = OperNode(tokn, kids=[node.kids[1], nod1])
        else:
            node = OperNode(tokn, kids=[node, nod1])

    return node, off

def eval(text, syms=None):
    '''
    Evaluate the given expression (with specified symbols).

    Example:

        eval('foo:bar <= baz + 10', syms=tufo[1])

    '''
    if syms is None:
        syms = {}

    toks = tokenize(text)
    node, off = expression(toks)

    if off < len(toks):
        raisetok(toks[off], 'trailing text')

    return node.eval(syms)
