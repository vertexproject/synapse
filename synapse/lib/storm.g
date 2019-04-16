%import common.WS -> _WS
%import common.LCASE_LETTER
%import common.LETTER
%import common.DIGIT
%import common.ESCAPED_STRING

query: _WSCOMM? ((_command | queryoption | _editopers | _oper) _WSCOMM?)*

_command: "|" _WS? stormcmd _WSCOMM? ["|"]

queryoption: "%" _WS? /[a-z]+/ _WS? "=" /\w+/
_editopers: "[" _WS? (_editoper _WS?)* "]"
_editoper: editpropset | editunivset | edittagadd | editpropdel | editunivdel | edittagdel | editnodeadd
edittagadd: "+" tagname [_WS? "=" _valu]
editunivdel: "-" UNIVPROP
edittagdel: "-" tagname
editpropset: RELPROP _WS? "=" _WS? _valu
editpropdel: "-" RELPROP
editunivset: UNIVPROP _WS? "=" _WS? _valu
editnodeadd: ABSPROPNOUNIV _WS? "=" _WS? _valu
ABSPROP: PROPNAME
ABSPROPNOUNIV: PROPS

_oper: subquery | _formpivot | formjoin | formpivotin | formjoinin | lifttagtag | opervarlist | valuvar | filtoper
    | liftbytag | operrelprop | forloop | switchcase | "break" | "continue" | _liftprop | stormcmd

forloop: "for" _WS? (_varname | varlist) _WS? "in" _WS? varvalu _WS? subquery
subquery: "{" query "}"
switchcase: "switch" _WS? varvalu _WS? "{" (_WSCOMM? (("*" _WS? ":" subquery) | (CASEVALU _WSCOMM? subquery)) )* _WSCOMM? "}"
varlist: "(" [_WS? _varname (_WS? "," _WS? _varname)*] _WS? ["," _WS?] ")"
CASEVALU: (DOUBLEQUOTEDSTRING _WSCOMM? ":") | /[^:]+:/


// FIXME:  reconsider this after prop redo
// Note: changed from syntax.py in that cannot start with ':' or '.'
VARSETS: ("$" | "." | LETTER | DIGIT) ("$" | "." | ":" | LETTER | DIGIT)*

_formpivot: formpivot_pivottotags | formpivot_pivotout | formpivot_
formpivot_pivottotags: "->" _WS? TAGMATCH
formpivot_pivotout:    "->" _WS? "*"
formpivot_:            "->" _WS? ABSPROP

formjoin: "-+>" _WS? "*" -> formjoin_pivotout
        | "-+>" _WS? ABSPROP -> formjoin_formpivot

formpivotin: "<-" _WS? "*" -> formpivotin_
           | "<-" _WS? ABSPROP -> formpivotin_pivotinfrom

formjoinin: "<+-" _WS? "*" -> formjoinin_pivotin
          | "<+-" _WS? ABSPROP -> formjoinin_pivotinfrom
opervarlist: varlist _WS? "=" _WS? _valu

operrelprop: RELPROP _WS? "->" _WS? ("*" | ABSPROP) -> operrelprop_pivot
           | RELPROP _WS? "-+>" _WS? ABSPROP -> operrelprop_join

valuvar: _varname _WS? "=" _WS? _valu

_liftprop: liftformtag | liftpropby | liftprop
liftformtag: PROPNAME tagname [_WS? CMPR _valu]
liftpropby: PROPNAME _WS? CMPR _WS? _valu
liftprop: PROPNAME
lifttagtag: "#" tagname
liftbytag: tagname
tagname: "#" _WS? (_varname | TAG)

_varname: "$" _WS? VARTOKN
VARTOKN: VARCHARS
VARCHARS: (LETTER | DIGIT | "_")+
stormcmd: CMDNAME (_WS cmdargv)* [_WS? "|"]
cmdargv: subquery | DOUBLEQUOTEDSTRING | SINGLEQUOTEDSTRING | NONCMDQUOTE

// Note: deviates from syntax.py in that moved regexp up from ast into syntax
TAG: /([\w]+\.)*[\w]+/
TAGMATCH: /#(([\w*]+\.)*[\w*]+)?/

// https://regex101.com/r/l8hFq8/1
CMPR: /[@!<>^~=][@!<>^~=]*|\*[^=\s]*?=/
_valu: NONQUOTEWORD | valulist | varvalu | RELPROPVALU | UNIVPROPVALU | tagpropvalue | DOUBLEQUOTEDSTRING
    | SINGLEQUOTEDSTRING
valulist: "(" [_WS? _valu (_WS? "," _WS? _valu)*] _WS? ["," _WS?] ")"
tagpropvalue: tagname

NONCMDQUOTE: /[^ \t\n|}]+/
NONQUOTEWORD: (LETTER | DIGIT | "-" | "?") /[^ \t\n),=\]}|]*/

varvalu:  _varname (VARDEREF | varcall)*
varcall: valulist
filtoper: FILTPREFIX cond
FILTPREFIX: "+" | "-"

cond: condexpr | condsubq | ("not" _WS? cond)
    | ((RELPROP | UNIVPROP | tagname | ABSPROPNOUNIV) [_WS? CMPR _WS? _valu])
    | TAGMATCH
condexpr: "(" _WS? cond (_WS? (("and" | "or") _WS? cond))* _WS? ")"
condsubq: "{" _WSCOMM? query _WS? "}" [_WSCOMM? CMPR _valu]
VARDEREF: "." VARTOKN
DOUBLEQUOTEDSTRING: ESCAPED_STRING
SINGLEQUOTEDSTRING: "'" /[^']/ "'"
UNIVPROP:  UNIVNAME
UNIVPROPVALU: UNIVPROP

RELPROP: ":" VARSETS
RELPROPVALU: RELPROP

// Whitespace or comments
_WSCOMM: (CCOMMENT | CPPCOMMENT | _WS)+

// From https://stackoverflow.com/a/36328890/6518334
CCOMMENT: /\/\*+[^*]*\*+([^\/*][^*]*\*+)*\//
CPPCOMMENT: /\/\/[^\n]*/

PROPS: /[a-z][a-z0-9]*(:[a-z0-9]+)+([:.][a-z][a-z0-9]+)*/
UNIVNAME: /\.[a-z][a-z0-9]*([:.][a-z0-9]+)*/
PROPNAME: PROPS | UNIVNAME

CMDNAME: /[a-z][a-z0-9.]+/
